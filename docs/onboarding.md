# Agent identity and capability onboarding

An ASK installation has four separate outcomes: a working private workspace/backup, persistent runtime bootstrap with fresh-session proof, a locally agreed agent identity, and useful documentation of the capabilities actually observed. `setup` and `doctor` assess workspace/runtime readiness; they do not inspect the roster or certify capability documentation. Finish this procedure before describing agent onboarding as complete. An owner request to install or connect this agent includes the narrow registration/documentation work described here; it does not authorize unrelated system changes.

## First agent

Read `ask.json` to locate `vault_root` rather than assuming a folder name. Complete the ordered bootstrap and applicable local rules. Read the existing `Agents/roster.md` and `Agents/capabilities/INDEX.md`, then only the relevant catalogs. Use the owner's existing layout when it differs from the starter. Do not replace customized notes or schemas with public templates.

Choose a stable, non-secret local agent ID. A runtime is the host, a model is a selectable implementation, a hat is a professional role, and the local ID identifies the enrolled agent. Record runtime, surface (for example CLI versus desktop), controller/worker/assistant responsibility, agreed scope, and date. Scope describes the owner's agreement; it cannot grant filesystem, service, delegation, or publication permissions. Use the current installation instruction for already-authorized choices; ask only for a material missing identity, scope, or conflicting existing registration. Do not register another agent from a guessed name.

The public tools offer a read-only plan:

```sh
python3 /path/to/your-workspace/system/scripts/ask.py agent onboarding --config /path/to/your-workspace/ask.json --runtime codex
```

It resolves the configured vault and reports whether standard catalog paths are present, missing, or outside declared read scope. It reads no catalog bodies, runtime configuration, or provider data and writes nothing. A missing catalog is a prompt to follow the owner's existing index or request the missing scope; it is not permission to recreate the standard layout.

## Discover exposed skills and scoped capabilities safely

1. Prefer the current session's exposed tool list and skill/plugin metadata. Inventory all skills discoverable from that session's metadata when feasible, not just those used for the present task. Record names, short purposes, runtime, surface, provenance, observation date, evidence, and known limits. Integrations/plugins should state their actual discovery scope too. A filesystem package or catalog name alone establishes neither current exposure nor authentication.
2. If more context is necessary and authorized, inspect only the relevant non-secret skill manifest or documented installation metadata. Summarize purpose and source; do not copy a full proprietary skill, raw inventory, or machine-specific cache listing into the vault. Do not traverse every runtime directory or open settings/credential files to build an inventory.
3. For integrations, distinguish a visible tool from a configured connection and a successfully exercised operation. A harmless scoped read may establish a specific working operation when already authorized. Never send a message, create a resource, spend money, authenticate, change permissions, or install/remove something merely to verify a catalog row.
4. Record missing or inaccessible capabilities as unavailable or unknown with a next owner/action. Empty discovery means “none observed within this scope,” not “nothing is installed.” Continue the rest of onboarding. Reuse shared entries and add runtime/surface-specific evidence instead of copying the same catalog for each agent.
5. Keep credentials, token values, private endpoints with authentication parameters, account identifiers, raw provider responses, and private runtime configuration out of notes and proposals. A label such as “current session tool discovery” is often sufficient provenance. The helper validates structure and escaping, not whether free text contains a secret; sanitize before supplying it.

Use these observation states in catalog bodies; they are not new frontmatter fields:

| Availability | Evidence required |
| --- | --- |
| `exposed` | Capability is advertised in this session; execution/authentication has not been proven |
| `configured-unverified` | Non-secret configuration or enrollment is known; live behavior is untested |
| `verified` | A specific authorized operation was observed working; name its surface, date, and limits |
| `unavailable` | The relevant capability or operation was observed absent or failing; state the narrow reason |
| `unknown` | No sufficient observation; state what could not be checked |

A past successful operation is dated evidence, not permanent health. Update descriptive evidence after meaningful changes; installing or changing a capability still requires the separate local capability-management authority.

## Optional row proposals

