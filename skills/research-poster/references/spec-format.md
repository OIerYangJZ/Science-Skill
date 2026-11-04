# Poster content spec

Same Markdown format as `group-meeting-deck` (see `lib/slidespec.py` and `skills/group-meeting-deck/references/spec-format.md`), with these poster-specific parts.

## Front matter

| Key | Used for |
|---|---|
| `title` | Poster title (at most two lines at the title size) |
| `authors`, `affiliations` | Header; use superscripts ¹ ² for affiliations |
| `contact` | Footer (email, URL) |
| `venue` | For the record and the footer |
| `takeaway` | The one-sentence finding; required by the billboard style; `==words==` are highlighted |
| `size` | Board size (`A0`, `A0-landscape`, `48x36in`, `900x1200mm`, ...) |
| `max-size` | The venue's limit, checked by `check` (or `--max-size`) |
| `columns` | Column count override |
| `style`, `palette`, `font` | As for slides |
| `logos` | Comma-separated image paths, placed at the right of the header |
| `qr`, `qr-label` | QR code image (supplied by the user) and its label |
| `footer` | Extra footer text |
| `source` | Manuscript and results files, for the number and claim trace |

## Panels

- `## Heading` starts a panel. Level-1 headings are not panels (in the billboard style the first one is used as the takeaway if the front matter has none).
- `{col=N}` pins a panel (and the unpinned panels after it) to column N. Without any `col`, panels are split into columns in reading order so that the columns have about equal height.
- `{footer}` sends a panel (references, acknowledgements, funding) to the footer band in small type.
- `{center}` (or `{key}`) puts a panel in the centre column under the takeaway in the billboard style; in other styles it is an ordinary panel.
- In the journal style, figures are labelled a, b, c in reading order; set `{label=d}` on an image to override.
- `> statement` gives a highlighted statement, useful for a theorem or the main result.
