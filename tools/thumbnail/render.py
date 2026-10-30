#!/usr/bin/env python3
"""
Content Engine — IG Reels cover renderer

Renders a 1080x1920 (9:16) Instagram Reel cover as a high-quality sRGB JPEG.
The user's frame is NEVER redrawn: it is only cover-cropped and given a global grade,
vignette and grain; everything else is an overlay (type, hairline, label).

Templates
  A  Statement   - one huge headline in the upper safe core. With --mask auto
                   (default) and rembg available, the subject is cut out and placed
                   IN FRONT of the type ("Just Start" look). If no reliable mask, the
                   headline is drawn at 90% opacity above the subject instead.
  B  Lower third - label + left-aligned headline sitting just above the IG caption zone,
                   over a soft bottom scrim.
  C  Title card  - text-only (no photo needed). Ink background, soft top light.
                   If a base image is given it is blurred + darkened into a backdrop.

Usage
  .venv/bin/python render.py --template B --base frame.jpg \
      --headline "Show up anyway." --label "Discipline" --accent anyway --out cover.jpg
  Add --guides to also write <out>_guides.jpg with the IG crops + safe zones drawn.
"""
import argparse, hashlib, io, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageEnhance, ImageCms

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
W, H = 1080, 1920

# ---------------------------------------------------------------- system tokens
INK = (11, 11, 12)          # #0B0B0C near-black
BONE = (242, 239, 233)      # #F2EFE9 off-white
BRASS = (201, 164, 92)      # #C9A45C single accent
GRAPHITE = (138, 138, 142)  # #8A8A8E secondary/neutral (not an accent)

F_HEAD = os.path.join(FONTS, "InterDisplay-Bold.ttf")
F_LABEL = os.path.join(FONTS, "InterDisplay-SemiBold.ttf")
F_BRAND = os.path.join(FONTS, "InterDisplay-Medium.ttf")
F_ACCENT = os.path.join(FONTS, "InstrumentSerif-Italic.ttf")

SAFE = dict(x0=80, x1=1000, y0=300, y1=1240, rail_x=850, rail_y=1150)  # text-safe box
HEAD_TRACK = -0.025   # em
LABEL_TRACK = 0.20    # em
BRAND_TRACK = 0.32    # em
LABEL_SIZE = 30
BRAND_SIZE = 22
BRAND_Y = 1224        # fixed signature baseline on every cover (inside the 1248 player limit)
ACCENT_SCALE = 1.12   # serif italic optically matched to Inter Display Bold

TEMPLATE = {
    "A": dict(size_max=250, size_min=150, max_lines=2, lead=0.92, width=920),
    "B": dict(size=132, size_min=100, max_lines=2, lead=0.98, width=770),
    "C": dict(size=144, size_min=104, max_lines=3, lead=1.0, width=900),
}

GRADE = dict(contrast=1.08, saturation=0.82, brightness=0.97)
VIGNETTE = 0.38          # max edge darkening
GRAIN = 5.0              # std-dev of mono grain, 0-255
TOP_QUIET = (300, 0.35)  # (height px, max darkening) gradient at top
BOT_QUIET = (720, 0.60)  # bottom gradient (keeps IG caption zone quiet)


STATE = {"light": False}  # set when template A sits on a bright frame


def font(path, size):
    return ImageFont.truetype(path, size)


# ---------------------------------------------------------------- image ops
def load_base(path):
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    icc = im.info.get("icc_profile")
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
    if im.mode == "RGBA":
        bg = Image.new("RGB", im.size, INK); bg.paste(im, mask=im.split()[3]); im = bg
    if icc:  # convert any embedded profile (Display P3 from iPhone etc.) to sRGB
        try:
            src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            im = ImageCms.profileToProfile(im, src, ImageCms.createProfile("sRGB"), outputMode="RGB")
        except Exception:
            pass
    return im


def cover_crop(im, focus_x=0.5, focus_y=0.5):
    """Scale to fill 1080x1920 (no distortion) and crop around the focus point."""
    s = max(W / im.width, H / im.height)
    nw, nh = round(im.width * s), round(im.height * s)
    im = im.resize((nw, nh), Image.LANCZOS)
    left = int(min(max(focus_x * nw - W / 2, 0), nw - W))
    top = int(min(max(focus_y * nh - H / 2, 0), nh - H))
    if s > 1.6:
        print(f"WARN: base image upscaled {s:.2f}x - ask for a sharper frame/screenshot", file=sys.stderr)
    return im.crop((left, top, left + W, top + H))


