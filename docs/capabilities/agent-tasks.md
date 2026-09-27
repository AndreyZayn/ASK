# Agent Tasks capability

Agent Tasks is a bounded job ledger for agents that share an ASK installation. A controller can post and review jobs; eligible agents can inspect suggested work, claim it, and submit results. The owner can verify or reject submitted work.

## Behavior and boundaries

- Jobs have stable identity, success criteria, worker suggestions, capability needs, claims, result evidence, and event history.
- Submission and verification are distinct states.
- Claiming and its event record are atomic.
- Agent Tasks tracks work; it does not launch agents, schedule runs, provide general messaging, or grant authority over repositories or external services.
- Identity, storage path, SSH bindings, and capacity data belong to each installation.

## Implementation status

A working implementation exists in Andrey's private reference installation. This public repository does not yet contain the component code, public setup guide, or a verified clean-install path. Do not treat it as released software until those are present and tested.

When productizing the capability, specify a portable configuration schema, install and recovery instructions, a sanitized example, and acceptance evidence for both the local interfaces and any claimed remote adapter.
