"""pptxwriter.py - write editable PowerPoint (.pptx) files with the standard library only.

Covers what the poster and slide skills need: slides of any size (up to PowerPoint's 56-inch limit),
solid backgrounds, rectangles and rounded rectangles, text boxes with styled runs, bullets, numbering
and hyperlinks, pictures (PNG, JPEG, GIF), tables, and speaker notes. Positions and sizes are given in
inches, font sizes in points, colours as '#RRGGBB'.

    deck = Pptx(13.333, 7.5, fonts={"latin": "Arial", "ea": "Microsoft YaHei"})
    s = deck.slide(bg="#FFFFFF")
    s.text(0.5, 0.4, 12.3, 1.0, [para("A title", size=32, bold=True)])
    s.image("fig.png", 1, 1.5, 6, 4)
    s.notes = "What to say"
    deck.save("talk.pptx")

The files open in PowerPoint, Keynote and LibreOffice. Text is not auto-fitted: callers size boxes from
designkit.wrap_lines estimates and should check a rendered preview.
"""
from __future__ import annotations

import datetime as dt
import os
import re
import zipfile

EMU_IN = 914400
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NSDECL = f'xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}"'
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
XML_HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
_BAD_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")


def emu(inches: float) -> int:
    return int(round(inches * EMU_IN))


def esc(s: str) -> str:
    s = _BAD_XML.sub("", s)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _clr(h: str) -> str:
    return h.lstrip("#").upper()


def run(text: str, **kw) -> dict:
    d = {"text": text}
    d.update(kw)
    return d


def para(text_or_runs, size: float = 18, bold: bool = False, color: str | None = None, align: str = "l",
         bullet: str | None = None, level: int = 0, space_before: float = 0, line: float = 1.1,
         italic: bool = False, font: str | None = None) -> dict:
    """A paragraph. text_or_runs is a string or a list of run dicts (text, bold, italic, color, size, font,
    link, sup, sub, strike). bullet is None, a bullet character, or 'num'."""
    runs = [run(text_or_runs)] if isinstance(text_or_runs, str) else text_or_runs
    for r in runs:
        r.setdefault("size", size)
        r.setdefault("bold", bold)
        r.setdefault("italic", italic)
        if color:
            r.setdefault("color", color)
        if font:
            r.setdefault("font", font)
    return {"runs": runs, "align": align, "bullet": bullet, "level": level, "space_before": space_before,
            "line": line, "size": size}

import html as H


# HTML rendering of paragraph dicts (the HTML twin and text measurement share it)
def runs_html(p: dict) -> str:
    out = []
    for r in p["runs"]:
        st = [f"font-size:{r.get('size', p['size'])}pt"]
        if r.get("bold"):
            st.append("font-weight:700")
        if r.get("italic"):
            st.append("font-style:italic")
        if r.get("color"):
            st.append(f"color:{r['color']}")
        if r.get("font"):
            st.append(f"font-family:'{r['font']}',sans-serif")
        if r.get("highlight"):
            st.append(f"background:{r['highlight']}")
        if r.get("strike"):
            st.append("text-decoration:line-through")
        t = H.escape(r["text"]).replace("\n", "<br>")
        if r.get("sup"):
            t = f"<sup>{t}</sup>"
        if r.get("sub"):
            t = f"<sub>{t}</sub>"
        out.append(f'<span style="{";".join(st)}">{t}</span>')
    return "".join(out)

def paras_html(paras: list[dict]) -> str:
    out = []
    counters: dict[int, int] = {}
    for p in paras:
        if p.get("bullet") == "num":
            counters[p.get("level", 0)] = counters.get(p.get("level", 0), 0) + 1
        else:
            counters.pop(p.get("level", 0), None)
        al = {"l": "left", "c": "center", "ctr": "center", "r": "right", "j": "justify"}.get(p.get("align"), "left")
        size = p.get("size", 18)
        st = [f"text-align:{al}", f"line-height:{p.get('line', 1.1) * 1.17:.2f}",
              f"margin:{p.get('space_before', 0)}pt 0 0 0", f"font-size:{size}pt"]
        b = p.get("bullet")
        lvl = p.get("level", 0)
        pre = ""
        if b:
            ind = size * 1.1
            st += [f"padding-left:{ind * (lvl + 1) * 1.15:.1f}pt", f"text-indent:{-ind:.1f}pt"]
            ch = H.escape(b) if b != "num" else f"{counters.get(lvl, 1)}."
            pre = (f'<span style="display:inline-block;width:{ind:.1f}pt;text-indent:0;'
                   f'color:{p.get("bullet_color") or "inherit"}">{ch}</span>')
        elif lvl:
            st.append(f"padding-left:{size * 1.2 * lvl:.1f}pt")
        out.append(f'<p style="{";".join(st)}">{pre}{runs_html(p)}</p>')
    return "".join(out)



