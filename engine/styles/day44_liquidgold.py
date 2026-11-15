"""Day 44 — LIQUID GOLD style (there's enough gold in Earth's core to coat the planet).
Everything that matters is molten metal. Each frame, scenes paint plain greyscale masks (titles, drops, rings, the
core); the engine turns those masks into liquid gold: the mask is blurred into a height field (so unions of drops
merge like metaballs and letters get rounded bevels), slow ripple noise makes it flow, normals are reflected into a
studio environment (top softbox band, side strip, dark horizon, warm orange bounce from below) and mapped through a
gold colour ramp; a soft drop shadow sits it on a dark obsidian backdrop with a warm heat glow and rising sparks.
Non-metal things (a shaded rotating Earth, the mantle cross-section, ruler, labels) are flat painted layers beneath.
Scene changes "melt in": masks are thresholded from blobs to crisp shapes over 0.35 s (with a liquid bloop).
Type: Abril Fatface (liquid display titles), Inter Display Bold (labels, captions).
Ending: a toggle whose knob is a molten gold drop that flows from FAKE to TRUE, flooding the track with gold.
Music: sub drone + FM gold bells (Dm-Bb-F-C) + soft pulse + bloops.
Usage: python3 engine/styles/day44_liquidgold.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
INTER = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter")
_F = {}
def F(kind, s):
    k = (kind, int(s))
    if k not in _F:
        if kind == "abril": _F[k] = ImageFont.truetype(f"{FONTS}/AbrilFatface-Regular.ttf", int(s))
        else: _F[k] = ImageFont.truetype(f"{INTER}/InterDisplay-Bold.otf", int(s))
    return _F[k]

CREAM, OBS, ORANGE, GOLDC = (244, 232, 206), (12, 9, 7), (255, 122, 34), (255, 204, 96)

# ---------- background (built once) ----------
def fbm(seed, scales, amps, size=(W, H)):
    rr = np.random.default_rng(seed); acc = np.zeros((size[1], size[0]), np.float32)
    for s, a in zip(scales, amps):
        g = rr.random((max(2, size[1] // s + 2), max(2, size[0] // s + 2))).astype(np.float32)
        acc += a * cv2.resize(g, size, interpolation=cv2.INTER_CUBIC)
    acc -= acc.min(); return acc / max(1e-6, acc.max())
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.52) / H) ** 2)
_n = fbm(3, [400, 120, 30], [1, 0.4, 0.15])
BG = np.stack([14 + 22 * np.exp(-_r * 4.5), 10 + 12 * np.exp(-_r * 4.5), 8 + 5 * np.exp(-_r * 4.5)], -1)
BG = (BG * (0.85 + 0.3 * _n[..., None]) * np.clip(1.25 - _r * 0.9, 0.6, 1.1)[..., None]).astype(np.float32)
RIP1 = (fbm(11, [160, 80, 40], [1, 0.6, 0.3], (W, H + 800)) - 0.5).astype(np.float32)
RIP2 = (fbm(12, [220, 90, 45], [1, 0.5, 0.3], (W + 800, H)) - 0.5).astype(np.float32)
STOPS = [(0.0, (26, 14, 4)), (0.22, (92, 54, 12)), (0.42, (170, 110, 30)), (0.6, (224, 164, 58)),
         (0.76, (250, 206, 104)), (0.9, (255, 238, 184)), (1.0, (255, 252, 236))]
LUT = np.zeros((256, 3), np.float32)
for i in range(256):
    v = i / 255
    for (a, ca), (b, cb) in zip(STOPS, STOPS[1:]):
        if a <= v <= b:
            f = (v - a) / (b - a); LUT[i] = [ca[j] + (cb[j] - ca[j]) * f for j in range(3)]; break

def blur(a, s): return cv2.GaussianBlur(a, (0, 0), s)

# ---------- canvas: masks for metal + a flat painted layer ----------
class Canvas:
    def __init__(self):
        self.MB = np.zeros((H, W), np.float32); self.MF = np.zeros((H, W), np.float32)
        self.HX = np.zeros((H, W), np.float32); self.HOT = None
        self.flat = Image.new("RGBA", (W, H), (0, 0, 0, 0)); self.top = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.heat = 0.35
    def fd(self): return ImageDraw.Draw(self.flat, "RGBA")
    def td(self): return ImageDraw.Draw(self.top, "RGBA")
    def put(self, m, x, y, big=True):
        """max-composite an L mask (numpy float 0..1) at top-left (x, y)."""
        M = self.MB if big else self.MF; x, y = int(x), int(y); h_, w_ = m.shape
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w_), min(H, y + h_)
        if x1 <= x0 or y1 <= y0: return
        np.maximum(M[y0:y1, x0:x1], m[y0 - y:y1 - y, x0 - x:x1 - x], out=M[y0:y1, x0:x1])
    def shape(self, fn, big=True):
        """draw with PIL onto a fresh L image via fn(draw) and add it (for polygons / ellipses)."""
        im = Image.new("L", (W, H), 0); fn(ImageDraw.Draw(im))
        M = self.MB if big else self.MF; np.maximum(M, np.asarray(im, np.float32) / 255, out=M)

_TM = {}
def tmask(s, size, kind="abril"):
    k = (s, int(size), kind)
    if k not in _TM:
        f = F(kind, size); bb = f.getbbox(s); pad = 30
        im = Image.new("L", (bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad), 0)
        ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), s, font=f, fill=255)
        _TM[k] = np.asarray(im, np.float32) / 255
    return _TM[k]
def fit(s, size, maxw=W - 130, kind="abril"):
    while F(kind, size).getlength(s) > maxw and size > 40: size -= 4
    return size
def gold_text(cv, s, size, cx, cy, scale=1.0, big=None):
    """liquid-metal title centred at (cx, cy)."""
    if scale <= 0.02: return
    m = tmask(s, size)
    if abs(scale - 1) > 0.01: m = cv2.resize(m, (max(1, int(m.shape[1] * scale)), max(1, int(m.shape[0] * scale))), interpolation=cv2.INTER_LINEAR)
    cv.put(m, cx - m.shape[1] / 2, cy - m.shape[0] / 2, size * scale >= 130 if big is None else big)

def label(cv, s, size, cx, cy, col=CREAM, a=1.0, anchor="mm"):
    if a <= 0: return
    cv.td().text((cx, cy), s, font=F("inter", size), fill=col + (int(255 * a),), anchor=anchor)

def slam(lt, at, d=0.3):
    u = (lt - at) / d
    if u <= 0: return 0.0
    return 1.0 if u >= 1 else 1 + 0.3 * (1 - back(u)) if u > 0.35 else back(u)

def wt(ln, i): return words[min(ln["_w0"] + i, ln["_w1"] - 1)][1] - ln["_s"]

# ---------- Earth (flat-painted, shaded, rotating) ----------
def tfbm(seed, scales, amps, size=(1024, 512)):
    """horizontally tileable fbm (for the Earth texture, so the globe has no seam)."""
    rr = np.random.default_rng(seed); acc = np.zeros((size[1], size[0]), np.float32)
    for s, a in zip(scales, amps):
        cols = max(2, size[0] // s); g = rr.random((size[1] // s + 2, cols)).astype(np.float32)
        g = np.hstack([g[:, -2:], g, g[:, :3]])
        big = cv2.resize(g, ((cols + 5) * s, size[1]), interpolation=cv2.INTER_CUBIC)
        sx = size[0] / cols; big = cv2.resize(g, (int(round((cols + 5) * sx)), size[1]), interpolation=cv2.INTER_CUBIC)
        acc += a * big[:, int(round(2 * sx)):int(round(2 * sx)) + size[0]]
    acc -= acc.min(); return acc / max(1e-6, acc.max())
_tex_land = tfbm(21, [170, 85, 40, 16], [1, 0.7, 0.35, 0.15])
_tex_tone = tfbm(22, [128, 64, 16], [1, 0.4, 0.2])
_lat = np.linspace(1, -1, 512)[:, None]
TEX = np.zeros((512, 1024, 3), np.float32)
land = (_tex_land > 0.56) & (np.abs(_lat) < 0.9)
ice = np.broadcast_to(np.abs(_lat) > 0.88, (512, 1024))
TEX[:] = np.stack([20 + 20 * _tex_tone, 70 + 40 * _tex_tone, 150 + 50 * _tex_tone], -1)
TEX[land] = (np.stack([60 + 90 * _tex_tone, 130 + 40 * _tex_tone, 60 + 30 * _tex_tone], -1))[land]
TEX[ice] = [228, 236, 244]
_ES = {}
def earth(r, lon):
    r = int(r); key = r
    if key not in _ES:
        y_, x_ = np.mgrid[-r:r, -r:r].astype(np.float32) / r
        rr = x_ ** 2 + y_ ** 2; inside = rr < 1; z = np.sqrt(np.clip(1 - rr, 0, 1))
        lat = np.arcsin(np.clip(-y_, -1, 1)); lo = np.arctan2(x_, z)
        L = np.clip(-0.55 * x_ - 0.6 * y_ + 0.6 * z, 0, 1)
        _ES[key] = (inside, lat, lo, L, rr)
    inside, lat, lo, L, rr = _ES[key]
    u = (((lo + lon) / (2 * math.pi)) % 1.0 * 1023).astype(np.int32); v = ((0.5 - lat / math.pi) * 511).astype(np.int32)
    col = TEX[v, u] * (0.25 + 0.95 * L[..., None])
    rim = np.clip((rr - 0.8) / 0.2, 0, 1)[..., None] ** 2
    col = col * (1 - 0.5 * rim) + np.array([110, 170, 255], np.float32) * 0.5 * rim
    a = np.clip((1 - np.sqrt(rr)) * r * 0.8, 0, 1) * inside
    return Image.fromarray(np.dstack([col.clip(0, 255), a[..., None] * 255]).astype(np.uint8), "RGBA")

def dome(cv, cx, cy, r, k=1.0):
    """spherical height bump (multiplies the blurred metal height so coated globes shade as spheres)."""
    x0, y0, x1, y1 = int(max(0, cx - r)), int(max(0, cy - r)), int(min(W, cx + r)), int(min(H, cy + r))
    sy, sx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d2 = ((sx - cx) ** 2 + (sy - cy) ** 2) / (r * r)
    np.maximum(cv.HX[y0:y1, x0:x1], k * np.sqrt(np.clip(1 - d2, 0, 1)) * 2.2, out=cv.HX[y0:y1, x0:x1])

def coat(cv, cx, cy, r, front, t, seed=0, drips=7):
    """gold coating the top of a globe down to y=front, with hanging drips."""
    rnd = random.Random(seed); im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    pts = [(cx - r - 4, cy - r - 10)]
    for i in range(41):
        x = cx - r + 2 * r * i / 40
        y = front + 10 * math.sin(x / 37 + t * 2.2) + 6 * math.sin(x / 13 - t * 3)
        pts.append((x, y))
    pts.append((cx + r + 4, cy - r - 10)); d.polygon(pts, fill=255)
    for k in range(drips):
        x = cx - r * 0.85 + 1.7 * r * (k + rnd.uniform(0.1, 0.9)) / drips
        L = (40 + 90 * rnd.random()) * (0.6 + 0.4 * math.sin(t * 0.9 + k))
        w_ = 16 + 10 * rnd.random(); y0 = front - 5
        d.rounded_rectangle([x - w_ / 2, y0, x + w_ / 2, y0 + L], radius=w_ / 2, fill=255)
        d.ellipse([x - w_ * 0.75, y0 + L - w_ * 0.9, x + w_ * 0.75, y0 + L + w_ * 0.5], fill=255)
    disc = Image.new("L", (W, H), 0); ImageDraw.Draw(disc).ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], fill=255)
    m = np.minimum(np.asarray(im, np.float32), np.asarray(disc, np.float32)) / 255
    np.maximum(cv.MB, m, out=cv.MB); dome(cv, cx, cy, r + 3)

def stream(cv, x, y0, y1, t, w=34):
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im); L_, R_ = [], []
    for i in range(30):
        y = y0 + (y1 - y0) * i / 29; ww = w * (1 - 0.35 * i / 29) * (1 + 0.12 * math.sin(y / 23 - t * 14))
        c = x + 5 * math.sin(y / 60 + t * 3); L_.append((c - ww / 2, y)); R_.append((c + ww / 2, y))
    d.polygon(L_ + R_[::-1], fill=255)
    np.maximum(cv.MB, np.asarray(im, np.float32) / 255, out=cv.MB)

# ---------- scenes ----------
EX, EY, ER = W / 2, 1090, 330
def S_hook(cv, sc, ln, lt, dur, t):
    loop = sc.get("loop")
    cv.flat.alpha_composite(earth(ER, t * 0.25), (int(EX - ER), int(EY - ER)))
    front = EY - ER * (0.35 if not loop else 0.35 - 0.5 * ease(lt / max(0.5, dur)))
    coat(cv, EX, EY, ER, front, t, 1)
    if not loop:
        gold_text(cv, "ENOUGH GOLD", fit("ENOUGH GOLD", 190), W / 2, 270)
        gold_text(cv, "TO COAT EARTH", fit("TO COAT EARTH", 140), W / 2, 450)
        stream(cv, W / 2 + 6, 520, EY - ER + 20, t)
        label(cv, "…and it's hiding in the core", 50, W / 2, 1490, CREAM, ease((lt - 0.6) / 0.4))
    else:
        s1 = slam(lt, 0.0); s2 = slam(lt, wt(ln, 3) - 0.05)
        gold_text(cv, "NOT EVEN THE", fit("NOT EVEN THE", 130), W / 2, 260, s1)
        gold_text(cv, "STRANGEST PART", fit("STRANGEST PART", 150), W / 2, 430, s2)
        stream(cv, W / 2 + 6, 520, EY - ER + 20, t, 26)

XC, XCY, XR = W / 2, 1010, 420
_xs = None
def xsection(cv, lt, core_r, glow=1.0):
    global _xs
    if _xs is None:
        s = 2 * XR; y_, x_ = np.mgrid[0:s, 0:s].astype(np.float32) - XR; rr = np.sqrt(x_ ** 2 + y_ ** 2) / XR
        n = fbm(31, [80, 30, 10], [1, 0.5, 0.25], (s, s))
        hot = np.clip(1 - rr, 0, 1)
        col = np.stack([90 + 165 * hot, 30 + 90 * hot ** 1.5, 18 + 30 * hot ** 2], -1) * (0.8 + 0.35 * n[..., None])
        crust = (rr > 0.94)
        col[crust] = (np.stack([96 + 30 * n, 72 + 20 * n, 52 + 14 * n], -1))[crust]
        a = np.clip((1 - rr) * XR, 0, 1) * 255
        _xs = Image.fromarray(np.dstack([col.clip(0, 255), a]).astype(np.uint8), "RGBA")
    cv.flat.alpha_composite(_xs, (int(XC - XR), int(XCY - XR)))
    if core_r > 2:
        cv.shape(lambda d: d.ellipse([XC - core_r, XCY - core_r, XC + core_r, XCY + core_r], fill=255))
        dome(cv, XC, XCY, core_r)
        cv.HOT = (XC, XCY, core_r * 1.9, glow)

DROPS = [(random.Random(i).uniform(0, 6.283), random.Random(i + 50).uniform(0.45, 0.88), random.Random(i + 90).uniform(18, 32),
          random.Random(i + 130).uniform(0, 0.9)) for i in range(18)]
def S_sink(cv, sc, ln, lt, dur, t):
    cv.heat = 0.7
    g = ease((lt - 0.2) / max(1, dur - 0.6))
    core_r = 60 + 120 * g
    xsection(cv, lt, core_r)
    for a, r0, rad, delay in DROPS:
        u = ease((lt - delay) / max(1.0, dur * 0.75))
        rr = r0 * XR * (1 - u) + core_r * 0.6 * u
        x, y = XC + rr * math.cos(a + 0.3 * u), XCY + rr * math.sin(a + 0.3 * u)
        rd = rad * (1 - 0.3 * u)
        cv.shape(lambda d, x=x, y=y, rd=rd: d.ellipse([x - rd, y - rd * 1.15, x + rd, y + rd * 0.95], fill=255))
    k8 = wt(ln, 8) - 0.1
    if lt < k8: gold_text(cv, "MOLTEN EARTH", fit("MOLTEN EARTH", 150), W / 2, 270, slam(lt, 0.0))
    else: gold_text(cv, "IT SANK", fit("IT SANK", 190), W / 2, 260, slam(lt, k8))
    gold_text(cv, "TO THE CENTER", fit("TO THE CENTER", 120), W / 2, 430, slam(lt, wt(ln, 9) - 0.05))
    label(cv, "MANTLE", 40, XC + XR * 0.62, XCY - XR * 0.62, CREAM, ease((lt - 0.4) / 0.4))
    a = ease((lt - 1.0) / 0.4)
    if a > 0:
        cv.td().line([(XC, XCY + core_r + 8), (XC, XCY + XR + 26)], fill=CREAM + (int(200 * a),), width=4)
        label(cv, "CORE", 46, XC, XCY + XR + 62, CREAM, a)
    label(cv, "iron + gold", 46, XC + 240, XCY + XR + 62, GOLDC, ease((lt - wt(ln, 12)) / 0.4))

def S_coat(cv, sc, ln, lt, dur, t):
    cv.flat.alpha_composite(earth(ER, 1.2 + t * 0.25), (int(EX - ER), int(EY - ER)))
    u = ease((lt - 0.2) / max(0.8, dur - 0.3))
    coat(cv, EX, EY, ER, EY - ER * 1.1 + 2.25 * ER * u, t, 3, drips=9)
    gold_text(cv, "ENOUGH TO COVER", fit("ENOUGH TO COVER", 150), W / 2, 260, slam(lt, wt(ln, 3) - 0.15))
    gold_text(cv, "THE WHOLE SURFACE", fit("THE WHOLE SURFACE", 130), W / 2, 430, slam(lt, wt(ln, 10) - 0.1))
    label(cv, "SCIENTISTS' ESTIMATE", 44, W / 2, 1490, CREAM, ease(lt / 0.3))

GROUND, PXM = 1480, 470          # ground y, px per metre
def figure(d, x, a=255):
    """generic standing figure (soft capsule shapes), 1.75 m tall."""
    s = PXM / 100; b = GROUND; f = (58, 46, 36, a); o = CREAM + (int(a * 0.85),)
    parts = [("e", [x - 12 * s, b - 176 * s, x + 12 * s, b - 150 * s]),
             ("r", [x - 19 * s, b - 146 * s, x + 19 * s, b - 88 * s], 12 * s),
             ("r", [x - 28 * s, b - 144 * s, x - 18 * s, b - 96 * s], 5 * s), ("r", [x + 18 * s, b - 144 * s, x + 28 * s, b - 96 * s], 5 * s),
             ("r", [x - 17 * s, b - 94 * s, x - 2 * s, b], 6 * s), ("r", [x + 2 * s, b - 94 * s, x + 17 * s, b], 6 * s)]
    for p in parts:
        if p[0] == "e": d.ellipse(p[1], fill=f, outline=o, width=5)
        else: d.rounded_rectangle(p[1], radius=p[2], fill=f, outline=o, width=5)
def S_depth(cv, sc, ln, lt, dur, t):
    d = cv.fd()
    rx = 150
    d.line([(rx, GROUND - PXM * 2), (rx, GROUND)], fill=CREAM + (220,), width=5)
    for i in range(21):
        y = GROUND - PXM * i / 10; L = 46 if i % 5 == 0 else 24
        d.line([(rx, y), (rx + L, y)], fill=CREAM + (220,), width=4)
        if i % 5 == 0: d.text((rx - 16, y), f"{i / 10:g} m", font=F("inter", 34), fill=CREAM + (230,), anchor="rm")
    figure(d, 600)
    d.line([(60, GROUND), (W - 60, GROUND)], fill=CREAM + (120,), width=3)
    lvl = 0.5 * ease((lt - 0.1) / 1.2)
    top = GROUND - PXM * lvl
    pts = [(rx + 6, GROUND + 22)] + [(x, top + 9 * math.sin(x / 45 + t * 3.1) + 5 * math.sin(x / 17 - t * 4.2)) for x in range(int(rx + 6), W + 30, 20)] + [(W + 30, GROUND + 22)]
    cv.shape(lambda dd: dd.polygon(pts, fill=255))
    gold_text(cv, "HALF A METER", fit("HALF A METER", 160), W / 2, 270, slam(lt, 0.0))
    s2 = slam(lt, wt(ln, 4) - 0.1)
    gold_text(cv, "KNEE-DEEP", fit("KNEE-DEEP", 150), W / 2 + 40, 450, s2)
    a = ease((lt - wt(ln, 4)) / 0.3)
    if a > 0:
        ky = GROUND - PXM * 0.5
        cv.td().line([(830, ky - 130), (700, ky - 22)], fill=GOLDC + (int(255 * a),), width=7)
        cv.td().polygon([(688, ky - 10), (692, ky - 52), (722, ky - 30)], fill=GOLDC + (int(255 * a),))
        label(cv, "everywhere", 50, 870, ky - 165, CREAM, a)

def S_percent(cv, sc, ln, lt, dur, t):
    k = wt(ln, 4) - 0.2
    u = ease((lt - k) / 1.1)
    n = int(round(99 * u))
    gold_text(cv, f"{n}%", 330, W / 2, 420, 1.0 if lt >= k else 0.0)
    if lt < k: gold_text(cv, "THE STRANGE", fit("THE STRANGE", 150), W / 2, 330, slam(lt, 0.0)); gold_text(cv, "PART?", 160, W / 2, 500, slam(lt, 0.35))
    label(cv, "OF EARTH'S GOLD", 56, W / 2, 640, CREAM, ease((lt - k - 0.3) / 0.4))
    # mini cross-section with a big gold core and a tiny surface speck
    cx, cy, R = W / 2, 1110, 300
    d = cv.fd(); d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(120, 44, 22, 255)); d.ellipse([cx - R + 14, cy - R + 14, cx + R - 14, cy + R - 14], fill=(176, 70, 28, 255))
    for i in range(6):
        rr = R - 40 - i * 30; d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(176 + i * 12, 70 + i * 10, 28, 255))
    cr = 110 + 25 * ease((lt - k) / 1.0)
    cv.shape(lambda dd: dd.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=255)); dome(cv, cx, cy, cr); cv.HOT = (cx, cy, cr * 1.8, 0.8)
    a = ease((lt - k - 0.6) / 0.4)
    if a > 0:
        sx, sy = cx + R * 0.71, cy - R * 0.71
        cv.td().ellipse([sx - 9, sy - 9, sx + 9, sy + 9], fill=GOLDC + (int(255 * a),))
        cv.td().line([(sx + 10, sy - 10), (sx + 70, sy - 70)], fill=CREAM + (int(255 * a),), width=4)
        label(cv, "under 1% up here", 40, sx + 80, sy - 90, CREAM, a, "lm" if sx + 80 < W - 330 else "rm")
        label(cv, "99% in the core", 46, cx, cy + R + 50, GOLDC, a)

def S_ring(cv, sc, ln, lt, dur, t):
    gold_text(cv, "EVERY GOLD", fit("EVERY GOLD", 170), W / 2, 260, slam(lt, 0.0))
    gold_text(cv, "RING EVER MADE", fit("RING EVER MADE", 130), W / 2, 430, slam(lt, wt(ln, 2) - 0.1))
    cx, cy = W / 2, 930; tilt = 0.42 + 0.12 * math.sin(t * 1.4); R, w = 330, 74
    sp = 1 + 0.03 * math.sin(t * 2)
    def ring(d):
        d.ellipse([cx - R * sp, cy - R * tilt, cx + R * sp, cy + R * tilt], fill=255)
        d.ellipse([cx - (R - w) * sp, cy - (R - w) * tilt - w * 0.18, cx + (R - w) * sp, cy + (R - w) * tilt - w * 0.18], fill=0)
    cv.shape(ring)
    a = ease((lt - wt(ln, 5)) / 0.4)
    label(cv, "comes from the tiny bit", 50, W / 2, 1260, CREAM, a)
    label(cv, "LEFT UP HERE", 64, W / 2, 1340, GOLDC, ease((lt - wt(ln, 10)) / 0.4))

def S_end(cv, sc, ln, lt, dur, t):
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.45)
    gold_text(cv, "SOUNDS FAKE?", fit("SOUNDS FAKE?", 160), W / 2, 230)
    y = 480; x0, x1, hh = 180, 900, 124
    d = cv.fd()
    d.rounded_rectangle([x0 - 8, y - hh / 2 - 8, x1 + 8, y + hh / 2 + 8], radius=hh / 2 + 8, fill=(40, 30, 22, 255), outline=(120, 90, 50, 255), width=4)
    d.rounded_rectangle([x0, y - hh / 2, x1, y + hh / 2], radius=hh / 2, fill=(8, 6, 5, 255))
    kx = x0 + hh / 2 + (x1 - x0 - hh) * on
    if on < 0.98: label(cv, "FAKE", 66, (x0 + x1) / 2 + 60, y, (150, 130, 110), 1 - on)
    if on > 0:
        cv.shape(lambda dd: dd.rounded_rectangle([x0 + 8, y - hh / 2 + 10, max(x0 + 8 + hh - 20, kx), y + hh / 2 - 10], radius=(hh - 20) / 2, fill=255))
        label(cv, "TRUE", 66, (x0 + kx) / 2 - 10, y, OBS, ease((on - 0.5) / 0.4))
    sq = 1 + 0.25 * math.sin(math.pi * on)
    rk = hh / 2 + 6
    cv.shape(lambda dd: dd.ellipse([kx - rk * sq, y - rk / sq, kx + rk * sq, y + rk / sq], fill=255))
    w_ = ease((lt - click - 0.3) / 0.35)
    if w_ > 0:
        gold_text(cv, "IT'S TRUE.", fit("IT'S TRUE.", 190), W / 2, 720, slam(lt, click + 0.3))
        label(cv, "Follow for more.", 66, W / 2, 890, CREAM, ease((lt - click - 0.55) / 0.3))
    r2 = 250; ey = 1270
    cv.flat.alpha_composite(earth(r2, t * 0.25), (int(W / 2 - r2), int(ey - r2)))
    coat(cv, W / 2, ey, r2, ey - r2 * 0.5, t, 1)

SCENES = dict(hook=S_hook, sink=S_sink, coat=S_coat, depth=S_depth, percent=S_percent, ring=S_ring, end=S_end)

# ---------- audio: sub drone + FM gold bells + pulse + bloops ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.22, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32); tt = np.arange(n) / SR
music += (0.12 * np.sin(2 * np.pi * 36.7 * tt) + 0.05 * np.sin(2 * np.pi * 73.4 * tt + 0.3 * np.sin(2 * np.pi * 0.2 * tt))).astype(np.float32)
def bell(f, dur, idx=2.2):
    s = np.arange(int(dur * SR)) / SR; env = np.exp(-s * 3.2)
    return (np.sin(2 * np.pi * f * s + idx * env * np.sin(2 * np.pi * f * 3.5 * s)) * env * np.minimum(1, s / 0.004)).astype(np.float32)
CH = [[293.66, 349.23, 440.0, 587.33], [233.08, 293.66, 349.23, 466.16], [349.23, 440.0, 523.25, 698.46], [261.63, 329.63, 392.0, 523.25]]
STEP = 0.3
for k in range(int(total / STEP)):
    ch = CH[(k // 8) % 4]; f = ch[[0, 2, 1, 3, 2, 1, 3, 2][k % 8]]
    place(music, k * STEP, bell(f, 1.4), 0.07 if k % 2 == 0 else 0.045)
    if k % 2 == 0:
        s = np.arange(int(0.35 * SR)) / SR
        place(music, k * STEP, (np.sin(2 * np.pi * (45 + 50 * np.exp(-s * 25)) * s) * np.exp(-s * 9)).astype(np.float32), 0.16 if k % 4 == 0 else 0.08)
    if k % 8 == 0:
        s = np.arange(int(STEP * 8 * SR)) / SR
        place(music, k * STEP, (np.sin(2 * np.pi * ch[0] / 2 * s) * np.minimum(1, s / 0.5) * np.exp(-s * 0.6)).astype(np.float32), 0.05)
def bloop(at, gain=0.16):
    s = np.arange(int(0.25 * SR)) / SR
    place(music, at, (np.sin(2 * np.pi * np.cumsum(900 * np.exp(-s * 14) + 180) / SR) * np.exp(-s * 12)).astype(np.float32), gain)
hook_hit(music, 0.38)
for s_ in scene_starts(spec): whoosh(music, s_, 0.1); bloop(s_)
for ln in spec["lines"]:
    if ln["scene"]["type"] == "end":
        c = ln["_s"] + ln["scene"].get("click_at", 0.45)
        bloop(c, 0.2); place(music, c + 0.3, bell(587.33 * 2, 2.0, 1.4), 0.14); place(music, c + 0.3, bell(880.0, 2.0, 1.4), 0.1)
    if ln["scene"]["type"] == "percent":
        k = words[ln["_w0"] + 4][1]
        for i in range(10): place(music, k + i * 0.1, bell(700 + 60 * i, 0.3, 1.0), 0.03)
write_audio(voice, music, work + "_audio.wav", music_gain=0.5, duck=0.45)

# ---------- metal shading ----------
def metal(cv, t):
    MB, MF = cv.MB, cv.MF
    alpha = np.maximum(MB, MF)
    h = blur(MB, 11) * (1 + cv.HX) + blur(MF, 4.5) * 0.9
    oy, ox = int(400 + 390 * math.sin(t * 0.1)), int(400 + 390 * math.sin(t * 0.07 + 1))      # smooth drift, no wrap seams
    h += (RIP1[oy:oy + H] * 0.6 + RIP2[:, ox:ox + W] * 0.6) * 0.13 * alpha
    gy, gx = np.gradient(h)
    S = 26.0; nx, ny = -gx * S, -gy * S; inv = 1 / np.sqrt(nx * nx + ny * ny + 1)
    nx *= inv; ny *= inv; nz = inv
    rx, ry = 2 * nz * nx, 2 * nz * ny
    I = (0.47 - 0.22 * ry + 0.95 * np.exp(-((ry + 0.5) / 0.13) ** 2) + 0.4 * np.exp(-((rx + 0.6) / 0.14) ** 2) * (ry < 0.3)
         + 0.25 * np.exp(-((rx - 0.7) / 0.1) ** 2) - 0.28 * np.exp(-((ry - 0.12) / 0.09) ** 2))
    col = LUT[(np.clip(I, 0, 1) * 255).astype(np.uint8)]
    warm = np.clip((ry - 0.3) / 0.45, 0, 1)[..., None] * cv.heat
    col = col * (1 - warm) + np.array([255, 120, 30], np.float32) * warm
    return col, alpha

STARTS = [ln["_s"] for ln in spec["lines"]]
def melt_u(t):
    for i, s in enumerate(STARTS[1:], 1):
        if spec["lines"][i]["scene"]["type"] == spec["lines"][i - 1]["scene"]["type"]: continue
        if s - 0.12 <= t < s + 0.35: return ease((t - s + 0.12) / 0.47)
    return 1.0

SPK = [(random.Random(i).uniform(0, W), random.Random(i + 7).uniform(0, 1), random.Random(i + 3).uniform(0.5, 1.5)) for i in range(11)]
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 72
    while F("inter", size).getlength(" ".join(ws)) > W - 220 and size > 36: size -= 4
    f = F("inter", size); tw = f.getlength(" ".join(ws)); x = (W - tw) / 2; y = 1590
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([x - 40, y - 24, x + tw + 40, y + size + 28], radius=(size + 52) / 2, fill=(10, 7, 5, 236), outline=(214, 160, 60, 255), width=4)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=(255, 206, 90, 255) if on else (255, 255, 255, 255)); x += f.getlength(w + " ")

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    cv = Canvas()
    SCENES[ln["scene"]["type"]](cv, ln["scene"], ln, lt, dur, t)
    u = melt_u(t)
    if u < 1:
        for M in (cv.MB, cv.MF):
            if M.any():
                th = np.clip((blur(M, 9) - (0.62 - 0.6 * u)) / 0.1, 0, 1); M[:] = th * (1 - u ** 3) + M * u ** 3
    out = BG.copy()
    if cv.HOT:
        hx, hy, hr, g = cv.HOT
        out += (np.exp(-(((xx - hx) ** 2 + (yy - hy) ** 2) / (hr * hr)) * 1.6) * 120 * g)[..., None] * np.array([1.0, 0.45, 0.1], np.float32)
    fa = np.asarray(cv.flat, np.float32); a = fa[..., 3:4] / 255
    out = out * (1 - a) + fa[..., :3] * a
    col, alpha = metal(cv, t)
    sh = blur(np.roll(alpha, 18, 0), 12)[..., None]
    out *= 1 - 0.6 * sh
    al = alpha[..., None]; out = out * (1 - al) + col * al
    img = Image.fromarray(out.clip(0, 255).astype(np.uint8)).convert("RGBA")
    img.alpha_composite(cv.top)
    d = ImageDraw.Draw(img, "RGBA")
    for x, ph, sp in SPK:                                                      # sparks rising from the heat
        v = (ph + t * 0.12 * sp) % 1.0; ex = x + 25 * math.sin(t * 1.6 * sp + ph * 6); ey = 1560 - v * 900
        al_ = int(110 * math.sin(math.pi * v) ** 2); r_ = 1.0 + 1.0 * sp
        d.ellipse([ex - r_ * 3, ey - r_ * 3, ex + r_ * 3, ey + r_ * 3], fill=(255, 130, 40, al_ // 6))
        d.ellipse([ex - r_, ey - r_, ex + r_, ey + r_], fill=(255, 210, 120, al_))
    caption(img, t)
    d.rectangle([0, H - 10, W, H], fill=(30, 22, 14)); d.rectangle([0, H - 10, int(W * t / total), H], fill=(240, 180, 60))
    return img.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=24); print(f"done {total:.1f}s")
