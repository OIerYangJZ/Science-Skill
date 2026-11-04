"""slidekit.py - turn slidespec elements into measured, drawable pieces for pptxwriter.

Shared by research-poster and group-meeting-deck. A layout asks for the pieces of a list of elements
at a given width and font size, measures them (headless Chrome when available, otherwise an estimate),
then places them. Every placed image is recorded with its placed width, so the checks can compute the
effective resolution; every display formula is rendered with LaTeX when available, otherwise set as
Unicode text.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import designkit as dk          # noqa: E402
import pptxwriter as px         # noqa: E402
from slidespec import Element, Run, runs_text   # noqa: E402

LINE = 1.1 * 1.17 / 72.0        # inches per point of font size per line (twin line height)

# ---------------------------------------------------------------------------
# LaTeX math to Unicode (fallback when LaTeX is not installed, and for inline math)
# ---------------------------------------------------------------------------
_SYM = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "varepsilon": "ε", "zeta": "ζ",
    "eta": "η", "theta": "θ", "vartheta": "ϑ", "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν",
    "xi": "ξ", "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ", "varphi": "φ",
    "chi": "χ", "psi": "ψ", "omega": "ω", "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ",
    "Pi": "Π", "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω", "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥",
    "neq": "≠", "ne": "≠", "approx": "≈", "sim": "∼", "simeq": "≃", "equiv": "≡", "propto": "∝", "times": "×",
    "cdot": "·", "pm": "±", "mp": "∓", "infty": "∞", "sum": "∑", "prod": "∏", "int": "∫", "oint": "∮",
    "partial": "∂", "nabla": "∇", "in": "∈", "notin": "∉", "subset": "⊂", "subseteq": "⊆", "supset": "⊃",
    "cup": "∪", "cap": "∩", "emptyset": "∅", "forall": "∀", "exists": "∃", "neg": "¬", "land": "∧", "lor": "∨",
    "to": "→", "rightarrow": "→", "Rightarrow": "⇒", "leftarrow": "←", "Leftarrow": "⇐", "leftrightarrow": "↔",
    "Leftrightarrow": "⇔", "mapsto": "↦", "ell": "ℓ", "hbar": "ℏ", "langle": "⟨", "rangle": "⟩", "dagger": "†",
    "otimes": "⊗", "oplus": "⊕", "circ": "∘", "ldots": "…", "cdots": "⋯", "dots": "…", "quad": "  ",
    "qquad": "    ", "lvert": "|", "rvert": "|", "Vert": "‖", "|": "‖", "mid": "|", "log": "log", "ln": "ln",
    "exp": "exp", "sin": "sin", "cos": "cos", "tan": "tan", "min": "min", "max": "max", "lim": "lim",
    "sup": "sup", "inf": "inf", "det": "det", "Pr": "Pr", "deg": "deg", "dim": "dim", "ker": "ker", "star": "⋆",
    "ast": "∗", "perp": "⊥", "parallel": "∥", "angle": "∠", "prime": "′", "lfloor": "⌊", "rfloor": "⌋",
    "lceil": "⌈", "rceil": "⌉", "ll": "≪", "gg": "≫", "sqrt": "√", "Re": "Re", "Im": "Im",
}
_BB = {"R": "ℝ", "N": "ℕ", "Z": "ℤ", "Q": "ℚ", "C": "ℂ", "E": "𝔼", "P": "ℙ", "F": "𝔽", "1": "𝟙"}
_SUP = dict(zip("0123456789+-=()niajkxyt", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱᵃʲᵏˣʸᵗ"))
_SUB = dict(zip("0123456789+-=()aeoxijknmt", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓᵢⱼₖₙₘₜ"))


def tex_to_unicode(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\\(?:text|mathrm|operatorname|textbf|mathbf|boldsymbol|bm|mathit|textit|mathsf)\s*\{([^{}]*)\}",
               r"\1", s)
    s = re.sub(r"\\mathbb\s*\{?(\w)\}?", lambda m: _BB.get(m.group(1), m.group(1)), s)
    s = re.sub(r"\\mathcal\s*\{?(\w)\}?", r"\1", s)
    for _ in range(3):
        s = re.sub(r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", lambda m: f"{_par(m.group(1))}/{_par(m.group(2))}", s)
        s = re.sub(r"\\sqrt\s*\{([^{}]*)\}", lambda m: "√" + _par(m.group(1)), s)
    s = re.sub(r"\\left|\\right|\\big|\\Big|\\bigg|\\Bigg|\\displaystyle|\\limits", "", s)
    s = re.sub(r"\\([A-Za-z]+)", lambda m: _SYM.get(m.group(1), m.group(1)), s)
    s = s.replace("\\{", "{").replace("\\}", "}").replace("\\,", " ").replace("\\;", " ").replace("\\!", "")
    s = s.replace("\\\\", " ").replace("~", " ").replace("&", " ")

    def script(m, table):
        body = m.group(1) if m.group(1) is not None else m.group(2)
        if all(c in table for c in body):
            return "".join(table[c] for c in body)
        return ("^" if table is _SUP else "_") + _par(body)
    s = re.sub(r"\^\{([^{}]*)\}|\^(\S)", lambda m: script(m, _SUP), s)
    s = re.sub(r"_\{([^{}]*)\}|_(\S)", lambda m: script(m, _SUB), s)
    s = s.replace("{", "").replace("}", "")
    return re.sub(r"\s{2,}", " ", s)


def _par(x: str) -> str:
    x = x.strip()
    return x if len(x) <= 1 or re.fullmatch(r"[\w.]+", x) else f"({x})"


# ---------------------------------------------------------------------------
# Context: style tokens, assets, measurement, records for the checks
# ---------------------------------------------------------------------------
class Ctx:
    def __init__(self, theme: dict, workdir: str, spec_path: str = "", math_mode: str = "auto"):
        self.t = theme
        self.workdir = workdir
        self.assets = os.path.join(workdir, "assets")
        os.makedirs(self.assets, exist_ok=True)
        self.spec_path = spec_path
        self.math_mode = math_mode           # auto | image | text
        self.placed: list[dict] = []          # images: path, placed width/height (in), info, where
        self.issues: list[tuple[str, str, str]] = []   # (level, code, message)
        self.fonts = {"latin": theme.get("font_body"), "ea": theme.get("font_ea"), "heading": theme.get("font_heading")}
        self._mcache: dict[str, float] = {}
        self.use_chrome = dk.find_chrome() is not None

    def issue(self, level: str, code: str, where_or_msg: str, msg: str | None = None):
        msg = f"{where_or_msg}: {msg}" if msg else where_or_msg
        if (level, code, msg) not in self.issues:
            self.issues.append((level, code, msg))

    # --- runs and paragraphs -------------------------------------------------
    def runs(self, runs: list[Run], size: float, color: str | None = None, bold: bool = False) -> list[dict]:
        t = self.t
        out = []
        for r in runs:
            d = {"text": r.text, "size": size, "bold": bold or r.bold, "italic": r.italic,
                 "color": color or t["fg"]}
            if r.code:
                d.update(font=t.get("font_mono", "Courier New"), size=size * 0.92)
            if r.math:
                d.update(text=tex_to_unicode(r.text), italic=True, font=t.get("font_math", "Cambria Math"))
            if r.link:
                d.update(link=r.link, color=t.get("link", t["accent"]))
            if r.highlight:
                d.update(color=t.get("highlight_fg", t["accent"]), bold=True)
            out.append(d)
        return out

    def chip(self, status: str, size: float) -> list[dict]:
        bg, fg, label = dk.STATUS.get(status, ("#E8E8E8", "#1A1A1A", status.upper()))
        return [{"text": f"\u2009{label}\u2009", "size": size * 0.72, "bold": True, "color": fg, "highlight": bg},
                {"text": "  ", "size": size}]

    def paras_for(self, e: Element, size: float, color: str | None = None, align: str = "l") -> list[dict]:
        t = self.t
        fg = color or t["fg"]
        if e.kind == "para":
            return [px.para(self.runs(e.runs, size, fg), size=size, align=align, line=t.get("line", 1.1))]
        if e.kind == "quote":
            return [px.para(self.runs(e.runs, size * 1.15, t.get("quote_fg", t["accent"]), bold=True),
                            size=size * 1.15, align=align, line=1.1)]
        if e.kind == "bullets":
            out = []
            for k, (lvl, runs, st, rid, num) in enumerate(e.items):
                s = size * (0.9 if lvl else 1.0)
                rr = (self.chip(st, s) if st else []) + self.runs(runs, s, fg)
                p = px.para(rr, size=s, bullet="num" if num else t.get("bullet", "•"), level=lvl,
                            space_before=size * (0.35 if k else 0) * (0.6 if lvl else 1), line=t.get("line", 1.1))
                p["bullet_color"] = t["accent"]
                out.append(p)
            return out
        if e.kind == "code":
            return [px.para([{"text": ln or " ", "size": size * 0.8, "font": t.get("font_mono", "Courier New"),
                              "color": t.get("code_fg", fg)}], size=size * 0.8, line=1.0)
                    for ln in e.text.split("\n")]
        if e.kind == "math":
            return [px.para([{"text": tex_to_unicode(e.text), "size": size * 1.05, "italic": True,
                              "font": t.get("font_math", "Cambria Math"), "color": fg}], size=size * 1.05, align="c")]
        return []

    # --- measurement -----------------------------------------------------------
    @staticmethod
    def estimate(paras: list[dict], w: float) -> float:
        h = 0.0
        for p in paras:
            size = p.get("size", 18)
            text = "".join(r["text"] for r in p["runs"])
            indent = (size * 1.1 * (p.get("level", 0) + 1) * 1.15 / 72) if p.get("bullet") else 0
            width_em = (w - indent) * 72 / size
            bold = any(r.get("bold") for r in p["runs"])
            lines = sum(dk.wrap_lines(seg, width_em, bold) for seg in (text.split("\n") or [""]))
            h += lines * size * LINE * p.get("line", 1.1) / 1.1 + p.get("space_before", 0) / 72
        return h

    def collect(self):
        """Start collecting measurement requests: measure() answers with estimates and remembers what it
        was asked; flush() then measures everything in one Chrome call. A layout run once while collecting
        and once after flush() costs one browser start instead of one per text block."""
        self._pending: dict = {}

    def flush(self):
        pend = getattr(self, "_pending", None)
        self._pending = None
        if pend:
            self.measure([(ck, w, ps) for ck, (w, ps) in pend.items()])

    def measure(self, reqs: list[tuple[str, float, list[dict]]]) -> dict[str, float]:
        """Heights (in) for (key, width, paras); cached; one Chrome call for all uncached requests."""
        out, todo = {}, []
        for k, w, ps in reqs:
            ck = hashlib.sha1(repr((round(w, 3), ps)).encode()).hexdigest()
            if ck in self._mcache:
                out[k] = self._mcache[ck]
            else:
                todo.append((k, w, ps, ck))
        pend = getattr(self, "_pending", None)
        if todo and pend is not None:
            for k, w, ps, ck in todo:
                pend[ck] = (w, ps)
                out[k] = self.estimate(ps, w) * 1.04
            return out
        if todo:
            got = px.measure_heights([(ck, w, ps) for k, w, ps, ck in todo], self.fonts,
                                     os.path.join(self.workdir, ".measure")) if self.use_chrome else None
            for k, w, ps, ck in todo:
                h = got.get(ck) if got else None
                if h is None:
                    h = self.estimate(ps, w)
                h *= 1.04                      # PowerPoint sets lines slightly looser than Chrome
                self._mcache[ck] = h
                out[k] = h
        return out

    # --- assets ------------------------------------------------------------------
    def image(self, path: str) -> tuple[str | None, dict | None]:
        """A PNG/JPEG/GIF usable by PowerPoint, converting PDF (pdftoppm) and SVG (Chrome) when needed.
        Returns (path, info of the original) or (None, None) with an issue recorded."""
        src = path
        if not os.path.exists(src):
            self.issue("FAIL", "IMG-MISSING", f"image not found: {path}")
            return None, None
        try:
            info = dk.image_info(src)
        except (ValueError, OSError) as e:
            self.issue("FAIL", "IMG-UNREADABLE", str(e))
            return None, None
        if info["kind"] in ("png", "jpeg", "gif"):
            return src, info
        stem = os.path.join(self.assets, hashlib.sha1(os.path.abspath(src).encode()).hexdigest()[:10])
        out = stem + ".png"
        if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
            return out, info
        if info["kind"] == "pdf":
            tool = shutil.which("pdftocairo") or shutil.which("pdftoppm")
            if tool:
                dk._run([tool, "-png", "-r", "300", "-singlefile", "-f", "1", "-l", "1", src, stem])
        elif info["kind"] == "svg" and self.use_chrome:
            w_pt, h_pt = info.get("w_pt") or 600, info.get("h_pt") or 400
            html = stem + ".html"
            with open(html, "w", encoding="utf-8") as fh:
                fh.write(f'<html><head><style>@page{{size:{w_pt}pt {h_pt}pt;margin:0}}body{{margin:0}}</style>'
                         f'</head><body><img src="file://{os.path.abspath(src)}" style="width:{w_pt}pt;'
                         f'height:{h_pt}pt"></body></html>')
            pdf = stem + ".pdf"
            if not dk.html_to_pdf(html, pdf):
                tool = shutil.which("pdftocairo") or shutil.which("pdftoppm")
                if tool:
                    dk._run([tool, "-png", "-r", "300", "-singlefile", pdf, stem])
        if os.path.exists(out):
            return out, info
        self.issue("FAIL", "IMG-CONVERT", f"{path}: could not convert {info['kind'].upper()} to PNG "
                                          "(install poppler for PDF; Chrome for SVG) - export a PNG instead")
        return None, None

    def math_image(self, expr: str, size: float, color: str) -> tuple[str, float, float] | None:
        """(png, width_in, height_in) for a display formula at the given font size, or None."""
        if self.math_mode == "text":
            return None
        key = hashlib.sha1(f"{expr}|{color}".encode()).hexdigest()[:12]
        out = os.path.join(self.assets, f"math-{key}.png")
        if not os.path.exists(out):
            err = dk.tex_math_png(expr, out, display=True, colour=color, dpi=600)
            if err:
                if self.math_mode == "image":
                    self.issue("WARN", "MATH", f"formula set as text ({err})")
                return None
        info = dk.image_info(out)
        scale = size / 10.0            # LaTeX 10 pt base, rendered at 600 dpi
        return out, info["w"] / 600 * scale, info["h"] / 600 * scale


# ---------------------------------------------------------------------------
# Pieces: what a list of elements needs, and how to draw it
# ---------------------------------------------------------------------------
class Piece:
    def __init__(self, kind: str, **kw):
        self.kind = kind
        self.h = 0.0          # fixed height (text, table, math image) or the caption height (image)
        self.flex = 0.0       # natural extra height for images at full width (shrinkable)
        self.__dict__.update(kw)


def pieces(ctx: Ctx, elements: list[Element], w: float, size: float, key: str, color: str | None = None,
           align: str = "l", where: str = "") -> list[Piece]:
    t = ctx.t
    out: list[Piece] = []
    reqs = []
    for n, e in enumerate(elements):
        k = f"{key}.{n}"
        if e.kind in ("para", "bullets", "quote", "code"):
            ps = ctx.paras_for(e, size, color, align)
            inset = 0.12 * size / 18 if e.kind == "code" else 0
            p = Piece("text", paras=ps, key=k, fill=t.get("code_bg") if e.kind == "code" else None, inset=inset,
                      quote=e.kind == "quote")
            reqs.append((k, w - 2 * inset, ps))
            out.append(p)
        elif e.kind == "math":
            m = ctx.math_image(e.text, size * 1.15, color or t["fg"])
            if m:
                png, mw, mh = m
                if mw > w:
                    mh, mw = mh * w / mw, w
                out.append(Piece("mathimg", path=png, mw=mw, mh=mh, h=mh + size * 0.3 / 72))
            else:
                ps = ctx.paras_for(e, size, color)
                reqs.append((k, w, ps))
                out.append(Piece("text", paras=ps, key=k, fill=None, inset=0, quote=False))
        elif e.kind == "image":
            path = ctx.spec_path and _resolve(ctx.spec_path, e.path) or e.path
            png, info = ctx.image(path)
            cap = ctx.runs(e.caption, size * 0.78, t.get("muted", t["fg"])) if e.caption else []
            cps = [px.para(cap, size=size * 0.78, align="c" if t.get("caption_center", True) else "l")] if cap else []
            frac = _width_frac(e.attrs.get("width"))
            ar = dk.aspect(info) if info else 0.6
            p = Piece("image", path=png, src=path, info=info, ar=ar or 0.6, frac=frac, caps=cps, key=k,
                      where=where, label=e.attrs.get("label"))
            if cps:
                reqs.append((k, w, cps))
            out.append(p)
        elif e.kind == "table":
            rows = e.rows
            ncol = max(len(r) for r in rows) if rows else 1
            cw = [w / ncol] * ncol
            cells = []
            for ri, row in enumerate(rows):
                crow = []
                for ci in range(ncol):
                    runs = row[ci] if ci < len(row) else []
                    al = "l" if ci == 0 else "c"
                    crow.append([px.para(ctx.runs(runs, size * 0.85, t["fg"], bold=ri == 0), size=size * 0.85,
                                         align=al, line=1.0)])
                cells.append(crow)
            margin = 0.06 * size / 18
            for ri, crow in enumerate(cells):
                for ci, cps in enumerate(crow):
                    reqs.append((f"{k}.r{ri}c{ci}", cw[ci] - 2 * margin, cps))
            out.append(Piece("table", cells=cells, cw=cw, key=k, margin=margin))
    hs = ctx.measure(reqs)
    for p in out:
        if p.kind == "text":
            p.h = hs[p.key] + 2 * p.inset
        elif p.kind == "image":
            p.h = hs.get(p.key, 0.0) + (size * 0.25 / 72 if p.caps else 0)
            p.flex = w * p.frac * p.ar
        elif p.kind == "table":
            p.row_h = []
            for ri, crow in enumerate(p.cells):
                p.row_h.append(max(hs[f"{p.key}.r{ri}c{ci}"] for ci in range(len(crow))) + 2 * p.margin + 0.02)
            p.h = sum(p.row_h)
    return out


def _resolve(spec_path: str, p: str) -> str:
    if os.path.isabs(p):
        return p
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(spec_path)), p))


def _width_frac(v) -> float:
    if isinstance(v, str) and v.endswith("%"):
        try:
            return max(0.1, min(1.0, float(v[:-1]) / 100))
        except ValueError:
            return 1.0
    return 1.0


def stack_height(ps: list[Piece], gap: float, img_scale: float = 1.0) -> float:
    if not ps:
        return 0.0
    return sum(p.h + p.flex * img_scale for p in ps) + gap * (len(ps) - 1)


def fit_images(ps: list[Piece], avail: float, gap: float) -> float:
    """Scale factor (0..1] for image heights so that the stack fits avail; 0 when even text does not fit."""
    fixed = stack_height(ps, gap, 0.0)
    flex = sum(p.flex for p in ps)
    if fixed > avail + 1e-6:
        return 0.0
    if flex <= 0:
        return 1.0
    return max(0.0, min(1.0, (avail - fixed) / flex))


def draw_stack(ctx: Ctx, slide: px.Slide, ps: list[Piece], x: float, y: float, w: float, gap: float,
               img_scale: float = 1.0, valign_space: float = 0.0, where: str = "") -> float:
    """Draw pieces top to bottom; returns the y after the last piece."""
    t = ctx.t
    cur = y
    for i, p in enumerate(ps):
        if i:
            cur += gap + (valign_space / max(1, len(ps) - 1) if valign_space else 0)
        if p.kind == "text":
            name = "quote" if p.quote else "text"
            slide.text(x, cur, w, p.h, p.paras, inset=p.inset, fill=p.fill, radius=0.06 if p.fill else None,
                       name=f"{where}:{name}")
            cur += p.h
        elif p.kind == "mathimg":
            slide.image(p.path, x + (w - p.mw) / 2, cur + (p.h - p.mh) / 2, p.mw, p.mh, "formula")
            cur += p.h
        elif p.kind == "image":
            ih = p.flex * img_scale
            iw = ih / p.ar if p.ar else w
            iw = min(iw, w)
            ix = x + (w - iw) / 2
            if p.path and ih > 0.05:
                if t.get("frame_images"):          # white card behind figures on dark backgrounds
                    pad = 0.08
                    slide.rect(ix - pad, cur - pad, iw + 2 * pad, ih + 2 * pad, fill="#FFFFFF", radius=0.08)
                slide.image(p.path, ix, cur, iw, ih, descr=os.path.basename(p.src))
                if p.label:
                    slide.text(ix, cur, 0.8, 0.5,
                               [px.para(str(p.label), size=t.get("label_pt", 20), bold=True, color=t["fg"])],
                               name=f"{where}:label")
                ctx.placed.append({"src": p.src, "w_in": iw, "h_in": ih, "info": p.info, "where": where})
            elif not p.path:
                slide.rect(ix, cur, iw, max(ih, 0.3), fill=t.get("panel_bg", "#EEEEEE"), line=t.get("muted"))
                slide.text(ix, cur, iw, max(ih, 0.3), [px.para(f"[[missing figure: {os.path.basename(p.src)}]]",
                                                               size=14, color=t.get("muted"), align="c")],
                           anchor="m", name=f"{where}:missing")
            cur += ih
            if p.caps:
                cur += 0.25 * p.caps[0]["size"] / 72
                slide.text(x, cur, w, p.h - 0.25 * p.caps[0]["size"] / 72, p.caps, name=f"{where}:caption")
                cur += p.h - 0.25 * p.caps[0]["size"] / 72
        elif p.kind == "table":
            slide.table(x, cur, w, p.cells, p.row_h, p.cw, header_fill=t.get("table_head_bg", t["accent"]),
                        header_fg=t.get("table_head_fg", "#FFFFFF"), fill=t.get("table_bg", t.get("bg", "#FFFFFF")),
                        zebra=t.get("table_zebra"), border=t.get("table_border", "#BFBFBF"), margin=p.margin)
            cur += p.h
    return cur


def split_columns(elements: list[Element]) -> list[list[Element]]:
    cols: list[list[Element]] = [[]]
    for e in elements:
        if e.kind == "colbreak":
            cols.append([])
        else:
            cols[-1].append(e)
    return [c for c in cols if c] or [[]]
