# analyze — procedure

Cross-source sweep. `analyze` runs in delta mode (default); `analyze --full` sweeps the whole wiki. Finds contradictions and convergences across sources, refreshes emergent themes, and keeps the wiki healthy. Page formats from `page-templates.md`. All commands zsh-safe (use `find`/`grep`, no bare globs).

## Delta detection (the only procedure)

Scope = sources named in `| ingest |` log lines that appear AFTER the last `| analyze |` line in `/Users/noahraford/magic/wiki/log.md`. If there is no prior `| analyze |` line, scope = every source in the log. `--full` overrides scope to **all** sources listed under `## Literature` in `index.md`.

Exact delta command (field 3 of an ingest line is the source slug):

```bash
LOG=/Users/noahraford/magic/wiki/log.md
START=$(grep -n '| analyze |' "$LOG" | tail -1 | cut -d: -f1); START=${START:-0}
awk -v s="$START" -F' \\| ' 'NR>s && $2=="ingest" {print $3}' "$LOG" | sort -u
```

Empty result (nothing ingested since the last analyze) → nothing to do; exit. For `--full`, ignore this and take every slug under `## Literature` in `index.md` instead.

## Pass A — contradiction / convergence

For each concept/thinker page whose `sources:` frontmatter intersects the scope AND lists ≥2 sources, compare its per-source `## In <source>` sections:

- **Genuine disagreement** (the sources make incompatible claims about the same thing) → create or update a `debates/<slug>.md` page using the debate template. The positions table must quote both sides, cite each per the citation grammar, and attribute each to its source via `[[literature/<slug>]]`. **The lead must be a rich standalone synthesis, not a one-paragraph stub — see "Lead enrichment standard" below.**
- **Genuine agreement across ≥3 sources** → record as a theme candidate for Pass B.

## Pass B — emergent themes

Cluster the theme candidates into `themes/<slug>.md` pages (theme template). Seeds:

- If `/Users/noahraford/magic/wiki/graphify-out/graph.json` exists, read its detected communities and use them as cluster seeds. (graphify output now lives *inside* the wiki at `wiki/graphify-out/` — always run graphify with CWD `/Users/noahraford/magic/wiki`, never at `magic/` scope and never under `X_Deeper_research/`.)
- Otherwise derive clusters from frontmatter co-occurrence: pages sharing sources in their `sources:` list plus shared outbound wikilinks.

Graphify is an optional enhancer — never require it.

Each theme page's lead must meet the **Lead enrichment standard** below — not a one-paragraph stub.

## Lead enrichment standard (required for every theme & debate)

Synthesis pages are the reader's payoff, so their **lead** — the prose between the
`# Title` and the first structural block (the positions table, or `## Evidence from the literature`)
— must be a genuine standalone essay, never a single orienting paragraph. Match the
concept/thinker house style in `HANDOVER.md` (v2):

- **~400–700 words**, scaled to how much evidence/positions the page holds; never pad.
- Plain, analytical voice. **No book-framing** ("the book", "the book's question",
  "matters for the book") and no significance-editorializing. Analyze the ideas directly.
- **A source is a vessel, not a subject** (hard rule): a source is a *container* for evidence
  and argument; write about what is INSIDE it (studies, findings, thinkers, traditions),
  never the container. Never make a source / "the page" / "the corpus" the grammatical
  subject, in ANY form: bare ("both sources", "each source"), **quantified** ("three of the
  sources converge", "the life-and-mind sources"), **named-by-topic** ("the extended-cognition
  source states…", "the what-is-life source argues…"), page/material-as-subject ("this page", "within this page's material",
  "the material here", "the sourcing here"), or locators ("Chapter 2", "Q4/Q8",
  "the source(d) material", "the sources agree", "position map", "Camp (a–d)"). Rewrite the
  subject to the real source of the claim: "Varela, Thompson and Rosch state…", "three
  independent lines of evidence converge…", "the autopoietic tradition holds…". The *content*
  is always fair game as a subject — a topic, idea, concept, author, tradition, or study
  ("the concept descends from…", "Bentham's footnote decoupled…"); only the *container*
  (source/page/material/corpus/document/chapter) is banned.
  Attribute claims to their real authors/traditions and cite normally; `[[literature/slug]]`
  links are fine (and the `## Evidence from the literature` section keeps them), but the prose is never
  a review of the literature. **Test:** delete every `[[literature/…]]` link and the corpus — each
  sentence must still read as a claim about the world. Say "across ritual and creative
  practice", not "across both sources".
