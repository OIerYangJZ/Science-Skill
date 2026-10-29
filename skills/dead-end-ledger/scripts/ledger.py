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
  graph LEDGER.md                      dependency tree; cycles; results relying on retracted/negative/failed
                                       nodes; VERIFIED results with unverified dependencies; targets ready to
                                       attempt (all dependencies VERIFIED)
  card --id X7 --out notes/X7.md       idea card: hypothesis, prediction, falsification criterion, plan,
                                       dependencies, difference from failed routes, budget
  status LEDGER.md                     counts by status, open targets, last log entry

Status words
  results (section 1): VERIFIED, UNVERIFIED, CONDITIONAL, PRELIMINARY, NEGATIVE, RETRACTED
                       (aliases accepted: PROVED-REVIEWED, PROVED-UNREVIEWED, REPLICATED, HEURISTIC, NULL, ...)
  routes  (section 4): FAILED, BLOCKED (technical; not evidence against the idea), INCONCLUSIVE,
                       PARTIAL, SUPERSEDED, IN-PROGRESS, SUCCEEDED
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
ROUTE_STATUS = {"FAILED", "PARTIAL", "SUPERSEDED", "IN-PROGRESS", "SUCCEEDED", "BLOCKED", "INCONCLUSIVE"}
ROUTE_ALIASES = {"TECH-FAIL": "BLOCKED", "TECHNICAL-FAILURE": "BLOCKED", "ERROR": "BLOCKED", "STALLED": "BLOCKED",
                 "UNDECIDED": "INCONCLUSIVE", "NO-CONCLUSION": "INCONCLUSIVE", "MIXED": "INCONCLUSIVE"}
ID_RX = re.compile(r"\b[A-Z]{1,3}\d+[a-z]?\b")
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
Routes (approaches, experiments, analyses, proof strategies): FAILED (the idea does not work, with the reason),
BLOCKED (could not be carried out: compute, bug, access, time; NOT evidence against the idea), INCONCLUSIVE (carried
out, but the result does not decide), PARTIAL, SUPERSEDED, IN-PROGRESS, SUCCEEDED.
Dependencies: list the IDs a result or target relies on in "Depends on" (results, targets, conjectures). A result
can be VERIFIED only if everything it depends on is VERIFIED; otherwise mark it CONDITIONAL(<IDs>).

## 1. Results

| ID | Result (exact statement or pointer) | Status | Depends on | Evidence | Reviewed / verified (by, date) |
|---|---|---|---|---|---|

## 2. Data and numerical evidence

| ID | Test / experiment / analysis | Range or sample covered | Result | Evidence |
|---|---|---|---|---|

## 3. Open targets (ranked)

| ID | Target statement | Would give | Depends on | Why hard / barrier |
|---|---|---|---|---|

## 4. Routes tried

| ID | Date | Route (one line) | Outcome | Stops at (barrier or step) | Evidence | Reopen only if |
|---|---|---|---|---|---|---|

## 5. Barriers

| Barrier | What it says | Routes that hit it |
|---|---|---|

## 6. Stop rules

- Budget: <time / compute / money available for this goal>
- Stop or pivot when: <e.g. N consecutive routes stop at the same barrier; budget spent; review date reached>
- Review date: <YYYY-MM-DD>

## 7. Log

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
                      ("open", "targets"), ("target", "targets"), ("barrier", "barriers"), ("stop", "stop")):
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
                key = ROUTE_ALIASES.get(key, key)
                if key == "BLOCKED" and not col(row, "stops"):
                    problems.append(f"{loc}: BLOCKED route without the blocking reason in 'stops at' "
                                    "(compute, bug, access, time)")
                if key == "INCONCLUSIVE" and not col(row, "stops"):
                    problems.append(f"{loc}: INCONCLUSIVE route without saying why it does not decide")
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
    if not any(section_kind(t["section"]) == "stop" for t in all_tables) and \
            not any(re.match(r"^#{1,4}\s.*stop", ln, re.I) for ln in lines):
        notes_out.append("no 'Stop rules' section: add a budget and the condition for stopping or pivoting")
    g = analyse_graph(build_graph(lines))
    problems += g["problems"]
    notes_out += g["warnings"]
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


# ---------------------------------------------------------------------------
# dependency graph
# ---------------------------------------------------------------------------
def build_graph(lines: list[str]) -> dict:
    """nodes: id -> {kind, status, deps, line, text}"""
    nodes: dict[str, dict] = {}
    for t in tables(lines):
        kind = section_kind(t["section"])
        if kind not in ("results", "targets", "routes"):
            continue
        for lineno, row in t["rows"]:
            nid = col(row, "id").strip()
            if not nid:
                continue
            if kind == "results":
                st = col(row, "status").upper()
                key = re.split(r"[\s(]", st)[0] if st else ""
                key = STATUS_ALIASES.get(key, key).rstrip("?")
            elif kind == "targets":
                st, key = "OPEN", "OPEN"
            else:
                st = col(row, "outcome", "status").upper()
                key = re.split(r"[\s(]", st)[0] if st else ""
                key = ROUTE_ALIASES.get(key, key)
            deps = ID_RX.findall(col(row, "depends"))
            nodes[nid] = {"kind": kind, "status": key, "raw_status": st, "deps": deps, "line": lineno,
                          "text": (col(row, "result", "target", "route") or "")[:80]}
    return nodes


