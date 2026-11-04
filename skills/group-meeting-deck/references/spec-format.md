# Content spec format

One Markdown file holds what the slides (or the poster) say. The parser is `lib/slidespec.py`; the same format is used by `research-poster`.

## Front matter

Simple `key: value` lines between `---` lines (not full YAML).

| Key | Used for |
|---|---|
| `title`, `subtitle` | Cover slide |
| `presenter`, `group`, `date`, `venue` | Cover slide and footers |
| `style` | Default style (overridden by `--style`) |
| `palette` | Colour overrides, e.g. `accent=#0B5394,fg=#222222` |
| `font` | One font for headings and body |
| `minutes`, `qa` | Meeting length and discussion time, for the timing check |
| `since` | Date of the previous meeting; ledger routes since then must be mentioned |
| `source` | Comma-separated results files or manuscript, for the number trace |
| `ledger` | dead-end-ledger file, for the status check |
| `footer` | Text in the footer of every slide |
| `cover` | `no` to omit the cover slide |
| `notes` | Speaker notes of the cover slide |
| `beamer-theme` | With the `beamer` style: the Beamer theme for `--format tex` (default Madrid) |

## Body

| Syntax | Meaning |
|---|---|
| `# Heading` | Section divider slide. `# Backup` (or Appendix, 备用, 附录) starts backup slides |
| `## Heading {attrs}` | A slide; the heading is its title |
| `{layout=split\|columns\|stack\|statement\|figure}` | Force a layout (default: chosen from the content) |
| `{time=1.5}` | Planned minutes for the slide (overrides the notes for timing) |
| `{backup}` | This slide is a backup slide |
| `{widths=40,60}` | Column proportions for `:::` columns |
| `{image=left}` | In a split layout, put the figure on the left |
| `{center}` | Centre the content vertically |
| Paragraph text | `**bold**`, `*italic*`, `` `code` ``, `$x^2$`, `[text](url)`, `==highlight==` |
| `- item` / `1. item` | Bullets / numbered items; indent two spaces per level |
| `- {verified R2} text` | Status chip; the ID (optional) refers to a dead-end-ledger row |
| `![Caption](path){width=70%}` | Figure: PNG, JPEG, GIF, SVG or PDF (converted for PowerPoint) |
| `\| a \| b \|` rows | Table; the first row is the header |
| `$$ ... $$` | Display formula: rendered with LaTeX when installed, else Unicode text |
| `> text` | Key message; a slide with only a quote becomes a statement slide. In the `beamer` style it is a block; `> text {title="Result"}` adds the block title |
| ```` ``` ```` fences | Code block |
| `:::` | Column break |
| `???` | Speaker notes for this slide follow, until the next heading |
| `<!-- ... -->` | Comment, ignored |
| `[[...]]` | Placeholder; `check` fails until it is replaced |

Status words: verified, unverified, conditional, preliminary, negative, retracted, done, in-progress, partial, inconclusive, failed, blocked, planned, dropped, succeeded.

## Layout rules

- A slide with `:::` breaks is laid out in columns.
- One figure with more than about 25 words of text: text left, figure right (`split`), except in the assertion style.
- Otherwise elements stack top to bottom; figures take the remaining height, keeping their aspect ratio.
- Text shrinks in steps down to the style minimum (18 pt); then the slide is reported as OVERFLOW.
