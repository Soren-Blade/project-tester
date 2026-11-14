# 身份 · 会话 · 令牌测试（v1.8）

> 触发：项目有登录/注册/找回/改密/登出、Cookie 会话、JWT/Opaque Token、OAuth 2.0 / OIDC / SSO、MFA / Passkey；或宣称「认证安全 / JWT 校验正确 / 令牌不可伪造 / 登出即失效 / 双因素」。
> 底座：OWASP ASVS 5.0（V6 Authentication、V7 Session、V8 Authorization、V9 Self-contained Tokens、V10 OAuth/OIDC）、RFC 8725（JWT BCP 225）、RFC 9700（OAuth 2.0 Security BCP 240）、OWASP Password Storage / Session Management / Authentication Cheat Sheets、NIST SP 800-63B-4、W3C WebAuthn L3。
> 一句话：**能登录 ≠ 认证安全；令牌能解码 ≠ 能伪造；Cookie 有 HttpOnly ≠ 会话安全。** 本手册的每条都能落成「动作 → 观察 → 判据」，不能落地的漂亮话不要写进报告。

## 0. 版本口径（先钉死，再测）

| 标准 | 引用版本 | 注意 |
|---|---|---|
| ASVS | **v5.0.0**（2025-05-30 发布） | 仓库 tag `latest` 是自动重建的 bleeding edge，**不是**新版本，不得当稳定版引用 |
| RFC 8725 | BCP 225，2020-02，Updates 7519 | 只点名 `kid`/`jku`/`x5u`；`x5c`/`jwk` 头注入**不是**它的明文条款 |
| RFC 9700 | BCP 240，2025-01，Updates 6749/6750/6819 | 定稿取代 draft-ietf-oauth-security-topics；不 obsoletes 6749 |
| NIST 800-63B-4 | Final，2025-07 | 取代 800-63B；限速条款**未给具体次数**，勿编「100 次」 |
| WebAuthn | W3C Rec L3（2026-08-25） | 若只读到 §1.2 之后被截断，机制描述标「推论」 |

报告里写标准版本；版本不明时写「标准版本未核验，结论降级为待确认」。不要把 ASVS L2/L3 条目当 L1 要求来判缺陷。

## 1. 令牌与会话清单（先做，1 小时内）

| 项 | 记录什么 |
|---|---|
| 令牌种类 | access / refresh / id_token / session cookie / reset / verify / MFA challenge |
| 载体 | `Authorization: Bearer` / Cookie / URL query / localStorage / sessionStorage / 日志 / 前端报错上报 |
| 形态 | JWT（`header.payload.signature`）/ opaque / 混合；JWE 是 5 段，工具不解密 |
| 生命周期 | 签发点、TTL、刷新方式、撤销方式、登出/改密/重置后的处置 |
| 端点 | 登录、刷新、登出、找回、重置、改密、MFA 绑定/校验、OAuth 授权/令牌/回调 |

**储存位置判据**：access/refresh 落在 `localStorage` → 任何 XSS 即令牌失窃，记高风险（与 `frontend-testing.md` §2 的 XSS 用例联动）；出现在 URL → 记入日志/Referer/浏览器历史泄漏路径。Cookie 必须逐项核对：`HttpOnly`、`Secure`、`SameSite`（会话 cookie 用 `Strict` 优先，`None` 必须配 `Secure`）、`Path`/`Domain`、`__Host-`/`__Secure-` 前缀约束。

结构审计先跑机器：`python scripts/jwt-audit.py decode --token-file token.txt --now 2026-11-14T00:00:00Z --format markdown`。它只报「可疑项」（缺 exp/aud/iss、alg none、弱 HMAC 字典命中、`kid`/`jku`/`x5u` 注入面、空签名），**不证明服务端接受了该令牌，也不证明密钥强度**。未命中弱密钥字典 ≠ 密钥强。

## 2. JWT 十类攻击测试卡（AUTH-1 ~ AUTH-12）

每张卡：动作 → 观察 → 判据。全部只对自己构造的测试账号与合成令牌执行。

