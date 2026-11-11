"""Native installations use Python rules and no configuration JSON fixtures."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.ws = self.base/'workspace'
        self.script = ROOT/'scripts/ask.py'
        self.env = dict(os.environ, HOME=str(self.base/'home'), GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        (self.base/'home').mkdir()

    def cli(self, *args):
        return subprocess.run([sys.executable, str(self.script), *map(str,args)], capture_output=True, text=True, env=self.env)

    def setup_workspace(self, *args):
        result = self.cli('setup', '--workspace', self.ws, *args)
        self.assertEqual(result.returncode, 2, result.stdout+result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['state'], 'setup-pending', data)
        return data

    def git(self, *args, expected=0):
        result = subprocess.run(['git','-C',str(self.ws),*args], capture_output=True,text=True,env=self.env)
        self.assertEqual(result.returncode, expected, result.stdout+result.stderr)
        return result

    def test_native_backup_readiness_verifies_git_origin_privacy(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        sys.path.insert(0, str(ROOT/'scripts'))
        from asklib import setup_checks
        self.setup_workspace()
        sha = 'a' * 40
        git_status = {'origin':'https://github.com/synthetic/private-notes.git',
                      'upstream':'origin/main', 'head':sha, 'remote_head':sha,
                      'ahead':0, 'behind':0, 'clean':True}
        valid = {'counts':{'errors':0,'notes':1},'issues':[]}
        for private in (True, False):
            response = SimpleNamespace(returncode=0, stdout=json.dumps({'nameWithOwner':'synthetic/private-notes','isPrivate':private}))
            remote = SimpleNamespace(returncode=0, stdout=json.dumps({'object':{'sha':sha}}))
            with patch.object(setup_checks.subprocess, 'run', side_effect=[response, remote]):
                result = setup_checks.assess(self.ws, git_status, {'runtimes':{}}, valid)
            self.assertEqual(result['checks']['backup']['ok'], private, result)
        self.assertFalse((self.ws/'system/settings.ini').exists())

    def test_fresh_defaults_bootstrap_validation_and_onboarding(self):
        result = self.setup_workspace()
        self.assertEqual(result['version'], '1.1.0')
        self.assertFalse((self.ws/'ask.json').exists())
        self.assertFalse((self.ws/'note.schema.json').exists())
        self.assertFalse((self.ws/'system/settings.ini').exists())
        self.assertFalse(list((self.ws/'system').rglob('note.schema.json')))
        self.assertTrue((self.ws/'system/scripts/asklib/schema.py').is_file())
        self.assertTrue((self.ws/'Knowledge Base/frontmatter-schema.md').is_file())
        instructions = (self.ws/'AGENTS.md').read_text()
        self.assertNotIn(str(self.ws), instructions)
        self.assertIn('system/scripts/ask.py', instructions)
        self.assertIn('Knowledge Base', instructions)
        for command in [('validate','--json'), ('bootstrap',), ('graph',), ('agent','onboarding','--runtime','generic')]:
            result = self.cli(*command,'--workspace',self.ws)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        note = self.ws/'Knowledge Base/goals.md'
        note.write_text(note.read_text().replace('scope: shared','scope: invalid'))
        result = self.cli('validate','--root',self.ws,'--json')
        self.assertEqual(result.returncode, 1, result.stdout+result.stderr)

    def test_removed_installer_rerun_and_offline_staged_checkpoint(self):
        source = self.base/'installer'
        shutil.copytree(ROOT,source,ignore=shutil.ignore_patterns('.git','__pycache__'))
        self.assertFalse((source/'schemas/note.schema.json').exists())
        self.script = source/'scripts/ask.py'
        data = self.setup_workspace()
        shutil.rmtree(source)
        self.script = self.ws/'system/scripts/ask.py'
        self.setup_workspace()
        for key,value in [('user.name','Synthetic Owner'),('user.email','owner@example.invalid'),('commit.gpgsign','false')]:
            self.git('config','--local',key,value)
        result = self.cli('checkpoint','--workspace',self.ws,'--files',*data['initial_checkpoint_files'],'--message','Initial synthetic workspace','--owner-approved')
        report = json.loads(result.stdout)
        self.assertTrue(report.get('committed'),report)
        self.assertTrue(report.get('backup_pending'),report)
        note = self.ws/'Knowledge Base/goals.md'; good = note.read_text()
        note.write_text('broken\n'); self.git('add','Knowledge Base/goals.md'); note.write_text(good)
        result = self.git('commit','-m','Reject invalid staged note',expected=1)
        self.assertIn('frontmatter',result.stdout+result.stderr)
        self.git('add','Knowledge Base/goals.md')
        note.write_text('broken worktree only\n')
        result = self.cli('validate','--workspace',self.ws,'--staged','--json')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_custom_settings_preserved_and_conflicting_legacy_fails_closed(self):
        self.setup_workspace('--vault-name','Notes','--read-only')
        settings = self.ws/'system/settings.ini'; before=settings.read_bytes()
        self.setup_workspace()
        self.assertEqual(settings.read_bytes(),before)
        result=self.cli('bootstrap','--workspace',self.ws)
        self.assertIn(str(self.ws/'Notes'),result.stdout)
        (self.ws/'ask.json').write_text('{"version": 1}')
        result=self.cli('validate','--workspace',self.ws,'--json')
        self.assertEqual(result.returncode,2)
        self.assertIn('ambiguous',result.stdout.lower())
        self.assertEqual(settings.read_bytes(),before)

    def test_native_settings_escape_and_symlink_rejected(self):
        self.setup_workspace()
        settings=self.ws/'system/settings.ini'
        settings.write_text('[workspace]\nvault_root = ../outside\n')
        result=self.cli('validate','--workspace',self.ws,'--json')
        self.assertEqual(result.returncode,2)
        settings.unlink(); settings.symlink_to(self.ws/'AGENTS.md')
        result=self.cli('validate','--workspace',self.ws,'--json')
        self.assertEqual(result.returncode,2)
        self.assertIn('symlink',result.stdout.lower())

    def test_staged_python_rules_and_settings_are_data_from_index(self):
        self.setup_workspace()
        self.git('add','-A')
        schema=self.ws/'system/scripts/asklib/schema.py'
        original=schema.read_text()
        # This untrusted code must never run, even in a staged rules file.
        marker=self.ws/'should-not-exist'
        schema.write_text(original+'\nraise RuntimeError("do not execute staged code")\n')
        self.git('add','system/scripts/asklib/schema.py')
        schema.write_text('SCHEMA = {"type": "unsupported"}\n')
        result=self.cli('validate','--workspace',self.ws,'--staged','--json')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertFalse(marker.exists())
        self.git('add','system/scripts/asklib/schema.py')
        schema.write_text(original)
        result=self.cli('validate','--workspace',self.ws,'--staged','--json')
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.git('add','system/scripts/asklib/schema.py')
        settings=self.ws/'system/settings.ini'
        settings.write_text('[workspace]\nvault_root = ../outside\n')
        self.git('add','system/settings.ini')
        settings.write_text('[workspace]\nvault_root = Knowledge Base\n')
        result=self.cli('validate','--workspace',self.ws,'--staged','--json')
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertIn('relative directory',result.stdout)
        self.git('add','system/settings.ini')
        settings.write_text('[workspace]\nvault_root = ../outside\n')
        result=self.cli('validate','--workspace',self.ws,'--staged','--json')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_native_runtime_proof_and_backup_selector(self):
        from unittest.mock import patch
        sys.path.insert(0,str(ROOT/'scripts'))
        from asklib import runtime, backup, configuration, gitops
        self.setup_workspace()
        home=self.base/'synthetic-runtime'; home.mkdir()
        foreign=home/'.codex/AGENTS.md'; foreign.parent.mkdir()
        foreign.write_text('Existing owner instructions.\n')
        result=runtime.connect(self.ws,'codex',home=home)
        self.assertEqual(result['state'],'configured-unverified')
        text=foreign.read_text()
        self.assertIn('Existing owner instructions.',text)
        self.assertIn('--workspace',text)
        self.assertNotIn('ask.json',text)
        proof={'bootstrap_files':configuration.BOOTSTRAP,
               'inside_session':{'session_id':'synthetic-inside','observed_phrase':'fixture'},
               'outside_session':{'session_id':'synthetic-outside','observed_phrase':'fixture'}}
        runtime.record_verification(self.ws,'codex',proof,home=home)
        self.assertEqual(runtime.inspect(self.ws,'codex',home=home)['state'],'verified')
        (self.ws/'system/settings.ini').write_text('[access]\nwrite =\n')
        self.assertNotEqual(runtime.inspect(self.ws,'codex',home=home)['state'],'verified')
        with patch.object(gitops,'status',return_value={}):
            report=backup._run_locked(self.ws,lambda:None,0)
        self.assertEqual(report['state'],'skipped:access',report)
        self.assertTrue(gitops.is_protected(self.ws,'system/settings.ini'))
        self.assertTrue(gitops.is_protected(self.ws,'system/scripts/asklib/schema.py'))
        import plistlib
        plist=self.base/'synthetic-backup.plist'
        with patch.object(backup,'_plist_path',return_value=plist), patch.object(backup,'_launchctl'), patch.object(backup.shutil,'which',return_value='/usr/bin/true'):
            backup.enable(self.ws,self.ws/'system/scripts/ask.py',self.ws)
        self.assertEqual(plistlib.loads(plist.read_bytes())['ProgramArguments'][-2:],['--workspace',str(self.ws)])

    def test_explicit_legacy_custom_rules_and_settings_are_preserved(self):
        from legacy_fixture import legacy_workspace
        self.setup_workspace('--vault-name','Custom Notes')
        legacy_workspace(self.ws,setup=True)
        cp=self.ws/'ask.json'; cfg=json.loads(cp.read_text())
        cfg['access']['write']=['Projects']; cfg['owner_extension']={'keep':'unchanged'}
        cfg['schema_path']='custom.schema.json'
        (self.ws/'note.schema.json').rename(self.ws/'custom.schema.json')
        schema=self.ws/'custom.schema.json'; data=json.loads(schema.read_text())
        data['properties']['owner_field']={'type':'string'}
        schema.write_text(json.dumps(data)); cp.write_text(json.dumps(cfg))
        note=self.ws/'Custom Notes/goals.md'; note.write_text(note.read_text().replace('title:', 'owner_field: preserved\ntitle:',1))
        before={p:p.read_bytes() for p in (cp,schema,note)}
        self.setup_workspace()
        result=self.cli('validate','--config',cp,'--json')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        result=self.cli('validate','--workspace',self.ws,'--json')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        for p,value in before.items(): self.assertEqual(p.read_bytes(),value)
        self.assertFalse((self.ws/'note.schema.json').exists())

    def test_missing_native_system_and_conflicting_setup_preserve_notes(self):
        self.setup_workspace()
        note=self.ws/'Knowledge Base/goals.md'; before=note.read_bytes()
        result=self.cli('setup','--workspace',self.ws,'--vault-name','Other')
        self.assertEqual(json.loads(result.stdout)['state'],'error')
        self.assertIn('no migration',result.stdout)
        shutil.rmtree(self.ws/'system')
        result=self.cli('setup','--workspace',self.ws)
        self.assertEqual(json.loads(result.stdout)['state'],'error')
        self.assertEqual(note.read_bytes(),before)
        self.assertFalse((self.ws/'ask.json').exists())

    def test_repository_binding_uses_git_remote_without_creating_settings(self):
        import argparse
        import contextlib
        import io
        from unittest.mock import patch
        sys.path.insert(0,str(ROOT/'scripts'))
        import ask
        from asklib import v1, gitops, configuration
        args=argparse.Namespace(workspace=str(self.ws),vault_name=None,read_only=False,
                                repository='synthetic/private-notes',create_repository=False,
                                runtime=None,backup='session')
        def identity(api, ws):
            for key,value in [('user.name','Synthetic Owner'),('user.email','owner@example.invalid'),('commit.gpgsign','false')]:
                self.git('config','--local',key,value)
        def bind(ws, repository, create=False):
            self.git('remote', 'add', 'origin', 'https://github.com/%s.git' % repository)
            return {'repository': repository, 'visibility': 'PRIVATE'}
        out=io.StringIO()
        with patch.dict(os.environ,self.env), patch.object(gitops,'configure_remote',side_effect=bind) as remote, patch.object(gitops,'_push',return_value={'pushed':False,'backup_pending':True,'reason':'offline'}), patch.object(v1,'_setup_identity',side_effect=identity), contextlib.redirect_stdout(out):
            code=v1._setup(ask,args)
        self.assertEqual(code,2)
        remote.assert_called_once_with(self.ws,args.repository,create=False)
        result=json.loads(out.getvalue())
        self.assertTrue(result['backup']['committed'],result)
        self.assertNotIn('system/settings.ini',result['initial_checkpoint_files'])
        self.assertFalse((self.ws/'system/settings.ini').exists())
        self.assertEqual(self.git('remote','get-url','origin').stdout.strip(), 'https://github.com/synthetic/private-notes.git')
        self.assertFalse((self.ws/'ask.json').exists())
        # A rejected privacy check must not write a repository binding.
        args.repository='synthetic/public-notes'
        before=self.git('remote','get-url','origin').stdout
        with patch.dict(os.environ,self.env), patch.object(gitops,'configure_remote',side_effect=gitops.GitError('repository is public')):
            with self.assertRaisesRegex(gitops.GitError,'public'):
                v1._setup(ask,args)
        self.assertEqual(self.git('remote','get-url','origin').stdout,before)
        self.assertFalse((self.ws/'system/settings.ini').exists())

    def test_staged_manifest_ignores_worktree_and_requires_index_marker(self):
        self.setup_workspace()
        self.git('add','-A')
        marker=self.ws/'system/install-manifest.json'; original=marker.read_text()
        marker.write_text('invalid worktree manifest\n')
        result=self.cli('validate','--workspace',self.ws,'--staged','--json')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        marker.write_text(original)
        self.git('rm','--cached','system/install-manifest.json')
        result=self.cli('validate','--workspace',self.ws,'--staged','--json')
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertIn('marker',result.stdout)

    def test_staged_legacy_workspace_uses_index_even_without_worktree_config(self):
        from legacy_fixture import legacy_workspace
        self.setup_workspace()
        legacy_workspace(self.ws,setup=True)
        self.git('add','-A')
        cp=self.ws/'ask.json'; cp.unlink()
        for selector,value in [('--workspace',self.ws),('--config',cp)]:
            result=self.cli('validate',selector,value,'--staged','--json')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
