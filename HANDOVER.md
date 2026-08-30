# Handover — finishing the full narrative + deep-link pass

You have a working pipeline and **8 pilot concept pages** fully enriched
(narrative + Sources deep-links). This is how to finish the remaining pages so
every entry reads as a real article and links back to its source sections.

## What "done" looks like for one page

An enriched page has, in order:

1. A **standalone encyclopedic entry** that replaces the old one-line definition —
   placed between the `# Title` and the first `## In <bible>` section. Length scales to
   the source: rich pages ~1,200–1,500 words; thin, single-sourced pages 500–900.
   **Never pad or invent to hit a length** — honesty over length. See the v2 house style.
2. `overview: true` in the frontmatter. (This flag tells the atlas to hide the raw
   `## In <bible>` bullet sections in the reader and show a **Sources** block instead.
   The bullets stay in the markdown for Obsidian + re-ingest.)
3. A `sources: {bible-slug: section-anchor}` frontmatter line (written by
   `match_sources.py`) → the atlas renders anchored deep-links to the source sections.

The `## In <bible>` sections and `See also` stay in the file untouched.

## Scope

- **Done:** 8 concepts — wu-wei, enactivism, relational-ontology, panpsychism,
  basal-cognition, tacit-knowledge, creativity-as-reception, hard-problem-of-consciousness.
- **Remaining:** ~123 concepts + ~117 thinkers under `/Users/noahraford/magic/wiki/{concepts,thinkers}/`
  that lack `overview: true`.

Find them:
```bash
cd /Users/noahraford/magic/wiki
for f in concepts/*.md thinkers/*.md; do grep -q '^overview: true' "$f" || echo "$f"; done
```

## The house style — v2 (locked 2026-08-30; supersedes the pilot style)

Write each entry as a **standalone encyclopedic analysis** of the concept — faithful
summary + how it interrelates with neighbouring ideas — usable for any exploration of
the material. **Not** a book-framed essay.

Voice: plain, intelligent, concrete — a great ideas writer for a curious
non-specialist. Common words, active voice, varied sentence length. No hedging or filler.

**Cover (as flowing prose, never as headers/checklist):** (1) what the concept IS in
depth — meaning, origin, internal distinctions; (2) how it works — structure, key
variants, the moves that make it distinctive; (3) its interrelationships — how it
connects to / depends on / contrasts with the neighbouring concepts, thinkers and
traditions in THIS page's material (name them, link with `[[concepts/slug]]` /
`[[thinkers/slug]]` — prefer slugs that appear in the page's own `## See also`); (4)
the live disagreements in the idea itself — what's contested, and by whom.

**Thinker entries:** identity-first — who they are and their central move — then their
contribution and where they're contested; same standalone, non-book-framed voice.

**No meta-framing (hard rule):** never reference "the book", "the book's question",
"a book about minds and machines", or "for a book asking/about". Never editorialize
significance ("rewires the whole question", "the whole frame shifts", "why it matters").
Analyze the ideas directly. Where the sources discuss AI / minds / machines, keep the
substance — stated as the idea itself and attributed to its author, not as "what the
bible says".

**Write about the ideas, not the source documents (hard rule):** the entry analyses the
*ideas*, never the research bibles that hold them. NEVER make a bible / document / "the page"
the subject: no "the bible(s)", "both bibles", "each bible", "this bible", "Chapter 2",
"Q4/Q8", "the corpus", "the source material" / "the sourced material", "the page", "the
sources agree/say", "position map", or the "Camp (a)/(b)/(c)/(d)" taxonomy. Attribute claims
to their real authors/traditions and cite normally. You MAY `[[bibles/slug]]`-link, but the
prose is never a review of the bibles. Write "across Taoist and Confucian thought", not
"across both bibles"; "one reading holds… another denies…", not "the sourced material is split".

**Length scales to source:** rich pages ~1,200–1,500 words; thin, single-sourced pages
500–900. Never pad, repeat, or invent to hit a length.

**Fidelity:** weave only from that page's existing per-bible material; don't invent
facts or citations. Reuse the real author citation tokens (`[Surname, YYYY]`) — but NEVER
carry the document-pointer tokens into prose: drop `[bible §N]`, `[chN-qN-…]`,
`[corpus synthesis]`, `[round2 synthesis]`, `[bible synthesis]` and the like (they name the
source doc, not a claim). A few well-placed cites, not one per sentence.

