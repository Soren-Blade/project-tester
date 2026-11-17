# 搜索相关性与排序质量（R-21）

一句话：**搜索测试不是看「能不能返回结果」，而是看「返回的是不是用户要的、排序是否可复现、换一次请求还是不是同一批」**——没有 qrels 的「看起来相关」、把零结果当正常、同 query 两次 top-20 不一致，任何一条都会让「搜索能用」退化成「搜索碰运气」。

适用：任何「query → 召回 → 排序 → 结果列表」的项目：电商站内搜索、文档/知识库检索、向量与混合检索、日志检索、多租户 B2B 搜索、带 `q` 参数的列表页。
配套：`assets/search-quality-matrix-template.md`（证据矩阵）、`scripts/search-audit.py`（`scan` / `eval` / `cases`）。
相关规则：R-19（分页与 `total` 口径）、R-20（非法 query 与超时的错误契约）、R-17（同一 query 的缓存键与陈旧度）、R-7（搜索框与结果列表的键盘/读屏可达）、R-4（tenant/ACL 过滤位置）。交叉点：**权限后置过滤 = 越权 + 文档数泄漏（R-4）；结果缓存不分用户 = 串号（R-17）；query 超时回 200 空列表 = 错误契约缺陷（R-20）；翻到第 2 页排序变了 = 相关性结论不可复现（R-19）；搜索框不可键盘操作 = 无障碍缺陷（R-7）**。

## 0. 触发条件与不适用

| 场景 | 是否触发 | 说明 |
|---|---|---|
| `GET /search?q=`、列表页带关键词 | ✅ 必做 | 主战场：qrels + nDCG@10 + 零结果率，三件套缺一不得下结论 |
| 文档 / 知识库 / 帮助中心检索 | ✅ 必做 | 必须覆盖长尾与同义词层，不得只测 5 个头部词 |
| 向量 / 混合检索（ANN + rerank） | ✅ 必做 | 另测 ANN recall 与 rerank 前后指标，不得只报端到端 nDCG |
| 日志检索（KQL / Lucene / SQL 全文） | ✅ 必做 | 用固定查询集对账命中条数，不得只看「能搜到」 |
| 多租户 B2B 搜索 | ✅ 必做 | ACL 过滤须在打分前，不得用「A 搜不到 B」代替隔离结论 |
| 纯 CRUD 精确匹配（`WHERE id = ?`、编码查单条） | ❌ 不适用 | 无召回与排序语义；只写「不适用：无相关性排序面」，**不得**写「搜索结果正确」 |
| 无 query 日志且无法构造判定集（内部工具、离线库） | ❌ 不适用 | 无意图样本时 nDCG 不可算；**不得**用「手工试了几个词」冒充评估 |
| 只有点击日志、无人工/LLM 判定 | ◐ 降级 | CTR 受位置偏差污染；只能测排序稳定性与零结果率，**不得**报 nDCG/MRR 数值 |
| 静态全量枚举（<100 条、无排序选项） | ◐ 部分 | 只测关键词命中与空结果文案，**不得**写「排序质量达标」 |
| 前端 `includes()` 过滤已加载的全量数据 | ◐ 部分 | 前端子串匹配不构成检索排序；只测边界输入，**不得**写「相关性达标」 |

## 1. 先问 8 个检索契约问题

1. **query 从哪来、量级多少**：搜索框 / URL `q` / 语音 / 内部 API；日 UV 与日 query 数决定样本量，也决定「200 条判定集」能否覆盖头部。
2. **文档集规模与更新频率**：万级还是亿级、日增多少、索引重建周期；「新文档多久可被搜到」是独立 SLA。
3. **语言与分词器**：语言清单、每语言分词器（中文须 `ik`/`jieba`/ICU 等，`standard` 按字切分不算中文分词）、停用词表、同义词表版本。
4. **字段与权重**：标题/正文/标签/类目的 boost 值、是否 `multi_match`、拼写容错参数（`fuzziness`、`prefix_length`）。
5. **过滤与权限**：tenant/ACL/上下架/地域过滤在 query 的哪一层（filter context 还是取回后过滤）；过滤后是否仍满足 top-k。
6. **排序信号与实验**：纯 BM25、加业务 boost（销量/新品/佣金）、学习排序或向量 rerank；是否有 A/B 分桶、分桶键是否稳定。
7. **评估集归属**：谁维护 qrels、多久更新一次、能否进 CI；没有归属人的评估集会腐烂。
8. **延迟/超时 SLA**：P95 目标（如 <300ms）、超时阈值与降级行为（超时返回空列表还是缓存/兜底结果）。

