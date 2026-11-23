#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""project-tester 版本升级写回器（替代 ad-hoc str.replace 补丁脚本）

背景：v1.13.0 / v1.14.0 两次升级用临时 Python 脚本做 `s.replace(old, new)` 补丁，
把上一版的 `## [v1.13.0]` / `## [v1.12.0]` H2 标题顶掉了，README 版本历史表也漏了
两行 —— 因为「插入新版本段」和「同步 10 处版本号」全靠手写字符串匹配。

本脚本只做**结构化、可重复、可校验**的三件事：
  1. 开新版本段：在 CHANGELOG 顶部插入 `## [vX.Y.Z] — YYYY-MM-DD · <标题>` + 六个 H3 骨架
  2. 同步版本号：SKILL.md frontmatter / README 徽章 / README 版本历史表首行
  3. 校验结构：插入后立刻检查「H2 序列严格递减、每段至多一个『治理分类』」，不通过则回滚

用法：
  python scripts/upgrade.py --new-version 1.15.0 --title "路由收口" --dry-run
  python scripts/upgrade.py --new-version 1.15.0 --title "路由收口" --date 2026-11-23
  python scripts/upgrade.py --check            # 只校验当前结构，不改文件
  python scripts/upgrade.py --self-test        # 自测：在临时目录造缺陷，验证能检出

不做（诚实边界）：
  - 不替你写变更说明的内容（六个 H3 只留空骨架，正文由人/主 agent 填）
  - 不猜日期、不猜标题；不给 --date 就用今天（本地时区）
  - 不改 references/ 下任何手册（那是内容工作，不是版本工作）
  - 不 git commit / push；不联网
退出码：0 = 成功或校验通过；1 = 结构校验失败 / 参数错误
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
H2 = re.compile(r"^##\s*\[?v?(\d+\.\d+\.\d+)\]?", re.M)
TITLE = re.compile(r"^#\s+.*·\s*v?(\d+\.\d+\.\d+)\s*$", re.M)
BADGE = re.compile(r"version-v(\d+\.\d+\.\d+)-")
H3_SKELETON = [
    "### 主题",
    "### 动机（来自提案区 / 实战反馈）",
    "### 改动清单（文件 : 做了什么）",
    "### 治理分类（Existing / Enhance / Merge / Match / New）",
    "### 口径诚实（不新增不可证伪的宣称）",
    "### 自检与门禁（selfcheck 结果）",
    "### 提案处置（采纳 / 驳回 + 理由）",
]


