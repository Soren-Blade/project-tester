# 项目解剖手册（阶段 1 详版）

目标：用最少的读写建立可测试的功能地图。解剖是手段不是目的——能支撑测试计划就停。

## 1. 栈指纹（看根目录文件即可判断）

| 看到什么 | 技术栈 | 重点读 |
|---|---|---|
| package.json | Node / JS / TS | `scripts`、`dependencies`（express/next/nuxt/vite/electron 等框架线索）、`main`/`bin` |
| pyproject.toml / requirements.txt | Python | 入口声明、依赖（fastapi/django/flask/click/pytest） |
| go.mod | Go | module 名、`cmd/` 目录、main.go |
| Cargo.toml | Rust | `[[bin]]`、src/lib.rs 导出面 |
| composer.json | PHP | laravel / symfony |
| pom.xml / build.gradle | Java / Kotlin | Spring Boot？入口类 |
| Gemfile | Ruby | Rails / Sinatra |
| index.html 且无打包器 | 静态前端 | `<script>` 引用链、内联逻辑 |
| CMakeLists.txt / Makefile | C / C++ | make 目标、可执行文件名 |
| Dockerfile / docker-compose.yml | 任意（容器化 / 多服务） | ENTRYPOINT、EXPOSE 端口、**服务间依赖边** |
| `*.proto` / `*.graphql` / `openapi.yaml` | 非 REST 协议 | 服务/operation 清单，见 `references/protocol-testing.md` |
| `migrations/` / `alembic/` / `prisma/` | 有持久化与迁移 | 迁移文件数量、是否可回滚，见 `references/data-integrity-testing.md` |
| `*lock*` / `Dockerfile` / `.github/workflows/release*` / `dist/`（v1.2） | 有交付链与发布产物 | lockfile 是否冻结依赖、镜像/产物如何构建、有无签名/SBOM/attestation → `references/supply-chain-testing.md` |
| `locales/` / `i18n/` / `messages.*` / `*.po`（v1.2） | 多语言 / 本地化 | 支持哪些 locale、有无 RTL 资源、格式化调用在何处 → `references/i18n-localization-testing.md` |
| `tenant_id` / `org_id` / `workspace_id`、RLS policy、共享 cache/queue 配置（v1.2） | 多租户 / SaaS | 租户标识来源、隔离策略声明、共享资源清单 → `references/multi-tenancy-testing.md` |

混合项目 / monorepo：对每个子目录（packages/、apps/、services/）重复此表，逐个记录。

## 2. 入口追踪

- README 的 quickstart 命令 → 那就是真实入口，优先级最高
- Web 服务：路由定义处（routes/、router/、controllers/、urls.py、app.py 的路由装饰器）
- GraphQL：schema + resolver 注册处（**单端点承载全部操作，按 operation 盘点**）
- gRPC：`.proto` 的 service/method + 服务端注册处（是否开 reflection）
- 实时：`/ws` upgrade、`EventSource` / `text/event-stream` 端点、订阅频道名
- CLI：命令注册处（commander / click / argparse / cobra 的子命令清单）
- 前端：菜单与路由（router/index、App.* 的导航结构）——菜单项 ≈ 功能清单
- 库：导出面（index.ts 的 export、`__init__.py`、lib.rs 的 pub）——导出 ≈ 可测 API

## 3. 功能清单提取（两列对照法）

| 宣称功能（文档/README/菜单文案声称的） | 实际功能（入口/路由/命令里真实存在的） |
|---|---|
| ... | ... |

差异本身生成测试点：

- 宣称了但代码里没有 → 功能未实现，P0 级问题
- 代码里有但文档没提 → 功能藏得深，测它 + 建议补文档
- 名字对不上 → 文档过时，行为以代码为准并记录

## 4. 可运行性探测（产出"命令速查"）

按顺序尝试，**每跑通一个就原样记下精确命令**（含工作目录、参数、端口）：

1. 项目自带测试：`npm test` / `make test` / `python -m pytest` / `go test ./...` / `cargo test`
2. 启动：`npm run dev` / `python app.py` / `./bin/name` …，记录启动耗时与端口
3. 装依赖或启动失败 → 记录卡点与报错原文，记忆树标 🔥，降级为静态测试

把"能跑通的命令"写进记忆树"命令速查"区——下次直接复制执行，**这是记忆树省 token 的大头**。

