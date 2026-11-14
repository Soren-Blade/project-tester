#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文件上传 / 下载内容边界离线审计（R-18 配套，零依赖）。

用法：
  python scripts/upload-audit.py scan <path> [--format text|json] [--fail-on-gap]
  python scripts/upload-audit.py matrix --file uploads.json [--format text|json] [--fail-on-gap]
  python scripts/upload-audit.py cases [--format text|json]
  python scripts/upload-audit.py --self-test

源码规则（scan）：
  UA-01 HIGH 扩展名与文件魔数不一致（只校验扩展名/Content-Type 的典型后果）
  UA-02 HIGH 可执行/脚本类扩展名（php / phtml / php5 / jsp / asp / aspx / exe …）
  UA-03 HIGH SVG 内含脚本/事件处理（未净化即可 XSS）
  UA-04 HIGH 路径拼接用户文件名（`..` 穿越、覆盖任意文件）
  UA-05 HIGH 直接使用原始文件名落盘（覆盖、ADS、双扩展）
  UA-08 MEDIUM 上传落点位于 webroot / public 目录

清单规则（matrix）：
  UA-10 S1 扩展不在白名单
  UA-11 S1 文件名含 `..`、空字节、`:` 或前导点
  UA-12 S1 扩展名与魔数不一致（改名绕过）
  UA-13 S1 落盘在 webroot / 可直链目录
  UA-14 S1 脚本类扩展 + 私有访问关闭
  UA-15 S1 presign 断签/登出后仍可用，或可重复换内容上传
  UA-16 MEDIUM 上传入口未要求身份
  UA-17 S1 图片未解码重编码（仅搬字节，图片马/元数据原样保留）

诚实边界：
- 只读本地源码与本地 JSON 清单，**不联网、不代填**任何字段。
- 魔数校验只读文件头，**不证明**内容安全（多态/嵌套载荷仍需解码重编码与 AV）。
- 清单通过**不证明**线上存储私有、presign 到期正确；必须用 curl 实取与断签复测留档。
- 不冒充「上传安全」「合规」，不替代人工源码审计与沙箱复核。
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import traceback
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

EXEC_EXT = {"php", "phtml", "php3", "php4", "php5", "pht", "jsp", "jspx", "asp",
            "aspx", "exe", "sh", "pl", "cgi", "war", "bat", "cmd", "ps1"}
ALLOWED = {"jpg", "jpeg", "png", "gif", "webp", "pdf", "docx", "xlsx", "zip", "mp4", "csv"}
MAGIC = {
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "gif": [b"GIF87a", b"GIF89a"],
    "pdf": [b"%PDF-"],
    "zip": [b"PK\x03\x04", b"PK\x05\x06"],
    "docx": [b"PK\x03\x04"],
    "xlsx": [b"PK\x03\x04"],
}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".test-memory", "dist", "build", ".venv"}


def ext_of(name: str) -> str:
    return os.path.splitext(str(name))[1].lower().lstrip(".")


def sniff(head: bytes) -> str:
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if head.startswith(b"%PDF-"):
        return "pdf"
    if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06"):
        return "zip"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head.startswith(b"\xca\xfe\xba\xbe"):
        return "class"
    return ""


def iter_files(root: Path):
    if root.is_file():
        yield root
        return
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        yield p


def scan_file(path: Path) -> list[dict]:
    out: list[dict] = []
    ext = ext_of(path.name)
    try:
        head = path.open("rb").read(4096)
    except Exception as e:
        return [{"rule": "UA-00", "severity": "LOW", "file": str(path), "line": 0,
                 "snippet": "", "reason": f"<读取失败: {e}>"}]
    low = head.lower()
    if ext in EXEC_EXT:
        out.append({"rule": "UA-02", "severity": "HIGH", "file": str(path), "line": 0,
                    "snippet": path.name, "reason": "可执行/脚本类扩展名：上传成功后可能被当代码执行"})
    if ext in MAGIC:
        hit = any(low.startswith(m.lower()) for m in MAGIC[ext])
        if not hit:
            out.append({"rule": "UA-01", "severity": "HIGH", "file": str(path), "line": 0,
                        "snippet": path.name, "reason": f".{ext} 的魔数与扩展不一致（改名/伪造 Content-Type）"})
    elif ext == "svg":
        text = head.decode("utf-8", "replace").lower()
        if "<script" in text or "onload=" in text or "onerror=" in text or "javascript:" in text or "foreignobject" in text:
            out.append({"rule": "UA-03", "severity": "HIGH", "file": str(path), "line": 0,
                        "snippet": path.name, "reason": "SVG 内含脚本/事件：直接内联渲染即 XSS"})
    elif sniff(head) in {"png", "jpg", "gif", "pdf", "zip", "webp"}:
        out.append({"rule": "UA-01", "severity": "HIGH", "file": str(path), "line": 0,
                    "snippet": path.name, "reason": f"二进制魔数是 {sniff(head)}，扩展却是 .{ext}（内容与类型不符）"})
    return out


