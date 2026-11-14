# 缓存与内容新鲜度测试（R-17）

一句话：**缓存不是「快不快」，而是「谁的内容、被谁、按什么键、存多久、什么时候必须失效」**——把这五问答不出来，CDN 就会把你的私有页面发给下一个访客。

适用：任何经过浏览器缓存、反向代理、CDN、service worker、应用内缓存或对象缓存的项目；有登录态与个性化内容时必做。
配套：`assets/cache-freshness-matrix-template.md`（矩阵）、`scripts/cache-audit.py`（`scan` / `headers` / `cases`）。
相关规则：R-17（本手册）、R-6 隐私（响应多给数据）、R-4 多租户（键里没有 tenant）、R-9 证据链（`Cache-Status` 输出留档）。三条交叉：**缓存泄漏 = 隐私泄漏 + 租户串数据 + 证据缺失**，任一命中都按 S1 处理。

## 0. 触发条件与不适用

| 场景 | 是否触发 | 说明 |
|---|---|---|
| 有 CDN / 反向代理 / `Cache-Control` 响应头 | ✅ 必做 | 共享缓存是主战场 |
| 登录后页面、`/api/me`、订单、后台 | ✅ 必做 | 个性化 + 鉴权内容最易被缓存泄漏 |
| 静态资源带 hash、长缓存 `immutable` | ✅ 做一遍 | 验发布后旧页面不引用新 hash 或反之 |
| 纯本地 CLI、无网络响应 | ❌ 不适用 | 只写「不适用：无 HTTP 缓存层」，**不得**写「缓存安全」 |
| 只有内存 LRU 且进程内、单租户 | ◐ 部分 | 只做键设计 + 失效，不写 CDN 结论 |

## 1. 缓存键与指令语义（先问五问）

1. **谁的内容**：公共？按用户？按租户？按 locale/设备？
2. **被谁缓存**：浏览器私有缓存、共享代理/CDN、service worker、应用内缓存
3. **键是什么**：path + query + `Vary` 头 + host/scheme；键里是否含 tenant/user/locale
4. **存多久**：`max-age` / `s-maxage` / `Expires` / heuristic freshness
5. **何时失效**：过期、`no-cache` 验证、purge、发布换名

| 指令 | 语义（RFC 9111） | 常见误用 |
|---|---|---|
| `no-store` | 任何缓存都不得存储 | 用 `no-cache` 当「不存」→ 仍会存，只是每次验证 |
| `no-cache` | 可存，但每次使用前必须向源站验证 | 用在含 PII 响应上 → 中间缓存仍持有副本 |
| `private` | 仅浏览器私有缓存可存 | 漏写 → CDN 可存个性化页 |
| `public` | 共享缓存可存 | 与 `Set-Cookie`、登录态同现即泄漏 |
| `max-age=N` | 相对新鲜期（秒） | `max-age=0, must-revalidate` 才是「可存但立即验证」 |
| `s-maxage=N` | 仅共享缓存的新鲜期，覆盖 max-age | 只写 `max-age` 却指望 CDN 短缓存 |
| `must-revalidate` | 过期后不得用 stale | 与 `stale-while-revalidate` 混用需说清优先级 |
| `stale-while-revalidate=N` | 后台异步刷新期间可先给 stale | 敏感内容用 stale → 已登出用户仍看到私有页 |
| `stale-if-error=N` | 源站错误时可用 stale | 未配合监控 → 故障期一直发旧数据无人知 |
| `immutable` | 有效期内不验证 | 配短 max-age 或可变 URL → 用户长期看不到更新 |

## 2. 新鲜度、验证与条件请求

- `ETag` + `If-None-Match` → 304；`Last-Modified` + `If-Modified-Since`。**304 不带 body，但头必须与 200 一致**（`Cache-Control`、`Vary`、`Content-Type`）。
- 强/弱 ETag：`W/` 前缀表示语义等价；按用户数据算 ETag 且未加 `private` → 跨用户 304 命中（信息泄漏）。
- `Range` + `If-Range`：分片下载时 ETag 变化必须使旧 Range 失效，否则拼出混合版本文件。
- 发布后的旧 HTML 引用新 hash 资源（或反之）→ 白屏/旧逻辑；用 `index.html` `no-cache` + 资源 `immutable` 的组合验证。
- 应用内缓存（Redis/memcached）同样要问键与 TTL：`no-store` 管不到它，见 `data-integrity-testing.md` 缓存一致性。

