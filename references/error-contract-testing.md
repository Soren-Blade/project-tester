# 错误契约与可诊断性（R-20）

一句话：**报错不是「给用户看一句话」，而是一份可被机器分支、被支持人员定位、被攻击者利用的契约**——状态码错了客户端会重试错，消息里带堆栈等于把源码目录送给对方，没有 trace id 等于线上事故只能靠猜。

适用：任何对外暴露 HTTP/RPC/GraphQL 的项目；内部服务间错误传播、CLI 退出码与 stderr、异步任务失败记录同样适用（换载体，不换要求）。
配套：`assets/error-contract-matrix-template.md`、`scripts/error-audit.py`（`scan` / `check` / `cases`）。
相关规则：R-1 安全（信息泄漏）、R-5 契约（状态码语义）、R-12 可观测性（trace 关联）、R-19 分页（非法参数的错误码）。**5xx 响应体含堆栈/绝对路径/SQL = S1**（v1.9 dogfood F7 实测：非法 `at` 入库 201，列表接口 500 回显 `time.js:7:24` 与绝对路径）。

## 0. 触发条件与不适用

| 场景 | 是否触发 | 说明 |
|---|---|---|
| REST/GraphQL 对外 API | ✅ 必做 | 主战场：状态码 + 错误体 + 关联 id |
| 内部 RPC / 事件消费失败 | ✅ 必做 | 错误码需可重试/不可重试分类 |
| CLI / 桌面端 | ✅ 必做 | 退出码 + stderr 分级（不混入 stdout 数据） |
| 纯静态站点、无错误面的库 | ❌ 不适用 | 只写「不适用：无对外错误面」，**不得**写「错误处理安全」 |
| 仅前端本地校验 | ◐ 部分 | 只验用户可见提示，不写服务端泄漏结论 |

## 1. 三层契约（缺一层就是缺陷）

| 层 | 内容 | 反例 |
|---|---|---|
| 传输层 | 正确的 HTTP 状态码 / 退出码 | 参数错返回 500；未登录返回 403 |
| 机器层 | 稳定的 `code`（如 `VALIDATION_FAILED`）、字段级 `errors[]` | 只有 `{"error": true}`；code 随文案变 |
| 人类层 | `message`（可本地化）、`trace_id`/`request_id`、`docs_url` | 只回 `"Internal Server Error"` 且无 id |

推荐错误体（RFC 9457 `application/problem+json` 或其等价物）：

```json
{"type":"https://api.example.com/errors/validation","title":"Validation failed",
 "status":422,"code":"VALIDATION_FAILED",
 "detail":"email: must be a valid address",
 "instance":"/v1/users","trace_id":"4bf92f3577b34da6a3ce929d0e0e4736",
 "errors":[{"field":"email","code":"INVALID_FORMAT"}]}
```

- `type`/`title` 稳定（同一类错误永远同一个），`detail` 可含本次细节；
- 扩展成员（`code`/`trace_id`/`errors`）合法，别塞进 `title`；
- 同一 API 的错误体**形状**要一致（别一半 JSON 一半 HTML 一半空体）。

## 2. 状态码选择（可判定的矩阵）

| 情况 | 码 | 关键约束 |
|---|---|---|
| JSON 语法错 / 缺必填 / 类型错 | 400 | 不回显解析器内部信息 |
| 未认证 / token 过期 | 401 | **必须**带 `WWW-Authenticate`；不得用 403 代 401 |
| 已认证但无权限 | 403 | 不得用 404 假装不存在（除非明确选「隐藏存在性」策略） |
| 资源不存在 | 404 | 空体或统一体，别回框架默认页 |
| 方法不支持 | 405 | 必须带 `Allow` |
| 媒体类型不支持 | 415 | 说明支持的 `Content-Type` |
| 语义冲突（重复创建、版本冲突、状态机非法） | 409 | 与 422 区分：409 = 当前状态冲突 |
| 语法对但语义不合法（字段值越界、业务规则） | 422 | 字段级 `errors[]` |
| 限流 | 429 | 带 `Retry-After` |
| 服务端未预期异常 | 500 | 通用体；细节只进日志 |
| 上游不可用 / 超时 / 网关超时 | 502 / 503 / 504 | 503 可带 `Retry-After`；不得把上游堆栈透传 |
| 部分成功（批量） | 207 | 每项独立状态 + 错误码 |

