import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wiki_roots import find_roots, default_wiki


def _mkwiki(d):
    os.makedirs(os.path.join(d, "concepts"))
    open(os.path.join(d, "index.md"), "w").close()
    open(os.path.join(d, "log.md"), "w").close()


def test_project_layout_from_subfolder(tmp_path):
    _mkwiki(tmp_path / "wiki"); (tmp_path / "deeper_research").mkdir(); (tmp_path / "a" / "b").mkdir(parents=True)
    r = find_roots(str(tmp_path / "a" / "b"))
    assert r["wiki"] == str(tmp_path / "wiki") and r["sources"] == str(tmp_path / "deeper_research")


def test_inside_wiki_folder(tmp_path):
    _mkwiki(tmp_path / "wiki")
    r = find_roots(str(tmp_path / "wiki" / "concepts"))
    assert r["wiki"] == str(tmp_path / "wiki") and r["sources"] is None


def test_config_overrides(tmp_path):
    (tmp_path / "notes").mkdir(); (tmp_path / "corpus").mkdir()
    (tmp_path / ".research-wiki.json").write_text(json.dumps({"wiki": "notes", "sources": "corpus"}))
    r = find_roots(str(tmp_path))
    assert r["wiki"] == str(tmp_path / "notes") and r["sources"] == str(tmp_path / "corpus")


def test_no_wiki_returns_none(tmp_path):
    assert find_roots(str(tmp_path)) is None or not str(find_roots(str(tmp_path))["wiki"]).startswith(str(tmp_path))
    assert default_wiki(str(tmp_path)) is None or not default_wiki(str(tmp_path)).startswith(str(tmp_path))
