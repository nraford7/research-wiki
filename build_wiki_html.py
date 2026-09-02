#!/usr/bin/env python3
"""Build the wiki atlas: one self-contained, styled wiki.html from the
research wiki (markdown pages) + graphify graph.json.

A reading pane (styled) + an interactive, collapsible, community-colored
SVG graph navigator with metadata nodes/edges excluded. See
docs/superpowers/specs/2026-08-30-wiki-atlas-html-design.md.
"""
import argparse
import glob
import html as _html
import json
import os
import re
import sys
from collections import Counter

import markdown

WIKI_DEFAULT = "/Users/noahraford/magic/wiki"
PAGE_DIRS = ("literature", "concepts", "thinkers", "debates", "themes", "answers")

# ---------------------------------------------------------------- parsing ----

def parse_frontmatter(text):
    """Split leading `---\\n...\\n---\\n` YAML block from body. Prefer PyYAML."""
    m = re.match(r'^---\n(.*?)\n---\n?(.*)$', text, re.S)
    if not m:
        return {}, text
    raw, body = m.group(1), m.group(2)
    try:
        import yaml
        fm = yaml.safe_load(raw) or {}
        if not isinstance(fm, dict):
            fm = {}
    except Exception:
        # best-effort last resort: simple `key: value` only
        fm = {}
        for line in raw.splitlines():
            if ':' in line and not line.startswith(' '):
                k, v = line.split(':', 1)
                fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, body


def resolve_title(fm, body, node_label, slug):
    """title -> name -> question -> first H1 -> graph label -> slug."""
    for k in ('title', 'name', 'question'):
        v = fm.get(k)
        if v:
            return str(v).strip()
    h1 = re.search(r'^#\s+(.+)$', body, re.M)
    if h1:
        return h1.group(1).strip()
    return node_label or slug


def EXCLUDE(sf):
    """True if source_file is a metadata page (never a graph node / nav item)."""
    return sf in ("index.md", "log.md", "about.md") or sf.startswith("reports/")


def load_pages(wiki_dir, node_labels):
    pages = {}
    for d in PAGE_DIRS:
        for p in sorted(glob.glob(os.path.join(wiki_dir, d, "*.md"))):
            base = os.path.basename(p)
            sf = f"{d}/{base}"
            if EXCLUDE(sf):
                continue
            with open(p, encoding="utf-8") as fh:
                fm, body = parse_frontmatter(fh.read())
            if d == "literature":
                # drop the scaffolding "method note" line — sources read as clean
                # research-question landing pages, not lab notes
                body = re.sub(r'(?m)^\*\*Method note:\*\*.*\n?', '', body)
            slug = fm.get("slug") or base[:-3]
            key = f"{d}/{slug}"
            literature = fm.get("literature") or []
            if isinstance(literature, str):
                literature = [b.strip() for b in literature.strip("[]").split(",") if b.strip()]
            pages[key] = {
                "title": resolve_title(fm, body, node_labels.get(key), slug),
                "type": d[:-1] if d.endswith("s") else d,
                "slug": slug,
                "overview": bool(fm.get("overview")),  # has an integrated narrative lead
                "sources": fm.get("sources") or {},    # {source-slug: section-anchor} deep-links
                "file": f"{d}/{base[:-3]}",  # filename stem, for graph node mapping
                "status": fm.get("status", ""),
                "literature": literature,
                "body": body,
            }
    return pages


# ----------------------------------------------------- markdown -> html ------

WIKILINK = re.compile(r'\[\[([a-z]+/[A-Za-z0-9_-]+)(?:\|([^\]]+))?\]\]')  # optional |alias (Obsidian-readable)
CITE = re.compile(
    r'\[([A-Z][^\]\[]*?,\s*\d{4}[a-z]?(?:;[^\]\[]*?\d{4}[a-z]?)*'
    r'(?:,\s*(?:ch\.|p\.|pp\.)[^\]\[]*)?)\]'
)


def md_to_html(body, pages):
    links, missing = [], []

    def wl(m):
        key = m.group(1)
        alias = m.group(2)  # Obsidian [[type/slug|alias]] display text, if given
        links.append(key)
        t = pages.get(key, {}).get("title")
        if t is None:
            missing.append(key)
            return f'<span class="wikilink-missing">{_html.escape(alias or key)}</span>'
        return f'<a class="wikilink" data-page="{key}">{_html.escape(alias or t)}</a>'

    tmp = WIKILINK.sub(wl, body)
    tmp = CITE.sub(lambda m: f'<cite class="cite">[{m.group(1)}]</cite>', tmp)
    out = markdown.markdown(tmp, extensions=["tables", "fenced_code", "sane_lists"])
    return out, links, missing


# ------------------------------------------------------------- graph ---------

def _spring(keep, edges):
    import networkx as nx
    G = nx.Graph()
    G.add_nodes_from(keep)
    G.add_edges_from((e["s"], e["t"]) for e in edges)
    pos = nx.spring_layout(G, seed=42) if G.number_of_nodes() else {}
    deg = dict(G.degree())
    for nid, n in keep.items():
        x, y = pos.get(nid, (0.5, 0.5))
        n["x"] = round(500 + x * 480, 1)
        n["y"] = round(500 + y * 480, 1)
        n["size"] = max(4, deg.get(nid, 0))


def _graph_from_links(pages):
    """Degraded fallback (no graph.json). Runs AFTER md_to_html filled links."""
    keep = {k: {"id": k, "key": k, "label": pages[k]["title"],
                "type": k.split("/")[0], "community": 0} for k in pages}
    edges = [{"s": k, "t": tgt, "relation": "references", "confidence": "EXTRACTED"}
             for k in pages for tgt in pages[k].get("links", []) if tgt in keep]
    _spring(keep, edges)
    return {"nodes": list(keep.values()), "edges": edges,
            "communities": sorted({n["community"] for n in keep.values()})}


def load_graph(graph_path, pages, log=lambda *a: None):
    if not os.path.exists(graph_path):
        log("graph.json absent — building degraded graph from wikilinks only")
        return _graph_from_links(pages)
    with open(graph_path) as fh:
        g = json.load(fh)

    def endpoint(e, a, b):
        return e.get(a, e.get(b))

    by_file = {p.get("file", k): k for k, p in pages.items()}  # filename stem -> page key
    keep = {}
    dropped_unmapped = 0
    for n in g.get("nodes", []):
        nid = n.get("id")
        sf = n.get("source_file", "")
        if not nid or not sf or EXCLUDE(sf):
            continue
        fkey = sf[:-3] if sf.endswith(".md") else sf
        key = by_file.get(fkey)
        if key is None:
            dropped_unmapped += 1
            continue
        keep[nid] = {
            "id": nid, "key": key, "label": n.get("label", key),
            "type": key.split("/")[0], "community": int(n.get("community", 0)),
        }
    if dropped_unmapped:
        log(f"dropped {dropped_unmapped} graph node(s) with no matching page")
    edges = []
    for e in g.get("links", g.get("edges", [])):
        s, t = endpoint(e, "source", "_src"), endpoint(e, "target", "_tgt")
        if s in keep and t in keep:
            edges.append({"s": s, "t": t, "relation": e.get("relation", ""),
                          "confidence": e.get("confidence", "")})
    # Partial graph.json (e.g. a freshly-ingested chapter graphify hasn't seen yet):
    # include every page still missing as its own community, wired by wikilinks, so the
    # atlas never silently drops content. Existing communities/colors are preserved.
    key2id = {v["key"]: nid for nid, v in keep.items()}
    if any(k not in key2id for k in pages):
        newc = max((v["community"] for v in keep.values()), default=-1) + 1
        for k in pages:
            if k not in key2id:
                keep[k] = {"id": k, "key": k, "label": pages[k]["title"],
                           "type": k.split("/")[0], "community": newc}
                key2id[k] = k
        seen = {(e["s"], e["t"]) for e in edges}
        for k in pages:
            sid = key2id.get(k)
            for tgt in pages[k].get("links", []):
                tid = key2id.get(tgt)
                if tid and sid != tid and (sid, tid) not in seen and (tid, sid) not in seen:
                    edges.append({"s": sid, "t": tid, "relation": "references", "confidence": "EXTRACTED"})
                    seen.add((sid, tid))
    _spring(keep, edges)
    communities = sorted({n["community"] for n in keep.values()})
    return {"nodes": list(keep.values()), "edges": edges, "communities": communities}


