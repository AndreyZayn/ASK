# Install ASK (macOS)

ASK installs a complete private workspace: `Knowledge Base/`, `system/` (including the installed scripts), and `artifacts/` are siblings within the chosen ASK folder. The public source checkout is only an installer and remains separate from private data. Use a new private workspace, not an existing Obsidian vault. Install Python 3.9+, Git, and GitHub CLI (`gh`); authenticate `gh` to create or use a **private** GitHub repository. Obsidian is optional.

```sh
git clone https://github.com/AndreyZayn/ASK.git ask-public
cd ask-public
python3 scripts/ask.py setup --workspace /path/to/your-workspace --repository OWNER/NAME --create-repository --runtime codex
```

Replace `OWNER/NAME` with your intended private repository. For an existing private repository, omit `--create-repository`. To start without a repository, omit both repository flags: setup leaves a usable local workspace in `setup-pending` state and exits 2; remote backup is not complete. Do not turn an authentication or privacy check failure into a success claim.

Choose `--runtime claude`, `codex`, `amp`, `droid`, `antigravity`, or a manual runtime such as `cursor` or `generic` for the agent you actually use. You can add `--read-only` to avoid content-writer declarations or `--backup scheduled` for optional scheduled backup. Setup creates `ask.json`, `note.schema.json`, a workspace `AGENTS.md`, the `Knowledge Base/` notes, `system/` with its portable scripts and guides, and `artifacts/` for private working outputs. After setup, run `python3 /path/to/your-workspace/system/scripts/ask.py` for normal ASK commands; the original checkout is not required. Its runtime configuration is **configured-unverified** until you test a new session. Every agent installing ASK must proactively persist the four-note bootstrap in its actual runtime, preserve foreign instructions, and report any registration it cannot do automatically for manual completion. See [runtime verification](runtime.md).

To view your notes, open Obsidian and choose **Open folder as vault**, then select `/path/to/your-workspace/Knowledge Base`, not the public checkout or the workspace root. No ASK plugin is required. The notes also work in a text editor.

Use `artifacts/` for private working outputs that do not belong in the Markdown graph. To include an owner-approved artifact in the private Git backup, review it and checkpoint its individual path, for example `python3 /path/to/your-workspace/system/scripts/ask.py checkpoint --config /path/to/your-workspace/ask.json --files artifacts/example.txt --message "Save working artifact" --owner-approved`. Scheduled backup handles eligible vault notes only; it does not automatically checkpoint artifacts or system files. Never put credentials in a checkpoint. A local commit remains backup pending until it is pushed to the verified private remote.

For an existing vault, do not run setup into it or overwrite its notes. Review a separate ASK workspace and merge only the notes and settings you choose. For remote work, use an owner-provided authenticated connection to the machine holding the private workspace; setup does not grant remote filesystem access or configure your network.

See [backup, recovery, and uninstall](backup.md) and [upgrades](upgrades.md). Access declarations in configuration are guidance, not enforcement; the owner controls actual runtime permissions.

After technical setup, complete [identity and capability onboarding](onboarding.md). Runtime registration, roster identity, observed capability documentation, and backup are separate outcomes. `doctor` checks technical readiness, not whether those human-facing records are complete.

## Choose the Git commit identity

GitHub authentication and commit authorship are separate. ASK checkpoints require repository-local `user.name` and `user.email`; a global identity alone is intentionally insufficient. Before the first backup, explain the choice: authenticated `setup --repository` fills missing local fields from the signed-in GitHub account, using its login and GitHub noreply address. It preserves existing local fields and does not change global Git settings or account settings. Do not claim backup success if identity lookup, commit, or push fails.

For a different owner-chosen identity, first run `setup --workspace /path/to/your-workspace` without repository flags. This intentionally returns `setup-pending` (exit 2). Then check the two local fields and fill only missing ones with the owner's chosen values:

```sh
git -C /path/to/your-workspace config --local --get user.name
git -C /path/to/your-workspace config --local --get user.email
git -C /path/to/your-workspace config --local user.name "CHOSEN_NAME"
git -C /path/to/your-workspace config --local user.email "CHOSEN_EMAIL"
```

Use the owner's exact GitHub noreply address if they choose it; do not guess account identifiers or copy credentials. Review existing fields before replacing either. Create the initial local baseline described below, then rerun the original setup command with the intended private repository and runtime to complete backup/enrollment. An offline local checkpoint can then commit, but it remains backup pending until a verified push succeeds. The roster's local agent ID is separate from the owner's Git author identity.

## Initial local baseline before offline onboarding

A fresh offline setup creates untracked files. Before roster/capability edits or narrow checkpoints, commit that generated baseline. Save the JSON output of the **first** setup outside the workspace (exit 2 with `setup-pending` is expected):

```sh
python3 scripts/ask.py setup --workspace /path/to/your-workspace > /path/to/initial-setup.json
```

After configuring the repository-local identity, review `initial_checkpoint_files` in that trusted output. It enumerates only files the initializer created, including configuration and the generated vault, with workspace-relative paths. It excludes `.ask`, unrelated files subsequently added anywhere in the workspace/vault, and other staged work. Review current contents of those exact files before committing. Do not replace this list with `git add .`, a directory glob, or a scan of untracked files.

Using the installed tools, checkpoint the reviewed list:

```sh
python3 - /path/to/initial-setup.json <<'PY'
import json
from pathlib import Path
import subprocess
import sys
report = json.loads(Path(sys.argv[1]).read_text())
files = report.get('initial_checkpoint_files')
if not files:
    raise SystemExit('Missing initial manifest; stop and review the existing installation manually.')
raise SystemExit(subprocess.call([
    sys.executable, str(Path(report['workspace']) / 'system/scripts/ask.py'), 'checkpoint',
    '--config', str(Path(report['workspace']) / 'ask.json'),
    '--files', *files, '--message', 'Initialize generated ASK baseline', '--owner-approved',
]))
PY
```

Exit 2 with `committed: true` and `backup_pending: true` is a successful local baseline without remote backup. A rejected checkpoint is not a commit: resolve only the reported condition and retry. Pre-existing staged work is preserved and blocks the checkpoint; do not reset or include another person's work. Once the baseline exists, continue the narrow onboarding checkpoints and later configure/sync the private remote.

A rerun does not reconstruct this manifest from the working directory. An existing installation without a first commit must use its saved trusted manifest or have an agent explicitly review and enumerate the initial owned files before checkpointing. Do not reinitialize or infer that all current files belong to ASK. `setup --repository` refuses that uncommitted existing baseline before contacting GitHub; a genuinely fresh one-step repository setup can checkpoint its exact newly generated list automatically.
