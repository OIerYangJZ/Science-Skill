# Check codes (`deck.py check`)

The exit code is 1 when any FAIL remains, otherwise 0. Every finding is a lead to read in context.

| Code | Level | Meaning | Typical fix |
|---|---|---|---|
| PLACEHOLDER | FAIL (slides), WARN (notes) | `[[...]]`, TODO, TBD, XX or ?? left | Fill from the sources or delete |
| NUM-NOT-IN-SOURCE | FAIL | A number on a slide or in the notes does not occur in any source | Copy the number from the source; or pass the file it comes from with `--source` |
| NUM-SCALED | WARN | Matches a source number only after ×100 or ÷100 | Check percent versus fraction |
| NUM-ROUNDED | INFO | A rounded form of a source number | Fine if the rounding is intended |
| CLAIM-STRONGER | WARN | The slide sentence adds a strength word (first, significant, proves, optimal, outperforms, ...) absent from the closest source sentence | Use the source's strength, or confirm the source supports it elsewhere |
| QUALIFIER-DROPPED | WARN | A condition or hedge in the closest source sentence (under, if, in mice, preliminary, up to, ...) is missing on the slide | Put the condition next to the number |
| STATUS-UPGRADE | FAIL | A chip claims more than the ledger (DONE or VERIFIED for an UNVERIFIED or PRELIMINARY row) | Use the ledger status, or get the result verified first |
| STATUS-UNKNOWN-ID | WARN | A chip's ID is not in the ledger | Fix the ID or add the row |
| STATUS-NO-ID | INFO | A VERIFIED/DONE chip without a ledger ID | Add the ID so it can be checked |
| STATUS-WEAKER | INFO | A chip is more cautious than the ledger | Fine; consider updating the ledger |
| NEGATIVE-OMITTED | WARN | A FAILED, NEGATIVE, BLOCKED, INCONCLUSIVE, PARTIAL or RETRACTED ledger row (since `since`) is not mentioned | Add it to the "what did not work" slide |
| TIMING-OVER | FAIL | Counted speaking time exceeds the talking time by more than 10% | Cut or move slides to backup |
| TIMING-UNDER | WARN | Counted time is under 60% of the talking time | Add notes, or plan for more discussion |
| TIMING-ASSUMED | WARN | Content slides with neither notes nor `{time=}`: their time is assumed | Write notes or declare the time |
| OVERFLOW | FAIL | Text does not fit at the minimum size, or a text box overflows in the rendered preview | Split the slide; move detail to notes or backup |
| TITLE-LONG | WARN | Title runs to three or more lines | Shorten the title |
| DENSE | WARN | More words than the style suggests | Move detail to the notes |
| BULLETS | WARN | More than seven bullets | Group or split |
| TITLE-NOT-CLAIM | WARN | Assertion style with a title of fewer than five words | Write the claim as a sentence |
| FONT-SHRUNK | INFO | Body text was reduced to fit | Consider cutting words |
| CONTRAST | FAIL / INFO | A text colour pair below 4.5:1 (3:1 for large text) | Change the palette override |
| CVD | WARN | Accent colours that collapse under protan-, deutan- or tritanopia | Do not let these two colours alone carry meaning |
| IMG-MISSING, IMG-UNREADABLE, IMG-CONVERT | FAIL | A figure file is missing or cannot be used | Fix the path or export PNG/PDF |
| IMG-RESOLUTION | FAIL (< 60 px/in), WARN (< 110 px/in) | Raster figure too small for a 1920-pixel projector at its placed size | Export at higher resolution or as vector |
| SOURCE, LEDGER, NO-SOURCE | WARN / INFO | A source or ledger could not be read, or none was given | Pass the files |

Speaking rates for the timing: 130 English words per minute and 250 CJK characters per minute by default (`--wpm`, `--cpm`).
