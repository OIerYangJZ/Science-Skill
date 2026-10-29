---
name: cite-verify
description: 核验参考文献（各学科通用），分两层：一是元数据，逐条与 Crossref、DataCite、arXiv、Europe PMC（PubMed）记录比对作者、标题、年份、期刊、卷号、页码和 DOI，检查编造或查无此文的条目、预印本是否已正式发表、撤稿与勘误、引用键缺失或多余；二是引用是否支撑论断，检查正文中"某人证明了 X [n]"这类句子，被引文献是否真的这样说。输入可以是 .bib、RIS（Zotero / EndNote 导出）、Word / PDF / Markdown 稿件末尾任意引用格式的参考文献列表，或 AI、人工整理的文献调研清单。不用于寻找新文献（那是 novelty-audit 的事）。
argument-hint: "[refs.bib / refs.ris / 稿件.docx / 调研.md] [--tex main.tex] [--claims]"
---

# cite-verify：每条引用都真实存在、信息准确，并且支撑它所在的句子

## 这个 skill 针对的问题

AI 生成或整理的文献列表常有元数据错误，甚至编造文献（见 `FAILURE_MODES.md` 第 4 条）。作者本人的一份调研 md 里就核出 8 处错误：

- 卷号写错（Tan 应为 PRXQ **7**, 033058）；
- 作者写错：Becker 等人的第四作者应为 Rouzé；"Nation, Treinish 等"实际只有两位作者；
- 机构和平台整个写错：Caesura 等人被写成 Quantinuum 的离子阱工作，实际是 PsiQuantum 与 Boehringer Ingelheim 的光量子 FBQC 工作。

元数据对了也不代表引用对了：被引文献可能并没有证明正文所说的结论。

## 硬性规则

1. **不改用户的文献文件或稿件。** 产出写到 `refcheck/<YYYY-MM-DD>/`（git 仓库内则加入 `.git/info/exclude`）。修正建议写在 `corrected.bib`，用户确认后才替换。
2. **记录是证据，记忆不是。** 每个"正确"或"错误"的判断都要能对应到 Crossref、DataCite、arXiv 或 Europe PMC 的一条记录。凭记忆说"这篇应该是 2019 年的"不算数。
3. **查不到不等于编造**，但必须人工确认。书籍、学位论文、软件、会议摘要、政府报告、档案和古籍常常不在这些数据库里；人文社科的很多文献没有 DOI。结论只能是"已找到 / 未找到（检索了 A、B、C）"。
4. **论断支撑检查必须读原文**：至少读摘要，涉及具体结论时读相关章节。读不到全文，就标记为"无法核实"，不能猜。
5. 对话用中文；修改建议里的 bib 条目和论文文本保持英文。

## Phase 0：接收

- 输入可以是：
  - `.bib` 文件（可以多个）+ 正文 `.tex`（用于判断哪些被引用）；
  - `.ris` 文件（Zotero、EndNote、Mendeley 导出），用 `check`；
  - Word、PDF、Markdown、纯文本稿件，或者单独的参考文献列表，任意引用格式（APA、Vancouver、Nature、Chicago……），用 `check-list`。它会自动找到 References 一节并逐条拆分；
  - 或调研 md 文件。md 文件先转换：把每条文献整理成最小的 BibTeX（title、author、journal、volume、pages、year、doi，有什么写什么），存为 `refcheck/<date>/from_md.bib`，并保留 md 中的行号作为注释（`% md line 37`）。**转换时只抄 md 里写了的内容，不补全、不纠正**，纠正交给核验步骤。
- 是否做第二层（论断支撑）：用户要求、或者文章即将投稿时默认做，只检查重点句子（见 Phase 3）。

## Phase 1：元数据核验

```
python3 -I <skill-dir>/scripts/refcheck.py check refs.bib --tex main.tex --out refcheck/<date>
python3 -I <skill-dir>/scripts/refcheck.py check refs.ris --out refcheck/<date>
# Word / PDF / Markdown 稿件末尾的参考文献列表（任意引用格式）：
python3 -I <skill-dir>/scripts/refcheck.py check-list manuscript.docx --out refcheck/<date>
# 调研 md：
python3 -I <skill-dir>/scripts/refcheck.py check refcheck/<date>/from_md.bib --out refcheck/<date>
```

