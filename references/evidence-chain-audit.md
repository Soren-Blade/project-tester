# 证据链可追溯性与合规声明对账（阶段 3/4 · 横向叠加）

> 蒸馏自 W3C PROV-DM（W3C Recommendation 2013-04-30）、NIST OSCAL（三层模型与 assessment-results）、NIST SP 800-218 SSDF v1.1（PO/PS/PW/RV 四组与四要素）、in-toto 官方 README（layout / link / in-toto-verify）、GitHub Docs 的 artifact attestations、以及 GitHub `naodeng/awesome-qa-skills` 的 `requirement-traceability-analysis` / `test-report-review` / `skill-change-verification` 分类。来源 URL 与逐条口径见 `CHANGELOG.md` v1.5.0。
> 定位：前面所有手册都在回答「**这个结论对不对**」；本手册回答「**这个结论能不能被别人复核、能不能拿去对账**」。一句话分野：**测试产物不是「跑了多少条」，而是「有没有一条断不掉的证据链」**。

## 0. 适用边界与分工

| 触发 | 叠加本手册 | 不适用 |
|---|---|---|
| 有测试报告 / 发布验收 / CI 门禁，需要结论可复核 | 是 | 一次性探索、无留档要求的临时验证 → 只写「未做证据链对账」，**不得**写「可审计 / 证据链完整」 |
| 声称「符合 SOC2 / 等保 / SSDF / GDPR」「已通过审计」 | 强制 | — |
| 有 R-1~R-8 任一专项证据模板、需要对账覆盖缺口 | 是 | — |
| 只想验制品本身有没有被改过 | 去 `references/supply-chain-testing.md`（R-3） | 制品完整性是证据链的**一个节点**，不是整条链 |
| 只想判断该不该发版 | 去 `references/quality-gates.md` §3 | 对账结果是 Go/No-Go 的输入，不是替代 |

**三条认知打底**：

1. **结论不是证据，证据也不是原始输出**。报告里写「链路完整」是结论；`runs/x.log` 是证据文件；日志里那一行 `trace_id=...` 才是原始输出。三者必须逐级可定位，断一级即不可复核。
2. **「文件存在」不等于「证据有效」**。一份过期（采集于旧 commit）、找不到锚点、或引用了不存在文件的证据，比没有证据更危险——它会让报告看起来完整。
3. **合规声明必须逐条挂证据，不能靠框架名字背书**。NIST 明确说 SSDF「not to create a checklist to follow」；勾完一份清单不能推出「合规通过」。

## 1. 用 PROV 三元组给证据链建模（不引入新工具）

W3C PROV-DM 把溯源建模为三类对象与二元关系，可直接映射到测试：

| PROV 概念 | 原文定义要点 | 测试里的对应物 |
|---|---|---|
| `Entity` | 「things we want to describe the provenance of」，有固定方面 | 测试报告、证据文件、制品、`runs/` 记录 |
| `Activity` | 「occurs over a period of time and acts upon or with entities」，可 consuming / generating | 一次测试执行、一次构建、一次扫描 |
| `Agent` | 「bears some form of responsibility」，可以是某类 entity/activity | 执行人、CI job、工具版本 |
| `wasGeneratedBy(e, a)` | 新实体由某活动生成 | 报告由本轮测试运行生成；日志由该次命令生成 |
| `used(a, e)` | 活动开始使用某实体 | 测试使用了该 commit 的代码、该版本规范 |
| `wasDerivedFrom(e2, e1)` | 实体由另一实体转换/更新/构造而来；仅 usage+generation 链不够，还需活动期间的影响 | 报告结论由原始日志派生（**必须能回溯到日志行**） |
| `wasAttributedTo` / `wasAssociatedWith` | 归责于 agent / 活动责任分配 | 谁跑的、哪个 CI job 产生的 |

> 口径诚实：PROV-DM 的目标是 provenance 在异构系统间的 **interchange**，并支持对「quality / reliability / trustworthiness」形成判断；页面**没有**把 `traceability` 定义成独立术语。本手册借用其对象与关系做**建模语言**，不宣称实现了完整 PROV 合规。

