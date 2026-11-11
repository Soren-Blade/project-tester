# 多租户隔离测试（阶段 3 · 横向叠加）

> 蒸馏自 OWASP《Multi_Tenant_Security_Cheat_Sheet》（`cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html`）、OWASP Authorization Cheat Sheet 基线，以及 `fullstack-dev` 的缓存 TTL/写失效、后台任务幂等与 DLQ 纪律。来源 URL 见 `CHANGELOG.md` v1.2.0。
> 定位：测的不是「有没有按 `tenant_id` 过滤」，而是**「在共享基础设施上，一个租户能否通过任意路径读到、写到、污染、恢复或观测到另一个租户的数据」**。单租户项目请勿叠加以免造出无意义的用例。

## 0. 适用边界与四条认知打底

| 触发 | 叠加本手册 | 不适用 |
|---|---|---|
| 有 tenant/organization/workspace 概念、SaaS、B2B 多客户、共享 DB/cache/queue/storage | 是 | 单租户、单用户本地工具 → 写「不适用：无租户边界」 |
| 有平台管理员、跨租户服务身份、共享备份或导出 | 是 | 仅靠物理隔离且无任何共享资源 → 只做 §5 DB-01 边界验证 |
| 只需验证运行时越权/注入 | 去 `references/security-testing.md` | 本手册只测**隔离**，不重复注入向量 |

四条最容易自欺的官方口径（原文引述，报告里可核查）：

1. 「Treat client-supplied tenant identifiers as selectors only. Verify that the authenticated principal is authorized to act in the selected tenant.」——`X-Tenant-ID` 不是授权凭证。
2. 「Query parameterization prevents injection, not cross-tenant access.」——参数化 SQL 通过 ≠ 隔离通过。
3. 「A shared queue or topic is not itself a tenant-isolation boundary.」
4. 「Object naming or prefixes alone are not authorization boundaries.」

**精度边界**：原 Cheat Sheet **没有独立的 Search / Index isolation 章节**，与搜索直接相关的明确要求只有 Separate Schemas 策略里的 "`search_path` handling"。本手册 §4 的搜索用例是把搜索当作 tenant-owned access path 从通用规则推导的，报告须标注「推导，非页面硬性规则」，不得写成「OWASP 要求每租户独立索引」。

## 1. 测试夹具（没有这套夹具，隔离测试基本测不出东西）

| 类别 | 最小配置 |
|---|---|
| 租户 | `T1`、`T2`；同一部署环境、同一套共享资源 |
| 身份 | `U1`(仅 T1 普通用户)、`U2`(仅 T2)、`A1`(T1 tenant admin)、`P1`(platform admin/auditor)、`S1`(tenant-scoped service identity)、`SX`(显式跨租户、单独授权、least privileged) |
| 冲突数据 | T1/T2 中存在**相同** `user_id`、`resource_id`、`document_id`、object key 片段、idempotency key —— 这是抓 cache key 碰撞的关键 |
| 共享资源 | 共享 cache、queue/topic、DB connection pool、backup、audit store、object storage |
| 环境指纹 | 必须用应用**实际部署**的 DB role、connection path、pooling mode；记录 `current_user`、`pg_roles`、policy inventory、cache key、queue metadata/payload、object path、signed URL、audit record、alert |

夹具用「相同 ID」而不是「不同 ID」——不同 ID 会让一大批越权路径碰巧返回空，把缺陷伪装成通过。

## 2. 一票否决门槛

任一命中即整个隔离结论 FAIL，不因其他项通过而折抵：

- `T1` 身份能读/写/删/列/缓存命中/队列消费/恢复/审计读取 `T2` 数据。
- `T1` 能通过 header、query、body、token claim、message field、object metadata 切换权威 tenant context。
- 普通 tenant request path 使用 superuser / `BYPASSRLS` / 无 tenant scope / privileged connection。
- 故意共享或 platform admin 路径缺 explicit authorization、exact permitted path、least privilege、audit trail，或能访问超出授权范围的租户。

