# AI 时代测试手册（AI for QA 与 Testing for AI）

> 蒸馏自 Playwright 官方 Test Agents 文档（v1.56+ / 2026，planner·generator·healer）、`naodeng/awesome-qa-skills`（四层能力体系与 `AI for QA` ≠ `Testing for AI` 的区分、ai-generated-test-review）、CAICT/AIIA《面向软件工程的智能体技术和应用要求 第3部分：测试智能体》（2026）相关公开资料、OWASP LLM 应用风险实践。
> 一条主线：**先分清是在"用 AI 做测试"，还是"在测试 AI"**。两者的方法、判据、风险完全不同，混为一谈是 2026 年最常见的测试设计错误。

## 1. 四层能力模型（升级与路由的坐标）

| 层 | 定位 | 本技能对应资产 |
|---|---|---|
| L1 Core QA 基础能力 | 需求、策略、测试设计、执行、缺陷、报告 | `test-design.md`、`personas.md`、`quality-gates.md` |
| L2 Engineering QA 质量工程 | 左移、API/UI 自动化、契约、性能、回归、CI | `api-testing.md`、`performance-testing.md`、`fullstack-integration.md` |
| L3 Production Quality 生产质量 | 发布验证、生产验证、事故、Trace/指标 | `fullstack-integration.md` §6、`quality-gates.md` §3 |
| L4 AI Native QA 原生质量 | AI 功能、LLM、Prompt、RAG、Agent、AI 安全 | 本文件 |

**跨阶段串联靠工作流，不新增第五层**；升级时按 `Existing / Enhance / Merge / Match / New` 分类，优先增强已有手册而不是新建别名文件（防止目录膨胀）。

## 2. AI for QA：用 AI 提效（横向能力）

| 场景 | 工具 | 审查要点 |
|---|---|---|
| 探索式测试 / 陌生页面冒烟 | Playwright planner | 产出的 `specs/*.md` 必须由人/技能复核覆盖面 |
| 计划 → 用例 | Playwright generator | 选择器是否稳定、断言是否有业务含义 |
| 失败用例自愈 | Playwright healer | **见 §3 的"自愈陷阱"** |
| 测试数据生成 | faker / LLM | 是否覆盖边界与脏数据，而非只生成"正常值" |
| 根因分析 / 优先级判断 | LLM | 结论必须有证据，不得作为事实写入报告 |

```bash
npx playwright init-agents --loop=vscode   # 生成 .github/ 下的 agent 定义
# 约定目录：specs/（计划）、tests/（生成用例）、tests/seed.spec.ts（环境初始化）
# Playwright 升级后需重新 init-agents 以同步新工具与指令
```

三智能体可单独用，也可串成 loop：planner 探索应用产出 Markdown 计划 → generator 把计划转成 `.spec.ts` 并实时验证选择器 → healer 重放失败、定位等价元素、建议补丁并重跑。**恰好映射本技能阶段 2→3→4**。

> 降级：无 Playwright / 无 AI agent 时，本技能的五阶段流程完全不变（`tools.md` 的降级策略优先）。AI 是加速器，不是前置依赖。

## 3. AI 生成测试的审查纪律（必做）

**自愈陷阱**：healer 的目标是"让测试变绿"，它可以通过放宽断言、跳过用例、把期望改成实际值来达成。测试变绿 ≠ 功能变好。**任何 AI 修改过的断言都要人工 diff 复核**。

伪测试 / 弱断言特征（发现即打回）：

- 只断言 `is not None` / `isinstance` / `toBeTruthy()` / `assertTrue(...)`
- 只断言 mock 被调用，不断言业务结果与副作用
- 把实现逻辑复制一遍当"预期值"
- 用 `try/except: pass`、`.catch(() => {})` 吞掉错误
- 用 `skip` / `test.fixme` 让失败消失而不登记 bug
- 期望值直接引用当前输出（自证循环）

复核清单：