| 编号 | 攻击 | 动作（curl/HTTP 客户端原文进证据） | 判据（失败信号） |
|---|---|---|---|
| AUTH-1 | `alg: none` 降级 | 取合法 token，改 header 为 `{"alg":"none","typ":"JWT"}`，签名段留空或删掉 | 受保护端点返回 2xx → 缺陷（ASVS 9.1.2；RFC 8725 3.2） |
| AUTH-2 | 算法混淆 | 服务端发布 RS256 公钥；用该公钥 PEM 当 HMAC 密钥签 HS256 token 提交 | 被接受 → 缺陷（RFC 8725 3.1：每把密钥只用于一种算法） |
| AUTH-3 | 弱 HMAC 密钥 | `jwt-audit.py verify --token … --secret …` 跑常见弱密钥字典；或用 `hashcat -m 16500` 离线验证（仅在自有副本/自有账号上） | 命中任意弱密钥 → 缺陷（RFC 8725 3.5：人可记密码不得直接当 MAC 密钥） |
| AUTH-4 | 签名剥离/篡改 | 改 payload 任一字段（`sub`、`role`、`tenant`、`aud`）保留原签名 | 仍被接受 → 缺陷（RFC 8725 3.3） |
| AUTH-5 | 过期令牌 | 用 `exp` 已过的令牌（`--now` 固定时间构造，勿等真实过期） | 2xx → 缺陷（ASVS 9.2.1） |
| AUTH-6 | 未来令牌 | `nbf`/`iat` 在未来的令牌 | 2xx → 缺陷（ASVS 9.2.1） |
| AUTH-7 | 受众错误 | 把给服务 A 的 token 提交给服务 B（改 `aud` 或直接跨服务） | 2xx → 缺陷（RFC 8725 3.9） |
| AUTH-8 | 签发方错误 | 改 `iss` 指向另一已接入 issuer，或伪造 issuer 域名 | 2xx → 缺陷（RFC 8725 3.8） |
| AUTH-9 | `kid` 注入 | `kid` 填 `' OR 1=1--`、`../../etc/passwd`、超长串、空串 | 500/数据库报错/路径报错 → 缺陷（RFC 8725 3.10） |
| AUTH-10 | `jku`/`x5u`/`x5c`/`jwk` 注入 | `jku`/`x5u` 指向自己控制的 JWKS 或内网地址；`jwk` 内嵌攻击者公钥 | 服务端拉取外链、接受内嵌密钥、或对内网发起请求 → 缺陷/SSRF（RFC 8725 3.10 点名 jku/x5u；x5c/jwk 属实现缺陷，勿冒充条款） |
| AUTH-11 | 类型混用（cross-JWT confusion） | 把 ID Token / logout+jwt 当 access token 调业务 API；`typ` 缺失或换类型 | 2xx → 缺陷（RFC 8725 3.11/3.12：不同令牌类型校验规则必须互斥） |
| AUTH-12 | 空签名/畸形结构 | 签名段为空、段数异常（2 段/4 段/5 段 JWE 混投）、base64 非法、超长 header | 5xx 或 2xx → 缺陷；**4xx 但要记录是否泄漏解析细节/堆栈** |

补充：JWT 里放 `role`/`tenant` 并直接用于授权而不校验签名或 `aud` → 记 AUTH-4+越权复合缺陷。

## 3. 会话生命周期（S1 ~ S9）

| 编号 | 场景 | 动作 | 判据 |
|---|---|---|---|
| S1 | 登录后会话固定 | 登录前后记录会话 ID/Cookie 值对比 | 值不变 → 缺陷（ASVS 7.2.4；Session CS「mandatory」） |
| S2 | 空闲超时 | 登录后静置（高价值 2–5 分钟 / 低风险 15–30 分钟口径），再请求受保护页 | 仍可用 → 缺陷（ASVS 7.3.1；必须服务端强制） |
| S3 | 绝对生命期 | 把客户端时间/本地存储里的时间戳改早改晚，重复请求；对照服务端会话记录 | 服务端到期仍可用 / 仅客户端计时 → 缺陷（NIST AAL2 overall ≤24h、inactivity ≤1h；AAL1 overall ≤30 天） |
| S4 | 登出失效 | 登出后重放旧 Cookie、旧 access、旧 refresh | 任一仍可用 → 缺陷（ASVS 7.4.1）；自包含令牌的撤销机制**需源码审计**才能确认 |
| S5 | 改密/重置后失效 | 改密或完成重置后重放旧会话与旧 refresh | 仍可用 → 缺陷（ASVS 7.2.4/7.4.1） |
| S6 | 刷新轮换 | 连续两次用同一 refresh token 换新 token（含 2 并发） | 旧 refresh 仍可反复使用 → 缺陷（RFC 9700 §4.14.2：旧 token 必须失效，重放撤销整条授权） |
| S7 | 会话 ID 熵 | 抓 ≥1000 个会话 ID/重置令牌，查重复、长度、字符集、模式 | 有重复/自增/时间戳/短于 128 bit 熵 → 缺陷（ASVS 7.2.3；Session CS 自建 ≥128 bit，建议 ≥160 bit） |
| S8 | 敏感操作再认证 | 改邮箱/手机/MFA/恢复信息、查看备份码 | 未要求重输密码或因子（仅 CSRF token 不算）→ 缺陷（ASVS 7.5.1） |
| S9 | Cookie 属性与会话边界 | 逐项核对 HttpOnly/Secure/SameSite/Path/Domain/前缀；`document.cookie` 是否可读 | 缺 HttpOnly → XSS 可窃取；缺 Secure → 明文信道；`SameSite=None` 无 Secure → 缺陷（Session CS） |