The installing agent can place a small sanitized observation profile in a temporary local file, then ask ASK to format proposed rows. The file below is a synthetic shape example, not a capability to enroll or proof of a real connection:

```json
{
  "observed_on": "2000-01-01",
  "coverage": "Current-session metadata only; no private configuration inspected",
  "agent": {
    "id": "assistant-one",
    "runtime": "generic",
    "surface": "cli",
    "role": "controller",
    "scope": "Read shared notes and write authorized project content",
    "responsibility": "Help with approved project tasks"
  },
  "capabilities": [
    {
      "kind": "skill",
      "name": "example-review",
      "purpose": "Review synthetic changes",
      "availability": "exposed",
      "source": "Current-session skill metadata",
      "evidence": "Metadata visible; execution not tested",
      "limits": "No provider operation was attempted"
    }
  ]
}
```

```sh
python3 /path/to/your-workspace/system/scripts/ask.py agent onboarding --config /path/to/your-workspace/ask.json --runtime generic --profile /path/to/sanitized-observations.json
```

Replace the example ID, runtime, date, scope, and observations with actual agreed facts. Keep `--runtime` and the profile's runtime identifier equal. IDs use lowercase letters, digits, and hyphens. Roles are `controller`, `worker`, or `assistant`; capability kinds are `skill`, `integration`, `plugin`, or `runtime`. All text fields are single-line and bounded to 1000 characters; the profile permits up to 200 capability entries and 256000 bytes. For more than 200 entries, use bounded profiles of at most 200 entries, label coverage with batch number and total/remaining counts, and merge the reviewed batches into the same observed catalog or dated snapshot without duplicating the roster/runtime records. Never silently truncate a discovery list. If the session cannot expose the full list, state partial coverage, what was unavailable, and the remaining action; do not read secrets to fill the gap. An empty capability array is valid when its coverage and missing observations are explained. Unknown fields and duplicate kind/name pairs are rejected without echoing their values. Symlinked profile/catalog paths are refused.

The JSON result contains proposed `header` and `row` strings and identity keys for the roster, current runtime, and capability catalogs. Only readable, present catalogs receive path-bearing proposals in `notes`. Missing or out-of-scope catalogs retain their supplied observations under `unresolved`, with `applicable: false`, `action: manual-mapping-required`, and no destination path. Resolve the owner’s custom layout or missing scope before applying those facts; do not create a standard catalog from an unresolved record. Exit 0 means proposal generation succeeded. It **does not** mean installation, registration, capability discovery, or runtime verification completed. The runtime row is deliberately unknown until reconciled with actual enrollment/proof; retain valid existing evidence rather than blindly downgrading it. The tool does not check for existing identity collisions or validate the truth of supplied evidence.

## Apply reviewed knowledge through the existing workflow

