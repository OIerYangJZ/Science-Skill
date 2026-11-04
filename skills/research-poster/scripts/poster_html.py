"""poster_html.py - the editable HTML poster: build it from a content spec, export it, inspect it, restyle it.

The HTML file is the master copy. It is plain, hand-editable HTML and CSS:
- every section is a <section class="panel"> inside a <div class="col">; move a section to another column
  by moving the element;
- colours, fonts and sizes are CSS variables in the <style id="poster-style"> block at the top;
- the page size is the CSS @page rule, so the browser's own "Print > Save as PDF" gives the print file;
- a small script fits the text to the page (scale between 72% and 120%) every time the file is opened,
  so edits reflow; set data-fit="off" on .poster to keep a fixed --scale;
- section numbers and figure letters are CSS counters, so they follow the order of the sections;
- a screen-only toolbar edits text in the browser, saves the edited HTML, re-fits and prints.
"""
from __future__ import annotations

import html as H
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "lib")))
import designkit as dk          # noqa: E402
import slidespec as ss          # noqa: E402

A0_SHORT_MM = 841.0
SANS_STACK = "'Helvetica Neue', Helvetica, 'PingFang SC', 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif"
SERIF_STACK = "'Times New Roman', 'Songti SC', 'Noto Serif CJK SC', SimSun, serif"


def font_stack(name: str) -> str:
    serif = name.lower() in ("georgia", "times new roman", "cambria", "garamond", "palatino")
    return f"'{name}', " + (SERIF_STACK if serif else SANS_STACK)


