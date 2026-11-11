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

from . import configuration, backup, gitops, runtime, validation, setup_checks, onboarding

VERSION = '1.1.0'
COMMANDS = {'setup', 'doctor', 'agent', 'checkpoint', 'sync', 'write', 'backup'}


def emit(value):
    print(json.dumps(value, indent=2, sort_keys=True))


def _json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _git(ws, *args):
    return subprocess.run(['git', *args], cwd=str(ws), capture_output=True, text=True, timeout=30)


def _context(api, config):
    cp = configuration.reference(config_path=config)
    ctx = api.load_config(cp)
    if ctx['vault'].resolve() == configuration.workspace(cp).resolve() or not api.inside(ctx['vault'], configuration.workspace(cp)):
        raise api.AskError('V1 vault must be a directory inside its private workspace')
    return cp, ctx


def _assert_valid(api, cp, staged=False):
    report, _ = validation.validate(api, cp, staged=staged)
    if report['counts']['errors']:
        raise api.AskError('; '.join('%s: %s' % (i['file'], i['message']) for i in report['issues'][:12]))
    return report


def _workspace_cli(api, ws):
    local = ws / 'system' / 'scripts' / 'ask.py'
    api.ensure_no_symlink_path(local)
    return local if local.is_file() else Path(api.__file__).resolve()


def _install_hook(api, cp):
    ws = configuration.workspace(cp)
    hooks = ws / '.ask' / 'hooks'
    api.ensure_no_symlink_path(hooks)
    current = _git(ws, 'config', '--local', '--get', 'core.hooksPath').stdout.strip()
    if current and Path(current) not in (hooks, Path('.ask/hooks')):
        raise api.AskError('existing core.hooksPath needs manual hook integration: %s' % current)
    default_hook = ws / '.git' / 'hooks' / 'pre-commit'
    if not current and (default_hook.exists() or default_hook.is_symlink()):
        raise api.AskError('existing pre-commit hook needs manual integration; it was preserved')
    hooks.mkdir(parents=True, exist_ok=True)
    hook = hooks / 'pre-commit'
    api.ensure_no_symlink_path(hook)
    if hook.exists() and hook.stat().st_nlink != 1:
        raise api.AskError('managed hook path is a hardlink; original files preserved')
    command = ('%s %s validate '+ ('--workspace' if cp.is_dir() else '--config') +' %s --staged --json') % tuple(shlex.quote(str(x)) for x in (sys.executable, _workspace_cli(api, ws), cp))
    content = '#!/bin/sh\n# ASK managed staged-snapshot validator\nexec '+command+'\n'
    if hook.exists() and '# ASK managed staged-snapshot validator' not in hook.read_text():
        raise api.AskError('foreign ASK hook path preserved')
    hook.write_text(content, encoding='utf-8')
    hook.chmod(0o700)
    r = _git(ws, 'config', '--local', 'core.hooksPath', str(hooks))
    if r.returncode:
        raise api.AskError(r.stderr)


def _setup_identity(api, ws):
    # Fill only missing repository-local fields; preserve the owner's choices.
    missing = [key for key in ('user.name', 'user.email')
               if not _git(ws, 'config', '--local', key).stdout.strip()]
    if not missing:
        return
    who = subprocess.run(['gh', 'api', 'user', '--jq', '{login: .login, id: .id}'],
                         capture_output=True, text=True, timeout=30)
    if who.returncode:
        raise api.AskError('cannot obtain GitHub no-reply identity; set repository-local user.name and user.email')
    user = json.loads(who.stdout)
    values = {'user.name': user['login'],
              'user.email': '%s+%s@users.noreply.github.com' % (user['id'], user['login'])}
    for key in missing:
        if _git(ws, 'config', '--local', key, values[key]).returncode:
            raise api.AskError('cannot set repository-local Git identity; configure it manually')


