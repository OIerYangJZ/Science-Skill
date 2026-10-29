# proof-audit reference: ledgers, step-check prompt, computer-assisted checklist, verdicts

## Verdict definitions

Step-level verdicts, used by subagents and by the main session:

| Verdict | Meaning | Required content |
|---|---|---|
| VALID | The step follows from the stated hypotheses, earlier steps and cited results, with every inference checkable by a reader at the paper's level | Nothing more; optionally the key inference |
| VALID WITH FIX | The conclusion holds, but the written step is wrong or incomplete in a repairable way (a wrong constant, a missing case, an index shift, a hypothesis that must be added to a lemma) | The fix, precise enough to insert, and whether the fix changes any statement |
| GAP | The step may be true, but it is not established by what is written: "clearly" over a nontrivial estimate, a sketched argument, an uncited "standard" result, an unproved reduction, a solver input not traced to a lemma | What is missing, and what would close it (a lemma statement, a citation with theorem number, a computation) |
| INVALID | The step is false as written, or it does not follow and cannot be repaired locally | The first failing step, with a counterexample, a failing parameter value, or the estimate that goes the wrong way |

Result-level status (Phase 8):

| Status | Meaning |
|---|---|
| VERIFIED | Every obligation in the result's closure is VALID, discharged by a precise citation, or covered by a checked certificate |
| VERIFIED WITH FIXES | As above once the listed fixes are applied; no fix changes the statement |
| CONDITIONAL on X | Verified, but the closure contains a conjecture, an assumption or a numerical observation X |
| GAP | At least one obligation is GAP |
| INVALID | At least one obligation is INVALID and no alternative route is known |
| NOT CHECKED | Outside scope or depth; say why |

A result is never VERIFIED because a solver returned the expected answer. What can be verified is the chain: lemma, then traced constraint, then encoding, then certificate.

## Obligation ledger (`obligation_ledger.md`)

One table per audited result. Every row is a single checkable claim.

```markdown
### Theorem <label> (<file:line>)

Statement (short): ...
Stated hypotheses: H1 ..., H2 ...

| # | Obligation | Kind | Where discharged | Depends on | Check | Verdict | Notes |
|---|---|---|---|---|---|---|---|
| O1 | Lemma <label> gives bound B(n) for n ≥ n0 | lemma use | proof of Lemma <label>, file:line | H1 | subagent S2 | VALID | |
| O2 | Case split covers all residues mod 4 | case analysis | proof of Thm, para 2 | — | main session | VALID WITH FIX | case r = 3 missing; same argument works |
| O3 | Interchange of sum and limit | analytic | "clearly", file:line | O1 | subagent S1 | GAP | needs dominated convergence; dominating function not given |
| O4 | Assembled inequality (piecewise-linear) holds on the region R | computation | solver run, script path | O1–O3, reduction O5 | Phase 6 | GAP | constraints 7–9 not traced to a lemma |
| O5 | Continuous problem reduces to finite grid | reduction | asserted, file:line | — | — | GAP | no proof given |
| O6 | External result: <author, year, Theorem n> applies | citation | ref [k] | its hypotheses A, B | main session | VALID | hypothesis B checked at file:line |
```

Kind values: lemma use, case analysis, inequality, limit or interchange, measurability or integrability, existence or construction, uniqueness, reduction, computation, citation, definition check, gap phrase.

Add one row for every gap phrase (category g of `proof_map.md`) inside the closure. Add one row for every computation, even small ones done "by hand" in the text.

## Assumption ledger (`assumption_ledger.md`)

```markdown
| Result | Stated hypotheses | Hypotheses actually used (with source) | Smuggled? | Conditional on | Stated as conditional in abstract / intro / conclusion? |
|---|---|---|---|---|---|
| Thm <label> | f continuous, n ≥ 2 | f continuous; f Lipschitz (Lemma <label>, used at file:line); n ≥ 3 (Lemma <label>) | yes: Lipschitz, n ≥ 3 | — | — |
| Cor <label> | none | Conjecture <label> via Thm <label> (file:line) | — | Conjecture <label> | abstract: no; intro: yes; conclusion: no |
```

- "Smuggled" means that a hypothesis used in the closure is neither stated in the result nor implied by its stated hypotheses.
- Conditional on a numerical observation counts as conditional.
- If a chain reported by `proof_map.py` turns out to be a pointer (a comparison or a remark, not a use), record it with the note "pointer, not used" and the location.

## Notation table (`notation.md`)

```markdown
| Symbol / macro | Meaning | Defined at | Also used as | Issue |
|---|---|---|---|---|
| \eps | small parameter in (0, 1/4) | file:line | error term in Section 5 | two meanings |
| N(x) | counting function, x real | file:line | — | used before definition at file:line |
```