- **Themes:** state the shared pattern precisely; show how it appears across the relevant
  traditions/domains (name them, not the source docs), drawing on the page's own
  `## Evidence from the literature`; name and `[[link]]` the concepts/thinkers it unifies; close on
  the nuance or the failure mode it warns against.
- **Debates:** state the question and why it is genuinely contested; lay out the positions
  in prose (complementing, not duplicating, the table); close on what is actually
  unresolved or where the sides talk past each other.
- **Fidelity:** reuse only the real author citation tokens already present (`[Surname, YYYY]`);
  never invent, and never carry document-pointer tokens (`[source §N]`, `[chN-qN-…]`,
  `[corpus/round2/source synthesis]`) into the prose.
- Keep the structured sections (table / `## Evidence from the literature` / `## Related` /
  `## Where the literature agrees` / `## Open questions` / `## See also`) **intact below** the lead.
- **Do NOT set `overview: true`** on themes/debates — unlike concept/thinker pages, their
  structured sections must stay visible in the atlas (only the lead is enriched, in place).

Practical splice: to enrich leads in bulk without disturbing the sections, draft each lead
as JSON `{slug: markdown}` and insert with a lead-only splice (replace title→first-`## `/`|`/`- `).

## Pass C — hygiene

Run these checks and fix the mechanical ones; queue judgment calls for the report.

- **Dangling wikilinks** (regex allows UPPERCASE — source slugs like `ch1-q1-non-western-AI` contain capitals; exclude `reports/` and `themes` example placeholders by scanning only the page directories, not the reports):
  ```bash
  grep -rohE '\[\[[A-Za-z0-9/_-]+\]\]' \
    /Users/noahraford/magic/wiki/sources /Users/noahraford/magic/wiki/concepts \
    /Users/noahraford/magic/wiki/thinkers /Users/noahraford/magic/wiki/debates \
    /Users/noahraford/magic/wiki/themes /Users/noahraford/magic/wiki/answers \
    --include='*.md' | sort -u
  ```
  For each link `[[<type>/<slug>]]`, confirm `test -f /Users/noahraford/magic/wiki/<type>/<slug>.md`. A miss is a dangling link — fix the link or create the missing stub. Ignore single-letter placeholder slugs (`x`, `y`) that appear only inside a page's own literal template example.
- **Orphans:** pages that never appear in the link list above (nothing links to them). Note in the report.
- **Stale stubs:** pages with `status: stub` older than the previous analyze — flag for enrichment.
- **Thin synthesis leads:** any `themes/` or `debates/` page whose lead (the prose before its first `## `/table/`- ` block) is under ~250 words → it is an un-enriched stub; enrich it per the **Lead enrichment standard** above before finishing.
- **Index ↔ frontmatter drift:** every page appears once in `index.md` under the right type with the right `(N sources)` count; fix mismatches.
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

The last section is the research-gap signal fed back to the deeper-research pipeline: questions the literature raise but none can answer.

## Log + commit

Append EXACTLY one line to `/Users/noahraford/magic/wiki/log.md`:

```
YYYY-MM-DD HH:MM | analyze | scope:<delta|full> | sources:<comma-list|all> | debates:+<n> themes:+<n> fixes:<n>
```

Concrete example (delta run over two sources):

```
2026-08-30 14:30 | analyze | scope:delta | sources:ch2-q4-ritual-nonhuman-powers,ch2-q8-creativity-reception | debates:+1 themes:+0 fixes:+2
```

Then commit (if the wiki repo exists): `cd /Users/noahraford/magic/wiki && git add -A && git commit -m "analyze: <YYYY-MM-DD>"`.

## Enrichment pass (`--full` only)

