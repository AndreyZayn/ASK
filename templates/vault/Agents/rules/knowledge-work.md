---
title: Knowledge Work Rules
description: Default rules for context routing, bounded authority, attribution and validation, and durable continuity.
kind: rule
scope: shared
lifecycle_status: stable
updated: {{DATE}}
tags: ["agents", "rules"]
canonical: true
associated_with:
  - "[[knowledge-continuity-loop]]"
---
# Knowledge Work Rules

These defaults apply to every agent working in this knowledge base. The owner may add or replace rules in [[Agents/rules/INDEX]].

## 1. Context routing

- Read the bootstrap notes in their configured order at each new project/work context.
- Use [[knowledge-map]] and the nearest index to find what a task needs. Do not read the whole vault by default.
- Treat linked Markdown as canonical, not exported graph JSON. Identify sources and assumptions; report conflicts or missing context.
- Route software work through [[Agents/rules/software-work]], communication through [[Agents/rules/communications]], capability changes through [[Agents/rules/capability-management]], and delegation through [[Agents/rules/orchestration]]. Follow [[Agents/rules/knowledge-work]] for all work.

## 2. Bounded authority

- Read and write only within the paths the workspace configuration declares and your runtime actually grants. Lower-level `init` starts read-only; `setup --read-only` also avoids writer declarations. Scoped setup writing still needs owner authority.
- Declarations are guidance, not a sandbox. Never widen your own access.
- Keep changes minimal and scoped to the task. Do not delete, move, or rewrite notes you were not asked to change.
- Keep private material inside the private workspace. Never put credentials in notes or Git; do not send private material to external services without explicit owner approval.
- Routine authorized content/index updates may include Projects, People, Personal, Tasks, Memory, `date.md`, `goals.md`, root `INDEX.md`, and ordinary `Agents/capabilities/` content. Policy (`Agents/rules/**`), schema and tag taxonomy, structure, roster, ontology, `agents.md`, `knowledge-map.md`, `knowledge-continuity-loop.md`, and permission changes require explicit owner direction.

## 3. Attribution and validation

- State where knowledge came from in the `source` field or in the text; record `by` and `upd` in durable content using locally enrolled IDs, not unregistered names.
- Separate facts, decisions, and assumptions. Mark unverified claims as such.
- Keep metadata valid per [[frontmatter-schema]] and run the validator after changing notes.
- Report failures honestly; do not hide or suppress validation errors.

## 4. Durable continuity

- Follow [[knowledge-continuity-loop]]: begin the write marker before edits, record outcomes in the owning note, append one monthly log entry, validate and checkpoint session-owned files, and end the marker.
- Update `updated` and `lifecycle_status` when a note changes meaningfully.
- Link every new note from its nearest index.
