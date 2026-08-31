# Handover — finishing the full narrative + deep-link pass

You have a working pipeline and **8 pilot concept pages** fully enriched
(narrative + Sources deep-links). This is how to finish the remaining pages so
every entry reads as a real article and links back to its source sections.

## What "done" looks like for one page

An enriched page has, in order:

1. A **standalone encyclopedic entry** that replaces the old one-line definition —
   placed between the `# Title` and the first `## In <source>` section. Length scales to
   the source: rich pages ~1,200–1,500 words; thin, single-sourced pages 500–900.
   **Never pad or invent to hit a length** — honesty over length. See the v2 house style.
2. `overview: true` in the frontmatter. (This flag tells the atlas to hide the raw
   `## In <source>` bullet sections in the reader and show a **Sources** block instead.
   The bullets stay in the markdown for Obsidian + re-ingest.)
3. A `sources: {source-slug: section-anchor}` frontmatter line (written by
   `match_sources.py`) → the atlas renders anchored deep-links to the source sections.

The `## In <source>` sections and `See also` stay in the file untouched.

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
source says".

**A source is a vessel, not a subject (hard rule).** A research source is a *container* for
evidence and argument; the prose is always about what is INSIDE it — the studies, findings,
thinkers, traditions, mechanisms — never about the container. The entry analyses the *ideas*,
never the documents that hold them. This bans every grammatical form that makes a research
document the actor, not just the bare word "source":
- **Bare / plural:** "the source(s)", "both sources", "each source", "this source".
- **Quantified** (the subtle one): "three of the sources converge", "several sources agree",
  "all the life-and-mind sources", "N of the sources say". Rewrite to the evidence itself —
  "three independent lines of evidence converge", "the autopoietic tradition holds".
- **Named-by-topic** (the other subtle one): "the extended-cognition source states…", "the
  what-is-life source pushes…", "the intelligence-without-brains source generalizes…".
  Rewrite the subject to the actual source of the claim — "Varela, Thompson and Rosch
  state…", "Maturana and Varela push the point to its limit…", "Di Paolo and Thompson
  generalize the move…".
- **Page / material as subject** (the most common real tic): "this page", "this page's
  material", "within this page's material", "on this page", "the material (here)", "the
  sourcing here", "the sources here". These frame the entry as a document about documents.
  Drop the frame and state the relation directly — "Within this page's material, X connects
  to Y" becomes "X connects to Y"; "the material treats it as settled" becomes "it is
  treated as settled" or, better, name who settles it.
- **Also banned as subjects:** "Chapter 2", "Q4/Q8", "the corpus", "the source material" /
  "the sourced material", "the sources agree/say", "position map", the
  "Camp (a)/(b)/(c)/(d)" taxonomy.

**What IS allowed as a subject** (so the rule isn't over-applied): the *content* — a topic,
an idea, a concept, an author, a tradition, a study, a school. "The concept descends from…",
"Bentham's footnote decoupled…", "the autopoietic tradition holds…", "the resemblance
heuristic explains…" are all fine. The ban is strictly on the *container* that holds the
content: source / page / material / corpus / document / chapter. Content = subject; vessel =
never. (Note the separate, unrelated style rule against opening an entry with the bare words
"This concept…" — that's about weak openings, not about container-talk.)

Attribute every claim to its real author / study / tradition and cite normally. You MAY
`[[literature/slug]]`-link, and the structured `## Evidence from the literature` section keeps its links —
but the *prose* is never a review of the literature. **The test:** if you deleted every
`[[literature/…]]` link and the corpus itself, each sentence must still read as a claim about
the world, not about a set of documents. Write "across Taoist and Confucian thought", not
"across both sources"; "one reading holds… another denies…", not "the sourced material is split".

**Length scales to source:** rich pages ~1,200–1,500 words; thin, single-sourced pages
500–900. Never pad, repeat, or invent to hit a length.

**Fidelity:** weave only from that page's existing per-source material; don't invent
facts or citations. Reuse the real author citation tokens (`[Surname, YYYY]`) — but NEVER
carry the document-pointer tokens into prose: drop `[source §N]`, `[chN-qN-…]`,
`[corpus synthesis]`, `[round2 synthesis]`, `[source synthesis]` and the like (they name the
source doc, not a claim). A few well-placed cites, not one per sentence.

**Banned** (house rules): "load-bearing", "ship/shipped", "delve", "tapestry",
"testament to", "at its core", "in essence", "it's worth noting"; document-as-subject in
ALL forms — bare ("the source(s)", "both sources", "the corpus", "the source(d) material",
"the page", "this page", "this page's material", "the material here"), quantified ("three of
the literature converge", "several sources agree", "the life-and-mind sources"), named-by-topic
("the extended-cognition source states", "the what-is-life source argues"), and locators
("Chapter N", "Q4/Q8", "Camp (a–d)", "position map", `[source §…]`, `[chN-qN…]`); no "This concept…" openings; no em-dash pile-ups; no
letter-spaced EMIR.

**Gold-standard exemplar:** the `buddha-nature` entry (~1,450 words) — match its depth
and standalone voice, scaling length to how rich each page's sourcing is.

> Note: the 8 pilots (wu-wei, enactivism, relational-ontology, panpsychism,
> basal-cognition, tacit-knowledge, creativity-as-reception, hard-problem-of-consciousness)
> predate v2 — they're book-framed and ~550w. Re-run them at v2 for consistency.

## The process (per page)

1. Read the page's full body (its definition + every `## In <source>` section).
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
python3 -B ~/.claude/skills/research-wiki/match_sources.py

# 2. rebuild the atlas (also happens automatically on /research-wiki analyze)
python3 -B ~/.claude/skills/research-wiki/build_wiki_html.py --wiki /Users/noahraford/magic/wiki --quiet
```

(If you add/adjust sources, first re-run `python3 -B ~/.claude/skills/research-wiki/extract_sources.py --resection`
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

- **Thinkers use `name:` (not `title:`) and sources use `question:`** — the tooling
  already resolves titles via a chain, but keep thinker narratives identity-first.
- **`match_sources.py` only touches `overview: true` pages** — run it *after* inserting
  narratives, not before.
- **Coarse sources** (ch1-q1, ch1-q2, ch1-q6) are re-sectioned to h2/h3/h4 so their
  deep-links are precise; don't re-bundle their HTML from source without re-running
  `--resection`.
- **Read-only sources**: never edit anything under `X_Deeper_research/`. All writes are
  under `wiki/`.
- **The atlas + corpus + graph are git-ignored** (rebuildable). Only the markdown
  pages are committed.

## Reference

- Style + mechanics origin: `docs/superpowers/{specs,plans,runs}/2026-08-30-*` in the
  magic project (the pilot, the RAG, and the deep-linking runs).
- Skill procedures: `references/ingest.md`, `references/analyze.md`,
  `references/page-templates.md`.
