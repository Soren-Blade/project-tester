# 更新日志

> 每日升级记录。格式与门禁见 `references/self-evolution.md` §3~§4。
> 版本号与 `SKILL.md` frontmatter、`README.md` 徽章三者由 `scripts/selfcheck.py` 校验一致。

---

## [v1.18.0] — 2026-11-24 · 桌面端专项 + R-26 桌面进程边界与分发

### 主题

**C2 桌面端专项**：把「桌面应用」从 `cross-platform-testing.md` 的一条附注升为独立能力层——新增 **R-26 桌面进程边界与分发**（管主进程/渲染进程边界、IPC、导航与 CSP、签名公证、自动更新、单实例/深链、崩溃回滚，与 R-8 的设备形态真实性分工）、`references/desktop-app-testing.md`、`assets/desktop-app-matrix-template.md`、`scripts/desktop-audit.py`（DT-01~DT-10 静态扫描 + DT-20~DT-29 运行矩阵）。专项手册 35→36 份、模板 33→34 份、脚本 20→21 个、规则 25→26 条。

### 动机（来自提案区 / 实战反馈）

1. **缺口实证**：v1.17 全库检索 `nodeIntegration|contextIsolation|sandbox|fuses|Tauri|senderFrame|codesign|stapler` 只命中 `supply-chain-testing.md` 的签名附注与 `cross-platform-testing.md` 的「桌面端也适用」一句，**没有任何可执行判据**；preload 暴露面、IPC sender 校验、capabilities 收窄、降级更新、单实例参数校验全部空白。
2. **R-8 管不到进程边界**：R-8 只要求「矩阵与载体真实、不拿仿真冒充真机」，无法推翻「桌面端能启动 / 装了签名就安全」这种结论。
3. **标准 1.2 缺桌面向量**：原 15 画像没有「在渲染进程里 `typeof require` 验证隔离」「用 `../` 打 IPC 路径」「安装中杀进程再启动」这类端侧刁钻路径。

### 改动清单（文件 : 做了什么）

- `references/desktop-app-testing.md`（**新建**）：§0 触发/不适用、§1 八问、§2 选型矩阵（Playwright+Electron / WebdriverIO / Spectron 已停维护 / tauri-driver / 原生 UI 自动化 / 签名命令行 / 人工清单，含证据强度与典型失真）、§3 环境能证明/不能证明、§4 进程权限（`nodeIntegration`/`contextIsolation`/`sandbox`/`webSecurity` + preload 最小暴露 + Tauri capabilities 与 `AppManifest::commands` 收窄）、§5 IPC 入参矩阵与 sender·路径校验、§6 导航/CSP/自定义协议、§7 更新签名（`codesign`/`spctl`/`stapler`/`signtool`/fuses/`pubkey`/降级与中断）、§8 单实例/深链/文件关联/托盘、§9 崩溃休眠回滚、§10 DT-01~DT-10、§11 DT-20~DT-29、§12 不得冒充与降级、§13 出处。
- `assets/desktop-app-matrix-template.md`（**新建**）：制品与分发 / 运行时权限声称值 vs 实测 / IPC 入参裁决 / 导航与 CSP / 更新签名公证 / 单实例·深链 / 崩溃休眠 / DT-01~DT-10 裁决表 / DT-20~DT-29 / 结论（含 R-26 不得声明）。
- `scripts/desktop-audit.py`（**新建**）：`scan`（table/json/markdown、`--include-docs`、`--fail-on-gap`）、`matrix`、`cases`（codesign/spctl/stapler/signtool/fuses/tasklist/pgrep）、`--self-test`；零依赖，文件头写明「不联网 / 不代填 / 0 命中也不证明没有缺陷」。
- `SKILL.md`：frontmatter v1.18.0、description 计数 26 条/R-1~R-26、36 份、21 个并加桌面触发词；规则表新增 R-26 行；阶段 4 证据矩阵改二十六行；判 bug 标准第 8 条、覆盖范围、参考文件表计数同步。
- `references/routing.md` / `references/dissect.md` §8：各加 desktop 行（手册 + 模板 + 脚本 + R-26）。
- `references/quality-gates.md`：§2A 第 8 条加「桌面进程边界未测」；§3A 加 R-26 证据行与出处；§3B 新增「桌面进程边界与分发」段 9 条「≠」；§8 自检计数改二十六条/二十五行。
- `assets/report-template.md`：证据矩阵加 R-26 行；模板清单加 desktop 模板，说明段改二十六行。
- `references/tools.md`：专项工具表登记 `desktop-audit.py`（含降级路径与「静态扫描 0 命中 ≠ 边界安全」）。
- `scripts/selfcheck.py`：`checks` 增手册/模板关键词；`SCRIPT_GATES` 增 desktop-audit 门禁（自检、命中规则、诚实边界词）；**§7c 规则同步门禁强化**（见「自检与门禁」）。
- `README.md`：徽章 / 文件结构计数（105 文件 / 45 references / 34 模板 / 21 脚本）/ R 列表 / 设计要点 / 版本历史同步。
- `memory/global-lessons.md`：本轮经验 2 条（桌面专项已吸收 + 静态扫描豁免按结构块判定）。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 分类 | 条目 | 说明 |
|---|---|---|
| **New** | `references/desktop-app-testing.md`、`assets/desktop-app-matrix-template.md`、`scripts/desktop-audit.py`、R-26 | 新能力层与可执行判据 |
| **Enhance** | `SKILL.md`、`references/routing.md`、`references/dissect.md`、`references/quality-gates.md`、`assets/report-template.md`、`references/tools.md`、`README.md`、`memory/global-lessons.md` | R-26 三处同步 + 计数 + 经验沉淀 |
| **Match** | `scripts/selfcheck.py` | 新手册/模板/脚本接线到门禁；§7c 补「§3A 逐条证据行 + 规则编号上限」负向漏洞 |
| **Existing** | 其余 35 份手册、R-1~R-25、其余 33 份模板、其余 20 个脚本 | **未改判据** |

### 口径诚实（不新增不可证伪的宣称）

- dogfood 的 **12 条违规 / 2 条无法核对**只证明「扫描器在自造夹具上按预期工作」，**不是任何真实桌面应用的结论**；夹具在 `.workbuddy-ai/` 下，不入库、不作案例背书。
- **DT-04（preload 过度暴露）未在夹具中出现**，由 `--self-test` 的 preload 夹具覆盖；这不等于真实项目里 DT-04 少见或常见。
- `desktop-audit.py` 只做**静态文本/正则扫描**：0 命中不证明边界安全；动态拼接、打包后才写入的配置、模板字符串拼接的 IPC 通道名会漏；它不替代运行态验证、不替代 `codesign`/`signtool` 实跑、不判断业务正确性。
- 手册里的 `codesign` / `spctl` / `stapler` / `signtool` / `@electron/fuses` / Tauri capability 命令来自官方文档，**本机（Windows）未逐条执行**（无 macOS 签名环境、未安装真实 Electron/Tauri 应用）；不同 Electron / Tauri / OS 版本默认值与参数会变，手册已标「版本敏感、执行前本机复核并留 `--help` 输出」。
- **未验证**：真实 Electron/Tauri 应用的命中率/误报率、跨平台签名差异、降级安装与中断更新的实际拦截行为、公证审核时延。

### 自检与门禁（selfcheck 结果）

**深度实测（dogfood v1.18.0）**：`.workbuddy-ai/dogfood/v1.18.0/desktop-sample/` 3 个可扫描文件，`python scripts/desktop-audit.py scan .workbuddy-ai/dogfood/v1.18.0/desktop-sample` 实跑 **12 违规 / 2 无法核对**——DT-01（`nodeIntegration: true`）、DT-02（`contextIsolation: false` + `sandbox: false`）、DT-03（`webSecurity: false`）、DT-05（IPC handler 读文件且无 sender/路径校验，标无法核对）、DT-06（`shell.openExternal(target)`）、DT-07（`setWindowOpenHandler` 恒 allow）、DT-08（`csp: null` + 项目级 CSP 缺口，各 1）、DT-09（`pubkey` 空 + http 更新源 + `dangerousInsecureTransportProtocol`）、DT-10（capability 全窗口 + fs/shell default；assetProtocol 裸 `**` + `requireLiteralLeadingDot:false`）。诱饵零误报：同文件已校验 handler（`senderFrame`+`realpath`）、注释里的 `senderFrame` 字样、https 无签名场景不编造「证书过期」。详见 `.workbuddy-ai/dogfood/v1.18.0/RESULT.md`。

本轮 dogfood 修掉的脚本缺陷（均已加回归断言）：① DT-05 整文件判定被同文件安全 handler 的 `senderFrame` 压掉 → 改逐 handler 块判定；② 注释里的 `senderFrame`/`realpath` 压制命中 → 新增 `_blank_comments()` 等长空格置空；③ Tauri `"csp": null` 未覆盖 → 新增行级规则 + 项目级「无法核对」兜底；④ 同行多规则重复条目 → 去重键改 `(rule, rel, line)`。

本轮负向测试发现并修掉的**门禁缺陷**：`selfcheck.py` §7c 原先把 `quality-gates.md` 全文件所有 `R-N` 当「引用集」，导致 ① 删掉 §3A 的 R-26 证据行仍 PASS（R-26 在 §3B 还有）；② SKILL 把「R-1~R-26」改成「R-1~R-27」也 PASS。已改为：§3A 区域内逐条 `| **R-N` 表格行必须覆盖 SKILL 规则集，且 SKILL 不得出现编号 > 最大规则的引用。

```powershell
python scripts/selfcheck.py                    # PASS 93 / WARN 1 / FAIL 0，exit 0
python scripts/upgrade.py --check              # 结构校验 GREEN，exit 0
python scripts/desktop-audit.py --self-test    # SELFTEST GREEN，exit 0
```

WARN 仍为 `memory/global-lessons.md` 347 行（D1 待做，非本轮引入）。

**负向测试 6/6**（在仓库临时副本上改坏一处，确认对应门禁 FAIL，原仓库不受影响）：

| # | 改坏什么 | 期望/实测 |
|---|---|---|
| N1 | 删 `report-template.md` 的 `\| R-26 ` 矩阵行 | FAIL「报告证据矩阵缺少规则表格行: R-26」 |
| N2 | SKILL 的 `R-1~R-26` 改成 `R-1~R-27` | FAIL「SKILL.md 出现超出最大规则编号 R-26 的引用: R-27」 |
| N3 | `desktop-audit.py` 的「0 命中也不证明没有缺陷」改成「0 命中即安全」 | FAIL「缺少可证伪性 / 诚实边界关键字段」 |
| N4 | 删 `quality-gates.md` §3A 的 R-26 证据行 | FAIL「§3A 缺少规则证据行: R-26」 |
| N5 | 删 `routing.md` 的 desktop 行 | FAIL「孤儿文档: desktop-app-testing.md」+「只在 dissect §8、未进 routing.md」 |
| N6 | 删 §3A 的 R-13 证据行 | FAIL「§3A 缺少规则证据行: R-13」 |

自动化提示词：revision 5 → 6。

### 提案处置（采纳 / 驳回 + 理由）

- **采纳（v1.18）**：C2 桌面端专项 —— v1.15 提案③「移动 / 桌面 / 小程序三份专项」的第二份；桌面端可零依赖落静态扫描（配置字面量、capability JSON、CSP），且官方文档足以支撑可证伪判据。
- **顺延（队列）**：C3 小程序专项（微信/支付宝：授权 scope、setData 性能、分包与首包、审核环境差异、storage 上限、真机调试）；C4 刁钻方向生成器（把 1.2 从静态 15 画像变成「给定功能 → 20+ 方向」）；D1 `global-lessons.md` TOC + 归档判据（347 行，阶段 0 每次整份读入）；D2 plans 复用实测；D3 CHANGELOG 归档。
- **低优先/暂不做**：D4 脚本公共 harness（同口径 Jaccard ≈0.24，收益低）；桌面端「运行态自动化」不写成必选——`tauri-driver`/原生 UI 自动化的跨平台成本高，手册只给选型与最低证据。

## [v1.17.0] — 2026-11-23 · 移动 App 专项：R-25 与 mobile-audit

### 主题

**C1 移动 App 专项**：把「移动 App」从 `cross-platform-testing.md` 的一条附注升为独立能力层——新增 **R-25 移动集成与分发**（管 OS 集成面，与 R-8 的设备矩阵真实性分工）、`references/mobile-app-testing.md` 手册、`assets/mobile-app-matrix-template.md` 矩阵模板、`scripts/mobile-audit.py` 静态扫描器（MB-01~MB-10 反模式 + MB-20~MB-29 运行矩阵）。专项手册 34→35 份、模板 32→33 份、脚本 19→20 个。

### 动机（来自提案区 / 实战反馈）

1. **缺口实证**：v1.16 全库检索 `权限弹窗|深链|推送|安装升级|弱网` 只命中 `cross-platform-testing.md` 的设备形态段与 `global-lessons.md` 的 7 条跨端教训，**没有任何可执行判据**；权限四态、进程回收、覆盖升级、灰度回滚全部空白。
2. **R-8 管不到 OS 集成面**：R-8 只要求「矩阵与载体真实、不拿仿真冒充真机」，无法推翻「真机装上但深链/推送/升级全没测」这种结论。
3. **标准 1.2 缺移动向量**：原 15 画像没有「拒绝权限后走设置撤销」「推送冷启动点击」「降级安装」这类端侧刁钻路径。

### 改动清单（文件 : 做了什么）

- `references/mobile-app-testing.md`（**新建**）：§0 触发/不适用、§1 八问、§2 选型矩阵（Appium 2+ / Maestro / XCUITest / Espresso / Detox / 设备云，含证据强度与典型失真）、§3 仿真器·真机·设备云边界、§4 权限四态与 `pm revoke`/`simctl privacy`、§5 生命周期、§6 深链六路径与 `am start`/`openurl`/`simctl push`、§7 安装升级灰度、§8 弱网电量、§9 MB-01~MB-10、§10 MB-20~MB-29、§11 不得冒充、§12 出处。
- `assets/mobile-app-matrix-template.md`（**新建**）：构建分发 / 载体 / 权限四态 / 中断生命周期 / 深链推送 / 安装升级灰度 / 弱网电量 / 扫描裁决 / 运行矩阵 / 结论（含 R-25 不得声明）。
- `scripts/mobile-audit.py`（**新建**）：`scan`（table/json/markdown、`--include-docs`、`--fail-on-gap`）、`matrix`、`cases`、`--self-test`；零依赖，文件头写明「不联网 / 不代填 / 0 命中也不证明无缺陷」。
- `SKILL.md`：frontmatter v1.17.0、description 计数 25 条/R-1~R-25、35 份、20 个并加移动触发词；规则表新增 R-25 行；阶段 4 证据矩阵改二十五行；判 bug 标准第 8 条、参考文件表计数同步。
- `references/routing.md` / `references/dissect.md` §8：各加 mobile 行（手册 + 模板 + 脚本 + R-25）。
- `references/quality-gates.md`：§2A 第 8 条加「移动集成面未测」；§3A 加 R-25 证据行与出处；§3B 跨端段加 5 条「≠」；§8 自检计数改二十五条/二十五行。
- `assets/report-template.md`：证据矩阵加 R-25 行；说明段补 R-23/R-24/R-25 的不得冒充句；模板清单加 mobile 模板。
- `references/tools.md`：专项工具表登记 `mobile-audit.py`（含降级路径与「静态扫描 0 命中 ≠ 无集成缺陷」）。
- `scripts/selfcheck.py`：`checks` 增手册/模板关键词；`SCRIPT_GATES` 增 mobile-audit 门禁（自检、命中规则、诚实边界词）。
- `README.md`：徽章 / 文件结构计数（102 文件 / 44 references / 33 模板 / 20 脚本）/ R 列表 / 设计要点 / 版本历史同步。
- `memory/global-lessons.md`：本轮经验 1 条已吸收（静态扫描器按标签边界判作用域，别用行窗口）。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 分类 | 条目 | 说明 |
|---|---|---|
| **New** | `references/mobile-app-testing.md`、`assets/mobile-app-matrix-template.md`、`scripts/mobile-audit.py`、R-25 | 新能力层与可执行判据 |
| **Enhance** | `SKILL.md`、`references/routing.md`、`references/dissect.md`、`references/quality-gates.md`、`assets/report-template.md`、`references/tools.md`、`README.md` | R-25 三处同步 + 计数 |
| **Match** | `scripts/selfcheck.py` | 新手册/模板/脚本接线到门禁 |
| **Existing** | 其余 34 份手册、R-1~R-24、其余 32 份模板、其余 19 个脚本 | **未改判据** |

