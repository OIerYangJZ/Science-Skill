#!/usr/bin/env python3
"""number_audit.py - inventory, cross-check and trace the numbers in a manuscript.

Subcommands
  extract MAIN.tex --out DIR [--all]
      Writes DIR/numbers.json and DIR/numbers.md (every number with file:line,
      region, symbol, context) and DIR/conflicts.md:
        - the same symbol given different values ("K = 197" here, "K = 784" there);
        - literal numbers that duplicate a data macro (\\X defined as 2814 but
          "2814" typed by hand elsewhere: it will not follow the data);
        - the same macro or number reported with inconsistent rounding.
      Small integers (< 10), year-like integers, section/figure/equation
      numbers, lengths and numbers inside \\cite/\\ref/\\label are skipped
      unless --all is given.

  stats MAIN [MAIN ...] --out DIR [--alpha 0.05]
      statcheck-style recomputation: p from reported t / F / chi2 / r / z and
      degrees of freedom (allowing for rounding), k/n (x%) percentages, and
      OR/RR/HR confidence intervals. Works on .tex, .docx, .md, .txt, .pdf.

  guard-init DIR/numbers.json --out guards.json [--regions ...]
  guard-check guards.json [--manuscript FILE ...] [--strict]
      Guards keep audited numbers tied to their sources. guard-init writes one
      entry per key number (display, anchor words, rounding); fill in source and
      locator (JSON path, CSV cell, regex, const). guard-check recomputes each
      value with decimal ROUND_HALF_UP rounding, looks for it near its anchor
      with digit boundaries, and fails on mismatches and on 'stale' values that
      were corrected and must not reappear. Exit code 1 on failure (use in CI or
      a pre-commit hook).

  trace DIR/numbers.json --repo REPO [--regions R1,R2] [--exclude PATTERN ...]
      Searches data files, generated tables and scripts in REPO for values
      that round to each displayed number. Writes DIR/trace.md and trace.json.
      Status per number: traced (1-5 candidate sources), ambiguous (many),
      orphan (nowhere in the repo: recompute it or document its derivation).

A trace hit only says "this value occurs there". Whether it is the right
source, with the right convention, is for the audit to decide.
"""
from __future__ import annotations

import argparse
import bisect
import fnmatch
import json
import math
import os
import re
import sys

LIB = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "lib")
sys.path.insert(0, os.path.normpath(LIB))
from texutil import (  # noqa: E402
    _command_spans, _line_of, clean_latex, doc_region_labeler, doc_sections, find_macros, light_clean,
    load_document, strip_comments_keep,
)
import statsutil  # noqa: E402

PLAIN_TR = str.maketrans({"\u2070": "0", "\u00b9": "1", "\u00b2": "2", "\u00b3": "3", "\u2074": "4", "\u2075": "5",
                          "\u2076": "6", "\u2077": "7", "\u2078": "8", "\u2079": "9", "\u207b": "-", "\u207a": "+",
                          "\u2212": "-", "\u2009": " ", "\u202f": " ", "\u00a0": " "})

# ---------------------------------------------------------------------------
# number recognition in LaTeX source
# ---------------------------------------------------------------------------
INT_OR_DEC = r"(?:\d{1,3}(?:(?:\{,\}|,)\d{3})+|\d+)(?:\.\d+)?"
NUM_RX = re.compile(
    r"(?P<enote>(?<![\w.])\d+(?:\.\d+)?[eE][-+]?\d+(?![\w.]))"
    r"|(?P<scim>(?<![\w.])" + INT_OR_DEC + r")\s*(?:\\times|\\cdot|×)\s*10\s*\^?\s*\{?\s*(?P<scie>[-−]?\s*\d+)\s*\}?"
    r"|(?P<pow>(?<![\w.])10)\s*\^\s*\{?\s*(?P<powe>[-−]\s*\d+|\d+)\s*\}?"
    r"|\\[td]?frac\s*\{?\s*(?P<fa>\d+)\s*\}?\s*\{?\s*(?P<fb>\d+)\s*\}?"
    r"|(?P<sa>(?<![\w.}/])\d+)\s*/\s*(?P<sb>\d+)(?![\w.{])(?!\s*/\s*\d)"
    r"|(?P<num>(?<![\w.])(?:" + INT_OR_DEC + r"|(?<![\d,])\.\d+))(?P<pct>\s*\\?%)?"
)
UNIT_AFTER = re.compile(r"\s*(?:pt|em|ex|cm|mm|in|bp|sp|\\textwidth|\\linewidth|\\columnwidth|\\textheight|\\hsize)\b")
LABEL_BEFORE = re.compile(
    r"(?:Fig(?:ure)?s?\.?|Sec(?:tion)?s?\.?|Thm\.?|Theorems?|Lemmas?|Lem\.?|Prop(?:osition)?s?\.?|Cor(?:ollary)?\.?|"
    r"Corollaries|Eqs?\.?|Equations?|Tables?|Tab\.?|Appendix|Appendices|App\.?|Refs?\.?|Conjectures?|Conj\.?|"
    r"Definitions?|Def\.?|Remarks?|Steps?|Cases?|Items?|Examples?|Algorithms?|Alg\.?|Chapters?|Ch\.?|Part|"
    r"arXiv:?|Vol\.?|No\.?|pp?\.)\s*~?\s*\(?\s*(?:[A-Z]\.?)?$"
)
SKIP_CMDS = ("label", "ref", "cref", "Cref", "eqref", "autoref", "pageref", "cite", "citep", "citet", "Cite",
             "onlinecite", "citealp", "citenum", "includegraphics", "vspace", "hspace", "setlength", "url", "href",
             "input", "include", "bibliography", "bibliographystyle", "usepackage", "documentclass", "textcolor",
             "color", "definecolor", "hypersetup", "xref", "doi", "linewidth", "resizebox", "scalebox",
             "multicolumn", "multirow", "rule", "raisebox", "hyperref")
