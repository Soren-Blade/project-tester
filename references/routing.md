# 路由与解剖清单（单一事实源）

> 本文件是「项目形态 → 能力层 → 专项手册 → 必做动作 → 规则」的**唯一**清单。
> `SKILL.md` 只留五阶段流程与规则 ID；阶段 1 结束时按 §1/§2 定路由，阶段 3 按 §3 逐条核必做动作。
> **改路由 = 改本文件**。`scripts/selfcheck.py` 校验 `dissect.md §8` ↔ 本文件 ↔ `SKILL.md` 三者集合一致。

## 1. 四层能力模型（阶段 1 末定稿）

| 层 | 能力 | 手册 | 典型触发 |
|---|---|---|---|
| L1 Core | 测试设计、用户画像、缺陷记录、质量门禁 | `references/test-design.md` · `references/personas.md` · `references/quality-gates.md` | 所有项目（无条件必读） |
| L2 Engineering | API、安全、性能、前端、全栈集成 | `references/api-testing.md` · `references/security-testing.md` · `references/performance-testing.md` · `references/frontend-testing.md` · `references/fullstack-integration.md` | REST/GraphQL、Web UI、全栈 |
| L3 Production | 发布门禁、生产验证、Go/No-Go | `references/fullstack-integration.md` §6 · `assets/release-gate-template.md` | 「上线前查一下」「能不能发」 |
| L4 AI Native | AI 辅助测试（横向）+ 测 AI 系统本身（纵向） | `references/ai-native-testing.md` · `references/llm-eval-testing.md`（R-24） | LLM/RAG/Agent；声称「AI 效果好 / 评测通过 / 换了 prompt 提升 X%」 |

> **先分清 “AI for QA”（用 AI 提效，横向）与 “Testing for AI”（测 AI 系统本身，L4）**——这是最容易混淆的一处。
> L1 是底座，任何项目都要读；L2/L3/L4 按形态叠加。**叠加不新增层级**，四层模型与五阶段语义不随专项变化。

## 2. 阶段 1 解剖面清单（22 面，每面一句话作答）

`references/dissect.md` §6~§7 是手法；本表是**必须回答的问题清单**，答不出就写「未确认」。

