"""Thumbnail for long-form ep05 (1280x720 JPG): parchment, emus vs a red 'ARMY LOST' stamp + 'BIRDS WON?!'.
Usage: python3 engine/long/thumb_ep05.py out.jpg"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
W, H = 1280, 720
ED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts") + "/"
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
SER = lambda s: ImageFont.truetype(ED + "DMSerifDisplay-Regular.ttf", s)
BLK = lambda s: ImageFont.truetype(f"{FD}InterDisplay-Black.otf", s)
INK, RED, PAPER = (36, 26, 20), (184, 36, 28), (236, 222, 188)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
v = np.clip(1 - (((xx - W / 2) / (W * 0.6)) ** 2 + ((yy - H / 2) / (H * 0.65)) ** 2) * 0.6, 0, 1)
bg = np.array(PAPER, np.float32) * (0.78 + 0.22 * v[..., None]) + np.random.default_rng(1).normal(0, 6, (H, W, 1))
img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(img)
d.rectangle([0, 600, W, H], fill=(206, 172, 96))
for k in range(160):
    x = (k * 97) % W; y = 600 + (k * 37) % 120; d.line([(x, y), (x + 4, y - 40)], fill=(168, 128, 58), width=3)
def emu(x, y, s):
    d.ellipse([x - 75 * s, y - 50 * s, x + 65 * s, y + 42 * s], fill=INK)
    d.polygon([(x - 70 * s, y - 20 * s), (x - 105 * s, y + 5 * s), (x - 72 * s, y + 25 * s)], fill=INK)
    hx, hy = x + 70 * s, y - 140 * s
    d.line([(x + 42 * s, y - 30 * s), (hx - 4 * s, hy + 10 * s)], fill=INK, width=int(16 * s))
    d.ellipse([hx - 16 * s, hy - 13 * s, hx + 16 * s, hy + 13 * s], fill=INK)
    d.polygon([(hx + 12 * s, hy - 5 * s), (hx + 36 * s, hy + 2 * s), (hx + 12 * s, hy + 7 * s)], fill=INK)
    d.ellipse([hx + 2 * s, hy - 6 * s, hx + 8 * s, hy], fill=PAPER)
    for o in (14, -14):
        d.line([(x + o * s, y + 25 * s), (x + o * s, y + 140 * s)], fill=INK, width=int(8 * s)); d.line([(x + o * s, y + 140 * s), (x + o * s + 22 * s, y + 140 * s)], fill=INK, width=int(6 * s))
emu(1040, 440, 1.4); emu(780, 470, 0.95)
# text block
def t(x, y, s, f, col): d.text((x, y), s, font=f, fill=col)
t(40, 120, "THE ARMY", SER(120), INK)
t(40, 250, "LOST", SER(190), RED)
t(40, 450, "TO BIRDS?!", SER(110), INK)
# stamp
m = Image.new("L", (500, 150), 0); md = ImageDraw.Draw(m); md.rounded_rectangle([6, 6, 494, 144], 14, outline=255, width=10)
md.text((250, 78), "100% REAL", font=BLK(84), fill=255, anchor="mm"); m = m.rotate(-8, expand=True)
img.paste(Image.new("RGB", m.size, RED), (700, 18), m)
d = ImageDraw.Draw(img); d.rectangle([40, 40, 470, 92], fill=INK); d.text((255, 66), "10 MOMENTS IN HISTORY", font=BLK(28), fill=PAPER, anchor="mm")
img.save(sys.argv[1], quality=92); print("ok")
