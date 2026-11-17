#!/usr/bin/env python3
"""metric-audit.py — 指标口径与报表可信审计（R-22）

用法:
  python scripts/metric-audit.py scan <路径> [--format markdown|json] [--fail-on-gap]
  python scripts/metric-audit.py check --file metrics.json [--format markdown|json]
                                      [--fail-on-gap] [--max-freshness 60]
  python scripts/metric-audit.py cases
  python scripts/metric-audit.py --self-test

静态规则（scan，逐行启发式）:
  MA-01 HIGH      COUNT(*) 所在语句无 WHERE（软删/测试单/退款行全部计入）
  MA-02 HIGH      对已聚合值再求平均（AVG(AVG(...)) / mean(means)）
  MA-03 HIGH      BETWEEN '23:59:59' 或 date_trunc 未声明时区（跨日边界丢单）
  MA-04 HIGH      count(user_id) 等唯一实体口径缺少 DISTINCT
  MA-05 MEDIUM    金额 SUM 走 float/double/parseFloat（尾差与舍入漂移）
  MA-06 MEDIUM    指标响应未见 as_of/updated_at（看板无法判断新鲜度）
  MA-07 HIGH      转化率用 count(*) 做分母，分子却是 sum(case ...)（口径不一致）
  MA-08 HIGH      读 orders/events/sessions 却无 is_test/bot/internal 过滤
  MA-09 MEDIUM    SELECT * 后在应用层过滤（分母漂移、口径不可复现）
  MA-10 HIGH      做显著性检验却未做 SRM 检查（分配异常会伪装成效果）

核对规则（check，读取 metrics.json；recon 指 dashboard / API / 源表三处对账）:
  MA-20 HIGH      指标定义卡缺字段（numerator/denominator/timezone/dedupe_key）
  MA-21 HIGH      dashboard 与源表相对差超过 tolerance_pct
  MA-22 MEDIUM    数据新鲜度超过 --max-freshness 分钟
  MA-23 HIGH      分子 > 分母（比率 > 100%，口径或过滤条件写反）
  MA-24 HIGH      SRM 卡方 p < 0.001（分流比例异常，实验结论不可用）
  MA-25 MEDIUM    单组样本量 < 1000（样本不足，指标波动无法归因）
  MA-26 MEDIUM    转化数 > 访问数（分子分母来自不同人群）

输入契约:
  {"metrics":[{"name":"paid_orders","numerator":"status='paid'",
               "denominator":"created_at in [start,end)","dashboard":1234,"source":1301,
               "tolerance_pct":0.5,"timezone":"Asia/Shanghai","dedupe_key":"order_id",
               "freshness_minutes":90,"numerator_value":1234,"denominator_value":1301}],
   "srm":[{"experiment":"exp-1","control":{"visitors":5000,"conversions":250},
           "treatment":{"visitors":5100,"conversions":280}}]}

口径:
  相对差 = |dashboard − source| / source × 100%；source=0 且 dashboard≠0 直接判超差。
  SRM: 期望 = 两组总量 / 2，χ² = Σ(O−E)²/E，df=1，p = erfc(sqrt(χ²/2))；
  p < 0.001 视为分流异常；p 不是「效果显著」，只回答「分流是否坏了」。

诚实边界:
  - 不联网：只读本地文件与本地 JSON，不连数据库、不调 BI API。
  - 不代填：dashboard/source/样本量必须来自真实查询或导出；脚本只做算术与比较。
  - 不证明：scan 命中是「需人工确认的线索」；check 通过只代表给定数字自洽，
    不代表口径正确、不代表业务结论成立；SRM 通过也不证明实验有效。
  - 不替代数据血缘：脚本不知道表之间的真实关系，口径冲突必须回到定义卡与源表核对。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile

SKIP_DIRS = {
    ".git", "node_modules", ".workbuddy-ai", ".test-memory", "dist", "build",
    ".venv", "venv", "__pycache__", ".next", "target", ".idea", "coverage",
}
SKIP_FILES = {"metric-audit.py"}
CODE_SUFFIXES = (
    ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".py", ".php", ".rb", ".java",
    ".kt", ".go", ".cs", ".sql", ".rs", ".vue", ".svelte",
)

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


def scan(root: str) -> list[dict]:
    findings: list[dict] = []
    for path in iter_files(root):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except OSError:
            continue
        rel = os.path.relpath(path, root)
        text = "\n".join(lines)
        low_all = text.lower()
        is_metric = bool(re.search(r"metric|dashboard|report|analytics|kpi|指标|看板|报表", low_all))
        has_where = "where" in low_all
        has_test_filter = bool(re.search(r"is_test|test_order|is_internal|internal_user|\bbot\b|exclude", low_all))
        has_freshness = bool(re.search(r"as_of|updated_at|last_updated|freshness|generated_at", low_all))
        seen_once: set[str] = set()

        def add(rid: str, sev: str, idx: int, reason: str) -> None:
            findings.append({
                "rule": rid, "severity": sev, "file": rel, "line": idx,
                "reason": reason, "excerpt": lines[idx - 1].strip()[:160] if idx else "",
            })

        for idx, line in enumerate(lines, 1):
            low = line.lower()
            window = " ".join(lines[max(0, idx - 1):idx + 1]).lower()

            # MA-01 COUNT(*) 无 WHERE
            if "count(*)" in low and "where" not in window:
                add("MA-01", "HIGH", idx, "COUNT(*) 语句无 WHERE，软删/测试/退款行会全部计入")

            # MA-02 平均的平均
            if re.search(r"avg\s*\(\s*(?:[\w.]*\.)?avg|mean\s*\([^)]*mean\s*\(|average\s*\(\s*avg", low):
                add("MA-02", "HIGH", idx, "对已聚合值再求平均，结果不可加且随分组粒度变化")

            # MA-03 日期边界/时区
            if ("between" in low and "23:59:59" in low) \
                    or (re.search(r"date_trunc\s*\(\s*['\"]day", low) and not re.search(r"asia/|utc|timezone|at time zone", window)):
                add("MA-03", "HIGH", idx, "日期边界用 23:59:59 或 date_trunc 未声明时区，跨日/夏令时会丢单")

            # MA-04 唯一实体缺 DISTINCT
            if re.search(r"count\s*\(\s*(?!distinct\b)[\w.]*(?:user_id|visitor_id|customer_id|session_id|device_id)", low):
                add("MA-04", "HIGH", idx, "按唯一实体计数却无 COUNT(DISTINCT ...)，一对多会重复计数")

            # MA-05 金额浮点
            if re.search(r"sum\s*\([^)]*(?:amount|price|revenue|gmv|fee)", low) \
                    and re.search(r"::float|::double|cast\s*\([^)]*float|\bfloat\b|double precision|parsefloat", low):
                add("MA-05", "MEDIUM", idx, "金额 SUM 走 float/double，尾差与舍入会在对账时暴露")

            # MA-07 转化率分母口径
            if re.search(r"/\s*count\s*\(\s*\*\s*\)", low) \
                    and re.search(r"sum\s*\(\s*case|purchase|conversion|checkout|order", low):
                add("MA-07", "HIGH", idx, "转化率分母用 COUNT(*)，与分子 sum(case ...) 的人群不一致")

            # MA-09 SELECT * 后应用层过滤
            if re.search(r"select\s+\*", low) and is_metric:
                add("MA-09", "MEDIUM", idx, "SELECT * 后在应用层过滤，分母人群无法在 SQL 层复现")

            # MA-10 显著性检验但无 SRM
            if re.search(r"p_value|p-value|\bttest\b|t_test|z_test|significance|显著性", low) \
                    and "MA-10" not in seen_once \
                    and not re.search(r"\bsrm\b|sample_ratio|chi2|chi_square|mismatch", low_all):
                seen_once.add("MA-10")
                add("MA-10", "HIGH", idx, "做显著性检验但全文件无 SRM 检查，分配异常会被读成效果")

        # 文件级规则也要落到真实命中的那一行，不能一律报 line 1
        def line_of(pattern: str) -> int:
            rx = re.compile(pattern)
            for i, ln in enumerate(lines, 1):
                if rx.search(ln.lower()):
                    return i
            return 0

        is_client = bool(re.search(r"\bfetch\(", low_all)) \
            and not re.search(r"createserver|\.listen\(|express\(\)|fastapi|flask", low_all)

        # MA-06 指标响应无新鲜度（文件级，仅对服务端响应代码生效，排除前端调用方）
        if is_metric and not is_client and (re.search(r"res\.json|jsonify|response\.json|render\(", low_all)
                                            and not has_freshness):
            idx = line_of(r"res\.json|jsonify|response\.json|render\(")
            add("MA-06", "MEDIUM", idx, "指标响应未见 as_of/updated_at，看板无法判断数据新鲜度")

        # MA-08 无测试/机器人过滤（文件级）
        if re.search(r"from\s+(orders|events|sessions|payments|transactions)\b", low_all) \
                and has_where and not has_test_filter:
            idx = line_of(r"from\s+(orders|events|sessions|payments|transactions)\b")
            add("MA-08", "HIGH", idx, "读取业务表却无 is_test/bot/internal 过滤，测试单会污染指标")

    findings.sort(key=lambda f: (SEV_ORDER.get(f["severity"], 9), f["rule"], f["file"], f["line"]))
    return findings


def srm_pvalue(control: int, treatment: int) -> float:
    total = control + treatment
    if total <= 0:
        return 1.0
    expected = total / 2.0
    chi2 = ((control - expected) ** 2) / expected + ((treatment - expected) ** 2) / expected
    return math.erfc(math.sqrt(chi2 / 2.0))


def check(data: dict, max_freshness: int = 60) -> dict:
    gaps: list[dict] = []
    metrics: list[dict] = []
    srm_rows: list[dict] = []

    def gap(rid: str, sev: str, reason: str) -> None:
        gaps.append({"rule": rid, "severity": sev, "reason": reason})

    for m in data.get("metrics") or []:
        name = str(m.get("name") or "unnamed")
        row = {"name": name}
        missing = [k for k in ("numerator", "denominator", "timezone", "dedupe_key")
                   if not str(m.get(k) or "").strip()]
        if missing:
            gap("MA-20", "HIGH", "%s 定义卡缺 %s" % (name, ",".join(missing)))

        dash = m.get("dashboard")
        src = m.get("source")
        tol = float(m.get("tolerance_pct") or 0.0)
        if dash is not None and src is not None:
            dashboard, source = float(dash), float(src)
            if source == 0:
                rel = 0.0 if dashboard == 0 else 100.0
            else:
                rel = abs(dashboard - source) / abs(source) * 100.0
            row.update({"dashboard": dashboard, "source": source,
                        "rel_diff_pct": round(rel, 4), "tolerance_pct": tol})
            if rel > tol:
                gap("MA-21", "HIGH", "%s 对账超差：dashboard=%.2f source=%.2f 相对差=%.3f%% > %.2f%%" % (
                    name, dashboard, source, rel, tol))
        else:
            row["rel_diff_pct"] = None

        fresh = m.get("freshness_minutes")
        if fresh is not None:
            row["freshness_minutes"] = float(fresh)
            if float(fresh) > max_freshness:
                gap("MA-22", "MEDIUM", "%s 新鲜度 %.0f 分钟 > %d 分钟" % (name, float(fresh), max_freshness))

        num_v, den_v = m.get("numerator_value"), m.get("denominator_value")
        if num_v is not None and den_v is not None:
            nv, dv = float(num_v), float(den_v)
            row.update({"numerator_value": nv, "denominator_value": dv})
            if nv > dv:
                gap("MA-23", "HIGH", "%s 分子 %.2f > 分母 %.2f，比率超过 100%%" % (name, nv, dv))

        metrics.append(row)

    for e in data.get("srm") or []:
        exp_name = str(e.get("experiment") or "unnamed")
        c = e.get("control") or {}
        t = e.get("treatment") or {}
        cv, tv = int(c.get("visitors") or 0), int(t.get("visitors") or 0)
        cc, tc = int(c.get("conversions") or 0), int(t.get("conversions") or 0)
        p = srm_pvalue(cv, tv)
        total = cv + tv
        expected = total / 2.0
        chi2 = 0.0 if total <= 0 else ((cv - expected) ** 2) / expected + ((tv - expected) ** 2) / expected
        row = {"experiment": exp_name, "control_visitors": cv, "treatment_visitors": tv,
               "control_conversions": cc, "treatment_conversions": tc,
               "chi2": round(chi2, 4), "p_value": float("%.3e" % p)}
        srm_rows.append(row)
        if p < 0.001:
            gap("MA-24", "HIGH", "%s SRM 卡方 p=%.3e < 0.001（分流比例异常）" % (exp_name, p))
        if min(cv, tv) < 1000:
            gap("MA-25", "MEDIUM", "%s 单组样本量 %d/%d < 1000" % (exp_name, cv, tv))
        if cc > cv or tc > tv:
            gap("MA-26", "MEDIUM", "%s 转化数 > 访问数（%d/%d, %d/%d）" % (exp_name, cc, cv, tc, tv))

    return {"rule": "R-22", "metrics": metrics, "srm": srm_rows, "gaps": gaps}


def fmt_findings(items: list[dict], title: str) -> str:
    lines = [f"### {title}", "", "| 规则 | 级别 | 位置 | 说明 |", "|---|---|---|---|"]
    for it in items:
        loc = it.get("file", "")
        if it.get("line"):
            loc = f"{loc}:{it['line']}"
        lines.append("| %s | %s | %s | %s |" % (
            it["rule"], it["severity"], loc, (it.get("reason") or "").replace("|", "\\|")))
    if not items:
        lines.append("| — | — | — | 未命中已知模式（不等于已证明口径正确） |")
    return "\n".join(lines)


def fmt_check(result: dict) -> str:
    lines = ["### R-22 指标对账", "",
             "| 指标 | dashboard | 源表 | 相对差 | 容差 | 新鲜度(min) |",
             "|---|---|---|---|---|---|"]
    for r in result["metrics"]:
        lines.append("| %s | %s | %s | %s | %s | %s |" % (
            r["name"], r.get("dashboard", "-"), r.get("source", "-"),
            "-" if r.get("rel_diff_pct") is None else "%.3f%%" % r["rel_diff_pct"],
            "-" if r.get("tolerance_pct") is None else "%.2f%%" % r["tolerance_pct"],
            "-" if r.get("freshness_minutes") is None else "%.0f" % r["freshness_minutes"]))
    if result["srm"]:
        lines += ["", "### A/B 分流检查（SRM）", "",
                  "| 实验 | 对照 n / 转化 | 实验 n / 转化 | p | 结论 |", "|---|---|---|---|---|"]
        for r in result["srm"]:
            verdict = "样本比例异常" if r["p_value"] < 0.001 else "未发现异常"
            lines.append("| %s | %d / %d | %d / %d | %.3e | %s |" % (
                r["experiment"], r["control_visitors"], r["control_conversions"],
                r["treatment_visitors"], r["treatment_conversions"], r["p_value"], verdict))
    lines += ["", fmt_findings(result["gaps"], "R-22 缺口")]
    return "\n".join(lines)


CASES = """# R-22 指标可信要点速查（自测/汇报用）

