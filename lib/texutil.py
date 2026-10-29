"""texutil.py - LaTeX reading and cleaning shared by the Science-Skill scripts.

Everything here keeps line numbers: cleaned text has the same number of lines
as the source, so an offset in cleaned text maps back to file:line through
Source.loc().
"""
from __future__ import annotations

import os
import re
import sys

ABBREVIATIONS = [
    "e.g.", "i.e.", "et al.", "Eq.", "Eqs.", "Fig.", "Figs.", "Ref.", "Refs.", "Sec.", "Secs.",
    "Thm.", "Thms.", "Prop.", "Lem.", "Cor.", "Def.", "App.", "Apps.", "vs.", "cf.", "approx.",
    "resp.", "Ch.", "No.", "Tab.", "Phys.", "Rev.", "Lett.", "Nat.", "Proc.", "Appx.", "etc.",
    "Dr.", "Prof.", "St.", "ca.", "viz.", "Conj.", "Alg.", "Ex.",
]

SECTION_CMD = re.compile(r"\\section\*?\s*(?:\[[^\]]*\])?\s*\{")
DISPLAY_ENVS = ("equation", "align", "gather", "multline", "eqnarray", "displaymath", "flalign", "alignat", "math")
FLOAT_ENVS = ("figure", "figure*", "table", "table*", "wrapfigure", "algorithm", "algorithm*")


# ---------------------------------------------------------------------------
# helpers that keep the line count of the text unchanged
# ---------------------------------------------------------------------------
def _keep_lines(s: str, repl: str = "") -> str:
    return repl + "\n" * s.count("\n")


def _sub(pattern, repl, text, flags=0):
    rx = re.compile(pattern, flags) if isinstance(pattern, str) else pattern

    def f(m):
        r = repl(m) if callable(repl) else m.expand(repl)
        return r + "\n" * (m.group(0).count("\n") - r.count("\n"))
    return rx.sub(f, text)


def _match_brace(text: str, i: int) -> int:
    """text[i] == '{'; return index just past the matching '}' (or len)."""
    depth = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def _command_spans(text: str, names: tuple[str, ...]):
    """Yield (start, arg_start, end) for \\name*[opt]{arg} occurrences."""
    rx = re.compile(r"\\(" + "|".join(re.escape(n) for n in names) + r")\*?\s*(?:\[[^\]]*\]\s*)*\{")
    pos = 0
    while True:
        m = rx.search(text, pos)
        if not m:
            return
        end = _match_brace(text, m.end() - 1)
        yield m.start(), m.end(), end, m.group(1)
        pos = end


def _replace_commands(text: str, names: tuple[str, ...], mode: str) -> str:
    """mode 'drop' removes the command with its argument, 'keep' keeps the
    argument text, 'ref' replaces it by the token REF."""
    out = []
    pos = 0
    for start, arg_start, end, _name in _command_spans(text, names):
        out.append(text[pos:start])
        chunk = text[start:end]
        if mode == "keep":
            out.append(text[arg_start:end - 1])
        elif mode == "ref":
            out.append(_keep_lines(chunk, "REF"))
        else:
            out.append(_keep_lines(chunk, " "))
        pos = end
    out.append(text[pos:])
    return "".join(out)


def _drop_envs(text: str, envs: tuple[str, ...], repl: str) -> tuple[str, int]:
    count = 0
    for env in envs:
        rx = re.compile(r"\\begin\{" + re.escape(env) + r"\*?\}.*?\\end\{" + re.escape(env) + r"\*?\}", re.S)
        text, n = rx.subn(lambda m: _keep_lines(m.group(0), repl), text)
        count += n
    return text, count


def _texorpdf(text: str) -> str:
    """\\texorpdfstring{tex}{pdf} -> tex"""
    out, pos = [], 0
    for m in re.finditer(r"\\texorpdfstring\s*\{", text):
        if m.start() < pos:
            continue
        a_end = _match_brace(text, m.end() - 1)
        b_start = text.find("{", a_end)
        if b_start < 0:
            break
        b_end = _match_brace(text, b_start)
        out.append(text[pos:m.start()])
        out.append(text[m.end():a_end - 1] + "\n" * text[a_end:b_end].count("\n"))
        pos = b_end
    out.append(text[pos:])
    return "".join(out)


