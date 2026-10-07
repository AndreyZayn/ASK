# ASK — Agentic Knowledge System

ASK is a local-first framework for a private, Obsidian-compatible Markdown knowledge base. Notes with frontmatter and wikilinks are canonical; graph JSON is derived. This public repository contains generic Python tooling, schemas, templates, and documentation, not anyone's private knowledge.

## Install

On macOS, install Python 3.9+, Git, and GitHub CLI (`gh`), then authenticate `gh` for private-repository setup. Keep the private workspace outside this public checkout.

```sh
git clone https://github.com/AndreyZayn/ASK.git ask-public
cd ask-public
python3 scripts/ask.py setup --workspace /path/to/your-workspace --repository OWNER/NAME --create-repository --runtime codex
```

Replace `OWNER/NAME` with the private repository you intend to use. Omit `--create-repository` for an existing private repository. If you omit `--repository` entirely, setup creates a usable local workspace but returns exit status 2 (`setup-pending`) until backup is bound. Choose `--runtime claude`, `codex`, `cursor`, or `generic`; `--read-only` avoids content-writer declarations, and `--backup scheduled` requests scheduled backup. Do not assume that runtime configuration means the agent has verified access.

Open `/path/to/your-workspace/Knowledge Base` as a vault in Obsidian, if you use Obsidian. No plugin is required. See [installation](docs/install.md), [runtime verification](docs/runtime.md), [backup and recovery](docs/backup.md), and [upgrades](docs/upgrades.md).

## Boundaries

The four bootstrap notes, in order, are `date.md`, `INDEX.md`, `agents.md`, and `knowledge-map.md`. Each installing agent should persist that bootstrap in its actual runtime, preserving unrelated instructions. Runtime access and owner authority, not template text or `ask.json` declarations, determine what an agent may do. A worker assigned `KB_ACCESS: none` must not read or bootstrap private knowledge.

The intended routine content scope includes Projects, People, Personal, Tasks, Memory, `date.md`, `goals.md`, `INDEX.md`, and ordinary Agents/capabilities content, subject to actual configured access and owner authorization. Policy, schema, taxonomy, roster, ontology, and the other protected bootstrap/rule notes require owner direction. Do not publish private notes or secrets.

Read [architecture](docs/architecture.md) and [schema](docs/schema.md) for the data model. [Public promotion](docs/public-promotion.md) explains how to generalize improvements without importing private history.
