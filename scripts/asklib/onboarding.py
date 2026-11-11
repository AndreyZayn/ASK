"""Read-only onboarding plans and caller-observed catalog row proposals.

This module never discovers runtime configuration, calls providers, writes notes,
registers identities, or certifies observations. The installing agent owns those
reviewed knowledge edits through the workspace's existing continuity process.
"""
import html
import json
from datetime import date
from pathlib import Path
import re

CATALOGS = {
    'roster': 'Agents/roster.md',
    'runtimes': 'Agents/capabilities/runtimes/INDEX.md',
    'skills': 'Agents/capabilities/skills/INDEX.md',
    'integrations': 'Agents/capabilities/integrations/INDEX.md',
    'plugins': 'Agents/capabilities/plugins/INDEX.md',
    'snapshots': 'Agents/capabilities/snapshots/INDEX.md',
}
KINDS = {'runtime': 'runtimes', 'skill': 'skills', 'integration': 'integrations', 'plugin': 'plugins'}
AVAILABILITY = {'exposed', 'configured-unverified', 'verified', 'unavailable', 'unknown'}


def _fields(api, value, names, label):
    if not isinstance(value, dict) or set(value) != set(names):
        raise api.AskError('%s must contain exactly: %s' % (label, ', '.join(names)))


def _text(api, value, label):
    if (not isinstance(value, str) or not value.strip() or len(value) > 1000
            or any(ord(c) < 32 for c in value) or len(value.splitlines()) != 1):
        raise api.AskError('%s must be non-empty single-line text (maximum 1000 characters)' % label)
    return value.strip()


def _slug(api, value, label):
    value = _text(api, value, label)
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', value):
        raise api.AskError('%s must be a lowercase local identifier using letters, digits, or hyphens' % label)
    return value


def _cell(value):
    return (html.escape(value, quote=True).replace('|', '&#124;')
            .replace('[', '&#91;').replace(']', '&#93;').replace('`', '&#96;'))


def _row(values):
    return '| ' + ' | '.join(_cell(value) for value in values) + ' |'


def _header(names):
    return _row(names) + '\n' + _row(['---'] * len(names))


def _profile(api, path, runtime_name):
    path = Path(path).expanduser().absolute()
    api.ensure_no_symlink_path(path)
    if path.stat().st_size > 256000:
        raise api.AskError('onboarding profile exceeds 256000 bytes')
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError):
        raise api.AskError('onboarding profile must be valid UTF-8 JSON')
    _fields(api, data, ('observed_on', 'coverage', 'agent', 'capabilities'), 'profile')
    observed = _text(api, data['observed_on'], 'observed_on')
    try:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', observed):
            raise ValueError()
        date.fromisoformat(observed)
    except ValueError:
        raise api.AskError('observed_on must be a valid YYYY-MM-DD date')
    data['coverage'] = _text(api, data['coverage'], 'coverage')
    agent = data['agent']
    _fields(api, agent, ('id', 'runtime', 'surface', 'role', 'scope', 'responsibility'), 'agent')
    for field in agent:
        agent[field] = (_slug if field in ('id', 'runtime') else _text)(api, agent[field], 'agent.' + field)
    if agent['runtime'] != runtime_name:
        raise api.AskError('profile runtime must match --runtime; use the same runtime identifier')
    if agent['role'] not in ('controller', 'worker', 'assistant'):
        raise api.AskError('agent.role must be controller, worker, or assistant')
    capabilities = data['capabilities']
    if not isinstance(capabilities, list) or len(capabilities) > 200:
        raise api.AskError('capabilities must be an array with at most 200 entries')
    seen = set()
    for capability in capabilities:
        _fields(api, capability, ('kind', 'name', 'purpose', 'availability', 'source', 'evidence', 'limits'), 'capability')
        for field in capability:
            capability[field] = _text(api, capability[field], 'capability.' + field)
        if capability['kind'] not in KINDS or capability['availability'] not in AVAILABILITY:
            raise api.AskError('unsupported capability kind or availability')
        key = (capability['kind'], capability['name'].casefold())
        if key in seen:
            raise api.AskError('duplicate capability kind/name within this runtime surface')
        seen.add(key)
    return data


