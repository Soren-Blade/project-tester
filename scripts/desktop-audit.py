#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""desktop-audit.py — 桌面应用静态反模式扫描与运行矩阵（R-26）

零依赖、不联网、不启动应用、不执行安装器或更新器。只做文本匹配与清单输出。

用法：
    python scripts/desktop-audit.py scan <路径> [--format table|json|markdown]
                                   [--include-docs] [--fail-on-gap]
    python scripts/desktop-audit.py matrix [--format table|json|markdown]
    python scripts/desktop-audit.py cases
    python scripts/desktop-audit.py --self-test

输出约定：
- 每条命中都是「待人工裁决的线索」，不是缺陷结论。
- 退出码：0 = 扫描完成；1 = 有违规且指定 --fail-on-gap；2 = 路径不存在。
- 边界（诚实声明）：
  1. 只做静态文本匹配，不理解数据流与控制流；
  2. 命中不证明存在漏洞，0 命中也不证明没有缺陷；
  3. 配置文件缺失或无法解析时只报「无法核对」，不猜；
  4. 不验证签名、公证与更新包，这些必须用 codesign / signtool / notarytool 实际执行；
  5. 不代填报告结论、不判断 Go/No-Go。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile

try:  # 控制台编码兜底：Windows 默认 GBK 时避免 UnicodeEncodeError
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "release", "out", "target",
    "__pycache__", ".venv", "venv", "coverage", "vendor", ".next", ".nuxt",
    ".gradle", "Pods", "DerivedData", ".idea", ".vscode", "bin", "obj",
}
CODE_EXTS = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json", ".rs", ".toml",
    ".html", ".htm", ".yml", ".yaml", ".cfg", ".ini", ".plist",
}
DOC_EXTS = {".md", ".txt", ".rst", ".adoc"}
MAX_FILE_BYTES = 2_000_000
SELF_NAME = "desktop-audit.py"

# 行级规则：(规则 ID, 说明, 正则, 类型)
RULES = [
    ("DT-01", "Node 集成开启",
     re.compile(r'\bnodeIntegration(?:InWorker|InSubFrames)?\s*["\']?\s*:\s*true\b'), "违规"),
    ("DT-02", "隔离/沙箱关闭",
     re.compile(r'\bcontextIsolation\s*["\']?\s*:\s*false\b'), "违规"),
    ("DT-02", "渲染进程沙箱关闭",
     re.compile(r'\bsandbox\s*["\']?\s*:\s*false\b'), "违规"),
    ("DT-02", "remote 模块开启",
     re.compile(r'\benableRemoteModule\s*["\']?\s*:\s*true\b'), "违规"),
    ("DT-03", "同源策略关闭",
     re.compile(r'\bwebSecurity\s*["\']?\s*:\s*false\b'), "违规"),
    ("DT-03", "允许不安全内容",
     re.compile(r'\ballowRunningInsecureContent\s*["\']?\s*:\s*true\b'), "违规"),
    ("DT-04", "preload 暴露特权对象",
     re.compile(r'exposeInMainWorld\(\s*["\'](?:ipcRenderer|require|process|electron|fs|shell|child_process)["\']'),
     "违规"),
    ("DT-04", "直接赋值特权对象",
     re.compile(r'window\.(?:ipcRenderer|require)\s*='), "违规"),
    ("DT-06", "openExternal 接变量",
     re.compile(r'shell\.openExternal\(\s*(?![\'"\s])'), "违规"),
    ("DT-06", "openExternal 模板拼接",
     re.compile(r'shell\.openExternal\(\s*`[^`]*\$\{'), "违规"),
    ("DT-07", "新窗口显式放行",
     re.compile(r'setWindowOpenHandler\([^)]*\)\s*=>\s*\(?\s*\{\s*action\s*:\s*["\']allow'),
     "违规"),
    ("DT-07", "webview 允许弹窗",
     re.compile(r'<webview[^>]*\ballowpopups\b'), "违规"),
    ("DT-08", "CSP 放行内联/求值",
     re.compile(r'script-src[^;\n]*unsafe-(?:inline|eval)'), "违规"),
    ("DT-08", "CSP 通配源",
     re.compile(r"default-src\s+['\"]?\*"), "违规"),
    ("DT-08", "CSP 关闭",
     re.compile(r'["\']csp["\']\s*:\s*null\b'), "违规"),
    ("DT-09", "更新公钥为空",
     re.compile(r'pubkey\s*["\']?\s*[:=]\s*["\']\s*["\']'), "违规"),
    ("DT-09", "更新允许明文传输",
     re.compile(r'dangerousInsecureTransportProtocol\s*["\']?\s*:\s*true'), "违规"),
    ("DT-09", "更新允许降级",
     re.compile(r'allowDowngrade\s*["\']?\s*:\s*true'), "违规"),
    ("DT-09", "明文更新源",
     re.compile(r'["\']http://[^"\']*(?:updat|releas)'), "违规"),
    ("DT-10", "asset 协议放宽隐藏文件",
     re.compile(r'requireLiteralLeadingDot\s*["\']?\s*:\s*false'), "违规"),
    ("DT-10", "scope 放行全部路径",
     re.compile(r'["\'](?:allow|scope)["\']\s*:\s*\[\s*["\']\*\*["\']'), "违规"),
    ("DT-10", "file 协议保留额外特权",
     re.compile(r'GrantFileProtocolExtraPrivileges\s*["\']?\s*[:=]\s*true'), "违规"),
]

