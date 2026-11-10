# Framework coverage and limits

Agentic System Knowledge (ASK) installs a reusable structure and working validation/enrollment tools. It starts without real people, projects, agent identities, schedules, service credentials, or private history.

| Area | Delivered behavior | Boundary |
| --- | --- | --- |
| Knowledge hierarchy | Projects and explicit archive; People, Personal, Tasks, Memory; Agents roles, rules, loops, capabilities, empty automation catalog | Project layers and local inventories are enrolled by the owner as needed |
| Bootstrap and routing | Four ordered notes, task-to-rule gates, minimal retrieval, delegated-worker exception | Instructions depend on the host honoring them; no permission enforcement |
| Roles and workflows | Eleven hats; separate software planning, development, QA, release/operations, practice improvement loops | Hats add judgment, not identities, invocation, authority, or background execution |
| Continuity | Durable capture/exclusion and placement matrix, provenance, nearest-index linking, date/log upkeep, explicit closeout outcomes | No automatic copying from conversations or private sources |
| Completion | Task owner, outcome, target, authority, repair, blocker and handoff contract | No completion prototype, task-board service, or agent lifecycle hooks |
| Validation | Local schema and path profiles, editable state/tag vocabulary, typed relations, ordinary wikilinks/Markdown links, attachments, title uniqueness, topology and dated records | Whole-snapshot validation; no incremental legacy-debt baseline, heading/block-anchor or shortcut-reference checks |
| Git hooks | Existing staged-snapshot pre-commit validator with safe foreign-hook refusal | Requires installed Python and the public checkout at its configured path; moving it needs reinstallation |
| Runtime enrollment | Managed local blocks for Codex, Claude Code, Amp, Droid, Antigravity; explicit manual routes for other surfaces | Fresh sessions and remote/provider connections must be observed by the installer; no claim of universal verified runtime parity |
| Upgrades | Existing config and templates remain owner-owned; validator accepts schemas without profiles | Review and apply changes manually; setup never replaces a customized vault |

The public validator intentionally retains strict whole-snapshot validation. A pre-existing invalid note can block an unrelated commit. Review existing debt before adopting new profiles; do not auto-migrate or suppress it. The installed schema controls vocabulary; the templates explain it. Runtime settings and live source remain operational truth.

Use `python3 -m unittest discover -s tests -v` and `python3 scripts/privacy_check.py` in the public checkout. Tests use only temporary synthetic workspaces and fake runtime homes. They establish tooling behavior and preservation boundaries, not actual account authentication or model compliance. See [release verification](release-verification.md) for the installer acceptance checklist and [runtime proof](runtime.md) for provider-level evidence.
