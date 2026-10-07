# Contributor instructions

This repository contains the public, generic ASK distribution: Python tooling, schemas, neutral templates, documentation, and synthetic fixtures. Keep private notes, real identities, owner-specific paths, personal policies, inventories, operational data, and private history out of the repository. Do not add credentials or secrets.

## Workflow

- Keep changes focused on the public framework and preserve the repository's existing license.
- Use synthetic notes and temporary workspaces for examples and checks. Never run initialization against a real private vault.
- Run the test suite with `python3 -m unittest discover -s tests -v` when changing implementation or tests.
- Review generated or changed files for private data and unsafe path assumptions before handing off changes.
- Do not initialize or configure an agent runtime, schedule work, or publish changes as part of repository development unless the owner explicitly requests that action.

## INSTALL intent

When the owner asks to **install ASK**, use [docs/install.md](docs/install.md) and [docs/runtime.md](docs/runtime.md). Installation means completing the private workspace setup, persistently registering the four-note bootstrap in each installing agent's actual runtime, and testing a new session both inside the workspace and in an unrelated directory. Preserve foreign runtime instructions; report unsupported registration as manual work and a connection as `configured-unverified` until evidence supports verification. A local setup without a repository remains usable but is `setup-pending` (exit 2), not a completed backup. Contributor review or framework development alone must not mutate a real runtime or private workspace. A delegated worker with `KB_ACCESS: none` must not bootstrap or read private knowledge.

## Boundaries

Markdown notes with frontmatter and wikilinks are the knowledge source of truth. Graph JSON is derived output. SQLite is reserved for a possible future Agent Task Board and is not the knowledge graph. Access declarations in ASK configuration are guidance; runtime permissions remain under the workspace owner's control.

Authorized routine writing includes Projects, People, Personal, Tasks, Memory, `date.md`, `goals.md`, root `INDEX.md`, and ordinary `Agents/capabilities/` content. Protected changes to `agents.md`, `knowledge-map.md`, `knowledge-continuity-loop.md`, schema or tag taxonomy, `Agents/rules/**`, roster, and ontology require explicit owner direction. Never assume text enforces these boundaries.

The public repository is independent of any private workspace and its history. Keep examples synthetic and templates generic.
