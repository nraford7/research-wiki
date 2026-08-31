#!/usr/bin/env python3
"""
batch_ingest.py — planner/tracker for batch ingesting a directory of research
products into the research-wiki.

WHY THIS IS A PLANNER, NOT AN INGESTER: `ingest` and `analyze` are LLM
procedures (they read source prose and author cross-linked wiki pages) — they
cannot be done in pure Python. This script does the *deterministic* part: it
enumerates the source dirs under a target directory, decides which are already
ingested (content-hash idempotency, byte-for-byte compatible with
references/ingest.md Step 1), and emits the next action so the agent can drive
the loop:

    ingest 1 source  ->  after every N ingests, delta-analyze  ->  repeat until
    nothing left  ->  one final `analyze --full` (enrich + atlas + search).

The whole state machine is derived from `wiki/log.md` + the filesystem, so it is
fully RESUMABLE: re-run `--next` in any session and it computes the correct next
step. No hidden state.

USAGE
    python3 batch_ingest.py <research-dir> [--plan | --next | --json]
                            [--every N] [--wiki PATH]

    --plan   (default) human-readable full plan + per-source status table
    --next   print ONLY the next action, one line, for the drive loop:
                 INGEST <abs-dir>
                 INGEST --force <abs-dir>
                 ANALYZE_DELTA
                 ANALYZE_FULL
                 DONE
    --json   machine-readable plan (all sources + statuses + next action)
    --every  delta-analyze cadence (default 3)
    --wiki   wiki path (default /Users/noahraford/magic/wiki)

STATUSES
    not-ingested     no matching ingest line in the log
    ingested-current a log line matches the CURRENT content hash -> skip
    changed          ingested before, but content hash differs now -> re-ingest --force
    not-a-source     fails the Step-0 qualification tests -> skip
    locked           a live deeper-research lease names it -> skip + warn
"""
import argparse
import hashlib
import os
import re
import sys

DEFAULT_WIKI = "/Users/noahraford/magic/wiki"
EMPTY_SHA12 = "e3b0c44298fc"  # sha256 of empty input -> zero content files

SLUG_RE = re.compile(r"ch\d+-q\d+", re.IGNORECASE)
TIMESTAMP_SUFFIX_RE = re.compile(r"-\d{8}t\d+z$", re.IGNORECASE)


def find_md(dirpath, exclude_names=()):
    """Non-recursive *.md in dirpath, sorted, excluding given basenames."""
    if not os.path.isdir(dirpath):
        return []
    out = []
    for n in os.listdir(dirpath):
        if not n.endswith(".md"):
            continue
        if n in exclude_names:
            continue
        out.append(os.path.join(dirpath, n))
    return sorted(out)


def qualifies(d):
    """Replicate references/ingest.md Step 0. Returns (ok, reason)."""
    name = os.path.basename(d.rstrip("/"))
    if not SLUG_RE.search(name):
        return False, "name-not-chN-qN"
    if "superseded" in name.lower():
        return False, "superseded"
    if TIMESTAMP_SUFFIX_RE.search(name):
        return False, "timestamped-variant"
    sections = os.path.join(d, "Sections")
    # (a) Sections/ with >= 3 md
    if len(find_md(sections)) >= 3:
        return True, "sections"
    # (b) a root *source*.md (case-insensitive)
    roots = find_md(d)
    if any("source" in os.path.basename(p).lower() for p in roots):
        return True, "source-monolith"
    # (c) exactly one root .md and it is >= 50KB
    if len(roots) == 1 and os.path.getsize(roots[0]) >= 50 * 1024:
        return True, "single-root-monolith"
    return False, "no-content-test-passed"


def content_hash(d):
    """Byte-for-byte compatible with references/ingest.md Step 1.

    CONTENT = Sections/*.md (excl bibliography.md, dedup-decisions.md) if >=3,
              else root *source*.md, else all root *.md.  (each sorted)
    SOURCES = Sources/{claims.jsonl,bibliography.md,bibliography.bib} (sorted)
    hash = sha256( concat(CONTENT_sorted + SOURCES_sorted) )[:12]
    """
    sections = os.path.join(d, "Sections")
    if len(find_md(sections)) >= 3:
        content = find_md(sections, exclude_names={"bibliography.md", "dedup-decisions.md"})
    else:
        content = [p for p in find_md(d) if "source" in os.path.basename(p).lower()]
        if not content:
            content = find_md(d)
    src_dir = os.path.join(d, "Sources")
    sources = []
    for base in ("bibliography.bib", "bibliography.md", "claims.jsonl"):
        p = os.path.join(src_dir, base)
        if os.path.isfile(p):
            sources.append(p)
    sources = sorted(sources)
    h = hashlib.sha256()
    for p in content + sources:
        try:
            with open(p, "rb") as fh:
                h.update(fh.read())
        except OSError:
            pass
    return h.hexdigest()[:12]


