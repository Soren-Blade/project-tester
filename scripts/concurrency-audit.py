#!/usr/bin/env python3
"""concurrency-audit.py — R-23「并发与幂等正确性」的静态线索与副作用对账。

用途
    scan 找 CC-01~CC-10 反模式线索（与手册第 9 节同号）；cases 打印 8 场景矩阵；
    side-effects 按幂等键聚合 JSONL 找「一键多副作用/多资源」；--self-test 证明三者真会命中/失败。

用法
    python scripts/concurrency-audit.py scan . [--format markdown|json] [--fail-on-gap]
    python scripts/concurrency-audit.py cases
    python scripts/concurrency-audit.py side-effects --events events.jsonl --fail-on-gap
    python scripts/concurrency-audit.py --self-test

退出码
    0  无缺口；不带 --fail-on-gap 时永远 0，只报告——「跑过了」不等于「通过了」。
    1  带 --fail-on-gap 且存在缺口（scan 有 HIGH / side-effects 有违规键）。
    2  参数错误、输入不可读、事件文件为空。

诚实边界
    **不联网、不代填结论、不证明服务端并发安全**。命中 CC 规则只说明「这里值得
    人看」，可能有误报；未命中也不代表并发安全。结论必须来自真并发用例（屏障同时
    发射）+ 数据库不变量对账 + 幂等键矩阵。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(".")
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__", ".workbuddy-ai"}
SUFFIXES = {".py", ".js", ".ts", ".tsx", ".go", ".java", ".kt",
            ".rb", ".php", ".sql", ".prisma", ".yml", ".yaml"}
MAX_BYTES = 512 * 1024  # 超大文件（生成物、压缩包）不读，避免把扫描变成 IO 灾难
HIGH, MEDIUM = "HIGH", "MEDIUM"
# 只有这些片段才当「疑似分布式锁」；进程内 threading.Lock 不在此列
DIST_LOCK = re.compile(r"redlock|redislock|setnx|set_nx|zookeeper|\betcd\b|SET\s+\S+\s+\S+\s+NX", re.I)

def snippet(line: str, width: int = 110) -> str:
    """把一行压成能进表格的片段：去首尾空白、折叠空白、超长截断、转义竖线。"""
    s = " ".join(line.strip().split())
    return s[:width].replace("|", "\\|") + ("..." if len(s) > width else "")


# ---------------------------------------------------------------- 规则实现（返回 1-based 行号；空列表=没找到）

def _hits(lines: list[str], pattern: str, limit: int = 3) -> list[int]:
    """返回匹配 pattern 的 1-based 行号，最多 limit 条（所有规则共用的取行器）。"""
    rx = re.compile(pattern, re.I)
    return [i + 1 for i, l in enumerate(lines) if rx.search(l)][:limit]


def cc01_check_then_insert(lines: list[str], text: str) -> list[int]:
    """先查后插、且全文件没有任何唯一约束：并发下必然能插进两条。"""
    if re.search(r"unique\s*=\s*True|\bUNIQUE\b|UniqueConstraint|@unique|uniq_", text, re.I):
        return []
    lookups = _hits(lines, r"\.(first|exists|count)\s*\(|\bSELECT\b.*\bFROM\b", 5)
    inserts = _hits(lines, r"\.create\s*\(|\.save\s*\(|INSERT\s+INTO|insertOne\s*\("
                           r"|\b(?:session|db|self\.db)\.add\s*\(", 5)
    return [i for i in inserts if any(k < i for k in lookups)][:2]


def cc02_read_modify_write(lines: list[str], text: str) -> list[int]:
    """应用层读改写：先读进内存，加减后再写回，并发下 lost update。"""
    pat = re.compile(r"(\w+)\.(\w+)\s*=\s*\1\.\2\s*[-+]"
                     r"|\b(balance|stock|amount|count|points|quota|total)\s*=\s*\3\s*[-+]"
                     r"|SET\s+(balance|stock|amount|count|points|quota)\s*=\s*[?%$:]")
    atomic_sql = re.compile(r"\bSET\s+\w+\s*=\s*\w+\s*[-+*/]", re.I)  # SET stock = stock - ? 是对的
    return [i + 1 for i, l in enumerate(lines)
            if pat.search(l) and not atomic_sql.search(l)][:3]


def cc03_setnx_then_expire(lines: list[str], text: str) -> list[int]:
    """SETNX 与 EXPIRE 分两步：中间崩溃就是永久死锁，而且不是原子的。"""
    if not re.search(r"\bpexpire\b|\bexpire\s*\(|EXPIRE\s+\w+", text, re.I):
        return []
    if re.search(r"\b(?:ex|px)\s*[= ]\s*\d", text, re.I):
        return []  # 单条 SET ... NX EX 60 已是原子写法，不报
    return _hits(lines, r"setnx|set_nx|setIfAbsent|\bSET\b\s+\S+\s+\S+\s+NX\b", 2)


def cc04_transactional_self_call(lines: list[str], text: str) -> list[int]:
    """@Transactional 方法被同类 this/self 调用：绕过代理，注解形同虚设。"""
    return _hits(lines, r"\b(self|this)\.\w+\s*\(", 2) if "@Transactional" in text else []


def cc05_stock_decrement_no_guard(lines: list[str], text: str) -> list[int]:
    """扣库存不带 WHERE stock >= n：永远更新成功，扣成负数也不报错。"""
    if re.search(r"rowcount", text, re.I):
        return []
    return [i + 1 for i, l in enumerate(lines)
            if re.search(r"stock\s*=\s*stock\s*-", l, re.I)
            and not re.search(r"stock\s*>=\s*|>=\s*\w*stock", l, re.I)][:2]


def cc06_key_compared_not_persisted(lines: list[str], text: str) -> list[int]:
    """幂等键只拿来比对、不落库：重启或别的实例照样能执行第二次。"""
    if not re.search(r"idempotency[_-]?key|idem_key|Idempotency-Key", text, re.I):
        return []
    if re.search(r"(INSERT\s+INTO|UPDATE|\.save|\.create|\.add|\.put_item)[^;\n]*?(idem|key)"
                 r"|(idem|key)[^;\n]*?(INSERT\s+INTO|\.save|\.create|\.put_item)", text, re.I):
        return []
    return _hits(lines, r"(idem\w*|key)\s*(==|!=)|(==|!=)\s*(idem\w*|key)", 2)


def cc07_select_then_update(lines: list[str], text: str) -> list[int]:
    """先 SELECT 再 UPDATE、既不加锁也不用版本号：读写之间就是并发窗口。"""
    if re.search(r"\bFOR\s+UPDATE\b|select_for_update|lock\s*=\s*True|\bversion\b", text, re.I):
        return []
    selects = _hits(lines, r"\bSELECT\b", 5)
    updates = _hits(lines, r"\bUPDATE\b\s+\w+\s+SET", 5)
    return [i for i in updates if any(s < i for s in selects)][:2]


def cc08_lock_without_fencing(lines: list[str], text: str) -> list[int]:
    """分布式锁没有 fencing token：锁过期后旧持有者仍能写，等于没锁。"""
    if re.search(r"fencing|fence", text, re.I):
        return []
    return _hits(lines, DIST_LOCK.pattern + r"|acquire_lock|acquire\s*\(", 2)


def cc09_get_or_create_no_fallback(lines: list[str], text: str) -> list[int]:
    """get_or_create 无唯一约束 + IntegrityError 兜底：并发时第二个请求 500。"""
    if not re.search(r"get_or_create|getOrCreate|get_or_insert|first_or_create", text, re.I):
        return []
    if re.search(r"IntegrityError|DuplicateKey|duplicate key|unique\s*=\s*True|\bUNIQUE\b", text, re.I):
        return []
    return _hits(lines, r"get_or_create|getOrCreate|get_or_insert|first_or_create", 2)


def cc10_ack_before_process(lines: list[str], text: str) -> list[int]:
    """消费者先 ack 再处理：处理失败消息已丢，副作用不会重试，更谈不上「恰好一次」。"""
    if re.search(r"auto_ack\s*=\s*True|autoAck\s*:\s*true|auto_ack\s*:\s*true", text, re.I):
        return _hits(lines, r"auto_ack|autoAck", 2)
    acks = _hits(lines, r"\.ack\s*\(|basic_ack|acknowledge\s*\(|commit_message|offset_commit", 5)
    handles = _hits(lines, r"def\s+(process|handle|consume)|\.process\s*\(|handle_message"
                            r"|do_work|consume_message|\.handle\s*\(", 5)
    return [a for a in acks if any(h > a for h in handles)][:2]


RULES: list[dict[str, Any]] = [
    {"id": "CC-01", "severity": HIGH, "fn": cc01_check_then_insert, "title": "先查后插且无唯一约束",
     "message": "并发下两个请求都能通过存在性检查；补 UNIQUE 约束并对冲突返回 409，不要只靠应用层判断。"},
    {"id": "CC-02", "severity": HIGH, "fn": cc02_read_modify_write, "title": "应用层读改写余额/库存",
     "message": "读出来再算再写回属于 lost update；改成原子 SET x = x - ? 或 WHERE version = ? 的 CAS 并核对影响行数。"},
    {"id": "CC-03", "severity": HIGH, "fn": cc03_setnx_then_expire, "title": "SETNX 后再 EXPIRE",
     "message": "两步之间崩溃即永久持锁；用单条 SET key val NX PX 60000 原子加锁，并对 TTL 续期与设上限。"},
    {"id": "CC-04", "severity": MEDIUM, "fn": cc04_transactional_self_call, "title": "@Transactional 方法被同类自调用",
     "message": "自调用绕过 Spring 代理，事务不生效；把方法挪到另一个 bean，或在入口方法上加事务。"},
    {"id": "CC-05", "severity": HIGH, "fn": cc05_stock_decrement_no_guard, "title": "扣库存无 WHERE stock >= n",
     "message": "加上 WHERE stock >= ? 并检查 rowcount：0 行即库存不足，不能当成成功。"},
    {"id": "CC-06", "severity": HIGH, "fn": cc06_key_compared_not_persisted, "title": "幂等键只比对不落库",
     "message": "键必须与结果一起持久化（唯一索引 + 首次响应），否则重启、换实例、并发都能再执行一次。"},
    {"id": "CC-07", "severity": HIGH, "fn": cc07_select_then_update, "title": "SELECT 后 UPDATE，无锁无版本号",
     "message": "用 SELECT ... FOR UPDATE、版本号 CAS 或单条条件更新；读与写之间不能留无人防守的窗口。"},
    {"id": "CC-08", "severity": HIGH, "fn": cc08_lock_without_fencing, "title": "分布式锁无 fencing token",
     "message": "锁过期后旧持有者仍可写；写入必须携带单调递增 fencing token 并由存储端拒绝旧 token。"},
    {"id": "CC-09", "severity": MEDIUM, "fn": cc09_get_or_create_no_fallback, "title": "get_or_create 无竞态兜底",
     "message": "并发首建会撞唯一约束；捕获 IntegrityError/DuplicateKey 后回查，避免把可重试冲突变成 500。"},
    {"id": "CC-10", "severity": HIGH, "fn": cc10_ack_before_process, "title": "消费者先 ack 后处理",
     "message": "处理完成（副作用已提交）之后再 ack；否则进程崩溃时消息已确认，副作用永久丢失。"},
]


def scan_file(path: Path, root: Path) -> list[dict[str, Any]]:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    if "\x00" in raw[:2048] or len(raw) > MAX_BYTES:
        return []
    lines = raw.splitlines()
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for rule in RULES:
        for lineno in rule["fn"](lines, raw):
            if (rule["id"], lineno) in seen or not (1 <= lineno <= len(lines)):
                continue
            seen.add((rule["id"], lineno))
            findings.append({
                "id": rule["id"], "path": path.relative_to(root).as_posix(), "line": lineno,
                "snippet": snippet(lines[lineno - 1]), "severity": rule["severity"],
                "message": f"{rule['title']}：{rule['message']}"})
    return findings


def iter_files(root: Path) -> Iterator[Path]:
    """遍历 root 下受支持的后缀；跳过 SKIP_DIRS（只按相对 root 的目录判断）与脚本自身。"""
    me = Path(__file__).resolve()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUFFIXES:
            continue
        try:
            rel_parts = path.relative_to(root).parts[:-1]
            resolved = path.resolve()
        except (ValueError, OSError):
            continue
        # root 本身在 .workbuddy-ai 下时（如 dogfood 夹具）仍然要能扫
        if any(part in SKIP_DIRS for part in rel_parts) or resolved == me:
            continue
        yield path


def scan(root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in iter_files(root):
        findings.extend(scan_file(path, root))
    findings.sort(key=lambda f: (f["path"], f["line"], f["id"]))
    return findings


def fmt_scan_markdown(findings: list[dict[str, Any]], root: Path) -> str:
    out = [f"# 并发/幂等静态线索（scan {root}）", ""]
    if not findings:
        return "\n".join(out + ["未命中 CC-01 ~ CC-10。**这不等于并发安全**：静态线索只能提示该看哪里。"])
    out += ["| 编号 | 级别 | 位置 | 证据片段 | 说明 |", "|---|---|---|---|---|"]
    for f in findings:
        out.append(f"| {f['id']} | {f['severity']} | `{f['path']}:{f['line']}` | "
                   f"`{f['snippet']}` | {f['message']} |")
    out += ["", f"合计 {len(findings)} 条：" + "、".join(sorted({f["id"] for f in findings})),
            "> 命中只代表「这里值得人看」，需逐条裁决为真问题或误报；未命中不代表并发安全。"]
    return "\n".join(out)


# ---------------------------------------------------------------- cases
CASES = """# 并发用例矩阵（R-23 标准 8 场景）

