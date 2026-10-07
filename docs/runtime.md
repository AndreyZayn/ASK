# Runtime connection and proof

`setup --workspace PATH [--repository OWNER/NAME --create-repository] [--runtime claude|codex|cursor|generic] [--read-only] [--backup scheduled]` configures the selected runtime when supported, without replacing unrelated instructions. The workspace-root `AGENTS.md` is not proof that every agent reads it. Every installing agent should explicitly persist the ordered bootstrap in **its actual runtime**: `date.md`, `INDEX.md`, `agents.md`, `knowledge-map.md`. If automatic registration is unsupported, report the exact manual step and leave the connection unverified. Preserve existing owner and third-party instructions.

From the public ASK checkout, inspect the selected connection:

```sh
python3 scripts/ask.py agent status --config /path/to/your-workspace/ask.json --runtime codex
python3 scripts/ask.py doctor --config /path/to/your-workspace/ask.json --json
python3 scripts/ask.py agent verify --config /path/to/your-workspace/ask.json --runtime codex
```

Status and doctor emit JSON. `agent verify` prints a procedure; it does **not** secretly invoke the agent or certify a session by itself. Start a genuinely **new** session in the selected runtime, first inside the private workspace, then from an unrelated directory. Check that it finds the configured bootstrap in order and respects the intended boundaries in both places. Do not give an agent with `KB_ACCESS: none` private vault access just to test this. Follow the printed procedure for the evidence file format; pass controller-observed evidence with `agent verify --config PATH --runtime NAME --evidence JSON_FILE`. Report separately any steps that require manual proof. Do not manufacture evidence or label `configured-unverified` as verified.

An authenticated remote session can be tested through an owner-provided connection, but neither configuration nor a local test proves a remote session works. Cursor and generic runtimes may require manual persistence and proof; unsupported registration must be reported rather than silently skipped.

The default `init` command remains a lower-level local bootstrap with read-only declarations; `bootstrap --config PATH` prints an adapter, not a runtime connection. No note or instruction text enforces filesystem or service permissions. Limit those in the runtime itself and obtain owner authorization for writes, publication, and external actions.