def is_locked(d):
    """A live deeper-research lease naming this slug lives in the chapter dir's
    .locks/leases/*/holders.json. Scan only that small tree (never .transactions)."""
    slug = os.path.basename(d.rstrip("/"))
    chapter_dir = os.path.dirname(d.rstrip("/"))
    leases = os.path.join(chapter_dir, ".locks", "leases")
    if not os.path.isdir(leases):
        return False
    for root, _dirs, files in os.walk(leases):
        for f in files:
            if f != "holders.json":
                continue
            try:
                with open(os.path.join(root, f), "r", errors="ignore") as fh:
                    if slug in fh.read():
                        return True
            except OSError:
                pass
    return False


def enumerate_sources(research_dir):
    """chN-qN-* dirs at depth 1 or 2 under research_dir, sorted by slug."""
    found = {}
    research_dir = os.path.abspath(research_dir)
    for root, dirs, _files in os.walk(research_dir):
        depth = root[len(research_dir):].count(os.sep)
        if depth >= 2:
            dirs[:] = []  # don't descend past chapter/source level
            continue
        for dname in dirs:
            if SLUG_RE.search(dname):
                p = os.path.join(root, dname)
                found[os.path.basename(p)] = p
    # dedup by slug (basename); sort by slug for stable q-order
    return [found[k] for k in sorted(found)]


def parse_log(wiki):
    """Return (records, lines) where records is an ordered list of dicts:
    {kind: 'ingest'|'analyze', slug, hash, scope}."""
    logpath = os.path.join(wiki, "log.md")
    records = []
    if not os.path.isfile(logpath):
        return records
    with open(logpath, "r", errors="ignore") as fh:
        for line in fh:
            parts = [p.strip() for p in line.rstrip("\n").split(" | ")]
            if len(parts) < 3:
                continue
            kind = parts[1]
            if kind == "ingest":
                slug = parts[2]
                h = ""
                if len(parts) >= 4 and parts[3].startswith("sha256:"):
                    h = parts[3][len("sha256:"):].strip()
                records.append({"kind": "ingest", "slug": slug, "hash": h})
            elif kind == "analyze":
                scope = ""
                if len(parts) >= 3 and parts[2].startswith("scope:"):
                    scope = parts[2][len("scope:"):].strip()
                records.append({"kind": "analyze", "scope": scope})
    return records


def ingested_hashes(records):
    """slug -> set of hashes ever ingested for it."""
    out = {}
    for r in records:
        if r["kind"] == "ingest":
            out.setdefault(r["slug"], set()).add(r["hash"])
    return out


def ingests_since_last_analyze(records):
    last_analyze_idx = -1
    for i, r in enumerate(records):
        if r["kind"] == "analyze":
            last_analyze_idx = i
    return sum(1 for r in records[last_analyze_idx + 1:] if r["kind"] == "ingest")


def full_analyze_is_current(records):
    """True iff a scope:full analyze is the most recent event after the last ingest."""
    last_ingest_idx = -1
    last_full_idx = -1
    for i, r in enumerate(records):
        if r["kind"] == "ingest":
            last_ingest_idx = i
        elif r["kind"] == "analyze" and r["scope"] == "full":
            last_full_idx = i
    return last_full_idx > last_ingest_idx and last_full_idx != -1


def classify(sources, wiki):
    records = parse_log(wiki)
    prior = ingested_hashes(records)
    rows = []
    for d in sources:
        slug = os.path.basename(d.rstrip("/"))
        ok, reason = qualifies(d)
        if not ok:
            rows.append({"slug": slug, "dir": d, "status": "not-a-source", "detail": reason})
            continue
        if is_locked(d):
            rows.append({"slug": slug, "dir": d, "status": "locked", "detail": "live lease"})
            continue
        h = content_hash(d)
        if h == EMPTY_SHA12:
            rows.append({"slug": slug, "dir": d, "status": "not-a-source", "detail": "empty-content"})
            continue
        seen = prior.get(slug, set())
        if not seen:
            rows.append({"slug": slug, "dir": d, "status": "not-ingested", "detail": h})
        elif h in seen:
            rows.append({"slug": slug, "dir": d, "status": "ingested-current", "detail": h})
        else:
            rows.append({"slug": slug, "dir": d, "status": "changed", "detail": h})
    return rows, records


