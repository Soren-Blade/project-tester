#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""project-tester 技能自检（每日升级门禁，见 references/self-evolution.md §3）

用法：python scripts/selfcheck.py
退出码：0 = 全部通过；1 = 存在 FAIL（禁止升版本 / 同步 / 提交）
只做本地确定性检查，不联网、不改文件。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".workbuddy-ai", "__pycache__", ".test-memory", "node_modules"}
errors: list[str] = []
warnings: list[str] = []
passes: list[str] = []


def ok(msg: str) -> None:
    passes.append(msg)


def fail(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def md_files() -> list[Path]:
    out = []
    for p in sorted(ROOT.rglob("*.md")):
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            continue
        out.append(p)
    return out


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        fail(f"{p.name}: 无法按 UTF-8 读取 ({e})")
        return ""


# 1) SKILL.md frontmatter
skill_path = ROOT / "SKILL.md"
skill = read(skill_path)
if not skill.startswith("---"):
    fail("SKILL.md 缺少 YAML frontmatter")
else:
    fm = skill.split("---", 2)[1] if skill.count("---") >= 2 else ""
    for key in ("name", "description", "version"):
        if not re.search(rf"^{key}:\s*\S", fm, re.M):
            fail(f"SKILL.md frontmatter 缺少 {key}")
    if len(re.search(r"^description:\s*(.+)$", fm, re.M).group(1) if re.search(r"^description:\s*(.+)$", fm, re.M) else "") < 60:
        fail("SKILL.md description 过短（触发词可能不足）")
    else:
        ok("SKILL.md frontmatter 完整（name/description/version）")

m = re.search(r"^version:\s*v?(\d+\.\d+\.\d+)\s*$", skill, re.M)
version = f"v{m.group(1)}" if m else None
if not version:
    fail("SKILL.md version 不是 vX.Y.Z 形式")
else:
    ok(f"技能版本 {version}")

# 2) 版本一致性：README 徽章 / CHANGELOG 首条
readme = read(ROOT / "README.md")
changelog = read(ROOT / "CHANGELOG.md")
if version and f"version-{version}" not in readme:
    fail(f"README.md 徽章未同步为 {version}")
else:
    ok("README.md 版本徽章一致")
if version and not re.search(rf"^##\s*\[?{re.escape(version)}\]?", changelog, re.M):
    fail(f"CHANGELOG.md 缺少 {version} 条目")
else:
    ok("CHANGELOG.md 版本条目存在")

# 3) 本地文件引用完整性（反引号中的 references/ assets/ memory/ scripts/ 路径）
ref_re = re.compile(r"`((?:references|assets|memory|scripts)/[A-Za-z0-9_.\-/]+\.(?:md|py|json|sh))`")
missing: set[str] = set()
for p in md_files():
    for rel in ref_re.findall(read(p)):
        if not (ROOT / rel).is_file():
            missing.add(f"{p.relative_to(ROOT).as_posix()} -> {rel}")
if missing:
    for item in sorted(missing):
        fail(f"断链引用: {item}")
else:
    ok("所有本地文件引用均存在")

# 4) 占位资源 URL（前端质量纪律的自身落实）
placeholder = re.compile(r"https?://(?:unsplash|picsum|placehold|via\.placeholder|dummyimage|lorem\.space)", re.I)
for p in md_files():
    if placeholder.search(read(p)):
        fail(f"{p.name}: 含占位资源 URL")
if not any("占位资源" in e for e in errors):
    ok("无占位资源 URL")

# 5) 关键纪律文件仍在且字段齐备
checks = {
    "assets/tree-template.md": ["技能版本", "严重度", "下次待办"],
    "assets/report-template.md": ["PASS / FAIL", "Go / No-Go", "覆盖口径"],
    "assets/bug-report-template.md": ["最小可复现实例", "预期 vs 实际", "环境指纹"],
    "assets/test-plan-template.md": ["风险分", "六维"],
    "assets/release-gate-template.md": ["/12", "回滚预案", "No-Go"],
    "references/self-evolution.md": ["测项目时不自治", "每日升级"],
    "references/quality-gates.md": ["缺陷报告八字段", "Flaky"],
}
for rel, needles in checks.items():
    text = read(ROOT / rel)
    if not text:
        continue
    absent = [n for n in needles if n not in text]
    if absent:
        fail(f"{rel} 缺少关键字段: {', '.join(absent)}")
    else:
        ok(f"{rel} 关键字段齐备")

# 6) 模板行数纪律
tree_tpl = ROOT / "assets/tree-template.md"
if tree_tpl.is_file() and len(read(tree_tpl).splitlines()) >= 100:
    fail("assets/tree-template.md ≥100 行（违反省 token 三律）")
else:
    ok("tree 模板 <100 行")

# 7) 索引覆盖：references/ 下每份手册都被 SKILL.md 或 README 提及
refs = sorted((ROOT / "references").glob("*.md"))
unindexed = [p.name for p in refs if p.name not in skill and p.name not in readme]
if unindexed:
    warn("未被 SKILL.md/README 索引的手册: " + ", ".join(unindexed))
else:
    ok(f"references/ 全部 {len(refs)} 份手册已索引")

# 8) global-lessons 格式（软约束）
gl = read(ROOT / "memory/global-lessons.md")
bad = [ln for ln in gl.splitlines()
       if ln.strip() and not ln.startswith(("#", ">", "-", "|", "`")) and not ln.startswith("[")]
if bad:
    warn(f"global-lessons.md 有 {len(bad)} 行不符合 '[标签] 教训 — 应用：' 约定")
else:
    ok("global-lessons.md 格式基本合规")

# 汇总
print(f"=== project-tester 自检 {version or '(版本未知)'} ===")
for p in passes:
    print(f"[PASS] {p}")
for w in warnings:
    print(f"[WARN] {w}")
for e in errors:
    print(f"[FAIL] {e}")
print(f"--- PASS {len(passes)} / WARN {len(warnings)} / FAIL {len(errors)} ---")
if errors:
    print("结论：BLOCKED —— 禁止升版本、同步与提交，先修复 FAIL。")
    sys.exit(1)
print("结论：GREEN —— 可执行同步与提交。")
sys.exit(0)
