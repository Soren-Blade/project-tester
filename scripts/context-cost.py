#!/usr/bin/env python3
"""context-cost.py — 测试会话的 token 成本账本（零依赖）

为什么存在
----------
「省 token」在本技能里长期只是一句定性口号（三律：tree < 100 行 / 先信记忆树 /
稳定模块折叠）。定性回答不了三个真问题：开局读记忆树到底花了多少？这次比上次省了
还是亏了？哪个文件是成本大头、值不值得拆？

四个子命令
----------
  estimate <paths...>            估算一组文件的读入成本
  session  --memory <dir>        估算「阶段 0 开局」成本：tree.md + lessons.md + plans 索引
  log      --memory <dir> ...    把一次实测写进 .test-memory/metrics.md
  report   --memory <dir>        汇总账本：轮次、均值、最近几次

口径与诚实边界
--------------
- tokens 是 **chars / 3.2 的估算**，不是任何 tokenizer 的精确值：中文普遍被低估
  （真实约 1.5~2 chars/token），英文偏准。因此它只适合**同一口径下的横向比较**
  （这次与上次谁更贵），不能当账单，也不能用来向用户承诺「省了 N 元」。
- 只读本地文件，不联网、不上报、不代填真实账单。
- 只量「读进来多少」，不评价「测得对不对」——省 token 与测得深是两件事。
- 账本只记**你显式写进去的事件**，不会自己观察到整场会话；漏记就是漏记。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

CHARS_PER_TOKEN = 3.2  # 估算口径：中文偏保守，见文件头「口径与诚实边界」

METRICS_HEADER = """# Token 成本账本（自动生成，勿手改表头）

> 口径：`tokens ≈ chars / 3.2`（估算，非 tokenizer 精确值；中文被低估）。
> 用途：同一口径下的**横向比较**，回答「开局贵不贵、这轮省没省」。
> 写入：`python scripts/context-cost.py log --memory <本项目>/.test-memory --scene "阶段0 开局"`。