### 口径诚实（不新增不可证伪的宣称）

- dogfood 的 **14 条违规 / 1 条无法核对**只证明「扫描器在自造夹具上按预期工作」，**不是任何真实 App 的结论**；夹具在 `.workbuddy-ai/` 下，不上传、不作为案例背书。
- **MB-09 未在夹具中触发**，由 `--self-test` 的负向控制用例覆盖；这不等于真实项目里 MB-09 少见或常见。
- `mobile-audit.py` 只做**静态文本/正则扫描**：0 命中不证明无缺陷，斜体/拼接/运行时权限等写法会漏；它不替代真机、不替代 Appium 执行、不判断业务正确性。
- 手册里的 `adb`/`simctl`/`-netdelay` 命令来自官方文档，**本机未逐条执行**；不同 OS/模拟器版本的权限重置与限速档位会变，手册已标「必须实测」，脚本不代填参数。
- **未验证**：真实 App 上的命中率/误报率、设备云与真机的行为差异、灰度回滚的实际耗时。

### 自检与门禁（selfcheck 结果）

**深度实测（dogfood v1.17.0）**：`.workbuddy-ai/dogfood/v1.17.0/mini-shop/` 8 个可扫描文件，`python scripts/mobile-audit.py scan .workbuddy-ai/dogfood/v1.17.0/mini-shop` 实跑 **14 违规 / 1 无法核对**——MB-01（Maestro `point` 百分比 + Flutter `tapAt`）、MB-02（`sleep: 4000` + `Future.delayed`）、MB-03（定位未声明 `ACCESS_FINE_LOCATION`，标无法核对）、MB-04（WebView `setJavaScriptEnabled(true)`）、MB-05（`getIntent().getData()` + `getInitialLink()`）、MB-06（`usesCleartextTraffic` + 明文 URL）、MB-07（两处 `exported="true"` 无 permission）、MB-08（硬编码 `sk-live-`）、MB-10（`autoGrantPermissions`/`autoAcceptAlerts`）。诱饵零误报：`localhost`、带 permission 的 exported service、docs 里的 sleep。详见 `.workbuddy-ai/dogfood/v1.17.0/RESULT.md`。

本轮 dogfood 修掉的脚本缺陷（均已加回归断言）：① 相对路径分隔符统一为 `/`；② MB-07 原 ±6 行窗口会把同文件带 permission 的 service 误当保护 → 改为按起始标签边界判定；③ 补 Flutter `tapAt(const Offset(...))` 与 `Future.delayed`；④ 补 `getInitialLink()`/`getAppLinks`；⑤ 补 Dart `permission_handler`。

```powershell
python scripts/selfcheck.py                    # PASS 90 / WARN 1 / FAIL 0，exit 0
python scripts/upgrade.py --check              # 结构校验 GREEN，exit 0
python scripts/mobile-audit.py --self-test     # SELFTEST GREEN，exit 0
```

唯一 WARN 仍是 `memory/global-lessons.md` 345 行（已知保留项，归档判据见该文件「待核实」）。

负向测试 **4/4 通过**：① 报告矩阵缺 R-25 → `[FAIL] 报告证据矩阵缺少规则表格行: R-25`；② SKILL 规则表写 R-26 → `[FAIL] 可证伪规则未接入 quality-gates.md: R-26`；③ 脚本文件头删「不联网」→ `[FAIL] ... 缺少可证伪性 / 诚实边界关键字段: 不联网`；④ 手册「不得」改「可以」→ `[FAIL] ... 缺少关键字段: 不得`。每次改坏后均恢复并复跑 GREEN。

自动化提示词：revision 5 → 6（更新后 4,183 字符；写入 `C:\Users\摩羯座\.dsh\storages\dsh_automation.json`，回读校验 revision=6、其它记录 prompt 未变）。

### 提案处置（采纳 / 驳回 + 理由）

| 提案 | 处置 | 理由 |
|---|---|---|
| 队列 C1「移动 App 专项」 | **采纳** | 本轮主线，按队列交付 |
| 「能零依赖就加静态扫描」 | **采纳** | 10 类反模式可用正则判，产出 `mobile-audit.py` 并接门禁 |
| 新增第 16 条判 bug 标准 | **驳回** | 会触发「十五条」全库连锁；改为扩展 §2A 第 8 条并挂新手册 |
| 在真实 App / 设备云实测 | **暂缓** | 本机无安装包与云设备账号；已标「待确认」，不写成已验证 |
| MB-09 无夹具命中 | **采纳为自检用例** | 用 `--self-test` 负向控制覆盖，CHANGELOG 明示未在 dogfood 出现 |

## [v1.16.0] — 2026-11-23 · 记忆升级：需求档案库 plans/ + token 成本账本

### 主题

**记忆升级，不新增测试维度**：把「越用越聪明」从口号变成两份可复用资产——`.test-memory/plans/` 需求档案库（同类需求第二次不再重推测试设计）与 `metrics.md` token 成本账本（把「省 token」变成可测的数）。这是 B 阶段（记忆升级），承接 v1.15 的 A 阶段收口。

### 动机（来自提案区 / 实战反馈）

1. **标准 1.1 的核心缺口**（v1.15 审计 §2 缺口 A）：全库 grep `plans/|requirements\.md|测试需求归档|需求库` **零命中**——「测试需求」只活在当轮对话与 `runs/` 的结论表里，而 `runs/` 超 10 份会删最旧，同类需求下次连历史方向清单都找不回，只能重推一遍测试设计。
2. **「省 token」全是设计意图**（同审计缺口 D）：三律（tree < 100 行 / 先信记忆树 / 稳定模块折叠）没有一条能被验证，全库没有任何计量。
3. **阶段 2 的模板只产出当轮计划**：`assets/test-plan-template.md` 没有「归档供下次复用」这一步，需求天然不可积累。

### 改动清单（文件 : 做了什么）

- `references/memory-tree.md`：目录结构加 `plans/` 与 `metrics.md`；新增「plans/ 需求档案格式」节（何时建档 / 命名 / 六节结构 / 复用规则 / 更新规则）；tree.md 新增第 6 区「需求索引」；更新规则补「plans 不随 runs 删除而失效」与每轮记账；「省 token 三律」扩为**四律**（第 4 条 = 需求复用 + 记账，并写明前三条无法被验证）。
- `assets/plan-template.md`（**新建**）：需求原文（逐字、追加不覆盖）/ 拆解与风险分 / **方向矩阵**（功能点 × 维度 × 可直接执行的方向 × 画像手册 × 上轮结论）/ 执行索引 / 未覆盖缺口 / 复用提示三行。
- `assets/tree-template.md`：新增「需求索引」区与 `metrics.md` 指针。
- `scripts/context-cost.py`（**新建**）：`estimate` / `session` / `log` / `report` 四子命令，零依赖，`--self-test` 14 项；诚实边界写进文件头与自测断言（估算非 tokenizer 精确值、不联网、只量读入不评测试质量、漏记就是漏记）。
- `SKILL.md`：阶段 0 由「读两份」改为「读三处」，并明确「命中同类需求只读档案 §3/§6，测试设计环节应接近零成本」；阶段 2 增加「需求档案落盘」；阶段 4 五步扩为七步（更新档案 / 记成本）；五阶段总览、记忆树速览、示例、参考文件表同步；脚本 18→19、模板 31→32。
- `references/tools.md`：登记 `context-cost.py`（用法 / 降级路径 / 「估算不是账单」的不得声明）；可用性探测块加自测行。
- `references/routing.md`：脚本数 18→19（两处）。
- `scripts/selfcheck.py`：新增 §7l 需求库/账本**接线完整性**（8 条接线 + 脚本与模板存在性）、§7m 树模板必须含需求索引区；§7f 脚本门禁加入 `context-cost.py`。
- `README.md`：版本历史补 v1.16.0 行；文件结构计数同步（99 文件 / 32 模板 / 19 脚本）。
- `memory/global-lessons.md`：新增 2 条已吸收 + 1 条待核实。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 分类 | 条目 | 说明 |
|---|---|---|
| **New** | `assets/plan-template.md`、`scripts/context-cost.py` | 新资产 |
| **Enhance** | `references/memory-tree.md`、`assets/tree-template.md` | 记忆树规范扩到「需求复用 + 记账」 |
| **Enhance** | `SKILL.md` 阶段 0/2/4、`references/tools.md`、`references/routing.md`、`README.md` | 流程接线与计数同步 |
| **Match** | `scripts/selfcheck.py` §7l / §7m / §7f | 门禁与规范对齐 |
| **Existing** | 34 份专项手册、R-1~R-24、其余 31 份模板、其余 18 个脚本 | **未改动** |

### 口径诚实（不新增不可证伪的宣称）

- 本轮**不新增测试维度、R 规则或检测项**；档案库与账本都是「让已有能力可复用 / 可测量」的机制。
- `tokens` 是 `chars / 3.2` 的**估算**，不是账单；中文真实约 1.5~2 chars/token，会被低估。它只用于**同一口径下的横向比较**。
- **未验证**：在真实第三方项目上跑两轮同类需求、对比「有档案 vs 无档案」的实测 token 差。本版只验证了机制接线与脚本自测，**不复述任何「省了 N%」的数字**。
- 文中的估算示例（`SKILL.md` 12,241 chars ≈ 3,825 tok；`routing.md` 13,508 ≈ 4,221；`global-lessons.md` 29,606 ≈ 9,252）来自对技能自身文件的 `estimate`，只证明口径能跑，不代表典型项目。

### 自检与门禁（selfcheck 结果）

```powershell
python scripts/selfcheck.py              # PASS 87 / WARN 1 / FAIL 0，exit 0
python scripts/context-cost.py --self-test  # SELFTEST GREEN（14 项），exit 0
python scripts/upgrade.py --check        # 结构校验 GREEN，exit 0
```

唯一 WARN 仍是 `memory/global-lessons.md` 341 行（已知保留项，归档判据见该文件「待核实」）。

### 提案处置（采纳 / 驳回 + 理由）

| 提案 | 处置 | 理由 |
|---|---|---|
| `.test-memory/plans/` 测试需求库 | **采纳** | v1.15 审计缺口 A；落地为档案库 + tree 需求索引 + §7l 接线门禁 |
| token 成本账本 | **采纳** | v1.15 审计缺口 D；落地为 `context-cost.py` + `metrics.md` |
| `global-lessons.md` TOC 与归档 | 顺延 | 需先定「连续两轮未被引用」的归档判据，避免删掉仍有召回价值的长尾经验 |
| 移动 App / 桌面端 / 小程序手册 | 顺延 | 属 C 阶段（形态补齐），不塞进「维护 + 记忆」版本 |
| 刁钻方向生成器 | 顺延 | 属 C 阶段；且需先靠档案库沉淀真实方向样本，作为生成器的评测素材 |

## [v1.15.0] — 2026-11-23 · 架构收口：SKILL 65KB → 15KB + 结构门禁补强

### 主题 

**架构收口，不新增任何测试维度**：把 `SKILL.md` 从 64,893 chars（430 行）压到 12,241 chars（185 行，−81%），把写散在 4 处的路由信息归一到 `references/routing.md` 一处，并把门禁从「只验当前版本条目存在」扩到「验历史版本序列完整 + 体积预算 + 跨文件集合一致」。这是一次**维护版本**，不属于每日升级序列（#15 之后不连续编号）。

### 动机（来自提案区 / 实战反馈） 

来自一次全库自审（报告留档 `.workbuddy-ai/review/2026-11-23-audit.md`，411 行）：

1. **同一套 34 份手册路由在 `SKILL.md` 里写了 4 遍** —— L53-134 四层叠加表 7,834 chars、L157-172 阶段 1 解剖面 3,787、L195-229 阶段 3 的 37 条专项 bullet 6,697、L324-418 参考索引 12,167，合计 **30,485 chars = 全文 47%**；R-1~R-24 的证据要求在 `quality-gates.md` §3 又有第 2 份全文渲染。
2. **`SKILL.md` 已超单次展示预算**：加载本技能时工具输出出现 `Omitted 20591 bytes`，规则表尾部（R-9~R-24 区域）在真实加载中有丢失风险；`description` 单行 4,433 chars（值长度，不含 `description:` 前缀），在会话技能目录里被截断为 `...`，尾部关键词既占 token 又不产生发现价值。
3. **`selfcheck.py` 报 PASS 77 / WARN 0 / FAIL 0 全绿，却漏掉两处真实回归**：`CHANGELOG.md` 的 `## [v1.13.0]` 与 `## [v1.12.0]` 两个 H2 标题被后续两次升级顶掉，两段正文成了挂在 v1.14 下的孤儿；`README.md` 版本历史表缺 v1.9.0 与 v1.7.0 两行。逐提交取证确认这是 `52a7dab`、`63aa844` 引入的回归，不是历史惯例。根因是升级靠 `.workbuddy-ai/tmp/patch_readme.py` 一类 `str.replace` 一次性脚本打补丁，无结构校验拦截。
4. 次要证据：`memory/global-lessons.md` 337 行，违反文件自定的「超 40 行修剪」8 倍，且阶段 0 每次整份读入（≈8.8k tok）。

### 改动清单（文件 : 做了什么） 

- `SKILL.md`：64,893 → 12,241 chars（430 → 185 行）。删除 v1.1~v1.14 逐版增量段（8,838 chars）、四份重复路由清单（30,485）、95 行参考索引；R-1~R-24 改为 24 行判据骨架表（列 = 规则｜结论必须附的证据｜不适用时），完整证据要求指向 `quality-gates.md` §3A；description 从 4,433 压到 752 chars（值长度），触发词前移。五阶段流程、双视角、证据纪律、安全边界、记忆树规范**语义未改**。
- `references/routing.md`（**新建**，13,508 chars / 115 行）：路由单一事实源 —— §1 四层模型、§2 22 个解剖面（含「必须回答 / 见哪份手册」）、§3 34 份专项手册的「触发信号 → 手册 → 必做动作 → 规则」、§4 元手册、§5 叠加纪律。
- `references/quality-gates.md`：10,150 → 20,119 chars。新增 §2A 判 bug 十五条表、§3A 24 条 R 规则的完整证据要求与「不适用时的写法」（逐字承接旧 SKILL 正文）、§3B「近似证据 ≠ 结论」40+ 组对照表；§3 收敛为作废判据决策表。
- `scripts/upgrade.py`（**新建**，294 行，零依赖）：结构化版本写回 —— `--new-version` 开新段并同步三处版本号、`--check` 校验结构、`--self-test` 自证可证伪；写盘前先校验、落盘后异常全量回滚。
- `scripts/selfcheck.py`：383 → 496 行。新增 §7g `CHANGELOG` H2 严格递减且每段至多一个「### 治理分类」、§7h `README` 版本表覆盖（只认表格行首列，散文提及不算）、§7i `SKILL.md` 体积（>26K FAIL / >22K WARN）与 description ≤1024、§7j `routing.md` ↔ `dissect.md` §8 集合相等、§7k 模板孤儿、§8a `global-lessons.md` 体积；索引池加入 `routing.md`。
- `references/tools.md`：专项工具表补 `upgrade.py` 一行、可用性探测补 2 行、自检项说明扩到 §7a~§7k。
- `CHANGELOG.md`：补回 `## [v1.13.0]`（L91）与 `## [v1.12.0]`（L166）两个 H2。
- `README.md`：版本历史表补 v1.9.0、v1.7.0 两行与 v1.15.0 行；徽章同步 v1.15.0。
- `.gitignore`：从「整个 `.test-memory/` 不入库」改为「`tree.md`/`lessons.md`/`plans/` 入库，`runs/`/`tmp/` 不入库」。

