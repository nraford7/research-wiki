# ingest — procedure

Ingest one source (`ingest <source-dir>`) or every source (`ingest --all`) into the wiki. Sources are read-only (see SKILL.md Safety invariants). Page formats come from `page-templates.md`. All commands assume zsh — use `find`, never bare globs.

If the wiki does not exist yet, do the First-run bootstrap from SKILL.md before step 0.

## Step 0 — Is this dir an ingestable source?

A directory `$D` qualifies iff its name matches `ch<N>-q<N>-*`, its name does NOT contain `superseded` and does NOT end in a timestamp suffix (regex `-\d{8}t\d+z$`, case-insensitive), AND at least one of these three tests succeeds (try in order):

```bash
# (a) Sections/ with >=3 md files:
[ "$(find "$D/Sections" -maxdepth 1 -name '*.md' 2>/dev/null | wc -l)" -ge 3 ]
# (b) a root monolith named like a source (case-insensitive):
[ "$(find "$D" -maxdepth 1 -iname '*source*.md' | wc -l)" -ge 1 ]
# (c) exactly one root .md and it is >= 50KB:
[ "$(find "$D" -maxdepth 1 -name '*.md' | wc -l)" -eq 1 ] && [ "$(find "$D" -maxdepth 1 -name '*.md' -size +50k | wc -l)" -eq 1 ]
```

Known irregulars this must catch: `ch1-q1` (single root md → test c), `ch1-q6` (`western-philosophy-of-mind-BIBLE.md` → test b), `ch1-q2` (monolith + Sources, no Sections/ → test b/c). If passed an explicit dir that fails all three, report "not a source" and stop.

## Step 1 — Validate + idempotency

Derive `slug` = the source dir's basename. Compute the content hash:

```bash
D="<source-dir>"
if [ "$(find "$D/Sections" -maxdepth 1 -name '*.md' 2>/dev/null | wc -l)" -ge 3 ]; then
  CONTENT=$(find "$D/Sections" -maxdepth 1 -name '*.md' ! -name 'bibliography.md' ! -name 'dedup-decisions.md' | sort)
else
  CONTENT=$(find "$D" -maxdepth 1 -iname '*source*.md' | sort)
  [ -z "$CONTENT" ] && CONTENT=$(find "$D" -maxdepth 1 -name '*.md' | sort)
fi
SOURCES=$(find "$D/Sources" -maxdepth 1 \( -name 'claims.jsonl' -o -name 'bibliography.md' -o -name 'bibliography.bib' \) 2>/dev/null | sort)
printf '%s\n%s\n' "$CONTENT" "$SOURCES" | grep -v '^$' | tr '\n' '\0' | xargs -0 cat | shasum -a 256 | cut -c1-12
```

**CRITICAL — NUL-delimit, never bare `xargs cat`.** Every source path contains a space (`.../2_Chapter 2/...`); a bare `xargs cat` word-splits on it and `cat` fails on every file, so the hash is garbage or the empty-input hash. The `tr '\n' '\0' | xargs -0 cat` above is space-safe (macOS `xargs` has no `-d`, so use `-0`). Do not "simplify" it back.

- **Empty-hash guard:** if the result is `e3b0c44298fc` (SHA-256 of empty input), STOP — the source resolved to zero content files. Report it; do not ingest.
- **Idempotency:** check the log:
  ```bash
  grep -F "| ingest | <slug> | sha256:<hash>" $WIKI_ROOT/log.md
  ```
  A hit → print `already ingested; use --force` and stop (unless `--force` was passed).
- **Lock check** — an active lock is a *live lease*, not transaction/backup residue. Scan ONLY `.locks/leases/*/holders.json` (64 KB), never the 500 MB+ `.transactions` tree (a recursive grep there false-positives on stale migration backups and is slow):
  ```bash
  find "<chapter-dir>/.locks/leases" -name holders.json 2>/dev/null \
    | tr '\n' '\0' | xargs -0 grep -l '<source-slug>' 2>/dev/null
  ```
  Any output → a live lease names this source; an active deeper-research run may be writing it: skip + warn. No output → proceed. (Idle leases hold `[]` and match nothing.)

## Step 2 — Read the source (read-only)

- Content: `Sections/*.md` EXCLUDING `bibliography.md` and `dedup-decisions.md` (reference lists, not content). If there is no qualifying `Sections/`, read the monolith and chunk it on `#`/`##` headings into ~2–4k-word units.
- `Sources/claims.jsonl`: these are SOURCE records (`url, title, year, slice, tier`) — no claim text, no author. Skip malformed lines with a per-line warning; a missing/empty file is a warning, not a failure.
- `Sources/bibliography.md` (primary) / `Sources/bibliography.bib` (fallback) — title/url/year lists. NOTE: these carry NO author field. The surname in a `[Surname, YYYY]` citation is resolved from the **section prose itself** (the text names "Victor Turner" beside `[Turner, 1969]`), not from the bibliography. Keep each citation verbatim as it appears in the section.

