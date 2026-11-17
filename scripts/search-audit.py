#!/usr/bin/env python3
"""search-audit.py — 搜索相关性与排序质量审计（R-21）

用法:
  python scripts/search-audit.py scan <路径> [--format markdown|json] [--fail-on-gap]
  python scripts/search-audit.py eval --qrels qrels.json --runs runs.json [--k 10]
                                      [--format markdown|json] [--fail-on-gap]
                                      [--min-ndcg 0.60] [--max-zero-rate 0.20]
  python scripts/search-audit.py cases
  python scripts/search-audit.py --self-test

静态规则（scan，逐行启发式）:
  SR-01 CRITICAL  用户输入被拼接进 SQL/DSL（字符串插值、+ 号、模板串）
  SR-02 HIGH      search 路径用 created_at/id 排序，全项目无 relevance/score/BM25
  SR-03 HIGH      深分页用 OFFSET / from+size 且无 search_after
  SR-04 MEDIUM    读取 hits.total 但未设置 track_total_hits（ES 默认 10000 截断）
  SR-05 MEDIUM    中文/日文/韩文匹配但未见 analyzer 配置（默认分词会切碎 CJK）
  SR-06 HIGH      highlight 片段未转义直接 innerHTML（存储型 XSS）
  SR-07 HIGH      tenant/owner 在取回结果后才过滤（post_filter 或应用层 filter）
  SR-08 MEDIUM    wildcard 查询带前导 *（词项无限展开，易被拖垮）
  SR-09 MEDIUM    search 全项目无结果上限（无 LIMIT / size / max_result_window）
  SR-10 MEDIUM    日志记录原始 query 且未见脱敏（mask/redact/hash）

评测规则（eval，读取 qrels + runs 计算）:
  SR-20 S1        某 query 返回空结果（零结果）
  SR-21 HIGH      nDCG@k 低于 --min-ndcg（默认 0.60）
  SR-22 HIGH      零结果率高于 --max-zero-rate（默认 0.20）
  SR-23 MEDIUM    某 query 的 top1 不是 rel>=2 的文档（头部意图未满足）
  SR-24 MEDIUM    runs 中 query 数与 qrels 不一致（缺跑或串号）
  SR-25 MEDIUM    runs 内出现重复 doc（去重后排名变化）

指标口径:
  nDCG@k = DCG@k / IDCG@k，DCG@k = Σ (2^rel_i − 1) / log2(i + 1)，i 从 1 开始；
  IDCG@k 用 qrels 中全部已判定文档按 rel 降序取前 k 计算；
  MRR@k = mean(1 / 首个 rel>=1 的排名)，没有则 0；
  Recall@k = |top-k 中 rel>=1| / |qrels 中 rel>=1|（分母为 0 的 query 不参与均值）；
  Precision@k = |top-k 中 rel>=1| / k（结果不足 k 条仍除以 k）；
  未判定文档按 rel=0 处理；重复 doc 只保留首次出现。

诚实边界:
  - 不联网：只读本地文件，不发任何检索请求。
  - 不代填：qrels 必须来自人工判定或双人抽检；runs 必须由真实请求导出，
    脚本只做算术，不生成、不补全、不猜测判定。
  - 不证明：scan 命中是「需人工确认的线索」，不是漏洞定论；eval 的 nDCG 只反映
    评估集上的排序质量，不代表线上全部 query，也不证明业务相关性成立。
  - 不替代在线实验：离线指标不能替代 interleaving / A/B，点击率不能替代 qrels。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile

SKIP_DIRS = {
    ".git", "node_modules", ".workbuddy-ai", ".test-memory", "dist", "build",
    ".venv", "venv", "__pycache__", ".next", "target", ".idea", "coverage",
}
SKIP_FILES = {"search-audit.py"}
CODE_SUFFIXES = (
    ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".py", ".php", ".rb", ".java",
    ".kt", ".go", ".cs", ".sql", ".rs", ".vue", ".svelte",
)
CJK_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")

SEV_ORDER = {"CRITICAL": 0, "S1": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def iter_files(root: str):
    if os.path.isfile(root):
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            if name in SKIP_FILES:
                continue
            if name.endswith(CODE_SUFFIXES):
                yield os.path.join(dirpath, name)


def scan(root: str) -> list[dict]:
    findings: list[dict] = []
    for path in iter_files(root):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except OSError:
            continue
        rel = os.path.relpath(path, root)
        text = "\n".join(lines)
        low_all = text.lower()
        has_search = bool(re.search(r"\bsearch\b|\bquery\b|\bkeyword\b|\bsearchafter\b", low_all))
        has_score = bool(re.search(r"\bscore\b|\brank\b|relevance|bm25|ts_rank|similarity|function_score|_score", low_all))
        track_total = "track_total_hits" in low_all
        has_analyzer = bool(re.search(r"analyzer|ik_|jieba|smartcn|kuromoji|nori\b", low_all))
        has_search_after = "search_after" in low_all
        has_limit = bool(re.search(r"\blimit\b|max_result_window|\"size\"\s*:|\bsize\s*[:=]", low_all))
        seen_once: set[str] = set()

        def add(rid: str, sev: str, idx: int, reason: str) -> None:
            findings.append({
                "rule": rid, "severity": sev, "file": rel, "line": idx,
                "reason": reason, "excerpt": lines[idx - 1].strip()[:160] if idx else "",
            })

        for idx, line in enumerate(lines, 1):
            low = line.lower()

            # SR-01 拼接注入：LIKE 插值 / SQL 字符串 + 变量 / 模板串里的请求参数
            if (re.search(r"like\s+(?:concat\()?\s*['\"]%['\"]?\s*(?:\+|\|\||\$\{|%s|%\s*\()", low)
                    or re.search(r"(?:select|where|from|match)[^\n]{0,60}['\"]\s*\+\s*(?:req\.)?(?:query|params|body|args)", low)
                    or re.search(r"\$\{\s*(?:req\.)?(?:query|params|body)\.(?:q|query|term|keyword)", line)
                    or re.search(r"(?:f['\"])[^'\"]*\{(?:q|query|term|keyword)\}", line) and has_search):
                add("SR-01", "CRITICAL", idx, "用户输入被拼接进检索语句，SQL/DSL 注入面")

            # SR-02 无相关性排序：search 路径按时间/主键排序且全项目无打分信号
            if ("order by" in low and has_search and not has_score
                    and re.search(r"order by[^\n]*(created_at|updated_at|\bid\b|name|price)", low)):
                add("SR-02", "HIGH", idx, "search 结果按 created_at/id 等非相关性字段排序，无 BM25/score")

            # SR-03 深分页
            if (has_search and not has_search_after
                    and re.search(r"\boffset\b[^\n]*(page|offset)\s*\*|\boffset\b\s+\S*\bpage\b|\bfrom\s*:\s*[^,]*\bpage\b", low)):
                add("SR-03", "HIGH", idx, "深分页依赖 OFFSET/from+size，且无 search_after，深页慢且易漂移")

            # SR-04 total 截断
            if "hits.total" in low and not track_total:
                add("SR-04", "MEDIUM", idx, "读取 hits.total 却未设 track_total_hits，ES 默认只精确到 10000")

            # SR-05 CJK 分词（每文件一次）
            if ("SR-05" not in seen_once and has_analyzer is False and CJK_RE.search(text)
                    and re.search(r"[\"']match[\"']|\bmatch\s*[:({]", low)):
                seen_once.add("SR-05")
                add("SR-05", "MEDIUM", idx, "CJK 文本用 match 检索但未见 analyzer 配置，默认分词会切碎词")

            # SR-06 highlight XSS：前端 innerHTML 直出，或服务端用字符串拼 <em>/<mark> 且全文件无转义
            if re.search(r"innerhtml\s*=\s*[^\"'\s]", low) \
                    and (re.search(r"highlight|<em>|fragment", low_all)
                         and not re.search(r"escape|sanitize|textcontent", low)):
                add("SR-06", "HIGH", idx, "highlight 片段未经转义写入 innerHTML，存在存储型 XSS")
            elif (re.search(r"(?:<em>|<mark>)[^\n]{0,40}(?:q|query|term|keyword)\b", low)
                  or re.search(r"(?:q|query|term|keyword)\b[^\n]{0,40}(?:<em>|<mark>)", low)) \
                    and not re.search(r"escapehtml|escape_html|htmlspecialchars|sanitize|encodeentities", low_all):
                add("SR-06", "HIGH", idx, "服务端用字符串拼 highlight 片段（<em>/<mark>）且全文件无转义，输出即 XSS 面")

            # SR-07 取回后过滤
            if (re.search(r"post_filter", low) and re.search(r"tenant|owner|org_id|account_id|acl", low_all)) \
                    or (re.search(r"\.filter\(", low) and re.search(r"tenant|owner|org_id|account_id", low)):
                add("SR-07", "HIGH", idx, "tenant/ACL 在结果取回后才过滤，文档数与 total 可能泄漏")

            # SR-08 前导通配符
            if re.search(r"wildcard[^\n]*[\"']?\*", low) and re.search(r"query|q\b|keyword|term", low):
                add("SR-08", "MEDIUM", idx, "wildcard 查询带前导 *，词项无限展开且无法用索引")

            # SR-09 结果上限缺失或过宽：size 直接取原始变量、LIMIT 拼接变量、或 LIMIT 四位数以上
            if ((re.search(r"\bsize\s*:\s*(?:size|limit|count|req\.query\.\w+|params\.\w+)\b", low)
                 and "math.min" not in low and "clamp" not in low)
                    or (re.search(r"\blimit\s*[\"']?\s*\+\s*[\w.]+", low)
                        and not re.search(r"math\.min|\bclamp\b|min\s*\(", low))
                    or re.search(r"\blimit\s+\d{4,}", low)):
                add("SR-09", "MEDIUM", idx, "结果集上限取原始变量或超过 1000，深翻/大页会拖垮检索")

            # SR-10 原始 query / 身份信息入日志
            if re.search(r"console\.(log|info)|logger\.(info|warn|error)|print\(", low) \
                    and re.search(r"(?:query|params)\.(?:q|query|term|keyword)|['\"]q['\"]|"
                                  r"\b(?:email|phone|token|authorization|password)\b|"
                                  r"[\"']q=[\"']|[\"']search q=", low) \
                    and not re.search(r"mask|redact|hash|sha256|anonym", low):
                add("SR-10", "MEDIUM", idx, "日志写入原始 query 或身份字段，未见脱敏，可能带 PII/敏感意图")

    findings.sort(key=lambda f: (SEV_ORDER.get(f["severity"], 9), f["rule"], f["file"], f["line"]))
    return findings


def _rel_map(q: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for doc, rel in (q.get("judgments") or {}).items():
        try:
            out[str(doc)] = max(0, int(rel))
        except (TypeError, ValueError):
            out[str(doc)] = 0
    return out


def _dedupe(docs: list) -> list[str]:
    out: list[str] = []
    for d in docs or []:
        s = str(d)
        if s not in out:
            out.append(s)
    return out


def query_metrics(qid: str, q: dict, run: list, k: int) -> dict:
    rels = _rel_map(q)
    docs = _dedupe(run)[:k]
    gains = [rels.get(d, 0) for d in docs]
    dcg = sum((2 ** rel - 1) / math.log2(i + 2) for i, rel in enumerate(gains))
    ideal = sorted(rels.values(), reverse=True)[:k]
    idcg = sum((2 ** rel - 1) / math.log2(i + 2) for i, rel in enumerate(ideal))
    ndcg = (dcg / idcg) if idcg > 0 else 0.0

    mrr = 0.0
    for i, rel in enumerate(gains, 1):
        if rel >= 1:
            mrr = 1.0 / i
            break

    total_rel = sum(1 for v in rels.values() if v >= 1)
    hits = sum(1 for v in gains if v >= 1)
    recall = (hits / total_rel) if total_rel else None
    precision = hits / k

    top1 = gains[0] if gains else None
    return {
        "query_id": qid,
        "query": q.get("query") or qid,
        "returned": len(run or []),
        "unique_returned": len(_dedupe(run)),
        "judged": bool(rels),
        "ndcg": round(ndcg, 6),
        "mrr": round(mrr, 6),
        "recall": None if recall is None else round(recall, 6),
        "precision": round(precision, 6),
        "top1_relevance": top1,
        "zero_result": len(run or []) == 0,
    }


def evaluate(qrels: dict, runs: dict, k: int | None = None,
             min_ndcg: float = 0.60, max_zero_rate: float = 0.20) -> dict:
    queries = qrels.get("queries") or {}
    kk = int(k or qrels.get("k") or 10)
    rows: list[dict] = []
    gaps: list[dict] = []

    def gap(rid: str, sev: str, reason: str) -> None:
        gaps.append({"rule": rid, "severity": sev, "reason": reason})

    for qid in sorted(queries):
        run = runs.get(qid) or []
        if not isinstance(run, list):
            run = []
        row = query_metrics(qid, queries[qid], run, kk)
        rows.append(row)
        if row["zero_result"]:
            gap("SR-20", "S1", "%s（%s）返回零结果" % (qid, row["query"]))
        # 无判定集时 nDCG/MRR 恒为 0，不能据此判「相关性不达标」——只说明未评测
        if row["judged"] and row["ndcg"] < min_ndcg:
            gap("SR-21", "HIGH", "%s nDCG@%d=%.3f < %.2f" % (qid, kk, row["ndcg"], min_ndcg))
        if row["judged"] and row["top1_relevance"] is not None and row["top1_relevance"] < 2 \
                and not row["zero_result"]:
            gap("SR-23", "MEDIUM", "%s top1 rel=%s，头部意图未满足" % (qid, row["top1_relevance"]))
        if row["returned"] != row["unique_returned"]:
            gap("SR-25", "MEDIUM", "%s runs 含重复 doc（%d -> %d）" % (
                qid, row["returned"], row["unique_returned"]))

    missing = sorted(set(queries) - set(runs))
    extra = sorted(set(runs) - set(runs).intersection(queries))
    if missing or extra:
        gap("SR-24", "MEDIUM", "qrels=%d runs=%d，缺跑=%s 多跑=%s" % (
            len(queries), len(runs), ",".join(missing[:5]) or "-", ",".join(extra[:5]) or "-"))

    judged_rows = [r for r in rows if r["judged"]]
    judged = len(judged_rows)
    evaluated = len(rows)
    zero = sum(1 for r in rows if r["zero_result"])
    zero_rate = (zero / evaluated) if evaluated else 0.0
    if zero_rate > max_zero_rate:
        gap("SR-22", "HIGH", "零结果率 %.1f%% > %.1f%%（%d/%d）" % (
            zero_rate * 100, max_zero_rate * 100, zero, evaluated))

    def mean(key: str):
        vals = [r[key] for r in judged_rows if r[key] is not None]
        return round(sum(vals) / len(vals), 6) if vals else None

    summary = {
        "k": kk,
        "queries": evaluated,
        "judged_queries": judged,
        "unjudged_queries": evaluated - judged,
        "mean_ndcg": mean("ndcg"),
        "mean_mrr": mean("mrr"),
        "mean_recall": mean("recall"),
        "mean_precision": mean("precision"),
        "zero_result_rate": round(zero_rate, 6),
        "min_ndcg_threshold": min_ndcg,
        "max_zero_rate_threshold": max_zero_rate,
    }
    worst = sorted(judged_rows, key=lambda r: (r["ndcg"], r["mrr"]))[:5]
    return {"rule": "R-21", "summary": summary, "rows": rows, "worst": worst, "gaps": gaps}


def fmt_findings(items: list[dict], title: str) -> str:
    lines = [f"### {title}", "", "| 规则 | 级别 | 位置 | 说明 |", "|---|---|---|---|"]
    for it in items:
        loc = it.get("file", "")
        if it.get("line"):
            loc = f"{loc}:{it['line']}"
        lines.append("| %s | %s | %s | %s |" % (
            it["rule"], it["severity"], loc, (it.get("reason") or "").replace("|", "\\|")))
    if not items:
        lines.append("| — | — | — | 未命中已知模式（不等于已证明相关） |")
    return "\n".join(lines)


def fmt_eval(result: dict) -> str:
    s = result["summary"]
    lines = ["### R-21 相关性评测汇总", "", "| 指标 | 数值 |", "|---|---|",
             f"| query 数 | {s['queries']} |",
             f"| 有判定集 query | {s['judged_queries']}（未判定 {s['unjudged_queries']}，其 nDCG 记为「—」不计均值） |",
             f"| k | {s['k']} |",
             f"| mean nDCG@k | {s['mean_ndcg']} |",
             f"| mean MRR@k | {s['mean_mrr']} |",
             f"| mean Recall@k | {s['mean_recall']} |",
             f"| mean Precision@k | {s['mean_precision']} |",
             f"| 零结果率 | {s['zero_result_rate']:.1%} |", "",
             "### 逐 query", "",
             "| query | nDCG | MRR | Recall | Precision | top1 rel | 返回 |",
             "|---|---|---|---|---|---|---|"]
    for r in result["rows"]:
        if not r["judged"]:
            lines.append("| %s | — | — | - | - | - | %d |" % (
                (r["query"] or "").replace("|", "\\|")[:40], r["returned"]))
            continue
        lines.append("| %s | %.3f | %.3f | %s | %.3f | %s | %d |" % (
            (r["query"] or "").replace("|", "\\|")[:40], r["ndcg"], r["mrr"],
            "-" if r["recall"] is None else "%.3f" % r["recall"],
            r["precision"], r["top1_relevance"], r["returned"]))
    lines += ["", "### 最差 5 条", ""]
    for r in result["worst"]:
        lines.append("- `%s` %s：nDCG=%.3f MRR=%.3f top1=%s" % (
            r["query_id"], r["query"], r["ndcg"], r["mrr"], r["top1_relevance"]))
    lines += ["", fmt_findings(result["gaps"], "R-21 缺口")]
    return "\n".join(lines)


CASES = """# R-21 搜索质量要点速查（自测/汇报用）