| 解剖面 | 必须回答 | 见 |
|---|---|---|
| 基础面 | 技术栈、入口文件、真实跑通的启动/测试命令 | `dissect.md` §1~§5 |
| 功能面 | README 宣称 vs 代码实际暴露（**差异本身就是测试点**） | `dissect.md` §3 |
| 测试设施 | 框架、规范文件、CI、E2E、coverage 配置 | `dissect.md` §4 |
| 攻击面 | 认证位置、对象 ID、配置/密钥、影子端点 | `dissect.md` §6 |
| 观测面 | 日志/埋点/健康检查、trace 传递 | `dissect.md` §6 |
| 依赖拓扑 | 外部依赖清单与故障域 | `dissect.md` §6 |
| 交付链 | lockfile / 镜像 / 产物 / 签名 / SBOM | `dissect.md` §6 与 `references/supply-chain-testing.md` |
| locale 面 | 资源文件、格式化调用、`dir`/`lang` | `dissect.md` §6 与 `references/i18n-localization-testing.md` |
| 租户边界 | tenant 标识来源、共享资源清单、隔离策略声明 | `dissect.md` §6 与 `references/multi-tenancy-testing.md` |
| 无障碍面 | 交互控件、焦点与 ARIA、目标尺寸、读屏支持声明 | `dissect.md` §6 与 `references/accessibility-testing.md` |
| 设备形态面 | 支持的 OS/内核/屏幕形态、安装量分布是否可得 | `dissect.md` §6 与 `references/cross-platform-testing.md` |
| 证据链面 | 有无留档要求、合规声明清单、原始输出在哪、commit/环境/时间窗、视觉基线与 install-base | `dissect.md` §6 与 `references/evidence-chain-audit.md` |
| 配置/开关面 | 开关与 kill-switch 清单、默认态/缺失态、目标群体属性来源、三处配置优先级、灰度能力 | `dissect.md` §6 与 `references/feature-flag-testing.md` |
| 测试数据面 | 测试库/fixtures/工厂/种子、来源是否合成、`--seed` 可复现、是否含 PII、迁移数据量 | `dissect.md` §6 与 `references/test-data-management.md` |
| 身份/会话面 | 认证方式、令牌类型与存放位置、会话生命周期、alg/aud/iss 声明、MFA、旁路端点 | `dissect.md` §6 与 `references/auth-session-testing.md` |
| 时间面 | 跨时区用户/定时任务/TTL、UTC 还是 naive、tzdata 版本与配置面、DST 转换日任务 | `dissect.md` §6 与 `references/time-correctness-testing.md` |
| 恢复面 | 备份对象/频率/保留/异地·离线·不可变/加密、最近一次**实际恢复**、RPO·RTO 声明 | `dissect.md` §6 与 `references/backup-recovery-testing.md` |
| 金额面 | 金额字段类型、currency 与 exponent 来源、舍入模式写在哪、分摊与对账文件、客户端能否传金额 | `dissect.md` §6 与 `references/money-correctness-testing.md` |
| 交付面 | webhook 端点与签名方案、是否保留原始 body、`event_id` 去重与窗口、重试/DLQ、沙箱可达性 | `dissect.md` §6 与 `references/webhook-delivery-testing.md` |
| 缓存面 | CDN/反代/共享缓存、`Cache-Control`/`Vary`/`ETag` 由哪层注入、缓存键是否含 tenant、purge 鉴权 | `dissect.md` §6 与 `references/cache-freshness-testing.md` |
| 上传下载面 | 入口与限制层、扩展名与魔数、落盘位置、下载鉴权、presigned 权限与过期 | `dissect.md` §6 与 `references/file-upload-download-testing.md` |
| 查询面 | 列表/搜索/导出端点、分页模式、排序白名单与 tie-breaker、collation 与 NULL、`total` 口径、深页 | `dissect.md` §6 与 `references/query-pagination-testing.md` |
| 错误面 | 错误体形状与 code 体系、5xx 回显、trace_id 可检索、debug 页、401/403/404 策略、`Retry-After` | `dissect.md` §6 与 `references/error-contract-testing.md` |
| 搜索面 | recall→rank 链路、分词器、排序信号、qrels 是否版本化、`q` 是否拼 DSL、零结果兜底 | `dissect.md` §6 与 `references/search-quality-testing.md` |
| 指标面 | 宣称的指标清单、定义卡十项、源表与聚合层、更新时间与截止、SRM、归属人 | `dissect.md` §6 与 `references/metrics-correctness-testing.md` |
| 并发面 | 写路径与并发窗口、幂等键来源与作用域、隔离级别与锁、单实例/多副本、唯一约束、防重复提交 | `dissect.md` §6 与 `references/idempotency-concurrency-testing.md` |
| AI 评测面 | 是否有 LLM/RAG、评测集与版本 hash、判定方式与 judge 模型、模型 pin 与采样参数、基线阈值、成本延迟 | `dissect.md` §6 与 `references/llm-eval-testing.md` |

**解剖够用即止**——能支撑测试计划就停，不做无死角代码审读；大型项目只解剖本次范围内的模块。

## 3. 专项路由表（36 份，阶段 3 逐条核「必做动作」）