### 治理分类（Existing / Enhance / Merge / Match / New） 

| 分类 | 对象 | 处置 |
|---|---|---|
| New | `references/routing.md` | 路由唯一事实源；原 4 处清单合并为此一处，34 份手册逐行给「触发信号 / 必做动作 / 所属规则」 |
| New | `scripts/upgrade.py` | 结构化版本写回器，替代 ad-hoc `str.replace` 补丁；本版开新段即由它完成 |
| Merge | `SKILL.md` → `references/quality-gates.md` | 旧 SKILL 的 R 表证据要求与「不得冒充」串迁入 §3A/§3B，判 bug 15 条迁入 §2A；SKILL 只留判据骨架 |
| Enhance | `scripts/selfcheck.py` | 新增 §7g~§7k、§8a 六类检查，直接覆盖本版修掉的两处回归 |
| Enhance | `references/tools.md`、`README.md`、`.gitignore` | 登记新脚本、补版本史与徽章、记忆树入库策略 |
| Existing | 其余 34 份专项手册、31 份模板、16 个 audit 脚本 | **未改动**，只在 `routing.md` 中重新索引 |

### 口径诚实（不新增不可证伪的宣称） 

- 本版**不新增任何测试维度、R 规则或脚本检测项**；34 份专项手册内容未重写，只是索引收敛。
- 「−81%」指字符数（python UTF-8 实测 64,893 → 12,241），不代表能力项减少：34 份手册在 `routing.md` §3、`dissect.md` §8、索引池三方齐备，由 §7b/§7j 强制。
- 破坏性验证在临时副本上做（删 H2 / 删 README 行 / 撑大 SKILL 后跑门禁），属**门禁负向测试**，不是真实故障演练。
- **未验证**：在真实第三方项目上跑一次完整「阶段 0→4」以对比新旧版实际 token 消耗；本版的省 token 结论只来自文件体积与加载截断的事实。
- `CHANGELOG` 两处 H2 属**修复既有内容**，不是本轮新增能力。

### 自检与门禁（selfcheck 结果） 

- `python scripts/selfcheck.py` → 见下方「落盘后实测」；`python scripts/upgrade.py --check` → GREEN；`python scripts/upgrade.py --self-test` → 8 项全 PASS / SELFTEST GREEN。
- 破坏性验证：临时副本删 `## [v1.13.0]` → §7g FAIL；删 README v1.9.0 行 → §7h FAIL；把 SKILL 撑到 >26K → §7i FAIL。三条门禁均可证伪。

### 提案处置（采纳 / 驳回 + 理由） 

- **采纳**：路由单一事实源（消除 47% 冗余）、结构化版本写回器（消除补丁脚本漂移）、体积与序列门禁（本版两处回归的直接解）。
- **顺延到下一版**：`.test-memory/plans/` 需求库 + tree.md 需求索引（记忆层缺口，改动面大）、token 成本账本 `context-cost.py`、移动 App / 桌面 CLI / 小程序三份专项手册（1.3 覆盖缺口）、刁钻方向生成器（1.2 从静态清单升级为可执行生成）。
- **驳回**：无。


## [v1.14.0] — 2026-11-18 · 每日升级 #15

**主题**：从「搜得准 · 数得对」扩展到「**并发不打架 · 评测说得清**」——并发与幂等正确性（R-23）与 AI 系统评测可信性（R-24）。一个接口全绿、分页正确、指标也对得上的系统，仍然会在「两个人同时下单，库存扣成 -1」「用户连点两次，生成两个订单扣两次款」「`SELECT` 完再 `UPDATE`，最后一笔覆盖前一笔」「`SETNX` 加锁后 `EXPIRE` 前进程挂了，锁永不过期」「同一消息被消费两次，用户收到两封邮件」「评测集 20 条就说准确率 90%」「LLM judge 和被测模型是同一个，自己给自己打分」「单次跑出 87 分就当 87 分」上成片出错；这类缺陷不是「没测」，而是「并发窗口、幂等语义与评测统计没有可证伪判据」。新增 **R-23 并发与幂等正确性**、**R-24 AI 系统评测可信性** 与六份文件（2 手册 + 2 矩阵模板 + 2 零依赖脚本），蒸馏底座为 Kleppmann *DDIA* 的 lost update 分类、PostgreSQL 事务隔离与 `SELECT … FOR UPDATE`、MySQL InnoDB locking reads、Stripe 幂等键（同键异体→409、结果缓存 24h）、IETF `Idempotency-Key` 草案、RFC 9110 §9.2.2、Jepsen 一致性模型、AWS Builders' Library 重试安全、Google SRE Workbook 重试放大，以及 NIST AI RMF (AI 100-1)、ISO/IEC 42001、HELM、MT-Bench 的 LLM-as-a-judge 偏见、Cohen's κ、McNemar、Wilson 区间、OWASP LLM Top 10。按每日升级序列记为 #15。

**遵循上轮建议**：未重写已覆盖的 22 个主题与五阶段、四层模型、路由闭环，以 **New 两条规则 + Enhance 全链路接线**；四层模型与五阶段流程**未改语义**，只升 MINOR。本轮选型理由来自上轮遗留账本：`data-integrity-testing.md` 全程只有「并发不变量」一句、`money-correctness-testing.md` 只有「并发重复扣款与超卖」一个词，**没有任何 R-N 规则、矩阵或脚本**覆盖并发写路径，而超卖/重复扣款/丢失更新恰是线上最常见的一类 S1；`ai-native-testing.md` 虽有 §4 评测手法，但 L4 层**至今无一条可证伪规则**，与「每一层都要有判据」自相矛盾。v1.13 遗留提案中，「qrels 双标注 κ 自动比对」顺延（本轮做的是 R-24 的 judge 校准 κ，两者不是同一件事）；「指标接口硬编码常量静态规则」仍**待评估**；「批量 207 逐条 code」「税务辖区舍入矩阵」「缓存键 × 身份 × tenant × locale 矩阵」「上传解码重编码自动化」「AI 变异杀伤跨语言跑数」继续顺延；「`money-audit.py` 自动拉渠道对账单」维持**已驳回**。每轮至少一条可证伪规则 → 本轮引入 **R-23 / R-24**，并做了**四例负向测试**。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 分类 | 对象 | 处置 |
|---|---|---|
| New | `references/idempotency-concurrency-testing.md`、`assets/idempotency-concurrency-matrix-template.md`、`scripts/concurrency-audit.py` | 新增 R-23 能力：不变量先行（余额 == Σ流水 / 库存 ≥ 0 / 一键一资源 / 单号唯一）、三种并发与「只有真并发算数」（屏障 `threading.Barrier` / `xargs -P` / k6 constant-arrival，N≥10）、幂等键矩阵（同键同体 / 同键异体→409 / 不同键同体 / 键过期重放 / 跨用户复用 / 归一化）、锁与事务六类漏点（`FOR UPDATE` 缺索引升级为表锁 / `version` 未进 `WHERE` / `rowcount` 被忽略 / `SETNX`+`EXPIRE` 两步 / 锁内 `sleep` / 自调用 `@Transactional`）、唯一约束与错误码映射（冲突→409 而非 500）、分布式锁与 fencing token、先 ack 后处理与 outbox、副作用对账；CC-01~CC-10 静态 + CC-20~CC-29 运行时 |
| New | `references/llm-eval-testing.md`、`assets/llm-eval-matrix-template.md`、`scripts/llm-eval-audit.py` | 新增 R-24 能力：评测集构成与污染检查（公开基准 n-gram/哈希比对）、非确定性与采样（n≥3、固定 `temperature/top_p/seed`、pass@1 vs pass@k）、判定器可信性（人工双标 κ≥0.60、judge 与人工一致率 ≥80%、judge ≠ generator、rubric 版本化、位置/长度偏见）、失败分类与分母诚实（error/timeout/限流/拒答一律计入）、成本与 p50/p95、注入与工具越权用例、回归与放量门槛（基线 + Wilson 95% CI + McNemar α=0.05 + 回滚演练）；LE-01~LE-10 静态 + `stats` 统计 |
| Enhance | `SKILL.md`（description 触发词、v1.14 增量段、L4 行挂两份手册、v1.14 横向叠加表、阶段 1 并发面/AI 评测面、阶段 3 两条专项、判 bug 13→**15** 条、**二十四条**规则表 R-23/R-24、反向断言链 9 句、阶段 4 自检、参考索引 6 行） | 只增量，不改五阶段与四层模型；「二十二条」标题、阶段 4 矩阵行数、`R-1~R-22` 全部同步为「二十四条 / 二十四行 / R-1~R-24」 |
| Enhance | `references/dissect.md` §6/§7/§8 | 测试设施盘点补「并发面」「AI 评测面」两行；攻击面补「并发与幂等」「AI 评测」两条；路由表补 R-23/R-24 两行（含「仅串行重放」「仅人工抽看」降级写法） |
| Enhance | `references/quality-gates.md` §3/§8、`assets/report-template.md` 证据矩阵 | 结论作废判据补 R-23/R-24 两行（R-23 必须给并发度 N 与实测差额；R-24 的 n<3 / 超时出分母 / judge 同模型 / 无基线即 S1）；24 行矩阵 + 「二十四行」脚注 + 「不得写成」交叉引用 |
| Enhance | `references/tools.md` | 专项工具表补 2 行 + 可用性探测 2 行 + 工具使用纪律 23/24（串行重放 ≠ 并发幂等；跑通一遍 ≠ 评测有效） |
| Enhance | `scripts/selfcheck.py` §5/§7f、`README.md`、`CHANGELOG.md`、`memory/global-lessons.md` | 登记 4 个新文件关键字段、2 个新脚本门禁（`CC-`/`LE-`/`SELFTEST GREEN`/`duplicate_side_effect`/`Wilson`/`McNemar`）、徽章/结构/速查/设计点/版本史、教训与提案 |
| Existing | 其余 40 份手册与 29 份模板 | 不重复造，仅在路由/交叉项里引用（`ai-native-testing.md` 保留注入手法，R-24 只做评测可信性） |

### 蒸馏来源（深度蒸馏，URL 全记录）

- Martin Kleppmann, *Designing Data-Intensive Applications*（lost update / write skew / 可串行化）：https://dataintensive.net/
- PostgreSQL, *Transaction Isolation*（READ COMMITTED 的非重复读与幻读语义）：https://www.postgresql.org/docs/current/transaction-iso.html
- PostgreSQL, *SELECT — Locking Clause*（`FOR UPDATE` 与行不存在时锁不住）：https://www.postgresql.org/docs/current/sql-select.html
- PostgreSQL, *Constraints*（UNIQUE 是最终防线）：https://www.postgresql.org/docs/current/ddl-constraints.html
- MySQL 8.0 Reference, *Locking Reads*（间隙锁与索引缺失升级为表锁）：https://dev.mysql.com/doc/refman/8.0/en/innodb-locking-reads.html
- Stripe, *Idempotent requests*（键保留 24h、同键异体报错、回放首次结果）：https://docs.stripe.com/api/idempotent_requests
- IETF, *The Idempotency-Key HTTP Header Field*（草案：键作用域与冲突语义）：https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/
- RFC 9110 §9.2.2, *Idempotent Methods*：https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2
- Jepsen, *Consistency Models*（并发历史与异常分类）：https://jepsen.io/consistency
- AWS Builders' Library, *Making retries safe with idempotent APIs*：https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/
- Google SRE Workbook, *Addressing Cascading Failures*（重试放大）：https://sre.google/workbook/cascading-failures/
- NIST, *AI Risk Management Framework (AI 100-1)*：https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf
- ISO/IEC 42001:2023, *AI management system*：https://www.iso.org/standard/81230.html
- HELM, *Holistic Evaluation of Language Models*：https://arxiv.org/abs/2211.09110
- Zheng et al., *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*（位置/长度/自我偏好偏见）：https://arxiv.org/abs/2306.05685
- Cohen, *A Coefficient of Agreement for Nominal Scales*（κ, 1960）：https://doi.org/10.1177/001316446002000104
- McNemar, *Note on the sampling error of the difference between correlated proportions*（1947）：https://doi.org/10.1007/BF02295996
- OWASP, *Top 10 for LLM Applications*（注入、越权、数据外泄）：https://owasp.org/www-project-top-10-for-large-language-model-applications/
- OpenAI Evals / Anthropic Evals（grader 设计与用例组织）：https://github.com/openai/evals · https://github.com/anthropics/evals

### 口径诚实

- `concurrency-audit.py` **不联网、不代填**：`scan` 是逐行启发式（先查后写、`FOR UPDATE` 缺索引、`version` 未进 `WHERE`、`rowcount` 被忽略、`SETNX`+`EXPIRE` 两步、锁内 `sleep`、自调用事务、无唯一约束/去重表、先 ack 后处理、共享可变状态），命中只是「可疑写法」，**不证明**并发安全；`cases` 只打印夹具与判据模板，**不替你造并发**；`side-effects` 只对账你给的 JSONL（`--events`），事件日志本身可伪造；`--fail-on-gap` 只把已发现的高危线索变成非零退出码，**不把「没发现」变成「幂等已做」**。
- 并发测试的假并发陷阱：串行 `for` 循环 + `sleep`、单实例压测、`Promise.all` 但每条请求打不同键，都不能证明并发安全；结论里必须写清**并发度 N、屏障方式、实例数**，缺一项即降级为「待确认」。
- `llm-eval-audit.py` 同理：`scan` 只认静态线索（无评测集、单样本、无基线、超时出分母、judge 未校准、judge = generator、未 pin snapshot、无成本观测、注入用例缺失、污染未查）；`stats` 只做算术（Wilson CI、McNemar 精确 p、Cohen's κ、逐类 pass rate），输入 JSONL 由测试者提供、**可伪造**；**统计显著 ≠ 模型可用**，**κ 达标 ≠ 判定器无偏**，**离线绿 ≠ 线上可用**。
- R-23 不认「串行重放通过」「代码里有锁」「压测没报错」「幂等键存在」「有事务注解」；R-24 不认「跑通一遍」「LLM judge 说好」「单次 87 分」「评测集 20 条」「改了 prompt 分数涨」。

### 深度实测（dogfood，模拟用户项目）

**并发侧**：在 `.workbuddy-ai/dogfood/v1.14.0/concurrency/` 建了一个 7 文件的零依赖反模式夹具（`demo_app/`：先查后写扣库存、`SETNX`+`EXPIRE` 两步锁、无唯一约束重复建单、先 ack 后处理消费者等），并用 `events.jsonl`（9 条有效事件 + 1 条注释 + 1 条坏行）模拟副作用日志，真实执行日志见 `run.log`（15040 字节，含命令原文与退出码）：

- `concurrency-audit.py scan demo_app` → **10 条命中（8 HIGH / 2 MEDIUM）**，id 集合 `CC-01/02/03/04/05/06/08/10`；`CC-07`（`version` 未进 `WHERE`）与 `CC-09` 只在 `--self-test` 夹具里覆盖；`CC-03`/`CC-08` 在 `lock.py` 各命中 2 处，属启发式噪声，报告已按 §11 第 7 项逐条标「需人工裁决」。
- `concurrency-audit.py side-effects --events events.jsonl --fail-on-gap` → **exit 1**，5 个键 / 9 条事件 / 1 条坏行，**2 个违规键**：`ord-1002`（一键多资源）、`ord-1003`（同键副作用 2 次）。
- 手工裁决结论：扣库存路径为「先查后写 + 无 `version` CAS + 无原子 `UPDATE … WHERE stock >= ?`」，按 R-23 判 **S1**（并发即超卖）；`SETNX` 后 `EXPIRE` 两步之间进程崩溃可致锁永不过期，判 **S1**。

