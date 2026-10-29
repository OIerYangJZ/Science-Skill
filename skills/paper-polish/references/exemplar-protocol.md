# 范文调研协议

## 1. 三个池

| 池 | 内容 | 数量 | 用途 |
|---|---|---|---|
| A 目标期刊范文 | 目标期刊（或同档期刊）近 5 年、同体裁、写得好的文章 | 15–30 篇，按体裁分 3–4 组；不得少于 8 篇 | 结构、写法和计量的参照 |
| B 最近邻工作 | 同一问题或同一技术、编辑会拿来比较的文章，不限期刊 | 5–10 篇 | 写"点名前人"的缺口；新颖性审计（标准技术、已有结果、应补引的文献） |
| C 编辑标准 | 目标期刊官方的 about / scope / criteria 页面 | 1–3 页 | 原文摘录，把 spine 映射到期刊标准上 |

**池 A 的选取标准**（满足越多越好）：
- 与本文体裁相同。理论证明与算法构造、随机对照试验与观察性研究、方法论文与应用论文，写法差别都很大，不要混在一组。
- 高引用（按年份归一化）、编辑推荐（Editors' Suggestion、Editor's Choice、Featured 等）、获奖论文，或者用户、合作者点名的。
- 与本文属于同一种文章类型（Article、Letter、Brief Report、Research Note 等）。期刊对不同类型有不同的篇幅和摘要要求。
- 主题相近，但不必相同。目的是学写法，不是学内容。
- 至少有 3 篇主题很近（与本文竞争同一批审稿人），以及 2–3 篇是目标期刊上公认写得特别清楚的文章。

**分组示例**：
- Case A（量子编译）：理论下界 7 篇、合成与 $T$-count 6 篇、随机编译与噪声感知 6 篇、容错编译 7 篇。
- 示意（流行病学）：同一结局的队列研究、孟德尔随机化研究、同期的随机对照试验各一组。
- 示意（机器学习）：同一任务的方法论文、基准或数据集论文、分析性论文各一组。

## 2. 检索

```
# 先确认期刊在 OpenAlex 里的 id
python3 -I <skill-dir>/scripts/exemplar_meta.py venue "PRX Quantum"

# 换 3–6 组关键词各查一次（方法词、问题词、对象词分开查）
python3 -I <skill-dir>/scripts/exemplar_meta.py search "T-count lower bound" --venue "PRX Quantum,Physical Review Letters" --from 2021 -n 25
python3 -I <skill-dir>/scripts/exemplar_meta.py search "circuit compilation streaming" --venue "Quantum" --sort relevance
```

- `search` 匹配的是标题和摘要，所有词都要出现。召回率不够时，减少关键词或换同义词。
- 结合 WebSearch（例如 `site:<期刊域名> <topic>`），以及期刊的编辑推荐列表。
- 各领域的补充数据库（OpenAlex 覆盖面最广，但下面这些在各自领域更全或更新）：

| 领域 | 数据库 / 来源 | 怎么用 |
|---|---|---|
| 生物医学、生命科学 | PubMed、Europe PMC（含 PMC 全文，以及 bioRxiv、medRxiv 等预印本） | `novelty-audit` 的 `lit_graph.py search --db europepmc`；fetch 可以直接用 PMID |
| 物理、数学、计算机 | arXiv；DBLP（计算机）；ACL Anthology（NLP）；OpenReview（ML 会议） | `--db arxiv`；会议论文用 WebSearch |
| 社会科学、经济学 | SSRN、RePEc / NBER working papers、OSF Preprints | WebSearch；正式版本用 OpenAlex 核验 |
| 化学、材料 | ChemRxiv | WebSearch |
| 人文学科 | JSTOR、PhilPapers、Project MUSE | WebSearch；很多文献没有 DOI，只能人工核对 |
- 用户已有的调研文件（例如 `*调研*.md`）可以直接作为候选，但里面的元数据一律重新核验。

## 3. 核验与下载

```
python3 -I <skill-dir>/scripts/exemplar_meta.py fetch <DOI/arXiv ...> --out polish/<date>/exemplars --intro
python3 -I <skill-dir>/scripts/exemplar_meta.py fetch --ids-file polish/<date>/exemplar_ids.txt --out polish/<date>/exemplars --intro
```

- 状态为 `NOT FOUND` 的不能用。出现 `WARNING arXiv title differs` 时要人工核对。
- 摘要来源依次取：Crossref（出版社存档的版本）、arXiv、PMC 或 Europe PMC、OpenAlex 重建版（公式会乱）。
- 引言来源依次取：
  1. arXiv 的 LaTeX 源码。只在内存中解析，不解压到磁盘，也不执行任何内容。PRL 风格的文章没有 Introduction 一节，脚本会取标题页之后、第一个 `\section` 之前的文字，并标注 "implicit"。
  2. PMC 开放获取全文 XML。适用于生物医学，以及 PLOS、eLife、BMC、Frontiers 等许多开放获取期刊。Nature 风格的文章引言没有标题，脚本会取正文第一节之前的段落，并标注。
  3. 两者都没有时，从出版社的开放获取页面获取，或者请用户提供 PDF。拿不到就只分析摘要，并在报告里说明（例如 Case A 中的 Tan PRXQ 7, 033058）。
