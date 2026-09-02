#!/usr/bin/env python3
"""Match each enriched concept to the most relevant SECTION of every source it
cites, and record the pointers as `sources: {source: anchor}` frontmatter.

Uses the literature-corpus semantic index to find the closest section, resolves the
hit to its nearest anchored heading, and writes the anchor back to the page.
See docs/superpowers/specs/2026-08-30-bible-deep-linking-design.md.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

WIKI_DEFAULT = "/Users/noahraford/magic/wiki"
SEARCH_DEFAULT = os.path.expanduser("~/.claude/skills/semantic-search/search.py")


def nearest_anchor(md_text, line, anchors_b):
    """Scan UP from `line` for the nearest ##/###/#### heading that has a
    non-null anchor. Well-anchored sources fall back to their h2 when the h3 is
    unanchored; re-sectioned coarse sources resolve to the finer h3."""
    by_heading = {e["heading"]: e.get("anchor") for e in anchors_b}
    lines = md_text.splitlines()
    for i in range(min(line, len(lines)) - 1, -1, -1):
        m = re.match(r"^#{2,4}\s+(.+)$", lines[i])
        if m:
            h = m.group(1).strip()
            if by_heading.get(h):
                return h, by_heading[h]
    return None, None


def _query(source, q, corpus, search):
    proc = subprocess.run(
        [sys.executable, "-B", search, "--cwd", corpus, "--in", f"{source}.md",
         "--json", q, "--top", "5"],
        capture_output=True, text=True)
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "no output"
        raise RuntimeError(f"semantic-search helper failed (exit {proc.returncode}) "
                           f"querying {source}: {detail}")
    hits = [json.loads(l) for l in proc.stdout.splitlines() if l.strip().startswith("{")]
    return hits[0] if hits else None


def match_page(page_path, anchors, corpus, search):
    raw = open(page_path, encoding="utf-8").read()
    fm = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not fm:
        return {}
    front, body = fm.group(1), fm.group(2)
    bm = re.search(r"literature:\s*\[(.*?)\]", front, re.S)
    literature = re.findall(r"[A-Za-z0-9][\w-]+", bm.group(1)) if bm else []
    tm = re.search(r"^title:\s*(.+)$", front, re.M)
    title = tm.group(1).strip() if tm else ""
    query = (title + " " + re.sub(r"\s+", " ", re.sub(r"^#.*$", "", body, flags=re.M))).strip()[:600]
    src = {}
    for b in literature:
        hit = _query(b, query, corpus, search)
        if not hit:
            print(f"  [match] {os.path.basename(page_path)}: no corpus hit for {b} (→ whole-source fallback)")
            continue
        md = open(os.path.join(corpus, f"{b}.md"), encoding="utf-8").read()
        _, anc = nearest_anchor(md, int(hit.get("line", 1)), anchors.get(b, []))
        if anc:
            src[b] = anc
        else:
            print(f"  [match] {os.path.basename(page_path)}: hit for {b} had no anchored heading (→ whole-source fallback)")
    return src


def write_sources(page_path, sources):
    raw = open(page_path, encoding="utf-8").read()
    fm = re.match(r"^(---\n)(.*?)(\n---\n)(.*)$", raw, re.S)
    if not fm:
        return
    front = fm.group(2)
    inline = "{" + ", ".join(f"{b}: {a}" for b, a in sources.items()) + "}"
    line = f"sources: {inline}"
    if re.search(r"^sources:.*$", front, re.M):
        front = re.sub(r"^sources:.*$", line, front, flags=re.M)
    else:
        front = front + "\n" + line
    open(page_path, "w", encoding="utf-8").write(fm.group(1) + front + fm.group(3) + fm.group(4))


def _targets(only, wiki):
    pages = []
    for d in ("concepts", "thinkers"):
        for p in sorted(glob.glob(os.path.join(wiki, d, "*.md"))):
            txt = open(p, encoding="utf-8").read()
            if only:
                if os.path.basename(p)[:-3] in only:
                    pages.append(p)
            elif re.search(r"^overview:\s*true\s*$", txt, re.M):
                pages.append(p)
    return pages


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write concept→source-section pointers.")
    ap.add_argument("--only", nargs="*", help="specific slugs (default: all overview:true pages)")
    ap.add_argument("--wiki", default=WIKI_DEFAULT,
                    help="wiki root; the corpus is <wiki>/.literature-text")
    ap.add_argument("--search", default=SEARCH_DEFAULT,
                    help="path to the semantic-search helper (search.py)")
    a = ap.parse_args(argv)
    corpus = os.path.join(a.wiki, ".literature-text")
    if not os.path.isfile(a.search):
        print(f"[match] error: semantic-search helper not found at {a.search} "
              f"(pass --search); nothing matched", file=sys.stderr)
        return 1
    anchors_path = os.path.join(corpus, "anchors.json")
    if not os.path.isfile(anchors_path):
        print(f"[match] error: {anchors_path} not found; run extract_sources.py "
              f"--html-dir {os.path.join(a.wiki, 'literature-html')} --out {corpus} "
              f"--resection first", file=sys.stderr)
        return 1
    anchors = json.load(open(anchors_path, encoding="utf-8"))
    pages = _targets(set(a.only) if a.only else None, a.wiki)
    for p in pages:
        try:
            src = match_page(p, anchors, corpus, a.search)
        except RuntimeError as e:
            print(f"[match] error: {e}", file=sys.stderr)
            return 1
        if src:
            write_sources(p, src)
        print(f"[match] {os.path.basename(p)}: {len(src)} deep-link(s) {src or ''}")
    print(f"[match] processed {len(pages)} page(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
