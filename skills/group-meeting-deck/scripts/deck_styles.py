"""Visual styles for group-meeting-deck. A style is a set of design tokens; the content spec never changes
when the style does. See references/styles.md for when to use each one."""
from __future__ import annotations

import sys

SANS = "Arial"
SERIF = "Georgia"
MONO = "Courier New"
EA = "PingFang SC" if sys.platform == "darwin" else "Microsoft YaHei"

BASE = {
    "bg": "#FFFFFF", "fg": "#1F2937", "muted": "#5B6472", "accent": "#1D4ED8", "accent2": "#B45309",
    "title_fg": "#111827", "title_bg": None, "title_rule": None, "title_pt": 30, "title_bold": True,
    "title_align": "l", "body_pt": 22, "min_pt": 18, "font_heading": SANS, "font_body": SANS, "font_mono": MONO,
    "font_ea": EA, "code_bg": "#F3F4F6", "code_fg": "#111827", "table_head_bg": "#1D4ED8", "table_head_fg": "#FFFFFF",
    "table_bg": "#FFFFFF", "table_zebra": "#F3F4F6", "table_border": "#D1D5DB", "footer": "page",
    "footer_bg": None, "footer_fg": "#5B6472", "progress": False, "section_bg": "#1D4ED8", "section_fg": "#FFFFFF",
    "cover": "left-rule", "bullet": "•", "line": 1.12, "max_words": 70, "frame_images": False,
}


def _s(**kw) -> dict:
    d = dict(BASE)
    d.update(kw)
    return d


STYLES: dict[str, dict] = {
    "clean": _s(
        label="Clean academic",
        summary="White background, navy accent bar under each title, sans-serif, page numbers. The safe default.",
        best_for="Weekly progress updates, mixed audiences, any field; prints well as a handout.",
        title_rule="#1D4ED8",
    ),
    "assertion": _s(
        label="Assertion-evidence",
        summary="Each title is a full-sentence claim; the body is the evidence (a figure, a table), with few or no bullets.",
        best_for="Result deep-dives and rehearsals where every slide must make one point the audience remembers.",
        fg="#111111", title_fg="#111111", accent="#9A3412", table_head_bg="#9A3412", title_pt=28, body_pt=22,
        title_rule="#D6D3D1", rule_full=True,
        section_bg="#9A3412", cover="plain", footer="page", max_words=45, assertion=True,
    ),
    "metropolis": _s(
        label="Metropolis",
        summary="Dark teal title bar, orange progress line, flat and quiet; in the spirit of the Beamer metropolis theme.",
        best_for="Mathematics, theory and computer science groups; talks with many formulas; also renders as Beamer.",
        bg="#FAFAFA", fg="#23373B", muted="#4F5D60", accent="#C2410C", title_bg="#23373B", title_fg="#FFFFFF",
        title_pt=26, table_head_bg="#23373B", section_bg="#23373B", section_fg="#FFFFFF", progress=True,
        cover="plain", footer="page", code_bg="#ECEFF0",
    ),
    "campus": _s(
        label="Campus classic",
        summary="Institution-coloured header band, gold divider, three-part footer (presenter, title, date and page).",
        best_for="Formal group meetings, milestone and committee reviews; set palette accent to your university colour.",
        fg="#1A1A1A", muted="#555555", accent="#7A1F2B", accent2="#B8860B", title_bg="#7A1F2B", title_fg="#FFFFFF",
        title_rule="#C9A227", title_pt=26, body_pt=21, font_heading=SERIF, table_head_bg="#7A1F2B",
        section_bg="#7A1F2B", section_fg="#FFFFFF", footer="full", footer_bg="#7A1F2B", footer_fg="#FFFFFF",
        cover="band",
    ),
    "notebook": _s(
        label="Lab notebook",
        summary="Dense and tidy: project strip with date on every slide, small titles, zebra tables, prominent status chips.",
        best_for="Progress reports with many runs, tables and status items; one-to-one meetings with an advisor.",
        fg="#111827", muted="#4B5563", accent="#047857", title_fg="#111827", title_rule="#047857", title_pt=24,
        body_pt=19, table_head_bg="#047857", section_bg="#047857", footer="page", cover="left-rule", strip=True,
        max_words=90,
    ),
    "dark": _s(
        label="Dark mode",
        summary="Deep slate background, cyan and amber accents; white-background figures are framed as cards.",
        best_for="Code, simulations, astronomy and imaging; dim rooms and screen sharing. Avoid for printed handouts.",
        bg="#0F172A", fg="#E2E8F0", muted="#A3B1C6", accent="#38BDF8", accent2="#FBBF24", title_fg="#F8FAFC",
        title_rule="#38BDF8", code_bg="#1E293B", code_fg="#E2E8F0", table_head_bg="#1E3A5F", table_head_fg="#F8FAFC",
        table_bg="#0F172A", table_zebra="#162033", table_border="#334155", footer_fg="#A3B1C6",
        section_bg="#0B1222", section_fg="#F8FAFC", cover="plain", frame_images=True, link="#7DD3FC",
    ),
    "minimal": _s(
        label="Minimal",
        summary="Large type, lots of white space, a single red accent; few words per slide.",
        best_for="Short updates, idea pitches and proposals where you talk and the slide only anchors the point.",
        fg="#000000", muted="#525252", accent="#B91C1C", title_fg="#000000", title_pt=40, body_pt=26,
        title_bold=False,
        table_head_bg="#000000", section_bg="#FFFFFF", section_fg="#000000", footer="page", cover="plain",
        bullet="–", max_words=30,
    ),
}


def get(name: str, palette: dict | None = None, font: str | None = None) -> dict:
    if name not in STYLES:
        raise SystemExit(f"unknown style {name!r}; choose from: {', '.join(STYLES)}")
    st = dict(STYLES[name])
    st["name"] = name
    for k, v in (palette or {}).items():
        st[k] = v
        if k == "accent":            # derived tokens follow the accent unless set explicitly
            for dep in ("table_head_bg",) + (("title_bg", "section_bg", "footer_bg") if st.get("title_bg") else ()):
                if dep not in (palette or {}) and st.get(dep):
                    st[dep] = v
            if not st.get("title_bg") and st.get("section_bg") not in (None, "#FFFFFF", "#0B1222"):
                st["section_bg"] = v
            if st.get("title_rule") and name != "campus":
                st["title_rule"] = v
    if font:
        st["font_body"] = st["font_heading"] = font
    st.setdefault("link", st["accent"])
    return st


def text_pairs(st: dict) -> list[tuple[str, str, str, bool]]:
    """(name, foreground, background, large) pairs that carry text, for contrast checks."""
    pairs = [("body text", st["fg"], st["bg"], False), ("muted text", st["muted"], st["bg"], False),
             ("accent text and links", st["link"], st["bg"], False),
             ("title", st["title_fg"], st.get("title_bg") or st["bg"], True),
             ("table header", st["table_head_fg"], st["table_head_bg"], False),
             ("section slide", st["section_fg"], st["section_bg"], True),
             ("code", st["code_fg"], st["code_bg"], False)]
    if st.get("footer_bg"):
        pairs.append(("footer", st["footer_fg"], st["footer_bg"], False))
    else:
        pairs.append(("footer", st["footer_fg"], st["bg"], False))
    return pairs
