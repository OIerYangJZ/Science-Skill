---
name: novelty-audit
description: Audit the novelty of a paper with falsification as the goal — decompose each contribution into result, technique, and model, and translate it into the terms of neighboring communities (e.g. compiler lower bound → multi-pass streaming algorithms / communication complexity / advice complexity; a "new model" for the area under the blood-glucose curve → the trapezoidal rule of numerical integration; spatial interpolation → Gaussian process regression), applicable across disciplines; then search in four directions (forward citations, backward citations, keywords, and recent preprints) for possibly existing results, proofs that are standard techniques, and concurrent work; after reading each paper, give a novelty verdict for each contribution, the references that must be added, and suggested wording. Use when preparing a submission, before writing "first / novel / to our knowledge", when a reviewer questions novelty, or when the user asks "is this result new?". Not for polishing prose (paper-polish) or checking existing citations (cite-verify).
argument-hint: "[manuscript .tex/.docx/.md/.pdf or one-sentence description of the result] [--claims C1,C2]"
---

# novelty-audit: first try to prove "this is not new"

## The problem this skill addresses

When AI searches the literature, it tends to look for evidence that supports "we are new" and misses the work that reviewers will use for comparison (see item 5 of `FAILURE_MODES.md`).

Case A: the author team believed the main theorem was new; the audit concluded:

- The main theorem is a **standard multipass streaming argument**: a fooling set plus Fano's inequality, plus the AMS and Guha–McGregor "p passes are equivalent to 2p−1 messages" simulation. To reviewers in theoretical computer science, this is a standard result.
- The commitment toll has precedents in the classical **advice complexity** literature (string guessing by Böckenhauer et al.; the survey by Boyar et al.).
- The original manuscript cited none of the 7 references that must be added, including concurrent work from 2026.

These references are almost impossible to find with the search terms of the quantum compilation community; the problem must first be translated into the language of neighboring communities.

A classic cross-disciplinary example: Tai (Diabetes Care 17(2):152–154, 1994) proposed "a mathematical model for the determination of total area under glucose tolerance curves", which is in fact the trapezoidal rule of numerical integration. Searching in medical terms finds no mathematical precedent; switching to the terms of numerical analysis finds it immediately.

## Hard rules

1. **The goal is falsification.** For every contribution, first assume "someone has already done this", then look for evidence. If none is found, write the conclusion as "not found within [databases, queries, dates]", not as "this is new".
2. **Only what has been read counts.** Every verdict of "known / partly known / standard technique" must rest on the source actually read (at least the abstract; for a specific result, read as far as the corresponding theorem, table, or section), and must give the location and a verbatim excerpt. Saying "X proved this long ago" from memory does not count.
3. **Log every search** (`lit_graph.py --log`); attach the complete search log to the final report.
4. **Diagnose only; do not edit the manuscript.** Write outputs to `novelty/<YYYY-MM-DD>/` (inside a git repository, add it to `.git/info/exclude`). Hand wording suggestions over to paper-polish or the author.
5. Verify the metadata of cited references; you can directly use cite-verify's `refcheck.py` or paper-polish's `exemplar_meta.py fetch`.
6. Talk to the user and write reports in the user's language; write suggested manuscript wording in English.

## Phase 0: Intake

- Input: the manuscript, or the user's description of the result.
- List the contributions: extract every "we prove / we show / we find / we develop / first / new / novel" claim from the abstract, introduction, and conclusion, and number them C1, C2, …; typically 2–6.
- Read the recent work already cited in the manuscript and its Related Work; note the prior work already acknowledged, so it is not reported again.

## Phase 1: Decompose and translate

For each contribution, write a contribution card following the template in `references/search-playbook.md`:

1. **Result**: restate it without field-specific jargon, in more general language, e.g. at the level of mathematics, statistics, algorithms, or mechanisms.
   - Case A: "for any p-pass streaming algorithm whose state across the cut is S, if it computes an injective aggregate, then A + (2p−1)S ≥ m log K".
   - Illustration: "compute the area under a sampled curve by piecewise linear interpolation".
