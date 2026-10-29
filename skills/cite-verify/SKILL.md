---
name: cite-verify
description: Verify references (any discipline) at two levels. (1) Metadata — compare each entry's authors, title, year, journal, volume, pages, and DOI against Crossref, DataCite, arXiv, and Europe PMC (PubMed) records, and flag fabricated or nonexistent entries, preprints that have since been formally published, retractions and errata, and missing or unused citation keys. (2) Claim support — for sentences in the text such as "So-and-so proved X [n]", check whether the cited work actually says so. Use when checking a .bib file, an RIS export (Zotero / EndNote), a reference list in any citation style at the end of a Word / PDF / Markdown manuscript, or a literature-survey list compiled by AI or by hand. Not for finding new literature (that is the job of novelty-audit).
argument-hint: "[refs.bib / refs.ris / manuscript.docx / survey.md] [--tex main.tex] [--claims]"
---

# cite-verify: every reference is real, accurately recorded, and supports the sentence that cites it

## The problem this skill addresses

Reference lists generated or compiled by AI often contain metadata errors, or even fabricated references (see item 4 of `FAILURE_MODES.md`). Checking a single survey md file of the author's own turned up 8 errors:

- Wrong volume (Tan should be PRXQ **7**, 033058);
- Wrong authors: the fourth author of Becker et al. should be Rouzé; "Nation, Treinish et al." actually has only two authors;
- Institution and platform entirely wrong: Caesura et al. was described as trapped-ion work from Quantinuum, but it is actually photonic FBQC work by PsiQuantum and Boehringer Ingelheim.

Correct metadata does not mean a correct citation: the cited work may not actually prove the result the text attributes to it.

## Hard rules

1. **Do not modify the user's bibliography files or manuscript.** Write outputs to `refcheck/<YYYY-MM-DD>/` (inside a git repository, add it to `.git/info/exclude`). Write proposed corrections to `corrected.bib`; replace entries only after the user confirms.
2. **Records are evidence; memory is not.** Every "correct" or "wrong" judgment must map to a record in Crossref, DataCite, arXiv, or Europe PMC. Saying from memory "this one should be from 2019" does not count.
3. **Not found does not mean fabricated**, but it must be confirmed manually. Books, theses, software, conference abstracts, government reports, archives, and ancient texts are often absent from these databases; many works in the humanities and social sciences have no DOI. The conclusion can only be "found / not found (searched A, B, C)".
4. **Claim-support checks require reading the source**: read at least the abstract, and the relevant sections when a specific result is involved. If the full text is not accessible, mark the item "cannot verify"; do not guess.
5. Talk to the user and write reports in the user's language; bib entries and manuscript text in proposed fixes stay in English (or the manuscript's language).

## Phase 0: Intake

- Input can be:
  - `.bib` files (one or more) + the main `.tex` (to determine which entries are cited);
  - `.ris` files (Zotero, EndNote, Mendeley exports); use `check`;
  - Word, PDF, Markdown, or plain-text manuscripts, or a standalone reference list, in any citation style (APA, Vancouver, Nature, Chicago, …); use `check-list`. It finds the References section automatically and splits it into individual entries;
  - or a survey md file. Convert the md file first: turn each reference into a minimal BibTeX entry (title, author, journal, volume, pages, year, doi, whichever are present), save it as `refcheck/<date>/from_md.bib`, and keep the line number in the md as a comment (`% md line 37`). **When converting, copy only what the md file says; do not complete or correct anything**; corrections are left to the verification step.
- Whether to run the second level (claim support): run it when the user asks, or by default when the paper is about to be submitted, checking only the key sentences (see Phase 3).

## Phase 1: Metadata verification

```
python3 -I <skill-dir>/scripts/refcheck.py check refs.bib --tex main.tex --out refcheck/<date>
python3 -I <skill-dir>/scripts/refcheck.py check refs.ris --out refcheck/<date>
# Reference list at the end of a Word / PDF / Markdown manuscript (any citation style):
python3 -I <skill-dir>/scripts/refcheck.py check-list manuscript.docx --out refcheck/<date>
# Survey md:
python3 -I <skill-dir>/scripts/refcheck.py check refcheck/<date>/from_md.bib --out refcheck/<date>
```

