# 国际化与本地化测试（阶段 3 · 横向叠加）

> 蒸馏自 Microsoft Learn《How to perform internationalization testing / Test cases for locale awareness》、W3C International《Structural markup and right-to-left text in HTML》（`dir` / `dir="auto"` / `dirname` / logical properties）、Unicode CLDR 与 ICU MessageFormat 复数规则、`frontend-dev` 的 RTL/字体/动态视口纪律、`fullstack-dev` 的日期时区与跨边界错误映射。来源 URL 见 `CHANGELOG.md` v1.2.0。
> 定位：测的不是「翻译得对不对」（那是语言审校），而是**「换一套 locale、文字、书写方向、时区后，系统还正确吗」**。伪本地化是低成本探针，不是翻译验收。

## 0. 适用边界与降级

| 触发 | 叠加本手册 | 不适用 |
|---|---|---|
| 有 UI 文案 / 多语言资源 / locale 切换 / 日期货币格式 / 用户输入姓名地址 | 是 | 完全无文本与格式化输出的纯计算库 → 写「不适用」 |
| 面向多地区、含时区或 DST、含搜索排序 | 是 | 单 locale 且无外部输入 → 只做 §3 的编码与时区最小检查 |
| 用户禁止改动环境、无伪本地化资源 | 降级为**静态审查**（§7），报告中写「未做伪本地化运行验证」，**不得**判 Pass | — |

**最重要的一条诚实边界**：Microsoft 原文明确 `pseudolocalization "can never catch all issues"`——它擅长抓截断、拼接、未暴露给本地化的字符串，抓不到语义、文化、真实字体渲染问题。结论只写「本次伪本地化未发现 X 类缺陷」，不写「多语言没问题」。

## 1. locale × 维度测试矩阵（模板见 `assets/i18n-matrix-template.md`）

选代表 locale，而不是穷举：

| 代表 locale | 它专门负责暴露什么 |
|---|---|
| `en-US` → `de-DE` | 文本扩展（德语更长）、句子结构、日期 `MM/DD` vs `DD.MM`、数字 `1,234.5` vs `1.234,5` |
| `ar-SA` / `he-IL` | RTL、UI 镜像、双向文本、标点位置、表单输入起点 |
| `tr-TR` | 大小写与排序：dotted/dotless `I`（`I`↔`ı`、`i`↔`İ`），**不能按 Unicode 码点排序** |
| `ja-JP` / `zh-CN` | 大字集、字体回退、IME 输入、全角/半角数字、按读音 vs 笔画排序 |
| `fr-FR` / `sv-SE` / `cs-CZ` | 变音符号排序（`côte` < `coté`）、`Å` 排在 Z 之后、`CH` 作为独立字母位于 H 与 I 之间 |
| `en-US` → `en-GB` | 同语言不同区域：日期、货币、单位、纸张尺寸 |
| `hi-IN` / `th-TH` | 复杂脚本、组合字符、无空格分词、字体回退 |

每个 locale × 六个维度至少各一格，不适用的格**写明原因**，不许留空：

| 维度 | 最小测试动作 | 通过判据 |
|---|---|---|
| 显示 | 用该 locale 走完主流程 | 所有字符串正确语言、无 tofu（方框）、无截断/遮挡/溢出 |
| 格式 | 日期/时间/数字/货币/日历/单位/地址/电话 | 遵循 OS 与目标市场约定；`honors system defaults and settings` |
| 排序/比较/搜索 | 用 §4 的构造数据跑列表、搜索、大小写转换 | 按 locale collation，不按码点 |
| 输入 | IME 输入非拉丁脚本、全角数字、多语言姓名，落库再读出 | 可接收、显示、保存、读回、校验，不按单一 locale 假设解析 |
| 布局 | 不同分辨率/宽高比、200% 缩放、文本扩展后 | 自适应布局、优雅换行与截断，无横向滚动 |
| 数据互通 | 用语言 A 写入的数据，在语言 B / 不同 OS 语言下读 | 可读、preserved；跨 regional settings 的 CSV 分隔符仍正确 |

## 2. 伪本地化（pseudolocalization）四步法

