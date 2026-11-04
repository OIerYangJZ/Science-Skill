"""Visual styles for research-poster. A style is a set of design tokens; sizes are given for an A0 poster
and scaled with the short side of the actual size. See references/styles.md for when to use each one."""
from __future__ import annotations

import re
import sys

SANS = "Arial"
SERIF = "Georgia"
MONO = "Courier New"
EA = "PingFang SC" if sys.platform == "darwin" else "Microsoft YaHei"

BASE = {
    "layout": "columns", "bg": "#FFFFFF", "fg": "#1A1A1A", "muted": "#555555", "accent": "#1F3A68",
    "accent2": "#C8102E", "link": None, "header_bg": None, "header_fg": "#1A1A1A", "header_sub_fg": "#444444",
    "title_align": "c", "title_pt": 96, "heading_pt": 50, "body_pt": 30, "min_body_pt": 24, "title_bold": True,
    "panel_bg": None, "panel_line": None, "panel_radius": 0.0, "panel_title": "text", "panel_title_bg": None,
    "panel_title_fg": "#1F3A68", "font_heading": SANS, "font_body": SANS, "font_mono": MONO, "font_ea": EA,
    "code_bg": "#F2F2F2", "code_fg": "#1A1A1A", "table_head_bg": "#1F3A68", "table_head_fg": "#FFFFFF",
    "table_bg": "#FFFFFF", "table_zebra": "#F3F4F6", "table_border": "#C8C8C8", "cols_portrait": 3,
    "cols_landscape": 4, "footer_fg": "#555555", "figure_labels": False, "frame_images": False, "line": 1.15,
    "max_words": 800,
}


def _s(**kw) -> dict:
    d = dict(BASE)
    d.update(kw)
    return d


STYLES: dict[str, dict] = {
    "classic": _s(
        label="Classic conference",
        summary="Full-width navy title banner, boxed sections with coloured header bars, three or four columns.",
        best_for="Traditional conference poster sessions, any field; the format most reviewers and judges expect.",
        header_bg="#1F3A68", header_fg="#FFFFFF", header_sub_fg="#DCE3EE", panel_bg="#F4F6FA",
        panel_line="#C9D3E3", panel_radius=0.25, panel_title="bar", panel_title_bg="#1F3A68",
        panel_title_fg="#FFFFFF", font_heading=SERIF,
    ),
    "billboard": _s(
        label="Billboard (#betterposter)",
        summary="One plain-language finding in huge type in a coloured centre column, with the key figure and a QR "
                "code; methods and details in narrow side columns.",
        best_for="Busy poster halls where people decide in seconds whether to stop; results with one clear message.",
        layout="billboard", accent="#0B5D4B", accent2="#F2C14E", header_fg="#1A1A1A", title_align="l",
        title_pt=60, panel_title="text", panel_title_fg="#0B5D4B", table_head_bg="#0B5D4B", center_bg="#0B5D4B",
        center_fg="#FFFFFF", takeaway_pt=118, max_words=500,
    ),
    "minimal": _s(
        label="Minimal grid",
        summary="White space, a strict grid, black type, numbered section headings with a single red-orange rule.",
        best_for="Design-conscious venues (HCI, CS, design, architecture); posters with few, strong figures.",
        accent="#C2410C", title_align="l", title_pt=104, panel_title="rule", panel_title_fg="#111111",
        table_head_bg="#111111", fg="#111111", heading_pt=46,
    ),
    "dark": _s(
        label="Dark",
        summary="Deep slate background, cyan and amber accents, cards for sections; light-background figures framed.",
        best_for="Machine learning, astronomy, imaging and visualisation; screens and digital poster sessions.",
        bg="#0F172A", fg="#E2E8F0", muted="#A3B1C6", accent="#38BDF8", accent2="#FBBF24", header_fg="#F8FAFC",
        header_sub_fg="#CBD5E1", panel_bg="#1E293B", panel_line=None, panel_radius=0.3, panel_title="text",
        panel_title_fg="#7DD3FC", code_bg="#0B1222", code_fg="#E2E8F0", table_head_bg="#1E3A5F",
        table_head_fg="#F8FAFC", table_bg="#1E293B", table_zebra="#24344D", table_border="#334155",
        footer_fg="#A3B1C6", frame_images=True, link="#7DD3FC",
    ),
    "journal": _s(
        label="Journal figure page",
        summary="Editorial look: serif title, thin rules instead of boxes, figure panels labelled a, b, c, muted palette.",
        best_for="Life and physical sciences with dense, multi-panel figures; posters that mirror a paper.",
        accent="#8C1C13", title_align="l", font_heading=SERIF, panel_title="caps", panel_title_fg="#8C1C13",
        table_head_bg="#333333", figure_labels=True, header_sub_fg="#444444",
    ),
    "storyboard": _s(
        label="Storyboard",
        summary="Numbered cards on a warm background that read as a sequence; the numbers guide the eye from step to step.",
        best_for="Method pipelines, interdisciplinary and public audiences, student symposia.",
        bg="#FAF6EF", accent="#5B3E96", accent2="#E07A1F", panel_bg="#FFFFFF", panel_line="#E8DFD0",
        panel_radius=0.4, panel_title="number", panel_title_fg="#5B3E96", table_head_bg="#5B3E96",
        header_fg="#2B2141", header_sub_fg="#4A4060",
    ),
}

