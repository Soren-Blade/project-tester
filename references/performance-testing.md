# 性能测试手册（阶段 3 · 性能维度）

> 蒸馏自 `fullstack-dev/references/testing-strategy.md`（k6 与性能预算）、`release-checklist.md` Gate 2、Grafana k6 阈值模型、Core Web Vitals 口径。
> **边界**：只对本地/授权测试环境施加负载。禁止对外部服务、生产系统做压力或 DoS 测试。本技能默认只做**轻量探测**，规模化压测需用户明确要求且环境隔离。

## 1. 五种负载形态（别把"访问了一下挺快"叫性能测试）

| 类型 | 目的 | 典型配置 | 观察什么 |
|---|---|---|---|
| 冒烟 / Smoke | 验证脚本与环境可用 | 1~5 VU，1 分钟 | 无错误、端点通 |
| 负载 / Load | 预期流量下是否达标 | 目标 RPS，持续 10~30 分钟 | p95/p99、错误率、资源 |
| 压力 / Stress | 找崩溃点 | 逐步加到远超预期（如 10×） | 在哪一档开始劣化/报错 |
| 浸泡 / Soak | 长时间是否泄漏 | 中等负载，数小时 | 内存 creep、连接池耗尽、FD 泄漏 |
| 尖峰 / Spike | 突发流量与恢复 | 瞬间拉高再回落 | 是否雪崩、能否自恢复、队列排空 |

本技能默认执行**冒烟 + 轻量负载**；压力/浸泡/尖峰需明确授权与环境隔离，且不得打外部服务。

## 2. 指标口径（先说清口径，再报数字）

| 指标 | 定义 | 常见目标 |
|---|---|---|
| p50 / 中位 | 一半请求快于此 | 体感基线 |
| **p95** | 95% 请求快于此 | API < 200~500ms（按 SLA 定） |
| p99 | 长尾 | < 1000ms，用于抓离群查询 |
| 错误率 | `http_req_failed` / 总请求 | < 0.1% |
| 吞吐 | RPS / QPS | 按容量目标 |
| TTFB | 首字节 | ≤ 0.8s（前端口径） |
| 并发数 | 同时在途请求 | 与 RPS、响应时间满足 Little's Law |

**Little's Law**：`并发数 ≈ 吞吐量(RPS) × 平均响应时间(s)`。用它反推该压多少 VU，别拍脑袋。"100 并发"没有响应时间就没有意义。

**前端 Core Web Vitals**（真实用户第 75 百分位）：LCP ≤ 2.5s、INP ≤ 200ms、CLS ≤ 0.1。这三个是**用户体验**指标，与后端 p95 不是一回事，报告中分开列。

> 陷阱：平均值会骗人。1% 的 10 秒请求被 99 个 100ms 请求平均掉后只显示 ~200ms。**必须报分位数**。

## 3. 轻量探测（零依赖，任何环境可用）

```bash
# 单次计时
curl -s -o /dev/null -w "HTTP %{http_code} | total %{time_total}s | ttfb %{time_starttransfer}s\n" \
  http://127.0.0.1:3000/api/orders

# N 次采样算分位数（无需压测工具）
for i in $(seq 1 30); do
  curl -s -o /dev/null -w "%{time_total}\n" http://127.0.0.1:3000/api/orders
done | sort -n > /tmp/lat.txt
awk 'NR==int(N*0.50)+1||NR==int(N*0.95)+1||NR==int(N*0.99)+1 {print NR": "$0}' N=30 /tmp/lat.txt

# 克制的并发探测（5 并发 × 3 轮）
for round in 1 2 3; do
  for i in 1 2 3 4 5; do curl -s -o /dev/null -w "%{http_code} %{time_total}\n" \
    http://127.0.0.1:3000/api/orders & done
  wait
done
```

把跑通的命令原样写进 `runs/` 与 `tree.md` 命令速查——这是接力时最值钱的一条。