def grade(im, desat=0.0):
    im = ImageEnhance.Contrast(im).enhance(GRADE["contrast"])
    im = ImageEnhance.Color(im).enhance(GRADE["saturation"] * (1 - desat))
    im = ImageEnhance.Brightness(im).enhance(GRADE["brightness"])
    return im


def shade_layers(im):
    """Vignette + quiet top/bottom bands. Multiplies toward INK, never repaints the subject."""
    a = np.asarray(im).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx, ny = (xx - W / 2) / (W / 2), (yy - H * 0.45) / (H / 2)
    r = np.sqrt(nx ** 2 * 0.9 + ny ** 2)
    vig = np.clip((r - 0.55) / 0.75, 0, 1) ** 1.6 * VIGNETTE
    th, tm = TOP_QUIET; bh, bm = BOT_QUIET
    top = np.clip(1 - yy / th, 0, 1) ** 1.5 * tm
    bot = np.clip((yy - (H - bh)) / bh, 0, 1) ** 1.3 * bm
    dark = 1 - (1 - vig) * (1 - top) * (1 - bot)
    ink = np.array(INK, np.float32)
    a = a * (1 - dark[..., None]) + ink * dark[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def add_grain(im, seed):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, GRAIN, (H // 2, W // 2)).astype(np.float32)
    n = np.asarray(Image.fromarray(n).resize((W, H), Image.BILINEAR))  # finer, film-like clumps
    a = np.asarray(im).astype(np.float32) + n[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def text_backdrop(seed):
    """Template C background: ink + soft top light (graphic only, never a photo)."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.9)) ** 2 + ((yy - H * 0.30) / (H * 0.55)) ** 2)
    light = np.clip(1 - d, 0, 1) ** 2.2 * 0.16
    base = np.array(INK, np.float32)[None, None, :] + light[..., None] * 255 * np.array([1.0, 0.97, 0.92])
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- typography
def tracked_width(f, text, track_em):
    if not text:
        return 0
    return f.getlength(text) + track_em * f.size * (len(text) - 1)


def draw_tracked(draw, xy, text, f, fill, track_em):
    """Draw with letter-spacing while keeping kerning (cumulative getlength)."""
    x0, y = xy
    tr = track_em * f.size
    for i, ch in enumerate(text):
        draw.text((x0 + f.getlength(text[:i]) + tr * i, y), ch, font=f, fill=fill, anchor="ls")


def tokens(headline, accent):
    acc = (accent or "").strip().lower().strip(".,!?")
    out = []
    for w in headline.replace("|", " | ").split():
        core = w.lower().strip(".,!?'\"")
        out.append((w, bool(acc) and core == acc))
    return out


def split_manual(words):
    """'|' in the headline forces a line break: "Discipline | is the price | of freedom." """
    groups, cur = [], []
    for w, a in words:
        if w == "|":
            groups.append(cur); cur = []
        else:
            cur.append((w, a))
    groups.append(cur)
    return [g for g in groups if g]


def word_font(is_acc, size):
    return font(F_ACCENT, round(size * ACCENT_SCALE)) if is_acc else font(F_HEAD, size)


def line_width(words, size):
    sp = font(F_HEAD, size).getlength(" ") * 0.9
    return sum(tracked_width(word_font(a, size), w, 0 if a else HEAD_TRACK) for w, a in words) + sp * (len(words) - 1)


def wrap(words, size, maxw, max_lines):
    lines, cur = [], []
    for wd in words:
        if cur and line_width(cur + [wd], size) > maxw:
            lines.append(cur); cur = [wd]
        else:
            cur.append(wd)
    if cur:
        lines.append(cur)
    ok = len(lines) <= max_lines and all(line_width(l, size) <= maxw for l in lines)
    return lines, ok


def balanced(words, size, maxw, max_lines):
    """Fewest lines that fit, then the most even line lengths (no orphan words)."""
    import itertools
    n = len(words)
    for k in range(1, min(max_lines, n) + 1):
        best = None
        for cuts in itertools.combinations(range(1, n), k - 1):
            idx = (0,) + cuts + (n,)
            lines = [words[idx[i]:idx[i + 1]] for i in range(k)]
            ws = [line_width(l, size) for l in lines]
            if max(ws) > maxw:
                continue
            score = (max(ws) - min(ws)) + (400 if k > 1 and len(lines[-1]) == 1 and n > 3 else 0)
            if best is None or score < best[0]:
                best = (score, lines)
        if best:
            return best[1]
    return None


def fit(words, size, size_min, maxw, max_lines):
    manual = [list(g) for g in split_manual(words)]
    s = size
    while s >= size_min:
        if len(manual) > 1:
            if len(manual) <= max_lines and all(line_width(l, s) <= maxw for l in manual):
                return manual, s
        else:
            lines = balanced(words, s, maxw, max_lines)
            if lines:
                return lines, s
        s -= 4
    raise SystemExit(f"ERROR: headline too long for this template - cut it to 3-6 words. ({' '.join(w for w,_ in words)})")


def render_headline(lines, size, lead, align, color=BONE, accent_color=BRASS):
    """Returns RGBA layer (W x tall) with the headline + its cap-top & block height."""
    hf = font(F_HEAD, size)
    asc = hf.getmetrics()[0]
    cap = hf.getbbox("H", anchor="ls")[1] * -1  # cap height
    lh = round(size * lead)
    block_h = cap + lh * (len(lines) - 1)
    layer = Image.new("RGBA", (W, block_h + size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    sp = hf.getlength(" ") * 0.9
    lefts = []
    for i, ln in enumerate(lines):
        lw = line_width(ln, size)
        x = (W - lw) / 2 if align == "center" else SAFE["x0"]
        lefts.append((x, lw))
        y = cap + i * lh
        for w, a in ln:
            f = word_font(a, size)
            draw_tracked(d, (x, y), w, f, accent_color if a else color, 0 if a else HEAD_TRACK)
            x += tracked_width(f, w, 0 if a else HEAD_TRACK) + sp
    return layer, cap, block_h, lefts


def soft_shadow(layer, blur=22, opacity=0.45):
    a = layer.split()[3].filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * opacity))
    sh = Image.new("RGBA", layer.size, INK + (0,)); sh.putalpha(a)
    return sh


def draw_label(canvas, text, cx_or_x, y, align, rule=True):
    """Small ALL-CAPS tracked label with a brass hairline. y = baseline."""
    if not text:
        return
    t = text.upper()
    f = font(F_LABEL, LABEL_SIZE)
    tw = tracked_width(f, t, LABEL_TRACK)
    rule_w, gap = (56, 22) if rule else (0, 0)
    total = rule_w + gap + tw
    x = cx_or_x - total / 2 if align == "center" else cx_or_x
    d = ImageDraw.Draw(canvas)
    if rule:
        cy = y - round(LABEL_SIZE * 0.36)
        d.rectangle([x, cy - 1, x + rule_w, cy + 1], fill=BRASS + (255,))
    col = INK + (235,) if STATE["light"] else BONE + (225,)
    draw_tracked(d, (x + rule_w + gap, y), t, f, col, LABEL_TRACK)


def draw_brand(canvas, align="center", text=""):
    if not text.strip():
        return
    f = font(F_BRAND, BRAND_SIZE)
    tw = tracked_width(f, text, BRAND_TRACK)
    d = ImageDraw.Draw(canvas)
    x = (W - tw) / 2 if align == "center" else SAFE["x0"]
    col = INK + (170,) if STATE["light"] else BONE + (150,)
    draw_tracked(d, (x, BRAND_Y), text, f, col, BRAND_TRACK)


# ---------------------------------------------------------------- subject mask (template A)
def subject_mask(base_rgb):
    try:
        os.environ.setdefault("U2NET_HOME", os.path.join(HERE, "models"))
        from rembg import remove, new_session
        sess = new_session("u2net_human_seg")
        m = remove(base_rgb, session=sess, only_mask=True, post_process_mask=True)
        m = m.convert("L")
    except Exception as e:
        print(f"INFO: no subject mask ({e.__class__.__name__}: {e}); using fallback A", file=sys.stderr)
        return None
    arr = np.asarray(m) / 255.0
    cover = (arr > 0.5).mean()
    if not (0.04 <= cover <= 0.80):
        print(f"INFO: mask unreliable (coverage {cover:.0%}); using fallback A", file=sys.stderr)
        return None
    return m.filter(ImageFilter.GaussianBlur(1.2))


# ---------------------------------------------------------------- templates
def compose(args):
    seed = int(hashlib.md5((args.headline + (args.label or "")).encode()).hexdigest()[:8], 16)
    words = tokens(args.headline, args.accent)
    n_words = len([w for w, _ in words if w != "|"])
    if n_words > 6:
        raise SystemExit("ERROR: max 6 words in the headline (system rule).")
    if args.base:
        base = cover_crop(load_base(args.base), args.focus_x, args.focus_y)
    else:
        base = None
    if args.template in "AB" and base is None:
        print("INFO: no base image - template", args.template, "falls back to C (text-only).", file=sys.stderr)
        args.template = "C"

    t = args.template
    if t == "C":
        if base is not None:
            bg = grade(base, desat=1.0).filter(ImageFilter.GaussianBlur(28))
            bg = Image.blend(bg, Image.new("RGB", (W, H), INK), 0.62)
        else:
            bg = text_backdrop(seed)
        canvas = shade_layers(bg).convert("RGBA")
        cfg = TEMPLATE["C"]
        lines, size = fit(words, cfg["size"], cfg["size_min"], cfg["width"], cfg["max_lines"])
        layer, cap, bh, _ = render_headline(lines, size, cfg["lead"], "center")
        top = round(840 - bh / 2)   # optical centre between player-safe core and grid tile
        canvas.alpha_composite(soft_shadow(layer, 18, 0.5), (0, top + 4))
        canvas.alpha_composite(layer, (0, top))
        draw_label(canvas, args.label, W / 2, top - 92, "center")
    else:
        g = grade(base, args.desat)
        mask = subject_mask(g) if (t == "A" and args.mask == "auto") else None
        canvas = g.convert("RGBA")
        if t == "A":
            cfg = TEMPLATE["A"]
            lines, size = fit(words, cfg["size_max"], cfg["size_min"], cfg["width"], cfg["max_lines"])
            layer, cap, bh, _ = render_headline(lines, size, cfg["lead"], "center")
            top = args.text_y if args.text_y is not None else 450
            region = np.asarray(g.convert("L").crop((80, top, 1000, top + bh)), np.float32)
            if args.text_color == "ink" or (args.text_color == "auto" and region.mean() > 165):
                STATE["light"] = True  # bright frame: switch the type to INK for contrast
                layer, cap, bh, _ = render_headline(lines, size, cfg["lead"], "center", color=INK)
            if mask is not None:
                # keep >= 55% of the headline visible; nudge up if the subject hides too much
                for cand in range(top, SAFE["y0"] - 1, -20):
                    vis = visible_fraction(layer, mask, cand)
                    if vis >= 0.55:
                        top = cand; break
                else:
                    print(f"WARN: subject covers most of the headline (visible {vis:.0%}); consider B", file=sys.stderr)
                if not STATE["light"]:
                    canvas.alpha_composite(soft_shadow(layer, 26, 0.35), (0, top + 6))
                canvas.alpha_composite(layer, (0, top))
                subj = g.convert("RGBA"); subj.putalpha(mask)
                canvas.alpha_composite(subj)  # real pixels of the user, untouched, back on top
            else:
                faded = layer.copy(); faded.putalpha(layer.split()[3].point(lambda v: int(v * 0.90)))
                if not STATE["light"]:
                    canvas.alpha_composite(soft_shadow(layer, 26, 0.40), (0, top + 6))
                canvas.alpha_composite(faded, (0, top))
            draw_label(canvas, args.label, W / 2, top - 70, "center")
        else:  # B
            cfg = TEMPLATE["B"]
            lines, size = fit(words, cfg["size"], cfg["size_min"], cfg["width"], cfg["max_lines"])
            layer, cap, bh, _ = render_headline(lines, size, cfg["lead"], "left")
            bottom = 1110  # last baseline; descenders clear the button rail (y 1150) and the brand line
            top = bottom - bh
            # local scrim: soft dark band behind the text block only
            yy = np.arange(H, dtype=np.float32)
            s0, s1 = top - 260, bottom + 220
            band = np.clip(np.minimum((yy - s0) / 260, (s1 - yy) / 220), 0, 1) ** 1.2 * 0.45
            sc = Image.fromarray((np.repeat(band[:, None], W, 1) * 255).astype(np.uint8), "L")
            ink = Image.new("RGBA", (W, H), INK + (255,)); ink.putalpha(sc)
            canvas.alpha_composite(ink)
            canvas.alpha_composite(soft_shadow(layer, 18, 0.45), (0, top + 4))
            canvas.alpha_composite(layer, (0, top))
            draw_label(canvas, args.label, SAFE["x0"], top - 62, "left")
        rgb = canvas.convert("RGB")
        canvas = shade_layers(rgb).convert("RGBA")
    if not args.no_brand and args.brand_text.strip():
        draw_brand(canvas, "left" if args.template == "B" else "center", args.brand_text)
    out = add_grain(canvas.convert("RGB"), seed)
    return out


def visible_fraction(layer, mask, top):
    a = np.asarray(layer.split()[3], np.float32) / 255
    m = np.asarray(mask, np.float32) / 255
    h = min(a.shape[0], H - top)
    a, m = a[:h], m[top:top + h]
    tot = a.sum()
    return 1.0 if tot == 0 else float((a * (1 - m)).sum() / tot)


# ---------------------------------------------------------------- export + guides
def export(im, path, q=92):
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    while True:
        im.save(path, "JPEG", quality=q, subsampling=0, optimize=True, progressive=True, icc_profile=srgb)
        mb = os.path.getsize(path) / 1e6
        if mb < 8 or q <= 80:
            break
        q -= 3
    return q, mb


def guides(im, path):
    g = im.convert("RGBA"); o = Image.new("RGBA", g.size, (0, 0, 0, 0)); d = ImageDraw.Draw(o)
    d.rectangle([0, 0, W, 270], fill=(255, 0, 0, 50)); d.rectangle([0, 1248, W, H], fill=(255, 0, 0, 50))
    d.rectangle([853, 1150, W, 1248], fill=(255, 0, 0, 50))
    d.rectangle([0, 240, W - 1, 1680], outline=(255, 190, 0, 255), width=4)   # grid 3:4
    d.rectangle([0, 285, W - 1, 1635], outline=(255, 255, 255, 200), width=2)  # feed 4:5
    d.rectangle([SAFE["x0"], SAFE["y0"], SAFE["x1"], SAFE["y1"]], outline=(0, 220, 120, 255), width=3)
    g.alpha_composite(o); g.convert("RGB").save(path, "JPEG", quality=85)


def main():
    p = argparse.ArgumentParser(description="Content Engine IG Reel cover renderer")
    p.add_argument("--base", help="The user's frame/photo (optional). Never redrawn, only cropped + graded.")
    p.add_argument("--template", "-t", choices=list("ABC"), required=True)
    p.add_argument("--headline", required=True, help="3-6 words, sentence case")
    p.add_argument("--label", help="small series/brand label, e.g. 'Project notes · Part 2'")
    p.add_argument("--accent", help="one word of the headline to set in serif italic brass")
    p.add_argument("--out", required=True)
    p.add_argument("--focus-x", type=float, default=0.5, help="crop focus 0-1 (default centre)")
    p.add_argument("--focus-y", type=float, default=0.5)
    p.add_argument("--desat", type=float, default=0.0, help="0-1 extra desaturation (1 = B&W)")
    p.add_argument("--mask", choices=["auto", "off"], default="auto", help="template A subject cut-out")
    p.add_argument("--text-y", type=int, help="template A: top of headline in px (default 450)")
    p.add_argument("--text-color", choices=["auto", "bone", "ink"], default="auto",
                   help="template A: auto switches to INK type on bright frames")
    p.add_argument("--brand-text", default="", help="custom signature; blank omits branding")
    p.add_argument("--no-brand", action="store_true", help="omit any configured signature")
    p.add_argument("--guides", action="store_true", help="also write <out>_guides.jpg")
    a = p.parse_args()
    im = compose(a)
    assert im.size == (W, H)
    q, mb = export(im, a.out)
    print(f"OK {a.out}  {W}x{H}  JPEG q{q} sRGB  {mb:.2f} MB  template {a.template}")
    if a.guides:
        gp = os.path.splitext(a.out)[0] + "_guides.jpg"; guides(im, gp); print("guides:", gp)


if __name__ == "__main__":
    main()