# ------------------------------------------------- front-door pieces ---------

def read_about(wiki_dir):
    p = os.path.join(wiki_dir, "about.md")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        _, body = parse_frontmatter(fh.read())
    return body


def resolve_atlas_title(wiki_dir, override=None):
    """The atlas masthead title, most-specific first:
      1. an explicit --title override,
      2. about.md frontmatter `title:`,
      3. about.md's H1 (the part before an em-dash/hyphen subtitle),
      4. the ATLAS_TITLE fallback constant.
    Keeps a second wiki from wearing this project's name."""
    if override:
        return override
    p = os.path.join(wiki_dir, "about.md")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            fm, body = parse_frontmatter(fh.read())
        if fm.get("title"):
            return str(fm["title"]).strip()
        h = re.search(r'^#\s+(.+)$', body, re.M)
        if h:
            return re.split(r'\s[—-]\s', h.group(1).strip(), maxsplit=1)[0].strip()
    return ATLAS_TITLE


def _newest_report(wiki_dir):
    reps = sorted(glob.glob(os.path.join(wiki_dir, "reports", "*-analysis.md")))
    return reps[-1] if reps else None


def read_unresolved(wiki_dir):
    p = _newest_report(wiki_dir)
    if not p:
        return ""
    with open(p, encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r'^##\s+Open questions the corpus cannot settle\s*\n(.*?)(?=^##\s|\Z)',
                  text, re.S | re.M)
    section = m.group(1).strip() if m else ""
    # ensure a blank line before the first list item so markdown renders a real
    # <ul> instead of folding the intro + bullets into one paragraph blob
    section = re.sub(r'(?m)^([^\n#>-].*\S)\n(- )', r'\1\n\n\2', section)
    return section


def read_community_labels(graphify_dir):
    """Parse `### Community N - "Name"` from GRAPH_REPORT.md (names renumber
    every analyze run, so never hard-code)."""
    p = os.path.join(graphify_dir, "GRAPH_REPORT.md")
    labels = {}
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            for m in re.finditer(r'^###\s+Community\s+(\d+)\s+-\s+"(.+)"\s*$',
                                 fh.read(), re.M):
                labels[int(m.group(1))] = m.group(2)
    return labels


def _hook(body):
    """First sentence after the H1, for theme/debate list hooks."""
    txt = re.sub(r'^#\s+.+$', '', body, count=1, flags=re.M)
    for line in txt.splitlines():
        line = line.strip()
        if line and not line.startswith(('#', '|', '-', '*', '>')):
            line = WIKILINK.sub(lambda m: m.group(2) or m.group(1).split('/')[-1], line)
            line = re.sub(r'[\*_`]', '', line)
            s = re.split(r'(?<=[.?!])\s', line)[0]
            return (s[:180] + '…') if len(s) > 180 else s
    return ""


def provenance(pages, wiki_dir):
    counts = Counter(p["type"] for p in pages.values())
    last = ""
    logp = os.path.join(wiki_dir, "log.md")
    if os.path.exists(logp):
        with open(logp, encoding="utf-8") as fh:
            stamps = re.findall(r'^(\d{4}-\d\d-\d\d \d\d:\d\d)\s*\|\s*analyze\s*\|',
                                fh.read(), re.M)
        if stamps:
            last = max(stamps)
    return {
        "literature": counts.get("literature", 0), "concepts": counts.get("concept", 0),
        "thinkers": counts.get("thinker", 0), "debates": counts.get("debate", 0),
        "themes": counts.get("theme", 0), "answers": counts.get("answer", 0),
        "last_analysis": last,
    }


def front_sections(pages, graph, community_labels):
    themes = [(k, p["title"], _hook(p["body"])) for k, p in pages.items() if p["type"] == "theme"]
    debates = [(k, p["title"]) for k, p in pages.items() if p["type"] == "debate"]
    clusters = [(cid, community_labels.get(cid, f"Community {cid}")) for cid in graph["communities"]]
    return {"themes": sorted(themes, key=lambda t: t[1]),
            "debates": sorted(debates, key=lambda t: t[1]),
            "clusters": clusters}


# ------------------------------------------------------------- render --------

PALETTE = ["#1e6154", "#9b4a2f", "#3a5a8c", "#7a5c99", "#3f7d4e", "#a8842a",
           "#8c3b5a", "#2f7d86", "#6b6f3a", "#894b2f", "#4a4a4a", "#5c7a99"]

# Masthead identity (thematic, editable here or via about.md's H1)
ATLAS_TITLE = "Other Minds"
ATLAS_KICKER = "A research atlas"

READER_CSS = """
:root{color-scheme:light dark;--paper:#f3f0e8;--paper-raised:#faf8f2;--ink:#181a18;
--muted:#666a62;--line:#c9c5b9;--accent:#1e6154;--accent-soft:#dce8e1;
--warning:#9b4a2f;--serif:Georgia,"Times New Roman",serif;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}
*{box-sizing:border-box;}html{scroll-behavior:smooth;}
body{margin:0;background:var(--paper);color:var(--ink);font:18px/1.72 var(--serif);text-rendering:optimizeLegibility;}
a{color:var(--accent);text-underline-offset:.18em;cursor:pointer;}
a:hover{text-decoration-thickness:2px;}
.masthead{padding:22px 28px 18px;border-bottom:3px double var(--ink);display:flex;
gap:24px;align-items:baseline;flex-wrap:wrap;justify-content:space-between;}
.masthead .brand{font:700 .74rem/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--accent);}
.masthead h1{margin:0;font:500 1.5rem/1 var(--serif);letter-spacing:-.02em;}
.prov{margin:0;color:var(--muted);font:600 .72rem/1.5 var(--sans);letter-spacing:.04em;text-transform:uppercase;}
#search{font:1rem var(--sans);padding:.5rem .7rem;border:1px solid var(--line);background:var(--paper-raised);color:var(--ink);min-width:220px;}
h2{margin:1.6em 0 .6em;font:500 2rem/1.05 var(--serif);letter-spacing:-.03em;}
h3{margin:1.6em 0 .5em;font:600 1.4rem/1.2 var(--serif);}
h4{margin:1.4em 0 .4em;font:700 1rem/1.3 var(--sans);}
p,ul,ol,blockquote,table{margin:0 0 1.2em;}li+li{margin-top:.4em;}
cite.cite{font-style:normal;color:var(--accent);font:600 .82em var(--sans);}
table{width:100%;border-collapse:collapse;font:.82rem/1.45 var(--sans);}
th,td{padding:9px;border:1px solid var(--line);text-align:left;vertical-align:top;}
blockquote{border-left:4px solid var(--accent);background:var(--accent-soft);margin:1.2em 0;padding:14px 20px;}
.wikilink-missing{color:var(--warning);border-bottom:1px dotted var(--warning);}
.status-chip{display:inline-block;font:700 .6rem var(--sans);letter-spacing:.1em;text-transform:uppercase;
color:var(--muted);border:1px solid var(--line);padding:2px 7px;border-radius:2px;margin-left:.6em;vertical-align:middle;}
"""

