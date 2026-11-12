#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""设备矩阵数据源汇总（project-tester v1.5.0）

把**本地导出**的 install-base 数据（CSV / JSON）汇总成设备矩阵草稿，
直接贴进 `assets/device-matrix-template.md`。落地 v1.4 提案区的
「设备矩阵与真实安装量数据源采集脚本」，但刻意保持诚实边界：

- **不联网、不调用任何 analytics API**（CrUX / GA / 自有埋点都只接受本地导出文件），
  因为各家 API 的字段与鉴权不同，臆造参数只会产出假证据。
- 脚本只算**占比与累计占比、80% 截断点、长尾补充位**；
  `real` / `emulator` / `simulator` / `browser-emulation` 载体与实测结论一律留空待人工填，
  **绝不替用户写「真机已验证」**。
- 固定输出数据源、时间窗、口径与局限声明；缺数据源就明确写「数据源未登记」。
- `--self-test` 用内置 CSV 验算占比、累计占比与 80% 截断点，算错即 exit 1。

输入 CSV 必需列（大小写不敏感，允许别名）：
  device, os, os_version, browser, engine, form_factor, installs
其中 `installs` 也可用 `sessions` / `users` / `count` / `install_base`。

用法：
  python scripts/device-matrix.py build --input <csv|json> --source "<数据源名>"
        --window "<时间窗>" [--min-coverage 0.8] [--format markdown|json] [--output <file>]
  python scripts/device-matrix.py --self-test
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FIELDS = {
    "device": ("device", "model", "机型", "设备"),
    "os": ("os", "platform", "操作系统"),
    "os_version": ("os_version", "osversion", "version", "系统版本"),
    "browser": ("browser", "浏览器"),
    "engine": ("engine", "browser_engine", "内核"),
    "form_factor": ("form_factor", "formfactor", "device_type", "形态"),
}
COUNT_FIELDS = ("installs", "sessions", "users", "count", "install_base", "安装量", "会话数")

LONG_TAIL = (
    "low-RAM Android（低配）",
    "oldest supported OS（最老受支持系统）",
    "vendor skin / 厂商定制 WebView",
    "foldable / tablet（折叠屏 / 平板）",
)

CRUX_CAVEAT = (
    "若数据源为 Chrome UX Report（CrUX）：只覆盖符合资格条件的**真实 Chrome 用户**，"
    "origin/page 需公开可发现且访问量足够才有数据；form factor 仅 phone/tablet/desktop 三值"
    "（由 User-Agent 推断），country 维度在 CrUX APIs 中不可用、ECT 维度已移除；"
    "**不能**据此推出机型、OS 版本或非 Chrome 内核的分布，也不能当作全量人群。"
)


def _pick(row: dict, names: tuple[str, ...]) -> str:
    lowered = {str(k).strip().lower(): str(v).strip() for k, v in row.items() if v is not None}
    for n in names:
        if n in lowered and lowered[n]:
            return lowered[n]
    return ""


def _count(row: dict) -> float:
    lowered = {str(k).strip().lower(): str(v).strip() for k, v in row.items() if v is not None}
    for n in COUNT_FIELDS:
        if n in lowered:
            try:
                return float(lowered[n].replace(",", ""))
            except ValueError:
                return 0.0
    return 0.0


def load_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw = raw.get("rows") or raw.get("data") or []
        if not isinstance(raw, list):
            raise ValueError("JSON 输入应为对象数组，或含 rows/data 数组的对象")
        rows = [dict(r) for r in raw]
    else:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError("输入文件没有数据行")
    return rows


