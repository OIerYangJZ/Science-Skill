#!/usr/bin/env python3
"""ledger.py - keep an honest research ledger: what is proved, what failed and why.

Subcommands
  init LEDGER.md --goal "..."          create the ledger from the template
  search LEDGER.md "idea" [--notes DIR ...] [-k 8]
        Before trying a route: find similar routes, barriers and results in
        the ledger and in the notes (TF-IDF over table rows and note sections).
  lint LEDGER.md [--notes DIR ...]
        Checks the status line, status words, evidence paths, review state of
        'proved' results, 'reopen if' conditions of failed routes; flags notes
        without a status header and strong-claim sentences in notes.
  status LEDGER.md                     counts by status, open targets, last log entry

Status words
  results (section 1): VERIFIED, UNVERIFIED, CONDITIONAL, PRELIMINARY, NEGATIVE, RETRACTED
                       (aliases accepted: PROVED-REVIEWED, PROVED-UNREVIEWED, REPLICATED, HEURISTIC, NULL, ...)
  routes  (section 4): FAILED, PARTIAL, SUPERSEDED, IN-PROGRESS, SUCCEEDED
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
import os
import re
import sys
from collections import Counter

RESULT_STATUS = {"VERIFIED", "UNVERIFIED", "CONDITIONAL", "PRELIMINARY", "NEGATIVE", "RETRACTED"}
# field-specific spellings accepted in ledgers and mapped to the canonical word
STATUS_ALIASES = {"PROVED-REVIEWED": "VERIFIED", "PROVED": "UNVERIFIED?", "PROVED-UNREVIEWED": "UNVERIFIED",
                  "REPLICATED": "VERIFIED", "REPRODUCED": "VERIFIED", "SINGLE-RUN": "UNVERIFIED",
                  "SINGLE-STUDY": "UNVERIFIED", "HEURISTIC": "PRELIMINARY", "EXPLORATORY": "PRELIMINARY",
                  "PILOT": "PRELIMINARY", "NULL": "NEGATIVE", "NOT-SUPPORTED": "NEGATIVE"}
ROUTE_STATUS = {"FAILED", "PARTIAL", "SUPERSEDED", "IN-PROGRESS", "SUCCEEDED"}
STRONG_CLAIM = re.compile(
    r"\b(we have (?:now )?(?:proved|proven|shown|established|solved|confirmed|demonstrated)|"
    r"this (?:proves|establishes|settles|solves|confirms)|definitively|conclusively|"
    r"(?:trend(?:ing)? toward|marginally|approaching) significan\w*|clearly works|"
    r"(?:is|are) (?:now )?(?:proved|proven|solved|settled)|breakthrough|essentially (?:proves|done|solved)|"
    r"should be (?:straightforward|routine|easy) to (?:complete|finish)|only (?:a|one) (?:small|minor) gap|"
    r"we are close|almost (?:there|done|proved))\b", re.I)
STATUS_HEADER = re.compile(r"(\*\*\s*Status|^Status\s*[:(]|^#+\s*Status)", re.I | re.M)

TEMPLATE = """# Research ledger: {goal}

**Status ({date}): nothing proved yet towards the goal. Update this line after every session; it must say exactly what is proved and what is not.**

Goal: {goal}
Current best: - (status, evidence)

Status words. Results: VERIFIED (independently checked: proof reviewed / result replicated / analysis re-run by
someone else), UNVERIFIED (complete but not independently checked), CONDITIONAL(hypothesis or assumption),
PRELIMINARY (heuristic, pilot, exploratory, trend), NEGATIVE (tested and not supported), RETRACTED.
Routes (approaches, experiments, analyses, proof strategies): FAILED, PARTIAL, SUPERSEDED, IN-PROGRESS, SUCCEEDED.

## 1. Results

| ID | Result (exact statement or pointer) | Status | Evidence | Reviewed / verified (by, date) |
|---|---|---|---|---|

## 2. Data and numerical evidence

| ID | Test / experiment / analysis | Range or sample covered | Result | Evidence |
|---|---|---|---|---|

## 3. Open targets (ranked)

| ID | Target statement | Would give | Why hard / barrier |
|---|---|---|---|

## 4. Routes tried

