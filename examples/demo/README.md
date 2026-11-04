# Synthetic demo: a progress-update deck and a poster

Everything in this folder is invented for trying `group-meeting-deck` and `research-poster`; no real project or data is involved.

| File | What it is |
|---|---|
| `deck.md` | Content spec of a 12-minute progress update (status chips with ledger IDs, notes, declared times, backup slide) |
| `poster.md` | Content spec of an A0 poster from the same "project" |
| `results.csv`, `config.json` | The sources the numbers are traced to |
| `LEDGER.md` | A small dead-end-ledger: one verified result, one preliminary, one negative route, one blocked route |
| `make_figures.py`, `figures/*.svg` | Figures drawn with the standard library |

```bash
D=skills/group-meeting-deck/scripts/deck.py
P=skills/research-poster/scripts/poster.py
python3 $D gallery examples/demo/deck.md --out /tmp/demo-gallery        # every slide style
python3 $D render examples/demo/deck.md --style metropolis --format pptx,tex --out /tmp/demo-deck
python3 $D check examples/demo/deck.md --out /tmp/demo-deck             # FAIL 0 · WARN 0; talk ≈ 8.2 min
python3 $P gallery examples/demo/poster.md --out /tmp/demo-pgallery     # every poster style
python3 $P render examples/demo/poster.md --style billboard --out /tmp/demo-poster
python3 $P check examples/demo/poster.md --out /tmp/demo-poster         # FAIL 0; INFO SPARSE (little content)
```

The style galleries in the main README (`docs/img/`) were rendered from these two files.