| 触发信号 | 手册 | 必做动作（阶段 3 逐条核） | 规则 |
|---|---|---|---|
| REST / GraphQL 接口、有 OpenAPI/proto、多客户端 | `references/api-testing.md` | 端点十项必测（方法·路径·参数·鉴权·幂等·分页·错误·限流·schema·副作用）、RFC 9457 错误体、BOLA/BFLA 授权矩阵、schema 校验与 schemathesis 属性测试 | R-12 · R-19 · R-20 |
| 有登录/支付/上传/用户输入，或声称「安全」 | `references/security-testing.md` | OWASP API Top 10 2023 逐项测试卡、输入向量库（注入·路径穿越·XXE·SSRF·批量分配）、配置与依赖审查、密钥不落日志 | R-6 · R-12 · R-18 |
| 有性能宣称、SLA、长列表或大文件 | `references/performance-testing.md` | 五种负载设计、p95/p99 分位数口径（**不用平均值**）、k6 阈值与失败阈值、瓶颈定位（DB/GC/网络）、结论必须带环境与样本量 | R-19 |
| Web UI / 表单 / 路由 / 样式 / 交互 | `references/frontend-testing.md` | 五态矩阵（空·加载·错误·边界·无权限）、WCAG 2.2 最小清单、Core Web Vitals、错误映射、动效运行时纪律 | R-7 |
| 全栈项目、要在上线前给结论 | `references/fullstack-integration.md` §6 | 测试金字塔与隔离、集成边界、工厂数据、六门禁 12 分（Gate 2/4/6 吸收观测·韧性·数据证据）、回滚预案 | — |
| 用 AI 生成用例 / 自愈断言 | `references/ai-native-testing.md` | 四层能力模型、AI for QA vs Testing for AI、生成用例审查（入库率·断言强度·假通过率）、prompt 注入与工具权限 | — |
| 有 LLM/RAG/Agent，或声称「AI 答得准 / 评测通过 / 提升 X%」 | `references/llm-eval-testing.md` | 评测集构成与污染、n≥3 与固定采样参数、判定器校准（κ≥0.60 且 judge ≠ generator）、Wilson 95% CI、McNemar、失败/超时进分母、p50/p95 与 token 成本、注入与工具越权 | **R-24** |
| 微服务 / 多组件 / 异步链路 / 有日志埋点 | `references/observability-testing.md` | `trace_id` 或 `request_id` 贯通 ≥2 组件、副作用 span、SLI/SLO 与错误预算、日志可检索 | **R-1** |
| 有外部依赖、要验证容错 | `references/chaos-resilience.md` | 稳态假设 → 最小爆炸半径注入 → 恢复验证 → `assets/resilience-runbook-template.md` 留证、先写死中止条件与回滚动作 | **R-2** |
| 有 DB / 迁移 / 缓存 / 多副本 | `references/data-integrity-testing.md` | 三重断言（响应 + DB + 派生状态）、迁移 up/down、事务隔离与并发不变量、缓存与事件一致性 | R-23 |
| GraphQL / gRPC / WebSocket / SSE | `references/protocol-testing.md` + `assets/protocol-matrix-template.md` | 按 operation/method 建矩阵（**不按 URL**）、协议特有错误与授权、WS 心跳与 SSE 重连 | — |
| 有 lockfile / 依赖清单 / 镜像 / 产物 / CI | `references/supply-chain-testing.md` + `assets/supply-chain-evidence-template.md` | 制品 `sha256` + SBOM 原件与覆盖缺口、签名/provenance 命令原文与退出码、锁文件冻结安装、**可复现构建两次 digest 比对**；纯源码/静态页只写「未做制品完整性验证」 | **R-3** |
| 多语言资源 / locale 切换 / 日期货币 / RTL / 跨国输入 | `references/i18n-localization-testing.md` + `assets/i18n-matrix-template.md` | 代表 locale × 六维矩阵、伪本地化四步、`dir`/`dirname`/`<bdi>`/logical properties、F-1~F-8 格式与数据往返；无浏览器时静态审查并标 `BLOCKED` | — |
| SaaS / 多租户 / 共享 DB·cache·queue·storage / platform admin / 共享备份 | `references/multi-tenancy-testing.md` + `assets/tenant-isolation-matrix-template.md` | 双租户**相同 ID** 冲突夹具、TC/IDOR/DB/CACHE/QUEUE/FILE/BACKUP/ADMIN 否定路径、连接复用与 noisy-neighbor、双租户备份恢复；单租户写「不适用：无租户边界」 | **R-4** |
| 有 OpenAPI/GraphQL/proto 且多客户端·多版本在跑 | `references/contract-evolution-testing.md` + `assets/contract-evolution-matrix-template.md` | `oasdiff breaking --fail-on=ERR` 退出码 + 输出行、Pact 消费者契约与 `can-i-deploy` 闸门、容忍读取、**只读影子流量比对**；无对外契约写「未做契约演进验证」 | **R-5** |
| 处理个人数据 / PII / UGC、有隐私政策或合规要求 | `references/privacy-compliance-testing.md` + `assets/privacy-matrix-template.md` | 字段级 PII 分类 + 读接口响应白名单比对、批量分配、删除权端到端（含缓存/索引/副本）、日志脱敏核查；不处理 PII 写「未做隐私合规验证」 | **R-6** |
| 有 CI / 测试套件 / 发布流程，需量化「测试值不值」 | `references/test-effectiveness-testing.md` + `assets/test-effectiveness-template.md` | DORA 四指标（CFR/MTTR 等）、缺陷逃逸率、flaky 配额与 quarantine、变异得分对照覆盖率、§5A 测试经济性/ROI、§5B AI 用例有效性；无自动化测试写「无测试度量基础」 | — |
| 有 UI / 交互，或声称「WCAG 2.2 AA / 支持读屏 / 可键盘操作」 | `references/accessibility-testing.md` + `assets/accessibility-matrix-template.md` | WCAG 2.2 增量 9 条、axe violations **+ incomplete** 人工复核、完整键盘路径、至少一组读屏+浏览器+OS 组合逐项标注、2.4.11/2.5.8/3.3.8 实测；无 UI 写「不适用：无图形交互界面」 | **R-7** |
| 移动端 / 桌面端 / 多浏览器，或声称「真机验过 / 适配折叠屏 / 跨浏览器兼容」 | `references/cross-platform-testing.md` + `assets/device-matrix-template.md` | 设备矩阵来源与覆盖占比、`real`/`emulator`/`simulator`/`browser-emulation` 逐项标注、多内核与长尾条目、端侧特有面与网络档位、§6A 视觉基线留痕；纯后端/CLI 写「不适用：无终端形态差异」 | **R-8** |
| 有移动安装包（`.apk`/`.aab`/`.ipa`/`.app`）、Appium/Maestro/XCUITest/Espresso/Detox，或声称「真机验过 / 权限正常 / 推送正常 / 升级无影响」 | `references/mobile-app-testing.md` + `assets/mobile-app-matrix-template.md` + `scripts/mobile-audit.py` | 构建与分发（bundle id/versionCode/签名/渠道/灰度轨道）、载体矩阵（real/emulator/simulator/cloud-real）、权限四态（允许/拒绝/不再询问/设置撤销）、中断与生命周期、深链冷/温/热启与非法入参、推送前台/后台/杀进程点击路由、覆盖升级保数据与降级/回滚、弱网档位与低电量/Doze；纯 Web 写「不适用：无移动安装包与 OS 集成面」 | **R-25** |
| 有桌面包（Electron/Tauri：`.exe`/`.msi`/`.dmg`/`.app`/`.AppImage`），或声称「进程隔离 / IPC 安全 / 签名公证 / 自动更新正常 / 单实例」 | `references/desktop-app-testing.md` + `assets/desktop-app-matrix-template.md` + `scripts/desktop-audit.py` | 运行时权限声称值 vs 实测（nodeIntegration/contextIsolation/sandbox/fuses 逐项）、IPC 入参矩阵与 sender·路径校验、导航·新窗口·CSP·自定义协议、更新签名与公证命令原文/退出码、降级更新与中断更新、单实例·深链·文件关联、崩溃恢复与版本回滚；纯 Web/CLI 写「不适用：无桌面安装包与本地进程边界」 | **R-26** |
| 有测试报告 / 发布验收 / CI 门禁，需结论可复核；或声称「符合 SOC2/等保/SSDF」「证据链完整」 | `references/evidence-chain-audit.md` + `assets/evidence-chain-template.md` + `scripts/evidence-audit.py` | 结论→证据文件→原始输出的三级引用链逐条可解析（`L<n>` / `text:` 锚点）、证据 `sha256` + commit/环境/时间窗绑定、自动对账与缺口清单、控制项映射与未映射声明、§10 OSCAL 导出；一次性探索写「不适用：无留档要求」 | **R-9** |
| 特性开关 / kill-switch / 远程配置 / 实验开关 / A-B | `references/feature-flag-testing.md` + `assets/flag-rollout-matrix-template.md` | 开关 off 态与**缺失态**回退安全路径、目标群体否定用例、env/文件/远程三处配置漂移比对、kill-switch 真关实测、灰度比例实测；无开关与配置化写「不适用：无开关与配置维度」 | **R-10** |
| 有测试库 / fixtures / 工厂 / 种子脚本，或声称「数据已脱敏 / 合成无 PII / 可复现 / 没用生产数据」 | `references/test-data-management.md` + `assets/test-data-matrix-template.md` + `scripts/test-data-gen.py` | 数据来源声明（合成种子/脱敏命令原文+退出码/明确未用生产数据）、脱敏字段清单 + 残留核查 + 人工复核、同 `--seed` 两次逐字节一致、子集外键悬空数 = 0；无数据依赖写「不适用：无测试数据维度」 | **R-11** |
| 登录 / 会话 / 令牌 / OAuth·OIDC / SSO / MFA / 密码重置 | `references/auth-session-testing.md` + `assets/auth-matrix-template.md` + `scripts/jwt-audit.py` | 令牌清单与存放位置、`alg=none`/算法混淆/空签名负向实测、`exp`/`nbf`/`aud`/`iss`/`typ` 五类负向、登出与改密后旧 access+refresh 均被拒、刷新轮换与 reuse detection、枚举三列对照 + 限流、密码存储参数；纯静态页写「不适用：无身份与会话维度」 | **R-12** |
| 跨时区用户 / 定时任务 / TTL·过期 / 时间排序 | `references/time-correctness-testing.md` + `assets/time-matrix-template.md` + `scripts/time-audit.py` | 存/算/显示三层口径 + tzdata 版本、T-01~T-12 扫描逐条裁决、DST gap/fold 的**实际执行次数**、TTL 前一秒/等于/后一秒三值、时钟回拨与单调时钟、RFC 3339 解析排序与 `-00:00`；无时间维度写「不适用：无时间与时区维度」 | **R-13** |
| 有备份 / 声称「可恢复 / 满足 RPO·RTO」 | `references/backup-recovery-testing.md` + `assets/restore-drill-template.md` + `scripts/restore-audit.py` | RPO/RTO 实测、隔离环境实恢复计时（三段）、行数/hash/外键/`max(id)`/blob/密钥/版本不变量、强校验真读数据、PITR 丢失窗口、删除权与多租户交叉；无持久化写「不适用：无持久化数据与备份面」 | **R-14** |
| 下单 / 支付 / 扣款 / 退款 / 多币种 / 对账 | `references/money-correctness-testing.md` + `assets/money-matrix-template.md` + `scripts/money-audit.py` | ISO 4217 exponent 与存储类型、舍入模式与所在层、展示价/应付额/实扣额/入账额四层对齐、分摊守恒（最大余额法）、借贷平衡与不可变分录、并发重复扣款与超卖、退款累计 ≤ 实付、渠道对账差异；无资金流写「不适用：无交易金额」 | **R-15** |
| webhook / 回调 / 队列消费 / 重试 / DLQ | `references/webhook-delivery-testing.md` + `assets/webhook-delivery-matrix-template.md` + `scripts/webhook-audit.py` | 签名覆盖字段与原始 body 复算（正例 + 篡改 body/时间戳/错密钥反例）、容忍窗实测、同 `event_id` 串行+并发副作用 = 1、退避与重启续投、乱序终态、DLQ 与渠道对账；无异步交付写「不适用：无异步交付」 | **R-16** |
| CDN / 反向代理 / 共享缓存 / 发布即生效 | `references/cache-freshness-testing.md` + `assets/cache-freshness-matrix-template.md` + `scripts/cache-audit.py` | 四层分层与策略来源、缓存键与 `Vary`（含身份/tenant）、双会话串号实测、缓存欺骗（扩展名 vs `Content-Type`）、purge 鉴权与失效、`stale-while-revalidate` 滥用；无共享缓存写「不适用：无共享缓存面」 | **R-17** |
| 文件上传 / 下载 / presigned URL | `references/file-upload-download-testing.md` + `assets/upload-security-matrix-template.md` + `scripts/upload-audit.py` | 三道闸（扩展名白名单/魔数与 `Content-Type`/解码重编码）、绕过矩阵（双扩展·大小写·ADS·前导点·空字节·SVG·ZIP）、落盘与执行权限、下载 IDOR 与 `Content-Disposition`、presigned bearer 与断签复用；无文件进出口写「不适用：无文件上传下载面」 | **R-18** |
| 列表 / 搜索 / 导出 / 排序端点 | `references/query-pagination-testing.md` + `assets/query-pagination-matrix-template.md` + `scripts/query-audit.py` | 三模式契约、**全量遍历去重条数 == total**、翻页插删的重复与遗漏、`ORDER BY` 唯一 tie-breaker、排序白名单与注入、collation/NULL 位置、深页 p95、行级授权与 `total` 泄漏；无列表端点写「不适用：无查询与分页面」 | **R-19** |
| 有 HTTP 接口，或要排查「出错了查不到哪条日志」 | `references/error-contract-testing.md` + `assets/error-contract-matrix-template.md` + `scripts/error-audit.py` | 三层契约（码/code/message+trace_id）、状态码矩阵与 401/403/404/409/422 判据、5xx 防泄漏硬门禁（堆栈·路径·SQL·内网主机·版本·调试页）、trace_id 与日志双向检索、存在性三态、错误路径副作用与重试分类、生产默认核对；无 HTTP 写「不适用：无 HTTP 错误契约」 | **R-20** |
| 有搜索框 / 召回 / 排序 | `references/search-quality-testing.md` + `assets/search-quality-matrix-template.md` + `scripts/search-audit.py` | qrels 0~3 分级与加权 κ≥0.60、分层 nDCG@10/MRR@10/Recall@10/零结果率 + bootstrap CI、DCG/IDCG 手算、查询理解九类、排序稳定性两次 top-20 逐位 diff、`search_after`/`max_result_window`/`track_total_hits`、filter vs post_filter、highlight XSS 与 DSL 注入；纯精确查询写「不适用：无相关性排序面」 | **R-21** |
| 有看板 / 报表 / 对外宣称的指标 | `references/metrics-correctness-testing.md` + `assets/metrics-correctness-matrix-template.md` + `scripts/metric-audit.py` | 定义卡十项、dashboard·API·源表三处对账与双阈值、七类口径陷阱、可加性与辛普森、SRM 卡方（`p<0.001`）、新鲜度 p50/p95 与重述、k<10 抑制；无指标产出写「不适用：无指标口径面」 | **R-22** |
| 写路径（下单/支付/领券/扣库存/唯一资源）、多副本、队列消费与超时重试，或声称「幂等 / 防重复 / 不会超卖 / 加了锁」 | `references/idempotency-concurrency-testing.md` + `assets/idempotency-concurrency-matrix-template.md` + `scripts/concurrency-audit.py` | 写路径与并发窗口清单、不变量先行（余额=Σ流水 / 库存≥0 / 一键一资源）、真并发屏障（N≥10，非 `sleep` 假并发）、幂等键六格矩阵（同键同体/同键异体/不同键同体/键过期/跨用户/归一化）、锁与事务六类漏点、唯一约束→409、fencing token、`side-effects` 事件对账；纯只读写「不适用：无并发写路径」 | **R-23** |

