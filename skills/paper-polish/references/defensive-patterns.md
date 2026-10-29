# 防御性写作与过冲：类别、识别、改法

编号与 `scripts/hedge_scan.py` 一致。脚本只能抓到词汇层面的线索（D1、D2、D4、D5、D6、D8、D10、D12、D13、O、S）。结构层面的问题（D3、D7、D9、D11、D14）要靠通读来判断。

判断标准只有一条：**这句话是在帮编辑看清结果，还是在替作者挡批评？** 挡批评的句子不一定要删。通常的处理是把它挪到范围段，或者改写成一个正面的条件从句。

例句里标 "Case A" 的，取自 `case-studies.md` 中那篇量子编译稿件的原稿和重写稿；标"示意"的是为说明其他领域而构造的例子，不是真实文献。

**跨学科使用时，先分清两种"限定"：**
- **领域规范要求的不确定性表述，必须保留。** 例如：观察性研究写 "was associated with"；探索性分析标明是探索性的；报告置信区间和样本；医学论文按要求写局限性段落；定性研究说明可迁移性。这些是读者和审稿人期待看到的，不是防御。
- **围绕"本文贡献"本身的免责和稀释，才是要处理的对象。** 例如：不点名的缺口；"we attempt to shed light"；先让步再给结果；负面范围句满篇；把主要发现埋在方法描述后面。

判断标准不靠直觉，靠范文。同一类词（如 may）在目标期刊范文中的密度，就是这个领域的正常水平（`exemplar_stats.md`）。

---

## D1 负面范围句 / 免责声明

**样子：** "We do not claim…"、"This does not imply…"、"No claim depends on…"、"without promoting them to a theorem"、"is worth clarifying early because a figure is easier to overinterpret than a theorem"。

**伤害在哪：** 编辑先读到的是"你没有做什么"。这类句子往往一段出现好几处，会让人觉得作者对自己的结果没有信心。

**改法：**
- 把"不适用于 Z"改写成"对 X，我们证明 Y"，把范围放进结果句的条件从句里。
- 整篇文章只留一个范围段，用正面措辞，最后落到一个设计原则或开放问题上。
- 真正需要说的负面结论只说一次，并给出理由。负面结论本身可以是结果，例如 Bapat 等人坦率写出的局限。

**例（Case A）：**
- 原："One downstream experiment fixes the physical stakes without promoting them to a representation-independent theorem."
- 改："Merging matters for fault-tolerant cost: on a four-qubit benchmark, under one disclosed synthesis and surface-code model, the output of Qiskit's highest preset optimization level needs 385–1,753 times the logical $T$ states of a merged circuit, while TKET's PauliSimp … avoids the gap."
  - 改后的句子先说重要性，再给数字。基线点名为 Qiskit opt3，适用范围压缩成一个短语 "under one disclosed … model"，同时坦率承认 TKET 能避开这个差距。

- 原："The same figure also delineates the scope of the statement, which is worth clarifying early because a figure is easier to overinterpret than a theorem."
- 改：删去这句话，范围集中写在引言末尾的一段里，并以一个设计原则收尾："Read the other way, these limits are a design rule: randomize and lower late, and keep phase semantics until the coefficients have been merged."

## D2 让步开头

**样子：** 句子以 "Although / While / Despite / Admittedly / Of course" 开头，而且整句里没有结果。

**不算 D2 的情况：** 让步从句后面紧接着给出结果，也就是把代价放进从句、把结果放在主句。这是好的写法，例如 Koczor 等人（PRL 132, 130602）的 "While PAI increases that sampling cost, we prove that (a) the approach is optimal…"。脚本已经排除了这种情况。

**改法：** 先说结果，代价放进从句。如果局限需要单独成句，放到结果之后。

## D3 结果被埋没（结构问题）

**样子：**
- 摘要先花 5–6 句搭建模型，到第 7 句才给结果；
- 结果以一个含 8 个符号的不等式给出；
- 引言里，主结果要到贡献清单的第 2 条才出现。

**伤害在哪：** 编辑只读前几句。读到那里还没看到结果，就会判断为 "lack of clarity"。

**改法：**
- 摘要第 2–4 句给出结果，用文字说，例如 "must move about $m\log_2(1/\epsilon)$ bits"。
- 引言在前 4 段内给出主结果。确实需要公式的，给一个显示公式，紧接着用文字解释每个符号。

