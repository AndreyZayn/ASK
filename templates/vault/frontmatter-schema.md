---
title: Frontmatter Schema
description: The metadata fields every note carries and how relations are written.
kind: schema
scope: shared
lifecycle_status: stable
updated: {{DATE}}
tags: ["schema"]
governed_by:
  - "[[Agents/rules/knowledge-work]]"
---
# Frontmatter Schema

Every note starts with flat YAML frontmatter. The machine-readable schema lives in the workspace next to the configuration file; the owner may extend its `kind`, `scope`, and `lifecycle_status` values there. ASK supports a documented subset of YAML and JSON Schema, described in the public distribution's `docs/schema.md`.

## Required fields

- `title` — unique across the vault
- `description` — one sentence
- `kind` — note type; paths ending in `INDEX.md` are `index`, and non-index notes under `Agents/rules/` are `rule`
- `scope` — `shared`, `personal`, `work`, or `side`
- `lifecycle_status` — `draft`, `active`, `stable`, `archived`, `empty`, `placeholder`, or `needs-update`
- `updated` — ISO date, `YYYY-MM-DD`

## Optional fields

`tags` (list), `project`, `domain`, `source` (text), `canonical` (`true` or `false`), and the relation lists `governed_by`, `depends_on`, `derived_from`, `associated_with`.

## Relations

Relation entries are quoted wikilinks to a whole note, written as the path from the vault root without `.md`. No aliases, headings, block references, embeds, or URLs.

```yaml
---
title: Example Decision
description: Why the example option was chosen.
kind: decision
scope: work
lifecycle_status: active
updated: 2000-01-01
tags: ["example"]
governed_by:
  - "[[Agents/rules/knowledge-work]]"
derived_from:
  - "[[Projects/example-project]]"
---
```

The example above is illustrative; links inside code are not checked. Typed relations must be quoted, vault-root-relative whole-note wikilinks with unique, existing targets. They cannot use aliases, headings, block references, embeds, or URLs.
