# 并发与幂等正确性（R-23）

一句话：**串行重放通过 ≠ 并发正确，幂等键存在 ≠ 幂等生效**——单线程把同一个请求回放十次都通过，只证明「当时没有并发」；请求头里有 `Idempotency-Key`、代码里也有 `if key in cache: return`，都不证明重放时副作用只发生了一次。并发正确性只有在**同一瞬间有 N 个请求真的在抢同一行、同一把锁、同一个键**时才被检验。

适用：任何有写路径的系统——下单与支付、钱包/积分/额度扣减、库存预占、优惠券与一人一单、消息消费、批量导入、定时任务重跑、Serverless 重试。
配套：`assets/idempotency-concurrency-matrix-template.md`（证据矩阵）、`scripts/concurrency-audit.py`（`scan` / `cases` / `side-effects`）。
相关规则：R-15（重复扣款 / 超卖）、R-16（`event_id` 并发去重）、R-19（翻页期间并发插入）、R-11（并发造数）。交叉点：**超卖是 R-15 的账务面在 R-23 的并发面被引爆；`event_id` 去重表缺唯一约束 = R-16 的「不重复」在并发下塌成 CC-01；翻页期间并发插入既算 R-19 的重复行也算 R-23 的隔离级别问题；没有可复现的并发夹具，R-11 的造数能力决定这一条能否被测**。

## 0. 触发条件与不适用

| 场景 | 是否触发 | 说明 |
|---|---|---|
| 写路径含扣减（库存 / 余额 / 额度 / 配额） | ✅ 必做 | 必须真并发打到同一行，**不得**用串行重放代替；判定「库存 ≥ 0」与「Σ扣减 ≤ 入库」 |
| 支付 / 退款 / 转账 / 代金券核销 | ✅ 必做 | 同时并入 R-15；必须验证同一幂等键的副作用次数为 1，**不得**只看「第二次也返回 200」 |
| 宣称「幂等」「可重试」「不重复」的 API | ✅ 必做 | 键的生成方、作用域、保留期、异体语义逐条核，**不得**把「键存在」当「幂等生效」 |
| 唯一性业务约束（单号 / 手机号 / 邮箱 / 一人一单） | ✅ 必做 | 必须并发插入同一值看错误码，**不得**只测串行插入的第二个请求 |
| 消息 / 队列 / Webhook 消费 | ✅ 必做 | 至少在业务侧注入重复投递；并入 R-16，**不得**把「先 ack 后处理」当可靠消费 |
| 定时任务 / 批处理（cron、xxl-job、Lambda 定时） | ✅ 必做 | 多实例同时触发或重跑昨天，**不得**假设调度器不会重叠 |
| 纯只读查询服务（无任何写入） | ❌ 不适用 | 只写「不适用：无写路径与并发写语义」，**不得**写「并发安全」 |
| 单用户本地 CLI、无共享状态 | ❌ 不适用 | 无并发写者；**不得**写「并发正确」 |
| 只有单元测试与内存 SQLite、无真实数据库 | ◐ 降级 | SQLite 的写锁语义与 PG/MySQL 不同；**不得**把 SQLite 结论当生产结论 |
| 压测只统计「无 5xx」、无业务对账 | ◐ 降级 | 200 也可能重复扣款；**不得**写「无超卖 / 无重复」 |

## 1. 先问 8 个契约问题