## 3. 共享缓存安全（Web Cache Deception / Poisoning）

| 编号 | 攻击/缺陷 | 最小验证 | 判据 |
|---|---|---|---|
| C-01 | 路径扩展名欺骗：`/account/foo.jpg` 被源站当 `/account` 处理却按 `.jpg` 缓存 | 登录后请求 `/account/x.jpg`，换未登录会话再取 | 第二个会话拿到第一个人的内容 → S1 |
| C-02 | 缺少 `Vary`（Accept-Encoding/Cookie/Authorization） | 带/不带 `Accept-Encoding: gzip` 各取一次 | 返回错编码体或错用户数据 |
| C-03 | `public` + `Set-Cookie` 同响应 | 检查响应头组合 | 共享缓存可存带会话的响应 → S1 |
| C-04 | 未键控输入投毒：`X-Forwarded-Host`、`X-Original-URL`、`X-Rewrite-URL` | 注入后看缓存键是否变化 | 攻击者一次请求污染所有用户 |
| C-05 | 缓存键归一化差异：大小写、`%2e%2e`、重复斜杠、`;` 参数 | 变体请求命同一条目 | 鉴权绕过 + 内容串号 |
| C-06 | `Vary: *` | 检查头 | 共享缓存无法使用（等于不缓存）或行为未定义 |
| C-07 | purge 端点无鉴权 | 匿名 POST purge | 任意人可清空/污染缓存 → S1 |
| C-08 | 多租户键缺 tenant | A 租户 URL 命中 B 租户内容 | R-4 交叉，S1 |

> 判定要点：**「刷新一下就好了」不是缓存正确**。要证明的是「不同身份的请求不会命中同一条缓存」，以及「过期/失效后必然回源」。

## 4. 个性化、鉴权与租户

- 登录态页面默认 `Cache-Control: private, no-store`（或至少 `private, no-cache`）；API 带 `Authorization` 时默认不共享缓存。
- 若必须缓存个性化片段，键必须含 user/tenant/权限版本，并在权限变更（登出、降权、踢人）时失效。
- 多租户：键含 `tenant_id`，且 tenant 来自服务端会话而非客户端头（见 `multi-tenancy-testing.md` CACHE 面）。
- 反例：`/api/users/:id` 用 URL 做键但鉴权在 handler 里 → 缓存层先返回别人的数据。

## 5. 失效、发布与 purge

- 发布三件套：HTML `no-cache`（或短 max-age + 验证）、静态资源内容 hash + `immutable`、API 版本化路径。
- purge 必须是**带鉴权 + 可审计**的操作；soft purge（标记 stale 再回源）与 hard purge 要分清。
- purge 失败要有兜底：发布后自动探测关键 URL 的 `Age` / `Cache-Status` / 内容版本号。
- `stale-if-error` 必须有监控与上限，否则源站故障时用户长期看旧数据且无人知晓。
- service worker：`skipWaiting`/`clients.claim` 与版本号策略；旧 SW 缓存新 API 响应是常见混合故障。

## 6. 缺陷判定表

| 现象 | 级别 | 判据 |
|---|---|---|
| 未登录会话拿到登录用户页面/接口数据 | S1 | 两个独立会话对照，响应体含他人 PII |
| `public` 响应携带 `Set-Cookie` 或 token | S1 | 响应头组合 + 共享缓存命中证据 |
| 匿名可调用 purge/invalidate | S1 | 请求原文 + 200 + 缓存被清 |
| 多租户缓存键无 tenant，A 命中 B | S1 | 双租户夹具对照 |
| `Vary` 缺失导致压缩/语言/设备错版 | S2 | 变体请求对照 |
| 发布后用户长期拿旧 HTML/JS | S2 | 版本号 + `Age` + 强刷对照 |
| `no-cache` 被当 `no-store` 使用 | S2 | 头语义 + 中间缓存仍持有副本 |
| `immutable` 配短 max-age 或可变 URL | S3 | 头组合与 URL 策略 |
| `stale-if-error` 无上限无监控 | S3 | 配置 + 故障期观测缺失 |

