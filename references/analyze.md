# analyze — procedure

Cross-bible sweep. `analyze` runs in delta mode (default); `analyze --full` sweeps the whole wiki. Finds contradictions and convergences across bibles, refreshes emergent themes, and keeps the wiki healthy. Page formats from `page-templates.md`. All commands zsh-safe (use `find`/`grep`, no bare globs).

## Delta detection (the only procedure)

Scope = bibles named in `| ingest |` log lines that appear AFTER the last `| analyze |` line in `/Users/noahraford/magic/wiki/log.md`. If there is no prior `| analyze |` line, scope = every bible in the log. `--full` overrides scope to **all** bibles listed under `## Bibles` in `index.md`.

Exact delta command (field 3 of an ingest line is the bible slug):

```bash
LOG=/Users/noahraford/magic/wiki/log.md
START=$(grep -n '| analyze |' "$LOG" | tail -1 | cut -d: -f1); START=${START:-0}
awk -v s="$START" -F' \\| ' 'NR>s && $2=="ingest" {print $3}' "$LOG" | sort -u
```

Empty result (nothing ingested since the last analyze) → nothing to do; exit. For `--full`, ignore this and take every slug under `## Bibles` in `index.md` instead.

## Pass A — contradiction / convergence

For each concept/thinker page whose `bibles:` frontmatter intersects the scope AND lists ≥2 bibles, compare its per-bible `## In <bible>` sections:

- **Genuine disagreement** (the bibles make incompatible claims about the same thing) → create or update a `debates/<slug>.md` page using the debate template. The positions table must quote both sides, cite each per the citation grammar, and attribute each to its source bible via `[[bibles/<slug>]]`.
- **Genuine agreement across ≥3 bibles** → record as a theme candidate for Pass B.

## Pass B — emergent themes

Cluster the theme candidates into `themes/<slug>.md` pages (theme template). Seeds:

- If `/Users/noahraford/magic/wiki/graphify-out/graph.json` exists, read its detected communities and use them as cluster seeds. (graphify output now lives *inside* the wiki at `wiki/graphify-out/` — always run graphify with CWD `/Users/noahraford/magic/wiki`, never at `magic/` scope and never under `X_Deeper_research/`.)
- Otherwise derive clusters from frontmatter co-occurrence: pages sharing bibles in their `bibles:` list plus shared outbound wikilinks.

Graphify is an optional enhancer — never require it.

## Pass C — hygiene

Run these checks and fix the mechanical ones; queue judgment calls for the report.

- **Dangling wikilinks** (regex allows UPPERCASE — bible slugs like `ch1-q1-non-western-AI` contain capitals; exclude `reports/` and `themes` example placeholders by scanning only the page directories, not the reports):
  ```bash
  grep -rohE '\[\[[A-Za-z0-9/_-]+\]\]' \
    /Users/noahraford/magic/wiki/bibles /Users/noahraford/magic/wiki/concepts \
    /Users/noahraford/magic/wiki/thinkers /Users/noahraford/magic/wiki/debates \
    /Users/noahraford/magic/wiki/themes /Users/noahraford/magic/wiki/answers \
    --include='*.md' | sort -u
  ```
  For each link `[[<type>/<slug>]]`, confirm `test -f /Users/noahraford/magic/wiki/<type>/<slug>.md`. A miss is a dangling link — fix the link or create the missing stub. Ignore single-letter placeholder slugs (`x`, `y`) that appear only inside a page's own literal template example.
- **Orphans:** pages that never appear in the link list above (nothing links to them). Note in the report.
- **Stale stubs:** pages with `status: stub` older than the previous analyze — flag for enrichment.
- **Index ↔ frontmatter drift:** every page appears once in `index.md` under the right type with the right `(N bibles)` count; fix mismatches.
- **Alias conflicts** queued by ingest — list them for human judgment.

## Report

Write `/Users/noahraford/magic/wiki/reports/<YYYY-MM-DD>-analysis.md` with these six sections (all present, even if empty):

