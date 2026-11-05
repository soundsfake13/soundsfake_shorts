"""Thumbnail for long-form ep02 (1280x720 JPG): a glowing human figure + 'YOU GLOW IN THE DARK'.
Usage: python3 engine/long/thumb_ep02.py out.jpg"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
W, H = 1280, 720
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
F = lambda s, w="Black": ImageFont.truetype(f"{FD}InterDisplay-{w}.otf", s)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
bg = np.zeros((H, W, 3), np.float32) + np.array([2, 6, 12])
bg += (np.exp(-(((xx - 330) / 380) ** 2 + ((yy - 380) / 420) ** 2)) * 60)[..., None] * np.array([0.3, 0.8, 1.0])
grid = ((xx % 48 < 1) | (yy % 48 < 1)) * 6.0
bg += grid[..., None] * np.array([0.5, 1, 1])
img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))

def figure(d, cx, foot, h, fill):
    s = h / 600.0; tor = 200 * s; leg = 270 * s; head = 52 * s; hip = foot - leg; sh = hip - tor; hy = sh - 18 * s - head; lw = int(46 * s)
    for dx in (-30, 30): d.line([(cx + dx * s * 0.8, hip), (cx + dx * s * 1.1, foot - lw / 2)], fill=fill, width=lw)
    for dx in (-30, 30): d.ellipse([cx + dx * s * 1.1 - lw / 2, foot - lw, cx + dx * s * 1.1 + lw / 2, foot], fill=fill)
    d.rounded_rectangle([cx - 66 * s, sh, cx + 66 * s, hip + 24 * s], int(40 * s), fill=fill)
    aw = int(36 * s)
    for sx in (-1, 1):
        pts = [(cx + sx * 74 * s, sh + 20 * s), (cx + sx * 150 * s, sh - 110 * s)]
        d.line(pts, fill=fill, width=aw)
        for p in pts: d.ellipse([p[0] - aw / 2, p[1] - aw / 2, p[0] + aw / 2, p[1] + aw / 2], fill=fill)
    d.rounded_rectangle([cx - 18 * s, sh - 26 * s, cx + 18 * s, sh + 8 * s], int(10 * s), fill=fill)
    d.ellipse([cx - head, hy - head, cx + head, hy + head], fill=fill)

m = Image.new("L", (W, H), 0); figure(ImageDraw.Draw(m), 330, 700, 640, 255)
for blur, k in ((70, 1.0), (28, 1.0), (8, 0.8)):
    img.paste(Image.new("RGB", (W, H), (120, 230, 255)), (0, 0), m.filter(ImageFilter.GaussianBlur(blur)).point(lambda v, kk=k: int(min(255, v * kk))))
img.paste(Image.new("RGB", (W, H), (150, 235, 255)), (0, 0), m.point(lambda v: int(v * 0.75)))
d = ImageDraw.Draw(img)

def outlined(x, y, s, size, fill, stroke=10):
    while d.textlength(s, font=F(size)) + 2 * stroke > W - x - 30 and size > 40: size -= 4
    d.text((x, y), s, font=F(size), fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))
outlined(650, 110, "YOU GLOW", 140, (255, 255, 255))
outlined(650, 260, "IN THE", 110, (255, 255, 255))
outlined(650, 380, "DARK ?!", 150, (255, 205, 80))
d.rounded_rectangle([660, 40, 1120, 92], 26, fill=(90, 230, 210))
d.text((890, 66), "10 BODY FACTS THAT SOUND FAKE", font=F(26, "Bold"), fill=(8, 18, 26), anchor="mm")
img.save(sys.argv[1], quality=92)
print("ok")