def _setup(api, args):
    ws = Path(args.workspace).expanduser().absolute()
    api.ensure_no_symlink_path(ws)
    legacy = ws/'ask.json'
    fresh = not (legacy.exists() or configuration.native(ws))
    if not fresh:
        cp = configuration.reference(workspace_path=ws)
        data = configuration.read(cp)
        if data.get('ask_version') != configuration.DEFAULTS['ask_version']:
            raise api.AskError('existing configuration is not a V1 installation; preserve it and follow the upgrade guide')
        if args.vault_name and args.vault_name != data.get('vault_root'):
            raise api.AskError('--vault-name differs from existing configuration; no migration was performed')
        if args.read_only and data.get('access',{}).get('write'):
            raise api.AskError('--read-only differs from existing access settings; edit settings explicitly; no overwrite was performed')
    else:
        if ws.exists() and any(ws.iterdir()):
            raise api.AskError('setup requires a new empty workspace; existing files were preserved')
        parent = ws
        while not parent.exists():
            parent = parent.parent
        if _git(parent, 'rev-parse', '--show-toplevel').returncode == 0:
            raise api.AskError('private workspace must be outside every existing repository')
        with contextlib.redirect_stdout(io.StringIO()):
            created = api.init(argparse.Namespace(workspace=str(ws), vault_name=args.vault_name, read_only=args.read_only))
        cp = ws
        data = configuration.read(cp)
        if args.read_only:
            data['access']['write'] = []
            changed = configuration.save(cp, data)
            if changed not in created:
                created.append(changed)
        (ws/'AGENTS.md').write_text(api.workspace_adapter(), encoding='utf-8')
        (ws/'.gitignore').write_text('.ask/\n.DS_Store\n**/.obsidian/workspace*.json\n**/.obsidian/cache/\n.env\n.env.*\n*.pem\n*.key\n__pycache__/\n', encoding='utf-8')
    cp, ctx = _context(api, cp)
    report = _assert_valid(api, cp)
    gitops.initialize(ws)
    _install_hook(api, cp)
    result = {'state': 'setup-pending', 'workspace': str(ws), 'vault': str(ctx['vault']),
              'version': VERSION, 'validation': report['counts'], 'pending': []}
    if fresh:
        result['initial_checkpoint_files'] = sorted(created + ['.gitignore'])
    if args.repository:
        if not fresh and _git(ws, 'rev-parse', '--verify', 'HEAD').returncode != 0:
            raise api.AskError('initial baseline is not committed; use the reviewed fresh-setup initial_checkpoint_files with checkpoint before retrying setup (see docs/install.md)')
        existing_repository = data.get('backup', {}).get('repository')
        if cp.is_dir() and existing_repository and existing_repository.casefold() != gitops._parse_slug(args.repository).casefold():
            raise api.AskError('the requested repository conflicts with existing owner settings; review them before changing the remote')
        result['remote'] = gitops.configure_remote(ws, args.repository, create=args.create_repository)
        data = configuration.read(cp)
        # Native installs use Git's verified origin as the backup binding, as
        # the private ASK does; do not recreate a settings file for defaults.
        config_changed = cp.is_file() and data.get('backup', {}).get('repository') != result['remote']['repository']
        if config_changed:
            data.setdefault('backup', {})['repository'] = result['remote']['repository']
            changed = configuration.save(cp, data)
            if fresh and changed not in result['initial_checkpoint_files']:
                result['initial_checkpoint_files'].append(changed)
        _setup_identity(api, ws)
        if _git(ws, 'rev-parse', '--verify', 'HEAD').returncode != 0:
            initial = result.get('initial_checkpoint_files')
            if initial is None:
                raise api.AskError('initial baseline is not committed; use the reviewed fresh-setup initial_checkpoint_files with checkpoint before retrying setup (see docs/install.md)')
            result['backup'] = gitops.checkpoint(ws, initial, 'Initialize private ASK workspace', lambda: _assert_valid(api, cp, True), owner_approved=True)
        else:
            if config_changed:
                result['configuration_checkpoint'] = gitops.checkpoint(ws,[cp.name],'Configure private ASK backup',lambda: _assert_valid(api,cp,True),owner_approved=True)
            result['backup'] = gitops.sync(ws)
        if result['backup'].get('backup_pending'):
            result['pending'].append('GitHub backup is pending; run sync when connected.')
    else:
        if not all(_git(ws, 'config', '--local', key).stdout.strip() for key in ('user.name', 'user.email')):
            result['pending'].append('Repository-local Git identity is missing; choose user.name and user.email before checkpointing (see docs/install.md).')
        result['pending'].append('Connect your own PRIVATE GitHub repository with setup --repository OWNER/NAME [--create-repository].')
    if args.runtime:
        previous = runtime.inspect(cp, args.runtime)
        keep_verified_manual = previous.get('state') == 'verified' and previous.get('target') is None
        result['runtime'] = previous if previous.get('block_present') or keep_verified_manual else runtime.connect(cp, args.runtime)
    else:
        result['pending'].append('Enroll each agent runtime with agent connect, then prove a fresh session using agent verify.')
    if args.backup == 'scheduled':
        if not args.repository:
            result['pending'].append('Scheduled backup needs a verified private GitHub repository first.')
        else:
            result['schedule'] = backup.enable(ws, _workspace_cli(api, ws), cp)
    if result.get('runtime',{}).get('state') != 'verified':
        result['pending'].append('Runtime bootstrap verification remains pending.')
    result['readiness'] = _doctor(api, cp)['readiness']
    result['state'] = result['readiness']['state']
    result['pending'] = list(dict.fromkeys(result['pending'] + result['readiness']['pending']))
    emit(result)
    return 0 if result['state'] == 'ready' else 2


