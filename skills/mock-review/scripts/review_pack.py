#!/usr/bin/env python3
"""review_pack.py - build an isolated, version-pinned copy of a paper repo for mock reviewers.

Subcommands
  pack --repo DIR --out DIR [--manuscript main.tex ...] [--roles r1,r2,r3]
       [--exclude GLOB ...] [--include-untracked GLOB ...] [--max-mb 20]
      Copies the repo into OUT/pack without the author's private material:
        - in a git repo only tracked files are copied (working-tree content,
          so uncommitted edits to tracked files are included); untracked
          files - where notes, earlier reviews and drafts usually live - are
          left out unless --include-untracked matches them;
        - default exclusions: CLAUDE.md, AGENTS.md, .claude/, polish/,
          rewrite_draft/, mock_review/, reviews/, outreach/, number_audit/,
          refcheck/, novelty/, *.zip; add more with --exclude;
        - files above --max-mb are omitted and listed.
      Writes OUT/PIN.json and OUT/MANIFEST.md (git HEAD, dirty flag, SHA-256 of
      the manuscript files: line numbers in the reviews refer to exactly this
      version). With --roles, also creates OUT/work-<role>/ copies so that
      reviewers who run code do not touch each other's files or the pack.

  check-pin OUT/PIN.json [--repo DIR]
      Re-hashes the manuscript files in the repo and says whether the reviews'
      line numbers still apply.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

DEFAULT_EXCLUDES = ["CLAUDE.md", "*/CLAUDE.md", "AGENTS.md", ".claude/*", "polish/*", "rewrite_draft/*",
                    "mock_review/*", "reviews/*", "outreach/*", "number_audit/*", "refcheck/*", "novelty/*", "*.zip",
                    ".git/*", "submission/*", "submissions/*", "internal/*", "*/internal/*"]
SUSPECT_TOKENS = {"review", "reviews", "referee", "referees", "rebuttal", "response", "responses", "reply",
                  "handoff", "progress", "todo", "note", "notes", "memo", "memos", "internal", "draft", "drafts",
                  "coverletter", "letter", "email", "emails", "outreach", "plan", "plans", "comment", "comments"}


def suspect_name(rel: str) -> bool:
    toks = set(re.split(r"[^a-z0-9]+", os.path.basename(rel).lower()))
    return bool(toks & SUSPECT_TOKENS)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(repo: str, *args: str) -> str | None:
    try:
        return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def list_files(repo: str, include_untracked: list[str]) -> tuple[list[str], bool, list[str]]:
    tracked = git(repo, "ls-files", "-z")
    if tracked is not None:
        files = [f for f in tracked.split("\0") if f]
        untracked_all = [f for f in (git(repo, "ls-files", "-z", "--others", "--exclude-standard") or "").split("\0") if f]
        extra = [f for f in untracked_all if any(fnmatch.fnmatch(f, g) for g in include_untracked)]
        left_out = [f for f in untracked_all if f not in extra]
        return files + extra, True, left_out
    out = []
    for root, dirs, fs in os.walk(repo):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in fs:
            out.append(os.path.relpath(os.path.join(root, f), repo))
    return out, False, []


def find_manuscripts(repo: str) -> list[str]:
    out = []
    for f in sorted(os.listdir(repo)):
        if f.lower().endswith((".docx", ".odt", ".pdf")) and not f.startswith("~$"):
            out.append(f)
            continue
        if f.lower().endswith(".md") and re.search(r"manuscript|paper|main|draft|article", f, re.I):
            out.append(f)
            continue
        if f.endswith(".tex"):
            try:
                with open(os.path.join(repo, f), encoding="utf-8", errors="replace") as fh:
                    if re.search(r"\\begin\{document\}", fh.read()):
                        out.append(f)
            except OSError:
                pass
    return out


def cmd_pack(args):
    repo = os.path.abspath(args.repo)
    out = os.path.abspath(args.out)
    if os.path.exists(out) and os.listdir(out):
        sys.exit(f"{out} exists and is not empty; choose a new directory")
    if out.startswith(repo + os.sep):
        sys.exit("--out must be outside the repo (reviewers must not see it through the repo, and vice versa)")
    pack = os.path.join(out, "pack")
    os.makedirs(pack)
    files, is_git, untracked_left_out = list_files(repo, args.include_untracked)
    excludes = DEFAULT_EXCLUDES + args.exclude
    copied, omitted_size, excluded, suspects = [], [], [], []
    for rel in files:
        src = os.path.join(repo, rel)
        if not os.path.isfile(src):
            continue
        if any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(os.path.basename(rel), g) for g in excludes):
            excluded.append(rel)
            continue
        size = os.path.getsize(src)
        if size > args.max_mb * 1e6:
            omitted_size.append(f"{rel} ({size / 1e6:.1f} MB)")
            continue
        if suspect_name(rel) and not rel.endswith((".py", ".json", ".csv", ".tex", ".bib")):
            suspects.append(rel)
        dst = os.path.join(pack, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)
    manuscripts = args.manuscript or find_manuscripts(repo)
    hashes = {}
    for m in manuscripts:
        p = os.path.join(repo, m)
        if os.path.isfile(p):
            hashes[m] = sha256(p)
    head = (git(repo, "rev-parse", "HEAD") or "").strip() if is_git else ""
    dirty = bool((git(repo, "status", "--porcelain", "--untracked-files=no") or "").strip()) if is_git else None
    pin = {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "repo": repo, "git": is_git, "head": head, "tracked_changes_uncommitted": dirty,
        "manuscript_sha256": hashes, "files_copied": len(copied),
        "excluded": excluded, "omitted_size": omitted_size, "untracked_left_out": untracked_left_out,
        "suspect_names_copied": suspects,
        "exclude_patterns": excludes,
    }
    with open(os.path.join(out, "PIN.json"), "w", encoding="utf-8") as fh:
        json.dump(pin, fh, indent=1, ensure_ascii=False)
    roles = [r.strip() for r in (args.roles or "").split(",") if r.strip()]
    for r in roles:
        shutil.copytree(pack, os.path.join(out, f"work-{r}"), symlinks=True)
    os.makedirs(os.path.join(out, "reports"), exist_ok=True)
    lines = [
        "# Review pack", "",
        f"- created (UTC): {pin['created_utc']}",
        f"- source repo: `{repo}`",
        f"- git HEAD: `{head or 'n/a'}`" + (" (tracked files have uncommitted changes; the pack contains the working-tree "
                                              "version)" if dirty else ""),
        f"- files copied: {len(copied)}; excluded by pattern: {len(excluded)}; omitted for size: {len(omitted_size)}; "
        f"untracked files left out: {len(untracked_left_out)}", "",
        "## Manuscript version (line numbers in reviews refer to these files)", "",
        "| file | SHA-256 |", "|---|---|"] + [f"| {k} | `{v}` |" for k, v in hashes.items()] + [
        "", "## Copied files whose names look like author notes (check; re-pack with --exclude if private)", ""] + \
        [f"- {x}" for x in suspects] + [
        "", "## Rules for reviewers", "",
        f"- Read from `{pack}` only. Do not open the source repo or any path outside this review directory.",
        "- Run code only in your own work copy" + (f" (`{out}/work-<role>/`)." if roles else
                                                    f": `cp -R {pack} /tmp/<your-role>-work` first."),
        f"- Write your report to `{out}/reports/<role>.md`.",
        "- List every file you read and every command you ran in the report's verification section.", "",
        "## Omitted for size", ""] + [f"- {x}" for x in omitted_size] + ["", "## Excluded by pattern", ""] + \
        [f"- {x}" for x in excluded[:200]] + ["", "## Untracked files left out (author notes, drafts, earlier reviews)", ""] + \
        [f"- {x}" for x in untracked_left_out[:200]]
    with open(os.path.join(out, "MANIFEST.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"pack: {len(copied)} files -> {pack}; excluded {len(excluded)}, omitted {len(omitted_size)}, "
          f"untracked left out {len(untracked_left_out)}; manuscripts pinned: {', '.join(hashes) or 'none'}"
          + (f"; CHECK {len(suspects)} copied files with note-like names (see MANIFEST)" if suspects else "")
          + (f"; work copies: {', '.join(roles)}" if roles else ""))


def cmd_check_pin(args):
    pin = json.load(open(args.pin, encoding="utf-8"))
    repo = os.path.abspath(args.repo or pin["repo"])
    ok = True
    for rel, h in pin["manuscript_sha256"].items():
        p = os.path.join(repo, rel)
        now = sha256(p) if os.path.isfile(p) else None
        same = now == h
        ok &= same
        print(f"{'same   ' if same else 'CHANGED'} {rel}")
    print("line numbers in the reviews still apply" if ok else
          "manuscript changed since the review: re-locate each issue before acting on its line numbers")
    sys.exit(0 if ok else 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack")
    p.add_argument("--repo", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--manuscript", nargs="*", default=[])
    p.add_argument("--roles")
    p.add_argument("--exclude", nargs="*", default=[])
    p.add_argument("--include-untracked", nargs="*", default=[])
    p.add_argument("--max-mb", type=float, default=20)
    p.set_defaults(func=cmd_pack)
    c = sub.add_parser("check-pin")
    c.add_argument("pin")
    c.add_argument("--repo")
    c.set_defaults(func=cmd_check_pin)
    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
