# wiki-bible

An LLM-maintained research wiki that sits between you and a pile of deep-research
documents — and turns them into something you can *navigate, argue with, browse,
and chat with*.

It follows Andrej Karpathy's "LLM wiki" pattern: interlinked plain-markdown pages,
maintained incrementally by the model, with you as editor-in-chief. On top of the
wiki it adds a browsable HTML **atlas**, a primary-source **chat corpus**, and
**deep-links** from each concept down to the exact section of the source it came
from.

It's a [Claude Code](https://claude.com/claude-code) skill: you drive it with
`/wiki-bible …` commands.

---

## The three layers

```
deep research  ─▶  BIBLES        the raw sources: long literature reviews, one per question
   (your        (read-only)      e.g. "What is wu-wei?", "What is life?"  (HTML)
   pipeline)         │
                     │  /wiki-bible ingest   (the model reads each bible, extracts
                     ▼                        concepts + thinkers, section-scoped)
                  WIKI            interlinked markdown: concepts/, thinkers/, debates/,
                (the map)         themes/, answers/  — an Obsidian vault + git repo
                     │
                     │  /wiki-bible analyze   (finds where bibles agree → themes,
                     ▼                         where they collide → debates)
                  ATLAS + CORPUS  wiki.html (browse) · .bibles-text/ (chat) · deep-links
```

- **Bibles** = the source of truth. Read-only; never modified.
- **Wiki** = the distilled, cross-linked map. What relates to what; where the debates are.
- **Atlas / corpus** = how you *use* it: a self-contained HTML reader + graph, and a
  semantic index over the primary text so you can chat with the whole corpus.

---

## What you get

- **An interlinked wiki** — every concept and thinker is one markdown page,
  cross-linked with `[[type/slug]]` wikilinks. Opens as an [Obsidian](https://obsidian.md) vault.
- **Cross-bible synthesis** — `analyze` promotes genuine agreements into **themes**
  and genuine disagreements into **debates**, each with quoted positions and citations.
- **A bible-styled atlas** (`wiki.html`) — one self-contained, offline HTML file:
  a community-colored knowledge graph + a searchable index + a reading pane. Shareable;
  no server, no Obsidian needed.
- **Chat with the corpus** — the 17 bibles are extracted to a searchable primary-text
  index; a project rule makes plain questions retrieve and answer from the *source*,
  not the summaries.
- **Deep-links to source** — each enriched entry links to the exact bible *section*
  it draws on.

---

## How it works — commands

| Command | What it does |
|---|---|
| `/wiki-bible ingest <bible-dir>` / `ingest --all` | Read a bible, extract its concepts + thinkers into wiki pages (merging into existing pages section-by-section). |
| `/wiki-bible analyze` / `analyze --full` | Sweep for cross-bible contradictions (→ `debates/`) and convergences (→ `themes/`); fix broken links; then auto-refresh search + rebuild the atlas. |
| `/wiki-bible ask <question>` / `ask <q> --file` | Answer a question from the accumulated wiki pages; `--file` saves the answer under `answers/`. |

`analyze` ends by automatically (a) refreshing the semantic-search index and
(b) rebuilding `wiki.html`. Both are non-fatal enhancers.

### Example

```
/wiki-bible ingest 2_Chapter\ 2/ch2-q1-wu-wei
  → concepts/wu-wei.md, concepts/ziran.md, thinkers/laozi.md, …

/wiki-bible analyze --full
  → debates/do-experts-think.md, themes/tacit-knowledge-resists-codification.md, …
  → wiki/wiki.html rebuilt · search index refreshed

/wiki-bible ask "does cognition require being alive?"
  → an answer citing [Thompson, 2022] vs [Levin, 2023], linking [[debates/does-cognition-require-life]]
```

A concept page looks like: a plain-language **overview**, then a `## In <bible>`
section per source (positions + citations), then `See also` links, and — once
enriched — a **Sources** block that deep-links to the exact bible sections.

---

## The extra tooling (Python)

Run by `analyze`, or standalone:

- **`build_wiki_html.py`** — builds the atlas `wiki.html` from the wiki pages +
  the graph. Offline, self-contained.
  `python3 build_wiki_html.py --wiki /path/to/wiki`
- **`extract_bibles.py`** — extracts the bibles' HTML into a clean, section-chunked
  markdown corpus (`.bibles-text/`) for retrieval, and captures section anchors for
  deep-linking. `python3 extract_bibles.py --resection`
- **`match_sources.py`** — matches each enriched concept to the most relevant
  *section* of every bible it cites, and records the deep-link pointers.
  `python3 match_sources.py`

Tests: `python3 -m pytest tests/ -q`

---

## Dependencies

**Companion skills** (optional but recommended — the wiki degrades gracefully without them):

- [**semantic-search**](https://github.com/) — hybrid BM25 + embedding search; powers
  the atlas search and the "chat with the corpus" retrieval. (Local Claude Code skill.)
- [**graphify**](https://pypi.org/project/graphifyy/) — community detection over the
  wiki; colors the atlas graph and seeds `analyze`'s themes. `pip install graphifyy`.

**Python:** `markdown`, `beautifulsoup4`, `networkx`, `PyYAML` (+ `pytest` for tests).

```bash
pip install markdown beautifulsoup4 networkx pyyaml pytest graphifyy
```

---

## Layout

```
wiki-bible/
  SKILL.md              # the skill: commands, safety invariants, dispatch
  references/           # the exact procedures for ingest / analyze / ask + page templates
  build_wiki_html.py    # atlas generator
  extract_bibles.py     # bible → corpus extraction + section anchors
  match_sources.py      # concept → bible-section deep-link matcher
  tests/                # pytest
  README.md · HANDOVER.md
```

The **wiki content itself** (pages, the atlas HTML, the extracted corpus, the graph)
lives in a separate directory and is not part of this repo — this repo is the tooling.

---

## Safety invariant

The source bibles are **read-only**. No operation ever writes, moves, or deletes
anything under the bibles directory; the wiki is maintained entirely in its own
tree, in its own git repo.

## A note on paths

This skill is currently wired to one author's setup (paths under
`/Users/noahraford/magic/…`). To reuse it, adjust the hardcoded paths at the top of
the three Python scripts and in `SKILL.md` / `references/`. No API keys are stored in
the code — `semantic-search` reads `OPENAI_API_KEY` from the environment or `~/.env`.