# ---------------------------------------------------------------------------
# CSS for a style
# ---------------------------------------------------------------------------
def css_for(st: dict, size_in: tuple[float, float], ncols: int) -> str:
    w_mm, h_mm = size_in[0] * 25.4, size_in[1] * 25.4
    u = min(w_mm, h_mm) / A0_SHORT_MM
    boxed = bool(st.get("panel_bg") or st.get("panel_line"))
    kind = st["panel_title"]
    v = {
        "page-w": f"{w_mm:.1f}mm", "page-h": f"{h_mm:.1f}mm", "u": f"{u:.4f}", "scale": "1", "cols": str(ncols),
        "bg": st["bg"], "fg": st["fg"], "muted": st["muted"], "accent": st["accent"], "accent2": st["accent2"],
        "link": st["link"], "header-bg": st.get("header_bg") or "transparent", "header-fg": st["header_fg"],
        "header-sub-fg": st["header_sub_fg"], "panel-bg": st.get("panel_bg") or "transparent",
        "panel-line": st.get("panel_line") or "transparent", "panel-radius": f"{st.get('panel_radius', 0) * 25.4:.1f}mm",
        "panel-title-bg": st.get("panel_title_bg") or "transparent", "panel-title-fg": st["panel_title_fg"],
        "table-head-bg": st["table_head_bg"], "table-head-fg": st["table_head_fg"], "table-bg": st["table_bg"],
        "table-zebra": st.get("table_zebra") or st["table_bg"], "table-border": st["table_border"],
        "code-bg": st["code_bg"], "code-fg": st["code_fg"], "footer-fg": st["footer_fg"],
        "center-bg": st.get("center_bg") or st["accent"], "center-fg": st.get("center_fg") or "#FFFFFF",
        "title-pt": f"{st['title_pt']}pt", "heading-pt": f"{st['heading_pt']}pt", "body-pt": f"{st['body_pt']}pt",
        "takeaway-pt": f"{st.get('takeaway_pt', 110)}pt",
        "font-heading": font_stack(st["font_heading"]), "font-body": font_stack(st["font_body"]),
    }
    root = "\n".join(f"  --{k}: {val};" for k, val in v.items())
    title_rules = {
        "bar": """.panel h2 { background: var(--panel-title-bg); color: var(--panel-title-fg);
  margin: calc(-1 * var(--pad)) calc(-1 * var(--pad)) var(--pad); padding: calc(0.55 * var(--pad)) var(--pad);
  border-radius: var(--panel-radius) var(--panel-radius) 0 0; }""",
        "text": ".panel h2 { color: var(--panel-title-fg); }",
        "rule": """.panel h2 { color: var(--panel-title-fg); border-bottom: calc(3mm * var(--u)) solid var(--accent);
  padding-bottom: calc(2mm * var(--u)); }
.panel h2::before { content: counter(panel, decimal-leading-zero) "\\00a0\\00a0"; color: var(--accent); }""",
        "caps": """.panel h2 { color: var(--panel-title-fg); text-transform: uppercase; letter-spacing: 0.04em;
  font-size: calc(0.72 * var(--heading-pt) * var(--u) * var(--scale)); border-top: calc(1.2mm * var(--u)) solid var(--fg);
  padding-top: calc(3mm * var(--u)); }""",
        "number": """.panel h2 { color: var(--panel-title-fg); display: flex; align-items: center; gap: 0.35em; }
.panel h2::before { content: counter(panel); flex: none; width: 1.45em; height: 1.45em; border-radius: 50%;
  background: var(--accent); color: #FFFFFF; display: inline-flex; align-items: center; justify-content: center;
  font-size: 0.8em; }""",
    }[kind]
    header_rule = ""
    if not st.get("header_bg") and st["name"] in ("minimal", "journal", "billboard"):
        line = "var(--accent)" if st["name"] == "minimal" else "var(--fg)"
        thick = "3mm" if st["name"] == "minimal" else "1.5mm"
        header_rule = f".poster-header {{ border-bottom: calc({thick} * var(--u)) solid {line}; }}"
    labels = """figure { counter-increment: fig; position: relative; }
figure::before { content: counter(fig, lower-alpha); position: absolute; left: 0; top: 0; font-weight: 700;
  font-size: calc(0.9 * var(--body-pt) * var(--u) * var(--scale)); background: var(--bg); padding: 0 0.25em; }""" \
        if st.get("figure_labels") else ""
    frame = ".panel figure img { background: #FFFFFF; padding: calc(3mm * var(--u)); border-radius: calc(3mm * var(--u)); }" \
        if st.get("frame_images") else ""
    stretch = ".col > .panel:last-child { flex-grow: 1; }" if boxed else ""
    head_band = """.poster-header { background: var(--header-bg); margin: calc(-1 * var(--margin)) calc(-1 * var(--margin)) 0;
  padding: calc(0.8 * var(--margin)) var(--margin); }""" if st.get("header_bg") else ""
    title_align = {"c": "center", "l": "left", "r": "right"}[st["title_align"]]
    pad = "calc(12mm * var(--u))" if boxed else "0mm"
    return f"""/* ===== Poster style: {st['name']} ({st['label']}) =====
   Edit the variables below to change colours, fonts and sizes. Sizes are for A0 and are multiplied by --u
   (the page's short side / 841 mm) and by --scale (set by the fit script, 0.72-1.2).
   `poster.py restyle` replaces this whole <style> block and keeps the content. */
@page {{ size: {w_mm:.1f}mm {h_mm:.1f}mm; margin: 0; }}
:root {{
{root}
  --margin: calc(25mm * var(--u));
  --gap: calc(16mm * var(--u));
  --pad: {pad};
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.poster {{ width: var(--page-w); height: var(--page-h); overflow: hidden; position: relative;
  display: flex; flex-direction: column; padding: var(--margin); gap: var(--gap);
  background: var(--bg); color: var(--fg); font-family: var(--font-body);
  font-size: calc(var(--body-pt) * var(--u) * var(--scale)); line-height: 1.3; counter-reset: panel fig; }}
.poster-header {{ display: flex; align-items: center; gap: var(--gap); text-align: {title_align}; }}
.poster-header .titles {{ flex: 1; }}
.poster-header h1 {{ font-family: var(--font-heading); font-size: calc(var(--title-pt) * var(--u) * var(--scale));
  line-height: 1.06; margin: 0; color: var(--header-fg); font-weight: {700 if st.get('title_bold', True) else 400}; }}
.poster-header .authors {{ font-size: calc(40pt * var(--u) * var(--scale)); font-weight: 700; color: var(--header-fg);
  margin-top: 0.45em; }}
.poster-header .affiliations {{ font-size: calc(30pt * var(--u) * var(--scale)); color: var(--header-sub-fg);
  margin-top: 0.2em; }}
.poster-header .logos {{ display: flex; gap: var(--gap); align-items: center; }}
.poster-header .logos img {{ height: calc(90mm * var(--u)); width: auto; }}
{head_band}
{header_rule}
.poster-body {{ flex: 1; min-height: 0; display: grid; gap: var(--gap);
  grid-template-columns: repeat(var(--cols), minmax(0, 1fr)); }}
.poster-body.billboard {{ grid-template-columns: minmax(0, 1fr) minmax(0, 2fr) minmax(0, 1fr); }}
.col {{ display: flex; flex-direction: column; gap: var(--gap); min-height: 0; overflow: hidden; }}
.panel {{ counter-increment: panel; background: var(--panel-bg); border: calc(1mm * var(--u)) solid var(--panel-line);
  border-radius: var(--panel-radius); padding: var(--pad); }}
.panel h2 {{ font-family: var(--font-heading); font-size: calc(var(--heading-pt) * var(--u) * var(--scale));
  line-height: 1.1; margin: 0 0 0.45em; }}
{title_rules}
{stretch}
.panel p, .panel ul, .panel ol {{ margin: 0 0 0.5em; }}
.panel ul, .panel ol {{ padding-left: 1.2em; }}
.panel li {{ margin-bottom: 0.25em; }}
.panel li::marker {{ color: var(--accent); }}
.panel a, .poster-footer a {{ color: var(--link); }}
mark {{ background: none; color: var(--accent2); font-weight: 700; }}
code, pre {{ font-family: 'Courier New', monospace; }}
pre {{ background: var(--code-bg); color: var(--code-fg); padding: 0.5em 0.7em; border-radius: 0.3em; font-size: 0.8em;
  white-space: pre-wrap; margin: 0 0 0.5em; }}
figure {{ margin: 0 0 0.6em; }}
figure img {{ width: 100%; height: auto; display: block; }}
figcaption {{ font-size: 0.78em; color: var(--muted); text-align: center; margin-top: 0.35em; }}
{frame}
{labels}
table {{ width: 100%; border-collapse: collapse; font-size: 0.85em; margin: 0 0 0.6em; background: var(--table-bg); }}
th {{ background: var(--table-head-bg); color: var(--table-head-fg); text-align: center; }}
th, td {{ border: calc(0.5mm * var(--u)) solid var(--table-border); padding: 0.2em 0.4em; }}
td:not(:first-child) {{ text-align: center; }}
tr:nth-child(even) td {{ background: var(--table-zebra); }}
blockquote {{ margin: 0 0 0.6em; padding: 0.4em 0.6em; border-left: calc(3mm * var(--u)) solid var(--accent);
  font-weight: 700; font-size: 1.08em; }}
.math-display {{ text-align: center; margin: 0.3em 0 0.6em; }}
.chip {{ display: inline-block; font-size: 0.68em; font-weight: 700; padding: 0.05em 0.35em; border-radius: 0.2em;
  margin-right: 0.3em; vertical-align: 0.1em; }}
.center {{ background: var(--center-bg); color: var(--center-fg); border-radius: calc(10mm * var(--u));
  padding: calc(30mm * var(--u)); display: flex; flex-direction: column; gap: var(--gap); min-height: 0;
  overflow: hidden; }}
.center .takeaway {{ font-size: calc(var(--takeaway-pt) * var(--u) * var(--scale)); font-weight: 700; line-height: 1.08;
  margin: auto 0 0; }}
.center .takeaway mark {{ color: var(--accent2); }}
.center .panel {{ background: none; border: none; padding: 0; color: var(--center-fg); }}
.center .panel h2 {{ color: var(--center-fg); background: none; margin: 0 0 0.3em; padding: 0; border: none; }}
.center .panel h2::before {{ display: none; }}
.center figure img {{ background: #FFFFFF; padding: calc(4mm * var(--u)); border-radius: calc(4mm * var(--u)); }}
.center figcaption {{ color: var(--center-fg); }}
.center .qr {{ margin: auto auto 0; text-align: center; font-size: 0.85em; }}
.center .qr img {{ width: calc(115mm * var(--u)); background: #FFFFFF; padding: calc(4mm * var(--u)); display: block;
  margin: 0 auto 0.3em; }}
.poster-footer {{ display: flex; gap: var(--gap); align-items: flex-end; font-size: calc(20pt * var(--u) * var(--scale));
  color: var(--footer-fg); border-top: calc(0.6mm * var(--u)) solid var(--muted); padding-top: calc(5mm * var(--u)); }}
.poster-footer .part {{ flex: 1; }}
.poster-footer .qr img {{ width: calc(80mm * var(--u)); display: block; }}
.poster-footer h3 {{ font-size: 1em; margin: 0 0 0.2em; }}
.poster-footer p {{ margin: 0; }}
/* screen only: grey surround, zoom to the window, toolbar */
@media screen {{
  body {{ background: #8A8F98; padding: 56px 0 24px; }}
  .poster {{ margin: 0 auto; box-shadow: 0 6px 30px rgba(0,0,0,.35); }}
}}
@media print {{
  .poster-toolbar {{ display: none !important; }}
  .poster {{ zoom: 1 !important; }}
  .overflowing {{ outline: none !important; }}
}}
"""


