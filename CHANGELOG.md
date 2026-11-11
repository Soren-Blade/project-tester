# 更新日志

> 每日升级记录。格式与门禁见 `references/self-evolution.md` §3~§4。
> 版本号与 `SKILL.md` frontmatter、`README.md` 徽章三者由 `scripts/selfcheck.py` 校验一致。

---

## [v1.1.0] — 2026-11-11 · 每日升级 #2

**主题**：从「响应断言」扩展到「系统内部行为验证」——补齐可观测性/Trace 驱动、韧性与故障注入、数据一致性、非 REST 协议四块深水区，并吸收 v1.0 遗留的 GraphQL/gRPC 提案。

**遵循上轮建议**：未重写已覆盖主题（测试设计、OWASP、性能、前端、全栈发布、AI 原生、自我进化），以 **Enhance 为主、New 为辅**；四层模型与五阶段流程**未改语义**（故按 `self-evolution.md` §7 只升 MINOR）；每轮新增至少一条可证伪规则 → 本轮引入 R-1 / R-2。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 动作 | 对象 |
|---|---|
| **New** | `references/observability-testing.md`、`references/chaos-resilience.md`、`references/data-integrity-testing.md`、`references/protocol-testing.md`、`assets/protocol-matrix-template.md`、`assets/resilience-runbook-template.md` |
| **Enhance** | `SKILL.md`（description 触发词、能力层叠加项、阶段 1/3/4、R-1/R-2、参考索引）、`README.md`（徽章/结构/速查/版本史）、`references/dissect.md`（栈指纹、协议入口、测试设施、观测面与依赖拓扑、路由表、产出格式）、`references/api-testing.md` §7 分流、`references/fullstack-integration.md` §5 分流、`references/performance-testing.md` §2 边界、`references/frontend-testing.md` §2.1 运行时实测、`references/quality-gates.md` §3/§8、`references/tools.md` 专项工具表、`references/self-evolution.md` §5 孤儿文档门禁 |
| **Merge** | `memory/global-lessons.md`：v1.0 中与新手册重复的条目改写为交叉引用（不二次抄写），提案区两项结案；新增 4 组 v1.1 教训但控制在同一文件内，不另建文件 |
| **Match** | 全部新增手册均已在 `dissect.md` §8 路由表与 `SKILL.md` 叠加项中有明确触发条件（满足本轮新加的「孤儿文档」门禁）；`selfcheck.py` 索引覆盖检查验证 |
| **Existing** | 五阶段模型、记忆树 <100 行纪律、双视角、"工具缺失不中止"的降级原则、六门禁 12 分、缺陷八字段、权限裁决 —— 全部保留，未改语义 |

### 蒸馏来源（本轮实查，均可核查）

