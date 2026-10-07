#!/usr/bin/env python3
"""ASK local workspace setup, validation, bootstrap, and graph export."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import sys
from datetime import date

RELATIONS = ('governed_by', 'depends_on', 'derived_from', 'associated_with')
DEFAULT_BOOTSTRAP = ['date.md', 'INDEX.md', 'agents.md', 'knowledge-map.md']
ATTACHMENT_SUFFIXES = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.avif', '.tif', '.tiff', '.pdf'}

class AskError(Exception):
    pass


def inside(child, parent):
    try:
        Path(child).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def safe_rel(value, label, allow_dot=False):
    if not isinstance(value, str) or not value or '\\' in value:
        raise AskError('%s must be a non-empty relative path' % label)
    p = Path(value)
    if p.is_absolute() or any(x == '..' for x in p.parts) or (not allow_dot and str(p) == '.'):
        raise AskError('%s must stay within its root' % label)
    return p


def ensure_no_symlink_path(path):
    """Reject symlinks in every existing component before normalizing a path."""
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    cur = Path(p.anchor)
    for part in p.parts[1:]:
        if part in ('', '.'):
            continue
        if part == '..':
            cur = cur.parent
            continue
        cur = cur / part
        if cur.is_symlink():
            raise AskError('symlink path is not allowed: %s' % cur)


def check_inside_symlinks(root, path):
    root = Path(root).absolute()
    path = Path(path).absolute()
    try: rel = path.relative_to(root)
    except ValueError: raise AskError('path escapes vault')
    cur = root
    for part in rel.parts:
        cur = cur / part
        if cur.is_symlink(): raise AskError('symlink path is not allowed: %s' % cur)


def adapter(config, cfgpath):
    vault = Path(config['vault']).resolve()
    cfgpath = Path(cfgpath).resolve()
    boot = config['bootstrap_files']
    read = config['access']['read']; write = config['access']['write']
    command = 'python3 %s validate --config %s' % (shlex.quote(str(Path(__file__).resolve())), shlex.quote(str(cfgpath)))
    lines = ['# Workspace agent bootstrap', '',
             'The owner configured this workspace adapter. Follow the notes in this order:']
    lines += ['%d. `%s`' % (i, vault / p) for i, p in enumerate(boot, 1)]
    lines += ['', 'Vault root: `%s`.' % vault,
              'Configuration: `%s`.' % cfgpath,
              'Validate the vault with: `%s`' % command,
              '', 'Access paths below are relative to the vault root (`.` means the whole vault).',
              'Declared read paths: %s.' % (', '.join('`%s`' % x for x in read) or '(none)'),
              'Declared write paths: %s.' % (', '.join('`%s`' % x for x in write) or '(none)'),
              '', '**These declarations are guidance only. They do not enforce runtime permissions. The owner must explicitly grant and constrain actual runtime filesystem permissions.**',
              'After the ordered bootstrap, use the knowledge map and linked notes for routing.']
    return '\n'.join(lines) + '\n'


def init(args):
    dist = Path(__file__).resolve().parents[1]
    ws = Path(args.workspace).expanduser().absolute()
    ensure_no_symlink_path(ws)
    if inside(ws, dist):
        raise AskError('workspace must be outside the distribution')
    vault_rel = safe_rel(args.vault_name or 'Knowledge Base', 'vault name')
    if not ws.exists():
        # parent may be created, but reject symlink ancestry above was checked
        ws.mkdir(parents=True)
    if not ws.is_dir():
        raise AskError('workspace must be a directory')
    vault = ws / vault_rel
    ensure_no_symlink_path(vault)
    if ws.exists(): check_inside_symlinks(ws, vault)
    if not inside(vault, ws) or vault.resolve() == ws.resolve():
        raise AskError('vault name must name a directory inside the workspace')
    planned = [ws/'ask.json', ws/'note.schema.json', ws/'AGENTS.md']
    template_root = dist / 'templates' / 'vault'
    files = sorted(p for p in template_root.rglob('*') if p.is_file())
    planned += [vault_rel / p.relative_to(template_root) for p in files]
    # Handle nested vault path by joining relative planned paths.
    planned = [p if p.is_absolute() else ws/p for p in planned]
    for p in planned:
        ensure_no_symlink_path(p)
        if inside(p, vault): check_inside_symlinks(vault, p)
        if p.exists():
            raise AskError('output already exists: %s' % p)
    for p in planned:
        p.parent.mkdir(parents=True, exist_ok=True)
    cfg = {'version': 1, 'vault_root': vault_rel.as_posix(), 'schema_path': 'note.schema.json',
           'bootstrap_files': DEFAULT_BOOTSTRAP, 'access': {'read': ['.'], 'write': []}}
    payloads = [(ws/'ask.json', json.dumps(cfg, indent=2) + '\n'),
                (ws/'note.schema.json', (dist/'schemas'/'note.schema.json').read_text(encoding='utf-8')),
                (ws/'AGENTS.md', adapter(dict(cfg, vault=vault), ws/'ask.json'))]
    for src in files:
        dest = vault / src.relative_to(template_root)
        payloads.append((dest, src.read_text(encoding='utf-8').replace('{{DATE}}', date.today().isoformat())))
    created=[]
    try:
        for path, content in payloads:
            with path.open('x', encoding='utf-8', newline='') as f:
                f.write(content)
            created.append(path)
    except Exception:
        for p in created:
            try: p.unlink()
            except OSError: pass
        raise
    print('Initialized workspace at %s' % ws)


def load_config(path):
    cp = Path(path).expanduser().absolute()
    ensure_no_symlink_path(cp)
    try: cfg=json.loads(cp.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e: raise AskError('cannot read config: %s' % e)
    if not isinstance(cfg, dict) or type(cfg.get('version')) is not int or cfg.get('version') != 1:
        raise AskError('config version must be the integer 1')
    if not isinstance(cfg.get('vault_root'), str) or not cfg['vault_root']: raise AskError('vault_root must be a path')
    raw=Path(cfg['vault_root']).expanduser()
    vault=raw if raw.is_absolute() else cp.parent/raw
    ensure_no_symlink_path(vault)
    if not vault.is_dir(): raise AskError('vault_root is not a directory')
    schema_rel=safe_rel(cfg.get('schema_path'), 'schema_path')
    schema=cp.parent/schema_rel
    ensure_no_symlink_path(schema)
    if not schema.is_file(): raise AskError('schema file does not exist')
    boot=cfg.get('bootstrap_files', DEFAULT_BOOTSTRAP)
    access=cfg.get('access', {'read':['.'], 'write':[]})
    if not isinstance(boot,list) or not boot: raise AskError('bootstrap_files must be a non-empty list')
    boot=[safe_rel(x,'bootstrap path').as_posix() for x in boot]
    if len(set(boot))!=len(boot): raise AskError('bootstrap_files contains duplicate entries')
    if not isinstance(access,dict) or set(access)-{'read','write'}: raise AskError('access must contain read and write lists')
    norm={}
    for k in ('read','write'):
        vals=access.get(k,[])
        if not isinstance(vals,list): raise AskError('access.%s must be a list' % k)
        norm[k]=[]
        for x in vals:
            rel=safe_rel(x,'access.%s path'%k,allow_dot=True)
            p=vault/rel
            if not inside(p,vault): raise AskError('access path escapes vault')
            check_inside_symlinks(vault, p)
            norm[k].append(rel.as_posix())
    for x in boot:
        p=vault/safe_rel(x,'bootstrap path')
        check_inside_symlinks(vault, p)
        if not p.is_file() or not inside(p,vault): raise AskError('configured bootstrap note missing: %s'%x)
        if not any(r=='.' or x==r or x.startswith(r+'/') for r in norm['read']):
            raise AskError('bootstrap note %s is not covered by access.read paths'%x)
    return {'config_path':cp,'vault':vault,'schema_path':schema,'vault_root':cfg['vault_root'],
            'bootstrap_files':boot,'access':norm}


def validate_schema(path):
    try: schema=json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e: raise AskError('cannot read schema: %s'%e)
    notes={'$schema','title','description'}
    scalar_keys={'string':{'enum','minLength','format'},'boolean':{'enum'}}
    def check_scalar(s, name):
        typ=s.get('type')
        if typ not in scalar_keys: raise AskError('%s: type must be string or boolean' % name)
        unknown=set(s)-notes-{'type'}-scalar_keys[typ]
        if unknown: raise AskError('%s: unsupported schema keyword for %s: %s' % (name, typ, sorted(unknown)[0]))
        if 'enum' in s:
            py=str if typ=='string' else bool
            if not isinstance(s['enum'],list) or not s['enum'] or not all(type(x) is py for x in s['enum']):
                raise AskError('%s: enum must be a non-empty array of %s values' % (name, typ))
        if 'minLength' in s and (type(s['minLength']) is not int or s['minLength']<0): raise AskError('%s: invalid minLength' % name)
        if 'format' in s and s['format'] not in ('date','wikilink-note'): raise AskError('%s: unsupported schema format' % name)
    def check_property(s, name):
        if not isinstance(s,dict): raise AskError('schema entries must be objects')
        if s.get('type')!='array': return check_scalar(s, name)
        unknown=set(s)-notes-{'type','items','minItems','uniqueItems'}
        if unknown: raise AskError('%s: unsupported schema keyword for array: %s' % (name, sorted(unknown)[0]))
        if 'minItems' in s and (type(s['minItems']) is not int or s['minItems']<0): raise AskError('%s: invalid minItems' % name)
        if 'uniqueItems' in s and not isinstance(s['uniqueItems'],bool): raise AskError('uniqueItems must be boolean')
        if 'items' in s:
            if not isinstance(s['items'],dict): raise AskError('schema entries must be objects')
            check_scalar(s['items'], name + ' items')
    if not isinstance(schema,dict): raise AskError('schema entries must be objects')
    unknown=set(schema)-notes-{'type','required','properties','additionalProperties'}
    if unknown: raise AskError('unsupported schema keyword: %s'%sorted(unknown)[0])
    if schema.get('type')!='object' or not isinstance(schema.get('properties'),dict): raise AskError('schema root must be an object schema')
    for k,v in schema['properties'].items(): check_property(v, k)
    req=schema.get('required',[])
    if not isinstance(req,list) or not all(isinstance(x,str) for x in req) or len(set(req))!=len(req): raise AskError('required must be an array of unique strings')
    for x in req:
        if x not in schema['properties']: raise AskError('required field is not a declared property: %s'%x)
    if 'additionalProperties' in schema and not isinstance(schema['additionalProperties'],bool): raise AskError('additionalProperties must be boolean')
    return schema


def parse_scalar(s):
    s=s.strip()
    if not s: return ''
    if s.startswith(('&','*','!','|','>')): raise ValueError('anchors, aliases, tags, and block scalars are unsupported')
    if s[0] in ('"', "'"):
        q=s[0]
        if len(s)<2 or s[-1]!=q: raise ValueError('unterminated quoted string')
        val=s[1:-1]
        if q=='"':
            try: return json.loads(s)
            except ValueError: raise ValueError('invalid quoted string')
        return val.replace("''", "'")
    if ': ' in s or s.startswith(('{','[','?','- ')): raise ValueError('invalid unquoted scalar')
    if s in ('true','false'): return s=='true'
    return s


def parse_frontmatter(text):
    if not text.startswith('---\n') and not text.startswith('---\r\n'): raise ValueError('missing YAML frontmatter')
    lines=text.splitlines()
    if not lines or lines[0]!='---': raise ValueError('missing frontmatter opening marker')
    try: end=lines.index('---',1)
    except ValueError: raise ValueError('missing frontmatter closing marker')
    data={}; key=None; block=[]
    def finish():
        nonlocal key,block
        if key is not None: data[key]=block
        key=None; block=[]
    for line in lines[1:end]:
        if '\t' in line: raise ValueError('tabs are unsupported')
        if not line.strip(): continue
        item=re.match(r'(?:  )?- (.*)$', line)
        if item:
            if key is None or not isinstance(block,list): raise ValueError('list item without key')
            item_raw=item.group(1).strip()
            if key in RELATIONS and not (item_raw.startswith("'") or item_raw.startswith('"')):
                raise ValueError('relation items must be quoted wikilinks')
            block.append(parse_scalar(item_raw)); continue
        if line.startswith(' '): raise ValueError('nested mappings are unsupported')
        finish()
        if ':' not in line: raise ValueError('expected key: value')
        k,raw=line.split(':',1); k=k.strip(); raw=raw.strip()
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*',k): raise ValueError('invalid key')
        if k in data or k==key: raise ValueError('duplicate key: %s'%k)
        if raw=='': key=k; block=[]; continue
        if raw.startswith('[') and raw.endswith(']'):
            inner=raw[1:-1].strip()
            if not inner: val=[]
            else:
                # Flow arrays are comma separated quoted strings only.
                parts=[]; pos=0
                token_re=re.compile(r'\s*("(?:\\.|[^"\\])*"|\'[^\']*(?:\'\'[^\']*)*\')\s*(?:,|$)')
                while pos < len(inner):
                    mt=token_re.match(inner,pos)
                    if not mt: raise ValueError('flow arrays must contain quoted strings')
                    parts.append(mt.group(1)); pos=mt.end()
                val=[parse_scalar(x) for x in parts]
            data[k]=val
        else: data[k]=parse_scalar(raw)
    finish()
    return data, '\n'.join(lines[end+1:])


def mask_code(body):
    """Blank fenced blocks and inline code spans while preserving line layout."""
    lines = body.splitlines(keepends=True)
    visible = []
    fence_char = None
    fence_length = 0
    for line in lines:
        stripped = line.lstrip(' ')
        indent = len(line) - len(stripped)
        run = re.match(r'(`{3,}|~{3,})', stripped) if indent <= 3 else None
        if fence_char is None:
            if run:
                marker = run.group(1)
                fence_char, fence_length = marker[0], len(marker)
                visible.append(''.join('\n' if c == '\n' else ' ' for c in line))
            else:
                visible.append(line)
            continue
        closing = run and run.group(1)[0] == fence_char and len(run.group(1)) >= fence_length
        if closing and not stripped[len(run.group(1)):].strip():
            fence_char = None
            fence_length = 0
        visible.append(''.join('\n' if c == '\n' else ' ' for c in line))
    body = ''.join(visible)

    masked = []
    i = 0
    while i < len(body):
        if body[i] != '`':
            masked.append(body[i])
            i += 1
            continue
        end = i + 1
        while end < len(body) and body[end] == '`':
            end += 1
        run_length = end - i
        search = end
        close_start = None
        close_end = None
        while search < len(body):
            tick = body.find('`', search)
            if tick < 0:
                break
            tick_end = tick + 1
            while tick_end < len(body) and body[tick_end] == '`':
                tick_end += 1
            if tick_end - tick == run_length:
                close_start, close_end = tick, tick_end
                break
            search = tick_end
        if close_start is None:
            # An unmatched run is ordinary Markdown text; later runs may still pair.
            masked.append(body[i:end])
            i = end
            continue
        masked.append(''.join('\n' if c == '\n' else ' ' for c in body[i:close_end]))
        i = close_end
    return ''.join(masked)


def note_files(vault):
    found=[]; attachments=[]
    def walk_error(error):
        raise OSError('cannot scan vault: %s' % error)
    for root, dirs, files in os.walk(vault, followlinks=False, onerror=walk_error):
        rp=Path(root)
        dirs[:]=[d for d in dirs if not d.startswith('.')]
        for d in list(dirs):
            p=rp/d
            if p.is_symlink(): raise AskError('symlink in vault: %s'%p)
        for f in files:
            if f.startswith('.'): continue
            p=rp/f
            if p.is_symlink(): raise AskError('symlink in vault: %s'%p)
            if p.suffix.lower()=='.md': found.append(p)
            elif p.suffix.lower() in ATTACHMENT_SUFFIXES: attachments.append(p)
    return sorted(found), sorted(attachments)


def resolve_link(raw, source, vault, files, relation=False, attachments=()):
    value=raw
    if relation:
        m=re.fullmatch(r'\[\[([^\]|#^]+)\]\]', value)
        if not m: raise ValueError('relation must be a quoted whole-note wikilink')
        target=m.group(1)
        if target.startswith('/') or any(x=='..' for x in Path(target).parts) or target.lower().endswith('.md'):
            raise ValueError('relation path must be vault-relative and extensionless')
    else:
        if value.startswith('!'): value=value[1:]
        if not (value.startswith('[[') and value.endswith(']]')): return None
        target=value[2:-2].split('|',1)[0].split('#',1)[0].split('^',1)[0].strip()
    if not target: return None
    if target.startswith(('http://','https://','mailto:')): return None if not relation else (_ for _ in ()).throw(ValueError('external relation'))
    rel=Path(target)
    if relation and rel.is_absolute(): raise ValueError('absolute relation path')
    suffix=rel.suffix.lower()
    if not relation and suffix in ATTACHMENT_SUFFIXES: pool=attachments; name=rel.name
    elif not relation and suffix=='.md': pool=files; name=rel.name
    elif not suffix: pool=files; name=rel.name+'.md'
    else: raise ValueError('unsupported link suffix: %s' % suffix)
    pool={p.resolve() for p in pool}
    if rel.is_absolute(): candidates=[rel.parent/name]
    elif relation: candidates=[vault/rel.parent/name]
    else: candidates=[source.parent/rel.parent/name, vault/rel.parent/name]
    resolved=[]
    for q in candidates:
        try:
            ensure_no_symlink_path(q)
            if inside(q, vault): check_inside_symlinks(vault, q)
        except AskError: raise ValueError('link traverses symlink')
        if q.is_file() and inside(q,vault):
            rr=q.resolve()
            if rr in pool and rr not in resolved: resolved.append(rr)
    # Basename lookup applies only to bare names; an explicit directory or a
    # relative path that misses (or escapes the vault) is an error.
    if not resolved and not relation and '/' not in target and len(rel.parts)==1:
        resolved=sorted(p for p in pool if p.name==name)
    if len(resolved)!=1: raise ValueError('link target %s is %s'%(target,'missing' if not resolved else 'ambiguous'))
    return resolved[0]


def issue(issues, file, msg): issues.append({'file':str(file),'message':msg})


def validate_vault(ctx):
    schema=validate_schema(ctx['schema_path']); issues=[]; metas={}; bodies={}; titles={}
    try: files,attachments=note_files(ctx['vault'])
    except AskError as e: return {'counts':{'notes':0,'errors':1},'issues':[{'file':'','message':str(e)}]}, {'nodes':[],'edges':[]}
    properties=schema['properties']; required=schema.get('required',[])
    for p in files:
        rel=p.relative_to(ctx['vault']).as_posix()
        try: text=p.read_text(encoding='utf-8')
        except (OSError,UnicodeError) as e: issue(issues,rel,'cannot read note: %s'%e); continue
        try: meta,body=parse_frontmatter(text)
        except ValueError as e: issue(issues,rel,'frontmatter: %s'%e); continue
        metas[p]=meta; bodies[p]=body
        for k in required:
            if k not in meta: issue(issues,rel,'missing required field: %s'%k)
        if schema.get('additionalProperties') is False:
            for k in meta:
                if k not in properties: issue(issues,rel,'unknown field: %s'%k)
        def check_value(spec, val, label):
            typ=spec.get('type')
            if not {'string':isinstance(val,str),'boolean':isinstance(val,bool)}[typ]:
                issue(issues,rel,'%s must be %s'%(label,typ)); return
            if 'enum' in spec and val not in spec['enum']: issue(issues,rel,'%s is not an allowed value'%label)
            if typ!='string': return
            if len(val)<spec.get('minLength',0): issue(issues,rel,'%s is too short'%label)
            if spec.get('format')=='date':
                try:
                    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',val): raise ValueError()
                    date.fromisoformat(val)
                except ValueError: issue(issues,rel,'%s must be a valid YYYY-MM-DD date'%label)
            if spec.get('format')=='wikilink-note':
                try:
                    target=resolve_link(val,p,ctx['vault'],files,True)
                    if target==p.resolve(): issue(issues,rel,'%s relation cannot point to itself'%label)
                except ValueError as e: issue(issues,rel,'%s: %s'%(label,e))
        for k,val in meta.items():
            spec=properties.get(k)
            if not spec: continue
            if spec['type']!='array': check_value(spec,val,k); continue
            if not isinstance(val,list): issue(issues,rel,'%s must be array'%k); continue
            if len(val)<spec.get('minItems',0): issue(issues,rel,'%s has too few items'%k)
            if spec.get('uniqueItems') and len(set(map(repr,val)))!=len(val): issue(issues,rel,'%s has duplicate items'%k)
            for x in val:
                if 'items' in spec: check_value(spec['items'],x,'%s item'%k)
        if 'title' in meta and isinstance(meta['title'],str):
            t=meta['title'].casefold()
            if t in titles: issue(issues,rel,'duplicate title also used by %s'%titles[t])
            else: titles[t]=rel
        if rel.endswith('INDEX.md') and meta.get('kind')!='index': issue(issues,rel,'INDEX.md requires kind: index')
        if rel.startswith('Agents/rules/') and not rel.endswith('INDEX.md') and meta.get('kind')!='rule': issue(issues,rel,'non-index Agents/rules notes require kind: rule')
    edges=[]
    for p,meta in metas.items():
        src=p.relative_to(ctx['vault']).as_posix()
        for prop in RELATIONS:
            for x in meta.get(prop,[]) if isinstance(meta.get(prop),list) else []:
                try:
                    target=resolve_link(x,p,ctx['vault'],files,True)
                    if target!=p.resolve(): edges.append({'source':src,'target':target.relative_to(ctx['vault'].resolve()).as_posix(),'type':prop})
                except ValueError: pass # detailed issue was recorded during schema validation
        body=mask_code(bodies[p])
        for m in re.finditer(r'!?\[\[[^\]]+\]\]',body):
            raw=m.group(0)
            # A wikilink also declared as metadata on this note is represented only by its relation edge.
            try:
                target=resolve_link(raw,p,ctx['vault'],files,False,attachments)
                if target:
                    edges.append({'source':src,'target':target.relative_to(ctx['vault'].resolve()).as_posix(),'type':'navigational'})
            except ValueError as e: issue(issues,src,str(e))
    # Remove duplicate navigational links while preserving deterministic graph.
    edges=sorted({(e['source'],e['target'],e['type']) for e in edges})
    edges=[{'source':a,'target':b,'type':c} for a,b,c in edges]
    nodes=[]
    for p in files:
        meta=metas.get(p,{})
        nodes.append({'id':p.relative_to(ctx['vault']).as_posix(),'type':'note','metadata':{k:meta[k] for k in ('title','description','kind','scope','lifecycle_status','updated','tags','project','domain','canonical') if k in meta}})
    for p in attachments:
        nodes.append({'id':p.relative_to(ctx['vault']).as_posix(),'type':'attachment','metadata':{'kind':'attachment'}})
    nodes.sort(key=lambda n:n['id'])
    return {'counts':{'notes':len(files),'errors':len(issues)},'issues':issues}, {'nodes':nodes,'edges':edges}


def output_guard(path, ctx):
    p=Path(path).expanduser().absolute(); dist=Path(__file__).resolve().parents[1]
    ensure_no_symlink_path(p)
    if inside(p,dist) or inside(p,ctx['vault']): raise AskError('output must be outside the distribution and vault')
    if p.exists(): raise AskError('output already exists: %s'%p)
    return p


def write_new(path, content):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='') as f: f.write(content)


def run(args):
    if args.command=='init': init(args); return 0
    ctx=None if getattr(args,'staged',False) else load_config(args.config)
    if args.command=='bootstrap':
        text=adapter({'vault':ctx['vault'],'bootstrap_files':ctx['bootstrap_files'],'access':ctx['access']},ctx['config_path'])
        if args.output: write_new(output_guard(args.output,ctx),text)
        else: sys.stdout.write(text)
        return 0
    from asklib import validation
    report,graph=validation.validate(sys.modules[__name__], args.config, staged=getattr(args,'staged',False), files=getattr(args,'files',None))
    if args.command=='validate':
        if args.json: sys.stdout.write(json.dumps(report,sort_keys=True)+'\n')
        else:
            for i in report['issues']: print('%s: %s'%(i['file'],i['message']),file=sys.stderr)
            if not report['issues']: print('Vault is valid (%d notes).'%report['counts']['notes'])
        return 2 if report.get('configuration_error') else (1 if report['counts']['errors'] else 0)
    if report['counts']['errors']:
        print('ask.py: vault has integrity findings; graph was not written', file=sys.stderr)
        for item in report['issues']:
            print('%s: %s' % (item['file'], item['message']), file=sys.stderr)
        return 1
    payload=json.dumps(graph,indent=2,sort_keys=True)+'\n'
    if args.output: write_new(output_guard(args.output,ctx),payload)
    else: sys.stdout.write(payload)
    return 0


def main():
    if len(sys.argv)>1 and sys.argv[1] in {'setup','doctor','agent','checkpoint','sync','write','backup'}:
        from asklib import v1
        return v1.dispatch(sys.modules[__name__], sys.argv[1:])
    parser=argparse.ArgumentParser(prog='ask.py'); sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('init'); p.add_argument('--workspace',required=True); p.add_argument('--vault-name');
    for name in ('validate','bootstrap','graph'):
        p=sub.add_parser(name); p.add_argument('--config',required=True)
        if name in ('bootstrap','graph'): p.add_argument('--output')
        if name=='validate':
            p.add_argument('--json',action='store_true')
            p.add_argument('--staged',action='store_true')
            p.add_argument('--files',nargs='+')
    args=parser.parse_args()
    try: return run(args)
    except AskError as e:
        if getattr(args,'command',None)=='validate' and getattr(args,'json',False):
            sys.stdout.write(json.dumps({'counts':{'notes':0,'errors':1},'issues':[{'file':'','message':str(e)}]},sort_keys=True)+'\n')
        else: print('ask.py: %s'%e,file=sys.stderr)
        return 2
    except OSError as e:
        message = 'I/O error: %s' % e
        if getattr(args,'command',None)=='validate' and getattr(args,'json',False):
            sys.stdout.write(json.dumps({'counts':{'notes':0,'errors':1},'issues':[{'file':'','message':message}]},sort_keys=True)+'\n')
        else: print('ask.py: %s' % message,file=sys.stderr)
        return 2
    except (UnicodeError, ValueError, TypeError, KeyError, IndexError) as e:
        message = 'invalid input: %s' % e
        if getattr(args,'command',None)=='validate' and getattr(args,'json',False):
            sys.stdout.write(json.dumps({'counts':{'notes':0,'errors':1},'issues':[{'file':'','message':message}]},sort_keys=True)+'\n')
        else: print('ask.py: %s' % message,file=sys.stderr)
        return 2

if __name__=='__main__': sys.exit(main())
