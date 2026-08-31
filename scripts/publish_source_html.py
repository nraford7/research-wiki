#!/usr/bin/env python3
"""
publish_source_html.py — copy a source's readable HTML into the wiki, scrubbed.

The wiki's readable layer is `wiki/literature-html/<slug>.html` (what the atlas
"Read full document" link opens, and what extract_sources.py turns into the
searchable `.literature-text/` RAG corpus). Ingest builds the wiki PAGES from the
source TEXT but does NOT populate this layer — this script does, and it scrubs two
known deeper-research export defects so they never reach the wiki:

  1. the `Research Bible` kicker stamp  -> `Research Report`  (terminology guard;
     the word "bible" is banned in this project — see magic/CLAUDE.md)
  2. the leaked `<section id="...shared-brief-for-all-section-subagents...">` block
     (the pipeline's internal per-section briefing, mis-rendered as content) and its
     stray table-of-contents `<li><a href="#...shared-brief...">` anchor.

It refuses to write if the word "bible" survives the scrub (fail loud, never publish
the banned term).

USAGE
    python3 publish_source_html.py --source-dir "<chN-qN dir>" [--wiki <wiki>]
    python3 publish_source_html.py --all <parent-dir> [--wiki <wiki>]   # every chN-qN under parent
"""
import argparse
import glob
import os
import re
import sys

DEFAULT_WIKI = "/Users/noahraford/magic/wiki"
BRIEF_SECTION = re.compile(
    r'<section class="research-section" id="section-shared-brief-for-all-section-subagents[^>]*>.*?</section>',
    re.S)
BRIEF_TOC = re.compile(
    r'<li><a href="#section-shared-brief-for-all-section-subagents[^"]*">.*?</a></li>', re.S)


def scrub(html):
    html = html.replace("Research Bible", "Research Report")
    html = BRIEF_SECTION.sub("", html)
    html = BRIEF_TOC.sub("", html)
    return html


def publish_one(source_dir, wiki):
    slug = os.path.basename(source_dir.rstrip("/"))
    src = os.path.join(source_dir, f"RESEARCH-REPORT_{slug}.html")
    if not os.path.isfile(src):
        cands = glob.glob(os.path.join(source_dir, "*.html"))
        if len(cands) != 1:
            return (slug, "no-single-html")
        src = cands[0]
    with open(src, encoding="utf-8") as fh:
        html = scrub(fh.read())
    if re.search(r"bible", html, re.I):
        return (slug, "REFUSED-bible-survived")  # never publish the banned term
    out = os.path.join(wiki, "literature-html", f"{slug}.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    return (slug, "published")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--source-dir", help="a single chN-qN source dir")
    g.add_argument("--all", metavar="PARENT", help="publish every chN-qN dir under PARENT")
    ap.add_argument("--wiki", default=DEFAULT_WIKI)
    a = ap.parse_args()

    if a.source_dir:
        dirs = [a.source_dir]
    else:
        dirs = sorted(d for d in glob.glob(os.path.join(a.all, "**", "ch*-q*"), recursive=True)
                      if os.path.isdir(d))
    rc = 0
    for d in dirs:
        slug, status = publish_one(d, a.wiki)
        print(f"[publish] {slug}: {status}")
        if status.startswith("REFUSED") or status == "no-single-html":
            rc = 1
    sys.exit(rc)


if __name__ == "__main__":
    main()
