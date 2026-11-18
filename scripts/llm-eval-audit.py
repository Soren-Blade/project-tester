#!/usr/bin/env python3
"""llm-eval-audit.py — AI 系统评测可信性审计（R-24）

用途:
  给 LLM / RAG / Agent / 分类抽取等 AI 系统做「评测结果可不可信」的离线体检：
  静态扫描评测代码与配置里的十类反模式，并统计逐 case 采样、Wilson 置信区间、
  McNemar 配对检验、失败分母、成本延迟与 judge 一致性（Cohen's kappa）。

用法:
  python scripts/llm-eval-audit.py scan [ROOT] [--include-docs] [--format markdown|json] [--fail-on-gap]
  python scripts/llm-eval-audit.py stats --runs FILE [--baseline FILE] [--judge FILE]
        [--min-pass 0.80] [--min-kappa 0.60] [--format markdown|json] [--fail-on-gap]
  python scripts/llm-eval-audit.py cases [--format markdown|json]
  python scripts/llm-eval-audit.py --self-test

静态规则（scan，逐行启发式，与 references/llm-eval-testing.md §9 同号）:
  LE-01 HIGH   单次采样（runs/samples=1、range(1)）就判定通过或失败
  LE-02 HIGH   temperature/top_p 未固定，或写入高方差温度（>=0.6）仍报单点结论
  LE-03 HIGH   模型写家族别名（gpt-4 / claude-3 / gemini-pro）而非带日期 snapshot
  LE-04 HIGH   judge 与 generator 使用同一模型（自偏好偏差，评分不可信）
  LE-05 HIGH   只报绝对分/通过率，全文件无基线、对照、差值或显著性
  LE-06 HIGH   把 error/timeout 从分母里排除（失败被悄悄消失）
  LE-07 MEDIUM 评测集来自公开基准/训练数据，未见污染、重叠或去泄漏检查
  LE-08 MEDIUM 评测集文件未版本化（无 version/hash/采集时间，无法复现）
  LE-09 MEDIUM 阈值只写小数，无样本量、CI、基线或来源说明（疑似单次观察）
  LE-10 MEDIUM 只测 happy path，无错误、拒答、超时、越权或对抗用例

统计口径:
  - 分母 = runs.jsonl 全部采样行，error 非空一律计为失败（不剔除）。
  - pass rate 95% 区间用 Wilson score（z=1.96）；p50/p95 延迟用 nearest-rank。
  - 基线按 case 聚合「任一 run 通过 = 该 case 通过（pass@k）」；McNemar 双尾精确二项。
  - Cohen's kappa：po 一致率，pe 按边际分布相乘，kappa=(po-pe)/(1-pe)。

退出码:
  0 无门槛失败；1 --fail-on-gap 命中；2 参数缺失或输入不可读/JSON 解析失败。

诚实边界:
  - **不联网、不代填结论、不证明模型质量**：只读本地 JSONL/文本，不发模型请求。
  - 不代填：runs/judge 必须来自真实执行或人工标注；脚本只做算术，不生成样本、不补 case、不猜标签。
  - 不证明：scan 命中是「需人工确认的线索」，不是缺陷定论；指标只反映所给文件，不代表线上分布。
  - 不替代在线实验：离线评测不能替代灰度放量与真实流量对照。
  - 默认不扫 `.md`：手册/文档常在正文里引用反模式原文，正则会命中，属噪声；
    需要看文档时显式加 `--include-docs`，并逐条按「引用 vs 实践」裁决。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__",
             ".workbuddy-ai", ".next", "target", "coverage", ".test-memory"}
# 本手册/模板自身在讲反模式，跳过以免自伤（同 search-audit.py 跳过自身）。
SKIP_FILES = {"llm-eval-audit.py", "llm-eval-testing.md", "llm-eval-matrix-template.md"}
EVAL_SUFFIXES = (".py", ".js", ".ts", ".tsx", ".ipynb", ".yaml", ".yml", ".json", ".jsonl")
DOC_SUFFIXES = (".md",)
SEV_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
ALIAS_RE = re.compile(r"(gpt-4|gpt-4o|gpt-4-turbo|gpt-3\.5|gpt-35|claude-3|claude-sonnet|"
                      r"claude-opus|gemini-1\.5|gemini-pro|qwen|llama-3|mistral|deepseek-chat)")
DATE_RE = re.compile(r"(?:19|20)\d{2}")
CONTAM_RE = re.compile(r"contaminat|decontamin|overlap|leak|dedup|held-?out|污染|重叠|泄漏|去重")
VERSION_RE = re.compile(r"version|hash|sha256|snapshot|collected_at|采集|\"v\d")
BASELINE_RE = re.compile(r"baseline|control|previous|prev_|delta|relative|p_value|wilson|"
                         r"confidence|对照|基线|提升|下降|显著性")
NEGATIVE_RE = re.compile(r"error|timeout|refus|invalid|edge|adversarial|injection|negative|"
                         r"越权|拒答|超时|失败")
METRIC_RE = re.compile(r"pass[_ ]rate|accuracy|\bf1\b|win[_ ]rate|exact[_ ]match|\bscore\b")


def iter_files(root: str, include_docs: bool = False) -> Iterable[str]:
    suffixes = EVAL_SUFFIXES + (DOC_SUFFIXES if include_docs else ())
    if os.path.isfile(root):
        if root.lower().endswith(suffixes) and os.path.basename(root) not in SKIP_FILES:
            yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name not in SKIP_FILES and name.lower().endswith(suffixes):
                yield os.path.join(dirpath, name)


def scan(root: str, include_docs: bool = False) -> List[Dict[str, Any]]:
    """返回 [{id,path,line,snippet,severity,message}]；纯启发式，需人工确认。"""
    findings: List[Dict[str, Any]] = []
    base_dir = root if os.path.isdir(root) else os.path.dirname(root) or "."
    for path in iter_files(root, include_docs):
        try:
            lines = open(path, "r", encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        rel = os.path.relpath(path, base_dir)
        text = "\n".join(lines)
        low_all = text.lower()
        has_eval = bool(re.search(r"\beval|judge|pass_rate|rubric|评测|判定", low_all))
        has_call = bool(re.search(r"\.create\(|chat\.completions|call_model|generate\(|"
                                  r"completion\(|invoke_model", low_all))
        judge_models: List[Tuple[int, str]] = []; gen_models: List[Tuple[int, str]] = []
        emitted: set = set()

        def add(rid: str, sev: str, idx: int, message: str) -> None:
            findings.append({"id": rid, "path": rel, "line": idx, "severity": sev,
                             "snippet": (lines[idx - 1].strip()[:160] if 0 < idx <= len(lines) else ""),
                             "message": message})

        if (re.match(r"(?:eval|golden|test)[_-]?set.*\.(?:json|jsonl)$", os.path.basename(path).lower())
                and not VERSION_RE.search(low_all)):
            add("LE-08", "MEDIUM", 1, "评测集文件未版本化（无 version/hash/采集时间），跨版本指标无法复现")

        for idx, line in enumerate(lines, 1):
            low = line.lower()
            if (re.search(r"(?:num_runs|n_runs|n_samples|samples|runs|repeats?)\s*[:=]\s*1\b", low)
                    or (re.search(r"range\(\s*1\s*\)", low) and has_eval)
                    or re.search(r"--runs\s+1\b", low)):
                add("LE-01", "HIGH", idx, "只跑 1 次就判定：非确定系统需 n>=3（建议 5）次采样并报告分布")
            if re.search(r"temperature\s*[:=]\s*(?:1(?:\.0+)?|0\.[6-9]\d*)\b", low):
                add("LE-02", "HIGH", idx, "采样温度设为高方差值，单点分数不可复现；应固定 temperature/top_p/seed")
            if ("LE-02" not in emitted and has_call and "temperature" not in low_all):
                emitted.add("LE-02"); add("LE-02", "HIGH", idx, "存在模型调用却未见 temperature/top_p 配置，采样参数未固定")
            for match in re.finditer(r"[\"']([^\"']+)[\"']", line):
                value = match.group(1).lower()
                if ALIAS_RE.search(value) and not DATE_RE.search(value) and "snapshot" not in value:
                    add("LE-03", "HIGH", idx, "模型写家族别名（未 pin 带日期 snapshot），换版后分数不可比"); break
            if re.search(r"judge[a-z_]*model\s*[:=]\s*(?:generator|sut|target|eval|sut_)|"
                         r"judge[a-z_]*model\s*[:=]\s*(?:MODEL|SUT_MODEL|EVAL_MODEL|GENERATOR_MODEL)\b",
                         line, re.I):
                add("LE-04", "HIGH", idx, "judge 直接复用 generator 模型，自偏好偏差使评分不可信")
            jm = re.search(r"judge[a-z_]*model\s*[:=]\s*[\"']([^\"']+)[\"']", low)
            gm = re.search(r"(?:generator|sut|target|candidate)[a-z_]*model\s*[:=]\s*[\"']([^\"']+)[\"']", low)
            if jm: judge_models.append((idx, jm.group(1)))
            if gm: gen_models.append((idx, gm.group(1)))
            if ("LE-05" not in emitted and has_eval and METRIC_RE.search(low)
                    and not BASELINE_RE.search(low_all)):
                emitted.add("LE-05")
                add("LE-05", "HIGH", idx, "只报绝对分/通过率且未见基线、对照或差值，无法判断好坏与回归")
            if (re.search(r"(?:passed|pass_count|passes|successes|correct)\s*/\s*\(?[^)\n]*-\s*"
                          r"(?:errors?|failed|failures|timeouts?)|(?:total|denominator|n_total)"
                          r"\s*=\s*[^;\n]*-[^;\n]*(?:errors?|timeouts?|failed)", low)
                    or re.search(r"if\s+[^\n]*(?:error|timeout)[^\n]*:\s*continue", low)
                    or (has_eval and re.search(r"except[^:\n]*:\s*pass\b", low))):
                add("LE-06", "HIGH", idx, "error/timeout 被排除或跳过，分母只含成功调用；失败必须计入分母")
            if (re.search(r"eval_set|golden|benchmark|test_set|评测集", low)
                    and re.search(r"open\(|read_text|json\.load|jsonl|load_", low)
                    and not CONTAM_RE.search(low_all)):
                add("LE-07", "MEDIUM", idx, "评测集来自公开基准/历史数据却未见污染、重叠或去泄漏检查")
            if (re.search(r"(?:threshold|min_pass|min_score|cutoff)[a-z_]*[\"']?\s*[:=]\s*0?\.\d+", low)
                    and not re.search(r"confidence|\bci\b|baseline|sample|n_runs|wilson|significan|"
                                      r"kappa|p_value", low_all)):
                add("LE-09", "MEDIUM", idx, "阈值只写数值，无样本量/CI/基线来源，疑似来自单次观察")
            if (has_eval and re.search(r"cases?|eval_set", low_all)
                    and re.search(r"for\s+[^\n]*\bin\b[^\n]*(?:case|cases|eval_set)", low)
                    and not NEGATIVE_RE.search(low_all)):
                add("LE-10", "MEDIUM", idx, "只遍历正常样本并断言通过，未见错误/拒答/超时/越权/对抗用例")

        judge_by_value = {value: idx for idx, value in judge_models}
        for idx, value in gen_models:
            if value in judge_by_value:
                add("LE-04", "HIGH", judge_by_value[value],
                    "judge 与 generator 使用同一模型 %r，评分存在自偏好偏差" % value)
                break
    findings.sort(key=lambda f: (SEV_ORDER.get(f["severity"], 9), f["id"], f["path"], f["line"]))
    return findings


def wilson_interval(passed: int, total: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score 95% 区间；total=0 返回 (0,0)。"""
    if total <= 0:
        return (0.0, 0.0)
    p = passed / total
    denom = 1.0 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def percentile(values: List[float], q: float) -> Optional[float]:
    """nearest-rank：排序后取第 ceil(q/100*n) 个（1-based）。"""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, min(len(ordered), int(math.ceil(q / 100.0 * len(ordered)))))
    return ordered[rank - 1]