class Slide:
    def __init__(self, deck: "Pptx", bg: str | None):
        self.deck = deck
        self.bg = bg
        self.shapes: list[str] = []
        self.rels: list[tuple[str, str, str, bool]] = []    # (rId, type, target, external)
        self.notes = ""
        self._id = 1
        self.items: list[dict] = []      # the same shapes in neutral form, for the HTML twin

    def _nid(self) -> int:
        self._id += 1
        return self._id

    def _rel(self, typ: str, target: str, external: bool = False) -> str:
        rid = f"rId{len(self.rels) + 2}"                   # rId1 is the layout
        self.rels.append((rid, typ, target, external))
        return rid

    @staticmethod
    def _xfrm(x, y, w, h, tag="a:xfrm") -> str:
        return (f'<{tag}><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{max(emu(w), 1)}" cy="{max(emu(h), 1)}"/>'
                f'</{tag}>')

    @staticmethod
    def _fill(fill: str | None) -> str:
        return f'<a:solidFill><a:srgbClr val="{_clr(fill)}"/></a:solidFill>' if fill else "<a:noFill/>"

    @staticmethod
    def _line(line: str | None, width_pt: float) -> str:
        if not line:
            return "<a:ln><a:noFill/></a:ln>"
        return f'<a:ln w="{int(width_pt * 12700)}"><a:solidFill><a:srgbClr val="{_clr(line)}"/></a:solidFill></a:ln>'

    def _geom(self, radius: float | None, w: float, h: float) -> str:
        if radius:
            adj = int(min(50000, radius / max(min(w, h), 1e-6) * 100000))
            return f'<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val {adj}"/></a:avLst></a:prstGeom>'
        return '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'

    def rect(self, x, y, w, h, fill=None, line=None, line_w=1.0, radius=None, name="Rectangle", geom=None):
        self.items.append({"kind": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill, "line": line,
                           "line_w": line_w, "radius": radius, "geom": geom})
        i = self._nid()
        g = f'<a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>' if geom else self._geom(radius, w, h)
        self.shapes.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{i}" name="{esc(name)} {i}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr>{self._xfrm(x, y, w, h)}{g}{self._fill(fill)}{self._line(line, line_w)}</p:spPr>'
            f'<p:txBody><a:bodyPr rtlCol="0" anchor="ctr"/><a:lstStyle/><a:p><a:endParaRPr lang="en-US" dirty="0"/>'
            f'</a:p></p:txBody></p:sp>')

    def _runs_xml(self, p: dict) -> str:
        out = []
        fonts = self.deck.fonts
        for r in p["runs"]:
            text = r["text"]
            attrs = [f'lang="{"zh-CN" if re.search(r"[一-鿿]", text) else "en-US"}"',
                     f'sz="{int(round(r.get("size", p["size"]) * 100))}"']
            if r.get("bold"):
                attrs.append('b="1"')
            if r.get("italic"):
                attrs.append('i="1"')
            if r.get("strike"):
                attrs.append('strike="sngStrike"')
            if r.get("sup"):
                attrs.append('baseline="30000"')
            if r.get("sub"):
                attrs.append('baseline="-25000"')
            attrs.append('dirty="0"')
            inner = ""
            if r.get("color"):
                inner += f'<a:solidFill><a:srgbClr val="{_clr(r["color"])}"/></a:solidFill>'
            if r.get("highlight"):
                inner += f'<a:highlight><a:srgbClr val="{_clr(r["highlight"])}"/></a:highlight>'
            latin = r.get("font") or fonts.get("latin")
            ea = r.get("font_ea") or fonts.get("ea")
            if latin:
                inner += f'<a:latin typeface="{esc(latin)}"/>'
            if ea:
                inner += f'<a:ea typeface="{esc(ea)}"/>'
            if latin:
                inner += f'<a:cs typeface="{esc(latin)}"/>'
            if r.get("link"):
                rid = self._rel(REL + "/hyperlink", r["link"], external=True)
                inner += f'<a:hlinkClick r:id="{rid}"/>'
            pieces = text.split("\n")
            for j, piece in enumerate(pieces):
                if j:
                    out.append(f'<a:br><a:rPr {" ".join(attrs)}/></a:br>')
                if piece:
                    out.append(f'<a:r><a:rPr {" ".join(attrs)}>{inner}</a:rPr><a:t>{esc(piece)}</a:t></a:r>')
        return "".join(out)

    def _paras_xml(self, paras: list[dict]) -> str:
        out = []
        for p in paras:
            algn = {"l": "l", "c": "ctr", "ctr": "ctr", "r": "r", "j": "just"}.get(p.get("align", "l"), "l")
            lvl = p.get("level", 0)
            size = p.get("size", 18)
            ppr = [f'algn="{algn}"']
            inner = f'<a:lnSpc><a:spcPct val="{int(p.get("line", 1.1) * 100000)}"/></a:lnSpc>'
            if p.get("space_before"):
                inner += f'<a:spcBef><a:spcPts val="{int(p["space_before"] * 100)}"/></a:spcBef>'
            b = p.get("bullet")
            if b:
                ind = int(size * 12700 * 1.1)
                mar = int(ind * (lvl + 1) * 1.15)
                ppr += [f'marL="{mar}"', f'indent="{-ind}"']
                bc = p.get("bullet_color")
                if bc:
                    inner += f'<a:buClr><a:srgbClr val="{_clr(bc)}"/></a:buClr>'
                if b == "num":
                    inner += '<a:buFont typeface="+mj-lt"/><a:buAutoNum type="arabicPeriod"/>'
                else:
                    inner += f'<a:buFont typeface="Arial"/><a:buChar char="{esc(b)}"/>'
            else:
                if lvl:
                    ppr.append(f'marL="{int(size * 12700 * 1.2 * lvl)}"')
                inner += "<a:buNone/>"
            end = f'<a:endParaRPr lang="en-US" sz="{int(size * 100)}" dirty="0"/>'
            out.append(f'<a:p><a:pPr {" ".join(ppr)}>{inner}</a:pPr>{self._runs_xml(p)}{end}</a:p>')
        return "".join(out) or '<a:p><a:endParaRPr lang="en-US" dirty="0"/></a:p>'

    def text(self, x, y, w, h, paras: list[dict], anchor: str = "t", inset: float = 0.05, fill=None, line=None,
             line_w=1.0, radius=None, name="TextBox", shrink: bool = False):
        self.items.append({"kind": "text", "x": x, "y": y, "w": w, "h": h, "paras": paras, "anchor": anchor,
                           "inset": inset, "fill": fill, "line": line, "line_w": line_w, "radius": radius,
                           "name": name})
        i = self._nid()
        ins = emu(inset)
        anc = {"t": "t", "m": "ctr", "c": "ctr", "ctr": "ctr", "b": "b"}.get(anchor, "t")
        fit = "<a:normAutofit/>" if shrink else "<a:noAutofit/>"
        self.shapes.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{i}" name="{esc(name)} {i}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr>{self._xfrm(x, y, w, h)}{self._geom(radius, w, h)}{self._fill(fill)}'
            f'{self._line(line, line_w)}</p:spPr>'
            f'<p:txBody><a:bodyPr wrap="square" lIns="{ins}" tIns="{ins}" rIns="{ins}" bIns="{ins}" anchor="{anc}" '
            f'rtlCol="0">{fit}</a:bodyPr><a:lstStyle/>{self._paras_xml(paras)}</p:txBody></p:sp>')

    def image(self, path: str, x, y, w, h, descr: str = ""):
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        ext = {"jpg": "jpeg"}.get(ext, ext)
        if ext not in ("png", "jpeg", "gif"):
            raise ValueError(f"{path}: PowerPoint pictures must be PNG, JPEG or GIF (convert PDF/SVG first)")
        self.items.append({"kind": "image", "x": x, "y": y, "w": w, "h": h, "path": os.path.abspath(path)})
        name = self.deck._media(path, ext)
        rid = self._rel(REL + "/image", f"../media/{name}")
        i = self._nid()
        self.shapes.append(
            f'<p:pic><p:nvPicPr><p:cNvPr id="{i}" name="Picture {i}" descr="{esc(descr)}"/><p:cNvPicPr>'
            f'<a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
            f'<p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
            f'<p:spPr>{self._xfrm(x, y, w, h)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')

    def table(self, x, y, w, rows: list[list[list[dict]]], row_h: list[float], col_w: list[float] | None = None,
              header_fill="#1F3A68", header_fg="#FFFFFF", fill="#FFFFFF", zebra=None, border="#BFBFBF",
              margin: float = 0.06):
        """rows: list of rows; each cell is a list of paragraph dicts. The first row is the header."""
        ncol = max(len(r) for r in rows)
        col_w = col_w or [w / ncol] * ncol
        self.items.append({"kind": "table", "x": x, "y": y, "w": w, "rows": rows, "row_h": row_h, "col_w": col_w,
                           "header_fill": header_fill, "header_fg": header_fg, "fill": fill, "zebra": zebra,
                           "border": border, "margin": margin})
        i = self._nid()
        grid = "".join(f'<a:gridCol w="{emu(cw)}"/>' for cw in col_w)
        trs = []
        m = emu(margin)
        for ri, r in enumerate(rows):
            tcs = []
            for ci in range(ncol):
                cell = r[ci] if ci < len(r) else [para("")]
                if ri == 0:
                    for p in cell:
                        for rr in p["runs"]:
                            rr["color"] = header_fg
                            rr["bold"] = True
                bg = header_fill if ri == 0 else (zebra if zebra and ri % 2 == 0 else fill)
                ln = "".join(f'<a:{side} w="9525"><a:solidFill><a:srgbClr val="{_clr(border)}"/></a:solidFill>'
                             f'</a:{side}>' for side in ("lnL", "lnR", "lnT", "lnB"))
                tcs.append(f'<a:tc><a:txBody><a:bodyPr/><a:lstStyle/>{self._paras_xml(cell)}</a:txBody>'
                           f'<a:tcPr marL="{m}" marR="{m}" marT="{m}" marB="{m}" anchor="ctr">{ln}'
                           f'{self._fill(bg)}</a:tcPr></a:tc>')
            trs.append(f'<a:tr h="{emu(row_h[ri])}">{"".join(tcs)}</a:tr>')
        self.shapes.append(
            f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{i}" name="Table {i}"/><p:cNvGraphicFramePr>'
            f'<a:graphicFrameLocks noGrp="1"/></p:cNvGraphicFramePr><p:nvPr/></p:nvGraphicFramePr>'
            f'{self._xfrm(x, y, w, sum(row_h), tag="p:xfrm")}<a:graphic>'
            f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table"><a:tbl>'
            f'<a:tblPr firstRow="1" bandRow="1"/><a:tblGrid>{grid}</a:tblGrid>{"".join(trs)}</a:tbl>'
            f'</a:graphicData></a:graphic></p:graphicFrame>')

    def xml(self) -> str:
        bg = (f'<p:bg><p:bgPr><a:solidFill><a:srgbClr val="{_clr(self.bg)}"/></a:solidFill><a:effectLst/></p:bgPr>'
              f'</p:bg>') if self.bg else ""
        return (XML_HEAD + f'<p:sld {NSDECL}><p:cSld>{bg}<p:spTree>{_GRP}{"".join(self.shapes)}</p:spTree></p:cSld>'
                '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>')


