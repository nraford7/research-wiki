# ask — procedure

Answer a question by using the wiki as a MAP to reach the research documents, then reading and answering from those documents. `ask <question>`, optionally filing the answer back (`ask <question> --file`). Page formats from `page-templates.md`.

## The rule: orient on the map, read and answer from the source

The wiki (`concepts/`, `thinkers/`, `debates/`, `themes/`, `literature/`) is a **MAP** — short, distilled, cross-linked summaries. The research documents in `$WIKI_ROOT/.literature-text/*.md` are the **SOURCE** — the full primary text the wiki was built from, and the thing to ground every answer in. *(Mnemonic: the wiki is the map; the research documents are the ground it maps.)*

Use the map to **orient and locate**; then open the source and **answer from it**. Do NOT answer from a map page's summary of a source when the source itself is one `Read` away. The map's job is to get you to the right part of the source fast — not to be the answer.

## Retrieval ladder

1. **Orient on the map.** Read `$WIKI_ROOT/index.md`, then open the 3–8 most relevant `concepts/` `thinkers/` `debates/` `themes/` pages. Use them to grasp the ideas, positions, and thinkers — and to locate WHICH research documents and sections hold the primary evidence. The pointers are: each page's `literature:` frontmatter, its `[[literature/<slug>]]` wikilinks, and the `[Author, Year]` / `[slug § heading]` references in the body.
2. **Turn the map into a read-list.** Convert those pointers into specific source files + section headings to open: `$WIKI_ROOT/.literature-text/<slug>.md`. If the map is thin or you need more, search the SOURCE directly (not the map):
   ```bash
   python3 -B ~/.claude/skills/semantic-search/search.py \
     --cwd $WIKI_ROOT/.literature-text "<the question>" --top 8
   ```
   (If you specifically need to search the MAP instead, scope semantic-search to `$WIKI_ROOT` — never to `magic/` or anything under `$SOURCES_ROOT/`, per the read-only invariant.)
3. **Read the source — do NOT skip this.** Open each `$WIKI_ROOT/.literature-text/<slug>.md` and read the actual sections: the primary prose and its original `[Author, Year]` citations. This is the step the map exists to deliver you to; skipping it is the failure mode this procedure exists to prevent.
4. **Analyse and answer from the research documents.** Ground every claim in what the sections actually say; quote `[slug § heading]` from the primary text.

**Fast path (structural questions only) — ASK before using it.** Never silently answer from the map alone. If a request looks like it only needs the map — what positions exist, who argues what, where a topic is debated, how ideas relate — STOP and ask the user which they want: *a quick map-level summary, or a deep dive that reads the source?* Only answer map-only after they confirm. Any request for evidence, analysis, quotes, numbers, or a grounded conclusion defaults straight to reading the source (steps 3–4) — no need to ask. The point is that map-only vs. source-grounded is always an explicit, agreed choice, never an accidental shortcut.

## Answer rules

- Answer from the RESEARCH DOCUMENTS (`.literature-text`), grounded in sections you actually opened and read.
- Every claim gets a `[slug § heading]` citation to the source section, plus the underlying `[Author, YYYY]` the document uses; add `[[debates/<slug>]]` / `[[concepts/<slug>]]` map links for navigation.
- Quote a wiki MAP page as a *source* only when you explicitly label it "wiki synthesis — not yet traced to the research document," and prefer to trace it to the source before relying on it.
- Where the documents disagree, say so and link `[[debates/<slug>]]` for the map of positions — but support the disagreement with source text, not the debate page's paraphrase.
- NO fabrication. If you cannot open the relevant source section, say so plainly and name which source/section would answer it — do not substitute the map's summary.

## Filing (`--file`, or offer when the answer is substantive)

- Write `$WIKI_ROOT/answers/<slug>.md` from the answer template in `page-templates.md`.
- Add its index line under the `## Answers` heading in `index.md`.
- Append one log line to `$WIKI_ROOT/log.md`:
  ```
  YYYY-MM-DD HH:MM | answer | <answer-slug> | filed
  ```
- Commit (if the wiki repo exists): `cd $WIKI_ROOT && git add -A && git commit -m "answer: <answer-slug>"`.
