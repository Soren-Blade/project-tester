# 桌面应用进程边界与分发（R-26）

**桌面端最贵的 bug 不在业务逻辑里，而在「配置声称的边界」与「运行时真实的边界」之间。** 测试要做的是把这条缝撕开：配置写 `sandbox: true` 不等于生效，签名验证通过不等于没有漏洞，更新成功一次不等于更新可信。

> **适用**：Electron / Tauri 及其它「WebView 壳 + 本地能力 + 安装包」的桌面应用（含更新器、单实例、深链/文件关联、托盘）。
> **配套**：`assets/desktop-app-matrix-template.md`（矩阵）；`scripts/desktop-audit.py`（静态扫描 + 运行用例）。
> **相关规则**：R-8（跨端真实性）、R-10（开关/配置/灰度）、R-18（上传下载边界）、R-20（错误契约）。
> **与 R-8 的分工**：R-8 管「在哪台机器上跑、覆盖多少终端」；R-26 管「跑起来之后，进程、协议、更新这三条边界是否真的成立」。

## §0 触发条件与不适用

| 场景 | 是否触发 | 说明 |
|---|---|---|
| 有 Electron / Tauri 的打包产物（`.dmg` / `.exe` / `.msi` / `.AppImage` / `.deb`） | ✅ 必做 | 至少测一个**打包后**的制品，dev 模式不算 |
| 有 preload / `contextBridge` / `invoke_handler` / 自定义协议 | ✅ 必做 | 权限边界与 IPC 入参是本手册核心 |
| 有自动更新（`autoUpdater` / `electron-updater` / `tauri-plugin-updater`） | ✅ 必做 | 含签名验证与降级拒绝 |
| 有深链、文件关联、单实例、托盘/菜单 | ✅ 必做 | 入口参数一律视为不可信输入 |
| 纯 Web 部署（无本地安装包） | ❌ 不适用 | 报告写「不适用：无桌面安装包与本地进程边界」 |
| CLI / 库 / 纯静态页 | ❌ 不适用 | 同上，不要把浏览器测试冒充桌面测试 |
| 只有 `npm run dev` / `tauri dev`，从未打包 | ◐ 降级 | 只能覆盖 §5/§6 的一部分；§7 更新、§8 单实例、签名与公证一律写「待确认」 |
| 浏览器扩展 / PWA | ◐ 不适用 | 另立场景；本手册的进程模型不成立 |

## §1 先问 8 个契约问题

1. **主进程暴露给渲染进程的 API 清单是什么？** 每个 API 的入参由谁校验？——没有清单就无法判断攻击面。
2. **渲染进程加载的是打包内的本地页面，还是任何远程 URL？** 远程内容是否可能经由重定向、`<webview>`、广告位进入？——远程内容 + Node 能力 = 远程代码执行。
3. **本地能读写的路径范围是什么？谁决定的？** 能否用 `../`、符号链接、UNC、编码绕写逃出去？——路径校验是桌面端最高频的真实漏洞。
4. **自动更新的信任根是什么？** 签名公钥/证书在哪、更新源是谁、能否降级、断网/断点续传失败怎么办？——更新通道本身就是一条提权通道。
5. **单实例与深链/文件关联的入口参数如何校验？** 第二次启动会发生什么、参数被转发给谁？——攻击者只需诱导用户点一个链接。
6. **崩溃/被杀/升级中断后，用户数据与许可状态如何恢复？** 有没有安全模式、有没有备份、回滚后旧数据能否读？——桌面应用最常见的投诉是「升级后打不开」。
7. **三个平台各自发布哪些制品？签名与公证在哪一步完成？** 未签名/未公证在 Gatekeeper 与 SmartScreen 下分别是什么表现？——分发信任是发布门槛。
8. **特权操作（文件、shell、注册表、摄像头、麦克风、剪贴板）由谁触发？** 如何确认是用户意图而不是渲染进程伪造？——权限弹窗与 IPC 之间必须有可验证的因果关系。

> 八问有一问答不出，报告只能写「未确认」，不得写「桌面端安全」。

## §2 框架与工具选型矩阵

