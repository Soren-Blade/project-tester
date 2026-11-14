# 全局测试经验（跨项目，持续进化）

> 阶段 0 读这里开局生效；阶段 4 有新通用教训就追加。一行一条：`[标签] 教训 — 应用：怎么用`。超 40 行修剪旧条目。
> v1.1 治理：本轮做了一次 **Merge** —— 与新增手册重复的条目改写为交叉引用（不二次抄写），新蒸馏条目本轮不归档，下轮按实际使用情况裁剪；提案区两项已按「已吸收 / 已驳回」结案并留理由。

## 环境类

- [环境] Windows/Git Bash 下路径含空格必须引号，统一用 /d/xxx 形式 — 应用：所有 shell 命令先检查路径引号
- [环境] python 与 python3 因机器而异 — 应用：先 `command -v python python3` 探测再调用
- [环境] Node ≥18 自带 `node --test`，零依赖可写单测 — 应用：项目无测试框架时的第一降级手段
- [环境] Git Bash 控制台把 UTF-8 中文显示成乱码（GBK 控制台所致），非服务端 bug — 应用：curl 输出中文乱码时先 `| xxd | head` 验字节再下结论

## 流程类

- [流程] 先跑项目自带测试套件再自己动手 — 应用：解剖阶段探测出的测试命令最先执行，红了先分清是"本来就坏"还是"环境问题"
- [流程] README 宣称与代码实际的差异是高产地 — 应用：解剖时必做两列对照，差异即测试点
- [流程] 每个失败结论必须当场留证据（命令+输出） — 应用：测试中即时记录，事后回忆必失真
- [流程] 证据不足只能降级为「待确认」，不许用"没报错"冒充"没问题" — 应用：见 SKILL.md 的 R-1/R-2 可证伪规则

## 手法类

- [手法] Express/Flask 类服务默认几乎不校验输入 — 应用：空 body、错误类型、超长字段优先打
- [手法] 空输入直接回车是最便宜的 bug 探针 — 应用：每个表单/接口第一步就试空提交
- [手法] 负数与零是数值字段的高频漏网鱼 — 应用：所有金额/数量/分页参数必测 0 和 -1

## API / 契约类（v1.0 蒸馏）

- [手法] 对象 ID 来自客户端且服务端只凭 ID 取数 → BOLA 是头号嫌疑 — 应用：每个 `:id` 端点补一条越权用例（OWASP API1:2023）
- [手法] 错误响应应带 `Content-Type: application/problem+json`，`status` 成员与实际 HTTP 码一致 — 应用：所有 4xx/5xx 抽查这两个判据（RFC 9457）
- [手法] 把 500 当"参数错误"记下来是漏报，500 永远是 bug — 应用：异常参数矩阵里单独统计 5xx 数量
- [手法] 有 OpenAPI 就先跑 schemathesis 再手写用例，它自带最小 curl 复现 — 应用：解剖阶段发现 openapi.json 时优先执行
- [手法] 分页合并后的集合应等于全量集合 — 应用：用蜕变关系测分页，无需预知总数
- [手法] 写操作的"响应 + DB"双重断言已升级为**三重断言**（响应 + 权威库 + 派生状态） — 应用：细则见 `references/data-integrity-testing.md` §1，本处不重复抄写

## 安全类（v1.0 蒸馏）

- [安全] 批量分配（请求体塞 role/price/user_id）与过度暴露（响应带 password/hash）同属 API3 — 应用：每个写接口测多余字段，每个读接口查响应白名单
- [安全] 静态审查也能出结论：`.env` 是否入库、密钥硬编码、`CORS: *`、废弃 `/v1/` 与 `/debug` 在线 — 应用：项目跑不起来时用 `git grep` + 路由盘点兜底
- [安全] 疑似密钥/漏洞写"待确认"，不写"已泄漏" — 应用：静态扫描结论一律标注推定性质
- [流程] 认证授权矩阵按「匿名/本人/他人/管理员」四列填满再逐格实调 — 应用：API 项目计划阶段先画矩阵；非 REST 的落点见 `references/protocol-testing.md` §5

## 性能类（v1.0 蒸馏）

- [手法] 平均值会骗人，必须报 p50/p95/p99 + 样本数 — 应用：任何"挺快"的结论都要补分位数
- [手法] 并发数 ≈ 吞吐(RPS) × 平均响应时间(s)（Little's Law） — 应用：反推该压多少 VU
- [手法] 一个请求发出几十条 SQL 是 N+1 的最快信号 — 应用：开 query logging 数查询条数
- [流程] 本机 localhost 结果不代表生产，报告必须写局限 — 应用：性能段落固定附一行"无网络延迟/数据量差异"
- [安全] 压力/浸泡/尖峰只在隔离的授权环境做 — 应用：默认只跑冒烟 + 轻量负载，禁止打外部服务

## 前端 / 全栈类（v1.0 蒸馏）

- [手法] 前端最高产的检查是五态矩阵（loading/empty/error/success/partial），缺一态即 bug — 应用：用 route 拦截 mock 出 500/空/延迟
- [手法] 4xx 不自动重试、5xx 最多 3 次退避重试 — 应用：逐状态码核对前端错误映射
- [手法] 占位资源 URL 与引用不存在的本地媒体是静态可查的硬失败 — 应用：grep unsplash/picsum/placeholder 并逐个核对媒体文件
- [流程] 集成测试用真 DB（事务回滚/testcontainers），只有单测才 mock repository — 应用：别把"跑得飞快"当成"验到了"
- [流程] 回滚预案没演练过就等于没有；"CI 过了"不等于六门禁过了 — 应用：发布验收逐门留证据再打 12 分