**落地成一条最小链**（缺任一段就标缺口）：

```
被测对象(commit/environment) ──used──> 测试活动(命令/时间窗) ──wasGeneratedBy──> 原始输出
        │                                                              │
        └────────────── subject_commit 绑定 ────────────────────────────┤
                                                                        ▼ wasDerivedFrom
                                                            证据文件(路径 + 锚点 + sha256)
                                                                        ▼ wasDerivedFrom
                                                          报告结论(R-N / PASS / FAIL)
```

`scripts/evidence-audit.py` 就是把这条链压成一份 JSON manifest 后逐段核对。

## 2. 合规声明 ↔ 控制项 ↔ 证据（OSCAL / SSDF 口径）

### 2.1 OSCAL 的分层与可追溯性

NIST OSCAL 是「standardized, data-centric framework」，用 XML/JSON/YAML 机器可读格式表达安全控制与评估，目标是自动化 security assessment / auditing / continuous monitoring。官方把模型组织成三层，且明确「The OSCAL models provide native traceability from the assessment layer to the catalog layer」：

| 层 | 模型（官方精确名） | 用途 |
|---|---|---|
| Control Layer | `catalog` · `profile` · `mapping` | 定义/裁剪控制基线；`mapping` 表达不同权威来源间控制的关系 |
| Implementation Layer | `component-definition` · `system-security-plan` | 描述系统实现与组件如何满足基线 |
| Assessment Layer | `assessment-plan` · `assessment-results` · `plan-of-action-and-milestones` | 计划、结果与整改 |

其中 **`assessment-results` 表示一组评估活动产出的信息，包括评估执行时间、scope、收集的 evidence 和 findings**，并支持 periodic 与 continuous assessments；`plan-of-action-and-milestones` 表示需由系统所有者处理的 findings。

**借用到测试报告**：一条合规声明必须写明「控制项 → 评估活动（哪次测试、时间窗、scope）→ evidence（哪个文件哪一行）→ finding（PASS/FAIL/BLOCKED）→ 未闭环项」。OSCAL 官网自述可把审计时长「from months to minutes」，这是**官网宣传口径**，不是本技能的实测承诺。

### 2.2 SSDF v1.1 的四组实践与「不是清单」

NIST SP 800-218（SSDF Version 1.1，2022-02）把实践分为四组，每条实践由四要素定义：

| 组 | 精确名 | 与本手册最相关 |
|---|---|---|
| PO | Prepare the Organization（v1.1 新增 PO.5 安全开发环境） | 证据留档规范由谁定义 |
| PS | Protect the Software | **PS.3.2：collecting and sharing provenance data for all components of software releases** |
| PW | Produce Well-Secured Software | **PW.1.2：tracking software security requirements, risks, and design decisions** |
| RV | Respond to Vulnerabilities | 发现缺口后的整改闭环 |

四要素：**Practice**（名称 + 唯一标识 + 理由）、**Task**、**Notional Implementation Example**（「no examples or combination of examples are required」）、**Reference**。NIST 明确：「The intention of the SSDF is not to create a checklist to follow」。

**因此本手册禁止两类写法**：① 把 SSDF/等保/SOC2 的控制项名抄一遍就写「合规通过」；② 把「有证据文件」写成「控制项已满足」。正确写法是逐控制项列「关联结论 + 证据锚点 + 缺口声明」，并把未映射项显式列出。

## 3. 供应链证据链：从「每步谁做的」到「机器可验」

### 3.1 in-toto（证据链的结构范本）

in-toto 官方 README 的核心是可验证的**连续链**：

