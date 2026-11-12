#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据链自动对账 / 审计导出（project-tester v1.5.0）

把测试报告里的「声称 / 规则结论」与证据文件、原始输出锚点、被测对象
commit 绑定起来，做**本地确定性**对账，并导出可交付的审计表。

设计约束（与 `references/self-evolution.md` §5 一致）：
- 只用标准库；不联网；不修改任何被测文件或证据文件（除非显式 --output）。
- 输入是显式的 JSON manifest，不猜测目录结构、不臆造证据。
- 所有检查必须可证伪：`--self-test` 故意制造 5 种缺陷并确认能检出，
  漏检任何一种即退出码 1。

manifest 格式（字段全为可选，缺什么就报什么）：
{
  "subject": {
    "name": "api-service",
    "commit": "abc123",
    "environment": "win32 / Python 3.13",
    "window": "2026-11-12T09:00+08:00 ~ 2026-11-12T11:00+08:00"
  },
  "claims": [
    {
      "id": "R-3",
      "statement": "制品可信",
      "status": "PASS | FAIL | 待确认 | 不适用 | BLOCKED",
      "evidence": "runs/2026-11-12-1.log",
      "anchor": "L12",            // L<n> 行号 或 text:<原文片段>
      "subject_commit": "abc123", // 证据采集时的被测对象 commit
      "conclusion_class": "运行时质量"  // 静态记录/评测准备度/运行时质量/发布批准
    }
  ],
  "control_mapping": [
    {"control": "SSDF PS.3.2 provenance", "claim_ids": ["R-3"], "status": "mapped"}
  ]
}

用法：
  python scripts/evidence-audit.py audit --manifest <path> [--root <dir>]
        [--format json|markdown] [--output <file>] [--fail-on-gap]
  python scripts/evidence-audit.py --self-test
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BLOCK = "BLOCK"
WARN = "WARN"
CLASSES = ("静态记录", "评测准备度", "运行时质量", "发布批准")
PASS_STATUSES = ("PASS", "通过", "PASS/FAIL: PASS")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check_anchor(path: Path, anchor: str) -> tuple[bool, str]:
    """锚点必须可解析：L<n> 行号存在，或 text: 片段确实出现在文件里。"""
    if not anchor:
        return False, "锚点为空"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return False, f"证据文件不可读: {exc}"
    if re.fullmatch(r"L\d+", anchor.strip()):
        n = int(anchor.strip()[1:])
        if n < 1 or n > len(lines):
            return False, f"锚点 {anchor} 超出文件行数 {len(lines)}"
        return True, lines[n - 1].strip()[:200]
    if anchor.startswith("text:"):
        needle = anchor[5:]
        if not needle:
            return False, "text: 锚点片段为空"
        for i, line in enumerate(lines, 1):
            if needle in line:
                return True, f"L{i}: {line.strip()[:200]}"
        return False, f"text: 片段未出现在证据文件中: {needle[:40]}"
    return False, f"未知锚点格式（支持 L<n> / text:<片段>）: {anchor}"


