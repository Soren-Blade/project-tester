# 前端 / UI 测试手册（阶段 3 · Web 项目）

> 蒸馏自用户附加技能 `frontend-dev` 的 Quality Gates / Design Rules / Motion Engine / Accessibility 章节、`fullstack-dev` 跨边界错误处理与集成检查、WCAG 2.2 / Core Web Vitals 公开口径。
> 核心主张：**前端 bug 大多不是"功能不工作"，而是"状态没做全"**。

## 1. 五态矩阵（最便宜、最高产的检查）

每个数据驱动的界面元素，逐格验证：

| 状态 | 触发方式 | 通过判据 |
|---|---|---|
| Loading | 节流网络 / 延迟响应 | 骨架屏或进度；不是白屏、不是无限转圈 |
| Empty | 清空数据 / 新账号 | 有引导与下一步动作，不只放一张插画 |
| Error | mock 500 / 断网 | 人话错误 + 重试入口；不显示 `NullPointerException` |
| Success | 正常流 | 有反馈（toast/inline），且状态确实落库 |
| Partial | 部分字段缺失 / 列表部分失败 | 不整页崩，缺失处有占位 |

```javascript
// Playwright 拦截改状态，无需改后端
await page.route('**/api/orders', r => r.fulfill({ status: 500, body: '{}' }));
await page.route('**/api/orders', r => r.fulfill({ status: 200, body: '[]' }));
await page.route('**/api/orders', async r => { await new Promise(x => setTimeout(x, 3000)); await r.continue(); });
```

**四态缺一即记 bug**（轻微~一般，涉及数据丢失则升级）。

## 2. 前端质量门禁（逐条可静态核对）

| 检查项 | 具体判据 | 来源 |
|---|---|---|
| 依赖真实存在 | `import` 的库都在 `package.json`；缺失即报缺失并给安装命令 | frontend-dev §1.2 |
| 无占位资源 | grep `unsplash\|picsum\|placeholder\|placehold\|via.placeholder\|dummyimage\|lorem` —— 命中即 FAIL；所有 `<img>/<video>/<source>/background-image` 必须指向本地已存在文件 | frontend-dev Quality Gates |
| 资源真实落地 | 断言每个引用的媒体文件在磁盘上存在（不是"应该会有"） | 同上 |
| 视口 | `min-h-[100dvh]` 而非 `h-screen`（移动端地址栏） | 同上 |
| 移动端塌陷 | 窄屏无横向滚动；高方差版式有 `w-full px-4` 降级 | 同上 |
| 动效性能 | 只动 `transform/opacity/filter/clip-path`；动 `width/height/top/left` 即 FAIL | frontend-dev §2.4 |
| 动效互斥 | 同一组件不混用 GSAP + Framer；`useEffect` 有 `ctx.revert()` 清理 | frontend-dev §2.1/2.4 |
| 减弱动效 | `prefers-reduced-motion` 下有降级；自动播放有暂停按钮；闪烁 ≤ 3 次/秒 | frontend-dev §2.6 |
| 焦点可见 | `outline` 未被 `none` 杀掉；Tab 顺序与视觉顺序一致 | WCAG 2.4.7 / 2.4.11 |
| ARIA | 动态内容有 `aria-live="polite"`；图标按钮有可访问名 | WCAG 4.1.2 |

### 2.1 运行时动效与资源实测（v1.1 新增，`frontend-dev` 二次蒸馏）

§2 是静态可查的；以下必须在**真实渲染**下观察，静态 grep 不能替代：

| 动作 | 观察点 | 通过判据 |
|---|---|---|
| 首屏加载 | Network 面板资源清单 | Lottie / GSAP / Three.js 等重库按需加载，不在首屏 bundle |
| 持续动画 30~60s | 内存 / FPS / CPU | 无持续上升；无限微动画隔离在 `React.memo` 叶组件；`will-change` 仅在动画期间存在 |
| 路由切换 / 组件卸载 | 监听器、RAF、定时器 | 每个含 GSAP/observer 的 `useEffect` 都 `return () => ctx.revert()`；无残留 RAF 与重复订阅 |
| 动态视口 resize | 390 / 768 / 1440 三档 + 移动端地址栏收起 | 无横向滚动、无重叠；`pointer: coarse` 下禁用 parallax/3D 与 GSAP pin |
| 自动播放媒体 | 暂停控件 | 有可见暂停按钮；`prefers-reduced-motion: reduce` 下动画停止；闪烁 ≤ 3 次/秒 |
| 动画属性 | 计算样式 / Performance 面板 | 只动 `transform/opacity/filter/clip-path`；出现 `width/height/top/left` 动画即 FAIL |

降级：无浏览器自动化时，至少静态核对 `prefers-reduced-motion` 分支、`useEffect` cleanup 返回值与 `lazy`/`dynamic` 导入，并注明「未做运行时渲染验证」——**静态核对不得冒充运行时结论**。

## 3. 可访问性实测（WCAG 2.2 口径）

