# 测试数据管理（TDM）专项手册

> 蒸馏自 Thoughtworks《Test data management》、K2view《What is Test Data Management / Synthetic Data Generation》、DATPROF、IRI Test Data Virtualization、用户附加技能 `fullstack-dev`（其 `testing-strategy.md` 的 Test Factories / Anti-Patterns、`db-schema.md` 的 seeding/subsetting）与 `frontend-dev`（其 minimax 指南的 `--seed` 可复现），并交叉引用本技能 `references/privacy-compliance-testing.md`（R-6 生产 PII）、`references/data-integrity-testing.md`（迁移用类生产数据量）。
>
> 主张：**喂给测试的数据本身必须是可信、合规、可复现的**——否则测试结论建立在"假数据 / 泄漏的生产 PII / 每次跑都不一样的随机样本"之上，再多用例也只是沙上筑塔。

## 1. 测试数据生命周期

TDM 不是"造几条假数据"，而是覆盖从定义到退役的四步：

| 阶段 | 做什么 | 判据 |
|---|---|---|
| 定义 (Define) | 列出每个用例需要的**字段、类型、分布、边界值、关联约束**（外键、唯一性、格式） | 字段清单可追溯到测试矩阵，不靠临时拍脑袋 |
| 制备 (Provision) | 合成生成 / 脱敏生产抽取 / 子集拷贝，落到测试库或 fixtures | 制备过程可重复、可审计、不触碰生产写路径 |
| 维护 (Maintain) | 随 schema 演进刷新、随回归需要重建、控制体积 | 任一用例可独立 setup/teardown，不共享可变状态 |
| 退役 (Retire) | 测试结束清掉含 PII 的临时数据、撤销临时库 | 不留可反推生产用户的残留（见 §5） |

`fullstack-dev` 的 Anti-Patterns #9 直接点题：**"Test against production data → Generated test data only"**——连生产数据的**只读快照**都算生产数据，须先脱敏再进测试环境。

## 2. 合成数据生成（Synthetic Data Generation）

用**程序化生成**替代手写硬编码，是 `fullstack-dev` 反复强调的第一原则（Anti-Patterns #4：Hardcode test data → 用 factories；#9：所有数据走生成）。

- **工厂模式 + 随机库**：JS/TS 用 `@faker-js/faker`，Python 用 `Faker()` + `factory_boy`；每个工厂一个 `build(overrides)` 让你"默认随机、特定字段可覆盖"（如把 `role` 覆写成 `admin` 测权限）。
- **确定性种子（deterministic seed）**：生成必须用固定种子（如 `faker.seed(42)` / `--seed 42`），保证"同一用例每次重建出同一份数据"。这是可复现测试与跨语言变异基准的地基（见 `scripts/test-data-gen.py`）。
- **真实分布而非均匀随机**：姓名/邮箱/地址要像真用户（含 unicode、长串、emoji），金额/日期要覆盖边界；不要全填 `"test"` / `"aaa"`——那会漏掉编码、截断、排序类 bug。
- **前端测试数据的真实感**（`frontend-dev`）：生成的媒体/文案也要可复现——`--seed` 相同的提示词产出相同图/音，否则视觉回归无从比对（交叉引用 `cross-platform-testing.md` §6A 基线治理）。

```typescript
// 来自 fullstack-dev/testing-strategy.md：工厂而非裸 SQL
import { faker } from '@faker-js/faker';
export function buildUser(overrides: Partial<User> = {}) {
  return { email: faker.internet.email(), firstName: faker.person.firstName(), role: 'customer', ...overrides };
}
```

```python
# Python 等价：factory_boy + Faker（fullstack-dev/testing-strategy.md）
class UserFactory(factory.Factory):
    class Meta: model = User
    email = factory.LazyAttribute(lambda _: Faker().email())
    first_name = factory.LazyAttribute(lambda _: Faker().first_name())
    role = "customer"
```

