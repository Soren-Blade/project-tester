#!/usr/bin/env python3
"""mobile-audit.py — 移动 App 操作系统集成面：静态扫描 + 运行矩阵 + 命令清单（R-25）。

零依赖（仅标准库），不联网、不启动模拟器、不运行被测 App。

用法：
  python scripts/mobile-audit.py scan <repo> [--format table|json|markdown] [--include-docs] [--fail-on-gap]
  python scripts/mobile-audit.py matrix [--format markdown]
  python scripts/mobile-audit.py cases [--platform android|ios|all]
  python scripts/mobile-audit.py --self-test

输出约定：
  - 每条命中都是「待人工裁决的线索」，裁决写进 assets/mobile-app-matrix-template.md §8。
  - 退出码：0 = 扫描完成；1 = 有命中且带 --fail-on-gap；2 = 路径不存在。

边界（诚实声明）：
  - 只做静态文本匹配：不联网、不运行 App、不读二进制/资源包/加密产物、不做逆向。
  - 命中不证明存在漏洞（可能是误报）；0 命中也不证明无缺陷（漏报随技术栈变化）。
  - MB-03 依赖清单存在性；清单缺失时只报「无法核对」，不冒充通过。
  - 本脚本不代填结论、不判 Go/No-Go；Go/No-Go 由 R-25 与人工裁决给。
"""

import argparse
import json
import os
import re
import sys
import tempfile

try:  # Windows 控制台默认可能是 cp936，避免中文输出崩掉
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SKIP_DIRS = {
    "node_modules", "build", "dist", "Pods", "DerivedData", "__pycache__",
    "venv", ".venv", "coverage", "vendor", "gradle", "bower_components",
}
CODE_EXTS = {".kt", ".kts", ".java", ".swift", ".m", ".mm", ".js", ".jsx", ".ts", ".tsx", ".dart"}
CONFIG_EXTS = {".xml", ".plist", ".yaml", ".yml", ".gradle", ".json"}
DOC_EXTS = {".md", ".txt"}
ANDROID_CODE = {".kt", ".kts", ".java"}
IOS_CODE = {".swift", ".m", ".mm"}

# ---------------------------------------------------------------- 规则（MB-01~MB-10）

RE_COORD = re.compile(
    r"(?i)(?:tapAt|tapCoordinate|byCoordinate|clickAt|coordinate)\s*\(\s*\d+\s*,"
    r"|tapAt\s*\(\s*(?:const\s+)?Offset\(\s*\d+"
    r"|\.tap\(\s*\d+\s*,"
    r"|point\s*:\s*['\"]?\d+%?\s*,\s*\d+%?"
)
RE_SLEEP = re.compile(r"(?:Thread\.sleep|time\.sleep|(?<![A-Za-z_.])sleep|setTimeout)\s*\(\s*[\w.]+\s*\)")
RE_FLUTTER_SLEEP = re.compile(r"Future\.delayed\s*\(\s*(?:const\s+)?Duration|(?<![A-Za-z_.])delay\s*\(\s*\d+\s*\)")
RE_YAML_SLEEP = re.compile(r"^\s*-\s*sleep:\s*\S")
WAIT_MARKERS = (
    "waitFor", "assertVisible", "extendedWaitUntil", "IdlingResource",
    "waitForAnimationToEnd", "waitUntil", "eventually", "toAppear",
    "pumpAndSettle", "pump(",
)
RE_JS_ANDROID = re.compile(r"setJavaScriptEnabled\s*\(\s*true\s*\)")
RE_JS_IOS = re.compile(r"javaScriptEnabled\s*=\s*true")
RE_GETDATA = re.compile(r"getData\(\)")
RE_FLUTTER_DEEPLINK = re.compile(r"getInitialLink\(\)|getInitialUri\(\)|onAppLink\b")
RE_SWIFT_OPENURL = re.compile(r"open url:\s*URL")
RE_CLEARTEXT = re.compile(r"usesCleartextTraffic\s*=\s*['\"]true['\"]")
RE_HTTP = re.compile(r"http://[^\s\"'<>)]+")
HTTP_ALLOW = ("localhost", "127.0.0.1", "0.0.0.0", "10.0.2.2", "schemas.android.com", "w3.org")
RE_EXPORTED = re.compile(r"android:exported\s*=\s*['\"]true['\"]")
RE_SECRET = re.compile(
    r"(?i)\b(api[_-]?key|secret|client[_-]?secret|access[_-]?token|password)\b\s*[:=]\s*[\"'][^\"']{12,}[\"']"
)
RE_AWS = re.compile(r"AKIA[0-9A-Z]{16}")
RE_SK = re.compile(r"\bsk-[A-Za-z0-9]{20,}")
RE_UPDATE_LIB = re.compile(r"react-native-code-push|expo-updates|ota_update|sparkle|autoUpdater|flutter_downloader")
RE_UPDATE_VERIFY = re.compile(r"verify|signature|publicKey|public_key|checksum", re.I)
RE_ALWAYS_ALLOW = re.compile(r"(?i)(autoGrantPermissions|autoAcceptAlerts|autoDismissAlerts)['\"]?\s*[:=]\s*true")
RE_ATS = re.compile(r"NSAllowsArbitraryLoads</key>\s*<true\s*/?>")
PLACEHOLDER = ("your_", "your-", "xxx", "example", "dummy", "placeholder", "changeme", "<", "test_", "fake")

