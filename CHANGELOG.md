# 更新日志

> 每日升级记录。格式与门禁见 `references/self-evolution.md` §3~§4。
> 版本号与 `SKILL.md` frontmatter、`README.md` 徽章三者由 `scripts/selfcheck.py` 校验一致。

---

## [v1.7.0] — 2026-11-13 · 每日升级 #8

**主题**：从「结论可复核」扩展到「**喂给测试的数据本身可信 · 合规 · 可复现**」——测试数据管理（TDM）：合成数据生成、PII 脱敏 / 掩码、确定性种子、数据子集与制备、绝不用生产数据。同一份测试结论若建立在「假数据 / 泄漏的生产 PII / 每次跑都不一样的随机样本」之上，再多用例也只是沙上筑塔。新增 **R-11 测试数据可信与合规** 与三份文件（手册 + 模板 + 零依赖脚本），蒸馏来源含权威 TDM 定义与用户附加技能 `fullstack-dev` / `frontend-dev` 的二次蒸馏。注：与 #1~#7 同属每日升级自动化序列，按轮次记为 #8。

**遵循上轮建议**：未重写已覆盖主题（无障碍、跨端、测试经济性、供应链、隐私、契约演进、i18n、多租户、观测、韧性、数据、协议、AI 原生、证据链、特性开关、五阶段与四层模型），以 **Enhance / New 混合、New 为主**；四层模型与五阶段流程**未改语义**（按 `self-evolution.md` §7 只升 MINOR）；每轮至少一条可证伪规则 → 本轮引入 **R-11**；本轮做了**负向测试**（临时副本破坏 R-11 一处，确认 `selfcheck.py` §7c/§7d/§7e 确实 FAIL）。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 动作 | 对象 |
|---|---|
| **New** | `references/test-data-management.md`、`assets/test-data-matrix-template.md`、`scripts/test-data-gen.py` |
| **Enhance** | `SKILL.md`（version 1.7.0、description 触发词、v1.7 增量说明、v1.7 叠加项、阶段1 测试数据面、R-11、参考索引）、`README.md`（徽章 28→29 references / 17→18 assets / 3→4 scripts / 53→56 files、问题表 +1 行、结构树 +3 条、速查 +1 行、设计要点 R-1~R-11 + 分层叠加 v1.7、版本史 +1 行）、`CHANGELOG.md`（本条目）、`references/dissect.md`（§6 测试数据面 + §8 路由行）、`references/quality-gates.md`（§3 R-11 + §8 十一条 + 规则同步）、`assets/report-template.md`（R-11 行 + 十一行矩阵 + 残留核查边界）、`scripts/selfcheck.py`（§5 新文件字段 + §7f 新脚本门禁）、`memory/global-lessons.md`（TDM 教训组） |

### 蒸馏来源（深度蒸馏，URL 全记录）

- Thoughtworks《Test data management》：TDM 定义——"用真实世界形态的数据测开发中的应用，同时不让真实数据承担风险"，质量是测试数据的最大杠杆 → `references/test-data-management.md` §1/§5
- K2view《What is Test Data Management (TDM)》《What is Synthetic Data Generation》：TDM 四步（define/provision/maintain/retire）、合成数据 vs 数据脱敏（用假值替换 PII 但结构一致） → §1/§3
- DATPROF / IRI Test Data Virtualization：masking + subsetting + synthetic generation + automation 的组合能力、子集须保引用完整 → §3/§4
- 用户附加技能 `fullstack-dev`（其 `testing-strategy.md` 外部技能，不在本仓库）：Test Factories（faker/factory_boy，hardcode→factories）、目录约定 `tests/fixtures/{factories,seeds}`、Anti-Patterns #4（hardcode→factories）/ #9（"Test against production data → Generated test data only"）、`db-schema.md` 迁移须在 production data size 下 < 30s → §2/§4/§5
- 用户附加技能 `frontend-dev`（其 minimax 指南外部技能）：`--seed` 保证相同提示词可复现产出（图像/音频），对应"确定性种子" → §2
- 交叉引用（不重复造轮子）：`references/privacy-compliance-testing.md`（R-6 生产 PII 生命周期）、`references/data-integrity-testing.md`（迁移 up/down 与类生产数据量） → §9

### 口径诚实

- 掩码是**启发式规则**（保留格式、替换主体），**不保证**覆盖全部 PII、**不保证**不可逆；用了 `scripts/test-data-gen.py` 的 `mask` **不**等于"数据已脱敏 / 无 PII 泄漏"（§3/§7，模板 §7）
- `self-test` 只证明脚本自身的确定性/掩码逻辑可用，**不证明**你的数据集无 PII 残留、不证明合规通过
- 声称"测试数据已脱敏 / 合成数据无 PII 泄漏 / 数据可复现"必须附 §6 五类证据，否则降级为「待确认」；**R-11 不认「用了生成器」、不认「掩码了已知字段」、不认「无种子却说可复现」**
- 与 R-6 边界：R-6 管"生产系统怎么处理真实 PII"，R-11 管"喂给测试的数据本身是否可信合规"，二者不重叠、不互相替代（§9）

### 自检与门禁

- `scripts/selfcheck.py`：源与全局安装均 **PASS 36 / WARN 0 / FAIL 0 / GREEN**（规则数 10→11，§7c 双向同步、§7d 逐行矩阵、§7e 例外声明、§7f 新脚本门禁全过）
- `scripts/test-data-gen.py --self-test` 退出码 0；`scripts/evidence-audit.py --self-test` 与 `scripts/device-matrix.py --self-test` 退出码均 0；`py_compile` OK
- **负向测试**（项目外临时副本）：删 SKILL.md 的 R-11 定义 → §7c FAIL；删 `report-template.md` 的 `| R-11 ... |` 表格行 → §7d FAIL；删 R-11 行的「不得」 → §7e FAIL；三例 exit=1，干净副本 exit 0，证明 §7c/§7d/§7e 可证伪
- 文件数 53 → 56（references 28→29、assets 17→18、scripts 3→4），`diff -r` 源与全局安装零差异

### 提案处置

- 待后续轮次（v1.7 已打底）：把「AI 生成用例有效性」的变异杀伤贡献做成跨语言自动跑数脚本 → TDM 的确定性 `--seed` 现已成为跨语言变异基准的可复现数据底座；本提案仍保留至具体变异工具输出 schema 确定（不硬编码某一家 JSON）

---

## [v1.6.0] — 2026-11-12 · 每日升级 #7

**主题**：从「结论可复核」扩展到「**动态正确 · 配置可信 · 开关可控 · 合规可机读**」——同一份代码在开关 / 配置 / 灰度的动态下是否仍正确、是否仍安全；并把 R-9 证据链做成可机读导出。新增 **R-10 特性开关 / 配置 / 灰度正确性** 与两份文件，落地一个 v1.5 顺延提案（`evidence-audit.py --format oscal` → OSCAL `assessment-results`）。注：与 #5/#6 同日（2026-11-12）执行，按自动化轮次记为 #7。

**遵循上轮建议**：未重写已覆盖主题（无障碍、跨端、测试经济性、供应链、隐私、契约演进、i18n、多租户、观测、韧性、数据、协议、AI 原生、证据链、五阶段与四层模型），以 **Enhance / Merge / New 混合、New + Merge 为主**；四层模型与五阶段流程**未改语义**（按 `self-evolution.md` §7 只升 MINOR）；每轮至少一条可证伪规则 → 本轮引入 **R-10**；本轮做了**负向测试**（临时副本破坏 R-10 一处，确认 `selfcheck.py` §7c/§7d 确实 FAIL）。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 动作 | 对象 |
|---|---|
| **New** | `references/feature-flag-testing.md`、`assets/flag-rollout-matrix-template.md` |
| **Merge** | v1.5 顺延提案「manifest ↔ OSCAL `assessment-results` 互转」落地为 `scripts/evidence-audit.py --format oscal` + `references/evidence-chain-audit.md` §10（**不另起文件**）；明确「只搬字段不裁决合规」，EA-13 纳入 `--self-test` 对等性校验 |
| **Enhance** | `SKILL.md`（version 1.6.0、description 触发词、v1.6 增量与横向叠加项、阶段 1 配置/开关面 / 阶段 3 专项维度 / 九条→十条规则与 R-10 定义行 / 参考索引 / 报告矩阵十行）、`README.md`（徽章 27→28 / 16→17 / 51→53、问题表 1 行、结构树、速查 2 行、设计要点 R-1~R-9→R-1~R-10 与 OSCAL 段、版本史）、`references/dissect.md`（§6 配置/开关面、§8 两条新路由、产出格式一行）、`references/quality-gates.md`（§3 R-10 行、§8 十条 / 十行 / 两条新核对）、`assets/report-template.md`（证据矩阵 R-10 + 第十份模板挂接 + 九行→十行）、`references/evidence-chain-audit.md`（§6 EA-1~EA-12→EA-13、§10 manifest→OSCAL 映射段）、`references/tools.md`（2 行专项工具 + 2 条纪律 + 可读性）、`references/self-evolution.md`（§3 ⑥ 与 §5 表格）、`scripts/selfcheck.py`（§5 两个新文件字段、`references/feature-flag-testing.md` 与 `assets/flag-rollout-matrix-template.md` 关键字段）、`memory/global-lessons.md`（新蒸馏 6 条、提案区改「已吸收（v1.6）」） |
| **Match** | 新手册在 `dissect.md` §8 与 `SKILL.md` v1.6 叠加项均有触发条件；R-10 在 `SKILL.md` 定义表、`quality-gates.md` §3/§8、`report-template.md` 证据矩阵、`selfcheck.py` §7c/§7d/§7e 四处口径一致；OSCAL 导出由 §7f 静态门禁 + EA-13 运行时自测约束。全部由 `selfcheck.py` **代码强制** |
| **Existing** | 五阶段模型、四层能力模型、记忆树 <100 行纪律、双视角、"工具缺失不中止"降级原则、六门禁 12 分、缺陷八字段、R-1~R-9 规则、权限裁决 —— 全部保留，未改语义 |

### 蒸馏来源（本轮实查，均可核查）

| 来源 | URL / 位置 | 关键结论 |
|---|---|---|
| Martin Fowler《Feature Toggles》 | https://martinfowler.com/articles/feature-toggles.html | 四类 toggle：Release / Experiment / Ops / Permissioning；明确「toggle 应有计划删除日期」；开关两态都要测 |
| Open Practice Library《Feature Toggles》 | https://openpracticelibrary.com/practice/feature-toggles/ | 避免长期存活的 toggle；两个状态都要测；与持续交付结合 |
| Harness / Rollout.io kill-switch 实践 | https://www.harness.io/harness-devops-academy/feature-flags · https://rollout.io/blog/how-to-disable-code-the-developers-production-kill-switch/ | 部署时功能处于休眠态、上线后再翻开关；kill-switch 是生产止血机制 |
| SEC 对 Knight Capital 2012-08-01 事件调查报告 | https://www.sec.gov/litigation/admin/2013/34-70694.pdf | 遗留/废弃路径被重新启用 + 缺乏对应控制，约 45 分钟损失约 4.6 亿美元；用于说明「开关默认态与废弃开关」风险，不臆造其内部结构 |
| Google SRE · progressive / canary rollout | https://sre.google/sre-book/ | 灰度曝光的「actual exposure 须可测量」，能与计划比例对照 |
| NIST OSCAL 模型分层 | https://pages.nist.gov/OSCAL/concepts/layer/ | Control / Implementation / Assessment 三层；`assessment-results` 含 scope、evidence 与 findings；native traceability to catalog layer |
| GitHub `naodeng/awesome-qa-skills` | https://github.com/naodeng/awesome-qa-skills | `requirement-traceability-analysis` / `test-report-review` / `skill-change-verification` 等 canonical names，佐证本轮主题与 OSCAL 导出方向 |

