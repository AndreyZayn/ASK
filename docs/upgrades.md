# Upgrading ASK

Update the **public** ASK checkout separately from the private workspace. Compare the installed schema and each template with its new distribution version. Apply only reviewed differences; upgrades must not automatically overwrite customized private notes, frontmatter, indexes, rules, or configuration.

Treat `date.md`, `goals.md`, root `INDEX.md`, Projects, People, Personal, Tasks, Memory, and ordinary `Agents/capabilities/` content as routine editable notes when authorized. `agents.md`, `knowledge-map.md`, `knowledge-continuity-loop.md`, schema and tag taxonomy, `Agents/rules/**`, the roster, and ontology are protected and need explicit owner direction for changes. `date.md` and `INDEX.md` are **not** protected simply because they are bootstrap notes. Changing bootstrap order or access declarations also needs owner direction.

Review diffs for link and frontmatter compatibility, validate the updated private vault, and verify any changed runtime bindings in a new session. Never copy a raw private folder or history into the public distribution. See [public promotion](public-promotion.md) for sanitized, generic contributions.
