# locale × 维度测试矩阵（i18n / L10n）

> 配合 `references/i18n-localization-testing.md` 使用。选**代表 locale**，不穷举。每格填 `✅ / 🐛 / ◐(仅静态) / ⬜(未做+原因) / N/A(原因)`，**不许留空**。
> 诚实边界：伪本地化 `can never catch all issues`；本表通过 ≠ 翻译正确、≠ 真实字体渲染无问题。

```
项目/版本：___　资源文件：___　伪本地化资源：有/无　浏览器：___
```

## 1. 主矩阵

| locale \ 维度 | 显示（无 tofu/截断） | 格式（日期/数字/货币/日历） | 排序/比较/搜索 | 输入（IME/姓名/落库读回） | 布局（文本扩展/200% 缩放/窄屏） | 数据互通（跨语言/跨 OS 读写） |
|---|---|---|---|---|---|---|
| `en-US`（基线） | | | | | | |
| `de-DE` 扩展、`DD.MM` | | | | | | |
| `ar-SA` RTL / 双向文本 | | | | | | |
| `tr-TR` dotted/dotless I | | | | | | |
| `ja-JP` / `zh-CN` 大字集 | | | | | | |
| `fr-FR` / `sv-SE` / `cs-CZ` collation | | | | | | |
| `en-GB` 同语言异区域 | | | | | | |
| `hi-IN` / `th-TH` 复杂脚本 | | | | | | |

## 2. 伪本地化与伪镜像

| 步骤 | 结果 |
|---|---|
| 资源生成（加长 + 变音 + 方括号，约 1.3~2×） | |
| 全量跑源语言同等时点的功能 + 视觉 | |
| 截断/遮挡/溢出/布局破坏 | |
| 字符串拼接 | |
| 未暴露给本地化的硬编码串（伪串未出现处） | |
| 图片内嵌文字 | |
| 同一串多上下文复用（应拆分） | |
| 伪镜像：RTL 伪资源 + UI mirroring | |

## 3. RTL / 双向文本静态 + 渲染

| 检查 | 静态 | 真实渲染 | 证据 |
|---|---|---|---|
| `<html lang="ar" dir="rtl">`（base direction 用 `dir` 不用 CSS） | | | |
| `lang` ≠ 方向；块级元素仅在需改向时加 `dir` | | | |
| logical properties（`start`/`end`、`margin-inline-start`） | | | |
| 运行时插入文本 / 聊天块 / `<input>` 用 `dir="auto"` | | | |
| `<textarea>` / `<pre>` 用 `dir="auto"`；纯数字行对齐 | | | |
| 用户名/标签用 `<bdi>` 隔离（去掉对比方向变化） | | | |
| 表单 `dirname` → 请求体 `commentdir=rtl/ltr` → 服务端保存复用 | | | |
| 边界控制符 `&rlm;` / `&lrm;` | | | |
| 双向文本流、标点位置、表格列 RTL、表单输入起点、`alt`/`title`、overflow 方向 | | | |
| 滚动条（属 browser chrome，**不计缺陷**） | | | |

## 4. 格式与数据互通（F-1~F-8）

| # | 检查 | 结果 / 差异 |
|---|---|---|
| F-1 | 同时间戳/金额/数字在各 locale 格式化，非硬编码 `toLocaleString('en-US')` | |
| F-2 | 时区 + DST 切换前后取值，UTC/neutral 存储、按用户时区显示、往返不漂移 | |
| F-3 | 非公历、周起始日、12/24 小时制 | |
| F-4 | 全角数字、千分位、小数点为逗号的输入解析 + round-trip | |
| F-5 | CSV/导出在不同 regional settings 下分隔符仍互通 | |
| F-6 | 语言 A 写入 → 所有 app languages × 所有 supported OS languages 读出且 preserved | |
| F-7 | localized OS objects（特殊文件夹名/账户名/registry），不假定英文路径 | |
| F-8 | 第三方文件含不同语言/脚本时兼容且数据不丢 | |

## 5. 源码静态审查（无浏览器时的最小集）

- [ ] 字符串全部外部化；无 `"Hello " + name` 拼接；无图片内嵌文字；有 context 注释
- [ ] locale 回退链 + 默认语言；缺 key 不显示 raw key / 空白
- [ ] 时间以 UTC/带偏移存储，仅展示层格式化；无 `new Date(str)` 本地假设解析
- [ ] URL/文件名/标识符不依赖 locale；不用 `toUpperCase()` 处理土耳其语用户名
- [ ] 排序/搜索调用带 locale 的 collator，不用默认 `sort()` 比码点
- [ ] `lang` 与 `dir` 成对；CSS 用 logical properties
- [ ] 错误文案也走资源文件且随 locale 变化
- [ ] 数字/金额来自格式化库，不是字符串模板拼 `,`/`.`
- [ ] font selection + font fallback（tofu 是缺陷）；`prefers-reduced-motion` 与动态视口在 RTL 下复验

## 6. 结论

```
locale 矩阵：___
伪本地化：___
RTL：___
格式：___
局限：___（例：未做真实语言审校；未做屏幕阅读器 RTL 验证；未做渲染验证）
结论：PASS / FAIL / BLOCKED（BLOCKED 项不得填 Pass）
```

> 无伪本地化资源 / 无浏览器时，报告固定写「**未做伪本地化与 RTL 运行时渲染验证**」，相关格标 `BLOCKED`。
> 分工：五态/a11y/CWV/运行时渲染 → `references/frontend-testing.md`；搜索结果的租户隔离 → `references/multi-tenancy-testing.md` §4。