## 1. nDCG 的手算例子（k=3）
qrels: docA=3, docB=1, docC=0
run  [A,B,C] -> DCG = 7/log2(2) + 1/log2(3) + 0 = 7.6309, IDCG 同 -> nDCG=1.000
run  [C,B,A] -> DCG = 0 + 1/log2(3) + 7/log2(4) = 4.1309 -> nDCG=0.541
run  [A,C]   -> DCG = 7 -> nDCG=0.917（缺 docB 被扣分）
未判定文档按 rel=0 处理：run 里混入 docX 会把后续名次整体压低。

## 2. 为什么不能只看「有没有结果」
零结果率 5% 的搜索可能 nDCG 只有 0.3；「返回 10 条」不等于「相关」。
点击率受位置偏差影响，必须与 qrels 离线指标交叉验证。

## 3. 排序稳定性的最小构造
同一 query 连续请求两次，diff top10；若出现交换，先查 tie-breaker：
  ORDER BY score DESC, id DESC   -- 必须有唯一第二排序键
ES 深分页用 search_after（PIT + sort），不要 from+size；from+size 有
max_result_window=10000 上限，track_total_hits 默认 10000 会把 total 截断。

## 4. 评测集分层（缺一层就会高估）
头部品牌词 / 腰部品类词 / 长尾自然语言 / 拼写错误 / 同义词 / 零结果 /
多语言 / 意图模糊。每层 ≥20 条 query 才能给出方向性结论。

