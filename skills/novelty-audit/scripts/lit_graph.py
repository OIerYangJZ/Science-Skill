#!/usr/bin/env python3
"""lit_graph.py - literature search for falsifying a novelty claim.

Every command prints a markdown table and, with --log FILE, appends the query
and the result count to a search log, so that "no prior work found" can be
stated with its scope (which databases, which queries, which date).

Subcommands
  resolve ID [ID ...]                 DOIs / arXiv ids / OpenAlex ids -> works
  refs ID [--match "words"]           works that ID cites (backward)
  citing ID [--match "words"] [--from 2018] [--sort date|cited] [-n 50]
                                      works that cite ID (forward): who built on
                                      the same foundation, possibly the same result
  search "query" [--db openalex|europepmc|arxiv|all] [--from Y] [--venue "A,B"] [--sort relevance|cited|date]
                                      OpenAlex (all fields), Europe PMC (PubMed, PMC,
                                      bioRxiv/medRxiv/preprints), or arXiv
  recent "query" [--days 540] [--db all] newest items from arXiv + OpenAlex + Europe PMC

Queries use OpenAlex full-text search. Quote phrases and join with AND for
precision: '"phase folding" AND "T-count"'. Bare words are joined with AND.
--match applies the same syntax to the citing/refs lists. Run with python3 -I.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

LIB = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "lib")
sys.path.insert(0, os.path.normpath(LIB))
import scholarly as sch  # noqa: E402


def table(rows: list[dict], cols=("year", "cited_by", "venue", "doi", "arxiv", "first_author", "title")) -> str:
    out = ["| # | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 1)]
    for k, r in enumerate(rows, 1):
        cells = []
        for c in cols:
            v = r.get(c, "")
            v = "" if v is None else str(v)
            if c == "title" and r.get("retracted"):
                v = "**[RETRACTED]** " + v
            cells.append(v.replace("|", "\\|")[:140])
        out.append(f"| {k} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def log(args, what: str, n: int, rows: list[dict]):
    if not getattr(args, "log", None):
        return
    os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
    new = not os.path.exists(args.log)
    with open(args.log, "a", encoding="utf-8") as fh:
        if new:
            fh.write("# Search log\n\n| time (UTC) | database | command | query / seed | filters | results | top hits |\n"
                     "|---|---|---|---|---|---|---|\n")
        top = "; ".join((r.get("doi") or r.get("arxiv") or r.get("id") or "") for r in rows[:5])
        filt = " ".join(f"{k}={v}" for k, v in (("match", getattr(args, "match", None)),
                                                 ("from", getattr(args, "year_from", None)),
                                                 ("venue", getattr(args, "venue", None)),
                                                 ("days", getattr(args, "days", None))) if v)
        db = getattr(args, "db", None) or "OpenAlex"
        db = {"all": "arXiv+OpenAlex+EuropePMC" if args.cmd == "recent" else "all"}.get(db, db)
        fh.write(f"| {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M')} | {db} | {args.cmd} | "
                 f"{what.replace('|', '/')} | {filt} | {n} | {top} |\n")


def emit(args, rows, what):
    md = table(rows)
    print(md)
    if getattr(args, "out", None):
        with open(args.out, "a", encoding="utf-8") as fh:
            fh.write(f"\n## {args.cmd}: {what}\n\n{md}\n")
    if getattr(args, "json", False):
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    log(args, what, len(rows), rows)


def _q(query: str | None) -> str | None:
    """OpenAlex 'search' string. Quoted phrases and AND / OR / NOT are passed
    through; bare words are joined with AND for precision."""
    if not query:
        return None
    if '"' in query or re.search(r"\b(AND|OR|NOT)\b", query):
        return query
    return " AND ".join(query.split())


def cmd_resolve(args):
    rows = []
    for i in args.ids:
        w = sch.openalex_work(i)
        rows.append(sch.work_row(w) if w else {"title": f"NOT FOUND: {i}"})
    emit(args, rows, " ".join(args.ids))


def cmd_refs(args):
    w = sch.openalex_work(args.id)
    if not w:
        sys.exit(f"not found: {args.id}")
    ids = w.get("referenced_works") or []
    works = sch.openalex_by_ids(ids)
    rows = [sch.work_row(x) for x in works]
    if args.match:
        words = [x.lower() for x in args.match.split()]
        rows = [r for r in rows if all(x in r["title"].lower() for x in words)]
    rows.sort(key=lambda r: -(r["cited_by"] or 0))
    emit(args, rows, f"refs of {args.id} ({len(ids)} references)")


def cmd_citing(args):
    w = sch.openalex_work(args.id)
    if not w:
        sys.exit(f"not found: {args.id}")
    wid = w["id"].rsplit("/", 1)[-1]
    filters = ["cites:" + wid]
    if args.year_from:
        filters.append(f"publication_year:{args.year_from}-")
    sort = {"date": "publication_date:desc", "cited": "cited_by_count:desc"}[args.sort]
    rows = [sch.work_row(x) for x in sch.openalex_list(filters, search=_q(args.match), sort=sort, n=args.n)]
    total = w.get("cited_by_count")
    emit(args, rows, f"citing {args.id} ({total} citing works in total)")


def _epmc_query(q: str) -> str:
    return q if ('"' in q or re.search(r"\b(AND|OR|NOT)\b", q)) else " AND ".join(q.split())


def cmd_search(args):
    if args.db in ("europepmc", "all"):
        q = _epmc_query(args.query) + (f" AND PUB_YEAR:[{args.year_from} TO 3000]" if args.year_from else "")
        rows = [sch.europepmc_row(x) for x in sch.europepmc_search(q, n=args.n,
                sort="CITED desc" if args.sort == "cited" else ("FIRST_PDATE desc" if args.sort == "date" else None))]
        emit(args, rows, f"[Europe PMC] {args.query}")
        if args.db == "europepmc":
            return
    if args.db == "arxiv":
        rows = [{"year": r["date"][:4], "venue": r["journal_ref"] or "arXiv", "arxiv": r["arxiv"],
                 "first_author": r["first_author"], "title": r["title"]} for r in sch.arxiv_search(args.query, n=args.n)]
        emit(args, rows, f"[arXiv] {args.query}")
        return
    filters = []
    if args.venue:
        v = sch.resolve_venues(args.venue)
        if v:
            filters.append("primary_location.source.id:" + "|".join(i for i, _ in v))
    if args.year_from:
        filters.append(f"publication_year:{args.year_from}-")
    sort = {"relevance": "relevance_score:desc", "cited": "cited_by_count:desc", "date": "publication_date:desc"}[args.sort]
    rows = [sch.work_row(x) for x in sch.openalex_list(filters, search=_q(args.query), sort=sort, n=args.n)]
    emit(args, rows, args.query)


def cmd_recent(args):
    since = (dt.date.today() - dt.timedelta(days=args.days)).isoformat()
    rows = []
    if args.db in ("arxiv", "all", "openalex"):
        ax = [r for r in sch.arxiv_search(args.query, n=args.n) if r["date"] >= since] if args.db != "openalex" else []
        rows += [{"year": r["date"][:4], "cited_by": "", "venue": r["journal_ref"] or "arXiv", "doi": "",
                  "arxiv": r["arxiv"], "first_author": r["first_author"], "title": r["title"]} for r in ax]
        if args.db == "arxiv":
            emit(args, rows, f"{args.query} (since {since}, arXiv)")
            return
    if args.db in ("europepmc", "all"):
        q = _epmc_query(args.query) + f" AND FIRST_PDATE:[{since} TO 3000-01-01]"
        rows += [sch.europepmc_row(x) for x in sch.europepmc_search(q, n=args.n)]
        if args.db == "europepmc":
            emit(args, rows, f"{args.query} (since {since}, Europe PMC incl. bioRxiv/medRxiv)")
            return
    oa = sch.openalex_list([f"from_publication_date:{since}"], search=_q(args.query),
                           sort="relevance_score:desc", n=args.n)
    seen = {r["arxiv"] for r in rows if r["arxiv"]}
    for x in oa:
        r = sch.work_row(x)
        if r["arxiv"] and r["arxiv"] in seen:
            continue
        rows.append(r)
    emit(args, rows, f"{args.query} (since {since})")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--log", help="append this query to a markdown search log")
    common.add_argument("--out", help="append the result table to this markdown file")
    common.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("resolve", parents=[common])
    p.add_argument("ids", nargs="+")
    p.set_defaults(func=cmd_resolve)
    p = sub.add_parser("refs", parents=[common])
    p.add_argument("id")
    p.add_argument("--match")
    p.set_defaults(func=cmd_refs)
    p = sub.add_parser("citing", parents=[common])
    p.add_argument("id")
    p.add_argument("--match")
    p.add_argument("--from", dest="year_from", type=int)
    p.add_argument("--sort", choices=["date", "cited"], default="cited")
    p.add_argument("-n", type=int, default=50)
    p.set_defaults(func=cmd_citing)
    p = sub.add_parser("search", parents=[common])
    p.add_argument("query")
    p.add_argument("--db", choices=["openalex", "europepmc", "arxiv", "all"], default="openalex",
                   help="openalex: all fields; europepmc: PubMed, PMC, bioRxiv/medRxiv; arxiv: physics/CS/math")
    p.add_argument("--from", dest="year_from", type=int)
    p.add_argument("--venue")
    p.add_argument("--sort", choices=["relevance", "cited", "date"], default="relevance")
    p.add_argument("-n", type=int, default=25)
    p.set_defaults(func=cmd_search)
    p = sub.add_parser("recent", parents=[common])
    p.add_argument("query")
    p.add_argument("--db", choices=["openalex", "europepmc", "arxiv", "all"], default="all",
                   help="all = arXiv + OpenAlex + Europe PMC")
    p.add_argument("--days", type=int, default=540)
    p.add_argument("-n", type=int, default=25)
    p.set_defaults(func=cmd_recent)
    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