ATLAS_CSS = """
[hidden]{display:none !important;}
.mast-controls{display:flex;gap:8px;align-items:center;}
#home-btn,#panel-btn{font:600 .72rem var(--sans);letter-spacing:.04em;border:1px solid var(--line);cursor:pointer;padding:.5rem .7rem;background:var(--paper);color:var(--ink);}
#home-btn{background:var(--ink);color:var(--paper);border-color:var(--ink);}
#atlas{display:grid;grid-template-columns:minmax(300px,36%) 1fr;height:calc(100vh - 66px);}
#atlas.collapsed{grid-template-columns:1fr;}
.left-pane{border-right:1px solid var(--line);display:flex;flex-direction:column;overflow:hidden;background:var(--paper-raised);min-width:0;}
#atlas.collapsed .left-pane{display:none;}
.pane-tabs{display:flex;border-bottom:1px solid var(--line);flex:none;}
.pane-tabs .tab{flex:1;font:600 .72rem var(--sans);letter-spacing:.08em;text-transform:uppercase;background:var(--paper);color:var(--muted);border:none;border-right:1px solid var(--line);padding:.6rem;cursor:pointer;}
.pane-tabs .tab:last-child{border-right:none;}
.pane-tabs .tab.active{background:var(--paper-raised);color:var(--accent);box-shadow:inset 0 -2px 0 var(--accent);}
.pane-body{flex:1;min-height:0;display:flex;}
#view-graph,#view-index{flex:1;min-height:0;width:100%;display:flex;flex-direction:column;}
#view-index{overflow:auto;padding:10px 12px;}
#index-filter{font:1rem var(--sans);padding:.4rem .6rem;border:1px solid var(--line);background:var(--paper);color:var(--ink);margin-bottom:6px;flex:none;}
.index-group{margin-bottom:.3em;}
.index-group h3{margin:.7em 0 .25em;font:700 .7rem var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--accent);}
.index-group ul{list-style:disc;margin:0;padding:0 0 0 1.6em;}
.index-group li{padding:1px 0;}
.index-group li::marker{color:var(--line);}
.index-group li a{font:.92rem/1.35 var(--serif);text-decoration:none;color:var(--ink);}
.index-group li a:hover{color:var(--accent);}
.svg-wrap{flex:1;overflow:hidden;position:relative;min-height:0;}
#atlas-graph{width:100%;height:100%;cursor:grab;}
#atlas-graph.grabbing{cursor:grabbing;}
#atlas-graph line{stroke:var(--line);stroke-opacity:.5;vector-effect:non-scaling-stroke;}
#atlas-graph circle{cursor:pointer;stroke:var(--paper);stroke-width:1.2;transition:opacity .12s;vector-effect:non-scaling-stroke;}
#atlas-graph circle.dim{opacity:.12;}
#atlas-graph circle.neighbor{opacity:1;stroke:var(--ink);stroke-width:1.6;}
#atlas-graph circle.active{stroke:var(--ink);stroke-width:2.5;}
#atlas-graph line.edge-active{stroke:var(--ink);stroke-opacity:.8;stroke-width:1.4;}
#atlas-graph line.edge-dim{stroke-opacity:.06;}
#atlas-graph text{font-family:var(--sans);paint-order:stroke;stroke:var(--paper);stroke-width:3px;stroke-linejoin:round;fill:var(--ink);pointer-events:none;vector-effect:non-scaling-stroke;}
#atlas-graph text.cluster-title{font-weight:700;fill:var(--accent);opacity:.92;}
#atlas-graph text.node-label.sel{font-weight:700;}
#atlas-graph text.node-label.nbr{font-weight:600;fill:var(--muted);}
#graph-clear{position:absolute;top:8px;right:8px;z-index:5;font:600 .62rem var(--sans);letter-spacing:.05em;text-transform:uppercase;border:1px solid var(--line);background:var(--paper-raised);color:var(--ink);padding:4px 9px;cursor:pointer;border-radius:2px;}
#graph-clear:hover{border-color:var(--ink);}
.legend{padding:8px 10px;border-top:1px solid var(--line);font:600 .68rem/1.5 var(--sans);max-height:26%;overflow:auto;flex:none;}
.legend .lg{display:flex;align-items:center;gap:7px;cursor:pointer;padding:1px 0;}
.legend .sw{width:11px;height:11px;border-radius:50%;flex:none;}
.typefilter{padding:6px 10px;border-top:1px solid var(--line);display:flex;gap:6px;flex-wrap:wrap;flex:none;}
.typefilter button{font:600 .64rem var(--sans);letter-spacing:.04em;text-transform:uppercase;border:1px solid var(--line);background:var(--paper);color:var(--muted);padding:3px 8px;cursor:pointer;border-radius:2px;}
.typefilter button.off{opacity:.35;text-decoration:line-through;}
.typefilter button.on{background:var(--accent);color:var(--paper);border-color:var(--accent);opacity:1;}
.reader{overflow:auto;padding:40px clamp(24px,5vw,72px) 100px;}
.reader .doc{max-width:760px;margin:0 auto;}
.reader .kicker{font:700 .72rem var(--sans);letter-spacing:.13em;text-transform:uppercase;color:var(--accent);margin:0 0 8px;}
.reader .doc-actions{margin:0 0 20px;}
.reader .read-full{display:inline-block;font:700 .68rem var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--paper);background:var(--accent);border:1px solid var(--accent);padding:7px 13px;border-radius:3px;text-decoration:none;}
.reader .read-full:hover{opacity:.85;}
.reader .cluster-more{color:var(--muted);font-style:italic;margin:.5em 0 0;font-size:.92rem;}
.front .lead{font-size:1.12rem;}
.front h1{font:500 clamp(2.4rem,5vw,3.6rem)/1 var(--serif);letter-spacing:-.03em;margin:.1em 0 .5em;}
.front .cards a,.front .qlist a{text-decoration:none;}
.howto{margin:1.6em 0;padding:18px 22px;border-left:4px solid var(--accent);background:var(--accent-soft);}
.howto ul{margin:.4em 0 0;}
.unresolved-wrap ul{list-style:none;padding:0;margin:.6em 0 0;}
.unresolved-wrap li{padding:9px 0 9px 16px;border-left:3px solid var(--accent-soft);margin-bottom:8px;}
#tooltip{position:fixed;pointer-events:none;background:var(--ink);color:var(--paper);font:600 .72rem var(--sans);padding:4px 8px;border-radius:3px;opacity:0;transition:opacity .1s;z-index:20;max-width:280px;}
.search-results{list-style:none;padding:0;margin:1em 0;}
.search-results li{padding:6px 0;border-bottom:1px solid var(--line);}
#mobile-nav{display:none;}
@media (max-width:760px){
  body{display:flex;flex-direction:column;height:100vh;height:100dvh;}
  .masthead{flex:none;padding:10px 14px;gap:8px 12px;}
  .masthead h1{font-size:1.15rem;}
  .masthead .brand{display:none;}
  .prov{display:none;}
  .mast-controls{flex:1 1 100%;gap:6px;}
  #panel-btn{display:none;}
  #home-btn{padding:.45rem .6rem;}
  #search{flex:1;min-width:0;}
  #atlas{display:flex;flex:1;min-height:0;height:auto;grid-template-columns:none;}
  #atlas .left-pane{flex:1;width:100%;min-width:0;min-height:0;border-right:none;display:flex;}
  #atlas .reader{flex:1;width:100%;min-width:0;min-height:0;}
  #atlas:not(.show-read) .reader{display:none;}
  #atlas.show-read .left-pane{display:none;}
  .reader{padding:22px 16px 24px;}
  .legend{max-height:22%;}
  #mobile-nav{display:flex;flex:none;border-top:1px solid var(--line);background:var(--paper-raised);}
  #mobile-nav button{flex:1;font:600 .7rem var(--sans);letter-spacing:.06em;text-transform:uppercase;
    border:none;border-right:1px solid var(--line);background:none;color:var(--muted);padding:13px 6px;cursor:pointer;}
  #mobile-nav button:last-child{border-right:none;}
  #mobile-nav button.active{color:var(--accent);box-shadow:inset 0 2px 0 var(--accent);background:var(--paper);}
}
"""