_GRP = ('<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm>'
        '<a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm>'
        '</p:grpSpPr>')
_CLRMAP = ('<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" '
           'accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" '
           'folHlink="folHlink"/>')


def _theme(name: str, colours: dict, fonts: dict) -> str:
    c = {"dk1": "000000", "lt1": "FFFFFF", "dk2": "1F2937", "lt2": "F3F4F6", "accent1": "1F3A68",
         "accent2": "C8102E", "accent3": "0072B2", "accent4": "E69F00", "accent5": "009E73", "accent6": "CC79A7",
         "hlink": "0563C1", "folHlink": "954F72"}
    c.update({k: _clr(v) for k, v in colours.items() if v})
    scheme = "".join(f'<a:{k}><a:srgbClr val="{c[k]}"/></a:{k}>' for k in
                     ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6",
                      "hlink", "folHlink"))
    maj = esc(fonts.get("heading") or fonts.get("latin") or "Arial")
    mnr = esc(fonts.get("latin") or "Arial")
    ea = esc(fonts.get("ea") or "")
    fill = '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    ln = '<a:ln w="{w}" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>' \
         '<a:prstDash val="solid"/><a:miter lim="800000"/></a:ln>'
    return (XML_HEAD + f'<a:theme xmlns:a="{NS_A}" name="{esc(name)}"><a:themeElements>'
            f'<a:clrScheme name="{esc(name)}">{scheme}</a:clrScheme>'
            f'<a:fontScheme name="{esc(name)}"><a:majorFont><a:latin typeface="{maj}"/><a:ea typeface="{ea}"/>'
            f'<a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="{mnr}"/><a:ea typeface="{ea}"/>'
            f'<a:cs typeface=""/></a:minorFont></a:fontScheme>'
            f'<a:fmtScheme name="{esc(name)}"><a:fillStyleLst>{fill}{fill}{fill}</a:fillStyleLst>'
            f'<a:lnStyleLst>{ln.format(w=6350)}{ln.format(w=12700)}{ln.format(w=19050)}</a:lnStyleLst>'
            '<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/>'
            '</a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>'
            f'<a:bgFillStyleLst>{fill}{fill}{fill}</a:bgFillStyleLst></a:fmtScheme></a:themeElements>'
            '<a:objectDefaults/><a:extraClrSchemeLst/></a:theme>')