TOOLBAR_CSS = """
.poster-toolbar { position: fixed; top: 0; left: 0; right: 0; height: 44px; z-index: 10; display: flex; gap: 8px;
  align-items: center; padding: 0 14px; background: #1F2430; color: #EEE; font: 14px -apple-system, Arial, sans-serif; }
.poster-toolbar button { font: inherit; padding: 5px 11px; border: 0; border-radius: 4px; background: #3A4254;
  color: #FFF; cursor: pointer; }
.poster-toolbar button.on { background: #2E7D32; }
.poster-toolbar .status { margin-left: auto; opacity: .85; }
.overflowing { outline: 6px dashed #E53935; outline-offset: -6px; }
[contenteditable="true"] .panel:hover, [contenteditable="true"] .poster-header:hover { outline: 2px dashed #3B82F6; }
"""

SCRIPT = r"""
(function () {
  var poster = document.querySelector('.poster');
  var report = { scale: null, overflow: [], fitted: false };
  function cols() { return Array.prototype.slice.call(document.querySelectorAll('.col, .center')); }
  function overflowing() {
    return cols().filter(function (c) { return c.scrollHeight > c.clientHeight + 2; });
  }
  function setScale(s) { poster.style.setProperty('--scale', s.toFixed(3)); }
  function fit() {
    var auto = (poster.getAttribute('data-fit') || 'auto') !== 'off';
    var lo = 0.72, hi = 1.2, best = null;
    if (auto) {
      for (var i = 0; i < 9; i++) {
        var mid = (lo + hi) / 2; setScale(mid);
        if (overflowing().length === 0) { best = mid; lo = mid; } else { hi = mid; }
      }
      setScale(1.2);
      if (overflowing().length === 0) best = 1.2;
      setScale(best === null ? 0.72 : best);
    }
    var bad = overflowing();
    cols().forEach(function (c) { c.classList.toggle('overflowing', bad.indexOf(c) >= 0); });
    var sc = parseFloat(getComputedStyle(poster).getPropertyValue('--scale')) || 1;
    report.scale = Math.round(sc * 1000) / 1000;
    report.overflow = bad.map(function (c) { return c.getAttribute('data-col') || c.className; });
    report.fitted = true;
    document.body.setAttribute('data-poster-report', JSON.stringify(report));
    var st = document.querySelector('.poster-toolbar .status');
    if (st) st.textContent = 'text ' + Math.round(sc * 100) + '%' + (bad.length ? ' - OVERFLOW in ' + report.overflow.join(', ') : '');
  }
  var wholePage = false;
  function zoomToWindow() {
    if (window.matchMedia && window.matchMedia('print').matches) return;
    var z = (window.innerWidth - 40) / poster.offsetWidth;
    if (wholePage) z = Math.min(z, (window.innerHeight - 80) / poster.offsetHeight);
    poster.style.zoom = Math.min(1, z);
  }
  function ready() {
    var waits = [];
    if (document.fonts && document.fonts.ready) waits.push(document.fonts.ready);
    Array.prototype.forEach.call(document.images, function (im) {
      if (!im.complete) waits.push(new Promise(function (r) { im.onload = im.onerror = r; }));
    });
    if (window.MathJax && MathJax.startup && MathJax.startup.promise) waits.push(MathJax.startup.promise);
    return Promise.all(waits);
  }
  window.posterFit = fit;
  window.addEventListener('load', function () {
    ready().then(function () { poster.style.zoom = 1; fit(); zoomToWindow(); });
  });
  window.addEventListener('resize', zoomToWindow);
  window.addEventListener('beforeprint', function () { poster.style.zoom = 1; });
  window.addEventListener('afterprint', zoomToWindow);
  // toolbar (screen only)
  var bar = document.querySelector('.poster-toolbar');
  if (!bar) return;
  bar.querySelector('[data-act=edit]').onclick = function () {
    var on = poster.getAttribute('contenteditable') !== 'true';
    poster.setAttribute('contenteditable', on ? 'true' : 'false');
    this.classList.toggle('on', on);
    this.textContent = on ? 'Editing: click text to change it' : 'Edit text';
  };
  bar.querySelector('[data-act=fit]').onclick = function () { poster.style.zoom = 1; fit(); zoomToWindow(); };
  bar.querySelector('[data-act=print]').onclick = function () { window.print(); };
  bar.querySelector('[data-act=zoom]').onclick = function () {
    wholePage = !wholePage; this.textContent = wholePage ? 'Fit width' : 'Whole page'; zoomToWindow();
  };
  bar.querySelector('[data-act=save]').onclick = function () {
    var z = poster.style.zoom, ce = poster.getAttribute('contenteditable');
    poster.style.zoom = ''; poster.removeAttribute('contenteditable');
    poster.style.removeProperty('--scale');
    cols().forEach(function (c) { c.classList.remove('overflowing'); });
    document.body.removeAttribute('data-poster-report');
    var html = '<!DOCTYPE html>\n' + document.documentElement.outerHTML;
    poster.style.zoom = z; if (ce) poster.setAttribute('contenteditable', ce); fit();
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
    a.download = (location.pathname.split('/').pop() || 'poster.html');
    a.click();
  };
})();
"""

