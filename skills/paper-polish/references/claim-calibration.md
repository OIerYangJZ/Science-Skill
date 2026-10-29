# Claim ledger 与主张强度校准

防御性写作和过冲是同一个问题的两面：措辞的强度与证据的强度不匹配。ledger 把每条主张钉到证据上，再由证据决定用什么动词、加什么限定。下面的规则适用于各学科；第 2 节按研究体裁给出证据等级。

## 1. Ledger 格式

保存为 `polish/<date>/claim_ledger.md`。范围是摘要、引言、结论和 cover letter 里的每一条主张：凡是"本文发现、证明、测量或主张了什么"的句子，都算一条。

| ID | 主张（原文，位置） | 证据类型 | 前提或条件 | 正文出处 | 当前强度 | 应有措辞 | 备注 |
|---|---|---|---|---|---|---|---|
| C1 | "Any compiler that … obeys …"（摘要第 5 句） | T1 | 网格输入；对每条合法流都正确 | Thm 1, `main.tex:962` | 恰当 | "we prove that any such compiler must …" | |
| C2 | "orders of magnitude more $T$ states"（摘要第 16 句） | C2 | 单一的、已说明的 QRE 模型；只用一个基准 | Sec. 8, `qre_results.csv` | 偏强（基线没点名） | "385–1,753× vs Qiskit opt3 … TKET avoids the gap" | 这个数不是由定理推出的 |
| C3 | "Social contact causes microbiome convergence"（摘要结论句） | O1 | 观察性研究，一个种群 | Table 2, Fig. 3 | 偏强（因果措辞） | "Social contact was associated with microbiome similarity, independent of diet" | 示意 |

"当前强度"取三个值之一：**偏弱**（防御）、**恰当**、**偏强**（过冲）。

## 2. 证据等级与对应措辞（按研究体裁）

所有体裁共用一条原则：**证据有多强，措辞就用多强，条件写在结论旁边，只写一次。**

### 理论 / 数学

| 等级 | 证据 | 措辞 | 限定 |
|---|---|---|---|
| T1 | 文中有完整证明的定理 | "we prove"、"X requires Y"、"any … must …"（一般现在时） | 不加情态词；条件写进主语或从句 |
| T2 | 依赖外部未证假设或猜想的证明 | "we prove … assuming H"、"Under H, …" | 假设紧挨着结论；摘要里不能省 |
| T3 | 构造或上界 | "we construct"、"… attains … within a constant factor" | 写明模型和参数范围 |
| T4 | 启发式论证或猜想 | "we conjecture"、"heuristically" | 给出支持它的证据 |

### 实验（实验室实验、随机对照试验）

| 等级 | 证据 | 措辞 | 限定 |
|---|---|---|---|
| X1 | 预注册的随机对照试验或有对照的实验，已重复 | "X reduced / increased Y by …"（可以用因果措辞） | 效应量 + 置信区间；样本和人群 |
| X2 | 单次的对照实验 | "in our experiments, X reduced Y …" | 条件、样本量；说明尚未重复 |
| X3 | 预实验、探索性分析、事后亚组分析 | "in an exploratory analysis …"、"pilot data indicate …" | 明确标注为探索性的；不进摘要头条 |

### 观察性研究（队列、病例对照、横断面、调查、生态学研究）

| 等级 | 证据 | 措辞 | 限定 |
|---|---|---|---|
| O1 | 关联分析，已调整混杂 | "X was associated with Y (OR …, 95% CI …)" | **不用** causes、leads to、effect of、drives、results in |
| O2 | 带因果识别策略（工具变量、断点回归、双重差分、孟德尔随机化等） | "consistent with a causal effect of X on Y under [assumption]" | 识别假设写在结论旁边 |
| O3 | 描述性分析 | "X was more common among …" | 不解释成机制 |

### 计算 / 模拟 / 机器学习

