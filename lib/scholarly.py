"""scholarly.py - OpenAlex / Crossref / arXiv access shared by the Science-Skill scripts.

Only public metadata APIs are contacted. Nothing personal is sent: set
OPENALEX_API_KEY or SCIENCE_SKILL_MAILTO yourself if you want them used.
arXiv sources are read in memory and never extracted or executed.
"""
from __future__ import annotations

import difflib
import gzip
import html
import io
import json
import os
import re
import sys
import tarfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import texutil  # noqa: E402

UA = "Science-Skill/0.2"
MAILTO = os.environ.get("SCIENCE_SKILL_MAILTO", "").strip()
OA_KEY = os.environ.get("OPENALEX_API_KEY", "").strip()
ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
_last_arxiv = 0.0


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
LAST_HTTP_ERROR: int | None = None
_ARXIV_DOWN = False


def http_get(url: str, binary: bool = False, tries: int = 3, timeout: int = 40, backoff: float = 3.0):
    headers = {"User-Agent": UA + (f" (mailto:{MAILTO})" if MAILTO else "")}
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
                return data if binary else data.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            global LAST_HTTP_ERROR
            last = e
            LAST_HTTP_ERROR = e.code
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(backoff * (k + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(2 * (k + 1))
    print(f"warning: GET failed {url}: {last}", file=sys.stderr)
    return None


def arxiv_get(url: str, binary: bool = False):
    """Rate-limited arXiv access with a circuit breaker: after arXiv answers
    429 (too many requests) through all retries, later arXiv calls in this run
    return None at once instead of stalling."""
    global _last_arxiv, _ARXIV_DOWN, LAST_HTTP_ERROR
    if _ARXIV_DOWN:
        return None
    wait = 3.1 - (time.time() - _last_arxiv)
    if wait > 0:
        time.sleep(wait)
    LAST_HTTP_ERROR = None
    try:
        res = http_get(url, binary=binary, tries=3, backoff=5.0)
        if res is None and LAST_HTTP_ERROR == 429:
            _ARXIV_DOWN = True
            print("warning: arXiv is rate-limiting this machine (HTTP 429); skipping arXiv for the rest of this run. "
                  "Results rely on Crossref / OpenAlex / Europe PMC; retry later for arXiv-only items.", file=sys.stderr)
        return res
    finally:
        _last_arxiv = time.time()


def oa_url(path: str, params: dict) -> str:
    p = dict(params)
    if OA_KEY:
        p["api_key"] = OA_KEY
    if MAILTO:
        p["mailto"] = MAILTO
    return "https://api.openalex.org/" + path + "?" + urllib.parse.urlencode(p, safe=":,|")


def oa_json(path: str, params: dict | None = None):
    txt = http_get(oa_url(path, params or {}))
    return json.loads(txt) if txt else None


# ---------------------------------------------------------------------------
# small utils
# ---------------------------------------------------------------------------
def norm_title(t: str) -> str:
    t = re.sub(r"<[^>]+>", " ", t or "")          # MathML / HTML markup in Crossref titles
    t = unicodedata.normalize("NFKD", t)
    t = re.sub(r"\$[^$]*\$", " ", t)
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def title_ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, norm_title(a), norm_title(b)).ratio()


def slugify(first_author: str, year, title: str) -> str:
    last = unicodedata.normalize("NFKD", first_author or "anon").encode("ascii", "ignore").decode()
    last = re.sub(r"[^A-Za-z]+", "", last.split()[-1] if last.split() else "anon").lower() or "anon"
    words = [w for w in norm_title(title).split() if w not in {"a", "an", "the", "of", "on", "for", "and", "in", "with", "to"}]
    return f"{last}{year or ''}-{'-'.join(words[:3]) or 'untitled'}"


def strip_jats(s: str) -> str:
    s = re.sub(r"<(?:jats:)?title>.*?</(?:jats:)?title>", " ", s, flags=re.S)
    s = re.sub(r"<(?:jats:)?inline-formula\b.*?</(?:jats:)?inline-formula>", " MATH ", s, flags=re.S)
    s = re.sub(r"<(\w+:)?math\b.*?</\1math>", " MATH ", s, flags=re.S)
    paras = re.split(r"</(?:jats:)?p>", s)
    paras = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", p))).strip() for p in paras]
    paras = [p for p in paras if p and not re.match(r"(Published by|\u00a9|Copyright|\(c\) \d{4})", p, re.I)]
    s = "\n\n".join(paras)
    s = re.sub(r"MATH\s+(?=[-,.;:)\u2013])", "MATH", s)
    s = re.sub(r"(?<=[(\[])\s+MATH", "MATH", s)
    return s.strip()


def inverted_to_text(inv: dict | None) -> str:
    if not inv:
        return ""
    pos = []
    for w, idxs in inv.items():
        for i in idxs:
            pos.append((i, w))
    text = " ".join(w for _, w in sorted(pos))
    return re.sub(r"(?<=[a-z0-9)\]])\.(?=[A-Z])", ". ", text)


ARXIV_ID = re.compile(r"(\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?")


def arxiv_from_url(u: str | None) -> str | None:
    if not u:
        return None
    m = re.search(r"arxiv\.org/(?:abs|pdf)/" + ARXIV_ID.pattern, u)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------
def resolve_venues(names: str) -> list[tuple[str, str]]:
    """Journal names or ISSNs (comma separated) -> [(OpenAlex source id, name)].
    An exact (case-insensitive) name match is required; otherwise the best
    candidate is used with a loud warning, because a wrong venue silently
    poisons the whole exemplar pool."""
    out = []
    for name in [n.strip() for n in names.split(",") if n.strip()]:
        if re.fullmatch(r"\d{4}-\d{3}[\dXx]", name):
            js = oa_json("sources", {"filter": "issn:" + name, "select": "id,display_name"})
            res = (js or {}).get("results", [])
            if res:
                out.append((res[0]["id"].rsplit("/", 1)[-1], res[0]["display_name"]))
            else:
                print(f"warning: no OpenAlex source with ISSN {name}", file=sys.stderr)
            continue
        js = oa_json("sources", {"search": name, "per_page": 50, "select": "id,display_name,works_count"})
        res = (js or {}).get("results", [])
        exact = [r for r in res if r["display_name"].lower() == name.lower()]
        if exact:
            pick = max(exact, key=lambda r: r.get("works_count") or 0)
        elif res:
            pick = res[0]
            print(f"warning: no exact OpenAlex match for '{name}'; using '{pick['display_name']}'. "
                  f"Pass the exact name or the ISSN. Candidates: "
                  + "; ".join(r["display_name"] for r in res[:6]), file=sys.stderr)
        else:
            pick = None
            print(f"warning: no OpenAlex source for '{name}'", file=sys.stderr)
        if pick:
            out.append((pick["id"].rsplit("/", 1)[-1], pick["display_name"]))
    return out


def crossref(doi: str) -> dict | None:
    q = "?mailto=" + urllib.parse.quote(MAILTO) if MAILTO else ""
    txt = http_get("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/:()") + q)
    if not txt:
        return None
    try:
        return json.loads(txt)["message"]
    except (ValueError, KeyError):
        return None


