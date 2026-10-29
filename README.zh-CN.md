# Science-Skill

[English](README.md) | **简体中文**

一组 Claude Code 技能，用于应对 AI 辅助科研中反复出现的失效模式。

AI 助手能帮忙写作和核查，但它们出错的方式是可以预见的：
- 让它润色稿件，它会层层加限定，直到贡献被埋没；让它写得有力一些，它又会过度宣称。
- 它会让正文数字与数据逐渐脱节。
- 它会编出不存在的参考文献。
- 它倾向于检索支持"我们是新的"的文献，而不是可能推翻新颖性的文献。
- 它写的模拟审稿意见，往往只是复述作者自己的笔记。
- 它汇报的进展，常常比证据所支持的更乐观。

本库的每个技能针对其中一种失效模式。技能是一份由 Claude Code 执行的书面流程，配有只用 Python 标准库实现的测量、追溯和核验脚本，让结论以证据为依据，而不取决于模型的语气。每个技能都是在相应问题于真实项目中出现之后编写的，见 [FAILURE_MODES.md](FAILURE_MODES.md)。

这些技能不限学科：支持 LaTeX、Word、Markdown、纯文本和 PDF 稿件，并区分理论、实验、观察性、计算、定性和综述等研究类型。

## 技能列表

| 技能 | 针对的失效模式 | 主要产出 |
|---|---|---|
| [`paper-polish`](skills/paper-polish/SKILL.md) | 防御性写作让编辑看不出新意，以及反方向的过度宣称 | 目标期刊范文调研；差距分析；claim ledger；重写的标题、摘要和引言；盲测编辑 |
| [`number-audit`](skills/number-audit/SKILL.md) | 数字与数据、代码脱节；误读工具约定；统计量对不上 | 数字清单；一致性线索；关键数字的来源追溯；类 statcheck 的 p 值、百分比和置信区间检查；审计报告 |
| [`cite-verify`](skills/cite-verify/SKILL.md) | 参考文献元数据错误或编造；引用并不支撑所在的句子 | 逐条与 Crossref、DataCite、arXiv、Europe PMC 核对；建议的修正条目；用于论断核查的引用上下文 |
| [`novelty-audit`](skills/novelty-audit/SKILL.md) | 只检索支持新颖性的文献 | 用相邻领域的术语重述每条贡献；关键词、正向引用、反向引用和同期工作检索；每条贡献的新颖性判定，附检索日志 |
| [`mock-review`](skills/mock-review/SKILL.md) | 模拟审稿不独立、不复核，稿件版本也不固定 | 隔离并锁定版本的审稿副本；独立的审稿报告；交叉讨论；主会话核实；按优先级排序的联合报告 |
| [`dead-end-ledger`](skills/dead-end-ledger/SKILL.md) | 讨好式的进展汇报，以及反复尝试已经失败的路线 | 研究账本：分级的结果、已试路线、障碍和带日期的状态行；新尝试前查重；格式检查 |

投稿前的典型顺序是 `novelty-audit` → `paper-polish` → `number-audit` → `cite-verify` → `mock-review`。`dead-end-ledger` 用于研究过程本身。

## 设计原则

1. **证据先于措辞。** 主张的强度由证据的强度决定：定理写成已证明；观察性研究中的关联不写成因果；单次运行的结果不写成一般结论。
2. **标准来自范文。** 怎样才算写得好，以目标期刊同类型的近期论文为准，不照搬任何一个学科的习惯。学科规范要求的不确定性表述（关联措辞、置信区间、局限性段落）予以保留；针对贡献本身的防御性限定予以删除。
3. **从不覆盖原件。** 所有产出写入带日期的工作目录；稿件在 git 仓库中时，该目录会被排除在版本控制之外。
4. **独立核查。** 负责审稿、分析范文或核验证明的子代理不读作者的笔记；它们的结论要经主会话核实后才会采用。
5. **模拟的判断如实标注。** 凡是"未找到"，都同时说明检索了什么、在哪里检索、何时检索。
6. **表述问题与实质问题分开。** 改写解决不了的问题会如实指出。
7. **语言。** 技能用用户的语言交流；稿件文本保持稿件原有的语言。

## 安装