BROAD_PERMS = re.compile(r'["\'](?:fs|shell|process|http|sql|os|window):default["\']')
ANY_WINDOWS = re.compile(r'["\']windows["\']\s*:\s*\[\s*["\']\*["\']\s*\]')
IPC_ANY = re.compile(r'\bipcMain\.(?:handle|handleOnce|on)\s*\(')
FS_ANY = re.compile(r'\b(?:fs|fsp)\.(?:readFile|writeFile|appendFile|readdir|unlink|rename|copyFile|open|createReadStream|createWriteStream|readFileSync|writeFileSync|openSync)\b|child_process|\bexecSync\b|\bexecFileSync\b|\bspawnSync\b')
VALIDATE_ANY = re.compile(r'senderFrame|sender\s*===|realpath|path\.resolve|path\.normalize|isTrusted')
NEW_WINDOW = re.compile(r'new\s+BrowserWindow\s*\(')
WINDOW_OPEN_HANDLER = re.compile(r'setWindowOpenHandler\s*\(')
ASTERISK = re.compile(r'["\']\*\*["\']')

MATRIX = [
    ("DT-20", "进程边界", "打包制品里查 typeof require / process / window.electron", "devtools 截图 + 返回值"),
    ("DT-21", "IPC 校验", "路径穿越 + 非法 sender 各 1 条", "主进程拒绝日志 + 渲染侧返回"),
    ("DT-22", "导航与新窗口", "注入远程链接、window.open、<a target=_blank>", "拦截日志 + 截图"),
    ("DT-23", "CSP 与本地内容", "注入 inline script / onerror，观察 console", "CSP 报错原文 + 请求被拦记录"),
    ("DT-24", "更新验签", "codesign / spctl / signtool / fuses read 输出", "命令 + 退出码 + 关键行"),
    ("DT-25", "安装升级回滚", "覆盖安装、降级、卸载各 1 次", "版本号 + 数据 diff + 残留检查"),
    ("DT-26", "单实例与深链", "双开 + 冷/温启动深链 + 文件关联", "进程列表 + 转发日志"),
    ("DT-27", "崩溃恢复", "结束渲染/主进程后重启", "重启截图 + 数据前后对比"),
    ("DT-28", "本地协议/路径", ".. / 绝对路径 / 编码绕写 / 符号链接", "请求原文 + 响应或拒绝日志"),
    ("DT-29", "跨平台", "Windows/macOS/Linux 各跑本表至少 3 条", "逐平台一行，标注制品与签名状态"),
]

