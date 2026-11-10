# Upgrading ASK

Update the **public** ASK checkout separately from the private workspace. Compare the installed schema and each template with its new distribution version. Apply only reviewed differences; upgrades must not automatically overwrite customized private notes, frontmatter, indexes, rules, or configuration.

Treat `date.md`, `goals.md`, root `INDEX.md`, Projects, People, Personal, Tasks, Memory, and ordinary `Agents/capabilities/` content as routine editable notes when authorized. `agents.md`, `knowledge-map.md`, `knowledge-continuity-loop.md`, schema and tag taxonomy, `Agents/rules/**`, the roster, and ontology are protected and need explicit owner direction for changes. `date.md` and `INDEX.md` are **not** protected simply because they are bootstrap notes. Changing bootstrap order or access declarations also needs owner direction.

Review diffs for link and frontmatter compatibility, validate the updated private vault, and verify any changed runtime bindings in a new session. Never copy a raw private folder or history into the public distribution. See [public promotion](public-promotion.md) for sanitized, generic contributions.

## Adopting path profiles and the expanded starter structure

Updating public scripts does not change installed templates or schemas. Schemas without `x-ask-path-rules` continue using their existing common-field rules. To adopt the expanded roles, software loops, completion guidance, and profiles, review the new templates beside your existing notes. Add only missing generic material, merge indexes and routing deliberately, and preserve existing owner policy. Do not rerun `init` over a vault or copy the entire template tree onto it.

Before enabling profiles, identify affected loop/person/skill state fields, daily/log metadata, project identifiers, and existing tags. Extend the local vocabulary deliberately. Check the full vault in a temporary synthetic or appropriately protected private review workspace; the validator checks all debt, not just edited notes. Commit only the owner-approved changes and recheck staged validation. Reconnecting a managed runtime may refresh only its ASK block; unrelated instructions remain intact and proof must be repeated if the binding changes.