**401 vs 403**：401 是「你是谁」未成立，且必须给挑战头；403 是「知道你是谁但不许」。把未登录写成 403 会让客户端不去刷新 token。
**404 vs 403**：对他人资源，选一种策略并全站一致——要么 404 隐藏存在性，要么 403 明示拒绝；两者混用本身就是可枚举信号（见 §5）。
**409 vs 422**：客户端能否靠「重读当前状态再重试」解决？能 → 409；不能（值本身非法）→ 422。

## 3. 5xx 防泄漏（本轮硬门禁）

5xx 响应体**只允许**：通用 `title`/`message`、稳定 `code`、`trace_id`、可选 `docs_url`。**禁止**出现：

| 泄漏物 | 示例 | 依据 |
|---|---|---|
| 堆栈帧 | `at time.js:7:24`、`File "app.py", line 88` | CWE-209；OWASP Error Handling CS |
| 绝对路径 | `D:\app\src\time.js`、`/srv/app/...` | 同上（PHP 警示页经典泄漏） |
| SQL/ORM 片段 | `syntax error at or near "at"`、表名/列名 | 同上 + R-1 |
| 内网主机/端口/IP | `10.0.3.7:5432`、`redis.internal` | 同上 |
| 依赖与版本 | `Express 4.18.2`、`X-Powered-By`、`Server: nginx/1.24` | 指纹用于定向攻击 |
| 源码片段 / 配置值 | 环境变量、密钥前缀、`DEBUG=True` 页 | CWE-209 + CWE-200 |
| 开发者调试页 | Django `DEBUG=True` 黄页、Spring Whitelabel、`UseDeveloperExceptionPage` 在生产启用 | 框架默认陷阱 |
| Source map / GraphQL introspection 在生产开启 | `.map` 可下载、`__schema` 可查 | 信息面扩大 |

框架默认要逐项核对（不是「我记得关了就关了」）：

- **Express**：默认错误处理在 `NODE_ENV !== 'production'` 时回堆栈 → 自定义 `app.use((err,req,res,next)=>...)` 且**不**输出 `err.stack`；关闭 `X-Powered-By`。
- **Spring Boot**：`server.error.include-stacktrace`（默认 `never`，但曾被改成 `always`）、`include-message`、`include-binding-errors`；Actuator 端点 `exposure.include` 不要 `*`。
- **Django**：`DEBUG=False` + `ALLOWED_HOSTS`；`DEBUG=True` 时任何异常都回完整 traceback 与 settings。
- **ASP.NET Core**：`UseDeveloperExceptionPage()` 只在 `env.IsDevelopment()` 分支；生产用 `UseExceptionHandler` + `ProblemDetails`。
- **PHP**：`display_errors=Off`、`log_errors=On`；`APP_DEBUG=false`（Laravel 会回 Ignition 页）。
- **GraphQL**：生产关闭 introspection/playground；`errors[].extensions.exception.stacktrace` 必须关（Apollo 有专门开关）。

**验证方式**：不是读配置就算完——用 6 类刻意触发路径打到 5xx，把响应体原文存证并用正则扫堆栈/路径/SQL/主机名；再对 4xx 做同样扫描（4xx 也可能回显解析器异常）。

## 4. 可诊断性（支持人员能不能只凭响应定位）

| 项 | 要求 | 反例 |
|---|---|---|
| `trace_id`/`request_id` | 每次响应都有，且能在日志/链路系统里查到同一 id | 有 id 但日志里搜不到；id 每次都是 `-` |
| W3C Trace Context | 入站 `traceparent` 被接受并传播（格式校验，不盲信客户端） | 自造 id 不传播，跨服务断链 |
| 时间 | 错误体或头部含服务端时间（排时区/时钟问题） | 只有客户端时间 |
| 稳定 `code` | 同一失败原因永远同一 code；文案可翻译但 code 不变 | `code` 里带变量/英文长句 |
| 文档链接 | 可选 `type`/`docs_url` 指向错误目录 | 用户只能截图问客服 |
| 字段级错误 | `errors[].field` + `errors[].code` | 只回 `"invalid input"` |
| 重试指引 | 429/503 带 `Retry-After`；不可重试错误明确 `retryable:false` | 客户端对 500 无限重试 |

**不得**把 `trace_id` 当成「已可诊断」的证据：要给出「响应里的 id → 日志里同 id 的完整记录」的对照截图/文本，否则只写「已返回 trace_id，未验证可检索」。

## 5. 存在性泄漏与枚举

