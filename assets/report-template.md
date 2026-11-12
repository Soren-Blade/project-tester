# 测试报告 — <项目名>

- 日期：<YYYY-MM-DD> ｜ 测试轮次：第 <N> 轮（接力自 <上轮日期> 或 "首轮"）
- 技能版本：v<X> ｜ 能力层路由：<依据 dissect.md §8>
- 范围：<本轮测了什么> ｜ 接力点：<tree.md 的一句话>
- 环境：<OS / 运行时版本 / 浏览器 / 降级说明与局限>

## 总览

| 指标 | 值 |
|---|---|
| 测试点 | N（通过 X / 失败 Y / 阻塞 Z / 待确认 W），X+Y+Z+W = N |
| 覆盖口径 | <功能点覆盖 / 端点覆盖 / 分支覆盖，写清分子分母> |
| 发现缺陷 | N（S1 严重 n / S2 一般 n / S3 轻微 n） |
| 模块覆盖 | a / b ｜ P0 覆盖 __% |
| 双视角 | 日常✅ 刁钻✅（或说明为何缺一遍） |
| 性能 | p50/p95/p99 = __/__/__ms ｜ 错误率 __% ｜ <注明"单点观测"或负载类型> |
| 证据完整率 | 失败结论中带 MRE + 实际输出的比例 __% |

## 证据矩阵（可证伪规则结论，缺则标 BLOCKED / 不适用）

| 规则 | 本次结论 | 关键证据 / 不适用声明 |
|---|---|---|
| R-1 链路 | PASS / 待确认 / 不适用 | <trace_id 贯通 ≥2 组件 证据 or 可观测性缺口> |
| R-2 韧性 | PASS / 待确认 / 不适用 | <故障注入记录 or 未做验证> |
| R-3 制品完整性 | PASS / 待确认 / 不适用 | <sha256+SBOM+验证命令原文 or 未做验证> |
| R-4 租户隔离 | PASS / 待确认 / 不适用 | <双租户否定路径 or 不适用> |
| R-5 契约演进 | PASS / 待确认 / 不适用 | <oasdiff 退出码+can-i-deploy or 未做验证> |
| R-6 隐私与数据生命周期 | PASS / 待确认 / 不适用 | <PII 分类+删除权+日志脱敏 or 未做验证> |
| R-7 无障碍可达性 | PASS / 待确认 / 不适用 | <WCAG 2.2 级别+violations/incomplete+键盘路径+读屏组合 or 未做无障碍实测> |
| R-8 跨端与设备形态真实性 | PASS / 待确认 / 不适用 | <设备矩阵来源+载体标注+端侧面+真机证据 or 未做跨端验证> |
| R-9 证据链可追溯与可复核性 | PASS / 待确认 / 不适用 | <三级引用链可解析+sha256/commit 绑定+自动对账缺口+控制项映射 or 未做证据链对账 / 不适用：无留档要求> |
| R-10 特性开关 / 配置 / 灰度正确性 | PASS / 待确认 / 不适用 | <开关off/缺失态回退+目标群体否定用例+三处配置比对+kill-switch实测+灰度比例 or 未做开关/配置/灰度验证 / 不适用：无开关与配置维度> |

> 详细证据填各专项模板：`supply-chain-evidence-template.md` / `i18n-matrix-template.md` / `tenant-isolation-matrix-template.md` / `contract-evolution-matrix-template.md` / `privacy-matrix-template.md` / `test-effectiveness-template.md` / `accessibility-matrix-template.md` / `device-matrix-template.md` / `evidence-chain-template.md`（R-9 三级引用链、控制项映射、锚点原文与审计导出留痕）/ **`flag-rollout-matrix-template.md`（R-10 四类必测面、目标群体否定用例、三处配置比对、kill-switch 实测、灰度比例）**。十行每行都必须填结论或「不适用 / 待确认」声明（由 `scripts/selfcheck.py` §7d 强制），任一条声称通过却无证据 → 该结论作废降为「待确认」。**R-9 的「对账 GREEN」只证明证据链可解析，不得写成「已通过审计 / 合规通过 / 软件安全」**（`references/evidence-chain-audit.md` §4）；**R-10 的「开态测过」不得写成「关态也安全 / 灰度可控」**（`references/feature-flag-testing.md` §4）。

## 缺陷清单（按严重度排序）

### BUG#n [S1 严重] <标题>
按 `assets/bug-report-template.md` 八字段填写：环境指纹 / MRE / 预期 vs 实际 / 证据 / 影响面 / 修复方向。

## 通过项摘要

<一句话列举，细节见 runs/ 记录>

## 未覆盖与降级说明

- <哪些维度没测、为什么、剩余风险>
- <工具缺失导致的降级（如"浏览器不可用 → HTTP 层验证，未做真实渲染验证"）>
- <单点性能观测不构成性能结论 之类的口径声明>

## 风险与建议

- 上线前必须修：<___> ｜ 建议修：<___> ｜ 可观察：<___>

## 结论（必须明确，禁止"基本可以"）

| 项 | 值 |
|---|---|
| 质量状态 | **PASS / FAIL** |
| 发布建议 | **Go / No-Go**（验收场景按 `assets/release-gate-template.md` 12 分门禁打分） |

一句话理由：<___>

## 记忆与进化

- 记忆树已更新：<新增模块 / 状态变化 / 待办>
- 本轮进化：新增教训 N 条（项目 n / 全局 m）｜技能改进提案 p 条｜下次从 <接力点> 开始
- 自检：`tree.md` <100 行 ✅ ｜ 临时探针已清理 ✅ ｜ 阶段 4 核对清单 ✅（`quality-gates.md` §8）
