# Release verification

## Historical V1 verification

The following evidence was recorded for the earlier 40-note release. It is not a claim that provider sessions, private backup, or scheduled jobs were re-exercised for the expanded starter.

The macOS release checks used synthetic workspaces; private reference notes and runtime credentials were not copied into the distribution.

- Python 3.9 and 3.14: automated tests cover scaffolding, metadata, links and attachments, graph topology, staged snapshots, runtime registration, private remote checks, scoped commits, conflicts, offline operation, write locks, backup selection, and LaunchAgent ownership.
- Fresh CLI setup produced 40 valid skeleton notes. Repeating setup preserved content. The validator caught staged errors even when the working file was valid, and accepted valid staged content despite an invalid working copy.
- Claude Code and Codex: separate authenticated fresh sessions inside the synthetic workspace and in an unrelated directory read the four bootstrap notes in order and returned the fixture phrase. Temporary global instruction blocks were removed and original instruction files restored byte for byte. Codex used CLI defaults for the smoke check because the host's saved model was unavailable.
- A real private GitHub test repository received the scaffold, was cloned into a second directory, and passed validation after rebinding its local hook. Runtime enrollment correctly remained pending on that restored installation.
- The macOS LaunchAgent was installed for a synthetic workspace, run once, and removed after checking its backup result. The restored workspace received the updated notes through normal fast-forward synchronization.

These tests establish the documented macOS workflow, not universal behavior across every agent. Each installation must prove its own persistent runtime connection with `agent verify`; Cursor and unknown runtimes use manual registration. Access declarations are advisory, and custom hooks or runtime restrictions may require explicit local integration.

GitHub private repository history provides the remote backup. It is not protection against every form of deletion or account loss. No additional local-backup system, hosted service, automatic AI maintenance, or migration importer is included in V1.

## Expanded starter verification — 2026-11-10

The expanded starter was checked in temporary synthetic workspaces. No real runtime configuration, private vault, provider account, or scheduled job was changed during these checks.

- `python3 -m unittest discover -s tests -v`: 152 tests passed on Python 3.14.2 (106.051 seconds).
- `/usr/bin/python3 -m unittest discover -s tests -v`: 152 tests passed on Python 3.9.6 (85.956 seconds).
- `git diff --check` passed; `python3 scripts/privacy_check.py` reported zero working-tree findings. Added-content review found no private-source identifiers, home paths, or excluded completion-prototype material.

- A fresh setup with a custom vault name and spaces in the workspace path produced 66 valid notes. It correctly stayed `setup-pending` because private backup and real runtime proof were intentionally absent.
- A real installed pre-commit hook accepted the initial valid commit and rejected an invalid staged profile even after the working copy was restored to valid content.
- Repeating setup preserved custom notes, index additions, local schema vocabulary, configuration, and workspace instructions by byte hash.
- Synthetic-home adapter checks covered Claude Code/Codex and the added Amp, Droid, and Antigravity targets, including foreign instructions, idempotence, disconnect, and symlink refusal. Current manual proof survives setup; malformed evidence or changed configuration cannot remain verified.
- Profile checks cover segment-aware matching, precedence and conflicts, owner vocabulary, operational metadata, existing schemas without profiles, and a staged schema that differs from the worktree.
- Actual authenticated model sessions, hosted Muse/Dot connections, OpenClaw assignments, Muse Code persistence, remote backup, and macOS scheduling were not re-exercised. Their prior or documented behavior is not new verification evidence. See the runtime support matrix for required installer proof.

## CI runner and historical-audit repair

The first expanded-starter PR run failed before tests because `ubuntu-latest` resolved to Ubuntu 26.04 and `actions/setup-python` could not find Python 3.9 for that image. Ubuntu jobs now run on Ubuntu 24.04, which has a Python 3.9 package in the official [Python versions manifest](https://github.com/actions/python-versions/blob/main/versions-manifest.json). The matrix labels remain unchanged to preserve required check names; fail-fast is disabled so each platform/version reports its own result.

The full historical scan also identifies a pre-existing personal-email author/committer finding at public base commit `42ad9010a9fbdecc5e6772b753af1e8582fcab5c`. No address is copied here and no history is rewritten. `.github/privacy-history-baseline.json` records only that exact reviewed commit ID. CI still scans and prints the entire source ancestry, marks the known finding explicitly, and fails on every new finding. The baseline cannot suppress file findings, patterns, or a new commit with the same identity. Running the scanner without the baseline remains a strict historical audit and reports the existing finding as failure. Baseline changes require explicit review; they must never be generated automatically to make a check pass.