def openalex_by_doi(doi: str) -> dict | None:
    return oa_json("works/doi:" + doi, {})


def arxiv_meta(aid: str) -> dict | None:
    txt = arxiv_get("https://export.arxiv.org/api/query?" + urllib.parse.urlencode({"id_list": aid, "max_results": 1}))
    if not txt:
        return None
    root = ET.fromstring(txt)
    e = root.find("a:entry", ATOM)
    if e is None or e.find("a:title", ATOM) is None:
        return None
    idurl = e.findtext("a:id", default="", namespaces=ATOM)
    m = ARXIV_ID.search(idurl.split("/abs/")[-1])
    return {
        "id": m.group(1) if m else aid,
        "version": (m.group(2) or "") if m else "",
        "title": re.sub(r"\s+", " ", e.findtext("a:title", default="", namespaces=ATOM)).strip(),
        "abstract": re.sub(r"\s+", " ", e.findtext("a:summary", default="", namespaces=ATOM)).strip(),
        "authors": [a.findtext("a:name", default="", namespaces=ATOM) for a in e.findall("a:author", ATOM)],
        "published": e.findtext("a:published", default="", namespaces=ATOM)[:10],
        "doi": e.findtext("arxiv:doi", default="", namespaces=ATOM),
        "journal_ref": e.findtext("arxiv:journal_ref", default="", namespaces=ATOM),
    }


