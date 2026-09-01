#!/usr/bin/env python3
"""Export the wiki as Obsidian-native notes: one note per page, named by its
title, with the path-qualified [[type/slug]] links rewritten to bare [[Title]]
links through an injective filename manifest.

The wiki itself keeps the [[type/slug]] grammar — the atlas builder, the
cluster validator and the procedures all depend on it. This is a one-way export
into a directory Obsidian opens directly (a vault, or a folder inside one):

    python3 -B export_obsidian.py --wiki <wiki> --out <dir> [--force] [--strict]

Exported: the literature, concept, thinker, debate, theme and answer pages,
plus the cluster essays in clusters/ as written (the atlas's generated member
lists are not reproduced). The wiki's own apparatus (index.md, log.md,
about.md, reports/) stays behind. Pages are read the way the atlas reads them
(line endings normalized to LF). --out must lie outside --wiki; the wiki is
never written to.

Filenames come from `title:` (never the slug). When two pages share a title the
ladder is: bare title -> "<title> (Debate)" / "(Theme)" / "(Cluster)" for those
types -> "<title> (<first literature slug>)" -> error. Every other frontmatter
field is copied verbatim; a `description` (the lead sentence(s), <= 150 chars)
is added unless the page already has the key.

`_manifest.json` in --out is written by and for this script:

    {"export_obsidian": 1, "pages": {"type/slug": "Title.md"}, "stale": [...]}

It is the ownership record. Filename identity is what Obsidian and APFS use
(case- and normalization-insensitive). A note is owned when the manifest
recorded its identity and exactly one file of that identity is on disk, or,
where a case-sensitive volume holds several variants, when the exact recorded
name is present. Only owned regular files are ever rewritten, renamed or
removed; every other file is refused and reported, a manifest this script did
not write is refused, and a page whose filename is refused is not exported
(links to it stay path-qualified and count as dangling). Without --force an
owned note that differs from the export is left alone, and an owned note whose
page is gone is kept (listed under "stale"); --force rewrites the former and
removes the latter. Writes go through a private temp file and os.replace, and
the manifest is written before the notes, so an interrupted run leaves owned
state that a plain rerun completes.
"""
import argparse
import glob
import json
import os
import re
import sys
import tempfile
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_wiki_html import (  # noqa: E402
    WIKI_DEFAULT, load_pages, parse_frontmatter, resolve_title,
)

MANIFEST = "_manifest.json"
MANIFEST_VERSION = 1
DESC_LIMIT = 150
# Ladder order: the types that carry their own suffix go last, so the bare
# title goes to the page most likely to be meant by [[Title]].
ORDER = ("concepts", "thinkers", "literature", "answers", "themes", "debates",
         "clusters")
RANK = {d: i for i, d in enumerate(ORDER)}
SUFFIX = {"debates": "Debate", "themes": "Theme", "clusters": "Cluster"}

FM = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.S)
LINK = re.compile(r"\[\[([^\]|#]+)(#[^\]|]*)?(\|[^\]]+)?\]\]")
MDLINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
CITE = re.compile(r"\s*\[[^\]]*\d{4}[^\]]*\]")
LABEL = re.compile(r"\*\*[^*\n]+:\*\*")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class ExportError(Exception):
    pass


def norm(s):
    return re.sub(r"[\W_]+", " ", s.casefold()).strip()


def ident(name):
    """Filename identity as Obsidian and APFS see it."""
    return unicodedata.normalize("NFC", name).casefold()


def note_name(title):
    """Title -> Obsidian-safe basename (no extension)."""
    name = CONTROL.sub("", str(title))
    name = re.sub(r"[/\\|]", "-", name)
    name = re.sub(r'[:#^\[\]?*"<>]', "", name)
    return re.sub(r"\s+", " ", name).strip(" -.")


def safe_basename(name):
    if (not isinstance(name, str) or not name or name in (".", "..")
            or name != os.path.basename(name) or CONTROL.search(name)):
        raise ExportError(f"unsafe filename {name!r} — refusing")
    return name


def load_all(wiki):
    """The atlas page set (load_pages) plus the cluster essays."""
    pages = load_pages(wiki, {})
    for p in sorted(glob.glob(os.path.join(wiki, "clusters", "*.md"))):
        stem = os.path.basename(p)[:-3]
        with open(p, encoding="utf-8") as fh:
            fm, body = parse_frontmatter(fh.read())
        pages[f"clusters/{stem}"] = {
            "title": resolve_title(fm, body, None, stem),
            "literature": [], "file": f"clusters/{stem}",
        }
    return pages


def build_manifest(pages):
    """type/slug -> filename; injective by construction or ExportError."""
    names, taken = {}, {}
    for key in sorted(pages, key=lambda k: (RANK.get(k.split("/")[0], 99), k)):
        d, title = key.split("/")[0], pages[key]["title"]
        base = note_name(title)
        if not base:
            raise ExportError(f"{key}: title {title!r} leaves no filename")
        cands = [base]
        if d in SUFFIX:
            cands.append(f"{base} ({SUFFIX[d]})")
        lits = pages[key]["literature"]
        if lits:
            cands.append(note_name(f"{base} ({lits[0]})"))
        for c in cands:
            if ident(c) not in taken:
                taken[ident(c)] = key
                names[key] = safe_basename(c + ".md")
                break
        else:
            holders = sorted({taken[ident(c)] for c in cands})
            raise ExportError(
                f"{key}: no free filename for title {title!r} — tried "
                f"{cands}, held by {holders}; retitle or add a literature slug")
    return names


