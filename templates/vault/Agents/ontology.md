---
title: Agent Ontology
description: Definitions for controller, worker, access, and delegation.
kind: reference
scope: shared
lifecycle_status: stable
updated: {{DATE}}
tags: ["agents", "ontology"]
---
# Agent Ontology

- **Owner** directs permission, policies, and structural changes.
- **Controller** routes work using [[knowledge-map]] and checks owner direction and actual runtime access.
- **Worker** receives a bounded task and a capsule with explicit `KB_ACCESS` and `DELEGATION_DEPTH`. `KB_ACCESS: none` forbids private bootstrap or reading the vault.
- **Local agent ID** is an owner-enrolled identifier in [[Agents/roster]] used for `by` attribution. An unregistered worker must not invent one.
- **Capability** is a descriptive listing in [[Agents/capabilities/INDEX]], not a permission. The runtime and owner control actual access.
