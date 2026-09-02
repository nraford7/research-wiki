import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from match_sources import _query, main, nearest_anchor  # noqa: E402


def test_nearest_anchor_prefers_finest_anchored_heading():
    md = "# B\n\n## Big Section\n\n### Fine Sub\n\nhit\n"  # "hit" is line 7
    anchors_b = [{"heading": "Big Section", "anchor": "section-big", "level": 2},
                 {"heading": "Fine Sub", "anchor": "section-fine", "level": 3}]
    assert nearest_anchor(md, 7, anchors_b) == ("Fine Sub", "section-fine")


def test_nearest_anchor_falls_back_to_h2_when_h3_unanchored():
    md = "# B\n\n## Big Section\n\n### Fine Sub\n\nhit\n"
    anchors_b = [{"heading": "Big Section", "anchor": "section-big", "level": 2},
                 {"heading": "Fine Sub", "anchor": None, "level": 3}]
    assert nearest_anchor(md, 7, anchors_b) == ("Big Section", "section-big")


def test_nearest_anchor_none_before_first_heading():
    assert nearest_anchor("# B\n\npreamble hit\n", 3, []) == (None, None)


def _helper(tmp_path, body):
    p = tmp_path / "search.py"
    p.write_text(body)
    return str(p)


def test_query_returns_first_json_hit_when_helper_succeeds(tmp_path):
    search = _helper(tmp_path, 'import json\nprint("note")\nprint(json.dumps({"line": 7}))\n')
    assert _query("src", "q", str(tmp_path), search) == {"line": 7}


def test_query_raises_when_helper_exits_nonzero(tmp_path):
    search = _helper(tmp_path, 'import sys\nsys.stderr.write("boom\\n")\nsys.exit(3)\n')
    with pytest.raises(RuntimeError, match=r"exit 3.*boom"):
        _query("src", "q", str(tmp_path), search)


def _wiki(tmp_path, with_anchors=True):
    """A one-page wiki: concepts/x.md (overview: true) citing source `src`,
    whose corpus text has one anchored h2 above the line the helper returns."""
    wiki = tmp_path / "wiki"
    corpus = wiki / ".literature-text"
    (wiki / "concepts").mkdir(parents=True)
    corpus.mkdir()
    (corpus / "src.md").write_text("# src\n\n## Big Section\n\nhit\n")  # "hit" is line 5
    if with_anchors:
        (corpus / "anchors.json").write_text(json.dumps(
            {"src": [{"heading": "Big Section", "anchor": "section-big", "level": 2}]}))
    (wiki / "concepts" / "x.md").write_text(
        "---\ntitle: X\nliterature: [src]\noverview: true\n---\n\nbody\n")
    return wiki


def test_main_writes_deep_links_for_the_given_wiki(tmp_path):
    wiki = _wiki(tmp_path)
    search = _helper(tmp_path, 'import json\nprint(json.dumps({"line": 5}))\n')
    assert main(["--wiki", str(wiki), "--search", search]) == 0
    assert "sources: {src: section-big}" in (wiki / "concepts" / "x.md").read_text()


def test_main_fails_when_helper_missing(tmp_path, capsys):
    wiki = _wiki(tmp_path)
    rc = main(["--wiki", str(wiki), "--search", str(tmp_path / "missing.py")])
    assert rc == 1
    assert "semantic-search helper not found" in capsys.readouterr().err


def test_main_fails_when_anchors_missing_and_names_the_corpus(tmp_path, capsys):
    wiki = _wiki(tmp_path, with_anchors=False)
    search = _helper(tmp_path, "print()\n")
    rc = main(["--wiki", str(wiki), "--search", search])
    assert rc == 1
    err = capsys.readouterr().err
    assert "anchors.json not found" in err
    assert f"--out {wiki / '.literature-text'}" in err  # recovery hint targets THIS wiki


def test_main_fails_when_helper_exits_nonzero(tmp_path, capsys):
    wiki = _wiki(tmp_path)
    search = _helper(tmp_path, 'import sys\nsys.stderr.write("boom\\n")\nsys.exit(3)\n')
    rc = main(["--wiki", str(wiki), "--search", search])
    assert rc == 1
    assert "exit 3" in capsys.readouterr().err
    assert "sources:" not in (wiki / "concepts" / "x.md").read_text()  # nothing written