def rewrite_links(body, names):
    dangling = []

    def sub(m):
        target = m.group(1).strip()
        fn = names.get(target)
        if fn is None:
            dangling.append(target)
            return m.group(0)
        return f"[[{fn[:-3]}{m.group(2) or ''}{m.group(3) or ''}]]"

    return LINK.sub(sub, body), dangling


def lead_description(body, title, titles, limit=DESC_LIMIT):
    """First sentence(s) of the first prose block, or None."""
    lead = ""
    for block in re.split(r"\n\s*\n", body):
        block = block.strip()
        if not block or block[0] in "#|<`":
            continue
        lines = [ln.strip() for ln in block.splitlines()]
        # a labelled lead line (**Core question:** ...) stands alone
        lead = lines[0] if LABEL.match(lines[0]) else " ".join(lines)
        break
    lead = LINK.sub(lambda m: (m.group(3) or "")[1:]
                    or titles.get(m.group(1).strip(), m.group(1).split("/")[-1]),
                    lead)
    lead = MDLINK.sub(r"\1", lead)
    lead = CITE.sub("", lead)
    lead = re.sub(r"[*_`]", "", lead)
    lead = re.sub(r"^[-\s]+", "", re.sub(r"\s+([.,;:?!])", r"\1", lead)).strip()
    out = ""
    for sent in re.split(r"(?<=[.!?])\s+", lead):
        if out and len(out) + 1 + len(sent) > limit:
            break
        out = f"{out} {sent}".strip()
    if len(out) > limit:
        cut = out[:limit - 1]
        cut = cut[:cut.rfind(" ")] if " " in cut else cut
        out = cut.rstrip(" ,;:—–-") + "…"
    if not out or norm(out) == norm(title):
        return None
    return out


def render(raw, names, titles, title):
    """Exported note text, dangling link targets, has-description flag."""
    m = FM.match(raw)
    front, body = (m.group(1), m.group(2)) if m else ("", raw)
    fm, _ = parse_frontmatter(raw)
    body, dangling = rewrite_links(body, names)
    has_desc = bool(fm.get("description"))
    if "description" not in fm:  # never add a second key, even to an empty one
        desc = lead_description(body, title, titles)
        if desc:
            # a JSON string is a valid YAML double-quoted scalar
            front += ("\n" if front else "") + \
                f"description: {json.dumps(desc, ensure_ascii=False)}"
            has_desc = True
    if not front:  # no frontmatter and nothing to add: copy the body as is
        return body, dangling, has_desc
    return f"---\n{front}\n---\n{body}", dangling, has_desc


def load_manifest(out):
    """(pages, stale) from an existing manifest, or ({}, []) if none.
    Anything this script did not write is refused, never treated as owned."""
    path = os.path.join(out, MANIFEST)
    if os.path.islink(path) or (os.path.exists(path)
                                and not os.path.isfile(path)):
        raise ExportError(f"{path} is not a regular file — refusing")
    if not os.path.exists(path):
        return {}, []
    try:
        with open(path, encoding="utf-8") as fh:
            m = json.load(fh)
    except (OSError, ValueError) as e:
        raise ExportError(f"{path} is not readable JSON ({e})")
    pages = m.get("pages") if isinstance(m, dict) else None
    stale = m.get("stale", []) if isinstance(m, dict) else None
    if (not isinstance(m, dict) or m.get("export_obsidian") != MANIFEST_VERSION
            or not isinstance(pages, dict) or not isinstance(stale, list)):
        raise ExportError(f"{path} was not written by export_obsidian "
                          f"(version {MANIFEST_VERSION}) — refusing to treat "
                          f"anything in {out} as owned")
    for fn in list(pages.values()) + stale:
        safe_basename(fn)
    return pages, stale


def place(fn, rec, present):
    """How the export may land `fn`, given the name the manifest recorded for
    its identity (`rec`, or None) and the on-disk names sharing that identity
    (`present`): "new", "owned", "rename" (owned under a case variant) or
    "refused". With several variants on disk (a case-sensitive volume) only the
    exact recorded name is owned, and nothing is renamed onto the others."""
    if not present:
        return "new"
    if rec is None:
        return "refused"
    if len(present) == 1:
        return "owned" if present[0] == fn else "rename"
    return "owned" if fn in present and rec == fn else "refused"


