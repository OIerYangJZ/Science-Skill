# Novelty search playbook

## 1. Contribution card template (`novelty/<date>/cards.md`)

```markdown
## C1: <one-sentence claim as stated in the manuscript> (abstract sentence n / Thm k)

- Result (restated without jargon):
- Technique (core steps of the proof):
- Model assumptions (which ones are specific to the field):
- Part most likely already done by someone:
- Neighboring communities and what they call it:
  - Community 1: <keywords>
  - Community 2: …
  - Community 3: …
- Queries:
  - '"phrase one" AND "phrase two"'
  - …
- Seed papers (for citing / refs): <classic papers this work relies on, nearest-neighbor papers>
```

## 2. Translation examples (Case A retrospective)

| Phrasing in this field | Neighboring community | Their terms | Precedents found |
|---|---|---|---|
| Lower bound on the restart state of a downstream compiler across the cut | Streaming algorithms / communication complexity | multi-pass streaming lower bound; fooling set; "pass elimination" | Alon–Matias–Szegedy; Guha–McGregor, ICALP 2008 |
| An executed prefix must specify the objects it acts on, at a cost of log₂C(m,k) | Online algorithms | advice complexity; "string guessing" | Böckenhauer et al., TCS 554 (2014); Boyar et al., ACM Comput. Surv. (2017) |
| Committed output + state across the cut | Streaming I/O complexity | "input/output streaming"; reversal; sorting | François–Jain–Magniez, arXiv:1309.0647 |
| Merging commuting rotations, phase folding | Program analysis / PL | relational analysis; "phase folding"; abstract interpretation | Amy–Lunderville, POPL 2025; Albarghouthi, arXiv:2605.13929 (concurrent) |
| Limits of the capability of local-window optimizers | PL / compilers | "local optimization" quantum circuits | Arora et al., arXiv:2502.19526 |

**Cross-disciplinary translation examples** (the last three rows are well-known cases of "same idea, different names"):

| Phrasing in one field | Phrasing in another field | Note |
|---|---|---|
| "A mathematical model for the determination of total area under glucose tolerance curves" (Tai, Diabetes Care 17(2):152–154, 1994) | The trapezoidal rule of numerical integration | A "new model" published in a medical journal that is in fact textbook numerical analysis |
| kriging (geostatistics) | Gaussian process regression (machine learning) | The same class of methods; each community has its own body of literature |
| Backpropagation (neural networks) | Reverse mode of automatic differentiation | Searches must cover both sets of terms |
| Difference-in-differences (econometrics) | Controlled interrupted time series (epidemiology, public health) | Similar design logic; the literature is published separately in the two fields |

Lessons:
- Using only the field's own terms ("quantum compiler state lower bound") retrieves none of these papers.
- In the retrospective test, the first hit of `search '"pass elimination" AND streaming'` is Guha–McGregor; `recent '"phase folding" AND "T-count"'` finds Albarghouthi 2026 and van de Wetering et al., Quantum 2025.

## 3. Search sources by field

| Field | Literature databases | Preprints / concurrent work | Other |
|---|---|---|---|
| General | OpenAlex (`lit_graph.py` default), Google Scholar (WebSearch) | — | — |
| Biomedicine, life sciences | PubMed, Europe PMC (`--db europepmc`) | bioRxiv, medRxiv (searchable in Europe PMC) | ClinicalTrials.gov, PROSPERO, Cochrane Library |
| Physics, mathematics, computer science | arXiv (`--db arxiv`), DBLP, zbMATH, MathSciNet | arXiv | Conference proceedings listings (STOC, NeurIPS, ACL, etc.), OpenReview, MathOverflow |
| Social sciences, economics | OpenAlex, RePEc / IDEAS, JSTOR | SSRN, NBER, OSF Preprints | AEA RCT Registry, OSF Registries |
| Psychology | PsycINFO (via institution), OpenAlex | PsyArXiv | OSF Registries (preregistration) |
| Chemistry, materials | OpenAlex, CAS (via institution) | ChemRxiv | Patent databases (Google Patents) |
| Engineering | IEEE Xplore, OpenAlex | arXiv (eess) | Patents, standards documents |
| Humanities | JSTOR, PhilPapers, Project MUSE | — | Books, archives; many have no DOI and require manual checking |

For databases that require institutional access, leave the search to the user, or use WebSearch to find public abstract pages. State in the search log which databases were not covered.

## 4. Writing queries

- OpenAlex full-text search: enclose phrases in quotes and join them with AND, e.g. `'"phase folding" AND "T-count"'`. Unquoted multi-word queries are very broad (they may return tens of thousands of irrelevant results).
- Per contribution, at least: 3 communities × 2 queries, plus citing on 2 seed papers (run once sorted by citation count and once sorted by date).
- Combine `citing` with `--match`: among the many papers citing a classic paper, find the few that "also prove a similar lower bound".
- `recent` looks back 540 days by default and is used to find concurrent work. Also check the relevant arXiv categories, e.g. quant-ph, cs.DS, cs.CC, cs.PL.
- For mathematical results, also check MathOverflow and relevant experts' homepages, lecture notes, and unpublished letters or notes. Connections pointed out by experts often cannot be found by keyword; when necessary, advise the user to consult domain experts directly.

## 5. Subagent prompt (one per contribution)

```
You are a referee who suspects that contribution C below is not new. Your job
is to find the strongest evidence that it is already known, follows from known
results, or uses a standard technique without acknowledging it.

Contribution card:
<card>

The manuscript's statement and proof sketch:
<theorem + proof outline, or file:line ranges to read>

Candidate prior work (verified metadata; read them, do not rely on memory):
<list with DOI / arXiv>

For each candidate that matters, give: relation (P already known / T standard
technique / S special case or corollary / C concurrent / R related / I
irrelevant), the exact location in the source (theorem or section), a quote
of at most 40 words, and one sentence on how it bears on C. You may search for
further candidates (OpenAlex, arXiv, web) and must list every query you ran.
End with a verdict for C: new (within the searched scope) / new application,
standard technique / partly known / known. Answer in the user's language (the
main session states it), quotes in English.
```

## 6. Examples of verdict wording

- **New application, standard technique:** "A lower bound on the state across the cut in quantum compilation (new); the proof is a standard multipass streaming reduction (AMS 1999; Guha–McGregor 2008). Suggested wording: The proof is a standard multipass streaming argument; what is specific to compilation is the fooling family and the accounting."
- **Partly known:** "The commitment toll is an instance of the string guessing lower bound (Böckenhauer et al. 2014, Thm 3) under the modeling assumption that 'an executed prefix must specify its targets'. Suggest positioning it as bringing advice complexity into quantum compilation, rather than as a new lower-bound technique."
- **Not found within the searched scope:** "No comparable result was found in OpenAlex (queries in lines 3–9 of the log), arXiv (quant-ph, cs.DS, last 18 months), or the QIP 2024–2026 paper lists. 'to our knowledge' may be kept once."
