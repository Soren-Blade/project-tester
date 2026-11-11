# API 深度测试手册（阶段 3 · API/全栈项目）

> 蒸馏自 `fullstack-dev/references/testing-strategy.md` 与 `release-checklist.md`、RFC 9457、OWASP API Security Top 10 2023、Schemathesis 官方文档。
> 前提：只对**自己拥有或明确授权**的本地/测试环境实调；禁止对外部服务压测。

## 1. 端点盘点：先建矩阵再动手

从路由定义（`routes/`、`urls.py`、OpenAPI 文档、装饰器）导出一张表，别凭 README 猜：

```
方法  路径                        认证  角色   输入        成功码  副作用
GET   /api/orders/:id            Bearer owner  id        200    -
POST  /api/orders                Bearer user   items[]   201    写库+扣库存
DELETE /api/orders/:id           Bearer admin  id        204    软删
```

**盘点本身就是测试点**：文档里有但路由没有 → 未实现；路由有但文档没写 → 影子端点/调试端点（对应 OWASP API9）。`GET /debug`、`/actuator`、`/swagger`、`/v1/` 与 `/v2/` 并存、废弃版本仍可访问，都要单独记。

## 2. 每个端点的十项必测（照抄即可）

| # | 测试点 | 期望 |
|---|---|---|
| 1 | 正确输入 | 正确状态码 + **正确 DB 状态**（不只验响应体） |
| 2 | 无 token / 伪造 token / 过期 token | 401，且不泄漏账号是否存在 |
| 3 | 低权限角色访问高权限端点 | 403（BFLA / API5） |
| 4 | 把对象 ID 换成**别人的** ID | 403/404（BOLA / API1，最高频漏洞） |
| 5 | 缺字段 / 错类型 / 边界值 / 超长 | 422 或 400，错误体带字段名 |
| 6 | 不存在的 ID、已删除资源 | 404，不是 500 |
| 7 | 重复创建 / 并发提交 / 重试 | 409 或幂等（不能产生两条） |
| 8 | 副作用核对 | DB 变更、事件发出、缓存失效均符合预期 |
| 9 | 错误格式一致性 | 全部端点同一错误信封（见 §3） |
| 10 | 响应字段白名单 | 不返回 `password`、`token`、他人 PII；不允许多写字段（mass assignment / API3） |

**curl 实调模板**（记录到 runs/ 供下次复制）：

```bash
# 带计时与状态码，一次拿到性能维度
curl -s -o /tmp/resp.json -w "HTTP %{http_code} %{time_total}s\n" \
  -X POST http://127.0.0.1:3000/api/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"items":[{"productId":"p1","quantity":2}]}'
cat /tmp/resp.json

# 期望被拒绝（刁钻输入）
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  http://127.0.0.1:3000/api/orders -H "Content-Type: application/json" \
  -d '{"items":[],"amount":-1}'
```

## 3. 错误契约：RFC 9457 Problem Details

现代 API 应返回 `Content-Type: application/problem+json`（RFC 9457，2023，废弃 RFC 7807），而非裸 `application/json`。

```json
{
  "type": "https://example.com/probs/validation-error",
  "title": "Validation failed",
  "status": 422,
  "detail": "items must contain at least one entry",
  "instance": "/api/orders/8f3a",
  "errors": [{ "field": "items", "reason": "empty" }],
  "request_id": "req_01J..."
}
```

**校验点**：
- `Content-Type` 是否为 `application/problem+json`
- `status` 成员与实际 HTTP 状态码**一致**（RFC 要求一致；不一致是 bug）
- 标准成员全部可选，但 `type/title/status/detail` 建议齐备；`type` 缺省语义为 `about:blank`
- 扩展成员（`errors`、`request_id`）用于机器可读信息，**客户端必须忽略不认识的扩展**
- `detail` 只给人看、不面向调试；**不得**含堆栈、SQL、内部路径、密钥
- 所有端点错误结构是否一致；4xx 前端能否映射成人话（见 `fullstack-integration.md`）

状态码速查：`400` 语法错 / `401` 未认证 / `403` 无权限 / `404` 不存在 / `409` 冲突 / `422` 语义校验失败 / `429` 限流 / `5xx` 服务端错。**把 500 当参数错误处理是 bug**。

## 4. 认证与授权专项（OWASP API1/2/3/5）

