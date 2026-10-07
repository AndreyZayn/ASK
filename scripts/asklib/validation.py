"""Advanced validation wrapper (Markdown links, topology, staged index).

Integrates with the base validator in ``ask.py`` through an ``api`` module
argument to avoid import cycles. The caller passes the base module (which
provides ``load_config``, ``validate_vault``, ``parse_frontmatter``,
``mask_code``, ``resolve_link`` and ``AskError``)::

    import ask as api
    from asklib import validation
    report, graph = validation.validate(api, config_path)

``files`` is report metadata only and never filters the validated set: the
whole vault (or the whole staged snapshot) is always validated.

Standard library only, Python 3.9 compatible. No shell, no checkout, no
mutation of the repository.
"""

import json
import os
import re
import subprocess
import tempfile
from datetime import date as _date
from pathlib import Path
from urllib.parse import unquote

__all__ = ['validate']

_SCHEME_RE = re.compile(r'^[A-Za-z][A-Za-z0-9+.\-]*:')
_DEF_RE = re.compile(
    r'(?m)^[ ]{0,3}\[([^\]\n]+)\]:[ \t]*'
    r'(<[^>\n]*>|[^ \t\n]+)'
    r'(?:[ \t]+("[^"\n]*"|\'[^\'\n]*\'|\([^)\n]*\)))?[ \t]*$')
_REF_USE_RE = re.compile(r'(!?)\[([^\]\n]*)\]\[([^\]\n]*)\]')
_INLINE_OPEN_RE = re.compile(r'(!?)\[([^\]\n]*)\]\(')

_DATED_PREFIXES = (
    'Tasks/Daily/',
    'Memory/Logs/',
    'Memory/Weekly/',
    'Memory/Monthly/',
)


def _error_report(message):
    return (
        {'configuration_error': True, 'counts': {'notes': 0, 'errors': 1},
         'issues': [{'file': '', 'message': str(message)}]},
        {'nodes': [], 'edges': []},
    )


def _topology_enabled(ctx, config_path):
    try:
        flag = ctx.get('validation', {}).get('topology')
        if flag is True:
            return True
    except AttributeError:
        pass
    try:
        raw = json.loads(Path(config_path).read_text(encoding='utf-8'))
        if isinstance(raw, dict) and isinstance(raw.get('validation'), dict):
            return raw['validation'].get('topology') is True
    except (OSError, ValueError, UnicodeError):
        pass
    return False


def _list_notes(api, vault):
    fn = getattr(api, 'note_files', None)
    if fn is not None:
        res = fn(vault)
        if isinstance(res, tuple) and len(res) == 2:
            notes, _atts = res
            return sorted(Path(p) for p in notes)
        return sorted(Path(p) for p in res)
    found = []
    for root, dirs, files in os.walk(vault, followlinks=False):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            if f.startswith('.'):
                continue
            p = Path(root) / f
            if p.suffix.lower() == '.md':
                found.append(p)
    return sorted(found)


def _parse_inline_links(text):
    """Yield raw destination strings of inline ``[t](dest)`` / ``![a](dest)``."""
    dests = []
    n = len(text)
    for m in _INLINE_OPEN_RE.finditer(text):
        pos = m.end()
        p = pos
        while p < n and text[p] in ' \t\n':
            p += 1
        if p >= n:
            continue
        dest = None
        if text[p] == '<':
            end = text.find('>', p + 1)
            if end < 0:
                continue
            dest = text[p + 1:end]
            p = end + 1
            while p < n and text[p] in ' \t\n':
                p += 1
            if p < n and text[p] in ('"', "'", '('):
                q = text[p]
                if q == '(':
                    close = text.find(')', p + 1)
                    if close < 0:
                        continue
                    p = close + 1
                else:
                    close = text.find(q, p + 1)
                    if close < 0:
                        continue
                    # title must stay on one line
                    if '\n' in text[p + 1:close]:
                        continue
                    p = close + 1
                while p < n and text[p] in ' \t\n':
                    p += 1
            if p >= n or text[p] != ')':
                continue
            dests.append(dest)
            continue
        # Bare destination with balanced parentheses; ends at space or ')'.
        depth = 0
        start = p
        closed = False
        while p < n:
            c = text[p]
            if c == '(':
                depth += 1
                p += 1
            elif c == ')':
                if depth == 0:
                    closed = True
                    break
                depth -= 1
                p += 1
            elif c in ' \t\n' and depth == 0:
                break
            elif c == '\\' and p + 1 < n and text[p + 1] in '()\\':
                p += 2
            else:
                p += 1
        dest = text[start:p]
        while p < n and text[p] in ' \t\n':
            p += 1
        if p < n and text[p] in ('"', "'", '('):
            q = text[p]
            if q == '(':
                close = text.find(')', p + 1)
                if close < 0:
                    continue
                p = close + 1
            else:
                close = text.find(q, p + 1)
                if close < 0:
                    continue
                if '\n' in text[p + 1:close]:
                    continue
                p = close + 1
            while p < n and text[p] in ' \t\n':
                p += 1
        if p >= n or text[p] != ')':
            if not closed:
                continue
            # Ended at inner space without title handling; re-check close.
            if p >= n:
                continue
        if not closed and (p >= n or text[p] != ')'):
            continue
        dests.append(dest)
    return dests


