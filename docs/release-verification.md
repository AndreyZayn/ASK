# V1 verification

The macOS release checks used synthetic workspaces; private reference notes and runtime credentials were not copied into the distribution.

- Python 3.9 and 3.14: automated tests cover scaffolding, metadata, links and attachments, graph topology, staged snapshots, runtime registration, private remote checks, scoped commits, conflicts, offline operation, write locks, backup selection, and LaunchAgent ownership.
- Fresh CLI setup produced 40 valid skeleton notes. Repeating setup preserved content. The validator caught staged errors even when the working file was valid, and accepted valid staged content despite an invalid working copy.
- Claude Code and Codex: separate authenticated fresh sessions inside the synthetic workspace and in an unrelated directory read the four bootstrap notes in order and returned the fixture phrase. Temporary global instruction blocks were removed and original instruction files restored byte for byte. Codex used CLI defaults for the smoke check because the host's saved model was unavailable.
- A real private GitHub test repository received the scaffold, was cloned into a second directory, and passed validation after rebinding its local hook. Runtime enrollment correctly remained pending on that restored installation.
- The macOS LaunchAgent was installed for a synthetic workspace, run once, and removed after checking its backup result. The restored workspace received the updated notes through normal fast-forward synchronization.

These tests establish the documented macOS workflow, not universal behavior across every agent. Each installation must prove its own persistent runtime connection with `agent verify`; Cursor and unknown runtimes use manual registration. Access declarations are advisory, and custom hooks or runtime restrictions may require explicit local integration.

GitHub private repository history provides the remote backup. It is not protection against every form of deletion or account loss. No additional local-backup system, hosted service, automatic AI maintenance, or migration importer is included in V1.
