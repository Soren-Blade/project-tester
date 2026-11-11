# 非 REST 端点矩阵模板（GraphQL / gRPC / WS / SSE）

> 配套 `references/protocol-testing.md`。逐类型勾选，每行都要有「结论 + 证据」；`⬜` 未测不等于通过。
> 状态：`✅` 通过 ｜ `🐛` 缺陷（附 BUG 编号）｜ `⬜` 未测 ｜ `🔥` 阻塞 ｜ `—` 不适用（须写原因）

**项目**：___　**协议**：___　**环境 / commit**：___　**日期**：___　**测试人**：___
**规范来源**：`*.graphql` / `*.proto` / OpenAPI / 文档（写明路径）___
**执行人凭证**：匿名 / 本人 / 他人 / 管理员 四类都已准备？___

---

## A. 通用底座（沿用 `references/api-testing.md` §2）

| # | 测试点 | 结论 | 证据（命令 / 输出 / 路径） |
|---|---|---|---|
| A1 | 端点/operation 盘点与文档两列对照 | ⬜ | |
| A2 | 认证授权四列矩阵逐格实调 | ⬜ | |
| A3 | 错误契约一致（状态码 / `errors[]` / grpc-status） | ⬜ | |
| A4 | 输入校验：空 / 错类型 / 边界 / 超长 | ⬜ | |
| A5 | 幂等、并发、重复提交 | ⬜ | |
| A6 | 副作用三重断言（响应 + DB + 缓存/事件） | ⬜ | |
| A7 | 限流与资源消耗 | ⬜ | |
| A8 | 响应字段白名单 / 多余字段（mass assignment） | ⬜ | |

## B. GraphQL 专项

| # | 测试点 | 期望 | 结论 | 证据 |
|---|---|---|---|---|
| B1 | 未认证 introspection | 生产禁用/按角色过滤 | ⬜ | |
| B2 | GraphiQL / schema 探索页 | 生产不开放 | ⬜ | |
| B3 | 错字段建议 `Did you mean` | 不泄漏 | ⬜ | |
| B4 | 深度嵌套 N 层 | 超上限被拒 | ⬜ | |
| B5 | `first: 99999999` 等超大 amount | 被数量上限拒绝 | ⬜ | |
| B6 | 高 query cost / 超时 | 有 cost 上限或超时 | ⬜ | |
| B7 | batching（数组操作 + alias 多实例） | 限制操作数与对象数 | ⬜ | |
| B8 | resolver 越权（换 id / `node(id:)` / `nodes`） | 拒绝 | ⬜ | |
| B9 | mutation / 字段级权限 | 逐 resolver 校验 | ⬜ | |
| B10 | variables 注入（allowlist / 自定义 scalar） | 拒绝且不崩 | ⬜ | |
| B11 | 错误响应无堆栈 / `errors[]` 结构一致 | 通过 | ⬜ | |
| B12 | 限流按 cost / 操作数（非仅请求数） | 生效 | ⬜ | |

> 断言提醒：`200` + `errors[]` 非空 = 失败；同时核对 `data` 与部分成功时的 `null` 字段。

## C. gRPC 专项

| RPC method | 正确输入 | 缺/错字段 → `INVALID_ARGUMENT` | 无凭证 → `UNAUTHENTICATED` | 越权 → `PERMISSION_DENIED` | 不存在 → `NOT_FOUND` | 重复 → `ALREADY_EXISTS` | deadline → 幂等验证 | 流式/中断 | 结论 |
|---|---|---|---|---|---|---|---|---|---|
| `Service/Method` | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

- [ ] `list` / `describe` 枚举与文档对照（差异：___ 个）
- [ ] reflection 生产是否关闭：___
- [ ] 码映射抽查：`RESOURCE_EXHAUSTED`（非 `PERMISSION_DENIED`）｜`INTERNAL`/`DATA_LOSS`（S1）｜`UNAVAILABLE`（重试安全吗）
- [ ] `DEADLINE_EXCEEDED` 后服务端状态已核对（操作可能已成功）
- [ ] `grpcurl` 原始输出已贴入 runs/；`-proto` / `-protoset` 路径：___

## D. WebSocket / SSE 专项

| # | 测试点 | 结论 | 证据 |
|---|---|---|---|
| D1 | 握手阶段认证（含过期 token） | ⬜ | |
| D2 | 越权订阅他人频道 / room / user id | ⬜ | |
| D3 | 心跳 ping/pong 与半开连接清理 | ⬜ | |
| D4 | 断线重连（退避 + 上限）与 `close` 退订 | ⬜ | |
| D5 | 双标签页同步，且只收一次 | ⬜ | |
| D6 | 消息顺序 / 重复投递幂等 | ⬜ | |
| D7 | 畸形帧 / 超大帧 / 非 JSON | ⬜ | |
| D8 | 背压与慢消费者 | ⬜ | |
| D9 | SSE：`text/event-stream`、`no-cache`、事件名与 `data:` 格式 | ⬜ | |
| D10 | SIGTERM 优雅停机，不丢在途 | ⬜ | |

---

## 汇总（X + Y + Z + B + N/A = 测试点总数）

```
通用 A：___ 条｜GraphQL B：___ 条｜gRPC C：___ 个 method × 8 项｜实时 D：___ 条
通过 ___ / 失败 ___ / 阻塞 ___ / 未测 ___ / 不适用 ___
S1 ___  S2 ___  S3 ___（未闭环 S1 → No-Go）
覆盖口径：按 operation / method 计，非按 URL 计；未测项写入下次待办
```

**质量状态**：`PASS / FAIL`　**发布建议**：`Go / No-Go`　**一句话理由**：___
**下次待办**：回归 ___ ／待测 ___ ／阻塞 ___