## 3. Tenant Context Resolution（TC）

| # | 最小测试动作 | 通过判据 |
|---|---|---|
| TC-1 | 无 `verified_claims` / 无 `tenant_id` / 无效 membership 各发一次 tenant-scoped 请求 | `401 {"error":"Missing tenant context"}` 或 `403 {"error":"Tenant access denied"}`，且**不进入业务查询** |
| TC-2 | `U1` 持 T1 token，分别改 `X-Tenant-ID: T2`、query `tenant_id=T2`、body `tenant_id=T2`、伪造 token claim、重复/冲突 header | 服务端验证 `U1 ∉ T2` 后拒绝；不得返回 T2 数据；不得把客户端值写进 `current_tenant` |
| TC-3 | 用仍带 `tenant_id=T2` claim 但 membership 已撤销/过期的 `U1` token；再伪造 issuer | `get_active_membership(principal_id, tenant_id)` 失败即 `403`；claim 有 T2 不构成授权 |
| TC-4 | 在下游 service、async job、logger、repository 注入冲突 header/body/message field | 所有 tenant-sensitive 决策与日志都用 middleware 设的 server-verified `current_tenant`；无 unverified override |
| TC-5 | 遍历 tenant-scoped / public / global endpoint | tenant-scoped 每请求都校验；public/global **不**因缺 tenant context 失败，也不创建 artificial tenant context |
| TC-6 | `S1` 用 T1 credential 访问 T2 scope；`SX` 访问未授权 tenant；改 environment/scope；重放 credential | `S1` 拒绝；`SX` 仅能访问显式授权 tenant set / scopes / environments |
| TC-7 | B2B 签名：改 tenant selection / audience / method / path / body digest / expiration，重放过期签名 | 签名校验失败；同一签名不能切到 T2 或延长有效期 |
| TC-8 | 用已知/猜测的 T2 opaque UUID、随机 resource ID 访问 | 仍因服务端授权失败；**不得**以「ID 不可猜」作为验收理由 |

## 4. 跨租户 IDOR 与搜索查询层

| # | 最小测试动作 | 通过判据 |
|---|---|---|
| IDOR-1 | `U1` 用 T1 context 请求 T2 的 `document_id`/`resource_id` | `404` 或同等不泄露存在性的错误；不返回 T2 对象 |
| IDOR-2 | 枚举**所有** lookup：`get_by_id`/`list_all`/`create`/`delete`/export/批量/relationship load/raw SQL/async job | 每条都含 tenant scope 或等价授权；`create` 传 `tenant_id=T2` 应拒绝；`tenant_id + resource_id` composite key 是「one option, not a universal requirement」 |
| IDOR-3 | 绕过 API 直接调 repository / job / DB | 仍拿不到 T2 数据；授权边界被**每条** tenant-owned path 穿越，data-layer check 作为 defense in depth |
| IDOR-4 | 对比「T2 存在资源 / 不存在资源 / T1 无权限资源」三种响应 | status、body、timing、error message 都不泄露 T2 资源是否存在 |
| SEARCH-1 | Separate Schemas 下 `T1` role 执行 `SET search_path` 指向 T2 schema；跑 migration | grants / role separation 阻断；migration 只作用于授权 schema |
| SEARCH-2 | `T1` 搜只存在于 T2 的关键词/`document_id`/object metadata；试全文、模糊、autocomplete、export | 不返回 T2 结果、**命中数**、摘要、高亮或缓存片段 |
| SEARCH-3 | 绕过 UI 直调 search API / index query / internal query service | 每个入口都有 tenant scope 或等价 policy；不能只靠前端过滤 |
| SEARCH-4 | T1 搜索后缓存，再以 T2 或不同 user / locale / feature set / permission version 查同一关键词 | 不命中 T1 cache；权限变更后旧缓存不授予访问 |
| SEARCH-5 | 声称「共享 index 安全」 | 按 shared resource + tenant-owned access path 做否定路径证明，报告标注「基于通用规则推导」 |