> 八问答不出来就先别测「相关性」——此时任何 nDCG 数字都没有可比口径。

## 2. 判定集（qrels）怎么来

**分级 0~3（有序，不合并成二值）**：

| 级别 | 定义 | 典型例子（query=「无线耳机」） |
|---|---|---|
| 3 | 完全满足意图，±1 个可直接使用 | 目标型号的蓝牙真无线耳机商详 |
| 2 | 相关，需再挑一下 | 同品类其他型号、同品牌上一代 |
| 1 | 边缘相关，用户可能点但多半不满足 | 有线耳机、耳机保护套 |
| 0 | 不相关 | 音箱、手机壳、无关文章 |

**标注来源**：人工标注为基准；LLM 辅助初标必须**双人抽检 ≥10%**，抽检一致率 <90% 则整批重标，且不得把 LLM 单标结果直接当 qrels。

**查询分层**（按 query 日志 volume 或显式构造，每层独立出指标）：

| 层 | 定义 | 最少样本 | 主要看什么 |
|---|---|---|---|
| 头部 T1 | 累计流量前 20% 的 query | 30 | nDCG@10 + 人工核对 top-3 |
| 腰部 T2 | 流量 20%~80% | 40 | nDCG@10、MRR@10 |
| 长尾 T3 | 剩余 80% 中抽样 | 40 | 零结果率、Recall@10 |
| 零结果 | 线上返回 0 条的 query | 20 | 兜底与空结果文案 |
| 拼写错误 | 日志真实错拼 + 人工构造 | 15 | 纠错命中与纠错后零结果 |
| 同义词/别名/缩写 | 同义改写对（无线耳机/蓝牙耳机/TWS） | 15 | top-10 交集 |
| 品牌/型号 | 品牌词、含连字符型号（WH-1000XM5） | 10 | 精确命中与变体归一 |
| 多语言 | 非默认 locale 的 query | 10 | 分词器与 locale 一致性 |
| 意图模糊 | 单字、宽泛词（「耳机」「怎么」） | 10 | 结果多样性与澄清入口 |

合计 **≥200 条**；层内 n<30 只报点估计与样本量，**不得**宣称「显著提升」。每层指标须附 95% bootstrap 置信区间（1000 次重采样），CI 半宽 >0.08 的层只写「方向性观察」。

**判定一致性**：≥100 条重叠双人独立标注，0~3 有序分级用二次加权 kappa（quadratic weighted κ），**κ ≥ 0.60 才可用于验收**；0.40~0.60 由第三人仲裁并记录分歧；<0.40 重写标注指南后重标。二值口径（相关/不相关）用 Cohen's κ，门槛同为 0.60。争议样本单列 `disputed`，**不得**直接删除来抬分。

**评估集版本化**：`qrels-v2026.11.json` 固定 `k`、`queries`、`judgments`、`annotators`、`kappa`、`date`、被测 commit；只增不改，新增 query 留旧版对照；跨版本比较指标前先声明用哪一版 qrels。

## 3. 指标与口径

```text
DCG@k  = Σ_{i=1..k} (2^rel_i − 1) / log2(i + 1)
IDCG@k = Σ_{i=1..k} (2^rel*_i − 1) / log2(i + 1)，rel* 为 qrels 中 rel 降序
nDCG@k = DCG@k / IDCG@k   （IDCG@k = 0 时定义为 0，并单列「全无关 query」条数）
MRR@k  = mean( 1 / rank_i )，rank_i = 首个 rel≥1 的文档排名；k 内无 rel≥1 记 0
Recall@k    = |top-k 中 rel≥1 的文档| / |qrels 中 rel≥1 的文档|
Precision@k = |top-k 中 rel≥1 的文档| / k
零结果率    = 返回 0 条的 query 数 / 总 query 数（分母须写明：评估集还是日志全量）
```

- `k` 主口径取 **10**，敏感性取 20，两个都报；只报一个且不写 k 的指标不可复核。
- **未判定文档按 rel=0 处理**；pooling 只到 top-100 时 Recall@k 是**下界**，必须声明 pooling 深度，否则不得把「召回低」当结论。
- 汇总用 **宏平均**（每 query 等权）；按流量加权时须同时给未加权值，否则头部词会掩盖长尾崩塌。
- 基线至少三条：**无排序**（按 id/时间）、**上版**、**默认 BM25 / 默认模型**；提升写 `(new−base)/base` 并同时给绝对值。
- **bootstrap** 1000 次重采样报 2.5/97.5 百分位；两版 CI 重叠或差值跨 0 时，**不得**写「提升 / 下降」。
- 样本 <30 的层不给 p 值，只写「样本不足，未做显著性」。
- **不得用 CTR 替代相关性**：首条点击率天然最高（位置偏差），未展示文档不可能被点击（展示偏差），点击也只代表「进入」不代表「满足」；CTR 仅作辅助信号并与 qrels 交叉。
- 空结果 query 的 nDCG 无定义时单列计数、不参与平均，并在报告里写明条数。