## 有效性 / AI 类（v1.0 蒸馏）

- [手法] 高覆盖率 + 低变异得分 = 一堆假测试 — 应用：核心模块抽查断言强度
- [工具] 给 CI 加 `retries: 3` 不是修 flaky，是把不确定性藏起来 — 应用：先定位共享状态/异步等待/外部依赖
- [AI] Playwright healer 让测试变绿不等于 bug 被修了 — 应用：任何 AI 改过的断言都做人工 diff 复核
- [AI] 「用 AI 写测试」与「测 AI 系统」方法完全不同 — 应用：先判能力层，后者改用不变量/蜕变关系/评测集
- [AI] 非确定性系统单次观测不构成结论 — 应用：同 prompt ≥5 次采样，报样本数与分布
- [流程] 静态记录 ≠ 评测准备度 ≠ 运行时质量 ≠ 发布批准 — 应用：文件数量增加只证明第一种

## 链路 / 可观测性类（v1.1 蒸馏）

- [手法] 同一请求的 span 共享 `trace_id`，中间服务必须转发 `traceparent` 否则链路断 — 应用：自定义 traceparent 发请求后 grep 同一 id，跨 ≥2 组件才算贯通（W3C Trace Context）
- [手法] 日志/span 属性里出现完整 token、PII 或请求体即为 S2 缺陷 — 应用：链路断言同时做脱敏检查
- [手法] SLI 按分布（p95/p99）而非平均值；SLO 必须写清 good/valid events 与时间窗 — 应用：把"99.9% 可用"改写成可计算比例，否则不可证伪（Google SRE）
- [流程] 错误预算耗尽时即使功能全绿也 No-Go — 应用：发布报告并列「实测 SLI / SLO / 预算余量」三列
- [手法] 单次 200 不代表副作用发生 — 应用：用 span 通配断言（所有 db span <100ms、MQ publish 存在）抓静默失败
- [流程] 无埋点/无日志时只能写「可观测性缺口」 — 应用：R-1 例外场景直接降级为待确认，不得判 Pass

## 韧性 / 故障注入类（v1.1 蒸馏）

- [流程] 稳态假设必须是可测量输出（成功率/p95/积压），不是 `/health` 200 — 应用：注入前后各采样 30s 并留对照组（Principles of Chaos）
- [流程] 实验目的是**证伪**假设，不是"证明很稳" — 应用：结论写「本次未被证伪」，别写「高可用」
- [安全] 故障注入只在隔离授权环境，先写死中止条件与回滚 — 应用：禁止打外部服务/生产；注入后必须撤销并验证恢复
- [手法] 恢复验证最容易漏 — 应用：撤销后核对指标回基线、无残留连接/积压/脏数据、记录恢复时长
- [手法] 4xx 不重试、5xx 退避 ≤3 次、上限进死信 — 应用：mock 永不返回的依赖，用 `time curl` 验 timeout 真的生效
- [流程] 一次演练不足以宣称韧性 — 应用：R-2 要求附注入点/时长/爆炸半径/稳态前后值/恢复时长（模板见 `assets/resilience-runbook-template.md`）

## 数据一致性类（v1.1 蒸馏）

- [手法] 只在空库上测迁移等于没测 — 应用：用类生产数据量的合成数据跑 `up → down → up` 并对照行数/NULL 数
- [手法] PG 默认 Read Committed 允许不可重复读/幻读/序列化异常 — 应用：并发扣减后核对不变量（库存≥0、总金额守恒）而非只数错误
- [手法] 不变量比期望值更好用 — 应用：分页合并=全量、订单数=事件数、总金额守恒，无需预知正确结果
- [流程] 缓存无 TTL 或写后不失效即缺陷 — 应用：写→读→再读 + 过期后读，四步核对
- [手法] 后台任务不能假定"恰好一次" — 应用：同一 job 手动执行两次，结果必须一致

## 非 REST 协议类（v1.1 蒸馏，吸收 #1 提案）

- [手法] GraphQL 常恒返 200，错误在 `errors[]` — 应用：断言同时看 `data` 与 `errors[]`，别把 200 当通过（OWASP GraphQL CS）
- [安全] GraphQL 授权必须落到每个 resolver，`node`/`nodes` 也要查 — 应用：换 id 越权用例逐个 field 打
- [手法] batching / 深层嵌套可在 1 个请求里放大成本 — 应用：限流按 query cost 与操作数，不只按请求数
- [手法] gRPC 无凭证是 `UNAUTHENTICATED`、越权是 `PERMISSION_DENIED`、超限是 `RESOURCE_EXHAUSTED` — 应用：逐 method 核对码映射（grpc.io）
- [手法] `DEADLINE_EXCEEDED` 时服务端可能已成功 — 应用：超时后查库验证幂等，别直接重试写操作
- [流程] WS/SSE 只在握手鉴权不够 — 应用：换频道/room 测消息级越权，并验心跳、重连退避、`close` 退订

## 交付链 / 制品完整性类（v1.2 蒸馏）