## 4. 元手册（L1 底座，任何项目都读）

| 文件 | 用途 | 何时读 |
|---|---|---|
| `references/dissect.md` | 解剖手法（栈指纹、入口、可运行性、测试设施、攻击面、观测面、依赖拓扑） | 阶段 1 |
| `references/tools.md` | **工具总表（21 个脚本的唯一登记处）**、可用性探测、降级策略、shell 断言模板 | 阶段 1 / 阶段 3 选手段 |
| `references/personas.md` | 7 日常 + 8 刁钻画像、判 bug 5 标准、手册映射 | 阶段 3 两遍执行 |
| `references/test-design.md` | 测试设计九式、六维矩阵 v2、风险分、覆盖准则与退出标准 | 阶段 1~2 |
| `references/quality-gates.md` | 缺陷八字段、严重度矩阵、判 bug 15 条、**R-1~R-26 证据要求全文**、flaky、覆盖率/变异、CI 门禁、阶段 4 自检 | 阶段 3 判缺陷 / 阶段 4 自检 |
| `references/memory-tree.md` | 记忆树规范、runs/ 格式、省 token 三律 | 阶段 0 / 阶段 4 |
| `references/evolution.md` | 运行时进化回路、四问、三层记忆 | 阶段 4 |
| `references/self-evolution.md` | 每日升级十步协议、权限裁决、版本与变更证据、蒸馏质量门槛 | 升级技能时（非测项目时） |
| `memory/global-lessons.md` | 跨项目通用经验（开局即读，自我进化载体） | 阶段 0 |

**模板**在 `assets/`（34 份，专项模板按 `<主题>-matrix-template.md` 命名，由本表 §3 对应行指向）。
**脚本**在 `scripts/`（21 个零依赖脚本，全部带 `--self-test`；命令与降级路径见 `references/tools.md`）。

## 5. 叠加纪律（三条硬约束）

1. **不为凑维度造测试**：不适用就写明「不适用：<原因>」，不得省略成沉默。
2. **同一份清单的三种视图**：`dissect.md §8` 给路由、本文件给触发条件与必做动作、`SKILL.md` 给规则 ID 与流程。任何一份漏了某手册，`scripts/selfcheck.py` 判「孤儿文档」FAIL。
3. **降级不中止**：工具缺失按 `references/tools.md` 降级执行；结论不足一律降为「待确认」，**不得**用「没报错」冒充「没问题」。
