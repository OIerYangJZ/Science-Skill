"""docxutil.py - read a Word .docx manuscript with the standard library only.

The document is turned into markdown-like text: headings (Word heading styles,
Title, or a short bold-only paragraph) become '#'/'##' lines, every other
paragraph is one line followed by a blank line, table rows become
'cell | cell' lines, equations become MATH. Each output line maps back to the
paragraph number in the document, so reports can point to '¶n'.
"""
from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def _para_text(p) -> str:
    out = []
    for el in p.iter():
        tag = el.tag
        if tag == W + "t" and el.text:
            out.append(el.text)
        elif tag == W + "tab":
            out.append("\t")
        elif tag in (W + "br", W + "cr"):
            out.append(" ")
        elif tag == M + "oMath":
            out.append(" MATH ")
    txt = "".join(out)
    # text inside an equation was also collected through w:t-free m:t nodes? keep MATH only
    return re.sub(r"[ \t]+", " ", txt).strip()


def _style(p) -> str:
    ppr = p.find(W + "pPr")
    if ppr is None:
        return ""
    ps = ppr.find(W + "pStyle")
    return (ps.get(W + "val") or "") if ps is not None else ""


def _all_bold(p) -> bool:
    runs = [r for r in p.iter(W + "r") if "".join(t.text or "" for t in r.iter(W + "t")).strip()]
    if not runs:
        return False
    for r in runs:
        rpr = r.find(W + "rPr")
        b = rpr.find(W + "b") if rpr is not None else None
        if b is None or b.get(W + "val") in ("0", "false"):
            return False
    return True


HEADING_WORDS = re.compile(
    r"^(\d+(\.\d+)*\.?\s+)?(abstract|summary|introduction|background|methods?|materials and methods|results|"
    r"discussion|conclusions?|references|bibliography|literature cited|acknowledg\w*|supplementary.*|"
    r"limitations|related work|outlook|appendix.*)\s*:?$", re.I)


def docx_to_markdown(path: str) -> tuple[str, list[int]]:
    """Return (text, para_of_line): para_of_line[i] is the 1-based paragraph
    number for output line i (0-based)."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    body = root.find(W + "body")
    lines: list[str] = []
    pmap: list[int] = []
    n = 0

    def emit(s: str, para: int):
        lines.append(s)
        pmap.append(para)

    for child in list(body) if body is not None else []:
        if child.tag == W + "p":
            n += 1
            txt = _para_text(child)
            # equations: collect m:t text is skipped on purpose (MATH placeholder)
            if not txt:
                continue
            st = _style(child).lower()
            m = re.match(r"heading\s*(\d)", st)
            short = len(txt) <= 80 and len(txt.split()) <= 10
            if st == "title":
                emit("# " + txt, n)
            elif m:
                emit("#" * min(6, int(m.group(1)) + 1) + " " + txt, n)
            elif "abstract" in st:
                if short and re.match(r"^(abstract|summary)\b", txt, re.I):
                    emit("## " + txt.rstrip(":"), n)
                else:
                    if not any(l.startswith("## Abstract") for l in lines):
                        emit("## Abstract", n)
                    emit(txt, n)
            elif short and ((_all_bold(child) and not txt.endswith(".")) or HEADING_WORDS.match(txt)):
                emit("## " + txt.rstrip(":"), n)
            else:
                lab = re.match(r"^(Abstract|Summary|ABSTRACT|SUMMARY)\s*[:.\u2014\u2013-]\s+(.{40,})$", txt)
                if lab:
                    emit("## Abstract", n)
                    emit(lab.group(2), n)
                else:
                    emit(txt, n)
            emit("", n)
        elif child.tag == W + "tbl":
            for tr in child.iter(W + "tr"):
                cells = []
                for tc in tr.iter(W + "tc"):
                    cells.append(" ".join(_para_text(p) for p in tc.iter(W + "p")).strip())
                n += 1
                emit(" | ".join(cells), n)
            emit("", n)
    return "\n".join(lines) + "\n", pmap
