# Page templates

Every wiki page is plain markdown with a YAML frontmatter block followed by a body. Use the exact frontmatter fields and body template for the page's type. All paths absolute: pages live under `/Users/noahraford/magic/wiki/<type>/<slug>.md`.

## Frontmatter (all types)

```yaml
---
type: bible | concept | thinker | debate | theme | answer
slug: <kebab-case-slug>
title: <Human Title>
aliases: [<alt name>, <alt name>]
bibles: [<bible-slug>, <bible-slug>]
status: stub | draft | mature
updated: YYYY-MM-DD
---
```

- `type` — one of the six values above; matches the directory the page lives in.
- `slug` — kebab-case, derived from the title; unique within the type.
- `aliases` — alternate surface names; the dedup key (see Alias rules).
- `bibles` — every source bible that contributes to this page; the provenance key `analyze` uses to find pages spanning ≥2 bibles.
- `status` — `stub` (<2 claims / thin), `draft` (has real content), `mature` (well-developed, cross-linked).
- `updated` — bump to today on every write that touches the page.

## Body template — bible

```markdown
# <Bible title>

**Core question:** <the bible's driving question, one sentence>
**Method note:** <corpus size, rounds, source counts — from the bible's own method note>

## Position map
<The bible's enumerated positions/answers, one line each, with lead thinker + key citation.>

## Key sources
<10–20 sources by tier: - [Surname, YYYY] — title (tier N)>

## Pages from this bible
- [[concepts/<slug>]] · [[thinkers/<slug>]] · ...
```

## Body template — concept AND thinker

Concept and thinker pages share one template. The preamble is a one-paragraph definition (concept) or identity (thinker). Each source bible contributes exactly one `## In <bible-slug>` section.

```markdown
# <Title>

<One-paragraph definition/identity — cited.>

## In <bible-slug-1>
<How THIS bible treats it: positions, claims, each with [Surname, YYYY] citations.>

## In <bible-slug-2>
...

## See also
- [[<type>/<slug>]] — <one-line reason>
```

## Body template — debate

The positions table is mandatory. One row per position; every row names who holds it, the source bible(s), and a citation.

```markdown
# <Contested question>

<One paragraph: what is contested and why it matters.>

| Position | Held by | Source bible(s) | Key citation | Evidence (one line) |
|---|---|---|---|---|
| ... | [[thinkers/x]] | [[bibles/y]] | [Surname, YYYY] | ... |

## Where the bibles agree
## Open questions
```

## Body template — theme

```markdown
# <Theme name>

<One paragraph: the emergent pattern and which bibles carry it.>

## Evidence by bible
- [[bibles/<slug>]] — <how it shows up here> [Surname, YYYY]

## Related
- [[debates/<slug>]] · [[concepts/<slug>]]
```

## Body template — answer

```markdown
# <Question as asked>

<The answer: every claim cited [Surname, YYYY] with a path-qualified wikilink
to the page it came from; disagreements flagged with a [[debates/<slug>]] link.>

## Drawn from
- [[bibles/<slug>]] · [[concepts/<slug>]] · ...
```

## Citation grammar

Accepted forms (normative for both parsing and writing):
- `[Surname, YYYY]`
- multi-cite `[A, YYYY; B, YYYY]`
- locator `[Surname, YYYY, ch. N]` / `[Surname, YYYY, p. N]` / `[Surname, YYYY, pp. N–M]`

Bracketed text NOT matching this grammar (e.g. `[see the liminality literature reviewed in Thomassen…]`) is prose — carry it verbatim, never index it as a citation. Every claim on a wiki page keeps its citation AND names its source bible (via the `## In <bible-slug>` section it sits in). A claim with neither is forbidden.

**Surname resolution:** the surname in `[Surname, YYYY]` is grounded in the bible's SECTION PROSE (the text names "Victor Turner" beside `[Turner, 1969]`), NOT in `bibliography.md`/`.bib` — those files are title/url/year lists with no author field. Never try to resolve a citation's author from the bibliography; copy the citation exactly as the section wrote it.

## Merge rule

Section-scoped replace. Ingesting bible B writes or replaces ONLY the `## In <B>` section of a concept/thinker page (creating it if absent), and never touches other bibles' sections or the page preamble. This is what makes re-ingest with `--force` safe: the same section is replaced, producing no duplicates and no cross-bible corruption.

## Alias rules

`aliases` is the dedup key: on ingest, match a candidate entity against existing pages' slugs + aliases (same type only) before creating a new page. Aliases must be unique across pages of the same type. If a new page would claim an alias already held by another page of that type, do NOT add the alias — record the conflict so the next `analyze` report surfaces it for human judgment.

## Index line format

`index.md` groups pages under per-type headings (`## Bibles`, `## Concepts`, `## Thinkers`, `## Debates`, `## Themes`, `## Answers`). Each entry is one line:

```
- [[<type>/<slug>]] (N bibles) — <one-line hook>
```

`N` is the count in the page's `bibles:` frontmatter. `index.md` is the primary navigation; search is a fallback.

## Slug rules

**Bible slugs are the source directory's basename, verbatim** — do NOT lowercase or otherwise normalize them. Real bible slugs contain uppercase (e.g. `ch1-q1-non-western-AI`); changing the case breaks the `[[bibles/<slug>]]` link target and the `--all` completeness check. Concept, thinker, debate, theme, and answer slugs ARE normalized kebab-case, derived from the title.

Collision check at creation:

```bash
test -f /Users/noahraford/magic/wiki/<type>/<slug>.md
```

If it exists, it is either the same entity (merge into it, section-scoped) or a genuine different entity of the same type (disambiguate the slug, e.g. append a distinguishing word). Slugs are unique within a type; cross-type same-slug is fine because wikilinks are path-qualified.