# MB-03：API 使用 → 必须声明的权限/用途描述（含 Flutter permission_handler 的 Dart 调用）
PERM_CHECKS = [
    ("相机", r"CameraManager|CameraX|CameraDevice|AVCaptureDevice|Permission\.camera",
     "android.permission.CAMERA", "NSCameraUsageDescription"),
    ("定位", r"FusedLocationProvider|LocationManager|LocationRequest|CLLocationManager|Permission\.location",
     "android.permission.ACCESS_FINE_LOCATION", "NSLocationWhenInUseUsageDescription"),
    ("麦克风", r"AudioRecord|MediaRecorder|AVAudioRecorder|AVAudioEngine|Permission\.microphone",
     "android.permission.RECORD_AUDIO", "NSMicrophoneUsageDescription"),
    ("通知", r"NotificationManagerCompat|NotificationCompat|Permission\.notifications",
     "android.permission.POST_NOTIFICATIONS", None),
]

MATRIX = [
    ("MB-20", "权限状态机", "允许 / 拒绝 / 不再询问 / 设置撤销 四态全走", "四段录屏或截图 + 降级文案"),
    ("MB-21", "系统中断", "来电、通知横幅、低电量弹窗、系统更新提示", "中断前后状态截图 + 是否丢输入"),
    ("MB-22", "生命周期", "后台→前台、进程被杀恢复、旋转、分屏/折叠", "恢复前后数据对照"),
    ("MB-23", "深链", "冷/温/热启、未登录、非法 host/参数、重复点击", "am start / simctl openurl 原文 + 落地页"),
    ("MB-24", "推送", "前台/后台/杀进程、点击路由、去重、权限拒绝", "simctl push / FCM 记录 + 落地页"),
    ("MB-25", "安装升级", "全新、覆盖 N-1、降级、强制更新", "安装命令 + 升级后数据核对"),
    ("MB-26", "灰度与回滚", "比例、停量、回滚旧版", "轨道记录 + 回滚后旧版可用"),
    ("MB-27", "弱网", "离线、2G/3G、弱 WiFi、网络切换", "档位参数 + 请求/重试日志"),
    ("MB-28", "电量与后台", "低电量、Doze、后台限制", "设置命令 + 行为变化"),
    ("MB-29", "无障碍与显示", "字体缩放、TalkBack/VoiceOver、RTL、深色", "逐项 passed/failed/not checked"),
]

CASES = {
    "android": [
        ("权限查询", 'adb shell dumpsys package <pkg> | findstr <permission>'),
        ("权限撤销", "adb shell pm revoke <pkg> android.permission.CAMERA"),
        ("清数据（是否重置权限需实测）", "adb shell pm clear <pkg>"),
        ("深链冷启", 'adb shell am start -W -a android.intent.action.VIEW -d "myapp://order/42" <pkg>'),
        ("强杀进程", "adb shell am force-stop <pkg>"),
        ("覆盖安装", "adb install -r app-release.apk"),
        ("允许降级", "adb install -r -d app-release.apk"),
        ("低电量", "adb shell dumpsys battery set level 5"),
        ("Doze", "adb shell dumpsys deviceidle force-idle"),
        ("关闭动画（测卡顿须恢复 1.0）", "adb shell settings put global animator_duration_scale 0"),
        ("弱网（模拟器启动参数）", "emulator -netdelay gprs -netspeed gsm"),
    ],
    "ios": [
        ("打开深链", 'xcrun simctl openurl booted "myapp://order/42"'),
        ("重置隐私授权", "xcrun simctl privacy booted reset all <bundle>"),
        ("注入推送", "xcrun simctl push booted <bundle> payload.apns"),
        ("状态栏（时间/电量/信号）", 'xcrun simctl status_bar booted override --time "9:41" --batteryLevel 20 --cellularBars 1'),
        ("终止进程", "xcrun simctl terminate booted <bundle>"),
        ("安装", "xcrun simctl install booted MyApp.app"),
        ("卸载（全新安装前）", "xcrun simctl uninstall booted <bundle>"),
        ("启动并输出日志", "xcrun simctl launch --console booted <bundle>"),
    ],
}