### 口径诚实（逐条核验，不臆造）

- Knight Capital 案例在公开报道中被广泛归结为「遗留功能开关/代码路径被重新启用 + 缺乏对应控制」，本手册把它作为**反面教材**引用，**只写「说明开关默认态/废弃开关风险」，不对其内部实现/具体 flag 名称下结论**。
- OSCAL `assessment-results` 子页（reference 路径）本轮经 WebFetch 返回 **404**（JS 渲染不可抓，与 v1.5 体验一致）；字段名（`metadata` / `result` / `finding` / `observation` / `relevant-evidence` / `implementation-status.state` / `location.related-observation`）依据 OSCAL Assessment Layer **模型规范描述**，已在 `evidence-chain-audit.md` §10.2 写明「落地以目标组织实际采用的 OSCAL 版本校验」，不臆造对方不需要的字段（如未确认消费方时不凭空加 `import-applicant`）。
- `to_oscal` 只做字段搬运：`待确认` / 缺口 在 OSCAL 里仍是 `partial` / `gap`，**不得**因「有了 OSCAL 文件」写成「已通过 OSCAL 合规评估」；导出件固定带 `_disclaimer`。
- R-10 的「开态测过 ≠ 关态也安全」「配置三处没比对 ≠ 开关可控」「说 5% 没实测 ≠ 灰度可控」均为**禁止冒充声明**，缺证据一律降级为「待确认」。

### 自检结果与门禁负向测试

- `scripts/selfcheck.py`：**PASS 34 / WARN 0 / FAIL 0 / GREEN**（源，含 §7c 规则双向同步、§7d 证据矩阵十行、§7e 例外声明、§7f 脚本门禁）；两个新文件关键字段齐备、路由闭环、索引覆盖均通过。
- `scripts/evidence-audit.py --self-test` 与 `scripts/device-matrix.py --self-test` 退出码均 0；`to_oscal` 新增 EA-13 对等性校验（claim 数与 findings 数一致、非 PASS 不被翻成 `implemented`）。
- 门禁负向测试（项目外临时副本）：删 `SKILL.md` 的 R-10 定义行 → §7c 判 `quality-gates.md 出现 SKILL.md 未定义的规则: R-10` FAIL、§7d 判 `报告证据矩阵缺少规则表格行: R-10` FAIL、§7e 判 `规则缺少禁止冒充声明: R-10` FAIL；删 `report-template.md` 的 `| R-10 ` 表格行 → §7d 单独 FAIL；干净副本退出码 0。证明 R-10 门禁可证伪而非文字声明。
- `py_compile` 校验三个脚本均 OK。

### 提交与同步 / 治理

- 文件 51 → 53（references 27→28、assets 16→17、scripts 不变）。
- 全局安装：`cp -r` 覆盖同步（`--exclude=.git/.workbuddy-ai/__pycache__/*.pyc/.test-memory`），全局版 `version: 1.6.0`，2 个新文件齐全，`diff -r` 零差异；全局目录复跑 selfcheck 同样 GREEN。
- `memory/global-lessons.md` 新增 6 条 v1.6 蒸馏（feature flag / config drift / kill-switch / OSCAL 边界），提案区「manifest ↔ OSCAL 互转」结案为「已吸收（v1.6）」，另一 v1.5 顺延提案（AI 用例变异杀伤跨语言自动跑数）保留为「待后续轮次」。
- 提交 `feat(v1.6.0): 每日升级 #7 <主题>`，push 到 `origin/main`（先常规 push，失败按 memory.md「环境事实」的 Git Data API 路径）。

---

## [v1.5.0] — 2026-11-12 · 每日升级 #6

**主题**：从「结论正确」扩展到「**结论可复核 · 声称可对账**」——把上一轮剩下的两个顺延提案全部结案：合规性声明与证据链自动对账、设备矩阵与真实安装量数据源采集脚本；新增 **R-9 证据链可追溯与可复核性** 与两个**零依赖、自带可证伪自检**的 Python 脚本，并把视觉回归基线治理、AI 生成用例有效性度量 **Merge** 进已有手册（不新增强化手册、不膨胀目录）。注：与 #5 同日（2026-11-12）执行，按自动化轮次仍记为 #6。

**遵循上轮建议**：未重写已覆盖主题（无障碍、跨端、测试经济性、供应链、隐私、契约演进、i18n、多租户、观测、韧性、数据、协议、AI 原生、五阶段与四层模型），以 **Enhance / Merge / New 混合、Merge 为主**；四层模型与五阶段流程**未改语义**（按 `self-evolution.md` §7 只升 MINOR）；每轮至少一条可证伪规则 → 本轮引入 **R-9**；本轮做了**负向测试**（临时副本破坏一处，确认 `selfcheck.py` 确实 FAIL）。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 动作 | 对象 |
|---|---|
| **New** | `references/evidence-chain-audit.md`、`assets/evidence-chain-template.md`、`scripts/evidence-audit.py`、`scripts/device-matrix.py` |
| **Enhance** | `SKILL.md`（version 1.5.0、description 触发词、v1.5 增量与横向叠加项、阶段 1 证据链面 / 阶段 3 三项专项 / 证据纪律 / 阶段 4 自检、九条规则与 R-9 定义行、参考索引）、`README.md`（徽章 26→27 / 15→16 / 47→51、问题表 3 行、结构树、速查 3 行、设计要点、升级流程、版本史、`R-1~R-8`→`R-1~R-9` 漂移修正）、`references/dissect.md`（§6 证据链面、§8 两条新路由、产出格式一行）、`references/quality-gates.md`（§3 R-9 行、§8 九条 / 九行 / 两条新核对）、`assets/report-template.md`（证据矩阵 R-9 + 第九份模板挂接 + 八行→九行）、`references/tools.md`（4 行专项工具 + 2 条纪律 + 可用性探测两条自检）、`references/self-evolution.md`（§3 ⑥ 与 §5 表格的 §7f / 脚本回归）、`scripts/selfcheck.py`（§5 字段、新增 §7f、**§7d 由「整段统计编号」加固为「逐条核对表格行」**）、`references/ai-native-testing.md`（§3 交叉引用 §5B，不重复抄写） |
| **Merge** | 两个顺延提案结案：合规声明对账落地为新手册 + 模板 + 脚本（因需独立 manifest 规范，另起文件）；设备矩阵数据源脚本落地为 `scripts/device-matrix.py` + `cross-platform-testing.md` §6A（**不另起手册**）。视觉回归基线治理并入 `cross-platform-testing.md` §6A、AI 生成用例有效性并入 `test-effectiveness-testing.md` §5B，均不新增文件；`memory/global-lessons.md` 提案区改为「已吸收（v1.5）」并新增 2 组共 13 条 v1.5 教训、2 条新提案 |
| **Match** | 新手册在 `dissect.md` §8 与 `SKILL.md` v1.5 叠加项均有触发条件；R-9 在 `SKILL.md` 定义表、`quality-gates.md` §3/§8、`report-template.md` 证据矩阵、`selfcheck.py` §7c/§7d/§7e 四处口径一致；两个新脚本由 §7f 静态门禁约束。全部由 `selfcheck.py` **代码强制** |
| **Existing** | 五阶段模型、四层能力模型、记忆树 <100 行纪律、双视角、"工具缺失不中止"降级原则、六门禁 12 分、缺陷八字段、R-1~R-8 规则、权限裁决 —— 全部保留，未改语义；`SKILL.md` 的 todo 示例逐字保留 |

### 蒸馏来源（本轮实查，均可核查）

| 来源 | URL / 位置 | 关键结论 |
|---|---|---|
| W3C PROV-DM（Recommendation 2013-04-30） | https://www.w3.org/TR/prov-dm/ | `Entity` / `Activity` / `Agent` 三类对象与 `wasGeneratedBy` / `used` / `wasDerivedFrom` / `wasAttributedTo` / `wasAssociatedWith` 等关系；目标是 provenance 在异构系统间 **interchange**，并支持对 quality / reliability / trustworthiness 形成判断 |
| NIST OSCAL 模型分层 | https://pages.nist.gov/OSCAL/concepts/layer/ · https://pages.nist.gov/OSCAL/ | Control / Implementation / Assessment 三层；模型精确名 `catalog` `profile` `mapping` `component-definition` `system-security-plan` `assessment-plan` `assessment-results` `plan-of-action-and-milestones`；官方原文「The OSCAL models provide native traceability from the assessment layer to the catalog layer」；`assessment-results` 含评估执行时间、scope、evidence 与 findings |
| NIST SP 800-218 SSDF v1.1 | https://csrc.nist.gov/pubs/sp/800/218/final · https://csrc.nist.gov/Projects/ssdf | 2022-02；PO / PS / PW / RV 四组；每条实践由 Practice / Task / Notional Implementation Example / Reference 四要素定义；与 PS.3.2（collecting and sharing provenance data）、PW.1.2 相关；官方明确「not to create a checklist to follow」 |
| in-toto 官方 README | https://github.com/in-toto/in-toto | `layout` 由 project owner 创建，列 `steps` 顺序与授权 `functionaries`；`material and product rules`（`CREATE`/`DELETE`/`MODIFY`/`ALLOW`/`DISALLOW`/`REQUIRE`/`MATCH`）；`link` file 记录 step name / command / materials / products 并签名，「provide the required evidence to establish a continuous chain」；`in-toto-verify` 校验签名、过期、授权与规则；未显式作为 artifacts 传入的文件不会被记录 |
| GitHub Docs · artifact attestations | https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations | `actions/attest@v4` 的 `subject-path` / `subject-name` + `subject-digest` / `sbom-path`；`gh attestation verify <artifact> -R ORG/REPO`、`--predicate-type https://spdx.dev/Document/v2.3`、`--format json --jq '.[].verificationResult.statement.predicate'` |
| Playwright · Visual comparisons / `toHaveScreenshot()` | https://playwright.dev/docs/test-snapshots | 像素比对会因 OS / 浏览器 / 平台渲染差异产生不同结果，应与生成基线相同的环境运行；`--update-snapshots`、`snapshotPathTemplate`、`maxDiffPixels` / `maxDiffPixelRatio` / `threshold`、`mask` / `stylePath`、`animations` / `caret` / `scale` / `omitBackground` |
| Chrome UX Report（CrUX）官方文档 | https://developer.chrome.com/docs/crux/ · https://developer.chrome.com/docs/crux/methodology | 符合条件的真实 Chrome 用户 field data；origin/page 需公开可发现且访问量足够；form factor 仅 `phone` / `tablet` / `desktop`（UA 推断）；country 维度在 CrUX APIs 中不可用、ECT 维度已移除；不覆盖机型 / OS 版本 / 非 Chrome 内核 |
| GitHub `naodeng/awesome-qa-skills` | https://github.com/naodeng/awesome-qa-skills | `requirement-traceability-analysis` / `test-report-review` / `skill-change-verification` / `visual-regression-testing` / `ai-generated-test-review` / `test-effectiveness-analysis` 等 canonical names，佐证本轮主题与 Merge 方向 |