- [手法] 组件没出现在 SBOM 里 ≠ 软件里没有它 — 应用：SBOM 必须写覆盖缺口声明，manifest 与最终制品要对账（OWASP Dependency Graph & SBOM CS）
- [安全] 签名有效只证明声明的来源与完整性，不证明软件安全或 SBOM 准确 — 应用：报告写「该声明来源与完整性已验证」，禁止升级成「无漏洞」
- [流程] SBOM 的生成与消费、provenance 的生成与验证必须成对自动化 — 应用：只做一半就标 BLOCKED，不算 R-3 通过
- [手法] `npm ci` 在 package.json 与 lock 不一致时报错且不写回 lock — 应用：CI 用冻结安装，装完 `git diff --exit-code -- <lock>` 验未被改写
- [流程] 「Silencing the scanner or bumping a version string is not remediation」 — 应用：补丁验证必须在未打补丁版本失败、打补丁版本通过，两种结果都留日志
- [流程] 逐条核验的是 SLSA **v1.0** 的 levels/provenance/verifying-artifacts — 应用：OWASP 页面引 v1.2 链接时不要写成「已核验 v1.2」，口径要诚实

## 国际化 / 本地化类（v1.2 蒸馏，吸收 #1 提案）

- [手法] 伪本地化 `can never catch all issues` — 应用：结论只写「本次伪本地化未发现 X 类缺陷」，不写「多语言没问题」（Microsoft Learn）
- [手法] 伪串没出现的地方就是硬编码串 — 应用：全量跑伪本地化版，专找截断/拼接/未外部化/图片内嵌文字/同串复用
- [手法] base direction 用 HTML `dir` 而非 CSS，`lang` ≠ 方向 — 应用：静态查 `<html lang="ar" dir="rtl">`、logical properties、`dirname`、`<bdi>`，再真实渲染验镜像（W3C）
- [手法] Turkish dotted/dotless `I` 与 `côte < coté` 说明排序不能按 Unicode 码点 — 应用：排序/搜索/大小写转换都调带 locale 的 collator，禁用裸 `sort()` / `toUpperCase()`
- [流程] 数据互通要跨 app language × OS language 双向验 — 应用：F-2 DST 边界、F-5 CSV 分隔符、F-6 跨语言读写各留一条往返证据
- [手法] tofu（字形缺失方框）是缺陷，静态 grep 出 `dir` 不等于 UI 已镜像 — 应用：字体回退与 RTL 布局必须真实渲染验证

## 多租户隔离类（v1.2 蒸馏）

- [安全] 客户端传的 tenant identifier 只是 selector，不是授权凭证 — 应用：改 header/query/body/token claim/message field 逐条打，服务端 membership 必须拒绝（OWASP Multi-Tenant Security CS）
- [手法] 参数化 SQL 防注入不防跨租户访问 — 应用：夹具用 T1/T2 **相同 ID**，否则越权会碰巧返回空被误判为通过
- [流程] 一条 `404` 不构成隔离通过 — 应用：cache/queue/search/audit/backup/admin 每条 tenant-owned path 都要否定路径证据（R-4）
- [手法] 共享 queue/topic、对象 prefix 都不是授权边界 — 应用：Q-2 producer 伪造 tenant_id、F-1 prefix 越权、`tenants/acme/` 尾斜杠删除边界逐个测
- [流程] 连接池复用是高频漏网鱼 — 应用：同一 pooled connection 先 T1 再 T2 再缺 context，验 `SET LOCAL` 而非 session 级 `SET`
- [安全] `FORCE RLS` 不约束 superuser / `BYPASSRLS` — 应用：查**部署环境** `pg_roles.rolsuper`/`rolbypassrls`，别只看源码配置
- [流程] 双租户 backup 恢复必须 restore into a separate resource + selectively recover — 应用：恢复后确认 T2 records absent，禁止把 shared snapshot 覆盖 live data
- [安全] 故意共享与 platform admin 路径要测「exact permitted path 且 no broader access」 — 应用：不能只测拒绝，也要测授权路径不越界

## 契约演进类（v1.3 蒸馏）

- [手法] 「本地能跑」≠「老客户端还能调」——后端加个 required 字段，所有没升级的老 App 直接 400/500 — 应用：有对外契约且多版本在跑时必跑 oasdiff（R-5）
- [手法] `oasdiff breaking --fail-on=ERR` 以退出码为门禁，baseline 必须是上一发布 tag 的规范，不得对空文件 diff 后声称无 breaking — 应用：CI 里接退出码，输出行留证据
- [手法] 消费者定义契约、只测实际被用到的字段；`can-i-deploy` 把版本+环境+依赖验证绑成闸门 — 应用：无 Pact 时用容忍读取（老客户端对新响应不报错）做降级验证
- [手法] SemVer 必须与变更性质对齐：breaking→MAJOR、扩展→MINOR、修复→PATCH — 应用：破坏性变更只升 PATCH 是缺陷，要在 release 评审拦下
- [手法] Zalando「客户端 MUST 容忍兼容扩展」= 响应多返字段老客户端不应崩 — 应用：静态审查时向响应塞未知字段验解析层不抛异常
- [手法] 弃用要公告 + 过渡期 > 老客户端最大更新周期 — 应用：静默删除字段/端点即缺陷，无论代码是否还跑得通

## 隐私与数据生命周期类（v1.3 蒸馏）

