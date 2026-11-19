"""Thumbnail for long-form ep06 (1280x720 JPG): Earth with a glowing golden cutaway core + '4 METERS OF GOLD?!'.
Usage: python3 engine/long/thumb_ep06.py out.jpg"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
W, H = 1280, 720
HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
BLK = lambda s: ImageFont.truetype(f"{FD}InterDisplay-Black.otf", s)
GOLD, WHITE = (255, 204, 70), (245, 248, 255)
rng = np.random.default_rng(2)
# background: deep space
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
bg = np.zeros((H, W, 3), np.float32) + np.array([4, 8, 20], np.float32)
bg += (np.exp(-(((xx - 380) / 420) ** 2 + ((yy - 380) / 380) ** 2)) * 50)[..., None] * np.array([0.4, 0.8, 1.6], np.float32)
img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(img)
for _ in range(260):
    x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.choice([0.8, 1.2, 1.8]); c = int(rng.uniform(120, 255)); d.ellipse([x - r, y - r, x + r, y + r], fill=(c, c, 255))
# globe
LAND = np.asarray(Image.open(os.path.join(HERE, "assets", "land_2048.png")).convert("L")).astype(np.float32) / 255
TH, TW = LAND.shape; LAND[int(TH * 168 / 180):] = 1
lat_ = (90 - (np.arange(TH) + 0.5) / TH * 180)[:, None]
ocean = np.array([14, 50, 110], np.float32); land = np.array([70, 125, 60], np.float32)
dry = np.exp(-((np.abs(lat_) - 23) / 8) ** 2)[..., None]
landc = land * (1 - dry) + np.array([214, 178, 112], np.float32) * dry
ice = (np.abs(lat_) > 64)[..., None]; landc = np.where(ice, 238, landc)
TEX = ocean * (1 - LAND[..., None]) + landc * LAND[..., None]
cx, cy, R = 400, 390, 300; lat0, lon0 = 18, 15
X, Y = np.meshgrid(np.arange(-R, R) + 0.5, np.arange(-R, R) + 0.5); x, y = X / R, -Y / R; rho2 = x * x + y * y
z = np.sqrt(np.clip(1 - rho2, 0, 1)); alpha = np.clip((1 - np.sqrt(rho2)) * R, 0, 1)
p0, l0 = math.radians(lat0), math.radians(lon0)
lat = np.arcsin(np.clip(z * math.sin(p0) + y * math.cos(p0), -1, 1)); lon = l0 + np.arctan2(x, z * math.cos(p0) - y * math.sin(p0))
u = ((np.degrees(lon) + 180) / 360 * TW).astype(int) % TW; v = np.clip(((90 - np.degrees(lat)) / 180 * TH).astype(int), 0, TH - 1)
L = np.array([-0.5, 0.45, 0.74]); L /= np.linalg.norm(L); lam = np.clip(x * L[0] + y * L[1] + z * L[2], 0, 1)
rgb = TEX[v, u] * (0.06 + 1.05 * lam ** 0.8)[..., None] + np.array([70, 150, 255]) * ((1 - z) ** 3 * 0.8)[..., None]
glow = Image.new("L", (W, H), 0); ImageDraw.Draw(glow).ellipse([cx - R - 20, cy - R - 20, cx + R + 20, cy + R + 20], fill=170)
img.paste(Image.new("RGB", (W, H), (50, 120, 255)), (0, 0), glow.filter(ImageFilter.GaussianBlur(40)))
g = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8), "RGBA"); img.paste(g, (cx - R, cy - R), g)
# cutaway wedge with a golden core
d = ImageDraw.Draw(img)
for f, c in ((1.0, (110, 64, 36)), (0.965, (214, 90, 40)), (0.56, (250, 170, 50)), (0.30, (255, 214, 90))):
    d.pieslice([cx - R * f, cy - R * f, cx + R * f, cy + R * f], -90, 0, fill=c)
core = Image.new("L", (W, H), 0); ImageDraw.Draw(core).pieslice([cx - 110, cy - 110, cx + 110, cy + 110], -90, 0, fill=200)
img.paste(Image.new("RGB", (W, H), (255, 230, 140)), (0, 0), core.filter(ImageFilter.GaussianBlur(14)))
d = ImageDraw.Draw(img); d.pieslice([cx - R * 0.3, cy - R * 0.3, cx + R * 0.3, cy + R * 0.3], -90, 0, fill=(255, 226, 120))
for k in range(26):
    a = rng.uniform(-math.pi / 2, 0); rr = rng.uniform(0.04, 0.28) * R; sx, sy = cx + rr * math.cos(a), cy + rr * math.sin(a); s = rng.uniform(2, 5)
    d.polygon([(sx, sy - s * 2), (sx + s, sy), (sx, sy + s * 2), (sx - s, sy)], fill=WHITE)
# text (top-right area; bottom-right corner left clear for YouTube's timestamp)
def T(s, size, x, y, col):
    while d.textlength(s, font=BLK(size)) > 540: size -= 4
    f = BLK(size); d.text((x + 5, y + 6), s, font=f, fill=(0, 0, 0), anchor="mm"); d.text((x, y), s, font=f, fill=col, anchor="mm")
T("4 METERS", 130, 990, 170, WHITE)
T("OF PRECIOUS", 130, 990, 300, GOLD)
T("METAL?!", 130, 990, 430, WHITE)
d.rounded_rectangle([60, 36, 380, 88], 24, fill=(10, 16, 30)); d.text((220, 62), "SOUNDS FAKE · EARTH", font=BLK(28), fill=(225, 230, 245), anchor="mm")
img.save(sys.argv[1], quality=92); print("ok")
