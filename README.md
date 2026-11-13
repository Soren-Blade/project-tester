# project-tester — 通用项目深度测试技能

> 一个会**自我进化**的测试 Skill：解剖任意项目 → 按风险生成测试需求 → 双视角深测 → 记忆树接力 → 每日蒸馏升级。不绑定语言、框架或 agent。

![version](https://img.shields.io/badge/version-v1.7.0-1677ff)
![references](https://img.shields.io/badge/reference_files-29-2ea44f)
![assets](https://img.shields.io/badge/templates-18-e60023)
![scripts](https://img.shields.io/badge/scripts-4-6f42c1)
![updated](https://img.shields.io/badge/updated-2026-11-13-6e7781)

---

## 它解决什么问题

| 问题 | 本 Skill 的解法 |
|---|---|
| 换个项目又从零探索 | `.test-memory/tree.md` 记忆树接力：画像与命令速查直接复用，跳过解剖 |
| 用例靠拍脑袋、穷举不完 | `test-design.md` 九式设计 + 风险分优先级 + 六维矩阵 v2 |
| 只测"能用"，漏掉越权与注入 | `security-testing.md` 逐条对齐 OWASP API Top 10 2023；`api-testing.md` 认证授权矩阵与 BOLA 用例 |
| 错误契约各端点不一样 | RFC 9457 `application/problem+json` 校验点 + 状态码矩阵 |
| "挺快的"没有依据 | `performance-testing.md` 分位数口径、Little's Law、k6 阈值、轻量 shell 降级 |
| 前端状态没做全、无障碍过不了 | `frontend-testing.md` 五态矩阵、WCAG 2.2 最小清单、Core Web Vitals、错误码映射、动效运行时纪律 |
| 本地能跑 ≠ 能上线 | `fullstack-integration.md` 六门禁 12 分 Go/No-Go + 回滚预案 |
| 测试"绿了"其实没杀伤力 | `quality-gates.md` 缺陷八字段、flaky 治理、覆盖率 vs 变异得分 |
| AI 生成测试藏伪断言 / AI 系统不会测 | `ai-native-testing.md`：AI for QA 与 Testing for AI 分离、自愈陷阱、评测集与蜕变关系 |
| HTTP 200 但链路断了、消息没发 | `observability-testing.md`：trace_id/request_id 贯通断言、副作用 span、SLI/SLO 与错误预算 |
| 只在依赖正常时测过，一挂就崩 | `chaos-resilience.md`：稳态假设 → 最小爆炸半径故障注入 → 恢复验证 + 演练记录模板 |
| 只验响应没验库，并发下双花 | `data-integrity-testing.md`：三重断言、迁移 up/down、隔离级别与并发不变量 |
| GraphQL/gRPC/WS/SSE 套 REST 矩阵漏测 | `protocol-testing.md` + `protocol-matrix-template.md`：按 operation/method 逐类型用例清单 |
| **功能全绿，但部署的制品不是被验证过的那个** | `supply-chain-testing.md`：制品 digest、SBOM 覆盖缺口、签名/provenance 验证、SLSA Build 判级、CI 完整性；R-3 要求命令原文 + 退出码 + 输出行 |
| **换个语言/地区就截断、串格式、RTL 没镜像** | `i18n-localization-testing.md`：代表 locale × 六维矩阵、伪本地化四步、W3C `dir`/`dirname`/`<bdi>`、F-1~F-8 格式与数据往返 |
| **共享 DB/cache/queue 上一个租户串到另一个** | `multi-tenancy-testing.md`：双租户相同 ID 夹具、分层否定路径、连接池复用、备份恢复、平台管理员越界；R-4 不认"一条 404" |
| **改了代码老客户端全挂 / API 升级不敢发** | `contract-evolution-testing.md`：oasdiff 破坏性变更检测、`--fail-on=ERR` 退出码、Pact 消费者契约与 can-i-deploy 闸门、容忍读取；R-5 不认"本地能跑" |
| **返回里夹带密码/多给数据 / 数据删不干净 / 日志漏 PII** | `privacy-compliance-testing.md`：PII 字段分类、响应白名单比对、批量分配、删除权端到端、GDPR Art5/17、日志脱敏；R-6 不认"接口 200" |
| **测试一堆但发布还翻车 / 覆盖率虚高** | `test-effectiveness-testing.md`：DORA 四指标（CFR/MTTR）、缺陷逃逸率、flaky 配额与 quarantine、变异得分对照覆盖率 |
| **axe 报 0 violations，辅助功能用户仍走不完流程** | `accessibility-testing.md`：WCAG 2.2 新增 9 条与 2.4.11/2.5.8/3.3.8 精确口径、自动化约 57% 边界与 `incomplete` 人工复核、完整键盘路径 + 读屏组合逐项标注；R-7 不认"扫描全绿" |
| **桌面 Chrome 通过，换台真机就崩** | `cross-platform-testing.md`：install-base 设备矩阵与约 80% 覆盖、`real`/`emulator`/`browser-emulation` 载体分野、端侧特有面与网络档位；R-8 不认"仿真 = 真机" |
| **测试越堆越多，说不清值不值** | `test-effectiveness-testing.md` §5A：建设/运行/维护成本、反馈时间收益、逃逸避免成本、选测/并行/缓存收益，与有效性指标合并成 ROI 口径 |
| **同一 commit 两次构建产物不一样** | `supply-chain-testing.md` §2A 可复现构建：固定 build inputs/environment/instructions、逐位或 hash 比对、时间戳与随机排序口径；R-3 证据增强 |
| **契约测试过了，线上真实流量行为仍不一致** | `contract-evolution-testing.md` §3A 影子流量：只读镜像比对响应与派生状态、脱敏与采样口径，不产生写副作用 |
| **报告结论看着全，却没人能按证据重放；说「合规」却挂不上控制项** | `evidence-chain-audit.md`：PROV 三级引用链、OSCAL/SSDF 控制项映射、`scripts/evidence-audit.py` 自动对账（悬空引用 / 过期证据 / 锚点失效 / PASS 无证据 / 未分类结论）；**R-9 不认「报告写全了 / 证据文件都在 / 对账 GREEN」** |
| **设备矩阵靠拍脑袋列机型 / 视觉基线被 `--update-snapshots` 悄悄换掉** | `cross-platform-testing.md` §6A + `scripts/device-matrix.py`：本地 install-base 导出算占比 / 累计 / 80% 截断点，固定输出 CrUX 口径局限；基线更新留旧/新 hash + 理由 + 批准人，载体列人工填 |
| **AI 一口气生成 200 条用例，其实没杀伤力** | `test-effectiveness-testing.md` §5B：入库率 / 断言强度合格率 / 变异杀伤贡献 / **假通过率**（故意改坏代码应转红）/ 审查人时，E-15~E-18；审查 diff 登记进 manifest |
| **功能对，但开关关掉系统就崩 / 灰度说 5% 实际全开 / 配置三处不一致 / 废弃开关没删干净** | `feature-flag-testing.md`：开关 off 态与缺失态回退安全路径、目标群体否定用例、env/文件/远程三处配置比对、kill-switch 真关实测、灰度比例实测；**R-10 不认「开态测过」、不认「配置三处没比对」、不认「说 5% 没实测」** |
| **喂给测试的数据被当成可信，实则漏了生产 PII / 每次跑都不一样的随机样本 / 掩码只盖了已知字段 / 连生产库抽数** | `test-data-management.md`：数据来源声明、合成数据 + 确定性种子、PII 保留格式掩码 + 残留核查、子集外键完整性、绝不用生产数据；**R-11 不认「用了生成器」、不认「掩码了已知字段」、不认「无种子却说可复现」** |
| 工具装不齐就测不下去 | `tools.md` 全表带降级路径，零依赖也能走完五阶段 |
| 升级无记录、越更越乱 | `self-evolution.md` 十步门禁 + `CHANGELOG.md` + `scripts/selfcheck.py` 自检（路由闭环、规则同步、报告矩阵、例外声明） |

---

## 文件结构（56 个文件）

```
project-tester/
├── SKILL.md                          # 主流程：五阶段 + 能力层路由 + R-1~R-11 + 参考索引
├── README.md                         # 本文件
├── CHANGELOG.md                      # 每日升级记录（来源 / 改动 / 自检）
├── .gitignore
├── references/                       # 29 份手册（渐进披露，按需读）
│   ├── dissect.md                    # 解剖：栈指纹 / 入口 / 测试设施 / 攻击面 / 观测面 / 交付链 / locale / 租户 / a11y / 设备形态 / 开关 / 路由
│   ├── tools.md                      # 工具总表 / 专项工具 / 可用性探测 / 降级纪律
│   ├── personas.md                   # 7 日常 + 8 刁钻画像 / 判 bug 标准 / 手册映射
│   ├── test-design.md                # 测试设计九式 / 六维矩阵 v2 / 风险分 / 覆盖与退出标准
│   ├── api-testing.md                # 端点十项必测 / RFC 9457 / 认证授权 / 幂等并发 / 契约与属性测试
│   ├── security-testing.md           # OWASP API Top 10 2023 逐项测试卡 / 输入向量 / 配置与依赖审查
│   ├── performance-testing.md        # 五种负载 / p95 口径 / k6 模板 / 性能预算 / 瓶颈定位
│   ├── frontend-testing.md           # 五态矩阵 / WCAG 2.2 最小清单 / CWV / 错误映射 / a11y 与跨端联动
│   ├── fullstack-integration.md      # 测试金字塔 / 隔离与工厂 / 集成边界 / 六门禁 12 分
│   ├── quality-gates.md              # 缺陷八字段 / 严重度 / flaky / 变异测试 / CI 门禁 / R-1~R-11 交付核对
│   ├── ai-native-testing.md          # 四层能力模型 / AI for QA vs Testing for AI / 评测集
│   ├── observability-testing.md      # 三大信号 / Trace 驱动 / W3C Trace Context / SLO 与错误预算 / R-1
│   ├── chaos-resilience.md           # 稳态假设 / 故障注入矩阵 / 三级工具阶梯 / 恢复判据 / R-2
│   ├── data-integrity-testing.md     # 三重断言 / 迁移 up-down / 事务隔离与并发 / 缓存与事件一致性
│   ├── protocol-testing.md           # GraphQL / gRPC / WebSocket / SSE 逐类型测试卡与命令
│   ├── supply-chain-testing.md       # 依赖冻结 / SBOM / 签名与 SLSA provenance / 可复现构建 / CI / R-3
│   ├── i18n-localization-testing.md  # locale × 六维矩阵 / 伪本地化 / collation / W3C RTL / F-1~F-8
│   ├── multi-tenancy-testing.md      # 双租户夹具 / TC·IDOR·DB·CACHE·QUEUE·FILE·BACKUP·ADMIN 否定路径 / R-4
│   ├── contract-evolution-testing.md # oasdiff / Pact / can-i-deploy / 影子流量 / Zalando·SemVer / R-5
│   ├── privacy-compliance-testing.md # PII 分类与最小化 / API3 / GDPR Art5·17 / 日志 PII / R-6
│   ├── test-effectiveness-testing.md # DORA 四指标 / 逃逸率 / flaky / 变异得分 / §5A 测试经济性·ROI / §5B AI 生成用例有效性
│   ├── accessibility-testing.md     # WCAG 2.2 增量 9 条 / 2.4.11·2.5.8·3.3.8 / axe 边界与 incomplete / 键盘路径·读屏组合 / R-7
│   ├── cross-platform-testing.md    # 设备矩阵与 80% 覆盖 / 载体分野 / Playwright Emulation / 端侧特有面·网络档位 / §6A 视觉基线治理与 install-base 导出 / R-8
│   ├── memory-tree.md                # 记忆树规范 / runs 格式 / 省 token 三律
│   ├── evolution.md                  # 运行时进化回路 / 四问 / 三层记忆
│   ├── self-evolution.md             # 每日升级十步协议 / 权限裁决 / 版本与蒸馏门槛
│   ├── feature-flag-testing.md       # 开关默认态/缺失态安全 / 目标群体隔离 / env/文件/远程配置漂移 / kill-switch 真关实测 / 灰度比例实测 / FF-1~FF-12 / R-10
│   ├── test-data-management.md       # 合成数据生成 / PII 脱敏与掩码 / 确定性种子 / 数据子集与制备 / 绝不用生产数据 / R-11 / §8 路由
│   └── evidence-chain-audit.md       # PROV 三级引用链 / OSCAL·SSDF 合规声明对账 / in-toto 与 GitHub attestations / manifest 与自动对账 / §10 manifest→OSCAL / EA-1~EA-13 / R-9
├── assets/                           # 18 份模板
│   ├── tree-template.md              # 项目记忆树初始化
│   ├── report-template.md            # 测试报告（强制 PASS/FAIL 与 Go/No-Go，含 R-1~R-11 证据矩阵）
│   ├── bug-report-template.md        # 缺陷报告八字段 + MRE
│   ├── test-plan-template.md         # 测试计划 / 六维矩阵
│   ├── release-gate-template.md      # 六门禁 12 分发布验收
│   ├── protocol-matrix-template.md   # 非 REST 端点矩阵（逐 operation/method + 证据列）
│   ├── resilience-runbook-template.md # 故障注入演练记录（稳态 / 爆炸半径 / 中止 / 恢复）
│   ├── supply-chain-evidence-template.md  # 制品 digest / SBOM / 验证命令原文 / provenance 对照 / R-3
│   ├── i18n-matrix-template.md       # locale × 六维矩阵 / 伪本地化 / RTL 静态+渲染 / F-1~F-8
│   ├── tenant-isolation-matrix-template.md # 双租户否定路径矩阵 / 特权路径登记 / R-4
│   ├── contract-evolution-matrix-template.md # oasdiff 退出码 / Pact·can-i-deploy / 容忍读取 / R-5
│   ├── privacy-matrix-template.md    # PII 分类 / 响应白名单 / 删除权 / 日志脱敏 / R-6
│   ├── test-effectiveness-template.md # DORA 四指标 / 逃逸率 / flaky / 变异得分 / ROI 成本·收益
│   ├── accessibility-matrix-template.md # WCAG 2.2 版本口径 / violations·incomplete / 键盘路径 / 读屏组合 / R-7
│   ├── device-matrix-template.md     # 矩阵来源·覆盖占比 / 载体标注 / 端侧特有面 / 网络档位 / 真机证据 / R-8
│   ├── evidence-chain-template.md    # 三级引用链（R-1~R-10）/ 控制项映射 / 缺口清单 / 锚点原文 / 审计导出留痕 / R-9 结论
│   └── flag-rollout-matrix-template.md # 开关/配置/灰度验证矩阵：四类必测面 / 目标群体否定用例 / 三处配置比对 / kill-switch 实测 / 灰度比例 / R-10 结论
│   └── test-data-matrix-template.md # 测试数据管理矩阵：数据来源 / 确定性种子 / PII 脱敏残留核查 / 子集外键完整性 / 无生产数据声明 / R-11 结论
├── memory/
│   └── global-lessons.md             # 跨项目经验（开局即读，自我进化载体）
└── scripts/                          # 4 个零依赖 Python 脚本（标准库，无外部包）
    ├── evidence-audit.py             # 证据链自动对账：audit --manifest / --fail-on-gap / --format json|markdown|oscal / --output / --self-test
    ├── device-matrix.py              # install-base 本地导出汇总：build --input/--source/--window/--min-coverage / --self-test
    ├── test-data-gen.py              # 测试数据生成与脱敏：generate --seed / mask --fields / self-test；确定性、保留格式掩码、诚实边界（不联网/不代填/不冒充/不保证无泄漏）
    └── selfcheck.py                  # 升级自检：frontmatter / 断链 / 版本 / 占位 URL / 模板字段 / 路由闭环 / 规则同步 / 报告矩阵 / 例外声明 / §7f 脚本门禁
```

## 知识资产速查

| 想做什么 | 读哪个 |
|---|---|
| 测一个 REST 服务 | `api-testing.md` + `security-testing.md` |
| 测 GraphQL / gRPC / WS / SSE | `protocol-testing.md` + `assets/protocol-matrix-template.md` |
| 测一个网页 / 前端 | `frontend-testing.md` + `personas.md` |
| 验证链路贯通 / 异步副作用 | `observability-testing.md` §3 |
| 定义 SLO 与错误预算发布门禁 | `observability-testing.md` §4 |
| 做故障注入 / 韧性演练 | `chaos-resilience.md` + `assets/resilience-runbook-template.md` |
| 验迁移 / 并发写 / 缓存一致性 | `data-integrity-testing.md` |
| 测全栈能不能上线 | `fullstack-integration.md` §6 + `release-gate-template.md` |
| 做压力 / 性能验证 | `performance-testing.md` |
| 测 LLM / RAG / Agent 应用 | `ai-native-testing.md` |
| 验制品是不是被改过 / SBOM 全不全 | `supply-chain-testing.md` + `assets/supply-chain-evidence-template.md`（R-3） |
| 做可复现构建比对 | `supply-chain-testing.md` §2A（固定 inputs/environment/instructions、逐位或 hash 比对） |
| 测多语言 / RTL / 跨国格式 | `i18n-localization-testing.md` + `assets/i18n-matrix-template.md` |
| 测多租户会不会串数据 | `multi-tenancy-testing.md` + `assets/tenant-isolation-matrix-template.md`（R-4） |
| 验 API 升级老客户端会不会挂 / 契约向后兼容 | `contract-evolution-testing.md` + `assets/contract-evolution-matrix-template.md`（R-5） |
| 用影子流量比对真实请求的行为差异 | `contract-evolution-testing.md` §3A（只读、脱敏、无写副作用） |
| 验隐私合规 / 数据可删除 / 返回没多给 / 日志无 PII | `privacy-compliance-testing.md` + `assets/privacy-matrix-template.md`（R-6） |
| 量化测试有效性 / 变更失败率 / flaky / 变异得分 | `test-effectiveness-testing.md` + `assets/test-effectiveness-template.md` |
| 算测试成本 / ROI / 自动化投入值不值 | `test-effectiveness-testing.md` §5A + `assets/test-effectiveness-template.md` |
| 验无障碍 / WCAG 2.2 AA / 读屏与键盘路径 | `accessibility-testing.md` + `assets/accessibility-matrix-template.md`（R-7） |
| 验移动端 / 真机 / 设备矩阵 / 跨浏览器 | `cross-platform-testing.md` + `assets/device-matrix-template.md`（R-8） |
| 让测试结论可被别人复核 / 对账合规声明 | `evidence-chain-audit.md` + `assets/evidence-chain-template.md` + `scripts/evidence-audit.py`（R-9） |
| 按真实安装量定设备矩阵 / 治理视觉快照基线 | `cross-platform-testing.md` §6A + `scripts/device-matrix.py` |
| 判断 AI 生成的一堆用例有没有杀伤力 | `test-effectiveness-testing.md` §5B + `ai-native-testing.md` §3 |
| 不知道该测哪些点 | `test-design.md` + `test-plan-template.md` |
| 写缺陷报告 | `bug-report-template.md` + `quality-gates.md` §2 |
| 判断测试是否可信 | `quality-gates.md` §5 + SKILL.md 的 R-1~R-10 可证伪规则 |
| 验特性开关 / 配置漂移 / 灰度放量 / kill-switch 能止血 | `feature-flag-testing.md` + `assets/flag-rollout-matrix-template.md`（R-10） |
| 验测试数据可信 / 合成数据无 PII 泄漏 / 数据可复现 / 没用生产数据 | `test-data-management.md` + `assets/test-data-matrix-template.md` + `scripts/test-data-gen.py`（R-11） |
| 把证据链导出成 OSCAL assessment-results 喂给 GRC/审计工具 | `evidence-chain-audit.md` §10 + `scripts/evidence-audit.py --format oscal` |
| 升级本技能 | `self-evolution.md` + `CHANGELOG.md` |

## 设计要点

- **通用性**：不绑定语言/框架/agent，只用通用能力（文件读写、shell、按需浏览器）；工具缺失自动降级，不中止
- **省 token**：被测项目根下 `.test-memory/tree.md`（<100 行）是接力地图，细节沉到 `runs/`；读一份树 = 跳过一次完整解剖
- **证据优先**：每个失败结论必须有 MRE + 实际输出；指标写清分子/分母；报告强制给出 `PASS/FAIL` 与 `Go/No-Go`
- **分层能力**：L1 Core → L2 Engineering → L3 Production → L4 AI Native，按项目形态路由；v1.1 起按项目形态**横向叠加**观测/韧性/数据/协议专项，v1.2 叠加交付链/本地化/租户隔离，v1.3 叠加契约演进/隐私/有效性，v1.4 叠加无障碍/跨端/测试经济性，v1.5 叠加证据链对账/视觉基线与 install-base 数据源/AI 用例有效性，v1.6 叠加特性开关/配置/灰度正确性与证据链 OSCAL `assessment-results` 导出，v1.7 叠加测试数据管理（合成数据/PII 脱敏/确定性种子/子集制备/绝不用生产数据），均不新增层级
- **路由闭环**：每份专项手册必须同时出现在 `dissect.md` §8 路由表与 `SKILL.md` 叠加项，由 `scripts/selfcheck.py` 逐份核对，缺一即 FAIL（不再只是文字约定）
- **可证伪**：R-1（链路）、R-2（韧性）、R-3（制品完整性）、R-4（租户隔离）、R-5（契约演进）、R-6（隐私与数据生命周期）、R-7（无障碍可达性）、R-8（跨端与设备形态真实性）、R-9（证据链可追溯与可复核性）、R-10（特性开关 / 配置 / 灰度正确性）、R-11（测试数据可信与合规）**十一条**规则都写清「什么情况下不适用」，证据不足只能降级为「待确认」，不许用"没报错"冒充"没问题"——R-5 不认"本地能跑"、R-6 不认"接口 200"、R-7 不认"axe 0 violations"、R-8 不认"仿真绿"、R-9 不认"报告写全了 / 证据文件都在 / 对账 GREEN"、R-10 不认"开态测过 / 配置三处没比对 / 说 5% 没实测"、**R-11 不认"用了生成器 / 掩码了已知字段 / 无种子却说可复现"**
- **证据闭环（v1.4 / v1.5）**：`selfcheck.py` 的代码门禁——`§7d` **逐条核对** `report-template.md` 证据矩阵的 `| R-N |` 表格行（v1.5 负向测试实证加固：旧版只统计整段编号，说明文字里的编号可蒙混），`§7e` 强制每条规则写清禁止冒充声明，**`§7f`（v1.5）强制可执行脚本自带 `--self-test` 与诚实边界声明**；新增规则却忘了留证据槽位、写清降级路径，或新增脚本只会打 PASS，自检直接 FAIL
- **可执行且诚实（v1.5）**：`scripts/evidence-audit.py`（本地确定性证据链对账）与 `scripts/device-matrix.py`（本地 install-base 导出汇总）只用 Python 标准库、不联网、不修改被测项目；前者固定输出「对账通过只证明证据链可解析，不证明合规或软件安全」，后者不代填 `real` 载体、不写「真机已验证」，缺数据源就显式标注不可作为 R-8 证据
- **证据可机读（v1.6）**：`scripts/evidence-audit.py` 新增 `--format oscal`，把 manifest 的「结论→证据→锚点」链按 `references/evidence-chain-audit.md` §10 字段映射导出为 OSCAL `assessment-results` JSON，让 R-9 证据链能直接喂给 GRC/审计工具；只做字段搬运，不裁决合规——`待确认`/缺口在 OSCAL 里仍是 `partial`/`gap`，**不得**因「有了 OSCAL 文件」写成「已通过 OSCAL 合规评估」（EA-13 已纳入 `--self-test` 对等性校验）
- **自我进化**：项目教训 → `.test-memory/lessons.md`；通用教训 → `memory/global-lessons.md`；每日升级 → `CHANGELOG.md` + 版本号
- **权限裁决**：**测项目时不自治**（运行时只提 `[技能改进]` 提案），**升级技能时授权自治**（用户明确授权的每日任务，走十步门禁）

## 安装位置

- 源（改动只改这里）：`D:\My Skills\project-tester\`
- 全局安装（所有项目、所有支持 `.agents/skills` 约定的 agent 可用）：`C:\Users\摩羯座\.agents\skills\project-tester\`
- GitHub 仓库：`https://github.com/Soren-Blade/project-tester`

改完源后同步并校验：

```bash
cp -r "/d/My Skills/project-tester/." "$HOME/.agents/skills/project-tester/"
diff -r "/d/My Skills/project-tester" "$HOME/.agents/skills/project-tester" --exclude=.git --exclude=.workbuddy-ai
```

## 每日升级流程

```
① 读 automation memory + CHANGELOG → ② 联网查权威资料并记来源 → ③ 深度蒸馏成可执行规则
→ ④ 治理分类（Existing/Enhance/Merge/Match/New）→ ⑤ 只改本文件夹
→ ⑥ python scripts/selfcheck.py（FAIL=0 才继续：断链 / 版本 / 路由闭环 / 规则同步 / 报告矩阵 / 例外声明 / §7f 脚本门禁）
   + 两个 scripts 的 --self-test 退出码为 0 + 回归检查 + 负向测试（临时副本破坏一处，确认确实 FAIL）
→ ⑦ 升版本 + 写 CHANGELOG → ⑧ 同步全局安装 + diff 校验
→ ⑨ git commit（`feat(vN): 每日升级 #M <主题>`）+ push → ⑩ 回写执行记忆
```

自检命令：

```bash
cd "D:/My Skills/project-tester" && python scripts/selfcheck.py
```

## 版本历史

| 版本 | 日期 | 主题 |
|---|---|---|
| v1.7.0 | 2026-11-13 | 每日升级 #8：从「结论可复核」扩展到「**喂给测试的数据本身可信 · 合规 · 可复现**」——测试数据管理（TDM）：合成数据生成、PII 脱敏/掩码、确定性种子、数据子集与制备、绝不用生产数据；新增 **R-11**、`references/test-data-management.md`、`assets/test-data-matrix-template.md`、`scripts/test-data-gen.py`（零依赖：generate/mask/self-test、保留格式掩码、诚实边界）；蒸馏来源含 Thoughtworks/K2view/DATPROF/IRI 与用户附加技能 `fullstack-dev`（`testing-strategy.md` factories/"no production data"/seeds）、`frontend-dev`（`--seed` 可复现）；R-11 不认「用了生成器 / 掩码了已知字段 / 无种子却说可复现」（[详见 CHANGELOG](CHANGELOG.md)） |
| v1.6.0 | 2026-11-12 | 每日升级 #7：从「结论可复核」扩展到「**动态正确 · 配置可信 · 开关可控 · 合规可机读**」——特性开关/配置/灰度正确性（Knight Capital 废弃开关反例、默认态/缺失态安全、目标群体隔离、env/文件/远程配置漂移、kill-switch 真关实测、灰度比例实测）；新增 **R-10**、`references/feature-flag-testing.md`、`assets/flag-rollout-matrix-template.md`；落地一个 v1.5 顺延提案：把 `scripts/evidence-audit.py` 的 manifest 增加 `--format oscal` 导出 OSCAL `assessment-results` JSON（`evidence-chain-audit.md` §10 字段映射），让 R-9 证据链可机读；EA-13 纳入 `--self-test` 对等性校验（[详见 CHANGELOG](CHANGELOG.md)） |
| v1.5.0 | 2026-11-12 | 每日升级 #6：从「结论正确」扩展到「**结论可复核 · 声称可对账**」——证据链可追溯与合规声明对账（PROV / OSCAL / SSDF v1.1 / in-toto / GitHub attestations）、设备矩阵真实安装量数据源采集、视觉回归基线治理、AI 生成用例有效性度量；新增 **R-9**、`references/evidence-chain-audit.md`、`assets/evidence-chain-template.md` 与两个带 `--self-test` 的零依赖脚本；落地两个顺延提案（Merge 为主，不新增强化手册）；`selfcheck.py` 新增 §7f 脚本可证伪性门禁（[详见 CHANGELOG](CHANGELOG.md)） |
| v1.4.0 | 2026-11-12 | 每日升级 #5：从「系统正确」扩展到「人人可用 · 处处可用 · 值得测」——无障碍可达性深度实测（WCAG 2.2 / 键盘 / 读屏）、跨端与设备形态真实性（设备矩阵 / 仿真 vs 真机）、测试经济性 ROI；新增 R-7/R-8；落地三个顺延提案；新增 `selfcheck.py` §7d/§7e 两条门禁；修正「四条规则 / R-1~R-4」历史漂移（[详见 CHANGELOG](CHANGELOG.md)） |
| v1.3.0 | 2026-11-11 | 每日升级 #4：从「边界正确性」扩展到「演进与合规正确性」——API 契约演进兼容性（oasdiff/Pact/SemVer）、隐私与数据生命周期（PII/GDPR/日志）、测试有效性度量（DORA/flaky/变异得分）；新增 R-5/R-6；把证据矩阵接进 `report-template.md`（[详见 CHANGELOG](CHANGELOG.md)） |
| v1.2.0 | 2026-11-11 | 每日升级 #3：从「系统行为」扩展到「交付链与边界正确性」——软件供应链/制品完整性、i18n 与本地化、多租户隔离；吸收 i18n 提案，新增 R-3/R-4；把「孤儿文档门禁」真正落进 `selfcheck.py` 并补齐 `performance-testing.md` 路由（[详见 CHANGELOG](CHANGELOG.md)） |
| v1.1.0 | 2026-11-11 | 每日升级 #2：从「响应断言」扩展到「系统内部行为验证」——可观测性/Trace 驱动、韧性与故障注入、数据一致性、非 REST 协议端点；吸收 GraphQL/gRPC 提案；新增 R-1/R-2 可证伪规则（[详见 CHANGELOG](CHANGELOG.md)） |
| v1.0.0 | 2026-11-11 | 每日升级 #1：分层能力 + 9 份专项手册 + 3 份模板 + 证据化门禁 + 自我进化协议 + 自检脚本（[详见 CHANGELOG](CHANGELOG.md)） |
| v0 | ~2026-10-30 | 基线：五阶段流程 + 5 份 references + 2 份模板 |

---

**许可**：自由使用与改造。蒸馏来源与参考链接见 `CHANGELOG.md` 与 `references/self-evolution.md`。