- [安全] 接口返回 200 不代表没多给数据 — 应用：每个读接口用普通用户调用，逐字段比对响应白名单，夹带 password/token/证件号即 S1（API3:2023，R-6）
- [安全] 批量分配：写接口塞 `role`/`price`/`userId` 被服务端采信即越权 — 应用：写接口请求体必加敏感字段试探，与 BOLA 是不同维度
- [安全] 「主库删了」≠「全链路删干净」— 应用：删除权验证要覆盖缓存/搜索索引/副本/对外传播，只删主库即缺陷（GDPR Art.17）
- [手法] 日志不得落明文 token/密码/PII，且要防日志注入 — 应用：触发带敏感数据请求后查日志与 span 属性，与可观测性脱敏是同一目标双切面
- [合规] 数据最小化：注册只收邮箱却收身份证即过度采集 — 应用：字段级 PII 分类表是隐私测试的起点，没分类就别写「合规」
- [合规] 隐私政策声明 vs 代码实际行为差异是高产地 — 应用：政策说不收集实际在收集即缺陷（OWASP 隐私 P6/P7）
- [手法] 存储限制：无留存期限/TTL 的长期 PII 留存即缺陷 — 应用：查 PII 字段有无到期清理策略，而非只看加密

## 测试有效性类（v1.3 蒸馏）

- [手法] 覆盖率高 + 变异得分低 = 一堆假测试 — 应用：核心模块抽查变异得分，低分写「覆盖率虚高、杀伤力不足」而非堆覆盖率数字
- [手法] CI 加 `retries: 3` 不是修 flaky，是把不确定性藏起来 — 应用：flaky 率超过 ~2% 告警，修不好就 quarantine 带负责人与解除日期
- [指标] 变更失败率 CFR = 失败部署/总部署（Elite 0–15%），与「用例绿」是两回事 — 应用：发布健康度用 CFR/MTTR 而非单轮测试通过数
- [指标] 缺陷逃逸率 = 生产缺陷/(生产+发布前) — 应用：走高即测试门禁没拦住该类，回看测试设计覆盖准则
- [手法] 非确定性根因：时钟/随机数/外部依赖/共享状态/异步等待 — 应用：定位 flaky 按这五类查，而非无脑重试（Martin Fowler）

## 无障碍可达性类（v1.4 蒸馏）

- [手法] axe 平均只能自动发现约 57% 的 WCAG 问题，且 `incomplete` 需人工复核 — 应用：0 violations 只写「本次扫描未发现」，不得写「符合 WCAG」（Deque axe-core README，R-7）
- [手法] WCAG 2.2 相对 2.1 新增 9 条成功标准，4.1.1 Parsing 已移除 — 应用：先核对验证基线版本，别拿 2.1 清单验 2.2（W3C What's New in WCAG 2.2）
- [手法] 2.5.8 门槛是 24×24 CSS px，44×44 是 2.5.5 的 AAA 增强 — 应用：报目标尺寸时写清条款号与级别，别误引标准
- [手法] 3.3.8 把手动转录验证码视为 cognitive function test，密码管理器/可粘贴属 Mechanism 例外 — 应用：认证流程逐环节查有无替代路径
- [流程] 焦点被 sticky header 整体遮住（2.4.11）不会让任何功能用例变红 — 应用：键盘路径逐步记 `activeElement` 与遮挡判定
- [流程] 读屏结果按 passed/failed/not checked/not present 四类标注，`not checked` 不计入通过 — 应用：至少覆盖一组 reader + browser + OS 组合并留证据（DWP Accessibility Manual）
- [手法] `toMatchAriaSnapshot` 断的是 accessibility tree 而非像素 — 应用：按组件粒度断言，快照变红先判「退化还是文案变化」再决定更新（Playwright）

## 跨端与设备形态类（v1.4 蒸馏）

- [手法] `devices['iPhone 13']` 是一组 viewport/UA/hasTouch 预设，不是真机 — 应用：矩阵逐台标 real/emulator/browser-emulation，仿真绿不得写成真机通过（R-8）
- [流程] 设备矩阵来源应是 install-base analytics 并覆盖约 80% installs — 应用：报告写数据源与时间窗，别拍脑袋列机型；季度复审
- [手法] 低配 Android / 最老受支持 OS / 厂商皮肤 / 折叠屏平板是占比小但出事多的长尾 — 应用：主干之外强制补这四类，未覆盖要显式写
- [流程] 三个 Chromium 套壳不构成跨浏览器覆盖 — 应用：至少覆盖两类真实内核（Chromium / WebKit / Gecko）
- [手法] battery/thermal/sensors/biometrics/real network 只能在真机验 — 应用：发布门禁前至少 1 组 real device 记录
- [流程] 「弱网测过」不是证据 — 应用：每档写上下行/时延数值 + 执行载体 + 观察结果
- [手法] 前后台切换、进程回收、权限「拒绝后不再询问」、旋转折叠、深链冷启动是桌面 Web 用例天然不覆盖的面 — 应用：端侧特有面逐条留输出

## 测试经济性 / ROI 类（v1.4 蒸馏）

- [指标] 成本分建设/运行/维护三类，收益分反馈时间/逃逸避免/优化三类 — 应用：ROI 写清分子分母与时间窗，别只报「自动化率」（`test-effectiveness-testing.md` §5A）
- [流程] 估计值必须标「估计」，不得写成实测账单 — 应用：缺 CI 账单时固定写「成本为估计值」
- [手法] 套件变快但变异得分下降或逃逸率上升 = 负收益 — 应用：报时长收益时同列有效性指标，防止「删用例换速度」
- [流程] ROI 是投入决策依据，不直接阻断单次发布 — 应用：套件时长/维护成本失控时回写 CI 门禁，而非拿 ROI 卡一次上线