def clean_latex(text: str, strip_comments: bool = True) -> tuple[str, dict]:
    """Turn LaTeX into prose while keeping one output line per input line."""
    stats = {"inline_math": 0, "display_math": 0, "citations": 0}
    if strip_comments:
        text = re.sub(r"(?<!\\)%[^\n]*", "", text)
    text = _texorpdf(text)
    text, _ = _drop_envs(text, FLOAT_ENVS, " ")
    text, n = _drop_envs(text, DISPLAY_ENVS, " DMATH ")
    stats["display_math"] += n
    for rx in (r"\$\$.*?\$\$", r"\\\[.*?\\\]"):
        text, n = re.subn(rx, lambda m: _keep_lines(m.group(0), " DMATH "), text, flags=re.S)
        stats["display_math"] += n
    for rx in (r"(?<!\\)\$(?:\\\$|[^$])+?(?<!\\)\$", r"\\\(.*?\\\)"):
        text, n = re.subn(rx, lambda m: _keep_lines(m.group(0), "MATH"), text, flags=re.S)
        stats["inline_math"] += n
    cites = list(_command_spans(text, ("cite", "citep", "citet", "Cite", "onlinecite", "citealp", "citeauthor", "citenum")))
    stats["citations"] = len(cites)
    text = _replace_commands(text, ("cite", "citep", "citet", "Cite", "onlinecite", "citealp", "citenum"), "drop")
    text = _replace_commands(text, ("citeauthor",), "keep")
    text = _replace_commands(text, ("footnote", "thanks", "label", "includegraphics", "caption", "vspace", "hspace",
                                    "bibliography", "bibliographystyle", "hypersetup", "url"), "drop")
    text = _replace_commands(text, ("ref", "cref", "Cref", "eqref", "autoref", "pageref", "nameref", "Ref", "Eqref",
                                    "crefrange", "Crefrange"), "ref")
    # \xref{label}{text}: keep the text
    text = _sub(r"\\xref\{[^{}]*\}\{([^{}]*)\}", lambda m: m.group(1), text)
    for _ in range(3):
        text = _replace_commands(text, ("emph", "textit", "textbf", "textsc", "texttt", "mbox", "text", "textrm",
                                        "underline", "textsf", "textnormal", "textmd", "textup", "hbox", "enquote",
                                        "mathrm", "uline", "textcolor"), "keep")
    text = re.sub(r"\\item\b(?:\[[^\]]*\])?", "\u2022 ", text)
    text = re.sub(r"\\(?:begin|end)\{[^{}]*\}(?:\[[^\]]*\])?", " ", text)
    text = text.replace("\\%", "%").replace("\\&", "&").replace("\\$", "$").replace("\\_", "_")
    text = text.replace("---", "\u2014").replace("--", "\u2013").replace("~", " ")
    text = text.replace("``", "\u201c").replace("''", "\u201d")
    text = re.sub(r"\\[a-zA-Z@]+\*?(?:\[[^\]\n]*\])?", " ", text)
    text = re.sub(r"\\[^a-zA-Z\n]", " ", text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"[ \t]+", " ", text)
    return text, stats


def light_clean(text: str) -> tuple[str, dict]:
    """For markdown/plain text that may contain $...$ but where % is literal."""
    return clean_latex(text, strip_comments=False)


# ---------------------------------------------------------------------------
# reading sources
# ---------------------------------------------------------------------------
class Source:
    """Concatenated text with a map from each line to (file, line)."""

    def __init__(self):
        self.lines: list[str] = []
        self.where: list[tuple[str, int]] = []

    @property
    def text(self) -> str:
        return "".join(self.lines)

    def loc(self, line_index: int) -> tuple[str, int]:
        if not self.where:
            return ("?", 0)
        line_index = max(0, min(line_index, len(self.where) - 1))
        return self.where[line_index]


INPUT_RX = re.compile(r"^(?P<pre>[^%]*?)\\(?:input|include|subfile)\s*\{(?P<name>[^{}]+)\}")