> 与 `references/i18n-localization-testing.md` §4 联动：locale 变化会改变 collation 与搜索结果，SEARCH-4 的 cache key 必须包含 locale，否则「换语言」会串出别的租户的数据。

## 5. DB / RLS / 连接池

| # | 最小测试动作 | 通过判据 |
|---|---|---|
| DB-1 | 四种隔离策略分别按声明验证：Separate DBs（凭据/网络/admin path/backup 全隔离）、Separate Schemas（grants + `search_path`）、Shared Tables RLS（每个 tenant-owned table 否定路径）、Hybrid（逐 data class 记录边界） | 声明与实现一致；每个边界都有对应测试 |
| DB-2 | 用**部署环境实际** request role、connection path、pooling mode 跑全部用例 | 证据含 `current_user`、`pg_roles` 查询结果、pooling mode；不得用 privileged test connection 假装通过 |
| DB-3 | 查 deployed request role：`SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user` | 两者均 `false`；**查部署角色，不只看源码里的配置** |
| DB-4 | 核对 `ENABLE ROW LEVEL SECURITY` / `FORCE ROW LEVEL SECURITY` / `CREATE POLICY`；用 T1/T2 context 跑 CRUD | `FORCE RLS` 约束 table owner 但**不约束 superuser / BYPASSRLS**；跨租户 SELECT/UPDATE/DELETE 全拒 |
| DB-5 | schema-derived inventory 对比 `pg_class.relrowsecurity`、`relforcerowsecurity`、`pg_policies` | 新表无 classification、RLS disabled、expected policy absent 任一即 FAIL；优先自动发现，别用手工表清单（会 drift） |
| DB-6 | 事务中不设 `app.current_tenant` 直接查 RLS 表 | fail closed（省略 `missing_ok => true` 会 raise error）；不得 fallback 到 unscoped query |
| DB-7 | 对比 `SET` / `SET LOCAL` / `set_config(..., true)`；每次借用连接后查 setting | 只允许 transaction-local；每个 transaction 重新建立 tenant context；「Never assume a newly borrowed connection has the correct setting.」 |
| DB-8 | **连接复用**：同一 pooled connection 上先 T1 请求、再 T2 请求、再缺 context 请求 | T2 看不到 T1 的 `app.current_tenant`；缺 context fail closed；连接归还前已 commit/rollback |
| DB-9 | ORM：测 eager load、lazy load、relationship load、aliases，再测 raw SQL / Core / bulk / 其他 session 类型 | `SessionEvents.do_orm_execute` + `with_loader_criteria` 覆盖 ORM 加载；`before_compile` 已 deprecated 且不覆盖 relationship loads；「This ORM helper is defense in depth, not complete enforcement.」 |
| DB-10 | 对每个 RLS-protected table 建授权矩阵 | same-tenant allowed / cross-tenant denied / intentional sharing & platform admin 仅 exact permitted path 且「grants no broader access」 |

## 6. Cache / Queue / 异步与共享资源