## 1. 定义卡必须能回答的 6 个问题
分子怎么过滤？分母是谁？时间窗与时区？按什么去重？排除哪些流量？多久更新？
答不上来的指标，先别上看板。

## 2. 对账的最小闭环
dashboard 数字 -> 同一口径的 API -> 源表 SQL。三处差异 >0.5% 时必须归因：
口径不同 / 任务迟到 / 去重不同 / 时区 / 缓存 / 抽样。只对两个页面不算对账。

## 3. 三个常见「凭空多出来」的订单
- 支付回调重试：同一 order_id 计了两次（缺 DISTINCT / 幂等键）；
- 跨日：UTC 23:30 的订单在 Asia/Shanghai 属于次日；
- 右边闭合：BETWEEN '2026-11-01' AND '2026-11-07' 实际包含 11-07 00:00:00，
  区间口径应写 [start, end)。

## 4. 不可加指标
AVG、比率、分位数、留存率都不能跨分组直接平均；「平均的平均」在分组样本不等时必错。
分位数更不能把各桶 p95 再平均。

## 5. SRM 的读法
期望 = 两组总量/2，χ² = Σ(O−E)²/E，df=1，p<0.001 先停实验查分流；
p 大不等于实验有效，只说明分流没坏。单组 <1000 时先谈样本量，别谈显著性。

