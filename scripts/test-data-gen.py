#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""project-tester 测试数据生成与脱敏脚本（TDM 辅助，见 references/test-data-management.md）

用法：
  python scripts/test-data-gen.py generate --count N --seed S --format json [--output FILE]
  python scripts/test-data-gen.py mask --input FILE --fields email,phone,name [--output FILE]
  python scripts/test-data-gen.py self-test

设计纪律（诚实边界，详见 references/test-data-management.md §7）：
  - 不联网：只用标准库与本地内置词表，绝不外发任何数据
  - 不代填：不连接任何真实数据库、不读取生产数据；输入只来自用户本地文件或 --count 生成
  - 不冒充：本脚本只做「生成 / 掩码 / 校验可复现」，不裁决「无 PII 泄漏」「合规通过」「数据可用」
  - 不保证无泄漏：掩码是启发式规则（保留格式、替换主体），不保证不可逆、不保证覆盖全部 PII；
    声称「测试数据已脱敏」必须结合人工复核与 R-11 证据，不得因用了本脚本就写「数据已脱敏」

退出码：0 = 成功 / SELFTEST GREEN；1 = 参数错误 / 自检失败 / 掩码校验失败
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FIRST_NAMES = ["Alice", "Bob", "Carol", "David", "Emma", "Frank", "Grace", "Henry",
               "张", "李", "王", "赵", "陈", "刘", "杨", "黄"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
              "伟", "芳", "娜", "敏", "静", "强", "磊"]
DOMAINS = ["example.com", "example.org", "test.dev", "mail.test"]
STREETS = ["Main St", "Oak Ave", "Pine Rd", "中山路", "解放大道", "科技园路"]
CITIES = ["Springfield", "Riverside", "北京", "上海", "深圳", "广州"]
ROLES = ["customer", "admin", "guest", "moderator"]

# determinism：固定词表顺序 + 显式 random.Random(seed)，保证同种子同输出


def _new_rng(seed: int) -> random.Random:
    rng = random.Random()
    rng.seed(seed)
    return rng


def generate_person(rng: random.Random, idx: int) -> dict:
    fn = rng.choice(FIRST_NAMES)
    ln = rng.choice(LAST_NAMES)
    name = f"{fn} {ln}"
    local = f"user{idx:04d}"
    email = f"{local}@{rng.choice(DOMAINS)}"
    phone = f"1{rng.randint(3000000000, 3999999999)}"  # 11 位，掩码只留后 4
    street_no = rng.randint(1, 999)
    address = f"{rng.choice(CITIES)} {rng.choice(STREETS)} {street_no}号"
    role = rng.choice(ROLES)
    return {
        "id": f"00000000-0000-0000-{idx:04x}-{idx:08x}",
        "name": name,
        "email": email,
        "phone": phone,
        "address": address,
        "role": role,
    }


def generate(count: int, seed: int) -> list[dict]:
    rng = _new_rng(seed)
    return [generate_person(rng, i) for i in range(count)]


def mask_field(field: str, value: str) -> str:
    """保留格式掩码（format-preserving）：只替换主体，不保证不可逆、不保证覆盖全部 PII。"""
    if not isinstance(value, str) or not value:
        return value
    if field == "email":
        if "@" not in value:
            return value
        local, _, domain = value.partition("@")
        if not local:
            return value
        return f"{local[0]}***@{domain}"
    if field == "phone":
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) < 4:
            return value
        return f"****{digits[-4:]}"
    if field == "name":
        # 取首字符 + 掩码，中文姓/英文 first name 都适用
        return f"{value[0]}***"
    return value  # 未声明字段不处理，避免误判"已脱敏"


def mask_records(records: list[dict], fields: list[str]) -> list[dict]:
    out = []
    for rec in records:
        new = dict(rec)
        for f in fields:
            if f in new:
                new[f] = mask_field(f, str(new[f]))
        out.append(new)
    return out


def _emit(payload, output: str | None, as_json: bool = True) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) if as_json else str(payload)
    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def cmd_generate(args: argparse.Namespace) -> int:
    data = generate(args.count, args.seed)
    _emit(data, args.output)
    return 0


