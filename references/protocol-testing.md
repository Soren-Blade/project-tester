# 非 REST 协议端点测试（GraphQL / gRPC / WebSocket / SSE）

> 蒸馏自 OWASP GraphQL Cheat Sheet、gRPC 官方 Status Codes、fullstorydev/grpcurl、`fullstack-dev` 的实时通信模式，以及本技能 `references/api-testing.md` 的端点矩阵方法。
> **本文件吸收了 v1.0 遗留提案**：「GraphQL / gRPC 项目缺一份专项端点矩阵模板」→ 逐类型用例清单见 §2~§4，可填写模板见 `assets/protocol-matrix-template.md`。

## 1. 为什么不能直接套 REST 端点矩阵

| 差异 | REST 的假设 | 非 REST 的现实 | 测试要补的 |
|---|---|---|---|
| 入口 | 多个路径 × 多个动词 | **单一 `/graphql` 端点**承载全部操作；gRPC 是 service/method | 按 operation / RPC method 建矩阵，不按 URL |
| 状态码 | HTTP 状态码即结果 | GraphQL 常恒返 200（错误在 `errors[]`）；gRPC 用 17 个自定义码 | 断言对象从 status 换成 `errors[]` / grpc status |
| 授权 | 路由级中间件 | GraphQL 需 **resolver 级**；gRPC 靠 metadata 拦截器 | 每个 field / method 单独测越权 |
| 传输 | 无状态请求-响应 | protobuf 二进制、WS 长连接、SSE 单向流 | 需要 `grpcurl` / ws 客户端 / SSE 读取器 |
| 资源消耗 | 限请求数即可 | 深度嵌套、batching、alias 可在 1 个请求里放大成本 | 限 query cost / 操作数 / 消息速率 |

**通用底座不变**：认证授权四列矩阵（匿名 / 本人 / 他人 / 管理员）、错误契约、幂等并发、副作用核对、限流，全部沿用 `references/api-testing.md` §2~§8。下表只列**各协议特有的增量**。

## 2. GraphQL 专项测试卡

### 2.1 用例清单（逐条打勾）

| # | 测试点 | 期望 | 风险来源 |
|---|---|---|---|
| 1 | 未认证执行 introspection 查询 | 生产/公开环境禁用或按角色过滤 | 泄露 schema、deprecated 与私有字段 |
| 2 | 访问 GraphiQL / schema 探索页 | 生产不开放 | 同上 |
| 3 | 故意拼错字段（如 `usr`） | 不返回 `Did you mean ...` 字段建议 | 禁用 introspection 后仍可爆破 schema |
| 4 | 深层嵌套查询（逐层加到 N） | 超过深度上限被拒 | 默认无限制 → DoS |
| 5 | `first: 99999999` / 超大 amount | 被数量上限拒绝 | 同上 |
| 6 | 高复杂度查询 / 高 cost | 有 query cost 上限或超时 | 单请求拖垮服务 |
| 7 | **batching**：数组多操作 + alias 同一查询重复 N 次 | 限制单次操作数与对象实例数 | 绕过按请求数限速；爆破 OTP/密码/枚举用户 |
| 8 | resolver 级越权：A 的 token 查 B 的 `user(id:)` | 拒绝；`node`/`nodes` **也要查** | edges 有校验、nodes 没有是经典漏洞 |
| 9 | mutation 越权 / 字段级读取权限 | 每个 resolver 独立校验，不靠"前端不显示" | BOLA / BFLA |
| 10 | variables 注入（SQL/NoSQL/OS/SSRF 串） | allowlist 校验；自定义 scalar/enum 生效 | 注入 |
| 11 | 错误响应 | 无堆栈、无内部路径；`errors[]` 结构一致 | 生产 debug 模式 |
| 12 | 限流按 **cost / 操作数**，不按请求数 | 昂贵查询与 batching 也被限住 | 网关 `limit_req` 看不见单请求内的成本 |

