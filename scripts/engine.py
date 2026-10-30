"""Shared configuration, binding, and deterministic template operations (stdlib only)."""
import copy
import hashlib
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r'\{\{\s*([\w.]+)\s*\}\}')
SLUG = re.compile(r'^[a-z][a-z0-9_-]*$')
PLATFORMS = ('tiktok', 'ig', 'yt')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def merge(base, override):
    out = copy.deepcopy(base)
    for key, value in override.items():
        out[key] = merge(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) else copy.deepcopy(value)
    return out


def read_json(path):
    return json.loads(Path(path).read_text())


def load_profile(path=None, mode='deploy'):
    base = read_json(ROOT / 'config/user.example.json')
    p = merge(base, path if isinstance(path, dict) else read_json(path)) if path else base
    if p['schema_version'] != 1:
        raise ValueError('Unsupported profile schema_version; expected 1')
    # Compile tokens in input are ambiguous and could otherwise be expanded as instructions.
    def has_tokens(value):
        if isinstance(value, str): return '{{' in value or '}}' in value
        if isinstance(value, dict): return any(has_tokens(v) for v in value.values())
        if isinstance(value, list): return any(has_tokens(v) for v in value)
        return False
    if has_tokens(p):
        raise ValueError('Profile values cannot contain compile-time template tokens')
    for field in ('creator', 'coordinator', 'brand', 'voice', 'schedule', 'phases', 'production', 'approvals', 'banks', 'safety', 'handles', 'goals', 'post_windows'):
        if not isinstance(p[field], dict):
            raise ValueError(f'{field} must be an object')
    def text(value, field, optional=False, blank=False):
        if optional and value is None:return
        if not isinstance(value,str) or (not blank and not value.strip()):
            raise ValueError(f'{field} must be a string'+(' or null' if optional else ''))
    def texts(value,field):
        if not isinstance(value,list) or any(not isinstance(v,str) or not v.strip() for v in value):
            raise ValueError(f'{field} must be a list of nonempty strings')
    text(p['brand']['name'],'brand.name',blank=True)
    text(p['brand']['signature'],'brand.signature',blank=True)
    for key in ('style','language'):text(p['voice'][key],'voice.'+key)
    for key in ('signature_phrases','banned_phrases'):texts(p['voice'][key],'voice.'+key)
    texts(p['creator']['confirmed_facts'],'creator.confirmed_facts')
    for key in ('creator','operator'):text(p['approvals'][key],'approvals.'+key)
    for key in ('topics_to_avoid','additional_rules'):texts(p['safety'][key],'safety.'+key)
    texts(p['banks']['watch_list'],'banks.watch_list')
    if not isinstance(p['banks']['hashtags'],dict):raise ValueError('banks.hashtags must be an object')
    for key in PLATFORMS:
        texts(p['banks']['hashtags'].get(key),'banks.hashtags.'+key)
        text(p['handles'].get(key),'handles.'+key,optional=True)
        text(p['post_windows'].get(key),'post_windows.'+key,optional=True)
    for key in ('outcome','deadline'):text(p['goals'][key],'goals.'+key,optional=True)
    cadence=p['goals']['cadence_per_week']
    if cadence is not None and (isinstance(cadence,bool) or not isinstance(cadence,int) or not 1<=cadence<=7):
        raise ValueError('goals.cadence_per_week must be 1–7 or null')
    for field in ('followers',):
        targets=p['goals'][field]
        if targets is not None and (not isinstance(targets,dict) or any(k not in PLATFORMS or isinstance(v,bool) or not isinstance(v,int) or v<0 for k,v in targets.items())):
            raise ValueError('goals.followers must map platform keys to nonnegative integers, or null')
    if p['statistics'] is not None and not isinstance(p['statistics'],dict):raise ValueError('statistics must be an object or null')
    for field in ('niche', 'audience', 'timezone'):
        if p[field] is not None and (not isinstance(p[field], str) or not p[field].strip()):
            raise ValueError(f'{field} must be a nonempty string or null')
        if mode == 'deploy' and not p[field]:
            raise ValueError(f'Missing required profile field: {field}')
    if p['timezone']:
        try:
            ZoneInfo(p['timezone'])
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError('timezone must be an IANA time zone') from None
    for key in ('display_name',):
        if not isinstance(p['creator'][key], str) or not p['creator'][key].strip():
            raise ValueError('creator.display_name must be nonempty')
    if not isinstance(p['coordinator']['name'], str) or not p['coordinator']['name'].strip():
        raise ValueError('coordinator.name must be nonempty')
    for key in ('pillars',):
        if not isinstance(p[key], list) or any(not isinstance(x, str) or not x.strip() for x in p[key]):
            raise ValueError(f'{key} must be a list of nonempty strings')
    if not isinstance(p['voice']['swearing'], bool):
        raise ValueError('voice.swearing must be boolean')
    for phase in ('2', '3'):
        if not isinstance(p['phases'][phase], bool):
            raise ValueError(f'phases.{phase} must be boolean')
    if p['phases']['3'] and not p['phases']['2']:
        raise ValueError('Phase 3 requires Phase 2')
    if p['schedule']['days'] not in ('daily', 'weekdays'):
        raise ValueError('schedule.days must be daily or weekdays')
    time_keys = ('checkin', 'nudge', 'idea', 'comments', 'research', 'analytics')
    for key in time_keys:
        value = p['schedule'][key]
        required = key in time_keys[:3] or (key in ('comments', 'research') and p['phases']['2']) or (key == 'analytics' and p['phases']['3'])
        if value is not None and (not isinstance(value, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value)):
            raise ValueError(f'schedule.{key} must be HH:MM, 24-hour local time')
        if mode == 'deploy' and required and value is None:
            raise ValueError(f'Missing required schedule.{key}')
    times = [p['schedule'][k] for k in time_keys[:3]]
    if all(times) and not times[0] < times[1] < times[2]:
        raise ValueError('Schedule must have checkin < nudge < idea on the same local day')
    # Compare actual selected weekly occurrences, including the Sunday/Monday boundary.
    occurrences=[]
    for row in schedule_rows(p):
        if not row['selected'] or row['time'] is None:continue
        days=range(7) if row['days']=='daily' else range(5) if row['days']=='weekdays' else (6,)
        minute=int(row['time'][:2])*60+int(row['time'][3:])
        occurrences.extend(day*1440+minute for day in days)
    occurrences.sort()
    gaps=[b-a for a,b in zip(occurrences,occurrences[1:])]
    if len(occurrences)>1:gaps.append(10080-occurrences[-1]+occurrences[0])
    if any(gap<5 for gap in gaps):
        raise ValueError('Selected routines on overlapping days must be at least 5 minutes apart')
    for key in ('workspace_root', 'output_dir', 'constraints'):
        if not isinstance(p['production'][key], str) or not p['production'][key].strip():
            raise ValueError(f'production.{key} must be a nonempty string')
    for platform in PLATFORMS:
        if not isinstance(p['banks']['hashtags'].get(platform), list):
            raise ValueError(f'banks.hashtags.{platform} must be a list')
    return p