### Windows / Git Bash 环境注意

- 路径含空格必须加引号；正斜杠反斜杠在 bash 里行为不同，优先用 `/d/apps/foo` 形式
- `python` / `python3` 命名因机器而异，先探测 `command -v`
- `npx` / `uvx` 可用性先确认；Node 自带测试器 `node --test`（Node ≥ 18）永远可用
- 长路径、中文路径都可能踩坑，遇到就记入 lessons.md

## 5. 规模感知（决定解剖深度）

- 小型（<10 个源文件）：全量解剖
- 中型：解剖入口 + 路由 + 核心模块，其余按目录名推定，测到再深入
- 大型：完全依赖记忆树接力，只解剖本次范围内的模块；没有记忆树时先建"骨架树"（目录级），随测试逐模块充实

## 6. 测试设施盘点（v1.0 新增，v1.1 扩充）

解剖时顺手记录「项目已经有什么」，决定阶段 3 是复用还是降级：

| 找什么 | 在哪看 | 影响 |
|---|---|---|
| 测试框架与脚本 | `package.json scripts`、`pyproject.toml`、`Makefile`、`*_test.go` | 有就先跑通它的套件 |
| 测试/覆盖率配置 | `vitest.config.*`、`jest.config.*`、`pytest.ini`、`coverage` 字段 | 覆盖准则的口径来源 |
| 契约/规范文件 | `openapi.yaml`、`swagger.json`、`*.graphql`、`*.proto` | 有规范就可上 schemathesis / 契约测试（`api-testing.md` §7）；非 REST 走 `references/protocol-testing.md` |
| 性能脚本 | `k6/`、`*.js` with `import http from 'k6/http'`、`locustfile.py` | 有基线就直接对比 |
| E2E 与 fixtures | `playwright.config.*`、`tests/seed.spec.ts`、`specs/*.md` | Playwright Test Agents 是否已初始化（`ai-native-testing.md` §2） |
| CI 配置 | `.github/workflows/*`、`.gitlab-ci.yml`、`Jenkinsfile` | 质量门禁现状（`quality-gates.md` §6） |
| 依赖锁文件 | `package-lock.json`、`poetry.lock`、`go.sum` | 依赖审计能否跑 |
| **可观测性配置**（v1.1） | OTel SDK / Collector 配置、`traceparent` 处理、结构化 logger、`/health` `/ready`、Prometheus/SLO 定义 | 决定能否做链路断言与 SLO 门禁（`references/observability-testing.md`）；没有就记「可观测性缺口」 |
| **迁移与数据设施**（v1.1） | `migrations/`、`alembic/`、`prisma/`、`*.protoset`、缓存配置、CDC/队列定义 | 决定数据一致性与迁移测试的入口（`references/data-integrity-testing.md`） |
| **交付链设施**（v1.2） | `package-lock.json` / `poetry.lock` / `go.sum`、`Dockerfile`、release workflow、`dist/` 与产物、SBOM 文件、签名/attestation 配置 | 决定能否叠加 `references/supply-chain-testing.md`；**无构建产物的纯源码脚本标「不适用」**，不写「供应链安全」 |
| **locale 面**（v1.2） | 资源文件（`locales/`、`i18n/`、`messages.*`）、`Intl`/`toLocaleString` 调用、`lang`/`dir` 属性、时区与货币格式化 | 决定代表 locale 清单与 `references/i18n-localization-testing.md` 的六维矩阵范围 |
| **租户边界**（v1.2） | `tenant_id`/`org_id`/`workspace_id` 从哪来、共享 DB/cache/queue/storage 清单、隔离策略声明（Separate DBs / Schemas / RLS / Hybrid）、platform admin 与跨租户 service identity | 决定 `references/multi-tenancy-testing.md` 的夹具与否定路径清单；**单租户标「不适用：无租户边界」** |
| **无障碍面**（v1.4） | 交互控件清单、认证方式（有无验证码/转录）、焦点样式与 ARIA、`aria-live`/`aria-describedby`、图标按钮可访问名、目标尺寸、是否已声明 WCAG 2.2 AA 与读屏支持 | 决定 `references/accessibility-testing.md` 的键盘路径与读屏组合范围；**无 UI 的 CLI/库标「不适用：无图形交互界面」** |
| **设备形态面**（v1.4） | 声明支持的 OS / 浏览器内核 / 屏幕形态（折叠屏、平板、小屏）、是否可得 install-base analytics、有无真机或设备云、CI 里是否已有 `devices`/emulation 配置 | 决定 `references/cross-platform-testing.md` 的矩阵来源与 `real`/`emulator` 载体划分；**纯后端 API/CLI 标「不适用：无终端形态差异」** |
| **证据链面**（v1.5） | 有无留档要求与合规声明清单（SOC2 / 等保 / SSDF / GDPR）、原始输出落点（`runs/` / CI artifacts / 日志）、能否取到 commit / 环境指纹 / 时间窗、是否有视觉快照基线与 install-base 本地导出、报告结论是否可指到文件行 | 决定能否叠加 `references/evidence-chain-audit.md`（R-9）与 `scripts/evidence-audit.py`；**一次性探索、无留档要求标「不适用：无留档要求」**，不写「可审计」 |

