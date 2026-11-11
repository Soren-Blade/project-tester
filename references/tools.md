# 测试工具调用表（阶段 3 详版）

选择顺序：**项目已有测试设施 > 轻量新增 > 裸执行断言**。任何工具缺失都不终止测试——按"降级"列执行，并在报告中注明降级原因。

## 按技术栈

### Node / JS / TS

| 用途 | 首选 | 命令 | 缺失时降级 |
|---|---|---|---|
| 单测 | 项目自带 | `npm test` / `npx vitest run` / `npx jest` | Node ≥18 用自带的 `node --test`；或 `npm i -D vitest` 装一个 |
| E2E | Playwright | `npx playwright test` | HTTP 层验证：`curl -s URL` 断言 HTML 关键元素；环境有浏览器自动化能力就用它 |
| HTTP 接口 | curl | `curl -s -w "\nHTTP %{http_code} %{time_total}s\n" -X POST -H "Content-Type: application/json" -d '{...}' URL` | — |
| 覆盖率 | vitest | `npx vitest run --coverage` | 跳过，用测试点计数代替 |

### Python

| 用途 | 首选 | 命令 | 降级 |
|---|---|---|---|
| 单测 | pytest | `python -m pytest -v --tb=short` | 直接 `python script.py` + 断言退出码 |
| 覆盖率 | pytest-cov | `python -m pytest --cov=. --cov-report=term` | 跳过 |
| Web 框架 | 框架测试客户端 | FastAPI `TestClient` / Django `test` | 起服务 `uvicorn app:app` + curl 实调 |

### Go / Rust / 其他

- Go：`go test ./... -race -cover`（-race 抓并发问题）
- Rust：`cargo test`
- PHP：`php artisan test` / `vendor/bin/phpunit`
- 静态前端：本地起静态服务 + 浏览器/curl 验证；表单用 POST 实测

## 通用 shell 断言模板（任何栈都能用）

```bash
# 期望成功
cmd args && echo "PASS" || echo "FAIL 退出码 $?"
# 期望失败（刁钻输入应当被优雅拒绝）
if cmd bad-input 2>/dev/null; then echo "FAIL: 应当拒绝却接受了"; else echo "PASS 已拒绝"; fi
# 期望特定输出
out=$(cmd args); [[ "$out" == *"期望片段"* ]] && echo PASS || echo "FAIL 实际: $out"
```

## 按测试对象

- **Web UI**：本地起服务（记端口）→ 有浏览器自动化就截图/点击/输表单；没有就 `curl -s http://127.0.0.1:PORT | grep 关键元素` + 表单 POST 实测。中文乱码、布局崩坏属于 bug。
- **API**：全动词遍历（GET/POST/PUT/DELETE/PATCH）+ 异常参数矩阵（空、超长、类型错、注入串、不存在的 id）+ 鉴权缺失/过期。`-w` 计时顺带看性能维度。
- **CLI**：逐命令执行；`--help` 是否存在且能看懂本身就是测试点；退出码 0/1/2 语义是否一致；管道与重定向下的行为。
- **库 / 包**：写最小调用程序（`.test-memory/tmp/probe_*`）验证导出行为与文档一致。
- **数据处理类**：构造小样本跑全流程比对输出——空文件、单行、脏行（缺列/类型错/BOM/CRLF）、大文件、重复键。

## 专项工具表（v1.0 新增）

**先探测再决定**，任何一行缺失都走降级列，绝不中止测试。

