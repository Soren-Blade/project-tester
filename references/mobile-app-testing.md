# 移动 App 操作系统集成面与分发（R-25）

**一句话主线：装上了、点得动 ≠ 在真实手机的操作系统里活下来了。本规则只回答一件事——把 App 装进一部会被来电、通知、低电量、弱网、系统回收打断的真实设备后，权限、生命周期、深链、推送、升级与分发这些「宿主环境契约」有没有被验证过。**

> 适用：iOS / Android / 鸿蒙原生 App、React Native / Flutter / 小程序壳等移动安装包 ｜ 配套：`assets/mobile-app-matrix-template.md` · `scripts/mobile-audit.py` ｜ 相关规则：R-8（设备矩阵真实性：管「测了哪些端」，本规则管「端上的宿主集成面」）、R-12（身份会话）、R-17（缓存与发布生效）、R-18（上传下载）
>
> **与 R-8 的分工**：R-8 问「矩阵是否真实、载体是否标对、真机有没有 ≥1 组」；R-25 问「在标对的设备上，权限/中断/生命周期/深链/推送/升级/弱网/电量是否逐项测过」。两条都要答，任一空白就不算「移动端测过」。

## 0. 触发条件与不适用

| 场景 | 是否触发 | 说明 |
|---|---|---|
| 有 `.apk`/`.aab`/`.ipa`/`.app` 产物，或要求在手机上使用 | ✅ 必做 | 安装包即触发；不得只测 Web 版就宣称移动端可用 |
| 声称「真机验过 / 已适配 iOS 或 Android / 不会闪退 / 推送正常 / 升级没影响」 | ✅ 必做 | 逐项给证据；不得用「装上了能点」代替 |
| 有权限申请（相机/定位/通知/麦克风/相册/蓝牙） | ✅ 必做 | 四种授权状态都要走；不得只测「允许」 |
| 有深链 / Universal Link / App Link / 推送落地页 | ✅ 必做 | 冷启/温启/热启、未登录、非法参数都要走 |
| 有分阶段发布 / 强制更新 / 热更新 / TestFlight / 灰度轨道 | ✅ 必做 | 升级与回滚是独立风险面；不得只看「能装上」 |
| 只有 H5 / 小程序、无原生安装包 | ❌ 不适用 | 写「不适用：无移动安装包与 OS 集成面」；小程序走 C3 手册 |
| 内部工具、只在单一测试机自用 | ◐ 降级 | 仍须测权限拒绝与后台回收；写「仅单机自用，未做设备矩阵与灰度」 |
| 纯后端 SDK / 无 UI 的库 | ❌ 不适用 | 写「不适用：无移动终端交互面」 |
| 客户提供已签名包、无源码与构建能力 | ◐ 降级 | 黑盒测权限/中断/深链/升级；静态扫描只报「无法核对源码」，不冒充通过 |

## 1. 先问 8 个契约问题

1. **构建与签名**：bundle id / applicationId、versionName + versionCode（iOS 为 CFBundleShortVersionString + CFBundleVersion）、签名证书、是否可重装同版本？
2. **分发渠道**：App Store / Google Play / 企业分发 / TestFlight / 内测轨道？灰度比例、停量、回滚旧版分别怎么做？
3. **最低与目标 OS**：minSdk / deployment target 各是多少？矩阵里有没有「最老受支持版本」与「最新大版本」两端？
4. **权限清单**：申请哪些运行时权限？每个权限的「拒绝 + 不再询问」后产品如何降级？有没有「先拒后开」的恢复路径？
5. **深链与推送**：scheme / host / path 白名单是什么？未登录点深链落到哪？推送 payload 的点击路由由谁解析？
6. **生命周期**：进程被系统杀死后，草稿/登录态/播放进度靠什么恢复？后台任务、定位、蓝牙在后台是否继续？
7. **弱网与电量**：目标用户网络档位（2G/3G/4G/弱 WiFi）？低电量模式 / Doze / 省电策略下哪些功能会停？
8. **热更新与强制更新**：是否可绕过商店更新？热更新包如何签名校验？强制更新失败时用户是否被锁死？

八问有一问答不出，报告只能写「未确认」，不得写「移动端通过」。

