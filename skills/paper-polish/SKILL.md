---
name: paper-polish
description: Polish a paper's title, abstract, introduction, Fig. 1 caption, and cover letter before submission (or after a desk reject) so that an editor sees the novelty and significance at a glance, without overclaiming. Works across disciplines (theory, experiment, observational studies, clinical, computational and machine learning, social science, etc.); the manuscript can be LaTeX, Word, Markdown, or PDF. Workflow — first run an augmented survey that retrieves well-written published papers of the same genre in the target journal, dissects each one along four dimensions (research question, prose, narrative emphasis, abstract and introduction structure), and compares them point by point with this manuscript; then rewrite based on a claim ledger; finally have an independent subagent play the editor in a blind test. Use when the user asks to polish the paper or revise the abstract or introduction, or worries that "the editor cannot see the novelty". Not for grammar-level minor edits.
argument-hint: "[manuscript path] [target journal] [--mode full|survey|rewrite|check]"
---

# paper-polish: let the editor see the novelty at a glance, without overclaiming

## The problem this skill addresses

When AI polishes a paper, it fails in two opposite directions.

1. **Defensive writing (the main problem).** Typical symptoms: hedges stacked layer upon layer; standalone "we do not claim / this does not imply" sentences; the concession first, the result after; the main result buried in the 7th sentence of the abstract, and given as a formula; a list of 6 equally weighted contributions; the gap written as "well known anecdotally" without naming prior work; long passages on version history. After reading the first two pages, the editor still cannot say "what the new result is and why it matters", and desk rejects the paper.
2. **Overclaiming in the opposite direction.** When asked to "make it stronger", the AI then writes conditional results as unconditional, numerical evidence as theorems, and correlation as causation; overuses law / first / universal / optimal / significant; or leads with a multiple computed against an unnamed strawman baseline. Referees will catch these.

The goal of this skill is **calibration**: state each claim once, in the strongest wording the evidence allows, and state its scope once, positively, in the result sentence. This does not mean deleting qualifiers; it means putting them where they belong and making them specific.

The real cases this is based on are in `references/case-studies.md`: one manuscript was rejected twice by editors for "lack of clarity"; for another, a mock review criticized both too many caveats and overclaim. Both cases come from quantum information, but the patterns they illustrate are cross-disciplinary. **Every standard of "good or bad" is set by exemplars of the same genre in the target journal, not by the conventions of any one field.** For example, medical journals require structured abstracts, and observational studies must use associational rather than causal wording; these are field norms, not defensiveness.

## Hard rules

1. **Do not modify the original manuscript.** Write all outputs under `polish/<YYYY-MM-DD>/` in the manuscript's directory. If it is a git repository, first check `.git/info/exclude` and `.gitignore`, add `polish/` to `.git/info/exclude` (local only, reversible), and tell the user. If the repository's CLAUDE.md or memory states that the manuscript is frozen or that internal material must not be committed to a public repository, follow those rules.
2. **Do not change the mathematics, do not change the data, do not add conclusions.** For every number in the new text, record its source in the notes (`file:line` or data file) and re-check it.
3. **Exemplars must be real.** Each must have a DOI, arXiv ID, or PMID resolved by `scripts/exemplar_meta.py`. Do not list references from memory. Volume, pages, and authors follow what the API returns; check the user's own survey files too (8 errors were once found in one).
4. **Label every conclusion of the simulated editor and simulated reviewers "inferred"**; never present them as the opinions of real editors.
5. **Separate presentation problems from substantive problems.** Presentation problems can be fixed by rewriting; substantive problems need new results (e.g., the main conclusion is a direct application of a standard method, the effect size is too small, the sample or controls are insufficient, the baseline is a strawman). Tell the user about substantive problems honestly; do not cover them with wording.
6. Talk to the user and write reports in the user's language; manuscript text stays in the manuscript's language (English, or whatever language the manuscript was originally written in).
7. **You will write defensively too.** After rewriting, you must run the scan script and self-check against the ledger (Phase 6). Do not add disclaimers to the new draft that the original manuscript did not have.

## Modes

| Mode | What it does | When to use |
|---|---|---|
| `full` (default) | Phase 0–7 | First polish of this manuscript |
| `survey` | Phase 0–4, survey report only | To see the gaps first, without changing the manuscript yet |
| `rewrite` | Reuses the existing `survey_report.md` and `exemplars/` in the working directory, runs Phase 5–7 | The survey has already been done |
| `check` | Only the Phase 1 scan and the Phase 7 blind test | Final check before submission |

