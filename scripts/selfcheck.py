#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""project-tester 技能自检（每日升级门禁，见 references/self-evolution.md §3）

用法：python scripts/selfcheck.py
退出码：0 = 全部通过；1 = 存在 FAIL（禁止升版本 / 同步 / 提交）
只做本地确定性检查，不联网、不改文件。

检查项：frontmatter / 版本一致 / 本地引用完整性 / 占位资源 URL /
关键字段 / 模板行数 / 索引覆盖 / **路由闭环（孤儿文档）** / **可证伪规则同步** /
**报告证据矩阵同步（§7d）** / **规则例外声明（§7e）** /
**脚本可证伪性静态门禁（§7f，v1.5）** / global-lessons 格式。
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
    "assets/supply-chain-evidence-template.md": ["R-3", "sha256", "provenance"],
    "assets/i18n-matrix-template.md": ["locale", "RTL", "伪本地化"],
    "assets/tenant-isolation-matrix-template.md": ["R-4", "否定路径", "BLOCKED"],
    "assets/contract-evolution-matrix-template.md": ["R-5", "oasdiff", "can-i-deploy"],
    "assets/privacy-matrix-template.md": ["R-6", "PII", "删除权"],
    "assets/test-effectiveness-template.md": ["DORA", "flaky", "变异得分", "ROI", "建设成本"],
    "assets/accessibility-matrix-template.md": ["R-7", "WCAG 2.2", "incomplete", "读屏"],
    "assets/device-matrix-template.md": ["R-8", "real", "设备矩阵", "网络档位"],
    "assets/evidence-chain-template.md": ["R-9", "sha256", "控制项", "不适用", "不得"],
    "references/evidence-chain-audit.md": ["R-9", "PROV", "OSCAL", "in-toto", "不适用"],
    "references/feature-flag-testing.md": ["R-10", "kill-switch", "灰度", "不适用", "不得"],
    "assets/flag-rollout-matrix-template.md": ["R-10", "开关", "灰度", "不适用", "不得"],
    "references/test-data-management.md": ["R-11", "合成数据", "脱敏", "不适用", "不得"],
    "assets/test-data-matrix-template.md": ["R-11", "合成数据", "脱敏", "不适用", "不得"],
    "references/auth-session-testing.md": ["R-12", "ASVS 5.0", "RFC 8725", "RFC 9700", "不得"],
    "assets/auth-matrix-template.md": ["R-12", "J1", "S1", "F1", "不适用"],
    "references/time-correctness-testing.md": ["R-13", "DST", "tzdata", "RFC 3339", "不得"],
    "assets/time-matrix-template.md": ["R-13", "DST", "gap", "fold", "不适用"],
    "references/backup-recovery-testing.md": ["R-14", "RPO", "RTO", "PITR", "不得"],
    "assets/restore-drill-template.md": ["R-14", "RPO", "RTO", "sha256", "不适用"],
    "references/money-correctness-testing.md": ["R-15", "ISO 4217", "exponent", "舍入", "不适用", "不得"],
    "assets/money-matrix-template.md": ["R-15", "exponent", "舍入", "分摊", "不适用", "不得"],
    "references/webhook-delivery-testing.md": ["R-16", "Standard Webhooks", "event_id", "DLQ", "不适用", "不得"],
    "assets/webhook-delivery-matrix-template.md": ["R-16", "签名", "幂等", "DLQ", "不适用", "不得"],
    "references/cache-freshness-testing.md": ["R-17", "Cache-Control", "Cache-Status", "不适用", "不得"],
    "assets/cache-freshness-matrix-template.md": ["R-17", "不适用", "不得"],
    "references/file-upload-download-testing.md": ["R-18", "魔数", "presigned", "不适用", "不得"],
    "assets/upload-security-matrix-template.md": ["R-18", "不适用", "不得"],
    "references/query-pagination-testing.md": ["R-19", "keyset", "cursor", "total", "不适用", "不得"],
    "assets/query-pagination-matrix-template.md": ["R-19", "遍历", "total", "不适用", "不得"],
    "references/error-contract-testing.md": ["R-20", "RFC 9457", "trace_id", "CWE-209", "不适用", "不得"],
    "assets/error-contract-matrix-template.md": ["R-20", "trace_id", "不适用", "不得"],
    "references/search-quality-testing.md": ["R-21", "nDCG", "qrels", "零结果", "不适用", "不得"],
    "assets/search-quality-matrix-template.md": ["R-21", "nDCG", "qrels", "不适用", "不得"],
    "references/metrics-correctness-testing.md": ["R-22", "分子", "分母", "对账", "SRM", "不适用", "不得"],
    "assets/metrics-correctness-matrix-template.md": ["R-22", "分子", "分母", "对账", "不适用", "不得"],
    "references/idempotency-concurrency-testing.md": ["R-23", "不变量", "幂等键", "并发", "不适用", "不得"],
    "assets/idempotency-concurrency-matrix-template.md": ["R-23", "不变量", "幂等键", "不适用", "不得"],
    "references/llm-eval-testing.md": ["R-24", "评测集", "判定器", "不适用", "不得"],
    "assets/llm-eval-matrix-template.md": ["R-24", "评测集", "不适用", "不得"],
    "references/mobile-app-testing.md": ["R-25", "权限", "深链", "不适用", "不得"],
    "assets/mobile-app-matrix-template.md": ["R-25", "权限", "不适用", "不得"],
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