1. **幂等键谁生成、放在哪**：客户端 UUID / 网关注入 / 服务端按业务键派生；位置是 header（`Idempotency-Key`）、body 字段还是 query。答案决定**重放时变的是什么**：header 同体同 / body 同键异体的检测点完全不同。
2. **服务端是否持久化键、存多久**：Redis TTL、DB 去重表还是根本没落库；保留期多久（Stripe 口径 24h）。答案决定**键过期后重放**这条用例是必测还是不存在。
3. **同键同体 / 同键异体的返回语义**：回放首次结果（200 + 原 body）、`409 Conflict`、还是 `422 Unprocessable`。答案决定**判据是「同一 resource_id」还是「状态码」**，也决定能否用幂等键做审计。
4. **键的作用域**：全局唯一、按用户、按租户、按 (用户, 端点)。答案决定**跨用户/跨租户复用键**这条负向能不能构造，以及「A 的键回放给 B」是否越权。
5. **写路径的事务隔离级别与锁类型**：READ COMMITTED / REPEATABLE READ / SERIALIZABLE；行锁、间隙锁、表锁；乐观版本号还是悲观 `FOR UPDATE`。答案决定**可以制造哪种竞态**，也决定「先查后写」是否天然不安全。
6. **扣减语义**：`UPDATE … SET stock = stock - n WHERE stock >= n` 并检查 `rowcount`、悲观锁、版本号 CAS、还是应用层读-改-写。答案决定**默认该怀疑哪条反模式**（对应 CC-02 / CC-05 / CC-07）。
7. **超时/失败后客户端是否重发、重发几次**：SDK 自动重试、网关重试、前端连点。答案决定**并发度 N 与重试次数**，是「双提交」用例的输入。
8. **是否多实例 / 多消费者 / 多分区**：K8s 多副本、消费者组并发数、消息分区键。答案决定**锁是否只在单进程内有效**，以及重复消费是必然还是偶然。

> 八问答不出来就先别写「幂等已做」——此时连「重放」指的是哪一层都没定义。

## 2. 不变量清单（先写清「什么必须永远成立」）

| 不变量 | 违反的具体形态 | 观测方式 |
|---|---|---|
| 余额 == Σ流水（含期初） | 并发两笔各 -10，终值只减了 10 | 对账 SQL：`balance` 与 `SUM(ledger.amount)` 差额必须为 0 |
| 库存 ≥ 0 且 Σ扣减 ≤ 入库 | 并发 20 单卖出 25 件，`stock = -5` | `SELECT MIN(stock)` 与 `SUM(出库) - SUM(入库)` 双查 |
| 一个幂等键 → 恰好一个资源 | 同键两次得到 `res_1` 与 `res_2` | 按 `key` 聚合 `resource_id` 去重数 > 1 即违反 |
| 单号 / 邮箱 / (用户,活动) 唯一 | 并发插入同一邮箱得到两行、或第二条 500 | `GROUP BY email HAVING COUNT(*) > 1`；错误码应为 409 而非 500 |
| 每用户只领一次 | 并发领券后 `user_id` 出现两条 | `GROUP BY user_id, campaign_id HAVING COUNT(*) > 1` |
| 同一 `event_id` 副作用恰好一次 | 重复投递扣了两次积分 | 消费者侧按 `event_id` 统计副作用行数，必须 == 1 |
| 账本借贷平衡 Σ借 == Σ贷（R-15） | 并发补偿只补一边 | 复式分录按 `txn_id` 聚合借贷差 == 0 |

每条不变量都要在报告里给出**期望值、实测值、差额**三个数字；只写「符合」不算证据。

## 3. 三种并发，只有一种算数

- **串行重放**（先 request 1 完成，再 request 2）：只能证明「重复请求不会在无并发时出错」，连一次真正的竞态窗口都没打开；`幂等键存在` 的结论通常就死在这一步。
- **「假并发」**：`for await (const r of reqs) await fetch(r)` 顺序执行；或先 `sleep(100ms)` 再发第二个请求「造窗口」。前者根本没并发；后者是**在你指定的时刻**插入，而真实竞态发生在你控制不了的调度点上，绿了也不能说明什么——**假并发测出来的绿是装饰**。
- **真并发**（唯一算数）：让 N 个执行体在屏障上同时释放，打到同一行/同一键。四种手段：前端/Node `Promise.all([...N])`；Python `threading.Barrier(N)` / `ThreadPoolExecutor(N)`；Shell `seq N | xargs -P N -I{} curl …`（`-P` 是并发度）；k6 `constant-arrival-rate`（按到达率而非 VU 数）。

判定要点：**并发度 N ≥ 10**（写路径建议 20~50）、**同一时间窗**（先做一次 5s 预热单发确认链路通，再并发）、**每个执行体独立连接**（连接池复用可能把请求串行化，反而测不出问题）。报告必须写 N、客户端线程/进程数、以及「是否为同一进程内并发」。

## 4. 幂等键矩阵

