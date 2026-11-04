"""designcheck.py - checks shared by research-poster and group-meeting-deck.

Each check adds findings (FAIL, WARN or INFO) with a code, a location and a message. The report lists
FAIL first; the exit code is 1 when any FAIL remains, else 0. Findings are leads to read in context:
a number missing from the source may come from a source that was not passed in.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import designkit as dk          # noqa: E402
import slidespec as ss          # noqa: E402

LEVELS = ("FAIL", "WARN", "INFO")

TITLES = {
    "en": {"FAIL": "Must fix", "WARN": "Check", "INFO": "For information", "none": "Nothing found.",
           "summary": "Summary", "where": "where", "code": "code", "msg": "finding"},
    "zh": {"FAIL": "必须修改", "WARN": "需要核对", "INFO": "供参考", "none": "未发现问题。",
           "summary": "汇总", "where": "位置", "code": "代码", "msg": "发现"},
}


class Findings:
    def __init__(self):
        self.rows: list[dict] = []

    def add(self, level: str, code: str, where: str, msg: str):
        row = {"level": level, "code": code, "where": where, "message": msg}
        if row not in self.rows:
            self.rows.append(row)

    def count(self, level: str) -> int:
        return sum(1 for r in self.rows if r["level"] == level)

    def exit_code(self) -> int:
        return 1 if self.count("FAIL") else 0

    def markdown(self, title: str, header_lines: list[str], lang: str = "en", sections: list[str] | None = None) -> str:
        T = TITLES.get(lang, TITLES["en"])
        out = [f"# {title}", "", f"Date: {dt.date.today().isoformat()}", *header_lines, ""]
        out.append(f"**{T['summary']}:** FAIL {self.count('FAIL')} · WARN {self.count('WARN')} · "
                   f"INFO {self.count('INFO')}")
        out.append("")
        for lv in LEVELS:
            rows = [r for r in self.rows if r["level"] == lv]
            if not rows:
                continue
            out += [f"## {lv}: {T[lv]} ({len(rows)})", "", f"| {T['code']} | {T['where']} | {T['msg']} |",
                    "|---|---|---|"]
            out += [f"| {r['code']} | {r['where']} | {r['message'].replace('|', '/')} |" for r in rows]
            out.append("")
        if not self.rows:
            out.append(T["none"])
        for sec in sections or []:
            out += ["", sec]
        return "\n".join(out) + "\n"

    def write(self, outdir: str, title: str, header_lines: list[str], lang: str = "en", extra: dict | None = None,
              sections: list[str] | None = None) -> tuple[str, str]:
        os.makedirs(outdir, exist_ok=True)
        md = os.path.join(outdir, "check.md")
        js = os.path.join(outdir, "check.json")
        with open(md, "w", encoding="utf-8") as fh:
            fh.write(self.markdown(title, header_lines, lang, sections))
        with open(js, "w", encoding="utf-8") as fh:
            json.dump({"findings": self.rows, **(extra or {})}, fh, ensure_ascii=False, indent=1)
        return md, js


def load_sources(paths: list[str]) -> tuple[str, list[str]]:
    """Plain text of every source (manuscripts via texutil; data files read as text). Returns (text, errors)."""
    texts, errs = [], []
    for p in paths:
        if not p:
            continue
        if not os.path.exists(p):
            errs.append(f"source not found: {p}")
            continue
        ext = os.path.splitext(p)[1].lower()
        try:
            if ext in (".tex", ".docx", ".pdf", ".md", ".txt"):
                import texutil
                src, _kind = texutil.load_document(p)
                texts.append(src.text if hasattr(src, "text") else str(src))
            else:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    texts.append(fh.read())
        except Exception as e:      # noqa: BLE001 - report and continue with the other sources
            errs.append(f"{p}: {e}")
    return "\n".join(texts), errs


def check_placeholders(f: Findings, where_text: list[tuple[str, str]], level: str = "FAIL"):
    for where, text in where_text:
        for ph in dk.placeholders(text):
            f.add(level, "PLACEHOLDER", where, f"placeholder left: {ph[:80]}")


def check_numbers(f: Findings, where_text: list[tuple[str, str]], source: str, include_small: bool = False):
    rows = []
    for where, text in where_text:
        for r in dk.trace_numbers(text, source, include_small):
            r["where"] = where
            rows.append(r)
            if r["status"] == "NOT-IN-SOURCE":
                f.add("FAIL", "NUM-NOT-IN-SOURCE", where, f"{r['number']} is not in the sources: …{r['context']}…")
            elif r["status"] == "SCALED":
                f.add("WARN", "NUM-SCALED", where, f"{r['number']} matches {r['source_match']} only after ×100 or "
                                                    f"÷100 (percent vs fraction?)")
            elif r["status"] == "ROUNDED":
                f.add("INFO", "NUM-ROUNDED", where, f"{r['number']} is {r['source_match']} rounded")
    return rows


def check_claims(f: Findings, where_text: list[tuple[str, str]], source: str):
    for where, text in where_text:
        for r in dk.claim_drift(text, source):
            if r["source"] is None:
                continue
            if r["added_strength"]:
                f.add("WARN", "CLAIM-STRONGER", where, f"adds {', '.join(r['added_strength'])} to the source "
                                                       f"sentence: “{r['source'][:140]}”")
            if r["dropped_qualifiers"]:
                f.add("WARN", "QUALIFIER-DROPPED", where, f"drops {', '.join(r['dropped_qualifiers'])} from the "
                                                          f"source sentence: “{r['source'][:140]}”")


def check_contrast(f: Findings, pairs: list[tuple[str, str, str, bool]], where: str = "style"):
    for name, fg, bg, large in pairs:
        if not (dk.is_hex(fg) and dk.is_hex(bg)):
            continue
        c = dk.contrast(fg, bg)
        need = 3.0 if large else 4.5
        if c < need:
            f.add("FAIL", "CONTRAST", where, f"{name}: {fg} on {bg} has contrast {c:.2f}:1 (needs {need}:1)")
        elif c < need + 1.0:
            f.add("INFO", "CONTRAST", where, f"{name}: {fg} on {bg} has contrast {c:.2f}:1 (passes; projectors "
                                             "wash out colours, more is safer)")


def check_cvd(f: Findings, colours: dict[str, str], where: str = "style"):
    for kind, a, b, d in dk.palette_report({k: v for k, v in colours.items() if dk.is_hex(v)}, 12.0):
        if kind != "normal":
            f.add("WARN", "CVD", where, f"{a} and {b} are hard to tell apart under {kind}opia (ΔE {d}); do not "
                                        "rely on these two colours alone to carry meaning")


def check_dpi(f: Findings, placed: list[dict], warn_ppi: float, fail_ppi: float, medium: str):
    for p in placed:
        info = p.get("info") or {}
        ppi = dk.effective_dpi(info, p["w_in"])
        name = os.path.basename(p["src"])
        if ppi is None:
            continue
        if ppi < fail_ppi:
            f.add("FAIL", "IMG-RESOLUTION", p["where"], f"{name}: {info['w']}×{info['h']} px placed "
                  f"{p['w_in']:.1f} in wide = {ppi:.0f} px/in; below {fail_ppi:.0f} px/in it looks blurred "
                  f"{medium} (export at higher resolution or as PDF/SVG)")
        elif ppi < warn_ppi:
            f.add("WARN", "IMG-RESOLUTION", p["where"], f"{name}: {ppi:.0f} px/in at the placed size "
                  f"({warn_ppi:.0f}+ recommended {medium})")


def check_ledger(f: Findings, spec: ss.Spec, ledger: str, where_of_block, since: str | None = None):
    """Status chips that claim more than the ledger records, IDs the ledger does not know, and negative
    or blocked routes (dated on or after `since`) that the deck or poster never mentions."""
    if not os.path.exists(ledger):
        f.add("WARN", "LEDGER", "ledger", f"ledger not found: {ledger}")
        return
    rows = dk.ledger_rows(ledger)
    status = {r["id"]: r["_status"] for r in rows if r["_status"]}
    chip_ids = [rid for b in spec.blocks for e in b.elements if e.kind == "bullets"
                for _l, _r, _s, rid, _n in e.items if rid]
    text_all = "\n".join([ss.visible_text(spec), *(b.notes for b in spec.blocks), " ".join(chip_ids)])
    for b in spec.blocks:
        for e in b.elements:
            if e.kind != "bullets":
                continue
            for _lvl, runs, st, rid, _num in e.items:
                if not st:
                    continue
                where = where_of_block(b)
                if not rid:
                    if st in ("verified", "done", "succeeded"):
                        f.add("INFO", "STATUS-NO-ID", where, f"'{st}' chip without a ledger ID: "
                                                             f"{ss.runs_text(runs)[:70]}")
                    continue
                if rid not in status:
                    f.add("WARN", "STATUS-UNKNOWN-ID", where, f"{rid} is not in the ledger")
                    continue
                led = dk.LEDGER_TO_CHIP.get(status[rid], status[rid].lower())
                if dk.STATUS_RANK.get(st, 0) > dk.STATUS_RANK.get(led, 0):
                    f.add("FAIL", "STATUS-UPGRADE", where, f"chip says {st.upper()} for {rid}; the ledger says "
                                                           f"{status[rid]}")
                elif st != led and dk.STATUS_RANK.get(st, 0) < dk.STATUS_RANK.get(led, 0):
                    f.add("INFO", "STATUS-WEAKER", where, f"chip says {st.upper()} for {rid}; the ledger says "
                                                          f"{status[rid]}")
    negative = {"FAILED", "NEGATIVE", "BLOCKED", "INCONCLUSIVE", "PARTIAL", "RETRACTED"}
    import re
    for r in rows:
        if r["_status"] not in negative:
            continue
        date = r.get("date", "")
        if since and date and date < since:
            continue
        if not re.search(r"(?<![\w])" + re.escape(r["id"]) + r"(?![\w])", text_all):
            f.add("WARN", "NEGATIVE-OMITTED", "ledger", f"{r['id']} ({r['_status']}{', ' + date if date else ''}) "
                  f"is not mentioned: {r['_line'][:120]}")