1. 断言的是**可观测业务结果**吗（响应、DB 状态、UI 文案），还是实现细节？
2. 把代码故意改坏，这条用例会红吗？（变异测试，见 `quality-gates.md` §5）
3. 失败时 healer 改的是 locator/wait，还是断言与预期？后者必须人工批准
4. 计划里的场景是否覆盖 P0 与至少 1 个无效等价类？
5. 生成用例是否自带 setup/teardown、不依赖执行顺序？

> **量化口径（v1.5）**：本节清单管「单条用例能不能要」；入库率 / 断言强度合格率 / 变异杀伤贡献 / 假通过率 / 审查成本管「这一批用例值不值」，见 `references/test-effectiveness-testing.md` §5B（E-15~E-18）。审查记录（提示词、diff、判定、批准人）须登记进 `scripts/evidence-audit.py` 的 manifest，否则 R-9 判证据链缺口；两处不重复抄写本清单。

## 4. Testing for AI：把 AI 系统当被测对象

**根本差异**：传统测试假设"同样输入 → 同样输出"，AI 系统天然非确定。因此**不能只靠单点期望值断言**，改用不变量 / 蜕变关系 / 评测集 / rubric。

| 维度 | 测试手法 | 通过判据 |
|---|---|---|
| 非确定性 | 同 prompt 跑 N 次（建议 ≥ 5），记录分布 | 关键**不变量**始终成立（格式合法、不泄漏系统提示、工具调用在白名单内） |
| 蜕变关系 | 输入顺序打乱、加无关上下文、改写同义句 | 语义等价变换下结论不应翻转 |
| 幻觉 / grounding | 构造 RAG 语料里**没有**的事实提问 | 拒答或标注不确定，不编造引用 |
| Prompt injection | 用户输入/检索文档里塞"忽略之前指令" | 不越权、不执行注入指令、不泄漏系统提示 |
| Agent 工具权限 | 诱导调用未授权工具、越权访问他人资源 | 工具白名单 + 每次调用鉴权；拒绝有审计日志 |
| Agent 状态与恢复 | 中途失败、工具超时、重复回调、长任务中断续跑 | 可恢复、幂等、无重复副作用 |
| 记忆 / 多轮 | 多轮后注入矛盾信息 | 能区分冲突、不把旧结论当事实 |
| 安全边界 | 输出含 PII/密钥/可执行代码；输出被下游直接执行 | 有过滤与人工确认环节 |
| 评测集 | 建带 rubric 的 golden set，按维度打分 | 有基线、有回归对比，不是"感觉变好了" |

**评估纪律**：
- 用 LLM 当裁判时要写清 rubric、给示例、多次采样；**不得让同一模型既当被测又当唯一裁判**（自偏好偏差）
- 保留人工抽检样本；评测集与训练集隔离（防泄漏）
- 报告写"在 N 条评测集上 X 维度得分 A→B"，不写"效果不错"
- 非确定性结论必须标置信/样本数；单次观测不构成结论

## 5. 与记忆树的接口（本技能的自我学习回路）

- 有效的 AI 辅助手法 → `memory/global-lessons.md`，标签 `[手法]`，附"哪类项目适用"
- AI 生成的伪测试案例 → 标签 `[工具]` 反例，防止下次重犯
- AI 系统被测项目的评测集路径与基线 → 项目 `.test-memory/tree.md` 的"命令速查/产物路径"
- 技能本体若要新增 AI 能力 → 按 `self-evolution.md` 的治理分类决定 Enhance 还是 New

## 6. 反模式

| ❌ | ✅ |
|---|---|
| 把"用 AI 写测试"和"测 AI 应用"混成一个模块 | 先判层：L2 横向 vs L4 被测对象 |
| healer 修完就认为 bug 没了 | diff 复核断言，功能缺陷照常登记 |
| 用单次 LLM 输出当断言基准 | 不变量 + 蜕变关系 + 评测集 + 样本数 |
| 用同一个 LLM 自评自测 | 独立 rubric + 人工抽检 + 隔离评测集 |
| 为赶时髦引入 AI 依赖才肯测 | AI 是可选加速，降级路径永远存在 |
| 把 skill/文件数量当质量结论 | 静态记录 ≠ 评测准备度 ≠ 运行时质量 ≠ 发布批准 |