| # | 最小测试动作 | 通过判据 |
|---|---|---|
| C-1 | 盘点所有 cache key，逐个分类 global / tenant-scoped / user-scoped | 无未分类 tenant-scoped value；global namespace 有「why safe to share」文档 |
| C-2 | T1/T2 建相同 `user_id`，先缓存 T1 preferences，再以 T2 读 | 不得命中；key 形如 `tenant:{tenant_id}:{resource}:{item_id}`；禁用 `global:user-preferences:{user_id}`（user IDs 跨租户不保证唯一） |
| C-3 | 改 user / **locale** / feature set / permission version 后复用同一 key；直接构造 T2 key 绕过鉴权读 Redis | 不返回他人结果；**授权发生在 cache lookup 之前**，key 隔离不能替代授权 |
| C-4 | 修改 membership/permission 后在 TTL 内重复访问 | 高授权风险 value 及时失效或版本变更；immutable versioned global entry 可按文档无 expiry |
| C-5 | `T1` 尝试写全局或 T2 namespace 的 cache key | 写入被拒或隔离；T2 后续读取不受污染 |
| Q-1 | 盘点所有 queue/topic/job，分类 global / tenant-scoped / explicitly cross-tenant | 无未分类 tenant-scoped job；共享 queue/topic 不被当成隔离边界 |
| Q-2 | `T1` producer 发 `tenant_id=T2` message field；篡改 metadata/payload；伪造 broker routing | consumer 不用 unverified field；context 来自 authenticated producer，靠 trusted broker routing / authenticated metadata / integrity-protected payload 绑定 |
| Q-3 | enqueue 后撤销 `U1` membership/permission，再让延迟 job 消费 T2 target | consumer 重新建立 context 并**重查 time-sensitive 授权**；拒绝 stale decision |
| Q-4 | T1/T2 用相同 idempotency key；T1 读 T2 retry state / dead-letter；乱序消费 | dedup / retry / DLQ / per-tenant ordering 不跨租户混用 |
| Q-5 | global job 伪造 `tenant_id`；cross-tenant job 用普通 tenant identity | 拒绝；使用 explicit identities and scopes，**不 fabricated tenant** |
| Q-6 | `T1` 灌满 shared queue / worker pool / DB connections / fan-out，同时观测 T2 的 latency、吞吐、error rate | T2 不被 unbounded consumption 影响；tenant-aware + service-wide limits 同时生效；必要时隔离 worker/resource pool |
| Q-7 | `T1` 向共享 topic 注入 T2 job、dead-letter 或 cache invalidation 消息 | T2 无副作用；producer/broker path 被认证 |
| API-1 | 多实例并发压测 T1/T2，检查 rate-limit counter 维度；触发 throttling | counter 含 tenant identity 且保留 global/endpoint/user/IP 维度；多实例用 shared counters + atomic updates；`429` + `Retry-After`；响应不泄露其他租户状态 |
| API-2 | `T1` 在 HTTP 限额内大量消耗 queue / DB connections / worker concurrency / CPU / memory | 「Rate limits at the HTTP boundary do not constrain every shared resource.」→ 瓶颈处也要 tenant-aware limits |

## 7. 文件 / Blob / Onboarding / Offboarding / Backup

| # | 最小测试动作 | 通过判据 |
|---|---|---|
| F-1 | 仅靠 prefix 命名 `tenants/T1/...`，用 T1 identity 请求 `tenants/T2/...` | prefix 不授权；必须有 enforceable storage policy / bucket / account + tenant-aware key + authorization |
| F-2 | 提交 `/tenants/T2/...`、`tenants/T1/../T2/...`、encoded separator、backslash、double encoding、异常 tenant ID | 全部拒绝；tenant ID 符合 allowlisted canonical format；无法 escape namespace |
| F-3 | `T1` 对 T2 object 做 upload / download / delete / **generate signed URL**，并绕过 UI 直调 storage API | 四类操作均在 exact tenant/object/operation 授权前拒绝；授权发生在 signed URL 生成**之前** |
| F-4 | 给 T2 object 附加 `tenant_id=T1` metadata | 不信任 client-supplied metadata；以服务端 ownership / policy 为准 |
| F-5 | 改 signed URL 的 object/operation/tenant；过期后重放；撤销后重放 | 仅限 required object + operation；expiration/revocation 生效；tenant ID 不必出现在 URL，但 pre-sign authorization 必须有证据 |
| F-6 | 同时存在 `tenants/acme/` 与 `tenants/acme-west/`，offboard `acme` | 仅删 `tenants/acme/`（**带尾斜杠**的 exact prefix）；`acme-west` 不受影响 |
| F-7 | offboard 后访问 old version、replica、backup、export | 按 retention/deletion policy 处理，不应借旧版本/副本恢复访问；加密密钥在所有副本过 retention 前不得删除 |
| F-8 | onboarding 中途注入失败 | all-or-nothing：部分资源被清理、failure 被记录、无半初始化 tenant 可访问 |
| F-9 | 检查 tenant API credential 生成/返回/存储 | cryptographically secure random、≥128 bits entropy、仅返回一次、仅存 hash、无 plaintext；`SHA-256` 仅适用于 high-entropy random key，user-chosen secret 按 Password Storage Cheat Sheet |
| F-10 | offboard 后用旧 session/API key/service credential 发新请求 | tenant state 先拒绝新操作，再 revoke 所有 active sessions / API keys / tenant-scoped credentials |
| BK-1 | 用含 T1+T2 的 shared backup 恢复 T1；尝试把 shared snapshot 覆盖 live data | **restore into a separate resource + selectively recover T1**；禁止直接覆盖 live data |
| BK-2 | 未授权 actor 发起 restore；授权 actor 发起 restore | 未授权拒绝；授权操作记录 source backup、target、reason、outcome |
| BK-3 | `A1` 直接访问 shared backup；把 T2 record/object 复制进 T1 live scope | `A1` 无 shared backup 访问；复制前校验 ownership |
| BK-4 | backup 含已删除的 T1 membership 或已过期数据，恢复后访问 | 重新应用**当前** access/retention rules；old memberships 不可复活 |
| BK-5 | 两租户 backup 恢复 T1 的完整验收 | T1 数据存在、T2 records/objects **absent**、unauthorized restore request 被拒 |

