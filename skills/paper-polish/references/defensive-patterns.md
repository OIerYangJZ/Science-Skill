# Defensive writing and overclaiming: categories, detection, fixes

The numbering matches `scripts/hedge_scan.py`. The script catches only lexical cues (D1, D2, D4, D5, D6, D8, D10, D12, D13, O, S). Structural problems (D3, D7, D9, D11, D14) must be judged by reading the full text.

There is only one test: **Does this sentence help the editor see the result, or does it shield the author from criticism?** A sentence that shields against criticism need not be deleted. The usual fix is to move it to the scope paragraph or rewrite it as a positive conditional clause.

Examples marked "Case A" are taken from the original and rewritten drafts of the quantum-compilation manuscript in `case-studies.md`; examples marked "Illustrative" are constructed to illustrate other fields and are not from real publications.

**When applying this across disciplines, first distinguish two kinds of qualifiers:**
- **Statements of uncertainty required by field norms must be kept.** For example: "was associated with" in observational studies; labeling exploratory analyses as exploratory; reporting confidence intervals and samples; a limitations paragraph in medical papers where required; stating transferability in qualitative studies. Readers and reviewers expect these; they are not defensive.
- **Disclaimers and dilution surrounding "this paper's contribution" itself are what need fixing.** For example: unnamed gaps; "we attempt to shed light"; conceding before giving the result; negative scope sentences throughout the paper; burying the main finding behind the method description.

The judgment rests on the exemplars, not on intuition. The density of a given class of words (e.g., may) in the target-journal exemplars is the norm for the field (`exemplar_stats.md`).

---

## D1 Negative scope sentences / disclaimers

**What it looks like:** "We do not claim…", "This does not imply…", "No claim depends on…", "without promoting them to a theorem", "is worth clarifying early because a figure is easier to overinterpret than a theorem".

**Why it hurts:** The first thing the editor reads is "what you did not do". Such sentences often appear several times in one paragraph and make the author seem to lack confidence in their own results.

**Fix:**
- Rewrite "does not apply to Z" as "for X, we prove Y", placing the scope in a conditional clause of the result sentence.
- Keep only one scope paragraph in the whole paper, in positive wording, ending on a design principle or an open question.
- State a negative conclusion that genuinely needs stating only once, and give the reason. A negative conclusion can itself be a result, as in the limitations that Bapat et al. state candidly.

**Examples (Case A):**
- Original: "One downstream experiment fixes the physical stakes without promoting them to a representation-independent theorem."
- Revised: "Merging matters for fault-tolerant cost: on a four-qubit benchmark, under one disclosed synthesis and surface-code model, the output of Qiskit's highest preset optimization level needs 385–1,753 times the logical $T$ states of a merged circuit, while TKET's PauliSimp … avoids the gap."
  - The revised sentence states the significance first, then gives the number. The baseline is named as Qiskit opt3, the scope is compressed into a single phrase, "under one disclosed … model", and the sentence candidly acknowledges that TKET avoids the gap.

- Original: "The same figure also delineates the scope of the statement, which is worth clarifying early because a figure is easier to overinterpret than a theorem."
- Revised: Delete this sentence; consolidate the scope into one paragraph at the end of the introduction, closing with a design principle: "Read the other way, these limits are a design rule: randomize and lower late, and keep phase semantics until the coefficients have been merged."

## D2 Concessive openings

**What it looks like:** The sentence begins with "Although / While / Despite / Admittedly / Of course", and the sentence as a whole contains no result.

**Not D2:** The concessive clause is immediately followed by a result, i.e., the cost goes in the subordinate clause and the result in the main clause. This is good writing, e.g., Koczor et al. (PRL 132, 130602): "While PAI increases that sampling cost, we prove that (a) the approach is optimal…". The script already excludes this case.

**Fix:** State the result first and put the cost in a subordinate clause. If a limitation needs a sentence of its own, place it after the result.

## D3 Buried result (structural)

**What it looks like:**
- The abstract spends 5–6 sentences setting up the model and gives the result only in sentence 7;
- The result is given as an inequality containing 8 symbols;
- In the introduction, the main result first appears only in item 2 of the contribution list.

**Why it hurts:** Editors read only the first few sentences. If they have not seen the result by then, they judge the paper as "lack of clarity".

**Fix:**
- Give the result in sentences 2–4 of the abstract, in words, e.g., "must move about $m\log_2(1/\epsilon)$ bits".
- Give the main result within the first 4 paragraphs of the introduction. If a formula is truly needed, give one displayed equation and immediately explain each symbol in words.