def summarize(rows: list[dict], source: str, window: str, min_coverage: float) -> dict:
    items = []
    for r in rows:
        items.append({
            **{k: _pick(r, names) for k, names in FIELDS.items()},
            "count": _count(r),
        })
    total = sum(x["count"] for x in items)
    if total <= 0:
        raise ValueError("installs/sessions 合计为 0 或无法解析，拒绝生成矩阵（不臆造占比）")
    items.sort(key=lambda x: x["count"], reverse=True)

    cumulative = 0.0
    cutoff_index = None
    for i, x in enumerate(items):
        cumulative += x["count"]
        x["share"] = x["count"] / total
        x["cumulative"] = cumulative / total
        x["in_main"] = x["cumulative"] <= min_coverage + 1e-9
        if x["cumulative"] >= min_coverage and cutoff_index is None:
            cutoff_index = i
    # 若第一条就超过阈值，仍把第一条算进主干（不能出现 0 台主干）
    if cutoff_index is None:
        cutoff_index = len(items) - 1

    caveats = [
        f"数据源：{source or '**数据源未登记**'} ｜ 时间窗：{window or '**时间窗未登记**'}",
        f"口径：按 installs/sessions 占比计算，合计 {total:,.0f}；**不是全量人群**，也不代表机型/OS 版本分布",
        "载体列（real / emulator / simulator / browser-emulation）与实测结论**由人工填写**，脚本不代填、不冒充真机证据",
        f"主干为累计占比达到 {min_coverage:.0%} 的最小前缀（第 {cutoff_index + 1} 条截断），其余为长尾需逐条给结论或显式「未覆盖」",
        CRUX_CAVEAT,
    ]
    return {
        "source": source, "window": window, "min_coverage": min_coverage,
        "total": total, "cutoff_index": cutoff_index,
        "covered_at_cutoff": items[cutoff_index]["cumulative"],
        "rows": items, "long_tail_suggestions": list(LONG_TAIL), "caveats": caveats,
    }