def read_tex(path: str, src: Source | None = None, depth: int = 0, root: str | None = None) -> Source:
    src = src or Source()
    root = root or os.path.dirname(os.path.abspath(path))
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read().replace("\r\n", "\n").replace("\r", "\n").splitlines(keepends=True)
    except OSError as exc:
        print(f"warning: cannot read {path}: {exc}", file=sys.stderr)
        return src
    rel = os.path.relpath(os.path.abspath(path), root)
    for i, line in enumerate(raw, 1):
        m = INPUT_RX.match(line)
        if m and depth < 6:
            name = m.group("name").strip()
            cands = [os.path.join(root, name), os.path.join(os.path.dirname(path), name)]
            cands += [c + ".tex" for c in list(cands)]
            target = next((c for c in cands if os.path.isfile(c)), None)
            if target:
                src.lines.append(m.group("pre") + "\n")
                src.where.append((rel, i))
                read_tex(target, src, depth + 1, root)
                continue
        if not line.endswith("\n"):
            line += "\n"
        src.lines.append(line)
        src.where.append((rel, i))
    return src


def read_plain(path: str) -> Source:
    src = Source()
    with open(path, encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh.read().replace("\r\n", "\n").splitlines(keepends=True), 1):
            if not line.endswith("\n"):
                line += "\n"
            src.lines.append(line)
            src.where.append((os.path.basename(path), i))
    return src


# ---------------------------------------------------------------------------
# section finding: returns {name: (start_offset, end_offset)} into src.text
# ---------------------------------------------------------------------------
def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset)


def tex_sections(text: str) -> dict[str, tuple[int, int, str]]:
    nocomment = re.sub(r"(?<!\\)%[^\n]*", lambda m: " " * len(m.group(0)), text)
    secs: dict[str, tuple[int, int, str]] = {}
    m = re.search(r"\\title\s*(?:\[[^\]]*\])?\s*\{", nocomment)
    if m:
        end = _match_brace(nocomment, m.end() - 1)
        secs["title"] = (m.end(), end - 1, "")
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", nocomment, re.S)
    if m:
        secs["abstract"] = (m.start(1), m.end(1), "")
    else:
        m = re.search(r"\\abstract\s*\{", nocomment)
        if m:
            secs["abstract"] = (m.end(), _match_brace(nocomment, m.end() - 1) - 1, "")

    headings = []
    for hm in SECTION_CMD.finditer(nocomment):
        end = _match_brace(nocomment, hm.end() - 1)
        headings.append((hm.start(), end, nocomment[hm.end():end - 1]))
    stops = [h[0] for h in headings]
    for rx in (r"\\appendix\b", r"\\bibliography\{", r"\\begin\{thebibliography\}", r"\\end\{document\}",
               r"\\begin\{acknowledgments?\}", r"\\section\*?\{Acknowledg"):
        mm = re.search(rx, nocomment)
        if mm:
            stops.append(mm.start())
    stops = sorted(set(stops))

    def next_stop(after: int) -> int:
        return next((s for s in stops if s > after), len(text))

    intro = next((h for h in headings if re.search(r"introduction|^\s*background\s*$", h[2], re.I)), None)
    if intro:
        secs["introduction"] = (intro[1], next_stop(intro[1]), "")
    else:
        # PRL style: the introduction is the text between the front matter and
        # the first \section.
        anchors = [x.end() for x in re.finditer(r"\\maketitle|\\end\{abstract\}", nocomment)]
        begin = max(anchors) if anchors else None
        if begin is None:
            bd = re.search(r"\\begin\{document\}", nocomment)
            begin = bd.end() if bd else None
        if begin is not None:
            end = next_stop(begin)
            if end - begin > 400:
                secs["introduction"] = (begin, end, "implicit (text before first \\section)")
    concl = [h for h in headings if re.search(r"conclu|discussion|outlook|summary|closing", h[2], re.I)]
    if concl:
        h = concl[-1]
        secs["conclusion"] = (h[1], next_stop(h[1]), h[2].strip())
    return secs


def md_sections(text: str) -> dict[str, tuple[int, int, str]]:
    secs: dict[str, tuple[int, int, str]] = {}
    heads = [(m.start(), m.end(), m.group(2).strip()) for m in re.finditer(r"^(#{1,3})\s+(.+)$", text, re.M)]
    for i, (s, e, title) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        low = title.lower()
        for key, rx in (("abstract", r"^abstract"), ("introduction", r"^intro"),
                        ("conclusion", r"conclu|discussion|outlook|summary"), ("title", r"^title$")):
            if re.search(rx, low) and key not in secs:
                secs[key] = (e, end, "")
    if "title" not in secs and heads and heads[0][2] and not re.match(r"abstract|intro", heads[0][2], re.I):
        secs["title"] = (heads[0][0] + len(heads[0][2]) - len(heads[0][2]), heads[0][1], "")
    return secs


