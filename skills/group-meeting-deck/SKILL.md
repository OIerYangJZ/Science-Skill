---
name: group-meeting-deck
description: Build slides for a research group meeting (weekly progress update, journal club, project proposal, result deep-dive, talk rehearsal) as an editable PowerPoint file and optionally Beamer, in one of seven visual styles (clean, assertion-evidence, metropolis, campus, notebook, dark, minimal) chosen from a side-by-side gallery of the user's own slides. Content and style are kept apart - a Markdown spec holds what the talk says, so the style can change without touching it. Every number is traced to the results or the manuscript; status chips (verified, preliminary, negative, blocked) are checked against the dead-end-ledger so progress is not reported as more than it is, and negative results are not left out; talk length is counted from the speaker notes, not guessed; overflow, font size, contrast and figure resolution are measured on a rendered preview. Use when the user asks for group meeting slides, a progress report deck, journal-club slides, or a practice talk. Not for conference posters (research-poster).
argument-hint: "[results, manuscript or notes] [--template progress|journal-club|proposal|deep-dive|rehearsal] [--minutes 15] [--style name]"
---

# group-meeting-deck: honest group-meeting slides in a chosen style

## The problem this skill addresses

Slides are where research gets summarised under time pressure, and the observed failures are specific (`FAILURE_MODES.md`, the `talk-deck` entry and item 6):
- slides drafted by the author were rewritten without consent, hedged, or given numbers that replaced the figures the author had stated;
- talk length was estimated instead of counted;
- in long-running projects, progress was reported as more settled than the evidence, and failed routes went unmentioned.

A group meeting is where negative results, blockers and open questions are most useful, so the deck must show them at their real status.

## Hard rules

1. **The author's words and numbers win.** If the user supplies slides, notes or text, keep their wording; propose changes as a list and apply only the ones the user accepts. Never replace a number the author gave with one you computed.
2. **Every number comes from a source.** Copy numbers from the results files, the manuscript or the ledger, never from memory. `deck.py check --source` must report no NUM-NOT-IN-SOURCE, or each remaining one must be explained to the user (for example, a number from a file that was not passed in).
3. **Status at the ledger's strength.** Status chips (`{verified R1}`, `{preliminary R2}`, `{negative X1}`, `{blocked X2}`) follow the dead-end-ledger when one exists: no chip may claim more than the ledger records (STATUS-UPGRADE is a FAIL). Negative, blocked and inconclusive routes since the last meeting appear in the deck (NEGATIVE-OMITTED). A BLOCKED item is presented as a technical obstacle, not as evidence against the idea.
4. **Talk length is counted.** Write speaker notes for every content slide, or set `{time=…}` (minutes) on slides where the notes are cues. Report the counted total against the talking time (meeting length minus Q&A).
5. **The style is the user's choice.** Show the gallery of the user's own slides in every style and ask; do not pick silently unless the user named a style.
6. **Figures are the author's.** Use the author's figure files. Never redraw a data figure from memory or by retyping data. If a figure must be restyled (for example a dark background), regenerate it from the author's plotting script, change only cosmetic parameters, and say so.
7. **Do not overwrite.** Write to `deck/<YYYY-MM-DD>/` next to the project, add it to `.git/info/exclude` in a git repository, and never overwrite the user's existing slide files.
8. Talk to the user in their language; slide text is in the language the user wants for the meeting.

## Phase 0: Intake

Determine, asking only what cannot be inferred:
- **meeting type** → template: `progress` (default for "组会汇报" / "progress update"), `journal-club`, `proposal`, `deep-dive`, `rehearsal`;
- **length** in minutes and how much of it is discussion (default Q&A: a quarter);
- **audience**: advisor only, whole group, mixed fields;
- **language** of the slides;
- **sources**: results files (CSV, JSON, logs), notebooks, the manuscript, the paper being presented (journal club), figures, the previous deck (for "last time's plan"), and the dead-end-ledger if the project has one;
- **constraints**: a group template or institution colour (`--palette accent=#…`), aspect ratio (16:9 default, 4:3 for old projectors), PowerPoint or Beamer.

## Phase 1: Evidence ledger

Before any slide, write `deck/<date>/evidence.md` in the user's language:

| claim on a slide | exact number(s) | source (file, line or cell) | status (ledger ID) | condition that limits it |
|---|---|---|---|---|

- Include what failed or is blocked since the last meeting, from the ledger's routes table or the user's notes.
- Include the questions the presenter needs the group to answer.
- If the deck presents someone else's paper, the status column records the paper's own strength ("proved", "shown in mice", "suggested") and the figures are credited on the slide.

## Phase 2: Content spec

```
D="python3 -I <skill-dir>/scripts/deck.py"
$D templates
$D init --template progress --minutes 15 --lang zh --out deck/<date>/deck.md
```

Fill the spec from the evidence ledger (format: `references/spec-format.md`):
- one message per slide; the title states it ("The new loss plateaus higher", not "Results");
- numbers copied verbatim, with their comparator and n; conditions next to the number they limit;
- status chips with ledger IDs; negative results and blockers on their own slide;
- speaker notes (`???`) written as what will be said, or `{time=…}`;
- details that will not be presented go to `# Backup` slides (not counted in the timing).

Leave `[[placeholders]]` for anything the sources do not contain and list them for the user; do not invent.

## Phase 3: Style choice

```
$D gallery deck/<date>/deck.md --out deck/<date>/gallery
```

Show `gallery.png` (Read it) and ask the user to choose (AskUserQuestion with the style names and the "best for" line; recommend one based on the meeting type and content, for example metropolis for formula-heavy theory, notebook for many tables and status items, assertion for a deep-dive). The seven styles and when to use them are in `references/styles.md`.

## Phase 4: Render and inspect

```
$D render deck/<date>/deck.md --style <chosen> --format pptx[,tex] [--compile] [--quicklook] --out deck/<date>
```

- `deck.pptx` is the deliverable (editable, speaker notes included); `deck.tex` is Beamer source if requested.
- Read the preview PNGs (`preview/slide-NNN.png`; on macOS `--quicklook` also renders the .pptx itself). Look for text that is cut off, crowded slides, figures too small to read from the back of the room, and chips or colours that do not read.
- Fix the spec (not the .pptx) and re-render until the previews are clean.

## Phase 5: Check

```
$D check deck/<date>/deck.md --source <results and manuscript files> --ledger <LEDGER.md> --minutes 15 --out deck/<date>
```

`check.md` lists FAIL, WARN and INFO findings (codes in `references/checks.md`). Resolve every FAIL; read every WARN in context:
- CLAIM-STRONGER / QUALIFIER-DROPPED compare each slide sentence with the closest source sentence. They are leads, and "first" may be right if the source says it.
- TIMING-OVER: cut slides or move them to backup; do not speed up the speaking rate.

## Phase 6: Discussion preparation (optional, recommended before rehearsals)

Launch one subagent (effort high) with only the rendered previews and the speaker notes, not the evidence ledger, as a sceptical labmate or advisor. It returns the five hardest questions and the slide each one targets. Do not install software; report missing tools as not checked. The main session checks each question against the evidence ledger and drafts backup slides for the ones the deck cannot answer. Label the questions as simulated.

## Final report (in the user's language)

- Path of the `.pptx` (and `.tex` / `.pdf`), the style chosen, slide count.
- Counted talk length versus the time available.
- Check summary: remaining WARN items and why they stand; placeholders still open.
- Statuses shown: what is verified, preliminary, negative, blocked.
- Anything that could not be checked (no Chrome for previews, no ledger, a source not provided).
