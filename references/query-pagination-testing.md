# 查询语义与分页正确性（R-19）

一句话：**列表页不是「能翻」，而是「同一条数据在被谁查、按什么排、翻到第几页、总数算的哪一批」**——排序无唯一键、`OFFSET` 漂移、`total` 漏了权限过滤，任何一条都会让用户「翻着翻着少一条 / 多一条 / 看到别人的」。

适用：任何有列表、搜索、筛选、排序、导出预览、无限滚动的项目；GraphQL connection、REST collection、后台表格、管理端都算。
配套：`assets/query-pagination-matrix-template.md`（矩阵）、`scripts/query-audit.py`（`scan` / `matrix` / `cases`）。
相关规则：R-19（本手册）、R-4 多租户（行级过滤）、R-6 隐私（`total` 与字段过度暴露）、R-17 缓存（同一 URL 不同页的缓存键）。三条交叉：**分页泄漏 = 越权 + 隐私 + 缓存串号**，任一命中按 S1。

## 0. 触发条件与不适用

| 场景 | 是否触发 | 说明 |
|---|---|---|
| 任何 `GET /collection?page=&size=&sort=&q=` | ✅ 必做 | 主战场 |
| 后台表格 / 管理端 / 导出前预览 | ✅ 必做 | 行级权限 + 深分页最易出事 |
| GraphQL `first/after/edges/pageInfo` | ✅ 必做 | 游标语义与 Relay 契约 |
| 无限滚动 / feed / 时间线 | ✅ 必做 | 并发插入下漂移最明显 |
| 单条详情、无列表的 CLI | ❌ 不适用 | 只写「不适用：无集合查询面」，**不得**写「分页正确」 |
| 静态全量列表（数据固定 < 1 页且无筛选） | ◐ 部分 | 只做排序与总数口径，不写并发稳定性结论 |

## 1. 先问五个契约问题

1. **谁能查**：过滤在 SQL/查询层还是取回后在内存过滤（后者 = 总数泄漏 + 短页）
2. **查什么**：`q` 的匹配语义（前缀 / 包含 / 分词 / 模糊）、大小写与重音是否敏感
3. **按什么排**：排序键是否白名单、是否唯一、空值排哪、collation 是什么
4. **页怎么切**：`offset/limit`、`keyset`（seek）、`cursor`；游标是否不透明、是否可篡改
5. **总数算哪批**：`total` 是否与 `items` 同一 `WHERE` + 同一权限；是精确 `COUNT(*)` 还是估算

> 五问答不出来就先别测「翻页」——测出来的「通过」没有口径。

## 2. 三种分页模式与稳定性判据

| 模式 | 典型参数 | 稳定条件 | 失效表现 |
|---|---|---|---|
| Offset | `page`/`size`、`LIMIT n OFFSET m` | 两次翻页之间数据不变 | 插入 → 重复；删除 → 遗漏；深页慢 |
| Keyset / seek | `after_id`、`(sort_key,id) > (?,?)` | `ORDER BY` 含**唯一 tie-breaker** | 无 tie-breaker → 同值行跨页乱序/丢失 |
| Cursor | `cursor=base64(...)`、`starting_after` | 游标不透明 + 服务端可校验 + 绑定过滤条件 | 改游标 → 越权/枚举/全表扫描 |

**必做实验（同一数据集，三组）**：

1. **静态遍历**：从第 1 页翻到最后一页，收集全部 id → `去重后数量 == 首页 total`，且 `并集 == 直接全量查询的 id 集合`（不重不漏）。
2. **并发插入**：翻到第 2 页前插入 1 条排在最前的新记录，再继续翻 → 记录是否重复或漏掉；`offset` 模式**必然**出问题，问题是要证明它出在哪一页、影响几条。
3. **并发删除**：翻页中途删掉第 2 页的一条 → 后续页是否整体前移导致漏读。

