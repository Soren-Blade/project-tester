# project-tester — 通用项目深度测试技能

> 一个会**自我进化**的测试 Skill：解剖任意项目 → 按风险生成测试需求 → 双视角深测 → 记忆树接力 → 每日蒸馏升级。不绑定语言、框架或 agent。

![version](https://img.shields.io/badge/version-v1.0.0-1677ff)
![references](https://img.shields.io/badge/reference_files-14-2ea44f)
![assets](https://img.shields.io/badge/templates-5-e60023)
![updated](https://img.shields.io/badge/updated-2026-11-11-6e7781)

---

## 它解决什么问题

| 问题 | 本 Skill 的解法 |
|---|---|
| 换个项目又从零探索 | `.test-memory/tree.md` 记忆树接力：画像与命令速查直接复用，跳过解剖 |
| 用例靠拍脑袋、穷举不完 | `test-design.md` 九式设计 + 风险分优先级 + 六维矩阵 v2 |
| 只测"能用"，漏掉越权与注入 | `security-testing.md` 逐条对齐 OWASP API Top 10 2023；`api-testing.md` 认证授权矩阵与 BOLA 用例 |
| 错误契约各端点不一样 | RFC 9457 `application/problem+json` 校验点 + 状态码矩阵 |
| "挺快的"没有依据 | `performance-testing.md` 分位数口径、Little's Law、k6 阈值、轻量 shell 降级 |
| 前端状态没做全、无障碍过不了 | `frontend-testing.md` 五态矩阵、WCAG 2.2、Core Web Vitals、错误码映射 |
| 本地能跑 ≠ 能上线 | `fullstack-integration.md` 六门禁 12 分 Go/No-Go + 回滚预案 |
| 测试"绿了"其实没杀伤力 | `quality-gates.md` 缺陷八字段、flaky 治理、覆盖率 vs 变异得分 |
| AI 生成测试藏伪断言 / AI 系统不会测 | `ai-native-testing.md`：AI for QA 与 Testing for AI 分离、自愈陷阱、评测集与蜕变关系 |
| 工具装不齐就测不下去 | `tools.md` 全表带降级路径，零依赖也能走完五阶段 |
| 升级无记录、越更越乱 | `self-evolution.md` 十步门禁 + `CHANGELOG.md` + `scripts/selfcheck.py` 自检 |

---

## 文件结构（25 个文件）

```
project-tester/
├── SKILL.md                          # 主流程：五阶段 + 能力层路由 + 参考索引
├── README.md                         # 本文件
├── CHANGELOG.md                      # 每日升级记录（来源 / 改动 / 自检）
├── .gitignore
├── references/                       # 14 份手册（渐进披露，按需读）
│   ├── dissect.md                    # 解剖：栈指纹 / 入口 / 可运行性 / 测试设施 / 攻击面 / 路由
│   ├── tools.md                      # 工具总表 / 专项工具 / 可用性探测 / 降级纪律
│   ├── personas.md                   # 7 日常 + 8 刁钻画像 / 判 bug 标准 / 手册映射
│   ├── test-design.md                # 测试设计九式 / 六维矩阵 v2 / 风险分 / 覆盖与退出标准
│   ├── api-testing.md                # 端点十项必测 / RFC 9457 / 认证授权 / 幂等并发 / 契约与属性测试
│   ├── security-testing.md           # OWASP API Top 10 2023 逐项测试卡 / 输入向量 / 配置与依赖审查
│   ├── performance-testing.md        # 五种负载 / p95 口径 / k6 模板 / 性能预算 / 瓶颈定位
│   ├── frontend-testing.md           # 五态矩阵 / WCAG 2.2 / Core Web Vitals / 错误映射 / Playwright Agents
│   ├── fullstack-integration.md      # 测试金字塔 / 隔离与工厂 / 集成边界 / 六门禁 12 分
│   ├── quality-gates.md              # 缺陷八字段 / 严重度 / flaky / 变异测试 / CI 门禁 / 交付核对
│   ├── ai-native-testing.md          # 四层能力模型 / AI for QA vs Testing for AI / 评测集
│   ├── memory-tree.md                # 记忆树规范 / runs 格式 / 省 token 三律
│   ├── evolution.md                  # 运行时进化回路 / 四问 / 三层记忆
│   └── self-evolution.md             # 每日升级十步协议 / 权限裁决 / 版本与蒸馏门槛
├── assets/                           # 5 份模板
│   ├── tree-template.md              # 项目记忆树初始化
│   ├── report-template.md            # 测试报告（强制 PASS/FAIL 与 Go/No-Go）
│   ├── bug-report-template.md        # 缺陷报告八字段 + MRE
│   ├── test-plan-template.md         # 测试计划 / 六维矩阵
│   └── release-gate-template.md      # 六门禁 12 分发布验收
├── memory/
│   └── global-lessons.md             # 跨项目经验（开局即读，自我进化载体）
└── scripts/
    └── selfcheck.py                  # 升级自检：frontmatter / 断链 / 版本一致 / 占位 URL / 模板字段
```

## 知识资产速查

| 想做什么 | 读哪个 |
|---|---|
| 测一个 REST / GraphQL 服务 | `api-testing.md` + `security-testing.md` |
| 测一个网页 / 前端 | `frontend-testing.md` + `personas.md` |
| 测全栈能不能上线 | `fullstack-integration.md` §6 + `release-gate-template.md` |
| 做压力 / 性能验证 | `performance-testing.md` |
| 测 LLM / RAG / Agent 应用 | `ai-native-testing.md` |
| 不知道该测哪些点 | `test-design.md` + `test-plan-template.md` |
| 写缺陷报告 | `bug-report-template.md` + `quality-gates.md` §2 |
| 判断测试是否可信 | `quality-gates.md` §5 |
| 升级本技能 | `self-evolution.md` + `CHANGELOG.md` |

## 设计要点

- **通用性**：不绑定语言/框架/agent，只用通用能力（文件读写、shell、按需浏览器）；工具缺失自动降级，不中止
- **省 token**：被测项目根下 `.test-memory/tree.md`（<100 行）是接力地图，细节沉到 `runs/`；读一份树 = 跳过一次完整解剖
- **证据优先**：每个失败结论必须有 MRE + 实际输出；指标写清分子/分母；报告强制给出 `PASS/FAIL` 与 `Go/No-Go`
- **分层能力**：L1 Core → L2 Engineering → L3 Production → L4 AI Native，按项目形态路由，不一套用例打天下
- **自我进化**：项目教训 → `.test-memory/lessons.md`；通用教训 → `memory/global-lessons.md`；每日升级 → `CHANGELOG.md` + 版本号
- **权限裁决**：**测项目时不自治**（运行时只提 `[技能改进]` 提案），**升级技能时授权自治**（用户明确授权的每日任务，走十步门禁）

## 安装位置

- 源（改动只改这里）：`D:\My Skills\project-tester\`
- 全局安装（所有项目、所有支持 `.agents/skills` 约定的 agent 可用）：`C:\Users\摩羯座\.agents\skills\project-tester\`
- GitHub 仓库：`https://github.com/Soren-Blade/project-tester`

改完源后同步并校验：

```bash
cp -r "/d/My Skills/project-tester/." "$HOME/.agents/skills/project-tester/"
diff -r "/d/My Skills/project-tester" "$HOME/.agents/skills/project-tester" --exclude=.git --exclude=.workbuddy-ai
```

## 每日升级流程

```
① 读 automation memory + CHANGELOG → ② 联网查权威资料并记来源 → ③ 深度蒸馏成可执行规则
→ ④ 治理分类（Existing/Enhance/Merge/Match/New）→ ⑤ 只改本文件夹
→ ⑥ python scripts/selfcheck.py（FAIL=0 才继续）+ 回归检查
→ ⑦ 升版本 + 写 CHANGELOG → ⑧ 同步全局安装 + diff 校验
→ ⑨ git commit（`feat(vN): 每日升级 #M <主题>`）+ push → ⑩ 回写执行记忆
```

自检命令：

```bash
cd "D:/My Skills/project-tester" && python scripts/selfcheck.py
```

## 版本历史

| 版本 | 日期 | 主题 |
|---|---|---|
| v1.0.0 | 2026-11-11 | 每日升级 #1：分层能力 + 9 份专项手册 + 3 份模板 + 证据化门禁 + 自我进化协议 + 自检脚本（[详见 CHANGELOG](CHANGELOG.md)） |
| v0 | ~2026-10-30 | 基线：五阶段流程 + 5 份 references + 2 份模板 |

---

**许可**：自由使用与改造。蒸馏来源与参考链接见 `CHANGELOG.md` 与 `references/self-evolution.md`。
