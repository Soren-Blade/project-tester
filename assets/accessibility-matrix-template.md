# 无障碍可达性矩阵 — <项目名>

- 日期：<YYYY-MM-DD> ｜ 技能版本：v<X> ｜ 关联规则：R-7
- 目标基线：<WCAG 2.2 AA / 其他，写明版本与级别>
- 适用：<有 UI 与交互；否则写「不适用：无图形交互界面，未做无障碍实测」>
- 执行环境：<OS / 浏览器 / 读屏器及版本 / 是否具备浏览器自动化>

## 版本口径核对

| 检查项 | 结论 |
|---|---|
| 验证基线为 WCAG 2.2（非 2.1），级别已声明 | <pass/fail> |
| 9 条新增成功标准已纳入检查清单 | <pass/fail/部分> |
| 4.1.1 Parsing 未被当作 2.2 失败项 | <pass/fail> |
| 2.5.8 按 24×24 CSS px 判定（未误用 44×44 AAA 门槛） | <pass/fail> |

## 自动化扫描与 incomplete 复核

| 工具/版本 | violations | incomplete | 逐条人工结论 |
|---|---|---|---|
| <axe-core / Lighthouse> | <n，附原文路径> | <规则 id 列表> | <每条：通过 / 缺陷 / 待确认> |

> `violations: 0` 单独不构成合规结论；`incomplete` 未复核即写 Pass = R-7 失败。

## 键盘路径逐步记录（每条 P0 流程一份）

| 步 | 焦点元素 | 焦点可见 | 被吸顶/吸底/banner 整体遮挡（2.4.11） | 备注 |
|---|---|---|---|---|
| 1 | <selector / 角色+名称> | <是/否> | <否/是 → BUG#> | <Tab/Enter/Esc> |
| 2 | | | | |

- 模态/抽屉焦点进入与 Esc 归还触发元素：<pass/fail/不适用>
- 200% 缩放 / 文本间距 / `prefers-reduced-motion`：<结论>
- 表单错误 `aria-live` 播报与焦点定位：<结论>

## 读屏组合逐项标注

| 组合（reader + browser + OS） | 检查项 | 结果（passed/failed/not checked/not present） | 证据 |
|---|---|---|---|
| <NVDA + Firefox + Windows> | 图标按钮可访问名 | <passed/...> | <记录路径> |
| | 动态结果播报 | <passed/...> | |
| | RTL 阅读顺序 | <passed/not present> | |

> `not checked` 不计入通过；未做任何读屏组时写明「未做读屏实测」，结论降级为「待确认」。

## WCAG 2.2 关键条款结论

| 条款 | 测试动作 | 结论 | 证据 |
|---|---|---|---|
| 2.4.11 Focus Not Obscured (Minimum) | 逐步焦点遮挡判定 | <pass/fail> | <上表> |
| 2.5.8 Target Size (Minimum) | 实测最小目标尺寸或命中例外 | <pass/fail，写尺寸> | <测量方式> |
| 3.3.8 Accessible Authentication (Minimum) | 认证各步是否有 cognitive function test / 有无 Mechanism 例外 | <pass/fail> | <可否粘贴/密码管理器> |
| 2.5.7 / 3.2.6 / 3.3.7 | 拖拽替代 / 帮助一致 / 不重填 | <pass/fail/not present> | |

## ARIA 结构回归（可选）

| 组件 | `toMatchAriaSnapshot` 断言范围 | 结果 | 快照变红时的人工判定 |
|---|---|---|---|
| <main / modal> | <组件粒度> | <pass/fail> | <退化 or 文案变化> |

## R-7 结论

- [ ] 已附 目标版本与级别 + violations/incomplete 原文与人工复核 + 完整键盘路径 + 至少一组读屏组合逐项标注 + 2.5.8/3.3.8 结论 → 可声称「符合 WCAG 2.2 AA / 支持读屏 / 可键盘操作」
- [ ] 不适用：纯 CLI / 无 UI 的库 / 批处理脚本 → 只写「不适用：无图形交互界面，未做无障碍实测」，**不得**写「无障碍合规」
- [ ] 仅自动化扫描 + 键盘路径、无读屏环境 → 写「未做读屏实测」，结论降级为「待确认」
- 不适用声明 / 例外：<___>

## 降级标注

<缺工具时：仅静态语义线索扫描 + 人工键盘走查，未做自动化扫描与读屏组合实测，结论降级为「待确认」并标 BLOCKED；静态 grep 出 aria-label ≠ 运行时可访问名正确>
