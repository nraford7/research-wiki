# batch — procedure

Point at a directory of finished research products and drive the whole pipeline
end to end: **ingest one source at a time, delta-analyze after every 3, loop
until nothing is left, then one `analyze --full`** (enrich + graphify + atlas +
search). The human does not manage the batch by hand — this procedure does.

Command: `batch <research-dir> [--every N]` (default cadence 3).

The deterministic bookkeeping (which dirs are sources, which are already
ingested, what to do next) lives in `scripts/batch_ingest.py`. It reads
`wiki/log.md` + the filesystem, so the whole loop is **resumable**: if a run is
interrupted, or new sources finish later, just run `batch` again and it resumes
from the correct step. You (the agent) execute the ingest/analyze procedures the
planner schedules.

## Safety (unchanged from SKILL.md)

- **Read-only sources.** ingest never writes under the source tree; each ingest
  proves it (the `/tmp/wb-marker` check in `ingest.md` Step 6).
- **Single writer / serialize.** Never run this concurrently with another
  ingest/analyze (last-writer-wins on `log.md`). One batch, one session.
- **Absolute paths.** The planner emits absolute source dirs; pass them straight
  to the ingest procedure.

## Step 1 — Show the plan

```bash
python3 -B ~/.claude/skills/research-wiki/scripts/batch_ingest.py "<research-dir>" --plan
```

Report the plan to the user in one or two lines: how many sources, how many will
be ingested, how many are already current, and any `not-a-source` (still
mid-run / incomplete) or `locked` (a live deeper-research lease) that will be
skipped. `not-a-source` on a `chN-qN-*` dir almost always means the run has not
finished (no `Sections/` with ≥3 md and no ≥50KB monolith yet) — say so, and note
they will be picked up automatically on a later `batch` run.

## Step 2 — Drive the loop

Repeat until the planner says `DONE`:

```bash
python3 -B ~/.claude/skills/research-wiki/scripts/batch_ingest.py "<research-dir>" --next [--every N]
```

Execute the single action it prints, then call `--next` again:

| `--next` output | What you do |
|---|---|
| `INGEST <abs-dir>` | Follow `references/ingest.md` **exactly** on that dir (Steps 0–6, incl. the read-only proof and the git commit + the one `\| ingest \|` log line). |
| `INGEST --force <abs-dir>` | Same, but pass `--force` — the content changed since a prior ingest; ingest.md's idempotency check would otherwise skip it. |
| `ANALYZE_DELTA` | Follow `references/analyze.md` in **delta** mode (its scope auto-derives from the log: everything ingested since the last analyze). Writes the report, the one `\| analyze \| scope:delta \|` log line, commits, refreshes search. |
| `ANALYZE_FULL` | Follow `references/analyze.md` with **`--full`**: the Enrichment pass (narrative leads on ingest-level pages), the graphify refresh, the cluster-narrative refresh, then the atlas build + search refresh. This is the "enrich everything" finish. |
| `DONE` | Stop. Everything is ingested, analyzed, and a full analyze is current. |

> **Who runs which step.** The `INGEST` steps are single-writer and may be delegated to a
> worker subagent (one at a time). The `ANALYZE_FULL` fan-out steps — the per-page
> **enrichment** and the **cluster-narrative refresh** — must be run by the **MAIN
> orchestrator agent**, because subagents cannot spawn subagents in this harness. If you
> delegated the ingests to a worker, do NOT also hand it `ANALYZE_FULL`; run the full pass
> yourself (dispatch the drafting agents, splice with `scripts/enrich_splice.py`).

**Do not batch the ingests or skip the log lines.** Each `INGEST` is a full
ingest.md run ending in its own git commit + log line — that is what makes the
next `--next` compute correctly. The planner counts ingests *from the log*, so
if you don't write the log line the loop will not advance.

## Step 3 — Finish

When `--next` returns `DONE`, run `--plan` once more to confirm all sources read
`ingested-current`, and report to the user: N ingested, debates/themes added
(from the analyze reports under `wiki/reports/`), and that the atlas + search are
rebuilt. If any dir is still `not-a-source` (a run that had not finished),
mention it and that a future `batch` will absorb it.

## Notes

- **Cadence.** `--every 3` is the default (ingest 3 → delta analyze). Raise it
  for a large batch you want analyzed less often, lower it to 1 to analyze after
  every source. The final `analyze --full` always runs regardless.
- **Resume / re-run.** Safe to run `batch` repeatedly. Already-current sources
  are skipped; changed sources re-ingest with `--force`; unfinished runs are
  skipped until they complete.
- **Locked sources.** If a source is `locked`, a deeper-research run may still be
  writing it — the planner skips it and you should leave it for the next batch.