**例（Case A）：**
- 原（摘要第 4 句起）："We formalize this representation-dependent recoverability for a downstream compiler… The model charges two information channels… For an $r$-round modular accumulation…"，主结果在第 7 句才以公式出现。
- 改（第 2–3 句）："We ask what a compiler that sees only the resulting instruction stream must pay to merge the pieces back into one rotation per term. For a layer of $m$ rotations on an accuracy-$\epsilon$ grid, we prove that any such compiler … must move about $m\log_2(1/\epsilon)$ bits across the boundary before the last round…"

- 示意（社会科学）：
  - 原："Although our sample is limited to one country and our measures are self-reported, we attempt to provide some preliminary insights into …"
  - 改："Using a nationally representative panel of 12,000 adults, we find that … (β = …, 95% CI …)." 局限放到讨论里写一次，并指向下一步该做的研究。

## D4 稀释贡献

**样子：** "we attempt / try / aim / seek"、"take a first step toward"、"preliminary"、"modest contribution"、"shed light on"、"a complementary perspective"。

**伤害在哪：** 把一个定理说成了一次尝试。

**改法：** 已经证明的写 "we prove"，已经构造出来的写 "we construct"，已经测量过的写 "we measure"。只有工作确实是初步的才写 preliminary，而且要说清楚还缺什么。

**相关信号（不算错）：** formalize、study、explore、consider 这类框架动词。脚本会把它们和结果动词的比例报出来。框架动词比结果动词多，往往说明摘要在讲"做了什么"，而不是"发现了什么"。

## D5 情态限定

**样子：** may、might、could、possibly、potentially、perhaps、seems to、to some extent，以及叠用的 "may potentially"。

**注意：** 用在背景描述里通常没问题，例如 Koczor 写 "a real device may only be capable of $b$ bits"。有问题的是**用在自己的结论上**。

**改法：**
- 已经证明的去掉限定。
- 真正不确定的，写出不确定的来源："supported by exhaustive enumeration up to $T$-count 22"，或者 "conjectured; we verify it for $n\le 8$"。
- 任何情况下都不要叠用两个限定词。

## D6 模糊缺口

**样子：** "well known anecdotally"、"remains largely unexplored"、"has received little attention"、"to the best of our knowledge"。

**伤害在哪：** 编辑看不出你比谁强，也无从判断这个缺口是否真实存在。

**改法：** 点名一篇前人工作，说清它缺的是哪一点。可参考 Case A 中 26 篇物理期刊范文里的写法："2018 年以来无改进"、"Tran 等结果多出 $O(n^{1/2})$ 开销"、"只能处理两两对易的情形"。

**例（Case A）：**
- 示意（生物医学）：
  - 原："The role of social contact in microbiome transmission remains largely unexplored."
  - 改："Studies of captive and laboratory animals link co-housing to shared gut taxa [Refs], but whether everyday social contact shapes the microbiome in wild populations, where diet and kinship also vary, is unknown."
  - 改后的句子点名了已有证据，并说清了缺的到底是哪一块。
- 原（Case A）："This representation dependence is well known anecdotally."
- 改："These methods assume an optimizer that sees, or can rebuild, a global description of the layer. Much compilation instead runs downstream of the steps that dispersed it." 后面列出具体场景，并引用 Hashim 2025 作为这个问题真实存在的证据。

## D7 等权重贡献清单（结构问题）

**样子：** 6 条带项目符号的贡献，每条都是带公式的长段。

**伤害在哪：** 编辑找不到"那一个"新结果。26 篇范文里只有 2 篇用了项目符号。

**改法：** 用散文写 2–3 个结果，按重要性排序，第一个结果占最多篇幅。CS 类期刊（例如 ACM TQC）的惯例是在引言末尾列 2–3 条 inline contributions，可以照办。

## D8 版本史与内部标签

**样子：** "The prior version of this work…"、"legacy"、"historical"、W3/W7 这类内部实验编号。

**改法：** 版本说明放进 arXiv 的 Comments 栏，或者放到附录标题里，例如 "Exact-semantics results (from v1)"。内部标签全部删掉。

## D9 图注变成范围讨论（结构问题）

**样子：** 图 1 图注超过 120 词，提前引用 5 个尚未定义的结果，还在图注里讨论适用范围。

**改法：** 图注只描述图里画的内容，每个面板一两句。范围讨论放回正文。

## D10 无主被动

**样子：** "It is shown that…"、"It can be proven that…"。

**改法：** 写成 "We show…"，或者直接陈述结论："Any compiler that … must …"。

## D11 验证条件堆在摘要里（结构问题；脚本只统计 S 类数量）

**样子：** 摘要里有整句交代技术条件，例如 "within their stated equivalence and error conventions"、"Under the additional, explicitly disclosed frame-tracked presentation…"、"Both bounds include per-coordinate allowances and remain valid when…"。