# 7) 索引覆盖：references/ 下每份手册都被 SKILL.md / routing.md / README 提及
#    v1.15.0 起路由单一事实源是 references/routing.md，SKILL.md 只留指针（体积预算）。
routing = read(ROOT / "references/routing.md")
refs = sorted((ROOT / "references").glob("*.md"))
index_pool = skill + readme + routing
unindexed = [p.name for p in refs if p.name not in index_pool]
if unindexed:
    warn("未被 SKILL.md/routing.md/README 索引的手册: " + ", ".join(unindexed))
else:
    ok(f"references/ 全部 {len(refs)} 份手册已索引")

# 7a) 工具表登记：scripts/ 下每个脚本都必须在 references/tools.md 有一行（v1.12 新增）
#     背景：v1.10/v1.11 的 4 个脚本长期没进 tools.md，手册写了工具表却查不到命令。
tools_doc = read(ROOT / "references/tools.md")
script_files = sorted((ROOT / "scripts").glob("*.py"))
missing_tools = [p.name for p in script_files if p.name not in tools_doc]
if missing_tools:
    fail("references/tools.md 未登记脚本: " + ", ".join(missing_tools))
else:
    ok(f"references/tools.md 已登记全部 {len(script_files)} 个脚本")

# 7b) 路由闭环（孤儿文档门禁）：专项手册必须同时出现在 references/routing.md §3 与
#     dissect.md §8 路由表。routing.md 是 v1.15.0 起的单一事实源；dissect §8 保留为
#     阶段 1 的项目形态视图，两者集合必须相等（7j 强制），否则会各自漂移。
CORE_REFS = {
    "dissect.md", "tools.md", "personas.md", "test-design.md", "routing.md",
    "memory-tree.md", "evolution.md", "self-evolution.md", "quality-gates.md",
}
dissect = read(ROOT / "references/dissect.md")
route_marker = "## 8. 项目形态 → 能力层路由"
if route_marker in dissect:
    route_section = dissect.split(route_marker, 1)[1].split("## 产出格式", 1)[0]
else:
    route_section = ""
    fail("references/dissect.md 缺少 §8 路由表，无法校验孤儿文档")
if "## 3." in routing:
    routing_section = routing
else:
    routing_section = ""
    fail("references/routing.md 缺少 §3 专项路由表，无法校验孤儿文档")
