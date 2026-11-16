#!/usr/bin/env python3
"""query-audit.py — 查询语义与分页正确性审计（R-19）

用法:
  python scripts/query-audit.py scan <路径> [--format markdown|json] [--fail-on-gap]
  python scripts/query-audit.py matrix --file pagination.json [--format markdown|json] [--fail-on-gap]
  python scripts/query-audit.py cases
  python scripts/query-audit.py --self-test

静态规则（scan，逐行，启发式）:
  QP-01 CRITICAL  ORDER BY 拼接用户输入（排序键注入）
  QP-02 HIGH      LIMIT / OFFSET 由字符串拼接产生
  QP-03 HIGH      total 取当前页行数（rows.length / len(items)）
  QP-04 MEDIUM    分页 ORDER BY 无唯一 tie-breaker（启发式：出现过 LIMIT 且排序键不含 id）
  QP-05 MEDIUM    LIKE 前导通配符（'%' 与参数直接拼接）
  QP-06 MEDIUM    page/size/limit 取参数后全项目无夹取（min/max/clamp）
  QP-07 MEDIUM    LIKE 参数未转义 % _ 通配符
  QP-08 LOW       OFFSET 由 page*size 计算且无上限

清单规则（matrix，读取采集 JSON）:
  QP-20 S1        逐页遍历出现重复 id
  QP-21 S1        逐页遍历遗漏 expected_ids
  QP-22 S1        并发插入/删除后遍历漂移（stable=false 或有重复/遗漏）
  QP-23 HIGH      declared_total 与逐页并集/条数不一致
  QP-24 HIGH      非白名单 sort 被接受（2xx）
  QP-25 S1        排序/筛选注入把 SQL 回显，或注入请求返回 2xx
  QP-26 MEDIUM    size 上限过宽（>1000）或缺失
  QP-27 MEDIUM    page 边界（0/负数/非数字）返回 5xx
  QP-28 MEDIUM    collation 声明与实际不符
  QP-29 S1        返回了其他租户/他人的行
  QP-30 MEDIUM    深页 P95 超预算（默认 500ms）

诚实边界:
  - 不联网：只读本地文件，不发任何请求。
  - 不代填：采集 JSON 里的 ids/total/状态码必须由真实请求得到；脚本只做集合比对。
  - 不证明：静态命中是「需人工确认的线索」，不是漏洞定论；GREEN 只代表未命中已知模式，
    不代表分页正确、排序稳定、越权不存在。真实结论必须由逐页遍历 + 双会话对照支撑。
  - 不替代压测：深页延迟以采集值为准，脚本不发起计时。
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
SKIP_FILES = {"query-audit.py"}
CODE_SUFFIXES = (
    ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".py", ".php", ".rb", ".java",
    ".kt", ".go", ".cs", ".sql", ".rs", ".vue", ".svelte",
)

SQL_INTERP = ("${", '" +', "' +", ".format(", "% (", "||", "f\"", "f'")
SQL_LEAK_MARKERS = (
    "select ", "from ", "where ", "syntax error", "syntaxerror", "near \"",
    "pg_", "sqlite_", "ora-", "mysql", "unclosed quotation", "column ",
)
PATH_MARKERS = ("/home/", "/app/", "/var/", "/usr/", "/srv/", "C:\\", "D:\\", "\\\\")
STACK_MARKERS = (" at ", "\n    at ", "traceback", "stack", ".java:", ".php:", ".rb:")

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
            if name.endswith(CODE_SUFFIXES):
                yield os.path.join(dirpath, name)


def has_interp(line: str) -> bool:
    return any(tok in line for tok in SQL_INTERP)


def line_findings(line: str, has_clamp: bool) -> list[tuple[str, str, str]]:
    low = line.lower()
    out: list[tuple[str, str, str]] = []

    if "order by" in low and has_interp(line):
        out.append(("QP-01", "CRITICAL", "ORDER BY 与字符串插值同现，排序键可能来自用户输入"))

    if re.search(r"(?:\blimit\b|\boffset\b)\s*(?:=\s*)?(?:\$\{|\"\s*\+|'\s*\+|%\s*\(|%\s*s\b|\.format\()", low):
        out.append(("QP-02", "HIGH", "LIMIT/OFFSET 由字符串插值/拼接产生"))

    if re.search(r"\b(total|count)\b\s*[:=]\s*(rows|items|data|list|results)\.(length|size)", line) or \
       re.search(r"\b(total|count)\b\s*[:=]\s*(len|count)\((rows|items|data|list|results)\)", line):
        out.append(("QP-03", "HIGH", "total 取当前页行数，跨页总数会随页变化"))

    if "limit" in low and "order by" in low and "id" not in low.split("order by", 1)[1]:
        out.append(("QP-04", "MEDIUM", "分页查询的 ORDER BY 未含唯一 tie-breaker（id/主键）"))

    if re.search(r"like\s*(?:concat\()?\s*['\"]%['\"]\s*(?:\+|,|\|\|)", low):
        out.append(("QP-05", "MEDIUM", "LIKE 前导通配符：索引失效且易成全表扫描"))

    if re.search(r"\b(page|size|limit|per_page|page_size)\b\s*=\s*(int|parseint|number|integer)?\s*\(?.*\b(query|args|params|get|form)\b", low) and not has_clamp:
        out.append(("QP-06", "MEDIUM", "page/size 取自请求参数，且同一处（±10 行）未见 min/max/clamp 夹取"))

    like_dynamic = re.search(r"like\s*(?:concat\()?\s*['\"]?%", low) and re.search(r"(?:\+|\|\||\$\{)\s*\w+", low)
    if like_dynamic and not re.search(r"escape|replace\(\s*['\"]%|re\.escape", low):
        out.append(("QP-07", "MEDIUM", "LIKE 动态参数未转义 %/_ 通配符"))

    if re.search(r"offset\s+\S*(page|offset)\s*\*", low):
        out.append(("QP-08", "LOW", "OFFSET 由 page*size 计算，深页会线性变慢"))

    return out


def scan(root: str) -> list[dict]:
    findings: list[dict] = []
    for path in iter_files(root):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except OSError:
            continue
        # 夹取判定只看「同一行或相邻 10 行」：全文件出现的 MAX(id) / Math.max 不能替远处的
        # 分页参数洗白（v1.12.0 dogfood 实证：`MAX(id)` 曾把 QP-06 全文件静音）
        clamp_re = re.compile(r"math\.min|math\.max|\bmin\(|\bmax\(|clamp|minvalue|maxsize|number\.isfinite")
        clamp_flags = [bool(clamp_re.search(l.lower())) for l in lines]
        seen: set[tuple[str, str]] = set()
        for idx, line in enumerate(lines, 1):
            near_clamp = any(clamp_flags[max(0, idx - 10):idx + 9])
            for rid, sev, reason in line_findings(line, near_clamp):
                key = (rid, os.path.relpath(path, root) + f":{idx}")
                if key in seen:
                    continue
                seen.add(key)
                findings.append({
                    "rule": rid, "severity": sev, "file": os.path.relpath(path, root),
                    "line": idx, "reason": reason, "excerpt": line.strip()[:160],
                })
    findings.sort(key=lambda f: (SEV_ORDER.get(f["severity"], 9), f["rule"], f["file"], f["line"]))
    return findings


def _ids(pages: list) -> list[str]:
    out: list[str] = []
    for page in pages or []:
        for item in (page or {}).get("ids") or []:
            out.append(str(item))
    return out


def matrix_check(data: dict) -> list[dict]:
    gaps: list[dict] = []

    def add(rid, sev, reason):
        gaps.append({"rule": rid, "severity": sev, "reason": reason})

    all_ids = _ids(data.get("pages"))
    uniq = list(dict.fromkeys(all_ids))
    dups = sorted({i for i in all_ids if all_ids.count(i) > 1})

    if dups:
        add("QP-20", "S1", "逐页遍历出现重复 id：%s" % ", ".join(dups[:8]))
    expected = [str(i) for i in (data.get("expected_ids") or [])]
    if expected:
        missing = [i for i in expected if i not in set(uniq)]
        if missing:
            add("QP-21", "S1", "遍历遗漏 expected_ids：%s" % ", ".join(missing[:8]))

    conc = data.get("concurrency") or {}
    if conc.get("stable") is False or conc.get("duplicates") or conc.get("missing"):
        add("QP-22", "S1", "并发插入/删除后遍历漂移（stable=%s dup=%s miss=%s）" % (
            conc.get("stable"), conc.get("duplicates"), conc.get("missing")))

    declared = data.get("declared_total")
    if declared is not None:
        if expected and int(declared) != len(expected):
            add("QP-23", "HIGH", "declared_total=%s 但 expected_ids=%d" % (declared, len(expected)))
        elif len(uniq) != int(declared) and not expected:
            add("QP-23", "HIGH", "declared_total=%s 但逐页去重后=%d" % (declared, len(uniq)))

    sort = data.get("sort") or {}
    whitelist = [str(s).lstrip("-") for s in (sort.get("whitelist") or [])]
    accepted = [str(s).lstrip("-") for s in (sort.get("accepted") or [])]
    bad = [s for s in accepted if whitelist and s not in whitelist]
    if bad:
        add("QP-24", "HIGH", "非白名单排序键被接受：%s" % ", ".join(bad))

    inj_status = sort.get("injection_status")
    inj_body = str(sort.get("injection_body") or "")
    if inj_status is not None:
        low = inj_body.lower()
        if any(m in low for m in SQL_LEAK_MARKERS):
            add("QP-25", "S1", "注入请求把 SQL 片段回显到响应体（status=%s）" % inj_status)
        elif 200 <= int(inj_status) < 300:
            add("QP-25", "HIGH", "排序/筛选注入请求返回 %s（应 4xx 拒绝）" % inj_status)

    size = data.get("page_size") or {}
    max_accepted = size.get("max_accepted")
    if max_accepted is None:
        add("QP-26", "MEDIUM", "未提供 size 上限采集值")
    elif int(max_accepted) > 1000:
        add("QP-26", "MEDIUM", "size=%s 被接受，超过 1000 上限" % max_accepted)

    boundary = data.get("boundary") or {}
    for key in ("page_zero_status", "negative_status", "non_numeric_status"):
        val = boundary.get(key)
        if val is not None and int(val) >= 500:
            add("QP-27", "MEDIUM", "%s 返回 %s（边界参数应 4xx 或夹取，不应 5xx）" % (key, val))

    coll = data.get("collation") or {}
    declared_coll = str(coll.get("declared") or "").lower()
    observed_coll = str(coll.get("observed") or "").lower()
    if declared_coll and observed_coll and declared_coll != observed_coll:
        add("QP-28", "MEDIUM", "collation 声明=%s 实测=%s" % (declared_coll, observed_coll))
    if coll.get("duplicates"):
        add("QP-28", "MEDIUM", "大小写/重音对照出现重复项：%s" % coll.get("duplicates"))

    leak = data.get("leak") or {}
    if int(leak.get("foreign_rows") or 0) > 0:
        add("QP-29", "S1", "返回了 %s 行其他租户/他人数据" % leak.get("foreign_rows"))
    if leak.get("total_leak"):
        add("QP-29", "S1", "total 暴露了不可见集合的条数：%s" % leak.get("total_leak"))

    deep = data.get("deep_page") or {}
    p95 = deep.get("p95_ms")
    budget = int(data.get("budget_ms") or 500)
    if p95 is not None and float(p95) > budget:
        add("QP-30", "MEDIUM", "第 %s 页 P95=%sms 超预算 %sms" % (deep.get("page", "?"), p95, budget))

    return gaps


def fmt_markdown(items: list[dict], title: str) -> str:
    lines = [f"### {title}", "", "| 规则 | 级别 | 位置/说明 |", "|---|---|---|"]
    for it in items:
        loc = it.get("file", "")
        if it.get("line"):
            loc = f"{loc}:{it['line']}"
        lines.append("| %s | %s | %s — %s |" % (
            it["rule"], it["severity"], loc or "matrix",
            (it.get("reason") or "").replace("|", "\\|")))
    if not items:
        lines.append("| — | — | 未命中已知模式（不等于已证明正确） |")
    return "\n".join(lines)


CASES = """# R-19 分页要点速查（自测/汇报用）

