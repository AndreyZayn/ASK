"""Runtime-neutral enrollment backend for ASK persistent bootstrap.

Controller-integrated helpers that connect an ASK workspace to agent
runtimes (Claude Code, Codex) or return manual instructions for any other
runtime. Standard library only, Python 3.9 compatible.
"""

import hashlib
import json
import os
import shlex
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

__all__ = [
    'RuntimeError',
    'connect',
    'disconnect',
    'inspect',
    'verification_prompt',
    'record_verification',
]


class RuntimeError(Exception):
    """Enrollment backend error (configuration, state, or I/O)."""


BOOTSTRAP_ORDER = ['date.md', 'INDEX.md', 'agents.md', 'knowledge-map.md']

SECRET_KEY_HINTS = (
    'secret', 'token', 'password', 'credential', 'private_key',
    'api_key', 'apikey', 'auth',
)


def _reject_symlinks(path: Path, label: str) -> Path:
    """Reject symlink components; return the absolute path."""
    p = Path(os.path.abspath(str(Path(path).expanduser())))
    cur = Path(p.anchor)
    for part in p.parts[1:]:
        if part in ('', '.'):
            continue
        if part == '..':
            cur = cur.parent
            continue
        cur = cur / part
        try:
            if os.path.islink(cur):
                raise RuntimeError('%s path is a symlink: %s' % (label, cur))
        except RuntimeError:
            raise
        except OSError as e:
            raise RuntimeError('%s cannot be checked: %s' % (label, e))
    return p


