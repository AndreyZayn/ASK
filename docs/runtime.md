# Runtime connection and proof

`setup --workspace PATH [--repository OWNER/NAME --create-repository] [--runtime claude|codex|amp|droid|antigravity|cursor|generic] [--read-only] [--backup scheduled]` configures the selected runtime when supported, without replacing unrelated instructions. The workspace-root `AGENTS.md` is not proof that every agent reads it. Every installing agent should explicitly persist the ordered bootstrap in **its actual runtime**: `date.md`, `INDEX.md`, `agents.md`, `knowledge-map.md`. If automatic registration is unsupported, report the exact manual step and leave the connection unverified. Preserve existing owner and third-party instructions.

From the public ASK checkout, inspect the selected connection:

```sh
python3 /path/to/your-workspace/system/scripts/ask.py agent status --config /path/to/your-workspace --runtime codex
python3 /path/to/your-workspace/system/scripts/ask.py doctor --config /path/to/your-workspace --json
python3 /path/to/your-workspace/system/scripts/ask.py agent verify --config /path/to/your-workspace --runtime codex
```

Status and doctor emit JSON. `agent verify` prints a procedure; it does **not** secretly invoke the agent or certify a session by itself. Start a genuinely **new** session in the selected runtime, first inside the private workspace, then from an unrelated directory. Check that it finds the configured bootstrap in order and respects the intended boundaries in both places. Do not give an agent with `KB_ACCESS: none` private vault access just to test this. Follow the printed procedure for the evidence file format; pass controller-observed evidence with `agent verify --config PATH --runtime NAME --evidence JSON_FILE`. Report separately any steps that require manual proof. Do not manufacture evidence or label `configured-unverified` as verified.

An authenticated remote session can be tested through an owner-provided connection, but neither configuration nor a local test proves a remote session works. Cursor and generic runtimes may require manual persistence and proof; unsupported registration must be reported rather than silently skipped.

The default `init` command remains a lower-level local bootstrap with read-only declarations; `bootstrap --config PATH` prints an adapter, not a runtime connection. No note or instruction text enforces filesystem or service permissions. Limit those in the runtime itself and obtain owner authorization for writes, publication, and external actions.

## Runtime support matrix

Managed means ASK can safely append/update/remove its delimited instruction block; it does **not** mean an authenticated provider session was tested. Every managed connection starts `configured-unverified`. The implementation is tested with synthetic homes, including foreign instructions, repeat connection, disconnect, and symlink refusal. Live model sessions, desktop variants, remote hosts, and scheduled runs require separate observed evidence.

| Runtime or surface | ASK integration | Remaining proof or manual step |
| --- | --- | --- |
| Codex local | Managed `${CODEX_HOME:-~/.codex}/AGENTS.md` | Test two new sessions and actual filesystem access; project overrides can supersede global guidance |
| Claude Code local | Managed `${CLAUDE_CONFIG_DIR:-~/.claude}/CLAUDE.md`; alias `claude-code` | Test each CLI/IDE/desktop surface separately; a local instruction file does not prove cloud or connector access |
| Amp local | Managed `~/.config/amp/AGENTS.md` | Test new sessions; guidance exclusions can disable loading |
| Factory Droid local | Managed `~/.factory/AGENTS.md` | Test new sessions; repository instructions can refine personal guidance |
| Antigravity local | Managed `~/.gemini/GEMINI.md` | Test the actual CLI/IDE surface and vault access; other Gemini tools can also read this shared file |
| Cursor | Manual | Add the generated bootstrap guidance to the runtime's persistent User Rules, preserve existing rules, then test inside/outside sessions |
| OpenClaw | Manual, per selected agent and run type | Determine the active agent workspace and instruction surface; merge the bootstrap there. For a scheduled or heartbeat run, explicitly deliver the required context in that run's payload and test it separately. ASK does not create jobs, bindings, or provider credentials |
| Muse / Dot hosted assistants | Manual, connection-dependent | Use the product's supported persistent instructions if available and an owner-authorized host connection. Verify the host can read the chosen vault and test a new hosted session. If either surface is unavailable, report unsupported persistent registration; a local worker's success does not prove hosted startup |
| Muse Code | Manual, persistence unverified | Inspect the installed runtime's documented instruction-loading surface before applying the generated adapter. No global path is assumed. If none is supported, supply bootstrap per authorized run and report persistent enrollment incomplete |
| Other runtimes | Manual | Identify a documented persistent instruction surface, preserve it, use `bootstrap --config PATH` as the content source, and perform fresh-session proof |

The added file targets follow [Amp's personal guidance documentation](https://ampcode.com/docs/customize/agents-md), [Factory's personal instruction discovery](https://docs.factory.com/harness/agents-md), and [Antigravity's global rules](https://antigravity.google/docs/rules). These sources establish intended discovery, not live provider connectivity. ASK does not change credentials, permission settings, or provider configuration. Existing symlinked instruction files are preserved and rejected for automatic editing; integrate through the owning system manually.

For a manual runtime, run `agent connect --config PATH --runtime NAME` to record pending enrollment and print the concrete vault path and bootstrap order. This writes only the local enrollment registry, not the runtime instructions. Apply the block through the selected runtime's supported persistent mechanism without bulk-copying the vault. Keep the delegated-worker exception. Record exactly which surface and connection were tested in the evidence. `verified` is a controller-attested observation, not cryptographic proof or an ASK-launched model test; synthetic unit-test evidence never verifies a real connection. Config changes invalidate prior proof for manual as well as managed connections.

After connecting a runtime, complete [agent identity and capability onboarding](onboarding.md) in the same owner-owned vault. Runtime enrollment does not create a roster identity or discover skills/integrations. The read-only `agent onboarding` command can format sanitized observations for review; it never certifies a connection or writes catalog rows.