| 方案 | 最适合 | 优势 | 代价 / 边界 | 证据强度 | 典型失真 |
|---|---|---|---|---|---|
| Playwright + Electron（`_electron.launch`） | 主流程 E2E、窗口/菜单、主进程 `evaluate` | 真实 Electron、可同时拿到主/渲染两侧 | 常跑未打包源码；版本耦合 | 中 | dev 模式自带调试口，会把「可 require」当成正常 |
| WebdriverIO + Electron service | CI 跨平台回归 | 与 WDIO 生态一致 | 配置重、升级易断 | 中 | 只覆盖窗口内，不覆盖安装器与托盘 |
| Spectron | —— | —— | **已停止维护，不要选** | 无 | 旧博客仍在推荐，属于过期信息 |
| Tauri：`tauri-driver` + Selenium/WebdriverIO（WRY） | Tauri 窗口内 WebView | 官方路径、可跨平台 | 只覆盖 WebView；Rust 命令、托盘、安装器另测 | 中 | 把 WebView 通过当成整个应用通过 |
| 原生 UI 自动化（WinAppDriver / Appium Windows、macOS XCUITest / Accessibility） | 菜单、托盘、文件对话框、安装器 | 能触达 WebView 之外的系统面 | 脚本脆弱、依赖真机与辅助权限 | 中高 | 选择器随系统语言变化 |
| 签名/安装器命令行（`codesign` / `spctl` / `stapler` / `signtool` / `osslsigncode`） | 分发信任链 | 命令 + 退出码，可复核 | 只证明签名与公证状态，不证明代码安全 | 高（但窄） | 把「签名有效」写成「应用安全」 |
| 人工检查清单（fuses、capabilities、CSP） | 配置面收口 | 快、可截图留证 | 不覆盖运行时；易漏改 | 低-中 | 只看配置文件就下结论 |

**选型纪律**：
1. 至少一条路径必须跑**打包后的制品**；`npm run dev` 的结论只能标注为「开发模式结论」。
2. 边界类结论必须来自「渲染进程发起 → 主进程记录/拒绝」的**双侧证据**，单侧截图不算。
3. 同一结论不跨框架混用：Playwright 的窗口结论不能外推到安装器，`codesign` 的结论不能外推到业务。

## §3 执行环境：能证明什么、不能证明什么

| 环境 | 能证明 | 不能证明 | 报告写法 |
|---|---|---|---|
| 源码 dev（`npm run dev` / `tauri dev`） | 业务 UI、部分 IPC 行为 | 打包后的权限、CSP、asar、签名、更新 | 「dev 模式验证，发布形态未验证」 |
| 打包未签名 | 安装、启动、基本流程、单实例 | Gatekeeper / SmartScreen、公证、更新验签 | 「未签名包，分发面待确认」 |
| 已签名 + 已公证 | 分发信任链、更新验签、Keychain 类 API | 业务正确性、权限边界 | 与业务结论分开写，不得合并成一句「通过」 |
| CI 无桌面会话 | 构建、签名、静态扫描、部分 headless E2E | 托盘、菜单、多显示器、休眠唤醒、文件对话框 | 「无 GUI 会话，交互面未测」 |
| 只测一个平台 | 该平台 | 另外两个平台 | 逐平台一行，禁止「跨平台已验证」 |

> 环境标注是硬要求：同一份报告里出现「桌面端通过」但没有平台与制品形态，判为证据不足。

## §4 进程与权限边界（核心）

Electron 的模型是 **main / preload / renderer** 三层；Tauri 是 **Rust core / WebView**。测试要验证的是「渲染侧拿不到它不该拿到的东西」。

| 配置 | 安全值 | 关掉的后果 | 最低验证动作 |
|---|---|---|---|
| `nodeIntegration` | `false` | 渲染进程可直接 `require('child_process')` | devtools 里 `typeof require` 应为 `undefined` |
| `contextIsolation` | `true`（Electron 12+ 默认） | preload 与页面共享全局对象，原型污染可提权；**关它会连带关 sandbox** | `window.process`、`window.electron` 应为 `undefined` |
| `sandbox` | `true`（Electron 20+ 默认） | 渲染进程获得更多系统调用面 | `process.sandboxed` 为 `true`（打包后验证） |
| `webSecurity` | `true` | 关闭同源策略，且等同 `allowRunningInsecureContent` | 页面内跨源 `fetch` 应被 CORS 拦 |
| 远程内容 | 禁止进入带 Node 能力的窗口 | 远程页面 = 本地权限 | 用 `will-navigate` / `setWindowOpenHandler` 实测拦截 |
| `<webview>` | 不加 `allowpopups`，显式 `preload` | 子窗口获得额外能力 | 点开 webview 内链接，看是否弹独立窗口 |
| 权限请求 | `ses.setPermissionRequestHandler` 显式拒绝 | 摄像头/麦克风/通知静默放行 | 页面 `getUserMedia` 应被拒且无系统弹窗 |