```markdown
# Analysis — <YYYY-MM-DD>

## New debates
## New/updated themes
## Contradictions found
## Hygiene fixes
## Alias conflicts
## Open questions the corpus cannot settle
```

The last section is the research-gap signal fed back to the deeper-research pipeline: questions the bibles raise but none can answer.

## Log + commit

Append EXACTLY one line to `/Users/noahraford/magic/wiki/log.md`:

```
YYYY-MM-DD HH:MM | analyze | scope:<delta|full> | bibles:<comma-list|all> | debates:+<n> themes:+<n> fixes:<n>
```

Concrete example (delta run over two bibles):

```
2026-08-30 14:30 | analyze | scope:delta | bibles:ch2-q4-ritual-nonhuman-powers,ch2-q8-creativity-reception | debates:+1 themes:+0 fixes:+2
```

Then commit (if the wiki repo exists): `cd /Users/noahraford/magic/wiki && git add -A && git commit -m "analyze: <YYYY-MM-DD>"`.

## Refresh the search index (automatic, last step)

Every `analyze` run ends by refreshing the semantic-search index so the new debates/themes/stubs are immediately searchable. Run it AFTER the commit (the index DB is git-ignored, so ordering vs. commit does not matter, but running last keeps the analytical work the priority):

```bash
python3 -B ~/.claude/skills/semantic-search/search.py --cwd /Users/noahraford/magic/wiki --index --quiet
```

- **`--cwd` scopes indexing to the wiki ONLY.** Never omit it and never point it at `magic/` or anything under `/Users/noahraford/magic/X_Deeper_research/` — the indexer writes a `.semantic-index.db` into its root, and doing so under the read-only bibles violates the safety invariant. The DB lands at `/Users/noahraford/magic/wiki/.semantic-index.db`, which the wiki `.gitignore` excludes.
- **Bible-corpus index (separate).** The primary-source RAG corpus lives at `/Users/noahraford/magic/wiki/.bibles-text/` (dot-prefixed, so the wiki index walker auto-skips it — the two indexes stay separate). It's built by `extract_bibles.py` from `wiki/bibles-html/` and has its OWN index: refresh with `python3 -B ~/.claude/skills/semantic-search/search.py --cwd /Users/noahraford/magic/wiki/.bibles-text --index --quiet` when the bibles change. This is the corpus that `magic/CLAUDE.md` tells free-form chat to retrieve from.
- The refresh is **incremental** (only changed files re-embed) and **non-fatal**: if it fails (e.g. no `OPENAI_API_KEY` in env or `~/.env`), note it in the run summary and continue — the analyze itself still succeeded. Search is an optional enhancer, never a gate.
- If the wiki has no `.gitignore` excluding `.semantic-index.db`, create one before the first refresh so the 13MB binary is never committed.

## Build the wiki atlas (automatic, last step)

After the search refresh, regenerate the **wiki atlas** — one self-contained, bible-styled `wiki/wiki.html` (a reading pane + an interactive, collapsible, community-colored graph navigator built from the wiki pages and `wiki/graphify-out/graph.json`). This makes every new debate/theme/page immediately browsable without Obsidian.

```bash
python3 -B ~/.claude/skills/wiki-bible/build_wiki_html.py --wiki /Users/noahraford/magic/wiki --quiet \
  || echo "[atlas] build failed — noted, continuing (analyze still succeeded)"
```

- **Non-fatal enhancer**, same contract as the search refresh: the `|| echo …` makes non-fatality mechanical — if the build fails (e.g. `markdown`/`networkx`/PyYAML missing, exit 1/2), note it in the run summary and continue; the analyze itself still succeeded.
- Output is `/Users/noahraford/magic/wiki/wiki.html` (~1 MB, git-ignored). If `graph.json` is absent it still builds, using a degraded graph from wikilinks only (no community colors).
- It reads only under `wiki/` (pages + `wiki/graphify-out/`); it never touches `X_Deeper_research/`. Community names come from `wiki/graphify-out/GRAPH_REPORT.md` (parsed at build time, since community numbering changes each run).
