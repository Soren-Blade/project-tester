#!/usr/bin/env python3
"""jwt-audit.py — 离线 JWT/JWS 结构审计（零依赖）

用途
  decode : 解释 JWT 头部/载荷，列出结构性风险（alg=none、缺 exp/aud/iss、kid 可疑字符、
           jku/x5u/jwk 键注入面、弱 HMAC 密钥字典命中、过期判定），输出 markdown 或 JSON。
  verify : 显式给定 HMAC 密钥时校验 HS256/384/512 签名（常量时间比较），只回答「签名对得上吗」。
  --self-test : 用固定时间戳构造样本令牌，证明上述检测项确实可被检出（门禁本身可证伪）。

诚实边界（必须与结论一起引用）
  * 不联网：只读你给的令牌字符串与本地字典，不请求 JWKS、不查黑名单。
  * 不代填：不猜服务端配置、不代替被测系统做校验。
  * 不冒充：decode 的发现是「结构可疑」，**不证明**服务端真的接受了该令牌；
    未命中弱密钥字典 **不证明**密钥强；签名验证通过 **不证明**令牌未被重放或权限正确；
    JWE（5 段）只提示存在，不做解密；非 HMAC 算法不在 verify 范围内。
  * 真正的「服务端接受 alg=none / 过期令牌」结论，必须由实际请求的响应码与响应体证明（R-12）。

用法
  python jwt-audit.py decode --token <JWT> [--now 1700000000] [--format markdown|json]
  python jwt-audit.py verify --token <JWT> --secret <KEY> [--alg HS256]
  python jwt-audit.py --self-test
"""

import argparse
import base64
import hashlib
import hmac
import json
import sys
import time

WEAK_SECRETS = [
    "secret", "secret123", "password", "123456", "changeme", "jwt", "jwtsecret",
    "supersecret", "mysecret", "test", "dev", "development", "admin", "key",
    "your-256-bit-secret", "s3cr3t", "secretkey", "token", "auth", "demo",
]
HS_ALGS = {"HS256": hashlib.sha256, "HS384": hashlib.sha384, "HS512": hashlib.sha512}
KID_SUSPICIOUS = set("/\\..'\"%;-() \t\n\r") | set("$`|&<>")


def b64url_decode(part):
    pad = "=" * (-len(part) % 4)
    return base64.urlsafe_b64decode(part + pad)