**preload 只暴露白名单**：

```js
// 反例：把整个 ipcRenderer 交出去，等于把主进程所有 handler 交给页面
contextBridge.exposeInMainWorld('ipcRenderer', ipcRenderer)

// 正例：只暴露具体函数，参数在主进程再校验一次
contextBridge.exposeInMainWorld('api', {
  readNote: (id) => ipcRenderer.invoke('note:read', String(id)),
})
```

**测试动作（每条都要有拒绝路径）**：在渲染进程控制台执行 `typeof require`、`typeof process`、`window.electron`，记录返回值；尝试 `fetch('file:///etc/passwd')`（Windows 用 `file:///C:/Windows/win.ini`）；尝试 `window.open('https://example.com')` 与 `location.href = 'https://example.com'`，确认分别被 `setWindowOpenHandler` 与 `will-navigate` 拦截。只有「允许路径成功」不算边界成立。

**Tauri 的等价物是 capabilities**：

- 文件在 `src-tauri/capabilities/*.json`；**目录内所有 capability 默认自动启用**，一旦 `tauri.conf.json app.security.capabilities` 显式列出，构建时只保留列出的那些。
- 多个 capability 命中同一窗口时权限**取并集**——这是最容易漏的放大面。
- 默认**所有 `invoke_handler` 注册的命令对所有窗口可用**；收窄要在 `build.rs`：

```rust
fn main() {
    tauri_build::try_build(
        tauri_build::Attributes::new()
            .app_manifest(tauri_build::AppManifest::new().commands(&["note_read"])),
    ).unwrap();
}
```

逐条检查 `"windows": ["*"]`、`fs:default`、`shell:default`、`process:default`、`allow-home-read-extended` 这类过宽写法；每个能力都要回答「哪个窗口、哪个用户动作、需要它做什么」。

## §5 IPC / 命令入参校验

**危险模式的共同点**：把渲染进程传来的字符串直接拼进文件路径、shell、SQL、URL。

```js
// 反例：路径穿越 + 任意文件读
ipcMain.handle('note:read', (e, name) => fs.readFileSync(path.join(DIR, name), 'utf8'))

// 正例：resolve + 前缀白名单 + realpath，再校验 sender
ipcMain.handle('note:read', (event, name) => {
  if (!isTrustedFrame(event.senderFrame)) throw new Error('untrusted sender')
  const p = fs.realpathSync(path.resolve(DIR, String(name)))
  if (p !== DIR && !p.startsWith(DIR + path.sep)) throw new Error('path escape')
  return fs.readFileSync(p, 'utf8')
})
```

- **校验 sender**：WebView / 多窗口共享同一个 `ipcMain`，不校验 `event.senderFrame` 的 origin，等于任何窗口都能调特权命令。
- **Tauri**：`#[tauri::command]` 参数用结构体 + `#[serde(deny_unknown_fields)]`；路径参数 `PathBuf` 后 `canonicalize` 再比对 scope；不要 `format!` 拼 shell 命令。
- **`shell.openExternal`** 只接受写死的 https 白名单，绝不接变量；`file://`、`smb://`、`javascript:` 一律拒绝。

| 输入 | 期望 | 证据 |
|---|---|---|
| `../../etc/passwd` / `..\..\Windows\win.ini` | 拒绝，且日志记录尝试 | 主进程日志 + 渲染侧错误 |
| 绝对路径 `C:\Windows\win.ini` / `/etc/shadow` | 拒绝（不在白名单根内） | 同上 |
| 符号链接指向根外 | 拒绝（`realpath` 后判定） | 准备链接 + 返回值 |
| 编码绕写 `%2e%2e%2f`、`%252e`、UTF-8 变体 | 拒绝（解码后再规范化） | 请求原文 + 响应 |
| 深链参数 `myapp://open?url=file:///...` | 拒绝非 http(s) 目标 | 深链命令 + 落地日志 |
| 文件关联：双击内容含 `; rm -rf` 的 `.foo` | 不执行、转义、可正常打开 | 样本文件 + 进程树 |

