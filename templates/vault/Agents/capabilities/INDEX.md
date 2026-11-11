---
title: Agent Capabilities Index
description: Descriptive catalogs for agent runtimes and extensions.
kind: index
scope: shared
lifecycle_status: active
updated: {{DATE}}
tags: ["agents", "capabilities"]
---
# Agent Capabilities Index

- [[Agents/capabilities/runtimes/INDEX]] — runtime availability
- [[Agents/capabilities/skills/INDEX]] — reusable instructions
- [[Agents/capabilities/integrations/INDEX]] — external connectors
- [[Agents/capabilities/plugins/INDEX]] — runtime extensions
- [[Agents/capabilities/snapshots/INDEX]] — scoped observations and coverage

These catalogs contain no credentials or authorization settings. Ordinary descriptive entries are routine when within the authorized content scope; installation, authentication, runtime settings, and access changes still follow the owner gate in [[Agents/rules/capability-management]].

## Onboarding and evidence

During an owner-requested installation or connection, document the installing agent's actually observed capabilities and discovery coverage. Start with current-session tool and skill metadata; use only safe, scoped additional sources when needed. Do not open credentials or export raw private configuration/inventories. Never install, remove, authenticate, or change permissions merely to fill this catalog.

Record runtime and surface separately: exposure in a desktop session does not prove CLI availability. Distinguish `exposed`, `configured-unverified`, `verified`, `unavailable`, and `unknown` in record bodies, with observation date, source, evidence, and limits. A tool name is not proof of authentication. Empty discovery means none observed within the stated coverage, not none installed.

Reuse shared records and merge new runtime/surface evidence rather than duplicating inventories. Preserve another agent's observations and valid prior evidence. These notes are descriptive; live permissions and current tools remain authoritative. The public distribution's `docs/onboarding.md` describes reviewed row proposals and the continuity/checkpoint handoff; `setup` and `doctor` do not fill or certify these catalogs.

## Structure and record types

Snapshots describe what was observed on a dated runtime/surface, including coverage and omissions. They are not curated recommendations or proof of access. Curated skill records live under [[Agents/capabilities/skills/shared/INDEX]]; project-scoped skill records can be added when needed and authorized. Integration and plugin directories hold reusable descriptions. Runtime records hold connection and surface-specific evidence. Link observations to curated records rather than copying inventories between agents.

Existing installations may retain flat catalogs or custom layouts. Reuse them; changing the public template does not migrate or overwrite installed notes.