orphans: list[str] = []
special_refs = [p for p in refs if p.name not in CORE_REFS]
for p in special_refs:
    if p.name not in route_section:
        orphans.append(f"{p.name}: 缺 dissect.md §8 路由")
    elif p.name not in routing_section:
        orphans.append(f"{p.name}: 缺 routing.md 专项路由")
    elif p.name not in index_pool:
        orphans.append(f"{p.name}: 缺 SKILL.md/routing.md 索引")
if orphans:
    for item in sorted(orphans):
        fail(f"孤儿文档: {item}")
else:
    ok(f"路由闭环：{len(special_refs)} 份专项手册均有 routing.md 路由 + dissect §8 视图 + 索引")

# 7c) 可证伪规则同步（双向）：SKILL.md 定义集与 quality-gates.md 引用集必须相等
#     单向检查挡不住「悄悄删掉一条规则」，所以两边都查。
rules = sorted(set(re.findall(r"\*\*(R-\d+)\s", skill)))
qg = read(ROOT / "references/quality-gates.md")
qg_rules = sorted(set(re.findall(r"R-\d+", qg)))
unsynced = [r for r in rules if r not in qg_rules]
orphan_qg = [r for r in qg_rules if r not in rules]
if len(rules) < 2:
    fail(f"SKILL.md 可证伪规则不足（仅识别到 {len(rules)} 条）")
elif unsynced:
    fail("可证伪规则未接入 quality-gates.md: " + ", ".join(unsynced))
elif orphan_qg:
    fail("quality-gates.md 出现 SKILL.md 未定义的规则（可能被悄悄删除或编号写错）: " + ", ".join(orphan_qg))
else:
    ok(f"可证伪规则双向同步：{', '.join(rules)} 共 {len(rules)} 条，SKILL.md 与 quality-gates.md 集合一致")

# 7d) 报告证据矩阵同步：证据矩阵**表格行**必须逐条覆盖 SKILL.md 定义的全部规则。
#     v1.5 负向测试发现：只统计整段里的 R-N 会被说明文字中的编号蒙混（删掉 R-9 表格行
#     仍判 PASS），因此改为只认 `| R-N ` 开头的表格行；说明段另查「未定义编号」。
report_tpl = read(ROOT / "assets/report-template.md")
matrix_marker = "## 证据矩阵"
if matrix_marker in report_tpl:
    matrix_section = report_tpl.split(matrix_marker, 1)[1].split("\n## ", 1)[0]
else:
    matrix_section = ""
    fail("assets/report-template.md 缺少「## 证据矩阵」段，无法校验规则覆盖")
row_re = re.compile(r"^\|\s*(R-\d+)\s")
matrix_rules = sorted({m.group(1) for ln in matrix_section.splitlines()
                       for m in [row_re.match(ln)] if m})
missing_matrix = [r for r in rules if r not in matrix_rules]
extra_matrix = [r for r in matrix_rules if r not in rules]
stray = [r for r in sorted(set(re.findall(r"R-\d+", matrix_section))) if r not in rules]
if missing_matrix:
    fail("报告证据矩阵缺少规则表格行: " + ", ".join(missing_matrix))
elif extra_matrix or stray:
    fail("报告证据矩阵/说明段出现 SKILL.md 未定义的规则: "
         + ", ".join(sorted(set(extra_matrix + stray))))
else:
    ok(f"报告证据矩阵同步：{', '.join(matrix_rules)} 共 {len(matrix_rules)} 条表格行，与 SKILL.md 规则集一致")

# 7e) 规则例外声明：每条规则定义行都必须写清「不适用时不得冒充通过」的降级写法。
#     只加一句「要有证据」而不写禁止冒充声明，规则仍不可证伪。
rule_rows = [ln for ln in skill.splitlines() if re.match(r"^\|\s*\*\*R-\d+\s", ln)]
if len(rule_rows) != len(rules):
    fail(f"SKILL.md 规则表行数 {len(rule_rows)} 与规则集 {len(rules)} 不一致（漏定义或编号重复）")
