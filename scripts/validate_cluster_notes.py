#!/usr/bin/env python3
"""
validate_cluster_notes.py — HARD GATE for wiki/clusters/*.md before the atlas build.

Cluster notes are the atlas's front-door prose. They regress in three ways that the
legend==heading check does NOT catch, so this validates them directly and exits
non-zero on any failure (run it in analyze.md `--full` before build_wiki_html.py):

  1. PIPE links `[[type/slug|alias]]` — the atlas WIKILINK regex is `[[type/slug]]`
     only, so piped links render as raw dead text.
  2. DEAD links — `[[type/slug]]` whose page does not exist (renders as a
     wikilink-missing span).
  3. DOUBLING — `Name ([[thinkers/slug]])`, which renders "Name (Name)".
  Plus: too-thin notes (word count) and notes that do not link enough of their own
  community's members to bind correctly (the atlas attaches a note to the community
  its links most overlap).

USAGE
    python3 validate_cluster_notes.py [--wiki <wiki>] [--min-words 600] [--min-own 5]
    exit 0 = all clean; exit 1 = one or more problems (printed).
"""
import argparse, glob, importlib.util, os, re, sys

LINK = re.compile(r"\[\[([^\]]+)\]\]")
PIPE = re.compile(r"\[\[[^\]]*\|")
DOUBLE = re.compile(r"[A-Za-z][A-Za-z.,'\- ]{0,70}\(\[\[[a-z]+/[^\]]+\]\]\)")
FM_COMMUNITY = re.compile(r"^community:\s*(\d+)\s*$", re.M)

def _load_bw(skill_dir):
    p = os.path.join(skill_dir, "build_wiki_html.py")
    spec = importlib.util.spec_from_file_location("bw", p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", default="/Users/noahraford/magic/wiki")
    ap.add_argument("--min-words", type=int, default=600)
    ap.add_argument("--min-own", type=int, default=5)
    a = ap.parse_args()
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bw = _load_bw(skill_dir)
    pages = bw.load_pages(a.wiki, {})
    graph = bw.load_graph(os.path.join(a.wiki, "graphify-out", "graph.json"), pages, lambda *x: None)
    members, _ = bw._cluster_structure(graph)
    mk = {cid: {m["key"] for m in ms} for cid, ms in members.items()}
    existing = set(pages)
    problems = 0
    files = sorted(glob.glob(os.path.join(a.wiki, "clusters", "*.md")))  # non-recursive: skips _stale/
    for f in files:
        raw = open(f, encoding="utf-8").read()
        body = re.sub(r"^---\n.*?\n---\n", "", raw, count=1, flags=re.S)
        body = re.sub(r"^#\s+.+$", "", body, count=1, flags=re.M)
        wc = len(body.split())
        links = [k.strip() for k in LINK.findall(body)]
        dead = sorted({k for k in links if k not in existing})
        pipes = PIPE.findall(body)
        doubles = DOUBLE.findall(body)
        cm = FM_COMMUNITY.search(raw)
        cid = int(cm.group(1)) if cm else None
        own = sum(1 for k in links if cid is not None and k in mk.get(cid, set()))
        ov = {c: sum(1 for k in links if k in m) for c, m in mk.items()}
        best = max(ov, key=ov.get) if ov else None
        fl = []
        if wc < a.min_words: fl.append(f"SHORT({wc})")
        if pipes: fl.append(f"PIPE({len(pipes)})")
        if dead: fl.append(f"DEAD={dead}")
        if doubles: fl.append(f"DOUBLING({len(doubles)})")
        if cid is not None and own < a.min_own: fl.append(f"OWN-MEMBER-LINKS({own})")
        if cid is not None and best is not None and best != cid:
            fl.append(f"BINDS-TO-{best}-NOT-{cid}")
        if fl:
            problems += 1
            print(f"FAIL {os.path.basename(f)}: " + " ".join(fl))
    if problems:
        print(f"\n{problems} cluster note(s) FAILED validation.")
        sys.exit(1)
    print(f"OK — {len(files)} cluster notes valid (words>= {a.min_words}, links resolve, no pipes/doubling, correct binding).")

if __name__ == "__main__":
    main()
