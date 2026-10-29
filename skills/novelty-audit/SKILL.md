---
name: novelty-audit
description: 以证伪为目标审计论文的新颖性：把每条贡献拆成结果、技术、模型三部分，转写成相邻社区的说法（例如编译器下界 → 多遍流算法 / 通信复杂度 / advice complexity；血糖曲线下面积的"新模型" → 数值积分的梯形法则；空间插值 → 高斯过程回归），各学科通用，再从正向引用、反向引用、关键词和近期预印本四个方向找可能已有的结果、属于标准技术的证明和同期工作，逐篇阅读后给出每条贡献的新颖性判定、必须补引的文献和建议的表述。用于投稿前、写 "first / novel / to our knowledge" 之前、被审稿人质疑新颖性时，或用户问"这个结果是不是新的"时。不用于润色文字（paper-polish）或核对已有引用（cite-verify）。
argument-hint: "[稿件 .tex/.docx/.md/.pdf 或 一句话的结果描述] [--claims C1,C2]"
---

# novelty-audit：先试着证明"这不是新的"

## 这个 skill 针对的问题

AI 检索文献时，倾向于找支持"我们是新的"的证据，漏掉审稿人会拿来对比的工作（见 `FAILURE_MODES.md` 第 5 条）。

Case A：作者团队认为主定理是新的，审计后的结论是：

- 主定理是**标准的多遍流论证**：fooling set 加 Fano 不等式，再加 AMS 和 Guha–McGregor 的"p 遍等价于 2p−1 条消息"模拟。在理论计算机科学的审稿人看来，这是标准结果。
- commitment toll 在经典的 **advice complexity** 文献里有先例（Böckenhauer 等人的 string guessing；Boyar 等人的综述）。
- 7 篇必须补引的文献原稿都没有引，其中包括 2026 年的同期工作。

这些文献在量子编译社区的检索词下几乎找不到，必须先把问题翻译成相邻社区的语言。

跨学科的经典例子：Tai（Diabetes Care 17(2):152–154, 1994）提出了一个"确定葡萄糖耐量曲线下总面积的数学模型"，它其实就是数值积分里的梯形法则。用医学的说法去检索，找不到数学上的先例；换成数值分析的说法，立刻就能找到。

## 硬性规则

1. **目标是证伪。** 每条贡献都先假设"已经有人做过"，然后去找证据。找不到时，结论写成"在 [数据库、检索式、日期] 范围内未发现"，不写"这是新的"。
2. **读过才算。** 每个"已有 / 部分已有 / 标准技术"的判定，都必须基于读过的原文（至少摘要，涉及具体结果时读到对应的定理、表或节），并给出位置和原文摘录。凭记忆说"X 早就证明过"不算。
3. **每次检索都记日志**（`lit_graph.py --log`），最终报告附上完整的检索日志。
4. **只诊断，不改稿。** 产出写到 `novelty/<YYYY-MM-DD>/`（git 仓库内则加入 `.git/info/exclude`）。表述建议交给 paper-polish 或作者。
5. 被引文献的元数据要核验，可直接用 cite-verify 的 `refcheck.py`，或 paper-polish 的 `exemplar_meta.py fetch`。
6. 对话用中文；建议的论文表述用英文。

## Phase 0：接收

- 输入：稿件，或者用户对结果的描述。
- 列出贡献：从摘要、引言、结论中提取每条"we prove / we show / we find / we develop / first / new / novel"主张，编号为 C1、C2……一般 2–6 条。
- 读稿件已引用的最近工作和 Related Work，记下已经承认的前人工作，免得重复报告。

## Phase 1：拆解与转写

对每条贡献，按 `references/search-playbook.md` 的模板写一张卡片：

1. **结果**：去掉本领域术语，用更一般的语言重述，例如数学、统计、算法或机制层面的语言。
   - Case A："任何 p 遍扫描、跨切点状态为 S 的流算法，若计算一个单射的聚合，则 A + (2p−1)S ≥ m log K"。
   - 示意："用分段线性插值计算采样曲线下的面积"。
2. **技术或方法**：核心步骤，例如证明技巧（fooling set、Fano 不等式）、实验技术（CRISPR 筛选、单细胞测序）、统计或计量方法（混合效应模型、双重差分）、模型结构（注意力机制、图神经网络）。
3. **模型**：哪些假设让结果成立，哪些是本领域特有的建模。
4. **相邻社区与他们的叫法**：至少 3 个。同一个想法在不同学科常常有不同的名字，例如：
   - 流算法里的 pass elimination；
   - 数值分析里的梯形法则；
   - 地统计学里的 kriging，在机器学习里叫高斯过程回归；
   - 神经网络的反向传播，在自动微分里叫反向模式。

   更多见 `references/search-playbook.md`。
