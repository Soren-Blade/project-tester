# 制品完整性证据表（R-3）

> 配合 `references/supply-chain-testing.md` 使用。**空白 = 未做**，不许填「通过」或 0 分；不适用写「N/A + 原因」。

```
项目/版本：___　commit：___　环境指纹：___　执行时间：___
```

## 1. 交付制品清单与 digest

| 制品路径 | 类型 | sha256 | 构建命令原文 | 两次构建 digest 一致？ |
|---|---|---|---|---|
| | binary/image/package | | | 是 / 否 / 未做（否 → 写明不可复现原因） |

## 2. 依赖与锁文件（D-1~D-10）

| 检查 | 命令原文 | 退出码 | 关键输出行 | 结论 |
|---|---|---|---|---|
| lockfile 入库 | | | | |
| 冻结安装 `npm ci` / `--frozen-lockfile` | | | | |
| 装依赖后 `git diff --exit-code -- <lock>` | | | | |
| 浮动版本 `latest`/`^`/`*`/git 分支 | | | | |
| `preinstall`/`postinstall`/`setup.py` 外联 | | | | |
| 直接 + 传递依赖 vs SBOM 对账 | | | | |
| 告警抑制（per-CVE + 理由 + 补丁测试） | | | | |

## 3. SBOM 元数据（B-1~B-10）

| 字段 | 值 |
|---|---|
| 原件路径 / 格式（CycloneDX / SPDX）+ schema 校验结果 | |
| 生成器与版本 / 生成时间 | |
| NTIA 七要素齐全？ | supplier / name / version / unique id / dependency relationship / author / timestamp |
| 直接 + 传递依赖覆盖数 / bundled / OS 包 | |
| **覆盖缺口声明**（incomplete / unknown） | |
| 与最终制品对账方式（非仅 manifest） | |
| 是否经**签名 attestation** 绑定制品 digest | |
| 每个 release 独立 + 与上一版 diff | |
| VEX 签发者 / 完整性 / 适用版本与部署条件 | |

## 4. 签名与 provenance 验证（命令原文 + 退出码 + 输出行）

```
$ ___
exit: ___
输出：PASSED: ___ / 或失败原文 ___
```

| 对照项 | 期望值 | 实际值 | 一致？ |
|---|---|---|---|
| builder identity / `builder.id` | | | |
| `source-uri`（不含 tag） / commit | | | |
| `predicateType` | `https://slsa.dev/provenance/v1` | | |
| `statement.subject` digest vs 制品 sha256 | | | |
| `externalParameters`（untrusted，须下游验证） | | | |
| SLSA Build Level 判级（L0/L1/L2/L3） | | | |
| tlog 条目 / 不可变引用 | | | |

## 5. 漏洞扫描与抑制

| 工具 + 版本 | 数据源 + 时间戳 | 扫描范围 | 结果 | per-CVE 抑制理由与补丁测试记录 |
|---|---|---|---|---|
| | | | | |

## 6. CI/CD 静态审查

- [ ] 构建在隔离 ephemeral 环境，无共享缓存污染
- [ ] pipeline / build script / config 入 VCS，protected branch + review
- [ ] 构建工具含版本与插件清单；私有制品库无直连公共仓库旁路
- [ ] 最小权限 / 职责分离 / MFA / 凭据轮换；密钥不入仓
- [ ] 认证与配置变更有集中式、可行动的日志
- [ ] CI 内 SAST/DAST/SCA/容器扫描，SAST 结果人工复核
- [ ] 最终二进制由供应方 + 消费方双侧扫描

## 7. R-3 结论

```
R-3：PASS / FAIL / BLOCKED
已验证声明：___（例：该制品的签名来源与完整性已验证）
明确未覆盖：___（例：未做漏洞扫描；未验证 v1.2 spec；未做可复现构建）
不适用声明：___（纯源码 / 无构建产物 / 离线 → 只写「未做制品完整性验证」）
```

> 禁止把「签名有效」升级为「制品无漏洞 / 软件安全」；扫描 0 漏洞必须同时写扫描范围与未覆盖项，否则结论作废、降为「待确认」。
> 分工：运行时越权 → `references/security-testing.md`；Go/No-Go → `references/quality-gates.md` §3；发布六门禁 → `references/fullstack-integration.md` §6。
