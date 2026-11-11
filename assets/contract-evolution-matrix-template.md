# API 契约演进兼容性矩阵 — <项目名>

- 日期：<YYYY-MM-DD> ｜ 技能版本：v1.3.0 ｜ 关联规则：R-5
- baseline 规范来源：<上一发布 tag 的 openapi.yaml / 当前规范> ｜ 修订版：<待发布版本>
- 适用：<有对外契约且多客户端/多版本在跑；否则写「未做契约演进验证」>

## 破坏性变更检测（oasdiff）

| 项 | 值 |
|---|---|
| 命令原文 | `oasdiff breaking <base> <revision> --fail-on=ERR` |
| 退出码 | <0=无 breaking / 非0=存在 breaking> |
| 关键输出行 | <粘贴 breaking 项原文> |
| baseline vs 修订版 | <明确两者来源，禁止对空文件 diff> |

## 消费者契约（Pact，若有消费者）

| 项 | 值 |
|---|---|
| 契约覆盖核心交互 | <列出消费者实际使用的字段/操作> |
| 提供方 verify 结果 | <pass/fail + 退出码> |
| `can-i-deploy` 闸门（目标环境） | <环境名 + 退出码 0/非0> |
| 契约文件归档 | <tag 对应 Pact/规范快照位置> |

## 容忍读取与版本对齐

| 检查 | 结果 |
|---|---|
| 老客户端对新增字段不报错（tolerant reader） | <pass/fail> |
| 路径版本 `/v1` 与文档一致 | <pass/fail> |
| 弃用字段有公告 + 过渡期 > 客户端更新周期 | <pass/fail/不适用> |
| SemVer 与变更性质对齐（breaking→MAJOR） | <pass/fail> |

## R-5 结论

- [ ] 已附 oasdiff 退出码 + 输出行，且 can-i-deploy 通过 → 可声称「向后兼容 / 可安全部署」
- [ ] 不适用：无对外契约的单体工具 → 只写「未做契约演进验证」，**不得**写「向后兼容」
- 不适用声明 / 例外：<___>

## 降级标注

<若工具缺失：仅做静态 diff + 历史审查，结论降级为「待确认」并标 BLOCKED>
