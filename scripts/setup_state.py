#!/usr/bin/env python3
"""Local setup journal and activation gate. Records evidence; never calls a provider API.

Use one setup actor per instance. Reconcile uncertain native tool results before retrying.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from engine import ROOT, digest, load_profile, read_json, resources, schedule_rows, validate_ids, validate_bundle


class Journal:
    REQUIRED_CAPABILITIES = ('agent_messaging','group_messaging','durable_instructions','files','scheduling','reply_detection','thumbnail_rendering')

    def __init__(self,path,profile):
        self.profile=load_profile(profile,'deploy')  # validate before creating state or any resource
        self.path=Path(path)
        self.topology=read_json(ROOT/'ids.json')
        self.expected={r['key']:r for r in resources(self.topology)}
        if self.path.exists():
            self.data=read_json(self.path)
            if self.data.get('schema_version')!=1:raise ValueError('Unsupported journal schema')
            if self.data['profile_hash']!=digest(self.profile):
                previously_active=self.data['activation'] in ('enabled','needs_pause')
                self.data['profile_hash']=digest(self.profile)
                self.invalidate()
                self.data['activation']='needs_pause' if previously_active else 'inactive'
                self.save()
        else:
            self.data={'schema_version':1,'profile_hash':digest(self.profile),'resources':{},'capabilities':{},
                       'routines':{},'bundle':None,'test':None,'activation':'inactive','activation_receipt':None}
            self.save()

    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,temp=tempfile.mkstemp(prefix='.state-',dir=self.path.parent)
        try:
            with os.fdopen(fd,'w') as f:
                json.dump(self.data,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
            os.replace(temp,self.path)
        finally:
            if os.path.exists(temp):os.unlink(temp)

    def invalidate(self):
        self.data.update(bundle=None,test=None)
        for row in self.data['routines'].values():
            row.pop('hash',None)
        for row in self.data['resources'].values():
            row.pop('installed',None);row.pop('verified',None)

    def mutable(self):
        if self.data['activation'] in ('enabled','needs_pause'):
            raise ValueError('Pause this deployment’s actual routines and record pause evidence before changing configuration')

    @staticmethod
    def evidence(value):
        if not isinstance(value,str) or not value.strip():raise ValueError('An observed tool result or explicit human verification receipt is required')

    def pending_resources(self):
        return [key for key in self.expected if key not in self.data['resources']]

    def bind(self,key,resource_id,ownership,evidence):
        self.evidence(evidence)
        if key not in self.expected:raise ValueError('Unknown resource key')
        if ownership not in ('created','selected'):raise ValueError('Ownership must be created or explicitly selected; name matching is insufficient')
        if not isinstance(resource_id,str) or not resource_id.strip() or any(x in resource_id for x in '\n\r{}'):raise ValueError('Invalid resource id')
        existing=self.data['resources'].get(key)
        if existing:
            if existing['id']!=resource_id:raise ValueError('Resource already bound; reconcile the existing resource rather than overwrite it')
            return
        self.mutable()
        if resource_id in [r['id'] for r in self.data['resources'].values()]:raise ValueError('Duplicate resource id')
        self.data['resources'][key]={'id':resource_id,'ownership':ownership,'binding_receipt':evidence}
        self.data['test']=None;self.save()

    def replace(self,key,old_id,new_id,ownership,evidence):
        """Explicit recovery after native reconciliation; never an implicit rebind."""
        self.mutable();self.evidence(evidence)
        if ownership not in ('created','selected'):raise ValueError('Replacement must be created for this deployment or explicitly selected')
        if not isinstance(new_id,str) or not new_id.strip() or any(c in new_id for c in '\n\r{}'):
            raise ValueError('Invalid replacement id')
        mapping=self.data['resources'] if key in self.expected else self.data['routines']
        old=mapping.get(key)
        if not old or old['id']!=old_id:raise ValueError('Prior binding does not match; reconcile actual state first')
        if old_id==new_id:raise ValueError('Use existing binding verification for an unchanged id')
        if any(row['id']==new_id for row in [*self.data['resources'].values(),*self.data['routines'].values()]):
            raise ValueError('Replacement id already belongs to another deployment role')
        if any(not row.get('paused',False) for row in self.data['routines'].values()):
            raise ValueError('Verify all instance routines paused before replacing a resource')
        self.invalidate()
        mapping[key]={'id':new_id,'ownership':ownership,'binding_receipt':evidence}
        if mapping is self.data['routines']:mapping[key]['paused']=True
        self.data.setdefault('replacements',[]).append({'key':key,'old_id':old_id,'new_id':new_id,'ownership':ownership,'evidence':evidence})
        self.save()

    def export_ids(self):
        ids=read_json(ROOT/'ids.json')
        for row in resources(ids):row['id']=self.data['resources'].get(row['key'],{}).get('id')
        return ids

    def capability(self,key,available,evidence):
        self.evidence(evidence)
        if not isinstance(available,bool):raise ValueError('Capability availability must be boolean')
        self.data['capabilities'][key]={'available':available,'evidence':evidence}
        if not available:
            self.data['test']=None
            if self.data['activation']=='enabled':self.data['activation']='needs_pause'
        self.save()

    def set_bundle(self,path):
        self.mutable()
        manifest=validate_bundle(path);path=Path(path).resolve()
        ids=validate_ids(self.export_ids(),'deploy')
        if manifest['profile_hash']!=digest(self.profile) or manifest['bindings_hash']!=digest(ids):
            raise ValueError('Bundle was not compiled for this profile and these exact bindings')
        for rel,sha in manifest['files'].items():
            target=(path/rel).resolve()
            if path not in target.parents or not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=sha:
                raise ValueError('Bundle file missing, unsafe or modified: '+rel)
        old=self.data.get('bundle')
        if old and old['hash']==digest(manifest) and old['path']==str(path):return
        self.invalidate()
        self.data['bundle']={'path':str(path),'hash':digest(manifest),'manifest':manifest}
        self.save()

    def bundle_hash(self):
        bundle=self.data.get('bundle')
        if not bundle:raise ValueError('Compile and register the resolved deployment bundle first')
        return bundle['hash']

    def install(self,key,evidence):
        self.mutable();self.evidence(evidence)
        if key not in self.data['resources'] or key.startswith('group_'):raise ValueError('Install requires a bound bot key')
        self.data['resources'][key]['installed']={'hash':self.bundle_hash(),'evidence':evidence}
        self.data['resources'][key].pop('verified',None);self.data['test']=None;self.save()

    def verify(self,key,evidence,members=None):
        self.mutable();self.evidence(evidence)
        if key not in self.data['resources']:raise ValueError('Resource not bound')
        row=self.data['resources'][key];revision=self.bundle_hash()
        row.pop('verified',None);self.data['test']=None
        if key.startswith('group_'):
            expected=[self.data['resources'][k]['id'] for k in self.expected[key]['members']]
            if not isinstance(members,list) or len(members)!=5 or set(members)!=set(expected):
                self.save();raise ValueError('Group membership must be exactly coordinator + four matching specialists')
        elif row.get('installed',{}).get('hash')!=revision:
            self.save();raise ValueError('Bot instructions not installed for this bundle')
        row['verified']={'hash':revision,'evidence':evidence,'members':members};self.save()

    def routine(self,key,resource_id,evidence,time,timezone,days):
        self.mutable();self.evidence(evidence)
        old=self.data['routines'].get(key)
        if old and old['id']!=resource_id:raise ValueError('Routine already bound; reconcile instead of creating a duplicate')
        revision=self.bundle_hash()
        selected={r['key']:r for r in schedule_rows(self.profile) if r['selected']}
        if key not in selected:raise ValueError('Routine phase is not selected')
        want=selected[key]
        if (time,timezone,days)!=(want['time'],want['timezone'],want['days']):raise ValueError('Saved routine schedule does not match profile')
        if not isinstance(resource_id,str) or not resource_id.strip():raise ValueError('Routine id required')
        if any(v['id']==resource_id for k,v in self.data['routines'].items() if k!=key):raise ValueError('Duplicate routine id')
        old=self.data['routines'].get(key)
        if old and old['id']!=resource_id:raise ValueError('Routine already bound; reconcile instead of creating a duplicate')
        self.data['routines'][key]={'id':resource_id,'hash':revision,'evidence':evidence,'time':time,'timezone':timezone,'days':days,'paused':True}
        self.data['test']=None;self.save()

    def record_test(self,kind,passed,evidence):
        self.mutable();self.evidence(evidence)
        if kind not in ('simulation','live') or not isinstance(passed,bool):raise ValueError('Test must be simulation/live with boolean result')
        self.data['test']={'kind':kind,'passed':passed,'evidence':evidence,'hash':self.bundle_hash()};self.save()

    def status(self):
        reasons=[];revision=(self.data.get('bundle') or {}).get('hash')
        if self.data['activation']=='needs_pause':reasons.append('Verify actual routines paused before continuing')
        if not revision:reasons.append('Resolved bundle not registered')
        for key in self.REQUIRED_CAPABILITIES:
            if not self.data['capabilities'].get(key,{}).get('available'):reasons.append('Missing capability: '+key)
        for key in self.expected:
            if self.data['resources'].get(key,{}).get('verified',{}).get('hash')!=revision or not revision:
                reasons.append('Resource not verified for current bundle: '+key)
        for row in schedule_rows(self.profile):
            if row['selected'] and (self.data['routines'].get(row['key'],{}).get('hash')!=revision or not revision):
                reasons.append('Saved routine not verified: '+row['key'])
        test=self.data.get('test') or {}
        if not (test.get('kind')=='live' and test.get('passed') is True and test.get('hash')==revision and revision):
            reasons.append('Passing live acceptance evidence required; offline simulation is insufficient')
        # A bundle edited after installation invalidates activation, even with old receipts.
        bundle=self.data.get('bundle')
        if bundle:
            try:
                path=Path(bundle['path'])
                if digest(validate_bundle(path))!=revision:raise ValueError('Manifest changed')
                for rel,sha in bundle['manifest']['files'].items():
                    target=(path/rel).resolve()
                    if path not in target.parents or hashlib.sha256(target.read_bytes()).hexdigest()!=sha:raise ValueError('Bundle changed')
            except (OSError,ValueError):reasons.append('Bundle missing or changed; compile and reinstall')
        return {'ready_to_activate':not reasons,'activation':self.data['activation'],'pending':reasons,'pending_resources':self.pending_resources()}

    def activate(self,evidence):
        self.evidence(evidence)
        if not self.status()['ready_to_activate']:raise ValueError('Activation prerequisites incomplete; inspect status')
        self.data['activation']='enabled';self.data['activation_receipt']=evidence
        for row in schedule_rows(self.profile):
            if row['selected']:self.data['routines'][row['key']]['paused']=False
        self.save()

    def pause(self,evidence):
        self.evidence(evidence)
        self.data['activation']='inactive';self.data['activation_receipt']=evidence
        for row in self.data['routines'].values():row['paused']=True
        self.save()


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--profile',type=Path,required=True)
    a.add_argument('--state',type=Path,required=True)
    sub=a.add_subparsers(dest='command',required=True)
    sub.add_parser('status');sub.add_parser('export-ids')
    b=sub.add_parser('bind');b.add_argument('key');b.add_argument('id');b.add_argument('--ownership',choices=('created','selected'),required=True);b.add_argument('--evidence',required=True)
    b=sub.add_parser('replace');b.add_argument('key');b.add_argument('old_id');b.add_argument('new_id');b.add_argument('--ownership',choices=('created','selected'),required=True);b.add_argument('--evidence',required=True)
    b=sub.add_parser('capability');b.add_argument('key');b.add_argument('--available',choices=('yes','no'),required=True);b.add_argument('--evidence',required=True)
    b=sub.add_parser('bundle');b.add_argument('path',type=Path)
    b=sub.add_parser('install');b.add_argument('key');b.add_argument('--evidence',required=True)
    b=sub.add_parser('verify');b.add_argument('key');b.add_argument('--members',nargs='*');b.add_argument('--evidence',required=True)
    b=sub.add_parser('routine');b.add_argument('key');b.add_argument('id');b.add_argument('--time',required=True);b.add_argument('--timezone',required=True);b.add_argument('--days',required=True);b.add_argument('--evidence',required=True)
    b=sub.add_parser('test');b.add_argument('--kind',choices=('simulation','live'),required=True);b.add_argument('--passed',choices=('yes','no'),required=True);b.add_argument('--evidence',required=True)
    for name in ('activate','pause'):
        b=sub.add_parser(name);b.add_argument('--evidence',required=True)
    args=a.parse_args()
    try:
        j=Journal(args.state,read_json(args.profile))
        cmd=args.command
        if cmd=='bind':j.bind(args.key,args.id,args.ownership,args.evidence)
        elif cmd=='replace':j.replace(args.key,args.old_id,args.new_id,args.ownership,args.evidence)
        elif cmd=='capability':j.capability(args.key,args.available=='yes',args.evidence)
        elif cmd=='bundle':j.set_bundle(args.path)
        elif cmd=='install':j.install(args.key,args.evidence)
        elif cmd=='verify':j.verify(args.key,args.evidence,args.members)
        elif cmd=='routine':j.routine(args.key,args.id,args.evidence,args.time,args.timezone,args.days)
        elif cmd=='test':j.record_test(args.kind,args.passed=='yes',args.evidence)
        elif cmd=='activate':j.activate(args.evidence)
        elif cmd=='pause':j.pause(args.evidence)
        print(json.dumps(j.export_ids() if cmd=='export-ids' else j.status(),indent=2))
    except (ValueError,KeyError,TypeError,OSError) as e:a.exit(1,f'Setup state error: {e}\n')


if __name__=='__main__':main()
