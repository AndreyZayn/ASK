"""ASK V1 orchestration. No model or background knowledge-writing dependency."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

from . import backup, gitops, runtime, validation, setup_checks

VERSION = '1.0.0'
COMMANDS = {'setup', 'doctor', 'agent', 'checkpoint', 'sync', 'write', 'backup'}


def emit(value):
    print(json.dumps(value, indent=2, sort_keys=True))


def _json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n', encoding='utf-8')


def _git(ws, *args):
    return subprocess.run(['git', *args], cwd=str(ws), capture_output=True, text=True, timeout=30)


def _context(api, config):
    cp = Path(config).expanduser().absolute()
    ctx = api.load_config(cp)
    if ctx['vault'].resolve() == cp.parent.resolve() or not api.inside(ctx['vault'], cp.parent):
        raise api.AskError('V1 vault must be a directory inside its private workspace')
    return cp, ctx


def _assert_valid(api, cp, staged=False):
    report, _ = validation.validate(api, cp, staged=staged)
    if report['counts']['errors']:
        raise api.AskError('; '.join('%s: %s' % (i['file'], i['message']) for i in report['issues'][:12]))
    return report


def _install_hook(api, cp):
    ws = cp.parent
    hooks = ws / '.ask' / 'hooks'
    api.ensure_no_symlink_path(hooks)
    current = _git(ws, 'config', '--local', '--get', 'core.hooksPath').stdout.strip()
    if current and Path(current) not in (hooks, Path('.ask/hooks')):
        raise api.AskError('existing core.hooksPath needs manual hook integration: %s' % current)
    default_hook = ws / '.git' / 'hooks' / 'pre-commit'
    if not current and default_hook.exists():
        raise api.AskError('existing pre-commit hook needs manual integration; it was preserved')
    hooks.mkdir(parents=True, exist_ok=True)
    hook = hooks / 'pre-commit'
    command = '%s %s validate --config %s --staged --json' % tuple(shlex.quote(str(x)) for x in (sys.executable, Path(api.__file__).resolve(), cp))
    content = '#!/bin/sh\n# ASK managed staged-snapshot validator\nexec '+command+'\n'
    if hook.exists() and '# ASK managed staged-snapshot validator' not in hook.read_text():
        raise api.AskError('foreign ASK hook path preserved')
    hook.write_text(content, encoding='utf-8')
    hook.chmod(0o700)
    r = _git(ws, 'config', '--local', 'core.hooksPath', str(hooks))
    if r.returncode:
        raise api.AskError(r.stderr)


def _setup(api, args):
    ws = Path(args.workspace).expanduser().absolute()
    api.ensure_no_symlink_path(ws)
    cp = ws / 'ask.json'
    fresh = not cp.exists()
    if not fresh:
        data = _json(cp)
        if not isinstance(data, dict) or data.get('ask_version') != VERSION:
            raise api.AskError('existing configuration is not a V1 installation; preserve it and follow the upgrade guide')
    else:
        if ws.exists() and any(ws.iterdir()):
            raise api.AskError('setup requires a new empty workspace; existing files were preserved')
        # Refuse an ancestor repository before writing any scaffold.
        parent = ws
        while not parent.exists():
            parent = parent.parent
        if _git(parent, 'rev-parse', '--show-toplevel').returncode == 0:
            raise api.AskError('private workspace must be outside every existing repository')
        with contextlib.redirect_stdout(io.StringIO()):
            api.init(argparse.Namespace(workspace=str(ws), vault_name=args.vault_name))
        data = _json(cp)
        data.update({'ask_version': VERSION, 'template_version': VERSION,
                     'validation': {'topology': True}, 'backup': {'mode': 'session'}})
        data['access']['write'] = [] if args.read_only else ['Projects','People','Personal','Tasks','Memory','date.md','goals.md','INDEX.md','Agents/capabilities']
        _save(cp, data)
        (ws/'AGENTS.md').write_text(
            '# ASK private workspace bootstrap\n\n'
            'Resolve paths relative to the directory containing this file, not the shell working directory.\n'
            'Read `ask.json` beside this file to locate `vault_root` and access declarations.\n'
            'For every session, read these notes under that vault in order: `date.md`, `INDEX.md`, `agents.md`, `knowledge-map.md`.\n'
            'Then route and follow the knowledge continuity loop before writing.\n'
            'Delegated workers with `KB_ACCESS: none` must skip vault access.\n'
            'Installation must also persist this bootstrap in the agent runtime; this workspace file alone does not prove enrollment.\n'
            'Use the separately installed ASK CLI and its agent connect/verify commands; preserve existing runtime instructions.\n'
            'Configuration declarations do not grant runtime permissions.\n', encoding='utf-8')
        (ws/'.gitignore').write_text('.ask/\n.DS_Store\n**/.obsidian/workspace*.json\n**/.obsidian/cache/\n.env\n.env.*\n*.pem\n*.key\n__pycache__/\n', encoding='utf-8')
    cp, ctx = _context(api, cp)
    report = _assert_valid(api, cp)
    gitops.initialize(ws)
    _install_hook(api, cp)
    result = {'state': 'setup-pending', 'workspace': str(ws), 'vault': str(ctx['vault']),
              'version': VERSION, 'validation': report['counts'], 'pending': []}
    if args.repository:
        result['remote'] = gitops.configure_remote(ws, args.repository, create=args.create_repository)
        data = _json(cp)
        config_changed = data.get('backup', {}).get('repository') != result['remote']['repository']
        data.setdefault('backup', {})['repository'] = result['remote']['repository']
        if config_changed:
            _save(cp, data)
        # Set a repository-only no-reply identity from the authenticated GitHub account.
        if not all(_git(ws, 'config', '--local', key).stdout.strip() for key in ('user.name','user.email')):
            who = subprocess.run(['gh','api','user','--jq','{login: .login, id: .id}'], capture_output=True, text=True, timeout=30)
            if who.returncode:
                raise api.AskError('cannot obtain GitHub no-reply identity; set repository-local user.name and user.email')
            user = json.loads(who.stdout)
            _git(ws, 'config', '--local', 'user.name', user['login'])
            _git(ws, 'config', '--local', 'user.email', '%s+%s@users.noreply.github.com' % (user['id'], user['login']))
        if _git(ws, 'rev-parse', '--verify', 'HEAD').returncode != 0:
            initial = ['ask.json','note.schema.json','AGENTS.md','.gitignore']
            initial += [p.relative_to(ws).as_posix() for p in ctx['vault'].rglob('*') if p.is_file()]
            result['backup'] = gitops.checkpoint(ws, initial, 'Initialize private ASK workspace', lambda: _assert_valid(api, cp, True), owner_approved=True)
        else:
            if config_changed:
                result['configuration_checkpoint'] = gitops.checkpoint(ws,['ask.json'],'Configure private ASK backup',lambda: _assert_valid(api,cp,True),owner_approved=True)
            result['backup'] = gitops.sync(ws)
        if result['backup'].get('backup_pending'):
            result['pending'].append('GitHub backup is pending; run sync when connected.')
    else:
        result['pending'].append('Connect your own PRIVATE GitHub repository with setup --repository OWNER/NAME [--create-repository].')
    if args.runtime:
        previous = runtime.inspect(cp, args.runtime)
        result['runtime'] = previous if previous.get('block_present') else runtime.connect(cp, args.runtime)
    else:
        result['pending'].append('Enroll each agent runtime with agent connect, then prove a fresh session using agent verify.')
    if args.backup == 'scheduled':
        if not args.repository:
            result['pending'].append('Scheduled backup needs a verified private GitHub repository first.')
        else:
            result['schedule'] = backup.enable(ws, Path(api.__file__).resolve(), cp)
    if result.get('runtime',{}).get('state') != 'verified':
        result['pending'].append('Runtime bootstrap verification remains pending.')
    result['readiness'] = _doctor(api, cp)['readiness']
    result['state'] = result['readiness']['state']
    result['pending'] = list(dict.fromkeys(result['pending'] + result['readiness']['pending']))
    emit(result)
    return 0 if result['state'] == 'ready' else 2


def _doctor(api, cp):
    cp, ctx = _context(api, cp)
    report, _ = validation.validate(api, cp)
    checks = {'validation': report, 'workspace': str(cp.parent), 'vault': str(ctx['vault'])}
    try:
        checks['git'] = gitops.status(cp.parent)
    except gitops.GitError as e:
        checks['git'] = {'error': str(e)}
    registry = cp.parent/'.ask/runtime.json'
    keys = _json(registry).get('runtimes', {}) if registry.exists() else {}
    checks['runtimes'] = {key: runtime.inspect(cp,key) for key in keys}
    checks['writers'] = gitops.active_writes(cp.parent)
    status = cp.parent/'.ask/backup-status.json'
    checks['backup'] = _json(status) if status.exists() else {'state':'not-scheduled-or-not-run'}
    st=checks['git']
    st['head']=_git(cp.parent,'rev-parse','--verify','HEAD').stdout.strip()
    st['remote_head']=_git(cp.parent,'rev-parse','--verify','@{u}').stdout.strip()
    readiness=setup_checks.assess(cp,st,{'runtimes':checks['runtimes']},report)
    configured_hook=_git(cp.parent,'config','--get','core.hooksPath').stdout.strip()
    if configured_hook not in (str(cp.parent/'.ask/hooks'), '.ask/hooks'):
        readiness['checks']['hook']={'ok':False,'status':'not-configured','detail':'Git is not using the ASK hook directory'}
        readiness['pending']=list(dict.fromkeys(readiness['pending']+['hook']))
        readiness['state']='setup-pending'
    checks['readiness']=readiness
    checks['state']=readiness['state']
    return checks


def _check_write_scope(api, cp, ctx, paths, approved):
    for raw in paths:
        rel = api.safe_rel(raw, 'checkpoint file')
        target = cp.parent/rel
        if target.is_dir():
            raise api.AskError('checkpoint requires individual file paths, not directories')
        if approved:
            continue
        try:
            vrel = target.relative_to(ctx['vault']).as_posix()
        except ValueError:
            raise api.AskError('workspace configuration changes require --owner-approved')
        if not any(p=='.' or vrel==p or vrel.startswith(p+'/') for p in ctx['access']['write']):
            raise api.AskError('file is outside configured access.write: %s' % raw)


def dispatch(api, argv):
    parser = argparse.ArgumentParser(prog='ask.py')
    subs = parser.add_subparsers(dest='command', required=True)
    setup = subs.add_parser('setup')
    setup.add_argument('--workspace', required=True)
    setup.add_argument('--vault-name')
    setup.add_argument('--repository')
    setup.add_argument('--create-repository', action='store_true')
    setup.add_argument('--runtime')
    setup.add_argument('--read-only', action='store_true')
    setup.add_argument('--backup', choices=('session','scheduled'), default='session')
    for cmd in ('doctor','sync','checkpoint'):
        p = subs.add_parser(cmd); p.add_argument('--config',required=True)
        p.add_argument('--json',action='store_true')
        if cmd=='checkpoint':
            p.add_argument('--files',nargs='+',required=True)
            p.add_argument('--message',required=True)
            p.add_argument('--owner-approved',action='store_true')
    p=subs.add_parser('agent'); actions=p.add_subparsers(dest='action',required=True)
    for action in ('connect','disconnect','status','verify'):
        q=actions.add_parser(action); q.add_argument('--config',required=True); q.add_argument('--runtime',required=True)
        if action=='verify': q.add_argument('--evidence',help='JSON file containing controller-observed fresh-session proof')
    p=subs.add_parser('write'); actions=p.add_subparsers(dest='action',required=True)
    for action in ('begin','end'):
        q=actions.add_parser(action); q.add_argument('--config',required=True)
        q.add_argument('--actor' if action=='begin' else '--token',required=True)
    p=subs.add_parser('backup'); actions=p.add_subparsers(dest='action',required=True)
    for action in ('enable','disable','run','status'):
        q=actions.add_parser(action); q.add_argument('--config',required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='setup': return _setup(api,args)
        cp,ctx=_context(api,args.config); ws=cp.parent
        if args.command=='doctor':
            result=_doctor(api,cp); emit(result); return 0 if result['state']=='ready' else 2
        if args.command=='agent':
            if args.action=='verify':
                result = runtime.record_verification(cp,args.runtime,_json(Path(args.evidence))) if args.evidence else {'state':'verification-required','instructions':runtime.verification_prompt(cp)}
            else:
                result=getattr(runtime,{'status':'inspect'}.get(args.action,args.action))(cp,args.runtime)
        elif args.command=='sync': result=gitops.sync(ws)
        elif args.command=='checkpoint':
            _check_write_scope(api,cp,ctx,args.files,args.owner_approved)
            result=gitops.checkpoint(ws,args.files,args.message,lambda: _assert_valid(api,cp,True),owner_approved=args.owner_approved)
        elif args.command=='write':
            result=gitops.begin_write(ws,args.actor) if args.action=='begin' else gitops.end_write(ws,args.token)
        elif args.action=='enable': result=backup.enable(ws,Path(api.__file__).resolve(),cp)
        elif args.action=='disable': result=backup.disable(ws)
        elif args.action=='run': result=backup.run(ws,lambda: _assert_valid(api,cp,True))
        else:
            path=ws/'.ask/backup-status.json'
            result=_json(path) if path.exists() else {'state':'not-run'}
        emit(result)
        return 2 if result.get('backup_pending') or result.get('state') in ('error','backup-pending','verification-required') else 0
    except (api.AskError,gitops.GitError,backup.BackupError,runtime.RuntimeError,subprocess.TimeoutExpired,OSError,ValueError,TypeError,KeyError) as e:
        emit({'state':'error','error':str(e)})
        return 2
