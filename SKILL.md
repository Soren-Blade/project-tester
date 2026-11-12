---
name: project-tester
version: 1.4.0
description: 通用项目深度测试技能：自动解剖任意项目的功能结构，按风险生成并完善测试需求，熟练调用匹配技术栈的测试工具，以「日常用户 + 刁钻用户」双视角做功能/边界/异常/安全/性能/体验六维深度测试，用测试记忆树记录每次过程与结果（下次免重复探索、大幅省 token），并持续沉淀经验、每日自我进化。覆盖 API 契约与 OWASP API Top 10 安全测试、k6 性能分位数、前端五态与 WCAG 可访问性、全栈集成与六门禁发布验收、契约/属性/变异测试、AI 辅助测试与 AI 系统评测；并支持可观测性与 Trace 驱动测试、韧性与故障注入演练、数据库迁移与数据一致性验证、GraphQL/gRPC/WebSocket/SSE 非 REST 协议端点矩阵，以及软件供应链与制品完整性验证（SBOM/签名/provenance/可复现构建）、国际化与本地化测试（伪本地化/RTL/locale 格式往返）、多租户隔离测试（双租户否定路径/共享资源/平台管理员）、契约演进兼容性（消费者契约 + 影子流量）、无障碍可达性深度实测（WCAG 2.2 AA / 键盘路径 / 读屏组合 / ARIA 快照）、跨端与设备形态真实性（设备矩阵 / 仿真 vs 真机 / 端侧特有面）、测试有效性与经济性（DORA / 变异得分 / ROI）。凡是用户想测试、验收、找 bug、检查质量、回归、上线前门禁、模拟用户操作、压测、安全审查任何项目时使用——包括"测一下这个项目""帮我测测""这项目稳不稳""上线前查一下""找找 bug""回归测试""模拟用户用一下""能不能发布""接口测一下""链路查一下""依赖挂了会怎样""迁移有没有问题""故障演练""数据一致性""安全有没有问题""制品有没有被改过""SBOM/依赖清单全不全""换个语言/地区还正常吗""RTL 排布对不对""多租户会不会串数据""租户隔离""test this project""find bugs""SBOM""i18n""multi-tenant"等说法，即使没说"测试"二字（如"检查一下有没有问题"）也应用本技能；以及"契约演进兼容性""API 升级老客户端会不会挂""隐私合规/PII 最小化/删除权 GDPR""测试有效性度量/变更失败率/flaky/变异得分"等说法（contract evolution / privacy / test effectiveness / mutation score / DORA / change failure rate）；以及"无障碍合规 / WCAG 2.2 AA / 焦点被遮挡 / 读屏 / 屏幕阅读器 / 键盘走查 / 目标尺寸 / 移动端可用 / 真机验证 / 设备矩阵 / 折叠屏 / 跨浏览器 / 仿真与真机区别 / 测试成本 / ROI / 自动化测试值不值"等说法（WCAG 2.2 / accessibility / screen reader / cross-platform / real device / test ROI）。
---

# 通用项目测试 (project-tester) · v1.4.0

一句话：**解剖 → 计划 → 深测 → 记忆 → 进化**，五阶段循环。记忆树让下一次测试从"接力点"出发，而不是从零开始。

v1.1 增量：**从「响应断言」扩展到「系统内部行为验证」**——链路、副作用、依赖故障下的一致性，同样要有证据。

v1.2 增量：**从「系统行为」扩展到「交付链与边界正确性」**——「我拿到的制品是不是我以为的那个」「换一套 locale / 书写方向后系统还正确吗」「共享基础设施上租户会不会串数据」。三条都配了可证伪规则 R-3 / R-4 与明确的不适用写法。

v1.3 增量：**从「边界正确性」扩展到「演进与合规正确性」**——「改了之后老客户端会不会挂」「系统该不该存这些个人数据、存了能不能删、返回时有没有多给」「你这一堆测试到底有没有用」。三条都配了可证伪规则 R-5 / R-6（R-5 契约演进 + R-6 隐私与数据生命周期；测试有效性作为度量纪律支撑 Go/No-Go），与前四者共用「不适用就降级、不得冒充通过」的写法。

v1.4 增量：**从「系统正确」扩展到「人人可用 · 处处可用 · 值得测」**——「辅助功能用户能不能走完流程」「换台真机、换个内核、换种网络还成立吗」「这堆测试的成本配得上收益吗」。新增 R-7（无障碍可达性）/ R-8（跨端与设备形态真实性）两条可证伪规则，把三个顺延提案（ROI 度量、移动端与桌面端专项、无障碍自动化实测）落地；同时修正此前「四条规则 / R-1~R-4」等文档漂移。四层模型与五阶段语义未变，故仍按 MINOR 升级。

适用对象：任何项目形态——代码库、Web 应用、API、CLI 工具、脚本、库/包、静态页面、LLM/Agent 应用。本技能不绑定语言框架、不绑定特定 agent：所有操作只用通用能力（读写文件、执行 shell、按需用浏览器/联网）。测试工具缺失时按 `references/tools.md` 降级策略执行，**绝不因"没有某某测试框架"而中止**。

