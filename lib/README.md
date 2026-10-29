# lib: Python modules shared by the skills

Depends only on the Python 3.10+ standard library. Each skill's scripts locate this directory via `os.path.realpath(__file__)`, so it is found even when a skill is invoked through a symlink at `~/.claude/skills/<name>`. Do not copy an individual skill directory elsewhere to use it on its own.

| Module | Contents | Used by |
|---|---|---|
| `texutil.py` | Unified reading of `.tex` (following `\input`), `.docx`, `.md`, `.txt`, `.pdf` (requires pdftotext), preserving a position map; cleaning to plain text; locating the abstract, introduction, conclusion, references, and figure captions (LaTeX commands, IMRaD headings, Nature-style untitled introductions, structured abstracts); sentence splitting, locating citations and macros, region labeling | All |
| `scholarly.py` | Access to OpenAlex, Crossref, DataCite, arXiv, Europe PMC (PubMed, PMC full text, bioRxiv/medRxiv); strict title matching; arXiv source parsed in memory only; automatic circuit breaker when arXiv rate-limits | paper-polish, cite-verify, novelty-audit |
| `bibtex.py` | Reading BibTeX and RIS, splitting free-form reference lists, extracting author surnames, converting LaTeX to plain text | cite-verify |
| `docxutil.py` | Reads Word `.docx` with the standard library only: heading styles and short bold paragraphs are recognized as sections, tables and equations become placeholders; positions are recorded as paragraph numbers | All (via texutil.load_document) |
| `statsutil.py` | p-values for t, F, χ², r, z (regularized incomplete beta and gamma functions) | number-audit stats |

Network access goes only to public metadata APIs; no personal information is sent. For your own quota, set `OPENALEX_API_KEY` (without a key, OpenAlex gives everyone one small shared daily allowance) and `SCIENCE_SKILL_MAILTO` (Crossref polite pool).