| 日期 | 场景 | 读入 | 估算 tokens | 说明 |
|---|---|---|---|---|
"""


# ---------------------------------------------------------------- 基础度量

def read_chars(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="replace"))


def est(chars: int, cpt: float = CHARS_PER_TOKEN) -> int:
    return int(round(chars / cpt))


def tree_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def rel_or_name(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


# ---------------------------------------------------------------- 内存树探测

def memory_files(memory: Path, with_plans: bool = True) -> list[Path]:
    """阶段 0 真正会读的那几份：tree.md + lessons.md + plans 索引（每份档案的 §1/§3 摘要位）。"""
    out: list[Path] = []
    for name in ("tree.md", "lessons.md"):
        p = memory / name
        if p.is_file():
            out.append(p)
    if with_plans:
        pdir = memory / "plans"
        if pdir.is_dir():
            out.extend(sorted(p for p in pdir.glob("*.md") if p.is_file()))
    return out


def cmd_estimate(args: argparse.Namespace) -> int:
    rows = []
    for raw in args.paths:
        p = Path(raw)
        if not p.exists():
            print(f"[WARN] 不存在，跳过：{raw}")
            continue
        chars = read_chars(p)
        rows.append((rel_or_name(p), chars, len(p.read_text(encoding="utf-8", errors="replace").splitlines()), est(chars, args.chars_per_token)))
    if not rows:
        print("[FAIL] 没有可度量的文件")
        return 2
    total_chars = sum(r[1] for r in rows)
    total_tok = sum(r[3] for r in rows)
    if args.json:
        print(json.dumps({
            "chars_per_token": args.chars_per_token,
            "files": [{"path": r[0], "chars": r[1], "lines": r[2], "tokens": r[3]} for r in rows],
            "total_chars": total_chars, "total_tokens": total_tok,
        }, ensure_ascii=False, indent=2))
        return 0
    width = max(len(r[0]) for r in rows)
    for name, chars, lines, tok in rows:
        print(f"{name:<{width}}  {chars:>8} chars  {lines:>5} 行  ≈{tok:>7} tokens")
    print(f"{'合计':<{width}}  {total_chars:>8} chars  {'':>5}     ≈{total_tok:>7} tokens")
    return 0


def cmd_session(args: argparse.Namespace) -> int:
    memory = Path(args.memory)
    files = memory_files(memory)
    skill_files: list[Path] = []
    if args.skill:
        gp = Path(args.skill) / "memory" / "global-lessons.md"
        if gp.is_file():
            skill_files.append(gp)
    allf = files + skill_files
    if not allf:
        print(f"[WARN] {memory} 下没有 tree.md / lessons.md / plans/，本次是冷启动（阶段 1 全量解剖）")
        base = est(args.skill_chars) if args.skill_chars else 0
        print(f"{'技能常驻（global-lessons）':<28} ≈{base:>7} tokens")
        print(f"{'合计（冷启动）':<28} ≈{base:>7} tokens")
        return 0
    rows = []
    for p in allf:
        chars = read_chars(p)
        rows.append((rel_or_name(p), chars, len(p.read_text(encoding="utf-8", errors="replace").splitlines()), est(chars, args.chars_per_token)))
    total = sum(r[3] for r in rows)
    width = max(len(r[0]) for r in rows)
    for name, chars, lines, tok in rows:
        print(f"{name:<{width}}  {chars:>8} chars  {lines:>5} 行  ≈{tok:>7} tokens")
    print(f"{'合计（阶段 0 开局）':<{width}}  {sum(r[1] for r in rows):>8} chars  {'':>5}     ≈{total:>7} tokens")

    tree = memory / "tree.md"
    if tree.is_file():
        n = tree_lines(tree)
        if n > 100:
            print(f"[WARN] tree.md 已 {n} 行，超 100 行上限：先折叠稳定模块或沉细节到 runs/")
        else:
            print(f"[OK] tree.md {n} 行（<100 行预算内）")
    plans = list((memory / "plans").glob("*.md")) if (memory / "plans").is_dir() else []
    if len(plans) > args.plans_warn:
        print(f"[WARN] plans/ 已 {len(plans)} 份档案，阶段 0 全读会变贵 → 先读 tree.md 需求索引定位，只读命中的那份")
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    memory = Path(args.memory)
    memory.mkdir(parents=True, exist_ok=True)
    metrics = memory / "metrics.md"
    paths = [Path(p) for p in args.paths] if args.paths else memory_files(memory)
    paths = [p for p in paths if p.is_file()]
    if not paths:
        print("[FAIL] 没有可记账的文件：先跑一次测试，或用 --paths 指定")
        return 2
    chars = sum(read_chars(p) for p in paths)
    tok = est(chars, args.chars_per_token)
    summary = args.summary or ("+".join(p.name for p in paths[:3]) + (f" 等 {len(paths)} 份" if len(paths) > 3 else ""))
    note = args.note or ""
    row = f"| {args.date or date.today().isoformat()} | {args.scene} | {summary} | ≈{tok} | {note} |\n"

    if not metrics.is_file():
        metrics.write_text(METRICS_HEADER + row, encoding="utf-8")
    else:
        text = metrics.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
        metrics.write_text(text + row, encoding="utf-8")
    print(f"[OK] 已记账：{args.scene} ≈{tok} tokens（{chars} chars / {len(paths)} 份）→ {metrics}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    metrics = Path(args.memory) / "metrics.md"
    if not metrics.is_file():
        print(f"[WARN] 还没有账本：{metrics}（先跑 log 子命令）")
        return 0
    rows = []
    for line in metrics.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[0]):
            continue
        m = re.search(r"(\d+)", cells[3])
        if not m:
            continue
        rows.append((cells[0], cells[1], cells[2], int(m.group(1)), cells[4]))
    if not rows:
        print("[WARN] 账本里没有可解析的记录")
        return 0
    toks = [r[3] for r in rows]
    print(f"记录数 {len(rows)} ｜ 合计 ≈{sum(toks)} tokens ｜ 均值 ≈{sum(toks)//len(toks)} ｜ "
          f"最高 ≈{max(toks)} ｜ 最低 ≈{min(toks)}")
    print("\n最近 5 次：")
    for d, scene, summary, tok, note in rows[-5:]:
        print(f"  {d}  {scene:<12} ≈{tok:>7}  {summary}  {note}")
    if len(toks) >= 4:
        half = len(toks) // 2
        early = sum(toks[:half]) / half
        late = sum(toks[half:]) / (len(toks) - half)
        verdict = "更省" if late < early else "更贵"
        print(f"\n趋势：前 {half} 次均值 ≈{early:.0f} → 后 {len(toks)-half} 次均值 ≈{late:.0f}"
              f"（{verdict} {abs(late-early)/max(early,1):.0%}）")
        print("口径提醒：估算值只做同口径比较；「更省」不等于「测得更好」。")
    return 0


# ---------------------------------------------------------------- 自测

def self_test() -> int:
    fails: list[str] = []

    def check(name: str, cond: bool) -> None:
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    with tempfile.TemporaryDirectory() as td:
        mem = Path(td) / ".test-memory"
        (mem / "plans").mkdir(parents=True)
        (mem / "tree.md").write_text("# 树\n" + "- [✅] 登录\n" * 30, encoding="utf-8")
        (mem / "lessons.md").write_text("- [校验] 服务端校验必带负数\n" * 5, encoding="utf-8")
        (mem / "plans" / "PLAN-1-login.md").write_text("# 档案\n" + "方向\n" * 20, encoding="utf-8")

        files = memory_files(mem)
        check("memory_files 收齐 tree/lessons/plans", len(files) == 3)
        chars = sum(read_chars(p) for p in files)
        check("est() 按 3.2 折算且为整数", est(chars) == int(round(chars / 3.2)))
        check("est() 对 320 chars 给 100 tokens", est(320) == 100)
        check("tree_lines 数行准确", tree_lines(mem / "tree.md") == 31)

        # log → metrics 落盘 → report 能解析
        rc = cmd_log(argparse.Namespace(memory=str(mem), paths=None, chars_per_token=3.2,
                                        scene="阶段0 开局", summary="tree+lessons", note="自测",
                                        date="2026-01-01"))
        metrics = mem / "metrics.md"
        check("log 写入成功", rc == 0 and metrics.is_file())
        check("账本表头含口径声明", "非 tokenizer 精确值" in metrics.read_text(encoding="utf-8"))
        cmd_log(argparse.Namespace(memory=str(mem), paths=None, chars_per_token=3.2,
                                   scene="回归", summary="tree", note="", date="2026-01-02"))
        text = metrics.read_text(encoding="utf-8")
        check("多次 log 追加不覆盖", text.count("2026-01-0") == 2)

        rc = cmd_report(argparse.Namespace(memory=str(mem)))
        check("report 解析账本", rc == 0)

        # 空账本 / 空目录 不应崩
        empty = Path(td) / "empty"
        empty.mkdir()
        check("空目录 session 走冷启动分支", cmd_session(argparse.Namespace(
            memory=str(empty), skill=None, chars_per_token=3.2, skill_chars=8000,
            plans_warn=6)) == 0)
        check("无账本 report 不崩", cmd_report(argparse.Namespace(memory=str(empty))) == 0)

    doc = Path(__file__).read_text(encoding="utf-8")
    check("文档写明估算非精确（诚实边界）", "不是任何 tokenizer 的精确值" in doc)
    check("文档写明不联网", "不联网" in doc)
    check("文档写明只量读入、不评价测试质量", "不评价「测得对不对」" in doc)
    check("场景口径已声明", "CHARS_PER_TOKEN" in doc)

    if fails:
        print(f"[FAIL] {len(fails)} 项自测未通过：{', '.join(fails)}")
        return 1
    print("\n--- SELFTEST GREEN（14 项）---")
    print("注：自测只证明度量与记账逻辑正确，不证明任何一次真实会话的 token 消耗。")
    return 0


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="context-cost.py",
        description="测试会话 token 成本账本（估算口径 chars/3.2，不联网）")
    ap.add_argument("--self-test", action="store_true", help="跑内置自测（14 项）")
    sub = ap.add_subparsers(dest="cmd")

    p1 = sub.add_parser("estimate", help="估算一组文件的读入成本")
    p1.add_argument("paths", nargs="+")
    p1.add_argument("--chars-per-token", type=float, default=CHARS_PER_TOKEN)
    p1.add_argument("--json", action="store_true")

    p2 = sub.add_parser("session", help="估算阶段 0 开局成本")
    p2.add_argument("--memory", required=True)
    p2.add_argument("--skill", default=None, help="技能目录（读 memory/global-lessons.md）")
    p2.add_argument("--skill-chars", type=int, default=0, help="冷启动时技能常驻字符数")
    p2.add_argument("--chars-per-token", type=float, default=CHARS_PER_TOKEN)
    p2.add_argument("--plans-warn", type=int, default=6)

    p3 = sub.add_parser("log", help="记一次账")
    p3.add_argument("--memory", required=True)
    p3.add_argument("--scene", required=True)
    p3.add_argument("--paths", nargs="*", default=None)
    p3.add_argument("--summary", default=None)
    p3.add_argument("--note", default=None)
    p3.add_argument("--date", default=None)
    p3.add_argument("--chars-per-token", type=float, default=CHARS_PER_TOKEN)

    p4 = sub.add_parser("report", help="汇总账本")
    p4.add_argument("--memory", required=True)

    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.cmd == "estimate":
        return cmd_estimate(args)
    if args.cmd == "session":
        return cmd_session(args)
    if args.cmd == "log":
        return cmd_log(args)
    if args.cmd == "report":
        return cmd_report(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
