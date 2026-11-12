# API 契约演进兼容性测试（阶段 3 · 横向叠加）

> 蒸馏自 `oasdiff`（OpenAPI 破坏性变更检测）、Pact 官方文档（消费者驱动契约 / can-i-deploy）、Zalando RESTful API Guidelines、SemVer 规范；v1.4 追加影子流量 / 只读镜像比对的工程实践（§3A）。`oasdiff` 与 Pact 的命令原文见 `CHANGELOG.md` v1.3.0；影子流量来源与口径诚实标注见 `CHANGELOG.md` v1.4.0。
> 定位：前面所有手册测的是「当前这一版对不对」；本手册测的是「**改了之后老客户端会不会挂**」。一次看似无害的 schema 改动，可能让所有老版本 App 全部 500——这正是兼容性测试的专属命题。

## 0. 适用边界与分工

| 触发 | 叠加本手册 | 不适用 |
|---|---|---|
| 项目有 OpenAPI/Swagger 规范、GraphQL schema、gRPC proto，且有多个客户端/版本在跑 | 是 | 纯内部一次性脚本、无对外契约的单体工具 → 只写「未做契约演进验证」，不得写「向后兼容」 |
| 已上线且需持续迭代（尤其是移动端 App 与后端分离） | 是 | 一次性 demo、无版本概念 → 标注缺口 |
| 只关心「这一版功能对不对」 | 去 `references/api-testing.md` | 本手册不重复功能正确性用例 |

**三条认知打底**（官方原文，最容易自欺）：
1. **「本地能跑」≠「老客户端还能调」**：后端加了个 required 字段，新代码能跑，但所有没升级的老 App 直接 400/500。
2. **「没改接口路径」≠「没改契约」**：响应里多返回了一个字段看似无害，但若删掉了一个字段、把整数改成字符串、把数组改成对象，老客户端解析就崩。
3. **「双方都用同一份规范」≠「双方都遵守」**：只有一方（消费者）真正用到的那部分字段才算契约；Pact 的核心就是「只测实际被用到的那部分通信」。

## 1. 兼容性四类问题（先定性再定量）

| 问题 | 含义 | 严重性 |
|---|---|---|
| **向后不兼容（Breaking）** | 老客户端按旧契约调用会失败 | 必须阻断发布 |
| **兼容扩展（Compatible addition）** | 新增字段/端点，老客户端无感 | 允许，但需消费者容忍 |
| **弃用（Deprecation）** | 字段/端点将移除，需给过渡期 | 必须公告 + 留过渡窗口 |
| **消费者契约偏离** | 实际用法与规范/提供方不一致 | 隐性风险，靠契约测试兜底 |

> 兼容性判定必须与 **语义化版本（SemVer）** 对齐：MAJOR = 向后不兼容，MINOR = 向后兼容的「新增」，PATCH = 向后兼容的缺陷修复。API 路径里的 `/v1/` 只表示「大版本族」，不等于每个 minor 变更都换路径。

## 2. OpenAPI 破坏性变更检测（oasdiff，CI 门禁首选）

`oasdiff` 直接对两份规范做 diff 并判定 breaking，支持 OpenAPI v2 与 v3。

```bash
# 安装
go install github.com/oasdiff/oasdiff/cmd/oasdiff@latest

# 破坏性变更检测（默认 exit code 非 0 即存在 breaking）
oasdiff breaking base.yaml revision.yaml
oasdiff breaking base.yaml revision.yaml --format text

# CI 门禁：只在 ERR 级别阻断（把 WARN 留作告警）；WARN 也阻断则用 --fail-on=WARN
oasdiff breaking base.yaml revision.yaml --fail-on=ERR

# 变更日志 / 纯 diff（用于人工评审变更范围）
oasdiff changelog base.yaml revision.yaml
oasdiff diff base.yaml revision.yaml
```

**判定 breaking 的常见类别**（来自 oasdiff 官方规则集，CI 里以 `--fail-on=ERR` 的退出码为准，不要自己拍脑袋）：
- 删除路径 / 操作（GET/POST…）/ operationId
- 新增 **必填** 请求参数、请求体属性、或把可选参数改为必填
- 删除响应、删除响应中的属性、把属性改为必填
- 变更参数/属性 **类型**（如 integer→string）、格式（int32→int64）、或把 `nullable` 改掉
- 收窄枚举（删除某个 enum 值）、把数组改成单值或反之
- 变更认证方式、变更 `additionalProperties` 限制、删除 callback
- 把响应码语义改掉（如 200 改成 201 且老客户端只认 200）

> 口径：以 `oasdiff breaking --fail-on=ERR` 的**退出码与原文输出**为证据，不要只截图 changelog。缺少历史规范时，用「当前规范 vs 上一次发布 tag 的规范」做 baseline，而非 vs 空文件。

