"""designkit.py - measurements shared by the poster and slide skills.

Standard library only. Everything here measures or traces; nothing decides what a poster or a talk
should say.

- colours: WCAG contrast ratios, colour-vision-deficiency simulation (Machado et al. 2009, severity 1)
  and CIELAB distances, so a style can be checked for legibility and for colours that collapse;
- images: pixel or physical size of PNG, JPEG, GIF, SVG and PDF files, for effective resolution at the
  printed or projected size;
- text: word counts that treat CJK characters as words, and a width estimate used for layout;
- numbers: every number on a poster or slide, traced to the author's source (exact, rounded, or not
  found);
- claims: strength words added and qualifiers dropped relative to the closest source sentence;
- ledgers: result and route statuses from a dead-end-ledger file;
- tools: optional Chrome, LibreOffice, pdftoppm and LaTeX for previews (never required).
"""
from __future__ import annotations

import glob
import math
import os
import re
import shutil
import struct
import subprocess
import zlib

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
HEX_RX = re.compile(r"^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")


def hex_rgb(h: str) -> tuple[int, int, int]:
    m = HEX_RX.match(h.strip())
    if not m:
        raise ValueError(f"not a hex colour: {h!r}")
    s = m.group(1)
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def rgb_hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c))):02X}" for c in rgb)


def is_hex(h) -> bool:
    return isinstance(h, str) and bool(HEX_RX.match(h.strip()))


def _lin(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _unlin(c: float) -> float:
    c = max(0.0, min(1.0, c))
    return 255.0 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)


def luminance(h: str) -> float:
    r, g, b = (_lin(c) for c in hex_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """WCAG 2.x contrast ratio, 1..21."""
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def mix(a: str, b: str, t: float) -> str:
    """Linear blend in sRGB: t=0 gives a, t=1 gives b."""
    ra, rb = hex_rgb(a), hex_rgb(b)
    return rgb_hex(tuple(x + (y - x) * t for x, y in zip(ra, rb)))


# Machado, Oliveira & Fernandes (2009), severity 1.0, applied to linear RGB.
CVD = {
    "protan": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "deutan": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "tritan": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}


def simulate(h: str, kind: str) -> str:
    lin = [_lin(c) for c in hex_rgb(h)]
    m = CVD[kind]
    out = [sum(m[i][j] * lin[j] for j in range(3)) for i in range(3)]
    return rgb_hex(_unlin(c) for c in out)


def _lab(h: str) -> tuple[float, float, float]:
    r, g, b = (_lin(c) for c in hex_rgb(h))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a: str, b: str) -> float:
    """CIE76 distance in CIELAB; below about 10 two marks are hard to tell apart at a glance."""
    la, lb = _lab(a), _lab(b)
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(la, lb)))


def palette_report(colours: dict[str, str], min_de: float = 12.0) -> list[tuple[str, str, str, float]]:
    """Pairs of named colours that become hard to distinguish under a colour-vision deficiency.
    Returns (kind, name_a, name_b, deltaE) for every pair below min_de (normal vision included)."""
    names = sorted(colours)
    bad = []
    for kind in ("normal", "protan", "deutan", "tritan"):
        sim = {n: colours[n] if kind == "normal" else simulate(colours[n], kind) for n in names}
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                d = delta_e(sim[a], sim[b])
                if d < min_de:
                    bad.append((kind, a, b, round(d, 1)))
    return bad