def arxiv_search_title(title: str) -> dict | None:
    words = [w for w in norm_title(title).split() if len(w) > 2][:12]
    if not words:
        return None
    q = " AND ".join(f"ti:{w}" for w in words)
    txt = arxiv_get("https://export.arxiv.org/api/query?" + urllib.parse.urlencode({"search_query": q, "max_results": 5}))
    if not txt:
        return None
    root = ET.fromstring(txt)
    best, best_r, best_title = None, 0.0, None
    for e in root.findall("a:entry", ATOM):
        t = re.sub(r"\s+", " ", e.findtext("a:title", default="", namespaces=ATOM))
        r = title_ratio(t, title)
        if r > best_r:
            m = ARXIV_ID.search(e.findtext("a:id", default="", namespaces=ATOM).split("/abs/")[-1])
            best, best_r, best_title = (m.group(1) if m else None), r, t
    if best and best_r >= 0.9 and best_title is not None and titles_match(best_title, title):
        return {"id": best, "ratio": best_r}
    return None


# ---------------------------------------------------------------------------
# arXiv LaTeX source -> abstract + introduction (in memory only)
# ---------------------------------------------------------------------------
MAX_MEMBER = 5_000_000


def arxiv_tex_files(aid: str) -> dict[str, str]:
    data = arxiv_get("https://arxiv.org/e-print/" + aid, binary=True)
    if not data:
        return {}
    files: dict[str, str] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile() or m.size > MAX_MEMBER or not m.name.lower().endswith(".tex"):
                    continue
                if m.name.startswith("/") or ".." in m.name.split("/"):
                    continue
                fh = tf.extractfile(m)
                if fh:
                    files[m.name] = fh.read().decode("utf-8", errors="replace")
        return files
    except tarfile.TarError:
        pass
    try:
        raw = gzip.decompress(data)
    except OSError:
        raw = data
    if raw[:4] == b"%PDF":
        return {}
    return {"main.tex": raw.decode("utf-8", errors="replace")}


def inline_inputs(files: dict[str, str], name: str, depth: int = 0) -> str:
    text = files.get(name, "")
    if depth > 6:
        return text
    base = os.path.dirname(name)

    def rep(m):
        target = m.group(1).strip()
        for cand in (target, target + ".tex", os.path.join(base, target), os.path.join(base, target) + ".tex"):
            cand = os.path.normpath(cand)
            if cand in files and cand != name:
                return inline_inputs(files, cand, depth + 1)
        return " "
    text = re.sub(r"(?<!%)\\(?:input|include|subfile)\s*\{([^{}]+)\}", rep, text)
    return text


def pick_main(files: dict[str, str]) -> str | None:
    cands = [n for n, t in files.items() if re.search(r"\\begin\{document\}", t)]
    if not cands:
        return None
    pref = [n for n in cands if re.search(r"(^|/)(main|ms|paper|article|manuscript)\.tex$", n, re.I)]
    return (pref or sorted(cands, key=lambda n: -len(files[n])))[0]


def arxiv_sections(aid: str) -> dict:
    files = arxiv_tex_files(aid)
    main = pick_main(files)
    if not main:
        return {"error": "no LaTeX source (PDF-only or download failed)"}
    text = inline_inputs(files, main)
    secs = texutil.tex_sections(text)
    out = {"main_file": main}
    for key in ("abstract", "introduction"):
        if key in secs:
            a, b, note = secs[key]
            raw = text[a:b]
            cleaned, _ = texutil.clean_latex(raw)
            cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(l.strip() for l in cleaned.splitlines())).strip()
            out[key] = {"raw": raw.strip(), "text": cleaned, "note": note}
    return out


# ---------------------------------------------------------------------------
# helpers used by cite-verify and novelty-audit
# ---------------------------------------------------------------------------
def crossref_search(title: str, author: str = "", rows: int = 5) -> list[dict]:
    params = {"query.bibliographic": title, "rows": rows}
    if author:
        params["query.author"] = author
    if MAILTO:
        params["mailto"] = MAILTO
    txt = http_get("https://api.crossref.org/works?" + urllib.parse.urlencode(params))
    if not txt:
        return []
    try:
        return json.loads(txt)["message"]["items"]
    except (ValueError, KeyError):
        return []