def _collect(path, include_docs):
    exts = CODE_EXTS | CONFIG_EXTS | (DOC_EXTS if include_docs else set())
    if os.path.isfile(path):
        return [os.path.basename(path)], [os.path.abspath(path)]
    rels, abss = [], []
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in exts:
                full = os.path.join(dirpath, fn)
                rels.append(os.path.relpath(full, path).replace(os.sep, "/"))
                abss.append(os.path.abspath(full))
    return rels, abss


def _testish(rel):
    low = rel.lower()
    if os.path.splitext(low)[1] in (".yaml", ".yml"):
        return any(k in low for k in ("flow", "test", "e2e", "maestro", "ui"))
    return any(k in low for k in ("test", "spec", "e2e", "flow", "maestro", "uitest"))


def _line_of(text, needle):
    for i, ln in enumerate(text.splitlines(), 1):
        if needle in ln:
            return i
    return 1


def _enclosing_tag(text, pos):
    """返回 pos 所在的 XML 起始标签（含属性）。跨行标签也能取到；不处理引号内的 '>'。"""
    start = text.rfind("<", 0, pos)
    if start < 0:
        return ""
    end = text.find(">", pos)
    return text[start:end + 1] if end > start else text[start:]


def scan_path(path, include_docs=False):
    rels, abss = _collect(path, include_docs)
    findings = []
    seen = set()
    texts = {}
    for rel, full in zip(rels, abss):
        try:
            with open(full, encoding="utf-8", errors="ignore") as fh:
                texts[rel] = fh.read()
        except OSError:
            continue
    android_text = "\n".join(t for r, t in texts.items() if os.path.splitext(r)[1].lower() in ANDROID_CODE)
    ios_text = "\n".join(t for r, t in texts.items() if os.path.splitext(r)[1].lower() in IOS_CODE)
    dart_text = "\n".join(t for r, t in texts.items() if os.path.splitext(r)[1].lower() == ".dart")
    android_usage = android_text + "\n" + dart_text
    ios_usage = ios_text + "\n" + dart_text
    manifests = [r for r in texts if os.path.basename(r) == "AndroidManifest.xml"]
    plists = [r for r in texts if os.path.basename(r) == "Info.plist"]
    manifest_text = "\n".join(texts[m] for m in manifests)
    plist_text = "\n".join(texts[p] for p in plists)

    def add(rule, rel, line, evidence, kind="违规"):
        key = (rule, rel, line)
        if key in seen:
            return
        seen.add(key)
        findings.append({
            "rule": rule, "file": rel, "line": line,
            "evidence": evidence.strip()[:140], "kind": kind,
        })

    for rel in texts:
        ext = os.path.splitext(rel)[1].lower()
        text = texts[rel]
        raw_lines = text.splitlines(keepends=True)
        lines = [ln.rstrip("\r\n") for ln in raw_lines]
        offsets, acc = [], 0
        for ln in raw_lines:
            offsets.append(acc)
            acc += len(ln)
        has_override = "shouldOverrideUrlLoading" in text
        has_decide = "decidePolicyFor" in text
        has_host = bool(re.search(r"getHost\(\)|\.host\b|host\s*==", text))
        has_swift_host = "url.host" in text
        has_verify = bool(RE_UPDATE_VERIFY.search(text))
        for i, line in enumerate(lines, 1):
            if RE_COORD.search(line):
                add("MB-01", rel, i, line)
            if (_testish(rel) and (RE_SLEEP.search(line) or RE_FLUTTER_SLEEP.search(line) or RE_YAML_SLEEP.search(line))
                    and not any(m in text for m in WAIT_MARKERS)):
                add("MB-02", rel, i, line)
            if ext in ANDROID_CODE and RE_JS_ANDROID.search(line) and not has_override:
                add("MB-04", rel, i, line)
            if ext in IOS_CODE and RE_JS_IOS.search(line) and not has_decide:
                add("MB-04", rel, i, line)
            if RE_GETDATA.search(line) and not has_host:
                add("MB-05", rel, i, line)
            if RE_FLUTTER_DEEPLINK.search(line) and not re.search(r"host\s*==|allowedHosts|allowlist|whitelist", text, re.I):
                add("MB-05", rel, i, line)
            if ext in IOS_CODE and RE_SWIFT_OPENURL.search(line) and not has_swift_host:
                add("MB-05", rel, i, line)
            if RE_CLEARTEXT.search(line):
                add("MB-06", rel, i, line)
            for m in RE_HTTP.finditer(line):
                if not any(a in m.group(0) for a in HTTP_ALLOW):
                    add("MB-06", rel, i, line)
                    break
            if RE_EXPORTED.search(line):
                m = RE_EXPORTED.search(line)
                tag = _enclosing_tag(text, offsets[i - 1] + m.start())
                if not re.search(r"android:permission\s*=", tag):
                    add("MB-07", rel, i, line)
            for rx in (RE_SECRET, RE_AWS, RE_SK):
                m = rx.search(line)
                if m and not any(p in m.group(0).lower() for p in PLACEHOLDER):
                    add("MB-08", rel, i, line)
                    break
            if "AndroidManifest.xml" not in rel and RE_UPDATE_LIB.search(line) and not has_verify:
                add("MB-09", rel, i, line)
            if RE_ALWAYS_ALLOW.search(line):
                add("MB-10", rel, i, line)

        ats = RE_ATS.search(text)
        if ats:
            add("MB-06", rel, _line_of(text, "NSAllowsArbitraryLoads"), "NSAllowsArbitraryLoads = true")

    # MB-03：清单声明缺失 / 无法核对
    for label, pattern, aperm, ikey in PERM_CHECKS:
        if re.search(pattern, android_usage):
            if not manifests:
                add("MB-03", "<no-AndroidManifest>", 1,
                    f"检测到{label}相关 API，但未找到 AndroidManifest.xml，无法核对 {aperm}", "无法核对")
            elif aperm not in manifest_text:
                add("MB-03", manifests[0], 1,
                    f"检测到{label}相关 API，清单未声明 {aperm}（若 targetSdk<33 等版本差异，可人工豁免）", "无法核对")
        if ikey and re.search(pattern, ios_usage):
            if not plists:
                add("MB-03", "<no-Info.plist>", 1,
                    f"检测到{label}相关 API，但未找到 Info.plist，无法核对 {ikey}", "无法核对")
            elif ikey not in plist_text:
                add("MB-03", plists[0], 1,
                    f"检测到{label}相关 API，Info.plist 缺 {ikey}（商店审核与首启崩溃风险）", "无法核对")

    findings.sort(key=lambda f: (f["rule"], f["file"], f["line"]))
    return len(texts), findings


