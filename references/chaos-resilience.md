# 韧性与故障注入测试（阶段 2/3 · 有外部依赖的服务）

> 蒸馏自《Principles of Chaos Engineering》、Shopify/toxiproxy、chaos-mesh/chaos-mesh、litmuschaos/litmus、jepsen-io/jepsen，以及用户附加技能 `fullstack-dev` 的超时/重试/死信/优雅降级规则。
> 定位：功能测试问「依赖正常时对不对」，本手册问「**依赖不正常时会怎样**」。目标是**证伪稳态假设**，不是"证明系统很稳"。

## 1. 适用边界与安全红线（先读这一段）

| 规则 | 说明 |
|---|---|
| 授权与隔离 | 只在自己拥有或明确授权的**本地/测试/预发**环境注入；**禁止对外部服务、生产第三方接口做故障/压力注入** |
| 影响面 | 注入前写明爆炸半径（目标进程/流量比例/时长），从最小范围开始 |
| 中止条件 | 事先写死停止线（错误率、延迟、资源、告警），任一触发立即撤销注入 |
| 可恢复 | 每次注入必须有撤销动作与恢复验证；未验证恢复的实验不算完成 |
| 用户禁止变更环境时 | 降级为**静态审查** + 依赖超时/重试配置核对，报告注明「未做故障注入验证」 |

单进程、无外部依赖的 CLI/库/静态页面**不适用**本手册 —— 别为了凑维度而造故障。

## 2. 稳态假设：先定义"正常"才可谈"被打断"

稳态必须是**系统可测量的输出**，不是内部属性：

```
✅ 差：/health 返回 200、CPU 正常
✅ 好：下单接口在 30 秒窗口内成功率 ≥ 99.5%、p95 ≤ 400ms、队列积压 < 100
```

四步实验协议（来自 Principles of Chaos）：

1. 用可测量输出定义稳态（吞吐、错误率、延迟分位数）
2. 假设该稳态在**对照组**与**实验组**都持续
3. 引入反映真实事件的变量（进程崩溃、网络断开、磁盘故障、流量尖峰）
4. **寻找两组稳态差异来证伪假设** —— 差异越小，信心越高；发现弱点就是改进靶子

高级原则五条：围绕稳态建假设 / 变化真实事件 / 持续自动化实验 / 最小化爆炸半径 / （原则原文倾向生产流量，但本技能按 §1 红线**只在隔离环境做**）。

> 本技能与原文的一处**明确偏离**：原文「在生产环境运行实验」，考虑到测试授权与安全边界，本技能默认只在隔离环境做，并在报告中标注该局限。这是可证伪规则 R-2 的例外来源。

## 3. 故障注入矩阵（照表挑，别自由发挥）

| 依赖 | 注入变量 | 期望行为 | 通过判据 |
|---|---|---|---|
| 数据库 | 连接超时 / 拒绝 / 慢查询 1s | 显式超时、不无限等待、返回可理解错误 | 有 timeout 且 < 设定值；无连接泄漏；恢复后自动重连 |
| 缓存 | 不可用 / 返回陈旧值 | 主流程不被拖垮（降级） | 核心接口仍可用；不把缓存当权威状态 |
| 下游 HTTP | 5xx / 永不返回 / 畸形 JSON | 指数退避重试 ≤ 3 次、上限后进死信并告警 | 4xx 不重试；无重试风暴；无未捕获异常 |
| 消息队列 | 消费延迟 / 重复投递 / 乱序 | 幂等消费、顺序或无顺序依赖 | 重复消息不产生重复副作用 |
| 网络 | 延迟抖动 / 丢包 / TCP RESET / 带宽限制 | 超时与重连策略生效 | 无挂死连接、无请求堆积不释放 |
| 进程 / 节点 | 杀掉一个实例 | 流量切走、在途请求排空 | 不丢在途请求；SIGTERM 后停止接新连接 |
| 时间 | 时钟跳变 | 依赖绝对时间的逻辑不崩 | token 过期、定时任务行为可解释 |
| 磁盘 / IO | 写满 / IO 延迟 | 明确报错，不静默丢数据 | 数据完整性见 `references/data-integrity-testing.md` |

**优先级**：按「潜在影响 × 估计频率」排序，先打最高频且最便宜的（网络延迟、超时），不要一上来杀节点。

## 4. 三级工具阶梯（任何一级缺失都可降级）

### L0 零依赖（默认，先做这个）

```bash
# 依赖永不返回 → 验证客户端 timeout 真的生效
python -m http.server 9999 --bind 127.0.0.1 >/dev/null 2>&1 &   # 起一个可控本地依赖
# 在应用配置里把该依赖指向 127.0.0.1:9999，然后：
time curl -s -o /dev/null -w "HTTP %{http_code} %{time_total}s\n" \
  http://127.0.0.1:3000/api/orders/8f3a
# 断言：耗时不超过配置的 timeout，且返回结构化错误而非 500 裸堆栈
kill %1 2>/dev/null

# 重复投递 / 并发 → 幂等判据（同一幂等键连发 3 次只应产生 1 条记录）
for i in 1 2 3; do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST \
    -H "Idempotency-Key: fix-key-001" -H "Content-Type: application/json" \
    -d '{"amount":100}' http://127.0.0.1:3000/api/charges &
done; wait
```