**Examples (Case A):**
- Original (from abstract sentence 4 on): "We formalize this representation-dependent recoverability for a downstream compiler… The model charges two information channels… For an $r$-round modular accumulation…", with the main result appearing only in sentence 7, as a formula.
- Revised (sentences 2–3): "We ask what a compiler that sees only the resulting instruction stream must pay to merge the pieces back into one rotation per term. For a layer of $m$ rotations on an accuracy-$\epsilon$ grid, we prove that any such compiler … must move about $m\log_2(1/\epsilon)$ bits across the boundary before the last round…"

- Illustrative (social science):
  - Original: "Although our sample is limited to one country and our measures are self-reported, we attempt to provide some preliminary insights into …"
  - Revised: "Using a nationally representative panel of 12,000 adults, we find that … (β = …, 95% CI …)." State the limitations once in the discussion, pointing to the next study that should be done.

## D4 Diluted contribution

**What it looks like:** "we attempt / try / aim / seek", "take a first step toward", "preliminary", "modest contribution", "shed light on", "a complementary perspective".

**Why it hurts:** It turns a theorem into an attempt.

**Fix:** Write "we prove" for what has been proven, "we construct" for what has been constructed, and "we measure" for what has been measured. Write preliminary only if the work truly is preliminary, and say clearly what is still missing.

**Related signal (not an error):** framing verbs such as formalize, study, explore, and consider. The script reports their ratio to result verbs. More framing verbs than result verbs often indicates that the abstract describes "what was done" rather than "what was found".

## D5 Modal hedges

**What it looks like:** may, might, could, possibly, potentially, perhaps, seems to, to some extent, and stacked hedges such as "may potentially".

**Note:** Use in background descriptions is usually fine, e.g., Koczor writes "a real device may only be capable of $b$ bits". The problem is **using them on your own conclusions**.

**Fix:**
- Remove the hedge from anything that has been proven.
- For what is genuinely uncertain, state the source of the uncertainty: "supported by exhaustive enumeration up to n = 20", or "conjectured; we verify it for $n\le 8$".
- Never stack two hedges, under any circumstances.

## D6 Vague gap

**What it looks like:** "well known anecdotally", "remains largely unexplored", "has received little attention", "to the best of our knowledge".

**Why it hurts:** The editor cannot tell whom you improve on, and has no way to judge whether the gap really exists.

**Fix:** Name one prior work and say exactly what it lacks. See how the 26 physics-journal exemplars in Case A do it: "no improvement since 2018", "the result of Tran et al. carries an extra $O(n^{1/2})$ overhead", "handles only the pairwise-commuting case".

**Examples (Case A):**
- Illustrative (biomedicine):
  - Original: "The role of social contact in microbiome transmission remains largely unexplored."
  - Revised: "Studies of captive and laboratory animals link co-housing to shared gut taxa [Refs], but whether everyday social contact shapes the microbiome in wild populations, where diet and kinship also vary, is unknown."
  - The revised sentence names the existing evidence and states exactly which piece is missing.
- Original (Case A): "This representation dependence is well known anecdotally."
- Revised: "These methods assume an optimizer that sees, or can rebuild, a global description of the layer. Much compilation instead runs downstream of the steps that dispersed it." This is followed by a list of concrete settings and a citation of Hashim 2025 as evidence that the problem is real.

## D7 Equal-weight contribution list (structural)

**What it looks like:** 6 bulleted contributions, each a long paragraph with formulas.

**Why it hurts:** The editor cannot find "the one" new result. Only 2 of the 26 exemplars used bullets.

**Fix:** Present 2–3 results in prose, ordered by importance, with the first result taking the most space. In CS journals (e.g., ACM TQC) the convention is to list 2–3 inline contributions at the end of the introduction; following that convention is fine.

## D8 Version history and internal labels

**What it looks like:** "The prior version of this work…", "legacy", "historical", and internal experiment IDs such as W3/W7.

**Fix:** Put version notes in the arXiv Comments field or in an appendix title, e.g., "Exact-semantics results (from v1)". Delete all internal labels.

## D9 Caption turned into a scope discussion (structural)

**What it looks like:** The Figure 1 caption exceeds 120 words, cites 5 results before they are defined, and discusses scope within the caption.

**Fix:** The caption describes only what the figure shows, in one or two sentences per panel. Move the scope discussion back into the main text.

## D10 Agentless passive

**What it looks like:** "It is shown that…", "It can be proven that…".

**Fix:** Write "We show…", or state the conclusion directly: "Any compiler that … must …".

## D11 Verification conditions piled into the abstract (structural; the script only counts S-class phrases)

**What it looks like:** The abstract contains whole sentences spelling out technical conditions, e.g., "within their stated equivalence and error conventions", "Under the additional, explicitly disclosed frame-tracked presentation…", "Both bounds include per-coordinate allowances and remain valid when…".

**Fix:** Keep in the abstract only the conditions the editor needs in order to judge the result, usually 1–3, attached to the result sentence. Move the rest into the theorem statements in the main text.

