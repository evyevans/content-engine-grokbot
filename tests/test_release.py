import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]

class ReleaseTests(unittest.TestCase):
    def test_finished_archive_excludes_private_and_unapproved_paths(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'release.zip'
            # Use a copied source so test writes cannot alter a user's actual local profile.
            import shutil
            repo=Path(td)/'repo';shutil.copytree(ROOT,repo,ignore=shutil.ignore_patterns('.local','__pycache__','.venv','models'))
            (repo/'config/user.json').write_text('{"private":true}')
            (repo/'.local').mkdir(exist_ok=True);(repo/'.local/state.json').write_text('private state')
            (repo/'notes.docx').write_text('private')
            r=subprocess.run([sys.executable,str(repo/'scripts/release.py'),'--output',str(out)],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr+r.stdout)
            with zipfile.ZipFile(out) as z:
                names=z.namelist()
                self.assertIn('LICENSE',names)
                self.assertIn('skills/setup-content-engine/SKILL.md',names)
                self.assertNotIn('config/user.json',names)
                self.assertFalse(any('.local' in n or n.endswith('.docx') for n in names))
                self.assertIn('RELEASE_MANIFEST.json',names)
                self.assertTrue((z.getinfo('tools/thumbnail/render.sh').external_attr >> 16) & 0o111)
                self.assertTrue(all(not n.startswith('/') and '..' not in Path(n).parts for n in names))

if __name__=='__main__':unittest.main()