**口径诚实标注**：① PROV-DM 页面**没有**把 `traceability` 定义成独立术语，本手册只借其对象与关系做建模语言，不宣称实现完整 PROV 合规；② OSCAL 官网「from months to minutes」是**宣传口径**，非本技能实测承诺；③ SSDF 的 Notional Implementation Example 明确非必需，且官方声明不是 checklist，故手册禁止「抄清单即合规」；④ in-toto README **未**给出 `threshold` 定义、**未**使用 `expected materials/products` 短语，手册不臆造字段；⑤ GitHub artifact attestations 是**产品级能力**非通用标准，离线/气隙验证流程不同，手册不套用在线命令；⑥ Playwright 阈值参数只列名称与用途，**不给默认数值**，避免把某个数字写成官方要求；⑦ CrUX 局限按官方文档逐条写明，脚本固定输出该声明；⑧ **未采用**任何「AI 提效 X%」类二手数据，`test-effectiveness-testing.md` §5B 只给可自测的度量口径；⑨ 设备矩阵脚本**不臆造 analytics API 字段或鉴权**，只接受本地导出；⑩ GitHub Docs 栏目 URL 为文档入口，具体子页路径以官方站点为准，手册中的命令按官方原文转述。

### 主要改动

1. **证据链可追溯与合规声明对账**（新手册 + 模板 + 脚本 + R-9）：PROV 三级引用链、OSCAL 三层与 SSDF 四组的「逐控制项挂证据」纪律、in-toto 连续链与 GitHub attestations 的真实命令、manifest 最小字段与 7 类检出码、EA-1~EA-12 测试卡、L0 人工降级路径；`scripts/evidence-audit.py` 只用标准库、不联网、不修改被测项目，自动补算证据 `sha256` 并抽出锚点原文，`--self-test` 可检出悬空引用 / 过期证据 / 不可解析锚点 / PASS 无证据 / 无控制项缺口声明 / 未分类结论
2. **R-9 证据链可追溯与可复核性**：声称「可复核 / 证据链完整 / 已通过审计」须附三级引用链 + hash/commit 绑定 + 自动对账缺口 + 控制项映射与未映射声明 + 导出件自身 hash；一次性探索、无留档要求写「不适用：无留档要求」，**不得**写「可审计 / 通过审计」；部分证据写「存在 N 处缺口，降为待确认」。**对账 GREEN ≠ 合规通过 ≠ 软件安全 ≠ 发布批准**
3. **设备矩阵真实安装量数据源**（落地顺延提案）：`scripts/device-matrix.py` 接受本地 CSV/JSON 导出，算占比 / 累计 / 80% 截断点 / 长尾补充位，固定输出数据源、时间窗与 CrUX 局限；空数据或合计 0 直接报错；**不代填** `real` / `emulator` 载体、不写「真机已验证」；`--self-test` 用 50/30/15/5 验算
4. **视觉回归基线治理**（`cross-platform-testing.md` §6A）：基线环境指纹、`--update-snapshots` 留旧/新 hash + 理由 + 批准人、`snapshotPathTemplate` 分平台、`maxDiffPixels`/`threshold`/`mask` 变更需批准、基线计入证据链；X-13~X-16 测试卡
5. **AI 生成用例有效性度量**（`test-effectiveness-testing.md` §5B）：入库率 / 断言强度合格率 / 变异杀伤贡献 / **假通过率** / 审查人时 / 逃逸拦截贡献，E-15~E-18；分母是「入库用例」而非「生成条数」；`ai-native-testing.md` §3 只加交叉引用，不二次抄写弱断言清单
6. **门禁升级**：`selfcheck.py` 新增 **§7f 脚本可证伪性静态门禁**——两个脚本必须自带 `--self-test`、`SELFTEST GREEN`、检出码与「不联网 / 不代填 / 不证明」诚实边界声明，缺字段即 FAIL；`self-evolution.md` §3 ⑥ 把两个 `--self-test` 列为升级固定动作
7. **漂移修正**：`SKILL.md` 规则数「八条→九条」、`quality-gates.md` §8「八条/八行→九条/九行」、`report-template.md`「八行→九行」、README 与索引中 `R-1~R-8` 统一改为 `R-1~R-9`
8. **§7d 门禁加固（负向测试实证驱动）**：旧实现只在证据矩阵**整段**里统计 `R-N` 编号，说明文字中出现的编号即可蒙混——删掉 R-9 表格行仍判 GREEN。现改为只认 `| R-N ` 开头的**表格行**逐条比对，说明段另查「未定义编号」。这恰好是本轮 R-9「结论可复核」要防的失效模式：**看起来有证据槽位，实际没有**

### 自检、回归与负向测试

| 项 | 结果 |
|---|---|
| `python scripts/selfcheck.py` | **PASS 32 / WARN 0 / FAIL 0**（frontmatter、断链、版本一致、占位 URL、模板/手册字段、tree 模板行数、27 份手册索引、19 份专项路由闭环、R-1~R-9 双向同步、报告矩阵九行、九条例外声明、§7f 两个脚本门禁、global-lessons 格式） |
| `python scripts/evidence-audit.py --self-test` | `SELFTEST GREEN`，exit 0 |
| `python scripts/device-matrix.py --self-test` | `SELFTEST GREEN`，exit 0 |
| `python -m py_compile scripts/*.py` | `COMPILE_OK` |
| 负向测试 | 临时副本两处破坏均 `PASS 31 / FAIL 1`、exit 1；其中 NEG-2 首次误判 GREEN 并促成 §7d 加固（详见下方记录） |
| 回归检查 | 五阶段与四层模型未改语义；todo 示例逐字保留；记忆树 <100 行纪律保留；新手册有 §8 路由；R-9 已落 `quality-gates.md` / `report-template.md` / 规则例外声明三处；旧示例仍成立 |

**负向测试记录**（临时副本中执行，源文件未改动，副本已清理）：

- **NEG-1**：把 `scripts/evidence-audit.py` 的 `SELFTEST GREEN` 改成 `SELFTEST OK` → `[FAIL] scripts/evidence-audit.py 缺少可证伪性 / 诚实边界关键字段: SELFTEST GREEN`，`PASS 31 / FAIL 1`，exit 1（§7f 确实生效）。
- **NEG-2**：删除 `assets/report-template.md` 证据矩阵的 `| R-9 ... |` 表格行 → **首次仍判 GREEN**，暴露 §7d 的真实缺陷：旧实现统计整段里的 `R-N`，说明文字里的 R-9 足以蒙混。随即把 §7d 改为只认表格行并重跑 → `[FAIL] 报告证据矩阵缺少规则表格行: R-9`，`PASS 31 / FAIL 1`，exit 1。
- **首次尝试的假 GREEN**：Git Bash 的 `mktemp -d` 返回 Windows 路径，拼进 Python 字符串字面量触发 `\U` unicodeescape 错误，导致副本**根本没被破坏**却打印了 GREEN。改为经 `sys.argv` 传路径后重做，才得到上面的真实结果。**「负向测试打印 GREEN」本身也可能是假象**，这与本轮 R-9 的主题一致，故如实留档。
- 主目录加固后自检仍为 `PASS 32 / WARN 0 / FAIL 0`；`python -m py_compile scripts/*.py` → `COMPILE_OK`。

**下轮建议**：① 别再重写已覆盖的大块，继续以 Enhance / Merge 为主；② 两个新提案（manifest ↔ OSCAL `assessment-results` 互转、跨语言变异杀伤自动跑数）先确认真实消费需求再动，避免造无人使用的转换层；③ 每轮仍至少一条可证伪规则、且必须做负向测试；④ 关注 `selfcheck.py` 检查项变多后的执行时长（当前仍是纯本地静态检查，无子进程）。

---

## [v1.4.0] — 2026-11-12 · 每日升级 #5

**主题**：从「系统正确」扩展到「**人人可用 · 处处可用 · 值得测**」——补齐无障碍可达性深度实测、跨端与设备形态真实性、测试经济性/ROI 三块深水区，落地三个顺延提案，新增 **R-7 / R-8** 两条可证伪规则，并新增两条自检门禁（§7d 报告证据矩阵同步 / §7e 规则例外声明）。

**遵循上轮建议**：未重写已覆盖主题（契约演进、隐私、有效性度量、供应链、i18n、多租户、观测、韧性、数据、协议、AI 原生、五阶段与四层模型），以 **Enhance 为主、New 为辅、Merge 消化顺延提案**；四层模型与五阶段流程**未改语义**（按 `self-evolution.md` §7 只升 MINOR）；每轮至少补一条可证伪规则 → 本轮引入 **R-7 / R-8**。同时修正历史文档漂移：`SKILL.md` 曾写「四条可证伪规则」而实际已有六条、`README.md` 速查曾写 `R-1~R-4`、`quality-gates.md` §8 曾写「六条」；并把各模板内硬编码的 `技能版本：v1.3.0` 统一改成 `v<X>` 占位，从根上消除逐轮漂移。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 动作 | 对象 |
|---|---|
| **New** | `references/accessibility-testing.md`、`references/cross-platform-testing.md`、`assets/accessibility-matrix-template.md`、`assets/device-matrix-template.md` |
| **Enhance** | `SKILL.md`（version 1.4.0、description 触发词、v1.4 增量、v1.4 叠加项、阶段 1/3/4、R-7/R-8 规则行、参考索引、漂移修正）、`README.md`（徽章 24→26 / 13→15 / 43→47、问题表 5 行、结构树、速查 5 行、设计要点、版本史、漂移修正）、`references/dissect.md`（§8 两条新路由、§6 两个解剖面、产出格式两行）、`references/quality-gates.md`（§3 R-7/R-8 两行、§8 核对扩为八条 + 两条新核对）、`assets/report-template.md`（证据矩阵 R-7/R-8 + 两份模板挂接）、`references/tools.md`（5 行专项工具 + 两条使用纪律）、`references/frontend-testing.md`（§3 分工与误引提醒）、`references/self-evolution.md`（§3/§5 新门禁与负向测试要求）、`scripts/selfcheck.py`（§5 字段、§7d、§7e） |
| **Merge** | 三个顺延提案全部结案：ROI **合并**进 `references/test-effectiveness-testing.md` §5A（不另起文件）与 `assets/test-effectiveness-template.md`；移动端/桌面端与无障碍落地为两份专项手册；`memory/global-lessons.md` 新增 4 组共 22 条 v1.4 教训，提案区改为「已吸收（v1.4）」并留理由。另：可复现构建并入 `references/supply-chain-testing.md` §2A、影子流量并入 `references/contract-evolution-testing.md` §3A，均不新增文件 |
| **Match** | 2 份新手册均在 `dissect.md` §8 与 `SKILL.md` v1.4 叠加项有触发条件；R-7/R-8 在 `SKILL.md` 定义表、`quality-gates.md` §3/§8、`report-template.md` 证据矩阵三处口径一致。以上由 `selfcheck.py` **代码强制**（§7b 路由闭环、§7c 规则双向同步、§7d 报告矩阵同步、§7e 例外声明） |
| **Existing** | 五阶段模型、四层能力模型、记忆树 <100 行纪律、双视角、"工具缺失不中止"降级原则、六门禁 12 分、缺陷八字段、R-1~R-6 规则、权限裁决 —— 全部保留，未改语义；`SKILL.md` 的 todo 示例逐字保留 |