GUIDE = """
  How to edit this poster
  - Text: edit it here, or open the file in a browser and press "Edit text" in the toolbar, then "Save HTML"
    (the browser saves a copy to your downloads folder; replace this file with it).
  - Move a section: cut a whole panel section element and paste it into another column div.
  - Colours, fonts, sizes: the CSS variables in the poster-style block below. Another style: poster.py restyle.
  - Fixed text size: set data-fit="off" on the poster div and --scale in :root.
  - Export: poster.py export <this file>  (PDF + previews + fit report), or the browser's Print > Save as PDF
    with margins "None" and "Background graphics" on; the page size comes from @page.
  - Check: poster.py check <this file> --source <manuscript and data>
"""


# ---------------------------------------------------------------------------
# Content to HTML
# ---------------------------------------------------------------------------
def runs_html(runs: list[ss.Run]) -> str:
    out = []
    for r in runs:
        t = H.escape(r.text)
        if r.math:
            out.append(f"\\({t}\\)")
            continue
        if r.code:
            t = f"<code>{t}</code>"
        if r.bold:
            t = f"<strong>{t}</strong>"
        if r.italic:
            t = f"<em>{t}</em>"
        if r.highlight:
            t = f"<mark>{t}</mark>"
        if r.link:
            t = f'<a href="{H.escape(r.link)}">{t}</a>'
        out.append(t)
    return "".join(out)


def chip_html(status: str) -> str:
    bg, fg, label = dk.STATUS.get(status, ("#E8E8E8", "#1A1A1A", status.upper()))
    border = "; border: 1px solid #999" if dk.contrast(bg, "#FFFFFF") < 1.3 else ""
    return f'<span class="chip" style="background:{bg}; color:{fg}{border}">{label}</span>'


