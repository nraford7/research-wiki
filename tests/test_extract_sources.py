import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extract_sources import (  # noqa: E402
    extract_all, extract_anchors, html_to_markdown, resection_html, slugify,
)


def test_slugify_matches_source_anchor_scheme():
    assert slugify("The paradox of wu wei and its proposed resolutions") == \
        "section-the-paradox-of-wu-wei-and-its-proposed-resolutions"
    assert slugify("Wu wei in the brain: Slingerland's cognitive-science") == \
        "section-wu-wei-in-the-brain-slingerland-s-cognitive-science"


def test_resection_injects_ids_on_h2_and_h3_where_missing():
    html = ('<main><h2>Alpha Beta</h2><p>x</p><h3>Gamma Delta</h3>'
            '<h2 id="section-keep">Keep</h2></main>')
    out = resection_html(html)
    assert 'id="section-alpha-beta"' in out
    assert 'id="section-gamma-delta"' in out
    assert out.count('id="section-keep"') == 1


def test_extract_anchors_reads_section_wrapper_and_strips_title():
    html = ('<main><section id="section-foo"><h2 id="section-foo-title">Foo</h2></section>'
            '<h3>Sub</h3></main>')
    a = extract_anchors(html)
    foo = [x for x in a if x["heading"] == "Foo"][0]
    assert foo["anchor"] == "section-foo" and foo["level"] == 2
    sub = [x for x in a if x["heading"] == "Sub"][0]
    assert sub["anchor"] is None


def test_headings_and_paragraphs():
    md = html_to_markdown("<main><h1>T</h1><h2>Sec</h2><p>Alpha beta.</p></main>")
    assert "# T" in md and "## Sec" in md and "Alpha beta." in md


def test_drops_real_bibliography_heading_and_subtree():
    md = html_to_markdown(
        "<main><h2>Argument</h2><p>keep this</p>"
        "<h2>Bibliography</h2><p>Smith 2020</p><h3>More refs</h3><p>Jones 2019</p>"
        "<h2>Conclusion</h2><p>keep too</p></main>")
    assert "keep this" in md and "keep too" in md
    assert "Smith 2020" not in md and "Jones 2019" not in md and "Bibliography" not in md


def test_apparatus_variants_drop_but_analytical_sources_heading_stays():
    md = html_to_markdown(
        "<main><h3>Sources (this section)</h3><p>Ref A 2020</p>"
        "<h3>Keyed inline-citation index</h3><p>k1 = X</p>"
        "<h3>Internal tension the sources flag</h3><p>real analysis here</p></main>")
    assert "Ref A 2020" not in md and "k1 = X" not in md            # apparatus dropped
    assert "real analysis here" in md                               # analytical heading kept
    assert "Internal tension the sources flag" in md


def test_drops_prefixed_bibliography_heading():
    md = html_to_markdown(
        "<main><h3>⚠ Unresolved bibliography entries</h3><p>Doe 2001, n.p.</p>"
        "<h2>Next</h2><p>keep</p></main>")
    assert "Doe 2001" not in md and "bibliography" not in md.lower()
    assert "keep" in md


def test_sibling_citation_integrity_appendix_dropped():
    # ch1-q6 shape: bibliography h2, then a NON-matching apparatus h2 sibling
    md = html_to_markdown(
        "<main><h2>Argument</h2><p>keep me</p>"
        "<h2>Master Bibliography</h2><p>Smith 2020</p>"
        "<h2>Appendix: Citation integrity (mechanical verification)</h2>"
        "<h3>Weak title match</h3><p>match 0.25, openalex</p></main>")
    assert "keep me" in md
    assert "openalex" not in md and "Smith 2020" not in md and "Citation integrity" not in md


def test_analytical_sources_references_headings_kept():
    # over-drop guard: these START with sources/references but are analytical
    md = html_to_markdown(
        "<main><h3>Sources of normativity</h3><p>alpha analysis</p>"
        "<h3>Reference frames in physics</h3><p>beta analysis</p></main>")
    assert "alpha analysis" in md and "beta analysis" in md
    assert "Sources of normativity" in md and "Reference frames in physics" in md


def test_standalone_source_record_marker_dropped():
    md = html_to_markdown("<main><p>real body</p><p>Source record</p></main>")
    assert "real body" in md and "Source record" not in md


def test_table_rows_preserved():
    md = html_to_markdown("<main><table><tr><th>Position</th><th>Outcome</th></tr>"
                          "<tr><td>Dualism</td><td>gap</td></tr></table></main>")
    assert "Position" in md and "Dualism" in md and "gap" in md


def test_strips_script_style():
    md = html_to_markdown("<main><script>x=1</script><style>a{}</style><p>real</p></main>")
    assert "x=1" not in md and "a{}" not in md and "real" in md


def test_extract_all_writes_one_md_per_html(tmp_path):
    html_dir = tmp_path / "h"
    html_dir.mkdir()
    (html_dir / "ch9-x.html").write_text("<main><h1>Q</h1><p>body text here</p></main>")
    out = tmp_path / "out"
    n = extract_all(str(html_dir), str(out))
    assert n == 1 and (out / "ch9-x.md").exists()
    assert "body text here" in (out / "ch9-x.md").read_text()
