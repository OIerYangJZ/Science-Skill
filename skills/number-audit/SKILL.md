---
name: number-audit
description: Audit every number in a paper before submission or preprint posting (any discipline; the manuscript can be LaTeX, Word, Markdown, or PDF). Recompute whether test statistics and p values agree, whether k/n matches percentages, and whether confidence intervals of ratio measures are internally consistent; inventory all numbers in the text; check whether the same symbol keeps the same value throughout and whether hand-copied numbers have drifted from data macros; trace key numbers in the abstract, introduction, tables, and figure captions to the data or script that produced them, and recompute them in a scratch copy; check parameter conventions of external tools against the tool's source code (e.g., the definition of an error norm); check whether figures and tables still use parameters the text has ruled out; then install guards that recompute key numbers from their sources on every build so they cannot drift again. Use when the user asks to check numbers, reproduce values, or verify that data and text agree, or before finalizing, submitting, or responding to reviewers. Not for checking mathematical proofs themselves.
argument-hint: "[manuscript .tex/.docx/.md/.pdf ...] [--repo data and code directory] [--scope key|all]"
---

# number-audit: every number in the paper can be traced and recomputed

## The problem this skill addresses

When AI writes or edits a manuscript, numbers drift silently. In empirical fields, the most common cases are test statistics that do not match their p values, percentages that do not match sample sizes, and numbers that differ between the abstract and the tables. The following three types actually occurred in the author's own theoretical manuscripts (see item 3 of `FAILURE_MODES.md` in the repository root):

1. **Adopting a tool's convention unchecked.** The text interpreted the precision parameter of an external synthesis tool under one error definition, but the source code of the version used applies a different distance. The two differ by a constant factor, so every "measured" number was shifted as a whole. The repository's own data had shown the sign all along: the ratio of measured error to the nominal parameter was consistently about 0.5.
2. **Two sets of values for one symbol.** The worked example in the introduction and the main theorem used two different definitions, so the same quantity differed by a factor of about 4 between them; an editor would see this on page 2.
3. **Ruled-out parameters still in the main figure.** The text already gave a counterexample showing that a certain constant must be larger, yet the main figure and table still used the old value to plot a "conditional lower bound".

There were also optimality claims of the form "other parameter choices can reach at most X", which a single actual parameter sweep exceeds.

## Hard rules

1. **Do not modify the manuscript or the data.** Write outputs to `number_audit/<YYYY-MM-DD>/` inside the repository; if it is a git repository, add `number_audit/` to `.git/info/exclude` and tell the user. Write proposed changes only as a patch or a list; edit the original manuscript only after the user agrees.
2. **Always recompute in a scratch copy.** Use `git worktree add /tmp/na-<date> HEAD` or copy to `/tmp`; never run scripts or analysis pipelines that may overwrite data in the original directory (this applies equally to Python, R, Stata, MATLAB, and Excel). For anything that needs a server or a long computation (e.g., `ssh school-server`), ask the user first.
3. **Scripts only give leads; conclusions come from recomputation or reading source code.** A trace hit only means "this value appears there". A number counts as confirmed only after you verify that it is the same quantity, with the same settings and conventions.
4. **For external tools, the source code is authoritative on conventions**, not the documentation or memory. Read the installed source of the pinned version (`pip show -f <pkg>`, then read the source files), and cross-check against data already in the repository.
5. Label every finding with a status: confirmed / mismatch / stats-inconsistent / orphan / convention-issue / superseded-parameter / unverifiable (with the reason stated). Do not report "no problem found" as "correct".
6. Talk to the user and write reports in the user's language; manuscript text in proposed changes stays in the manuscript's language (English, or whatever language the manuscript is written in).

## Phase 0: Intake

- Identify the entry files: the main manuscript and supplementary material; there may be several, each a separate document. Supported formats are `.tex`, `.docx`, `.md`, `.txt`; `.pdf` requires `pdftotext`. Locations in Word manuscripts are given as paragraph numbers `¶n`.
- Identify the directory that holds the data and code, and where the data, scripts, generated tables (e.g., `generated/`), and frozen data (e.g., `data/frozen/`) each live. If there is only a manuscript with no data or code, run Phases 1, 2, 2b, and 5, mark trace and recomputation as unverifiable, and ask the user to provide the data.
- Identify exclusions: large raw data, old copies of the manuscript, submission packages, third-party code.
- Scope: `key` (default) audits only numbers in the abstract, introduction, conclusion, figure captions, tables, and theorem statements; `all` audits every number.
- Read the repository's README or reproduction instructions, plus `requirements.txt` and lock files, and record the pinned tool versions.

