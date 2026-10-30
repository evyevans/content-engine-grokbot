"""Generate neutral abstract plates; run from any directory. No photos or network."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
W, H = 1080, 1920


def main():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for name,cx,cy,tint in [('abstract_light.jpg',.5,.2,(90,85,70)),('abstract_gradient.jpg',.7,.4,(65,80,95))]:
        glow=np.exp(-(((xx-W*cx)/520)**2+((yy-H*cy)/680)**2))
        pixels=np.clip(np.array([11,11,12])+glow[...,None]*np.array(tint),0,255).astype(np.uint8)
        Image.fromarray(pixels).filter(ImageFilter.GaussianBlur(3)).save(HERE/name,quality=95)
    print('OK: generated two neutral abstract plates')


if __name__=='__main__':main()
