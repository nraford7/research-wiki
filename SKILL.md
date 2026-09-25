---
name: research-wiki
description: LLM-maintained research wiki over a research-source corpus (e.g. deeper-research output). Use when the user says /research-wiki, or asks to ingest a research source into the wiki, run a cross-source analysis (contradictions, convergences, emergent themes), or ask a question answerable from the research-source wiki. Commands - ingest <source-dir>|--all, batch <research-dir>, analyze [--full], ask <question> [--file].
---

# research-wiki

An LLM-maintained research wiki over a project's research sources. The skill is project-agnostic: it works on the wiki of whatever project it is invoked in. It follows the Karpathy "LLM wiki" pattern: interlinked plain-markdown pages that sit between the reader and the raw sources, maintained incrementally by the model, with the human as editor-in-chief. Three layers: the **raw sources** under `$SOURCES_ROOT/` are read-only sources; the **wiki** at `$WIKI_ROOT/` is the LLM-maintained set of pages (literature, concepts, thinkers, debates, themes, answers); and **this skill** is the schema plus the procedures that keep the wiki correct and current.

Sources live one or two levels deep under `$SOURCES_ROOT/` (e.g. `<run>/` or `<chapter-dir>/<source-dir>/`). The wiki compounds: each `ingest` adds a source's concepts and positions; each `analyze` finds where sources agree, disagree, and cluster into emergent themes; each `ask` orients on the accumulated pages, reads the underlying source, and can file the answer back so explorations accumulate rather than evaporate. Everything is plain markdown you can read in Obsidian.

## Reading discipline: the wiki is a MAP, the research documents are the SOURCE

For `ask` and any "read/check the wiki" request: the wiki pages (`concepts/`, `thinkers/`, `debates/`, `themes/`) are a **MAP** — distilled summaries. The full research-document text in `$WIKI_ROOT/.literature-text/*.md` is the **SOURCE**. *(Mnemonic: the wiki is the map; the research documents are the ground it maps.)* Use the map to orient and to locate the right sections, then **READ and ANSWER from the source** — never answer from a map page's summary when the source is one `Read` away. If a request looks map-only, ask the user whether they want a quick map summary or a source-grounded deep dive before answering. Full procedure in `references/ask.md`.

## Roots — resolved from the folder you are invoked in

The skill never hardcodes a project. **First step of every operation:** resolve the two roots from the current working directory:

```bash
python3 ~/.claude/skills/research-wiki/wiki_roots.py
```

It walks up from the current folder and stops at the first match: a `.research-wiki.json` (explicit `{"wiki": ..., "sources": ...}`, paths relative to that file), else a `wiki/index.md` (wiki = `<dir>/wiki`, sources = `<dir>/deeper_research`), else a folder that is itself a wiki. It prints JSON `{"project", "wiki", "sources", "via"}`.

| Placeholder | Value | What it is |
|---|---|---|
| `$WIKI_ROOT` | the resolver's `wiki` | the LLM-maintained wiki (writable) |
| `$SOURCES_ROOT` | the resolver's `sources` | the read-only research-source corpus |

**Rules:**
- State the resolved project once at the start ("Using the wiki at …").
- Substitute the literal paths into every command (the shell resets between tool calls; these are not exported variables).
- **No wiki found (exit 1):** stop and ask. Offer to bootstrap a new wiki at `<cwd>/wiki` (see First run). **Never fall back to another project's wiki.**
- **`sources` is null:** ask the user where the research sources live, then offer to write a `.research-wiki.json` in the project root so it resolves next time. Before any read-only proof, confirm `$SOURCES_ROOT` is a real directory — an empty value would make the proof pass falsely.
- The Python scripts use the same resolver as their `--wiki` default; an explicit `--wiki` always wins.

## Safety invariants

These are non-negotiable and apply to every operation:

