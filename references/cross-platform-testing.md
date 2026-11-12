# 跨端与设备形态真实性测试（阶段 3 · 横向叠加）

> 蒸馏自 Playwright 官方文档 Emulation / `devices` 描述符、LambdaTest Learning Hub 的设备矩阵与真机选型实践、DWP Accessibility Manual 的平台组合口径、GitHub `naodeng/awesome-qa-skills` 的 `mobile-testing` / `cross-browser-testing` / `visual-regression-testing` 分类，以及 `frontend-dev` 的动态视口 / `pointer: coarse` 纪律。来源 URL 见 `CHANGELOG.md` v1.4.0。
> 定位：`references/frontend-testing.md` 的窄屏三档断点测的是**版式**；本手册回答「**换一台真实设备、换一个浏览器内核、换一种网络，结论还成立吗**」。一句话分野：**仿真能验布局与流程，真机才能验硬件与现实网络**。

## 0. 适用边界与分工

| 触发 | 叠加本手册 | 不适用 |
|---|---|---|
| 有 Web UI / 移动端 / 桌面端 / 多浏览器用户 | 是 | 纯后端 API、CLI、无 UI 的库 → 只写「不适用：无终端形态差异」，**不得**写「跨端已验证」 |
| 声称「移动端可用」「兼容主流浏览器」「已适配折叠屏/平板」「真机验过」 | 强制 | — |
| 关心读屏、键盘、WCAG 2.2 | 去 `references/accessibility-testing.md`（R-7） | 可达性与设备真实性是两个维度 |
| 只想快速验窄/中/宽三档断点 | 去 `references/frontend-testing.md` §4 | 三档断点不等于设备矩阵 |

**三条认知打底**：
1. **设备描述符不是真机**：Playwright 的 `devices['iPhone 13']` 是一组 viewport / userAgent / hasTouch / deviceScaleFactor 等预设，属于仿真；它跑在桌面内核上，没有真实基带、电池、传感器与厂商皮肤。
2. **矩阵要从数据来，不从想象来**：设备清单应以 install-base analytics（真实用户占比）为依据，覆盖绝大部分实际安装量，再补上「低配、老系统、异形屏、厂商定制」这些占比小但出事概率高的条目，并定期复审。
3. **仿真与真机是分工，不是替代**：emulator/simulator 适合 CI 里快速拿布局与流程反馈；发布门禁前的 battery / thermal / sensors / biometrics / real network 只能在真机上验。

## 1. 设备矩阵怎么定（先写来源，再写清单）

| 步骤 | 动作 | 判据 |
|---|---|---|
| M-1 | 从 install-base analytics 取 OS / 机型 / 浏览器版本分布 | 报告写明**数据来源与时间窗**，不写「凭经验选几台」 |
| M-2 | 取覆盖约 **80% installs** 的主干组合 | 累计占比写进矩阵；不足 80% 要说明取舍理由 |
| M-3 | 强制补充长尾高危条目 | low-RAM Android、oldest supported OS、vendor skin（厂商定制 ROM/WebView）、foldable / tablet、小屏 + 大字体 |
| M-4 | 浏览器内核覆盖 | 至少覆盖实际用户里的不同内核（Chromium / WebKit / Gecko），别用三个 Chromium 套壳冒充跨浏览器 |
| M-5 | 定期复审 | 每季度用最新分布重算一次，过期矩阵标「需复审」而非继续沿用 |

> 矩阵里必须区分 `real` / `emulator` / `simulator` / `browser-emulation` 四种执行载体。**把 emulation 写成 "真机验证" 是最常见也是最严重的证据造假**。

## 2. 仿真能做什么、真机必须做什么

| 载体 | 适合验 | 不适合验 | 结论怎么写 |
|---|---|---|---|
| 浏览器 emulation（Playwright `devices` / viewport / locale 等） | 布局、流程、文案溢出、时区/locale 格式、深色模式、减弱动效、离线态 | 性能、电量、发热、传感器、生物识别、真实网络切换、厂商 WebView 差异 | 「已在 N 组仿真配置下验证布局/流程」 |
| emulator / simulator | 安装、启动、权限弹窗、旋转、生命周期事件的自动化回归 | 真实 GPU/thermal throttle、基带、指纹/人脸、真机推送 | 「已在模拟器验证 X，真机项未覆盖」 |
| real device | battery、thermal、sensors、biometrics、real network（含弱网/切换）、应用商店构建、release gate | 大规模并发矩阵（成本高，交给 CI 仿真） | 「发布门禁前至少 1 组真机组合通过」 |
| device cloud | 补齐长尾机型与厂商皮肤 | 需要本地硬件/离线/外设的场景 | 注明云真机厂商与机型，仍属 real |

