#!/usr/bin/env python3
"""exemplar_meta.py - find, verify and fetch exemplar papers.

Every exemplar used in a polish survey must be a real paper with resolved
metadata. This script queries OpenAlex, Crossref and the arXiv API, and
writes one markdown file per paper in the format hedge_scan.py reads.

Run it with `python3 -I` (it parses downloaded text).

Subcommands
  venue NAME                      list OpenAlex source ids for a journal name
  search QUERY [options]          candidate papers from OpenAlex
      --venue "PRX Quantum,Physical Review Letters"   restrict to journals
      --from 2021 --to 2026       publication years
      --sort cited|relevance|date (default cited)
      -n 25                       number of results
  fetch ID [ID ...] --out DIR     verify + write DIR/<slug>.md for each ID
      ID is a DOI (10.xxxx/...), an arXiv id (2502.19526), a PMID or a PMCID
      --ids-file FILE             one ID per line ('#' comments allowed)
      --intro                     also pull the introduction: arXiv LaTeX source
                                  (read in memory, never run), else PMC open-access XML

Environment (optional)
  OPENALEX_API_KEY      own OpenAlex budget instead of the shared one
  SCIENCE_SKILL_MAILTO  e-mail for the Crossref/OpenAlex polite pool; set it
                        yourself, the script never guesses one

Abstract preference: Crossref (publisher deposit) > OpenAlex > arXiv. The
source used is recorded in each file. Introductions come from the arXiv
version, which can differ from the published one; that is recorded too.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

LIB = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "lib")
sys.path.insert(0, os.path.normpath(LIB))
from scholarly import (  # noqa: E402
    arxiv_from_url, arxiv_meta, arxiv_search_title, arxiv_sections, crossref, europepmc_lookup, europepmc_sections,
    inverted_to_text, oa_json, openalex_by_doi, resolve_venues, slugify, strip_jats, title_ratio,
)

# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------
def cmd_venue(args):
    js = oa_json("sources", {"search": args.name, "per_page": 10, "select": "id,display_name,works_count,host_organization_name"})
    for r in (js or {}).get("results", []):
        print(f"{r['id'].rsplit('/', 1)[-1]}\t{r['display_name']}\t{r.get('works_count')} works\t{r.get('host_organization_name') or ''}")


def cmd_search(args):
    q = re.sub(r"[,|:]", " ", args.query).strip()
    filters = ["type:article", "title_and_abstract.search:" + q]
    if args.venue:
        v = resolve_venues(args.venue)
        if not v:
            sys.exit("no venue resolved")
        print("venues: " + "; ".join(f"{n} ({i})" for i, n in v), file=sys.stderr)
        filters.append("primary_location.source.id:" + "|".join(i for i, _ in v))
    if args.year_from or args.year_to:
        filters.append(f"publication_year:{args.year_from or ''}-{args.year_to or ''}")
    sort = {"cited": "cited_by_count:desc", "date": "publication_date:desc", "relevance": "relevance_score:desc"}[args.sort]
    params = {"filter": ",".join(filters), "sort": sort, "per_page": min(args.n, 100),
              "select": "id,doi,title,publication_year,cited_by_count,primary_location,locations,authorships"}
    js = oa_json("works", params)
    rows = []
    for r in (js or {}).get("results", []):
        title = r.get("title") or ""
        if re.match(r"(erratum|publisher'?s note|retraction|correction)", title, re.I):
            continue
        arx = None
        for loc in r.get("locations") or []:
            arx = arx or arxiv_from_url(loc.get("landing_page_url")) or arxiv_from_url(loc.get("pdf_url"))
        venue = ((r.get("primary_location") or {}).get("source") or {}).get("display_name", "")
        au = r.get("authorships") or []
        first = au[0]["author"]["display_name"] if au else ""
        rows.append((r.get("publication_year"), r.get("cited_by_count"), venue,
                     (r.get("doi") or "").replace("https://doi.org/", ""), arx or "", first, title))
    if args.json:
        print(json.dumps([dict(zip(["year", "cited_by", "venue", "doi", "arxiv", "first_author", "title"], x)) for x in rows],
                         ensure_ascii=False, indent=1))
        return
    print("| # | year | cites | venue | doi | arXiv | first author | title |")
    print("|---|---|---|---|---|---|---|---|")
    for k, (y, c, v, d, a, f, t) in enumerate(rows, 1):
        print(f"| {k} | {y} | {c} | {v} | {d} | {a} | {f} | {t} |")


def fetch_one(ident: str, out_dir: str, want_intro: bool) -> dict:
    ident = ident.strip()
    ident = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", ident, flags=re.I)
    ident = re.sub(r"^(https?://arxiv\.org/(abs|pdf)/|arxiv:)", "", ident, flags=re.I)
    rec = {"input": ident, "checks": []}
    pm = re.match(r"^(?:pmid:\s*)?(\d{5,9})$|^(PMC\d+)$", ident, re.I)
    if pm:
        e = europepmc_lookup(pm.group(1) or pm.group(2).upper())
        if not e or not e.get("doi"):
            rec["status"] = "NOT FOUND (or no DOI) in Europe PMC - do not use" if not e else "no DOI; fetch by hand"
            return rec
        rec["checks"].append(f"Europe PMC {e.get('pmid') or e.get('pmcid')}")
        ident = e["doi"]
    is_doi = ident.startswith("10.")
    cr = oa = ax = None
    if is_doi:
        cr = crossref(ident)
        oa = openalex_by_doi(ident)
        if cr:
            rec["checks"].append("Crossref")
        if oa:
            rec["checks"].append("OpenAlex")
        if not cr and not oa:
            rec["status"] = "NOT FOUND - do not use"
            return rec
        title = ((cr or {}).get("title") or [None])[0] or (oa or {}).get("title") or ""
        authors = [" ".join(x for x in (a.get("given"), a.get("family")) if x) for a in (cr or {}).get("author", [])] \
            or [a["author"]["display_name"] for a in (oa or {}).get("authorships", [])]
        venue = ((cr or {}).get("container-title") or [""])[0] or \
            (((oa or {}).get("primary_location") or {}).get("source") or {}).get("display_name", "")
        dp = ((cr or {}).get("published") or (cr or {}).get("issued") or {}).get("date-parts", [[None]])[0]
        year = dp[0] if dp and dp[0] else (oa or {}).get("publication_year")
        vol = (cr or {}).get("volume", "")
        num = (cr or {}).get("article-number") or (cr or {}).get("page", "")
        rec.update(title=title, authors=authors, venue=venue, year=year, doi=ident,
                   citation=f"{venue} {vol}, {num} ({year})".replace(" , ", " ").strip(),
                   cited_by=(oa or {}).get("cited_by_count"))
        abstract, src = "", ""
        if cr and cr.get("abstract"):
            abstract, src = strip_jats(cr["abstract"]), "Crossref (publisher deposit)"
        aid = None
        for loc in (oa or {}).get("locations") or []:
            aid = aid or arxiv_from_url(loc.get("landing_page_url")) or arxiv_from_url(loc.get("pdf_url"))
        if not aid and title:
            hit = arxiv_search_title(title)
            if hit:
                aid = hit["id"]
                rec["checks"].append(f"arXiv title match {hit['ratio']:.2f}")
        if aid:
            ax = arxiv_meta(aid)
            if ax:
                r = title_ratio(ax["title"], title)
                rec["checks"].append(f"arXiv {aid} (title ratio {r:.2f})")
                if r < 0.8:
                    rec["checks"].append("WARNING arXiv title differs - check by hand")
        if not abstract and ax and title_ratio(ax["title"], title) >= 0.8:
            abstract, src = ax["abstract"], "arXiv (preprint version; published text may differ)"
        if not abstract and oa and oa.get("abstract_inverted_index"):
            abstract, src = inverted_to_text(oa["abstract_inverted_index"]), "OpenAlex (reconstructed; math may be garbled)"
    else:
        ax = arxiv_meta(ident)
        if not ax:
            rec["status"] = "NOT FOUND - do not use"
            return rec
        rec["checks"].append("arXiv")
        title, authors = ax["title"], ax["authors"]
        year = ax["published"][:4]
        rec.update(title=title, authors=authors, venue=ax["journal_ref"] or "arXiv preprint", year=year,
                   doi=ax["doi"], citation=ax["journal_ref"] or f"arXiv:{ax['id']} ({year})")
        abstract, src = ax["abstract"], "arXiv"
        aid = ax["id"]
        if ax["doi"]:
            cr = crossref(ax["doi"])
            if cr:
                rec["checks"].append("Crossref (journal DOI)")
                if cr.get("abstract"):
                    abstract, src = strip_jats(cr["abstract"]), "Crossref (publisher deposit)"
                vol = cr.get("volume", "")
                num = cr.get("article-number") or cr.get("page", "")
                cy = (cr.get("published") or cr.get("issued") or {}).get("date-parts", [[None]])[0][0]
                rec["citation"] = f"{(cr.get('container-title') or [''])[0]} {vol}, {num} ({cy})"
    rec["arxiv"] = aid or ""
    rec["abstract_source"] = src
    rec["status"] = "verified" if rec["checks"] else "unverified"
    slug = slugify(rec["authors"][0] if rec.get("authors") else "", rec.get("year"), rec.get("title", ""))
    rec["slug"] = slug

    intro = None
    if want_intro and aid:
        secs = arxiv_sections(aid)
        if "error" in secs:
            rec["intro_source"] = "none: " + secs["error"]
        else:
            intro = secs.get("introduction")
            ver = (ax or {}).get("version", "")
            rec["intro_source"] = f"arXiv {aid}{ver} source, {secs['main_file']}" + \
                (f" ({intro['note']})" if intro and intro.get("note") else "") + \
                ("" if intro else " - introduction not found")
            if intro:
                with open(os.path.join(out_dir, slug + ".intro.tex"), "w", encoding="utf-8") as fh:
                    fh.write(f"% Introduction of arXiv:{aid}{ver}, extracted from {secs['main_file']} for analysis only.\n")
                    fh.write(intro["raw"] + "\n")
    if want_intro and intro is None and rec.get("doi"):
        e = europepmc_lookup(rec["doi"])
        if e and e.get("pmcid"):
            ps = europepmc_sections(e["pmcid"])
            if ps.get("introduction"):
                intro = {"text": ps["introduction"], "raw": ps["introduction"], "note": ps.get("intro_note", "")}
                rec["intro_source"] = f"PMC open-access full text {e['pmcid']}" + \
                    (f" ({ps['intro_note']})" if ps.get("intro_note") else "")
                with open(os.path.join(out_dir, slug + ".intro.txt"), "w", encoding="utf-8") as fh:
                    fh.write(f"Introduction of {e['pmcid']} (PMC open-access XML), for analysis only.\n\n")
                    fh.write(ps["introduction"] + "\n")
            if not abstract and ps.get("abstract"):
                abstract, src = ps["abstract"], f"PMC full text {e['pmcid']}"
                rec["abstract_source"] = src
        if e and not abstract and e.get("abstractText"):
            abstract, src = re.sub(r"<[^>]+>", " ", e["abstractText"]), "Europe PMC (PubMed abstract)"
            rec["abstract_source"] = src
    if want_intro and intro is None and not rec.get("intro_source"):
        rec["intro_source"] = "none: no arXiv version and no PMC open-access full text; get the introduction from " \
                              "the publisher page or the user's PDF"

    lines = [f"# {rec.get('title', '')}", ""]
    lines += [f"- authors: {', '.join(rec.get('authors', []))}",
              f"- citation: {rec.get('citation', '')}",
              f"- doi: {rec.get('doi') or '-'}",
              f"- arxiv: {rec.get('arxiv') or '-'}",
              f"- cited_by (OpenAlex): {rec.get('cited_by') if rec.get('cited_by') is not None else '-'}",
              f"- verified via: {', '.join(rec['checks'])}",
              f"- abstract_source: {src or 'none'}",
              f"- intro_source: {rec.get('intro_source', 'not requested')}",
              "- pool: (A target-venue exemplar / B nearest prior work)",
              "- group: (genre group)", "",
              "## Abstract", "", abstract or "(no abstract found)", ""]
    if intro:
        words = intro["text"].split()
        body = intro["text"]
        if len(words) > 4000:
            body = " ".join(words[:4000]) + "\n\n[truncated at 4000 words; full LaTeX in .intro.tex]"
        lines += ["## Introduction", "", body, ""]
    lines += ["## Analysis card", "", "(fill in with the template in references/exemplar-protocol.md)", ""]
    with open(os.path.join(out_dir, slug + ".md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return rec


def cmd_fetch(args):
    ids = list(args.ids or [])
    if args.ids_file:
        with open(args.ids_file, encoding="utf-8") as fh:
            ids += [l.split("#", 1)[0].strip() for l in fh if l.split("#", 1)[0].strip()]
    if not ids:
        sys.exit("no identifiers")
    os.makedirs(args.out, exist_ok=True)
    recs = []
    for i in ids:
        try:
            r = fetch_one(i, args.out, args.intro)
        except Exception as exc:  # keep going; report the failure
            r = {"input": i, "status": f"ERROR {type(exc).__name__}: {exc}", "checks": []}
        recs.append(r)
        print(f"[{len(recs)}/{len(ids)}] {r.get('status')}: {r.get('slug', i)}", file=sys.stderr)
    print("| # | status | slug | citation | arXiv | abstract | intro | checks |")
    print("|---|---|---|---|---|---|---|---|")
    for k, r in enumerate(recs, 1):
        print(f"| {k} | {r.get('status')} | {r.get('slug', r['input'])} | {r.get('citation', '')} | {r.get('arxiv', '')} | "
              f"{(r.get('abstract_source') or '-').split(' ')[0]} | {(r.get('intro_source') or '-')[:40]} | {'; '.join(r['checks'])} |")
    with open(os.path.join(args.out, "_fetch_log.json"), "a", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("venue")
    v.add_argument("name")
    v.set_defaults(func=cmd_venue)
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--venue")
    s.add_argument("--from", dest="year_from", type=int)
    s.add_argument("--to", dest="year_to", type=int)
    s.add_argument("--sort", choices=["cited", "relevance", "date"], default="cited")
    s.add_argument("-n", type=int, default=25)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_search)
    f = sub.add_parser("fetch")
    f.add_argument("ids", nargs="*")
    f.add_argument("--ids-file")
    f.add_argument("--out", required=True)
    f.add_argument("--intro", action="store_true")
    f.set_defaults(func=cmd_fetch)
    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
