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
| **SBOM 与依赖扫描**（v1.2） | `syft ./proj -o cyclonedx-json=cdx.json` → `grype sbom:./cdx.json`；`osv-scanner scan source -r .`（V2 beta）；`trivy image <img>` | 静态查 lockfile、`sha256sum` 两次构建比对、`git diff --exit-code -- <lock>`，注明「未扫描」 | `supply-chain-testing.md` §4/§8 |
| **签名与 provenance 验证**（v1.2） | `cosign verify $IMAGE --certificate-identity=$ID --certificate-oidc-issuer=$ISSUER`；`slsa-verifier verify-artifact <artifact> --provenance-path <p> --source-uri github.com/<org>/<repo>` | 只留 digest 与静态审查，结论标 `BLOCKED`，**不得**写「已验证供应链安全」 | `supply-chain-testing.md` §4/§8 |
| **伪本地化 / locale 矩阵**（v1.2） | 脚本生成加长带变音伪串；浏览器切 `lang`/`dir`；`new Intl.Collator('tr-TR')` 对比排序 | `git grep` 查硬编码串、拼接、`toLocaleString('en-US')`、裸 `sort()` / `toUpperCase()`；注明「未做渲染验证」 | `i18n-localization-testing.md` §2/§7 |
| **双租户否定路径**（v1.2） | 构造 T1/T2 + 相同 ID 夹具；`curl` 换 `X-Tenant-ID`/token；`psql -tAc "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user"`；同一 pooled connection 连跑两租户 | `git grep` 查 context 传播、cache key、prefix 授权、`SET LOCAL`，注明「未做双租户实测」 | `multi-tenancy-testing.md` §1/§10 |
| **无障碍自动化扫描**（v1.4） | `npx @axe-core/cli <url> --exit`、`npx lighthouse --only-categories=accessibility --output=json`；结果必须同时记 `violations` 与 `incomplete` | curl 验 HTML 语义（`label for`/`alt`/`lang`）+ 人工键盘走查；注明「未做自动化扫描」 | `accessibility-testing.md` §2/§6 |
| **读屏与键盘路径**（v1.4） | NVDA/JAWS + Firefox·Chromium（Windows）、VoiceOver + Safari（macOS）、Narrator（Win+Ctrl+Enter）；Playwright `toMatchAriaSnapshot` 断言 a11y tree | 人工 Tab/Shift+Tab/Enter/Esc 逐步记 `activeElement` 与焦点遮挡，结果标 passed/failed/not checked/not present | `accessibility-testing.md` §3 |
| **跨端仿真**（v1.4） | Playwright `devices['iPhone 13']` / `devices['Pixel 7']`；`test.use({ locale, timezoneId, colorScheme, reducedMotion, permissions })`；`context.setOffline(true)` | 手工改浏览器窗口 + DevTools 节流，注明「浏览器仿真，非真机」 | `cross-platform-testing.md` §3/§5 |
| **真机与设备云**（v1.4） | 真机 / device cloud 覆盖 battery、thermal、sensors、biometrics、real network；`adb` / `xcrun simctl` 辅助 | 手边 1 台真机手工走查（前台→后台→回前台、旋转、飞行模式→恢复、深链冷启动），**只能写「单台真机手工走查」** | `cross-platform-testing.md` §2/§8 |
| **测试经济性 / ROI 取证**（v1.4） | CI 时长与并发数、runner 成本、quarantine 名单、发布回滚记录、工单系统缺陷来源 | `git log` 统计变更频率 + 手工估时，注明「成本为估计值，非实测账单」 | `test-effectiveness-testing.md` §5A |
| **证据链自动对账**（v1.5） | `python scripts/evidence-audit.py audit --manifest <json> --root . --format markdown --output <md>`；CI 门禁加 `--fail-on-gap --format json`；`python scripts/evidence-audit.py --self-test` 验门禁可证伪 | 按 `evidence-chain-audit.md` §8 用 `git rev-parse HEAD` + `grep -n` + `sha256sum` 手工重建链，标 `BLOCKED`、结论降为「待确认」，**不得**写「可审计」 | `evidence-chain-audit.md` §4/§8 |
| **install-base 设备矩阵草稿**（v1.5） | `python scripts/device-matrix.py build --input <csv\|json> --source "<数据源>" --window "<时间窗>" --min-coverage 0.8 --format markdown` | 无本地导出时人工填 `assets/device-matrix-template.md` 并写「数据源未登记 / 时间窗未登记」；**不得**把占比草稿写成真机证据 | `cross-platform-testing.md` §6A |
| **视觉回归基线**（v1.5） | Playwright `toHaveScreenshot()` + `snapshotPathTemplate`；`npx playwright test --update-snapshots`；`maxDiffPixels` / `maxDiffPixelRatio` / `threshold` / `mask` / `stylePath` | 三档断点人工截图比对；注明「未做像素级基线比对」；基线更新须留旧/新 hash + 理由 + 批准人 | `cross-platform-testing.md` §6A |
| **AI 生成用例有效性**（v1.5） | 变异测试（`npx stryker run` / `mutmut run`）+ 故意改坏 ≥1 处核心逻辑验假通过率 | 人工逐条审断言强度（`ai-native-testing.md` §3），注明「未做变异实测」，不写「有效性已验证」 | `test-effectiveness-testing.md` §5B |

