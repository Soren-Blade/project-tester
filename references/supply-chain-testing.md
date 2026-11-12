# 软件供应链与制品完整性测试（阶段 3 · 横向叠加）

> 蒸馏自 OWASP Top 10:2025 A03、OWASP Software Supply Chain Security / Dependency Graph & SBOM / Vulnerable Dependency Management Cheat Sheets、SLSA v1.0 spec（levels / provenance / verifying-artifacts）、NTIA SBOM 最小要素、以及 `anchore/syft`、`anchore/grype`、`google/osv-scanner`、`sigstore/cosign`、`slsa-framework/slsa-verifier`、npm `ci` 官方文档；v1.4 追加 Reproducible Builds 官方定义（§2A 可复现构建）。来源 URL 见 `CHANGELOG.md` v1.2.0 / v1.4.0。
> 定位：前面所有手册测的是**运行时行为**；本手册测的是**「我拿到的这个制品，是不是我以为的那个」**。依赖清单、构建产物、签名与来源证明都属于交付链，跑通功能不代表交付可信。

## 0. 适用边界与分工（先别把它塞进安全测试）

| 触发 | 叠加本手册 | 不适用 |
|---|---|---|
| 项目有 lockfile / 依赖清单 / 容器镜像 / 发布产物 / CI 流水线 | 是 | 纯源码脚本、无构建产物的静态页 → 只写「未做制品完整性验证」，**不得**写「供应链安全」 |
| 项目要发布、交付给他人、被他人安装 | 是 | 本地一次性脚本、离线环境 → 标注缺口，不判 Pass |
| 只关心运行时越权/注入 | 去 `references/security-testing.md` | 本手册不重复 BOLA/注入用例 |

**三条认知打底**（都来自官方原文，最容易自欺）：
1. **组件没出现在 SBOM 里 ≠ 软件里没有它**：「A component missing from an SBOM is not evidence that it is absent from the software.」
2. **签名有效 ≠ 安全**：签名只认证声明的来源与完整性，「do not prove that an SBOM is accurate or complete, that software is safe, or that a trusted builder has not been compromised.」
3. **「生成」与「验证」必须成对**：SBOM 要求 production + consumption 双端自动化；provenance 要求 build platform 生成 + 验证器实际执行验证。只做一半不构成可验证规则。

## 1. 四类测试对象与最小证据

| 对象 | 要回答的问题 | 最小证据 |
|---|---|---|
| 依赖与锁文件 | 装的是不是被评审过的那些版本？ | lockfile 入库、冻结安装命令退出码、`git diff` 前后对比、registry/scope 配置 |
| SBOM | 交付物里到底有什么（含传递依赖）？ | SBOM 原件 + 生成器与版本 + 生成时间 + 覆盖缺口声明 |
| 制品、签名、provenance | 这个二进制/镜像由谁、从哪个源、怎么构建？ | `sha256sum` / 验证器命令原文 + 退出码 + `PASSED` 输出行 + `subject` digest 比对 |
| CI/CD 完整性 | 流水线能不能被绕过或污染产物？ | 构建配置入库、protected branch、ephemeral 构建、私有 registry 不可旁路、密钥不入仓 |

## 2. 依赖与锁文件测试卡（L0 零依赖也能跑）

| # | 测试动作 | 通过判据 | 常见失败 |
|---|---|---|---|
| D-1 | 查 lockfile 是否存在且入库：`git ls-files '*lock*' 'go.sum'` | 有且被追踪 | 只有 `package.json`，用浮动范围 `^1.2`/`latest` |
| D-2 | 冻结安装：`npm ci` / `pnpm i --frozen-lockfile` / `pip install -r requirements.txt --require-hashes` | 退出码 0；`npm ci` 在 package.json 与 lock 不一致时**必须报错**（官方：will exit with an error, instead of updating the package lock）；绝不写回 lockfile | CI 里用 `npm install`，悄悄改了依赖树 |
| D-3 | 同一 commit 连续两次干净构建，比对产物 `sha256sum` | digest 一致，或明确列出不可复现原因（时间戳、随机排序） | 两次 digest 不同却写「可复现构建」 |
| D-4 | 依赖混淆：检查私有包名是否占用公共 namespace、registry 优先级、`.npmrc`/`pip.conf` scope 配置 | 私有包强制走受信任 registry；无直连公共仓库旁路 | 同名包被公共源抢先解析 |
| D-5 | 直接 + 传递依赖盘点：`npm ls --all` / `pipdeptree` / `go list -m all`；与 SBOM 逐项对照 | 数量与版本对得上；对不上的写进缺口，不当作"没有" | manifest 有、SBOM 无，却判「清单完整」 |
| D-6 | 检查 `alpha`/`beta`/`latest`/`*`/git 分支引用 | 只有已验证的 release 版本 | 生产依赖指向 main 分支 |
| D-7 | 告警抑制范围：`npm audit` 忽略项 / scanner ignore list | **按 CVE 精确抑制**且附理由与补丁测试记录；不存在整包永久忽略 | 「Silencing the scanner or bumping a version string is not remediation.」 |
| D-8 | 补丁有效性：漏洞复现用例在未打补丁版本失败、在打补丁版本通过 | 两种结果都留日志；「A test that passes in both cases proves nothing about the patch.」 | 只跑应用测试，不跑依赖自身测试 |
| D-9 | 上游可用性：是否仍在维护、是否有安全公告流程 | 有记录；停维护且有已知漏洞 → 写迁移/虚拟补丁方案 | 「没报错」当「没问题」 |
| D-10 | 安装脚本审查：`preinstall`/`postinstall`/`setup.py` 是否有网络外联 | 无异常外联；必要时 `--ignore-scripts` 复测 | Shai-Hulud 类 npm 蠕虫正是借 postinstall 传播（OWASP A03:2025 场景 3） |