## 3. 消费者驱动的契约测试（Pact）

核心思路：**契约由消费者（client）定义**——它只声明「我实际会用到的字段和交互」，提供方据此验证自己仍然满足。这样即便提供方响应里多出几十个字段，只要消费者要的那几个没变，契约就通过。

```
消费者侧：写期望（Pact 文件）→ 跑消费者测试生成契约 → 发布到 Pact Broker
提供方侧：拉取契约 → 用真实 provider 状态验证 → 回写验证结果到 Broker
部署门禁：can-i-deploy 查「我的版本 + 所有依赖契约都验证通过了吗」
```

```bash
# 提供方验证（示意；具体 CLI 随语言 provider 而定，命令以官方为准）
pact-provider-verifier --pact-urls=./pacts/consumer-provider.json

# 部署闸门：本版本能否部署到某环境？
pact-broker can-i-deploy \
  --pacticipant <consumer-or-provider-name> \
  --version <git-sha-or-semver> \
  --to-environment <prod|staging>
# 退出码非 0 → 存在未验证通过的契约依赖 → 禁止部署
```

**要点**：
- 「only test the parts of the communication that are actually used」——契约只覆盖消费者真实使用的字段，避免过度约束。
- `can-i-deploy` 把「版本 + 环境 + 依赖契约验证结果」绑在一起判定，比「我本地跑通了」可靠得多。
- 契约文件本身要随版本留存，作为「某天某客户端依赖了哪些字段」的法定证据。

## 3A. 影子流量 / 只读镜像比对（v1.4 增强，落地顺延提案）

> 定位：oasdiff / Pact 验的是**双方声明的契约**，影子流量验的是**真实请求下新旧实现的行为差异**。两者互补，不互相替代。

**三条硬约束**：
1. **不得影响真实用户**：镜像流量走旁路，比对响应不返回给调用方；原链路的 p95 与错误率必须无变化。
2. **不得引入写副作用**：只对只读路径做影子比对；含写操作的路径须用合成账号 + 隔离环境，并在报告写明「未在生产写路径做影子比对」。
3. **脱敏与采样先于比对**：PII / token 在镜像前脱敏；写明采样率、时间窗、请求去重口径。

| 步骤 | 动作 | 判据 |
|---|---|---|
| S-1 | 选定只读路径与采样率，记录时间窗 | 采样口径写进报告，不写「全量比对」 |
| S-2 | 镜像一份请求到新实现（原链路不受影响） | 原链路 p95 / 错误率无变化 |
| S-3 | 响应规范化后比对（忽略时间戳、随机 id、无序集合的排序差异），列出 diff 分类 | 每类 diff 有「预期 / 缺陷 / 待确认」结论 |
| S-4 | 有派生状态（缓存 / 事件 / 读模型）时核对一致性 | 派生状态差异不静默忽略 |
| S-5 | 与 Pact 契约结果交叉验证 | 契约绿但影子 diff 有非预期项 → 回看契约覆盖缺口 |

**口径诚实标注**：本技能不绑定具体影子流量产品；Istio `mirror`、Envoy shadow、Diffy 类响应 diff 工具、服务网格/网关的流量复制都是可选实现，命令以各自官方文档为准，手册**不臆造参数**。无网关/无镜像能力时写「未做影子流量比对」并标 `BLOCKED`，不得写成「已验证线上行为一致」。

> 与 R-5 的关系：R-5 证据仍以 oasdiff 退出码 + 消费者契约 + 容忍读取为准；影子流量是**增强证据**，不单独构成 R-5 通过。

## 4. 兼容演进规范（Zalando 准则 + 容忍读取）

| 规则（Zalando RESTful API Guidelines，精简转述） | 测试动作 |
|---|---|
| **MUST NOT break backward compatibility**：变更不得破坏已有客户端 | 用 §2 的 oasdiff 量化，而非主观判断 |
| 客户端 **MUST 容忍兼容扩展**（忽略未知字段 / 新端点） | 响应里塞一个消费者从未见过的字段，老 mock 仍应解析成功（tolerant reader 验证） |
| API 版本放 **URL 路径** `/v1/` 而非 header（便于缓存与调试） | 核对路由前缀与文档一致 |
| **弃用要公告**：标记 deprecated、指定过渡期、公开后继版本 | 查 deprecation 标注与公告，确认过渡窗口 > 老客户端最大更新周期 |

**容忍读取（Tolerant Reader）最小验证**：
```bash
# 在响应里人为追加一个未知字段，确认消费者/解析层不报错（仅当无法跑真实老客户端时做静态审查）
# 真实做法：用老版本客户端 SDK 对新响应做反序列化，断言不抛异常
```