5. **检索式**：每个社区 2–4 条，用带引号的短语加 AND 提高精度。

## Phase 2：四个方向的检索

```
L="python3 -I <skill-dir>/scripts/lit_graph.py"
LOG=novelty/<date>/search_log.md
# A 关键词（每个社区的检索式都跑一遍）
$L search '"pass elimination" AND streaming' --log $LOG --out novelty/<date>/hits.md
# B 正向：谁引用了本文所依赖的经典文献（往往有人做过同样的事）
$L citing <经典文献 DOI> --match '"lower bound" AND pass' --sort cited --log $LOG --out novelty/<date>/hits.md
# C 反向：最近邻文章引用了什么
$L refs <最近邻 DOI 或 arXiv> --log $LOG --out novelty/<date>/hits.md
# D 同期工作（最近 18 个月；默认同时查 arXiv、OpenAlex、Europe PMC，后者包括 bioRxiv 和 medRxiv）
$L recent '"phase folding" AND "T-count"' --days 540 --log $LOG --out novelty/<date>/hits.md
# 生物医学 / 生命科学：PubMed、PMC 和预印本
$L search '"gut microbiome" AND "social network"' --db europepmc --log $LOG --out novelty/<date>/hits.md
```

再按领域补充（完整列表见 `references/search-playbook.md` 第 3 节）：
- WebSearch，以及 Google Scholar 风格的短语检索；
- 本领域的主要会议或期刊的近期目录；
- 预印本平台：arXiv、bioRxiv、medRxiv、SSRN、ChemRxiv、OSF；
- 注册库：ClinicalTrials.gov 查进行中的试验，PROSPERO 查系统综述方案，OSF Registries 查预注册研究；
- 专家问答社区：MathOverflow、Cross Validated 等。

arXiv 限流（429）时脚本会自动跳过 arXiv，并在日志里注明；之后再补查。

候选文献控制在每条贡献 10–30 篇。先按标题和摘要筛，再精读最相关的 3–8 篇。

## Phase 3：阅读与判定（可并行）

每条贡献派一个子代理，扮演"想证明这不是新结果的审稿人"。提示词见 `references/search-playbook.md`。子代理拿到：贡献卡片、候选列表、原稿的相关定理。子代理要读原文，对每篇候选给出关系：

| 关系 | 含义 |
|---|---|
| P 已有 | 同样或更强的结果已发表 |
| T 标准技术 | 证明用的是已知技术，结果本身可能是新的 |
| S 特例或推论 | 本文结果是已知结果的特例，或可以直接推出 |
| C 同期 | 近 18 个月内出现的相近工作 |
| R 相关 | 应当引用，用于定位，但不威胁新颖性 |
| I 无关 | 不相关 |

主会话复核每个 P、S 和 T 的判定：读原文对应位置，确认后才写入报告。

## Phase 4：报告

写 `novelty/<date>/report.md`（中文），结论放最前：

1. **每条贡献的判定**，四选一：
   - 新的（在检索范围内）；
   - 新在本领域的应用或建模，技术是标准的；
   - 部分已有（说明差异在哪）；
   - 已有。

   每条附上依据：文献、定理号、原文摘录。
2. **哪个社区会觉得它是标准的**。例如"流算法领域的审稿人会视为标准结果；程序语言和体系结构领域会觉得新"。这关系到投稿去向。
3. **必须补引 / 建议补引**的文献清单（元数据已核验），并说明各自对应哪条贡献。
4. **建议的表述**，例如 "The proof is a standard multipass streaming argument [AMS, Guha–McGregor]; what is specific to compilation is the fooling family and the accounting." 以及哪些 "first / novel" 措辞要删掉或限定。
5. **想要更强的新颖性，需要什么新结果**。例如 Case A 中的"依赖 r 的 T 数下界"；或者"在另一人群中重复"、"用随机化设计检验因果"。
6. **检索范围**：附上 `search_log.md`，写明没有覆盖的数据库和社区。

## 最终汇报（中文，简洁）

- 每条贡献一句话的判定。
- 必须补引的文献数量和最关键的 2–3 篇。
- 最大的新颖性风险，以及它是表述问题还是实质问题。
- 报告和检索日志的路径。
