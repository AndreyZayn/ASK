"""Workspace defaults and explicit legacy configuration, without executing settings.

Native installations need no settings file. Optional INI overrides are data;
validation rules live in schema.py. Existing JSON installations remain explicit.
"""
import configparser
from copy import deepcopy
import io
import json
from pathlib import Path

BOOTSTRAP = ['date.md', 'INDEX.md', 'agents.md', 'knowledge-map.md']
WRITABLE = ['Projects', 'People', 'Personal', 'Tasks', 'Memory', 'date.md',
            'goals.md', 'INDEX.md', 'Agents/capabilities']
DEFAULTS = {'version': 1, 'ask_version': '1.0.0', 'template_version': '1.0.0',
            'vault_root': 'Knowledge Base', 'bootstrap_files': BOOTSTRAP,
            'access': {'read': ['.'], 'write': WRITABLE},
            'validation': {'topology': True}, 'backup': {'mode': 'session'}}


def safe_path(path):
    path = Path(path).expanduser().absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise ValueError('symlink path is not allowed: %s' % current)
    return path


def workspace(reference):
    p = Path(reference).expanduser().absolute()
    return p if p.is_dir() else p.parent


def native(ws):
    marker = safe_path(Path(ws)/'system/install-manifest.json')
    if not marker.is_file():
        return False
    try:
        return json.loads(marker.read_text(encoding='utf-8')).get('workspace_layout') == 2
    except (ValueError, AttributeError):
        raise ValueError('invalid installed manifest; installation was preserved')


def reference(workspace_path=None, config_path=None):
    """Resolve a CLI selector. Legacy files are never silently replaced."""
    p = safe_path(workspace_path if workspace_path is not None else config_path)
    if workspace_path is not None and not p.is_dir():
        raise ValueError('workspace is not a directory: %s' % p)
    if not p.is_dir():
        if not p.is_file():
            raise ValueError('configuration file does not exist: %s' % p)
        return p
    legacy = safe_path(p/'ask.json')
    is_native = native(p)
    if legacy.exists():
        if is_native:
            raise ValueError('ambiguous native workspace and legacy ask.json; select the legacy file explicitly with --config or reconcile manually; nothing was migrated')
        return legacy
    if not is_native:
        raise ValueError('native installation marker system/install-manifest.json is missing or unsupported; restore installed system files or select an existing legacy --config; nothing was migrated')
    if (p/'note.schema.json').exists() or (p/'note.schema.json').is_symlink():
        raise ValueError('unexpected legacy note.schema.json in native workspace; reconcile manually; nothing was migrated')
    return p


def read(reference_path):
    ref = reference(config_path=reference_path)
    if ref.is_file():
        data = json.loads(ref.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('configuration must be an object')
        return data
    data = deepcopy(DEFAULTS)
    settings = safe_path(ref/'system/settings.ini')
    if not settings.exists():
        return data
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(settings.read_text(encoding='utf-8'))
        allowed = {'workspace': {'vault_root'}, 'access': {'read','write'},
                   'validation': {'topology'}, 'backup': {'mode','repository'}}
        if parser.defaults():
            raise ValueError('DEFAULT values are unsupported')
        for section in parser.sections():
            if section not in allowed or set(parser[section])-allowed[section]:
                raise ValueError('unsupported settings section or key: %s' % section)
            for key, value in parser[section].items():
                if section == 'workspace':
                    data[key] = value
                elif section == 'access':
                    data[section][key] = [v.strip() for v in value.splitlines() if v.strip()]
                elif section == 'validation':
                    data[section][key] = parser.getboolean(section,key)
                else:
                    data[section][key] = value
        raw = data['vault_root']
        p = Path(raw)
        if (not raw or p.is_absolute() or '..' in p.parts or '\\' in raw or p == Path('.')
                or any(ord(c) < 32 for c in raw) or p.parts[0].startswith('~') or p.parts[0].casefold() in {'system','artifacts','.ask','.git'}):
            raise ValueError('native vault_root must be a relative directory within the workspace, outside reserved directories')
        if data['backup']['mode'] not in ('session','scheduled'):
            raise ValueError('backup.mode must be session or scheduled')
    except configparser.Error as e:
        raise ValueError('invalid system/settings.ini: %s' % type(e).__name__)
    return data


def save(reference_path, data):
    """Only deliberate setup changes call this; reruns preserve settings bytes."""
    ref = reference(config_path=reference_path)
    if ref.is_file():
        if ref.stat().st_nlink != 1:
            raise ValueError('configuration is a hardlink; original files preserved')
        ref.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        return ref.name
    settings = safe_path(ref/'system/settings.ini')
    if settings.exists() and settings.stat().st_nlink != 1:
        raise ValueError('settings are a hardlink; original files preserved')
    parser = configparser.ConfigParser(interpolation=None)
    if settings.exists():
        parser.read_string(settings.read_text(encoding='utf-8'))
    for section, values in [('workspace', {'vault_root':data['vault_root']}),
                            ('access',data['access']), ('validation',data['validation']),
                            ('backup',data['backup'])]:
        defaults = {'vault_root':DEFAULTS['vault_root']} if section=='workspace' else DEFAULTS[section]
        for key,value in values.items():
            if value == defaults.get(key) and not parser.has_option(section,key):
                continue
            if not parser.has_section(section):
                parser.add_section(section)
            parser[section][key] = ('\n'.join(value) if isinstance(value,list)
                                    else str(value).lower() if isinstance(value,bool) else str(value))
    if parser.sections():
        out=io.StringIO(); parser.write(out)
        settings.write_text(out.getvalue(),encoding='utf-8')
    return 'system/settings.ini'


def add_selector(parser):
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--workspace','--root',dest='workspace',help='Installed workspace root')
    group.add_argument('--config',help='Existing legacy JSON configuration (no migration)')
