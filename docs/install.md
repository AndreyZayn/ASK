# Install ASK (macOS)

ASK keeps the public program and your private notes in separate folders. Use a new private workspace, not an existing Obsidian vault. Install Python 3.9+, Git, and GitHub CLI (`gh`); authenticate `gh` to create or use a **private** GitHub repository. Obsidian is optional.

```sh
git clone https://github.com/AndreyZayn/ASK.git ask-public
cd ask-public
python3 scripts/ask.py setup --workspace /path/to/your-workspace --repository OWNER/NAME --create-repository --runtime codex
```

Replace `OWNER/NAME` with your intended private repository. For an existing private repository, omit `--create-repository`. To start without a repository, omit both repository flags: setup leaves a usable local workspace in `setup-pending` state and exits 2; remote backup is not complete. Do not turn an authentication or privacy check failure into a success claim.

Choose `--runtime claude`, `codex`, `cursor`, or `generic` for the agent you actually use. You can add `--read-only` to avoid content-writer declarations or `--backup scheduled` for optional scheduled backup. Setup creates `ask.json`, `note.schema.json`, a workspace `AGENTS.md`, and the `Knowledge Base/` notes. Its runtime configuration is **configured-unverified** until you test a new session. Every agent installing ASK must proactively persist the four-note bootstrap in its actual runtime, preserve foreign instructions, and report any registration it cannot do automatically for manual completion. See [runtime verification](runtime.md).

To view your notes, open Obsidian and choose **Open folder as vault**, then select `/path/to/your-workspace/Knowledge Base`, not the public checkout or the workspace root. No ASK plugin is required. The notes also work in a text editor.

For an existing vault, do not run setup into it or overwrite its notes. Review a separate ASK workspace and merge only the notes and settings you choose. For remote work, use an owner-provided authenticated connection to the machine holding the private workspace; setup does not grant remote filesystem access or configure your network.

See [backup, recovery, and uninstall](backup.md) and [upgrades](upgrades.md). Access declarations in configuration are guidance, not enforcement; the owner controls actual runtime permissions.