REL_RX = re.compile(
    r"(?P<sym>(?:\\[A-Za-z]+|\b[A-Z]{2,5}|[A-Za-z])(?:\s*(?:_|\^)\s*(?:\{[^{}]*\}|\\[A-Za-z]+|[A-Za-z0-9]))*"
    r"(?:\s*\([^()]{0,20}\))?)\s*(?P<rel>=|\\approx|\\simeq|\\sim|\\leq?|\\geq?|\\lesssim|\\gtrsim|<|>|≈|≤|≥)\s*$"
)


def _f(s: str) -> float:
    return float(s.replace("{,}", "").replace(",", "").replace("−", "-").replace(" ", ""))


def _decimals(s: str) -> int:
    s = s.replace("{,}", "").replace(",", "")
    return len(s.split(".")[1]) if "." in s else 0


def _sigfigs(s: str) -> int:
    d = re.sub(r"[^\d]", "", s.split("e")[0].split("E")[0]).lstrip("0")
    return max(1, len(d))


def parse_match(m: re.Match) -> dict | None:
    g = m.groupdict()
    if g["enote"]:
        v = float(g["enote"])
        mant = re.split(r"[eE]", g["enote"])[0]
        exp = int(re.split(r"[eE]", g["enote"])[1])
        return {"value": v, "kind": "sci", "halfwidth": 0.5 * 10 ** (exp - _decimals(mant))}
    if g["scim"]:
        e = int(g["scie"].replace("−", "-").replace(" ", ""))
        mant = g["scim"]
        return {"value": _f(mant) * 10 ** e, "kind": "sci", "halfwidth": 0.5 * 10 ** (e - _decimals(mant))}
    if g["pow"]:
        e = int(g["powe"].replace("−", "-").replace(" ", ""))
        return {"value": 10.0 ** e, "kind": "sci", "halfwidth": 0.05 * 10.0 ** e}
    if g["fa"]:
        a, b = int(g["fa"]), int(g["fb"])
        return {"value": a / b, "kind": "frac", "halfwidth": 1e-9 * max(1, a / b)} if b else None
    if g["sa"]:
        a, b = int(g["sa"]), int(g["sb"])
        return {"value": a / b, "kind": "frac", "halfwidth": 1e-9 * max(1, a / b)} if b else None
    s = g["num"]
    v = _f(s)
    dec = _decimals(s)
    if g["pct"]:
        return {"value": v, "kind": "percent", "halfwidth": 0.5 * 10 ** -dec}
    if dec:
        return {"value": v, "kind": "decimal", "halfwidth": 0.5 * 10 ** -dec}
    if 1900 <= v <= 2099 and "," not in s and "{,}" not in s:
        return {"value": v, "kind": "year-like", "halfwidth": 0.5}
    return {"value": v, "kind": "int" if v >= 10 else "small", "halfwidth": 0.5}


def norm_symbol(sym: str) -> str:
    s = re.sub(r"\s+", "", sym)
    s = re.sub(r"\{(\\?[A-Za-z0-9]+)\}", r"\1", s)
    s = s.replace("\\varepsilon", "\\epsilon").replace("\\mathrm", "").replace("\\rm", "")
    return s


def display_key(v: float, halfwidth: float) -> str:
    if halfwidth <= 0:
        return repr(v)
    digits = max(0, -int(math.floor(math.log10(halfwidth * 2))) )
    return f"{v:.{min(digits, 12)}f}"


def extract_plain(main: str, src, kind: str, include_all: bool) -> dict:
    """Numbers in .docx / .md / .txt / .pdf manuscripts (no macros, no LaTeX)."""
    text = src.text
    nc = text.translate(PLAIN_TR)
    label = doc_region_labeler(nc, kind)
    secs = doc_sections(nc, kind)
    skip = []
    if "references" in secs:
        skip.append((secs["references"][0], secs["references"][1]))
    for m in re.finditer(r"https?://\S+|\b10\.\d{4,9}/\S+|arXiv:\s*\d{4}\.\d{4,5}|\[\d+(?:[,\u2013\-]\s*\d+)*\]", nc):
        skip.append((m.start(), m.end()))
    items = []
    for m in NUM_RX.finditer(nc):
        if any(a <= m.start() < b for a, b in skip):
            continue
        before = nc[max(0, m.start() - 40):m.start()]
        if LABEL_BEFORE.search(before.replace("\n", " ")):
            continue
        p = parse_match(m)
        if not p or (not include_all and p["kind"] in ("small", "year-like")):
            continue
        f, ln = src.loc(_line_of(text, m.start()))
        rel = REL_RX.search(nc[max(0, m.start() - 80):m.start()])
        ctx, _ = light_clean(nc[max(0, m.start() - 90):m.end() + 90])
        items.append({
            "file": f, "line": ln, "region": label(m.start()), "raw": re.sub(r"\s+", " ", m.group(0)),
            "value": p["value"], "kind": p["kind"], "halfwidth": p["halfwidth"],
            "symbol": norm_symbol(rel.group("sym")) if rel else "", "relation": rel.group("rel") if rel else "",
            "macro": "", "context": re.sub(r"\s+", " ", ctx).strip(),
        })
    for k, it in enumerate(items, 1):
        it["id"] = f"N{k:04d}"
    return {"main": main, "macros": {}, "items": items, "conflicts": find_conflicts(items, {})}


def extract_many(mains: list[str], include_all: bool = False) -> dict:
    parts = [extract(m, include_all) for m in mains]
    items, macros = [], {}
    root = os.path.dirname(os.path.abspath(mains[0]))
    for m, p in zip(mains, parts):
        off = os.path.relpath(os.path.dirname(os.path.abspath(m)), root)
        for it in p["items"]:
            if off != ".":
                it["file"] = os.path.normpath(os.path.join(off, it["file"]))
            items.append(it)
        macros.update(p["macros"])
    for k, it in enumerate(items, 1):
        it["id"] = f"N{k:04d}"
    return {"main": mains[0], "mains": mains, "macros": macros, "items": items,
            "conflicts": find_conflicts(items, macros)}


