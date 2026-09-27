# Agentic Knowledge System (ASK)

ASK is a configurable system for giving people and their AI agents durable shared knowledge, useful task context, explicit authority, and traceable changes.

The goal is a reusable software system others can install and adapt. Andrey's private ASK is a reference instance and proving ground; its personal knowledge, runtime configuration, machine paths, identities, and operational data are not part of this repository.

## What ASK is taking shape to provide

- Durable knowledge with clear structure and ownership.
- Context routing that helps agents find the smallest relevant information for a task.
- Governance for agent access and changes.
- Provenance, validation, and recoverable history for durable writes.
- Optional agent capabilities with installation-specific configuration and adapters.

The system is early. This repository currently contains the project README, license, and design documentation. It does not yet contain an installable ASK implementation. A bounded Agent Tasks component exists in a private reference installation; it has not been released here.

## Documentation

- [Vision and scope](docs/vision.md)
- [Working architecture](docs/architecture.md)
- [Capability productization](docs/capability-productization.md)
- [Agent Tasks capability](docs/capabilities/agent-tasks.md)

The first adopter and primary user job are still being defined. Product decisions and implementation contracts will be added as they are established.

## Portability and privacy

Public software must work without Andrey's host, paths, agent identities, credentials, or personal data. Installation-dependent values belong in explicit configuration with documented defaults and validation. Use sanitized example data.

Do not publish private notes, artifacts, runtime configuration, credentials, machine paths, or private repository history.

## Contributing

New capabilities should include their user outcome, reusable boundary, configuration surface, permission model, failure behavior, and clean-install acceptance evidence. See [Capability productization](docs/capability-productization.md).

## License

See [LICENSE](LICENSE).