When a chapter is complete, `analyze --full` finishes every page. Concept/thinker pages
still at ingest level (frontmatter lacks `overview: true`) get a standalone **narrative
lead** per the v2 house style in `HANDOVER.md` — standalone analysis of the idea, length
scaled to source, **no book-framing, no document-talk** ("the source(s)"/"the corpus"/etc.),
cross-linked. Mechanics that scale (used for 250 then 400 pages):

- Dispatch parallel **read-only drafting agents** (~7 pages each; point them at the
  gold-sample exemplar + the v2 rules). Each reads a page (its definition + `## In <source>`
  sections) and RETURNS the lead as JSON `{slug: markdown}` — never edits files, so voice
  stays consistent and the insert is single-writer.
- Insert with a splice that replaces the text between the `# Title` line and the first
  `## ` and sets `overview: true`. Then run `match_sources.py` (deep-links) and **strip any
  dangling `[[links]]` to plain text** (agents guess slugs; this guarantees clean links).
- **Skip pages that already have `overview: true`.** Delta `analyze` does NOT enrich — a
  page may still gain `## In` sections from later ingests, which would stale its narrative.

This is the pass that brings a freshly-ingested chapter to the depth of the rest of the wiki.

## graphify refresh (`--full`, before the atlas)

Refresh community detection so new pages are colored/clustered, not dumped in one group:
invoke the **graphify** skill on the wiki (CWD `/Users/noahraford/magic/wiki`, output
`wiki/graphify-out/`, `--update` on later runs). graphify is **agent-driven — there is no
build CLI** (`graphify` the command only installs the skill / manages hooks). Non-fatal: if
it can't run, `build_wiki_html.py`'s partial-graph fallback still includes every page (as an
uncolored group wired by wikilinks), so the atlas never drops content.

## Refresh cluster narratives (`--full`, after graphify, before the atlas)

graphify **renumbers communities on every run**, so the hand/LLM-written cluster notes in
`wiki/clusters/*.md` go stale the moment membership shifts (new ingests create, merge, or
split communities). Left unattended, the legend showed one cluster's name while the reader
opened a different (old-numbered) cluster's essay. Two safeguards — one automatic, one you
must run here:

- **Automatic safety net (already in `build_wiki_html.py`).** The atlas no longer trusts a
  narrative's `community:` frontmatter id. `_match_narratives_to_communities` attaches each
  narrative to the *current* community whose members it most **wikilinks**, and the cluster
  page heading is the current graphify label — so a stale id can never again surface the
  wrong essay, and legend label always equals the reader heading. The load-bearing
  requirement is therefore that **every cluster note wikilinks several of its community's
  member pages**; keep that dense. A note that overlaps no current community is dropped from
  the atlas (member list shown under the correct label, never the wrong prose).

