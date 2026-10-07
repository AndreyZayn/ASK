"""Staged + advanced validation wrapper tests (synthetic temp Git repos only)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import ask as askapi
from asklib import validation as vmod


def cli_init(ws):
    r = subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'ask.py'),
         'init', '--workspace', str(ws)],
        text=True, capture_output=True)
    assert r.returncode == 0, r.stderr
    return ws / 'ask.json'


def git(ws, *args):
    r = subprocess.run(
        ['git', *args], cwd=str(ws),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert r.returncode == 0, 'git %s: %s' % (args, r.stderr)
    return r


def git_repo(ws, commit=True):
    git(ws, 'init')
    git(ws, 'config', 'user.email', 't@t.t')
    git(ws, 'config', 'user.name', 't')
    git(ws, 'config', 'commit.gpgsign', 'false')
    git(ws, 'add', '-A')
    if commit:
        git(ws, 'commit', '-m', 'init', '--no-gpg-sign')


VALID_FM = (
    "---\ntitle: {title}\ndescription: D {title}\nkind: note\n"
    "scope: shared\nlifecycle_status: active\nupdated: 2026-10-05\n---\n"
)


def write_note(vault, rel, title, body=""):
    p = vault / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(VALID_FM.format(title=title) + body, encoding='utf-8')
    return p


class StagedValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.ws = self.base / 'ws'
        self.config = cli_init(self.ws)
        self.vault = self.ws / 'Knowledge Base'

    def tearDown(self):
        self.tmp.cleanup()

    def validate(self, staged=False, files=None):
        return vmod.validate(askapi, Path(self.config), staged=staged, files=files)

    def test_baseline_valid(self):
        report, graph = self.validate()
        self.assertEqual(report['counts']['errors'], 0, report['issues'])

    def test_markdown_inline_link_ok_and_graph_edge(self):
        write_note(self.vault, 'Projects/a.md', 'AlphaOne',
                   'See [bee](b.md).\n')
        write_note(self.vault, 'Projects/b.md', 'BeeOne', 'Hello.\n')
        git_repo(self.ws)
        report, graph = self.validate()
        self.assertEqual(report['counts']['errors'], 0, report['issues'])
        edges = {(e['source'], e['target']) for e in graph['edges']}
        self.assertIn(('Projects/a.md', 'Projects/b.md'), edges)

    def test_markdown_escaping_and_absolute_fail(self):
        write_note(self.vault, 'Projects/a.md', 'AlphaTwo',
                   'Bad [x](../escape.md) and [y](/absolute.md).\n')
        report, _ = self.validate()
        self.assertGreater(report['counts']['errors'], 0)

    def test_markdown_symlink_target_fails(self):
        target = self.vault / 'Projects' / 'real.md'
        write_note(self.vault, 'Projects/real.md', 'RealNote', 'Hi.\n')
        link = self.vault / 'Projects' / 'link.md'
        try:
            if link.exists() or link.is_symlink():
                link.unlink()
            os.symlink('real.md', link)
        except OSError as e:
            self.skipTest('symlink unavailable: %s' % e)
        write_note(self.vault, 'Projects/a.md', 'AlphaThree',
                   'See [s](link.md).\n')
        report, _ = self.validate()
        self.assertGreater(report['counts']['errors'], 0)

    def test_files_filter_cannot_hide_errors(self):
        write_note(self.vault, 'Projects/broken.md', 'BrokenNote',
                   'Missing [gone](definitely-gone-xyz.md).\n')
        ok = self.vault / 'Projects' / 'ok.md'
        write_note(self.vault, 'Projects/ok.md', 'OkNote', 'Fine.\n')
        report, _ = self.validate(files=[str(ok)])
        self.assertGreater(report['counts']['errors'], 0)

    def test_staged_valid_passes_when_worktree_invalid(self):
        write_note(self.vault, 'Projects/a.md', 'StageAlpha',
                   'See [b](b.md).\n')
        write_note(self.vault, 'Projects/b.md', 'StageBee', 'Hi.\n')
        git_repo(self.ws)
        # Break worktree only (no git add): staged content stays valid.
        bad = self.vault / 'Projects' / 'b.md'
        bad.write_text(VALID_FM.format(title='StageBee') + '[gone](gone-xyz.md)\n',
                       encoding='utf-8')
        live_report, _ = self.validate(staged=False)
        self.assertGreater(live_report['counts']['errors'], 0)
        staged_report, _ = self.validate(staged=True)
        self.assertEqual(staged_report['counts']['errors'], 0,
                         staged_report['issues'])

    def test_staged_invalid_fails_when_worktree_valid(self):
        write_note(self.vault, 'Projects/a.md', 'StageAlpha2',
                   'See [b](b.md).\n')
        write_note(self.vault, 'Projects/b.md', 'StageBee2', 'Hi.\n')
        git_repo(self.ws)
        # Stage invalid content, then repair worktree without staging.
        bad = self.vault / 'Projects' / 'a.md'
        bad.write_text(VALID_FM.format(title='StageAlpha2') + '[gone](gone-xyz.md)\n',
                       encoding='utf-8')
        git(self.ws, 'add', '-A')
        bad.write_text(VALID_FM.format(title='StageAlpha2') + 'See [b](b.md).\n',
                       encoding='utf-8')
        live_report, _ = self.validate(staged=False)
        self.assertEqual(live_report['counts']['errors'], 0, live_report['issues'])
        staged_report, _ = self.validate(staged=True)
        self.assertGreater(staged_report['counts']['errors'], 0)

    def test_staged_deleted_linked_target_fails(self):
        write_note(self.vault, 'Projects/a.md', 'DelAlpha',
                   'See [b](b.md).\n')
        write_note(self.vault, 'Projects/b.md', 'DelBee', 'Hi.\n')
        git_repo(self.ws)
        subprocess.run(['git', 'rm', '-q', 'Knowledge Base/Projects/b.md'],
                       cwd=str(self.ws), check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        staged_report, _ = self.validate(staged=True)
        self.assertGreater(staged_report['counts']['errors'], 0)

    def test_staged_without_head_commit(self):
        write_note(self.vault, 'Projects/a.md', 'NoHeadA', 'Hi.\n')
        git(self.ws, 'init')
        git(self.ws, 'config', 'user.email', 't@t.t')
        git(self.ws, 'config', 'user.name', 't')
        git(self.ws, 'add', '-A')
        report, _ = self.validate(staged=True)
        self.assertEqual(report['counts']['errors'], 0, report['issues'])

    def test_topology_orphan_then_index_link(self):
        cfg = json.loads(self.config.read_text(encoding='utf-8'))
        cfg['validation'] = {'topology': True}
        self.config.write_text(json.dumps(cfg), encoding='utf-8')
        write_note(self.vault, 'Projects/orph.md', 'OrphanNote', 'Alone.\n')
        report, _ = self.validate()
        self.assertGreater(report['counts']['errors'], 0)
        idx = self.vault / 'Projects' / 'INDEX.md'
        text = idx.read_text(encoding='utf-8')
        if 'orph' not in text:
            idx.write_text(text + '\n- [[orph]]\n', encoding='utf-8')
        report2, _ = self.validate()
        self.assertEqual(report2['counts']['errors'], 0, report2['issues'])

    def test_topology_dated_record_exempt_but_index_required(self):
        cfg = json.loads(self.config.read_text(encoding='utf-8'))
        cfg['validation'] = {'topology': True}
        self.config.write_text(json.dumps(cfg), encoding='utf-8')
        daily_dir = self.vault / 'Tasks' / 'Daily'
        daily_dir.mkdir(parents=True, exist_ok=True)
        (daily_dir / 'INDEX.md').write_text(
            VALID_FM.format(title='Daily Index').replace(
                'kind: note', 'kind: index') + '# Daily\n', encoding='utf-8')
        (daily_dir / '2026-10-07.md').write_text(
            VALID_FM.format(title='Daily Record') + '# Day\n', encoding='utf-8')
        tasks_idx = self.vault / 'Tasks' / 'INDEX.md'
        ttext = tasks_idx.read_text(encoding='utf-8')
        if 'Daily/INDEX' not in ttext:
            tasks_idx.write_text(ttext + '\n- [[Daily/INDEX]]\n', encoding='utf-8')
        report, _ = self.validate()
        self.assertEqual(report['counts']['errors'], 0, report['issues'])


if __name__ == '__main__':
    unittest.main()