def tex_captions(text: str) -> list[tuple[int, int]]:
    nocomment = re.sub(r"(?<!\\)%[^\n]*", lambda m: " " * len(m.group(0)), text)
    out = []
    for m in re.finditer(r"\\caption\*?\s*(?:\[[^\]]*\])?\s*\{", nocomment):
        end = _match_brace(nocomment, m.end() - 1)
        out.append((m.end(), end - 1))
    return out


# ---------------------------------------------------------------------------
# measurement
# ---------------------------------------------------------------------------
WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\u2019\-\u2013]*|MATH|DMATH")


def _protect(text: str) -> str:
    for ab in ABBREVIATIONS:
        safe = ab.replace(".", "\u2024")
        text = re.sub(r"(?<![A-Za-z])" + re.escape(ab), safe, text)
    # initials such as "A. B. Smith"
    text = re.sub(r"\b([A-Z])\.(?=\s?[A-Z][a-z])", "\\1\u2024", text)
    return text


def sentences(text: str) -> list[tuple[int, int]]:
    prot = _protect(text)
    spans = []
    start = 0
    for m in re.finditer(r"(?<=[.!?])[\"\u201d')\]]*\s+(?=[\"\u201c(\[]?[A-Z0-9\u2022]|MATH|DMATH)", prot):
        if prot[start:m.start()].strip():
            spans.append((start, m.start()))
        start = m.end()
    if prot[start:].strip():
        spans.append((start, len(prot)))
    return spans


def paragraphs(text: str) -> int:
    return len([p for p in re.split(r"\n\s*\n|\\par\b", text) if WORD.search(p)])


def snippet(text: str, a: int, b: int, width: int = 70) -> str:
    s = text[max(0, a - width):min(len(text), b + width)]
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# offset-preserving helpers used by number-audit, cite-verify, novelty-audit
# ---------------------------------------------------------------------------
def strip_comments_keep(text: str) -> str:
    """Replace LaTeX comments by spaces of the same length (offsets unchanged)."""
    return re.sub(r"(?<!\\)%[^\n]*", lambda m: " " * len(m.group(0)), text)


CITE_CMDS = ("cite", "citep", "citet", "Cite", "onlinecite", "citealp", "citealt", "citenum", "citeauthor",
             "citeyear", "parencite", "textcite", "autocite", "footcite", "nocite")


def find_cites(text: str) -> list[tuple[int, int, str, list[str]]]:
    """[(start, end, command, [keys])] for every citation command (comments ignored)."""
    nc = strip_comments_keep(text)
    out = []
    for start, arg_start, end, name in _command_spans(nc, CITE_CMDS):
        keys = [k.strip() for k in nc[arg_start:end - 1].split(",") if k.strip()]
        out.append((start, end, name, keys))
    return out


def find_macros(text: str) -> dict[str, str]:
    """\\newcommand{\\X}{body}, \\renewcommand, \\providecommand, \\def\\X{body} -> {"\\X": body}.
    Macros with arguments are skipped."""
    nc = strip_comments_keep(text)
    out: dict[str, str] = {}
    rx = re.compile(r"\\(?:re|provide)?newcommand\*?\s*\{?\s*(\\[A-Za-z@]+)\s*\}?\s*(\[\d\])?\s*\{")
    for m in rx.finditer(nc):
        if m.group(2):
            continue
        end = _match_brace(nc, m.end() - 1)
        out[m.group(1)] = nc[m.end():end - 1]
    for m in re.finditer(r"\\def\s*(\\[A-Za-z@]+)\s*\{", nc):
        end = _match_brace(nc, m.end() - 1)
        out.setdefault(m.group(1), nc[m.end():end - 1])
    return out


THEOREM_ENVS = ("theorem", "lemma", "proposition", "corollary", "conjecture", "definition", "claim", "remark",
                "assumption", "hypothesis")


