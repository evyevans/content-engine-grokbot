import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

class RendererTests(unittest.TestCase):
    def test_custom_brand_and_no_brand_with_all_layouts(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);base=td/'base.jpg'
            Image.new('RGB',(1080,1920),(85,100,120)).save(base)
            def run(name,template='C',extra=()):
                out=td/(name+'.jpg')
                r=subprocess.run([sys.executable,str(ROOT/'tools/thumbnail/render.py'),'-t',template,'--base',str(base),'--mask','off','--headline','A useful next step','--out',str(out),*extra],capture_output=True,text=True)
                self.assertEqual(r.returncode,0,r.stderr)
                with Image.open(out) as im:
                    self.assertEqual((im.size,im.format,im.mode),((1080,1920),'JPEG','RGB'))
                    self.assertTrue(im.info.get('icc_profile'))
                    return im.tobytes()
            blank=run('blank')
            custom=run('custom',extra=('--brand-text','EXAMPLE STUDIO'))
            suppressed=run('suppressed',extra=('--brand-text','EXAMPLE STUDIO','--no-brand'))
            self.assertNotEqual(hashlib.sha256(blank).hexdigest(),hashlib.sha256(custom).hexdigest())
            self.assertEqual(blank,suppressed)
            run('a','A');run('b','B')

if __name__=='__main__':unittest.main()