- **READ-ONLY SOURCES.** Never write, move, or delete anything under `$SOURCES_ROOT/`. Prove it on every ingest: `touch /tmp/wb-marker` before, then after run `find $SOURCES_ROOT -newer /tmp/wb-marker -type f ! -name '.DS_Store'` — it MUST return empty. (`.DS_Store` is excluded because Finder churns those continuously; they are not content.)
- **Wikilinks are always path-qualified:** `[[concepts/liminality]]`, `[[thinkers/turner]]`, `[[literature/ch2-q4-ritual-nonhuman-powers]]` — never bare `[[liminality]]`. This removes cross-type slug collisions.
- **Citation grammar:** `[Surname, YYYY]` · multi-cite `[A, YYYY; B, YYYY]` · locator `[Surname, YYYY, ch. N | p. N | pp. N–M]`. Bracketed text that does not match this grammar is prose — carry it verbatim, never index it as a citation.
- **Merge rule is section-scoped replace:** ingesting source B writes or replaces ONLY the `## In <B>` section of a concept/thinker page; it never touches other sources' sections or the page preamble. This makes re-ingest (`--force`) safe and duplicate-free.
- **Single-session operation.** Do not run two ingests/analyzes concurrently (last-writer-wins on `log.md`).
- **Absolute paths everywhere.** Always use the `$WIKI_ROOT`/`$SOURCES_ROOT` values from the Roots table; never rely on a prior `cd` (the shell cwd resets between calls).
- **Version control is scoped to the wiki ONLY:** `git init` inside `$WIKI_ROOT`, NEVER at the project scope above it — that would place the read-only sources inside a repo whose rollback commands could write or delete under them.
- **Shell is zsh:** never use bare globs that may not match (zsh aborts the whole command on a no-match). Always use `find` with `-name`/`-iname`.

## Command dispatch

| Command | Do this |
|---|---|
| `ingest <source-dir>` / `ingest --all` | Read `references/ingest.md` and follow it exactly. |
| `analyze` / `analyze --full` | Read `references/analyze.md` and follow it exactly. |
| `batch <research-dir>` | Read `references/batch-ingest.md` and follow it exactly. Drives the full loop over a finished directory: ingest one source at a time, delta-analyze every 3, then a final `analyze --full`. Resumable; skips already-ingested and unfinished runs. |
| `ask <question>` / `ask <question> --file` | Read `references/ask.md` and follow it exactly — orient on the wiki MAP, then READ and ANSWER from the research documents (`.literature-text`), not the map summaries. If it looks map-only, ask the user first (summary vs. deep dive). |
| (any operation, for page formats) | Read `references/page-templates.md` — frontmatter, body templates, alias/slug/index rules. |

Always read the relevant reference file before acting; the procedures carry the exact commands, schemas, and templates.

## First run (bootstrap)

If the resolver finds no wiki and the user agrees to start one, create it at `<cwd>/wiki` (with sources at `<cwd>/deeper_research`, or record their real location in `<cwd>/.research-wiki.json`) before the first ingest:

```bash
mkdir -p $WIKI_ROOT/{literature,concepts,thinkers,debates,themes,answers,reports}
```

Write a skeleton `$WIKI_ROOT/index.md` with one heading per page type, in this order:

```markdown
# research-wiki index

## Literature

## Concepts

## Thinkers

## Debates

## Themes

## Answers
```

Write an empty `$WIKI_ROOT/log.md` (a single `# research-wiki log` header line is fine). Then initialise the wiki's own repo:

```bash
cd $WIKI_ROOT && git init && git add -A && git commit -m "wiki: bootstrap"
```

## Recommended cadence

- `ingest` each new source as it is finished.
- `analyze` after every 1–3 ingests; `analyze --full` when a chapter is complete. **`--full` also finishes the chapter**: it enriches every ingest-level concept/thinker page with a v2 narrative lead (`overview: true`) and re-runs graphify for fresh communities, before rebuilding the atlas (see `references/analyze.md` → Enrichment pass / graphify refresh). Delta `analyze` stays light (no enrichment).
- **`analyze` auto-refreshes semantic-search as its last step** (see `references/analyze.md`), so the wiki's search index stays current without a separate command. It always passes `--cwd $WIKI_ROOT` so indexing is scoped to the wiki ONLY. Never run semantic-search (or any indexing skill) with a working directory at or under `$SOURCES_ROOT/` — it writes a `.semantic-index.db` into its target tree, which would violate the read-only-sources invariant (there are already stray `.semantic-index.db` files under the literature from earlier misuse; do not add more). If you refresh search by hand between analyzes, pass the wiki path explicitly the same way.
- **`analyze` also auto-builds the wiki atlas as its last step** (see `references/analyze.md`): one self-contained, styled `wiki/wiki.html` — a reading pane + interactive collapsible community-colored graph — via `build_wiki_html.py`. Non-fatal enhancer; output is git-ignored (~1 MB). This is the shareable, no-Obsidian-needed view of the whole wiki.
- Optionally run `graphify` against `$WIKI_ROOT` with output at `$WIKI_ROOT/graphify-out/` (run graphify with CWD `wiki/`, use `--update` on later runs) for the community detection that both `analyze` (theme seeds) and the atlas (graph colors + cluster names) consume from `graph.json` / `GRAPH_REPORT.md`. Both `semantic-search` and `graphify` are optional enhancers, never required — the atlas degrades gracefully without the graph.