**评测侧**：在 `.workbuddy-ai/dogfood/v1.14.0/llm-eval/` 建了评测 harness（6 文件）与 `runs.jsonl`（29 次采样）、`baseline.jsonl`（29 条基线）、`judge.jsonl`（36 条人工/judge 对照），真实执行日志 126 行：

- `llm-eval-audit.py stats --fail-on-gap` → pass **23/29 = 79.3%**，Wilson 95% CI **[61.6%, 90.2%]**；8 个 case，error 2（6.9%）与 timeout 1（3.4%）**均计入分母**；p50/p95 = **888/1500 ms**；基线 McNemar **b=6 c=0，双尾 p=0.031250**（当前优于基线）；judge 36 条，po=0.7500 pe=0.5000，**Cohen's κ=0.5000**（阈值 0.60 → 判不可用）。**exit=1**，3 条 FAIL 原因：pass rate < 80%、`c07`/`c08` 的 n=1（样本量不足）、κ < 0.60。
- `llm-eval-audit.py scan` 夹具 → **LE-01~LE-10 全部命中（13 条 findings），`--fail-on-gap` exit 1**；`cases` exit 0。
- 手工裁决结论：单次采样 + judge 自评的系统按 R-24 判 **S1**（评测结论不可信）；把超时样本算通过判 **S1**（分母造假）。
- **dogfood 反向修复（本轮真实缺陷）**：用 `scan` 扫技能仓库自身时命中 6 条（`SKILL.md:33`、`references/ai-native-testing.md`、`references/idempotency-concurrency-testing.md`、`scripts/test-data-gen.py`、`scripts/error-audit.py`），全是**文档正文引用反模式原文**（「不要写 `temperature: 1.0`」「超时必须计入分母」）被正则误伤——旧实现只排除了自己的手册/模板，没排除其它 `.md`。已修：`scan` 默认跳过 `.md`（`EVAL_SUFFIXES` 去掉 `.md`），新增 `--include-docs` 显式开启，并在 `--self-test` 加文档噪声回归断言；修复后自扫 0 命中、纯代码夹具仍 13 条全中。手册 §10 写入「扫描范围契约」，`tools.md` 与 `selfcheck.py` §7f 同步锁住 `--include-docs`。

证据与报告已归档 `.workbuddy-ai/dogfood/v1.14.0/{concurrency,llm-eval}/`（夹具源码、JSONL、run.log、报告）；该目录本地记忆、不入库。

### 自检与门禁

- `python scripts/selfcheck.py`：**GREEN**（PASS 77 / WARN 0 / FAIL 0，exit 0）。
- 四个负向测试（临时副本 `D:\My Skills\.negtest`，不污染源，实测输出见 `.workbuddy-ai/dogfood/v1.14.0/MANIFEST.md` §4）：① `assets/report-template.md` 的 `| R-23` 行改号 → `[FAIL] 报告证据矩阵缺少规则表格行: R-23`（§7d）；② 删 `references/llm-eval-testing.md` 并把引用改成 `llm-eval-gone.md` → `[FAIL] 断链引用: …` 6 条（§3）；③ `SKILL.md` 的 `**R-24 …**` 行改号 → `[FAIL] quality-gates.md 出现 SKILL.md 未定义的规则: R-24` + 矩阵同步 FAIL（§7c/§7d）；④ 把 `references/tools.md` 里 `concurrency-audit.py` 抹成 `X-audit.py` → `[FAIL] references/tools.md 未登记脚本: concurrency-audit.py`（§7a）。四例全部 exit 1，还原后回 GREEN。
- 16 个带 `--self-test` 的脚本全部 exit 0（`selfcheck.py` 本身由上述 GREEN 覆盖）。两个新脚本自扫技能仓库：`concurrency-audit.py scan .` **0 命中**（仓库无并发写路径，符合预期）；`llm-eval-audit.py scan .` 修复前 6 条全是文档噪声，修复后 **0 命中**（见上「dogfood 反向修复」）——「0 命中」只说明没有已知形态，**不等于**仓库无缺陷。`llm-eval-audit.py` 按 Python 3.9 语法做了 `ast` 校验，`concurrency-audit.py` 过 `py_compile`。
- 同步全局 `C:\Users\摩羯座\.agents\skills\project-tester` 并逐文件 sha256 比对（排除 `.git`/`.workbuddy-ai`）0 差异；git commit + push 到 `https://github.com/Soren-Blade/project-tester.git`。

### 提案处置

- **已吸收**（v1.13 提出）：「指标接口硬编码常量静态规则」→ 本轮**仍未落地**，但 R-24 的 `LE-10`「合成数据/评测集污染未查」间接覆盖同类「字面量冒充测量」问题；判据仍待定，继续待评估。
- **已吸收**（本轮 dogfood）：`CC-07`/`CC-09` 仅 self-test 覆盖（夹具缺对应写法）已在手册 §9 标注覆盖边界；未做规则合并以免误报。
- 待评估：并发结论的「最小并发度 N 门槛」目前给的是 N≥10（写路径 20~50），缺跨语言经验值 —— 需更多真实项目回归再定。
- 待评估：`side-effects` 的事件 schema 目前绑定 JSONL 六字段，是否需要兼容 OTel span 导出。
- 待核实：不同消息中间件（Kafka / SQS / RabbitMQ / NATS）的「重复投递窗口」与 at-least-once 默认行为差异 —— 需各跑一次真实注入，不把 Kafka 的语义推广到全家。
- 顺延：批量 207 逐条 code 一致性、税务辖区舍入矩阵、缓存键 × 身份 × tenant × locale 矩阵、上传解码重编码自动化、AI 变异杀伤跨语言跑数、qrels 双标注 κ 自动比对。

---

## [v1.13.0] — 2026-11-17 · 每日升级 #14

**主题**：从「翻得准 · 报得清」扩展到「**搜得准 · 数得对**」——搜索相关性与排序质量（R-21）与指标口径与报表可信（R-22）。一个分页正确、错误契约也规范的系统，仍然会在「搜『蓝牙耳机』第一页出来的是音箱和手机壳」「同一个词上午搜和下午搜 top-10 不一样」「翻到第 2 页又看到第 1 页那三条」「零结果率 18% 没人看」「看板写转化率 3.2%、源表算出来 4.1%」「两个报表 GMV 差 8 万，两边都说自己对」「A/B 说提升 12%，其实是分流比例坏了」上成片出错；这类缺陷不是「没测」，而是「相关性、排序稳定性、指标定义与对账没有可证伪判据」。新增 **R-21 搜索相关性与排序质量**、**R-22 指标口径与报表可信** 与六份文件（2 手册 + 2 矩阵模板 + 2 零依赖脚本），蒸馏底座为 NDCG 原论文 / TREC `trec_eval` / ir_measures / BEIR、Elasticsearch 的 `search_after`、`max_result_window`、`track_total_hits` 与 tie-breaker 语义、二次加权 κ、dbt MetricFlow 与 dbt tests、GA4 的 users vs sessions 口径差、Microsoft ExP 的 SRM 卡方、Simpson 悖论。按每日升级序列记为 #14。

**遵循上轮建议**：未重写已覆盖的 20 个主题与五阶段、四层模型、路由闭环，以 **New 两条规则 + Enhance 全链路接线**；四层模型与五阶段流程**未改语义**，只升 MINOR。吸收 v1.12 遗留提案「分页 collation 声明 vs 实测自动化」的**检索侧**——本轮把它推进为「排序顺序必须可复现」：唯一 tie-breaker + 两次同 query 的 top-20 逐位 diff + 第 2 页拼接去重（R-21 §5、SR-25）；该提案的数据库方言元数据读取部分仍**待评估**（不能零依赖通用）。「批量 207 部分失败逐条 code」仍**待评估**；「AI 变异杀伤跨语言自动跑数」继续受变异工具 JSON schema 未定阻塞，顺延；「`money-audit.py` 自动拉渠道对账单」维持**已驳回**（违反零依赖/不联网边界）。每轮至少一条可证伪规则 → 本轮引入 **R-21/R-22**，并做了**四例负向测试**。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 分类 | 对象 | 处置 |
|---|---|---|
| New | `references/search-quality-testing.md`、`assets/search-quality-matrix-template.md`、`scripts/search-audit.py` | 新增 R-21 能力：qrels 0~3 分级与九层样本量（合计 ≥200）、二次加权 κ≥0.60、bootstrap CI 半宽 >0.08 只写方向、DCG/IDCG/nDCG/MRR/Recall/Precision/零结果率公式与分母、查询理解九类、排序稳定性与唯一 tie-breaker、`search_after`/`max_result_window`/`track_total_hits`、filter vs post_filter、冷启动兜底标记、highlight XSS 与 DSL 注入、CI 门槛（nDCG@10 相对下降 >2% 阻塞）；SR-01~SR-10 静态 + SR-20~SR-25 评估 |
| New | `references/metrics-correctness-testing.md`、`assets/metrics-correctness-matrix-template.md`、`scripts/metric-audit.py` | 新增 R-22 能力：指标定义卡十项（分子/分母/时间窗/时区/去重键/过滤/来源/新鲜度/负责人/版本）、dashboard·API·源表三处对账与双阈值（0.5%+2 单 / 0.1%+1 元 / 0.2pp / 1%+50 人）、七类口径陷阱（平均的平均、率的分母、重述、辛普森、分群泄漏、测试流量、时区边界）、新鲜度与重述、可加性、SRM 卡方与固定样本、权限 k<10 抑制；MA-01~MA-10 静态 + MA-20~MA-26 核对 |
| Enhance | `SKILL.md`（description 触发词、v1.13 增量段、阶段 1 搜索面/指标面、阶段 3 两条专项、判 bug 第 13 条、**二十二条**规则表、阶段 4 自检、索引） | 只增量，不改五阶段与四层模型；「二十条」标题与阶段 4 矩阵行数同步到「二十二条/二十二行」 |
| Enhance | `references/dissect.md` §6/§8、`references/quality-gates.md` §3/§8、`assets/report-template.md` 证据矩阵 | 搜索/指标两面路由与解剖项、结论作废判据、22 行矩阵与「不得写成」交叉引用 |
| Enhance | `references/tools.md` | 专项工具表补 2 行（scan/eval/check/`--self-test` 与降级路径）+ 可用性探测 2 行 |
| Enhance | `scripts/selfcheck.py` §5/§7f、`README.md`、`CHANGELOG.md`、`memory/global-lessons.md` | 登记 4 个新文件字段、2 个新脚本门禁、徽章/结构/速查/设计点/版本史、教训与提案 |
| Existing | 其余 38 份手册与 27 份模板 | 不重复造，仅在路由/交叉项里引用 |

### 蒸馏来源（深度蒸馏，URL 全记录）

- Järvelin & Kekäläinen, *Cumulated gain-based evaluation of IR techniques*（nDCG 原论文）：https://dl.acm.org/doi/10.1145/582415.582418
- `trec_eval`（qrels 格式与指标定义）：https://github.com/usnistgov/trec_eval
- ir_measures（指标口径与实现对照）：https://ir-measur.es/
- BEIR（跨域 nDCG@10 报告口径）：https://arxiv.org/abs/2104.08663
- Elasticsearch 分页（`from+size` / `search_after` / `max_result_window`）：https://www.elastic.co/docs/reference/elasticsearch/rest-apis/paginate-search-results
- Elasticsearch 排序（tie-breaker 与 sort 语义）：https://www.elastic.co/docs/reference/elasticsearch/rest-apis/sort-search-results
- Elasticsearch BM25 相似度：https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules-similarity.html
- scikit-learn `ndcg_score`（实现参数与 tie 处理）：https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg_score.html
- interleaving 评估（在线排序对比）：https://dl.acm.org/doi/10.1145/2094072.2094078
- OWASP Query Parameterization（注入防护）：https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html
- Cohen's κ（二次加权一致性口径）：https://en.wikipedia.org/wiki/Cohen%27s_kappa
- dbt 数据测试（unique / not_null / accepted_values / relationships）：https://docs.getdbt.com/docs/build/tests
- dbt MetricFlow 语义层指标定义：https://docs.getdbt.com/docs/build/about-metricflow
- GA4 sessions vs users 口径差：https://support.google.com/analytics/answer/12159447
- Microsoft ExP：Diagnosing SRM in A/B testing：https://www.exp-platform.com/Documents/2019-02-SRM.pdf
- Simpson 悖论（Stanford Encyclopedia of Philosophy）：https://plato.stanford.edu/entries/paradox-simpson/
- PostgreSQL 日期/时间与时区语义：https://www.postgresql.org/docs/current/datatype-datetime.html

### 口径诚实

- `search-audit.py` **不联网、不代填**：`scan` 是逐行启发式（拼接 DSL、时间冒充排序、`from+size` 深翻、`track_total_hits` 缺失、CJK 无 analyzer、highlight 未转义、ACL 后置、前导 wildcard、`LIMIT` 不夹取、日志 PII），命中只是「可疑写法」，**不证明**相关性成立；`eval` 的 nDCG/MRR/Recall 完全取决于测试者给的 qrels 与 runs，**可伪造**，单人标注无 κ 时**不得**外推业务效果；`--fail-on-gap` 只把已发现的缺口变成非零退出码，**不把「没发现」变成「搜索达标」**。
- 无判定集 query（如 dogfood 的「月球基地」）只计零结果率；nDCG 记「—」、不进均值、**不触发** SR-21——「未评测」不得读成「相关性差」。这条口径由本轮 dogfood 逼出来（见下）。
- `metric-audit.py` 同理：`scan` 只认静态写法（`COUNT(*)` 无 WHERE、`AVG(AVG())`、`23:59:59`、缺 `DISTINCT`、金额 float、响应无 `as_of`、`SELECT *`、无 SRM）；`check` 只核给到的 `metrics.json`（定义卡字段、两处取值、双阈值、新鲜度、分子>分母、SRM），dashboard/source 数字由测试者提供，**可伪造**；**静态未命中 ≠ 口径正确**——dogfood 里硬编码的 `paid_orders: 1234` 就没有被任何静态规则捕获。
- SRM 用 df=1 卡方与 `p<0.001` 判分流异常，只说明「分配比例不像随机」，**不证明**实验无偏（埋点、去重、跨设备身份仍可能错）；「对账一致」也不升级为「口径正确」，只证明三处当前取值一致。
- R-21 不认「手工试了几个词」「CTR 高」「两次看着一样」「有同义词表」「零结果少」；R-22 不认「看板截图」「数字差不多」「p<0.05」「单一汇总值」「日均值求平均」。

### 深度实测（dogfood，模拟用户项目）

在项目外临时目录 `C:\Users\摩羯座\AppData\Local\Temp\pt-v113-dogfood\searchmetric-demo` 建了一个零依赖 Node 24 夹具（`node:http`，40 条商品 + 搜索/翻页/指标/实验端点 + 一个前端渲染文件），故意植入缺陷：`LIKE` 字符串拼接、`ORDER BY created_at` 无 tie-breaker、先切片后租户过滤、`total: 10000` 常量、`LIMIT size` 不夹取、highlight 拼 `<em>`+q、日志打 q 与 `user_email`、`/api/metrics` 硬编码 1234、`metrics.json` 定义卡缺字段与分子>分母；用 `probe.js` 真实请求采集：

