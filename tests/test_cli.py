import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ASK = ROOT / 'scripts' / 'ask.py'


def cli(*args, env=None):
    return subprocess.run([sys.executable, str(ASK), *map(str, args)], text=True, capture_output=True, env=env)


class AskCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.workspace = self.base / 'private'

    def tearDown(self):
        self.tmp.cleanup()

    def init(self, *args):
        return cli('init', '--workspace', self.workspace, *args)

    def config(self):
        return self.workspace / 'ask.json'

    def test_init_validate_bootstrap_and_safe_graph(self):
        r = self.init('--vault-name', 'My Vault')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.workspace / 'My Vault' / 'INDEX.md').exists())
        self.assertEqual(cli('validate', '--config', self.config()).returncode, 0)
        b = cli('bootstrap', '--config', self.config())
        self.assertEqual(b.returncode, 0, b.stderr)
        self.assertIn('actual runtime filesystem permissions', b.stdout.lower())
        g = cli('graph', '--config', self.config())
        self.assertEqual(g.returncode, 0, g.stderr)
        graph = json.loads(g.stdout)
        self.assertTrue(graph['nodes'])
        out = self.base / 'graph.json'
        self.assertEqual(cli('graph', '--config', self.config(), '--output', out).returncode, 0)
        self.assertEqual(out.read_text(), g.stdout)

    def test_init_preflights_all_outputs_and_never_overwrites(self):
        self.workspace.mkdir()
        (self.workspace / 'note.schema.json').write_text('keep')
        r = self.init()
        self.assertEqual(r.returncode, 2)
        self.assertIn('output already exists', r.stderr)
        self.assertEqual((self.workspace / 'note.schema.json').read_text(), 'keep')
        self.assertFalse((self.workspace / 'ask.json').exists())

    def test_init_rejects_distribution_and_unsafe_vault_name(self):
        dest = ROOT / 'new-private'
        r = cli('init', '--workspace', dest)
        self.assertEqual(r.returncode, 2); self.assertIn('outside the distribution', r.stderr)
        self.assertFalse(dest.exists())
        for i, name in enumerate(('../escape', '/tmp/escape')):
            ws = self.base / ('unsafe-' + str(i))
            r = cli('init', '--workspace', ws, '--vault-name', name)
            self.assertEqual(r.returncode, 2); self.assertIn('stay within', r.stderr)
            self.assertFalse((ws / 'ask.json').exists())

    def test_custom_config_access_and_enum(self):
        self.assertEqual(self.init().returncode, 0)
        cfg = json.loads(self.config().read_text())
        cfg['bootstrap_files'] = ['INDEX.md', 'date.md']
        cfg['access'] = {'read': ['Agents', 'INDEX.md', 'date.md'], 'write': ['Tasks']}
        self.config().write_text(json.dumps(cfg))
        schema_path = self.workspace / 'note.schema.json'
        schema = json.loads(schema_path.read_text())
        schema['properties']['scope']['enum'].append('local-extra')
        schema_path.write_text(json.dumps(schema))
        b = cli('bootstrap', '--config', self.config())
        self.assertLess(b.stdout.index('INDEX.md'), b.stdout.index('date.md'))
        self.assertIn('Agents', b.stdout)
        self.assertIn('Tasks', b.stdout)
        note = self.workspace / 'Knowledge Base' / 'custom.md'
        note.write_text('---\ntitle: Custom\ndescription: Test\nkind: note\nscope: local-extra\nlifecycle_status: active\nupdated: 2026-10-05\n---\n')
        self.assertEqual(cli('validate', '--config', self.config()).returncode, 0)

    def test_strict_metadata_date_json_and_schema_errors(self):
        self.assertEqual(self.init().returncode, 0)
        vault = self.workspace / 'Knowledge Base'
        note = vault / 'bad.md'
        note.write_text('---\ntitle: Bad\ntitle: Duplicate\ndescription: Bad\nkind: note\nscope: shared\nlifecycle_status: active\nupdated: 2026-02-30\n---\n')
        r = cli('validate', '--config', self.config(), '--json')
        self.assertEqual(r.returncode, 1)
        payload = json.loads(r.stdout)
        self.assertGreater(payload['counts']['errors'], 0)
        note.write_text('---\ntitle: Bad\ndescription: Bad\nkind: note\nscope: shared\nlifecycle_status: active\nupdated: 2026-02-30\n---\n')
        self.assertEqual(cli('validate', '--config', self.config()).returncode, 1)
        schema = json.loads((self.workspace / 'note.schema.json').read_text())
        schema['properties']['kind']['unsupported_keyword'] = True
        (self.workspace / 'note.schema.json').write_text(json.dumps(schema))
        r = cli('validate', '--config', self.config(), '--json')
        self.assertEqual(r.returncode, 2)
        self.assertIsInstance(json.loads(r.stdout), dict)

    def test_link_resolution_ambiguity_parent_and_deleted_target(self):
        self.assertEqual(self.init().returncode, 0)
        v = self.workspace / 'Knowledge Base'
        (v / 'Projects').mkdir(exist_ok=True)
        (v / 'Projects' / 'one.md').write_text('---\ntitle: One\ndescription: A\nkind: note\nscope: shared\nlifecycle_status: active\nupdated: 2026-10-05\n---\n[[../date]]\n')
        (v / 'Projects' / 'two.md').write_text('---\ntitle: Two\ndescription: B\nkind: note\nscope: shared\nlifecycle_status: active\nupdated: 2026-10-05\n---\n[[one|alias]]\n')
        self.assertEqual(cli('validate', '--config', self.config()).returncode, 0)
        (v / 'Projects' / 'two.md').write_text((v / 'Projects' / 'two.md').read_text().replace('[[one|alias]]', '[[gone]]'))
        self.assertEqual(cli('validate', '--config', self.config()).returncode, 1)
        (v / 'x').mkdir(); (v / 'y').mkdir()
        for d in ('x', 'y'):
            (v / d / 'same.md').write_text('---\ntitle: Same %s\ndescription: X\nkind: note\nscope: shared\nlifecycle_status: active\nupdated: 2026-10-05\n---\n' % d)
        (v / 'Projects' / 'two.md').write_text((v / 'Projects' / 'two.md').read_text().replace('[[gone]]', '[[same]]'))
        self.assertEqual(cli('validate', '--config', self.config()).returncode, 1)

    def test_relations_direction_and_invalid_relation(self):
        self.assertEqual(self.init().returncode, 0)
        v = self.workspace / 'Knowledge Base'
        target = '---\ntitle: Target\ndescription: X\nkind: note\nscope: shared\nlifecycle_status: active\nupdated: 2026-10-05\n---\n'
        (v / 'target.md').write_text(target)
        src = v / 'source.md'
        valid = '---\ntitle: Source\ndescription: X\nkind: note\nscope: shared\nlifecycle_status: active\nupdated: 2026-10-05\ndepends_on:\n  - "[[target]]"\n---\n'
        src.write_text(valid)
        r = cli('graph', '--config', self.config())
        self.assertEqual(r.returncode, 0, r.stderr)
        graph = json.loads(r.stdout)
        edge = next(e for e in graph['edges'] if e['type'] == 'depends_on' and e['source'] == 'source.md')
        self.assertEqual((edge['source'], edge['target']), ('source.md', 'target.md'))
        self.assertFalse(any(e['source'] == 'target.md' and e['target'] == 'source.md' for e in graph['edges']))

        src.write_text(valid.replace('[[target]]', '[[target|alias]]'))
        self.assertEqual(cli('validate', '--config', self.config()).returncode, 1)
        src.write_text(valid.replace('"[[target]]"', '[[target]]'))
        self.assertEqual(cli('validate', '--config', self.config()).returncode, 1)

        src.write_text(valid.replace('[[target]]', '[[source]]'))
        r = cli('validate', '--config', self.config(), '--json')
        self.assertEqual(r.returncode, 1)
        self.assertIn('self', json.loads(r.stdout)['issues'][0]['message'])
        graph_out = self.base / 'self-graph.json'
        r = cli('graph', '--config', self.config(), '--output', graph_out)
        self.assertEqual(r.returncode, 1)
        self.assertIn('integrity', r.stderr.lower())
        self.assertFalse(graph_out.exists())

    def test_symlink_and_output_escape_refused(self):
        self.assertEqual(self.init().returncode, 0)
        v = self.workspace / 'Knowledge Base'
        outside = self.base / 'outside.md'; outside.write_text('secret')
        try:
            (v / 'link.md').symlink_to(outside)
        except OSError:
            self.skipTest('symlinks unavailable')
        r = cli('validate', '--config', self.config())
        self.assertEqual(r.returncode, 1); self.assertIn('symlink in vault', r.stderr)
        out = self.base / 'graph.json'
        r = cli('graph', '--config', self.config(), '--output', out)
        self.assertEqual(r.returncode, 1); self.assertIn('integrity', r.stderr.lower())
        self.assertFalse(out.exists())

    def test_rejects_symlinked_path_ancestors(self):
        real_parent = self.base / 'real-parent'; real_parent.mkdir()
        parent_link = self.base / 'parent-link'
        parent_link.symlink_to(real_parent, target_is_directory=True)
        workspace = parent_link / 'new-workspace'
        r = cli('init', '--workspace', workspace)
        self.assertEqual(r.returncode, 2); self.assertIn('symlink path', r.stderr)
        self.assertFalse((real_parent / 'new-workspace' / 'ask.json').exists())

        self.assertEqual(self.init().returncode, 0)
        real_output = self.base / 'real-output'; real_output.mkdir()
        output_link = self.base / 'output-link'
        output_link.symlink_to(real_output, target_is_directory=True)
        r = cli('bootstrap', '--config', self.config(), '--output', output_link / 'adapter.md')
        self.assertEqual(r.returncode, 2); self.assertIn('symlink path', r.stderr)
        self.assertFalse((real_output / 'adapter.md').exists())

        vault = self.workspace / 'Knowledge Base'
        real_vault_parent = self.workspace / 'real-vault'; real_vault_parent.mkdir()
        vault.rename(real_vault_parent / 'Knowledge Base')
        vault_link = self.workspace / 'vault-link'
        vault_link.symlink_to(real_vault_parent, target_is_directory=True)
        cfg = json.loads(self.config().read_text()); cfg['vault_root'] = 'vault-link/Knowledge Base'
        self.config().write_text(json.dumps(cfg))
        r = cli('validate', '--config', self.config(), '--json')
        self.assertEqual(r.returncode, 2)
        self.assertIn('symlink path', json.loads(r.stdout)['issues'][0]['message'])

    def test_rejects_symlinked_config_and_schema_ancestors(self):
        self.assertEqual(self.init().returncode, 0)
        config_parent_link = self.base / 'config-link'
        config_parent_link.symlink_to(self.workspace, target_is_directory=True)
        r = cli('bootstrap', '--config', config_parent_link / 'ask.json')
        self.assertEqual(r.returncode, 2); self.assertIn('symlink path', r.stderr)

        schema_dir = self.workspace / 'schema-real'; schema_dir.mkdir()
        (self.workspace / 'note.schema.json').rename(schema_dir / 'note.schema.json')
        (self.workspace / 'schema-link').symlink_to(schema_dir, target_is_directory=True)
        cfg = json.loads(self.config().read_text()); cfg['schema_path'] = 'schema-link/note.schema.json'
        self.config().write_text(json.dumps(cfg))
        r = cli('validate', '--config', self.config(), '--json')
        self.assertEqual(r.returncode, 2)
        self.assertIn('symlink path', json.loads(r.stdout)['issues'][0]['message'])

    def test_frontmatter_colon_and_code_examples(self):
        self.assertEqual(self.init().returncode, 0)
        vault = self.workspace / 'Knowledge Base'
        note = vault / 'colon.md'
        note.write_text('---\ntitle: Colon\ndescription: unquoted: invalid\nkind: note\nscope: shared\nlifecycle_status: active\nupdated: 2026-10-05\n---\n```md\n[[missing]]\n```\nInline `[[also-missing]]`.\n')
        r = cli('validate', '--config', self.config(), '--json')
        self.assertEqual(r.returncode, 1)
        self.assertIn('invalid unquoted scalar', json.loads(r.stdout)['issues'][0]['message'])
        note.write_text(note.read_text().replace('description: unquoted: invalid', 'description: "quoted: valid"'))
        r = cli('validate', '--config', self.config(), '--json')
        self.assertEqual(r.returncode, 0, r.stdout)

        target = vault / 'target.md'
        target.write_text('---\ntitle: Target\ndescription: Target note\nkind: note\nscope: shared\nlifecycle_status: active\nupdated: 2026-10-05\n---\n')
        note.write_text('---\ntitle: Colon\ndescription: Clean\nkind: note\nscope: shared\nlifecycle_status: active\nupdated: 2026-10-05\n---\n'
                        'Double ``[[missing-double]]`` and triple ```[[missing-triple]]``` spans.\n'
                        'Inner `` `[[missing-inner]]` `` backtick.\n'
                        '```md\n[[missing-fenced]]\n```\n')
        r = cli('validate', '--config', self.config(), '--json')
        self.assertEqual(r.returncode, 0, r.stdout)

        note.write_text(note.read_text() + 'Unmatched delimiter: `[[missing-unmatched]].\n')
        r = cli('validate', '--config', self.config(), '--json')
        self.assertEqual(r.returncode, 1)
        self.assertTrue(any('missing-unmatched' in issue['message'] for issue in json.loads(r.stdout)['issues']))

    def test_config_version_requires_integer_one(self):
        self.assertEqual(self.init().returncode, 0)
        for value in (True, 1.0):
            cfg = json.loads(self.config().read_text())
            cfg['version'] = value
            self.config().write_text(json.dumps(cfg))
            r = cli('bootstrap', '--config', self.config())
            self.assertEqual(r.returncode, 2)
            self.assertIn('version must be the integer 1', r.stderr)

    def test_vault_walk_io_error_fails_validation_and_graph(self):
        self.assertEqual(self.init().returncode, 0)
        vault = self.workspace / 'Knowledge Base'
        shim = self.base / 'python-shim'; shim.mkdir()
        (shim / 'sitecustomize.py').write_text(
            'import os\nfrom pathlib import Path\n_real_walk = os.walk\n'
            'def _walk(top, *args, **kwargs):\n'
            '    fail = os.environ.get("ASK_WALK_ERROR_ROOT")\n'
            '    if fail and Path(top).resolve() == Path(fail).resolve():\n'
            '        error = PermissionError(13, "simulated scan denial", str(top))\n'
            '        callback = kwargs.get("onerror")\n'
            '        if callback: callback(error)\n'
            '        return iter(())\n'
            '    return _real_walk(top, *args, **kwargs)\n'
            'os.walk = _walk\n')
        env = os.environ.copy()
        env['PYTHONPATH'] = str(shim) + os.pathsep + env.get('PYTHONPATH', '')
        env['ASK_WALK_ERROR_ROOT'] = str(vault)
        r = cli('validate', '--config', self.config(), '--json', env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn('cannot scan vault', json.loads(r.stdout)['issues'][0]['message'])
        output = self.base / 'incomplete-graph.json'
        r = cli('graph', '--config', self.config(), '--output', output, env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn('cannot scan vault', r.stderr)
        self.assertFalse(output.exists())

    def test_config_path_rejections_and_missing_bootstrap(self):
        self.assertEqual(self.init().returncode, 0)
        cfg = json.loads(self.config().read_text())
        cfg['bootstrap_files'] = ['../outside.md']
        self.config().write_text(json.dumps(cfg))
        r = cli('bootstrap', '--config', self.config())
        self.assertEqual(r.returncode, 2); self.assertIn('stay within', r.stderr)
        cfg['bootstrap_files'] = ['missing.md']
        self.config().write_text(json.dumps(cfg))
        r = cli('validate', '--config', self.config(), '--json')
        self.assertEqual(r.returncode, 2); self.assertIn('bootstrap note missing', json.loads(r.stdout)['issues'][0]['message'])

    def test_cli_errors_and_output_no_overwrite(self):
        self.assertEqual(cli('validate', '--config', self.base / 'missing').returncode, 2)
        self.assertEqual(self.init().returncode, 0)
        output = self.base / 'adapter.md'; output.write_text('keep')
        self.assertEqual(cli('bootstrap', '--config', self.config(), '--output', output).returncode, 2)
        self.assertEqual(output.read_text(), 'keep')
        r = cli('validate', '--config', self.base / 'missing', '--json')
        self.assertEqual(r.returncode, 2)
        json.loads(r.stdout)


if __name__ == '__main__':
    unittest.main()