def next_action(rows, records, every):
    """Pure state machine over current filesystem + log."""
    todo = [r for r in rows if r["status"] in ("not-ingested", "changed")]
    if todo:
        if ingests_since_last_analyze(records) >= every:
            return ("ANALYZE_DELTA", None)
        nxt = todo[0]
        force = nxt["status"] == "changed"
        return ("INGEST", {"dir": nxt["dir"], "force": force})
    # nothing left to ingest
    if full_analyze_is_current(records):
        return ("DONE", None)
    return ("ANALYZE_FULL", None)


def cmd_next(rows, records, every):
    action, payload = next_action(rows, records, every)
    if action == "INGEST":
        prefix = "INGEST --force " if payload["force"] else "INGEST "
        print(prefix + payload["dir"])
    else:
        print(action)


def cmd_plan(rows, records, every, research_dir, wiki):
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"# batch-ingest plan")
    print(f"research-dir : {os.path.abspath(research_dir)}")
    print(f"wiki         : {wiki}")
    print(f"cadence      : delta-analyze every {every} ingests; full-analyze at end")
    print(f"sources found: {len(rows)}")
    for k in ("not-ingested", "changed", "ingested-current", "not-a-source", "locked"):
        if counts.get(k):
            print(f"  {k:16s}: {counts[k]}")
    print()
    print(f"{'STATUS':16s}  SLUG")
    print(f"{'-'*16}  {'-'*40}")
    for r in rows:
        print(f"{r['status']:16s}  {r['slug']}")
    print()
    todo = [r for r in rows if r["status"] in ("not-ingested", "changed")]
    if todo:
        print(f"To process ({len(todo)}), in order, with delta-analyze after every {every}:")
        for i, r in enumerate(todo, 1):
            mark = r["status"] == "changed" and " (--force)" or ""
            print(f"  {i:2d}. ingest {r['slug']}{mark}")
            if i % every == 0 and i != len(todo):
                print(f"      -> delta analyze")
        print(f"  -> then: analyze --full   (enrich + graphify + atlas + search)")
    else:
        if full_analyze_is_current(records):
            print("Nothing to do — everything ingested and a full analyze is current. DONE.")
        else:
            print("All sources ingested; a final `analyze --full` is still needed.")
    print()
    action, payload = next_action(rows, records, every)
    if action == "INGEST":
        print(f"NEXT: ingest{' --force' if payload['force'] else ''} {payload['dir']}")
    else:
        print(f"NEXT: {action}")


def cmd_json(rows, records, every):
    import json
    action, payload = next_action(rows, records, every)
    out = {
        "sources": [{"slug": r["slug"], "status": r["status"], "dir": r["dir"], "detail": r["detail"]} for r in rows],
        "every": every,
        "next": {"action": action, "payload": payload},
    }
    print(json.dumps(out, indent=2))


def main():
    ap = argparse.ArgumentParser(description="Planner/tracker for batch wiki ingest.")
    ap.add_argument("research_dir", help="directory of research products (chN-qN-* subdirs)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="full human-readable plan (default)")
    mode.add_argument("--next", action="store_true", help="print only the next action")
    mode.add_argument("--json", action="store_true", help="machine-readable plan")
    ap.add_argument("--every", type=int, default=3, help="delta-analyze cadence (default 3)")
    ap.add_argument("--wiki", default=DEFAULT_WIKI, help="wiki path")
    args = ap.parse_args()

    if not os.path.isdir(args.research_dir):
        print(f"error: not a directory: {args.research_dir}", file=sys.stderr)
        sys.exit(2)

    sources = enumerate_sources(args.research_dir)
    if not sources:
        print(f"error: no chN-qN-* source dirs found under {args.research_dir}", file=sys.stderr)
        sys.exit(2)

    rows, records = classify(sources, args.wiki)

    if args.next:
        cmd_next(rows, records, args.every)
    elif args.json:
        cmd_json(rows, records, args.every)
    else:
        cmd_plan(rows, records, args.every, args.research_dir, args.wiki)


if __name__ == "__main__":
    main()
