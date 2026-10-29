# Exemplar survey protocol

## 1. The three pools

| Pool | Contents | Number | Purpose |
|---|---|---|---|
| A: Target-journal exemplars | Well-written articles of the same genre published in the target journal (or a journal of the same tier) in the last 5 years | 15–30 papers, in 3–4 groups by genre; no fewer than 8 papers | Reference for structure, writing, and measurement |
| B: Nearest-neighbor work | Papers on the same problem or the same technique that an editor would compare against, from any journal | 5–10 papers | Writing a gap statement that names prior work; novelty audit (standard techniques, existing results, citations that must be added) |
| C: Editorial criteria | The target journal's official about / scope / criteria pages | 1–3 pages | Verbatim excerpts; map the spine onto the journal's criteria |

**Selection criteria for Pool A** (the more satisfied, the better):
- Same genre as this paper. Theoretical proofs and algorithmic constructions, randomized controlled trials and observational studies, methods papers and application papers all differ greatly in how they are written; do not mix them in one group.
- Highly cited (normalized by year), editor-highlighted (Editors' Suggestion, Editor's Choice, Featured, etc.), award-winning, or named by the user or collaborators.
- Same article type as this paper (Article, Letter, Brief Report, Research Note, etc.). Journals set different length and abstract requirements for different types.
- Similar topic, but not necessarily the same. The goal is to learn how to write, not to learn the content.
- At least 3 papers on very close topics (competing with this paper for the same reviewers), plus 2–3 papers in the target journal widely recognized as exceptionally clearly written.

**Grouping examples:**
- Case A (quantum compilation): theoretical lower bounds, 7 papers; synthesis and $T$-count, 6 papers; randomized compiling and noise-aware compilation, 6 papers; fault-tolerant compilation, 7 papers.
- Illustrative (epidemiology): one group each of cohort studies, Mendelian randomization studies, and contemporaneous randomized controlled trials on the same outcome.
- Illustrative (machine learning): one group each of methods papers, benchmark or dataset papers, and analysis papers on the same task.

## 2. Search

```
# First confirm the journal's id in OpenAlex
python3 -I <skill-dir>/scripts/exemplar_meta.py venue "PRX Quantum"

# Run one search for each of 3–6 keyword sets (search method terms, problem terms, and object terms separately)
python3 -I <skill-dir>/scripts/exemplar_meta.py search "T-count lower bound" --venue "PRX Quantum,Physical Review Letters" --from 2021 -n 25
python3 -I <skill-dir>/scripts/exemplar_meta.py search "circuit compilation streaming" --venue "Quantum" --sort relevance
```

- `search` matches titles and abstracts, and all terms must appear. If recall is insufficient, use fewer keywords or switch to synonyms.
- Combine this with WebSearch (e.g., `site:<journal-domain> <topic>`) and with the journal's lists of editor-highlighted papers.
- Supplementary databases by field (OpenAlex has the broadest coverage, but the following are more complete or more up to date in their respective fields):

| Field | Database / source | How to use |
|---|---|---|
| Biomedicine, life sciences | PubMed, Europe PMC (including PMC full texts and preprints such as bioRxiv and medRxiv) | `lit_graph.py search --db europepmc` from `novelty-audit`; fetch accepts PMIDs directly |
| Physics, mathematics, computer science | arXiv; DBLP (computer science); ACL Anthology (NLP); OpenReview (ML conferences) | `--db arxiv`; use WebSearch for conference papers |
| Social sciences, economics | SSRN, RePEc / NBER working papers, OSF Preprints | WebSearch; verify published versions with OpenAlex |
| Chemistry, materials | ChemRxiv | WebSearch |
| Humanities | JSTOR, PhilPapers, Project MUSE | WebSearch; many works have no DOI and can only be checked manually |
- The user's existing survey files (e.g., `*survey*.md`) can be used directly as candidates, but re-verify all metadata in them.

## 3. Verification and download

```
python3 -I <skill-dir>/scripts/exemplar_meta.py fetch <DOI/arXiv ...> --out polish/<date>/exemplars --intro
python3 -I <skill-dir>/scripts/exemplar_meta.py fetch --ids-file polish/<date>/exemplar_ids.txt --out polish/<date>/exemplars --intro
```

- Do not use any entry with status `NOT FOUND`. When `WARNING arXiv title differs` appears, check manually.
- Take the abstract from the following sources, in order of preference: Crossref (the version deposited by the publisher), arXiv, PMC or Europe PMC, the OpenAlex reconstruction (formulas get garbled).
- Take the introduction from the following sources, in order of preference:
  1. The arXiv LaTeX source. It is parsed in memory only, never extracted to disk, and nothing in it is executed. PRL-style articles have no Introduction section; the script takes the text after the title page and before the first `\section`, and labels it "implicit".
  2. PMC open-access full-text XML. This covers biomedicine and many open-access journals such as PLOS, eLife, BMC, and Frontiers. In Nature-style articles the introduction has no heading; the script takes the paragraphs before the first section of the main text and labels them accordingly.
  3. If neither is available, obtain the text from the publisher's open-access page or ask the user for the PDF. If it cannot be obtained, analyze only the abstract and state this in the report (e.g., Tan PRXQ 7, 033058 in Case A).
