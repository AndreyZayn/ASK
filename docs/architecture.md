# Architecture

ASK is a complete local working system containing an Obsidian-compatible knowledge base, reusable software, and a place for functional working artifacts. Markdown notes with YAML frontmatter and wikilinks are the canonical records. Obsidian can render and navigate them, but ASK does not require Obsidian or a plugin.

## Files and responsibilities

- `templates/vault/` contains neutral Markdown notes copied into a new private workspace. The default bootstrap order is `date.md`, `INDEX.md`, `agents.md`, `knowledge-map.md`.
- `scripts/note_schema.py` defines generic machine validation rules; the vault describes the corresponding human-readable schema.
- `scripts/ask.py` is the Python 3.9+ standard-library entry point. The V1 controller provides setup, runtime connection and status, write markers, scoped checkpoints, sync, backup, validation, bootstrap output, and graph export. See [install.md](install.md), [runtime.md](runtime.md), and [backup.md](backup.md).
- The installed `system/` contains scripts, schemas, templates and guides; `artifacts/` holds private working files outside the graph. The installed scripts are the execution source for hooks, agent guidance and scheduled backup.
- `install-manifest.json` lists the reviewed distribution files copied into an installation. Update it when adding or removing public scripts, schemas, templates, documentation or the root README/license; unlisted local checkout files are never installed.
- Default workspace locations and validation rules are defined in installed scripts. Existing legacy `ask.json` installations remain readable without migration.
- The generated workspace-root `AGENTS.md` tells an agent how to read the configured bootstrap notes and where to find its local policy.

## Initialization and configuration

Run `python3 scripts/ask.py setup --workspace PATH [--repository OWNER/NAME --create-repository] [--runtime claude|codex|amp|droid|antigravity|cursor|generic] [--read-only] [--backup scheduled]` to install. The default vault folder is `Knowledge Base`. Setup copies the portable tools, guides, templates and schema into `system/`, renders `{{DATE}}` for the vault, and creates `artifacts/` and a workspace-root `AGENTS.md`. After setup, use the installed `system/scripts/ask.py`; normal use does not depend on the original public checkout. It can bind a private repository, install a staged-snapshot pre-commit hook without overwriting custom hooks, and configure the selected runtime without replacing foreign instructions. Omitting `--repository` leaves a usable local `setup-pending` workspace (exit 2). An installed runtime remains `configured-unverified` pending a real new-session test.

The lower-level `init --workspace PATH [--vault-name NAME]` creates a local read-only-declared workspace without remote or runtime setup. Do not run either initialization command into an existing vault or inside the public checkout. Runtime registration does not grant operating-system permissions.

In version 1 configuration, `vault_root` is relative to the config file or an explicit absolute owner-selected path; `schema_path` is relative to the config file and cannot use traversal; and `bootstrap_files` is an ordered list of vault-relative notes. Bootstrap and `access.read` / `access.write` paths cannot be absolute, contain a `..` segment, or escape the vault. Lower-level `init` defaults to `access.read` of `["."]` and `access.write` of `[]`. Setup provides a `--read-only` option or scoped content-writer declarations. Changes to bootstrap order and access declarations need owner direction.

Access declarations tell an agent what the owner intends it to read or write. They do not enforce access. The agent runtime's actual filesystem permissions control what it can reach, so the owner must constrain runtime access and explicitly grant any desired write permission.

## Validation and bootstrap

`validate --config PATH [--json]` checks note metadata and links against the private schema and configured vault. `bootstrap --config PATH [--output PATH]` prints an agent adapter that reflects the configured bootstrap order and access declarations; printing it is not runtime registration or verification. An explicit output path must be new and outside both the distribution and private vault. `agent verify` prints a real-session proof procedure, and `--evidence JSON_FILE` records controller-observed evidence; it does not secretly invoke an agent. Status and doctor emit JSON.

The default four bootstrap files orient an agent in each new user project context before it follows the knowledge map and nearby indexes. Every installing agent should proactively persist this order in its actual runtime, preserving unrelated instructions and reporting unsupported bindings. Additional templates provide neutral goals, metadata, continuity, project/people/personal indexes, task states, date-routed operational history, requested rollup indexes, and descriptive agent catalogs and policy gates. They are not additional default bootstrap notes. A worker assigned `KB_ACCESS: none` must not bootstrap or read a private vault.

## Derived graph

`graph --config PATH [--output PATH]` emits a deterministic JSON index with vault-relative note IDs, selected metadata, and directed edges. Ordinary Markdown wikilinks become `navigational` edges. The `governed_by`, `depends_on`, `derived_from`, and `associated_with` fields produce directed edges with their corresponding relation names. The exporter validates the vault first. Note integrity findings exit with status `1` and prevent export; configuration, usage, and I/O errors exit with status `2`. Output goes to stdout by default; an explicit output must be a new path outside the distribution and private vault, and is created only after validation succeeds.

The JSON is a derived, read-only view of Markdown. Notes remain canonical, and graph edges do not grant runtime access. Agent task-board services and their scripts are outside the public ASK distribution. Optional scheduled backup does not schedule an AI agent. No hosted service or runtime permission enforcement is bundled.

For native installations, the repository-local Git setting `ask.readOnly` records the advisory write mode. A restored clone defaults to read-only when setup is rerun because Git does not copy local settings. To explicitly permit normal write declarations on that clone, run `git -C /path/to/your-workspace config --local ask.readOnly false` and reconnect the agent runtime. This declaration does not enforce filesystem permissions.
