#!/usr/bin/env python3
"""error-audit.py — 错误契约与可诊断性审计（R-20）

用法:
  python scripts/error-audit.py scan <路径> [--format markdown|json] [--fail-on-gap]
  python scripts/error-audit.py check --file errors.json [--format markdown|json] [--fail-on-gap]
  python scripts/error-audit.py cases
  python scripts/error-audit.py --self-test

静态规则（scan，逐行，启发式）:
  EC-01 CRITICAL  响应里输出 err.stack / exception stack
  EC-02 CRITICAL  直接把 err/异常对象塞进响应体
  EC-03 HIGH      生产配置开启调试细节（include-stacktrace/include-message/DEBUG）
  EC-04 HIGH      404/未找到处理返回 200
  EC-05 MEDIUM    空 catch / except: pass（吞掉错误）
  EC-06 HIGH      500 处理回显 err.message
  EC-07 MEDIUM    调试端点/Actuator 全暴露
  EC-08 MEDIUM    错误消息拼接绝对路径（__dirname / cwd / abspath）

清单规则（check，读取采集 JSON）:
  EC-20 S1        响应体泄漏堆栈/绝对路径/SQL/内网主机/框架版本
  EC-21 HIGH      实际状态码与契约不符
  EC-22 HIGH      5xx 既无稳定 code 也无 correlation id
  EC-23 HIGH      错误响应 Content-Type 不是 JSON（HTML 错误页）
  EC-24 HIGH      429/503 缺 Retry-After
  EC-25 HIGH      存在性泄漏（未认证判 403 / 403 与 404 同体 / 显式 leak）
  EC-26 MEDIUM    message 为空或 undefined/null/error
  EC-27 HIGH      生产配置 debug=true 或 include-stacktrace=always
  EC-28 HIGH      GraphQL 200 + errors 内含内部堆栈
  EC-29 S1        HTML 错误页反射请求内容（XSS）
  EC-30 MEDIUM    所有错误均无稳定 code
  EC-31 MEDIUM    所有错误均无 trace/request id（不可诊断）

诚实边界:
  - 不联网：只读本地文件与采集 JSON，不发请求。
  - 不代填：cases 的状态码/响应体/头必须来自真实请求；脚本只做规则判定。
  - 不证明：静态命中是线索；GREEN 不代表生产未泄漏（可能是另一路径/另一部署）。
  - correlation id 的「可诊断」还要求日志可检索，脚本不读日志系统，只检查字段存在。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile

SKIP_DIRS = {
    ".git", "node_modules", ".workbuddy-ai", ".test-memory", "dist", "build",
    ".venv", "venv", "__pycache__", ".next", "target", ".idea", "coverage",
}
SKIP_FILES = {"error-audit.py"}
CODE_SUFFIXES = (
    ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".py", ".php", ".rb", ".java",
    ".kt", ".go", ".cs", ".rs", ".vue", ".svelte", ".properties", ".yml", ".yaml", ".env",
)

STACK_RE = re.compile(
    r"(?:\bat\s+[^\n()]*\(\s*[^()\s]*\.\w+:\d+(?::\d+)?\s*\))"   # V8: at fn (file:line:col)
    r"|(?:\bat\s+\S*\.\w+:\d+(?::\d+)?)"                          # at file:line[:col]
    r"|(?:Traceback \(most recent call last\))"
    r"|(?:File \"[^\"]+\", line \d+)",
    re.M,
)
PATH_RE = re.compile(r"(?:[A-Za-z]:\\[^\s\"']+)|(?:/(?:home|srv|var|app|usr)/[^\s\"']+)")
SQL_RE = re.compile(r"(?:syntax error|near \"|SQLSTATE|ORA-\d{5}|sqlite3\.|pg_|unclosed quotation)", re.I)
HOST_RE = re.compile(r"(?:\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b)|(?:\b192\.168\.\d{1,3}\.\d{1,3}\b)|(?:localhost:\d+)|(?:[\w-]+\.internal\b)")
VERSION_RE = re.compile(r"(?:X-Powered-By|Express/\d|nginx/\d|Apache/\d|Werkzeug/\d|ASP\.NET)", re.I)

SEV_ORDER = {"CRITICAL": 0, "S1": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def iter_files(root: str):
    if os.path.isfile(root):
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            if name in SKIP_FILES:
                continue
            if name.endswith(CODE_SUFFIXES) or name == ".env":
                yield os.path.join(dirpath, name)


def line_findings(line: str) -> list[tuple[str, str, str]]:
    low = line.lower()
    out: list[tuple[str, str, str]] = []
    is_log = bool(re.search(r"(console\.|logger\.|log\.|print\(|logging\.|sys\.stderr)", line))

    if ".stack" in low and not is_log and re.search(
            r"(res\.(json|send|status|end)|response\.|reply\.|body\s*[:=]|return\s)", line):
        out.append(("EC-01", "CRITICAL", "响应路径输出 .stack"))

    if re.search(r"(res\.(send|json|end)|response\.(send|json))\(\s*(err|error|e|ex|exception)\s*\)", line) or \
       re.search(r"res\.(json|send)\(\s*\{\s*(error|err|e)\s*:\s*(err|error|e|ex|exception)\s*\}", line) or \
       re.search(r"res\.json\(\s*\{[^}]*\.\.\.\s*(err|error|e)\b", line):
        out.append(("EC-02", "CRITICAL", "直接回传异常对象"))

    if re.search(r"include-stacktrace\s*[=:]\s*always|include-message\s*[=:]\s*always", low) or \
       re.search(r"^\s*debug\s*=\s*true\b", low) or re.search(r"debug\s*=\s*true\s*\)", low) or \
       re.search(r"display_errors\s*=\s*on\b", low):
        out.append(("EC-03", "HIGH", "生产配置开启调试细节"))

    if re.search(r"(notfound|not_found|not found)", low) and re.search(r"status\s*\(\s*200\s*\)|statuscode\s*=\s*200", low):
        out.append(("EC-04", "HIGH", "未找到处理返回 200"))

    if re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", line) or re.search(r"except[^:]*:\s*pass\b", low) or \
       re.search(r"catch\s*\{\s*\}", line):
        out.append(("EC-05", "MEDIUM", "空 catch 吞掉错误"))

    if re.search(r"status\s*\(\s*500\s*\)", low) and re.search(r"(?:message|error|detail)\s*:\s*(err|error|e|ex)\.message", low):
        out.append(("EC-06", "HIGH", "500 处理回显 err.message"))

    if re.search(r"['\"]/__debug__|app\.(get|use)\(\s*['\"]/debug|exposure\.include\s*[=:]\s*[\"']?\*", low):
        out.append(("EC-07", "MEDIUM", "调试端点/Actuator 全暴露"))

    if re.search(r"(message|detail|error)\s*[:=][^\n]*(__dirname|process\.cwd\(\)|os\.path\.abspath|path\(__file__\))", low):
        out.append(("EC-08", "MEDIUM", "错误消息拼接绝对路径"))

    return out


def scan(root: str) -> list[dict]:
    findings: list[dict] = []
    for path in iter_files(root):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except OSError:
            continue
        for idx, line in enumerate(lines, 1):
            for rid, sev, reason in line_findings(line):
                findings.append({
                    "rule": rid, "severity": sev, "file": os.path.relpath(path, root),
                    "line": idx, "reason": reason, "excerpt": line.strip()[:160],
                })
    findings.sort(key=lambda f: (SEV_ORDER.get(f["severity"], 9), f["rule"], f["file"], f["line"]))
    return findings


def leaks_in(body: str) -> list[str]:
    hits: list[str] = []
    for name, rx in (("堆栈", STACK_RE), ("绝对路径", PATH_RE), ("SQL", SQL_RE),
                     ("内网主机", HOST_RE), ("框架版本", VERSION_RE)):
        if body and rx.search(body):
            hits.append(name)
    return hits


def matrix_check(data: dict) -> list[dict]:
    gaps: list[dict] = []
    cases = data.get("cases") or []

    def add(rid, sev, reason):
        gaps.append({"rule": rid, "severity": sev, "reason": reason})

    for case in cases:
        cid = case.get("id") or "?"
        body = str(case.get("body") or "")
        status = case.get("actual_status")
        ctype = str(case.get("content_type") or "").lower()

        hits = leaks_in(body)
        if hits:
            add("EC-20", "S1", "%s 响应体泄漏：%s" % (cid, "、".join(hits)))

        expected = case.get("expected_status")
        if expected is not None and status is not None and int(expected) != int(status):
            add("EC-21", "HIGH", "%s 期望 %s 实际 %s" % (cid, expected, status))

        if status is not None and 500 <= int(status) < 600:
            if not case.get("has_code") and not case.get("has_trace_id"):
                add("EC-22", "HIGH", "%s 为 5xx 且无 code、无 correlation id" % cid)

        if ctype and "json" not in ctype and "problem+json" not in ctype:
            add("EC-23", "HIGH", "%s Content-Type=%s（错误响应应为 JSON）" % (cid, ctype))

        if status is not None and int(status) in (429, 503) and not case.get("retry_after"):
            add("EC-24", "HIGH", "%s 返回 %s 但无 Retry-After" % (cid, status))

        has_msg_key = "message" in case
        msg = str(case.get("message") or "").strip()
        low_body = body.strip().lower()
        if (has_msg_key and msg.lower() in ("", "error", "undefined", "null")) or \
                low_body in ("", "error", "undefined", "null"):
            add("EC-26", "MEDIUM", "%s message 为空或退化值" % cid)

        if "text/html" in ctype and re.search(r"<script|onerror\s*=", body, re.I):
            add("EC-29", "S1", "%s HTML 错误页反射请求内容" % cid)

    existence = data.get("existence") or {}
    unauth = existence.get("unauth")
    if existence.get("leak") or (unauth is not None and int(unauth) == 403):
        add("EC-25", "HIGH", "存在性泄漏：未认证=%s leak=%s" % (unauth, existence.get("leak")))

    config = data.get("config") or {}
    if config.get("debug") is True or str(config.get("include_stacktrace") or "").lower() == "always":
        add("EC-27", "HIGH", "生产配置 debug=%s include_stacktrace=%s" % (
            config.get("debug"), config.get("include_stacktrace")))

    graphql = data.get("graphql") or {}
    for err in (graphql.get("errors") or []):
        msg = str((err or {}).get("message") or "")
        if leaks_in(msg):
            add("EC-28", "HIGH", "GraphQL 200 + errors 泄漏内部细节：%s" % leaks_in(msg))
            break

    if cases:
        if not any(c.get("has_code") for c in cases):
            add("EC-30", "MEDIUM", "所有错误用例均无稳定 code")
        if not any(c.get("has_trace_id") for c in cases):
            add("EC-31", "MEDIUM", "所有错误用例均无 trace/request id（不可诊断）")

    return gaps


def fmt_markdown(items: list[dict], title: str) -> str:
    lines = [f"### {title}", "", "| 规则 | 级别 | 位置/说明 |", "|---|---|---|"]
    for it in items:
        loc = it.get("file", "")
        if it.get("line"):
            loc = f"{loc}:{it['line']}"
        lines.append("| %s | %s | %s — %s |" % (
            it["rule"], it["severity"], loc or "check",
            (it.get("reason") or "").replace("|", "\\|")))
    if not items:
        lines.append("| — | — | 未命中已知模式（不等于未泄漏） |")
    return "\n".join(lines)


CASES = """# R-20 错误契约要点速查

