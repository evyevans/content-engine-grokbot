#!/usr/bin/env python3
"""Compile neutral previews or an isolated, fully bound deployment bundle."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from engine import context, digest, fenced_after, load_profile, read_json, render, resources, schedule_rows, validate_ids, validate_bundle


def profile_text(row, desc, ctx):
    name=ctx['coordinator.name'] if row['key']=='head' else row['name']
    return f"""# Bot profile – {name}

Generated preview or deployment instructions. Edit source specs and the user profile, then rebuild.
Resource key: `{row['key']}` · Binding: `{ctx['bindings.'+row['key']]}`

Install the following instructions through the harness's supported durable-instruction mechanism.
On current personal Grok Bots, send them in chat, ask the bot to retain its role and reopen its master configuration; verify receipt. A shared Bot may expose different controls.

`````text
{desc}
`````
"""


def generate(p,ids,dest):
    ctx=context(p,ids)
    for directory in ('agents','playbooks','templates','architecture','examples'):
        for f in sorted((ROOT/directory).rglob('*.md')):
            target=dest/f.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(render(f.read_text(),ctx))
    (dest/'01_MASTER_CONFIG.md').write_text(render((ROOT/'01_MASTER_CONFIG.md').read_text(),ctx))
    out=dest/'bot_profiles';out.mkdir()
    intro = (f"Project: {ctx['brand.name']}. Creator: {ctx['creator.display_name']}. Niche: {ctx['niche']}. "
             f"Audience: {ctx['audience']}. Pillars: {ctx['pillars']}. Voice: {ctx['voice.style']}. "
             f"Language: {ctx['voice.language']}. Time zone: {ctx['timezone']}. "
             f"Coordinator: {ctx['coordinator.name']} ({ctx['bindings.head']}).\n"
             'The resolved 01_MASTER_CONFIG.md is authoritative. Reopen it and your role references before work. '
             'If files are unavailable, request the attached copies; do not infer missing context from old memory.\n')
    master=(dest/'01_MASTER_CONFIG.md').read_text()
    modules=['head_strategist','daily_briefing_orchestrator','comment_strategy','strategy_rd','brand_voice_cta','analytics_feedback']
    prompts=[]
    for slug in modules:
        blocks=fenced_after((dest/'agents'/f'{slug}.md').read_text(),r'^## System prompt')
        if len(blocks)!=1:raise ValueError(f'{slug}: expected one system prompt')
        prompts.append(f'===== {slug} =====\n'+blocks[0])
    coordinator=intro+'\n'+'\n\n'.join(prompts)+'\n\n===== RESOLVED MASTER =====\n'+master
    (out/'coordinator.md').write_text(profile_text(ids['head'],coordinator,ctx))
    for platform in ('tiktok','ig','yt'):
        doc=(dest/'agents'/f'team_{platform}.md').read_text()
        shared=fenced_after(doc,r'^## Shared team context')[0]
        for row in [x for x in ids['specialists'] if x['team']=={'tiktok':'Team TikTok','ig':'Team IG','yt':'Team Youtube'}[platform]]:
            marker=f'## Specialist {row["order"]} – '
            section=doc[doc.index(marker):]
            prompt=fenced_after(section,r'^\*\*System prompt')[0]
            desc=intro+f"\nTEAM CONTEXT:\n{shared}\n\nYOUR ROLE:\n{prompt}\n\n===== RESOLVED MASTER =====\n{master}"
            (out/Path(row['profile']).name).write_text(profile_text(row,desc,ctx))
    row=ids['standalone'][0]
    prompt=fenced_after((dest/'agents/ig_thumbnail_designer.md').read_text(),r'^## System prompt')[0]
    (out/'ig_thumbnail.md').write_text(profile_text(row,intro+'\n'+prompt+'\n\n'+master,ctx))
    (out/'routines.md').write_text((dest/'templates/routines.md').read_text())
    for name,value in [('ids.json',ids),('schedule.json',schedule_rows(p))]:
        (dest/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
    manifest={'project':'grok-bot-content-engine','schema_version':1,'profile_hash':digest(p),'bindings_hash':digest(ids),
              'files':{str(f.relative_to(dest)):__import__('hashlib').sha256(f.read_bytes()).hexdigest()
                       for f in sorted(dest.rglob('*')) if f.is_file()}}
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',type=Path)
    parser.add_argument('--ids',type=Path,default=ROOT/'ids.json')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--mode',choices=('template','deploy'),default='template')
    a=parser.parse_args()
    try:
        if a.mode=='deploy' and (a.profile is None or a.output is None):raise ValueError('Deploy requires --profile and --output')
        p=load_profile(a.profile,a.mode);ids=validate_ids(read_json(a.ids),a.mode)
        if a.output and a.output.is_symlink():raise ValueError('Output must not be a symlink')
        output=a.output.resolve() if a.output else None
        if output and (output==ROOT or output in ROOT.parents or (ROOT in output.parents and '.local' not in output.relative_to(ROOT).parts)):
            raise ValueError('Output must be outside the source tree or inside .local/')
        if output and output.exists():validate_bundle(output)
        parent=output.parent if output else ROOT
        parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.engine-build-',dir=parent) as temp:
            staged=Path(temp)/'bundle';staged.mkdir();generate(p,ids,staged)
            if a.mode=='deploy':
                for f in staged.rglob('*.md'):
                    if 'UNBOUND:' in f.read_text():raise ValueError(f'Unbound reference in {f.name}')
            if output:
                backup=Path(temp)/'previous'
                if output.exists():os.replace(output,backup)
                try:os.replace(staged,output)
                except BaseException:
                    if backup.exists():os.replace(backup,output)
                    raise
            else:
                # No-output template mode refreshes only committed generated previews.
                for f in staged.joinpath('bot_profiles').glob('*.md'):shutil.copyfile(f,ROOT/'bot_profiles'/f.name)
                for stale in (ROOT/'bot_profiles').glob('*.md'):
                    if not (staged/'bot_profiles'/stale.name).exists():stale.unlink()
        print('OK: '+(str(output) if output else 'neutral bot_profiles previews'))
    except (ValueError,KeyError,TypeError,OSError,IndexError) as e:
        parser.exit(1,f'Build failed: {e}\n')


if __name__=='__main__':main()