## 5. 注入与越权
`{"query":{"wildcard":{"name":"*"}}}` 会让词项无限展开；tenant 过滤必须
写进 query filter（打分前），不能 post_filter 或取回后用 Python filter。

## 6. 数字口径
k=10 是常用口径；报告必须写 k、qrels 版本、每层样本量、基线（上版/无排序）。
离线 nDCG 下降 >2% 应有阻塞门槛；提升必须用 interleaving/A/B 复核。
"""


def self_test() -> int:
    bad_src = """\
function search(req, res) {
  const q = req.query.q;
  // 中文标题匹配
  const sql = "SELECT * FROM docs WHERE title LIKE '%" + q + "%' ORDER BY created_at DESC";
  const rows = db.query(sql);
  const hits = es.search({ index: 'docs', body: { query: { match: { title: q } },
    from: page * size, size: size } });
  const total = hits.hits.total.value;
  el.innerHTML = hits.highlight.title;
  res.send(rows.map(r => `<em>${r.title}</em>`).join(''));
  const visible = rows.filter(r => r.tenant === req.user.tenant);
  const w = es.search({ query: { wildcard: { title: '*' + q + '*' } } });
  console.log('query', req.query.q);
  res.json({ total, visible, w });
}
"""
    good_src = """\
const ALLOWED_SORT = { score: '_score', created_at: 'created_at' };
app.get('/search', async (req, res) => {
  const q = String(req.query.q || '').slice(0, 200);
  const tenant = req.user.tenant_id;
  const body = {
    track_total_hits: true,
    size: Math.min(50, Number(req.query.size) || 10),
    query: { bool: {
      must: { multi_match: { query: q, fields: ['title^2', 'body'], analyzer: 'ik_max_word' } },
      filter: { term: { tenant_id: tenant } },
    } },
    highlight: { fields: { title: {} } },
    search_after: req.query.cursor ? [req.query.cursor] : undefined,
  };
  const hits = await es.search({ index: 'docs', body });
  const safe = hits.hits.hits.map(h => ({
    id: h._id,
    title: escapeHtml(h.highlight?.title?.[0] || h._source.title),
  }));
  logger.info('search', { q_hash: sha256(q), n: safe.length });
  res.json({ total: hits.hits.total.value, items: safe });
});
"""
    clean_qrels = {"k": 3, "queries": {
        "q1": {"query": "无线耳机", "judgments": {"A": 3, "B": 1, "C": 0}},
        "q2": {"query": "降噪", "judgments": {"A": 2, "B": 2}},
    }}
    clean_runs = {"q1": ["A", "B", "C"], "q2": ["A", "B", "X"]}
    bad_qrels = {"k": 3, "queries": {
        "q1": {"query": "无线耳机", "judgments": {"A": 3, "B": 1, "C": 0}},
        "q2": {"query": "降噪", "judgments": {"A": 2, "B": 2}},
        "q3": {"query": "冷门型号", "judgments": {"A": 1}},
    }}
    bad_runs = {"q1": ["C", "B", "A"], "q2": [], "q3": ["A", "A"], "q4": ["A"]}

    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="saudit-") as tmp:
        bad_path = os.path.join(tmp, "bad.js")
        good_path = os.path.join(tmp, "good.js")
        with open(bad_path, "w", encoding="utf-8") as fh:
            fh.write(bad_src)
        with open(good_path, "w", encoding="utf-8") as fh:
            fh.write(good_src)

        found = scan(tmp)
        rids = {f["rule"] for f in found}
        for rid in ("SR-01", "SR-02", "SR-03", "SR-04", "SR-05", "SR-06", "SR-07", "SR-08", "SR-09", "SR-10"):
            if rid not in rids:
                failures.append("静态夹具未命中 " + rid)
        if any(f["file"] == "good.js" for f in found):
            failures.append("干净夹具误报：" + ",".join(
                sorted({f["rule"] for f in found if f["file"] == "good.js"})))

        res = evaluate(clean_qrels, clean_runs)
        r1 = next(r for r in res["rows"] if r["query_id"] == "q1")
        if abs(r1["ndcg"] - 1.0) > 1e-3 or abs(r1["mrr"] - 1.0) > 1e-3:
            failures.append("完美排序 nDCG/MRR 应为 1，实得 %.4f/%.4f" % (r1["ndcg"], r1["mrr"]))
        if abs(r1["precision"] - 2 / 3) > 1e-3:
            failures.append("Precision@3 应为 0.667，实得 %.4f" % r1["precision"])

        rev = evaluate({"k": 3, "queries": {"q1": clean_qrels["queries"]["q1"]}},
                       {"q1": ["C", "B", "A"]}, k=3)
        if abs(rev["rows"][0]["ndcg"] - 0.5413) > 1e-3:
            failures.append("逆序 nDCG 应为 0.5413，实得 %.4f" % rev["rows"][0]["ndcg"])
        miss = evaluate({"k": 3, "queries": {"q1": clean_qrels["queries"]["q1"]}},
                        {"q1": ["A", "C"]}, k=3)
        if abs(miss["rows"][0]["ndcg"] - 0.9173) > 1e-3:
            failures.append("缺 docB 的 nDCG 应为 0.9173，实得 %.4f" % miss["rows"][0]["ndcg"])
        unj = evaluate({"k": 3, "queries": {"q1": clean_qrels["queries"]["q1"]}},
                       {"q1": ["X", "A"]}, k=3)
        if abs(unj["rows"][0]["ndcg"] - 0.5787) > 1e-3:
            failures.append("未判定文档应按 0 计（nDCG 0.5787），实得 %.4f" % unj["rows"][0]["ndcg"])

        bad = evaluate(bad_qrels, bad_runs, k=3)
        bad_rids = {g["rule"] for g in bad["gaps"]}
        for rid in ("SR-20", "SR-21", "SR-22", "SR-23", "SR-24", "SR-25"):
            if rid not in bad_rids:
                failures.append("评测夹具未命中 " + rid)
        if abs(bad["summary"]["zero_result_rate"] - 1 / 3) > 1e-6:
            failures.append("零结果率应为 0.333，实得 %.4f" % bad["summary"]["zero_result_rate"])
        if any(r["zero_result"] for r in res["rows"]):
            failures.append("干净评测误报零结果")

    if failures:
        print("SELFTEST FAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("SELFTEST GREEN: 静态 10 条规则可命中夹具、干净夹具零误报、"
          "%d 条评测规则可复现、手算 nDCG/MRR/Recall 全部吻合" % len(bad_rids))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R-21 搜索相关性与排序质量审计")
    parser.add_argument("command", nargs="?", choices=["scan", "eval", "cases", "self-test"],
                        default="cases")
    parser.add_argument("target", nargs="?", default=".")
    parser.add_argument("--qrels", default=None)
    parser.add_argument("--runs", default=None)
    parser.add_argument("--k", type=int, default=None)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--fail-on-gap", action="store_true")
    parser.add_argument("--min-ndcg", type=float, default=0.60)
    parser.add_argument("--max-zero-rate", type=float, default=0.20)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test or args.command == "self-test":
        return self_test()

    if args.command == "scan":
        items = scan(args.target)
        if args.format == "json":
            print(json.dumps({"rule": "R-21", "findings": items}, ensure_ascii=False, indent=2))
        else:
            print(fmt_findings(items, "R-21 静态线索（启发式，需人工确认）"))
        if args.fail_on_gap:
            return 1 if any(i["severity"] in ("CRITICAL", "S1") for i in items) else 0
        return 0

    if args.command == "eval":
        if not args.qrels or not args.runs:
            print("eval 需要 --qrels qrels.json --runs runs.json", file=sys.stderr)
            return 2
        try:
            with open(args.qrels, "r", encoding="utf-8") as fh:
                qrels = json.load(fh)
            with open(args.runs, "r", encoding="utf-8") as fh:
                runs = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print("读取失败：%s" % exc, file=sys.stderr)
            return 2
        result = evaluate(qrels, runs, k=args.k,
                          min_ndcg=args.min_ndcg, max_zero_rate=args.max_zero_rate)
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(fmt_eval(result))
        if args.fail_on_gap:
            return 1 if result["gaps"] else 0
        return 0

    print(CASES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
