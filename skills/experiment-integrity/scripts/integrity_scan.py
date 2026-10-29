#!/usr/bin/env python3
"""integrity_scan.py - static scan of analysis code for patterns that have
produced false results in real projects.

Usage
  integrity_scan.py CODE_DIR [CODE_DIR ...] [--out DIR] [--exclude GLOB ...]

Python files are analysed with the ast module; R, Julia, MATLAB and shell
files get a lighter regex scan. Every hit is a lead to be read in context,
not a verdict.

Codes
  S1  sentinel guard in a denominator: x / max(d, 1e-12), x / (d + eps)
  S2  constant returned on an edge-case branch (if len(x) < 3: return 360)
  S3  swallowed exception: except: pass / continue / return <constant>
  S4  missing values replaced by a constant: fillna(0), nan_to_num, .get(k, 0.0)
  R1  random draw inside a condition (if cond and rng.random() < p) - the random
      stream then depends on cond, so changing a parameter changes the scenarios
  R2  random draw only inside one branch of an if - same desynchronisation risk
  R3  seeds: every literal seed or seed range, listed per file, to check that
      compared arms really use the same instances
  P1  number hard-coded in figure text (title, label, annotation)
  L1  preprocessing fitted on data that later becomes the test set: .fit /
      .fit_transform before train_test_split in the same function, or a
      scaler / selector / imputer fitted in a function that never splits,
      in a module that splits elsewhere
  L2  model or hyperparameter selection by a test-set score: inside a loop, a
      metric computed on test-named data (y_test, Xte, ...) is compared with
      a "best" value
  G1  check script that tests a number with a substring test (str(v) in text):
      "0.47" is a substring of "10.47"
  G2  shell: grep -c ... || echo 0 (prints "0\\n0" when nothing matches)
  X1  placeholder or synthetic data on a result path: random numbers assigned
      to a result-like variable (scores, acc, results, metrics), or
      dummy / placeholder / fake / TODO markers outside tests
  X2  metric-like function (accuracy, f1, auc, score, error, ...) defined but
      never referenced in the scanned code (a dead metric)
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import os
import re
import sys
from collections import defaultdict

SKIP_DIRS = {".git", ".venv", "venv", "env", "node_modules", "__pycache__", "site-packages", "dist-packages",
             "third_party", "vendor", "_vendor", "build", "dist", ".ipynb_checkpoints", ".mypy_cache", ".tox",
             "polish", "number_audit", "integrity", "refcheck", "novelty"}
RNG_ATTRS = {"random", "rand", "randn", "randint", "integers", "uniform", "normal", "choice", "shuffle",
             "permutation", "sample", "binomial", "poisson", "exponential", "gauss", "random_sample", "standard_normal",
             "multivariate_normal", "beta", "gamma", "randrange", "bernoulli", "rand_like", "randn_like",
             "randint_like", "multinomial"}
RNG_BASES = re.compile(r"^(rng|rs|random|np\.random|numpy\.random|torch|gen|generator|prng|self\.rng|self\._rng|"
                       r"self\.random|state|rand_state|random_state)$")
PLOT_FUNCS = {"set_title", "title", "suptitle", "text", "annotate", "set_xlabel", "set_ylabel", "xlabel", "ylabel",
              "figtext", "set_label", "legend", "set_text", "add_annotation", "update_layout"}
SEED_KW = {"seed", "random_state", "random_seed", "rng_seed"}
RESULT_NAME = re.compile(r"(^|_)(results?|scores?|metrics?|acc|accuracy|auc|f1|precision|recall|loss|errors?|perf|"
                         r"performance|outputs?|preds?|predictions|y_pred|y_hat|ground_?truth|gt|labels?)(_|$)", re.I)
# Whole name tokens only ("roc_auc", "f1_macro", "accuracy_score"), so that "preprocess" does not match "roc".
METRIC_FUNC = re.compile(r"(?:^|_)(accuracy|precision|recall|f1|auc|roc|auroc|score|scores|metric|metrics|error|errors|"
                         r"loss|bleu|rouge|rmse|mae|mse|psnr|ssim|iou|map|brier|kappa|mcc)(?:_|$)", re.I)
PLACEHOLDER = re.compile(r"\b(dummy|placeholder|fake|lorem ipsum|hard-?coded|mock(ed)? (data|result)s?)\b", re.I)
PLACEHOLDER_NEG = re.compile(r"\b(no|not|non|without|replac\w*|remov\w*|instead of)\b|无|非|替换|去除|删除|不是", re.I)
TODO_RX = re.compile(r"#\s*(TODO|FIXME|HACK|XXX)\b")
PREPROC = re.compile(r"(Scaler|Normalizer|Imputer|Encoder|Vectorizer|Selector|SelectKBest|SelectPercentile|"
                     r"VarianceThreshold|PCA|TruncatedSVD|PolynomialFeatures|Binarizer|QuantileTransformer|"
                     r"PowerTransformer|KBinsDiscretizer)$|^(scaler|selector|pca|imputer|encoder|vectorizer|normali[sz]er)",
                     re.I)
TRAIN_NAME = re.compile(r"(^|_)(tr|train|training|fit)(_|$)|^(x|y)_?(tr|train)$", re.I)
TEST_NAME = re.compile(r"^(x|y)_?(te|test|tst)$|(^|_)(test|holdout)(_|$)", re.I)
NUM_IN_TEXT = re.compile(r"(?<![A-Za-z_])\d+\.\d+|\d+\s*(?:°|%|\\%|deg|m\b|km|ms|s\b)|\d{3,}")


def src_line(lines: list[str], n: int) -> str:
    return lines[n - 1].strip()[:160] if 0 < n <= len(lines) else ""


def dotted(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = dotted(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return dotted(node.func)
    return ""


def is_rng_call(node) -> bool:
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    if isinstance(f, ast.Attribute) and f.attr in RNG_ATTRS:
        base = dotted(f.value)
        return bool(RNG_BASES.match(base)) or base.endswith("random") or base.endswith("rng")
    if isinstance(f, ast.Name) and f.id in {"random", "rand", "randn", "randint", "uniform", "choice", "shuffle"}:
        return True
    return False


def small_const(node) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool) \
        and 0 < abs(node.value) <= 1e-3


def num_const(node) -> bool:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        node = node.operand
    if isinstance(node, ast.Call) and dotted(node.func) in ("float", "np.float64") and node.args and \
            isinstance(node.args[0], ast.Constant) and str(node.args[0].value).lower() in ("inf", "nan", "-inf"):
        return True
    if isinstance(node, ast.Attribute) and dotted(node) in ("np.inf", "np.nan", "math.inf", "math.nan", "numpy.inf",
                                                            "numpy.nan"):
        return True
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)


class Visitor(ast.NodeVisitor):
    def __init__(self, path: str, lines: list[str], hits: list, seeds: dict, defs: dict | None = None,
                 refs: set | None = None):
        self.path, self.lines, self.hits, self.seeds = path, lines, hits, seeds
        self.defs = defs if defs is not None else {}
        self.refs = refs if refs is not None else set()
        self.func_stack: list[ast.AST] = []
        self._seen: set = set()
        self.is_test = bool(re.search(r"(^|/)(tests?|testing)(/|$)|(^|/)test_|_test\.py$", path))
        self.split_funcs: set[str] = set()
        self.preproc_fits: list[tuple[str, ast.AST, str]] = []
        self.check_script = bool(re.search(r"check|guard|verify|assert|validate|test", os.path.basename(path), re.I))

    def hit(self, code: str, node: ast.AST, note: str):
        n = getattr(node, "lineno", 0)
        key = (code, self.path, n)
        if key in self._seen:
            return
        self._seen.add(key)
        self.hits.append({"code": code, "file": self.path, "line": n, "src": src_line(self.lines, n), "note": note})

    # S1 -------------------------------------------------------------
    def visit_BinOp(self, node: ast.BinOp):
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            r = node.right
            if isinstance(r, ast.Call) and dotted(r.func) in ("max", "np.maximum", "numpy.maximum", "np.fmax") and \
                    any(small_const(a) for a in r.args):
                self.hit("S1", node, "denominator floored at a tiny constant: when it triggers, the result is a sentinel, "
                                     "not a measurement")
            elif isinstance(r, ast.BinOp) and isinstance(r.op, ast.Add) and (small_const(r.right) or small_const(r.left)):
                self.hit("S1", node, "epsilon added to a denominator: check whether the zero case can occur in "
                                     "reported runs")
        self.generic_visit(node)

    # S2 -------------------------------------------------------------
    def visit_If(self, node: ast.If):
        test_src = ast.unparse(node.test) if hasattr(ast, "unparse") else ""
        edge = re.search(r"\blen\(|\.size\b|\.shape\b|\bcount\b|\bn_\w+|\bnot \w+|== ?0\b|< ?[1-9]\b|<= ?[0-9]\b|"
                         r"is None|isnan|\bempty\b", test_src)
        if edge and self.func_stack and self._mixed_returns(self.func_stack[-1]):
            for stmt in node.body:
                if isinstance(stmt, ast.Return) and stmt.value is not None and num_const(stmt.value):
                    self.hit("S2", stmt, f"constant returned when `{test_src[:60]}`: make sure this value never "
                                         "reaches a table as if computed")
                if isinstance(stmt, ast.Assign) and num_const(stmt.value) and len(node.body) <= 3:
                    tgt = ", ".join(ast.unparse(t) for t in stmt.targets) if hasattr(ast, "unparse") else "?"
                    self.hit("S2", stmt, f"`{tgt}` set to a constant when `{test_src[:60]}`")
        # R1: rng inside the condition itself
        for sub in ast.walk(node.test):
            if is_rng_call(sub):
                self.hit("R1", node, "random draw inside the if-condition; with short-circuit evaluation the number "
                                     "of draws depends on the other operands. Draw unconditionally, then decide.")
                break
        # R2: rng only in the body, not in orelse
        body_rng = any(is_rng_call(s) for b in node.body for s in ast.walk(b))
        else_rng = any(is_rng_call(s) for b in node.orelse for s in ast.walk(b))
        if body_rng != else_rng:
            self.hit("R2", node, "random draws happen in only one branch: the random stream shifts whenever the "
                                 "branch condition changes (e.g. across parameter values or arms)")
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp):
        if any(is_rng_call(s) for v in node.values[1:] for s in ast.walk(v)):
            self.hit("R1", node, "random draw on the right of and/or: it is skipped when the left side decides")
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp):
        if any(is_rng_call(s) for s in ast.walk(node.body)) != any(is_rng_call(s) for s in ast.walk(node.orelse)):
            self.hit("R2", node, "random draw in only one arm of a conditional expression")
        self.generic_visit(node)

    # S3 -------------------------------------------------------------
    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        body = node.body
        if len(body) == 1:
            s = body[0]
            if isinstance(s, (ast.Pass, ast.Continue)):
                self.hit("S3", node, "exception swallowed: failures disappear from the results instead of being counted")
            elif isinstance(s, ast.Return) and (s.value is None or num_const(s.value)):
                self.hit("S3", node, "exception turned into a constant result")
            elif isinstance(s, ast.Assign) and num_const(s.value):
                self.hit("S3", node, "exception turned into a constant value")
        self.generic_visit(node)

    # Calls: S4, R3, P1, L1, G1 -------------------------------------------
    def visit_Call(self, node: ast.Call):
        name = dotted(node.func)
        last = name.split(".")[-1]
        if last in ("fillna", "nan_to_num") or (last == "get" and len(node.args) == 2 and num_const(node.args[1])):
            arg = node.args[1] if last == "get" else (node.args[0] if node.args else None)
            if last != "get" or True:
                if last == "nan_to_num" or (arg is not None and num_const(arg)) or any(
                        k.arg in ("value", "nan") for k in node.keywords):
                    self.hit("S4", node, f"missing values replaced by a constant ({last}): check how many and whether "
                                         "they enter reported statistics")
        # seeds
        seed_vals = []
        if last in ("seed", "manual_seed", "default_rng", "RandomState", "PRNGKey", "Generator", "set_seed",
                    "manual_seed_all") and node.args:
            seed_vals.append(ast.unparse(node.args[0]) if hasattr(ast, "unparse") else "?")
        for k in node.keywords:
            if k.arg in SEED_KW:
                seed_vals.append(ast.unparse(k.value) if hasattr(ast, "unparse") else "?")
        for v in seed_vals:
            self.seeds[self.path].append((node.lineno, v, src_line(self.lines, node.lineno)))
        # plot text with hard-coded numbers
        if last in PLOT_FUNCS:
            for a in list(node.args) + [k.value for k in node.keywords if k.arg in ("label", "text", "title", "s")]:
                txt = None
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    txt = a.value
                elif isinstance(a, ast.JoinedStr):
                    txt = "".join(v.value for v in a.values if isinstance(v, ast.Constant) and isinstance(v.value, str))
                if txt and NUM_IN_TEXT.search(txt):
                    self.hit("P1", node, f"number written into figure text ({txt[:50]!r}): read it from the results "
                                         "file instead")
                    break
        # leakage across functions: remember preprocessing fits and where splits happen
        if last == "train_test_split":
            self.split_funcs.add(getattr(self.func_stack[-1], "name", "<module>") if self.func_stack else "<module>")
        if last in ("fit", "fit_transform") and isinstance(node.func, ast.Attribute):
            recv = node.func.value
            recv_name = dotted(recv).split(".")[-1]
            first = ast.unparse(node.args[0]) if node.args and hasattr(ast, "unparse") else ""
            if PREPROC.search(recv_name) and not TRAIN_NAME.search(first.split("[")[0].split(".")[0]):
                fname = getattr(self.func_stack[-1], "name", "<module>") if self.func_stack else "<module>"
                self.preproc_fits.append((fname, node, recv_name))
        # leakage: fit before split in the same function
        if last == "train_test_split" and self.func_stack:
            fn = self.func_stack[-1]
            for sub in ast.walk(fn):
                if isinstance(sub, ast.Call) and dotted(sub.func).split(".")[-1] in ("fit", "fit_transform") and \
                        getattr(sub, "lineno", 10**9) < node.lineno:
                    self.hit("L1", sub, "fit/fit_transform before train_test_split: preprocessing may have seen the "
                                        "test data")
                    break
        self.generic_visit(node)

    # L2: selection by a test-set score -------------------------------
    def visit_For(self, node):
        scored = {}
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call) and \
                    METRIC_FUNC.search(dotted(stmt.value.func).split(".")[-1] or ""):
                names = {n.id for a in stmt.value.args for n in ast.walk(a) if isinstance(n, ast.Name)}
                if any(TEST_NAME.search(n) for n in names):
                    for t in stmt.targets:
                        if isinstance(t, ast.Name):
                            scored[t.id] = stmt
        if scored:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Compare):
                    used = {n.id for n in ast.walk(sub) if isinstance(n, ast.Name)}
                    if used & set(scored) and any("best" in n.lower() for n in used):
                        self.hit("L2", sub, "the best model or configuration is chosen by a score computed on test data; "
                                            "the reported test score is then optimistically biased. Select on a "
                                            "validation split or by cross-validation within the training data")
                        break
        self.generic_visit(node)

    visit_AsyncFor = visit_For

    def finish(self):
        """Module-level leads that need the whole file: preprocessing fitted in a function that does not split."""
        if not self.split_funcs:
            return
        for fname, node, recv in self.preproc_fits:
            if fname in self.split_funcs:
                continue
            where = ", ".join(sorted(self.split_funcs))
            self.hit("L1", node, f"{recv} is fitted in `{fname}()`, but the train/test split happens in `{where}()`: "
                                 "if this runs before the split, the test data shaped the preprocessing")

    def visit_Compare(self, node: ast.Compare):
        if self.check_script and any(isinstance(op, ast.In) for op in node.ops):
            left = node.left
            numeric_left = (isinstance(left, ast.Call) and dotted(left.func) in ("str", "format", "repr")) or \
                isinstance(left, ast.JoinedStr) or (isinstance(left, ast.Constant) and isinstance(left.value, str)
                                                    and re.fullmatch(r"-?\d+(\.\d+)?", left.value or ""))
            if numeric_left:
                self.hit("G1", node, "number checked by substring: '0.47' is found inside '10.47'. Use a regex with "
                                     "(?<![0-9.]) and (?![0-9]) boundaries and a context window")
        self.generic_visit(node)

    @staticmethod
    def _mixed_returns(fn) -> bool:
        """True when the function returns both computed values and constants:
        the sentinel-masquerading-as-result pattern. Exit-code style functions
        (only constant returns) and CLI entry points are skipped."""
        if getattr(fn, "name", "") in ("main", "cli", "_main", "run_cli"):
            return False
        rets = [n for n in ast.walk(fn) if isinstance(n, ast.Return) and n.value is not None]
        return any(not num_const(r.value) for r in rets) and any(num_const(r.value) for r in rets)

    def visit_Assign(self, node: ast.Assign):
        if not self.is_test:
            names = []
            for t in node.targets:
                for sub in ast.walk(t):
                    if isinstance(sub, ast.Name):
                        names.append(sub.id)
                    elif isinstance(sub, ast.Attribute):
                        names.append(sub.attr)
            if any(re.search(r"seed", n, re.I) for n in names) and isinstance(
                    node.value, (ast.List, ast.Tuple, ast.Constant, ast.Call)) and not is_rng_call(node.value):
                val = ast.unparse(node.value) if hasattr(ast, "unparse") else "?"
                if re.search(r"\d", val):
                    self.seeds[self.path].append((node.lineno, val[:80], src_line(self.lines, node.lineno)))
            if any(RESULT_NAME.search(n) for n in names) and any(is_rng_call(x) for x in ast.walk(node.value)):
                self.hit("X1", node, "random numbers assigned to a result-like variable: placeholder or synthetic data "
                                     "on a result path? Confirm it never reaches a reported number")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        if (not self.is_test and isinstance(node.value, str) and PLACEHOLDER.search(node.value)
                and len(node.value) < 200 and not re.fullmatch(r"\w+", node.value)
                and not PLACEHOLDER_NEG.search(node.value)):
            self.hit("X1", node, f"placeholder marker in a string ({PLACEHOLDER.search(node.value).group(0)!r})")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        self.refs.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        self.refs.add(node.attr)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if not self.is_test and METRIC_FUNC.search(node.name) and not node.name.startswith("test"):
            self.defs.setdefault(node.name, []).append((self.path, node.lineno, src_line(self.lines, node.lineno)))
        self.func_stack.append(node)
        self.generic_visit(node)
        self.func_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef


REGEX_RULES = {
    ".r": [("S1", r"/\s*max\([^)]*1e-\d+", "denominator floored at a tiny constant"),
           ("S3", r"tryCatch\([^)]*error\s*=\s*function\(e\)\s*(NA|0|NULL)", "error turned into NA/0/NULL"),
           ("R3", r"set\.seed\(\s*([^)]+)\)", "seed"),
           ("S4", r"(replace_na|ifelse\(is\.na\([^)]*\),\s*0)", "missing values replaced by a constant")],
    ".jl": [("S1", r"/\s*max\([^)]*1e-\d+", "denominator floored at a tiny constant"),
            ("R3", r"(Random\.seed!|MersenneTwister|Xoshiro|StableRNG)\(\s*([^)]*)\)", "seed"),
            ("R1", r"\bif\b.*(&&|\|\|).*\brand(n)?\(", "random draw inside a short-circuit condition"),
            ("S3", r"catch\s*(\w+)?\s*$", "catch block: check it does not turn failures into results")],
    ".m": [("S1", r"/\s*max\([^)]*1e-\d+", "denominator floored at a tiny constant"),
           ("R3", r"rng\(\s*([^)]+)\)", "seed")],
    ".sh": [("G2", r"grep\s+-c[^|]*\|\|\s*echo\s+0", "grep -c exits 1 with output '0'; '|| echo 0' then yields '0\\n0'"),
            ("G2", r"grep\s+-[A-Za-z]*F[A-Za-z]*\s+\"[^\"]*/[^\"]*\"", "path matched without an end delimiter: "
                                                                     "'id_ed25519' also matches 'id_ed25519.pub'")],
}
REGEX_RULES[".R"] = REGEX_RULES[".r"]
REGEX_RULES[".bash"] = REGEX_RULES[".sh"]


def scan(paths: list[str], excludes: list[str]) -> tuple[list[dict], dict, int]:
    hits: list[dict] = []
    seeds: dict = defaultdict(list)
    defs: dict = {}
    refs: set = set()
    nfiles = 0
    for root_path in paths:
        for root, dirs, files in os.walk(root_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".") and not d.endswith("-venv")]
            for fn in files:
                path = os.path.join(root, fn)
                rel = os.path.relpath(path, root_path) if len(paths) == 1 else path
                if any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(fn, g) for g in excludes):
                    continue
                ext = os.path.splitext(fn)[1]
                if ext not in (".py",) and ext not in REGEX_RULES:
                    continue
                try:
                    text = open(path, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                if len(text) > 3_000_000:
                    continue
                lines = text.splitlines()
                nfiles += 1
                if ext == ".py":
                    try:
                        tree = ast.parse(text)
                    except SyntaxError:
                        continue
                    v = Visitor(rel, lines, hits, seeds, defs, refs)
                    v.visit(tree)
                    v.finish()
                    if not re.search(r"(^|/)(tests?|testing)(/|$)|(^|/)test_|_test\.py$", rel):
                        for i, line in enumerate(lines, 1):
                            if TODO_RX.search(line):
                                hits.append({"code": "X1", "file": rel, "line": i, "src": line.strip()[:160],
                                             "note": "unfinished-code marker: check that this path does not "
                                                     "produce a reported number"})
                else:
                    for code, rx, note in REGEX_RULES[ext]:
                        for i, line in enumerate(lines, 1):
                            m = re.search(rx, line)
                            if m:
                                if code == "R3":
                                    seeds[rel].append((i, m.group(m.lastindex or 0), line.strip()[:160]))
                                else:
                                    hits.append({"code": code, "file": rel, "line": i, "src": line.strip()[:160],
                                                 "note": note})
    for name, places in defs.items():
        if name not in refs:
            for f, ln, src in places:
                hits.append({"code": "X2", "file": f, "line": ln, "src": src,
                             "note": f"metric-like function '{name}' is never referenced: a metric described in the "
                                     "paper may never be computed, or a different one is used"})
    return hits, seeds, nfiles


TITLES = {
    "S1": "Sentinel guards in denominators", "S2": "Constants returned on edge-case branches",
    "S3": "Swallowed exceptions", "S4": "Missing values replaced by constants",
    "R1": "Random draws inside conditions", "R2": "Random draws in only one branch",
    "P1": "Numbers hard-coded in figure text", "L1": "Preprocessing fitted before the train/test split",
    "L2": "Selection by a test-set score",
    "G1": "Numbers checked by substring", "G2": "Shell matching pitfalls",
    "X1": "Placeholder or synthetic data on a result path", "X2": "Metric functions never used",
}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--out", help="directory for integrity_scan.md / .json (default: print only)")
    ap.add_argument("--exclude", nargs="*", default=[])
    args = ap.parse_args(argv)
    hits, seeds, nfiles = scan(args.paths, args.exclude)
    by = defaultdict(list)
    for h in hits:
        by[h["code"]].append(h)
    lines = [f"# Integrity scan: {', '.join(args.paths)}", "",
             f"{nfiles} code files scanned; {len(hits)} leads. Every lead must be read in context: a guard can be "
             "legitimate, a branch can be unreachable in reported runs.", "",
             "| code | leads | pattern |", "|---|---|---|"]
    for code in TITLES:
        lines.append(f"| {code} | {len(by.get(code, []))} | {TITLES[code]} |")
    for code, title in TITLES.items():
        if not by.get(code):
            continue
        lines += ["", f"## {code} {title} ({len(by[code])})", "", "| loc | code | note |", "|---|---|---|"]
        for h in sorted(by[code], key=lambda h: (h["file"], h["line"]))[:300]:
            lines.append(f"| {h['file']}:{h['line']} | `{h['src'].replace('|', '/')[:110]}` | {h['note']} |")
    if seeds:
        lines += ["", "## R3 Seeds (compare across arms, conditions and parameter values)", "",
                  "| file | line | seed expression | code |", "|---|---|---|---|"]
        for f in sorted(seeds):
            for ln, v, src in seeds[f][:60]:
                lines.append(f"| {f} | {ln} | `{v}` | `{src.replace('|', '/')[:100]}` |")
    report = "\n".join(lines) + "\n"
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        with open(os.path.join(args.out, "integrity_scan.md"), "w", encoding="utf-8") as fh:
            fh.write(report)
        with open(os.path.join(args.out, "integrity_scan.json"), "w", encoding="utf-8") as fh:
            json.dump({"hits": hits, "seeds": {k: v for k, v in seeds.items()}}, fh, ensure_ascii=False, indent=1)
        print(f"{nfiles} files, {len(hits)} leads, seeds in {len(seeds)} files -> {args.out}/integrity_scan.md")
    else:
        print(report)


if __name__ == "__main__":
    main()