## 2A. 可复现构建实测（v1.4 增强，落地顺延提案）

> 蒸馏自 Reproducible Builds 官方定义：给定相同的 **source code / build environment / build instructions**，任何一方都应能重建出 **bit-by-bit identical** 的产物；验证方式是逐位比较或密码学 hash 一致。D-3 此前只写了「两次构建比对 digest」，本节把三类输入与差异归因补齐。

**三要素必须同时固定**（缺一就不能写「可复现」）：

| 要素 | 要记录什么 | 常见漂移源 |
|---|---|---|
| source code | commit SHA、子模块/依赖解析结果、有无未提交改动 | 浮动版本、未锁依赖 |
| build environment | 编译器/运行时版本、OS/架构、locale、时区、环境变量、构建路径 | 不同镜像、绝对路径被写进产物 |
| build instructions | 完整构建命令、脚本版本、并行度、构建参数 | 随机排序、并发产物顺序 |

```bash
# 同 commit、同环境、同指令，两次干净构建并比对
git rev-parse HEAD > /tmp/build-inputs.txt
sha256sum dist/* > /tmp/digest-a.txt
# 清理产物后按完全相同的命令重建
sha256sum dist/* > /tmp/digest-b.txt
diff -u /tmp/digest-a.txt /tmp/digest-b.txt && echo "PASS: bit-identical" || echo "FAIL: 不可复现"
# 逐位差异定位（工具可选，命令以官方文档为准）
diffoscope dist/a.tar.gz dist/b.tar.gz | head -80
```

| # | 检查 | 判据 |
|---|---|---|
| RB-1 | 两次干净构建 digest 一致 | 逐位相同或 sha256 全部一致；不一致必须列出具体原因 |
| RB-2 | 三类输入已固定并留档 | commit / 环境指纹 / 完整命令都有原文 |
| RB-3 | 时间戳确定性 | 产物含构建时间时，核对是否统一（如 `SOURCE_DATE_EPOCH` 一类机制）；未统一则写明 |
| RB-4 | 路径与顺序确定性 | 绝对路径、文件遍历顺序、并行构建产物顺序不影响结果 |
| RB-5 | 差异可解释 | 每个不一致都能归因到具体输入；归因不了写「待确认」 |

> 口径诚实：`SOURCE_DATE_EPOCH`、`diffoscope` 等是可复现构建生态中常用的机制/工具线索，本手册只作检查方向，**不臆造具体参数，也不把「设置了环境变量」当成「已可复现」**；以两次 digest 的实际比对结果与各工具官方文档为准。R-3 的证据要求不因本节放宽——digest 不一致却写「可复现构建」按 R-3 作废结论。

## 3. SBOM 测试卡

| # | 检查 | 判据 |
|---|---|---|
| B-1 | 格式 | CycloneDX 或 SPDX 的 JSON/XML；先按该格式 schema 校验再谈内容 |
| B-2 | NTIA 七要素 | supplier / component name / version / unique identifier / dependency relationship / author / timestamp 七项齐全 |
| B-3 | 元数据 | 被描述的产品、生成时间、生成器身份与版本（如 `syft 1.x`） |
| B-4 | 覆盖 | 组件名、版本、supplier、包标识、可用 hash；**直接 + 传递依赖关系**；bundled library 与 OS 包 |
| B-5 | 与最终制品对账 | 依赖解析后生成，再与最终包/镜像比对；「manifests alone can misrepresent shipped contents」 |
| B-6 | 缺口显式声明 | incomplete / unknown coverage 明确写出；不把「没列」当成「没有」 |
| B-7 | 每 release 独立 | 每个发布版本各有 SBOM，重建后与上一版 diff 并更新部署映射 |
| B-8 | 绑定制品 | SBOM 通过**签名 attestation** 绑定到最终制品的 digest；「Signing the artifact and SBOM separately does not establish that relationship.」 |
| B-9 | VEX 复核 | 接受「not affected」前验证签发者身份、文档完整性、理由是否针对确切产品版本与部署条件 |
| B-10 | 原件留存 | 原始 SBOM 与签名证据随 release 保存；限制写权限 |

