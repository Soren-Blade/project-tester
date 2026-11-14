#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""缓存与内容新鲜度离线审计（R-17 配套，零依赖）。

用法：
  python scripts/cache-audit.py scan <path> [--format text|json] [--fail-on-gap]
  python scripts/cache-audit.py headers --file headers.json [--format text|json] [--fail-on-gap]
  python scripts/cache-audit.py cases [--format text|json]
  python scripts/cache-audit.py --self-test

静态规则（scan，行级启发式）：
  CA-01 MEDIUM 用 no-cache 冒充「不存储」（敏感响应应 no-store）
  CA-02 MEDIUM Vary: * —— 共享缓存无法处理
  CA-03 HIGH   public 缓存与身份/会话内容同现
  CA-04 LOW    s-maxage 存在但缺 max-age（浏览器侧无新鲜期）
  CA-05 LOW    immutable 配短 max-age（资源更新不可见）
  CA-06 LOW    Expires 与 max-age 并存（语义漂移，前者被忽略）
  CA-07 HIGH   purge/invalidate 路由无鉴权守卫
  CA-08 MEDIUM stale-while-revalidate / stale-if-error 用于个性化响应

清单规则（headers）：
  CA-10 S1 个性化响应可被 public 缓存
  CA-11 S1 鉴权响应 public 且 Vary 未含 Authorization
  CA-12 S1 带 Set-Cookie 的响应既非 private 也非 no-store
  CA-13 S1 purge 端点未鉴权
  CA-14 MEDIUM public 响应完全没有 Vary
  CA-15 LOW  鉴权/个性化响应用 no-cache 而非 no-store
  CA-16 MEDIUM immutable 配短 max-age

诚实边界：
- 只读本地源码与本地 JSON 清单，**不联网、不代填**任何字段。
- 静态命中只是「可疑写法」，**不证明**线上缓存真的泄漏；未命中**不证明**缓存正确。
- headers 清单只证明「给定头组合内部自洽」，**不证明** CDN 实际配置与真实命中行为。
- 不冒充「缓存安全」「合规」，不替代双会话实测与 Cache-Status / Age 原文留档。
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import traceback
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CODE_SUFFIXES = {
    ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".py", ".go", ".java",
    ".kt", ".php", ".rb", ".cs", ".rs", ".vue", ".svelte", ".html",
    ".conf", ".config", ".json", ".yaml", ".yml", ".toml", ".ini",
}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".test-memory", "dist", "build", ".venv"}

CACHE_WORD = re.compile(
    r"(?i)(cache-control|vary|max-age|s-maxage|immutable|expires|purge|"
    r"invalidate|stale-while-revalidate|stale-if-error)"
)
IDENTITY = re.compile(r"(?i)(set-cookie|res\.cookie|session|cookie|authorization|req\.user|currentUser|auth)")
ROUTE = re.compile(r"(?i)\b(app|router|server|route)\s*\.\s*(get|post|put|delete|patch)\s*\(")
AUTH_GUARD = re.compile(r"(?i)(auth|admin|token|secret|verify|guard|requireLogin|permission|rbac)")


def iter_files(root: Path):
    if root.is_file():
        yield root
        return
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in CODE_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        yield p


def max_age_of(text: str) -> int | None:
    m = re.search(r"(?i)\bmax-age\s*=\s*(\d+)", text)
    return int(m.group(1)) if m else None