> 判据：至少 1 条「越权被拒」的原始返回或日志，配 1 条「合法读取成功」的对照。只有后者 = 未测边界。

## §6 导航、新窗口与本地内容

- 主进程必须设置 `will-navigate` 白名单与 `setWindowOpenHandler`（默认 `{action: 'deny'}`）；只放行 https 且再走 `shell.openExternal` 白名单。
- 自定义协议：`protocol.handle('app', ...)` 必须把 URL 映射到固定目录，拒绝 `..`、绝对路径、编码变体；先 `decodeURIComponent` 再 `path.normalize`，再前缀校验。
- 尽量不用 `file://` 加载应用页；必须用时，关掉 `grantFileProtocolExtraPrivileges` fuse，并确认没有「file 页面可 fetch 任意本地文件」。
- **CSP**：Electron 用 `session.defaultSession.webRequest.onHeadersReceived` 注入，或页面 `<meta http-equiv="Content-Security-Policy">`；Tauri 用 `app.security.csp`。底线：`script-src 'self'`，不出现 `unsafe-inline` / `unsafe-eval` / `*`。
- 验证：在本地页注入 `<img src=x onerror="fetch('http://127.0.0.1:PORT/steal')">`，CSP 应拦截并在 console 留下报错原文；`fetch` 到本地回环端口应被 CSP `connect-src` 拦。

## §7 自动更新、签名与公证

更新是**唯一一条由厂商主动推送代码到用户机器的通道**，它的信任根必须可验证。

| 检查项 | 命令 / 证据 | 判据 |
|---|---|---|
| macOS 签名 | `codesign -dv --verbose=4 Foo.app` | `Authority=Developer ID Application: ...`，非 `adhoc` |
| macOS 公证 | `spctl -a -vv Foo.app`、`xcrun stapler validate Foo.app` | `accepted`、`source=Notarized Developer ID`；`stapler` 成功 |
| Windows 签名 | `signtool verify /pa /v Foo.exe` | `Successfully verified`；2023-06 起普通 OV 证书被当未签名，需 EV |
| Electron fuses | `npx --yes @electron/fuses read --app Foo.app` | `RunAsNode`/`NodeCliInspect` 关；`OnlyLoadAppFromAsar`、`EmbeddedAsarIntegrityValidation` 开 |
| Tauri 更新签名 | `tauri.conf.json` 的 `plugins.updater.pubkey` 非空、`endpoints` 是 https | 空 pubkey = 更新包不验签 |
| 降级拒绝 | 把旧版本包塞给更新器 | 应拒绝并记录；若产品明确允许降级，须在报告写「允许降级，风险已确认」 |
| 更新中断 | 下载中断、磁盘满、替换失败、杀进程 | 旧版本仍能启动，或明确报错；不得黑屏/配置损坏 |

- **签名只证明来源与完整性，不证明代码安全**；被正确签名的 XSS 仍是 XSS。反之未签名也不等于一定被拦（视 Gatekeeper/SmartScreen 策略与用户操作），这类写「待实测」，不要断言。
- macOS 上 `safeStorage`、`app.setLoginItemSettings()`、`cookieEncryption`、`autoUpdater`（Squirrel.Mac）都**依赖有效签名**；未签名时表现为 Keychain 反复弹窗、登录项静默失败、更新完全不工作——这些要单独列为「签名缺失的连带故障」。

## §8 单实例、深链、文件关联、托盘

- **单实例**：Electron `app.requestSingleInstanceLock()` + `second-instance`；Tauri `tauri-plugin-single-instance`。缺了它，双开会同时写同一个 SQLite / 配置目录，导致数据损坏或「许可证翻倍消耗」。
- **深链**：`setAsDefaultProtocolClient` 注册后，参数一律按 §5 当不可信输入；冷启动（进程未起）与温启动（进程已起）要分别测。
- **文件关联**：安装器负责注册；双击文件路径必须 canonicalize 并校验扩展名白名单，不能把文件名拼进 shell。
- **托盘 / 菜单**：优先用内置 `role`；自定义回调里不做特权操作；明确「关窗口 = 退出还是驻留」，并在两个平台分别验证进程真的退出（Windows `tasklist | findstr Foo`，macOS `pgrep -fl Foo`）。
- **验证**：同时启动两个实例 → 只有一个窗口，第二个实例的参数被转发；从 Finder/Explorer 拖文件到窗口与双击文件各测一次；托盘退出后进程消失。