class Problem(Exception):
    pass


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def write(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8", newline="\n")


# ---------- 结构校验 ----------
def h2_versions(changelog: str) -> list[str]:
    return H2.findall(changelog)


def check_structure(changelog: str, skill: str, readme: str) -> list[str]:
    """返回问题清单（空 = 通过）。这是门禁本体，--check 与插入后都跑它。"""
    problems: list[str] = []

    vers = h2_versions(changelog)
    if not vers:
        problems.append("CHANGELOG 未识别到任何 `## [vX.Y.Z]` 版本标题")
        return problems

    # 1) 严格递减（同版本不得重复出现）
    for prev, cur in zip(vers, vers[1:]):
        if tuple(int(x) for x in cur.split(".")) >= tuple(int(x) for x in prev.split(".")):
            problems.append(f"版本标题顺序异常：{prev} 之后出现 {cur}（应严格递减）")
    dup = {v for v in vers if vers.count(v) > 1}
    if dup:
        problems.append("版本标题重复：" + ", ".join(sorted(dup)))

    # 2) 每个版本段内 `### 治理分类` 至多出现一次
    #    上一版 H2 被顶掉时，两个版本的 H3 组会挤在同一段里 —— 这是 v1.13/v1.14 的真实故障。
    cur_ver = None
    seen: dict[str, int] = {}
    for ln in changelog.splitlines():
        m = H2.match(ln)
        if m:
            cur_ver = m.group(1)
        elif ln.startswith("### 治理分类") and cur_ver:
            seen[cur_ver] = seen.get(cur_ver, 0) + 1
    for ver, n in seen.items():
        if n > 1:
            problems.append(f"v{ver} 段内出现 {n} 个『### 治理分类』（上一版 H2 标题可能被顶掉）")

    # 3) SKILL.md 标题版本 == frontmatter 版本 == CHANGELOG 首条
    fm = re.search(r"^version:\s*v?(\d+\.\d+\.\d+)\s*$", skill, re.M)
    title = TITLE.search(skill)
    if not fm:
        problems.append("SKILL.md frontmatter 缺 version")
    if title and fm and title.group(1) != fm.group(1):
        problems.append(f"SKILL.md 标题版本 v{title.group(1)} ≠ frontmatter v{fm.group(1)}")
    if fm and vers and fm.group(1) != vers[0]:
        problems.append(f"CHANGELOG 首条 v{vers[0]} ≠ SKILL.md v{fm.group(1)}")

    # 4) README 徽章
    badge = BADGE.search(readme)
    if not badge:
        problems.append("README 缺 `version-vX.Y.Z` 徽章")
    elif fm and badge.group(1) != fm.group(1):
        problems.append(f"README 徽章 v{badge.group(1)} ≠ SKILL.md v{fm.group(1)}")

    # 5) README 版本历史表覆盖 CHANGELOG 的每个版本
    marker = "## 版本历史"
    if marker not in readme:
        problems.append("README 缺「## 版本历史」段")
    else:
        table = readme.split(marker, 1)[1]
        rows = set(re.findall(r"v?(\d+\.\d+\.\d+)", table))
        missing = [v for v in vers if v not in rows]
        if missing:
            problems.append("README 版本历史表缺行：" + ", ".join(f"v{v}" for v in missing))

    return problems


# ---------- 开新版本段 ----------
def insert_version(changelog: str, version: str, date: str, title: str) -> str:
    first = H2.search(changelog)
    if not first:
        raise Problem("CHANGELOG 找不到任何版本标题，无法定位插入点")
    head = changelog[: first.start()]
    block = [f"## [v{version}] — {date} · {title}", ""] + [h + " " for h in H3_SKELETON] + [""]
    body = "\n".join(block) + "\n"
    return head + body + changelog[first.start():]


def sync_versions(skill: str, readme: str, old: str, new: str) -> tuple[str, str]:
    skill = re.sub(rf"^(version:\s*)v?{re.escape(old)}\s*$", rf"\g<1>{new}", skill, count=1, flags=re.M)
    skill = re.sub(rf"^(#\s+.*·\s*)v?{re.escape(old)}\s*$", rf"\g<1>v{new}", skill, count=1, flags=re.M)
    readme = readme.replace(f"version-v{old}", f"version-v{new}")
    return skill, readme


def current_version(skill: str) -> str:
    m = re.search(r"^version:\s*v?(\d+\.\d+\.\d+)\s*$", skill, re.M)
    if not m:
        raise Problem("SKILL.md frontmatter 缺 version，无法确定当前版本")
    return m.group(1)


# ---------- 自测 ----------
GOOD_CL = """# 变更记录

## [v1.2.0] — 2026-01-02 · 二版

### 治理分类（Existing / Enhance / Merge / Match / New） x

## [v1.1.0] — 2026-01-01 · 一版

### 治理分类（Existing / Enhance / Merge / Match / New） y
"""
GOOD_SKILL = "---\nname: x\nversion: 1.2.0\ndescription: " + "d" * 80 + "\n---\n\n# T · v1.2.0\n"
GOOD_README = "# R\n\n![b](https://x/badge/version-v1.2.0-blue)\n\n## 版本历史\n\n| v1.2.0 | a |\n| v1.1.0 | b |\n"
BAD_CL_ORPHAN = GOOD_CL.replace(
    "### 治理分类（Existing / Enhance / Merge / Match / New） y",
    "### 治理分类（Existing / Enhance / Merge / Match / New） y\n\n## 阶段\n\n### 治理分类（Existing / Enhance / Merge / Match / New） z",
)


def self_test() -> int:
    print("=== upgrade.py 自测 ===")
    failures = 0

    def expect(name: str, cond: bool) -> None:
        nonlocal failures
        print(("[PASS] " if cond else "[FAIL] ") + name)
        if not cond:
            failures += 1

    expect("正常结构无问题", check_structure(GOOD_CL, GOOD_SKILL, GOOD_README) == [])

    # 标题被顶掉（同一段两个「治理分类」）
    p = check_structure(BAD_CL_ORPHAN, GOOD_SKILL, GOOD_README)
    expect("能检出『上一版 H2 被顶掉』", any("治理分类" in x for x in p))

    # 顺序反转
    rev = GOOD_CL.replace("## [v1.2.0]", "## [v0.9.0]")
    p = check_structure(rev, GOOD_SKILL, GOOD_README)
    expect("能检出标题顺序异常", any("顺序" in x for x in p))

    # README 漏行
    p = check_structure(GOOD_CL, GOOD_SKILL, GOOD_README.replace("| v1.1.0 | b |\n", ""))
    expect("能检出 README 版本表缺行", any("缺行" in x for x in p))

    # 徽章不一致
    p = check_structure(GOOD_CL, GOOD_SKILL, GOOD_README.replace("version-v1.2.0", "version-v1.1.0"))
    expect("能检出 README 徽章不同步", any("徽章" in x for x in p))

    # 标题/frontmatter 不一致
    p = check_structure(GOOD_CL, GOOD_SKILL.replace("# T · v1.2.0", "# T · v1.1.9"), GOOD_README)
    expect("能检出 SKILL 标题版本漂移", any("标题版本" in x for x in p))

    # 插入 + 同步后结构仍自洽（端到端，跑在临时目录）
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "CHANGELOG.md").write_text(GOOD_CL, encoding="utf-8")
        (tmp / "SKILL.md").write_text(GOOD_SKILL, encoding="utf-8")
        (tmp / "README.md").write_text(GOOD_README, encoding="utf-8")
        cl = read(tmp / "CHANGELOG.md")
        cl2 = insert_version(cl, "1.3.0", "2026-01-03", "三版")
        sk, rd = sync_versions(GOOD_SKILL, GOOD_README, "1.2.0", "1.3.0")
        rd = rd.replace("## 版本历史\n\n", "## 版本历史\n\n| v1.3.0 | c |\n")
        expect("开新版本段后结构自洽", check_structure(cl2, sk, rd) == [])
        expect("新段落排在旧段落之前", cl2.index("v1.3.0") < cl2.index("v1.2.0"))

    print(f"--- SELFTEST {'GREEN' if failures == 0 else 'RED'} ({failures} failed) ---")
    return 0 if failures == 0 else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="project-tester 版本升级写回器")
    ap.add_argument("--new-version", help="要开的新版本，如 1.15.0")
    ap.add_argument("--title", default="", help="版本标题（写进 ## [vX.Y.Z] — 日期 · 标题）")
    ap.add_argument("--date", default="", help="日期 YYYY-MM-DD，默认今天")
    ap.add_argument("--check", action="store_true", help="只校验结构，不改文件")
    ap.add_argument("--dry-run", action="store_true", help="打印将要做的事，不落盘")
    ap.add_argument("--self-test", action="store_true", help="自测")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    cl_p, sk_p, rd_p = ROOT / "CHANGELOG.md", ROOT / "SKILL.md", ROOT / "README.md"
    for p in (cl_p, sk_p, rd_p):
        if not p.is_file():
            print(f"[FAIL] 缺文件：{p}")
            return 1
    changelog, skill, readme = read(cl_p), read(sk_p), read(rd_p)

    if args.check or not args.new_version:
        problems = check_structure(changelog, skill, readme)
        for x in problems:
            print(f"[FAIL] {x}")
        print(f"--- 结构校验：{'GREEN' if not problems else 'BLOCKED'} ---")
        return 0 if not problems else 1

    new = args.new_version.lstrip("v")
    if not SEMVER.match(new):
        print(f"[FAIL] 版本号格式错误：{args.new_version}（要 X.Y.Z）")
        return 1
    old = current_version(skill)
    if tuple(int(x) for x in new.split(".")) <= tuple(int(x) for x in old.split(".")):
        print(f"[FAIL] 新版本 {new} 必须大于当前 {old}")
        return 1
    title = args.title.strip() or f"每日升级 · v{new}"
    date = args.date.strip() or dt.date.today().isoformat()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        print(f"[FAIL] 日期格式错误：{date}（要 YYYY-MM-DD）")
        return 1

    new_cl = insert_version(changelog, new, date, title)
    new_sk, new_rd = sync_versions(skill, readme, old, new)
    problems = check_structure(new_cl, new_sk, new_rd)
    if problems:
        for x in problems:
            print(f"[FAIL] {x}")
        print("--- 未写入：插入后结构校验失败（已放弃改动） ---")
        return 1

    if args.dry_run:
        print(f"[DRY-RUN] CHANGELOG: 在 v{old} 前插入 ## [v{new}] — {date} · {title}")
        print(f"[DRY-RUN] SKILL.md : version {old} -> {new}（含 H1 标题）")
        print(f"[DRY-RUN] README   : 徽章 version-v{old} -> version-v{new}")
        print("[DRY-RUN] 提醒：README 版本历史表需手工加一行（脚本不猜摘要）")
        return 0

    backup = {p: p.read_text(encoding="utf-8") for p in (cl_p, sk_p, rd_p)}
    try:
        write(cl_p, new_cl)
        write(sk_p, new_sk)
        write(rd_p, new_rd)
        if check_structure(read(cl_p), read(sk_p), read(rd_p)):
            raise Problem("落盘后校验失败")
    except Exception as e:  # 回滚，绝不留下半坏状态
        for p, text in backup.items():
            p.write_text(text, encoding="utf-8")
        print(f"[FAIL] 写入异常已回滚：{e}")
        return 1

    print(f"[OK] 已开 v{new}：CHANGELOG 骨架 + SKILL.md 版本号 + README 徽章")
    print(f"[NEXT] 1) 填 CHANGELOG 六个 H3 的正文  2) README 版本历史表加一行  3) python scripts/selfcheck.py")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Problem as e:
        print(f"[FAIL] {e}")
        sys.exit(1)