## 2. 选型矩阵（按被测形态选，不按喜好选）

| 方案 | 最适合 | 优势 | 代价 / 边界 | 证据强度 | 典型失真 |
|---|---|---|---|---|---|
| **Appium 2+** | 跨 iOS/Android 黑盒、已有 WebDriver 体系 | 驱动可插拔（官方 `uiautomator2` / `xcuitest` / `espresso` / `mac2` 等需单独 `appium driver install`）；多语言客户端 | 需装驱动与服务端；会话启动慢；系统弹窗/权限需额外处理；版本矩阵自身也要维护 | 中（黑盒可复现，但易只测主路径） | 用 `autoGrantPermissions` 一把梭，拒绝路径从未被测 |
| **Maestro** | 快速冒烟、YAML 可读、非工程同学也能改 | 命令面覆盖 `launchApp` 权限配置、`setPermissions`、`openLink`、`setAirplaneMode`、`assertVisible`（自带重试）、`extendedWaitUntil`、`startRecording`；学习成本低 | 复杂手势/原生混合栈覆盖有限；断言偏「可见/文本」，弱于像素与结构断言；CI 需另配 | 中 | 只断言「看得见」，不校验数据与副作用 |
| **XCUITest** | iOS 原生、需要系统级中断与 Apple 能力 | 苹果官方；`addUIInterruptionMonitor` 可处理系统弹窗；`launchArguments` 注入测试开关；与 Xcode Cloud 集成 | 仅 iOS/macOS；Swift/ObjC 门槛；跨端要再写一套 | 高（原生、可访问系统层） | 用 `launchArguments` 把权限/网络全 mock 掉，真机集成面没测 |
| **Espresso** | Android 原生、单 App 内 UI 同步 | 官方；`IdlingResource` 与主线程同步，flaky 低；速度快 | 只能驱动被测 App 自身，系统 UI（权限弹窗、通知栏）需 UiAutomator 配合；跨 App 流程弱 | 高（进程内、确定性强） | 在 `@Before` 里预授权，拒绝路径与「不再询问」没测 |
| **Detox** | React Native / 混合 JS 栈 | 与 RN 同步机制集成，自动等待网络/动画/定时器；`device.launchApp({ permissions })` 可编排权限 | 绑定 RN/Jest；原生模块与系统层覆盖不如原生框架；iOS 需构建 test target | 中高 | 同步等待掩盖真实弱网/卡顿，性能结论不可用 |
| **设备云**（Firebase Test Lab / BrowserStack / Sauce / AWS Device Farm / Xcode Cloud） | 真机长尾、并发跑矩阵 | 真机型号多、可并行、留存录像与日志 | 网络整形与真机温度/电量不可完全控；账号/支付/推送常受限；结果回传有延迟 | 中（真机但环境被托管） | 把云真机结果当「用户真机」；弱网档位是平台预设而非目标用户网络 |

**选型纪律**：① 至少一条**真机**路径（R-8）；② 权限拒绝路径必须有能「不预授权」的框架（Appium 关掉 `autoGrantPermissions`、Maestro 用 `setPermissions: deny`、XCUITest 不预置、Espresso 用 UiAutomator 处理弹窗）；③ 同一结论不跨框架混用——Espresso 的「无 flaky」不能证明 Maestro 流程稳定。

## 3. 执行环境：仿真器 · 真机 · 设备云

| 环境 | 能证明 | 不能证明 | 报告写法 |
|---|---|---|---|
| 仿真器 / 模拟器 | 布局、跳转、权限状态机、深链路由、崩溃栈 | 真实性能、相机/蓝牙/生物识别、厂商 ROM 差异、真实网络与电量 | 「仅仿真验证」 |
| 真机（自持） | 上述全部 + 传感器、热、电、厂商皮肤 | 长尾机型、真实用户网络分布 | 「真机 N 台：型号/OS/ROM」 |
| 设备云 | 型号长尾、并行回归、录像留证 | 支付/推送/账号常被限制；网络档位是平台参数 | 「云真机，未验证支付与推送」 |

