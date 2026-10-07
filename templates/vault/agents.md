---
title: Agent Entry Point
description: How agents orient, act, and record work in this knowledge base; the third bootstrap note.
kind: rule
scope: shared
lifecycle_status: active
updated: {{DATE}}
tags: ["bootstrap", "agents"]
governed_by:
  - "[[Agents/rules/knowledge-work]]"
depends_on:
  - "[[knowledge-continuity-loop]]"
---
# Agent Entry Point

This is bootstrap note 3 of 4. Read [[knowledge-map]] next.

## Before you act

- Read the configured bootstrap notes in order for each new user project or work context, not just once per runtime installation. Follow [[Agents/rules/knowledge-work]] and the task's policy gate in [[Agents/rules/INDEX]].
- When installing ASK, proactively persist that ordered bootstrap in your actual runtime, not only in this note or a printed adapter. Preserve other instructions. If registration is unsupported, report the manual step and keep the runtime `configured-unverified` until a fresh-session test inside this workspace and from an unrelated directory.
- Use [[knowledge-map]] and the nearest index. Load only relevant notes, not the entire vault.
- A worker capsule with `KB_ACCESS: none` must not open or bootstrap private knowledge. The controller supplies only authorized, minimal context.

## Authority

The workspace configuration declares advisory paths. Lower-level `init` defaults to read-only; `setup` offers `--read-only` or scoped content-writer declarations. Routine authorized writes can include Projects, People, Personal, Tasks, Memory, `date.md`, `goals.md`, root `INDEX.md`, and ordinary `Agents/capabilities/` content. `agents.md`, `knowledge-map.md`, `knowledge-continuity-loop.md`, schema and tag taxonomy, `Agents/rules/**`, roster, and ontology require explicit owner direction to change. Neither these declarations nor this text enforces runtime permissions. Write only with owner authorization, declared access, and actual runtime access; follow the narrowest boundary. Never infer permission to send, publish, install, change policy, or access secrets from file access.

## After you act

For an authorized write session, follow [[knowledge-continuity-loop]] from begin marker through checkpoint and end marker. Keep metadata valid per [[frontmatter-schema]]. If a required CLI command is unavailable, do not pretend the session was committed or backed up; report the limitation.
