# Science-Skill

[English](README.md) | **简体中文**

一组 Claude Code 技能，用于应对 AI 辅助科研中反复出现的失效模式。

AI 助手能帮忙写作、分析和核查，但它出错的方式是可以预见的：
- 让它润色稿件，它会层层加限定，直到贡献被埋没；让它写得有力一些，它又会过度宣称。
- 它会让正文数字与数据逐渐脱节。
- 它写的代码，渐渐不再是论文所描述的那套方法。
- 它会编出不存在的参考文献。
- 它倾向于检索支持"我们是新的"的文献，而不是可能推翻新颖性的文献。
- 它凭印象选择投稿期刊。
- 它写的模拟审稿意见，往往只是复述作者自己的笔记。
- 它汇报的进展，常常比证据所支持的更乐观。

本库的每个技能针对其中一种失效模式。技能是一份由 Claude Code 执行的书面流程，配有只用 Python 标准库实现的测量、追溯和核验脚本，让结论以证据为依据，而不取决于模型的语气。每个技能都是在相应问题于真实项目中出现之后编写的，见 [FAILURE_MODES.md](FAILURE_MODES.md)。

这些技能不限学科：支持 LaTeX、Word、Markdown、纯文本和 PDF 稿件，并区分理论、实验、观察性、计算、定性和综述等研究类型。

## 目录