## 5. 测试卡（C-1 ~ C-12）

| # | 测试动作 | 通过判据 | 常见失败 |
|---|---|---|---|
| C-1 | `oasdiff breaking base revision --fail-on=ERR` | 退出码 0 | 任意字段删除/类型变更/required 新增 |
| C-2 | `oasdiff changelog` 审查变更范围 | 无未预期的 breaking 项 | 隐性 breaking（枚举收窄）被忽略 |
| C-3 | 旧客户端/老 SDK 对**新响应**反序列化 | 不抛异常、忽略未知字段 | 老客户端解析新结构崩溃 |
| C-4 | 新增 required 字段的迁移 | 老请求（缺该字段）仍被兼容处理或明确 400+文档 | 老请求直接 500 |
| C-5 | 枚举/常量变更 | 移除的值无老客户端仍在使用（用 Pact 契约佐证） | 删掉老客户端依赖的枚举值 |
| C-6 | Pact 消费者契约覆盖核心交互 | 提供方 verify 全绿，Broker 记录验证结果 | 提供方改了字段但契约未拦住 |
| C-7 | `can-i-deploy` 闸门 | 目标环境退出码 0 | 依赖契约未验证通过即放行 |
| C-8 | 路径版本与文档一致 | `/v1` 实际存在且语义匹配 | 文档写 v2 代码还是 v1 |
| C-9 | 弃用字段/端点有公告与过渡期 | deprecation 标注 + 后继版本 + 窗口 > 客户端更新周期 | 静默删除 |
| C-10 | SemVer 与变更性质对齐 | breaking→MAJOR、扩展→MINOR、修复→PATCH | 破坏性变更只升了 PATCH |
| C-11 | 契约文件随版本归档 | 每个发布 tag 有对应 Pact/规范快照 | 无法追溯「那天依赖了哪些字段」 |
| C-12 | 非 REST 契约（GraphQL/Proto）同样做演进检查 | GraphQL schema 用 schema registry 比对、proto 用 `protoc --validate`/兼容性工具 | 只测 REST 漏掉 gRPC/GraphQL 破坏性变更 |

## 6. R-5 契约演进兼容性（可证伪规则，见 SKILL.md）

| 声称 | 必须附的证据 | 不适用时的写法 |
|---|---|---|
| 「API 向后兼容 / 升级可安全部署 / 老客户端不受影响」 | ① `oasdiff breaking --fail-on=ERR` 的**命令原文 + 退出码 + 输出行**（baseline 与修订版明确）；② 若有消费者，Pact verify 绿 + `can-i-deploy` 目标环境退出码 0；③ 容忍读取验证（老客户端对新增字段不报错） | 无对外契约的单体工具、纯内部一次性脚本、无版本概念的 demo → 只写「未做契约演进验证」，**不得**写「向后兼容 / 老客户端不受影响」 |

推论：**「本地新代码能跑」不能推出「老客户端不挂」**。缺 baseline 规范时，用「上一发布 tag 的规范」作 base，不得对空文件 diff 后声称无 breaking。

## 7. L0 零依赖降级路径（工具全缺也能走完）

```bash
# 无 oasdiff 时，用结构化 diff 逐字段比对（只能查明显删除/重命名，无法替代语义判定）
diff <(grep -oE '"[^"]+":' base.json | sort) <(grep -oE '"[^"]+":' revision.json | sort)
git show <last-release-tag>:openapi.yaml > /tmp/base.yaml   # 取上一版作 baseline
git grep -n "deprecated" -- openapi.yaml                     # 查弃用标注
git log --oneline -L '/openapi.yaml/'                        # 看契约变更历史
```

降级时报告固定写一行：「本轮仅做**静态契约比对**（diff + 历史审查），**未跑 oasdiff/Pact 语义判定**，结论降级为待确认」，并标 `BLOCKED` 而非 Pass。

## 8. 报告字段与分工

用 `assets/contract-evolution-matrix-template.md` 记录：baseline 与修订版来源、oasdiff 输出与退出码、Pact 契约覆盖与 verify 结果、can-i-deploy 闸门、容忍读取验证、R-5 结论、不适用声明。

| 主题 | 去哪 |
|---|---|
| 当前版本功能正确性、认证授权、错误契约 | `references/api-testing.md` / `security-testing.md` |
| 非 REST 协议端点矩阵 | `references/protocol-testing.md` |
| 制品/依赖是否被篡改（与契约分属不同维度） | `references/supply-chain-testing.md`（R-3） |
| 全局 Go/No-Go | `references/quality-gates.md` §3（R-5） |
| 工具与降级 | `references/tools.md` |
