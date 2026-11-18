"""Day 47 — ZERO-G style (Astronauts get taller in space).
A soft pastel space-station interior seen through a playful UI: lavender-to-peach padded wall panels with rivets and a
big porthole onto a night Earth limb; everything in the scene floats — rounded white 'glass' cards with soft indigo
shadows bob and tilt on their own phases, title lines drift independently, and small loose objects (pencil, water blob,
bolt, notepad) tumble slowly across the cabin. Illustrations are flat-shaded with thin indigo outlines, supersampled 2x:
a generic rounded astronaut whose torso can stretch, a cartoon side-view spine (bone-cream vertebrae, coral discs) that
squeezes under a '1g' weight and relaxes when it floats away, a swelling disc soaking up blue droplets, a measuring
ruler with a +3% counter, a re-entry capsule under a striped parachute, a green landing pad with gravity arrows.
Type: Baloo 2 ExtraBold (puffy rounded display) + Nunito Black for labels. Palette: indigo ink, coral, mint, sky, butter.
Scene changes: new cards float up with a springy overshoot and a soft 'pop' ring.
Ending: pastel toggle whose knob is an astronaut helmet; FAKE (coral) -> TRUE (mint track); last 0.6 s cross-fades back
into the hook for the loop.
Music: floaty F-major pad + echoing sine plucks + shaker; bloops, squish, rising stretch sweep, landing thump.
Usage: python3 engine/styles/day47_zerog.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]

INK = (46, 40, 92); CORAL = (255, 112, 102); MINT = (98, 206, 176); SKY = (118, 168, 250); BUTTER = (255, 206, 92)
BONE = (252, 241, 222); DISC = (255, 150, 160); WHITE = (255, 255, 255); NIGHT = (52, 46, 112); LAV = (214, 206, 248)
SS = 2

_F = {}
def F(size, wt=800, kind="baloo"):
    k = (kind, int(size), int(wt))
    if k not in _F:
        f = ImageFont.truetype(f"{FONTS}/{'Baloo2-VF' if kind == 'baloo' else 'Nunito-VF'}.ttf", int(size))
        f.set_variation_by_axes([int(wt)]); _F[k] = f
    return _F[k]

# ---------- sprite helpers ----------
def new(w, h): return Image.new("RGBA", (int(w * SS), int(h * SS)), (0, 0, 0, 0))
def down(im): return im.resize((im.width // SS, im.height // SS), Image.LANCZOS)
def S(v): return [x * SS for x in v]
def rrect(d, box, r, fill=None, outline=INK, w=4):
    x0, y0, x1, y1 = box
    if x1 - x0 < 2 or y1 - y0 < 2: return
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    d.rounded_rectangle(S(box), radius=r * SS, fill=fill, outline=outline, width=int(w * SS) if outline else 0)
def ell(d, box, fill=None, outline=INK, w=4):
    d.ellipse(S(box), fill=fill, outline=outline, width=int(w * SS) if outline else 0)
def poly(d, pts, fill=None, outline=INK, w=4):
    q = [(x * SS, y * SS) for x, y in pts]
    if fill: d.polygon(q, fill=fill)
    if outline: d.line(q + [q[0]], fill=outline, width=int(w * SS), joint="curve")
def capsule(d, a, b, r, fill, outline=INK, w=4):
    """thick rounded limb from a to b"""
    (x0, y0), (x1, y1) = a, b
    if outline:
        d.line(S([x0, y0, x1, y1]), fill=outline, width=int((2 * r + 2 * w) * SS))
        for x, y in (a, b): ell(d, (x - r - w, y - r - w, x + r + w, y + r + w), outline, None)
    d.line(S([x0, y0, x1, y1]), fill=fill, width=int(2 * r * SS))
    for x, y in (a, b): ell(d, (x - r, y - r, x + r, y + r), fill, None)

def with_shadow(im, off=(0, 22), blur=16, al=0.22, pad=50):
    W2, H2 = im.width + 2 * pad, im.height + 2 * pad
    out = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    a = np.zeros((H2, W2), np.float32); a[pad:pad + im.height, pad:pad + im.width] = np.asarray(im)[..., 3] / 255.0
    a = np.roll(np.roll(a, off[1], 0), off[0], 1); a = cv2.GaussianBlur(a, (0, 0), blur) * al
    sh = np.zeros((H2, W2, 4), np.uint8); sh[..., :3] = (40, 30, 90); sh[..., 3] = (a * 255).clip(0, 255).astype(np.uint8)
    out = Image.fromarray(sh, "RGBA"); out.alpha_composite(im, (pad, pad)); return out

def put(base, spr, cx, cy, ang=0.0, al=1.0, sc=1.0):
    if al <= 0.01 or spr is None: return
    if abs(sc - 1) > 0.003: spr = spr.resize((max(1, int(spr.width * sc)), max(1, int(spr.height * sc))), Image.BICUBIC)
    if abs(ang) > 0.05: spr = spr.rotate(ang, resample=Image.BICUBIC, expand=True)
    if al < 0.99:
        spr = spr.copy(); a = np.asarray(spr)[..., 3].astype(np.float32) * al
        spr.putalpha(Image.fromarray(a.astype(np.uint8)))
    x, y = int(round(cx - spr.width / 2)), int(round(cy - spr.height / 2))
    sx0, sy0 = max(0, -x), max(0, -y); sx1, sy1 = min(spr.width, W - x), min(spr.height, H - y)
    if sx1 <= sx0 or sy1 <= sy0: return
    if (sx0, sy0, sx1, sy1) != (0, 0, spr.width, spr.height): spr = spr.crop((sx0, sy0, sx1, sy1))
    base.alpha_composite(spr, (x + sx0, y + sy0))

_TC = {}
def tsprite(s, size, col=INK, wt=800, kind="baloo", shadow=True):
    k = (s, int(size), col, wt, kind, shadow)
    if k not in _TC:
        f = F(size * SS, wt, kind); bb = f.getbbox(s)
        im = Image.new("RGBA", (bb[2] - bb[0] + 40 * SS, bb[3] - bb[1] + 40 * SS), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((20 * SS - bb[0], 20 * SS - bb[1]), s, font=f, fill=col + (255,))
        im = down(im)
        _TC[k] = with_shadow(im, (0, 10), 8, 0.22, 30) if shadow else im
    return _TC[k]
def fit(s, size, maxw=W - 140, wt=800, kind="baloo"):
    while F(size, wt, kind).getlength(s) > maxw and size > 40: size -= 2
    return size

def title(base, s, size, cy, col, t, ph, al=1.0, maxw=W - 140, ent=1.0):
    size = fit(s, size, maxw)
    bob = 7 * math.sin(t * 1.3 + ph); ang = 1.4 * math.sin(t * 0.9 + ph * 1.7)
    put(base, tsprite(s, size, col), W / 2 + 4 * math.sin(t * 0.7 + ph), cy + bob + (1 - ent) * 90, ang, al * min(1, ent * 1.5))

_CC = {}
def card(w, h, fill=WHITE, r=46, key=None, deco=None):
    k = (w, h, fill, r, key)
    if k not in _CC:
        im = new(w, h); d = ImageDraw.Draw(im)
        rrect(d, (3, 3, w - 3, h - 3), r, fill + (255,), INK, 4)
        if deco: deco(d, w, h)
        _CC[k] = with_shadow(down(im), (0, 26), 20, 0.25, 60)
    return _CC[k]

# ---------- background: pastel cabin ----------
BW, BH = W + 120, H + 120
def make_bg():
    v = np.linspace(0, 1, BH, dtype=np.float32)[:, None, None]
    top = np.array([206, 198, 246], np.float32); bot = np.array([252, 214, 204], np.float32)
    a = np.broadcast_to(top * (1 - v) + bot * v, (BH, BW, 3)).copy()
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")
    lay = new(BW, BH); d = ImageDraw.Draw(lay)
    cols, rows = 3, 5; mx, my = 30, 30; pw = (BW - mx * (cols + 1)) / cols; ph = (BH - my * (rows + 1)) / rows
    for i in range(cols):
        for j in range(rows):
            x0 = mx + i * (pw + mx); y0 = my + j * (ph + my)
            rrect(d, (x0, y0, x0 + pw, y0 + ph), 44, (255, 255, 255, 46), (255, 255, 255, 120), 3)
            rrect(d, (x0 + 10, y0 + ph - 18, x0 + pw - 10, y0 + ph - 6), 6, (110, 90, 170, 26), None)
            for rx, ry in ((x0 + 26, y0 + 26), (x0 + pw - 26, y0 + 26), (x0 + 26, y0 + ph - 40), (x0 + pw - 26, y0 + ph - 40)):
                ell(d, (rx - 7, ry - 7, rx + 7, ry + 7), (255, 255, 255, 150), (120, 100, 180, 90), 2)
    # porthole
    cx, cy, R = BW / 2, 1120 + 60, 360
    ell(d, (cx - R - 46, cy - R - 46, cx + R + 46, cy + R + 46), (238, 234, 252, 255), INK + (255,), 5)
    for k in range(12):
        th = k * math.pi / 6; bx, by = cx + (R + 23) * math.cos(th), cy + (R + 23) * math.sin(th)
        ell(d, (bx - 8, by - 8, bx + 8, by + 8), (200, 192, 236, 255), INK + (255,), 3)
    ell(d, (cx - R, cy - R, cx + R, cy + R), NIGHT + (255,), INK + (255,), 5)
    im.alpha_composite(down(lay))
    # window contents: stars + Earth limb with glow (numpy, clipped to the round window)
    arr = np.asarray(im).astype(np.float32)
    yy, xx = np.mgrid[0:BH, 0:BW].astype(np.float32)
    win = np.clip((R - 3 - np.hypot(xx - cx, yy - cy)) / 2, 0, 1)
    ex, ey, er = cx - 120, cy + R + 900, 1150
    de = np.hypot(xx - ex, yy - ey) - er
    glow = np.exp(-np.clip(de, 0, None) / 40) * (de > 0) * 0.85
    earth = np.clip(-de / 2, 0, 1)
    shade = np.clip((yy - (ey - er)) / 400, 0, 1)
    ecol = np.stack([118 - 30 * shade, 178 - 40 * shade, 236 - 50 * shade], -1)
    rr_ = random.Random(47); st = np.zeros((BH, BW), np.float32)
    for _ in range(160):
        sx, sy = rr_.uniform(cx - R, cx + R), rr_.uniform(cy - R, cy + R)
        cv2.circle(st, (int(sx), int(sy)), rr_.choice((1, 1, 2, 3)), rr_.uniform(0.3, 1.0), -1, cv2.LINE_AA)
    rgb = arr[..., :3]
    rgb = rgb + (st * (1 - earth))[..., None] * (255 - rgb) * 0.9
    rgb = rgb + glow[..., None] * (np.array([170, 230, 255]) - rgb) * 0.8 * (1 - earth[..., None])
    rgb = rgb * (1 - earth[..., None]) + ecol * earth[..., None]
    # pastel continents (soft mint blobs)
    cn = np.zeros((BH, BW), np.float32)
    for _ in range(9):
        bx, by = rr_.uniform(cx - R, cx + R), rr_.uniform(ey - er + 40, ey - er + 380)
        cv2.ellipse(cn, (int(bx), int(by)), (int(rr_.uniform(60, 150)), int(rr_.uniform(20, 50))), rr_.uniform(-20, 20), 0, 360, 1, -1, cv2.LINE_AA)
    cn = cv2.GaussianBlur(cn, (0, 0), 6) * earth
    rgb = rgb * (1 - 0.7 * cn[..., None]) + np.array([150, 222, 180]) * 0.7 * cn[..., None]
    arr[..., :3] = arr[..., :3] * (1 - win[..., None]) + rgb * win[..., None]
    # inner rim highlight
    rim = np.clip(1 - np.abs(np.hypot(xx - cx, yy - cy) - (R - 18)) / 10, 0, 1) * np.clip((cy - yy) / R, 0, 1) * 0.35
    arr[..., :3] += rim[..., None] * (255 - arr[..., :3])
    # vignette
    vg = np.hypot((xx - BW / 2) / BW, (yy - BH / 2) / BH); arr[..., :3] *= (1 - 0.22 * np.clip(vg - 0.25, 0, 1) ** 1.2 * 2)[..., None]
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")
BG = make_bg()
def background(t):
    ox = 60 + 40 * math.sin(t * 0.21); oy = 60 + 30 * math.sin(t * 0.17 + 1)
    return BG.crop((int(ox), int(oy), int(ox) + W, int(oy) + H))

# ---------- props ----------
def draw_astro(s):
    """generic rounded astronaut, front view. s in [0,1] stretches torso + neck."""
    T = 210 * (1 + 0.20 * s); w_, h_ = 440, 330 + T + 260
    im = new(w_, h_); d = ImageDraw.Draw(im); cx = w_ / 2
    hy = 115; sh_y = hy + 95 + 18 * s; hip = sh_y + T
    rrect(d, (cx - 120, sh_y - 10, cx + 120, hip - 30), 40, (214, 206, 240, 255))                 # backpack
    for sx in (-1, 1):                                                                             # legs + boots
        capsule(d, (cx + sx * 50, hip - 10), (cx + sx * 64, hip + 175), 40, (246, 244, 255, 255))
        rrect(d, (cx + sx * 64 - 46, hip + 165, cx + sx * 64 + 46, hip + 225), 24, CORAL + (255,))
        rrect(d, (cx + sx * 64 - 34, hip + 172, cx + sx * 64 + 10, hip + 186), 7, (255, 170, 160, 255), None)
    for sx, ang in ((-1, 0.85), (1, 0.55)):                                                        # arms (floaty pose)
        a = (cx + sx * 88, sh_y + 30); b = (a[0] + sx * 150 * math.sin(ang + 0.6), a[1] + 150 * math.cos(ang + 0.6) - 40)
        capsule(d, a, b, 36, (246, 244, 255, 255))
        ell(d, (b[0] - 36, b[1] - 36, b[0] + 36, b[1] + 36), MINT + (255,))
    rrect(d, (cx - 100, sh_y, cx + 100, hip + 20), 60, (250, 248, 255, 255))                       # torso
    rrect(d, (cx - 100 + 10, sh_y + 10, cx - 60, hip + 10), 30, (232, 228, 248, 255), None)
    rrect(d, (cx - 70, sh_y + 40 + 0.25 * T, cx + 70, sh_y + 120 + 0.25 * T), 18, (232, 236, 255, 255))  # chest panel
    for k, c in enumerate((CORAL, MINT, BUTTER)):
        bx = cx - 38 + k * 38; by = sh_y + 80 + 0.25 * T; ell(d, (bx - 12, by - 12, bx + 12, by + 12), c + (255,), INK, 3)
    rrect(d, (cx - 100, hip - 30, cx + 100, hip - 6), 10, SKY + (255,), INK, 3)                       # belt
    rrect(d, (cx - 46, hy + 70, cx + 46, sh_y + 20), 16, (226, 222, 246, 255))                     # neck ring
    ell(d, (cx - 100, hy - 100, cx + 100, hy + 100), (252, 250, 255, 255))                            # helmet
    rrect(d, (cx - 72, hy - 52, cx + 72, hy + 50), 46, NIGHT + (255,), INK, 4)                       # visor
    d.arc(S((cx - 58, hy - 40, cx + 30, hy + 36)), 190, 250, fill=(255, 255, 255, 220), width=10 * SS)
    ell(d, (cx + 30, hy - 30, cx + 44, hy - 16), (255, 255, 255, 200), None)
    return down(im), hip + 225 + 50 - (h_ + 100) / 2
_AC = {}; AFOOT = {}
def astro(s):
    k = int(round(max(0, min(1, s)) * 24))
    if k not in _AC: im, AFOOT[k] = draw_astro(k / 24); _AC[k] = with_shadow(im, (0, 24), 18, 0.22, 50)
    return _AC[k]
def afoot(s): astro(s); return AFOOT[int(round(max(0, min(1, s)) * 24))]

def spine_spr(gap, curve, n=7, vw=170, vh=58, drops=None, sc=1.0):
    tot = n * vh + (n - 1) * gap
    w_, h_ = vw + 220, tot + 40
    im = new(w_, h_); d = ImageDraw.Draw(im); cx = w_ / 2 - 30
    y = 20; xs = [cx + curve * math.sin(math.pi * 1.6 * i / (n - 1) - 0.4) for i in range(n)]
    for i in range(n):
        x = xs[i]
        rrect(d, (x + vw / 2 - 20, y + 8, x + vw / 2 + 70, y + vh - 14), 16, BONE + (255,))       # spinous process
        rrect(d, (x - vw / 2, y, x + vw / 2, y + vh), 20, BONE + (255,))
        rrect(d, (x - vw / 2 + 12, y + 8, x - vw / 2 + 60, y + 18), 5, (255, 255, 255, 255), None)
        y += vh
        if i < n - 1:
            xm = (x + xs[i + 1]) / 2
            if gap > 3:
                rrect(d, (xm - vw / 2 + 12, y + 1, xm + vw / 2 - 12, y + gap - 1), min(gap / 2, 18), DISC + (255,), INK, 3)
                if gap > 14: rrect(d, (xm - vw / 2 + 30, y + 5, xm - 10, y + 5 + gap * 0.25), 4, (255, 205, 210, 255), None)
            y += gap
    return down(im)

def weight_spr(label="1g"):
    im = new(300, 190); d = ImageDraw.Draw(im)
    poly(d, [(60, 40), (240, 40), (285, 180), (15, 180)], (120, 110, 170, 255), INK, 5)
    rrect(d, (110, 6, 190, 48), 18, None, INK, 10)
    f = F(84 * SS, 800); d.text((150 * SS, 118 * SS), label, font=f, fill=(255, 255, 255, 255), anchor="mm")
    return with_shadow(down(im), (0, 16), 12, 0.2, 40)

def arrow_spr(col, L=120, up=False):
    im = new(80, L + 10); d = ImageDraw.Draw(im)
    pts = [(28, 5), (52, 5), (52, L - 44), (74, L - 44), (40, L + 2), (6, L - 44), (28, L - 44)]
    poly(d, pts, col + (255,), INK, 4)
    im = down(im)
    return im.rotate(180) if up else im

def drop_spr(r=18):
    im = new(2 * r + 12, 2.6 * r + 12); d = ImageDraw.Draw(im); cx = r + 6
    poly(d, [(cx, 6), (cx + r * 0.75, 6 + r * 1.0), (cx - r * 0.75, 6 + r * 1.0)], SKY + (255,), None)
    ell(d, (cx - r, 6 + r * 0.55, cx + r, 6 + r * 2.55), SKY + (255,), None)
    d.line(S([cx, 6, cx + r * 0.78, 6 + r * 1.05]), fill=INK + (255,), width=3 * SS)
    d.line(S([cx, 6, cx - r * 0.78, 6 + r * 1.05]), fill=INK + (255,), width=3 * SS)
    d.arc(S((cx - r, 6 + r * 0.55, cx + r, 6 + r * 2.55)), -35, 215, fill=INK + (255,), width=3 * SS)
    ell(d, (cx - r * 0.5, 6 + r * 1.2, cx - r * 0.1, 6 + r * 1.6), (255, 255, 255, 230), None)
    return down(im)
DROP = drop_spr()

def capsule_spr():
    im = new(420, 620); d = ImageDraw.Draw(im); cx = 210
    # parachute canopy with stripes
    for k in range(6):
        a0 = 180 + k * 30; c = CORAL if k % 2 == 0 else WHITE
        d.pieslice(S((cx - 200, 10, cx + 200, 330)), a0, a0 + 30, fill=c + (255,))
    d.arc(S((cx - 200, 10, cx + 200, 330)), 180, 360, fill=INK + (255,), width=5 * SS)
    d.line(S([cx - 200, 170, cx + 200, 170]), fill=INK + (255,), width=5 * SS)
    for k in range(6): d.line(S([cx - 200 + k * 80, 170, cx - 40 + k * 16, 420]), fill=INK + (255,), width=3 * SS)
    poly(d, [(cx - 50, 410), (cx + 50, 410), (cx + 100, 560), (cx - 100, 560)], (250, 248, 255, 255), INK, 5)
    rrect(d, (cx - 110, 548, cx + 110, 590), 16, (140, 120, 190, 255))
    ell(d, (cx - 26, 452, cx + 26, 504), NIGHT + (255,), INK, 4)
    ell(d, (cx - 14, 462, cx - 2, 474), (255, 255, 255, 220), None)
    return with_shadow(down(im), (0, 20), 14, 0.2, 40)
CAPS = capsule_spr()

def helmet_spr(r=56):
    im = new(2 * r + 12, 2 * r + 12); d = ImageDraw.Draw(im); c = r + 6
    ell(d, (c - r, c - r, c + r, c + r), (252, 250, 255, 255), INK, 4)
    rrect(d, (c - r * 0.72, c - r * 0.5, c + r * 0.72, c + r * 0.5), r * 0.46, NIGHT + (255,), INK, 4)
    d.arc(S((c - r * 0.6, c - r * 0.4, c + r * 0.3, c + r * 0.36)), 190, 250, fill=(255, 255, 255, 220), width=6 * SS)
    return down(im)
HELM = helmet_spr()

# loose floating objects
def obj_sprites():
    out = []
    im = new(200, 40); d = ImageDraw.Draw(im)                                                      # pencil
    rrect(d, (30, 6, 170, 34), 6, BUTTER + (255,)); rrect(d, (150, 6, 190, 34), 10, (255, 160, 180, 255))
    poly(d, [(30, 6), (30, 34), (4, 20)], (255, 220, 180, 255), INK, 4); out.append(down(im))
    im = new(80, 80); d = ImageDraw.Draw(im)                                                        # water blob
    ell(d, (6, 10, 74, 70), SKY + (220,)); ell(d, (20, 22, 36, 36), (255, 255, 255, 220), None); out.append(down(im))
    im = new(70, 70); d = ImageDraw.Draw(im)                                                        # bolt (hex nut)
    poly(d, [(35 + 28 * math.cos(k * math.pi / 3), 35 + 28 * math.sin(k * math.pi / 3)) for k in range(6)], (200, 192, 230, 255), INK, 4)
    ell(d, (24, 24, 46, 46), (150, 140, 200, 255), INK, 3); out.append(down(im))
    im = new(110, 130); d = ImageDraw.Draw(im)                                                      # notepad
    rrect(d, (6, 6, 104, 124), 12, (255, 255, 255, 255))
    for k in range(4): d.line(S([22, 36 + k * 20, 88, 36 + k * 20]), fill=(180, 170, 220, 255), width=3 * SS)
    rrect(d, (6, 6, 104, 22), 8, MINT + (255,)); out.append(down(im))
    return [with_shadow(o, (0, 14), 8, 0.18, 26) for o in out]
OBJ = obj_sprites()
FLOAT = [(0, 140, 760, 0.6, 17, 0.0), (1, 960, 690, 0.5, -11, 1.3), (2, 120, 1470, 0.45, 23, 2.1), (3, 940, 1460, 0.4, -14, 3.0)]
def loose(base, t, al=1.0):
    for i, x, y, sp, rot, ph in FLOAT:
        xx_ = x + 40 * math.sin(t * sp + ph); yy_ = y + 30 * math.sin(t * sp * 1.3 + ph * 2)
        put(base, OBJ[i], xx_, yy_, rot * t + ph * 40, al)

def ruler_spr(h=700, top_mark=None):
    w = 170
    im = new(w, h); d = ImageDraw.Draw(im)
    rrect(d, (4, 4, w - 4, h - 4), 34, (255, 255, 255, 255))
    rrect(d, (4, 4, 40, h - 4), 20, BUTTER + (255,), None); rrect(d, (4, 4, w - 4, h - 4), 34, None, INK, 4)
    for k in range(0, 33):
        y = h - 40 - k * (h - 80) / 32; L = 46 if k % 4 == 0 else 24
        d.line(S([w - 20 - L, y, w - 20, y]), fill=INK + (255,), width=3 * SS)
    return with_shadow(down(im), (0, 20), 16, 0.22, 50)
RULER = ruler_spr()
def ruler_y(v, cy, h=700): return cy + h / 2 - 40 - v * (h - 80)          # v in [0,1] along the scale

def tag(s, size, fill, col=WHITE, kind="baloo", wt=800, pad=(26, 10)):
    f = F(size * SS, wt, kind); bb = f.getbbox(s); tw = (bb[2] - bb[0]) / SS
    im = new(tw + 2 * pad[0] + 8, size * 1.05 + 2 * pad[1] + 8); d = ImageDraw.Draw(im)
    rrect(d, (4, 4, tw + 2 * pad[0] + 4, size * 1.05 + 2 * pad[1] + 4), 999, fill + (255,), INK, 4)
    d.text(((tw + 2 * pad[0] + 8) / 2 * SS, (size * 1.05 + 2 * pad[1] + 8) / 2 * SS), s, font=f, fill=col + (255,), anchor="mm")
    return with_shadow(down(im), (0, 10), 8, 0.2, 26)
_TG = {}
def TAG(*a, **k):
    key = (a, tuple(sorted(k.items())))
    if key not in _TG: _TG[key] = tag(*a, **k)
    return _TG[key]

# ---------- scene utilities ----------
def wt_(ln, i): return words[min(ln["_w0"] + i, ln["_w1"] - 1)][1] - ln["_s"]
def ent(lt, at=0.0, d=0.5): return back((lt - at) / d, 1.4)
def fd(lt, at, d=0.3): return ease((lt - at) / d)
def bob(t, ph, a=10): return a * math.sin(t * 1.1 + ph)

# ---------- scenes ----------
def S_hook(b, sc, ln, lt, dur, t, first=True):
    e = 1.0
    title(b, "ASTRONAUTS", 156, 235, INK, t, 0.0)
    title(b, "GET TALLER", 156, 395, CORAL, t, 1.1)
    title(b, "IN SPACE.", 124, 540, INK, t, 2.3)
    put(b, astro(1.0), 410, 1110 + bob(t, 0.4, 14), -7 + 3 * math.sin(t * 0.6))
    rc = 1080 + bob(t, 2.0, 8); put(b, RULER, 850, rc, 2 * math.sin(t * 0.7 + 1))
    put(b, TAG("ON EARTH", 30, INK, kind="nunito", wt=900), 850, ruler_y(0.2, rc) + 40, 0)
    put(b, TAG("+5 cm", 54, CORAL), 850, ruler_y(0.86, rc), 3 * math.sin(t * 1.4))
    put(b, arrow_spr(MINT, 120, up=True), 850, ruler_y(0.55, rc), 0)

def S_loop(b, sc, ln, lt, dur, t):
    title(b, "BUT WAIT FOR", 116, 250, INK, t, 0.3, ent=ent(lt, 0.0))
    title(b, "THE LANDING.", 150, 400, CORAL, t, 1.4, ent=ent(lt, 0.12))
    # pastel Earth rising from below
    er = 900; ey = 2460 - 120 * eout(lt / 1.2)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.ellipse((W / 2 - er - 30, ey - er - 30, W / 2 + er + 30, ey + er + 30), fill=(190, 230, 255, 120))
    d.ellipse((W / 2 - er, ey - er, W / 2 + er, ey + er), fill=SKY + (255,), outline=INK + (255,), width=5)
    for k, (dx, dy, rx, ry) in enumerate(((-300, -760, 160, 50), (120, -820, 220, 60), (380, -700, 120, 40))):
        d.ellipse((W / 2 + dx - rx, ey + dy - ry, W / 2 + dx + rx, ey + dy + ry), fill=(150, 222, 180, 255))
    b.alpha_composite(lay)
    yy_ = 760 + 300 * eout((lt - 0.1) / (dur + 0.4))
    put(b, CAPS, 540 + 30 * math.sin(t * 1.6), yy_ + (1 - ent(lt, 0.15)) * -200, 6 * math.sin(t * 1.6 + 0.5))
    put(b, TAG("TOUCHDOWN", 34, MINT, INK, kind="nunito", wt=900), 840, 1240 + bob(t, 1), 4, fd(lt, 0.6))

def S_squeeze(b, sc, ln, lt, dur, t):
    title(b, "GRAVITY", 160, 240, CORAL, t, 0.1, ent=ent(lt))
    title(b, "SQUEEZES YOU", 112, 400, INK, t, 1.0, ent=ent(lt, 0.1))
    k = wt_(ln, 3) - 0.1
    e = ent(lt, 0.05); cy = 1050 + (1 - e) * 260
    put(b, card(780, 860, (226, 246, 238), key="earth"), 540, cy + bob(t, 0.5, 6), 1.5 * math.sin(t * 0.8), min(1, e * 1.4))
    put(b, TAG("ON EARTH · 1g", 36, MINT, INK), 300, cy + 370, -4, min(1, e * 1.4))
    pr = ease((lt - k) / 0.35)
    pulse = 0.5 + 0.5 * math.sin((lt - k) * 5) if lt > k else 0
    gap = 26 - 20 * pr - 3 * pulse * pr
    sp = spine_spr(gap, 34, n=7)
    put(b, sp, 540, cy + 120 - sp.height / 2 + 120 + bob(t, 0.5, 6) * 0, 0, min(1, e * 1.4))
    top = cy + 240 - sp.height
    put(b, weight_spr(), 520, top - 80 - (1 - pr) * 70 + 4 * pulse, 0, min(1, e * 1.4) * fd(lt, k - 0.45, 0.3))
    for j, x in enumerate((300, 780)):
        put(b, arrow_spr(CORAL, 110), x, cy - 120 + 12 * math.sin(t * 6 + j), 0, pr)
    put(b, TAG("SQUISH", 40, CORAL), 830, cy + 280, 8, fd(lt, k + 0.2))

def S_stretch(b, sc, ln, lt, dur, t):
    title(b, "IN ORBIT:", 110, 230, INK, t, 0.6, ent=ent(lt))
    title(b, "NO SQUEEZE!", 150, 380, CORAL, t, 1.8, ent=ent(lt, 0.1))
    e = ent(lt, 0.05); cy = 1060 + (1 - e) * 260
    def deco(d, w, h):
        rr_ = random.Random(3)
        for _ in range(40):
            x, y, r = rr_.uniform(40, w - 40), rr_.uniform(40, h - 40), rr_.choice((2, 2, 3, 4))
            ell(d, (x - r, y - r, x + r, y + r), (255, 255, 255, 200), None)
    put(b, card(780, 880, NIGHT, key="orbit", deco=deco), 540, cy + bob(t, 2.0, 6), 1.5 * math.sin(t * 0.8 + 1), min(1, e * 1.4))
    put(b, TAG("IN ORBIT · 0g", 36, BUTTER, INK), 330, cy - 380, -4, min(1, e * 1.4))
    k = wt_(ln, 7) - 0.2                                        # "the spine stretches"
    u = ease((lt - k) / 1.0)
    gap = 6 + 20 * u; curve = 34 - 26 * u
    sp = spine_spr(gap, curve, n=7)
    bot = cy + 360
    put(b, sp, 540 + 6 * math.sin(t * 1.2), bot - sp.height / 2 + bob(t, 1.0, 8), 3 * math.sin(t * 0.9), min(1, e * 1.4))
    fl = ease((lt - 0.2) / 1.4)                                  # the weight drifts away, tumbling
    put(b, weight_spr("1g"), 520 + 260 * fl, bot - sp.height - 80 - 520 * fl, 40 * fl, (1 - fl) * min(1, e * 1.4))
    if u > 0:                                                     # length gauge
        y0, y1 = bot - 10, bot - sp.height + 30
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        x = 850
        d.line((x, y1 + 20, x, y0 - 20), fill=BUTTER + (int(255 * u),), width=8)
        d.polygon([(x - 22, y1 + 24), (x + 22, y1 + 24), (x, y1 - 8)], fill=BUTTER + (int(255 * u),))
        d.polygon([(x - 22, y0 - 24), (x + 22, y0 - 24), (x, y0 + 8)], fill=BUTTER + (int(255 * u),))
        b.alpha_composite(lay)
        put(b, TAG("STRETCH", 36, BUTTER, INK), 850, (y0 + y1) / 2, -90, u)

def S_discs(b, sc, ln, lt, dur, t):
    title(b, "THE DISCS", 120, 230, INK, t, 0.9, ent=ent(lt))
    k = wt_(ln, 7) - 0.15                                       # "puff up"
    sw = ease((lt - k) / 0.9)
    title(b, "PUFF UP!", 150 + 14 * sw, 385, CORAL, t, 2.0, ent=ent(lt, 0.1))
    e = ent(lt, 0.05); cy = 1060 + (1 - e) * 260; al = min(1, e * 1.4)
    put(b, card(800, 820, (236, 232, 255), key="disc"), 540, cy + bob(t, 3.0, 6), 1.2 * math.sin(t * 0.8 + 2), al)
    g = 60 + 70 * sw
    im = new(620, 560); d = ImageDraw.Draw(im); cx = 310; cyl = 280
    rrect(d, (cx - 230, cyl - g / 2 - 150, cx + 230, cyl - g / 2 - 6), 40, BONE + (255,))
    rrect(d, (cx - 200, cyl - g / 2 - 130, cx - 80, cyl - g / 2 - 112), 8, (255, 255, 255, 255), None)
    rrect(d, (cx - 230, cyl + g / 2 + 6, cx + 230, cyl + g / 2 + 150), 40, BONE + (255,))
    rrect(d, (cx - 200, cyl + g / 2 + 26, cx - 80, cyl + g / 2 + 44), 8, (255, 255, 255, 255), None)
    rrect(d, (cx - 200, cyl - g / 2, cx + 200, cyl + g / 2), g / 2, DISC + (255,), INK, 5)
    rrect(d, (cx - 160, cyl - g / 2 + 12, cx - 20, cyl - g / 2 + 12 + g * 0.2), 8, (255, 210, 215, 255), None)
    sp = with_shadow(down(im), (0, 14), 10, 0.18, 30)
    put(b, sp, 540, cy + 10 + bob(t, 3.0, 6), 0, al)
    for j in range(6):                                           # fluid drops drift in and get absorbed
        u = ((lt - 0.4 - j * 0.28) / 1.3)
        if 0 < u < 1:
            side = -1 if j % 2 == 0 else 1
            x = 540 + side * (420 - 230 * eout(u)); y = cy + 10 + (j % 3 - 1) * 40 * (1 - u)
            put(b, DROP, x, y, side * 90 * 0 + 30 * math.sin(t * 3 + j), (1 - ease((u - 0.75) / 0.25)) * al, 1.5 + 0.4 * (j % 2))
    put(b, TAG("BONE", 32, WHITE, INK, kind="nunito", wt=900), 270, cy - g / 2 - 210, -5, fd(lt, 0.5))
    put(b, TAG("DISC", 32, CORAL, WHITE, kind="nunito", wt=900), 830, cy + 10 + g / 2 + 40, 6, fd(lt, 0.8))
    put(b, TAG("+ FLUID", 32, SKY, WHITE, kind="nunito", wt=900), 830, cy - 300, -6, fd(lt, k))

def S_grow(b, sc, ln, lt, dur, t):
    k1 = wt_(ln, 3) - 0.1; k2 = wt_(ln, 9) - 0.1               # "up to 3%", "about 5"
    pct = max(1, 3 * ease((lt - k1 + 0.4) / 1.0))
    title(b, "UP TO", 96, 210, INK, t, 0.2, ent=ent(lt))
    title(b, f"{pct:.0f}% TALLER", 160, 360, CORAL, t, 1.1, ent=ent(lt, 0.1))
    s = ease((lt - k1 + 0.4) / 1.0)
    e = ent(lt, 0.05); al = min(1, e * 1.4)
    put(b, astro(s), 380, 1110 + bob(t, 0.4, 12) + (1 - e) * 260, -4 + 3 * math.sin(t * 0.6), al)
    rc = 1080 + bob(t, 2.0, 8) + (1 - e) * 260; put(b, RULER, 850, rc, 2 * math.sin(t * 0.7 + 1), al)
    m = 0.2 + 0.66 * s
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((770, ruler_y(m, rc) - 6, 930, ruler_y(m, rc) + 6), radius=6, fill=CORAL + (int(255 * al),))
    b.alpha_composite(lay)
    put(b, TAG("ON EARTH", 30, INK, kind="nunito", wt=900), 850, ruler_y(0.2, rc) + 40, 0, al)
    put(b, TAG("≈ 5 cm", 58, CORAL), 820, ruler_y(0.95, rc) - 30, 3 * math.sin(t * 1.4), fd(lt, k2, 0.25), 0.8 + 0.2 * back((lt - k2) / 0.4))
    put(b, TAG("for a tall adult", 42, WHITE, INK, kind="nunito", wt=900), 540, 505, 0, fd(lt, k2 - 0.9))

def S_land(b, sc, ln, lt, dur, t):
    k = wt_(ln, 4) - 0.15                                       # "gravity squeezes"
    title(b, "THEN THEY LAND...", 110, 220, INK, t, 0.4, ent=ent(lt))
    sq = ease((lt - k) / 0.7)
    title(b, "BACK TO NORMAL.", 128, 370, CORAL, t, 1.5, al=fd(lt, k + 0.2), ent=ent(lt, k + 0.2))
    # landing pad floor
    land = eout(lt / 0.6)
    fy = 1500 - 0 * land
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((40, fy - 40 + (1 - land) * 300, W - 40, fy + 20 + (1 - land) * 300), radius=30, fill=MINT + (255,), outline=INK + (255,), width=5)
    for x in range(110, W - 80, 120): d.line((x, fy - 28 + (1 - land) * 300, x + 50, fy - 28 + (1 - land) * 300), fill=(255, 255, 255, 200), width=6)
    b.alpha_composite(lay)
    s = 1 - sq
    sp = astro(s); drop_ = eout((lt - 0.1) / 0.5)
    bounce = 30 * math.sin(min(1, max(0, (lt - k) / 0.5)) * math.pi) * (1 - sq * 0)
    ay = fy - 36 - afoot(s) - (1 - drop_) * 300 + (bounce if lt > k else 0) * -0.5
    put(b, sp, 380, ay, -8 * (1 - drop_))
    rc = 1040; put(b, RULER, 850, rc, 0)
    m = 0.2 + 0.66 * s
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((770, ruler_y(m, rc) - 6, 930, ruler_y(m, rc) + 6), radius=6, fill=CORAL + (255,))
    b.alpha_composite(lay)
    put(b, TAG("ON EARTH", 30, INK, kind="nunito", wt=900), 850, ruler_y(0.2, rc) + 40, 0)
    for j, x in enumerate((180, 600)):
        put(b, arrow_spr(CORAL, 110), x, 740 + 14 * math.sin(t * 7 + j) + (1 - fd(lt, k - 0.2)) * -60, 0, fd(lt, k - 0.2) * (1 - fd(lt, k + 1.2, 0.4)))

def S_end(b, sc, ln, lt, dur, t):
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.35)
    title(b, "SOUNDS FAKE?", 128, 240, INK, t, 0.2, ent=ent(lt))
    y = 480 + bob(t, 0.3, 8); x0, x1, hh = 190, 890, 150
    lay = new(x1 - x0 + 20, hh + 20); d = ImageDraw.Draw(lay)
    rrect(d, (10, 10, x1 - x0 + 10, hh + 10), hh / 2, (255, 255, 255, 255), INK, 5)
    kx = hh / 2 + (x1 - x0 - hh) * on
    if on > 0.02: rrect(d, (20, 20, 10 + kx + hh / 2 - 10, hh), (hh - 20) / 2, MINT + (255,), None)
    rrect(d, (10, 10, x1 - x0 + 10, hh + 10), hh / 2, None, INK, 5)
    tog = with_shadow(down(lay), (0, 20), 14, 0.22, 40)
    put(b, tog, W / 2, y, 1.2 * math.sin(t * 0.9))
    put(b, tsprite("FAKE", 64, CORAL, shadow=False), (x0 + x1) / 2 + 70, y, 0, 1 - on)
    put(b, tsprite("TRUE", 64, INK, shadow=False), (x0 + x1) / 2 - 70, y, 0, ease((on - 0.5) / 0.4))
    put(b, with_shadow(HELM, (0, 10), 8, 0.2, 20), x0 + hh / 2 + (x1 - x0 - hh) * on, y, -360 * on + 8 * math.sin(t * 2))
    put(b, astro(0.6), 540, 1290 + bob(t, 1.0, 16) + (1 - ent(lt, click + 0.4)) * 120, 18 * math.sin(t * 0.5), fd(lt, click + 0.4, 0.3), 0.55)
    ec = ent(lt, click + 0.25); cy = 800 + bob(t, 2.0, 8) + (1 - ec) * 200
    put(b, card(860, 330, key="endcard"), 540, cy, 1.5 * math.sin(t * 0.8), min(1, ec * 1.5))
    put(b, tsprite("IT'S TRUE.", 150, CORAL, shadow=False), 540, cy - 50, 1.5 * math.sin(t * 0.8), fd(lt, click + 0.3))
    put(b, tsprite("Follow for more.", 70, INK, shadow=False), 540, cy + 90, 1.5 * math.sin(t * 0.8), fd(lt, click + 0.6))

SCENES = dict(hook=S_hook, loop=S_loop, squeeze=S_squeeze, stretch=S_stretch, discs=S_discs, grow=S_grow, land=S_land, end=S_end)

# ---------- audio ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
rng = np.random.default_rng(47)
def pluck(f, gain=0.05, dur=1.2):
    s = np.arange(int(dur * SR)) / SR
    sig = (np.sin(2 * np.pi * f * s) + 0.3 * np.sin(2 * np.pi * f * 2 * s) * np.exp(-s * 5)) * np.exp(-s * 3.2) * np.minimum(1, s / 0.01)
    return (sig * gain).astype(np.float32)
CH = [[174.61, 220.0, 261.63, 329.63], [146.83, 174.61, 220.0, 261.63], [116.54, 174.61, 220.0, 293.66], [130.81, 196.0, 246.94, 293.66]]
SC = [523.25, 587.33, 659.25, 698.46, 783.99, 880.0, 1046.5]
BEAT = 60 / 96; BAR = 4 * BEAT
rr = random.Random(47)
for bi in range(int(total / BAR) + 1):
    ch = CH[bi % 4]; s = np.arange(int(BAR * 1.4 * SR)) / SR
    env = np.minimum(1, s / 0.6) * np.exp(-s * 0.35)
    pad = sum(np.sin(2 * np.pi * f * s * (1 + dd)) / (1 + 0.4 * i) for i, f in enumerate(ch) for dd in (-0.003, 0.003))
    place(music, bi * BAR, (pad * env * 0.028).astype(np.float32))
    place(music, bi * BAR, pluck(ch[0] / 2, 0.08, 1.6))
    for k in range(8):
        if rr.random() < 0.55:
            f = rr.choice(SC); at = bi * BAR + k * BEAT / 2
            for e_, g in ((0, 0.045), (BEAT * 0.75, 0.02), (BEAT * 1.5, 0.009)): place(music, at + e_, pluck(f, g))
    for k in range(8):                                                       # soft shaker
        sl = np.arange(int(0.06 * SR)) / SR; z = rng.normal(0, 1, len(sl)) * np.exp(-sl * 60)
        place(music, bi * BAR + k * BEAT / 2 + BEAT / 4, z.astype(np.float32), 0.012 if k % 2 else 0.007)
def bloop(at, f0=300, f1=900, gain=0.12, dur=0.18):
    s = np.arange(int(dur * SR)) / SR; f = f0 + (f1 - f0) * s / dur
    place(music, at, (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * s / dur)).astype(np.float32), gain)
hook_hit(music, 0.3); bloop(0.02, 260, 1000, 0.12)
for i, ln in enumerate(spec["lines"]):
    st = ln["scene"]["type"]; s0 = ln["_s"]
    if i > 0: whoosh(music, s0, 0.1); bloop(s0 + 0.05, 300, 800, 0.08)
    if st == "squeeze": bloop(s0 + wt_(ln, 3) - 0.1, 500, 120, 0.14, 0.35)
    if st == "stretch": bloop(s0 + wt_(ln, 7) - 0.2, 200, 1200, 0.08, 0.9)
    if st == "discs":
        for j in range(6): bloop(s0 + 0.4 + j * 0.28 + 1.0, 700, 1300, 0.05, 0.08)
    if st == "grow": bloop(s0 + wt_(ln, 9) - 0.1, 600, 1400, 0.1, 0.12)
    if st == "land":
        sl = np.arange(int(0.5 * SR)) / SR; place(music, s0 + 0.4, (np.sin(2 * np.pi * (50 + 60 * np.exp(-sl * 18)) * sl) * np.exp(-sl * 7)).astype(np.float32), 0.35)
        bloop(s0 + wt_(ln, 4) - 0.15, 600, 150, 0.12, 0.5)
    if st == "end":
        c = s0 + ln["scene"].get("click_at", 0.45)
        sl = np.arange(int(0.04 * SR)) / SR; place(music, c, (rng.normal(0, 1, len(sl)) * np.exp(-sl * 120)).astype(np.float32), 0.25)
        for j, f in enumerate((698.46, 880.0, 1046.5, 1396.9)): place(music, c + 0.2 + j * 0.07, pluck(f, 0.07, 1.6))
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.42)

# ---------- compositing ----------
STARTS = [ln["_s"] for ln in spec["lines"]]
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 74
    f = F(size, 800)
    while f.getlength(" ".join(ws)) > W - 260 and size > 40: size -= 4; f = F(size, 800)
    tw_ = f.getlength(" ".join(ws)); x = (W - tw_) / 2; y = 1590
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([x - 50, y - 18, x + tw_ + 50, y + size + 14], radius=(size + 32) // 2, fill=INK + (245,), outline=(255, 255, 255, 255), width=4)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]
        d.text((x, y + size * 0.47), w, font=f, fill=(BUTTER if on else WHITE) + (255,), anchor="lm"); x += f.getlength(w + " ")

def scene_frame(t, ln):
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    b = background(t).copy()
    loose(b, t)
    SCENES[ln["scene"]["type"]](b, ln["scene"], ln, lt, dur, t)
    return b

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]
    b = scene_frame(t, ln)
    if ln["scene"]["type"] == "end":
        lt = t - ln["_s"]; dur = total - ln["_s"]; lp = ease((lt - (dur - 0.42)) / 0.38)
        if lp > 0: b = Image.blend(b, scene_frame(t, spec["lines"][0]), lp)
    for s in STARTS[1:]:                                           # soft pop ring on cuts
        u = (t - s) / 0.35
        if 0 <= u < 1:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); r = 80 + 900 * eout(u)
            d.ellipse((W / 2 - r, 1000 - r, W / 2 + r, 1000 + r), outline=(255, 255, 255, int(200 * (1 - u))), width=int(30 * (1 - u)) + 2)
            b.alpha_composite(lay)
    img = b.convert("RGB")
    caption(img, t)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 10, W, H], fill=(236, 230, 250)); d.rectangle([0, H - 10, int(W * t / total), H], fill=CORAL)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=22); print(f"done {total:.1f}s")