def _lvl_style(size: int) -> str:
    return (f'<a:lvl1pPr marL="0" algn="l" defTabSz="914400" rtl="0" eaLnBrk="1" latinLnBrk="0" hangingPunct="1">'
            f'<a:defRPr sz="{size}" kern="1200"><a:solidFill><a:schemeClr val="tx1"/></a:solidFill>'
            '<a:latin typeface="+mn-lt"/><a:ea typeface="+mn-ea"/><a:cs typeface="+mn-cs"/></a:defRPr></a:lvl1pPr>')


class Pptx:
    MAX_IN = 56.0

    def __init__(self, width_in: float, height_in: float, fonts: dict | None = None, colours: dict | None = None,
                 title: str = "", author: str = ""):
        if not (1 <= width_in <= self.MAX_IN and 1 <= height_in <= self.MAX_IN):
            raise ValueError(f"slide size {width_in:.1f} x {height_in:.1f} in is outside PowerPoint's 1-56 in range")
        self.w, self.h = width_in, height_in
        self.fonts = fonts or {}
        self.colours = colours or {}
        self.title, self.author = title, author
        self.slides: list[Slide] = []
        self.media: dict[str, str] = {}        # abs path -> media name
        self._media_data: list[tuple[str, str]] = []

    def slide(self, bg: str | None = None) -> Slide:
        s = Slide(self, bg)
        self.slides.append(s)
        return s

    def _media(self, path: str, ext: str) -> str:
        ap = os.path.abspath(path)
        if ap not in self.media:
            name = f"image{len(self.media) + 1}.{ext}"
            self.media[ap] = name
            self._media_data.append((ap, name))
        return self.media[ap]

    def save_each(self, outdir: str, stem: str = "slide") -> list[str]:
        """One single-slide .pptx per slide (macOS Quick Look previews only the first slide of a file)."""
        paths = []
        for k, s in enumerate(self.slides, 1):
            sub = Pptx(self.w, self.h, self.fonts, self.colours, self.title, self.author)
            sub.slides = [s]
            sub.media, sub._media_data = self.media, self._media_data
            p = os.path.join(outdir, f"{stem}-{k:03d}.pptx")
            sub.save(p)
            paths.append(p)
        return paths

    def to_html(self, path: str, px_per_in: float = 96.0) -> None:
        """The same geometry as absolutely positioned HTML, one page per slide. Used for previews with
        headless Chrome and for overflow checks: a text box whose content is taller than the box gets
        data-overflow on <body>. Fonts are substituted, so treat it as a layout preview."""
        W, Hh = self.w, self.h

        def box(it):
            return (f"left:{it['x']}in;top:{it['y']}in;width:{it['w']}in;"
                    + (f"height:{it['h']}in;" if "h" in it else ""))
        pages = []
        for k, s in enumerate(self.slides, 1):
            el = []
            for it in s.items:
                if it["kind"] == "rect":
                    br = f"border-radius:{it['radius']}in;" if it.get("radius") else ""
                    if it.get("geom") == "ellipse":
                        br = "border-radius:50%;"
                    bd = f"border:{it['line_w']}pt solid {it['line']};" if it.get("line") else ""
                    el.append(f'<div class="r" style="{box(it)}background:{it.get("fill") or "transparent"};{br}{bd}">'
                              "</div>")
                elif it["kind"] == "text":
                    br = f"border-radius:{it['radius']}in;" if it.get("radius") else ""
                    bd = f"border:{it['line_w']}pt solid {it['line']};" if it.get("line") else ""
                    jc = {"t": "flex-start", "m": "center", "c": "center", "ctr": "center", "b": "flex-end"}.get(
                        it["anchor"], "flex-start")
                    el.append(f'<div class="t" data-name="{H.escape(it.get("name", ""))}" style="{box(it)}'
                              f'background:{it.get("fill") or "transparent"};{br}{bd}padding:{it["inset"]}in;'
                              f'justify-content:{jc}"><div class="in">{paras_html(it["paras"])}</div></div>')
                elif it["kind"] == "image":
                    el.append(f'<img class="r" style="{box(it)}" src="file://{H.escape(it["path"])}">')
                elif it["kind"] == "table":
                    trs = []
                    for ri, row in enumerate(it["rows"]):
                        bg = it["header_fill"] if ri == 0 else (it["zebra"] if it["zebra"] and ri % 2 == 0 else
                                                                it["fill"])
                        tds = "".join(f'<td style="width:{cw}in;background:{bg};border:0.75pt solid {it["border"]};'
                                      f'padding:{it["margin"]}in">{paras_html(cell)}</td>'
                                      for cw, cell in zip(it["col_w"], row))
                        trs.append(f'<tr style="height:{it["row_h"][ri]}in">{tds}</tr>')
                    el.append(f'<table class="r" style="{box(it)}">{"".join(trs)}</table>')
            pages.append(f'<section class="slide" data-n="{k}" style="background:{s.bg or "#FFFFFF"}">'
                         + "".join(el) + "</section>")
        fam = ",".join(f"'{f}'" for f in (self.fonts.get("latin"), self.fonts.get("ea")) if f)
        pages_html = "".join(pages)
        doc = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@page {{ size: {W}in {Hh}in; margin: 0 }}
