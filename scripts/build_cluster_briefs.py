#!/usr/bin/env python3
"""
build_cluster_briefs.py — emit one drafting brief per current graphify community.

The cluster-narrative refresh (analyze.md `--full`) fans out one drafting agent per
community. Each agent must link ONLY real member pages in the atlas-native
`[[type/slug]]` form — so this script hands it the exact valid link targets, removing
any chance of invented/dead slugs or Obsidian pipe-aliases (which the atlas cannot
render). Reproducible: derived entirely from graph.json + GRAPH_REPORT.md + the pages.

USAGE
    python3 build_cluster_briefs.py [--wiki <wiki>] [--out /tmp/cluster_briefs] [--top 25]

Writes <out>/<NN>.md, one per community, containing the label, the top-degree member
pages (exact keys), and the full debate/theme key list the agent may also link.
"""
import argparse, importlib.util, os

def _load_bw(wiki_skill_dir):
    p = os.path.join(wiki_skill_dir, "build_wiki_html.py")
    spec = importlib.util.spec_from_file_location("bw", p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", default="/Users/noahraford/magic/wiki")
    ap.add_argument("--out", default="/tmp/cluster_briefs")
    ap.add_argument("--top", type=int, default=25)
    a = ap.parse_args()
    bw = _load_bw(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pages = bw.load_pages(a.wiki, {})
    graph = bw.load_graph(os.path.join(a.wiki, "graphify-out", "graph.json"), pages, lambda *x: None)
    labels = bw.read_community_labels(os.path.join(a.wiki, "graphify-out"))
    members, related = bw._cluster_structure(graph)
    dt = sorted((k, pages[k]["title"]) for k in pages if pages[k]["type"] in ("debate", "theme"))
    dt_block = "\n".join(f"- [[{k}]] — {t}" for k, t in dt)
    os.makedirs(a.out, exist_ok=True)
    for cid in sorted(members):
        lab = labels.get(cid, f"Community {cid}")
        mem = members[cid][:a.top]
        mem_block = "\n".join(f'- [[{m["key"]}]] — {m["label"]}' for m in mem)
        rel = ", ".join(labels.get(rc, f"Community {rc}") for rc in related.get(cid, []))
        brief = (f"CLUSTER: {lab}\n(community {cid}; {len(members[cid])} member pages; "
                 f"related: {rel or 'none'})\n\n"
                 f"MEMBER PAGES — link these (EXACT keys, plain [[key]] form, NO pipes):\n{mem_block}\n\n"
                 f"DEBATES & THEMES you may also link (exact keys, same rule):\n{dt_block}\n")
        open(os.path.join(a.out, f"{cid:02d}.md"), "w", encoding="utf-8").write(brief)
    print(f"wrote {len(members)} briefs to {a.out}")

if __name__ == "__main__":
    main()