## 五阶段总览

| 阶段 | 做什么 | 完成标志 |
|---|---|---|
| 0 读记忆 | 读项目记忆树 + 技能全局经验 | 明确本次只测增量/待办，或确认从零开始 |
| 1 解剖 | 识别栈、入口、模块、可运行性、**测试设施、攻击面、观测面、依赖拓扑、交付链、locale 面、租户边界、无障碍面与设备形态面** | 项目画像 + 功能清单 + 能力层路由定稿 |
| 2 计划 | 功能清单 → 风险分 → 六维测试矩阵（P0/P1/P2） | 测试点列表确定（用户确认或按默认执行） |
| 3 深测 | 日常用户 + 刁钻用户双视角，按能力层调用专项手册 | 每个测试点有 通过/失败/阻塞/待确认 结论 + 证据 |
| 4 记忆与进化 | 写运行记录、更新树、沉淀教训、自检 | 记忆树反映最新状态，报告含 PASS/FAIL 与 Go/No-Go |

**无论中途因什么结束（用户打断、环境阻塞、发现重大 bug），阶段 4 都必须执行**——没有落记忆的测试等于白测。

## 能力分层与路由（v1.0 建立，v1.1 / v1.2 / v1.3 / v1.4 叠加专项）

阶段 1 结束时按项目形态选手册，避免"不管什么项目都同一套用例"（详见 `references/dissect.md` §8）：

| 层 | 能力 | 手册 | 典型触发 |
|---|---|---|---|
| L1 Core | 测试设计、画像、缺陷、报告 | `references/test-design.md` · `personas.md` · `quality-gates.md` | 所有项目 |
| L2 Engineering | API、安全、性能、前端、全栈集成 | `api-testing.md` · `security-testing.md` · `performance-testing.md` · `frontend-testing.md` · `fullstack-integration.md` | REST/GraphQL、Web UI、全栈 |
| L3 Production | 发布门禁、生产验证、Go/No-Go | `fullstack-integration.md` §6 · `assets/release-gate-template.md` | "上线前查一下""能不能发" |
| L4 AI Native | AI 辅助测试 + 测试 AI 系统 | `references/ai-native-testing.md` | LLM/RAG/Agent 应用、Playwright Test Agents |

**v1.1 横向叠加项**（不新增层级，按项目形态在 L2/L3 上叠加；四层模型与五阶段均未变更）：

| 触发条件 | 叠加手册 | 必做动作 |
|---|---|---|
| 微服务 / 多组件 / 异步链路 | `references/observability-testing.md` | `trace_id` 或 `request_id` 贯通 ≥2 组件、副作用 span、SLI/SLO 与错误预算 |
| 有外部依赖、要验证容错 | `references/chaos-resilience.md` | 稳态假设 → 最小爆炸半径注入 → 恢复验证 → `assets/resilience-runbook-template.md` 留证 |
| 有 DB / 迁移 / 缓存 / 多副本 | `references/data-integrity-testing.md` | 三重断言（响应+DB+派生状态）、迁移 up/down、并发不变量 |
| GraphQL / gRPC / WebSocket / SSE | `references/protocol-testing.md` + `assets/protocol-matrix-template.md` | 按 operation/method 建矩阵（不按 URL）、协议特有错误与授权 |
| 上线前验收 | `references/fullstack-integration.md` §6 + `assets/release-gate-template.md` | 六门禁 12 分，Gate 2/4/6 吸收观测、韧性与数据证据 |

**v1.2 / v1.3 横向叠加项**（同样不新增层级；四层模型与五阶段语义未变）：

