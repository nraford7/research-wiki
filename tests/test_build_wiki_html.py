import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from build_wiki_html import (  # noqa: E402
    ATLAS_TITLE, EXCLUDE, build_all, load_graph, md_to_html, parse_frontmatter,
    provenance, read_community_labels, render, resolve_atlas_title, resolve_title,
)

WIKI = "/Users/noahraford/magic/wiki"


# -- Task 1 -----------------------------------------------------------------

def test_parse_frontmatter_splits_yaml_and_body():
    fm, body = parse_frontmatter(
        "---\ntype: concept\nslug: wu-wei\ntitle: Wu-Wei\n---\n# Wu-Wei\n\nbody text")
    assert fm["type"] == "concept" and fm["title"] == "Wu-Wei"
    assert body.strip().startswith("# Wu-Wei")


def test_resolve_title_chain():
    assert resolve_title({"title": "T"}, "# H", "L", "s") == "T"
    assert resolve_title({"name": "Aristotle"}, "# H", "L", "s") == "Aristotle"
    assert resolve_title({"question": "Q?"}, "# H", "L", "s") == "Q?"
    assert resolve_title({}, "# H1 Heading\n\nx", "L", "s") == "H1 Heading"
    assert resolve_title({}, "no heading", "GraphLabel", "s") == "GraphLabel"
    assert resolve_title({}, "no heading", None, "the-slug") == "the-slug"


def test_parse_frontmatter_quoted_value_with_comma_and_colon():
    # literature pages use `question:` with commas/colons; must survive
    txt = ('---\ntype: literature\nslug: ch1-q1\n'
           'question: "Do minds, in the strong sense: differ across cultures?"\n---\nbody')
    fm, _ = parse_frontmatter(txt)
    assert resolve_title(fm, "body", None, "ch1-q1") == \
        "Do minds, in the strong sense: differ across cultures?"


# -- Task 2 -----------------------------------------------------------------

def test_exclude_metadata():
    assert EXCLUDE("index.md") and EXCLUDE("log.md") and EXCLUDE("about.md")
    assert EXCLUDE("reports/2026-08-30-analysis.md")
    assert not EXCLUDE("concepts/wu-wei.md")
    assert not EXCLUDE("literature/ch1-q1-non-western-AI.md")


# -- Task 3 -----------------------------------------------------------------

def test_wikilink_resolves_and_missing_tracked():
    pages = {"concepts/wu-wei": {"title": "Wu-Wei"}}
    html, links, missing = md_to_html(
        "See [[concepts/wu-wei]] and [[concepts/ghost]].", pages)
    assert 'data-page="concepts/wu-wei"' in html and "Wu-Wei" in html
    assert "concepts/wu-wei" in links and missing == ["concepts/ghost"]


def test_citation_wrapped():
    html, _, _ = md_to_html("As shown [Slingerland, 2014].", {})
    assert '<cite' in html and "Slingerland, 2014" in html


def test_table_renders():
    html, _, _ = md_to_html("| A | B |\n|---|---|\n| 1 | 2 |", {})
    assert "<table" in html


def test_citation_does_not_touch_wikilinks():
    pages = {"concepts/wu-wei": {"title": "Wu-Wei"}}
    html, _, _ = md_to_html("[[concepts/wu-wei]] then [Author, 2020]", pages)
    assert 'data-page="concepts/wu-wei"' in html and '<cite' in html


# -- Task 4 -----------------------------------------------------------------

def test_graph_filter_drops_metadata_nodes_and_edges(tmp_path):
    g = {"nodes": [
            {"id": "wu-wei", "label": "Wu-Wei", "source_file": "concepts/wu-wei.md", "community": 2},
            {"id": "index", "label": "idx", "source_file": "index.md", "community": 0}],
         "links": [{"source": "index", "target": "wu-wei", "relation": "references"}],
         "hyperedges": [{"id": "h", "nodes": ["wu-wei"]}]}
    p = tmp_path / "graph.json"
    p.write_text(json.dumps(g))
    pages = {"concepts/wu-wei": {"title": "Wu-Wei"}}
    out = load_graph(str(p), pages)
    assert {n["id"] for n in out["nodes"]} == {"wu-wei"}
    assert out["edges"] == []
    assert out["communities"] == [2]


def test_graph_fallback_when_absent():
    pages = {"concepts/a": {"title": "A", "links": ["concepts/b"]},
             "concepts/b": {"title": "B", "links": []}}
    out = load_graph("/nonexistent/graph.json", pages)
    assert {n["id"] for n in out["nodes"]} == {"concepts/a", "concepts/b"}
    assert len(out["edges"]) == 1


def test_graph_maps_when_slug_differs_from_filename(tmp_path):
    # page key is by slug; node source_file is by filename — must reconcile
    g = {"nodes": [{"id": "n1", "label": "De la Cadena",
                    "source_file": "thinkers/dela-cadena.md", "community": 0}],
         "links": []}
    p = tmp_path / "graph.json"
    p.write_text(json.dumps(g))
    pages = {"thinkers/de-la-cadena": {"title": "De la Cadena",
                                       "file": "thinkers/dela-cadena"}}
    out = load_graph(str(p), pages)
    assert len(out["nodes"]) == 1
    assert out["nodes"][0]["key"] == "thinkers/de-la-cadena"  # mapped to slug key