判据：**「翻完一次没发现重复」不算通过**，要给出页数、每页 id 数、去重前后数量、并发场景的前后对照。

## 3. 排序语义

- **白名单**：`sort` 只接受枚举值（`created_at|-created_at|title`），映射到固定列名；直接把 `req.query.sort` 拼进 `ORDER BY` 是 SQL 注入（`sort=id;DROP...`、`sort=(SELECT ...)`）。
- **唯一 tie-breaker**：`ORDER BY created_at DESC` 在大量同秒数据上顺序不稳定 → 必须补 `, id DESC`；否则分页边界会随机丢/重。
- **空值位置**：PostgreSQL 默认 `ASC` 时 NULLS LAST、`DESC` 时 NULLS FIRST；MySQL 相反；SQLite 又是 NULLS FIRST（ASC）。跨库/换库后「空值排最后」的承诺会静默改变。
- **collation**：MySQL `utf8mb4_0900_ai_ci` 大小写与重音不敏感；PostgreSQL 默认 libc/ICU 依 locale；`C` collation 按字节。`ORDER BY name` 在 `a`/`A`/`á`/`ä` 上的顺序、以及 `WHERE name = 'a'` 是否命中 `A`，必须实测而不是推断。
- **多键排序**：`sort=status,created_at` 的解析、缺省方向、非法方向（`sort=created_at;--`）都要有 4xx。
- **中文/emoji/土耳其 i**：`İ`/`i`、`ß`/`ss`、emoji 的排序与大小写映射在 ICU 与 libc 下不同；声称「按拼音排序」就必须给出 collation 或显式转换证据。

## 4. 搜索与筛选语义

