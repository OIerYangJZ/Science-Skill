# Science-Skill

**English** | [简体中文](README.zh-CN.md)

Claude Code skills that counter the recurring failure modes of AI-assisted research.

AI assistants help with research writing and checking, but they fail in predictable ways:
- When asked to polish a manuscript, they hedge until the contribution disappears; when asked to make it stronger, they overclaim.
- They let numbers drift away from the data.
- They produce citations that do not exist.
- They search for literature that confirms novelty instead of literature that challenges it.
- They write mock reviews that echo the authors' own notes.
- They report progress more optimistically than the evidence allows.

Each skill in this library targets one of these failure modes. A skill is a written procedure that Claude Code follows, backed by standard-library Python scripts that measure, trace, or verify, so that conclusions rest on evidence rather than on the model's tone. Every skill was written after the corresponding failure occurred in real projects ([FAILURE_MODES.md](FAILURE_MODES.md)).

The skills are discipline-agnostic. They work on LaTeX, Word, Markdown, plain-text, and PDF manuscripts, and they distinguish theoretical, experimental, observational, computational, qualitative, and review studies.

## Skills

| Skill | Failure mode addressed | Main outputs |
|---|---|---|
| [`paper-polish`](skills/paper-polish/SKILL.md) | Defensive writing that hides the novelty from editors, and the opposite swing to overclaiming | Survey of exemplar papers from the target journal; gap analysis; claim ledger; rewritten title, abstract and introduction; blind editor test |
| [`number-audit`](skills/number-audit/SKILL.md) | Numbers that drift from data and code; misread tool conventions; statistics that do not add up | Number inventory; consistency leads; trace of each key number to its source; statcheck-style checks of p-values, percentages and CIs; audit report |
| [`cite-verify`](skills/cite-verify/SKILL.md) | Wrong or fabricated bibliographic metadata; citations that do not support the sentence they are attached to | Per-entry verification against Crossref, DataCite, arXiv and Europe PMC; proposed corrected entries; list of citation contexts for claim checking |
| [`novelty-audit`](skills/novelty-audit/SKILL.md) | Searching only for literature that confirms novelty | Contributions restated in neighboring communities' terms; forward, backward, keyword and concurrent-work searches; per-contribution novelty verdict with a search log |
| [`mock-review`](skills/mock-review/SKILL.md) | Mock reviews that are not independent, not verified, or tied to a moving manuscript | Isolated, version-pinned review pack; independent reviewer reports; cross-discussion; main-session verification; prioritized joint report |
| [`dead-end-ledger`](skills/dead-end-ledger/SKILL.md) | Sycophantic progress reports, and repeated attempts at routes that already failed | Research ledger with graded results, routes, barriers and a dated status line; duplicate check before each new attempt; lint |

A typical pre-submission sequence is `novelty-audit` → `paper-polish` → `number-audit` → `cite-verify` → `mock-review`. `dead-end-ledger` is meant for the research phase itself.

## Design principles

1. **Evidence before wording.** Claim strength follows evidence strength. A theorem is stated as proved; an observational association is not stated as a cause; a single run is not stated as a general result.
2. **Norms come from exemplars.** What counts as good writing is measured on recent papers of the same type in the target journal, not taken from any one field's habits. Uncertainty language that a field requires (associational wording, confidence intervals, limitations sections) is kept. Defensive hedging around the contribution itself is removed.
3. **Originals are never overwritten.** All outputs go to a dated working directory. When the manuscript lives in a git repository, that directory is excluded from git.
4. **Independent checking.** Subagents that review, analyze exemplars, or verify proofs do not see the authors' notes. The main session verifies their claims before anything is acted on.
5. **Simulated judgments are labeled as such.** A "not found" result is always reported with what was searched, where, and when.
6. **Presentation and substance are kept apart.** Problems that rewriting cannot fix are reported as such.
7. **Language.** The skills talk to the user in the user's language. Manuscript text stays in the manuscript's language.

## Installation