# Status chips used by the slide and poster skills. The vocabulary follows dead-end-ledger.
# Colours are from the Okabe-Ito palette; every chip carries its word, so colour is never the only cue.
STATUS = {
    "verified":    ("#0072B2", "#FFFFFF", "VERIFIED"),
    "done":        ("#0072B2", "#FFFFFF", "DONE"),
    "succeeded":   ("#0072B2", "#FFFFFF", "SUCCEEDED"),
    "unverified":  ("#E8E8E8", "#1A1A1A", "UNVERIFIED"),
    "conditional": ("#CC79A7", "#1A1A1A", "CONDITIONAL"),
    "preliminary": ("#E69F00", "#1A1A1A", "PRELIMINARY"),
    "in-progress": ("#F0E442", "#1A1A1A", "IN PROGRESS"),
    "partial":     ("#F0E442", "#1A1A1A", "PARTIAL"),
    "inconclusive": ("#E8E8E8", "#1A1A1A", "INCONCLUSIVE"),
    "negative":    ("#D55E00", "#FFFFFF", "NEGATIVE"),
    "failed":      ("#D55E00", "#FFFFFF", "FAILED"),
    "blocked":     ("#7F3C8D", "#FFFFFF", "BLOCKED"),
    "planned":     ("#FFFFFF", "#1A1A1A", "PLANNED"),
    "dropped":     ("#9E9E9E", "#1A1A1A", "DROPPED"),
    "retracted":   ("#000000", "#FFFFFF", "RETRACTED"),
}
# Strength order for the ledger check: a chip may not claim more than the ledger records.
STATUS_RANK = {"retracted": 0, "negative": 0, "failed": 0, "dropped": 0, "blocked": 0, "planned": 0,
               "inconclusive": 1, "unverified": 2, "preliminary": 1, "in-progress": 1, "partial": 1,
               "conditional": 2, "verified": 3, "done": 3, "succeeded": 3}
# Ledger statuses mapped to the chip vocabulary.
LEDGER_TO_CHIP = {"VERIFIED": "verified", "PROVED-REVIEWED": "verified", "UNVERIFIED": "unverified",
                  "PROVED-UNREVIEWED": "unverified", "CONDITIONAL": "conditional", "PRELIMINARY": "preliminary",
                  "HEURISTIC": "preliminary", "NEGATIVE": "negative", "RETRACTED": "retracted",
                  "FAILED": "failed", "BLOCKED": "blocked", "INCONCLUSIVE": "inconclusive", "PARTIAL": "partial",
                  "SUPERSEDED": "dropped", "IN-PROGRESS": "in-progress", "SUCCEEDED": "succeeded",
                  "OPEN": "planned"}

# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------
PT_PER_IN = 72.0
MM_PER_IN = 25.4


