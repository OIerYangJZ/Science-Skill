#!/usr/bin/env python3
"""poster.py - build, export and check a research poster whose master copy is an editable HTML file.

A Markdown content spec (see lib/slidespec.py) is rendered once into poster.html: plain HTML and CSS that
you edit by hand or in the browser (toolbar: Edit text, Save HTML, Re-fit, Print). The PDF and previews
are always exported from the HTML, so they contain your edits. See references/editing.md.

Usage
  poster.py styles | sizes
  poster.py init --template empirical --size A0 [--lang zh] --out poster.md
  poster.py render poster.md [--style classic] [--size A0-landscape] --out DIR    -> DIR/poster.html + PDF/PNG
  poster.py export DIR/poster.html                    PDF + preview PNGs from the HTML as it is now
  poster.py restyle DIR/poster.html --style dark      same content, another style -> poster-dark.html
  poster.py gallery poster.md|poster.html --out DIR   every style with your content, side by side
  poster.py check DIR/poster.html [--source paper.tex results.csv] [--max-size 841x1189mm] --out DIR

render never overwrites an existing poster.html (it may contain your edits) unless --force; --pptx also
writes a PowerPoint version built from the spec. check exits 1 while a FAIL remains: a placeholder, a
number not in the sources, overflow, text below the readable minimum, a missing or low-resolution figure,
unreadable contrast, a billboard without a takeaway, or a poster larger than the venue's board.
"""
from __future__ import annotations

import argparse
import copy
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
import poster_styles as PS      # noqa: E402
import poster_templates as PT   # noqa: E402
import poster_html as PH        # noqa: E402

A0_SHORT = 841 / 25.4


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
    name = getattr(args, "style", None) or spec.get("style") or "classic"
    pal = parse_palette(spec.get("palette"))
    pal.update(parse_palette(getattr(args, "palette", None)))
    return PS.get(name, pal, getattr(args, "font", None) or spec.get("font"))


def size_for(spec: ss.Spec, args) -> tuple[float, float]:
    s = getattr(args, "size", None) or spec.get("size") or "A0"
    if dk.placeholders(s):
        s = "A0"
    return PS.parse_size(s)


def linear_partition(hs: list[float], k: int) -> list[int]:
    """Split hs (in order) into k contiguous groups minimising the largest sum; returns group index per item."""
    n = len(hs)
    if n == 0:
        return []
    k = max(1, min(k, n))
    pre = [0.0]
    for h in hs:
        pre.append(pre[-1] + h)
    INF = float("inf")
    best = [[INF] * (n + 1) for _ in range(k + 1)]
    cut = [[0] * (n + 1) for _ in range(k + 1)]
    best[0][0] = 0.0
    for j in range(1, k + 1):
        for i in range(1, n + 1):
            for p in range(j - 1, i):
                v = max(best[j - 1][p], pre[i] - pre[p])
                if v < best[j][i]:
                    best[j][i], cut[j][i] = v, p
    groups = [0] * n
    i = n
    for j in range(k, 0, -1):
        p = cut[j][i]
        for t in range(p, i):
            groups[t] = j - 1
        i = p
    return groups