## D12 Filler

**What it looks like:** "It is worth noting that", "Note that", "Interestingly".

**Fix:** Delete them and state the content directly.

## D13 "Not X, but Y" framing

**What it looks like:** "A fault-tolerant compiler is not only a translator", "The point is not … but …".

**Why it hurts:** The first thing the reader encounters is you rebutting a misconception that no one has raised.

**Fix:** State Y directly.
- Original (Case A, first sentence of the introduction): "A fault-tolerant compiler is not only a translator; some of its standard stages also disperse structure…"
- Revised: "Two routine steps of a fault-tolerant software stack split rotation angles on purpose."

## D14 Unnamed baseline (both defensive and overclaiming)

**What it looks like:** "orders of magnitude more than the materialize-first pipeline", without saying what materialize-first is or whether it is a straw man.

**Fix:** Name the baseline as the current best method or the production default, and give the factor in the same sentence. If some tool avoids the gap, acknowledge that as well.

**Example (Case A):** materialize-first is in fact Qiskit preset optimization level 3. The original draft did not name it, which made it look like a straw man; the rewritten draft names it and acknowledges that TKET PauliSimp avoids the gap.

---

# Overclaiming (O class)

The script flags the following words as O, as a prompt to check them against the ledger; this does not mean the words cannot be used.

| Code | What it looks like | Check |
|---|---|---|
| O1 | A conditional conclusion written as unconditional: "This is the rate", when it actually depends on an unproven assumption | Is the condition right next to the conclusion? |
| O2 | A numerical, experimental, or observational result written as "we establish / prove" | The evidence level is C1–C3, X2–X3, or O1–O3 (see `claim-calibration.md`); the verb should be find / observe / is associated with |
| O3 | law / universal / fundamental / first / novel / optimal / tight | Does a theorem say exactly this? Has "first" been checked against Pool B? |
| O4 | "orders of magnitude", "dramatically" | Is the baseline named, and is it the current best? Is the factor a comparison against a straw man? |
| O5 | The abstract opens with a non-effective asymptotic result that is vacuous at practical parameters | Does the abstract state what holds at practical parameters? |
| O6 | Scope extrapolation: a result in model M is said to apply to "compilers"; a result for one population is said to apply to "people"; a result on one dataset is said to hold "in general" | Does the subject in the abstract and title match the object of the evidence? |
| O7 | Correlation written as causation: an observational study uses causes, leads to, effect of, drives, results in (the OC class in `hedge_scan`) | Does the design support causal inference (randomization, or a stated identification strategy and assumptions)? |
| O8 | "significant" without a statistical test, or statistical significance presented as practical importance (OS class) | Are the test and the effect size reported? For the non-statistical sense, use substantial or marked instead |
| O9 | Pilot, post hoc, or subgroup results as the headline; "trend toward significance" | Was it prespecified? Is it labeled as exploratory? |
| O10 | Machine learning: comparing only against weak baselines, not reporting variance, tuning on the test set and then reporting | Are the comparators tuned to their best? Number of seeds and variance; data splits |

**Examples (Case B, overclaiming identified by a mock review, paraphrased):**
- A theorem whose premises already contain most of the conclusion is promoted in the abstract as the main result.
- Conclusions that depend on unproven assumptions are written in the abstract as if already established.
- A noun in the title ("law") suggests that the result is stronger than what is actually proven.
- The abstract opens with asymptotic results that are vacuous at any practically meaningful parameters; the practical numbers appear only at the end of the abstract.

---

**Illustrative (machine learning):** "Our method achieves state-of-the-art results" → "On three standard benchmarks (A, B, C), our method improves accuracy over the strongest published baseline (D, retuned with the same budget) by 1.8–3.1 points (mean of 5 seeds; s.d. ≤ 0.4)."

# When qualifiers are appropriate

- Conjectures, numerical extrapolation, heuristic arguments: qualify them, but state the evidence. Write "we conjecture X; exhaustive enumeration up to n = 20 supports it", not "X may hold".
- Theorems that depend on an external assumption: state the assumption next to the conclusion, e.g., "Under Conjecture H, …", and only that once.
- The result really is weak, e.g., the number is small: say so directly, then explain what it constrains.

  Example (Case A): "Per term the price is modest, $\log_2 K_\epsilon\approx 9.6$ bits… What Eq. (1) fixes is where those bits must live." This is how the weakness is turned into the operational meaning of the result.
- The technique comes from a standard method: acknowledge it directly, then say clearly where the new part lies.

  Example (Case A): "The proof is a standard multipass streaming argument […]. What is specific to compilation is the fooling family and the accounting." Acknowledging it up front works better than waiting for a reviewer to point it out.