def image_info(path: str) -> dict:
    """{'kind', 'w', 'h', 'vector', 'w_pt', 'h_pt'}: pixel size for raster images, point size for vector
    ones (None when unknown). Raises ValueError for unreadable files."""
    with open(path, "rb") as fh:
        head = fh.read(65536)
    info = {"kind": None, "w": None, "h": None, "vector": False, "w_pt": None, "h_pt": None}
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", head[16:24])
        info.update(kind="png", w=w, h=h)
        return info
    if head[:6] in (b"GIF87a", b"GIF89a"):
        w, h = struct.unpack("<HH", head[6:10])
        info.update(kind="gif", w=w, h=h)
        return info
    if head[:2] == b"\xff\xd8":
        with open(path, "rb") as fh:
            data = fh.read()
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            seg = struct.unpack(">H", data[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                info.update(kind="jpeg", w=w, h=h)
                return info
            i += 2 + seg
        raise ValueError(f"{path}: JPEG without a frame header")
    if head[:4] == b"%PDF":
        with open(path, "rb") as fh:
            data = fh.read()
        m = re.search(rb"/(?:CropBox|MediaBox)\s*\[\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\]", data)
        info.update(kind="pdf", vector=True)
        if m:
            x0, y0, x1, y1 = (float(v) for v in m.groups())
            info.update(w_pt=abs(x1 - x0), h_pt=abs(y1 - y0))
        return info
    text = head.decode("utf-8", "replace")
    if "<svg" in text:
        info.update(kind="svg", vector=True)
        tag = re.search(r"<svg\b[^>]*>", text, re.S)
        tag = tag.group(0) if tag else ""

        def dim(name):
            m = re.search(name + r'\s*=\s*["\']\s*([\d.]+)\s*(px|pt|mm|cm|in)?\s*["\']', tag)
            if not m:
                return None
            v, unit = float(m.group(1)), m.group(2) or "px"
            return v * {"px": 0.75, "pt": 1.0, "mm": PT_PER_IN / MM_PER_IN, "cm": PT_PER_IN / 2.54,
                        "in": PT_PER_IN}[unit]
        w, h = dim("width"), dim("height")
        vb = re.search(r'viewBox\s*=\s*["\']\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)', tag)
        if (w is None or h is None) and vb:
            w, h = float(vb.group(1)) * 0.75, float(vb.group(2)) * 0.75
        info.update(w_pt=w, h_pt=h)
        return info
    raise ValueError(f"{path}: not a PNG, JPEG, GIF, SVG or PDF file")


def aspect(info: dict) -> float | None:
    """Height / width, or None if unknown."""
    if info.get("w") and info.get("h"):
        return info["h"] / info["w"]
    if info.get("w_pt") and info.get("h_pt"):
        return info["h_pt"] / info["w_pt"]
    return None


def effective_dpi(info: dict, placed_width_in: float) -> float | None:
    """Pixels per inch at the placed width; None for vector images."""
    if info.get("vector") or not info.get("w") or placed_width_in <= 0:
        return None
    return info["w"] / placed_width_in


def write_png(path: str, w: int, h: int, rgb=(200, 200, 200)) -> None:
    """A flat-colour PNG (used for placeholders and test fixtures)."""
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(data)


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------
CJK_RX = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]")
LATIN_WORD_RX = re.compile(r"[A-Za-z0-9\u00C0-\u024F][A-Za-z0-9\u00C0-\u024F'’\-.,%]*")


def has_cjk(text: str) -> bool:
    return bool(CJK_RX.search(text))


def word_count(text: str) -> int:
    """Latin words plus CJK characters (a CJK character is counted as one word)."""
    cjk = len(CJK_RX.findall(text))
    return cjk + len(LATIN_WORD_RX.findall(CJK_RX.sub(" ", text)))


def speaking_seconds(text: str, wpm: float = 130.0, cpm: float = 250.0) -> float:
    """Seconds to say the text aloud: Latin words at wpm, CJK characters at cpm."""
    cjk = len(CJK_RX.findall(text))
    latin = len(LATIN_WORD_RX.findall(CJK_RX.sub(" ", text)))
    return 60.0 * (latin / wpm + cjk / cpm)


def text_width_em(text: str, bold: bool = False) -> float:
    """Approximate rendered width in em for a proportional sans font."""
    w = 0.0
    for ch in text:
        if CJK_RX.match(ch) or ord(ch) > 0x2E80:
            w += 1.0
        elif ch == " ":
            w += 0.28
        elif ch.isupper():
            w += 0.64
        elif ch.isdigit():
            w += 0.56
        elif ch in "ilj.,;:'!|()[]{}":
            w += 0.28
        elif ch in "mwMW":
            w += 0.82
        else:
            w += 0.52
    return w * (1.06 if bold else 1.0)


def wrap_lines(text: str, width_em: float, bold: bool = False) -> int:
    """Number of lines needed to set the text in a box width_em wide (greedy, word-based; CJK breaks anywhere)."""
    if width_em <= 0:
        return 1
    lines, cur = 1, 0.0
    tokens = re.findall(r"[\u2E80-\uFFFF]|\S+\s*", text)
    for tok in tokens:
        w = text_width_em(tok, bold)
        if cur + w > width_em and cur > 0:
            lines += 1
            cur = w
            while cur > width_em:      # a token longer than the line
                lines += 1
                cur -= width_em
        else:
            cur += w
    return lines


# ---------------------------------------------------------------------------
# Numbers: trace every number on a poster or slide to the author's source
# ---------------------------------------------------------------------------
NUM_RX = re.compile(r"(?<![\w.])[-−–]?\d{1,3}(?:[,\u202f\u00a0 ]\d{3})+(?:\.\d+)?(?![\w])|(?<![\w.])[-−–]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w])")
# Numbers that are labels, not results: "Fig. 2", "Eq. (3)", "Table 1", "Section 4", "R2", "[12]", years
LABEL_RX = re.compile(r"(?:\b(?:Fig(?:ure)?s?|Eqs?|Equations?|Tables?|Tab|Sec(?:tion)?s?|Lemma|Theorem|Thm|"
                      r"Prop(?:osition)?|Cor(?:ollary)?|Def(?:inition)?|Step|Slide|Panel|Part|Chapter|Ch|Ref|"
                      r"Appendix|App|Algorithm|Alg|Week|Day|Phase|v|ver(?:sion)?|No)\.?\s*\(?$|"
                      r"图|表|式|第|章节?|节|定理|引理|命题)", re.I)


def _norm_num(tok: str) -> str:
    return re.sub(r"[,\u202f\u00a0 ]", "", tok).replace("−", "-").replace("–", "-")


def numbers_in(text: str, include_small: bool = False) -> list[tuple[str, float, int, str]]:
    """(token, value, offset, context) for every number that looks like a result. Labels (Fig. 2, Eq. 3,
    [12], R2), years 1900-2100 and, unless include_small, integers 0-10 are skipped."""
    out = []
    for m in NUM_RX.finditer(text):
        tok = m.group(0)
        a = m.start()
        before = text[max(0, a - 14):a]
        after = text[m.end():m.end() + 2]
        if LABEL_RX.search(before) or before.endswith("[") and after.startswith("]"):
            continue
        if a > 0 and text[a - 1] in "#§":
            continue
        if re.search(r"[A-Za-z]$", before) and not re.search(r"[A-Za-z]{2,}\s$", before):
            continue                    # identifiers such as R2, T1, H2O, x3
        s = _norm_num(tok)
        try:
            v = float(s)
        except ValueError:
            continue
        frac = "." in s or "e" in s.lower()
        pct = after.strip().startswith("%")
        if not frac and not pct and 1900 <= v <= 2100:
            continue
        if not include_small and not frac and not pct and 0 <= abs(v) <= 10:
            continue
        ctx = text[max(0, a - 40):m.end() + 40].replace("\n", " ")
        out.append((tok, v, a, ctx))
    return out


def _decimals(tok: str) -> int:
    s = _norm_num(tok)
    if "e" in s.lower():
        return -1
    return len(s.split(".")[1]) if "." in s else 0


def trace_numbers(deck_text: str, source_text: str, include_small: bool = False) -> list[dict]:
    """Each number in deck_text with status:
    EXACT      the same token occurs in the source;
    ROUNDED    a source number rounds to it (the source number is given);
    SCALED     it matches a source number times 100 or divided by 100 (percent vs fraction);
    NOT-IN-SOURCE  none of the above (a number the source does not contain, or a drifted one)."""
    src = numbers_in(source_text, include_small=True)
    src_tokens = {_norm_num(t) for t, *_ in src}
    src_vals = [(t, v) for t, v, *_ in src]
    rows = []
    for tok, v, off, ctx in numbers_in(deck_text, include_small):
        s = _norm_num(tok)
        st, match = "NOT-IN-SOURCE", ""
        if s in src_tokens or s.lstrip("-") in src_tokens:
            st, match = "EXACT", tok
        else:
            d = _decimals(tok)
            for t, sv in src_vals:
                if d >= 0 and _decimals(t) > d and abs(round(abs(sv), d) - abs(v)) < 10 ** (-d) / 2 * 1.0001 and \
                        f"{round(abs(sv), d):.{d}f}" == f"{abs(v):.{d}f}":
                    st, match = "ROUNDED", t
                    break
            if st == "NOT-IN-SOURCE":
                for t, sv in src_vals:
                    if sv and (abs(sv * 100 - v) < 1e-9 * max(1, abs(v)) or abs(sv / 100 - v) < 1e-12):
                        st, match = "SCALED", t
                        break
        rows.append({"number": tok, "status": st, "source_match": match, "context": ctx.strip(), "offset": off})
    return rows


# ---------------------------------------------------------------------------
# Claims: strength words added, qualifiers dropped
# ---------------------------------------------------------------------------
STRENGTH_RX = re.compile(r"\b(first|novel|unprecedented|breakthrough|revolution\w*|significant(?:ly)?|"
                         r"prove[sdn]?|proof|optimal(?:ly)?|tight|state[- ]of[- ]the[- ]art|SOTA|outperform\w*|"
                         r"best|superior|universal(?:ly)?|always|never|guarantee[sd]?|solve[sd]?|dramatic(?:ally)?|"
                         r"substantial(?:ly)?|cause[sd]?|demonstrate[sd]?|establish(?:es|ed)?|confirm[sed]*|"
                         r"universally|exact(?:ly)?|robust(?:ly)?|definitive(?:ly)?|clearly)\b|"
                         r"首次|首个|突破|显著|证明|最优|最佳|普适|总是|保证|解决|确立|证实", re.I)
QUALIFIER_RX = re.compile(r"\b(may|might|could|suggests?|preliminary|pilot|appears?|possibly|likely|"
                          r"conditional(?:ly)?|assum\w+|under|if|unless|provided|conjecture\w*|heuristic\w*|"
                          r"in (?:mice|vitro|silico|simulation)|simulated|for (?:n|small|large|d)\b|"
                          r"up to|at most|at least|approximately|about|roughly|associated|correlat\w+|"
                          r"subset|sample|only|except|within)\b|"
                          r"可能|初步|假设|条件|猜想|在.{0,6}下|仅|约|至多|至少|相关", re.I)
TOKEN_RX = re.compile(r"[A-Za-z][A-Za-z\-]{2,}|[\u4e00-\u9fff]")
STOP = set("the and for with that this from are was were have has had been our their its into than then "
           "which when where while also can not but use using used each per via such these those both".split())


def _content_tokens(s: str) -> set[str]:
    return {t.lower() for t in TOKEN_RX.findall(s)} - STOP


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。！？；;])\s+|\n{2,}|\n(?=\s*[-*•]\s)", text)
    return [p.strip(" -*•\t\n") for p in parts if len(p.strip()) > 12]