CASES = [
    ("通用", "Electron fuses", 'npx --yes @electron/fuses read --app "/Applications/Foo.app"'),
    ("通用", "结构扫描", "python scripts/desktop-audit.py scan . --format table"),
    ("macOS", "签名信息", 'codesign -dv --verbose=4 "Foo.app"'),
    ("macOS", "Gatekeeper", 'spctl -a -vv "Foo.app"'),
    ("macOS", "公证票据", 'xcrun stapler validate "Foo.app"'),
    ("macOS", "进程是否退出", 'pgrep -fl "Foo"'),
    ("Windows", "签名校验", 'signtool verify /pa /v "Foo.exe"'),
    ("Windows", "进程是否退出", 'tasklist | findstr /i foo'),
    ("Windows", "文件关联", 'reg query "HKCR\\.foo" /ve'),
    ("Linux", "AppImage 运行", "./Foo.AppImage --appimage-extract-and-run"),
    ("Linux", "进程是否退出", "pgrep -af foo"),
]


def _collect(path, include_docs):
    """返回 (相对路径列表, 绝对路径列表)。文件直接返回；目录按扩展名过滤。"""
    if os.path.isfile(path):
        return [os.path.basename(path)], [os.path.abspath(path)]
    exts = CODE_EXTS | (DOC_EXTS if include_docs else set())
    rels, abss = [], []
    for root, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(files):
            if name == SELF_NAME:
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in exts:
                continue
            ab = os.path.join(root, name)
            try:
                if os.path.getsize(ab) > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            rels.append(os.path.relpath(ab, path).replace("\\", "/"))
            abss.append(ab)
    return rels, abss


def _read(abspath):
    try:
        with open(abspath, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def _line_of(text, pos):
    return text.count("\n", 0, pos) + 1


COMMENT_RE = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)


def _blank_comments(text):
    """把注释替换成等长空格（保留换行与偏移），避免注释里的关键词干扰判定。"""
    return COMMENT_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def scan_path(path, include_docs=False):
    rels, abss = _collect(path, include_docs)
    findings = []
    seen = set()

    def add(rule, rel, line, evidence, kind="违规"):
        evidence = re.sub(r"\s+", " ", evidence).strip()[:140]
        key = (rule, rel, line)
        if key in seen:
            return
        seen.add(key)
        findings.append({"rule": rule, "file": rel, "line": line,
                         "evidence": evidence, "kind": kind})

    texts = {}
    for rel, ab in zip(rels, abss):
        texts[rel] = _read(ab)

    # 行级规则
    for rel in sorted(texts):
        text = texts[rel]
        if not text:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            for rule, _desc, pattern, kind in RULES:
                if pattern.search(line):
                    add(rule, rel, lineno, line, kind)

    # 文件级规则：需要跨行上下文
    for rel in sorted(texts):
        text = texts[rel]
        if not text:
            continue
        low = rel.lower()
        text_an = _blank_comments(text)

        # DT-05：逐个 handler 看上下文，避免「同文件另有一个安全 handler」掩盖风险
        handlers = list(IPC_ANY.finditer(text_an))
        for idx, m in enumerate(handlers):
            start = m.start()
            end = handlers[idx + 1].start() if idx + 1 < len(handlers) else min(len(text_an), start + 4000)
            block = text_an[start:end]
            if FS_ANY.search(block) and not VALIDATE_ANY.search(block):
                add("DT-05", rel, _line_of(text, start),
                    "IPC handler 内有文件/命令调用，未见 senderFrame/path.resolve/realpath",
                    "无法核对")

        # DT-07：创建窗口但没有任何新窗口限制
        m = NEW_WINDOW.search(text_an)
        if m and not WINDOW_OPEN_HANDLER.search(text_an):
            add("DT-07", rel, _line_of(text, m.start()),
                "new BrowserWindow 未见 setWindowOpenHandler", "无法核对")

        # DT-10：capability 对全部窗口 + 宽泛权限
        if low.endswith((".json", ".toml")) and ANY_WINDOWS.search(text) and BROAD_PERMS.search(text):
            m = ANY_WINDOWS.search(text)
            add("DT-10", rel, _line_of(text, m.start()),
                "capability 授权全部窗口且包含 fs/shell/process 等 default 权限", "违规")

        # DT-10：assetProtocol 配置里出现裸 **
        if "assetProtocol" in text and ASTERISK.search(text):
            m = ASTERISK.search(text)
            add("DT-10", rel, _line_of(text, m.start()),
                "assetProtocol 使用裸 ** scope（可能覆盖隐藏目录）", "违规")

    # DT-08：整个项目找不到任何 CSP（Electron 侧），只能报「无法核对」
    project_has_csp = any(
        ("content-security-policy" in t.lower()) or re.search(r'["\']csp["\']\s*:\s*["\']', t)
        for t in texts.values()
    )
    if not project_has_csp:
        for rel in sorted(texts):
            text = texts[rel]
            if not rel.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
                continue
            m = NEW_WINDOW.search(text) or re.search(r'\.loadFile\s*\(', text)
            if m:
                add("DT-08", rel, _line_of(text, m.start()),
                    "创建/加载窗口但项目内未见任何 CSP（meta 或 csp 配置）", "无法核对")

    findings.sort(key=lambda f: (f["rule"], f["file"], f["line"]))
    return len(texts), findings


