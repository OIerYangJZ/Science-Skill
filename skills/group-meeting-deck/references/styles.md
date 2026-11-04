# Slide styles

Seven styles, all rendered from the same content spec. `deck.py gallery` shows the user's own slides in each one; `deck.py styles` prints this list. Every style passes the contrast check (text at least 4.5:1, large text at least 3:1) with its default colours; `--palette` overrides are checked again by `deck.py check`.

| Style | Looks like | Best for | Avoid when |
|---|---|---|---|
| `clean` (default) | White, sans-serif, short navy bar under each title, page numbers | Weekly progress updates, mixed audiences, handouts | You want the deck to look like a formal institution template |
| `assertion` | Full-sentence claim as each title, evidence (figure or table) as the body, few bullets; thin full-width rule | Result deep-dives, conference rehearsals; every slide makes one memorable point | Slides that are lists of status items |
| `metropolis` | Dark teal title bar, orange progress line, flat; in the spirit of the Beamer metropolis theme | Mathematics, theory, computer science; formula-heavy talks; pairs naturally with `--format tex` | Audiences that expect institution branding |
| `campus` | Header band in the institution colour, gold divider, three-part footer (presenter, title, date and page), serif titles | Formal group meetings, milestone and committee reviews | Very short informal updates |
| `notebook` | Project strip with the date on every slide, compact titles, zebra tables, status chips stand out | Progress reports with many runs, tables and statuses; one-to-one advisor meetings | Pitches and talks for outsiders |
| `dark` | Deep slate background, cyan and amber accents; white-background figures framed as cards | Code, simulations, imaging, astronomy; dim rooms and screen sharing | Printed handouts; rooms with bright projectors that wash out dark slides |
| `minimal` | Large light titles, lots of white space, one red accent, at most about 30 words per slide | Short updates, proposals, idea pitches where you talk and the slide anchors | Detailed result reviews |

## Choosing

- The meeting type is a better guide than taste: progress → `clean` or `notebook`; journal club → `clean`; proposal → `minimal`; deep-dive → `assertion`; rehearsal → whatever the external venue expects (`metropolis` for theory, `assertion` for experimental talks).
- Institution colours: `--palette accent=#RRGGBB` (also `fg`, `bg`, `muted`, `title_bg`, ...). Derived colours (table headers, title band, section slides) follow the accent unless set explicitly. Run `check` afterwards: some brand colours fail contrast as text.
- One font for everything: `--font "Source Sans 3"`. PowerPoint substitutes fonts that are not installed on the presenting machine, so prefer fonts available there.

## Design rules built into every style

- Body text 22 pt by default (19-26 by style); it shrinks to fit down to 18 pt, never below. A slide that still does not fit is reported as OVERFLOW: split it.
- Status chips always carry their word (VERIFIED, PRELIMINARY, NEGATIVE, BLOCKED...), so colour is never the only cue; chip colours come from the Okabe-Ito palette.
- Titles longer than two lines are shrunk once and reported (TITLE-LONG).
- Backup slides (after a `# Backup` / `# 附录` heading, or with `{backup}`) are numbered "Backup" and excluded from the timing.

## Sources for the design choices

- Assertion-evidence structure: M. Alley, *The Craft of Scientific Presentations*, 2nd ed. (Springer, 2013), doi:10.1007/978-1-4419-8279-7.
- Colour-blind-safe palette: M. Okabe and K. Ito, *Color Universal Design* (2008); B. Wong, "Points of view: Color blindness", *Nature Methods* 8, 441 (2011), doi:10.1038/nmeth.1618.
- Contrast thresholds: WCAG 2.1, success criterion 1.4.3.