def crossref_year(cr: dict) -> int | None:
    for k in ("published-print", "published-online", "published", "issued"):
        dp = (cr.get(k) or {}).get("date-parts", [[None]])[0]
        if dp and dp[0]:
            return int(dp[0])
    return None


def crossref_years(cr: dict) -> set[int]:
    ys = set()
    for k in ("published-print", "published-online", "published", "issued"):
        dp = (cr.get(k) or {}).get("date-parts", [[None]])[0]
        if dp and dp[0]:
            ys.add(int(dp[0]))
    return ys


def crossref_updates(cr: dict) -> list[str]:
    """Retractions, corrections etc. attached to this work (Crossref 'updated-by')."""
    out = []
    for u in cr.get("updated-by") or []:
        t = (u.get("type") or "").lower()
        out.append(f"{t} {u.get('DOI', '')}".strip())
    return out


def openalex_work(ident: str) -> dict | None:
    """ident: OpenAlex id (W123...), DOI, arXiv id, PMID (PMID:123 or pmid:123) or PMCID (PMC123)."""
    ident = ident.strip()
    if re.match(r"^(https://openalex\.org/)?W\d+$", ident):
        return oa_json("works/" + ident.rsplit("/", 1)[-1], {})
    m = re.fullmatch(r"(?i)pmid:\s*(\d+)", ident)
    if m:
        return oa_json("works/pmid:" + m.group(1), {})
    m = re.fullmatch(r"(?i)(?:pmcid:\s*)?(PMC\d+)", ident)
    if m:
        return oa_json("works/pmcid:" + m.group(1).upper(), {})
    if ident.lower().startswith("10."):
        return oa_json("works/doi:" + ident, {})
    m = ARXIV_ID.fullmatch(ident) or ARXIV_ID.search(ident)
    if m:
        js = oa_json("works", {"filter": "doi:10.48550/arxiv." + m.group(1), "per_page": 1})
        res = (js or {}).get("results", [])
        if res:
            return res[0]
        meta = arxiv_meta(m.group(1))
        if meta:
            js = oa_json("works", {"filter": "title.search:" + re.sub(r"[,|:]", " ", meta["title"]), "per_page": 5})
            for r in (js or {}).get("results", []):
                if title_ratio(r.get("title") or "", meta["title"]) >= 0.9:
                    return r
    return None


WORK_SELECT = "id,doi,title,publication_year,publication_date,cited_by_count,primary_location,locations,authorships,type,is_retracted"


def openalex_list(filters: list[str], search: str | None = None, sort: str | None = None, n: int = 25,
                  select: str = WORK_SELECT) -> list[dict]:
    params = {"filter": ",".join(f for f in filters if f), "per_page": min(n, 200), "select": select}
    if search:
        params["search"] = search
    if sort:
        params["sort"] = sort
    js = oa_json("works", params)
    return (js or {}).get("results", [])


def openalex_by_ids(ids: list[str], select: str = WORK_SELECT) -> list[dict]:
    out = []
    ids = [i.rsplit("/", 1)[-1] for i in ids]
    for k in range(0, len(ids), 50):
        chunk = ids[k:k + 50]
        out += openalex_list(["openalex:" + "|".join(chunk)], n=len(chunk), select=select)
    return out


def work_row(r: dict) -> dict:
    arx = None
    for loc in r.get("locations") or []:
        arx = arx or arxiv_from_url(loc.get("landing_page_url")) or arxiv_from_url(loc.get("pdf_url"))
    au = r.get("authorships") or []
    return {
        "id": (r.get("id") or "").rsplit("/", 1)[-1],
        "year": r.get("publication_year"),
        "date": r.get("publication_date"),
        "cited_by": r.get("cited_by_count"),
        "venue": ((r.get("primary_location") or {}).get("source") or {}).get("display_name", ""),
        "doi": (r.get("doi") or "").replace("https://doi.org/", ""),
        "arxiv": arx or "",
        "first_author": au[0]["author"]["display_name"] if au else "",
        "title": r.get("title") or "",
        "retracted": bool(r.get("is_retracted")),
    }