### 蒸馏来源（本轮实查，均可核查）

| 来源 | URL / 位置 | 关键结论 |
|---|---|---|
| W3C/WAI《What's New in WCAG 2.2》 | https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/ | 相较 2.1 **新增 9 条成功标准**（2.4.11/2.4.12/2.4.13、2.5.7/2.5.8、3.2.6、3.3.7/3.3.8/3.3.9 及各自 A/AA/AAA 级别）；**4.1.1 Parsing is obsolete and removed from WCAG 2.2**；WCAG 2.2 于 **2023-10-05** 成为 W3C Recommendation |
| WCAG 2.2 Recommendation | https://www.w3.org/TR/WCAG22/ | 2.4.11 Focus Not Obscured (Minimum) AA；2.5.8 Target Size (Minimum) AA = **24×24 CSS px**，例外 Spacing / Equivalent / Inline / User Agent Control / Essential；3.3.8 Accessible Authentication (Minimum) AA 禁止 cognitive function test，除非 Alternative / Mechanism / Object Recognition / Personal Content |
| Deque `axe-core` README | https://github.com/dequelabs/axe-core | 「find on **average 57%** of WCAG issues automatically」；结果含 `incomplete`，需人工复核；官方示例对 `results.violations` 判失败 |
| DWP Accessibility Manual | https://accessibility-manual.dwp.gov.uk/ | 测试须覆盖至少一个常用 screen reader；JAWS/NVDA 配 Windows + Firefox/Chromium、VoiceOver 在 macOS 上仅 Safari fully supported、Narrator 用 Win+Ctrl+Enter；结果标 **passed / failed / not checked / not present** 并保存证据 |
| Playwright 官方文档 | https://playwright.dev/docs/emulation · https://playwright.dev/docs/aria-snapshots | Emulation 可覆写 userAgent / viewport / hasTouch / locale / timezoneId / geolocation / permissions / colorScheme / reducedMotion / forcedColors / contrast / offline 等；`devices[...]` 只是描述符预设；`toMatchAriaSnapshot` 断言 **accessibility tree 的 YAML 快照**，支持 partial matching 与 `/children: equal` |
| LambdaTest Learning Hub（移动设备矩阵） | https://www.lambdatest.com/learning-hub/ | 设备矩阵应来自 install-base analytics 并覆盖约 **80% installs**；补 low-RAM Android、foldable/tablet、vendor skin、oldest supported OS；emulator 适合快速布局/流程反馈，battery/thermal/sensors/biometrics/real network 须真机；矩阵季度复审 |
| GitHub `naodeng/awesome-qa-skills` | https://github.com/naodeng/awesome-qa-skills | 存在 `accessibility-testing` / `mobile-testing` / `cross-browser-testing` / `visual-regression-testing` / `automation-roi-analysis` / `test-maintenance-cost-analysis` / `regression-optimization` / `ci-test-optimization` 等 canonical names，佐证本轮主题与顺延提案方向 |
| Reproducible Builds 官方定义 | https://reproducible-builds.org/docs/definition/ | 相同 **source code / build environment / build instructions** 应能由任何一方重建 **bit-by-bit identical** 产物；以逐位比较或密码学 hash 验证 |
| 影子流量工程模式（线索层） | Istio `mirror` / Envoy shadow / Diffy 类响应 diff 工具的公开资料 | 只作为「只读镜像 + 响应规范化比对」的模式输入；未逐条核验具体产品参数，手册不臆造命令 |

**口径诚实标注**：① 9 条新增 SC 的编号与级别来自 W3C 官方 What's New 页面（本轮复核），三条 AA 的判据为精简转述，落地验收以 WCAG 2.2 原文为准；② 57% 是 `axe-core` README 的**自述平均值**，非本技能实测，不能当覆盖率承诺；③ DWP 组合是「至少一个常用 screen reader」的最低口径，不构成全部合规覆盖；④ 设备矩阵 80% 覆盖与季度复审是**工程选型建议**而非标准强制，报告须写数据源与时间窗；⑤ 影子流量只作模式输入，不绑定产品、不臆造参数，无镜像能力时明确标 `BLOCKED`；⑥ `SOURCE_DATE_EPOCH` / `diffoscope` 只作可复现构建的排查线索，不把「设了环境变量」当成「已可复现」；⑦ 本轮未把 2G 网络写成任何来源的原文要求，网络档位一律要求自写数值与载体。

### 主要改动

1. **无障碍可达性深度实测**（`accessibility-testing.md` + 证据模板）：WCAG 2.2 增量 9 条与 4.1.1 移除、2.4.11/2.5.8/3.3.8 精确口径与三处易错提醒（44×44 属 AAA、验证码属认知测试、Parsing 已移除）、axe 自动化边界与 `incomplete`、键盘路径逐步记录、DWP 读屏组合与四类结果标注、`toMatchAriaSnapshot` 断言纪律、A-1~A-12 测试卡
2. **R-7 无障碍可达性**：声称合规须附目标版本级别 + violations/incomplete 原文与人工结论 + 完整键盘路径 + 至少一组读屏组合逐项标注 + 2.5.8/3.3.8 实测；明确「axe 0 violations ≠ WCAG 合规」「键盘通 ≠ 读屏懂」「有 aria-label ≠ 点得中」，无 UI 项目写「不适用：无图形交互界面」
3. **跨端与设备形态真实性**（`cross-platform-testing.md` + 证据模板）：install-base 设备矩阵与约 80% 覆盖、`real`/`emulator`/`simulator`/`browser-emulation` 四类载体分野、Playwright Emulation 清单与 `devices` 预设、端侧特有面（生命周期/中断/权限/旋转折叠/深链/生物识别/软键盘）、网络档位数值口径、X-1~X-12 测试卡
4. **R-8 跨端与设备形态真实性**：声称跨端/真机须附矩阵来源与覆盖占比 + 载体逐项标注 + 多内核实测 + 长尾条目结论 + 端侧面与网络档位输出 + ≥1 组 real device 记录；明确「三档断点 ≠ 移动端可用」「Mobile Safari 仿真绿 ≠ iOS 真机」「桌面 Chrome ≠ WebKit/Gecko」，纯后端写「不适用：无终端形态差异」
5. **测试经济性 / ROI（Merge，落地顺延提案）**：`test-effectiveness-testing.md` §5A 三类成本 × 三类收益、ROI/回收周期口径、E-11~E-14 度量卡、四条反模式；模板加对应字段；**不另起新文件**，与有效性指标联动防止「删用例换速度」
6. **两份既有手册 Enhance**：`supply-chain-testing.md` §2A 可复现构建（三类输入固定、RB-1~RB-5、`diffoscope` 线索、R-3 证据不放宽）；`contract-evolution-testing.md` §3A 影子流量（只读镜像、无写副作用、脱敏采样、S-1~S-5、不单独构成 R-5 通过）
7. **证据闭环两条新门禁**：`selfcheck.py` §7d 逐条比对 `report-template.md` 证据矩阵与 SKILL.md 规则集（缺行/多编号即 FAIL）；§7e 逐条检查规则表行的「不适用时禁止冒充声明」（须含「不得」，行数与规则集一致）。`self-evolution.md` §3/§5 同步写明并要求**每轮做负向测试**
8. **经验治理与漂移修正**：`global-lessons.md` 新增无障碍 7 条 / 跨端 7 条 / ROI 4 条 / 可复现构建与影子流量 4 条共 22 条；三个顺延提案结案为「已吸收（v1.4）」；修正「四条规则」「R-1~R-4」「六条」三处历史漂移，把 4 处模板内硬编码版本统一为 `v<X>` 占位

### 回归检查

- [x] 五阶段模型闭环未变，`SKILL.md` 的 todo 示例（4 条 MRE、含越权 S1）逐字保留
- [x] 四层能力模型语义未变（v1.4 内容以「横向叠加项」呈现，不构成 MAJOR）
- [x] 记忆树 <100 行纪律保留；`assets/tree-template.md` 未改，仍 <100 行
- [x] 「工具缺失不中止」降级原则保留，两份新手册各有 L0 零依赖路径（静态语义/视口线索 + 人工键盘/单台真机走查）
- [x] 运行时不擅自改本体的安全约束保留；权限裁决原文未改
- [x] 原有文件引用路径未失效（由 `selfcheck.py` 断链检查验证）
- [x] 新增 2 份手册不产生孤儿文档（由 `selfcheck.py` §7b 路由闭环验证）
- [x] R-1~R-8 在 `SKILL.md`、`quality-gates.md` §3/§8 口径一致（由 `selfcheck.py` §7c 双向同步验证）
- [x] 报告证据矩阵八行与规则集一致（由 `selfcheck.py` §7d 验证）；八条规则均含禁止冒充声明（由 §7e 验证）
- [x] 六门禁 12 分、缺陷八字段、Flaky 治理、变异测试等关键字段仍在（由 `selfcheck.py` 字段检查验证）
- [x] 报告模板新增两行未破坏原有 PASS/FAIL 与 Go/No-Go 结构
- [x] 已做负向测试：在临时副本中分别破坏报告矩阵与规则例外声明，确认 §7d / §7e 均返回 FAIL=1（详见下方自检结果）

### 自检结果

`python scripts/selfcheck.py` → **PASS / WARN 0 / FAIL 0 → GREEN**（退出码 0）；全局安装版复跑结果一致；源与全局安装 `diff -r` 完全一致（47 文件）。负向测试在项目外的临时副本执行，未改动源目录。

---

## [v1.3.0] — 2026-11-11 · 每日升级 #4

**主题**：从「边界正确性」扩展到「演进与合规正确性」——补齐 API 契约演进兼容性、隐私与数据生命周期、测试有效性度量三块深水区，并落地提案区的「证据矩阵接进报告」。