- **Refresh you must run on `--full`.** After the graphify refresh, reconcile the cluster
  notes to the *current* communities so new clusters get prose and drifted ones get updated:
  1. Read `wiki/graphify-out/graph.json` (member pages per `community`) and
     `GRAPH_REPORT.md` (current `### Community N - "Name"` labels).
  2. For **each current community**, ensure exactly one `wiki/clusters/<NN>-<slug>.md` note
     that (a) sets `community:` to the current id and `title:` to the graphify label, and
     (b) opens with a standalone narrative that **wikilinks 5+ of that community's
     top-degree members** (so the atlas binds it by content). Refresh the prose of notes that
     still map to a community; **create notes for NEW communities** (e.g. the agency and CEO
     clusters from ch5/ch6); **archive** notes whose topic no longer forms a distinct
     community by moving them to `wiki/clusters/_stale/` (the atlas ignores that subdir).
  3. Scale it like the lead-enrichment pass: dispatch parallel **read-only drafting agents**
     (one per community, given that community's member list + the v2 house style), each
     RETURNING `{slug: markdown}`; do the file writes single-writer in the main context.
  4. Runs **after graphify and before the atlas build**, so the rebuilt `wiki.html` picks up
     the refreshed notes. Non-fatal: if skipped, the automatic safety net still prevents
     mislabeling — you just miss prose for brand-new clusters.

## Refresh the search index (automatic, last step)

Every `analyze` run ends by refreshing the semantic-search index so the new debates/themes/stubs are immediately searchable. Run it AFTER the commit (the index DB is git-ignored, so ordering vs. commit does not matter, but running last keeps the analytical work the priority):

```bash
python3 -B ~/.claude/skills/semantic-search/search.py --cwd /Users/noahraford/magic/wiki --index --quiet
```

- **`--cwd` scopes indexing to the wiki ONLY.** Never omit it and never point it at `magic/` or anything under `/Users/noahraford/magic/X_Deeper_research/` — the indexer writes a `.semantic-index.db` into its root, and doing so under the read-only sources violates the safety invariant. The DB lands at `/Users/noahraford/magic/wiki/.semantic-index.db`, which the wiki `.gitignore` excludes.
- **Source-corpus index (separate).** The primary-source RAG corpus lives at `/Users/noahraford/magic/wiki/.literature-text/` (dot-prefixed, so the wiki index walker auto-skips it — the two indexes stay separate). It's built by `extract_sources.py` from `wiki/literature-html/` and has its OWN index: refresh with `python3 -B ~/.claude/skills/semantic-search/search.py --cwd /Users/noahraford/magic/wiki/.literature-text --index --quiet` when the literature change. This is the corpus that `magic/CLAUDE.md` tells free-form chat to retrieve from.
- The refresh is **incremental** (only changed files re-embed) and **non-fatal**: if it fails (e.g. no `OPENAI_API_KEY` in env or `~/.env`), note it in the run summary and continue — the analyze itself still succeeded. Search is an optional enhancer, never a gate.
- If the wiki has no `.gitignore` excluding `.semantic-index.db`, create one before the first refresh so the 13MB binary is never committed.

## Build the wiki atlas (automatic, last step)

After the search refresh, regenerate the **wiki atlas** — one self-contained, styled `wiki/wiki.html` (a reading pane + an interactive, collapsible, community-colored graph navigator built from the wiki pages and `wiki/graphify-out/graph.json`). This makes every new debate/theme/page immediately browsable without Obsidian.

```bash
python3 -B ~/.claude/skills/research-wiki/build_wiki_html.py --wiki /Users/noahraford/magic/wiki --quiet \
  || echo "[atlas] build failed — noted, continuing (analyze still succeeded)"
```

- **Non-fatal enhancer**, same contract as the search refresh: the `|| echo …` makes non-fatality mechanical — if the build fails (e.g. `markdown`/`networkx`/PyYAML missing, exit 1/2), note it in the run summary and continue; the analyze itself still succeeded.
- Output is `/Users/noahraford/magic/wiki/wiki.html` (~1 MB, git-ignored). If `graph.json` is absent it still builds, using a degraded graph from wikilinks only (no community colors).
- It reads only under `wiki/` (pages + `wiki/graphify-out/`); it never touches `X_Deeper_research/`. Community names come from `wiki/graphify-out/GRAPH_REPORT.md` (parsed at build time, since community numbering changes each run).
- **Front door (`about.md`).** The landing lead is the one hand-written part of the atlas. Keep it **topic-framed and extensible** — describe the intellectual territory the wiki covers (e.g. "What minds, life, and intelligence are"; "Mind in practice"), and **never organize it by the book's chapter structure** ("Chapter 1 / Chapter 2…") or hardcode counts ("seventeen sources"). The auto sections — the provenance count line, **themes**, **live questions**, **topic clusters**, and the graph — already regenerate from whatever the corpus currently holds and scale on their own, so the lead must stay true as new questions/material are added without needing per-chapter edits.
- **Public splash + login gate (`landing.html`).** The build also emits a public splash page (title + subtitle from `about.md`) that carries a **username/password login form** (`POST /login`) — no credentials are ever shown or embedded. A password-protected deploy serves `landing.html` at `/` publicly, and its `server.js` validates the form against `ATLAS_USER`/`ATLAS_PASSWORD`, sets an HttpOnly session cookie, and gates the atlas (`/wiki.html`) + source pages on that cookie (redirecting to `/` when absent). The build inserts a `__LOGIN_ERROR__` placeholder the server fills after a failed attempt. See the reference `server.js` in the deployed wiki repo.