def scan_text_rules(path: Path) -> list[dict]:
    out: list[dict] = []
    if path.suffix.lower() not in {".js", ".mjs", ".cjs", ".ts", ".tsx", ".py", ".go",
                                   ".java", ".php", ".rb", ".cs", ".kt", ".vue", ".svelte"}:
        return out
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return out
    for i, line in enumerate(lines, 1):
        low = line.lower()
        if re.search(r"\.\.(/|\\|[\"'])", line) and re.search(r"(?i)(upload|filename|originalname|file\.name)", line):
            out.append({"rule": "UA-04", "severity": "HIGH", "file": str(path), "line": i,
                        "snippet": line.strip()[:200], "reason": "用户文件名参与路径拼接：可穿越目录/覆盖文件"})
        if re.search(r"(?i)(join|resolve)\([^)]*(originalname|originalfilename|original_filename|file\.name|file\.filename|req\.body\.filename)", line) or \
           re.search(r"(?i)(writeFile|createWriteStream|copyFile)\([^)]*(originalname|file\.name)", line):
            out.append({"rule": "UA-05", "severity": "HIGH", "file": str(path), "line": i,
                        "snippet": line.strip()[:200], "reason": "用原始文件名落盘：覆盖、ADS、双扩展都由此来"})
        if re.search(r"(?i)(uploads?/|upload_dir|uploaddir|/public/|webroot|/var/www|static/uploads)", line) and \
           re.search(r"(?i)(move|rename|dest|destination|save|write|join|resolve|filename)", line):
            out.append({"rule": "UA-08", "severity": "MEDIUM", "file": str(path), "line": i,
                        "snippet": line.strip()[:200], "reason": "上传落点疑似 webroot/public：文件可被直链访问甚至执行"})
    return out


def scan(root: Path) -> list[dict]:
    hits: list[dict] = []
    for p in iter_files(root):
        hits.extend(scan_file(p))
        hits.extend(scan_text_rules(p))
    seen, out = set(), []
    for h in hits:
        k = (h["rule"], h["file"], h["line"])
        if k not in seen:
            seen.add(k)
            out.append(h)
    return out


def audit_matrix(items: list) -> list[dict]:
    issues: list[dict] = []
    if not isinstance(items, list) or not items:
        return [{"id": "UA-09", "severity": "S1", "name": "", "reason": "清单为空，无法审计"}]
    for it in items:
        if not isinstance(it, dict):
            issues.append({"id": "UA-09", "severity": "S1", "name": "", "reason": "条目不是对象"})
            continue
        name = str(it.get("filename") or it.get("name") or "")
        ext = ext_of(it.get("ext") or name)
        stored = str(it.get("stored_path") or it.get("stored_name") or "")
        magic = str(it.get("magic") or "")
        ct = str(it.get("content_type") or "")
        after_logout = bool(it.get("presign_valid_after_logout"))
        uses = int(it.get("presign_uses") or 1)
        presign = bool(it.get("presign_url"))

        if ext and ext not in ALLOWED:
            issues.append({"id": "UA-10", "severity": "S1", "name": name,
                           "reason": f"扩展 .{ext} 不在白名单"})
        if ".." in name or "\x00" in name or ":" in name or name.startswith("."):
            issues.append({"id": "UA-11", "severity": "S1", "name": name,
                           "reason": "文件名含 .. / 空字节 / 冒号 / 前导点（穿越、ADS、隐藏）"})
        if magic and (ext in MAGIC or ext == "webp") and sniff(magic.encode("latin-1", "replace")) not in {ext, "zip", "docx", "xlsx"}:
            issues.append({"id": "UA-12", "severity": "S1", "name": name,
                           "reason": f"扩展 .{ext} 与魔数 {magic!r} 不一致"})
        if re.search(r"(?i)(^/|^\.?/)?(public|www|webroot|static)/", stored) or re.search(r"(?i)/var/www", stored):
            issues.append({"id": "UA-13", "severity": "S1", "name": name,
                           "reason": f"落盘路径 {stored!r} 位于 webroot：可直链/可执行"})
        if ext in EXEC_EXT and not it.get("private_access", True):
            issues.append({"id": "UA-14", "severity": "S1", "name": name,
                           "reason": "脚本类扩展 + 私有访问关闭：上传目录就是执行入口"})
        if presign and (after_logout or uses > 1):
            issues.append({"id": "UA-15", "severity": "S1", "name": name,
                           "reason": f"presign URL 在断签后仍有效或可重复使用 {uses} 次（bearer token）"})
        if it.get("auth_required") is False:
            issues.append({"id": "UA-16", "severity": "MEDIUM", "name": name,
                           "reason": "上传入口未要求身份：匿名可写存储/消耗配额"})
        if ext in {"jpg", "jpeg", "png", "gif", "webp"} and it.get("decoded_and_reencoded") is not True:
            issues.append({"id": "UA-17", "severity": "S1", "name": name,
                           "reason": "图片未经解码重编码：图片马、EXIF、pixel flood 全部原样落盘"})
    return issues


