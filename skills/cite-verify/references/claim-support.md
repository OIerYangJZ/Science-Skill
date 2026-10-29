# Claim-support check procedure

## 1. For each "sentence + citation"

1. **Extract the claim.** What does the sentence attribute to the cited work? Write it as a single checkable statement, e.g., "[12] proved that X requires Ω(n log n) queries under condition C".
2. **Locate the source text.** Read the abstract first; if the claim involves a specific theorem, number, or condition, find the corresponding theorem or section number. Sources of the original text, in order: arXiv full text (`https://arxiv.org/abs/<id>`), the publisher's open-access page, LibKey or institutional access. WebFetch returns text rewritten by a model; use it only for locating, never for verbatim quotation.
3. **Judge.**

| Verdict | Criterion |
|---|---|
| supports | The source explicitly states this result, under the same or broader conditions |
| partially supports | The source gives a weaker result or narrower conditions, offers only numerical evidence or a conjecture, or the result holds only in special cases |
| does not support | The source does not contain this result, or states the opposite, or the wrong work is cited (common with another paper by the same authors) |
| cannot verify | The full text is unavailable and the abstract is not enough to decide |

4. **Record the evidence**: cite the relevant location in the source (theorem or section number, plus a quotation of at most 40 words), and give a suggested rewrite.

## 2. Common error patterns

- **Upgrading**: the source offers a conjecture, a heuristic, or a numerical observation, but the text says "proved" or "showed".
- **Scope extrapolation**: the source addresses only a particular model or parameter range, but the text states it as a general result.
- **Misattribution**: the result comes from another paper by the same group of authors, or from a work that the cited work itself cites.
- **Outdated**: later work has improved on or overturned the result, but the text still says "the best known". In this case, use novelty-audit's `citing` command to find follow-up work on the cited paper.
- **Review as proxy**: a review is cited to support a specific technical result. Cite the original work instead.
- **Misstated self-citation**: the authors' own earlier work is described as stronger than it actually is.

## 3. Record format (`refcheck/<date>/claims.md`)

| key | location | sentence in the text (excerpt) | extracted claim | source evidence (theorem/section + excerpt) | verdict | suggested rewrite |
|---|---|---|---|---|---|---|

## 4. Subagent task prompt (use when grouping by citation key)

```
You check whether cited sources support the sentences that cite them.
For each item below (key, sentence, location), open the source (arXiv or
publisher open-access page), find the specific result, and classify as:
supports / partially supports / does not support / cannot verify.
Quote at most 40 words of the source with its theorem/section number.
Do not rely on memory of the paper; if you cannot access the text, say so.
Answer in the user's language (the main session states it); quotes in English.
<items>
```
