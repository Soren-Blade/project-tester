# Webhook / 异步消息交付可靠性测试（R-16）

> 一句话：Webhook 是**至少一次（at-least-once）**投递，不是「发一次就到一次」；测的是「重复会不会重复生效、丢失能不能发现、乱序会不会做错事、失败能不能补偿」。
> 适用：支付/退款回调、订阅续费、发货通知、第三方事件订阅、消息队列消费者、Cron 触发的异步任务。
> 配套：`assets/webhook-delivery-matrix-template.md`、`scripts/webhook-audit.py`、`references/api-testing.md`、`references/chaos-resilience.md`、`references/observability-testing.md`。
> 相关规则：R-16 本手册；R-2 韧性（重试/超时/熔断）、R-12 身份与会话（签名密钥）、R-15 金额（重复扣款）、R-9 证据链（事件号可追溯）。

## 0. 触发条件与不适用

| 触发条件（命中任一即必须做 R-16） | 不适用写法（必须写清理由） |
|---|---|
| 接收第三方 webhook（支付、物流、IM、CI） | 纯同步请求-响应，无异步事件 → 「不适用：无异步交付」 |
| 对外发送 webhook / 事件订阅 | 只读静态数据，无事件 → 「不适用：无事件流」 |
| 使用 MQ（Kafka/RabbitMQ/SQS）消费业务事件 | 本地单进程内存队列且**明确不跨重启** → 「不适用：无持久化交付语义」 |
| 有重试、DLQ、补偿任务 | 事件只用于日志/统计，重复无副作用 → 可降级，但须写「重复无副作用」证据 |
| 支付/退款/发货等有副作用的消费者 | — |

> 只要消费者会「扣钱、发货、改状态、发通知」，就**不得**以「webhook 很成熟」为由跳过 R-16。

## 1. 先分清三种语义

| 语义 | 含义 | 现实 |
|---|---|---|
| at-most-once | 最多一次，可能丢 | 很少用于钱 |
| at-least-once | 至少一次，可能重 | **绝大多数 webhook / MQ 的默认** |
| exactly-once | 恰好一次 | 端到端不存在；只能靠**幂等 + 去重**做到「效果上一次」 |

> 测试立场：默认按 at-least-once 设计用例——**重复是正常现象，不是异常**；系统必须对重复免疫。

有据可依的例子（写进证据时引用具体语义，别笼统说「MQ 保证不丢」）：SQS Standard 明说 **at-least-once 且可能乱序**；SQS FIFO 去重窗口 **5 分钟**、同一 message group 内严格有序；Kafka 开启幂等生产者后**单 partition 恰好一份**、顺序只保证 partition 内；CloudEvents 核心规范**不承诺**投递保证，只规定 `source + id` 唯一、消费者可据此去重。

## 2. 签名与鉴权（先过这道门）

### 2.1 三种主流方案（务必按实际方案测）

| 方案 | 覆盖内容 | 头部 | 算法 |
|---|---|---|---|
| Standard Webhooks | `${webhook-id}.${webhook-timestamp}.${raw body}` | `webhook-id`、`webhook-timestamp`、`webhook-signature: v1,<base64>`（多签名空格分隔） | HMAC-SHA256，密钥为 `whsec_` 后 base64 解码的字节 |
| Stripe | `${t}.${raw body}` | `Stripe-Signature: t=…,v1=<hex>` | HMAC-SHA256，密钥为 `whsec_…` 字符串本身（不 base64 解码） |
| GitHub | raw body | `X-Hub-Signature-256: sha256=<hex>`；`X-GitHub-Delivery` 做去重 | HMAC-SHA256，无时间戳 → 重放靠 delivery id 去重 |

> 两个坑：① **必须用原始 body 字节验签**，不能先 JSON 解析再序列化（字段顺序/空格/转义都会变）；② `whsec_` 前缀在 Standard Webhooks 与 Stripe 下的处理不同，照抄示例会全部验签失败。

### 2.2 必测

- 正常签名 → 200，且**验签在业务处理之前**；
- body 改 1 字节 → 拒绝（401/400），业务零副作用；
- 用旧消息的签名配新 body → 拒绝（签名覆盖 id/timestamp/body）；
- 重放 10 分钟前的合法请求 → 超容忍窗拒绝（**Standard Webhooks 规范只要求校验时间戳在「可接受容差」内，未给具体秒数**；±5 分钟是常见实现约定，Stripe 官方库默认 300 秒且明确说不要设 0 —— 一律以被测实现的实际配置为准并在证据里写清数值）；窗内重放由幂等兜住；
- **容差边界三值必测**：`now-301s`、`now-299s`、`now+301s`（未来时间戳同样要拒），记录实际判定结果；只知道「配了 300 秒」不够，要证明窗口真的生效；
- **timestamp 必须进签名**：保持 body 与签名不变、只把 `webhook-timestamp`/`t` 改大（如 9999999999），旧签名必须 401——只签 body 的实现会放行，属 S1；
- 缺头/空签名/未知版本（`v2,`）→ 拒绝，日志可定位；
- 密钥轮换期：新旧密钥并行验签（多签名头/多密钥配置）不误杀；
- 验签失败不得 500、不得把内部堆栈/密钥回显。

