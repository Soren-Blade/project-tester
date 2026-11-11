# 更新日志

> 每日升级记录。格式与门禁见 `references/self-evolution.md` §3~§4。
> 版本号与 `SKILL.md` frontmatter、`README.md` 徽章三者由 `scripts/selfcheck.py` 校验一致。

---

## [v1.0.0] — 2026-11-11 · 每日升级 #1

**主题**：从「通用项目测试流程」升级为「分层能力 + 专项手册 + 证据化门禁 + 可追溯自我进化」体系。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 动作 | 对象 |
|---|---|
| **Enhance** | `SKILL.md`（能力层路由、六维专项、权限裁决、参考索引）、`README.md`、`references/dissect.md`（测试设施/攻击面/路由）、`references/tools.md`（专项工具表/探测/降级纪律）、`references/personas.md`（4 个新画像 + 手册映射）、`references/memory-tree.md`（版本/严重度/三类待办）、`references/evolution.md`（四问 + 四层视角 + 权限裁决）、`assets/tree-template.md`、`assets/report-template.md`、`memory/global-lessons.md` |
| **New** | 9 份手册、3 份模板、1 个自检脚本、CHANGELOG、.gitignore |
| **Existing** | 五阶段模型、记忆树 <100 行纪律、双视角、"跑不起来也继续测"的降级原则 —— 全部保留，未改语义 |

### 蒸馏来源（可核查）

| 来源 | URL / 位置 | 关键结论 |
|---|---|---|
| OWASP API Security Top 10 – 2023（官方） | https://owasp.org/API-Security/editions/2023/en/0x11-t10/ | 十项官方名称逐条对齐；API3 合并过度暴露+批量分配；API1 BOLA 居首 |
| RFC 9457 Problem Details (2023) | https://www.rfc-editor.org/rfc/rfc9457.html | `application/problem+json`；标准成员全部可选；`status` 须与实际 HTTP 码一致；扩展成员客户端须忽略 |
| Playwright Test Agents（官方） | https://playwright.dev/docs/test-agents | planner/generator/healer 三件套、`npx playwright init-agents`、specs/ 与 seed.spec.ts 约定、healer 可跳过疑似损坏功能 |
| Schemathesis 官方文档 | https://schemathesis.readthedocs.io/en/stable/ | OpenAPI/GraphQL/gRPC 属性与状态化测试、每个发现自带最小 curl 复现 |
| awesome-qa-skills (GitHub) | https://github.com/naodeng/awesome-qa-skills | 四层能力体系、`AI for QA` ≠ `Testing for AI`、Skill Engineering 治理、Existing/Enhance/Merge/Match/New、证据门禁与四类结论区分 |
| 用户附加技能 `fullstack-dev` | 本地 `~/.workbuddy-ai/skills/fullstack-dev/` | testing-strategy.md（金字塔/隔离/工厂/Pact/k6/预算）、release-checklist.md（六门禁 12 分、金丝雀停止线、回滚预案）、§12 错误映射、Anti-Patterns |
| 用户附加技能 `frontend-dev` | 本地 `~/.workbuddy-ai/skills/frontend-dev/` | Quality Gates（无占位 URL、本地资源、动态视口、五态）、§2.4 动效性能与清理、§2.6 无障碍（reduced-motion/焦点/aria-live） |
| WCAG 2.2 / Core Web Vitals 公开口径 | 检索汇总 | LCP ≤2.5s / INP ≤200ms / CLS ≤0.1（P75）；WCAG 2.2 的 2.4.11 焦点不被遮挡、2.5.8 目标 ≥24px |
| 测试智能体标准与行业动态（2026） | 检索汇总 | CAICT/AIIA《测试智能体》标准、Playwright v1.56+ 内置 Agents、AI 生成测试需配套审查（伪测试/弱断言） |

### 主要改动

1. **能力分层路由**：L1 Core / L2 Engineering / L3 Production / L4 AI Native + `dissect.md` §8 项目形态→手册路由表
2. **测试设计体系**：九式设计手法、六维矩阵 v2、风险分优先级、覆盖口径与退出标准（`test-design.md`）
3. **API 与安全专项**：端点十项必测、RFC 9457 错误契约、OWASP API Top 10 逐项测试卡、认证授权矩阵、输入向量库、幂等/并发/限流、schemathesis
4. **性能专项**：五种负载形态、p50/p95/p99 与 Little's Law、k6 thresholds、性能预算、瓶颈定位顺序、轻量 shell 降级
5. **前端专项**：五态矩阵、WCAG 2.2 实测动作、Core Web Vitals、跨边界错误码映射、占位资源纪律、Playwright Test Agents 接入
6. **全栈与发布**：测试金字塔/隔离策略/集成边界、六门禁 12 分 Go/No-Go、金丝雀与回滚预案
7. **证据与有效性**：缺陷八字段 + MRE、严重度矩阵、flaky 治理、覆盖率 vs 变异得分、CI 门禁、指标口径
8. **AI 时代**：四层模型、AI for QA 与 Testing for AI 分离、AI 生成测试审查（自愈陷阱/伪测试）、AI 系统评测集与蜕变关系
9. **自我进化协议**：裁决"测项目时不自治 / 升级技能时授权自治"，十步升级门禁、变更证据要求、蒸馏质量门槛、语义化版本
10. **可验证性**：`scripts/selfcheck.py`（frontmatter / 断链 / 版本一致 / 占位 URL / 模板字段 / 索引覆盖），`CHANGELOG.md`，`.gitignore`
11. **模板升级**：新增 `bug-report-template.md` / `test-plan-template.md` / `release-gate-template.md`；报告模板强制 PASS/FAIL 与 Go/No-Go

### 回归检查

- [x] 五阶段模型闭环未变，示例仍成立（升级为含越权 bug 的 4 条 MRE 示例）
- [x] 记忆树 <100 行纪律保留；tree 模板仍 <100 行
- [x] 「工具缺失不中止」的降级原则保留，并在 `tools.md` §纪律 6 强化
- [x] 运行时不擅自改本体的安全约束保留，且用权限裁决明确了自动化升级的合法路径
- [x] 原有文件引用路径未失效（由 `selfcheck.py` 断链检查验证）

### 自检结果

`python scripts/selfcheck.py` → **PASS 16 / WARN 0 / FAIL 0 → GREEN**（退出码 0）。

首轮自检曾报 3 处断链（2 处为 `fullstack-dev` 外部技能的引用写成裸 `references/...`，1 处为已驳回提案里提到不存在的模板），已改为显式外部路径与文字描述后复跑通过——**门禁确实拦住了会导致误读的引用**，这是本次升级引入自检的价值验证。每日升级要求 FAIL = 0 才允许同步与提交。

---

## [v0] — 基线（未版本化，2026-10-30 前）

`SKILL.md` 五阶段 + 5 份 references + 2 份 assets + `memory/global-lessons.md`。无版本号、无 CHANGELOG、无 git 仓库、无专项手册与自检。
