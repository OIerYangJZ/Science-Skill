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
  recent "query" [--days 540] [--db all] newest items from arXiv + OpenAlex + Europe PMC + Zenodo
  watch --queries FILE --state FILE [--days 90] [--github] [--out FILE]
                                      rerun saved queries across all sources and print
                                      only items not seen before (for scouting a
                                      direction before and while investing in it)

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
    if args.db == "zenodo":
        rows = sch.zenodo_search(_q(args.query), n=args.n, sort="date" if args.sort == "date" else "bestmatch",
                                 since=f"{args.year_from}-01-01" if args.year_from else None)
        emit(args, rows, f"[Zenodo] {args.query}")
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
    if args.db in ("zenodo", "all"):
        rows += sch.zenodo_search(_q(args.query), n=args.n, sort="date", since=since)
        if args.db == "zenodo":
            emit(args, rows, f"{args.query} (since {since}, Zenodo)")
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


def _row_key(r: dict) -> str:
    doi = (r.get("doi") or "").lower()
    m = re.match(r"10\.48550/arxiv\.(.+)$", doi)
    if r.get("arxiv") or m:
        return "arxiv:" + (r.get("arxiv") or m.group(1))
    return doi or \
        (r.get("pmid") and "pmid:" + str(r["pmid"])) or (r.get("id") and "id:" + str(r["id"])) or \
        "title:" + sch.norm_title(r.get("title", ""))


def _github_repos(query: str, n: int) -> list[dict]:
    import shutil
    import subprocess
    if not shutil.which("gh"):
        return []
    try:
        out = subprocess.run(["gh", "search", "repos", query, "--sort", "updated", "--limit", str(n), "--json",
                              "fullName,updatedAt,description,url"], capture_output=True, text=True, timeout=60).stdout
        return [{"id": "gh:" + r["fullName"], "year": r["updatedAt"][:4], "date": r["updatedAt"][:10], "cited_by": "",
                 "venue": "GitHub", "doi": "", "arxiv": "", "first_author": r["fullName"].split("/")[0],
                 "title": f"{r['fullName']}: {(r.get('description') or '')[:100]}"} for r in json.loads(out or "[]")]
    except (subprocess.SubprocessError, ValueError):
        return []


def cmd_watch(args):
    """Rerun saved queries and print only items not seen in earlier runs."""
    queries = [l.split("#", 1)[0].strip() for l in open(args.queries, encoding="utf-8")]
    queries = [q for q in queries if q]
    state = json.load(open(args.state, encoding="utf-8")) if os.path.exists(args.state) else {"seen": {}, "runs": []}
    since = (dt.date.today() - dt.timedelta(days=args.days)).isoformat()
    new_rows = []
    for q in queries:
        rows = []
        rows += [{"year": r["date"][:4], "date": r["date"], "venue": r["journal_ref"] or "arXiv", "doi": "",
                  "arxiv": r["arxiv"], "first_author": r["first_author"], "title": r["title"]}
                 for r in sch.arxiv_search(q, n=args.n) if r["date"] >= since]
        rows += [sch.work_row(x) for x in sch.openalex_list([f"from_publication_date:{since}"], search=_q(q),
                                                            sort="publication_date:desc", n=args.n)]
        rows += [sch.europepmc_row(x) for x in sch.europepmc_search(
            _epmc_query(q) + f" AND FIRST_PDATE:[{since} TO 3000-01-01]", n=args.n)]
        rows += sch.zenodo_search(_q(q), n=args.n, sort="date", since=since)
        if args.github:
            rows += _github_repos(q.replace('"', ""), min(args.n, 20))
        seen_q = set(state["seen"].get(q, []))
        fresh = []
        for r in rows:
            k = _row_key(r)
            if k and k not in seen_q:
                seen_q.add(k)
                r["query"] = q
                fresh.append(r)
        state["seen"][q] = sorted(seen_q)
        new_rows += fresh
    first_run = not state["runs"]
    state["runs"].append({"date": dt.date.today().isoformat(), "new": len(new_rows)})
    json.dump(state, open(args.state, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    label = "baseline (first run: everything is new)" if first_run else "new since the last run"
    print(f"# Watch: {len(queries)} queries, {len(new_rows)} items {label}\n")
    if new_rows:
        print(table(new_rows, cols=("date", "venue", "doi", "arxiv", "first_author", "title", "query")))
    if args.out:
        with open(args.out, "a", encoding="utf-8") as fh:
            fh.write(f"\n## watch {dt.date.today().isoformat()}: {len(new_rows)} {label}\n\n")
            if new_rows:
                fh.write(table(new_rows, cols=("date", "venue", "doi", "arxiv", "first_author", "title", "query")) + "\n")


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
    p.add_argument("--db", choices=["openalex", "europepmc", "arxiv", "zenodo", "all"], default="openalex",
                   help="openalex: all fields; europepmc: PubMed, PMC, bioRxiv/medRxiv; arxiv: physics/CS/math; "
                        "zenodo: code, data, reports, reproductions")
    p.add_argument("--from", dest="year_from", type=int)
    p.add_argument("--venue")
    p.add_argument("--sort", choices=["relevance", "cited", "date"], default="relevance")
    p.add_argument("-n", type=int, default=25)
    p.set_defaults(func=cmd_search)
    p = sub.add_parser("recent", parents=[common])
    p.add_argument("query")
    p.add_argument("--db", choices=["openalex", "europepmc", "arxiv", "zenodo", "all"], default="all",
                   help="all = arXiv + OpenAlex + Europe PMC + Zenodo")
    p.add_argument("--days", type=int, default=540)
    p.add_argument("-n", type=int, default=25)
    p.set_defaults(func=cmd_recent)
    p = sub.add_parser("watch")
    p.add_argument("--queries", required=True, help="text file, one query per line ('#' comments)")
    p.add_argument("--state", required=True, help="JSON file remembering what was already seen")
    p.add_argument("--days", type=int, default=90)
    p.add_argument("-n", type=int, default=25)
    p.add_argument("--github", action="store_true", help="also search GitHub repositories (needs the gh CLI)")
    p.add_argument("--out", help="append new items to this markdown file")
    p.set_defaults(func=cmd_watch)
    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