html, body {{ margin: 0; padding: 0 }}
body {{ font-family: {fam or 'Arial'}, 'Helvetica Neue', Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif; color: #000 }}
.slide {{ position: relative; width: {W}in; height: {Hh}in; overflow: hidden; page-break-after: always }}
.r, .t {{ position: absolute; box-sizing: border-box }}
.t {{ display: flex; flex-direction: column; overflow: hidden }}
.t p {{ margin: 0 }}
table.r {{ border-collapse: collapse; table-layout: fixed }}
</style></head><body>{pages_html}
<script>
window.addEventListener('load', function () {{
  var bad = [];
  document.querySelectorAll('.slide').forEach(function (sl) {{
    sl.querySelectorAll('.t').forEach(function (t) {{
      var inner = t.querySelector('.in');
      if (inner && inner.scrollHeight > t.clientHeight + 2) {{
        bad.push(sl.dataset.n + ':' + (t.dataset.name || 'text') + ':' + Math.round(100 * inner.scrollHeight / t.clientHeight) + '%');
      }}
    }});
  }});
  document.body.setAttribute('data-overflow', bad.join(';'));
}});
</script></body></html>"""
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(doc)

    def save(self, path: str) -> None:
        notes = any(s.notes for s in self.slides)
        n = len(self.slides)
        ct = ['<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
              '<Default Extension="xml" ContentType="application/xml"/>',
              '<Default Extension="png" ContentType="image/png"/>',
              '<Default Extension="jpeg" ContentType="image/jpeg"/>',
              '<Default Extension="gif" ContentType="image/gif"/>']
        pml = "application/vnd.openxmlformats-officedocument.presentationml"
        ov = [("/ppt/presentation.xml", pml + ".presentation.main+xml"),
              ("/ppt/slideMasters/slideMaster1.xml", pml + ".slideMaster+xml"),
              ("/ppt/slideLayouts/slideLayout1.xml", pml + ".slideLayout+xml"),
              ("/ppt/theme/theme1.xml", "application/vnd.openxmlformats-officedocument.theme+xml"),
              ("/ppt/presProps.xml", pml + ".presProps+xml"),
              ("/ppt/viewProps.xml", pml + ".viewProps+xml"),
              ("/ppt/tableStyles.xml", pml + ".tableStyles+xml"),
              ("/docProps/core.xml", "application/vnd.openxmlformats-package.core-properties+xml"),
              ("/docProps/app.xml", "application/vnd.openxmlformats-officedocument.extended-properties+xml")]
        ov += [(f"/ppt/slides/slide{k}.xml", pml + ".slide+xml") for k in range(1, n + 1)]
        if notes:
            ov += [("/ppt/notesMasters/notesMaster1.xml", pml + ".notesMaster+xml"),
                   ("/ppt/theme/theme2.xml", "application/vnd.openxmlformats-officedocument.theme+xml")]
            ov += [(f"/ppt/notesSlides/notesSlide{k}.xml", pml + ".notesSlide+xml")
                   for k, s in enumerate(self.slides, 1) if s.notes]
        ct += [f'<Override PartName="{p}" ContentType="{t}"/>' for p, t in ov]
        files: dict[str, str] = {}
        files["[Content_Types].xml"] = (XML_HEAD + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
                                        f'content-types">{"".join(ct)}</Types>')
        files["_rels/.rels"] = _rels([
            ("rId1", REL + "/officeDocument", "ppt/presentation.xml"),
            ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties",
             "docProps/core.xml"),
            ("rId3", REL + "/extended-properties", "docProps/app.xml")])
        now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        files["docProps/core.xml"] = (
            XML_HEAD + '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/'
            'core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{esc(self.title)}</dc:title><dc:creator>{esc(self.author)}</dc:creator>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>')
        files["docProps/app.xml"] = (
            XML_HEAD + '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
            f'<Application>Science-Skill</Application><Slides>{n}</Slides></Properties>')
        prels = [("rId1", REL + "/slideMaster", "slideMasters/slideMaster1.xml")]
        prels += [(f"rId{k + 1}", REL + "/slide", f"slides/slide{k}.xml") for k in range(1, n + 1)]
        base = n + 2
        prels += [(f"rId{base}", REL + "/presProps", "presProps.xml"),
                  (f"rId{base + 1}", REL + "/viewProps", "viewProps.xml"),
                  (f"rId{base + 2}", REL + "/theme", "theme/theme1.xml"),
                  (f"rId{base + 3}", REL + "/tableStyles", "tableStyles.xml")]
        nm = ""
        if notes:
            prels.append((f"rId{base + 4}", REL + "/notesMaster", "notesMasters/notesMaster1.xml"))
            nm = f'<p:notesMasterIdLst><p:notesMasterId r:id="rId{base + 4}"/></p:notesMasterIdLst>'
        files["ppt/_rels/presentation.xml.rels"] = _rels(prels)
        sld_ids = "".join(f'<p:sldId id="{255 + k}" r:id="rId{k + 1}"/>' for k in range(1, n + 1))
        files["ppt/presentation.xml"] = (
            XML_HEAD + f'<p:presentation {NSDECL} saveSubsetFonts="1"><p:sldMasterIdLst>'
            f'<p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>{nm}<p:sldIdLst>{sld_ids}</p:sldIdLst>'
            f'<p:sldSz cx="{emu(self.w)}" cy="{emu(self.h)}"/><p:notesSz cx="6858000" cy="9144000"/>'
            f'<p:defaultTextStyle>{_lvl_style(1800)}</p:defaultTextStyle></p:presentation>')
        files["ppt/presProps.xml"] = XML_HEAD + f'<p:presentationPr {NSDECL}/>'
        files["ppt/viewProps.xml"] = (XML_HEAD + f'<p:viewPr {NSDECL}><p:normalViewPr><p:restoredLeft sz="15620"/>'
                                      '<p:restoredTop sz="94660"/></p:normalViewPr><p:gridSpacing cx="76200" '
                                      'cy="76200"/></p:viewPr>')
        files["ppt/tableStyles.xml"] = (XML_HEAD + f'<a:tblStyleLst xmlns:a="{NS_A}" '
                                        'def="{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}"/>')
        files["ppt/theme/theme1.xml"] = _theme("Science-Skill", self.colours, self.fonts)
        files["ppt/slideMasters/slideMaster1.xml"] = (
            XML_HEAD + f'<p:sldMaster {NSDECL}><p:cSld><p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/></p:bgRef>'
            f'</p:bg><p:spTree>{_GRP}</p:spTree></p:cSld>{_CLRMAP}<p:sldLayoutIdLst>'
            '<p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst><p:txStyles>'
            f'<p:titleStyle>{_lvl_style(4400)}</p:titleStyle><p:bodyStyle>{_lvl_style(2400)}</p:bodyStyle>'
            f'<p:otherStyle>{_lvl_style(1800)}</p:otherStyle></p:txStyles></p:sldMaster>')
        files["ppt/slideMasters/_rels/slideMaster1.xml.rels"] = _rels([
            ("rId1", REL + "/slideLayout", "../slideLayouts/slideLayout1.xml"),
            ("rId2", REL + "/theme", "../theme/theme1.xml")])
        files["ppt/slideLayouts/slideLayout1.xml"] = (
            XML_HEAD + f'<p:sldLayout {NSDECL} type="blank" preserve="1"><p:cSld name="Blank"><p:spTree>{_GRP}'
            '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>')
        files["ppt/slideLayouts/_rels/slideLayout1.xml.rels"] = _rels([
            ("rId1", REL + "/slideMaster", "../slideMasters/slideMaster1.xml")])
        if notes:
            files["ppt/theme/theme2.xml"] = _theme("Notes", {}, self.fonts)
            files["ppt/notesMasters/notesMaster1.xml"] = _NOTES_MASTER
            files["ppt/notesMasters/_rels/notesMaster1.xml.rels"] = _rels([
                ("rId1", REL + "/theme", "../theme/theme2.xml")])
        for k, s in enumerate(self.slides, 1):
            xml = s.xml()
            rels = [("rId1", REL + "/slideLayout", "../slideLayouts/slideLayout1.xml", False)] + s.rels
            if s.notes:
                rels.append((f"rId{len(rels) + 1}", REL + "/notesSlide", f"../notesSlides/notesSlide{k}.xml", False))
                files[f"ppt/notesSlides/notesSlide{k}.xml"] = _notes_slide(s.notes)
                files[f"ppt/notesSlides/_rels/notesSlide{k}.xml.rels"] = _rels([
                    ("rId1", REL + "/notesMaster", "../notesMasters/notesMaster1.xml"),
                    ("rId2", REL + "/slide", f"../slides/slide{k}.xml")])
            files[f"ppt/slides/slide{k}.xml"] = xml
            files[f"ppt/slides/_rels/slide{k}.xml.rels"] = _rels(rels)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", files.pop("[Content_Types].xml"))
            for name, data in files.items():
                z.writestr(name, data)
            for ap, name in self._media_data:
                z.write(ap, f"ppt/media/{name}")


def measure_heights(boxes: list[tuple[str, float, list[dict]]], fonts: dict, workdir: str) -> dict[str, float] | None:
    """Rendered height in inches of each (key, width_in, paras) text block, measured by headless Chrome
    (None when Chrome is unavailable). Fonts are those of the HTML twin, so allow a few per cent of slack."""
    import json
    import sys
    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
    import designkit
    if not boxes or not designkit.find_chrome():
        return None
    os.makedirs(workdir, exist_ok=True)
    fam = ",".join(f"'{f}'" for f in (fonts.get("latin"), fonts.get("ea")) if f)
    divs = "".join(f'<div class="m" data-k="{H.escape(k)}" style="width:{w}in">{paras_html(ps)}</div>'
                   for k, w, ps in boxes)
    doc = (f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{{margin:0;font-family:{fam or "Arial"},'
           "'Helvetica Neue',Arial,'PingFang SC','Microsoft YaHei',sans-serif}} .m{{position:relative;"
           "box-sizing:border-box}} .m p{{margin:0}}</style></head><body>" + divs +
           "<script>window.addEventListener('load',function(){var o={};document.querySelectorAll('.m')."
           "forEach(function(d){o[d.dataset.k]=d.getBoundingClientRect().height/96;});"
           "document.body.setAttribute('data-h',JSON.stringify(o));});</script></body></html>")
    path = os.path.join(workdir, "measure.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    dom, err = designkit.html_dump_dom(path, wait_ms=2000)
    if err or not dom:
        return None
    m = re.search(r'data-h="([^"]*)"', dom)
    if not m:
        return None
    return json.loads(H.unescape(m.group(1)))


def _rels(items) -> str:
    out = []
    for it in items:
        rid, typ, target = it[0], it[1], it[2]
        ext = len(it) > 3 and it[3]
        mode = ' TargetMode="External"' if ext else ""
        out.append(f'<Relationship Id="{rid}" Type="{typ}" Target="{esc(target)}"{mode}/>')
    return (XML_HEAD + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(out) + "</Relationships>")


_NOTES_MASTER = (
    XML_HEAD + f'<p:notesMaster {NSDECL}><p:cSld><p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/></p:bgRef></p:bg>'
    f'<p:spTree>{_GRP}'
    '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Slide Image Placeholder 1"/><p:cNvSpPr><a:spLocks noGrp="1" noRot="1" '
    'noChangeAspect="1"/></p:cNvSpPr><p:nvPr><p:ph type="sldImg" idx="2"/></p:nvPr></p:nvSpPr><p:spPr><a:xfrm>'
    '<a:off x="381000" y="685800"/><a:ext cx="6096000" cy="3429000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/>'
    '</a:prstGeom><a:noFill/><a:ln w="12700"><a:solidFill><a:prstClr val="black"/></a:solidFill></a:ln></p:spPr>'
    '</p:sp>'
    '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Notes Placeholder 2"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
    '<p:nvPr><p:ph type="body" sz="quarter" idx="3"/></p:nvPr></p:nvSpPr><p:spPr><a:xfrm><a:off x="685800" '
    'y="4343400"/><a:ext cx="5486400" cy="4114800"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
    '</p:spPr><p:txBody><a:bodyPr vert="horz" lIns="91440" tIns="45720" rIns="91440" bIns="45720" rtlCol="0"/>'
    '<a:lstStyle/><a:p><a:endParaRPr lang="en-US"/></a:p></p:txBody></p:sp>'
    f'</p:spTree></p:cSld>{_CLRMAP}<p:notesStyle>{_lvl_style(1200)}</p:notesStyle></p:notesMaster>')


def _notes_slide(text: str) -> str:
    paras = "".join(f'<a:p><a:r><a:rPr lang="en-US" dirty="0"/><a:t>{esc(line)}</a:t></a:r></a:p>' if line else
                    '<a:p><a:endParaRPr lang="en-US" dirty="0"/></a:p>' for line in text.split("\n"))
    return (XML_HEAD + f'<p:notes {NSDECL}><p:cSld><p:spTree>{_GRP}'
            '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Slide Image Placeholder 1"/><p:cNvSpPr><a:spLocks noGrp="1" '
            'noRot="1" noChangeAspect="1"/></p:cNvSpPr><p:nvPr><p:ph type="sldImg"/></p:nvPr></p:nvSpPr><p:spPr/>'
            '</p:sp><p:sp><p:nvSpPr><p:cNvPr id="3" name="Notes Placeholder 2"/><p:cNvSpPr><a:spLocks noGrp="1"/>'
            '</p:cNvSpPr><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/>'
            f'<a:lstStyle/>{paras}</p:txBody></p:sp></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/>'
            '</p:clrMapOvr></p:notes>')


def validate(path: str) -> list[str]:
    """Structural checks: every part parses as XML, every internal relationship target exists, and every
    part has a content type. Returns a list of problems (empty when the package is consistent)."""
    import posixpath
    import xml.etree.ElementTree as ET
    problems = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        ct = ET.fromstring(z.read("[Content_Types].xml"))
        ns = "{http://schemas.openxmlformats.org/package/2006/content-types}"
        defaults = {e.get("Extension") for e in ct.iter(ns + "Default")}
        overrides = {e.get("PartName").lstrip("/") for e in ct.iter(ns + "Override")}
        for n in names:
            if n.endswith("/"):
                continue
            if n.endswith(".xml") or n.endswith(".rels"):
                try:
                    ET.fromstring(z.read(n))
                except ET.ParseError as e:
                    problems.append(f"{n}: XML error {e}")
            if n not in overrides and n.rsplit(".", 1)[-1] not in defaults:
                problems.append(f"{n}: no content type")
        for o in overrides:
            if o not in names:
                problems.append(f"content type for missing part {o}")
        for n in names:
            if not n.endswith(".rels"):
                continue
            base = posixpath.dirname(posixpath.dirname(n))
            for rel in ET.fromstring(z.read(n)):
                if rel.get("TargetMode") == "External":
                    continue
                t = posixpath.normpath(posixpath.join(base, rel.get("Target")))
                if t not in names:
                    problems.append(f"{n}: relationship {rel.get('Id')} points to missing {t}")
    return problems