| 维度 | 构造方式 | 期望结果 | 判据 |
|---|---|---|---|
| 同键同体 | 同一 `Idempotency-Key` + 完全相同的 body，并发 2~N 次 | 全部成功且指向同一资源；或 1 次 2xx + 其余回放同一响应 | `COUNT(DISTINCT resource_id) == 1` 且副作用次数 == 1 |
| 同键异体 | 同键，body 改数量/金额/商品 | 拒绝：`409`（键已用于其他请求）或 `422`；**不得**按新 body 执行 | 资源数仍为 1，且首次结果未被改写；响应体不泄漏首次请求的业务数据 |
| 不同键同体 | 两个不同键，相同 body，并发 | 两条独立业务（若允许）或由业务唯一约束拒绝；**不得**静默产生两条扣款 | 资源数 == 期望业务数；余额差额 == 2×金额 或 1×金额（有唯一约束时） |
| 键过期后重放 | 等过 TTL（或手动删键）再重发 | 重复执行并产生第二个资源（这是**已知语义**，须写入契约）或由业务唯一约束拦住 | 若宣称「永久幂等」而键只存 1h，判 CC-25 |
| 键跨用户/跨租户复用 | A 的键被 B 拿来回放 | 拒绝（404/409）或视为不同键；**不得**回放 A 的结果 | B 拿到的 `resource_id` 不得属于 A；响应不得含 A 的数据 |
| 键在 header vs body vs query | 同一逻辑键分别放三处，看服务端认哪个 | 只认一处并在文档写明；另两处忽略或拒绝 | 放错位置时不产生去重效果，须能复现「同键两次两个资源」 |
| 键的大小写与空白归一化 | `ABC-1` / `abc-1` / `" ABC-1 "` | 明确归一策略；若按原样存，三者视为不同键 | 归一后同键必须命中同一记录；不归一时须写明「大小写敏感」 |
| 客户端重试：键相同、trace 不同 | 同键 + 不同 `traceparent` / `X-Request-Id` 并发 3 次 | 仍只有一个资源；trace 只用于观测，不参与去重 | 去重键不得包含 trace/时间戳等易变字段（否则每次都是新键） |

矩阵里每一行都要有**实际响应码 + 实际副作用次数**；只写期望不写实测就是没测。

## 5. 运行时缺陷与判定

| 编号 | 现象 | 级别 | 判据 |
|---|---|---|---|
| CC-20 | lost update：并发两笔各 -10，终值只 -10 | HIGH | 终值 ≠ 期望终值，且 Σ流水 ≠ 终值；差额 == 丢失的那笔金额 |
| CC-21 | 超卖：卖出的比库存多 | HIGH | `MIN(stock) < 0` 或 `Σ扣减 > Σ入库`；并发度 N 下成功数 > 库存数 |
| CC-22 | 重复下单 / 重复扣款 | HIGH | 同一业务键产生 >1 个资源，或 `SUM(charge) > 应扣`；连点/重试场景必现 |
| CC-23 | 唯一插入竞争返回 500 | HIGH | 并发插同一唯一值时出现 5xx（应为 409 或幂等回放）；日志含唯一约束报错却映射成 500 |
| CC-24 | 幂等键命中仍二次副作用 | HIGH | 键命中路径已执行，但下游扣款/发货被再次触发（副作用数 > 1） |
| CC-25 | 键过期后重复执行 | MEDIUM | TTL 之后重放产生第二个资源，而契约宣称「永久幂等」 |
| CC-26 | 锁过期双持有 | HIGH | 业务执行时长 > 锁 TTL，两个执行体同时进入临界区（日志时间戳交叠） |
| CC-27 | 读已提交下幻读补偿错 | MEDIUM | 补偿任务按旧快照计算，多扣/少扣；重跑补偿后余额不归位 |
| CC-28 | 批处理重复消费 | HIGH | 同一 `event_id` / 同一批次被处理 >1 次；重跑后总数翻倍 |
| CC-29 | 并发下 `total` 与条数不符 | MEDIUM | 并发写入期间 `total` 与逐页遍历去重条数差 > 0（并入 R-19） |

