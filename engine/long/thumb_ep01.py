"""Thumbnail for long-form ep01 (1280x720 JPG). Usage: python3 engine/long/thumb_ep01.py out.jpg"""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
W, H = 1280, 720
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
F = lambda s, w="Black": ImageFont.truetype(f"{FD}InterDisplay-{w}.otf", s)
rng = np.random.default_rng(3); r = random.Random(3)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
bg = np.zeros((H, W, 3), np.float32) + np.array([4, 6, 18])
bg += (np.exp(-(((xx - 330) / 420) ** 2 + ((yy - 380) / 380) ** 2)) * 80)[..., None] * np.array([0.4, 0.6, 1.0])
img = Image.fromarray(bg.astype(np.uint8)); d = ImageDraw.Draw(img)
for _ in range(260):
    x, y, s = r.uniform(0, W), r.uniform(0, H), r.choice([1, 1, 2]); c = r.randint(120, 255); d.ellipse([x - s, y - s, x + s, y + s], fill=(c, c, 255))

# ice giant, shaded
cx, cy, R = 330, 400, 300
X, Y = np.meshgrid(np.arange(-R, R, dtype=np.float32), np.arange(-R, R, dtype=np.float32))
d2 = (X ** 2 + Y ** 2) / R ** 2; disk = np.clip((1 - np.sqrt(d2)) * R, 0, 1); z = np.sqrt(np.clip(1 - d2, 0, 1))
lam = np.clip(-0.5 * X / R - 0.5 * Y / R + 0.7 * z, 0, 1)
band = 0.9 + 0.1 * np.sin(Y / R * 14)
col = np.array([60, 120, 235], np.float32) * (0.12 + 1.1 * lam)[..., None] * band[..., None]
pl = Image.fromarray(np.dstack([np.clip(col, 0, 255), disk * 255]).astype(np.uint8), "RGBA")
glow = Image.new("L", (W, H), 0); ImageDraw.Draw(glow).ellipse([cx - R - 30, cy - R - 30, cx + R + 30, cy + R + 30], fill=150)
img.paste(Image.new("RGB", (W, H), (70, 140, 255)), (0, 0), glow.filter(ImageFilter.GaussianBlur(40)))
img.paste(pl, (cx - R, cy - R), pl); d = ImageDraw.Draw(img)

# falling diamonds with sparkle
for k in range(26):
    x = r.uniform(80, 640); y = r.uniform(120, 700); s = r.uniform(12, 30)
    d.polygon([(x, y - s), (x + s * 0.75, y - s * 0.25), (x, y + s), (x - s * 0.75, y - s * 0.25)], fill=(235, 250, 255))
    d.polygon([(x - s * 0.75, y - s * 0.25), (x + s * 0.75, y - s * 0.25), (x, y - s)], fill=(255, 255, 255))
    d.line([(x, y - s * 2.6), (x, y - s * 1.3)], fill=(190, 225, 255), width=3)
spark = img.filter(ImageFilter.GaussianBlur(6)); img = Image.blend(img, spark, 0.25); d = ImageDraw.Draw(img)

def outlined(x, y, s, size, fill, stroke=10):
    while d.textlength(s, font=F(size)) + 2 * stroke > W - x - 30 and size > 40: size -= 4
    d.text((x, y), s, font=F(size), fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))
outlined(650, 150, "IT RAINS", 132, (255, 255, 255))
outlined(650, 290, "DIAMONDS", 132, (255, 210, 70))
outlined(650, 420, "?!", 150, (255, 90, 70))
d.rounded_rectangle([660, 600, 1240, 668], 34, fill=(255, 210, 70))
d.text((950, 634), "10 SPACE FACTS THAT SOUND FAKE", font=F(30, "Bold"), fill=(14, 16, 30), anchor="mm")
img.save(sys.argv[1], quality=92)
print("ok")
