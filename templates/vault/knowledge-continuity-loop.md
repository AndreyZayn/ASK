---
title: Knowledge Continuity Loop
description: The cycle agents follow so that work and decisions survive between sessions.
kind: rule
scope: shared
lifecycle_status: stable
updated: {{DATE}}
tags: ["continuity"]
governed_by:
  - "[[Agents/rules/knowledge-work]]"
depends_on:
  - "[[frontmatter-schema]]"
---
# Knowledge Continuity Loop

Sessions end; the knowledge base remains. Each piece of work follows this loop.

1. **Orient and route** — read the four configured bootstrap notes, the nearest index, and the matching policy gate. Gather only needed context; separate sources from assumptions. Before starting a write marker, run the installed ASK CLI `sync --config PATH` to fetch and fast-forward a clean vault. If remote changes arrive, reread affected bootstrap and routing notes. A dirty, offline, or conflicted vault must be reported; never stash, reset, rebase, or force-push automatically.
2. **Authorize** — check owner instruction, declared paths, actual runtime permissions, and unrelated dirty changes. Routine content and index additions inside authorized paths are allowed; structural, policy, schema, or permission changes require owner direction. If writing, start a session with `python3 scripts/ask.py write begin --config PATH --actor ID` before editing; retain the token.
3. **Act and preserve** — write durable decisions, state, blockers, and next steps in the owning note, not only a transcript. Attribute `by` (locally enrolled agent ID) and `upd` (local date) in the record text where applicable; use `source` or prose for provenance and label assumptions. Do not invent identities or facts.
4. **Link and date** — link new durable notes from the nearest index. Update frontmatter `updated` on meaningful changes. Advance [[date]] only to the current local date, never backward. Operational history is date-routed rather than individually indexed.
5. **Close out** — append exactly one concise entry per vault-writing session to the current `Memory/Logs/YYYY-MM.md` (create it under [[Memory/Logs/INDEX]] if needed), summarizing changed paths and outcome. Validate all session-owned notes and links, including this entry and the date note. Use a scoped checkpoint of only session-owned files, then sync to the verified private remote when available. Do not stage, commit, or overwrite unrelated changes. End with `python3 scripts/ask.py write end --config PATH --token TOKEN` and report failures.
6. **Hand off** — classify the result explicitly as durable knowledge updated, lifecycle logged, blocker recorded, or no durable change. If no write authority, give the owner a proposed update instead of writing.

Use the V1 controller's write markers, validation, scoped checkpoint, and sync commands; if using an older checkout without one of these commands, report the gap rather than simulating success. Do not sync to an unverified remote or bypass owner authority. Offline content can stay local as `backup-pending`; missing or unbound private-repository access leaves setup `setup-pending`. A hook must not overwrite a custom existing hook or silently stage unrelated files.

Back to [[INDEX]].