def _doctor(api, cp):
    cp, ctx = _context(api, cp)
    ws = ctx['workspace']
    report, _ = validation.validate(api, cp)
    checks = {'validation': report, 'workspace': str(ws), 'vault': str(ctx['vault'])}
    try:
        checks['git'] = gitops.status(ws)
    except gitops.GitError as e:
        checks['git'] = {'error': str(e)}
    registry = ws/'.ask/runtime.json'
    keys = _json(registry).get('runtimes', {}) if registry.exists() else {}
    checks['runtimes'] = {key: runtime.inspect(cp,key) for key in keys}
    checks['writers'] = gitops.active_writes(ws)
    status = ws/'.ask/backup-status.json'
    checks['backup'] = _json(status) if status.exists() else {'state':'not-scheduled-or-not-run'}
    st=checks['git']
    st['head']=_git(ws,'rev-parse','--verify','HEAD').stdout.strip()
    st['remote_head']=_git(ws,'rev-parse','--verify','@{u}').stdout.strip()
    readiness=setup_checks.assess(cp,st,{'runtimes':checks['runtimes']},report)
    configured_hook=_git(ws,'config','--get','core.hooksPath').stdout.strip()
    if configured_hook not in (str(ws/'.ask/hooks'), '.ask/hooks'):
        readiness['checks']['hook']={'ok':False,'status':'not-configured','detail':'Git is not using the ASK hook directory'}
        readiness['pending']=list(dict.fromkeys(readiness['pending']+['hook']))
        readiness['state']='setup-pending'
    checks['readiness']=readiness
    checks['state']=readiness['state']
    return checks


def _check_write_scope(api, cp, ctx, paths, approved):
    for raw in paths:
        rel = api.safe_rel(raw, 'checkpoint file')
        target = configuration.workspace(cp)/rel
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
    setup.add_argument('--workspace','--root',dest='workspace', required=True)
    setup.add_argument('--vault-name')
    setup.add_argument('--repository')
    setup.add_argument('--create-repository', action='store_true')
    setup.add_argument('--runtime')
    setup.add_argument('--read-only', action='store_true')
    setup.add_argument('--backup', choices=('session','scheduled'), default='session')
    for cmd in ('doctor','sync','checkpoint'):
        p = subs.add_parser(cmd); configuration.add_selector(p)
        p.add_argument('--json',action='store_true')
        if cmd=='checkpoint':
            p.add_argument('--files',nargs='+',required=True)
            p.add_argument('--message',required=True)
            p.add_argument('--owner-approved',action='store_true')
    p=subs.add_parser('agent'); actions=p.add_subparsers(dest='action',required=True)
    for action in ('connect','disconnect','status','verify','onboarding'):
        q=actions.add_parser(action); configuration.add_selector(q); q.add_argument('--runtime',required=True)
        if action=='verify': q.add_argument('--evidence',help='JSON file containing controller-observed fresh-session proof')
        if action=='onboarding': q.add_argument('--profile',help='Sanitized caller-observed JSON; generates proposed rows without writing notes')
    p=subs.add_parser('write'); actions=p.add_subparsers(dest='action',required=True)
    for action in ('begin','end'):
        q=actions.add_parser(action); configuration.add_selector(q)
        q.add_argument('--actor' if action=='begin' else '--token',required=True)
    p=subs.add_parser('backup'); actions=p.add_subparsers(dest='action',required=True)
    for action in ('enable','disable','run','status'):
        q=actions.add_parser(action); configuration.add_selector(q)
    args=parser.parse_args(argv)
    try:
        if args.command=='setup': return _setup(api,args)
        cp,ctx=_context(api,configuration.reference(args.workspace,args.config)); ws=configuration.workspace(cp)
        if args.command=='doctor':
            result=_doctor(api,cp); emit(result); return 0 if result['state']=='ready' else 2
        if args.command=='agent':
            if args.action=='onboarding':
                result = onboarding.report(api, cp, args.runtime, args.profile)
            elif args.action=='verify':
                result = runtime.record_verification(cp,args.runtime,_json(Path(args.evidence))) if args.evidence else {'state':'verification-required','instructions':runtime.verification_prompt(cp)}
            else:
                result=getattr(runtime,{'status':'inspect'}.get(args.action,args.action))(cp,args.runtime)
        elif args.command=='sync': result=gitops.sync(ws)
        elif args.command=='checkpoint':
            _check_write_scope(api,cp,ctx,args.files,args.owner_approved)
            result=gitops.checkpoint(ws,args.files,args.message,lambda: _assert_valid(api,cp,True),owner_approved=args.owner_approved)
        elif args.command=='write':
            result=gitops.begin_write(ws,args.actor) if args.action=='begin' else gitops.end_write(ws,args.token)
        elif args.action=='enable':
            result=backup.enable(ws,_workspace_cli(api,ws),cp)
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
