# Note schema and links

Every Markdown note has YAML frontmatter. Native workspaces use the literal `SCHEMA` in `system/scripts/asklib/schema.py`, paired with the human-readable `Knowledge Base/frontmatter-schema.md`. Rules are generic; owner-approved changes should keep both aligned. No JSON schema file is created or needed. The Python rule literal uses the constrained object/field vocabulary below; the validator parses it as data without executing Python. Legacy `--config` installations keep using their existing JSON schema unchanged.

## Supported JSON Schema subset

The validator implements only these keywords: `type`, `required`, `properties`, `additionalProperties`, `enum`, `minLength`, `minItems`, `uniqueItems`, `items`, and `format`. The supported formats are `date` (a valid ISO calendar date in `YYYY-MM-DD` form), `month` (`YYYY-MM`), `repository-url` (HTTPS with a host and at least two path components, without credentials/query/fragment), and `wikilink-note` (a quoted whole-note wikilink satisfying the relation rules below). Descriptive annotations such as `title`, `description`, and `$schema` do not add validation behavior. This is not a general JSON Schema engine.

Ordinary notes provide these common fields. The path profiles below can replace the state field or relax operational metadata:

| Field | Meaning |
| --- | --- |
| `title` | Non-empty title, unique across the vault. |
| `description` | Non-empty summary. |
| `kind` | Non-empty note type from the local schema enum. |
| `scope` | Non-empty area from the local schema enum. |
| `lifecycle_status` | Non-empty maintenance state from the local schema enum. |
| `updated` | Valid calendar date in `YYYY-MM-DD` form. |

The supplied schema also defines optional `relationship_status`, `capability_status`, `loop_status`, `contexts`, `repositories`, `aliases`, `cssclasses`, `date`, `month`, `plan_status`, `tags`, `project`, `domain`, `source`, `canonical`, and four typed relation arrays. Arrays use unique values where specified. Unknown fields are rejected by the default `additionalProperties: false`. Owners can adjust the local schema, including enum values, within the supported subset.

Paths ending in `INDEX.md` must use `kind: index`. A non-index note under `Agents/rules/` must use `kind: rule`.

## YAML subset

Frontmatter supports a flat mapping of scalar values and lists of strings. Lists may use block form or flow form. Nested mappings, anchors, aliases, block scalars, duplicate keys, and tabs are unsupported and rejected. The parser does not claim general YAML compatibility.

## Typed relations

The relation fields `governed_by`, `depends_on`, `derived_from`, and `associated_with` contain one or more quoted, vault-root-relative wikilinks to whole notes, for example:

```yaml
governed_by:
  - "[[Agents/rules/knowledge-work]]"
```

Each target must resolve to exactly one note in the vault. Relation paths cannot be absolute or contain a `..` segment. Relation links cannot contain aliases, headings, block references, embeds, external URLs, or `.md` extensions; they cannot repeat, point to the current note, or escape the vault. Missing and ambiguous targets are errors. Relations have direction: if note A declares `depends_on: [[B]]`, the graph contains an edge from A to B; it does not infer an inverse edge.

## Ordinary navigation links

Markdown wikilinks in note bodies are navigational. They may use aliases or headings and can resolve by a path relative to the current note, a vault-root-relative path, or a unique basename. Parent-relative paths containing `../` are allowed when the resolved note remains inside the vault; traversal that escapes the vault and symlink escapes are errors. Missing or ambiguous destinations are errors. Links inside fenced or inline code are examples and are ignored.

Configured bootstrap note paths and `access.read` / `access.write` paths are vault-relative. They must not be absolute, contain a `..` segment, or escape the vault. The configured `schema_path` is relative to the configuration file and must not use traversal. The low-level validator accepts an absolute `vault_root`; V1 setup, runtime enrollment and staged validation use a relative directory inside the private workspace for portability. V1 enrollment requires the four standard bootstrap filenames in their documented order. Use canonical paths on macOS (for temporary workspaces, `/private/tmp` rather than its `/tmp` symlink).

The graph exporter records these links as directed `navigational` edges. It does not replace or rewrite Markdown notes.

## Operational notes

The root `date.md` stores a nondecreasing local date floor. Routine durable records identify a locally enrolled `by` agent and `upd` date in their body; `updated` in frontmatter is the last meaningful note change. Use `source` or prose for provenance and label assumptions. Do not add unsupported `by`/`upd` frontmatter fields to the default schema.

Each authorized vault-writing session appends one entry to `Memory/Logs/YYYY-MM.md` (with `kind: log`, `scope: personal`, and `month: YYYY-MM`). Its index routes by month, so individual session lines are exempt from manual per-record indexing. Daily plans require their date and plan state; rollups retain common fields. The owning project or topic note, not the log, carries decisions and durable state. Weekly and monthly memory summaries require an explicit request.

