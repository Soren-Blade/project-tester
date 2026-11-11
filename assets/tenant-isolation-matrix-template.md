# 租户隔离否定路径矩阵（R-4）

> 配合 `references/multi-tenancy-testing.md` 使用。每行必须填：**请求原文 + 返回码 + 实际数据结果 + 共享资源证据**。空格、`-`、`无异常` 一律不算证据。
> 结论标记：`✅ 已拒绝` ｜ `🐛 越权/泄漏` ｜ `◐ 仅静态` ｜ `⬜ 未做（写原因）` ｜ `N/A（写原因）`。

```
项目/版本：___　隔离策略声明：Separate DBs / Separate Schemas / Shared Tables RLS / Hybrid
夹具：T1/T2 ___　冲突相同ID ___　U1/U2/A1/P1/S1/SX ___
环境指纹：DB current_user ___　rolsuper ___　rolbypassrls ___　pooling mode ___　connection path ___
```

## 1. 一票否决（任一不为 ✅ 则 R-4 = FAIL）

| # | 路径 | 请求原文 / 身份 | 返回码 | 实际数据结果 | 结论 |
|---|---|---|---|---|---|
| V-1 | T1 → T2 读/写/删/列/缓存命中/队列消费/恢复/审计读取 | | | | |
| V-2 | 改 header / query / body / token claim / message field / object metadata 切换 context | | | | |
| V-3 | 普通 tenant request path 使用 superuser / `BYPASSRLS` / 无 scope / privileged connection | | | | |
| V-4 | intentional sharing / platform admin 路径越出 exact permitted path | | | | |

## 2. 分层否定路径矩阵

| 层 | 用例 | server-verified tenant_id | 请求/响应原文 | 共享资源证据（cache key / queue metadata / object path / audit / alert） | 结果 |
|---|---|---|---|---|---|
| TC | TC-1 缺 context / 无效 membership | | | | |
| TC | TC-2 `X-Tenant-ID: T2` 注入 | | | | |
| TC | TC-3 撤销 membership 后旧 token | | | | |
| TC | TC-4 下游 / job / logger 注入冲突字段 | | | | |
| TC | TC-6 `S1`/`SX` credential scope | | | | |
| IDOR | IDOR-1 `T2` document_id | | | | |
| IDOR | IDOR-2 get / list / create / delete / export / bulk / relationship load / raw SQL | | | | |
| IDOR | IDOR-4 存在性泄露（status/body/timing/error） | | | | |
| SEARCH | SEARCH-2 全文/模糊/autocomplete/export 的 T2 结果、**命中数**、摘要、高亮、缓存片段 | | | | |
| SEARCH | SEARCH-4 locale / permission version 变化后的搜索缓存 | | | | |
| DB | DB-1 策略边界（凭据/网络/admin/backup 或 schema grants 或 RLS） | | | | |
| DB | DB-3 deployed role `rolsuper`/`rolbypassrls` | | | | |
| DB | DB-5 policy inventory vs `pg_class` / `pg_policies` | | | | |
| DB | DB-6 缺 `app.current_tenant` 时 fail closed | | | | |
| DB | **DB-8 同一 pooled connection：T1 → T2 → 缺 context** | | | | |
| DB | DB-9 eager/lazy relationship load、raw SQL、bulk | | | | |
| CACHE | C-2 相同 `user_id` 的 cache key 碰撞 | | | | |
| CACHE | C-3 绕过鉴权直读 Redis；权限/locale/feature 变更后复用 key | | | | |
| QUEUE | Q-2 producer 伪造 `tenant_id=T2` / metadata 篡改 | | | | |
| QUEUE | Q-3 enqueue 后撤销权限，延迟 job 的 stale 授权 | | | | |
| QUEUE | Q-4 相同 idempotency key / DLQ / ordering | | | | |
| QUEUE | **Q-6 noisy-neighbor：T1 flood 时 T2 的 latency/吞吐/错误率** | | | | |
| FILE | F-1 prefix 命名被当授权边界 | | | | |
| FILE | F-2 路径逃逸 `/tenants/T2/`、`../`、encoded separator | | | | |
| FILE | F-3 upload/download/delete/**signed URL 生成前**授权 | | | | |
| FILE | F-6 offboard `tenants/acme/` 时 `acme-west` 是否受牵连 | | | | |
| FILE | F-7 old version / replica / backup / export 残留 | | | | |
| BK | **BK-5 双租户 backup 恢复 T1：T2 records absent + 未授权 restore 被拒** | | | | |
| LOG | L-1 audit 里的 tenant_id 是否 server-verified | | | | |
| LOG | L-3 tenant admin 读 platform-wide audit | | | | |
| LOG | L-4/L-5 append-only / WORM 与 tamper detection | | | | |
| ADM | ADM-2 exact permitted path 与 "no broader access" | | | | |
| ADM | ADM-3 privileged job 未 constrain tenant set | | | | |
| ADM | ADM-5 内部 service 跳过授权 | | | | |

## 3. Intentional sharing / 特权路径登记（不能只测「拒绝」）

| 路径 | 身份 | 显式授权来源 | exact permitted path | least privilege | audit trail | no broader access 证据 |
|---|---|---|---|---|---|---|
| | `P1` / `SX` | | | | | |

## 4. 结论

```
一票否决：___（4 条逐条结果）
否定路径：✅__ / 🐛__ / ◐__ / ⬜__ / N/A__（合计 = 用例总数）
静态-only 项：___
未做项与原因：___
R-4：PASS / FAIL / BLOCKED
```

> 只测「T1 请求 T2 资源返回 404」**不构成 R-4 通过**；以「ID 是 UUID 猜不到」「有 RLS」「前缀带 tenant_id」作理由，结论作废、降为「待确认」。
> 单租户 / 无共享资源 / 禁止构造第二租户 → 只写「未做租户隔离验证 / 不适用」，不得写「隔离良好」。
> 分工：运行时越权 → `references/security-testing.md`；locale 对搜索缓存的影响 → `references/i18n-localization-testing.md` §4；Go/No-Go → `references/quality-gates.md` §3；发布门禁 → `references/fullstack-integration.md` §6。
