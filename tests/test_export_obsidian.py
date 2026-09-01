import hashlib
import json
import os
import re
import sys

import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import export_obsidian  # noqa: E402
from export_obsidian import main, place  # noqa: E402


# -- fixture wiki ------------------------------------------------------------

def page(w, d, slug, title, aliases, lits, body):
    (w / d).mkdir(parents=True, exist_ok=True)
    (w / d / f"{slug}.md").write_text(
        "---\n"
        f"type: {d if d == 'literature' else d[:-1]}\n"
        f"slug: {slug}\n"
        f"title: {json.dumps(title) if ':' in title else title}\n"
        f"aliases: [{', '.join(aliases)}]\n"
        f"literature: [{', '.join(lits)}]\n"
        "status: draft\n"
        "updated: 2026-08-31\n"
        "---\n\n"
        f"# {title}\n\n{body}", encoding="utf-8")


def mkwiki(tmp):
    w = tmp / "wiki"
    page(w, "concepts", "takeoff", "Takeoff",
         ["takeoff dynamics", "acceleration"], ["ch1-q1-alpha"],
         "Acceleration dynamics across both runs, per [METR, 2026a]; see "
         "[[concepts/metr-time-horizon|the METR horizon]] and "
         "[[debates/takeoff-speed]].\n\n"
         "## In ch1-q1-alpha\n\n- a [METR, 2026a]\n\n"
         "## See also\n- [[concepts/ghost]] — dangling on purpose\n")
    page(w, "concepts", "takeoff-2", "Takeoff", [], ["ch1-q2-beta"],
         "A second concept with the same title, so the literature rung is "
         "exercised.\n\n## In ch1-q2-beta\n\n- b\n")
    page(w, "concepts", "metr-time-horizon", "METR Time-Horizon", ["TH1.1"],
         ["ch1-q1-alpha"],
         "The load-bearing benchmark of the timeline debate [METR, 2026a].\n\n"
         "## In ch1-q1-alpha\n\n- doubling claim [METR, 2026a]\n\n"
         "## See also\n- [[concepts/takeoff#In ch1-q1-alpha]] — anchored\n")
    page(w, "concepts", "bare-stub", "Bare Stub", [], ["ch1-q1-alpha"], "")
    page(w, "debates", "takeoff-speed", "Takeoff", [], ["ch1-q1-alpha"],
         "Contested question colliding with the concept title on purpose.\n\n"
         "| Position | Held by | Source(s) | Key citation | Evidence |\n"
         "|---|---|---|---|---|\n"
         "| fast | [[thinkers/jane-doe]] | [[literature/ch1-q1-alpha]] "
         "| [Doe, 2025] | x |\n\n## Open questions\nSpeed.\n")
    page(w, "themes", "takeoff-theme", "Takeoff", [], ["ch1-q1-alpha"],
         "The theme across sources.\n\n## Evidence from the literature\n"
         "- [[literature/ch1-q1-alpha]] — here\n")
    page(w, "thinkers", "jane-doe", "Jane Doe", ["Doe"], ["ch1-q1-alpha"],
         "Economist of takeoff dynamics; see [[concepts/metr-time-horizon]].\n\n"
         "## In ch1-q1-alpha\n\n- c\n")
    page(w, "literature", "ch1-q1-alpha", "Alpha Report: What Is Takeoff?",
         [], ["ch1-q1-alpha"],
         "**Core question:** What is takeoff?\n"
         "**Method note:** three rounds.\n\n"
         "## Overview\nx\n\n## Pages from this source\n**Concepts**\n"
         "- [[concepts/takeoff]]\n")
    page(w, "answers", "does-takeoff-happen", "Does takeoff happen?", [], [],
         "Yes, per [[concepts/takeoff]] [METR, 2026a].\n\n"
         "## Drawn from\n- [[literature/ch1-q1-alpha]]\n")
    # cluster essays: not graph nodes, but the atlas renders them as pages
    (w / "clusters").mkdir()
    (w / "clusters" / "03-timelines.md").write_text(
        "---\ntitle: Timelines\ncommunity: 3\n---\n\n# Timelines\n\n"
        "How fast things move, per [[concepts/takeoff]] and "
        "[[concepts/metr-time-horizon]].\n")
    (w / "clusters" / "04-takeoff.md").write_text(
        "---\ntitle: Takeoff\ncommunity: 4\n---\n\n# Takeoff\n\n"
        "A cluster sharing the concept's title.\n")
    # the wiki's own apparatus is not exported
    (w / "index.md").write_text("# index\n- [[concepts/takeoff]]\n")
    (w / "log.md").write_text("# log\n")
    (w / "reports").mkdir()
    (w / "reports" / "2026-08-30-analysis.md").write_text("# report\n")
    return w


