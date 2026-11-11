import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ASK = Path(__file__).resolve().parents[1] / 'scripts' / 'ask.py'
sys.path.insert(0, str(ASK.parent))
from asklib import gitops


class VaultDiscoveryTests(unittest.TestCase):
    def test_distribution_has_no_root_agent_policy(self):
        self.assertFalse((ASK.parents[1] / 'AGENTS.md').exists())

    def test_bootstrap_keeps_selected_vault_with_another_agent_folder(self):
        for name in ('Knowledge Base', 'My Notes', 'Nested/Vault'):
            with self.subTest(vault=name), tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp).resolve() / 'ASK'
                init = subprocess.run([sys.executable, str(ASK), 'init', '--workspace',
                                       str(workspace), '--vault-name', name],
                                      capture_output=True, text=True)
                self.assertEqual(init.returncode, 0, init.stderr)
                self.assertFalse((workspace / 'AGENTS.md').exists())
                other = workspace / 'Other Project'
                other.mkdir()
                (other / 'agents.md').write_text('Project instructions', encoding='utf-8')
                result = subprocess.run([sys.executable, str(ASK), 'bootstrap', '--config',
                                         str(workspace)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(str(workspace / name), result.stdout)
                self.assertNotIn(str(other / 'date.md'), result.stdout)

    def test_another_complete_vault_does_not_change_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve() / 'ASK'
            init = subprocess.run([sys.executable, str(ASK), 'init', '--workspace',
                                   str(workspace)], capture_output=True, text=True)
            self.assertEqual(init.returncode, 0, init.stderr)
            other = workspace / 'Other Project'
            other.mkdir()
            for note in ('date.md', 'INDEX.md', 'agents.md', 'knowledge-map.md'):
                (other / note).write_text('Other knowledge base', encoding='utf-8')
            result = subprocess.run([sys.executable, str(ASK), 'bootstrap', '--config',
                                     str(workspace)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(workspace / 'Knowledge Base'), result.stdout)

            (workspace / 'Knowledge Base' / 'date.md').unlink()
            broken = subprocess.run([sys.executable, str(ASK), 'bootstrap', '--config', str(workspace)],
                                    capture_output=True, text=True)
            self.assertNotEqual(broken.returncode, 0)
            self.assertNotIn(str(other / 'date.md'), broken.stdout)

    def test_existing_root_agent_file_is_preserved_and_not_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve() / 'ASK'
            init = subprocess.run([sys.executable, str(ASK), 'init', '--workspace', str(workspace)],
                                  capture_output=True, text=True)
            self.assertEqual(init.returncode, 0, init.stderr)
            old = workspace / 'AGENTS.md'
            old.write_text('Existing owner instructions; preserve them.\n', encoding='utf-8')
            result = subprocess.run([sys.executable, str(ASK), 'bootstrap', '--config', str(workspace)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(workspace / 'Knowledge Base'), result.stdout)
            self.assertEqual(old.read_text(encoding='utf-8'), 'Existing owner instructions; preserve them.\n')

    def test_nested_vault_remains_selected_with_complete_ancestor(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve() / 'ASK'
            init = subprocess.run([sys.executable, str(ASK), 'init', '--workspace', str(workspace),
                                   '--vault-name', 'Nested/Vault'], capture_output=True, text=True)
            self.assertEqual(init.returncode, 0, init.stderr)
            for note in ('date.md', 'INDEX.md', 'agents.md', 'knowledge-map.md'):
                (workspace / 'Nested' / note).write_text('Other knowledge base', encoding='utf-8')
            result = subprocess.run([sys.executable, str(ASK), 'bootstrap', '--config', str(workspace)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(workspace / 'Nested/Vault'), result.stdout)

    def test_v110_custom_vault_uses_existing_declaration_without_modifying_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve() / 'ASK'
            init = subprocess.run([sys.executable, str(ASK), 'init', '--workspace', str(workspace),
                                   '--vault-name', 'Nested/Vault'], capture_output=True, text=True)
            self.assertEqual(init.returncode, 0, init.stderr)
            manifest_path = workspace / 'system/install-manifest.json'
            manifest = json.loads(manifest_path.read_text())
            del manifest['vault_root']
            manifest_path.write_text(json.dumps(manifest))
            old = workspace / 'AGENTS.md'
            old.write_text('The knowledge base is `Nested/Vault/` beside `system/`.\n')
            result = subprocess.run([sys.executable, str(ASK), 'bootstrap', '--config', str(workspace)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(workspace / 'Nested/Vault'), result.stdout)
            self.assertEqual(old.read_text(), 'The knowledge base is `Nested/Vault/` beside `system/`.\n')
            old.unlink()
            result = subprocess.run([sys.executable, str(ASK), 'bootstrap', '--config', str(workspace)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('needs its vault_root', result.stderr)

    def test_installed_manifest_rejects_escaping_vault_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve() / 'ASK'
            init = subprocess.run([sys.executable, str(ASK), 'init', '--workspace', str(workspace)],
                                  capture_output=True, text=True)
            self.assertEqual(init.returncode, 0, init.stderr)
            manifest_path = workspace / 'system/install-manifest.json'
            manifest = json.loads(manifest_path.read_text())
            for unsafe in ('../outside', '~', '~other/notes'):
                with self.subTest(vault=unsafe):
                    manifest['vault_root'] = unsafe
                    manifest_path.write_text(json.dumps(manifest))
                    result = subprocess.run([sys.executable, str(ASK), 'bootstrap', '--config', str(workspace)],
                                            capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('vault path is invalid', result.stderr)
                    rejected = subprocess.run([sys.executable, str(ASK), 'init', '--workspace', str(workspace.parent / 'new'),
                                               '--vault-name', unsafe], capture_output=True, text=True)
                    self.assertNotEqual(rejected.returncode, 0)

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