`CC-2x` 是**运行时观测项**，不能靠读代码下结论；每条都要有并发用例的记录（N、成功数、失败数、证据路径）。

## 6. 锁与事务：各自能防什么、漏什么

- **悲观锁 `SELECT … FOR UPDATE`**：防住同一行的并发写；**漏在**：`WHERE` 走了非唯一索引或没有索引 → InnoDB 退化为大范围/表锁；行不存在时没有行可锁，"先查不存在再插入"依然两个请求都能通过（幻读面）→ 必须靠唯一约束兜底。
- **乐观锁（版本号 CAS）**：`UPDATE … SET v = v + 1, stock = stock - n WHERE id = ? AND version = ?`，检查 `rowcount == 1` 否则重试/409；**漏在**：`version` 没进 `WHERE`、或读完不校验影响行数——那就退化成 lost update。
- **原子 SQL 条件更新**：`UPDATE stock SET n = n - ? WHERE sku = ? AND n >= ?`，**必须检查 `rowcount`**；不检查就只是「语句跑了」，并不代表扣到了。这是最便宜也最容易漏的一处（CC-05）。
- **分布式锁**：一条原子命令 `SET key val NX PX 30000`，不是 `SETNX` + `EXPIRE` 两步（中间崩溃 = 死锁，两步之间也可能被插队，CC-03）；TTL 要短于业务上限并配续期；**锁过期后仍可能双持有**，写路径需要 **fencing token**（单调递增，存储侧拒绝旧 token 的写），否则锁只是「大概率的礼貌」。
- **`@Transactional`**：Spring 基于代理，同类内 `this.method()` / 私有方法自调用**不经过代理**，注解不生效（CC-04）；方法抛的异常类型不在 `rollbackFor` 里也不回滚。
- **「先查后写」在事务外**：`if (!exists) insert` 跨两个事务，隔离级别再高也挡不住另一个事务的提交；唯一约束是唯一可靠的最终防线。

每条都要能回答「怎么测出来」：`FOR UPDATE` 用两个连接同时 SELECT 验证阻塞；乐观锁用同 `version` 并发两次看第二次 `rowcount == 0`；原子更新用 `rowcount` 断言；分布式锁用注册表/日志时间戳证明临界区交叠；`@Transactional` 用一个中途抛异常的自调用方法看是否落库。

## 7. 数据层证据（可复核的硬证据）

- **唯一约束与错误码映射**：`UNIQUE (order_no)` / `UNIQUE (user_id, campaign_id)` 必须真实存在于 DDL，并验证违反时映射为 `409`，而不是 500（CC-23）。`INSERT … ON CONFLICT DO NOTHING` / `INSERT IGNORE` 之后要看 `rowcount`，静默 0 行等同「没插进去」。
- **`version` 列**：存在、被 `WHERE` 引用、每次写 +1；缺一不可。
- **`rowcount` / `affected_rows`**：条件更新后必须断言 == 1；这是区分「执行成功」与「业务成功」的唯一证据。
- **序列 / 自增 / 单号**：并发下不得重号；`nextval` 与「序列 + 业务前缀」的组合要验证重启后不重用。
- **outbox / 去重表**：`event_id` 去重表要有唯一约束，写入与业务同事务（outbox），消费侧 `ON CONFLICT DO NOTHING` + `rowcount` 判定是否首次；锁视图（MySQL `SHOW ENGINE INNODB STATUS` 的 `LOCK WAIT`、PG 的 `pg_locks`）跑完留档，证明「确实在抢同一行」。

**数据库约束是最后一道防线，应用层去重是性能手段**——反过来（只靠应用层 `if exists`）在并发下必然漏；只靠数据库约束则会把冲突暴露成 500，两者都要。

## 8. 观测与回归

- **冲突计数**：`409` / `423` / 唯一约束错误码的次数必须单独计数，不能混进 5xx 错误率（否则「冲突」会被当成「故障」）。
- **锁等待与重试**：锁等待 p95、重试次数分布；重试放大（一次失败触发 N 次重放）并入 R-16 / SRE 的重试放大面。
- **延迟分位**：并发下 p95/p99；只报平均值会掩盖「部分请求卡在锁上 3s」。
- **业务对账指标与回归门槛（建议值）**：库存差额、资源数 − 期望数、副作用次数 − 1 三类必须进门槛——超卖数 **> 0 阻塞**；同一键副作用次数 **> 1 阻塞**；唯一冲突映射为 5xx **> 0 阻塞**；`total` 与遍历条数差 **> 0 阻塞**；p95 相比串行基线退化 **> 20%** 告警。