def resources(ids):
    return [ids['head']] + ids['specialists'] + ids['standalone'] + ids['group_chats']


def validate_ids(ids, mode='deploy'):
    canonical = read_json(ROOT / 'ids.json')
    for platform,label in [('tiktok','Team TikTok'),('ig','Team IG'),('yt','Team Youtube')]:
        team=[r for r in canonical['specialists'] if r['team']==label]
        groups=[r for r in canonical['group_chats'] if r['key']=='group_'+platform]
        if len(team)!=4 or sorted(r['order'] for r in team)!=[1,2,3,4] or len(groups)!=1:
            raise ValueError('Invalid public platform topology')
        expected_members=['head']+[r['key'] for r in sorted(team,key=lambda r:r['order'])]
        if groups[0]['members']!=expected_members:raise ValueError('Invalid public group membership')
    rows = resources(ids)
    if len(rows) != 17 or len(ids['specialists']) != 12 or len(ids['standalone']) != 1 or len(ids['group_chats']) != 3:
        raise ValueError('Expected 14 bots and 3 group chats')
    actual = {r['key']: r for r in rows}
    expected = {r['key']: r for r in resources(canonical)}
    if set(actual) != set(expected) or len(actual) != 17:
        raise ValueError('Resource logical keys must match the public topology')
    for key, row in actual.items():
        for field in ('profile', 'members', 'team', 'order', 'slug'):
            if row.get(field) != expected[key].get(field):
                raise ValueError(f'Incorrect topology for {key}.{field}')
    values = [r['id'] for r in rows if r['id'] is not None]
    if any(not isinstance(v,str) or not v.strip() or any(c in v for c in '\n\r{}') for v in values):
        raise ValueError('Resource ids must be nonempty single-line strings')
    if len(set(values)) != len(values):
        raise ValueError('Duplicate resource ids')
    if mode == 'deploy' and len(values) != 17:
        raise ValueError('All 17 resource bindings are required before deployment compilation')
    return ids