def extract(main: str, include_all: bool = False) -> dict:
    src, kind = load_document(main)
    text = src.text
    is_tex = kind == "tex"
    if not is_tex:
        return extract_plain(main, src, kind, include_all)
    nc = strip_comments_keep(text)
    label = doc_region_labeler(text, kind)
    begin = re.search(r"\\begin\{document\}", nc)
    body_start = begin.end() if begin else 0

    skip_spans = []
    for start, arg_start, end, _name in _command_spans(nc, SKIP_CMDS):
        skip_spans.append((start, end))
    for m in re.finditer(r"\\begin\{(?:tabular\*?|tabularx|array)\}\s*(?:\[[^\]]*\])?\s*\{", nc):
        from texutil import _match_brace
        skip_spans.append((m.start(), _match_brace(nc, m.end() - 1)))
    for m in re.finditer(r"\[[^\[\]\n]*(?:width|height|scale|angle)\s*=[^\[\]\n]*\]", nc):
        skip_spans.append((m.start(), m.end()))
    for m in re.finditer(r"\b10\.\d{4,9}/\S+|arXiv:\s*\d{4}\.\d{4,5}|\d{4}\.\d{4,5}v?\d*", nc):
        skip_spans.append((m.start(), m.end()))
    skip_spans.sort()
    starts = [s for s, _ in skip_spans]

    def skipped(off: int) -> bool:
        i = bisect.bisect_right(starts, off) - 1
        while i >= 0 and i >= len(starts) - 10_000:
            s, e = skip_spans[i]
            if s <= off < e:
                return True
            if e < off - 5000:
                break
            i -= 1
        return False

    macros = {}
    for name, body in find_macros(text).items():
        m = re.search(r"\\[A-Za-z]+\s*\{[^{}]*\}\s*\{\s*(" + INT_OR_DEC + r")\s*(\\%)?\s*\}\s*$", body.strip())
        raw = None
        if m:
            raw = m.group(1) + ("%" if m.group(2) else "")
        else:
            b = re.sub(r"\\[,;!:]|\\ |\{,\}", lambda x: "," if x.group(0) == "{,}" else "", body).strip()
            b = re.sub(r"^\{|\}$|^\$|\$$|\\ensuremath\{|\\text\{", "", b).strip().rstrip("}")
            if re.fullmatch(INT_OR_DEC + r"(\\%)?", b):
                raw = b.replace("\\%", "%")
        if raw:
            r0 = raw.rstrip("%")
            macros[name] = {"raw": raw, "value": _f(r0), "halfwidth": 0.5 * 10 ** -_decimals(r0),
                            "decimals": _decimals(r0)}

    items = []
    for m in NUM_RX.finditer(nc, body_start):
        if skipped(m.start()):
            continue
        before = nc[max(0, m.start() - 40):m.start()]
        if re.search(r"[\^_]\s*\{?\s*-?\s*$", before) and not (m.group("pow") or m.group("scim")):
            continue
        if LABEL_BEFORE.search(before.replace("\n", " ")):
            continue
        if UNIT_AFTER.match(nc, m.end()):
            continue
        p = parse_match(m)
        if not p:
            continue
        if not include_all and p["kind"] in ("small", "year-like"):
            continue
        line_idx = _line_of(text, m.start())
        f, ln = src.loc(line_idx)
        rel = REL_RX.search(nc[max(0, m.start() - 80):m.start()])
        ctx_a = max(0, m.start() - 90)
        ctx, _ = clean_latex(text[ctx_a:m.end() + 90])
        items.append({
            "file": f, "line": ln, "region": label(m.start()), "raw": re.sub(r"\s+", " ", m.group(0)),
            "value": p["value"], "kind": p["kind"], "halfwidth": p["halfwidth"],
            "symbol": norm_symbol(rel.group("sym")) if rel else "", "relation": rel.group("rel") if rel else "",
            "macro": "", "context": re.sub(r"\s+", " ", ctx).strip(),
        })
    for name, info in macros.items():
        for m in re.finditer(re.escape(name) + r"(?![A-Za-z@])", nc[body_start:]):
            off = body_start + m.start()
            f, ln = src.loc(_line_of(text, off))
            rel = REL_RX.search(nc[max(0, off - 80):off])
            ctx, _ = clean_latex(text[max(0, off - 90):off + len(name) + 90])
            items.append({
                "file": f, "line": ln, "region": label(off), "raw": f"{name}={info['raw']}",
                "value": info["value"], "kind": "macro", "halfwidth": info["halfwidth"],
                "symbol": norm_symbol(rel.group("sym")) if rel else "", "relation": rel.group("rel") if rel else "",
                "macro": name, "context": re.sub(r"\s+", " ", ctx).strip(),
            })
    items.sort(key=lambda x: (x["file"], x["line"]))
    for k, it in enumerate(items, 1):
        it["id"] = f"N{k:04d}"
    return {"main": main, "macros": macros, "items": items, "conflicts": find_conflicts(items, macros)}


def _same(a: dict, b: dict) -> bool:
    tol = max(a["halfwidth"], b["halfwidth"]) + 1e-12 * max(abs(a["value"]), abs(b["value"]), 1)
    return abs(a["value"] - b["value"]) <= tol


def find_conflicts(items: list[dict], macros: dict) -> dict:
    by_sym: dict[str, list[dict]] = {}
    for it in items:
        if it["symbol"] and it["relation"] in ("=", "\\approx", "\\simeq", "≈"):
            by_sym.setdefault(it["symbol"], []).append(it)
    sym_conf = []
    for sym, its in by_sym.items():
        groups: list[list[dict]] = []
        for it in its:
            for g in groups:
                if _same(g[0], it):
                    g.append(it)
                    break
            else:
                groups.append([it])
        if len(groups) > 1:
            sym_conf.append({"symbol": sym, "generic": bool(re.fullmatch(r"\\?[A-Za-z]", sym)), "values": [
                {"value": g[0]["value"], "raw": g[0]["raw"], "where": [f"{x['file']}:{x['line']} ({x['region']})" for x in g]}
                for g in groups]})
    dup = []
    for name, info in macros.items():
        if info["value"] < 100 and info["decimals"] == 0:
            continue  # small integers coincide too often to be informative
        hits = [it for it in items if not it["macro"] and it["kind"] not in ("frac",)
                and abs(it["value"] - info["value"]) <= 1e-12 * max(1, abs(info["value"]))
                and abs(it["halfwidth"] - info["halfwidth"]) < 1e-15]
        if hits:
            dup.append({"macro": name, "raw": info["raw"],
                        "literal_at": [f"{x['file']}:{x['line']} ({x['region']}): {x['raw']}" for x in hits]})
    return {"symbol_conflicts": sym_conf, "macro_duplicates": dup}