def _reference_dests(masked):
    defs = {}
    for m in _DEF_RE.finditer(masked):
        label = m.group(1).strip().lower()
        dest = m.group(2).strip()
        if dest.startswith('<') and dest.endswith('>') and len(dest) >= 2:
            dest = dest[1:-1]
        if label and label not in defs:
            defs[label] = dest
    dests = []
    for m in _REF_USE_RE.finditer(masked):
        text_label = (m.group(2) or '').strip().lower()
        ref_label = (m.group(3) or '').strip().lower()
        key = ref_label if ref_label else text_label
        if not key:
            continue
        if key in defs:
            dests.append(defs[key])
    return dests


def _check_markdown_dest(vault, vault_resolved, source, raw_dest):
    """Return (target_rel_posix, error_message). Ignorable -> (None, None)."""
    dest = (raw_dest or '').strip()
    if not dest:
        return None, None
    if dest.startswith('#'):
        return None, None
    filepart = dest.split('#', 1)[0]
    if '?' in filepart:
        filepart = filepart.split('?', 1)[0]
    filepart = filepart.strip()
    if not filepart:
        return None, None
    if _SCHEME_RE.match(filepart):
        return None, None
    if filepart.startswith('//'):
        return None, None
    try:
        decoded = unquote(filepart).strip()
    except Exception:
        decoded = filepart
    if not decoded or decoded.startswith('#'):
        return None, None
    if _SCHEME_RE.match(decoded):
        return None, None
    if decoded.startswith('//'):
        return None, None
    if decoded.startswith('/') or '\\' in decoded:
        return None, 'markdown link escapes vault: %s' % raw_dest
    import posixpath as _pp
    try:
        parts = Path(decoded).parts
    except Exception:
        return None, 'markdown link escapes vault: %s' % raw_dest
    try:
        try:
            src_rel = source.resolve().relative_to(vault_resolved)
        except ValueError:
            src_rel = Path(os.path.abspath(str(source))).relative_to(
                Path(os.path.abspath(str(vault))))
    except (ValueError, OSError):
        return None, 'markdown link escapes vault: %s' % raw_dest
    src_dir = src_rel.parent.as_posix()
    joined = _pp.normpath(_pp.join(src_dir, decoded))
    if joined == '.' or joined.startswith('../') or joined == '..':
        return None, 'markdown link escapes vault: %s' % raw_dest
    rel = Path(joined)
    if str(rel) == '.' or rel.parts[:1] == ('..',):
        return None, 'markdown link escapes vault: %s' % raw_dest
    # Symlink check on every component including the target itself.
    cur = vault_resolved
    for part in rel.parts:
        cur = cur / part
        try:
            if os.path.islink(cur):
                return None, 'markdown link traverses symlink: %s' % raw_dest
        except OSError:
            return None, 'markdown link traverses symlink: %s' % raw_dest
    full = vault_resolved / rel
    try:
        if not full.exists():
            return None, 'markdown link target missing: %s' % raw_dest
        if not full.is_file() or os.path.islink(full):
            return None, 'markdown link target missing: %s' % raw_dest
    except OSError:
        return None, 'markdown link target missing: %s' % raw_dest
    return rel.as_posix(), None


def _dated_kind(rel):
    if Path(rel).name == 'INDEX.md':
        return None
    for prefix in _DATED_PREFIXES:
        if rel.startswith(prefix) and Path(rel).parent.as_posix() + '/' == prefix:
            return prefix
    return None


def _valid_dated_filename(prefix, rel):
    stem = Path(rel).stem
    if prefix == 'Tasks/Daily/':
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', stem):
            return False
        try:
            _date.fromisoformat(stem)
        except ValueError:
            return False
        return True
    if prefix in ('Memory/Logs/', 'Memory/Monthly/'):
        return re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', stem) is not None
    if prefix == 'Memory/Weekly/':
        if not re.fullmatch(r'\d{4}-W(0[1-9]|[1-4][0-9]|5[0-3])', stem):
            return False
        try:
            _date.fromisocalendar(int(stem[:4]), int(stem[6:]), 1)
            return True
        except ValueError:
            return False
    return False