Requirements:
- [Claude Code](https://claude.com/claude-code).
- Python 3.10 or later. The scripts use the standard library only and are tested on Python 3.14.
- Optional: `pdftotext` (poppler), for PDF manuscripts.
- Network access to the public scholarly APIs listed under [Data sources and privacy](#data-sources-and-privacy).

```bash
git clone https://github.com/OIerYangJZ/Science-Skill.git
cd Science-Skill
./install.sh            # symlinks skills/* into ~/.claude/skills/
./install.sh uninstall  # removes only the links created by install.sh
```

Start a new Claude Code session afterwards; each skill is then available as `/<skill-name>`. The symlinks point to the cloned repository, so edits and `git pull` take effect in the next session.

Alternatively, load the repository as a plugin for a single session with `claude --plugin-dir /path/to/Science-Skill`. The skills are then namespaced, for example `/science-skill:paper-polish`. Use one method or the other, not both.

The scripts depend on the shared `lib/` directory, so do not copy a single skill directory elsewhere.

## Usage

Invoke a skill in Claude Code with a manuscript and, where relevant, a target journal:

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

Each skill defines its phases, the points where it stops for the user's decision, and what it reports at the end. For example, `paper-polish` produces:

```text
polish/2026-10-29/
  scan_before.md / .json        metrics and flagged phrasing in the editor-facing sections
  claim_ledger.md               each claim, its evidence, and the wording that evidence allows
  exemplars/*.md, *.intro.*     verified exemplar papers: metadata, abstract, introduction, analysis card
  exemplar_stats.md             the same metrics computed on the exemplars
  survey_report.md              comparison of research question, writing, narrative, abstract and introduction
  abstract_intro.tex            rewritten abstract and introduction (optional: titles, Fig. 1 caption, cover letter)
  polish_notes.md               structural comparison, number provenance, changes the authors must confirm
  blind/                        blind editor test, overclaim review, and their verification
```

## Command-line tools

Each script can also be run on its own; use `--help` for details.

| Script | Purpose |
|---|---|
| `paper-polish/scripts/hedge_scan.py` | Measures title, abstract, introduction, conclusion and captions; flags defensive phrasing, overclaiming, causal wording and unsupported "significant" |
| `paper-polish/scripts/exemplar_meta.py` | Finds candidate exemplars (OpenAlex, by journal and year); verifies metadata; fetches abstracts and introductions (arXiv source or PMC open-access XML) |
| `number-audit/scripts/number_audit.py` | `extract`: number inventory and consistency leads. `trace`: locate each number in data and code. `stats`: recompute p-values from t, F, χ², r and z; check k/n percentages and ratio confidence intervals |
| `cite-verify/scripts/refcheck.py` | `check`: BibTeX or RIS against Crossref, DataCite, arXiv and Europe PMC. `check-list`: free-text reference lists in any citation style. `contexts`: the sentences in which each reference is cited |
| `novelty-audit/scripts/lit_graph.py` | Keyword, forward-citation, backward-citation and concurrent-work searches across OpenAlex, arXiv and Europe PMC, with a search log |
| `mock-review/scripts/review_pack.py` | Builds an isolated, SHA-256-pinned copy of a manuscript directory without the authors' notes; later checks whether review line numbers still apply |
| `dead-end-ledger/scripts/ledger.py` | Creates, searches (TF-IDF over routes and notes), lints, and summarizes a research ledger |

```bash
S=skills
python3    $S/paper-polish/scripts/hedge_scan.py manuscript.docx
python3    $S/number-audit/scripts/number_audit.py stats manuscript.docx --out audit/
python3 -I $S/cite-verify/scripts/refcheck.py check-list manuscript.docx --out refcheck/
python3 -I $S/novelty-audit/scripts/lit_graph.py search '"pass elimination" AND streaming' --log search_log.md
```

Run the scripts that read downloaded content with `python3 -I`.

## Supported inputs

| Input | Formats |
|---|---|
| Manuscripts | `.tex` (following `\input` / `\include`), `.docx`, `.md`, `.txt`, `.pdf` (via `pdftotext`) |
| Section detection | LaTeX sectioning; IMRaD headings; numbered and all-caps headings; unheaded introductions (Nature style); structured abstracts |
| References | BibTeX; RIS (Zotero, EndNote, Mendeley export); free-text reference lists in any citation style; LaTeX `thebibliography` |
| Citation contexts | `\cite` keys; numeric `[n]` citations; author–year citations |
| Statistics | Inline APA-style reports such as `t(23) = 2.45, p = .02`, `F(2, 45) = 3.21, p < .05`, `χ2(1) = 3.84, p = .05`, `r(46) = .32, p = .03`, `z = 1.96, p = .05`; `k of n (x%)`; OR / RR / HR with 95% CI |

## Data sources and privacy

The scripts query only public metadata services: [OpenAlex](https://openalex.org), [Crossref](https://www.crossref.org), [DataCite](https://datacite.org), [arXiv](https://arxiv.org), and [Europe PMC](https://europepmc.org) (PubMed, PMC full text, bioRxiv, medRxiv). No personal information is sent.

Two optional environment variables:
- `OPENALEX_API_KEY`: without a key, all users on the same IP address share a small daily OpenAlex budget. A free key is recommended for heavy use.
- `SCIENCE_SKILL_MAILTO`: an e-mail address for the Crossref and OpenAlex polite pools. It is never set automatically.

Other behavior:
- arXiv requests are rate-limited. If arXiv still answers HTTP 429 after retries, the scripts skip arXiv for the rest of that run and say so.
- arXiv LaTeX sources are parsed in memory; nothing from them is written to disk or executed.
- Verbatim quotes and measurements are taken only from API text or source files, never from model-summarized web pages.

## Limitations

- Only English-language manuscripts are supported; the phrase lists and sentence splitting are English-specific.
- Superscript citation numbers in Word documents are lost in text conversion and must be checked by hand.
- The statistics checker recognizes inline APA-style reports only. Statistics in tables need a manual check.
- Subscription databases (Web of Science, Scopus, PsycINFO) are not queried; the skills hand such searches to the user. Many humanities sources are not indexed in any of the services above.
- Pattern scans and traces produce leads, not verdicts. The skills require each lead to be read in context.
- Mock reviews and editor simulations are performed by the same family of models. They test whether a contribution can be found and whether claims are supported; they do not predict editorial decisions.

## Repository layout

```text
skills/<name>/SKILL.md         procedure followed by Claude Code
skills/<name>/references/      detailed rules, templates and examples
skills/<name>/scripts/         standalone checking scripts
lib/                           shared modules: document reading, scholarly APIs, BibTeX/RIS, statistics
templates/SKILL_TEMPLATE.md    template for new skills
FAILURE_MODES.md               catalog of observed failure modes; the library's roadmap
install.sh                     installs the skills as symlinks
.claude-plugin/plugin.json     plugin manifest
```

## Extending the library

1. Record the failure mode and the observed evidence in [FAILURE_MODES.md](FAILURE_MODES.md). A new skill should address a failure that has actually occurred.
2. Copy [templates/SKILL_TEMPLATE.md](templates/SKILL_TEMPLATE.md) to `skills/<name>/SKILL.md`, and add `references/` and `scripts/` as needed. Scripts locate `lib/` through `os.path.realpath(__file__)`.
3. Run `./install.sh` and test in a new session.

Case studies from other disciplines are welcome. The current evidence comes from theoretical physics manuscripts and has been anonymized.

## License

No license has been chosen yet.