## 4. 制品、签名与 provenance 的真实命令

```bash
# 生成 SBOM（Syft；不加 -o 只是列包，不是 SBOM）
syft ./my-project -o cyclonedx-json=./cdx.json
syft alpine:latest -o spdx-json=./spdx.json -o cyclonedx-json=./cdx.json

# 漏洞扫描（记录工具版本 + 数据源 + 时间戳，缺一不算证据）
grype sbom:./cdx.json
grype <image>:<tag>
osv-scanner scan source -r /path/to/your/dir       # V2；递归找 package.json/go.mod/pom.xml
osv-scanner scan image my-image-name:tag           # layer-aware 容器镜像
trivy image <image>:<tag>                         # 或 trivy fs .

# 签名验证（cosign，keyless 必须写明期望身份与 issuer）
cosign verify $IMAGE --certificate-identity=$IDENTITY --certificate-oidc-issuer=$OIDC_ISSUER
cosign verify --key cosign.pub $IMAGE_URI:1h
cosign verify-attestation --key cosign.pub $IMAGE_URI
cosign verify-blob artifact --bundle artifact.sigstore.json \
  --certificate-identity "https://github.com/ORG/REPO/.github/workflows/release.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"

# SLSA provenance 验证（artifact 是位置参数，不是 --artifact-path）
slsa-verifier verify-artifact <artifact> \
  --provenance-path <artifact>.intoto.jsonl \
  --source-uri github.com/<org>/<repo>              # 只支持 GitHub URI，tag 用 --source-tag
slsa-verifier verify-github-attestation <artifact> \
  --attestation-path <artifact>.intoto.jsonl \
  --builder-id https://github.com/<org>/<repo>/.github/workflows/<wf>.yml \
  --source-uri github.com/<org>/<repo>              # 此子命令 builder-id 必填
```

**期望输出要留原文**：`PASSED: Verified SLSA provenance` / `PASSED: SLSA verification passed`；同时记录 tlog 条目、builder、commit。`--source-uri` 别塞 tag；验证 commit SHA 用 `--print-provenance` 检查 config source / materials。验证器要传**不可变引用**（immutable reference），避免 TOCTOU。

## 5. SLSA Build 等级判级表（v1.0 spec）

| Level | 官方 summary | 重点防范 | 测试时怎么判 |
|---|---|---|---|
| L0 | No guarantees | — | 本机开发构建、单测 |
| L1 | Provenance exists | 失误、文档缺失 | 有 provenance 描述 build platform / process / top-level inputs；**可不完整、可不签名** |
| L2 | Hosted build platform（签名 provenance） | 构建后被篡改 | 专用基础设施 + 数字签名 + 下游验证真实性 |
| L3 | Hardened builds | 构建中被篡改 | 运行间互不影响、签名密钥对用户定义构建步骤不可访问 |

> v1.0 起只有 **Build track**（Source 部分被移出）。注意 `levels` 页为描述性概览，逐条强制要求见 `requirements` 页——报告里别把「概览」当「合规认证」。

**provenance 必填结构（REQUIRED for SLSA Build L1）**：`predicateType` 恒为 `https://slsa.dev/provenance/v1`；`predicate.buildDefinition`（含 `buildType`、`externalParameters`）与 `predicate.runDetails.builder.id` 必填；`BuildMetadata` 无必填字段。

**验证三步（verifying-artifacts）**：
1. **Check SLSA Build level**：配置 roots of trust（builder 公钥身份 + `builder.id` → 可信等级）→ 验签名 → 验 `statement.subject` 与制品 digest 一致 → 验 `predicateType` → 查 `builder.id` 对应等级（默认 L1）。
2. **Check expectations**：比对 builder identity、canonical source repository、`buildType`、`externalParameters`；「Any unrecognized `externalParameters` SHOULD cause verification to fail.」期望值以 **package name** 绑定，provenance 以 **artifact** 绑定，别混淆。
3. **递归依赖（可选）**：`resolvedDependencies` 完整性 v1.0 无要求，best-effort；需要裁剪/例外机制。