2. **Technique or method**: the core steps, e.g. proof techniques (fooling set, Fano's inequality), experimental techniques (CRISPR screening, single-cell sequencing), statistical or econometric methods (mixed-effects models, difference-in-differences), model architectures (attention mechanisms, graph neural networks).
3. **Model**: which assumptions make the result hold, and which modeling choices are specific to the field.
4. **Neighboring communities and what they call it**: at least 3. The same idea often has different names in different disciplines, for example:
   - pass elimination in streaming algorithms;
   - the trapezoidal rule in numerical analysis;
   - kriging in geostatistics, called Gaussian process regression in machine learning;
   - backpropagation in neural networks, called reverse mode in automatic differentiation.

   See `references/search-playbook.md` for more.
5. **Queries**: 2–4 per community; use quoted phrases joined with AND to improve precision.

## Phase 2: Search in four directions

```
L="python3 -I <skill-dir>/scripts/lit_graph.py"
LOG=novelty/<date>/search_log.md
# A Keywords (run every community's queries)
$L search '"pass elimination" AND streaming' --log $LOG --out novelty/<date>/hits.md
# B Forward: who cites the classic papers this work relies on (someone has often done the same thing)
$L citing <DOI of the classic paper> --match '"lower bound" AND pass' --sort cited --log $LOG --out novelty/<date>/hits.md
# C Backward: what the nearest-neighbor papers cite
$L refs <nearest-neighbor DOI or arXiv> --log $LOG --out novelty/<date>/hits.md
# D Concurrent work (last 18 months; by default queries arXiv, OpenAlex, and Europe PMC together, the last of which includes bioRxiv and medRxiv)
$L recent '"phase folding" AND "T-count"' --days 540 --log $LOG --out novelty/<date>/hits.md
# Biomedicine / life sciences: PubMed, PMC, and preprints
$L search '"gut microbiome" AND "social network"' --db europepmc --log $LOG --out novelty/<date>/hits.md
```

Then supplement by field (full list in Section 3 of `references/search-playbook.md`):
- WebSearch, and Google Scholar–style phrase searches;
- recent tables of contents of the field's main conferences or journals;
- preprint servers: arXiv, bioRxiv, medRxiv, SSRN, ChemRxiv, OSF;
- registries: ClinicalTrials.gov for ongoing trials, PROSPERO for systematic review protocols, OSF Registries for preregistered studies;
- expert Q&A communities: MathOverflow, Cross Validated, etc.

When arXiv rate-limits (429), the script skips arXiv automatically and notes this in the log; run those searches again later.

Keep candidates to 10–30 papers per contribution. Screen first by title and abstract, then read the 3–8 most relevant closely.

## Phase 3: Reading and verdicts (can run in parallel)

Assign one subagent per contribution, playing "a reviewer who wants to prove this is not a new result". The prompt is in `references/search-playbook.md`. The subagent receives the contribution card, the candidate list, and the relevant theorems of the manuscript. The subagent must read the sources and assign each candidate a relation:

| Relation | Meaning |
|---|---|
| P already known | The same or a stronger result has been published |
| T standard technique | The proof uses a known technique; the result itself may be new |
| S special case or corollary | The paper's result is a special case of a known result, or follows directly from one |
| C concurrent | Closely related work that appeared within the last 18 months |
| R related | Should be cited for positioning, but does not threaten novelty |
| I irrelevant | Not related |

The main session re-checks every P, S, and T verdict: read the corresponding location in the source, and write it into the report only after confirming it.

## Phase 4: Report

Write `novelty/<date>/report.md` (in the user's language), conclusions first:

1. **A verdict for each contribution**, one of four:
   - new (within the searched scope);
   - new in its application or modeling in this field, with a standard technique;
   - partly known (state where the difference lies);
   - known.

   Support each verdict with evidence: the reference, theorem number, and verbatim excerpt.
2. **Which community would consider it standard.** For example, "reviewers in streaming algorithms would regard it as a standard result; programming languages and computer architecture would find it new". This bears on where to submit.
3. A list of references that **must be added / are recommended** (metadata verified), stating which contribution each one concerns.
4. **Suggested wording**, e.g. "The proof is a standard multipass streaming argument [AMS, Guha–McGregor]; what is specific to compilation is the fooling family and the accounting.", and which "first / novel" phrasings to delete or qualify.
5. **What new results would be needed for stronger novelty.** For example, "an r-dependent T-count lower bound" in Case A; or "replicate in another population", "test causality with a randomized design".
6. **Search scope**: attach `search_log.md`, and state the databases and communities not covered.

## Final report to the user (concise, in the user's language)

- A one-sentence verdict per contribution.
- The number of references that must be added, and the 2–3 most important ones.
- The biggest novelty risk, and whether it is a wording problem or a substantive one.
- Paths to the report and the search log.
