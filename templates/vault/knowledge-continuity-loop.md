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
2. **Authorize** — check owner instruction, declared paths, actual runtime permissions, and unrelated dirty changes. Routine content and index additions inside authorized paths are allowed; structural, policy, schema, or permission changes require owner direction. From the ASK workspace root, start a session with `python3 system/scripts/ask.py write begin --config PATH --actor ID` before editing; retain the token.
3. **Act and preserve** — write durable decisions, state, blockers, and next steps in the owning note, not only a transcript. Attribute `by` (locally enrolled agent ID) and `upd` (local date) in the record text where applicable; use `source` or prose for provenance and label assumptions. Do not invent identities or facts.
4. **Link and date** — link new durable notes from the nearest index. Update frontmatter `updated` on meaningful changes. Advance [[date]] only to the current local date, never backward. Operational history is date-routed rather than individually indexed.
5. **Close out** — append exactly one concise entry per vault-writing session to the current `Memory/Logs/YYYY-MM.md` (create it under [[Memory/Logs/INDEX]] if needed), summarizing changed paths and outcome. Validate all session-owned notes and links, including this entry and the date note. Use a scoped checkpoint of only session-owned files, then from the ASK workspace root end the write marker with `python3 system/scripts/ask.py write end --config PATH --token=TOKEN`, and sync to the verified private remote when available. Preserve the `--token=` form for opaque tokens that begin with a hyphen. Do not stage, commit, or overwrite unrelated changes. Report failures and deferred sync as backup pending.
6. **Hand off** — classify the result explicitly as durable knowledge updated, lifecycle logged, blocker recorded, or no durable change. If no write authority, give the owner a proposed update instead of writing.

For a first offline installation with no committed baseline, follow the public installation guide to checkpoint only the exact `initial_checkpoint_files` returned by fresh setup before making narrow onboarding checkpoints. Preserve unrelated files and staged work; do not infer a baseline from all current files.

Use the V1 controller's write markers, validation, scoped checkpoint, and sync commands; if using an older checkout without one of these commands, report the gap rather than simulating success. Do not sync to an unverified remote or bypass owner authority. Offline content can stay local as `backup-pending`; missing or unbound private-repository access leaves setup `setup-pending`. A hook must not overwrite a custom existing hook or silently stage unrelated files.

Back to [[INDEX]].

## Preserve knowledge, not execution residue

Capture a reusable decision, contract, verified finding, accepted commitment, meaningful relationship fact, or lesson when it will change future work. Record the smallest explanation that remains useful without this chat. Search the existing canonical note first; prefer an update over a parallel summary. Preserve source, date, uncertainty, and the reason for a decision. Separate observed facts, owner choices, and hypotheses.

| Information | Durable destination |
| --- | --- |
| Product behavior, architecture, policy, schema, workflow decision | Existing project or topic note; link the implementation evidence |
| Engineering planning, execution, review, verification, rework | Existing project development log; no automatic new log hierarchy |
| Accepted commitment, owner, deadline, blocker, next action | Tasks or the owner's established task system |
| Person or relationship context | Scoped People registry and detail note; link both directions |
| Preferences or personal constraints | Relevant Personal note |
| Reusable role, procedure, or workflow | Agents hats, rules, or loops, with owner direction for policy changes |
| Per-session changes | One concise monthly Memory/Logs entry; never the sole home of a decision |

Exclude credentials, access tokens, private keys, raw tool logs, full chat transcripts, scratch attempts, replay state, and redundant copies of repository source. Keep a useful conclusion and a safe source reference instead. A transient successful lookup or routine operation may need no durable record. If a fact is unreliable or the destination/authority is missing, report that precise gap instead of inventing a note.

## Topology and maintenance

New canonical notes need an inbound link from the nearest governing index. Create a local index when a folder defines a scope, registry, workflow, or has subfolders; compact domains may stay cataloged by their ancestor index. Update incoming links and the catalog when renaming or deleting a note. Dated operational records are routed through their folder index. Keep knowledge-map routing-only and avoid duplicated canonical facts.

The installed staged-snapshot pre-commit hook enforces the local schema and graph checks. Run `validate --config PATH --json` before a scoped checkpoint; `validate --staged` reproduces the hook. The public validator checks the whole snapshot, including existing debt; it never silently migrates legacy notes. Preserve custom hooks and integrate validation manually when automatic setup refuses a conflict.

## Closeout assessment

The controller chooses one or more outcomes: **durable knowledge updated**, **lifecycle logged**, **blocker recorded**, or **no durable knowledge changed**. This assessment does not require writing a note for every task. When notes changed, identify their paths and evidence; when preservation is blocked, name the next owner and required input. A log entry or successful worker exit is not evidence that the requested task reached its target.