Before writing anything, `touch /tmp/wb-marker` so the read-only invariant can be verified after (see Step 6).

## Step 3 — Source page

Create/update `$WIKI_ROOT/literature/<slug>.md` from the **source** template in `page-templates.md`: core question, method note, position map, 10–20 key sources by tier, and links to every wiki page this source touches (filled in during Step 5).

## Step 3b — Publish the readable HTML (auxiliary layer)

Ingest builds the wiki PAGES from the source text; it must ALSO populate the
readable layer `wiki/literature-html/<slug>.html` (what the atlas "Read full
document" link opens, and the input `extract_sources.py` turns into the searchable
`.literature-text/` RAG corpus). If this is skipped, the source is invisible to the
"Read full document" link AND to free-form corpus chat — a silent gap (this is
exactly how ch4–ch6 went missing).

```bash
python3 -B ~/.claude/skills/research-wiki/scripts/publish_source_html.py \
  --source-dir "<source-dir>" --wiki $WIKI_ROOT
```

It copies `RESEARCH-REPORT_<slug>.html` → `literature-html/<slug>.html`, scrubbing
two known deeper-research export defects: the `Research Bible` stamp (→ `Research
Report`; the b-word is banned — see `magic/CLAUDE.md`) and the leaked
`<section id="…shared-brief-for-all-section-subagents…">` briefing block + its TOC
anchor. It REFUSES to write if "bible" survives. If the source has no HTML yet,
note it and run this later once the HTML lands (then re-run `--full` so the text
layer + anchors catch up).

## Step 4 — Entity extraction (subagent fan-out)

Dispatch one subagent per 2–3 section files (or per 2–3 monolith chunks). Give each this prompt verbatim:

```text
Read these files from a research source (read-only): <paths>. Return raw structured
data (no prose): candidate CONCEPTS, THINKERS, and INTERNAL DEBATES. For each:
name; aliases; one-line definition/identity; 2–6 key claims, each with its inline
citation copied exactly as it appears (grammar: [Surname, YYYY] / [A, YYYY; B, YYYY]
/ [Surname, YYYY, ch.|p.|pp. N]); the section file it came from. Brackets not
matching the grammar are prose — ignore them as citations. Zero entities is a
valid answer.
```

A source yielding zero entities still gets a stub source page + a warning.

## Step 5 — Dedup + merge (single writer, main context)

Do the merge yourself in the main context (never in a subagent — single writer). For each candidate:

- Match against existing pages by slug + aliases, **same type only** (concepts vs concepts, thinkers vs thinkers).
- **Existing page:** section-scoped replace of its `## In <source-slug>` section (create the section if absent); add this source to the page's `sources:` frontmatter if not already there. Never touch other sources' sections or the preamble.
- **New page:** create from the concept/thinker template; `status: stub` if it carries <2 claims, else `draft`.
- **Alias conflict:** if a candidate's alias is already held by another page of the same type, do NOT add the alias — note the conflict for the next `analyze` report.

A typical source touches 10–25 pages. Fill the source page's "Pages from this source" list with links to all of them.

## Step 6 — Bookkeeping + read-only proof

- Update the touched lines in `$WIKI_ROOT/index.md` (per-type headings; index line format from `page-templates.md`).
- Bump `updated:` frontmatter to today on every page you touched.
- Append EXACTLY one line to `$WIKI_ROOT/log.md`:
  ```
  YYYY-MM-DD HH:MM | ingest | <source-slug> | sha256:<12-hex> | created:<n> updated:<n>
  ```
- Prove read-only: `find $SOURCES_ROOT -newer /tmp/wb-marker -type f ! -name '.DS_Store'` must be empty. If it is not, something wrote to the literature — stop and report.
- Commit the wiki: `cd $WIKI_ROOT && git add -A && git commit -m "ingest: <source-slug>"` (if the repo exists).

## `--all`

Enumerate candidate dirs (zsh-safe), then test each against Step 0's three qualification commands, ingest matches sequentially (skipping already-ingested), and print a one-line status per dir with its skip reason (`already-ingested | superseded | locked | not-a-source`):

```bash
find $SOURCES_ROOT -mindepth 2 -maxdepth 2 -type d -name 'ch*-q*' \
  | grep -viE '(superseded|-[0-9]{8}t[0-9]+z$)' | sort
```

(The `-name 'ch*-q*'` filter enforces spec §4.1.7's chapter exclusions — `0_Research Guide`, `Process`, and dot-dirs hold no `ch*-q*` children, so they never appear. The `grep -viE` drops `superseded`/timestamped variants; the Step-0 tests drop non-sources; the lock check drops locked ones.)