依赖：
- [Claude Code](https://claude.com/claude-code)。
- Python 3.10 或更高版本。脚本只使用标准库，已在 Python 3.14 上测试。
- 可选：`pdftotext`（poppler），用于读取 PDF 稿件。
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

## 使用

在 Claude Code 中调用技能，传入稿件，需要时再加上目标期刊：

```text
/paper-polish manuscript.docx "The Lancet"
/paper-polish main.tex "Physical Review Letters" --mode survey
/number-audit main.tex supplement.tex
/cite-verify manuscript.docx
/cite-verify references.bib --tex main.tex
/novelty-audit main.tex
/mock-review ./paper "BMJ" --roles clinical,statistics,reporting
/dead-end-ledger research/LEDGER.md before
```

每个技能都规定了自己的阶段、在哪些地方停下来请用户决定，以及最后汇报哪些内容。以 `paper-polish` 为例，产出如下：

```text
polish/2026-10-29/
  scan_before.md / .json        编辑会读的部分的指标，以及被标出的措辞
  claim_ledger.md               每条主张、对应的证据，以及证据允许的措辞
  exemplars/*.md, *.intro.*     核验过的范文：元数据、摘要、引言、分析卡
  exemplar_stats.md             在范文上按同一口径计算的指标
  survey_report.md              研究问题、写作行文、叙事重心、摘要与引言的对比
  abstract_intro.tex            重写的摘要和引言（可选：标题、图 1 图注、cover letter）
  polish_notes.md               结构对比、数字出处、需要作者确认的改动
  blind/                        盲测编辑、过度宣称审查，以及对它们的核实
```

## 命令行工具

每个脚本都可以单独运行；用 `--help` 查看详细说明。

| 脚本 | 用途 |
|---|---|
| `paper-polish/scripts/hedge_scan.py` | 测量标题、摘要、引言、结论和图注；标出防御性措辞、过度宣称、因果措辞和缺少检验的 "significant" |
| `paper-polish/scripts/exemplar_meta.py` | 查找候选范文（OpenAlex，可按期刊和年份过滤）；核验元数据；获取摘要和引言（arXiv 源码或 PMC 开放获取 XML） |
| `number-audit/scripts/number_audit.py` | `extract`：数字清单和一致性线索。`trace`：在数据和代码中定位每个数字。`stats`：根据 t、F、χ²、r、z 重算 p 值，检查 k/n 百分比和比值类指标的置信区间 |
| `cite-verify/scripts/refcheck.py` | `check`：把 BibTeX 或 RIS 与 Crossref、DataCite、arXiv、Europe PMC 核对。`check-list`：核对任意引用格式的文末参考文献列表。`contexts`：列出每条文献被引用的句子 |
| `novelty-audit/scripts/lit_graph.py` | 在 OpenAlex、arXiv、Europe PMC 中做关键词、正向引用、反向引用和同期工作检索，并记录检索日志 |
| `mock-review/scripts/review_pack.py` | 为稿件目录生成隔离副本：不含作者笔记，并以 SHA-256 锁定版本；之后可检查审稿意见中的行号是否仍然有效 |
| `dead-end-ledger/scripts/ledger.py` | 研究账本的创建、检索（对路线和笔记做 TF-IDF）、格式检查和状态汇总 |

```bash
S=skills
python3    $S/paper-polish/scripts/hedge_scan.py manuscript.docx
python3    $S/number-audit/scripts/number_audit.py stats manuscript.docx --out audit/
python3 -I $S/cite-verify/scripts/refcheck.py check-list manuscript.docx --out refcheck/
python3 -I $S/novelty-audit/scripts/lit_graph.py search '"pass elimination" AND streaming' --log search_log.md
```

会读取下载内容的脚本，请用 `python3 -I` 运行。

## 支持的输入

| 输入 | 格式 |
|---|---|
| 稿件 | `.tex`（跟随 `\input` / `\include`）、`.docx`、`.md`、`.txt`、`.pdf`（借助 `pdftotext`） |
| 章节识别 | LaTeX 章节命令；IMRaD 标题；编号标题和全大写标题；无标题引言（Nature 风格）；结构化摘要 |
| 参考文献 | BibTeX；RIS（Zotero、EndNote、Mendeley 导出）；任意引用格式的文本列表；LaTeX `thebibliography` |
| 引用上下文 | `\cite` 键；数字引用 `[n]`；作者–年份引用 |
| 统计量 | 正文中的 APA 风格报告，如 `t(23) = 2.45, p = .02`、`F(2, 45) = 3.21, p < .05`、`χ2(1) = 3.84, p = .05`、`r(46) = .32, p = .03`、`z = 1.96, p = .05`；`k of n (x%)`；带 95% 置信区间的 OR / RR / HR |

## 数据来源与隐私

脚本只访问公开的元数据服务：[OpenAlex](https://openalex.org)、[Crossref](https://www.crossref.org)、[DataCite](https://datacite.org)、[arXiv](https://arxiv.org) 和 [Europe PMC](https://europepmc.org)（PubMed、PMC 全文、bioRxiv、medRxiv）。不会发送任何个人信息。

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
- 不检索 Web of Science、Scopus、PsycINFO 等订阅数据库，这类检索会交给用户完成。许多人文学科文献不在上述任何服务中。
- 模式扫描和来源追溯给出的是线索，不是结论；技能要求逐条结合上下文阅读。
- 模拟审稿和模拟编辑由同一类模型完成。它们检验的是贡献能否被读出、主张是否有依据，不能预测编辑的决定。

## 仓库结构

```text
skills/<name>/SKILL.md         Claude Code 执行的流程
skills/<name>/references/      细则、模板和示例
skills/<name>/scripts/         可单独运行的检查脚本
lib/                           共享模块：文档读取、学术接口、BibTeX/RIS、统计
templates/SKILL_TEMPLATE.md    新技能模板
FAILURE_MODES.md               已观察到的失效模式目录，也是本库的路线图
install.sh                     以软链接方式安装技能
.claude-plugin/plugin.json     插件清单
```

## 扩展

1. 在 [FAILURE_MODES.md](FAILURE_MODES.md) 中登记失效模式和观察到的证据。新技能应当针对实际发生过的问题。
2. 把 [templates/SKILL_TEMPLATE.md](templates/SKILL_TEMPLATE.md) 复制为 `skills/<name>/SKILL.md`，按需添加 `references/` 和 `scripts/`。脚本通过 `os.path.realpath(__file__)` 定位 `lib/`。
3. 运行 `./install.sh`，在新会话中测试。

欢迎补充其他学科的案例。目前的证据来自理论物理方向的稿件，均已脱敏。

## 许可证

尚未选定许可证。