1. **造资源**：用 Multilingual App Toolkit 或等价脚本把源串替换成加长、带变音、带方括号的伪串（例 `Save` → `[Şäṽéééé !!!]`），长度按德语 ~1.3~2 倍膨胀；不要真的翻译
2. **全量跑**：在通常测源语言版本的每个时点，也跑一遍伪本地化版本，功能与视觉都覆盖
3. **专门找这五类**（原文：pseudo 版比真实语言更容易发现）
   - 截断 / 遮挡 / 溢出 / 布局破坏
   - 字符串拼接（`Concatenation is never used to assemble messages`）
   - **没暴露给本地化的硬编码串**（伪串没出现的地方就是硬编码）
   - 图片里嵌文字
   - 同一串在不同上下文被复用（应拆分）
4. **伪镜像（pseudomirroring）**：面向 RTL 市场时生成 RTL 伪资源、开启 mirroring，逐项验证 UI 镜像行为

**静态前提（源码层）**：所有字符串外部化到可翻译资源；不可本地化串明确标记；给译者留 context 注释；不用拼接组装消息；图片无内嵌文字；术语清晰一致、无俚语/文化特定引用。

## 3. 格式、解析与数据互通

| # | 测试动作 | 判据 |
|---|---|---|
| F-1 | 每个 supported locale 格式化同一时间戳、同一金额、同一数字 | 符合目标市场约定；不是硬编码 `toLocaleString('en-US')` |
| F-2 | 时区 + DST 边界：跨日、跨月、夏令时切换前后各取一值 | 存储用 UTC/neutral 表示；显示按用户时区；往返不漂移 |
| F-3 | 日历差异（非公历）、周起始日、12/24 小时制 | 与 locale 一致 |
| F-4 | 全角 vs 半角数字、千分位分隔符、小数点为逗号 | 输入解析与校验都能接受并能正确 round-trip |
| F-5 | 含区域格式数据的文件（CSV/导出）在不同 regional settings 下读写 | delimiters vary regionally 仍互通；优先 neutral format |
| F-6 | 用一种 app language 写入的数据，在所有其他 app languages + supported OS languages 中读 | 可读且 preserved（原文：all app languages × all supported OS languages × data in any language） |
| F-7 | localized OS objects：特殊文件夹名、账户名、registry 项 | 应用不假定英文路径 |
| F-8 | 第三方文件加入不同语言/脚本后 | 兼容、限制被优雅处理、数据不丢 |

## 4. 排序、大小写与搜索（最容易按英文想当然）

- **不要按 Unicode code point 值判断排序**——原文明确 Turkish 的 dotted/dotless I 顺序与码点顺序不同
- Turkish 大小写：`I`(U+0049)↔`ı`(U+0131)、`i`(U+0069)↔`İ`(U+0130)；大小写转换时点不增不减
- 德语 `ä`：电话簿按 `ae`，多数其他场景排在 `a` 之后（context-dependent）
- 法语按词内 accents 出现顺序：`côte` < `coté`；立陶宛语 `Y` 排在 `J` 之前；瑞典/北欧 `Å` 在 `Z` 之后
- 中文：按用户选择的读音或笔画排序，结果应随之变化；构造含 `䠀 㠀 䀀 䘀 𠀀` 等字符的数据
- 复数与选择：ICU MessageFormat / CLDR plural rules，`one/few/many/other` 不要硬编码英文两分支；数字转词、text-to-speech、case mapping 一并验证
- 搜索结果里的高亮、摘要、命中数、缓存片段也要按 locale 核对（与 `references/multi-tenancy-testing.md` §4 的 search 隔离联动）

## 5. RTL 与双向文本（W3C 硬规则，静态可查 + 渲染必验）