class Poster:
    def __init__(self, spec: ss.Spec, st: dict, size: tuple[float, float], workdir: str, math: str = "auto"):
        self.spec, self.st = spec, st
        self.W, self.H = size
        self.u = min(self.W, self.H) / A0_SHORT
        self.m = 1.0 * self.u
        self.g = 0.7 * self.u
        self.ctx = sk.Ctx(dict(st, highlight_fg=st["accent2"] if st["layout"] != "billboard" else st["accent"]),
                          workdir, spec.path, math)
        self.pres = px.Pptx(self.W, self.H, fonts={"latin": st["font_body"], "ea": st["font_ea"],
                                                   "heading": st["font_heading"]},
                            colours={"dk1": st["fg"], "lt1": st["bg"], "accent1": st["accent"],
                                     "accent2": st["accent2"]},
                            title=spec.get("title", ""), author=spec.get("authors", ""))
        self.info = {"body_pt": None, "scale": 1.0, "overflow": [], "panels": [], "size_in": [self.W, self.H],
                     "u": self.u}
        blocks = [b for b in spec.blocks if b.level == 2]
        self.footer_blocks = [b for b in blocks if b.attrs.get("footer")]
        self.center_blocks = [b for b in blocks if b.attrs.get("center") or b.attrs.get("key")]
        self.panels = [b for b in blocks if b not in self.footer_blocks and b not in self.center_blocks]
        if st["layout"] != "billboard":
            self.panels = [b for b in blocks if b not in self.footer_blocks]
            self.center_blocks = []
        if st.get("figure_labels"):
            k = 0
            for b in self.panels + self.center_blocks:
                for e in b.elements:
                    if e.kind == "image" and "label" not in e.attrs:
                        e.attrs["label"] = "abcdefghijklmnopqrstuvwxyz"[k % 26]
                        k += 1

    def pt(self, a0_pt: float) -> float:
        return a0_pt * self.u

    def runs(self, text: str, size, color, bold=False):
        return self.ctx.runs(ss.inline(text), size, color, bold=bold)

    # --- header and footer ----------------------------------------------------
    def header(self, s: px.Slide) -> float:
        st, W, m = self.st, self.W, self.m
        meta = self.spec.meta
        fg, sub = st["header_fg"], st["header_sub_fg"]
        al = st["title_align"]
        logos = [x.strip() for x in meta.get("logos", "").split(",") if x.strip() and not dk.placeholders(x)]
        logo_imgs = []
        for lp in logos:
            png, info = self.ctx.image(self.spec.resolve(lp))
            if png:
                logo_imgs.append((png, info, lp))
        logo_w = 0.0
        tsize = self.pt(st["title_pt"])
        lh = 3.6 * self.u
        if logo_imgs:
            logo_w = sum(lh / (dk.aspect(i) or 1) for _p, i, _l in logo_imgs) + self.g * len(logo_imgs)
            logo_w = min(logo_w, W * 0.3)
        tx = m
        tw = W - 2 * m - logo_w
        ps = [px.para(self.ctx.runs(ss.inline(meta.get("title", "")), tsize, fg, bold=st["title_bold"]), size=tsize,
                      align=al, line=1.05, font=st["font_heading"])]
        if meta.get("authors"):
            ps.append(px.para(self.runs(meta["authors"], self.pt(40), fg, bold=True), size=self.pt(40), align=al,
                              space_before=self.pt(18)))
        if meta.get("affiliations"):
            ps.append(px.para(self.runs(meta["affiliations"], self.pt(30), sub), size=self.pt(30), align=al,
                              space_before=self.pt(8)))
        h = self.ctx.measure([("header", tw, ps)])["header"]
        pad = 0.8 * self.u if st.get("header_bg") else 0
        top = m if not st.get("header_bg") else 0
        band_h = h + 2 * pad + (m if st.get("header_bg") else 0) * 0.6
        if st.get("header_bg"):
            s.rect(0, 0, W, band_h, fill=st["header_bg"])
            y_text = (band_h - h) / 2
        else:
            y_text = top
        s.text(tx, y_text, tw, h, ps, name="header")
        # logos, right-aligned and vertically centred on the text block
        x = W - m
        for png, info, lp in reversed(logo_imgs):
            ar = dk.aspect(info) or 1
            lw = min(lh / ar, W * 0.3)
            lhh = lw * ar
            x -= lw
            s.image(png, x, y_text + (h - lhh) / 2, lw, lhh, descr=lp)
            self.ctx.placed.append({"src": lp, "w_in": lw, "h_in": lhh, "info": info, "where": "header logo"})
            x -= self.g
        bottom = band_h if st.get("header_bg") else y_text + h + 0.5 * self.u
        if not st.get("header_bg") and st["name"] in ("minimal", "journal", "billboard"):
            s.rect(m, bottom, W - 2 * m, 0.06 * self.u if st["name"] != "minimal" else 0.12 * self.u,
                   fill=st["fg"] if st["name"] != "minimal" else st["accent"])
            bottom += 0.12 * self.u
        return bottom

    def footer(self, s: px.Slide, measure_only: bool = False) -> float:
        """Draws the footer band; returns its top y."""
        st, W, H, m, u = self.st, self.W, self.H, self.m, self.u
        meta = self.spec.meta
        size = self.pt(20)
        cols = []
        if meta.get("contact"):
            cols.append([px.para(self.runs("**Contact** " + meta["contact"], size, st["footer_fg"]), size=size)])
        for b in self.footer_blocks:
            ps = [px.para(self.ctx.runs(b.title, size, st["footer_fg"], bold=True), size=size)]
            for e in b.elements:
                ps += self.ctx.paras_for(e, size, st["footer_fg"])
            cols.append(ps)
        if meta.get("footer"):
            cols.append([px.para(self.runs(meta["footer"], size, st["footer_fg"]), size=size)])
        qr = meta.get("qr") if st["layout"] != "billboard" else None
        qr_png = None
        if qr and not dk.placeholders(qr):
            qr_png, qr_info = self.ctx.image(self.spec.resolve(qr))
        qr_side = 3.2 * u if qr_png else 0
        if not cols and not qr_png:
            return H - m
        avail = W - 2 * m - (qr_side + self.g if qr_png else 0)
        weights = [max(1.0, len("".join(r["text"] for p in c for r in p["runs"])) ** 0.5) for c in cols] or [1]
        tot = sum(weights)
        ws = [(avail - self.g * (len(cols) - 1)) * w / tot for w in weights]
        hs = self.ctx.measure([(f"f{i}", w, c) for i, (w, c) in enumerate(zip(ws, cols))])
        fh = max(list(hs.values()) + [qr_side])
        top = H - m - fh
        if measure_only:
            return top - 0.4 * u
        s.rect(m, top - 0.4 * u, W - 2 * m, 0.04 * u, fill=st["muted"])
        x = m
        for i, (w, c) in enumerate(zip(ws, cols)):
            s.text(x, top, w, hs[f"f{i}"], c, name="footer")
            x += w + self.g
        if qr_png:
            s.image(qr_png, W - m - qr_side, top, qr_side, qr_side, descr="QR code")
            self.ctx.placed.append({"src": qr, "w_in": qr_side, "h_in": qr_side, "info": qr_info, "where": "footer QR"})
        return top - 0.4 * u

    # --- panels ------------------------------------------------------------------
    def boxed(self) -> bool:
        return bool(self.st.get("panel_bg") or self.st.get("panel_line"))

    def panel_title(self, b: ss.Block, k: int, w: float, scale: float) -> tuple[list[dict], float, float]:
        """(paragraphs, height, left offset for a number badge)"""
        st = self.st
        hs = self.pt(st["heading_pt"]) * scale
        kind = st["panel_title"]
        runs = list(b.title)
        if kind == "rule":
            runs = [ss.Run(f"{k:02d}  ")] + runs
        if kind == "caps":
            runs = [ss.Run(r.text.upper(), bold=True) for r in runs]
            hs *= 0.72
        color = st["panel_title_fg"]
        rr = self.ctx.runs(runs, hs, color, bold=True)
        if kind == "rule":
            rr[0]["color"] = st["accent"]
        off = 1.25 * hs / 72 * 1.6 if kind == "number" else 0
        ps = [px.para(rr, size=hs, line=1.05, font=st["font_heading"])]
        pad = 0.5 * self.u if self.boxed() else 0.0
        inner = w - 0.7 * self.u if kind == "bar" else w - 2 * pad - off
        h = self.ctx.measure([(f"pt{id(b)}-{scale:.3f}", inner, ps)])[f"pt{id(b)}-{scale:.3f}"]
        if kind == "number":
            h = max(h, off * 0.85)
        return ps, h, off

    def panel(self, b: ss.Block, k: int, w: float, scale: float, color: str | None = None) -> dict:
        st, u = self.st, self.u
        pad = 0.5 * u if self.boxed() else 0.0
        tps, th, off = self.panel_title(b, k, w, scale)
        bar = st["panel_title"] == "bar"
        title_block = th + (2 * 0.3 * u if bar else 0) + 0.35 * u * scale + \
            (0.14 * u if st["panel_title"] in ("rule", "caps") else 0)
        size = self.pt(st["body_pt"]) * scale
        ps = sk.pieces(self.ctx, b.elements, w - 2 * pad, size, f"p{k}-{scale:.3f}", color=color,
                       where=f"panel {k} ({b.title_text[:30]})")
        fixed = sk.stack_height(ps, 0.45 * u * scale, 0.0)
        flex = sum(p.flex for p in ps)
        return {"b": b, "k": k, "w": w, "pad": pad, "tps": tps, "th": th, "off": off, "title_block": title_block,
                "pieces": ps, "fixed": title_block + fixed + 2 * pad, "flex": flex, "size": size, "scale": scale,
                "gap": 0.45 * u * scale}

    def draw_panel(self, s: px.Slide, P: dict, x: float, y: float, h: float, img_scale: float):
        st, u = self.st, self.u
        w, pad = P["w"], P["pad"]
        kind = st["panel_title"]
        if self.boxed():
            s.rect(x, y, w, h, fill=st.get("panel_bg"), line=st.get("panel_line"), line_w=1.5 * u,
                   radius=st.get("panel_radius") * u or None)
        cy = y
        if kind == "bar":
            bh = P["th"] + 2 * 0.3 * u
            r = st.get("panel_radius") * u or None
            s.rect(x, y, w, bh, fill=st["panel_title_bg"], radius=r)
            if r:
                s.rect(x, y + bh / 2, w, bh / 2, fill=st["panel_title_bg"])
            s.text(x + 0.35 * u, y + 0.3 * u, w - 0.7 * u, P["th"], P["tps"], name=f"panel {P['k']}:title")
            cy = y + bh + 0.35 * u * P["scale"]
        else:
            cy = y + pad
            if kind == "caps":
                s.rect(x + pad, cy, w - 2 * pad, 0.05 * u, fill=st["fg"])
                cy += 0.14 * u
            if kind == "number":
                d = P["off"] * 0.85
                s.rect(x + pad, cy, d, d, fill=st["accent"], geom="ellipse")
                ns = P["tps"][0]["size"] * 0.8
                s.text(x + pad, cy, d, d, [px.para(str(P["k"]), size=ns, bold=True, color="#FFFFFF", align="c")],
                       anchor="m", inset=0, name=f"panel {P['k']}:number")
                s.text(x + pad + P["off"], cy + max(0, (d - P["th"]) / 2), w - 2 * pad - P["off"], P["th"], P["tps"],
                       name=f"panel {P['k']}:title")
            else:
                s.text(x + pad, cy, w - 2 * pad, P["th"], P["tps"], name=f"panel {P['k']}:title")
            cy += P["th"]
            if kind == "rule":
                s.rect(x + pad, cy + 0.05 * u, w - 2 * pad, 0.09 * u, fill=st["accent"])
                cy += 0.14 * u
            cy += 0.35 * u * P["scale"]
        sk.draw_stack(self.ctx, s, P["pieces"], x + pad, cy, w - 2 * pad, P["gap"], img_scale,
                      where=f"panel {P['k']} ({P['b'].title_text[:30]})")

    # --- layouts ---------------------------------------------------------------------
    def assign(self, blocks: list[ss.Block], ncol: int, heights: list[float]) -> list[int]:
        pinned = [b.attrs.get("col") for b in blocks]
        if all(p is None for p in pinned):
            return linear_partition(heights, ncol)
        out, cur = [], 0
        for b in blocks:
            c = b.attrs.get("col")
            if c is not None:
                try:
                    cur = max(0, min(ncol - 1, int(str(c)) - 1))
                except ValueError:
                    pass
            out.append(cur)
        return out

    def columns_layout(self, s, top, bottom, x0, width, ncol, blocks, number_from=1, draw=True):
        st, u = self.st, self.u
        g = self.g
        colw = (width - g * (ncol - 1)) / ncol
        avail = bottom - top
        def attempt(sc):
            self.ctx.collect()              # measure all text blocks of this attempt in one browser call
            for i, b in enumerate(blocks):
                self.panel(b, number_from + i, colw, sc)
            self.ctx.flush()
            Ps = [self.panel(b, number_from + i, colw, sc) for i, b in enumerate(blocks)]
            groups = self.assign(blocks, ncol, [P["fixed"] + P["flex"] for P in Ps])
            cols = [[P for P, gi in zip(Ps, groups) if gi == c] for c in range(ncol)]
            fixed = [sum(P["fixed"] for P in c) + g * max(0, len(c) - 1) for c in cols]
            full = [f + sum(P["flex"] for P in c) for f, c in zip(fixed, cols)]
            return cols, fixed, full
        # largest text scale (up to 120%) at which every column fits with full-width figures;
        # otherwise 100% with smaller figures; otherwise shrink the text (down to 72%)
        scale = 1.0
        cols, fixed, full = attempt(scale)
        if max(full, default=0) <= avail:
            for sc in (1.05, 1.1, 1.15, 1.2):
                c2, f2, u2 = attempt(sc)
                if max(u2, default=0) > avail:
                    break
                scale, cols, fixed, full = sc, c2, f2, u2
        while max(fixed, default=0) > avail and scale > 0.72:
            scale *= 0.95
            cols, fixed, full = attempt(scale)
        over = [c for c, f in enumerate(fixed) if f > avail]
        for c in over:
            self.info["overflow"].append(f"column {c + 1}")
            self.ctx.issue("FAIL", "OVERFLOW", f"column {c + 1}", f"column {c + 1} needs {fixed[c]:.1f} in of "
                           f"{avail:.1f} in even with text at {scale:.0%}; cut words or move a panel")
        self.info["scale"] = scale if not self.info["panels"] and not self.info.get("fill") else \
            min(self.info["scale"], scale)
        self.info["body_pt"] = round(self.pt(st["body_pt"]) * self.info["scale"], 1)
        if not draw:
            return
        for c, col in enumerate(cols):
            x = x0 + c * (colw + g)
            flex = sum(P["flex"] for P in col)
            room = avail - fixed[c]
            img = 1.0 if flex <= 0 else max(0.25, min(1.0, room / flex)) if room > 0 else 0.25
            used = fixed[c] + flex * img
            extra = max(0.0, avail - used)
            self.info.setdefault("fill", []).append(round(used / avail, 2) if avail > 0 else 1.0)
            y = top
            for i, P in enumerate(col):
                h = P["fixed"] + P["flex"] * img
                if i == len(col) - 1 and self.boxed() and extra > 0:
                    h += extra                       # boxed styles: columns end on the same line
                self.draw_panel(s, P, x, y, h, img)
                self.info["panels"].append({"k": P["k"], "title": P["b"].title_text, "column": c + 1,
                                            "body_pt": round(P["size"], 1)})
                spread = min(extra / max(1, len(col) - 1), 2.0 * u) if not self.boxed() and len(col) > 1 else 0
                y += h + g + spread

    def billboard(self, s, top, bottom):
        st, W, u, m, g = self.st, self.W, self.u, self.m, self.g
        bw = W - 2 * m
        side = (bw - 2 * g) * 0.25
        center = (bw - 2 * g) * 0.5
        left = [b for b in self.panels if str(b.attrs.get("col", "1")) in ("1", "left")]
        right = [b for b in self.panels if b not in left]
        if not any(b.attrs.get("col") for b in self.panels):
            n = len(self.panels)
            left, right = self.panels[:(n + 1) // 2], self.panels[(n + 1) // 2:]
        self.columns_layout(s, top, bottom, m, side, 1, left, 1)
        self.columns_layout(s, top, bottom, m + side + g + center + g, side, 1, right, len(left) + 1)
        cx = m + side + g
        s.rect(cx, top, center, bottom - top, fill=st["center_bg"], radius=0.4 * u)
        pad = 1.2 * u
        inner = center - 2 * pad
        take = self.spec.get("takeaway") or next((b.title_text for b in self.spec.blocks if b.level == 1), "")
        if not take:
            self.ctx.issue("FAIL", "NO-TAKEAWAY", "centre", "billboard style needs a takeaway sentence "
                                                           "(front matter 'takeaway:')")
        tsz = self.pt(st.get("takeaway_pt", 110))
        ctx = self.ctx
        ctx.t = dict(ctx.t, highlight_fg=st["accent2"])
        tps = [px.para(ctx.runs(ss.inline(take), tsz, st["center_fg"], bold=True), size=tsz, line=1.08)]
        th = ctx.measure([("take", inner, tps)])["take"]
        while th > (bottom - top) * 0.45 and tsz > self.pt(60):
            tsz *= 0.92
            tps = [px.para(ctx.runs(ss.inline(take), tsz, st["center_fg"], bold=True), size=tsz, line=1.08)]
            th = ctx.measure([("take", inner, tps)])["take"]
        qr = self.spec.get("qr")
        qr_png = None
        if qr and not dk.placeholders(qr):
            qr_png, qr_info = ctx.image(self.spec.resolve(qr))
        qside = 4.5 * u if qr_png else 0
        saved = dict(st)
        self.st = dict(st, panel_title_fg=st["center_fg"], panel_bg=None, panel_line=None, fg=st["center_fg"])
        Ps = [self.panel(b, 90 + i, inner, 1.0, color=st["center_fg"]) for i, b in enumerate(self.center_blocks)]
        fixed = sum(P["fixed"] for P in Ps) + g * max(0, len(Ps) - 1)
        flex = sum(P["flex"] for P in Ps)
        room = (bottom - top) - 2 * pad - th - 1.5 * u - (qside + 1.5 * u if qr_png else 0)
        img = 1.0 if flex <= 0 else max(0.2, min(1.0, (room - fixed) / flex))
        content_h = th + (1.5 * u + fixed + flex * img if Ps else 0)
        y = top + pad + max(0.0, (room - fixed - flex * img) * 0.35)
        s.text(cx + pad, y, inner, th, tps, name="takeaway")
        y += th + 1.5 * u
        for P in Ps:
            h = P["fixed"] + P["flex"] * img
            self.draw_panel(s, P, cx + pad, y, h, img)
            y += h + g
        self.st = saved
        if qr_png:
            qy = bottom - pad - qside
            s.rect(cx + (center - qside) / 2 - 0.2 * u, qy - 0.2 * u, qside + 0.4 * u, qside + 0.4 * u, fill="#FFFFFF",
                   radius=0.2 * u)
            s.image(qr_png, cx + (center - qside) / 2, qy, qside, qside, descr="QR code")
            ctx.placed.append({"src": qr, "w_in": qside, "h_in": qside, "info": qr_info, "where": "centre QR"})
            lab = self.spec.get("qr-label") or "Scan for the paper"
            s.text(cx + pad, qy - 1.3 * u, inner, 1.0 * u, [px.para(ctx.runs(ss.inline(lab), self.pt(26), st["center_fg"]),
                                                                    size=self.pt(26), align="c")], name="qr label")
        if content_h > (bottom - top) - 2 * pad:
            self.ctx.issue("FAIL", "OVERFLOW", "centre", "the takeaway and centre panels do not fit the centre column")

    def build(self) -> px.Pptx:
        st = self.st
        s = self.pres.slide(bg=st["bg"])
        top = self.header(s) + self.g
        bottom = self.footer(s) - self.g * 0.5
        if st["layout"] == "billboard":
            self.billboard(s, top, bottom)
        else:
            ncol = int(self.spec.get("columns") or (st["cols_landscape"] if self.W > self.H else st["cols_portrait"]))
            self.columns_layout(s, top, bottom, self.m, self.W - 2 * self.m, ncol, self.panels, 1)
        return self.pres


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def render_files(p: Poster, spec: ss.Spec, out: str, stem: str, preview: bool = True) -> dict:
    os.makedirs(out, exist_ok=True)
    res = {"files": [], "notes": [], "overflow": []}
    pp = os.path.join(out, stem + ".pptx")
    p.pres.save(pp)
    probs = px.validate(pp)
    if probs:
        res["notes"].append("pptx structure problems: " + "; ".join(probs[:5]))
    res["files"].append(pp)
    html = os.path.join(out, stem + ".html")
    p.pres.to_html(html)
    res["files"].append(html)
    dom, err = dk.html_dump_dom(html, 6000)
    if dom:
        m = re.search(r'data-overflow="([^"]*)"', dom)
        res["overflow"] = [x for x in (m.group(1).split(";") if m else []) if x]
    if preview:
        pdf = os.path.join(out, stem + ".pdf")
        err = dk.html_to_pdf(html, pdf, 6000)
        if err:
            res["notes"].append(f"no PDF/preview: {err}")
        else:
            res["files"].append(pdf)
            for name, wpx in (("preview", 1600), ("glance", 520)):
                files, err = dk.pdf_to_png(pdf, os.path.join(out, name), wpx)
                if files:
                    os.replace(files[0], os.path.join(out, name + ".png"))
                    res["files"].append(os.path.join(out, name + ".png"))
    return res


def cmd_styles(args):
    if args.json:
        print(json.dumps({k: {x: v[x] for x in ("label", "summary", "best_for")} for k, v in PS.STYLES.items()},
                         ensure_ascii=False, indent=1))
        return 0
    for k, v in PS.STYLES.items():
        print(f"{k:11s} {v['label']}\n            {v['summary']}\n            Best for: {v['best_for']}\n")
    return 0


def cmd_sizes(args):
    for k, (w, h) in PS.SIZES.items():
        print(f"{k:9s} {w:.0f} x {h:.0f} mm ({w / 25.4:.1f} x {h / 25.4:.1f} in)")
    print("append -landscape to an ISO size; or give WxHmm / WxHin / WxHcm")
    return 0


def cmd_init(args):
    t = PT.TEMPLATES.get(args.template)
    if not t:
        raise SystemExit(f"unknown template; choose from {', '.join(PT.TEMPLATES)}")
    if os.path.exists(args.out) and not args.force:
        raise SystemExit(f"{args.out} exists; use --force to overwrite")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(t[args.lang].format(size=args.size))
    print(f"wrote {args.out} ({t['label']}); size {args.size}")
    return 0


def _report_lines(rep: dict) -> list[str]:
    if not rep:
        return []
    out = [f"text scale {rep.get('scale', 1):.0%}, body text {rep.get('body_pt')} pt"]
    if rep.get("overflow"):
        out.append(f"OVERFLOW in {', '.join(rep['overflow'])}: cut words or move a section")
    return out


def cmd_render(args):
    spec = ss.parse(args.spec)
    st = style_for(spec, args)
    size = size_for(spec, args)
    os.makedirs(args.out, exist_ok=True)
    html_path = os.path.join(args.out, "poster.html")
    if os.path.exists(html_path) and not args.force:
        raise SystemExit(f"{html_path} exists and may contain your edits; export it with 'poster.py export', "
                         "change its style with 'poster.py restyle', or pass --force to rebuild from the spec")
    path, missing = PH.build(spec, st, size, args.out, args.math)
    print("wrote", path, "(editable master: edit it, then run poster.py export)")
    for m in missing:
        print("FAIL IMG-MISSING:", m)
    if not args.no_preview:
        rep, files, notes = PH.export(path, args.out)
        for f in files:
            print("wrote", f)
        for n in notes:
            print("note:", n)
        for line in _report_lines(rep):
            print(line)
    if args.pptx:
        p = Poster(spec, st, size, os.path.join(args.out, ".pptx-build"), args.math)
        p.build()
        pp = os.path.join(args.out, "poster.pptx")
        p.pres.save(pp)
        print("wrote", pp, "(built from the spec; edits made in the HTML are not in it)")
    return 0


def cmd_export(args):
    rep, files, notes = PH.export(args.html, args.out)
    for f in files:
        print("wrote", f)
    for n in notes:
        print("note:", n)
    for line in _report_lines(rep):
        print(line)
    return 1 if (rep.get("overflow") or not files) else 0


def cmd_restyle(args):
    with open(args.html, encoding="utf-8") as fh:
        doc = fh.read()
    st = PS.get(args.style, parse_palette(args.palette), args.font)
    size = PS.parse_size(args.size) if args.size else None
    new = PH.restyle(doc, st, size)
    out = args.html if args.in_place else (args.out or os.path.splitext(args.html)[0] + f"-{args.style}.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(new)
    print("wrote", out)
    return 0


def cmd_gallery(args):
    src_html = args.spec.lower().endswith((".html", ".htm"))
    spec = None if src_html else ss.parse(args.spec)
    names = [s.strip() for s in args.styles.split(",")] if args.styles else list(PS.STYLES)
    os.makedirs(args.out, exist_ok=True)
    rows = []
    for name in names:
        st = PS.get(name, parse_palette(spec.get("palette") if spec else None) | parse_palette(args.palette), args.font)
        sd = os.path.join(args.out, name)
        os.makedirs(sd, exist_ok=True)
        if src_html:
            doc = open(args.spec, encoding="utf-8").read()
            try:
                doc = PH.restyle(doc, st)
            except SystemExit as e:
                print(f"{name}: skipped ({e})")
                continue
            # keep figure paths valid: write next to the original
            path = os.path.join(os.path.dirname(os.path.abspath(args.spec)), f".gallery-{name}.html")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(doc)
        else:
            path, _missing = PH.build(copy.deepcopy(spec), st, size_for(spec, args), sd, args.math, "sample.html")
        rep, files, notes = PH.export(path, sd)
        if src_html:
            os.remove(path)          # a preview only; restyle writes a real copy when you choose a style
        png = next((f for f in files if f.endswith("-preview.png")), None)
        rows.append((name, st, png))
        print(f"{name}: {png or os.path.join(sd, 'sample.html')}" + ("" if png else f" (no preview: {'; '.join(notes)})"))
    if not rows:
        return 1
    W, Hh = (spec and size_for(spec, args)) or (841, 1189)
    cw = 360
    ch = cw * Hh / W
    cards = "".join(f'<div class="c"><img src="file://{os.path.abspath(png)}" style="width:{cw}px;height:{ch:.0f}px">'
                    f'<b>{name}</b> · {st["label"]}<p>{st["summary"]}</p><p><i>Best for:</i> {st["best_for"]}</p></div>'
                    if png else f'<div class="c"><b>{name}</b> (no preview)</div>' for name, st, png in rows)
    per_row = 3
    nrow = (len(rows) + per_row - 1) // per_row
    page_w = per_row * (cw + 30) + 40
    page_h = nrow * (ch + 190) + 90
    title = ss.runs_text(ss.inline(spec.get("title", ""))) if spec else os.path.basename(args.spec)
    doc = (f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>@page{{size:{page_w}px {page_h:.0f}px;margin:0}}'
           "body{font-family:Arial,'PingFang SC',sans-serif;margin:20px;color:#222}.g{display:flex;flex-wrap:wrap}"
           f".c{{width:{cw}px;margin:0 30px 22px 0;font-size:12.5px}}.c img{{border:1px solid #CCC;display:block;"
           "margin-bottom:6px}.c p{margin:3px 0}.c b{font-size:15px}</style></head><body>"
           f"<h2 style='margin:0 0 14px'>Poster styles: {title}</h2><div class='g'>{cards}</div></body></html>")
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


def _pairs_from_vars(v: dict, billboard: bool) -> list[tuple[str, str, str, bool]]:
    def c(name, fallback=None):
        x = (v.get(name) or "").strip()
        return x if dk.is_hex(x) else fallback
    bg = c("bg", "#FFFFFF")
    panel = c("panel-bg", bg)
    head = c("header-bg", bg)
    pairs = [("body text", c("fg"), panel, False), ("muted text and captions", c("muted"), panel, False),
             ("links", c("link"), panel, False), ("title", c("header-fg"), head, True),
             ("authors and affiliations", c("header-sub-fg"), head, False),
             ("section headings", c("panel-title-fg"), c("panel-title-bg", panel), True),
             ("table header", c("table-head-fg"), c("table-head-bg"), False), ("footer", c("footer-fg"), bg, False)]
    if billboard:
        pairs += [("takeaway", c("center-fg"), c("center-bg"), True), ("takeaway highlight", c("accent2"), c("center-bg"),
                                                                       True)]
    return [p for p in pairs if p[1] and p[2]]


def check_html(path: str, args, f: dc.Findings) -> dict:
    r = PH.read(path)
    base = os.path.dirname(os.path.abspath(path))
    rep, err = PH.inspect(path)
    page = r["page_mm"] or (841, 1189)
    u = min(page) / 841.0
    name = r["meta"].get("style", "classic")
    st = PS.STYLES.get(name, PS.STYLES["classic"])
    # text: placeholders, numbers, claims, words
    where_text = [("header", r["header"])] + ([("takeaway", r["takeaway"])] if r["billboard"] else []) + \
        [(f"section '{s['title'][:40]}'", s["title"] + "\n" + s["text"]) for s in r["sections"]] + [("footer", r["footer"])]
    dc.check_placeholders(f, where_text, "FAIL")
    sources = list(args.source or [])
    if not sources and r["meta"].get("source"):
        sources = [os.path.normpath(os.path.join(base, x.strip())) for x in r["meta"]["source"].split(",") if x.strip()]
    body = [x for x in where_text if x[0] != "footer"]
    if sources:
        src_text, errs = dc.load_sources(sources)
        for e in errs:
            f.add("WARN", "SOURCE", "sources", e)
        if src_text:
            dc.check_numbers(f, body, src_text, args.all_numbers)
            dc.check_claims(f, body, src_text)
    else:
        f.add("INFO", "NO-SOURCE", "sources", "no --source given: numbers and claims were not traced")
    words = sum(dk.word_count(t) for w, t in body if w != "header") + dk.word_count(r["header"].split("\n")[0])
    if words > st["max_words"]:
        f.add("WARN", "WORDS", "poster", f"{words} words (style '{name}' suggests at most {st['max_words']}); visitors "
                                         "read a poster in about 3 minutes")
    else:
        f.add("INFO", "WORDS", "poster", f"{words} words")
    if r["billboard"] and (not r["takeaway"] or dk.placeholders(r["takeaway"])):
        f.add("FAIL", "NO-TAKEAWAY", "centre", "billboard poster without a takeaway sentence")
    if "<h1></h1>" in r["doc"] or "<h1>" not in r["doc"]:
        f.add("FAIL", "MISSING", "header", "no title")
    if "Contact" not in r["footer"] and not any("qr" in i.lower() for i in r["images"]):
        f.add("WARN", "MISSING", "footer", "no contact and no QR code: visitors cannot follow up")
    # layout as the browser renders it
    if rep:
        for col in rep.get("overflow") or []:
            f.add("FAIL", "OVERFLOW", col, f"content does not fit even with text at {rep.get('scale', 0):.0%}; cut "
                                           "words, remove a section or move one to a shorter column")
        need = st["min_body_pt"] * u
        if rep.get("body_pt") and rep["body_pt"] < need - 0.05:
            f.add("FAIL", "FONT-MIN", "poster", f"body text {rep['body_pt']} pt; at least {need:.1f} pt is readable "
                                                "from 1.5-2 m at this size")
        elif rep.get("scale", 1) < 0.999:
            f.add("INFO", "FONT-SHRUNK", "poster", f"text set at {rep['scale']:.0%} of the style size "
                                                   f"(body {rep.get('body_pt')} pt) to fit")
        for im in rep.get("images", []):
            if im.get("broken"):
                f.add("FAIL", "IMG-MISSING", im.get("where") or "poster", f"image not found: {im['src']}")
                continue
            if im.get("vector") or not im["natural"][0] or not im["placed_in"][0]:
                continue
            ppi = im["natural"][0] / im["placed_in"][0]
            nm = os.path.basename(im["src"])
            if ppi < 100:
                f.add("FAIL", "IMG-RESOLUTION", im.get("where") or "poster", f"{nm}: {im['natural'][0]} px over "
                      f"{im['placed_in'][0]:.1f} in = {ppi:.0f} px/in; blurred in print (export at 300 px/in or as SVG/PDF)")
            elif ppi < 150:
                f.add("WARN", "IMG-RESOLUTION", im.get("where") or "poster", f"{nm}: {ppi:.0f} px/in at the printed size "
                                                                            "(150+ recommended)")
    else:
        f.add("INFO", "NOT-MEASURED", "layout", (err or "layout not measured") + "; overflow and text size were not "
              "checked, figure resolution is estimated from the column width")
        ncols = max(1, len(re.findall(r'^\s*<div class="col" data-col=', r["doc"], re.M)))
        pw_in = page[0] / 25.4
        col_in = (pw_in - 2 * 25 * u / 25.4 - (ncols - 1) * 16 * u / 25.4) / (4 if r["billboard"] else ncols)
        for src in r["images"]:
            fp = os.path.normpath(os.path.join(base, src))
            if not os.path.exists(fp):
                f.add("FAIL", "IMG-MISSING", "poster", f"image not found: {src}")
                continue
            try:
                info = dk.image_info(fp)
            except (ValueError, OSError):
                continue
            ppi = dk.effective_dpi(info, col_in)
            if ppi is not None and ppi < 100:
                f.add("FAIL", "IMG-RESOLUTION", "poster", f"{os.path.basename(src)}: {info['w']} px over about "
                      f"{col_in:.1f} in (a column) = {ppi:.0f} px/in; blurred in print")
            elif ppi is not None and ppi < 150:
                f.add("WARN", "IMG-RESOLUTION", "poster", f"{os.path.basename(src)}: about {ppi:.0f} px/in at column width")
    lim = args.max_size or r["meta"].get("max-size")
    if lim and not dk.placeholders(lim):
        lw, lh = PS.parse_size(lim)
        pw, ph = page[0] / 25.4, page[1] / 25.4
        if pw > lw + 1e-3 or ph > lh + 1e-3:
            f.add("FAIL", "SIZE", "poster", f"{page[0]:.0f} x {page[1]:.0f} mm exceeds the venue limit "
                                            f"{lw * 25.4:.0f} x {lh * 25.4:.0f} mm")
        elif (pw > ph) != (lw > lh) and abs(lw - lh) > 1:
            f.add("FAIL", "ORIENTATION", "poster", "orientation differs from the venue's board")
    dc.check_contrast(f, _pairs_from_vars(r["vars"], r["billboard"]), f"style {name}")
    acc = {k: r["vars"].get(k, "").strip() for k in ("accent", "accent2")}
    dc.check_cvd(f, {k: v for k, v in acc.items() if dk.is_hex(v)}, f"style {name}")
    return {"report": rep, "words": words, "style": name, "page_mm": page, "sources": sources}


def cmd_check(args):
    path = args.spec
    if not path.lower().endswith((".html", ".htm")):
        spec = ss.parse(path)
        work = os.path.join(args.out, ".check-build")
        path, _missing = PH.build(spec, style_for(spec, args), size_for(spec, args), work, args.math)
    f = dc.Findings()
    info = check_html(path, args, f)
    lang = args.lang or ("zh" if dk.has_cjk(PH.read(path)["header"]) else "en")
    rep = info["report"] or {}
    header = [f"Poster: `{args.spec}`", f"Style: {info['style']}; page {info['page_mm'][0]:.0f} x {info['page_mm'][1]:.0f}"
              f" mm; text scale {rep.get('scale', 1):.0%}; body text {rep.get('body_pt', '?')} pt",
              f"Sources: {', '.join(info['sources']) if info['sources'] else 'none'}"]
    md, _js = f.write(args.out, "Poster check" if lang == "en" else "海报检查", header, lang, info | {"report": rep})
    print(f"FAIL {f.count('FAIL')} · WARN {f.count('WARN')} · INFO {f.count('INFO')}; {info['words']} words; "
          f"body {rep.get('body_pt', '?')} pt")
    print("wrote", md)
    return f.exit_code()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("styles")
    a.add_argument("--json", action="store_true")
    sp.add_parser("sizes")
    a = sp.add_parser("init")
    a.add_argument("--template", default="empirical")
    a.add_argument("--size", default="A0")
    a.add_argument("--lang", choices=("en", "zh"), default="en")
    a.add_argument("--out", required=True)
    a.add_argument("--force", action="store_true")

    def common(a):
        a.add_argument("spec")
        a.add_argument("--style")
        a.add_argument("--size")
        a.add_argument("--palette")
        a.add_argument("--font")
        a.add_argument("--math", choices=("auto", "image", "text"), default="auto")
        a.add_argument("--out", required=True)
    a = sp.add_parser("render")
    common(a)
    a.add_argument("--no-preview", action="store_true")
    a.add_argument("--pptx", action="store_true", help="also write an editable PowerPoint built from the spec")
    a.add_argument("--force", action="store_true", help="overwrite an existing poster.html")
    a = sp.add_parser("export")
    a.add_argument("html")
    a.add_argument("--out", help="output folder (default: next to the HTML)")
    a = sp.add_parser("restyle")
    a.add_argument("html")
    a.add_argument("--style", required=True)
    a.add_argument("--palette")
    a.add_argument("--font")
    a.add_argument("--size", help="new page size, e.g. A0-landscape (columns stay as they are)")
    a.add_argument("--out")
    a.add_argument("--in-place", action="store_true")
    a = sp.add_parser("gallery")
    common(a)
    a.add_argument("--styles")
    a = sp.add_parser("check")
    common(a)
    a.add_argument("--source", nargs="*")
    a.add_argument("--ledger")
    a.add_argument("--max-size", help="venue limit, e.g. 841x1189mm or A0")
    a.add_argument("--all-numbers", action="store_true")
    a.add_argument("--lang", choices=("en", "zh"))
    args = ap.parse_args(argv)
    return {"styles": cmd_styles, "sizes": cmd_sizes, "init": cmd_init, "render": cmd_render, "export": cmd_export,
            "restyle": cmd_restyle, "gallery": cmd_gallery, "check": cmd_check}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