| 风险 | 怎么测（本地授权目标） | 通过判据 |
|---|---|---|
| API1 BOLA / IDOR | A 的 token 访问 B 的资源 ID；遍历连续 ID | 403/404，绝不返回他人数据 |
| API2 认证失效 | 无/伪造/过期/篡改 JWT；改 `alg:none`；弱密钥；token 放 URL 查询串；刷新 token 重放 | 一律拒绝；刷新后旧 token 失效 |
| API3 属性级授权 | 请求体塞 `role:"admin"`、`price:0`、`user_id:他人`；检查响应是否过度暴露字段 | 服务端白名单，忽略/拒绝多余字段 |
| API5 功能级授权 | 普通用户调 `/admin/*`；把 `GET` 换成 `DELETE`；改路径大小写 | 403 |
| API9 资产管理 | 找 `/v1/` 旧版、`/debug`、`/swagger`、健康检查是否泄漏版本/内网信息 | 无非必要暴露，旧版有下线策略 |
| API10 第三方消费 | 让 mock 返回畸形/超大/恶意 JSON | 不盲信、不崩溃、不执行 |

> 安全边界：注入与越权测试只在本地授权环境验证**防御是否生效**，不生成攻击载荷去打外部服务。完整 10 项见 `security-testing.md`。

## 5. 幂等、并发与状态一致性

- **幂等**：`POST` 同 payload 连发 2 次 / `PUT` 重放 / 网络超时后客户端重试 → 不能重复扣款、重复建单
- **并发**：`for i in 1 2 3 4 5; do curl ... & done; wait` 打同一资源，核对最终状态（库存不能为负、余额不能双花）
- **跳步**：不创建订单直接调 `/pay`；用已取消订单的 ID 调发货
- **乱序**：先收到回调再收到创建成功；重复回调
- 通过判据：状态机合法迁移表之外的操作一律被拒，且有明确错误码

## 6. 分页、过滤、排序、批量

- `page=0` / `page=-1` / `page=999999` / `limit=0` / `limit=100000`（API4 资源消耗）
- 排序字段注入、未知字段、`sort=;DROP` 类字符串
- 分页合并后的集合 == 全量集合（**蜕变关系**，见 `test-design.md`）
- 批量接口部分失败：是全部回滚还是部分成功？必须明确且一致

## 7. Schema / 契约 / 属性测试

| 手段 | 命令 / 工具 | 抓什么 |
|---|---|---|
| 契约测试 | Pact（consumer-driven）、Spring Cloud Contract、OpenAPI diff | 服务间接口变更破坏下游 |
| Schema 校验 | 响应体对照 OpenAPI schema | 字段缺失/类型错/多余字段 |
| 属性测试 | `schemathesis run http://127.0.0.1:3000/openapi.json --checks all` | 自动从规范生成负例：5xx、schema 违规、校验缺口 |
| 状态化测试 | Schemathesis stateful / OpenAPI links | 多步工作流（建→查→删）串联真实 ID |
| 向后兼容 | 老客户端 payload 打新版接口 | 旧字段被删/改名导致破坏 |

Schemathesis 支持 OpenAPI 2.0/3.0/3.1/3.2、GraphQL、gRPC；每个发现自带最小 `curl`/`grpcurl` 复现命令——这正好符合本技能"失败必须附证据"的纪律。**无规范文件时降级**：手写异常参数矩阵（§2 第 5 项）。

## 8. 限流与资源消耗（API4 / API6）

- 短时间内连续请求登录/短信/导出/搜索 → 期望 `429` + `Retry-After`
- 超大 `limit`、超大上传、深层嵌套 JSON → 服务端有上限且明确拒绝
- 敏感业务流（购票、发帖、优惠券）能否被脚本无限自动重复 → 业务层风控，不只是技术限流
- 本地轻测即可（`for` 短循环），**禁止对外部服务压测**；规模化见 `performance-testing.md`

## 9. 记录格式（写进 runs/）

```
端点矩阵：共 N 个端点 × M 动词，本轮实调 X 个
认证：401/过期/伪造 ✅｜授权：BOLA ✅ / BFLA 🐛 BUG#7
错误契约：application/problem+json ✅? ｜ status 一致 ✅?
幂等：重复 POST 产生 2 条 → 🐛 BUG#8
契约：schemathesis 发现 3 个 5xx（附最小 curl）
```

## 10. 反模式

| ❌ | ✅ |
|---|---|
| 只验响应码，不查数据库状态 | 响应 + 副作用双重断言 |
| 用 admin token 测所有端点 | 每个端点用**最低应有权限**的账号测 |
| 把 500 记成"参数错误" | 500 永远是 bug，单独分类 |
| 手搓几十条 curl 而不看规范 | 有 OpenAPI 就先跑 schemathesis |
| 测试打到生产/第三方 | 只打本地授权实例，外部依赖用 nock/responses mock |