def run(tmp, *extra):
    return main(["--wiki", str(tmp / "wiki"), "--out", str(tmp / "out"),
                 *extra])


def names(out):
    # compare actual directory names — Path.exists() is case-insensitive on APFS
    return {p.name for p in out.iterdir() if p.suffix == ".md"}


def fm(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    assert m, f"no frontmatter in {path}"
    return yaml.safe_load(m.group(1)), m.group(2), text


def manifest(tmp):
    return json.loads((tmp / "out" / "_manifest.json").read_text())


def tree_hash(root):
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


ALL = {
    "Takeoff.md",                    # the concept wins the bare title
    "Takeoff (Debate).md",
    "Takeoff (Theme).md",
    "Takeoff (Cluster).md",
    "Takeoff (ch1-q2-beta).md",      # same-type collision -> literature slug
    "METR Time-Horizon.md",          # title casing preserved, not .title()
    "Bare Stub.md",
    "Jane Doe.md",
    "Alpha Report What Is Takeoff.md",   # ':' and '?' dropped
    "Does takeoff happen.md",
    "Timelines.md",
}


# -- filenames ---------------------------------------------------------------

def test_filenames_come_from_title_with_collision_suffixes(tmp_path):
    mkwiki(tmp_path)
    assert run(tmp_path) == 0
    assert names(tmp_path / "out") == ALL


def test_unresolvable_collision_fails_before_writing(tmp_path):
    w = mkwiki(tmp_path)
    page(w, "concepts", "takeoff-3", "Takeoff", [], [],
         "No literature list, so no rung is left.\n")
    assert run(tmp_path) != 0
    assert not (tmp_path / "out").exists()


def test_missing_or_empty_wiki_fails(tmp_path):
    assert main(["--wiki", str(tmp_path / "nope"),
                 "--out", str(tmp_path / "out")]) != 0
    (tmp_path / "empty" / "concepts").mkdir(parents=True)
    assert main(["--wiki", str(tmp_path / "empty"),
                 "--out", str(tmp_path / "out")]) != 0
    assert not (tmp_path / "out").exists()


def test_out_inside_wiki_is_refused(tmp_path):
    w = mkwiki(tmp_path)
    before = tree_hash(w)
    for out in (w, w / "concepts", w / "export"):
        assert main(["--wiki", str(w), "--out", str(out)]) != 0
    assert tree_hash(w) == before
    assert not (w / "export").exists()


# -- links -------------------------------------------------------------------

def test_links_rewritten_through_manifest(tmp_path):
    mkwiki(tmp_path)
    run(tmp_path)
    out = tmp_path / "out"
    _, _, takeoff = fm(out / "Takeoff.md")
    assert "[[METR Time-Horizon|the METR horizon]]" in takeoff   # alias kept
    assert "[[Takeoff (Debate)]]" in takeoff                     # suffixed target
    _, _, debate = fm(out / "Takeoff (Debate).md")
    assert "[[Jane Doe]]" in debate
    assert "[[Alpha Report What Is Takeoff]]" in debate
    _, _, metr = fm(out / "METR Time-Horizon.md")
    assert "[[Takeoff#In ch1-q1-alpha]]" in metr                 # anchor kept
    _, _, cluster = fm(out / "Timelines.md")
    assert "[[Takeoff]] and [[METR Time-Horizon]]" in cluster


def test_dangling_link_left_as_is_and_reported(tmp_path, capsys):
    mkwiki(tmp_path)
    assert run(tmp_path) == 0
    out = tmp_path / "out"
    _, _, takeoff = fm(out / "Takeoff.md")
    assert "[[concepts/ghost]]" in takeoff
    assert "concepts/ghost" in capsys.readouterr().out
    # the reported one is the ONLY path-qualified link left in the export
    left = [(p.name, m) for p in out.glob("*.md")
            for m in re.findall(r"\[\[[a-z]+/[^\]|#]+", p.read_text())]
    assert left == [("Takeoff.md", "[[concepts/ghost")]


def test_strict_exits_nonzero_on_dangling_link(tmp_path):
    mkwiki(tmp_path)
    assert run(tmp_path, "--strict") != 0
    # strict does not stop the export itself
    assert names(tmp_path / "out") == ALL


# -- frontmatter -------------------------------------------------------------

def test_frontmatter_kept_verbatim_and_description_added(tmp_path):
    mkwiki(tmp_path)
    run(tmp_path)
    meta, body, text = fm(tmp_path / "out" / "Takeoff.md")
    assert "aliases: [takeoff dynamics, acceleration]\n" in text  # verbatim
    assert meta["aliases"] == ["takeoff dynamics", "acceleration"]
    assert meta["type"] == "concept" and meta["slug"] == "takeoff"
    assert meta["literature"] == ["ch1-q1-alpha"]
    assert meta["status"] == "draft" and str(meta["updated"]) == "2026-08-31"
    assert 0 < len(meta["description"]) <= 150
    assert meta["description"] != meta["title"]
    assert meta["description"].startswith("Acceleration dynamics")
    assert "[[" not in meta["description"] and "[METR" not in meta["description"]
    assert body.startswith("\n# Takeoff\n")                       # body untouched
    cluster, _, _ = fm(tmp_path / "out" / "Timelines.md")
    assert cluster["community"] == 3                              # kept as written


def test_description_skips_table_and_lead_label(tmp_path):
    mkwiki(tmp_path)
    run(tmp_path)
    debate, _, _ = fm(tmp_path / "out" / "Takeoff (Debate).md")
    assert debate["description"].startswith("Contested question")
    lit, _, _ = fm(tmp_path / "out" / "Alpha Report What Is Takeoff.md")
    assert lit["description"] == "Core question: What is takeoff?"


def test_page_without_a_lead_gets_no_description(tmp_path, capsys):
    mkwiki(tmp_path)
    run(tmp_path)
    meta, _, _ = fm(tmp_path / "out" / "Bare Stub.md")
    assert "description" not in meta
    assert "concepts/bare-stub" in capsys.readouterr().out


def test_description_is_valid_yaml_when_it_has_quotes_and_colons(tmp_path):
    w = mkwiki(tmp_path)
    page(w, "concepts", "quoted", "Quoted", [], ["ch1-q1-alpha"],
         'He said: "it\'s a #tag, not a: key" — really.\n')
    assert run(tmp_path) == 0
    meta, _, _ = fm(tmp_path / "out" / "Quoted.md")
    assert meta["description"] == 'He said: "it\'s a #tag, not a: key" — really.'


def test_description_never_exceeds_150_characters(tmp_path):
    w = mkwiki(tmp_path)
    page(w, "concepts", "long", "Long", [], ["ch1-q1-alpha"], "x" * 200 + "\n")
    page(w, "concepts", "sentences", "Sentences", [], ["ch1-q1-alpha"],
         "First sentence is short. " + "Second sentence is long " * 8 + "end.\n")
    run(tmp_path)
    long, _, _ = fm(tmp_path / "out" / "Long.md")
    assert len(long["description"]) <= 150 and long["description"].endswith("…")
    sent, _, _ = fm(tmp_path / "out" / "Sentences.md")
    assert sent["description"] == "First sentence is short."


def test_non_latin_description_is_kept(tmp_path):
    w = mkwiki(tmp_path)
    page(w, "concepts", "wu-wei-ja", "無為", [], ["ch1-q1-alpha"],
         "無為とは作為のない行為である。\n")
    run(tmp_path)
    meta, _, _ = fm(tmp_path / "out" / "無為.md")
    assert meta["description"] == "無為とは作為のない行為である。"


def test_bold_opening_is_not_a_label(tmp_path):
    w = mkwiki(tmp_path)
    page(w, "concepts", "wu-wei", "Wu-Wei", [], ["ch1-q1-alpha"],
         "**Wu-wei** is effortless\naction. Second sentence.\n")
    run(tmp_path)
    meta, _, _ = fm(tmp_path / "out" / "Wu-Wei.md")
    assert meta["description"] == "Wu-wei is effortless action. Second sentence."


def test_page_without_frontmatter(tmp_path):
    w = mkwiki(tmp_path)
    (w / "concepts" / "lone.md").write_text("# Lone\n\nJust a body.\n")
    (w / "concepts" / "bare.md").write_text("# Bare\n")
    assert run(tmp_path) == 0
    assert (tmp_path / "out" / "Lone.md").read_text() == \
        '---\ndescription: "Just a body."\n---\n# Lone\n\nJust a body.\n'
    # nothing to add -> the body is copied as it is, no empty frontmatter block
    assert (tmp_path / "out" / "Bare.md").read_text() == "# Bare\n"


# -- manifest, idempotence, ownership ---------------------------------------

def test_manifest_maps_key_to_filename(tmp_path):
    mkwiki(tmp_path)
    run(tmp_path)
    m = manifest(tmp_path)
    assert m["export_obsidian"] == 1
    assert m["pages"]["concepts/takeoff"] == "Takeoff.md"
    assert m["pages"]["debates/takeoff-speed"] == "Takeoff (Debate).md"
    assert m["pages"]["clusters/03-timelines"] == "Timelines.md"
    assert m["pages"]["literature/ch1-q1-alpha"] == "Alpha Report What Is Takeoff.md"
    assert set(m["pages"].values()) == names(tmp_path / "out")
    assert m["stale"] == []
    assert not any(k in ("index", "log") or k.startswith("reports/")
                   for k in m["pages"])


def test_rerun_is_byte_identical_and_wiki_untouched(tmp_path):
    mkwiki(tmp_path)
    before = tree_hash(tmp_path / "wiki")
    assert run(tmp_path) == 0
    first = tree_hash(tmp_path / "out")
    assert run(tmp_path) == 0
    assert tree_hash(tmp_path / "out") == first
    assert tree_hash(tmp_path / "wiki") == before
    assert not list((tmp_path / "out").glob("*.tmp"))


def test_unowned_file_is_never_touched(tmp_path, capsys):
    mkwiki(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "Jane Doe.md").write_text("# my own note\n")
    assert run(tmp_path) != 0
    assert (out / "Jane Doe.md").read_text() == "# my own note\n"
    assert "Jane Doe.md" in capsys.readouterr().out
    assert run(tmp_path, "--force") != 0
    assert (out / "Jane Doe.md").read_text() == "# my own note\n"
    # the rest of the export still landed, and the manifest does not claim it
    assert "Takeoff.md" in names(out)
    assert "thinkers/jane-doe" not in manifest(tmp_path)["pages"]


def test_unowned_file_collision_is_case_insensitive(tmp_path):
    mkwiki(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "jane doe.md").write_text("# my own note\n")
    assert run(tmp_path, "--force") != 0
    assert (out / "jane doe.md").read_text() == "# my own note\n"
    assert "Jane Doe.md" not in names(out)


def test_owned_file_is_rewritten_only_with_force(tmp_path, capsys):
    mkwiki(tmp_path)
    run(tmp_path)
    f = tmp_path / "out" / "Takeoff.md"
    exported = f.read_text()
    f.write_text(exported + "\nhand edit\n")
    assert run(tmp_path) != 0
    assert f.read_text().endswith("hand edit\n")
    assert "--force" in capsys.readouterr().out
    assert run(tmp_path, "--force") == 0
    assert f.read_text() == exported


def test_force_removes_stale_owned_files(tmp_path, capsys):
    w = mkwiki(tmp_path)
    run(tmp_path)
    (w / "thinkers" / "jane-doe.md").unlink()
    # without --force: the stale file stays, and the debate page that linked
    # to it now differs, so the run is reported incomplete
    assert run(tmp_path) == 1
    assert (tmp_path / "out" / "Jane Doe.md").exists()
    assert "Jane Doe.md" in capsys.readouterr().out
    m = manifest(tmp_path)
    assert "thinkers/jane-doe" not in m["pages"]
    assert m["stale"] == ["Jane Doe.md"]                     # still owned
    assert run(tmp_path, "--force") == 0
    assert not (tmp_path / "out" / "Jane Doe.md").exists()
    assert manifest(tmp_path)["stale"] == []


def test_case_only_retitle_keeps_one_owned_file(tmp_path):
    w = mkwiki(tmp_path)
    run(tmp_path)
    p = w / "concepts" / "takeoff.md"
    p.write_text(p.read_text().replace("title: Takeoff\n", "title: TAKEOFF\n"))
    assert run(tmp_path) == 1                      # content differs -> --force
    assert "TAKEOFF.md" in names(tmp_path / "out")  # renamed, never duplicated
    assert "Takeoff.md" not in names(tmp_path / "out")
    assert run(tmp_path, "--force") == 0
    assert "TAKEOFF.md" in names(tmp_path / "out")
    assert "Takeoff.md" not in names(tmp_path / "out")
    assert manifest(tmp_path)["pages"]["concepts/takeoff"] == "TAKEOFF.md"
    meta, _, _ = fm(tmp_path / "out" / "TAKEOFF.md")
    assert meta["title"] == "TAKEOFF"


def test_foreign_manifest_is_refused(tmp_path):
    mkwiki(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "Journal.md").write_text("mine\n")
    (out / "_manifest.json").write_text(json.dumps({"other": "Journal.md"}))
    assert run(tmp_path, "--force") != 0
    assert (out / "Journal.md").read_text() == "mine\n"
    assert names(out) == {"Journal.md"}


@pytest.mark.parametrize("bad", [
    '["Takeoff.md"]',
    '{"export_obsidian": 2, "pages": {}}',
    '{"export_obsidian": 1, "pages": {"concepts/takeoff": 3}}',
    '{"export_obsidian": 1, "pages": {}, "stale": "Takeoff.md"}',
    '{"export_obsidian": 1, "pages": {"thinkers/gone": "../victim.md"}}',
    '{"export_obsidian": 1, "pages": {}, "stale": ["../victim.md"]}',
    '{"export_obsidian": 1, "pages": {',
])
def test_malformed_manifest_is_refused_before_any_write(tmp_path, bad):
    mkwiki(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    victim = tmp_path / "victim.md"
    victim.write_text("keep me\n")
    (out / "_manifest.json").write_text(bad)
    assert run(tmp_path, "--force") == 2
    assert names(out) == set()
    assert victim.read_text() == "keep me\n"
    assert (out / "_manifest.json").read_text() == bad


def test_interrupted_run_leaves_owned_state_and_recovers(tmp_path, monkeypatch):
    mkwiki(tmp_path)
    real = export_obsidian.write_atomic
    calls = []

    def flaky(path, data):
        calls.append(path)
        if len(calls) == 3:
            raise OSError("disk full")
        real(path, data)

    monkeypatch.setattr(export_obsidian, "write_atomic", flaky)
    assert run(tmp_path) == 2
    m = manifest(tmp_path)                     # claimed before any note
    assert set(m["pages"].values()) == ALL
    assert len(names(tmp_path / "out")) < len(ALL)
    monkeypatch.setattr(export_obsidian, "write_atomic", real)
    assert run(tmp_path) == 0                  # plain rerun completes it
    assert names(tmp_path / "out") == ALL


# -- ownership hazards -------------------------------------------------------

def test_place_decisions_are_exact_name_based():
    # (wanted name, name the manifest recorded for this identity, names on
    # disk sharing the identity) -> what the export may do
    assert place("Takeoff.md", None, []) == "new"
    assert place("Takeoff.md", "Takeoff.md", ["Takeoff.md"]) == "owned"
    assert place("Takeoff.md", None, ["Takeoff.md"]) == "refused"
    assert place("TAKEOFF.md", "Takeoff.md", ["Takeoff.md"]) == "rename"
    assert place("TAKEOFF.md", None, ["Takeoff.md"]) == "refused"
    # a case-sensitive volume can hold both: the exact owned name is usable,
    # but nothing may ever be renamed onto the other one
    assert place("Takeoff.md", "Takeoff.md", ["Takeoff.md", "TAKEOFF.md"]) \
        == "owned"
    assert place("TAKEOFF.md", "Takeoff.md", ["Takeoff.md", "TAKEOFF.md"]) \
        == "refused"


def test_tmp_and_symlink_paths_are_never_used_or_followed(tmp_path):
    mkwiki(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    victim = tmp_path / "victim.md"
    victim.write_text("keep me\n")
    (out / "Takeoff.md.tmp").write_text("someone else's tmp\n")
    (out / "_manifest.json.tmp").symlink_to(victim)
    assert run(tmp_path) == 0
    assert (out / "Takeoff.md.tmp").read_text() == "someone else's tmp\n"
    assert victim.read_text() == "keep me\n"
    assert (out / "_manifest.json.tmp").is_symlink()
    assert not list(out.glob(".export-*"))
    # an owned name that has become a symlink is not a regular owned file
    (out / "Jane Doe.md").unlink()
    (out / "Jane Doe.md").symlink_to(victim)
    assert run(tmp_path, "--force") == 1
    assert (out / "Jane Doe.md").is_symlink()
    assert victim.read_text() == "keep me\n"


def test_unicode_variant_of_unowned_file_is_refused(tmp_path):
    w = mkwiki(tmp_path)
    page(w, "concepts", "cafe", "Caf\u00e9", [], ["ch1-q1-alpha"], "Coffee.\n")
    out = tmp_path / "out"
    out.mkdir()
    nfd = out / "Cafe\u0301.md"
    nfd.write_text("mine\n")
    assert run(tmp_path, "--force") == 1
    assert nfd.read_text() == "mine\n"
    assert "concepts/cafe" not in manifest(tmp_path)["pages"]
    assert len(names(out)) == len(ALL) + 1


def test_unsafe_literature_slug_cannot_escape_out(tmp_path):
    w = mkwiki(tmp_path)
    page(w, "concepts", "takeoff-evil", "Takeoff", [], ["../evil"],
         "A page whose provenance slug is not a plain slug.\n")
    assert run(tmp_path) == 0
    assert "Takeoff (..-evil).md" in names(tmp_path / "out")
    assert not (tmp_path / "evil.md").exists()
    assert not (tmp_path / "Takeoff (").exists()
    assert all(os.sep not in fn for fn in manifest(tmp_path)["pages"].values())


def test_links_to_a_refused_page_stay_path_qualified(tmp_path, capsys):
    mkwiki(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "Jane Doe.md").write_text("# my own note\n")
    assert run(tmp_path) == 1
    _, _, debate = fm(out / "Takeoff (Debate).md")
    assert "[[thinkers/jane-doe]]" in debate          # not pointed at my note
    assert "[[Jane Doe]]" not in debate
    assert "thinkers/jane-doe" in capsys.readouterr().out


def test_existing_empty_description_key_is_not_duplicated(tmp_path, capsys):
    w = mkwiki(tmp_path)
    p = w / "concepts" / "takeoff.md"
    p.write_text(p.read_text().replace("status: draft\n",
                                       "status: draft\ndescription:\n"))
    run(tmp_path)
    meta, _, text = fm(tmp_path / "out" / "Takeoff.md")
    assert text.count("\ndescription:") == 1
    assert meta.get("description") is None
    assert "concepts/takeoff" in capsys.readouterr().out


def test_symlinked_manifest_is_refused(tmp_path):
    mkwiki(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    other = tmp_path / "other-manifest.json"
    other.write_text(json.dumps({"export_obsidian": 1,
                                 "pages": {"thinkers/x": "Journal.md"}}))
    (out / "Journal.md").write_text("mine\n")
    (out / "_manifest.json").symlink_to(other)
    assert run(tmp_path, "--force") == 2
    assert (out / "Journal.md").read_text() == "mine\n"
    assert (out / "_manifest.json").is_symlink()
    assert names(out) == {"Journal.md"}


def test_control_characters_never_reach_the_filesystem(tmp_path):
    w = mkwiki(tmp_path)
    title = "Bad" + chr(0) + "Ti" + chr(1) + "tle" + chr(127)
    (w / "concepts" / "nul.md").write_text(
        "---\ntype: concept\nslug: nul\ntitle: " + json.dumps(title)
        + "\nliterature: [ch1-q1-alpha]\n---\n\n# Bad Title\n\n"
        "A title with control characters, escaped in the YAML.\n")
    assert run(tmp_path) == 0
    assert "BadTitle.md" in names(tmp_path / "out")
    (tmp_path / "out" / "_manifest.json").write_text(json.dumps(
        {"export_obsidian": 1,
         "pages": {"concepts/x": "Bad" + chr(1) + ".md"}}))
    assert run(tmp_path, "--force") == 2
