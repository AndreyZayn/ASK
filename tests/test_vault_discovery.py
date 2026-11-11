import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ASK = Path(__file__).resolve().parents[1] / 'scripts' / 'ask.py'
sys.path.insert(0, str(ASK.parent))
from asklib import gitops


class VaultDiscoveryTests(unittest.TestCase):
    def test_bootstrap_keeps_selected_vault_with_another_agent_folder(self):
        for name in ('Knowledge Base', 'My Notes', 'Nested/Vault'):
            with self.subTest(vault=name), tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp).resolve() / 'ASK'
                init = subprocess.run([sys.executable, str(ASK), 'init', '--workspace',
                                       str(workspace), '--vault-name', name],
                                      capture_output=True, text=True)
                self.assertEqual(init.returncode, 0, init.stderr)
                other = workspace / 'Other Project'
                other.mkdir()
                (other / 'agents.md').write_text('Project instructions', encoding='utf-8')
                result = subprocess.run([sys.executable, str(ASK), 'bootstrap', '--config',
                                         str(workspace)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(str(workspace / name), result.stdout)
                self.assertNotIn(str(other / 'date.md'), result.stdout)

    def test_missing_vault_declaration_fails_closed_when_ambiguous(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve() / 'ASK'
            init = subprocess.run([sys.executable, str(ASK), 'init', '--workspace',
                                   str(workspace)], capture_output=True, text=True)
            self.assertEqual(init.returncode, 0, init.stderr)
            other = workspace / 'Other Project'
            other.mkdir()
            (other / 'agents.md').write_text('Project instructions', encoding='utf-8')
            (workspace / 'AGENTS.md').write_text('Custom instructions', encoding='utf-8')
            result = subprocess.run([sys.executable, str(ASK), 'bootstrap', '--config',
                                     str(workspace)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('must identify its knowledge base', result.stderr)

    def test_system_files_are_protected_even_with_different_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(gitops.is_protected(tmp, 'system/scripts/note_schema.py'))
            self.assertTrue(gitops.is_protected(tmp, 'System/scripts/ask.py'))

    def test_restored_workspace_remains_read_only_when_setup_is_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve() / 'ASK'
            setup = [sys.executable, str(ASK), 'setup', '--workspace', str(workspace)]
            first = subprocess.run(setup + ['--read-only'], capture_output=True, text=True)
            self.assertEqual(first.returncode, 2, first.stderr)
            self.assertTrue((workspace / 'system/install-manifest.json').is_file())
            subprocess.run(['git', '-C', str(workspace), 'config', '--local', '--unset',
                            'ask.readOnly'], check=True, capture_output=True)
            again = subprocess.run(setup, capture_output=True, text=True)
            self.assertEqual(again.returncode, 2, again.stderr)
            value = subprocess.run(['git', '-C', str(workspace), 'config', '--local', '--get',
                                    'ask.readOnly'], check=True, capture_output=True, text=True)
            self.assertEqual(value.stdout.strip(), 'true')
            self.assertEqual(gitops.read_config(workspace)['access']['write'], [])


if __name__ == '__main__':
    unittest.main()