### 2.2 可直接粘贴的探针

```bash
# introspection 是否开放（生产应被拒）
curl -s -X POST http://127.0.0.1:4000/graphql -H 'Content-Type: application/json' \
  -d '{"query":"{ __schema { types { name fields { name } } } }"}' | head -c 300

# 字段建议是否泄漏
curl -s -X POST http://127.0.0.1:4000/graphql -H 'Content-Type: application/json' \
  -d '{"query":"{ usr { id } }"}'

# 深层嵌套 / batching（观察是否被拒与耗时）
curl -s -o /tmp/gql.json -w "HTTP %{http_code} %{time_total}s\n" -X POST \
  -H 'Content-Type: application/json' \
  -d '{"query":"query { a:user(id:1){id} b:user(id:2){id} c:user(id:3){id} }"}' \
  http://127.0.0.1:4000/graphql
cat /tmp/gql.json
```

**判据提醒**：GraphQL 返回 `200` 且带 `errors[]` 是常见设计 —— **别把 200 当成功**。断言要同时看 `data` 是否非空、`errors[]` 是否为空、以及部分成功时 `data` 里哪些字段为 null。

## 3. gRPC 专项测试卡

### 3.1 用例清单

| # | 测试点 | 期望 |
|---|---|---|
| 1 | server reflection 是否在生产暴露 | 公开环境按需关闭；测试时用 `-proto` / `-protoset` 代替 |
| 2 | `list` / `describe` 枚举出的 service 与文档一致 | 差异 = 影子方法/未实现功能（同 `references/api-testing.md` §1） |
| 3 | 每个 RPC：正确输入 / 缺字段 / 错类型 / 边界值 | `INVALID_ARGUMENT` 或 `OUT_OF_RANGE`，不是 `UNKNOWN`/`INTERNAL` |
| 4 | 认证 metadata 缺失 / 伪造 / 过期 | `UNAUTHENTICATED`（**不是** `PERMISSION_DENIED`） |
| 5 | 低权限角色调高权限方法 | `PERMISSION_DENIED`；拒绝整类用户时可用 `NOT_FOUND` |
| 6 | 不存在的实体 / 重复创建 / 并发冲突 | `NOT_FOUND` / `ALREADY_EXISTS` / `ABORTED` |
| 7 | 超限时 | `RESOURCE_EXHAUSTED`，**不得**误用 `PERMISSION_DENIED` |
| 8 | deadline / 超时 | `DEADLINE_EXCEEDED`；**注意：此时操作可能已在服务端成功** → 重试必须幂等 |
| 9 | 依赖不可用 | `UNAVAILABLE`（可退避重试，但非幂等操作不安全）；`INTERNAL` 是严重错误、`DATA_LOSS` 是数据损坏（S1） |
| 10 | 流式 RPC | 客户端中断、服务端中断、背压、消息顺序、半关闭 |
| 11 | 未实现方法 | `UNIMPLEMENTED`，不是 500 裸错 |

### 3.2 grpcurl 命令速查

```bash
# 依赖 server reflection；否则加 -proto / -import-path 或 -protoset
grpcurl -plaintext 127.0.0.1:50051 list
grpcurl -plaintext 127.0.0.1:50051 describe my.pkg.OrderService

grpcurl -plaintext -d '{"id":"8f3a"}' \
  127.0.0.1:50051 my.pkg.OrderService/GetOrder

# metadata（认证/追踪）
grpcurl -plaintext -H "authorization: Bearer $TOKEN" \
  -H "traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01" \
  -d '{"id":"8f3a"}' 127.0.0.1:50051 my.pkg.OrderService/GetOrder

# 无 reflection 时先生成 protoset（--include_imports 必须带）
protoc --proto_path=. --descriptor_set_out=svc.protoset --include_imports \
  my/pkg/order_service.proto
grpcurl -protoset svc.protoset -plaintext -d '{"id":"8f3a"}' \
  127.0.0.1:50051 my.pkg.OrderService/GetOrder
```