## 可复现构建 / 影子流量类（v1.4 蒸馏）

- [手法] 可复现 = 相同 source / build environment / build instructions 重建出 bit-by-bit identical 产物 — 应用：两次干净构建逐位或 hash 比对，三类输入都要留档（Reproducible Builds）
- [流程] digest 不一致必须归因到具体输入，归因不了写「待确认」 — 应用：时间戳、随机排序、绝对路径、并行顺序逐个排查
- [安全] 影子流量只做只读镜像比对，不得影响真实用户或引入写副作用 — 应用：PII/token 先脱敏，写明采样率与时间窗
- [手法] 契约绿但影子 diff 出现非预期项 = 契约覆盖有缺口 — 应用：回看 Pact 交互清单，别把影子流量当 R-5 的替代品

## 证据链与合规声明类（v1.5 蒸馏）

- [流程] 结论 ≠ 证据文件 ≠ 原始输出；报告写「链路完整」却指不到日志那一行，等于不可复核 — 应用：每条结论登记路径 + 可解析锚点 + `sha256` + 采集 commit（W3C PROV-DM，R-9）
- [合规] SSDF 明确「not to create a checklist to follow」；抄一份控制项清单不能写「合规通过」 — 应用：逐控制项挂「评估活动 / 证据锚点 / finding / 缺口声明」（NIST SP 800-218 v1.1）
- [流程] 对账 GREEN 只证明链可解析，不证明软件安全、合规通过或发布批准 — 应用：固定区分静态记录 / 评测准备度 / 运行时质量 / 发布批准四类结论
- [手法] 过期证据比没有证据更危险：采集于旧 commit 的日志会让报告看起来完整 — 应用：PASS 结论必须绑 `subject_commit`，否则判 `stale_evidence` 降为待确认
- [手法] in-toto 的 link file 只记录显式登记为 artifacts 的文件，没登记的原始输出等于不存在 — 应用：证据清单显式登记，不靠事后翻目录补
- [安全] 视觉基线被 `--update-snapshots` 悄悄覆盖等同于证据被替换 — 应用：每次更新留旧/新 hash + 理由 + 批准人（Playwright Visual comparisons）
- [流程] 一次性探索、无留档要求 → 只写「未做证据链对账 / 不适用」，不得写「可审计 / 证据链完整」 — 应用：R-9 例外场景统一降级写法
- [流程] 门禁只统计「段落里出现的编号」会被说明文字蒙混；负向测试打印 GREEN 也可能是副本根本没被破坏 — 应用：门禁只认结构化行（表格行 / 代码块），负向测试先确认破坏确实生效再下结论（v1.5 §7d 加固实证）

## 设备矩阵数据源与 AI 用例有效性类（v1.5 蒸馏）

- [手法] CrUX 是符合条件的真实 Chrome 用户 field data，form factor 仅 `phone`/`tablet`/`desktop`，country 不在 CrUX APIs、ECT 已移除 — 应用：不能据此推机型 / OS 版本 / 非 Chrome 内核分布，也不能当全量人群
- [流程] 设备矩阵草稿必须由本地导出算占比并写数据源与时间窗 — 应用：缺 `--source` / `--window` 就写「未登记」，该草稿不能作为 R-8 矩阵来源证据
- [安全] 采集脚本绝不代填 `real` / `emulator` 载体或写「真机已验证」 — 应用：载体列与实测结论一律人工填（`scripts/device-matrix.py`）
- [指标] AI 生成用例的分母是「入库用例」而非「生成条数」 — 应用：报入库率 / 断言强度合格率 / 变异杀伤贡献 / 假通过率，别只报「生成 200 条」
- [手法] 故意改坏核心逻辑后 AI 生成用例仍全绿 = 假通过 — 应用：E-17 实测，与 `ai-native-testing.md` §3 的自愈陷阱同源
- [流程] AI 改过的断言与视觉基线更新都要人工 diff 并留痕 — 应用：审查记录进 `scripts/evidence-audit.py` 的 manifest，否则 R-9 判缺口

## 特性开关 / 配置 / 灰度类（v1.6 蒸馏）

- [手法] 「功能对」≠「开关隔离对」：feature 对目标群可见 ≠ 对非目标群不可见；灰度 5% 须实测采样而非只写计划值 — 应用：非目标群体必须补否定用例，灰度比例实测与计划值并列（feature-flag-testing.md §2/§3，R-10）
- [安全] 开关默认态/缺失态回退到哪个路径要写成明确假设并验证：配置中心宕机时回退到「开」会把没准备的功能暴露给全员 — 应用：缺省即开是 S1 级缺陷，R-10 要求测 off 态与缺失态（Knight Capital 反例）
- [安全] 废弃/应休眠的开关是高危资产：本以为没人翻的 flag 在灰度里被重新命中，等于多了一条没人测的代码路径 — 应用：每个还活着的废弃开关都要显式验证当前解析为 off 或已移除（SEC 对 Knight Capital 2012 调查口径）
- [手法] env / 文件 / 远程配置三处不一致时，代码跑的是「你没注意到的那份配置」且无报错 — 应用：开关/配置维度先声明优先级再比对，非法值须被拒绝而非静默采纳（FF-7/FF-8）
- [流程] kill-switch 必须经过真关验证：声称「一键关掉」必须附「真关后回到安全态」的证据 — 应用：关态路径从没被执行过的系统，R-10 判缺口而非 PASS（FF-9/FF-12）
- [合规] OSCAL 导出是「同一份证据的另一种编码」，不是新的评估结论 — 应用：`待确认`/缺口到 OSCAL 里仍是 `partial`/`gap`，不得因「有了 OSCAL 文件」写成「已通过 OSCAL 合规评估」（evidence-chain-audit.md §10）

