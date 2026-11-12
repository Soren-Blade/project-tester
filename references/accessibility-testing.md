# 无障碍可达性深度实测（阶段 3 · 横向叠加）

> 蒸馏自 W3C/WAI《What's New in WCAG 2.2》（2023-10-05 成为 W3C Recommendation）、WCAG 2.2 的 2.4.11 / 2.5.8 / 3.3.8 成功标准、Deque `axe-core` README（自动化覆盖率与 `incomplete` 结果）、DWP Accessibility Manual 的屏幕阅读器组合与结果标注、Playwright `toMatchAriaSnapshot` 官方文档，以及 `frontend-dev` / `fullstack-dev` 的焦点、表单与错误处理纪律。来源 URL 见 `CHANGELOG.md` v1.4.0。
> 定位：`references/frontend-testing.md` §3 给的是「前端可访问性最小动作清单」；本手册回答「**凭什么说它人人可用**」。三条分野：**自动化扫描绿 ≠ WCAG 合规**，**读屏能过 ≠ 键盘能过**，**有可访问名 ≠ 目标点得中**。

## 0. 适用边界与分工

| 触发 | 叠加本手册 | 不适用 |
|---|---|---|
| 有 UI、有交互、有表单/认证/导航的 Web 或桌面应用 | 是 | 纯 CLI / 无 UI 的库 / 批处理脚本 → 只写「不适用：无图形交互界面」，**不得**写「无障碍合规」 |
| 声称「符合 WCAG 2.2 AA」「支持读屏」「可键盘操作」「无障碍已验收」 | 强制 | — |
| 只想快速查 `alt` / `label for` / 对比度 | 去 `references/frontend-testing.md` §3 | 本手册不重复最小清单 |
| 关心跨设备 / 浏览器 / 真机覆盖 | 去 `references/cross-platform-testing.md`（R-8） | 设备真实性与可达性是两个维度，别互相替代 |

**三条认知打底**：
1. **自动化只能发现一部分**：`axe-core` README 明确写「find on average 57% of WCAG issues automatically」，且结果里有 `incomplete` 类型**需要人工复核**。`violations: 0` 不能推出「符合 WCAG」。
2. **WCAG 2.2 不是 2.1 换个版本号**：相较 2.1 新增 9 条成功标准；`4.1.1 Parsing` 被标为 obsolete 并**从 2.2 移除**。还把 4.1.1 当 2.2 检查项、或漏掉 2.4.11 / 2.5.8 / 3.3.8，就是验错了版本。
3. **「功能全绿」可能仍对一部分人完全不可用**：焦点被吸顶栏整体遮住、目标小于 24×24 点不中、认证要求手动转录验证码——这三类缺陷不会让任何一条功能用例变红。

## 1. WCAG 2.2 增量口径（先对准版本再测）

W3C 官方列出 2.2 相较 2.1 的 9 条新增成功标准：

| 编号 | 名称 | 级别 | 一句话判据 |
|---|---|---|---|
| 2.4.11 | Focus Not Obscured (Minimum) | AA | 组件获得键盘焦点时，不得被作者创建的内容**整体隐藏**（部分遮挡允许）；sticky header/footer、cookie banner 是高风险区 |
| 2.4.12 | Focus Not Obscured (Enhanced) | AAA | 焦点组件不得被任何作者创建内容遮挡（无「部分遮挡」豁免） |
| 2.4.13 | Focus Appearance | AAA | 焦点指示器有最小面积与对比度要求 |
| 2.5.7 | Dragging Movements | AA | 依赖拖拽的操作须有单指针替代（点一下也能完成） |
| 2.5.8 | Target Size (Minimum) | AA | 指针目标至少 **24×24 CSS pixels**；例外：Spacing / Equivalent / Inline / User Agent Control / Essential |
| 3.2.6 | Consistent Help | A | 帮助入口在多页间保持相对一致的顺序 |
| 3.3.7 | Redundant Entry | A | 同一流程中已填过的信息不要求重填（自动填充或可选择） |
| 3.3.8 | Accessible Authentication (Minimum) | AA | 认证**任一环节**不得要求 cognitive function test（记忆/转录/解谜），除非提供 Alternative / Mechanism / Object Recognition / Personal Content 之一 |
| 3.3.9 | Accessible Authentication (Enhanced) | AAA | 同上，允许例外更少 |

> **易错口径（本轮实测最容易写错的三处）**：
> - **44×44 CSS px 是 2.5.5 Target Size (Enhanced, AAA)**，不是 2.5.8 的门槛；把 2.5.8 写成「必须 44×44」属误引标准。
> - 3.3.8 中「密码管理器自动填充 / 允许 copy-paste」属于 **Mechanism** 例外；而**手动转录短信或图片验证码属于 cognitive function test**，没有替代方式即不合规。
> - `4.1.1 Parsing` 已从 WCAG 2.2 移除，不要再当 2.2 的失败项报；对 2.0/2.1 的合规声明才适用。

