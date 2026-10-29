#!/usr/bin/env python3
"""hedge_scan.py - measure the editor-facing parts of a manuscript and flag
defensive or overclaiming phrasing.

An editor deciding whether to send a paper out reads the title, the abstract,
the first page or two of the introduction, and the Fig. 1 caption. This script
measures those parts with one fixed convention so that our manuscript and the
exemplar papers are counted the same way.

Usage
  hedge_scan.py main.tex                     markdown report on stdout
  hedge_scan.py main.tex --json scan.json    also write JSON
  hedge_scan.py draft.tex --sections abstract,introduction
  hedge_scan.py exemplars/*.md --summary     median [min-max] over many files
  hedge_scan.py abstract.txt --text          whole file is one 'abstract'

Input formats
  .tex  sections found from \\begin{abstract}, \\section{Introduction} (or the
        text before the first \\section for PRL-style papers), and a
        conclusion/discussion/outlook/summary section. \\input/\\include are
        followed. Line numbers in the report refer to the source files.
  .docx Word manuscripts (standard library only); locations are paragraph numbers.
  .pdf  via pdftotext when it is installed.
  .md / .txt  heading lines (markdown '#', numbered, ALL CAPS, or IMRaD words such
        as Background / Methods / Results / Discussion); the format exemplar_meta.py writes.
  --text treats the whole file as one abstract.

The scan only finds leads. Every hit has to be read in context before it is
called a problem: 'may' is right for a conjecture, and 'optimal' is right
when a theorem says so.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys

# ---------------------------------------------------------------------------
# Pattern catalogue. Codes match references/defensive-patterns.md.
# D* = defensive, O* = possible overclaim (check against the claim ledger),
# S  = scope qualifier (counted, not a defect by itself).
# ---------------------------------------------------------------------------
PATTERNS: dict[str, tuple[str, list[str]]] = {
    "D1": ("negative scope / disclaimer", [
        r"\bwe (?:do|did) not (?:claim|assert|suggest|imply|prove|show|address|consider|attempt|study|treat|promote)\b",
        r"\b(?:we )?make no claims?\b",
        r"\bno claims?\b",
        r"\b(?:does|do|did) not (?:imply|mean|show|establish|prove|follow|entail)\b",
        r"\bis not (?:meant|intended|designed|claimed) to\b",
        r"\bshould not be (?:read|interpreted|taken|construed|understood)\b",
        r"\bwithout (?:promoting|claiming|implying|asserting|suggesting)\b",
        r"\bwe (?:caution|stress|emphasi[sz]e) that\b",
        r"\bit is important to (?:note|stress|emphasi[sz]e|clarify)\b",
        r"\b(?:beyond|outside) (?:the |our )?scope\b",
        r"\blies? outside\b",
        r"\bworth clarifying\b",
        r"\boverinterpret\w*\b",
    ]),
    "D2": ("concession-first sentence", []),  # sentence-level check below
    "D4": ("diluted contribution", [
        r"\bwe (?:attempt|try|aim|seek|hope|endeavou?r)\b",
        r"\b(?:take|takes|taking|took) (?:a |the )?(?:first |small |modest |preliminary |initial )?steps?\b",
        r"\bpreliminary\b",
        r"\bmodest (?:step|contribution|attempt|goal|aim|improvement|progress|advance|result)s?\b",
        r"\bshed(?:s|ding)? (?:some |new )?light\b",
        r"\bcomplementary (?:perspective|view|viewpoint|approach|angle)\b",
        r"\bsome insights?\b",
        r"\bfirst attempt\b",
    ]),
    "D5": ("modal hedge", [
        r"\b(?:may|might|could|can) (?:potentially|possibly|perhaps|conceivably)\b",
        r"\b(?:possibly|potentially|perhaps|presumably|arguably|conceivably|seemingly)\b",
        r"\b(?:seems?|appears?) to\b",
        r"\bto (?:some|a certain|a limited) (?:extent|degree)\b",
        r"\bin some sense\b",
        r"\bsomewhat\b",
        r"\btends? to\b",
        r"\bmay\b",
        r"\bmight\b",
        r"\bwe (?:believe|hope|speculate|feel)\b",
    ]),
    "D6": ("vague gap", [
        r"\b(?:remains?|remained) (?:largely |relatively |still |so far |poorly |mostly )?(?:unexplored|unknown|unclear|elusive|understudied|poorly understood|not well understood)\b",
        r"\b(?:has|have) (?:received|attracted) (?:little|limited|scant|less) attention\b",
        r"\blittle is known\b",
        r"\banecdotal(?:ly)?\b",
        r"\bto the best of our knowledge\b",
        r"\bnot (?:yet )?(?:well|fully) understood\b",
    ]),
    "D8": ("version / internal history", [
        r"\b(?:prior|previous|earlier|original|first|older) version\b",
        r"\bthis (?:revision|revised (?:version|manuscript))\b",
        r"\blegacy\b",
        r"\bhistorical(?:ly)?\b",
    ]),
    "D10": ("ownerless passive", [
        r"\bit (?:is|was|can be|could be|has been|will be) (?:shown|proven|proved|found|demonstrated|established|argued|observed|verified)\b",
    ]),
    "D12": ("filler / throat-clearing", [
        r"\bit (?:is|should be) (?:worth )?(?:noting|noted|mentioning|mentioned|pointing out|stressing)\b",
        r"\bneedless to say\b",
        r"\bit is (?:interesting|important|crucial) to\b",
        r"\binterestingly\b",
    ]),
    "D13": ("'not X but Y' framing", [
        r"\bnot (?:only|merely|just|simply) (?:a|an|the)\b",
        r"\bis not (?:a|an|the)\b[^.;:]{1,80}?\bbut\b",
    ]),
    "D15": ("work-report narrative (chronology instead of argument)", [
        r"\bwe (?:first|then|next|subsequently|later|finally) (?:tried|attempted|ran|performed|conducted|implemented|"
        r"tested|explored|checked|considered|looked at|collected|built|trained|repeated)\b",
        r"(?:^|[.;]\s+)(?:Next|Then|After that|Afterwards|Subsequently),? we\b",
        r"\bwe (?:performed|conducted|carried out|ran|did) (?:a (?:series|set|number) of |several |some |many |extensive |"
        r"various |multiple )?(?:experiments|simulations|tests|analyses|evaluations|benchmarks)\b(?! (?:to|that|which|showing|testing))",
    ]),
    "D16": ("local weakness stated as global", [
        # Intransitive uses only: "may not generalize." is flagged; "may not generalize to unseen sites" names
        # the condition, and "does not hold randomness" is a different verb sense.
        r"\b(?:may|might|could|does|do|did|will) not (?:generali[sz]e|scale)\b(?! (?:to|for|when|beyond|if|in|on|across|"
        r"with|past|the|a|an|this|these|its|our|their) )",
        r"\b(?:may|might|could) not (?:transfer|extend|apply|hold|work)\b(?! (?:to|for|when|beyond|if|in|on|across|"
        r"with|under|outside|the|a|an|this|these|its|our|their) )",
        r"\bin (?:some|certain) (?:cases|settings|scenarios|situations|instances)\b",
        r"\b(?:our|the|this|the proposed) (?:method|approach|framework|model|analysis|study|technique|algorithm)s? "
        r"(?:is|are|remains?|has been) (?:still |somewhat |inherently )?limited\b(?! (?:to|by) )",
        r"\b(?:has|have) (?:some|several|certain|inherent) limitations\b",
        r"\bnot (?:always|universally|generally) (?:applicable|reliable|effective|accurate)\b",
    ]),
    "O": ("overclaim flag (check ledger)", [
        r"\bfor the first time\b",
        r"\bthe first (?:\w+ )?(?:demonstration|proof|result|framework|method|study|work|example|evidence|bound|algorithm)\b",
        r"\bnovel\b",
        r"\bunprecedented\b",
        r"\brevolution(?:ary|i[sz]es?)\b",
        r"\bgroundbreaking\b",
        r"\bparadigm\b",
        r"\buniversal(?:ly)?\b",
        r"\blaws?\b",
        r"\bfundamental(?:ly)?\b",
        r"\bdefinitive(?:ly)?\b",
        r"\bcompletely (?:solve|resolve|settle|characteri[sz]e)\w*\b",
        r"\b(?:optimal|optimality|tight|sharp)\b",
        r"\borders? of magnitude\b",
        r"\bstate[- ]of[- ]the[- ]art\b",
        r"\bdramatic(?:ally)?\b",
        r"\bsolves?\b",
        r"\b(?:this|which|that|these|results?|data|findings?|evidence|study)\s+(?:clearly\s+)?prov(?:es|e|en)\b",
        r"\b(?:clearly|undoubtedly|definitely|conclusively|unequivocally)\b",
        r"\bbreakthrough\b",
    ]),
    "OC": ("causal wording (check the design supports it)", [
        r"\b(?:causes?|caused|causing)\b",
        r"\bleads? to\b|\bled to\b",
        r"\bresults? in\b",
        r"\b(?:drives?|driven by)\b",
        r"\b(?:the )?(?:causal )?effects? of\b",
        r"\bimpact of\b",
    ]),
    "OS": ("'significant' (check a test is reported, or reword)", [
        r"\bsignificant(?:ly)?\b",
        r"\bhighly significant\b",
    ]),
    "S": ("scope qualifier (count only)", [
        r"\bunder (?:the |our |these |this |an? |one |mild |standard |additional |stated |reasonable )?(?:\w+[ ,]+){0,3}?(?:assumptions?|hypothes[ie]s|conditions?|model|conjecture)\b",
        r"\bprovided (?:that )?\b",
        r"\bassuming\b",
        r"\b(?:only|exclusively) (?:for|when|if|in)\b",
        r"\bdisclosed\b",
        r"\bwithin (?:this|the|our|these|that) (?:[\w-]+ ){0,3}?(?:family|families|model|setting|class|regime|framework|convention)s?\b",
        r"\bin (?:this|the|our) (?:[\w-]+ ){0,2}?(?:model|setting|regime)\b(?! of)",
        r"\bsubject to\b",
    ]),
}

RESULT_VERBS = re.compile(
    r"\b(?:we|here we|this (?:paper|work|letter|article)|our (?:main |first |central |key )?results?)\s+"
    r"(?:also |then |further |rigorously |explicitly )?"
    r"(?:prove|proves|show|shows|establish|establishes|derive|derives|find|finds|demonstrate|demonstrates|"
    r"obtain|obtains|construct|constructs|determine|determines|identify|identifies|compute|computes|"
    r"report|reports|resolve|resolves|answer|answers)\b"
    r"|\b(?:we|here we|this (?:paper|work|letter|article))\s+(?:develop|design|present|give|introduce|propose|construct)s?"
    r" (?:a |an |the |new |two |three )?(?:[\w-]+ ){0,3}?(?:proofs?|bounds?|algorithms?|protocols?|schemes?|"
    r"constructions?|methods?|circuits?|codes?|compilers?|techniques?|procedures?)\b",
    re.I,
)
UNIVERSAL_CLAIM = re.compile(
    r"\b(?:any|every)\s+[\w-]+(?:\s+[\w-]+)?\s+(?:that|which|who|whose|with)\b[^.;]{0,160}?\b(?:must|requires?|obeys?|needs?|cannot|satisf(?:y|ies)|pays?|"
    r"incurs?|costs?|is at least|are at least|is bounded|scales?)\b",
    re.I,
)
FRAMING_VERBS = re.compile(
    r"\bwe (?:formali[sz]e|explore|study|investigate|consider|examine|discuss|introduce|propose|develop|"
    r"address|analy[sz]e|revisit|describe|define|model)\b",
    re.I,
)
CONCESSION_START = re.compile(
    r"\s*(?:Although|Though|While|Whilst|Despite|Admittedly|Of course|Granted|Notwithstanding|Even though|Even if)\b"
)
NUMBER = re.compile(r"(?<![A-Za-z_])\d[\d,]*(?:\.\d+)?(?:\s?(?:%|×|x\b|-fold\b))?")

LIB = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "lib")
sys.path.insert(0, os.path.normpath(LIB))
from texutil import (  # noqa: E402
    WORD, Source, clean_latex, doc_captions, doc_sections, is_structured_abstract, light_clean, load_document,
    paragraphs, sentences, snippet, _line_of,
)

def measure(name: str, cleaned: str, stats: dict, src: Source | None, base_line: int,
            note: str = "") -> dict:
    words = WORD.findall(cleaned)
    nwords = len(words)
    sents = sentences(cleaned)
    first_result = None
    result_sent_count = 0
    for k, (a, b) in enumerate(sents, 1):
        if RESULT_VERBS.search(cleaned[a:b]) or UNIVERSAL_CLAIM.search(cleaned[a:b]):
            result_sent_count += 1
            if first_result is None:
                first_result = (k, re.sub(r"\s+", " ", cleaned[a:b]).strip()[:160])
    framing = len(FRAMING_VERBS.findall(cleaned))
    paras = paragraphs(cleaned)
    first_result_para = None
    if first_result is not None:
        a = sents[first_result[0] - 1][0]
        first_result_para = len([p for p in re.split(r"\n\s*\n|\\par\b", cleaned[:a]) if WORD.search(p)]) or 1

    hits = []

    def add_hit(code, a, b):
        line_idx = base_line + _line_of(cleaned, a)
        f, ln = src.loc(line_idx) if src else ("", 0)
        hits.append({"code": code, "match": re.sub(r"\s+", " ", cleaned[a:b]), "file": f, "line": ln,
                     "context": snippet(cleaned, a, b)})

    for code, (_label, rxs) in PATTERNS.items():
        seen = set()
        for rx in rxs:
            for m in re.finditer(rx, cleaned, re.I):
                if any(m.start() < e and s < m.end() for s, e in seen):
                    continue
                seen.add((m.start(), m.end()))
                add_hit(code, m.start(), m.end())
    for a, b in sents:
        m = CONCESSION_START.match(cleaned[a:b])
        # "While X costs more, we prove Y" puts the cost in a subordinate clause
        # and the result in the main clause: that is the good pattern.
        if m and not (RESULT_VERBS.search(cleaned[a:b]) or UNIVERSAL_CLAIM.search(cleaned[a:b])):
            lead = len(m.group(0)) - len(m.group(0).lstrip())  # report the line of the word, not of the whitespace
            add_hit("D2", a + m.start() + lead, a + m.end())

    counts: dict[str, int] = {}
    for h in hits:
        counts[h["code"]] = counts.get(h["code"], 0) + 1
    defensive = sum(v for k, v in counts.items() if k.startswith("D"))
    res = {
        "section": name,
        "note": note,
        "words": nwords,
        "sentences": len(sents),
        "paragraphs": paras,
        "mean_sentence_words": round(nwords / len(sents), 1) if sents else 0,
        "inline_math": len(re.findall(r"\bMATH\b", cleaned)),
        "display_math": stats.get("display_math", 0),
        "citations": stats.get("citations", 0),
        "numbers": len(NUMBER.findall(cleaned)),
        "first_result_sentence": first_result[0] if first_result else None,
        "first_result_paragraph": first_result_para,
        "first_result_text": first_result[1] if first_result else None,
        "result_sentences": result_sent_count,
        "framing_verbs": framing,
        "bullets": cleaned.count("\u2022"),
        "defensive_hits": defensive,
        "defensive_per_100w": round(100 * defensive / nwords, 2) if nwords else 0,
        "overclaim_flags": counts.get("O", 0) + counts.get("OC", 0) + counts.get("OS", 0),
        "scope_qualifiers": counts.get("S", 0),
        "counts": counts,
        "hits": sorted(hits, key=lambda h: (h["file"], h["line"], h["code"])),
    }
    return res


def analyse(path: str, plain: bool = False, wanted: set[str] | None = None) -> dict:
    src, kind = load_document(path, plain)
    is_tex = kind == "tex"
    text = src.text
    if plain:
        secs = {"abstract": (0, len(text), "whole file")}
    else:
        secs = doc_sections(text, kind)
    report = {"file": path, "sections": {}, "captions": []}
    for name in ("title", "abstract", "introduction", "conclusion"):
        if name not in secs or (wanted and name not in wanted):
            continue
        a, b, note = secs[name]
        chunk = text[a:b]
        cleaned, stats = clean_latex(chunk) if is_tex else light_clean(chunk)
        base = _line_of(text, a)
        if name == "title":
            report["sections"]["title"] = {"section": "title", "text": re.sub(r"\s+", " ", cleaned).strip(),
                                           "words": len(WORD.findall(cleaned)),
                                           "question": "?" in cleaned}
            continue
        report["sections"][name] = measure(name, cleaned, stats, src, base, note)
        if name == "abstract":
            report["sections"][name]["structured"] = is_structured_abstract(chunk)
        f0, l0 = src.loc(base)
        f1, l1 = src.loc(_line_of(text, b))
        report["sections"][name]["span"] = f"{f0}:{l0}-{l1}" if f0 == f1 else f"{f0}:{l0} - {f1}:{l1}"
    if not plain and (not wanted or "captions" in wanted):
        for k, (a, b) in enumerate(doc_captions(text, kind), 1):
            cleaned, _ = clean_latex(text[a:b]) if is_tex else light_clean(text[a:b])
            f, ln = src.loc(_line_of(text, a))
            report["captions"].append({"index": k, "file": f, "line": ln, "words": len(WORD.findall(cleaned)),
                                       "start": re.sub(r"\s+", " ", cleaned).strip()[:90]})
    return report


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------
METRIC_ROWS = [
    ("paragraphs", "paragraphs"),
    ("words", "words"),
    ("sentences", "sentences"),
    ("mean_sentence_words", "mean words / sentence"),
    ("inline_math", "inline math"),
    ("display_math", "display math"),
    ("numbers", "numbers"),
    ("citations", "citations"),
    ("first_result_sentence", "first result sentence (proxy)"),
    ("first_result_paragraph", "first result paragraph (proxy)"),
    ("result_sentences", "result-verb sentences"),
    ("framing_verbs", "framing verbs (formalize/study/...)"),
    ("bullets", "bulleted items"),
    ("defensive_hits", "defensive hits (D*)"),
    ("defensive_per_100w", "defensive hits / 100 words"),
    ("scope_qualifiers", "scope qualifiers (S)"),
    ("overclaim_flags", "overclaim flags (O)"),
]


def to_markdown(rep: dict, max_hits: int = 80) -> str:
    out = [f"# hedge_scan: `{rep['file']}`", ""]
    t = rep["sections"].get("title")
    if t:
        out += [f"**Title** ({t['words']} words{', question' if t['question'] else ''}): {t['text']}", ""]
    for name in ("abstract", "introduction", "conclusion"):
        s = rep["sections"].get(name)
        if not s:
            continue
        head = f"## {name.capitalize()}"
        if s.get("span"):
            head += f" (`{s['span']}`)"
        if s.get("note"):
            head += f" - {s['note']}"
        out += [head, "", "| metric | value |", "|---|---|"]
        for key, label in METRIC_ROWS:
            if name != "abstract" and key in ("first_result_sentence",):
                continue
            out.append(f"| {label} | {s[key] if s[key] is not None else '-'} |")
        if s.get("structured"):
            out += ["", "Structured abstract (labelled Background/Methods/Results/...): several paragraphs are expected; "
                    "compare with exemplars from the same journal."]
        if s.get("first_result_text"):
            out += ["", f"First result-verb sentence: \u201c{s['first_result_text']}\u201d"]
        cats = ", ".join(f"{k} {PATTERNS[k][0]}: {v}" for k, v in sorted(s["counts"].items()) if k in PATTERNS)
        if cats:
            out += ["", f"By category: {cats}"]
        hits = [h for h in s["hits"] if h["code"] != "S"]
        if hits:
            out += ["", "| loc | code | match | context |", "|---|---|---|---|"]
            for h in hits[:max_hits]:
                ctx = h["context"].replace("|", "\\|")
                out.append(f"| {h['file']}:{h['line']} | {h['code']} | {h['match']} | {ctx} |")
            if len(hits) > max_hits:
                out.append(f"| ... | | {len(hits) - max_hits} more in JSON | |")
        out.append("")
    if rep["captions"]:
        long = [c for c in rep["captions"] if c["words"] > 120]
        out += ["## Captions", "",
                f"{len(rep['captions'])} captions; first caption {rep['captions'][0]['words']} words "
                f"(`{rep['captions'][0]['file']}:{rep['captions'][0]['line']}`).", ""]
        if long:
            out += ["Captions over 120 words:", ""]
            out += [f"- `{c['file']}:{c['line']}` {c['words']} words: {c['start']}..." for c in long]
            out.append("")
    out += ["Codes: " + "; ".join(f"{k} = {v[0]}" for k, v in PATTERNS.items()),
            "Hits are leads, not verdicts. Read each in context (references/defensive-patterns.md)."]
    return "\n".join(out)


def summary_markdown(reps: list[dict]) -> str:
    out = [f"# hedge_scan summary over {len(reps)} files", ""]
    for name in ("abstract", "introduction"):
        rows = [r["sections"][name] for r in reps if name in r["sections"]]
        if not rows:
            continue
        out += [f"## {name.capitalize()} (n = {len(rows)})", "", "| metric | median | min | max |", "|---|---|---|---|"]
        for key, label in METRIC_ROWS:
            vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
            if not vals:
                continue
            med = statistics.median(vals)
            out.append(f"| {label} | {round(med, 2)} | {min(vals)} | {max(vals)} |")
        out += ["", "| file | words | sent. | paras | math | 1st result sent. | D/100w | S | O |",
                "|---|---|---|---|---|---|---|---|---|"]
        for r in reps:
            s = r["sections"].get(name)
            if s:
                out.append(f"| {os.path.basename(r['file'])} | {s['words']} | {s['sentences']} | {s['paragraphs']} | "
                           f"{s['inline_math']} | {s['first_result_sentence'] or '-'} | {s['defensive_per_100w']} | "
                           f"{s['scope_qualifiers']} | {s['overclaim_flags']} |")
        out.append("")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", help="write the full result (all hits) to this JSON file")
    ap.add_argument("--text", action="store_true", help="treat each file as one plain-text abstract")
    ap.add_argument("--sections", help="comma list: title,abstract,introduction,conclusion,captions")
    ap.add_argument("--summary", action="store_true", help="distribution over all files instead of per-file reports")
    ap.add_argument("--max-hits", type=int, default=80)
    args = ap.parse_args(argv)
    wanted = set(args.sections.split(",")) if args.sections else None
    reps = [analyse(f, plain=args.text, wanted=wanted) for f in args.files]
    if args.summary:
        print(summary_markdown(reps))
    else:
        print("\n\n".join(to_markdown(r, args.max_hits) for r in reps))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(reps if len(reps) > 1 else reps[0], fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