## Phase 1: Inventory

```
python3 <skill-dir>/scripts/number_audit.py extract main.tex [supplement.tex] --out number_audit/<date>
```

Outputs:
- `numbers.md`: the location, region, associated symbol, and context of each number;
- `numbers.json`;
- `conflicts.md`: different values of the same symbol (look at specific symbols first; for single-letter variables the differences are usually just different settings), and hand-copied data-macro values (these hand-copied values do not update when the data are regenerated).

By default, small integers, years, section numbers, lengths, and the like are skipped; add `--all` when needed.

## Phase 2: Consistency

Work through `conflicts.md` item by item:
- Different values under different settings (two precisions, two examples): confirm that the text states the setting.
- Genuine contradictions (different values under the same setting): record as mismatch and state which value is correct (the definition used by the theorem is authoritative).
- Hand-copied macro values: recommend referencing the macro instead.

In addition, check manually:
- Whether the same quantity agrees across the abstract, introduction, tables, figure captions, and cover letter, including the digits after rounding (2.41 and 2.4 are both acceptable; 2.41 and 2.50 are not).
- Whether ratios, percentages, and "about N times" statements match their numerators and denominators.

## Phase 2b: Statistical consistency (mandatory for empirical papers)

```
python3 <skill-dir>/scripts/number_audit.py stats main.docx [supplement.docx] --out number_audit/<date>
```

The script runs three kinds of checks (similar to statcheck):
- recompute p values from the reported test statistic and degrees of freedom for t, F, χ², r, and z, allowing for rounding of both;
- check "k of n (x%)" against the percentage;
- check whether point estimates of OR, RR, and HR fall inside their confidence intervals, and whether the intervals are roughly symmetric on the log scale.

Results are classified as:
- GROSS: the significance decision is flipped; must be investigated;
- INCONSISTENT: the numbers do not match;
- one-tailed?: consistent only under a one-tailed test; confirm whether the text states that the test is one-tailed;
- CHECK: needs manual confirmation;
- ok.

The script recognizes only APA-style inline reports in the text, such as `t(23) = 2.45, p = .02`. Statistics in tables, other reporting formats, and p values given without a test statistic all need a manual check. Also verify manually:
- whether sample sizes agree across the abstract, methods, Table 1, and the flow diagram;
- whether the group sizes sum to the total;
- whether the same result has the same value in the abstract, main text, and tables;
- whether means and standard deviations are plausible (e.g., within the scale range).

## Phase 3: Trace

```
python3 <skill-dir>/scripts/number_audit.py trace number_audit/<date>/numbers.json --repo <repo> \
    --regions abstract,introduction,conclusion,caption,table,theorem --exclude "submission/*" "arxiv/*"
```

`trace.md` sorts each number into one of four classes:
- orphan: not found in the repository;
- text-only: appears only in other documents, with no computational source;
- traced: 1–5 data or script sources;
- ambiguous: the value is common in the repository.

Candidate sources are ranked by "data > code > documents", then by word overlap with the context.

For each key number:
1. **traced**: open the candidate source and confirm that it is the same quantity, with the same settings, parameters, and conventions.
2. **ambiguous**: use the context (variable names, file names, settings) to find the true source; if you cannot find it, treat the number as an orphan.
3. **orphan and text-only**: search the code for the computation (variable names, formulas) to find the script that produced it. For derived numbers with no script (e.g., worked examples in the introduction), recompute them in `number_audit/<date>/recompute.py` using the definitions in the text.
4. Record each number's provenance, recomputation command, and result in `ledger.md` (format below).

## Phase 4: Recompute

- Run the generating scripts in the scratch copy and compare the results with the values displayed in the text, at the displayed precision.
- **Recompute worked examples using the definitions the theorem uses**. This is how the factor-of-about-4 contradiction in Case A was found.
- **Run a parameter sweep for optimality and extremal claims**, e.g., "other parameters give at most X" or "the optimal choice is …"; record the sweep range and the best value found.
- For intervals, ratios, and multiples, recompute the endpoints from the raw data.

## Phase 5: Convention audit