| 等级 | 证据 | 措辞 | 限定 |
|---|---|---|---|
| C1 | 穷举或经认证的计算，范围有限 | "exhaustive enumeration up to N shows" | 必须写出范围 |
| C2 | 基准测试或模拟 | "on [benchmarks / settings], X outperforms Y by …" | 数据集、种子数、方差，比较对象要调到最好 |
| C3 | 单个数据集或单次运行 | "on [dataset], we observe …" | 不外推到 "in general" |

### 定性研究

| 等级 | 证据 | 措辞 | 限定 |
|---|---|---|---|
| Q1 | 主题分析，达到饱和，多人编码 | "participants described …"、"we identified three themes …" | 说明情境、样本和可迁移性，不说"普遍" |

### 综述与元分析

| 等级 | 证据 | 措辞 | 限定 |
|---|---|---|---|
| R1 | 按 PRISMA 做的系统综述或元分析 | "pooled estimate …"、"the evidence indicates …" | 写明证据质量（如 GRADE）和异质性 |

### 解读与含义（所有体裁）

只有能从结果推出时才写 "this means / implies"；推不出时，写成 "a possible consequence would be"，或者不写。

## 3. 规则

1. **不升级。**
   - 数值、单次实验、观察性证据不能用 prove、establish、demonstrate that … causes。
   - 非有效的渐近结果，不能当成实际参数下的数字来写。
2. **不降级。** 已经证明的结论、预注册试验的主要终点，不能写成 "suggests"、"may"、"we attempt to show"。
3. **条件只写一次，紧挨着结论**，不要在后文以免责句的形式重复。
4. **下面这些词必须有对应的证据：**
   - law、universal、fundamental、optimal、tight：需要定理正好这样说；
   - first、for the first time、novel：需要池 B 或 novelty-audit 的检索支持，且全文最多出现一次；
   - orders of magnitude、dramatically、substantially：需要点名的、不是稻草人的比较对象；
   - significant(ly)：只能用在统计意义上，并且要报告检验；非统计意义请改用 substantial、marked 等；
   - causes、leads to、effect of、drives：需要实验设计或因果识别策略支持。
5. **主语与证据对象一致。**
   - 定理讲的是"模型 M 中的过程"，摘要就不能写成 "compilers"。
   - 研究对象是"某地区的成年人"，摘要就不能写成 "people"。
6. **头条数字只有一个**，比较对象写在同一句里。实证研究带上置信区间或其他不确定性。
7. **结果在实际条件下不成立或没有意义时**（例如非有效的界，或者统计显著但效应量很小），摘要和引言要说清楚在实际条件下什么成立。做不到的，就不要让它当头条。
8. **技术或方法来源**：用的是标准论证或已有方法时，在引言里直接承认，并说明新在哪里。
9. **领域规范要求的限定要保留。** 观察性研究的关联措辞、预实验的标注、置信区间、报告规范要求的局限性段落，都不是防御。要去掉的，是围绕"本文贡献"本身的免责和稀释（见 `defensive-patterns.md`）。

## 4. 范围句的写法

- **防御式**："[Result]. This does not hold for Z, and we make no claim about W. Note that our model assumes V."
- **校准式**：
  - 理论："For [class defined by V], we prove [result]." 然后在引言末尾写一个范围段，最后落到一个设计原则或开放问题上。
  - 实证："In [population / setting], X was associated with Y (…). [Design] does not establish causality; [the specific next study] would." 局限只写一次，落到下一步研究上。

## 5. 每轮重写后的核对清单

- [ ] 摘要里的每一句都能对应到 ledger 的某个 ID，或者是背景句。
- [ ] 每条依赖假设的主张（T2、O2），假设都写在它旁边。
- [ ] 没有一条数值、观察性或探索性主张用了 prove、establish 或因果动词。
- [ ] 每个 O、OC、OS 类词（`hedge_scan.py` 标出的）都有对应的证据。
- [ ] 每个数字都在 `polish_notes.md` 的出处表里，并且重新核对过；统计量已用 `number-audit stats` 检查过。
- [ ] 新稿没有加入原稿中不存在的结论。
