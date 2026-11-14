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
| R-11 测试数据可信与合规 | PASS / 待确认 / 不适用 | <数据来源声明+脱敏字段清单与残留核查+人工复核+同seed两次生成一致校验+子集外键悬空=0+无生产数据声明 or 未做测试数据可信验证 / 不适用：无测试数据维度> |
| R-12 身份与会话不可冒充 | PASS / 待确认 / 不适用 | <令牌清单+jwt-audit decode 结构审计+alg=none/算法混淆/空签名三连请求原文与响应+exp/nbf/aud/iss/typ 五类负向+登出改密重置后旧 access 与 refresh 均拒+refresh 轮换与 reuse detection+枚举三列与限流+密码存储源码 or 未做身份与会话验证 / 不适用：无身份与会话维度> |
| R-13 时间与时区正确性 | PASS / 待确认 / 不适用 | <三层口径表+应用与DB的tzdata版本+time-audit scan 输出+命中逐条裁决+DST gap 与 fold 实跑执行次数（调度日志/幂等键）+TTL 前一秒/等于/后一秒+时钟回拨与单调时钟+RFC 3339 解析与排序 or 未做时间与时区验证 / 不适用：无时间与时区维度 / 未做 DST 与时钟实测：tzdata 不可用> |
| R-14 备份与恢复可验证性 | PASS / 待确认 / 不适用 | <备份清单与频率/保留期/加密与密钥位置+最近一次隔离环境实恢复记录（恢复点/耗时三段/RTO）+restore-audit compare 输出（缺口与 warnings）+强校验命令输出（--read-data/--verify-data/pg_verifybackup checksum）+行数/hash/外键/序列/blob/版本不变量+PITR 丢失窗口与删除权/多租户交叉 or 未做过恢复演练 / 不适用：无持久化数据与备份面> |

> 详细证据填各专项模板：`supply-chain-evidence-template.md` / `i18n-matrix-template.md` / `tenant-isolation-matrix-template.md` / `contract-evolution-matrix-template.md` / `privacy-matrix-template.md` / `test-effectiveness-template.md` / `accessibility-matrix-template.md` / `device-matrix-template.md` / `evidence-chain-template.md`（R-9 三级引用链、控制项映射、锚点原文与审计导出留痕）/ **`flag-rollout-matrix-template.md`（R-10 四类必测面、目标群体否定用例、三处配置比对、kill-switch 实测、灰度比例）** / **`test-data-matrix-template.md`（R-11 数据来源 / 确定性种子 / PII 脱敏残留核查 / 子集外键完整性 / 无生产数据声明）** / **`auth-matrix-template.md`（R-12 令牌清单与结构审计 / J1~J11 伪造降级 / S1~S9 会话生命周期 / F1~F12 认证流程 / 不适用声明）** / **`time-matrix-template.md`（R-13 三层口径 / tzdata 版本 / DST gap 与 fold 执行次数 / TTL 三值 / 降级声明）** / **`restore-drill-template.md`（R-14 RPO·RTO 实测 / 恢复计时 / 不变量 12 行 / 强校验输出）**。十四行每行都必须填结论或「不适用 / 待确认」声明（由 `scripts/selfcheck.py` §7d 强制），任一条声称通过却无证据 → 该结论作废降为「待确认」。**R-9 的「对账 GREEN」只证明证据链可解析，不得写成「已通过审计 / 合规通过 / 软件安全」**（`references/evidence-chain-audit.md` §4）；**R-10 的「开态测过」不得写成「关态也安全 / 灰度可控」**（`references/feature-flag-testing.md` §4）；**R-11 的「用了生成器 / 掩码了已知字段」不得写成「数据已脱敏 / 无 PII 泄漏 / 数据可复现」**（`references/test-data-management.md` §6）**；R-12 的「登录成功 / 令牌可解码 / Cookie 有 HttpOnly」不得写成「认证安全 / 可伪造 / 会话安全」**（`references/auth-session-testing.md` §7）**；R-13 的「能解析时间 / 静态扫描未命中」不得写成「时间正确」，R-14 的「备份任务成功 / 结构校验通过」不得写成「可恢复」**（`references/time-correctness-testing.md` §9、`references/backup-recovery-testing.md` §8）。

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
