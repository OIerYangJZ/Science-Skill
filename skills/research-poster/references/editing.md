# Editing the HTML poster

`poster.html` is the master copy. The PDF and the PNG previews are made from it; regenerate them after every change with `poster.py export poster.html`, or print from the browser.

## Three ways to edit

| Way | How | Good for |
|---|---|---|
| In the browser | Open `poster.html` (Chrome, Edge, Safari, Firefox). Press **Edit text**, click any text and type; press **Save HTML**. The browser saves a copy to your downloads folder: replace `poster.html` with it | Wording, numbers, captions |
| In an editor | Open `poster.html` in any text editor (VS Code, Sublime, TextEdit in plain-text mode) | Moving sections, adding figures, colours, sizes |
| Ask Claude | "Shorten the methods section", "move Ablation under Results", "make the accent our university red" | Anything; Claude edits the HTML in place, then exports and checks it |

After editing, the fit script runs again when the file is opened, so text grows or shrinks to fill the page. The toolbar shows the current text scale and marks overflowing columns with a dashed red outline (not printed).

## Structure

```html
<div class="poster" data-fit="auto">
  <header class="poster-header"> <h1>Title</h1> <div class="authors">…</div> <div class="affiliations">…</div> </header>
  <main class="poster-body">
    <div class="col" data-col="column 1">
      <section class="panel"> <h2>Question</h2> <ul><li>…</li></ul> </section>
      <section class="panel"> <h2>Approach</h2> <figure><img src="figures/x.svg"><figcaption>…</figcaption></figure> </section>
    </div>
    <div class="col" data-col="column 2"> … </div>
    <div class="col" data-col="column 3"> … </div>
  </main>
  <footer class="poster-footer"> <div class="part">Contact …</div> <div class="part"><h3>References</h3>…</div> </footer>
</div>
```

The billboard style has `<main class="poster-body billboard">` with a left column, a `<div class="center">` (the takeaway in `<p class="takeaway">`, key figures, QR code) and a right column.

| Task | Edit |
|---|---|
| Move a section | Cut the whole `<section class="panel">…</section>` and paste it into another column. Section numbers (minimal, storyboard) and figure letters (journal) follow automatically |
| Add a section | Copy an existing `<section class="panel">` and change it |
| Add a figure | `<figure><img src="figures/new.svg"><figcaption>What is plotted, n, error bars</figcaption></figure>`; put the file in `figures/` (SVG, PNG at 300 px/in at printed width, JPEG) |
| Narrower figure | `<figure style="width:70%; margin-left:auto; margin-right:auto">` |
| Highlight words | `<mark>…</mark>` (accent colour, bold) |
| Status chip | `<span class="chip" style="background:#0072B2; color:#FFFFFF">VERIFIED</span>` |
| Formula | `\( … \)` inline or `<div class="math-display">\[ … \]</div>`; MathJax is loaded from a CDN when the poster has formulas, so viewing and exporting need a network connection |
| Another column count | Add or remove a `<div class="col" data-col="column N">` and set `--cols` in `:root` |
| Fixed text size | `data-fit="off"` on `<div class="poster">`, then set `--scale` (for example `1.1`) in `:root` |

## Style variables (in `<style id="poster-style">`)

| Variable | Meaning |
|---|---|
| `--page-w`, `--page-h` and the `@page` rule | Page size; change both together (or use `poster.py restyle --size`) |
| `--u` | The page's short side ÷ 841 mm; all sizes scale with it |
| `--scale` | Text scale; the fit script sets it between 0.72 and 1.2 |
| `--bg`, `--fg`, `--muted`, `--accent`, `--accent2`, `--link` | Background, text, captions, accent colours, links |
| `--header-bg`, `--header-fg`, `--header-sub-fg` | Title band |
| `--panel-bg`, `--panel-line`, `--panel-radius`, `--panel-title-bg`, `--panel-title-fg` | Section boxes and headings |
| `--table-*`, `--code-*`, `--footer-fg`, `--center-bg`, `--center-fg` | Tables, code, footer, billboard centre |
| `--title-pt`, `--heading-pt`, `--body-pt`, `--takeaway-pt` | Font sizes at A0 and scale 1 |
| `--font-heading`, `--font-body` | Font stacks |

`poster.py restyle poster.html --style dark` writes `poster-dark.html` with another style block and the same content (`--in-place` to replace the file, `--palette accent=#…` for institution colours, `--size A0-landscape` for another page size). It also refreshes the toolbar and the fit script to the current version. Billboard and column styles have different structures and cannot be swapped this way.

## Exporting

- `poster.py export poster.html` writes `poster.pdf`, `poster-preview.png` and `poster-glance.png`, and reports the text scale and any overflow; it exits 1 on overflow.
- Or in the browser: **Print / Save as PDF**, destination "Save as PDF", margins **None**, **Background graphics** on, scale 100%. The page size comes from `@page`.
- Then `poster.py check poster.html --source …` before printing.