- **不要用 WebFetch 的输出做逐字引用或计量**，它返回的是模型改写过的文本。
- 每篇文章的 `.md` 头部要补填 `pool` 和 `group` 两项。

## 4. 分析卡（每篇一张，填在 `.md` 的 "## Analysis card" 下）

逐字引文用英文原文，每条不超过 40 词，标明出自摘要还是引言第几段。其余各项用中文填写。

```markdown
## Analysis card

- 体裁 / 组：
- 研究问题（改写成一个问句）：
- 答案的形态：一个数 / 一个标度 / 是或否 / 一个构造 / 一个分类
- 一句话结论（slogan，逐字或近似）：
- 缺口句（逐字）：
  - 点名的前人：有（谁） / 无
- 操作意义：约束了谁，或改变了哪个可测量的量
- 头条数字：数值 + 基线（是否在同一句里）
- 摘要的句子功能序列：如 1 背景 → 2 缺口 → 3 结果 → 4 结果 → 5 方法 → 6 意义
  - 主结果首次出现在第几句；用文字还是公式
  - 范围限定几处；是附在结果句里，还是单独成句
  - 结尾落在：意义 / 方法 / 局限 / 展望
- 引言逐段功能：P1 …，P2 …，…
  - 主结果首次出现在第几段
  - 贡献的呈现方式：散文 / 编号清单（几条）
  - 前人工作的处理方式：点名对比 / 笼统概括 / 有对比表
  - 适用范围怎样写：位置、句数、正面还是负面措辞
  - 图 1 的作用：机制图 / 结果图 / 代价模型图；图注长度
- 标题形式：陈述 / 问句 / "Toward…" / 名词短语
- 值得借用的写法（1–2 条逐字引文 + 为什么好）：
- 与本文最相关的启发（一句话）：
```

## 5. 计量口径

所有数字都用 `hedge_scan.py` 计算，保证本文与范文按同一口径计数。不要在报告里混用人工计数和脚本计数。

| 指标 | 定义 |
|---|---|
| words | 去掉 LaTeX 命令后的词数，每个行内公式记 1 个词 |
| sentences | 按句末标点切分，常见缩写（Eq.、Fig.、et al.、i.e.）已做保护 |
| first result sentence | 第一个含结果动词（we prove/show/find/…）或含"any … that … must/obeys"句式的句子。**这是代理指标，分析卡要以通读结果为准** |
| inline math | 行内公式个数 |
| defensive / 100 words | D 类命中数 ÷ 词数 × 100 |
| scope qualifiers (S) | "under … assumption/model"、"within this family" 等短语的数量 |
| overclaim flags (O) | 需要对照 ledger 检查的强词数量，包括 O（强词）、OC（因果措辞）、OS（"significant"） |
| structured | 摘要是否为结构化格式（Background / Methods / Results / Conclusions 等标签） |

结构化摘要的段落数和句数，不能与非结构化摘要直接比较。分组统计时，把两种摘要分开。

**以下只是一个领域的例子，不是默认值。** Case A 中 26 篇物理期刊范文的分布如下；每次都要用当次的样本重新统计：
- 摘要全部是 1 段，109–300 词，5–12 句；
- 主结果多在第 2–4 句出现，最晚第 6 句；
- 行内公式通常 0–3 处；
- 26 篇中只有 2 篇在引言里用项目符号列贡献；
- 没有一篇在引言里写版本历史。

其他领域的分布可能很不一样。例如：
- 临床期刊多用结构化摘要，字数上限 250–300；
- Nature 系列的摘要是一段约 150–200 词的 summary paragraph，引言没有标题；
- 计算机会议论文常在引言末尾列出贡献。

所以每次都要以当次的范文统计为准。

## 6. 报告里的对比表模板

按四个维度各给一张表：研究问题、写作行文、叙事重心、摘要与引言。

```markdown
| 方面 | 范文（中位数 / 范围；举例并点名） | 本文（数值；行号） | 差距与改法 |
|---|---|---|---|
| 主结果首次出现 | 第 2–4 句，最晚第 6 句（Tan：第 1 句给结果、第 2 句给此前最好的结果） | 第 7 句，公式（`main.tex:97`） | 提到第 2–3 句，用文字表述 |
```

报告最后列出 2–4 个可以套用的模板，写法如下：
"**Tan 式**：第 1 句给结果；第 2 句给此前最好的结果；第 3–4 句给下界或开放问题；最后交代技术。适合：改进已知界的理论结果。"

## 7. 局限（必须写进报告）

- 样本只有成功发表的文章，结论只能是"发表的文章通常这样写"。
- 引言读的是 arXiv 版，可能与正式版不同。
- 范文的选取会影响结论。要写明是怎样选的，包括检索词和筛选标准。
