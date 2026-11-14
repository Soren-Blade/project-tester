#!/usr/bin/env python3
"""time-audit.py — 时间/时区正确性离线审计（零依赖）

用途
  scan : 静态扫描源码中的时间反模式（无参 new Date()、'YYYY-MM-DD' 当 UTC、
         naive datetime、固定 86400 当一天、toLocale* 未指定 timeZone、时间字符串比较等），
         输出 markdown 或 JSON。
  dst  : 用 zoneinfo 计算指定时区某年的夏令时转换点，给出「不存在的本地时间（gap）」与
         「重复的本地时间（fold）」；可再用 --at 判断某个每日时刻在转换日是否被跳过/重复。
  --self-test : 用临时夹具证明「坏写法能被检出、好写法不被误报」，并校验 gap/fold 分类逻辑。

诚实边界（必须与结论一起引用）
  * 不联网：只读你给的本地文件与系统时区库，不查 IANA 更新、不请求被测服务。
  * 不代填：不猜被测系统使用哪个时区、不代替运行时验证调度器行为。
  * 不证明：静态命中只是「可疑写法」，**不证明**线上确有缺陷；未命中 **不证明**时间处理正确。
    真正的 DST/过期/排序缺陷必须由实际运行输出证明（R-13）。
  * dst 依赖系统 tzdata / zoneinfo 数据库。不可用时明确报错退出（给出安装提示），
    绝不伪造转换结果；tzdb 版本本身会漂移，跨版本结论需注明 tzdb 版本。

用法
  python time-audit.py scan <path> [--format markdown|json] [--fail-on-gap]
  python time-audit.py dst --zone America/New_York --year 2026 [--at 02:30]
  python time-audit.py --self-test
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone

SKIP_DIRS = {".git", "node_modules", "__pycache__", "dist", "build", ".venv", "venv", "target", "vendor", ".test-memory"}
SKIP_EXT = {".min.js", ".map", ".lock", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".woff", ".woff2", ".ico"}
MAX_BYTES = 1_500_000

# (编号, 级别, 适用语言, 正则, 说明)
# 语言用 "any" 表示不限；说明必须能转成一次运行时验证动作。
SCAN_RULES = [
    ("T-01", "high", {"js", "ts", "jsx", "tsx"},
     r"new\s+Date\s*\(\s*\)",
     "无参 new Date() 直接读墙上时钟：测试无法注入假时钟，断言随运行时刻漂移（应注入 clock）"),
    ("T-02", "high", {"js", "ts", "jsx", "tsx"},
     r"new\s+Date\s*\(\s*['\"]\d{4}-\d{2}-\d{2}['\"]\s*\)",
     "JS 把 'YYYY-MM-DD' 按 UTC 解析：UTC+8 等时区会整体偏移一天（应带显式偏移或按本地历法构造）"),
    ("T-03", "high", {"py"},
     r"\bdatetime\.(?:now|today)\s*\(\s*\)",
     "naive 本地时间入库：夏令时 fold 时段会出现两个相同时间戳，且无法还原时区（应 tz-aware）"),
    ("T-04", "medium", {"py"},
     r"\bdatetime\.utcnow\s*\(\s*\)",
     "utcnow() 返回 naive UTC（Py3.12 起弃用）：序列化后无偏移标记，消费端易误读为本地时间"),
    ("T-05", "high", "any",
     r"\b(?:24\s*\*\s*60\s*\*\s*60|86_?400)\b",
     "固定 86400 秒当「一天」：DST 切换日不是 86400 秒，过期/调度会偏 1 小时（应用日历日加减）"),
    ("T-06", "medium", {"js", "ts", "jsx", "tsx"},
     r"toLocale(?:String|DateString|TimeString)\s*\((?![^)]*timeZone)",
     "toLocale* 未显式 timeZone：输出随运行环境时区漂移，快照与断言不稳定"),
    ("T-07", "high", "any",
     r"\b\w*(?:expire|expiry|expires|deadline|ttl|created_at|updated_at|timestamp|start_at|end_at)\w*\s*(?:<=|<|>=|>)\s*(?:['\"]|new\s+Date|Date\.now|time\.time)",
     "时间用字符串/裸时间戳直接比较：不同偏移、精度或格式会得到错误先后（应先解析为 tz-aware 再比）"),
    ("T-08", "medium", {"sql"},
     r"\b(?:TIMESTAMP|DATETIME)\b(?!\s+WITH\s+TIME\s+ZONE)",
     "时间列类型可能无时区语义（PostgreSQL timestamp / MySQL DATETIME 与 TIMESTAMP 语义不同）：确认存储口径与迁移影响"),
    ("T-09", "medium", {"java"},
     r"\bLocalDateTime\.now\s*\(",
     "Java LocalDateTime 无时区：跨时区与 DST 事件会错位（应用 Instant/ZonedDateTime）"),
    ("T-10", "medium", {"java"},
     r"\bSimpleDateFormat\s*\(",
     "SimpleDateFormat 默认取 JVM 时区且非线程安全：确认是否 setTimeZone 及并发复用"),
]

EXT_LANG = {
    ".js": "js", ".mjs": "js", ".cjs": "js", ".jsx": "jsx",
    ".ts": "ts", ".tsx": "tsx", ".py": "py", ".java": "java",
    ".sql": "sql", ".go": "go",
}


def _iter_files(root):
    if os.path.isfile(root):
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            if any(name.endswith(ext) for ext in SKIP_EXT):
                continue
            yield os.path.join(dirpath, name)


def _read_text(path):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def scan(root):
    findings = []
    scanned = 0
    for path in _iter_files(root):
        lang = EXT_LANG.get(os.path.splitext(path)[1].lower())
        if lang is None:
            continue
        text = _read_text(path)
        if text is None:
            continue
        scanned += 1
        for rule_id, level, langs, pattern, message in SCAN_RULES:
            if langs != "any" and lang not in langs:
                continue
            regex = re.compile(pattern)
            for lineno, line in enumerate(text.splitlines(), 1):
                match = regex.search(line)
                if not match:
                    continue
                findings.append({
                    "id": rule_id,
                    "level": level,
                    "file": path,
                    "line": lineno,
                    "snippet": line.strip()[:160],
                    "message": message,
                })
    return {"root": root, "scanned_files": scanned, "findings": findings}


def render_scan(result):
    lines = ["# 时间/时区静态审计（time-audit.py）", ""]
    lines.append("- 扫描根：`%s`；可解析文件 %d 个；命中 %d 处" % (
        result["root"], result["scanned_files"], len(result["findings"])))
    lines += ["", "| 位置 | 编号 | 级别 | 证据 | 说明 |", "|---|---|---|---|---|"]
    for item in result["findings"]:
        loc = "%s:%d" % (item["file"], item["line"])
        snippet = item["snippet"].replace("|", "\\|").replace("`", "'")
        lines.append("| `%s` | %s | %s | `%s` | %s |" % (loc, item["id"], item["level"], snippet, item["message"]))
    if not result["findings"]:
        lines.append("| — | — | — | 未命中内置反模式 | 未命中不证明正确：仍需运行时 DST/边界实测 |")
    lines += ["", "## 边界", "",
              "- 静态命中是「可疑写法」，不证明线上缺陷；未命中不证明时间处理正确。",
              "- 不联网、不代填、不证明；tzdb 版本与部署时区需另行确认（R-13）。"]
    return "\n".join(lines)


def _fmt_offset(delta):
    total = int(delta.total_seconds())
    sign = "+" if total >= 0 else "-"
    hours, rem = divmod(abs(total), 3600)
    return "UTC%s%02d:%02d" % (sign, hours, rem // 60)


def classify_transition(utc_instant, offset_before, offset_after):
    """给定 UTC 转换时刻与前后 utcoffset，返回 gap/fold 的本地时间窗口。"""
    if offset_after > offset_before:
        kind = "gap"
        start = (utc_instant + offset_before).replace(tzinfo=None)
        end = (utc_instant + offset_after).replace(tzinfo=None)
        note = "本地时间 %s–%s 不存在（春季前跳）" % (start.strftime("%H:%M"), end.strftime("%H:%M"))
    elif offset_after < offset_before:
        kind = "fold"
        start = (utc_instant + offset_after).replace(tzinfo=None)
        end = (utc_instant + offset_before).replace(tzinfo=None)
        note = "本地时间 %s–%s 出现两次（秋季回拨）" % (start.strftime("%H:%M"), end.strftime("%H:%M"))
    else:
        kind = "none"
        start = end = (utc_instant + offset_before).replace(tzinfo=None)
        note = "偏移未变化"
    return {
        "kind": kind,
        "utc": utc_instant.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "offset_before": _fmt_offset(offset_before),
        "offset_after": _fmt_offset(offset_after),
        "local_window": [start.strftime("%Y-%m-%d %H:%M"), end.strftime("%Y-%m-%d %H:%M")],
        "note": note,
    }


def find_transitions(zone, year):
    try:
        from zoneinfo import ZoneInfo
    except ImportError as exc:  # pragma: no cover - 由 dst 命令的显式报错覆盖
        raise SystemExit("FAIL: Python 缺少 zoneinfo 模块：%s" % exc)
    try:
        tz = ZoneInfo(zone)
    except Exception as exc:  # ZoneInfoNotFoundError 在无 tzdata 的 Windows 上最常见
        raise SystemExit(
            "FAIL: 无法加载时区 %r（%s）。\n"
            "  本机 tzdata 不可用；安装后重试：pip install tzdata\n"
            "  或设置环境变量 PYTHONTZPATH 指向 IANA tzdata 编译产物目录。\n"
            "  本工具不会伪造转换结果。" % (zone, exc)
        )

    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    step = timedelta(hours=6)
    transitions = []
    prev = start
    prev_off = prev.astimezone(tz).utcoffset()
    cursor = start + step
    while cursor <= end:
        off = cursor.astimezone(tz).utcoffset()
        if off != prev_off:
            lo, hi = prev, cursor
            while (hi - lo) > timedelta(seconds=1):
                mid = lo + (hi - lo) / 2
                if mid.astimezone(tz).utcoffset() == prev_off:
                    lo = mid
                else:
                    hi = mid
            instant = hi.replace(microsecond=0)
            item = classify_transition(instant, prev_off, off)
            item["year"] = year
            item["zone"] = zone
            transitions.append(item)
            prev_off = off
        prev = cursor
        cursor += step
    return transitions


def at_time_verdict(transitions, hhmm):
    hour, minute = (int(part) for part in hhmm.split(":", 1))
    verdicts = []
    for item in transitions:
        start, end = (datetime.strptime(value, "%Y-%m-%d %H:%M") for value in item["local_window"])
        probe = start.replace(hour=hour, minute=minute)
        if start <= probe < end:
            if item["kind"] == "gap":
                verdicts.append({
                    "zone": item.get("zone", "(未提供)"), "date": start.date().isoformat(), "at": hhmm,
                    "verdict": "该日 %s 不存在（gap）：wall-clock 调度器应跳过或顺延，必须实测其实际行为" % hhmm,
                })
            else:
                verdicts.append({
                    "zone": item.get("zone", "(未提供)"), "date": start.date().isoformat(), "at": hhmm,
                    "verdict": "该日 %s 出现两次（fold）：必须实测任务只执行一次，避免重复扣款/重复通知" % hhmm,
                })
    return verdicts


def cmd_scan(args):
    result = scan(args.path)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_scan(result))
    if result["scanned_files"] == 0:
        print("FAIL: 未扫描到可解析源码（检查路径或扩展名）", file=sys.stderr)
        return 3
    if args.fail_on_gap and result["findings"]:
        return 2
    return 0


def cmd_dst(args):
    transitions = find_transitions(args.zone, args.year)
    if args.format == "json":
        payload = {"zone": args.zone, "year": args.year, "transitions": transitions}
        if args.at:
            payload["at_verdicts"] = at_time_verdict(transitions, args.at)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    lines = ["# DST 转换（time-audit.py）", "", "- 时区：`%s`；年份：%d；转换 %d 次" % (
        args.zone, args.year, len(transitions))]
    lines += ["", "| UTC 时刻 | 偏移 | 类型 | 本地窗口 | 含义 |", "|---|---|---|---|---|"]
    for item in transitions:
        lines.append("| %s | %s → %s | %s | %s – %s | %s |" % (
            item["utc"], item["offset_before"], item["offset_after"], item["kind"],
            item["local_window"][0], item["local_window"][1], item["note"]))
    if not transitions:
        lines.append("| — | — | — | — | 该时区该年无 DST 转换（或 tzdb 不含 DST） |")
    if args.at:
        verdicts = at_time_verdict(transitions, args.at)
        lines += ["", "## 每日 %s 的判定" % args.at, ""]
        if verdicts:
            for item in verdicts:
                lines.append("- %s %s：%s" % (item["date"], item["at"], item["verdict"]))
        else:
            lines.append("- 该年转换日不落在 %s，每日任务不受 gap/fold 影响。" % args.at)
    lines += ["", "## 边界", "",
              "- 结果来自本机 tzdata，版本漂移会改变未来年份的转换规则；结论需注明 tzdb 版本。",
              "- 只回答「本地时间在数学上是否 gap/fold」，不证明调度器实际跳过或去重；后者必须实测。"]
    print("\n".join(lines))
    return 0


def selftest():
    failures = []

    def expect(name, condition):
        if not condition:
            failures.append(name)

    bad_js = (
        "const now = new Date();\n"
        "const d = new Date('2026-03-08');\n"
        "setTimeout(fn, 86400 * 1000);\n"
        "const s = now.toLocaleString();\n"
        "if (user.expires_at < '2026-03-09') { logout(); }\n"
    )
    good_js = (
        "const now = clock.now();\n"
        "const d = new Date('2026-03-08T00:00:00+08:00');\n"
        "const s = now.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });\n"
    )
    bad_py = (
        "from datetime import datetime\n"
        "stamp = datetime.now()\n"
        "other = datetime.utcnow()\n"
        "ttl = 86400\n"
    )
    good_py = (
        "from datetime import datetime, timezone\n"
        "stamp = datetime.now(timezone.utc)\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        for name, body in (("bad.js", bad_js), ("good.js", good_js),
                           ("bad.py", bad_py), ("good.py", good_py)):
            with open(os.path.join(tmp, name), "w", encoding="utf-8") as handle:
                handle.write(body)
        result = scan(tmp)
        by_file = {}
        for item in result["findings"]:
            by_file.setdefault(os.path.basename(item["file"]), set()).add(item["id"])
        expect("bad.js 命中 T-01", "T-01" in by_file.get("bad.js", set()))
        expect("bad.js 命中 T-02", "T-02" in by_file.get("bad.js", set()))
        expect("bad.js 命中 T-05", "T-05" in by_file.get("bad.js", set()))
        expect("bad.js 命中 T-06", "T-06" in by_file.get("bad.js", set()))
        expect("bad.js 命中 T-07", "T-07" in by_file.get("bad.js", set()))
        expect("bad.py 命中 T-03", "T-03" in by_file.get("bad.py", set()))
        expect("bad.py 命中 T-04", "T-04" in by_file.get("bad.py", set()))
        expect("good.js 零误报", not by_file.get("good.js"))
        expect("good.py 零误报", not by_file.get("good.py"))

    spring = classify_transition(
        datetime(2026, 3, 8, 7, 0, tzinfo=timezone.utc),
        timedelta(hours=-5), timedelta(hours=-4))
    expect("gap 分类", spring["kind"] == "gap" and spring["local_window"] == [
        "2026-03-08 02:00", "2026-03-08 03:00"])
    fall = classify_transition(
        datetime(2026, 11, 1, 6, 0, tzinfo=timezone.utc),
        timedelta(hours=-4), timedelta(hours=-5))
    expect("fold 分类", fall["kind"] == "fold" and fall["local_window"] == [
        "2026-11-01 01:00", "2026-11-01 02:00"])
    verdicts = at_time_verdict([spring], "02:30")
    expect("02:30 落在 gap 被识别", len(verdicts) == 1 and "不存在" in verdicts[0]["verdict"])

    if failures:
        print("SELFTEST FAIL: " + ", ".join(failures))
        return 1
    print("SELFTEST GREEN: 12 项断言全过（5 类 JS 反模式 + 2 类 Python 反模式 + 双好样本零误报 + gap/fold/02:30 判定）")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="时间/时区离线审计（不联网、不代填、不证明）")
    sub = parser.add_subparsers(dest="command")

    scan_cmd = sub.add_parser("scan", help="静态扫描时间反模式")
    scan_cmd.add_argument("path", help="文件或目录")
    scan_cmd.add_argument("--format", choices=["markdown", "json"], default="markdown")
    scan_cmd.add_argument("--fail-on-gap", action="store_true", help="有命中即返回非零（门禁用）")
    scan_cmd.set_defaults(func=cmd_scan)

    dst_cmd = sub.add_parser("dst", help="列出时区某年的 DST 转换与 gap/fold")
    dst_cmd.add_argument("--zone", required=True, help="IANA 时区名，如 America/New_York")
    dst_cmd.add_argument("--year", type=int, default=2026)
    dst_cmd.add_argument("--at", help="每日固定时刻 HH:MM，判断是否落在 gap/fold")
    dst_cmd.add_argument("--format", choices=["markdown", "json"], default="markdown")
    dst_cmd.set_defaults(func=cmd_dst)

    parser.add_argument("--self-test", action="store_true", help="运行可证伪自检")
    args = parser.parse_args(argv)

    if args.self_test:
        return selftest()
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