def audit_manifest(manifest_path: Path, root: Path | None = None) -> dict:
    """只做确定性检查，返回结构化对账结果。不写文件、不联网。"""
    findings: list[dict] = []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "manifest": str(manifest_path),
            "findings": [{"severity": BLOCK, "code": "manifest_unreadable",
                          "claim": "-", "detail": str(exc)}],
            "counts": {"claims": 0, "block": 1, "warn": 0},
            "claims": [],
        }

    base = root or manifest_path.parent
    subject = data.get("subject") or {}
    subject_commit = str(subject.get("commit") or "")
    if not subject_commit:
        findings.append({"severity": BLOCK, "code": "missing_subject_binding",
                         "claim": "-", "detail": "subject.commit 缺失，无法判断证据是否过期"})

    claims = data.get("claims") or []
    report_rows: list[dict] = []
    for idx, claim in enumerate(claims):
        cid = str(claim.get("id") or f"#{idx + 1}")
        status = str(claim.get("status") or "")
        statement = str(claim.get("statement") or "")
        is_pass = status.upper() in {s.upper() for s in PASS_STATUSES}
        row = {
            "id": cid, "statement": statement, "status": status,
            "evidence": str(claim.get("evidence") or ""),
            "anchor": str(claim.get("anchor") or ""),
            "subject_commit": str(claim.get("subject_commit") or ""),
            "conclusion_class": str(claim.get("conclusion_class") or ""),
            "sha256": "", "anchor_excerpt": "", "verdict": "",
        }

        ev = claim.get("evidence")
        if not ev:
            sev = BLOCK if is_pass else WARN
            findings.append({"severity": sev, "code": "pass_without_proof" if is_pass else "missing_evidence",
                             "claim": cid,
                             "detail": "状态为 PASS 却未登记证据文件" if is_pass else "未登记证据文件"})
        else:
            ep = Path(str(ev))
            if not ep.is_absolute():
                ep = base / ep
            if not ep.is_file():
                findings.append({"severity": BLOCK, "code": "dangling_reference",
                                 "claim": cid, "detail": f"证据文件不存在: {ev}"})
            else:
                row["sha256"] = sha256(ep)
                ok_anchor, excerpt = check_anchor(ep, row["anchor"])
                if not ok_anchor:
                    findings.append({"severity": BLOCK, "code": "unresolvable_anchor",
                                     "claim": cid, "detail": excerpt})
                else:
                    row["anchor_excerpt"] = excerpt

        if subject_commit and row["subject_commit"] and row["subject_commit"] != subject_commit:
            findings.append({"severity": BLOCK, "code": "stale_evidence",
                             "claim": cid,
                             "detail": f"证据采集于 commit {row['subject_commit']}，当前 {subject_commit}"})
        elif subject_commit and not row["subject_commit"] and is_pass:
            findings.append({"severity": BLOCK, "code": "missing_subject_binding",
                             "claim": cid, "detail": "PASS 结论缺少 subject_commit 绑定"})

        if row["conclusion_class"] not in CLASSES:
            findings.append({"severity": WARN, "code": "unclassified_conclusion",
                             "claim": cid,
                             "detail": f"结论类型应为 {'/'.join(CLASSES)}，实际 '{row['conclusion_class']}'"})

        blocking = [f for f in findings if f["claim"] == cid and f["severity"] == BLOCK]
        if is_pass and blocking:
            row["verdict"] = "作废 → 待确认（PASS 无有效证据链）"
        elif blocking:
            row["verdict"] = "证据链缺口"
        elif row["status"] in ("不适用", "BLOCKED", "待确认"):
            row["verdict"] = row["status"]
        else:
            row["verdict"] = "证据链可解析"
        report_rows.append(row)

    # 合规声明 ↔ 控制项 ↔ 证据 的对账：只统计，不冒充「已合规」
    mapped_ids = {str(c.get("id")) for c in claims}
    controls = data.get("control_mapping") or []
    control_rows = []
    for c in controls:
        ids = [str(x) for x in (c.get("claim_ids") or [])]
        missing = [x for x in ids if x not in mapped_ids]
        control_rows.append({
            "control": str(c.get("control") or ""),
            "claim_ids": ids,
            "status": str(c.get("status") or ""),
            "missing_claims": missing,
        })
        if missing:
            findings.append({"severity": BLOCK, "code": "unmapped_control",
                             "claim": str(c.get("control") or ""),
                             "detail": f"控制项指向未登记的结论: {', '.join(missing)}"})
    for cid in sorted(mapped_ids):
        if not any(cid in cr["claim_ids"] for cr in control_rows) and controls:
            findings.append({"severity": WARN, "code": "unmapped_claim",
                             "claim": cid, "detail": "该结论未映射到任何合规控制项（可接受，但须声明）"})

    block = sum(1 for f in findings if f["severity"] == BLOCK)
    warn = sum(1 for f in findings if f["severity"] == WARN)
    return {
        "ok": block == 0,
        "manifest": str(manifest_path),
        "subject": subject,
        "findings": findings,
        "counts": {"claims": len(claims), "controls": len(controls), "block": block, "warn": warn},
        "claims": report_rows,
        "controls": control_rows,
    }


