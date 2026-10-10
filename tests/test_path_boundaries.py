"""Synthetic regression tests for staged validation and hook path boundaries."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ask
from asklib import v1, validation


class PathBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.ws = self.base / 'workspace'
        result = subprocess.run(
            [sys.executable, str(ROOT / 'scripts/ask.py'), 'init',
             '--workspace', str(self.ws)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.config = self.ws / 'ask.json'
        self.git('init')

    def git(self, *args):
        result = subprocess.run(['git', *args], cwd=self.ws,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_staged_home_vault_cannot_replace_index_snapshot(self):
        home = self.base / 'home'
        home.mkdir()
        shutil.copytree(self.ws / 'Knowledge Base', home / 'clean-vault')
        indexed_vault = self.ws / '~' / 'clean-vault'
        shutil.copytree(self.ws / 'Knowledge Base', indexed_vault)
        (indexed_vault / 'date.md').write_text('Invalid staged note\n', encoding='utf-8')
        cfg = json.loads(self.config.read_text(encoding='utf-8'))
        for root in ('~/clean-vault', './~/clean-vault'):
            with self.subTest(vault_root=root):
                cfg['vault_root'] = root
                self.config.write_text(json.dumps(cfg), encoding='utf-8')
                self.git('add', '-A')
                with mock.patch.dict(os.environ, {'HOME': str(home)}):
                    report, _ = validation.validate(ask, self.config, staged=True)
                self.assertGreater(report['counts']['errors'], 0, report)
                self.assertIn('staged vault_root', str(report['issues']))

    def test_staged_named_home_fails_without_expanding_user(self):
        cfg = json.loads(self.config.read_text(encoding='utf-8'))
        cfg['vault_root'] = '~synthetic-review-user/vault'
        self.config.write_text(json.dumps(cfg), encoding='utf-8')
        self.git('add', '-A')
        report, _ = validation.validate(ask, self.config, staged=True)
        self.assertGreater(report['counts']['errors'], 0, report)
        self.assertIn('staged vault_root', str(report['issues']))

    def test_managed_hook_symlink_preserves_external_file_and_mode(self):
        hooks = self.ws / '.ask/hooks'
        hooks.mkdir(parents=True)
        outside = self.base / 'external-hook'
        original = '# ASK managed staged-snapshot validator\n# Keep this file\n'
        outside.write_text(original, encoding='utf-8')
        outside.chmod(0o640)
        (hooks / 'pre-commit').symlink_to(outside)
        with self.assertRaises(ask.AskError):
            v1._install_hook(ask, self.config)
        self.assertEqual(outside.read_text(encoding='utf-8'), original)
        self.assertEqual(outside.stat().st_mode & 0o777, 0o640)
        self.assertTrue((hooks / 'pre-commit').is_symlink())

    def test_dangling_managed_hook_does_not_create_external_file(self):
        hooks = self.ws / '.ask/hooks'
        hooks.mkdir(parents=True)
        outside = self.base / 'not-created'
        (hooks / 'pre-commit').symlink_to(outside)
        with self.assertRaises(ask.AskError):
            v1._install_hook(ask, self.config)
        self.assertFalse(outside.exists())
        self.assertTrue((hooks / 'pre-commit').is_symlink())

    def test_dangling_default_hook_is_preserved_without_rebinding(self):
        hooks = self.ws / '.git/hooks'
        hooks.mkdir(parents=True, exist_ok=True)
        hook = hooks / 'pre-commit'
        hook.symlink_to(self.base / 'owner-hook-not-mounted')
        with self.assertRaises(ask.AskError):
            v1._install_hook(ask, self.config)
        self.assertTrue(hook.is_symlink())
        result = subprocess.run(['git', 'config', '--local', '--get', 'core.hooksPath'],
                                cwd=self.ws, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.ws / '.ask/hooks/pre-commit').exists())


if __name__ == '__main__':
    unittest.main()