## 7. 攻击面、观测面与依赖拓扑（v1.0 新增，v1.1 / v1.2 扩充）

一眼扫出高风险区，直接喂给测试矩阵的安全维度：

- **认证/鉴权位置**：中间件顺序（request-id → logging → CORS → ratelimit → body → auth → authz → validation → handler）
- **输入边界**：所有 `req.body` / `req.query` / 文件上传 / webhook / callback 字段 → 注入与 SSRF 候选
- **对象 ID 来源**：路径参数 `:id` 是否只凭 ID 取数据 → BOLA 头号嫌疑（`security-testing.md` API1）
- **配置**：`.env.example` 是否存在、`CORS` 是否 `*`、是否有 `/health` `/ready`、是否有调试端点
- **密钥**：`git grep -nEi '(api[_-]?key|secret|password|BEGIN .*PRIVATE KEY)'`
- **影子端点**：`/v1/` 与 `/v2/` 并存、`/debug`、`/swagger`、`/actuator`
- **观测面**（v1.1）：日志是否结构化、是否带 `request_id` / `trace_id`、跨服务是否转发 `traceparent`、span 属性是否脱敏；错误响应是否泄漏堆栈
- **依赖拓扑与故障域**（v1.1）：列出所有外部依赖（DB / 缓存 / 队列 / 第三方 API / 文件系统），逐个记「是否设 timeout、是否重试、是否有降级、是否幂等」。这张表就是 `references/chaos-resilience.md` §3 故障注入矩阵的输入；**没有外部依赖的单体项目不必叠加韧性专项**
- **交付链攻击面**（v1.2）：lockfile 是否入库、是否有浮动版本（`latest`/`^`/git 分支）、`preinstall`/`postinstall`/`setup.py` 是否联网外联、CI workflow 是否可绕过 review、是否有直连公共 registry 的旁路、构建机是否 ephemeral、产物有没有 digest/签名/provenance → 输入 `references/supply-chain-testing.md` §2/§6
- **locale 与文本面**（v1.2）：硬编码文案与字符串拼接、图片内嵌文字、`toUpperCase()`/裸 `sort()`、硬编码 `toLocaleString('en-US')`、CSS 里用 `direction`/固定 `left|right` 代替 `dir`/logical properties → 输入 `references/i18n-localization-testing.md` §7 静态审查
- **租户边界与共享资源**（v1.2）：客户端 `X-Tenant-ID` 是否被直接当权威 context、cache key 是否含 `tenant_id`、queue payload 的 `tenant_id` 是否被 consumer 采信、object prefix 是否被当授权、是否有 superuser/`BYPASSRLS` request role、session 级 `SET`（应为 `SET LOCAL`）、platform admin 是否有 explicit authorization → 输入 `references/multi-tenancy-testing.md` §10 静态降级

这些是**静态也能做的测试**，项目跑不起来时尤其有价值。

## 8. 项目形态 → 能力层路由（v1.0 新增，v1.1 扩充）

