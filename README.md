# Agentic System Knowledge (ASK)

ASK is a local-first working system: an ASK folder containing a private, Obsidian-compatible Markdown knowledge base, reusable system scripts, and an artifacts directory for working outputs. The knowledge base is the navigable Markdown graph; functional files and outputs live alongside it, outside the vault. Notes are canonical and graph JSON is derived. This public repository contains generic Python tooling, schemas, templates, and documentation, not anyone's private knowledge.

## Start with your agent

On macOS, give your local agent this prompt:

> Install ASK from https://github.com/AndreyZayn/ASK for me. Read AGENTS.md and docs/start-here.md and complete their installation checklist. Create my own complete ASK folder, with Knowledge Base/, system/scripts/, and artifacts/ inside it, and set up my private GitHub backup. Use the installed scripts within that ASK folder after setup. Register this agent in the new workspace’s generated roster, document its actually observed capabilities and discovery coverage with evidence and limits, and persist the four-note bootstrap in its actual runtime, preserving existing instructions. Verify a fresh session inside the workspace and from another directory. Ask for the workspace and repository choices you need, and tell me what remains unverified. Show me which folder to open in Obsidian.

Your agent needs local file and command access. You supply your own agent account and GitHub authentication; ASK has no central registration service. Each person gets their own complete ASK folder and private repository. See [the agent installation checklist](docs/start-here.md), including how to connect another agent later.

ASK's “software” is a small set of Python command-line tools for setup, validation, agent registration, Git synchronization, and optional macOS backup. Your agent runs those tools while you work through conversation. Your knowledge remains ordinary Markdown files that Obsidian can open.

## Command-line installation

On macOS, install Python 3.9+, Git, and GitHub CLI (`gh`), then authenticate `gh` for private-repository setup. Choose a new private ASK folder outside the installer checkout.

```sh
git clone https://github.com/AndreyZayn/ASK.git ask-public
cd ask-public
python3 scripts/ask.py setup --workspace /path/to/your-workspace --repository OWNER/NAME --create-repository --runtime codex
```

Replace `OWNER/NAME` with the private repository you intend to use. Omit `--create-repository` for an existing private repository. If you omit `--repository` entirely, setup creates a usable local workspace but returns exit status 2 (`setup-pending`) until backup is bound. Choose `--runtime claude`, `codex`, `amp`, `droid`, `antigravity`, or a manual runtime such as `cursor` or `generic`; `--read-only` avoids content-writer declarations, and `--backup scheduled` requests scheduled backup. Do not assume that runtime configuration means the agent has verified access.

Setup copies the reusable tools into `ASK/system/` and creates `ASK/artifacts/` beside `ASK/Knowledge Base/`. After installation, run `python3 /path/to/your-workspace/system/scripts/ask.py` for ASK commands; the installer checkout is not needed for normal operation. The private repository is distinct from the public source. Scheduled backup covers eligible vault notes; review and checkpoint artifact files explicitly.

Open `/path/to/your-workspace/Knowledge Base` as a vault in Obsidian, if you use Obsidian. No plugin is required. See [installation](docs/install.md), [runtime verification](docs/runtime.md), [backup and recovery](docs/backup.md), and [upgrades](docs/upgrades.md).

## What a fresh workspace includes

```text
ASK/
├── Knowledge Base/   # private Markdown graph and agent knowledge
├── system/           # installed scripts, templates, schemas, and guides
├── artifacts/        # private working files outside the vault
├── backups/          # optional local recovery files (ignored by Git)
├── staging/          # temporary working files (ignored by Git)
├── AGENTS.md
├── ask.json
└── note.schema.json
```

The starter vault supplies routing, durable knowledge capture, eleven reusable professional hats, five separate software workflows, and a task-completion contract. Configurable path profiles validate note identity, state, and retrieval vocabulary alongside links and nearest-index coverage. See [framework coverage and limits](docs/framework-coverage.md) and the [runtime support matrix](docs/runtime.md#runtime-support-matrix). Existing notes and schema customizations are never upgraded automatically.

## Boundaries

The four bootstrap notes, in order, are `date.md`, `INDEX.md`, `agents.md`, and `knowledge-map.md`. Each installing agent should persist that bootstrap in its actual runtime, preserving unrelated instructions. Runtime access and owner authority, not template text or `ask.json` declarations, determine what an agent may do. A worker assigned `KB_ACCESS: none` must not read or bootstrap private knowledge.

The intended routine content scope includes Projects, People, Personal, Tasks, Memory, `date.md`, `goals.md`, `INDEX.md`, and ordinary Agents/capabilities content, subject to actual configured access and owner authorization. Policy, schema, taxonomy, roster, ontology, and the other protected bootstrap/rule notes require owner direction. Do not publish private notes or secrets.

Read [architecture](docs/architecture.md) and [schema](docs/schema.md) for the data model. [Public promotion](docs/public-promotion.md) explains how to generalize improvements without importing private history.