def claim_drift(deck_text: str, source_text: str, min_overlap: float = 0.25) -> list[dict]:
    """For each deck sentence, the closest source sentence (token Jaccard) and the strength words it adds
    and the qualifiers it drops. Leads only: read both sentences before calling anything a problem."""
    src = [(s, _content_tokens(s)) for s in split_sentences(source_text)]
    rows = []
    for d in split_sentences(deck_text):
        dt = _content_tokens(d)
        if len(dt) < 3:
            continue
        best, score = None, 0.0
        for s, st in src:
            if not st:
                continue
            j = len(dt & st) / len(dt | st)
            if j > score:
                best, score = s, j
        added = sorted({m.group(0).lower() for m in STRENGTH_RX.finditer(d)})
        dropped = []
        if best is not None and score >= min_overlap:
            src_strong = {m.group(0).lower() for m in STRENGTH_RX.finditer(best)}
            added = [w for w in added if w not in src_strong]
            deck_q = {m.group(0).lower() for m in QUALIFIER_RX.finditer(d)}
            dropped = sorted({m.group(0).lower() for m in QUALIFIER_RX.finditer(best)} - deck_q)
        rows.append({"deck": d, "source": best if score >= min_overlap else None, "overlap": round(score, 2),
                     "added_strength": added, "dropped_qualifiers": dropped})
    return rows