登出可附带 `Clear-Site-Data: "cache", "cookies", "storage"`；但**响应头存在不等于服务端已失效**，必须重放验证。

## 4. 登录 / 找回 / MFA / OAuth 流程（F1 ~ F12）

| 编号 | 场景 | 动作 | 判据 |
|---|---|---|---|
| F1 | 账户枚举 | 存在/不存在用户各 20 次失败登录 + 注册 + 找回，记录状态码、响应体、耗时分布 | 任一可区分 → 缺陷（ASVS 6.3.8）；统一文案示例：「If that email address is in our database, we will send you an email to reset your password.」 |
| F2 | 爆破限速 | 同一账号连续错误口令，观察锁定阈值/观察窗/锁定时长；换 IP/换 UA 再试 | 无锁定、仅按 IP 限速、可无限尝试 → 缺陷（NIST：必须有效限速，未给次数；计数应绑账户） |
| F3 | 锁号 DoS | 用他人账号触发锁定，再用正确密码登录 | 正确密码也被长期拒绝且无解锁路径 → 记风险（限速设计的副作用） |
| F4 | 密码策略 | 7 位/8 位/20 位全小写、>64 位、含空格与 emoji；检查是否有组成规则/周期改密 | 8 位被拒、强制大小写数字符号、90 天强制改密 → 缺陷（ASVS 6.2.1/6.2.5/6.2.10；NIST：单因子 ≥15、MFA 下 ≥8、最大 ≥64、无组成规则、不周期改密） |
| F5 | 密码截断 | 构造 72/73/100 字节及含多字节字符的密码注册再登录 | 超长被静默截断（bcrypt 72 字节上限）→ 缺陷（NIST：必须校验完整密码） |
| F6 | 密码存储 | 读源码/配置：算法、参数、每用户 salt；解析 hash 串 | `$argon2id$m=…,t=…,p=…` 低于 19 MiB/t=2/p=1、bcrypt cost<10、PBKDF2-SHA256<600k、scrypt<2^17、无 salt、SHA/MD5 明文散列 → 缺陷（Password Storage CS）；黑盒无源码 → 「未验证（需源码审计）」 |
| F7 | 重置令牌 | 触发找回，检查令牌是否出现在响应/URL/日志；再请求重置 | 可预测（base64(email)/时间戳/短随机）、无过期、重置后仍有效、响应体回显 → 缺陷（ASVS 7.2.3；重置令牌 TTL 应短且一次性） |
| F8 | 重置令牌重放 | 同一重置令牌用两次；重置后旧令牌再试 | 第二次成功 → 缺陷（一次性） |
| F9 | 重置后旧凭据 | 重置密码后，用旧密码、旧会话、旧 refresh 登录/访问 | 任一成功 → 缺陷 |
| F10 | MFA / OTP | 同 OTP 两次提交（含 2 并发）；OOB 等待 >10 分钟再试；换 OTP 后错误计数是否重置；`userVerification=required` 时检查 UV | OTP 可复用、OOB 超 10 分钟仍有效、换码重置失败计数、SMS/邮件作为唯一 OOB → 缺陷（ASVS 6.5.1/6.5.5；NIST：OOB 10 分钟内、≥6 位、邮件不得用于 OOB） |
| F11 | OAuth/OIDC 流程 | `redirect_uri` 变体（加 `/`、`../`、`?x=1`、`#`、子域、http、非 localhost 端口、开放重定向跳板）；缺 PKCE / `plain` / 错 verifier；同一 code 换两次；`response_type=token`；`grant_type=password`；双 AS mix-up | 非精确匹配被接受、公共客户端无 PKCE 仍成功、code 可重放且未撤销令牌、implicit/ROPC 可用、错配 issuer 被接受 → 缺陷（RFC 9700；ASVS 10.4.1/10.4.2/10.4.6） |
| F12 | 会话/令牌日志 | 抓服务端日志、错误上报、前端 console | 打印原始 token/密码/Cookie/Authorization → 缺陷（V16；Session CS：不得记录原始 session ID） |

