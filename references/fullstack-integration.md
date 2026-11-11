# 全栈集成与发布验收手册（阶段 2/3 · 全栈项目）

> 蒸馏自用户附加技能 `fullstack-dev` 主文档及其 `fullstack-dev/references/testing-strategy.md`、`fullstack-dev/references/release-checklist.md`（6 门禁 12 分模型），以及 `naodeng/awesome-qa-skills` 的 Engineering / Production 能力层。以下路径均指**该外部技能内**的文件，不是本技能目录。
> 定位：项目「能跑通」不等于「能上线」。本手册负责**测试金字塔、集成边界、六道发布门禁**。

## 1. 测试金字塔与选型（先决定在哪一层测）

```
         ╱╲        E2E (~10%)   完整用户流，跨服务，1~30s
        ╱  ╲
       ╱────╲      Integration (~20%)  API + 真 DB + mock 外部，50~500ms
      ╱      ╲
     ╱────────╲    Unit (~70%)  纯逻辑无 I/O，<10ms
    ╱__________╲
   横向：Contract（服务边界，<100ms）｜Performance（关键路径）
```

| 层级 | 该测 | 不该测 | 常见坑 |
|---|---|---|---|
| 单测 | 业务规则、纯函数、边界 | DB、网络、HTTP 类型 | mock 一切导致"绿但没用" |
| 集成 | 路由 + 真 DB + 副作用 | mock 掉 service 层 | 用内存 DB 假装是 Postgres |
| E2E | 关键用户旅程 | 每个分支都来一遍 | 慢、脆、flaky |
| 契约 | 服务间请求/响应结构 | 业务逻辑 | 只在单侧验证 |

**铁律**：集成测试用真 DB（事务回滚 / truncation / testcontainers），单测才 mock repository；**永远不要在集成测试里 mock service 层**。

## 2. 测试隔离与测试数据

| 策略 | 速度 | 真实度 | 何时 |
|---|---|---|---|
| 事务回滚（默认） | 最快 | 中 | 单测 + 集成，`beforeEach` 开事务 `afterEach` 回滚 |
| Truncation | 快 | 高 | 回滚不可用 |
| Testcontainers | 启动慢 | 最高 | CI 全流程，`tmpfs` RAM 盘提速 |

- 用**工厂**（faker / factory_boy）而非硬编码数据；每个用例自带 setup/teardown，不依赖执行顺序
- 迁移必须能从零跑通一次（CI 里做），且 down migration 测过
- 常见故障速查：测试单独过、一起挂 → 共享状态；`Jest did not exit` → 连接/服务没关；异步超时 → 漏 `await`

## 3. 全栈集成检查点（`fullstack-dev` Step 4 的测试化扩充）

| 边界 | 测试点 | 通过判据 |
|---|---|---|
| 构建 | 前后端分别 `npm run build` | 无错误、无类型错 |
| 启动 + 冒烟 | `/health` → 200、`/ready` → 依赖全绿 | 依赖挂时 `/ready` 返回 503 且 `/health` 仍 200 |
| CORS | 允许源放行、其他源拒绝 | 生产**不是** `*` |
| API base URL | 来自环境变量，非硬编码 | 换 env 后指向正确 |
| Auth 携带 | token 自动 attach；401 触发 refresh 后透明重试一次 | 刷新失败跳登录，不无限重试 |
| 类型安全 | 前后端共享类型 / OpenAPI codegen / tRPC | 边界字段改名能被编译期发现 |
| 实时（若有） | SSE 自动重连与 `req.on('close')` 退订；WS 心跳 ping/pong 与断线重连 | 双标签页同步、无泄漏订阅 |
| 文件上传 | 大文件走 presigned URL；FormData **不手动设** `Content-Type` | 类型/大小/文件名校验生效 |
| 优雅停机 | SIGTERM 后停止接新连接、排空在途、关 DB | 不丢在途请求 |

**降级**：起不了服务就静态核对配置项 + 文档一致性，`tree.md` 标 🔥 并写明卡点，绝不静默跳过。

## 4. 契约测试与 Schema 校验

- 消费者驱动（Pact）：consumer 定义期望 → 生成 pact 文件 → provider 在 CI 里 `verifyProvider()`
- 有 OpenAPI 就跑 schema diff 与 schemathesis（见 `api-testing.md` §7）
- 错误信封按 RFC 9457 统一；前端按状态码映射人话（见 `frontend-testing.md` §5）
- 向后兼容：老客户端 payload 打新版接口不能破

## 5. 可观测性与韧性（属于"测得到"的前提）

| 项 | 最小验证 |
|---|---|
| 结构化日志 | 输出 JSON、含 `request_id`；**不含**密码/token/PII |
| request_id 贯通 | 一次请求从入口到外部调用的日志都能用同一 id 串起来 |
| 超时 | 每个外部调用都设了 timeout（mock 一个永不返回的依赖验证） |
| 重试 | 瞬时失败指数退避；4xx 不重试；重试上限后进入死信/告警 |
| 限流 | 超阈值返回 429 + `Retry-After` |
| 优雅降级 | 非核心依赖挂掉时主流程仍可用（断路器） |
| 幂等 | 后台任务重复执行结果一致（不能"假定恰好一次"） |