def line_findings(line: str) -> list[tuple[str, str, str]]:
    low = line.lower()
    out: list[tuple[str, str, str]] = []
    if "cache-control" in low and "no-cache" in low and "no-store" not in low:
        out.append(("CA-01", "MEDIUM", "用 no-cache 冒充不存储：响应仍会被缓存，敏感内容应 no-store"))
    if re.search(r"(?i)\bvary\b\s*[:=]?\s*['\"]?\*", line):
        out.append(("CA-02", "MEDIUM", "Vary: * 使共享缓存无法正确匹配请求，等同于行为未定义"))
    if "public" in low and IDENTITY.search(line):
        out.append(("CA-03", "HIGH", "public 缓存与身份/会话内容同现：个性化响应可能被共享缓存"))
    if "s-maxage" in low and not re.search(r"(?i)\bmax-age\b", line):
        out.append(("CA-04", "LOW", "只有 s-maxage 没有 max-age：浏览器私有缓存无新鲜期口径"))
    if "immutable" in low:
        ma = max_age_of(line)
        if ma is not None and ma < 31536000:
            out.append(("CA-05", "LOW", f"immutable 配短 max-age={ma}：有效期内用户看不到更新"))
    if "expires" in low and "max-age" in low:
        out.append(("CA-06", "LOW", "Expires 与 max-age 并存：Expires 被忽略，两处口径会漂移"))
    if ROUTE.search(line) and re.search(r"(?i)(purge|invalidate|flush|clean)", line) and not AUTH_GUARD.search(line):
        out.append(("CA-07", "HIGH", "purge/invalidate 路由未见鉴权守卫：任意人可清空缓存"))
    if re.search(r"(?i)stale-(while-revalidate|if-error)", line) and IDENTITY.search(line):
        out.append(("CA-08", "MEDIUM", "stale-while-revalidate / stale-if-error 用于个性化响应：登出后仍可能拿到私有页"))
    return out


def scan(root: Path) -> list[dict]:
    hits: list[dict] = []
    for path in iter_files(root):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception as e:
            hits.append({"rule": "CA-00", "severity": "LOW", "file": str(path),
                         "line": 0, "snippet": f"<读取失败: {e}>", "reason": "无法读取，未审计"})
            continue
        for i, line in enumerate(lines, 1):
            if not CACHE_WORD.search(line):
                continue
            for rid, sev, reason in line_findings(line):
                hits.append({"rule": rid, "severity": sev, "file": str(path),
                             "line": i, "snippet": line.strip()[:200], "reason": reason})
    seen, out = set(), []
    for h in hits:
        key = (h["rule"], h["file"], h["line"])
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out


def audit_headers(routes: list) -> list[dict]:
    issues: list[dict] = []
    if not isinstance(routes, list) or not routes:
        return [{"id": "CA-09", "severity": "S1", "path": "", "reason": "清单为空或无 routes，无法审计"}]

    for r in routes:
        if not isinstance(r, dict):
            issues.append({"id": "CA-09", "severity": "S1", "path": "", "reason": "条目不是对象"})
            continue
        path = str(r.get("path") or "")
        cc = str(r.get("cache_control") or "").lower()
        vary = [str(v).lower() for v in (r.get("vary") or [])]
        personal = bool(r.get("personalized"))
        auth = bool(r.get("auth"))
        cookie = bool(r.get("has_cookie"))
        ma = max_age_of(cc)

        if personal and "public" in cc:
            issues.append({"id": "CA-10", "severity": "S1", "path": path,
                           "reason": "个性化响应标 public：共享缓存可把 A 的内容给 B"})
        if auth and "public" in cc and "authorization" not in vary:
            issues.append({"id": "CA-11", "severity": "S1", "path": path,
                           "reason": "鉴权响应 public 且 Vary 未含 Authorization"})
        if cookie and "no-store" not in cc and "private" not in cc:
            issues.append({"id": "CA-12", "severity": "S1", "path": path,
                           "reason": "响应带 Set-Cookie 但既非 private 也非 no-store"})
        if r.get("purge_endpoint") and not r.get("purge_auth"):
            issues.append({"id": "CA-13", "severity": "S1", "path": path,
                           "reason": "purge 端点未鉴权：任意调用方可清缓存/制造回源风暴"})
        if "public" in cc and not vary:
            issues.append({"id": "CA-14", "severity": "MEDIUM", "path": path,
                           "reason": "public 响应完全没有 Vary：压缩/语言/设备变体会串"})
        if "no-cache" in cc and "no-store" not in cc and (auth or personal):
            issues.append({"id": "CA-15", "severity": "LOW", "path": path,
                           "reason": "鉴权/个性化用 no-cache：中间缓存仍持有副本"})
        if "immutable" in cc and ma is not None and ma < 31536000:
            issues.append({"id": "CA-16", "severity": "MEDIUM", "path": path,
                           "reason": f"immutable 配短 max-age={ma}"})
    return issues