## §9 崩溃、休眠、回滚与数据

| 场景 | 必测动作 | 判据 |
|---|---|---|
| 渲染进程崩溃 | 任务管理器结束渲染进程 / `render-process-gone` | 窗口可恢复或给出重试；未保存数据有提示 |
| 主进程崩溃 | `kill -9` / 任务管理器结束主进程 | 下次启动可恢复；崩溃日志落盘且含版本号 |
| 休眠唤醒 / 锁屏 | 合盖 10 分钟再打开 | token 刷新、WebSocket 重连、定时任务不重复 |
| 升级后首次启动 | 覆盖安装新版本 | 旧配置/旧数据可读；迁移失败有回退路径 |
| 回滚 | 装回上一版本 | 数据向后兼容或明确不兼容；有真实执行记录 |
| 卸载 | 卸载后残留检查 | 用户数据按产品声明保留或清除；不留孤儿进程/计划任务 |

> 崩溃恢复不能靠「看起来没事」：要给出重启后打开的截图/日志，以及数据前后对比。

## §10 静态反模式 DT-01 ~ DT-10

静态扫描只报「代码形态可疑」，每条命中必须逐条裁决（真缺陷 / 误报原因 / 不适用原因），不得只贴数量。

| ID | 反模式 | 为什么是风险 | 典型误报 |
|---|---|---|---|
| DT-01 | `nodeIntegration: true`（含 Worker/SubFrames） | 渲染进程获得 Node，远程内容即可执行系统命令 | 本地纯离线工具且从不加载远程内容——仍需裁决并留证 |
| DT-02 | `contextIsolation: false` / `sandbox: false` | 隔离失效，原型污染可跨上下文提权；关隔离会连带关沙箱 | 旧版 Electron 的历史兼容代码，需确认发布版本已升级 |
| DT-03 | `webSecurity: false` / `allowRunningInsecureContent: true` | 关闭同源策略，任意页面可读跨源响应 | 仅测试构建可接受，但不得进入发布制品 |
| DT-04 | preload 暴露整个 `ipcRenderer`/`require`/`process` | 页面可调用主进程全部 handler | 变量名恰好叫 `api` 但内部是白名单函数——看实现不看名字 |
| DT-05 | IPC handler 用入参直接拼路径/shell，且无 sender 校验 | 路径穿越、任意命令执行 | 参数是枚举值或已在上层强校验 |
| DT-06 | `shell.openExternal(` 接变量 | 攻击者可打开 `file://`、`smb://`、恶意协议 | 变量来自配置白名单且已校验 |
| DT-07 | 导航/新窗口无限制或显式 `action: 'allow'` | 应用窗口被导航到远程页面，继承本地权限 | 只放行固定 https 域名且另有 CSP |
| DT-08 | CSP 缺失 / `unsafe-inline` / `unsafe-eval` / `*` | XSS 可执行任意脚本，进而调 preload API | 仅 dev 生效、生产由响应头覆盖——需给生产响应头证据 |
| DT-09 | 更新未验签 / 允许降级 / 明文 http 更新源 | 更新通道可被劫持或替换为旧版漏洞 | 企业内网签名网关另行校验——需给网关证据 |
| DT-10 | 权限面过宽：capability `windows:["*"]` + `fs:default`、assetProtocol 裸 `**` 或 `requireLiteralLeadingDot:false`、file 协议额外特权 | 任意窗口读写任意路径，隐藏文件暴露 | 只读资源目录且 deny 覆盖敏感路径——看 deny 是否真的生效 |

> 扫描器报 `无法核对` 的条目（如「有 `ipcMain.handle` 但看不到校验函数」）不是通过项，要在矩阵里写清「缺什么证据才能判」。

## §11 运行矩阵 DT-20 ~ DT-29

每条都要有「做 / 未做 + 证据位置」；未做就写未做，不得留空当通过。