# ---------------------------------------------------------------------------
# Placeholders
# ---------------------------------------------------------------------------
PLACEHOLDER_RX = re.compile(r"\[\[[^\]]*\]\]|\bTODO\b|\bTBD\b|\bFIXME\b|\bXX+\b|\?\?+|lorem ipsum|待补|待定", re.I)


def placeholders(text: str) -> list[str]:
    return [m.group(0) for m in PLACEHOLDER_RX.finditer(text)]


# ---------------------------------------------------------------------------
# dead-end-ledger statuses
# ---------------------------------------------------------------------------
def ledger_rows(path: str) -> list[dict]:
    """Rows of every Markdown table in a ledger that has an ID column, as {lower-case header: cell} plus
    '_status' (the first upper-case word of Status or Outcome) and '_line' (the row as written)."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    header = None
    for line in lines:
        if not line.strip().startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if all(set(c) <= set("-: ") for c in cells) or "id" not in header:
            continue
        row = {h: (cells[i] if i < len(cells) else "") for i, h in enumerate(header)}
        col = next((k for k in ("status", "outcome") if k in header), None)
        word = re.match(r"[A-Z][A-Z\-]*", row.get(col, "").upper()) if col else None
        row["_status"] = word.group(0) if word else ""
        row["_line"] = line.strip()
        if row.get("id"):
            rows.append(row)
    return rows


def ledger_statuses(path: str) -> dict[str, tuple[str, str]]:
    """{ID: (status word, row text)} from every ledger table with ID and Status (or Outcome) columns."""
    return {r["id"]: (r["_status"], r["_line"]) for r in ledger_rows(path) if r["_status"]}


# ---------------------------------------------------------------------------
# Optional tools for previews (never required)
# ---------------------------------------------------------------------------
def find_chrome() -> str | None:
    """Headless Chrome/Chromium/Edge, or None. SCIENCE_SKILL_NO_CHROME=1 disables it (tests, CI)."""
    if os.environ.get("SCIENCE_SKILL_NO_CHROME"):
        return None
    env = os.environ.get("SCIENCE_SKILL_CHROME")
    if env and os.path.exists(env):
        return env
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium",
              "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"):
        if os.path.exists(p):
            return p
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"):
        p = shutil.which(name)
        if p:
            return p
    return None


_SOFFICE: list = []


FONT_FILES = {"CMU Sans Serif": ("cmunss", "cmunsx"), "CMU Serif": ("cmunrm",),
              "Latin Modern Sans": ("lmsans10",)}
FONT_DIRS = ("~/Library/Fonts", "/Library/Fonts", "/System/Library/Fonts", "~/.fonts", "~/.local/share/fonts",
             "/usr/share/fonts", "/usr/local/share/fonts", "C:/Windows/Fonts",
             os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft/Windows/Fonts"))


def font_installed(family: str) -> bool:
    """Whether a font family listed in FONT_FILES is installed as a system font (by file name)."""
    stems = FONT_FILES.get(family)
    if not stems:
        return False
    for d in FONT_DIRS:
        d = os.path.expanduser(d)
        if not os.path.isdir(d):
            continue
        for _root, _dirs, files in os.walk(d):
            if any(f.lower().startswith(stems) and f.lower().endswith((".otf", ".ttf")) for f in files):
                return True
    return False


def find_soffice() -> str | None:
    """A LibreOffice binary that actually runs (package-manager wrappers can outlive the app)."""
    if _SOFFICE:
        return _SOFFICE[0]
    found = None
    cands = [shutil.which(n) for n in ("soffice", "libreoffice")]
    cands.append("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    for p in cands:
        if p and os.path.exists(p):
            try:
                if _run([p, "--version"], timeout=60).returncode == 0:
                    found = p
                    break
            except (OSError, subprocess.TimeoutExpired):
                continue
    _SOFFICE.append(found)
    return found


def quicklook_png(paths: list[str], outdir: str, width_px: int = 1600) -> tuple[list[str], str | None]:
    """macOS Quick Look thumbnails (first page of each file; uses the system's Office renderer)."""
    ql = shutil.which("qlmanage")
    if not ql:
        return [], "qlmanage (macOS Quick Look) not found"
    p = _run([ql, "-t", "-s", str(width_px), "-o", outdir, *paths], timeout=300)
    files = [os.path.join(outdir, os.path.basename(x) + ".png") for x in paths]
    files = [f for f in files if os.path.exists(f)]
    return files, (None if files else f"Quick Look failed: {(p.stderr or p.stdout)[-300:]}")


def _run(cmd: list[str], timeout: int = 180, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)


def _chrome_flags(profile: str) -> list[str]:
    return ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
            "--hide-scrollbars", f"--user-data-dir={profile}", "--allow-file-access-from-files"]


