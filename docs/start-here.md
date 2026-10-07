# Install through your agent

ASK is designed to be installed through a conversation with a local agent. The owner gives the prompt in the [README](../README.md); the agent performs the steps below. These are installation instructions, not authorization to install during a code review or a delegated task with `KB_ACCESS: none`.

## Installation checklist for the agent

1. **Choose the owner's locations and runtime.** Ask only for missing choices: a new private workspace folder, the owner's private GitHub repository name, and the runtime being connected. Keep the public checkout outside the private workspace. Never initialize over an existing vault. Use [the upgrade guide](upgrades.md) or [recovery guide](backup.md) when appropriate.
2. **Check prerequisites.** On macOS, check Python 3.9+, Git, GitHub CLI, and the selected agent runtime. Help the owner authenticate GitHub using its normal login flow; never request credentials in notes or put them in the vault. Obsidian is optional. Keep the public checkout at a stable location because runtime instructions and scheduled backup can reference its tools.
3. **Create the workspace and backup.** Run the setup command in [install.md](install.md) with the actual choices. Check that the GitHub destination is private and the initial backup succeeds. Explain a local-only or offline pending state accurately. Scheduled backup is optional; enable it only when the owner chooses it.
4. **Persist the bootstrap in the real runtime.** Setup supports managed global instructions for Claude Code and Codex. For other runtimes, follow the manual output and that runtime's supported persistent-instruction mechanism. The instruction must point to this owner's vault and read `date.md`, `INDEX.md`, `agents.md`, then `knowledge-map.md` at the beginning of a session. Preserve unrelated instructions. Merely reading these files once, or adding a row to a roster, does not complete runtime registration.
5. **Register the agent's local identity.** When the owner's installation request includes agent registration, add a stable, non-secret local ID, runtime, agreed scope, and responsibility to the private vault's `Agents/roster.md`. Follow the generated vault's continuity instructions, validation, and scoped checkpoint process. Setup does not fill this roster automatically. Do not infer broad permissions from the installation request; actual access remains controlled by the owner and runtime.
6. **Prove the connection.** Follow [runtime.md](runtime.md): test genuinely fresh sessions inside the workspace and from an unrelated directory, inspect the observed bootstrap, and record real evidence. If you cannot launch a fresh session, give the owner the exact test prompt and keep the connection unverified until they complete it. Run `doctor` and report remaining pending checks instead of claiming success.
7. **Open and explain the vault.** Show the owner the exact `Knowledge Base` folder to open in Obsidian. It starts with 40 generic notes: core navigation and policies; Projects, People, and Personal indexes; task lists and daily records; memory logs and summary areas; and agent rules, roster, and capability indexes. No personal notes or histories are supplied. Ask what project or goal they want to add first.

After installation, the owner works through ordinary conversation. During authorized work, agents follow the continuity loop to update linked notes, record decisions, validate changes, and sync the private backup. The notes do not think or update themselves: ongoing knowledge maintenance happens during agent sessions. Optional scheduled backup runs Git checks without invoking AI.

## Connect another agent to the same vault

Give the new local agent this prompt, replacing the two paths:

> Connect yourself to my existing ASK workspace at WORKSPACE_PATH using the public ASK tools at PUBLIC_CHECKOUT_PATH. Read its Knowledge Base/date.md, INDEX.md, agents.md, and knowledge-map.md in that order. Follow docs/runtime.md in the public checkout to persist this bootstrap in your actual runtime, preserving existing instructions. Register your local identity and agreed scope in my private Agents/roster.md using the vault's continuity process. Verify fresh sessions inside and outside the workspace. Reuse the existing vault and backup; do not create another vault. Report any manual or unverified step.

From the public checkout, the connection command is:

```sh
python3 scripts/ask.py agent connect --config /path/to/your-workspace/ask.json --runtime claude
```

Use `codex`, `cursor`, or the other runtime's name as appropriate. Follow with the status and verification commands in [runtime.md](runtime.md). Each runtime needs its own persistent registration and proof. This does not grant a remote or browser-only agent access to local files; the owner must provide a supported connection first.

## Share ASK with another person

Send them the public repository link and the README prompt. They repeat installation using their own folders, agent accounts, and private GitHub repository. They do not register with the project's author or receive access to anyone else's vault. Shared team vaults and their permissions need a separate, explicit setup.
