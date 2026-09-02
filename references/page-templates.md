# Page templates

Every wiki page is plain markdown with a YAML frontmatter block followed by a body. Use the exact frontmatter fields and body template for the page's type. All paths absolute: pages live under `$WIKI_ROOT/<type>/<slug>.md`.

## Frontmatter (all types)

```yaml
---
type: literature | concept | thinker | debate | theme | answer
slug: <kebab-case-slug>
title: <Human Title>
aliases: [<alt name>, <alt name>]
literature: [<source-slug>, <source-slug>]
status: stub | draft | mature
updated: YYYY-MM-DD
---
```

- `type` — one of the six values above; matches the directory the page lives in.
- `slug` — kebab-case, derived from the title; unique within the type.
- `aliases` — alternate surface names; the dedup key (see Alias rules).
- `literature` — every source that contributes to this page; the provenance key `analyze` uses to find pages spanning ≥2 sources.
- `status` — `stub` (<2 claims / thin), `draft` (has real content), `mature` (well-developed, cross-linked).
- `updated` — bump to today on every write that touches the page.

## Body template — source

```markdown
# <Source title>

**Core question:** <the source's driving question, one sentence>
**Method note:** <corpus size, rounds, source counts — from the source's own method note>

## Overview
<2–4 short paragraphs of narrative synthesis. ORDER MATTERS: FIRST introduce and explain
the core idea(s) the source is about — what they are, in plain terms, and how they work —
so a reader who knew nothing walks away understanding the substance. ONLY THEN turn to the
debate: the competing positions, disagreements, and open questions. Explanation before
controversy; never lead with the debate. Grounded in the Position map and the source's own
text — not model priors. This is what makes the source page teach the ideas like the
enriched concept pages, rather than read as a bare index of who-disagrees-with-whom.>

## Position map
<The source's enumerated positions/answers, one line each, with lead thinker + key citation.>

## Key sources
<10–20 sources by tier: - [Surname, YYYY] — title (tier N)>

## Pages from this source
**Concepts**
- [[concepts/<slug>]]
- ...

**Thinkers**
- [[thinkers/<slug>]]
- ...
```

"Pages from this source": one link per bullet, grouped by kind (Concepts, then Thinkers,
then Debates/Themes/Answers if present) — never a dot-joined inline run.

## Body template — concept AND thinker

Concept and thinker pages share one template. The preamble is a one-paragraph definition (concept) or identity (thinker). Each source contributes exactly one `## In <source-slug>` section.

```markdown
# <Title>

<One-paragraph definition/identity — cited.>

## In <source-slug-1>
<How THIS source treats it: positions, claims, each with [Surname, YYYY] citations.>

## In <source-slug-2>
...

## See also
- [[<type>/<slug>]] — <one-line reason>
```

## Body template — debate

The positions table is mandatory. One row per position; every row names who holds it, the source(s), and a citation.

```markdown
# <Contested question>

<One paragraph: what is contested and why it matters.>

| Position | Held by | Source(s) | Key citation | Evidence (one line) |
|---|---|---|---|---|
| ... | [[thinkers/x]] | [[literature/y]] | [Surname, YYYY] | ... |

## Where the literature agrees
## Open questions
```

## Body template — theme

```markdown
# <Theme name>

<One paragraph: the emergent pattern and which sources carry it.>

## Evidence from the literature
- [[literature/<slug>]] — <how it shows up here> [Surname, YYYY]

## Related
- [[debates/<slug>]] · [[concepts/<slug>]]
```

## Body template — answer

```markdown
# <Question as asked>

<The answer: every claim cited [Surname, YYYY] with a path-qualified wikilink
to the page it came from; disagreements flagged with a [[debates/<slug>]] link.>

## Drawn from
- [[literature/<slug>]] · [[concepts/<slug>]] · ...
```

## Citation grammar

Accepted forms (normative for both parsing and writing):
- `[Surname, YYYY]`
- multi-cite `[A, YYYY; B, YYYY]`
- locator `[Surname, YYYY, ch. N]` / `[Surname, YYYY, p. N]` / `[Surname, YYYY, pp. N–M]`

Bracketed text NOT matching this grammar (e.g. `[see the liminality literature reviewed in Thomassen…]`) is prose — carry it verbatim, never index it as a citation. Every claim on a wiki page keeps its citation AND names its source (via the `## In <source-slug>` section it sits in). A claim with neither is forbidden.

**Surname resolution:** the surname in `[Surname, YYYY]` is grounded in the source's SECTION PROSE (the text names "Victor Turner" beside `[Turner, 1969]`), NOT in `bibliography.md`/`.bib` — those files are title/url/year lists with no author field. Never try to resolve a citation's author from the bibliography; copy the citation exactly as the section wrote it.

## Merge rule

Section-scoped replace. Ingesting source B writes or replaces ONLY the `## In <B>` section of a concept/thinker page (creating it if absent), and never touches other sources' sections or the page preamble. This is what makes re-ingest with `--force` safe: the same section is replaced, producing no duplicates and no cross-source corruption.

## Alias rules

`aliases` is the dedup key: on ingest, match a candidate entity against existing pages' slugs + aliases (same type only) before creating a new page. Aliases must be unique across pages of the same type. If a new page would claim an alias already held by another page of that type, do NOT add the alias — record the conflict so the next `analyze` report surfaces it for human judgment.

## Index line format

`index.md` groups pages under per-type headings (`## Literature`, `## Concepts`, `## Thinkers`, `## Debates`, `## Themes`, `## Answers`). Each entry is one line:

```
- [[<type>/<slug>]] (N sources) — <one-line hook>
```

`N` is the count in the page's `sources:` frontmatter. `index.md` is the primary navigation; search is a fallback.

## Slug rules

**Source slugs are the source directory's basename, verbatim** — do NOT lowercase or otherwise normalize them. Real source slugs contain uppercase (e.g. `ch1-q1-non-western-AI`); changing the case breaks the `[[literature/<slug>]]` link target and the `--all` completeness check. Concept, thinker, debate, theme, and answer slugs ARE normalized kebab-case, derived from the title.

Collision check at creation:

```bash
test -f $WIKI_ROOT/<type>/<slug>.md
```

If it exists, it is either the same entity (merge into it, section-scoped) or a genuine different entity of the same type (disambiguate the slug, e.g. append a distinguishing word). Slugs are unique within a type; cross-type same-slug is fine because wikilinks are path-qualified.