def to_markdown(res: dict) -> str:
    pct = min_coverage = res["min_coverage"]
    out = ["# 设备矩阵草稿（install-base 数据源驱动）", "",
           f"- 数据源：{res['source'] or '**未登记**'} ｜ 时间窗：{res['window'] or '**未登记**'}",
           f"- 样本合计：{res['total']:,.0f} ｜ 主干阈值：{pct:.0%} ｜ 截断点：第 {res['cutoff_index'] + 1} 条（累计 {res['covered_at_cutoff']:.1%}）",
           "", "| # | 设备/机型 | OS / 版本 | 浏览器 / 内核 | 形态 | 安装量 | 占比 | 累计 | 主干/长尾 | 载体（待填） | 实测结论（待填） |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(res["rows"], 1):
        osv = " / ".join(x for x in (r["os"], r["os_version"]) if x) or "—"
        be = " / ".join(x for x in (r["browser"], r["engine"]) if x) or "—"
        tag = "主干" if r["in_main"] else "长尾"
        out.append(f"| {i} | {r['device'] or '—'} | {osv} | {be} | {r['form_factor'] or '—'} | "
                   f"{r['count']:,.0f} | {r['share']:.1%} | {r['cumulative']:.1%} | {tag} | "
                   f"`待测` | `未填` |")
    out += ["", "## 强制补充的长尾高危条目（占比小但出事多）", ""]
    for t in res["long_tail_suggestions"]:
        out.append(f"- [ ] {t} —— 逐条写结论或显式「未覆盖」")
    out += ["", "## 口径与局限声明（报告必须保留）", ""]
    out += [f"- {c}" for c in res["caveats"]]
    out += ["", "> 本表只是**占比计算的草稿**：矩阵来源真实性、载体标注、多内核与真机证据仍按 "
            "`references/cross-platform-testing.md` 与 `assets/device-matrix-template.md` 人工补齐（R-8）。"]
    return "\n".join(out) + "\n"


def self_test() -> int:
    """占比 / 累计 / 80% 截断点验算 + 诚实边界检查，算错即 exit 1。"""
    csv_text = (
        "device,os,os_version,browser,engine,form_factor,installs\n"
        "A,Android,14,Chrome,Chromium,phone,50\n"
        "B,iOS,17,Safari,WebKit,phone,30\n"
        "C,Windows,11,Chrome,Chromium,desktop,15\n"
        "D,macOS,14,Firefox,Gecko,desktop,5\n"
    )
    import tempfile
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "install.csv"
        p.write_text(csv_text, encoding="utf-8")
        res = summarize(load_rows(p), "本地导出 fixture", "2026-10-01..2026-10-31", 0.8)
        if abs(res["total"] - 100) > 1e-9:
            failures.append(f"合计应为 100，实际 {res['total']}")
        if abs(res["rows"][0]["share"] - 0.5) > 1e-9:
            failures.append(f"第一条占比应为 50%，实际 {res['rows'][0]['share']}")
        if abs(res["rows"][2]["cumulative"] - 0.95) > 1e-9:
            failures.append(f"第三条累计应为 95%，实际 {res['rows'][2]['cumulative']}")
        # 50+30 = 80% 已达标，截断点应为第 2 条（index 1）
        if res["cutoff_index"] != 1:
            failures.append(f"80% 截断点应为第 2 条，实际第 {res['cutoff_index'] + 1} 条")
        md = to_markdown(res)
        for needle in ("数据源", "时间窗", "待测", "未覆盖", "CrUX", "不代填"):
            if needle not in md:
                failures.append(f"导出缺少诚实口径声明: {needle}")
        if "真机已验证" in md:
            failures.append("导出出现了脚本不该写的「真机已验证」冒充语")

        # 无数据源 / 空数据必须显式报错，而不是编造
        no_source = summarize(load_rows(p), "", "", 0.8)
        if "**数据源未登记**" not in to_markdown(no_source):
            failures.append("缺数据源时未显式标注")
        empty = Path(tmp) / "empty.csv"
        empty.write_text("device,installs\n", encoding="utf-8")
        try:
            summarize(load_rows(empty), "x", "y", 0.8)
            failures.append("空数据未报错（会产出假矩阵）")
        except ValueError:
            pass

    if failures:
        for f in failures:
            print(f"[SELFTEST FAIL] {f}")
        print("结论：SELFTEST BLOCKED —— 矩阵脚本不可信，禁止用于交付。")
        return 1
    print("[SELFTEST PASS] 合计/占比/累计/80% 截断点正确；缺数据源与空数据被显式拦截；未冒充真机证据")
    print("结论：SELFTEST GREEN —— 设备矩阵脚本可证伪。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="设备矩阵数据源汇总（project-tester v1.5）")
    ap.add_argument("--self-test", action="store_true", help="运行占比与口径自检")
    sub = ap.add_subparsers(dest="cmd")
    b = sub.add_parser("build", help="从本地 CSV/JSON 生成矩阵草稿")
    b.add_argument("--input", required=True)
    b.add_argument("--source", default="", help="数据源名称（如「CrUX BigQuery 导出 2026-10」）")
    b.add_argument("--window", default="", help="数据时间窗")
    b.add_argument("--min-coverage", type=float, default=0.8)
    b.add_argument("--format", choices=("markdown", "json"), default="markdown")
    b.add_argument("--output", default=None, help="显式给出才写文件；默认只打印")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.cmd != "build":
        ap.print_help()
        return 0
    if not 0 < args.min_coverage <= 1:
        print("ERROR: --min-coverage 必须在 (0, 1] 区间")
        return 1
    try:
        res = summarize(load_rows(Path(args.input)), args.source, args.window, args.min_coverage)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    text = json.dumps(res, ensure_ascii=False, indent=2) if args.format == "json" else to_markdown(res)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"已写入矩阵草稿：{args.output}")
    else:
        print(text)
    if not args.source or not args.window:
        print("提示：数据源或时间窗未登记 → 该矩阵**不得**作为 R-8 的矩阵来源证据")
    return 0


if __name__ == "__main__":
    sys.exit(main())