| 触发条件 | 叠加手册 | 必做动作 |
|---|---|---|
| 有 lockfile / 依赖清单 / 容器镜像 / 发布产物 / CI 流水线 | `references/supply-chain-testing.md` + `assets/supply-chain-evidence-template.md` | 制品 `sha256` + SBOM 原件与覆盖缺口、签名/provenance 验证命令原文与退出码、锁文件冻结安装、**可复现构建两次 digest 比对**；**R-3**。纯源码/静态页只写「未做制品完整性验证」 |
| 有多语言资源 / locale 切换 / 日期货币格式 / RTL / 跨国输入 | `references/i18n-localization-testing.md` + `assets/i18n-matrix-template.md` | 代表 locale × 六维矩阵、伪本地化四步、`dir`/`dirname`/`<bdi>`/logical properties、F-1~F-8 格式与数据往返；无浏览器时静态审查并标 `BLOCKED` |
| SaaS / 多租户 / 共享 DB·cache·queue·storage / platform admin / 共享备份 | `references/multi-tenancy-testing.md` + `assets/tenant-isolation-matrix-template.md` | 双租户**相同 ID** 冲突夹具、TC/IDOR/DB/CACHE/QUEUE/FILE/BACKUP/ADMIN 否定路径、连接复用与 noisy-neighbor；**R-4**。单租户写「不适用：无租户边界」 |
| 有 OpenAPI/GraphQL/proto 规范且多客户端/多版本在跑、需持续迭代 | `references/contract-evolution-testing.md` + `assets/contract-evolution-matrix-template.md` | `oasdiff breaking --fail-on=ERR` 退出码 + 输出行、Pact 消费者契约与 `can-i-deploy` 闸门、容忍读取、**影子流量比对（无写副作用）**；**R-5**。无对外契约的单体工具写「未做契约演进验证」 |
| 处理个人数据 / PII / 用户生成内容、有隐私政策或合规要求 | `references/privacy-compliance-testing.md` + `assets/privacy-matrix-template.md` | 字段级 PII 分类 + 读接口响应白名单比对、批量分配、删除权端到端验证、日志脱敏核查；**R-6**。不处理 PII 的纯技术工具写「未做隐私合规验证」 |
| 有 CI / 测试套件 / 发布流程，需量化「测试值不值」 | `references/test-effectiveness-testing.md` + `assets/test-effectiveness-template.md` | DORA 四指标（CFR/MTTR 等）、缺陷逃逸率、flaky 配额与 quarantine、变异得分对照覆盖率、§5A 测试经济性/ROI；结论支撑 Go/No-Go。无自动化测试写「无测试度量基础」 |

**v1.4 横向叠加项**（同样不新增层级；四层模型与五阶段语义未变）：

| 触发条件 | 叠加手册 | 必做动作 |
|---|---|---|
| 有 UI / 交互 / 表单 / 认证，或声称「WCAG 2.2 AA / 支持读屏 / 可键盘操作 / 无障碍已验收」 | `references/accessibility-testing.md` + `assets/accessibility-matrix-template.md` | WCAG 2.2 增量 9 条口径、axe violations **+ incomplete** 人工复核、完整键盘路径、至少一组读屏 + 浏览器 + OS 组合逐项标注、2.4.11 / 2.5.8 / 3.3.8 实测；**R-7**。无 UI 的 CLI/库写「不适用：无图形交互界面」 |
| 有移动端 / 桌面端 / 多浏览器用户，或声称「移动端可用 / 真机验过 / 已适配折叠屏 / 跨浏览器兼容」 | `references/cross-platform-testing.md` + `assets/device-matrix-template.md` | 设备矩阵来源与覆盖占比、`real`/`emulator`/`simulator`/`browser-emulation` 逐项标注、多内核与长尾条目、端侧特有面与网络档位、发布门禁真机证据；**R-8**。纯后端 API/CLI 写「不适用：无终端形态差异」 |
| 关心「测试成本配不配得上收益」、要决定自动化投入 | `references/test-effectiveness-testing.md` §5A + `assets/test-effectiveness-template.md` | 建设/运行/维护成本、反馈时间收益、逃逸避免成本、选测/并行/缓存收益，与有效性指标合并成 ROI 口径；无自动化测试写「无测试度量基础」 |

**先分清 "AI for QA"（用 AI 提效，横向）与 "Testing for AI"（测 AI 系统本身，L4）**——这是最容易混淆的一处。工具总表与降级见 `references/tools.md`。

> 叠加纪律：`dissect.md` §8 路由表与本节叠加项是**同一份清单的两种视图**。每份专项手册必须能在两处都查到触发条件，否则 `scripts/selfcheck.py` 判「孤儿文档」并 FAIL；**不为凑维度造测试**，不适用就写明原因。

---

## 阶段 0：读记忆（先看地图再上路）

按顺序读两份文件，都不存在才从零开始：

1. `<目标项目>/.test-memory/tree.md` —— 项目级记忆树（存在则整份读入，它 <100 行）
2. 本技能目录下 `memory/global-lessons.md` —— 跨项目通用经验

记忆树存在时：

- 复用其中"项目画像"和"命令速查"，**跳过阶段 1 的已知部分**（不重新识别栈、不重新探索入口）
- 模块树只测标记为 ⬜（未测）、◐（部分）、🔥（阻塞，先尝试解锁）的项，以及"已知问题"里待回归的 bug 和"下次待办"
- 用一句话向用户说明接力点（例："上次 10-28 测到支付模块，3 个 bug 未回归，本次从退款流程继续"），用户可以推翻、要求全量重测

记忆树不存在时：完整执行阶段 1，并在阶段 4 用 `assets/tree-template.md` 初始化。

## 阶段 1：解剖项目

目标：用最少的读写建立**可测试的功能地图**。详细手法见 `references/dissect.md`。产出五样：