def write_atomic(path, data):
    """Write via a private temp file in the same directory, then rename."""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".export-",
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        umask = os.umask(0)
        os.umask(umask)
        os.chmod(tmp, 0o666 & ~umask)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def export(wiki, out, force=False, strict=False, log=print):
    wiki, out = os.path.realpath(wiki), os.path.realpath(out)
    if out == wiki or out.startswith(wiki + os.sep):
        raise ExportError(f"--out {out} lies inside --wiki {wiki}; the wiki "
                          f"is never written to")
    pages = load_all(wiki)
    if not pages:
        raise ExportError(f"--wiki {wiki} contains no pages")
    names = build_manifest(pages)
    titles = {k: p["title"] for k, p in pages.items()}
    prev_pages, prev_stale = load_manifest(out)
    owned = {ident(fn): fn for fn in list(prev_pages.values()) + prev_stale}

    os.makedirs(out, exist_ok=True)
    on_disk = {}
    for f in os.listdir(out):
        on_disk.setdefault(ident(f), []).append(f)
    wanted = {ident(fn) for fn in names.values()}

    def regular(name):
        p = os.path.join(out, name)
        return os.path.isfile(p) and not os.path.islink(p)

    # 1. owned files whose page is gone (exact recorded name, regular file)
    stale = sorted(fn for lo, fn in owned.items()
                   if lo not in wanted and fn in on_disk.get(lo, [])
                   and regular(fn))
    if force:
        for fn in stale:
            os.remove(os.path.join(out, fn))
            on_disk[ident(fn)].remove(fn)
            log(f"[export] removed stale owned file: {fn}")
        stale = []

    # 2. decide every landing, rename case variants, and claim the names in
    #    the manifest before any note is written
    plan, refused = {}, []
    for key in sorted(pages):
        fn = names[key]
        lo = ident(fn)
        present = on_disk.get(lo, [])
        kind = place(fn, owned.get(lo), present)
        if kind in ("owned", "rename") and not regular(
                fn if kind == "owned" else present[0]):
            kind = "refused"
        if kind == "refused":
            refused.append((key, ", ".join(present)))
            continue
        if kind == "rename":
            os.replace(os.path.join(out, present[0]), os.path.join(out, fn))
            on_disk[lo] = [fn]
            log(f"[export] renamed {present[0]} -> {fn}")
            kind = "owned"
        plan[key] = (fn, kind)
    placed = {k: fn for k, (fn, _) in plan.items()}
    manifest = {"export_obsidian": MANIFEST_VERSION, "pages": placed,
                "stale": stale}
    data = (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)
            + "\n").encode("utf-8")
    mpath = os.path.join(out, MANIFEST)
    same = False
    if os.path.exists(mpath):
        with open(mpath, "rb") as fh:
            same = fh.read() == data
    if not same:
        write_atomic(mpath, data)

    # 3. the notes; links resolve only through pages that actually land
    written = unchanged = 0
    skipped, dangling, nodesc = [], [], []
    for key in sorted(pages):
        with open(os.path.join(wiki, pages[key]["file"] + ".md"),
                  encoding="utf-8") as fh:
            raw = fh.read()
        text, dang, has_desc = render(raw, placed, titles, titles[key])
        dangling += [(key, t) for t in dang]
        if not has_desc:
            nodesc.append(key)
        if key not in plan:
            continue
        fn, kind = plan[key]
        path = os.path.join(out, fn)
        data = text.encode("utf-8")
        if kind == "owned":
            with open(path, "rb") as fh:
                if fh.read() == data:
                    unchanged += 1
                    continue
            if not force:
                skipped.append(fn)
                continue
        write_atomic(path, data)
        written += 1

    log(f"[export] {len(pages)} page(s) -> {out}: {written} written, "
        f"{unchanged} unchanged")
    for key, target in dangling:
        why = ("page not exported" if target in names else "not a page")
        log(f"[export] dangling: {key} -> [[{target}]] ({why}; left as-is)")
    if dangling:
        log(f"[export] {len(dangling)} dangling link(s) not rewritten")
    for key in nodesc:
        log(f"[export] no description for {key} (no lead, or it equals the title)")
    if skipped:
        log(f"[export] {len(skipped)} owned file(s) differ and were NOT "
            f"rewritten (rerun with --force): {', '.join(skipped)}")
    for key, what in refused:
        log(f"[export] {key} not exported: {what} in {out} is not a file "
            f"this export owns; left untouched")
    if stale:
        log(f"[export] {len(stale)} stale owned file(s) from a previous export "
            f"(--force removes them): {', '.join(stale)}")
    if skipped or refused:
        return 1
    return 1 if strict and dangling else 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Export the wiki as Obsidian-native notes "
                    "(title filenames, bare [[Title]] links).")
    ap.add_argument("--wiki", default=WIKI_DEFAULT,
                    help="wiki root (default: %(default)s)")
    ap.add_argument("--out", required=True,
                    help="target directory, outside the wiki (a vault, or a "
                         "folder inside one)")
    ap.add_argument("--force", action="store_true",
                    help="rewrite owned files that differ and remove owned "
                         "files whose page is gone; unowned files are never "
                         "touched")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any link target is not an exported page")
    a = ap.parse_args(argv)
    try:
        return export(a.wiki, a.out, force=a.force, strict=a.strict)
    except (ExportError, OSError) as e:
        print(f"[export] error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