## 6. 新鲜度与重述
事件延迟 p95 是多少？T+1 backfill 后昨日数字变了多少？看板上的 as_of 是数据时间
还是渲染时间？没有 as_of 的看板只能写「截至采集时刻」。
"""


def self_test() -> int:
    bad_src = """\
-- 中文注释：订单指标（故意植入缺陷）
SELECT count(*) AS orders FROM orders;
SELECT avg(t.avg_amount) AS a FROM (SELECT avg(amount) AS avg_amount FROM orders GROUP BY shop) t;
SELECT count(*) FROM orders WHERE created_at BETWEEN '2026-11-01' AND '2026-11-07 23:59:59';
SELECT count(user_id) AS dau FROM events;
SELECT sum(amount::float) AS gmv FROM payments;
SELECT sum(CASE WHEN event = 'purchase' THEN 1 ELSE 0 END) / count(*) AS cvr FROM events;
SELECT * FROM events WHERE country = 'CN';
SELECT p_value FROM ab_test WHERE experiment = 'exp-1';
res.json({ orders: 1234 });
"""
    good_src = """\
-- 中文注释：订单指标（干净版本）
SELECT count(DISTINCT order_id) AS paid_orders FROM orders
 WHERE status = 'paid' AND deleted_at IS NULL AND is_test = false
   AND created_at >= '2026-11-01' AND created_at < '2026-11-08';