**Banned** (house rules): "load-bearing", "ship/shipped", "delve", "tapestry",
"testament to", "at its core", "in essence", "it's worth noting"; document-talk ("the
bible(s)", "both bibles", "the corpus", "the source(d) material", "the page", "Chapter N",
"Q4/Q8", "Camp (a–d)", "position map", `[bible §…]`, `[chN-qN…]`); no "This concept…"
openings; no em-dash pile-ups; no letter-spaced EMIR.

**Gold-standard exemplar:** the `buddha-nature` entry (~1,450 words) — match its depth
and standalone voice, scaling length to how rich each page's sourcing is.

> Note: the 8 pilots (wu-wei, enactivism, relational-ontology, panpsychism,
> basal-cognition, tacit-knowledge, creativity-as-reception, hard-problem-of-consciousness)
> predate v2 — they're book-framed and ~550w. Re-run them at v2 for consistency.

## The process (per page)

1. Read the page's full body (its definition + every `## In <bible>` section).
2. Draft the narrative lead per the style above.
3. Replace the text between the `# Title` line and the first `## ` heading with the
   narrative; add `overview: true` to the frontmatter. (The 8 pilots were inserted
   with a tiny script — reuse that shape: match `^(\s*#[^\n]+\n)(.*?)(\n##\s.*)$`,
   keep group 1 + `\n` + narrative + group 3.)

That's the whole per-page edit. The atlas + deep-links are then generated by the
two commands below.

## Recommended execution — batch by chapter, parallel agents

Do it in batches (e.g. one chapter's concepts at a time) so you can eyeball a batch
before spending on the rest. The efficient shape:

- Dispatch **parallel drafting agents**, ~6–8 pages each, each given the style spec
  above and told to **return** the narrative per page (JSON keyed by slug) — don't let
  them edit files, so the voice stays consistent and you review before inserting.
- Insert the narratives with the small regex script (above).
- Review one batch; if the voice is right, continue.

Or run it through **`/do-it medium`** with the instruction "enrich chapter N concepts
per HANDOVER.md style", which will spec → plan → parallel-execute → review → commit.

## After each batch — 2 commands

```bash
# 1. deep-link pointers for the newly-enriched pages (matches overview:true pages)
python3 -B ~/.claude/skills/wiki-bible/match_sources.py

# 2. rebuild the atlas (also happens automatically on /wiki-bible analyze)
python3 -B ~/.claude/skills/wiki-bible/build_wiki_html.py --wiki /Users/noahraford/magic/wiki --quiet
```

(If you add/adjust bibles, first re-run `python3 -B ~/.claude/skills/wiki-bible/extract_bibles.py --resection`
to refresh the corpus + anchors.)

## Verify a batch

```bash
cd /Users/noahraford/magic/wiki
# every enriched page has sources: and no leftover one-line-def-only pages
grep -c '^overview: true' concepts/*.md thinkers/*.md | grep -c ':1'
# deep-links resolve (spot-check): open wiki.html → click an entry → Sources → a § link
open wiki.html
```

Then commit the batch to the wiki repo:
```bash
git -C /Users/noahraford/magic/wiki add concepts/ thinkers/ && \
git -C /Users/noahraford/magic/wiki commit -m "wiki: narrative + deep-links, chapter N"
```

## Gotchas

- **Thinkers use `name:` (not `title:`) and bibles use `question:`** — the tooling
  already resolves titles via a chain, but keep thinker narratives identity-first.
- **`match_sources.py` only touches `overview: true` pages** — run it *after* inserting
  narratives, not before.
- **Coarse bibles** (ch1-q1, ch1-q2, ch1-q6) are re-sectioned to h2/h3/h4 so their
  deep-links are precise; don't re-bundle their HTML from source without re-running
  `--resection`.
- **Read-only bibles**: never edit anything under `X_Deeper_research/`. All writes are
  under `wiki/`.
- **The atlas + corpus + graph are git-ignored** (rebuildable). Only the markdown
  pages are committed.

## Reference

- Style + mechanics origin: `docs/superpowers/{specs,plans,runs}/2026-08-30-*` in the
  magic project (the pilot, the RAG, and the deep-linking runs).
- Skill procedures: `references/ingest.md`, `references/analyze.md`,
  `references/page-templates.md`.
