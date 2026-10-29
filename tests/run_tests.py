#!/usr/bin/env python3
"""Regression tests for the Science-Skill scripts.

  python3 tests/run_tests.py            offline, deterministic tests (default)
  python3 tests/run_tests.py --online   also run tests that query OpenAlex / Crossref / arXiv
  python3 tests/run_tests.py -v         verbose unittest output

Every fixture is synthetic and contains planted errors. A test passes when each
planted error is reported and the clean controls next to it are not. The
scripts are run as a user would run them (python3 -I script ...), in a
temporary directory; nothing in the repository is modified.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures")
SK = os.path.join(ROOT, "skills")
ONLINE = "--online" in sys.argv


def script(skill: str, name: str) -> str:
    return os.path.join(SK, skill, "scripts", name)


def run(args: list[str], cwd: str | None = None, ok_codes=(0,)) -> subprocess.CompletedProcess:
    p = subprocess.run([sys.executable, "-I", *args], cwd=cwd, capture_output=True, text=True, timeout=300)
    if p.returncode not in ok_codes:
        raise AssertionError(f"exit {p.returncode}: {' '.join(args)}\nstdout:\n{p.stdout[-2000:]}\n"
                             f"stderr:\n{p.stderr[-2000:]}")
    return p


def rd(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def wr(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def jload(path: str):
    return json.loads(rd(path))


def write_docx(path: str, paragraphs: list[tuple[str, str]]) -> None:
    """Minimal .docx: (style, text) pairs; style 'Heading1' or '' for body text."""
    def para(style: str, text: str) -> str:
        ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f'<w:p>{ppr}<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'
    body = "".join(para(s, t) for s, t in paragraphs)
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f"<w:body>{body}</w:body></w:document>")
    types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/>'
             '<Override PartName="/word/document.xml" '
             'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
             "</Types>")
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="science-skill-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# number-audit
# ---------------------------------------------------------------------------
class NumberAuditStats(Tmp):
    def stats(self, *extra) -> dict[tuple[str, str], str]:
        out = os.path.join(self.tmp, "stats")
        run([script("number-audit", "number_audit.py"), "stats", os.path.join(FIX, "stats.md"), "--out", out, *extra])
        rows = jload(os.path.join(out, "stats.json"))
        return {(r["test"], r["reported"]): r["status"] for r in rows}

    def find(self, rows, test, fragment):
        hits = [s for (t, rep), s in rows.items() if t == test and fragment in rep]
        self.assertTrue(hits, f"{test} row containing {fragment!r} not recognised; rows: {sorted(rows)}")
        return hits[0]

    def test_planted_errors_flagged(self):
        rows = self.stats()
        self.assertEqual(self.find(rows, "GRIM mean", "3.48"), "CHECK")
        self.assertEqual(self.find(rows, "GRIM %", "33.3%"), "CHECK")
        self.assertEqual(self.find(rows, "SD bound", "60.1"), "CHECK")
        self.assertEqual(self.find(rows, "SD bound", "0.40"), "CHECK")
        self.assertEqual(self.find(rows, "delta", "40%"), "INCONSISTENT")
        self.assertEqual(self.find(rows, "overlap", "81.2"), "CHECK")
        p_rows = [s for (t, rep), s in rows.items() if "2.20" in rep]
        self.assertTrue(p_rows and p_rows[0] != "ok", f"t(28) = 2.20, p = .004 should be flagged: {rows}")

    def test_clean_controls_pass(self):
        rows = self.stats()
        self.assertEqual(self.find(rows, "GRIM mean", "3.47"), "ok")
        self.assertEqual(self.find(rows, "delta", "25%"), "ok")
        self.assertEqual(self.find(rows, "delta", "3.5-fold"), "ok")
        self.assertEqual(self.find(rows, "delta", "0.1 point"), "ok")
        p_rows = [s for (t, rep), s in rows.items() if "2.10" in rep]
        self.assertTrue(p_rows and p_rows[0] == "ok", f"t(40) = 2.10, p = .042 is consistent: {rows}")
        self.assertFalse([1 for (t, rep), s in rows.items() if "35.7%" in rep and s != "ok"],
                         "35.7% of 28 (10/28) is possible")

    def test_grim_phrasing_and_boundaries(self):
        path = os.path.join(self.tmp, "extra.md")
        wr(path, "## Results\n\nMean length of stay in the validation subsample was 4.37 days (n = 23).\n"
                 "Mean AUC across folds was 0.81 (n = 5).\n"
                 "Mean age of participants was 54.35 years (n = 20).\n"
                 "参数敏感性分析中，准确率为 84.23%；n=6 时达到最优。\n"
                 "Readmission occurred after 1,610 of 12,840 discharges (12.5%).\n\n"
                 "Our model outperforms the baseline (0.81 ± 0.02 vs 0.79 ± 0.02).\n")
        out = os.path.join(self.tmp, "extra")
        run([script("number-audit", "number_audit.py"), "stats", path, "--out", out])
        rows = {(r["test"], r["reported"]): r["status"] for r in jload(os.path.join(out, "stats.json"))}
        self.assertEqual(self.find(rows, "GRIM mean", "4.37"), "CHECK")      # integer days, n = 23
        self.assertEqual(self.find(rows, "GRIM mean", "54.35"), "ok")        # 1087 / 20
        self.assertFalse([1 for (t, rep) in rows if "AUC" in rep], "GRIM does not apply to AUC")
        self.assertFalse([1 for (t, rep) in rows if "84.23" in rep], "n=6 after '；' is not the sample size")
        self.assertEqual(self.find(rows, "k/n %", "1,610 of 12,840"), "ok")      # thousands separators, unit word
        locs = {r["test"]: r["loc"] for r in jload(os.path.join(out, "stats.json"))}
        self.assertTrue(locs["overlap"].endswith(":9"), locs)                     # the sentence's own line

    def test_bounded_scale(self):
        self.assertNotIn(("SD bound", "4.1 ± 3.5"), self.stats())
        rows = self.stats("--bounds", "1,7")
        self.assertEqual(self.find(rows, "SD bound", "3.5"), "CHECK")


class NumberAuditGuards(Tmp):
    def test_guard_check(self):
        work = os.path.join(self.tmp, "guard")
        shutil.copytree(os.path.join(FIX, "guard"), work)
        p = run([script("number-audit", "number_audit.py"), "guard-check", "guards.json"], cwd=work, ok_codes=(1,))
        out = p.stdout
        self.assertIn("PASS 3", out)          # 12.35% needs ROUND_HALF_UP (12.345); 1{,}753; 0.47
        self.assertIn("FAIL           N0003", out)
        self.assertIn("STALE_PRESENT", out)
        self.assertNotIn("N0001", out.split("\n", 1)[1])
        self.assertNotIn("N0004", out.split("\n", 1)[1])

    def test_guard_substring_boundary(self):
        work = os.path.join(self.tmp, "guard")
        shutil.copytree(os.path.join(FIX, "guard"), work)
        tex = os.path.join(work, "paper.tex")
        s = rd(tex).replace("reached 0.47", "reached 10.47")
        wr(tex, s)
        p = run([script("number-audit", "number_audit.py"), "guard-check", "guards.json"], cwd=work, ok_codes=(1,))
        self.assertIn("N0004", p.stdout, "0.47 must not be found inside 10.47")


class NumberAuditTrace(Tmp):
    def test_manuscript_is_not_its_own_source(self):
        work = os.path.join(self.tmp, "study")
        os.makedirs(os.path.join(work, "results"))
        wr(os.path.join(work, "paper.md"), "# Title\n\n## Abstract\n\nThe median latency was 1,753 ms, and the "
                                           "model achieved an AUC of 0.837 in the cohort.\n")
        wr(os.path.join(work, "results", "metrics.json"), '{"latency_ms": 1752.6}\n')
        out = os.path.join(self.tmp, "na")
        run([script("number-audit", "number_audit.py"), "extract", "paper.md", "--out", out], cwd=work)
        run([script("number-audit", "number_audit.py"), "trace", os.path.join(out, "numbers.json"),
             "--repo", work, "--out", out], cwd=self.tmp)   # a different working directory on purpose
        rows = {r["raw"]: r["status"] for r in jload(os.path.join(out, "trace.json"))["rows"]}
        self.assertEqual(rows.get("0.837"), "orphan", rows)        # occurs only in the manuscript itself
        self.assertEqual(rows.get("1,753"), "traced", rows)        # 1752.6 in results/metrics.json


# ---------------------------------------------------------------------------
# paper-polish
# ---------------------------------------------------------------------------
class HedgeScan(Tmp):
    def scan(self, path):
        out = os.path.join(self.tmp, "h.json")
        run([script("paper-polish", "hedge_scan.py"), path, "--json", out])
        return jload(out)

    def counts(self, res, section):
        files = res if isinstance(res, list) else res.get("files", [res])
        return files[0]["sections"][section]["counts"]

    def test_patterns(self):
        res = self.scan(os.path.join(FIX, "hedge.md"))
        c = self.counts(res, "abstract")
        for code, n in (("D1", 1), ("D2", 1), ("D4", 2), ("D12", 1), ("D15", 2), ("D16", 2)):
            self.assertGreaterEqual(c.get(code, 0), n, f"{code} in abstract: {c}")
        ci = self.counts(res, "introduction")
        for code in ("D6", "D10", "O"):
            self.assertGreaterEqual(ci.get(code, 0), 1, f"{code} in introduction: {ci}")
        files = res if isinstance(res, list) else res.get("files", [res])
        o_hits = [h["match"] for h in files[0]["sections"]["introduction"]["hits"] if h["code"] == "O"]
        self.assertTrue(any("first machine-learning model" in m for m in o_hits), o_hits)

    def test_specific_limitations_not_flagged(self):
        res = self.scan(os.path.join(FIX, "hedge.md"))
        files = res if isinstance(res, list) else res.get("files", [res])
        d16 = [h["match"] for h in files[0]["sections"]["abstract"]["hits"] if h["code"] == "D16"]
        self.assertFalse([m for m in d16 if "hospitals" in m or "binary" in m], d16)

    def test_docx(self):
        path = os.path.join(self.tmp, "ms.docx")
        write_docx(path, [("Title", "A synthetic Word manuscript"), ("Heading1", "Abstract"),
                          ("", "We attempt to shed light on a question that remains largely unexplored. "
                               "We do not claim generality."),
                          ("Heading1", "Introduction"), ("", "It is worth noting that this is a test."),
                          ("Heading1", "Methods"), ("", "Nothing here.")])
        res = self.scan(path)
        c = self.counts(res, "abstract")
        self.assertGreaterEqual(c.get("D4", 0), 2, c)
        self.assertGreaterEqual(c.get("D1", 0), 1, c)


# ---------------------------------------------------------------------------
# experiment-integrity
# ---------------------------------------------------------------------------
class IntegrityScan(Tmp):
    def test_planted_bugs(self):
        out = os.path.join(self.tmp, "ei")
        run([script("experiment-integrity", "integrity_scan.py"), os.path.join(FIX, "integrity_proj"), "--out", out])
        hits = jload(os.path.join(out, "integrity_scan.json"))["hits"]
        by = {}
        for h in hits:
            by.setdefault(h["code"], []).append(h)
        for code in ("S1", "S2", "S3", "R1", "P1", "L1", "G1", "G2", "X1", "X2"):
            self.assertIn(code, by, f"{code} not found; got {sorted(by)}")
        r1_lines = {h["line"] for h in by["R1"]}
        src = rd(os.path.join(FIX, "integrity_proj", "model.py")).splitlines()
        fine = next(i for i, l in enumerate(src, 1) if "drawn unconditionally" in l) + 1
        self.assertNotIn(fine, r1_lines, "unconditional draw followed by a condition is the correct pattern")
        self.assertFalse([h for h in hits if "tests/" in h["file"]], "tests/ must not produce X1 leads")
        self.assertTrue(any("f1_macro" in h["note"] for h in by["X2"]))


class IntegrityPipeline(Tmp):
    def test_leakage_selection_and_seed_lists(self):
        out = os.path.join(self.tmp, "ei")
        run([script("experiment-integrity", "integrity_scan.py"), os.path.join(FIX, "integrity_pipeline"),
             "--out", out])
        d = jload(os.path.join(out, "integrity_scan.json"))
        by = {}
        for h in d["hits"]:
            by.setdefault(h["code"], []).append(h["line"])
        self.assertEqual(sorted(by.get("L1", [])), [14, 15], d["hits"])   # fitted in preprocess(), split in pick_k()
        self.assertEqual(by.get("L2"), [28], d["hits"])                   # best k chosen on y_test
        self.assertNotIn("X2", by, "'preprocess' is not a metric function")
        lists = {s[1] for v in d["seeds"].values() for s in v}
        self.assertTrue({"[1, 2, 3]", "[7, 8, 9]"} <= lists, lists)


# ---------------------------------------------------------------------------
# dead-end-ledger
# ---------------------------------------------------------------------------
class Ledger(Tmp):
    def test_graph(self):
        p = run([script("dead-end-ledger", "ledger.py"), "graph", os.path.join(FIX, "ledger.md")], ok_codes=(1,))
        out = p.stdout
        self.assertIn("depends on Z9, which is not in the ledger", out)
        self.assertIn("dependency cycle: R5 -> R6 -> R5", out)
        self.assertIn("R2 (line 22) is VERIFIED but depends on T1", out)
        self.assertIn("R3 (line 23) relies on R4 (RETRACTED)", out)
        ready = out.split("## Ready to attempt", 1)[1].split("##", 1)[0]
        self.assertIn("T2", ready)
        self.assertNotIn("T3", ready)

    def test_lint_route_statuses(self):
        p = run([script("dead-end-ledger", "ledger.py"), "lint", os.path.join(FIX, "ledger.md")], ok_codes=(0, 1))
        self.assertIn("BLOCKED route without the blocking reason", p.stdout)
        self.assertNotIn("line 48: INCONCLUSIVE", p.stdout)

    def test_init_card(self):
        led = os.path.join(self.tmp, "LEDGER.md")
        run([script("dead-end-ledger", "ledger.py"), "init", led, "--goal", "a synthetic goal"])
        self.assertIn("## 6. Stop rules", rd(led))
        card = os.path.join(self.tmp, "X7.md")
        run([script("dead-end-ledger", "ledger.py"), "card", "--id", "X7", "--out", card, "--ledger", led])
        self.assertTrue(os.path.exists(card))
        run([script("dead-end-ledger", "ledger.py"), "card", "--id", "X7", "--out", card], ok_codes=(1, 2))


# ---------------------------------------------------------------------------
# proof-audit
# ---------------------------------------------------------------------------
class ProofMap(Tmp):
    def test_planted(self):
        out = os.path.join(self.tmp, "pm")
        run([script("proof-audit", "proof_map.py"), os.path.join(FIX, "proofs.tex"), "--out", out])
        d = jload(os.path.join(out, "proof_map.json"))
        flat = json.dumps(d)
        self.assertTrue(d["cycles"], "lem:a <-> lem:b cycle")
        self.assertIn("eq:missing", json.dumps(d["undefined"]))
        self.assertIn("lem:noproof", json.dumps(d["missing"]))
        self.assertIn("lem:unused", json.dumps(d["unused"]))
        self.assertIn("conj:H", json.dumps(d["conditions"]))
        self.assertTrue(d["macro_redef"])
        md = rd(os.path.join(out, "proof_map.md")).lower()
        for phrase in ("clearly", "one can show", "standard argument"):
            self.assertIn(phrase, md)
        self.assertIn("thm:main", flat)


# ---------------------------------------------------------------------------
# mock-review
# ---------------------------------------------------------------------------
@unittest.skipUnless(shutil.which("git"), "git not available")
class ReviewPack(Tmp):
    def test_isolation(self):
        repo = os.path.join(self.tmp, "repo")
        os.makedirs(os.path.join(repo, "polish"))
        files = {"main.tex": "\\documentclass{article}\\begin{document}Hi.\\end{document}\n",
                 "analysis.py": "print(1)\n", "CLAUDE.md": "notes\n", "polish/draft.md": "x\n",
                 "REVIEW_round1.md": "earlier review\n"}
        for k, v in files.items():
            wr(os.path.join(repo, k), v)
        g = ["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
        subprocess.run(g[:3] + ["init", "-q"], check=True)
        subprocess.run(g + ["add", "-A"], check=True)
        subprocess.run(g + ["commit", "-qm", "init"], check=True)
        wr(os.path.join(repo, "untracked_notes.md"), "private\n")
        out = os.path.join(self.tmp, "mr")
        run([script("mock-review", "review_pack.py"), "pack", "--repo", repo, "--out", out, "--roles", "a,b"])
        packed = set()
        for dp, _, fs in os.walk(os.path.join(out, "pack")):
            packed |= {os.path.relpath(os.path.join(dp, f), os.path.join(out, "pack")) for f in fs}
        self.assertIn("main.tex", packed)
        self.assertIn("analysis.py", packed)
        for bad in ("CLAUDE.md", "polish/draft.md", "untracked_notes.md"):
            self.assertNotIn(bad, packed)
        self.assertTrue(os.path.exists(os.path.join(out, "PIN.json")))
        manifest = rd(os.path.join(out, "MANIFEST.md"))
        self.assertIn("REVIEW_round1.md", manifest, "files that look like reviews must be listed for the user")
        run([script("mock-review", "review_pack.py"), "check-pin", os.path.join(out, "PIN.json"), "--repo", repo])


# ---------------------------------------------------------------------------
# cite-verify (offline part)
# ---------------------------------------------------------------------------
class CiteContexts(Tmp):
    def test_contexts(self):
        tex = os.path.join(self.tmp, "m.tex")
        wr(tex, "\\documentclass{article}\\begin{document}\n\\begin{abstract}A.\\end{abstract}\n"
                             "\\section{Introduction}\nSmith et al. proved that the bound is tight \\cite{smith}.\n"
                             "Related work exists \\cite{smith,jones}.\n\\end{document}\n")
        out = os.path.join(self.tmp, "cv")
        run([script("cite-verify", "refcheck.py"), "contexts", tex, "--out", out])
        d = jload(os.path.join(out, "contexts.json"))
        self.assertEqual(len(d["smith"]), 2)
        self.assertTrue(any(c["claim"] for c in d["smith"]))
        self.assertEqual(d["jones"][0]["co_cited"], 2)


# ---------------------------------------------------------------------------
# Reports computed from findings ledgers (lib/findings.py)
# ---------------------------------------------------------------------------
LEDGER_HEAD = "| id | item | location | verdict | evidence | verified |\n|---|---|---|---|---|---|\n"


class FindingsReports(Tmp):
    def report(self, skill, name, body, ok_codes, *extra):
        led = os.path.join(self.tmp, "ledger.md")
        wr(led, "# Ledger\n\n" + LEDGER_HEAD + body)
        out = os.path.join(self.tmp, "report.md")
        p = run([script(skill, name), led, "--out", out, *extra], ok_codes=ok_codes)
        return p.returncode, rd(out)

    def test_proof_profile_exit_codes(self):
        code, text = self.report("proof-audit", "audit_report.py",
                                 "| R1 | thm:a | m:1 | VERIFIED | ok | no |\n"
                                 "| R2 | lem:b | m:2 | Valid with fix | wording | no |\n"
                                 "| R3 | thm:c | m:3 | CONDITIONAL(Conj. 1) | stated | no |\n", (0,))
        self.assertEqual(code, 0)
        self.assertIn("No confirmed severe finding", text)
        self.assertIn("CONDITIONAL (Conj. 1)", text)
        code, text = self.report("proof-audit", "audit_report.py",
                                 "| R1 | thm:a | m:1 | GAP | missing step | no |\n", (2,))
        self.assertIn("NOT FINAL", text)                         # an unverified GAP cannot conclude anything
        code, text = self.report("proof-audit", "audit_report.py",
                                 "| R1 | thm:a | m:1 | GAP | missing step | yes |\n"
                                 "| R2 | thm:b | m:2 | PLAUSIBLE | ? | yes |\n", (2,))
        self.assertIn("outside the vocabulary", text)
        code, text = self.report("proof-audit", "audit_report.py",
                                 "| R1 | thm:a | m:1 | GAP | missing step | yes |\n"
                                 "| R2 | sup | s:1 | NOT CHECKED | out of scope | no |\n", (1,), "--lang", "zh")
        self.assertIn("已确认的严重问题：thm:a", text)
        self.assertIn("1 条未检查", text)

    def test_review_profile_with_pin(self):
        pin = os.path.join(self.tmp, "PIN.json")
        wr(pin, '{"head": "abcdef1234", "manuscript_sha256": {"main.tex": "' + "0" * 64 + '"}}')
        code, text = self.report("mock-review", "review_report.py",
                                 "| K1 | claim | m:1 | partial | half true | yes |\n"
                                 "| K2 | claim | m:2 | refuted | misread | yes |\n", (1,), "--pin", pin)
        self.assertIn("does not represent the decision", text)
        self.assertIn("git abcdef1", text)
        self.assertIn("PARTIALLY CONFIRMED 1", text)

    def test_integrity_and_numbers_profiles(self):
        code, _ = self.report("experiment-integrity", "integrity_report.py",
                              "| F1 | seeds | a.py:3 | POSSIBLE | innocent explanation open | no |\n", (0,))
        self.assertEqual(code, 0)
        code, text = self.report("number-audit", "numbers_report.py",
                                 "| N1 | 0.83 | paper:5 | mismatch | data 0.812 | yes |\n"
                                 "| N2 | 12.5% | paper:29 | confirmed | 1610/12840 | no |\n", (1,))
        self.assertIn("MISMATCH 1", text)


# ---------------------------------------------------------------------------
# Repository conventions (see Contributing in README.md)
# ---------------------------------------------------------------------------
class SkillMetadata(unittest.TestCase):
    def skills(self):
        return sorted(d for d in os.listdir(SK) if os.path.isfile(os.path.join(SK, d, "SKILL.md")))

    def test_frontmatter(self):
        import re
        for name in self.skills():
            text = rd(os.path.join(SK, name, "SKILL.md"))
            m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
            self.assertTrue(m, f"{name}: no frontmatter")
            fm = dict(line.split(": ", 1) for line in m.group(1).splitlines() if ": " in line)
            self.assertEqual(fm.get("name"), name, f"{name}: name must match the directory")
            desc = fm.get("description", "")
            self.assertTrue(desc, f"{name}: missing description")
            self.assertLessEqual(len(desc), 1024, f"{name}: description has {len(desc)} characters")
            self.assertNotIn(": ", desc, f"{name}: ': ' in the description breaks YAML")
            self.assertNotIn(" #", desc, f"{name}: ' #' in the description starts a YAML comment")

    def test_documented_in_both_readmes(self):
        for readme in ("README.md", "README.zh-CN.md"):
            text = rd(os.path.join(ROOT, readme))
            for name in self.skills():
                self.assertIn(f"### {name}", text, f"{readme} has no guide for {name}")

    def test_failure_modes_registered(self):
        text = rd(os.path.join(ROOT, "FAILURE_MODES.md"))
        for name in self.skills():
            self.assertIn(f"`{name}`", text, f"FAILURE_MODES.md does not register {name}")


# ---------------------------------------------------------------------------
# Online (opt-in)
# ---------------------------------------------------------------------------
@unittest.skipUnless(ONLINE, "online tests run only with --online")
class Online(Tmp):
    def test_refcheck_real_and_fabricated(self):
        bib = os.path.join(self.tmp, "r.bib")
        wr(bib, 
            "@article{lecun2015,\n title={Deep learning},\n author={LeCun, Yann and Bengio, Yoshua and Hinton, "
            "Geoffrey},\n journal={Nature}, volume={521}, pages={436--444}, year={2015},\n doi={10.1038/nature14539}\n}\n"
            "@article{fake2024,\n title={A Universal Estimator That Is Optimal for Every Dataset},\n"
            " author={Doe, Jane and Roe, Richard},\n journal={Nature}, volume={630}, pages={1--9}, year={2024},\n"
            " doi={10.1038/s41586-024-99999-9}\n}\n")
        out = os.path.join(self.tmp, "cv")
        run([script("cite-verify", "refcheck.py"), "check", bib, "--all", "--out", out], ok_codes=(0, 1))
        res = {r["key"]: {i[1] for i in r["issues"]} for r in jload(os.path.join(out, "results.json"))["results"]}
        self.assertEqual(res["lecun2015"], set(), res)
        self.assertIn("NOT_FOUND", res["fake2024"])

    def test_crossref_subtitle_is_not_a_title_mismatch(self):
        bib = os.path.join(self.tmp, "s.bib")
        wr(bib, "@article{kansagara2011,\n title={Risk prediction models for hospital readmission: a systematic "
                "review},\n author={Kansagara, Devan and Englander, Honora and Salanitro, Amanda and Kagen, David and "
                "Theobald, Cecelia and Freeman, Michele and Kripalani, Sunil},\n journal={JAMA}, volume={306}, "
                "number={15}, pages={1688--1698}, year={2011},\n doi={10.1001/jama.2011.1515}\n}\n")
        out = os.path.join(self.tmp, "cv")
        run([script("cite-verify", "refcheck.py"), "check", bib, "--all", "--out", out], ok_codes=(0, 1))
        res = {r["key"]: {i[1] for i in r["issues"]} for r in jload(os.path.join(out, "results.json"))["results"]}
        self.assertNotIn("TITLE_MISMATCH", res["kansagara2011"], res)   # Crossref keeps "A Systematic Review" apart

    def test_revtex_reference_list(self):
        tex = os.path.join(self.tmp, "refs.tex")
        wr(tex, "\\documentclass{article}\\begin{document}\nText~\\cite{a,b}.\n\\begin{thebibliography}{2}\n"
                "\\bibitem{a} I. H. Kim, \\href{https://doi.org/10.22331/q-2026-08-13-2191}{Catalytic $z$-rotations "
                "in constant $T$-depth}, Quantum \\textbf{10}, 2191 (2026).\n"
                "\\bibitem{b} L. de Moura and N. Bj{\\o}rner, \\href{https://doi.org/10.1007/978-3-540-78800-3_24}"
                "{Z3: An efficient SMT solver}, in TACAS 2008, LNCS 4963, 337 (2008).\n"
                "\\end{thebibliography}\n\\end{document}\n")
        out = os.path.join(self.tmp, "cl")
        run([script("cite-verify", "refcheck.py"), "check-list", tex, "--out", out], ok_codes=(0, 1))
        report = rd(os.path.join(out, "report.md"))
        for bad in ("DOI_NOT_FOUND", "NOT_FOUND", "AUTHOR_MISSING", "TITLE_DIFFERS"):
            self.assertNotIn(bad, report, report[-1500:])

    def test_lit_graph_resolve_pmid(self):
        p = run([script("novelty-audit", "lit_graph.py"), "resolve", "PMID:26044081"])
        self.assertIn("predicting early hospital readmissions", p.stdout)

    def test_lit_graph_resolve(self):
        p = run([script("novelty-audit", "lit_graph.py"), "resolve", "10.1038/nature14539", "--json"])
        self.assertIn("Deep learning", p.stdout)


if __name__ == "__main__":
    argv = [a for a in sys.argv if a != "--online"]
    unittest.main(argv=argv)