## 测试数据管理类（v1.7 蒸馏）

- [流程] 测试用数据必须可信、合规、可复现，否则再多用例也是沙上筑塔 — 应用：解剖阶段先判数据来源（合成/脱敏/子集/生产），R-11 据此定结论（test-data-management.md §1）
- [手法] 硬编码测试数据 → 用工厂（faker + overrides）；随机库要带固定种子才能复现 — 应用：`faker.seed(42)` / `--seed`，断言"数据可复现"须附同种子两次生成一致性校验（fullstack-dev testing-strategy.md / test-data-gen.py）
- [安全] 连生产库抽数做测试本身是 S1 反模式，即便"只读副本"里的 PII 仍受 GDPR/个保法约束 — 应用：进测试环境前必须脱敏，且脱敏命令原文 + 退出码留证；直接连生产库即判缺陷（test-data-management.md §5）
- [安全] 掩码是启发式（保留格式、替换主体），不保证覆盖全部 PII、不保证不可逆 — 应用：用了 `mask` 子命令不写「数据已脱敏」，须附掩码后残留核查 + 人工复核（test-data-management.md §3）
- [手法] 子集须保引用完整：外键图抽取后悬空外键数必须为 0，否则关联查询会跑出脏数据 — 应用：子集制备后查 `LEFT JOIN ... WHERE fk IS NULL` 计数（test-data-management.md §4）
- [流程] 前端/媒体测试数据的真实感也要可复现：`--seed` 相同提示词产出相同图/音，视觉回归才能比对 — 应用：生成媒体统一带种子，避免每次基线漂移（frontend-dev minimax --seed）

## 身份 / 会话 / 令牌类（v1.8 蒸馏）

- [安全] 登录成功 ≠ 认证安全；令牌可解码 ≠ 可伪造；Cookie 有 HttpOnly ≠ 会话安全 — 应用：R-12 三不认，认证结论只认「负向请求原文 + 响应码 + 登出/改密后重放结果」
- [安全] alg=none、空签名、算法混淆必须实测而不是读代码猜测；RFC 8725 明文只点名 `kid`/`jku`/`x5u`，`x5c`/`jwk` 注入不是其明文条款 — 应用：拒绝 `none` 用请求原文 + 200/401 证据；别把「RFC 没写」当成「不可能被接受」
- [安全] 弱 HMAC 密钥只能证明「命中 N 条字典」，不能证明「必然可爆破」；`jwt-audit.py verify` 只回答签名是否匹配 — 应用：报告写「该值在字典中命中」，不写「密钥可爆破/已被攻破」
- [手法] 登出/改密/重置后必须**同时**重放旧 access 与旧 refresh 两类令牌；只测 access 会漏掉 refresh 继续换新令牌 — 应用：S4/S5 成对用例，缺一列即不算覆盖
- [手法] 重置令牌可预测性先 `base64` 解码看是否含 email/序号/时间戳；`reset_token` 出现在 HTTP 响应里本身就是缺陷（应带外投递）— 应用：F7 双判据（可解码 + 响应暴露）
- [流程] 枚举判定用「三列不可区分」：状态码 + 文案 + 时序；只比状态码不够，时序没测就写「未测」— 应用：F1 至少两列实测，第三列显式标注
- [安全] 认证测试只用自建账号与合成令牌；限流小样本即停；证据里的 `password_hash`/token 截断 — 应用：执行纪律 §6，生产只读且先授权
- [手法] 模拟项目要内建「README 宣称 vs 实现」落差（如宣称过期校验/轮换/HttpOnly/限流），否则测不出「宣称不可冒充」门禁 — 应用：dogfood 种子项目让 README 写全套宣称，报告逐条对账
- [流程] 测试脚本必须自备份/恢复夹具（`users.json`/`notes.json`），并固定 `--now` 判定过期，否则第二次跑结果漂移 — 应用：`finally` 恢复 + 固定 epoch，回归才可比
- [环境] Windows 下 Python 中文输出经 PowerShell 管道会乱码，`Out-File` 还会写 BOM 破坏 JSON — 应用：`$env:PYTHONUTF8=1` + `cmd /c "python ... > out.json"`；读回用 `utf-8` 并跑 `json.load` 验证

## 时间 / 时区 / 备份恢复类（v1.9 蒸馏）

