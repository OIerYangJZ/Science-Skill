# Check codes (`poster.py check`)

The exit code is 1 when any FAIL remains, otherwise 0. Every finding is a lead to read in context.

| Code | Level | Meaning | Typical fix |
|---|---|---|---|
| PLACEHOLDER | FAIL | `[[...]]`, TODO, TBD, XX or ?? left | Fill from the sources or delete |
| NUM-NOT-IN-SOURCE | FAIL | A number on the poster does not occur in any source | Copy it from the source; or pass the file it comes from |
| NUM-SCALED / NUM-ROUNDED | WARN / INFO | Percent-versus-fraction match / rounded form | Confirm |
| CLAIM-STRONGER | WARN | A strength word absent from the closest source sentence | Use the source's strength |
| QUALIFIER-DROPPED | WARN | A condition in the closest source sentence is missing | Keep the condition next to the result |
| OVERFLOW | FAIL | A column does not fit even with text at 72%, or a text box overflows in the rendered preview | Cut words, remove a panel, or use a larger board |
| FONT-MIN | FAIL | Body text below 24 pt at A0 (scaled) | Cut words |
| FONT-SHRUNK | INFO | Body text set below the style default | Consider cutting words |
| NO-TAKEAWAY | FAIL (billboard) / INFO | No takeaway sentence | Write one from the claim ledger |
| MISSING | FAIL / WARN | No title or authors / no contact and no QR code | Add them |
| WORDS | WARN / INFO | Word count above the style's suggestion (800; billboard 500) | Move detail to the paper or a handout |
| SPARSE | INFO | Columns mostly empty | Fewer columns, larger figures, or a smaller board |
| SIZE / ORIENTATION | FAIL | Larger than the venue's board, or the wrong orientation | Use the venue size |
| CONTRAST | FAIL / INFO | A text colour pair below 4.5:1 (3:1 for large text) | Change the palette override |
| CVD | WARN | Accent colours that collapse under a colour-vision deficiency | Do not let colour alone carry meaning |
| IMG-RESOLUTION | FAIL (< 100 px/in), WARN (< 150 px/in) | Raster figure too coarse at its printed size | Export at 300 px/in at the printed size, or as PDF/SVG |
| IMG-MISSING, IMG-UNREADABLE, IMG-CONVERT | FAIL | A figure or logo cannot be used | Fix the path or export PNG/PDF |
| STATUS-* | as for slides | With `--ledger`, status chips are checked against dead-end-ledger | |
