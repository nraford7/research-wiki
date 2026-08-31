#!/usr/bin/env python3
"""
enrich_splice.py — single-writer splice of v2 narrative leads into concept/thinker pages.

The enrichment pass drafts a standalone narrative lead per page (via parallel READ-ONLY
drafting agents, orchestrated by the MAIN agent — subagents can't fan out). Those agents
return {page: lead_markdown}. This script performs the WRITE half, single-writer:

  - replaces the text between the `# Title` line and the first `## ` heading with the new
    lead (keeps the `## In <source>` and `## See also` sections intact below),
  - sets `overview: true` in frontmatter (build_wiki_html then drops the raw `## In`
    scaffolding from the atlas reader view),
  - bumps `updated:`.

It SKIPS pages that already have `overview: true` (idempotent; never clobbers a good lead)
unless --force. Pages it can't find or splice are reported and left untouched.

USAGE
    python3 enrich_splice.py --wiki /Users/noahraford/magic/wiki --input drafts.json [--date YYYY-MM-DD] [--force]

drafts.json: {"concepts/foo": "lead markdown...", "thinkers/bar.md": "...", ...}
Keys may be "type/slug", "type/slug.md", or a path relative to the wiki.
"""
import argparse
import datetime
import json
import os
import re
import sys

H2 = re.compile(r'^##\s', re.M)


def resolve_path(wiki, key):
    k = key.strip()
    if not k.endswith(".md"):
        k += ".md"
    p = os.path.join(wiki, k)
    return p if os.path.isfile(p) else None


def splice_one(path, lead, date_str, force):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r'^(---\n.*?\n---\n)(.*)$', text, re.S)
    if not m:
        return "no-frontmatter"
    fm, body = m.group(1), m.group(2)
    if re.search(r'^overview:\s*true\s*$', fm, re.M) and not force:
        return "already-enriched"

    # frontmatter: set overview: true (insert before closing ---), bump updated
    if re.search(r'^overview:\s*', fm, re.M):
        fm = re.sub(r'^overview:\s*.*$', 'overview: true', fm, count=1, flags=re.M)
    else:
        fm = fm[:-4] + 'overview: true\n' + fm[-4:]  # before the closing '---\n'
    if re.search(r'^updated:\s*', fm, re.M):
        fm = re.sub(r'^updated:\s*.*$', f'updated: {date_str}', fm, count=1, flags=re.M)

    # body: keep the "# Title" line, replace lead up to the first "## "
    tm = re.search(r'^#\s+.+$', body, re.M)
    if not tm:
        return "no-title"
    title_end = tm.end()
    h2 = H2.search(body, title_end)
    tail = body[h2.start():] if h2 else ""
    new_body = body[:title_end] + "\n\n" + lead.strip() + "\n\n" + tail
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(fm + new_body)
    return "spliced"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", default="/Users/noahraford/magic/wiki")
    ap.add_argument("--input", required=True, help="JSON {page: lead_markdown}")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--force", action="store_true", help="re-splice even if overview:true")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as fh:
        drafts = json.load(fh)

    counts = {}
    problems = []
    for key, lead in drafts.items():
        path = resolve_path(args.wiki, key)
        if not path:
            counts["not-found"] = counts.get("not-found", 0) + 1
            problems.append(f"not-found: {key}")
            continue
        if not isinstance(lead, str) or not lead.strip():
            counts["empty-lead"] = counts.get("empty-lead", 0) + 1
            problems.append(f"empty-lead: {key}")
            continue
        r = splice_one(path, lead, args.date, args.force)
        counts[r] = counts.get(r, 0) + 1
        if r not in ("spliced", "already-enriched"):
            problems.append(f"{r}: {key}")

    print(f"enrich_splice: {counts}")
    for p in problems:
        print("  " + p, file=sys.stderr)
    # non-zero exit only if nothing spliced and there were inputs
    if drafts and not counts.get("spliced") and not counts.get("already-enriched"):
        sys.exit(1)


if __name__ == "__main__":
    main()
