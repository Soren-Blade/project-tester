#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""金额与账务正确性离线审计（R-15 配套，零依赖）。

用法：
  python scripts/money-audit.py scan <path> [--format text|json] [--fail-on-gap]
  python scripts/money-audit.py ledger --file <ledger.json> [--format text|json] [--fail-on-gap]
  python scripts/money-audit.py cases [--format text|json]
  python scripts/money-audit.py --self-test

规则编号：
  MO-01 金额经 parseFloat/parseInt/Number 进入浮点    （HIGH）
  MO-02 用 toFixed 做金融舍入（二进制误差）            （HIGH）
  MO-03 硬编码 *100 / /100 换算最小单位（0/3 位货币坏） （MEDIUM）
  MO-04 用 Math.round / 无舍入模式的 round             （MEDIUM）
  MO-05 金额列声明为 FLOAT / REAL / DOUBLE PRECISION   （HIGH）
  MO-06 对金额做浮点相等比较 == / !=                    （MEDIUM）
  MO-07 金额除以份数做分摊（余数丢失）                  （HIGH）
  MO-08 直接信任客户端传入的 amount / price             （HIGH）
  MO-09 硬编码 2 位小数（零小数与三位小数货币错）        （HIGH）
  MO-10 账本：交易不平 / 单边分录 / 精度越界 / 混币      （S1）

诚实边界：
- 只读本地源码与本地 JSON 清单，**不联网、不代填**任何字段。
- 静态命中只是「可疑写法」，**不证明**被测系统真的算错；未命中**不证明**金额正确。
- ledger 对账只证明「给定清单内部自洽」，**不证明**真实账本完整、不证明业务可用。
- 不冒充「财务合规」「账务准确」，不替代人工复核与真实交易对账。
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import traceback
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CODE_SUFFIXES = {
    ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".py", ".go", ".java",
    ".kt", ".php", ".rb", ".cs", ".rs", ".sql", ".vue", ".svelte",
}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".test-memory", "dist", "build", ".venv"}

# 只在一行里出现「金额语义」时才判，降低噪音；命中只是可疑项，不是定论。
MONEY_WORD = re.compile(
    r"(?i)(amount|price|total|subtotal|discount|tax|refund|balance|fee|cost|"
    r"charge|payment|invoice|money|cents?|currency|ledger|debit|credit)"
)

RULES = [
    ("MO-01", "HIGH", re.compile(r"\b(parseFloat|parseInt|Number)\s*\("),
     "金额经浮点/整数解析进入计算", "改用整数最小单位或十进制定点（DECIMAL/NUMERIC）"),
    ("MO-02", "HIGH", re.compile(r"\.toFixed\s*\("),
     "用 toFixed 做金融舍入", "toFixed 在二进制浮点上会产生 2.675→2.67 类误差；改用十进制 + 显式舍入模式"),
    ("MO-03", "MEDIUM", re.compile(r"(\*\s*100|/\s*100)\b"),
     "硬编码 ×100 / ÷100 换算最小单位", "按 ISO 4217 exponent 换算（JPY=0、KWD=3），不得全局写死 100"),
    ("MO-04", "MEDIUM", re.compile(r"\bMath\.round\s*\(|(?<!Decimal\.)\bround\s*\("),
     "用默认 round / Math.round 做金额舍入", "金融舍入需显式模式（half-even / half-up）并写进契约"),
    ("MO-05", "HIGH", re.compile(r"\b(FLOAT|REAL|DOUBLE\s+PRECISION|double|float)\b", re.I),
     "金额列/字段声明为浮点类型", "金额用整数最小单位或 DECIMAL/NUMERIC，不用 float/double"),
    ("MO-06", "MEDIUM", re.compile(r"(?<![=!<>])(==|!=)(?!=)"),
     "对金额做浮点相等比较", "用最小单位整数比较，或按容差比较并写清容差"),
    ("MO-07", "HIGH", re.compile(r"/\s*(count|n|parts|length|people|users|split)\b", re.I),
     "金额除以份数做分摊", "用最大余额法/分配算法，保证 Σ分摊 == 原额，余数显式落账"),
    ("MO-08", "HIGH", re.compile(
        r"(?i)\b(amount|price|total)\b\s*[:=]\s*(req|request|body|params|query|client)\b"),
     "直接信任客户端传入的金额", "服务端按 SKU 单价重新计价；客户端金额只做校验，不参与扣款"),
    ("MO-09", "HIGH", re.compile(r"(?i)(toFixed|quantize|round)\s*\(\s*2\s*\)"),
     "硬编码 2 位小数", "按币种 exponent 决定小数位（JPY 0 位、KWD 3 位）"),
]

