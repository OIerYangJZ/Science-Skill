"""slidespec.py - the Markdown content spec shared by research-poster and group-meeting-deck.

Content and style are kept apart: one spec file holds what the poster or talk says; the style is chosen
at render time, so the same content can be rendered in every style for comparison.

Format
------
    ---
    title: Short title
    authors: A. Author, B. Author
    style: clean
    ---
    # Section divider {attrs}          (slides: a section slide; poster: ignored as a panel title)
    ## Slide or panel title {col=2 layout=figure key}
    Paragraph text with **bold**, *italic*, `code`, $x^2$, [link](https://...), ==highlight==.
    - bullet
      - sub-bullet
    - {verified R2} bullet with a status chip; R2 is a dead-end-ledger ID (optional)
    1. numbered item
    ![Caption](figures/fig1.png){width=70%}
    | table | header |
    |---|---|
    | cell | cell |
    $$ display math $$
    > quote or key message
    :::                                (column break inside a slide or panel)
    ???                                (speaker notes until the next heading)
    <!-- comment, ignored -->

The front matter is simple 'key: value' lines (not full YAML). Placeholders are written [[like this]]
and are reported by the checks until replaced.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

ATTR_RX = re.compile(r"\s*\{([^{}]*)\}\s*$")
STATUS_WORDS = ("verified", "unverified", "conditional", "preliminary", "negative", "retracted", "done",
                "in-progress", "blocked", "planned", "dropped", "failed", "partial", "inconclusive", "succeeded")
CHIP_RX = re.compile(r"^\{(" + "|".join(re.escape(w) for w in STATUS_WORDS) + r")(?:[\s:]+([A-Za-z]+\d+[\w.\-]*))?\}\s*",
                     re.I)
IMG_RX = re.compile(r"^!\[(?P<cap>(?:\[\[[^\]]*\]\]|[^\]])*)\]\((?P<path>(?:\[\[[^\]]*\]\]|[^)\s])+)(?:\s+\"[^\"]*\")?\)"
                    r"(?P<attrs>\{[^{}]*\})?\s*$")


@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False
    math: bool = False
    link: str | None = None
    highlight: bool = False


@dataclass
class Element:
    kind: str                      # para, bullets, image, table, math, code, quote, colbreak
    runs: list[Run] = field(default_factory=list)                 # para, quote
    items: list[tuple[int, list[Run], str | None, str | None, bool]] = field(default_factory=list)
    # bullets: (level, runs, status, ledger id, numbered)
    path: str = ""                 # image
    caption: list[Run] = field(default_factory=list)
    attrs: dict = field(default_factory=dict)
    rows: list[list[list[Run]]] = field(default_factory=list)     # table; first row is the header
    text: str = ""                 # math, code (raw)
    line: int = 0


@dataclass
class Block:
    level: int                     # 1 = section, 2 = slide / panel
    title: list[Run]
    attrs: dict
    elements: list[Element] = field(default_factory=list)
    notes: str = ""
    line: int = 0

    @property
    def title_text(self) -> str:
        return runs_text(self.title)


@dataclass
class Spec:
    meta: dict
    blocks: list[Block]
    path: str = ""
    preamble: list[Element] = field(default_factory=list)   # elements before the first heading

    def get(self, key: str, default=None):
        return self.meta.get(key, default)

    def resolve(self, p: str) -> str:
        if os.path.isabs(p) or not self.path:
            return p
        return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(self.path)), p))


def parse_attrs(s: str) -> dict:
    out: dict = {}
    for tok in re.findall(r"[\w\-]+=\"[^\"]*\"|[\w\-]+=\S+|[\w\-#.]+", s):
        if "=" in tok:
            k, v = tok.split("=", 1)
            out[k.lower()] = v.strip('"')
        else:
            out[tok.lower()] = True
    return out


def _split_attrs(text: str) -> tuple[str, dict]:
    m = ATTR_RX.search(text)
    if m and not text.rstrip().endswith("$}"):
        return text[:m.start()].rstrip(), parse_attrs(m.group(1))
    return text, {}


INLINE_RX = re.compile(r"(\*\*(?P<b>.+?)\*\*|__(?P<b2>.+?)__|(?<![\w*])\*(?P<i>[^*\s][^*]*?)\*(?!\w)|"
                       r"(?<![\w_])_(?P<i2>[^_\s][^_]*?)_(?![\w])|`(?P<c>[^`]+)`|(?<![\\$])\$(?P<m>[^$\n]+?)\$|"
                       r"\[(?P<lt>[^\]]+)\]\((?P<lu>[^)\s]+)\)|==(?P<h>.+?)==)")


def inline(text: str) -> list[Run]:
    """Inline Markdown to runs. Nesting is one level deep: **bold *italic*** gives a bold run."""
    runs: list[Run] = []
    pos = 0
    for m in INLINE_RX.finditer(text):
        if m.start() > pos:
            runs.append(Run(text[pos:m.start()]))
        g = m.groupdict()
        if g["b"] is not None or g["b2"] is not None:
            for r in inline(g["b"] if g["b"] is not None else g["b2"]):
                r.bold = True
                runs.append(r)
        elif g["i"] is not None or g["i2"] is not None:
            runs.append(Run(g["i"] if g["i"] is not None else g["i2"], italic=True))
        elif g["c"] is not None:
            runs.append(Run(g["c"], code=True))
        elif g["m"] is not None:
            runs.append(Run(g["m"], math=True))
        elif g["lt"] is not None:
            runs.append(Run(g["lt"], link=g["lu"]))
        elif g["h"] is not None:
            for r in inline(g["h"]):
                r.highlight = True
                runs.append(r)
        pos = m.end()
    if pos < len(text):
        runs.append(Run(text[pos:]))
    return [r for r in runs if r.text]


def runs_text(runs: list[Run]) -> str:
    return "".join(r.text for r in runs)


def _table_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_text(text: str, path: str = "") -> Spec:
    lines = text.splitlines()
    meta: dict = {}
    i = 0
    if lines and lines[0].strip() == "---":
        j = 1
        while j < len(lines) and lines[j].strip() != "---":
            ln = lines[j]
            if ":" in ln and not ln.lstrip().startswith("#"):
                k, v = ln.split(":", 1)
                meta[k.strip().lower()] = v.strip()
            j += 1
        i = j + 1
    spec = Spec(meta=meta, blocks=[], path=path)
    cur: Block | None = None
    in_notes = False
    notes: list[str] = []
    para: list[str] = []
    para_line = 0

    def target() -> list[Element]:
        return cur.elements if cur is not None else spec.preamble

    def flush_para():
        nonlocal para
        if para:
            target().append(Element("para", runs=inline(" ".join(s.strip() for s in para)), line=para_line))
            para = []

    def flush_notes():
        nonlocal notes
        if cur is not None and notes:
            cur.notes = "\n".join(notes).strip()
        notes = []

    # strip HTML comments (possibly multi-line)
    body = "\n".join(lines[i:])
    body = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), body, flags=re.S)
    lines = body.splitlines()
    base = i
    k = 0
    while k < len(lines):
        raw = lines[k]
        ln = raw.rstrip()
        lineno = base + k + 1
        h = re.match(r"^(#{1,2})\s+(.*)$", ln)
        if h:
            flush_para()
            flush_notes()
            in_notes = False
            title, attrs = _split_attrs(h.group(2).strip())
            cur = Block(level=len(h.group(1)), title=inline(title), attrs=attrs, line=lineno)
            spec.blocks.append(cur)
            k += 1
            continue
        if in_notes:
            notes.append(raw)
            k += 1
            continue
        s = ln.strip()
        if s == "???":
            flush_para()
            in_notes = True
            k += 1
            continue
        if not s:
            flush_para()
            k += 1
            continue
        if s == ":::":
            flush_para()
            target().append(Element("colbreak", line=lineno))
            k += 1
            continue
        if s.startswith("```"):
            flush_para()
            code = []
            k += 1
            while k < len(lines) and not lines[k].strip().startswith("```"):
                code.append(lines[k])
                k += 1
            target().append(Element("code", text="\n".join(code), attrs={"lang": s[3:].strip()}, line=lineno))
            k += 1
            continue
        if s.startswith("$$"):
            flush_para()
            buf = s[2:]
            while not buf.rstrip().endswith("$$") and k + 1 < len(lines):
                k += 1
                buf += "\n" + lines[k]
            target().append(Element("math", text=buf.rstrip()[:-2].strip() if buf.rstrip().endswith("$$") else buf,
                                    line=lineno))
            k += 1
            continue
        m = IMG_RX.match(s)
        if m:
            flush_para()
            attrs = parse_attrs(m.group("attrs")[1:-1]) if m.group("attrs") else {}
            target().append(Element("image", path=m.group("path"), caption=inline(m.group("cap")), attrs=attrs,
                                    line=lineno))
            k += 1
            continue
        if s.startswith("|"):
            flush_para()
            rows = []
            while k < len(lines) and lines[k].strip().startswith("|"):
                cells = _table_row(lines[k])
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append([inline(c) for c in cells])
                k += 1
            target().append(Element("table", rows=rows, line=lineno))
            continue
        if s.startswith(">"):
            flush_para()
            q = []
            while k < len(lines) and lines[k].strip().startswith(">"):
                q.append(lines[k].strip()[1:].strip())
                k += 1
            text_q, attrs = _split_attrs(" ".join(q))
            target().append(Element("quote", runs=inline(text_q), attrs=attrs, line=lineno))
            continue
        b = re.match(r"^(\s*)([-*+•]|\d+[.)])\s+(.*)$", ln)
        if b:
            flush_para()
            items = []
            while k < len(lines):
                b = re.match(r"^(\s*)([-*+•]|\d+[.)])\s+(.*)$", lines[k].rstrip())
                if not b:
                    nxt = lines[k].strip()
                    if nxt and items and lines[k].startswith("  ") and not nxt.startswith(("|", "![", "$$")):
                        lvl, runs, st, rid, num = items[-1]
                        items[-1] = (lvl, runs + [Run(" ")] + inline(nxt), st, rid, num)
                        k += 1
                        continue
                    break
                level = len(b.group(1).expandtabs(4)) // 2
                body_t = b.group(3)
                st = rid = None
                c = CHIP_RX.match(body_t)
                if c:
                    st, rid = c.group(1).lower(), c.group(2)
                    body_t = body_t[c.end():]
                items.append((min(level, 3), inline(body_t), st, rid, b.group(2)[0].isdigit()))
                k += 1
            target().append(Element("bullets", items=items, line=lineno))
            continue
        if not para:
            para_line = lineno
        para.append(ln)
        k += 1
    flush_para()
    flush_notes()
    return spec


def parse(path: str) -> Spec:
    with open(path, encoding="utf-8") as fh:
        return parse_text(fh.read(), path)


def element_text(e: Element) -> str:
    if e.kind in ("para", "quote"):
        return runs_text(e.runs)
    if e.kind == "bullets":
        return "\n".join(runs_text(r) for _, r, *_ in e.items)
    if e.kind == "image":
        return runs_text(e.caption)
    if e.kind == "table":
        return "\n".join(" | ".join(runs_text(c) for c in row) for row in e.rows)
    if e.kind in ("math", "code"):
        return e.text
    return ""


def block_text(b: Block, with_title: bool = True) -> str:
    parts = [b.title_text] if with_title else []
    parts += [element_text(e) for e in b.elements]
    return "\n".join(p for p in parts if p)


VISIBLE_META = ("title", "subtitle", "takeaway", "authors", "presenter", "affiliations", "venue", "group",
                "contact", "footer", "date")


def visible_text(spec: Spec, meta_keys=VISIBLE_META) -> str:
    """All text that appears on the poster or slides (not speaker notes)."""
    parts = [str(spec.meta[k]) for k in meta_keys if spec.meta.get(k)]
    parts += [element_text(e) for e in spec.preamble]
    parts += [block_text(b) for b in spec.blocks]
    return "\n".join(parts)
