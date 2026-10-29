---
name: dead-end-ledger
description: Use when pushing one research goal forward over a long period (any discipline — attacking an open problem or conjecture, getting an experiment or measurement to work, improving a metric of a model or method, testing a hypothesis), to record progress honestly in a research ledger. The ledger contains a precise one-line status sentence at the top; graded results (independently verified / unverified / conditional / preliminary / negative / retracted); evidence with its range or sample; open targets ranked by feasibility; routes tried (proof ideas, experimental protocols, analysis or model changes), each with where it got stuck and under what conditions it is worth reopening; and a barrier index. Before trying each new route, check the ledger for duplicates; update the ledger at the end of each session; upgrade a result only after independent verification (proof review, replicated experiment, re-run by someone else); tell the user only what the ledger supports. Also use whenever the user asks to "keep pushing", "solve X", "make this work", or "report progress", or repeatedly asks for the same goal.
argument-hint: "[ledger path LEDGER.md] [init|before|record|report]"
---

# dead-end-ledger: record research progress honestly, without re-treading dead ends

## The problem this skill addresses

When the user repeatedly asks to push the same goal forward, AI tends to fall into two patterns (see `FAILURE_MODES.md`, item 6):
1. **Sycophantic progress reporting**: presenting partial progress, a heuristic argument, an experiment that worked once, or a favorable random seed as "essentially solved", "just one small step away", or "a significant effect".
2. **Re-treading dead ends**: retrying an already-failed route under a different framing and stopping at the same place again. In mathematics this shows up as the same barrier; in experiments, as the same technical problem; in machine learning, as the same kind of change having no effect on the validation set.

Both patterns occur in every kind of research, for example:
- Mathematics: repeatedly trying a proof idea that has already been shown not to work;
- Laboratory: repeatedly optimizing, with the same kind of conditions, a reaction or measurement that is bound to give no result;
- Machine learning: taking a lucky one-time improvement as evidence that the method works;
- Social science: treating conclusions from an exploratory analysis as confirmed findings.

The author handled one long-running mathematical effort as follows; it can serve as an example:
- The user repeatedly asked to push a proven bound to the conjectured optimal value. The right response was to state honestly that "all routes reduce to the same unsolved proposition", and to maintain an index of failed routes marked "do not redo".
- The author's `HANDOFF.md` is a good ledger, and this skill uses it as its template: the status line at the top says "not reached"; it has a table of proven results, a table of numerical evidence with coverage ranges, open targets ranked by feasibility, and where each route stops.
- Opening each research note with a status declaration ("The requested estimate (15) has not been proved. No … is claimed.") is also a habit worth keeping.

## Hard rules

1. **State status only as the ledger records it.** In progress reports to the user, every "proved / achieved / works / significant" must correspond to a VERIFIED entry in the ledger. For unverified results, write "completed, not yet independently verified"; for conditional results, state the condition in the same sentence; mark preliminary results as preliminary.
2. **Check for duplicates before starting.** Run `ledger.py search` before every new route. If the route resembles a failed one, first write down "what is different this time, and how it gets past the recorded barrier". If you cannot write this, do not retry, and tell the user so honestly.
3. **Record failures too**, and record negative results as well. For every failed route, state the step or barrier where it stops, where the evidence is, and what new input would make it worth reopening.
4. **Upgrading to VERIFIED requires independent verification**; record the verifier and the date in the ledger:
   - Proofs: dispatch a subagent that reads only the proof, not the author's notes, to check it step by step, or use mock-review;
   - Experiments: independent replication (different batch, operator, or sample), or at least a recomputation from the raw data by someone else;
   - Computation or machine learning: a re-run from scratch by someone else or in a clean environment; multiple random seeds; evaluation on data not used for tuning.

   If verification finds an error, change the status to RETRACTED and record the reason; do not delete the entry.
5. **Open each note with a status declaration** that states clearly what the note establishes and what it does not.
6. Keep the ledger in the research directory, alongside the notes. Do not push or commit unless the user asks; if the repository has rules about what may be committed, follow them.
7. Talk to the user in the user's language; the ledger and notes follow the language of the existing material.

## Status words

| Applies to | Status | Meaning | Field-specific equivalents |
|---|---|---|---|
| Result | VERIFIED | Independently verified | Proof reviewed; experiment replicated; analysis re-run by someone else |
| Result | UNVERIFIED | Completed, not independently verified | Written-up proof; single experiment; single run |
| Result | CONDITIONAL(H) | Holds under condition H, with H written in the parentheses | Depends on a conjecture; depends on identification assumptions; holds only on a particular dataset |
| Result | PRELIMINARY | Preliminary result | Heuristic argument; pilot experiment; exploratory analysis; trend |
| Result | NEGATIVE | Tested; does not hold | Counterexample; negative result; change had no effect |
| Result | RETRACTED | Verification found an error; retracted (entry and reason kept) | — |
| Route | FAILED / PARTIAL / SUPERSEDED / IN-PROGRESS / SUCCEEDED | SUCCEEDED must link to an ID in the results table | Proof ideas, experimental protocols, analyses, model changes |