**遵循上轮建议**：未重写已覆盖主题（测试设计、OWASP API、性能、前端、全栈发布、AI 原生、可观测性、韧性、数据一致性、非 REST 协议、供应链、i18n、多租户），以 **Enhance 为主、New 为辅**；四层模型与五阶段流程**未改语义**（故按 `self-evolution.md` §7 只升 MINOR）；每轮至少补一条可证伪规则 → 本轮引入 **R-5 / R-6**（共 2 条）。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 动作 | 对象 |
|---|---|
| **New** | `references/contract-evolution-testing.md`、`references/privacy-compliance-testing.md`、`references/test-effectiveness-testing.md`、`assets/contract-evolution-matrix-template.md`、`assets/privacy-matrix-template.md`、`assets/test-effectiveness-template.md` |
| **Enhance** | `SKILL.md`（version 1.3.0、description 触发词、v1.3 增量说明、v1.3 叠加项表、阶段 3 专项维度、R-5/R-6 规则行、参考索引）、`README.md`（徽章 21→24/10→13、问题表 3 行、结构 37→43、速查 3 行、设计要点 R-1~R-6、版本史）、`references/dissect.md`（§8 三条新路由）、`references/quality-gates.md`（§3 R-5/R-6 两行、§8 核对扩为 R-1~R-6）、`assets/report-template.md`（证据矩阵段，落地提案区）、`scripts/selfcheck.py`（§5 三份新模板关键字段检查） |
| **Merge** | `memory/global-lessons.md`：新增 3 组共 18 条 v1.3 教训（契约/隐私/有效性），仍单文件不膨胀；提案区「证据矩阵接进报告」结案为「已吸收」，ROI/移动端/桌面端顺延并续写理由 |
| **Match** | 3 份新手册均在 `dissect.md` §8 与 `SKILL.md` v1.3 叠加项有触发条件；R-5/R-6 在 `SKILL.md`、`quality-gates.md` §3/§8 两处口径一致。以上由 `selfcheck.py` **代码强制**（§7b 路由闭环、§7c 规则双向同步） |
| **Existing** | 五阶段模型、四层能力模型、记忆树 <100 行纪律、双视角、"工具缺失不中止"降级原则、六门禁 12 分、缺陷八字段、R-1~R-4 规则、权限裁决 —— 全部保留，未改语义 |

### 蒸馏来源（本轮实查，均可核查）

| 来源 | URL / 位置 | 关键结论 |
|---|---|---|
| oasdiff（GitHub + 官方站 + raw README） | https://github.com/oasdiff/oasdiff · https://www.oasdiff.com/ | `oasdiff breaking base.yaml revision.yaml` 对 OpenAPI v2/v3 做破坏性变更检测；`--fail-on=ERR` 设为 CI 门禁（非 0 退出即阻断）；`changelog`/`diff` 子命令；支持 v2/v3 |
| Pact 官方文档 / can-i-deploy | https://docs.pact.io/ · https://docs.pact.io/pact_broker/can_i_deploy | 消费者定义契约（只测实际被用到的通信）、提供方 verify、Broker 记录验证结果；`can-i-deploy --pacticipant <name> --version <ver> --to-environment <env>` 退出码非 0 即禁止部署 |
| Zalando RESTful API Guidelines | https://zalando.github.io/restful-api-guidelines/ | MUST NOT break backward compatibility；客户端 MUST 容忍兼容扩展（忽略未知字段）；API 版本放 URL 路径 `/v1/`；弃用须公告 + 过渡期 |
| SemVer 规范 | https://semver.org/ | MAJOR=向后不兼容、MINOR=向后兼容新增、PATCH=向后兼容修复；与 API 变更性质对齐 |
| OWASP API Security Top 10:2023 — API3:2023 | https://owasp.org/API-Security/editions/2023/en/0x11-t10/ | Broken Object Property Level Authorization：过度数据暴露（响应夹带敏感字段）+ 批量分配（请求体塞敏感属性） |
| OWASP Top 10 Privacy Risks | https://owasp.org/www-project-top-10-privacy-risks/ | P1 传输同意 / P2 处理同意 / P3 无理监视 / P4 不安全存储 / P5 不安全传输 / P6 不透明政策 / P7 二次利用 / P8 主动联系 / P9 数据泄露 / P10 不合规 |
| GDPR 第 5 条 / 第 17 条 | https://gdpr-info.eu/art-5-gdpr/ · https://gdpr-info.eu/art-17-gdpr/ | Art.5：数据最小化、目的限制、存储限制、完整性与保密性；Art.17：被遗忘权——无不当延迟删除、对接收方/链接/副本/复制的处置义务 |
| OWASP Logging Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html | 不记录 PII/令牌/密码；防范日志注入（转义换行/分隔符）；日志数据最小化 |
| DORA 指标（Google / dora.dev） | https://dora.dev/guides/dora-metrics/ · https://sre.google/sre-book/service-level-objectives/ | 四指标：部署频率、变更前置时间、**变更失败率 CFR=失败部署/总部署（Elite 0–15%）**、恢复时长 MTTR（Elite <1h） |
| Google 测试博客（flaky tests） | https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html | 约 1–2% 测试会 flaky；靠重复运行检测；quarantine 而非无限重试；flaky 会延迟真实回归发现 |
| Martin Fowler《Eradicating Non-Determinism in Tests》 | https://martinfowler.com/articles/nonDeterminism.html | 非确定性根因：时钟/时间、随机数、外部依赖、共享状态、异步等待；修复：注入时钟、固定种子、mock、自清理、显式等待 |
| 变异测试工具（Stryker / mutmut / Pitest / cargo-mutants） | 各自官方文档 | 变异得分 = 被杀死变异体/变异体总数；低分 = 伪测试；与覆盖率互补 |

**口径诚实标注**：oasdiff 破坏性变更规则集以 `--fail-on=ERR` 退出码为准，手册未逐条罗列全部规则项（已列最常见类别并注明「以退出码为准」）；OWASP 隐私 Top10 的 P1–P10 编号取自该列表原始命名，落地时按项目实际数据处理链路核对，不要求全中；Pact 的 `can-i-deploy` 命令以官方页面给出的语法为准，具体 provider verify CLI 随语言而定（手册未臆造参数）。

### 主要改动

1. **API 契约演进兼容性**（`contract-evolution-testing.md` + 证据模板）：三条认知（本地能跑≠老客户端不挂、没改路径≠没改契约、双方同规范≠都遵守）、oasdiff `breaking --fail-on=ERR` 命令原文与退出码、Pact 消费者驱动契约与 `can-i-deploy` 闸门、Zalando 兼容演进规范与容忍读取、C-1~C-12 测试卡
2. **R-5 契约演进**：声称「向后兼容 / 可安全部署」须附 oasdiff 退出码 + 输出行 + Pact verify/can-i-deploy + 容忍读取验证；明确定义不适用写法（无对外契约的单体工具）
3. **隐私与数据生命周期**（`privacy-compliance-testing.md` + 证据模板）：PII 字段分类与最小化（GDPR Art.5）、API3 过度暴露/批量分配、删除权端到端验证（GDPR Art.17，主库+缓存/索引/副本）、日志 PII 与注入（OWASP Logging CS）、OWASP 隐私 Top10 映射、P-1~P-12 测试卡
4. **R-6 隐私与数据生命周期**：声称「隐私合规 / 数据可删除」须附 PII 分类 + 响应白名单 + 删除权端到端 + 日志脱敏；明确「接口 200 不能推出没多给、主库删了不能推出全链路删干净」
5. **测试有效性度量**（`test-effectiveness-testing.md` + 模板）：DORA 四指标（CFR/MTTR 口径）、缺陷逃逸率、flaky 配额与 quarantine（反模式：retries 掩盖）、变异得分对照覆盖率、E-1~E-10 度量卡；作为度量纪律支撑 Go/No-Go（本轮未单列 R-7，避免与已有六条规则过度膨胀）
6. **证据矩阵接进报告**（落地提案区）：`report-template.md` 新增「证据矩阵」段，把 R-1~R-6 结论与六份证据模板固定挂接，缺证据即标 BLOCKED；同时 `selfcheck.py` §5 补三份新模板关键字段检查
7. **路由闭环与规则同步**：3 份新手册均接入 `dissect.md` §8 + `SKILL.md` v1.3 叠加项；R-5/R-6 在 `SKILL.md`、`quality-gates.md` §3/§8 三处口径一致，由 `selfcheck.py` §7b/§7c 代码强制
8. **经验治理**：`global-lessons.md` 新增契约 6 条、隐私 7 条、有效性 5 条共 18 条；提案区「证据矩阵接进报告」结案，ROI/移动端/桌面端顺延并续写理由

### 回归检查

- [x] 五阶段模型闭环未变，`SKILL.md` 的 todo 示例（4 条 MRE、含越权 S1）逐字保留
- [x] 四层能力模型语义未变（L1~L4 仍是四层，v1.3 内容以「横向叠加项」呈现，不构成 MAJOR）
- [x] 记忆树 <100 行纪律保留；`assets/tree-template.md` 未改，仍 <100 行
- [x] 「工具缺失不中止」降级原则保留，且 3 份新手册每份都有 L0 零依赖路径（diff / git show / git grep）
- [x] 运行时不擅自改本体的安全约束保留；权限裁决原文未改
- [x] 原有文件引用路径未失效（由 `selfcheck.py` 断链检查验证）
- [x] 新增路由不产生孤儿文档（由 `selfcheck.py` §7b 路由闭环验证）
- [x] R-1~R-6 在 `SKILL.md`、`quality-gates.md` §3/§8 两处口径一致（由 `selfcheck.py` §7c 双向同步验证）
- [x] 六门禁 12 分、缺陷八字段、Flaky 治理、变异测试等关键字段仍在（由 `selfcheck.py` 字段检查验证）
- [x] 报告模板新增证据矩阵段未破坏原有 PASS/FAIL 与 Go/No-Go 结构

### 自检结果

`python scripts/selfcheck.py` → **PASS / WARN 0 / FAIL 0 → GREEN**（退出码 0）；全局安装版复跑结果一致；源与全局安装 `diff -r` 完全一致（43 文件）。

**门禁有效性负向测试**（在临时副本上篡改，全程不触碰源目录）：

| 篡改动作 | 期望 | 实际结果 |
|---|---|---|
| 从 `SKILL.md` 悄悄删除 `R-5` 的规则定义行 | BLOCKED | `exit=1`，`[FAIL] quality-gates.md 出现 SKILL.md 未定义的规则（可能被悄悄删除或编号写错）` 类失败（§7c 双向比对） |
| 删除 `dissect.md` §8 中 `contract-evolution-testing.md` 的路由行 | BLOCKED | `exit=1`，`[FAIL] 孤儿文档: contract-evolution-testing.md: 缺 dissect.md §8 路由`（§7b） |

两例都证明 §7b / §7c 是**可证伪的门禁**而非文字声明；§7c 仍是「SKILL.md 定义集 ↔ quality-gates.md 引用集」双向比对，避免「删掉一条规则反而全绿」。

> 门禁说明：按 `self-evolution.md` §3，FAIL > 0 即停止升版本/同步/提交。本轮严格按 ⑥ 自检 → ⑦ 版本 → ⑧ 同步 → ⑨ 提交的顺序执行。

---

## [v1.2.0] — 2026-11-11 · 每日升级 #3

**主题**：从「系统行为」扩展到「交付链与边界正确性」——补齐软件供应链/制品完整性、国际化与本地化、多租户隔离三块深水区，并吸收提案区的 i18n 提案。

**遵循上轮建议**：未重写已覆盖主题（测试设计、OWASP API、性能、前端、全栈发布、AI 原生、可观测性、韧性、数据一致性、非 REST 协议），以 **Enhance 为主、New 为辅**；四层模型与五阶段流程**未改语义**（故按 `self-evolution.md` §7 只升 MINOR）；每轮至少补一条可证伪规则 → 本轮引入 **R-3 / R-4**（共 2 条）。

**本轮修正的两处真实缺口（自我进化证据）**：