def show_cases() -> list[str]:
    return [
        "# 上传/下载判定反例（确定性，可直接作为期望值）",
        "",
        "- 只白名单扩展名不够：`.jpg` 里放 PHP/JS，或把 `shell.php` 改名 `shell.jpg`（魔数检查也要做）。",
        "- 只信任 `Content-Type` 不够：它由客户端给，上传时伪造 `image/png` 完全合法。",
        "- 只校验魔数也不够：GIF89a + PHP 的「图片马」魔数正确；必须解码重编码。",
        "- 文件名 `..\\..\\web.config`、`shell.asp:.jpg`（NTFS ADS）、`.htaccess` 都能绕过只看后缀的过滤。",
        "- 落盘到 webroot 且允许脚本执行时，任意外传文件即 RCE；上传目录必须禁执行且放 webroot 外。",
        "- S3 presigned URL 是 bearer token，不绑会话：断签/登出后仍可用到过期，可重复 PUT 换内容。",
        "- presign 本身不限制大小/类型：条件必须来自签名策略（`content-length-range`、Content-Type、checksum）。",
        "- 下载侧同样要测：任意人凭可猜路径直链取私有文件，等于没有鉴权（IDOR 的表亲）。",
        "",
        "> 这些是确定性规则，不是对被测系统的实测结论；线上必须用 curl 实传/实取与存储侧证据证明。",
    ]


def parse_args(argv: list[str]) -> dict:
    o = {"cmd": None, "path": None, "file": None, "format": "text", "fail": False, "self": False}
    rest = argv[1:]
    if "--self-test" in rest:
        o["self"] = True
        return o
    if not rest:
        return o
    o["cmd"] = rest[0]
    i = 1
    while i < len(rest):
        a = rest[i]
        if a == "--format" and i + 1 < len(rest):
            o["format"] = rest[i + 1]; i += 2
        elif a == "--file" and i + 1 < len(rest):
            o["file"] = rest[i + 1]; i += 2
        elif a == "--fail-on-gap":
            o["fail"] = True; i += 1
        elif not a.startswith("--") and o["path"] is None:
            o["path"] = a; i += 1
        else:
            i += 1
    return o


def print_scan(hits: list[dict], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps({"tool": "upload-audit", "mode": "scan", "hits": hits,
                          "note": "静态命中只是可疑写法；未命中不证明上传安全"}, ensure_ascii=False, indent=2))
        return
    print(f"# 上传/下载反模式扫描：{len(hits)} 处可疑")
    for h in hits:
        print(f"[{h['rule']} {h['severity']}] {h['file']}:{h['line']}  {h['reason']}")
        print(f"    {h['snippet']}")
    print("> 未命中不证明安全；魔数只读文件头，必须再解码重编码并做存储侧验证。")


def print_matrix(issues: list[dict], fmt: str) -> None:
    hard = [i for i in issues if i["severity"] == "S1"]
    if fmt == "json":
        print(json.dumps({"tool": "upload-audit", "mode": "matrix", "issues": issues, "gaps": len(hard),
                          "note": "清单通过不证明线上私有与到期正确"}, ensure_ascii=False, indent=2))
        return
    print(f"# 上传清单审计：{len(issues)} 处问题（S1 {len(hard)}）")
    for i in issues:
        print(f"[{i['id']} {i['severity']}] {i['name'] or '-'}  {i['reason']}")
    print(f"> 缺口 {len(hard)} 项；必须用 curl 实传/实取与存储侧证据补证。")