脚本的匹配顺序：
- 自由格式的条目（`check-list`）：整条文本交给 Crossref 书目检索，再依次查 arXiv 和 Europe PMC；找到记录后，检查年份、卷号、首页、作者、期刊是否出现在这条文本里；
- 有 DOI：查 Crossref，查不到再查 DataCite（LIPIcs、Zenodo 和 arXiv 的 DOI 注册在 DataCite）；
- 有 arXiv 号：查 arXiv，同时查它是否已有期刊版；
- 两者都没有：按标题和第一作者检索。标题匹配是严格的："Clifford+T" 和 "Clifford+V" 不算同一篇。

产出：
- `report.md`：问题按严重程度分级；
- `results.json`；
- `corrected.bib`：只是建议。

问题代码：

| 级别 | 代码 | 含义 |
|---|---|---|
| ERROR | NOT_FOUND / DOI_NOT_FOUND / EPRINT_NOT_FOUND | 找不到记录，可能是编造或写错 |
| ERROR | TITLE_MISMATCH / FIRST_AUTHOR / AUTHOR_NOT_IN_RECORD / AUTHOR_MISSING_FROM_BIB | 标题或作者与记录不符 |
| ERROR | VOLUME_MISMATCH / PAGES_MISMATCH / VENUE_MISMATCH（期刊） / YEAR_MISMATCH（差 2 年以上） | 出版信息不符 |
| ERROR | RETRACTED | 已撤稿 |
| WARN | PREPRINT_PUBLISHED | 引的是预印本，但已有期刊版 |
| WARN | HAS_ERRATUM / HAS_UPDATE | 有勘误或更新，要看是否影响所引内容 |
| WARN | YEAR_MISMATCH（差 1 年） | 通常是在线年份与印刷年份之差 |
| INFO | MISSING_DOI / PAGES_FORM / VENUE_MISMATCH（会议论文集） / BOOK_NOT_VERIFIED / JOURNAL_FIELDS_UNCHECKED | 提示，或需人工确认 |

## Phase 2：人工复核

- **每条 ERROR 都打开记录核对**（DOI 落地页、arXiv 页）。脚本可能匹配错（同名文章），也可能是 bib 写法不同（会议名、合著机构名）。复核后分类：真错 / 脚本误报。
- **NOT_FOUND**：用 WebSearch 按标题和作者再找一次；仍然找不到，就标记为"疑似编造，需作者确认来源"。
- **HAS_ERRATUM**：读勘误，看是否改动了正文引用的那个结果。
- **PREPRINT_PUBLISHED**：建议改引期刊版；要注意期刊版标题、结论是否和预印本不同。
- 对调研 md：除了元数据，还要核对 md 里写的**描述性信息**，如机构、平台、方法、"首次"之类的说法。这些不在元数据里，要读摘要或正文确认（Caesura 那条就错在这里）。

## Phase 3：论断支撑（第二层）

```
python3 -I <skill-dir>/scripts/refcheck.py contexts main.tex --out refcheck/<date>     # 或 manuscript.docx / .md / .pdf
```

`contexts.md` 按引用列出每处引用所在的句子，并把"把某个结果或性质归于被引文献"的句子标为 **claim**。LaTeX 稿件按 `\cite` 键分组；其他格式识别 `[n]` 数字引用（并对应到文末第 n 条）和 "(Author et al., 2015)" 作者-年份引用。Word 里的上标数字引用在转成文本后无法识别，需要人工检查。

优先检查：
1. 摘要、引言、结论里标为 claim 的句子；
2. 带具体数字、"首次"、"最优"、"已证明"、"不可能"的句子；
3. 被拿来当本文前提或对比基线的引用；
4. 只引了综述、却在说一个具体结论的句子。

按 `references/claim-support.md` 的流程逐句判断，结论分四类：支撑 / 部分支撑 / 不支撑 / 无法核实。引用较多时，按引用键分组派子代理并行检查；子代理返回后，主会话抽查至少 3 条。

## Phase 4：报告

写 `refcheck/<date>/summary.md`（中文），结论放最前：

1. **必须修改**：确认的 ERROR（编造、作者或卷号错误、撤稿）、不支撑的论断。每条写清现状、正确信息、依据（记录链接）和受影响的句子。
2. **建议修改**：已发表的预印本、勘误、缺 DOI、部分支撑的论断（建议的改写）。
3. **脚本误报**：列出，供以后改进脚本。
4. **无法核实**：列出原因。
5. 修正后的 bib 条目在 `corrected.bib`。只列需要改的条目，用户确认后再替换。

## 最终汇报（中文，简洁）

- 共检查多少条：确认错误几条、建议修改几条、无法核实几条。
- 最严重的 3 条，各一句话。
- 报告和 `corrected.bib` 的路径。