- **Do not use WebFetch output for verbatim quotes or measurements**; it returns text that has been rewritten by a model.
- Fill in the `pool` and `group` fields in the header of each article's `.md` file.

## 4. Analysis card (one per article, filled in under "## Analysis card" in the `.md`)

Give verbatim quotes in the original language of the source, at most 40 words each, and indicate whether each comes from the abstract or from which paragraph of the introduction. Fill in all other fields in the user's language.

```markdown
## Analysis card

- Genre / group:
- Research question (rephrased as a question):
- Form of the answer: a number / a scaling / yes or no / a construction / a classification
- One-sentence conclusion (slogan, verbatim or approximate):
- Gap sentence (verbatim):
  - Prior work named: yes (who) / no
- Operational meaning: what it constrains, or which measurable quantity it changes
- Headline number: value + baseline (in the same sentence or not)
- Sentence-function sequence of the abstract: e.g., 1 background → 2 gap → 3 result → 4 result → 5 method → 6 significance
  - Sentence in which the main result first appears; in words or as a formula
  - Number of scope qualifiers; attached to the result sentence or standing as separate sentences
  - Ends on: significance / method / limitation / outlook
- Paragraph-by-paragraph function of the introduction: P1 …, P2 …, …
  - Paragraph in which the main result first appears
  - How contributions are presented: prose / numbered list (how many items)
  - How prior work is handled: named comparison / general summary / comparison table
  - How the scope is written: location, number of sentences, positive or negative wording
  - Role of Figure 1: mechanism figure / results figure / cost-model figure; caption length
- Title form: statement / question / "Toward…" / noun phrase
- Writing worth borrowing (1–2 verbatim quotes + why they work):
- Most relevant lesson for this paper (one sentence):
```

## 5. Measurement conventions

Compute all numbers with `hedge_scan.py`, so that this paper and the exemplars are counted under the same conventions. Do not mix manual counts and script counts in the report.

| Metric | Definition |
|---|---|
| words | Word count after removing LaTeX commands; each inline formula counts as 1 word |
| sentences | Split on sentence-final punctuation, with common abbreviations (Eq., Fig., et al., i.e.) protected |
| first result sentence | The first sentence that contains a result verb (we prove/show/find/…) or the pattern "any … that … must/obeys". **This is a proxy; the analysis card must rely on a full read of the text** |
| inline math | Number of inline formulas |
| defensive / 100 words | Number of D-class hits ÷ word count × 100 |
| scope qualifiers (S) | Number of phrases such as "under … assumption/model" and "within this family" |
| overclaim flags (O) | Number of strong words to check against the ledger, including O (strong words), OC (causal wording), and OS ("significant") |
| structured | Whether the abstract is in structured format (labels such as Background / Methods / Results / Conclusions) |

The paragraph and sentence counts of structured abstracts cannot be compared directly with those of unstructured abstracts. When computing statistics by group, keep the two kinds of abstract separate.

**The following is an example from one field only, not a default.** The distribution for the 26 physics-journal exemplars in Case A is as follows; recompute the statistics from the current sample every time:
- All abstracts are 1 paragraph, 109–300 words, 5–12 sentences;
- The main result usually appears in sentences 2–4, and no later than sentence 6;
- Inline formulas usually number 0–3;
- Only 2 of the 26 list contributions as bullets in the introduction;
- None mentions version history in the introduction.

Distributions in other fields may be very different. For example:
- Clinical journals mostly use structured abstracts, with a word limit of 250–300;
- In the Nature family, the abstract is a single summary paragraph of about 150–200 words, and the introduction has no heading;
- Computer science conference papers often list contributions at the end of the introduction.

So always rely on the statistics from the current set of exemplars.

## 6. Comparison table template for the report

Give one table for each of the four dimensions: research question, writing style, narrative focus, and abstract and introduction.

```markdown
| Aspect | Exemplars (median / range; examples, named) | This paper (value; line number) | Gap and fix |
|---|---|---|---|
| First appearance of main result | Sentences 2–4, no later than sentence 6 (Tan: sentence 1 gives the result, sentence 2 gives the previous best result) | Sentence 7, as a formula (`main.tex:97`) | Move to sentences 2–3, stated in words |
```

End the report with 2–4 reusable templates, written as follows:
"**Tan style**: sentence 1 gives the result; sentence 2 gives the previous best result; sentences 3–4 give a lower bound or an open question; the technique comes last. Suited to: theoretical results that improve a known bound."

## 7. Limitations (must be included in the report)

- The sample contains only successfully published articles, so the conclusion can only be "published articles are usually written this way".
- The introductions read are the arXiv versions, which may differ from the published versions.
- The choice of exemplars affects the conclusions. State how they were selected, including the search terms and screening criteria.