**载体标注**必须逐条落到矩阵（`real` / `emulator` / `simulator` / `cloud-real`），不得把 `cloud-real` 简写成 `real` 而不写环境限制。

## 4. 权限与系统弹窗（最容易被「全允许」掩盖）

Android 运行时权限是一个**状态机**，至少有四态；只测「允许」等于没测：

| 状态 | 如何到达 | 必测行为 |
|---|---|---|
| 首次询问 → 允许 | 全新安装首次触发 | 功能正常；授权后不再重复弹 |
| 首次询问 → 拒绝 | 点「拒绝」 | 功能降级可理解、可恢复；不得白屏/崩溃 |
| 拒绝两次 → 「不再询问」 | Android 连续拒绝 / iOS 曾拒绝 | 引导去系统设置；返回后状态能刷新 |
| 系统设置中手动关闭 | 设置页撤销权限 | 回到 App 时检测到撤销并降级，不沿用旧缓存 |

```bash
# Android：查看/撤销运行时权限（包名替换）
adb shell dumpsys package com.example.app | findstr "android.permission.CAMERA"
adb shell pm revoke com.example.app android.permission.CAMERA
adb shell pm clear com.example.app        # 清数据；是否同时重置权限随 OS 版本不同，必须实测确认，不得假设
# iOS 模拟器：重置某 App 的全部隐私授权
xcrun simctl privacy booted reset all com.example.app
```

**系统弹窗与中断**：来电、闹钟、低电量弹窗、系统更新提示、通知横幅、控制中心下拉、分屏/画中画。弹窗出现时被测页面的输入焦点、计时器、上传/支付流程是否被破坏，必须逐项记录；**用 `autoAcceptAlerts` / `autoGrantPermissions` 把弹窗全自动点掉，等于把这些风险从测试里删掉**（脚本 MB-10 会报）。

## 5. 生命周期与进程回收

必须实测的六件事：

1. **后台 → 前台**：计时器、轮询、播放、上传是否继续/恢复；恢复后是否重复提交。
2. **进程被系统杀死后恢复**：开发者选项「不保留活动」或 `adb shell am kill` / `am force-stop` 后重进，草稿、登录态、支付中间态是否可恢复；不得出现「订单已支付但页面显示未支付」。
3. **旋转 / 分屏 / 折叠**：布局重排后输入内容与滚动位置是否保留；折叠屏展开/合上不得丢状态。
4. **字体缩放 / 显示大小 / 深色模式**：系统级设置变化后文字不截断、对比度可读。
5. **时区 / 语言切换**：切到非默认 locale 后日期、金额、RTL 布局正确（与 R-13、i18n 手册联动）。
6. **低内存 / 后台限制**：后台任务被限制时，同步、上传、定位是否有明确失败提示与重试。

## 6. 深链、推送与通知

**深链（Deep Link / Universal Link / App Link）**：至少六条路径——冷启动、温启动（后台）、热启动（前台）、未登录、非法 host/path、重复点击同一链接。每条要记录落到哪一页、是否要求登录、登录后是否回到目标页、参数是否被当作用户输入校验（`orderId` 注入、越权查看他人订单 = S1）。

```bash
# Android
adb shell am start -W -a android.intent.action.VIEW -d "myapp://order/42" com.example.app
# iOS 模拟器
xcrun simctl openurl booted "myapp://order/42"
```

**推送**：APNs / FCM 至少覆盖前台、后台、杀进程三态；点击通知的路由是否正确、同一消息是否重复展示、通知权限被拒后是否有站内替代、token 刷新后旧 token 是否失效。iOS 模拟器可注入本地 payload：

```bash
xcrun simctl push booted com.example.app payload.apns
```

**证据**：每条深链/推送要有「命令 + 落地页截图/日志 + 是否越权」三件套；只证明「能打开」不算通过。

## 7. 安装、升级与灰度