def _nearest_index(rel, notes_set):
    if rel == 'INDEX.md':
        return None
    if '/' not in rel:
        cand = 'INDEX.md'
        return cand if cand in notes_set else False
    if rel.endswith('INDEX.md'):
        start = Path(rel).parent.parent
    else:
        start = Path(rel).parent
    cur = start
    while True:
        cand = 'INDEX.md' if str(cur) == '.' else (cur / 'INDEX.md').as_posix()
        if cand in notes_set:
            return cand
        if str(cur) == '.':
            return False
        cur = cur.parent


def _validate_snapshot(api, config_path, files, redact=None):
    AskError = api.AskError
    try:
        ctx = api.load_config(str(config_path))
    except AskError as e:
        return _error_report(e)
    topology = _topology_enabled(ctx, config_path)
    try:
        report, graph = api.validate_vault(ctx)
    except AskError as e:
        return _error_report(e)
    vault = Path(ctx['vault'])
    try:
        vault_resolved = vault.resolve()
    except OSError:
        vault_resolved = vault.absolute()
    try:
        notes = _list_notes(api, vault)
    except AskError:
        notes = []
    issues = list(report.get('issues', []))
    edges = list(graph.get('edges', []))
    nodes = list(graph.get('nodes', []))
    node_ids = {n.get('id') for n in nodes}
    md_pairs = []
    if notes:
        notes_set = set()
        for p in notes:
            try:
                notes_set.add(p.relative_to(vault_resolved).as_posix())
            except ValueError:
                try:
                    notes_set.add(p.relative_to(vault).as_posix())
                except ValueError:
                    continue
        for p in notes:
            try:
                rel = p.relative_to(vault_resolved).as_posix()
            except ValueError:
                try:
                    rel = p.relative_to(vault).as_posix()
                except ValueError:
                    continue
            try:
                text = p.read_text(encoding='utf-8')
            except (OSError, UnicodeError):
                continue
            try:
                _meta, body = api.parse_frontmatter(text)
            except (ValueError, UnicodeError):
                continue
            try:
                masked = api.mask_code(body)
            except Exception:
                masked = body
            dests = _parse_inline_links(masked) + _reference_dests(masked)
            for d in dests:
                target_rel, err = _check_markdown_dest(
                    vault, vault_resolved, p, d)
                if err is not None:
                    issues.append({'file': rel, 'message': err})
                elif target_rel is not None:
                    md_pairs.append((rel, target_rel))
        seen = set()
        for src, tgt in md_pairs:
            key = (src, tgt, 'navigational')
            if key not in seen:
                seen.add(key)
                edges.append({'source': src, 'target': tgt, 'type': 'navigational'})
        for _src, tgt in md_pairs:
            if tgt not in node_ids:
                node_ids.add(tgt)
                nodes.append({'id': tgt, 'type': 'attachment', 'metadata': {'kind': 'attachment'}})
        edges = sorted({(e['source'], e['target'], e['type']) for e in edges})
        edges = [{'source': a, 'target': b, 'type': c} for a, b, c in edges]
        if topology:
            notes_rels = set()
            for p in notes:
                try:
                    notes_rels.add(p.relative_to(vault_resolved).as_posix())
                except ValueError:
                    try:
                        notes_rels.add(p.relative_to(vault).as_posix())
                    except ValueError:
                        continue
            inbound = {}
            for e in edges:
                if e.get('type') == 'navigational':
                    inbound.setdefault(e['target'], set()).add(e['source'])
            for rel in sorted(notes_rels):
                if not rel.lower().endswith('.md'):
                    continue
                prefix = _dated_kind(rel)
                if prefix is not None:
                    if not _valid_dated_filename(prefix, rel):
                        issues.append({
                            'file': rel,
                            'message': 'dated record filename is not a valid date: %s' % rel})
                    owner = (Path(rel).parent / 'INDEX.md').as_posix()
                    if owner not in notes_rels:
                        issues.append({
                            'file': rel,
                            'message': 'dated record folder INDEX is required: %s' % owner})
                    continue
                if rel == 'INDEX.md':
                    continue
                need = _nearest_index(rel, notes_rels)
                if need is None:
                    continue
                if need is False:
                    issues.append({
                        'file': rel,
                        'message': 'no ancestor INDEX.md found for topology'})
                    continue
                if rel not in inbound or need not in inbound[rel]:
                    issues.append({
                        'file': rel,
                        'message': 'topology: no inbound link from %s' % need})
    out_report = {
        'counts': {'notes': report.get('counts', {}).get('notes', len(notes)),
                   'errors': len(issues)},
        'issues': issues,
    }
    if files is not None:
        out_report['files'] = [str(f) for f in files]
    out_graph = {'nodes': nodes, 'edges': edges}
    if redact:
        tag = '<staged>'
        for it in out_report['issues']:
            for k in ('file', 'message'):
                v = it.get(k)
                if isinstance(v, str) and redact in v:
                    it[k] = v.replace(redact, tag)
    return out_report, out_graph