Issues to flag: two meanings for one symbol, used before definition, a macro redefined with a different body, an implicit dependence of a constant on parameters (C versus C(k, ε)), silent changes of normalization.

## Step-check subagent prompt

Fill in the bracketed parts. Give the subagent only the files or excerpts listed: the proof under review, the definitions and statements it cites, and the external statements quoted verbatim. Never give it author notes, ledgers, earlier reviews or other subagents' outputs.

```
You are checking one proof, step by step, as an independent referee. You have no
access to the authors' notes or to other reviews, and you should not try to find them.

Material (read only this):
- Proof under review: [file:line range, or pasted excerpt] of [Lemma/Theorem label]
- Statement of the result: [pasted]
- Definitions and results it cites: [pasted statements with labels; for external
  results, the exact statement and source]
- Standing hypotheses and notation: [pasted]

Task:
1. Split the proof into numbered steps (one inference each). Quote the first words
   of each step so it can be located.
2. For each step, give a verdict:
   - VALID: follows from the hypotheses, earlier steps and cited results.
   - VALID WITH FIX: the conclusion holds but the step as written is wrong or
     incomplete; give the exact fix and say whether it changes any statement.
   - GAP: not established by what is written; say exactly what is missing and what
     would close it.
   - INVALID: false or does not follow; give the first failing step and a
     counterexample or the parameter values where the estimate fails.
3. Check in particular: every case is covered; every inequality holds in the full
   parameter range claimed (including boundary and smallest admissible values);
   limits, sums and integrals are interchanged legitimately; constants are explicit
   or their dependence is stated; every cited result is applied within its
   hypotheses; nothing stronger than the stated hypotheses is used.
4. Words such as "clearly", "similarly", "one can show", "standard" and "sketch"
   are not arguments. If the step they cover is nontrivial, check it yourself or
   mark it GAP.
5. You may test claims numerically with small exact computations (rational
   arithmetic). A numerical check can refute a step; it cannot make it VALID.
6. Before reporting a GAP or INVALID, look for an innocent explanation: a notation
   convention, a result proved earlier in the material, a hypothesis stated
   elsewhere in the material. State which ones you ruled out.

Output:
- A table: step | quote | verdict | reason | fix or missing piece.
- Overall verdict for the proof (the worst step verdict, unless a fix resolves it).
- Hypotheses used that are not in the statement.
- What you did not check, and why.

Do not rewrite the proof in full. Do not soften verdicts. Answer in the user's
language (the main session states it).
```

For a theorem's assembly step, which combines several lemmas into the final bound, give the subagent the lemma statements, not their proofs. Ask it to check that the combination is correct and that every lemma is applied within its hypotheses and parameter range.

## Computer-assisted proof checklist

Fill one block per computation the proofs rely on.

```markdown
### Computation <name> (used in <result label>, obligation O<k>)

- Purpose: what mathematical statement the computation establishes.
- Program and versions: solver / CAS / language and exact versions; OS.
- Inputs: paths and SHA-256 hashes of every input and script.
- Command: exact command line; runtime; machine.
- Output: verdict and the certificate path and hash.

Traceability
| Constraint / case / formula | Source lemma or inequality (label, file:line) | Parameter regime | Status |
|---|---|---|---|
| c1: x + 2y ≤ 3 | Lemma <label>, eq. (k) | n ≥ n0 | traced |
| c7 | — | — | NOT TRACED (GAP) |

Independent encoding
- Written from: the paper's statements (not from the first encoding)  [yes/no]
- Author of second encoding: [subagent / main session]
- Differences found between the encodings: ...
- Result of second encoding: ...

Certificates
- Type: rational Farkas multipliers / LP dual / interval bounds / enumeration log / other
- Checked by: an independent checker script with exact arithmetic (path, hash)
- Result: ...

Sanity queries
- Satisfiable sanity query (a known-feasible point or a weaker target): expected SAT, got ...
- Hypothesis removed (drop a key constraint): target should fail, got ...
- Boundary cases: ...

Reductions
- Continuous to discrete, infinite to finite, or general to normal form: where it is
  proved (label, file:line), or GAP.

Verdict: VALID / VALID WITH FIX / GAP / INVALID, with the reason.
```

Rules:
- Two solvers on the same formula check the arithmetic, not the formula. The formula's derivation is checked only by traceability and an independent encoding.
- Floating-point solver output is not a certificate. Convert to exact rationals and check the certificate exactly, or use interval arithmetic with outward rounding.
- A vacuous encoding (one where the target holds even with the hypotheses removed) is a red flag: the encoding probably does not say what the paper says.
- Record everything needed to rerun the computation. A computation that cannot be rerun is NOT CHECKED.