- 未认证 vs 无权限 vs 不存在：三种情况的**状态码 + 响应体 + 时延**都要对照；若「他人资源」和「不存在」返回不同体/不同耗时，攻击者可枚举 id。
- 批量接口的部分失败会泄漏「哪些 id 存在」（如返回 `[{"id":1,"error":"forbidden"},{"id":2,"error":"not found"}]`）——若这是敏感集合，需统一为同一错误或整体拒绝。
- 登录/注册/找回密码：账号是否存在不得通过文案/状态码/时延区分（与 R-1 账户枚举合并判定）。
- 时序：数据库命中 vs 未命中的耗时差要测（多次取中位数），别只看状态码。

## 6. 错误路径的副作用与重试

- **事务回滚**：业务写到一半抛错，是否留下半条记录/孤儿文件/已扣库存？用「注入失败点」验证（如唯一键冲突、下游 500）。
- **幂等**：同一请求重试两次，是否重复扣款/重复发消息；`Idempotency-Key` 是否真正生效。
- **重试语义**：4xx（除 408/429）不应重试；5xx/超时可重试但需退避；`Retry-After` 必须被客户端尊重。
- **超时与取消**：客户端断开后服务端是否继续写；超时错误返回 504 还是 500 要与网关一致。
- **错误后的可恢复性**：失败任务是否进死信/可重放；部分成功是否可补偿。

## 7. 错误与可观测性一致（与 R-12 交叉）

- 错误响应里的 `trace_id` 必须能在日志/APM 中检索到，且日志含同一请求的关键上下文（路由、用户/租户匿名 id、错误 code）。
- 日志**不得**记录密码、token、完整卡号、身份证、请求体原文（与 R-6 隐私交叉）；堆栈只进服务端日志，且日志访问受控。
- 指标：按 `code`/状态码分类的错误率、5xx 比例、429 比例；告警阈值与错误预算挂钩。
- 告警内容含 trace 链接，而不是只有「500 增多了」。

## 8. 缺陷判定表

| 现象 | 级别 | 判据 |
|---|---|---|
| 5xx 响应含堆栈/绝对路径/SQL/内网主机/版本 | S1 | 响应原文 + 正则命中位置 |
| 调试页/`DEBUG=True`/`include-stacktrace=always` 在生产生效 | S1 | 触发请求 + 响应原文 |
| 未认证返回 403 或 200；401 无 `WWW-Authenticate` | S2 | 状态码 + 头 |
| 参数校验失败返回 5xx | S2 | 请求 + 响应码 |
| 429/503 无 `Retry-After` | S2 | 响应头 |
| 所有错误体无稳定 `code` | S2 | 多类错误体对照 |
| 有 `trace_id` 但日志不可检索 | S2 | 响应 id + 日志检索结果 |
| 他人资源与不存在返回不同体/不同时延（可枚举） | S2 | 三态对照 + 时延 |
| 错误体 `message` 为空/`undefined`/`null` | S3 | 响应原文 |
| 错误体反射请求内容且未转义（HTML 页） | S1 | 响应原文（XSS） |
| 错误路径留下半条写入/重复扣款 | S1 | 前后数据对照 |

## 9. 验证命令（只读优先）

```bash
# 1) 触发 6 类错误并落盘原文
B=https://host
curl -sS -D /tmp/h1 -o /tmp/b1 "$B/api/users/abc"                 # 非法 id
curl -sS -D /tmp/h2 -o /tmp/b2 -X POST "$B/api/users" -H 'Content-Type: application/json' -d '{bad'
curl -sS -D /tmp/h3 -o /tmp/b3 "$B/api/users?size=abc"            # 非法参数
curl -sS -D /tmp/h4 -o /tmp/b4 -X POST "$B/api/users" -H 'Content-Type: text/plain' -d x  # 415
curl -sS -D /tmp/h5 -o /tmp/b5 "$B/api/__nope"                    # 404
curl -sS -D /tmp/h6 -o /tmp/b6 "$B/api/users?sort=id,(select%201)" # 排序注入

# 2) 泄漏扫描（堆栈/路径/SQL/内网/版本）
grep -aiE 'at [A-Za-z0-9_./\\-]+:[0-9]+|Traceback|SyntaxError|syntax error|/home/|/srv/|/var/|C:\\\\|10\.[0-9]+\.|192\.168\.|X-Powered-By|Express' /tmp/b*

# 3) 头检查
grep -aiE 'WWW-Authenticate|Retry-After|Content-Type|X-Request-Id|traceparent' /tmp/h*

# 4) 三态存在性对照（A 登录、B 资源、不存在资源）
curl -sS -o /dev/null -w 'unauth=%{http_code} t=%{time_total}\n' "$B/api/users/2"
curl -sS -o /dev/null -w 'missing=%{http_code} t=%{time_total}\n' "$B/api/users/999999"
```

