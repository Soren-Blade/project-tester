#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Webhook / 异步消息交付可靠性离线审计（R-16 配套，零依赖）。

用法：
  python scripts/webhook-audit.py check --file deliveries.json [--tolerance 300]
                                        [--format text|json] [--fail-on-gap]
  python scripts/webhook-audit.py verify --scheme standard --id msg_1 --timestamp 1700000000 \
                                        --payload '{"a":1}' --secret whsec_xxx --signature 'v1,...'
  python scripts/webhook-audit.py --self-test

check 输入（JSON）：
{
  "audit": {"tolerance_seconds": 300, "scheme": "standard"},
  "deliveries": [
    {"event_id":"evt_1","type":"payment.captured","sequence":1,
     "created_at":"2026-11-14T01:00:00Z","delivered_at":"2026-11-14T01:00:01Z",
     "attempt":1,"signature":"v1,...","signed_fields":["id","timestamp","body"],
     "http_status":200,"consumer_processed":true,"processed_at":"...",
     "dedup_key":null,"retry_after_seconds":null,"final":false,"dlq":false}
  ]
}

规则编号：
  WH-01 无签名 / 空签名                              （HIGH）
  WH-02 签名未覆盖 id+timestamp（可重放）              （HIGH）
  WH-03 缺事件时间戳                                  （HIGH）
  WH-04 交付/处理时间与事件时间偏差超过容忍窗（重放）    （HIGH）
  WH-05 同一 event_id 被处理多次且无去重证据（重复扣款） （S1）
  WH-06 重试间隔未递增（无退避，打爆下游）              （MEDIUM）
  WH-07 失败后既不重试也不进 DLQ（静默丢失）            （HIGH）
  WH-08 最终失败未落 DLQ                              （HIGH）
  WH-09 有序事件被乱序处理且无补偿                      （MEDIUM）
  WH-10 返回 4xx/5xx 却标记已处理（假成功）             （S1）
  WH-11 返回 2xx 却未处理且不再重试（静默丢弃）          （HIGH）