## 4. k6 模板（有工具且用户要求规模化时用）

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 },   // ramp up
    { duration: '1m',  target: 100 },  // sustain（目标按 Little's Law 反推）
    { duration: '30s', target: 0 },    // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed:   ['rate<0.01'],
  },
};

export default function () {
  const res = http.get(`${__ENV.BASE_URL}/api/orders`);
  check(res, { 'status 200': (r) => r.status === 200 });
  sleep(1);
}
```

```bash
k6 run -e BASE_URL=http://127.0.0.1:3000 load-test.js
```

`thresholds` 是质量门禁，不满足时 k6 以非零码退出，可直接接 CI。降级：无 k6 就用 §3 的 shell 采样 + 手工判分位。

## 5. 性能预算表（写进测试计划，别事后找标准）

| 指标 | 目标 | 超了查什么 |
|---|---|---|
| p95 响应 | < ___ms（按项目定，API 常取 200~500） | 慢查询、N+1、缺索引、无缓存 |
| p99 响应 | < 1000ms | 离群查询、GC、锁等待 |
| 错误率（负载下） | < 0.1% | 连接池耗尽、超时、限流误伤 |
| DB 单查询 | < 100ms | `EXPLAIN ANALYZE`、加索引 |
| 缓存命中率 | > 80%（若用了缓存） | key 设计、TTL、写后是否失效 |
| 分页大数据量 | 不随页码线性劣化 | `OFFSET` 深翻页 → 游标分页 |
| 内存/CPU | 浸泡下无持续上升 | 泄漏、未释放连接/句柄 |

## 6. 瓶颈定位顺序（从最便宜的查起）

1. **看日志/慢查询** —— 开 query logging，数一个请求发了多少条 SQL（N+1 一眼可见）
2. **看 DB** —— `EXPLAIN ANALYZE` 关键查询；连接池是否打满；事务是否过长
3. **看缓存** —— 命中率、TTL 是否全设了、写后有没有失效（**写不失效 = 脏数据**）
4. **看外部依赖** —— 每个外部调用是否有超时与重试退避；无超时的依赖会拖垮整条链路
5. **看资源** —— CPU / 内存 / FD / 线程池；浸泡测试看 creep
6. **看前端** —— LCP/INP/CLS、未压缩资源、无尺寸图片导致 CLS（见 `frontend-testing.md`）

## 7. 性能维度的判 bug 标准

- 明确 SLA/预算下 p95 超标 → **一般 bug**（若用户给了 SLA 则升级）
- 负载下出现 5xx / 错误率超标 / 服务不恢复 → **严重 bug**
- 大数据量分页直接超时、界面卡死 → **一般~严重**
- 并发下产生重复数据/负库存/双花 → **严重**（属正确性 bug，见 `api-testing.md`）
- 无基线、只测了一次 → 报告写"**单点观测，不构成性能结论**"，不许写成"性能良好"

## 8. 记录格式

```
类型：冒烟 + 轻量负载（30 次采样 / 5 并发 × 3 轮）｜目标：本地 127.0.0.1:3000
p50/p95/p99: 42ms / 118ms / 310ms ｜ 错误率 0% ｜ 吞吐 23 RPS
预算：p95<500ms ✅ ｜ 压力/浸泡/尖峰：本轮未执行（需隔离环境）
瓶颈线索：/api/orders 单次请求 31 条 SQL，疑似 N+1 → 建议开 query logging 复核
局限：单机 localhost，无网络延迟，不代表生产
```

## 9. 反模式

| ❌ | ✅ |
|---|---|
| 只报平均值 | 报 p50/p95/p99 + 样本数 |
| 拿本机 localhost 结果推断生产 | 注明局限与网络/数据差异 |
| 没基线就说"优化后快了" | 先存基线再比 |
| 压测打到第三方/生产 | 本地隔离 + mock 外部依赖 |
| 用压测掩盖正确性问题 | 并发下的数据错乱归到正确性，优先修 |