def b64url_encode(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def parse_json(part, name):
    try:
        value = json.loads(b64url_decode(part).decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("%s 不是 JSON 对象" % name)
        return value
    except Exception as exc:  # noqa: BLE001 - 报告原始原因，不吞掉
        raise SystemExit("无法解析 %s：%s" % (name, exc))


def b64url_json(obj):
    return b64url_encode(json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def audit(token, now, wordlist):
    findings = []
    warnings = []

    segments = token.strip().split(".")
    if len(segments) == 5:
        return {
            "kind": "JWE",
            "findings": [{
                "id": "JWT-12",
                "level": "info",
                "message": "检测到 5 段 JWE：本工具不解密，需用对应解密流程单独评估",
            }],
            "warnings": ["JWE 的加密强度与密钥管理需源码/配置审计，不能由结构判断"],
        }
    if len(segments) != 3:
        return {
            "kind": "UNKNOWN",
            "findings": [{
                "id": "JWT-00",
                "level": "high",
                "message": "不是标准 3 段 JWS 或 5 段 JWE（段数=%d）" % len(segments),
            }],
            "warnings": [],
        }

    header = parse_json(segments[0], "header")
    payload = parse_json(segments[1], "payload")
    signature = segments[2]
    alg = header.get("alg")

    if alg == "none" or alg is None:
        findings.append({
            "id": "JWT-01", "level": "critical",
            "message": "alg 为 none/缺失：若服务端接受，等于无需签名即可伪造任意身份（R-12 必测）",
        })
    elif alg not in HS_ALGS and alg not in ("RS256", "RS384", "RS512", "ES256", "ES384", "ES512", "PS256", "PS384", "PS512", "EdDSA"):
        findings.append({
            "id": "JWT-02", "level": "medium",
            "message": "非标准 alg=%r：确认服务端是否有算法白名单，拒绝未知算法" % (alg,),
        })

    if alg in ("RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512", "EdDSA") and header.get("typ") not in ("JWT", "at+jwt"):
        warnings.append("非对称算法但 typ=%r：确认服务端是否与 HS* 严格隔离，防算法混淆" % (header.get("typ"),))

    if "exp" not in payload:
        findings.append({
            "id": "JWT-03", "level": "high",
            "message": "载荷无 exp：令牌永不过期，泄漏后长期可用（除服务端另有会话表控制）",
        })
    else:
        exp = payload.get("exp")
        if not isinstance(exp, (int, float)):
            findings.append({"id": "JWT-03b", "level": "medium", "message": "exp 不是数字：%r" % (exp,)})
        elif exp < now:
            findings.append({
                "id": "JWT-04", "level": "medium",
                "message": "令牌已过期（exp=%s，now=%s）：若服务端仍返回 200，即为过期校验缺失" % (int(exp), int(now)),
            })
        elif exp - now > 86400 * 30:
            findings.append({
                "id": "JWT-04b", "level": "low",
                "message": "有效期超过 30 天（%.0f 天）：确认是否与声明的会话策略一致" % ((exp - now) / 86400.0),
            })

    if "nbf" not in payload:
        warnings.append("载荷无 nbf：无法从结构判断是否做「未生效」校验")
    if "iat" not in payload:
        warnings.append("载荷无 iat：无法判断令牌签发时间，弱化重放/轮换分析")
    if "aud" not in payload:
        findings.append({
            "id": "JWT-06", "level": "medium",
            "message": "载荷无 aud：多服务/多受众场景下，令牌可能被拿去别的服务重放",
        })
    if "iss" not in payload:
        findings.append({
            "id": "JWT-07", "level": "medium",
            "message": "载荷无 iss：无法确认签发者，跨环境/跨租户令牌混用风险",
        })
    if header.get("typ") not in ("JWT", "at+jwt", "refresh+jwt"):
        warnings.append("typ=%r：确认服务端是否校验令牌类型，防 access/refresh 混用" % (header.get("typ"),))

    for key in ("jku", "x5u", "jwk", "x5c"):
        if key in header:
            findings.append({
                "id": "JWT-09", "level": "high",
                "message": "头部含 %s：服务端若据此拉取/内联公钥，存在密钥注入与 SSRF 面（RFC 8725）" % key,
            })

    kid = header.get("kid")
    if isinstance(kid, str) and (KID_SUSPICIOUS & set(kid) or ".." in kid):
        findings.append({
            "id": "JWT-10", "level": "high",
            "message": "kid 含路径/SQL/命令可疑字符：%r（确认是否拼接进文件路径或查询）" % kid,
        })

    if alg in HS_ALGS:
        raw = (segments[0] + "." + segments[1]).encode("ascii")
        hit = None
        for candidate in wordlist:
            digest = hmac.new(candidate.encode("utf-8"), raw, HS_ALGS[alg]).digest()
            if hmac.compare_digest(b64url_encode(digest), signature):
                hit = candidate
                break
        if hit is not None:
            findings.append({
                "id": "JWT-11", "level": "critical",
                "message": "HMAC 密钥命中弱密钥字典（%s）：可离线伪造任意令牌" % ("***" if len(hit) > 6 else hit),
            })
        else:
            warnings.append("未命中内置弱密钥字典：**不证明**密钥强，需源码/配置审计密钥熵")

    if signature == "":
        findings.append({"id": "JWT-08", "level": "critical", "message": "签名为空：确认服务端是否接受空签名"})

    return {
        "kind": "JWS",
        "alg": alg,
        "header": header,
        "payload": payload,
        "findings": findings,
        "warnings": warnings,
    }


def render_markdown(result, token_len):
    lines = ["# JWT 结构审计（jwt-audit.py）", ""]
    lines.append("- 令牌长度：%d 段数：%s" % (token_len, "3(JWS)" if result["kind"] == "JWS" else result["kind"]))
    if result.get("alg") is not None:
        lines.append("- alg：`%s`" % result.get("alg"))
    lines += ["", "## 发现", "", "| 编号 | 级别 | 说明 |", "|---|---|---|"]
    for item in result["findings"] or []:
        lines.append("| %s | %s | %s |" % (item["id"], item["level"], item["message"].replace("|", "\\|")))
    if not result["findings"]:
        lines.append("| — | — | 未发现结构性可疑项 |")
    lines += ["", "## 待确认（结构无法证明）", ""]
    for warning in result["warnings"]:
        lines.append("- " + warning.replace("**", ""))
    if not result["warnings"]:
        lines.append("- 无")
    lines += ["", "## 边界", "",
              "- decode 只解释结构，不证明服务端校验正确；结论须由实际请求的响应码/响应体证明（R-12）。",
              "- 不联网、不代填、不冒充；JWE 不解密；签名验证需显式 `verify --secret`。"]
    return "\n".join(lines)


def cmd_decode(args):
    token = args.token or sys.stdin.read().strip()
    wordlist = WEAK_SECRETS
    if args.wordlist:
        with open(args.wordlist, "r", encoding="utf-8") as handle:
            wordlist = [line.rstrip("\n") for line in handle if line.strip()]
    result = audit(token, args.now, wordlist)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(result, len(token)))
    levels = {item["level"] for item in result["findings"]}
    return 2 if levels & {"critical", "high"} else 0


def cmd_verify(args):
    segments = args.token.strip().split(".")
    if len(segments) != 3:
        print("FAIL: 不是 3 段 JWS", file=sys.stderr)
        return 1
    header = parse_json(segments[0], "header")
    alg = args.alg or header.get("alg")
    if alg not in HS_ALGS:
        print("FAIL: verify 只支持 HS256/HS384/HS512，收到 %r" % (alg,), file=sys.stderr)
        return 1
    raw = (segments[0] + "." + segments[1]).encode("ascii")
    expected = b64url_encode(hmac.new(args.secret.encode("utf-8"), raw, HS_ALGS[alg]).digest())
    if hmac.compare_digest(expected, segments[2]):
        print("OK: %s 签名匹配（仅证明密钥正确，不证明令牌未过期/未重放/权限正确）" % alg)
        return 0
    print("MISMATCH: %s 签名不匹配" % alg)
    return 1


def build_token(header, payload, secret=None):
    h = b64url_json(header)
    p = b64url_json(payload)
    if secret is None:
        return h + "." + p + "."
    digest = hmac.new(secret.encode("utf-8"), (h + "." + p).encode("ascii"), hashlib.sha256).digest()
    return h + "." + p + "." + b64url_encode(digest)


def selftest():
    failures = []
    now = 1_700_000_000

    def expect(name, condition):
        if not condition:
            failures.append(name)

    none_token = build_token({"alg": "none"}, {"sub": "1", "role": "admin", "exp": now + 600})
    none_result = audit(none_token, now, WEAK_SECRETS)
    expect("alg=none 被检出", any(i["id"] == "JWT-01" for i in none_result["findings"]))

    expired = build_token({"alg": "HS256", "typ": "JWT"}, {"sub": "1", "aud": "a", "iss": "b", "iat": now - 7200, "exp": now - 3600}, "secret123")
    expired_result = audit(expired, now, WEAK_SECRETS)
    expect("过期被检出", any(i["id"] == "JWT-04" for i in expired_result["findings"]))
    expect("弱密钥被检出", any(i["id"] == "JWT-11" for i in expired_result["findings"]))

    missing = build_token({"alg": "HS256", "typ": "JWT"}, {"sub": "1"})
    missing_result = audit(missing, now, WEAK_SECRETS)
    ids = {i["id"] for i in missing_result["findings"]}
    expect("缺 exp/aud/iss 被检出", {"JWT-03", "JWT-06", "JWT-07"} <= ids)

    injected = build_token({"alg": "HS256", "typ": "JWT", "jku": "http://evil.example/jwks.json", "kid": "../../etc/passwd"}, {"sub": "1", "exp": now + 60})
    injected_result = audit(injected, now, WEAK_SECRETS)
    ids = {i["id"] for i in injected_result["findings"]}
    expect("jku/kid 注入面被检出", {"JWT-09", "JWT-10"} <= ids)

    good = build_token({"alg": "HS256", "typ": "JWT"}, {"sub": "1", "aud": "a", "iss": "b", "iat": now, "exp": now + 300}, "a-strong-secret-9f2c")
    good_result = audit(good, now, WEAK_SECRETS)
    expect("强密钥不误报", not any(i["id"] == "JWT-11" for i in good_result["findings"]))

    ok_header, ok_payload, ok_sig = good.split(".")
    raw = (ok_header + "." + ok_payload).encode("ascii")
    expected = b64url_encode(hmac.new(b"a-strong-secret-9f2c", raw, hashlib.sha256).digest())
    expect("verify 对得上", hmac.compare_digest(expected, ok_sig))
    wrong = b64url_encode(hmac.new(b"wrong", raw, hashlib.sha256).digest())
    expect("verify 对不上", not hmac.compare_digest(expected, wrong))

    if failures:
        print("SELFTEST FAIL: " + ", ".join(failures))
        return 1
    print("SELFTEST GREEN: 8 项断言全过（alg=none/过期/缺 claim/键注入/弱密钥/不误报/签名对/签名错）")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="离线 JWT 结构审计（不联网、不代填、不冒充）")
    sub = parser.add_subparsers(dest="command")

    decode = sub.add_parser("decode", help="解释 JWT 结构并列出可疑项")
    decode.add_argument("--token", help="JWT 字符串；缺省从 stdin 读")
    decode.add_argument("--now", type=int, default=int(time.time()), help="判定过期用的 epoch 秒（默认当前时间）")
    decode.add_argument("--wordlist", help="弱密钥字典文件（每行一个），缺省用内置小字典")
    decode.add_argument("--format", choices=["markdown", "json"], default="markdown")
    decode.set_defaults(func=cmd_decode)

    verify = sub.add_parser("verify", help="用 HMAC 密钥验证签名")
    verify.add_argument("--token", required=True)
    verify.add_argument("--secret", required=True)
    verify.add_argument("--alg", choices=sorted(HS_ALGS))
    verify.set_defaults(func=cmd_verify)

    parser.add_argument("--self-test", action="store_true", help="运行可证伪自检")
    args = parser.parse_args(argv)

    if args.self_test:
        return selftest()
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
