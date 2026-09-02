# ask — procedure

Answer a question from the wiki (`ask <question>`), optionally filing the answer back (`ask <question> --file`). Answers come from wiki pages only, with citations and path-qualified wikilinks. Page formats from `page-templates.md`.

## Retrieval ladder

1. **Index first.** Read `$WIKI_ROOT/index.md`, scan the one-line hooks, and open the 3–8 pages most relevant to the question.
2. **Semantic search** (only if the index is insufficient AND an index exists for the wiki): invoke the `semantic-search` skill scoped to `$WIKI_ROOT` ONLY. It writes a `.semantic-index.db` into the tree it indexes, so it must NEVER be pointed at `magic/` or anything under `X_Deeper_research/` (read-only invariant). Run it with the wiki as the working directory / explicit target — never a parent that contains the literature.
3. **Grep fallback:**
   ```bash
   grep -ril '<terms>' $WIKI_ROOT --include='*.md'
   ```

## Answer rules

- Answer from wiki pages ONLY.
- Every claim gets a citation (grammar: `[Surname, YYYY]`, etc.) AND a path-qualified wikilink to the page it came from (`[[concepts/<slug>]]`).
- Where the literature disagree, say so explicitly and link the relevant `[[debates/<slug>]]` page.
- `NO fabrication: if the wiki cannot support a claim, do not make it.` If the wiki is empty or cannot answer, say so plainly and name which source/section would probably answer it.

## Filing (`--file`, or offer when the answer is substantive)

- Write `$WIKI_ROOT/answers/<slug>.md` from the answer template in `page-templates.md`.
- Add its index line under the `## Answers` heading in `index.md`.
- Append one log line to `$WIKI_ROOT/log.md`:
  ```
  YYYY-MM-DD HH:MM | answer | <answer-slug> | filed
  ```
- Commit (if the wiki repo exists): `cd $WIKI_ROOT && git add -A && git commit -m "answer: <answer-slug>"`.
