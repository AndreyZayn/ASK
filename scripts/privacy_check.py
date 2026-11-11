#!/usr/bin/env python3
"""Conservative public-source checks. Findings show paths/rules, never secrets."""
import argparse
import json
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
    p=argparse.ArgumentParser();p.add_argument('--history',action='store_true');p.add_argument('--history-ref',help='Scan this real branch ancestry instead of all local refs');p.add_argument('--history-author-baseline', type=Path, help='Reviewed exact commit IDs with existing author-email findings; all findings remain reported');args=p.parse_args()
    baseline=set()
    approved_sources=[]
    if args.history_author_baseline:
        if not args.history: p.error('--history-author-baseline requires --history')
        try:
            data=json.loads(args.history_author_baseline.read_text(encoding='utf-8'))
            if not isinstance(data,dict) or 'author_commits' not in data or set(data)-{'author_commits','allowed_author_email_from_commits'}:
                raise ValueError('baseline contains unsupported fields')
            commits=data['author_commits']
            approved_sources=data.get('allowed_author_email_from_commits',[])
            for values in (commits,approved_sources):
                if not isinstance(values,list) or not all(isinstance(c,str) and re.fullmatch(r'[0-9a-f]{40}',c) for c in values):
                    raise ValueError('baseline must contain exact full commit IDs only')
            baseline={c+': personal author/committer email' for c in commits}
        except (OSError,ValueError,TypeError) as e:
            p.error('invalid history author baseline: %s'%e)
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
    approved_findings=set()
    if args.history:
        commits=git('rev-list',args.history_ref or '--all').decode().splitlines()
        if not set(approved_sources).issubset(set(commits)):
            p.error('approved author source must be in the scanned ancestry')
        approved_emails=set()
        for source in approved_sources:
            email=git('show','-s','--format=%ae',source).strip()
            if not RULES['personal-email'].fullmatch(email):
                p.error('approved author source must have a personal-email author')
            approved_emails.add(email)
        for commit in commits:
            identity=git('show','-s','--format=%an <%ae>%n%cn <%ce>',commit)
            emails=set(RULES['personal-email'].findall(identity))
            if emails:
                finding='%s: personal author/committer email'%commit
                findings.append(finding)
                if emails.issubset(approved_emails): approved_findings.add(finding)
            for entry in git('ls-tree','-r','-z',commit).split(b'\0'):
                if not entry: continue
                meta,path=entry.split(b'\t',1); mode,kind,oid=meta.split()
                if kind!=b'blob':continue
                content=git('cat-file','blob',oid.decode())
                for label,pat in RULES.items():
                    if pat.search(content): findings.append('%s:%s: %s'%(commit[:12],path.decode(),label))
    unique=set(findings)
    known=unique & (baseline | approved_findings)
    new=unique - known
    for finding in sorted(unique):
        print(finding + (' (reviewed historical baseline)' if finding in known else ''))
    print('Public privacy scan: %d finding(s); %d reviewed historical; %d new'%(len(unique),len(known),len(new)))
    return 1 if new else 0

if __name__=='__main__':sys.exit(main())
