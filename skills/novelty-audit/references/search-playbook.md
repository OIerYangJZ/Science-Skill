# 新颖性检索手册

## 1. 贡献卡片模板（`novelty/<date>/cards.md`）

```markdown
## C1：<一句话原文主张>（摘要第 n 句 / Thm k）

- 结果（去术语重述）：
- 技术（证明核心步骤）：
- 模型假设（哪些是本领域特有的）：
- 最可能已经有人做过的部分：
- 相邻社区及其叫法：
  - 社区 1：<关键词>
  - 社区 2：…
  - 社区 3：…
- 检索式：
  - '"phrase one" AND "phrase two"'
  - …
- 种子文献（用于 citing / refs）：<本文依赖的经典文献、最近邻文献>
```

## 2. 转写示例（Case A 回溯）

| 本领域说法 | 相邻社区 | 那边的叫法 | 能找到的先例 |
|---|---|---|---|
| 下游编译器跨切点的 restart 状态下界 | 流算法 / 通信复杂度 | multi-pass streaming lower bound; fooling set; "pass elimination" | Alon–Matias–Szegedy；Guha–McGregor, ICALP 2008 |
| 已执行的前缀必须指明作用对象，代价是 log₂C(m,k) | 在线算法 | advice complexity; "string guessing" | Böckenhauer 等, TCS 554 (2014)；Boyar 等, ACM Comput. Surv. (2017) |
| 已提交输出 + 跨切点状态 | 流式 I/O 复杂度 | "input/output streaming"; reversal; sorting | François–Jain–Magniez, arXiv:1309.0647 |
| 合并对易旋转、phase folding | 程序分析 / PL | relational analysis; "phase folding"; abstract interpretation | Amy–Lunderville, POPL 2025；Albarghouthi, arXiv:2605.13929（同期） |
| 局部窗口优化器的能力边界 | PL / 编译器 | "local optimization" quantum circuits | Arora 等, arXiv:2502.19526 |

**跨学科的转写示例**（后三行是广为人知的"同一个想法、不同的名字"）：

| 一个领域的说法 | 另一个领域的说法 | 说明 |
|---|---|---|
| "确定葡萄糖耐量曲线下总面积的数学模型"（Tai, Diabetes Care 17(2):152–154, 1994） | 数值积分的梯形法则 | 医学期刊发表的"新模型"，其实是数值分析的教科书内容 |
| kriging（地统计学） | 高斯过程回归（机器学习） | 同一类方法，两个社区各有一套文献 |
| 反向传播（神经网络） | 自动微分的反向模式 | 检索要覆盖两套术语 |
| 双重差分（计量经济学） | 有对照的中断时间序列（流行病学、公共卫生） | 设计思路相近，文献分别发表在两个领域 |

经验：
- 只用本领域的词（"quantum compiler state lower bound"），这些文献一篇都检索不到。
- 回溯测试中，`search '"pass elimination" AND streaming'` 第一条就是 Guha–McGregor；`recent '"phase folding" AND "T-count"'` 能找到 Albarghouthi 2026 和 van de Wetering 等人的 Quantum 2025。

## 3. 各领域的检索来源

| 领域 | 文献数据库 | 预印本 / 同期工作 | 其他 |
|---|---|---|---|
| 通用 | OpenAlex（`lit_graph.py` 默认）、Google Scholar（WebSearch） | — | — |
| 生物医学、生命科学 | PubMed、Europe PMC（`--db europepmc`） | bioRxiv、medRxiv（在 Europe PMC 中可检索） | ClinicalTrials.gov、PROSPERO、Cochrane Library |
| 物理、数学、计算机 | arXiv（`--db arxiv`）、DBLP、zbMATH、MathSciNet | arXiv | 会议目录（STOC、NeurIPS、ACL 等）、OpenReview、MathOverflow |
| 社会科学、经济学 | OpenAlex、RePEc / IDEAS、JSTOR | SSRN、NBER、OSF Preprints | AEA RCT Registry、OSF Registries |
| 心理学 | PsycINFO（通过机构）、OpenAlex | PsyArXiv | OSF Registries（预注册） |
| 化学、材料 | OpenAlex、CAS（通过机构） | ChemRxiv | 专利数据库（Google Patents） |
| 工程 | IEEE Xplore、OpenAlex | arXiv（eess） | 专利、标准文档 |
| 人文学科 | JSTOR、PhilPapers、Project MUSE | — | 图书、档案；很多没有 DOI，需人工核对 |

要通过机构才能访问的数据库，交给用户检索，或者用 WebSearch 找公开的摘要页面。检索日志里要写明哪些数据库没有覆盖。

## 4. 检索式写法

- OpenAlex 全文检索：用引号括短语，用 AND 连接，例如 `'"phase folding" AND "T-count"'`。不加引号的多词查询会很宽泛（可能返回上万条无关结果）。
- 每条贡献至少：3 个社区 × 2 条检索式，外加 2 个种子文献的 citing（按引用数排序和按时间排序各跑一次）。
- `citing` 结合 `--match`：在经典文献的大量施引文献中，找"也做了同类下界"的那几篇。
- `recent` 默认回溯 540 天，用来找同期工作。还要检查 arXiv 的相关分类，例如 quant-ph、cs.DS、cs.CC、cs.PL。
- 数学类结果，加查 MathOverflow 和相关专家的主页、讲义、未正式发表的信件或笔记。专家指出的联系往往用关键词查不到；必要时建议用户直接请教领域专家。

## 5. 子代理提示词（每条贡献一个）

```
You are a referee who suspects that contribution C below is not new. Your job
is to find the strongest evidence that it is already known, follows from known
results, or uses a standard technique without acknowledging it.

Contribution card:
<card>

The manuscript's statement and proof sketch:
<theorem + proof outline, or file:line ranges to read>

Candidate prior work (verified metadata; read them, do not rely on memory):
<list with DOI / arXiv>

For each candidate that matters, give: relation (P already known / T standard
technique / S special case or corollary / C concurrent / R related / I
irrelevant), the exact location in the source (theorem or section), a quote
of at most 40 words, and one sentence on how it bears on C. You may search for
further candidates (OpenAlex, arXiv, web) and must list every query you ran.
End with a verdict for C: new (within the searched scope) / new application,
standard technique / partly known / known. Answer in Chinese, quotes in English.
```

## 6. 判定写法示例

- **新的应用，技术标准：**"在量子编译中给出跨切点状态下界（新）；证明是标准的多遍流归约（AMS 1999；Guha–McGregor 2008）。建议写成：The proof is a standard multipass streaming argument; what is specific to compilation is the fooling family and the accounting."
- **部分已有：**"commitment toll 是 string guessing 下界（Böckenhauer 等 2014, Thm 3）在'已执行前缀须指明目标'这一建模下的实例。建议定位为把 advice complexity 引入量子编译，而不是新的下界技术。"
- **在检索范围内未发现：**"在 OpenAlex（检索式见日志第 3–9 行）、arXiv（quant-ph、cs.DS，近 18 个月）以及 QIP 2024–2026 的论文列表中未发现同类结果。'to our knowledge' 可以保留一次。"