1. **项目画像**：技术栈、入口文件、启动/测试命令——必须是真实跑通的命令，将来写进记忆树"命令速查"
2. **功能清单**：README 宣称的功能 + 代码实际暴露的功能，**两者的差异本身就是测试点**（文档过时？功能没实现？）
3. **优先级**：风险分 = 影响 × 概率 × 暴露面（见 `test-design.md` §4），P0 核心 / P1 主要 / P2 边缘
4. **测试设施、攻击面、观测面与依赖拓扑**：框架、规范文件、CI、E2E；认证位置、对象 ID、配置/密钥、影子端点；日志/埋点/健康检查、外部依赖清单与故障域；**交付链**（lockfile / 镜像 / 产物 / 签名 / SBOM）、**locale 面**（资源文件 / 格式化调用 / `dir`/`lang`）、**租户边界**（tenant 标识来源 / 共享资源清单 / 隔离策略声明）、**无障碍面**（交互控件 / 认证方式 / 焦点与 ARIA / 目标尺寸 / 读屏支持声明）、**设备形态面**（支持的 OS / 浏览器内核 / 屏幕形态 / 安装量分布数据是否可得）——见 `dissect.md` §6~7
5. **能力层路由**：本项目主用哪些手册（§上表 + v1.1 / v1.2 / v1.3 / v1.4 叠加项）

原则：解剖够用即止——能支撑测试计划就停，不做无死角的代码审读。大型项目只解剖本次范围内的模块。

## 阶段 2：完善测试需求

把功能清单转成**测试矩阵**：每个功能 × 六个维度——正确性 / 边界 / 异常 / 安全 / 性能 / 体验——删掉不适用的维度并**写明原因**，按 P0 > P1 > P2 排序。模板 `assets/test-plan-template.md`。

用 `references/test-design.md` 的九式挑代表值，别靠穷举：等价类、边界值、判定表、状态迁移、成对组合、错误推测、属性测试、蜕变测试、探索式会话。

规模控制：P0 全测，P1 抽核心路径，P2 视时间与用户意向。除非用户已说"直接测"，否则把测试计划简报给用户（一个短清单即可），确认后执行；用户不回应就按 P0 全量 + P1 核心默认执行。发布验收场景直接走六门禁 12 分模型。

## 阶段 3：深度执行——双视角 + 专项

**第一遍：日常用户**（7 个画像见 `references/personas.md`）
按画像走真实工作流：新手什么都不懂乱点乱输、熟练用户跑完整链路、管理员碰权限与配置、国际用户输入 emoji 与本国格式、弱网小屏用户、辅助功能用户、多租户用户。关注：功能对不对、流程顺不顺、出错时提示能不能看懂。

**第二遍：刁钻用户**（8 个画像）
边界值、空/null、超长输入、特殊字符、注入式输入、路径穿越、重复/并发提交、跳步骤直达内部状态、过期凭证、越权改他人 ID、批量分配属性、幂等破坏……（动作清单见 `personas.md`，向量库见 `security-testing.md`）

**专项维度按能力层调用**：

- API → 端点矩阵、RFC 9457 错误契约、认证授权矩阵（BOLA/BFLA）、幂等并发、schema 与 schemathesis → `api-testing.md`
- 安全 → OWASP API Top 10 2023 逐项测试卡、输入向量、依赖审计 → `security-testing.md`
- 性能 → 分位数口径、k6 阈值、瓶颈定位 → `performance-testing.md`
- 前端 → 五态矩阵、WCAG 2.2 最小清单、Core Web Vitals、错误映射、动效运行时纪律 → `frontend-testing.md`
- 全栈 → 测试金字塔、测试隔离、集成边界、六门禁 → `fullstack-integration.md`
- AI 系统 → 评测集、蜕变关系、prompt injection、工具权限、非确定性 → `ai-native-testing.md`
- **链路与可靠性**（v1.1）→ trace/request_id 贯通、SLI/SLO/错误预算 → `observability-testing.md`
- **韧性**（v1.1）→ 稳态假设、故障注入矩阵、恢复验证 → `chaos-resilience.md`
- **数据**（v1.1）→ 三重断言、迁移 up/down、事务隔离与并发不变量 → `data-integrity-testing.md`
- **非 REST 协议**（v1.1）→ GraphQL/gRPC/WS/SSE 逐 operation 矩阵 → `protocol-testing.md` + `assets/protocol-matrix-template.md`
- **交付链与制品**（v1.2）→ 依赖冻结、SBOM 覆盖缺口、签名/provenance 验证、可复现构建两次 digest 比对、CI 完整性 → `supply-chain-testing.md` + `assets/supply-chain-evidence-template.md`
- **国际化 / 本地化**（v1.2）→ locale × 六维矩阵、伪本地化、RTL 与双向文本、格式往返 → `i18n-localization-testing.md` + `assets/i18n-matrix-template.md`
- **多租户隔离**（v1.2）→ 双租户否定路径、共享资源、连接复用、备份恢复、平台管理员 → `multi-tenancy-testing.md` + `assets/tenant-isolation-matrix-template.md`
- **契约演进兼容性**（v1.3）→ oasdiff 破坏性变更、`--fail-on=ERR` 退出码、Pact 消费者契约与 can-i-deploy、容忍读取、影子流量比对 → `contract-evolution-testing.md` + `assets/contract-evolution-matrix-template.md`
- **隐私与数据生命周期**（v1.3）→ PII 分类、响应白名单、批量分配、删除权端到端、日志脱敏 → `privacy-compliance-testing.md` + `assets/privacy-matrix-template.md`
- **测试有效性与经济性**（v1.3 / v1.4）→ DORA 四指标、缺陷逃逸率、flaky 配额、变异得分对照覆盖率、§5A 测试成本/收益 ROI → `test-effectiveness-testing.md` + `assets/test-effectiveness-template.md`
- **无障碍可达性**（v1.4）→ WCAG 2.2 增量 9 条、axe violations + `incomplete` 人工复核、键盘路径与读屏组合、ARIA 快照、2.4.11/2.5.8/3.3.8 → `accessibility-testing.md` + `assets/accessibility-matrix-template.md`
- **跨端与设备形态真实性**（v1.4）→ 设备矩阵来源与载体标注、仿真 vs 真机边界、端侧特有面、网络档位 → `cross-platform-testing.md` + `assets/device-matrix-template.md`

