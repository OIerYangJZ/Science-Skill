# Science-Skill

**English** | [简体中文](README.zh-CN.md)

Claude Code skills that counter the recurring failure modes of AI-assisted research.

AI assistants help with research writing, analysis and checking, but they fail in predictable ways:
- When asked to polish a manuscript, they hedge until the contribution disappears; when asked to make it stronger, they overclaim.
- They let numbers drift away from the data.
- They write code that no longer does what the paper says.
- They produce citations that do not exist.
- They search for literature that confirms novelty instead of literature that challenges it.
- They choose venues from memory.
- They write mock reviews that echo the authors' own notes.
- They report progress more optimistically than the evidence allows.

Each skill in this library targets one of these failure modes. A skill is a written procedure that Claude Code follows, backed by standard-library Python scripts that measure, trace or verify, so that conclusions rest on evidence rather than on the model's tone. Every skill was written after the corresponding failure occurred in real projects ([FAILURE_MODES.md](FAILURE_MODES.md)).

The skills are discipline-agnostic. They work on LaTeX, Word, Markdown, plain-text and PDF manuscripts, and they distinguish theoretical, experimental, observational, computational, qualitative and review studies.

## Contents

- [Skills at a glance](#skills-at-a-glance)
- [Design principles](#design-principles)
- [Installation](#installation)
- [How to use the skills](#how-to-use-the-skills)
- [Skill guide](#skill-guide): [paper-polish](#paper-polish) · [number-audit](#number-audit) · [experiment-integrity](#experiment-integrity) · [cite-verify](#cite-verify) · [novelty-audit](#novelty-audit) · [venue-fit](#venue-fit) · [mock-review](#mock-review) · [dead-end-ledger](#dead-end-ledger)
- [Command-line tools](#command-line-tools)
- [Supported inputs](#supported-inputs)
- [Data sources and privacy](#data-sources-and-privacy)
- [Limitations](#limitations)
- [Repository layout](#repository-layout) · [Extending the library](#extending-the-library) · [License](#license)

## Skills at a glance

| Skill | Failure mode addressed | Main outputs |
|---|---|---|
| [`paper-polish`](#paper-polish) | Defensive writing that hides the novelty from editors, and the opposite swing to overclaiming | Exemplar survey from the target journal; gap analysis; claim ledger; rewritten title, abstract and introduction; blind editor test |
| [`number-audit`](#number-audit) | Numbers that drift from data and code; misread tool conventions; statistics that do not add up | Number inventory; consistency leads; source trace; statcheck-style checks; audit report; guards that keep numbers tied to data |
| [`experiment-integrity`](#experiment-integrity) | Code that does not implement the design the text describes; experiment designs that manufacture results | Claimed-design ledger; static code scan; confirmed findings with before/after impact; regression guards |
| [`cite-verify`](#cite-verify) | Wrong or fabricated bibliographic metadata; citations that do not support their sentences | Per-entry verification against Crossref, DataCite, arXiv and Europe PMC; proposed corrections; claim-support check |
| [`novelty-audit`](#novelty-audit) | Searching only for literature that confirms novelty; being pre-empted after investing | Contributions restated in neighboring communities' terms; multi-source searches with a log; novelty verdicts; scout mode and watch list |
| [`venue-fit`](#venue-fit) | Choosing a venue from impressions | Where similar work is published; venue profiles; official fact sheets with URLs and dates; fit assessment; submission plan and calendar |
| [`mock-review`](#mock-review) | Mock reviews that are not independent, not verified, or tied to a moving manuscript | Isolated, version-pinned review pack; independent reports; cross-discussion; verification; prioritized joint report |
| [`dead-end-ledger`](#dead-end-ledger) | Sycophantic progress reports and repeated attempts at failed routes | Research ledger with graded results, routes and barriers; duplicate check before new attempts; lint |

Typical order:
- **Before starting a project:** `novelty-audit --mode scout`.
- **During research:** `dead-end-ledger`, and `experiment-integrity` once the analysis code stabilizes.
- **Before submission:** `novelty-audit` → `venue-fit` → `paper-polish` → `experiment-integrity` → `number-audit` → `cite-verify` → `mock-review`.

## Design principles

1. **Evidence before wording.** Claim strength follows evidence strength. A theorem is stated as proved; an observational association is not stated as a cause; a single run is not stated as a general result.
2. **Norms come from exemplars.** What counts as good writing is measured on recent papers of the same type in the target journal, not taken from any one field's habits. Uncertainty language that a field requires (associational wording, confidence intervals, limitations sections) is kept. Defensive hedging around the contribution itself is removed.
3. **Originals are never overwritten.** All outputs go to a dated working directory, excluded from git when the manuscript lives in a repository. Code changes are proposed as patches, and reruns happen in scratch copies.
4. **Independent checking.** Subagents that review, analyze exemplars, or verify proofs and results do not see the authors' notes. The main session verifies their claims before anything is acted on.
5. **Simulated judgments are labeled as such.** "Not found" is always reported with what was searched, where, and when. Facts about venues and tools come from official sources or source code, with the date checked.
6. **Presentation and substance are kept apart.** Problems that rewriting cannot fix are reported as such.
7. **Expensive steps need consent.** Long or paid reruns are estimated first and started only after the user agrees.
8. **Language.** The skills talk to the user, and write reports, in the user's language. Manuscript text stays in the manuscript's language.

## Installation

Requirements:
- [Claude Code](https://claude.com/claude-code).
- Python 3.10 or later. The scripts use the standard library only and are tested on Python 3.14.
- Optional: `pdftotext` (poppler), for PDF manuscripts.
- Optional: the GitHub CLI `gh`, for repository searches in `novelty-audit`.
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

## How to use the skills

- **Invoke** a skill by typing `/<skill-name>` followed by its arguments in a Claude Code session started in, or near, the project directory. The arguments are free text: paths, a target journal, a mode. Claude Code may also invoke a skill on its own when your request matches the skill's description (for example, "check the numbers in my paper").
- **The skill runs a fixed procedure** (its phases) and **stops where a decision is yours**, for example to confirm the novelty statement before rewriting, or to approve a long rerun.
- **Outputs** go to a dated working directory next to the manuscript (`polish/`, `number_audit/`, `integrity/`, `refcheck/`, `novelty/`, `venue/`) or, for mock reviews, outside the repository. In a git repository the directory is added to `.git/info/exclude`.
- **Every skill ends** with a short report in your language: conclusions, file paths, decisions needed, and anything it could not check.
- **Scripts can run on their own**, without Claude Code (see [Command-line tools](#command-line-tools)).

## Skill guide

### paper-polish

**What it does.** Makes the novelty and significance visible to an editor at a glance without overclaiming. It measures your editor-facing text (title, abstract, introduction, Fig. 1 caption, cover letter) against recent well-written papers of the same type in your target journal, then rewrites from a claim ledger that ties every claim to its evidence.

**Use it when** you are about to submit, after a desk rejection, or when you suspect AI polishing made the paper defensive. **Not for** grammar-level editing.

**Invoke.**
```text
/paper-polish <manuscript> "<target journal>" [--mode full|survey|rewrite|check]
/paper-polish manuscript.docx "The Lancet"
/paper-polish main.tex "Physical Review Letters" --mode survey
```

| Mode | What runs | When |
|---|---|---|
| `full` (default) | Phases 0–7 | First polish of this manuscript |
| `survey` | Phases 0–4 (gap report only) | You want the diagnosis before any rewriting |
| `rewrite` | Phases 5–7, reusing an earlier survey | The survey already exists |
| `check` | Scan and blind editor test only | Final check before submission |

**What happens.**
1. **Intake.** It asks for the target journal if you did not give one. Provide rejection letters and reviews if you have them.
2. **Measure** the editor-facing sections: where the main result first appears, hedges, causal wording, unsupported "significant", symbol density, caption length. It also builds the claim ledger.
3. **Find 15–30 exemplars** in the target journal (Pool A), 5–10 nearest prior works (Pool B), and the journal's official criteria (Pool C). Every exemplar is verified by DOI, arXiv ID or PMID.
4. **Analyze the exemplars** in parallel with subagents that do not see your manuscript.
5. **Write `survey_report.md`.** It compares research question, prose, narrative emphasis, and abstract and introduction structure, and separates presentation problems from problems that need new results.
6. **Novelty spine.** Five sentences: result, gap, stakes, headline number, scope. **It stops here for your confirmation.**
7. **Rewrite** into new files. Every number gets a provenance entry, and every change of claim strength or scope is listed for you to approve.
8. **Blind editor test.** A subagent reads the old and new versions as A and B without knowing which is new; another subagent hunts for overclaiming. The main session verifies both reports.

**Outputs** (`polish/<date>/`): `scan_before.md`, `claim_ledger.md`, `exemplars/`, `exemplar_stats.md`, `survey_report.md`, `abstract_intro.tex` (or your format), `polish_notes.md`, `blind/`.

**Run the scripts directly.**
```bash
python3    skills/paper-polish/scripts/hedge_scan.py manuscript.docx
python3    skills/paper-polish/scripts/hedge_scan.py polish/*/exemplars/*.md --summary
python3 -I skills/paper-polish/scripts/exemplar_meta.py search '"T-count" AND "lower bound"' --venue "PRX Quantum" --from 2021
python3 -I skills/paper-polish/scripts/exemplar_meta.py fetch 10.7554/eLife.05224 PMID:25774601 2211.09133 --out exemplars --intro
```

**Tips.**
- The writing norms come from the exemplar statistics, so the choice of target journal matters.
- Field-required uncertainty language (associational wording, confidence intervals) is kept on purpose.

### number-audit

**What it does.** Audits every number in the manuscript:
- inventories them;
- flags symbols with conflicting values and hand-typed copies of data macros;
- recomputes p-values from reported test statistics, k/n percentages and ratio confidence intervals;
- traces key numbers to the data or code that produced them, and recomputes them in a scratch copy;
- checks external tools' conventions against their source code;
- checks for parameters that the text has ruled out.

It then installs **guards** that recompute the key numbers from their sources on every build.

**Use it when** the analysis is final and before submission, after any rerun or data update, and before responding to reviewers.

**Invoke.**
```text
/number-audit <main> [<supplement>] [--repo <data-and-code dir>] [--scope key|all]
/number-audit main.tex supplement.tex --repo .
/number-audit manuscript.docx --scope all
```
`key` (default) audits the abstract, introduction, conclusion, captions, tables and theorem statements; `all` audits every number.

**What happens.**
1. Inventory and consistency leads.
2. Statistical consistency.
3. Trace each number to its source.
4. Recompute in a scratch copy. **It asks before long or paid runs.**
5. Convention audit from tool source code.
6. Parameter validity.
7. Guards.
8. Report.

**Outputs** (`number_audit/<date>/`): `numbers.md` / `.json`, `conflicts.md`, `stats.md`, `trace.md`, `ledger.md` (provenance table), `report.md`, and `guards.json` next to the manuscript.

**Run the scripts directly.**
```bash
N=skills/number-audit/scripts/number_audit.py
python3 $N extract main.tex supplement.tex --out number_audit/today      # inventory + conflicts.md
python3 $N stats manuscript.docx --out number_audit/today                 # t/F/chi2/r/z p-values, k/n %, OR/RR/HR CIs
python3 $N trace number_audit/today/numbers.json --repo . --regions abstract,introduction,caption,table
python3 $N guard-init number_audit/today/numbers.json --out guards.json  # then fill "source" and "locator"
python3 $N guard-check guards.json                                        # exit code 1 on failure
```

Guard locators:
- JSON path: `metrics.err` or `runs[0].auc`;
- CSV cell: `row=model:B;col=auc` or `row=3;col=auc`;
- regex over a text file: `re:Final loss: ([0-9.]+)`;
- constant: `const:0.5`.

Use `"scale": 100` for percentages, and set `"decimals"` and `"thousands"` for the display. List corrected values that must never reappear under `"stale"`.

`guard-check` reports each entry as PASS, FAIL (with the value found), ANCHOR_MISSING (the sentence was rewritten), UNSOURCED, SOURCE_ERROR or STALE_PRESENT. Put it in a Makefile, pre-commit hook or CI. Do not guard wall-clock times.

### experiment-integrity

**What it does.** Checks that the code and procedures behind the results implement what the text claims, and that the design is not producing the result. It covers:
- pairing, seeds, splits and sample sizes;
- random draws inside conditions that desynchronize the scenarios;
- sentinel or fallback values reported as results;
- discretization artifacts;
- small samples that hide failures;
- instrumentation and order effects;
- leakage and multiple testing;
- misleading figures;
- holes in the project's own automated checks.

Every confirmed problem is quantified by a rerun and turned into a regression guard.

**Use it when** all automated checks pass and you want an adversarial pass, when a result looks too large or too clean, or before submission of any paper with code, simulations, measurements or backtests.

**Invoke.**
```text
/experiment-integrity <manuscript or report> <code/data directory> [--rounds 1|2]
/experiment-integrity paper.tex ./analysis --rounds 2
```

**What happens.**
1. **Claimed-design ledger.** Every methodological claim, with the code that should implement it.
2. **Static scan** (codes below).
3. **Claim-to-code verification** by reading the code and by instrumented runs in a scratch copy.
4. **Design checks** from the checklist: randomness, fallbacks, tails, numerics, measurement validity, statistics, figures.
5. **Impact.** Before/after numbers for each confirmed finding. **It asks before long or paid reruns.**
6. **Guards.**
7. **Report.**

`--rounds 2` repeats the attack after the fixes, aimed at the design and at the new guards.

**Outputs** (`integrity/<date>/`): `design_ledger.md`, `integrity_scan.md` / `.json`, `impact.md`, `report.md`, proposed patches.

**Run the scanner directly.**
```bash
python3 skills/experiment-integrity/scripts/integrity_scan.py ./analysis --out integrity/today
```

| Code | Pattern |
|---|---|
| S1 | Sentinel guard in a denominator (`x / max(d, 1e-12)`) |
| S2 | Constant returned on an edge-case branch of a function that otherwise computes (`if len(x) < 3: return 360`) |
| S3 | Swallowed exception (`except: pass`, `except: return 0`) |
| S4 | Missing values replaced by a constant (`fillna(0)`, `nan_to_num`) |
| R1 | Random draw inside a condition (`if cond and rng.random() < p`) |
| R2 | Random draw in only one branch of an `if` |
| R3 | Seed list per file (compare arms) |
| P1 | Number hard-coded in figure text |
| L1 | Preprocessing fitted before the train/test split |
| G1 | A check script that tests numbers by substring ("0.47" inside "10.47") |
| G2 | Shell pitfalls (`grep -c … \|\| echo 0`; paths without end delimiters) |

Python gets an AST-based scan; R, Julia, MATLAB and shell get a regex scan. Every hit is a lead to be read in context. The full checklist is in `skills/experiment-integrity/references/checklist.md`.

### cite-verify

**What it does.** Verifies references at two levels:
- **Metadata.** Authors, title, year, venue, volume, pages and DOI are checked against Crossref, DataCite, arXiv and Europe PMC. It also detects fabricated or missing entries, published preprints, retractions and errata, and undefined or unused keys.
- **Claim support.** It checks whether each cited work actually says what the citing sentence attributes to it.

**Use it when** checking a bibliography before submission, or a literature list compiled by AI or by hand.

**Invoke.**
```text
/cite-verify references.bib --tex main.tex       # BibTeX + the manuscript (only cited entries)
/cite-verify library.ris                         # Zotero / EndNote / Mendeley export
/cite-verify manuscript.docx                     # reference list in any citation style
/cite-verify survey.md                           # a literature survey list (converted to BibTeX first)
```

**What happens.**
1. **Metadata check.** DOI → Crossref, then DataCite; arXiv ID → arXiv; free-text entries → bibliographic search, with strict title matching.
2. **Manual review of every error.**
3. **Claim-support check** of claim-type citing sentences, by reading the sources.
4. **Report.**

**Outputs** (`refcheck/<date>/`): `report.md`, `results.json`, `corrected.bib` (proposals only), `contexts.md`, `claims.md`, `summary.md`.

**Run the scripts directly.**
```bash
R=skills/cite-verify/scripts/refcheck.py
python3 -I $R check references.bib --tex main.tex --out refcheck/today
python3 -I $R check library.ris --out refcheck/today
python3 -I $R check-list manuscript.docx --out refcheck/today
python3 -I $R contexts manuscript.docx --out refcheck/today
```

**Tips.**
- "Not found" is not proof of fabrication: books, theses, software and archives are often not indexed.
- Superscript citations in Word are not detected.

### novelty-audit

**What it does.** Tries to falsify novelty. Each contribution is split into result, technique and model, and restated in the terms of neighboring communities; for example, "a new model for the area under a glucose curve" is the trapezoidal rule. It then searches keywords, forward and backward citations, and concurrent work across OpenAlex, arXiv, Europe PMC and Zenodo, reads the candidates, and gives a verdict per contribution with the references that must be added.

**Scout mode** checks an idea before you invest in it, and keeps a watch list that reports only new items.

**Invoke.**
```text
/novelty-audit main.tex                                            # audit mode
/novelty-audit "independent certified reproduction of X" --mode scout
```

**What happens (audit).**
1. Contribution cards.
2. Translation into neighboring communities' terms.
3. Searches in four directions, all logged.
4. Reading by subagents that try to prove the work is not new, then verification by the main session.
5. Report: verdict per contribution, which community would see the result as standard, references to add, suggested wording, and what new result would strengthen novelty.

**What happens (scout).**
1. Planned results as cards.
2. Searches over the last year, including code and data deposits.
3. Verdict per planned result: done, in progress elsewhere, or open, with differentiation options.
4. A watch list. Whether to start or redirect is your decision.

**Outputs** (`novelty/<date>/`): `cards.md`, `hits.md`, `search_log.md`, `report.md`; for scout mode also `novelty/watch_queries.txt`, `watch_state.json`, `watch_log.md`.

**Run the scripts directly.**
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

**Query tips.**
- Quote phrases and join them with AND; bare words are joined with AND automatically.
- `--db` takes `openalex` (all fields, the default), `europepmc` (PubMed, PMC, bioRxiv, medRxiv), `arxiv`, `zenodo`, or `all`.

### venue-fit

**What it does.** Chooses where to submit from verified facts. It finds where similar work is published and profiles candidate venues. It then fills a fact sheet per shortlisted venue from official pages, each fact with URL, date checked and a verbatim snippet: scope, criteria, limits, review model, fees, preprint, AI and data policies, concurrent-submission and transfer rules, deadlines, anonymity, archival status. Finally it rates fit and proposes a primary venue, fallbacks, compatible parallel options and a deadline calendar.

**Use it when** choosing or changing the target venue, after a rejection, or before committing to a deadline.

**Invoke.**
```text
/venue-fit main.tex
/venue-fit manuscript.docx "Nature Communications, PLOS Biology, eLife" --budget 3000 --deadline 2027-01-31
```

**What happens.**
1. Intake: genre, constraints, history, novelty verdict.
2. Long list from neighbor venues and your candidates.
3. Profiles to screen a shortlist of 3–6.
4. Official fact sheets.
5. Fit assessment with reasons.
6. Plan: primary, fallbacks, parallel options, calendar, and actions before submission.

It never submits or contacts editors.

**Outputs** (`venue/<date>/`): `factsheets.md`, `plan.md`, and optionally an `.ics` calendar.

**Run the script directly.**
```bash
V=skills/venue-fit/scripts/venue_fit.py
python3 -I $V neighbors --query '"T-count" AND "lower bound"' --from 2019 --types journal,conference
python3 -I $V neighbors --seed 10.1103/PRXQuantum.4.020323 --from 2019
python3 -I $V profile "Quantum" "PRX Quantum" 2470-0029
python3 -I $V factsheet "PRX Quantum" "Quantum" --out venue/today/factsheets.md
```

**Tip.** OpenAlex profiles are screening pointers; fees, dates and policies must be confirmed on the official pages. In testing, OpenAlex listed a start year decades before one journal was founded.

### mock-review

**What it does.** Runs an independent mock review:
- 2–4 reviewer roles chosen by paper type (e.g. proofs, domain expert, statistics and design, reproducibility, reporting guidelines such as CONSORT, STROBE, PRISMA, ARRIVE or TRIPOD), plus an optional editor;
- each reviewer works on an isolated, SHA-256-pinned copy without your notes and reproduces numbers in its own scratch copy;
- cross-discussion that preserves the first-round text;
- verification of every claimed error by the main session;
- a joint report with P0/P1 priorities and a revision order.

**Use it when** self-checking before submission, diagnosing a rejection, or preparing to respond to referees.

**Invoke.**
```text
/mock-review ./paper "BMJ" --roles clinical,statistics,reporting
/mock-review . "Physical Review Letters" --roles proofs,domain,reproducibility --editor
```

**What happens.**
1. Intake, including the journal's review criteria.
2. Pack and pin. Check the manifest for files that look like private notes.
3. Choose the roles.
4. Independent reviews in parallel.
5. Cross-discussion.
6. Verification by the main session.
7. Joint report.
8. Later, `check-pin` before acting on line numbers. A second round uses new subagents.

**Outputs** (outside the repository, `~/mock_review/<name>-<date>/`): `pack/`, `work-<role>/`, `reports/`, `verification.md`, `joint_report.md`, `PIN.json`, `MANIFEST.md`.

**Run the script directly.**
```bash
P=skills/mock-review/scripts/review_pack.py
python3 $P pack --repo . --out ~/mock_review/paper-2026-10-29 --roles math,domain,stats --exclude "notes/*"
python3 $P check-pin ~/mock_review/paper-2026-10-29/PIN.json
```

In a git repository only tracked files are packed. Untracked notes, `CLAUDE.md`, working directories, `submission/` and `internal/` are left out by default.

### dead-end-ledger

**What it does.** Keeps an honest research ledger for a long-running goal: an open problem, an experiment that must work, a metric to improve, a hypothesis to test. The ledger records:
- a dated status line;
- graded results;
- evidence with its range or sample;
- ranked open targets;
- routes tried, with where each stopped and when it is worth reopening;
- a barrier index.

Before each new attempt, it checks the ledger for similar failed routes. Results are upgraded only after independent verification, and progress reports say only what the ledger supports.

**Invoke.**
```text
/dead-end-ledger research/LEDGER.md init      # create, or migrate an existing handoff document
/dead-end-ledger research/LEDGER.md before    # duplicate check before trying a new idea
/dead-end-ledger research/LEDGER.md record    # update after a session
/dead-end-ledger research/LEDGER.md report    # progress report from the ledger
```

| Status words | |
|---|---|
| Results | VERIFIED, UNVERIFIED, CONDITIONAL(H), PRELIMINARY, NEGATIVE, RETRACTED |
| Routes | FAILED, PARTIAL, SUPERSEDED, IN-PROGRESS, SUCCEEDED |

Field spellings such as PROVED-REVIEWED, REPLICATED, HEURISTIC and NULL are accepted.

**Run the script directly.**
```bash
G=skills/dead-end-ledger/scripts/ledger.py
python3 $G init research/LEDGER.md --goal "raise the bound from a to b unconditionally"
python3 $G search research/LEDGER.md "use a sieve over the fibration" --notes research/notes
python3 $G lint research/LEDGER.md --notes research/notes
python3 $G status research/LEDGER.md
```

## Command-line tools

| Script | Subcommands and purpose |
|---|---|
| `paper-polish/scripts/hedge_scan.py` | Metrics and flagged phrasing in title, abstract, introduction, conclusion and captions; `--summary` over many files |
| `paper-polish/scripts/exemplar_meta.py` | `venue`, `search`: find exemplars; `fetch`: verify metadata and fetch abstract and introduction (arXiv source or PMC XML; DOI, arXiv ID or PMID) |
| `number-audit/scripts/number_audit.py` | `extract`, `stats`, `trace`, `guard-init`, `guard-check` |
| `experiment-integrity/scripts/integrity_scan.py` | Static scan for sentinel, randomness, leakage, figure and check-script pitfalls |
| `cite-verify/scripts/refcheck.py` | `check` (BibTeX / RIS), `check-list` (free-text lists), `contexts` |
| `novelty-audit/scripts/lit_graph.py` | `resolve`, `search`, `citing`, `refs`, `recent`, `watch` over OpenAlex, arXiv, Europe PMC and Zenodo |
| `venue-fit/scripts/venue_fit.py` | `neighbors`, `profile`, `factsheet` |
| `mock-review/scripts/review_pack.py` | `pack`, `check-pin` |
| `dead-end-ledger/scripts/ledger.py` | `init`, `search`, `lint`, `status` |

Every script prints help with `--help`. Run the scripts that read downloaded content with `python3 -I`.

## Supported inputs

| Input | Formats |
|---|---|
| Manuscripts | `.tex` (following `\input` / `\include`), `.docx`, `.md`, `.txt`, `.pdf` (via `pdftotext`) |
| Section detection | LaTeX sectioning; IMRaD headings; numbered and all-caps headings; unheaded introductions (Nature style); structured abstracts |
| References | BibTeX; RIS; free-text reference lists in any citation style; LaTeX `thebibliography` |
| Citation contexts | `\cite` keys; numeric `[n]` citations; author–year citations |
| Statistics | Inline APA-style reports such as `t(23) = 2.45, p = .02`, `F(2, 45) = 3.21, p < .05`, `χ2(1) = 3.84, p = .05`, `r(46) = .32, p = .03`, `z = 1.96, p = .05`; `k of n (x%)`; OR / RR / HR with 95% CI |
| Code (integrity scan) | Python (AST); R, Julia, MATLAB, shell (regex) |

## Data sources and privacy

The scripts query only public services: [OpenAlex](https://openalex.org), [Crossref](https://www.crossref.org), [DataCite](https://datacite.org), [arXiv](https://arxiv.org), [Europe PMC](https://europepmc.org) (PubMed, PMC full text, bioRxiv, medRxiv) and [Zenodo](https://zenodo.org); `novelty-audit` can also use the GitHub CLI if it is installed. No personal information is sent.

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
- The statistics checker recognizes inline APA-style reports only; statistics in tables need a manual check.
- The integrity scan reads Python precisely and other languages approximately. It finds patterns, not bugs; design problems are found by the claim-to-code verification and the checklist.
- Subscription databases (Web of Science, Scopus, PsycINFO) are not queried; the skills hand such searches to the user. Many humanities sources are not indexed in any of the services above.
- Pattern scans and traces produce leads, not verdicts. The skills require each lead to be read in context.
- Mock reviews and editor simulations are performed by the same family of models. They test whether a contribution can be found and whether claims are supported; they do not predict editorial decisions.

## Repository layout

```text
skills/<name>/SKILL.md         procedure followed by Claude Code
skills/<name>/references/      detailed rules, checklists, templates and examples
skills/<name>/scripts/         standalone scripts
lib/                           shared modules: document reading, scholarly APIs, BibTeX/RIS, statistics
templates/SKILL_TEMPLATE.md    template for new skills
FAILURE_MODES.md               catalog of observed failure modes and candidate skills
install.sh                     installs the skills as symlinks
.claude-plugin/plugin.json     plugin manifest
```

## Extending the library

1. Record the failure mode and the observed evidence in [FAILURE_MODES.md](FAILURE_MODES.md). A new skill should address a failure that has actually occurred. The file also lists observed candidates that are not yet written.
2. Copy [templates/SKILL_TEMPLATE.md](templates/SKILL_TEMPLATE.md) to `skills/<name>/SKILL.md`. Write it in English, and add `references/` and `scripts/` as needed. Scripts locate `lib/` through `os.path.realpath(__file__)`.
3. Add a section to the [Skill guide](#skill-guide) in both README files.
4. Run `./install.sh` and test in a new session.

Case studies from other disciplines are welcome. The current evidence comes from the author's projects and has been anonymized.

## License

[MIT](LICENSE).
