#!/usr/bin/env python3
"""restore-audit.py — 备份/恢复可验证性离线审计（零依赖）

用途
  compare : 对比「备份时清单（source manifest）」与「恢复后清单（restored manifest）」，
            检出文件缺失/多出/大小不符/hash 不符、表行数不符、序列 max(id) 不符、
            恢复时间缺失时区、恢复早于备份（陈旧恢复）、应用/模式版本不符。
  --self-test : 用内造的好/坏两套清单证明每类缺口都能被检出，且好清单不误报。

清单 JSON 约定（两侧同构；恢复侧必须有 restored_at）
  {
    "generated_at": "2026-11-14T02:00:00Z",      // 备份快照时刻，必须带偏移
    "restored_at": "2026-11-14T03:10:00+08:00",  // 仅恢复侧：恢复完成时刻，必须带偏移
    "app_version": "1.4.2",
    "schema_version": "2026_11_01",
    "files": [{"path": "attachments/a.pdf", "sha256": "<hex>", "bytes": 1234}],
    "tables": [{"name": "users", "rows": 120, "max_id": 120}]
  }

诚实边界（必须与结论一起引用）
  * 不联网：只读本地两份 JSON，不连接数据库、不校验真实文件字节。
  * 不代填：不猜 RPO/RTO、不代替恢复流程；清单可由任何人生成。
  * 不证明：两份清单一致 **不证明** 恢复出的系统业务可用（索引、权限、密钥、扩展、
    触发器、外部依赖均未覆盖）；清单本身可伪造。真正的结论必须来自实际恢复后
    抽样查询与业务冒烟（R-14）。
  * 未恢复过的备份 **不算备份**：本工具无法替代一次真实 restore drill。

用法
  python restore-audit.py compare --source source-manifest.json --restored restored-manifest.json
  python restore-audit.py compare ... --format json --fail-on-gap
  python restore-audit.py --self-test
"""

import argparse
import json
import sys
import tempfile
from datetime import datetime


