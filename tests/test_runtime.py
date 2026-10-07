import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from asklib import runtime as rt


def init_workspace(base, name='ws'):
    ws = base / name
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'ask.py'),
                        'init', '--workspace', str(ws)],
                       text=True, capture_output=True)
    assert r.returncode == 0, r.stderr
    return ws


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / 'fakehome'
        self.home.mkdir()
        self.ws = init_workspace(self.base)
        self.config = self.ws / 'ask.json'

    def tearDown(self):
        self.tmp.cleanup()

    def test_reconnect_is_byte_idempotent(self):
        rt.connect(self.config,'claude',home=self.home)
        target=self.home/'.claude/CLAUDE.md'
        initial=target.read_bytes()
        rt.connect(self.config,'claude',home=self.home)
        self.assertEqual(initial,target.read_bytes())

    def test_registry_symlink_refused(self):
        (self.ws/'.ask').symlink_to(self.home, target_is_directory=True)
        with self.assertRaises(rt.RuntimeError):
            rt.connect(self.config,'claude',home=self.home)
        self.assertFalse((self.home/'runtime.json').exists())

    def test_missing_block_invalidates_verification(self):
        rt.connect(self.config,'claude',home=self.home)
        path=self.ws/'.ask/runtime.json'
        reg=json.loads(path.read_text()); reg['runtimes']['claude']['state']='verified'
        path.write_text(json.dumps(reg))
        (self.home/'.claude/CLAUDE.md').write_text('foreign only')
        self.assertNotEqual(rt.inspect(self.config,'claude',home=self.home)['state'],'verified')

    def test_error_type(self):
        self.assertTrue(issubclass(rt.RuntimeError, Exception))

    def test_connect_claude_fake_home(self):
        res = rt.connect(self.config, 'claude', home=self.home)
        target = self.home / '.claude' / 'CLAUDE.md'
        self.assertEqual(res['state'], 'configured-unverified')
        self.assertTrue(target.is_file())
        text = target.read_text(encoding='utf-8')
        self.assertIn(str(self.ws.resolve()), text)
        self.assertIn(str(self.config.resolve()), text)
        self.assertIn('scripts/ask.py', text)
        self.assertIn('validate', text)
        order = ['date.md', 'INDEX.md', 'agents.md', 'knowledge-map.md']
        idx = [text.index(x) for x in order]
        self.assertEqual(idx, sorted(idx))
        reg = json.loads((self.ws / '.ask' / 'runtime.json').read_text(encoding='utf-8'))
        self.assertIn('claude', reg['runtimes'])

    def test_connect_honors_claude_config_dir(self):
        cfgdir = self.base / 'claude-env'
        env = dict(os.environ)
        env['CLAUDE_CONFIG_DIR'] = str(cfgdir)
        old = os.environ.get('CLAUDE_CONFIG_DIR')
        os.environ['CLAUDE_CONFIG_DIR'] = str(cfgdir)
        try:
            rt.connect(self.config, 'claude')
        finally:
            if old is None:
                del os.environ['CLAUDE_CONFIG_DIR']
            else:
                os.environ['CLAUDE_CONFIG_DIR'] = old
        self.assertTrue((cfgdir / 'CLAUDE.md').is_file())

    def test_connect_honors_codex_home(self):
        codedir = self.base / 'codex-env'
        old = os.environ.get('CODEX_HOME')
        os.environ['CODEX_HOME'] = str(codedir)
        try:
            rt.connect(self.config, 'codex')
        finally:
            if old is None:
                del os.environ['CODEX_HOME']
            else:
                os.environ['CODEX_HOME'] = old
        self.assertTrue((codedir / 'AGENTS.md').is_file())

    def test_connect_preserves_foreign_and_idempotent(self):
        target = self.home / '.claude' / 'CLAUDE.md'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('# mine\nforeign-body\n', encoding='utf-8')
        rt.connect(self.config, 'claude', home=self.home)
        first = target.read_text(encoding='utf-8')
        self.assertIn('foreign-body', first)
        rt.connect(self.config, 'claude', home=self.home)
        second = target.read_text(encoding='utf-8')
        self.assertIn('foreign-body', second)
        self.assertEqual(second.count('ASK-MANAGED-START'), 1)

    def test_block_instructions(self):
        rt.connect(self.config, 'claude', home=self.home)
        text = (self.home / '.claude' / 'CLAUDE.md').read_text(encoding='utf-8')
        lowered = text.lower()
        self.assertIn('knowledge-map', lowered)
        self.assertIn('continu', lowered)
        self.assertIn('skip', lowered)
        self.assertIn('step', lowered)

    def test_multiple_workspaces_coexist(self):
        ws2 = init_workspace(self.base, name='ws2 space')
        rt.connect(self.config, 'claude', home=self.home)
        rt.connect(ws2 / 'ask.json', 'claude', home=self.home)
        text = (self.home / '.claude' / 'CLAUDE.md').read_text(encoding='utf-8')
        self.assertEqual(text.count('ASK-MANAGED-START'), 2)
        rt.disconnect(self.config, 'claude', home=self.home)
        text2 = (self.home / '.claude' / 'CLAUDE.md').read_text(encoding='utf-8')
        self.assertEqual(text2.count('ASK-MANAGED-START'), 1)
        self.assertIn('ws2 space', text2)

    def test_disconnect_recomputes_target(self):
        rt.connect(self.config, 'claude', home=self.home)
        reg = self.ws / '.ask' / 'runtime.json'
        data = json.loads(reg.read_text(encoding='utf-8'))
        data['runtimes']['claude']['target'] = str(self.base / 'evil.md')
        reg.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaises(rt.RuntimeError):
            rt.disconnect(self.config, 'claude', home=self.home)
        self.assertFalse((self.base / 'evil.md').exists())
        self.assertTrue((self.home / '.claude' / 'CLAUDE.md').is_file())

    def test_corrupt_markers_fail_safe(self):
        ws = str(self.ws.resolve())
        target = self.home / '.claude' / 'CLAUDE.md'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('<!-- ASK-MANAGED-START %s -->\norphan\n' % ws, encoding='utf-8')
        with self.assertRaises(rt.RuntimeError):
            rt.connect(self.config, 'claude', home=self.home)
        self.assertIn('orphan', target.read_text(encoding='utf-8'))

    def test_foreign_orphan_block_preserved(self):
        target = self.home / '.claude' / 'CLAUDE.md'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('<!-- ASK-MANAGED-START /other-ws -->\norphan\n', encoding='utf-8')
        rt.connect(self.config, 'claude', home=self.home)
        text = target.read_text(encoding='utf-8')
        self.assertIn('orphan', text)
        self.assertIn('ASK-MANAGED-START %s' % str(self.ws.resolve()), text)

    def test_rejects_symlink_config(self):
        link = self.base / 'cfg-link.json'
        try:
            link.symlink_to(self.config)
        except OSError:
            self.skipTest('symlinks unavailable')
        with self.assertRaises(rt.RuntimeError):
            rt.connect(link, 'claude', home=self.home)

    def test_requires_four_bootstrap_files(self):
        (self.ws / 'Knowledge Base' / 'date.md').unlink()
        with self.assertRaises(rt.RuntimeError):
            rt.connect(self.config, 'claude', home=self.home)

    def test_generic_runtime_manual_no_writes(self):
        res = rt.connect(self.config, 'cursor', home=self.home)
        self.assertEqual(res['state'], 'manual')
        self.assertIn('manual', res.get('instructions', '').lower())
        self.assertFalse((self.home / '.claude' / 'CLAUDE.md').exists())

    def test_inspect_unverified_until_proof(self):
        rt.connect(self.config, 'claude', home=self.home)
        info = rt.inspect(self.config, 'claude', home=self.home)
        self.assertEqual(info['state'], 'configured-unverified')
        prompt = rt.verification_prompt(self.config)
        self.assertIn('date.md', prompt)
        info2 = rt.inspect(self.config, 'claude', home=self.home)
        self.assertEqual(info2['state'], 'configured-unverified')

    def test_verification_prompt_names_scratch(self):
        prompt = rt.verification_prompt(self.config)
        lowered = prompt.lower()
        self.assertIn('unrelated', lowered)
        self.assertIn('sentinel', lowered)
        self.assertIn('.md', prompt)

    def test_record_verification(self):
        with self.assertRaises(rt.RuntimeError):
            rt.record_verification(self.config, 'claude', {'note': 'x'})
        rt.connect(self.config, 'claude', home=self.home)
        with self.assertRaises(rt.RuntimeError):
            rt.record_verification(self.config, 'claude', {})
        res = rt.record_verification(self.config, 'claude', {'bootstrap_files': rt.BOOTSTRAP_ORDER, 'inside_session': {'session_id':'one','observed_phrase':'synthetic'}, 'outside_session':{'session_id':'two','observed_phrase':'synthetic'}}, home=self.home)
        self.assertEqual(res['state'], 'verified')
        info = rt.inspect(self.config, 'claude', home=self.home)
        self.assertEqual(info['state'], 'verified')

    def test_workspace_with_spaces(self):
        ws = init_workspace(self.base, name='my ws')
        res = rt.connect(ws / 'ask.json', 'codex', home=self.home)
        self.assertEqual(res['state'], 'configured-unverified')
        self.assertTrue((self.home / '.codex' / 'AGENTS.md').is_file())


if __name__ == '__main__':
    unittest.main()
