# lib：各 skill 共用的 Python 模块

只依赖 Python 3.10+ 标准库。各 skill 的脚本通过 `os.path.realpath(__file__)` 定位到本目录，所以通过 `~/.claude/skills/<name>` 的软链接调用也能找到它。不要单独把某个 skill 目录复制到别处使用。

| 模块 | 内容 | 使用者 |
|---|---|---|
| `texutil.py` | 统一读取 `.tex`（跟随 `\input`）、`.docx`、`.md`、`.txt`、`.pdf`（需 pdftotext），保留位置映射；清洗为纯文本；定位摘要、引言、结论、参考文献、图注（LaTeX 命令、IMRaD 标题、Nature 式无标题引言、结构化摘要）；句子切分、引用和宏定位、区域标注 | 全部 |
| `scholarly.py` | OpenAlex、Crossref、DataCite、arXiv、Europe PMC（PubMed、PMC 全文、bioRxiv/medRxiv）访问；严格标题匹配；arXiv 源码只在内存中解析；arXiv 限流时自动断路 | paper-polish、cite-verify、novelty-audit |
| `bibtex.py` | BibTeX 与 RIS 读取、自由格式参考文献列表拆分、作者姓氏提取、LaTeX 转纯文本 | cite-verify |
| `docxutil.py` | 只用标准库读取 Word `.docx`：标题样式和加粗短段落识别为章节，表格、公式占位；位置记为段落号 | 全部（通过 texutil.load_document） |
| `statsutil.py` | t、F、χ²、r、z 的 p 值（正则化不完全 beta 和 gamma 函数） | number-audit stats |

网络访问只针对公开的元数据 API，不会发送个人信息。如需自己的配额，可设置 `OPENALEX_API_KEY`（OpenAlex 无 key 时所有人共用一个小的每日额度）和 `SCIENCE_SKILL_MAILTO`（Crossref polite pool）。