def html_to_pdf(html: str, pdf: str, wait_ms: int = 4000) -> str | None:
    """Print an HTML file to PDF with headless Chrome (page size from CSS @page). Returns an error or None."""
    chrome = find_chrome()
    if not chrome:
        return "Chrome/Chromium not found (set SCIENCE_SKILL_CHROME)"
    prof = os.path.join(os.path.dirname(os.path.abspath(pdf)), ".chrome-profile")
    p = _run([chrome, *_chrome_flags(prof), "--no-pdf-header-footer", "--print-to-pdf-no-header",
              f"--virtual-time-budget={wait_ms}", f"--print-to-pdf={os.path.abspath(pdf)}",
              "file://" + os.path.abspath(html)])
    return None if os.path.exists(pdf) else f"Chrome failed: {p.stderr[-400:]}"


def html_dump_dom(html: str, wait_ms: int = 4000) -> tuple[str | None, str | None]:
    """The DOM after scripts ran (used to read overflow marks). Returns (dom, error)."""
    chrome = find_chrome()
    if not chrome:
        return None, "Chrome/Chromium not found"
    prof = os.path.join(os.path.dirname(os.path.abspath(html)), ".chrome-profile")
    p = _run([chrome, *_chrome_flags(prof), f"--virtual-time-budget={wait_ms}", "--dump-dom",
              "file://" + os.path.abspath(html)])
    return (p.stdout, None) if p.stdout else (None, f"Chrome failed: {p.stderr[-400:]}")


