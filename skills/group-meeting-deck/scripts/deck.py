#!/usr/bin/env python3
"""deck.py - build and check group-meeting slides from a Markdown content spec.

Content and style are separate: the spec (see lib/slidespec.py) says what the talk says; a style says
how it looks. The same spec renders in every style, so styles can be compared side by side.

Usage
  deck.py styles                                   list the visual styles
  deck.py templates                                list the structure templates
  deck.py init --template progress --minutes 15 [--lang zh] --out deck.md
  deck.py render deck.md [--style clean] [--format pptx,tex] [--aspect 16:9] --out deck/2026-11-04
  deck.py gallery deck.md [--styles clean,dark] [--slides 2,4] --out deck/2026-11-04/gallery
  deck.py check deck.md [--source results.csv paper.tex] [--ledger LEDGER.md] [--minutes 15] --out DIR

render writes <stem>.pptx (editable; speaker notes included), <stem>.tex (Beamer) on request,
<stem>.html and <stem>.pdf (a layout twin printed by headless Chrome, when installed) and
preview/slide-NNN.png. --quicklook adds previews rendered by macOS Quick Look from the .pptx itself.

check exits 1 when a FAIL remains: a placeholder, a number not in the sources, a status chip stronger
than the ledger, text that does not fit, a missing or low-resolution image, unreadable contrast, or a
talk that runs over. Findings are leads: read each one in context.

Options shared by render, gallery and check
  --palette accent=#0B5394,fg=#222222   override style colours (institution colours)
  --font "Source Sans Pro"              one font for headings and body
  --math auto|image|text                display formulas via LaTeX images (auto: when LaTeX exists)
  --beamer-theme Warsaw                 with --style beamer: Beamer theme for --format tex (default Madrid)
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "lib")))
import designcheck as dc        # noqa: E402
import designkit as dk          # noqa: E402
import pptxwriter as px         # noqa: E402
import slidekit as sk           # noqa: E402
import slidespec as ss          # noqa: E402
import deck_styles as DS        # noqa: E402
import deck_templates as DT     # noqa: E402

ASPECTS = {"16:9": (13.333, 7.5), "4:3": (10.0, 7.5), "16:10": (12.0, 7.5)}
BACKUP_RX = re.compile(r"^\s*(backup|appendix|extra|备用|附录|补充)\b", re.I)


def parse_palette(s: str | None) -> dict:
    out = {}
    for part in (s or "").split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            v = v.strip()
            if not dk.is_hex(v):
                raise SystemExit(f"--palette {k}: {v!r} is not a #RRGGBB colour")
            out[k.strip()] = "#" + v.lstrip("#").upper()
    return out


def style_for(spec: ss.Spec, args) -> dict:
    name = getattr(args, "style", None) or spec.get("style") or "clean"
    pal = parse_palette(spec.get("palette"))
    pal.update(parse_palette(getattr(args, "palette", None)))
    st = DS.get(name, pal, getattr(args, "font", None) or spec.get("font"))
    theme = getattr(args, "beamer_theme", None) or spec.get("beamer-theme")
    if theme and st.get("beamer_theme"):
        st["beamer_theme"] = theme          # Beamer output only (Warsaw, CambridgeUS, Boadilla, ...)
    return st


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
class Deck:
    def __init__(self, spec: ss.Spec, st: dict, aspect: str, workdir: str, math: str = "auto"):
        self.spec, self.st = spec, st
        if aspect not in ASPECTS:
            raise SystemExit(f"--aspect must be one of {', '.join(ASPECTS)}")
        self.W, self.H = ASPECTS[aspect]
        self.mx = 0.6 if self.W > 11 else 0.5
        self.ctx = sk.Ctx(st, workdir, spec.path, math)
        self.pres = px.Pptx(self.W, self.H, fonts={"latin": st["font_body"], "ea": st["font_ea"],
                                                   "heading": st["font_heading"]},
                            colours={"dk1": st["fg"], "lt1": st["bg"], "accent1": st["accent"],
                                     "accent2": st.get("accent2")},
                            title=spec.get("title", ""), author=spec.get("presenter", ""))
        self.slides: list[dict] = []
        self.footer_h = {"full": 0.45, "infolines": 0.28}.get(st["footer"], 0.35)

    # --- helpers ---------------------------------------------------------------
    def plan(self) -> list[tuple[str, ss.Block | None, bool]]:
        seq: list[tuple[str, ss.Block | None, bool]] = []
        if self.spec.get("title") and str(self.spec.get("cover", "yes")).lower() not in ("no", "false", "0"):
            seq.append(("cover", None, False))
        backup = False
        for b in self.spec.blocks:
            if b.level == 1:
                if BACKUP_RX.match(b.title_text) or b.attrs.get("backup"):
                    backup = True
                seq.append(("section", b, backup))
            else:
                seq.append(("content", b, backup or bool(b.attrs.get("backup"))))
        return seq

    def tpara(self, runs, size, color, bold=True, align="l", font=None):
        return px.para(self.ctx.runs(runs, size, color, bold=bold), size=size, align=align, line=1.05,
                       font=font or self.st["font_heading"])

    def build(self) -> px.Pptx:
        seq = self.plan()
        self.n_main = sum(1 for kind, _b, bk in seq if not bk)
        main_k = 0
        for kind, b, bk in seq:
            if not bk:
                main_k += 1
            k = len(self.slides) + 1
            info = {"n": k, "kind": kind, "backup": bk, "title": b.title_text if b else self.spec.get("title", ""),
                    "line": b.line if b else 0, "notes": b.notes if b else self.spec.get("notes", ""),
                    "body_pt": None, "overflow": False, "layout": kind,
                    "time": (b.attrs.get("time") if b else self.spec.get("cover-time"))}
            self.slides.append(info)
            if kind == "cover":
                self.cover(info)
            elif kind == "section":
                self.section(b, info, main_k)
            else:
                self.content(b, info, main_k, bk)
        return self.pres

    def footer(self, s: px.Slide, k_main: int, backup: bool, dark: bool = False):
        st = self.st
        W, H = self.W, self.H
        page = "Backup" if backup else f"{k_main} / {self.n_main}"
        if st["footer"] == "infolines":           # Beamer infolines: three boxes in shades of the structure colour
            fh = self.footer_h
            fg = st["footer_fg"]
            who = self.spec.get("presenter", "")
            if self.spec.get("group"):
                who = f"{who} ({self.spec.get('group')})" if who else self.spec.get("group")
            mid = self.spec.get("footer") or self.spec.get("title", "")
            right = "    ".join(x for x in (self.spec.get("date", ""), page) if x)
            third = W / 3
            for i, (txt, fill, al) in enumerate(((who, st["foot_left"], "c"), (mid, st["foot_mid"], "c"),
                                                 (right, st["foot_right"], "r"))):
                s.rect(i * third, H - fh, third + 0.01, fh, fill=fill)
                s.text(i * third + 0.15, H - fh, third - 0.3, fh,
                       [px.para(self.ctx.runs(ss.inline(txt), 10, fg), size=10, align=al)], anchor="m", inset=0,
                       name="footer")
            return
        if st["footer"] == "full":
            fh = self.footer_h
            s.rect(0, H - fh, W, fh, fill=st["footer_bg"])
            fg = st["footer_fg"]
            left = self.spec.get("presenter", "")
            mid = self.spec.get("footer") or self.spec.get("title", "")
            right = "   ".join(x for x in (self.spec.get("date", ""), page) if x)
            for x, w, txt, al in ((self.mx, W * 0.3, left, "l"), (W * 0.3, W * 0.4, mid, "c"),
                                  (W * 0.7 - self.mx, W * 0.3, right, "r")):
                s.text(x, H - fh, w, fh, [px.para(ss.inline(txt) and self.ctx.runs(ss.inline(txt), 11, fg) or "",
                                                  size=11, align=al, color=fg)], anchor="m", name="footer")
            return
        if st["footer"] == "page":
            fg = st["footer_fg"]
            s.text(W - self.mx - 2.0, H - 0.42, 2.0, 0.3, [px.para(page, size=11, color=fg, align="r")],
                   anchor="m", name="footer")
            if self.spec.get("footer"):
                s.text(self.mx, H - 0.42, W * 0.6, 0.3,
                       [px.para(self.ctx.runs(ss.inline(self.spec.get("footer")), 11, fg), size=11)],
                       anchor="m", name="footer")

    def strip(self, s: px.Slide):
        """notebook style: project strip with the date on every content slide."""
        st = self.st
        left = self.spec.get("group") or self.spec.get("title", "")
        s.rect(0, 0, self.W, 0.34, fill="#F3F4F6")
        s.rect(0, 0.34, self.W, 0.02, fill=st["accent"])
        s.text(self.mx, 0.02, self.W * 0.6, 0.3, [px.para(left.upper(), size=10, bold=True, color=st["muted"])],
               anchor="m", name="strip")
        s.text(self.W - self.mx - 3, 0.02, 3, 0.3, [px.para(self.spec.get("date", ""), size=10, color=st["muted"],
                                                            align="r")], anchor="m", name="strip")

    # --- slide types ---------------------------------------------------------------
    def cover(self, info):
        st, W, H, mx = self.st, self.W, self.H, self.mx
        s = self.pres.slide(bg=st["bg"])
        meta = self.spec.meta
        title_runs = ss.inline(meta.get("title", ""))
        sub = meta.get("subtitle", "")
        who = " · ".join(x for x in (meta.get("presenter", ""), meta.get("group", "")) if x)
        when = " · ".join(x for x in (meta.get("venue", ""), meta.get("date", "")) if x)
        tw = W - 2 * mx
        if st["cover"] == "beamer":               # Madrid title page: rounded title box, centred details below
            bw = tw * 0.96
            bx = (W - bw) / 2
            ps = [self.tpara(title_runs, 30, st["title_fg"], bold=False, align="c")]
            if sub:
                ps.append(px.para(self.ctx.runs(ss.inline(sub), 20, st["title_fg"]), size=20, align="c",
                                  space_before=6))
            th = self.ctx.measure([("cover", bw - 0.4, ps)])["cover"] + 0.45
            top = H * 0.2
            s.rect(bx + 0.05, top + 0.06, bw, th, fill=dk.mix(st["bg"], "#000000", 0.25), radius=0.12)   # shadow
            s.rect(bx, top, bw, th, fill=st["title_bg"], radius=0.12)
            s.text(bx + 0.2, top, bw - 0.4, th, ps, anchor="m", name="cover-title")
            det = []
            if meta.get("presenter"):
                det.append(px.para(self.ctx.runs(ss.inline(meta["presenter"]), 22, st["fg"]), size=22, align="c"))
            if meta.get("group"):
                det.append(px.para(self.ctx.runs(ss.inline(meta["group"]), 16, st["fg"]), size=16, align="c",
                                   space_before=14))
            if when:
                det.append(px.para(self.ctx.runs(ss.inline(when), 20, st["fg"]), size=20, align="c", space_before=14))
            if det:
                s.text(mx, top + th + 0.45, tw, 2.2, det, name="cover-details")
            self.footer(s, 1, False)
            s.notes = self.spec.get("notes", "")
            return
        if st["cover"] == "band":
            band_h = H * 0.48
            s.rect(0, 0, W, band_h, fill=st["title_bg"] or st["accent"])
            s.rect(0, band_h, W, 0.07, fill=st.get("title_rule") or st["accent2"])
            ps = [self.tpara(title_runs, 38, st["title_fg"])]
            if sub:
                ps.append(px.para(self.ctx.runs(ss.inline(sub), 20, st["title_fg"]), size=20, space_before=8))
            s.text(mx, 0.5, tw, band_h - 0.7, ps, anchor="b", name="cover-title")
            det = [px.para(self.ctx.runs(ss.inline(who), 20, st["fg"], bold=True), size=20)]
            if when:
                det.append(px.para(self.ctx.runs(ss.inline(when), 16, st["muted"]), size=16, space_before=6))
            s.text(mx, band_h + 0.45, tw, 1.6, det, name="cover-details")
            return
        x = mx + (0.35 if st["cover"] == "left-rule" else 0)
        cover_fg = st["fg"] if st.get("title_bg") else st["title_fg"]      # title_fg belongs to the band
        ps = [self.tpara(title_runs, 40 if W > 11 else 34, cover_fg, bold=st["title_bold"])]
        if sub:
            ps.append(px.para(self.ctx.runs(ss.inline(sub), 22, st["muted"]), size=22, space_before=10))
        hs = self.ctx.measure([("cover", tw - (x - mx), ps)])
        top = H * 0.30
        th = max(hs["cover"], 0.8)
        s.text(x, top, tw - (x - mx), th, ps, name="cover-title")
        if st["cover"] == "left-rule":
            s.rect(mx, top + 0.05, 0.09, th + 1.1, fill=st["accent"])
        else:
            s.rect(x, top + th + 0.18, 1.6 if st["name"] != "metropolis" else tw, 0.05, fill=st["accent"])
        det = [px.para(self.ctx.runs(ss.inline(who), 20, st["fg"], bold=True), size=20)] if who else []
        if when:
            det.append(px.para(self.ctx.runs(ss.inline(when), 16, st["muted"]), size=16, space_before=6))
        if det:
            s.text(x, top + th + 0.4, tw - (x - mx), 1.2, det, name="cover-details")
        s.notes = self.spec.get("notes", "")

    def section(self, b: ss.Block, info, k_main):
        st, W, H, mx = self.st, self.W, self.H, self.mx
        s = self.pres.slide(bg=st["section_bg"])
        if st.get("section_style") == "box":      # Beamer \sectionpage: rounded box with the section title
            self.n_sections = getattr(self, "n_sections", 0) + 1
            bw = (W - 2 * mx) * 0.96
            bx = (W - bw) / 2
            if not info["backup"]:
                s.text(mx, H * 0.27, W - 2 * mx, 0.5, [px.para(f"Section {self.n_sections}", size=22, color=st["fg"],
                                                               align="c")], anchor="b", name="section-label")
            s.rect(bx + 0.05, H * 0.36 + 0.06, bw, 0.85, fill=dk.mix(st["bg"], "#000000", 0.25), radius=0.12)
            s.rect(bx, H * 0.36, bw, 0.85, fill=st["title_bg"], radius=0.12)
            s.text(bx, H * 0.36, bw, 0.85, [self.tpara(b.title, 24, st["title_fg"], bold=False, align="c")],
                   anchor="m", name="section-title")
            self.footer(s, k_main, info["backup"])
            s.notes = b.notes
            return
        ps = [self.tpara(b.title, 36, st["section_fg"], bold=st["title_bold"])]
        s.text(mx, H * 0.36, W - 2 * mx, 1.6, ps, anchor="m", name="section-title")
        line = st["accent"] if st["section_bg"] in (st["bg"], "#FFFFFF") or st["name"] == "metropolis" else \
            st["section_fg"]
        s.rect(mx, H * 0.36 + 1.65, 1.6, 0.05, fill=line)
        s.notes = b.notes

    def title_area(self, s: px.Slide, b: ss.Block, k_main: int) -> float:
        st, W, mx = self.st, self.W, self.mx
        tw = W - 2 * mx
        size = st["title_pt"]
        top = 0.5 if st.get("strip") else 0.32
        if st.get("title_bg"):
            band = 0.85 if st.get("beamer_theme") else 1.0
            ps = [self.tpara(b.title, size, st["title_fg"], bold=st["title_bold"])]
            h = self.ctx.measure([("t", tw, ps)])["t"]
            if h > band - 0.15:
                size *= 0.82
                ps = [self.tpara(b.title, size, st["title_fg"], bold=st["title_bold"])]
                h = self.ctx.measure([("t", tw, ps)])["t"]
                band = max(band, h + 0.25)
            s.rect(0, 0, W, band, fill=st["title_bg"])
            s.text(mx, 0, tw, band, ps, anchor="m", name="title")
            y = band
            if st.get("progress") and self.n_main:
                s.rect(0, band, W * min(1.0, k_main / self.n_main), 0.045, fill=st["accent"])
            if st.get("title_rule"):
                s.rect(0, band, W, 0.06, fill=st["title_rule"])
                y += 0.06
            return y + 0.3
        ps = [self.tpara(b.title, size, st["title_fg"], bold=st["title_bold"])]
        h = self.ctx.measure([("t", tw, ps)])["t"]
        one = size * sk.LINE * 1.05 / 1.1 * 1.04
        if h > 2.2 * one:
            size *= 0.85
            ps = [self.tpara(b.title, size, st["title_fg"], bold=st["title_bold"])]
            h = self.ctx.measure([("t", tw, ps)])["t"]
            if h > 2.2 * size * sk.LINE:
                self.ctx.issue("WARN", "TITLE-LONG", f"slide {len(self.slides)}: title runs to three or more lines")
        s.text(mx, top, tw, h, ps, name="title")
        y = top + h
        if st.get("title_rule"):
            full = st.get("strip") or st.get("rule_full")
            s.rect(mx, y + 0.08, tw if full else 1.1, 0.05 if not full else 0.025, fill=st["title_rule"])
            y += 0.13
        return y + 0.28

    def content(self, b: ss.Block, info, k_main, backup):
        st, W, H, mx = self.st, self.W, self.H, self.mx
        s = self.pres.slide(bg=st["bg"])
        s.notes = b.notes
        if st.get("strip"):
            self.strip(s)
        where = f"slide {info['n']}"
        top = self.title_area(s, b, k_main)
        bottom = H - self.footer_h - 0.22
        avail = bottom - top
        tw = W - 2 * mx
        gap_col = 0.45
        cols = sk.split_columns(b.elements)
        n_img = sum(1 for e in b.elements if e.kind == "image")
        text_words = sum(dk.word_count(ss.element_text(e)) for e in b.elements if e.kind != "image")
        layout = b.attrs.get("layout")
        if not layout:
            if len(cols) > 1:
                layout = "columns"
            elif n_img == 1 and len(b.elements) > 1 and text_words > 25 and not st.get("assertion"):
                layout = "split"
            elif len(b.elements) == 1 and b.elements[0].kind == "quote" and not st.get("quote_box"):
                layout = "statement"
            else:
                layout = "stack"
        info["layout"] = layout
        if layout == "statement":
            e = b.elements[0] if b.elements else None
            if e is not None:
                size = st["title_pt"] * 1.15
                ps = [px.para(self.ctx.runs(e.runs if e.kind in ("para", "quote") else ss.inline(ss.element_text(e)),
                                            size, st.get("quote_fg", st["accent"]), bold=True),
                              size=size, align="c", line=1.15)]
                h = self.ctx.measure([("st", tw * 0.85, ps)])["st"]
                s.text(mx + tw * 0.075, top + max(0, (avail - h) / 2), tw * 0.85, h, ps, name=f"{where}:statement")
                info["body_pt"] = size
                info["overflow"] = h > avail
            self.footer(s, k_main, backup)
            return
        if layout == "split":
            img = [e for e in b.elements if e.kind == "image"]
            txt = [e for e in b.elements if e.kind != "image"]
            left_img = str(b.attrs.get("image", "right")) == "left"
            cols = [img, txt] if left_img else [txt, img]
            fr = [0.55, 0.45] if left_img else [0.45, 0.55]
            widths = [(tw - gap_col) * f for f in fr]
        elif layout == "columns":
            ws = b.attrs.get("widths")
            if isinstance(ws, str):
                try:
                    fr = [float(x) for x in ws.split(",")]
                except ValueError:
                    fr = [1.0] * len(cols)
            else:
                fr = [1.0] * len(cols)
            fr = (fr + [1.0] * len(cols))[:len(cols)]
            tot = sum(fr)
            widths = [(tw - gap_col * (len(cols) - 1)) * f / tot for f in fr]
        else:
            cols = [[e for e in b.elements if e.kind != "colbreak"]]
            widths = [tw]
        size = st["body_pt"]
        gap = 0.22
        while True:
            self.ctx.collect()
            for i, (c, w) in enumerate(zip(cols, widths)):
                sk.pieces(self.ctx, c, w, size, f"s{info['n']}c{i}", where=where)
            self.ctx.flush()
            pss = [sk.pieces(self.ctx, c, w, size, f"s{info['n']}c{i}", where=where) for i, (c, w) in
                   enumerate(zip(cols, widths))]
            scales = [sk.fit_images(ps, avail, gap * size / st["body_pt"]) for ps in pss]
            if all(sc > 0 for sc in scales) or size <= st["min_pt"] + 1e-6:
                break
            size = max(st["min_pt"], size * 0.92)
        info["body_pt"] = round(size, 1)
        if any(sc == 0 for sc in scales):
            info["overflow"] = True
            self.ctx.issue("FAIL", "OVERFLOW", where, f"'{b.title_text[:50]}' does not fit even at {st['min_pt']} pt; "
                                                     "split the slide or move detail to the notes or a backup slide")
            scales = [sc or 0.3 for sc in scales]
        x = mx
        for ps, w, sc in zip(pss, widths, scales):
            g = gap * size / st["body_pt"]
            h = sk.stack_height(ps, g, sc)
            y = top
            only_images = ps and all(p.kind in ("image", "mathimg") for p in ps)
            if layout == "split" and only_images or b.attrs.get("center"):
                y = top + max(0.0, (avail - h) / 2)
            sk.draw_stack(self.ctx, s, ps, x, y, w, g, sc, where=where)
            x += w + gap_col
        self.footer(s, k_main, backup)


# ---------------------------------------------------------------------------
# Beamer
# ---------------------------------------------------------------------------
TEX_ESC = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{",
           "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def tesc(s: str) -> str:
    return "".join(TEX_ESC.get(c, c) for c in s)


def runs_tex(runs: list[ss.Run]) -> str:
    out = []
    for r in runs:
        if r.math:
            out.append(f"${r.text}$")
            continue
        t = r"\texttt{" + tesc(r.text) + "}" if r.code else tesc(r.text)
        if r.bold:
            t = r"\textbf{" + t + "}"
        if r.italic:
            t = r"\emph{" + t + "}"
        if r.highlight:
            t = r"\alert{" + t + "}"
        if r.link:
            t = r"\href{" + r.link.replace("%", r"\%").replace("#", r"\#") + "}{" + t + "}"
        out.append(t)
    return "".join(out)


def _hex(h: str) -> str:
    return h.lstrip("#").upper()


def beamer(spec: ss.Spec, st: dict, aspect: str, outdir: str, ctx: sk.Ctx | None = None) -> tuple[str, bool]:
    cjk = dk.has_cjk(ss.visible_text(spec))
    ar = {"16:9": "169", "4:3": "43", "16:10": "1610"}[aspect]
    cols = {"ssfg": st["fg"], "ssbg": st["bg"], "ssmuted": st["muted"], "ssaccent": st["accent"],
            "sstitlefg": st["title_fg"], "sstitlebg": st.get("title_bg") or st["bg"], "ssrule": st.get("title_rule") or
            st["accent"], "sssectionbg": st["section_bg"], "sssectionfg": st["section_fg"], "sscodebg": st["code_bg"],
            "ssfootbg": st.get("footer_bg") or st["bg"], "ssfootfg": st["footer_fg"], "sslink": st["link"]}
    L = [f"\\documentclass[aspectratio={ar},11pt]{{beamer}}",
         "\\usepackage{graphicx,amsmath,amssymb,booktabs,tikz,appendixnumberbeamer}",
         "\\usepackage[UTF8,scheme=plain]{ctex}" if cjk else "\\usepackage[T1]{fontenc}",
         "\\usepackage{hyperref}"]
    L += [f"\\definecolor{{{k}}}{{HTML}}{{{_hex(v)}}}" for k, v in cols.items()]
    for name, (bg, fg, _label) in dk.STATUS.items():
        L.append(f"\\definecolor{{chip{name.replace('-', '')}bg}}{{HTML}}{{{_hex(bg)}}}"
                 f"\\definecolor{{chip{name.replace('-', '')}fg}}{{HTML}}{{{_hex(fg)}}}")
    L += ["\\newcommand{\\chip}[2]{\\colorbox{chip#1bg}{\\textcolor{chip#1fg}{\\scriptsize\\bfseries #2}}\\,}",
          "\\setbeamertemplate{navigation symbols}{}",
          "\\hypersetup{colorlinks=true,urlcolor=sslink,linkcolor=ssfg}",
          "\\setbeamerfont{caption}{size=\\footnotesize}",
          "\\setbeamertemplate{caption}{\\raggedright\\usebeamercolor[fg]{normal text}\\color{ssmuted}\\insertcaption\\par}"]
    theme = st.get("beamer_theme")
    if theme:
        # the real Beamer theme; the structure colour follows the style accent (palette overrides included)
        L.insert(1, f"\\usetheme{{{theme}}}")
        if st["accent"].upper() != "#3333B3":
            r, g, b = dk.hex_rgb(st["accent"])
            L.insert(2, f"\\usecolortheme[RGB={{{r},{g},{b}}}]{{structure}}")
    else:
        L += ["\\setbeamercolor{normal text}{fg=ssfg,bg=ssbg}", "\\setbeamercolor{structure}{fg=ssaccent}",
              "\\setbeamercolor{alerted text}{fg=ssaccent}", "\\setbeamercolor{frametitle}{fg=sstitlefg,bg=sstitlebg}",
              "\\setbeamercolor{title}{fg=" + ("ssfg" if st.get("title_bg") else "sstitlefg") + "}",
              "\\setbeamertemplate{itemize item}{\\color{ssaccent}\\raisebox{0.1ex}{\\small$\\bullet$}}",
              "\\setbeamertemplate{itemize subitem}{\\color{ssaccent}\\raisebox{0.1ex}{\\scriptsize$\\bullet$}}",
              "\\setbeamertemplate{enumerate item}{\\color{ssaccent}\\insertenumlabel.}",
              "\\setbeamerfont{frametitle}{size=\\Large,series=\\bfseries}"]
        if st["font_heading"] == DS.SERIF:
            L.append("\\setbeamerfont{frametitle}{family=\\rmfamily,size=\\Large,series=\\bfseries}")
        if st.get("title_bg"):
            prog = ("\\begin{tikzpicture}\\fill[ssaccent] (0,0) rectangle "
                    "({\\paperwidth*min(1,\\insertframenumber/max(1,\\inserttotalframenumber))},0.5pt);\\end{tikzpicture}"
                    if st.get("progress") else "")
            rule = "{\\color{ssrule}\\rule{\\paperwidth}{2pt}}" if st.get("title_rule") else ""
            L.append("\\setbeamertemplate{frametitle}{\\nointerlineskip\\begin{beamercolorbox}[wd=\\paperwidth,ht=2.8ex,"
                     "dp=1.6ex,leftskip=1.1em]{frametitle}\\usebeamerfont{frametitle}\\insertframetitle"
                     f"\\end{{beamercolorbox}}\\par\\nointerlineskip{prog}{rule}\\vspace*{{0.4em}}}}")
        else:
            rule = "\\par\\vspace*{0.15em}{\\color{ssrule}\\rule{3em}{2pt}}" if st.get("title_rule") else ""
            L.append("\\setbeamertemplate{frametitle}{\\vspace*{0.7em}{\\usebeamerfont{frametitle}"
                     f"\\usebeamercolor[fg]{{frametitle}}\\insertframetitle}}{rule}\\par\\vspace*{{0.3em}}}}")
        if st["footer"] == "full":
            L.append("\\setbeamertemplate{footline}{\\begin{beamercolorbox}[wd=\\paperwidth,ht=2.4ex,dp=1ex]{}"
                     "\\color{ssfootfg}\\scriptsize\\hspace*{1em}\\insertshortauthor\\hfill\\insertshorttitle\\hfill"
                     "\\insertshortdate\\quad\\insertframenumber/\\inserttotalframenumber\\hspace*{1em}"
                     "\\end{beamercolorbox}}\\setbeamercolor{footline}{bg=ssfootbg}")
            L.append("\\makeatletter\\setbeamertemplate{footline}{\\begin{tikzpicture}[remember picture,overlay]"
                     "\\fill[ssfootbg] (current page.south west) rectangle ([yshift=3.6ex]current page.south east);"
                     "\\end{tikzpicture}\\leavevmode\\color{ssfootfg}\\scriptsize\\hspace*{1em}\\insertshortauthor"
                     "\\hfill\\insertshorttitle\\hfill\\insertshortdate\\quad\\insertframenumber/"
                     "\\inserttotalframenumber\\hspace*{1em}\\vspace*{1.2ex}}\\makeatother")
        elif st["footer"] == "page":
            L.append("\\setbeamertemplate{footline}{\\hfill{\\color{ssfootfg}\\scriptsize\\insertframenumber/"
                     "\\inserttotalframenumber}\\hspace*{1.2em}\\vspace*{0.8em}}")
        L.append("\\setbeamertemplate{title page}{\\vfill{\\usebeamerfont{title}\\usebeamercolor[fg]{title}"
                 "\\LARGE\\bfseries\\inserttitle\\par}\\ifx\\insertsubtitle\\empty\\else\\vspace*{0.4em}"
                 "{\\large\\color{ssmuted}\\insertsubtitle\\par}\\fi\\vspace*{0.6em}{\\color{ssaccent}\\rule{4em}{2pt}}"
                 "\\par\\vspace*{0.8em}{\\bfseries\\insertauthor\\par}\\vspace*{0.3em}{\\small\\color{ssmuted}"
                 "\\insertinstitute\\par\\insertdate\\par}\\vfill}")
    meta = spec.meta
    L += [f"\\title{{{runs_tex(ss.inline(meta.get('title', '')))}}}",
          f"\\subtitle{{{runs_tex(ss.inline(meta.get('subtitle', '')))}}}",
          f"\\author{{{runs_tex(ss.inline(meta.get('presenter', '')))}}}",
          f"\\institute{{{runs_tex(ss.inline(meta.get('group', '')))}}}",
          f"\\date{{{runs_tex(ss.inline(' · '.join(x for x in (meta.get('venue', ''), meta.get('date', '')) if x)))}}}",
          "\\begin{document}", ("\\begin{frame}\\titlepage\\end{frame}" if theme else
                                 "\\begin{frame}[plain]\\titlepage\\end{frame}") if meta.get("title") else ""]

    def img_tex(e: ss.Element, height: str) -> str:
        path = spec.resolve(e.path)
        frac = sk._width_frac(e.attrs.get("width"))
        if not os.path.exists(path):
            return f"\\fbox{{\\parbox{{0.8\\linewidth}}{{\\centering missing figure: {tesc(e.path)}}}}}"
        if os.path.splitext(path)[1].lower() == ".svg":     # LaTeX cannot read SVG: use the converted PDF/PNG
            c = ctx or sk.Ctx(st, outdir, spec.path)
            png, _info = c.image(path)
            if png is None:
                return f"\\fbox{{cannot convert {tesc(e.path)}}}"
            pdf = os.path.splitext(png)[0] + ".pdf"
            path = pdf if os.path.exists(pdf) else png
        rel = os.path.relpath(path, outdir).replace("\\", "/")
        cap = f"\\par\\vspace*{{0.2em}}{{\\footnotesize\\color{{ssmuted}}{runs_tex(e.caption)}}}" if e.caption else ""
        return (f"{{\\centering\\includegraphics[width={frac:.2f}\\linewidth,height={height},keepaspectratio]"
                f"{{{rel}}}{cap}\\par}}")

    def elems_tex(els: list[ss.Element], n_img: int) -> list[str]:
        out = []
        h = "0.62\\textheight" if n_img <= 1 else f"{0.6 / n_img:.2f}\\textheight"
        for e in els:
            if e.kind in ("para",):
                out.append(runs_tex(e.runs) + "\\par\\medskip")
            elif e.kind == "quote" and theme:
                title = runs_tex(ss.inline(str(e.attrs["title"]))) if e.attrs.get("title") else ""
                out.append(f"\\begin{{block}}{{{title}}}{runs_tex(e.runs)}\\end{{block}}")
            elif e.kind == "quote":
                out.append(f"{{\\large\\bfseries\\color{{ssaccent}}{runs_tex(e.runs)}}}\\par\\medskip")
            elif e.kind == "bullets":
                env = "enumerate" if e.items and e.items[0][4] else "itemize"
                out.append(f"\\begin{{{env}}}")
                cur = 0
                for lvl, runs, stt, rid, num in e.items:
                    while lvl > cur:
                        out.append("\\begin{itemize}")
                        cur += 1
                    while lvl < cur:
                        out.append("\\end{itemize}")
                        cur -= 1
                    chip = (f"\\chip{{{stt.replace('-', '')}}}{{{dk.STATUS[stt][2]}}}" if stt in dk.STATUS else "")
                    out.append(f"\\item {chip}{runs_tex(runs)}")
                while cur > 0:
                    out.append("\\end{itemize}")
                    cur -= 1
                out.append(f"\\end{{{env}}}")
            elif e.kind == "image":
                out.append(img_tex(e, h))
            elif e.kind == "math":
                out.append(f"\\[ {e.text} \\]")
            elif e.kind == "code":
                lines = "\\\\\n".join("\\texttt{" + tesc(x).replace(" ", "~") + "}" for x in e.text.split("\n"))
                out.append(f"{{\\setlength{{\\fboxsep}}{{6pt}}\\colorbox{{sscodebg}}{{\\parbox{{0.95\\linewidth}}"
                           f"{{\\footnotesize {lines}}}}}}}\\par\\medskip")
            elif e.kind == "table" and e.rows:
                nc = max(len(r) for r in e.rows)
                body = []
                for ri, row in enumerate(e.rows):
                    cells = [runs_tex(c) for c in row] + [""] * (nc - len(row))
                    if ri == 0:
                        cells = [f"\\textbf{{{c}}}" for c in cells]
                    body.append(" & ".join(cells) + " \\\\" + (" \\midrule" if ri == 0 else ""))
                tab = f"\\begin{{tabular}}{{l{'c' * (nc - 1)}}}\\toprule " + "\n".join(body) + " \\bottomrule\\end{tabular}"
                if nc > 4:
                    tab = f"\\resizebox{{\\linewidth}}{{!}}{{{tab}}}"
                out.append(f"{{\\centering\\small {tab}\\par}}\\medskip")
        return out

    backup = False
    for b in spec.blocks:
        if b.level == 1:
            if (BACKUP_RX.match(b.title_text) or b.attrs.get("backup")) and not backup:
                backup = True
                L.append("\\appendix")
            if theme:
                L += [f"\\section{{{runs_tex(b.title)}}}", "\\begin{frame}\\sectionpage",
                      (f"\\note{{{tesc(b.notes)}}}" if b.notes else ""), "\\end{frame}"]
                continue
            L += ["{\\setbeamercolor{background canvas}{bg=sssectionbg}\\begin{frame}[plain]\\vfill",
                  f"{{\\color{{sssectionfg}}\\LARGE\\bfseries {runs_tex(b.title)}\\par}}\\vspace*{{0.5em}}"
                  "{\\color{ssaccent}\\rule{4em}{2pt}}\\vfill",
                  (f"\\note{{{tesc(b.notes)}}}" if b.notes else ""), "\\end{frame}}"]
            continue
        if b.attrs.get("backup") and not backup:
            backup = True
            L.append("\\appendix")
        layout = b.attrs.get("layout")
        cols_ = sk.split_columns(b.elements)
        n_img = sum(1 for e in b.elements if e.kind == "image")
        L.append(f"\\begin{{frame}}{{{runs_tex(b.title)}}}\\relax")   # \\relax: a following {...} is not a subtitle
        if layout == "statement" or (not layout and len(b.elements) == 1 and b.elements[0].kind == "quote"
                                     and not theme):
            e = b.elements[0] if b.elements else None
            txt = runs_tex(e.runs) if e is not None and e.kind in ("para", "quote") else ""
            L.append(f"\\vfill\\begin{{center}}{{\\Large\\bfseries\\color{{ssaccent}}{txt}}}\\end{{center}}\\vfill")
        elif len(cols_) > 1:
            L.append("\\begin{columns}[T]")
            w = 0.96 / len(cols_)
            for c in cols_:
                L.append(f"\\begin{{column}}{{{w:.2f}\\textwidth}}")
                L += elems_tex(c, sum(1 for e in c if e.kind == "image"))
                L.append("\\end{column}")
            L.append("\\end{columns}")
        elif n_img == 1 and len(b.elements) > 1 and not st.get("assertion") and \
                sum(dk.word_count(ss.element_text(e)) for e in b.elements if e.kind != "image") > 25:
            img = [e for e in b.elements if e.kind == "image"]
            txt = [e for e in b.elements if e.kind != "image"]
            L += ["\\begin{columns}[T]", "\\begin{column}{0.44\\textwidth}", *elems_tex(txt, 0), "\\end{column}",
                  "\\begin{column}{0.54\\textwidth}", *elems_tex(img, 1), "\\end{column}", "\\end{columns}"]
        else:
            L += elems_tex(b.elements, n_img)
        if b.notes:
            L.append(f"\\note{{{tesc(b.notes)}}}")
        L.append("\\end{frame}")
    L.append("\\end{document}")
    return "\n".join(x for x in L if x) + "\n", cjk


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def build_deck(spec, st, aspect, workdir, math) -> Deck:
    d = Deck(spec, st, aspect, workdir, math)
    d.build()
    return d


def twin_overflow(d: Deck, html: str) -> list[str]:
    dom, err = dk.html_dump_dom(html)
    if err or not dom:
        return []
    m = re.search(r'data-overflow="([^"]*)"', dom)
    return [x for x in (m.group(1).split(";") if m else []) if x]


def write_outputs(d: Deck, spec: ss.Spec, st: dict, args, out: str) -> dict:
    stem = os.path.splitext(os.path.basename(spec.path))[0] or "deck"
    fmts = [f.strip() for f in (args.format or "pptx").split(",") if f.strip()]
    res = {"files": [], "previews": [], "notes": []}
    os.makedirs(out, exist_ok=True)
    if "pptx" in fmts:
        p = os.path.join(out, stem + ".pptx")
        d.pres.save(p)
        probs = px.validate(p)
        if probs:
            res["notes"].append("pptx structure problems: " + "; ".join(probs[:5]))
        res["files"].append(p)
    html = os.path.join(out, stem + ".html")
    d.pres.to_html(html)
    res["files"].append(html)
    res["overflow"] = twin_overflow(d, html)
    if not getattr(args, "no_preview", False):
        pdf = os.path.join(out, stem + ".pdf")
        err = dk.html_to_pdf(html, pdf)
        if err:
            res["notes"].append(f"no PDF/preview: {err}")
        else:
            res["files"].append(pdf)
            pv = os.path.join(out, "preview")
            os.makedirs(pv, exist_ok=True)
            files, err = dk.pdf_to_png(pdf, os.path.join(pv, "slide"), 1280)
            res["previews"] += files
            if err:
                res["notes"].append(err)
    if getattr(args, "quicklook", False) and "pptx" in fmts:
        qd = os.path.join(out, "preview-quicklook")
        os.makedirs(qd, exist_ok=True)
        files, err = dk.quicklook_png(d.pres.save_each(qd, stem), qd, 1280)
        res["previews"] += files
        if err:
            res["notes"].append(err)
    if "tex" in fmts or "beamer" in fmts:
        tex, cjk = beamer(spec, st, args.aspect, out, d.ctx)
        tp = os.path.join(out, stem + ".tex")
        with open(tp, "w", encoding="utf-8") as fh:
            fh.write(tex)
        res["files"].append(tp)
        if getattr(args, "compile", False):
            bdir = os.path.join(out, "beamer-build")
            os.makedirs(bdir, exist_ok=True)
            import shutil
            shutil.copy(tp, bdir)
            tex2 = beamer(spec, st, args.aspect, bdir, d.ctx)[0]
            with open(os.path.join(bdir, stem + ".tex"), "w", encoding="utf-8") as fh:
                fh.write(tex2)
            pdf, log, err = dk.compile_tex(os.path.join(bdir, stem + ".tex"), cjk)
            if err:
                res["notes"].append(err)
            else:
                res["files"].append(pdf)
                over = len(re.findall(r"Overfull \\vbox", log))
                if over:
                    res["notes"].append(f"Beamer: {over} frame(s) overfull (content taller than the frame)")
    return res


def layout_json(d: Deck, res: dict, out: str):
    data = {"slides": d.slides, "placed": [{k: v for k, v in p.items()} for p in d.ctx.placed],
            "issues": d.ctx.issues, "overflow_twin": res.get("overflow", []), "style": d.st["name"]}
    with open(os.path.join(out, "layout.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1, default=str)


def cmd_styles(args):
    if args.json:
        print(json.dumps({k: {x: v[x] for x in ("label", "summary", "best_for")} for k, v in DS.STYLES.items()},
                         ensure_ascii=False, indent=1))
        return 0
    for k, v in DS.STYLES.items():
        print(f"{k:11s} {v['label']}\n            {v['summary']}\n            Best for: {v['best_for']}\n")
    return 0


def cmd_templates(args):
    for k, v in DT.TEMPLATES.items():
        print(f"{k:13s} {v['label']}: {v['use']}")
    return 0


def cmd_init(args):
    t = DT.TEMPLATES.get(args.template)
    if not t:
        raise SystemExit(f"unknown template; choose from {', '.join(DT.TEMPLATES)}")
    qa = args.qa if args.qa is not None else max(2, round(args.minutes * 0.25))
    text = t[args.lang].format(minutes=args.minutes, qa=qa)
    if os.path.exists(args.out) and not args.force:
        raise SystemExit(f"{args.out} exists; use --force to overwrite")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    talk = args.minutes - qa
    print(f"wrote {args.out} ({t['label']}). Talking time {talk} min of {args.minutes} (Q&A {qa}): "
          f"plan about {max(3, round(talk / 1.5))}-{max(4, round(talk / 1.0))} content slides.")
    return 0


def cmd_render(args):
    spec = ss.parse(args.spec)
    st = style_for(spec, args)
    out = args.out
    d = build_deck(spec, st, args.aspect, out, args.math)
    res = write_outputs(d, spec, st, args, out)
    layout_json(d, res, out)
    for f in res["files"]:
        print("wrote", f)
    if res["previews"]:
        print(f"previews: {len(res['previews'])} PNG in {os.path.dirname(res['previews'][0])}")
    for n in res["notes"]:
        print("note:", n)
    for lv, code, msg in d.ctx.issues:
        print(f"{lv} {code}: {msg}")
    for o in res.get("overflow", []):
        k, name, pct = (o.split(":") + ["", ""])[:3] if o.count(":") < 3 else (o.split(":")[0], o.split(":")[1] + ":"
                                                                                + o.split(":")[2], o.split(":")[-1])
        print(f"FAIL OVERFLOW: slide {k}: text box '{name}' needs {pct} of its height")
    return 0


def cmd_gallery(args):
    spec = ss.parse(args.spec)
    names = [s.strip() for s in args.styles.split(",")] if args.styles else list(DS.STYLES)
    content = [i for i, b in enumerate(spec.blocks) if b.level == 2 and not b.attrs.get("backup")]
    if args.slides:
        pick = [int(x) - 1 for x in args.slides.split(",")]
    else:
        with_img = [i for i in content if any(e.kind == "image" for e in spec.blocks[i].elements)]
        with_txt = [i for i in content if any(e.kind in ("bullets", "table") for e in spec.blocks[i].elements)]
        pick = []
        for cand in (with_txt[:1], with_img[:1], content):
            for i in cand:
                if i not in pick and len(pick) < 2:
                    pick.append(i)
    sub = copy.copy(spec)
    sub.blocks = [spec.blocks[i] for i in pick if 0 <= i < len(spec.blocks)]
    os.makedirs(args.out, exist_ok=True)
    rows = []
    for name in names:
        st = DS.get(name, parse_palette(spec.get("palette")) | parse_palette(args.palette), args.font)
        sd = os.path.join(args.out, name)
        os.makedirs(sd, exist_ok=True)
        d = build_deck(sub, st, args.aspect, sd, args.math)
        p = os.path.join(sd, "sample.pptx")
        d.pres.save(p)
        html = os.path.join(sd, "sample.html")
        d.pres.to_html(html)
        pngs = []
        err = dk.html_to_pdf(html, os.path.join(sd, "sample.pdf"))
        if not err:
            pngs, err = dk.pdf_to_png(os.path.join(sd, "sample.pdf"), os.path.join(sd, "s"), 900)
        if not pngs:
            pngs, err2 = dk.quicklook_png(d.pres.save_each(sd, "q"), sd, 900)
        rows.append((name, st, pngs, p))
        print(f"{name}: {p}" + (f" ({len(pngs)} previews)" if pngs else f" (no preview: {err})"))
    W, H = ASPECTS[args.aspect]
    cell_w = 300
    cards = []
    for name, st, pngs, p in rows:
        imgs = "".join(f'<img src="file://{os.path.abspath(x)}" style="width:{cell_w}px;height:{cell_w * H / W:.0f}px;'
                       f'border:1px solid #CCC;margin-right:10px">' for x in pngs)
        cards.append(f'<div class="row"><div class="lab"><b>{name}</b><br><span>{st["label"]}</span>'
                     f'<p>{st["summary"]}</p><p><i>Best for:</i> {st["best_for"]}</p></div>{imgs}</div>')
    ncol = max((len(r[2]) for r in rows), default=1)
    page_w = 300 + ncol * (cell_w + 12) + 40
    page_h = len(rows) * (cell_w * H / W + 28) + 80
    doc = (f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>@page{{size:{page_w}px {page_h:.0f}px;margin:0}}'
           "body{font-family:Arial,'PingFang SC',sans-serif;margin:20px;color:#222}.row{display:flex;align-items:"
           "flex-start;margin-bottom:24px}.lab{width:280px;margin-right:14px;font-size:13px}.lab b{font-size:17px}"
           ".lab span{color:#555}.lab p{margin:4px 0}</style></head><body>"
           f"<h2 style='margin:0 0 14px'>Style gallery: {ss.runs_text(ss.inline(spec.get('title', '')))}</h2>"
           + "".join(cards) + "</body></html>")
    gh = os.path.join(args.out, "gallery.html")
    with open(gh, "w", encoding="utf-8") as fh:
        fh.write(doc)
    gp = os.path.join(args.out, "gallery.pdf")
    if not dk.html_to_pdf(gh, gp):
        files, _ = dk.pdf_to_png(gp, os.path.join(args.out, "gallery"), 1800)
        if files:
            os.replace(files[0], os.path.join(args.out, "gallery.png"))
            print("wrote", os.path.join(args.out, "gallery.png"))
    print("wrote", gh)
    return 0


def cmd_check(args):
    spec = ss.parse(args.spec)
    st = style_for(spec, args)
    out = args.out
    work = os.path.join(out, ".check-build")
    d = build_deck(spec, st, args.aspect, work, args.math)
    html = os.path.join(work, "twin.html")
    d.pres.to_html(html)
    over = twin_overflow(d, html)
    f = dc.Findings()
    lang = args.lang or ("zh" if dk.has_cjk(ss.visible_text(spec)) else "en")
    block_slide = {}
    for info in d.slides:
        if info["kind"] != "cover":
            pass
    k = 1 if d.slides and d.slides[0]["kind"] == "cover" else 0
    for b in spec.blocks:
        k += 1
        block_slide[id(b)] = k

    def where(b):
        return f"slide {block_slide.get(id(b), '?')} ({b.title_text[:40]})"
    for lv, code, msg in d.ctx.issues:
        f.add(lv, code, msg.split(":")[0] if msg.startswith("slide") else "layout", msg)
    for o in over:
        parts = o.split(":")
        f.add("FAIL", "OVERFLOW", f"slide {parts[0]}", f"text box '{':'.join(parts[1:-1])}' needs {parts[-1]} of its "
                                                      "height in the rendered preview")
    vis = [("front matter", "\n".join(str(spec.meta.get(x, "")) for x in ss.VISIBLE_META if spec.meta.get(x)))]
    vis += [(where(b), ss.block_text(b)) for b in spec.blocks]
    notes = [(where(b) + " notes", b.notes) for b in spec.blocks if b.notes]
    dc.check_placeholders(f, vis, "FAIL")
    dc.check_placeholders(f, notes, "WARN")
    sources = list(args.source or [])
    if not sources and spec.get("source") and not dk.placeholders(spec.get("source")):
        sources = [spec.resolve(x.strip()) for x in spec.get("source").split(",")]
    if sources:
        src_text, errs = dc.load_sources(sources)
        for e in errs:
            f.add("WARN", "SOURCE", "sources", e)
        if src_text:
            dc.check_numbers(f, vis[1:] + notes, src_text, args.all_numbers)
            dc.check_claims(f, vis[1:], src_text)
    else:
        f.add("INFO", "NO-SOURCE", "sources", "no --source given: numbers and claims were not traced")
    ledger = args.ledger or (spec.get("ledger") if spec.get("ledger") and not dk.placeholders(spec.get("ledger"))
                             else None)
    if ledger:
        since = args.since or (spec.get("since") if spec.get("since") and not dk.placeholders(spec.get("since"))
                               else None)
        dc.check_ledger(f, spec, spec.resolve(ledger) if not args.ledger else ledger, where, since)
    # timing: counted from the speaker notes
    minutes = args.minutes or _num(spec.get("minutes"))
    qa = args.qa if args.qa is not None else (_num(spec.get("qa")) or 0)
    rows, total, est = [], 0.0, 0
    for info in d.slides:
        if info["backup"]:
            continue
        nt = info["notes"] or ""
        declared = _num(info.get("time"))
        if declared:
            sec = declared * 60
            how = "declared"
        elif nt.strip() and not dk.placeholders(nt):
            sec = dk.speaking_seconds(nt, args.wpm, args.cpm)
            how = "notes"
        else:
            sec = 15.0 if info["kind"] in ("cover", "section") else args.per_slide * 60
            how = "assumed"
            if info["kind"] == "content":
                est += 1
        total += sec
        rows.append((info["n"], info["title"][:50], how, sec))
    if minutes:
        talk = minutes - qa
        if total > talk * 60 * 1.1:
            f.add("FAIL", "TIMING-OVER", "talk", f"about {total / 60:.1f} min of speaking for {talk:g} min of talking "
                                                  f"time ({minutes:g} min minus {qa:g} min Q&A)")
        elif total < talk * 60 * 0.6:
            f.add("WARN", "TIMING-UNDER", "talk", f"about {total / 60:.1f} min of speaking for {talk:g} min")
    if est:
        f.add("WARN", "TIMING-ASSUMED", "talk", f"{est} content slide(s) have neither speaker notes nor a declared "
                                                f"{{time=…}}; their time is assumed ({args.per_slide:g} min each), "
                                                "not counted")
    # density, assertion titles, fonts
    for info in d.slides:
        if info["kind"] != "content":
            continue
        b = next((bb for bb in spec.blocks if block_slide.get(id(bb)) == info["n"]), None)
        if b is None:
            continue
        words = sum(dk.word_count(ss.element_text(e)) for e in b.elements)
        nb = sum(len(e.items) for e in b.elements if e.kind == "bullets")
        if words > st["max_words"] and not info["backup"]:
            f.add("WARN", "DENSE", where(b), f"{words} words on the slide (style '{st['name']}' suggests at most "
                                             f"{st['max_words']}); move detail to the notes")
        if nb > 7:
            f.add("WARN", "BULLETS", where(b), f"{nb} bullets; more than 6-7 are hard to follow")
        if st.get("assertion") and dk.word_count(b.title_text) < 5:
            f.add("WARN", "TITLE-NOT-CLAIM", where(b), "assertion-evidence titles should be a full-sentence claim")
        if info["body_pt"] and info["body_pt"] < st["body_pt"] - 0.5:
            f.add("INFO", "FONT-SHRUNK", where(b), f"body text set at {info['body_pt']} pt to fit "
                                                   f"(style default {st['body_pt']} pt)")
    dc.check_contrast(f, DS.text_pairs(st), f"style {st['name']}")
    dc.check_cvd(f, {"accent": st["accent"], "accent2": st.get("accent2", st["accent"])}, f"style {st['name']}")
    dc.check_dpi(f, d.ctx.placed, 110, 60, "on a 1920-pixel projector")
    tim = ["## Timing", "", "| slide | title | basis | seconds |", "|---|---|---|---|"]
    tim += [f"| {n} | {t.replace('|', '/')} | {h} | {s:.0f} |" for n, t, h, s in rows]
    tim.append(f"| | **total** | | **{total:.0f} s = {total / 60:.1f} min** |")
    header = [f"Spec: `{args.spec}`", f"Style: {st['name']}; slides: {len(d.slides)} "
              f"({sum(1 for s_ in d.slides if s_['backup'])} backup)",
              f"Sources: {', '.join(sources) if sources else 'none'}; ledger: {ledger or 'none'}"]
    md, js = f.write(out, "Deck check" if lang == "en" else "幻灯片检查", header, lang,
                     {"timing": rows, "total_seconds": total}, ["\n".join(tim)])
    print(f"FAIL {f.count('FAIL')} · WARN {f.count('WARN')} · INFO {f.count('INFO')}; talk ≈ {total / 60:.1f} min")
    print("wrote", md)
    return f.exit_code()


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("styles")
    a.add_argument("--json", action="store_true")
    sp.add_parser("templates")
    a = sp.add_parser("init")
    a.add_argument("--template", default="progress")
    a.add_argument("--minutes", type=float, default=15)
    a.add_argument("--qa", type=float)
    a.add_argument("--lang", choices=("en", "zh"), default="en")
    a.add_argument("--out", required=True)
    a.add_argument("--force", action="store_true")

    def common(a):
        a.add_argument("spec")
        a.add_argument("--style")
        a.add_argument("--aspect", default="16:9")
        a.add_argument("--palette")
        a.add_argument("--font")
        a.add_argument("--math", choices=("auto", "image", "text"), default="auto")
        a.add_argument("--beamer-theme", help="with --style beamer: the Beamer theme for --format tex (default Madrid)")
        a.add_argument("--out", required=True)
    a = sp.add_parser("render")
    common(a)
    a.add_argument("--format", default="pptx", help="comma list of pptx, tex")
    a.add_argument("--compile", action="store_true", help="compile the Beamer file (needs LaTeX)")
    a.add_argument("--quicklook", action="store_true", help="also preview the .pptx with macOS Quick Look")
    a.add_argument("--no-preview", action="store_true")
    a = sp.add_parser("gallery")
    common(a)
    a.add_argument("--styles")
    a.add_argument("--slides", help="1-based block numbers to sample (default: two content slides)")
    a = sp.add_parser("check")
    common(a)
    a.add_argument("--source", nargs="*")
    a.add_argument("--ledger")
    a.add_argument("--since")
    a.add_argument("--minutes", type=float)
    a.add_argument("--qa", type=float)
    a.add_argument("--wpm", type=float, default=130)
    a.add_argument("--cpm", type=float, default=250, help="CJK characters per minute")
    a.add_argument("--per-slide", type=float, default=1.5, help="minutes assumed for a slide without notes")
    a.add_argument("--all-numbers", action="store_true", help="also trace integers 0-10")
    a.add_argument("--lang", choices=("en", "zh"))
    args = ap.parse_args(argv)
    return {"styles": cmd_styles, "templates": cmd_templates, "init": cmd_init, "render": cmd_render,
            "gallery": cmd_gallery, "check": cmd_check}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