## 9. 静态扫描规则 CC-01 ~ CC-10

| 编号 | 反模式 | 为什么错 | 判据（可被 grep 识别） |
|---|---|---|---|
| CC-01 | 无唯一约束的先查后插（`if exists … else insert`） | 两个事务同时「查不到」，都插入成功，产生重复业务对象 | 出现存在性查询（`SELECT … FROM` / `.first(` / `.exists(` / `.count(`）后再 `INSERT INTO` / `.create(` / `.save(` / `.add(`，且全文件无 `unique` / `UNIQUE` / `UniqueConstraint` / `@unique` / `uniq_` |
| CC-02 | 应用层读改写余额（`acct.balance = acct.balance - n; save()`） | 后写覆盖先写，lost update | `(\w+)\.(\w+) = \1\.\2 - …`（自减自赋值）或 `balance\|stock\|amount\|count\|points\|quota = 自身 - …`，或 `SET <列> = ?`（值由应用算好）；`SET stock = stock - ?` 这类原子 SQL 例外放行 |
| CC-03 | `SETNX` 后再 `EXPIRE` 两步加锁 | 两步之间崩溃则死锁，或并发窗口内被插队 | 同一文件既有 `expire(` / `pexpire` 又有 `setnx` / `set_nx` / `setIfAbsent` / `SET … NX`，且全文件无 `ex=` / `px=` 数字（单条 `SET … NX EX 60` 不报） |
| CC-04 | `@Transactional` 同类自调用 / 私有方法调用 | 代理被绕过，注解不生效，异常不回滚 | 文件含 `@Transactional` 且出现 `self.xxx(` / `this.xxx(` |
| CC-05 | 扣库存无 `WHERE stock >= n` 守卫、不查 `rowcount` | 库存被扣成负数；语句跑了但没扣到 | `stock = stock -` 且同行无 `>=` 守卫、全文件无 `rowcount` |
| CC-06 | 幂等键只比对不落库 | 每个请求都「首次」，重放照样执行 | 出现 `idempotency_key` / `idem_key` / `Idempotency-Key` 并做 `==` / `!=` 比较，且全文件无「插入/更新该键」的语句 |
| CC-07 | `SELECT` 后 `UPDATE` 无锁（无 `FOR UPDATE`、无版本号） | 查询与更新之间被插队，读到的值已过期 | 全文件无 `FOR UPDATE` / `select_for_update` / `lock=True` / `version`，且 `UPDATE <表> SET` 出现在 `SELECT` 之后 |
| CC-08 | 分布式锁无 fencing / 无 token 校验 | 锁过期后旧持有者继续写，覆盖新持有者 | 出现 `setnx` / `redlock` / `redislock` / `zookeeper` / `etcd` / `SET … NX` / `acquire_lock` / `acquire(`，且全文件无 `fence` / `fencing` |
| CC-09 | `get_or_create` / `findOrCreate` 无竞态兜底 | 两个请求同时 create，第二个撞唯一约束抛异常 | 出现 `get_or_create` / `getOrCreate` / `get_or_insert` / `first_or_create`，且全文件无 `IntegrityError` / `DuplicateKey` / `UNIQUE` 兜底 |
| CC-10 | 队列消费者先 `ack` 后处理 | 处理失败消息已确认，业务丢失；重投又被 ack 掉 | 同文件 `ack(` / `basic_ack` / `acknowledge(` / `commit_message` / `offset_commit` 出现在 `def process\|handle\|consume` / `.process(` / `handle_message` / `.handle(` 之前；或 `auto_ack=True` |

`scan` 命中是**需人工确认的线索**，不是漏洞定论：例如 CC-08 在单实例内存锁场景可能是误报，CC-04 在非 Spring 环境不适用。