def _load_config(config_path: Union[str, Path]) -> Dict[str, Any]:
    cp = _reject_symlinks(Path(config_path), 'config')
    if not cp.is_file():
        raise RuntimeError('config does not exist: %s' % cp)
    try:
        cfg = json.loads(cp.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise RuntimeError('cannot read config: %s' % e)
    if not isinstance(cfg, dict):
        raise RuntimeError('config must be a JSON object')
    if type(cfg.get('version')) is not int or cfg.get('version') != 1:
        raise RuntimeError('config version must be the integer 1')
    if not isinstance(cfg.get('vault_root'), str) or not cfg['vault_root']:
        raise RuntimeError('vault_root must be a non-empty path')
    if not isinstance(cfg.get('schema_path'), str) or not cfg['schema_path']:
        raise RuntimeError('schema_path must be a non-empty path')
    raw_vault = Path(cfg['vault_root'])
    vault = raw_vault if raw_vault.is_absolute() else cp.parent / raw_vault
    vault = _reject_symlinks(vault, 'vault_root')
    if not vault.is_dir():
        raise RuntimeError('vault_root is not a directory: %s' % vault)
    schema = cp.parent / Path(cfg['schema_path'])
    if Path(cfg['schema_path']).is_absolute() or '..' in Path(cfg['schema_path']).parts:
        raise RuntimeError('schema_path must stay within its root')
    schema = _reject_symlinks(schema, 'schema_path')
    if not schema.is_file():
        raise RuntimeError('schema file does not exist: %s' % schema)
    boot = cfg.get('bootstrap_files')
    if boot != BOOTSTRAP_ORDER:
        raise RuntimeError(
            'bootstrap_files must be the persistent four-note order: %s'
            % (BOOTSTRAP_ORDER,))
    for name in BOOTSTRAP_ORDER:
        p = vault / name
        if p.is_symlink():
            raise RuntimeError('bootstrap path is a symlink: %s' % p)
        if not p.is_file():
            raise RuntimeError('configured bootstrap note missing: %s' % name)
    workspace = cp.parent
    return {
        'config_path': cp,
        'workspace': workspace,
        'vault': vault,
        'bootstrap_files': list(BOOTSTRAP_ORDER),
        'config_digest': hashlib.sha256(cp.read_bytes()).hexdigest(),
    }


def _dist_ask() -> Path:
    return Path(__file__).resolve().parents[2] / 'scripts' / 'ask.py'


def _normalize_runtime(runtime: str) -> Tuple[Optional[str], str]:
    key = str(runtime).strip().lower().replace('_', '-')
    if key in ('claude', 'claude-code'):
        return 'claude', 'claude'
    if key in ('codex', 'openai-codex'):
        return 'codex', 'codex'
    if not key:
        raise RuntimeError('runtime must be a non-empty name')
    return None, key


def _expected_target(managed: str, home: Optional[Union[str, Path]]) -> Path:
    if managed == 'claude':
        if home is not None:
            base = Path(home).expanduser() / '.claude'
        elif os.environ.get('CLAUDE_CONFIG_DIR'):
            base = Path(os.environ['CLAUDE_CONFIG_DIR']).expanduser()
        else:
            base = Path.home() / '.claude'
        return base / 'CLAUDE.md'
    if managed == 'codex':
        if home is not None:
            base = Path(home).expanduser() / '.codex'
        elif os.environ.get('CODEX_HOME'):
            base = Path(os.environ['CODEX_HOME']).expanduser()
        else:
            base = Path.home() / '.codex'
        return base / 'AGENTS.md'
    raise RuntimeError('no managed file for this runtime')


def _markers(workspace: Path) -> Tuple[str, str]:
    ws = str(workspace)
    return (
        '<!-- ASK-MANAGED-START %s -->' % ws,
        '<!-- ASK-MANAGED-END %s -->' % ws,
    )


def _owned_span(text: str, workspace: Path) -> Optional[Tuple[int, int]]:
    """Return (start, end) offsets of the owned block, or None if absent."""
    start, end = _markers(workspace)
    n_start = text.count(start)
    n_end = text.count(end)
    if n_start == 0 and n_end == 0:
        if str(workspace) in text and 'ASK-MANAGED' in text:
            raise RuntimeError('managed block markers are corrupt; refusing to modify file')
        return None
    if n_start != 1 or n_end != 1:
        raise RuntimeError('managed block markers are corrupt or duplicated; refusing to modify file')
    si = text.index(start)
    ei = text.index(end)
    if ei < si:
        raise RuntimeError('managed block markers are corrupt; refusing to modify file')
    stop = ei + len(end)
    if text[stop:stop+1] == "\n":
        stop += 1
    return (si, stop)


def _build_block(ctx: Dict[str, Any]) -> str:
    ws = str(ctx['workspace'])
    cfg = str(ctx['config_path'])
    vault = str(ctx['vault'])
    dist = str(_dist_ask())
    start, end = _markers(ctx['workspace'])
    cmd = '%s %s validate --config %s --json' % (
        shlex.quote('python3'), shlex.quote(dist), shlex.quote(cfg))
    lines = [
        start,
        '# ASK workspace enrollment (managed block — do not edit by hand)',
        '',
        'This block is managed for exactly one ASK workspace. Update or remove',
        'it only with the workspace enrollment tooling (connect/disconnect).',
        'Enrollment never touches credentials or settings files and never',
        'grants permissions; the owner constrains actual runtime access.',
        '',
        'Workspace: `%s`' % ws,
        'Config: `%s`' % cfg,
        'Vault root: `%s`' % vault,
        '',
        'Bootstrap — read these notes in order at the start of every session',
        'and across project tasks. Start from step 1 even if your entry point',
        'already loaded one of these notes early:',
        '',
        '1. `%s/date.md`' % vault,
        '2. `%s/INDEX.md`' % vault,
        '3. `%s/agents.md`' % vault,
        '4. `%s/knowledge-map.md`' % vault,
        '',
        'After the ordered bootstrap, route from the knowledge map, then follow',
        'the knowledge continuity loop (`knowledge-continuity-loop.md`).',
        'Delegated workers without knowledge-base access (no-KB workers) must',
        'skip this bootstrap and follow only the delegating prompt.',
        '',
        'Validate the workspace with this exact command:',
        '',
        '    %s' % cmd,
        '',
        'Access declarations are guidance only. The owner must explicitly grant',
        'and constrain actual runtime filesystem permissions.',
        end,
    ]
    return '\n'.join(lines) + '\n'


def _registry_path(workspace: Path) -> Path:
    return _reject_symlinks(workspace / '.ask' / 'runtime.json', 'registry')


def _read_registry(workspace: Path) -> Dict[str, Any]:
    path = _registry_path(workspace)
    if not path.exists():
        return {'version': 1, 'runtimes': {}}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise RuntimeError('cannot read enrollment registry: %s' % e)
    if not isinstance(data, dict) or not isinstance(data.get('runtimes'), dict):
        raise RuntimeError('enrollment registry is corrupt')
    return data


def _write_registry(workspace: Path, data: Dict[str, Any]) -> None:
    path = _registry_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, sort_keys=True) + '\n'
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix='.tmp-runtime-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            f.write(payload)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _atomic_write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix='.tmp-ask-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _manual_instructions(ctx: Dict[str, Any], runtime_key: str) -> str:
    dist = str(_dist_ask())
    return (
        'Manual setup for runtime "%s" (no files were written).\n'
        '1. Open this workspace in the agent runtime: %s\n'
        '2. Point the runtime instructions at config %s (vault %s).\n'
        '3. Instruct the agent to read, in order: date.md, INDEX.md, '
        'agents.md, knowledge-map.md, then route from the knowledge map and '
        'follow knowledge-continuity-loop.md.\n'
        '4. Validate with: %s %s validate --config %s --json\n'
        'Enrollment state is recorded as manual; the owner completes the '
        'wiring by hand.'
        % (runtime_key, ctx['workspace'], ctx['config_path'], ctx['vault'],
           shlex.quote('python3'), shlex.quote(dist),
           shlex.quote(str(ctx['config_path']))))