def test_graph_node_missing_id_is_dropped_not_crash(tmp_path):
    g = {"nodes": [{"label": "x", "source_file": "concepts/a.md", "community": 0},
                   {"id": "ok", "label": "A", "source_file": "concepts/a.md", "community": 0}],
         "links": []}
    p = tmp_path / "graph.json"
    p.write_text(json.dumps(g))
    out = load_graph(str(p), {"concepts/a": {"title": "A", "file": "concepts/a"}})
    assert {n["id"] for n in out["nodes"]} == {"ok"}  # missing-id node skipped, no crash


# -- Task 5 -----------------------------------------------------------------

def test_provenance_counts_and_max_date(tmp_path):
    (tmp_path / "log.md").write_text(
        "# log\n2026-08-30 15:45 | analyze | x\n2026-08-30 10:15 | analyze | y\n")
    pages = {"concepts/a": {"type": "concept"}, "debates/b": {"type": "debate"}}
    pr = provenance(pages, str(tmp_path))
    assert pr["concepts"] == 1 and pr["debates"] == 1
    assert pr["last_analysis"] == "2026-08-30 15:45"


def test_read_community_labels(tmp_path):
    gd = tmp_path / "graphify-out"
    gd.mkdir()
    (gd / "GRAPH_REPORT.md").write_text(
        '## Communities\n### Community 0 - "Non-Western & Relational Minds"\n'
        'Cohesion: 0.12\n### Community 5 - "Western Philosophy of Mind"\n')
    labels = read_community_labels(str(gd))
    assert labels[0] == "Non-Western & Relational Minds"
    assert labels[5] == "Western Philosophy of Mind"


# -- Task 6: end-to-end -----------------------------------------------------

def test_script_tag_breakout_is_escaped():
    # a page body containing </script> must not break the embedded JSON island
    pages = {"concepts/x": {"title": "X", "type": "concept", "status": "draft",
                            "html": "<p>evil </script><script>alert(1)</script></p>",
                            "slug": "x", "file": "concepts/x", "body": "b"}}
    graph = {"nodes": [], "edges": [], "communities": []}
    front = {"themes": [], "debates": [], "clusters": []}
    prov = {k: 0 for k in ("literature", "concepts", "thinkers", "debates", "themes", "answers")}
    prov["last_analysis"] = ""
    html = render(pages, graph, None, "", front, prov, {})
    import re as _re
    m = _re.search(r'id="PAGES"[^>]*>(.*?)</script>', html, _re.S)
    assert m and json.loads(m.group(1))  # island parses; breakout neutralized
    assert "</script>" not in m.group(1)


@pytest.mark.skipif(not os.path.isdir(WIKI), reason="wiki absent")
def test_end_to_end_builds_and_validates(tmp_path):
    import re
    out = str(tmp_path / "wiki.html")
    problems = build_all(WIKI, out)
    assert problems == [], problems
    html = open(out, encoding="utf-8").read()
    assert "Other Minds" in html and 'id="atlas-graph"' in html
    assert 'id="view-index"' in html and 'data-view="index"' in html  # index panel present
    g = json.loads(re.search(r'id="GRAPH"[^>]*>(.*?)</script>', html, re.S).group(1))
    ok = {"literature", "concepts", "thinkers", "debates", "themes", "answers"}
    assert all(n["key"].split("/")[0] in ok for n in g["nodes"])
    node_ids = {n["id"] for n in g["nodes"]}
    assert all(e["s"] in node_ids and e["t"] in node_ids for e in g["edges"])


# -- atlas title portability (issue #7) -------------------------------------

def _about(tmp_path, text):
    (tmp_path / "about.md").write_text(text)
    return str(tmp_path)


def test_resolve_atlas_title_override_wins(tmp_path):
    w = _about(tmp_path, "---\ntitle: From File\n---\n# From H1\n")
    assert resolve_atlas_title(w, "Explicit") == "Explicit"


def test_resolve_atlas_title_reads_frontmatter(tmp_path):
    w = _about(tmp_path, "---\ntitle: My Second Wiki\n---\n# Ignored H1\n")
    assert resolve_atlas_title(w) == "My Second Wiki"


def test_resolve_atlas_title_falls_back_to_h1_before_dash(tmp_path):
    w = _about(tmp_path, "# Second Wiki — A research atlas\n\nlead para\n")
    assert resolve_atlas_title(w) == "Second Wiki"


def test_resolve_atlas_title_uses_full_h1_when_no_dash(tmp_path):
    w = _about(tmp_path, "# Just A Title\n\nlead para\n")
    assert resolve_atlas_title(w) == "Just A Title"


def test_resolve_atlas_title_falls_back_to_constant_when_no_about(tmp_path):
    assert resolve_atlas_title(str(tmp_path)) == ATLAS_TITLE


def test_render_uses_provided_title():
    pages, graph = {}, {"nodes": [], "edges": [], "communities": []}
    prov = {k: 0 for k in ("literature", "concepts", "thinkers", "debates", "themes", "answers")}
    prov["last_analysis"] = ""
    front = {"themes": [], "debates": [], "clusters": []}
    html = render(pages, graph, None, "", front, prov, {}, title="A Different Atlas")
    assert "<title>A Different Atlas</title>" in html
    assert "<h1>A Different Atlas</h1>" in html
    assert "Other Minds" not in html


def test_render_defaults_to_constant_without_title():
    pages, graph = {}, {"nodes": [], "edges": [], "communities": []}
    prov = {k: 0 for k in ("literature", "concepts", "thinkers", "debates", "themes", "answers")}
    prov["last_analysis"] = ""
    front = {"themes": [], "debates": [], "clusters": []}
    html = render(pages, graph, None, "", front, prov, {})
    assert f"<h1>{ATLAS_TITLE}</h1>" in html
