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

- **Genuine disagreement** (the bibles make incompatible claims about the same thing) → create or update a `debates/<slug>.md` page using the debate template. The positions table must quote both sides, cite each per the citation grammar, and attribute each to its source bible via `[[bibles/<slug>]]`. **The lead must be a rich standalone synthesis, not a one-paragraph stub — see "Lead enrichment standard" below.**
- **Genuine agreement across ≥3 bibles** → record as a theme candidate for Pass B.

## Pass B — emergent themes

Cluster the theme candidates into `themes/<slug>.md` pages (theme template). Seeds:

- If `/Users/noahraford/magic/wiki/graphify-out/graph.json` exists, read its detected communities and use them as cluster seeds. (graphify output now lives *inside* the wiki at `wiki/graphify-out/` — always run graphify with CWD `/Users/noahraford/magic/wiki`, never at `magic/` scope and never under `X_Deeper_research/`.)
- Otherwise derive clusters from frontmatter co-occurrence: pages sharing bibles in their `bibles:` list plus shared outbound wikilinks.

Graphify is an optional enhancer — never require it.

Each theme page's lead must meet the **Lead enrichment standard** below — not a one-paragraph stub.

## Lead enrichment standard (required for every theme & debate)

Synthesis pages are the reader's payoff, so their **lead** — the prose between the
`# Title` and the first structural block (the positions table, or `## Evidence by bible`)
— must be a genuine standalone essay, never a single orienting paragraph. Match the
concept/thinker house style in `HANDOVER.md` (v2):

- **~400–700 words**, scaled to how much evidence/positions the page holds; never pad.
- Plain, analytical voice. **No book-framing** ("the book", "the book's question",
  "matters for the book") and no significance-editorializing. Analyze the ideas directly.
- **Write about the ideas, not the source documents** (hard rule): never make a bible /
  "the page" / "the corpus" the subject — no "both bibles", "each bible", "Chapter 2",
  "Q4/Q8", "the source(d) material", "the sources agree", "position map", "Camp (a–d)".
  Attribute claims to their real authors/traditions and cite normally; `[[bibles/slug]]`
  links are fine, but the prose is never a review of the bibles. Say "across ritual and
  creative practice", not "across both bibles".
- **Themes:** state the shared pattern precisely; show how it appears across the relevant
  traditions/domains (name them, not the source docs), drawing on the page's own
  `## Evidence by bible`; name and `[[link]]` the concepts/thinkers it unifies; close on
  the nuance or the failure mode it warns against.
- **Debates:** state the question and why it is genuinely contested; lay out the positions
  in prose (complementing, not duplicating, the table); close on what is actually
  unresolved or where the sides talk past each other.
- **Fidelity:** reuse only the real author citation tokens already present (`[Surname, YYYY]`);
  never invent, and never carry document-pointer tokens (`[bible §N]`, `[chN-qN-…]`,
  `[corpus/round2/bible synthesis]`) into the prose.
- Keep the structured sections (table / `## Evidence by bible` / `## Related` /
  `## Where the bibles agree` / `## Open questions` / `## See also`) **intact below** the lead.
- **Do NOT set `overview: true`** on themes/debates — unlike concept/thinker pages, their
  structured sections must stay visible in the atlas (only the lead is enriched, in place).

Practical splice: to enrich leads in bulk without disturbing the sections, draft each lead
as JSON `{slug: markdown}` and insert with a lead-only splice (replace title→first-`## `/`|`/`- `).

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
- **Thin synthesis leads:** any `themes/` or `debates/` page whose lead (the prose before its first `## `/table/`- ` block) is under ~250 words → it is an un-enriched stub; enrich it per the **Lead enrichment standard** above before finishing.
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
- **Front door (`about.md`).** The landing lead is the one hand-written part of the atlas. Keep it **topic-framed and extensible** — describe the intellectual territory the wiki covers (e.g. "What minds, life, and intelligence are"; "Mind in practice"), and **never organize it by the book's chapter structure** ("Chapter 1 / Chapter 2…") or hardcode counts ("seventeen bibles"). The auto sections — the provenance count line, **themes**, **live questions**, **topic clusters**, and the graph — already regenerate from whatever the corpus currently holds and scale on their own, so the lead must stay true as new questions/material are added without needing per-chapter edits.
- **Public splash (`landing.html`).** The build also emits a public gate page (title + subtitle drawn from `about.md` + an *Enter* button) beside `wiki.html`. A deploy that serves the atlas behind auth should serve `landing.html` at `/` **publicly** and inject the live credentials into its `__ATLAS_USER__` / `__ATLAS_PASSWORD__` placeholders at serve time (never commit the real password) — so visitors meet a branded page, and the atlas (`/wiki.html`) + bible pages stay behind Basic Auth. See the reference `server.js` in the deployed wiki repo.