| 来源 | URL / 位置 | 关键结论 |
|---|---|---|
| OpenTelemetry Traces（官方） | https://opentelemetry.io/docs/concepts/signals/traces/ | Span Context = Trace ID/Span ID/TraceFlags/TraceState；根 span 无 parent；`status` 三态 Unset/Error/Ok；属性宜在 span 创建时添加以便 SDK 采样；带独立时间戳用 Span Event；Context Propagation 是分布式追踪核心 |
| OpenTelemetry Semantic Conventions（官方） | https://opentelemetry.io/docs/concepts/semantic-conventions/ | 统一属性命名（traces/metrics/logs/profiles/resources）才能跨库跨语言关联；各服务自造属性名 = 断言写不出来 |
| W3C Trace Context（W3C Recommendation） | https://www.w3.org/TR/trace-context/ | `traceparent: 00-<32hex trace-id>-<16hex parent-id>-<2hex flags>`；全零 ID 非法；最低合规 MUST 转发且保证 trace 不断；除 restart trace 外 `trace-id` 不得变 |
| Tracetest 官方文档 + GitHub | https://docs.tracetest.io/ · https://github.com/kubeshop/tracetest | `trigger + selector + assertions` YAML；断言响应 + trace 数据、span 时长、通配断言（所有 db span <100ms）、MQ/异步/外部 API 等副作用；CLI 进 CI |
| Google SRE Book《Service Level Objectives》 | https://sre.google/sre-book/service-level-objectives/ | SLI 应按分布（percentiles）而非平均；SLO = SLI + target + 测量条件；SLA 含"未达成后果"；错误预算 = 允许未达成的比率，用于决定何时发布；不要按当前性能定目标 |
| Principles of Chaos Engineering（官方） | https://principlesofchaos.org/ | 四步实验（定义稳态 → 假设对照/实验组持续 → 引入真实事件 → 找差异**证伪**）；五条高级原则；稳态用可测量输出（吞吐/错误率/延迟分位数），关注系统行为而非内部属性 |
| Shopify/Toxiproxy（GitHub） | https://github.com/Shopify/toxiproxy | 确定性故障注入；HTTP API :8474；toxics: latency(±jitter)/bandwidth/slow_close/timeout/reset_peer/slicer/limit_data/packet_loss；`stream` 上下游、`toxicity` 默认 1.0；`down` 是 `enabled=false`；`POST /reset` 兜底 |
| chaos-mesh/chaos-mesh（GitHub） | https://github.com/chaos-mesh/chaos-mesh | CNCF incubating；K8s CRD 定义实验；Pod/network/DNS/HTTP/I-O/time/stress/kernel 等故障；Schedule/Workflow/StatusCheck；RBAC 收窄作用域 |
| litmuschaos/litmus（GitHub） | https://github.com/litmuschaos/litmus | ChaosExperiment（故障模板）→ ChaosEngine（绑定 workload + probes 稳态约束）→ ChaosResult（verdict、revert/rollback 状态、Prometheus 指标）；可作 CI/CD stage |
| jepsen-io/jepsen（GitHub） | https://github.com/jepsen-io/jepsen | generator 生成操作 → nemesis 注入故障 → history 记录每个操作起止 → checker 分析正确性；借用「操作历史 + 故障 + 不变量检查」思路 |
| OWASP GraphQL Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html | introspection/GraphiQL/字段建议；深度·数量·query cost 限制；batching 绕过按请求数限流并爆破 OTP；resolver 级授权（edges 与 nodes 都要查）；allowlist 输入；生产不返回 stack trace |
| gRPC 官方 Status Codes | https://grpc.io/docs/guides/status-codes/ | 17 个码；`NOT_FOUND`/`PERMISSION_DENIED`/`UNAUTHENTICATED`/`RESOURCE_EXHAUSTED` 有严格区分；`DEADLINE_EXCEEDED` 时操作**可能已成功**；`UNAVAILABLE` 可退避重试但非幂等操作不安全；`DATA_LOSS`/`INTERNAL` 是严重错误 |
| fullstorydev/grpcurl（GitHub） | https://github.com/fullstorydev/grpcurl | JSON → protobuf；依赖 server reflection 或 `-proto`/`-protoset`；`list`/`describe`；`-plaintext`、`-H` metadata；`protoc --descriptor_set_out --include_imports` |
| PostgreSQL 事务隔离（官方） | https://www.postgresql.org/docs/current/transaction-iso.html | 四类异常（脏读/不可重复读/幻读/序列化异常）× 四隔离级别对照表；PG 默认 Read Committed 允许后三者；Repeatable Read 用快照隔离且 PG 中不出现幻读；Serializable 全禁但需准备重试 |
| 用户附加技能 `frontend-dev` / `fullstack-dev`（二次蒸馏） | 本地 `~/.workbuddy-ai/skills/` | frontend-dev：GPU-only 动画属性、`useEffect` cleanup `ctx.revert()`、重库 lazy-load、`prefers-reduced-motion`、动态视口；fullstack-dev：结构化日志 request_id、`/health` vs `/ready`、迁移 up/down、缓存 TTL 与写失效、后台任务幂等与 DLQ、SSE/WS 重连退订、优雅停机 |

### 主要改动