The script also accepts field-specific spellings such as PROVED-REVIEWED, PROVED-UNREVIEWED, REPLICATED, HEURISTIC, and NULL, and maps them automatically to the status words in the table above.

## Phase 0: Create or take over the ledger

- **Existing ledger** (`LEDGER.md`, or a document like `HANDOFF.md`): read it first, then run `ledger.py status` and `lint`. If the format differs, migrate it according to `references/ledger-format.md`, preserving the existing section-number pointers; tell the user before migrating.
- **No ledger**:
  ```
  python3 <skill-dir>/scripts/ledger.py init <research-dir>/LEDGER.md --goal "<precise, testable goal statement>"
  ```
  Then backfill known results, failed routes, and barriers from existing notes, lab records, and run logs. Every status entered while backfilling needs a source; mark anything uncertain as PRELIMINARY or UNVERIFIED, and do not err on the high side.
- **Make the goal statement testable.** For example:
  - "Improve the bound from a to b (unconditionally)";
  - "Reach a yield above 80%, reproducibly";
  - "Beat the strongest baseline on benchmark X by 2 points (mean over 5 seeds)".

  Do not write something like "improve the method", for which there is no way to tell whether it has been achieved.

## Phase 1: Before starting (before)

1. Write the new idea down in one paragraph: the route, the key steps, what you expect to obtain, and how success or failure will be judged. Write the criteria down in advance, so that results are not cherry-picked after the fact.
2. Check for duplicates:
   ```
   python3 <skill-dir>/scripts/ledger.py search LEDGER.md "<idea>" --notes <notes-dir>
   ```
3. Read the matching entries and note passages. If there is a similar FAILED route, write a "difference statement": what input this attempt uses that the earlier one did not, and why it can get past the barrier recorded in the "Stops at" column.
4. If you cannot write a difference statement, do not do it. Tell the user that this route has already been tried and where it got stuck, and offer directions in the ledger that have not been tried yet.

## Phase 2: Attempt

- Create a new note whose first paragraph is the status declaration (template in `references/ledger-format.md`).
- Leave a reproducible record of every computation, analysis, and experiment: scripts and commands, parameters, random seeds, samples, batches, instrument settings.
- Label every claimed conclusion with its level of evidence.

## Phase 3: Record (record)

Update the ledger at the end of every work session:
1. Routes table: outcome, where it stops, evidence, and under what conditions it is worth reopening.
2. Results table: enter new results with their actual status. Anything newly completed but not yet verified is always UNVERIFIED; enter negative results as NEGATIVE.
3. Evidence table: state what was tested, the range or sample covered, and the conclusion.
4. Barriers table: new barriers, or newly blocked routes for existing barriers.
5. Add a line to the log; **rewrite the status line at the top** with today's date, stating in one sentence what is now established and what is not.
6. Run `ledger.py lint LEDGER.md --notes <notes-dir>`. Resolve all Problems; for each strong assertion under "To check", confirm that what the note says agrees with the ledger.

## Phase 4: Upgrade after verification

- To upgrade an UNVERIFIED result, first obtain independent verification. The prompts are in `references/ledger-format.md`, Section 4. The verifier reads only the necessary material (the proof itself, the raw data and analysis code), not the author's notes or the ledger.
- The main session checks the verifier's conclusions: confirm each issue the verifier raises, one by one.
- If it passes, change it to VERIFIED and record the verifier and the date; if it has errors, change it to RETRACTED or back to UNVERIFIED, and record the problems.

## Phase 5: Report to the user (report)

Format (in the user's language):
1. **Status**: copy the status line from the top of the ledger verbatim.
2. **Changes this session**: new or changed results (with status words), failed routes (where they stop), new evidence (with range or sample).
3. **Distance to the goal**: explain it using the open targets and barriers in the ledger.
4. **Next steps**: directions in the ledger not yet tried, ranked by feasibility. Other options may also be offered: lowering the goal, settling for a conditional result, switching the experimental system, consulting an expert.

When the user asks for the same goal again and the ledger shows that the main routes have all failed:
- state the current situation and the barriers honestly;
- do not produce something that looks like success just to meet expectations (a derivation that looks like a proof, cherry-picked seeds, post hoc subgroups);
- offer the other options above, or propose a category of new idea that genuinely does not appear in the ledger, and run the Phase 1 duplicate check first.

For the reporting phrasebook, see `references/ledger-format.md`, Section 3.

## Final report to the user (concise, in the user's language)

The four parts of Phase 5, plus the paths to the ledger and to this session's note, and whether lint passed.