诚实边界：
- 只读本地交付日志/本地签名参数，**不联网**、**不代填**任何字段。
- 日志自洽**不证明**真实渠道按此行为；未命中**不证明**交付可靠。
- verify 只证明「给定 payload+secret 能/不能复算出该签名」，**不证明**密钥真实、不证明业务幂等。
- 不冒充「消息必达」「支付成功」，不替代真实渠道联调与对账。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def parse_ts(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    s = str(value).strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def parse_epoch(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        dt = parse_ts(value)
        return int(dt.timestamp()) if dt else None


def b64d(data: str) -> bytes:
    data = data.strip()
    pad = "=" * (-len(data) % 4)
    return base64.b64decode(data + pad)


def standard_expected(secret: str, msg_id: str, ts: str, payload: str) -> tuple[str, bytes]:
    key = b64d(secret[len("whsec_"):]) if secret.startswith("whsec_") else secret.encode()
    content = f"{msg_id}.{ts}.{payload}".encode()
    sig = base64.b64encode(hmac.new(key, content, hashlib.sha256).digest()).decode()
    return sig, content


def stripe_expected(secret: str, ts: str, payload: str) -> str:
    return hmac.new(secret.encode(), f"{ts}.{payload}".encode(), hashlib.sha256).hexdigest()


def verify(scheme: str, secret: str, msg_id: str | None, ts: str, payload: str,
           signature: str, tolerance: int) -> list[str]:
    reasons: list[str] = []
    epoch = parse_epoch(ts)
    if epoch is None:
        reasons.append("时间戳无法解析，无法判断重放窗口")
    else:
        skew = abs(int(datetime.now(tz=timezone.utc).timestamp()) - epoch)
        reasons.append(f"时钟偏差 {skew}s（容忍 {tolerance}s）"
                       + ("" if skew <= tolerance else " → 超出窗口，按重放拒绝"))
    if scheme == "standard":
        if not msg_id:
            reasons.append("standard 方案缺少消息 id（签名内容为 id.timestamp.body）")
        exp, content = standard_expected(secret, msg_id or "", ts, payload)
        got = [p.split(",", 1)[1] for p in signature.split() if "," in p and p.split(",", 1)[0] == "v1"]
        ok = any(hmac.compare_digest(exp, g) for g in got)
        reasons.append(f"签名复算 {'一致' if ok else '不一致'}（内容 {content[:40]!r}…）")
    elif scheme == "stripe":
        exp = stripe_expected(secret, ts, payload)
        parts = dict(p.split("=", 1) for p in signature.split(",") if "=" in p)
        got = parts.get("v1", "")
        ok = hmac.compare_digest(exp, got)
        reasons.append(f"签名复算 {'一致' if ok else '不一致'}（内容 t.payload，hex）")
    else:
        return [f"未知 scheme: {scheme}（支持 standard / stripe）"]
    if not ok:
        reasons.append("结论：签名不可复算，按伪造/篡改处理")
    return reasons


def check_deliveries(obj: dict, default_tolerance: int = 300) -> tuple[list[dict], dict]:
    issues: list[dict] = []
    audit = obj.get("audit") or {}
    tolerance = int(audit.get("tolerance_seconds", default_tolerance) or default_tolerance)
    rows = obj.get("deliveries") or obj.get("events") or []
    meta = {"deliveries": len(rows), "events": 0, "tolerance_seconds": tolerance}

    if not rows:
        return [{"id": "WH-00", "severity": "S1", "reason": "无交付记录，无法验证可靠性"}], meta

    def add(rid, sev, reason, event_id=None):
        issues.append({"id": rid, "severity": sev, "reason": reason, "event_id": event_id})

    events: dict[str, list[dict]] = {}
    for idx, d in enumerate(rows):
        if not isinstance(d, dict):
            add("WH-00", "S1", f"第 {idx} 条记录不是对象")
            continue
        eid = d.get("event_id") or d.get("id")
        if not eid:
            add("WH-00", "S1", f"第 {idx} 条记录缺 event_id")
            continue
        events.setdefault(str(eid), []).append(d)

        sig = d.get("signature")
        if not sig or not str(sig).strip() or "REPLACE" in str(sig).upper():
            add("WH-01", "HIGH", f"第 {idx} 条无签名/占位签名", eid)
        fields = [str(f).lower() for f in (d.get("signed_fields") or [])]
        if fields and ("id" not in fields or "timestamp" not in fields):
            add("WH-02", "HIGH", f"签名仅覆盖 {fields}，未覆盖 id+timestamp，可跨消息重放", eid)

        created = parse_ts(d.get("created_at"))
        if created is None:
            add("WH-03", "HIGH", "缺事件时间戳 created_at，无法判定乱序与重放窗口", eid)
        else:
            anchor = parse_ts(d.get("delivered_at")) or parse_ts(d.get("processed_at"))
            if anchor:
                skew = abs((anchor - created).total_seconds())
                if skew > tolerance:
                    add("WH-04", "HIGH",
                        f"交付/处理与事件时间相差 {skew:.0f}s > {tolerance}s（重放或积压）", eid)

        status = d.get("http_status")
        processed = d.get("consumer_processed")
        if isinstance(status, int) and status >= 400 and processed is True:
            add("WH-10", "S1", f"返回 HTTP {status} 却标记已处理（假成功，上游不会重试）", eid)
        final = bool(d.get("final"))
        dlq = bool(d.get("dlq"))
        if isinstance(status, int) and 200 <= status < 300 and processed is False and final and not dlq:
            add("WH-11", "HIGH", f"返回 HTTP {status} 但未处理且为最终尝试，消息静默丢弃", eid)
        failed = (isinstance(status, int) and status >= 400) or processed is False
        if failed and final and not dlq:
            add("WH-08", "HIGH", "最终失败未落 DLQ，无法人工补偿/重放", eid)

    meta["events"] = len(events)
    for eid, ds in events.items():
        ds = sorted(ds, key=lambda x: int(x.get("attempt") or 0))
        # 重复处理
        processed_count = sum(1 for d in ds if d.get("consumer_processed") is True)
        has_dedup = any(d.get("dedup_key") for d in ds) or any(
            str(d.get("dedup_result", "")).lower() in {"duplicate", "deduped"} for d in ds)
        if processed_count > 1 and not has_dedup:
            add("WH-05", "S1",
                f"同一 event_id 被处理 {processed_count} 次且无 dedup_key/去重结果（可能重复扣款/重复发货）", eid)
        # 退避
        intervals = [d.get("retry_after_seconds") for d in ds if d.get("retry_after_seconds") is not None]
        ints = [float(x) for x in intervals]
        if len(ints) >= 2 and any(b <= a for a, b in zip(ints, ints[1:])):
            add("WH-06", "MEDIUM", f"重试间隔 {ints} 未严格递增（无指数退避/抖动）", eid)
        # 丢弃
        last = ds[-1]
        last_failed = ((isinstance(last.get("http_status"), int) and last["http_status"] >= 400)
                       or last.get("consumer_processed") is False)
        if last_failed and not last.get("dlq") and not last.get("retry_after_seconds") \
                and not last.get("final") and len(ds) == 1:
            add("WH-07", "HIGH", "唯一一次失败后既不重试也未进 DLQ（静默丢失）", eid)
        # 乱序
        seqs = [(d.get("sequence"), parse_ts(d.get("processed_at"))) for d in ds
                if d.get("sequence") is not None and d.get("processed_at")]
        if len(seqs) >= 2:
            seqs.sort(key=lambda x: float(x[0]))
            times = [t for _, t in seqs]
            if any(b < a for a, b in zip(times, times[1:])):
                add("WH-09", "MEDIUM",
                    f"序号 {[s for s, _ in seqs]} 的处理时间非单调（乱序处理且无补偿证据）", eid)
    return issues, meta


def print_check(issues: list[dict], meta: dict, fmt: str) -> None:
    hard = [i for i in issues if i["severity"] in ("S1", "HIGH")]
    if fmt == "json":
        print(json.dumps({"tool": "webhook-audit", "mode": "check", "meta": meta,
                          "issues": issues, "gaps": len(hard),
                          "note": "日志自洽不证明真实渠道行为；不联网、不代填"},
                         ensure_ascii=False, indent=2))
        return
    print(f"# 交付日志审计：{meta['deliveries']} 条交付 / {meta['events']} 个事件 / 容忍 {meta['tolerance_seconds']}s")
    for i in issues:
        print(f"[{i['id']} {i['severity']}] {i.get('event_id') or '-'}  {i['reason']}")
    print(f"> 硬缺口 {len(hard)} 项；日志只能证明『记录里发生了什么』，真实渠道需联调+渠道侧对账。")


def self_test() -> int:
    checks: list[tuple[str, bool]] = []
    secret = "whsec_" + base64.b64encode(b"selftest-secret-key").decode()
    payload = '{"id":"evt_1","amount":100}'
    msg_id = "msg_1"
    ts = "1700000000"
    sig, _ = standard_expected(secret, msg_id, ts, payload)
    header = f"v1,{sig}"
    ok_reasons = verify("standard", secret, msg_id, ts, payload, header, 300)
    checks.append(("standard 签名可复算", any("一致" in r and "不一致" not in r for r in ok_reasons)))
    bad = verify("standard", secret, msg_id, ts, payload + " ", header, 300)
    checks.append(("篡改 payload 后签名不一致", any("不一致" in r for r in bad)))
    stripe_sig = stripe_expected("sk_test", ts, payload)
    stripe_header = f"t={ts},v1={stripe_sig}"
    sr = verify("stripe", "sk_test", None, ts, payload, stripe_header, 300)
    checks.append(("stripe 签名可复算", any("一致" in r and "不一致" not in r for r in sr)))

    now = int(datetime.now(tz=timezone.utc).timestamp())
    fixture = {"audit": {"tolerance_seconds": 300}, "deliveries": [
        {"event_id": "evt_dup", "type": "payment.captured", "sequence": 1,
         "created_at": now, "delivered_at": now, "attempt": 1, "signature": "v1,x",
         "signed_fields": ["body"], "http_status": 200, "consumer_processed": True,
         "processed_at": now, "dedup_key": None, "final": False, "dlq": False},
        {"event_id": "evt_dup", "type": "payment.captured", "sequence": 1,
         "created_at": now, "delivered_at": now + 5, "attempt": 2, "signature": "v1,x",
         "signed_fields": ["body"], "http_status": 200, "consumer_processed": True,
         "processed_at": now + 5, "dedup_key": None, "final": False, "dlq": False},
        {"event_id": "evt_fail", "type": "shipment.created", "sequence": 2,
         "created_at": now, "delivered_at": now, "attempt": 1, "signature": "",
         "signed_fields": ["id", "timestamp", "body"], "http_status": 500,
         "consumer_processed": True, "processed_at": now, "final": True, "dlq": False},
        {"event_id": "evt_old", "type": "refund.created", "sequence": 3,
         "created_at": now - 7200, "delivered_at": now, "attempt": 1, "signature": "v1,y",
         "signed_fields": ["id", "timestamp", "body"], "http_status": 200,
         "consumer_processed": False, "final": True, "dlq": False},
    ]}
    issues, meta = check_deliveries(fixture)
    ids = {i["id"] for i in issues}
    for rid in ("WH-01", "WH-02", "WH-04", "WH-05", "WH-08", "WH-10", "WH-11"):
        checks.append((f"check 检出 {rid}", rid in ids))
    checks.append(("事件数统计正确", meta["events"] == 3))

    clean = {"audit": {"tolerance_seconds": 300}, "deliveries": [
        {"event_id": "evt_ok", "type": "payment.captured", "sequence": 1,
         "created_at": now, "delivered_at": now + 1, "attempt": 1, "signature": "v1,ok",
         "signed_fields": ["id", "timestamp", "body"], "http_status": 200,
         "consumer_processed": True, "processed_at": now + 1, "dedup_key": "evt_ok",
         "final": False, "dlq": False},
    ]}
    ok_issues, _ = check_deliveries(clean)
    checks.append(("干净交付零缺口", not ok_issues))

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {n}")
    if failed:
        print(f"SELFTEST RED（{len(failed)} 项失败）")
        return 1
    print(f"SELFTEST GREEN（{len(checks)} 项断言）")
    print("边界：自检只证明本脚本的签名复算/日志审计逻辑可用，不证明真实渠道交付可靠，不冒充消息必达。")
    return 0


def parse_args(argv: list[str]) -> dict:
    opts = {"cmd": None, "self": False, "format": "text", "fail": False,
            "file": None, "scheme": "standard", "id": None, "timestamp": None,
            "payload": None, "payload_file": None, "secret": None,
            "signature": None, "tolerance": 300}
    rest = argv[1:]
    if "--self-test" in rest:
        opts["self"] = True
        return opts
    if not rest:
        return opts
    opts["cmd"] = rest[0]
    i = 1
    while i < len(rest):
        a = rest[i]
        val = rest[i + 1] if i + 1 < len(rest) else None
        if a == "--file":
            opts["file"] = val; i += 2
        elif a == "--format":
            opts["format"] = val; i += 2
        elif a == "--fail-on-gap":
            opts["fail"] = True; i += 1
        elif a == "--scheme":
            opts["scheme"] = val; i += 2
        elif a == "--id":
            opts["id"] = val; i += 2
        elif a == "--timestamp":
            opts["timestamp"] = val; i += 2
        elif a == "--payload":
            opts["payload"] = val; i += 2
        elif a == "--payload-file":
            opts["payload_file"] = val; i += 2
        elif a == "--secret":
            opts["secret"] = val; i += 2
        elif a == "--signature":
            opts["signature"] = val; i += 2
        elif a == "--tolerance":
            opts["tolerance"] = int(val or 300); i += 2
        else:
            i += 1
    return opts


def main(argv: list[str]) -> int:
    opts = parse_args(argv)
    if opts["self"]:
        return self_test()
    if opts["cmd"] == "check":
        if not opts["file"]:
            print("用法: webhook-audit.py check --file deliveries.json")
            return 2
        try:
            obj = json.loads(Path(opts["file"]).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"读取交付日志失败: {e}")
            return 2
        issues, meta = check_deliveries(obj, opts["tolerance"])
        print_check(issues, meta, opts["format"])
        hard = [i for i in issues if i["severity"] in ("S1", "HIGH")]
        return 1 if (opts["fail"] and hard) else 0
    if opts["cmd"] == "verify":
        payload = opts["payload"]
        if opts["payload_file"]:
            payload = Path(opts["payload_file"]).read_text(encoding="utf-8")
        if payload is None or opts["secret"] is None or opts["signature"] is None or opts["timestamp"] is None:
            print("verify 需要 --timestamp --secret --signature，以及 --payload 或 --payload-file")
            return 2
        reasons = verify(opts["scheme"], opts["secret"], opts["id"], str(opts["timestamp"]),
                         payload, opts["signature"], opts["tolerance"])
        for r in reasons:
            print(f"- {r}")
        bad = [r for r in reasons if "不一致" in r or "无法解析" in r or "超出窗口" in r or "伪造" in r]
        return 1 if bad else 0
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
