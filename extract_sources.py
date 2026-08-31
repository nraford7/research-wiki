#!/usr/bin/env python3
"""Extract the bundled research sources (HTML) into clean, section-chunked
markdown for the literature-corpus RAG index.

Reads wiki/literature-html/<slug>.html (already copied from the read-only sources),
writes wiki/.literature-text/<slug>.md — headings preserved, reference apparatus
(bibliographies / citation indexes) dropped, tables flattened to pipe rows.
See docs/superpowers/specs/2026-08-30-bible-corpus-rag-design.md.
"""
import argparse
import glob
import json
import os
import re

from bs4 import BeautifulSoup

HTML_DIR = "/Users/noahraford/magic/wiki/literature-html"
OUT_DIR = "/Users/noahraford/magic/wiki/.literature-text"

# Apparatus headings: anchored at start (so "Sources (this section)" drops but
# the analytical "Internal tension the sources flag" does NOT), plus the
# unambiguous phrase "citation index" anywhere (catches "Keyed inline-citation
# index"). NOTE: never a trailing \b after "bibliograph" — "Bibliography" ends
# in a word char, so \b there fails to match.
# Apparatus headings. DROP_START is precise: bibliography-family words are always
# apparatus; "sources/references/key sources" are apparatus ONLY when followed by an
# apparatus marker — "(", ":", "cited", or end-of-heading — so "Sources (this section)"
# and "Sources cited in this section" drop, but analytical "Sources of normativity" /
# "Reference frames…" are KEPT.
DROP_START = re.compile(
    r'^\s*('
    r'bibliography|master bibliography|works cited|source record'
    r'|(?:key\s+)?sources?(?:\s*[\(:]|\s+cited\b|\s*$)'
    r'|references?(?:\s*[\(:]|\s*$)'
    r')',
    re.I)
# Unambiguous apparatus phrases wherever they appear in a heading:
# "…citation index", "…bibliograph…", the "citation integrity" verifier appendix.
DROP_ANY = re.compile(r'citation index|citation integrity|bibliograph', re.I)
# Standalone marker lines that carry no content.
SKIP_EXACT = {"source record"}


def _is_apparatus(txt):
    return bool(DROP_START.match(txt) or DROP_ANY.search(txt))


def html_to_markdown(html):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "nav"]):
        t.decompose()
    main = soup.find("main") or soup.body or soup
    out, skip = [], None
    for el in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "blockquote", "table"]):
        nm = el.name
        # avoid double-emitting content nested inside a list item / quote / table
        if nm in ("p", "li", "table") and el.find_parent(["li", "blockquote", "table"]):
            continue
        if nm == "blockquote" and el.find_parent(["blockquote"]):
            continue
        if nm[0] == "h":
            txt = el.get_text(" ", strip=True)
            lvl = int(nm[1])
            if skip is not None:
                if lvl <= skip:
                    skip = None
                else:
                    continue
            if _is_apparatus(txt):
                skip = lvl
                continue
            if txt:
                out.append("#" * lvl + " " + txt)
        elif nm == "table":
            if skip is not None:
                continue
            rows = []
            for tr in el.find_all("tr"):
                cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                if any(cells):
                    rows.append("| " + " | ".join(cells) + " |")
            if rows:
                out.append("\n".join(rows))
        else:
            if skip is not None:
                continue
            txt = el.get_text(" ", strip=True)
            if not txt or txt.lower() in SKIP_EXACT:
                continue
            out.append(("- " if nm == "li" else ("> " if nm == "blockquote" else "")) + txt)
    md = "\n\n".join(out)
    # the stripped bibliography leaves a dangling "see the bibliography at the end"
    # pointer in method-note prose; drop that clause so it doesn't mislead
    md = re.sub(r'\s*;?\s*see the bibliography at the end\.?', '', md, flags=re.I)
    return md


# --- section anchors (for concept→source-section deep-linking) --------------

# Coarse sources whose bundled HTML has headings but no section ids.
COARSE = ("ch1-q1-non-western-AI", "ch1-q2-extended-cognition",
          "ch1-q6-western-philosophy-of-mind")


def slugify(text):
    """Match the sources' own anchor scheme: 'section-' + lower, non-alnum runs -> '-'."""
    return "section-" + re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def heading_anchor(el):
    """The scroll target for a heading: its own id (minus a '-title' suffix),
    else the enclosing <section>'s id, else None."""
    hid = el.get("id")
    if hid:
        return hid[:-6] if hid.endswith("-title") else hid
    sec = el.find_parent("section")
    if sec and sec.get("id"):
        return sec["id"]
    return None


def resection_html(html):
    """Inject id='section-<slug>' on h2/h3 that lack one (for coarse sources).
    Idempotent — preserves existing ids."""
    soup = BeautifulSoup(html, "html.parser")
    # h2/h3/h4: coarse sources have very broad h2s and few <section> wrappers, so
    # finer headings must carry their own ids (else they inherit the top-of-document id)
    for el in soup.find_all(["h2", "h3", "h4"]):
        if not el.get("id"):
            txt = el.get_text(" ", strip=True)
            if txt:
                el["id"] = slugify(txt)
    return str(soup)


def extract_anchors(html):
    """List every content heading with its scroll anchor: [{heading, anchor, level}]."""
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "nav"]):
        t.decompose()
    main = soup.find("main") or soup.body or soup
    res = []
    for el in main.find_all(["h2", "h3", "h4"]):
        txt = el.get_text(" ", strip=True)
        if txt and not _is_apparatus(txt):
            res.append({"heading": txt, "anchor": heading_anchor(el), "level": int(el.name[1])})
    return res


def resection_coarse(html_dir):
    """Rewrite the coarse sources' bundled HTML in place, adding section ids."""
    for slug in COARSE:
        p = os.path.join(html_dir, slug + ".html")
        if os.path.exists(p):
            html = open(p, encoding="utf-8").read()
            open(p, "w", encoding="utf-8").write(resection_html(html))


def extract_all(html_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    anchors, n = {}, 0
    for p in sorted(glob.glob(os.path.join(html_dir, "*.html"))):
        slug = os.path.basename(p)[:-5]
        html = open(p, encoding="utf-8").read()
        md = html_to_markdown(html)
        with open(os.path.join(out_dir, slug + ".md"), "w", encoding="utf-8") as fh:
            fh.write(f"<!-- source: literature-html/{slug}.html -->\n\n# {slug}\n\n" + md + "\n")
        anchors[slug] = extract_anchors(html)
        n += 1
    with open(os.path.join(out_dir, "anchors.json"), "w", encoding="utf-8") as fh:
        json.dump(anchors, fh, indent=0)
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description="Extract sources to section-chunked markdown.")
    ap.add_argument("--html-dir", default=HTML_DIR)
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--resection", action="store_true",
                    help="inject section ids into the coarse sources' bundled HTML first")
    a = ap.parse_args(argv)
    if a.resection:
        resection_coarse(a.html_dir)
        print(f"[extract-sources] re-sectioned coarse sources in {a.html_dir}")
    n = extract_all(a.html_dir, a.out)
    print(f"[extract-sources] wrote {n} sources + anchors.json to {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