def schedule_rows(p):
    rows=[]
    for key in ('checkin','nudge','idea','comments','research','analytics'):
        phase = 1 if key in ('checkin','nudge','idea') else 3 if key == 'analytics' else 2
        rows.append({'key':key,'owner':'head','time':p['schedule'][key],
                     'days':'Sunday' if key in ('research','analytics') else p['schedule']['days'],
                     'timezone':p['timezone'], 'phase':phase,
                     'selected': phase == 1 or p['phases'][str(phase)], 'enabled':False})
    return rows


def context(p, ids):
    ctx={}
    def flatten(prefix,value):
        if isinstance(value,dict):
            for k,v in value.items():flatten(f'{prefix}.{k}' if prefix else k,v)
        else:
            ctx[prefix] = ('unknown' if value is None else '; '.join(map(str,value)) if isinstance(value,list) else str(value))
    flatten('',p)
    ctx['brand.name'] = p['brand']['name'] or 'User content project'
    ctx['pillars'] = '; '.join(p['pillars']) or 'Choose a configured pillar suited to the input'
    ctx['timezone'] = p['timezone'] or 'SET_TIME_ZONE'
    for key,value in p['schedule'].items():
        ctx['schedule.'+key] = value or 'NOT_SCHEDULED'
    ctx['profile.json'] = json.dumps(p,indent=2,ensure_ascii=False)
    ctx['bindings.table'] = '\n'.join(f"| {r['key']} | {r['id'] or 'UNBOUND:'+r['key']} |" for r in resources(ids))
    for r in resources(ids):ctx['bindings.'+r['key']] = r['id'] or 'UNBOUND:'+r['key']
    ctx['post_windows.summary'] = '; '.join(f"{k}: {p['post_windows'][k] or 'ask the user; no tested window yet'}" for k in PLATFORMS)
    return ctx


def render(text, ctx):
    def sub(m):
        if m[1] not in ctx:
            raise ValueError(f'Unknown compile-time token: {m[1]}')
        return ctx[m[1]]
    result = TOKEN.sub(sub,text)
    if '{{' in result or '}}' in result:
        raise ValueError('Unresolved or malformed compile-time token')
    return result


def fenced_after(text, marker):
    """Extract complete prompts, allowing nested triple-backtick copy fields."""
    blocks=[]; lines=text.splitlines(); i=0
    while i < len(lines):
        if re.match(marker,lines[i]):
            i+=1
            while i < len(lines) and not re.match(r'^`{3,}',lines[i]):i+=1
            if i == len(lines):raise ValueError('Prompt marker has no fenced block')
            fence=re.match(r'^(`{3,})',lines[i])[1]; i+=1; start=i
            while i < len(lines) and lines[i] != fence:i+=1
            if i == len(lines):raise ValueError('Unterminated prompt block')
            blocks.append('\n'.join(lines[start:i]))
        i+=1
    return blocks


def validate_bundle(path):
    """Validate generated ownership, exact membership, safe paths and current checksums."""
    path=Path(path)
    if path.is_symlink():raise ValueError('Bundle directory must not be a symlink')
    path=path.resolve()
    manifest=read_json(path/'manifest.json')
    if not isinstance(manifest,dict) or manifest.get('project')!='grok-bot-content-engine' or manifest.get('schema_version')!=1:
        raise ValueError('Directory is not an owned content-engine bundle')
    if not isinstance(manifest.get('files'),dict) or not manifest['files']:
        raise ValueError('Generated bundle manifest is missing file membership')
    for field in ('profile_hash','bindings_hash'):
        if not isinstance(manifest.get(field),str) or not re.fullmatch('[0-9a-f]{64}',manifest[field]):
            raise ValueError('Invalid bundle '+field)
    declared=set(manifest['files'])|{'manifest.json'}
    actual=set()
    for f in path.rglob('*'):
        if f.is_symlink():raise ValueError('Bundle contains a symlink')
        if f.is_file():actual.add(str(f.relative_to(path)))
    if actual!=declared:raise ValueError('Bundle contains missing or untracked files; preserve them before replacing')
    for rel,sha in manifest['files'].items():
        if not isinstance(rel,str) or Path(rel).is_absolute() or '..' in Path(rel).parts or str(Path(rel))!=rel:
            raise ValueError('Unsafe manifest path')
        target=path/rel
        if path not in target.resolve().parents or hashlib.sha256(target.read_bytes()).hexdigest()!=sha:
            raise ValueError('Bundle file missing or changed: '+rel)
    return manifest