| 组件 | 官方精确术语与内容 |
|---|---|
| `layout` | 由 `project owner` 创建，列出供应链 `steps` 的**顺序**与获授权的 `functionaries`；包含 `expiration date`、`readme`、`functionary keys`、`signatures`、`software supply chain steps`、`inspections` |
| `steps` | 需唯一名称，`material and product rules` 定义该步应操作哪些文件；规则名 `CREATE` / `DELETE` / `MODIFY` / `ALLOW` / `DISALLOW` / `REQUIRE` / `MATCH`，并建议以 `DISALLOW *` 收尾 |
| `link` file | 记录 `step name`、`command`、`materials`、`products` 与其他相关细节，由 `functionary's key` 签名；「link files provide the required evidence to establish a continuous chain」 |
| `in-toto-verify` | 检查 layout 由 owner 私钥签名、未过期、每步由授权 functionary 执行并签名、命令符合预期、materials/products 符合规则、并运行 `inspections` |

**最值得抄进测试纪律的一条边界**（README 原文）：执行中被修改或使用、但**没有显式作为 artifacts 传入**的文件，「are not recorded in the link file」。映射到测试：**没登记进证据清单的原始输出，等于不存在**——这就是 `scripts/evidence-audit.py` 要求 `anchor` 可解析、要求 `sha256` 的原因。

> 口径诚实：该 README **没有**给出 `threshold` 的定义，也**没有**使用 `expected materials/products` 这一短语；本手册只写页面实际出现的 `material and product rules`、`materials`、`products`，不臆造字段。

### 3.2 GitHub artifact attestations（制品绑定的真实命令）

GitHub Docs 给出的是**产品级**能力（不是通用标准）：`actions/attest@v4` 为二进制/镜像生成 build provenance，也可为 SBOM 生成 attestation。

```bash
# 生成（workflow 内，须 permissions: id-token: write / contents: read / attestations: write）
- uses: actions/attest@v4
  with:
    subject-path: 'PATH/TO/ARTIFACT'      # 镜像则用 subject-name + subject-digest + push-to-registry
    # sbom-path: 'sbom.json'             # 为 SBOM 生成 attestation 时加这一项

# 验证（官方原文命令）
gh attestation verify PATH/TO/YOUR/BUILD/ARTIFACT-BINARY -R ORGANIZATION_NAME/REPOSITORY_NAME
gh attestation verify oci://ghcr.io/ORG/IMAGE:test -R ORGANIZATION_NAME/REPOSITORY_NAME
gh attestation verify PATH/TO/ARTIFACT -R ORG/REPO --predicate-type https://spdx.dev/Document/v2.3
gh attestation verify PATH/TO/ARTIFACT -R ORG/REPO --format json --jq '.[].verificationResult.statement.predicate'
```

**证据纪律**：R-3 仍要求「命令原文 + 退出码 + 输出行」；这里额外要求把 `-R` 的仓库范围、`--predicate-type`、验证时间与 `subject-digest` 一并留档，否则「验证通过」无法复核。离线/气隙环境官方另有 verify-attestations-offline 流程，不能套用上面的在线命令。

## 4. 落地：manifest 字段规范与自动对账

### 4.1 manifest 最小字段（人类可读、可版本化）

```json
{
  "subject": {
    "name": "api-service",
    "commit": "abc123",
    "environment": "win32 / Python 3.13 / Node 22",
    "window": "2026-11-12T09:00+08:00 ~ 2026-11-12T11:00+08:00"
  },
  "claims": [
    {
      "id": "R-3",
      "statement": "制品可信",
      "status": "PASS",
      "evidence": "runs/2026-11-12-1.log",
      "anchor": "L12",
      "subject_commit": "abc123",
      "conclusion_class": "运行时质量"
    }
  ],
  "control_mapping": [
    {"control": "SSDF PS.3.2 provenance", "claim_ids": ["R-3"], "status": "mapped"}
  ]
}
```

| 字段 | 作用 | 缺失后果 |
|---|---|---|
| `subject.commit` / `environment` / `window` | 被测对象与环境指纹 | 无法判断证据是否过期、结论适用于哪次构建 |
| `evidence` | 证据文件（相对 `--root` 或 manifest 目录） | `dangling_reference` / `pass_without_proof` |
| `anchor` | `L<n>` 行号或 `text:<原文片段>` | `unresolvable_anchor`；没有锚点＝「引用了文件但指不到那一行」 |
| `subject_commit` | 证据采集时的 commit | `stale_evidence`；PASS 结论缺此项直接 BLOCK |
| `conclusion_class` | 静态记录 / 评测准备度 / 运行时质量 / 发布批准 | `unclassified_conclusion`（WARN），防止四类结论互冒充 |
| `control_mapping` | 合规声明 → 控制项 → 关联结论 | `unmapped_control`；无映射须写「未做合规性声明对账」 |

