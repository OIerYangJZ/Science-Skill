---
name: research-poster
description: Build a research poster from a manuscript or results as an editable PowerPoint file and a print-ready PDF at the exact board size (A0, A1, A2, US 48x36 in, either orientation, or custom), in one of six styles (classic conference, billboard / betterposter, minimal grid, dark, journal figure page, storyboard) chosen from a gallery of the user's own poster. Content and style are kept apart, so the style can change without touching the text. Board size comes from the venue's official page; the takeaway and every number are traced to the source so claims are neither strengthened nor stripped of their conditions; text is fitted by measurement, and the check fails on overflow, text below the readable minimum, figures below print resolution, low contrast, colours that collapse under colour-vision deficiency, or a poster larger than the board. An independent reader tests what a passer-by takes away. Use when the user asks for a conference poster. Not for slides (group-meeting-deck).
argument-hint: "[manuscript or results] [--size A0|A0-landscape|48x36in] [--style name] [venue]"
---

# research-poster: a poster that says what the paper says, in a chosen style

## The problem this skill addresses

A poster compresses a paper for a reader who gives it seconds, then minutes. Compression is where the failures recorded in `FAILURE_MODES.md` reappear:
- claims get stronger, or lose their conditions (item 2);
- numbers are retyped and drift from the source (item 3);
- summaries written for an audience are rewritten without the author's consent (the `talk-deck` entry);
- venue requirements are recalled from memory (item 8). For example, a talk submission is not automatically considered for the poster track.

Physical failures add to this: text too small to read from two metres, figures that print blurred, a board size that does not match the venue.

## Hard rules

1. **The paper's strength, not more and not less.** The takeaway and every panel title are written from a claim ledger, and each carries the condition that limits it. If the user supplies their own text, keep it and propose changes as a list.
2. **Every number comes from the source.** Copy numbers from the manuscript or the results files. `poster.py check --source` must show no NUM-NOT-IN-SOURCE, or each remaining one must be explained to the user.
3. **Venue facts from the venue.** Board size, orientation, deadlines for printing or upload, and any required template come from the venue's official page, with the URL and the date checked (the same rule as `venue-fit`). Unknown stays unknown: ask, and default to A0 portrait only with the user's agreement.
4. **The style is the user's choice.** Show the gallery of the user's own poster in every style and ask, unless the user named a style.
5. **Figures are the author's.** Use the author's figure files, vector (PDF/SVG) or high-resolution PNG. Never redraw data figures. Restyling (for example for the dark style) means regenerating from the author's script with cosmetic changes only.
6. **Do not overwrite.** Write to `poster/<YYYY-MM-DD>/`, add it to `.git/info/exclude` in a git repository, and never overwrite existing poster files.
7. **Nothing is sent or printed for the user.** No uploads to a print service or the venue.
8. Talk to the user in their language; poster text is in the language of the venue.

## Phase 0: Intake

- **Source:** manuscript (LaTeX, Word, Markdown, PDF), results files, figures, logos, and the link the QR code should point to. If a QR code is wanted, the user supplies the image; the skill does not generate one.
- **Venue:** name and the poster instructions page. Record size, orientation, mounting, digital or printed, and any template, each with URL and date. If the user does not know, say what is unknown.
- **Audience:** specialists, a broad conference, the public.
- **Constraints:** institution colours (`palette: accent=#…`), required logos, language, deadline.

## Phase 1: Claim ledger

Write `poster/<date>/claims.md` in the user's language:

| poster element | text (draft) | source location | exact numbers | condition kept next to it | strength word in source |
|---|---|---|---|---|---|

Cover:
- the takeaway (one sentence a passer-by can repeat);
- the title;
- every panel title;
- every number;
- the limitation a visitor is most likely to ask about.

If `paper-polish` produced a claim ledger, start from it.

## Phase 2: Content spec

```
P="python3 -I <skill-dir>/scripts/poster.py"
$P sizes
$P init --template empirical|theory|billboard --size A0 --lang en --out poster/<date>/poster.md
```

Fill the spec from the claim ledger (format: `references/spec-format.md`):
- 300–800 words in total (billboard: at most 500);
- one finding per panel, stated in the panel title;
- figures with captions that say what is plotted, n, and what the error bars mean;
- `{col=N}` to fix the reading order across columns;
- `{footer}` for references and acknowledgements;
- `{center}` for the key figure in the billboard style.

Leave `[[placeholders]]` for anything missing and list them.

## Phase 3: Style choice

```
$P gallery poster/<date>/poster.md --out poster/<date>/gallery
```

Show `gallery.png` (Read it) and ask the user to choose (AskUserQuestion with the style names and the "best for" line; recommend one). When to use each style is in `references/styles.md`.

## Phase 4: Render and inspect

```
$P render poster/<date>/poster.md --style <chosen> [--size A0-landscape] --out poster/<date>
```

Outputs:
- `poster.pptx`: one editable slide at the printed size;
- `poster.pdf`: the print file;
- `preview.png`;
- `glance.png`: about how the poster looks from a few metres away.

Read both PNGs:
- does the takeaway read at glance size?
- is the reading order obvious?
- does any panel look empty or crowded?
- are figure labels legible?

Fix the spec and re-render. The layout scales text between 72% and 120% of the style default to fit. If it shrinks, cut words rather than accept small text.

## Phase 5: Check

```
$P check poster/<date>/poster.md --source <manuscript and results> --max-size <venue size> --out poster/<date>
```

Resolve every FAIL (codes in `references/checks.md`): placeholders, numbers not in the source, overflow, body text below the minimum, figures below 100 px/in at print size, contrast, missing takeaway (billboard), size or orientation beyond the venue's board. Read each WARN in context (CLAIM-STRONGER, QUALIFIER-DROPPED, IMG-RESOLUTION below 150 px/in, CVD, WORDS).

## Phase 6: Passer-by test

Launch one subagent (effort high) that sees only `glance.png` and then `preview.png`, not the paper or the claim ledger. It answers:
1. after a glance: what is this poster's main finding, in one sentence?
2. after reading: the finding with its conditions; the headline number and its comparator; what was done; the one question it would ask the presenter.

Do not install software; report missing tools as not checked. The main session compares the answers with the claim ledger:
- a finding stated more strongly than the ledger, or without its condition, means the poster misleads; revise and re-test;
- a finding the reader could not find means the hierarchy is wrong.

Label the result as a simulated reader.

## Final report (in the user's language)

- Paths of `poster.pptx` and `poster.pdf`, style, size (with the venue source and date checked).
- Body text size and word count; check summary with remaining WARN items and why they stand.
- Passer-by test: what the reader took away versus the claim ledger.
- Placeholders still open; facts still unknown (for example, the board size if the venue page did not say); anything not checked.
