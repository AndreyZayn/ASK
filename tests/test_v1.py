import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'ask.py'

class V1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.ws = self.base / 'Private Knowledge'

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)

    def setup_pending(self):
        result = self.cli('setup', '--workspace', self.ws)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertTrue(result.stdout.strip(), result.stderr)
        state = json.loads(result.stdout)
        self.assertEqual(state['state'], 'setup-pending')
        self.assertTrue((self.ws / '.git').is_dir())
        return self.ws / 'ask.json'

    def test_setup_offline_preserves_usable_local_vault_and_rerun(self):
        cfg = self.setup_pending()
        note = self.ws / 'Knowledge Base' / 'goals.md'
        previous = note.read_text() if note.exists() else ''
        again = self.cli('setup', '--workspace', self.ws)
        self.assertEqual(again.returncode, 2, again.stderr)
        self.assertEqual(note.read_text() if note.exists() else '', previous)
        self.assertEqual(self.cli('validate', '--config', cfg, '--json').returncode, 0)
        self.assertTrue(json.loads(cfg.read_text())['access']['write'])

    def test_setup_refuses_foreign_existing_workspace(self):
        self.ws.mkdir()
        (self.ws / 'ask.json').write_text('{"version": 1}')
        r = self.cli('setup', '--workspace', self.ws)
        self.assertEqual(r.returncode, 2)
        self.assertFalse((self.ws / '.git').exists())

    def test_v1_orphan_fails_then_nearest_index_fixes(self):
        cfg = self.setup_pending()
        vault = self.ws / 'Knowledge Base'
        (vault / 'Projects' / 'sample.md').write_text('---\ntitle: Synthetic project fact\ndescription: Fixture\nkind: note\nscope: work\nlifecycle_status: active\nupdated: 2026-10-07\n---\n')
        r = self.cli('validate', '--config', cfg, '--json')
        self.assertEqual(r.returncode, 1, r.stdout+r.stderr)
        self.assertIn('index', r.stdout.lower())
        with (vault / 'Projects' / 'INDEX.md').open('a') as f:
            f.write('\n- [[Projects/sample]]\n')
        self.assertEqual(self.cli('validate', '--config', cfg, '--json').returncode, 0)

    def test_staged_snapshot_not_worktree_is_validated(self):
        cfg = self.setup_pending()
        subprocess.run(['git','add','.'], cwd=self.ws, check=True, capture_output=True)
        # Staged valid content, worktree invalid: hook must read index blobs.
        (self.ws / 'Knowledge Base' / 'date.md').write_text('invalid worktree')
        r = self.cli('validate', '--config', cfg, '--staged', '--json')
        self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
        subprocess.run(['git','add','Knowledge Base/date.md'], cwd=self.ws, check=True)
        r = self.cli('validate', '--config', cfg, '--staged', '--json')
        self.assertEqual(r.returncode, 1, r.stdout+r.stderr)

    def test_staged_config_never_reads_worktree_config(self):
        cfg=self.setup_pending()
        subprocess.run(['git','add','.'],cwd=self.ws,check=True,capture_output=True)
        cfg.write_text('not JSON')
        r=self.cli('validate','--config',cfg,'--staged','--json')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_staged_absolute_vault_cannot_validate_live_data(self):
        cfg=self.setup_pending()
        data=json.loads(cfg.read_text()); data['vault_root']=str(self.ws/'Knowledge Base')
        cfg.write_text(json.dumps(data))
        subprocess.run(['git','add','.'],cwd=self.ws,check=True,capture_output=True)
        r=self.cli('validate','--config',cfg,'--staged','--json')
        self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)

    def test_plain_markdown_missing_link_and_attachment(self):
        cfg = self.setup_pending()
        vault = self.ws / 'Knowledge Base'
        with (vault / 'Projects' / 'INDEX.md').open('a') as f:
            f.write('\n[Missing](missing.md)\n')
        r = self.cli('validate', '--config', cfg, '--json')
        self.assertEqual(r.returncode, 1, r.stdout+r.stderr)
        self.assertIn('missing', r.stdout.lower())

if __name__ == '__main__':
    unittest.main()
