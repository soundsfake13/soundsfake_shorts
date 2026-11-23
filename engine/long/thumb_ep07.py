"""Thumbnail for long-form ep07 (1280x720 JPG): a glowing calendar page 'FEBRUARY 30' + 'IT WAS REAL?!'.
Usage: python3 engine/long/thumb_ep07.py out.jpg"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
W, H = 1280, 720
HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
BLK = lambda s: ImageFont.truetype(f"{FD}InterDisplay-Black.otf", s)
SER = lambda s: ImageFont.truetype(os.path.join(os.path.dirname(HERE), "fonts", "OldStandard-Bold.ttf"), s)
BRASS, WHITE, RED = (255, 198, 80), (248, 244, 234), (200, 56, 44)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
bg = np.zeros((H, W, 3), np.float32) + np.array([8, 10, 26], np.float32)
bg += (np.exp(-(((xx - 360) / 420) ** 2 + ((yy - 380) / 360) ** 2)) * 70)[..., None] * np.array([1.4, 1.0, 0.5], np.float32)
img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(img)
# faint gear (top right)
cx, cy, R = 1180, 90, 200
pts = [(cx + (R + (16 if k % 4 in (1, 2) else -8)) * math.cos(2 * math.pi * k / 96), cy + (R + (16 if k % 4 in (1, 2) else -8)) * math.sin(2 * math.pi * k / 96)) for k in range(96)]
d.polygon(pts, outline=(70, 60, 50), width=6); d.ellipse([cx - 60, cy - 60, cx + 60, cy + 60], outline=(70, 60, 50), width=6)
# calendar page with glow
px, py, pw, ph = 90, 110, 540, 520
glow = Image.new("L", (W, H), 0); ImageDraw.Draw(glow).rounded_rectangle([px - 30, py - 30, px + pw + 30, py + ph + 30], 50, fill=200)
img.paste(Image.new("RGB", (W, H), (255, 170, 70)), (0, 0), glow.filter(ImageFilter.GaussianBlur(40))); d = ImageDraw.Draw(img)
page = Image.new("RGBA", (pw + 40, ph + 40), (0, 0, 0, 0)); pd = ImageDraw.Draw(page)
pd.rounded_rectangle([20, 20, 20 + pw, 20 + ph], 34, fill=(246, 238, 220)); pd.rounded_rectangle([20, 20, 20 + pw, 150], 34, fill=RED); pd.rectangle([20, 110, 20 + pw, 150], fill=RED)
pd.text((20 + pw / 2, 86), "FEBRUARY", font=SER(76), fill=(252, 242, 224), anchor="mm")
pd.text((20 + pw / 2, 330), "30", font=BLK(300), fill=(34, 28, 34), anchor="mm")
pd.text((20 + pw / 2, 500), "1712 · SWEDEN", font=BLK(40), fill=(150, 110, 90), anchor="mm")
page = page.rotate(-5, expand=True, resample=Image.BICUBIC); img.paste(page, (px - 40, py - 40), page); d = ImageDraw.Draw(img)
for k in range(5): rx = px + 70 + k * 105; d.ellipse([rx - 12, py - 6, rx + 12, py + 18], fill=(50, 50, 60))
# text (right side, upper area; bottom-right corner left clear)
def T(s, size, x, y, col):
    while d.textlength(s, font=BLK(size)) > 560: size -= 4
    f = BLK(size); d.text((x + 5, y + 6), s, font=f, fill=(0, 0, 0), anchor="mm"); d.text((x, y), s, font=f, fill=col, anchor="mm")
T("THIS DAY", 120, 960, 170, WHITE)
T("REALLY", 130, 960, 310, BRASS)
T("HAPPENED", 120, 960, 450, WHITE)
d.rounded_rectangle([700, 30, 1010, 80], 24, fill=(10, 12, 26)); d.text((855, 55), "SOUNDS FAKE · TIME", font=BLK(28), fill=(230, 226, 214), anchor="mm")
img.save(sys.argv[1], quality=92); print("ok")