## 1. offset 漂移的最小构造
数据 1..10，size=3，按 created_at DESC：
- 第 1 页：[10,9,8]；此时插入 11（最新）
- 第 2 页 offset=3 → [9,8,7]   ← 9、8 重复
- 若改为删除 10：第 2 页 → [7,6,5] ← 8 遗漏

## 2. keyset 的正确写法
  WHERE (created_at, id) < (:last_created, :last_id)
  ORDER BY created_at DESC, id DESC
  LIMIT :size
需要 (created_at, id) 复合索引；不能跳任意页，适合无限滚动/导出。

## 3. collation 对照（同一批值）
  ['Ada','ada','Áda','Äda','ada '] 在 ci/ai、ci/as、cs/as 下的排序互不相同；
  声明「不区分大小写」却在 WHERE 层用二进制比较 = 搜索漏命中。

## 4. 总数口径
  total = COUNT(*) 同 WHERE 同权限；内存过滤后 len(rows) 会让第 1 页条数与 total 脱钩。
  估算值（reltuples / track_total_hits=false）只能标「约」，不能写「共 N 条」。

## 5. 边界期望
  page=0/-1/abc -> 4xx 或夹到 1；size>上限 -> 4xx 或截断；越界页 -> 200 空页 + has_next=false。

## 6. 深页
  OFFSET 1000000 需先排序再丢弃 100 万行；P95 随页码线性增长，必须给页码-延迟曲线。
