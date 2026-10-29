---
name: proof-audit
description: Audit the proofs of a mathematical or theoretical manuscript before submission or before a result is reported as proved. Maps every theorem, lemma and proof and their dependencies (cycles, results without proofs, lemmas never used, undefined labels, results that silently depend on a conjecture or assumption, gap phrases such as "clearly" or "one can show", implicit constants); builds an obligation ledger and an assumption ledger; has independent subagents check each proof step by step without the authors' notes; runs numeric sanity checks; traces every formula fed to a solver or script back to the lemma that justifies it and requires an independent second encoding or an exact certificate; and checks effectivity and scope against how the results are stated in the abstract. Use for LaTeX manuscripts with proofs, computer-assisted proofs, or before upgrading a result to proved in a research ledger. Not for checking numbers against data (number-audit) or code against the described method (experiment-integrity).
argument-hint: "[main.tex] [supplement.tex] [--results thm:main,lem:key] [--depth map|full]"
---

# proof-audit: every step is written, every assumption is visible, every computation is traceable

## The problem this skill addresses

AI assistants produce and polish long proofs quickly. They are good at making a chain of estimates look complete, and poor at noticing which steps were never written. Computer assistance adds a second failure: a solver confirms a formula, and the confirmation is taken as confirmation of the mathematics that produced the formula.

The observed case (a theory manuscript, examined in a mock review and in independent reviews of its parts):
- **The assembly step was never written.** The headline theorem rested on a long chain of estimates assembled into a piecewise-linear formula, and a solver checked that formula. The assembly itself was never written out as a human-checkable proof.
- **Two solvers checked the same formula.** This validates the arithmetic but not the derivation of the formula from the lemmas.
- **Steps were only sketched.** Several lemmas carried unspecified constants and steps that were "only sketched".
- **A reduction was asserted without proof.** A continuum reduction, on which the solver check depended, was stated without a proof.
- **Other parts passed only after fixes.** Independent reviews of other parts returned VALID only after fixes were applied.
- **An interpretation was withdrawn.** An earlier interpretation of numerical evidence was withdrawn after review.

None of this is visible from the statements alone. It shows up only when every theorem is reduced to its obligations and each obligation is checked by someone who has not seen the authors' notes.

## Hard rules

1. **Never edit the manuscript.** Write outputs to `proof_audit/<YYYY-MM-DD>/`. Inside a git repository, add `proof_audit/` to `.git/info/exclude` and tell the user. Propose fixes as separate text, never as edits to the source.
2. **A step is checked only when someone checked it.** "Plausible", "standard" and "the solver says sat/unsat" are not verdicts. Every obligation gets a verdict from an explicit check: written verification, a counterexample search, an exact certificate, or a reference to a precise published statement (theorem number and edition).
3. **Independence.** Step-check subagents read only the proof under review and the definitions and results it cites. They do not see author notes, ledgers, earlier reviews or this skill's working files.
4. **Main-session verification.** Every GAP or INVALID verdict is re-checked by the main session before it is reported. Every critical finding states the innocent explanations it ruled out (a notation convention, a result proved elsewhere in the paper, a cited theorem).
5. **Long computations and new software need the user's go-ahead.** Estimate the runtime first, run in a scratch directory, and hand long jobs over with an ETA instead of polling. Subagents do not install solvers or packages; a check that needs one is reported as not run until the user approves the installation.
6. **Unchecked means unchecked.** Report what was not checked, explicitly. "No problems found" applies only to what was checked.
7. Talk to the user and write reports in the user's language. Mathematics stays in LaTeX.

## Phase 0: Intake

- The source: the LaTeX entry files, the supplement, and the code or certificates for computer-assisted parts.
- **Scope.** Which results to audit. The default is the results stated in the abstract and introduction, plus everything they depend on. `--results` can name labels.
- **Depth.** `map` (Phases 1–3 only: structure and ledgers) or `full` (all phases, the default).
- **External results relied on**, with the exact statement and source of each.
- **Known status.** What the authors already consider proved, conditional or open, if a research ledger exists (`dead-end-ledger`).

## Phase 1: Proof map and obligation ledger

```
python3 <skill-dir>/scripts/proof_map.py main.tex [supplement.tex] --out proof_audit/<date>
```

`proof_map.md` lists every theorem-like statement, its proof or proofs, and the dependency graph built from `\ref`/`\cref`/`\eqref` inside proofs. Proofs are recognized in several forms: a following proof environment, a `Proof of Theorem~\ref{x}` proof elsewhere, sections titled "Proof of …", and inline "Proof." paragraphs. Labels from `\externaldocument` (xr) are followed.

Leads by category:

| Category | What to do with it |
|---|---|
| (a) dependency trees | Starting point for the obligation ledger |
| (b) cycles | Check each edge at its location: a real use is circular; a mention of a consequence is not |
| (c) provable results without a proof | Needs a proof, a precise citation, or "immediate from X" |
| (d) conditional chains | If real, every statement of the result must carry the condition; if a pointer, note it |
| (e) undefined labels | Broken references; possibly a deleted lemma that is still used |
| (f) results never used | Dead weight, or an implicit dependency to make explicit |
| (g) gap phrases in proofs | Each becomes an obligation: "clearly", "similarly", "one can show", "standard argument", "sketch" |
| (h) constants and effectivity | Unspecified constants, O(1), sufficiently large, non-effective |
| (i) macros with different bodies | Possible notation drift |