def connect(config_path: Union[str, Path], runtime: str,
            home: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Enroll a workspace with a runtime; returns enrollment details."""
    ctx = _load_config(config_path)
    _read_registry(ctx['workspace'])  # Preflight before changing an adapter.
    managed, key = _normalize_runtime(runtime)
    if managed is None:
        reg = _read_registry(ctx['workspace'])
        reg['runtimes'][key] = {
            'target': None,
            'state': 'manual',
            'workspace': str(ctx['workspace']),
            'config': str(ctx['config_path']),
            'vault': str(ctx['vault']),
        }
        _write_registry(ctx['workspace'], reg)
        return {
            'runtime': key,
            'target': None,
            'workspace': str(ctx['workspace']),
            'config': str(ctx['config_path']),
            'vault': str(ctx['vault']),
            'state': 'manual',
            'instructions': _manual_instructions(ctx, key),
        }
    target = _expected_target(managed, home)
    _reject_symlinks(target.parent if not target.exists() else target, 'adapter target')
    if os.path.islink(target):
        raise RuntimeError('adapter target is a symlink: %s' % target)
    existing = ''
    if target.exists():
        if not target.is_file():
            raise RuntimeError('adapter target is not a file: %s' % target)
        existing = target.read_text(encoding='utf-8')
    block = _build_block(ctx)
    span = _owned_span(existing, ctx['workspace'])
    if span is None:
        prefix = existing
        if prefix and not prefix.endswith('\n'):
            prefix += '\n'
        if prefix and not prefix.endswith('\n\n'):
            prefix += '\n'
        updated = prefix + block
        created = True
    else:
        updated = existing[:span[0]] + block + existing[span[1]:]
        if not updated.endswith('\n'):
            updated += '\n'
        created = False
    _atomic_write_file(target, updated)
    reg = _read_registry(ctx['workspace'])
    reg['runtimes'][managed] = {
        'target': str(target),
        'state': 'configured-unverified',
        'config_digest': ctx['config_digest'],
        'workspace': str(ctx['workspace']),
        'config': str(ctx['config_path']),
        'vault': str(ctx['vault']),
    }
    _write_registry(ctx['workspace'], reg)
    return {
        'runtime': managed,
        'target': str(target),
        'workspace': str(ctx['workspace']),
        'config': str(ctx['config_path']),
        'vault': str(ctx['vault']),
        'state': 'configured-unverified',
        'created': created,
    }


def disconnect(config_path: Union[str, Path], runtime: str,
               home: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Remove only the owned managed block; returns removal details."""
    ctx = _load_config(config_path)
    _read_registry(ctx['workspace'])  # Preflight before changing an adapter.
    managed, key = _normalize_runtime(runtime)
    reg = _read_registry(ctx['workspace'])
    name = managed if managed is not None else key
    entry = reg['runtimes'].get(name)
    if not isinstance(entry, dict):
        raise RuntimeError('runtime is not enrolled for this workspace: %s' % name)
    if managed is None:
        del reg['runtimes'][name]
        _write_registry(ctx['workspace'], reg)
        return {'runtime': name, 'state': 'removed', 'target': None, 'removed': True}
    expected = _expected_target(managed, home)
    stored = entry.get('target')
    if stored != str(expected):
        raise RuntimeError(
            'stored enrollment target does not match recomputed target; refusing to modify files')
    target = _reject_symlinks(expected, 'adapter target')
    removed = False
    if target.exists():
        if os.path.islink(target):
            raise RuntimeError('adapter target is a symlink: %s' % target)
        text = target.read_text(encoding='utf-8')
        span = _owned_span(text, ctx['workspace'])
        if span is not None:
            rest = text[:span[0]] + text[span[1]:]
            if rest.strip() == '':
                target.unlink()
            else:
                _atomic_write_file(target, rest)
            removed = True
    del reg['runtimes'][name]
    _write_registry(ctx['workspace'], reg)
    return {
        'runtime': name,
        'target': str(expected),
        'workspace': str(ctx['workspace']),
        'removed': removed,
        'state': 'removed',
    }


def inspect(config_path: Union[str, Path], runtime: str,
            home: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Report enrollment state without modifying files."""
    ctx = _load_config(config_path)
    _read_registry(ctx['workspace'])  # Preflight before changing an adapter.
    managed, key = _normalize_runtime(runtime)
    name = managed if managed is not None else key
    reg = _read_registry(ctx['workspace'])
    entry = reg['runtimes'].get(name)
    if not isinstance(entry, dict):
        result = {
            'runtime': name,
            'configured': False,
            'state': 'not-configured',
            'workspace': str(ctx['workspace']),
            'config': str(ctx['config_path']),
            'vault': str(ctx['vault']),
        }
        if managed is not None:
            result['target'] = str(_expected_target(managed, home))
            result['file_exists'] = False
            result['block_present'] = False
        return result
    result = {
        'runtime': name,
        'configured': True,
        'state': entry.get('state', 'configured-unverified'),
        'workspace': str(ctx['workspace']),
        'config': str(ctx['config_path']),
        'vault': str(ctx['vault']),
    }
    if managed is not None:
        expected = _expected_target(managed, home)
        result['target'] = str(expected)
        result['stored_target'] = entry.get('target')
        _reject_symlinks(expected, 'adapter target')
        exists = expected.exists() and not os.path.islink(expected)
        result['file_exists'] = bool(exists)
        present = False
        if exists:
            try:
                text = expected.read_text(encoding='utf-8')
            except OSError:
                text = ''
            try:
                span = _owned_span(text, ctx['workspace'])
                present = span is not None and text[span[0]:span[1]].strip() == _build_block(ctx).strip()
            except RuntimeError:
                present = False
        result['block_present'] = present
        if not present or entry.get('target') != str(expected) or entry.get('config_digest') != ctx['config_digest']:
            result['configured'] = False
            result['state'] = 'not-configured'
    else:
        result['target'] = None
    if isinstance(entry.get('evidence'), dict):
        result['evidence'] = entry['evidence']
    return result


def verification_prompt(config_path: Union[str, Path]) -> str:
    """Return controller instructions for proving enrollment in a fresh session."""
    ctx = _load_config(config_path)
    dist = str(_dist_ask())
    scratch = 'Tasks/_ask_verification_sentinel.md'
    cmd = '%s %s validate --config %s --json' % (
        shlex.quote('python3'), shlex.quote(dist),
        shlex.quote(str(ctx['config_path'])))
    return (
        'ASK enrollment verification (controller-run; no execution here).\n'
        '\n'
        '1. As the controller, write a fresh random synthetic sentinel token '
        '(no secrets) into the explicitly named scratch note "%s" inside the '
        'vault at %s.\n'
        '2. Test one fresh session inside the workspace, then from a directory unrelated to the workspace (outside %s), start a '
        'fresh agent session with the enrolled runtime so no workspace files '
        'are preloaded from the working directory.\n'
        '3. Ask the fresh agent to report: (a) the bootstrap read sequence in '
        'order — date.md, INDEX.md, agents.md, knowledge-map.md; '
        '(b) the vault root %s; (c) the exact sentinel value read back from '
        '"%s".\n'
        '4. Confirm the reported sequence matches the configured order and the '
        'sentinel matches the synthetic value, then record the actual observed '
        'evidence with record_verification (evidence must be non-empty and '
        'contain no secrets).\n'
        '5. Optional cross-check: %s\n'
        '\n'
        'Do not mark the enrollment verified based on registration alone; only '
        'actual fresh-session proof counts. Evidence JSON requires bootstrap_files (the four filenames in order), '
        'inside_session and outside_session objects, each with session_id and observed_phrase. '
        'The two session IDs must differ, and both observed phrases must match the fixture. '
        'Create the scratch note with valid frontmatter and link it from Tasks/INDEX.md; remove both after proof.'
        % (scratch, ctx['vault'], ctx['workspace'], ctx['vault'],
           scratch, cmd))


def record_verification(config_path: Union[str, Path], runtime: str,
                        evidence: Dict[str, Any],
                        home: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Record controller-observed fresh-session proof for an enrolled runtime."""
    ctx = _load_config(config_path)
    _read_registry(ctx['workspace'])  # Preflight before changing an adapter.
    managed, key = _normalize_runtime(runtime)
    name = managed if managed is not None else key
    reg = _read_registry(ctx['workspace'])
    entry = reg['runtimes'].get(name)
    if not isinstance(entry, dict):
        raise RuntimeError('runtime is not enrolled for this workspace: %s' % name)
    if not isinstance(evidence, dict) or not evidence:
        raise RuntimeError('evidence must be a non-empty object')
    for k, v in evidence.items():
        if not isinstance(k, str) or not k.strip():
            raise RuntimeError('evidence keys must be non-empty strings')
        lowered = k.strip().lower()
        if any(hint in lowered for hint in SECRET_KEY_HINTS):
            raise RuntimeError('evidence must not contain secrets: %s' % k)
        if v is None or (isinstance(v, str) and not v.strip()):
            raise RuntimeError('evidence values must be non-empty: %s' % k)
        if not isinstance(v, (str, int, float, bool, list, dict)):
            raise RuntimeError('evidence value has unsupported type: %s' % k)
    if managed and not inspect(config_path, runtime, home=home).get('block_present'):
        raise RuntimeError('managed bootstrap is missing or changed; reconnect before verification')
    if evidence.get('bootstrap_files') != BOOTSTRAP_ORDER:
        raise RuntimeError('evidence must include the observed ordered bootstrap_files')
    for location in ('inside_session', 'outside_session'):
        proof = evidence.get(location)
        if not isinstance(proof, dict) or not all(isinstance(proof.get(k), str) and proof[k].strip() for k in ('session_id', 'observed_phrase')):
            raise RuntimeError('evidence needs %s session_id and observed_phrase' % location)
    if evidence['inside_session']['session_id'] == evidence['outside_session']['session_id']:
        raise RuntimeError('inside and outside proof must be different fresh sessions')
    if evidence['inside_session']['observed_phrase'] != evidence['outside_session']['observed_phrase']:
        raise RuntimeError('fresh sessions did not observe the same verification phrase')
    entry['config_digest'] = ctx['config_digest']
    entry['evidence'] = dict(evidence)
    entry['state'] = 'verified'
    reg['runtimes'][name] = entry
    _write_registry(ctx['workspace'], reg)
    return {
        'runtime': name,
        'workspace': str(ctx['workspace']),
        'config': str(ctx['config_path']),
        'state': 'verified',
        'evidence': dict(evidence),
    }