ZERO_DECIMAL = {
    "BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW", "PYG",
    "RWF", "UGX", "UYI", "VND", "VUV", "XAF", "XOF", "XPF",
}
THREE_DECIMAL = {"BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"}


def exponent(currency: str) -> int:
    c = (currency or "").upper()
    if c in ZERO_DECIMAL:
        return 0
    if c in THREE_DECIMAL:
        return 3
    return 2


def iter_code_files(root: Path):
    if root.is_file():
        if root.suffix.lower() in CODE_SUFFIXES:
            yield root
        return
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in CODE_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        yield p


def scan(root: Path) -> list[dict]:
    hits: list[dict] = []
    for path in iter_code_files(root):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception as e:
            hits.append({"rule": "MO-00", "severity": "LOW", "file": str(path),
                         "line": 0, "snippet": f"<读取失败: {e}>", "reason": "无法读取，未审计"})
            continue
        for i, line in enumerate(lines, 1):
            if not MONEY_WORD.search(line):
                continue
            for rid, sev, rx, reason, hint in RULES:
                if rx.search(line):
                    hits.append({"rule": rid, "severity": sev,
                                 "file": str(path), "line": i,
                                 "snippet": line.strip()[:200],
                                 "reason": reason, "hint": hint})
    # 同一行同一规则只留一条
    seen, out = set(), []
    for h in hits:
        key = (h["rule"], h["file"], h["line"])
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out


def dec(value, currency: str) -> Decimal:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"非法金额: {value!r}")
    if not d.is_finite():
        raise ValueError(f"非法金额: {value!r}")
    return d


def audit_ledger(obj) -> tuple[list[dict], dict]:
    issues: list[dict] = []
    meta: dict = {"entries": 0, "transactions": 0, "currencies": []}

    if isinstance(obj, list):
        entries, top_currency, multi = obj, None, True
    elif isinstance(obj, dict):
        entries = obj.get("entries") or []
        top_currency = obj.get("currency")
        multi = bool(obj.get("multi_currency"))
    else:
        return [{"id": "LG-00", "severity": "S1", "reason": "清单不是对象或数组"}], meta

    if not entries:
        issues.append({"id": "LG-00", "severity": "S1", "reason": "账本为空或无 entries，无法对账"})
        return issues, meta

    meta["entries"] = len(entries)
    txs: dict[str, list[dict]] = {}
    currencies: set[str] = set()
    for idx, e in enumerate(entries):
        if not isinstance(e, dict):
            issues.append({"id": "LG-00", "severity": "S1", "reason": f"第 {idx} 条分录不是对象"})
            continue
        cur = (e.get("currency") or top_currency or "").upper()
        if not cur:
            issues.append({"id": "LG-01", "severity": "S1",
                           "reason": f"第 {idx} 条分录缺 currency（无法知 exponent）"})
        else:
            currencies.add(cur)
        for side in ("debit", "credit"):
            if e.get(side) is None:
                continue
            try:
                amount = dec(e[side], cur)
            except ValueError as ex:
                issues.append({"id": "LG-04", "severity": "S1", "reason": f"第 {idx} 条 {side} {ex}"})
                continue
            if amount < 0:
                issues.append({"id": "LG-05", "severity": "S1",
                               "reason": f"第 {idx} 条 {side} 为负数（应改用反向科目）"})
            if cur:
                digits = -amount.as_tuple().exponent if amount.as_tuple().exponent < 0 else 0
                if digits > exponent(cur):
                    issues.append({"id": "LG-04", "severity": "S1",
                                   "reason": f"第 {idx} 条 {side}={amount} 超出 {cur} 的 {exponent(cur)} 位小数"})
        tx = str(e.get("tx") or e.get("transaction_id") or "")
        if not tx:
            issues.append({"id": "LG-03", "severity": "S1",
                           "reason": f"第 {idx} 条分录缺 tx（无法判断是否平衡）"})
            continue
        txs.setdefault(tx, []).append(e)

    meta["transactions"] = len(txs)
    meta["currencies"] = sorted(currencies)
    if len(currencies) > 1 and not multi:
        issues.append({"id": "LG-06", "severity": "S1",
                       "reason": f"同一账本混用多币种 {sorted(currencies)} 且未声明 multi_currency"})
    for tx, rows in txs.items():
        if len(rows) < 2:
            issues.append({"id": "LG-03", "severity": "S1",
                           "reason": f"交易 {tx} 只有 {len(rows)} 条分录（复式记账至少借+贷两条）"})
        debit = sum((dec(r.get("debit", 0), r.get("currency") or top_currency or "USD") for r in rows), Decimal("0"))
        credit = sum((dec(r.get("credit", 0), r.get("currency") or top_currency or "USD") for r in rows), Decimal("0"))
        if debit != credit:
            issues.append({"id": "LG-02", "severity": "S1",
                           "reason": f"交易 {tx} 不平：借 {debit} ≠ 贷 {credit}（差 {debit - credit}）"})
    return issues, meta