class Assets:
    """Copies figures next to the HTML (figures/), converting PDF to SVG (vector) so a browser can show it."""

    def __init__(self, spec: ss.Spec, out_dir: str):
        self.spec, self.out = spec, out_dir
        self.dir = os.path.join(out_dir, "figures")
        self.missing: list[str] = []
        self.map: dict[str, str] = {}

    def __call__(self, path: str) -> str | None:
        if dk.placeholders(path):
            self.missing.append(path)
            return None
        src = self.spec.resolve(path)
        if src in self.map:
            return self.map[src]
        if not os.path.exists(src):
            self.missing.append(path)
            return None
        os.makedirs(self.dir, exist_ok=True)
        base = os.path.basename(src)
        stem, ext = os.path.splitext(base)
        dst = os.path.join(self.dir, base)
        if ext.lower() == ".pdf":
            dst = os.path.join(self.dir, stem + ".svg")
            tool = shutil.which("pdftocairo")
            if tool:
                subprocess.run([tool, "-svg", "-f", "1", "-l", "1", src, dst], capture_output=True)
            if not os.path.exists(dst):
                dst = os.path.join(self.dir, stem + ".png")
                tool = shutil.which("pdftoppm")
                if tool:
                    subprocess.run([tool, "-png", "-r", "300", "-singlefile", src, dst[:-4]], capture_output=True)
            if not os.path.exists(dst):
                self.missing.append(path + " (PDF could not be converted: install poppler or export PNG/SVG)")
                return None
        elif os.path.abspath(src) != os.path.abspath(dst):
            shutil.copy2(src, dst)
        rel = os.path.relpath(dst, self.out).replace(os.sep, "/")
        self.map[src] = rel
        return rel


def element_html(e: ss.Element, assets: Assets) -> str:
    if e.kind == "para":
        return f"<p>{runs_html(e.runs)}</p>"
    if e.kind == "quote":
        return f"<blockquote>{runs_html(e.runs)}</blockquote>"
    if e.kind == "bullets":
        out, stack = [], []
        for lvl, runs, st, _rid, num in e.items:
            tag = "ol" if num else "ul"
            while len(stack) > lvl + 1:
                out.append(f"</{stack.pop()}>")
            if len(stack) == lvl + 1 and stack[-1] != tag:      # list type changes at this level
                out.append(f"</{stack.pop()}>")
            while len(stack) <= lvl:
                out.append(f"<{tag}>")
                stack.append(tag)
            out.append(f"<li>{chip_html(st) if st else ''}{runs_html(runs)}</li>")
        while stack:
            out.append(f"</{stack.pop()}>")
        return "".join(out)
    if e.kind == "image":
        rel = assets(e.path)
        cap = f"<figcaption>{runs_html(e.caption)}</figcaption>" if e.caption else ""
        frac = e.attrs.get("width")
        style = f' style="width:{H.escape(str(frac))}; margin-left:auto; margin-right:auto"' if isinstance(frac, str) \
            and frac.endswith("%") else ""
        if rel is None:
            return (f'<figure{style}><div class="missing" style="border:3px dashed var(--muted);padding:2em;'
                    f'text-align:center;color:var(--muted)">[[missing figure: {H.escape(e.path)}]]</div>{cap}</figure>')
        return f'<figure{style}><img src="{H.escape(rel)}" alt="{H.escape(ss.runs_text(e.caption))}">{cap}</figure>'
    if e.kind == "table" and e.rows:
        head = "".join(f"<th>{runs_html(c)}</th>" for c in e.rows[0])
        body = "".join("<tr>" + "".join(f"<td>{runs_html(c)}</td>" for c in r) + "</tr>" for r in e.rows[1:])
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    if e.kind == "math":
        return f'<div class="math-display">\\[{H.escape(e.text)}\\]</div>'
    if e.kind == "code":
        return f"<pre>{H.escape(e.text)}</pre>"
    return ""


def panel_html(b: ss.Block, assets: Assets, indent: str = "      ") -> str:
    inner = "\n".join(indent + "  " + element_html(e, assets) for e in b.elements if e.kind != "colbreak")
    return f'{indent}<section class="panel">\n{indent}  <h2>{runs_html(b.title)}</h2>\n{inner}\n{indent}</section>'


def estimate_height(b: ss.Block, col_w_mm: float, spec: ss.Spec) -> float:
    """Rough relative height of a panel, for the initial column split (the browser does the real layout)."""
    words = dk.word_count(ss.block_text(b))
    h = 40.0 + words * 1.7 * 841 / max(col_w_mm * 3.4, 1)
    for e in b.elements:
        if e.kind == "image":
            try:
                ar = dk.aspect(dk.image_info(spec.resolve(e.path))) or 0.65
            except (ValueError, OSError):
                ar = 0.65
            h += col_w_mm * ar
        if e.kind == "table":
            h += 14 * len(e.rows)
    return h