## 4. 查询理解

| 维度 | 用例 | 判据 |
|---|---|---|
| 拼写纠错 | `wirless earbuds`、`蓝牙耳几` | 编辑距离：≤4 字符允许 1，5~8 字符允许 2，>8 允许 2 且不得改首字符；候选须在词典/商品词表命中；纠错后仍零结果比例单独统计，>10% 判纠错无效 |
| 同义词/别名/缩写 | `无线耳机` / `蓝牙耳机` / `TWS` / `真无线` | 四词 top-10 交集 ≥60%，且每组至少 1 条 rel=3 |
| 停用词 | `怎么 连接 蓝牙 耳机` | 去停用词前后 top-10 一致率 ≥80%；品牌/型号不得被当停用词 |
| 大小写与全半角 | `iPhone` / `iphone` / `ＩＰＨＯＮＥ` | NFKC 规范化后 top-10 完全一致；不一致须文档化 |
| 简繁 | `台湾`/`臺灣`、`耳机`/`耳機` | 按声明（等价/不等价）；声明等价则 top-10 一致率 ≥90% |
| 数字与单位 | `5kg` / `5 kg` / `5KG`、`1.5k`、`100-200元` | 归一后同一结果集；区间词不得被解析成减号 |
| 品牌与型号 | `WH-1000XM5` / `wh1000xm5` / `XM5` | 连字符与空格变体命中同一主商品；型号截断不得召回同系列错误型号 |
| query 注入 | `*`、`"`、`~`、`^`、`:`、`\`、`( ) [ ] { }`、`' OR 1=1--` | 当字面量处理或 4xx；不得 500、不得回显解析器原文 |
| 长度与空白 | 空串、纯空格、1 万字符、emoji、`\u0000` | 空/纯空白 → 200 空结果或 4xx；超长 → 4xx 或截断声明；不得 500 |

## 5. 排序与分页

- **排序稳定性**：同一 query 两次请求（间隔 0s 与 60s）top-20 的 id 序列逐位比对；差异条数与位置必须写进证据。ES 用 Lucene 内部 doc id 兜底排序，副本间可能不同——`_score` 相同且无唯一 tie-breaker 时，翻页会重复/丢失。
- **tie-breaker 必须唯一**：`sort: [{"_score":"desc"},{"product_id":"asc"}]`；`tie_breaker_id` 要有 doc values。只用 `_score` 或只用 `created_at` 都不唯一。
- **`search_after` vs `from+size`**：`from+size` 受 `index.max_result_window` 限制（默认 **10000**），且深页每分片都要加载前面所有命中；`search_after` 无此上限但**不能跳页**，需 PIT 或 refresh 间隔内数据不变。
- **`track_total_hits` 默认 10000**：超过即返回 `"relation":"gte"`，`total` 只是下界；写「共 N 条」前必须 `track_total_hits: true` 或声明下界（与 R-19 的 `total` 口径联动）。
- **过滤后排序**：filter 必须在打分/取回前生效；`post_filter` 只裁剪命中、不影响排序与聚合，用它做权限会先按未过滤集合排序，再删掉部分结果 → top-k 不足且顺序错。
- **个性化 / 实验分桶**：同 query 同用户同桶必须稳定；跨桶差异要能归因到具体信号，不得把 A/B 差异当噪声。
- **A/B 用 interleaving**：只看 CTR 会被位置偏差放大；优先 team-draft interleaving 比较偏好，样本量按最小可检测效应算，分流比例另做 SRM 校验（→ R-22）。

## 6. 冷启动与长尾