The script's matching order:
- Free-form entries (`check-list`): send the whole entry text to Crossref bibliographic search, then query arXiv and Europe PMC in turn; once a record is found, check whether its year, volume, first page, authors, and journal appear in the entry text;
- With a DOI: query Crossref, and DataCite if it is not found there (LIPIcs, Zenodo, and arXiv DOIs are registered with DataCite);
- With an arXiv ID: query arXiv, and also check whether a journal version already exists;
- With neither: search by title and first author. Title matching is strict: "Clifford+T" and "Clifford+V" do not count as the same paper.

Outputs:
- `report.md`: issues graded by severity;
- `results.json`;
- `corrected.bib`: suggestions only.

Issue codes:

| Level | Code | Meaning |
|---|---|---|
| ERROR | NOT_FOUND / DOI_NOT_FOUND / EPRINT_NOT_FOUND | No record found; possibly fabricated or mistyped |
| ERROR | TITLE_MISMATCH / FIRST_AUTHOR / AUTHOR_NOT_IN_RECORD / AUTHOR_MISSING_FROM_BIB | Title or authors do not match the record |
| ERROR | VOLUME_MISMATCH / PAGES_MISMATCH / VENUE_MISMATCH (journal) / YEAR_MISMATCH (off by 2 or more years) | Publication details do not match |
| ERROR | RETRACTED | Retracted |
| WARN | PREPRINT_PUBLISHED | A preprint is cited, but a journal version exists |
| WARN | HAS_ERRATUM / HAS_UPDATE | Has an erratum or update; check whether it affects the cited content |
| WARN | YEAR_MISMATCH (off by 1 year) | Usually the difference between the online and print years |
| INFO | MISSING_DOI / PAGES_FORM / VENUE_MISMATCH (conference proceedings) / BOOK_NOT_VERIFIED / JOURNAL_FIELDS_UNCHECKED | Notice, or needs manual confirmation |

## Phase 2: Manual review

- **Open the record for every ERROR and check it** (DOI landing page, arXiv page). The script may have matched the wrong paper (one with the same title), or the bib may simply use a different form (conference name, collaboration author name). After review, classify each one as a genuine error / script false positive.
- **NOT_FOUND**: search again with WebSearch by title and authors; if still not found, mark it as "suspected fabrication; the author must confirm the source".
- **HAS_ERRATUM**: read the erratum and check whether it changes the result cited in the text.
- **PREPRINT_PUBLISHED**: recommend citing the journal version instead; note whether the journal version's title or conclusions differ from the preprint.
- For survey md files: besides metadata, also check the **descriptive information** written in the md, such as institutions, platforms, methods, and "first" claims. These are not in the metadata; confirm them by reading the abstract or full text (this is where the Caesura entry went wrong).

## Phase 3: Claim support (second level)

```
python3 -I <skill-dir>/scripts/refcheck.py contexts main.tex --out refcheck/<date>     # or manuscript.docx / .md / .pdf
```

`contexts.md` lists, by reference, the sentence in which each citation occurs, and marks sentences that "attribute a result or property to the cited work" as **claim**. LaTeX manuscripts are grouped by `\cite` key; for other formats, the script recognizes `[n]` numeric citations (mapped to the n-th entry of the reference list) and "(Author et al., 2015)" author–year citations. Superscript numeric citations in Word cannot be recognized after conversion to text and need a manual check.

Check first:
1. sentences marked claim in the abstract, introduction, and conclusion;
2. sentences with specific numbers, or with "first", "optimal", "proved", or "impossible";
3. citations used as a premise of this paper or as a comparison baseline;
4. sentences that cite only a review yet state a specific result.

Judge each sentence following the procedure in `references/claim-support.md`, with four possible verdicts: supports / partially supports / does not support / cannot verify. When there are many citations, group them by citation key and dispatch subagents to check them in parallel; after the subagents return, the main session spot-checks at least 3 items.

## Phase 4: Report

Write `refcheck/<date>/summary.md` (in the user's language), with conclusions first:

1. **Must fix**: confirmed ERRORs (fabrication, wrong authors or volume, retraction) and claims the cited work does not support. For each, give the current state, the correct information, the evidence (record link), and the affected sentences.
2. **Should fix**: preprints that have since been published, errata, missing DOIs, partially supported claims (with suggested rewrites).
3. **Script false positives**: list them, to improve the script later.
4. **Cannot verify**: list the reasons.
5. Corrected bib entries are in `corrected.bib`. List only the entries that need changes; replace them after the user confirms.

## Final report to the user (concise, in the user's language)

- How many entries were checked in total: how many confirmed errors, how many suggested changes, how many could not be verified.
- The 3 most serious issues, one sentence each.
- Paths to the report and `corrected.bib`.