1. v1.1 CHANGELOG 声称「孤儿文档门禁由 `selfcheck.py` 索引覆盖检查验证」**并不准确**——旧脚本只检查 references 是否被 `SKILL.md`/`README.md` 提及，从未校验 `dissect.md` §8 路由表。本轮在 `scripts/selfcheck.py` 新增 §7b，逐份核对「§8 路由 + SKILL.md 触发条件」双条件（L1 元手册白名单豁免），缺一即 **FAIL**。
2. 上轮新增的 4 份手册都有路由，但更早的 `references/performance-testing.md` 至今**没有 §8 路由**。本轮补齐该行。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 动作 | 对象 |
|---|---|
| **New** | `references/supply-chain-testing.md`、`references/i18n-localization-testing.md`、`references/multi-tenancy-testing.md`、`assets/supply-chain-evidence-template.md`、`assets/i18n-matrix-template.md`、`assets/tenant-isolation-matrix-template.md` |
| **Enhance** | `SKILL.md`（version 1.2.0、description 触发词、v1.2 叠加项表、阶段 1/3/4、判 bug 第 7 条、R-3/R-4、参考索引）、`README.md`（徽章/问题表/结构 31→37/速查/设计要点/版本史）、`references/dissect.md`（§1 栈指纹、§6 设施盘点、§7 攻击面、§8 补 `performance-testing.md` + 3 条新路由、路由闭环说明、产出格式）、`references/quality-gates.md`（§3 加 R-3/R-4 两行、§8 核对项扩为 R-1~R-4）、`references/tools.md`（专项工具表 4 行、可用性探测、降级纪律）、`references/fullstack-integration.md`（§6 Gate 1/3/4 证据 + v1.2 分流表与打分纪律）、`references/frontend-testing.md`（§6 i18n 联动、§8 判 bug 第 8 条）、`references/security-testing.md`（§5 三条分工 + 边界说明）、`references/self-evolution.md`（§3 自检范围、§5 门禁改为代码强制）、`scripts/selfcheck.py`（§7b 路由闭环、§7c 可证伪规则同步、3 份新模板字段检查） |
| **Merge** | `memory/global-lessons.md`：新增 3 组共 20 条 v1.2 教训，仍保持单文件不膨胀；i18n 提案结案为「已吸收」，ROI / 移动端 / 桌面端提案标注顺延理由；不重复抄写手册正文，只留「教训 — 应用」一行式条目 |
| **Match** | 3 份新手册 + 早前遗漏的 `performance-testing.md` 均在 `dissect.md` §8 与 `SKILL.md` 叠加项有触发条件；R-3/R-4 在 `SKILL.md`、`quality-gates.md` §3/§8、Go/No-Go 三处口径一致。以上均由 `selfcheck.py` **代码强制**，不再是人工声明 |
| **Existing** | 五阶段模型、四层能力模型、记忆树 <100 行纪律、双视角、"工具缺失不中止"降级原则、六门禁 12 分、缺陷八字段、权限裁决、`SKILL.md` 的 todo 示例 —— 全部保留，未改语义 |

### 蒸馏来源（本轮实查，均可核查）

| 来源 | URL / 位置 | 关键结论 |
|---|---|---|
| OWASP Top 10:2025 A03（官方） | https://owasp.org/Top10/2025/A03_2025-Software_Supply_Chain_Failures/ | 依赖漏洞、恶意依赖、CI/CD 污染、制品篡改、供应链变更管理；postinstall 蠕虫类场景 |
| OWASP Software Supply Chain Security CS | https://cheatsheetseries.owasp.org/cheatsheets/Software_Supply_Chain_Security_Cheat_Sheet.html | 依赖锁定与签名验证、SBOM production + consumption 双端自动化、ephemeral 构建、protected branch、私有 registry 无旁路、最终二进制**供应方与消费方双侧**扫描、SAST 结果须人工复核 |
| OWASP Dependency Graph & SBOM CS | https://cheatsheetseries.owasp.org/cheatsheets/Dependency_Graph_SBOM_Cheat_Sheet.html | 「A component missing from an SBOM is not evidence that it is absent from the software」；direct + transitive；schema 校验与覆盖缺口声明；**签名 attestation 绑定制品 digest**（分别签名不建立关系）；VEX 复核；签名「do not prove that an SBOM is accurate or complete」 |
| OWASP Vulnerable Dependency Management CS | https://cheatsheetseries.owasp.org/cheatsheets/Vulnerable_Dependency_Management_Cheat_Sheet.html | 「Silencing the scanner or bumping a version string is not remediation」；补丁验证须未打补丁失败、打补丁通过，「A test that passes in both cases proves nothing about the patch」 |
| OWASP Multi_Tenant_Security_Cheat_Sheet | https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html | client-supplied tenant identifier 只是 selector；「Query parameterization prevents injection, not cross-tenant access」；共享 queue/topic 与 object prefix 不是隔离边界；RLS / `SET LOCAL` / 连接池复用 / deployed request role / WORM audit / offboarding / 双租户 backup 恢复；intentional sharing 须 exact permitted path 且 no broader access |
| SLSA v1.0 spec（levels / provenance / verifying-artifacts） | https://slsa.dev/spec/v1.0/levels · https://slsa.dev/spec/v1.0/provenance · https://slsa.dev/spec/v1.0/verifying-artifacts | Build L0~L3；`predicateType=https://slsa.dev/provenance/v1`；`buildDefinition`/`runDetails`/`buildType`/`externalParameters`/`builder.id` 为 L1 REQUIRED；`externalParameters` untrusted 须下游验证；`Consumers MUST accept only specific signer-builder pairs`；验证三步（level → expectations → 可选递归依赖） |
| NTIA SBOM 最小要素 | https://www.ntia.gov/SBOM | supplier / component name / version / unique identifier / dependency relationship / author / timestamp 七要素 |
| npm `ci` 官方文档 | https://docs.npmjs.com/cli/v10/commands/npm-ci | 必须有 lockfile；package.json 与 lock 不一致时**退出错误**而非更新 lock；不写回 package.json / lock |
| Microsoft Learn《Test cases for locale awareness》 | https://learn.microsoft.com/en-us/globalization/testing/test-cases-for-locale-awareness | 日期/时间/数字/货币/日历/时区/DST、CSV 分隔符、collation（土耳其语 dotted/dotless I、`côte < coté`、`Å`、`CH`）、IME、文本扩展、伪本地化、伪镜像、font fallback；`pseudolocalization "can never catch all issues"`；数据跨 app language × OS language 互通 |
| W3C International《Structural markup and right-to-left text in HTML》 | https://www.w3.org/International/questions/qa-html-dir | base direction 用 HTML `dir` **而非 CSS**；`lang` ≠ 方向；`<html lang="ar" dir="rtl">`；`dir="auto"` 按首个强方向性字符；`<bdi>`；`dirname` 提交方向；logical properties；textarea/pre 多段落方向；滚动条属 browser chrome 不算缺陷 |
| GitHub 供应链工具链 | https://github.com/anchore/syft · https://github.com/anchore/grype · https://github.com/google/osv-scanner · https://github.com/sigstore/cosign · https://github.com/slsa-framework/slsa-verifier · https://github.com/aquasecurity/trivy | Syft `-o cyclonedx-json` / `-o spdx-json`；Grype `sbom:`；OSV-Scanner V2 beta `scan source -r` / `scan image`；Cosign keyless 须 `--certificate-identity` + `--certificate-oidc-issuer`；slsa-verifier `verify-artifact` 的 artifact 是位置参数、`--source-uri` 只收 GitHub URI；只记录页面明确给出的命令，不臆造参数 |
| `awesome-qa-skills` / `awesome-qa-prompt`（GitHub） | https://github.com/naodeng/awesome-qa-skills · https://github.com/naodeng/awesome-qa-prompt | 复核治理分类与证据门禁口径，确认本轮仍走 Existing/Enhance/Merge/Match/New，不引入新流程层级 |
| 用户附加技能 `frontend-dev` / `fullstack-dev`（二次蒸馏） | 本地 `~/.workbuddy-ai/skills/` | frontend-dev：无 placeholder URL、GPU-only 动画、`useEffect` cleanup `ctx.revert()`、`prefers-reduced-motion`、动态视口、font fallback、运行时渲染验证；fullstack-dev：结构化日志 request_id、`/health` vs `/ready`、迁移 up/down、缓存 TTL 与写失效、后台任务幂等与 DLQ、跨边界错误映射、六门禁 12 分 |

**口径诚实标注**：OWASP Dependency Graph & SBOM Cheat Sheet 引用的是 `slsa.dev/spec/v1.2/verifying-artifacts`，但本轮逐条核验的是 **v1.0** 的 levels / provenance / verifying-artifacts 三个页面，v1.2 仅记录链接、未逐条比对，故手册与本报告均不得写成「已核验 v1.2」。W3C `qa-html-dir` 是 structural markup 页面，把 inline bidi 指向另文，页面本身**没有 `bdo` 规则**可审查，故未伪造相关 guidance。OWASP 多租户 CS **没有独立 Search/Index isolation 章节**，搜索用例是从 tenant-owned access path 通用规则推导，手册已显式标注。

### 主要改动

1. **软件供应链与制品完整性**（`supply-chain-testing.md` + 证据模板）：三条认知打底（SBOM 缺项 ≠ 不存在、签名有效 ≠ 安全、生成与验证须成对）、依赖/锁文件 D-1~D-10、SBOM B-1~B-10（NTIA 七要素、覆盖缺口、attestation 绑 digest）、Syft/Grype/OSV-Scanner/Trivy/Cosign/slsa-verifier 真实命令、SLSA Build L0~L3 判级与 provenance 验证三步、CI/CD 完整性静态审查、L0 零依赖降级
2. **R-3 制品完整性**：要求 `sha256` + SBOM 原件 + 验证命令原文/退出码/输出行 + 扫描输出；明确定义不适用写法，禁止把「签名有效」升级成「制品无漏洞」
3. **国际化与本地化**（`i18n-localization-testing.md` + 矩阵模板）：代表 locale × 六维矩阵、伪本地化四步与五类缺陷、伪镜像、F-1~F-8 格式与数据互通、collation/大小写/复数、W3C RTL 硬规则表（`dir`/`dir="auto"`/`dirname`/`<bdi>`/logical properties）、字体与 IME、静态审查清单、`BLOCKED` 降级写法
4. **多租户隔离**（`multi-tenancy-testing.md` + 矩阵模板）：双租户相同 ID 夹具与一票否决四条、TC-1~TC-8、IDOR/SEARCH、DB/RLS/连接池（含 `rolsuper`/`rolbypassrls`、`SET LOCAL`、连接复用）、CACHE/QUEUE/noisy-neighbor、FILE/offboarding/BACKUP（含 `tenants/acme/` 尾斜杠、双租户恢复到独立资源）、LOG/AUDIT/ADMIN、L0 静态降级
5. **R-4 租户隔离**：要求夹具 + 一票否决逐条结果 + 连接复用/noisy-neighbor/双租户备份恢复三项原始输出 + intentional sharing 的 "no broader access" 证据；明确「一条 404 不构成通过」
6. **路由闭环落地到代码**：`selfcheck.py` §7b 双条件核对（§8 路由 + SKILL.md）、§7c 可证伪规则 R-1~R-4 在 `quality-gates.md` 同步、3 份新模板字段检查；补齐 `performance-testing.md` 缺失的 §8 路由；`self-evolution.md` §5 改为「代码强制」表述
7. **交叉引用而非重写**：`security-testing.md` §5 划清「运行时输入与权限 / 交付链来源与完整性 / 共享基础设施边界」三者分工；`fullstack-integration.md` §6 加 v1.2 分流表，明确三类新证据各归 Gate 1/3/4 且「是 2 分的前置条件，不是额外加分」；`frontend-testing.md` §6/§8 加 i18n 联动与 tofu/RTL 判 bug 条款
8. **工具与降级**：`tools.md` 加 4 行专项工具（SBOM/签名/i18n/双租户）与探测循环，每行的降级都落到 `sha256sum`、`git grep`、静态审查，并强制 `BLOCKED` 而非 Pass
9. **经验治理**：`global-lessons.md` 新增交付链 6 条、i18n 6 条、多租户 8 条共 20 条；i18n 提案结案，ROI / 移动端 / 桌面端顺延并写明理由
10. **文档与版本**：`SKILL.md` / `README.md` / `CHANGELOG.md` 同步到 v1.2.0；README 文件结构 31 → 37、references 18 → 21、assets 7 → 10