| 编号 | 反模式 | 最小验证 | 判据 |
|---|---|---|---|
| QP-01 | `ORDER BY ${sort}` / 拼接排序键 | `sort=id,(select 1)`、`sort=1;--` | 500 且回显 SQL / 排序被改变 → S1 |
| QP-02 | `LIKE '%' || q || '%'` 未转义 `%` `_` `\` | `q=%`、`q=_`、`q=\` | 返回全表 / 语义被通配符改变 |
| QP-03 | 前导通配 `%q%` 走全表 | `EXPLAIN` 或延迟对比 | 10 万行下查询超预算且无 trigram/全文索引 |
| QP-04 | 大小写/重音敏感性与宣称不符 | `Ada` vs `ada` vs `Áda` | 该命中未命中 / 不该命中却命中 |
| QP-05 | `q` 超长/空串/纯空格/控制字符 | 1 万字符、`\u0000`、`%00` | 崩溃、500、或退化为全量 |
| QP-06 | 筛选与总数不同源 | 带 `filter` 的 `total` vs 逐页累加 | 数字不一致 |
| QP-07 | 多值筛选 `status=a&status=b` 解析歧义 | 重复参数、逗号、数组注入 | 只取第一个 / 注入 / 500 |
| QP-08 | 高亮/摘要未转义 | `q=<img src=x onerror=...>` | 响应 HTML 里原样出现 → XSS（并入 R-1 安全面） |

**空结果 vs 错误**：合法但无匹配 → `200 + items: [] + total: 0`；非法参数 → `4xx`。把「无结果」写成 404/500、或把非法排序静默退回默认值，都是契约缺陷（与 R-20 联动）。

## 5. 总数、页边界与元数据

- `total` 必须与 `items` **同一 `WHERE` + 同一权限过滤**；内存过滤后再 `total = filtered.length` 会让「第 1 页只有 3 条但 total=100」。
- `total` 是精确 `COUNT(*)`、窗口函数 `COUNT(*) OVER()` 还是估算（`pg_class.reltuples`、ES `track_total_hits`）必须写明；估算值不得写成「共 N 条」。
- 边界：`page=0`、`page=-1`、`page=abc`、`size=0`、`size=100000`、`page` 超出末页 → 明确 4xx 或空页 + 元数据；**不得** 500。
- `size` 必须有服务端上限（如 100），否则一次拉全表 = DoS + 数据外带。
- 末页 `has_next` / `next_cursor` 必须与「还有没有数据」一致；`next_cursor` 指向已删除行时要能优雅结束。
- 总页数 `ceil(total/size)` 与末页条数要对得上（`total=101,size=10 → 11 页，末页 1 条`）。

## 6. 深分页与性能

- `OFFSET 1000000` 会先取出并丢弃 100 万行（SQL:2023 语义如此，不是实现 bug）→ 深页延迟随页码线性增长；用 keyset 或「先按 id 范围过滤」替代。
- `COUNT(*)` 在大表 + 多条件 + 多租户下常是最大开销；要么缓存总数、要么显式声明「估算」。
- 排序键无索引 → filesort/全表；`EXPLAIN` 里出现 `Seq Scan` + `Sort` 要记录。
- 判据：给出「页码 → P50/P95 延迟」曲线与预算（如 P95 < 500ms）；只有第 1 页快不算通过。

## 7. 行级授权与租户（与 R-4 交叉）

- 过滤必须在查询层（`WHERE tenant_id = :ctx`），**不得**取回后在 JS/Python 里 `filter`：后者 `total` 会泄漏他人条数、页大小会抖动。
- 越权探测：A 会话用 B 的 `tenant`/`owner` 过滤参数 → 返回空/403，且**响应体与耗时**不暴露 B 是否存在。
- 权限变更（降权、移出团队）后，已发出的 `cursor` 不得继续返回旧权限范围的数据。
- 共享资源（公开项目 + 私有项目混排）的 `total` 只算可见集合。

## 8. 缺陷判定表

| 现象 | 级别 | 判据 |
|---|---|---|
| 翻页出现重复/遗漏（含并发插入/删除） | S1 | 逐页 id 集合去重前后数量 + 并发前后对照 |
| 排序/筛选参数可注入并回显 SQL | S1 | 请求原文 + 500 响应含 SQL 片段 |
| A 会话列表出现 B 租户/他人数据，或 total 泄漏他人条数 | S1 | 双会话对照 + 响应体字段 |
| 改 cursor 可越权/枚举/拉全表 | S1 | 篡改前后响应 + 行数 |
| `total` 与逐页累加不一致 | S2 | 两值 + 复现请求 |
| 深页超时/线性变慢且无预算声明 | S2 | 页码-延迟曲线 |
| 非法 page/size/sort 返回 500 或静默回退 | S2 | 请求 + 响应码 |
| 空结果与错误混淆（404/500 表示无匹配） | S2 | 契约对照 |
| 大小写/重音/空值排序与宣称不符 | S3 | 对照表 |
| 无 `size` 上限 | S2 | `size=100000` 实际返回行数 |

## 9. 验证命令（零依赖优先）

```bash
# 1) 逐页遍历并找重复/遗漏（jq 可用时）
for p in $(seq 1 20); do curl -sS "https://host/api/items?page=$p&size=50" \
  | jq -r '.items[].id' >> ids.txt; done
sort ids.txt | uniq -d        # 重复 id
sort -u ids.txt | wc -l       # 去重数量 vs total

# 2) 排序注入（只读探测，勿打生产写接口）
curl -sS -o /tmp/r.txt -w '%{http_code}\n' \
  "https://host/api/items?sort=id%2C(select%201)&size=1"; cat /tmp/r.txt

# 3) 页边界
for q in 'page=0' 'page=-1' 'page=abc' 'size=0' 'size=100000'; do
  curl -sS -o /dev/null -w "$q -> %{http_code}\n" "https://host/api/items?$q"; done