def office_to_pdf(path: str, outdir: str) -> tuple[str | None, str | None]:
    """Convert a .pptx with LibreOffice. Returns (pdf path, error)."""
    so = find_soffice()
    if not so:
        return None, "LibreOffice (soffice) not found"
    prof = "file://" + os.path.join(os.path.abspath(outdir), ".lo-profile")
    p = _run([so, f"-env:UserInstallation={prof}", "--headless", "--convert-to", "pdf", "--outdir", outdir, path],
             timeout=300)
    pdf = os.path.join(outdir, os.path.splitext(os.path.basename(path))[0] + ".pdf")
    return (pdf, None) if os.path.exists(pdf) else (None, f"LibreOffice failed: {(p.stderr or p.stdout)[-400:]}")


def pdf_to_png(pdf: str | None, prefix: str, width_px: int = 1600, first: int | None = None,
               last: int | None = None) -> tuple[list[str], str | None]:
    """Render PDF pages to PNG with pdftoppm. Returns (files, error)."""
    if not pdf or not os.path.exists(pdf):
        return [], "no PDF to render"
    tool = shutil.which("pdftoppm")
    if not tool:
        return [], "pdftoppm (poppler) not found"
    cmd = [tool, "-png", "-scale-to-x", str(width_px), "-scale-to-y", "-1"]
    if first:
        cmd += ["-f", str(first)]
    if last:
        cmd += ["-l", str(last)]
    p = _run([*cmd, pdf, prefix])
    files = sorted(glob.glob(prefix + "*.png"))
    return files, (None if files else f"pdftoppm failed: {p.stderr[-300:]}")


def latex_engine(cjk: bool) -> list[str] | None:
    """Command prefix for compiling a .tex file, or None if no TeX is installed."""
    if shutil.which("latexmk"):
        return ["latexmk", "-xelatex" if cjk else "-pdf", "-interaction=nonstopmode", "-halt-on-error"]
    eng = "xelatex" if cjk else "pdflatex"
    return [eng, "-interaction=nonstopmode", "-halt-on-error"] if shutil.which(eng) else None


def compile_tex(tex: str, cjk: bool) -> tuple[str | None, str, str | None]:
    """Compile tex in its directory. Returns (pdf, log text, error)."""
    cmd = latex_engine(cjk)
    if not cmd:
        return None, "", "no LaTeX installation found"
    d = os.path.dirname(os.path.abspath(tex))
    p = _run([*cmd, os.path.basename(tex)], timeout=600, cwd=d)
    pdf = os.path.splitext(os.path.abspath(tex))[0] + ".pdf"
    logf = os.path.splitext(os.path.abspath(tex))[0] + ".log"
    log = open(logf, encoding="utf-8", errors="replace").read() if os.path.exists(logf) else p.stdout
    return (pdf if os.path.exists(pdf) and p.returncode == 0 else None), log, \
        (None if p.returncode == 0 else f"LaTeX failed (exit {p.returncode}); see {logf}")


def tex_math_png(expr: str, out_png: str, display: bool = False, colour: str = "#000000",
                 dpi: int = 300) -> str | None:
    """Render one LaTeX math expression to a transparent PNG (pdflatex + pdftoppm). Returns an error or None."""
    if not (shutil.which("pdflatex") and (shutil.which("pdftocairo") or shutil.which("pdftoppm"))):
        return "pdflatex or pdftoppm not found"
    d = os.path.splitext(out_png)[0] + "_tex"
    os.makedirs(d, exist_ok=True)
    r, g, b = hex_rgb(colour)
    body = f"$\\displaystyle {expr}$" if display else f"${expr}$"
    src = ("\\documentclass[border=1pt,varwidth]{standalone}\n\\usepackage{amsmath,amssymb,bm}\n"
           "\\usepackage{xcolor}\n\\begin{document}\n"
           f"\\definecolor{{fg}}{{RGB}}{{{r},{g},{b}}}\\color{{fg}}{body}\n\\end{{document}}\n")
    with open(os.path.join(d, "m.tex"), "w", encoding="utf-8") as fh:
        fh.write(src)
    p = _run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "m.tex"], cwd=d)
    if p.returncode != 0:
        return "LaTeX could not typeset: " + expr[:60]
    if shutil.which("pdftocairo"):       # transparent background
        cmd = ["pdftocairo", "-png", "-transp", "-r", str(dpi), "-singlefile"]
    else:
        cmd = ["pdftoppm", "-png", "-r", str(dpi), "-singlefile"]
    q = _run([*cmd, os.path.join(d, "m.pdf"), os.path.splitext(out_png)[0]])
    return None if os.path.exists(out_png) else f"pdftoppm failed: {q.stderr[-200:]}"
