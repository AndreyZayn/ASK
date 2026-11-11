"""Synthetic profile, upgrade compatibility, and staged-schema regression tests."""
from legacy_fixture import legacy_result
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ask
from asklib import validation
from asklib.path_schema import matches


def cli(*args):
    return legacy_result(subprocess.run([sys.executable, str(ROOT/'scripts/ask.py'), *map(str,args)], capture_output=True, text=True), args)


class PathProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name).resolve()/'workspace'
        self.assertEqual(cli('init','--workspace',self.ws,'--vault-name','My Notes').returncode,0)
        self.cp = self.ws/'ask.json'
        self.vault = self.ws/'My Notes'
        self.schema = self.ws/'note.schema.json'

    def tearDown(self):
        self.tmp.cleanup()

    def report(self, staged=False):
        return validation.validate(ask,self.cp,staged=staged)[0]

    def edit_schema(self, fn):
        schema=json.loads(self.schema.read_text());fn(schema)
        self.schema.write_text(json.dumps(schema))

    def write(self,path,fields,body=''):
        p=self.vault/path;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text('---\n'+fields+'\n---\n'+body)
        return p

    def git(self,*args):
        r=subprocess.run(['git',*args],cwd=self.ws,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        return r

    def test_fresh_scaffold_is_valid_with_topology(self):
        cfg=json.loads(self.cp.read_text());cfg['validation']={'topology':True};self.cp.write_text(json.dumps(cfg))
        self.assertEqual(self.report()['counts']['errors'],0,self.report())
        self.assertEqual(len(list((self.vault/'Agents/hats').glob('*.md'))),12)
        self.assertTrue((self.vault/'Agents/rules/task-completion.md').exists())

    def test_globs_are_segment_aware(self):
        self.assertTrue(matches('People/team/person.md','People/*/*.md'))
        self.assertFalse(matches('People/team/archive/person.md','People/*/*.md'))
        self.assertTrue(matches('Projects/Example/INDEX.md','Projects/*/**/*.md'))
        self.assertTrue(matches('Projects/Example/product/story.md','Projects/*/**/*.md'))
        self.assertFalse(matches('Projects/INDEX.md','Projects/*/**/*.md'))

    def test_operational_profiles_and_required_state(self):
        p=self.write('Tasks/Daily/2000-01-01.md','date: 2000-01-01\nkind: daily-plan\nscope: personal\nplan_status: planned')
        self.write('Memory/Logs/2000-01.md','month: 2000-01\nkind: log\nscope: personal')
        self.assertEqual(self.report()['counts']['errors'],0,self.report())
        p.write_text(p.read_text().replace('plan_status: planned','lifecycle_status: active'))
        messages=str(self.report()['issues'])
        self.assertIn('missing required field: plan_status',messages)
        self.assertIn('forbidden',messages)

    def test_person_profile(self):
        p=self.write('People/personal/example.md','title: Example Person\ndescription: Synthetic contact\nkind: person\nscope: personal\nupdated: 2000-01-01\ncontexts: ["example"]\nrelationship_status: warm')
        self.assertEqual(self.report()['counts']['errors'],0,self.report())
        p.write_text(p.read_text().replace('contexts: ["example"]','project: forbidden'))
        self.assertIn('contexts',str(self.report()['issues']))
        self.assertIn('forbidden',str(self.report()['issues']))

    def test_project_identity_and_owner_mapping(self):
        p=self.write('Projects/Example/INDEX.md','title: Example Project\ndescription: Synthetic project\nkind: index\nscope: work\nupdated: 2000-01-01\nlifecycle_status: active')
        self.assertIn('missing required field: project',str(self.report()['issues']))
        p.write_text(p.read_text().replace('scope: work','scope: work\nproject: example'))
        self.edit_schema(lambda s:s['x-ask-path-rules'].append({'glob':'Projects/Example/**','properties':{'project':{'type':'string','enum':['example']}}}))
        self.assertEqual(self.report()['counts']['errors'],0,self.report())
        p.write_text(p.read_text().replace('project: example','project: wrong'))
        self.assertIn('project is not an allowed value',str(self.report()['issues']))

    def test_owner_tag_vocabulary(self):
        p=self.write('custom.md','title: Custom\ndescription: Synthetic\nkind: note\nscope: shared\nlifecycle_status: active\nupdated: 2000-01-01\ntags: ["local-facet"]')
        self.assertIn('tags item is not an allowed value',str(self.report()['issues']))
        self.edit_schema(lambda s:s['properties']['tags']['items']['enum'].append('local-facet'))
        self.assertEqual(self.report()['counts']['errors'],0,self.report())

    def test_later_properties_override_and_conflicts_fail_closed(self):
        self.edit_schema(lambda s:s['x-ask-path-rules'].append({'glob':'Personal/**','properties':{'scope':{'type':'string','enum':['personal','shared']}}}))
        p=self.vault/'Personal/INDEX.md';p.write_text(p.read_text().replace('scope: personal','scope: shared'))
        self.assertEqual(self.report()['counts']['errors'],0,self.report())
        self.edit_schema(lambda s:s['x-ask-path-rules'].append({'glob':'Personal/**','required':['project']}))
        self.assertTrue(self.report().get('configuration_error'))

    def test_malformed_profile_fails_as_configuration(self):
        original=self.schema.read_text()
        for rule in ({'glob':'../*.md'}, {'glob':'*.md','properties':{'unknown':{'type':'string'}}}, {'glob':'*.md','required':['title'],'forbidden':['title']}, {'glob':'*.md','optional':'title'}, {'glob':'*.md','unexpected':True}):
            self.schema.write_text(original)
            self.edit_schema(lambda s:s['x-ask-path-rules'].append(rule))
            self.assertTrue(self.report().get('configuration_error'),rule)

    def test_existing_schema_without_extension_is_not_migrated(self):
        self.edit_schema(lambda s:s.pop('x-ask-path-rules'))
        # Existing installations can retain their common-field loop conventions.
        for p in (self.vault/'Agents/loops').glob('*.md'):
            p.write_text(p.read_text().replace('loop_status: active','lifecycle_status: active'))
        p=self.vault/'Personal/INDEX.md';p.write_text(p.read_text().replace('scope: personal','scope: shared'))
        before={str(p.relative_to(self.ws)):p.read_bytes() for p in self.ws.rglob('*') if p.is_file()}
        self.assertEqual(self.report()['counts']['errors'],0,self.report())
        self.assertEqual(cli('init','--workspace',self.ws).returncode,2)
        after={str(p.relative_to(self.ws)):p.read_bytes() for p in self.ws.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_legacy_custom_fields_and_operational_notes_remain_valid(self):
        self.edit_schema(lambda s:s.pop('x-ask-path-rules'))
        self.edit_schema(lambda s:s['required'].remove('lifecycle_status'))
        self.edit_schema(lambda s:s['properties']['repositories']['items'].pop('format'))
        common='title: %s\ndescription: Synthetic legacy record\nkind: %s\nscope: shared\nupdated: 2000-01-01\n'
        self.write('Tasks/Daily/2000-01-01.md', common % ('Legacy Plan','daily-plan'))
        self.write('Memory/Logs/2000-01.md', common % ('Legacy Log','log'))
        self.write('custom.md', (common % ('Legacy Custom','note'))+'repositories: ["local-source-label"]')
        self.assertEqual(self.report()['counts']['errors'],0,self.report())

    def test_operational_dates_and_repository_urls(self):
        p=self.write('Memory/Logs/2000-01.md','month: 2000-02\nkind: log\nscope: personal')
        self.assertIn('month must match',str(self.report()['issues']))
        p.write_text(p.read_text().replace('2000-02','2000-13'))
        self.assertIn('valid YYYY-MM',str(self.report()['issues']))
        p.unlink()
        p=self.write('asset.md','title: Asset\ndescription: Synthetic\nkind: codebase\nscope: shared\nlifecycle_status: active\nupdated: 2000-01-01\nrepositories: ["https://example.org/team/repo"]')
        self.assertEqual(self.report()['counts']['errors'],0,self.report())
        p.write_text(p.read_text().replace('https://example.org','https://user@example.org'))
        self.assertIn('without credentials',str(self.report()['issues']))

    def test_staged_profile_cannot_be_bypassed_by_worktree_schema(self):
        self.git('init');self.git('add','.')
        p=self.vault/'Personal/INDEX.md';p.write_text(p.read_text().replace('scope: personal','scope: shared'))
        self.git('add','My Notes/Personal/INDEX.md')
        self.edit_schema(lambda s:s.pop('x-ask-path-rules'))
        # Keep new loop notes valid under the relaxed worktree-only base schema.
        self.edit_schema(lambda s:s['required'].remove('lifecycle_status'))
        self.assertEqual(self.report()['counts']['errors'],0,self.report())
        self.assertGreater(self.report(staged=True)['counts']['errors'],0)


if __name__=='__main__':unittest.main()