**判定 bug 的标准**（任一命中即算）：

1. 崩溃、异常退出、未捕获报错（500、堆栈裸奔）
2. 报错信息人类看不懂或误导；该报错时不报错（静默失败）
3. 数据损坏、状态错乱、丢数据
4. 安全漏洞（注入、越权、泄漏）
5. 明显不符文档宣称的行为
6. 前端五态缺失 / 焦点不可见 / 仅靠颜色表达状态 / 占位资源未替换（`frontend-testing.md` §8）
7. **跨租户数据或副作用泄漏**（`multi-tenancy-testing.md` §2）、**制品 digest/SBOM/签名对不上**（`supply-chain-testing.md` §7）、**locale 切换后格式漂移或 RTL 未镜像**（`i18n-localization-testing.md` §1/§5）
8. **焦点被整体遮挡 / 目标 <24×24 CSS px 且无例外 / 认证强制认知测试却无替代**（`accessibility-testing.md` §1/§4）、**仿真被写成真机 / 设备矩阵无来源却声称跨端通过**（`cross-platform-testing.md` §7）

严重度 S1 数据损坏·安全·崩溃 ＞ S2 功能错误但有绕过 ＞ S3 体验/提示。缺陷按 `assets/bug-report-template.md` 八字段记录。

**执行手段**按对象选择（工具表与真实命令见 `references/tools.md`）：项目自带测试先跑通 → Web UI 起服务加浏览器自动化（不可用时降级 HTTP 层）→ API 用 curl 实调异常参数矩阵 → CLI/脚本真实执行捕获退出码与输出 → 库写最小调用程序 → 跑不起来则静态审查 + 文档一致性核对，报告中注明局限，记忆树标 🔥。工具缺失一律降级，**不中止**。

**证据纪律**：每个"失败"结论必须附 MRE 最小复现步骤 + 实际输出（命令、输出原文、截图路径）。推测标"待确认"，不得写成事实。指标写清分子/分母/口径。临时探针放 `.test-memory/tmp/`，用完即删。AI 生成的用例与"自愈"后的断言必须人工复核（`ai-native-testing.md` §3）。

**安全边界**：只测用户自己的或明确授权的项目；不对外部服务做压力/DoS 测试；注入类测试仅针对本地授权目标验证防御能力；复现命令中的 token/密码一律脱敏。故障注入只在隔离环境，且先写死中止条件与回滚动作（`chaos-resilience.md` §1）。**多租户测试须构造自己的合成租户与数据，禁止拿真实客户数据做越权验证**（`multi-tenancy-testing.md` §1）。**影子流量只做只读比对，不得对真实用户产生写副作用**。

**八条可证伪规则**（v1.1 引入 R-1/R-2，v1.2 引入 R-3/R-4，v1.3 引入 R-5/R-6，v1.4 引入 R-7/R-8）——规则的价值在于写清「什么时候不适用」：