def print_scan(root, files_scanned, findings, fmt):
    violations = [f for f in findings if f["kind"] == "违规"]
    gaps = [f for f in findings if f["kind"] != "违规"]
    if fmt == "json":
        print(json.dumps({
            "root": root,
            "files_scanned": files_scanned,
            "counts": {"violation": len(violations), "unverifiable": len(gaps),
                       "total": len(findings)},
            "findings": findings,
        }, ensure_ascii=False, indent=2))
        return
    if fmt == "markdown":
        print("| 规则 | 位置 | 证据 | 类型 |")
        print("|---|---|---|---|")
        for f in findings:
            ev = f["evidence"].replace("|", "\\|")
            print(f'| {f["rule"]} | `{f["file"]}:{f["line"]}` | {ev} | {f["kind"]} |')
    else:
        print(f'{"规则":<7} {"位置":<46} {"类型":<6} 证据')
        print("-" * 100)
        for f in findings:
            loc = f'{f["file"]}:{f["line"]}'
            if len(loc) > 45:
                loc = "..." + loc[-42:]
            print(f'{f["rule"]:<8} {loc:<46} {f["kind"]:<7} {f["evidence"]}')
    print()
    print(f"扫描 {files_scanned} 个文件；命中 {len(violations)} 条违规 / {len(gaps)} 条无法核对。")
    print("命中≠缺陷；逐条裁决写进模板 §8；0 命中≠无缺陷。")


def print_matrix(fmt):
    if fmt == "json":
        print(json.dumps([{"id": i, "面": a, "必测动作": b, "最低证据": c}
                          for i, a, b, c in MATRIX], ensure_ascii=False, indent=2))
        return
    if fmt == "markdown":
        print("| ID | 面 | 必测动作 | 最低证据 |")
        print("|---|---|---|---|")
        for i, a, b, c in MATRIX:
            print(f"| {i} | {a} | {b} | {c} |")
        return
    print(f'{"ID":<7} {"面":<14} {"必测动作":<44} 最低证据')
    print("-" * 100)
    for i, a, b, c in MATRIX:
        print(f"{i:<8} {a:<15} {b:<45} {c}")


def print_cases():
    platform = None
    for plat, label, cmd in CASES:
        if plat != platform:
            platform = plat
            print(f"\n[{plat}]")
        print(f"  {label}: {cmd}")