工具：`python scripts/webhook-audit.py verify --scheme standard|stripe ...` 可对样例复算签名（只证明「给定 payload+secret 能复算出该签名」，不证明密钥真实）。

## 3. 幂等与去重（决定会不会重复扣款）

- **幂等键选谁**：渠道事件 id（`event_id` / `X-GitHub-Delivery`）优先；没有就用业务唯一键（订单号 + 事件类型 + 版本）。
- **存哪**：持久化去重表/唯一索引，**不能**放进程内 Map（重启/多副本失效）。
- **保留多久**：≥ 渠道最大重试跨度（Stripe 重试可跨 3 天；以渠道文档为准），否则过期后重放会二次生效。
- **先占位再处理**：唯一键插入成功才处理；插入冲突 → 直接返回 2xx（视为已处理），不重复执行。
- **并发**：同 event_id 10 并发只能生效 1 次；靠数据库唯一约束/行锁，不靠「先查再写」。
- **业务幂等**：即便去重表漏了，核心操作也要幂等（`UPDATE balance = balance - ? WHERE balance >= ?`、状态机 CAS）。

必测：连发 5 次、并发 10 次、处理中崩溃后重投、去重键过期后重放（记录风险）。

## 4. 重试、退避与超时

- 渠道侧：`5xx`/超时 → 重试；`4xx` 通常**不重试**（除非 429）。要实测「4xx 是否被盲目重试」。
- 退避：指数 + 抖动（jitter），间隔必须递增；固定 1s 重试会打爆下游（`webhook-audit.py` WH-06）。
- 超时：消费者必须在渠道超时前回 2xx。做法是**先持久化（或入队）再回 2xx**，重活异步做；不要在请求线程里跑长事务。
- 重启：待重试消息要持久化，进程重启后继续；不能只存内存。
- 上限：达到最大次数 → 进 DLQ + 告警，**不得静默丢弃**；实测「attempt 计数真的递增、nextRetryAt 真的存在、最终失败真的出现在 DLQ」，只看到配置里有 `maxRetries` 不算证据（`dropped: no retry configured` 这类日志就是反例）。
- **handler 原子性**：处理中途抛错必须零残留（事务回滚/补偿/先入队后处理）；否则渠道重投会与残留叠加成双份副作用。必测「第 N 步失败 → 无半条数据 → 重投（replay）后总副作用仍为 1」。
- 顺序与重试的关系：重试会加剧乱序；消费者不能假设「先到先处理」。

## 5. 顺序与状态机

- 渠道通常**不保证**跨事件顺序；同一聚合根（订单）的事件可能乱序到达。
- 用**序号/版本号**（`sequence`、`created_at`、`version`）做裁决：旧版本事件到达时，要么丢弃，要么补偿，不能把状态改回去。
- 状态机必须拒绝非法倒退：已支付 → 待支付、已发货 → 未支付、已退款 → 再退款（超额）。
- 乱序且无序号可用时，用**主动查询**兜底（收到事件后回查渠道当前状态），而不是相信事件顺序。
- **前置事件缺失**：收到 `refund` 但本地没有对应 `capture`/`payment` → 必须挂起等待或拒绝，**不得凭空创建**支付/退款对象（`webhook-audit.py` WH-01 同类）；挂起的要在前置事件到达后补放且仅一次。
- 必测：created→paid→shipped 三轮乱序排列组合，业务终态一致；重复事件不改变终态。

## 6. 丢失、DLQ 与对账

webhook 会丢：消费者挂了、网络断、渠道放弃重试。必须能**发现**并**补偿**：

- 每条事件有 `event_id`、attempt、耗时、结果日志，可按 event_id 串起全链路（trace）。
- 指标：接收数、成功数、失败数、重试数、DLQ 深度、处理延迟分位数；失败率/积压有告警阈值。
- DLQ：可查看、可重放、重放幂等；重放要有操作审计。
- **对账**：渠道侧事件数/金额 vs 本地生效数/金额，差异分类（重复/丢失/过滤/金额差），不能只抽样。
- 主动补偿：定时任务扫描「已支付未发货」「已退款未入账」等中间态，按业务 SLA 修复。
- 事务性发件箱（outbox）：本地事务写业务表 + outbox 表，再由投递器发送，避免「业务成功、事件丢失」。