降级：项目无 faker/factory_boy 时，用 `scripts/test-data-gen.py` 的零依赖生成器（标准库 `random` + 内置词表 + 种子），或至少手写带边界值的固定 fixtures，**禁止**直接连生产库抽数。

## 3. PII 脱敏 / 掩码（Masking / Anonymization）

当测试环境**必须**用接近生产形态的数据（如性能压测、复杂关联查询）时，先脱敏：

- **保留格式掩码（format-preserving）**：邮箱 `alice@example.com` → `a***@example.com`、手机 `13800001234` → `****1234`、姓名 `张三` → `张**`——保留结构便于走通格式校验，但主体被替换。
- **确定性 vs 可逆**：测试数据**不应**可逆回真实 PII；若业务需要同一条记录多次出现一致（如关联查询），用**确定性哈希掩码**（同一输入恒得同一假值），但哈希盐必须独立于生产、且不可反推。
- **替换 vs 删除**：整列无意义字段直接置空/置假优于保留原值；外键关联要随主表一起替换，否则会"假名 + 真地址"仍可被重识别。
- **诚实边界（关键）**：掩码是**启发式规则**，只替换你显式列出的字段，**不保证**覆盖了全部 PII，更**不保证**不可逆。声称"测试数据已脱敏"必须附：① 被掩码字段清单 ② 掩码后**仍残留**的疑似 PII 核查 ③ 人工复核结论。用了 `scripts/test-data-gen.py` 的 `mask` 子命令，**不**因此写成"数据已脱敏 / 无 PII 泄漏"。

## 4. 数据子集与制备（Subsetting / Test-Data-as-Code）

生产库几十 GB，测试只要能覆盖用例的最小相关切片：

- **子集 (Subsetting)**：按外键图抽取关联一致的子图（用户→订单→订单项），保证引用完整、不留悬空外键；体积按 CI 资源与目标覆盖定，而非整库拷贝。
- **测试数据即代码 (Test-Data-as-Code)**：fixtures / factories / seed 脚本入库受版本管理，与代码同评审、同回滚（`fullstack-dev/testing-strategy.md` 目录约定 `tests/fixtures/{factories,seeds}`）。
- **独立 setup/teardown**：`fullstack-dev` Anti-Patterns #3/#6——每个用例自管状态（事务回滚 / testcontainers / 工厂清理），**不共享可变数据**，否则顺序依赖会让"绿了"变成偶然。
- **迁移须在类生产数据量上验证**：用合成数据跑 `up → down → up` 并对照行数/NULL 数（交叉引用 `data-integrity-testing.md` §1；`fullstack-dev/db-schema.md` 要求迁移在 production data size 下 < 30s）。

## 5. 绝不用生产 PII / 生产数据跑测试

- 生产库直连做测试 = 高危（误改/误删/泄漏），且在合规上是事件。`fullstack-dev` 明确列为 Anti-Pattern #9。
- 即便"只读副本"，里面的 PII 仍受 GDPR / 个保法约束；进测试环境前必须脱敏（§3）。
- 测试结束必须退役含 PII 的临时数据（§1 退役阶段），与 `privacy-compliance-testing.md` 的"删除权 / 数据生命周期"同源。

## 6. R-11 可证伪规则：测试数据可信与合规

声称"测试数据已脱敏 / 合成数据无 PII 泄漏 / 数据可复现 / 子集引用完整 / 没用生产数据"时，必须附：

