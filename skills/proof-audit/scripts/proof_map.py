#!/usr/bin/env python3
"""proof_map.py - map the logical structure of a LaTeX manuscript's proofs.

Usage
  proof_map.py main.tex [supplement.tex ...] --out DIR

Extracts theorem-like environments (theorem, lemma, proposition, corollary,
claim, conjecture, definition, assumption, hypothesis, remark, and every
environment declared with \\newtheorem or \\declaretheorem), their labels and
statements, and the proofs that belong to them (the proof environment that
follows, "Proof of Theorem~\\ref{x}" proofs elsewhere, e.g. in appendices,
proofs in sections titled "Proof of ...", and inline "Proof." paragraphs).
The dependency graph comes from \\ref, \\cref, \\Cref, \\eqref, \\autoref inside
statements and proofs.

Writes DIR/proof_map.md and DIR/proof_map.json:
  (a) dependency tree per top-level result
  (b) cycles in the dependency graph (possible circularity)
  (c) results without a proof that are not definitions, conjectures or
      assumptions and show no citation (missing obligation, or an external
      result that should be cited)
  (d) results depending, directly or transitively, on a conjecture,
      assumption or hypothesis (conditional chains)
  (e) labels referenced but never defined
  (f) lemmas and propositions never referenced by any other result
  (g) gap phrases inside proofs ("clearly", "similarly", "one can show", ...)
  (h) constant and effectivity leads in final statements
  (i) macros defined more than once with different bodies

Every item is a lead for the audit, not a verdict. Hard-coded references
("Theorem 3" without \\ref) are not tracked.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict

LIB = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "lib")
sys.path.insert(0, os.path.normpath(LIB))
from texutil import _line_of, _match_brace, clean_latex, read_tex, strip_comments_keep  # noqa: E402

KIND_WORDS = ["theorem", "lemma", "proposition", "corollary", "claim", "conjecture", "definition", "assumption",
              "hypothesis", "remark", "example", "fact", "observation", "notation", "condition", "property",
              "problem", "question", "principle", "axiom", "postulate"]
DEFAULT_ENVS = {
    "theorem": "theorem", "thm": "theorem", "maintheorem": "theorem", "lemma": "lemma", "lem": "lemma",
    "proposition": "proposition", "prop": "proposition", "corollary": "corollary", "cor": "corollary",
    "claim": "claim", "conjecture": "conjecture", "conj": "conjecture", "definition": "definition",
    "defn": "definition", "dfn": "definition", "assumption": "assumption", "hypothesis": "hypothesis",
    "remark": "remark", "rem": "remark", "fact": "fact", "observation": "observation", "example": "example",
}
PROVABLE = {"theorem", "lemma", "proposition", "corollary", "claim", "fact", "property", "observation"}
CONDITIONAL = {"conjecture", "assumption", "hypothesis", "axiom", "postulate", "condition"}
NO_PROOF_NEEDED = {"definition", "remark", "example", "notation", "conjecture", "assumption", "hypothesis",
                   "axiom", "postulate", "condition", "problem", "question", "principle"}
REF_RX = re.compile(r"\\(?:ref|cref|Cref|eqref|autoref|labelcref|cpageref|Cpageref|nameref|vref|Vref)\*?\s*\{([^{}]+)\}")
LABEL_RX = re.compile(r"\\label\s*\{([^{}]+)\}")
GAP_RX = re.compile(
    r"\b(clearly|obviously|evidently|trivially|it is (?:easy|straightforward|not hard|routine) to (?:see|check|verify|show)|"
    r"easy to (?:see|check|verify)|it is clear that|straightforward(?:ly)?|(?:a |the )?standard (?:argument|computation|"
    r"calculation|estimate|technique)s?|similarly|analogously|without loss of generality|w\.l\.o\.g\.|"
    r"one (?:can|may) (?:show|check|verify|see)|it can be (?:shown|checked|verified)|routine|by a similar argument|"
    r"by the same argument|left to the reader|we omit|(?:details|the proof) (?:is|are) omitted|omitted|sketch(?:ed)?|"
    r"it follows easily|a (?:short|simple|direct) (?:calculation|computation)|one checks|the rest is)\b", re.I)
CONST_RX = re.compile(
    r"(for some (?:absolute |universal |positive |effective |ineffective |explicit )?constants?|"
    r"(?<![A-Za-z])O\(1\)|(?<![A-Za-z])o\(1\)|\\ll\b|\\gg\b|\\lesssim|\\gtrsim|sufficiently (?:large|small)|"
    r"non-?effective|ineffective|implied constants?|absolute constants?|unspecified constants?)", re.I)
TEXT_CONDITION_RX = re.compile(
    r"\b(assuming|under (?:the )?(?:assumption|hypothesis|conjecture)|conditional(?:ly)? on|provided (?:that )?"
    r"(?:conjecture|hypothesis)|if (?:conjecture|hypothesis) \S+ holds)\b", re.I)
HEADING_RX = re.compile(r"\\(section|subsection|subsubsection|paragraph)\*?\s*(?:\[[^\]]*\])?\s*\{")
LEVEL = {"section": 1, "subsection": 2, "subsubsection": 3, "paragraph": 4}


def loc(src, text, off):
    f, ln = src.loc(_line_of(text, off))
    return f"{f}:{ln}"


def refs_in(s: str) -> list[str]:
    out = []
    for m in REF_RX.finditer(s):
        out += [k.strip() for k in m.group(1).split(",") if k.strip()]
    return out


def kind_of(title: str, env: str) -> str:
    t = (title or "").lower()
    for w in KIND_WORDS:
        if w in t:
            return w
    e = env.lower().rstrip("*")
    if e in DEFAULT_ENVS:
        return DEFAULT_ENVS[e]
    for w in KIND_WORDS:
        if e.startswith(w[:4]):
            return w
    return "other"


def theorem_envs(nc: str) -> dict[str, str]:
    envs = dict(DEFAULT_ENVS)
    for m in re.finditer(r"\\(?:new|spnew)theorem\*?\s*\{([^{}]+)\}\s*(?:\[[^\]]*\])?\s*\{([^{}]*)\}", nc):
        envs[m.group(1).strip()] = kind_of(m.group(2), m.group(1))
    for m in re.finditer(r"\\declaretheorem\s*(?:\[([^\]]*)\])?\s*\{([^{}]+)\}", nc):
        opts = m.group(1) or ""
        nm = re.search(r"name\s*=\s*\{?([^,}\]]+)", opts)
        for env in m.group(2).split(","):
            envs[env.strip()] = kind_of(nm.group(1) if nm else env, env.strip())
    return envs


def is_condition(n: dict) -> bool:
    """Conjectures, assumptions, hypotheses - and unproved statements of another
    kind whose title names them as such (e.g. a remark titled 'Hypothesis H')."""
    return n["kind"] in CONDITIONAL or (n["kind"] not in PROVABLE and bool(
        re.match(r"\s*(conjecture|hypothesis|assumption)\b", n["title"], re.I)))


def find_env_spans(nc: str, name: str):
    rx_b = re.compile(r"\\begin\{" + re.escape(name) + r"(\*?)\}")
    for m in rx_b.finditer(nc):
        star = m.group(1)
        end_tok = "\\end{" + name + star + "}"
        depth, pos = 1, m.end()
        while depth:
            nb = nc.find("\\begin{" + name + star + "}", pos)
            ne = nc.find(end_tok, pos)
            if ne < 0:
                break
            if 0 <= nb < ne:
                depth += 1
                pos = nb + 1
            else:
                depth -= 1
                pos = ne + len(end_tok)
        if depth:
            continue
        body_start = m.end()
        opt = ""
        om = re.match(r"\s*\[", nc[body_start:])
        if om:
            j = body_start + om.end() - 1
            depth2, k = 0, j
            while k < len(nc):
                if nc[k] == "[":
                    depth2 += 1
                elif nc[k] == "]":
                    depth2 -= 1
                    if depth2 == 0:
                        break
                k += 1
            opt = nc[j + 1:k]
            body_start = k + 1
        yield m.start(), body_start, pos - len(end_tok), pos, opt


def build(mains: list[str]) -> dict:
    text, sources = "", []
    offsets = []
    for p in mains:
        src = read_tex(p)
        offsets.append((len(text), src))
        text += src.text
    nc = strip_comments_keep(text)

    def where(off: int) -> str:
        base, src = offsets[0]
        for b, s in offsets:
            if b <= off:
                base, src = b, s
        f, ln = src.loc(_line_of(text, off) - _line_of(text, base))
        return f"{f}:{ln}"

    envs = theorem_envs(nc)
    nodes = []
    for env, kind in envs.items():
        for s, bs, be, e, opt in find_env_spans(nc, env):
            body = nc[bs:be]
            lab = LABEL_RX.search(body)
            stmt, _ = clean_latex(text[bs:be])
            stmt = re.sub(r"\s+", " ", stmt).strip()
            nodes.append({"env": env, "kind": kind_of(opt, env) if kind == "other" else kind, "title": opt.strip(),
                          "label": lab.group(1).strip() if lab else "", "start": s, "end": e,
                          "loc": where(s), "statement": stmt[:200], "stmt_refs": refs_in(body),
                          "stmt_span": (bs, be), "proofs": [], "proof_refs": [], "gaps": [],
                          "cited": bool(re.search(r"\\cite\w*\s*[\[{]", opt + body + nc[max(0, s - 400):s])),
                          "text_condition": bool(TEXT_CONDITION_RX.search(body))})
    # drop environments nested in other theorem-like environments of the same span (e.g. aliases)
    nodes.sort(key=lambda n: n["start"])
    uniq = []
    for n in nodes:
        if uniq and uniq[-1]["start"] == n["start"]:
            continue
        uniq.append(n)
    nodes = uniq
    by_label = {n["label"]: n for n in nodes if n["label"]}
    for i, n in enumerate(nodes):
        n["id"] = n["label"] or f"{n['kind']}@{n['loc']}"

    # proofs ---------------------------------------------------------------
    proof_spans = []  # (start, body_start, body_end, owner_or_None, how)
    heads = [(m.start(), m.group(1), _match_brace(nc, m.end() - 1), m.end()) for m in HEADING_RX.finditer(nc)]
    proof_heads = []  # (heading start, heading end, section end, [labels])
    for i, (hs, lvl, he, ab) in enumerate(heads):
        title = nc[ab:he - 1]
        if not re.search(r"\bproofs? of\b", title, re.I):
            continue
        r = [x for x in refs_in(title) if x in by_label]
        if not r:
            continue
        end = len(nc)
        for hs2, lvl2, _he2, _ab2 in heads[i + 1:]:
            if LEVEL[lvl2] <= LEVEL[lvl]:
                end = hs2
                break
        proof_heads.append((hs, he, end, r))
    env_proofs = list(find_env_spans(nc, "proof"))
    for s, bs, be, e, opt in env_proofs:
        owner = None
        how = "following"
        r = refs_in(opt)
        if r and r[0] in by_label:
            owner, how = by_label[r[0]], "proof of \\ref"
        elif r:
            how = f"proof of undefined label {r[0]}"
        else:
            prev = [n for n in nodes if n["end"] <= s]
            prev_end = prev[-1]["end"] if prev else -1
            head = [h for h in proof_heads if prev_end <= h[0] < s and len(h[3]) == 1]
            if head:
                owner, how = by_label[head[-1][3][0]], "under a 'Proof of' heading"
            elif prev:
                owner = prev[-1]
        proof_spans.append((s, bs, be, owner, how))
    # text of a "Proof of X" section that lies outside nested statements and proofs belongs to X
    nested = sorted([(n["start"], n["end"]) for n in nodes] + [(s, e) for s, bs, be, e, opt in env_proofs])
    for hs, he, end, labs in proof_heads:
        pos = he
        for a, b in nested:
            if b <= he or a >= end:
                continue
            if a > pos:
                for lab in labs:
                    proof_spans.append((pos, pos, a, by_label[lab], "section 'Proof of'"))
            pos = max(pos, b)
        if pos < end:
            for lab in labs:
                proof_spans.append((pos, pos, end, by_label[lab], "section 'Proof of'"))
    inline_rx = re.compile(r"(?:\\(?:textit|emph|textbf|textsc)\s*\{\s*Proof(?: of ([^{}]*?(?:\{[^{}]*\}[^{}]*?)*))?[.:]?\s*\}|"
                           r"\{\\(?:it|bf|em)\s+Proof[^{}]*\}|\\noindent\s*\\textit\{Proof)")
    for m in inline_rx.finditer(nc):
        if any(a <= m.start() < c for a, b, c, o, h in proof_spans):
            continue
        r = [x for x in refs_in(m.group(0)) if x in by_label]
        owner = by_label[r[0]] if r else None
        if owner is None:
            prev = [n for n in nodes if n["end"] <= m.start() and m.start() - n["end"] < 300]
            owner = prev[-1] if prev else None
        if owner is None:
            continue
        stop = re.compile(r"\\(?:qed|qedhere|Box|square|blacksquare|hfill\s*\$\\(?:Box|square|blacksquare))|"
                          r"\\begin\{(?:" + "|".join(re.escape(e) for e in envs) + r")\*?\}|\\(?:sub)*section\b")
        sm = stop.search(nc, m.end())
        end = sm.start() if sm else min(len(nc), m.end() + 4000)
        proof_spans.append((m.start(), m.end(), end, owner, "inline 'Proof.'"))
    node_proofs = defaultdict(list)
    for s, bs, be, owner, how in proof_spans:
        if owner is None:
            continue
        body = nc[bs:be]
        words = len(re.findall(r"[A-Za-z]+", body))
        if how == "section 'Proof of'":
            if words < 15 and not refs_in(body):
                continue
            prev = [p for p in owner["proofs"] if p["how"] == how]
            if prev:
                prev[0]["length_words"] += words
            else:
                owner["proofs"].append({"loc": where(s), "how": how, "length_words": words})
        else:
            owner["proofs"].append({"loc": where(s), "how": how, "length_words": words})
        owner["proof_refs"] += refs_in(body)
        for rm in REF_RX.finditer(body):
            for k in rm.group(1).split(","):
                if k.strip():
                    owner.setdefault("proof_ref_locs", []).append((k.strip(), bs + rm.start(), how))
        for gm in GAP_RX.finditer(body):
            ctx = re.sub(r"\s+", " ", nc[max(bs, bs + gm.start() - 60):min(be, bs + gm.end() + 60)]).strip()
            owner["gaps"].append({"loc": where(bs + gm.start()), "phrase": gm.group(1), "context": ctx[:160]})
        node_proofs[id(owner)].append((bs, be))

    # labels: definition sites and owners ------------------------------------
    label_sites = {}
    for m in LABEL_RX.finditer(nc):
        label_sites.setdefault(m.group(1).strip(), m.start())

    prefixes = [m.group(1) for m in re.finditer(r"\\externaldocument\s*\[([^\]]+)\]\s*\{[^{}]*\}", nc)]

    def canon(lab: str) -> str:
        if lab in label_sites:
            return lab
        for pre in prefixes:
            if lab.startswith(pre) and lab[len(pre):] in label_sites:
                return lab[len(pre):]
        return lab

    def owner_of_label(lab: str):
        lab = canon(lab)
        if lab in by_label:
            return by_label[lab]
        off = label_sites.get(lab)
        if off is None:
            return None
        for n in nodes:
            a, b = n["stmt_span"]
            if a <= off < b:
                return n
        for s, bs, be, owner, how in proof_spans:
            if owner is not None and bs <= off < be:
                return owner
        return None

    all_refs = []
    for m in REF_RX.finditer(nc):
        for k in m.group(1).split(","):
            if k.strip():
                all_refs.append((k.strip(), m.start()))
    undefined = defaultdict(list)
    for k, off in all_refs:
        if canon(k) not in label_sites:
            undefined[k].append(where(off))
    # edges: what a proof uses; from statements only conditions and definitions
    # ("Under Conjecture 1", "with c as in Definition 2"), not pointers such as
    # "cf. Theorem 2". Remarks and examples neither carry nor receive edges.
    edges = defaultdict(set)
    edge_loc = {}
    passive = {"remark", "example", "notation", "question", "problem"}
    for n in nodes:
        if n["kind"] in passive:
            continue
        for k, off, how in n.get("proof_ref_locs", []):
            o = owner_of_label(k)
            if o is not None and o is not n and o["kind"] not in passive:
                edges[n["id"]].add(o["id"])
                tag = "section prose" if how == "section 'Proof of'" else ("inline proof" if how.startswith("inline")
                                                                         else "proof")
                edge_loc.setdefault((n["id"], o["id"]), f"{where(off)}, {tag}")
        for k in n["stmt_refs"]:
            o = owner_of_label(k)
            if o is not None and o is not n and (is_condition(o) or o["kind"] == "definition"):
                edges[n["id"]].add(o["id"])
    ids = {n["id"]: n for n in nodes}
    referenced_by_result = defaultdict(set)
    for a, bs_ in edges.items():
        for b in bs_:
            referenced_by_result[b].add(a)
    referenced_anywhere = set()
    for k, off in all_refs:
        o = owner_of_label(k)
        if o is None:
            continue
        a, b = o["stmt_span"]
        inside_own = (o["start"] <= off < o["end"]) or any(bs <= off < be for bs, be in node_proofs[id(o)])
        if not inside_own:
            referenced_anywhere.add(o["id"])

    # cycles ------------------------------------------------------------------
    cycles, color, stack = [], {}, []

    def dfs(u):
        color[u] = 1
        stack.append(u)
        for v in sorted(edges.get(u, ())):
            if color.get(v, 0) == 0:
                dfs(v)
            elif color.get(v) == 1:
                cyc = stack[stack.index(v):] + [v]
                key = tuple(sorted(set(cyc)))
                if key not in {tuple(sorted(set(c))) for c in cycles}:
                    cycles.append(cyc)
        stack.pop()
        color[u] = 2
    sys.setrecursionlimit(10000)
    for n in nodes:
        if color.get(n["id"], 0) == 0:
            dfs(n["id"])

    # conditional closure -------------------------------------------------------
    cond_ids = {n["id"] for n in nodes if is_condition(n)}
    memo = {}

    def conds(u, seen=None):
        if u in memo:
            return memo[u]
        seen = seen or set()
        if u in seen:
            return set()
        seen.add(u)
        out = set()
        for v in edges.get(u, ()):
            if v in cond_ids:
                out.add(v)
            out |= conds(v, seen)
        memo[u] = out
        return out
    for n in nodes:
        n["depends_on_conditions"] = sorted(conds(n["id"])) if n["id"] not in cond_ids else []
        n["condition_paths"] = {}
        for c in n["depends_on_conditions"]:
            # shortest chain of uses from n to c (BFS), for the report
            prev, frontier, seen = {}, [n["id"]], {n["id"]}
            while frontier and c not in seen:
                nxt = []
                for u in frontier:
                    for v in sorted(edges.get(u, ())):
                        if v not in seen:
                            seen.add(v)
                            prev[v] = u
                            nxt.append(v)
                frontier = nxt
            path, x = [c], c
            while x != n["id"] and x in prev:
                x = prev[x]
                path.append(x)
            n["condition_paths"][c] = list(reversed(path))

    # macros redefined -----------------------------------------------------------
    macro_bodies = defaultdict(list)
    for m in re.finditer(r"\\(re|provide)?newcommand\*?\s*\{?\s*(\\[A-Za-z@]+)\s*\}?\s*(?:\[\d\])?(?:\[[^\]]*\])?\s*\{", nc):
        end = _match_brace(nc, m.end() - 1)
        macro_bodies[m.group(2)].append((re.sub(r"\s+", "", nc[m.end():end - 1]), where(m.start()), m.group(1) or "new"))
    for m in re.finditer(r"\\def\s*(\\[A-Za-z@]+)\s*\{", nc):
        end = _match_brace(nc, m.end() - 1)
        macro_bodies[m.group(1)].append((re.sub(r"\s+", "", nc[m.end():end - 1]), where(m.start()), "def"))
    macro_redef = [{"macro": k, "definitions": [{"loc": l, "via": v, "body": b[:60]} for b, l, v in vs]}
                   for k, vs in macro_bodies.items() if len({b for b, _, _ in vs}) > 1]

    # constants leads in final statements ------------------------------------------
    const_leads = []
    for n in nodes:
        if n["kind"] not in ("theorem", "proposition", "corollary"):
            continue
        a, b = n["stmt_span"]
        for cm in CONST_RX.finditer(nc[a:b]):
            const_leads.append({"id": n["id"], "kind": n["kind"], "loc": where(a + cm.start()), "phrase": cm.group(1)})

    missing = [n for n in nodes if n["kind"] in PROVABLE and not n["proofs"]]
    unused = [n for n in nodes if n["kind"] in ("lemma", "proposition", "claim", "fact") and n["label"]
              and n["id"] not in referenced_by_result]
    tops = [n for n in nodes if n["kind"] == "theorem" or (n["kind"] in ("proposition", "corollary")
                                                         and n["id"] not in referenced_by_result)]
    return {"mains": mains, "nodes": nodes, "edges": {k: sorted(v) for k, v in edges.items()}, "cycles": cycles,
            "edge_loc": {f"{a} -> {b}": l for (a, b), l in edge_loc.items()},
            "undefined": dict(undefined), "missing": missing, "unused": unused, "tops": tops,
            "referenced_anywhere": referenced_anywhere, "const_leads": const_leads, "macro_redef": macro_redef,
            "cond_ids": cond_ids, "ids": ids}


def tree_lines(res: dict, root: str, max_depth: int = 6) -> list[str]:
    ids, edges, cond_ids = res["ids"], res["edges"], res["cond_ids"]
    out, shown = [], set()

    def tag(nid: str) -> str:
        n = ids[nid]
        marks = []
        if nid in cond_ids:
            marks.append("CONDITION")
        elif n["kind"] in PROVABLE and not n["proofs"]:
            marks.append("no proof")
        if n["gaps"]:
            marks.append(f"gaps {len(n['gaps'])}")
        return f"{n['kind']} `{n['label'] or '(unlabeled)'}` ({n['loc']})" + (f" [{', '.join(marks)}]" if marks else "")

    def walk(nid, depth, path):
        pre = "  " * depth + "- "
        if nid in path:
            out.append(pre + tag(nid) + " ↺ cycle")
            return
        if nid in shown and edges.get(nid):
            out.append(pre + tag(nid) + " (expanded above)")
            return
        out.append(pre + tag(nid))
        shown.add(nid)
        if depth >= max_depth:
            if edges.get(nid):
                out.append("  " * (depth + 1) + "- …")
            return
        for v in sorted(edges.get(nid, ())):
            if v in ids:
                walk(v, depth + 1, path | {nid})
    walk(root, 0, frozenset())
    return out


def write(res: dict, out: str):
    os.makedirs(out, exist_ok=True)
    nodes = res["nodes"]
    counts = defaultdict(int)
    for n in nodes:
        counts[n["kind"]] += 1
    gaps = [(n, g) for n in nodes for g in n["gaps"]]
    cond = [n for n in nodes if n["depends_on_conditions"]]
    text_cond = [n for n in nodes if n["text_condition"] and n["kind"] in PROVABLE and not n["depends_on_conditions"]]
    L = [f"# Proof map: {', '.join('`' + m + '`' for m in res['mains'])}", "",
         "Leads for the proof audit, not verdicts. References typed by hand ('Theorem 3') are not tracked.", "",
         "| item | count |", "|---|---|",
         f"| results by kind | {', '.join(f'{k} {v}' for k, v in sorted(counts.items(), key=lambda x: -x[1]))} |",
         f"| (b) dependency cycles | {len(res['cycles'])} |",
         f"| (c) provable results without a proof (not cited) | {sum(1 for n in res['missing'] if not n['cited'])} |",
         f"| (c') provable results without a proof but with a citation nearby | {sum(1 for n in res['missing'] if n['cited'])} |",
         f"| (d) results depending on a conjecture / assumption / hypothesis | {len(cond)} |",
         f"| (d') results naming a condition in words without a reference | {len(text_cond)} |",
         f"| (e) labels referenced but never defined | {len(res['undefined'])} |",
         f"| (f) lemmas / propositions not used by any other result | {len(res['unused'])} |",
         f"| (g) gap phrases in proofs | {len(gaps)} |",
         f"| (h) constant / effectivity leads in final statements | {len(res['const_leads'])} |",
         f"| (i) macros defined with different bodies | {len(res['macro_redef'])} |", ""]
    L += ["## Results", "", "| id | kind | location | proof(s) | uses | used by | conditions | gaps | statement |",
          "|---|---|---|---|---|---|---|---|---|"]
    used_by = defaultdict(int)
    for a, bs_ in res["edges"].items():
        for b in bs_:
            used_by[b] += 1
    for n in nodes:
        pr = "; ".join(f"{p['loc']} ({p['how']}, {p['length_words']} w)" for p in n["proofs"]) or \
            ("—" if n["kind"] not in PROVABLE else ("cited?" if n["cited"] else "**none**"))
        L.append(f"| `{n['id']}` | {n['kind']} | {n['loc']} | {pr} | {len(res['edges'].get(n['id'], []))} | "
                 f"{used_by.get(n['id'], 0)} | {', '.join(n['depends_on_conditions']) or ''} | {len(n['gaps']) or ''} | "
                 f"{n['statement'][:110].replace('|', '/')} |")
    L += ["", "## (a) Dependency trees of top-level results", ""]
    budget = 600
    for t in res["tops"]:
        lines = tree_lines(res, t["id"])
        if budget <= 0:
            L.append(f"- … (more trees in proof_map.json)")
            break
        L += lines[:budget] + [""]
        budget -= len(lines)
    L += ["## (b) Cycles", ""]
    L += ["A cycle is circular reasoning only if each reference is a real use. A proof that merely mentions a "
          "consequence ('Corollary 2 follows') also closes a loop; check each edge at its location.", ""]
    for c in res["cycles"]:
        steps = [f"`{a}` uses `{b}` at {res['edge_loc'].get(f'{a} -> {b}', '?')}" for a, b in zip(c, c[1:])]
        L.append("- " + "; ".join(steps))
    if not res["cycles"]:
        L.append("none")
    L += ["", "## (c) Provable results without a proof", "",
          "Each needs a proof, a precise citation, or a note that it is immediate from a named result.", ""]
    L += [f"- {n['kind']} `{n['id']}` ({n['loc']}){' — citation nearby' if n['cited'] else ''}: {n['statement'][:120]}"
          for n in res["missing"]] or ["none"]
    L += ["", "## (d) Conditional chains", "",
          "If a dependency is real, every statement of the result (abstract, introduction, conclusion) must carry the "
          "condition. Check each chain at its locations first: a reference in section prose or a comparison with a "
          "conjecture's equation is often a pointer, not a use.", ""]
    for n in cond:
        L.append(f"- {n['kind']} `{n['id']}` ({n['loc']}) depends on: "
                 f"{', '.join('`' + c + '`' for c in n['depends_on_conditions'])}")
        for c, path in n["condition_paths"].items():
            if len(path) > 1:
                steps = [f"`{a}` → `{b}` ({res['edge_loc'].get(f'{a} -> {b}', 'statement')})" for a, b in zip(path, path[1:])]
                L.append("  - chain: " + "; ".join(steps))
    if not cond:
        L.append("none")
    if text_cond:
        L += ["", "Results that name a condition in words (assuming / under the hypothesis …) without a reference:", ""]
        L += [f"- {n['kind']} `{n['id']}` ({n['loc']}): {n['statement'][:120]}" for n in text_cond]
    L += ["", "## (e) Undefined labels", ""]
    L += [f"- `{k}`: {', '.join(v[:5])}" for k, v in sorted(res["undefined"].items())] or ["none"]
    L += ["", "## (f) Lemmas and propositions not used by any other result", "",
          "Either dead weight, or used implicitly ('by the previous lemma') - make the dependency explicit.", ""]
    L += [f"- {n['kind']} `{n['id']}` ({n['loc']}){' — referenced in the text' if n['id'] in res['referenced_anywhere'] else ' — never referenced'}"
          for n in res["unused"]] or ["none"]
    L += ["", "## (g) Gap phrases in proofs", "", "| loc | result | phrase | context |", "|---|---|---|---|"]
    for n, g in gaps[:400]:
        L.append(f"| {g['loc']} | `{n['id']}` | {g['phrase']} | {g['context'].replace('|', '/')[:140]} |")
    L += ["", "## (h) Constant and effectivity leads in final statements", "",
          "Check that every constant is explicit or its dependence is stated, and whether the result is vacuous at "
          "practical parameters.", ""]
    L += [f"- {c['kind']} `{c['id']}` ({c['loc']}): {c['phrase']}" for c in res["const_leads"]] or ["none"]
    L += ["", "## (i) Macros defined with different bodies", ""]
    L += [f"- `{m['macro']}`: " + "; ".join(f"{d['loc']} ({d['via']}) `{d['body']}`" for d in m["definitions"])
          for m in res["macro_redef"]] or ["none"]
    with open(os.path.join(out, "proof_map.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    js = {k: v for k, v in res.items() if k not in ("ids", "referenced_anywhere", "cond_ids", "tops", "missing",
                                                     "unused", "nodes")}
    js["nodes"] = [{k: v for k, v in n.items() if k not in ("stmt_span",)} for n in nodes]
    js["missing"] = [n["id"] for n in res["missing"]]
    js["unused"] = [n["id"] for n in res["unused"]]
    js["conditions"] = sorted(res["cond_ids"])
    with open(os.path.join(out, "proof_map.json"), "w", encoding="utf-8") as fh:
        json.dump(js, fh, ensure_ascii=False, indent=1, default=list)
    print(f"{len(nodes)} results; cycles {len(res['cycles'])}; no proof {len(res['missing'])}; conditional "
          f"{len(cond)}; undefined labels {len(res['undefined'])}; unused {len(res['unused'])}; gap phrases "
          f"{len(gaps)}; constant leads {len(res['const_leads'])}; macro redefinitions {len(res['macro_redef'])} "
          f"-> {out}/proof_map.md")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mains", nargs="+", help="top-level .tex files (main text, supplement)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    write(build(args.mains), args.out)


if __name__ == "__main__":
    main()
