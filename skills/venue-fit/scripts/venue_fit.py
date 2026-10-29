#!/usr/bin/env python3
"""venue_fit.py - evidence for choosing where to submit.

Subcommands
  neighbors --query QUERY [--seed DOI ...] [--from 2021] [-n 200] [--types journal,conference]
      Where similar work is published: aggregates the venues of works matching
      the query (OpenAlex full-text search; quote phrases and join with AND) and
      of works citing or cited by the seed papers. Counts, median citations and
      example titles per venue.

  profile NAME_OR_ISSN [...]
      OpenAlex profile per venue: type (journal / conference / repository),
      publisher, ISSN, homepage, open-access and DOAJ status, listed APC,
      yearly output, 2-year mean citedness, h-index. These are pointers for
      screening; fees, scope and policies must be confirmed on the venue's
      official pages.

  factsheet NAME_OR_ISSN [...] --out FILE
      Writes a fact-sheet template per venue: every fact to be collected from
      official pages, with columns for value, source URL, date checked and a
      verbatim snippet. OpenAlex values are prefilled and marked "verify".

Run with python3 -I. Network: OpenAlex only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import statistics
import sys
from collections import defaultdict

LIB = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "lib")
sys.path.insert(0, os.path.normpath(LIB))
import scholarly as sch  # noqa: E402

SELECT = "id,doi,title,publication_year,cited_by_count,primary_location"


def _q(query: str) -> str:
    if '"' in query or re.search(r"\b(AND|OR|NOT)\b", query):
        return query
    return " AND ".join(query.split())


def _venue(w: dict) -> tuple[str, str, str]:
    src = ((w.get("primary_location") or {}).get("source") or {})
    return (src.get("id") or "").rsplit("/", 1)[-1], src.get("display_name") or "", src.get("type") or ""


def cmd_neighbors(args):
    works = []
    filters = [f"publication_year:{args.year_from}-"] if args.year_from else []
    if args.query:
        works += sch.openalex_list(filters, search=_q(args.query), sort="relevance_score:desc", n=args.n, select=SELECT)
    for seed in args.seed or []:
        w = sch.openalex_work(seed)
        if not w:
            print(f"warning: seed not found: {seed}", file=sys.stderr)
            continue
        wid = w["id"].rsplit("/", 1)[-1]
        works += sch.openalex_list([f"cites:{wid}"] + filters, sort="cited_by_count:desc", n=min(args.n, 200),
                                   select=SELECT)
        refs = w.get("referenced_works") or []
        works += sch.openalex_by_ids(refs[:150], select=SELECT)
    seen, agg = set(), defaultdict(list)
    for w in works:
        if w.get("id") in seen:
            continue
        seen.add(w.get("id"))
        vid, name, vtype = _venue(w)
        if not name:
            continue
        if args.types and vtype not in args.types.split(","):
            continue
        agg[(vid, name, vtype)].append(w)
    rows = sorted(agg.items(), key=lambda kv: -len(kv[1]))
    print(f"# Venues of {len(seen)} related works" + (f" (query: {args.query})" if args.query else "") + "\n")
    print("| # | venue | type | related works | median cites | latest year | examples |")
    print("|---|---|---|---|---|---|---|")
    for k, ((vid, name, vtype), ws) in enumerate(rows[:args.top], 1):
        cites = [x.get("cited_by_count") or 0 for x in ws]
        ex = "; ".join((x.get("title") or "")[:60] for x in sorted(ws, key=lambda x: -(x.get("cited_by_count") or 0))[:2])
        latest = max((x.get("publication_year") or 0) for x in ws)
        print(f"| {k} | {name} ({vid}) | {vtype} | {len(ws)} | {statistics.median(cites):.0f} | {latest} | "
              f"{ex.replace('|', '/')} |")
    print("\nCounts show where similar work appears, not whether a venue would accept this manuscript.")


def _profile(ident: str) -> dict | None:
    v = sch.resolve_venues(ident)
    if not v:
        return None
    return sch.oa_json("sources/" + v[0][0], {})


def _profile_lines(js: dict) -> list[tuple[str, str]]:
    cby = sorted(js.get("counts_by_year") or [], key=lambda r: -r["year"])[:3]
    stats = js.get("summary_stats") or {}
    apc = ", ".join(f"{p['price']} {p['currency']}" for p in js.get("apc_prices") or []) or "-"
    return [
        ("Name", js.get("display_name", "")),
        ("OpenAlex id", (js.get("id") or "").rsplit("/", 1)[-1]),
        ("Type", js.get("type") or "-"),
        ("Publisher / host", js.get("host_organization_name") or "-"),
        ("ISSN-L / ISSN", f"{js.get('issn_l') or '-'} / {', '.join(js.get('issn') or []) or '-'}"),
        ("Homepage", js.get("homepage_url") or "-"),
        ("Open access (fully OA venue)", str(js.get("is_oa"))),
        ("In DOAJ", str(js.get("is_in_doaj"))),
        ("Listed APC", f"{apc} (approx. USD {js.get('apc_usd') or '-'})"),
        ("Works per year (latest 3)", "; ".join(f"{r['year']}: {r['works_count']}" for r in cby) or "-"),
        ("2-year mean citedness", f"{stats.get('2yr_mean_citedness', 0):.2f}" if stats else "-"),
        ("h-index", str(stats.get("h_index", "-"))),
        ("Publishing since / until", f"{js.get('first_publication_year') or '-'} / {js.get('last_publication_year') or '-'}"),
    ]


def cmd_profile(args):
    for ident in args.venues:
        js = _profile(ident)
        if not js:
            print(f"## {ident}\n\nnot found in OpenAlex\n")
            continue
        print(f"## {js.get('display_name')}\n\n| field | value (OpenAlex; verify on the official site) |\n|---|---|")
        for k, v in _profile_lines(js):
            print(f"| {k} | {str(v).replace('|', '/')} |")
        print()


FACTS = [
    ("Scope and aims (verbatim)", "aims & scope page"),
    ("Editorial criteria for sending out / acceptance (verbatim)", "editorial policies / criteria page"),
    ("Article types and length limits (words / pages / figures)", "author guidelines"),
    ("Abstract format and limit (structured? words)", "author guidelines"),
    ("Peer-review model (single / double blind, open, transparent)", "editorial policies"),
    ("Fees: APC, page or submission charges, waivers and discounts", "fees page"),
    ("Open-access options and license", "OA / licensing page"),
    ("Preprint policy (arXiv / bioRxiv / SSRN allowed?)", "editorial policies"),
    ("Generative AI / LLM use policy and disclosure", "editorial or AI policy page"),
    ("Data and code availability requirements", "data policy"),
    ("Required reporting guidelines or checklists", "author guidelines"),
    ("Concurrent submission, resubmission after rejection, transfer options", "editorial policies"),
    ("Deadlines (conferences: abstract, paper, supplementary, video, notification, camera-ready; time zone)", "call for papers"),
    ("Anonymity and public posting of submissions (conferences)", "call for papers"),
    ("Proceedings or archival status (does it block later journal submission?)", "call for papers"),
    ("Typical time to first decision / acceptance rate (if published by the venue)", "journal metrics page"),
    ("Template and submission system", "author guidelines"),
]


def cmd_factsheet(args):
    today = dt.date.today().isoformat()
    out = [f"# Venue fact sheets (created {today})", "",
           "Fill every row from the venue's official pages: value, URL, date checked, and a short verbatim snippet. "
           "Rows that cannot be confirmed stay 'unknown'. OpenAlex values are pointers only.", ""]
    for ident in args.venues:
        js = _profile(ident)
        name = js.get("display_name") if js else ident
        out += [f"## {name}", ""]
        if js:
            out += ["OpenAlex profile (verify): " + "; ".join(f"{k}: {v}" for k, v in _profile_lines(js)[2:9]), ""]
        out += ["| fact | value | source URL | checked | verbatim snippet |", "|---|---|---|---|---|"]
        for fact, where in FACTS:
            out.append(f"| {fact} | unknown (look in: {where}) | | | |")
        out += ["", "Fit notes (filled in Phase 4): scope evidence, bar, format, audience, cost, timeline, policy "
                    "compatibility, history, risks.", ""]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"fact sheets for {len(args.venues)} venues -> {args.out}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("neighbors")
    p.add_argument("--query")
    p.add_argument("--seed", nargs="*")
    p.add_argument("--from", dest="year_from", type=int)
    p.add_argument("-n", type=int, default=200)
    p.add_argument("--top", type=int, default=25)
    p.add_argument("--types", help="comma list, e.g. journal,conference")
    p.set_defaults(func=cmd_neighbors)
    p = sub.add_parser("profile")
    p.add_argument("venues", nargs="+")
    p.set_defaults(func=cmd_profile)
    p = sub.add_parser("factsheet")
    p.add_argument("venues", nargs="+")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_factsheet)
    args = ap.parse_args(argv)
    if args.cmd == "neighbors" and not (args.query or args.seed):
        ap.error("neighbors needs --query and/or --seed")
    args.func(args)


if __name__ == "__main__":
    main()