判定门槛固定：**先只读探测版本与端点 → 再用自建账号做负向 → 再回归正向**。每条例外都要写「未测/待确认」，不得用「登录成功」覆盖认证结论。

## 5. 授权交叉（与 BOLA 联动）

认证通过后立刻做 A2/A3：A 的令牌访问 B 的对象 ID（数字、UUID、批量、导出、嵌套资源）→ 必须 403/404；管理员端点用普通用户令牌 → 必须 403。一条 404 不能证明隔离（可能只是路由不存在），要用**存在对象 + 无权限**的组合证明（ASVS 8.2.2；交叉 `api-testing.md` §4、`multi-tenancy-testing.md`）。

## 6. 执行纪律与安全边界

- 只用**自己注册/构造**的测试账号与合成令牌；不猜真实用户密码、不撞库、不对第三方服务爆破。
- 限流/锁定测试保持**小样本**（如 5–10 次即停），命中锁定立刻停止并等待解锁，避免把测试环境锁死。
- 发现真实令牌/密码泄漏：先脱敏（只留前 6 位+长度），再记录；报告与截图不得含完整凭据。
- 生产环境只做只读探测与自建账号的负向测试；破坏性用例（改密、锁定、撤销）默认只在测试环境执行。
- `jwt-audit.py` 的结论是「结构可疑项」，不能写成「令牌可伪造 / 服务端校验失败」；必须补请求原文与响应码。
- 时间相关用例用固定 `--now` 构造令牌，避免等待与不确定性；报告写清构造命令。

## 7. 证据清单（R-12 对应）

| 证据 | 具体内容 |
|---|---|
| E1 令牌清单 | 种类 × 载体 × 形态 × TTL × 撤销方式 |
| E2 结构审计 | `jwt-audit.py decode` 原文输出（含 alg/exp/aud/iss/kid/jku 判定） |
| E3 伪造三连 | alg=none、算法混淆、空签名：请求原文 + 响应码 + 响应体 |
| E4 五类负向 | 过期 / 未来 / 错 aud / 错 iss / 类型混用，逐条结果 |
| E5 生命周期 | 登出、改密、重置后旧 access + 旧 refresh 均被拒的实测记录 |
| E6 刷新轮换 | 旧 refresh 重放结果；reuse detection/family 撤销证据；未实现则明确降级 |
| E7 枚举与限流 | 三列对照（状态码/响应体/耗时）+ 限流触发记录 |
| E8 密码存储 | 算法/参数/每用户 salt 的源码位置与原文（无源码写「未验证」） |

全部证据缺一不可；缺项时 R-12 只能写「降级为待确认」，**不得**写「认证安全 / 令牌不可伪造 / 会话安全」。

## 8. 路由与产出

- 模板：`assets/auth-matrix-template.md`（T1~T2 令牌行、J1~J11、S1~S9、F1~F12、A1~A3、R-12 结论）。
- 工具：`scripts/jwt-audit.py`（结构审计/签名核对/自检）；抓包与重放用项目既有 curl/HTTP 客户端，不新增强依赖。
- 联合手册：`api-testing.md`（BOLA/幂等）、`security-testing.md`（API Top 10 与输入向量）、`frontend-testing.md`（XSS 窃取 localStorage 令牌）、`observability-testing.md`（认证失败日志与告警）、`privacy-compliance-testing.md`（密码/token 入日志属 PII 泄漏）、`multi-tenancy-testing.md`（tenant 声明来自令牌时）。
- 产出：R-12 行 + 本手册 §7 证据表 + 缺陷单（按 `quality-gates.md` 八字段）+ 不适用声明（无身份与会话维度时写一句话，不填 PASS）。
