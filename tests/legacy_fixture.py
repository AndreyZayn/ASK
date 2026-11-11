"""Explicit synthetic pre-layout installations for compatibility regressions.

Fresh installs no longer write root ``ask.json`` or ``note.schema.json``.
Tests that customize JSON settings or schema convert a fresh synthetic
workspace with this helper instead of expecting installs to emit those files.
Production never performs this conversion.
"""
import ast
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / 'scripts'))
from asklib import gitops  # noqa: E402

LEGACY_INIT_KEYS = ('version', 'vault_root', 'bootstrap_files', 'access')


def public_schema():
    """Parse the shipped Python rules as a literal, as the validator does."""
    tree = ast.parse((ROOT / 'scripts' / 'note_schema.py').read_text(encoding='utf-8'))
    values = [n.value for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1
              and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'SCHEMA']
    assert len(values) == 1, 'note_schema.py must declare one literal SCHEMA'
    return ast.literal_eval(values[0])


def legacy_workspace(ws, setup=False):
    """Write the ask.json and note.schema.json an older ASK release created.

    ``setup=False`` mirrors a former ``init`` (no topology or version keys);
    ``setup=True`` mirrors a former V1 ``setup`` with its full settings.
    Returns the legacy configuration path.
    """
    ws = Path(ws)
    cp = ws / 'ask.json'
    if cp.exists():
        return cp
    derived = gitops.read_config(ws)
    data = dict(derived) if setup else {k: derived[k] for k in LEGACY_INIT_KEYS}
    data['schema_path'] = 'note.schema.json'
    if not setup:
        data['access'] = {'read': ['.'], 'write': []}
    cp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    (ws / 'note.schema.json').write_text(json.dumps(public_schema(), indent=2) + '\n', encoding='utf-8')
    import ask
    (ws / 'AGENTS.md').write_text(
        ask.adapter(dict(data, vault=ws / data['vault_root']), cp, ws / 'system/scripts/ask.py'),
        encoding='utf-8')
    return cp


def legacy_result(result, args):
    """Convert only successful synthetic setups for tests of legacy behavior."""
    if args and args[0] in ('init', 'setup') and '--workspace' in args:
        ws = Path(args[args.index('--workspace') + 1])
        if not (ws / 'ask.json').exists() and (ws / 'system/install-manifest.json').exists():
            if args[0] == 'init' and result.returncode == 0:
                legacy_workspace(ws)
            elif args[0] == 'setup':
                data = json.loads(result.stdout)
                if data.get('initial_checkpoint_files'):
                    legacy_workspace(ws, setup=True)
                    data['initial_checkpoint_files'] += ['ask.json', 'note.schema.json']
                    result.stdout = json.dumps(data)
    return result