def print_scan(root, files, findings, fmt):
    if fmt == "json":
        print(json.dumps({
            "root": os.path.abspath(root),
            "files_scanned": files,
            "counts": {
                "violations": sum(1 for f in findings if f["kind"] == "违规"),
                "gaps": sum(1 for f in findings if f["kind"] == "无法核对"),
            },
            "findings": findings,
        }, ensure_ascii=False, indent=2))
        return
    if fmt == "markdown":
        print("| 规则 | 位置 | 证据 | 类型 |")
        print("|---|---|---|---|")
        for f in findings:
            ev = f["evidence"].replace("|", "\\|")
            print(f"| {f['rule']} | `{f['file']}:{f['line']}` | `{ev}` | {f['kind']} |")
    else:
        print("规则 | 位置 | 证据 | 类型")
        for f in findings:
            print(f"{f['rule']} | {f['file']}:{f['line']} | {f['evidence'][:100]} | {f['kind']}")
    v = sum(1 for f in findings if f["kind"] == "违规")
    g = len(findings) - v
    print(f"\n扫描 {files} 个文件；命中 {v} 条违规 / {g} 条无法核对。")
    print("提示：命中≠缺陷；逐条裁决写进 assets/mobile-app-matrix-template.md §8；0 命中≠无缺陷。")