| ID | Date | Route (one line) | Outcome | Stops at (barrier or step) | Evidence | Reopen only if |
|---|---|---|---|---|---|---|

## 5. Barriers

| Barrier | What it says | Routes that hit it |
|---|---|---|

## 6. Log

- {date}: ledger created.
"""

STOP = set("""a an the of on for and in with to via from by at is are was were be been being this that these those it its
as or not no but if then than so such into onto over under about which who whom whose what when where how all any each
we our us you your they their there here also only just can could may might must should would will shall do does did
done use used using one two three per vs i e g eg ie""".split())


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------
def read(path: str) -> list[str]:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read().splitlines()


def split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    cells, cur, esc = [], [], False
    for ch in s:
        if esc:
            cur.append(ch)
            esc = False
        elif ch == "\\":
            cur.append(ch)
            esc = True
        elif ch == "|":
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    cells.append("".join(cur).strip())
    return cells


def tables(lines: list[str]) -> list[dict]:
    """[{section, header: [...], rows: [(lineno, {col: val})]}]"""
    out = []
    section = ""
    i = 0
    while i < len(lines):
        ln = lines[i]
        h = re.match(r"^#{1,4}\s+(.*)", ln)
        if h:
            section = h.group(1).strip()
        if ln.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            header = [c.lower() for c in split_row(ln)]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                cells = split_row(lines[j])
                rows.append((j + 1, dict(zip(header, cells + [""] * (len(header) - len(cells))))))
                j += 1
            out.append({"section": section, "header": header, "rows": rows})
            i = j
            continue
        i += 1
    return out


def col(row: dict, *names: str) -> str:
    for k, v in row.items():
        if any(k.startswith(n) for n in names):
            return v
    return ""


def section_kind(title: str) -> str:
    t = title.lower()
    for key, kind in (("route", "routes"), ("result", "results"), ("proven", "results"), ("numer", "numerics"),
                      ("open", "targets"), ("target", "targets"), ("barrier", "barriers")):
        if key in t:
            return kind
    return "other"


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------
def tokens(text: str) -> list[str]:
    text = text.lower()
    toks = re.findall(r"\d+/\d+|[a-z][a-z0-9\-]*[a-z0-9]|[a-z]|\d+(?:\.\d+)?", text)
    out = []
    for t in toks:
        if t in STOP or len(t) < 2 and not t.isdigit():
            continue
        for suf in ("ations", "ation", "ings", "ing", "ies", "es", "ed", "s"):
            if len(t) > len(suf) + 3 and t.endswith(suf):
                t = t[: -len(suf)]
                break
        out.append(t)
    return out + [a + "_" + b for a, b in zip(out, out[1:])]


def note_chunks(path: str) -> list[tuple[int, str, str]]:
    lines = read(path)
    chunks, start, title, buf = [], 1, os.path.basename(path), []
    for i, ln in enumerate(lines, 1):
        if re.match(r"^#{1,4}\s", ln) and buf:
            chunks.append((start, title, "\n".join(buf)))
            buf, start, title = [], i, ln.strip("# ").strip()
        elif re.match(r"^#{1,4}\s", ln):
            start, title = i, ln.strip("# ").strip()
        buf.append(ln)
        if sum(len(x.split()) for x in buf) > 350 and ln.strip() == "":
            chunks.append((start, title, "\n".join(buf)))
            buf, start = [], i + 1
    if buf:
        chunks.append((start, title, "\n".join(buf)))
    return chunks


def collect_docs(ledger: str, notes: list[str]) -> list[dict]:
    docs = []
    lines = read(ledger)
    for t in tables(lines):
        kind = section_kind(t["section"])
        for lineno, row in t["rows"]:
            text = " ".join(row.values())
            docs.append({"src": f"{os.path.basename(ledger)}:{lineno}", "kind": "ledger:" + kind, "text": text,
                         "status": col(row, "outcome", "status"), "stops": col(row, "stops", "why hard", "barrier"),
                         "reopen": col(row, "reopen")})
    for d in notes:
        paths = [d] if os.path.isfile(d) else [os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs
                                                  if f.endswith((".md", ".txt", ".tex"))]
        for p in sorted(paths):
            if os.path.abspath(p) == os.path.abspath(ledger):
                continue
            for start, title, text in note_chunks(p):
                docs.append({"src": f"{os.path.relpath(p, os.path.dirname(os.path.abspath(ledger)))}:{start}",
                             "kind": "note", "text": text, "title": title})
    return docs


def tfidf_search(docs: list[dict], query: str, k: int) -> list[tuple[float, dict]]:
    dtoks = [Counter(tokens(d["text"])) for d in docs]
    df = Counter()
    for c in dtoks:
        df.update(c.keys())
    n = len(docs)
    idf = {t: math.log((n + 1) / (v + 1)) + 1 for t, v in df.items()}

    def vec(c):
        v = {t: (1 + math.log(f)) * idf.get(t, math.log(n + 1) + 1) for t, f in c.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}
    q = vec(Counter(tokens(query)))
    scored = []
    for d, c in zip(docs, dtoks):
        v = vec(c)
        s = sum(q[t] * v.get(t, 0.0) for t in q)
        if s > 0:
            scored.append((s, d))
    scored.sort(key=lambda x: -x[0])
    return scored[:k]


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------
def cmd_init(args):
    if os.path.exists(args.ledger) and not args.force:
        sys.exit(f"{args.ledger} exists; not overwriting")
    os.makedirs(os.path.dirname(os.path.abspath(args.ledger)), exist_ok=True)
    with open(args.ledger, "w", encoding="utf-8") as fh:
        fh.write(TEMPLATE.format(goal=args.goal, date=dt.date.today().isoformat()))
    print(f"created {args.ledger}")


def cmd_search(args):
    docs = collect_docs(args.ledger, args.notes)
    hits = tfidf_search(docs, args.idea, args.k)
    print(f"# Similar routes and notes for: {args.idea}\n")
    if not hits:
        print("No overlap found in the ledger or notes. That is not proof the idea is new; check the barriers table.")
        return
    print("| score | where | kind | status | stops at | reopen only if | excerpt |\n|---|---|---|---|---|---|---|")
    for s, d in hits:
        ex = re.sub(r"\s+", " ", d["text"]).strip()[:220].replace("|", "\\|")
        print(f"| {s:.2f} | {d['src']} | {d['kind']} | {d.get('status', '')} | "
              f"{d.get('stops', '').replace('|', '/')[:80]} | {d.get('reopen', '').replace('|', '/')[:60]} | {ex} |")
    failed = [d for s, d in hits if d["kind"] == "ledger:routes" and d.get("status", "").upper().startswith("FAILED")]
    if failed:
        print("\nSimilar FAILED routes exist. Before trying again, write down what the new attempt does that "
              "the failed one did not, and how it gets past the recorded barrier.")


def cmd_lint(args):
    lines = read(args.ledger)
    base = os.path.dirname(os.path.abspath(args.ledger))
    problems, notes_out = [], []
    head = "\n".join(lines[:15])
    m = re.search(r"\*\*Status \((\d{4}-\d{2}-\d{2})\)", head)
    if not m:
        problems.append("no '**Status (YYYY-MM-DD): ...**' line in the first 15 lines")
    else:
        age = (dt.date.today() - dt.date.fromisoformat(m.group(1))).days
        if age > 14:
            problems.append(f"status line is {age} days old")
    all_tables = tables(lines)
    if "Update this line after every session" in head and any(t["rows"] for t in all_tables):
        problems.append("status line is still the template text although results or routes are recorded")
    for t in all_tables:
        kind = section_kind(t["section"])
        for lineno, row in t["rows"]:
            loc = f"line {lineno}"
            if kind == "results":
                st = col(row, "status").upper()
                key = re.split(r"[\s(]", st)[0] if st else ""
                if key == "PROVED":
                    problems.append(f"{loc}: bare 'PROVED': say VERIFIED (checked by someone else) or UNVERIFIED")
                    key = "UNVERIFIED"
                key = STATUS_ALIASES.get(key, key)
                if key not in RESULT_STATUS:
                    problems.append(f"{loc}: result status '{st}' not one of {sorted(RESULT_STATUS)}")
                if key in ("VERIFIED", "UNVERIFIED", "NEGATIVE") and not col(row, "evidence"):
                    problems.append(f"{loc}: {key} without evidence")
                if key == "UNVERIFIED":
                    notes_out.append(f"{loc}: UNVERIFIED: get an independent check (proof review, replication, or a "
                                     "re-run by someone else) before reporting it as established")
                if key == "VERIFIED" and not col(row, "reviewed", "verified", "checked"):
                    problems.append(f"{loc}: VERIFIED but the 'Reviewed / verified by' column is empty")
                if key == "CONDITIONAL" and "(" not in st:
                    problems.append(f"{loc}: CONDITIONAL without the hypothesis in parentheses")
            elif kind == "routes":
                st = col(row, "outcome", "status").upper()
                key = re.split(r"[\s(]", st)[0] if st else ""
                if key not in ROUTE_STATUS:
                    problems.append(f"{loc}: route outcome '{st}' not one of {sorted(ROUTE_STATUS)}")
                if key in ("FAILED", "PARTIAL") and not col(row, "stops"):
                    problems.append(f"{loc}: {key} route without 'stops at'")
                if key == "FAILED" and not col(row, "reopen"):
                    problems.append(f"{loc}: FAILED route without a 'reopen only if' condition")
            ev = col(row, "evidence")
            for p in re.findall(r"`([^`]+)`", ev) or ([ev] if re.match(r"^[\w./\-]+\.(md|py|tex|json|txt|c)$", ev) else []):
                p0 = re.split(r"[:#§ ]", p)[0]
                if p0 and "/" in p0 or re.search(r"\.\w+$", p0 or ""):
                    if not os.path.exists(os.path.join(base, p0)) and not os.path.exists(p0):
                        problems.append(f"line {lineno}: evidence path not found: {p0}")
    for d in args.notes:
        paths = [d] if os.path.isfile(d) else [os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs
                                                  if f.endswith(".md")]
        for p in sorted(paths):
            if os.path.abspath(p) == os.path.abspath(args.ledger):
                continue
            nl = read(p)
            if not STATUS_HEADER.search("\n".join(nl[:20])):
                notes_out.append(f"{os.path.relpath(p, base)}: no status header in the first 20 lines")
            for i, ln in enumerate(nl, 1):
                if STRONG_CLAIM.search(ln):
                    notes_out.append(f"{os.path.relpath(p, base)}:{i}: strong claim, check it matches the ledger: "
                                     f"{ln.strip()[:140]}")
    print(f"# Ledger lint: {args.ledger}\n")
    print(f"## Problems ({len(problems)})\n")
    print("\n".join(f"- {x}" for x in problems) or "- none")
    print(f"\n## To check ({len(notes_out)})\n")
    print("\n".join(f"- {x}" for x in notes_out[:200]) or "- none")
    sys.exit(1 if problems else 0)


def cmd_status(args):
    lines = read(args.ledger)
    head = next((ln for ln in lines[:15] if ln.startswith("**Status")), "(no status line)")
    print(head + "\n")
    for t in tables(lines):
        kind = section_kind(t["section"])
        if kind in ("results", "routes"):
            c = Counter(re.split(r"[\s(]", (col(r, "status") if kind == "results" else col(r, "outcome", "status"))
                                 .upper() or "?")[0] for _, r in t["rows"])
            print(f"{t['section']}: " + ", ".join(f"{k} {v}" for k, v in c.most_common()))
        if kind == "targets":
            print(f"{t['section']}:")
            for _, r in t["rows"][:6]:
                print(f"  - {col(r, 'id')} {col(r, 'target')[:100]} -> {col(r, 'would')}")
    logs = [ln for ln in lines if re.match(r"^- \d{4}-\d{2}-\d{2}", ln)]
    if logs:
        print("\nLast log: " + logs[-1][2:])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("ledger")
    p.add_argument("--goal", required=True)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)
    p = sub.add_parser("search")
    p.add_argument("ledger")
    p.add_argument("idea")
    p.add_argument("--notes", nargs="*", default=[])
    p.add_argument("-k", type=int, default=8)
    p.set_defaults(func=cmd_search)
    p = sub.add_parser("lint")
    p.add_argument("ledger")
    p.add_argument("--notes", nargs="*", default=[])
    p.set_defaults(func=cmd_lint)
    p = sub.add_parser("status")
    p.add_argument("ledger")
    p.set_defaults(func=cmd_status)
    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