| Operational note profile | `kind` | Additional guidance |
| --- | --- | --- |
| `Memory/Logs/YYYY-MM.md` | `log` | Require `month` matching filename; keep the owning note authoritative. |
| `Tasks/Daily/YYYY-MM-DD.md` | `daily-plan` | Require matching `date` and `plan_status`; create only when requested. |
| `Memory/Weekly/` or `Memory/Monthly/` dated summaries | `memory` | Create only when requested; link from the corresponding index. |

Ordinary new files need a unique `title`, non-empty `description`, valid `scope`, path-specific state, and `updated` date. Daily plans and monthly session logs use the lighter profiles below. Use `by` and `upd` in the body, not as unrecognized frontmatter fields.

See [upgrades](upgrades.md) for routine editable notes versus protected schema, taxonomy, and policy files. Do not automatically replace private schema customizations during an upgrade.

## Markdown, attachments, and topology

Inline and full/collapsed reference Markdown links are checked relative to their source note, including percent-encoded destinations. Existing local attachments are graph nodes. Image and PDF wikilinks are supported; arbitrary file attachments can use normal Markdown links. Heading and block anchors are not validated. Code examples are ignored. Single-bracket shortcut references are not currently validated.

V1 setup enables nearest-index checks: each ordinary note must be linked from its nearest ancestor `INDEX.md`; each nested index is linked from its parent index. Dated daily plans, monthly logs, and weekly/monthly memory records are routed through their folder index and do not require individual listing. Invalid dated filenames fail validation. `validate --files` records the requested paths but still checks the whole vault, because links and title uniqueness cross file boundaries.

Exit status: 0 valid, 1 content findings, 2 invalid configuration/schema or unavailable operation. `validate --staged` checks only the staged Git snapshot, including its staged configuration and schema.

## Configurable path profiles

`x-ask-path-rules` is an ASK extension to the documented subset, not a standard JSON Schema keyword. It lives in the installed Python rule literal (or the existing JSON schema for a legacy installation). Older schemas without this key retain their existing common-field behavior. No validator run edits the schema or notes.

Rules are ordered objects with `glob`, optional `exclude` patterns, `required`, `optional`, `forbidden` property lists, and `properties` overrides. Patterns are vault-relative, case-sensitive POSIX paths: `*` matches one path segment, `**` matches zero or more segments, and standard fnmatch `?`/character classes work within a segment. Excludes apply only to their own rule. All properties must be declared in the base schema. Later property definitions replace earlier definitions; `optional` removes a field from required fields, `required` adds it, and forbidden fields accumulate. A matched field that is both required and forbidden fails as a configuration error. Unknown profile keywords, unsafe patterns, and invalid field schemas fail closed.

| Default path | Profile |
| --- | --- |
| `Agents/**` | Shared scope; hats are references, rules remain rules, capabilities cannot be rules |
| `Agents/loops/**` except indexes | `kind: loop`, required `loop_status`; no `lifecycle_status` |
| `Agents/capabilities/skills/*/*.md` except indexes | `kind: skill`, `capability_status`; shared folder forbids project |
| `Projects/<Project>/**` | Required owner-defined `project`, work or side scope |
| `Projects/Archive/INDEX.md` | Shared navigation, no project identifier |
| `Personal/**` | Personal scope, no project identifier |
| `People/<scope>/<person>.md` | Person, contexts, relationship state; personal scope forbids project |
| `Tasks/Daily/*.md` except index | Date, daily-plan, personal scope, plan state; no lifecycle state |
| `Memory/Logs/*.md` except index | Month, log, personal scope; no lifecycle state |
| Weekly/monthly memory records | Memory kind and personal scope |

The daily and log profiles make title, description, and updated optional. Their date/month must match the filename. Indexes keep common fields. `repositories` is restricted to `kind: codebase`. The generic `status` field is undeclared and rejected by default.

Extend the local tag enum with owner-approved retrieval facets; keep `tags.md` aligned. To register a project's spelling, scope, domains, or extra tags, append a local profile, for example:

```json
{
  "glob": "Projects/Example/**",
  "properties": {
    "project": {"type": "string", "enum": ["example"]},
    "scope": {"type": "string", "enum": ["work"]}
  }
}
```

A second `Projects/Example/product/**` rule can require `domain` and constrain it to `product`. A project tag override should retain the shared enum and add local facets. The distribution does not infer personal project names or normalize them through a private mapping. Topology retains the standard folder names inside a configurable vault root.
