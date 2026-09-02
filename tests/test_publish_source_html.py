import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from publish_source_html import scrub, publish_one, DELIVERABLE  # noqa: E402


# -- scrub: the deliverable name is replaced, case-preserving, spaced or hyphenated ----

def test_scrub_replaces_title_case_deliverable():
    assert scrub("<h2>Research Bible</h2>") == "<h2>Research Report</h2>"


def test_scrub_replaces_lowercase_hyphenated_leak():
    # a leaked CSS class/id like class="research-bible" must be fixed too
    assert scrub('<div class="research-bible">') == '<div class="research-report">'


def test_scrub_preserves_upper_case():
    assert scrub("RESEARCH BIBLE") == "RESEARCH REPORT"


def test_scrub_keeps_research_word_case_and_separator():
    # "research" and the separator carry through verbatim; only "bible"->"report" recases
    assert scrub("research-Bible") == "research-Report"


# -- scrub leaves the bare English word "bible" (content) untouched --------------------

def test_scrub_leaves_standalone_bible_prose():
    prose = "the sociopath's bible, the confiscated contraband"
    assert scrub(prose) == prose


def test_scrub_leaves_cited_source_title_with_bible():
    title = "I'm Reading the Bible of Patriarchy"
    assert scrub(title) == title


# -- publish gate: content "bible" publishes; a deliverable-name leak is refused -------

def _write_export(tmp_path, slug, body):
    d = tmp_path / slug
    d.mkdir()
    (d / f"RESEARCH-REPORT_{slug}.html").write_text(f"<html><body>{body}</body></html>")
    return str(d)


def test_publish_allows_content_bible(tmp_path):
    # the real power-2-greene-laws failure mode: prose "bible" + a cited "Bible of Patriarchy"
    body = ("<p>the sociopath's bible, the confiscated contraband</p>"
            "<p>I'm Reading the Bible of Patriarchy "
            "(cockyventures.substack.com/p/im-reading-the-bible-of-patriarchy)</p>")
    src = _write_export(tmp_path, "power-2-greene-laws", body)
    wiki = tmp_path / "wiki"
    slug, status = publish_one(src, str(wiki))
    assert status == "published"
    out = (wiki / "literature-html" / "power-2-greene-laws.html").read_text()
    assert "sociopath's bible" in out          # content preserved verbatim
    assert "Bible of Patriarchy" in out


def test_gate_pattern_flags_deliverable_name_not_content():
    # The gate/scrub pattern: matches the deliverable name in either form, never bare "bible".
    assert DELIVERABLE.search("Research Bible")
    assert DELIVERABLE.search('class="research-bible"')
    assert DELIVERABLE.search("RESEARCH BIBLE")
    assert not DELIVERABLE.search("the sociopath's bible")
    assert not DELIVERABLE.search("Bible of Patriarchy")


def test_publish_refuses_when_scrub_bypassed(monkeypatch, tmp_path):
    # The gate is the safety net: if scrub ever fails to remove the deliverable term,
    # publish_one must still refuse rather than write it. Simulate a scrub that no-ops.
    import publish_source_html as mod
    monkeypatch.setattr(mod, "scrub", lambda html: html)
    src = _write_export(tmp_path, "ch1-q1-x", "<footer>Research Bible</footer>")
    slug, status = mod.publish_one(src, str(tmp_path / "wiki"))
    assert status == "REFUSED-bible-survived"


def test_publish_scrubbed_deliverable_then_publishes(tmp_path):
    # a normal "Research Bible" stamp is scrubbed to "Research Report" and publishes
    src = _write_export(tmp_path, "ch1-q2-y", "<div class='kicker'>Research Bible</div>")
    wiki = tmp_path / "wiki"
    slug, status = publish_one(src, str(wiki))
    assert status == "published"
    out = (wiki / "literature-html" / "ch1-q2-y.html").read_text()
    assert "Research Report" in out
    assert "Research Bible" not in out