**改法：** 摘要只保留编辑判断所必需的条件，一般 1–3 处，并且附在结果句里。其余放进正文的定理陈述。

## D12 填充语

**样子：** "It is worth noting that"、"Note that"、"Interestingly"。

**改法：** 直接删掉，把要说的内容直接写出来。

## D13 "不是 X，而是 Y"式框定

**样子：** "A fault-tolerant compiler is not only a translator"、"The point is not … but …"。

**伤害在哪：** 读者先读到的是你在反驳一个没人提出的误解。

**改法：** 直接陈述 Y。
- 原（Case A，引言第一句）："A fault-tolerant compiler is not only a translator; some of its standard stages also disperse structure…"
- 改："Two routine steps of a fault-tolerant software stack split rotation angles on purpose."

## D14 基线不点名（同时属于防御和过冲）

**样子：** "orders of magnitude more than the materialize-first pipeline"，而 materialize-first 是谁、是不是稻草人，都没有说。

**改法：** 基线点名为当前最好的方法或生产环境默认设置，并在同一句里给出倍数。如果有工具能避开这个差距，也要承认。

**例（Case A）：** materialize-first 实际上就是 Qiskit preset optimization level 3。原稿没有点名，反而让它看起来像稻草人；重写稿点了名，并承认 TKET PauliSimp 能避开这个差距。

---

# 过冲（O 类）

脚本把下列词标为 O，提示去对照 ledger 检查，不是说这些词不能用。

| 编号 | 样子 | 检查 |
|---|---|---|
| O1 | 条件结论写成无条件："This is the rate"，实际依赖一个未证明的假设 | 条件是否紧挨着结论 |
| O2 | 数值结果写成 "we establish / prove" | 证据等级是 E4/E5，动词应该用 find / observe |
| O3 | law / universal / fundamental / first / novel / optimal / tight | 是否有定理正好这样说；"first" 是否查过池 B |
| O4 | "orders of magnitude"、"dramatically" | 基线是否点名、是否当前最好；倍数是否是在比稻草人 |
| O5 | 摘要开头是非有效（non-effective）的渐近结果，而在实际参数下它是空的 | 摘要是否说明在实际参数下什么成立 |
| O6 | 范围外推：模型 M 里的结果被说成适用于 "compilers"；某一人群的结果被说成适用于 "people"；某个数据集上的结果被说成 "in general" | 摘要和标题中的主语是否等于证据的对象 |
| O7 | 相关写成因果：观察性研究用 causes、leads to、effect of、drives、results in（`hedge_scan` 中的 OC 类） | 设计是否支持因果推断（随机化，或写明识别策略和假设） |
| O8 | "significant" 不带统计检验，或者把统计显著说成实际意义重大（OS 类） | 有没有报告检验和效应量；非统计意义请改用 substantial 或 marked |
| O9 | 预实验、事后分析、亚组结果当头条；"trend toward significance" | 是否预先设定；是否标明是探索性的 |
| O10 | 机器学习：只比弱基线、没报方差、在测试集上调参后报告 | 比较对象是否调到最好；种子数和方差；数据划分 |

**例（Case B，模拟审稿指出的过冲，转述）：**
- 一个定理的前提已经包含了大部分结论，摘要却把它当成主要结果来宣传。
- 依赖未证假设的结论，在摘要里写得像已经成立。
- 标题里的名词（"law"）让人以为结果比实际证明的更强。
- 摘要以渐近结果开头，而这些结果在任何有实际意义的参数下都是空的；实用数字到摘要末尾才出现。

---

**示意（机器学习）：** "Our method achieves state-of-the-art results" → "On three standard benchmarks (A, B, C), our method improves accuracy over the strongest published baseline (D, retuned with the same budget) by 1.8–3.1 points (mean of 5 seeds; s.d. ≤ 0.4)."

# 什么时候限定是对的

- 猜想、数值外推、启发式论证：要限定，但要说清证据。写 "we conjecture X; exhaustive enumeration up to 22 supports it"，不写 "X may hold"。
- 依赖外部假设的定理：把假设写在结论旁边，例如 "Under Conjecture H, …"，只写这一次。
- 结果确实很弱，例如数值很小：直接说出来，再说明它约束的是谁。

  例（Case A）："Per term the price is modest, $\log_2 K_\epsilon\approx 9.6$ bits… What Eq. (1) fixes is where those bits must live." 弱点就这样转成了结果的操作意义。
- 技术来源是标准方法：直接承认，再说清楚新的部分在哪。

  例（Case A）："The proof is a standard multipass streaming argument […]. What is specific to compilation is the fooling family and the accounting." 主动承认，比等审稿人来指出更有利。
