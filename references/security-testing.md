# 安全测试手册（阶段 3 · 安全维度）

> 权威基线：OWASP **API Security Top 10 — 2023**（官方十项名称逐条对齐）、OWASP WSTG / ASVS、`fullstack-dev` Security Review 门禁。
> **授权边界（不可协商）**：只测用户自己的或明确书面授权的项目；注入/越权仅用于验证**本地目标防御是否生效**；不对外部服务做压力、DoS 或真实攻击；不得把可用攻击载荷用于非授权目标。

## 1. OWASP API Top 10 (2023) 逐项测试卡

| # | 官方风险名 | 一句话成因 | 最小测试动作 | 通过判据 |
|---|---|---|---|---|
| API1 | Broken Object Level Authorization (BOLA) | 用客户端传来的 ID 取数据却没校验归属 | A 的 token 请求 B 的 `order_id`；连续 ID 遍历 | 403/404，不返回他人数据。**最高频、优先测** |
| API2 | Broken Authentication | 认证机制实现有误，令牌可被窃取/冒用 | 无/伪造/过期/篡改 JWT、`alg:none`、token 出现在 URL/日志、刷新后旧 token 是否还活 | 一律拒绝；凭证不进 URL 与日志；有短时访问 + 可撤销刷新 |
| API3 | Broken Object Property Level Authorization | 合并了 2019 的"过度数据暴露"+"批量分配"；属性级授权缺失 | 请求体塞 `role/price/user_id`；响应体查 `password/hash/内部字段` | 服务端属性白名单；不多读不多写 |
| API4 | Unrestricted Resource Consumption | 带宽/CPU/内存/存储/付费短信等无上限 | `limit=100000`、超大上传、深层 JSON、密集触发短信/邮件 | 有上限、有 429/413、有超时 |
| API5 | Broken Function Level Authorization (BFLA) | 管理功能与普通功能边界不清 | 普通用户调 `/admin/*`、换 HTTP 动词、改路径大小写 | 403；默认拒绝而非默认放行 |
| API6 | Unrestricted Access to Sensitive Business Flows | 业务流程被自动化滥用（不一定是代码 bug） | 脚本高频重复购票/发帖/领券/注册 | 有业务层风控（限速、验证码、幂等、配额） |
| API7 | Server Side Request Forgery (SSRF) | 服务端拉取用户提供的 URI 未校验 | 把 `url/webhook/callback/import` 字段指向内网地址或本地元数据地址（仅本地授权环境） | 白名单校验、拒绝内网/回环/非预期 scheme |
| API8 | Security Misconfiguration | 复杂配置漏配或默认不安全 | 检查 CORS 是否 `*`、默认错误页/堆栈、缺失安全头、开放调试端点、目录列表、默认凭据 | 显式 origins、无堆栈外泄、helmet 类头齐备、无默认密码 |
| API9 | Improper Inventory Management | 端点/版本/主机无清单，废弃版本与调试端点仍在线 | 探测 `/v1/` vs `/v2/`、`/debug`、`/swagger`、`/actuator`、文档与实际端点 diff | 有清单、旧版本有下线计划、无影子端点 |
| API10 | Unsafe Consumption of APIs | 过度信任第三方返回的数据 | mock 第三方返回畸形/超大/恶意内容（nock / responses） | 与用户输入同等校验，不解析执行、不崩溃 |

> API3 与 API5 的区别：API3 管**对象的属性**（能不能改 `role`），API5 管**功能/端点**（能不能进 `/admin`）。别混成一条用例。

## 2. 认证 / 授权矩阵（每次必填）

```
端点            | 匿名 | 普通用户(本人) | 普通用户(他人) | 管理员
GET /me         | 401  | 200            |   —           | 200
GET /users/:id  | 401  | 403(他人)      | 403           | 200
DELETE /users/:id| 401 | 403            | 403           | 204
GET /health     | 200  | 200            | 200           | 200
```

填完矩阵再逐格实调。**空白格 = 未测 = 风险**，不许默认"应该没问题"。