## 7. 验证命令（零依赖优先）

```bash
# 1) 看头：两次请求对比 Age / Cache-Status / X-Cache / Vary
curl -sSI https://host/account | grep -iE 'cache-control|vary|age|cache-status|x-cache|etag|set-cookie'
curl -sSI https://host/account | grep -iE 'cache-control|vary|age|cache-status|x-cache|etag|set-cookie'

# 2) 条件请求：应 304 且头一致
ETAG=$(curl -sSI https://host/app.js | awk -F': ' 'tolower($1)=="etag"{print $2}' | tr -d '\r')
curl -sSI -H "If-None-Match: $ETAG" https://host/app.js | head -1

# 3) 缓存欺骗：登录态取带扩展名路径，再换会话取
curl -sS -b userA.jar https://host/account/foo.jpg -o a.html
curl -sS -b userB.jar https://host/account/foo.jpg -o b.html
cmp -s a.html b.html && echo "SAME-CONTENT: 需人工确认是否泄漏" || echo "different"

# 4) 未键控头投毒（只读探测，勿对生产写入）
curl -sSI -H 'X-Forwarded-Host: canary.example' https://host/ | grep -iE 'cache-control|age|x-cache'

# 5) 脚本：静态头与策略审计
python scripts/cache-audit.py scan .
python scripts/cache-audit.py headers --file headers.json --fail-on-gap
python scripts/cache-audit.py cases
```

`headers` 清单格式：`{"routes":[{"path":"/api/me","cache_control":"public, max-age=60","vary":[],"personalized":true,"auth":true,"purge_endpoint":"/admin/purge","purge_auth":false,"has_cookie":true}]}`。

## 8. 报告证据写法（R-17 五项）

1. 缓存策略表：路由 / 键来源 / `Cache-Control` / `Vary` / 个性化与鉴权标记；
2. 双会话对照：同一 URL 在两个独立会话下的响应 hash 与关键字段差异；
3. 头证据：两次请求的 `Age`、`Cache-Status`（RFC 9211）或 `X-Cache` 原文；
4. 攻击用例：C-01~C-08 中实际执行的条目与结果（未做的写明原因）；
5. 发布/purge：purge 鉴权、审计与失败兜底，或明确「未验证」。

**不得**写：「配了 CDN 就是缓存正确」「`no-cache` 就是不存」「缓存命中率高就是好」「刷新后正常就是没泄漏」。

## 9. 项目形态 → 证据

| 形态 | 必做 | 证据 |
|---|---|---|
| 静态站 + CDN | HTML 短缓存 + 资源 hash | 发布前后 `Age`/版本号对照 |
| 登录型 Web/API | 私有响应不被共享缓存 | 双会话 + 头组合 |
| 多租户 SaaS | 键含 tenant 且服务端来源 | 双租户对照 |
| 服务端渲染 + 片段缓存 | 片段键含用户维度 | 登出/降权后片段失效 |
| service worker | 版本与 API 响应策略 | 旧 SW 下新接口行为 |

## 10. 来源

- RFC 9111 HTTP Caching：https://www.rfc-editor.org/rfc/rfc9111.html
- RFC 5861 stale-while-revalidate / stale-if-error：https://www.rfc-editor.org/rfc/rfc5861.html
- RFC 8246 immutable：https://www.rfc-editor.org/rfc/rfc8246.html
- RFC 9211 Cache-Status：https://www.rfc-editor.org/rfc/rfc9211.html
- RFC 9110 条件请求与 `Vary`：https://www.rfc-editor.org/rfc/rfc9110.html
- Cloudflare Cache Deception Armor（扩展名与 Content-Type 一致性校验）：https://developers.cloudflare.com/cache/cache-security/cache-deception-armor/
- PortSwigger Web Cache Deception / Poisoning：https://portswigger.net/web-security/web-cache-deception
- OWASP Web Security Testing Guide · Testing for Web Cache Poisoning：https://owasp.org/www-project-web-security-testing-guide/