## 10. 验证命令

```bash
# 1) 静态线索（默认 markdown；--fail-on-gap 时存在 HIGH 即退出码 1）
python scripts/concurrency-audit.py scan . --format markdown
python scripts/concurrency-audit.py scan . --format json --fail-on-gap

# 2) 8 个标准并发场景的可填写矩阵（贴进报告用）
python scripts/concurrency-audit.py cases

# 3) 幂等键副作用对账（读 JSONL，按 key 聚合）
python scripts/concurrency-audit.py side-effects --events events.jsonl \
  --format markdown --fail-on-gap

# 4) 自检：夹具能命中规则、重复键能触发 duplicate_side_effect
python scripts/concurrency-audit.py --self-test
```

输入契约（UTF-8 JSONL，每行一个事件；空行与 `#` 注释行忽略，坏行跳过并计数）：

```jsonl
{"key":"ord-1","attempt":1,"status":201,"resource_id":"res-9","side_effects":1,"ts":"2026-11-18T10:00:00Z"}
{"key":"ord-1","attempt":2,"status":201,"resource_id":"res-9","side_effects":1,"ts":"2026-11-18T10:00:00.120Z"}
{"key":"ord-2","attempt":1,"status":201,"resource_id":"res-10","side_effects":1,"ts":"2026-11-18T10:00:01Z"}
{"key":"ord-2","attempt":2,"status":201,"resource_id":"res-11","side_effects":1,"ts":"2026-11-18T10:00:01.080Z"}
```

输出契约：每个键给 `attempts`、`distinct_resource_ids`、`max_side_effects`、`total_side_effects`、`duplicate_side_effect`（总副作用 > 1）、`multi_resource`（资源去重数 > 1）与判定；汇总给键数、总事件数、违规键数、坏行数。退出码：**0 = 无缺口；1 = 有缺口且带 `--fail-on-gap`；2 = 输入不可读/参数错误**。脚本默认只报告，不带 `--fail-on-gap` 不会因缺口失败——这一点必须在报告里写明，否则「跑过了」会被误读成「通过了」。

手动真并发（最小可跑，需按实际路由改 URL）：

```python
# Python：20 个线程卡在同一个 Barrier 上，同时打同一端点（同一幂等键）
import json, threading, urllib.request
N, KEY, URL = 20, "k-1", "http://127.0.0.1:8000/orders"
barrier, results = threading.Barrier(N), []
def fire() -> None:
    body = json.dumps({"sku": "A1", "qty": 1}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Content-Type": "application/json", "Idempotency-Key": KEY})
    barrier.wait()                  # 所有线程在此对齐，一起放行
    with urllib.request.urlopen(req, timeout=15) as r:
        results.append((r.status, r.read().decode()))
threads = [threading.Thread(target=fire) for _ in range(N)]
[t.start() for t in threads]
[t.join() for t in threads]
print(len(results), sorted({s for s, _ in results}))
```

```bash
# curl × N 并行（同键并发；git-bash / WSL 可直接跑）
seq 10 | xargs -P 10 -I{} curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST http://127.0.0.1:8000/orders -H "Content-Type: application/json" \
  -H "Idempotency-Key: k-1" -d '{"sku":"A1","qty":1}'
# PowerShell 7 等价：1..10 | ForEach-Object -Parallel { curl.exe … } -ThrottleLimit 10
```

## 11. 报告证据写法（R-23 八项）

1. **契约清单**：§1 八问的答案原文（键位置、保留期、异体语义、隔离级别、扣减语义、重试策略、实例数），缺哪条写「未确认」。
2. **并发夹具**：N、执行体数量、屏障实现、是否同进程、请求原文（含 `Idempotency-Key` 与 trace），以及为什么它是真并发。
3. **不变量对账**：每条不变量的期望值、实测值、差额，附对账 SQL 原文与执行时间。
4. **幂等键矩阵**：§4 每行的实际响应码、实际 `resource_id`、实际副作用次数；至少一行「同键异体」与一行「跨用户复用」的负向。
5. **`side-effects` 输出原文**：命令 + 退出码 + 逐键表；重复键的关键行（`duplicate_side_effect=true` / `multi_resource=true`）必须原样贴。
6. **锁与事务证据**：`rowcount` 断言、`version` 递增、`pg_locks` / `INNODB STATUS` 的锁等待片段、分布式锁临界区时间戳交叠（或 fencing token 拒绝旧写的日志）。
7. **`scan` 命中逐条裁决**：每条命中写「真缺陷 / 误报（原因） / 不适用（原因）」，不得只贴数量。
8. **回归对照**：串行基线 vs 真并发的成功数、错误率、p95、冲突计数；未做写「未做并发基线对照」并降级。