## 2. 自动化能做什么、不能做什么

| 手段 | 能覆盖 | 明确不能覆盖 | 必须留的证据 |
|---|---|---|---|
| `axe-core` / Lighthouse a11y | 语义、`alt`、可访问名、对比度、部分 ARIA 用法 | 焦点是否被遮挡、目标实际可点面积、读屏播报是否可理解、整条键盘路径、认知负担 | `violations` **+ `incomplete` 列表**（逐条人工复核，不得当 pass 计入） |
| Playwright `toMatchAriaSnapshot` | accessibility tree 的结构回归（角色 / 名称 / 层级） | 视觉、颜色、真实焦点顺序的可用性 | YAML 快照断言；它是 **a11y tree 快照，不是视觉截图** |
| 键盘自动化（Tab 序列断言） | 焦点顺序、焦点是否可见、有无键盘陷阱 | 听感与可理解性 | 每一步的 `document.activeElement` + 计算样式 |
| 人工读屏 | 名称/角色/状态是否播报正确、错误是否播报 | 大批量回归 | 记录 reader + browser + OS 组合、逐项结果标注 |

```bash
npx @axe-core/cli http://127.0.0.1:3000 --exit
npx lighthouse http://127.0.0.1:3000 --only-categories=accessibility --output=json
```

```javascript
// axe-core：只看 violations 会漏掉需要人工判定的项
axe.run().then(results => {
  console.log('violations:', results.violations.length);
  console.log('incomplete (需人工复核):', results.incomplete.map(r => r.id));
  if (results.violations.length) throw new Error('Accessibility issues found');
});
```

```javascript
// Playwright：断言 accessibility tree，不是像素；按组件粒度断言，别锁死整页
await expect(page.getByRole('main')).toMatchAriaSnapshot(`
  - heading "title" [level=1]
  - textbox "Email"
  - button "Sign in"
`);
```

> 断言纪律：`toMatchAriaSnapshot` 支持 partial matching 与 `/children: equal` / `deep-equal`。锁死整棵树会让无关文案改动造成大面积红灯；按组件/区域粒度断言更稳。快照变红时要区分「可达性退化」与「文案改了」，别无脑更新快照。

## 3. 人工实测：键盘路径 + 读屏组合（R-7 的主证据）

**键盘路径**（每个 P0 流程至少完整走一遍，全程不看鼠标）：

- 只用 Tab / Shift+Tab / Enter / Space / Esc / 方向键走完主流程
- 每停一处记三项：焦点元素、焦点是否可见（`:focus-visible` 的 `outline` 未被 `none` 杀掉）、是否被吸顶/吸底栏或 banner **整体遮住**（2.4.11）
- 弹窗 / 抽屉：打开时焦点进入、Tab 不逃出容器、Esc 关闭后焦点回到触发元素
- 200% 缩放、文本间距覆盖、`prefers-reduced-motion` 下复验无遮挡、无截断、无重叠
- 表单错误：错误播报（`aria-live` / `aria-describedby`）、错误文案说明「怎么改」而非「格式不正确」，且焦点能定位到出错字段

**读屏组合**（DWP Accessibility Manual 口径：至少覆盖一个常用 screen reader，结果逐项标注并保存证据）：

| 组合 | 环境 | 备注 |
|---|---|---|
| NVDA + Firefox / Chromium | Windows | 常用免费组合 |
| JAWS + Firefox / Chromium | Windows | 企业环境常见 |
| VoiceOver + Safari | macOS | macOS 上仅 Safari 是 fully supported 的组合 |
| Narrator + Edge | Windows | `Windows key + Control + Enter` 启停 |

每项结果标 **passed / failed / not checked / not present** 四类并留证据；`not checked` **不许计入通过**，也不许填 0 分假装修好。RTL locale 下需复验阅读顺序与双向文本播报（与 `references/i18n-localization-testing.md` §5 联动）。

## 4. 测试卡（A-1 ~ A-12）

