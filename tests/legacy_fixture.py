"""Explicit synthetic pre-native installations for compatibility regressions.

Production never performs this conversion. Tests that exercise customized JSON
settings/schema use this helper instead of expecting fresh installs to emit JSON.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from asklib import configuration, schema


def legacy_workspace(ws, setup=False):
    ws=Path(ws)
    if (ws/'ask.json').exists():
        return
    data=configuration.read(ws)
    data['schema_path']='note.schema.json'
    if not setup:
        data.pop('ask_version',None)
        data.pop('template_version',None)
        data.pop('validation',None)
        data['access']['write']=[]
    (ws/'ask.json').write_text(json.dumps(data,indent=2)+'\n')
    (ws/'note.schema.json').write_text(json.dumps(schema.SCHEMA, indent=2)+'\n')
    manifest=ws/'system/install-manifest.json'
    value=json.loads(manifest.read_text());value.pop('workspace_layout',None)
    manifest.write_text(json.dumps(value,indent=2)+'\n')
    import ask
    (ws/'AGENTS.md').write_text(ask.adapter(dict(data,vault=ws/data['vault_root']),ws/'ask.json',ws/'system/scripts/ask.py'))


def legacy_result(result,args):
    if args and args[0] in ('init','setup') and '--workspace' in args:
        ws=Path(args[args.index('--workspace')+1])
        if not (ws/'ask.json').exists() and (ws/'system/install-manifest.json').exists():
            if args[0]=='init' and result.returncode==0:
                legacy_workspace(ws)
            elif args[0]=='setup':
                data=json.loads(result.stdout)
                if data.get('initial_checkpoint_files'):
                    legacy_workspace(ws,setup=True)
                    data['initial_checkpoint_files']+=['ask.json','note.schema.json']
                    result.stdout=json.dumps(data)
    return result
