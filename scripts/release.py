#!/usr/bin/env python3
"""Build and inspect a deterministic public archive from an explicit file allowlist."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {'.md','.py','.json','.sh','.txt'}
ALLOWED_SUFFIXES = TEXT_SUFFIXES | {'.ttf','.jpg','.png'}
PRIVATE_PARTS = {'.git','.local','.venv','__pycache__','logs','models','proposed'}
UUID = re.compile(rb'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',re.I)


def allowlist():
    value=json.loads((ROOT/'config/release-files.json').read_text())
    if value.get('schema_version')!=1 or not isinstance(value.get('files'),list):
        raise ValueError('Invalid release allowlist')
    names=value['files']
    if len(names)!=len(set(names)) or not names:raise ValueError('Release allowlist is empty or has duplicates')
    for name in names:
        rel=PurePosixPath(name)
        if not isinstance(name,str) or rel.is_absolute() or '..' in rel.parts or '\\' in name or str(rel)!=name:
            raise ValueError('Unsafe release entry')
        if set(rel.parts)&PRIVATE_PARTS or name=='config/user.json' or name.startswith('.env'):
            raise ValueError('Private file on release allowlist: '+name)
        if rel.suffix not in ALLOWED_SUFFIXES and name not in ('LICENSE','.gitignore'):
            raise ValueError('Unapproved release format: '+name)
        path=ROOT
        for part in rel.parts:
            path=path/part
            if path.is_symlink():raise ValueError('Symlink on release allowlist: '+name)
        if not path.is_file():raise ValueError('Missing release file: '+name)
    return sorted(names)


def inspect_payload(name,data):
    if re.search(rb'https?://(?:docs|drive)\.google\.com/',data,re.I):
        raise ValueError('Private document reference in '+name)
    # Public tests use synthetic UUID fixtures only. No account bindings may ship.
    if any(not value.startswith(b'00000000-0000-4000-8000-') for value in UUID.findall(data)):
        raise ValueError('Account identifier in '+name)
    if name.endswith('.png'):
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Invalid PNG: '+name)
        pos=8
        while pos+12<=len(data):
            size=int.from_bytes(data[pos:pos+4],'big'); kind=data[pos+4:pos+8]
            if pos+12+size>len(data):raise ValueError('Malformed PNG metadata: '+name)
            if kind in (b'tEXt',b'zTXt',b'iTXt',b'eXIf'):raise ValueError('Unapproved PNG metadata: '+name)
            pos+=12+size
            if kind==b'IEND':break
        else:raise ValueError('Incomplete PNG: '+name)
    if name.endswith('.jpg'):
        # Reject EXIF/IPTC/XMP/comments rather than publish a photo's hidden metadata.
        if not data.startswith(b'\xff\xd8'):raise ValueError('Invalid JPEG: '+name)
        pos=2
        while pos < len(data):
            if data[pos]!=255:break
            while pos < len(data) and data[pos]==255:pos+=1
            marker=data[pos];pos+=1
            if marker in (0xda,0xd9):break
            if marker in (0x01,*range(0xd0,0xd8)):continue
            length=int.from_bytes(data[pos:pos+2],'big')
            if length<2 or pos+length>len(data):raise ValueError('Malformed JPEG metadata: '+name)
            if marker in (0xe1,0xed,0xfe):raise ValueError('Unapproved image metadata: '+name)
            pos+=length


def inspect_archive(path,names,expected):
    with zipfile.ZipFile(path) as z:
        if sorted(z.namelist())!=sorted(names+['RELEASE_MANIFEST.json']):raise ValueError('Archive membership differs from allowlist')
        if z.testzip():raise ValueError('Archive CRC check failed')
        manifest=json.loads(z.read('RELEASE_MANIFEST.json'))
        if manifest['files']!=expected:raise ValueError('Archive manifest mismatch')
        for name in names:
            data=z.read(name)
            if hashlib.sha256(data).hexdigest()!=expected[name]:raise ValueError('Archive checksum mismatch: '+name)
            inspect_payload(name,data)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args()
    try:
        output=a.output.resolve()
        if output==ROOT or ROOT in output.parents:raise ValueError('Release output must be outside the source folder')
        names=allowlist()
        # Verify before packaging. A failing check cannot replace an existing archive.
        r=subprocess.run([sys.executable,str(ROOT/'scripts/verify.py'),'--mode','template'],capture_output=True,text=True)
        if r.returncode:raise ValueError('Template verification failed:\n'+r.stdout+r.stderr)
        payload={name:(ROOT/name).read_bytes() for name in names}
        for name,data in payload.items():inspect_payload(name,data)
        hashes={name:hashlib.sha256(data).hexdigest() for name,data in payload.items()}
        manifest=json.dumps({'schema_version':1,'project':'Grok Bot Content Engine','version':'2.0.0','files':hashes},indent=2,sort_keys=True).encode()+b'\n'
        output.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.engine-release-',dir=output.parent) as td:
            staged=Path(td)/'release.zip'
            with zipfile.ZipFile(staged,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
                for name,data in list(payload.items())+[('RELEASE_MANIFEST.json',manifest)]:
                    info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                    info.external_attr=((0o100755 if name.endswith('.sh') else 0o100644)<<16);z.writestr(info,data)
            inspect_archive(staged,names,hashes)
            os.replace(staged,output)
        print(f'OK: {len(names)} allowlisted files; archive inspected; SHA256 {hashlib.sha256(output.read_bytes()).hexdigest()}\n{output}')
    except (ValueError,KeyError,TypeError,OSError,zipfile.BadZipFile) as e:parser.exit(1,f'Release failed: {e}\n')


if __name__=='__main__':main()