def main(argv=None):
    ap = argparse.ArgumentParser(description="移动 App 集成面静态扫描与运行矩阵（R-25）")
    ap.add_argument("--self-test", action="store_true", help="内置自检（GREEN 才可用）")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("scan", help="静态扫描")
    s.add_argument("path")
    s.add_argument("--format", choices=["table", "json", "markdown"], default="table")
    s.add_argument("--include-docs", action="store_true", help="连 .md/.txt 一起扫（默认跳过文档）")
    s.add_argument("--fail-on-gap", action="store_true", help="有命中时 exit 1（门禁用）")
    sub.add_parser("matrix", help="输出 MB-20~MB-29 运行矩阵骨架")
    c = sub.add_parser("cases", help="输出 adb/simctl 命令清单")
    c.add_argument("--platform", choices=["android", "ios", "all"], default="all")

    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.cmd == "scan":
        if not os.path.exists(args.path):
            print(f"路径不存在：{args.path}", file=sys.stderr)
            return 2
        files, findings = scan_path(args.path, args.include_docs)
        print_scan(args.path, files, findings, args.format)
        if args.fail_on_gap and findings:
            return 1
        return 0
    if args.cmd == "matrix":
        print("| ID | 面 | 必测动作 | 最低证据 |")
        print("|---|---|---|---|")
        for rid, title, action, ev in MATRIX:
            print(f"| {rid} | {title} | {action} | {ev} |")
        print("\n缺失项写「未做」，不适用写原因；不得用「基本可用」填空。")
        return 0
    if args.cmd == "cases":
        plats = ["android", "ios"] if args.platform == "all" else [args.platform]
        for p in plats:
            print(f"## {p}")
            for label, cmd in CASES[p]:
                print(f"- {label}：`{cmd}`")
        print("\n参数以本机 `adb help` / `simctl help` / `emulator -help-netdelay` 为准。")
        return 0
    ap.print_help()
    return 0