**不得**写：「代码里有锁」≠「并发安全」、「串行重放通过」≠「并发幂等」、「压测没报错」≠「无超卖」、「幂等键存在」≠「幂等生效」、「事务注解存在」≠「事务生效」、「日志里没有重复」≠「正好一次」、「唯一约束在」≠「冲突已映射为 409」、「第二次返回 200」≠「副作用只发生一次」。

## 12. 项目形态 → 证据

| 形态 | 必做 | 可降级 |
|---|---|---|
| 单体 Web + 关系库 | 真并发打同一行 + `rowcount` 断言 + 唯一约束错误码 + 锁视图 | 无多实例时可降级「分布式锁」一项，但须写明单实例 |
| 微服务 + 消息队列 | 重复投递注入 + 去重表唯一约束 + 先 ack 后处理检查 + outbox 一致性 | 无消息中间件沙箱时只做静态 + 本地重放，写明未做端到端 |
| Serverless / 无状态 API | 幂等键持久化（外部存储）+ 重试放大 + 冷启动并发 | 无平台重试注入能力时用客户端并发代替，写明差异 |
| 纯只读查询服务 | 无写路径 → 只写「不适用：无并发写语义」，可并入 R-19 的并发插入面 | 不适用本身即结论，不得省略 |
| CLI / 批处理 | 多实例同时跑 + 重跑昨天 + 断点续跑不重复 | 单机单实例可降级，写明未验证多实例 |
| 无 DB 的内存服务 | 进程内锁 + 单实例假设 + 重启后状态丢失对幂等的影响 | 无持久化即无法保证跨重启幂等，必须写明 |

## 13. 来源

- [PostgreSQL：Transaction Isolation（READ COMMITTED 的非重复读与幻读语义）](https://www.postgresql.org/docs/current/transaction-iso.html) → 蒸馏到 §1.5 隔离级别问法与 §6「先查后写」失效面
- [PostgreSQL：SELECT（`FOR UPDATE` / `FOR NO KEY UPDATE` 锁定行为）](https://www.postgresql.org/docs/current/sql-select.html) → 蒸馏到 §6 悲观锁「行不存在时锁不住」的漏洞
- [PostgreSQL：Constraints（UNIQUE 与唯一索引是最终防线）](https://www.postgresql.org/docs/current/ddl-constraints.html) → 蒸馏到 §7 唯一约束 + 错误码映射
- [MySQL 8.0 Reference：Locking Reads（`SELECT … FOR UPDATE` 与间隙锁）](https://dev.mysql.com/doc/refman/8.0/en/innodb-locking-reads.html) → 蒸馏到 §6 范围锁 / 索引缺失升级为表锁
- [Stripe：Idempotent requests（键保留 24h、同键异体报错、回放首次结果）](https://docs.stripe.com/api/idempotent_requests) → 蒸馏到 §1.2/§1.3 与 §4 幂等键矩阵
- [IETF：The Idempotency-Key HTTP Header Field（draft-ietf-httpapi-idempotency-key-header）](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/) → 蒸馏到 §4 键作用域、指纹与冲突语义
- [RFC 9110 §9.2.2：Idempotent Methods（幂等方法与可重试性）](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2) → 蒸馏到 §4「POST 默认不幂等」与重试前提
- [Jepsen：Consistency Models（并发历史与异常分类）](https://jepsen.io/consistency) → 蒸馏到 §2 不变量与 §5 的 lost update / 幻读判定
- [AWS Builders' Library：Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) → 蒸馏到 §1.7 客户端重试、§4 同键同体不同 trace 与 §8 重试放大的计数口径