MM = 25.4
SIZES = {"A0": (841, 1189), "A1": (594, 841), "A2": (420, 594), "A3": (297, 420),
         "B1": (707, 1000), "48x36in": (48 * MM, 36 * MM), "42x36in": (42 * MM, 36 * MM),
         "36x48in": (36 * MM, 48 * MM), "36x24in": (36 * MM, 24 * MM)}


def parse_size(s: str) -> tuple[float, float]:
    """'A0' (portrait), 'A0-landscape', '48x36in', '900x1200mm' -> (width_in, height_in)."""
    s = (s or "A0").strip()
    land = bool(re.search(r"[-_ ]?(landscape|横)", s, re.I))
    s = re.sub(r"[-_ ]?(landscape|portrait|横|竖)", "", s, flags=re.I)
    if s.upper() in SIZES:
        w, h = SIZES[s.upper()]
        if land:
            w, h = max(w, h), min(w, h)
        return w / MM, h / MM
    if s in SIZES:
        w, h = SIZES[s]
        return w / MM, h / MM
    m = re.fullmatch(r"([\d.]+)\s*[x×]\s*([\d.]+)\s*(mm|cm|in)", s, re.I)
    if not m:
        raise SystemExit(f"unknown poster size {s!r}; use A0, A1, A0-landscape, 48x36in, 900x1200mm ...")
    f = {"mm": 1 / MM, "cm": 10 / MM, "in": 1.0}[m.group(3).lower()]
    return float(m.group(1)) * f, float(m.group(2)) * f


def get(name: str, palette: dict | None = None, font: str | None = None) -> dict:
    if name not in STYLES:
        raise SystemExit(f"unknown style {name!r}; choose from: {', '.join(STYLES)}")
    st = dict(STYLES[name])
    st["name"] = name
    pal = palette or {}
    for k, v in pal.items():
        st[k] = v
    if "accent" in pal:                 # tokens derived from the accent follow it unless set explicitly
        deps = ["table_head_bg", "center_bg"] + (["panel_title_fg"] if st["panel_title"] != "bar" else [])
        if st.get("header_bg"):
            deps += ["header_bg", "panel_title_bg"]
        for dep in deps:
            if dep not in pal and st.get(dep):
                st[dep] = pal["accent"]
    if font:
        st["font_body"] = st["font_heading"] = font
    st["link"] = st.get("link") or st["accent"]
    return st


def text_pairs(st: dict) -> list[tuple[str, str, str, bool]]:
    """(name, foreground, background, large) pairs that carry text, for contrast checks."""
    panel = st.get("panel_bg") or st["bg"]
    pairs = [("body text", st["fg"], panel, False), ("muted text and captions", st["muted"], panel, False),
             ("links", st["link"], panel, False),
             ("title", st["header_fg"], st.get("header_bg") or st["bg"], True),
             ("authors and affiliations", st["header_sub_fg"], st.get("header_bg") or st["bg"], False),
             ("section headings", st["panel_title_fg"], st.get("panel_title_bg") or panel, True),
             ("table header", st["table_head_fg"], st["table_head_bg"], False),
             ("footer", st["footer_fg"], st["bg"], False)]
    if st.get("center_bg"):
        pairs.append(("takeaway", st["center_fg"], st["center_bg"], True))
        pairs.append(("takeaway highlight", st["accent2"], st["center_bg"], True))
    return pairs
