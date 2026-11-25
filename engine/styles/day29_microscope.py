"""Day 29 — MICROSCOPE-DIC style (tardigrades survived the vacuum of space).
Looking down a lab microscope eyepiece:
- a round eyepiece field on a matte graphite instrument surround (machined, knurled rim that turns on every cut);
- the specimen is a *height field* rendered as Nomarski DIC (differential interference contrast): shear-derivative
  relief shading mapped through slate-violet → grey → warm cream, so everything looks embossed and glassy; living
  tissue tinted by an absorption layer (amber gut, dark eyespots, green moss chloroplasts);
- space scenes switch the condenser to DARKFIELD: black field where only edges scatter light (cool white), with
  emission tints (Earth glow, cosmic-ray tracks, amber 'alive' glow);
- procedural tardigrade: segmented dome body, 4 pairs of stubby paddling legs with claws, storage-cell granules,
  eyespots, pharynx bulb; morphs smoothly into a dried barrel 'tun' (legs retract, wrinkle rings) and back;
- focus pulls (variable blur) and objective-turret cuts (field slides sideways with motion blur + click);
- micrometer reticle, scale bar, mono readouts (objective, focus µm, specimen) in Martian Mono; titles in Sora
  ExtraBold, white + amber;
- ending: an embossed FAKE out of focus; a glass bead slides along a groove, focus snaps and TRUE appears in amber.
Music: original D-major pizzicato/celesta lab tune at 112 bpm + sub, turret clicks on cuts, low pad in orbit.
Usage: python3 engine/styles/day29_microscope.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]

_F = {}
def F(kind, s, wght=800):
    k = (kind, int(s), wght)
    if k not in _F:
        if kind == "m":
            f = ImageFont.truetype(f"{FONTS}/MartianMono-VF.ttf", int(s))
            try: f.set_variation_by_axes([100, wght])
            except Exception: pass
        else:
            f = ImageFont.truetype(f"{FONTS}/Sora-VF.ttf", int(s))
            try: f.set_variation_by_axes([wght])
            except Exception: pass
        _F[k] = f
    return _F[k]

AMBER = (255, 184, 76); WHITE = (244, 241, 232); SLATE = (138, 146, 162); DARK = (14, 16, 20)
CX, CY, R = 540, 940, 440
X0, Y0, D = CX - R, CY - R, 2 * R
FS = 440                      # field resolution (half of D)
rng0 = np.random.default_rng(29)

# ---------- DIC colour map ----------
C_MID = np.array([150, 150, 162], np.float32)
C_HI = np.array([238, 228, 204], np.float32)
C_LO = np.array([46, 46, 74], np.float32)

def dome(mask, r):
    dt = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    u = np.clip(dt / max(r, 1e-3), 0, 1)
    return (1 - (1 - u) ** 2).astype(np.float32)

def gblur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s) if s > 0.05 else a

def dic(h, absorb, k=2.6):
    hb = gblur(h, 0.8)
    rel = (np.roll(hb, (-1, -1), (0, 1)) - np.roll(hb, (1, 1), (0, 1))) * k
    rel = np.tanh(rel)[..., None]
    col = np.where(rel > 0, C_MID + rel * (C_HI - C_MID), C_MID - rel * (C_LO - C_MID))
    col = col * (1 + 0.06 * gblur(h, 6)[..., None])        # thicker areas a touch brighter (halo)
    return col * np.exp(-absorb)

def darkfield(h, emit, k=2.2):
    hb = gblur(h, 0.9)
    gx = cv2.Sobel(hb, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(hb, cv2.CV_32F, 0, 1, ksize=3)
    e = np.clip(np.sqrt(gx * gx + gy * gy) * k, 0, 1.4) ** 0.85
    col = np.array([8, 10, 18], np.float32) + e[..., None] * np.array([196, 214, 240], np.float32)
    return col + emit * 255

# ---------- static field textures ----------
YY, XX = np.mgrid[0:FS, 0:FS].astype(np.float32)
def fbm(seed, base=48, oct_=4):
    r = np.random.default_rng(seed); acc = np.zeros((FS, FS), np.float32); amp = 1.0; b = base
    for _ in range(oct_):
        n = r.normal(0, 1, (FS // b + 3, FS // b + 3)).astype(np.float32)
        acc += amp * cv2.resize(n, (FS + 3 * b, FS + 3 * b), interpolation=cv2.INTER_CUBIC)[:FS, :FS]
        amp *= 0.5; b = max(2, b // 2)
    return acc / 1.9

def voronoi(seed, n=46, size=FS):
    r = np.random.default_rng(seed)
    pts = np.stack([np.linspace(0, 1, n) * 0 + r.uniform(-20, size + 20, n), r.uniform(-20, size + 20, n)], 1)
    # elongated moss-leaf cells: stretch along a diagonal
    d1 = np.full((size, size), 1e9, np.float32); d2 = d1.copy(); idx = np.zeros((size, size), np.int32)
    for i, (px, py) in enumerate(pts):
        dx = XX - px; dy = YY - py
        u = (dx * 0.8 + dy * 0.6); v = (-dx * 0.6 + dy * 0.8) * 1.9
        d = np.sqrt(u * u + v * v)
        nearer = d < d1
        d2 = np.where(nearer, d1, np.minimum(d2, d)); idx = np.where(nearer, i, idx); d1 = np.where(nearer, d, d1)
    return d1, d2, idx, pts

_V = voronoi(7)
WALL = np.exp(-((_V[1] - _V[0]) / 3.2) ** 2).astype(np.float32)
CELLIN = np.clip((_V[1] - _V[0]) / 18, 0, 1).astype(np.float32)
CHL = np.zeros((FS, FS), np.float32)
for i in range(420):
    x, y = rng0.uniform(0, FS, 2)
    cv2.ellipse(CHL, (int(x), int(y)), (4, 3), float(rng0.uniform(0, 180)), 0, 360, 1.0, -1, cv2.LINE_AA)
CHL = gblur(CHL * CELLIN * (rng0.uniform(0, 1, (FS, FS)) > -1), 0.8)
GRAIN = fbm(3, 24, 3)
DEBRIS = []
for i in range(26):
    DEBRIS.append((rng0.uniform(0, FS), rng0.uniform(0, FS), rng0.uniform(2, 7), rng0.uniform(0, 6.28)))

def moss(dx=0.0, dy=0.0, amt=1.0):
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    w = cv2.warpAffine(WALL, M, (FS, FS), borderMode=cv2.BORDER_WRAP)
    c = cv2.warpAffine(CHL, M, (FS, FS), borderMode=cv2.BORDER_WRAP)
    h = (0.6 * w + 0.35 * c + 0.12 * GRAIN) * amt
    a = c[..., None] * np.array([0.42, 0.1, 0.45], np.float32) * amt * 0.7
    return h, a

def debris(h, t, drift=(6, -3)):
    for (x, y, r, p) in DEBRIS:
        xx = (x + drift[0] * t + 3 * math.sin(t * 0.7 + p)) % FS; yy = (y + drift[1] * t) % FS
        cv2.circle(h, (int(xx * 4), int(yy * 4)), int(r * 4), 0.0, -1, cv2.LINE_AA, 2)
    return h

def blobs(h, pts, val=1.0):
    m = np.zeros((FS, FS), np.uint8)
    for (x, y, r) in pts: cv2.circle(m, (int(x * 4), int(y * 4)), int(r * 4), 255, -1, cv2.LINE_AA, 2)
    return m

# ---------- the tardigrade ----------
GRAN = [(rng0.uniform(-0.75, 0.6), rng0.uniform(-0.7, 0.7), rng0.uniform(0.03, 0.06)) for _ in range(46)]
def rot(ang): c, s = math.cos(ang), math.sin(ang); return np.array([[c, -s], [s, c]], np.float32)

def tardigrade(h, a, cx, cy, s, ang, ph, dry=0.0, alive=1.0, ink=None):
    """Draw a water bear (head toward +x local) into height h and absorption a (field coords). dry 0→1 = tun."""
    Rm = rot(ang); dry = float(np.clip(dry, 0, 1))
    Lf = 1 - 0.42 * dry; Wf = 1 + 0.12 * dry
    us = np.linspace(-1, 1, 80)
    def P(u, v): q = Rm @ np.array([u * s * Lf, v * s], np.float32); return (cx + q[0], cy + q[1])
    wob = 0.05 * (1 - dry)
    wseg = 0.07 + 0.08 * dry
    half = []
    for u in us:
        w = 0.36 * Wf * (max(0.0, 1 - u * u)) ** (0.5 - 0.15 * dry) * (1 + wseg * math.cos(u * math.pi * 4.5 + 0.6))
        half.append((u, w + 0.015, wob * math.sin(ph * 0.5 + u * 2.2)))
    top = [P(u, w + o) for (u, w, o) in half]; bot = [P(u, -w + o) for (u, w, o) in half[::-1]]
    m = np.zeros((FS, FS), np.uint8)
    poly = (np.array(top + bot) * 4).astype(np.int32)
    cv2.fillPoly(m, [poly], 255, cv2.LINE_AA, 2)
    # legs: 3 side pairs + rear pair
    tips = []
    ll = 0.2 * (1 - dry) * s
    if ll > 1.0:
        for k, u in enumerate((0.42, 0.08, -0.26)):
            for side in (1, -1):
                sw = math.sin(ph + k * 1.4 + (0 if side > 0 else math.pi)) * 0.45
                base = np.array(P(u, side * 0.26))
                dirv = Rm @ np.array([math.sin(sw) * 0.9, side * math.cos(sw)], np.float32)
                tip = base + dirv * ll
                cv2.line(m, tuple((base * 4).astype(int)), tuple((tip * 4).astype(int)), 255, max(1, int(0.19 * s)), cv2.LINE_AA, 2)
                tips.append((tip, dirv))
        for side in (1, -1):
            sw = math.sin(ph + 4.2 + (0 if side > 0 else math.pi)) * 0.3
            base = np.array(P(-0.82, side * 0.1))
            dirv = Rm @ np.array([-math.cos(sw), side * 0.55 + math.sin(sw) * 0.3], np.float32); dirv /= np.linalg.norm(dirv)
            tip = base + dirv * ll * 0.9
            cv2.line(m, tuple((base * 4).astype(int)), tuple((tip * 4).astype(int)), 255, max(1, int(0.17 * s)), cv2.LINE_AA, 2)
            tips.append((tip, dirv))
    body = dome(m, 0.36 * s * Wf)
    # wrinkle rings on the tun
    if dry > 0.05:
        loc = np.linalg.inv(Rm) @ np.stack([(XX - cx).ravel(), (YY - cy).ravel()])
        uu = (loc[0] / (s * Lf)).reshape(FS, FS)
        body = body * (1 - 0.22 * dry * (0.5 + 0.5 * np.cos(uu * math.pi * 7)))
    g = np.zeros((FS, FS), np.float32)
    for (gu, gv, gr) in GRAN:
        x, y = P(gu * 0.95, gv * 0.3 * Wf)
        cv2.circle(g, (int(x * 4), int(y * 4)), max(1, int(gr * s * 4 * (1 - 0.3 * dry))), 1.0, -1, cv2.LINE_AA, 2)
    g = gblur(g, 0.7) * (m > 0)
    h += body * (0.04 * s) + (g * (0.012 * s) if s > 40 else 0)
    # absorption: amber gut, pharynx bulb, eyespots, claws
    gut = np.zeros((FS, FS), np.float32)
    gx, gy = P(-0.15, 0)
    cv2.ellipse(gut, (int(gx * 4), int(gy * 4)), (int(0.5 * s * Lf * 4), int(0.16 * s * Wf * 4)), -math.degrees(-ang) if False else math.degrees(ang), 0, 360, 1.0, -1, cv2.LINE_AA, 2)
    gut = gblur(gut, 2.5)
    tint = np.array([0.10, 0.42, 0.95], np.float32) * (0.55 + 0.45 * alive) + np.array([0.2, 0.25, 0.2], np.float32) * dry
    a += gut[..., None] * tint * 0.85 + (body * 0.18)[..., None] * np.array([0.05, 0.18, 0.4], np.float32)
    if dry < 0.95:
        ph_ = np.zeros((FS, FS), np.float32)
        bx, by = P(0.66, 0); cv2.circle(ph_, (int(bx * 4), int(by * 4)), int(0.09 * s * 4), 1.0, -1, cv2.LINE_AA, 2)
        for side in (1, -1):
            ex, ey = P(0.8, side * 0.13); cv2.circle(ph_, (int(ex * 4), int(ey * 4)), max(1, int(0.035 * s * 4)), 1.6, -1, cv2.LINE_AA, 2)
        sx0, sy0 = P(0.95, 0); sx1, sy1 = P(0.68, 0)
        cv2.line(ph_, (int(sx0 * 4), int(sy0 * 4)), (int(sx1 * 4), int(sy1 * 4)), 1.2, max(1, int(0.02 * s)), cv2.LINE_AA, 2)
        for (tip, dv) in tips:
            for c_ in (-0.5, 0.0, 0.5):
                q = rot(c_) @ dv
                e = tip + q * 0.06 * s
                cv2.line(ph_, tuple((tip * 4).astype(int)), tuple((e * 4).astype(int)), 1.1, max(1, int(0.016 * s)), cv2.LINE_AA, 2)
        ph_ = gblur(ph_, 0.6) * (1 - dry)
        a += ph_[..., None] * np.array([0.9, 1.0, 0.9], np.float32)
    return m

# ---------- text as relief ----------
_TM = {}
def tmask(s, size, wght=800):
    k = (s, size, wght)
    if k not in _TM:
        f = F("s", size, wght); w_ = int(f.getlength(s)) + 20
        im = Image.new("L", (w_, int(size * 1.4)), 0); ImageDraw.Draw(im).text((10, 0), s, font=f, fill=255)
        _TM[k] = np.array(im)
    return _TM[k]

def text_relief(h, s, size, cx, cy):
    tm = tmask(s, size); th, tw = tm.shape
    m = np.zeros((FS, FS), np.uint8)
    x0 = int(cx - tw / 2); y0 = int(cy - th / 2)
    xa, ya = max(0, x0), max(0, y0); xb, yb = min(FS, x0 + tw), min(FS, y0 + th)
    m[ya:yb, xa:xb] = tm[ya - y0:yb - y0, xa - x0:xb - x0]
    m = (m > 110).astype(np.uint8) * 255
    hh = dome(m, size * 0.09); h += hh * size * 0.04
    return hh

# ---------- scenes (field coords 0..FS; return dict) ----------
def base_bf(t, amt=1.0, dx=0, dy=0):
    h, a = moss(dx, dy, amt)
    h = h.copy(); a = a.copy()
    dm = np.zeros((FS, FS), np.uint8)
    for (x, y, r, p) in DEBRIS[:14]:
        xx = (x + 7 * t + 3 * math.sin(t * 0.7 + p)) % FS; yy = (y - 3 * t) % FS
        cv2.circle(dm, (int(xx * 4), int(yy * 4)), int(r * 4), 255, -1, cv2.LINE_AA, 2)
    h += dome(dm, 4) * 1.4
    return h, a

def hook(ln, lt, dur, t):
    h, a = base_bf(t, 1.0, -t * 9, t * 4)
    tardigrade(h, a, 205 + 10 * lt, 235 - 4 * lt, 150, -0.45, t * 7.0)
    return dict(h=h, a=a, mode="dic", focus=0.0, obj="40×", label="SPECIMEN · TARDIGRADA · LIVE",
                titles=[("THIS TINY ANIMAL", 92, WHITE), ("SURVIVED", 128, WHITE), ("SPACE.", 128, AMBER)])

def nosuit(ln, lt, dur, t):
    z = 1.0 + 0.25 * eout(lt / 1.2)
    h, a = base_bf(t, 0.9, -t * 9, t * 4)
    tardigrade(h, a, 170 - 40 * (z - 1), 240, 190 * z, -0.25, t * 7.0)
    def ov(d):
        hx, hy = fx(330 - 50 * (z - 1)), fy(195)
        p = eout((lt - 0.15) / 0.5); rr = 150 * (0.6 + 0.4 * p)
        if p > 0:
            for k in range(0, 360, 14):
                a0 = math.radians(k); a1 = math.radians(k + 8)
                d.line([(hx + rr * math.cos(a0), hy + rr * math.sin(a0)), (hx + rr * math.cos(a1), hy + rr * math.sin(a1))], fill=AMBER + (int(255 * p),), width=6)
        q = eout((lt - 0.75) / 0.3)
        if q > 0:
            L = 120 * q
            for sgn in (1, -1):
                d.line([(hx - L, hy - sgn * L), (hx + L, hy + sgn * L)], fill=(255, 92, 92, 255), width=16)
        if lt > 1.3 and int(t * 3) % 2 == 0:
            d.rounded_rectangle([fx(150), fy(395), fx(290), fy(425)], radius=10, fill=(255, 184, 76, 235))
            d.text((fx(220), fy(410)), "WAIT FOR IT", font=F("m", 30, 700), fill=DARK, anchor="mm")
    return dict(h=h, a=a, mode="dic", focus=0.0, obj="100×", label="SPECIMEN · HEAD · NO SUIT",
                titles=[("NO", 120, WHITE), ("SPACESUIT.", 128, AMBER)], ov=ov)

def meet(ln, lt, dur, t):
    h, a = base_bf(t, 1.0, -t * 5, t * 2)
    x = 140 + 26 * lt
    tardigrade(h, a, x, 205, 78, -0.08, t * 7.5)
    def ov(d):
        p = eout((lt - 0.9) / 0.6)
        if p <= 0: return
        y = fy(300); xa = fx(x - 80); xb = xa + (fx(x + 80) - xa) * p
        d.line([(xa, y), (xb, y)], fill=AMBER + (255,), width=6)
        for xx in (xa, xb): d.line([(xx, y - 18), (xx, y + 18)], fill=AMBER + (255,), width=6)
        if p > 0.9:
            d.rounded_rectangle([(xa + xb) / 2 - 92, y + 30, (xa + xb) / 2 + 92, y + 86], radius=12, fill=(14, 16, 20, 220))
            d.text(((xa + xb) / 2, y + 58), "≈ 1 mm", font=F("m", 34, 700), fill=AMBER, anchor="mm")
    return dict(h=h, a=a, mode="dic", focus=0.0, obj="10×", label="TARDIGRADE · 'WATER BEAR'",
                titles=[("TARDIGRADE", 118, WHITE), ("A.K.A. WATER BEAR", 66, AMBER)], ov=ov)

def tun(ln, lt, dur, t):
    h, a = base_bf(t, 0.75 * (1 - 0.6 * ease(lt / dur)), 0, 0)
    dry = ease((lt - 0.4) / (dur * 0.6))
    tardigrade(h, a, 220, 215, 140, -0.3, t * 7.0 * (1 - dry), dry=dry, alive=1 - dry)
    # water droplets leaving the body
    dm = np.zeros((FS, FS), np.uint8)
    for k in range(10):
        ang = k * 0.63 + 0.3; pr = ease((lt - 0.4 - k * 0.12) / 1.4)
        if 0 < pr < 1:
            rr = 60 + 170 * pr; r_ = 9 * (1 - pr) + 2
            cv2.circle(dm, (int((220 + rr * math.cos(ang)) * 4), int((215 + rr * math.sin(ang)) * 4)), int(r_ * 4), 255, -1, cv2.LINE_AA, 2)
    h += dome(dm, 6) * 3.0
    def ov(d):
        x0, y0 = fx(95), fy(400); w = fx(345) - x0
        d.rounded_rectangle([x0, y0 - 14, x0 + w, y0 + 14], radius=14, fill=(14, 16, 20, 200), outline=SLATE + (200,), width=3)
        lvl = 1 - 0.95 * dry
        d.rounded_rectangle([x0 + 4, y0 - 10, x0 + 4 + (w - 8) * lvl, y0 + 10], radius=10, fill=(96, 176, 255, 255))
        d.text((x0 + w / 2, y0 - 44), "WATER LEVEL", font=F("m", 30, 700), fill=WHITE, anchor="mm")
    return dict(h=h, a=a, mode="dic", focus=0.0, obj="40×", label="STATE · DRYING → 'TUN'",
                titles=[("DRIES OUT", 116, WHITE), ("INTO A 'TUN'", 116, AMBER)], ov=ov)

STARS = [(rng0.uniform(0, FS), rng0.uniform(0, FS), rng0.uniform(0.3, 1)) for _ in range(90)]
def stars_emit(e, t, amt=1.0):
    for (x, y, b) in STARS:
        tw = 0.6 + 0.4 * math.sin(t * 3 + x)
        cv2.circle(e, (int(x * 4), int(y * 4)), 4, (0.9 * b * tw * amt, 0.9 * b * tw * amt, b * tw * amt), -1, cv2.LINE_AA, 2)

def launch(ln, lt, dur, t):
    h = np.zeros((FS, FS), np.float32); e = np.zeros((FS, FS, 3), np.float32)
    stars_emit(e, t)
    m = np.zeros((FS, FS), np.uint8)
    cv2.circle(m, (220 * 4, 900 * 4), 560 * 4, 255, -1, cv2.LINE_AA, 2)
    earth = dome(m, 60); h += earth * 1.2 + (m > 0) * 0.25 * fbm(11, 32, 4) * (1 + 0.0 * t)
    dd = np.sqrt((XX - 220) ** 2 + (YY - 900) ** 2) - 560
    glow = np.exp(-np.clip(dd, 0, None) / 14) * (dd > -2)
    e += glow[..., None] * np.array([0.12, 0.35, 0.75], np.float32) + (dd <= 0)[..., None] * np.array([0.03, 0.1, 0.22], np.float32)
    # orbit + capsule
    th = -1.9 + 0.62 * ease(lt / dur)
    ox, oy = 220 + 470 * math.cos(th) * 0.0 + 210 * math.cos(th) * 1.6, 900 + 690 * math.sin(th)
    ox = 220 + 640 * math.cos(th); oy = 900 + 640 * math.sin(th)
    # capsule: emission-shaded sphere + service module (lit from the upper right)
    dv = np.array([-math.sin(th), math.cos(th)]); dv /= np.linalg.norm(dv)
    nv = np.array([-dv[1], dv[0]])
    rx, ry = XX - ox, YY - oy
    along = rx * dv[0] + ry * dv[1]; perp = rx * nv[0] + ry * nv[1]
    mod = ((along < -10) & (along > -46) & (np.abs(perp) < 15 - 0.12 * np.clip(-along - 10, 0, 40))).astype(np.float32)
    mod = gblur(mod, 0.7) * (0.35 + 0.65 * np.cos(np.clip(perp / 16, -1, 1) * math.pi / 2)) * (0.75 + 0.25 * np.cos(along * 0.9))
    dd_ = np.sqrt(rx * rx + ry * ry)
    sph = np.sqrt(np.clip(1 - (dd_ / 21) ** 2, 0, 1))
    lit = np.clip(0.35 + 0.65 * ((rx * 0.6 - ry * 0.8) / 21 * 0.8 + sph * 0.6), 0, 1.2) * (dd_ < 21)
    sph_e = gblur(lit.astype(np.float32), 0.7)
    body_e = np.maximum(sph_e, mod * (dd_ >= 19))
    e += body_e[..., None] * np.array([0.86, 0.82, 0.74], np.float32)
    rimg = np.exp(-((dd_ - 21) / 1.5) ** 2) * 0.5
    e += rimg[..., None] * np.array([0.5, 0.7, 1.0], np.float32)
    def ov(d):
        pts = [(fx(220 + 640 * math.cos(a_)), fy(900 + 640 * math.sin(a_))) for a_ in np.linspace(-2.2, th - 0.12, 50)]
        for i in range(0, len(pts) - 1, 2): d.line([pts[i], pts[i + 1]], fill=AMBER + (200,), width=5)
        p = eout((lt - 0.9) / 0.4)
        if p > 0:
            d.rounded_rectangle([fx(130), fy(330), fx(310), fy(368)], radius=10, fill=(14, 16, 20, int(220 * p)), outline=AMBER + (int(255 * p),), width=3)
            d.text((fx(220), fy(349)), "≈3,000 ON BOARD", font=F("m", 30, 700), fill=AMBER + (int(255 * p),), anchor="mm")
    return dict(h=h, a=e, mode="dark", focus=0.0, obj="DARKFIELD", label="MISSION · FOTON-M3 · SEPT 2007",
                titles=[("2007:", 120, AMBER), ("INTO ORBIT", 120, WHITE)], ov=ov)

TRAY = [(70 + 60 * i, 150 + 140 * r_) for r_ in range(2) for i in range(6)]
ALIVE = [1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0]
def space(ln, lt, dur, t):
    h = np.zeros((FS, FS), np.float32); e = np.zeros((FS, FS, 3), np.float32); a = e
    stars_emit(e, t, 0.5)
    p1 = ease((lt - dur * 0.38) / 0.6); p2 = ease((lt - dur * 0.72) / 0.6)
    for k, (x, y) in enumerate(TRAY):
        row = k // 6
        al = ALIVE[k] * (p1 if row == 0 else p2)
        th_ = np.zeros((FS, FS), np.float32)
        tardigrade(th_, np.zeros((FS, FS, 3), np.float32), x, y, 28, 0.0, 0, dry=1.0)
        pr = p1 if row == 0 else p2
        h += th_ * (1 - 0.6 * (1 - ALIVE[k]) * pr)
        g = np.zeros((FS, FS), np.float32); cv2.circle(g, (int(x * 4), int(y * 4)), 15 * 4, 1.0, -1, cv2.LINE_AA, 2)
        g = gblur(g, 5)
        e += g[..., None] * np.array([1.6, 0.85, 0.2], np.float32) * al * (0.9 + 0.1 * math.sin(t * 6 + k))
    # UV glare for the lower row
    sd = np.sqrt((XX - 420) ** 2 + (YY - 330) ** 2)
    e += (np.exp(-sd / 90) * 0.55)[..., None] * np.array([0.55, 0.35, 1.0], np.float32)
    # cosmic-ray tracks
    r = np.random.default_rng(int(t * 6))
    if r.uniform() < 0.8:
        trk = np.zeros((FS, FS), np.float32)
        x0, y0 = r.uniform(0, FS, 2); an = r.uniform(0, math.pi)
        cv2.line(trk, (int(x0 * 4), int(y0 * 4)), (int((x0 + 500 * math.cos(an)) * 4), int((y0 + 500 * math.sin(an)) * 4)), 1.0, 4, cv2.LINE_AA, 2)
        e += gblur(trk, 1.2)[..., None] * np.array([0.6, 1.0, 0.9], np.float32) * 1.6
    def ov(d):
        f = F("m", 28, 700)
        d.text((fx(220), fy(102)), "VACUUM + COSMIC RAYS", font=f, fill=WHITE + (230,), anchor="mm")
        d.text((fx(220), fy(242)), "+ RAW SUNLIGHT (UV)", font=f, fill=(200, 170, 255, 240), anchor="mm")
        for row, p in ((0, p1), (1, p2)):
            if p > 0.5:
                n_ = sum(ALIVE[row * 6:(row + 1) * 6])
                txt = "MOST SURVIVED" if row == 0 else "A FEW SURVIVED"
                y = fy(196 + 140 * row)
                d.rounded_rectangle([fx(220) - 170, y - 22, fx(220) + 170, y + 22], radius=10, fill=AMBER + (240,))
                d.text((fx(220), y), txt, font=f, fill=DARK, anchor="mm")
    return dict(h=h, a=e, mode="dark", focus=0.0, obj="DARKFIELD", label="EXPOSED · OPEN SPACE · >1 WEEK",
                titles=[("OPEN SPACE", 120, WHITE), ("FOR OVER A WEEK", 82, AMBER)], ov=ov)

EGGS = [(320, 300), (350, 255), (300, 340)]
def wake(ln, lt, dur, t):
    flood = eout(lt / 0.8)
    h, a = base_bf(t, 0.35 + 0.65 * flood, 0, 0)
    fr = flood * 560
    # meniscus ridge sweeping in from the left
    ridge = np.exp(-((XX + 60 - fr) / 10) ** 2) * (flood < 0.999)
    h += ridge.astype(np.float32) * 0.9
    dry = 1 - ease((lt - 0.7) / 1.3)
    walk = ease((lt - 1.9) / (dur - 1.9))
    x = 170 + 50 * walk
    tardigrade(h, a, x, 200, 120, -0.2, t * 7.0 * (1 - dry), dry=dry, alive=1 - dry)
    pe = ease((lt - dur * 0.55) / 0.5); hatch = ease((lt - dur * 0.75) / 0.6)
    if pe > 0:
        em = np.zeros((FS, FS), np.uint8)
        for (ex, ey) in EGGS:
            cv2.ellipse(em, (ex * 4, ey * 4), (int(17 * pe * 4), int(13 * pe * 4)), 30, 0, 360, 255, -1, cv2.LINE_AA, 2)
        eh = dome(em, 9) * (1 - 0.75 * hatch)
        h += eh * 3.0; a += (eh * 0.25)[..., None] * np.array([0.1, 0.2, 0.45], np.float32)
        if hatch > 0:
            for k, (ex, ey) in enumerate(EGGS):
                tardigrade(h, a, ex - 26 * hatch - 4 * k, ey + 8 * hatch, 22 * (0.6 + 0.4 * hatch), 2.6 + k * 0.4, t * 9 + k)
    titles = [("JUST ADD", 116, WHITE), ("WATER.", 128, AMBER)] if lt < dur * 0.45 else [("THEY WOKE UP", 108, WHITE), ("& LAID EGGS!", 108, AMBER)]
    return dict(h=h, a=a, mode="dic", focus=0.0, obj="40×", label="REHYDRATED · ALIVE", titles=titles)

def end(ln, lt, dur, t):
    ca = ln["scene"].get("click_at", 0.45)
    h, a = base_bf(t, 0.6, -t * 5, 0)
    p = ease((lt - ca) / 0.3)
    word = "FAKE" if p < 0.5 else "TRUE"
    tm = np.zeros((FS, FS), np.float32)
    th_ = text_relief(tm, word, 128, 220, 175)
    h += tm
    if word == "TRUE": a += (th_ * 0.8)[..., None] * np.array([0.0, 0.32, 1.0], np.float32)
    else: a += (th_ * 0.25)[..., None] * np.array([0.4, 0.4, 0.3], np.float32)
    # groove + bead
    g = np.zeros((FS, FS), np.uint8)
    cv2.rectangle(g, (100 * 4, 300 * 4), (340 * 4, 336 * 4), 255, -1, cv2.LINE_AA, 2)
    h -= dome(g, 10) * 3.0
    bx = 118 + 204 * p
    bm = np.zeros((FS, FS), np.uint8); cv2.circle(bm, (int(bx * 4), 318 * 4), 26 * 4, 255, -1, cv2.LINE_AA, 2)
    h += dome(bm, 26) * 8.0
    a += (dome(bm, 26) * 0.6)[..., None] * (np.array([0.0, 0.3, 0.9], np.float32) * p + np.array([0.3, 0.3, 0.3], np.float32) * (1 - p))
    fill = np.zeros((FS, FS), np.float32); cv2.rectangle(fill, (100 * 4, 304 * 4), (int(bx * 4), 332 * 4), 1.0, -1, cv2.LINE_AA, 2)
    a += gblur(fill, 1)[..., None] * np.array([0.0, 0.3, 0.9], np.float32) * p
    foc = 4.5 * (1 - p) + 2.5 * math.sin(math.pi * min(1, max(0, (lt - ca) / 0.3)))
    titles = [("SOUNDS FAKE?", 112, WHITE)] if p < 0.5 else [("IT'S TRUE.", 128, AMBER), ("FOLLOW FOR MORE", 64, WHITE)]
    return dict(h=h, a=a, mode="dic", focus=foc, obj="40×", label="VERDICT · IN FOCUS" if p > 0.5 else "VERDICT · OUT OF FOCUS", titles=titles)

SCENES = {"hook": hook, "nosuit": nosuit, "meet": meet, "tun": tun, "launch": launch, "space": space, "wake": wake, "end": end}
def fx(x): return x * D / FS
def fy(y): return y * D / FS

# ---------- narration + music ----------
voice, words, total = narrate(spec, lead=0.08)
n = len(voice); music = np.zeros(n, np.float32)

def pluck(f, dur=0.9, amp=1.0, bright=1.0):
    s = np.arange(int(dur * SR)) / SR
    sig = np.sin(2 * np.pi * f * s) + 0.4 * bright * np.sin(2 * np.pi * 2 * f * s) * np.exp(-s * 9) + 0.15 * bright * np.sin(2 * np.pi * 3 * f * s) * np.exp(-s * 16)
    return (amp * sig * np.exp(-s * 6) * np.clip(s / 0.003, 0, 1)).astype(np.float32)

def celesta(f, dur=1.4, amp=1.0):
    s = np.arange(int(dur * SR)) / SR
    sig = np.sin(2 * np.pi * f * s) + 0.3 * np.sin(2 * np.pi * f * 4.0 * s) * np.exp(-s * 8)
    return (amp * sig * np.exp(-s * 3.2) * np.clip(s / 0.002, 0, 1)).astype(np.float32)

def pad(freqs, dur):
    s = np.arange(int(dur * SR)) / SR
    sig = sum(np.sin(2 * np.pi * f * s) + 0.5 * np.sin(2 * np.pi * f * 1.004 * s) for f in freqs)
    env = np.clip(s / 0.6, 0, 1) * np.clip((dur - s) / 0.6, 0, 1)
    return (sig * env / len(freqs)).astype(np.float32)

def click(at, gain=0.2):
    s = np.arange(int(0.08 * SR)) / SR
    nz = np.random.default_rng(int(at * 100)).normal(0, 1, len(s))
    sig = nz * np.exp(-s * 90) * 0.6 + np.sin(2 * np.pi * 1800 * s) * np.exp(-s * 60) * 0.5
    place(music, at, sig.astype(np.float32), gain)

BEAT = 60 / 112
CH = [(146.83, 185.0, 220.0), (123.47, 146.83, 185.0), (98.0, 123.47, 146.83), (110.0, 138.59, 164.81)]   # D Bm G A
PAT = [0, 2, 1, 2, 0, 2, 1, 3]
for k in range(int(total / BEAT) + 1):
    c = CH[(k // 8) % 4]
    if k % 2 == 0: place(music, k * BEAT, pluck(c[0] / 2, 0.6, 1.0, 0.4), 0.11)
    tri = [c[0] * 2, c[1] * 2, c[2] * 2, c[1] * 4]
    place(music, k * BEAT + (BEAT / 2 if k % 4 == 3 else 0), pluck(tri[PAT[k % 8]], 0.7), 0.045)
    if k % 8 in (0, 5): place(music, k * BEAT, celesta(tri[(k // 8) % 3] * 2, 1.4), 0.035)
hook_hit(music, 0.3)
for i, ln in enumerate(spec["lines"]):
    s0 = ln["_s"]; st = ln["scene"]["type"]
    if i > 0: whoosh(music, s0 - 0.08, 0.06, 0.3); click(s0 - 0.1, 0.22); click(s0 + 0.12, 0.14)
    if st in ("launch", "space"): place(music, s0, pad((73.42, 110.0, 146.83), ln["_se"] - s0 + 0.4), 0.08)
    if st == "nosuit": place(music, s0 + 0.8, pluck(220.0, 0.5, 1.0, 1.5), 0.08)
    if st == "end":
        c = s0 + ln["scene"].get("click_at", 0.45)
        click(c, 0.3)
        for j, fq in enumerate((587.33, 739.99, 880.0, 1174.66)): place(music, c + 0.1 + j * 0.07, celesta(fq, 1.6), 0.08)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.45)

# ---------- static surround ----------
GY, GX = np.mgrid[0:H, 0:W].astype(np.float32)
RD = np.sqrt((GX - CX) ** 2 + (GY - CY) ** 2)
BG = np.full((H, W, 3), 13, np.float32) + np.array([0, 1, 4], np.float32)
BG += (np.exp(-np.clip(RD - R, 0, None) / 260) * 22)[..., None] * np.array([1.0, 0.92, 0.75], np.float32)
BG += np.random.default_rng(1).normal(0, 2.2, (H, W, 1)).astype(np.float32)
rim = (RD > R) & (RD < R + 46)
BG[rim] = BG[rim] * 0.3 + np.array([46, 48, 54], np.float32)
hl = np.clip(1 - np.abs(RD - (R + 3)) / 3, 0, 1); BG += (hl * 60)[..., None]
hl2 = np.clip(1 - np.abs(RD - (R + 46)) / 2, 0, 1); BG += (hl2 * 30)[..., None]
ANG = np.arctan2(GY - CY, GX - CX)
RIMMASK = ((RD > R + 10) & (RD < R + 40)).astype(np.float32)
BG = BG.astype(np.float32)
# circle masks (local D×D)
ly, lx = np.mgrid[0:D, 0:D].astype(np.float32)
lr = np.sqrt((lx - R + 0.5) ** 2 + (ly - R + 0.5) ** 2)
CMASK = np.clip(R - lr, 0, 1)[..., None]
VIG = (1 - 0.42 * (lr / R) ** 3)[..., None]
FRINGE = np.exp(-((lr - (R - 6)) / 4) ** 2)[..., None]

groups = caption_groups(words, 3)

def field_rgb(t, ln):
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    S = SCENES[ln["scene"]["type"]](ln, lt, dur, t)
    if S["mode"] == "dic":
        rgb = dic(S["h"], S["a"])
    else:
        rgb = darkfield(S["h"], S["a"])
    rgb = gblur(rgb, S.get("focus", 0.0) + 0.0)
    big = cv2.resize(rgb, (D, D), interpolation=cv2.INTER_CUBIC)
    # focus breathing + slight edge haze
    return big, S

def draw_titles(d, titles, alpha=1.0, dy=0):
    ys = []; y = 92 + dy
    for (s, size, col) in titles:
        f = F("s", size, 800)
        while f.getlength(s) > 980 and size > 40: size -= 4; f = F("s", size, 800)
        d.text((CX + 4, y + 6), s, font=f, fill=(0, 0, 0, int(160 * alpha)), anchor="mt")
        d.text((CX, y), s, font=f, fill=col + (int(255 * alpha),), anchor="mt")
        y += int(size * 1.02)

def caption(d, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 74; f = F("s", size, 700)
    while f.getlength(" ".join(ws)) > W - 220 and size > 44: size -= 4; f = F("s", size, 700)
    gap = f.getlength(" ") + 14
    tw_ = sum(f.getlength(w) for w in ws) + gap * (len(ws) - 1); x = (W - tw_) / 2; y = 1598
    d.rounded_rectangle([x - 36, y - 24, x + tw_ + 36, y + size + 26], radius=20, fill=(10, 11, 14, 238), outline=AMBER + (255,), width=4)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]; wl = f.getlength(w)
        if on: d.rounded_rectangle([x - 10, y - 8, x + wl + 10, y + size + 12], radius=10, fill=AMBER + (255,))
        d.text((x, y - size * 0.08), w, font=f, fill=DARK if on else WHITE); x += wl + gap

def frame(t, fi):
    lines = spec["lines"]; ln = active_line(spec, t) or lines[0]; i = lines.index(ln)
    big, S = field_rgb(t, ln)
    prevS = None; ph = 1.0
    if i > 0:
        ph = (t - (ln["_s"] - 0.12)) / 0.36
        if ph < 1:   # objective-turret cut: old field slides out, new slides in, with motion blur
            old, prevS = field_rgb(ln["_s"] - 0.13, lines[i - 1])
            e = eout(ph); sh = int((D + 70) * e)
            comp = np.full((D, D, 3), 8, np.float32)
            a1 = D - sh
            if a1 > 0: comp[:, :a1] = old[:, sh:sh + a1] if sh + a1 <= D else comp[:, :a1]
            nx0 = D + 70 - sh
            if nx0 < D: comp[:, max(0, nx0):] = big[:, :D - max(0, nx0)]
            big = cv2.blur(comp, (int(9 + 50 * math.sin(math.pi * ph)), 1))
    if t > total - 0.45:
        a_ = ease((t - (total - 0.45)) / 0.45)
        b0, _ = field_rgb(lines[0]["_s"], lines[0])
        big = big * (1 - a_) + b0 * a_
    big = big * VIG
    big = big + FRINGE * np.array([60, 40, 10], np.float32)
    out = BG.copy()
    # knurled rim ticks turn with the scene index
    rot_ = i * 0.21 + (1 - eout(min(1, ph))) * -0.21 if i > 0 else 0.0
    kn = (np.cos((ANG + rot_) * 90) > 0.6).astype(np.float32) * RIMMASK
    out += (kn * 26)[..., None]
    reg = out[Y0:Y0 + D, X0:X0 + D]
    out[Y0:Y0 + D, X0:X0 + D] = reg * (1 - CMASK) + big * CMASK
    im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).convert("RGBA")
    O = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(O)
    # reticle
    rc = (255, 250, 235, 70)
    d.line([(CX - R + 30, CY), (CX + R - 30, CY)], fill=rc, width=2); d.line([(CX, CY - R + 30), (CX, CY + R - 30)], fill=rc, width=2)
    for k in range(-10, 11):
        L = 22 if k % 5 == 0 else 11
        d.line([(CX + k * 30, CY + R - 70 - L), (CX + k * 30, CY + R - 70)], fill=(255, 250, 235, 110), width=2)
    d.line([(CX - 300, CY + R - 70), (CX + 300, CY + R - 70)], fill=(255, 250, 235, 110), width=2)
    # scene overlays inside the circle (clipped)
    showS = S if (i == 0 or ph >= 0.55) else prevS
    if showS is not None and "ov" in showS and (i == 0 or ph >= 1.0):
        L_ = Image.new("RGBA", (D, D), (0, 0, 0, 0)); showS["ov"](ImageDraw.Draw(L_))
        cm = Image.new("L", (D, D), 0); ImageDraw.Draw(cm).ellipse([2, 2, D - 2, D - 2], fill=255)
        L_.putalpha(Image.fromarray(np.minimum(np.array(L_.split()[3]), np.array(cm))))
        O.alpha_composite(L_, (X0, Y0))
    # titles
    if i > 0 and ph < 1:
        if ph < 0.5 and prevS is not None: draw_titles(d, prevS["titles"], 1 - ph * 2)
        else: draw_titles(d, S["titles"], min(1, (ph - 0.5) * 2), int(24 * (1 - eout(min(1, (ph - 0.5) * 2)))))
    else:
        draw_titles(d, S["titles"])
    # readouts under the eyepiece
    fm = F("m", 28, 600)
    foc = 3.2 * math.sin(t * 0.9) + S.get("focus", 0) * 6
    d.text((X0 + 10, 1418), f"OBJ {S['obj']}", font=fm, fill=AMBER + (255,))
    d.text((X0 + D - 10, 1418), f"FOCUS {foc:+.1f} µm", font=fm, fill=SLATE + (255,), anchor="ra")
    d.text((CX, 1478), S["label"], font=F("m", 26, 500), fill=WHITE + (200,), anchor="mt")
    d.ellipse([X0 + 10, 1484, X0 + 24, 1498], fill=(255, 90, 80, 255 if int(t * 2) % 2 == 0 else 90))
    caption(d, t)
    d.rounded_rectangle([30, H - 16, W - 30, H - 8], radius=4, fill=(255, 255, 255, 40))
    pw = int((W - 60) * t / total)
    if pw > 1: d.rounded_rectangle([30, H - 16, 30 + pw, H - 8], radius=4, fill=AMBER + (255,))
    im.alpha_composite(O)
    return im.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), int(float(tt_) * FPS))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=22); print(f"done {total:.1f}s")