## 3. 输入向量库（配合 `personas.md` 刁钻画像）

| 类别 | 代表值 | 观察点 |
|---|---|---|
| SQL | `' OR '1'='1`、`'; DROP TABLE x--` | 参数化查询；不 500、不执行 |
| XSS | `<script>alert(1)</script>`、`"><img onerror=...>` | 输出编码；CSP；存储后回显仍转义 |
| 命令 | `; id`、`$(id)`、`` `id` ``、管道符 | 不调用 shell；白名单 |
| 路径 | `../../etc/passwd`、`..\..\windows\win.ini`、绝对路径、URL 编码变体 | 规范化后仍在允许根目录内 |
| 模板/SSTI | `{{7*7}}`、`${7*7}`、`<%= 7*7 %>` | 不出现 `49` |
| 反序列化 / XXE | 畸形 JSON、超深嵌套、外部实体声明 | 有深度/大小上限；禁用外部实体 |
| 特殊字符 | 零宽空格 U+200B、`%00`、emoji、RTL、CRLF 注入头 | 原样存取、不截断、不注入头 |
| HTTP | 超长 URL/Header、重复 Header、畸形 `Content-Length`、`Host` 篡改 | 413/400，不崩溃 |

**判据**：被正确转义/参数化/拦截 = PASS；原样执行或回显未转义 = **严重 bug**；返回 500 = bug（无论注入是否生效）。

## 4. 敏感信息与配置审查（静态也有效，跑不起来也能做）

```bash
# 硬编码密钥 / 私钥 / .env 被提交
git grep -nEi '(api[_-]?key|secret|password|token|BEGIN .*PRIVATE KEY)' -- . ':!*.lock'
git ls-files | grep -E '(^|/)\.env($|\.)' && echo "FAIL: .env 已入库"
# 依赖漏洞（按栈选一个）
npm audit --omit=dev ; pip-audit ; govulncheck ./... ; cargo audit
```

其他静态检查点：
- 日志/错误响应是否含密码、token、PII、堆栈、SQL
- `CORS` 是否 `Access-Control-Allow-Origin: *`（生产环境）
- 安全头：`Strict-Transport-Security`、`X-Content-Type-Options`、`Content-Security-Policy`、`X-Frame-Options`
- 上传：类型/大小/文件名校验，是否可传可执行文件，是否走 presigned URL
- 密码是否 bcrypt/argon2（不是 MD5/SHA1）
- `.env.example` 存在且不含真实值；`.gitignore` 覆盖 `.env`

## 5. 与其他手册的分工

| 主题 | 去哪 |
|---|---|
| 端点矩阵、错误契约 RFC 9457、幂等/并发/分页 | `api-testing.md` |
| 负载/压力/浸泡、p95 | `performance-testing.md` |
| 发布前安全门禁（Gate 3）、回滚 | `fullstack-integration.md` |
| 缺陷严重度、报告八字段 | `quality-gates.md` |
| 越权/注入的具体"刁钻用户"动作 | `personas.md` |

## 6. 严重度判定

| 级别 | 命中 |
|---|---|
| **严重** | 越权可读写他人数据、认证可绕过、注入生效、密钥硬编码入库、远程代码执行 |
| **一般** | 500 暴露堆栈、缺限流、CORS 过宽、缺安全头、废弃端点在线、错误信息泄漏内部路径 |
| **轻微** | 提示信息可枚举账号、错误文案不精确 |

> **推定不等于事实**：静态扫到疑似密钥，报告写"疑似硬编码凭据，待确认"，不要写"已泄漏密钥"。所有安全结论必须附实际请求/输出原文。

## 7. 报告纪律

- 复现命令**脱敏**（token、密码用 `$TOKEN` 占位，不写真实值）
- 不在报告里贴可被直接复用的完整攻击链；写"验证防御是否生效"的最小载荷即可
- 发现严重漏洞：立即停止扩大测试范围，先报告、再等用户决定