else:
    bad_rows = [re.search(r"R-\d+", ln).group(0) for ln in rule_rows if "不得" not in ln]
    if bad_rows:
        fail("规则缺少「不适用时的禁止冒充声明」（须含『不得』）: " + ", ".join(bad_rows))
    else:
        ok(f"规则例外声明齐备：{len(rule_rows)} 条规则均写清禁止冒充的降级写法")

# 7f) 脚本可证伪性静态门禁（v1.5）：新增可执行脚本必须自带 --self-test 与诚实边界声明。
#     「加了个脚本」只证明静态记录；能检出自己造的假缺陷、且明确写出不越界声明，
#     才允许作为交付证据。运行时另须人工执行两个 --self-test 并确认退出码 0。
SCRIPT_GATES = {
    "scripts/evidence-audit.py": [
        "--self-test", "SELFTEST GREEN", "--fail-on-gap",
        "dangling_reference", "unresolvable_anchor", "stale_evidence",
        "pass_without_proof", "unclassified_conclusion", "不证明",
    ],
    "scripts/device-matrix.py": [
        "--self-test", "SELFTEST GREEN", "CRUX_CAVEAT", "数据源未登记",
        "不联网", "不代填",
    ],
    "scripts/test-data-gen.py": [
        "--self-test", "SELFTEST GREEN", "deterministic", "seed", "mask",
        "不联网", "不代填", "不冒充", "不保证无泄漏",
    ],
    "scripts/jwt-audit.py": [
        "--self-test", "SELFTEST GREEN", "alg=none", "kid", "jku",
        "不联网", "不代填", "不冒充", "不证明",
    ],
    "scripts/time-audit.py": [
        "--self-test", "SELFTEST GREEN", "--fail-on-gap", "DST",
        "gap", "fold", "不联网", "不代填",
    ],
    "scripts/restore-audit.py": [
        "--self-test", "SELFTEST GREEN", "--fail-on-gap", "RST-",
        "不联网", "不代填", "不证明",
    ],
    "scripts/money-audit.py": [
        "--self-test", "SELFTEST GREEN", "--fail-on-gap", "MO-",
        "LG-", "exponent", "不联网", "不代填", "不证明",
    ],
    "scripts/webhook-audit.py": [
        "--self-test", "SELFTEST GREEN", "WH-", "hmac", "standard",
        "stripe", "不联网", "不代填", "不证明",
    ],
    "scripts/cache-audit.py": [
        "--self-test", "SELFTEST GREEN", "--fail-on-gap", "CA-",
        "Cache-Status", "Vary", "不联网", "不代填", "不证明",
    ],
    "scripts/upload-audit.py": [
        "--self-test", "SELFTEST GREEN", "--fail-on-gap", "UA-",
        "magic", "presign", "不联网", "不代填", "不证明",
    ],
    "scripts/query-audit.py": [
        "--self-test", "SELFTEST GREEN", "--fail-on-gap", "QP-",
        "keyset", "collation", "不联网", "不代填", "不证明",
    ],
    "scripts/error-audit.py": [
        "--self-test", "SELFTEST GREEN", "--fail-on-gap", "EC-",
        "stack", "Retry-After", "不联网", "不代填", "不证明",
    ],
    "scripts/search-audit.py": [
        "--self-test", "SELFTEST GREEN", "--fail-on-gap", "SR-",
        "nDCG", "qrels", "不联网", "不代填", "不证明",
    ],
    "scripts/metric-audit.py": [
        "--self-test", "SELFTEST GREEN", "--fail-on-gap", "MA-",
        "recon", "SRM", "不联网", "不代填", "不证明",
    ],
    "scripts/concurrency-audit.py": [
        "--self-test", "SELFTEST GREEN", "--fail-on-gap", "CC-",
        "duplicate_side_effect", "multi_resource", "不联网", "不代填", "不证明",
    ],
    "scripts/llm-eval-audit.py": [
        "--self-test", "SELFTEST GREEN", "--fail-on-gap", "LE-",
        "Wilson", "McNemar", "--include-docs", "不联网", "不代填", "不证明",
    ],
    "scripts/mobile-audit.py": [
        "--self-test", "SELFTEST GREEN", "--fail-on-gap", "MB-01", "MB-20",
        "不联网", "不代填", "不证明", "0 命中也不证明无缺陷",
    ],
    "scripts/upgrade.py": [
        "--self-test", "SELFTEST", "--check", "check_structure",
        "治理分类", "不联网", "回滚",
    ],
    "scripts/context-cost.py": [
        "--self-test", "SELFTEST GREEN", "CHARS_PER_TOKEN", "metrics.md",
        "不是任何 tokenizer 的精确值", "不联网", "不评价「测得对不对」",
        "只适合**同一口径下的横向比较**",
    ],
}
for rel, needles in SCRIPT_GATES.items():
    sp = ROOT / rel
    if not sp.is_file():
        fail(f"{rel} 缺失：脚本可证伪性门禁无法校验")
        continue
    stext = read(sp)
    absent = [n for n in needles if n not in stext]
    if absent:
        fail(f"{rel} 缺少可证伪性 / 诚实边界关键字段: {', '.join(absent)}")
    else:
        ok(f"{rel} 自带 --self-test 与诚实边界声明（§7f）")

