# project-tester — 通用项目深度测试技能

> 一个会**自我进化**的测试 Skill：解剖任意项目 → 按风险生成测试需求 → 双视角深测 → 记忆树接力 → 每日蒸馏升级。不绑定语言、框架或 agent。

![version](https://img.shields.io/badge/version-v1.2.0-1677ff)
![references](https://img.shields.io/badge/reference_files-21-2ea44f)
![assets](https://img.shields.io/badge/templates-10-e60023)
![updated](https://img.shields.io/badge/updated-2026-11-11-6e7781)

---

## 它解决什么问题

| 问题 | 本 Skill 的解法 |
|---|---|
| 换个项目又从零探索 | `.test-memory/tree.md` 记忆树接力：画像与命令速查直接复用，跳过解剖 |
| 用例靠拍脑袋、穷举不完 | `test-design.md` 九式设计 + 风险分优先级 + 六维矩阵 v2 |
| 只测"能用"，漏掉越权与注入 | `security-testing.md` 逐条对齐 OWASP API Top 10 2023；`api-testing.md` 认证授权矩阵与 BOLA 用例 |
| 错误契约各端点不一样 | RFC 9457 `application/problem+json` 校验点 + 状态码矩阵 |
| "挺快的"没有依据 | `performance-testing.md` 分位数口径、Little's Law、k6 阈值、轻量 shell 降级 |
| 前端状态没做全、无障碍过不了 | `frontend-testing.md` 五态矩阵、WCAG 2.2、Core Web Vitals、错误码映射、动效运行时纪律 |
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
| 工具装不齐就测不下去 | `tools.md` 全表带降级路径，零依赖也能走完五阶段 |
| 升级无记录、越更越乱 | `self-evolution.md` 十步门禁 + `CHANGELOG.md` + `scripts/selfcheck.py` 自检（含路由闭环与可证伪规则同步） |

---

## 文件结构（37 个文件）

```
project-tester/
├── SKILL.md                          # 主流程：五阶段 + 能力层路由 + R-1~R-4 + 参考索引
├── README.md                         # 本文件
├── CHANGELOG.md                      # 每日升级记录（来源 / 改动 / 自检）
├── .gitignore
├── references/                       # 21 份手册（渐进披露，按需读）
│   ├── dissect.md                    # 解剖：栈指纹 / 入口 / 测试设施 / 攻击面 / 观测面 / 交付链 / locale / 租户边界 / 路由
│   ├── tools.md                      # 工具总表 / 专项工具 / 可用性探测 / 降级纪律
│   ├── personas.md                   # 7 日常 + 8 刁钻画像 / 判 bug 标准 / 手册映射
│   ├── test-design.md                # 测试设计九式 / 六维矩阵 v2 / 风险分 / 覆盖与退出标准
│   ├── api-testing.md                # 端点十项必测 / RFC 9457 / 认证授权 / 幂等并发 / 契约与属性测试
│   ├── security-testing.md           # OWASP API Top 10 2023 逐项测试卡 / 输入向量 / 配置与依赖审查
│   ├── performance-testing.md        # 五种负载 / p95 口径 / k6 模板 / 性能预算 / 瓶颈定位
│   ├── frontend-testing.md           # 五态矩阵 / WCAG 2.2 / CWV / 错误映射 / i18n 联动
│   ├── fullstack-integration.md      # 测试金字塔 / 隔离与工厂 / 集成边界 / 六门禁 12 分
│   ├── quality-gates.md              # 缺陷八字段 / 严重度 / flaky / 变异测试 / CI 门禁 / 交付核对
│   ├── ai-native-testing.md          # 四层能力模型 / AI for QA vs Testing for AI / 评测集
│   ├── observability-testing.md      # 三大信号 / Trace 驱动 / W3C Trace Context / SLO 与错误预算 / R-1
│   ├── chaos-resilience.md           # 稳态假设 / 故障注入矩阵 / 三级工具阶梯 / 恢复判据 / R-2
│   ├── data-integrity-testing.md     # 三重断言 / 迁移 up-down / 事务隔离与并发 / 缓存与事件一致性
│   ├── protocol-testing.md           # GraphQL / gRPC / WebSocket / SSE 逐类型测试卡与命令
│   ├── supply-chain-testing.md       # 依赖冻结 / SBOM 与 NTIA 七要素 / 签名与 SLSA provenance / CI 完整性 / R-3
│   ├── i18n-localization-testing.md  # locale × 六维矩阵 / 伪本地化与伪镜像 / collation / W3C RTL / F-1~F-8
│   ├── multi-tenancy-testing.md      # 双租户夹具 / TC·IDOR·DB·CACHE·QUEUE·FILE·BACKUP·ADMIN 否定路径 / R-4
│   ├── memory-tree.md                # 记忆树规范 / runs 格式 / 省 token 三律
│   ├── evolution.md                  # 运行时进化回路 / 四问 / 三层记忆
│   └── self-evolution.md             # 每日升级十步协议 / 权限裁决 / 版本与蒸馏门槛
├── assets/                           # 10 份模板
│   ├── tree-template.md              # 项目记忆树初始化
│   ├── report-template.md            # 测试报告（强制 PASS/FAIL 与 Go/No-Go）
│   ├── bug-report-template.md        # 缺陷报告八字段 + MRE
│   ├── test-plan-template.md         # 测试计划 / 六维矩阵
│   ├── release-gate-template.md      # 六门禁 12 分发布验收
│   ├── protocol-matrix-template.md   # 非 REST 端点矩阵（逐 operation/method + 证据列）
│   ├── resilience-runbook-template.md # 故障注入演练记录（稳态 / 爆炸半径 / 中止 / 恢复）
│   ├── supply-chain-evidence-template.md  # 制品 digest / SBOM / 验证命令原文 / provenance 对照 / R-3
│   ├── i18n-matrix-template.md       # locale × 六维矩阵 / 伪本地化 / RTL 静态+渲染 / F-1~F-8
│   └── tenant-isolation-matrix-template.md # 双租户否定路径矩阵 / 特权路径登记 / R-4
├── memory/
│   └── global-lessons.md             # 跨项目经验（开局即读，自我进化载体）
└── scripts/
    └── selfcheck.py                  # 升级自检：frontmatter / 断链 / 版本一致 / 占位 URL / 模板字段 / 路由闭环 / 规则同步
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
| 测多语言 / RTL / 跨国格式 | `i18n-localization-testing.md` + `assets/i18n-matrix-template.md` |
| 测多租户会不会串数据 | `multi-tenancy-testing.md` + `assets/tenant-isolation-matrix-template.md`（R-4） |
| 不知道该测哪些点 | `test-design.md` + `test-plan-template.md` |
| 写缺陷报告 | `bug-report-template.md` + `quality-gates.md` §2 |
| 判断测试是否可信 | `quality-gates.md` §5 + SKILL.md 的 R-1~R-4 可证伪规则 |
| 升级本技能 | `self-evolution.md` + `CHANGELOG.md` |

## 设计要点

- **通用性**：不绑定语言/框架/agent，只用通用能力（文件读写、shell、按需浏览器）；工具缺失自动降级，不中止
- **省 token**：被测项目根下 `.test-memory/tree.md`（<100 行）是接力地图，细节沉到 `runs/`；读一份树 = 跳过一次完整解剖
- **证据优先**：每个失败结论必须有 MRE + 实际输出；指标写清分子/分母；报告强制给出 `PASS/FAIL` 与 `Go/No-Go`
- **分层能力**：L1 Core → L2 Engineering → L3 Production → L4 AI Native，按项目形态路由；v1.1 起按项目形态**横向叠加**观测/韧性/数据/协议专项，v1.2 再叠加交付链/本地化/租户隔离，均不新增层级
- **路由闭环**：每份专项手册必须同时出现在 `dissect.md` §8 路由表与 `SKILL.md` 叠加项，由 `scripts/selfcheck.py` 逐份核对，缺一即 FAIL（不再只是文字约定）
- **可证伪**：R-1（链路）、R-2（韧性）、R-3（制品完整性）、R-4（租户隔离）四条规则都写清「什么情况下不适用」，证据不足只能降级为「待确认」，不许用"没报错"冒充"没问题"
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
→ ⑥ python scripts/selfcheck.py（FAIL=0 才继续：断链 / 版本 / 路由闭环 / 规则同步）+ 回归检查
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
| v1.2.0 | 2026-11-11 | 每日升级 #3：从「系统行为」扩展到「交付链与边界正确性」——软件供应链/制品完整性、i18n 与本地化、多租户隔离；吸收 i18n 提案，新增 R-3/R-4；把「孤儿文档门禁」真正落进 `selfcheck.py` 并补齐 `performance-testing.md` 路由（[详见 CHANGELOG](CHANGELOG.md)） |
| v1.1.0 | 2026-11-11 | 每日升级 #2：从「响应断言」扩展到「系统内部行为验证」——可观测性/Trace 驱动、韧性与故障注入、数据一致性、非 REST 协议端点；吸收 GraphQL/gRPC 提案；新增 R-1/R-2 可证伪规则（[详见 CHANGELOG](CHANGELOG.md)） |
| v1.0.0 | 2026-11-11 | 每日升级 #1：分层能力 + 9 份专项手册 + 3 份模板 + 证据化门禁 + 自我进化协议 + 自检脚本（[详见 CHANGELOG](CHANGELOG.md)） |
| v0 | ~2026-10-30 | 基线：五阶段流程 + 5 份 references + 2 份模板 |

---

**许可**：自由使用与改造。蒸馏来源与参考链接见 `CHANGELOG.md` 与 `references/self-evolution.md`。