- [手法] 时间缺陷只在「区间过滤 / 调度 / 过期 / 排序」四类动作里现形，显示层往返全绿不代表时间语义正确 — 应用：同一请求用两个时区各打一次，比较返回集合与条数（R-13 T-01/T-02）
- [手法] `+86400` 不是「加一天」；DST 切换日只有 23/25 小时 — 应用：每日任务必须用日历日加减，并实跑 gap/fold 两天的执行次数（cronie：gap 从不匹配、fold 跑两次；`time-audit.py` scan T-05）
- [安全] `exp` 无偏移、`createdAt` 无时区、按字符串选「最新备份」都是跨时区错位源 — 应用：所有时间戳必须带偏移或 Z，比较用解析后的瞬时，禁止字符串排序（`restore-audit.py` RST-01/RST-02）
- [手法] 静态扫描命中只是「可疑写法」，未命中不等于正确；tzdb 会漂移（IANA 2026f 取消古巴 2026-11-01 回拨） — 应用：记录应用/DB tzdata 版本 + 未来三次转换的 offset 对照，不一致即阻塞发布（T-11/T-12）
- [安全] 备份任务成功 ≠ 可恢复；结构校验通过 ≠ 内容完整（restic 默认 `check` 不读数据、borg `check` 只查 CRC、`pg_verifybackup` 仍需 test restore） — 应用：强校验必须出现真读数据的命令与输出原文（R-14 §3.1）
- [手法] 恢复必须对账六类不变量：文件覆盖域 / sha256 / 行数 / max(id) 与序列 / app·schema 版本 / 恢复时刻是否晚于备份 — 应用：`restore-audit.py compare` 的 RST-03~RST-10；缺 hash 也判失败，缺清单数组只报盲区
- [安全] 恢复演练必须在隔离环境做，且恢复点早于备份、旧备份覆盖新库、删中间增量仍成功都是 S1 级 — 应用：先确认恢复环境隔离、再跑恢复、最后冒烟；非空库恢复默认拒绝覆盖
- [流程] 删除权与备份天然冲突：备份里的用户数据不会随主库删除而消失 — 应用：要么 tombstone 重放，要么书面保留期 + 销毁证据（GDPR Art.17），不能写「已删除」了事
- [流程] 恢复后多租户/密钥/配置/外部依赖都要单独验：T2 数据不得出现、密钥不得与备份同机、恢复环境的 TZ 不得默认成 UTC — 应用：把这几项写进 restore drill 模板的交叉项
- [环境] Windows + Python zoneinfo 缺 tzdata 会直接抛 `ModuleNotFoundError`；Node 的 `Intl` 可作独立对照实现 — 应用：脚本缺 tzdb 时明确报错并给 `pip install tzdata` 提示，绝不伪造转换结果
- [流程] 「服务器跑 UTC」不是时区正确的证据：用户本地日边界、DST 调度、日志口径仍可能全错 — 应用：报告分开写「存储口径 / 计算口径 / 展示口径」三行结论

- [流程] 金额系统的第一层证据只是「账本内部借贷平衡」；它不证明与渠道对账单一致，也不证明税额口径正确 — 应用：报告分开写「内部平衡 / 渠道对账 / 税务口径」三行，缺一行就标待确认
- [流程] 零小数币种不得 ×100：500 JPY 传 `amount=500`；但渠道有特例（Stripe 的 ISK/UGX 历史两位、HUF/TWD 仅 payout 为零小数且需被 100 整除）— 应用：先查渠道币种表再写期望值，不套用「最小单位=分」
- [流程] 「写进去 = 读回来」是金额系统最低要求：进程内 Map/缓存做去重键或账本唯一副本，重启即归零 — 应用：每个金额流做一次 kill→重启→读回，`data.json` 有记录但没加载属 S1
- [流程] webhook 返回 200 不等于已处理：验签在业务前、业务失败要回非 2xx 或进 DLQ；验签函数存在不等于签名覆盖 timestamp — 应用：改 ts 保留旧签名必须 401，容差窗口用 `now±301/299s` 三值实跑
- [流程] handler 中途失败必须零残留，否则渠道重投会与残留叠加成双份副作用 — 应用：测「第 N 步失败 → 无半条数据 → replay 后副作用仍为 1」
- [环境] Windows PowerShell 5.1 的 `Get-Content`/`Out-File` 默认 GBK/UTF-16，读写 UTF-8 中文证据会乱码甚至写坏；`curl` 是 `Invoke-WebRequest` 别名会吞掉 `--data-binary @file` — 应用：证据用 Node `fs.writeFileSync(...,'utf8')`，请求用 `curl.exe`，判端口用 `Get-NetTCPConnection -State Listen`，起服务轮询 `/health` 不用 `Start-Sleep`

## 技能改进提案区（供用户决策，不自行改动）

> 运行时发现的流程缺口写这里；每日升级任务按 `references/self-evolution.md` §3 处理后，在 CHANGELOG 标注"已吸收 / 已驳回 + 理由"。