**v1.1 分流**：§5 是「测得到」的最小前提清单；要把每项变成断言，见 `references/observability-testing.md`（链路贯通、span、SLI/SLO 与错误预算）；要验证依赖挂掉时的行为，见 `references/chaos-resilience.md`（稳态假设 + 故障注入 + 恢复验证）；写入后的库/缓存/事件一致性见 `references/data-integrity-testing.md`。Gate 2（非功能）、Gate 4（部署与回滚）、Gate 6（发布后验证）应吸收这三类证据，并在 `assets/release-gate-template.md` 逐门留证。

**v1.2 分流（三类新证据各自归门，不重复计分）**：

| 新证据 | 归入 | 说明 |
|---|---|---|
| `references/supply-chain-testing.md` 的 digest / SBOM / 签名 / provenance（R-3） | **Gate 3 + Gate 4** | Gate 3 看依赖侧漏洞与抑制，Gate 4 看「部署的制品是否就是被验证过的那个」；纯源码项目标「不适用」，不倒扣也不冒充通过 |
| `references/i18n-localization-testing.md` 的 locale × 六维矩阵（含 RTL、格式往返） | **Gate 1** | 属于「需求都实现了吗」在多语言下的等价验收；无浏览器时静态审查标 BLOCKED，不填 2 分 |
| `references/multi-tenancy-testing.md` 的双租户否定路径（R-4） | **Gate 1 + Gate 3** | 功能验收要证明 T1 看不到 T2，安全审查要证明每条 tenant-owned path 都有授权边界；单租户标「不适用」 |

> 打分纪律：这三类证据是**对应门的「有证据地完整验证」(2 分) 的前置条件**，不是额外加分项。缺证据时该门最高 1 分，并在 `assets/release-gate-template.md` 写明缺口。

## 6. 六道发布门禁（12 分 Go/No-Go）

每道 0~2 分：`0` 未检查 ｜ `1` 部分检查 ｜ `2` 有证据地完整验证。

| Gate | 问题 | 关键证据 |
|---|---|---|
| 1 功能验收 | 需求都实现了吗？ | 验收标准 ↔ 用例 ↔ 结果对照表；happy/边界/异常/数据完整性/向后兼容/幂等；**多语言/RTL 场景按 `i18n-localization-testing.md` 的 locale 矩阵复验** |
| 2 非功能验收 | 快、稳、可观测吗？ | p95/p99 实测值、错误率、N+1 检查、`EXPLAIN ANALYZE`、缓存命中率、`/health` `/ready`、日志与告警 |
| 3 安全审查 | 安全吗？ | 见 `security-testing.md`：输入校验、BOLA/BFLA、上传、限流、密钥、`npm audit`/`pip-audit`/`govulncheck`；**多租户项目另加 R-4 否定路径矩阵**（`multi-tenancy-testing.md` §2）；**有发布产物另加 R-3 制品完整性证据**（`supply-chain-testing.md` §7） |
| 4 部署就绪 | 能安全部署与回滚吗？ | CI 全绿、lint/build、迁移在类生产数据上测过且 down 可用、`.env.example`、回滚预案、**制品 `sha256` + SBOM 原件 + 签名/provenance 验证输出、CI 流水线完整性静态审查** |
| 5 发布执行 | 怎么放？ | 公告 → 迁移 → 金丝雀 10%→50%→100% → 冒烟 → 监控 30 分钟 |
| 6 发布后验证 | 真的好了吗？ | 0~30min 健康检查/错误率/延迟/核心旅程/日志/告警；1~24h 客诉、业务指标、内存 CPU、队列积压 |

| 总分 | 决策 |
|---|---|
| **12/12** | Ship ✅ |
| **10~11** | 允许发布，但必须写明例外项 + 指定负责人 + 补齐日期 |
| **< 10** | **No-Go**，先补缺口 |

**金丝雀停止线**（示例，按项目校准）：错误率 > 0.5% 立即停、> 1% 回滚；p95 > 700ms 停、> 1000ms 回滚。

> 常见自欺：「改动很小」「本地测过了」「CI 过了」「上次也没事」「随时能回滚」——回滚只有在**预案写过且演练过**时才成立。逐次跑门禁，不靠幸存者偏差。

## 7. 本技能如何使用这份门禁

- 用户说"上线前查一下 / 验收 / 能不能发" → **直接按 §6 打分**，输出 `assets/release-gate-template.md` 报告
- 用户只说"测一下" → 不做完整 6 门禁，但 Gate 1~3 的高风险项纳入测试矩阵
- 分数与证据写入 `runs/`，Next Todo 写入 `tree.md`；下次接力可直接从缺口开始

## 8. 反模式（继承 fullstack-dev Anti-Patterns 的测试视角）

| ❌ | ✅ |
|---|---|
| 集成测试全 mock，跑得飞快但啥也没验证 | 真 DB + HTTP 层 mock 外部 |
| 测试依赖执行顺序 | 每例自 setup/teardown |
| 生产数据拿来测 | 只用生成的测试数据 |
| 全套 > 10 分钟还硬跑 | 并行、RAM 盘、按变更选测 |
| 用"CI 绿了"代替门禁 | CI 只覆盖一部分，逐门留证据 |