# 7g) CHANGELOG 版本层级完整性（v1.15.0 新增）
#     回归来源：v1.13.0 / v1.14.0 两次升级用临时 str.replace 脚本打补丁，把上一版的
#     `## [v1.13.0]` / `## [v1.12.0]` H2 标题顶掉，两个版本的正文成了挂在 v1.14 下的孤儿段。
#     旧门禁只查「当前版本条目存在」，对历史序列断裂完全无感。
h2_re = re.compile(r"^##\s*\[?v?(\d+\.\d+\.\d+)\]?", re.M)
cl_versions = h2_re.findall(changelog)
if not cl_versions:
    fail("CHANGELOG.md 未识别到任何 `## [vX.Y.Z]` 版本标题（层级无法校验）")
else:
    rev_bad = [f"{a} → {b}" for a, b in zip(cl_versions, cl_versions[1:])
               if tuple(int(x) for x in b.split(".")) >= tuple(int(x) for x in a.split("."))]
    dup_ver = sorted({v for v in cl_versions if cl_versions.count(v) > 1})
    h3_seen: dict[str, int] = {}
    cur_ver = None
    for ln in changelog.splitlines():
        m2 = h2_re.match(ln)
        if m2:
            cur_ver = m2.group(1)
        elif ln.startswith("### 治理分类") and cur_ver:
            h3_seen[cur_ver] = h3_seen.get(cur_ver, 0) + 1
    orphan_blocks = [f"v{v}（{n} 次）" for v, n in h3_seen.items() if n > 1]
    if rev_bad:
        fail("CHANGELOG 版本标题顺序异常（应严格递减）: " + ", ".join(rev_bad))
    elif dup_ver:
        fail("CHANGELOG 版本标题重复: " + ", ".join(dup_ver))
    elif orphan_blocks:
        fail("CHANGELOG 版本段内出现重复『### 治理分类』—— 上一版 H2 标题可能被顶掉: "
             + ", ".join(orphan_blocks))
    else:
        ok(f"CHANGELOG 版本层级完整：{len(cl_versions)} 个 H2 严格递减，无孤儿段")

# 7h) README 版本历史表覆盖 CHANGELOG 的每个版本（v1.15.0 新增）
#     回归来源：v1.9.0 与 v1.7.0 两次升级没往 README 表里补行，表内直接跳版。
vh_marker = "## 版本历史"
if vh_marker not in readme:
    fail("README.md 缺少「## 版本历史」段（无法校验版本表）")