| 维度 | 最小测试动作 |
|---|---|
| 键盘 | 全程只用 Tab/Shift+Tab/Enter/Esc 走完主流程；焦点不丢失、不陷入陷阱 |
| 读屏 | 用屏幕阅读器或 accessibility tree 检查：图片 alt、表单 label 关联、错误是否播报 |
| 对比度 | 正文 ≥ 4.5:1、大字 ≥ 3:1；不**只靠颜色**传达状态（错误不能只是变红） |
| 目标尺寸 | WCAG 2.2 的 2.5.8 最小 24×24 CSS px（推荐 44×44）；相邻目标间距足够 |
| 焦点不被遮挡 | WCAG 2.2 的 2.4.11 Focus Not Obscured：吸顶/吸底元素别盖住焦点 |
| 缩放 | 200% 缩放与文本间距覆盖后不重叠、不截断 |
| 表单 | 标签在输入框上方、错误在输入框下方；错误文案说明"怎么改"而非"格式不正确" |

```bash
# 自动化兜底：axe-core / Lighthouse（若环境有 Node）
npx @axe-core/cli http://127.0.0.1:3000 --exit
npx lighthouse http://127.0.0.1:3000 --only-categories=accessibility,performance --output=json
```
降级：无浏览器自动化时用 curl 验 HTML 语义标签、`label for`、`alt`、`lang`，并在报告注明"未做真实渲染验证"。

## 4. 性能与视觉（用户感知，不是后端 p95）

- **Core Web Vitals**（真实用户第 75 百分位）：LCP ≤ 2.5s、INP ≤ 200ms、CLS ≤ 0.1；TTFB ≤ 0.8s
- 图片/视频声明尺寸，否则加载后布局跳动 → CLS
- 长列表、大图、字体自托管与 `font-display`；中文逐字符回退避免方框乱码
- 视觉回归：同尺寸截图 diff（有工具时）；无工具时至少核对窄/中/宽三档断点的人工截图
- 指标只是代理，**以"用户看到的内容是否可用"为准**；为刷 LCP 换成模糊小图是反模式

## 5. 跨边界错误映射（`fullstack-dev` §12）

后端错误码 → 前端人话，逐格验证：

| 码 | 应显示 | 禁止 |
|---|---|---|
| 401 | 引导重新登录（先尝试刷新 token） | 直接白屏 / 原始 JSON |
| 403 | 无权限说明 | 显示"服务器错误" |
| 404 | 找不到 + 返回入口 | 空白页 |
| 409 | 冲突说明 + 刷新建议 | 静默失败 |
| 422 | **字段级**错误贴在对应输入框旁 | 只在页面顶部弹一句"请检查输入" |
| 429 | 稍后重试 + 等待提示 | 无限重试 |
| 5xx | 通用提示 + 重试 | 自动无限重试、暴露堆栈 |
| 网络断开 | 离线横幅 | 无限 loading |

规则：4xx **不自动重试**；5xx 最多 3 次退避重试；刷新 token 失败后跳登录；错误不得被静默吞掉。

## 6. 表单与输入专项

- 空提交、纯空格、超长（1 万 / 10 万字符）、`<script>`、emoji、RTL、零宽空格、粘贴富文本
- 校验时机三档：输入中（格式）/ 失焦（字段）/ 提交（跨字段）；**一进页面就全红 = bug**
- 客户端校验通过但服务端拒绝时，前端能否把服务端字段错误回填到对应控件
- 双击提交、提交后立刻刷新 → 幂等与重复提交防护（与 `api-testing.md` §5 联动）
- 日期/时区：跨日边界、不同 locale 格式解析一致性

## 7. Playwright Test Agents（AI 辅助生成，v1.56+ / 2026）

官方内置三智能体，可单独或串成 loop（`npx playwright init-agents --loop=vscode`，VS Code ≥ 1.105）：

| Agent | 输入 | 产出 |
|---|---|---|
| 🎭 planner | 明确请求 + `seed.spec.ts`（环境初始化）+ 可选 PRD | `specs/*.md` 人类可读测试计划 |
| 🎭 generator | Markdown 计划 | `tests/**/*.spec.ts`，边生成边验证选择器与断言 |
| 🎭 healer | 失败的测试名 | 重放、定位等价元素、建议补丁、重跑；修复不了则跳过并标注"疑似功能损坏" |

**这正好对应本技能的阶段 2→3**：planner 产计划、generator 产用例、healer 处理失败。但必须遵守 `ai-native-testing.md` 的审查纪律——**healer 把测试改成"通过"不等于 bug 被修了**，要核对它是不是把断言删弱了。

降级：无 Playwright 时按 `tools.md` 走 HTTP 层验证 + HTML 关键元素断言。

## 8. 判 bug 补充条款（叠加在 SKILL.md 五条之上）

1. 五态矩阵缺失任一态
2. 报错信息为技术原文 / 原始 JSON / 堆栈
3. 窄屏横向滚动、200% 缩放内容截断
4. 焦点不可见、键盘走不完主流程、仅靠颜色表达状态
5. 占位资源 URL 或引用了不存在的本地媒体
6. 动效未尊重 `prefers-reduced-motion`、持续动画导致卡顿
7. 加载后布局跳动（CLS）、图片未声明尺寸

## 9. 记录格式

```
渲染验证：浏览器自动化 ✅ / 降级 HTTP 层 ⚠️（注明局限）
五态：L✅ E🐛(空态只有插画无引导) Err✅ S✅ P◐
a11y：键盘通路 ✅ ｜ axe-core 3 violations（附规则 id）｜ 对比度 2 处不达标
CWV：LCP 1.9s / INP 240ms 🐛 / CLS 0.02（本地合成数据，非 RUM）
错误映射：422 未回填字段 → 🐛 BUG#12
```
