---
name: wiki-bible
description: LLM-maintained research wiki over the book's research bibles (X_Deeper_research). Use when the user says /wiki-bible, or asks to ingest a research bible into the wiki, run a cross-bible analysis (contradictions, convergences, emergent themes), or ask a question answerable from the research-bible wiki. Commands - ingest <bible-dir>|--all, analyze [--full], ask <question> [--file].
---

# wiki-bible

An LLM-maintained research wiki over the book's research bibles. It follows the Karpathy "LLM wiki" pattern: interlinked plain-markdown pages that sit between the reader and the raw source bibles, maintained incrementally by the model, with the human as editor-in-chief. Three layers: the **raw bibles** under `/Users/noahraford/magic/X_Deeper_research/` are read-only sources; the **wiki** at `/Users/noahraford/magic/wiki/` is the LLM-maintained set of pages (bibles, concepts, thinkers, debates, themes, answers); and **this skill** is the schema plus the procedures that keep the wiki correct and current.

The bibles live two levels deep: `X_Deeper_research/<chapter-dir>/<bible-dir>/` (e.g. `2_Chapter 2/ch2-q4-ritual-nonhuman-powers/`). The wiki compounds: each `ingest` adds a bible's concepts and positions; each `analyze` finds where bibles agree, disagree, and cluster into emergent themes; each `ask` answers from the accumulated pages and can file the answer back so explorations accumulate rather than evaporate. Everything is plain markdown you can read in Obsidian.

## Safety invariants

These are non-negotiable and apply to every operation:

- **READ-ONLY BIBLES.** Never write, move, or delete anything under `/Users/noahraford/magic/X_Deeper_research/`. Prove it on every ingest: `touch /tmp/wb-marker` before, then after run `find /Users/noahraford/magic/X_Deeper_research -newer /tmp/wb-marker -type f ! -name '.DS_Store'` — it MUST return empty. (`.DS_Store` is excluded because Finder churns those continuously; they are not content.)
- **Wikilinks are always path-qualified:** `[[concepts/liminality]]`, `[[thinkers/turner]]`, `[[bibles/ch2-q4-ritual-nonhuman-powers]]` — never bare `[[liminality]]`. This removes cross-type slug collisions.
- **Citation grammar:** `[Surname, YYYY]` · multi-cite `[A, YYYY; B, YYYY]` · locator `[Surname, YYYY, ch. N | p. N | pp. N–M]`. Bracketed text that does not match this grammar is prose — carry it verbatim, never index it as a citation.
- **Merge rule is section-scoped replace:** ingesting bible B writes or replaces ONLY the `## In <B>` section of a concept/thinker page; it never touches other bibles' sections or the page preamble. This makes re-ingest (`--force`) safe and duplicate-free.
- **Single-session operation.** Do not run two ingests/analyzes concurrently (last-writer-wins on `log.md`).
- **Absolute paths everywhere.** The wiki is always `/Users/noahraford/magic/wiki`; never rely on a prior `cd` (the shell cwd resets between calls).
- **Version control is scoped to the wiki ONLY:** `git init` inside `/Users/noahraford/magic/wiki`, NEVER at `magic/` scope — that would place the read-only bibles inside a repo whose rollback commands could write or delete under them.
- **Shell is zsh:** never use bare globs that may not match (zsh aborts the whole command on a no-match). Always use `find` with `-name`/`-iname`.

## Command dispatch

| Command | Do this |
|---|---|
| `ingest <bible-dir>` / `ingest --all` | Read `references/ingest.md` and follow it exactly. |
| `analyze` / `analyze --full` | Read `references/analyze.md` and follow it exactly. |
| `ask <question>` / `ask <question> --file` | Read `references/ask.md` and follow it exactly. |
| (any operation, for page formats) | Read `references/page-templates.md` — frontmatter, body templates, alias/slug/index rules. |

Always read the relevant reference file before acting; the procedures carry the exact commands, schemas, and templates.

## First run (bootstrap)

If `/Users/noahraford/magic/wiki/` does not exist, create it before the first ingest:

```bash
mkdir -p /Users/noahraford/magic/wiki/{bibles,concepts,thinkers,debates,themes,answers,reports}
```

Write a skeleton `/Users/noahraford/magic/wiki/index.md` with one heading per page type, in this order:

```markdown
# wiki-bible index

## Bibles

## Concepts

## Thinkers

## Debates

## Themes

## Answers
```

Write an empty `/Users/noahraford/magic/wiki/log.md` (a single `# wiki-bible log` header line is fine). Then initialise the wiki's own repo:

```bash
cd /Users/noahraford/magic/wiki && git init && git add -A && git commit -m "wiki: bootstrap"
```

## Recommended cadence

- `ingest` each new bible as it is finished.
- `analyze` after every 1–3 ingests; `analyze --full` when a chapter is complete. **`--full` also finishes the chapter**: it enriches every ingest-level concept/thinker page with a v2 narrative lead (`overview: true`) and re-runs graphify for fresh communities, before rebuilding the atlas (see `references/analyze.md` → Enrichment pass / graphify refresh). Delta `analyze` stays light (no enrichment).
- **`analyze` auto-refreshes semantic-search as its last step** (see `references/analyze.md`), so the wiki's search index stays current without a separate command. It always passes `--cwd /Users/noahraford/magic/wiki` so indexing is scoped to the wiki ONLY. Never run semantic-search (or any indexing skill) with a working directory at or under `/Users/noahraford/magic/X_Deeper_research/` — it writes a `.semantic-index.db` into its target tree, which would violate the read-only-bibles invariant (there are already stray `.semantic-index.db` files under the bibles from earlier misuse; do not add more). If you refresh search by hand between analyzes, pass the wiki path explicitly the same way.
- **`analyze` also auto-builds the wiki atlas as its last step** (see `references/analyze.md`): one self-contained, bible-styled `wiki/wiki.html` — a reading pane + interactive collapsible community-colored graph — via `build_wiki_html.py`. Non-fatal enhancer; output is git-ignored (~1 MB). This is the shareable, no-Obsidian-needed view of the whole wiki.
- Optionally run `graphify` against `/Users/noahraford/magic/wiki` with output at `/Users/noahraford/magic/wiki/graphify-out/` (run graphify with CWD `wiki/`, use `--update` on later runs) for the community detection that both `analyze` (theme seeds) and the atlas (graph colors + cluster names) consume from `graph.json` / `GRAPH_REPORT.md`. Both `semantic-search` and `graphify` are optional enhancers, never required — the atlas degrades gracefully without the graph.
