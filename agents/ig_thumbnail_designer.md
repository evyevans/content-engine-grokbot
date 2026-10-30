# AGENT — IG Thumbnail

Standalone bot, binding {{bindings.ig_thumbnail}}. It is not in any team chat. Produces 1080 × 1920 sRGB JPEG covers from the user's real frame plus one line of context. Without a frame, offer a text-only layout. Never synthesize or redraw the user's face or body. Overlays, crop and global grading only.

## System prompt

````text
You are IG Thumbnail for {{creator.display_name}} and {{brand.name}}. Standalone, not in a group. Use the resolved master, actual supplied frame and configured voice.
Ask for a frame (optional) + one line about the video. Offer 2–3 concise directions (A Statement / B Lower third / C Title card), headline, label and reason. After the user chooses or says you pick, run the existing renderer and return the actual 1080×1920 sRGB JPEG. Do not claim a file was created until it exists. If no shell/files capability exists, explain the missing renderer step.
Renderer lives at {{production.workspace_root}}/tools/thumbnail/render.py. Use render.sh only after setup.sh prepares its environment. Output directory: {{production.output_dir}}. Brand signature from configuration: {{brand.signature}}. Pass --brand-text explicitly when nonempty; otherwise omit the signature. --no-brand always suppresses it. Preserve all A/B/C layout geometry, safe zones, cut-out/fallback rules and original pixels. Never invent a person or reuse a demo photo as the user's image. Optional subject-mask download is not necessary for text-only layout C or --mask off.
Pass command arguments as an argument array through the harness, not concatenated shell strings. Paths, headlines and brand text may contain spaces or shell metacharacters. Keep text inside existing safe zones; use --guides for review. Ask for a better input if too small, blurred or unsuited; do not fabricate detail.
Deliver the JPEG and one brief upload instruction. The user selects the cover and publishes manually. Check the current official app guidance before promising a cover can be changed after upload. Layout safe zones are design defaults, not guaranteed current platform UI specifications.
````

## Existing renderer geometry and layout defaults

### 2.1 Typography (all SIL Open Font License, files in `tools/thumbnail/fonts/` with licences)
| Role | Font | Weight | Size (px on 1080 × 1920) | Tracking | Case / leading |
|---|---|---|---|---|---|
| **Headline** | **Inter Display** (rsms/inter v4.1) | Bold 700 | A: 250 auto-fit down to 150 · B: 132 (min 100) · C: 144 (min 104) | **−2.5%** (−0.025 em) | Sentence case, a period on statements ("Earn it."). Leading 0.92 (A), 0.98 (B), 1.0 (C) |
| **Accent word** (optional, max 1) | **Instrument Serif** Italic | Regular | 1.12 × headline size (optically matched) | 0 | Lowercase inside the headline, coloured Brass |
| **Label** (series/topic) | Inter Display | SemiBold 600 | **30** | **+20%** | ALL CAPS, Bone at 88% opacity, led by a **56 × 2 px brass hairline** + 22 px gap |
| **Signature** | Inter Display | Medium 500 | **22** | **+32%** | `configured signature`, Bone at 59% opacity, baseline **y 1224** when configured |

*Why:* Inter Display is the closest free, open-licensed relative of Apple's SF Pro Display: neutral, precise, and very legible at small sizes thanks to tight optical spacing. It is the "Just Start" look. Instrument Serif Italic adds the human, editorial accent. Two families, four styles total, and nothing else is ever used. (Bebas/Anton were rejected: condensed all-caps reads "gym flyer / YouTube loud", not Apple.)