- [技能改进] ✅ **已吸收（v1.1）**：为 GraphQL / gRPC 补专项端点矩阵 → 落地为 `references/protocol-testing.md` + `assets/protocol-matrix-template.md`，并扩展到 WebSocket / SSE
- [技能改进] 已驳回（v1.0，理由保留）：另建"统一证据采集模板" → 缺陷八字段已覆盖，Merge 过度不新增文件
- [技能改进] ✅ **已吸收（v1.2）**：i18n 与本地化测试 → 落地为 `references/i18n-localization-testing.md` + `assets/i18n-matrix-template.md`，含伪本地化、W3C RTL、`dirname`/`<bdi>`、collation 与 F-1~F-8 格式往返
- [技能改进] ✅ **已吸收（v1.2）**：补真正的「孤儿文档」门禁 → `scripts/selfcheck.py` 现在核对 `dissect.md` §8 路由表与 SKILL.md 叠加项，并补齐了 `performance-testing.md` 缺失的路由；此前 v1.1 CHANGELOG 声称由自检验证并不准确
- [技能改进] ✅ **已吸收（v1.3）**：把证据矩阵接进 `assets/report-template.md` 固定字段 → 报告新增「证据矩阵」段挂接 R-1~R-6 与六份证据模板，缺证据即标 BLOCKED（早于 v1.2 先落各自模板的承诺）
- [技能改进] ✅ **已吸收（v1.4）**：测试成本 / ROI 度量 → **合并**进 `references/test-effectiveness-testing.md` §5A（不另起文件），模板加三类成本/三类收益与 E-11~E-14；理由：与有效性度量是同一把尺的两面，另起文件会膨胀目录
- [技能改进] ✅ **已吸收（v1.4）**：移动端与桌面端专项 → 落地为 `references/cross-platform-testing.md` + `assets/device-matrix-template.md`，以 R-8 固定「仿真 ≠ 真机」；理由：本轮实查 Playwright Emulation 官方能力与 install-base 设备矩阵口径，不再靠臆造平台特有断言
- [技能改进] ✅ **已吸收（v1.4）**：无障碍自动化实测的边界 → 落地为 `references/accessibility-testing.md` + `assets/accessibility-matrix-template.md`，以 R-7 固定「axe 0 violations ≠ 合规」；来源 W3C WCAG 2.2 / Deque axe-core / DWP / Playwright
- [技能改进] ✅ **已吸收（v1.5）**：把「合规性声明」（SOC2 / 等保 / SSDF）与证据链自动对账 → 落地为 `references/evidence-chain-audit.md` + `assets/evidence-chain-template.md` + `scripts/evidence-audit.py`，新增 **R-9**；理由：本轮实查 W3C PROV-DM / NIST OSCAL / NIST SP 800-218 v1.1 / in-toto / GitHub artifact attestations，权威映射来源已足，不再造空泛清单，且明确「对账 GREEN ≠ 合规通过」
- [技能改进] ✅ **已吸收（v1.5）**：把设备矩阵与真实安装量数据源做成可复用采集脚本 → 落地为 `scripts/device-matrix.py` + `references/cross-platform-testing.md` §6A；理由：**不臆造 analytics API**，只接受本地 CSV/JSON 导出，算占比/累计/80% 截断点并固定输出 CrUX 口径局限；载体与实测结论仍人工填，不冒充真机证据
- [技能改进] ✅ **已吸收（v1.6）**：把 `scripts/evidence-audit.py` 的 manifest 与 OSCAL `assessment-results` 做格式互转 → 落地为 `evidence-audit.py --format oscal` + `references/evidence-chain-audit.md` §10 字段映射；理由：本轮确认确有 GRC/审计消费场景，且明确「只搬字段不裁决合规」，EA-13 纳入 `--self-test` 对等性校验，不造无人消费的转换层
- [技能改进] 待后续轮次（v1.7 已打底）：把「AI 生成用例有效性」的变异杀伤贡献做成跨语言自动跑数脚本 → TDM 的确定性 `--seed` 现为跨语言变异基准的可复现数据底座；本提案仍保留至具体变异工具输出 schema 确定，不硬编码某一家 JSON schema
- [技能改进] 待评估（v1.8 提出）：把 AUTH/S/F 三张测试卡做成「可执行 adapter」（统一 `token-provider` 接口：登录/刷新/重置取令牌 → 跑卡 → 出 JSON），减少手工 curl；暂不落地，理由：先确认 adapter 接口不绑定某框架，且不能替代人工判据
- [技能改进] ✅ **已吸收（v1.9）**：时间/时区正确性与备份/恢复可验证性 → 落地为 `references/time-correctness-testing.md` + `references/backup-recovery-testing.md` + 两份矩阵/演练模板 + `scripts/time-audit.py` / `scripts/restore-audit.py`，新增 **R-13/R-14**；理由：dogfood 的 `timedemo` 用 v1.8 实测出 2×S1（令牌跨时区多活 8h、错误备份覆盖新数据）与 UTC 日过滤、`+86400` 调度漂移，旧手册无对应判据
- [技能改进] 待后续轮次（v1.9 提出）：把「5xx 响应体不得含堆栈 / 绝对路径 / SQL」做成安全手册的固定检查项与报告字段 → 来源：dogfood F7（非法 `at` 入库 201，列表 500 回显 `time.js:7:24` 与绝对路径）；本轮只记提案，不扩 scope
- [技能改进] ✅ **已吸收（v1.10）**：金额与账务正确性、异步消息/Webhook 交付可靠性 → 落地为 `references/money-correctness-testing.md` + `references/webhook-delivery-testing.md` + 两份矩阵模板 + `scripts/money-audit.py` / `scripts/webhook-audit.py`，新增 **R-15/R-16**；理由：dogfood 的 `shopdemo` 用 v1.9 实测出 15×S1（0.1+0.2、JPY×100、幂等失效、退款超退、单边账本、混币种相加、重启丢账、签名不覆盖 ts、事件重复、乱序落退款、handler 残留、无重试/DLQ），旧手册无对应判据
- [技能改进] 待评估（v1.10 提出）：按税务辖区做「舍入/计税口径矩阵」→ 需要逐国读官方文档（本轮只给 HMRC 示例），不做全球通用断言
- [技能改进] 已驳回（v1.10，理由保留）：让 `money-audit.py` 自动拉取渠道对账单 → 需真实凭据与网络，违反零依赖/不联网边界；保持离线审计，渠道对账仍由测试者提供数据
- [技能改进] 待核实（v1.10 提出）：各支付渠道对 ISK/UGX/HUF/TWD 的「最小单位」处理随 API 版本变化 — 应用：以接入时渠道文档为准，证据里写清币种、amount 原值、期望 minor 值，不把特例写成通则