If the user does not specify a mode, run `full`.

## Phase 0: Intake

Establish the following. Do not ask about anything that can be inferred from the manuscript and the repository; usually only the target journal needs to be asked.

- **Manuscript entry file**: the scripts read `.tex`, `.docx`, `.md`, and `.txt` directly; PDF requires `pdftotext` installed locally, otherwise ask the user to export Word or text. If there are several entry files (preprint version, journal version), ask which one to use.
- **Target journal.** It determines the exemplar pool and the editorial standards; the user decides it.
- **Genre**: theoretical or mathematical result; method or algorithm; computation or simulation; experiment (laboratory experiment, randomized controlled trial); observational study (cohort, case-control, cross-sectional, survey); machine learning or data-driven research; qualitative research; systematic review or meta-analysis; review or perspective. The genre determines the evidence level (see `references/claim-calibration.md`) and the reporting guidelines to follow (e.g., CONSORT, STROBE, PRISMA, and the journal's requirements for structured abstracts).
- **Existing material**: rejection letters, reviewer comments, the user's own survey files, earlier surveys. Quote rejection reasons verbatim in the report.
- **The user's one-sentence "novelty"** (if the user is willing to give one). If not, that is fine; Phase 5 will distill it and ask the user to confirm.

Then create the working directory: `polish/<date>/`, containing `exemplars/`.

## Phase 1: The manuscript's "editor's view" and baseline measurement

Before deciding whether to send a manuscript out for review, an editor usually reads only the title, the abstract, the first one or two pages of the introduction, Fig. 1 and its caption, and the cover letter.

1. Run the scan:
   ```
   python3 <skill-dir>/scripts/hedge_scan.py <manuscript .tex/.docx/.md/.pdf> --json polish/<date>/scan_before.json > polish/<date>/scan_before.md
   ```
   The script reports metrics for the abstract, introduction, and conclusion (paragraph count, word count, sentence count, inline formula count, the sentence or paragraph in which the main result first appears, hedges, defensive-pattern hits and their locations, causal wording and uses of "significant"), as well as caption length, and it flags structured abstracts. It only provides leads; the final judgment requires a full read.
2. **Build the claim ledger** (format in `references/claim-calibration.md`). List every claim from the abstract, introduction, conclusion, and cover letter; go back to the body to find its support (theorem number, figure or table, statistical analysis, data file); record the evidence type and preconditions; and judge whether the current wording is too weak, appropriate, or too strong.
3. **Read through and record the structure**: in which sentence of the abstract the main result first appears, and whether in words or as a formula; in which paragraph of the introduction it appears; what form the contribution list takes; in how many places the text states the scope, and whether the wording is positive or negative; how long the Fig. 1 caption is; whether any terms are used before they are defined.

## Phase 2: Augmented survey, finding exemplars

The full procedure is in `references/exemplar-protocol.md`; the key points follow.

- **Pool A, target-journal exemplars.** Well-written articles of the same genre from the target journal or journals of the same tier in the last 5 years: highly cited, editor-recommended (Editors' Suggestion, Editor's Choice, etc.), award-winning, or specified by the user. This is the main pool; take 15–30 papers, split into 3–4 groups by genre.
- **Pool B, nearest-neighbor work.** 5–10 papers that editors and reviewers will compare this manuscript against (same problem or same technique), from any journal. Use them to write a gap that "names prior work", and also for a novelty audit: has prior work already obtained the result, and are there standard techniques this manuscript should acknowledge?
- **Pool C, editorial standards.** Verbatim excerpts from the target journal's official about, scope, and criteria pages.
- **Search.** Use `exemplar_meta.py search` (based on OpenAlex, covers all disciplines, can filter by journal and year, sorts by citations or relevance); run several queries with different keyword sets, and combine them with WebSearch, field-specific databases (see `references/exemplar-protocol.md`), and the user's survey files.
- **Verify and download.**
  ```
  python3 -I <skill-dir>/scripts/exemplar_meta.py fetch <DOI / arXiv ID / PMID ...> --out polish/<date>/exemplars --intro
  ```
  This produces one `<slug>.md` per paper (metadata, verification source, abstract, introduction) and saves the raw introduction separately: from arXiv source as `<slug>.intro.tex`, from PMC open-access full text as `<slug>.intro.txt`. Entries with status NOT FOUND must not be used.
- **Text sources.** For abstracts, prefer the version the publisher deposited with Crossref. For introductions, try in order: arXiv source (physics, mathematics, computer science, etc.); PMC open-access full text (biomedicine, life sciences, and many open-access journals); the publisher's open-access page; a PDF provided by the user. Record which version you read. WebFetch returns a model summary, not the original text; do not use it for verbatim quotes or measurements.
- If the sample has fewer than 8 papers, say so honestly and weaken the conclusions accordingly.
- Pool B gets only a lightweight audit here. When a formal novelty verdict is needed, or the survey finds that "the main result may be a standard result", switch to `novelty-audit`.

## Phase 3: Per-paper dissection (in parallel)

- Group the papers by genre and dispatch one subagent per group, launching them concurrently in the same message. Each subagent follows the analysis card template in `references/exemplar-protocol.md` and fills each paper's card into the "Analysis card" section of the corresponding `.md`.
- **Subagents read only the exemplars, not this manuscript**, so that their conclusions are not biased by it.
- After the subagents return, spot-check 2–3 papers in the main session, verifying that the verbatim quotes in the cards match the original text.
- Measure all exemplars with the same yardstick:
  ```
  python3 <skill-dir>/scripts/hedge_scan.py polish/<date>/exemplars/*.md --summary > polish/<date>/exemplar_stats.md
  ```

## Phase 4: Comparison and diagnosis; write `survey_report.md`

Write the report in the user's language, with the conclusions first. Compare the four dimensions the user named, one by one. In each cell, state two things: what the exemplars do (cite 1–2 by name), and what this manuscript does (give line numbers). For numerical values, give the exemplars' median and range.

1. **Research question**: how the question is posed, what shape the answer takes (a number or bound, an effect size, yes or no, a mechanism, a method), what the object of study is, whether the gap names prior work, and what the practical significance of the result is (what it constrains theoretically, or what it means for clinical practice, policy, engineering, or follow-up research).
2. **Prose**: sentence length, hedge density, active or passive voice, verb strength, formula and symbol density, caption length, whether terms are explained before their first use.
3. **Narrative emphasis**: the one-sentence conclusion (slogan), the headline number and its baseline, where the novelty lies (result, method, or modeling), the relation to prior work, how the scope is stated, how space is allocated.
4. **Abstract and introduction**: metrics in `references/exemplar-protocol.md`.

Also write:

- **Defensive-pattern diagnosis table**, listing category, original sentence, line number, why it weakens the novelty, and how to fix it. Category definitions are in `references/defensive-patterns.md`.
- **Novelty risks** (from Pool B): results prior work has already obtained, standard techniques this manuscript uses, references that should be added.
- **Priority table** with three columns: problem, rewriting suffices, new results needed.
- **2–4 exemplar templates that can be adopted**: name them, and write out the sequence of functions of each sentence in their abstracts.
- **Survey method and limitations**: the sample contains only successfully published papers; measurement conventions; which versions were read.

## Phase 5: Novelty spine (the only confirmation point before rewriting)

Write the 5 sentences an editor should take away within 30 seconds. Give each sentence in the manuscript's language with an explanation in the user's language, and mark the corresponding ledger entry:

1. **Result**: what the new result is. In words, not a formula.
2. **Gap**: name one piece of prior work and the one thing it lacks.
3. **Stakes**: why it matters — whom it constrains, or which measurable quantity or which decision it changes.
4. **Headline number**: at most one, with the comparator in the same sentence. The comparator must be the current best method, the standard of care, a commonly used control, or the production default setting, not a strawman you built yourself; empirical studies must include uncertainty (confidence intervals, etc.).
5. **Scope**: one sentence, positively worded, attached to the result.

How to position the novelty is the author's decision. In `full` mode, pause here once and ask the user to confirm or revise the spine; continue directly only if the user explicitly says "no confirmation needed".

## Phase 6: Rewrite

**Outputs** (all written in the working directory; do not touch the original manuscript):

- `abstract_intro.tex` (or the manuscript's original format): the new abstract and introduction. Optionally also 3–5 title candidates, the Fig. 1 caption, a conclusion paragraph, and a cover letter.
- `polish_notes.md`, containing:
  - a structure comparison table: paragraph count, word count, main-result position, hedge count, etc., for the original and the new draft;
  - a provenance table for every number (re-checked);
  - **"Deliberately changed statements (author to confirm)"**: list every place that changes the scope or strength of a claim, changes how the baseline is named, or replaces a term;
  - places not changed this time that must be updated in step when merging into the body (body definitions, figures, numbering, etc.);
  - alternative titles and the rationale for each.

**Writing rules** (details in `references/defensive-patterns.md` and `references/claim-calibration.md`):

- **Abstract.** The format follows the journal's rules first, e.g., structured-abstract labels and word limits. On top of that, use the exemplar statistics (`exemplar_stats.md`) to decide the number of sentences, the position of the main result, and the symbol density. Principles that hold across disciplines: the result appears early, in words; at most one headline number, with its comparator stated; the scope attached to the result sentence; end on significance, not on limitations. The statistics from 26 physics-journal exemplars in Case A (1 paragraph, main result in sentences 2–4, no more than 3 symbols) are only an example from one field and must not be used as defaults.
- **Introduction.**
  - Paragraph 1 covers the field's problem or real-world motivation; do not open with a definitional sentence such as "X is not only a Y".
  - Paragraphs 2–3 state the gap, naming prior work.
  - The main result appears within the first 4 paragraphs.
  - How to write the contributions depends on the exemplars' conventions: most journals state 2–3 in prose; some fields (e.g., computer science conferences) customarily list contributions at the end of the introduction, in which case list them, but still with a clear hierarchy, never 6 equally weighted items.
  - State the scope in one paragraph, positively worded.
  - Do not write version history; it belongs in the preprint server's version notes or the cover letter.
- **Verb strength is determined by the evidence**; choose by the ledger's evidence level (see `references/claim-calibration.md`): prove / show / establish; find / observe / measure; is associated with (observational studies); conjecture / suggest. Put qualifiers only where they are needed, state the specific conditions, and do not use vague modal verbs. **Uncertainty statements required by field norms** (no causal claims in observational studies, labeling pilot studies as pilots, confidence intervals) **are not defensiveness; keep them**. What should be removed is disclaimers and dilution around this paper's own contribution.
- **State the source of the technique directly.** For example: "The proof is a standard X argument; what is new is Y.", or "We use the established X assay; what is new is its application to Y." This deflects a reviewer's "this is just a standard result" objection better than evasion does.
- **For results with small numbers or high costs, explain whom they constrain.** Turn the weakness into operational meaning; do not avoid it.

**Self-check**:

1. Run `hedge_scan.py` on the new draft and compare it with the before scan and the exemplar distribution. For each category above the exemplar range, address every hit or state the reason.
2. Check for overclaiming item by item against the ledger: whether conditional conclusions are written as unconditional; whether observational results use causal wording (causes, leads to, effect of); whether "significant" has a corresponding test; whether words such as law, first, optimal, universal, orders of magnitude, breakthrough have a corresponding theorem or data with a comparator.
3. Every symbol in the new abstract is defined or can be deleted; every number is in the provenance table. If there are many numbers, or the text and data may be out of sync, run `number-audit` first. Verify newly added references with `cite-verify`.

## Phase 7: Blind editor test (independent subagents)

Prompts and procedure are in `references/blind-editor-test.md`.

- **Editor test.** Dispatch one subagent and give it only the title, abstract, introduction, and Fig. 1 caption of the two versions (the original and the new draft, randomly labeled A and B, without saying which is new), plus the Pool C journal standards. Have it play an editor at the target journal, with a 5-minute reading limit. For each version, it must give: the main result in one sentence, why it matters, the closest prior work, and whether to send out for review or reject, with reasons. Finally, it compares which version is clearer.
- **Overclaim referee.** Dispatch another subagent, give it the new draft and the full body text but not our notes, and have it find every sentence that goes beyond what the body supports.
- **Verification.** Verify every issue a subagent raises in the main session, and confirm or reject it before revising.
- **Pass criteria**: the editor subagent's one-sentence restatement of the new draft matches sentence 1 of the spine, and the overclaim review has no confirmed issues. If it fails, iterate once; if it still fails, report honestly.
- When a full review from multiple angles is needed (not just the editor's view and the overclaim check), use `mock-review`.

## Final report to the user (concise, in the user's language)

- 3–5 conclusions: what the most important gaps are, and what was changed.
- Paths of the output files.
- Changes that need the author's confirmation.
- Problems that rewriting alone cannot fix (if any).
- Blind test results, labeled as inferred.
