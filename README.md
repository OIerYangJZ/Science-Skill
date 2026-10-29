# Science-Skill

**English** | [简体中文](README.zh-CN.md)

Claude Code skills that counter the recurring failure modes of AI-assisted research.

AI assistants help with research writing, analysis and checking, but they fail in predictable ways:
- When asked to polish a manuscript, they hedge until the contribution disappears; when asked to make it stronger, they overclaim.
- They let numbers drift away from the data.
- They write code that no longer does what the paper says.
- They produce long proofs whose steps were never checked, and take a solver's answer as proof of the formula fed to it.
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
- [Skill guide](#skill-guide): [paper-polish](#paper-polish) · [number-audit](#number-audit) · [experiment-integrity](#experiment-integrity) · [proof-audit](#proof-audit) · [cite-verify](#cite-verify) · [novelty-audit](#novelty-audit) · [venue-fit](#venue-fit) · [mock-review](#mock-review) · [dead-end-ledger](#dead-end-ledger)
- [Quick prompts without Claude Code](#quick-prompts-without-claude-code)
- [Using the skills as gates in automated research pipelines](#using-the-skills-as-gates-in-automated-research-pipelines)
- [Command-line tools](#command-line-tools)
- [Supported inputs](#supported-inputs)
- [Data sources and privacy](#data-sources-and-privacy)
- [Limitations](#limitations)
- [Related projects](#related-projects)
- [Repository layout](#repository-layout) · [Tests](#tests) · [Extending the library](#extending-the-library) · [License](#license)

## Skills at a glance

| Skill | Failure mode addressed | Main outputs |
|---|---|---|
| [`paper-polish`](#paper-polish) | Defensive writing that hides the novelty from editors, and the opposite swing to overclaiming | Exemplar survey from the target journal; gap analysis; claim ledger; rewritten title, abstract and introduction; blind editor test |
| [`number-audit`](#number-audit) | Numbers that drift from data and code; misread tool conventions; statistics that do not add up | Number inventory; consistency leads; source trace; statistical consistency checks (p-values, GRIM, SD bounds, change arithmetic); audit report; guards that keep numbers tied to data |
| [`experiment-integrity`](#experiment-integrity) | Code that does not implement the design the text describes; experiment designs and evaluations that manufacture results | Claimed-design ledger; static code scan; confirmed findings with before/after impact; regression guards |
| [`proof-audit`](#proof-audit) | Proof steps that were never written or checked; solver results taken as proof of the formula | Proof map with dependency leads; obligation and assumption ledgers; independent step checks; traceability of computer-assisted parts |
| [`cite-verify`](#cite-verify) | Wrong or fabricated bibliographic metadata; citations that do not support their sentences | Per-entry verification against Crossref, DataCite, arXiv and Europe PMC; proposed corrections; claim-support check |
| [`novelty-audit`](#novelty-audit) | Searching only for literature that confirms novelty; being pre-empted after investing | Contributions restated in neighboring communities' terms; multi-source searches with a log; novelty verdicts; scout mode and watch list |
| [`venue-fit`](#venue-fit) | Choosing a venue from impressions | Where similar work is published; venue profiles; official fact sheets with URLs and dates; fit assessment; submission plan and calendar |
| [`mock-review`](#mock-review) | Mock reviews that are not independent, not verified, or tied to a moving manuscript | Isolated, version-pinned review pack; independent reports; cross-discussion; verification; prioritized joint report; quick kill-argument mode |
| [`dead-end-ledger`](#dead-end-ledger) | Sycophantic progress reports and repeated attempts at failed routes | Research ledger with graded results, routes, dependencies and barriers; duplicate check and idea card before new attempts; stop rules; lint and dependency graph |

Typical order:
- **Before starting a project:** `novelty-audit --mode scout`.
- **During research:** `dead-end-ledger`; `experiment-integrity` once the analysis code stabilizes; `proof-audit` before a theoretical result is recorded as proved; `mock-review --quick` to test a framing.
- **Before submission:** `novelty-audit` → `venue-fit` → `paper-polish` → `experiment-integrity` and/or `proof-audit` → `number-audit` → `cite-verify` → `mock-review`.

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
- **Outputs** go to a dated working directory next to the manuscript (`polish/`, `number_audit/`, `integrity/`, `proof_audit/`, `refcheck/`, `novelty/`, `venue/`) or, for mock reviews, outside the repository. In a git repository the directory is added to `.git/info/exclude`.
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
2. **Measure** the editor-facing sections: where the main result first appears, hedges, causal wording, unsupported "significant", work-report narrative ("we first tried… then we…"), local weaknesses stated as global ("our method may not generalize"), symbol density, caption length. It also builds the claim ledger.
3. **Find 15–30 exemplars** in the target journal (Pool A), 5–10 nearest prior works (Pool B), and the journal's official criteria (Pool C). Every exemplar is verified by DOI, arXiv ID or PMID.
4. **Analyze the exemplars** in parallel with subagents that do not see your manuscript.
5. **Write `survey_report.md`.** It compares research question, prose, narrative emphasis, and abstract and introduction structure, and separates presentation problems from problems that need new results.
6. **Novelty spine.** Five sentences: result, gap, stakes, headline number, scope. **It stops here for your confirmation.**
7. **Rewrite** into new files. Every experiment is introduced by the question it answers, weaknesses are stated where they were observed, and every number gets a provenance entry. Every change of claim strength or scope is listed for you to approve. Calibration never removes results: failed conditions, the planned primary metric and needed limitations stay.
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
- `hedge_scan.py` codes: D1 disclaimers, D2 concession first, D4 diluted contribution, D5 modal hedges, D6 vague gap, D8 version history, D10 ownerless passive, D12 filler, D13 "not X but Y", D15 work-report narrative, D16 local weakness stated as global; O, OC, OS possible overclaims; S scope qualifiers. Definitions and fixes: `skills/paper-polish/references/defensive-patterns.md`.
- For a quick pass in any chat assistant, see [Quick prompts](#quick-prompts-without-claude-code).

### number-audit

**What it does.** Audits every number in the manuscript:
- inventories them;
- flags symbols with conflicting values and hand-typed copies of data macros;
- recomputes p-values from reported test statistics, k/n percentages and ratio confidence intervals;
- checks whether means and percentages are possible for integer data of the stated n (GRIM), whether SDs fit the scale (Bhatia–Davis bound), whether stated changes match their endpoints ("from 200 to 150, a 40% reduction"), and flags "outperforms" claims whose ± intervals overlap;
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
python3 $N stats manuscript.docx --out number_audit/today                 # p-values, k/n %, CIs, GRIM, SD bounds, changes
python3 $N stats survey.docx --out number_audit/today --bounds 1,7 --items 4   # scale of 4 items scored 1-7
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

`stats` options: `--bounds lo,hi` gives the range of a bounded scale for the SD check (percentages and proportions are detected automatically); `--items k` tells GRIM that each score is the mean of k integer items. GRIM is skipped when n × items is too large for the reported decimals to constrain it. Every CHECK row is a lead: a GRIM failure can also mean that n differs for that variable, or that the scores are not integers.

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
- evaluation validity: ground truth produced by the method under test, scores normalized by the method's own statistics, metrics described but never computed, placeholder data on result paths, LLM judges without validation, selective reporting, ablations that change more than one thing;
- misleading figures;
- holes in the project's own automated checks.

Every confirmed problem is quantified by a rerun and turned into a regression guard. A finding is reported as confirmed only after the innocent explanations are ruled out (they are listed), and each finding states what could be observed: T (text only), S (source code read) or R (rerun).

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
| X1 | Placeholder or synthetic data on a result path (random values assigned to `scores` or `results`; `dummy` or `placeholder` strings; `TODO` markers outside tests) |
| X2 | Metric function (accuracy, F1, AUC, error …) defined but never called |

Python gets an AST-based scan; R, Julia, MATLAB and shell get a regex scan. Every hit is a lead to be read in context. The full checklist is in `skills/experiment-integrity/references/checklist.md`.

### proof-audit

**What it does.** Audits the proofs of a mathematical or theoretical manuscript:
- maps every theorem, lemma and proof and the dependencies between them;
- flags cycles, results without proofs, lemmas never used, undefined labels, results that silently depend on a conjecture or assumption, gap phrases ("clearly", "one can show", "standard argument") and implicit constants;
- builds an obligation ledger (every step a result rests on) and an assumption ledger (hypotheses stated versus hypotheses actually used);
- has independent subagents check each proof step by step, without the authors' notes; the main session re-checks every GAP or INVALID verdict;
- runs numeric sanity checks that can refute a step;
- for computer-assisted proofs, traces every constraint fed to a solver to the lemma that justifies it, and asks for an independent second encoding or an exact certificate (a second solver on the same formula checks only the arithmetic);
- compares the scope of each theorem with how the abstract and introduction describe it.

**Use it when** a theoretical result is about to be reported as proved (in a paper or in the research ledger), before submitting a paper with proofs, or when a proof relies on computation. **Not for** checking numbers against data (`number-audit`) or code against the described method (`experiment-integrity`).

**Invoke.**
```text
/proof-audit main.tex supplement.tex
/proof-audit main.tex --results thm:main,lem:key        # audit these results and their dependencies
/proof-audit main.tex --depth map                       # structure and ledgers only, no step checks
```

**What happens.**
1. **Intake:** scope (by default the results stated in the abstract and introduction), depth, external results relied on.
2. **Proof map and obligation ledger.**
3. **Assumption ledger:** stated versus used hypotheses; conditional chains that must be stated wherever the result is.
4. **Notation and scope.**
5. **Independent step checks** by subagents, one per lemma or assembly step; verdicts VALID, VALID WITH FIX, GAP or INVALID. Every critical finding lists the innocent explanations ruled out.
6. **Numeric sanity checks** in a scratch directory, with exact arithmetic where rounding matters.
7. **Computer-assisted parts:** traceability, independent encoding, certificates, sanity queries, reproducibility record. **It asks before long computations.**
8. **Effectivity and constants**, then the **report**: a status per result (VERIFIED, VERIFIED WITH FIXES, GAP, INVALID, CONDITIONAL on …), the minimal fixes, and what was not checked.

**Outputs** (`proof_audit/<date>/`): `proof_map.md` / `.json`, `obligation_ledger.md`, `assumption_ledger.md`, `notation.md`, `report.md`.

**Run the script directly.**
```bash
python3 skills/proof-audit/scripts/proof_map.py main.tex supplement.tex --out proof_audit/today
```

The map follows `\ref`, `\cref`, `\eqref` and `\autoref` inside statements and proofs, recognizes proofs placed elsewhere ("Proof of Theorem~\ref{…}", "Proof of …" sections, inline "Proof." paragraphs), and follows `\externaldocument` labels. It does not see references typed by hand ("Theorem 3") or dependencies that are never referenced; a mention of a result in prose can create a false cycle, so every edge carries its location for checking. LaTeX only.

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

**Quick mode** (`--quick`) takes minutes instead of hours. One fresh subagent writes the strongest rejection memo it can (at most 200 words, at most three kill arguments, each with a location and evidence). Another fresh subagent defends each argument from the paper alone: REBUTTED (with a quote), FIXABLE (with the minimal change) or STANDS. The main session verifies what is not cleanly rebutted. A rebutted argument still means the answer is not visible enough.

Optionally, one reviewer role can run on a model from another family, if you have one available. Sending an unpublished manuscript to another provider shares it with that provider, so the skill asks you first, every time.

**Use it when** self-checking before submission, diagnosing a rejection, or preparing to respond to referees. Use the quick mode while the paper is still changing, or to test a new framing.

**Invoke.**
```text
/mock-review ./paper "BMJ" --roles clinical,statistics,reporting
/mock-review . "Physical Review Letters" --roles proofs,domain,reproducibility --editor
/mock-review ./paper "Nature Communications" --quick
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

**Outputs** (outside the repository, `~/mock_review/<name>-<date>/`): `pack/`, `work-<role>/`, `reports/`, `verification.md`, `joint_report.md` (or `quick_report.md`), `PIN.json`, `MANIFEST.md`.

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

Before each new attempt, it checks the ledger for similar failed routes and writes an idea card with a falsifiable success criterion. Results and targets list what they depend on, so a retracted lemma or an unproved conjecture propagates to everything built on it. Results are upgraded only after independent verification, and progress reports say only what the ledger supports. Stop rules (budget, when to pivot, review date) are set at the start and checked after every session.

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
| Routes | FAILED (the idea does not work), BLOCKED (could not be carried out: compute, bug, access, time; not evidence against the idea), INCONCLUSIVE (carried out, but does not decide), PARTIAL, SUPERSEDED, IN-PROGRESS, SUCCEEDED |

Field spellings such as PROVED-REVIEWED, REPLICATED, HEURISTIC and NULL are accepted, and so are TECH-FAIL, ERROR or STALLED (read as BLOCKED) and MIXED or UNDECIDED (read as INCONCLUSIVE).

**Dependencies.** The Results and Open targets tables have a "Depends on" column with IDs (`R1, T3`). `graph` prints the dependency tree and reports missing IDs, cycles, results that rely on something RETRACTED, NEGATIVE or FAILED, and VERIFIED results whose dependencies are not all VERIFIED (they should be CONDITIONAL). It also lists the targets that are ready to attempt.

**Run the script directly.**
```bash
G=skills/dead-end-ledger/scripts/ledger.py
python3 $G init research/LEDGER.md --goal "raise the bound from a to b unconditionally"
python3 $G search research/LEDGER.md "use a sieve over the fibration" --notes research/notes
python3 $G lint research/LEDGER.md --notes research/notes     # format, statuses, evidence paths, graph problems; exit 1 on problems
python3 $G graph research/LEDGER.md                            # dependency tree, problems, ready targets; exit 1 on problems
python3 $G card --id X7 --out research/notes/X7.md --ledger research/LEDGER.md   # idea card before a new route
python3 $G status research/LEDGER.md
```

## Quick prompts without Claude Code

[`prompts/calibrated-writing-en.txt`](prompts/calibrated-writing-en.txt) and [`prompts/calibrated-writing-zh.txt`](prompts/calibrated-writing-zh.txt) are short instructions for any chat assistant that edits a manuscript: result first, verbs that follow the evidence, no added disclaimers or dilution, field-required qualifiers kept, weaknesses named where they were observed, experiments introduced by their question, no evidence removed, nothing invented, and a list of every changed claim at the end. Paste one before the text. They are a lightweight subset of `paper-polish`: no exemplar survey, no claim ledger, no blind test.

## Using the skills as gates in automated research pipelines

Agent pipelines that run literature survey, ideation and experiments in a loop fail in the same ways as interactive work, only faster. The skills can serve as gates between stages:

| Pipeline stage | Gate | What it prevents |
|---|---|---|
| Literature survey | `novelty-audit --mode scout`; `cite-verify` on every literature list the agent compiles | Ideas that are already done; fabricated or misattributed references |
| Ideation (idea graph) | `dead-end-ledger`: `search` before each new idea, an idea card with a falsifiable criterion, "Depends on" edges, `graph` for ready targets, stop rules | Re-running failed routes; ideas built on retracted or unproved results; open-ended loops |
| Experiment outcome | Ledger route statuses: SUCCEEDED, NEGATIVE / FAILED, INCONCLUSIVE, and BLOCKED for technical failures | Treating a crash or timeout as evidence against an idea, or an undecided result as support |
| Before a result counts | `experiment-integrity` on the code; `proof-audit` for theoretical claims; `number-audit` guards on reported values | Results produced by the pipeline's own bugs, sentinels, leakage or unchecked proof steps |
| Writing and review | `paper-polish`, `cite-verify`, `mock-review --quick` per iteration, full `mock-review` before submission | Defensive or inflated drafts; unverified review claims |

Machine-checkable gates (non-zero exit code on failure): `number_audit.py guard-check`, `ledger.py lint` and `ledger.py graph`, `review_pack.py check-pin`. The other scripts produce leads that an agent or a person must read; `refcheck.py` writes `results.json` with ERROR and WARN issues per entry. The skills' consent rules still apply inside a pipeline: long or paid runs and anything sent to an outside service need the user's approval.

## Command-line tools

| Script | Subcommands and purpose |
|---|---|
| `paper-polish/scripts/hedge_scan.py` | Metrics and flagged phrasing in title, abstract, introduction, conclusion and captions; `--summary` over many files |
| `paper-polish/scripts/exemplar_meta.py` | `venue`, `search`: find exemplars; `fetch`: verify metadata and fetch abstract and introduction (arXiv source or PMC XML; DOI, arXiv ID or PMID) |
| `number-audit/scripts/number_audit.py` | `extract`, `stats` (`--bounds`, `--items`), `trace`, `guard-init`, `guard-check` |
| `experiment-integrity/scripts/integrity_scan.py` | Static scan for sentinel, randomness, leakage, figure, check-script, placeholder-data and unused-metric pitfalls |
| `proof-audit/scripts/proof_map.py` | Theorem and proof map of LaTeX sources with dependency, gap-phrase, constant and notation leads |
| `cite-verify/scripts/refcheck.py` | `check` (BibTeX / RIS), `check-list` (free-text lists), `contexts` |
| `novelty-audit/scripts/lit_graph.py` | `resolve`, `search`, `citing`, `refs`, `recent`, `watch` over OpenAlex, arXiv, Europe PMC and Zenodo |
| `venue-fit/scripts/venue_fit.py` | `neighbors`, `profile`, `factsheet` |
| `mock-review/scripts/review_pack.py` | `pack`, `check-pin` |
| `dead-end-ledger/scripts/ledger.py` | `init`, `search`, `lint`, `graph`, `card`, `status` |

Every script prints help with `--help`. Run the scripts that read downloaded content with `python3 -I`.

## Supported inputs

| Input | Formats |
|---|---|
| Manuscripts | `.tex` (following `\input` / `\include`), `.docx`, `.md`, `.txt`, `.pdf` (via `pdftotext`) |
| Section detection | LaTeX sectioning; IMRaD headings; numbered and all-caps headings; unheaded introductions (Nature style); structured abstracts |
| References | BibTeX; RIS; free-text reference lists in any citation style; LaTeX `thebibliography` |
| Citation contexts | `\cite` keys; numeric `[n]` citations; author–year citations |
| Statistics | Inline APA-style reports such as `t(23) = 2.45, p = .02`, `F(2, 45) = 3.21, p < .05`, `χ2(1) = 3.84, p = .05`, `r(46) = .32, p = .03`, `z = 1.96, p = .05`; `k of n (x%)`; OR / RR / HR with 95% CI; `M = 3.48, n = 15` and `x% (n = 28)` (GRIM); `mean ± SD`; "from A to B, a C% / C-fold / C-point change" |
| Proofs | LaTeX theorem-like environments (including `\newtheorem` and `\declaretheorem`), proof environments, `\ref`-family references, xr `\externaldocument` |
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
- The proof map reads LaTeX only, and only sees dependencies that are written as references. Step checks by subagents are careful readings, not formal verification.
- The integrity scan reads Python precisely and other languages approximately. It finds patterns, not bugs; design problems are found by the claim-to-code verification and the checklist.
- Subscription databases (Web of Science, Scopus, PsycINFO) are not queried; the skills hand such searches to the user. Many humanities sources are not indexed in any of the services above.
- Pattern scans and traces produce leads, not verdicts. The skills require each lead to be read in context.
- Mock reviews and editor simulations are performed by the same family of models. They test whether a contribution can be found and whether claims are supported; they do not predict editorial decisions.

## Related projects

Other open projects address neighboring problems; several are larger or more automated. Science-Skill is narrower: each skill targets one failure mode that was observed in practice, ships scripts that measure or verify rather than only instructions, and works across disciplines.

- [ARIS (Auto-Research-In-Sleep)](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep): Markdown skills for autonomous machine-learning research, with cross-model review loops, idea discovery and experiment automation. Science-Skill can serve as the verification gates inside such a loop (see [above](#using-the-skills-as-gates-in-automated-research-pipelines)).
- [Anti-Autoresearch](https://github.com/wanshuiyin/Anti-Autoresearch): reviewer-side integrity forensics for papers produced by automated research, with a deterministic verdict. Science-Skill works on the author's side, before submission, and turns confirmed problems into fixes and guards.
- [anti-defensive-writing-Skill](https://github.com/Adkid-Zephyr/anti-defensive-writing-Skill) and [anti-defensive-writing](https://github.com/Kiterlin/anti-defensive-writing): writing principles and prompt packs against defensive academic prose. `paper-polish` addresses the same problem by calibrating against exemplars from the target journal and a claim ledger, which also guards against the swing to overclaiming; `prompts/` offers a lightweight version.
- [K-Dense scientific agent skills](https://github.com/K-Dense-AI/scientific-agent-skills): a large library of skills that give agents access to scientific tools, databases and analyses. It helps agents do science; Science-Skill checks what they produce. The two are complementary.
- [academic-research-skills](https://github.com/Imbad0202/academic-research-skills): a research → write → review → revise → finalize workflow suite for Claude Code. Science-Skill is not a workflow; its skills are checks that can be inserted at any stage of one.

## Repository layout

```text
skills/<name>/SKILL.md         procedure followed by Claude Code
skills/<name>/references/      detailed rules, checklists, templates and examples
skills/<name>/scripts/         standalone scripts
lib/                           shared modules: document reading, scholarly APIs, BibTeX/RIS, statistics
templates/SKILL_TEMPLATE.md    template for new skills
FAILURE_MODES.md               catalog of observed failure modes and candidate skills
prompts/                       calibrated-writing prompts for use without Claude Code
tests/run_tests.py             regression tests on synthetic fixtures with planted errors
install.sh                     installs the skills as symlinks
.claude-plugin/plugin.json     plugin manifest
```

## Tests

```bash
python3 tests/run_tests.py            # offline and deterministic, about one second
python3 tests/run_tests.py --online   # also queries Crossref, OpenAlex and arXiv
```

The fixtures in `tests/fixtures/` are synthetic and contain planted errors: an impossible mean, an SD above its bound, a wrong percentage change, a p-value that does not match its statistic, defensive phrasing, a random draw inside a condition, a sentinel return, placeholder data, a dependency cycle in a ledger, a circular proof, a retracted dependency, and a fabricated reference. Each test checks that the planted errors are reported and that the clean controls next to them are not.

## Extending the library

1. Record the failure mode and the observed evidence in [FAILURE_MODES.md](FAILURE_MODES.md). A new skill should address a failure that has actually occurred. The file also lists observed candidates that are not yet written.
2. Copy [templates/SKILL_TEMPLATE.md](templates/SKILL_TEMPLATE.md) to `skills/<name>/SKILL.md`. Write it in English, and add `references/` and `scripts/` as needed. Scripts locate `lib/` through `os.path.realpath(__file__)`.
3. Add a section to the [Skill guide](#skill-guide) in both README files.
4. Add a fixture with planted errors to `tests/`, run `python3 tests/run_tests.py`, then run `./install.sh` and test in a new session.

Case studies from other disciplines are welcome. The current evidence comes from the author's projects and has been anonymized.

## License

[MIT](LICENSE).