def write_extract(res: dict, out: str):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "numbers.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    items = res["items"]
    regions: dict[str, int] = {}
    for it in items:
        key = it["region"].split(":")[0]
        regions[key] = regions.get(key, 0) + 1
    lines = [f"# Number inventory: {', '.join('`' + m + '`' for m in res.get('mains', [res['main']]))}", "",
             f"{len(items)} numbers ({sum(1 for i in items if i['macro'])} via {len(res['macros'])} numeric macros). "
             "By region: " + ", ".join(f"{k} {v}" for k, v in sorted(regions.items(), key=lambda x: -x[1])), "",
             "| id | loc | region | raw | kind | symbol | context |", "|---|---|---|---|---|---|---|"]
    order = {"title": 0, "abstract": 1, "introduction": 2, "conclusion": 3, "caption": 4, "table": 5, "theorem": 6}
    for it in sorted(items, key=lambda i: (order.get(i["region"].split(":")[0], 9), i["file"], i["line"])):
        sym = f"{it['symbol']} {it['relation']}" if it["symbol"] else ""
        ctx = it["context"][:150].replace("|", "\\|")
        lines.append(f"| {it['id']} | {it['file']}:{it['line']} | {it['region']} | {it['raw'].replace('|', '\\|')} | "
                     f"{it['kind']} | {sym.replace('|', '\\|')} | {ctx} |")
    with open(os.path.join(out, "numbers.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    c = res["conflicts"]
    cl = ["# Consistency leads", "",
          "Each item is a lead. A symbol can legitimately take different values in different settings "
          "(two examples at different accuracies); the audit decides.", "",
          f"## Same symbol, different values ({len(c['symbol_conflicts'])})", ""]
    specific = [sc for sc in c["symbol_conflicts"] if not sc["generic"]]
    generic = [sc for sc in c["symbol_conflicts"] if sc["generic"]]
    for title, group in (("Specific symbols (check first)", specific),
                         ("Single-letter variables (usually different settings)", generic)):
        if not group:
            continue
        cl += [f"### {title}", ""]
        for sc in group:
            cl.append(f"- `{sc['symbol']}`")
            for v in sc["values"]:
                cl.append(f"  - {v['raw']}: " + "; ".join(v["where"]))
        cl.append("")
    cl += ["", f"## Hand-typed copies of data macros ({len(c['macro_duplicates'])})", "",
           "These will not update when the data are regenerated.", ""]
    for d in c["macro_duplicates"]:
        cl.append(f"- `{d['macro']}` = {d['raw']}: " + "; ".join(d["literal_at"]))
    with open(os.path.join(out, "conflicts.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(cl) + "\n")
    print(f"{len(items)} numbers; {len(c['symbol_conflicts'])} symbol conflicts; "
          f"{len(c['macro_duplicates'])} macro duplicates -> {out}/numbers.md, conflicts.md")


# ---------------------------------------------------------------------------
# tracing
# ---------------------------------------------------------------------------
DATA_EXT = {".json", ".jsonl", ".csv", ".tsv", ".txt", ".dat", ".out", ".yaml", ".yml", ".toml", ".log", ".ipynb"}
CODE_EXT = {".py", ".m", ".jl", ".c", ".h", ".cpp", ".r", ".R", ".sh", ".sage", ".gp", ".nb", ".wl"}
TEXT_EXT = {".tex", ".md"}
SKIP_DIRS = {".git", ".venv", "venv", "env", "node_modules", "__pycache__", ".ipynb_checkpoints", ".mypy_cache",
             ".pytest_cache", "dist", "build", ".claude", ".tox", "site-packages", "dist-packages", "third_party",
             "vendor", "_vendor", "number_audit", "polish"}
TOKEN_RX = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w.])")
RANK = {"data": 0, "code": 1, "text": 2}


def file_class(rel: str, ext: str) -> str | None:
    if ext in DATA_EXT:
        return "data"
    if ext in CODE_EXT:
        return "code"
    if ext in TEXT_EXT:
        return "data" if re.search(r"(^|/)generated/|(^|/)gen_|_generated", rel) else "text"
    return None


def build_index(repo: str, exclude_files: set[str], exclude_globs: list[str], max_mb: float):
    vals: list[tuple[float, int]] = []
    locs: list[tuple[str, int, str, str, bool]] = []
    nfiles = 0
    skipped = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".") and not d.endswith("-venv")
                   and not d.endswith("_venv")]
        for fn in files:
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, repo)
            ext = os.path.splitext(fn)[1]
            cls = file_class(rel, ext)
            if not cls or os.path.abspath(path) in exclude_files:
                continue
            if any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(fn, g) for g in exclude_globs):
                continue
            if ext == ".log" and any(os.path.exists(os.path.splitext(path)[0] + e) for e in (".tex", ".aux")):
                continue  # LaTeX build log
            if os.path.getsize(path) > max_mb * 1e6:
                skipped.append(rel)
                continue
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    for ln, line in enumerate(fh, 1):
                        if len(line) > 20000:
                            line = line[:20000]
                        for m in TOKEN_RX.finditer(line):
                            tok = m.group(0)
                            try:
                                v = float(tok)
                            except ValueError:
                                continue
                            if math.isfinite(v):
                                vals.append((v, len(locs)))
                                locs.append((rel, ln, line.strip()[:140], cls, not re.search(r"[.eE]", tok)))
            except OSError:
                continue
            nfiles += 1
    vals.sort()
    return vals, locs, nfiles, skipped


STOP = {"the", "and", "for", "with", "that", "this", "are", "from", "per", "math", "ref", "bits", "data", "json",
        "true", "false", "none", "null", "into", "than", "each", "its", "our", "which", "when", "where", "all"}