1. **数据来源声明**：合成生成（种子值、生成器版本）/ 脱敏生产抽取（抽取与掩码命令原文 + 退出码）/**明确写"未使用生产数据"**；声称"纯合成"须附生成命令与种子。
2. **脱敏证据**：被掩码字段清单 + 掩码后**残留核查**（扫描仍含明文邮箱/手机/姓名/证件号的疑似项）+ 人工复核结论；若无法核查则降为「待确认」。
3. **可复现证据**：同一 `--seed` 两次生成结果**逐字节一致**的校验值（或 `scripts/test-data-gen.py self-test` 同类断言）；声称"数据可复现"而无种子/无校验值 → 不得判 PASS。
4. **子集完整性**：外键图抽取后悬空外键数 = 0 的核查命令与输出；或明确写"未做子集，使用全量合成"。
5. **无生产数据证据**：测试环境连接串不含生产 host、临时库已退役的声明；或明确写"不适用：本项目无 PII/无生产环境"。

**不适用时的写法**：纯静态审查脚本、或无任何数据依赖的纯算法库 → 只写「不适用：无测试数据维度」，**不得**写"测试数据可信 / 数据已脱敏 / 数据可复现"。只有部分证据时写「测试数据存在 N 处缺口，R-11 降级为待确认」，**不得**把"用了生成器"冒充"数据已脱敏"，**不得**把"掩码了已知字段"冒充"无 PII 泄漏"。

> **口径诚实**：掩码工具能算 ≠ 数据已合规；`scripts/test-data-gen.py` 的 `self-test` 只证明脚本自身的确定性/掩码逻辑可用，**不证明**你的数据集无 PII 残留、不证明合规通过。

## 7. 工具与降级

| 需求 | 首选 | 降级（零依赖） |
|---|---|---|
| 合成生成 | `faker` / `factory_boy` / `Bogus`(C#) | `scripts/test-data-gen.py generate --seed`（标准库，确定性） |
| PII 掩码 | IRI FieldShield / DATPROF / 自写确定性哈希 | `scripts/test-data-gen.py mask --fields email,phone,name` |
| 数据子集 | 专有 TDM 平台 / 自写外键图抽取 | 手写 SQL 按主键抽样 + 外键回填，核对悬空外键 |
| 种子/制备即代码 | 项目 fixtures/factories/seeds 目录 | 入库的固定 JSON fixtures + 版本管理 |

`scripts/test-data-gen.py` 纪律（详见脚本头部）：**不联网**（只走标准库与本地词表）、**不代填**（不连任何真实库、不读生产数据）、**不冒充**（只做生成/掩码/校验，不裁决无泄漏或合规）、**不保证无泄漏**（掩码是启发式，保留格式替换主体）。

## 8. 路由表（与 `dissect.md` §8、`SKILL.md` 横向叠加项同一份清单）

| 形态 | 主用手册 | 必做动作 |
|---|---|---|
| 有测试数据库 / fixtures / 工厂 / 种子脚本，或声称"测试数据已脱敏 / 合成数据无泄漏 / 数据可复现"，或要验证"迁移在类生产数据量上跑通" | `references/test-data-management.md` + `assets/test-data-matrix-template.md` + `scripts/test-data-gen.py` | 数据来源声明、脱敏清单+残留核查、种子可复现校验、子集外键完整性、无生产数据声明（R-11）；纯静态算法库写「不适用：无测试数据维度」 |

> 本手册与 `privacy-compliance-testing.md`（R-6，生产 PII 生命周期）是**同一目标双切面**：R-6 管"生产系统怎么处理真实 PII"，R-11 管"喂给测试的数据本身是否可信合规"。两者不重叠、不互相替代。

## 9. 与既有手册的关系（避免重写）

- 不重复 `privacy-compliance-testing.md` 的生产 PII 字段分类/删除权细节，只在 §3/§5 引用。
- 不重复 `data-integrity-testing.md` 的迁移 up/down 与事务隔离，只在 §4 引用"迁移须类生产数据量"。
- 不重复 `supply-chain-testing.md` 的 SBOM/签名，TDM 只关心"测试数据这一环"。
- `scripts/test-data-gen.py` 与 v1.5 的 `evidence-audit.py`/`device-matrix.py` 同属"零依赖 + `--self-test` + 诚实边界"家族，受 `selfcheck.py` §7f 同一门禁约束。
