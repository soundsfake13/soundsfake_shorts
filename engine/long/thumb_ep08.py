"""Thumbnail for long-form ep08 (1280x720 JPG): a glowing X-ray hand with a ring on blueprint blue + 'BY ACCIDENT?!'.
Usage: python3 engine/long/thumb_ep08.py out.jpg"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
W, H = 1280, 720
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
BLK = lambda s: ImageFont.truetype(f"{FD}InterDisplay-Black.otf", s)
AMBER, WHITE, CYAN = (255, 190, 70), (246, 250, 255), (200, 236, 255)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
bg = np.zeros((H, W, 3), np.float32) + np.array([8, 24, 58], np.float32)
bg += (np.exp(-(((xx - 330) / 420) ** 2 + ((yy - 380) / 380) ** 2)) * 60)[..., None] * np.array([0.5, 1.0, 1.4], np.float32)
img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(img)
for x in range(0, W, 40): d.line([(x, 0), (x, H)], fill=(24, 48, 92) if x % 200 else (34, 64, 116), width=1)
for y in range(0, H, 40): d.line([(0, y), (W, y)], fill=(24, 48, 92) if y % 200 else (34, 64, 116), width=1)
# dark X-ray film panel
px0, py0, px1, py1 = 70, 50, 590, 690
d.rounded_rectangle([px0, py0, px1, py1], 26, fill=(4, 10, 22), outline=(190, 220, 255), width=6)
layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
def bone(a, b, w, col=CYAN + (255,)):
    ld.line([a, b], fill=col, width=int(w))
    for p in (a, b): ld.ellipse([p[0] - w * 0.75, p[1] - w * 0.75, p[0] + w * 0.75, p[1] + w * 0.75], fill=col)
cx, base, s = 330, 540, 0.95
pw = 230 * s; top = base - 220 * s
fingers = [(-0.36, 190), (-0.12, 230), (0.12, 215), (0.36, 170)]
for i, (fx, fl) in enumerate(fingers):
    kx = cx + fx * pw; ky = top + 30 * s; bone((cx + fx * 50 * s, base - 20 * s), (kx, ky), 18 * s)
    y = ky; Lf = fl * s + 30 * s
    for j, f in enumerate([0.45, 0.32, 0.23]):
        y2 = y - Lf * f; bone((kx, y - 8 * s), (kx, y2 + 8 * s), (15 - j * 3) * s)
        if i == 2 and j == 0: ry = (y + y2) / 2; ring = (kx, ry)
        y = y2
tb = (cx - pw / 2 + 20 * s, base - 70 * s)
bone((cx - 40 * s, base - 10 * s), tb, 18 * s); bone(tb, (cx - pw / 2 - 70 * s, top + 40 * s), 16 * s); bone((cx - pw / 2 - 70 * s, top + 40 * s), (cx - pw / 2 - 100 * s, top - 10 * s), 13 * s)
for k in range(6): ld.ellipse([cx - 70 * s + k * 26 * s, base - 10 * s, cx - 46 * s + k * 26 * s, base + 18 * s], fill=CYAN + (255,))
bone((cx - 40 * s, base + 30 * s), (cx - 50 * s, base + 150 * s), 26 * s); bone((cx + 40 * s, base + 30 * s), (cx + 50 * s, base + 150 * s), 22 * s)
glow = layer.filter(ImageFilter.GaussianBlur(14)); img.paste(glow, (0, 0), glow); img.paste(layer, (0, 0), layer); d = ImageDraw.Draw(img)
rx, ry = ring
g = Image.new("L", (W, H), 0); ImageDraw.Draw(g).ellipse([rx - 60, ry - 40, rx + 60, ry + 40], fill=220)
img.paste(Image.new("RGB", (W, H), AMBER), (0, 0), g.filter(ImageFilter.GaussianBlur(20))); d = ImageDraw.Draw(img)
d.ellipse([rx - 36, ry - 15, rx + 36, ry + 15], outline=AMBER, width=12)
# text (right, upper area; bottom-right corner left clear)
def T(s_, size, x, y, col):
    while d.textlength(s_, font=BLK(size)) > 600: size -= 4
    f = BLK(size); d.text((x + 5, y + 6), s_, font=f, fill=(0, 0, 0), anchor="mm"); d.text((x, y), s_, font=f, fill=col, anchor="mm")
T("INVENTED", 116, 945, 190, WHITE)
T("BY", 116, 945, 320, WHITE)
T("ACCIDENT?!", 130, 945, 455, AMBER)
d.rounded_rectangle([780, 40, 1110, 92], 24, fill=(6, 16, 40)); d.text((945, 66), "SOUNDS FAKE · DEEP DIVE", font=BLK(26), fill=(230, 236, 246), anchor="mm")
img.save(sys.argv[1], quality=92); print("ok")