def _svg(graph):
    node_by_id = {n["id"]: n for n in graph["nodes"]}
    lines = []
    for e in graph["edges"]:
        a, b = node_by_id.get(e["s"]), node_by_id.get(e["t"])
        if not a or not b:
            continue
        lines.append(f'<line x1="{a["x"]}" y1="{a["y"]}" x2="{b["x"]}" y2="{b["y"]}" '
                     f'data-s="{a["key"]}" data-t="{b["key"]}"/>')
    circles = []
    for n in graph["nodes"]:
        r = round(3 + (n["size"] ** 0.5) * 1.6, 1)
        color = PALETTE[n["community"] % len(PALETTE)]
        circles.append(
            f'<circle cx="{n["x"]}" cy="{n["y"]}" r="{r}" fill="{color}" '
            f'data-page="{n["key"]}" data-community="{n["community"]}" data-type="{n["type"]}" '
            f'data-label="{_html.escape(n["label"], quote=True)}"/>')
    return ('<g class="edges">' + "".join(lines) + '</g>'
            '<g class="nodes">' + "".join(circles) + '</g>')


def _index_html(pages):
    """Grouped, alphabetized, browsable list of every entry."""
    order = [("theme", "Themes"), ("debate", "Debates"), ("concept", "Concepts"),
             ("thinker", "Thinkers"), ("literature", "Literature"), ("answer", "Answers")]
    parts = []
    for typ, label in order:
        items = sorted(((k, p["title"]) for k, p in pages.items() if p["type"] == typ),
                       key=lambda t: t[1].lower())
        if not items:
            continue
        parts.append(f'<div class="index-group"><h3>{label} ({len(items)})</h3><ul>')
        for k, t in items:
            parts.append(f'<li><a data-page="{k}">{_html.escape(t)}</a></li>')
        parts.append('</ul></div>')
    return "".join(parts)


def _front_door_html(about_html, front, unresolved_html, prov):
    parts = ['<div class="doc front">', f'<p class="kicker">{_html.escape(ATLAS_KICKER)}</p>']
    if about_html:
        parts.append(f'<div class="lead">{about_html}</div>')
    else:
        parts.append(f'<p class="lead">A research wiki over {prov["literature"]} source documents — '
                     f'{prov["concepts"]} concepts, {prov["thinkers"]} thinkers, '
                     f'{prov["debates"]} debates, {prov["themes"]} themes.</p>')
    if front["themes"]:
        parts.append('<h2>Themes it explores</h2><ul>')
        for k, t, hook in front["themes"]:
            h = f' — {_html.escape(hook)}' if hook else ''
            parts.append(f'<li><a class="wikilink" data-page="{k}">{_html.escape(t)}</a>{h}</li>')
        parts.append('</ul>')
    if front["debates"]:
        parts.append('<h2>Live questions</h2><ul class="qlist">')
        for k, t in front["debates"]:
            parts.append(f'<li><a class="wikilink" data-page="{k}">{_html.escape(t)}</a></li>')
        parts.append('</ul>')
    if front["clusters"]:
        parts.append('<h2>Topic clusters</h2>'
                     '<p class="cluster-hint">Click a cluster to read what it is about — '
                     'its members and neighbouring topics — and light it up on the graph.</p><p>')
        chips = []
        for cid, label in front["clusters"]:
            color = PALETTE[cid % len(PALETTE)]
            chips.append(f'<a class="cluster-link" data-community="{cid}">'
                         f'<span class="sw" style="display:inline-block;width:11px;height:11px;'
                         f'border-radius:50%;background:{color};vertical-align:middle;margin-right:5px"></span>'
                         f'{_html.escape(label)}</a>')
        parts.append(' &nbsp;·&nbsp; '.join(chips))
        parts.append('</p>')
    parts.append(
        '<div class="howto"><strong>How to use this</strong><ul>'
        '<li><strong>Graph</strong> tab (left): click a node to open it and light up its neighbours; <em>Clear selection</em> resets and shows the cluster names. Topic chips isolate one kind — click more to add them back.</li>'
        '<li><strong>Index</strong> tab (left): browse every entry grouped by kind; filter as you type.</li>'
        '<li><strong>Search</strong> (top) finds any concept, thinker, or idea by name or meaning.</li>'
        '<li>Inside a page, follow the <em>See also</em> links to walk the ideas.</li>'
        '<li><strong>⌂ Home</strong> returns here; <strong>Panel</strong> hides the left side to read full-width.</li>'
        '<li>Open the <code>wiki/</code> folder in Obsidian to edit the underlying notes.</li>'
        '</ul></div>')
    if unresolved_html:
        parts.append('<h2>Open questions the corpus cannot settle</h2>')
        parts.append(f'<div class="unresolved-wrap">{unresolved_html}</div>')
    parts.append('</div>')
    return "".join(parts)


def _about_taglines(wiki, prov):
    """Subtitle (after the em-dash in about.md's H1) + a short blurb (first lead
    sentence) for the public landing page. Falls back to provenance counts."""
    subtitle, blurb = "", ""
    p = os.path.join(wiki, "about.md")
    if os.path.exists(p):
        body = re.sub(r'^---\n.*?\n---\n', '', open(p, encoding="utf-8").read(), flags=re.S)
        h = re.search(r'^#\s+(.+)$', body, re.M)
        if h and ("—" in h.group(1) or "-" in h.group(1)):
            subtitle = re.split(r'\s[—-]\s', h.group(1).strip(), maxsplit=1)[-1].strip()
        after = body[h.end():] if h else body
        for para in re.split(r'\n\s*\n', after):
            t = para.strip()
            if t and not t.startswith('#') and not t.startswith('**'):
                t = re.sub(r'[*_`]', '', t)
                blurb = (t[:220].rsplit(' ', 1)[0] + '…') if len(t) > 220 else t
                break
    if not blurb:
        blurb = (f'A research wiki over {prov["literature"]} source documents — '
                 f'{prov["concepts"]} concepts, {prov["thinkers"]} thinkers, '
                 f'{prov["debates"]} debates, {prov["themes"]} themes.')
    return subtitle, blurb