def show_cases() -> list[str]:
    return [
        "# 缓存判定反例（确定性，可直接作为期望值）",
        "",
        "- `Cache-Control: no-cache` 允许缓存，只是每次使用前要回源验证；`no-store` 才禁止存储。",
        "- `public, max-age=600` + `Set-Cookie: sid=...`：共享缓存可存带会话的响应 → S1。",
        "- `/account/foo.jpg` 若源站按 `/account` 处理却按 `.jpg` 命中缓存：换会话即拿到他人页面（缓存欺骗）。",
        "- `Vary: *` 在共享缓存里无法匹配，等价于未定义/不可用；压缩变体应 `Vary: Accept-Encoding`。",
        "- `s-maxage=600` 只约束共享缓存；浏览器侧仍需 `max-age`，否则本地新鲜期口径缺失。",
        "- `immutable` 只在 URL 随内容变化时成立；配 `max-age=60` 或可变 URL 会让用户长期看不到更新。",
        "- 多租户缓存键必须含服务端 tenant；键里没有 tenant 时 A 的 URL 可命中 B 的内容（R-4 交叉）。",
        "",
        "> 这些是确定性规则，不是对被测系统的实测结论；线上必须用双会话 + Cache-Status/Age 原文证明。",
    ]


def parse_args(argv: list[str]) -> dict:
    opts = {"cmd": None, "path": None, "file": None, "format": "text", "fail": False, "self": False}
    rest = argv[1:]
    if "--self-test" in rest:
        opts["self"] = True
        return opts
    if not rest:
        return opts
    opts["cmd"] = rest[0]
    i = 1
    while i < len(rest):
        a = rest[i]
        if a == "--format" and i + 1 < len(rest):
            opts["format"] = rest[i + 1]; i += 2
        elif a == "--file" and i + 1 < len(rest):
            opts["file"] = rest[i + 1]; i += 2
        elif a == "--fail-on-gap":
            opts["fail"] = True; i += 1
        elif not a.startswith("--") and opts["path"] is None:
            opts["path"] = a; i += 1
        else:
            i += 1
    return opts


def print_scan(hits: list[dict], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps({"tool": "cache-audit", "mode": "scan", "hits": hits,
                          "note": "静态命中只是可疑写法；未命中不证明缓存正确"}, ensure_ascii=False, indent=2))
        return
    print(f"# 缓存反模式扫描：{len(hits)} 处可疑")
    for h in hits:
        print(f"[{h['rule']} {h['severity']}] {h['file']}:{h['line']}  {h['reason']}")
        print(f"    {h['snippet']}")
    print("> 未命中不证明缓存正确；必须配合双会话对照与 Cache-Status / Age 原文。")


def print_headers(issues: list[dict], fmt: str) -> None:
    hard = [i for i in issues if i["severity"] == "S1"]
    if fmt == "json":
        print(json.dumps({"tool": "cache-audit", "mode": "headers", "issues": issues,
                          "gaps": len(hard),
                          "note": "只证明给定头组合内部自洽，不证明 CDN 实际配置与命中行为"},
                         ensure_ascii=False, indent=2))
        return
    print(f"# 缓存头策略审计：{len(issues)} 处问题（S1 {len(hard)}）")
    for i in issues:
        print(f"[{i['id']} {i['severity']}] {i['path'] or '-'}  {i['reason']}")
    print(f"> 缺口 {len(hard)} 项；清单自洽不等于线上安全，需双会话实测与头原文留档。")