### 回归检查

- [x] 五阶段模型闭环未变，`SKILL.md` 的 todo 示例（4 条 MRE、含越权 S1）逐字保留
- [x] 四层能力模型语义未变（L1~L4 仍是四层，v1.2 内容以「横向叠加项」呈现，不构成 MAJOR）
- [x] 记忆树 <100 行纪律保留；`assets/tree-template.md` 未改，仍 <100 行
- [x] 「工具缺失不中止」降级原则保留，且 3 份新手册每份都有 L0 零依赖路径（`sha256sum`/`git grep`/静态审查）
- [x] 运行时不擅自改本体的安全约束保留；权限裁决原文未改
- [x] 原有文件引用路径未失效（由 `selfcheck.py` 断链检查验证）
- [x] 新增路由不产生孤儿文档（由 `selfcheck.py` **§7b 真正的路由闭环检查**验证；v1.1 只查索引的缺口已修复）
- [x] R-1~R-4 在 `SKILL.md`、`quality-gates.md` §3/§8、各手册结论三处口径一致（由 `selfcheck.py` §7c 验证）
- [x] 六门禁 12 分与缺陷八字段、Flaky 治理等关键字段仍在（由 `selfcheck.py` 字段检查验证）

### 自检结果

`python scripts/selfcheck.py` → **PASS 21 / WARN 0 / FAIL 0 → GREEN**（退出码 0）；全局安装版复跑结果一致；源与全局安装 `diff -r` 完全一致（37 文件）。详见本轮交付报告。

**门禁有效性负向测试**（在临时副本上篡改，全程不触碰源目录）：

| 篡改动作 | 期望 | 实际结果 |
|---|---|---|
| 删除 `dissect.md` §8 中 `supply-chain-testing.md` 的路由行 | BLOCKED | `exit=1`，`[FAIL] 孤儿文档: supply-chain-testing.md: 缺 dissect.md §8 路由` |
| 从 `SKILL.md` 悄悄删除 `R-4` 的规则定义行 | BLOCKED | `exit=1`，`[FAIL] quality-gates.md 出现 SKILL.md 未定义的规则（可能被悄悄删除或编号写错）: R-4` |

两例都证明 §7b / §7c 是**可证伪的门禁**而非文字声明；§7c 特意做成「SKILL.md 定义集 ↔ quality-gates.md 引用集」双向比对，避免单向检查放过「删掉一条规则反而全绿」的情况。这也是对 v1.1「声称由自检验证但脚本没实现」的直接纠偏。

> 门禁说明：按 `self-evolution.md` §3，FAIL > 0 即停止升版本/同步/提交。本轮严格按 ⑥ 自检 → ⑦ 版本 → ⑧ 同步 → ⑨ 提交的顺序执行；⑦ 与 ⑥ 的先后通过"先写版本再复跑自检"闭环验证。

---

## [v1.1.0] — 2026-11-11 · 每日升级 #2

**主题**：从「响应断言」扩展到「系统内部行为验证」——补齐可观测性/Trace 驱动、韧性与故障注入、数据一致性、非 REST 协议四块深水区，并吸收 v1.0 遗留的 GraphQL/gRPC 提案。

**遵循上轮建议**：未重写已覆盖主题（测试设计、OWASP、性能、前端、全栈发布、AI 原生、自我进化），以 **Enhance 为主、New 为辅**；四层模型与五阶段流程**未改语义**（故按 `self-evolution.md` §7 只升 MINOR）；每轮新增至少一条可证伪规则 → 本轮引入 R-1 / R-2。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 动作 | 对象 |
|---|---|
| **New** | `references/observability-testing.md`、`references/chaos-resilience.md`、`references/data-integrity-testing.md`、`references/protocol-testing.md`、`assets/protocol-matrix-template.md`、`assets/resilience-runbook-template.md` |
| **Enhance** | `SKILL.md`（description 触发词、能力层叠加项、阶段 1/3/4、R-1/R-2、参考索引）、`README.md`（徽章/结构/速查/版本史）、`references/dissect.md`（栈指纹、协议入口、测试设施、观测面与依赖拓扑、路由表、产出格式）、`references/api-testing.md` §7 分流、`references/fullstack-integration.md` §5 分流、`references/performance-testing.md` §2 边界、`references/frontend-testing.md` §2.1 运行时实测、`references/quality-gates.md` §3/§8、`references/tools.md` 专项工具表、`references/self-evolution.md` §5 孤儿文档门禁 |
| **Merge** | `memory/global-lessons.md`：v1.0 中与新手册重复的条目改写为交叉引用（不二次抄写），提案区两项结案；新增 4 组 v1.1 教训但控制在同一文件内，不另建文件 |
| **Match** | 全部新增手册均已在 `dissect.md` §8 路由表与 `SKILL.md` 叠加项中有明确触发条件（满足本轮新加的「孤儿文档」门禁）；`selfcheck.py` 索引覆盖检查验证 |
| **Existing** | 五阶段模型、记忆树 <100 行纪律、双视角、"工具缺失不中止"的降级原则、六门禁 12 分、缺陷八字段、权限裁决 —— 全部保留，未改语义 |

### 蒸馏来源（本轮实查，均可核查）

| 来源 | URL / 位置 | 关键结论 |
|---|---|---|
| OpenTelemetry Traces（官方） | https://opentelemetry.io/docs/concepts/signals/traces/ | Span Context = Trace ID/Span ID/TraceFlags/TraceState；根 span 无 parent；`status` 三态 Unset/Error/Ok；属性宜在 span 创建时添加以便 SDK 采样；带独立时间戳用 Span Event；Context Propagation 是分布式追踪核心 |
| OpenTelemetry Semantic Conventions（官方） | https://opentelemetry.io/docs/concepts/semantic-conventions/ | 统一属性命名（traces/metrics/logs/profiles/resources）才能跨库跨语言关联；各服务自造属性名 = 断言写不出来 |
| W3C Trace Context（W3C Recommendation） | https://www.w3.org/TR/trace-context/ | `traceparent: 00-<32hex trace-id>-<16hex parent-id>-<2hex flags>`；全零 ID 非法；最低合规 MUST 转发且保证 trace 不断；除 restart trace 外 `trace-id` 不得变 |
| Tracetest 官方文档 + GitHub | https://docs.tracetest.io/ · https://github.com/kubeshop/tracetest | `trigger + selector + assertions` YAML；断言响应 + trace 数据、span 时长、通配断言（所有 db span <100ms）、MQ/异步/外部 API 等副作用；CLI 进 CI |
| Google SRE Book《Service Level Objectives》 | https://sre.google/sre-book/service-level-objectives/ | SLI 应按分布（percentiles）而非平均；SLO = SLI + target + 测量条件；SLA 含"未达成后果"；错误预算 = 允许未达成的比率，用于决定何时发布；不要按当前性能定目标 |
| Principles of Chaos Engineering（官方） | https://principlesofchaos.org/ | 四步实验（定义稳态 → 假设对照/实验组持续 → 引入真实事件 → 找差异**证伪**）；五条高级原则；稳态用可测量输出（吞吐/错误率/延迟分位数），关注系统行为而非内部属性 |
| Shopify/Toxiproxy（GitHub） | https://github.com/Shopify/toxiproxy | 确定性故障注入；HTTP API :8474；toxics: latency(±jitter)/bandwidth/slow_close/timeout/reset_peer/slicer/limit_data/packet_loss；`stream` 上下游、`toxicity` 默认 1.0；`down` 是 `enabled=false`；`POST /reset` 兜底 |
| chaos-mesh/chaos-mesh（GitHub） | https://github.com/chaos-mesh/chaos-mesh | CNCF incubating；K8s CRD 定义实验；Pod/network/DNS/HTTP/I-O/time/stress/kernel 等故障；Schedule/Workflow/StatusCheck；RBAC 收窄作用域 |
| litmuschaos/litmus（GitHub） | https://github.com/litmuschaos/litmus | ChaosExperiment（故障模板）→ ChaosEngine（绑定 workload + probes 稳态约束）→ ChaosResult（verdict、revert/rollback 状态、Prometheus 指标）；可作 CI/CD stage |
| jepsen-io/jepsen（GitHub） | https://github.com/jepsen-io/jepsen | generator 生成操作 → nemesis 注入故障 → history 记录每个操作起止 → checker 分析正确性；借用「操作历史 + 故障 + 不变量检查」思路 |
| OWASP GraphQL Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html | introspection/GraphiQL/字段建议；深度·数量·query cost 限制；batching 绕过按请求数限流并爆破 OTP；resolver 级授权（edges 与 nodes 都要查）；allowlist 输入；生产不返回 stack trace |
| gRPC 官方 Status Codes | https://grpc.io/docs/guides/status-codes/ | 17 个码；`NOT_FOUND`/`PERMISSION_DENIED`/`UNAUTHENTICATED`/`RESOURCE_EXHAUSTED` 有严格区分；`DEADLINE_EXCEEDED` 时操作**可能已成功**；`UNAVAILABLE` 可退避重试但非幂等操作不安全；`DATA_LOSS`/`INTERNAL` 是严重错误 |
| fullstorydev/grpcurl（GitHub） | https://github.com/fullstorydev/grpcurl | JSON → protobuf；依赖 server reflection 或 `-proto`/`-protoset`；`list`/`describe`；`-plaintext`、`-H` metadata；`protoc --descriptor_set_out --include_imports` |
| PostgreSQL 事务隔离（官方） | https://www.postgresql.org/docs/current/transaction-iso.html | 四类异常（脏读/不可重复读/幻读/序列化异常）× 四隔离级别对照表；PG 默认 Read Committed 允许后三者；Repeatable Read 用快照隔离且 PG 中不出现幻读；Serializable 全禁但需准备重试 |
| 用户附加技能 `frontend-dev` / `fullstack-dev`（二次蒸馏） | 本地 `~/.workbuddy-ai/skills/` | frontend-dev：GPU-only 动画属性、`useEffect` cleanup `ctx.revert()`、重库 lazy-load、`prefers-reduced-motion`、动态视口；fullstack-dev：结构化日志 request_id、`/health` vs `/ready`、迁移 up/down、缓存 TTL 与写失效、后台任务幂等与 DLQ、SSE/WS 重连退订、优雅停机 |