| 形态 | 主用手册 | 必做动作 |
|---|---|---|
| REST / GraphQL / gRPC 服务 | `api-testing.md` + `security-testing.md` | 端点矩阵、认证授权矩阵、错误契约、幂等 |
| **GraphQL / gRPC / WS / SSE** | `references/protocol-testing.md` + `assets/protocol-matrix-template.md` | 按 operation/method 建矩阵；协议特有错误码、resolver/metadata 鉴权、重连退订 |
| 全栈应用（前后端） | `fullstack-integration.md` + `frontend-testing.md` | 构建/冒烟/CORS/auth 携带 + 五态矩阵 |
| 纯前端 / 静态页 | `frontend-testing.md` | 五态、a11y、窄屏、无占位资源、CWV |
| CLI / 脚本 / 库 | `tools.md` + `test-design.md` | 退出码、`--help`、边界值、属性测试不变量 |
| LLM / Agent / RAG 应用 | `ai-native-testing.md` | 评测集、蜕变关系、注入、工具权限、非确定性 |
| **微服务 / 多组件 / 异步链路** | `references/observability-testing.md` | trace_id/request_id 贯通 ≥2 组件、副作用 span、SLO 与错误预算 |
| **有外部依赖、需验容错** | `references/chaos-resilience.md` + `assets/resilience-runbook-template.md` | 稳态假设 → 最小爆炸半径注入 → 恢复验证（R-2） |
| **有 DB / 迁移 / 缓存 / 多副本** | `references/data-integrity-testing.md` | 三重断言、迁移 up/down、并发不变量 |
| 压测 / 负载与分位数验收 | `references/performance-testing.md` | 五种负载、p95/p99 口径、k6 thresholds、性能预算与瓶颈定位（v1.2 补齐此前缺失的路由） |
| 上线前验收 / 发布 | `fullstack-integration.md` §6 + `quality-gates.md` | 六门禁 12 分打分、Go/No-Go |
| **有 lockfile / 镜像 / 发布产物 / CI 流水线**（v1.2） | `references/supply-chain-testing.md` + `assets/supply-chain-evidence-template.md` | 制品 `sha256` + SBOM 原件与覆盖缺口 + 签名/provenance 验证命令原文与退出码（R-3）；纯源码/静态页标「不适用」 |
| **多语言资源 / locale 切换 / RTL / 跨国格式**（v1.2） | `references/i18n-localization-testing.md` + `assets/i18n-matrix-template.md` | 代表 locale × 六维矩阵、伪本地化、`dir`/`dirname`/`<bdi>`、F-1~F-8 格式往返；无浏览器时静态审查并标 BLOCKED |
| **多租户 / SaaS / 共享 DB·cache·queue·storage / platform admin**（v1.2） | `references/multi-tenancy-testing.md` + `assets/tenant-isolation-matrix-template.md` | 双租户相同 ID 夹具、分层否定路径、连接复用与双租户备份恢复（R-4）；单租户标「不适用」 |
| **有 OpenAPI/GraphQL/proto 规范且多客户端/多版本在跑**（v1.3） | `references/contract-evolution-testing.md` + `assets/contract-evolution-matrix-template.md` | `oasdiff breaking --fail-on=ERR` 退出码 + 输出行、Pact 消费者契约与 `can-i-deploy` 闸门、容忍读取验证（R-5）；无对外契约的单体工具标「不适用」 |
| **处理个人数据 / PII / 用户生成内容、有隐私政策或合规要求**（v1.3） | `references/privacy-compliance-testing.md` + `assets/privacy-matrix-template.md` | 字段级 PII 分类 + 读接口响应白名单比对、批量分配、删除权端到端验证、日志脱敏核查（R-6）；不处理 PII 的纯技术工具标「不适用」 |
| **有 CI / 测试套件 / 发布流程，需量化测试有效性或成本收益**（v1.3 / v1.4） | `references/test-effectiveness-testing.md` + `assets/test-effectiveness-template.md` | DORA 四指标（CFR/MTTR）、缺陷逃逸率、flaky 配额与 quarantine、变异得分对照覆盖率、§5A 测试经济性/ROI；结论支撑 Go/No-Go；无自动化测试标「无测试度量基础」 |
| **有 UI / 交互 / 表单 / 认证，或声称 WCAG 2.2 AA / 支持读屏**（v1.4） | `references/accessibility-testing.md` + `assets/accessibility-matrix-template.md` | 版本与级别口径、axe violations + `incomplete` 人工复核、完整键盘路径、至少一组读屏组合逐项标注、2.4.11/2.5.8/3.3.8 实测（R-7）；无 UI 的 CLI/库标「不适用：无图形交互界面」 |
| **有移动端 / 桌面端 / 多浏览器用户，或声称移动端可用 / 真机验过**（v1.4） | `references/cross-platform-testing.md` + `assets/device-matrix-template.md` | 设备矩阵来源与覆盖占比、`real`/`emulator`/`browser-emulation` 载体标注、多内核与长尾条目、端侧特有面与网络档位、发布门禁真机证据（R-8）；纯后端 API/CLI 标「不适用：无终端形态差异」 |
| **有测试报告 / 发布验收 / CI 门禁需结论可复核，或声称「符合 SOC2 / 等保 / SSDF」「已通过审计」「证据链完整」**（v1.5） | `references/evidence-chain-audit.md` + `assets/evidence-chain-template.md` | 三级引用链（结论→证据文件→原始输出）逐条可解析、证据 `sha256` + `subject.commit`/环境/时间窗、`scripts/evidence-audit.py` 自动对账与缺口清单、合规声明→控制项→证据映射与未映射声明、审计导出件自身 hash（R-9）；一次性探索、无留档要求标「不适用：无留档要求」 |
| **有视觉快照基线 / install-base 导出数据，或要按真实安装量定设备矩阵**（v1.5） | `references/cross-platform-testing.md` §6A + `scripts/device-matrix.py` + `assets/device-matrix-template.md` | 基线环境指纹与 `--update-snapshots` 留痕、`maxDiffPixels`/`mask`/`threshold` 变更批准；本地 CSV/JSON 导出的占比/累计/80% 截断点与 CrUX 口径声明，载体列人工填（R-8 增强，不新增规则） |