def self_test() -> int:
    checks: list[tuple[str, bool]] = []
    tmp = Path(tempfile.mkdtemp(prefix="cache-audit-selftest-"))
    bad = tmp / "bad.conf"
    bad.write_text(
        'add_header Cache-Control "no-cache";\n'
        'add_header Vary "*";\n'
        'res.setHeader("Cache-Control", "public, max-age=600"); res.cookie("sid", token);\n'
        'add_header Cache-Control "public, s-maxage=600";\n'
        'add_header Cache-Control "public, max-age=60, immutable";\n'
        'res.setHeader("Expires", exp); res.setHeader("Cache-Control", "max-age=300");\n'
        "app.post('/cache/purge', purgeHandler);\n"
        'res.setHeader("Cache-Control", "private, stale-while-revalidate=600"); req.user;\n',
        encoding="utf-8",
    )
    good = tmp / "good.conf"
    good.write_text(
        'res.setHeader("Cache-Control", "private, no-store");\n'
        'app.post("/admin/purge", requireAdmin, purgeHandler);\n'
        'add_header Cache-Control "public, max-age=31536000, immutable";\n'
        'add_header Vary "Accept-Encoding";\n',
        encoding="utf-8",
    )
    hits = scan(tmp)
    found = {h["rule"] for h in hits}
    for rid in ("CA-01", "CA-02", "CA-03", "CA-04", "CA-05", "CA-06", "CA-07", "CA-08"):
        checks.append((f"scan 检出 {rid}", rid in found))
    checks.append(("good.conf 无 HIGH 命中", not [h for h in hits if h["file"].endswith("good.conf") and h["severity"] == "HIGH"]))

    routes = [
        {"path": "/api/me", "cache_control": "public, max-age=60", "vary": [],
         "personalized": True, "auth": True, "has_cookie": True,
         "purge_endpoint": "/admin/purge", "purge_auth": False},
        {"path": "/app.js", "cache_control": "public, max-age=60, immutable", "vary": []},
        {"path": "/feed", "cache_control": "no-cache, max-age=0", "auth": True},
    ]
    issues = audit_headers(routes)
    ids = {i["id"] for i in issues}
    for rid in ("CA-10", "CA-11", "CA-12", "CA-13", "CA-14", "CA-15", "CA-16"):
        checks.append((f"headers 检出 {rid}", rid in ids))
    good_issues = audit_headers([{"path": "/static/app.js", "cache_control": "private, no-store",
                                  "vary": ["accept-encoding"], "purge_auth": True}])
    checks.append(("私有 no-store 路由零问题", not [i for i in good_issues if i["severity"] == "S1"]))

    cases = "\n".join(show_cases())
    checks.append(("cases 说明 no-cache 与 no-store 区别", "no-store` 才禁止存储" in cases))
    checks.append(("cases 给出缓存欺骗路径", "/account/foo.jpg" in cases))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if failed:
        print(f"SELFTEST RED（{len(failed)} 项失败）")
        return 1
    print(f"SELFTEST GREEN（{len(checks)} 项断言）")
    print("边界：自检只证明本脚本的扫描/头审计逻辑可用，不证明线上缓存安全，不冒充合规。")
    return 0


def main(argv: list[str]) -> int:
    opts = parse_args(argv)
    if opts["self"]:
        return self_test()
    if opts["cmd"] == "scan":
        root = Path(opts["path"] or ".")
        if not root.exists():
            print(f"路径不存在: {root}")
            return 2
        hits = scan(root)
        print_scan(hits, opts["format"])
        high = [h for h in hits if h["severity"] == "HIGH"]
        return 1 if (opts["fail"] and high) else 0
    if opts["cmd"] == "headers":
        if not opts["file"]:
            print("用法: cache-audit.py headers --file headers.json")
            return 2
        try:
            obj = json.loads(Path(opts["file"]).read_text(encoding="utf-8-sig"))
        except Exception as e:
            print(f"读取清单失败: {e}")
            return 2
        routes = obj.get("routes") if isinstance(obj, dict) else obj
        issues = audit_headers(routes or [])
        print_headers(issues, opts["format"])
        return 1 if (opts["fail"] and any(i["severity"] == "S1" for i in issues)) else 0
    if opts["cmd"] == "cases":
        if opts["format"] == "json":
            print(json.dumps({"tool": "cache-audit", "mode": "cases",
                              "no_cache_keeps_copy": True, "no_store_forbids_copy": True,
                              "note": "确定性规则，不替代线上实测"}, ensure_ascii=False, indent=2))
        else:
            print("\n".join(show_cases()))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(3)