def show_cases() -> list[str]:
    lines = ["# 金额计算反例（用十进制真值对照）", ""]
    f = 0.1 + 0.2
    lines.append(f"- 浮点：0.1 + 0.2 = {f!r}（不是 0.3）")
    d = Decimal("2.675")
    lines.append(f"- 十进制 2.675 按 half-up 两位 = {d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}")
    lines.append(f"- 浮点 2.675 经 round(...,2) = {round(2.675, 2)!r}（二进制表示低于真值，被舍成 2.67）")
    lines.append("- JPY 是 0 位小数：最小单位 1000 = ¥1000；若按 2 位处理会变成 ¥10.00")
    lines.append("- KWD 是 3 位小数：最小单位 1234 = KWD 1.234；按 2 位处理会变成 12.34")
    amount = Decimal("100.00")
    n = 3
    base = (amount / n).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    allocated = base * n
    lines.append(f"- 100.00 分 3 份：直接除 = {base} × 3 = {allocated}（丢 {amount - allocated}）；"
                 f"最大余额法 = 33.33 / 33.33 / 33.34，Σ = 100.00")
    lines.append("")
    lines.append("> 这些是确定性反例，可直接作为 M-01~M-05 的期望值；不能替代对被测系统的实调。")
    return lines


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
        print(json.dumps({"tool": "money-audit", "mode": "scan", "hits": hits,
                          "note": "静态命中只是可疑写法，未命中不证明金额正确"}, ensure_ascii=False, indent=2))
        return
    print(f"# 金额反模式扫描：{len(hits)} 处可疑")
    for h in hits:
        print(f"[{h['rule']} {h['severity']}] {h['file']}:{h['line']}  {h['reason']}")
        print(f"    {h['snippet']}")
        if h.get("hint"):
            print(f"    → {h['hint']}")
    print("> 未命中不证明金额正确；必须配合实调金额边界与账本对账。")


def print_ledger(issues: list[dict], meta: dict, fmt: str) -> None:
    hard = [i for i in issues if i["severity"] == "S1"]
    if fmt == "json":
        print(json.dumps({"tool": "money-audit", "mode": "ledger", "meta": meta,
                          "issues": issues, "gaps": len(hard),
                          "note": "只证明给定清单内部自洽，不证明真实账本完整或业务可用"},
                         ensure_ascii=False, indent=2))
        return
    print(f"# 账本对账：{meta['entries']} 条分录 / {meta['transactions']} 笔交易 / 币种 {meta['currencies']}")
    for i in issues:
        print(f"[{i['id']} {i['severity']}] {i['reason']}")
    print(f"> 缺口 {len(hard)} 项；清单内部平衡不等于真实账本完整，需与支付渠道/银行流水对账。")