def analyse_graph(nodes: dict) -> dict:
    problems, warnings, ready, waiting = [], [], [], []
    for nid, n in nodes.items():
        for d in n["deps"]:
            if d not in nodes:
                problems.append(f"{nid} (line {n['line']}) depends on {d}, which is not in the ledger")
    # cycles
    color: dict[str, int] = {}
    cycles = []

    def dfs(u, stack):
        color[u] = 1
        stack.append(u)
        for v in nodes[u]["deps"]:
            if v not in nodes:
                continue
            if color.get(v) == 1:
                cycles.append(stack[stack.index(v):] + [v])
            elif not color.get(v):
                dfs(v, stack)
        stack.pop()
        color[u] = 2
    for u in nodes:
        if not color.get(u):
            dfs(u, [])
    for c in cycles:
        problems.append("dependency cycle: " + " -> ".join(c))

    def upstream(u, seen=None):
        seen = seen if seen is not None else set()
        for v in nodes.get(u, {}).get("deps", []):
            if v in nodes and v not in seen:
                seen.add(v)
                upstream(v, seen)
        return seen
    for nid, n in nodes.items():
        ups = upstream(nid)
        bad = [u for u in ups if nodes[u]["status"] in ("RETRACTED", "NEGATIVE", "FAILED")]
        if bad:
            problems.append(f"{nid} (line {n['line']}) relies on {', '.join(sorted(bad))} "
                            f"({', '.join(nodes[b]['status'] for b in sorted(bad))}): re-check or retract it")
        if n["status"] == "VERIFIED":
            weak = [u for u in ups if nodes[u]["status"] not in ("VERIFIED",)]
            if weak:
                problems.append(f"{nid} (line {n['line']}) is VERIFIED but depends on "
                                + ", ".join(f"{u} ({nodes[u]['status']})" for u in sorted(weak))
                                + ": mark it CONDITIONAL(" + ",".join(sorted(weak)) + ") or verify those first")
        if n["status"] == "CONDITIONAL":
            named = set(ID_RX.findall(n["raw_status"]))
            unlisted = [u for u in n["deps"] if u in nodes and nodes[u]["status"] != "VERIFIED" and u not in named]
            if unlisted:
                warnings.append(f"{nid}: CONDITIONAL should name its open dependencies: {', '.join(unlisted)}")
        if n["kind"] == "targets" or n["status"] in ("IN-PROGRESS",):
            open_deps = [u for u in n["deps"] if u in nodes and nodes[u]["status"] != "VERIFIED"]
            (waiting if open_deps else ready).append((nid, n, open_deps))
    return {"problems": problems, "warnings": warnings, "ready": ready, "waiting": waiting}


def cmd_graph(args):
    lines = read(args.ledger)
    nodes = build_graph(lines)
    a = analyse_graph(nodes)
    print(f"# Dependency graph: {len(nodes)} nodes\n")
    users: dict[str, list[str]] = {u: [] for u in nodes}
    for nid, n in nodes.items():
        for d in n["deps"]:
            users.setdefault(d, []).append(nid)

    def show(u, depth, seen):
        n = nodes.get(u)
        tag = f"{n['status']}" if n else "MISSING"
        print("  " * depth + f"- {u} [{tag}] {n['text'] if n else ''}")
        if u in seen:
            return
        seen.add(u)
        for d in (n["deps"] if n else []):
            show(d, depth + 1, seen)
    roots = [u for u in nodes if not users.get(u)] or list(nodes)
    for r in roots:
        show(r, 0, set())
    print(f"\n## Problems ({len(a['problems'])})\n")
    print("\n".join(f"- {x}" for x in a["problems"]) or "- none")
    if a["warnings"]:
        print("\n## Warnings\n")
        print("\n".join(f"- {x}" for x in a["warnings"]))
    print("\n## Ready to attempt (all dependencies VERIFIED)\n")
    print("\n".join(f"- {nid}: {n['text']}" for nid, n, _ in a["ready"]) or "- none")
    print("\n## Waiting on dependencies\n")
    print("\n".join(f"- {nid}: needs {', '.join(d)}" for nid, n, d in a["waiting"]) or "- none")
    sys.exit(1 if a["problems"] else 0)


CARD = """# Idea card {id}: <one-line idea>

Date: {date}. Ledger: {ledger}

- **Hypothesis / claim to establish:**
- **Prediction or deliverable** (what will be true or produced if it works):
- **Falsification / success criterion, fixed before starting:**
- **Verification plan** (proof steps, experiment, analysis; who or what checks it independently):
- **Depends on** (ledger IDs that must hold first):
- **Similar routes in the ledger** (`ledger.py search`) and the difference statement (what is new, and why it gets past the recorded barrier):
- **Budget** (time / compute / money) and the point at which to stop:

## Status

**Not started. Nothing is claimed.**
"""


def cmd_card(args):
    if os.path.exists(args.out):
        sys.exit(f"{args.out} exists; not overwriting")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(CARD.format(id=args.id, date=dt.date.today().isoformat(), ledger=args.ledger or "<path>"))
    print(f"created {args.out}")


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
    p = sub.add_parser("graph")
    p.add_argument("ledger")
    p.set_defaults(func=cmd_graph)
    p = sub.add_parser("card")
    p.add_argument("--id", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--ledger")
    p.set_defaults(func=cmd_card)
    p = sub.add_parser("status")
    p.add_argument("ledger")
    p.set_defaults(func=cmd_status)
    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