"""


def self_test() -> int:
    bad_src = """\
function list(req, res) {
  const page = parseInt(req.query.page);
  const size = parseInt(req.query.size);
  const sort = req.query.sort;
  const rows = db.query(`SELECT * FROM items ORDER BY ${sort} LIMIT ${size} OFFSET ${page * size}`);
  const total = rows.length;
  const q = req.query.q;
  const hits = db.query(`SELECT * FROM items WHERE name LIKE '%${q}%'`);
  const older = db.query("SELECT * FROM items WHERE name LIKE CONCAT('%', ?, '%')", [q]);
  res.json({ total, rows: hits.concat(older) });
}
"""
    good_src = """\
const ALLOWED = {created_at: 'created_at', id: 'id'};
function list(req, res) {
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const size = Math.min(100, Math.max(1, parseInt(req.query.size, 10) || 20));
  const column = ALLOWED[req.query.sort] ? ALLOWED[req.query.sort] : ALLOWED.created_at;
  const sql = [
    'SELECT * FROM items',
    'ORDER BY created_at DESC, id DESC',
    'LIMIT ? OFFSET ?',
  ].join(' ');
  const rows = db.query(sql, [size, (page - 1) * size]);
  const total = db.count('SELECT COUNT(*) FROM items');
  res.json({ total, rows, column });
}
"""
    bad_matrix = {
        "pages": [{"page": 1, "ids": ["a", "b"]}, {"page": 2, "ids": ["b", "c"]}],
        "expected_ids": ["a", "b", "c", "d"],
        "declared_total": 9,
        "sort": {"whitelist": ["created_at", "id"], "accepted": ["title"],
                 "injection_status": 200, "injection_body": "ok"},
        "page_size": {"max_accepted": 100000},
        "boundary": {"page_zero_status": 200, "negative_status": 500},
        "collation": {"declared": "ci", "observed": "cs"},
        "leak": {"foreign_rows": 2},
        "deep_page": {"page": 1000, "p95_ms": 4200},
        "concurrency": {"stable": False, "duplicates": 1},
    }
    good_matrix = {
        "pages": [{"page": 1, "ids": ["a", "b"]}, {"page": 2, "ids": ["c", "d"]}],
        "expected_ids": ["a", "b", "c", "d"],
        "declared_total": 4,
        "sort": {"whitelist": ["created_at", "id"], "accepted": ["created_at"],
                 "injection_status": 400, "injection_body": "invalid sort"},
        "page_size": {"max_accepted": 100},
        "boundary": {"page_zero_status": 400, "negative_status": 400, "non_numeric_status": 400},
        "collation": {"declared": "ci", "observed": "ci"},
        "leak": {"foreign_rows": 0},
        "deep_page": {"page": 1000, "p95_ms": 320},
        "concurrency": {"stable": True},
    }

    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="qaudit-") as tmp:
        bad_path = os.path.join(tmp, "bad.js")
        good_path = os.path.join(tmp, "good.js")
        with open(bad_path, "w", encoding="utf-8") as fh:
            fh.write(bad_src)
        with open(good_path, "w", encoding="utf-8") as fh:
            fh.write(good_src)

        # v1.12.0 dogfood 回归：远处的 MAX(id) 不得替分页参数洗白（QP-06 必须仍命中）；
        # 同文件近距离 Math.max 夹取则不应再报（QP-06 不得命中）。
        agg_src = "const page = parseInt(req.query.page);\n" + \
                  "".join("// filler line %d\n" % i for i in range(20)) + \
                  "const stmt = db.prepare('SELECT MAX(id) AS n FROM items');\n" + \
                  "const row = stmt.get();\n" + "res.json({ page, row });\n"
        clamp_src = "const page = parseInt(req.query.page);\n" + \
                    "const safe = Math.max(1, Math.min(page, 100));\n" + \
                    "res.json({ safe });\n"
        agg_path = os.path.join(tmp, "agg.js")
        clamp_path = os.path.join(tmp, "clamp.js")
        with open(agg_path, "w", encoding="utf-8") as fh:
            fh.write(agg_src)
        with open(clamp_path, "w", encoding="utf-8") as fh:
            fh.write(clamp_src)

        found = scan(tmp)
        rids = {f["rule"] for f in found}
        for rid in ("QP-01", "QP-02", "QP-03", "QP-05", "QP-06", "QP-07", "QP-08"):
            if rid not in rids:
                failures.append("静态夹具未命中 " + rid)
        if not any(f["file"] == "bad.js" for f in found):
            failures.append("命中未归属到 bad.js")
        if any(f["file"] == "good.js" for f in found):
            failures.append("干净夹具误报")
        if not any(f["rule"] == "QP-06" and f["file"] == "agg.js" for f in found):
            failures.append("远处 MAX(id) 把 QP-06 静音（回归：应仍命中 agg.js）")
        if any(f["rule"] == "QP-06" and f["file"] == "clamp.js" for f in found):
            failures.append("近距离夹取被误报 QP-06（回归：clamp.js 应干净）")

        bad_gaps = {g["rule"] for g in matrix_check(bad_matrix)}
        for rid in ("QP-20", "QP-21", "QP-22", "QP-23", "QP-24", "QP-25",
                    "QP-26", "QP-27", "QP-28", "QP-29", "QP-30"):
            if rid not in bad_gaps:
                failures.append("清单夹具未命中 " + rid)
        good_gaps = matrix_check(good_matrix)
        if good_gaps:
            failures.append("干净清单误报：" + ",".join(g["rule"] for g in good_gaps))

        leakage = matrix_check({"sort": {"injection_status": 500,
                                         "injection_body": "syntax error near \"ORDER\""}})
        if not any(g["rule"] == "QP-25" and g["severity"] == "S1" for g in leakage):
            failures.append("SQL 回显未判 S1")

    if failures:
        print("SELFTEST FAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("SELFTEST GREEN: 静态 %d 条规则可命中夹具、清单 %d 条可命中假缺陷、干净夹具零误报" % (
        len({f["rule"] for f in found}), len(bad_gaps)))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R-19 查询语义与分页正确性审计")
    parser.add_argument("command", nargs="?", choices=["scan", "matrix", "cases", "self-test"],
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
            print(json.dumps({"rule": "R-19", "findings": items}, ensure_ascii=False, indent=2))
        else:
            print(fmt_markdown(items, "R-19 静态线索（启发式，需人工确认）"))
        if args.fail_on_gap:
            critical = [i for i in items if i["severity"] in ("CRITICAL", "S1")]
            return 1 if critical else 0
        return 0

    if args.command == "matrix":
        if not args.file or not os.path.isfile(args.file):
            print("matrix 需要 --file pagination.json", file=sys.stderr)
            return 2
        with open(args.file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        gaps = matrix_check(data)
        if args.format == "json":
            print(json.dumps({"rule": "R-19", "gaps": gaps}, ensure_ascii=False, indent=2))
        else:
            print(fmt_markdown(gaps, "R-19 清单缺口"))
        if args.fail_on_gap:
            return 1 if gaps else 0
        return 0

    print(CASES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
