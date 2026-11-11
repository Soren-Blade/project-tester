# 可观测性驱动测试（阶段 1/3 · 服务化与分布式项目）

> 蒸馏自 OpenTelemetry Traces / Semantic Conventions、W3C Trace Context、Tracetest 官方文档与仓库、Google SRE Book《Service Level Objectives》，以及用户附加技能 `fullstack-dev` 的「结构化日志 + request_id」与 `frontend-dev` 的运行时质量门禁。
> 定位：**响应体只是系统行为的一小部分**。本手册把「看不见的链路、异步副作用、长尾与可靠性目标」变成可断言的测试用例。

## 1. 响应断言的三个盲区

| 盲区 | 典型漏报 | 本手册的补法 |
|---|---|---|
| 链路中间层 | HTTP 200，但下游被调用 3 次、或走了错误的 fallback | §3 用 span 数量/层级/属性断言 |
| 异步副作用 | 接口返回成功，消息没进队列、事件没发、缓存没失效 | §3 Tracetest 式副作用断言 / §5 日志核对 |
| 时间窗与长尾 | 单次请求很快，但 p99 超标、错误预算已耗尽 | §4 SLI/SLO 变成可断言的门禁 |

前提：**可观测性是"测得到"的前提**。埋点缺失本身就是缺陷（记为「可观测性缺口」），不是"测试跳过"。

## 2. 三大信号的最小测试判据

| 信号 | 最小证据 | 通过判据 | 零依赖降级 |
|---|---|---|---|
| Logs | 一次请求的 2 条以上原始日志行 | 结构化 JSON、含同一 `request_id`、**不含**密码/token/PII/堆栈 | `curl -si` 触发请求 → `grep` 日志文件按 id 串联 |
| Metrics | 计数/直方图在请求前后各一份采样 | 分子分母可解释，时间窗与口径写明 | shell 循环 + `sort`/`awk` 算分位数（见 `references/performance-testing.md` §3） |
| Traces | 同一 `trace_id` 下 ≥2 个组件各 1 个 span | 父子层级正确、无断链、`status` 无 `Error` | 若完全无埋点 → 判「缺口」，用日志 `request_id` 降级 |

三者都要过**脱敏检查**：日志/span attributes 里出现 `Authorization`、完整 cookie、身份证/手机号、`password=` 即 S2 缺陷。

## 3. Trace 驱动测试：把链路当断言对象

### 3.1 必须知道的格式（W3C Trace Context）

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
             ^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^ ^^
           version      32 hex trace-id        16 hex parent-id  flags
```

- `trace-id` / `parent-id` 全零非法；`flags` 最低位为 `sampled`。
- **最低合规**：中间服务必须把 `traceparent`（及收到的 `tracestate`）转发给出站请求，保证 trace 不断；除「重启 trace」外 `trace-id` 不得改变。
- OTel `Span Context` = `Trace ID` + `Span ID` + `Trace Flags` + `Trace State`，是不可变对象，随上下文跨进程传播；根 span 的 `parent_id` 为空。
- Span `status` 三态：`Unset`（默认，无错误）/ `Error`（如 HTTP 500）/ `Ok`（开发者显式标记）。**`Unset` 不等于"验过了"**。
- 属性建议在 **span 创建时**添加，这样 SDK 采样策略才能用到它们；带独立时间戳的单点事件用 `Span Event`，否则用 `Attribute`。
- 语义约定（统一命名如 `http.request.method`、`db.system`、`error.type`）的价值是跨库/跨语言可关联；属性名各服务自造 = 断言写不出来。

### 3.2 五步最小实验（无需任何平台）

```bash
# ① 用自定义 traceparent 发一次请求，把 trace-id 留作证据
TID=4bf92f3577b34da6a3ce929d0e0e4736
curl -s -o /tmp/resp.json -w "HTTP %{http_code} %{time_total}s\n" \
  -H "traceparent: 00-$TID-00f067aa0ba902b7-01" \
  -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:3000/api/orders/8f3a
# ② 在入口日志 / 下游日志 / 队列生产者日志里查同一个 id
grep -rn "$TID" ./logs ./var/log 2>/dev/null | head -20
# ③ 断言：命中组件数 ≥2（链路贯通），且没有第二条不同的 trace-id 出现在出站请求里
```

降级：项目无日志、无 tracing 后端时，用「注入永不返回的依赖 + 记录超时时间」验证 timeout 生效，并明确写「链路可观测性未验证」。**不得把"没有证据"写成"链路正常"**。

### 3.3 断言清单（直接抄进测试矩阵）

| # | 断言 | 判据 | 抓什么 bug |
|---|---|---|---|
| 1 | 同一请求所有 span 共享 `trace_id` | 100% 命中，无新根 | 上下文丢失、异步线程断链 |
| 2 | 关键 span 存在且顺序正确 | `http.server → service → db → cache` | 该调的没调、顺序颠倒 |
| 3 | 子 span 数量在上限内 | 例如单个请求 DB span ≤ 3 | N+1、重复调用、无缓存 |
| 4 | span 时长阈值 | `attr:tracetest.span.duration < 100ms` | 慢查询、串行调用 |
| 5 | 通配断言 | 所有 gRPC span 返回码 = `0`；所有 db span < 100ms | 局部失败被 200 掩盖 |
| 6 | 副作用 span 存在 | MQ publish / 外部 API / 异步任务各 1 个 | 事件没发出、消费者没触发 |
| 7 | `status` 无 `Error`，且错误路径有 `error.type` | 显式检查 | 静默失败、错误信息缺失 |
| 8 | 属性脱敏 | 无 token/PII/完整 body | 敏感信息进日志 |

工具（可选，非前置）：Tracetest 用 `trigger + selector + assertions` 的 YAML 定义，可直接把上表写成机器可执行的用例：

```yaml
type: Test
spec:
  trigger:
    type: http
    httpRequest: { url: "http://127.0.0.1:3000/api/orders", method: POST }
  specs:
    - name: "All Database Spans: 处理时间 < 100ms"
      selector: span[tracetest.span.type="database"]
      assertions:
        - attr:tracetest.span.duration < 100ms