- **零结果兜底**：同义扩展 → 拼写建议（did you mean）→ 热门/类目回退；兜底结果必须带标记（如 `fallback: popular`），**不得**静默用热门结果冒充「匹配结果」。
- **空结果文案与埋点**：文案给出可操作下一步（去引号、换词、去型号后缀）；埋点记录 query、locale、是否触发建议、是否点兜底。
- **新文档冷启动**：发布 → 可检索时延（如 ≤5 min）要有实测；新品 boost 不得压过相关性主信号；索引/缓存双写不一致时以索引为准并告警。
- **多语言 / 多租户 locale**：每个 locale 独立分词器与停用词；`locale=zh-CN` 不得落到英文分词器；混合语言文档做字段级 language 声明。
- **低资源语言**：无词典、无标注时只报零结果率与排序稳定性，**不得**编造 nDCG；用 LLM 翻译 query 构造判定集须写明方法并抽检。

## 7. 安全与越权

- **query DSL 注入**：`{"query":{"wildcard":{"name":"*"}}}`、`query_string` 的 `*:*`、空 `bool.must` 都能拉全量；拼接 DSL 字符串与拼接 SQL 同类，属 S1。
- **前缀通配性能攻击**：`a*`、`*a*`、`?a?` 在千万级索引上放大 IO；须限制 leading wildcard、`max_expansions` 与超时。
- **highlight XSS**：高亮片段里的 `<img src=x onerror=...>` 必须 HTML 实体转义；前端 `innerHTML` 直出即反射型 XSS（并入 R-1 安全面）。
- **ACL/tenant 过滤在打分前**：用 filter context + 文档级 ACL 字段；取回后过滤会让 `hits.total`、聚合桶泄漏他人文档数，且非授权文档挤占 top-k 导致返回不足 k 条。
- **搜索日志 PII**：query 可能含手机号/邮箱/身份证；采样 + 脱敏（哈希或分词保留）+ 保留期（如 90 天）+ 访问审计；**不得**存明文完整 query 与用户标识。

## 8. 观测与回归

- **query 日志采样与脱敏**：如 1% 全量 + 100% 零结果；记录 `query`、`normalized`、结果数、耗时、桶、locale；脱敏规则版本化。
- **评估集进 CI**：`eval` 作为 PR job，qrels 钉 commit；结果作 artifact 留存，失败可复现。
- **离线回归门槛**：nDCG@10 相对上版**下降 >2% 直接阻塞合并**；MRR@10 或零结果率任一超阈值（如 +3pp）告警；新增 query 层单列对比。
- **在线实验**：最小样本按 MDE 与基线方差算，分流做 SRM 卡方校验（p<0.001 判异常，→ R-22）；实验期不得同时改索引或分词器。
- **指标漂移告警**：周环比 nDCG@10 绝对下降 >0.03、或零结果率 >0.20 触发排查；索引重建后必须重跑评估集并留前后对照。

## 9. 反模式与缺陷判定

| 编号 | 现象 | 级别 | 判据 |
|---|---|---|---|
| SR-01 | 字符串拼接 SQL/DSL（含 `LIKE '%x%'` 全表扫描） | S1 | 注入 payload 改变语义或回显解析器报错；`EXPLAIN` 出现 Seq Scan |
| SR-02 | `ORDER BY created_at` 等非相关性字段冒充相关性 | S2 | 换关键词 top-10 几乎不变 |
| SR-03 | 深分页用 `from+size` / `OFFSET` 且无 `search_after` | S2 | 页码→P95 曲线陡增或直接 4xx |
| SR-04 | `total` 取默认 `track_total_hits`（10000） | S2 | `relation: gte` 却写「共 N 条」 |
| SR-05 | 中文无分词器（按字/空格切） | S2 | 「无线耳机」只命中含完整串的文档，召回显著低于 jieba/ik |
| SR-06 | highlight 未转义（前端 `innerHTML` 直出 / 服务端拼 `<em>`） | S1 | `<img onerror>` 原样出现在响应 HTML 或 DOM |
| SR-07 | 权限过滤后置（post-filter / 内存 filter） | S1 | `total`/聚合含他人文档数，或 top-k 不足 |
| SR-08 | 前导 wildcard / 正则查询（`*耳机`、`.*`） | S2 | 词项无限展开，延迟随索引增长且无法走索引 |
| SR-09 | 无结果上限（`size` 无 cap、返回全量） | S2 | `size=100000` 实际返回行数 |
| SR-10 | 日志存明文 query + PII | S1 | 日志样例中出现手机号/邮箱原文 |

## 10. 验证命令（零依赖优先）