| 用例 ID | 场景 | 并发度 N | 前置数据 | 期望 | 实测 | 判定 |
|---|---|---|---|---|---|---|
| CC-21 | 超卖（库存 10，N 个并发下单） | 20 | stock=10 | 成功 <= 10 且 `MIN(stock) >= 0` | | |
| CC-20 | lost update（两笔各 -10，余额 100） | 2 | balance=100 | 终值 80，差额 0 | | |
| CC-22 | 双提交（同键同体 N 次） | 10 | 同一 Idempotency-Key | 资源 1 个，返回首次结果 | | |
| CC-23 | 唯一插入竞争（同邮箱注册） | 10 | 无该邮箱 | 1 成功 + 9x409，无 500 | | |
| CC-24 | 幂等重放（键命中第二次） | 5 | 已有键记录 | 副作用总计 1 次 | | |
| CC-26 | 锁过期双持有 | 2 | TTL=1s，临界区 3s | 旧持有者写入被拒 / 无交叠 | | |
| CC-27 | 跨用户键复用（A 的键给 B 用） | 2 | A 已成功 | 4xx 拒绝，不回放 A 的结果 | | |
| CC-28 | 多消费者重复消费（同 event_id） | 4 | 同一消息投递 4 次 | 副作用 1 次 | | |