```

`tracetest run test --file <yaml>` 可进 CI。**工具缺失就用 §3.2 的 curl + grep 降级**，不中止测试。

## 4. SLI / SLO / 错误预算：把可靠性目标变成门禁

| 概念 | 定义 | 测试化动作 |
|---|---|---|
| SLI | 对服务水平的**定量测量**；应按分布（p50/p95/p99）而非平均值表述 | 先固定分子/分母/时间窗/测量点，再写断言 |
| SLO | SLI 的目标值或范围，且**必须说明测量方式与生效条件** | 写成可判定句：`过去 28 天内，valid events 中 good events 占比 ≥ 99.9%` |
| SLA | 含「未达成后果」的用户合同 | 测试报告不评判 SLA |
| 错误预算 | 允许 SLO 未达成的比率（1 − SLO），按日/周跟踪 | 预算耗尽 → 发布门禁自动 No-Go |

**推荐句式**（照填即可）：

```
在 <时间窗/聚合间隔> 内，<纳入的 valid events> 中 <good events> 的比例 ≥ <target>%；
测量范围：<全部后端实例 / 黑盒探测>；获取方式：<服务端埋点 / 客户端 RUM>；聚合方式：<1 分钟平均>。
```

判据纪律：

- SLO 里必须写清 `valid events` 与 `good events`，否则"99.9%"不可证伪 —— 例如 5xx 算 bad，但 4xx 不一定算。
- **不要按当前性能反推目标**；目标要少、要简单、别写 "100% 可用"。
- 报告里把「实测 SLI」「SLO 目标」「预算余量」三列并排；预算耗尽时即使功能全绿也写 `No-Go`（并入 `references/fullstack-integration.md` §6 Gate 2/6）。
- 与 `references/performance-testing.md` 的分工：那边测**单次负载下的表现**，这边测**时间窗内的目标达成与发布决策**。

## 5. 日志与 request_id 的静态 + 动态核对

静态（`git grep`，项目跑不起来也能做）：

- 是否结构化 JSON 输出（而非 `console.log` 拼字符串）
- 中间件顺序是否含 request-id 且贯穿到外部调用
- 是否 log 了 `password` / `token` / 完整请求体；生产是否 debug 级
- 是否有 `/health`（存活）与 `/ready`（依赖全绿）两个不同语义的端点

动态（起服务后）：

- 发 1 次请求 → 用同一 `request_id` grep，跨 ≥2 个组件的日志必须都能串起来
- 依赖挂掉时：`/ready` 返回 503 而 `/health` 仍 200（**两者混为一谈是 bug**）
- 触发一次 5xx → 日志有堆栈但**响应体没有**（见 `references/api-testing.md` §3）

## 6. 生产与发布后验证（只读、不改数据）

- 合成监控：对授权的自有服务按固定间隔跑一条只读核心旅程，记录 SLI；禁止压测外部服务
- 发布后 0~30 分钟：健康检查、错误率、延迟分位数、核心旅程、日志与告警；1~24 小时：客诉、业务指标、队列积压
- 与 `assets/release-gate-template.md` 的 Gate 6 对齐，逐项留证据

## 7. 与其他手册的边界

| 想验 | 去哪 |
|---|---|
| 链路贯通、副作用、埋点质量 | 本手册 §3 |
| 分位数、并发、瓶颈定位 | `references/performance-testing.md` |
| 依赖故障下的行为 | `references/chaos-resilience.md` |
| 发布门禁 12 分 | `references/fullstack-integration.md` §6 + `assets/release-gate-template.md` |
| 写入后库/缓存是否真的对 | `references/data-integrity-testing.md` |
| GraphQL/gRPC/WS 的端点矩阵 | `references/protocol-testing.md` |

## 8. 反模式

| ❌ | ✅ |
|---|---|
| 只用 HTTP 200 判定"链路正常" | 加 span 数量/层级/副作用断言 |
| 把平均值当 SLI | 用分位数 + 样本数 + 时间窗 |
| 埋点缺失就跳过该维度 | 记为「可观测性缺口」，是缺陷不是豁免 |
| 日志里打完整 token/请求体"方便排查" | 脱敏，用 `request_id` 关联 |
| SLO 写"系统稳定可用" | 写成 good/valid events 的可计算比例 |
| 把 Tracetest 当默认前置依赖 | 可选加速器，缺失用 curl + grep 降级 |

> **可证伪规则 R-1**（v1.1 引入）：凡声称"请求链路完整 / 副作用已发生"的结论，必须给出同一 `trace_id` 或 `request_id` 贯穿 **≥2 个组件**的原始证据（日志行或 span），并写明采样窗口与样本数。
> **不适用**：单进程、无外部依赖、无日志/埋点的 CLI/库/静态项目，或用户明确禁止读取运行环境日志时 —— 此时结论只能写「未做链路验证 / 可观测性缺口」，**不得**判定链路正常，也不得据此给出 Pass。
