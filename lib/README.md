# lib: Python modules shared by the skills

Depends only on the Python 3.10+ standard library (Chrome, LaTeX and poppler are optional for slide and poster previews). Each skill's scripts locate this directory via `os.path.realpath(__file__)`, so it is found even when a skill is invoked through a symlink at `~/.claude/skills/<name>`. Do not copy an individual skill directory elsewhere to use it on its own.

| Module | Contents | Used by |
|---|---|---|
| `texutil.py` | Unified reading of `.tex` (following `\input`), `.docx`, `.md`, `.txt`, `.pdf` (requires pdftotext), preserving a position map; cleaning to plain text; locating the abstract, introduction, conclusion, references, and figure captions (LaTeX commands, IMRaD headings, Nature-style untitled introductions, structured abstracts); sentence splitting, locating citations and macros, region labeling | All |
| `scholarly.py` | Access to OpenAlex, Crossref, DataCite, arXiv, Europe PMC (PubMed, PMC full text, bioRxiv/medRxiv); strict title matching; arXiv source parsed in memory only; automatic circuit breaker when arXiv rate-limits | paper-polish, cite-verify, novelty-audit |
| `bibtex.py` | Reading BibTeX and RIS, splitting free-form reference lists, extracting author surnames, converting LaTeX to plain text | cite-verify |
| `docxutil.py` | Reads Word `.docx` with the standard library only: heading styles and short bold paragraphs are recognized as sections, tables and equations become placeholders; positions are recorded as paragraph numbers | All (via texutil.load_document) |
| `statsutil.py` | p-values for t, F, χ², r, z (regularized incomplete beta and gamma functions) | number-audit stats |
| `slidespec.py` | The Markdown content spec for slides and posters: front matter, headings with `{attrs}`, bullets with status chips, figures, tables, formulas, columns, speaker notes, placeholders | group-meeting-deck, research-poster |
| `pptxwriter.py` | Editable PowerPoint (.pptx) files with the standard library: any slide size up to 56 in, shapes, styled text, bullets, pictures, tables, speaker notes; an HTML twin of the same geometry for previews and overflow checks; text measurement in headless Chrome; package validation | group-meeting-deck, research-poster |
| `slidekit.py` | Spec elements turned into measured pieces and stacked (images fill the remaining height); PDF/SVG figures converted for PowerPoint; display formulas via LaTeX or Unicode | group-meeting-deck, research-poster |
| `designkit.py` | WCAG contrast, colour-vision-deficiency simulation, image size and effective resolution, CJK-aware word counts and speaking time, number tracing against sources, claim-strength drift, placeholders, ledger statuses, optional Chrome / LibreOffice / Quick Look / pdftoppm / LaTeX helpers | group-meeting-deck, research-poster |
| `designcheck.py` | Checks shared by the slide and poster skills and their FAIL / WARN / INFO report (exit 1 while a FAIL remains) | group-meeting-deck, research-poster |

Network access goes only to public metadata APIs; no personal information is sent. For your own quota, set `OPENALEX_API_KEY` (without a key, OpenAlex gives everyone one small shared daily allowance) and `SCIENCE_SKILL_MAILTO` (Crossref polite pool).

## findings.py

Findings ledgers and the reports computed from them. `proof-audit`, `mock-review`, `experiment-integrity` and `number-audit` call `findings.main_cli(<profile>)` from their report scripts. Each profile (`proof`, `review`, `integrity`, `numbers`) defines its verdict vocabulary, the severe verdicts that need main-session verification, and the report title. `render()` returns the Markdown report and the analysis; the exit code is 0 when there is no confirmed severe finding, 1 when there are confirmed severe findings, and 2 when the report is not final.
