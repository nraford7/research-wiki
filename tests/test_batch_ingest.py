import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from batch_ingest import (  # noqa: E402
    qualifies, content_hash, enumerate_sources, _sections_dir, _sources_files,
)


def _mk(d, files):
    """Create dir d with {relpath: content} files (dirs made as needed)."""
    os.makedirs(d, exist_ok=True)
    for rel, content in files.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(content)
    return d


def _book_source(parent, slug):
    """Book-corpus layout: Sections/ (capital) + Sources/."""
    return _mk(os.path.join(parent, slug), {
        "Sections/01.md": "# One\n\naaa", "Sections/02.md": "# Two\n\nbbb",
        "Sections/03.md": "# Three\n\nccc",
        "Sources/claims.jsonl": '{"url":"u","title":"t","year":"2020","slice":"s","tier":"pub"}\n',
        "Sources/bibliography.bib": "@article{x, title={T}}\n",
    })


def _deeper_run(parent, slug):
    """deeper-research layout: sections/ (lowercase) + top-level claims.jsonl."""
    return _mk(os.path.join(parent, slug), {
        "sections/01.md": "# One\n\naaa", "sections/02.md": "# Two\n\nbbb",
        "sections/03.md": "# Three\n\nccc",
        "claims.jsonl": '{"file":"sections/01.md","sentence":"s","citations":[]}\n',
        "bibliography.bib": "@article{x, title={T}}\n",
        "round1/slice_0.jsonl": '{"url":"u"}\n',   # internal; must NOT be a source
    })


# -- qualification is by content, both layouts, any name --------------------

def test_book_layout_qualifies(tmp_path):
    d = _book_source(str(tmp_path), "ch1-q1-x")
    assert qualifies(d) == (True, "sections")


def test_deeper_research_lowercase_sections_qualifies(tmp_path):
    d = _deeper_run(str(tmp_path), "ai-impact-1-executives")
    assert qualifies(d) == (True, "sections")   # topic-slug name, lowercase sections/


def test_no_content_does_not_qualify(tmp_path):
    d = _mk(os.path.join(str(tmp_path), "empty"), {"note.txt": "x"})
    ok, reason = qualifies(d)
    assert not ok and reason == "no-content-test-passed"


def test_superseded_and_timestamped_rejected(tmp_path):
    s = _deeper_run(str(tmp_path), "topic-superseded")
    assert qualifies(s) == (False, "superseded")
    t = _deeper_run(str(tmp_path), "topic-20260101t1200z")
    assert qualifies(t) == (False, "timestamped-variant")


def test_name_pattern_restricts(tmp_path):
    d = _deeper_run(str(tmp_path), "ai-impact-1-executives")
    assert qualifies(d, name_pattern=r"ch\d+-q\d+")[0] is False
    b = _book_source(str(tmp_path), "ch2-q3-y")
    assert qualifies(b, name_pattern=r"ch\d+-q\d+") == (True, "sections")


# -- helpers -----------------------------------------------------------------

def test_sections_dir_resolves_either_case(tmp_path):
    # FS-agnostic: on a case-sensitive FS the basenames differ; on a case-insensitive
    # one (macOS APFS) they alias. Either way _sections_dir must point at the dir
    # holding the 3 section files, and its basename reads as "sections".
    from batch_ingest import find_md
    b = _book_source(str(tmp_path), "ch1-q1-x")       # created as Sections/
    assert os.path.basename(_sections_dir(b)).lower() == "sections"
    assert len(find_md(_sections_dir(b))) == 3
    dr = _deeper_run(str(tmp_path), "topic")          # created as sections/
    assert os.path.basename(_sections_dir(dr)).lower() == "sections"
    assert len(find_md(_sections_dir(dr))) == 3


def test_sources_files_from_sources_dir_or_run_root(tmp_path):
    b = _book_source(str(tmp_path), "ch1-q1-x")
    assert [os.path.basename(p) for p in _sources_files(b)] == ["bibliography.bib", "claims.jsonl"]
    dr = _deeper_run(str(tmp_path), "topic")
    assert [os.path.basename(p) for p in _sources_files(dr)] == ["bibliography.bib", "claims.jsonl"]


# -- content_hash is layout-independent for identical bytes ------------------

def test_hash_identical_across_layouts_for_same_bytes(tmp_path):
    # same section bytes + same source bytes, one in Sections/+Sources/, one in
    # sections/+top-level -> identical content hash (idempotent re-ingest either way)
    common = {"01.md": "# One\n\naaa", "02.md": "# Two\n\nbbb", "03.md": "# Three\n\nccc"}
    claims = '{"a":1}\n'
    cap = _mk(os.path.join(str(tmp_path), "cap"), {
        **{f"Sections/{k}": v for k, v in common.items()},
        "Sources/claims.jsonl": claims})
    low = _mk(os.path.join(str(tmp_path), "low"), {
        **{f"sections/{k}": v for k, v in common.items()},
        "claims.jsonl": claims})
    assert content_hash(cap) == content_hash(low)


# -- enumeration: flat deeper-research runs AND nested book corpus -----------

def test_enumerate_flat_deeper_research_runs(tmp_path):
    root = str(tmp_path / "research")
    _deeper_run(root, "ai-impact-1-executives")
    _deeper_run(root, "power-2-greene-laws")
    got = [os.path.basename(p) for p in enumerate_sources(root)]
    assert got == ["ai-impact-1-executives", "power-2-greene-laws"]  # sorted, round1/ excluded


def test_enumerate_nested_book_corpus(tmp_path):
    root = str(tmp_path / "corpus")
    _book_source(os.path.join(root, "1_Chapter 1"), "ch1-q1-a")
    _book_source(os.path.join(root, "1_Chapter 1"), "ch1-q2-b")
    got = [os.path.basename(p) for p in enumerate_sources(root)]
    assert got == ["ch1-q1-a", "ch1-q2-b"]  # chapter wrapper not counted; leaves found


def test_enumerate_mixed_and_name_pattern(tmp_path):
    root = str(tmp_path / "mixed")
    _deeper_run(root, "topic-slug-run")
    _book_source(os.path.join(root, "2_Chapter 2"), "ch2-q1-c")
    assert [os.path.basename(p) for p in enumerate_sources(root)] == ["ch2-q1-c", "topic-slug-run"]
    # restricting to book naming drops the topic-slug run
    only_book = enumerate_sources(root, name_pattern=r"ch\d+-q\d+")
    assert [os.path.basename(p) for p in only_book] == ["ch2-q1-c"]
