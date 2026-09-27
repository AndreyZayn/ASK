# ASK vision

## Purpose

Agentic Knowledge System (ASK) aims to make durable knowledge useful to people and the AI agents they work with. It should help a person record knowledge once, route relevant context to an agent when needed, and govern how agents use and change that knowledge.

ASK is intended to become reusable software, not a package of one person's notes or machine configuration. Each installation should be able to choose its knowledge, agents, integrations, storage, and operating policies.

## System qualities

- **Durable:** important context survives individual conversations and agent runs.
- **Relevant:** routing surfaces task-specific context without loading an entire knowledge base.
- **Governed:** access and write authority are explicit and bounded.
- **Traceable:** durable changes have provenance, validation, and recoverable history.
- **Adaptable:** installations can configure paths, identities, storage, runtimes, and optional capabilities.
- **Composable:** useful capabilities can be added without requiring every adopter to use the same host or vendor stack.

## Scope boundaries

ASK is the system and its reusable software. A knowledge base is an installation's data. Integrations and runtime adapters connect the system to an installation's chosen tools. Private notes, credentials, operational data, and personal configuration are not product assets.

The first adopter and primary job are still open product decisions. This document records the system goal without preempting that choice.