- **真实 HTTP 证据**：耳机/跑鞋/咖啡/键盘/显示器 **五个 query 返回同一组 top-6**（`doc-20,39,38,18,17,36`）；`total` 恒 10000；月球基地 0 结果；page0 6 条 / page1 7 条、overlap=[]（tenant-a 共 27 条）；注入 `' OR 1=1 --` 返回 200 并回显 `... WHERE title LIKE '%' OR 1=1 --%' ORDER BY created_at DESC LIMIT 3 OFFSET 0`；`size=100000` 实际返回 26；以 alice 身份 `tenant=tenant-b` 拿到 14 条 tenant-b 文档；dashboard 1234 vs 源表 1301（5.150%）；实验 5000/250 vs 5100/280（SRM p=3.197e-01）。
- `search-audit.py scan`：9 行（SR-01 CRITICAL、SR-02 HIGH×2、SR-03、SR-06×2、SR-07、SR-09、SR-10），其中 ACL 后置与拼接 DSL 由 `--fail-on-gap` 判 exit 1；`eval`：13 gap（SR-20 S1 ×1、SR-21 HIGH ×7、SR-23 MEDIUM ×5），mean nDCG@10 = 0.235121，零结果率 11.1%（8 条有判定集 query 参与均值）。
- `metric-audit.py scan`：0 行（静态规则不解析指标定义 JSON，D14 硬编码 1234 靠人工发现）；`check`：6 gap（MA-21×2、MA-20×2、MA-22、MA-23），SRM 表输出 χ²≈0.99、p=3.197e-01。
- 合计 **19 条脚本 gap + 3 项人工发现**，质量状态 **FAIL**、发布建议 **No-Go**（S1 4 / HIGH 7 / MEDIUM 3）。
- **dogfood 反向改进了技能（本轮真实增量）**：① `SR-06` 把 `el.innerHTML = ""`（清空占位）误判为 XSS sink → 赋值目标改为 `[^"'\s]`，空串不再命中，`web.js:6` 消失、`:9` 保留；② 无判定集的「月球基地」被算成 nDCG=0 并报 SR-21「相关性差」→ `query_metrics` 增 `judged`，SR-21/SR-23 只对有判定集 query 生效、均值只统计有判定集 query，复跑 mean nDCG 0.209→0.235；③ `metric-audit` 文件级规则一律报 `line 1`，且把含 `fetch`/`res.json` 的前端 `probe.js` 判成指标服务端 → 增 `line_of()` 取真实命中行 + `is_client` 排除，假阳性消失；④ 手册 §9 的 SR 编号与脚本**整体错位**（手册 SR-01=LIKE、脚本 SR-01=拼接，SR-06/07/08 全错位）→ 按脚本重排 §9 十行、补 SR-08「前导 wildcard」，README/SKILL 的脚本索引同步。
- 证据与报告已归档 `.workbuddy-ai/dogfood/v1.13.0/`（`tree.md`、`report.md`、4 份工具输出、3 份采集 JSON、夹具源码与 `MANIFEST.sha256.json`）；该目录本地记忆、不入库。

### 自检与门禁

- `python scripts/selfcheck.py`：**GREEN**（PASS 71 / WARN 0 / FAIL 0，exit 0）。
- 四个负向测试（临时副本，不污染源）：① 删 `assets/report-template.md` 的 `| R-21` 行 → §7d FAIL；② 删 `references/search-quality-testing.md` → 断链 FAIL；③ 删 `SKILL.md` 的 R-22 规则行 → §7c 双向同步 FAIL；④ 把 `references/tools.md` 里 4 处 `metric-audit.py` 全部抹成 `X-audit.py` → §7a 工具表登记 FAIL。还原后回 GREEN。
- 14 个带 `--self-test` 的脚本全部 exit 0（`selfcheck.py` 本身由上述 GREEN 覆盖）；`search-audit.py scan .` / `metric-audit.py scan .` 对技能仓库自身「未命中已知模式」（证明无自伤，也不等于仓库无缺陷）。
- 同步全局 `C:\Users\摩羯座\.agents\skills\project-tester` 并逐文件 sha256 比对（排除 `.git`/`.workbuddy-ai`）0 差异；git commit + push 到 `https://github.com/Soren-Blade/project-tester.git`。

### 提案处置

- **已吸收**（v1.12 提出）：「分页 collation 声明 vs 实测自动化」的检索侧 → R-21 §5 的「唯一 tie-breaker + 两次 top-20 逐位 diff + 第 2 页拼接去重」+ `SR-25`；数据库方言元数据部分仍待评估。
- **已吸收**（本轮 dogfood）：四条真实缺陷（空串 sink 误报、无判定集 nDCG 误报、文件级行号/前端假阳性、手册 SR 编号错位），均加回归并在本条目记录。
- 待评估：指标接口「硬编码常量」静态规则（子串/字面量判据未定，易把配置常量误报）。
- 待评估：qrels 双标注一致性的自动比对（两文件逐 query κ 矩阵）。
- 待核实：不同检索后端（ES / OpenSearch / pgvector / Meilisearch）对 `track_total_hits`、`max_result_window`、tie-breaker 的默认差异，需各跑一次真实请求，不把 ES 的 10000 默认推广到全家。
- 顺延：批量 207 逐条 code 一致性、税务辖区舍入矩阵、缓存键双会话矩阵、上传解码重编码自动化、AI 变异杀伤跨语言跑数。

---

## [v1.12.0] — 2026-11-16 · 每日升级 #13

**主题**：从「缓存不串号 · 文件不可当代码」扩展到「**翻得准 · 报得清**」——查询语义与分页正确性（R-19）与错误契约与可诊断性（R-20）。一个接口全绿、金额也对、缓存也隔离的系统，仍然会在「第 1 页的 10 条永远看不到」「翻页时后台插了 1 行，后面 10 条被跳过」「`total` 显示 33 但只有 18 条可见」「`sort=created_at LIMIT 1` 让 500 把 SQL 与堆栈一起吐给用户」「429 没 `Retry-After`，客户端把重试打成雪崩」上成片出错；这类缺陷不是「边界没测」，而是「分页契约与错误契约没有可证伪判据」。新增 **R-19 查询语义与分页正确性**、**R-20 错误契约与可诊断性** 与六份文件（2 手册 + 2 矩阵模板 + 2 零依赖脚本），蒸馏底座为 Use The Index Luke「No OFFSET Movement」、PostgreSQL/MySQL collation、RFC 8288、GraphQL Relay Cursor、OWASP SQLi Prevention，以及 RFC 9457 / 9110 / 6585 / 4918、OWASP Error Handling Cheat Sheet、OWASP WSTG ERRH、CWE-209、W3C Trace Context。按每日升级序列记为 #13。