def mcnemar_exact(b: int, c: int) -> float:
    """McNemar 双尾精确二项检验；b/c 为两组不一致对。"""
    total = b + c
    if total == 0:
        return 1.0
    tail = sum(math.comb(total, i) for i in range(min(b, c) + 1)) / (2 ** total)
    return min(1.0, 2.0 * tail)


def cohens_kappa(pairs: List[Tuple[str, str]]) -> Dict[str, Any]:
    """多分类 Cohen's kappa；返回 n/po/pe/kappa 与混淆矩阵。"""
    counted = Counter(pairs)
    n = len(pairs)
    if n == 0:
        return {"n": 0, "po": 0.0, "pe": 0.0, "kappa": 0.0, "matrix": []}
    po = sum(c for (judge, human), c in counted.items() if judge == human) / n
    jm, hm = Counter(j for j, _ in pairs), Counter(h for _, h in pairs)
    pe = sum(jm[k] / n * hm.get(k, 0) / n for k in jm)
    kappa = (1.0 if po >= 1.0 else 0.0) if pe >= 1.0 else (po - pe) / (1.0 - pe)
    matrix = [{"judge": j, "human": h, "count": c} for (j, h), c in sorted(counted.items())]
    return {"n": n, "po": po, "pe": pe, "kappa": kappa, "matrix": matrix}


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return isinstance(value, str) and value.strip().lower() in ("1", "true", "yes", "y", "pass", "passed")


