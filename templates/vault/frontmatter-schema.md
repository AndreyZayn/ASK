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

## Ordinary required fields

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
tags: ["reference"]
governed_by:
  - "[[Agents/rules/knowledge-work]]"
derived_from:
  - "[[Projects/example-project]]"
---
```

The example above is illustrative; links inside code are not checked. Typed relations must be quoted, vault-root-relative whole-note wikilinks with unique, existing targets. They cannot use aliases, headings, block references, embeds, or URLs.

## Path-specific identity and state

The local schema's `x-ask-path-rules` is authoritative. Loop definitions use `kind: loop` and `loop_status`; people details use `kind: person`, `contexts`, and `relationship_status`; skill details use `capability_status`. These profiles replace `lifecycle_status`. Daily plans require `date`, `kind: daily-plan`, personal scope, and `plan_status`. Monthly session logs require `month`, `kind: log`, and personal scope. Daily and log records may omit title, description, and updated; date/month must match the filename. Indexes keep ordinary fields.

Project subtrees declare an owner-defined `project` and work or side scope. Personal notes use personal scope. Capabilities are descriptive and cannot use `kind: rule`. Tags come from the locally configured enum aligned with [[tags]]. With owner direction, extend the schema for project identities, domains, and vocabulary; never copy another user's inventory. See the distribution's `docs/schema.md` for matching and override semantics. Existing schemas are not migrated automatically.
