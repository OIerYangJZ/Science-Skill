#!/usr/bin/env python3
"""refcheck.py - verify bibliography metadata against Crossref / arXiv / OpenAlex.

Subcommands
  check REFS.bib [--tex MAIN.tex ...] [--all] --out DIR
      For each entry (only cited ones when --tex is given, unless --all):
        DOI      -> Crossref record (arXiv DOIs 10.48550/... go to arXiv)
        eprint   -> arXiv record (and its journal version, if any)
        neither  -> Crossref bibliographic search, then arXiv title search
      Compares title, authors, year, venue, volume, pages/article number;
      flags retractions/corrections (Crossref 'updated-by'), preprints that
      have since been published, and missing DOIs.
      Writes DIR/report.md, DIR/results.json, DIR/corrected.bib (proposals
      only; the user's .bib is never modified), and key-level problems
      (cited but undefined, defined but uncited).

  check-list MANUSCRIPT_OR_LIST --out DIR
      Free-text references in any citation style: the reference section of a
      .docx / .pdf / .md / .txt manuscript, a .tex thebibliography, or a plain
      list. Each string goes to Crossref's bibliographic search (then arXiv,
      Europe PMC); year, volume, first page, authors and venue are checked for
      presence in the string. RIS files (Zotero/EndNote export) go to `check`.

  contexts MAIN [--keys k1,k2] --out DIR
      .tex: \\cite keys. Other formats: numeric [n] and author-year citations.
      Writes DIR/contexts.md: every sentence that cites each key, with
      file:line and region, for checking that the source supports the claim.

Network: Crossref, arXiv and OpenAlex public APIs only. Run with python3 -I.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

LIB = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "lib")
sys.path.insert(0, os.path.normpath(LIB))
import bibtex  # noqa: E402
import scholarly as sch  # noqa: E402
from texutil import (  # noqa: E402
    _line_of, clean_latex, doc_region_labeler, doc_sections, find_cites, light_clean, load_document, read_tex,
    region_labeler, sentences,
)

ERROR, WARN, INFO = "ERROR", "WARN", "INFO"
BOOKISH = {"book", "inbook", "incollection", "misc", "phdthesis", "mastersthesis", "techreport", "manual", "online",
           "software", "unpublished", "booklet"}
BOOK_TYPES = {"book", "monograph", "edited-book", "reference-book", "book-chapter", "book-part", "book-section",
              "book-series", "book-set", "dissertation", "report", "standard"}
CLAIM_VERBS = re.compile(
    r"\b(show(?:s|ed|n)?|prov(?:e|es|ed|en)|demonstrat\w+|establish\w*|f(?:ou|i)nds?|report\w*|achiev\w+|"
    r"reduc\w+|improv\w+|requir\w+|is known|are known|introduc\w+|first|best|optimal|lower bound|upper bound)\b",
    re.I)


# ---------------------------------------------------------------------------
# normalisation
# ---------------------------------------------------------------------------
def venue_key(s: str) -> str:
    s = bibtex.latex_to_text(s or "")
    s = re.sub(r"[^A-Za-z0-9 ]+", " ", s)
    words = [w for w in s.split() if w.lower() not in {"of", "the", "and", "on", "in", "for", "journal"}]
    return " ".join(w[:3].lower() for w in words)


def venue_same(a: str, b: str) -> bool:
    if not a or not b:
        return False
    ka, kb = set(venue_key(a).split()), set(venue_key(b).split())
    if not ka or not kb:
        return False
    if venue_key(a) == venue_key(b):
        return True
    inter = len(ka & kb)
    return inter / min(len(ka), len(kb)) >= 0.8


def pages_key(s: str) -> str:
    s = (s or "").replace("--", "-").replace("–", "-")
    first = s.split("-")[0]
    return re.sub(r"[^0-9A-Za-z]", "", first).lstrip("0").lower()


def first_author_ok(bib_first: str, cr_item: dict) -> bool:
    if not bib_first:
        return True
    au = cr_item.get("author") or []
    if not au:
        return True
    rf = bibtex.norm_name(au[0].get("family") or au[0].get("name") or "")
    bf = bibtex.norm_name(bib_first)
    return bool(rf) and (rf == bf or rf.split()[-1:] == bf.split()[-1:] or rf in bf or bf in rf)


def record_from_crossref(cr: dict) -> dict:
    authors = []
    for a in cr.get("author") or []:
        if a.get("family"):
            authors.append((a.get("family", ""), a.get("given", "")))
        elif a.get("name"):
            authors.append((a["name"], ""))
    return {
        "source": "Crossref",
        "title": (cr.get("title") or [""])[0],
        "authors": authors,
        "years": sorted(sch.crossref_years(cr)),
        "year": sch.crossref_year(cr),
        "venue": (cr.get("container-title") or [""])[0],
        "venue_short": (cr.get("short-container-title") or [""])[0],
        "volume": cr.get("volume", ""),
        "pages": cr.get("article-number") or cr.get("page", ""),
        "doi": cr.get("DOI", ""),
        "type": cr.get("type", ""),
        "updates": sch.crossref_updates(cr),
    }


def record_from_datacite(dc: dict, doi: str) -> dict:
    authors = []
    for c in dc.get("creators") or []:
        if c.get("familyName"):
            authors.append((c["familyName"], c.get("givenName", "")))
        elif c.get("name"):
            nm = c["name"]
            authors.append((nm.split(",")[0].strip(), nm.split(",")[1].strip() if "," in nm else ""))
    cont = dc.get("container") or {}
    pub = dc.get("publisher")
    y = dc.get("publicationYear")
    return {
        "source": "DataCite", "title": ((dc.get("titles") or [{}])[0]).get("title", ""), "authors": authors,
        "years": [int(y)] if y else [], "year": int(y) if y else None,
        "venue": cont.get("title") or (pub if isinstance(pub, str) else (pub or {}).get("name", "")),
        "venue_short": "", "volume": cont.get("volume", ""), "pages": cont.get("firstPage", ""), "doi": doi,
        "type": (dc.get("types") or {}).get("resourceTypeGeneral", ""), "updates": [],
    }


def record_from_arxiv(ax: dict) -> dict:
    authors = []
    for name in ax["authors"]:
        parts = name.split()
        authors.append((parts[-1] if parts else name, " ".join(parts[:-1])))
    return {
        "source": "arXiv", "title": ax["title"], "authors": authors,
        "years": [int(ax["published"][:4])] if ax.get("published") else [],
        "year": int(ax["published"][:4]) if ax.get("published") else None,
        "venue": "", "venue_short": "", "volume": "", "pages": "",
        "doi": ax.get("doi", ""), "journal_ref": ax.get("journal_ref", ""), "arxiv": ax["id"], "updates": [],
    }


def arxiv_id_of(fields: dict) -> str | None:
    for k in ("eprint", "arxiv", "arxivid"):
        if fields.get(k):
            m = sch.ARXIV_ID.search(fields[k])
            if m:
                return m.group(1)
    doi = fields.get("doi", "")
    m = re.match(r"10\.48550/arxiv\.(.+)$", doi, re.I)
    if m:
        return m.group(1)
    for k in ("journal", "note", "url", "howpublished", "archiveprefix"):
        v = fields.get(k, "")
        m = re.search(r"arxiv[:/ ]*(?:abs/)?(\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})", v, re.I)
        if m:
            return m.group(1)
    return None


# ---------------------------------------------------------------------------
# verification of one entry
# ---------------------------------------------------------------------------
def compare(entry: dict, rec: dict) -> list[tuple[str, str, str]]:
    f = entry["fields"]
    issues = []
    btitle = bibtex.latex_to_text(f.get("title", ""))
    r = sch.title_ratio(btitle, rec["title"])
    if btitle and not sch.titles_match(btitle, rec["title"]):
        issues.append((ERROR, "TITLE_MISMATCH", f"bib: {btitle!r} | record: {rec['title']!r} (ratio {r:.2f})"))
    bauth_raw = bibtex.split_authors(f.get("author", ""))
    has_others = any(a.lower() in ("others", "{others}") for a in bauth_raw)
    bfam = [bibtex.norm_name(bibtex.family_name(a)) for a in bauth_raw if a.lower() not in ("others", "{others}")]
    rfam = [bibtex.norm_name(a[0]) for a in rec["authors"]]
    if bfam and rfam:
        def same(x, y):
            return x == y or x.split()[-1:] == y.split()[-1:] or x in y or y in x
        if not same(bfam[0], rfam[0]):
            issues.append((ERROR, "FIRST_AUTHOR", f"bib: {bfam[0]} | record: {rfam[0]}"))
        missing = [b for b in bfam if not any(same(b, x) for x in rfam)]
        extra = [x for x in rfam if not any(same(b, x) for b in bfam)]
        if missing:
            issues.append((ERROR, "AUTHOR_NOT_IN_RECORD", ", ".join(missing)))
        if extra and not has_others:
            sev = ERROR if len(rfam) <= 12 else WARN
            issues.append((sev, "AUTHOR_MISSING_FROM_BIB",
                           f"{len(bfam)} in bib vs {len(rfam)} in record; missing: " + ", ".join(extra[:6])
                           + (" ..." if len(extra) > 6 else "")))
    by = re.search(r"\d{4}", f.get("year", "") or f.get("date", ""))
    if by and rec["years"]:
        y = int(by.group(0))
        if y not in rec["years"]:
            near = min(abs(y - z) for z in rec["years"])
            issues.append((WARN if near <= 1 else ERROR, "YEAR_MISMATCH",
                           f"bib {y} | record {', '.join(map(str, rec['years']))}"))
    bven = f.get("journal") or f.get("booktitle") or ""
    if bven and rec["venue"] and not re.search(r"arxiv|preprint", bven, re.I):
        if not venue_same(bven, rec["venue"]) and not venue_same(bven, rec["venue_short"]):
            sev = INFO if (f.get("booktitle") and not f.get("journal")) else ERROR
            issues.append((sev, "VENUE_MISMATCH", f"bib: {bibtex.latex_to_text(bven)} | record: {rec['venue']}"))
    if f.get("volume") and rec["volume"] and str(f["volume"]).strip() != str(rec["volume"]).strip():
        issues.append((ERROR, "VOLUME_MISMATCH", f"bib {f['volume']} | record {rec['volume']}"))
    bp = f.get("pages") or f.get("eid") or ""
    if bp and rec["pages"] and pages_key(bp) != pages_key(rec["pages"]):
        rng_b = bool(re.search(r"\d\s*[-–]+\s*\d", bp)) and ":" not in bp
        rng_r = bool(re.search(r"\d\s*[-–]+\s*\d", str(rec["pages"])))
        if rng_b == rng_r:
            issues.append((ERROR, "PAGES_MISMATCH", f"bib {bp} | record {rec['pages']}"))
        else:
            issues.append((INFO, "PAGES_FORM", f"bib {bp} | record {rec['pages']} (article number vs page range)"))
    if not f.get("doi") and rec.get("doi") and rec["source"] == "Crossref":
        issues.append((INFO, "MISSING_DOI", rec["doi"]))
    for u in rec.get("updates", []):
        if u.startswith("retraction") or u.startswith("withdrawal"):
            issues.append((ERROR, "RETRACTED", u))
        else:
            issues.append((WARN, "HAS_UPDATE", u))
    return issues


def verify(entry: dict) -> dict:
    f = entry["fields"]
    out = {"key": entry["key"], "line": entry["line"], "type": entry["type"], "issues": [], "record": None,
           "via": ""}
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", f.get("doi", "").strip(), flags=re.I)
    aid = arxiv_id_of(f)
    title = bibtex.latex_to_text(f.get("title", ""))
    first = bibtex.family_name(bibtex.split_authors(f.get("author", ""))[0]) if f.get("author") else ""
    rec = None
    if doi and not doi.lower().startswith("10.48550/"):
        cr = sch.crossref(doi)
        if cr:
            rec, out["via"] = record_from_crossref(cr), "DOI"
        else:
            dc = sch.datacite(doi)
            if dc:
                rec, out["via"] = record_from_datacite(dc, doi), "DOI (DataCite)"
            elif sch.doi_resolves(doi):
                out["issues"].append((INFO, "DOI_NO_METADATA", f"{doi} resolves at doi.org but has no Crossref/"
                                                               "DataCite metadata; fields not compared"))
                return out
            else:
                out["issues"].append((ERROR, "DOI_NOT_FOUND", doi))
    if rec is None and aid:
        ax = sch.arxiv_meta(aid)
        if ax:
            rec, out["via"] = record_from_arxiv(ax), "arXiv id"
            venue = f.get("journal") or f.get("booktitle") or ""
            published = ax.get("doi") or ax.get("journal_ref")
            if published and (not venue or re.search(r"arxiv|preprint", venue, re.I)):
                out["issues"].append((WARN, "PREPRINT_PUBLISHED",
                                      f"journal version: {ax.get('journal_ref') or ''} doi:{ax.get('doi') or '-'}"))
                if ax.get("doi"):
                    cr = sch.crossref(ax["doi"])
                    if cr:
                        out["journal_record"] = record_from_crossref(cr)
            if venue and not re.search(r"arxiv|preprint", venue, re.I):
                cr = sch.crossref(ax["doi"]) if ax.get("doi") else None
                if cr:
                    rec, out["via"] = record_from_crossref(cr), "arXiv -> journal DOI"
                else:
                    for item in sch.crossref_search(title or ax["title"], first, rows=5):
                        if sch.titles_match(title or ax["title"], (item.get("title") or [""])[0]) and \
                                item.get("type") != "posted-content" and first_author_ok(first, item):
                            rec, out["via"] = record_from_crossref(item), "arXiv id + journal title search"
                            break
        else:
            out["issues"].append((ERROR, "EPRINT_NOT_FOUND", aid))
    if rec is None and title:
        best, br = None, 0.0
        for item in sch.crossref_search(title, first, rows=5):
            t = (item.get("title") or [""])[0]
            if not (sch.titles_match(title, t) and first_author_ok(first, item)):
                continue
            r = sch.title_ratio(title, t)
            if r > br:
                best, br = item, r
        bookish = entry["type"] in BOOKISH
        if best and br >= 0.9 and bookish and best.get("type") not in BOOK_TYPES:
            out["issues"].append((INFO, "BOOK_NOT_VERIFIED", f"closest Crossref record with this title is a "
                                                             f"{best.get('type')} ({best.get('DOI')}); check by hand"))
            return out
        if best and br >= 0.9:
            rec, out["via"] = record_from_crossref(best), f"title search (Crossref, ratio {br:.2f})"
        else:
            hit = sch.arxiv_search_title(title)
            if hit:
                ax = sch.arxiv_meta(hit["id"])
                if ax:
                    rec, out["via"] = record_from_arxiv(ax), f"title search (arXiv, ratio {hit['ratio']:.2f})"
                    out["issues"].append((INFO, "ARXIV_ID_AVAILABLE", hit["id"]))
    if rec is None:
        out["issues"].append((ERROR, "NOT_FOUND", "no record by DOI, arXiv id or title; possibly fabricated "
                                                  "or very obscure: check by hand"))
        return out
    if rec["source"] == "Crossref" and rec["title"]:
        for item in sch.crossref_search("Erratum " + rec["title"], rows=4):
            t = (item.get("title") or [""])[0]
            m = re.match(r"\s*(erratum|corrigendum|publisher'?s note|correction|addendum)\s*[:\-]?\s*(.*)", t, re.I)
            if m and sch.title_ratio(m.group(2), rec["title"]) >= 0.9 and item.get("DOI") != rec["doi"]:
                cy = sch.crossref_year(item)
                out["issues"].append((WARN, "HAS_ERRATUM", f"{m.group(1)} {item.get('DOI')} ({cy}): check whether "
                                                           "it changes what you cite"))
    out["record"] = rec
    if rec["source"] == "arXiv" and (f.get("journal") and not re.search(r"arxiv|preprint", f["journal"], re.I)):
        # compare bibliographic fields only against a journal record
        f2 = dict(f)
        for k in ("journal", "volume", "pages", "year"):
            f2.pop(k, None)
        out["issues"] += compare({"fields": f2}, rec)
        out["issues"].append((INFO, "JOURNAL_FIELDS_UNCHECKED", "only the arXiv record was found; journal, volume, "
                                                                "pages and year not compared"))
    else:
        out["issues"] += compare(entry, rec)
    return out


def proposed_entry(entry: dict, res: dict) -> str | None:
    rec = res.get("journal_record") or res.get("record")
    if not rec:
        return None
    fields = {}
    fields["author"] = " and ".join(f"{fam}, {giv}".strip(", ") for fam, giv in rec["authors"])
    fields["title"] = "{" + rec["title"] + "}"
    if rec["source"] == "Crossref":
        if rec["venue"]:
            fields["journal"] = rec["venue"]
        if rec["volume"]:
            fields["volume"] = rec["volume"]
        if rec["pages"]:
            fields["pages"] = rec["pages"]
    if rec.get("year"):
        fields["year"] = str(rec["year"])
    if rec.get("doi"):
        fields["doi"] = rec["doi"]
    aid = arxiv_id_of(entry["fields"]) or rec.get("arxiv")
    if aid:
        fields["eprint"] = aid
        fields["archiveprefix"] = "arXiv"
    etype = "article" if rec["source"] == "Crossref" and rec.get("type") == "journal-article" else entry["type"]
    return bibtex.format_entry(etype, entry["key"], fields)


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------
def cited_keys(tex_files: list[str]) -> dict[str, list[str]]:
    keys: dict[str, list[str]] = {}
    for t in tex_files:
        src = read_tex(t)
        text = src.text
        for start, end, cmd, ks in find_cites(text):
            f, ln = src.loc(_line_of(text, start))
            for k in ks:
                keys.setdefault(k, []).append(f"{f}:{ln}")
    return keys


def cmd_check(args):
    entries = []
    for b in args.bib:
        with open(b, encoding="utf-8", errors="replace") as fh:
            txt = fh.read()
        entries += bibtex.parse_ris(txt) if b.lower().endswith((".ris", ".txt")) and "TY  -" in txt \
            else bibtex.parse_bib(txt)
    by_key = {e["key"]: e for e in entries}
    cited = cited_keys(args.tex) if args.tex else {}
    if args.tex and not args.all:
        todo = [by_key[k] for k in cited if k in by_key]
    else:
        todo = entries
    os.makedirs(args.out, exist_ok=True)
    results = []
    for n, e in enumerate(todo, 1):
        try:
            r = verify(e)
        except Exception as exc:  # report and continue
            r = {"key": e["key"], "line": e["line"], "issues": [(ERROR, "CHECK_FAILED", f"{type(exc).__name__}: {exc}")],
                 "record": None, "via": ""}
        results.append(r)
        worst = min((i[0] for i in r["issues"]), key=[ERROR, WARN, INFO].index, default="OK")
        print(f"[{n}/{len(todo)}] {worst:5} {e['key']}", file=sys.stderr)
        time.sleep(0.1)
    undefined = sorted(k for k in cited if k not in by_key)
    uncited = sorted(k for k in by_key if args.tex and k not in cited)
    with open(os.path.join(args.out, "results.json"), "w", encoding="utf-8") as fh:
        json.dump({"results": results, "undefined": undefined, "uncited": uncited}, fh, ensure_ascii=False, indent=1)
    props = []
    for r in results:
        if any(i[0] in (ERROR, WARN) for i in r["issues"]) or any(i[1] == "MISSING_DOI" for i in r["issues"]):
            p = proposed_entry(by_key[r["key"]], r)
            if p:
                props.append(f"% proposed for {r['key']} (bib line {r['line']}); via {r['via']}\n{p}\n")
    with open(os.path.join(args.out, "corrected.bib"), "w", encoding="utf-8") as fh:
        fh.write("% Proposals generated from Crossref/arXiv records. Review each before use.\n"
                 "% Keys are kept; titles are braced to keep capitalisation.\n\n" + "\n".join(props))
    counts = {s: sum(1 for r in results if any(i[0] == s for i in r["issues"])) for s in (ERROR, WARN, INFO)}
    ok = sum(1 for r in results if not r["issues"])
    lines = [f"# Bibliography check: {', '.join(args.bib)}", "",
             f"{len(results)} entries checked: {ok} clean, {counts[ERROR]} with errors, {counts[WARN]} with warnings, "
             f"{counts[INFO]} with notes only.", ""]
    if args.tex:
        lines += [f"Cited but not in the .bib ({len(undefined)}): " + (", ".join(undefined) or "none"),
                  f"In the .bib but never cited ({len(uncited)}): " + (", ".join(uncited) or "none"), ""]
    rank = [ERROR, WARN, INFO]

    def worst(r):
        return min((rank.index(i[0]) for i in r["issues"]), default=None)
    for sev in rank:
        sel = [r for r in results if worst(r) == rank.index(sev)]
        if not sel:
            continue
        lines += [f"## {sev} ({len(sel)})", "", "| key | bib line | via | issues | record |", "|---|---|---|---|---|"]
        for r in sel:
            iss = "<br>".join(f"**{c}** {d}".replace("|", "\\|") for s, c, d in r["issues"])
            rec = r.get("record")
            rs = ""
            if rec:
                a1 = rec["authors"][0][0] if rec["authors"] else ""
                rs = f"{a1} et al., {rec['title'][:70]}; {rec['venue'] or 'arXiv'} {rec['volume']} {rec['pages']} " \
                     f"({rec.get('year')}) {rec.get('doi') or ''}".replace("|", "\\|")
            lines.append(f"| {r['key']} | {r['line']} | {r['via']} | {iss} | {rs} |")
        lines.append("")
    lines += ["Proposed replacements for flagged entries: `corrected.bib` (review before use).",
              "A record that matches is evidence the reference exists; it does not show the reference supports "
              "the sentence that cites it (use `contexts`)."]
    with open(os.path.join(args.out, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"{len(results)} checked: {ok} clean, errors {counts[ERROR]}, warnings {counts[WARN]} -> {args.out}/report.md")


def cmd_contexts(args):
    want = set(k.strip() for k in args.keys.split(",")) if args.keys else None
    by_key: dict[str, list[dict]] = {}
    for t in [x for x in args.tex if not x.lower().endswith((".tex", ".ltx"))]:
        for k, v in plain_contexts(t).items():
            if not want or k in want:
                by_key.setdefault(k, []).extend(v)
    for t in [x for x in args.tex if x.lower().endswith((".tex", ".ltx"))]:
        src = read_tex(t)
        text = src.text
        label = region_labeler(text)
        for start, end, cmd, ks in find_cites(text):
            a = max(text.rfind(". ", 0, start), text.rfind(".\n", 0, start), text.rfind("\n\n", 0, start), 0)
            b_candidates = [x for x in (text.find(". ", end), text.find(".\n", end), text.find("\n\n", end)) if x >= 0]
            b = min(b_candidates) + 1 if b_candidates else len(text)
            sent, _ = clean_latex(text[a:b])
            sent = re.sub(r"\s+", " ", sent).strip(" .") + "."
            f, ln = src.loc(_line_of(text, start))
            for k in ks:
                if want and k not in want:
                    continue
                by_key.setdefault(k, []).append({"loc": f"{f}:{ln}", "region": label(start), "sentence": sent,
                                                 "claim": bool(CLAIM_VERBS.search(sent)), "co_cited": len(ks)})
    os.makedirs(args.out, exist_ok=True)
    lines = ["# Citation contexts", "",
             "Each sentence that cites a key. 'claim' marks sentences that attribute a result or property to the "
             "source; check those against the source itself.", ""]
    for k in sorted(by_key):
        lines.append(f"## {k} ({len(by_key[k])})")
        for c in by_key[k]:
            flag = " **claim**" if c["claim"] else ""
            ref = f" ← {c['reference'][:100]}" if c.get("reference") else ""
            lines.append(f"- `{c['loc']}` ({c['region']}, {c['co_cited']} keys){flag}: {c['sentence']}{ref}")
        lines.append("")
    with open(os.path.join(args.out, "contexts.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    with open(os.path.join(args.out, "contexts.json"), "w", encoding="utf-8") as fh:
        json.dump(by_key, fh, ensure_ascii=False, indent=1)
    n_claim = sum(1 for v in by_key.values() for c in v if c["claim"])
    print(f"{len(by_key)} keys, {sum(len(v) for v in by_key.values())} citing sentences, {n_claim} claim-type "
          f"-> {args.out}/contexts.md")


# ---------------------------------------------------------------------------
# plain reference lists (any citation style)
# ---------------------------------------------------------------------------
def _ntoks(s: str) -> list[str]:
    return sch.norm_title(bibtex.latex_to_text(s)).split()


def verify_string(ref: str) -> dict:
    out = {"issues": [], "record": None, "via": ""}
    rtoks = set(_ntoks(ref))
    rnorm = " " + " ".join(_ntoks(ref)) + " "
    cands = []
    dm = re.search(r"\b(10\.\d{4,9}/[^\s,;]+?)[.,;]?(?:\s|$)", ref)
    if dm:
        cr = sch.crossref(dm.group(1))
        if cr:
            cands.append(("DOI in reference", cr))
        else:
            out["issues"].append((ERROR, "DOI_NOT_FOUND", dm.group(1)))
    if not cands:
        cands += [("Crossref bibliographic search", it) for it in sch.crossref_search(ref, rows=5)]

    def coverage(title: str) -> float:
        tt = [t for t in sch.norm_title(title).split() if len(t) > 2 or t.isdigit()]
        return sum(1 for t in tt if t in rtoks) / len(tt) if tt else 0.0
    best, bcov = None, 0.0
    for via, it in cands:
        t = (it.get("title") or [""])[0]
        cov = coverage(t)
        au = it.get("author") or []
        fam = bibtex.norm_name((au[0].get("family") or au[0].get("name") or "")) if au else ""
        if fam and (" " + fam.split()[-1] + " ") not in rnorm:
            cov -= 0.3
        if cov > bcov:
            best, bcov, bvia = it, cov, via
    if best is None or bcov < 0.85:
        am = sch.ARXIV_ID.search(ref) if re.search(r"arxiv", ref, re.I) else None
        if am:
            ax = sch.arxiv_meta(am.group(1))
            if ax:
                out["record"], out["via"] = record_from_arxiv(ax), "arXiv id in reference"
                return out
        epmc = sch.europepmc_search(" ".join(w for w in re.findall(r"[A-Za-z]{4,}", ref)[:14]), n=3)
        for r in epmc:
            if coverage(r.get("title", "")) >= 0.85:
                out["via"] = "Europe PMC search"
                out["record"] = {"source": "Europe PMC", "title": r.get("title", ""), "authors": [
                    (a.get("lastName", a.get("fullName", "")), a.get("firstName", "")) for a in
                    (r.get("authorList") or {}).get("author", [])], "years": [int(r["pubYear"])] if r.get("pubYear") else [],
                    "year": int(r["pubYear"]) if r.get("pubYear") else None,
                    "venue": ((r.get("journalInfo") or {}).get("journal") or {}).get("title", ""), "venue_short": "",
                    "volume": (r.get("journalInfo") or {}).get("volume", ""), "pages": r.get("pageInfo", ""),
                    "doi": r.get("doi", ""), "updates": []}
                break
        if out["record"] is None:
            out["issues"].append((ERROR, "NOT_FOUND", "no matching record in Crossref, arXiv or Europe PMC; "
                                                      "possibly fabricated or not indexed (books, archives): check by hand"))
            return out
    else:
        out["record"], out["via"] = record_from_crossref(best), f"{bvia} (title coverage {bcov:.2f})"
    rec = out["record"]
    years = {int(y) for y in re.findall(r"\b(1[6-9]\d{2}|20\d{2})\b", ref)}
    if rec["years"] and years and not (years & set(rec["years"])):
        near = min(abs(a - b) for a in years for b in rec["years"])
        out["issues"].append((WARN if near <= 1 else ERROR, "YEAR_MISMATCH",
                              f"reference {sorted(years)} | record {rec['years']}"))
    if rec.get("volume") and not re.search(r"(?<!\d)" + re.escape(str(rec["volume"])) + r"(?!\d)", ref):
        out["issues"].append((WARN, "VOLUME_NOT_IN_REFERENCE", f"record volume {rec['volume']}"))
    if rec.get("pages"):
        fp = re.split(r"[-–]", str(rec["pages"]))[0].strip()
        if fp and not re.search(r"(?<![\dA-Za-z])" + re.escape(fp) + r"(?![\d])", ref):
            out["issues"].append((WARN, "PAGES_NOT_IN_REFERENCE", f"record pages {rec['pages']}"))
    fams = [bibtex.norm_name(a[0]) for a in rec["authors"] if a[0]]
    if fams:
        missing = [f for f in fams if (" " + f.split()[-1] + " ") not in rnorm]
        etal = bool(re.search(r"\bet\.? al\b|\.\.\.", ref, re.I))
        if missing and missing[0] == fams[0]:
            out["issues"].append((ERROR, "FIRST_AUTHOR", f"record first author {fams[0]} not in reference"))
        elif missing and not etal:
            out["issues"].append((ERROR, "AUTHOR_MISSING_FROM_REFERENCE", ", ".join(missing[:6])))
        n_listed = len(re.findall(r"\b[A-Z][a-zA-Z\-']+,?\s+(?:[A-Z]\.?\s?){1,3}(?=[,.;&]|\s+and\b|\s+et\b)", ref))
        if not etal and n_listed > len(fams) + 1:
            out["issues"].append((WARN, "MORE_NAMES_THAN_RECORD", f"~{n_listed} names in reference, {len(fams)} in record"))
    if rec.get("venue"):
        rk = set(venue_key(rec["venue"]).split())
        fk = {w[:3].lower() for w in re.findall(r"[A-Za-z]{2,}", ref)}
        if rk and len(rk & fk) / len(rk) < 0.6:
            out["issues"].append((WARN, "VENUE_NOT_IN_REFERENCE", f"record venue {rec['venue']}"))
    for u in rec.get("updates", []):
        out["issues"].append((ERROR if u.startswith("retraction") else WARN,
                              "RETRACTED" if u.startswith("retraction") else "HAS_UPDATE", u))
    if not dm and rec.get("doi"):
        out["issues"].append((INFO, "MISSING_DOI", rec["doi"]))
    return out


def reference_strings(path: str) -> list[tuple[str, str]]:
    src, kind = load_document(path)
    text = src.text
    if kind == "tex":
        items = []
        for m in re.finditer(r"\\bibitem(?:\[[^\]]*\])?\{[^}]*\}(.*?)(?=\\bibitem|\\end\{thebibliography\})", text, re.S):
            cleaned, _ = clean_latex(m.group(1))
            f, ln = src.loc(_line_of(text, m.start()))
            items.append((f"{f}:{ln}", re.sub(r"\s+", " ", cleaned).strip()))
        return items
    secs = doc_sections(text, kind)
    if "references" in secs:
        a, b, _ = secs["references"]
        body, base = text[a:b], _line_of(text, a)
    else:
        body, base = text, 0
    out = []
    for n, ref in bibtex.split_reference_list(body):
        f, ln = src.loc(base + n - 1)
        out.append((f"{f}:{ln}", ref))
    return out


def cmd_check_list(args):
    refs = reference_strings(args.source)
    os.makedirs(args.out, exist_ok=True)
    results = []
    for k, (loc, ref) in enumerate(refs, 1):
        try:
            r = verify_string(ref)
        except Exception as exc:
            r = {"issues": [(ERROR, "CHECK_FAILED", f"{type(exc).__name__}: {exc}")], "record": None, "via": ""}
        r.update({"key": f"ref{k}", "line": loc, "reference": ref})
        results.append(r)
        worst = min((i[0] for i in r["issues"]), key=[ERROR, WARN, INFO].index, default="OK")
        print(f"[{k}/{len(refs)}] {worst:5} {ref[:70]}", file=sys.stderr)
        time.sleep(0.1)
    with open(os.path.join(args.out, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    rank = [ERROR, WARN, INFO]
    lines = [f"# Reference list check: {args.source}", "", f"{len(results)} references.", "",
             "| # | loc | worst | reference | via | issues | record |", "|---|---|---|---|---|---|---|"]
    for r in sorted(results, key=lambda r: min((rank.index(i[0]) for i in r["issues"]), default=9)):
        worst = min((i[0] for i in r["issues"]), key=rank.index, default="OK")
        rec = r.get("record")
        rs = ""
        if rec:
            a1 = rec["authors"][0][0] if rec["authors"] else ""
            rs = f"{a1}; {rec['title'][:60]}; {rec.get('venue', '')} {rec.get('volume', '')} {rec.get('pages', '')} " \
                 f"({rec.get('year')}) {rec.get('doi', '')}"
        iss = "<br>".join(f"**{c}** {d}" for _s, c, d in r["issues"]).replace("|", "\\|")
        lines.append(f"| {r['key']} | {r['line']} | {worst} | {r['reference'][:120].replace('|', '/')} | {r['via']} | "
                     f"{iss} | {rs.replace('|', '/')} |")
    lines += ["", "Field checks on free-text references are presence checks (is the record's year / volume / first "
              "page / author in the string?). Read every ERROR and WARN against the record before changing anything."]
    with open(os.path.join(args.out, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    n_err = sum(1 for r in results if any(i[0] == ERROR for i in r["issues"]))
    print(f"{len(results)} references, {n_err} with errors -> {args.out}/report.md")


def plain_contexts(path: str) -> dict[str, list[dict]]:
    src, kind = load_document(path)
    text = src.text
    label = doc_region_labeler(text, kind)
    refs = {}
    secs = doc_sections(text, kind)
    if "references" in secs:
        a, b, _ = secs["references"]
        for k, (_n, r) in enumerate(bibtex.split_reference_list(text[a:b]), 1):
            refs[str(k)] = r
    by_key: dict[str, list[dict]] = {}
    clean, _ = light_clean(text)
    spans = []
    for pm in re.finditer(r"[^\n]+(?:\n(?!\n)[^\n]+)*", clean):
        if re.match(r"\s*#", pm.group(0)):
            continue
        spans += [(pm.start() + a, pm.start() + b) for a, b in sentences(pm.group(0))]
    for a, b in spans:
        sent = re.sub(r"\s+", " ", clean[a:b]).strip()
        if "references" in secs and secs["references"][0] <= a:
            continue
        keys = []
        for m in re.finditer(r"\[(\d+(?:\s*[,\u2013\-]\s*\d+)*)\]", sent):
            for part in re.split(r"\s*,\s*", m.group(1)):
                rng = re.split(r"\s*[\u2013\-]\s*", part)
                if len(rng) == 2 and rng[0].isdigit() and rng[1].isdigit() and int(rng[1]) - int(rng[0]) < 50:
                    keys += [str(x) for x in range(int(rng[0]), int(rng[1]) + 1)]
                elif part.isdigit():
                    keys.append(part)
        for m in re.finditer(r"\(([^()]*?\b(?:1[6-9]|20)\d{2}[a-z]?)\)", sent):
            for part in m.group(1).split(";"):
                am = re.search(r"([A-Z][A-Za-z\-']+(?: et al\.?| (?:and|&) [A-Z][A-Za-z\-']+)?),? ((?:1[6-9]|20)\d{2}[a-z]?)",
                               part)
                if am:
                    keys.append(f"{am.group(1)} {am.group(2)}")
        if not keys:
            continue
        f, ln = src.loc(_line_of(clean, a))
        for k in keys:
            by_key.setdefault(k, []).append({"loc": f"{f}:{ln}", "region": label(a), "sentence": sent,
                                             "claim": bool(CLAIM_VERBS.search(sent)), "co_cited": len(keys),
                                             "reference": refs.get(k, "")})
    return by_key


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("bib", nargs="+")
    c.add_argument("--tex", nargs="*", default=[])
    c.add_argument("--all", action="store_true", help="check every entry, not only cited ones")
    c.add_argument("--out", required=True)
    c.set_defaults(func=cmd_check)
    cl = sub.add_parser("check-list", help="free-text reference list (from .docx/.pdf/.md/.txt or a .tex thebibliography)")
    cl.add_argument("source")
    cl.add_argument("--out", required=True)
    cl.set_defaults(func=cmd_check_list)
    x = sub.add_parser("contexts")
    x.add_argument("tex", nargs="+")
    x.add_argument("--keys")
    x.add_argument("--out", required=True)
    x.set_defaults(func=cmd_contexts)
    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