| 场景 | 必须验证 | 判据 |
|---|---|---|
| 全新安装 | 首次启动引导、权限、登录、崩溃率 | 首启 3 分钟内无崩溃；权限四态可达 |
| 覆盖升级（N-1 → N） | 本地数据、登录态、数据库迁移、缓存兼容 | 升级后旧数据可读；不得清空登录态或丢草稿 |
| 降级安装 | 是否允许、数据是否可回退 | 明确声明允许/禁止；禁止时给用户可执行路径 |
| 分阶段放量 | 灰度比例、停量、回滚旧版 | 记录实际比例与观察指标；「能停」要有操作证据 |
| 强制更新 | 老版本被拦截时的提示与出口 | 不得把用户锁死；离线/失败时可重试 |

```bash
adb install -r app-release.apk          # 覆盖安装，保留数据
adb install -r -d app-release.apk       # 允许降级（是否可用随系统/签名策略）
xcrun simctl install booted MyApp.app   # 覆盖安装；先 uninstall 再 install = 全新安装
```

**灰度结论不得只看「装上了」**：必须有「当前轨道 / 比例 / 回滚动作 / 回滚后旧版可用」四项证据，否则只能写「未做灰度回滚验证」。

## 8. 弱网、电量与性能

**弱网必须写清档位**：上下行带宽、时延、丢包、是否抖动。只写「弱网下能用」不可复核。

| 档位 | 参数示例 | 关注点 |
|---|---|---|
| 离线 | 飞行模式 / 断网 | 本地缓存、队列重试、错误提示 |
| 2G/3G 等效 | 低带宽 + 高时延（模拟器 `-netdelay gprs -netspeed gsm`，以本机 `emulator -help-netdelay` 为准） | 首屏、图片、超时与重试 |
| 弱 WiFi | 高丢包 + 抖动 | 长连接、上传中断续传 |
| 网络切换 | WiFi ↔ 蜂窝、飞行模式开关 | 会话是否断、请求是否重放、支付是否重复 |

**电量与后台**：低电量模式、Doze、后台刷新限制下，同步/定位/推送是否按产品声明降级；不得出现「后台被杀后本地队列丢失」。性能只报可测项：冷/热启动耗时、首屏时间、内存峰值、包体大小、崩溃率（crash-free sessions），并写清设备型号与 OS。

```bash
adb shell dumpsys battery set level 5; adb shell dumpsys battery unplug
adb shell dumpsys deviceidle force-idle
adb shell settings put global animator_duration_scale 0   # 仅用于功能回归；测卡顿必须恢复 1.0
xcrun simctl status_bar booted override --time "9:41" --batteryLevel 20 --cellularBars 1
```

## 9. 静态反模式（`scripts/mobile-audit.py scan`，MB-01~MB-10）

静态扫描只报「代码形态可疑」，**每一条命中都必须逐条裁决**（真缺陷 / 误报原因 / 不适用原因），不得只贴数量。

| ID | 反模式 | 为什么是风险 | 典型误报 |
|---|---|---|---|
| MB-01 | UI 测试用绝对坐标点击 | 分辨率/刘海/折叠屏一变就点空，测试却可能「碰巧通过」 | 画布/游戏类坐标点击是业务本身 |
| MB-02 | 用固定 `sleep` 等界面，无 `waitFor`/`assertVisible` | 慢设备必 flaky；快设备掩盖真实卡顿 | 轮询外部任务的固定间隔 |
| MB-03 | 代码用了相机/定位/通知/麦克风，但清单缺权限声明或 iOS 缺 `NS*UsageDescription` | 真机首启即崩或被商店拒审 | 权限由宿主 App/插件声明（需人工核对） |
| MB-04 | WebView 开 JS 且无 URL 白名单/导航拦截 | 深链/广告页可加载任意页面，配合 JS 桥可越权 | 纯展示型 WebView 且无 JS 桥 |
| MB-05 | 深链入口直接取 `getData()`/URL 后 `startActivity`/跳转，无 host/path 校验 | 任意 App 可拉起内部页，造成越权或钓鱼 | 已在路由层统一校验（需指出位置） |
| MB-06 | 明文流量 / ATS 全放开 / 硬编码 `http://` 业务端点 | 中间人可篡改；商店审核风险 | 本地调试地址（localhost/10.0.2.2） |
| MB-07 | 组件 `exported="true"` 且无 `permission` 保护 | 任意 App 可调起内部组件 | 桌面启动器/必须导出的入口（需说明） |
| MB-08 | 源码硬编码 API key / secret / token | 反编译即泄漏 | 占位符、测试专用假 key（需标注） |
| MB-09 | 热更新/自更新通道无签名校验 | 可被替换恶意包 | 仅商店内更新、无自更新 |
| MB-10 | 测试能力里 `autoGrantPermissions`/`autoAcceptAlerts` 恒真 | 拒绝路径与系统弹窗永远不被测 | 仅用于与权限无关的冒烟套件（需分套件） |

