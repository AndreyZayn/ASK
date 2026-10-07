# Backup, conflicts, and recovery

Use a private GitHub repository for remote backup. Setup checks the repository privacy before treating it as a backup destination. With no repository, the local workspace remains usable but setup exits 2 as `setup-pending`. Optional `--backup scheduled` enables the controller's macOS scheduled backup; it does not run an AI agent. Setup installs a staged-snapshot pre-commit hook but must not overwrite an existing custom hook. Review hook behavior before using an existing workspace.

For an authorized write, use `write begin --config PATH --actor ID` before editing; update the owning note and append one entry to `Memory/Logs/YYYY-MM.md`. Validate, checkpoint only session-owned files, sync to the verified private remote, and end with `write end --config PATH --token TOKEN`. Checkpointing and syncing are distinct from runtime verification. Keep unrelated dirty or staged changes out of the checkpoint. A protected change needs explicit owner direction, even when a command accepts `--owner-approved`.

The scheduled backup is bounded to at most every 15 minutes after 5 minutes of quiet. It skips active writes, staged changes, conflicts, and protected changes instead of forcing a push. Inspect `backup status --config PATH`; `backup run --config PATH` runs a backup check, and `backup disable --config PATH` stops ASK's scheduled job. Offline edits remain local as `backup-pending`; retry after network and private-remote access return. Do not force-push or resolve a conflict by discarding local or remote work. Review both sides and resolve conflicts explicitly before resuming backup.

## Restore on a new machine

Authenticate GitHub and confirm the remote is private. Clone the **private** repository into a separate workspace, then from a public ASK checkout rebind machine-local hooks and runtime configuration without replacing notes:

```sh
git clone git@github.com:OWNER/NAME.git /path/to/your-workspace
python3 scripts/ask.py setup --workspace /path/to/your-workspace --runtime codex --repository OWNER/NAME
python3 scripts/ask.py validate --config /path/to/your-workspace/ask.json
```

Preserve existing hooks and unrelated instructions. Re-test a new runtime session inside the workspace and from an unrelated directory; see [runtime proof](runtime.md). If authentication, privacy, conflicts, or permissions block recovery, stop and report the state instead of resetting or overwriting local edits. Derived graph JSON can be regenerated from notes.

## Uninstall

Disable ASK's scheduled backup if enabled with `backup disable --config PATH`. Review the selected binding, then use `agent disconnect --config PATH --runtime NAME` for that runtime only. Preserve foreign hooks and instructions. Uninstalling the integration does **not** delete the private workspace, its Git history, or the remote repository. Remove those only with separate owner direction.