| # | 测试动作 | 通过判据 | 常见失败 |
|---|---|---|---|
| A-1 | 确认验证基线写的是 **WCAG 2.2** 及目标级别（通常 AA） | 报告写明版本与级别 | 沿用 2.1 清单，漏 9 条新增项 |
| A-2 | `axe-core` 全页扫描，记录 violations + **incomplete** | 两类都留原文，incomplete 逐条给人工结论 | 只报 0 violations 就宣称合规 |
| A-3 | 键盘走完 P0 流程，逐步记 `activeElement` | 无焦点丢失/陷阱，顺序与视觉一致 | 自定义控件无 `tabindex`、模态可 Tab 逃逸 |
| A-4 | 焦点被吸顶/吸底/cookie banner 遮挡检查（2.4.11） | 焦点组件不被**整体**隐藏 | sticky header 盖住正在 Tab 的输入框 |
| A-5 | 目标尺寸实测（2.5.8） | ≥ 24×24 CSS px 或命中五类例外之一并写明 | 图标按钮 16×16；把 44×44 误当 AA 门槛 |
| A-6 | 认证流程 cognitive function test 检查（3.3.8） | 无转录/记忆/解谜，或有 Mechanism/Alternative | 只能手动抄图片验证码、禁止粘贴密码 |
| A-7 | 读屏组合逐项标注 passed/failed/not checked/not present | 至少一组组合有完整记录 | 只写「用 NVDA 测过」无逐项结论 |
| A-8 | 可访问名与状态播报 | 图标按钮有名称、动态结果 `aria-live` 播报 | 只有颜色/图标、提交成功无播报 |
| A-9 | 表单错误关联与焦点定位 | `aria-describedby` 生效、焦点跳到出错字段 | 错误只在页顶弹一句，读屏不播报 |
| A-10 | 200% 缩放 / 文本间距 / 减弱动效 | 无截断、无重叠、动画停止 | 固定 px 容器裁掉文字 |
| A-11 | 拖拽操作有单指针替代（2.5.7）、帮助入口一致（3.2.6）、不重填（3.3.7） | 逐条有结论 | 只能拖动排序、每步重填地址 |
| A-12 | `toMatchAriaSnapshot` 结构回归 | 按组件粒度、失败时人工判断是退化还是文案变化 | 无脑 `--update-snapshots` 把退化一起刷绿 |

## 5. R-7 无障碍可达性（可证伪规则，见 SKILL.md）

| 声称 | 必须附的证据 | 不适用时的写法 |
|---|---|---|
| 「符合 WCAG 2.2 AA / 支持读屏 / 可键盘操作 / 无障碍已验收」 | ① 明确目标版本与级别（WCAG 2.2 AA）；② `axe-core` 或等价扫描的 **violations + incomplete 原文**，且 incomplete 逐条给人工结论；③ 至少一条 P0 流程的**完整键盘路径记录**（逐步焦点元素、可见性、2.4.11 遮挡判定）；④ 至少一组**读屏 + 浏览器 + OS 组合**的逐项 passed/failed/not checked/not present 标注；⑤ 2.5.8 目标尺寸与 3.3.8 认证认知负担的实测结论 | 纯 CLI / 无 UI 的库 / 批处理脚本 / 无图形交互界面 → 只写「不适用：无图形交互界面，未做无障碍实测」，**不得**写「无障碍合规 / 符合 WCAG」；无读屏环境时只写「未做读屏实测（仅自动化扫描 + 键盘路径）」，结论降级为「待确认」 |

推论：**「axe 0 violations」不能推出「WCAG 合规」**（官方自述平均仅自动发现约 57% 问题 + 存在 `incomplete`）；**「keyboard 走得通」不能推出「读屏能理解」**；**「有 `aria-label`」不能推出「目标点得中」**。缺读屏或键盘任一路证据，结论一律降级为「待确认」，不许用「前端用例全绿」冒充通过。

## 6. L0 零依赖降级路径（工具全缺也能走完）

```bash
# 静态语义线索（仅作线索，不是判定）：查 label/alt/lang/aria 与 outline 是否被杀掉
curl -s "$URL" | grep -oiE '<(img|input|button|label)[^>]*>' | head -40
git grep -nE 'outline:\s*none|outline:\s*0' -- '*.css' '*.scss' '*.tsx' '*.vue'
git grep -nE 'aria-(label|live|describedby)|role=' -- '*.html' '*.tsx' '*.vue' | head -40
git grep -nEi '(captcha|verification code|paste|autocomplete)' -- '*.tsx' '*.vue' '*.html'
# 人工键盘走查：不装任何工具，只用 Tab/Shift+Tab/Enter/Esc，逐步记录焦点与遮挡
```

降级时报告固定写一行：「本轮仅做**静态语义线索扫描 + 人工键盘走查**，**未做自动化扫描与读屏组合实测**，结论降级为「待确认」」，并标 `BLOCKED` 而非 Pass。静态 `git grep` 出 `aria-label` **不等于**可访问名在运行时的树里正确。

## 7. 报告字段与分工

用 `assets/accessibility-matrix-template.md` 记录：目标版本与级别、violations/incomplete 原文与人工复核、键盘路径逐步记录、读屏组合与逐项标注、2.4.11 / 2.5.8 / 3.3.8 结论、缩放与减弱动效、R-7 结论、不适用声明。

| 主题 | 去哪 |
|---|---|
| 最小 a11y 动作清单、五态矩阵、CWV | `references/frontend-testing.md` §1~§4 |
| 跨设备 / 真机 / 浏览器矩阵 | `references/cross-platform-testing.md`（R-8） |
| RTL 下的读屏顺序与双向文本 | `references/i18n-localization-testing.md` §5 |
| 表单错误的跨边界映射 | `references/frontend-testing.md` §5 |
| 全局 Go/No-Go | `references/quality-gates.md` §3（R-7） |
| 工具与降级 | `references/tools.md` |