| 规则 | 结论必须附的证据 | 不适用时的写法 |
|---|---|---|
| **R-1 链路** | 声称"链路完整 / 副作用已发生"，须有同一 `trace_id` 或 `request_id` 贯穿 **≥2 个组件**的原始日志行或 span，并写明采样窗口与样本数 | 单进程、无日志/埋点的 CLI/库/静态页 → 只写「可观测性缺口 / 未做链路验证」，**不得**判 Pass |
| **R-2 韧性** | 声称"依赖故障下仍可用 / 具备韧性"，须附可复现的故障注入记录：注入点、时长、爆炸半径、稳态前后值、对照组、恢复时长、撤销证据 | 无外部依赖、或用户禁止变更环境 → 只写「未做故障注入验证」，**不得**写「具备韧性」 |
| **R-3 制品完整性** | 声称"交付物可信 / 依赖清单完整 / 供应链安全"，须附每个制品的 `sha256` + SBOM 原件（含 direct/transitive、生成器版本、覆盖缺口）+ 签名或 provenance 验证的**命令原文、退出码、输出行** + 扫描输出（工具版本、数据源、时间戳、per-CVE 抑制理由） | 纯源码/脚本/静态页、无构建产物、离线 → 只写「未做制品完整性验证」，**不得**写「供应链安全 / 无已知漏洞」 |
| **R-4 租户隔离** | 声称"租户隔离有效 / 无跨租户泄漏"，须附双租户相同 ID 夹具 + 一票否决四条逐条否定路径结果 + 连接复用、noisy-neighbor、双租户备份恢复三项原始输出 + intentional sharing 的 "no broader access" 证据 | 单租户、无共享资源、禁止构造第二租户 → 只写「未做租户隔离验证 / 不适用」，**不得**写「隔离良好」 |
| **R-5 契约演进** | 声称"API 向后兼容 / 升级可安全部署 / 老客户端不受影响"，须附 ① `oasdiff breaking --fail-on=ERR` 的命令原文 + 退出码 + 输出行（baseline 与修订版明确）；② 若有消费者，Pact verify 绿 + `can-i-deploy` 目标环境退出码 0；③ 容忍读取验证（老客户端对新增字段不报错） | 无对外契约的单体工具、无版本概念 demo → 只写「未做契约演进验证」，**不得**写「向后兼容 / 老客户端不受影响」 |
| **R-6 隐私与数据生命周期** | 声称"隐私合规 / 数据可删除 / 无过度暴露 / 满足 GDPR·个保法"，须附 ① 字段级 PII 分类表 + 每个读接口响应白名单比对（无越权敏感字段）；② 删除权验证（删除后主库 + 缓存/索引/副本不可复原证据）；③ 数据最小化与存储限制证据；④ 日志脱敏核查 | 不处理任何个人数据的纯技术工具、无 PII 离线脚本 → 只写「未做隐私合规验证」，**不得**写「隐私合规 / 满足 GDPR」 |
| **R-7 无障碍可达性** | 声称"符合 WCAG 2.2 AA / 支持读屏 / 可键盘操作 / 无障碍已验收"，须附 ① 目标版本与级别；② `axe-core` 或等价扫描的 violations **+ incomplete 原文**且 incomplete 逐条人工结论；③ 至少一条 P0 流程的完整键盘路径记录（逐步焦点、可见性、2.4.11 遮挡判定）；④ 至少一组读屏 + 浏览器 + OS 组合的逐项 passed/failed/not checked/not present 标注；⑤ 2.5.8 目标尺寸与 3.3.8 认证认知负担实测结论 | 纯 CLI / 无 UI 的库 / 批处理脚本、无图形交互界面 → 只写「不适用：无图形交互界面，未做无障碍实测」，**不得**写「无障碍合规 / 符合 WCAG」；无读屏环境只写「未做读屏实测」，结论降为「待确认」 |
| **R-8 跨端与设备形态真实性** | 声称"移动端可用 / 兼容主流浏览器 / 已适配折叠屏 / 跨端已验证 / 真机验过"，须附 ① 设备矩阵来源（install-base analytics 数据源 + 时间窗）与覆盖占比；② `real`/`emulator`/`simulator`/`browser-emulation` 逐项载体标注；③ 不同浏览器内核实测；④ 长尾条目（低配/最老受支持 OS/厂商皮肤/折叠屏平板）逐条结论或显式未覆盖；⑤ 生命周期、中断、权限、旋转、深链、网络档位的实际输出；⑥ 声称真机须有 ≥1 组 real device 记录 | 纯后端 API / CLI / 无 UI 的库 → 只写「不适用：无终端形态差异，未做跨端验证」，**不得**写「跨端已验证」；只有仿真时写「仅完成仿真验证，未做真机验证」并降为「待确认」，**不得**写「真机验过 / 全平台兼容」 |

详见 `references/observability-testing.md` §8、`references/chaos-resilience.md` §8、`references/supply-chain-testing.md` §7、`references/multi-tenancy-testing.md` §9、`references/contract-evolution-testing.md` §6、`references/privacy-compliance-testing.md` §7、`references/accessibility-testing.md` §5、`references/cross-platform-testing.md` §7。证据不足时结论一律降级为「待确认」，**不许用"没报错"冒充"没问题"**；签名有效 ≠ 软件安全，一条 404 ≠ 隔离通过，axe 0 violations ≠ WCAG 合规，仿真绿 ≠ 真机可用。

## 阶段 4：记忆与进化（本技能的灵魂）

1. **写运行记录** `.test-memory/runs/YYYY-MM-DD-N-<slug>.md`：范围、环境、每个测试点结论、**可复用的真实命令**、bug 复现步骤、产物路径
2. **更新 tree.md**：模块叶节点状态、严重度与回归用例、新增模块、已知问题表、"下次待办"三类（回归/待测/阻塞）
3. **沉淀教训**：项目级 → `.test-memory/lessons.md`；跨项目 → 本技能 `memory/global-lessons.md`
4. **进化检查四问**（`references/evolution.md` §1）：踩了什么坑、什么手法有效、证据够不够、流程哪里不足 → 通用项写 global-lessons.md，`[技能改进]` 提案进提案区
5. **自检**：按 `references/quality-gates.md` §8 打勾（tree.md <100 行、探针已清、失败结论有证据、报告已出），核对 R-1~R-8 是否在不适用的场景里被误判为通过，并确认报告证据矩阵八行都填了结论或「不适用 / 待确认」声明