def build(spec: ss.Spec, st: dict, size_in: tuple[float, float], out_dir: str, math: str = "auto",
          html_name: str = "poster.html") -> tuple[str, list[str]]:
    """Write the editable HTML poster. Returns (path, missing figures)."""
    sys.path.insert(0, HERE)
    from poster import linear_partition       # noqa: E402 - shared with the PowerPoint layout
    os.makedirs(out_dir, exist_ok=True)
    assets = Assets(spec, out_dir)
    meta = spec.meta
    w_mm, h_mm = size_in[0] * 25.4, size_in[1] * 25.4
    billboard = st["layout"] == "billboard"
    blocks = [b for b in spec.blocks if b.level == 2]
    footer_blocks = [b for b in blocks if b.attrs.get("footer")]
    center_blocks = [b for b in blocks if billboard and (b.attrs.get("center") or b.attrs.get("key"))]
    panels = [b for b in blocks if b not in footer_blocks and b not in center_blocks]
    ncols = 2 if billboard else int(meta.get("columns") or (st["cols_landscape"] if w_mm > h_mm else st["cols_portrait"]))
    col_w = (w_mm - 50) / (4 if billboard else ncols)
    # columns: explicit {col=N} wins; otherwise split in reading order so columns have similar height
    if any(b.attrs.get("col") for b in panels):
        groups, cur = [], 0
        for b in panels:
            if b.attrs.get("col") is not None:
                try:
                    cur = max(0, min(ncols - 1, int(str(b.attrs["col"])) - 1))
                except ValueError:
                    pass
            groups.append(cur)
    else:
        groups = linear_partition([estimate_height(b, col_w, spec) for b in panels], ncols)
    cols = [[b for b, g in zip(panels, groups) if g == c] for c in range(ncols)]

    def col_html(c, idx):
        body = "\n".join(panel_html(b, assets) for b in c)
        return f'    <div class="col" data-col="column {idx}">\n{body}\n    </div>'
    # header
    logos = [x.strip() for x in meta.get("logos", "").split(",") if x.strip() and not dk.placeholders(x)]
    logo_html = "".join(f'<img src="{H.escape(r)}" alt="logo">' for r in (assets(x) for x in logos) if r)
    header = ['  <header class="poster-header">', '    <div class="titles">',
              f'      <h1>{runs_html(ss.inline(meta.get("title", "")))}</h1>']
    if meta.get("authors"):
        header.append(f'      <div class="authors">{runs_html(ss.inline(meta["authors"]))}</div>')
    if meta.get("affiliations"):
        header.append(f'      <div class="affiliations">{runs_html(ss.inline(meta["affiliations"]))}</div>')
    header.append("    </div>")
    if logo_html:
        header.append(f'    <div class="logos">{logo_html}</div>')
    header.append("  </header>")
    qr = meta.get("qr")
    qr_rel = assets(qr) if qr and not dk.placeholders(qr) else None
    # body
    if billboard:
        take = meta.get("takeaway") or next((b.title_text for b in spec.blocks if b.level == 1), "")
        center = ['    <div class="center" data-col="centre">',
                  f'      <p class="takeaway">{runs_html(ss.inline(take)) if take else "[[takeaway: the main finding in one sentence]]"}</p>']
        center += [panel_html(b, assets) for b in center_blocks]
        if qr_rel:
            lab = H.escape(meta.get("qr-label") or "Scan for the paper")
            center.append(f'      <div class="qr"><img src="{H.escape(qr_rel)}" alt="QR code">{lab}</div>')
        center.append("    </div>")
        body = ['  <main class="poster-body billboard">', col_html(cols[0], 1), "\n".join(center),
                col_html(cols[1], 2), "  </main>"]
    else:
        body = ['  <main class="poster-body">'] + [col_html(c, i + 1) for i, c in enumerate(cols)] + ["  </main>"]
    # footer
    parts = []
    if meta.get("contact"):
        parts.append(f'    <div class="part"><p><strong>Contact</strong> {runs_html(ss.inline(meta["contact"]))}</p></div>')
    for b in footer_blocks:
        inner = "".join(element_html(e, assets) for e in b.elements)
        parts.append(f'    <div class="part"><h3>{runs_html(b.title)}</h3>{inner}</div>')
    if meta.get("footer"):
        parts.append(f'    <div class="part"><p>{runs_html(ss.inline(meta["footer"]))}</p></div>')
    if qr_rel and not billboard:
        parts.append(f'    <div class="qr"><img src="{H.escape(qr_rel)}" alt="QR code"></div>')
    footer = ['  <footer class="poster-footer">', *parts, "  </footer>"] if parts else []
    has_math = any(r.math for b in blocks for e in b.elements for r in (e.runs if e.kind in ("para", "quote") else
                   [x for it in e.items for x in it[1]] if e.kind == "bullets" else [])) or \
        any(e.kind == "math" for b in blocks for e in b.elements)
    mathjax = ""
    if has_math and math != "text":
        mathjax = ('<script>window.MathJax = { tex: { inlineMath: [["\\\\(", "\\\\)"], ["$", "$"]] }, '
                   'svg: { fontCache: "global" } };</script>\n'
                   '<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>')
    srcs = [x.strip() for x in meta.get("source", "").split(",") if x.strip() and not dk.placeholders(x)]
    src_rel = ", ".join(os.path.relpath(spec.resolve(x), out_dir).replace(os.sep, "/") for x in srcs)
    metas = [("poster:style", st["name"]), ("poster:size", f"{w_mm:.0f}x{h_mm:.0f}mm"),
             ("poster:source", src_rel), ("poster:max-size", meta.get("max-size", "")),
             ("poster:generator", "Science-Skill research-poster")]
    meta_html = "\n".join(f'<meta name="{k}" content="{H.escape(str(v))}">' for k, v in metas if v)
    lang = "zh" if dk.has_cjk(ss.visible_text(spec)) else "en"
    doc = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<title>{H.escape(ss.runs_text(ss.inline(meta.get("title", "Poster"))))}</title>
{meta_html}
<!--{GUIDE}-->
<style id="poster-style">
{css_for(st, size_in, ncols)}
</style>
<style id="poster-toolbar-style">{TOOLBAR_CSS}</style>
{mathjax}
</head>
<body class="style-{st['name']}">
{TOOLBAR_HTML}
<div class="poster" data-fit="auto">
{chr(10).join(header)}
{chr(10).join(body)}
{chr(10).join(footer)}
</div>
<script id="poster-script">{SCRIPT}</script>
</body>
</html>
"""
    path = os.path.join(out_dir, html_name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    return path, assets.missing


# ---------------------------------------------------------------------------
# Restyle: replace the style block, keep the content
# ---------------------------------------------------------------------------
STYLE_RX = re.compile(r'^(<style id="poster-style">)(.*?)(</style>)', re.S | re.M)
SCRIPT_RX = re.compile(r'^(<script id="poster-script">)(.*?)(</script>)', re.S | re.M)
TOOLCSS_RX = re.compile(r'^(<style id="poster-toolbar-style">)(.*?)(</style>)', re.S | re.M)
TOOLBAR_RX = re.compile(r'^<div class="poster-toolbar">.*?</div>', re.S | re.M)
TOOLBAR_HTML = """<div class="poster-toolbar"><b>Poster</b>
  <button data-act="edit">Edit text</button><button data-act="save">Save HTML</button>
  <button data-act="fit">Re-fit</button><button data-act="zoom">Whole page</button>
  <button data-act="print">Print / Save as PDF</button>
  <span class="status"></span></div>"""


def page_size_mm(doc: str) -> tuple[float, float] | None:
    m = re.search(r"@page\s*\{[^}]*size:\s*([\d.]+)mm\s+([\d.]+)mm", doc)
    return (float(m.group(1)), float(m.group(2))) if m else None


def restyle(doc: str, st: dict, size_in: tuple[float, float] | None = None) -> str:
    if not STYLE_RX.search(doc):
        raise SystemExit('no <style id="poster-style"> block: this HTML was not made by poster.py')
    is_bb = bool(re.search(r'<main class="poster-body billboard"', doc))
    if (st["layout"] == "billboard") != is_bb:
        raise SystemExit("billboard and column styles have different structure; render the billboard version "
                         "from the spec, or move the content by hand")
    if size_in is None:
        mm = page_size_mm(doc) or (841, 1189)
        size_in = (mm[0] / 25.4, mm[1] / 25.4)
    ncols = len(re.findall(r'^\s*<div class="col" data-col=', doc, re.M)) if not is_bb else 2
    css = css_for(st, size_in, max(1, ncols))
    doc = STYLE_RX.sub(lambda m: m.group(1) + "\n" + css + "\n" + m.group(3), doc, count=1)
    # the toolbar and the fit script are tool code, not content: bring them up to date
    doc = SCRIPT_RX.sub(lambda m: m.group(1) + SCRIPT + m.group(3), doc, count=1)
    doc = TOOLCSS_RX.sub(lambda m: m.group(1) + TOOLBAR_CSS + m.group(3), doc, count=1)
    doc = TOOLBAR_RX.sub(lambda m: TOOLBAR_HTML, doc, count=1)
    doc = re.sub(r'<body class="style-[\w-]+"', f'<body class="style-{st["name"]}"', doc, count=1)
    doc = re.sub(r'<meta name="poster:style" content="[^"]*">', f'<meta name="poster:style" content="{st["name"]}">',
                 doc, count=1)
    return doc


# ---------------------------------------------------------------------------
# Inspect and export with headless Chrome
# ---------------------------------------------------------------------------
MEASURE = r"""
<script id="poster-measure">
window.addEventListener('load', function () {
  var tries = 0;
  (function tick() {
    if (!document.body.getAttribute('data-poster-report') && tries++ < 150) { setTimeout(tick, 40); return; }
    var poster = document.querySelector('.poster');
    var px2in = 1 / 96;
    var r = JSON.parse(document.body.getAttribute('data-poster-report') || '{}');
    var cs = getComputedStyle(poster);
    r.body_pt = Math.round(parseFloat(cs.fontSize) * 0.75 * 10) / 10;
    r.page_in = [poster.offsetWidth * px2in, poster.offsetHeight * px2in];
    r.images = Array.prototype.map.call(document.querySelectorAll('.poster img'), function (im) {
      var where = im.closest('section') ? (im.closest('section').querySelector('h2') || {}).textContent :
                  (im.closest('header') ? 'header' : (im.closest('.qr') ? 'QR code' : 'poster'));
      return { src: im.getAttribute('src'), natural: [im.naturalWidth, im.naturalHeight],
               placed_in: [im.offsetWidth * px2in, im.offsetHeight * px2in], where: where || '',
               vector: /\.svg(\?|$)/i.test(im.getAttribute('src') || ''), broken: im.complete && im.naturalWidth === 0 };
    });
    r.captions_pt = Array.prototype.map.call(document.querySelectorAll('figcaption'), function (c) {
      return Math.round(parseFloat(getComputedStyle(c).fontSize) * 0.75 * 10) / 10; });
    r.min_text_pt = Math.min.apply(null, Array.prototype.map.call(
      document.querySelectorAll('.panel p, .panel li, .panel td'), function (e) {
        return parseFloat(getComputedStyle(e).fontSize) * 0.75; }).concat([999]));
    document.body.setAttribute('data-measure', JSON.stringify(r));
  })();
});
</script>
"""


def inspect(html_path: str) -> tuple[dict | None, str | None]:
    """Fit report and measurements of the HTML as a browser lays it out."""
    if not dk.find_chrome():
        return None, "Chrome/Chromium not found: layout was not measured (open the HTML in a browser to see it)"
    with open(html_path, encoding="utf-8") as fh:
        doc = fh.read()
    probe = os.path.join(os.path.dirname(os.path.abspath(html_path)), ".poster-measure.html")
    with open(probe, "w", encoding="utf-8") as fh:
        fh.write(doc.replace("</body>", MEASURE + "</body>", 1))
    try:
        dom, err = dk.html_dump_dom(probe, 8000)
    finally:
        os.remove(probe)
    if err or not dom:
        return None, err or "no DOM"
    m = re.search(r'data-measure="([^"]*)"', dom)
    if not m:
        return None, "the page did not report (the fit script may have been removed)"
    return json.loads(H.unescape(m.group(1))), None


def export(html_path: str, out_dir: str | None = None) -> tuple[dict, list[str], list[str]]:
    """PDF (print file) and PNG previews from the HTML as it is now. Returns (report, files, notes)."""
    out_dir = out_dir or os.path.dirname(os.path.abspath(html_path))
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(html_path))[0]
    files, notes = [], []
    rep, err = inspect(html_path)
    if err:
        notes.append(err)
        return {}, files, notes
    pdf = os.path.join(out_dir, stem + ".pdf")
    e = dk.html_to_pdf(html_path, pdf, 8000)
    if e:
        notes.append(e)
        return rep, files, notes
    files.append(pdf)
    for name, wpx in (("preview", 1600), ("glance", 520)):
        got, e = dk.pdf_to_png(pdf, os.path.join(out_dir, f"{stem}-{name}"), wpx, 1, 1)
        if got:
            final = os.path.join(out_dir, f"{stem}-{name}.png")
            os.replace(got[0], final)
            files.append(final)
        elif e:
            notes.append(e)
    return rep, files, notes


# ---------------------------------------------------------------------------
# Read the HTML back (for the text checks)
# ---------------------------------------------------------------------------
from html.parser import HTMLParser  # noqa: E402


class _Reader(HTMLParser):
    SKIP = {"script", "style", "title"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.sections: list[dict] = []        # {"title", "text", "where"}
        self.header, self.takeaway, self.footer = [], [], []
        self.imgs: list[str] = []
        self._stack: list[str] = []
        self._skip = 0
        self._sec = None
        self._in_h2 = False
        self._zone = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "") or ""
        if tag == "meta" and a.get("name", "").startswith("poster:"):
            self.meta[a["name"][7:]] = a.get("content", "")
        if tag in self.SKIP or "poster-toolbar" in cls:
            self._skip += 1
            self._stack.append(("skip", tag))
            return
        mark = None
        if tag == "section" and "panel" in cls:
            self._sec = {"title": "", "text": [], "footer": False}
            self.sections.append(self._sec)
            mark = "section"
        elif tag == "header" and "poster-header" in cls:
            self._zone, mark = "header", "zone"
        elif tag == "footer" and "poster-footer" in cls:
            self._zone, mark = "footer", "zone"
        elif "takeaway" in cls.split():
            self._zone, mark = "takeaway", "zone"
        elif tag == "h2" and self._sec is not None:
            self._in_h2, mark = True, "h2"
        if tag == "img" and a.get("src"):
            self.imgs.append(a["src"])
        if tag not in ("img", "meta", "br", "hr", "link", "input"):
            self._stack.append((mark, tag))
        if tag in ("p", "li", "br", "tr", "h2", "h3", "figcaption", "blockquote", "div"):
            self._text("\n")

    def handle_endtag(self, tag):
        while self._stack:
            mark, t = self._stack.pop()
            if mark == "skip":
                self._skip -= 1
            elif mark == "section":
                self._sec = None
            elif mark == "zone":
                self._zone = None
            elif mark == "h2":
                self._in_h2 = False
            if t == tag:
                break
        if tag in ("p", "li", "td", "th", "figcaption"):
            self._text(" ")

    def _text(self, s):
        if self._skip:
            return
        if self._sec is not None:
            if self._in_h2:
                self._sec["title"] += s
            else:
                self._sec["text"].append(s)
        elif self._zone == "header":
            self.header.append(s)
        elif self._zone == "takeaway":
            self.takeaway.append(s)
        elif self._zone == "footer":
            self.footer.append(s)

    def handle_data(self, data):
        self._text(data)


def read(html_path: str) -> dict:
    with open(html_path, encoding="utf-8") as fh:
        doc = fh.read()
    r = _Reader()
    r.feed(doc)
    clean = lambda s: re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", s)).strip()   # noqa: E731
    secs = [{"title": clean(s["title"]), "text": clean("".join(s["text"]))} for s in r.sections]
    vars_ = dict(re.findall(r"--([\w-]+):\s*([^;]+);", STYLE_RX.search(doc).group(2))) if STYLE_RX.search(doc) else {}
    return {"meta": r.meta, "sections": secs, "header": clean("".join(r.header)), "takeaway": clean("".join(r.takeaway)),
            "footer": clean("".join(r.footer)), "images": r.imgs, "vars": vars_, "page_mm": page_size_mm(doc),
            "billboard": bool(re.search(r'<main class="poster-body billboard"', doc)), "doc": doc}