## 3. 仿真配置的可执行清单（Playwright）

Playwright 的 emulation 可覆盖：`userAgent`、`screenSize`、`viewport`、`hasTouch`、`deviceScaleFactor`、`locale`、`timezoneId`、`geolocation`、`permissions`、`colorScheme`、`reducedMotion`、`forcedColors`、`contrast`、`offline`、`javaScriptEnabled`。

```javascript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  projects: [
    { name: 'chromium',       use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox',        use: { ...devices['Desktop Firefox'] } },
    { name: 'Mobile Safari',  use: { ...devices['iPhone 13'] } },     // 仿真，非真机
    { name: 'Mobile Chrome',  use: { ...devices['Pixel 7'] } },
  ],
});
```

```javascript
// 单测里覆写区域、时区、配色、离线与权限
test.use({
  locale: 'de-DE',
  timezoneId: 'Europe/Berlin',
  colorScheme: 'dark',
  reducedMotion: 'reduce',
  permissions: ['geolocation'],
  geolocation: { latitude: 52.52, longitude: 13.405 },
});
await page.context().setOffline(true);   // 离线态：错误提示 / 缓存 / 重试入口
```

> 纪律：`locale` / `timezoneId` 仿真只能验格式与文案，不能替代 `references/i18n-localization-testing.md` 的真实 locale 数据往返；`colorScheme` / `reducedMotion` 仿真不能替代 `references/accessibility-testing.md` 的人工读屏与键盘路径。三者各记各的证据，不许互相冒充。

## 4. 端侧特有面（桌面 Web 用例天然不覆盖）

| 面 | 最小测试动作 | 常见失败 |
|---|---|---|
| 应用生命周期 | 前台→后台→回前台、锁屏/解锁、进程被系统回收后恢复 | 白屏、表单数据丢失、重复提交 |
| 中断 | 来电/通知/闹钟/分屏切换、切换 App 再回来 | 支付/上传中断后状态错乱 |
| 权限 | 首次拒绝、拒绝后不再询问、设置里改回允许、仅使用时允许 | 拒绝后死循环弹窗或静默无功能 |
| 屏幕形态 | 旋转、折叠/展开、平板多窗口、外接显示器、刘海/安全区 | 布局重叠、状态丢失、`h-screen` 在地址栏收起时溢出 |
| 深链 / 推送 | 冷启动经 deep link / push 进入、未登录态落地页、参数篡改 | 直达内部状态绕过鉴权 |
| 生物识别 | 指纹/人脸成功、失败、设备未录入、锁屏后回前台 | 失败后无限重试、无密码回退路径 |
| 输入与硬件 | 软键盘遮挡输入框、实体键盘 Tab、触屏 `pointer: coarse`、相机/定位 | 提交按钮被键盘盖住、hover 才可见的操作触屏永远点不到 |
| 安装与升级 | 覆盖安装、从旧版本数据迁移、离线安装、商店签名构建 | 旧数据 schema 不兼容即崩 |

## 5. 网络与环境档位（写清口径，别写「弱网测过」）

| 档位 | 可复现口径 | 观察点 |
|---|---|---|
| 离线 | `context.setOffline(true)` / 飞行模式 | 离线横幅、缓存可读、重试入口、无无限 loading |
| 高延迟 / 低带宽 | 浏览器网络节流或设备侧限速，写明上下行与时延数值 | 骨架屏、超时提示、请求不重复发 |
| 网络切换 | Wi-Fi → 蜂窝 → 弱信号 → 恢复 | 请求幂等、断线重连、不丢已提交数据 |
| 后台/受限 | 系统省电模式、后台数据受限 | 同步任务被推迟后状态一致 |

> 每档都写**具体参数 + 执行载体（仿真/真机）+ 观察结果**。「弱网下正常」这种没有数值、没有载体的结论不算证据。

## 6. 测试卡（X-1 ~ X-12）

