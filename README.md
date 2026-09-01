# research-wiki

Turn a stack of deep-research documents into a wiki you can browse, search, and question.

`research-wiki` is a [Claude Code](https://claude.com/claude-code) skill. You point it at long research reports. It reads them, builds a linked set of notes, finds where the reports agree and disagree, and makes one web page you can explore. You run it with `/research-wiki` commands.

---

## What it is

You start with source documents: long, deep research reports, one per question. For example, "What is wu-wei?" or "What is life?". A stack of files like this is hard to use. You cannot see how the ideas connect. You cannot find every place two authors disagree.

research-wiki sits between you and those documents. It reads them and builds three things: a linked wiki, a browsable atlas, and a searchable copy of the source text. The model does the reading and writing. You stay the editor.

The source documents are never changed. The skill only reads them.

---

## What it does

- It **reads each source** and pulls out the key concepts and thinkers. Each one becomes its own note.
- It **links the notes** to each other, so you can see what relates to what.
- It **compares the sources**. Where several agree, it writes a **theme**. Where they disagree, it writes a **debate**, with both sides quoted and cited.
- It **builds an atlas**: one web page with a map of the ideas, a search box, and a reading pane.
- It **makes the source text searchable**, so you can ask plain questions and get answers from the real documents, not from a summary.

---

## What you need to run it

- **Claude Code.** research-wiki is a skill you run inside it.
- **Your source documents.** One folder per report, as HTML or markdown. A separate research pipeline makes these. research-wiki only reads them.
- **Python** with a few libraries: `markdown`, `beautifulsoup4`, `networkx`, `PyYAML` (and `pytest` to run the tests).
- **Two optional helper skills.** The wiki still works without them, with less polish:
  - **semantic-search** — powers the atlas search box and the "ask the corpus" answers. It reads an `OPENAI_API_KEY` from your environment or `~/.env`.
  - **graphify** — groups the ideas into colored clusters on the map.

Install the Python parts:
```bash
pip install markdown beautifulsoup4 networkx pyyaml pytest graphifyy
```

---

## How it works

You drive it with four commands.

| Command | What it does |
|---|---|
| `/research-wiki ingest <folder>` | Read one source document. Turn its concepts and thinkers into wiki notes. |
| `/research-wiki batch <folder>` | Do a whole folder of finished documents. It reads them one at a time, checks its work as it goes, and ends with a full analysis. Safe to re-run. |
| `/research-wiki analyze` | Compare the sources. Write the themes and debates. Fix broken links. Rebuild the atlas and the search index. |
| `/research-wiki ask "<question>"` | Answer a question from the wiki. Add `--file` to save the answer. |

The normal flow: **ingest** (or **batch**) your documents, then **analyze**. `analyze --full` also writes a full narrative for every note, groups the map into clusters, and rebuilds the web page.

### Example
```
/research-wiki batch "5_Chapter 5"
  → reads every finished report in the folder
  → concepts/…, thinkers/…, debates/…, themes/… all written
  → wiki.html and the search index rebuilt

/research-wiki ask "does cognition require being alive?"
  → an answer that cites [Thompson, 2022] against [Levin, 2023]
    and links [[debates/does-cognition-require-life]]
```

---

## What you get

- **A linked wiki.** Every concept and thinker is one markdown note. The notes link to each other. You can open the whole thing as an [Obsidian](https://obsidian.md) vault.
- **Themes and debates.** Cross-source notes that show where the authors agree and where they clash, with quotes and citations.
- **One atlas web page (`wiki.html`).** It holds a map of the ideas (colored by cluster), a search box, and a reading pane. It is one self-contained file. It needs no server and no Obsidian. You can share it.
- **A searchable copy of the source text.** You can ask plain questions and get answers grounded in the real documents.
- **Deep-links.** Each note links down to the exact section of the source it came from.

Today's wiki holds 50 source documents: 655 concepts, 427 thinkers, 35 debates, 24 themes, and 19 topic clusters. Every concept and thinker note carries a full narrative.

---

## What you can do with it

- **Browse the whole field** on one page, and follow the links between ideas.
- **Find the fault lines** fast. The debates collect every real disagreement in one place.
- **Chat with the sources.** Ask a question in plain words and get a cited answer from the primary text.
- **Trace any claim** back to the exact source section through the deep-links.
- **Share the atlas** as a single file, or host it. This project runs it password-protected on Railway.
- **Keep it growing.** Each new document you ingest makes the map richer. Re-run analyze to find the new agreements and clashes.

---

## The tooling (Python)

`analyze` and `batch` run these for you. You can also run them alone.

- **`build_wiki_html.py`** — builds the atlas `wiki.html` from the notes and the graph.
- **`extract_sources.py`** — turns the source HTML into clean, section-sized text for search, and records the section anchors for deep-links.
- **`match_sources.py`** — links each note to the right source section.
- **`scripts/batch_ingest.py`** — plans and tracks a full folder run (ingest, then analyze).
- **`scripts/enrich_splice.py`** — writes the narrative lead into each note.
- **`scripts/build_cluster_briefs.py`** and **`scripts/validate_cluster_notes.py`** — build the cluster notes and check that every link resolves.
- **`scripts/publish_source_html.py`** — copies each source's readable HTML into the wiki, and removes export junk.
- **`export_obsidian.py`** — writes the wiki as Obsidian-native notes (title filenames, bare `[[Title]]` links) into a folder of your choosing.

Run the tests:
```bash
python3 -m pytest tests/ -q
```

---

## Export to Obsidian

The wiki's links are path-qualified (`[[concepts/wu-wei]]`) because the atlas, the cluster checks, and the procedures all key on `type/slug`. Obsidian can open the wiki folder as it is, but its own idiom is one note per title and bare `[[Title]]` links. `export_obsidian.py` writes that form into a folder of your choosing, outside the wiki, and leaves the wiki untouched:

```bash
python3 -B export_obsidian.py --wiki /path/to/wiki --out ~/Vault/research-wiki
```

- It exports the literature, concept, thinker, debate, theme and answer pages, plus the cluster essays in `clusters/` as written (the atlas's generated member lists are not reproduced). `index.md`, `log.md`, `about.md` and `reports/` are the wiki's own apparatus and stay behind.
- One note per page, named by its `title:`. When two pages share a title, the debate gets `(Debate)`, the theme `(Theme)`, the cluster `(Cluster)`, and any other clash gets the page's first literature slug. If that still clashes, the export stops and names the pages.
- Every `[[type/slug]]` and `[[type/slug|alias]]` link becomes `[[Title]]` / `[[Title|alias]]`. A link to a page that does not exist is left as it is and listed; `--strict` makes that an error.
- Frontmatter is copied as written, plus a `description` (the first sentence or two of the note, 150 characters at most). `aliases` carry through, so Obsidian resolves them.
- `_manifest.json` in the output folder records `type/slug` → filename and is the ownership record. The export never overwrites or removes a file it did not write (a page whose filename is taken by such a file is left out and reported, and links to it stay path-qualified), and it refuses a manifest it did not write. Re-running is safe: a note you have edited by hand is left alone and reported, and a note whose page is gone is kept. `--force` rewrites the first kind and removes the second.

---

## Repo layout
```
research-wiki/
  SKILL.md          # the skill: commands, safety rules, dispatch
  references/       # the exact steps for ingest / batch / analyze / ask + page templates
  scripts/          # batch, enrich, cluster, and publish helpers
  build_wiki_html.py  extract_sources.py  match_sources.py  export_obsidian.py
  tests/
  README.md  HANDOVER.md
```

This repo is the **tooling**. The wiki content — the notes, the atlas, the extracted text, the graph — lives in a separate folder.

---

## Safety

The source documents are read-only. No command ever writes to, moves, or deletes them. The wiki lives in its own folder and its own git repo.

## Setup note

The skill is wired to one author's paths (`/Users/noahraford/magic/…`). To reuse it, change the paths at the top of the Python scripts and in `SKILL.md` and `references/`. No API keys live in the code.
