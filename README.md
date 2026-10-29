# Science-Skill

一组 Claude Code skill，用来对付 AI 辅助科研时反复出现的失效模式。每个 skill 都对应 [FAILURE_MODES.md](FAILURE_MODES.md) 里登记的一种问题，而且这种问题在真实项目中发生过。

**适用范围：各学科通用。**
- **稿件格式**：LaTeX、Word（.docx）、Markdown、纯文本、PDF（需安装 pdftotext）。
- **参考文献**：BibTeX、RIS（Zotero / EndNote 导出），或者稿件末尾任意引用格式的参考文献列表。
- **文献来源**：OpenAlex（全学科）、Crossref、DataCite、arXiv，以及 Europe PMC（PubMed、PMC 全文、bioRxiv / medRxiv）。
- **研究体裁**：理论、实验、随机对照试验、观察性研究、计算或机器学习、定性研究、系统综述。证据等级、报告规范和措辞规则都按体裁区分。
- **"写得好不好"的标准**：一律以目标期刊同体裁的范文统计为准，不预设任何学科的习惯。

skill 的起源案例来自作者的量子信息论文，它们只用来说明问题确实存在，不构成默认标准。目前只支持英文稿件。

## 现有 skill

| skill | 解决什么 | 典型用法 |
|---|---|---|
| [paper-polish](skills/paper-polish/SKILL.md) | AI 润色导致防御性写作，编辑看不出新意；以及反方向的过度宣称（包括相关写成因果） | `/paper-polish manuscript.docx "The Lancet"` |
| [number-audit](skills/number-audit/SKILL.md) | 统计量与 p 值对不上、百分比与 n 对不上、正文数字与数据或脚本脱节、工具约定读错、同一符号两套数值 | `/number-audit main.tex supplement.tex` |
| [cite-verify](skills/cite-verify/SKILL.md) | 参考文献元数据错误或编造；引用并不支撑所在的句子 | `/cite-verify manuscript.docx` 或 `/cite-verify refs.bib --tex main.tex` |
| [novelty-audit](skills/novelty-audit/SKILL.md) | 只找支持"我们是新的"的文献，漏掉审稿人会拿来对比的先例和标准技术 | `/novelty-audit main.tex` |
| [mock-review](skills/mock-review/SKILL.md) | 模拟审稿不独立、不复核、行号漂移；报告规范（CONSORT、STROBE、PRISMA 等）没人查 | `/mock-review <稿件目录> BMJ --roles 临床,统计,报告规范` |
| [dead-end-ledger](skills/dead-end-ledger/SKILL.md) | 长期攻关（证明、实验、模型）时的讨好式汇报，以及重走已失败的路线 | `/dead-end-ledger research/LEDGER.md before` |

投稿前的推荐顺序：先做 `novelty-audit`（新意的定位决定怎么写），再依次做 `paper-polish`、`number-audit` 和 `cite-verify`，最后用 `mock-review` 总检。`dead-end-ledger` 用在研究过程中，不在投稿流程里。

候选（还没写）：venue-fit，见 [FAILURE_MODES.md](FAILURE_MODES.md)。

## 安装

```bash
cd ~/Desktop/Science-Skill
./install.sh            # 把 skills/* 软链接到 ~/.claude/skills/，新开会话后可用 /<name> 调用
./install.sh uninstall  # 只移除本脚本创建的软链接
```

软链接指向本目录，所以在这里修改会直接生效（需新开会话）。新增 skill 后，重新运行一次 `./install.sh`。各 skill 的脚本依赖仓库根目录的 `lib/`，所以不要单独把某个 skill 目录复制到别处使用。

另一种方式是把整个仓库当作插件加载，例如 `claude --plugin-dir ~/Desktop/Science-Skill`，此时调用名带命名空间，如 `/science-skill:paper-polish`。两种方式选一种，不要同时用。

## 目录

```
skills/<name>/SKILL.md        流程（中文）
skills/<name>/references/     细则、模板、案例
skills/<name>/scripts/        可单独运行的检查脚本（各自有 --help）
lib/                          共用模块：LaTeX 解析、学术 API、BibTeX（见 lib/README.md）
templates/SKILL_TEMPLATE.md   新 skill 模板
FAILURE_MODES.md              失效模式目录 = 路线图
```

## 脚本速查

```bash
S=~/Desktop/Science-Skill/skills
python3    $S/paper-polish/scripts/hedge_scan.py manuscript.docx           # 摘要和引言的指标 + 防御性/过冲/因果措辞（.tex/.docx/.md/.pdf）
python3    $S/number-audit/scripts/number_audit.py stats manuscript.docx --out number_audit/today   # 统计量与 p 值、k/n%、OR/HR 置信区间
python3 -I $S/cite-verify/scripts/refcheck.py check-list manuscript.docx --out refcheck/today        # 任意格式的文末参考文献
python3 -I $S/novelty-audit/scripts/lit_graph.py search '"gut microbiome" AND "social network"' --db europepmc
python3 -I $S/paper-polish/scripts/exemplar_meta.py search '"T-count" AND "lower bound"' --venue "PRX Quantum" --from 2021
python3    $S/number-audit/scripts/number_audit.py extract main.tex supplement.tex --out number_audit/today
python3    $S/number-audit/scripts/number_audit.py trace number_audit/today/numbers.json --repo . --regions abstract,introduction,caption,table
python3 -I $S/cite-verify/scripts/refcheck.py check references.bib --tex main.tex --out refcheck/today
python3 -I $S/novelty-audit/scripts/lit_graph.py search '"pass elimination" AND streaming' --log novelty/today/search_log.md
python3    $S/mock-review/scripts/review_pack.py pack --repo . --out ~/mock_review/paper-today --roles math,application
python3    $S/dead-end-ledger/scripts/ledger.py search LEDGER.md "new idea" --notes research/
```

联网的脚本只访问 OpenAlex、Crossref、DataCite、arXiv 和 Europe PMC 的公开接口，不会发送任何个人信息。OpenAlex 在没有 API key 时，同一网络下的所有人共用一个很小的每日额度，大量检索前建议申请免费 key，并设置 `OPENALEX_API_KEY`。arXiv 请求过于频繁会返回 429；脚本会退避重试，仍然失败时，本次运行就跳过 arXiv，并给出提示。

## 所有 skill 共用的设计原则

1. **证据先于措辞。** 结论的强度由证据决定，不由语气决定。
2. **不覆盖原件。** 产出放在独立的工作目录里；在 git 仓库中，工作目录会加入 `.git/info/exclude`。
3. **独立复核。** 子代理不读作者的笔记；子代理给出的结论，由主会话核实后才采用。
4. **模拟的判断标"推断"。** 检索不到的东西，只说"在某某范围内未发现"。
5. **表述问题和实质问题分开说。** 靠重写解决不了的，如实告诉用户。
6. 对话用中文；论文和代码保持原语言。

## 新增 skill

1. 先在 `FAILURE_MODES.md` 登记症状和真实证据。
2. 复制 `templates/SKILL_TEMPLATE.md` 到 `skills/<name>/SKILL.md`，按需加 `references/` 和 `scripts/`。脚本按现有写法通过 `realpath` 引用 `lib/`。
3. 运行 `./install.sh`，新开一个会话测试。

## 注意

各 skill 引用的案例（Case A、Case B）都已脱敏：不含期刊名、投稿经过或审稿细节，只保留写作规律和改法。范文列表中的论文都是公开发表的文献。