def _words(text: str) -> set[str]:
    toks = re.findall(r"[A-Za-z]{3,}", re.sub(r"[_\-/.]", " ", text))
    return {t.lower() for t in toks} - STOP


def _lookup(keys, vals, locs, lo, hi):
    i = bisect.bisect_left(keys, lo)
    out = []
    while i < len(keys) and keys[i] < hi:
        out.append(locs[vals[i][1]])
        i += 1
    return out


def trace(numbers_json: str, repo: str, regions: list[str] | None, exclude: list[str], max_mb: float, out: str):
    res = json.load(open(numbers_json, encoding="utf-8"))
    main_dir = os.path.dirname(os.path.abspath(res["main"]))
    manuscript = {os.path.abspath(os.path.join(main_dir, it["file"])) for it in res["items"]}
    for m in res.get("mains", [res["main"]]):
        manuscript.add(os.path.abspath(m))
    vals, locs, nfiles, skipped = build_index(repo, manuscript, exclude, max_mb)
    keys = [v for v, _ in vals]
    rows = []
    wanted = res["items"]
    if regions:
        wanted = [it for it in wanted if any(it["region"].startswith(r) for r in regions)]
    for it in wanted:
        v, hw = it["value"], it["halfwidth"]
        targets = [(v, hw)]
        if it["kind"] == "percent" or it["raw"].endswith("%"):
            targets.append((v / 100, hw / 100))
        hits, how = [], "rounding"
        is_int_display = it["kind"] in ("int", "small", "year-like") or (it["kind"] == "macro" and hw == 0.5)
        if is_int_display:
            exact = [h for h in _lookup(keys, vals, locs, v - 1e-9, v + 1e-9) if h[4]]
            if exact:
                hits, how = exact, "exact integer"
        if not hits:
            for tv, thw in targets:
                pad = 1e-12 * max(1.0, abs(tv))
                hits += _lookup(keys, vals, locs, tv - thw - pad, tv + thw + pad)
        uniq = list(dict.fromkeys(hits))
        ctx_words = _words(it["context"])
        uniq.sort(key=lambda h: (RANK[h[3]], -len(ctx_words & _words(h[0] + " " + h[2]))))
        src_files = list(dict.fromkeys(h[0] for h in uniq if h[3] in ("data", "code")))
        if not uniq:
            status = "orphan"
        elif not src_files:
            status = "text-only"
        elif len(src_files) <= 5:
            status = "traced"
        else:
            status = "ambiguous"
        rows.append({"id": it["id"], "loc": f"{it['file']}:{it['line']}", "region": it["region"], "raw": it["raw"],
                     "status": status, "match": how, "n_hits": len(uniq), "n_source_files": len(src_files),
                     "candidates": [f"[{h[3]}] {h[0]}:{h[1]}  {h[2]}" for h in uniq[:5]],
                     "context": it["context"][:140]})
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "trace.json"), "w", encoding="utf-8") as fh:
        json.dump({"repo": repo, "files_indexed": nfiles, "skipped_large": skipped, "rows": rows}, fh,
                  ensure_ascii=False, indent=1)
    order = ("orphan", "text-only", "traced", "ambiguous")
    cnt = {st: sum(1 for r in rows if r["status"] == st) for st in order}
    lines = [f"# Trace: {len(rows)} numbers against {nfiles} files in `{repo}`", "",
             " · ".join(f"{k} {v}" for k, v in cnt.items()), "",
             "Candidates are ranked data > code > text. 'text-only' means the value occurs only in other documents "
             "(copies of the paper, notes), not in any data file or script: treat it like an orphan.", ""]
    if skipped:
        lines += ["Skipped (larger than limit): " + ", ".join(skipped[:20]), ""]
    notes = {"orphan": "Not found anywhere at the displayed precision. Recompute it, or record its derivation.",
             "text-only": "Only in other documents. Find or write the computation that produces it.",
             "traced": "Open the candidate and confirm it is the right quantity, setting and convention.",
             "ambiguous": "The value is common in the repo. Identify the true source by context."}
    for status in order:
        sel = [r for r in rows if r["status"] == status]
        if not sel:
            continue
        lines += [f"## {status} ({len(sel)})", "", notes[status], "",
                  "| id | loc | region | raw | match | hits | first candidates | context |",
                  "|---|---|---|---|---|---|---|---|"]
        for r in sel:
            cands = "<br>".join(c.replace("|", "\\|")[:120] for c in r["candidates"][:3])
            lines.append(f"| {r['id']} | {r['loc']} | {r['region']} | {r['raw'].replace('|', '\\|')} | {r['match']} | "
                         f"{r['n_hits']} | {cands} | {r['context'].replace('|', '\\|')} |")
        lines.append("")
    with open(os.path.join(out, "trace.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(" ".join(f"{k} {v}," for k, v in cnt.items()) + f" ({nfiles} files indexed) -> {out}/trace.md")


# ---------------------------------------------------------------------------
# statistical consistency (statcheck-style)
# ---------------------------------------------------------------------------
PV = (r"p\s*(?P<prel>[<>=≤≥])\s*(?P<pval>(?:\d*\.\d+|\d+)\s*(?:[×x]\s*10\s*\^?\s*[-−]\s*\d+|[eE]-\d+)"
      r"|\d*\.\d+|1|0)")
STAT_RX = {
    "t": re.compile(r"(?<![A-Za-z])t\s*\(\s*(?P<df>\d+(?:\.\d+)?)\s*\)\s*=\s*(?P<stat>-?\d*\.?\d+)\s*[,;]\s*" + PV),
    "F": re.compile(r"(?<![A-Za-z])F\s*\(\s*(?P<df1>\d+(?:\.\d+)?)\s*,\s*(?P<df2>\d+(?:\.\d+)?)\s*\)\s*=\s*"
                    r"(?P<stat>\d*\.?\d+)\s*[,;]\s*" + PV),
    "chi2": re.compile(r"(?:χ\s*2|χ²|[Cc]hi-?squared?|X\s*2)\s*\(\s*(?P<df>\d+)(?:\s*,\s*[Nn]\s*=\s*\d+)?\s*\)\s*=\s*"
                       r"(?P<stat>\d*\.?\d+)\s*[,;]\s*" + PV),
    "r": re.compile(r"(?<![A-Za-z])r\s*\(\s*(?P<df>\d+)\s*\)\s*=\s*(?P<stat>-?\d*\.?\d+)\s*[,;]\s*" + PV),
    "z": re.compile(r"(?<![A-Za-z])[zZ]\s*=\s*(?P<stat>-?\d*\.?\d+)\s*[,;]\s*" + PV),
}
PCT_RX = re.compile(r"(?P<k>\d+)\s*(?:/|of|out of)\s*(?P<n>\d+)\s*\(\s*(?P<pct>\d+(?:\.\d+)?)\s*%\s*\)")
RATIO_RX = re.compile(r"\b(?P<m>a?OR|RR|a?HR|IRR|PR|RRR)\s*[=:]?\s*(?P<pt>\d+\.?\d*)\s*[,;(\[]?\s*(?:95\s*%\s*)?"
                      r"(?:CI|confidence interval)[:,]?\s*[\[(]?\s*(?P<lo>\d+\.?\d*)\s*(?:[-–—]|to|,)\s*(?P<hi>\d+\.?\d*)")


def _p_value(s: str) -> tuple[float, float]:
    """reported p -> (value, half rounding width)"""
    s = s.replace(" ", "")
    s = s.replace("−", "-")
    m = re.match(r"(\d*\.?\d+)(?:[×x]10\^?-(\d+)|[eE]-(\d+))?$", s)
    if not m:
        return float("nan"), 0.0
    mant, e = m.group(1), m.group(2) or m.group(3)
    dec = _decimals(mant)
    if e:
        return float(mant) * 10 ** -int(e), 0.5 * 10 ** (-dec - int(e))
    return float(mant), 0.5 * 10 ** -dec


def _pfun(kind: str, g: dict):
    if kind == "t":
        return lambda x, two=True: statsutil.p_t(x, float(g["df"]), two)
    if kind == "F":
        return lambda x, two=True: statsutil.p_f(x, float(g["df1"]), float(g["df2"]))
    if kind == "chi2":
        return lambda x, two=True: statsutil.p_chi2(x, float(g["df"]))
    if kind == "r":
        return lambda x, two=True: statsutil.p_r(x, float(g["df"]), two)
    return lambda x, two=True: statsutil.p_z(x, two)


def _consistent(rel: str, pr: float, hp: float, lo: float, hi: float) -> bool:
    if rel in ("=",):
        return not (hi < pr - hp - 1e-12 or lo > pr + hp + 1e-12)
    if rel in ("<", "≤"):
        return lo < pr + (1e-12 if rel == "≤" else 0)
    return hi > pr - (1e-12 if rel == "≥" else 0)


def stats_check(main: str, alpha: float = 0.05) -> list[dict]:
    src, kind = load_document(main)
    text = src.text
    if kind == "tex":
        t = strip_comments_keep(text)
        for a, b in ((r"\\chi\s*\^\s*\{?\s*2\s*\}?", "χ2"), (r"\\times", "×"), (r"\\(?:leq|le)\b", "≤"),
                     (r"\\(?:geq|ge)\b", "≥"), (r"\\(?:left|right|mathit|mathrm|textit|it)\b", ""),
                     (r"\\[,;!:]", " "), (r"\\%", "%"), (r"---?", "–"), (r"[${}]", "")):
            t = re.sub(a, b, t)
    else:
        t = text.translate(PLAIN_TR)
    rows = []
    for kind_s, rx in STAT_RX.items():
        for m in rx.finditer(t):
            g = m.groupdict()
            stat_s = g["stat"]
            x = abs(float(stat_s))
            hs = 0.5 * 10 ** -_decimals(stat_s)
            f = _pfun(kind_s, g)
            lo_x, hi_x = x + hs, max(0.0, x - hs)
            p_lo, p_hi = f(lo_x), f(hi_x)
            p_c = f(x)
            pr, hp = _p_value(g["pval"])
            rel = g["prel"]
            ok = _consistent(rel, pr, hp, p_lo, p_hi)
            note = ""
            if not ok and kind_s in ("t", "z", "r"):
                if _consistent(rel, pr, hp, f(lo_x, False), f(hi_x, False)):
                    note = "consistent only if one-tailed"
            reported_sig = (rel in ("<", "≤") and pr <= alpha) or (rel == "=" and pr <= alpha)
            computed_sig = p_c <= alpha
            gross = (not ok) and (reported_sig != computed_sig) and not note
            line = text.count("\n", 0, 0)  # placeholder
            ln_idx = t.count("\n", 0, m.start())
            fl, ln = src.loc(ln_idx)
            rows.append({"loc": f"{fl}:{ln}", "test": kind_s, "reported": re.sub(r"\s+", " ", m.group(0)),
                         "computed_p": p_c, "computed_range": [p_lo, p_hi],
                         "status": "ok" if ok else ("GROSS (significance flips)" if gross else
                                                    ("one-tailed?" if note else "INCONSISTENT")),
                         "note": note})
    for m in PCT_RX.finditer(t):
        k, n, pct = int(m.group("k")), int(m.group("n")), m.group("pct")
        if n == 0 or k > n:
            continue
        exp = 100.0 * k / n
        ok = abs(exp - float(pct)) <= 0.5 * 10 ** -_decimals(pct) + 1e-9
        fl, ln = src.loc(t.count("\n", 0, m.start()))
        rows.append({"loc": f"{fl}:{ln}", "test": "k/n %", "reported": m.group(0), "computed_p": None,
                     "computed_range": [round(exp, 3)], "status": "ok" if ok else "INCONSISTENT",
                     "note": f"{k}/{n} = {exp:.2f}%"})
    for m in RATIO_RX.finditer(t):
        pt, lo, hi = float(m.group("pt")), float(m.group("lo")), float(m.group("hi"))
        fl, ln = src.loc(t.count("\n", 0, m.start()))
        issues = []
        if not (lo <= pt <= hi):
            issues.append("point estimate outside the CI")
        if lo >= hi:
            issues.append("lower bound >= upper bound")
        if lo > 0 and hi > 0 and pt > 0 and lo < pt < hi:
            mid = math.exp((math.log(lo) + math.log(hi)) / 2)
            tol = 0.5 * 10 ** -min(_decimals(m.group("lo")), _decimals(m.group("hi")), _decimals(m.group("pt"))) * 3
            if abs(mid - pt) > max(tol, 0.06 * pt):
                issues.append(f"asymmetric on the log scale (geometric mid of CI {mid:.2f}); check")
        rows.append({"loc": f"{fl}:{ln}", "test": m.group("m") + " CI", "reported": m.group(0), "computed_p": None,
                     "computed_range": [], "status": "ok" if not issues else "CHECK", "note": "; ".join(issues)})
    return rows


def write_stats(rows: list[dict], out: str, main: str):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "stats.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    bad = [r for r in rows if r["status"] != "ok"]
    lines = [f"# Statistical consistency: `{main}`", "",
             f"{len(rows)} reported results recognised; {len(bad)} need attention.", "",
             "Recomputes p from the reported test statistic and degrees of freedom (two-tailed unless noted), "
             "allowing for rounding of both; checks k/n percentages and ratio-measure CIs. Only APA-like inline "
             "reports are recognised (e.g. t(23) = 2.45, p = .02); results in tables need a manual check.", "",
             "| status | loc | test | reported | recomputed | note |", "|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["status"] == "ok", r["loc"])):
        rec = ""
        if r["computed_p"] is not None:
            lo, hi = r["computed_range"]
            rec = f"p = {r['computed_p']:.4g} (range {lo:.3g}–{hi:.3g})"
        elif r["computed_range"]:
            rec = str(r["computed_range"][0]) + "%"
        lines.append(f"| {r['status']} | {r['loc']} | {r['test']} | {r['reported'].replace('|', '/')} | {rec} | "
                     f"{r['note']} |")
    with open(os.path.join(out, "stats.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"{len(rows)} statistical results, {len(bad)} flagged -> {out}/stats.md")


# ---------------------------------------------------------------------------
# guards: keep audited numbers tied to their sources on every rerun
# ---------------------------------------------------------------------------
from decimal import Decimal, ROUND_HALF_UP  # noqa: E402

KEY_REGIONS = ("title", "abstract", "introduction", "conclusion", "caption", "table", "theorem")


def _raw_anchor(main_dir: str, file: str, line: int, raw: str) -> str:
    path = os.path.join(main_dir, file.split(" ")[0]) if not file.endswith("¶") else None
    if not path or not os.path.isfile(path):
        return ""
    lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    chunk = " ".join(lines[max(0, line - 3):line])
    chunk = re.sub(r"(?<!\\)%[^\n]*", " ", chunk)
    first = re.escape(raw.split("=")[-1].split()[0]) if raw else ""
    m = None
    for m in re.finditer(first, chunk):
        pass
    before = chunk[:m.start()] if m else chunk
    before = re.sub(r"\\[A-Za-z]+|\$[^$]*\$", " ", before)
    words = re.findall(r"[A-Za-z]{3,}", before)
    return " ".join(words[-3:])


def guard_init(numbers_json: str, out: str, regions: list[str] | None):
    res = json.load(open(numbers_json, encoding="utf-8"))
    main_dir = os.path.dirname(os.path.abspath(res["main"]))
    want = regions or list(KEY_REGIONS)
    entries = []
    for it in res["items"]:
        if it["kind"] in ("small", "year-like") or not any(it["region"].startswith(r) for r in want):
            continue
        display = it["raw"].split("=", 1)[1] if it["macro"] else it["raw"]
        display = display.replace("{,}", ",").replace("\\%", "%")
        num = re.search(r"\d[\d,]*(?:\.\d+)?", display)
        decimals = len(num.group(0).split(".")[1]) if num and "." in num.group(0) else 0
        entries.append({
            "id": it["id"], "where": f"{it['file']}:{it['line']} ({it['region']})", "display": display,
            "anchor": _raw_anchor(main_dir, it["file"], it["line"], it["raw"]) if not it["macro"] else "",
            "macro": it["macro"], "source": None, "locator": None, "scale": 1, "decimals": decimals,
            "thousands": bool(num and "," in num.group(0)), "suffix": "%" if display.endswith("%") else "",
            "note": "", "context": it["context"][:160],
        })
    doc = {"manuscripts": res.get("mains", [res["main"]]),
           "help": "Fill source + locator for each entry you want enforced. locator: JSON path 'a.b[0].c', "
                   "CSV 'row=<col>:<value>;col=<name>' or 'row=<index>;col=<name>', regex 're:<pattern with one "
                   "group>', or 'const:<value>'. Entries without a source are reported as UNSOURCED. Add corrected "
                   "values that must never reappear to 'stale'. Do not guard wall-clock times.",
           "stale": [], "entries": entries}
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print(f"{len(entries)} guard entries -> {out} (fill 'source' and 'locator', then run guard-check)")


def _locate(source: str, locator: str, base: str):
    if locator.startswith("const:"):
        return float(locator[6:])
    path = source if os.path.isabs(source) else os.path.join(base, source)
    if locator.startswith("re:"):
        m = re.search(locator[3:], open(path, encoding="utf-8", errors="replace").read(), re.M)
        if not m:
            raise ValueError("regex did not match")
        return float(m.group(1).replace(",", ""))
    if locator.startswith("row="):
        import csv
        parts = dict(p.split("=", 1) for p in locator.split(";"))
        rows = list(csv.DictReader(open(path, encoding="utf-8", errors="replace")))
        rk = parts["row"]
        if ":" in rk:
            kc, kv = rk.split(":", 1)
            row = next(r for r in rows if str(r.get(kc)) == kv)
        else:
            row = rows[int(rk)]
        return float(str(row[parts["col"]]).replace(",", ""))
    obj = json.load(open(path, encoding="utf-8"))
    for tok in re.findall(r"[^.\[\]]+", locator.lstrip("$.")):
        obj = obj[int(tok)] if isinstance(obj, list) else obj[tok]
    return float(obj)


def _render(v: float, e: dict) -> str:
    d = Decimal(str(v)) * Decimal(str(e.get("scale", 1)))
    q = Decimal(1).scaleb(-int(e.get("decimals", 0)))
    d = d.quantize(q, rounding=ROUND_HALF_UP)
    txt = f"{d:,}" if e.get("thousands") else f"{d}"
    return txt + e.get("suffix", "")


def _num_rx(txt: str) -> str:
    core = re.escape(txt).replace(",", "(?:,|\\{,\\})").replace("%", "\\\\?%")
    return r"(?<![0-9.,])" + core + r"(?![0-9])"


def guard_check(guards_json: str, manuscripts: list[str] | None, strict: bool) -> int:
    g = json.load(open(guards_json, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(guards_json))
    mans = manuscripts or g.get("manuscripts", [])
    text = ""
    for m in mans:
        mp = m if os.path.isabs(m) or os.path.exists(m) else os.path.join(base, m)
        src, kind = load_document(mp)
        t = src.text
        if kind == "tex":
            t = strip_comments_keep(t)
        text += "\n" + t
    norm = re.sub(r"\s+", " ", text.translate(PLAIN_TR))
    counts = {"PASS": 0, "FAIL": 0, "ANCHOR_MISSING": 0, "UNSOURCED": 0, "SOURCE_ERROR": 0, "STALE_PRESENT": 0}
    rows = []
    for e in g.get("entries", []):
        if not e.get("source") and not str(e.get("locator") or "").startswith("const:"):
            counts["UNSOURCED"] += 1
            continue
        try:
            expected = _render(_locate(e.get("source") or "", e["locator"], base), e)
        except Exception as exc:  # report and continue
            counts["SOURCE_ERROR"] += 1
            rows.append(("SOURCE_ERROR", e, f"{type(exc).__name__}: {exc}"))
            continue
        if e.get("macro"):
            # a macro value is checked in the macro definition file instead of the prose
            hit = re.search(re.escape(e["macro"]) + r"\}?\s*\{(?:[^{}]*\{[^{}]*\})*[^{}]*?" + _num_rx(expected), norm)
            status = "PASS" if hit else "FAIL"
            rows.append((status, e, f"expected {expected} in the definition of {e['macro']}"))
            counts[status] += 1
            continue
        words = [w for w in (e.get("anchor") or "").split() if w]
        found_anchor = False
        ok = False
        for m in re.finditer(_num_rx(expected), norm):
            window = norm[max(0, m.start() - 220):m.start()]
            if all(w in window for w in words):
                ok = True
                break
        if not ok and words:
            arx = r"\W+(?:\S+\W+){0,3}?".join(re.escape(w) for w in words)
            am = re.search(arx, norm)
            found_anchor = bool(am)
            nearby = ""
            if am:
                nm = re.search(r"(?<![0-9.])\d[\d,]*(?:\.\d+)?", norm[am.end():am.end() + 220])
                nearby = nm.group(0) if nm else ""
            status = "FAIL" if found_anchor else "ANCHOR_MISSING"
            rows.append((status, e, f"expected {expected}" + (f", found {nearby} after the anchor" if nearby else "")))
        elif not ok:
            status = "FAIL"
            rows.append((status, e, f"expected {expected} not found"))
        else:
            status = "PASS"
        counts[status] += 1
    for sv in g.get("stale", []):
        rx = _num_rx(sv) if re.fullmatch(r"[\d.,%]+", sv) else re.escape(sv)
        if re.search(rx, norm):
            counts["STALE_PRESENT"] += 1
            rows.append(("STALE_PRESENT", {"id": "-", "where": "-", "display": sv}, "a corrected value reappeared"))
    print("guard-check: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    for status, e, msg in rows:
        print(f"  {status:14} {e.get('id')} {e.get('where')} [{e.get('display')}] {msg}")
    bad = counts["FAIL"] + counts["SOURCE_ERROR"] + counts["STALE_PRESENT"] + (counts["ANCHOR_MISSING"] if strict else 0)
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("main", nargs="+", help="one or more top-level .tex files (e.g. main.tex supplement.tex)")
    e.add_argument("--out", required=True)
    e.add_argument("--all", action="store_true", help="also keep small integers and year-like numbers")
    t = sub.add_parser("trace")
    t.add_argument("numbers_json")
    t.add_argument("--repo", required=True)
    t.add_argument("--regions", help="comma list of region prefixes, e.g. abstract,introduction,caption,table,theorem")
    t.add_argument("--exclude", nargs="*", default=[], help="glob patterns (relative paths or file names) to skip")
    t.add_argument("--max-mb", type=float, default=30)
    t.add_argument("--out")
    gi = sub.add_parser("guard-init", help="create a guard file from numbers.json")
    gi.add_argument("numbers_json")
    gi.add_argument("--out", required=True)
    gi.add_argument("--regions", help="comma list of region prefixes (default: title,abstract,introduction,"
                                      "conclusion,caption,table,theorem)")
    gc = sub.add_parser("guard-check", help="recompute guarded numbers from their sources and check the manuscript")
    gc.add_argument("guards_json")
    gc.add_argument("--manuscript", nargs="*")
    gc.add_argument("--strict", action="store_true", help="also fail on ANCHOR_MISSING")
    st = sub.add_parser("stats")
    st.add_argument("main", nargs="+")
    st.add_argument("--out", required=True)
    st.add_argument("--alpha", type=float, default=0.05)
    args = ap.parse_args(argv)
    if args.cmd == "guard-init":
        guard_init(args.numbers_json, args.out, args.regions.split(",") if args.regions else None)
        return
    if args.cmd == "guard-check":
        sys.exit(guard_check(args.guards_json, args.manuscript, args.strict))
    if args.cmd == "stats":
        rows = []
        for m in args.main:
            rows += stats_check(m, args.alpha)
        write_stats(rows, args.out, ", ".join(args.main))
        return
    if args.cmd == "extract":
        write_extract(extract_many(args.main, args.all), args.out)
    else:
        trace(args.numbers_json, args.repo, args.regions.split(",") if args.regions else None, args.exclude,
              args.max_mb, args.out or os.path.dirname(os.path.abspath(args.numbers_json)))


if __name__ == "__main__":
    main()