### 主要改动

1. **可观测性驱动测试**（`observability-testing.md`）：三大信号最小判据、W3C `traceparent` 格式与转发规则、五步零依赖链路实验、8 条 span 断言清单、Tracetest YAML、SLI/SLO/错误预算写成可断言门禁、日志脱敏与 `/health` vs `/ready`
2. **韧性与故障注入**（`chaos-resilience.md`）：适用边界与安全红线、稳态假设四步协议、8 类故障注入矩阵、L0 shell / L1 Toxiproxy / L2 K8s 三级工具阶梯、恢复核对 6 条、演练记录模板
3. **数据一致性**（`data-integrity-testing.md`）：三重断言、迁移 7 条用例与 checksum 证据、PG 隔离级别对照与并发 5 条、缓存/双写/CDC/读副本/幂等/死信、SQL 对账脚本、不变量优于期望值
4. **非 REST 协议**（`protocol-testing.md` + 矩阵模板）：**吸收 v1.0 遗留提案**，逐类型给出 GraphQL 12 项、gRPC 11 项、WS/SSE 10 项用例清单，含 curl / grpcurl / protoset 命令与四协议认证矩阵落点
5. **两条可证伪规则**：R-1（链路结论须有 ≥2 组件的同 id 原始证据）、R-2（韧性结论须有可复现的故障注入记录），各自**明确写了不适用条件与降级写法**，并接入 `quality-gates.md` §3 Go/No-Go 与 §8 交付核对
6. **解剖增强**：`dissect.md` 新增协议与可观测性栈指纹、非 REST 入口追踪、观测面/依赖拓扑/故障域盘点、4 条新路由与「叠加项按触发条件选，不为凑维度造测试」
7. **路由闭环**：所有新增手册都有 `dissect.md` §8 触发条件与 `SKILL.md` 叠加项；`self-evolution.md` §5 新增「孤儿文档」门禁，防止只加文件不加路由
8. **交叉引用而非重写**：`api-testing.md` §7、`fullstack-integration.md` §5、`performance-testing.md` §2 各加一段分流，明确"REST 底座 / 单次负载表现 / 时间窗 SLO / 依赖故障行为"的边界
9. **前端运行时实测**（`frontend-testing.md` §2.1）：从 `frontend-dev` 二次蒸馏出首屏资源、持续动画 30~60s、卸载 cleanup、动态视口、reduced-motion 等 6 项**必须真实渲染**的判据，并明确静态核对不得冒充运行时结论
10. **经验治理**：`global-lessons.md` 吸收提案（GraphQL/gRPC 已吸收、统一证据模板驳回理由保留）、新增 4 组共 23 条 v1.1 教训、重复项改写为交叉引用，控制为单文件不膨胀
11. **文档与版本**：`SKILL.md` / `README.md` / `CHANGELOG.md` 同步到 v1.1.0；README 文件结构 25 → 31、徽章 references 14 → 18、templates 5 → 7

### 回归检查

- [x] 五阶段模型闭环未变，`SKILL.md` 的 todo 示例（4 条 MRE、含越权 S1）逐字保留
- [x] 四层能力模型语义未变（L1~L4 仍是四层，新增内容以「横向叠加项」呈现，不构成 MAJOR）
- [x] 记忆树 <100 行纪律保留；`assets/tree-template.md` 未改，仍 <100 行
- [x] 「工具缺失不中止」降级原则保留，且新手册每份都有 L0 零依赖路径（curl+grep / shell 并发 / 静态审查）
- [x] 运行时不擅自改本体的安全约束保留；权限裁决原文未改
- [x] 原有文件引用路径未失效（由 `selfcheck.py` 断链检查验证）
- [x] 新增路由不产生孤儿文档（由 `selfcheck.py` 索引覆盖检查验证）
- [x] 六门禁 12 分与缺陷八字段、Flaky 治理等关键字段仍在（由 `selfcheck.py` 字段检查验证）

### 自检结果

`python scripts/selfcheck.py` → **PASS 16 / WARN 0 / FAIL 0 → GREEN**（退出码 0）；全局安装版复跑结果一致；源与全局安装 `diff -r` 完全一致（31 文件）。详见本轮交付报告。

> 门禁说明：按 `self-evolution.md` §3，FAIL > 0 即停止升版本/同步/提交。本轮严格按 ⑥ 自检 → ⑦ 版本 → ⑧ 同步 → ⑨ 提交的顺序执行。

---

## [v1.0.0] — 2026-11-11 · 每日升级 #1

**主题**：从「通用项目测试流程」升级为「分层能力 + 专项手册 + 证据化门禁 + 可追溯自我进化」体系。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 动作 | 对象 |
|---|---|
| **Enhance** | `SKILL.md`（能力层路由、六维专项、权限裁决、参考索引）、`README.md`、`references/dissect.md`（测试设施/攻击面/路由）、`references/tools.md`（专项工具表/探测/降级纪律）、`references/personas.md`（4 个新画像 + 手册映射）、`references/memory-tree.md`（版本/严重度/三类待办）、`references/evolution.md`（四问 + 四层视角 + 权限裁决）、`assets/tree-template.md`、`assets/report-template.md`、`memory/global-lessons.md` |
| **New** | 9 份手册、3 份模板、1 个自检脚本、CHANGELOG、.gitignore |
| **Existing** | 五阶段模型、记忆树 <100 行纪律、双视角、"跑不起来也继续测"的降级原则 —— 全部保留，未改语义 |

### 蒸馏来源（可核查）

| 来源 | URL / 位置 | 关键结论 |
|---|---|---|
| OWASP API Security Top 10 – 2023（官方） | https://owasp.org/API-Security/editions/2023/en/0x11-t10/ | 十项官方名称逐条对齐；API3 合并过度暴露+批量分配；API1 BOLA 居首 |
| RFC 9457 Problem Details (2023) | https://www.rfc-editor.org/rfc/rfc9457.html | `application/problem+json`；标准成员全部可选；`status` 须与实际 HTTP 码一致；扩展成员客户端须忽略 |
| Playwright Test Agents（官方） | https://playwright.dev/docs/test-agents | planner/generator/healer 三件套、`npx playwright init-agents`、specs/ 与 seed.spec.ts 约定、healer 可跳过疑似损坏功能 |
| Schemathesis 官方文档 | https://schemathesis.readthedocs.io/en/stable/ | OpenAPI/GraphQL/gRPC 属性与状态化测试、每个发现自带最小 curl 复现 |
| awesome-qa-skills (GitHub) | https://github.com/naodeng/awesome-qa-skills | 四层能力体系、`AI for QA` ≠ `Testing for AI`、Skill Engineering 治理、Existing/Enhance/Merge/Match/New、证据门禁与四类结论区分 |
| 用户附加技能 `fullstack-dev` | 本地 `~/.workbuddy-ai/skills/fullstack-dev/` | testing-strategy.md（金字塔/隔离/工厂/Pact/k6/预算）、release-checklist.md（六门禁 12 分、金丝雀停止线、回滚预案）、§12 错误映射、Anti-Patterns |
| 用户附加技能 `frontend-dev` | 本地 `~/.workbuddy-ai/skills/frontend-dev/` | Quality Gates（无占位 URL、本地资源、动态视口、五态）、§2.4 动效性能与清理、§2.6 无障碍（reduced-motion/焦点/aria-live） |
| WCAG 2.2 / Core Web Vitals 公开口径 | 检索汇总 | LCP ≤2.5s / INP ≤200ms / CLS ≤0.1（P75）；WCAG 2.2 的 2.4.11 焦点不被遮挡、2.5.8 目标 ≥24px |
| 测试智能体标准与行业动态（2026） | 检索汇总 | CAICT/AIIA《测试智能体》标准、Playwright v1.56+ 内置 Agents、AI 生成测试需配套审查（伪测试/弱断言） |

### 主要改动

1. **能力分层路由**：L1 Core / L2 Engineering / L3 Production / L4 AI Native + `dissect.md` §8 项目形态→手册路由表
2. **测试设计体系**：九式设计手法、六维矩阵 v2、风险分优先级、覆盖口径与退出标准（`test-design.md`）
3. **API 与安全专项**：端点十项必测、RFC 9457 错误契约、OWASP API Top 10 逐项测试卡、认证授权矩阵、输入向量库、幂等/并发/限流、schemathesis
4. **性能专项**：五种负载形态、p50/p95/p99 与 Little's Law、k6 thresholds、性能预算、瓶颈定位顺序、轻量 shell 降级
5. **前端专项**：五态矩阵、WCAG 2.2 实测动作、Core Web Vitals、跨边界错误码映射、占位资源纪律、Playwright Test Agents 接入
6. **全栈与发布**：测试金字塔/隔离策略/集成边界、六门禁 12 分 Go/No-Go、金丝雀与回滚预案
7. **证据与有效性**：缺陷八字段 + MRE、严重度矩阵、flaky 治理、覆盖率 vs 变异得分、CI 门禁、指标口径
8. **AI 时代**：四层模型、AI for QA 与 Testing for AI 分离、AI 生成测试审查（自愈陷阱/伪测试）、AI 系统评测集与蜕变关系
9. **自我进化协议**：裁决"测项目时不自治 / 升级技能时授权自治"，十步升级门禁、变更证据要求、蒸馏质量门槛、语义化版本
10. **可验证性**：`scripts/selfcheck.py`（frontmatter / 断链 / 版本一致 / 占位 URL / 模板字段 / 索引覆盖），`CHANGELOG.md`，`.gitignore`
11. **模板升级**：新增 `bug-report-template.md` / `test-plan-template.md` / `release-gate-template.md`；报告模板强制 PASS/FAIL 与 Go/No-Go

### 回归检查

- [x] 五阶段模型闭环未变，示例仍成立（升级为含越权 bug 的 4 条 MRE 示例）
- [x] 记忆树 <100 行纪律保留；tree 模板仍 <100 行
- [x] 「工具缺失不中止」的降级原则保留，并在 `tools.md` §纪律 6 强化
- [x] 运行时不擅自改本体的安全约束保留，且用权限裁决明确了自动化升级的合法路径
- [x] 原有文件引用路径未失效（由 `selfcheck.py` 断链检查验证）

### 自检结果

`python scripts/selfcheck.py` → **PASS 16 / WARN 0 / FAIL 0 → GREEN**（退出码 0）。

首轮自检曾报 3 处断链（2 处为 `fullstack-dev` 外部技能的引用写成裸 `references/...`，1 处为已驳回提案里提到不存在的模板），已改为显式外部路径与文字描述后复跑通过——**门禁确实拦住了会导致误读的引用**，这是本次升级引入自检的价值验证。每日升级要求 FAIL = 0 才允许同步与提交。

---

## [v0] — 基线（未版本化，2026-10-30 前）

`SKILL.md` 五阶段 + 5 份 references + 2 份 assets + `memory/global-lessons.md`。无版本号、无 CHANGELOG、无 git 仓库、无专项手册与自检。
