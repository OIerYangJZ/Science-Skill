# Poster styles

Six styles, all rendered from the same content spec. `poster.py gallery` shows the user's own poster in each one; `poster.py styles` prints this list. Font sizes are defined for A0 and scale with the short side of the board (A1 ≈ 0.71×, A2 ≈ 0.5×).

| Style | Looks like | Best for | Avoid when |
|---|---|---|---|
| `classic` (default) | Full-width navy title banner, boxed sections with coloured header bars, 3 columns portrait / 4 landscape, serif headings | Traditional conference sessions, any field; what judges expect | You need to stand out in a hall of identical posters |
| `billboard` | Mike Morrison's #betterposter: one plain-language finding in huge type in a coloured centre column, key figure and QR code below it; methods and details in narrow side columns | Busy halls where people decide in seconds; results with one clear message | Work whose contribution is many small results; theory without a one-line statement |
| `minimal` | White space, strict grid, black type, numbered headings (01, 02, ...) with one red-orange rule | HCI, CS, design and architecture venues; few strong figures | Dense multi-panel biology |
| `dark` | Deep slate background, cyan and amber accents, cards for sections; light figures framed | Machine learning, astronomy, imaging, visualisation; digital poster sessions and screens | Printing on paper (ink, banding) unless the printer has been tested |
| `journal` | Editorial: serif title, thin rules instead of boxes, small-caps section labels, figure panels labelled a, b, c | Life and physical sciences with multi-panel figures; posters that mirror a paper | Public audiences |
| `storyboard` | Numbered cards on a warm background that read as a sequence | Method pipelines, interdisciplinary and public audiences, student symposia | Results that do not follow a sequence |

## Size and layout

- `size:` A0, A1, A2, A3, B1, `A0-landscape`, `48x36in`, `36x48in`, `42x36in`, `36x24in`, or custom `900x1200mm`. Use the venue's board size, from its official page.
- `columns:` overrides the column count. With little content, fewer columns give larger figures.
- Text is fitted by measurement: it grows up to 120% of the style default when there is room and shrinks down to 72% when there is not. Below the readable minimum (24 pt at A0, scaled) the check fails.
- Figures are never wider than their column; the `SPARSE` hint suggests fewer columns when columns are mostly empty.

## Typography at A0 (scaled for other sizes)

| Element | Default | Readable minimum |
|---|---|---|
| Title | 96 pt (60 pt in billboard, where the takeaway is the headline) | - |
| Takeaway (billboard) | 118 pt, shrinks to fit | 60 pt |
| Section headings | 50 pt | - |
| Body | 30 pt | 24 pt |
| Captions | 0.78 × body | - |
| Footer, references | 20 pt | - |

## Sources for the design choices

- Billboard layout: M. Morrison, "How to create a better research poster in less time (#betterposter)", video and templates (2019).
- Colour-blind-safe palette: M. Okabe and K. Ito, *Color Universal Design* (2008); B. Wong, "Points of view: Color blindness", *Nature Methods* 8, 441 (2011), doi:10.1038/nmeth.1618.
- Contrast thresholds: WCAG 2.1, success criterion 1.4.3.
