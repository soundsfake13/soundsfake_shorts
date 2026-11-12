"""Thumbnail for long-form ep04 (1280x720 JPG): a frog frozen in an ice block + 'FROZEN. THEN ALIVE?!'.
Usage: python3 engine/long/thumb_ep04.py out.jpg"""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
W, H = 1280, 720
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
F = lambda s, w="Black": ImageFont.truetype(f"{FD}InterDisplay-{w}.otf", s)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
r = np.sqrt(((xx - 900) / W) ** 2 + ((yy - 340) / W) ** 2); a = np.arctan2(yy - 340, xx - 900)
bg = np.array([70, 34, 120], np.float32) * np.clip(1 - r * 1.3, 0, 1)[..., None] + np.array([14, 8, 30], np.float32)
bg += ((np.sin(a * 14) > 0.5) * np.clip(1 - r * 1.5, 0, 1) * 14)[..., None]
img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))
def paste(col, mask): img.paste(Image.new("RGB", (W, H), col), (0, 0), mask)
cx, cy, s = 900, 380, 1.0
g = Image.new("L", (W, H), 0); ImageDraw.Draw(g).rounded_rectangle([630, 70, 1170, 610], 30, fill=230)
paste((110, 200, 255), g.filter(ImageFilter.GaussianBlur(40)))
d = ImageDraw.Draw(img); col = (150, 156, 170); dk = (104, 108, 120)
for sx in (-1, 1): d.ellipse([cx + sx * 150 - 110, cy + 10, cx + sx * 150 + 110, cy + 150], fill=dk)
d.ellipse([cx - 190, cy - 150, cx + 190, cy + 140], fill=col); d.ellipse([cx - 120, cy - 10, cx + 120, cy + 130], fill=(196, 204, 214))
for sx in (-1, 1):
    d.polygon([(cx + sx * 60, cy - 120), (cx + sx * 200, cy - 100), (cx + sx * 190, cy - 40), (cx + sx * 60, cy - 70)], fill=(60, 56, 70))
    ex, ey = cx + sx * 100, cy - 140; d.ellipse([ex - 50, ey - 46, ex + 50, ey + 46], fill=col)
    d.ellipse([ex - 32, ey - 30, ex + 32, ey + 30], fill=(220, 225, 200)); d.ellipse([ex - 26, ey - 6, ex + 26, ey + 6], fill=(14, 10, 10))
d.arc([cx - 130, cy - 110, cx + 130, cy - 10], 20, 160, fill=(70, 60, 80), width=6)
m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rounded_rectangle([640, 80, 1160, 600], 26, fill=120); paste((160, 225, 255), m)
d = ImageDraw.Draw(img); d.rounded_rectangle([640, 80, 1160, 600], 26, outline=(230, 248, 255), width=7)
rr = random.Random(3)
for k in range(9):
    x, y = rr.uniform(670, 1100), rr.uniform(110, 560); d.line([(x, y), (x + 50, y - 36)], fill=(240, 252, 255), width=4)
# flat-line monitor strip under the block
d.rounded_rectangle([640, 615, 1120, 685], 20, fill=(6, 20, 16), outline=(70, 120, 100), width=4)
d.text((662, 628), "HEART: 0 BPM", font=F(30), fill=(255, 96, 110))
d.line([(880, 650), (1100, 650)], fill=(140, 255, 170), width=5)
def outlined(x, y, s_, size, fill, stroke=10): d.text((x, y), s_, font=F(size), fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))
outlined(40, 150, "FROZEN.", 130, (190, 235, 255))
outlined(40, 300, "THEN", 110, (255, 255, 255))
outlined(40, 425, "ALIVE?!", 150, (255, 204, 64))
d.rounded_rectangle([44, 40, 560, 92], 26, fill=(255, 96, 110))
d.text((302, 66), "10 ANIMAL SUPERPOWERS THAT SOUND FAKE", font=F(22, "Bold"), fill=(255, 255, 255), anchor="mm")
img.save(sys.argv[1], quality=92); print("ok")
