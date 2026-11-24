"""Day 28 — ROMAN MOSAIC style (Romans, urine, teeth, laundry and Vespasian's tax).
The whole frame is a Roman floor mosaic. Every scene is drawn flat in a 8-colour stone palette (cream limestone, black,
terracotta, ochre, grey stone, oxblood, white marble, blue-green glass) into a palette-index image, then *tessellated*:
the floor is a fixed field of ~13 px tesserae laid in slightly wavy brick courses with jittered widths (opus tessellatum);
each tessera takes the majority colour of the drawing under it, gets its own tiny tone variation, a bevel from a
distance-field (light from the upper left) and dark mortar grout between stones. Moving things are 'living mosaic':
the drawing moves, the stones re-colour. A checker + terracotta border frames the floor.
Motion language: new elements are laid tile by tile (sweep or scatter reveal, freshly laid stones flash bright), every
scene change re-tiles the floor in a diagonal wave (stones flip with a lift), a polished-stone glint sweeps across the
floor every few seconds. Type: Cinzel Black inscriptions laid in stone with black outlines; captions on a crisp marble
tablet in Cinzel. Ending: a stone slider groove whose knob is a gold coin, FAKE -> TRUE, then the floor re-tiles back
into the hook (loop).
Music: original D-Dorian lyre (Karplus-Strong) over a reedy aulos-style drone + frame drum; stone clacks on re-tiles.
Usage: python3 engine/styles/day28_mosaic.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
_F = {}
def F(s, wt=900):
    k = (int(s), wt)
    if k not in _F:
        if wt == 900: f = ImageFont.truetype(f"{FONTS}/AlegreyaSC-Black.ttf", int(s))
        else:
            f = ImageFont.truetype(f"{FONTS}/Cinzel[wght].ttf", int(s))
            try: f.set_variation_by_axes([wt])
            except Exception: pass
        _F[k] = f
    return _F[k]

# ---------- palette ----------
CREAM, BLACK, TERRA, OCHRE, STONE, RED, WHITE, GLASS = range(8)
PAL = np.array([(229, 217, 190), (36, 31, 29), (178, 80, 46), (212, 156, 58), (150, 140, 124),
                (124, 42, 34), (247, 243, 233), (54, 104, 116)], np.float32)
K = len(PAL); NONE = 255
GROUT = np.array([74, 66, 58], np.float32)

# ---------- the tessera field (built once) ----------
T = 10
rng = np.random.default_rng(28)
def smooth_noise(n, scale, seed, amp):
    r = np.random.default_rng(seed).normal(0, 1, n // scale + 3)
    return np.interp(np.arange(n) / scale, np.arange(len(r)), r) * amp
yy, xx = np.mgrid[0:H, 0:W]
rowf = (yy + smooth_noise(W, 90, 1, 2.2)[None, :] + smooth_noise(W, 23, 2, 0.7)[None, :]) / T
ROW = np.floor(rowf).astype(np.int32) + 1
NR = ROW.max() + 2
LAB = np.zeros((H, W), np.int32); nid = 0
colnoise = smooth_noise(H, 70, 3, 1.8)[:, None] + smooth_noise(H, 17, 4, 0.6)[:, None]
xsh = xx + colnoise
for r in range(NR):
    m = ROW == r
    if not m.any(): continue
    widths = rng.uniform(T * 0.78, T * 1.22, W // 8)
    b = np.cumsum(widths) - rng.uniform(0, T)
    c = np.searchsorted(b, xsh[m])
    LAB[m] = nid + c; nid += len(b) + 1
_, LAB = np.unique(LAB, return_inverse=True); LAB = LAB.reshape(H, W).astype(np.int32)
N = LAB.max() + 1
LABF = LAB.ravel().astype(np.int64)
cnt = np.bincount(LABF, minlength=N).astype(np.float32)
CX = np.bincount(LABF, xx.ravel(), N) / np.maximum(cnt, 1)
CY = np.bincount(LABF, yy.ravel(), N) / np.maximum(cnt, 1)
# grout + bevel
edge = np.zeros((H, W), bool)
edge[:, 1:] |= LAB[:, 1:] != LAB[:, :-1]; edge[1:, :] |= LAB[1:, :] != LAB[:-1, :]
edge = cv2.dilate(edge.astype(np.uint8), np.ones((2, 2), np.uint8)).astype(bool)
dist = cv2.distanceTransform((~edge).astype(np.uint8), cv2.DIST_L2, 3)
dc = np.minimum(dist, 4.0)
gx = cv2.Sobel(dc, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(dc, cv2.CV_32F, 0, 1, ksize=3)
SHADE = (1.0 + 0.045 * (gx + gy) / 2 - 0.10 * np.clip(1 - dist / 3.0, 0, 1)).astype(np.float32)
pit = rng.random((H, W)) > 0.993
SHADE[pit] *= 0.9
SHADE = SHADE[..., None]
EDGE = edge[..., None]
TVAR = (1 + rng.normal(0, 0.045, N)).astype(np.float32)          # tone of each stone
TTINT = rng.normal(0, 5, (N, 3)).astype(np.float32)               # slight hue of each stone
GLOSS = rng.random(N).astype(np.float32) ** 3
TRND = rng.random(N).astype(np.float32)
SWEEP = (0.72 * CX / W + 0.28 * TRND).astype(np.float32)
DIAG = ((CX / W) * 0.45 + (CY / H) * 0.55) * 0.8 + 0.2 * TRND

def tile_mode(idx_img):
    a = np.asarray(idx_img, np.uint8).ravel().astype(np.int64)
    a = np.where(a == NONE, K, a)
    c = np.bincount(LABF * (K + 1) + a, minlength=N * (K + 1)).reshape(N, K + 1)
    m = c.argmax(1); m[m == K] = -1
    return m.astype(np.int16)

# ---------- drawing helpers (palette-index images, no antialias) ----------
def canvas(fill=NONE):
    im = Image.new("P", (W, H), fill); d = ImageDraw.Draw(im); d.fontmode = "1"; return im, d

def border(d):
    d.rectangle([0, 0, W, H], fill=CREAM)
    d.rectangle([0, 0, W - 1, H - 1], outline=BLACK, width=26)
    s = 26
    for x in range(26, W - 26, s):
        for y in (26, H - 52):
            d.rectangle([x, y, x + s - 1, y + s - 1], fill=BLACK if (x // s) % 2 else CREAM)
    for y in range(52, H - 52, s):
        for x in (26, W - 52):
            d.rectangle([x, y, x + s - 1, y + s - 1], fill=BLACK if (y // s) % 2 else CREAM)
    d.rectangle([52, 52, W - 53, H - 53], outline=TERRA, width=13)

def fit(s, size, maxw):
    while F(size).getlength(s) > maxw and size > 30: size -= 2
    return size

TXT = []
def text(d, s, size, x, y, fill=BLACK, outline=None, sw=4, maxw=900, anchor="ms", mosaic=False):
    """Inscriptions: crisp cut-marble inlays (opus sectile) laid over the mosaic; mosaic=True lays them in tesserae."""
    size = fit(s, size, maxw)
    if not mosaic:
        TXT.append((s, int(size), float(x), float(y), fill, outline, sw, anchor)); return
    if outline is None: d.text((x, y), s, font=F(size), fill=fill, anchor=anchor)
    else: d.text((x, y), s, font=F(size), fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=outline)

def star(d, x, y, r, fill):
    d.polygon([(x, y - r), (x + r * 0.25, y - r * 0.25), (x + r, y), (x + r * 0.25, y + r * 0.25),
               (x, y + r), (x - r * 0.25, y + r * 0.25), (x - r, y), (x - r * 0.25, y - r * 0.25)], fill=fill)

def coin(d, x, y, r, face="wreath", sx=1.0, label=""):
    rx = max(6, r * abs(sx))
    d.ellipse([x - rx - 10, y - r - 10, x + rx + 10, y + r + 10], fill=BLACK)
    d.ellipse([x - rx, y - r, x + rx, y + r], fill=OCHRE)
    if abs(sx) < 0.25: return
    for k in range(28):
        a = 2 * math.pi * k / 28
        px, py = x + math.cos(a) * rx * 0.84, y + math.sin(a) * r * 0.84
        d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=TERRA)
    if face == "wreath":
        for side in (-1, 1):
            for k in range(7):
                a = math.pi / 2 + side * (0.35 + k * 0.33)
                px, py = x + math.cos(a) * rx * 0.62, y + math.sin(a) * r * 0.62
                d.ellipse([px - 14 * abs(sx), py - 24, px + 14 * abs(sx), py + 24], fill=RED)
        if label: text(d, label, int(r * 0.42), x, y + r * 0.04, fill=BLACK, maxw=rx * 1.0, anchor="mm", mosaic=abs(sx) < 0.99)
    elif face == "q":
        if abs(sx) > 0.45: text(d, "?", int(r * 1.35), x, y + r * 0.08, fill=RED, outline=BLACK, sw=8, maxw=rx * 2.2, anchor="mm", mosaic=True)

def amphora(d, x, y, s=1.0, fill=TERRA):
    d.ellipse([x - 70 * s, y - 60 * s, x + 70 * s, y + 110 * s], fill=BLACK)
    d.ellipse([x - 58 * s, y - 48 * s, x + 58 * s, y + 98 * s], fill=fill)
    d.polygon([(x - 26 * s, y + 90 * s), (x + 26 * s, y + 90 * s), (x, y + 170 * s)], fill=BLACK)
    d.polygon([(x - 16 * s, y + 96 * s), (x + 16 * s, y + 96 * s), (x, y + 150 * s)], fill=fill)
    d.rectangle([x - 24 * s, y - 110 * s, x + 24 * s, y - 40 * s], fill=BLACK)
    d.rectangle([x - 14 * s, y - 100 * s, x + 14 * s, y - 40 * s], fill=fill)
    for sd in (-1, 1):
        d.arc([x + sd * 20 * s - 40 * s, y - 100 * s, x + sd * 20 * s + 40 * s, y - 10 * s], 270 if sd > 0 else 180,
              360 if sd > 0 else 270, fill=BLACK, width=int(12 * s))
    d.rectangle([x - 50 * s, y + 10 * s, x + 50 * s, y + 24 * s], fill=BLACK)

def smile(d, cx, cy, w, h):
    # lips (terracotta band), dark mouth, two rows of white teeth
    d.chord([cx - w / 2 - 40, cy - h - 40, cx + w / 2 + 40, cy + h + 40], 0, 180, fill=BLACK)
    d.chord([cx - w / 2 - 28, cy - h - 28, cx + w / 2 + 28, cy + h + 28], 0, 180, fill=TERRA)
    d.rectangle([cx - w / 2 - 40, cy - 36, cx + w / 2 + 40, cy - 6], fill=BLACK)
    d.chord([cx - w / 2, cy - h, cx + w / 2, cy + h], 0, 180, fill=BLACK)
    n = 8; tw = w * 0.86 / n
    for k in range(n):
        x0 = cx - w * 0.43 + k * tw
        th = 78 if 2 <= k <= 5 else 62
        d.rounded_rectangle([x0 + 4, cy + 2, x0 + tw - 4, cy + th], radius=10, fill=WHITE)
    for k in range(n - 2):
        x0 = cx - w * 0.33 + k * tw
        d.rounded_rectangle([x0 + 5, cy + h * 0.52, x0 + tw - 5, cy + h * 0.52 + 52], radius=8, fill=WHITE)

def plaque(d, s, y, size=58, fill=STONE, ink=BLACK, maxw=820):
    size = fit(s, size, maxw)
    tw = F(size).getlength(s)
    d.rectangle([W / 2 - tw / 2 - 40, y - size - 26, W / 2 + tw / 2 + 40, y + 30], fill=BLACK)
    d.rectangle([W / 2 - tw / 2 - 28, y - size - 14, W / 2 + tw / 2 + 28, y + 18], fill=fill)
    text(d, s, size, W / 2, y - 4, fill=ink, maxw=maxw)

def wstart(ln, i): return words[min(ln["_w0"] + i, ln["_w1"] - 1)][1] - ln["_s"]

# ---------- scenes: each returns a list of layers (key, draw_fn, prog, order) ----------
_cache = {}
def layer_modes(layers):
    global TXT
    out = []
    for key, fn, prog, order in layers:
        if key is not None and key in _cache: m, items = _cache[key]
        else:
            TXT = []
            im, d = canvas(); fn(d); m = tile_mode(im); items = TXT
            if key is not None: _cache[key] = (m, items)
        out.append((m, prog, order, items))
    return out

def base(key, fn):
    def f(d): border(d); fn(d)
    return (key, f, 1.0, None)

def hook(ln, lt, dur, t):
    def b(d):
        text(d, "BRUSHED TEETH", 124, W / 2, 250, maxw=900)
        text(d, "WITH URINE?!", 150, W / 2, 420, fill=OCHRE, outline=BLACK, sw=6, maxw=880)
        smile(d, W / 2, 760, 720, 280)
        amphora(d, 220, 1290, 0.95, OCHRE)
    def sp(d):
        for k, (x, y, r) in enumerate(((170, 610, 64), (920, 610, 80), (760, 1180, 60), (420, 1150, 48), (930, 1330, 64))):
            rr = r * (0.75 + 0.35 * math.sin(t * 7 + k * 1.7))
            star(d, x, y, rr, WHITE if k % 2 else OCHRE)
    def dr(d):
        x = 600; y = 1150 + ((lt * 380) % 240)
        d.ellipse([x - 60, y - 10, x + 60, y + 110], fill=BLACK); d.polygon([(x - 54, y + 40), (x + 54, y + 40), (x, y - 70)], fill=BLACK)
        d.ellipse([x - 48, y + 2, x + 48, y + 98], fill=OCHRE); d.polygon([(x - 40, y + 40), (x + 40, y + 40), (x, y - 50)], fill=OCHRE)
    return [base("hook", b), (None, sp, 1.0, None), (None, dr, 1.0, None)]

def tease(ln, lt, dur, t):
    def b(d):
        text(d, "IN ROME IT GETS", 96, W / 2, 230, maxw=880)
        text(d, "WEIRDER", 170, W / 2, 420, fill=TERRA, outline=BLACK, sw=6)
    sx = math.cos(lt * 5.0)
    def c(d): coin(d, W / 2, 860, 290, "q" if sx > 0 else "wreath", sx)
    def p(d): plaque(d, "WAIT FOR THE END", 1340, 64, fill=OCHRE)
    return [base("tease", b), (None, c, 1.0, None), ("tease_p", p, eout((lt - wstart(ln, 6)) / 0.4), SWEEP)]

def poet(ln, lt, dur, t):
    def b(d):
        text(d, "A ROMAN POET", 110, W / 2, 220)
        text(d, "CATULLUS", 150, W / 2, 390, fill=TERRA, outline=BLACK, sw=6)
        d.rectangle([150, 520, 930, 1080], fill=BLACK); d.rectangle([164, 534, 916, 1066], fill=OCHRE)
        for x in (120, 900):
            d.rounded_rectangle([x, 500, x + 60, 1100], radius=28, fill=BLACK)
            d.rounded_rectangle([x + 10, 510, x + 50, 1090], radius=20, fill=TERRA)
    def wr(d):
        for k in range(8):
            y = 590 + k * 58; L = 560 - 70 * (k % 3)
            d.rectangle([220, y, 220 + L, y + 14], fill=BLACK)
    def q(d):
        k = min(7, int(lt / 0.5)); qx = 220 + min(1, (lt % 0.5) / 0.5) * (560 - 70 * (k % 3)); qy = 590 + k * 58
        d.polygon([(qx, qy), (qx + 20, qy - 120), (qx + 120, qy - 330), (qx + 150, qy - 300), (qx + 70, qy - 90)], fill=BLACK)
        d.polygon([(qx + 10, qy - 24), (qx + 30, qy - 120), (qx + 122, qy - 308), (qx + 134, qy - 296), (qx + 60, qy - 100)], fill=WHITE)
        d.line([(qx + 6, qy - 10), (qx + 120, qy - 300)], fill=STONE, width=6)
    def y2(d): plaque(d, "OVER 2,000 YEARS AGO", 1200, 60, fill=CREAM)
    def grin(d):
        smile(d, W / 2, 1330, 380, 120)
        star(d, 300, 1330, 46 * (0.8 + 0.3 * math.sin(t * 8)), OCHRE); star(d, 790, 1300, 40 * (0.8 + 0.3 * math.sin(t * 8 + 2)), WHITE)
    g_at = wstart(ln, 10)
    return [base("poet", b), ("poet_w", wr, min(1, lt / 4.0), SWEEP), (None, q, 1.0, None),
            ("poet_y", y2, eout(lt / 0.5), TRND), (None, grin, eout((lt - g_at + 0.3) / 0.4), None)]

IBERIA = [(-9.2, 43.2), (-8.0, 43.7), (-5.5, 43.5), (-3.5, 43.4), (-1.8, 43.3), (0.5, 42.7), (3.2, 42.4), (3.2, 41.9),
          (1.0, 41.0), (0.0, 39.9), (-0.3, 39.4), (0.2, 38.8), (-0.7, 37.6), (-2.1, 36.7), (-4.4, 36.7), (-5.6, 36.0),
          (-6.4, 36.8), (-7.4, 37.2), (-8.9, 37.0), (-8.8, 38.4), (-9.5, 38.8), (-8.9, 40.2), (-8.7, 42.0), (-9.3, 42.9)]
def spain(ln, lt, dur, t):
    def b(d):
        text(d, "HIS JOKE:", 100, W / 2, 210)
        text(d, "A HABIT FROM SPAIN", 112, W / 2, 360, fill=TERRA, outline=BLACK, sw=5, maxw=900)
        d.rectangle([96, 470, W - 96, 1300], fill=BLACK); d.rectangle([108, 482, W - 108, 1288], fill=GLASS)
        for k in range(7):
            y = 520 + k * 118
            for x in range(140, W - 160, 120):
                d.arc([x, y, x + 60, y + 30], 200, 340, fill=CREAM, width=6)
        sc = 800 / 13.0
        pts = [(W / 2 + (lo + 3.0) * sc * 0.78, 880 - (la - 40.0) * sc) for lo, la in IBERIA]
        d.polygon(pts, fill=BLACK)
        cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
        d.polygon([(cx + (x - cx) * 0.96, cy + (y - cy) * 0.95) for x, y in pts], fill=OCHRE)
        text(d, "HISPANIA", 76, cx + 10, cy + 30, fill=BLACK, maxw=560)
    def cup(d):
        k = eout(lt / 0.5); x, y = 860, 1180 - 30 * k
        d.polygon([(x - 80, y - 80), (x + 80, y - 80), (x + 55, y + 70), (x - 55, y + 70)], fill=BLACK)
        d.polygon([(x - 66, y - 68), (x + 66, y - 68), (x + 45, y + 58), (x - 45, y + 58)], fill=WHITE)
        d.rectangle([x - 62, y - 66, x + 62, y - 40], fill=OCHRE)
    def pin(d):
        u = ((lt * 2.2) % 1.0); r = 20 + 60 * u
        x, y = 470, 840
        d.ellipse([x - 22, y - 22, x + 22, y + 22], fill=RED)
        if u < 0.85: d.ellipse([x - r, y - r, x + r, y + r], outline=RED, width=10)
    return [base("spain", b), (None, cup, 1.0, None), (None, pin, 1.0, None)]

def fullers(ln, lt, dur, t):
    def b(d):
        text(d, "ROMAN LAUNDRY", 110, W / 2, 200, maxw=900)
        d.line([(90, 360), (W - 90, 360)], fill=BLACK, width=10)
        d.polygon([(250, 1080), (830, 1080), (770, 1440), (310, 1440)], fill=BLACK)
        d.polygon([(266, 1094), (814, 1094), (758, 1426), (322, 1426)], fill=TERRA)
        for y in (1180, 1300): d.line([(290, y), (790, y)], fill=RED, width=10)
        d.rectangle([236, 1060, 844, 1100], fill=BLACK)
        d.ellipse([280, 1040, 800, 1110], fill=OCHRE)
    def toga(d):
        sw = 10 * math.sin(t * 2.2)
        d.polygon([(170, 364), (910, 364), (880 + sw, 720), (720 + sw, 660), (540 + sw, 740), (360 + sw, 660), (200 + sw, 720)], fill=BLACK)
        d.polygon([(186, 372), (894, 372), (864 + sw, 700), (720 + sw, 644), (540 + sw, 722), (360 + sw, 644), (216 + sw, 700)], fill=WHITE)
        for x in (330, 540, 750): d.line([(x, 380), (x + sw, 650)], fill=CREAM, width=12)
        for k, (x, y) in enumerate(((250, 470), (840, 520), (600, 600))):
            star(d, x, y, 44 * (0.7 + 0.4 * math.sin(t * 6 + k * 2)), OCHRE)
    def legs(d):
        for k, x in enumerate((450, 630)):
            up = 60 * max(0, math.sin(t * 7 + k * math.pi))
            y0, y1 = 780, 1070 - up
            d.rectangle([x - 34, y0, x + 34, y1], fill=BLACK); d.rectangle([x - 22, y0, x + 22, y1 - 6], fill=TERRA)
            d.rounded_rectangle([x - 44, y1 - 30, x + 54, y1 + 10], radius=12, fill=BLACK)
        for k in range(6):
            u = (t * 0.9 + k / 6) % 1; bx = 320 + (k * 97) % 440; by = 1070 - u * 120
            d.ellipse([bx - 16, by - 16, bx + 16, by + 16], fill=WHITE)
    def am(d): plaque(d, "AMMONIA = WHITER WOOL", 1270 + 230, 54, fill=OCHRE, maxw=760)
    am_at = wstart(ln, 8)
    return [base("fullers", b), (None, legs, 1.0, None), (None, toga, eout((lt - 0.1) / 0.6), None),
            ("fullers_am", am, eout((lt - am_at) / 0.45), SWEEP)]

def tax(ln, lt, dur, t):
    def b(d):
        text(d, "SO VALUABLE", 110, W / 2, 210)
        text(d, "IT WAS TAXED", 130, W / 2, 370, fill=TERRA, outline=BLACK, sw=6)
        d.rectangle([66, 1330, W - 66, 1470], fill=STONE)
        for y in (1370, 1420):
            for x in range(80 + (y // 50 % 2) * 40, W - 80, 80): d.rectangle([x, y, x + 64, y + 36], fill=CREAM)
    def jars(d):
        for k, x in enumerate((170, 390, 690, 910)):
            if lt > 0.15 * k: amphora(d, x, 1150, 0.95, TERRA if k % 2 else OCHRE)
    def cn(d):
        u = back(min(1, max(0, (lt - wstart(ln, 4)) / 0.4)), 1.6)
        r = 230 * max(0.05, u); coin(d, W / 2, 760, r, "wreath", 1.0, "TAX")
    return [base("tax", b), (None, jars, 1.0, None), (None, cn, 1.0, None)]

def coinsc(ln, lt, dur, t):
    def b(d):
        # generic profile nose + lip on the right edge
        pts = [(W - 66, 560), (860, 600), (700, 900), (660, 960), (720, 1000), (800, 1010), (820, 1060), (W - 66, 1080)]
        d.polygon(pts, fill=BLACK)
        d.polygon([(W - 66, 578), (872, 616), (720, 900), (686, 952), (726, 984), (810, 994), (836, 1060), (W - 66, 1062)], fill=TERRA)
        d.ellipse([890, 690, 970, 730], fill=BLACK); d.ellipse([916, 698, 948, 724], fill=WHITE)
        d.line([(870, 660), (980, 650)], fill=BLACK, width=16)
        d.arc([740, 930, 800, 990], 90, 250, fill=BLACK, width=10)
    ms = wstart(ln, 15)
    sm = wstart(ln, 14)
    def head(d):
        if lt < ms - 0.1:
            text(d, "A TAX COIN", 110, W / 2, 220, maxw=880)
            text(d, "TO HIS SON'S NOSE", 120, W / 2, 380, fill=TERRA, outline=BLACK, sw=6, maxw=900)
    def money(d):
        text(d, "MONEY DOESN'T", 108, W / 2, 220, maxw=900)
        text(d, "STINK!", 190, W / 2, 420, fill=OCHRE, outline=BLACK, sw=7)
    u = eout(lt / 1.2)
    cx, cy = 180 + 260 * u, 1400 - 380 * u
    def c(d):
        coin(d, cx, cy, 170, "wreath", math.cos(lt * 3) if lt < 1.2 else 1.0, "TAX")
    def sniff(d):
        if lt > 1.0:
            for k in range(3):
                ph = (lt * 1.5 + k / 3) % 1
                x = 690 - ph * 40; y0 = 1010 - k * 46
                pts = [(x - j * 12, y0 + 16 * math.sin(j * 0.9 + lt * 6)) for j in range(7)]
                d.line(pts, fill=STONE, width=14)
        if lt > sm:
            k = eout((lt - sm) / 0.25); x, y, r = 300, 720, 110 * k
            d.line([(x - r, y - r), (x + r, y + r)], fill=RED, width=34)
            d.line([(x - r, y + r), (x + r, y - r)], fill=RED, width=34)
    L = [base("coin", b), (None, head, 1.0, None), (None, c, 1.0, None), (None, sniff, 1.0, None)]
    if lt > ms - 0.1: L.append(("coin_money", money, eout((lt - ms + 0.1) / 0.35), SWEEP))
    return L

def end(ln, lt, dur, t):
    c = ln["scene"].get("click_at", 0.5)
    def b(d):
        text(d, "SOUNDS FAKE?", 124, W / 2, 270)
        d.rounded_rectangle([150, 790, 930, 1010], radius=110, fill=BLACK)
        d.rounded_rectangle([166, 806, 914, 994], radius=94, fill=STONE)
        text(d, "FAKE", 86, 290, 1130, fill=BLACK)
        text(d, "TRUE", 86, 790, 1130, fill=TERRA)
    u = back(min(1, max(0, (lt - c) / 0.4)), 1.2)
    kx = 260 + (820 - 260) * u
    def knob(d): coin(d, kx, 900, 86, "wreath", 1.0)
    def tr(d):
        text(d, "IT'S TRUE.", 150, W / 2, 470, fill=TERRA, outline=BLACK, sw=6)
        d.rectangle([660, 1150, 920, 1166], fill=RED)
    def fo(d): text(d, "FOLLOW FOR MORE", 80, W / 2, 1330, fill=BLACK)
    return [base("end", b), (None, knob, 1.0, None), ("end_t", tr, eout((lt - c - 0.25) / 0.35), SWEEP),
            ("end_f", fo, eout((lt - 0.9) / 0.5), TRND)]

SCENES = {"hook": hook, "tease": tease, "poet": poet, "spain": spain, "fullers": fullers, "tax": tax, "coin": coinsc, "end": end}

# ---------- narration + music ----------
voice, words, total = narrate(spec, lead=0.08)
n = len(voice); music = np.zeros(n, np.float32); mr = np.random.default_rng(280)

def pluck(f, dur=1.6, bright=0.5, decay=0.996):
    L = int(dur * SR); Np = max(2, int(SR / f))
    y = np.zeros(L + Np + 1, np.float32)
    y[:Np + 1] = mr.uniform(-1, 1, Np + 1) * np.hanning(Np + 1)
    for st in range(Np + 1, L + Np + 1, Np):
        e = min(st + Np, L + Np + 1)
        y[st:e] = decay * ((1 - bright * 0.5) * y[st - Np:e - Np] + bright * 0.5 * y[st - Np - 1:e - Np - 1])
    out = y[Np + 1:Np + 1 + L]
    return out / (np.abs(out).max() + 1e-6)

def drum(at, gain=0.25, low=True):
    s = np.arange(int(0.5 * SR)) / SR
    if low: sig = np.sin(2 * np.pi * (70 + 40 * np.exp(-s * 25)) * s) * np.exp(-s * 9)
    else: sig = mr.normal(0, 1, len(s)) * np.exp(-s * 45) * 0.6 + np.sin(2 * np.pi * 320 * s) * np.exp(-s * 30) * 0.4
    place(music, at, sig.astype(np.float32), gain)

def clack(at, gain=0.05):
    s = np.arange(int(0.04 * SR)) / SR
    f = mr.uniform(1800, 3200)
    place(music, at, (np.sin(2 * np.pi * f * s) * np.exp(-s * 160) + mr.normal(0, 0.3, len(s)) * np.exp(-s * 200)).astype(np.float32), gain)

DOR = [146.83, 164.81, 174.61, 196.0, 220.0, 246.94, 261.63, 293.66, 329.63, 349.23, 392.0, 440.0]   # D Dorian
BEAT = 60 / 104
pat = [7, 9, 10, 9, 7, 6, 4, 6, 7, 4, 5, 6, 7, 9, 11, 10]
for k in range(int(total / BEAT * 2)):
    at = k * BEAT / 2
    if k % 2 == 0 or k % 8 in (3, 7):
        place(music, at, pluck(DOR[pat[k % 16]], 1.3, 0.55), 0.075)
    if k % 8 == 0:
        place(music, at, pluck(DOR[0] / 2, 2.2, 0.3, 0.998), 0.07); place(music, at, pluck(DOR[4] / 2, 2.2, 0.3, 0.998), 0.05)
    if k % 4 == 0: drum(at, 0.16, True)
    if k % 4 == 2: drum(at, 0.07, False)
s_ = np.arange(n) / SR
ph = 2 * np.pi * 73.42 * s_ * (1 + 0.002 * np.sin(2 * np.pi * 4.8 * s_))
reed = sum(np.sin(h * ph) / h ** 0.9 for h in (1, 2, 3, 4, 5, 6)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.15 * s_))
music += (reed * 0.018 + np.sin(2 * np.pi * 110 * s_) * 0.012).astype(np.float32)
hook_hit(music, 0.32); drum(0.0, 0.3, True)
for i, ln in enumerate(spec["lines"]):
    s0 = ln["_s"]; st = ln["scene"]["type"]
    if i > 0:
        whoosh(music, s0 - 0.1, 0.07, 0.3); drum(s0 - 0.1, 0.22, True)
        for k in range(14): clack(s0 - 0.12 + k * 0.032 + mr.uniform(0, 0.02), 0.035)
    if st == "tax": drum(s0 + wstart(ln, 4) + 0.1, 0.3, True)
    if st == "coin":
        drum(s0 + wstart(ln, 11), 0.22, False); drum(s0 + wstart(ln, 13), 0.32, True)
    if st == "end":
        c = s0 + ln["scene"].get("click_at", 0.5)
        drum(c + 0.4, 0.35, True)
        for j, fq in enumerate((293.66, 349.23, 440.0, 587.33)): place(music, c + 0.45 + j * 0.08, pluck(fq, 1.6, 0.7), 0.09)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.45)

# ---------- compositing ----------
def tiles_for(t, ln):
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    L = layer_modes(SCENES[ln["scene"]["type"]](ln, lt, dur, t))
    idx = L[0][0].copy(); fresh = np.zeros(N, np.float32); texts = [(L[0][3], 1.0)]
    for m, prog, order, items in L[1:]:
        if prog <= 0: continue
        texts.append((items, prog))
        has = m >= 0
        if order is None or prog >= 1: on = has
        else:
            p = prog * 1.08
            on = has & (order < p)
            fresh = np.maximum(fresh, (has & (order < p) & (order > p - 0.08)).astype(np.float32))
        idx[on] = m[on]
    return idx, fresh, texts

# ---------- cut-marble inscriptions ----------
_mr = np.random.default_rng(7)
def _fbm(scales, amps, seed):
    r = np.random.default_rng(seed); acc = np.zeros((H, W), np.float32)
    for sc, a in zip(scales, amps):
        g = r.random((H // sc + 2, W // sc + 2)).astype(np.float32)
        acc += a * cv2.resize(g, (W, H), interpolation=cv2.INTER_CUBIC)
    return (acc - acc.min()) / (acc.max() - acc.min())
_v = _fbm([300, 90, 30, 9], [1, .5, .25, .12], 70)
MARB = (0.93 + 0.08 * _fbm([200, 50, 12], [1, .4, .2], 71) - 0.10 * np.exp(-((np.sin(_v * 14 + yy / 260.0)) / 0.12) ** 2)).astype(np.float32)
_tcache = {}
def inlay(item):
    if item in _tcache: return _tcache[item]
    s, size, x, y, fill, outline, sw, anchor = item
    f = F(size); swo = sw if outline is not None else 0
    pad = 30 + swo
    l, tp, r, b = f.getbbox(s, anchor=anchor, stroke_width=swo)
    x0, y0 = int(x + l) - pad, int(y + tp) - pad; w, h = int(r - l) + 2 * pad, int(b - tp) + 2 * pad
    mS = Image.new("L", (w, h), 0); mF = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mS).text((x - x0, y - y0), s, font=f, fill=255, anchor=anchor, stroke_width=swo)
    ImageDraw.Draw(mF).text((x - x0, y - y0), s, font=f, fill=255, anchor=anchor)
    S = np.asarray(mS, np.float32) / 255; Fm = np.asarray(mF, np.float32) / 255
    sh = np.roll(np.roll(cv2.GaussianBlur(S, (0, 0), 3), 6, 0), 4, 1) * 0.45           # seat shadow on the floor
    hi = np.clip(Fm - np.roll(np.roll(Fm, 3, 0), 3, 1), 0, 1)                          # cut-edge highlight
    lo = np.clip(Fm - np.roll(np.roll(Fm, -3, 0), -3, 1), 0, 1)
    ys, xs = slice(max(0, y0), min(H, y0 + h)), slice(max(0, x0), min(W, x0 + w))
    oy, ox = ys.start - y0, xs.start - x0
    ny, nx = ys.stop - ys.start, xs.stop - xs.start
    S, Fm, sh, hi, lo = (a[oy:oy + ny, ox:ox + nx] for a in (S, Fm, sh, hi, lo))
    fc = PAL[fill][None, None, :] * MARB[ys, xs][..., None]
    fc = fc * (1 + 0.35 * hi[..., None] - 0.25 * lo[..., None])
    oc = PAL[outline if outline is not None else fill][None, None, :] * np.ones_like(fc)
    col = oc * (1 - Fm[..., None]) + fc * Fm[..., None]
    res = (ys, xs, S, sh, col)
    _tcache[item] = res; return res

def draw_texts(img, texts, alpha=1.0):
    for items, prog in texts:
        a = alpha * min(1.0, max(0.0, prog))
        if a <= 0: continue
        for it in items:
            ys, xs, S, sh, col = inlay(it)
            A = S; shm = sh
            if prog < 1:   # laid left to right
                ww = S.shape[1]; cut = prog * 1.15 * ww
                cm = np.clip((cut - np.arange(ww)[None, :]) / 40.0, 0, 1)
                A = S * cm; shm = sh * cm
                a = alpha
            reg = img[ys, xs]
            reg *= (1 - (shm * a)[..., None])
            img[ys, xs] = reg * (1 - (A * a)[..., None]) + col * (A * a)[..., None]

def colors(idx, fresh, t):
    col = PAL[idx] * TVAR[:, None] + TTINT
    g = (t % 4.2) / 4.2 * 1.6 - 0.3                       # polished-stone glint band sweeping diagonally
    band = np.exp(-(((CX / W) * 0.5 + (CY / H) * 0.5 - g) / 0.05) ** 2)
    col = col * (1 + (0.22 * GLOSS * band + 0.25 * fresh)[:, None])
    return col

def frame_rgb(t):
    lines = spec["lines"]; ln = active_line(spec, t) or lines[0]; i = lines.index(ln)
    idx, fresh, texts = tiles_for(t, ln)
    col = colors(idx, fresh, t)
    trans = None
    if i > 0 and t < ln["_s"] + 0.42: trans = (lines[i - 1], (t - (ln["_s"] - 0.12)) / 0.54)
    if t > total - 0.6: trans = ("loop", (t - (total - 0.6)) / 0.6)
    tl = [(texts, 1.0)]
    if trans is not None:
        src, ph = trans
        if src == "loop":   # re-tile forward into the hook (seamless replay)
            oi, of, otx = tiles_for(lines[0]["_s"], lines[0]); oc = colors(oi, of, t)
            flip = DIAG < ph
            new = np.where(flip[:, None], oc, col)
            tl = [(texts, 1 - 2 * ph), (otx, 2 * ph - 1)]
        else:
            oi, of, otx = tiles_for(src["_s"] + max(0.0, src["_se"] - src["_s"] - 0.13), src); oldc = colors(oi, of, t)
            flip = DIAG < ph; new = np.where(flip[:, None], col, oldc)
            tl = [(otx, 1 - 2 * ph), (texts, 2 * ph - 1)]
        lift = np.exp(-((DIAG - ph) / 0.05) ** 2)
        col = new * (1 + 0.35 * lift[:, None])
    img = col[LAB] * SHADE
    img = np.where(EDGE, GROUT, img).astype(np.float32)
    for tx, a in tl:
        if a > 0: draw_texts(img, tx, min(1.0, a))
    return img

def caption(O, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0].upper() for i in g]; size = 70; f = F(size, 800)
    while f.getlength(" ".join(ws)) > W - 240 and size > 40: size -= 4; f = F(size, 800)
    tw_ = f.getlength(" ".join(ws)); x = (W - tw_) / 2; y = 1600
    d = ImageDraw.Draw(O)
    d.rectangle([x - 40, y - 22, x + tw_ + 40, y + size + 30], fill=(244, 239, 228, 245), outline=(30, 26, 24, 255), width=5)
    d.rectangle([x - 30, y - 12, x + tw_ + 30, y + size + 20], outline=(178, 80, 46, 255), width=2)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]; wl = f.getlength(w)
        if on: d.rectangle([x - 8, y - 6, x + wl + 8, y + size + 12], fill=(178, 80, 46, 255))
        d.text((x, y + size * 0.02), w, font=f, fill=(250, 245, 232) if on else (28, 24, 22)); x += f.getlength(w + " ")

groups = caption_groups(words, 3)
def frame(t, fi):
    rgb = frame_rgb(t)
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert("RGBA")
    O = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    caption(O, t)
    d = ImageDraw.Draw(O)
    d.rectangle([70, H - 92, W - 70, H - 78], fill=(36, 31, 29, 120))
    pw = int((W - 140) * t / total)
    if pw > 1:
        d.rectangle([70, H - 92, 70 + pw, H - 78], fill=(212, 156, 58, 255))
        d.rectangle([70 + pw - 12, H - 96, 70 + pw + 2, H - 74], fill=(178, 80, 46, 255))
    im.alpha_composite(O)
    return im.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), int(float(tt_) * FPS))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=24); print(f"done {total:.1f}s")