```bash
# 1) 静态扫描：拼接 DSL / LIKE 全表 / 无 tie-breaker / post-filter / highlight 直出
python scripts/search-audit.py scan . --format markdown

# 2) 离线评估（缺 run 的 query 按空结果计入；无判定集的 query 只计零结果率，
#    nDCG 记「—」、不进均值、不触发 SR-21，避免「未评测」被读成「相关性差」）
python scripts/search-audit.py eval --qrels qrels.json --runs runs.json \
  --k 10 --format markdown --fail-on-gap

# 3) 内置反例清单（SR-01~SR-10 的最小复现输入）
python scripts/search-audit.py cases

# 4) 自检：指标实现手算对照 + 脚本自身用例
python scripts/search-audit.py --self-test
```

输入契约（UTF-8 JSON；`k` 可省略，默认 10）：

```json
qrels.json = {"k":10,"queries":{"q1":{"query":"无线耳机","judgments":{"docA":3,"docB":1,"docC":0}}}}
runs.json  = {"q1":["docB","docA","docC"]}
```

输出 markdown 固定含：每 query 一行 `nDCG@10 / MRR@10 / Recall@10 / Precision@10`、宏平均与 bootstrap 95% CI、零结果率（分母=query 总数）、最差 5 条 query（按 nDCG 升序，附 `query` 原文与判定）。`--fail-on-gap` 触发条件：默认 **nDCG@10 < 0.60 或零结果率 > 0.20**，命中即退出码 1；任一 query 缺 run 或 qrels 未覆盖 top-k 时输出 gap 清单，**不得**静默按 0 分补。

## 11. 报告证据写法（R-21 七项）

1. **评估集来源与版本**：qrels 文件名、版本、被测 commit、标注人数与 κ 值、判定 query 总数与分层样本量。
2. **指标表原文**：`eval` 输出的 markdown 原样贴（含 CI），不得只写「nDCG 0.72」这一位数。
3. **最差 5 条 query 原文** + top-10 文档 id + 每条 rel 判定 + 失败归因（分词/召回/排序/过滤）。
4. **零结果与查询理解**：零结果率分子分母、拼写/同义/大小写/单位各层结果与 query 原文。
5. **排序稳定性**：同 query 两次请求 top-20 的 id 序列 diff（差异条数 + 位置），以及第 2 页拼接后的去重结果。
6. **负向安全**：注入 payload 原文 + 响应码 + 是否泄漏文档数/是否高亮转义。
7. **回归对照**：上版 vs 本版同 qrels 的指标差与 CI；未做则写「未做回归对照」并降级。

**不得**写：「搜索功能正常」「结果相关」「排序合理」「召回率高」「nDCG 0.8 所以达标」「用户没反馈问题所以质量 OK」「CTR 高所以相关」「两次结果看着一样所以稳定」「有同义词表所以召回没问题」。

## 12. 项目形态 → 证据

| 形态 | 必做证据 |
|---|---|
| 电商站内搜索 | 分层 qrels + nDCG@10/MRR@10 + 零结果率 + 型号变体命中 + 新品冷启动时延 |
| SaaS 文档检索 | 长尾 query 的 Recall@10 + 同义词/缩写覆盖 + 空结果文案 + 文档更新后可检索时延 |
| 向量 / 混合检索 | ANN recall@k（对暴力检索）+ rerank 前后 nDCG 对照 + 低资源语言零结果率 |
| 日志检索（KQL/Lucene） | 固定查询集命中条数对账 + 时间范围过滤正确性 + 超时降级行为 |
| 多租户 B2B 搜索 | 双租户同 query 结果集对照 + ACL 前/后过滤的 total 与聚合 + 跨租户注入负向 |

## 13. 来源

- [ACM：Cumulated gain-based evaluation of IR techniques（NDCG 原论文）](https://dl.acm.org/doi/10.1145/582415.582418)
- [ir_measures：信息检索指标库与口径说明](https://ir-measur.es/)
- [trec_eval：TREC 官方评估工具（qrels 格式与指标定义）](https://github.com/usnistgov/trec_eval)
- [BEIR：零样本检索基准（跨域评估集与 nDCG@10 报告口径）](https://arxiv.org/abs/2104.08663)
- [Elasticsearch：BM25 相似度与字段 boost](https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules-similarity.html)
- [Elasticsearch：分页结果（`from+size` / `search_after` / `max_result_window`）](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/paginate-search-results)
- [Elasticsearch：排序结果（tie-breaker 与 sort 语义）](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/sort-search-results)
- [scikit-learn：`ndcg_score` 实现与参数](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg_score.html)
- [ACM TOIS：Large-scale validation and analysis of interleaved search evaluation](https://dl.acm.org/doi/10.1145/2094072.2094078)
- [OWASP：Query Parameterization Cheat Sheet（注入防护）](https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html)