elif not cl_versions:
    warn("CHANGELOG 版本标题未识别，跳过 README 版本表校验")
else:
    vh_table = readme.split(vh_marker, 1)[1]
    # 只认表格行的第一个单元格：散文里提到「v1.9.0」不算补过行
    # （v1.15.0 实测踩过：版本历史表头下方的说明文字写了「补回 v1.9.0 与 v1.7.0 两行」，
    #   旧的全文 regex 因此误判为表内已有这些版本）
    vh_versions = set()
    for ln in vh_table.splitlines():
        row = ln.strip()
        if not row.startswith("|"):
            continue
        cell = row.strip("|").split("|")[0].strip().lstrip("vV")
        if re.fullmatch(r"\d+\.\d+\.\d+", cell):
            vh_versions.add(cell)
    missing_rows = [v for v in cl_versions if v not in vh_versions]
    if missing_rows:
        fail("README 版本历史表缺行: " + ", ".join(f"v{v}" for v in missing_rows))
    else:
        ok(f"README 版本历史表覆盖全部 {len(cl_versions)} 个已发布版本")

# 7i) SKILL.md 体积与 description 预算（v1.15.0 新增）
#     回归来源：v1.14.0 的 SKILL.md 达 64,898 chars，技能加载时工具输出被截断
#     （`Omitted 20591 bytes`），规则表尾部在真实加载中有丢失风险；description 4,433 chars
#     在会话技能目录里同样被截断。体积超标 = 规则不可靠送达，属 FAIL 级问题。
skill_chars = len(skill)
if skill_chars > 26000:
    fail(f"SKILL.md 体积 {skill_chars} chars 超硬上限 26,000（加载会被截断，规则不可靠送达）")
elif skill_chars > 22000:
    warn(f"SKILL.md 体积 {skill_chars} chars 超建议上限 22,000（接近截断风险）")
else:
    ok(f"SKILL.md 体积 {skill_chars} chars（< 22,000 预算，加载不截断）")
desc_m = re.search(r"^description:\s*(.+)$", (skill.split("---", 2)[1] if skill.count("---") >= 2 else ""), re.M)
if desc_m and len(desc_m.group(1)) > 1024:
    fail(f"SKILL.md description 长 {len(desc_m.group(1))} chars，超 skill 规范上限 1024（会被截断）")
elif desc_m:
    ok(f"SKILL.md description {len(desc_m.group(1))} chars（< 1024，不被截断）")

# 7j) routing.md ↔ dissect §8 集合一致（v1.15.0 新增）
#     routing.md 是路由单一事实源；dissect §8 是阶段 1 的项目形态视图。两份清单各写一遍，
#     只靠「都在」挡不住新增手册只补了一处 —— 必须集合相等。
special_names = {p.name for p in special_refs} if "special_refs" in dir() else set()
if special_names and route_section and routing_section:
    in_dissect = {n for n in special_names if n in route_section}
    in_routing = {n for n in special_names if n in routing_section}
    only_d = sorted(in_dissect - in_routing)
    only_r = sorted(in_routing - in_dissect)
    if only_d:
        fail("手册只在 dissect §8、未进 routing.md: " + ", ".join(only_d))
    elif only_r:
        fail("手册只在 routing.md、未进 dissect §8: " + ", ".join(only_r))
    else:
        ok(f"routing.md 与 dissect §8 路由集合一致（{len(in_routing)} 份专项手册）")

# 7k) 模板孤儿检查（软约束，v1.15.0 新增）：assets/ 下每个模板应被至少一处引用
asset_files = sorted((ROOT / "assets").glob("*.md"))
all_md_text = "\n".join(read(p) for p in md_files())
orphan_assets = [p.name for p in asset_files if p.name not in all_md_text]
if orphan_assets:
    warn("未被任何文档引用的模板: " + ", ".join(orphan_assets))
else:
    ok(f"assets/ 全部 {len(asset_files)} 份模板均被引用")

