import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_engine import ROOT, profile, bindings

class VerificationTests(unittest.TestCase):
    def test_deploy_verifier_checks_manifest_and_bound_topology(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);(td/'p.json').write_text(json.dumps(profile()));(td/'i.json').write_text(json.dumps(bindings()))
            r=subprocess.run([sys.executable,str(ROOT/'bot_profiles/_build_profiles.py'),'--mode','deploy','--profile',str(td/'p.json'),'--ids',str(td/'i.json'),'--output',str(td/'bundle')],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            cmd=[sys.executable,str(ROOT/'scripts/verify.py'),'--mode','deploy','--bundle',str(td/'bundle')]
            r=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            (td/'bundle/bot_profiles/coordinator.md').write_text('tampered')
            r=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0)
            self.assertIn('FAIL',r.stdout)

if __name__=='__main__':unittest.main()