**记录格式**：把 `grpc-status`、错误描述、`-d` 原文、耗时一起写进 runs/；`grpcurl` 输出即原始证据。跨服务链路的 `traceparent` 贯通判据见 `references/observability-testing.md` §3。

## 4. WebSocket / SSE 专项测试卡

| # | 测试点 | 期望 |
|---|---|---|
| 1 | 握手阶段认证 | 无/过期 token 被拒；**不能连上再靠首条消息鉴权** |
| 2 | 越权订阅他人频道 / 篡改 room id | 拒绝，不推他人数据（BOLA 在长连接上的形态） |
| 3 | 心跳 ping/pong | 无心跳或心跳超时能检测半开连接并清理 |
| 4 | 断线重连 | 指数退避、有上限；`req.on('close')` / 客户端 cleanup 退订，无订阅泄漏 |
| 5 | 双标签页同步 | 一端变更，另一端收到且只收一次 |
| 6 | 消息顺序与重复 | 有序号/幂等键；重复投递不产生重复副作用 |
| 7 | 畸形 / 超大帧 / 非 JSON 消息 | 优雅关闭或明确错误码，不崩进程 |
| 8 | 背压与慢消费者 | 有缓冲上限与丢弃/降级策略，不无限堆积 |
| 9 | SSE 特有 | `Content-Type: text/event-stream`、`Cache-Control: no-cache`、自动重连、事件名与 `data:` 格式 |
| 10 | 优雅停机 | SIGTERM 后停止接新连接、排空在途、关闭连接 |

```bash
# SSE 最小探针（观察首行与事件格式，5 秒后自动断开）
curl -sN --max-time 5 -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:3000/api/events | head -20
```

WS 无专用客户端时降级：用 Node 自带 `WebSocket`（Node 22+）或 Python `websockets`；都缺失则静态审读连接/订阅/close 处理代码并标注「未做运行时验证」。

## 5. 认证授权矩阵在四种协议上的落点

| 协议 | 凭证放哪 | 「他人」怎么造 | 常见漏测 |
|---|---|---|---|
| REST | `Authorization` header | 换 `:id` | 已在 `references/api-testing.md` §4 覆盖 |
| GraphQL | header + **resolver 上下文** | 换 `id` 参数 / `node(id:)` | 只在网关鉴权、resolver 不校验 |
| gRPC | metadata (`-H`) | 换请求里的资源 ID | 统一拦截器漏掉某个 method |
| WS / SSE | 握手 query/header/cookie | 换订阅频道 / room / user id | 连上之后不再校验消息级权限 |

## 6. 记录格式（写进 runs/）

```
协议：GraphQL / gRPC / WS / SSE
端点矩阵：N 个 operation / method（含文档未列的 ___ 个）
认证授权四列：匿名 ✅｜本人 ✅｜他人 🐛 BUG#__｜管理员 ✅
协议特有项：introspection ___｜深度/复杂度 ___｜batching ___｜grpc-status 映射 ___｜重连/退订 ___
错误契约：___（GraphQL 看 errors[]，gRPC 看 grpc-status）
副作用：响应 + DB/事件/缓存 三重断言 ___
```

可填写矩阵见 `assets/protocol-matrix-template.md`。

## 7. 反模式

| ❌ | ✅ |
|---|---|
| 把 `/graphql` 当成一个端点只测一次 | 按 operation/field 建矩阵 |
| GraphQL 返回 200 就判通过 | 同时看 `data` 与 `errors[]` |
| 用 `curl` 直接打 gRPC | 用 `grpcurl` + reflection/protoset |
| 把 `DEADLINE_EXCEEDED` 当"没执行" | 它可能已成功，必须验幂等 |
| 只在连接建立时鉴权 | WS/SSE 的每条消息、每个频道都要校验归属 |
| 关掉浏览器就算测完重连 | 显式断网 → 观察退避、重连、退订与恢复 |