def self_test() -> int:
    checks: list[tuple[str, bool]] = []
    tmp = Path(tempfile.mkdtemp(prefix="money-audit-selftest-"))
    bad = tmp / "bad.js"
    bad.write_text(
        "const total = parseFloat(req.body.amount) * 100;\n"
        "const price = (a + b).toFixed(2);\n"
        "const rate = Math.round(tax * 100) / 100;\n"
        "const share = amount / parts;\n"
        "const amount = req.body.amount;\n"
        "if (charged == total) {}\n"
        "// CREATE TABLE orders (total FLOAT)\n",
        encoding="utf-8",
    )
    good = tmp / "good.js"
    good.write_text(
        "const totalMinor = money.add(priceMinor, taxMinor); // integer minor units\n"
        "const display = formatMoney(totalMinor, currency); // exponent from ISO 4217\n",
        encoding="utf-8",
    )
    hits = scan(tmp)
    found = {h["rule"] for h in hits}
    for rid in ("MO-01", "MO-02", "MO-03", "MO-04", "MO-07", "MO-08", "MO-09"):
        checks.append((f"scan 检出 {rid}", rid in found))
    checks.append(("good.js 不产生 HIGH 命中", not [h for h in hits if h["file"].endswith("good.js")]))

    bad_ledger = {
        "currency": "USD",
        "entries": [
            {"tx": "t1", "account": "cash", "debit": "100.00"},
            {"tx": "t1", "account": "revenue", "credit": "99.99"},
            {"tx": "t2", "account": "cash", "debit": "5.00"},
            {"tx": "t3", "account": "cash", "debit": "1.234"},
        ],
    }
    issues, meta = audit_ledger(bad_ledger)
    ids = {i["id"] for i in issues}
    checks.append(("ledger 检出不平 LG-02", "LG-02" in ids))
    checks.append(("ledger 检出单边 LG-03", "LG-03" in ids))
    checks.append(("ledger 检出精度越界 LG-04", "LG-04" in ids))
    good_ledger = {"currency": "USD", "entries": [
        {"tx": "t1", "account": "cash", "debit": "100.00"},
        {"tx": "t1", "account": "revenue", "credit": "100.00"},
    ]}
    good_issues, _ = audit_ledger(good_ledger)
    checks.append(("平衡账本零缺口", not good_issues))
    jpy = {"currency": "JPY", "entries": [
        {"tx": "j1", "account": "cash", "debit": "1000"},
        {"tx": "j1", "account": "revenue", "credit": "1000"},
    ]}
    jpy_issues, _ = audit_ledger(jpy)
    checks.append(("JPY 整数金额不误报精度", not jpy_issues))

    cases = "\n".join(show_cases())
    checks.append(("cases 给出 0.1+0.2 反例", "0.30000000000000004" in cases))
    checks.append(("cases 给出 JPY 0 位小数", "¥1000" in cases))
    checks.append(("cases 给出分摊丢分", "最大余额法" in cases))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if failed:
        print(f"SELFTEST RED（{len(failed)} 项失败）")
        return 1
    print(f"SELFTEST GREEN（{len(checks)} 项断言）")
    print("边界：自检只证明本脚本的扫描/对账逻辑可用，不证明被测系统金额正确，不冒充财务合规。")
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
    if opts["cmd"] == "ledger":
        if not opts["file"]:
            print("用法: money-audit.py ledger --file ledger.json")
            return 2
        try:
            obj = json.loads(Path(opts["file"]).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"读取清单失败: {e}")
            return 2
        issues, meta = audit_ledger(obj)
        print_ledger(issues, meta, opts["format"])
        return 1 if (opts["fail"] and any(i["severity"] == "S1" for i in issues)) else 0
    if opts["cmd"] == "cases":
        if opts["format"] == "json":
            print(json.dumps({"tool": "money-audit", "mode": "cases",
                              "float_0_1_plus_0_2": repr(0.1 + 0.2),
                              "jpy_minor_example": 1000, "kwd_minor_example": 1234,
                              "note": "确定性反例，不替代实调"}, ensure_ascii=False, indent=2))
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
