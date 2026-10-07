#!/usr/bin/env python3
"""Conservative public-source checks. Findings show paths/rules, never secrets."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

RULES = {
    'machine-home': re.compile(rb'/(?:Users|home)/[A-Za-z][A-Za-z0-9_.-]*/'),
    'private-key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'github-token': re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})'),
    'service-key': re.compile(rb'(?:sk-(?:proj-)?[A-Za-z0-9_-]{24,}|AKIA[A-Z0-9]{16})'),
    'personal-email': re.compile(rb'[A-Za-z0-9._%+-]+@(?:gmail|icloud|yahoo|hotmail|outlook|protonmail|proton)\.[A-Za-z]+'),
}


def main():
    p=argparse.ArgumentParser();p.add_argument('--history',action='store_true');p.add_argument('--history-ref',help='Scan this real branch ancestry instead of all local refs');args=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    def git(*argv):
        return subprocess.check_output(['git',*argv],cwd=str(root))
    findings=[]
    paths=git('ls-files','--cached','--others','--exclude-standard','-z').split(b'\0')
    for raw in paths:
        if not raw: continue
        path=root/raw.decode()
        if not path.is_file(): continue
        content=path.read_bytes()
        for label,pat in RULES.items():
            if pat.search(content): findings.append('%s: %s'%(raw.decode(),label))
    if args.history:
        for commit in git('rev-list',args.history_ref or '--all').decode().splitlines():
            identity=git('show','-s','--format=%an <%ae>%n%cn <%ce>',commit)
            if RULES['personal-email'].search(identity): findings.append('%s: personal author/committer email'%commit[:12])
            for entry in git('ls-tree','-r','-z',commit).split(b'\0'):
                if not entry: continue
                meta,path=entry.split(b'\t',1); mode,kind,oid=meta.split()
                if kind!=b'blob':continue
                content=git('cat-file','blob',oid.decode())
                for label,pat in RULES.items():
                    if pat.search(content): findings.append('%s:%s: %s'%(commit[:12],path.decode(),label))
    for finding in sorted(set(findings)): print(finding)
    print('Public privacy scan: %d finding(s)'%len(set(findings)))
    return 1 if findings else 0

if __name__=='__main__':sys.exit(main())
