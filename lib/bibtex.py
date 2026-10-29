"""bibtex.py - a small, dependency-free BibTeX reader for checking metadata.

It keeps each entry's line number and its raw fields. It is meant for
verification, not for round-trip editing: proposed corrections are written as
new entries, never by rewriting the user's .bib in place.
"""
from __future__ import annotations

import re
import unicodedata

ACCENTS = {
    "`": "\u0300", "'": "\u0301", "^": "\u0302", "~": "\u0303", "=": "\u0304", "u": "\u0306", ".": "\u0307",
    '"': "\u0308", "r": "\u030a", "H": "\u030b", "v": "\u030c", "c": "\u0327", "k": "\u0328",
}
SPECIAL = {r"\ss": "ss", r"\o": "o", r"\O": "O", r"\ae": "ae", r"\AE": "AE", r"\l": "l", r"\L": "L",
           r"\i": "i", r"\j": "j", r"\aa": "a", r"\AA": "A", r"\oe": "oe", r"\OE": "OE"}


def _read_value(s: str, i: int) -> tuple[str, int]:
    """Read a field value starting at s[i] (after '='). Returns (value, index after it)."""
    parts = []
    n = len(s)
    while i < n:
        while i < n and s[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        c = s[i]
        if c == "{":
            depth, j = 0, i
            while j < n:
                if s[j] == "\\":
                    j += 2
                    continue
                if s[j] == "{":
                    depth += 1
                elif s[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            parts.append(s[i + 1:j])
            i = j + 1
        elif c == '"':
            j = i + 1
            depth = 0
            while j < n and not (s[j] == '"' and depth == 0):
                if s[j] == "{":
                    depth += 1
                elif s[j] == "}":
                    depth -= 1
                j += 1
            parts.append(s[i + 1:j])
            i = j + 1
        else:
            m = re.match(r"[^\s,#}]+", s[i:])
            tok = m.group(0) if m else ""
            parts.append(tok)
            i += len(tok)
        while i < n and s[i] in " \t\r\n":
            i += 1
        if i < n and s[i] == "#":
            i += 1
            continue
        break
    return "".join(parts), i


def parse_bib(text: str) -> list[dict]:
    entries = []
    for m in re.finditer(r"@\s*([A-Za-z]+)\s*([{(])", text):
        etype = m.group(1).lower()
        if etype in ("comment", "preamble", "string"):
            continue
        i = m.end()
        km = re.match(r"\s*([^,\s]+)\s*,", text[i:])
        if not km:
            continue
        key = km.group(1)
        i += km.end()
        fields = {}
        n = len(text)
        while i < n:
            fm = re.match(r"\s*([A-Za-z][\w\-:]*)\s*=\s*", text[i:])
            if not fm:
                break
            name = fm.group(1).lower()
            i += fm.end()
            val, i = _read_value(text, i)
            fields[name] = re.sub(r"\s+", " ", val).strip()
            cm = re.match(r"\s*,", text[i:])
            if cm:
                i += cm.end()
            else:
                break
        entries.append({"type": etype, "key": key, "fields": fields, "line": text.count("\n", 0, m.start()) + 1})
    return entries


def latex_to_text(s: str) -> str:
    s = s or ""
    for k, v in SPECIAL.items():
        s = re.sub(re.escape(k) + r"(?![A-Za-z])", v, s)

    def acc(m):
        return unicodedata.normalize("NFC", m.group(2) + ACCENTS.get(m.group(1), ""))
    s = re.sub(r"\\([`'^~=u.\"rHvck])\s*\{?([A-Za-z])\}?", acc, s)
    s = re.sub(r"\$([^$]*)\$", r"\1", s)
    s = re.sub(r"\\(?:emph|textit|textbf|textrm|mathrm|mathcal|mathbb|text)\s*\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\[A-Za-z]+\s*", " ", s)
    s = s.replace("{", "").replace("}", "").replace("~", " ").replace("--", "-")
    return re.sub(r"\s+", " ", s).strip()


def split_authors(s: str) -> list[str]:
    return [a.strip() for a in re.split(r"\s+and\s+", s or "") if a.strip()]


def family_name(author: str) -> str:
    """'Last, First' / 'First Last' / '{Collaboration}' -> family name (plain text)."""
    a = author.strip()
    if a.startswith("{") and a.endswith("}"):
        return latex_to_text(a)
    a = latex_to_text(a)
    if "," in a:
        return a.split(",")[0].strip()
    toks = a.split()
    if not toks:
        return ""
    # keep lowercase particles: "van de Wetering", "de Beaudrap"
    i = len(toks) - 1
    while i > 0 and toks[i - 1][:1].islower():
        i -= 1
    return " ".join(toks[i:])


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]+", "", s).strip()


def format_entry(etype: str, key: str, fields: dict) -> str:
    order = ["author", "title", "journal", "booktitle", "volume", "number", "pages", "year", "doi", "eprint",
             "archiveprefix", "primaryclass", "url", "note"]
    keys = [k for k in order if k in fields] + [k for k in fields if k not in order]
    lines = [f"@{etype}{{{key},"]
    for k in keys:
        lines.append(f"  {k} = {{{fields[k]}}},")
    lines.append("}")
    return "\n".join(lines)


def parse_ris(text: str) -> list[dict]:
    """RIS (Zotero / EndNote / Mendeley export) -> entries shaped like parse_bib()."""
    entries, cur, authors, start = [], None, [], 0
    tagmap = {"TI": "title", "T1": "title", "JO": "journal", "JF": "journal", "T2": "journal", "JA": "journal",
              "VL": "volume", "IS": "number", "DO": "doi", "UR": "url", "PB": "publisher", "SN": "issn",
              "BT": "booktitle"}
    sp = ep = ""
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^([A-Z][A-Z0-9])\s{2}-\s?(.*)$", line)
        if not m:
            continue
        tag, val = m.group(1), m.group(2).strip()
        if tag == "TY":
            cur, authors, start, sp, ep = {"_ty": val}, [], i, "", ""
        elif cur is None:
            continue
        elif tag in ("AU", "A1"):
            authors.append(val)
        elif tag in ("PY", "Y1", "DA") and "year" not in cur:
            ym = re.search(r"\d{4}", val)
            if ym:
                cur["year"] = ym.group(0)
        elif tag == "SP":
            sp = val
        elif tag == "EP":
            ep = val
        elif tag in tagmap and tagmap[tag] not in cur:
            cur[tagmap[tag]] = val
        elif tag == "ER":
            if authors:
                cur["author"] = " and ".join(authors)
            if sp:
                cur["pages"] = f"{sp}--{ep}" if ep else sp
            ty = cur.pop("_ty", "JOUR")
            etype = {"JOUR": "article", "BOOK": "book", "CHAP": "incollection", "CONF": "inproceedings",
                     "CPAPER": "inproceedings", "THES": "phdthesis", "RPRT": "techreport", "ELEC": "online",
                     "UNPB": "unpublished", "GEN": "misc"}.get(ty, "misc")
            entries.append({"type": etype, "key": f"ris{len(entries) + 1}", "fields": cur, "line": start})
            cur = None
    return entries


def split_reference_list(text: str) -> list[tuple[int, str]]:
    """A plain reference list -> [(line_number, reference string)]. Entries are
    separated by blank lines, or each starts with '1.', '[1]', '(1)' or is one line."""
    lines = text.splitlines()
    numbered = sum(1 for l in lines if re.match(r"^\s*(\[\d+\]|\(\d+\)|\d+[.)])\s+\S", l))
    out, buf, start = [], [], 0
    for i, l in enumerate(lines, 1):
        if not l.strip():
            if buf:
                out.append((start, " ".join(buf)))
                buf = []
            continue
        if re.match(r"^#{1,6}\s", l):
            continue
        new_entry = (numbered >= 2 and re.match(r"^\s*(\[\d+\]|\(\d+\)|\d+[.)])\s+\S", l)) or numbered < 2 and not buf
        if new_entry and buf:
            out.append((start, " ".join(buf)))
            buf = []
        if not buf:
            start = i
        buf.append(l.strip())
        if numbered < 2:
            out.append((start, " ".join(buf)))
            buf = []
    if buf:
        out.append((start, " ".join(buf)))
    return [(n, re.sub(r"^\s*(\[\d+\]|\(\d+\)|\d+[.)])\s+", "", s)) for n, s in out if len(s) > 25]