1. **可观测性驱动测试**（`observability-testing.md`）：三大信号最小判据、W3C `traceparent` 格式与转发规则、五步零依赖链路实验、8 条 span 断言清单、Tracetest YAML、SLI/SLO/错误预算写成可断言门禁、日志脱敏与 `/health` vs `/ready`
2. **韧性与故障注入**（`chaos-resilience.md`）：适用边界与安全红线、稳态假设四步协议、8 类故障注入矩阵、L0 shell / L1 Toxiproxy / L2 K8s 三级工具阶梯、恢复核对 6 条、演练记录模板
3. **数据一致性**（`data-integrity-testing.md`）：三重断言、迁移 7 条用例与 checksum 证据、PG 隔离级别对照与并发 5 条、缓存/双写/CDC/读副本/幂等/死信、SQL 对账脚本、不变量优于期望值
4. **非 REST 协议**（`protocol-testing.md` + 矩阵模板）：**吸收 v1.0 遗留提案**，逐类型给出 GraphQL 12 项、gRPC 11 项、WS/SSE 10 项用例清单，含 curl / grpcurl / protoset 命令与四协议认证矩阵落点
5. **两条可证伪规则**：R-1（链路结论须有 ≥2 组件的同 id 原始证据）、R-2（韧性结论须有可复现的故障注入记录），各自**明确写了不适用条件与降级写法**，并接入 `quality-gates.md` §3 Go/No-Go 与 §8 交付核对
6. **解剖增强**：`dissect.md` 新增协议与可观测性栈指纹、非 REST 入口追踪、观测面/依赖拓扑/故障域盘点、4 条新路由与「叠加项按触发条件选，不为凑维度造测试」
7. **路由闭环**：所有新增手册都有 `dissect.md` §8 触发条件与 `SKILL.md` 叠加项；`self-evolution.md` §5 新增「孤儿文档」门禁，防止只加文件不加路由
8. **交叉引用而非重写**：`api-testing.md` §7、`fullstack-integration.md` §5、`performance-testing.md` §2 各加一段分流，明确"REST 底座 / 单次负载表现 / 时间窗 SLO / 依赖故障行为"的边界
9. **前端运行时实测**（`frontend-testing.md` §2.1）：从 `frontend-dev` 二次蒸馏出首屏资源、持续动画 30~60s、卸载 cleanup、动态视口、reduced-motion 等 6 项**必须真实渲染**的判据，并明确静态核对不得冒充运行时结论
10. **经验治理**：`global-lessons.md` 吸收提案（GraphQL/gRPC 已吸收、统一证据模板驳回理由保留）、新增 4 组共 23 条 v1.1 教训、重复项改写为交叉引用，控制为单文件不膨胀
11. **文档与版本**：`SKILL.md` / `README.md` / `CHANGELOG.md` 同步到 v1.1.0；README 文件结构 25 → 31、徽章 references 14 → 18、templates 5 → 7

### 回归检查

- [x] 五阶段模型闭环未变，`SKILL.md` 的 todo 示例（4 条 MRE、含越权 S1）逐字保留
- [x] 四层能力模型语义未变（L1~L4 仍是四层，新增内容以「横向叠加项」呈现，不构成 MAJOR）
- [x] 记忆树 <100 行纪律保留；`assets/tree-template.md` 未改，仍 <100 行
- [x] 「工具缺失不中止」降级原则保留，且新手册每份都有 L0 零依赖路径（curl+grep / shell 并发 / 静态审查）
- [x] 运行时不擅自改本体的安全约束保留；权限裁决原文未改
- [x] 原有文件引用路径未失效（由 `selfcheck.py` 断链检查验证）
- [x] 新增路由不产生孤儿文档（由 `selfcheck.py` 索引覆盖检查验证）
- [x] 六门禁 12 分与缺陷八字段、Flaky 治理等关键字段仍在（由 `selfcheck.py` 字段检查验证）

### 自检结果

`python scripts/selfcheck.py` → **PASS 16 / WARN 0 / FAIL 0 → GREEN**（退出码 0）；全局安装版复跑结果一致；源与全局安装 `diff -r` 完全一致（31 文件）。详见本轮交付报告。

> 门禁说明：按 `self-evolution.md` §3，FAIL > 0 即停止升版本/同步/提交。本轮严格按 ⑥ 自检 → ⑦ 版本 → ⑧ 同步 → ⑨ 提交的顺序执行。

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
