"""The installed ASK folder owns its tools, vault, and artifact space."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]


class WholeWorkspaceTest(unittest.TestCase):
    def test_existing_migration_directories_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            workspace = root/'ASK'
            command = [sys.executable, str(SOURCE/'scripts/ask.py'), 'setup', '--workspace', str(workspace)]
            first = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(json.loads(first.stdout)['state'], 'setup-pending')
            for name in ('backups', 'staging'):
                (workspace/name).mkdir()
                (workspace/name/'owner-file.txt').write_text('Keep existing owner data.\n')
            second = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(json.loads(second.stdout)['state'], 'setup-pending')
            for name in ('backups', 'staging'):
                self.assertEqual((workspace/name/'owner-file.txt').read_text(), 'Keep existing owner data.\n')

    def test_legacy_install_can_rebind_using_source_without_migration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            workspace = root/'ASK'
            env = dict(os.environ, HOME=str(root/'home'), GIT_CONFIG_NOSYSTEM='1')
            (root/'home').mkdir()
            command = [sys.executable, str(SOURCE/'scripts/ask.py')]
            first = subprocess.run(command+['setup','--workspace',str(workspace)], text=True, capture_output=True, env=env)
            self.assertEqual(json.loads(first.stdout)['state'], 'setup-pending', first.stdout)
            note = workspace/'Knowledge Base/goals.md'; before = note.read_bytes()
            shutil.rmtree(workspace/'system')
            result = subprocess.run(command+['setup','--workspace',str(workspace),'--runtime','generic'], text=True, capture_output=True, env=env)
            self.assertEqual(json.loads(result.stdout)['state'], 'setup-pending', result.stdout)
            self.assertEqual(note.read_bytes(), before)
            self.assertFalse((workspace/'system').exists())
            self.assertIn(str(SOURCE/'scripts/ask.py'), (workspace/'.ask/hooks/pre-commit').read_text())

    def test_existing_install_refuses_symlinked_tool_for_hook_and_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            workspace = root / 'ASK'
            env = dict(os.environ, HOME=str(root/'home'), GIT_CONFIG_NOSYSTEM='1')
            (root/'home').mkdir()
            command = [sys.executable, str(SOURCE/'scripts/ask.py')]
            setup = subprocess.run(command + ['setup', '--workspace', str(workspace)], text=True, capture_output=True, env=env)
            self.assertEqual(json.loads(setup.stdout)['state'], 'setup-pending', setup.stdout)
            hook = workspace/'.ask/hooks/pre-commit'
            before = hook.read_bytes()
            local = workspace/'system/scripts/ask.py'
            local.unlink()
            external = root/'unrelated.py'; external.write_text('# unrelated\n')
            local.symlink_to(external)
            for args in (['setup','--workspace',str(workspace)],
                         ['agent','connect','--config',str(workspace/'ask.json'),'--runtime','generic']):
                result = subprocess.run(command + args, text=True, capture_output=True, env=env)
                self.assertEqual(result.returncode, 2)
                self.assertIn('symlink', result.stdout.lower())
            self.assertEqual(hook.read_bytes(), before)
            self.assertEqual(external.read_text(), '# unrelated\n')

    def test_manifest_covers_versioned_distribution_files(self):
        if not (SOURCE/'.git').exists():
            self.skipTest('manifest completeness requires a Git checkout')
        manifest = json.loads((SOURCE/'install-manifest.json').read_text())['files']
        tracked = subprocess.check_output(['git', 'ls-files', 'scripts', 'schemas', 'templates', 'docs', 'README.md', 'LICENSE'],
                                          cwd=SOURCE, text=True).splitlines()
        self.assertEqual(set(manifest), set(tracked))

    def test_missing_or_symlinked_manifest_asset_fails_before_workspace_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            for mode in ('missing', 'symlink'):
                source = root / ('source-' + mode)
                shutil.copytree(SOURCE, source, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc'))
                target = source/'templates/vault/agents.md'
                target.unlink()
                if mode == 'symlink':
                    target.symlink_to(root/'outside.md')
                    (root/'outside.md').write_text('unrelated data')
                workspace = root / ('ASK-' + mode)
                result = subprocess.run([sys.executable, str(source/'scripts/ask.py'), 'setup', '--workspace', str(workspace)],
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn('error', json.loads(result.stdout))
                self.assertFalse((workspace/'ask.json').exists())

    def test_vault_cannot_overlap_the_system_or_working_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            for name in ('system', 'system/nested', 'SYSTEM/nested', 'artifacts', '.git/nested', '.ask'):
                with self.subTest(name=name):
                    workspace = root / name.replace('/', '-')
                    result = subprocess.run([sys.executable, str(SOURCE/'scripts/ask.py'), 'setup',
                                             '--workspace', str(workspace), '--vault-name', name],
                                            text=True, capture_output=True)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn('reserved', result.stdout + result.stderr)
                    self.assertFalse((workspace/'ask.json').exists())

    def test_fresh_install_survives_removal_of_installer_checkout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / 'public-checkout'
            shutil.copytree(SOURCE, source, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc'))
            (source/'templates/vault/local-draft.md').write_text('Private local draft; do not distribute.\n')
            (source/'scripts/local_draft.py').write_text('# Private local draft; do not distribute.\n')
            workspace = root / 'ASK'
            env = dict(os.environ, HOME=str(root / 'home'), CODEX_HOME=str(root / 'codex'), XDG_CONFIG_HOME=str(root / 'config'), GIT_CONFIG_NOSYSTEM='1')
            (root / 'home').mkdir()
            setup = subprocess.run([sys.executable, str(source / 'scripts/ask.py'), 'setup',
                                    '--workspace', str(workspace), '--runtime', 'codex'],
                                   text=True, capture_output=True, env=env)
            self.assertEqual(setup.returncode, 2, setup.stdout + setup.stderr)
            report = json.loads(setup.stdout)
            self.assertEqual(report.get('state'), 'setup-pending', report)
            installed = workspace / 'system/scripts/ask.py'
            self.assertTrue(installed.is_file(), 'ASK must include its own executable tools')
            self.assertTrue((workspace / 'artifacts').is_dir())
            self.assertFalse((workspace / 'backups').exists())
            self.assertFalse((workspace / 'staging').exists())
            self.assertTrue((workspace / 'Knowledge Base/agents.md').is_file())
            self.assertFalse((workspace/'Knowledge Base/local-draft.md').exists())
            self.assertFalse((workspace/'system/scripts/local_draft.py').exists())
            self.assertIn('system/scripts/ask.py', report['initial_checkpoint_files'])
            self.assertNotIn(str(source), (workspace / '.ask/hooks/pre-commit').read_text())
            self.assertIn(str(installed), (workspace / '.ask/hooks/pre-commit').read_text())
            runtime_instructions = (root / 'codex/AGENTS.md').read_text()
            self.assertIn(str(installed), runtime_instructions)
            self.assertNotIn(str(source), runtime_instructions)
            shutil.rmtree(source)
            run = subprocess.run([sys.executable, str(installed), 'validate', '--config',
                                  str(workspace / 'ask.json'), '--json'], text=True, capture_output=True, env=env)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(json.loads(run.stdout)['counts']['errors'], 0)
            for key, value in [('user.name', 'Synthetic Owner'), ('user.email', 'owner@example.invalid')]:
                subprocess.run(['git', '-C', str(workspace), 'config', '--local', key, value], check=True, env=env)
            cp = subprocess.run([sys.executable, str(installed), 'checkpoint', '--config', str(workspace/'ask.json'),
                                 '--files', *report['initial_checkpoint_files'], '--message', 'Initial ASK', '--owner-approved'],
                                text=True, capture_output=True, env=env)
            self.assertEqual(cp.returncode, 2, cp.stdout + cp.stderr)
            self.assertTrue(json.loads(cp.stdout)['committed'], cp.stdout)
            self.assertTrue(json.loads(cp.stdout)['backup_pending'], cp.stdout)
            artifact = workspace / 'artifacts' / 'result.txt'
            artifact.write_text('Synthetic working output.\n')
            artifact_cp = subprocess.run([sys.executable, str(installed), 'checkpoint', '--config', str(workspace/'ask.json'),
                                          '--files', 'artifacts/result.txt', '--message', 'Save artifact', '--owner-approved'],
                                         text=True, capture_output=True, env=env)
            self.assertEqual(artifact_cp.returncode, 2, artifact_cp.stdout + artifact_cp.stderr)
            self.assertTrue(json.loads(artifact_cp.stdout)['committed'], artifact_cp.stdout)
            tracked = subprocess.check_output(['git', '-C', str(workspace), 'show', 'HEAD:artifacts/result.txt'], text=True, env=env)
            self.assertEqual(tracked, 'Synthetic working output.\n')


if __name__ == '__main__':
    unittest.main()