def self_test():
    """夹具全部在临时目录生成；负向控制：clean 注入 autoGrantPermissions 必须被抓到。"""
    root = tempfile.mkdtemp(prefix="mobile-audit-selftest-")

    def w(rel, body):
        full = os.path.join(root, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(body)

    # 脏夹具：10 条规则都应命中
    w("bad/AndroidManifest.xml", '<manifest xmlns:android="http://schemas.android.com/apk/res/android">'
      '<application><activity android:name=".Main" android:exported="true"/></application></manifest>\n')
    w("bad/app/src/MainActivity.kt",
      "val cm = getSystemService(CameraManager::class.java)\n"
      "webView.settings.setJavaScriptEnabled(true)\n"
      "val data = intent.getData()\n"
      "startActivity(Intent(this, Detail::class.java))\n"
      'val apiKey = "sk-abcdefghijklmnopqrstuvwxyz"\n'
      'val baseUrl = "http://api.prod.internal"\n')
    w("bad/ios/AppDelegate.swift",
      "func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey: Any] = [:]) -> Bool {\n"
      "  let manager = CLLocationManager()\n  return true\n}\n")
    w("bad/ios/Info.plist", "<plist><dict><key>CFBundleIdentifier</key><string>com.example</string></dict></plist>\n")
    w("bad/ui/flows/login.yaml",
      "appId: com.example\n---\n- launchApp\n- sleep: 5000\n- tapOn:\n    point: \"50%, 50%\"\n")
    w("bad/wdio.conf.js", "exports.config = { capabilities: [{ 'appium:autoGrantPermissions': true, "
      "'appium:autoAcceptAlerts': true }] }\n")
    w("bad/package.json", '{"dependencies": {"react-native-code-push": "^7.0.0"}}\n')
    w("bad/docs/notes.md", "- sleep: 5000\nautoGrantPermissions: true\n")
    w("bad/lib/util.kt", "fun pause() { sleep(500) }\n")
    w("bad/integration_test/shop_test.dart",
      "await Future.delayed(const Duration(seconds: 3));\n"
      "await tester.tapAt(const Offset(100, 200));\n"
      "final link = await appLinks.getInitialLink();\n")

    # 干净夹具：0 命中
    w("clean/AndroidManifest.xml",
      '<manifest xmlns:android="http://schemas.android.com/apk/res/android">'
      '<uses-permission android:name="android.permission.CAMERA"/>'
      '<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>'
      '<uses-permission android:name="android.permission.RECORD_AUDIO"/>'
      '<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>'
      '<application><activity android:name=".Main"/>'
      '<service android:name=".Sync" android:exported="true"\n'
      '  android:permission="com.example.shop.BIND_SYNC"/></application></manifest>\n')
    w("clean/app/src/MainActivity.kt",
      "val cm = getSystemService(CameraManager::class.java)\n"
      "val lm = getSystemService(LocationManager::class.java)\n"
      "val rec = MediaRecorder()\n"
      "NotificationCompat.Builder(this, \"ch\").build()\n"
      "webView.settings.setJavaScriptEnabled(true)\n"
      "webView.webViewClient = object : WebViewClient() {\n"
      "  override fun shouldOverrideUrlLoading(v: WebView, u: String) = false\n}\n")
    w("clean/ios/AppDelegate.swift",
      "let manager = CLLocationManager()\nlet cam = AVCaptureDevice.default(for: .video)\n"
      "let rec = try AVAudioRecorder()\n")
    w("clean/ios/Info.plist",
      "<plist><dict>"
      "<key>NSCameraUsageDescription</key><string>camera</string>"
      "<key>NSLocationWhenInUseUsageDescription</key><string>loc</string>"
      "<key>NSMicrophoneUsageDescription</key><string>mic</string>"
      "</dict></plist>\n")
    w("clean/ui/flows/ok.yaml", "appId: com.example\n---\n- launchApp\n- assertVisible: \"Home\"\n- tapOn: \"Login\"\n")
    w("clean/package.json", '{"dependencies": {"react-native-code-push": "^7.0.0"}, '
      '"codePushPublicKey": "abc"}\n')

    files, bad = scan_path(os.path.join(root, "bad"))
    ids = {f["rule"] for f in bad}
    missing = [f"MB-{i:02d}" for i in range(1, 11) if f"MB-{i:02d}" not in ids]
    assert not missing, f"脏夹具漏报：{missing}；实际 {sorted(ids)}"
    dart_ids = {f["rule"] for f in bad if f["file"].endswith("shop_test.dart")}
    assert {"MB-01", "MB-02", "MB-05"} <= dart_ids, f"Flutter 夹具漏报：{sorted(dart_ids)}"
    assert any(f["file"].endswith("util.kt") for f in bad) is False, "非测试文件 sleep 被误报（MB-02）"
    assert all("docs/notes.md" not in f["file"] for f in bad), "默认扫描不应包含 .md 文档"

    _, bad_docs = scan_path(os.path.join(root, "bad"), include_docs=True)
    assert any("docs/notes.md" in f["file"] for f in bad_docs), "--include-docs 未生效"

    # 回归：Flutter permission_handler 只在 Dart 里申请权限，也必须触发 MB-03
    w("dartonly/AndroidManifest.xml", '<manifest xmlns:android="http://schemas.android.com/apk/res/android">'
      '<application><activity android:name=".Main"/></application></manifest>\n')
    w("dartonly/lib/perm.dart", "final status = await Permission.camera.request();\n")
    _, dart_only = scan_path(os.path.join(root, "dartonly"))
    assert any(f["rule"] == "MB-03" and "相机" in f["evidence"] for f in dart_only), \
        f"Dart 侧权限申请漏报：{dart_only}"

    _, clean = scan_path(os.path.join(root, "clean"))
    assert not clean, f"干净夹具被误报：{clean}"

    # 负向控制：把干净夹具改坏，必须出现命中
    with open(os.path.join(root, "clean", "wdio.conf.js"), "w", encoding="utf-8") as fh:
        fh.write("exports.config = { capabilities: [{ autoGrantPermissions: true }] }\n")
    _, mutated = scan_path(os.path.join(root, "clean"))
    assert any(f["rule"] == "MB-10" for f in mutated), "负向控制失败：改坏后仍未命中"

    # 空目录不崩、0 命中
    empty = os.path.join(root, "empty")
    os.makedirs(empty, exist_ok=True)
    f0, none = scan_path(empty)
    assert f0 == 0 and not none, "空目录扫描异常"

    # 矩阵与命令清单
    assert len(MATRIX) == 10 and MATRIX[0][0] == "MB-20" and MATRIX[-1][0] == "MB-29"
    assert "adb" in CASES["android"][1][1] and "simctl" in CASES["ios"][0][1]

    print(f"SELFTEST GREEN: 脏夹具 {len(bad)} 条命中覆盖 10/10 规则；干净夹具 0 命中；"
          f"docs 默认排除生效；负向控制命中 MB-10；矩阵 10 行；命令清单含 adb/simctl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