def arxiv_search(query: str, n: int = 25, sort: str = "submittedDate") -> list[dict]:
    """Free-text arXiv search (all: fields), newest first by default."""
    toks = [t for t in re.findall(r'"[^"]+"|[A-Za-z0-9\-+]+', query) if t not in ("AND", "OR", "NOT") and len(t) > 1]
    q = " AND ".join(f"all:{t}" for t in toks)
    txt = arxiv_get("https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": q, "max_results": n, "sortBy": sort, "sortOrder": "descending"}))
    if not txt:
        return []
    root = ET.fromstring(txt)
    out = []
    for e in root.findall("a:entry", ATOM):
        m = ARXIV_ID.search(e.findtext("a:id", default="", namespaces=ATOM).split("/abs/")[-1])
        out.append({
            "arxiv": m.group(1) if m else "",
            "date": e.findtext("a:published", default="", namespaces=ATOM)[:10],
            "title": re.sub(r"\s+", " ", e.findtext("a:title", default="", namespaces=ATOM)).strip(),
            "first_author": (e.find("a:author/a:name", ATOM).text if e.find("a:author/a:name", ATOM) is not None else ""),
            "journal_ref": e.findtext("arxiv:journal_ref", default="", namespaces=ATOM),
        })
    return out


def datacite(doi: str) -> dict | None:
    """DataCite record for DOIs not registered with Crossref (LIPIcs, Zenodo, arXiv 10.48550, ...)."""
    txt = http_get("https://api.datacite.org/dois/" + urllib.parse.quote(doi, safe="/:()"))
    if not txt:
        return None
    try:
        return json.loads(txt)["data"]["attributes"]
    except (ValueError, KeyError, TypeError):
        return None


def doi_resolves(doi: str) -> bool | None:
    """True/False from the DOI handle API; None if the check itself failed."""
    txt = http_get("https://doi.org/api/handles/" + urllib.parse.quote(doi, safe="/:()"))
    if txt is None:
        return False
    try:
        return json.loads(txt).get("responseCode") == 1
    except ValueError:
        return None


_TITLE_FILLER = {"a", "an", "the", "of", "on", "for", "and", "in", "with", "to", "via", "from", "by", "at", "its"}


def titles_match(a: str, b: str) -> bool:
    """Stricter than title_ratio: near-identical titles that differ in a content
    token ("Clifford+T" vs "Clifford+V") do not match."""
    ta, tb = norm_title(a).split(), norm_title(b).split()
    if not ta or not tb:
        return False
    if ta == tb:
        return True
    if title_ratio(a, b) < 0.9:
        return False
    def stem(w):
        return w[:-1] if len(w) > 3 and w.endswith("s") else w
    diff = {stem(w) for w in ta} ^ {stem(w) for w in tb}
    return all(w in _TITLE_FILLER for w in diff)


# ---------------------------------------------------------------------------
# Europe PMC: PubMed, PMC full text, and bioRxiv / medRxiv / other preprints
# ---------------------------------------------------------------------------
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/"


def europepmc_search(query: str, n: int = 25, core: bool = True, sort: str | None = None) -> list[dict]:
    params = {"query": query, "format": "json", "pageSize": min(n, 100), "resultType": "core" if core else "lite"}
    if sort:
        params["sort"] = sort
    txt = http_get(EPMC + "search?" + urllib.parse.urlencode(params))
    if not txt and sort:
        params.pop("sort")
        txt = http_get(EPMC + "search?" + urllib.parse.urlencode(params))
    if not txt:
        return []
    try:
        return json.loads(txt)["resultList"]["result"]
    except (ValueError, KeyError):
        return []


def europepmc_row(r: dict) -> dict:
    src = r.get("source", "")
    venue = ((r.get("journalInfo") or {}).get("journal") or {}).get("title") or r.get("journalTitle") or ""
    if src == "PPR":
        venue = ((r.get("bookOrReportDetails") or {}).get("publisher") or "preprint") + " (preprint)"
    auth = (r.get("authorList") or {}).get("author") or []
    first = auth[0].get("fullName", "") if auth else (r.get("authorString", "").split(",")[0])
    return {"id": r.get("id", ""), "year": r.get("pubYear", ""), "date": r.get("firstPublicationDate", ""),
            "cited_by": r.get("citedByCount", ""), "venue": venue, "doi": r.get("doi", ""), "arxiv": "",
            "pmid": r.get("pmid", ""), "pmcid": r.get("pmcid", ""), "first_author": first,
            "title": (r.get("title") or "").rstrip("."), "retracted": "retract" in (r.get("pubTypeList") or {}).__str__().lower()}