`scripts/evidence-audit.py` 会自动补算每个证据文件的 `sha256`，并把锚点那一行原文抽出放进审计表。

### 4.2 命令

```bash
# 对账 + 导出审计表（不加 --output 时只打印，不改任何文件）
python scripts/evidence-audit.py audit --manifest .test-memory/evidence.json \
  --root . --format markdown --output .test-memory/audit-export.md

# CI 门禁：有 BLOCK 级缺口即退出 1
python scripts/evidence-audit.py audit --manifest .test-memory/evidence.json \
  --fail-on-gap --format json

# 证明门禁本身可证伪（悬空引用 / 过期 / 锚点失效 / PASS 无证据 / 未分类结论）
python scripts/evidence-audit.py --self-test
```

| 检出码 | 含义 | 结论处置 |
|---|---|---|
| `dangling_reference` | 证据文件不存在 | 该结论作废 → 待确认 |
| `unresolvable_anchor` | 锚点超出行数或片段找不到 | 该结论作废 → 待确认 |
| `stale_evidence` | 证据 commit 与当前 commit 不一致 | 重采或明确标「历史证据，不适用本次」 |
| `pass_without_proof` / `missing_evidence` | PASS 却没登记证据 | 作废 → 待确认 |
| `unmapped_control` | 控制项指向未登记的结论 | 补映射或写出缺口 |
| `unclassified_conclusion` | 四类结论未标注 | WARN；报告须补 |

> **对账通过 ≠ 合规通过 ≠ 软件安全**。脚本输出固定带一行：「对账通过只证明证据链可解析，不证明合规或软件安全」。这与 R-3「签名有效 ≠ 无漏洞」、R-7「axe 0 violations ≠ WCAG 合规」是同一纪律。

## 5. 审计导出与四类结论

`--format markdown` 产出五段：结论→证据→原始输出表、控制项映射表、缺口清单、锚点原文、局限声明。导出件本身是 `Entity`，也应记录 `sha256` 与生成时间，避免「审计导出被事后替换」。

报告里必须区分（`references/self-evolution.md` §4）：

| 结论类型 | 证据链能证明什么 |
|---|---|
| 静态记录 | 文件写了、manifest 登记了 |
| 评测准备度 | 门禁配置好、`--self-test` 通过 |
| 运行时质量 | 证据文件里有**本次**真实执行的原始输出 |
| 发布批准 | 用户/评审者认可（证据链无法代替） |

## 6. 测试卡（EA-1 ~ EA-13）

| # | 测试动作 | 通过判据 | 常见失败 |
|---|---|---|---|
| EA-1 | 每条 PASS/FAIL 结论都登记 `evidence` + `anchor` | 无 `pass_without_proof` | 报告里写「详见附件」但没路径 |
| EA-2 | 逐个证据文件解析锚点 | 行号存在或片段命中 | 引用 `L200` 但文件只有 30 行 |
| EA-3 | 证据与 `subject_commit` 绑定 | 无 `stale_evidence` | 拿上个月的日志当本轮证据 |
| EA-4 | 记录证据 `sha256` | 每条有 64 位 hex | 只有文件名，事后被改也看不出 |
| EA-5 | 环境指纹与时间窗 | OS/运行时/版本/窗口齐全 | 只写「本地测过」 |
| EA-6 | 四类结论逐条标注 | 无 `unclassified_conclusion` | 把「门禁配置好」写成「质量达标」 |
| EA-7 | 合规声明逐控制项挂证据 | 控制项 → 结论 → 锚点三段齐全 | 抄一份 SSDF 清单就写「合规」 |
| EA-8 | 未映射/未覆盖项显式列出 | 缺口清单非空时如实写 | 静默跳过不适用的控制项 |
| EA-9 | 重放：换个人按锚点能找到同一行 | 锚点原文可逐字对照 | 锚点写成「见日志后半段」 |
| EA-10 | `--self-test` 门禁有效 | 5 种缺陷全部被检出 | 门禁只会打 PASS，不可证伪 |
| EA-11 | 审计导出件自身留痕 | 有 hash 与生成时间 | 导出后被覆盖、无版本 |
| EA-12 | 对账结论不越界 | 未把「链可解析」写成「合规/安全」 | 用对账 GREEN 冒充发布批准 |