def _parse_dt(value):
    """解析 ISO 8601；naive（无偏移）返回 (None, 原文) 交给调用方报错。"""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _load(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit("FAIL: %s 不是 JSON 对象" % path)
    return data


def _index_files(manifest, side, errors):
    files = manifest.get("files")
    if files is None:
        return None
    if not isinstance(files, list):
        errors.append({"id": "RST-11", "level": "high", "message": "%s 的 files 不是数组，无法核对附件" % side})
        return None
    indexed = {}
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            errors.append({"id": "RST-11", "level": "high", "message": "%s 的 files 有条目缺 path" % side})
            continue
        indexed[item["path"]] = item
    return indexed


def _index_tables(manifest, side, errors):
    tables = manifest.get("tables")
    if tables is None:
        return None
    if not isinstance(tables, list):
        errors.append({"id": "RST-11", "level": "high", "message": "%s 的 tables 不是数组，无法核对行数" % side})
        return None
    indexed = {}
    for item in tables:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            errors.append({"id": "RST-11", "level": "high", "message": "%s 的 tables 有条目缺 name" % side})
            continue
        indexed[item["name"]] = item
    return indexed


def compare(source, restored):
    errors = []
    warnings = []

    src_at = _parse_dt(source.get("generated_at"))
    if src_at is None:
        errors.append({"id": "RST-01", "level": "high",
                       "message": "源清单 generated_at 缺失或未带时区偏移：无法确定备份对应哪个时刻"})

    res_at = _parse_dt(restored.get("restored_at"))
    if res_at is None:
        errors.append({"id": "RST-02", "level": "high",
                       "message": "恢复清单 restored_at 缺失或未带时区偏移：无法判断恢复是否新鲜"})

    if src_at and res_at and res_at < src_at:
        errors.append({"id": "RST-03", "level": "critical",
                       "message": "恢复时刻（%s）早于备份时刻（%s）：这是陈旧/错误备份，不是可用恢复" % (
                           restored.get("restored_at"), source.get("generated_at"))})

    for key in ("app_version", "schema_version"):
        src_v = source.get(key)
        res_v = restored.get(key)
        if src_v != res_v:
            errors.append({"id": "RST-10", "level": "high",
                           "message": "%s 不一致：备份 %r ≠ 恢复 %r（跨版本恢复需单独验证兼容性）" % (
                               key, src_v, res_v)})

    src_files = _index_files(source, "源清单", errors)
    res_files = _index_files(restored, "恢复清单", errors)
    if src_files is None or res_files is None:
        warnings.append("至少一侧没有 files 数组：附件完整性未验证（这是盲区，不是通过）")
    else:
        for path in sorted(set(src_files) - set(res_files)):
            errors.append({"id": "RST-04", "level": "critical",
                           "message": "备份含文件但恢复缺失：%s" % path})
        for path in sorted(set(res_files) - set(src_files)):
            errors.append({"id": "RST-05", "level": "high",
                           "message": "恢复多出备份中没有的文件：%s（确认是否串库/串租户）" % path})
        for path in sorted(set(src_files) & set(res_files)):
            src_item, res_item = src_files[path], res_files[path]
            if src_item.get("bytes") != res_item.get("bytes"):
                errors.append({"id": "RST-06", "level": "high",
                               "message": "文件大小不符：%s（备份 %r ≠ 恢复 %r）" % (
                                   path, src_item.get("bytes"), res_item.get("bytes"))})
            src_hash = src_item.get("sha256")
            res_hash = res_item.get("sha256")
            if not src_hash or not res_hash:
                errors.append({"id": "RST-07", "level": "high",
                               "message": "文件缺 sha256：%s（无法证明字节一致；应生成并比对校验和）" % path})
            elif src_hash != res_hash:
                errors.append({"id": "RST-07", "level": "critical",
                               "message": "文件 hash 不符：%s（备份 %s… ≠ 恢复 %s…）" % (
                                   path, src_hash[:12], res_hash[:12])})

    src_tables = _index_tables(source, "源清单", errors)
    res_tables = _index_tables(restored, "恢复清单", errors)
    if src_tables is None or res_tables is None:
        warnings.append("至少一侧没有 tables 数组：行数/序列未验证（这是盲区，不是通过）")
    else:
        for name in sorted(set(src_tables) - set(res_tables)):
            errors.append({"id": "RST-08", "level": "critical",
                           "message": "备份含表但恢复缺失：%s（恢复不完整）" % name})
        for name in sorted(set(res_tables) - set(src_tables)):
            errors.append({"id": "RST-08", "level": "high",
                           "message": "恢复多出备份中没有的表：%s（确认是否串库）" % name})
        for name in sorted(set(src_tables) & set(res_tables)):
            src_row, res_row = src_tables[name], res_tables[name]
            if src_row.get("rows") != res_row.get("rows"):
                errors.append({"id": "RST-08", "level": "critical",
                               "message": "表行数不符：%s（备份 %r ≠ 恢复 %r）" % (
                                   name, src_row.get("rows"), res_row.get("rows"))})
            if src_row.get("max_id") != res_row.get("max_id"):
                errors.append({"id": "RST-09", "level": "high",
                               "message": "序列/max(id) 不符：%s（备份 %r ≠ 恢复 %r）；恢复后新插入可能主键冲突" % (
                                   name, src_row.get("max_id"), res_row.get("max_id"))})

    return {"verdict": "FAIL" if errors else "PASS", "errors": errors, "warnings": warnings}


def render(result):
    lines = ["# 备份/恢复清单核对（restore-audit.py）", ""]
    lines.append("- 结论：**%s**；缺口 %d 项；盲区提示 %d 条" % (
        result["verdict"], len(result["errors"]), len(result["warnings"])))
    lines += ["", "| 编号 | 级别 | 说明 |", "|---|---|---|"]
    for item in result["errors"]:
        lines.append("| %s | %s | %s |" % (item["id"], item["level"], item["message"].replace("|", "\\|")))
    if not result["errors"]:
        lines.append("| — | — | 两份清单在已登记的不变量上一致 |")
    lines += ["", "## 盲区（未覆盖 ≠ 通过）", ""]
    for warning in result["warnings"]:
        lines.append("- " + warning)
    if not result["warnings"]:
        lines.append("- 无：但仍不代表业务可用，须做恢复后抽样查询与冒烟。")
    lines += ["", "## 边界", "",
              "- 清单一致不证明恢复可用（索引/权限/密钥/扩展/外部依赖未覆盖）；清单可伪造。",
              "- 不联网、不代填、不证明；结论须配合一次真实 restore drill（R-14）。"]
    return "\n".join(lines)


def selftest():
    failures = []

    def expect(name, condition):
        if not condition:
            failures.append(name)

    good_source = {
        "generated_at": "2026-11-14T02:00:00Z",
        "app_version": "1.4.2",
        "schema_version": "2026_11_01",
        "files": [
            {"path": "attachments/a.pdf", "sha256": "a" * 64, "bytes": 100},
            {"path": "attachments/b.png", "sha256": "b" * 64, "bytes": 200},
        ],
        "tables": [
            {"name": "users", "rows": 120, "max_id": 120},
            {"name": "events", "rows": 3400, "max_id": 3400},
        ],
    }
    good_restored = json.loads(json.dumps(good_source))
    good_restored["restored_at"] = "2026-11-14T10:10:00+08:00"
    good_result = compare(good_source, good_restored)
    expect("好清单零误报", good_result["verdict"] == "PASS" and not good_result["errors"])

    bad_restored = json.loads(json.dumps(good_source))
    bad_restored["restored_at"] = "2026-11-14T03:10:00"  # naive
    bad_restored["schema_version"] = "2026_10_01"
    bad_restored["files"] = [
        {"path": "attachments/a.pdf", "sha256": "c" * 64, "bytes": 100},
        {"path": "attachments/extra.txt", "sha256": "d" * 64, "bytes": 5},
    ]
    bad_restored["tables"] = [
        {"name": "users", "rows": 117, "max_id": 121},
        {"name": "events", "rows": 3400, "max_id": 3400},
    ]
    bad_result = compare(good_source, bad_restored)
    ids = {item["id"] for item in bad_result["errors"]}
    expect("RST-02 无时区被检出", "RST-02" in ids)
    expect("RST-04 缺文件被检出", "RST-04" in ids)
    expect("RST-05 多文件被检出", "RST-05" in ids)
    expect("RST-07 hash 不符被检出", "RST-07" in ids)
    expect("RST-08 行数不符被检出", "RST-08" in ids)
    expect("RST-09 序列不符被检出", "RST-09" in ids)
    expect("RST-10 版本不符被检出", "RST-10" in ids)
    expect("坏清单判 FAIL", bad_result["verdict"] == "FAIL")

    stale_restored = json.loads(json.dumps(good_source))
    stale_restored["restored_at"] = "2026-11-13T23:00:00Z"
    stale_result = compare(good_source, stale_restored)
    expect("RST-03 陈旧恢复被检出", any(i["id"] == "RST-03" for i in stale_result["errors"]))

    gap_source = {"generated_at": "2026-11-14T02:00:00Z", "tables": []}
    gap_restored = {"generated_at": "2026-11-14T02:00:00Z", "restored_at": "2026-11-14T03:00:00Z", "tables": []}
    gap_result = compare(gap_source, gap_restored)
    expect("缺 files 时给盲区警告", any("附件完整性未验证" in w for w in gap_result["warnings"]))

    with tempfile.TemporaryDirectory() as tmp:
        path = tmp + "/manifest.json"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(good_source, handle)
        expect("_load 读回字典", _load(path)["app_version"] == "1.4.2")

    if failures:
        print("SELFTEST FAIL: " + ", ".join(failures))
        return 1
    print("SELFTEST GREEN: 12 项断言全过（好清单零误报 + 缺文件/多文件/hash/行数/序列/版本/无时区/陈旧恢复 + 盲区告警）")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="备份/恢复清单核对（不联网、不代填、不证明）")
    sub = parser.add_subparsers(dest="command")

    cmp_cmd = sub.add_parser("compare", help="对比源清单与恢复后清单")
    cmp_cmd.add_argument("--source", required=True, help="备份时生成的 manifest.json")
    cmp_cmd.add_argument("--restored", required=True, help="恢复后生成的 manifest.json")
    cmp_cmd.add_argument("--format", choices=["markdown", "json"], default="markdown")
    cmp_cmd.add_argument("--fail-on-gap", action="store_true",
                         help="存在任一缺口即返回 1（默认仅在 critical/high 时返回 1）")
    cmp_cmd.set_defaults(func=cmd_compare)

    parser.add_argument("--self-test", action="store_true", help="运行可证伪自检")
    args = parser.parse_args(argv)

    if args.self_test:
        return selftest()
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    return args.func(args)


def cmd_compare(args):
    result = compare(_load(args.source), _load(args.restored))
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render(result))
    if result["verdict"] == "FAIL":
        return 1
    if args.fail_on_gap and result["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