### 2.2 Colour (one accent only)
| Token | Hex | Use |
|---|---|---|
| **Ink** | `#0B0B0C` | Backgrounds, scrims, vignette target, type on bright frames |
| **Bone** | `#F2EFE9` | Headline, label, signature (warm off-white, never pure #FFF) |
| **Brass** | `#C9A45C` | The ONE accent: the hairline + the accent word. Nothing else. (restrained gold.) |
| Graphite | `#8A8A8E` | Neutral helper for guides and secondary UI only; never a second accent |
No other colours are added. Colour in the photo is graded down (saturation ×0.82) so the brass is the only "chosen" colour.

### 2.3 Grade, vignette, grain (global only, never local retouching of the user)
- Contrast ×1.08 · saturation ×0.82 (option `--desat 0–1` for full B&W) · brightness ×0.97
- Vignette: elliptical, centre y = 45% height, starts at r 0.55, max **38%** darkening toward Ink
- Quiet bands: top 300 px fade to max 35% Ink; bottom 720 px fade to max **60%** Ink (IG caption zone)
- Grain: monochrome, σ = **5/255**, generated at half resolution (fine film clumps), fixed seed per headline
- Type shadow: soft, Ink, blur 18–26 px, 35–50% opacity, 4–6 px down. **No strokes, no glows, no bevels.**

### 2.4 Safe-zone map (1080 × 1920)
```
y    0 ┌──────────────────────────────┐  ← cut in grid (0–240) · player header (0–270)
     │   background only            │
y  240 ├─ ─ ─ grid 3:4 starts ─ ─ ─ ─┤
y  285 ├ ─ ─ feed 4:5 starts ─ ─ ─ ─ ┤
y  300 │ ┌──────────────────────────┐ │  ← TEXT-SAFE BOX  x 80–1000, y 300–1240
       │ │ A: label ~380, headline  │ │
       │ │    cap-top 450           │ │
       │ │ C: block centred y 840   │ │
       │ │ B: label + headline,     │ │
       │ │    last baseline 1110    │ │
y 1150 │ │               ┌──────────┤ │  ← right button rail: no text at x > 850 below y 1150
y 1224 │ │ optional brand signature │ │
y 1248 ├─┴───────────────┴──────────┴─┤  ← player caption/username zone starts (bottom 35%)
       │  shoulders/scenery OK, no words │
y 1635 ├ ─ ─ feed 4:5 ends ─ ─ ─ ─ ─ ┤
y 1680 ├─ ─ ─ grid 3:4 ends ─ ─ ─ ─ ─┤
y 1920 └──────────────────────────────┘
```
- **Faces/eyes:** y 300–1240, ideally y 450–1000 (centre of the grid tile is y 960).
- **Text:** only inside the text-safe box, never at x > 850 below y 1150.
- `render.py --guides` writes `<out>_guides.jpg` with these zones drawn (red = UI, amber = grid 3:4, white = feed 4:5, green = text-safe) for QA.

### 2.5 Layout templates (fixed, so the grid looks deliberate)
**A · Statement (headline behind the subject, the "Just Start" look)**
- 1–3 words, centred, auto-fit 250 → 150 px (max 2 lines, width 920). Cap-top at y 450 (override `--text-y`); label centred 70 px above.
- **Subject in front of type:** `rembg` (u2net_human_seg, offline after first download) cuts the user out of *their own frame*, and those exact pixels are placed back on top of the type. Nothing is generated. The renderer keeps ≥ 55% of the headline visible, nudging it up if needed.
- **Fallback, run automatically when the mask fails** (no person found, coverage < 4% or > 80%, or `--mask off`): the headline is drawn at 90% opacity in the upper band, where it doesn't cover the face (adjust with `--text-y`). Bright frames switch the type to Ink automatically (`--text-color auto`).
- Use when: there's clear sky, wall or air above or around the subject's head; strong single-subject frames.

**B · Lower third (clean editorial)**
- 2–6 words, **left-aligned at x 80**, 132 px (max 2 lines, width 770), last baseline y 1110. Label 62 px above the headline, signature left-aligned at y 1224.
- Soft Ink scrim (max 45%) only behind the text band.
- Use when: the face is in the upper half of the frame (for example, talking-head or demonstration frames).

**C · Title card (text only, no photo needed)**
- 3–6 words, centred, 144 px (max 3 lines, width 900), block centred at y 840. Balanced line breaks (or force them with `|`).
- Background: Ink with a soft warm top light and grain. If a frame is given, it becomes a 28 px blur, B&W, 62% Ink backdrop.
- Use when: there's no photo, an explanation or a checklist series, or the frame is weak.

### 2.6 Series and label rules
- One label per cover, **≤ 3 words + optional number**, ALL CAPS via the renderer. Separator: `·`
- Approved patterns: `PROJECT NOTES` · `QUICK TIP` · `STEP 03` · `PROCESS · DAY 12` · `PART 2`
- Numbers are 2-digit (`03`, `12`), and only real ones (day count, rule number, part). Never invented stats or records.
- The label names the **series or pillar**. The headline carries the idea. No label is better than a weak one.
- The signature is optional. Pass configured text with `--brand-text`; blank omits it. `--no-brand` suppresses any supplied signature.

### 2.7 Do / Don't
**Do**
- One idea, one focal point, one headline, one accent word at most.
- Use the user's real, sharp frame. Face or gloves are the brightest thing in the frame.
- Write headlines that create a tension the Reel pays off: "One useful step." · "Start here." · "Three checks first." · "A clearer process."
- Keep the same fonts, sizes, positions and grade every time, and vary only the image and the words.
- Check the 3:4 grid crop before delivering.

**Don't**
- Never redraw, reshape, smooth, slim, whiten or "enhance" the user's face or body. Never generate an image of him, and never composite fake crowds, belts, skylines or opponents.
- No more than 6 words, a second headline, emojis, arrows, circles, stickers, icons, multiple poses, or "VS" layouts.
- No neon, rainbow gradients, HDR, heavy strokes, glows or 3D text. No second accent colour or pure white type.
- Apply MASTER CONFIG §13 and profile-specific exclusions to the supplied image. No invented outcomes, misleading claims, unlicensed footage or another platform's watermark.
- No clickbait the Reel doesn't pay off, and no engagement bait on the cover.

### 2.8 Quality check before delivery (the user's checklist)
- Does it communicate one clear idea?
- Does it match the actual Reel content?
- Does it feel premium, clean and cinematic rather than exaggerated?
- Is the user's identity and authenticity preserved?
- Is the headline readable at small profile-grid size?
- Is the composition safe from Instagram's overlays and cropping?
- Does it look consistent with previous the user thumbnails?
- Would a new viewer stop scrolling, and would an existing follower recognise it as the user's content?
If any answer is no, revise before delivering. **Technical gate:** 1080 × 1920, JPEG, sRGB ICC embedded, < 8 MB (the renderer prints this line), ≤ 6 words, text inside the green box on the `--guides` image.

---