## 7. R-9 证据链可追溯与可复核性（可证伪规则，见 SKILL.md）

| 声称 | 必须附的证据 | 不适用时的写法 |
|---|---|---|
| 「测试结论可复核 / 证据链完整 / 已通过审计 / 合规声明有证据支撑」 | ① 每条结论 → 证据文件 → 原始输出的三级引用链，且 `anchor` **可解析**（行号存在或片段命中）；② 证据 `sha256` + 被测对象 `commit` / 环境指纹 / 时间窗绑定，无 `stale_evidence`；③ 自动对账结果（`scripts/evidence-audit.py`）含覆盖缺口、悬空引用、过期证据与四类结论区分；④ 合规声明 → 控制项 → 证据的映射表与**未映射项声明**；⑤ 审计导出件自身 hash 与生成时间 | 一次性探索测试、无留档要求的临时验证 → 只写「未做证据链对账 / 不适用：无留档要求」，**不得**写「可审计 / 证据链完整 / 通过审计」；只有部分证据时写「证据链存在 N 处缺口，结论降级为待确认」，**不得**写「证据齐全」 |

推论：**「报告写全了」不能推出「结论可复核」**；**「证据文件都在」不能推出「证据没过期」**；**「对账 GREEN」不能推出「合规通过」**。任何一段链断裂而声称通过，一律作废降为「待确认」。

## 8. L0 零依赖降级路径（脚本也跑不起来时）

```bash
# 用 git + grep 手工重建最小链（不写脚本、不联网）
git rev-parse HEAD                              # subject.commit
git log -1 --format='%cI %s'                    # 时间窗与变更
grep -n 'trace_id\|sha256\|PASS' .test-memory/runs/*.log | head -40   # 锚点 L<n>
sha256sum .test-memory/runs/*.log               # 证据 hash
```

降级时报告固定写一行：「本轮仅做**人工证据链走查**（git + grep + sha256sum），**未做自动对账与审计导出、未逐条验证锚点**，结论降级为「待确认」」，并标 `BLOCKED` 而非 Pass。手工走查仍可列出链，但不能升级成「可审计」。

## 9. 报告字段与分工

用 `assets/evidence-chain-template.md` 记录：subject 指纹、逐条结论→证据→锚点→hash、控制项映射、对账缺口、锚点原文、四类结论标注、R-9 结论与不适用声明。

| 主题 | 去哪 |
|---|---|
| 制品 digest / SBOM / 签名验证 | `references/supply-chain-testing.md`（R-3） |
| 隐私与 GDPR 控制项证据 | `references/privacy-compliance-testing.md`（R-6） |
| 视觉基线是否被悄悄替换 | `references/cross-platform-testing.md` §6A |
| AI 生成用例的杀伤力证据 | `references/test-effectiveness-testing.md` §5B |
| 全局 Go/No-Go | `references/quality-gates.md` §3（R-9） |
| 记忆树与 runs 格式 | `references/memory-tree.md` |
| 工具与降级 | `references/tools.md` |

## 10. manifest ↔ OSCAL `assessment-results` 字段映射（R-9 证据链可机读导出）