def _landing_html(title, kicker, subtitle, blurb):
    """Public splash with a login FORM (posts to /login). No credentials are shown or
    embedded. `__LOGIN_ERROR__` is replaced by the deploy server (empty, or an error
    line after a failed attempt); the server validates and sets a session cookie."""
    sub = f'<p class="sub">{_html.escape(subtitle)}</p>' if subtitle else ''
    blb = f'<p class="blurb">{_html.escape(blurb)}</p>' if blurb else ''
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark"><title>{_html.escape(title)}</title>
<style>
:root{{--paper:#f3f0e8;--paper-raised:#faf8f2;--ink:#181a18;--muted:#666a62;--line:#c9c5b9;--accent:#1e6154;--accent-soft:#dce8e1;--serif:Georgia,"Times New Roman",serif;--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}}
*{{box-sizing:border-box;}}
body{{margin:0;min-height:100vh;min-height:100dvh;display:flex;align-items:center;justify-content:center;padding:32px;background:var(--paper);color:var(--ink);font:18px/1.6 var(--serif);}}
.gate{{max-width:560px;width:100%;}}
.kicker{{font:700 .74rem/1 var(--sans);letter-spacing:.16em;text-transform:uppercase;color:var(--accent);margin:0 0 14px;}}
h1{{font:500 clamp(2.6rem,7vw,4rem)/1.02 var(--serif);letter-spacing:-.03em;margin:0 0 .2em;}}
.sub{{font:400 clamp(1.05rem,2.6vw,1.35rem)/1.4 var(--serif);margin:0 0 1.1em;}}
.blurb{{color:var(--muted);font-size:1rem;margin:0 0 1.8em;max-width:48ch;}}
.login{{margin-top:24px;border-top:1px solid var(--line);padding-top:22px;max-width:340px;}}
.login label{{display:block;font:600 .68rem/1 var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--accent);margin:0 0 6px;}}
.login input{{display:block;width:100%;font:1rem var(--sans);padding:.6rem .7rem;margin:0 0 14px;border:1px solid var(--line);background:var(--paper-raised);color:var(--ink);border-radius:2px;}}
.login input:focus{{outline:none;border-color:var(--accent);}}
.login button{{font:600 .82rem var(--sans);letter-spacing:.04em;text-transform:uppercase;cursor:pointer;background:var(--ink);color:var(--paper);border:none;padding:.85rem 1.4rem;border-radius:2px;}}
.login button:hover{{background:var(--accent);}}
.err{{color:#9b4a2f;font:600 .82rem var(--sans);margin:0 0 12px;}}
</style></head><body>
<main class="gate">
<p class="kicker">{_html.escape(kicker)}</p>
<h1>{_html.escape(title)}</h1>
{sub}
{blb}
<form class="login" method="post" action="login">
__LOGIN_ERROR__
<label for="u">Username</label><input id="u" name="username" autocomplete="username" autofocus required>
<label for="p">Password</label><input id="p" name="password" type="password" autocomplete="current-password" required>
<button type="submit">Enter the atlas &rarr;</button>
</form>
</main></body></html>"""


def render(pages, graph, about_html, unresolved_html, front, prov, community_labels,
           cluster_pages=None, title=None):
    title = title or ATLAS_TITLE
    front_door = _front_door_html(about_html, front, unresolved_html, prov)
    # PAGES payload for client navigation
    payload = {k: {"title": p["title"], "type": p["type"],
                   "status": _html.escape(str(p["status"])),
                   "html": p["html"], "text": re.sub(r'<[^>]+>', ' ', p["html"])[:4000]}
               for k, p in pages.items()}
    # cluster pages are reader-pane destinations, not graph nodes — merge into PAGES only
    if cluster_pages:
        payload.update(cluster_pages)
    legend = "".join(
        f'<div class="lg" data-community="{cid}"><span class="sw" '
        f'style="background:{PALETTE[cid % len(PALETTE)]}"></span>'
        f'{_html.escape(community_labels.get(cid, f"Community {cid}"))}</div>'
        for cid in graph["communities"])
    types = sorted({n["type"] for n in graph["nodes"]})
    typefilter = "".join(f'<button data-type="{t}">{t}</button>' for t in types)
    prov_line = " · ".join([
        f'{prov["literature"]} sources', f'{prov["concepts"]} concepts',
        f'{prov["thinkers"]} thinkers', f'{prov["debates"]} debates',
        f'{prov["themes"]} themes', f'{prov["answers"]} answers']
        + ([f'updated {prov["last_analysis"]}'] if prov["last_analysis"] else []))
    svg = _svg(graph)
    index_html = _index_html(pages)
    # `<\/` is JSON-safe (decodes to `</`) and prevents any page body containing
    # a literal </script> from closing the embedding <script> tag early.
    def _safe(obj):
        return json.dumps(obj).replace("</", "<\\/")
    graph_json = _safe({"nodes": graph["nodes"], "edges": graph["edges"]})
    pages_json = _safe(payload)
    front_json = _safe(front_door)
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark"><title>{_html.escape(title)}</title>
<style>{READER_CSS}{ATLAS_CSS}</style></head><body>
<header class="masthead">
  <div><span class="brand">{_html.escape(ATLAS_KICKER)}</span> <h1>{_html.escape(title)}</h1></div>
  <p class="prov">{prov_line}</p>
  <div class="mast-controls">
    <button id="home-btn" title="Front door">⌂ Home</button>
    <button id="panel-btn" title="Show/hide the left panel">Panel</button>
    <input id="search" type="search" placeholder="Search…" autocomplete="off">
  </div>
</header>
<div id="atlas" class="show-read">
  <aside class="left-pane">
    <div class="pane-tabs">
      <button class="tab active" data-view="graph">Graph</button>
      <button class="tab" data-view="index">Index</button>
    </div>
    <div class="pane-body">
      <section id="view-graph">
        <div class="svg-wrap"><button id="graph-clear" title="Clear graph selection" hidden>Clear selection</button><svg id="atlas-graph" viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid meet">{svg}</svg></div>
        <div class="typefilter">{typefilter}</div>
        <div class="legend">{legend}</div>
      </section>
      <section id="view-index" hidden>
        <input id="index-filter" type="search" placeholder="Filter entries…" autocomplete="off">
        <div class="index-groups">{index_html}</div>
      </section>
    </div>
  </aside>
  <main class="reader" id="reader"></main>
</div>
<nav id="mobile-nav">
  <button data-m="graph">Graph</button>
  <button data-m="index">Index</button>
  <button data-m="read">Read</button>
</nav>
<div id="tooltip"></div>
<script type="application/json" id="PAGES">{pages_json}</script>
<script type="application/json" id="GRAPH">{graph_json}</script>
<script type="application/json" id="FRONT">{front_json}</script>
<script>{CLIENT_JS}</script>
</body></html>"""


CLIENT_JS = r"""
const PAGES = JSON.parse(document.getElementById('PAGES').textContent);
const FRONT = JSON.parse(document.getElementById('FRONT').textContent);
const reader = document.getElementById('reader');
const svg = document.getElementById('atlas-graph');
const tip = document.getElementById('tooltip');
const atlas = document.getElementById('atlas');
const circles = [...svg.querySelectorAll('circle')];
const esc = s => String(s).replace(/</g,'&lt;');

function showFront(){ reader.innerHTML = FRONT; setActive(null); reader.scrollTop=0; }
function renderPage(key){
  const p = PAGES[key];
  if(!p){ return; }
  const isLit = key.indexOf('literature/')===0;
  const isCluster = key.indexOf('clusters/')===0;
  const kicker = isCluster ? 'topic cluster' : (isLit ? 'source document' : esc(p.type));
  let head = '';
  if(isLit){
    const href = 'literature-html/'+key.slice(11)+'.html';
    head = '<p class="doc-actions"><a class="read-full" href="'+href+'" target="_blank" rel="noopener">Read full document ↗</a></p>';
  }
  reader.innerHTML = '<div class="doc"><p class="kicker">'+kicker+
    (p.status?'<span class="status-chip">'+esc(p.status)+'</span>':'')+'</p>'+head+p.html+'</div>';
  reader.scrollTop=0;
  // a cluster page is a lens, not a graph node: light up its community instead of selecting a node
  if(isCluster){ highlightCommunity(+key.slice(9)); } else { setActive(key); }
  if(typeof mobileShow==='function' && isMobile()) mobileShow('read');
}
// clicking a cluster (legend swatch, front chip, or "related cluster" link) opens its
// page in the reader AND highlights it on the graph
function openCluster(cid){
  setView('graph');
  if(PAGES['clusters/'+cid]) renderPage('clusters/'+cid); else highlightCommunity(cid);
}
// A literature node now opens its source-hub page IN THE READER, like every other node.
// Only an anchored deep-link (a concept's "Sources" line) jumps into the full bundled
// document in a new tab, scrolled to the cited section; the hub page's own
// "Read full document" button covers the whole-document case.
function openEntry(key, anchor){
  if(key.indexOf('literature/')===0 && anchor){
    window.open('literature-html/'+key.slice(11)+'.html#'+anchor,'_blank');
  } else { renderPage(key); }
}
// one delegated listener handles every internal link (reader, index, search, clusters)
document.addEventListener('click', e=>{
  const p = e.target.closest('a[data-page]');
  if(p){ e.preventDefault(); openEntry(p.dataset.page, p.dataset.anchor); return; }
  const c = e.target.closest('a[data-community]');
  if(c){ e.preventDefault(); openCluster(+c.dataset.community); }
});
// ---- graph selection, neighbour highlight, labels, cluster titles ----
const svgNS='http://www.w3.org/2000/svg';
const lines=[...svg.querySelectorAll('line')];
const circleByKey={}; circles.forEach(c=>circleByKey[c.dataset.page]=c);
const adj={};
lines.forEach(l=>{ const s=l.dataset.s,t=l.dataset.t; if(!s||!t)return;
  (adj[s]=adj[s]||new Set()).add(t); (adj[t]=adj[t]||new Set()).add(s); });
const commLabel={}; document.querySelectorAll('.legend .lg').forEach(l=>commLabel[l.dataset.community]=l.textContent.trim());
const commMembers={}; circles.forEach(c=>{ (commMembers[c.dataset.community]=commMembers[c.dataset.community]||[]).push(c); });
const labelG=document.createElementNS(svgNS,'g'); labelG.setAttribute('class','labels'); svg.appendChild(labelG);
const clearBtn=document.getElementById('graph-clear');
let selState={mode:'default'};
const vis=c=>c.style.display!=='none';
function clearLabels(){ while(labelG.firstChild) labelG.removeChild(labelG.firstChild); }
const trunc=(s,n)=>String(s).length>n?String(s).slice(0,n-1)+'…':String(s);
function labelScale(){ return vb.w/1000; } // keep label px ~constant across zoom
function addLabel(x,y,text,cls,base){ const t=document.createElementNS(svgNS,'text');
  t.setAttribute('x',x); t.setAttribute('y',y); t.setAttribute('text-anchor','middle');
  t.setAttribute('class',cls); t.setAttribute('data-base',base);
  t.setAttribute('font-size', base*labelScale());
  t.textContent=text; labelG.appendChild(t); }
function updateLabelSizes(){ const s=labelScale();
  labelG.querySelectorAll('text').forEach(t=>t.setAttribute('font-size',(+t.getAttribute('data-base'))*s)); }
function centroid(ms){ let sx=0,sy=0,n=0; ms.forEach(c=>{ if(!vis(c))return; sx+=+c.getAttribute('cx'); sy+=+c.getAttribute('cy'); n++; }); return n?[sx/n,sy/n]:null; }
function showClusterTitles(){ clearLabels();
  Object.keys(commMembers).forEach(cid=>{ const c=centroid(commMembers[cid]); if(c) addLabel(c[0],c[1],commLabel[cid]||('Community '+cid),'cluster-title',17); }); }
function clearGraph(){ circles.forEach(c=>c.classList.remove('active','dim','neighbor'));
  lines.forEach(l=>l.classList.remove('edge-active','edge-dim')); }
function setDefault(){ selState={mode:'default'}; clearGraph(); showClusterTitles(); clearBtn.hidden=true; }
function setActive(key){
  const hit = key && circleByKey[key];
  if(!hit){ setDefault(); return; }
  selState={mode:'node',key:key};
  clearGraph(); clearLabels();
  const nb = adj[key] || new Set();
  circles.forEach(c=>{ const k=c.dataset.page;
    if(k===key) c.classList.add('active'); else if(nb.has(k)) c.classList.add('neighbor'); else c.classList.add('dim'); });
  lines.forEach(l=>{ const s=l.dataset.s,t=l.dataset.t;
    if((s===key&&nb.has(t))||(t===key&&nb.has(s))) l.classList.add('edge-active'); else l.classList.add('edge-dim'); });
  const sc=circleByKey[key], r=+sc.getAttribute('r');
  // neighbours first, selected label LAST so it always paints on top
  nb.forEach(k=>{ const c=circleByKey[k]; if(c&&vis(c)) addLabel(+c.getAttribute('cx'), +c.getAttribute('cy')-(+c.getAttribute('r'))-3, trunc(c.dataset.label,24), 'node-label nbr', 11); });
  addLabel(+sc.getAttribute('cx'), +sc.getAttribute('cy')-r-6, trunc(sc.dataset.label,44), 'node-label sel', 21);
  clearBtn.hidden=false;
}
function highlightCommunity(cid){
  selState={mode:'community',cid:cid};
  clearGraph(); clearLabels();
  circles.forEach(c=> c.classList.toggle('dim', +c.dataset.community!==cid));
  const c=centroid(commMembers[cid]||[]); if(c) addLabel(c[0],c[1],commLabel[cid]||('Community '+cid),'cluster-title',17);
  clearBtn.hidden=false;
}
function refreshGraph(){ if(selState.mode==='node') setActive(selState.key);
  else if(selState.mode==='community') highlightCommunity(selState.cid); else showClusterTitles(); }
clearBtn.addEventListener('click', setDefault);
// node interactions
circles.forEach(c=>{
  c.addEventListener('click',()=>openEntry(c.dataset.page));
  c.addEventListener('mousemove',e=>{ tip.textContent=c.dataset.label; tip.style.opacity=1;
    tip.style.left=(e.clientX+12)+'px'; tip.style.top=(e.clientY+12)+'px'; });
  c.addEventListener('mouseleave',()=>{ tip.style.opacity=0; });
});
document.querySelectorAll('.legend .lg').forEach(l=>l.addEventListener('click',()=>openCluster(+l.dataset.community)));
// topic chips: default shows ALL; first click isolates that type; extra clicks
// add types back in; clicking an active type removes it (empty -> back to all)
let activeTypes=null; // null = all types shown
function applyTypeFilter(){
  circles.forEach(c=>{ c.style.display = (activeTypes===null||activeTypes.has(c.dataset.type))?'':'none'; });
  document.querySelectorAll('.typefilter button').forEach(b=>{
    const on = activeTypes!==null && activeTypes.has(b.dataset.type);
    b.classList.toggle('on', on);
    b.classList.toggle('off', activeTypes!==null && !on);
  });
  refreshGraph();
}
document.querySelectorAll('.typefilter button').forEach(b=>b.addEventListener('click',()=>{
  const t=b.dataset.type;
  if(activeTypes===null) activeTypes=new Set([t]);
  else if(activeTypes.has(t)){ activeTypes.delete(t); if(!activeTypes.size) activeTypes=null; }
  else activeTypes.add(t);
  applyTypeFilter();
}));
// Home
document.getElementById('home-btn').addEventListener('click',showFront);
// Panel collapse (persisted)
function applyPanel(v){ atlas.classList.toggle('collapsed',v); }
applyPanel(localStorage.getItem('wikiAtlas.paneCollapsed')==='1');
document.getElementById('panel-btn').addEventListener('click',()=>{
  const v=!atlas.classList.contains('collapsed');
  localStorage.setItem('wikiAtlas.paneCollapsed', v?'1':'0'); applyPanel(v);
});
// Graph / Index tabs (persisted)
function setView(v){
  document.getElementById('view-graph').hidden = v!=='graph';
  document.getElementById('view-index').hidden = v!=='index';
  document.querySelectorAll('.pane-tabs .tab').forEach(t=>t.classList.toggle('active',t.dataset.view===v));
  if(atlas.classList.contains('collapsed')){ applyPanel(false); localStorage.setItem('wikiAtlas.paneCollapsed','0'); }
  localStorage.setItem('wikiAtlas.view', v);
}
document.querySelectorAll('.pane-tabs .tab').forEach(t=>t.addEventListener('click',()=>setView(t.dataset.view)));
setView(localStorage.getItem('wikiAtlas.view')||'graph');
// Index filter
const idxFilter=document.getElementById('index-filter');
idxFilter.addEventListener('input',()=>{
  const q=idxFilter.value.trim().toLowerCase();
  document.querySelectorAll('.index-group').forEach(g=>{
    let shown=0;
    g.querySelectorAll('li').forEach(li=>{ const hit=li.textContent.toLowerCase().includes(q);
      li.style.display=hit?'':'none'; if(hit)shown++; });
    g.style.display=shown?'':'none';
  });
});
// pan + zoom
let vb={x:0,y:0,w:1000,h:1000};
function setVB(){ svg.setAttribute('viewBox',`${vb.x} ${vb.y} ${vb.w} ${vb.h}`); updateLabelSizes(); }
svg.addEventListener('wheel',e=>{ e.preventDefault(); const f=e.deltaY<0?0.9:1.1;
  const r=svg.getBoundingClientRect(); const mx=vb.x+(e.clientX-r.left)/r.width*vb.w, my=vb.y+(e.clientY-r.top)/r.height*vb.h;
  vb.w*=f; vb.h*=f; vb.x=mx-(mx-vb.x)*f; vb.y=my-(my-vb.y)*f; setVB(); },{passive:false});
let drag=null;
svg.addEventListener('mousedown',e=>{ if(e.target.tagName==='circle')return; drag={x:e.clientX,y:e.clientY}; svg.classList.add('grabbing'); });
window.addEventListener('mousemove',e=>{ if(!drag)return; const r=svg.getBoundingClientRect();
  vb.x-=(e.clientX-drag.x)/r.width*vb.w; vb.y-=(e.clientY-drag.y)/r.height*vb.h; drag={x:e.clientX,y:e.clientY}; setVB(); });
window.addEventListener('mouseup',()=>{ drag=null; svg.classList.remove('grabbing'); });
// search
const search=document.getElementById('search');
search.addEventListener('input',()=>{
  const q=search.value.trim().toLowerCase();
  if(!q){ showFront(); return; }
  const hits=Object.entries(PAGES).filter(([k,p])=>
    p.title.toLowerCase().includes(q)||p.text.toLowerCase().includes(q))
    .sort((a,b)=>{ const at=a[1].title.toLowerCase().startsWith(q)?0:1, bt=b[1].title.toLowerCase().startsWith(q)?0:1; return at-bt; })
    .slice(0,40);
  reader.innerHTML='<div class="doc"><p class="kicker">Search</p><h2>'+hits.length+' result'+(hits.length===1?'':'s')+' for “'+esc(q)+'”</h2><ul class="search-results">'+
    hits.map(([k,p])=>'<li><a data-page="'+k+'">'+esc(p.title)+'</a> <span class="prov" style="text-transform:none;letter-spacing:0">'+esc(p.type)+'</span></li>').join('')+'</ul></div>';
  if(isMobile()) mobileShow('read');
});
// mobile single-panel nav: switch Graph / Index / Read (one panel at a time)
const isMobile=()=>matchMedia('(max-width:760px)').matches;
function mobileShow(m){
  if(m==='read'){ atlas.classList.add('show-read'); }
  else { atlas.classList.remove('show-read'); setView(m); }
  document.querySelectorAll('#mobile-nav button').forEach(b=>b.classList.toggle('active',b.dataset.m===m));
}
document.querySelectorAll('#mobile-nav button').forEach(b=>b.addEventListener('click',()=>mobileShow(b.dataset.m)));
mobileShow('read');
showFront();
"""


# ------------------------------------------------------------- validate ------

def validate(pages, graph, html, extra_pages=0):
    problems = []
    if not html or len(html) < 1000:
        problems.append("output HTML is empty or too small")
    m = re.search(r'id="PAGES"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        problems.append("PAGES payload missing")
    else:
        try:
            if len(json.loads(m.group(1))) != len(pages) + extra_pages:
                problems.append("embedded PAGES count != parsed pages count")
        except json.JSONDecodeError:
            problems.append("PAGES payload does not parse (script-tag breakout?)")
    for island in ("GRAPH", "FRONT"):
        mm = re.search(rf'id="{island}"[^>]*>(.*?)</script>', html, re.S)
        if not mm:
            problems.append(f"{island} payload missing")
            continue
        try:
            json.loads(mm.group(1))
        except json.JSONDecodeError:
            problems.append(f"{island} payload does not parse (script-tag breakout?)")
    ok = set(PAGE_DIRS)
    for n in graph["nodes"]:
        if n["key"].split("/")[0] not in ok:
            problems.append(f"metadata node leaked: {n['key']}")
    node_ids = {n["id"] for n in graph["nodes"]}
    for e in graph["edges"]:
        if e["s"] not in node_ids or e["t"] not in node_ids:
            problems.append("edge with endpoint outside node set")
            break
    return problems


# ------------------------------------------------------------- build ---------

def _load_anchor_heading(wiki):
    """{source-slug: {anchor: heading}} from the corpus anchors.json (for labels)."""
    p = os.path.join(wiki, ".literature-text", "anchors.json")
    out = {}
    if os.path.exists(p):
        data = json.load(open(p, encoding="utf-8"))
        for slug, entries in data.items():
            m = {}
            for e in entries:
                # keep the FIRST heading per anchor — the section-title h2, since
                # child h3s inherit the same section anchor and come later in order
                if e.get("anchor") and e["anchor"] not in m:
                    m[e["anchor"]] = e["heading"]
            out[slug] = m
    return out


def _sources_html(page, anchor_heading):
    """Anchored deep-links into the literature: each source opens the document scrolled
    to the section the concept draws on (via page['sources']), falling back to the
    whole document when no anchor is known."""
    items = []
    for b in page["literature"]:
        anc = page.get("sources", {}).get(b)
        if anc:
            head = anchor_heading.get(b, {}).get(anc, "")
            label = f"{b} § {head}" if head else b
            items.append(f'<a class="wikilink" data-page="literature/{b}" data-anchor="{_html.escape(anc, quote=True)}">{_html.escape(label)}</a>')
        else:
            items.append(f'<a class="wikilink" data-page="literature/{b}">{_html.escape(b)}</a>')
    if not items:
        return ""
    return '<h2>Sources</h2><p>Drawn from the literature: ' + " · ".join(items) + '.</p>'


# graph node types are the directory names (plural), e.g. key.split("/")[0]
CLUSTER_TYPE_ORDER = [("literature", "Sources"), ("concepts", "Concepts"),
                      ("thinkers", "Thinkers"), ("debates", "Debates"),
                      ("themes", "Themes"), ("answers", "Answers")]


def _cluster_structure(graph):
    """Per-community member lists (sorted by degree desc) + top related communities.
    Derived from the graph itself so membership always matches what the graph shows."""
    deg = Counter()
    for e in graph["edges"]:
        deg[e["s"]] += 1
        deg[e["t"]] += 1
    id2comm = {n["id"]: n["community"] for n in graph["nodes"]}
    members = {}
    for n in graph["nodes"]:
        members.setdefault(n["community"], []).append(
            {"key": n["key"], "label": n["label"], "type": n["type"],
             "deg": deg.get(n["id"], 0)})
    for cid in members:
        members[cid].sort(key=lambda m: (-m["deg"], m["label"].lower()))
    cross = {}
    for e in graph["edges"]:
        ca, cb = id2comm.get(e["s"]), id2comm.get(e["t"])
        if ca is None or cb is None or ca == cb:
            continue
        cross.setdefault(ca, Counter())[cb] += 1
        cross.setdefault(cb, Counter())[ca] += 1
    related = {cid: [c for c, _ in cross.get(cid, Counter()).most_common(3)]
               for cid in members}
    return members, related


def _load_cluster_narratives(wiki, pages):
    """Hand/LLM-written prose bodies from wiki/clusters/*.md, returned as a LIST.

    Deliberately NOT keyed by the frontmatter `community:` integer: graphify
    renumbers communities on every run, so that id goes stale and would attach an
    essay to the wrong current cluster. Instead each narrative carries the set of
    member pages it wikilinks to, and `_match_narratives_to_communities` re-attaches
    it to whatever current community its content actually overlaps. The leading H1 is
    stripped (build_cluster_pages prepends the authoritative graphify label as the
    heading, so the reader title always matches the legend)."""
    out = []
    for p in sorted(glob.glob(os.path.join(wiki, "clusters", "*.md"))):
        with open(p, encoding="utf-8") as fh:
            fm, body = parse_frontmatter(fh.read())
        links = {m[0] for m in WIKILINK.findall(body)}  # slug only (ignore |alias)
        body = re.sub(r'^#\s+.+$', '', body, count=1, flags=re.M)  # drop dup H1
        out.append({"title": fm.get("title", ""), "links": links,
                    "html": md_to_html(body, pages)[0]})
    return out


def _match_narratives_to_communities(narratives, members):
    """Attach each stale-numbered narrative to the CURRENT community whose members it
    most overlaps (by wikilinked pages). Greedy by overlap; each community and each
    narrative used at most once; a narrative overlapping nothing is dropped (an
    unadorned member list beats the wrong essay). Returns {cid: narrative}."""
    member_keys = {cid: {m["key"] for m in mems} for cid, mems in members.items()}
    cand = []  # (overlap, narrative_index, cid)
    for i, n in enumerate(narratives):
        for cid, keys in member_keys.items():
            ov = len(n["links"] & keys)
            if ov:
                cand.append((ov, i, cid))
    cand.sort(reverse=True)  # strongest overlap wins ties for a community
    used_narr, used_cid, by_cid = set(), set(), {}
    for ov, i, cid in cand:
        if i in used_narr or cid in used_cid:
            continue
        by_cid[cid] = narratives[i]
        used_narr.add(i)
        used_cid.add(cid)
    return by_cid


def build_cluster_pages(wiki, pages, graph, labels):
    """Reader-pane pages for each topic cluster: narrative + linked member list +
    related clusters. NOT graph nodes — a lens over the graph, reachable from the
    legend/chips. Returned in payload shape to merge into PAGES."""
    members, related = _cluster_structure(graph)
    narr = _match_narratives_to_communities(_load_cluster_narratives(wiki, pages), members)

    def clabel(cid):
        return labels.get(cid) or narr.get(cid, {}).get("title") or f"Community {cid}"

    payload = {}
    CAP = 30  # big clusters list only their most-connected members
    for cid, mems in members.items():
        # authoritative heading = the current graphify label, so the reader title
        # always matches the legend swatch; the matched narrative prose follows.
        parts = [f'<h1>{_html.escape(clabel(cid))}</h1>', narr.get(cid, {}).get("html", "")]
        total = len(mems)
        shown = mems[:CAP]  # mems already sorted by degree desc
        by_type = {}
        for m in shown:
            by_type.setdefault(m["type"], []).append(m)
        head = "In this cluster"
        if total > CAP:
            head += f" — top {CAP} of {total} by connectivity"
        parts.append(f'<h2>{head}</h2>')
        for typ, tlabel in CLUSTER_TYPE_ORDER:
            if typ in by_type:
                parts.append(f'<h3>{tlabel} ({len(by_type[typ])})</h3><ul>')
                parts.extend(
                    f'<li><a class="wikilink" data-page="{m["key"]}">'
                    f'{_html.escape(m["label"])}</a></li>' for m in by_type[typ])
                parts.append('</ul>')
        if total > CAP:
            parts.append(f'<p class="cluster-more">+{total - CAP} more '
                         f'(open the cluster note in Obsidian for the full list)</p>')
        rel = related.get(cid, [])
        if rel:
            links = " · ".join(f'<a class="cluster-link" data-community="{rc}">'
                               f'{_html.escape(clabel(rc))}</a>' for rc in rel)
            parts.append(f'<h2>Related clusters</h2><p>{links}</p>')
        html = "".join(parts)
        payload[f"clusters/{cid}"] = {
            "title": clabel(cid), "type": "cluster", "status": "",
            "html": html, "text": re.sub(r'<[^>]+>', ' ', html)[:4000]}
    return payload


def build_all(wiki, out, quiet=True, title=None):
    def log(*a):
        if not quiet:
            print("[wiki-atlas]", *a)

    title = resolve_atlas_title(wiki, title)

    anchor_heading = _load_anchor_heading(wiki)
    pages = load_pages(wiki, {})
    for p in pages.values():
        body = p["body"]
        if p["overview"]:
            # the narrative already integrates the per-source material, so drop the
            # raw "## In <source>" scaffolding sections from the reader view (they
            # stay in the markdown for Obsidian + the ingest pipeline)
            body = re.sub(r'(?ms)^##\s+In\s+.*?(?=^##\s|\Z)', '', body)
        p["html"], p["links"], p["missing"] = md_to_html(body, pages)
        if p["overview"] and p["literature"]:
            p["html"] += _sources_html(p, anchor_heading)
    graph = load_graph(os.path.join(wiki, "graphify-out", "graph.json"), pages, log)
    # optional title backfill for the rare graph-label fallback
    node_label = {n["key"]: n["label"] for n in graph["nodes"]}
    for k, p in pages.items():
        if p["title"] == p["slug"] and node_label.get(k):
            p["title"] = node_label[k]
    labels = read_community_labels(os.path.join(wiki, "graphify-out"))
    about_html_body = read_about(wiki)
    about_html = md_to_html(about_html_body, pages)[0] if about_html_body else None
    unresolved_html = md_to_html(read_unresolved(wiki), pages)[0]
    prov = provenance(pages, wiki)
    front = front_sections(pages, graph, labels)
    cluster_pages = build_cluster_pages(wiki, pages, graph, labels)
    html = render(pages, graph, about_html, unresolved_html, front, prov, labels,
                  cluster_pages, title=title)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    # public landing/gate page beside the atlas; the deploy server serves it at "/"
    # (creds injected at serve time). Optional artifact — the atlas works without it.
    subtitle, blurb = _about_taglines(wiki, prov)
    with open(os.path.join(wiki, "landing.html"), "w", encoding="utf-8") as fh:
        fh.write(_landing_html(title, ATLAS_KICKER, subtitle, blurb))
    missing_total = sum(len(p.get("missing", [])) for p in pages.values())
    problems = validate(pages, graph, html, extra_pages=len(cluster_pages))
    if missing_total:
        log(f"note: {missing_total} unresolved wikilink(s) rendered as inert text")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the wiki atlas HTML.")
    ap.add_argument("--wiki", default=WIKI_DEFAULT)
    ap.add_argument("--out", default=None)
    ap.add_argument("--title", default=None,
                    help="atlas masthead title; overrides about.md's title:/H1 "
                         "(default: resolve from about.md, else the built-in fallback)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    out = args.out or os.path.join(args.wiki, "wiki.html")
    try:
        problems = build_all(args.wiki, out, quiet=args.quiet, title=args.title)
    except Exception as e:  # hard failure only
        print(f"[wiki-atlas] BUILD FAILED: {e}", file=sys.stderr)
        return 2
    if problems:
        print("[wiki-atlas] validator problems:")
        for p in problems:
            print("  -", p)
        return 1
    if not args.quiet:
        print(f"[wiki-atlas] wrote {out} (validator clean)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