def to_markdown(result: dict) -> str:
    out = ["# 证据链对账 / 审计导出", "",
           f"- manifest：`{result['manifest']}`",
           f"- 被测对象：{result.get('subject', {}).get('name', '(未填)')} ｜ commit：{result.get('subject', {}).get('commit', '(未填)')}",
           f"- 环境：{result.get('subject', {}).get('environment', '(未填)')} ｜ 时间窗：{result.get('subject', {}).get('window', '(未填)')}",
           f"- 结论数 {result['counts']['claims']} ｜ 控制项 {result['counts']['controls']} ｜ BLOCK {result['counts']['block']} ｜ WARN {result['counts']['warn']}",
           "", "> 本表只证明「证据链可解析」，**不证明**软件安全、合规通过或运行时质量。",
           "", "## 结论 → 证据 → 原始输出", "",
           "| 规则/结论 | 声称 | 状态 | 证据文件 | 锚点 | 证据 sha256 | 采集 commit | 结论类型 | 对账判定 |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in result["claims"]:
        out.append(f"| {r['id']} | {r['statement']} | {r['status']} | `{r['evidence'] or '—'}` | "
                   f"`{r['anchor'] or '—'}` | `{r['sha256'][:16]}…` | {r['subject_commit'] or '—'} | "
                   f"{r['conclusion_class'] or '—'} | {r['verdict']} |")
    out += ["", "## 控制项映射", "",
            "| 控制项 | 关联结论 | 状态 | 缺口 |", "|---|---|---|---|"]
    for c in result["controls"]:
        out.append(f"| {c['control']} | {', '.join(c['claim_ids']) or '—'} | {c['status'] or '—'} | "
                   f"{', '.join(c['missing_claims']) or '无'} |")
    if not result["controls"]:
        out.append("| （未登记控制项） | — | — | 合规声明未做映射，须写「未做合规性声明对账」 |")
    out += ["", "## 缺口清单", ""]
    if result["findings"]:
        for f in result["findings"]:
            out.append(f"- [{f['severity']}] `{f['code']}` / {f['claim']}：{f['detail']}")
    else:
        out.append("- 无（本轮证据链未发现缺口）")
    out += ["", "## 锚点原文（可复核）", ""]
    for r in result["claims"]:
        if r["anchor_excerpt"]:
            out.append(f"- {r['id']} `{r['anchor']}` → `{r['anchor_excerpt']}`")
    return "\n".join(out) + "\n"


def self_test() -> int:
    """可证伪性自检：5 种缺陷必须全部被检出，漏检即 exit 1。"""
    cases: list[tuple[str, str, str]] = []  # (name, 期望 code, 说明)

    def make(dirpath: Path, *, drop_file=False, stale=False, bad_anchor=False,
             no_evidence=False, unclassified=False, with_controls=True) -> Path:
        ev = dirpath / "run.log"
        ev.write_text("line 1: start\nline 2: sha256 OK\nline 3: done\n", encoding="utf-8")
        if drop_file:
            ev.unlink()
        claim = {
            "id": "R-3", "statement": "制品可信", "status": "PASS",
            "evidence": "run.log",
            "anchor": "L999" if bad_anchor else "L2",
            "subject_commit": "old-commit" if stale else "abc123",
            "conclusion_class": "运行时质量" if not unclassified else "随便写写",
        }
        if no_evidence:
            claim.pop("evidence")
        manifest = {
            "subject": {"name": "self-test", "commit": "abc123",
                        "environment": "local", "window": "fixture"},
            "claims": [claim],
        }
        if with_controls:
            manifest["control_mapping"] = [
                {"control": "SSDF PS.3.2", "claim_ids": ["R-3"], "status": "mapped"}]
        p = dirpath / "manifest.json"
        p.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return p

    scenarios = [
        ("clean", {}, None),
        ("dangling", {"drop_file": True}, "dangling_reference"),
        ("stale", {"stale": True}, "stale_evidence"),
        ("bad_anchor", {"bad_anchor": True}, "unresolvable_anchor"),
        ("no_evidence", {"no_evidence": True}, "pass_without_proof"),
        ("unmapped_control", {"with_controls": False}, None),  # 单独验：无控制项须留一行声明
    ]
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, kwargs, expected in scenarios:
            d = Path(tmp) / name
            d.mkdir()
            p = make(d, **kwargs)
            res = audit_manifest(p)
            codes = {f["code"] for f in res["findings"]}
            if name == "clean":
                if res["counts"]["block"] != 0:
                    failures.append(f"clean: 干净链被误报 BLOCK: {sorted(codes)}")
                if not res["claims"][0]["sha256"]:
                    failures.append("clean: 未计算证据 sha256")
                if "sha256 OK" not in res["claims"][0]["anchor_excerpt"]:
                    failures.append("clean: 锚点原文未被解析出来")
            elif name == "unmapped_control":
                md = to_markdown(res)
                if "未做合规性声明对账" not in md:
                    failures.append("unmapped_control: 无控制项时未输出缺口声明")
                if res["counts"]["block"] != 0:
                    failures.append(f"unmapped_control: 无控制项被误判 BLOCK: {sorted(codes)}")
            elif expected not in codes:
                failures.append(f"{name}: 期望检出 {expected}，实际 {sorted(codes)}")

    # 结论类型未标注必须被 WARN（防止四类结论被混为一谈）
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "cls"
        d.mkdir()
        p = make(d, unclassified=True)
        res = audit_manifest(p)
        if "unclassified_conclusion" not in {f["code"] for f in res["findings"]}:
            failures.append("unclassified: 未标注四类结论未被检出")

    if failures:
        for f in failures:
            print(f"[SELFTEST FAIL] {f}")
        print("结论：SELFTEST BLOCKED —— 证据链对账门禁不可信，禁止用于交付。")
        return 1
    print("[SELFTEST PASS] 干净链无 BLOCK；悬空引用 / 过期证据 / 不可解析锚点 / PASS 无证据 / 无控制项缺口声明 / 未分类结论 均被检出")
    print("结论：SELFTEST GREEN —— 证据链对账门禁可证伪。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="证据链自动对账 / 审计导出（project-tester v1.5）")
    ap.add_argument("--self-test", action="store_true", help="运行可证伪性自检，不读写项目文件")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("audit", help="对账一个 manifest")
    a.add_argument("--manifest", required=True)
    a.add_argument("--root", default=None, help="相对证据路径的解析根目录（默认 manifest 所在目录）")
    a.add_argument("--format", choices=("json", "markdown"), default="markdown")
    a.add_argument("--output", default=None, help="显式给出才写文件；默认只打印到 stdout")
    a.add_argument("--fail-on-gap", action="store_true", help="存在 BLOCK 级缺口时退出码 1")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.cmd != "audit":
        ap.print_help()
        return 0

    manifest = Path(args.manifest)
    root = Path(args.root) if args.root else None
    result = audit_manifest(manifest, root)
    text = json.dumps(result, ensure_ascii=False, indent=2) if args.format == "json" else to_markdown(result)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"已写入审计导出：{args.output}")
    else:
        print(text)
    if args.fail_on_gap and result["counts"]["block"] > 0:
        print(f"结论：BLOCKED（{result['counts']['block']} 处 BLOCK 级证据链缺口）")
        return 1
    print(f"结论：{'GREEN' if result['ok'] else '有缺口'} ｜ "
          f"BLOCK {result['counts']['block']} / WARN {result['counts']['warn']} ｜ "
          f"注：对账通过只证明证据链可解析，不证明合规或软件安全")
    return 0


if __name__ == "__main__":
    sys.exit(main())