def region_labeler(text: str):
    """Return f(offset) -> region label: title, abstract, introduction,
    conclusion, caption, table, theorem:<env>, appendix:<heading>,
    section:<heading>, front, back."""
    nc = strip_comments_keep(text)
    secs = tex_sections(text)
    spans: list[tuple[int, int, str]] = []
    for name in ("title", "abstract", "introduction", "conclusion"):
        if name in secs:
            spans.append((secs[name][0], secs[name][1], name))
    for a, b in tex_captions(text):
        spans.append((a, b, "caption"))
    for env in ("table", "tabular", "tabularx", "longtable"):
        for m in re.finditer(r"\\begin\{" + env + r"\*?\}.*?\\end\{" + env + r"\*?\}", nc, re.S):
            spans.append((m.start(), m.end(), "table"))
    for m in re.finditer(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", nc, re.S):
        spans.append((m.start(), m.end(), "bibliography"))
    for env in THEOREM_ENVS:
        for m in re.finditer(r"\\begin\{" + env + r"\*?\}.*?\\end\{" + env + r"\*?\}", nc, re.S):
            spans.append((m.start(), m.end(), "theorem:" + env))
    heads = []
    for m in re.finditer(r"\\(section|subsection)\*?\s*(?:\[[^\]]*\])?\s*\{", nc):
        end = _match_brace(nc, m.end() - 1)
        heads.append((m.start(), re.sub(r"\s+", " ", nc[m.end():end - 1]).strip()[:50], m.group(1)))
    app = re.search(r"\\appendix\b", nc)
    app_at = app.start() if app else None
    begin_doc = re.search(r"\\begin\{document\}", nc)
    doc_at = begin_doc.end() if begin_doc else 0
    sec_heads = [h for h in heads if h[2] == "section"]

    def label(off: int) -> str:
        best = None
        for a, b, name in spans:
            if a <= off < b and (best is None or (b - a) < (best[1] - best[0])):
                best = (a, b, name)
        if best:
            return best[2]
        if off < doc_at:
            return "preamble"
        head = None
        for h in sec_heads:
            if h[0] <= off:
                head = h
        prefix = "appendix" if app_at is not None and off >= app_at else "section"
        return f"{prefix}:{head[1]}" if head else ("appendix" if prefix == "appendix" else "front")
    return label


# ---------------------------------------------------------------------------
# format-independent loading: .tex, .md, .txt, .docx, .pdf
# ---------------------------------------------------------------------------
def doc_kind(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return {".tex": "tex", ".ltx": "tex", ".md": "md", ".markdown": "md", ".docx": "docx", ".pdf": "pdf",
            ".rst": "md"}.get(ext, "txt")


def read_docx(path: str) -> Source:
    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
    from docxutil import docx_to_markdown
    text, pmap = docx_to_markdown(path)
    src = Source()
    name = os.path.basename(path)
    for line, para in zip(text.splitlines(keepends=True), pmap + [pmap[-1] if pmap else 0] * 2):
        src.lines.append(line if line.endswith("\n") else line + "\n")
        src.where.append((name + " ¶", para))
    return src


def read_pdf(path: str) -> Source:
    import shutil
    import subprocess
    exe = shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("PDF input needs pdftotext (poppler); install it or export the manuscript as .docx/.txt")
    out = subprocess.run([exe, "-layout", "-enc", "UTF-8", path, "-"], capture_output=True, text=True, check=True).stdout
    src = Source()
    name = os.path.basename(path)
    page = 1
    for i, line in enumerate(out.splitlines(keepends=True), 1):
        if "\f" in line:
            page += line.count("\f")
            line = line.replace("\f", "")
        src.lines.append(line if line.endswith("\n") else line + "\n")
        src.where.append((f"{name} p{page} l", i))
    return src


def load_document(path: str, plain: bool = False) -> tuple[Source, str]:
    """Return (Source, kind). kind is the parser to use for sections: tex or md
    (docx and pdf are converted to markdown-like text first) or txt."""
    kind = "txt" if plain else doc_kind(path)
    if kind == "tex":
        return read_tex(path), "tex"
    if kind == "docx":
        return read_docx(path), "md"
    if kind == "pdf":
        src = read_pdf(path)
        return src, "pdfmd"
    return read_plain(path), ("md" if kind == "md" else "txt")


STRUCTURED_LABELS = re.compile(
    r"^\s*\**(background|objectives?|aims?|purpose|context|importance|methods?|design|setting|participants|"
    r"interventions?|main outcome measures?|measurements|results?|findings|conclusions?|interpretation|"
    r"relevance|significance|funding|trial registration)\**\s*[:.]", re.I | re.M)


def is_structured_abstract(text: str) -> bool:
    return len(set(m.group(1).lower()[:5] for m in STRUCTURED_LABELS.finditer(text))) >= 3


def plain_sections(text: str) -> dict[str, tuple[int, int, str]]:
    """Sections for markdown-like text (md, converted docx/pdf, plain text with
    heading lines). Handles IMRaD headings, numbered headings, ALL-CAPS
    headings, and the Nature style where the introduction has no heading."""
    secs: dict[str, tuple[int, int, str]] = {}
    heads = []
    for m in re.finditer(r"^(?:#{1,6}[ \t]+(.+?)|((?:\d+(?:\.\d+)*\.?[ \t]+)?[A-Z][A-Za-z ,&\-]{2,60}|[A-Z][A-Z ,&\-]{3,60}))[ \t]*$",
                         text, re.M):
        title = (m.group(1) or m.group(2) or "").strip()
        bare = re.sub(r"^\d+(\.\d+)*\.?\s+", "", title).strip().rstrip(":")
        if m.group(1) or re.fullmatch(r"(?i)(abstract|summary|introduction|background|methods?|materials and methods|"
                                      r"results(?: and discussion)?|discussion|conclusions?|references|bibliography|"
                                      r"literature cited|acknowledg\w*|related work|limitations|outlook|"
                                      r"concluding remarks|summary and outlook)", bare):
            heads.append((m.start(), m.end(), bare, m.start(1) if m.group(1) else m.start(2)))
    for i, (s, e, title, _ts) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        low = title.lower()
        for key, rx in (("abstract", r"^(abstract|summary)$"), ("introduction", r"^(introduction|background)\b"),
                        ("conclusion", r"conclu|discussion|outlook|summary and|concluding"),
                        ("references", r"^(references|bibliography|literature cited)$")):
            if re.search(rx, low) and key not in secs:
                if key == "abstract" and "introduction" in secs:
                    continue
                secs[key] = (e, end, "")
    if heads and "title" not in secs:
        h0 = heads[0]
        first_kw = re.fullmatch(r"(?i)(abstract|summary|introduction|background)", h0[2])
        before_abs = "abstract" not in secs or h0[0] < secs["abstract"][0]
        if not first_kw and before_abs and len(h0[2].split()) >= 3:
            secs["title"] = (h0[3], h0[1], "")
    if "introduction" not in secs and "abstract" in secs:
        a_end = secs["abstract"][1]
        nxt = next((h for h in heads if h[0] >= a_end), None)
        if nxt is None or True:
            # Nature style: unheaded paragraphs right after the abstract
            following = [h for h in heads if h[0] >= a_end]
            start = a_end
            end = following[0][0] if following else len(text)
            if end - start > 400:
                secs["introduction"] = (start, end, "implicit (unheaded text after the abstract)")
    return secs


CAPTION_START = re.compile(r"^\s*\**((?:Supplementary\s+)?(?:Figure|Fig\.|Table|Extended Data Fig\.?)\s*S?\d+[A-Za-z]?)"
                           r"\s*[.:|—–-]", re.I | re.M)


def plain_captions(text: str) -> list[tuple[int, int]]:
    out = []
    for m in CAPTION_START.finditer(text):
        end = text.find("\n\n", m.start())
        out.append((m.start(), end if end > 0 else len(text)))
    return out


def doc_sections(text: str, kind: str) -> dict[str, tuple[int, int, str]]:
    return tex_sections(text) if kind == "tex" else plain_sections(text)


def doc_captions(text: str, kind: str) -> list[tuple[int, int]]:
    return tex_captions(text) if kind == "tex" else plain_captions(text)


def plain_region_labeler(text: str):
    secs = plain_sections(text)
    spans = [(a, b, name) for name, (a, b, _n) in secs.items() if name in ("title", "abstract", "introduction",
                                                                            "conclusion", "references")]
    spans += [(a, b, "caption") for a, b in plain_captions(text)]
    for m in re.finditer(r"(?m)^(?:[^\n|]*\|){2,}[^\n]*$", text):
        spans.append((m.start(), m.end(), "table"))
    heads = [(m.start(), m.group(1).strip()[:50]) for m in re.finditer(r"(?m)^#{1,6}\s+(.+)$", text)]

    def label(off: int) -> str:
        best = None
        for a, b, name in spans:
            if a <= off < b and (best is None or (b - a) < (best[1] - best[0])):
                best = (a, b, name)
        if best:
            return best[2]
        head = None
        for h in heads:
            if h[0] <= off:
                head = h
        return f"section:{head[1]}" if head else "front"
    return label


def doc_region_labeler(text: str, kind: str):
    return region_labeler(text) if kind == "tex" else plain_region_labeler(text)