**硬约束**：`externalParameters` 是 untrusted，「MUST be included in the provenance and MUST be verified downstream」；`internalParameters` 由可信平台内部设置、无需下游验证；`Consumers MUST accept only specific signer-builder pairs`（GitHub 不能替 Google Cloud Build 签）；未识别字段 MUST ignore，但 `externalParameters` 内未识别字段 SHOULD reject。

> 口径诚实标注：OWASP Dependency Graph & SBOM Cheat Sheet 引用的是 `slsa.dev/spec/v1.2/verifying-artifacts`；本轮实读并逐条核验的是 **v1.0** 三个页面（levels / provenance / verifying-artifacts）。v1.2 仅记录链接，未逐条比对，报告不得写成「已核验 v1.2」。

## 6. CI/CD 完整性静态审查（跑不起来也能做）

- 构建在隔离、临时（ephemeral）环境执行，结束后销毁；无共享缓存污染
- pipeline 配置、build script、config 全部入 VCS，套用 review / merge rules / protected branches
- 构建工具清单含版本与插件，并监控漏洞库与厂商公告
- 最小化用户可控构建参数；私有制品库入库前 review，**不存在直连公共仓库的旁路**
- 构建/开发/VCS 环境最小权限、职责分离、MFA、凭据轮换；凭据不明文、不入仓
- 认证尝试与配置变更有日志，汇总到集中式日志；日志可行动（actionable）
- CI 内自动化 SAST/DAST/SCA/容器扫描，且对 OSS 组件也跑 SAST；**SAST 结果必须人工复核**（有 false positive/negative，不能当全面视图）
- 最终二进制扫描由**供应方与消费方双侧**执行
- 大改/发布采用分批灰度，避免一次性全量推送受污染版本（OWASP A03:2025 防护建议）

## 7. R-3 制品完整性（可证伪规则，见 SKILL.md）

| 声称 | 必须附的证据 | 不适用时的写法 |
|---|---|---|
| 「交付物可信 / 依赖清单完整 / 供应链安全」 | ① 每个交付制品的 `sha256` 与 SBOM 原件（含 direct + transitive、生成器版本、生成时间、覆盖缺口）；② 签名或 provenance 验证的**命令原文 + 退出码 + 输出行**（builder identity、source-uri、`subject` digest 匹配）；③ 漏洞扫描输出含工具版本、数据源、时间戳与 per-CVE 抑制理由 | 纯源码/脚本/静态页、无构建产物、离线或用户禁止联网 → 只写「未做制品完整性验证」，**不得**写「供应链安全 / 无已知漏洞」 |

推论：**通过签名验证只能写「该声明来源与完整性已验证」，不得升级成「制品无漏洞、软件安全」**；扫描报 0 漏洞必须同时写扫描范围与未覆盖项，否则结论作废、降为「待确认」。

## 8. L0 零依赖降级路径（工具全缺也能走完）

```bash
sha256sum dist/* > /tmp/digest-before.txt        # 两次构建比对
git ls-files '*lock*' 'go.sum' 'requirements*.txt'
git diff --exit-code -- package-lock.json        # 装依赖后 lock 是否被改写
git grep -nE '(latest|\^~|\*|git\+|alpha|beta)' -- package.json requirements.txt
git grep -nEi '(curl|wget|http://|https://)' -- '*/postinstall*' 'setup.py' 2>/dev/null
git grep -nEi '(api[_-]?key|secret|BEGIN .*PRIVATE KEY)' -- . ':!*.lock'
grep -c '"name"' cdx.json                        # SBOM 组件数（仅作对照，不等于覆盖完整）
```

降级时报告固定写一行：「本轮仅静态核对依赖声明与制品 digest，**未做签名/provenance 验证与漏洞扫描**」，并标 `BLOCKED` 而非 Pass。

## 9. 报告字段与分工

用 `assets/supply-chain-evidence-template.md` 记录：制品清单与 digest、SBOM 元数据与缺口、验证命令与原始输出、provenance 期望值对照、扫描结果与抑制项、锁文件一致性、R-3 结论、不适用声明。

| 主题 | 去哪 |
|---|---|
| 运行时越权/注入/OWASP API Top 10 | `references/security-testing.md` |
| 依赖漏洞的**修复与缓解流程**、误报抑制 | `references/supply-chain-testing.md` §2 D-7/D-8（OWASP Vulnerable Dependency Management CS） |
| 发布六门禁 12 分 | `references/fullstack-integration.md` §6（Gate 3/4 吸收本手册证据） |
| 全局 Go/No-Go | `references/quality-gates.md` §3 |
| 工具与降级 | `references/tools.md` |