**遵循上轮建议**：未重写已覆盖的 18 个主题与五阶段、四层模型、路由闭环，以 **New 为主 + Enhance 为辅**；四层模型与五阶段流程**未改语义**，只升 MINOR。**吸收 v1.9 遗留提案**：「5xx 响应体不得含堆栈 / 绝对路径 / SQL」此前只记提案未扩 scope，本轮做成 R-20 的固定检查项 + 报告字段 + `error-audit.py` 的 EC-20/EC-01/EC-02/EC-06，并用真实 500 证据验收。上轮「税务辖区舍入矩阵」「缓存键 × 身份 × tenant × locale 自动矩阵」「上传解码重编码证据自动化」继续**待评估**；「AI 变异杀伤跨语言自动跑数」仍受变异工具 JSON schema 未定阻塞，顺延；「`money-audit.py` 自动拉渠道对账单」维持**已驳回**（违反零依赖/不联网边界）。每轮至少一条可证伪规则 → 本轮引入 **R-19 / R-20**，并做了**三例负向测试**。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 分类 | 对象 | 处置 |
|---|---|---|
| New | `references/query-pagination-testing.md`、`assets/query-pagination-matrix-template.md`、`scripts/query-audit.py` | 新增 R-19 能力：分页三模式契约（offset/keyset/cursor）、全量遍历去重后必须等于 `total`、翻页插删的重复与遗漏、`ORDER BY` 唯一 tie-breaker 与 NULL 位置、排序白名单与注入、collation 声明 vs 实测、行级授权与 `total` 泄漏、深页 p95；QP-01~QP-08 静态扫描 + QP-20~QP-30 清单判定 |
| New | `references/error-contract-testing.md`、`assets/error-contract-matrix-template.md`、`scripts/error-audit.py` | 新增 R-20 能力：三层契约（传输码 / 机器 `code` / 人类 `message`+`trace_id`+`docs_url`）、逐状态码矩阵与 401vs403 / 404vs403 / 409vs422 判据、5xx 防泄漏硬门禁（堆栈/绝对路径/SQL/内网主机/版本/调试页/source map）、六框架默认核对、可诊断性、存在性三态泄漏、错误路径副作用与重试分类；EC-01~EC-08 静态扫描 + EC-20~EC-31 清单判定 |
| Enhance | `SKILL.md`（description 触发词、v1.12 增量段、阶段 1 查询面/错误面、阶段 3 两条专项、判 bug 第 12 条、**二十条**规则表、阶段 4 自检、索引） | 只增量，不改五阶段与四层模型；顺带把「十六条可证伪规则」标题漂移修正为「二十条」并补齐 v1.11/v1.12 括号说明 |
| Enhance | `references/dissect.md` §6/§8、`references/quality-gates.md` §3/§8、`assets/report-template.md` 证据矩阵 | 查询/错误两面路由与攻击面、结论作废判据、20 行矩阵 |
| Enhance | `references/tools.md` | 补登记 v1.10/v1.11 遗漏的 4 个脚本（money/webhook/cache/upload）+ 本轮 2 个脚本 + 长期缺席的 `selfcheck.py` / `test-data-gen.py`，含 `--self-test` 探测与降级路径；纪律补第 18~22 条 |
| Enhance | `scripts/selfcheck.py` §5/§7f/**新增 §7a**、`README.md`、`CHANGELOG.md`、`memory/global-lessons.md` | 登记 6 个新文件字段、2 个新脚本门禁、**新增「tools.md 必须登记 scripts/ 下每个脚本」硬门禁**、徽章/结构/速查/设计点/版本史、教训与提案 |
| Existing | 其余 36 份手册与 25 份模板 | 不重复造，仅在路由/交叉项里引用 |

### 蒸馏来源（深度蒸馏，URL 全记录）

- PostgreSQL `LIMIT`/`OFFSET` 与「无 ORDER BY 时顺序未定义」：https://www.postgresql.org/docs/current/queries-limit.html
- ISO SQL:2023 对 `OFFSET` 的语义 + keyset/seek（`WHERE id < ?last_seen ORDER BY id DESC FETCH FIRST n ROWS ONLY`）：https://use-the-index-luke.com/no-offset
- 深分页与索引（分页查询执行计划）：https://use-the-index-luke.com/sql/partial-results/fetch-next-page
- RFC 8288 Web Linking（`Link: rel="next"` 分页头）：https://www.rfc-editor.org/rfc/rfc8288.html
- GraphQL Relay Cursor Connections（`edges/pageInfo`、cursor 不透明）：https://relay.dev/graphql/connections.htm
- OWASP SQL Injection Prevention（`ORDER BY` 白名单与参数化边界）：https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- MySQL collation（`utf8mb4_0900_ai_ci` 大小写/重音不敏感）：https://dev.mysql.com/doc/refman/8.4/en/charset-collation-names.html
- PostgreSQL collation 与 ICU：https://www.postgresql.org/docs/current/collation.html
- Unicode TR10（土耳其 i / 德语 ß 的大小写特例）：https://www.unicode.org/reports/tr10/
- RFC 9457 Problem Details（`type/title/status/detail/instance`、`application/problem+json`）：https://www.rfc-editor.org/rfc/rfc9457.html
- RFC 9110 HTTP Semantics（401/403/404/405/409/415/503、`WWW-Authenticate`、`Retry-After`）：https://www.rfc-editor.org/rfc/rfc9110.html
- RFC 6585（429 + `Retry-After`）：https://www.rfc-editor.org/rfc/rfc6585.html
- RFC 4918（422、207 Multi-Status）：https://www.rfc-editor.org/rfc/rfc4918.html
- OWASP Error Handling Cheat Sheet（5xx 只回通用体、细节只进服务端日志、各框架配置范式）：https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html
- OWASP WSTG — Testing for Improper Error Handling：https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/08-Testing_for_Error_Handling/
- CWE-209（错误消息含敏感信息）：https://cwe.mitre.org/data/definitions/209.html
- W3C Trace Context（`traceparent`/`tracestate`）：https://www.w3.org/TR/trace-context/
- ASP.NET Core 错误处理（`UseDeveloperExceptionPage` 仅开发）：https://learn.microsoft.com/aspnet/core/fundamentals/error-handling
- Spring Boot 错误属性（`server.error.include-stacktrace`）：https://docs.spring.io/spring-boot/reference/web/servlet.html#web.servlet.spring-mvc.error-handling

### 口径诚实

- `query-audit.py` **不联网、不代填**：`scan` 是逐行启发式（排序键拼接、LIMIT/OFFSET 插值、`total=rows.length`、无 tie-breaker、分页参数无夹取、LIKE 未转义），命中只是「可疑写法」，**不证明**运行时翻页正确；`matrix` 的数据由测试者提供，可伪造。`--fail-on-gap` 只把已发现的 S1 变成非零退出码，**不把「没发现」变成「分页正确」**。
- `query-audit.py` 的 QP-06 夹取判定是「同一行 ±10 行窗口」而非全文件——dogfood 实测证明全文件判定会被同文件里无关的 `MAX(id)` 静音（漏报），窗口化后用 `agg.js`（远处聚合）与 `clamp.js`（近距离夹取）双向回归锁住；窗口仍可能漏掉「夹取写在另一个模块」的合法写法，命中后必须人工确认。
- `error-audit.py` 同理：`scan` 只看响应路径是否输出 `.stack`、是否 `res.json(err)`、是否 `include-stacktrace=always` / `debug=True` / `display_errors=On`、空 catch、404 回 200、调试路由、message 拼路径；`check` 只核给到的 JSON 样本（状态码、`Content-Type`、`code`/`trace_id`、`Retry-After`、存在性三态、配置）。**静态未命中 ≠ 生产不泄漏**：运行期才出现的堆栈、框架默认页、反代注入的 HTML 错误页都可能绕过。
- 堆栈识别用文件扩展名锚定（`.js/.py/...` + `:line[:col]`），故意不匹配 `at 10:30` 这类时间文本；代价是 `at node:events:517:28` 这种无扩展名的内部帧不单独判泄漏——所以判据是「应用帧或绝对路径 + 堆栈形态」的合取，单条正则不足时人工看原文。
- RFC 9457 是**推荐格式**而非强制：手册允许团队自定义错误体，但要求「机器 `code` 稳定 + 人类 `message` 不泄漏 + `trace_id` 可检索」三件事都有证据；**不得**把「用了 problem+json」写成「错误契约合格」。
- R-19 不认「翻了一遍没重复」「首页 10 条对」「`total` 数字对得上页面」「第 1 页快」；R-20 不认「返回 500」「有 `trace_id`」「4xx 无堆栈」「框架默认不回堆栈」。

### 深度实测（dogfood，模拟用户项目）

在项目外临时目录 `C:\Users\摩羯座\AppData\Local\Temp\pt-v112-dogfood\pagerr-demo` 建了一个零依赖 Node 24 夹具（`node:http` + `node:sqlite`，33 行数据，监听 `127.0.0.1:4321`），故意植入 12 类缺陷（`offset = page * size`、排序键拼接、`total = rows.length`、500 回 `e.stack`、not-found 回 200、429 无 `Retry-After`、未认证 403、HTML 错误页反射 `<script>`、`include-stacktrace=always`、`debug=true` 等），全程只读技能目录：

- 真实 HTTP 采集（`probe.js`）：`baseline dup=[] missing=["3","6","9","12","15","18","21","24","27","30"]`（首屏 10 条永不可见）；插行后 `drift` 同样漏 10 行；`collation count=33 group=["ALPHA","Alpha","alpha"]`（声明 nocase、实测 binary）；`p95_page3=2 size5000=200 sizeNaN=500 pageNeg=200 inj=500 pub=200`；`errors: boom=500 nf=200 throttle=429 admin=403 html=text/html v2=422`。
- `query-audit.py scan`：6 行（QP-01 CRITICAL、QP-02/03 HIGH、QP-04/06 MEDIUM ×2），exit 1；`matrix`：10 行（QP-21/22/25/29 S1，QP-23/24 HIGH，QP-26/27/28 MEDIUM），exit 1。
- `error-audit.py scan`：5 行（EC-01 CRITICAL ×2、EC-03 HIGH ×3），exit 1；`check`：9 行（EC-20 S1「堆栈、绝对路径」、EC-29 S1、EC-21/22/23/24/25/27 HIGH），exit 1。
- 合计 **30 项命中（S1 7 / CRITICAL 3 / HIGH 12 / MEDIUM 8）**，质量状态 **FAIL**、发布建议 **No-Go**；注入响应原文含 `near "LIMIT": syntax error` 与 `C:\Users\...\pagerr-demo\server.js:41:23`。
- **dogfood 反向改进了技能（本轮真实增量）**：① `QP-06` 原用整文件判定夹取，被夹具里 `COALESCE(MAX(id),0)` 静音 → 改为逐行 ±10 行窗口，并加 `agg.js`/`clamp.js` 双向回归；② `STACK_RE` 原只认 `at file:line`，漏掉 V8 括号帧 `at handler (./src/app.js:41:23)` → 改为括号帧 + 带扩展名裸帧，并加「`at 10:30` 不得误判」回归。两脚本自测复跑：query `SELFTEST GREEN（静态 8 / 清单 11 / 干净夹具零误报）`、error `SELFTEST GREEN（静态 6 / 清单 12 / 干净夹具零误报）`。
- 证据与报告已归档 `.workbuddy-ai/dogfood/v1.12.0/`（`tree.md`、`report.md`、4 份工具输出、3 份采集 JSON 与 `MANIFEST.sha256.json` 校验和）；该目录本地记忆、不入库。

### 自检与门禁

- `python scripts/selfcheck.py`：**GREEN**（PASS 65 / WARN 0 / FAIL 0，exit 0）。
- 四个负向测试（临时副本，不污染源）：① 删 `assets/report-template.md` 的 `| R-19` 行 → §7d FAIL；② 删 `references/error-contract-testing.md` → 断链 4 处 FAIL；③ 删 `SKILL.md` 的 R-20 规则行 → §7c 双向同步 FAIL；④ 把 `tools.md` 里的 `error-audit.py` 抹成 `X-audit.py` → 新增的 §7a 工具表登记门禁 FAIL。还原后回 GREEN（65/0/0）。
- 新增 §7a 门禁的直接来由：`references/tools.md` 此前从未登记 `selfcheck.py` 与 `test-data-gen.py`，v1.10/v1.11 的四个脚本也长期缺席——「手册里有脚本、工具表查不到命令」这类漂移靠人眼守不住，改成逐文件比对 `scripts/*.py ⊂ tools.md`，缺一个即 FAIL。
- 12 个脚本 `--self-test` 全部 exit 0；`query-audit.py scan .` / `error-audit.py scan .` 对技能仓库自身「未命中已知模式」（证明无自伤，也不等于仓库无缺陷）。
- 同步全局 `C:\Users\摩羯座\.agents\skills\project-tester` 并 `diff -r`（排除 `.git`/`.workbuddy-ai`）0 差异；git commit + push 到 `https://github.com/Soren-Blade/project-tester.git`。

### 提案处置

- **已吸收**（v1.9 提出）：「5xx 响应体不得含堆栈 / 绝对路径 / SQL」做成 R-20 固定检查项 + 报告矩阵行 + `error-audit.py`（EC-20 五正则、EC-01/02/06/08 静态），dogfood 以真实 500 原文验收。
- 采纳：dogfood 暴露的 `QP-06` 全文件静音与 `STACK_RE` 漏 V8 括号帧，直接改脚本并加双向回归（旧断言只覆盖了 `at file:line` 与绝对路径，覆盖不到括号帧）。
- 采纳：`tools.md` 长期漏登 v1.10/v1.11 脚本，本轮补齐 6 行工具表 + 8 条 `--self-test` 探测 + 5 条纪律（第 18~22 条），并把它变成 §7a 硬门禁，避免「手册有脚本、工具表查不到」再次发生。
- 待评估：分页「collation 声明 vs 实测」自动化（需按数据库方言读 `information_schema` / `pg_collation`，不能零依赖通用）。
- 待评估：错误契约的 207/部分失败矩阵（批量接口逐条 `code` + 顶层 `status` 的一致性判据，本轮只给单条判据）。
- 待核实：Express 5 / Fastify 4 / Koa 在 `NODE_ENV=production` 下的默认错误体差异，需逐框架跑一次真实 500，不把「Express 默认不回栈」推广到全家。
- 待核实：`selfcheck.py` 的 §7a 只核「脚本名出现在 tools.md」，不核「命令与真实 `--help` 一致」——脚本参数改名而工具表未更新仍会通过，需评估是否加 `--help` 抓取比对（会引入执行依赖，暂不做）。
- 顺延：税务辖区舍入矩阵、缓存键双会话自动矩阵、上传解码重编码证据自动化、AI 变异杀伤跨语言跑数。

---

## [v1.11.0] — 2026-11-14 · 每日升级 #12

**主题**：从「功能、金额、交付都正确」扩展到「**缓存不串号 · 发布即生效 · 文件不可当代码**」——缓存与内容新鲜度（R-17）与文件上传下载内容边界（R-18）。一个接口全绿、金额也对、webhook 也幂等的系统，仍然会在「A 登录后 B 打开同一 URL 看到 A 的账单」「发了新版但 CDN 还吐旧页面」「把 shell 改名成 `.jpg` 就传上去了」「登出后预签名 URL 还能往桶里写」上成片出错；这类缺陷不是「边界没测」，而是「缓存键与文件边界没有可证伪判据」。新增 **R-17 缓存与内容新鲜度**、**R-18 文件上传下载与内容边界** 与六份文件（2 手册 + 2 矩阵模板 + 2 零依赖脚本），蒸馏底座为 RFC 9111 / 5861 / 8246 / 9211 / 9110 / 6266、Cloudflare Cache Deception Armor、OWASP File Upload Cheat Sheet、OWASP WSTG、S3 presigned 官方文档、sharp 构造器文档与 ImageTragick。按每日升级序列记为 #12。

**遵循上轮建议**：未重写已覆盖的 16 个主题与五阶段、四层模型、路由闭环，以 **New 为主 + Enhance 为辅**；四层模型与五阶段流程**未改语义**，只升 MINOR。上轮遗留的「AUTH/S/F 三张卡做成可执行 adapter」「税务辖区舍入矩阵」继续**待评估**；「AI 变异杀伤跨语言自动跑数」仍受变异工具 JSON schema 未定阻塞，顺延；「`money-audit.py` 自动拉渠道对账单」维持**已驳回**（违反零依赖/不联网边界）。每轮至少一条可证伪规则 → 本轮引入 **R-17 / R-18**，并做了**三例负向测试**（临时副本分别删 R-17 手册「不得」、删报告矩阵 R-18 行、删 SKILL.md R-17 行里的「不得」声明，确认 `selfcheck.py` 对应检查确实 FAIL）。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 分类 | 对象 | 处置 |
|---|---|---|
| New | `references/cache-freshness-testing.md`、`assets/cache-freshness-matrix-template.md`、`scripts/cache-audit.py` | 新增 R-17 能力：四层缓存分层与策略来源、`Cache-Control` 指令语义、`Vary` 与缓存键、ETag/304/Range、C-01~C-08 共享缓存安全用例、缓存欺骗、个性化与多租户、失效与发布、CA-01~CA-08 / CA-10~CA-16 审计 |
| New | `references/file-upload-download-testing.md`、`assets/upload-security-matrix-template.md`、`scripts/upload-audit.py` | 新增 R-18 能力：三道闸（扩展名 / 魔数与 Content-Type / 解码重编码）、U-01~U-09 绕过矩阵、落盘与执行权限、presigned bearer 语义、下载 IDOR 与 `Content-Disposition`、SVG 与压缩炸弹、UA-01~UA-08 / UA-10~UA-17 审计 |
| Enhance | `SKILL.md`（description 触发词、v1.11 增量段、阶段 1 缓存面/上传下载面、阶段 3 两条专项、十八条规则表、阶段 4 自检、索引） | 只增量，不改五阶段与四层模型 |
| Enhance | `references/dissect.md` §6/§8、`references/quality-gates.md` §3/§8、`assets/report-template.md` 证据矩阵 | 缓存/上传两面路由、结论作废判据、18 行矩阵 |
| Enhance | `scripts/selfcheck.py` §5/§7f、`README.md`、`CHANGELOG.md`、`memory/global-lessons.md` | 登记 6 个新文件字段、2 个新脚本门禁、徽章/结构/速查/设计点/版本史、教训与提案 |
| Existing | 其余 34 份手册与 23 份模板 | 不重复造，仅在路由/交叉项里引用 |

### 蒸馏来源（深度蒸馏，URL 全记录）

- RFC 9111 HTTP Caching（`no-store`/`no-cache`/`private`/`public`/`s-maxage`/`must-revalidate` 语义）：https://www.rfc-editor.org/rfc/rfc9111.html
- RFC 5861 `stale-while-revalidate` / `stale-if-error`：https://www.rfc-editor.org/rfc/rfc5861.html
- RFC 8246 `immutable`：https://www.rfc-editor.org/rfc/rfc8246.html
- RFC 9211 `Cache-Status`：https://www.rfc-editor.org/rfc/rfc9211.html
- RFC 9110 条件请求、`Vary`、`Age`：https://www.rfc-editor.org/rfc/rfc9110.html
- Cloudflare Cache Deception Armor（URL 扩展名 ↔ 返回 `Content-Type` 一致性判据；源站 Cache-Control / Edge TTL 可覆盖）：https://developers.cloudflare.com/cache/cache-security/cache-deception-armor/
- PortSwigger Web Cache Deception：https://portswigger.net/web-security/web-cache-deception
- OWASP WSTG（缓存与信息泄露测试项）：https://owasp.org/www-project-web-security-testing-guide/
- OWASP File Upload Cheat Sheet（白名单、UUID 重命名、ADS/双扩展/空字节绕过、webroot 外存储、解码重编码）：https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
- RFC 6266 `Content-Disposition`：https://www.rfc-editor.org/rfc/rfc6266.html
- Fetch `X-Content-Type-Options`（`nosniff`）：https://fetch.spec.whatwg.org/#x-content-type-options-header
- AWS S3 presigned URL（bearer token、到期前可重复使用、能力受生成者权限限制、`s3:signatureAge`）：https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html
- sharp 构造器（`limitInputPixels` 默认 268402689、`limitInputChannels` 默认 5、`unlimited` 移除防护）：https://sharp.pixelplumbing.com/api-constructor/
- ImageTragick（ImageMagick 处理不可信输入的策略要求）：https://imagetragick.com/
- CWE-434 / CWE-22 / CWE-409（不受限上传、路径穿越、解压炸弹）：https://cwe.mitre.org/data/definitions/434.html

### 口径诚实

- `cache-audit.py` **不联网、不代填**：只读本地源码/配置/头清单，不连 CDN、不回源；`scan` 命中只是「可疑写法」，`headers` 只审 `headers.json` 自述的策略，**不证明线上真实响应头**；`--fail-on-gap` 只把发现的缺口变成非零退出码，不把「没发现」变成「缓存安全」。
- `upload-audit.py` 的 `scan`/`matrix` 同理：魔数只读文件头，**不证明内容安全**（图片马、SVG 脚本、压缩炸弹都可能绕过扩展名与魔数）；`matrix` 数据由测试者提供，可伪造；presign 判据基于「断签/登出后仍有效或 uses>1」，不证明桶策略正确。
- Cloudflare Cache Deception Armor 是**平台侧缓解**，不是规范；官方文档明确写「源站 `Cache-Control` 或 Edge TTL 可覆盖该保护」，故手册要求看实际响应头与双会话结果，**不得**把「开了 Armor」写成「缓存安全」。
- ASVS 5.0 的「拒绝超大图片（pixel flood）」与「净化用户上传 SVG」两项要求只从他人标题侧证核到，官方 raw 文件 404，故手册只写「ASVS 5.0 有要求」**不写具体控制编号**，避免伪造引用。
- S3 presigned 官方页只承诺「bearer token、到期前可多次使用、受生成者权限约束」，**未承诺限制大小/类型/Content-Length**；手册据此要求配条件策略（`content-length-range`/前缀/`signatureAge`），不把「presign 能生成」写成「上传受限」。
- R-17 不认「响应头写对」「`Age` 小」「purge 接口存在」；R-18 不认「上传成功」「扩展名合法」「presign 未过期」。

### 深度实测（dogfood，模拟用户项目）

在项目外临时目录 `C:\Users\摩羯座\AppData\Local\Temp\pt-v111-dogfood\cache-upload-demo` 建了一个零依赖 Express 夹具（静态页 + 双会话接口 + 上传路由 + webroot 落盘 + 4 条头策略 + 4 条上传清单），全程只读技能目录：

- `cache-audit.py scan`：4 处命中——CA-03 HIGH（`public` 与个性化/`Set-Cookie` 同现）、CA-01 MEDIUM（`no-cache` 冒充不存储）、CA-05 LOW ×2（`immutable` 配 `max-age=60`）；
- `cache-audit.py headers`：8 处问题（**S1 4**）——CA-10 个性化标 public、CA-11 鉴权 public 缺 `Vary: Authorization`、CA-12 带 `Set-Cookie` 却非 private/no-store、CA-13 purge 未鉴权，另 CA-14 ×2、CA-15、CA-16；
- `upload-audit.py scan`：7 处命中——UA-01（`.jpg` 装 PHP）、UA-02（`.php` 落 public）、UA-03（SVG `onload`）、UA-04（`'../' + filename` 穿越）、UA-05 ×2（原始文件名 `join` 落盘）、UA-08（webroot 落点）；
- `upload-audit.py matrix`：10 处问题（**S1 9**）——UA-10/11/12/13/14/15/17 与 UA-16；
- 合计 **29 项检查，S1 13 项**，质量状态 **FAIL**、发布建议 **No-Go**（按 `quality-gates.md` §3 无条件 No-Go）；
- 两个脚本各自 `--self-test`：cache `SELFTEST GREEN（19 项断言）`、upload `SELFTEST GREEN（18 项断言）`，均 exit 0。

### 自检与门禁

- `python scripts/selfcheck.py`：**GREEN**（PASS 58 / WARN 0 / FAIL 0，exit 0）。
- 负向测试三例（临时副本，不污染源）：① 删 `references/cache-freshness-testing.md` 的「不得」→ §5 关键字段 FAIL；② 删 `assets/report-template.md` 的 `| R-18` 行 → §7d 矩阵同步 FAIL；③ 删 `SKILL.md` R-17 规则行里的「不得」→ §7e 例外声明 FAIL。三例均按预期转 FAIL。
- 同步全局 `C:\Users\摩羯座\.agents\skills\project-tester` 并 `diff -r`（排除 `.git`/`.workbuddy-ai`）0 差异；git commit + push 到 `https://github.com/Soren-Blade/project-tester.git`。

### 提案处置

- 采纳：dogfood 的「缓存头策略 ↔ 双会话串号」组合检查、「`Vary: Authorization` 缺失」与「purge 未鉴权」判据，「原始文件名 `join` 落盘」与「webroot 落点」判据，已写入两本手册与两份矩阵模板。
- 采纳：两个审计脚本读 JSON 清单统一 `encoding="utf-8-sig"`，容忍 Windows 写出的 BOM；`upload-audit.py` 的 UA-05/UA-08 从「`os.path.join` + 原始文件名」扩展到任意 `join/resolve`，覆盖 Express 写法（首轮 dogfood 实测漏检后修正）。
- 待评估：把「缓存键 × 身份 × tenant × locale」做成自动生成的双会话矩阵——需先定义 provider 无关的请求夹具格式。
- 待评估：上传解码重编码的证据自动化（探测 sharp/ImageMagick + 对比输出像素与元数据）——依赖本机图形库，本轮只给命令与判据。
- 待核实：Cloudflare 之外（Akamai / Fastly / CloudFront）的缓存欺骗缓解差异，需按厂商文档逐家核对，不把 Armor 判据当通用规范。

---

## [v1.10.0] — 2026-11-14 · 每日升级 #11

**主题**：从「接口、时间、恢复都正确」扩展到「**钱算得对 · 账记平衡 · 消息只达一次**」——金额/账务正确性与异步消息/Webhook 交付可靠性。一个接口全绿、时间也对、备份可恢复的系统，仍然会在 `0.1+0.2`、`2.675`、JPY×100、100 分 3 份、重复扣款、退款超退、签名不覆盖时间戳、同 `event_id` 发两次货、重试写死 1 秒、消息丢了不进 DLQ 上成片出错；这类缺陷不是「边界没测」，是「金额最小单位与交付语义没有可证伪判据」。新增 **R-15 金额与账务正确性**、**R-16 异步消息 / Webhook 交付可靠性** 与六份文件（2 手册 + 2 矩阵模板 + 2 零依赖脚本），蒸馏底座为 ISO 4217 minor unit / IEEE 754 / Fowler Money 模式 / 最大余额法 / 复式记账 / Standard Webhooks / Stripe / GitHub / CloudEvents / Kafka / SQS / AWS 退避抖动 / OWASP API7。按每日升级序列记为 #11。

**遵循上轮建议**：未重写已覆盖的 14 个主题与五阶段、四层模型、路由闭环，以 **New 为主 + Enhance 为辅**；四层模型与五阶段流程**未改语义**，只升 MINOR。上轮遗留「AUTH/S/F 三张卡做成可执行 adapter」继续**待评估**（本轮聚焦金额与交付）；「AI 变异杀伤跨语言自动跑数」仍受变异工具 JSON schema 未定阻塞，顺延。每轮至少一条可证伪规则 → 本轮引入 **R-15 / R-16**，并做了**三例负向测试**（临时副本分别删 R-15 手册「不得」、删报告矩阵 R-16 行、删 SKILL.md R-15 规则行，确认 `selfcheck.py` 对应检查确实 FAIL）。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 分类 | 对象 | 处置 |
|---|---|---|
| New | `references/money-correctness-testing.md`、`assets/money-matrix-template.md`、`scripts/money-audit.py` | 新增 R-15 能力：ISO 4217 exponent（0/2/3/4 位）、IEEE 754 十进制陷阱、四种舍入模式与所在层、最大余额法分摊守恒、复式借贷不变量与只追加分录、M-01~M-24 六面、MO-01~MO-09 反模式扫描、LG-00~LG-06 账本负向、渠道对账三步法 |
| New | `references/webhook-delivery-testing.md`、`assets/webhook-delivery-matrix-template.md`、`scripts/webhook-audit.py` | 新增 R-16 能力：at-least-once / at-most-once / exactly-once 语义、Standard/Stripe/GitHub 签名与原始 body、时间戳容忍窗、`event_id` 去重与并发、指数退避 + jitter、重启续投、乱序状态机、DLQ 与渠道对账、D-01~D-22 六面、WH-01~WH-11 审计 |
| Enhance | `SKILL.md`（description 触发词、v1.10 增量段、阶段 1 金额面/交付面、阶段 3 两条专项、判 bug 第 11 条、十六条规则表、阶段 4 自检、索引） | 只增量，不改五阶段与四层模型 |
| Enhance | `references/dissect.md` §6/§7/§8、`references/quality-gates.md` §3/§8、`assets/report-template.md` 证据矩阵 | 金额/交付两面路由与攻击面、结论作废判据、16 行矩阵 |
| Enhance | `scripts/selfcheck.py` §5/§7f、`README.md`、`CHANGELOG.md`、`memory/global-lessons.md` | 登记 4 个新文件字段、2 个新脚本门禁、徽章/结构/速查/设计点/版本史、教训与提案 |
| Existing | 其余 32 份手册与 21 份模板 | 不重复造，仅在路由/交叉项里引用 |

### 蒸馏来源（深度蒸馏，URL 全记录）

- SIX ISO 4217 `list-one.xml`（货币 minor unit 权威表）：https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml
- Stripe Currencies（零小数币种与特例口径）：https://docs.stripe.com/currencies
- Stripe Idempotent requests（`Idempotency-Key` ≤255 字符、24h 清理、仅 POST）：https://docs.stripe.com/api/idempotent_requests
- Python `decimal` / floating-point 教程（`round(2.675, 2) == 2.67` 与 HALF_EVEN）：https://docs.python.org/3/tutorial/floatingpoint.html
- PostgreSQL 17 §8.1 Numeric Types（精确十进制、舍入模式）：https://www.postgresql.org/docs/17/datatype-numeric.html
- MySQL 8.4 Fixed-Point Types（DECIMAL 精确存储）：https://dev.mysql.com/doc/refman/8.4/en/fixed-point-types.html
- Java `RoundingMode`（HALF_UP / HALF_EVEN / DOWN 语义）：https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/math/RoundingMode.html
- HMRC VATREC12010 / 12030（逐行舍入与 0.004p/0.005p 示例）：https://www.gov.uk/hmrc-internal-manuals/vat-records/vatrec12010
- OpenStax 复式记账（借贷相等与分录只追加）：https://openstax.org/books/principles-accounting/pages/3-1-describe-principles-of-accounting
- moneyphp（`allocate` 余数分配 334/333/333）：https://moneyphp.org/
- dinero.js（不可变 Money、amount+currency 成对）：https://dinerojs.com/
- Largest remainder method：https://en.wikipedia.org/wiki/Largest_remainder_method
- Standard Webhooks 规范（签 `id.timestamp.body`、`whsec_` base64、多签名）：https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md
- Stripe Webhooks（默认 300 秒容差、原始 body、勿设 0）：https://docs.stripe.com/webhooks
- GitHub Validating webhook deliveries（`X-Hub-Signature-256` hex、`X-GitHub-Delivery`）：https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
- CloudEvents 核心规范（只规定 `source`+`id` 去重，不承诺投递语义）：https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md
- Kafka Producer Configs（幂等生产者、仅 partition 内有序）：https://kafka.apache.org/documentation/#producerconfigs
- Amazon SQS 标准队列（at-least-once、可能乱序）/ FIFO 去重 5 分钟 / DLQ：https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html
- AWS Builders' Library — Timeouts, retries, and backoff with jitter（加大 jitter，不是去掉退避）：https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
- OWASP API Security Top 10 2023 API7（SSRF，webhook 回调地址校验）：https://owasp.org/API-Security/editions/2023/en/0xa7-server-side-request-forgery/

### 口径诚实

- `money-audit.py` **不联网、不代填**：只读本地源码/JSON，不连接支付渠道、不调用汇率服务；`ledger` 只验证「给出的分录是否平衡」，**不证明账本与渠道对账单一致**，也不证明符合当地财务/税务合规。静态扫描命中只是「可疑写法」，**未命中不证明金额正确**——浮点错误在特定输入才出现，必须跑用例。
- `webhook-audit.py` 的 `verify` 只证明「给定 payload+secret 能复算出该签名」，**不证明密钥真实、不证明服务端校验、不证明渠道侧投递成功**；`check` 对 `deliveries.json` 做规则审计，数据由测试者提供，可伪造；`--fail-on-gap` 只把「发现的缺口」变成非零退出码，不把「没发现」变成「没问题」。
- ISO 指数以 SIX 表为准，但 Stripe 等渠道有**特例**：ISK/UGX 历史上按两位表示（5 ISK 传 `amount=500`）；HUF/TWD 仅 payout 视为零小数且金额须被 100 整除；其余零小数币种直接传（500 JPY ⇒ `amount=500`，不要 ×100）。特例已写进手册，**不得**把「渠道按最小单位」当成「所有货币都 ×100」。
- Standard Webhooks 规范**只要求**时间戳在可接受容差内，**未给具体秒数**；±5 分钟是常见约定，Stripe 官方库默认 300 秒且明确说不要设 0。手册以「被测实现的实际配置」为准，要求证据写清数值，不把「常见约定」冒充「规范规定」。
- R-15 不认「界面显示 2.68」「账本内部平衡」「单笔用例通过」；R-16 不认「验签函数存在」「回调返回 200」「配了重试」。

### 深度实测（dogfood，模拟用户项目）

在项目外临时目录 `C:\Users\摩羯座\AppData\Local\Temp\pt-v110-dogfood\shopdemo` 建了一个零依赖 Node 商城（商品/购物车/下单/支付/退款/账本/webhook 接收端，带 18 处预埋缺陷），全程只读技能目录，按五阶段走完：

- 记忆树 69 行、run 记录 1 份、报告 1 份、证据 21 份 `<ID>.json`（含完整 request/response + `results.json` + `env.json` + `server.log` + `MANIFEST.sha256.json`，22 条 sha256 校验 0 mismatch）；
- 执行 21 个检查点：**PASS 3 / FAIL 18 / BLOCKED 0**；缺陷 S1 15 / S2 3 / S3 0；质量状态 **FAIL**、发布建议 **No-Go**（15 个未闭环 S1，按 `quality-gates.md` §3 无条件 No-Go）；
- 复跑：`node tools/dogfood-tests.mjs`（自起停，约 4s）；服务已停，端口 3419 无监听；
- 典型命中：3×0.10 合计 `0.30000000000000004`；JPY 1000 记成 100000；客户端 `unitPrice=0.01` 覆盖目录价；同幂等键两笔支付；退款 200 超退；账本 9 条单边、Σ=840.28；混币种直接相加；`qty=-2` 订单 -20；10.999 入账 10.99 而账本 10.999；重启后账本 19→0；`ts=now-3600` 与「只签 body 改 ts」均 200；同 `webhook-id` 两事件两账本；`refund` 先于 `capture` 落退款；handler 失败留残留、replay 后翻倍；`attempts` 不增、`dropped: no retry configured`、无 DLQ。仅 3 项通过：合法签名 200、篡改 body 401、缺签名头 401。
- **回灌**：dogfood 提出的 15 条检查已蒸馏进手册（不回写 demo 目录）——M-01 零小数币种、M-02 浮点禁令、M-03 服务端定价、M-04 支付幂等、M-05 退款上限、M-06 账本平衡、M-07 税额口径、M-08 混币种、M-09 符号/精度、M-10 持久化往返、W-01 签名覆盖 timestamp、W-02 容差边界三值、W-03 去重持久化、W-04 乱序状态机、W-05 原子与重试/DLQ 判据；其中「落盘往返（面 7）」「税额按行 vs 按订单」「混币种/数量行」「timestamp 进签名 + 容差三值」「handler 零残留」「attempt/nextRetryAt 实测」「前置事件缺失」为本轮**新增**到手册的检查点。
- Windows 实测坑（已写入 `memory/global-lessons.md`）：PowerShell 5.1 默认 GBK/UTF-16 读写会破坏 UTF-8 中文证据 → 证据用 Node `fs.writeFileSync(...,'utf8')`；`curl` 是 `Invoke-WebRequest` 别名、`--data-binary @file` 语义丢失 → 用 `curl.exe`；`Stop-Process` 后 TIME_WAIT 短暂占端口 → 用 `Get-NetTCPConnection -LocalPort ... -State Listen` 判定；起服务用轮询 `/health` 代替 `Start-Sleep`；同一 body 两次签名 sha256 一致，夹具可复现。

### 自检与门禁

- `python scripts/selfcheck.py`：**GREEN**（PASS 52 / WARN 0 / FAIL 0，exit 0）。
- `python scripts/money-audit.py --self-test`：SELFTEST GREEN（16 项断言，exit 0）；`cases` 输出与手册期望一致。
- `python scripts/webhook-audit.py --self-test`：SELFTEST GREEN（12 项断言，exit 0）；`verify --scheme standard` 支持多签名。
- 负向测试三例（临时副本，不污染源）：①删 `money-correctness-testing.md` 的「不得」→ §5 FAIL；②删 `report-template.md` 的 `| R-16` 行 → §7d FAIL；③删 `SKILL.md` 的 `**R-15` 规则行 → §7c FAIL。三例均按预期转 FAIL。
- 同步全局 `C:\Users\摩羯座\.agents\skills\project-tester` 并 `diff -r`（排除 `.git`/`.workbuddy-ai`）0 差异；git commit + push 到 `https://github.com/Soren-Blade/project-tester.git`。

### 提案处置

- 采纳：dogfood 的「持久化往返」「税额口径」「混币种/数量」「签名覆盖 timestamp + 容差三值」「handler 原子性」「attempt/DLQ 实测」「前置事件缺失」七项检查，已写入两本手册与本轮矩阵模板。
- 采纳：`webhook-audit.py` 的 `verify` 增加 `--scheme` 区分 standard/stripe，避免把两种 `whsec_` 处理混为一谈。
- 待评估：金额四舍五入的「税务辖区矩阵」（按国家/税种给出权威舍入规则）——需要逐辖区读官方文档，本轮只给 HMRC 示例，不冒充全球口径。
- 暂不采纳：把 `money-audit.py` 扩展成「自动对渠道账单」——需要真实 API 凭据与网络，违反零依赖/不联网边界，保持离线审计定位。

---

## [v1.9.0] — 2026-11-14 · 每日升级 #10

**主题**：从「正常路径与数据形态的正确」扩展到「**时间维度正确 · 灾难后可恢复**」——时间/时区正确性与备份/恢复可验证性。同一套功能全绿的 API，只要按 UTC 日过滤、每日任务固定 `+24h`、`exp` 无时区、备份只备一个文件、恢复按字符串挑「最新」，就会在跨时区用户、DST 切换日、真实故障恢复时成片出错；这类缺陷不是「边界没测」，是「时间语义与恢复目标没有可证伪判据」。新增 **R-13 时间与时区正确性**、**R-14 备份与恢复可验证性** 与六份文件（2 手册 + 2 矩阵/演练模板 + 2 零依赖脚本），蒸馏底座为 IANA tzdb 2026f / RFC 3339 / cronie crontab(5) / PostgreSQL 17 §8.5 / MySQL 8.4 §13.2.2 / SQLite Date Functions / NIST SP 800-34 Rev.1 / pg_verifybackup / restic / Borg / GDPR Art.17。按每日升级序列记为 #10。

**遵循上轮建议**：未重写已覆盖的 12 个主题（五阶段、四层模型、可观测、韧性、数据、协议、供应链、i18n、多租户、契约、隐私、有效性、无障碍、跨端、ROI、证据链、特性开关、TDM、认证会话），以 **New 为主 + Enhance 为辅**；四层模型与五阶段流程**未改语义**，只升 MINOR。上轮遗留的「AUTH/S/F 三张卡做成可执行 adapter」继续保持**待评估**（本轮聚焦时间与恢复，未动 auth 手册）；「AI 变异杀伤跨语言自动跑数」仍受变异工具 JSON schema 未定阻塞，顺延。每轮至少一条可证伪规则 → 本轮引入 **R-13 / R-14**，并做了**负向测试**（临时副本分别删 R-13 定义行 / 删报告矩阵行 / 删手册「不得」，确认 `selfcheck.py` 对应检查确实 FAIL）。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 分类 | 对象 | 处置 |
|---|---|---|
| New | `references/time-correctness-testing.md`、`assets/time-matrix-template.md`、`scripts/time-audit.py` | 新增 R-13 能力：存/算/显示三层口径、T-01~T-12 反模式（含 tzdata 漂移与配置面）、DST gap/fold 实跑、TTL 三值边界、wall vs monotonic、RFC 3339、PG/MySQL/SQLite 时间类型差异 |
| New | `references/backup-recovery-testing.md`、`assets/restore-drill-template.md`、`scripts/restore-audit.py` | 新增 R-14 能力：RPO/RTO 实测、3-2-1、恢复演练八步、RST-01~RST-11 双清单对账、强校验真读数据、PITR 丢失窗口、删除权/多租户交叉 |
| Enhance | `SKILL.md`（description 触发词、v1.9 增量段、阶段 1 时间面/恢复面、阶段 3 两条专项、判 bug 第 10 条、十四条规则表、索引） | 只增量，不改五阶段与四层模型 |
| Enhance | `references/dissect.md` §6/§8、`references/quality-gates.md` §3/§8、`assets/report-template.md` 证据矩阵、`references/tools.md` | 时间/恢复两行路由、结论作废判据、14 行矩阵、两工具与两条纪律 |
| Enhance | `scripts/selfcheck.py` §5/§7f、`README.md`、`CHANGELOG.md`、`memory/global-lessons.md` | 登记 4 个新文件字段、2 个新脚本门禁、徽章/结构/速查/设计点/版本史、教训与提案 |
| Existing | 其余 24 份专项手册与 19 份模板 | 不重复造，仅在路由/交叉项里引用 |

### 蒸馏来源（深度蒸馏，URL 全记录）

- IANA Time Zone Database 2026f：https://data.iana.org/time-zones/releases/
- RFC 3339（Date and Time on the Internet: Timestamps）：https://www.rfc-editor.org/rfc/rfc3339
- cronie `crontab(5)`（gap 从不匹配、fold 跑两次的原文）：https://cronie.org/
- PostgreSQL 17 §8.5 Date/Time Types：https://www.postgresql.org/docs/17/datatype-datetime.html
- MySQL 8.4 §13.2.2 Date and Time Data Types：https://dev.mysql.com/doc/refman/8.4/en/datetime.html
- SQLite Date And Time Functions：https://sqlite.org/lang_datefunc.html
- NIST SP 800-34 Rev.1（RPO/RTO 的业务连续性口径）：https://csrc.nist.gov/pubs/sp/800/34/r1/upd1/final
- PostgreSQL `pg_verifybackup`：https://www.postgresql.org/docs/17/app-pgverifybackup.html
- restic `check` / `--read-data`：https://restic.readthedocs.io/en/stable/045_working_with_repos.html
- Borg `check` / `--verify-data`：https://borgbackup.readthedocs.io/en/stable/usage/check.html
- Playwright Clock：https://playwright.dev/docs/clock
- GDPR Art.17（删除权与备份保留期）：https://gdpr-info.eu/art-17-gdpr/

### 口径诚实

- 两个新脚本都**不联网、不代填**：`time-audit.py` 只读本地文件与系统时区库，不查 IANA 更新、不请求被测服务；`restore-audit.py` 只读两份本地 JSON，不连接数据库、不校验真实文件字节。
- `time-audit.py` 的 `dst` 依赖 zoneinfo + tzdata；缺失时**明确报错并给安装提示，绝不伪造转换结果**。本机实算使用 tzdata 2026.6，`tzdata 2026.6 ↔ IANA 2026f` 的映射未独立核实（已列入手册不确定项）。静态扫描命中只是「可疑写法」，**未命中不证明时间正确**；调度器 gap/fold 行为必须实测，systemd timer / Quartz 的行为未读原文证实，手册保留【不确定】。
- `restore-audit.py` 只证明「两份清单一致」，**不证明恢复出的系统业务可用**（索引/权限/密钥/扩展/外部依赖未覆盖）；清单本身可伪造；没有 `files`/`tables` 数组时只报盲区告警，**不当作通过**。
- R-13 不认「能解析时间」「服务器跑 UTC」「用了某个库」；R-14 不认「备份任务成功」「结构校验通过」「有备份但没恢复过」。

### 深度实测（dogfood，模拟用户项目）

用 v1.8.0 五阶段在项目外搭零依赖 Node 模拟项目 `timedemo`（事件时区过滤、DST 每日任务、令牌过期、backup/restore），全程真实命令证据（30 个证据文件、记忆树 37 行、运行记录/报告/教训齐备），结论 **No-Go**：**10 个缺陷（2×S1 / 5×S2 / 3×S3）+ 9 条盲区**。

- S1：令牌无签名可伪造（伪造 admin → 200）；`exp` 无偏移，同一令牌在 Shanghai/UTC 多活 8h；restore 按字符串挑「最新」选错备份（09:00+08 vs 02:00Z），旧备份静默覆盖较新数据且 exit 0。
- S2：事件按 UTC 日过滤（`2026-11-13` 返回 id2/id3，`2026-11-15` 返回 0 条）；每日任务固定 `+24h`，NY 春季 02:30→03:30 后永久漂移；backup 只备 `db.json`、`checksums:{}` 却 `verified:true`、`createdAt` 无时区；restore 不校验（manifest 99 行 vs db 3 行仍 `ok:true`）；非法 `at` 入库 201 → 列表 500 裸堆栈含绝对路径。
- 盲区：旧版 i18n 只管显示/往返、不管区间过滤与调度；调度器无 DST 规则；`data-integrity` 全文无「备份/恢复」；时间戳表示、时钟回拨/单调时钟、5xx 错误体泄露均无规则。
- 反哺：本轮新手册的 TZ-1~TZ-12 / BK-1~BK-16 已能覆盖上述缺陷（映射见 `.workbuddy-ai/dogfood/v1.9.0-dogfood.md` 22 条检查项）；「5xx 响应体不得含堆栈/绝对路径」作为**下一轮**安全手册提案写入 global-lessons，不在本轮扩 scope。

### 自检与门禁

- `python scripts/selfcheck.py` → **PASS 46 / WARN 0 / FAIL 0 / GREEN**；14 条规则双向同步、14 行报告矩阵、14 条例外声明、32 份手册全索引、24 份专项路由闭环、7 个脚本门禁全过。
- 6 个脚本 `--self-test` 全部 exit 0：evidence-audit / device-matrix / test-data-gen / jwt-audit / time-audit（12 断言）/ restore-audit（12 断言）。
- 负向测试三例：删 R-13 定义行 → §7c 双向同步 FAIL；删报告矩阵 R-13 行 → §7d FAIL；删时间手册「不得」→ §5 字段 FAIL；复原后全部 PASS。
- 文件数 59 → 65（references 30→32、assets 19→21、scripts 5→7）；`diff -r` 源目录与全局安装目录零差异。
- 提交：`feat(v1.9): 每日升级 #10 时间维度与灾难恢复`；push 到 `https://github.com/Soren-Blade/project-tester`。

### 提案处置

- 采纳：dogfood 提出的「备份必须做一次真实恢复演练」「时间过滤要用双时区对照」「DST 任务必须实跑执行次数」已分别落入 R-14/R-13 证据要求；新增 T-11（tzdata 漂移）与「强校验必须真读数据」两节。
- 顺延：5xx 错误体泄露 → 下一轮安全手册；systemd timer / Quartz 的 gap/fold 原文核实；`tzdata 2026.6 ↔ IANA 2026f` 映射；变异杀伤贡献自动跑数；AUTH/S/F adapter。
- 回写：automation memory 记录本轮结论与下轮建议（避免重复主题，优先把 5xx 错误体与调度器原文核实做掉）。

---

## [v1.8.0] — 2026-11-14 · 每日升级 #9

**主题**：从「功能与数据的正确」扩展到「**身份不可冒充 · 会话可终止 · 令牌不可伪造**」——身份认证 / 会话 / 令牌安全。同一套功能全绿的 API，只要 `alg:none` 被接受、过期 `exp` 被忽略、登出后旧令牌仍可用，攻击者就能直接变成管理员；这类缺陷不是「边界没测」，是「认证的可信前提没测」。新增 **R-12 身份与会话不可冒充** 与三份文件（手册 + 矩阵模板 + 零依赖 `jwt-audit.py`），蒸馏底座为 ASVS 5.0.0 / RFC 8725（BCP 225）/ RFC 9700（BCP 240）/ OWASP 认证·会话·密码存储 Cheat Sheet / NIST SP 800-63B-4 / WebAuthn L3。注：与 #1~#8 同属每日升级自动化序列，按轮次记为 #9。

**遵循上轮建议**：未重写已覆盖主题（五阶段、四层模型、可观测、韧性、数据、协议、供应链、i18n、多租户、契约、隐私、有效性、无障碍、跨端、ROI、证据链、特性开关、TDM），以 **New 为主 + Enhance 为辅**；四层模型与五阶段流程**未改语义**（按 `self-evolution.md` §7 只升 MINOR）；每轮至少一条可证伪规则 → 本轮引入 **R-12**；本轮做了**负向测试**（临时副本分别删 R-12 定义行 / 删报告矩阵行 / 删手册「不得」，确认 `selfcheck.py` §7c/§7d/§5 确实 FAIL）。

### 治理分类（Existing / Enhance / Merge / Match / New）

| 动作 | 对象 |
|---|---|
| **New** | `references/auth-session-testing.md`、`assets/auth-matrix-template.md`、`scripts/jwt-audit.py` |
| **Enhance** | `SKILL.md`（version 1.8.0、description 触发词、v1.8 增量说明与叠加项、阶段1 身份/会话面、R-12 定义行、参考索引、对账边界）、`README.md`（徽章 / 问题表 +1 / 59 文件结构 / 速查 +1 / 设计要点 R-12 + 身份不可冒充 / 版本史）、`CHANGELOG.md`（本条目）、`references/dissect.md`（§6 身份/会话面 + §8 路由）、`references/quality-gates.md`（§3 R-12 作废行 + §8 十二条）、`assets/report-template.md`（R-12 行 + 十二行矩阵 + 边界）、`scripts/selfcheck.py`（§5 两文件字段 + §7f jwt-audit 门禁）、`references/tools.md`（JWT/OAuth 工具行 + 纪律 15）、`memory/global-lessons.md`（身份/会话/令牌教训组 + 提案） |

### 蒸馏来源（深度蒸馏，URL 全记录）

- OWASP ASVS 5.0.0（tag `v5.0.0_release`，2025-05-30；`latest` 是自动重建的 bleeding edge，不作为版本依据）：6.2.1 密码≥8（推荐 15）、6.2.5 无组成规则、6.2.10 不强制周期改密、6.3.8 枚举三列不可区分、6.5.1 OTP 一次性、7.2.3 引用令牌≥128bit CSPRNG、7.2.4 认证时换新令牌、7.3.1 服务端强制空闲/绝对超时、7.4.1 登出失效、7.5.1 敏感操作再认证、9.1.2 算法 allowlist 禁 none、9.2.1 校验 nbf/exp、10.4.1 redirect_uri 精确匹配、10.4.2 code 一次性、10.4.6 PKCE 拒 plain → `references/auth-session-testing.md` §2~§4、R-12
- RFC 8725 JWT BCP（BCP 225，2020-02）：算法白名单、拒绝 `none`、`kid`/`jku`/`x5u` 属不可信头；**注意**：`x5c`/`jwk` 注入不是 RFC 8725 明文条款，手册按「同类风险」标注而非冒充条款 → §2 AUTH-9/AUTH-10
- RFC 9700 OAuth 2.0 Security BCP（BCP 240，2025-01，取代 oauth-security-topics draft）：PKCE 必须、redirect_uri 精确匹配、code 一次性与短 TTL、refresh 轮换与 sender-constrained → §4 F11
- OWASP Password Storage Cheat Sheet：Argon2id 最低 m=19MiB,t=2,p=1；bcrypt cost≥10 且 72 字节上限；scrypt N=2^17/r=8/p=1；PBKDF2-SHA256 600k / SHA512 220k；hash <1s → §4 F6
- OWASP Authentication / Session Management Cheat Sheet：会话 ID≥64bit（自建≥128，建议≥160）、空闲 2–5min（高价值）/15–30min（低风险）、绝对 4–8h、SameSite 优先 Strict/Lax、None 必配 Secure、`__Host-` 三条件、登出撤销全部同逻辑会话、枚举统一文案、按账户限速 → §1/§3
- NIST SP 800-63B-4（Final 2025-07）：AAL1 overall ≤30 天、AAL2 ≤24h + inactivity ≤1h、单因子≥15 / MFA 下≥8 / 最大≥64、不得截断、blocklist 全串比对、OOB 10 分钟、邮件不得作 OOB → §4 F4/F6/F10
- WebAuthn L3（W3C Rec 2026-08-25）：RP ID/origin 校验、challenge 一次性 → §4 F10 附注（页面截断处标「推论」）
- 工具链（GitHub）：`jwt_tool`（alg none `-X a`、JWKS 注入 `-X i`、kid 注入 `-I -hc kid`）、`hashcat -m 16500`（module_16500.c 仅 HS*）、`oauth2c`（PKCE/PAR/DPoP/JARM）、nuclei 官方 `cookies-without-httponly/-secure` 模板、ZAP/Autorize 低权重放 → `references/tools.md` §2、`§6` 边界

### 口径诚实

- `scripts/jwt-audit.py` 只做**离线结构审计**与 HMAC 签名匹配；**不联网、不代填、不冒充**服务端已校验。结构可疑 ≠ 服务端接受；未命中字典 ≠ 密钥强（只能证「未在 N 条字典中命中」）。
- `--self-test` 只证明脚本自身解析/判定逻辑可用，**不证明**被测系统认证安全。
- ASVS 5.0 改写为「动作 + 判据」而非抄条目；`latest` tag 不作为版本号；NIST 800-63B 未给具体限速次数，手册不编造「100 次」。
- **R-12 不认「登录成功 / 令牌可解码 / Cookie 有 HttpOnly」**；只有黑盒时密码存储写「未验证（需源码）」，只有部分证据时降级「待确认」，无认证系统写「不适用：无身份与会话维度」。

### 深度实测（dogfood，模拟用户项目）

- 在项目外搭建含种缺陷的模拟项目 `authdemo`（零依赖 Node 笔记 API + 前端，README 声称 9 项安全措施而实现 0 项成立），用新手册 AUTH-1~12 / S1~S9 / F1~F12 实际执行。
- 结果：**30 项检查 = FAIL 24 / PASS 4 / 观察 2**，18 个缺陷（S0 2 个：`alg:none` 与 `secret123` 均可伪造 admin；S1 10 个：exp/nbf/aud/iss 不校验、登出与重置不撤销、refresh 不轮换、reset_token=base64(email)、`password_hash` 外泄、无盐 SHA-256；S2 6 个：枚举、无限速、弱密码、BOLA、Cookie 缺属性/localStorage/innerHTML、POST 笔记 404）。
- 记忆树：`.test-memory/tree.md`（<100 行）+ `runs/2026-11-14-1.*`（结果 JSON / HTTP 原文 / 令牌样本 / jwt-audit JSON）+ `reports/2026-11-14-auth-report.md`（PASS/FAIL、No-Go、R-12 七类证据、R-1~R-12 全矩阵、未测/不适用明细）。验证「宣称 vs 实际」「不适用不冒充」「观察项不写成漏洞」三条门禁真实可执行。
- 实测暴露并已修正的工具问题：`--now` 只属 `decode`（`verify` 无此参数）；Windows 控制台中文经管道会乱码、`Out-File` 会写 BOM 破坏 JSON → 用 `PYTHONUTF8=1` + `cmd /c "python ... > out.json"` 并 `json.load` 回读校验（已写入 global-lessons）。

### 自检与门禁

- `scripts/selfcheck.py`：源与全局安装均 **PASS 40 / WARN 0 / FAIL 0 / GREEN**（规则 11→12；§7c 双向同步、§7d 逐行矩阵、§7e 例外声明、§7f jwt-audit 门禁全过；路由闭环 22 份专项）
- `scripts/jwt-audit.py --self-test` 退出码 0（8 项断言，`SELFTEST GREEN`）；`evidence-audit.py` / `device-matrix.py` / `test-data-gen.py --self-test` 均 0；`py_compile` OK
- **负向测试**（项目外临时副本，Python 改文件避免 PowerShell 编码破坏）：删 `SKILL.md` 的 R-12 定义行 → §7c/§7d FAIL；删 `report-template.md` 的 `| R-12 ... |` 行 → §7d FAIL；删 `auth-session-testing.md` 的「不得」→ §5 FAIL；三例 exit=1，干净副本仅剩（未写本条目时的）CHANGELOG 缺口
- 文件数 56 → 59（references 29→30、assets 18→19、scripts 4→5），`diff -r` 源与全局安装零差异

### 提案处置

- 上轮顺延「AI 生成用例变异杀伤贡献跨语言自动跑数」仍保留（理由：变异工具输出 schema 未定，不硬编码某一家 JSON；TDM `--seed` 已是可复现底座）。
- 新增待评估提案：「AUTH/S/F 三张卡做成可执行 adapter（统一 token-provider 接口）」，暂不落地，先确认接口不绑定框架且不替代人工判据。

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
