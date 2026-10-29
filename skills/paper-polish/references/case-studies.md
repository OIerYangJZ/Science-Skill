# Cases: where this skill's lessons come from

Both cases are the author's own theoretical manuscripts (quantum information). Only the patterns and fixes that concern writing are kept here; journal names, submission history, and review details have been removed.

**Scope:** These two cases illustrate only two patterns:
- defensive writing buries the novelty;
- overclaiming gets caught by reviewers.

The specific numbers in the table (1-paragraph abstract, 109–300 words, no more than 3 symbols, etc.) are distributions from physics journals and must not be applied to other fields; derive the distributions for other fields afresh from paper-polish's exemplar statistics. Cases from other disciplines are welcome: just state the genre, the problem, and the fix.

---

## Case A: A theory manuscript rejected twice by editors for "unclear presentation"

**Facts**
- Both submissions stopped at the editorial level; no external referee read the manuscript.
- The only specific reason the editors gave was unclear presentation (lack of clarity in presentation).

**Survey method**
- Several survey streams ran in parallel: a prior-work audit, and a structural dissection of 26 same-genre articles from the target journal and journals of the same tier (in 4 groups).
- Afterward, the original manuscript and the data were checked manually, item by item.
- The author's own literature survey file turned out to contain 8 metadata errors: volume numbers, authors, affiliations; for one paper, the affiliation and the experimental platform were entirely wrong.

**Measurements**

| Item | Original | 26 exemplars | Rewrite |
|---|---|---|---|
| Abstract paragraphs | 4 | All 1 paragraph | 1 |
| Abstract words | 497 | 109–300 (theory median 161) | About 230 |
| Abstract sentences | 20 | 5–12 | 7 |
| First appearance of main result | Sentence 7, as an inequality with about 8 symbols | Sentences 2–4, sentence 6 at the latest | Sentence 3, in words |
| Inline formulas | 19 | Typically 0–3 | 7 |
| Scope qualifiers | 6+ places, plus 3 whole sentences | 1–3, attached to the result sentence | 1, attached to the result sentence |
| Baseline of the headline number | "orders of magnitude", baseline not named | At most one, baseline stated in the same sentence | Gives a range of factors, names the baseline (the highest optimization level of a mainstream tool), and acknowledges that another tool avoids this gap |
| First sentence of introduction | "A fault-tolerant compiler is not only a translator" | A hard problem in the field or a real-world motivation | "Two routine steps … split rotation angles on purpose." |
| Position of main result in introduction | Item 2 of the contribution list | Paragraphs 1–6 | Paragraph 4: a displayed formula, then each symbol explained in words |
| Contribution list | 6 long bulleted paragraphs | Only 2 of 26 use bullets | Removed, replaced by prose |
| Version-history paragraph | Present | 0 papers | Deleted, moved to the preprint's version notes |
| does / does not / no claim sentences | About 12 | 1 sentence or 0 | 1 scope paragraph, ending with a design principle |
| Fig. 1 caption | A full paragraph, citing 5 results not yet defined | Describes only what the figure shows | Condensed |
| Source of the technique | Mentioned only in Related Work | — | The introduction states directly that it is a standard multi-pass streaming argument, and says clearly where the new part lies |

**Lessons**
1. **"Unclear presentation" is mostly a structural problem, not a grammatical one.** Where the main result appears, whether the contributions are prioritized, how much space the scope discussion takes: these matter more than wording.
2. **Defensive writing creates the impression of a strawman.** The unnamed baseline in the original was in fact the default highest optimization level of a mainstream tool. Once it was named, it became harder for reviewers to call it a strawman.
3. **Acknowledge the source of the technique proactively.** The novelty audit found that the main theorem used a standard argument from an adjacent field, and that the original also omitted key references from that field (e.g., Guha–McGregor). Rather than wait for reviewers to point this out, state clearly in the introduction where the new part lies.
4. **For a result with small numbers, explain whom it constrains.** The original's example was "about 31 bytes", which reads as if the result does not matter; the rewrite explained which class of systems it constrains.
5. **Separate presentation problems from substantive problems.** The survey's priority table had a "new results needed" column, e.g., stronger, more application-relevant lower bounds. Rewriting cannot resolve this column.
6. **The same symbol must keep the same value throughout.** The worked example in the introduction and the main theorem used two different definitions, so the same quantity differed by a factor of about 4; an editor will notice this on page 2.

**Exemplar templates validated as effective** (all published, publicly available literature)
- Tan, PRX Quantum 7, 033058: result → previous best result → open problem.
- Koczor et al., PRL 132, 130602: the stakes first, then the metric expressed in bits; the cost goes in a concessive clause ("While PAI increases that sampling cost, we prove…").
- Low et al., PRX Quantum 4, 020323: gives the result at the very start of the introduction, and uses a lower bound to explain why those assumptions are needed.
- Caesura et al., PRX Quantum 6, 030337: headline number and baseline in the same sentence ("2 orders of magnitude over prior art"), with the exact factors broken down in a table in the introduction.

---

## Case B: A mock review of a theory manuscript that flagged both defensiveness and overclaiming

**Facts**
- An independent subagent wrote a mock review report according to the target journal's external review standards. It had not read the author's notes or revision plan beforehand.
- The report identified both kinds of problems.

**Defensive side** (paraphrased)
- Paragraphs consist of long sentences, each hung with qualifiers and "not … but …" constructions.
- The abstract gives the asymptotic result first and puts the practically meaningful number at the end.
- Captions are too long; the same symbol has two meanings; the introduction relies on specialized concepts that are not explained.
- Readers find it hard to extract the core message they should remember.

**Overclaiming side** (paraphrased)
- Nouns in the title and abstract (e.g., "law") are stronger than what is actually proved.
- Conclusions that depend on unproven assumptions are written in the abstract as if already established.
- Asymptotic results that are meaningless at practical parameters are placed at the start of the abstract.
- In addition, the parameter convention of an external tool was used incorrectly, which is a factual error (for this type of problem, see number-audit).

**What the author did afterward**
- Mapped every headline conclusion to a theorem and its conditions; the conditions always stay right next to the conclusion.
- Considered splitting the very long mathematical proofs into a separate paper, so that the main manuscript focuses on the core contribution.
- Cut the cover letter from about 500 words to about 350 and reordered it as: core problem → substantive novelty → journal fit → distinction from related manuscripts. Reduced the share of methods, numbers, and qualifying conditions, leaving the details to the body.

**Lessons**
1. **Removing defensiveness and avoiding overclaiming must be done together.** That is why this skill uses a claim ledger rather than simply deleting qualifiers.
2. **The mock review must be independent, and the main session must re-check it.** The main session recomputed each of the errors the mock review claimed: most were fully valid; one was valid only in substance, and its specific parameters needed correcting.
3. **The allocation of space is itself part of the narrative.** Long technical detail dilutes the editor's impression of the core contribution.