SELECT date_trunc('day', created_at AT TIME ZONE 'Asia/Shanghai') AS d,
       sum(amount) AS gmv
  FROM payments WHERE is_test = false GROUP BY 1;
SELECT count(DISTINCT user_id) AS dau FROM events
 WHERE is_test = false AND user_agent NOT LIKE '%bot%';
-- 响应带 as_of 与 SRM 字段
res.json({ metrics: gmv, as_of: new Date().toISOString(), srm_p: 0.42 });
"""
    bad_metrics = {
        "metrics": [
            {"name": "paid_orders", "numerator": "status='paid'", "denominator": "",
             "dashboard": 1234, "source": 1301, "tolerance_pct": 0.5,
             "freshness_minutes": 240, "numerator_value": 300, "denominator_value": 200},
            {"name": "gmv", "numerator": "sum(amount)", "denominator": "orders",
             "timezone": "Asia/Shanghai", "dedupe_key": "order_id",
             "dashboard": 500, "source": 0, "tolerance_pct": 1.0, "freshness_minutes": 30},
        ],
        "srm": [
            {"experiment": "exp-bad", "control": {"visitors": 5000, "conversions": 250},
             "treatment": {"visitors": 6000, "conversions": 280}},
            {"experiment": "exp-small", "control": {"visitors": 500, "conversions": 40},
             "treatment": {"visitors": 500, "conversions": 45}},
            {"experiment": "exp-over", "control": {"visitors": 100, "conversions": 120},
             "treatment": {"visitors": 100, "conversions": 90}},
        ],
    }
    good_metrics = {
        "metrics": [
            {"name": "paid_orders", "numerator": "status='paid'", "denominator": "created_at in [start,end)",
             "dashboard": 1000, "source": 1002, "tolerance_pct": 1.0,
             "timezone": "Asia/Shanghai", "dedupe_key": "order_id",
             "freshness_minutes": 30, "numerator_value": 200, "denominator_value": 2000},
        ],
        "srm": [
            {"experiment": "exp-ok", "control": {"visitors": 5000, "conversions": 250},
             "treatment": {"visitors": 5050, "conversions": 260}},
        ],
    }

    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="maudit-") as tmp:
        bad_path = os.path.join(tmp, "bad.sql")
        good_path = os.path.join(tmp, "good.sql")
        with open(bad_path, "w", encoding="utf-8") as fh:
            fh.write(bad_src)
        with open(good_path, "w", encoding="utf-8") as fh:
            fh.write(good_src)

        found = scan(tmp)
        rids = {f["rule"] for f in found}
        for rid in ("MA-01", "MA-02", "MA-03", "MA-04", "MA-05", "MA-06",
                    "MA-07", "MA-08", "MA-09", "MA-10"):
            if rid not in rids:
                failures.append("静态夹具未命中 " + rid)
        bad_on_good = sorted({f["rule"] for f in found if f["file"] == "good.sql"})
        if bad_on_good:
            failures.append("干净夹具误报：" + ",".join(bad_on_good))

        bad = check(bad_metrics)
        bad_rids = {g["rule"] for g in bad["gaps"]}
        for rid in ("MA-20", "MA-21", "MA-22", "MA-23", "MA-24", "MA-25", "MA-26"):
            if rid not in bad_rids:
                failures.append("核对夹具未命中 " + rid)
        if bad["srm"][0]["p_value"] >= 0.001:
            failures.append("5000 vs 6000 的 SRM p 应 <0.001，实得 %s" % bad["srm"][0]["p_value"])
        if check(good_metrics)["gaps"]:
            failures.append("干净指标误报：" + ",".join(
                g["rule"] for g in check(good_metrics)["gaps"]))
        p_ok = srm_pvalue(5000, 5050)
        if not 0.4 < p_ok < 0.8:
            failures.append("5000 vs 5050 的 SRM p 应接近 0.62，实得 %.4f" % p_ok)

    if failures:
        print("SELFTEST FAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("SELFTEST GREEN: 静态 10 条规则可命中夹具、干净夹具零误报、%d 条核对规则可复现、"
          "SRM 卡方 p 与手算一致" % len(bad_rids))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R-22 指标口径与报表可信审计")
    parser.add_argument("command", nargs="?", choices=["scan", "check", "cases", "self-test"],
                        default="cases")
    parser.add_argument("target", nargs="?", default=".")
    parser.add_argument("--file", dest="file", default=None)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--fail-on-gap", action="store_true")
    parser.add_argument("--max-freshness", type=int, default=60)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test or args.command == "self-test":
        return self_test()

    if args.command == "scan":
        items = scan(args.target)
        if args.format == "json":
            print(json.dumps({"rule": "R-22", "findings": items}, ensure_ascii=False, indent=2))
        else:
            print(fmt_findings(items, "R-22 静态线索（启发式，需人工确认）"))
        if args.fail_on_gap:
            return 1 if any(i["severity"] in ("CRITICAL", "S1") for i in items) else 0
        return 0

    if args.command == "check":
        if not args.file or not os.path.isfile(args.file):
            print("check 需要 --file metrics.json", file=sys.stderr)
            return 2
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print("读取失败：%s" % exc, file=sys.stderr)
            return 2
        result = check(data, max_freshness=args.max_freshness)
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(fmt_check(result))
        if args.fail_on_gap:
            return 1 if result["gaps"] else 0
        return 0

    print(CASES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