## 1. 状态码判定顺序
未认证(401 + WWW-Authenticate) → 无权限(403) → 不存在(404) →
解析/类型错(400) → 语义不合法(422) → 状态冲突(409) → 媒体类型(415) →
方法(405 + Allow) → 限流(429 + Retry-After) → 未预期(500，通用体)。

## 2. 泄漏正则（扫描 4xx/5xx 响应体）
  堆栈:   at func (file.js:12:34) | File "app.py", line 88 | Traceback
  路径:   C:\\app\\... | /home/app/... | /srv/... | /var/...
  SQL:    syntax error | near " | SQLSTATE | ORA- | unclosed quotation
  主机:   10.x.x.x | 192.168.x.x | localhost:5432 | svc.internal
  版本:   X-Powered-By | Express/4 | nginx/1.24 | Werkzeug

## 3. 可诊断最小集
  {code, message, trace_id, errors:[{field,code}]} + 429/503 带 Retry-After；
  trace_id 必须能在日志/链路中检索到同一请求。

## 4. 存在性对照
  未认证 / 无权限 / 不存在 三态的「状态码 + 响应体 + 时延」逐一记录；
  任一维度可区分 = 可枚举（他人资源）。

## 5. 生产配置必查
  Express: NODE_ENV=production + 自定义错误处理器（不回 err.stack）
  Spring:  server.error.include-stacktrace=never
  Django:  DEBUG=False
  ASP.NET: UseDeveloperExceptionPage 只在 Development
  PHP:     display_errors=Off, APP_DEBUG=false
  GraphQL: introspection/playground 关闭，errors.extensions 不带 stacktrace