def self_test():
    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            ok = False
            print(f"SELFTEST FAIL: {msg}")

    tmp = tempfile.mkdtemp(prefix="desktop-audit-selftest-")
    try:
        dirty = os.path.join(tmp, "dirty")
        clean = os.path.join(tmp, "clean")
        empty = os.path.join(tmp, "empty")
        os.makedirs(dirty)
        os.makedirs(clean)
        os.makedirs(empty)

        # 脏夹具：10 条规则全覆盖
        with open(os.path.join(dirty, "main.js"), "w", encoding="utf-8") as fh:
            fh.write("""const { BrowserWindow, ipcMain, shell } = require('electron')
const fs = require('fs')
const win = new BrowserWindow({
  webPreferences: {
    nodeIntegration: true,
    contextIsolation: false,
    sandbox: false,
    webSecurity: false,
  },
})
win.webContents.setWindowOpenHandler(() => ({ action: 'allow' }))
win.webContents.on('will-attach-webview', (e, w) => { w.allowpopups = true })
ipcMain.handle('note:read', (event, name) => {
  return fs.readFileSync(name, 'utf8')
})
function open(target) { shell.openExternal(target) }
""")
        with open(os.path.join(dirty, "preload.js"), "w", encoding="utf-8") as fh:
            fh.write("""const { contextBridge, ipcRenderer } = require('electron')
contextBridge.exposeInMainWorld('ipcRenderer', ipcRenderer)
""")
        with open(os.path.join(dirty, "index.html"), "w", encoding="utf-8") as fh:
            fh.write("""<html><head>
<meta http-equiv="Content-Security-Policy" content="script-src 'self' 'unsafe-inline'">
</head><body><webview allowpopups src="https://example.com"></webview></body></html>
""")
        with open(os.path.join(dirty, "tauri.conf.json"), "w", encoding="utf-8") as fh:
            fh.write("""{
  "plugins": {
    "updater": {
      "pubkey": "",
      "endpoints": ["http://updates.example.com/latest.json"],
      "dangerousInsecureTransportProtocol": true,
      "allowDowngrade": true
    }
  },
  "app": {
    "security": {
      "assetProtocol": {
        "enable": true,
        "scope": { "allow": ["**"], "requireLiteralLeadingDot": false }
      }
    }
  }
}
""")
        os.makedirs(os.path.join(dirty, "capabilities"))
        with open(os.path.join(dirty, "capabilities", "default.json"), "w", encoding="utf-8") as fh:
            fh.write("""{
  "identifier": "main",
  "windows": ["*"],
  "permissions": ["fs:default", "shell:default"]
}
""")
        # 干净夹具：同形态但已收口
        with open(os.path.join(clean, "main.js"), "w", encoding="utf-8") as fh:
            fh.write("""const { BrowserWindow, ipcMain } = require('electron')
const fs = require('fs')
const path = require('path')
const DIR = path.join(__dirname, 'notes')
const win = new BrowserWindow({
  webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true },
})
win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
ipcMain.handle('note:read', (event, name) => {
  if (!event.senderFrame || !event.senderFrame.url.startsWith('app://bundle')) {
    throw new Error('untrusted sender')
  }
  const p = fs.realpathSync(path.resolve(DIR, String(name)))
  if (!p.startsWith(DIR)) throw new Error('path escape')
  return fs.readFileSync(p, 'utf8')
})
""")
        with open(os.path.join(clean, "index.html"), "w", encoding="utf-8") as fh:
            fh.write("""<html><head>
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'">
</head><body><a href="https://example.com">x</a></body></html>
""")
        with open(os.path.join(clean, "tauri.conf.json"), "w", encoding="utf-8") as fh:
            fh.write("""{
  "plugins": {
    "updater": { "pubkey": "dW50cnVzdGVk", "endpoints": ["https://updates.example.com/latest.json"] }
  },
  "app": {
    "security": {
      "assetProtocol": {
        "enable": true,
        "scope": { "allow": ["$HOME/notes/**/*"], "requireLiteralLeadingDot": true }
      }
    }
  }
}
""")

        n_dirty, dirty_findings = scan_path(dirty)
        found = {f["rule"] for f in dirty_findings}
        expected = {f"DT-{i:02d}" for i in range(1, 11)}
        missing = sorted(expected - found)
        check(not missing, f"脏夹具漏报规则: {missing}")
        check(n_dirty >= 5, f"脏夹具扫描文件数异常: {n_dirty}")

        n_clean, clean_findings = scan_path(clean)
        check(clean_findings == [], f"干净夹具出现误报: {clean_findings[:3]}")

        # 文档默认排除；--include-docs 后应命中
        with open(os.path.join(clean, "notes.md"), "w", encoding="utf-8") as fh:
            fh.write("配置示例：nodeIntegration: true 是反面教材\n")
        _, no_docs = scan_path(clean)
        check(no_docs == [], "默认扫描不应包含 .md 文档")
        _, with_docs = scan_path(clean, include_docs=True)
        check(any(f["rule"] == "DT-01" and f["file"].endswith("notes.md") for f in with_docs),
              "--include-docs 应扫描 .md 并命中 DT-01")
        os.remove(os.path.join(clean, "notes.md"))

        # 负向控制：干净夹具改坏必须命中
        main_clean = os.path.join(clean, "main.js")
        with open(main_clean, encoding="utf-8") as fh:
            original = fh.read()
        with open(main_clean, "w", encoding="utf-8") as fh:
            fh.write(original.replace("sandbox: true", "sandbox: false"))
        _, mutated = scan_path(clean)
        check(any(f["rule"] == "DT-02" for f in mutated), "负向控制失败：改坏后应命中 DT-02")
        with open(main_clean, "w", encoding="utf-8") as fh:
            fh.write(original)

        # 空目录不崩
        n_empty, empty_findings = scan_path(empty)
        check(n_empty == 0 and empty_findings == [], "空目录处理异常")

        # matrix / cases 结构
        check(len(MATRIX) == 10 and MATRIX[0][0] == "DT-20" and MATRIX[-1][0] == "DT-29",
              "MATRIX 应为 DT-20..DT-29 共 10 行")
        check(any("codesign" in c[2] for c in CASES), "CASES 应包含 codesign")
        check(any("signtool" in c[2] for c in CASES), "CASES 应包含 signtool")

        # JSON 输出可解析
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            print_scan(dirty, n_dirty, dirty_findings, "json")
        parsed = json.loads(buf.getvalue())
        check(parsed["counts"]["total"] == len(dirty_findings), "JSON 输出计数不一致")

        # 每条规则都有可读说明
        for rule, desc, _pat, kind in RULES:
            check(bool(desc) and kind in ("违规", "无法核对"), f"规则元数据异常: {rule}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if ok:
        print(f"SELFTEST GREEN: {len(RULES)} 条行级规则 + 文件级规则，脏夹具全覆盖，干净夹具 0 命中，负向控制有效。")
        return 0
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="桌面应用静态反模式扫描（R-26）。零依赖、不联网、不执行被测程序。")
    parser.add_argument("--self-test", action="store_true", help="运行自测夹具")
    sub = parser.add_subparsers(dest="cmd")

    sp = sub.add_parser("scan", help="扫描目录或单文件")
    sp.add_argument("path", help="项目根目录或单文件")
    sp.add_argument("--format", choices=["table", "json", "markdown"], default="table")
    sp.add_argument("--include-docs", action="store_true", help="同时扫描 .md/.txt 文档")
    sp.add_argument("--fail-on-gap", action="store_true", help="存在违规时退出码 1")

    mp = sub.add_parser("matrix", help="输出运行矩阵 DT-20..DT-29")
    mp.add_argument("--format", choices=["table", "json", "markdown"], default="table")

    sub.add_parser("cases", help="输出常用验证命令")

    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.cmd == "scan":
        if not os.path.exists(args.path):
            print(f"路径不存在: {args.path}", file=sys.stderr)
            return 2
        files_scanned, findings = scan_path(args.path, args.include_docs)
        print_scan(args.path, files_scanned, findings, args.format)
        if args.fail_on_gap and any(f["kind"] == "违规" for f in findings):
            return 1
        return 0
    if args.cmd == "matrix":
        print_matrix(args.format)
        return 0
    if args.cmd == "cases":
        print_cases()
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