| 规则 | 可验证检查 |
|---|---|
| base direction 用 HTML `dir`，**绝不用 CSS 设置** | 禁用 CSS 后方向信息仍在 markup 中；无 `direction: rtl` 承担语义 |
| `lang` ≠ 方向 | `<html lang="ar">` 不能替代 `<html lang="ar" dir="rtl">` |
| 整体 RTL 在 `<html dir="rtl">` | 段落右对齐、双向文本流、标点位置、表格列 RTL、表单输入从右开始、`alt`/`title` 方向、CSS 自动镜像、overflow 方向 —— 共 8 项逐项看渲染 |
| 块级元素只在**需要改变方向**时加 `dir` | 无冗余 `dir`；LTR 引文用 `dir="ltr"` |
| 布局用 logical properties | `start/end`、`margin-inline-start`、`text-align: start`，不用固定 `left/right` 做本地化布局 |
| 运行时插入文本、论坛/聊天块、`<input>` 用 `dir="auto"` | 由第一个**强方向性字符**决定；检查 corner case（以 RTL 字符开头的 LTR 句子被误判） |
| `<textarea>` / `<pre>` 用 `dir="auto"` | 每个段落独立判方向；纯数字行对齐在目标浏览器单独验 |
| 用户名/标签用 `<bdi>` 隔离 | 方向探测跳过 `bdi` 内文本；去掉 `bdi` 对比方向是否变化 |
| 表单用 `dirname` 提交方向 | 请求体出现 `commentdir=rtl` / `ltr`，服务端保存并在后续渲染复用 |
| 边界控制符 | RTL 标题以 Latin acronym 开头加 `&rlm;`；反之 `&lrm;` |
| 表格整体位置 | 用 `<div dir="ltr">` 包裹，不要用 CSS `text-align` 修表格对齐 |
| 滚动条 | 属于 browser chrome，**不作为 RTL 缺陷** |

UI 镜像必须**真实渲染**验证，`frontend-testing.md` §2.1 的运行时纪律同样适用：静态 grep 出 `dir` 属性不等于界面已正确镜像。

## 6. 文本、编码、字体与输入

- 全链路 UTF-8（原文：`Unicode is usually the best option for text data`）；legacy 编码额外验证
- 构造覆盖 broad range of characters 的数据：Unicode、sort、casing、emoji、零宽空格、组合字符、多语言姓名、数据库内容、文件内容
- **tofu（字形缺失方框）是缺陷**：检查 font selection + font fallback，UI 语言与用户数据用各自合适的字体
- IME：任意键盘 / 输入法都能输入、显示、保存非拉丁脚本；拼写检查/预测/词典按语言有支持
- `prefers-reduced-motion`、动态视口、窄屏在 RTL 布局下重复验证（不是只在英文下过一遍）
- 与 `references/frontend-testing.md` §6 表单专项联动：RTL、零宽空格、粘贴富文本、日期/时区跨日边界

## 7. 静态审查清单（无浏览器 / 跑不起来时）

- [ ] 字符串全部外部化；无 `"Hello " + name` 式拼接；无图片内嵌文字
- [ ] 有 locale 回退链与默认语言；缺失 key 不显示 raw key 或空白
- [ ] 时间以 UTC/带偏移存储，只在展示层格式化；无 `new Date(str)` 按本地假设解析
- [ ] URL/文件名/标识符不依赖 locale；大小写转换不用 `toUpperCase()` 处理土耳其语用户名
- [ ] 排序与搜索调用带 locale 的 collator，不用默认 `sort()` 比码点
- [ ] `lang` 与 `dir` 成对存在；CSS 用 logical properties
- [ ] 错误文案也走资源文件，且随 locale 变化（与 `frontend-testing.md` §5 错误映射联动）
- [ ] 数字/金额格式来自格式化库，不是字符串模板拼 `,`/`.`

## 8. 降级与结论写法

无伪本地化资源、无浏览器自动化时：只做 §7 静态审查 + §3 F-2/F-4 的 API 层格式往返，报告写「**未做伪本地化与 RTL 运行时渲染验证**」，相关矩阵格标 `BLOCKED`／`待确认`，不填 Pass。

**R-3/R-4 之外的一致性**：本地化结论同样不许用「没报错」冒充「没问题」；`SKILL.md` 的证据纪律在本手册全量适用。

## 9. 记录格式与分工

```
locale 矩阵：de-DE✅ ar-SA🐛(表格未镜像) tr-TR◐(仅静态) ja-JP⬜
伪本地化：资源生成✅ 截断 3 处🐛 硬编码串 2 处🐛 拼接 1 处🐛
RTL：<html dir=rtl>✅ dirname 缺失🐛 textarea 方向◐
格式：F-2 DST 边界🐛（相差 1h）｜F-5 CSV 分隔符✅
局限：未做真实语言审校；未做屏幕阅读器 RTL 验证
```

| 主题 | 去哪 |
|---|---|
| 五态、a11y、CWV、运行时渲染纪律 | `references/frontend-testing.md` |
| 跨边界错误码 → 人话 | `references/frontend-testing.md` §5、`references/fullstack-integration.md` §3 |
| 搜索结果的租户隔离 | `references/multi-tenancy-testing.md` §4 |
| 模板 | `assets/i18n-matrix-template.md` |