def cmd_mask(args: argparse.Namespace) -> int:
    path = Path(args.input)
    if not path.is_file():
        print(f"[FAIL] 输入文件不存在: {args.input}", file=sys.stderr)
        return 1
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[FAIL] 输入非合法 JSON: {e}", file=sys.stderr)
        return 1
    if not isinstance(records, list):
        records = [records]
    fields = [f.strip() for f in args.fields.split(",") if f.strip()]
    masked = mask_records(records, fields)
    _emit(masked, args.output)
    return 0


def cmd_self_test(args: argparse.Namespace) -> int:
    """脚本可证伪自检：验证确定性 + 掩码逻辑，不联网、不代填、不冒充、不保证无泄漏。"""
    failures: list[str] = []

    # 1) 确定性：同种子两次生成逐字节一致
    a = generate(20, 42)
    b = generate(20, 42)
    if json.dumps(a, ensure_ascii=False) != json.dumps(b, ensure_ascii=False):
        failures.append("deterministic: 同种子两次生成不一致")

    # 2) 不同种子应不同
    c = generate(20, 43)
    if json.dumps(a, ensure_ascii=False) == json.dumps(c, ensure_ascii=False):
        failures.append("deterministic: 不同种子却生成相同数据")

    # 3) 掩码：已知 PII 掩码后原标识符不可恢复
    sample = [
        {"name": "Alice Smith", "email": "alice@example.com", "phone": "13800001234"},
        {"name": "张三", "email": "zhangsan@test.dev", "phone": "13912345678"},
    ]
    masked = mask_records(sample, ["name", "email", "phone"])
    for orig, m in zip(sample, masked):
        for f in ("name", "email", "phone"):
            if str(orig[f]) in str(m[f]):
                failures.append(f"mask: 字段 {f} 掩码后仍含原文 '{orig[f]}'")

    # 4) 掩码保留格式（仍能识别类型，便于走通校验）
    if not masked[0]["email"].endswith("@example.com"):
        failures.append("mask: email 掩码破坏了 @domain 结构")
    if not masked[0]["phone"].startswith("****"):
        failures.append("mask: phone 掩码格式异常")

    # 5) 未声明字段不被掩码（避免误判"已脱敏"）
    if "address" in masked[0] and masked[0]["address"] == "***":
        failures.append("mask: 未声明字段被错误掩码")

    if failures:
        for f in failures:
            print(f"[SELFTEST FAIL] {f}", file=sys.stderr)
        print("结论：BLOCKED —— 脚本逻辑自检失败。", file=sys.stderr)
        return 1
    print("SELFTEST GREEN —— 脚本确定性/掩码逻辑可用（不证明你的数据集无 PII 泄漏或合规通过）。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="project-tester 测试数据生成与脱敏（零依赖，标准库）")
    p.add_argument("--self-test", action="store_true", help="脚本自身可证伪自检（确定性 + 掩码逻辑）")
    sub = p.add_subparsers(dest="cmd")

    g = sub.add_parser("generate", help="合成生成测试数据（确定性种子）")
    g.add_argument("--count", type=int, default=10)
    g.add_argument("--seed", type=int, default=42, help="确定性种子：同种子同输出")
    g.add_argument("--format", choices=["json"], default="json")
    g.add_argument("--output", default=None, help="输出文件，缺省打印到 stdout")
    g.set_defaults(func=cmd_generate)

    m = sub.add_parser("mask", help="对本地 JSON 记录的指定字段做保留格式掩码")
    m.add_argument("--input", required=True, help="输入 JSON 文件（list[dict]）")
    m.add_argument("--fields", required=True, help="逗号分隔字段，如 email,phone,name")
    m.add_argument("--output", default=None, help="输出文件，缺省打印到 stdout")
    m.set_defaults(func=cmd_mask)

    sub.add_parser("self-test", help="脚本自身可证伪自检（确定性 + 掩码逻辑）")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.self_test or args.cmd == "self-test" or args.cmd is None:
        return cmd_self_test(args)
    if args.cmd == "generate":
        return cmd_generate(args)
    if args.cmd == "mask":
        return cmd_mask(args)
    return cmd_self_test(args)


if __name__ == "__main__":
    raise SystemExit(main())