路由结果写进阶段 2 的计划，避免"不管什么项目都同一套用例"。**叠加项按触发条件选，不是所有项目都做**；无日志埋点、无外部依赖、单存储的项目对应专项标「不适用」并写明原因，别为凑维度造测试。

> **路由闭环（v1.2）**：本表与 `SKILL.md` 的「横向叠加项」必须成对出现——每份专项手册在两处都有触发条件，`scripts/selfcheck.py` 会逐份核对，缺一处即判「孤儿文档」并 FAIL。L1 元手册（`dissect.md` / `tools.md` / `personas.md` / `test-design.md` / `memory-tree.md` / `evolution.md` / `self-evolution.md` / `quality-gates.md`）对所有项目都读，不要求在本表出现。

## 产出格式

解剖结束时应能填出：

```
栈：___　入口：___　启动命令：___　测试命令：___
功能清单：P0: ___ / P1: ___ / P2: ___（附风险分，见 test-design.md §4）
宣称 vs 实际差异：___（无则写"一致"）
测试设施：框架___ 规范文件___ CI___ E2E___
攻击面：认证位置___ 对象ID___ 配置/密钥___
观测面：结构化日志___ trace_id/request_id___ 健康检查___（无则写"缺口"）
依赖拓扑：DB___ 缓存___ 队列___ 第三方API___；各自 timeout/重试/降级/幂等 ___
交付链（v1.2）：lockfile___ 产物/镜像___ SBOM/签名___ CI 可绕过?___（无则写"不适用：无构建产物"）
locale 面（v1.2）：支持 locale___ 资源文件___ RTL___ 格式化调用___（单 locale 写"最小检查"）
租户边界（v1.2）：标识来源___ 隔离策略___ 共享资源___ platform admin___（单租户写"不适用"）
无障碍面（v1.4）：交互控件___ 认证方式(有无认知测试)___ 焦点/ARIA___ 目标尺寸___ 声明级别___（无 UI 写"不适用"）
设备形态面（v1.4）：支持OS/内核___ 屏幕形态___ install-base 数据可得?___ 真机/设备云___（纯后端写"不适用"）
证据链面（v1.5）：留档要求___ 合规声明清单___ 原始输出落点___ commit/环境/时间窗可得?___ 视觉基线___ install-base 本地导出___（无留档要求写"不适用"）
能力层路由：___（对应手册 ___；v1.1/v1.2/v1.3/v1.4/v1.5 叠加项 ___，不适用原因 ___）
风险初判：___（如"无任何输入校验""秘密硬编码""无链路埋点""下游调用无 timeout""客户端 tenant_id 直取""浮动依赖版本"）
```