## 10. 运行矩阵（`scripts/mobile-audit.py matrix`，MB-20~MB-29）

每条都要有「做/未做 + 证据」；未做写「未做 X 验证」，不适用写原因。

| ID | 面 | 必测动作 | 最低证据 |
|---|---|---|---|
| MB-20 | 权限状态机 | 允许 / 拒绝 / 不再询问 / 设置撤销 四态 | 四段录屏或截图 + 降级文案 |
| MB-21 | 系统中断 | 来电、通知横幅、低电量弹窗、系统更新提示 | 中断前后状态截图 + 是否丢输入 |
| MB-22 | 生命周期 | 后台→前台、进程被杀恢复、旋转、分屏/折叠 | 恢复前后数据对照 |
| MB-23 | 深链 | 冷/温/热启、未登录、非法 host/参数、重复点击 | `am start`/`simctl openurl` 原文 + 落地页 |
| MB-24 | 推送 | 前台/后台/杀进程、点击路由、去重、权限拒绝 | `simctl push`/FCM 记录 + 落地页 |
| MB-25 | 安装升级 | 全新、覆盖 N-1、降级、强制更新 | 安装命令 + 升级后数据核对 |
| MB-26 | 灰度与回滚 | 比例、停量、回滚旧版 | 轨道截图/后台记录 + 回滚后旧版可用 |
| MB-27 | 弱网 | 离线、2G/3G、弱 WiFi、网络切换 | 档位参数 + 请求/重试日志 |
| MB-28 | 电量与后台 | 低电量、Doze、后台限制 | 设置命令 + 行为变化 |
| MB-29 | 无障碍与显示 | 字体缩放、TalkBack/VoiceOver、RTL、深色 | 逐项 passed/failed/not checked |

## 11. 结论与降级（R-25 不认什么）

- **R-25 不认**：真机装上了 ≠ OS 集成面测过；权限全允许 ≠ 拒绝路径安全；深链能打开 ≠ 入参校验正确；推送能收到 ≠ 点击路由正确；覆盖安装成功 ≠ 数据迁移无损；TestFlight 装过 ≠ 灰度可回滚；弱网能加载 ≠ 弱网体验达标；后台没崩 ≠ 生命周期正确；静态扫描 0 命中 ≠ 无集成缺陷。
- 只有仿真器 → 写「仅仿真验证，未做真机验证」，结论降「待确认」。
- 只测了允许路径 → 写「仅验证授权后主路径，未测拒绝与不再询问，R-25 降级为待确认」。
- 无灰度后台/无回滚操作 → 写「未做灰度回滚验证」，不得写「灰度可控」。
- 每条结论必须能回到本手册 §9/§10 的 ID 与原始输出；对不上就降级。

## 12. 出处与联动

- 规则全文：`references/quality-gates.md` §3A（R-25 行）；报告矩阵：`assets/report-template.md`；矩阵模板：`assets/mobile-app-matrix-template.md`；脚本：`scripts/mobile-audit.py`。
- 选型事实来源：Appium 官方驱动表（`appium driver install uiautomator2|xcuitest|espresso`，appium.io/docs/en/latest/ecosystem/drivers/）；Maestro 命令表（`launchApp`/`setPermissions`/`openLink`/`setAirplaneMode`/`assertVisible`/`extendedWaitUntil`，docs.maestro.dev/reference/commands-available）；Apple / Android 平台命令以本机 SDK 的 `--help` / `simctl help` / `adb help` 输出为准。
- **版本敏感**：命令参数、权限状态机细节、商店审核规则随 OS 与商店政策变化；本手册给的是「必须验证的面」，具体命令执行前先在本机复核（跑 `--help` 并把输出留进证据）。