脚本：

```bash
python scripts/error-audit.py scan . --format markdown --fail-on-gap
python scripts/error-audit.py check --file errors.json --format markdown --fail-on-gap
python scripts/error-audit.py cases
python scripts/error-audit.py --self-test
```

`check` 清单格式：

```json
{"cases":[{"id":"bad-json","expected_status":400,"actual_status":500,
           "body":"SyntaxError: Unexpected token\n    at JSON.parse (<anonymous>)",
           "content_type":"text/html","has_code":false,"has_trace_id":false}],
 "config":{"debug":false,"include_stacktrace":"always"},
 "existence":{"unauth":401,"forbidden":403,"missing":404,"leak":false},
 "graphql":{"status":200,"errors":[{"message":"Cannot read property x"}]}}
```

## 10. 报告证据写法（R-20 六项）

1. 状态码矩阵：每类错误的请求原文 + 期望码 + 实际码；
2. 5xx 防泄漏：≥3 条刻意触发路径的响应体原文 + 正则扫描输出（堆栈/路径/SQL/主机/版本各一）；
3. 可诊断性：错误体里的 `code`/`trace_id` 字段 + 同一 id 在日志中的检索记录；
4. 存在性对照：未认证/无权限/不存在三态的码、体、时延；
5. 副作用：失败点注入前后数据对照（是否半写/重复）；
6. 配置证据：生产环境 `DEBUG`/`include-stacktrace`/introspection 的实际配置值与生效验证。

**不得**写：「返回了 500 就是有错误处理」「`message` 是英文就是给用户看的」「有 `trace_id` 就是可诊断」「4xx 不算信息泄漏」「本地 `NODE_ENV=production` 跑过就是生产安全」「框架默认不会回堆栈」（默认值随版本变，必须实测）。

## 11. 项目形态 → 证据

| 形态 | 必做 | 证据 |
|---|---|---|
| REST API | 状态码矩阵 + 5xx 泄漏扫描 | 6 类错误原文 + grep 输出 |
| GraphQL | 200 + `errors[]` 语义、`extensions` 不泄漏 | 触发查询 + 完整响应 |
| 内部 RPC | 错误码可重试分类、超时/取消 | 错误码表 + 重试实验 |
| 批量/导入 | 207 部分失败、逐项错误 | 混合成功失败响应 |
| 网关/BFF | 上游错误透传边界 | 上游 500 → 对外响应 |
| CLI | 退出码 + stderr 分级 | 失败命令的码与输出 |

## 12. 来源

- RFC 9457 Problem Details for HTTP APIs（`type/title/status/detail/instance`、`application/problem+json`）：https://www.rfc-editor.org/rfc/rfc9457.html
- RFC 9110 HTTP Semantics（401/403/404/405/409/415/503 语义与 `WWW-Authenticate`、`Retry-After`）：https://www.rfc-editor.org/rfc/rfc9110.html
- RFC 6585（429 Too Many Requests + `Retry-After`）：https://www.rfc-editor.org/rfc/rfc6585.html
- RFC 4918（422 Unprocessable Content、207 Multi-Status 来源）：https://www.rfc-editor.org/rfc/rfc4918.html
- OWASP Error Handling Cheat Sheet（5xx 只回通用体、细节进服务端日志、各框架配置）：https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html
- OWASP WSTG — Testing for Improper Error Handling：https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/08-Testing_for_Error_Handling/
- CWE-209 Generation of Error Message Containing Sensitive Information：https://cwe.mitre.org/data/definitions/209.html
- W3C Trace Context（`traceparent`/`tracestate`）：https://www.w3.org/TR/trace-context/
- ASP.NET Core 错误处理（`UseDeveloperExceptionPage` 仅开发、`UseExceptionHandler`）：https://learn.microsoft.com/aspnet/core/fundamentals/error-handling
- Spring Boot 错误属性（`server.error.include-stacktrace` 等）：https://docs.spring.io/spring-boot/reference/web/servlet.html#web.servlet.spring-mvc.error-handling