静态也能出结论：`git grep` 找所有外部调用是否设 timeout、重试是否区分 4xx/5xx、SIGTERM 是否排空在途、后台任务是否假定"恰好一次"。

### L1 确定性网络故障（Toxiproxy，可选）

- TCP 代理 + HTTP API（默认端口 `8474`），把应用连依赖的流量引到代理的 `listen` 地址
- toxics：`latency`（`latency` ± `jitter`，毫秒）、`bandwidth`（KB/s）、`slow_close`、`timeout`（`timeout=0` 表示一直丢数据直到移除）、`reset_peer`、`slicer`、`limit_data`、`packet_loss`
- `stream` 默认 `downstream`（server→client），`upstream` 是 client→server；`toxicity` 默认 `1.0`（100% 生效）
- `down` 不是 toxic，是把 proxy 的 `enabled` 设 false；`POST /reset` 一键恢复全部
- 确定性来自固定属性 + `toxicity=1.0` + 把注入限定在测试作用域内；`jitter`/低 `toxicity` 才用于随机化
- 端口避开系统 ephemeral range（Linux 常见 32768~61000），避免随机端口冲突

```bash
toxiproxy-cli create dep_redis --listen 127.0.0.1:22220 --upstream 127.0.0.1:6379
toxiproxy-cli toxic add --type latency --attribute latency=1000 dep_redis
# 在此期间执行断言…
toxiproxy-cli toxic remove --toxicName latency_downstream dep_redis
curl -X POST http://127.0.0.1:8474/reset      # 兜底恢复
```

### L2 编排式（Kubernetes，可选）

- **Chaos Mesh**（CNCF incubating）：实验用 K8s CRD 定义，覆盖 Pod / network / DNS / HTTP / I/O / time / stress / kernel 等故障，`Schedule` / `Workflow` / `StatusCheck` 支持周期实验与串行编排，作用域靠 K8s selector/namespace + RBAC 收窄
- **LitmusChaos**：`ChaosExperiment`（故障模板）→ `ChaosEngine`（绑定 workload + `probes` 稳态约束）→ `ChaosResult`（verdict、故障 revert/rollback 状态、Prometheus 指标），可作为 CI/CD 的一个 stage
- **Jepsen 风格**（分布式存储/一致性）：generator 生成操作 → nemesis 注入故障 → 记录每个操作起止的 history → checker 分析正确性（线性一致性等）；本技能只借用「操作历史 + 故障 + 一致性检查」的思路，不要求部署其集群

> 三级都缺失时仍可完成：L0 + 静态审查 + 明确标注局限。工具是加速器，**不是前置依赖**。

## 5. 恢复与收尾判据（最容易漏的一段）

实验结束必须逐条留证据，否则结论无效：

- [ ] 注入已撤销（toxic 已移除 / proxy reset / CRD 已删除 / 进程已恢复）
- [ ] 稳态指标在约定时间内回到基线（写清恢复时长）
- [ ] 无残留：连接数、队列积压、临时文件、脏数据、僵尸进程
- [ ] 告警是否被触发（没触发说明监控有缺口，也是发现）
- [ ] 中止条件与回滚动作实际可执行（不是写在纸上的预案）
- [ ] 对照组同期指标已记录（否则无法区分"注入导致"与"本来就抖"）

回滚预案没演练过就等于没有 —— 与 `references/fullstack-integration.md` §6 Gate 4 一致。

## 6. 演练记录格式

用 `assets/resilience-runbook-template.md` 逐次记录；结论写 `PASS / FAIL` 且区分「稳态未被证伪」与「已具备韧性」——前者只是**一次实验的结果**，后者需要多次、多故障类型、不同负载下的证据。

## 7. 反模式

| ❌ | ✅ |
|---|---|
| 直接杀主库/打生产流量 | 从网络延迟这类最小爆炸半径开始，隔离环境 |
| 没有对照组 | 同期记录对照组稳态，否则无法归因 |
| 只看"服务还活着" | 看吞吐/错误率/p95 的可测量输出 |
| 注入完不撤销 | 每次都有恢复验证与 `/reset` 兜底 |
| 把"没崩"写成"高可用" | 写清实验次数、故障类型、负载与恢复时长 |
| 用一次实验证明稳态假设 | 目标是**证伪**；证伪不了只提升信心 |

> **可证伪规则 R-2**（v1.1 引入）：凡声称"系统在依赖故障下仍可用 / 具备韧性"的结论，必须附一次**可复现的故障注入记录**：注入点、时长、爆炸半径、稳态指标前后值、对照组、恢复时长、撤销证据（模板见 `assets/resilience-runbook-template.md`）。
> **不适用**：单进程无外部依赖的 CLI/库/静态项目、用户明确禁止变更运行环境、或只有静态审查条件 —— 此时只能写「未做故障注入验证」，**不得**写「具备韧性」；仅靠"代码里有 try/catch"或"配置了重试"不构成通过证据。