- [技能一览](#技能一览)
- [设计原则](#设计原则)
- [安装](#安装)
- [使用方式](#使用方式)
- [技能详解](#技能详解)：[paper-polish](#paper-polish) · [number-audit](#number-audit) · [experiment-integrity](#experiment-integrity) · [cite-verify](#cite-verify) · [novelty-audit](#novelty-audit) · [venue-fit](#venue-fit) · [mock-review](#mock-review) · [dead-end-ledger](#dead-end-ledger)
- [命令行工具](#命令行工具)
- [支持的输入](#支持的输入)
- [数据来源与隐私](#数据来源与隐私)
- [局限](#局限)
- [仓库结构](#仓库结构) · [扩展](#扩展) · [许可证](#许可证)

## 技能一览

| 技能 | 针对的失效模式 | 主要产出 |
|---|---|---|
| [`paper-polish`](#paper-polish) | 防御性写作让编辑看不出新意，以及反方向的过度宣称 | 目标期刊范文调研；差距分析；claim ledger；重写的标题、摘要和引言；盲测编辑 |
| [`number-audit`](#number-audit) | 数字与数据、代码脱节；误读工具约定；统计量对不上 | 数字清单；一致性线索；来源追溯；类 statcheck 检查；审计报告；让数字始终与数据绑定的护栏 |
| [`experiment-integrity`](#experiment-integrity) | 代码没有实现正文所描述的设计；实验设计本身制造出结果 | 设计声明台账；代码静态扫描；带前后对比的确认问题；回归护栏 |
| [`cite-verify`](#cite-verify) | 参考文献元数据错误或编造；引用不支撑所在的句子 | 逐条与 Crossref、DataCite、arXiv、Europe PMC 核对；修正建议；论断支撑检查 |
| [`novelty-audit`](#novelty-audit) | 只检索支持新颖性的文献；投入之后才发现被抢先 | 用相邻领域术语重述的贡献；附日志的多源检索；新颖性判定；立项前查重与持续监测 |
| [`venue-fit`](#venue-fit) | 凭印象选投稿去向 | 相似工作发在哪里；期刊档案；附网址和核对日期的官方事实表；匹配度评估；投稿计划与日程 |
| [`mock-review`](#mock-review) | 模拟审稿不独立、不复核，稿件版本也不固定 | 隔离并锁定版本的审稿副本；独立报告；交叉讨论；核实；按优先级排序的联合报告 |
| [`dead-end-ledger`](#dead-end-ledger) | 讨好式的进展汇报，以及反复尝试已经失败的路线 | 研究账本：分级的结果、路线和障碍；新尝试前查重；格式检查 |

典型顺序：
- **立项前：** `novelty-audit --mode scout`；
- **研究中：** `dead-end-ledger`，分析代码稳定后用 `experiment-integrity`；
- **投稿前：** `novelty-audit` → `venue-fit` → `paper-polish` → `experiment-integrity` → `number-audit` → `cite-verify` → `mock-review`。

## 设计原则

1. **证据先于措辞。** 主张的强度由证据的强度决定：定理写成已证明；观察性研究中的关联不写成因果；单次运行的结果不写成一般结论。
2. **标准来自范文。** 怎样才算写得好，以目标期刊同类型的近期论文为准，不照搬任何一个学科的习惯。学科规范要求的不确定性表述（关联措辞、置信区间、局限性段落）予以保留；针对贡献本身的防御性限定予以删除。
3. **从不覆盖原件。** 所有产出写入带日期的工作目录；稿件在 git 仓库中时，该目录会被排除在版本控制之外。代码修改以补丁形式提出，重跑都在副本里进行。
4. **独立核查。** 负责审稿、分析范文、核验证明或结果的子代理不读作者的笔记；它们的结论要经主会话核实后才会采用。
5. **模拟的判断如实标注。** 凡是"未找到"，都同时说明检索了什么、在哪里检索、何时检索。关于期刊和工具的事实，只取自官方来源或源代码，并注明核对日期。
6. **表述问题与实质问题分开。** 改写解决不了的问题会如实指出。
7. **高成本步骤先征得同意。** 耗时长或要付费的重跑，先估算，经用户同意后才启动。
8. **语言。** 技能用用户的语言交流、写报告；稿件文本保持原有的语言。

## 安装

依赖：
- [Claude Code](https://claude.com/claude-code)。
- Python 3.10 或更高版本。脚本只使用标准库，已在 Python 3.14 上测试。
- 可选：`pdftotext`（poppler），用于读取 PDF 稿件。
- 可选：GitHub CLI `gh`，用于 `novelty-audit` 中的代码仓库检索。
- 能访问[数据来源与隐私](#数据来源与隐私)一节中列出的公开学术接口。

```bash
git clone https://github.com/OIerYangJZ/Science-Skill.git
cd Science-Skill
./install.sh            # 把 skills/* 软链接到 ~/.claude/skills/
./install.sh uninstall  # 只移除 install.sh 创建的链接
```

安装后新开一个 Claude Code 会话，即可用 `/<技能名>` 调用。软链接指向克隆下来的仓库，所以修改文件或 `git pull` 之后，下一个会话就会生效。

也可以把仓库作为插件在单次会话中加载：`claude --plugin-dir /path/to/Science-Skill`。此时技能名带命名空间，例如 `/science-skill:paper-polish`。两种方式任选其一，不要同时使用。

各脚本依赖共享的 `lib/` 目录，不要把单个技能目录单独复制到别处使用。

## 使用方式

- **调用：** 在项目目录（或其附近）启动的 Claude Code 会话中，输入 `/<技能名>` 加参数。参数是自由文本，可以写路径、目标期刊、模式等。当你的请求与某个技能的描述相符时（例如"帮我核对论文里的数字"），Claude Code 也可能自动调用它。
- **流程固定：** 技能按规定的阶段执行，并在**需要你做决定的地方停下来**，例如重写前请你确认新意的表述，或者长时间重跑前请你批准。
- **产出位置：** 写在稿件旁边带日期的工作目录里（`polish/`、`number_audit/`、`integrity/`、`refcheck/`、`novelty/`、`venue/`）；模拟审稿的产出放在仓库之外。在 git 仓库中，工作目录会加入 `.git/info/exclude`。
- **结束汇报：** 每个技能最后用你的语言给出简短汇报：结论、文件路径、需要你决定的事项，以及没能检查的部分。
- **脚本单独使用：** 脚本也可以脱离 Claude Code 单独运行，见[命令行工具](#命令行工具)。

## 技能详解

### paper-polish

**作用。** 让编辑一眼看到论文的新意和重要性，同时不过度宣称。它把稿件中编辑会读的部分（标题、摘要、引言、图 1 图注、cover letter）与目标期刊同类型的近期优秀论文对比，再基于 claim ledger 重写，ledger 把每条主张钉到对应的证据上。

**适用场景：** 即将投稿、被 desk reject 之后，或者怀疑 AI 润色把稿子写得过于保守。**不适用：** 语法层面的小修改。

**调用。**
```text
/paper-polish <稿件> "<目标期刊>" [--mode full|survey|rewrite|check]
/paper-polish manuscript.docx "The Lancet"
/paper-polish main.tex "Physical Review Letters" --mode survey
```

| 模式 | 执行内容 | 何时用 |
|---|---|---|
| `full`（默认） | 阶段 0–7 | 第一次润色这篇稿子 |
| `survey` | 阶段 0–4，只出差距报告 | 想先看诊断、暂不改写 |
| `rewrite` | 阶段 5–7，复用已有调研 | 调研已经做过 |
| `check` | 只做扫描和盲测 | 投稿前最后检查 |

**流程。**
1. **接收。** 没给目标期刊时会问你。有拒稿信和审稿意见请一并提供。
2. **测量编辑会读的部分。** 包括主结果首次出现的位置、限定语、因果措辞、缺少检验的 "significant"、符号密度、图注长度，同时建立 claim ledger。
3. **找范文。** 目标期刊范文 15–30 篇（池 A）、最近邻的前人工作 5–10 篇（池 B）、期刊官方的编辑标准（池 C）。每篇范文都经 DOI、arXiv ID 或 PMID 核验。
4. **拆解范文。** 子代理并行拆解，且不读你的稿件。
5. **写 `survey_report.md`。** 从研究问题、行文、叙事重心、摘要与引言结构四个方面对比，并把表述问题与需要新结果的问题分开。
6. **新意主线（novelty spine）。** 五句话：结果、缺口、重要性、头条数字、适用范围。**在这里停下来请你确认。**
7. **重写到新文件。** 每个数字都有出处记录，凡是改变了主张强度或范围的地方，都列出来请你确认。
8. **盲测编辑。** 一个子代理在不知道哪个是新稿的情况下读 A、B 两版，另一个子代理专找过度宣称；两份结论都由主会话核实。

**产出**（`polish/<日期>/`）：`scan_before.md`、`claim_ledger.md`、`exemplars/`、`exemplar_stats.md`、`survey_report.md`、`abstract_intro.tex`（或稿件原格式）、`polish_notes.md`、`blind/`。

**单独运行脚本。**
```bash
python3    skills/paper-polish/scripts/hedge_scan.py manuscript.docx
python3    skills/paper-polish/scripts/hedge_scan.py polish/*/exemplars/*.md --summary
python3 -I skills/paper-polish/scripts/exemplar_meta.py search '"T-count" AND "lower bound"' --venue "PRX Quantum" --from 2021
python3 -I skills/paper-polish/scripts/exemplar_meta.py fetch 10.7554/eLife.05224 PMID:25774601 2211.09133 --out exemplars --intro
```

**提示。**
- 写作标准来自范文统计，所以目标期刊选得是否准确很重要。
- 学科规范要求的不确定性表述（关联措辞、置信区间）会被有意保留。

### number-audit

**作用。** 审计稿件中的每个数字：
- 盘点全文数字；
- 标出同一符号取值不一致之处，以及手抄的数据宏值；
- 根据报告的检验统计量重算 p 值，核对 k/n 百分比和比值类指标的置信区间；
- 把关键数字追溯到生成它的数据或代码，并在副本中重算；
- 按源代码核对外部工具的约定；
- 检查正文已排除的参数是否仍在使用。

最后**安装护栏**：每次构建时从数据源重算关键数字。

**适用场景：** 分析定稿后、投稿前；每次重跑或更新数据之后；回复审稿意见之前。

**调用。**
```text
/number-audit <主稿> [<补充材料>] [--repo <数据与代码目录>] [--scope key|all]
/number-audit main.tex supplement.tex --repo .
/number-audit manuscript.docx --scope all
```
`key`（默认）只审计摘要、引言、结论、图注、表格和定理陈述中的数字；`all` 审计全部数字。

**流程。**
1. 盘点数字，列出一致性线索；
2. 统计一致性检查；
3. 追溯每个数字的来源；
4. 在副本中重算，**长时间或付费的运行会先问你**；
5. 按源代码审计工具约定；
6. 检查参数有效性；
7. 安装护栏；
8. 写报告。

**产出**（`number_audit/<日期>/`）：`numbers.md` / `.json`、`conflicts.md`、`stats.md`、`trace.md`、`ledger.md`（出处表）、`report.md`；护栏文件 `guards.json` 放在稿件旁边。

**单独运行脚本。**
```bash
N=skills/number-audit/scripts/number_audit.py
python3 $N extract main.tex supplement.tex --out number_audit/today      # 数字清单 + conflicts.md
python3 $N stats manuscript.docx --out number_audit/today                 # t/F/χ²/r/z 的 p 值、k/n 百分比、OR/RR/HR 置信区间
python3 $N trace number_audit/today/numbers.json --repo . --regions abstract,introduction,caption,table
python3 $N guard-init number_audit/today/numbers.json --out guards.json  # 然后填写 "source" 和 "locator"
python3 $N guard-check guards.json                                        # 有问题时退出码为 1
```

护栏的 locator 写法：
- JSON 路径：`metrics.err` 或 `runs[0].auc`；
- CSV 单元格：`row=model:B;col=auc` 或 `row=3;col=auc`；
- 对文本文件做正则匹配：`re:Final loss: ([0-9.]+)`；
- 常数：`const:0.5`。

百分数用 `"scale": 100`；用 `"decimals"` 和 `"thousands"` 控制显示格式；已更正、不得再出现的旧值写进 `"stale"`。

`guard-check` 给每一项的结果是以下之一：
- PASS；
- FAIL：附上正文中实际找到的值；
- ANCHOR_MISSING：句子被改写过，需要更新锚点；
- UNSOURCED；
- SOURCE_ERROR；
- STALE_PRESENT。

可以把它接进 Makefile、pre-commit 钩子或 CI。不要给运行时间这类每次都会变的数值设护栏。

### experiment-integrity

**作用。** 检查结果背后的代码和流程是否实现了正文所声称的设计，以及设计本身是否在制造结果。检查范围：
- 配对、随机种子、数据划分和样本量；
- 放在条件判断里的随机数抽取（会让不同参数下的场景错位）；
- 被当作结果报告的哨兵值或兜底值；
- 离散化带来的假象；
- 小样本掩盖的失败；
- 观测手段和测量顺序带来的效应；
- 数据泄漏和多重检验；
- 误导性的图；
- 项目自带自动检查的漏洞。

每个确认的问题，都通过重跑量化影响，并转成回归护栏。

**适用场景：** 自动检查全部通过后想再做一轮对抗性检查；结果看起来过大或过于干净；任何带代码、模拟、测量或回测的论文投稿前。

**调用。**
```text
/experiment-integrity <稿件或报告> <代码/数据目录> [--rounds 1|2]
/experiment-integrity paper.tex ./analysis --rounds 2
```

**流程。**
1. **设计声明台账。** 列出每条方法学声明，以及应当实现它的代码。
2. **静态扫描**（代码见下表）。
3. **核对声明与代码。** 读代码，并在副本里做插桩运行。
4. **按清单检查设计。** 包括随机性、兜底分支、尾部情况、数值计算、测量有效性、统计、图。
5. **评估影响。** 给出每个确认问题的前后数值。**长时间或付费重跑会先问你。**
6. **安装护栏。**
7. **写报告。**

`--rounds 2` 会在修复之后再攻击一轮，针对设计本身和新加的护栏。

**产出**（`integrity/<日期>/`）：`design_ledger.md`、`integrity_scan.md` / `.json`、`impact.md`、`report.md`，以及建议的补丁。

**单独运行扫描。**
```bash
python3 skills/experiment-integrity/scripts/integrity_scan.py ./analysis --out integrity/today
```

| 代码 | 模式 |
|---|---|
| S1 | 分母中的哨兵兜底（`x / max(d, 1e-12)`） |
| S2 | 在本应计算结果的函数里，边界分支返回常数（`if len(x) < 3: return 360`） |
| S3 | 吞掉异常（`except: pass`、`except: return 0`） |
| S4 | 用常数填补缺失值（`fillna(0)`、`nan_to_num`） |
| R1 | 条件里抽随机数（`if cond and rng.random() < p`） |
| R2 | 只在 `if` 的一个分支里抽随机数 |
| R3 | 每个文件的随机种子清单（用于比较各组） |
| P1 | 图中文字写死了数字 |
| L1 | 在划分训练/测试集之前就拟合了预处理 |
| G1 | 检查脚本用子串判断数字（"0.47" 能在 "10.47" 里找到） |
| G2 | shell 陷阱（`grep -c … \|\| echo 0`；路径匹配缺少结尾定界） |

Python 用语法树扫描，R、Julia、MATLAB 和 shell 用正则扫描。每条命中都只是线索，要结合上下文阅读。完整清单见 `skills/experiment-integrity/references/checklist.md`。

### cite-verify

**作用。** 分两层核验参考文献：
- **元数据：** 与 Crossref、DataCite、arXiv、Europe PMC 核对作者、标题、年份、期刊、卷号、页码和 DOI；识别编造或查无此文的条目、已正式发表的预印本、撤稿与勘误，以及未定义或未使用的引用键。
- **论断支撑：** 检查被引文献是否真的说了引用句所归于它的内容。

**适用场景：** 投稿前核对参考文献；核对 AI 或人工整理的文献清单。

**调用。**
```text
/cite-verify references.bib --tex main.tex       # BibTeX + 稿件（只查被引用的条目）
/cite-verify library.ris                         # Zotero / EndNote / Mendeley 导出
/cite-verify manuscript.docx                     # 任意引用格式的文末参考文献
/cite-verify survey.md                           # 文献调研清单（先转换为 BibTeX）
```

**流程。**
1. **元数据核验。** 有 DOI 的查 Crossref，查不到再查 DataCite；有 arXiv 号的查 arXiv；自由文本条目做书目检索，标题按严格规则匹配。
2. **人工复核每条错误。**
3. **论断支撑检查。** 针对"论断型"引用句，阅读原文判断。
4. **写报告。**

**产出**（`refcheck/<日期>/`）：`report.md`、`results.json`、`corrected.bib`（仅为建议）、`contexts.md`、`claims.md`、`summary.md`。

**单独运行脚本。**
```bash
R=skills/cite-verify/scripts/refcheck.py
python3 -I $R check references.bib --tex main.tex --out refcheck/today
python3 -I $R check library.ris --out refcheck/today
python3 -I $R check-list manuscript.docx --out refcheck/today
python3 -I $R contexts manuscript.docx --out refcheck/today
```

**提示。**
- "查不到"不等于编造：书籍、学位论文、软件和档案常常没有被收录。
- Word 中的上标引用识别不了。

### novelty-audit

**作用。** 以证伪为目标审计新颖性：
- 把每条贡献拆成结果、技术、模型三部分，再用相邻领域的术语重述。例如"计算血糖曲线下面积的新模型"，其实就是梯形法则。
- 在 OpenAlex、arXiv、Europe PMC、Zenodo 中做关键词、正向引用、反向引用和同期工作检索。
- 逐篇阅读候选文献，对每条贡献给出判定，并列出必须补引的文献。

**scout 模式**在你投入之前先查重，并维护一份监测清单，之后每次只报告新出现的条目。

**调用。**
```text
/novelty-audit main.tex                                       # 审计模式
/novelty-audit "对某结果做独立的可认证复现" --mode scout          # 立项前查重
```

**审计模式流程：**
1. 写贡献卡片；
2. 转写成相邻领域的说法；
3. 四个方向检索，全部记入日志；
4. 由一心想证明"这不是新的"的子代理阅读候选文献，主会话再逐项复核；
5. 写报告：每条贡献的判定、哪个领域会认为它是标准结果、必须补引的文献、建议的表述，以及需要什么新结果才能增强新颖性。

**scout 模式流程：**
1. 把计划中的结果写成卡片；
2. 检索最近一年的文献，包括代码和数据存档；
3. 对每个计划中的结果给出判定（已有人做过 / 他人正在做 / 仍是空白），并列出差异化选项；
4. 建立监测清单。是否启动或调整方向，由你决定。

**产出**（`novelty/<日期>/`）：`cards.md`、`hits.md`、`search_log.md`、`report.md`；scout 模式另有 `novelty/watch_queries.txt`、`watch_state.json`、`watch_log.md`。

**单独运行脚本。**
```bash
L=skills/novelty-audit/scripts/lit_graph.py
python3 -I $L search '"pass elimination" AND streaming' --log search_log.md
python3 -I $L search '"gut microbiome" AND "social network"' --db europepmc
python3 -I $L search '"single-cell" AND "foundation model"' --db zenodo --sort date
python3 -I $L citing 10.1006/jcss.1997.1545 --match '"lower bound" AND pass' --sort cited
python3 -I $L refs 2502.19526
python3 -I $L recent '"phase folding" AND "T-count"' --days 540
python3 -I $L watch --queries watch_queries.txt --state watch_state.json --days 90 --github
```

**检索提示。**
- 短语加引号，用 AND 连接；不加引号的多个词会自动用 AND 连接。
- `--db` 可选：`openalex`（全学科，默认）、`europepmc`（PubMed、PMC、bioRxiv、medRxiv）、`arxiv`、`zenodo`、`all`。

### venue-fit

**作用。** 依据核实过的事实选择投稿去向：
- 先找出相似工作都发表在哪里，给候选期刊建档案；
- 再为入围期刊逐项填写官方事实表，每条事实附网址、核对日期和原文摘录。事实包括范围、编辑标准、篇幅限制、评审方式、费用、预印本政策、AI 与数据政策、一稿多投与转投规则、截止日期、匿名要求、是否进入正式出版物；
- 最后评估匹配度，给出首选、备选、可并行的低成本选项和截止日程。

**适用场景：** 选择或更换目标期刊、被拒之后、确定截止日期之前。

**调用。**
```text
/venue-fit main.tex
/venue-fit manuscript.docx "Nature Communications, PLOS Biology, eLife" --budget 3000 --deadline 2027-01-31
```

**流程。**
1. 接收：体裁、约束条件、投稿历史、新颖性判定；
2. 根据相似工作的发表去向和你的候选，列出长名单；
3. 用期刊档案筛出 3–6 个入围期刊；
4. 填写官方事实表；
5. 附理由的匹配度评估；
6. 计划：首选、备选、可并行选项、日程，以及投稿前要做的事。

它不会代你投稿，也不会联系编辑。

**产出**（`venue/<日期>/`）：`factsheets.md`、`plan.md`，可选 `.ics` 日程文件。

**单独运行脚本。**
```bash
V=skills/venue-fit/scripts/venue_fit.py
python3 -I $V neighbors --query '"T-count" AND "lower bound"' --from 2019 --types journal,conference
python3 -I $V neighbors --seed 10.1103/PRXQuantum.4.020323 --from 2019
python3 -I $V profile "Quantum" "PRX Quantum" 2470-0029
python3 -I $V factsheet "PRX Quantum" "Quantum" --out venue/today/factsheets.md
```

**提示：** OpenAlex 的期刊档案只用于筛选，费用、日期和政策必须到官网确认。测试中，OpenAlex 记录的某期刊创刊年份比实际早了几十年。

### mock-review

**作用。** 组织一轮独立的模拟审稿：
- 按论文类型选 2–4 个审稿方向（例如证明、领域专家、统计与研究设计、复现性，以及 CONSORT、STROBE、PRISMA、ARRIVE、TRIPOD 等报告规范），可另加一位编辑；
- 每位审稿人只读隔离并以 SHA-256 锁定版本的副本，不看你的笔记，在自己的副本里复现数字；
- 交叉讨论，保留第一轮原文；
- 审稿人声称的每个错误，都由主会话核实；
- 最后给出按 P0/P1 排序、附修订顺序的联合报告。

**适用场景：** 投稿前自查、被拒后诊断、准备回复审稿意见。

**调用。**
```text
/mock-review ./paper "BMJ" --roles clinical,statistics,reporting
/mock-review . "Physical Review Letters" --roles proofs,domain,reproducibility --editor
```

**流程。**
1. 接收，包括抓取期刊的审稿标准；
2. 打包并锁定版本，检查清单中是否有像私人笔记的文件；
3. 选定审稿方向；
4. 并行独立审稿；
5. 交叉讨论；
6. 主会话核实；
7. 写联合报告；
8. 之后按审稿意见改稿前，先运行 `check-pin`，确认行号仍然有效。第二轮审稿要换新的子代理。

**产出**（放在仓库之外：`~/mock_review/<名称>-<日期>/`）：`pack/`、`work-<方向>/`、`reports/`、`verification.md`、`joint_report.md`、`PIN.json`、`MANIFEST.md`。

**单独运行脚本。**
```bash
P=skills/mock-review/scripts/review_pack.py
python3 $P pack --repo . --out ~/mock_review/paper-2026-10-29 --roles math,domain,stats --exclude "notes/*"
python3 $P check-pin ~/mock_review/paper-2026-10-29/PIN.json
```

在 git 仓库中只打包已跟踪的文件。未跟踪的笔记、`CLAUDE.md`、各类工作目录、`submission/` 和 `internal/` 默认都会排除。

### dead-end-ledger

**作用。** 为长期研究目标维护一份如实的研究账本。目标可以是一个开放问题、一个必须做成的实验、一个要提升的指标，或一个要检验的假设。账本记录：
- 带日期的状态行；
- 分级的结果；
- 附范围或样本的证据；
- 按可行性排序的开放目标；
- 已试路线，写明每条止于何处、什么条件下才值得重开；
- 障碍索引。

每次尝试新路线前，先查账本里有没有类似的失败路线。结果经独立复核后才能升级；进展汇报只说账本支持的内容。

**调用。**
```text
/dead-end-ledger research/LEDGER.md init      # 新建，或迁移已有的交接文档
/dead-end-ledger research/LEDGER.md before    # 尝试新想法前查重
/dead-end-ledger research/LEDGER.md record    # 一次工作结束后更新
/dead-end-ledger research/LEDGER.md report    # 根据账本汇报进展
```

| 状态词 | |
|---|---|
| 结果 | VERIFIED、UNVERIFIED、CONDITIONAL(H)、PRELIMINARY、NEGATIVE、RETRACTED |
| 路线 | FAILED、PARTIAL、SUPERSEDED、IN-PROGRESS、SUCCEEDED |

也接受 PROVED-REVIEWED、REPLICATED、HEURISTIC、NULL 等各领域的写法。

**单独运行脚本。**
```bash
G=skills/dead-end-ledger/scripts/ledger.py
python3 $G init research/LEDGER.md --goal "把界从 a 无条件地提升到 b"
python3 $G search research/LEDGER.md "use a sieve over the fibration" --notes research/notes
python3 $G lint research/LEDGER.md --notes research/notes
python3 $G status research/LEDGER.md
```

## 命令行工具

| 脚本 | 子命令与用途 |
|---|---|
| `paper-polish/scripts/hedge_scan.py` | 标题、摘要、引言、结论和图注的指标与被标出的措辞；`--summary` 汇总多个文件 |
| `paper-polish/scripts/exemplar_meta.py` | `venue`、`search`：查找范文；`fetch`：核验元数据并获取摘要和引言（arXiv 源码或 PMC XML；支持 DOI、arXiv ID、PMID） |
| `number-audit/scripts/number_audit.py` | `extract`、`stats`、`trace`、`guard-init`、`guard-check` |
| `experiment-integrity/scripts/integrity_scan.py` | 静态扫描哨兵值、随机性、数据泄漏、图和检查脚本中的陷阱 |
| `cite-verify/scripts/refcheck.py` | `check`（BibTeX / RIS）、`check-list`（自由文本列表）、`contexts` |
| `novelty-audit/scripts/lit_graph.py` | `resolve`、`search`、`citing`、`refs`、`recent`、`watch`，覆盖 OpenAlex、arXiv、Europe PMC 和 Zenodo |
| `venue-fit/scripts/venue_fit.py` | `neighbors`、`profile`、`factsheet` |
| `mock-review/scripts/review_pack.py` | `pack`、`check-pin` |
| `dead-end-ledger/scripts/ledger.py` | `init`、`search`、`lint`、`status` |

每个脚本都可以用 `--help` 查看说明。会读取下载内容的脚本，请用 `python3 -I` 运行。

## 支持的输入

| 输入 | 格式 |
|---|---|
| 稿件 | `.tex`（跟随 `\input` / `\include`）、`.docx`、`.md`、`.txt`、`.pdf`（借助 `pdftotext`） |
| 章节识别 | LaTeX 章节命令；IMRaD 标题；编号标题和全大写标题；无标题引言（Nature 风格）；结构化摘要 |
| 参考文献 | BibTeX；RIS；任意引用格式的文本列表；LaTeX `thebibliography` |
| 引用上下文 | `\cite` 键；数字引用 `[n]`；作者–年份引用 |
| 统计量 | 正文中的 APA 风格报告，如 `t(23) = 2.45, p = .02`、`F(2, 45) = 3.21, p < .05`、`χ2(1) = 3.84, p = .05`、`r(46) = .32, p = .03`、`z = 1.96, p = .05`；`k of n (x%)`；带 95% 置信区间的 OR / RR / HR |
| 代码（integrity 扫描） | Python（语法树分析）；R、Julia、MATLAB、shell（正则） |

## 数据来源与隐私

脚本只访问公开服务：[OpenAlex](https://openalex.org)、[Crossref](https://www.crossref.org)、[DataCite](https://datacite.org)、[arXiv](https://arxiv.org)、[Europe PMC](https://europepmc.org)（PubMed、PMC 全文、bioRxiv、medRxiv）和 [Zenodo](https://zenodo.org)；装有 GitHub CLI 时，`novelty-audit` 也可以调用它。不会发送任何个人信息。

两个可选的环境变量：
- `OPENALEX_API_KEY`：不设置时，同一 IP 下的所有用户共用一个很小的 OpenAlex 每日额度；大量使用时建议申请免费的 key。
- `SCIENCE_SKILL_MAILTO`：用于 Crossref 和 OpenAlex polite pool 的邮箱，脚本不会自动设置。

其他行为：
- arXiv 请求有频率限制。重试后 arXiv 仍返回 HTTP 429 时，脚本在本次运行中跳过 arXiv，并给出提示。
- arXiv 的 LaTeX 源码只在内存中解析，不会写到磁盘，也不会被执行。
- 逐字引文和计量只取自接口返回的文本或源文件，不使用经模型概括的网页内容。

## 局限

- 只支持英文稿件；措辞词表和句子切分都是针对英文设计的。
- Word 文档中的上标引用编号在转换为文本时会丢失，需要人工检查。
- 统计检查只识别正文中 APA 风格的行内报告，表格中的统计量需要人工检查。
- integrity 扫描对 Python 是精确分析，对其他语言是近似匹配。它只能发现可疑模式，不能直接判定 bug；设计层面的问题要靠"声明与代码核对"和检查清单来发现。
- 不检索 Web of Science、Scopus、PsycINFO 等订阅数据库，这类检索会交给用户完成。许多人文学科文献不在上述任何服务中。
- 模式扫描和来源追溯给出的是线索，不是结论；技能要求逐条结合上下文阅读。
- 模拟审稿和模拟编辑由同一类模型完成。它们检验的是贡献能否被读出、主张是否有依据，不能预测编辑的决定。

## 仓库结构

```text
skills/<name>/SKILL.md         Claude Code 执行的流程
skills/<name>/references/      细则、检查清单、模板和示例
skills/<name>/scripts/         可单独运行的脚本
lib/                           共享模块：文档读取、学术接口、BibTeX/RIS、统计
templates/SKILL_TEMPLATE.md    新技能模板
FAILURE_MODES.md               已观察到的失效模式和候选技能
install.sh                     以软链接方式安装技能
.claude-plugin/plugin.json     插件清单
```

## 扩展

1. 在 [FAILURE_MODES.md](FAILURE_MODES.md) 中登记失效模式和观察到的证据。新技能应当针对实际发生过的问题；该文件也列出了已观察到、但尚未编写的候选技能。
2. 把 [templates/SKILL_TEMPLATE.md](templates/SKILL_TEMPLATE.md) 复制为 `skills/<name>/SKILL.md`，用英文编写，按需添加 `references/` 和 `scripts/`。脚本通过 `os.path.realpath(__file__)` 定位 `lib/`。
3. 在两份 README 的[技能详解](#技能详解)中各加一节。
4. 运行 `./install.sh`，在新会话中测试。

欢迎补充其他学科的案例。目前的证据来自作者的项目，均已脱敏。

## 许可证

[MIT](LICENSE)。