| 用途 | 工具 / 命令 | 缺失时降级 | 手册 |
|---|---|---|---|
| API 属性/规范测试 | `schemathesis run <openapi-url> --checks all`（或 `uvx schemathesis run`） | 手写异常参数矩阵 | `api-testing.md` §7 |
| 负载与分位数 | `k6 run -e BASE_URL=... load-test.js` | shell 采样 + `sort`/`awk` 算 p50/p95/p99 | `performance-testing.md` §3 |
| 契约测试 | `npx pact-js` / Pact Verifier / OpenAPI diff | 手工比对请求响应结构 | `fullstack-integration.md` §4 |
| 真 DB 集成 | `@testcontainers/*` / docker compose + `tmpfs` | 事务回滚 / truncation | `fullstack-integration.md` §2 |
| 可访问性 | `npx @axe-core/cli <url> --exit`、`npx lighthouse --only-categories=accessibility` | curl 验 HTML 语义（`label for` / `alt` / `lang`）+ 人工键盘走查 | `frontend-testing.md` §3 |
| 视觉回归 | Playwright `toHaveScreenshot()` | 三档断点人工截图比对 | `frontend-testing.md` §4 |
| 依赖漏洞 | `npm audit --omit=dev` / `pip-audit` / `govulncheck ./...` / `cargo audit` | 静态查锁文件版本 + 记录"未扫描" | `security-testing.md` §4 |
| 变异测试 | `npx stryker run` / `mutmut run` / PIT / `cargo mutants` | 人工抽查断言强度（伪测试清单） | `quality-gates.md` §5 |
| AI 辅助 E2E | `npx playwright init-agents --loop=vscode`（v1.56+） | 手写用例 / HTTP 层验证 | `ai-native-testing.md` §2 |
| 浏览器自动化 | Playwright / 环境自带浏览器能力 | `curl -s URL` 断言 HTML 关键元素 + 表单 POST 实测 | SKILL.md 阶段 3 |
| Trace / 链路断言 | Tracetest `tracetest run test --file <yaml>`（可选） | curl 带 `traceparent` + `grep` 同一 id 跨组件日志 | `observability-testing.md` §3 |
| 确定性网络故障 | Toxiproxy（HTTP API `:8474`）/ `toxiproxy-cli` | 本地起一个永不返回的依赖 + `time curl` 验 timeout | `chaos-resilience.md` §4 |
| K8s 故障编排 | Chaos Mesh CRD / LitmusChaos `ChaosEngine` | 静态审查 timeout / 重试 / SIGTERM 配置 | `chaos-resilience.md` §4 |
| 非 REST 实调 | `grpcurl -plaintext -d '{...}' host:port Service/Method`（reflection 或 `-protoset`） | 用项目自带 client / 静态读 `.proto`、`*.graphql` | `protocol-testing.md` §3 |
| DB 对账与并发 | `psql -tAc "SELECT count(*)"` + shell 后台并发 | 通过 API 读回比对，标注「间接验证」 | `data-integrity-testing.md` §4/§6 |

### 可用性探测（一次跑完，结果记进命令速查）

```bash
for c in node npm npx python python3 pytest go cargo curl git; do
  printf '%-10s' "$c"; command -v "$c" >/dev/null && "$c" --version 2>/dev/null | head -1 || echo "MISSING"
done
command -v k6 || echo "k6 MISSING -> 用 shell 分位数采样"
command -v schemathesis || command -v uvx || echo "schemathesis MISSING -> 手写参数矩阵"
```

## 工具使用纪律

1. 优先复用记忆树"命令速查"里已验证的命令，不重复试错
2. 新跑通的命令立即记进当次 runs/ 记录
3. 临时探针文件统一放 `.test-memory/tmp/`，测试结束删除，不污染项目
4. 性能维度用时间戳差值 / `time` / curl `-w` 即可，不引入重型压测工具；**禁止对外部服务压测**
5. 并发类测试用后台进程 + 短循环模拟（如 `for i in 1 2 3; do curl ... & done; wait`），规模保持克制
6. **工具是可选加速器，不是前置依赖**：任何专项工具缺失，都必须能用 `curl` + shell 断言 + 静态审查走完五阶段，并在报告注明降级原因
7. 装新依赖前先确认是否污染被测项目；优先用 `npx`/`uvx` 临时执行，或把探针放 `.test-memory/tmp/`
8. 每个工具输出都要留原始片段作证据；**工具说"通过"不等于断言有效**（见 `quality-gates.md` §5）