# 4) 深页延迟
curl -sS -o /dev/null -w 'p1 %{time_total}\n' 'https://host/api/items?page=1&size=50'
curl -sS -o /dev/null -w 'p1000 %{time_total}\n' 'https://host/api/items?page=1000&size=50'
```

脚本：

```bash
python scripts/query-audit.py scan . --format markdown --fail-on-gap
python scripts/query-audit.py matrix --file pagination.json --format markdown --fail-on-gap
python scripts/query-audit.py cases
python scripts/query-audit.py --self-test
```

`matrix` 清单格式（每项最少字段）：

```json
{"pages":[{"page":1,"ids":["a","b"]},{"page":2,"ids":["b","c"]}],
 "expected_ids":["a","b","c","d"], "declared_total":4,
 "sort":{"whitelist":["created_at","id"],"accepted":["title"],"injection_status":200,"injection_body":"SELECT"},
 "page_size":{"max_accepted":100000}, "boundary":{"page_zero_status":200,"negative_status":500},
 "collation":{"mode":"ci","observed":["Ada","ada"]}, "leak":{"foreign_rows":1},
 "deep_page":{"page":1000,"p95_ms":4200}}
```

## 10. 报告证据写法（R-19 六项）

1. 分页契约表：模式 / 排序键 / tie-breaker / 空值与 collation / `size` 上限 / `total` 口径；
2. 遍历证据：页数、每页 id 数、去重前后数量、与全量查询集合的差异；
3. 并发对照：插入/删除发生页与受影响 id，前后两次遍历的差异；
4. 参数负向：`sort`/`page`/`size`/`q` 的非法值请求原文 + 响应码；
5. 权限对照：双会话/双租户的 `items` 与 `total`；
6. 性能：页码 → P95 曲线与 `EXPLAIN` 关键行（或明确「未做深页性能验证」）。

**不得**写：「翻了一遍没重复就是分页正确」「第 1 页快就是列表快」「`total` 显示 100 就是 100 条」「加了 `ORDER BY` 就稳定」「`cursor` 是 base64 就不透明」「A 看不到 B 的数据就是隔离通过」（A 看不到可能是 404 掩盖，另见 R-20）。

## 11. 项目形态 → 证据

| 形态 | 必做 | 证据 |
|---|---|---|
| REST collection | offset/keyset 稳定性 + 边界参数 | 逐页 id + 状态码矩阵 |
| GraphQL connection | `first/after` 语义、`pageInfo` 一致性 | 两页 edges + `hasNextPage` |
| 后台管理表格 | 行级权限 + 深分页 | 双角色 items/total + 深页延迟 |
| 无限滚动 feed | 并发插入漂移 | 滚到第 N 屏的新旧对照 |
| 搜索页 | 空结果语义 + 通配符转义 + 高亮转义 | `q` 矩阵 + 响应原文 |
| 多租户 SaaS | 查询层过滤 + 越权 cursor | 双租户 + 旧 cursor 降权对照 |

## 12. 来源

- PostgreSQL `LIMIT`/`OFFSET` 与「无 ORDER BY 时顺序未定义」：https://www.postgresql.org/docs/current/queries-limit.html
- ISO SQL:2023 对 `OFFSET` 的语义（Winand 引文）与 keyset/seek：https://use-the-index-luke.com/no-offset
- 深分页与索引（分页查询执行计划）：https://use-the-index-luke.com/sql/partial-results/fetch-next-page
- RFC 8288 Web Linking（`Link: rel="next"`）：https://www.rfc-editor.org/rfc/rfc8288.html
- GraphQL Relay Cursor Connections（`edges/pageInfo`）：https://relay.dev/graphql/connections.htm
- OWASP SQL Injection Prevention（`ORDER BY` 白名单与参数化边界）：https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- MySQL collation（`utf8mb4_0900_ai_ci` 大小写/重音不敏感）：https://dev.mysql.com/doc/refman/8.4/en/charset-collation-names.html
- PostgreSQL collation 与 ICU：https://www.postgresql.org/docs/current/collation.html
- Unicode TR10（土耳其 i / 德语 ß 的大小写特例）：https://www.unicode.org/reports/tr10/