最后用 `assets/report-template.md` 输出测试报告，**必须给出明确的 `PASS/FAIL` 与 `Go/No-Go`**，禁止"基本可以"。发布验收用 `assets/release-gate-template.md` 打 12 分。

> **权限裁决**：运行时（用本技能测项目）**不自行修改 SKILL.md / references**，只提提案；用户明确授权的「每日升级」任务按 `references/self-evolution.md` 走十步门禁后可改本体并全局安装。即"测项目时不自治，升级技能时授权自治"。

---

## 记忆树速览（完整规范见 `references/memory-tree.md`）

```
<目标项目>/.test-memory/
├── tree.md          # 地图+索引：画像、命令速查、模块树(带状态)、已知问题、下次待办
├── lessons.md       # 项目级经验教训
├── tmp/             # 临时探针，用完即删
└── runs/            # 每次运行的详细记录（保留最近 10 份）
```

```
- [✅] 认证 — 5/5 通过 (10-28) → runs/2026-10-28-1.md
  - [✅] 登录
  - [🐛] 密码重置 — BUG#2 邮箱大写漏校验
- [◐] 支付 — 部分测试 (10-30)
  - [⬜] 退款 — 待测
```

状态标记：`✅` 通过 ｜ `🐛` 有 bug ｜ `⬜` 未测 ｜ `◐` 部分 ｜ `🔥` 阻塞

**省 token 的机制本身**：tree.md 保持 <100 行，细节全部沉到 runs/，树上只留状态与指针。读一份树 = 跳过一次完整解剖。

## 参考索引（渐进披露：主文件只留流程，细节按需读）