def self_test() -> int:
    checks: list[tuple[str, bool]] = []
    tmp = Path(tempfile.mkdtemp(prefix="upload-audit-selftest-"))
    (tmp / "shell.php").write_bytes(b"<?php echo 'hello'; ?>")
    (tmp / "evil.png").write_bytes(b"<?php echo 1; ?>")
    (tmp / "real.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 64)
    (tmp / "pic.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    (tmp / "x.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>', encoding="utf-8")
    (tmp / "app.py").write_text(
        "stored = os.path.join(UPLOAD_DIR, original_filename)\n"
        "user_name = \"../..\" + filename\n"
        "await writeFile(os.path.join(uploadDir, file.name), buf)\n"
        "os.move(dest=os.path.join('/var/www/uploads', name))\n",
        encoding="utf-8",
    )
    hits = scan(tmp)
    rules = {h["rule"] for h in hits}
    for rid in ("UA-01", "UA-02", "UA-03", "UA-04", "UA-05", "UA-08"):
        checks.append((f"scan 检出 {rid}", rid in rules))
    checks.append(("real.jpg 与 pic.png 未被误报", not [h for h in hits if h["file"].endswith(("real.jpg", "pic.png"))]))

    items = [
        {"filename": "a.jpg", "magic": "GIF89a", "stored_path": "public/u/a.jpg", "private_access": False,
         "presign_url": "https://s3/x", "presign_valid_after_logout": True, "presign_uses": 3,
         "auth_required": False, "decoded_and_reencoded": False},
        {"filename": "..\\shell.asp:.jpg", "stored_path": "public/u/x"},
        {"filename": "run.php", "private_access": False, "auth_required": True},
        {"filename": "logo.webp", "magic": "RIFF", "stored_path": "private/u/logo.webp",
         "private_access": True, "auth_required": True, "decoded_and_reencoded": True},
    ]
    issues = audit_matrix(items)
    ids = {i["id"] for i in issues}
    for rid in ("UA-10", "UA-11", "UA-12", "UA-13", "UA-14", "UA-15", "UA-16", "UA-17"):
        checks.append((f"matrix 检出 {rid}", rid in ids))
    ok_items = [{"filename": "a.png", "magic": "\x89PNG\r\n\x1a\n", "stored_path": "private/u/a.png",
                 "private_access": True, "auth_required": True, "decoded_and_reencoded": True}]
    ok_issues = [i for i in audit_matrix(ok_items) if i["severity"] == "S1"]
    checks.append(("合规条目零 S1", not ok_issues))

    cases = "\n".join(show_cases())
    checks.append(("cases 说明图片马", "图片马" in cases))
    checks.append(("cases 说明 presign bearer", "bearer token" in cases))

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {n}")
    if failed:
        print(f"SELFTEST RED（{len(failed)} 项失败）")
        return 1
    print(f"SELFTEST GREEN（{len(checks)} 项断言）")
    print("边界：自检只证明本脚本规则逻辑可用，不证明线上上传安全，不冒充合规。")
    return 0


def main(argv: list[str]) -> int:
    o = parse_args(argv)
    if o["self"]:
        return self_test()
    if o["cmd"] == "scan":
        root = Path(o["path"] or ".")
        if not root.exists():
            print(f"路径不存在: {root}")
            return 2
        hits = scan(root)
        print_scan(hits, o["format"])
        return 1 if (o["fail"] and any(h["severity"] == "HIGH" for h in hits)) else 0
    if o["cmd"] == "matrix":
        if not o["file"]:
            print("用法: upload-audit.py matrix --file uploads.json")
            return 2
        try:
            obj = json.loads(Path(o["file"]).read_text(encoding="utf-8-sig"))
        except Exception as e:
            print(f"读取清单失败: {e}")
            return 2
        items = obj.get("items") if isinstance(obj, dict) else obj
        issues = audit_matrix(items or [])
        print_matrix(issues, o["format"])
        return 1 if (o["fail"] and any(i["severity"] == "S1" for i in issues)) else 0
    if o["cmd"] == "cases":
        if o["format"] == "json":
            print(json.dumps({"tool": "upload-audit", "mode": "cases",
                              "magic_not_enough": True, "presign_is_bearer": True,
                              "note": "确定性规则，不替代线上实测"}, ensure_ascii=False, indent=2))
        else:
            print("\n".join(show_cases()))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(3)
