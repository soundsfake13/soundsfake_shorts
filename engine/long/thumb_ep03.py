"""Thumbnail for long-form ep03 (1280x720 JPG): Everest sunk in the deepest trench + 'EVEREST WOULD VANISH?!'.
Usage: python3 engine/long/thumb_ep03.py out.jpg"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
W, H = 1280, 720
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
F = lambda s, w="Black": ImageFont.truetype(f"{FD}InterDisplay-{w}.otf", s)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
SURF = 120
bg = np.zeros((H, W, 3), np.float32)
bg += np.array([4, 30, 66]) * np.clip(1 - (yy - SURF) / (H - SURF), 0, 1)[..., None] ** 1.2 + np.array([1, 4, 12])
bg[yy < SURF] = np.array([12, 40, 70])
img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(img)
# trench cross-section (right side)
def floor(x):
    if x < 640 or x > 1240: return 420
    if 840 <= x <= 1040: return 690
    u = (x - 640) / 200 if x < 840 else (1240 - x) / 200
    u = max(0, min(1, u)); return 420 + 270 * u * u * (3 - 2 * u)
pts = [(560, H)] + [(x, floor(x)) for x in range(560, W + 1, 8)] + [(W, H)]
d.polygon(pts, fill=(38, 34, 44)); d.line(pts[1:-1], fill=(80, 100, 125), width=4)
cx, base, top = 940, 690, 250
m = [(cx - 230, base), (cx - 120, base - 210), (cx - 70, base - 240), (cx - 30, base - 380), (cx, top), (cx + 30, base - 400), (cx + 70, base - 345), (cx + 110, base - 270), (cx + 230, base)]
glow = Image.new("L", (W, H), 0); ImageDraw.Draw(glow).polygon(m, fill=200)
img.paste(Image.new("RGB", (W, H), (140, 200, 255)), (0, 0), glow.filter(ImageFilter.GaussianBlur(28)))
d = ImageDraw.Draw(img); d.polygon(m, fill=(130, 138, 156), outline=(210, 220, 235))
d.polygon([(cx - 30, base - 380), (cx, top), (cx + 30, base - 400), (cx + 50, base - 370), (cx + 10, base - 365), (cx - 15, base - 350)], fill=(245, 250, 255))
d.line([(560, SURF + 4 * math.sin(x)) for x in range(1)] + [(x, SURF + 5 * math.sin(x * 0.04)) for x in range(560, W + 1, 6)], fill=(90, 230, 255), width=6)
d.line([(0, SURF), (560, SURF)], fill=(90, 230, 255), width=6)
bx = 1160; d.line([(bx, SURF + 10), (bx, top)], fill=(255, 205, 80), width=7)
for y in (SURF + 10, top): d.line([(bx - 22, y), (bx + 22, y)], fill=(255, 205, 80), width=7)
d.line([(cx + 20, top), (bx - 26, top)], fill=(255, 205, 80), width=3)
d.text((bx - 30, (SURF + top) / 2 + 4), "2+ KM", font=F(44), fill=(255, 205, 80), anchor="rm", stroke_width=6, stroke_fill=(0, 0, 0))
def outlined(x, y, s, size, fill, stroke=10):
    d.text((x, y), s, font=F(size), fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))
outlined(40, 170, "EVEREST", 130, (255, 255, 255))
outlined(40, 320, "WOULD", 100, (255, 255, 255))
outlined(40, 440, "VANISH?!", 140, (255, 205, 80))
d.rounded_rectangle([44, 30, 530, 82], 26, fill=(90, 230, 210))
d.text((287, 56), "10 DEEP-SEA FACTS THAT SOUND FAKE", font=F(23, "Bold"), fill=(8, 18, 26), anchor="mm")
img.save(sys.argv[1], quality=92); print("ok")
