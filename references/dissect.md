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
| Dockerfile | 任意（容器化） | ENTRYPOINT、EXPOSE 端口 |

混合项目 / monorepo：对每个子目录（packages/、apps/、services/）重复此表，逐个记录。

## 2. 入口追踪

- README 的 quickstart 命令 → 那就是真实入口，优先级最高
- Web 服务：路由定义处（routes/、router/、controllers/、urls.py、app.py 的路由装饰器）
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

## 6. 测试设施盘点（v1.0 新增）

解剖时顺手记录「项目已经有什么」，决定阶段 3 是复用还是降级：

| 找什么 | 在哪看 | 影响 |
|---|---|---|
| 测试框架与脚本 | `package.json scripts`、`pyproject.toml`、`Makefile`、`*_test.go` | 有就先跑通它的套件 |
| 测试/覆盖率配置 | `vitest.config.*`、`jest.config.*`、`pytest.ini`、`coverage` 字段 | 覆盖准则的口径来源 |
| 契约/规范文件 | `openapi.yaml`、`swagger.json`、`*.graphql`、`*.proto` | 有规范就可上 schemathesis / 契约测试（`api-testing.md` §7） |
| 性能脚本 | `k6/`、`*.js` with `import http from 'k6/http'`、`locustfile.py` | 有基线就直接对比 |
| E2E 与 fixtures | `playwright.config.*`、`tests/seed.spec.ts`、`specs/*.md` | Playwright Test Agents 是否已初始化（`ai-native-testing.md` §2） |
| CI 配置 | `.github/workflows/*`、`.gitlab-ci.yml`、`Jenkinsfile` | 质量门禁现状（`quality-gates.md` §6） |
| 依赖锁文件 | `package-lock.json`、`poetry.lock`、`go.sum` | 依赖审计能否跑 |

## 7. 攻击面与配置指纹（v1.0 新增）

一眼扫出高风险区，直接喂给测试矩阵的安全维度：

- **认证/鉴权位置**：中间件顺序（request-id → logging → CORS → ratelimit → body → auth → authz → validation → handler）
- **输入边界**：所有 `req.body` / `req.query` / 文件上传 / webhook / callback 字段 → 注入与 SSRF 候选
- **对象 ID 来源**：路径参数 `:id` 是否只凭 ID 取数据 → BOLA 头号嫌疑（`security-testing.md` API1）
- **配置**：`.env.example` 是否存在、`CORS` 是否 `*`、是否有 `/health` `/ready`、是否有调试端点
- **密钥**：`git grep -nEi '(api[_-]?key|secret|password|BEGIN .*PRIVATE KEY)'`
- **影子端点**：`/v1/` 与 `/v2/` 并存、`/debug`、`/swagger`、`/actuator`

这些是**静态也能做的测试**，项目跑不起来时尤其有价值。

## 8. 项目形态 → 能力层路由（v1.0 新增）

| 形态 | 主用手册 | 必做动作 |
|---|---|---|
| REST / GraphQL / gRPC 服务 | `api-testing.md` + `security-testing.md` | 端点矩阵、认证授权矩阵、错误契约、幂等 |
| 全栈应用（前后端） | `fullstack-integration.md` + `frontend-testing.md` | 构建/冒烟/CORS/auth 携带 + 五态矩阵 |
| 纯前端 / 静态页 | `frontend-testing.md` | 五态、a11y、窄屏、无占位资源、CWV |
| CLI / 脚本 / 库 | `tools.md` + `test-design.md` | 退出码、`--help`、边界值、属性测试不变量 |
| LLM / Agent / RAG 应用 | `ai-native-testing.md` | 评测集、蜕变关系、注入、工具权限、非确定性 |
| 上线前验收 / 发布 | `fullstack-integration.md` §6 + `quality-gates.md` | 六门禁 12 分打分、Go/No-Go |

路由结果写进阶段 2 的计划，避免"不管什么项目都同一套用例"。

## 产出格式

解剖结束时应能填出：

```
栈：___　入口：___　启动命令：___　测试命令：___
功能清单：P0: ___ / P1: ___ / P2: ___（附风险分，见 test-design.md §4）
宣称 vs 实际差异：___（无则写"一致"）
测试设施：框架___ 规范文件___ CI___ E2E___
攻击面：认证位置___ 对象ID___ 配置/密钥___
能力层路由：___（对应手册 ___）
风险初判：___（如"无任何输入校验""秘密硬编码"）
```
