#!/usr/bin/env python3
"""Read-only structural checks for public templates or a compiled deployment bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from engine import ROOT, context, fenced_after, load_profile, read_json, resources, validate_ids, validate_bundle


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('template','deploy'),default='template')
    parser.add_argument('--bundle',type=Path)
    a=parser.parse_args()
    results=[]
    def check(name,callback):
        try:
            detail=callback()
            results.append((name,True,detail or ''))
        except (ValueError,KeyError,TypeError,OSError,AssertionError,IndexError) as e:
            results.append((name,False,str(e)))
    def require(ok,detail):
        if not ok:raise ValueError(detail)
    target=a.bundle.resolve() if a.bundle else ROOT
    if a.mode=='deploy' and a.bundle is None:parser.error('--mode deploy requires --bundle')

    def topology():
        ids=validate_ids(read_json(target/'ids.json'),a.mode)
        if a.mode=='template':require(all(r['id'] is None for r in resources(ids)),'Public topology must have null account IDs')
        require(len([x for x in ids['specialists'] if x['order']==4])==3,'Expected one lead per platform')
    check('14 bots / 3 groups / exact membership topology',topology)

    def prompts():
        profiles=sorted((target/'bot_profiles').glob('*.md'))
        require(len(profiles)==15,'Expected 14 bot profiles and routine instructions')
        for row in resources(read_json(target/'ids.json')):
            if row['key'].startswith('group_'):continue
            p=target/row['profile'];text=p.read_text()
            require(len(fenced_after(text,r'^Install the following'))==1,f'Missing complete fenced instructions: {p.name}')
            binding=row['id'] if a.mode=='deploy' else 'UNBOUND:'+row['key']
            require(binding in text,f'Profile lacks its binding: {p.name}')
        for name in ('head_strategist','daily_briefing_orchestrator','comment_strategy','strategy_rd','brand_voice_cta','analytics_feedback','ig_thumbnail_designer'):
            require(len(fenced_after((target/'agents'/f'{name}.md').read_text(),r'^## System prompt'))==1,'Invalid module prompt: '+name)
        for platform in ('tiktok','ig','yt'):
            text=(target/'agents'/f'team_{platform}.md').read_text()
            require(len(fenced_after(text,r'^## Shared team context'))==1,'Missing shared team context')
            require(len(fenced_after(text,r'^\*\*System prompt'))==4,'Expected four specialist prompts')
        require(len(fenced_after((target/'bot_profiles/routines.md').read_text(),r'^## (checkin|nudge|idea|comments|research|analytics)'))==6,'Expected six routine prompt templates')
    check('Fenced role, team and routine instruction blocks',prompts)

    def limits():
        for name,required in {
            'tiktok_team_lead':['3 to 5','FORMAT (HARD FAIL)','Post window'],
            'ig_team_lead':['HARD cap 5','FORMAT (HARD FAIL)','Alt text'],
            'yt_team_lead':['EXACTLY 3 hashtags','no #shorts','FORMAT (HARD FAIL)','Post window'],
            'coordinator':['HARD FAIL','Last 3 CTAs','SAME','DIFFERENT']}.items():
            text=(target/'bot_profiles'/f'{name}.md').read_text()
            for term in required:require(term in text,f'{name} missing {term}')
        require('## 10. Hashtag banks' in (target/'01_MASTER_CONFIG.md').read_text(),'Hashtag bank absent')
    check('Platform editorial caps and copy-format quality gates',limits)

    def layers():
        names=['relevance','triggers','workflows','agents','tools_matrix','memory','security_governance','rnd_loop','human_in_the_loop','success_rubric']
        for n,name in enumerate(names,1):require((target/'architecture'/f'{n:02d}_{name}.md').is_file(),'Missing architecture layer')
        require((target/'architecture/README.md').is_file(),'Missing architecture index')
    check('Ten architecture layers and index',layers)

    if a.mode=='template':
        def syntax():
            from release import allowlist
            for name in allowlist():
                p=ROOT/name
                if p.suffix=='.py':compile(p.read_text(),name,'exec')
                if p.suffix=='.sh':
                    r=subprocess.run(['bash','-n',str(p)],capture_output=True,text=True)
                    require(r.returncode==0,r.stderr)
        check('Public Python and shell syntax',syntax)

        def privacy():
            from release import allowlist,inspect_payload
            for name in allowlist():inspect_payload(name,(ROOT/name).read_bytes())
        check('Allowlisted public content / no live bindings or document links',privacy)

        def links():
            from release import allowlist
            for name in allowlist():
                if not name.endswith('.md'):continue
                for url in re.findall(r'\]\(([^)\s]+)\)',(ROOT/name).read_text()):
                    if url.startswith(('https://','http://','#','mailto:')):continue
                    path=(ROOT/name).parent/url.split('#')[0]
                    require(path.exists(),f'Broken local link: {name}: {url}')
        check('Local Markdown links',links)

        def identical():
            load_profile(mode='template')
            with tempfile.TemporaryDirectory() as td:
                out=Path(td)/'bundle'
                r=subprocess.run([sys.executable,str(ROOT/'bot_profiles/_build_profiles.py'),'--mode','template','--output',str(out)],capture_output=True,text=True)
                require(r.returncode==0,r.stderr)
                files=sorted((ROOT/'bot_profiles').glob('*.md'))
                for p in files:require(p.read_bytes()==(out/'bot_profiles'/p.name).read_bytes(),'Generated profile drift: '+p.name)
        check('Neutral profile rebuild is byte-identical',identical)
    else:
        def manifest():
            m=validate_bundle(target)
            require(m.get('schema_version')==1,'Invalid manifest schema')
            declared=set(m['files'])|{'manifest.json'}
            actual={str(p.relative_to(target)) for p in target.rglob('*') if p.is_file()}
            require(actual==declared,'Bundle file set differs from manifest')
            for rel,sha in m['files'].items():
                p=(target/rel).resolve()
                require(target in p.parents and not (target/rel).is_symlink(),'Unsafe manifest path')
                require(hashlib.sha256(p.read_bytes()).hexdigest()==sha,'Changed bundle file: '+rel)
            require(m['bindings_hash']==__import__('engine').digest(read_json(target/'ids.json')),'Bindings hash mismatch')
        check('Bundle manifest / all file checksums / bindings hash',manifest)

        def resolved():
            for p in target.rglob('*.md'):
                text=p.read_text()
                require('{{' not in text and '}}' not in text,'Unresolved compile token: '+str(p.relative_to(target)))
                require('UNBOUND:' not in text,'Unbound resource: '+str(p.relative_to(target)))
            rows=read_json(target/'schedule.json')
            for row in rows:
                require(row['enabled'] is False,'Generated schedules must remain inactive')
                if row['selected']:
                    require(row['time'] and row['timezone'],'Selected schedule incomplete')
                    __import__('zoneinfo').ZoneInfo(row['timezone'])
        check('Resolved context and inactive IANA schedules',resolved)

    for name,ok,detail in results:
        print(f'{"PASS" if ok else "FAIL"}  {name}'+(f' — {detail}' if detail else ''))
    passed=sum(ok for _,ok,_ in results)
    print(f'\n{passed}/{len(results)} checks passed ({a.mode}).')
    return 0 if passed==len(results) else 1


if __name__=='__main__':sys.exit(main())