def report(api, config_path, runtime_name, profile_path=None):
    ctx = api.load_config(config_path)
    runtime_name = _slug(api, runtime_name, 'runtime')
    result = {
        'state': 'onboarding-plan', 'applied': False, 'runtime_verified': False,
        'vault': str(ctx['vault']), 'runtime': runtime_name, 'catalogs': {},
        'instructions': [
            'Review the existing roster and local catalog layout before choosing an unused or matching agent ID.',
            'Inventory all exposed current-session skills when feasible; state partial coverage and use labeled batches above 200 entries. Record source, scope, limits, and date without inspecting secrets or installing capabilities.',
            'Merge reviewed proposals with existing notes; update matching rows rather than duplicating them. Missing/custom catalogs require the owner\'s existing layout, not replacement.',
            'Follow knowledge-continuity-loop.md for authorized edits, date/log upkeep, validation, scoped checkpoint, and backup.',
            'Runtime connection, fresh inside/outside proof, roster registration, and capability documentation are separate outcomes. This report certifies none of them.',
        ],
    }
    for name, preferred in CATALOGS.items():
        candidates = [preferred]
        if name in KINDS.values():
            candidates.append('Agents/capabilities/' + name + '.md')
        present = []
        readable = []
        for rel in candidates:
            if not any(entry == '.' or rel == entry or rel.startswith(entry + '/') for entry in ctx['access']['read']):
                continue
            readable.append(rel)
            path = ctx['vault'] / rel
            api.ensure_no_symlink_path(path)
            if path.is_file():
                present.append(rel)
        if len(present) > 1:
            raise api.AskError('multiple catalog layouts for %s; reconcile the intended catalog manually' % name)
        rel = present[0] if present else (readable[0] if readable else preferred)
        state = 'present' if present else ('missing' if readable else 'not-in-declared-read-scope')
        result['catalogs'][name] = {'path': rel, 'state': state}
    if profile_path is None:
        return result
    data = _profile(api, profile_path, runtime_name)
    agent = data['agent']
    result.update(state='onboarding-proposal', agent_id=agent['id'],
                  capability_count=len(data['capabilities']), observed_on=data['observed_on'],
                  coverage=data['coverage'])
    notes = [{
        'path': result['catalogs']['roster']['path'], 'key': {'agent_id': agent['id']},
        'header': _header(['Agent ID', 'Runtime', 'Surface', 'Role', 'Agreed scope', 'Responsibility', 'Recorded']),
        'row': _row([agent['id'], runtime_name, agent['surface'], agent['role'], agent['scope'], agent['responsibility'], data['observed_on']]),
    }]
    coverage = data['coverage']
    if not data['capabilities']:
        coverage += '; No capabilities reported within this coverage; not proof that none are installed'
    names = ['Capability', 'Runtime', 'Surface', 'Agent ID', 'Purpose', 'Availability', 'Source', 'Evidence', 'Limits', 'Observed']
    notes.append({
        'path': result['catalogs']['runtimes']['path'],
        'key': {'runtime': runtime_name, 'surface': agent['surface'], 'agent_id': agent['id']},
        'header': _header(names),
        'row': _row([runtime_name, runtime_name, agent['surface'], agent['id'], 'Current agent runtime', 'unknown',
                     'Caller-provided runtime identity', coverage, 'This proposal does not inspect enrollment or establish live access', data['observed_on']]),
    })
    for capability in data['capabilities']:
        notes.append({
            'path': result['catalogs'][KINDS[capability['kind']]]['path'],
            'key': {'kind': capability['kind'], 'name': capability['name'], 'runtime': runtime_name, 'surface': agent['surface']},
            'header': _header(names),
            'row': _row([capability['name'], runtime_name, agent['surface'], agent['id'], capability['purpose'],
                         capability['availability'], capability['source'], capability['evidence'], capability['limits'], data['observed_on']]),
        })
    available = []
    unresolved = []
    by_path = {item['path']: (name, item['state']) for name, item in result['catalogs'].items()}
    for note in notes:
        catalog, state = by_path[note['path']]
        if state == 'present':
            available.append(note)
        else:
            # Keep supplied facts without suggesting a destination we could not read.
            pending = {key: value for key, value in note.items() if key != 'path'}
            pending.update(catalog=catalog, catalog_state=state, applicable=False,
                           action='manual-mapping-required')
            unresolved.append(pending)
    result['notes'] = available
    result['unresolved'] = unresolved
    return result