# 7l) 需求库与成本账本的接线完整性（v1.16.0 新增）
#     回归来源：v1.14 之前「测试需求/计划」从不落盘，plans/ 全库 0 命中 —— 同一类需求
#     下次要重推一遍测试设计；而「省 token」也只有定性三律、没有可测的数。
#     本门禁锁住四处接线，任何一处被删/漂移就 FAIL，防止功能「写在规范里但流程没接上」。
try:
    mt = read(ROOT / "references/memory-tree.md")
    tl = read(ROOT / "references/tools.md")
    wiring = {
        "memory-tree.md 未定义 plans/ 需求档案格式": "plans/PLAN-<N>-<slug>.md",
        "memory-tree.md 未定义 tree.md 需求索引": "需求索引",
        "memory-tree.md 未引用档案模板": "assets/plan-template.md",
        "memory-tree.md 未定义成本账本 metrics.md": "metrics.md",
        "SKILL.md 阶段 0 未接入需求档案索引": "plans/",
        "SKILL.md 阶段 2 未要求落盘需求档案": "plan-template.md",
        "SKILL.md 未接入成本账本脚本": "context-cost.py",
        "tools.md 未登记 context-cost.py": "context-cost.py",
    }
    missing_wiring = []
    for label, needle in wiring.items():
        pool = mt if "memory-tree" in label else (tl if "tools.md" in label else skill)
        if needle not in pool:
            missing_wiring.append(label)
    script_ok = (ROOT / "scripts/context-cost.py").is_file()
    if not script_ok:
        missing_wiring.append("scripts/context-cost.py 缺失")
    tmpl_ok = (ROOT / "assets/plan-template.md").is_file()
    if not tmpl_ok:
        missing_wiring.append("assets/plan-template.md 缺失")
    if missing_wiring:
        fail("需求库/成本账本接线不完整: " + "；".join(missing_wiring))
    else:
        ok("需求库（plans/）与成本账本（metrics.md）已接线：规范 + 模板 + 脚本 + 阶段 0/2/4 全链")
except OSError as e:  # 文件缺失由上方的断链检查负责报错
    warn(f"需求库接线检查跳过：{e}")

# 7m) 记忆树模板必须含需求索引区（v1.16.0 新增）
tree_tmpl = ROOT / "assets/tree-template.md"
if tree_tmpl.is_file():
    tt = read(tree_tmpl)
    if "需求索引" not in tt or "PLAN-" not in tt:
        fail("assets/tree-template.md 缺「需求索引」区：新建的树将无法定位需求档案")
    else:
        ok("tree 模板含需求索引区（PLAN- 指针）")
else:
    fail("assets/tree-template.md 缺失")

# 8) global-lessons 格式（软约束）
gl = read(ROOT / "memory/global-lessons.md")
bad = [ln for ln in gl.splitlines()
       if ln.strip() and not ln.startswith(("#", ">", "-", "|", "`")) and not ln.startswith("[")]
if bad:
    warn(f"global-lessons.md 有 {len(bad)} 行不符合 '[标签] 教训 — 应用：' 约定")
else:
    ok("global-lessons.md 格式基本合规")
# 8a) 体积纪律（v1.15.0 新增）：文件头自定「>40 行修剪旧条目」，实际已 337 行且阶段 0 整份读入。
#     不直接 FAIL（会造成「要么删知识、要么门禁永远红」的两难），但必须持续可见、逼出索引化。
gl_lines = len(gl.splitlines())
if gl_lines > 500:
    fail(f"memory/global-lessons.md 已 {gl_lines} 行（>500），阶段 0 整份读入成本过高，必须索引化/归档")
elif gl_lines > 200:
    warn(f"memory/global-lessons.md 已 {gl_lines} 行，超自定 40 行上限，建议加 TOC 并把冷门条目归档")
else:
    ok(f"memory/global-lessons.md {gl_lines} 行（体积可控）")

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
