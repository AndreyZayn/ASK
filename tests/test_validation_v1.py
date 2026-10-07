import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ASK = ROOT / 'scripts' / 'ask.py'
HEAD = '---\ntitle: %s\ndescription: X\nkind: note\nscope: shared\nlifecycle_status: active\nupdated: 2026-10-05\n%s---\n'


def cli(*args):
    return subprocess.run([sys.executable, str(ASK), *map(str, args)], text=True, capture_output=True)


def note(title, body='', extra=''):
    return HEAD % (title, extra) + body


class ValidationV1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.ws = self.base / 'private'
        r = cli('init', '--workspace', self.ws)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.cfg = self.ws / 'ask.json'
        self.vault = self.ws / 'Knowledge Base'

    def tearDown(self):
        self.tmp.cleanup()

    def validate(self):
        r = cli('validate', '--config', self.cfg, '--json')
        return r.returncode, json.loads(r.stdout)

    def write(self, rel, text):
        p = self.vault / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def edit_cfg(self, **changes):
        cfg = json.loads(self.cfg.read_text())
        cfg.update(changes)
        self.cfg.write_text(json.dumps(cfg))

    def edit_schema(self, fn):
        path = self.ws / 'note.schema.json'
        schema = json.loads(path.read_text())
        fn(schema)
        path.write_text(json.dumps(schema))

    # Attachments
    def test_image_and_pdf_links_are_attachment_nodes(self):
        (self.vault / 'assets').mkdir()
        (self.vault / 'assets' / 'diagram.png').write_bytes(b'\x89PNG')
        (self.vault / 'docs').mkdir()
        (self.vault / 'docs' / 'spec.pdf').write_bytes(b'%PDF')
        self.write('media.md', note('Media', '![[diagram.png]]\n[[assets/diagram.png|pic]]\n![[docs/spec.pdf#page=2]]\n'))
        code, report = self.validate()
        self.assertEqual(code, 0, report)
        r = cli('graph', '--config', self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        graph = json.loads(r.stdout)
        nodes = {n['id']: n for n in graph['nodes']}
        for att in ('assets/diagram.png', 'docs/spec.pdf'):
            self.assertEqual(nodes[att]['type'], 'attachment')
            self.assertEqual(nodes[att]['metadata']['kind'], 'attachment')
            self.assertIn({'source': 'media.md', 'target': att, 'type': 'navigational'}, graph['edges'])
        self.assertEqual(nodes['media.md']['type'], 'note')
        edge_ends = {e['source'] for e in graph['edges']} | {e['target'] for e in graph['edges']}
        self.assertTrue(edge_ends <= set(nodes))

    def test_missing_attachment_fails(self):
        self.write('media.md', note('Media', '![[missing.png]]\n'))
        code, report = self.validate()
        self.assertEqual(code, 1)
        self.assertIn('missing.png', report['issues'][0]['message'])

    # Suffix handling
    def test_arbitrary_suffix_not_coerced_to_md(self):
        self.write('readme.md', note('Readme'))
        self.write('src.md', note('Src', '[[readme.txt]]\n'))
        self.assertEqual(self.validate()[0], 1)
        self.write('src.md', note('Src', '[[readme.png]]\n'))
        self.assertEqual(self.validate()[0], 1)
        self.write('readme.txt.md', note('Dotted Readme'))
        self.write('src.md', note('Src', '[[readme.txt]]\n'))
        self.assertEqual(self.validate()[0], 1)

    def test_numeric_suffix_is_not_coerced_either(self):
        self.write('release-1.2.md', note('Release'))
        self.write('src.md', note('Src', '[[release-1.2]]\n'))
        self.assertEqual(self.validate()[0], 1)
        self.write('src.md', note('Src', '[[release-1.2.md]]\n'))
        code, report = self.validate()
        self.assertEqual(code, 0, report)

    # Path resolution
    def test_wrong_directory_does_not_basename_fallback(self):
        self.write('real/target.md', note('Target'))
        self.write('src.md', note('Src', '[[target]]\n'))
        self.assertEqual(self.validate()[0], 0)
        self.write('src.md', note('Src', '[[wrong/target]]\n'))
        self.assertEqual(self.validate()[0], 1)
        self.write('src.md', note('Src', '[[./target]]\n'))
        self.assertEqual(self.validate()[0], 1)

    def test_escaping_relative_path_does_not_basename_fallback(self):
        self.write('target.md', note('Target'))
        self.write('src.md', note('Src', '[[../target]]\n'))
        self.assertEqual(self.validate()[0], 1)
        self.write('sub/src2.md', note('Src2', '[[../../target]]\n'))
        self.write('src.md', note('Src'))
        self.assertEqual(self.validate()[0], 1)

    # YAML and schema
    def test_unindented_block_list_and_obsidian_fields(self):
        self.write('tags.md', note('Tags', extra='tags:\n- alpha\n- beta\naliases:\n- Tag Note\ncssclasses:\n- wide\n'))
        code, report = self.validate()
        self.assertEqual(code, 0, report)

    def test_unindented_relation_items_still_require_quotes(self):
        self.write('target.md', note('Target'))
        self.write('src.md', note('Src', extra='depends_on:\n- [[target]]\n'))
        self.assertEqual(self.validate()[0], 1)
        self.write('src.md', note('Src', extra='depends_on:\n- "[[target]]"\n'))
        self.assertEqual(self.validate()[0], 0)

    def test_item_enum_and_format_enforced(self):
        def fn(s):
            s['properties']['labels'] = {'type': 'array', 'items': {'type': 'string', 'enum': ['alpha', 'beta']}}
            s['properties']['reviewed'] = {'type': 'array', 'items': {'type': 'string', 'format': 'date'}}
        self.edit_schema(fn)
        self.write('a.md', note('A', extra='labels:\n  - gamma\n'))
        code, report = self.validate()
        self.assertEqual(code, 1)
        self.assertIn('labels', report['issues'][0]['message'])
        self.write('a.md', note('A', extra='reviewed:\n  - "2026-02-30"\n'))
        code, report = self.validate()
        self.assertEqual(code, 1)
        self.assertIn('reviewed', report['issues'][0]['message'])
        self.write('a.md', note('A', extra='labels:\n  - beta\nreviewed:\n  - "2026-02-03"\n'))
        self.assertEqual(self.validate()[0], 0)

    def test_scalar_wikilink_format_enforced(self):
        self.edit_schema(lambda s: s['properties'].__setitem__('parent', {'type': 'string', 'format': 'wikilink-note'}))
        self.write('a.md', note('A', extra='parent: "[[missing]]"\n'))
        self.assertEqual(self.validate()[0], 1)
        self.write('a.md', note('A', extra='parent: "[[INDEX]]"\n'))
        self.assertEqual(self.validate()[0], 0)

    def test_unsupported_schema_combinations_rejected(self):
        cases = [
            lambda s: s['properties'].__setitem__('nested', {'type': 'array', 'items': {'type': 'array'}}),
            lambda s: s['properties'].__setitem__('obj', {'type': 'object'}),
            lambda s: s['properties'].__setitem__('untyped', {'minLength': 1}),
            lambda s: s['properties'].__setitem__('arrenum', {'type': 'array', 'enum': [['a']]}),
            lambda s: s['properties'].__setitem__('boolfmt', {'type': 'boolean', 'format': 'date'}),
            lambda s: s['properties']['tags'].__setitem__('additionalProperties', False),
            lambda s: s['required'].append('not_a_property'),
            lambda s: s['properties']['kind'].__setitem__('enum', ['note', 3]),
        ]
        original = (self.ws / 'note.schema.json').read_text()
        for fn in cases:
            (self.ws / 'note.schema.json').write_text(original)
            self.edit_schema(fn)
            code, report = self.validate()
            self.assertEqual(code, 2, (fn, report))

    # Config invariants
    def test_duplicate_bootstrap_rejected(self):
        for boot in (['INDEX.md', 'INDEX.md'], ['INDEX.md', './INDEX.md']):
            self.edit_cfg(bootstrap_files=boot)
            r = cli('bootstrap', '--config', self.cfg)
            self.assertEqual(r.returncode, 2)
            self.assertIn('duplicate', r.stderr)

    def test_read_paths_must_cover_bootstrap(self):
        self.edit_cfg(access={'read': ['Agents'], 'write': []})
        r = cli('bootstrap', '--config', self.cfg)
        self.assertEqual(r.returncode, 2)
        self.assertIn('not covered', r.stderr)
        self.edit_cfg(access={'read': ['Agents', 'INDEX.md', 'date.md', 'agents.md', 'knowledge-map.md'], 'write': []})
        r = cli('bootstrap', '--config', self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)

    # Adapter
    def test_adapter_renders_resolved_paths_and_command(self):
        for text in ((self.ws / 'AGENTS.md').read_text(), cli('bootstrap', '--config', self.cfg).stdout):
            self.assertIn(str(self.vault), text)
            self.assertIn(str(self.vault / 'INDEX.md'), text)
            cmd = 'python3 %s validate --config %s' % (shlex.quote(str(ASK)), shlex.quote(str(self.cfg)))
            self.assertIn(cmd, text)
            self.assertIn('relative to the vault root', text)
        (self.ws / 'nested').mkdir()
        r = cli('bootstrap', '--config', self.ws / 'nested' / '..' / 'ask.json')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(str(self.vault / 'INDEX.md'), r.stdout)
        self.assertIn('python3 %s validate --config %s' % (shlex.quote(str(ASK)), shlex.quote(str(self.cfg))), r.stdout)
        self.assertNotIn('/nested/../', r.stdout)

    # Init
    def test_vault_name_normalized_before_writing(self):
        ws = self.base / 'norm'
        r = cli('init', '--workspace', ws, '--vault-name', './Nested/./Vault/')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads((ws / 'ask.json').read_text())['vault_root'], 'Nested/Vault')
        self.assertTrue((ws / 'Nested' / 'Vault' / 'INDEX.md').is_file())
        for i, name in enumerate(('./', '.', 'a/..')):
            ws = self.base / ('dot%d' % i)
            r = cli('init', '--workspace', ws, '--vault-name', name)
            self.assertEqual(r.returncode, 2, name)
            self.assertFalse((ws / 'ask.json').exists())
            self.assertFalse(ws.exists())

    def test_init_bootstrap_defaults_retained(self):
        cfg = json.loads(self.cfg.read_text())
        self.assertEqual(cfg['bootstrap_files'], ['date.md', 'INDEX.md', 'agents.md', 'knowledge-map.md'])
        self.assertEqual(cli('init', '--workspace', self.ws).returncode, 2)


if __name__ == '__main__':
    unittest.main()