### 可用性探测（一次跑完，结果记进命令速查）

```bash
for c in node npm npx python python3 pytest go cargo curl git; do
  printf '%-10s' "$c"; command -v "$c" >/dev/null && "$c" --version 2>/dev/null | head -1 || echo "MISSING"
done
command -v k6 || echo "k6 MISSING -> 用 shell 分位数采样"
command -v schemathesis || command -v uvx || echo "schemathesis MISSING -> 手写参数矩阵"
for c in syft grype osv-scanner cosign slsa-verifier trivy; do
  command -v "$c" >/dev/null || echo "$c MISSING -> 走 sha256sum / git grep 静态降级，结论标 BLOCKED"
done
# v1.5 两个零依赖脚本：先证明门禁本身可证伪，再用于交付
python scripts/evidence-audit.py --self-test || echo "evidence-audit SELFTEST FAIL -> 走 §8 人工链，结论标 BLOCKED"
python scripts/device-matrix.py --self-test || echo "device-matrix SELFTEST FAIL -> 退回人工填模板，注明数据源口径"
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
9. **自动化 a11y ≠ 人工读屏**：`axe-core` 自述平均仅自动发现约 57% 的 WCAG 问题，且 `incomplete` 需人工复核；扫描绿只能写「本次自动化扫描未发现 violations」，不能写「符合 WCAG 2.2 AA」（`accessibility-testing.md` §2/§5）
10. **仿真 ≠ 真机**：`devices['iPhone 13']`、emulator、simulator 一律标注载体，不得写成「真机验证」；battery/thermal/sensors/biometrics/real network 只能在 real device 上验（`cross-platform-testing.md` §2/§7）
11. **对账 GREEN ≠ 合规通过**：`scripts/evidence-audit.py` 只证明「结论 → 证据 → 原始输出」可解析；`--update-snapshots` 与 `--output` 是受控变更，基线/导出件更新都要留旧/新 hash 与理由；一次性探索无留档要求写「不适用」（`evidence-chain-audit.md` §4/§7）
12. **占比草稿 ≠ 安装量真相**：`scripts/device-matrix.py` 只吃本地导出、不联网、不代填载体，缺 `--source` / `--window` 时不能作为 R-8 矩阵来源证据；CrUX 只覆盖符合条件的真实 Chrome 用户且 form factor 仅三值，不能推出机型/OS 版本/非 Chrome 内核分布（`cross-platform-testing.md` §6A）
