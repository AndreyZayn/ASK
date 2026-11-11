"""Privacy baseline regressions using synthetic repositories and fake data."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class PrivacyBaselineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name).resolve()
        (self.root/'scripts').mkdir()
        shutil.copyfile(ROOT/'scripts/privacy_check.py',self.root/'scripts/privacy_check.py')
        self.git('init')
        self.git('config','user.name','Synthetic Tester')
        self.git('config','user.email','test@example.invalid')
        self.git('config','commit.gpgsign','false')
        self.git('add','.')
        # Construct a fake personal-domain identity without publishing a real one.
        self.fake_email='synthetic-test'+'@'+'gmail.com'
        self.git('commit','-m','Synthetic historical record','--author','Synthetic <'+self.fake_email+'>')
        self.old=self.git('rev-parse','HEAD').stdout.strip()
        self.baseline=self.root/'baseline.json'
        self.baseline.write_text(json.dumps({'author_commits':[self.old]}))

    def tearDown(self):self.tmp.cleanup()

    def git(self,*args):
        result=subprocess.run(['git',*args],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        return result

    def scan(self,*args):
        return subprocess.run([sys.executable,str(self.root/'scripts/privacy_check.py'),'--history','--history-ref','HEAD',*map(str,args)],cwd=self.root,capture_output=True,text=True)

    def test_strict_scan_reports_existing_history_and_baseline_still_reports_it(self):
        strict=self.scan();self.assertEqual(strict.returncode,1)
        result=self.scan('--history-author-baseline',self.baseline)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn(self.old,result.stdout)
        self.assertIn('1 reviewed historical; 0 new',result.stdout)
        self.assertNotIn(self.fake_email,result.stdout)

    def test_new_commit_with_same_personal_identity_is_not_exempt(self):
        (self.root/'note.md').write_text('Synthetic note')
        self.git('add','note.md')
        self.git('commit','-m','New record','--author','Synthetic <'+self.fake_email+'>')
        result=self.scan('--history-author-baseline',self.baseline)
        self.assertEqual(result.returncode,1)
        self.assertIn('1 reviewed historical; 1 new',result.stdout)

    def test_new_secret_in_history_still_fails_after_removal(self):
        (self.root/'fixture.txt').write_text('sk-'+'a'*30)
        self.git('add','fixture.txt');self.git('commit','-m','Synthetic fixture')
        self.git('rm','fixture.txt');self.git('commit','-m','Remove fixture')
        result=self.scan('--history-author-baseline',self.baseline)
        self.assertEqual(result.returncode,1)
        self.assertIn('fixture.txt: service-key',result.stdout)
        self.assertNotIn('sk-'+'a'*30,result.stdout)

    def test_baseline_cannot_exempt_file_patterns_or_short_commit_ids(self):
        for data in ({'author_commits':['*']},{'author_commits':[self.old[:12]]},{'author_commits':[self.old],'files':['fixture.txt']},[]):
            self.baseline.write_text(json.dumps(data))
            self.assertEqual(self.scan('--history-author-baseline',self.baseline).returncode,2)


if __name__=='__main__':unittest.main()