def europepmc_lookup(ident: str) -> dict | None:
    """DOI, PMID (digits), or PMCID (PMC...) -> core record."""
    ident = ident.strip()
    if ident.upper().startswith("PMC"):
        q = f"PMCID:{ident.upper()}"
    elif ident.isdigit():
        q = f"EXT_ID:{ident} AND SRC:MED"
    else:
        q = f'DOI:"{ident}"'
    res = europepmc_search(q, n=1)
    return res[0] if res else None


def europepmc_sections(pmcid: str) -> dict:
    """Abstract and introduction from the PMC open-access JATS XML (if available)."""
    txt = http_get(EPMC + pmcid + "/fullTextXML")
    if not txt:
        return {"error": "no open-access full text in PMC"}
    try:
        root = ET.fromstring(txt)
    except ET.ParseError:
        return {"error": "full text XML could not be parsed"}

    def text_of(el) -> str:
        parts = [el.text or ""]
        for ch in el:
            tag = ch.tag.split("}")[-1]
            if tag in ("inline-formula", "disp-formula"):
                parts.append(" MATH ")
            elif tag in ("title", "label", "fig", "table-wrap", "xref") and tag != "xref":
                pass
            elif tag == "xref":
                parts.append("")
            else:
                parts.append(text_of(ch))
            parts.append(ch.tail or "")
        t = "".join(parts)
        t = re.sub(r"\(\s*(?:[;,\u2013\-]\s*)*\)|\[\s*(?:[;,\u2013\-]\s*)*\]", "", t)
        return re.sub(r"[ \t]+", " ", t).replace(" .", ".").replace(" ,", ",")

    out = {}
    ab = root.find(".//abstract")
    if ab is not None:
        out["abstract"] = "\n\n".join(re.sub(r"\s+", " ", text_of(p)).strip() for p in ab.iter("p"))
    intro = None
    body = root.find(".//body")
    if body is not None:
        for sec in body.findall("sec"):
            st = (sec.get("sec-type") or "").lower()
            title = (sec.findtext("title") or "").strip().lower()
            if "intro" in st or re.match(r"^(\d+\.?\s*)?(introduction|background)\b", title):
                intro = sec
                break
        if intro is None:
            first_sec = body.find("sec")
            leading = [p for p in body.findall("p")]
            if leading:
                out["introduction"] = "\n\n".join(re.sub(r"\s+", " ", text_of(p)).strip() for p in leading)
                out["intro_note"] = "implicit (paragraphs before the first section)"
            elif first_sec is not None:
                intro = first_sec
                out["intro_note"] = "first section (no Introduction heading)"
    if intro is not None:
        out["introduction"] = "\n\n".join(re.sub(r"\s+", " ", text_of(p)).strip() for p in intro.iter("p"))
    return out


# ---------------------------------------------------------------------------
# Zenodo: code, data, reports and independent reproductions often appear here first
# ---------------------------------------------------------------------------
def zenodo_search(query: str, n: int = 25, sort: str = "bestmatch", since: str | None = None) -> list[dict]:
    q = query if not since else f"({query}) AND publication_date:[{since} TO *]"
    params = {"q": q, "size": min(n, 100), "sort": "mostrecent" if sort == "date" else "bestmatch"}
    txt = http_get("https://zenodo.org/api/records?" + urllib.parse.urlencode(params))
    if not txt:
        return []
    try:
        hits = json.loads(txt)["hits"]["hits"]
    except (ValueError, KeyError):
        return []
    out = []
    for h in hits:
        m = h.get("metadata", {})
        creators = m.get("creators") or []
        out.append({"id": str(h.get("id", "")), "year": (m.get("publication_date") or "")[:4],
                    "date": m.get("publication_date", ""), "cited_by": "",
                    "venue": "Zenodo (" + ((m.get("resource_type") or {}).get("type") or "record") + ")",
                    "doi": h.get("doi") or m.get("doi", ""), "arxiv": "",
                    "first_author": creators[0].get("name", "") if creators else "",
                    "title": m.get("title", ""), "retracted": False})
    return out