## 8. Log / Audit / Admin / Privileged Path

| # | 最小测试动作 | 通过判据 |
|---|---|---|
| L-1 | 产生 T1 登录/拒绝/读写/admin 事件，检查 audit fields | 含 server-verified `tenant_id` + actor；**不记录客户端 header 里的 `tenant_id`** |
| L-2 | 产生匿名/系统/global infrastructure 事件 | 不强制伪造 actor 或 tenant；global event 可无 tenant |
| L-3 | `A1` 读 T2 audit / platform-wide audit；`P1` 无 explicit authorization 读取 | `A1` 拒绝（"Tenant administrator rights must not grant platform-wide audit access."）；`P1` 无授权也拒绝；授权成功有 audit trail |
| L-4 | 用 app role / tenant admin 尝试 update/delete audit record，并直接访问 DB/storage | append-only 由 DB permissions 或 WORM 控制，不能只靠应用层校验 |
| L-5 | 绕过应用直接篡改 audit storage | 产生 tamper detection / alert；报告明确「**检测**而非防止」 |
| L-6 | 生成 T1→T2 拒绝、重复 suspicious denial、授权 platform cross-tenant 操作 | 前两类监控/告警；授权 platform operation **不误报**为 violation |
| L-7 | 触发 RLS 缺失、role bypass、cache key 碰撞、queue tenant mismatch、storage path escape | 有 alert；控制失败与重复 denial pattern 可查询 |
| L-8 | 检查 access/error/audit/debug/signed URL/credential provisioning log | 无 secrets、无 plaintext 敏感 tenant data；必要字段按 policy mask/protect；每类 audit data 有 access + retention policy |
| ADM-1 | 所有 admin/service/internal endpoint 做 baseline access control | 无未授权访问；**"Skip authorization merely because a service is internal." 是反模式** |
| ADM-2 | `P1` 执行显式 cross-tenant admin path，再尝试扩大 tenant set / scope / object / operation | 仅 exact permitted path 成功；任何 broader access 被拒 |
| ADM-3 | privileged DB job 未指定 tenant set，或超出授权范围 | 拒绝或 fail closed；「A privileged job must explicitly authorize and constrain its tenant set or cross-tenant operation because RLS will not do so.」 |
| ADM-4 | `SX` 用 fabricated tenant ID / 访问未授权 scope；普通 `S1` 执行 cross-tenant job | 全部拒绝；`SX` 独立身份、显式 scope、least privileged |
| ADM-5 | 普通 tenant request 触发无 tenant scope query；cross-tenant admin path 无 audit | 普通路径必须 scoped；cross-tenant admin path 必须 explicit、separately authorized、auditable |

## 9. R-4 租户隔离（可证伪规则，见 SKILL.md）