> N 必须是真并发的执行体数量（线程池 + Barrier / xargs -P / k6 constant-arrival），并注明是否同进程、实例数；
> 串行 for 循环 + sleep 造出来的绿是装饰。判定只能填 PASS / FAIL / 未验证，证据路径写 run.log 或对账 SQL。
"""


# ---------------------------------------------------------------- side-effects
def load_events(path: Path) -> tuple[list[dict[str, Any]], int]:
    """逐行读事件；容忍空行与 # 注释，坏行跳过并计数（stderr warn）。"""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise SystemExit(f"[concurrency-audit] 读不了事件文件：{path}（{exc}）")
    events: list[dict[str, Any]] = []
    bad = 0
    for lineno, line in enumerate(raw.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            obj = None
        if not isinstance(obj, dict) or not isinstance(obj.get("key"), str) or not obj["key"]:
            bad += 1
            print(f"warn: 第 {lineno} 行不是合法事件，已跳过", file=sys.stderr)
            continue
        se = obj.get("side_effects", 0)
        if not isinstance(se, int) or se < 0:
            bad += 1
            print(f"warn: 第 {lineno} 行 side_effects 非法，已跳过", file=sys.stderr)
            continue
        obj["side_effects"] = se
        events.append(obj)
    return events, bad


def aggregate(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按 key 聚合：副作用总数 > 1 或资源数 > 1 都算缺口。"""
    groups: dict[str, dict[str, Any]] = {}
    for ev in events:
        g = groups.setdefault(str(ev["key"]), {
            "key": str(ev["key"]), "attempts": 0,
            "resource_ids": set(), "max_side_effects": 0, "total_side_effects": 0, "statuses": []})
        g["attempts"] += 1
        if isinstance(ev.get("resource_id"), str) and ev["resource_id"]:
            g["resource_ids"].add(ev["resource_id"])
        g["max_side_effects"] = max(g["max_side_effects"], ev["side_effects"])
        g["total_side_effects"] += ev["side_effects"]
        if isinstance(ev.get("status"), int):
            g["statuses"].append(ev["status"])
    rows = []
    for g in groups.values():
        dup, multi = g["total_side_effects"] > 1, len(g["resource_ids"]) > 1
        rows.append({
            "key": g["key"], "attempts": g["attempts"],
            "resource_ids": sorted(g["resource_ids"]), "distinct_resource_ids": len(g["resource_ids"]),
            "max_side_effects": g["max_side_effects"], "total_side_effects": g["total_side_effects"],
            "statuses": g["statuses"], "duplicate_side_effect": dup, "multi_resource": multi,
            "verdict": "GAP" if (dup or multi) else "OK"})
    rows.sort(key=lambda r: (r["verdict"] != "GAP", r["key"]))
    return rows


def fmt_events_markdown(rows: list[dict[str, Any]], total_events: int, bad: int) -> str:
    out = ["# 幂等键副作用对账（side-effects）", "",
           "| 键 | attempts | 资源数 | max 副作用 | 总副作用 | 状态码 | 判定 |",
           "|---|---|---|---|---|---|---|"]
    for r in rows:
        flag = [n for n, on in (("副作用>1", r["duplicate_side_effect"]),
                                ("多资源", r["multi_resource"])) if on]
        out.append(f"| `{r['key']}` | {r['attempts']} | {r['distinct_resource_ids']} | "
                   f"{r['max_side_effects']} | {r['total_side_effects']} | "
                   f"{','.join(str(s) for s in r['statuses'])} | "
                   f"{'GAP：' + '/'.join(flag) if flag else 'OK'} |")
    gaps = [r for r in rows if r["verdict"] == "GAP"]
    out += ["", f"汇总：键 {len(rows)} 个、事件 {total_events} 条、坏行 {bad} 条、违规键 {len(gaps)} 个。"]
    if gaps:
        out += ["", "违规键：" + "、".join(f"`{g['key']}`" for g in gaps)]
    out += ["", "> `duplicate_side_effect`（总副作用 > 1）与 `multi_resource`（资源数 > 1）"
                "任一命中，即「同一幂等键没能收住」，不得在报告里写「幂等生效」。"]
    return "\n".join(out)


# ---------------------------------------------------------------- self-test
FIXTURES = {
    "svc.py": (
        "def create_order(db, body):\n"
        "    if db.query(Order).filter_by(no=body['no']).first():\n"
        "        return 409\n"
        "    return db.add(Order(no=body['no']))\n"
        "def debit(wallet, amount):\n"
        "    wallet.balance = wallet.balance - amount\n"
        "def replay(req, row):\n"
        "    key = req.headers['Idempotency-Key']\n"
        "    if row.key == key:\n"
        "        return row.response\n"),
    "lock.py": (
        "def acquire(r, key):\n"
        "    ok = r.setnx(key, '1')\n"
        "    r.expire(key, 10)\n"
        "    return ok\n"
        "def stock(r, sku, n):\n"
        "    return r.execute('UPDATE stock SET stock = stock - ? WHERE sku = ?', n, sku)\n"
        "def read_then_write(r):\n"
        "    row = r.execute('SELECT qty FROM stock WHERE sku = ?', 'A1')\n"
        "    r.execute('UPDATE stock SET qty = ? WHERE sku = ?', row[0] - 1, 'A1')\n"
        "def get_or_create(db, **kw):\n"
        "    return db.query(T).filter_by(**kw).first() or db.add(T(**kw))\n"),
    "consumer.py": (
        "class S:\n"
        "    @Transactional\n"
        "    def run(self):\n"
        "        self.inner()\n"
        "    def inner(self):\n"
        "        pass\n"
        "def consume(msg):\n"
        "    msg.ack()\n"
        "    handle_message(msg.body)\n"),
}


def self_test() -> int:
    def fail(msg: str) -> int:
        print(f"SELFTEST FAIL: {msg}")
        return 1

    with tempfile.TemporaryDirectory(prefix="ca-selftest-") as tmp:
        base = Path(tmp)
        root = base / "repo"
        root.mkdir()
        for name, body in FIXTURES.items():
            (root / name).write_text(body, encoding="utf-8")
        found = {f["id"] for f in scan(root)}
        expect = {r["id"] for r in RULES}
        if expect - found:
            return fail(f"夹具未命中 {sorted(expect - found)}（实际 {sorted(found)}）")
        print(f"[ok] scan 命中全部 {len(expect)} 条规则")

        clean = base / "clean_only"
        clean.mkdir()
        (clean / "clean.py").write_text("def add(a: int, b: int) -> int:\n    return a + b\n",
                                        encoding="utf-8")
        if scan(clean):
            return fail("干净夹具出现误报")
        print("[ok] 干净夹具零误报")

        events_path = base / "events.jsonl"
        events_path.write_text(
            "# comment\n\n"
            '{"key":"k-1","attempt":1,"status":201,"resource_id":"r-9","side_effects":1,"ts":"t"}\n'
            '{"key":"k-1","attempt":2,"status":201,"resource_id":"r-9","side_effects":1,"ts":"t"}\n'
            '{"key":"k-2","attempt":1,"status":201,"resource_id":"r-10","side_effects":1,"ts":"t"}\n'
            '{"key":"k-2","attempt":2,"status":201,"resource_id":"r-11","side_effects":2,"ts":"t"}\n'
            '{"key":"k-3","attempt":1,"status":201,"resource_id":"r-12","side_effects":1,"ts":"t"}\n'
            "not-json\n", encoding="utf-8")
        events, bad = load_events(events_path)
        rows = {r["key"]: r for r in aggregate(events)}
        if bad != 1:
            return fail(f"坏行计数 {bad} != 1")
        if not rows["k-1"]["duplicate_side_effect"] or rows["k-1"]["multi_resource"]:
            return fail("k-1 应命中 duplicate_side_effect 且非 multi_resource")
        if not (rows["k-2"]["multi_resource"] and rows["k-2"]["duplicate_side_effect"]):
            return fail("k-2 应同时命中 multi_resource 与 duplicate_side_effect")
        if rows["k-3"]["verdict"] != "OK":
            return fail("k-3 不应违规")
        gap_keys = sorted(k for k, r in rows.items() if r["verdict"] == "GAP")
        if gap_keys != ["k-1", "k-2"]:
            return fail(f"违规键集合 {gap_keys} 不符")
        print("[ok] 重复副作用 / 多资源 / 坏行计数均按预期（含 --fail-on-gap 会判 1 的集合）")
        if "用例 ID" not in CASES or "并发度" not in CASES:
            return fail("cases 输出缺表头关键字")
        print("[ok] cases 表头齐全")

    print("SELFTEST GREEN")
    return 0


# ---------------------------------------------------------------- CLI
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="concurrency-audit.py",
        description="R-23 并发与幂等正确性：静态线索 scan / 并发用例 cases / 副作用对账 side-effects。")
    p.add_argument("--self-test", action="store_true", help="用临时夹具自检后退出")
    sub = p.add_subparsers(dest="cmd")
    s = sub.add_parser("scan", help="扫描并发/幂等反模式线索")
    s.add_argument("root", nargs="?", default=str(ROOT))
    s.add_argument("--format", choices=["markdown", "json"], default="markdown")
    s.add_argument("--fail-on-gap", action="store_true", help="存在 HIGH 时退出码 1")
    c = sub.add_parser("cases", help="打印 8 个标准并发场景矩阵")
    c.add_argument("--format", choices=["markdown", "json"], default="markdown")
    e = sub.add_parser("side-effects", help="按幂等键聚合事件流，找重复副作用")
    e.add_argument("--events", required=True, help="事件 JSONL 路径")
    e.add_argument("--format", choices=["markdown", "json"], default="markdown")
    e.add_argument("--fail-on-gap", action="store_true", help="任一键违规时退出码 1")
    return p


def cmd_scan(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if not root.is_dir():
        print(f"[concurrency-audit] 不是目录：{root}", file=sys.stderr)
        return 2
    findings = scan(root)
    if args.format == "json":
        counts = {r["id"]: 0 for r in RULES}
        for f in findings:
            counts[f["id"]] += 1
        print(json.dumps({
            "tool": "concurrency-audit.py", "mode": "scan", "root": str(root),
            "findings": findings,
            "summary": {"total": len(findings),
                        "high": sum(1 for f in findings if f["severity"] == HIGH),
                        "medium": sum(1 for f in findings if f["severity"] == MEDIUM),
                        "by_rule": counts},
            "honest_boundary": "不联网、不代填结论、不证明服务端并发安全"}, ensure_ascii=False, indent=2))
    else:
        print(fmt_scan_markdown(findings, root))
    high = [f for f in findings if f["severity"] == HIGH]
    if args.fail_on_gap and high:
        print(f"[fail] {len(high)} 条 HIGH 线索，--fail-on-gap 退出 1", file=sys.stderr)
        return 1
    return 0


def cmd_cases(args: argparse.Namespace) -> int:
    if args.format == "json":
        print(json.dumps({"mode": "cases", "cases": [
            {"id": "CC-21", "scenario": "超卖", "n": 20}, {"id": "CC-20", "scenario": "lost update", "n": 2},
            {"id": "CC-22", "scenario": "双提交", "n": 10}, {"id": "CC-23", "scenario": "唯一插入竞争", "n": 10},
            {"id": "CC-24", "scenario": "幂等重放", "n": 5}, {"id": "CC-26", "scenario": "锁过期双持有", "n": 2},
            {"id": "CC-27", "scenario": "跨用户键复用", "n": 2}, {"id": "CC-28", "scenario": "多消费者重复消费", "n": 4},
        ]}, ensure_ascii=False, indent=2))
    else:
        print(CASES)
    return 0


def cmd_side_effects(args: argparse.Namespace) -> int:
    path = Path(args.events)
    if not path.is_file():
        print(f"[concurrency-audit] 事件文件不存在：{path}", file=sys.stderr)
        return 2
    events, bad = load_events(path)
    if not events:
        print(f"[concurrency-audit] 事件文件没有可用行：{path}", file=sys.stderr)
        return 2
    rows = aggregate(events)
    gaps = [r for r in rows if r["verdict"] == "GAP"]
    if args.format == "json":
        print(json.dumps({
            "tool": "concurrency-audit.py", "mode": "side-effects", "events_file": str(path),
            "keys": rows,
            "summary": {"keys": len(rows), "events": len(events), "bad_lines": bad, "gap_keys": len(gaps)},
            "honest_boundary": "不联网、不代填结论、不证明服务端并发安全"}, ensure_ascii=False, indent=2))
    else:
        print(fmt_events_markdown(rows, len(events), bad))
    if args.fail_on_gap and gaps:
        print(f"[fail] {len(gaps)} 个键存在违规，--fail-on-gap 退出 1", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    handlers = {"scan": cmd_scan, "cases": cmd_cases, "side-effects": cmd_side_effects}
    handler = handlers.get(getattr(args, "cmd", None) or "")
    if handler is None:
        parser.print_help()
        return 2
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