"""


def self_test() -> int:
    bad_src = """\
app.use((err, req, res, next) => {
  res.status(500).json({ error: err.message, stack: err.stack });
});
app.get('/api/users/:id', (req, res) => {
  try { findUser(req.params.id); } catch (e) {}
  res.json({ error: e });
});
app.use((req, res) => { res.status(200).json({ error: 'not found' }); });
app.get('/debug', (req, res) => res.json(process.cwd()));
"""
    good_src = """\
app.use((err, req, res, next) => {
  const traceId = req.id || crypto.randomUUID();
  logger.error({ traceId, code: 'INTERNAL_ERROR', err });
  res.status(500).json({ code: 'INTERNAL_ERROR', message: 'Internal server error', trace_id: traceId });
});
"""
    bad_matrix = {
        "cases": [
            {"id": "bad-json", "expected_status": 400, "actual_status": 500,
             "body": "SyntaxError: Unexpected token\n    at JSON.parse (<anonymous>)\n    at D:\\app\\server.js:12:9",
             "content_type": "text/html", "has_code": False, "has_trace_id": False},
            {"id": "rate", "expected_status": 429, "actual_status": 429,
             "body": "Error", "content_type": "application/json", "has_code": False, "has_trace_id": False},
            {"id": "xss", "expected_status": 400, "actual_status": 400,
             "body": "<html><script>alert(1)</script></html>", "content_type": "text/html",
             "has_code": False, "has_trace_id": False},
        ],
        "existence": {"unauth": 403, "forbidden": 403, "missing": 404, "leak": True},
        "config": {"debug": True, "include_stacktrace": "always"},
        "graphql": {"status": 200, "errors": [{"message": "Cannot read property of undefined\n at resolver.js:12"}]},
    }
    good_matrix = {
        "cases": [
            {"id": "bad-json", "expected_status": 400, "actual_status": 400,
             "body": '{"code":"INVALID_JSON","message":"Malformed JSON","trace_id":"abc123"}',
             "content_type": "application/json", "has_code": True, "has_trace_id": True},
            {"id": "boom", "expected_status": 500, "actual_status": 500,
             "body": '{"code":"INTERNAL_ERROR","message":"Internal server error","trace_id":"abc123"}',
             "content_type": "application/problem+json", "has_code": True, "has_trace_id": True},
            {"id": "rate", "expected_status": 429, "actual_status": 429,
             "body": '{"code":"RATE_LIMITED","message":"Too many requests","trace_id":"abc123"}',
             "content_type": "application/json", "has_code": True, "has_trace_id": True, "retry_after": "30"},
        ],
        "existence": {"unauth": 401, "forbidden": 404, "missing": 404, "leak": False},
        "config": {"debug": False, "include_stacktrace": "never"},
    }

    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="eraudit-") as tmp:
        bad_path = os.path.join(tmp, "bad.js")
        good_path = os.path.join(tmp, "good.js")
        with open(bad_path, "w", encoding="utf-8") as fh:
            fh.write(bad_src)
        with open(good_path, "w", encoding="utf-8") as fh:
            fh.write(good_src)

        found = scan(tmp)
        rids = {f["rule"] for f in found}
        for rid in ("EC-01", "EC-02", "EC-04", "EC-05", "EC-06", "EC-07"):
            if rid not in rids:
                failures.append("静态夹具未命中 " + rid)
        # v1.12.0 dogfood 回归：V8 括号帧 `at fn (./src/app.js:41:23)` 必须判堆栈泄漏；
        # 而「at 10:30」这类时间文本不得误判（无文件名扩展名，不构成帧）。
        v8_stack = "Unhandled error\n    at handler (./src/app.js:41:23)\n"
        if "堆栈" not in leaks_in(v8_stack):
            failures.append("V8 括号帧未判堆栈泄漏（回归）")
        if "堆栈" in leaks_in("Rate limit resets at 10:30, retry later"):
            failures.append("时间文本 at 10:30 被误判堆栈（回归）")
        if any(f["file"] == "good.js" for f in found):
            failures.append("干净夹具误报：" + ",".join(f["rule"] for f in found if f["file"] == "good.js"))

        bad_gaps = {g["rule"] for g in matrix_check(bad_matrix)}
        for rid in ("EC-20", "EC-21", "EC-22", "EC-23", "EC-24", "EC-25", "EC-27",
                    "EC-28", "EC-29", "EC-30", "EC-31"):
            if rid not in bad_gaps:
                failures.append("清单夹具未命中 " + rid)
        good_gaps = matrix_check(good_matrix)
        if good_gaps:
            failures.append("干净清单误报：" + ",".join(g["rule"] for g in good_gaps))

        partial = matrix_check({"cases": [
            {"id": "a", "expected_status": 400, "actual_status": 400, "body": "bad request",
             "message": "undefined",
             "content_type": "application/json", "has_code": True, "has_trace_id": True}]})
        if not any(g["rule"] == "EC-26" for g in partial):
            failures.append("退化 message 未命中 EC-26")

    if failures:
        print("SELFTEST FAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("SELFTEST GREEN: 静态 %d 条可命中夹具、清单 %d 条可命中假缺陷、干净夹具零误报" % (
        len({f["rule"] for f in found}), len(bad_gaps)))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R-20 错误契约与可诊断性审计")
    parser.add_argument("command", nargs="?", choices=["scan", "check", "cases", "self-test"],
                        default="cases")
    parser.add_argument("target", nargs="?", default=".")
    parser.add_argument("--file", dest="file", default=None)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--fail-on-gap", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test or args.command == "self-test":
        return self_test()

    if args.command == "scan":
        items = scan(args.target)
        if args.format == "json":
            print(json.dumps({"rule": "R-20", "findings": items}, ensure_ascii=False, indent=2))
        else:
            print(fmt_markdown(items, "R-20 静态线索（启发式，需人工确认）"))
        if args.fail_on_gap:
            critical = [i for i in items if i["severity"] in ("CRITICAL", "S1")]
            return 1 if critical else 0
        return 0

    if args.command == "check":
        if not args.file or not os.path.isfile(args.file):
            print("check 需要 --file errors.json", file=sys.stderr)
            return 2
        with open(args.file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        gaps = matrix_check(data)
        if args.format == "json":
            print(json.dumps({"rule": "R-20", "gaps": gaps}, ensure_ascii=False, indent=2))
        else:
            print(fmt_markdown(gaps, "R-20 清单缺口"))
        if args.fail_on_gap:
            return 1 if gaps else 0
        return 0

    print(CASES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