## 7. 缺陷判定与严重级

| 现象 | 级别 | 判据 |
|---|---|---|
| 重复事件导致重复扣款/重复发货 | S1 | 可复现的二次副作用 |
| 验签缺失/可绕过/用解析后 JSON 验签 | S1 | 可伪造事件 |
| 无时间戳或容忍窗无限大 | S1 | 可无限重放 |
| 消费成功但回 4xx/5xx（假失败） | S2 | 渠道无限重试，放大副作用 |
| 回 2xx 但业务未落库（假成功） | S1 | 静默丢失，对账才发现 |
| 最终失败不进 DLQ 无告警 | S2 | 无法补偿 |
| 重试无退避/固定间隔 | S2 | 下游雪崩风险 |
| 乱序导致状态倒退 | S2 | 业务错乱，可补偿则降级 |
| 去重窗口 < 渠道重试跨度 | S2 | 过期重放二次生效 |
| 日志缺 event_id | S3 | 排障困难 |

## 8. 工具：scripts/webhook-audit.py（零依赖）

```bash
python scripts/webhook-audit.py check --file deliveries.json            # 审计交付日志 WH-01~WH-11
python scripts/webhook-audit.py check --file deliveries.json --fail-on-gap
python scripts/webhook-audit.py verify --scheme standard --id msg_1 --timestamp 1700000000 \
    --payload-file body.json --secret whsec_xxx --signature 'v1,...'
python scripts/webhook-audit.py --self-test
```

- `check` 读交付日志做规则审计（无签名、签名未覆盖 id/timestamp、超窗、重复处理、无退避、静默丢弃、假成功、乱序、未进 DLQ）；**日志自洽不证明真实渠道行为**。
- `verify` 复算签名，支持 Standard Webhooks 与 Stripe 两种方案；**不证明密钥真实、不证明业务幂等**。
- 脚本**不联网、不代填**；结论必须由实测与渠道侧记录支撑。

## 9. 报告与证据写法

- 每条结论附：请求头原文、原始 body（脱敏）、签名复算结果、HTTP 状态、业务副作用查询（DB 行数/余额变化）、渠道侧事件记录。
- 重复类缺陷必须给「同一 event_id 的处理次数」与「副作用次数」两个数字。
- 没有渠道沙箱/真实回调时，R-16 只能写「部分覆盖」，盲区表写清「签名与重试策略来自文档推断」。

## 10. 项目形态 → R-16 证据

| 项目形态 | 最小必测集 | 证据 |
|---|---|---|
| 支付回调 | D-01~D-07、D-15、D-20 | 验签日志、去重表、扣款次数、渠道事件列表 |
| 对外事件订阅 | D-09~D-12、D-17、D-18 | 重试时间线、DLQ 记录、投递日志 |
| MQ 消费者 | D-06、D-07、D-11、D-13 | 重复消费计数、重启后续消费、乱序终态 |
| 定时任务触发 | D-09、D-11、D-16 | 执行记录、失败重跑、漏跑发现 |
| 纯通知类 | D-01、D-02、D-05 | 验签与拒绝证据；标注「重复无副作用」 |

> 收尾自检：R-16 的每条 PASS 是否都有「event_id + 处理次数 + 证据位置」？没有就降为「待确认」，**不得**凭「webhook 应该没问题」写 PASS。

## 11. 来源（2026-11 核对）

- Standard Webhooks 规范（`id.timestamp.payload`、`webhook-id` / `webhook-timestamp` / `webhook-signature`、空间分隔多签名、去重建议、重试表）：<https://raw.githubusercontent.com/standard-webhooks/standard-webhooks/main/spec/standard-webhooks.md>
- Stripe webhook 签名（`t=…,v1=…`、`t.payload`、原始 body、默认 300s、勿设 0）：<https://docs.stripe.com/webhooks>
- GitHub webhook 校验（`X-Hub-Signature-256`、`sha256=` 前缀、hex、constant-time）：<https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries>
- CloudEvents 规范（`source + id` 唯一、可据其去重；核心不承诺投递语义）：<https://raw.githubusercontent.com/cloudevents/spec/main/cloudevents/spec.md>
- Kafka 幂等生产者（单 partition 恰好一份、需 `acks=all`、顺序仅 partition 内）：<https://kafka.apache.org/documentation/#producerconfigs>
- SQS Standard（at-least-once、可能乱序）/ FIFO（5 分钟去重、同 group 有序）/ DLQ：<https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues.html>、<https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues-exactly-once-processing.html>、<https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html>
- 指数退避 + jitter（「不是去掉退避，而是加 jitter」）：<https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/>
- OWASP API7:2023 SSRF（webhook 出站请求面）：<https://owasp.org/API-Security/editions/2023/en/0xa7-server-side-request-forgery/>
