# ASK working architecture

This document is an early system model for design and implementation. It sets boundaries and principles; it does not define a final API, database schema, or deployment topology.

## Responsibilities

1. **Knowledge** — durable information with explicit ownership, structure, and history.
2. **Context routing** — indexes and rules that locate the smallest useful context for a task.
3. **Authority and governance** — controls over which agents can read or change which knowledge and capabilities.
4. **Provenance and validation** — attributable changes, structural checks, and recoverable version history.
5. **Capabilities and coordination** — optional bounded operations, such as agent job tracking.
6. **Installation adapters** — configuration and integrations for paths, identity, storage, runtimes, and transport.

An installation supplies its own data and policy, then enables the capabilities it needs.

## Portability rules

- Treat any single deployment as a reference, not as a required host, path, identity list, or vendor stack.
- Put installation-varying values in explicit configuration with documented defaults and validation.
- Keep portable software separate from installation data, secrets, and personal knowledge.
- Give each capability a bounded interface and least authority.
- Preserve provenance and make durable writes recoverable.
- Keep integrations replaceable so they do not become accidental core dependencies.

## Current evidence

A private reference installation contains a structured knowledge base, context-routing and governance rules, validators, and an Agent Tasks component. Agent Tasks uses a local SQLite ledger and controlled interfaces in that installation. This repository does not yet contain that implementation; its public architecture and configuration contract remain to be designed and verified.

## Decisions still open

- First adopter and primary user job.
- Minimum installable ASK system and optional module boundaries.
- Knowledge storage and import/export contracts.
- Identity and policy model for local and hosted agents.
- Extension interfaces for storage, retrieval, validation, and transport.
- Installation, upgrade, backup, and recovery.
- Security requirements for individual and shared installations.

Resolve these choices in focused design notes before relying on them as implementation contracts.