The script does not see references typed by hand ("Theorem 3" without `\ref`) or logical dependencies that are not referenced at all. Read the proofs for those.

Then write `obligation_ledger.md` (format in `references/obligation-ledger.md`): for each audited result, every obligation it rests on. Obligations include lemmas used, cases, inequalities and their parameter regimes, limits and interchanges, measurability or convergence conditions, external results, and computations. Each obligation records where it is discharged and its status.

## Phase 2: Assumption ledger

For each audited result:
- **The assumptions stated** in the theorem.
- **The assumptions actually used** in its proof chain, including those of the lemmas it calls and of the external results it cites. Watch in particular for stronger hypotheses smuggled in by a lemma: independence, a compact support, a growth condition, a non-degeneracy, a parameter range.
- **Conditional chains.** Results that depend on a conjecture, an unproved hypothesis or a numerical observation must say so in every place they are stated: abstract, introduction, conclusion, figure captions. Cross-check with the claim ledger of `paper-polish` if one exists.

## Phase 3: Notation and scope

- **Notation table.** Each symbol, its meaning, and where it is defined. Flag symbols with two meanings, symbols used before definition, and redefined macros (category i).
- **Scope.** Compare the object and the regime of each theorem with how the result is described in the abstract and introduction: general versus restricted class; all parameters versus asymptotic regime; worst case versus typical. A narrower theorem described broadly is an overclaim to report.

## Phase 4: Independent step checks (subagents)

- Split the obligation ledger into groups, typically one lemma or one theorem's assembly step per group. Start one subagent per group in a single message, using the prompt in `references/obligation-ledger.md`.
- Each subagent reads only the proof and the cited definitions and results. It returns one verdict per step:
  - VALID;
  - VALID WITH FIX (with the fix);
  - GAP (what is missing);
  - INVALID (the first failing step, with a counterexample or the failing estimate).

  It also lists what it did not check.
- **Main session.** Re-check every GAP and INVALID verdict. For each critical finding, record which innocent explanations were ruled out. Downgrade findings that do not survive. Never report a subagent's verdict unverified.

## Phase 5: Numeric sanity checks

In a scratch directory, never inside the repository:
- Evaluate stated inequalities at sample parameter values, including boundary regimes and the smallest admissible parameters.
- Search for counterexamples to finite or small cases by brute force where feasible.
- Recompute explicit constants. Use exact rational arithmetic (`fractions`, `sympy`) or interval arithmetic where rounding could matter.
- Record commands, versions and outputs.

These checks can refute a step; they never prove one.

## Phase 6: Computer-assisted parts

For every computation a proof relies on (SMT or LP solvers, enumerations, certified numerics, symbolic algebra):
1. **Traceability.** Every constraint, formula or case fed to the program maps to the lemma or inequality that justifies it. Untraceable inputs are GAPs.
2. **Independent encoding.** A second, independent encoding of the statement, written from the paper and not from the first encoding. A second solver on the same formula checks only the arithmetic.
3. **Certificates over verdicts.** Prefer artifacts that can be checked independently: rational Farkas or LP dual certificates, interval-arithmetic bounds, exact enumeration logs with hashes.
4. **Sanity queries.** Check that the encoding is not vacuous: satisfiable sanity queries must be satisfiable, the target must fail when a key hypothesis is removed, and boundary cases must behave as stated.
5. **Reproducibility record.** Tool versions, input hashes, commands and outputs. Note any continuous-to-discrete reduction and where it is proved.

## Phase 7: Effectivity and constants

- For each audited result: are the constants explicit, computable in principle, or ineffective? Where do they depend on the parameters?
- At practical parameter values, is the statement non-vacuous? If the headline result is asymptotic and vacuous at the parameters of interest, say so, and point to `number-audit` for any numbers evaluated from it.

## Phase 8: Report

Write `proof_audit/<date>/report.md` in the user's language, conclusions first:
1. **Per audited result.** Status (VERIFIED, VERIFIED WITH FIXES, GAP, INVALID, or CONDITIONAL on …), open obligations, conditional dependencies, and the proposed fixes or missing lemmas.
2. **Confirmed issues**, ordered by severity, each with the location, the evidence, the innocent explanations ruled out, and the minimal fix.
3. **Scope and statement mismatches** between the theorems and the abstract and introduction.
4. **Computer-assisted parts.** Traceability status, the independent encoding, certificates, and the reproducibility record.
5. **Not checked**, with reasons.
6. **Commands** to reproduce the map, the numeric checks and the computations.

When the audit is done for a research ledger (`dead-end-ledger`), record each verified result as VERIFIED, with the verifier and the date. Results with open GAPs stay UNVERIFIED. Conditional results become CONDITIONAL(<IDs>), and INVALID results become RETRACTED with the reason.

## Final report to the user (concise, in the user's language)

- For each audited result, the status in one line.
- The confirmed gaps and errors, one sentence each, with the minimal fix.
- Conditional dependencies that the abstract or introduction does not state.
- What was not checked, and the path of the full report.