| 声称 | 必须附的证据 | 不适用时的写法 |
|---|---|---|
| 「租户隔离有效 / 无跨租户数据泄漏」 | ① §1 夹具清单（T1/T2 + 相同 ID 冲突数据 + 实际 DB role/pooling mode）；② §2 一票否决四条逐条的**否定路径结果**（请求原文 + 返回码 + 数据结果 + cache key / queue metadata / object path / audit record）；③ §5 DB-8 连接复用、§6 Q-6 noisy-neighbor、§7 BK-5 双租户恢复三项的原始输出；④ 所有 intentional sharing / platform admin 路径的 exact permitted path 与 "no broader access" 证据 | 单租户、无共享资源、或用户禁止构造第二租户 → 只写「未做租户隔离验证 / 不适用」，**不得**写「隔离良好」 |

推论：**只测「T1 请求 T2 资源返回 404」不构成 R-4 通过**——它只覆盖了一条 API 路径，cache / queue / search / audit / backup / admin 每条 tenant-owned path 都要有否定路径证据。用「ID 是 UUID 猜不到」「有 RLS」「前缀带 tenant_id」当理由，一律判结论作废、降为「待确认」。

## 10. L0 零依赖降级、记录格式与分工

跑不起多实例/无第二个租户/无 DB 权限时，仍可做静态审查（结论标 `BLOCKED`，不判 Pass）：

```bash
git grep -nE '(X-Tenant-ID|tenant_id)' -- '*.ts' '*.py' '*.go' | head -60   # 客户端值是否被直接当权威 context
git grep -nE '(SET |set_config|search_path|BYPASSRLS|rolbypassrls)' -- .      # 事务本地 vs session 级、特权角色
git grep -nEi '(cache|redis).*(key|get|set)' -- .                              # key 是否含 tenant_id
git grep -nE '(tenants/|prefix|signed_url|presign)' -- .                       # prefix 是否被当授权边界
git grep -nE '(\.\.|path\.join|os\.path)' -- '*/upload*' '*/storage*' 2>/dev/null  # 路径逃逸
```

报告固定写一行：「本轮仅静态核对 tenant context 传播与共享资源命名，**未做双租户否定路径实测**」。

```
夹具：T1/T2✅ 冲突ID✅ 部署role/pool◐(未取到 pg_roles)
TC：TC-1 401✅ TC-2 header注入✅ TC-3 撤销membership🐛(仍 200)
IDOR：get_by_id 404✅ list_all✅ search 命中数🐛 export⬜
DB：DB-3 rolsuper=false✅ DB-8 连接复用◐ DB-5 policy inventory⬜
Cache/Queue：C-2 key碰撞🐛 Q-3 stale授权⬜ Q-6 noisy-neighbor⬜
文件/备份：F-6 前缀尾斜杠✅ BK-5 双租户恢复⬜
审计：L-1 server-verified✅ L-3 tenant admin 越权🐛
局限：无第二套部署环境；未做 backup restore 实测
R-4：FAIL（否定路径存在 3 处通过 + 6 项 BLOCKED）
```

| 主题 | 去哪 |
|---|---|
| 运行时越权 / 注入 / OWASP API Top 10 2023 | `references/security-testing.md` |
| 端点矩阵、认证授权四列 | `references/api-testing.md` §3、`references/security-testing.md` §2 |
| 事务隔离、迁移 up/down、缓存与事件一致性 | `references/data-integrity-testing.md` |
| 结构化日志 / request_id / 告警（R-1） | `references/observability-testing.md` |
| locale 变化对排序与搜索缓存的影响 | `references/i18n-localization-testing.md` §4 |
| 交付链完整性（R-3） | `references/supply-chain-testing.md` |
| 全局 Go/No-Go | `references/quality-gates.md` §3 |
| 六门禁 12 分（Gate 1/3 吸收本手册证据） | `references/fullstack-integration.md` §6 |
| 矩阵模板 | `assets/tenant-isolation-matrix-template.md` |