Go through the checklist in `references/conventions.md` item by item. Core steps:
1. List every external tool, library, and dataset whose output feeds numbers in the paper, together with the pinned versions.
2. For each tool, write down the convention the text claims. For example: "F1 is macro-averaged", "standard errors are cluster-robust", "doses are normalized by body weight", "the synthesis tool's ε is the up-to-phase operator distance".
3. Read the source code of that version and find the actual definition of the acceptance criterion or error function; then cross-check with repository data, e.g., the ratio of measured error to nominal ε.
4. When the convention does not match, compute all affected numbers (text, tables, figures, abstract) and list them as convention-issue.

## Phase 6: Parameter validity

- For every parameter value used in figures, tables, and captions (constants, thresholds, cutoffs), search the text to see whether it has been ruled out, superseded, or marked as insufficient, e.g., "requires c ≥", "counterexample", "fails", "superseded".
- List as superseded-parameter any ruled-out parameter that still appears in a main figure or table as a "valid bound".
- For values that depend on a conjecture or assumption, check whether the caption states this premise.

## Phase 7: Guards (keep the numbers from drifting again)

An audit fixes the numbers once; a rerun, a new data version or an edit can break them again. Every project behind this library ended up building some "numbers come from data" mechanism; this phase builds one deliberately.

1. **LaTeX manuscripts: generate macros from data.** Have the analysis write a file of macros (for example `generated/numbers.tex` with `\newcommand{\MainEffect}{0.47}`), input it in the preamble, and use the macros in the text. `extract` already reports hand-typed copies of macro values (`conflicts.md`).
2. **Every format: a guard file checked on each build.**
   ```
   python3 <skill-dir>/scripts/number_audit.py guard-init number_audit/<date>/numbers.json --out guards.json
   # fill "source" and "locator" for each entry you want enforced:
   #   JSON path  "metrics.err"              CSV cell   "row=model:B;col=auc"  or  "row=3;col=auc"
   #   regex      "re:Final loss: ([0-9.]+)" constant   "const:0.5"
   #   "scale": 100 for percentages, "decimals" and "thousands" control the display
   # list corrected values that must never reappear under "stale"
   python3 <skill-dir>/scripts/number_audit.py guard-check guards.json     # exit code 1 on failure
   ```
   `guard-check` recomputes each value from its source with decimal ROUND_HALF_UP rounding, which avoids the inconsistent rounding of binary floats. It looks for the value near its anchor words, with digit boundaries on both sides, so "0.47" is not found inside "10.47". Each entry is reported as:
   - `PASS`;
   - `FAIL`, with the value actually found;
   - `ANCHOR_MISSING`: the sentence was rewritten; update the anchor;
   - `UNSOURCED`;
   - `SOURCE_ERROR`;
   - `STALE_PRESENT`: a corrected value reappeared.
3. Wire `guard-check` into the build: a Makefile target, a pre-commit hook, or CI. Run it after the analysis and before the PDF is built. If the pipeline chains freshness checks, keep their order fixed.
4. Do not guard wall-clock times or other values that change on every run. Report them as orders of magnitude.
5. Guard numbers in figure titles and annotations by generating them from the same result files (see experiment-integrity, scan code P1).

## Phase 8: Report

Write `number_audit/<date>/report.md` (in the user's language), with conclusions first:

1. **Must fix**: mismatch, stats-inconsistent (especially GROSS), convention-issue, superseded-parameter, and orphans in key locations. For each, give the location, current value, correct value, evidence, and the other affected locations.
2. **Should fix**: hand-copied macro values, inconsistent rounding, values without a statement of their setting.
3. **Confirmed**: the count, plus the full provenance table `ledger.md`.
4. **Unverifiable**: list the reasons, e.g., needs a server, missing data, script does not run.
5. Guards installed (Phase 7): how many entries are sourced, and how to run `guard-check`.
6. Reproduction commands.

Format of `ledger.md`:

| id | location | displayed value | status | source (file:line / script + command) | recomputed value | convention / setting | notes |
|---|---|---|---|---|---|---|---|

Optional: also write a patch `fixes.patch`, or a location-by-location replacement table, for the user to review before it is applied.

## Final report to the user (concise, in the user's language)

- How many must-fix issues there are, with one sentence on each.
- How many key numbers are confirmed and how many are unverifiable.
- Paths to the report and the provenance table.
- Decisions the user needs to make, e.g., whether to allow recomputation on a server.
- Whether guards are in place, and the command that runs them.