| ID | 面 | 必测动作 | 最低证据 |
|---|---|---|---|
| DT-20 | 进程边界 | 打包制品里查 `typeof require` / `process` / `window.electron` | devtools 截图 + 返回值 |
| DT-21 | IPC 校验 | 路径穿越 + 非法 sender 各 1 条 | 主进程拒绝日志 + 渲染侧返回 |
| DT-22 | 导航与新窗口 | 注入远程链接、`window.open`、`<a target=_blank>` | 拦截日志 + 截图 |
| DT-23 | CSP 与本地内容 | 注入 inline script / onerror，观察 console | CSP 报错原文 + 请求被拦记录 |
| DT-24 | 更新验签 | `codesign` / `spctl` / `signtool` / fuses read 输出 | 命令 + 退出码 + 关键行 |
| DT-25 | 安装升级回滚 | 覆盖安装、降级、卸载各 1 次 | 版本号 + 数据 diff + 残留检查 |
| DT-26 | 单实例与深链 | 双开 + 冷/温启动深链 + 文件关联 | 进程列表 + 转发日志 |
| DT-27 | 崩溃恢复 | 结束渲染/主进程后重启 | 重启截图 + 数据前后对比 |
| DT-28 | 本地协议/路径 | `..`、绝对路径、编码绕写、符号链接 | 请求原文 + 响应/拒绝日志 |
| DT-29 | 跨平台 | Windows/macOS/Linux 各跑本表至少 3 条 | 逐平台一行，标注制品与签名状态 |

**命令参考**（执行前本机复核，留 `--help` 输出）：

```bash
# Electron fuses（打包后）
npx --yes @electron/fuses read --app "/Applications/Foo.app"

# macOS 签名 / 公证 / 启动校验
codesign -dv --verbose=4 "Foo.app"
spctl -a -vv "Foo.app"
xcrun stapler validate "Foo.app"

# Windows 签名
signtool verify /pa /v "Foo.exe"

# 进程真的退出了吗
tasklist | findstr /i foo        # Windows
pgrep -fl "Foo|foo"              # macOS / Linux
```

## §12 结论与降级（R-26 不认什么）

- **dev 模式跑通 ≠ 发布形态可用**：打包后 asar、fuses、CSP、签名都可能变。
- **配置里写了 `sandbox: true` ≠ 运行时生效**：要在打包制品里读 `process.sandboxed`。
- **签名/公证通过 ≠ 没有漏洞**：它只证明来源与完整性。
- **只有允许路径 ≠ 边界成立**：每条特权 API 必须有拒绝路径的实测。
- **一个平台通过 ≠ 三平台通过**：签名、SmartScreen、Gatekeeper 各自独立。
- **静态扫描 0 命中 ≠ 无风险**：扫描器只认已知形态，`无法核对` 项必须进矩阵。
- **更新成功一次 ≠ 更新可信**：要验签 + 拒绝降级 + 中断可恢复。
- **「自动更新已开启」≠「用户不会被降级」**：看是否允许降级、更新源是否 https。

**三条降级句式**：
1. 只在 dev 模式测过 → 全部结论降为「待确认」，分销面写「未验证」。
2. 只测了允许路径 → 该边界写「未验证拒绝路径」，不得写「边界成立」。
3. 没有回滚执行记录 → 不得写「可回滚」。

> 每条结论必须能回到本手册 §10 / §11 的 ID 与原始输出；对不上就降级。

## §13 出处与联动

- **规则全文**：`SKILL.md` 的 R-26 行（证据要求栏）
- **报告矩阵**：`assets/report-template.md`（R-26 行）
- **矩阵模板**：`assets/desktop-app-matrix-template.md`
- **扫描脚本**：`scripts/desktop-audit.py`（`scan` / `matrix` / `cases` / `--self-test`）

事实来源（官方文档）：

- Electron Security Checklist：https://www.electronjs.org/docs/latest/tutorial/security
- Electron Fuses：https://www.electronjs.org/docs/latest/tutorial/fuses
- Electron Code Signing：https://www.electronjs.org/docs/latest/tutorial/code-signing
- Electron Process Model：https://www.electronjs.org/docs/latest/tutorial/process-model
- Tauri Capabilities：https://v2.tauri.app/security/capabilities/
- Tauri Asset Protocol Scope：https://v2.tauri.app/security/asset-protocol/
- Tauri Updater：https://v2.tauri.app/plugin/updater/
- Tauri Single Instance：https://v2.tauri.app/plugin/single-instance/
- Tauri macOS Signing：https://v2.tauri.app/distribute/sign/macos/

**版本敏感**：`contextIsolation` / `sandbox` 的默认值随 Electron 大版本变化（12 / 20）；Windows 自 2023-06 起要求 EV 证书；Tauri 2.x 的 capability 与 plugin 配置在 minor 版本间有增删。执行前在本机复核，并保留命令 `--help` 输出与版本号。