def _git_run(args, cwd):
    return subprocess.run(
        ['git'] + list(args), cwd=str(cwd),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _validate_staged(api, config_path, files):
    AskError = api.AskError
    try:
        cfg_abs = Path(config_path).expanduser()
        if not cfg_abs.is_absolute():
            cfg_abs = Path.cwd() / cfg_abs
        cfg_abs = cfg_abs.absolute()
        r = _git_run(['rev-parse', '--show-toplevel'], cfg_abs.parent)
        if r.returncode != 0:
            raise AskError('not inside a git workspace')
        top = Path(r.stdout.decode('utf-8', 'surrogateescape').strip())
        try:
            top_resolved = top.resolve()
        except OSError:
            top_resolved = top.absolute()
        try:
            cfg_parent = cfg_abs.parent.resolve()
        except OSError:
            cfg_parent = cfg_abs.parent.absolute()
        if cfg_parent != top_resolved:
            raise AskError('config must be in the workspace git root')
        r = _git_run(['ls-files', '--stage', '-z'], top_resolved)
        if r.returncode != 0:
            raise AskError('cannot read git index')
        data = r.stdout or b''
        entries = []
        if data:
            for chunk in data.split(b'\0'):
                if not chunk:
                    continue
                try:
                    meta, raw_path = chunk.split(b'\t', 1)
                except ValueError:
                    raise AskError('cannot parse git index')
                try:
                    meta_s = meta.decode('utf-8', 'surrogateescape')
                    path_s = raw_path.decode('utf-8', 'surrogateescape')
                except ValueError:
                    raise AskError('cannot parse git index')
                m = meta_s.split(' ')
                if len(m) != 3:
                    raise AskError('cannot parse git index')
                mode, sha, stage = m
                if stage != '0':
                    raise AskError('unmerged index entry: %s' % path_s)
                if mode == '120000':
                    raise AskError('symlink in index: %s' % path_s)
                if mode == '160000':
                    raise AskError('submodule in index: %s' % path_s)
                if not path_s or path_s.startswith('/') or '\\' in path_s:
                    raise AskError('index path escapes workspace: %s' % path_s)
                if any(x == '..' for x in Path(path_s).parts):
                    raise AskError('index path escapes workspace: %s' % path_s)
                entries.append((mode, sha, path_s))
        indexed = {p for (_m, _s, p) in entries}
        try:
            config_rel = cfg_abs.relative_to(top_resolved).as_posix()
        except ValueError:
            raise AskError('config must be in the workspace git root')
        if config_rel not in indexed:
            raise AskError('config must exist in the index: %s' % config_rel)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            try:
                tmp_resolved = tmp_p.resolve()
            except OSError:
                tmp_resolved = tmp_p.absolute()
            for mode, sha, rel in entries:
                if rel == '.git' or rel.startswith('.git/'):
                    continue
                if rel == '.ask' or rel.startswith('.ask/'):
                    continue
                if mode not in ('100644', '100755'):
                    raise AskError('unsupported index mode for %s' % rel)
                c = _git_run(['cat-file', '-p', sha], top_resolved)
                if c.returncode != 0:
                    raise AskError('cannot read staged blob for %s' % rel)
                dest = tmp_resolved / rel
                try:
                    dest.relative_to(tmp_resolved)
                except ValueError:
                    raise AskError('index path escapes workspace: %s' % rel)
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open('wb') as f:
                    f.write(c.stdout)
            staged_config = tmp_resolved / config_rel
            if not staged_config.is_file():
                raise AskError('config must exist in the index: %s' % config_rel)
            raw_cfg = json.loads(staged_config.read_text(encoding='utf-8'))
            root = raw_cfg.get('vault_root', '')
            if not isinstance(root, str) or not root or Path(root).is_absolute() or '..' in Path(root).parts or Path(root) == Path('.'):
                raise AskError('staged vault_root must be a relative directory inside the workspace')
            return _validate_snapshot(
                api, staged_config, files, redact=str(tmp_resolved))
    except AskError as e:
        return _error_report(e)


def validate(api, config_path, staged=False, files=None):
    """Validate the vault (or staged index snapshot).

    ``api`` is the base module (``ask.py``) providing ``load_config``,
    ``validate_vault``, ``parse_frontmatter``, ``mask_code``,
    ``resolve_link`` and ``AskError``. Returns ``(report, graph)``.
    """
    if staged:
        return _validate_staged(api, Path(config_path), files)
    return _validate_snapshot(api, Path(config_path), files)