For an offline first installation, complete the [initial generated baseline checkpoint](install.md#initial-local-baseline-before-offline-onboarding) before these narrow edits. A new untracked workspace cannot validate a staged roster alone because its configuration and schema are not yet in Git. Existing installations with a committed baseline continue normally.

The installing agent reviews the existing notes and then performs authorized edits with its normal file tools:

- Match roster records by local agent ID; match capability records by kind/name, runtime, and surface. Add a missing row, or reconcile that exact record in place. Preserve other agents, owner commentary, custom layouts, and stronger still-valid evidence. If two identities conflict, resolve that specific conflict before writing.
- For standard tables, use a header only when the table is absent; append rows directly to that table. For custom prose or a different schema/layout, translate the facts into the existing structure instead of appending a parallel registry.
- Remove an obsolete empty-placeholder sentence only when adding the first real record. Change `lifecycle_status: empty` to the appropriate locally supported state and update the note's `updated` date. Do not broaden enum values or overwrite a customized schema automatically.
- Follow `knowledge-continuity-loop.md`: begin an authorized write session, record the locally agreed ID, update date/log evidence, validate, and checkpoint only owned files. The roster is protected; use the installation's explicit registration authority with `checkpoint --owner-approved` for that scoped change, not as standing permission for unrelated policy changes. Do not expand `access.write` merely to register an agent.
- End the write session after its edits/checkpoint, then sync to the verified private remote using the normal backup process. A sync deferred by active writers, staged work, or conflicts remains backup pending; it does not establish successful backup. Report offline or missing-backup state honestly. The profile can remain temporary; the reviewed Markdown facts are canonical, not the JSON proposal.

For example, after reviewing the actual paths, use the normal CLI sequence (replace the placeholders; list only files you edited):

```sh
python3 /path/to/your-workspace/system/scripts/ask.py write begin --config /path/to/your-workspace/ask.json --actor LOCAL_AGENT_ID
# Save the returned token. Apply the reviewed note edits and required date/log upkeep.
python3 /path/to/your-workspace/system/scripts/ask.py validate --config /path/to/your-workspace/ask.json --json
python3 /path/to/your-workspace/system/scripts/ask.py checkpoint --config /path/to/your-workspace/ask.json --files "Knowledge Base/Agents/roster.md" "Knowledge Base/Agents/capabilities/runtimes/INDEX.md" "Knowledge Base/Agents/capabilities/skills/INDEX.md" "Knowledge Base/Memory/Logs/YYYY-MM.md" --message "Register agent and observed capabilities" --owner-approved
python3 /path/to/your-workspace/system/scripts/ask.py write end --config /path/to/your-workspace/ask.json --token=RETURNED_TOKEN
python3 /path/to/your-workspace/system/scripts/ask.py sync --config /path/to/your-workspace/ask.json
```

Keep the `--token=` form because an opaque token can begin with a hyphen. Paths passed to `checkpoint` are workspace-relative; substitute the configured vault name and legacy/custom catalog paths. Include `date.md` only if it needed an update. A local commit without a configured remote returns exit 2 with `backup_pending`; it does not undo the commit. End the write session after the authorized work, report backup pending, and follow the installation backup setup before claiming completion.

For read-only enrollment, or when actual runtime permissions prevent writing, supply the proposed changes to the owner and report registration/documentation pending. Do not treat a proposal as an applied record.

## Connecting another agent or revisiting an existing one

Reuse the existing workspace and backup. Resolve the vault through its config and read its roster/capability indexes before selecting the local ID. An already enrolled identity keeps its ID; a genuinely different agent gets its own agreed ID. Connect only the requested runtime and preserve unrelated instruction blocks, other registered workspaces, and other agents' proof. Run fresh-session verification for the actual surface being connected; another runtime's successful proof cannot be reused.

Document the new agent's observations with explicit coverage, including all exposed skill metadata when feasible. A capability can be exposed on one surface and absent on another, even when both use the same model or service. Merge those observations into the shared catalog and preserve the earlier records. Re-running the read-only proposal command is safe; re-applying its rows blindly is not an idempotent update.

## Completion evidence

Report each outcome separately: workspace/backup state; persistent runtime enrollment and observed fresh-session proof; the registered local ID and roster path; the capability notes updated, discovery coverage, and any unavailable/unknown surfaces; validation and scoped checkpoint/backup evidence. Neither a roster row nor `doctor: ready` proves all these outcomes. Live providers, remote hosts, and authentication remain unverified until actually exercised within authority.

## Fresh hierarchy and existing layouts

Fresh workspaces have `Agents/capabilities/{skills,integrations,plugins,runtimes,snapshots}/INDEX.md` and `skills/shared/INDEX.md`. Use snapshots for dated, scoped observed inventories with coverage and omissions; inventory does not imply adoption. Use curated shared skill records for reusable descriptions and provenance; and runtime records for connection and surface-specific evidence. Project-scoped skills can be added when useful and authorized. Do not turn discovery into an automatic inventory mirror.

The helper prefers an existing directory index, or an existing legacy flat `skills.md`, `integrations.md`, `plugins.md`, or `runtimes.md`. If both exist it refuses to choose; reconcile the layout manually. Missing catalogs are reported, never created. Custom layouts require manual mapping and reviewed edits under the owner's conventions. Existing installations are not migrated, and an onboarding proposal never rewrites their catalogs or schema. Do not reinitialize an existing vault to obtain the new hierarchy.