> 蒸馏自 NIST OSCAL 的 Assessment Layer 模型（官方三层：`assessment-plan` / `assessment-results` / `plan-of-action-and-milestones`，且明确「native traceability from the assessment layer to the catalog layer」）。`assessment-results` 表示一组评估活动产出的信息，包含 scope、收集的 `evidence` 与 `findings`，并支持 periodic / continuous assessments。
> 定位：前面 §4 的 manifest 是**人类可核对**的结论→证据→锚点链；本节能把它**自动导出**成 OSCAL `assessment-results` JSON，让 R-9 的证据链直接喂给 GRC / 审计工具，而不必手工重录。一句话分野：**导出件是「同一份证据的另一种编码」，不是新的评估结论**。

### 10.1 字段映射（manifest → OSCAL）

| manifest 字段 | OSCAL `assessment-results` 落点 | 备注 |
|---|---|---|
| `subject.name` / `subject.commit` / `environment` / `window` | `metadata.title` + `result.description` + `result.start`/`end`（window 拆两端） | 被测对象指纹写进结果级元信息 |
| 每条 `claim`（id/statement/status/evidence/anchor/sha256） | 一条 `finding`：`uuid`、`title`（claim.id + statement）、`description`、`implementation-status.state`、若干 `relevant-evidence`（证据文件路径 + `href` + `sha256` 摘要 + anchor 原文） | `state` 由 status 映射：PASS→`implemented`、FAIL→`no-expectation`/问题、`不适用`→`not-applicable`、`待确认`→`partial`、BLOCKED→`planned` |
| `anchor`（L<n> / text:） | `relevant-evidence.description` 里的锚点原文片段 | 保留可复核锚点 |
| `control_mapping`（control / claim_ids） | `result.local-definitions` 或直接挂到对应 `finding`，并生成 `observation`（评估活动）记录"哪次测试、时间窗、scope" | OSCAL 用 `observation` 承载评估活动与证据采集，`finding` 通过 `location.related-observation` 关联 |
| 四类 `conclusion_class` | `observation.methods` / `prop`（区分静态记录 / 评测准备度 / 运行时质量 / 发布批准） | 防止四类结论被混为一谈 |
| 自动对账的缺口清单（dangling / stale / 不可解析锚点等） | `finding.implementation-status.state=partial` 或追加 `prop`（缺口码），并在 `prop` 显式标 `gap` | 缺口随导出件一起带走，不丢 |

### 10.2 诚实边界（导出件不得越界）

- 导出只做**字段搬运**：manifest 里是 `待确认` / 缺口，导出件也必须是 `partial` / `gap`，**不得**因为「有了 OSCAL 文件」就写成 `implemented` 或「已通过 OSCAL 合规评估」。
- OSCAL 是**可机读格式**，不是**合规裁决**：审计员 / 评审者仍需按 `catalog` 逐控制项判定。`scripts/evidence-audit.py --format oscal` 的输出固定带一行「本导出件只证明证据链可机读编码，不证明合规通过或软件安全」，与 §4 的对账 GREEN 同一纪律。
- 字段名依据 OSCAL `assessment-results` 模型（`metadata` / `result` / `finding` / `observation` / `relevant-evidence` / `implementation-status.state`）。本轮未能实时取到该子页（官方 reference 页返回 404，JS 渲染不可抓），以下字段以 OSCAL 模型规范描述为准，**落地以目标组织实际采用的 OSCAL 版本校验**——若对方用 `assessment-plan` + `assessment-results` 分离建模，需额外补 `import-applicant` 与 `local-definitions`，不要臆造对方不需要的字段。
- 转换只在**确有 OSCAL 消费方**时启用（`scripts/evidence-audit.py --format oscal`）；无消费方时仍用 §4 的 markdown 导出，避免造无人使用的转换层。

### 10.3 测试卡（EA-13）

| # | 测试动作 | 通过判据 |
|---|---|---|
| EA-13 | 对同一份 manifest 分别跑 `--format markdown` 与 `--format oscal` | 两者覆盖的 claim 数量一致；`oscal` 导出里每个 `finding` 都能回溯到 manifest 的某条 claim 与证据文件；`待确认`/`缺口` 未被翻成 `implemented` |

> 口径诚实：`--format oscal` 是 v1.6 新增的可选导出；`--self-test` 已覆盖其对等性与不越界检查（见 `scripts/evidence-audit.py`）。