def _as_number(value: Any, default: float, cast) -> Any:
    try:
        return cast(value)
    except (TypeError, ValueError):
        return default


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("%s 第 %d 行不是合法 JSON：%s" % (path, lineno, exc))
            if not isinstance(obj, dict):
                raise ValueError("%s 第 %d 行不是 JSON 对象" % (path, lineno))
            rows.append(obj)
    return rows


def normalize_runs(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for lineno, obj in enumerate(rows, 1):
        cid = obj.get("case_id")
        if not isinstance(cid, str) or not cid.strip():
            raise ValueError("runs 第 %d 行缺少 case_id" % lineno)
        error = obj.get("error")
        error = None if error in (None, "") else str(error)
        out.append({"case_id": cid.strip(), "run": _as_number(obj.get("run"), 0, int),
                    "passed": _as_bool(obj.get("passed")), "model": str(obj.get("model") or ""),
                    "temperature": obj.get("temperature"),
                    "latency_ms": _as_number(obj.get("latency_ms"), 0.0, float),
                    "tokens": _as_number(obj.get("tokens"), 0, int),
                    "cost": _as_number(obj.get("cost"), 0.0, float), "error": error,
                    "timeout": bool(error and re.search(r"timeout|timed out|超时", error, re.I))})
    return out


def _case_pass_map(rows: List[Dict[str, Any]]) -> Dict[str, bool]:
    """任一 run 通过且无 error => 该 case 通过（pass@k 口径）。"""
    result: Dict[str, bool] = {}
    for row in rows:
        result[row["case_id"]] = result.get(row["case_id"], False) or (row["passed"] and not row["error"])
    return result


def compute_stats(rows, baseline_rows=None, judge_rows=None, min_pass=0.80, min_kappa=0.60,
                  alpha=0.05) -> Dict[str, Any]:
    total = len(rows)
    passed = sum(1 for r in rows if r["passed"] and not r["error"])
    pass_rate = (passed / total) if total else 0.0
    low, high = wilson_interval(passed, total)
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows: grouped.setdefault(row["case_id"], []).append(row)
    case_rows = [{"case_id": cid, "n": len(g), "passed": (p := sum(1 for r in g if r["passed"] and not r["error"])),
                  "pass_rate": p / len(g), "errors": sum(1 for r in g if r["error"])}
                 for cid, g in sorted(grouped.items())]
    n_lt_three = [{"case_id": r["case_id"], "n": r["n"]} for r in case_rows if r["n"] < 3]
    errors = [r for r in rows if r["error"]]
    timeouts = [r for r in errors if r.get("timeout")]
    latencies = [r["latency_ms"] for r in rows if r["latency_ms"] >= 0]
    result: Dict[str, Any] = {"rule": "R-24", "summary": {
        "total": total, "passed": passed, "pass_rate": pass_rate,
        "wilson_low": low, "wilson_high": high, "cases": len(case_rows),
        "errors": len(errors), "error_rate": len(errors) / total if total else 0.0,
        "timeouts": len(timeouts), "timeout_rate": len(timeouts) / total if total else 0.0,
        "p50_latency_ms": percentile(latencies, 50), "p95_latency_ms": percentile(latencies, 95),
        "total_tokens": sum(r["tokens"] for r in rows), "total_cost": sum(r["cost"] for r in rows),
        "models": sorted({r["model"] for r in rows if r["model"]}),
        "temperatures": sorted({str(r["temperature"]) for r in rows if r["temperature"] is not None}),
        "min_pass": min_pass, "min_kappa": min_kappa},
        "cases": case_rows, "n_lt_3": n_lt_three, "fail_reasons": [], "baseline": None, "judge": None}
    if baseline_rows:
        cmap, bmap = _case_pass_map(rows), _case_pass_map(baseline_rows)
        common = sorted(set(cmap) & set(bmap))
        b = sum(1 for cid in common if cmap[cid] and not bmap[cid])
        c = sum(1 for cid in common if bmap[cid] and not cmap[cid])
        p_value = mcnemar_exact(b, c)
        result["baseline"] = {"paired_cases": len(common), "only_current_pass": b,
            "only_baseline_pass": c, "p_value": p_value, "significant": p_value < alpha,
            "direction": "improved" if b > c else ("regressed" if b < c else "tied"),
            "alpha": alpha, "case_aggregation": "任一 run 通过 = 该 case 通过（pass@k）"}
    if judge_rows:
        pairs = [(str(r["judge_label"]), str(r["human_label"])) for r in judge_rows
                 if "judge_label" in r and "human_label" in r]
        judge = cohens_kappa(pairs); judge["min_kappa"] = min_kappa
        judge["available"] = judge["n"] > 0 and judge["kappa"] >= min_kappa
        result["judge"] = judge
    reasons = result["fail_reasons"]
    if total == 0: reasons.append("runs 为空，无样本可统计")
    elif pass_rate < min_pass:
        reasons.append("总体 pass rate %.1f%% < 门槛 %.1f%%（%d/%d）" % (
            pass_rate * 100, min_pass * 100, passed, total))
    if n_lt_three:
        reasons.append("存在 n<3 的 case（LE-01）：" + ", ".join(
            "%s(n=%d)" % (r["case_id"], r["n"]) for r in n_lt_three))
    judge = result["judge"]
    if judge is not None and judge["n"] > 0 and judge["kappa"] < min_kappa:
        reasons.append("judge-human kappa %.3f < 门槛 %.2f，判定器不可用" % (judge["kappa"], min_kappa))
    baseline = result["baseline"]
    if baseline and baseline["significant"] and baseline["direction"] == "regressed":
        reasons.append("McNemar 显示显著回归（p=%.4f，b=%d c=%d）" % (
            baseline["p_value"], baseline["only_current_pass"], baseline["only_baseline_pass"]))
    result["ok"] = not reasons
    return result


def fmt_scan(items: List[Dict[str, Any]]) -> str:
    lines = ["### R-24 静态线索（启发式，需人工确认）", "",
             "| 编号 | 级别 | 位置 | 说明 |", "|---|---|---|---|"]
    for item in items:
        lines.append("| %s | %s | %s:%d | %s |" % (
            item["id"], item["severity"], item["path"], item["line"],
            item["message"].replace("|", "\\|")))
    if not items: lines.append("| — | — | — | 未命中已知反模式（不等于评测可信） |")
    return "\n".join(lines)


def _pct(value: Optional[float]) -> str:
    return "—" if value is None else "%.1f%%" % (value * 100)


def _ms(value: Optional[float]) -> str:
    return "—" if value is None else "%.1f" % value


def fmt_stats(result: Dict[str, Any]) -> str:
    s = result["summary"]
    lines = ["### R-24 评测统计汇总", "", "| 指标 | 值 |", "|---|---|",
             "| 总采样数（分母，含 error/timeout） | %d |" % s["total"],
             "| 通过数 | %d |" % s["passed"], "| 总体 pass rate | %s |" % _pct(s["pass_rate"]),
             "| Wilson 95%% CI | [%s, %s] |" % (_pct(s["wilson_low"]), _pct(s["wilson_high"])),
             "| case 数 | %d |" % s["cases"],
             "| error 数 / 占比 | %d / %s |" % (s["errors"], _pct(s["error_rate"])),
             "| timeout 数 / 占比 | %d / %s |" % (s["timeouts"], _pct(s["timeout_rate"])),
             "| p50 / p95 延迟 | %s ms / %s ms |" % (_ms(s["p50_latency_ms"]), _ms(s["p95_latency_ms"])),
             "| tokens / 成本 | %d / $%.4f |" % (s["total_tokens"], s["total_cost"]),
             "| 模型 / temperature | %s / %s |" % (", ".join(s["models"]) or "—",
                                                  ", ".join(s["temperatures"]) or "—"),
             "", "### 逐 case", "", "| case | n | pass | pass rate | error |", "|---|---|---|---|---|"]
    for row in result["cases"]:
        lines.append("| %s | %d | %d | %s | %d |" % (
            row["case_id"], row["n"], row["passed"], _pct(row["pass_rate"]), row["errors"]))
    if result["n_lt_3"]:
        lines += ["", "### n<3（LE-01）", ""]
        lines.append("- " + ", ".join("%s(n=%d)" % (row["case_id"], row["n"]) for row in result["n_lt_3"]))
    baseline = result["baseline"]
    if baseline:
        lines += ["", "### 基线对比（McNemar 精确检验）", "", "| 项 | 值 |", "|---|---|",
                  "| 配对 case | %d |" % baseline["paired_cases"],
                  "| 仅当前通过 / 仅基线通过（b / c） | %d / %d |" % (
                      baseline["only_current_pass"], baseline["only_baseline_pass"]),
                  "| 双尾 p | %.6f |" % baseline["p_value"],
                  "| 结论 | %s（alpha=%.2f，聚合=%s） |" % (
                      "显著" if baseline["significant"] else "不显著", baseline["alpha"],
                      baseline["case_aggregation"]),
                  "| 方向 | %s |" % {"improved": "当前优于基线", "regressed": "当前劣于基线",
                                     "tied": "无方向差异"}[baseline["direction"]]]
    judge = result["judge"]
    if judge:
        lines += ["", "### 判定器一致性（Cohen's kappa）", "", "| 项 | 值 |", "|---|---|",
                  "| 标注样本 | %d |" % judge["n"], "| 一致率 po / 期望 pe | %.4f / %.4f |" % (judge["po"], judge["pe"]),
                  "| kappa | %.4f |" % judge["kappa"],
                  "| 门槛 / 结论 | %.2f / %s |" % (judge["min_kappa"],
                                                  "可用" if judge["available"] else "不可用 / 需重标")]
        lines += ["", "| judge\\human | count |", "|---|---|"]
        lines += ["| %s\\%s | %d |" % (cell["judge"], cell["human"], cell["count"])
                  for cell in judge["matrix"]]
    lines += ["", "### 门槛判定", ""]
    if result["ok"]:
        lines.append("- PASS：未触发 pass rate / 采样 / kappa / 回归门槛")
    else:
        lines += ["- FAIL：" + reason for reason in result["fail_reasons"]]
    return "\n".join(lines)


def cases_data() -> Dict[str, Any]:
    return {"rule": "R-24", "matrix": [
        {"dimension": "任务", "must": "任务定义、输入输出契约、允许失败的业务后果", "fill": ""},
        {"dimension": "评测集", "must": "规模、分层、来源、版本 hash、污染检查结论", "fill": ""},
        {"dimension": "判定器", "must": "规则/人工双标/LLM judge、kappa 或一致率、rubric 版本", "fill": ""},
        {"dimension": "采样", "must": "n（>=3，建议 5）、temperature/top_p/seed、pass@1 或 pass@k", "fill": ""},
        {"dimension": "基线", "must": "上版/无增强/默认模型、差值、CI、McNemar p", "fill": ""},
        {"dimension": "成本", "must": "p50/p95 延迟、token、$ 成本、预算与超支判定", "fill": ""},
        {"dimension": "安全", "must": "注入、越权工具、数据外泄、RAG 越权、XSS、PII", "fill": ""},
    ], "checks": [
        "评测集每类 >=30、合计 >=200；n<30 的类只报点估计与样本量", "每个 case 采样 n>=3（建议 5），temperature/top_p/seed 固定并写明",
        "判定器与 generator 不同模型不同 prompt；kappa>=0.60 或一致率>=80%", "分母包含 error/timeout/拒答；不得只统计成功调用",
        "报告 pass rate 必须带 Wilson 95% CI 与样本量", "有基线对照；显著性与配对检验（McNemar / 配对 bootstrap）写清",
        "模型 pin 到 snapshot；评测集文件带 version + hash + 采集时间", "安全用例覆盖 prompt injection、越权工具、RAG 越权、XSS 与 PII 回显",
    ]}

def fmt_cases(data: Dict[str, Any]) -> str:
    lines = ["# R-24 评测就绪度矩阵（可填写）", "", "| 维度 | 必填证据 | 本项目 |", "|---|---|---|"]
    lines += ["| %s | %s | %s |" % (row["dimension"], row["must"], row["fill"] or "<!-- 填写 -->")
              for row in data["matrix"]]
    lines += ["", "## 8 条必查", ""]; lines += ["%d. %s" % (i, check) for i, check in enumerate(data["checks"], 1)]
    return "\n".join(lines)


def self_test() -> int:
    """夹具自检：10 条静态规则、n<3 检出、McNemar 手算、kappa 手算、cases 表头。"""
    fixtures = {
        "run_eval.py": 'MODEL = "gpt-4"\nNUM_RUNS = 1\n'
                       'for case in json.load(open("eval_set.jsonl", encoding="utf-8")):\n'
                       '    passed = case["expected"] in call_model(MODEL, case["prompt"])\n'
                       '    print("score", passed)\n',
        "judge.py": 'GENERATOR_MODEL = "gpt-4o"\nJUDGE_MODEL = GENERATOR_MODEL\ntemperature = 1.0\n',
        "config.yaml": "model: gpt-4\ntemperature: 1.0\n",
        "metrics.py": 'def summarize(total, errors):\n'
                      '    print("accuracy", passed / (total - errors))\n',
        "thresholds.json": '{"pass_rate_threshold": 0.87}\n', "eval_set.jsonl": '{"case_id": "c1"}\n' * 3,
        "clean_eval.py": 'MODEL = "gpt-4o-2024-08-06"\nNUM_RUNS = 5\nTEMPERATURE = 0.0\n'
                         'BASELINE_PASS_RATE = 0.72\n',
    }
    bad = {(1, 5): "HTTP 500", (3, 4): "timeout after 30s"}
    run_rows = [{"case_id": "c%02d" % i, "run": r, "passed": (i, r) not in bad, "model": "m-2026-01-01",
                 "temperature": 0, "latency_ms": 800 + i * 10 + r, "tokens": 500 + i, "cost": 0.001 * i,
                 "error": bad.get((i, r))} for i in range(1, 19) for r in range(1, 6)]
    run_rows += [{"case_id": cid, "run": 1, "passed": True, "model": "m-2026-01-01",
                  "temperature": 0, "latency_ms": 1200, "tokens": 400, "cost": 0.002, "error": None}
                 for cid in ("c19", "c20")]
    baseline_rows = [{"case_id": "c%02d" % i, "run": r, "passed": i <= 14, "model": "m-old", "temperature": 0,
                      "latency_ms": 900, "tokens": 500, "cost": 0.001, "error": None if i <= 14 else "wrong answer"}
                     for i in range(1, 21) for r in range(1, 6)]
    judge_rows = ([{"judge_label": 1, "human_label": 1}] * 12 + [{"judge_label": 1, "human_label": 0}] * 3
                  + [{"judge_label": 0, "human_label": 1}] * 3 + [{"judge_label": 0, "human_label": 0}] * 12)
    try:
        with tempfile.TemporaryDirectory(prefix="llmeval-") as tmp:
            for name, content in fixtures.items():
                open(os.path.join(tmp, name), "w", encoding="utf-8").write(content)
            found = scan(tmp); hit = {item["id"] for item in found}
            missing = sorted({"LE-%02d" % i for i in range(1, 11)} - hit)
            assert not missing, "静态夹具未命中：" + ", ".join(missing)
            assert not [f for f in found if f["path"] == "clean_eval.py"], "干净夹具误报"
            result = compute_stats(normalize_runs(run_rows), normalize_runs(baseline_rows),
                                   judge_rows)
            assert abs(result["summary"]["pass_rate"] - 90 / 92) < 1e-9, "pass rate 应为 90/92"
            assert result["summary"]["wilson_low"] < result["summary"]["pass_rate"] < result["summary"]["wilson_high"], "Wilson 区间不合理"
            assert sorted(row["case_id"] for row in result["n_lt_3"]) == ["c19", "c20"], "n<3 应检出 c19/c20"
            base = result["baseline"] or {}
            assert (base.get("only_current_pass"), base.get("only_baseline_pass")) == (6, 0), "McNemar b/c 应为 6/0"
            assert abs(base.get("p_value", -1) - 0.03125) < 1e-9, "McNemar p 应为 0.03125"
            assert base.get("significant") and base.get("direction") == "improved", "McNemar 应判显著提升"
            assert abs((result["judge"] or {}).get("kappa", -1) - 0.60) < 0.02, "kappa 应约 0.60"
            # 文档噪声回归：默认跳过 .md，--include-docs 时才扫
            open(os.path.join(tmp, "notes.md"), "w", encoding="utf-8").write(
                "评测说明：temperature: 1.0\nNUM_RUNS = 1\n")
            assert not [f for f in scan(tmp) if f["path"] == "notes.md"], "默认应跳过 .md"
            assert [f for f in scan(tmp, True) if f["path"] == "notes.md"], "--include-docs 应扫 .md"
        assert all(k in fmt_cases(cases_data()) for k in ("评测就绪度", "判定器", "8 条必查", "Wilson")), "cases 缺关键字"
    except AssertionError as exc:
        print("SELFTEST FAIL: %s" % exc)
        return 1
    print("SELFTEST GREEN: 10 条 LE 规则全部命中、干净夹具零误报、n<3 检出 2 个、"
          "Wilson CI 可算、McNemar p=0.03125、kappa=0.600、cases 表头完整")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="R-24 AI 系统评测可信性审计")
    p.add_argument("command", nargs="?", choices=["scan", "stats", "cases", "self-test"], default="cases")
    p.add_argument("target", nargs="?", default=".")
    for flag in ("--runs", "--baseline", "--judge"):
        p.add_argument(flag, default=None)
    p.add_argument("--min-pass", type=float, default=0.80)
    p.add_argument("--min-kappa", type=float, default=0.60)
    p.add_argument("--format", choices=["markdown", "json"], default="markdown")
    p.add_argument("--fail-on-gap", action="store_true")
    p.add_argument("--include-docs", action="store_true",
                   help="同时扫描 .md（默认跳过，避免文档引用反模式原文被误报）")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test or args.command == "self-test":
        return self_test()

    def dump(data: Any, text: str) -> None:
        print(json.dumps(data, ensure_ascii=False, indent=2) if args.format == "json" else text)

    if args.command == "scan":
        items = scan(args.target, args.include_docs)
        dump({"rule": "R-24", "findings": items}, fmt_scan(items))
        if args.fail_on_gap and any(i["severity"] == "HIGH" for i in items):
            print("[FAIL] 存在 HIGH 级评测反模式", file=sys.stderr)
            return 1
        return 0
    if args.command == "stats":
        if not args.runs:
            print("stats 需要 --runs runs.jsonl", file=sys.stderr)
            return 2
        try:
            rows = normalize_runs(load_jsonl(args.runs))
            baseline = normalize_runs(load_jsonl(args.baseline)) if args.baseline else None
            judge = load_jsonl(args.judge) if args.judge else None
        except (OSError, ValueError) as exc:
            print("读取失败：%s" % exc, file=sys.stderr)
            return 2
        result = compute_stats(rows, baseline, judge, args.min_pass, args.min_kappa)
        dump(result, fmt_stats(result))
        for reason in result["fail_reasons"]:
            print("[FAIL] " + reason, file=sys.stderr)
        return 1 if args.fail_on_gap and not result["ok"] else 0
    data = cases_data()
    dump(data, fmt_cases(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