| 文件 | 内容 |
|---|---|
| `references/dissect.md` | 解剖：栈指纹、入口、可运行性、测试设施、攻击面、观测面与依赖拓扑、交付链/locale/租户边界/无障碍面/设备形态面、能力层路由 |
| `references/tools.md` | 工具总表、专项工具、可用性探测、降级策略、shell 断言模板 |
| `references/personas.md` | 7 日常 + 8 刁钻画像、判 bug 标准、手册映射 |
| `references/test-design.md` | 测试设计九式、六维矩阵 v2、风险分、覆盖准则与退出标准 |
| `references/api-testing.md` | 端点十项必测、RFC 9457、认证授权、幂等并发、契约与属性测试 |
| `references/security-testing.md` | OWASP API Top 10 2023 逐项测试卡、输入向量、配置与依赖审查 |
| `references/performance-testing.md` | 五种负载、p95 口径、k6 模板、性能预算、瓶颈定位 |
| `references/frontend-testing.md` | 五态矩阵、WCAG 2.2 最小清单、Core Web Vitals、错误映射、动效运行时纪律 |
| `references/fullstack-integration.md` | 测试金字塔、隔离与工厂、集成边界、六门禁 12 分 Go/No-Go |
| `references/quality-gates.md` | 缺陷八字段、严重度矩阵、flaky 治理、覆盖率与变异测试、CI 门禁、R-1~R-8 Go/No-Go |
| `references/ai-native-testing.md` | 四层能力模型、AI for QA vs Testing for AI、AI 生成测试审查、AI 系统评测 |
| `references/observability-testing.md` | 三大信号、Trace 驱动测试、W3C Trace Context、SLI/SLO/错误预算、R-1 可证伪规则 |
| `references/chaos-resilience.md` | 稳态假设、故障注入矩阵、三级工具阶梯、恢复判据、R-2 可证伪规则 |
| `references/data-integrity-testing.md` | 三重断言、迁移 up/down、事务隔离与并发异常、缓存与事件一致性 |
| `references/protocol-testing.md` | GraphQL/gRPC/WebSocket/SSE 逐类型用例清单与命令 |
| `references/supply-chain-testing.md` | 依赖冻结、SBOM 与 NTIA 七要素、签名/provenance、SLSA Build L0~L3、可复现构建、CI 完整性、R-3 |
| `references/i18n-localization-testing.md` | locale × 六维矩阵、伪本地化与伪镜像、collation、W3C RTL/`dir`/`dirname`/`<bdi>`、F-1~F-8 |
| `references/multi-tenancy-testing.md` | 双租户夹具、TC/IDOR/DB/CACHE/QUEUE/FILE/BACKUP/ADMIN 否定路径、R-4 |
| `references/contract-evolution-testing.md` | oasdiff 破坏性变更、Pact 消费者契约、can-i-deploy 闸门、容忍读取、影子流量、Zalando/SemVer、R-5 |
| `references/privacy-compliance-testing.md` | PII 分类与最小化、API3 过度暴露/批量分配、GDPR Art5/17、日志 PII、OWASP 隐私 Top10、R-6 |
| `references/test-effectiveness-testing.md` | DORA 四指标、缺陷逃逸率、flaky 配额、变异得分、§5A 测试经济性/ROI、度量纪律 |
| `references/accessibility-testing.md` | WCAG 2.2 新增 9 条与 2.4.11/2.5.8/3.3.8 精确口径、axe 自动化边界与 incomplete、键盘路径与读屏组合、ARIA 快照、R-7 |
| `references/cross-platform-testing.md` | install-base 设备矩阵与 80% 覆盖、real/emulator/browser-emulation 载体分野、Playwright Emulation、端侧特有面与网络档位、R-8 |
| `references/memory-tree.md` | 记忆树规范、runs/ 格式、省 token 三律 |
| `references/evolution.md` | 运行时进化回路、四问、三层记忆 |
| `references/self-evolution.md` | 每日升级十步协议、权限裁决、版本与变更证据、蒸馏质量门槛 |
| `assets/tree-template.md` | 记忆树初始化模板 |
| `assets/report-template.md` | 测试报告模板（含 PASS/FAIL、Go/No-Go 与 R-1~R-8 证据矩阵） |
| `assets/bug-report-template.md` | 缺陷报告八字段 + MRE |
| `assets/test-plan-template.md` | 测试计划/测试矩阵模板 |
| `assets/release-gate-template.md` | 六门禁 12 分发布验收模板 |
| `assets/protocol-matrix-template.md` | 非 REST 端点矩阵（逐 operation/method + 证据列） |
| `assets/resilience-runbook-template.md` | 故障注入演练记录（稳态/爆炸半径/中止条件/恢复核对） |
| `assets/supply-chain-evidence-template.md` | 制品 digest、SBOM 元数据、验证命令原文、provenance 对照、R-3 结论 |
| `assets/i18n-matrix-template.md` | locale × 六维矩阵、伪本地化、RTL 静态+渲染、F-1~F-8 |
| `assets/tenant-isolation-matrix-template.md` | 双租户否定路径矩阵、特权路径登记、R-4 结论 |
| `assets/contract-evolution-matrix-template.md` | 契约演进矩阵：oasdiff 退出码、Pact/can-i-deploy、容忍读取、R-5 结论 |
| `assets/privacy-matrix-template.md` | 隐私矩阵：PII 分类、响应白名单、删除权、日志脱敏、R-6 结论 |
| `assets/test-effectiveness-template.md` | 测试有效性与经济性：DORA 四指标、逃逸率、flaky、变异得分、ROI 成本/收益 |
| `assets/accessibility-matrix-template.md` | 无障碍矩阵：WCAG 2.2 版本口径、violations/incomplete、键盘路径、读屏组合、R-7 结论 |
| `assets/device-matrix-template.md` | 设备矩阵：来源与覆盖占比、载体标注、端侧特有面、网络档位、真机证据、R-8 结论 |
| `memory/global-lessons.md` | 跨项目经验（开局即读，自我进化载体） |
| `scripts/selfcheck.py` | 升级自检：frontmatter、断链、版本一致、占位资源、模板字段、索引覆盖、路由闭环与规则同步、**报告证据矩阵同步与规则例外声明** |
| `CHANGELOG.md` | 每日升级记录：来源、改动、自检结果 |

## 示例（锁定行为）

用户："帮我测一下 D:\apps\todo 这个项目"

1. 读 `D:\apps\todo\.test-memory\tree.md` → 不存在 → 从零开始
2. 解剖：Node/Express + SQLite；入口 src/server.js；`npm start` 可跑通（记入命令速查）；功能清单 = 增删改查 + 登录；攻击面 = `:id` 直接取数（BOLA 嫌疑）；路由 = API + 安全 + 前端
3. 计划：风险分定价 → P0 = 增/删/查/登录/越权，P1 = 改、过滤，P2 = 导出；六维矩阵用 `test-plan-template.md`
4. 深测：日常用户走查增删查 ✅；刁钻用户发空标题 todo（应 4xx 实际 500 → BUG#1 S2）、标题 10 万字符（界面卡死 → BUG#2 S2）、标题填 `<script>`（未转义 → BUG#3 S1）、A 的 token 改 B 的 todo id（成功 → BUG#4 S1 越权）
5. 记忆：写 `runs/2026-10-30-1-todo.md`（含四条 MRE）；初始化 tree.md，四个 bug 带严重度入"已知问题"；教训"输入校验应统一放中间件 + 对象 ID 必须校验归属"入 lessons.md
6. 交付报告：`FAIL / No-Go`（存在 2 个未闭环 S1）；"下次待办" = 回归四个 bug + 测导出

下次用户再喊"继续测 todo"：直接读 tree.md → 只回归四个 bug + 测导出，**跳过全部解剖**。
