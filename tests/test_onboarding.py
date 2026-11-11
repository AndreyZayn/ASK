"""Exercise read-only onboarding proposals and their reviewed synthetic use."""
from datetime import date
import hashlib
import re
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/ask.py'


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name).resolve()
        self.ws=self.root/'owner workspace'
        self.cli('init','--workspace',self.ws,'--vault-name','Private Notes',expected=0)
        self.config=self.ws/'ask.json'
        self.vault=self.ws/'Private Notes'
        self.profile=self.root/'observations.json'

    def tearDown(self):self.tmp.cleanup()

    def cli(self,*args,expected=None):
        result=subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],capture_output=True,text=True)
        if expected is not None:self.assertEqual(result.returncode,expected,result.stdout+result.stderr)
        return result

    def data(self,agent='assistant-one',runtime='generic'):
        return {'observed_on':'2000-01-01','coverage':'Current session discovery only; no private configuration read',
            'agent':{'id':agent,'runtime':runtime,'surface':'cli','role':'controller','scope':'Read shared notes; authorized project writing','responsibility':'Help with approved project tasks'},
            'capabilities':[{'kind':'skill','name':'review-example','purpose':'Review synthetic changes','availability':'exposed','source':'Current session skill list','evidence':'Skill metadata visible; execution not tested','limits':'No install or provider test performed'}]}

    def propose(self,data=None,runtime='generic',expected=0):
        self.profile.write_text(json.dumps(self.data() if data is None else data))
        r=self.cli('agent','onboarding','--config',self.config,'--runtime',runtime,'--profile',self.profile,expected=expected)
        return json.loads(r.stdout)

    def hashes(self):
        return {p.relative_to(self.ws).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in self.ws.rglob('*') if p.is_file()}

    def test_plan_and_proposal_are_read_only_and_use_configured_vault(self):
        before=self.hashes()
        plan=json.loads(self.cli('agent','onboarding','--config',self.config,'--runtime','generic',expected=0).stdout)
        self.assertEqual(plan['state'],'onboarding-plan')
        self.assertEqual(plan['vault'],str(self.vault))
        proposal=self.propose()
        self.assertEqual(proposal['state'],'onboarding-proposal')
        self.assertFalse(proposal['applied'])
        self.assertEqual(proposal['notes'][0]['path'],'Agents/roster.md')
        self.assertIn('assistant-one',proposal['notes'][0]['row'])
        self.assertEqual(before,self.hashes())

    def git(self,*args):
        result=subprocess.run(['git',*args],cwd=self.ws,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        return result.stdout

    def test_first_and_second_agent_complete_scoped_cli_write_flow(self):
        self.complete_write_flow(legacy=False)

    def test_legacy_first_and_second_agent_complete_scoped_cli_write_flow(self):
        self.complete_write_flow(legacy=True)

    def legacy_catalogs(self):
        for name in ('skills','integrations','plugins','runtimes'):
            index=self.vault/('Agents/capabilities/'+name+'/INDEX.md')
            flat=self.vault/('Agents/capabilities/'+name+'.md')
            flat.write_text(index.read_text().replace('kind: index','kind: registry')+'\nLegacy custom catalog.\n')
            index.unlink()
        for note in self.vault.rglob('*.md'):
            text=note.read_text()
            for name in ('skills','integrations','plugins','runtimes'):
                text=text.replace('Agents/capabilities/'+name+'/INDEX]]','Agents/capabilities/'+name+']]')
            note.write_text(text)

    def complete_write_flow(self,legacy):
        self.ws=self.root/'flow workspace';self.config=self.ws/'ask.json';self.vault=self.ws/'Private Notes'
        setup=json.loads(self.cli('setup','--workspace',self.ws,'--vault-name','Private Notes',expected=2).stdout)
        self.assertEqual(setup['state'],'setup-pending')
        if legacy:self.legacy_catalogs()
        self.git('config','user.name','Synthetic Tester');self.git('config','user.email','test@example.invalid')
        self.git('config','commit.gpgsign','false');self.git('add','.');self.git('commit','-m','Synthetic scaffold')
        # A valid unrelated change remains outside both scoped checkpoints.
        unrelated=self.vault/'goals.md';unrelated.write_text(unrelated.read_text()+'\nUnrelated owner edit.\n')
        unrelated_bytes=unrelated.read_bytes()
        today=date.today().isoformat();month=today[:7];log=self.vault/('Memory/Logs/'+month+'.md')
        first_roster=None;first_skill=None
        for agent,runtime in [('assistant-one','generic'),('assistant-two','second-runtime')]:
            token=json.loads(self.cli('write','begin','--config',self.config,'--actor',agent,expected=0).stdout)['token']
            data=self.data(agent,runtime);data['observed_on']=today
            proposal=self.propose(data,runtime=runtime)
            owned=set()
            for item in proposal['notes']:
                p=self.vault/item['path'];text=p.read_text()
                if item['header'] not in text:text=text.rstrip()+'\n\n'+item['header']+'\n'
                lines=text.splitlines();position=lines.index(item['header'].splitlines()[0])+2
                while position<len(lines) and lines[position].startswith('|'):position+=1
                lines.insert(position,item['row']);text='\n'.join(lines)+'\n'
                text=text.replace('lifecycle_status: empty','lifecycle_status: active')
                text=re.sub(r'^updated: .*$', 'updated: '+today,text,flags=re.M)
                p.write_text(text);owned.add(p.relative_to(self.ws).as_posix())
            if not log.exists():log.write_text('---\nmonth: '+month+'\nkind: log\nscope: personal\n---\n### '+today+'\n')
            log.write_text(log.read_text()+'- '+today+' '+agent+' — registered identity and observed synthetic skill.\n')
            owned.add(log.relative_to(self.ws).as_posix())
            self.cli('validate','--config',self.config,'--json',expected=0)
            # The protected roster requires explicit registration authority.
            denied=self.cli('checkpoint','--config',self.config,'--files',*sorted(owned),'--message','Register '+agent,expected=2)
            self.assertIn('access.write',denied.stdout)
            result=json.loads(self.cli('checkpoint','--config',self.config,'--files',*sorted(owned),'--message','Register '+agent,'--owner-approved',expected=2).stdout)
            self.assertTrue(result['committed']);self.assertTrue(result['backup_pending'])
            changed=set(self.git('diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines())
            self.assertEqual(changed,owned)
            self.cli('write','end','--config',self.config,'--token',token,expected=0)
            self.assertEqual(unrelated.read_bytes(),unrelated_bytes)
            roster=(self.vault/'Agents/roster.md').read_text()
            skill=(self.vault/proposal['catalogs']['skills']['path']).read_text()
            if first_roster is None:first_roster=roster;first_skill=skill
            else:
                self.assertTrue(all(line in roster for line in first_roster.splitlines()))
                self.assertTrue(all(line in skill for line in first_skill.splitlines()))
            self.assertIn('Private Notes/goals.md',self.git('status','--porcelain'))
        self.assertEqual(list((self.ws/'.ask/writers').glob('*')),[])
        self.assertFalse((self.ws/'.ask/runtime.json').exists())

    def test_fresh_people_scope_registry_and_existing_layout_preservation(self):
        registry=self.vault/'People/personal/INDEX.md'
        self.assertTrue(registry.is_file())
        self.assertIn('[[People/personal/INDEX]]',(self.vault/'People/INDEX.md').read_text())
        cfg=json.loads(self.config.read_text());cfg['validation']={'topology':True};self.config.write_text(json.dumps(cfg))
        self.cli('validate','--config',self.config,'--json',expected=0)
        (self.vault/'People/INDEX.md').write_text('Owner custom people layout.\n')
        registry.unlink();before=self.hashes()
        self.cli('init','--workspace',self.ws,'--vault-name','Private Notes',expected=2)
        self.assertEqual(before,self.hashes())
        self.assertFalse(registry.exists())

    def test_fresh_hierarchy_and_legacy_flat_catalogs(self):
        for name in ('skills','integrations','plugins','runtimes','snapshots'):
            self.assertTrue((self.vault/('Agents/capabilities/'+name+'/INDEX.md')).is_file())
        self.assertTrue((self.vault/'Agents/capabilities/skills/shared/INDEX.md').is_file())
        self.legacy_catalogs()
        self.cli('validate','--config',self.config,'--json',expected=0)
        before=self.hashes();result=self.propose()
        self.assertEqual(result['catalogs']['skills']['path'],'Agents/capabilities/skills.md')
        self.assertEqual(result['notes'][-1]['path'],'Agents/capabilities/skills.md')
        self.assertEqual(before,self.hashes())

    def test_conflicting_catalog_layouts_require_manual_reconciliation(self):
        (self.vault/'Agents/capabilities/skills.md').write_text('Custom flat catalog.\n')
        before=self.hashes()
        result=self.cli('agent','onboarding','--config',self.config,'--runtime','generic',expected=2)
        self.assertIn('multiple catalog layouts',result.stdout)
        self.assertEqual(before,self.hashes())

    def test_large_inventory_requires_explicit_bounded_batches(self):
        data=self.data()
        data['capabilities']=[dict(data['capabilities'][0],name='skill-'+str(i)) for i in range(201)]
        self.propose(data,expected=2)
        before=self.hashes();names=[]
        for i,batch in enumerate((data['capabilities'][:200],data['capabilities'][200:])):
            profile=dict(data,capabilities=batch,coverage='Batch '+str(i+1)+' of 2; total 201 exposed synthetic skills')
            result=self.propose(profile)
            self.assertEqual(result['coverage'],profile['coverage'])
            self.assertEqual(result['capability_count'],len(batch))
            names.extend(note['key']['name'] for note in result['notes'][2:])
        self.assertEqual(len(set(names)),201)
        self.assertEqual(before,self.hashes())

    def test_observation_states_and_empty_discovery_do_not_claim_verification(self):
        data=self.data();data['capabilities']=[]
        result=self.propose(data)
        self.assertEqual(result['capability_count'],0)
        self.assertFalse(result['runtime_verified'])
        self.assertIn('No capabilities',result['notes'][1]['row'])
        data=self.data();data['capabilities'][0]['availability']='unknown'
        result=self.propose(data)
        self.assertIn('unknown',result['notes'][-1]['row'])

    def test_custom_notes_and_missing_catalog_are_preserved(self):
        roster=self.vault/'Agents/roster.md';roster.write_text(roster.read_text()+'\nCustom owner policy.\n')
        missing=self.vault/'Agents/capabilities/skills/INDEX.md';missing.unlink()
        before=self.hashes();result=self.propose()
        self.assertEqual(result['catalogs']['skills']['state'],'missing')
        self.assertNotIn('Agents/capabilities/skills/INDEX.md',[n['path'] for n in result['notes']])
        self.assertEqual(result['unresolved'][0]['catalog_state'],'missing')
        self.assertIn('review-example',result['unresolved'][0]['row'])
        self.assertEqual(len(result['notes']),2)
        self.assertEqual(before,self.hashes())
        self.assertFalse(missing.exists())

    def test_custom_catalog_requires_mapping_without_losing_observations(self):
        standard=self.vault/'Agents/capabilities/skills/INDEX.md'
        custom=self.vault/'Agents/capabilities/owner-skills.md'
        standard.rename(custom)
        before=self.hashes();result=self.propose()
        self.assertNotIn(str(custom),json.dumps(result))
        self.assertEqual(len(result['notes']),2)
        unresolved=result['unresolved'][0]
        self.assertFalse(unresolved['applicable'])
        self.assertEqual(unresolved['action'],'manual-mapping-required')
        self.assertNotIn('path',unresolved)
        self.assertIn('review-example',unresolved['row'])
        self.assertEqual(before,self.hashes())

    def test_symlinked_profile_or_catalog_is_rejected_without_reading_target(self):
        self.profile.write_text(json.dumps(self.data()))
        link=self.root/'linked-profile.json';link.symlink_to(self.profile)
        self.cli('agent','onboarding','--config',self.config,'--runtime','generic','--profile',link,expected=2)
        catalog=self.vault/'Agents/capabilities/skills/INDEX.md';catalog.unlink()
        outside=self.root/'outside.md';outside.write_text('Do not expose this fixture')
        catalog.symlink_to(outside)
        r=self.cli('agent','onboarding','--config',self.config,'--runtime','generic',expected=2)
        self.assertNotIn(outside.read_text(),r.stdout+r.stderr)

    def test_scope_restriction_does_not_probe_catalogs(self):
        # An unreadable catalog path must not even trigger the symlink probe.
        roster=self.vault/'Agents/roster.md';roster.unlink()
        outside=self.root/'unread-catalog.md';outside.write_text('Synthetic private fixture')
        roster.symlink_to(outside)
        cfg=json.loads(self.config.read_text());cfg['access']['read']=cfg['bootstrap_files'];self.config.write_text(json.dumps(cfg))
        result=self.propose()
        self.assertEqual(result['catalogs']['roster']['state'],'not-in-declared-read-scope')
        self.assertEqual(result['notes'],[])
        self.assertNotIn('Synthetic private fixture',json.dumps(result))
        self.assertEqual(len(result['unresolved']),3)
        self.assertTrue(all(n['catalog_state']=='not-in-declared-read-scope' for n in result['unresolved']))
        self.assertFalse(result['applied'])

    def test_invalid_manifest_does_not_echo_sensitive_values_or_change_files(self):
        cases=[]
        data=self.data();data['agent']['id']='../foreign';cases.append(data)
        data=self.data();data['agent']['runtime']='different';cases.append(data)
        data=self.data();data['observed_on']='2000-02-30';cases.append(data)
        data=self.data();data['capabilities'][0]['availability']='ready';cases.append(data)
        data=self.data();data['capabilities'][0]['token']='synthetic-sensitive-value';cases.append(data)
        data=self.data();data['capabilities'][0]['evidence']='';cases.append(data)
        data=self.data();data['capabilities'].append(dict(data['capabilities'][0]));cases.append(data)
        before=self.hashes()
        for data in cases:
            self.profile.write_text(json.dumps(data))
            r=self.cli('agent','onboarding','--config',self.config,'--runtime','generic','--profile',self.profile,expected=2)
            self.assertNotIn('synthetic-sensitive-value',r.stdout+r.stderr)
        self.assertEqual(before,self.hashes())

    def test_proposed_markdown_cannot_inject_links_or_rows(self):
        data=self.data();data['capabilities'][0]['purpose']='Pipe | [[missing-note]] <script>'
        result=self.propose(data)
        row=result['notes'][-1]['row']
        self.assertNotIn('[[missing-note]]',row)
        self.assertNotIn('<script>',row)
        self.assertEqual(row.count('|'),11)
        for item in result['notes']:
            p=self.vault/item['path'];p.write_text(p.read_text()+'\n'+item['header']+'\n'+item['row']+'\n')
        self.cli('validate','--config',self.config,'--json',expected=0)


if __name__=='__main__':unittest.main()