| # | 测试动作 | 通过判据 | 常见失败 |
|---|---|---|---|
| X-1 | 设备矩阵来源与覆盖占比写进报告 | 有 analytics 来源、时间窗、约 80% 覆盖 | 拍脑袋列 3 台机型 |
| X-2 | 矩阵标全 `real` / `emulator` / `browser-emulation` 载体 | 无载体混淆 | 把 `devices['iPhone 13']` 写成真机 |
| X-3 | 覆盖不同浏览器内核 | 至少两类真实内核 | 三个 Chromium 套壳 |
| X-4 | 长尾条目：low-RAM、oldest OS、vendor skin、foldable/tablet | 逐条有结论或显式声明未覆盖 | 只测最新旗舰机 |
| X-5 | 生命周期与中断 | 前后台/回收/来电后状态一致 | 回前台白屏、重复扣款 |
| X-6 | 权限四态（首次/拒绝/不再询问/设置改回） | 每态有降级路径 | 拒绝后功能静默消失 |
| X-7 | 旋转 / 折叠 / 多窗口 / 安全区 | 无重叠、无横向滚动、状态保持 | 旋转后表单清空 |
| X-8 | 深链 / 推送冷启动 + 未登录态 | 落地页正确、鉴权不被绕过 | 直达内部页跳过登录 |
| X-9 | 生物识别成功/失败/未录入 | 有密码回退，失败不无限重试 | 无回退路径，用户被锁死 |
| X-10 | 软键盘 / `pointer: coarse` / 触屏专属操作 | 输入框与提交按钮可见可点 | hover-only 菜单触屏不可用 |
| X-11 | 网络档位（离线/高延迟/切换/省电） | 每档有参数、载体、观察结果 | 只写「弱网测过」 |
| X-12 | 发布门禁前的真机组 | 至少 1 组 real device 覆盖 battery/thermal/real network 观察 | 全靠仿真就宣布可发布 |

## 7. R-8 跨端与设备形态真实性（可证伪规则，见 SKILL.md）

| 声称 | 必须附的证据 | 不适用时的写法 |
|---|---|---|
| 「移动端可用 / 兼容主流浏览器 / 已适配折叠屏 / 跨端已验证 / 真机验过」 | ① **设备矩阵来源**（install-base analytics 的数据源与时间窗）、覆盖占比、以及 `real` / `emulator` / `browser-emulation` 逐项标注；② 不同浏览器内核的实测记录；③ 长尾条目（低配 / 最老受支持 OS / 厂商皮肤 / 折叠屏平板）逐条结论或显式「未覆盖」；④ 端侧特有面（生命周期、中断、权限、旋转、深链、网络档位）的实际输出；⑤ 声称「真机验过」须有至少 1 组 real device 记录（含机型/OS/网络与 battery/thermal/real network 观察） | 纯后端 API / CLI / 无 UI 的库 → 只写「不适用：无终端形态差异，未做跨端验证」，**不得**写「跨端已验证」；只有仿真时写「仅完成仿真验证，未做真机验证」，结论降级为「待确认」，**不得**写「真机验过 / 全平台兼容」 |

推论：**「三档断点都正常」不能推出「移动端可用」**；**「Playwright Mobile Safari 项目绿」不能推出「iOS 真机没问题」**；**「桌面 Chrome 通过」不能推出「WebKit/Gecko 通过」**。缺 real device 而声称跨端通过，一律作废降为「待确认」；缺矩阵来源而列一堆机型，同样不算证据。

## 8. L0 零依赖降级路径（工具全缺也能走完）

```bash
# 静态线索：查视口单位、hover-only、触屏降级、固定定位与安全区
git grep -nE '100vh|h-screen|@media.*hover|:hover' -- '*.css' '*.scss' '*.tsx' '*.vue' | head -40
git grep -nE 'safe-area-inset|viewport-fit|min-h-\[100dvh\]' -- '*.html' '*.css' '*.tsx'
git grep -nEi '(orientationchange|visibilitychange|resize|onResume|onPause)' -- '*.ts' '*.tsx' '*.java' '*.kt' '*.swift'
# 人工真机最小集：手边 1 台真机，走 前台→后台→回前台 + 旋转 + 飞行模式→恢复 + 深链冷启动
```

降级时报告固定写一行：「本轮仅做**静态视口线索审查 + 单台真机手工走查**，**未建立基于安装量分布的设备矩阵、未覆盖多内核与长尾机型**，结论降级为「待确认」」，并标 `BLOCKED` 而非 Pass。手工走查仍属 real device 观察，但只能写「单台真机手工走查」，不能升级成「设备矩阵验证通过」。

## 9. 报告字段与分工

用 `assets/device-matrix-template.md` 记录：矩阵来源与覆盖占比、逐设备的载体标注与内核、长尾条目结论、生命周期/中断/权限/旋转/深链/生物识别、网络档位参数与观察、真机证据、R-8 结论、不适用声明。

| 主题 | 去哪 |
|---|---|
| 五态矩阵、三档断点、CWV、视觉回归 | `references/frontend-testing.md` §1/§4 |
| WCAG 2.2、键盘与读屏 | `references/accessibility-testing.md`（R-7） |
| locale / 时区 / RTL 数据往返 | `references/i18n-localization-testing.md` |
| 发布六门禁 12 分 | `references/fullstack-integration.md` §6 |
| 全局 Go/No-Go | `references/quality-gates.md` §3（R-8） |
| 工具与降级 | `references/tools.md` |
