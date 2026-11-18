"""Day 22 — COMIC-PANELS style (some turtles breathe through their butts).
A family-friendly 1960s comic-book page: cream newsprint with a faint pink Ben-Day dot field, panels with thick ink
borders and hard offset shadows that slam in from the side, flat process colours (cyan, process blue, yellow, red,
olive) shaded only with real halftone dots (anti-aliased Ben-Day screen at a 20-degree angle), and fat ink outlines.
The hero is a flat cartoon river turtle (olive dome shell with hexagon scutes, cream plastron, big friendly eye)
drawn from shapes; bubbles have ink rings and a gloss tick. Lettering: Bangers for headlines and sound effects
(yellow / red fill, black stroke, hard ink drop shadow, slight tilt) on starburst balloons ("BLUB!", "IN!", "POW!"),
Comic Neue Bold for yellow narration boxes and the word-by-word caption box. A magnifier inset shows the two cloacal
sacs (bursae) lined with branching bumps, and O2 bubbles turning into red dots that run along blood vessels.
Ending: an inked FAKE -> TRUE switch with a turtle-shell knob and a POW! burst; the hook page fades back in to loop.
Music: bouncy oom-pah bed (tuba bass + pizzicato plucks + woodblock) in F major, bubble "blub" sounds, slide whistle.
Usage: python3 engine/styles/day22_comic.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
_F = {}
def F(size, kind="bang"):
    k = (kind, int(size))
    if k not in _F:
        _F[k] = ImageFont.truetype(f"{FONTS}/{'Bangers-Regular.ttf' if kind == 'bang' else 'ComicNeue-Bold.ttf'}", int(size))
    return _F[k]

INK = (22, 20, 28)
PAPER = (247, 238, 214)
DOTPINK = (241, 196, 178)
RED = (230, 50, 46)
YEL = (255, 212, 38)
CYAN = (96, 200, 236)
CYAN_L = (168, 228, 248)
BLUE = (30, 108, 190)
SHELL = (122, 140, 62)
SHELL_D = (62, 80, 34)
SKIN = (188, 182, 108)
SKIN_D = (118, 118, 58)
PLAST = (236, 214, 140)
SAND = (236, 200, 120)
SAND_D = (196, 140, 70)
PINK = (238, 128, 140)
PINK_L = (250, 196, 196)
GREEN = (60, 168, 84)
WHITE = (255, 255, 255)
NAVY = (30, 40, 90)

# ---------- drawing helpers (uint8 HxWx3, local coords) ----------
def P(pts): return (np.array(pts, np.float32).reshape(-1, 1, 2) * 8).astype(np.int32)
def fill(a, pts, col):
    if len(pts) >= 3: cv2.fillPoly(a, [P(pts)], col, cv2.LINE_AA, shift=3)
def line(a, pts, col, w=3, closed=False):
    if len(pts) >= 2: cv2.polylines(a, [P(pts)], closed, col, max(1, int(round(w))), cv2.LINE_AA, shift=3)
def ell(cx, cy, rx, ry, n=48, rot=0.0, a0=0.0, a1=2 * math.pi):
    c, s = math.cos(rot), math.sin(rot)
    out = []
    for k in range(n):
        th = a0 + (a1 - a0) * k / (n - 1 if a1 - a0 < 2 * math.pi - 1e-6 else n)
        x, y = rx * math.cos(th), ry * math.sin(th)
        out.append((cx + x * c - y * s, cy + x * s + y * c))
    return out
def shape(a, pts, col, lw):
    fill(a, pts, col); line(a, pts, INK, lw, True)
def mix(c1, c2, u): u = max(0.0, min(1.0, u)); return tuple(int(c1[i] * (1 - u) + c2[i] * u) for i in range(3))

# halftone screen (Ben-Day dots), anti-aliased
PER = 14.0
_yy, _xx = np.mgrid[0:H + 40, 0:W + 40].astype(np.float32)
_ca, _sa = math.cos(0.35), math.sin(0.35)
_u = _xx * _ca + _yy * _sa; _v = -_xx * _sa + _yy * _ca
DOT = np.sqrt(((_u % PER) - PER / 2) ** 2 + ((_v % PER) - PER / 2) ** 2).astype(np.float32)
del _u, _v
def ht(a, shade, col, mask=None, x0=0, y0=0):
    """Halftone dots of `col` over region a (already sliced), radius from `shade` (array or scalar 0..1)."""
    h, w = a.shape[:2]
    r = PER * 0.74 * np.sqrt(np.clip(shade, 0, 1))
    al = np.clip(r - DOT[y0:y0 + h, x0:x0 + w] + 0.5, 0, 1)
    if mask is not None: al = al * mask
    al = al[..., None]
    a[:] = (a * (1 - al) + np.array(col, np.float32) * al).astype(np.uint8)
def ht_poly(a, pts, shade_fn, col):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; h, w = a.shape[:2]
    x0, y0 = max(0, int(min(xs)) - 2), max(0, int(min(ys)) - 2); x1, y1 = min(w, int(max(xs)) + 3), min(h, int(max(ys)) + 3)
    if x1 <= x0 or y1 <= y0: return
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillPoly(m, [P([(x - x0, y - y0) for x, y in pts])], 255, cv2.LINE_AA, shift=3)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    ht(a[y0:y1, x0:x1], shade_fn(xx, yy), col, m.astype(np.float32) / 255, x0, y0)

def burst(a, cx, cy, r, col, n=14, rot=0.0, lw=6, jag=0.68):
    pts = []
    for k in range(2 * n):
        rr = r * (1.0 if k % 2 == 0 else jag) * (1 + 0.08 * math.sin(k * 2.7))
        th = rot + math.pi * k / n
        pts.append((cx + rr * math.cos(th), cy + rr * math.sin(th) * 0.82))
    fill(a, [(x + 9, y + 10) for x, y in pts], INK); shape(a, pts, col, lw)

def bubble(a, x, y, r):
    lw = max(2.0, r * 0.2)
    pts = ell(x, y, r, r, 28)
    fill(a, pts, (236, 250, 255)); line(a, pts, INK, lw, True)
    if r > 7: line(a, ell(x, y, r * 0.58, r * 0.58, 10, 0, 3.6, 4.6), INK, max(1.5, lw * 0.6))

def arrow(a, pts, width, col, lw=6, head=1.0):
    """Fat comic arrow along a polyline, ink outline."""
    pts = np.array(pts, np.float32)
    d = np.gradient(pts, axis=0); d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-6
    nrm = np.stack([-d[:, 1], d[:, 0]], 1)
    hw = width / 2
    body_end = len(pts) - 1
    L = pts[:body_end + 1] + nrm[:body_end + 1] * hw; R = pts[:body_end + 1] - nrm[:body_end + 1] * hw
    tip = pts[-1] + d[-1] * width * 1.3 * head
    hl = pts[-1] + nrm[-1] * width * 1.1 * head; hr = pts[-1] - nrm[-1] * width * 1.1 * head
    poly = [tuple(p) for p in L] + [tuple(hl), tuple(tip), tuple(hr)] + [tuple(p) for p in R[::-1]]
    fill(a, [(x + 7, y + 8) for x, y in poly], INK); shape(a, poly, col, lw)

# ---------- the turtle (side view, facing left) ----------
def turtle(a, cx, cy, s, t, eye=1.0, swim=1.0, look=0.0, worried=False):
    lw = max(3.0, 7 * s)
    cy = cy + math.sin(t * 2.3) * 6 * s
    L, Ht, Hb = 210 * s, 128 * s, 36 * s
    fl = math.sin(t * 3.4) * swim
    # far flippers (darker)
    shape(a, ell(cx + 150 * s, cy + 36 * s, 62 * s, 21 * s, 30, 0.55 + 0.25 * fl), SKIN_D, lw)
    shape(a, ell(cx - 115 * s, cy + 36 * s, 88 * s, 25 * s, 30, -0.55 + 0.35 * fl), SKIN_D, lw)
    # tail
    shape(a, [(cx + 180 * s, cy + 6 * s), (cx + 258 * s, cy + 30 * s), (cx + 182 * s, cy + 34 * s)], SKIN, lw)
    # neck + head
    hx, hy = cx - 262 * s, cy - 14 * s + look * 10 * s
    shape(a, [(cx - 150 * s, cy - 40 * s), (hx + 20 * s, hy - 34 * s), (hx + 26 * s, hy + 36 * s), (cx - 150 * s, cy + 32 * s)], SKIN, lw)
    head = ell(hx, hy, 68 * s, 52 * s, 40, -0.08)
    shape(a, head, SKIN, lw)
    ht_poly(a, head, lambda xx, yy: np.clip((yy - hy) / (52 * s), 0, 1) * 0.55, SKIN_D)
    line(a, head, INK, lw, True)
    # shell
    up = [(cx + L * math.cos(th), cy - Ht * math.sin(th) * (1.0 + 0.06 * math.cos(th))) for th in np.linspace(0, math.pi, 36)]
    lo = [(cx + L * math.cos(th), cy + Hb * math.sin(th)) for th in np.linspace(math.pi, 2 * math.pi, 24)]
    shell = up + lo
    fill(a, shell, SHELL)
    ht_poly(a, up + [(cx - L, cy), (cx + L, cy)], lambda xx, yy: np.clip((yy - (cy - Ht * 0.25)) / (Ht * 1.1), 0, 1) * 0.75
            + np.clip((xx - cx) / L, 0, 1) * 0.25, SHELL_D)
    fill(a, lo + [(cx - L * 0.97, cy - 4 * s), (cx + L * 0.97, cy - 4 * s)], PLAST)
    line(a, [(cx - L * 0.98, cy), (cx + L * 0.98, cy)], INK, lw * 0.8)
    # scutes: rim band + three hexagons
    rim = [(cx + (L - 30 * s) * math.cos(th), cy - (Ht - 28 * s) * math.sin(th)) for th in np.linspace(0.08, math.pi - 0.08, 30)]
    line(a, rim, INK, lw * 0.7)
    for th in np.linspace(0.25, math.pi - 0.25, 7):
        line(a, [(cx + (L - 30 * s) * math.cos(th), cy - (Ht - 28 * s) * math.sin(th)), (cx + L * math.cos(th), cy - Ht * math.sin(th) * 0.98)], INK, lw * 0.6)
    for k in (-1, 0, 1):
        hxk, hyk = cx + k * 92 * s, cy - Ht * 0.5 + abs(k) * 12 * s
        hexp = [(hxk + 44 * s * math.cos(math.pi / 3 * j), hyk + 30 * s * math.sin(math.pi / 3 * j)) for j in range(6)]
        fill(a, hexp, mix(SHELL, YEL, 0.18)); line(a, hexp, INK, lw * 0.7, True)
    line(a, ell(cx - 70 * s, cy - Ht * 0.8, 70 * s, 26 * s, 14, -0.1, 3.5, 4.4), WHITE, lw * 0.9)   # gloss
    line(a, shell, INK, lw, True)
    # face
    ex, ey = hx - 18 * s, hy - 12 * s
    if eye > 0.15:
        e = ell(ex, ey, 21 * s, 21 * s * eye, 24)
        shape(a, e, WHITE, lw * 0.6)
        fill(a, ell(ex - 7 * s - look * 2 * s, ey + 1 * s, 10 * s, 10 * s * eye, 16), INK)
        fill(a, ell(ex - 10 * s, ey - 4 * s * eye, 3.5 * s, 3.5 * s, 8), WHITE)
    else:
        line(a, ell(ex, ey, 20 * s, 9 * s, 12, 0, 0.2, math.pi - 0.2), INK, lw * 0.7)
    if worried:
        line(a, [(ex - 26 * s, ey - 34 * s), (ex + 12 * s, ey - 26 * s)], INK, lw * 0.7)
    fill(a, ell(hx - 58 * s, hy - 10 * s, 4 * s, 3 * s, 8), INK)
    line(a, ell(hx - 30 * s, hy + 12 * s, 24 * s, 12 * s, 12, 0.1, 0.3, 2.6) if not worried else
         ell(hx - 30 * s, hy + 26 * s, 16 * s, 8 * s, 12, 0, 3.6, 5.8), INK, lw * 0.6)
    # near flippers
    shape(a, ell(cx - 128 * s, cy + 56 * s, 98 * s, 27 * s, 30, -0.35 + 0.4 * fl), SKIN, lw)
    shape(a, ell(cx + 138 * s, cy + 56 * s, 64 * s, 22 * s, 30, 0.4 - 0.3 * fl), SKIN, lw)
    for (sx_, sy_) in ((-150, 60), (-110, 52)):
        fill(a, ell(cx + sx_ * s, cy + sy_ * s, 6 * s, 4 * s, 8), SKIN_D)
    return (cx + 232 * s, cy + 20 * s)        # vent (cloaca), just behind the tail

def stream(a, x, y, t, n=9, rate=0.7, rise=520, spread=60, r0=6, r1=20, seed=0):
    rr = np.random.default_rng(seed); ph = rr.random(n); dx = rr.uniform(-1, 1, n); wob = rr.uniform(0, 6.28, n)
    for k in range(n):
        age = (t * rate + ph[k]) % 1.0
        bx = x + 30 * age + dx[k] * spread * age + math.sin(t * 5 + wob[k]) * 10 * age
        by = y - rise * age
        bubble(a, bx, by, r0 + (r1 - r0) * min(1.0, age * 1.4))

# ---------- backgrounds ----------
_BG = {}
def water(w, h, surface=0, bed=True, seed=1, sky=YEL):
    key = (w, h, surface, bed, seed, sky)
    if key in _BG: return _BG[key].copy()
    a = np.zeros((h, w, 3), np.uint8); a[:] = CYAN
    rr = np.random.default_rng(seed)
    for k in range(4):                                         # light rays
        x = rr.uniform(0.05, 0.95) * w; ww = rr.uniform(40, 90)
        fill(a, [(x, surface), (x + ww, surface), (x + ww + 0.35 * h, h), (x + 0.35 * h - ww * 0.6, h)], CYAN_L)
    yy = np.arange(h, dtype=np.float32)[:, None].repeat(w, 1)
    ht(a, np.clip((yy - surface) / max(1, h - surface), 0, 1) ** 1.3 * 0.8, BLUE)
    if surface > 0:
        a[:surface] = sky if sky != NAVY else NAVY
        if sky == YEL:
            ht(a[:surface], 0.35, (255, 236, 150))
        wave = [(x, surface + 8 * math.sin(x / 38)) for x in np.linspace(0, w, 60)]
        fill(a, [(0, 0), (w, 0)] + wave[::-1], a[0, 0].tolist())
        if sky == YEL:
            sx = int(w * 0.8); fill(a, ell(sx, surface * 0.5, surface * 0.3, surface * 0.3, 32), (255, 248, 210))
            line(a, ell(sx, surface * 0.5, surface * 0.3, surface * 0.3, 32), INK, 5, True)
        fill(a, wave + [(w, surface + 26), (0, surface + 26)], CYAN_L)
        line(a, wave, INK, 6)
    if bed:
        by = h - 0.12 * h
        sand = [(x, by + 18 * math.sin(x / 70 + seed) + 10 * math.sin(x / 23)) for x in np.linspace(0, w, 50)]
        poly = sand + [(w, h), (0, h)]
        fill(a, poly, SAND)
        ht_poly(a, poly, lambda xx, yy: np.clip((yy - by) / (0.12 * h), 0, 1) * 0.6 + 0.1, SAND_D)
        line(a, sand, INK, 6)
        for k in range(7):
            px, py = rr.uniform(0, w), by + rr.uniform(0.25, 0.8) * 0.12 * h
            shape(a, ell(px, py, rr.uniform(14, 30), rr.uniform(9, 16), 20), (170, 160, 150), 4)
    _BG[key] = a
    return a.copy()

def reeds(a, t, xs, h, seed=3):
    rr = np.random.default_rng(seed)
    for k, x in enumerate(xs):
        hh = rr.uniform(0.25, 0.45) * h; base = h - 0.08 * h
        pts = [(x + math.sin(t * 1.6 + k + u * 2) * 26 * u * u, base - hh * u) for u in np.linspace(0, 1, 10)]
        line(a, pts, INK, 20); line(a, pts, GREEN, 10)

PAGE = np.zeros((H, W, 3), np.uint8); PAGE[:] = PAPER
ht(PAGE, 0.16, DOTPINK)
_n = np.random.default_rng(7).normal(0, 1, (H // 4, W // 4)).astype(np.float32)
PTEX = (1 - 0.035 * np.clip(cv2.resize(cv2.GaussianBlur(_n, (0, 0), 1.2), (W, H)), -2, 2) ** 2)[..., None].astype(np.float32)

# ---------- panels ----------
def panel(a, rect, draw, slide=1.0, side=1):
    x0, y0, x1, y1 = rect; w, h = x1 - x0, y1 - y0
    dx = int((1 - slide) * 1150 * side)
    sub = np.zeros((h, w, 3), np.uint8); draw(sub, w, h, (x0 + dx, y0))
    X0, Y0 = x0 + dx, y0
    # hard offset shadow
    sx0, sy0, sx1, sy1 = max(0, X0 + 14), max(0, Y0 + 16), min(W, X0 + w + 14), min(H, Y0 + h + 16)
    if sx1 > sx0: a[sy0:sy1, sx0:sx1] = INK
    cx0, cx1 = max(0, X0), min(W, X0 + w)
    if cx1 > cx0: a[Y0:Y0 + h, cx0:cx1] = sub[:, cx0 - X0:cx1 - X0]
    if cx1 > cx0: cv2.rectangle(a, (X0, Y0), (X0 + w - 1, Y0 + h - 1), INK, 9)
    return X0, Y0

def slide_u(lt, at=0.0, d=0.32): return back(max(0.0, min(1.0, (lt - at) / d)), 1.2)

# ---------- text (PIL, after the paper) ----------
TXT = []
_TC = {}
def _timg(s, kind, size, fill_, stroke, shadow, rot):
    key = (s, kind, size, fill_, stroke, shadow, rot)
    if key in _TC: return _TC[key]
    f = F(size, kind); bb = f.getbbox(s, stroke_width=stroke)
    pad = stroke + 24
    im = Image.new("RGBA", (bb[2] - bb[0] + 2 * pad + 14, bb[3] - bb[1] + 2 * pad + 14), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, oy = pad - bb[0], pad - bb[1]
    if shadow: d.text((ox + 8, oy + 9), s, font=f, fill=INK + (255,), stroke_width=stroke, stroke_fill=INK + (255,))
    d.text((ox, oy), s, font=f, fill=fill_ + (255,), stroke_width=stroke, stroke_fill=INK + (255,))
    if rot: im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    _TC[key] = im; return im
def text(s, size, cx, cy, col=YEL, al=1.0, stroke=7, kind="bang", pop=1.0, rot=0, shadow=True):
    if al > 0.01 and pop > 0.02: TXT.append((s, int(size), cx, cy, col, al, stroke, kind, pop, rot, shadow))
def fit(s, size, maxw=W - 120, kind="bang"):
    while F(size, kind).getlength(s) > maxw and size > 30: size -= 4
    return size
BOX = []
def nbox(s, x, y, size=40, col=YEL, al=1.0, anchor="tl"):
    BOX.append((s, x, y, size, col, al, anchor))
def draw_texts(img):
    for s, x, y, size, col, al, anchor in BOX:
        f = F(size, "cn"); tw = f.getlength(s); bw, bh = tw + 40, size + 30
        if anchor == "br": x, y = x - bw, y - bh
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        d.rectangle([x, y, x + bw, y + bh], fill=col + (255,), outline=INK + (255,), width=5)
        d.text((x + 20, y + 12), s, font=f, fill=INK + (255,))
        if al < 0.99: ov.putalpha(ov.getchannel("A").point(lambda v: int(v * al)))
        img.alpha_composite(ov)
    for s, size, cx, cy, col, al, stroke, kind, pop, rot, shadow in TXT:
        im = _timg(s, kind, size, col, stroke, shadow, rot)
        if abs(pop - 1) > 0.01: im = im.resize((max(1, int(im.width * pop)), max(1, int(im.height * pop))), Image.BICUBIC)
        if al < 0.99:
            im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * al)))
        img.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))
    TXT.clear(); BOX.clear()

def fade(lt, at, d=0.25): return ease((lt - at) / d)
def popv(lt, at, d=0.32): return back(max(0.0, min(1.0, (lt - at) / d)))
def wt_(ln, i): return words[min(ln["_w0"] + i, ln["_w1"] - 1)][1] - ln["_s"]
def headline(lines, lt, first=False):
    for k, (s, size, y, col) in enumerate(lines):
        p = 1.0 if first else popv(lt, 0.05 + 0.12 * k)
        text(s, fit(s, size), W / 2, y, col, 1.0, 8, pop=p, rot=(2 if k % 2 else -2))

# ---------- scenes ----------
def S_hook(a, sc, ln, lt, dur, t, first=True):
    headline([("SOME TURTLES", 150, 170, WHITE), ("BREATHE THROUGH", 150, 320, YEL), ("THEIR BUTTS!", 170, 480, RED)], lt, first)
    def d(sub, w, h, org):
        sub[:] = water(w, h, 0, True, 1)
        reeds(sub, t, [70, 120, w - 90], h)
        z = 1.22 + 0.06 * min(1.0, lt / 2.5)
        vx, vy = turtle(sub, w * 0.43, h * 0.55, z, t)
        stream(sub, vx, vy, t, 12, 0.8, 470, 70, 11, 28)
        pb = 1 + 0.1 * max(0.0, math.sin(t * 7.0))
        burst(sub, w * 0.78, h * 0.2, 125 * pb, YEL, 13, t * 0.4)
        text("BLUB!", 104, org[0] + w * 0.78, org[1] + h * 0.2 - 6, RED, 1.0, 7, pop=pb, rot=8)
        nbox("TRUE STORY!", org[0] + 24, org[1] + 24, 38)
    panel(a, (50, 600, 1030, 1490), d)

def S_loop(a, sc, ln, lt, dur, t):
    headline([("BUT THE WEIRDEST PART...", 112, 170, WHITE)], lt)
    def d1(sub, w, h, org):
        sub[:] = water(w, h, 0, False, 2)
        turtle(sub, w * 0.5 + 262 * 2.4 - 40, h * 0.55, 2.4, t, eye=1.0, swim=0.3, look=0.4, worried=True)
        for k in range(3):                                    # comic "shock" lines
            th = -2.2 + 0.35 * k
            line(sub, [(w * 0.28 + 150 * math.cos(th), h * 0.42 + 150 * math.sin(th)), (w * 0.28 + 205 * math.cos(th), h * 0.42 + 205 * math.sin(th))], INK, 9)
        text("?!", 150, org[0] + w * 0.12, org[1] + h * 0.26, YEL, 1.0, 8, pop=popv(lt, 0.25), rot=-8)
    panel(a, (50, 290, 1030, 860), d1, slide_u(lt, 0.0), -1)
    at = max(0.6, wt_(ln, 4) - 0.15)
    if lt > at:
        def d2(sub, w, h, org):
            sub[:] = water(w, h, 90, True, 3)
            tx, ty = w * 0.62, h * 0.78
            turtle(sub, tx, ty, 0.52, t)
            yy = 110
            while yy < ty - 70:
                line(sub, [(w * 0.2, yy), (w * 0.2, min(yy + 24, ty - 60))], INK, 7); yy += 42
            fill(sub, [(w * 0.2 - 22, ty - 70), (w * 0.2 + 22, ty - 70), (w * 0.2, ty - 34)], INK)
            text("HOW LONG?!", 120, org[0] + w * 0.5, org[1] + h * 0.42, YEL, 1.0, 8, pop=popv(lt, at + 0.25), rot=-4)
        panel(a, (50, 900, 1030, 1490), d2, slide_u(lt, at), 1)

def S_meet(a, sc, ln, lt, dur, t):
    headline([("MEET THE", 96, 150, WHITE), ("FITZROY RIVER TURTLE", 150, 285, YEL)], lt)
    def d(sub, w, h, org):
        sub[:] = water(w, h, 120, True, 4)
        reeds(sub, t, [60, 110, 160, w - 140, w - 80], h, 5)
        u = min(1.0, lt / max(0.5, dur))
        vx, vy = turtle(sub, w * (0.62 - 0.12 * u), h * 0.55, 1.2, t, swim=1.3)
        stream(sub, vx, vy, t, 6, 0.6, 360, 50, 6, 16, 4)
        nbox("QUEENSLAND, AUSTRALIA", org[0] + w - 24, org[1] + h - 24, 40, YEL, fade(lt, wt_(ln, 6) - 0.1), "br")
    panel(a, (50, 420, 1030, 1490), d, slide_u(lt), 1)

def S_pump(a, sc, ln, lt, dur, t):
    headline([("WATER IN...", 140, 165, WHITE), ("...WATER OUT!", 140, 305, YEL)], lt)
    def d(sub, w, h, org):
        sub[:] = water(w, h, 0, True, 6)
        vx, vy = turtle(sub, w * 0.36, h * 0.52, 1.12, t, swim=0.5)
        ph = (lt * 1.25) % 1.0; inn = ph < 0.5
        if inn:
            k = ph / 0.5
            pts = [(vx + 330 - 30 * math.sin(u * 2), vy - 200 + 190 * u) for u in np.linspace(0, 1, 14)]
            pts = [(x - 120 * u_ * u_, y) for (x, y), u_ in zip(pts, np.linspace(0, 1, 14))]
            arrow(sub, pts[: max(3, int(14 * min(1, k * 2.2)))] if k < 0.45 else pts[:12], 46, CYAN_L, 6)
            burst(sub, w * 0.82, h * 0.2, 105, YEL, 12, 0.3)
            text("IN!", 120, org[0] + w * 0.82, org[1] + h * 0.2 - 4, BLUE, 1.0, 7, pop=popv(ph / 0.5 * 0.5, 0.0, 0.12), rot=-6)
        else:
            k = (ph - 0.5) / 0.5
            pts = [(vx + 50 + 260 * u, vy + 10 - 40 * math.sin(u * 3)) for u in np.linspace(0, 1, 14)]
            arrow(sub, pts[: max(3, int(14 * min(1, k * 2.2)))], 46, WHITE, 6)
            for j in range(5): bubble(sub, vx + 60 + 70 * j * k, vy - 30 - 40 * j * k - 20 * j, 10 + 4 * j)
            burst(sub, w * 0.82, h * 0.2, 115, RED, 12, 0.1)
            text("OUT!", 116, org[0] + w * 0.82, org[1] + h * 0.2 - 4, YEL, 1.0, 7, pop=popv((ph - 0.5) / 0.5 * 0.5, 0.0, 0.12), rot=6)
    panel(a, (50, 430, 1030, 1490), d, slide_u(lt), -1)

def lens_inset(sub, w, h, t, lt, grow=1.0, oxy=0.0, oxy_lt=0.0):
    """Turtle bottom-left + magnifier showing the two sacs with branching bumps."""
    vx, vy = turtle(sub, w * 0.3, h * 0.8, 0.62, t, swim=0.4)
    cx, cy, R = w * 0.56, h * 0.38, min(w, h) * 0.36
    fill(sub, [(vx - 8, vy), (cx - R * 0.55, cy + R * 0.82), (cx + R * 0.2, cy + R * 0.98)], WHITE)
    line(sub, [(cx - R * 0.55, cy + R * 0.82), (vx - 8, vy), (cx + R * 0.2, cy + R * 0.98)], INK, 6)
    fill(sub, ell(cx + 14, cy + 16, R + 12, R + 12, 64), INK)
    circ = ell(cx, cy, R, R, 64)
    inner = np.zeros_like(sub); inner[:] = PINK_L
    ht(inner, 0.3, PINK)
    sacs = []
    for side in (-1, 1):
        sx, sy = cx + side * R * 0.42, cy + 10
        o = ell(sx, sy, R * 0.32, R * 0.62, 48, side * 0.18)
        fill(inner, o, CYAN_L); ht_poly(inner, o, lambda xx, yy: 0.25 + 0 * xx, CYAN)
        line(inner, o, PINK, 26, True); line(inner, ell(sx, sy, R * 0.32 + 13, R * 0.62 + 13, 48, side * 0.18), INK, 6, True)
        sacs.append((sx, sy, o))
    rr = np.random.default_rng(11)
    for si, (sx, sy, o) in enumerate(sacs):                    # branching bumps grow inward
        n = 16
        for k in range(n):
            if k / n > grow: break
            px, py = o[(k * 3 + 1) % len(o)]
            dx, dy = sx - px, sy - py; dl = math.hypot(dx, dy) + 1e-6; dx, dy = dx / dl, dy / dl
            Lp = (34 + 14 * rr.random()) * min(1.0, (grow - k / n) * 4)
            wig = math.sin(t * 3 + k) * 4
            tip = (px + dx * Lp + wig, py + dy * Lp)
            for (q, wd) in ((INK, 14), (PINK, 7)):
                line(inner, [(px, py), tip], q, wd)
                for sgn in (-1, 1):
                    bx, by = px + dx * Lp * 0.55, py + dy * Lp * 0.55
                    line(inner, [(bx, by), (bx + (dx * 0.6 - sgn * dy * 0.8) * Lp * 0.45 + wig, by + (dy * 0.6 + sgn * dx * 0.8) * Lp * 0.45)], q, wd)
            for (q, rad) in ((INK, 9), (PINK, 5)):
                fill(inner, ell(tip[0], tip[1], rad, rad, 12), q)
    # blood vessels + oxygen
    if oxy > 0:
        for side in (-1, 1):
            sx = cx + side * R * 0.42
            ves = [(sx + side * R * 0.25 * math.sin(u * 3), cy - R * 0.5 + R * 1.5 * u) for u in np.linspace(0, 1, 20)]
            line(inner, ves, INK, 22); line(inner, ves, RED, 12)
            for j in range(6):
                u = ((oxy_lt * 0.6 + j / 6) % 1.0)
                if u < oxy:
                    q = ves[min(19, int(u * 19))]
                    fill(inner, ell(q[0], q[1], 9, 9, 12), (255, 240, 240)); line(inner, ell(q[0], q[1], 9, 9, 12), INK, 3, True)
        for j in range(8):                                   # O2 bubbles drifting into the sacs
            u = ((oxy_lt * 0.45 + j / 8) % 1.0)
            side = -1 if j % 2 else 1
            sx = cx + side * R * 0.42
            bx = sx + side * R * 0.15 * (1 - u) + math.sin(t * 4 + j) * 8; by = cy - R * 0.55 + R * 0.95 * u
            bubble(inner, bx, by, 17 * (1 - 0.5 * u))
    m = np.zeros(sub.shape[:2], np.uint8); cv2.fillPoly(m, [P(circ)], 255, cv2.LINE_AA, shift=3)
    mf = (m.astype(np.float32) / 255)[..., None]
    sub[:] = (sub * (1 - mf) + inner * mf).astype(np.uint8)
    line(sub, circ, INK, 12, True); line(sub, ell(cx, cy, R - 10, R - 10, 64), WHITE, 6, True)
    return cx, cy, R

def S_sacs(a, sc, ln, lt, dur, t):
    headline([("2 LITTLE SACS", 150, 165, YEL), ("FULL OF TINY BUMPS", 104, 300, WHITE)], lt)
    def d(sub, w, h, org):
        sub[:] = water(w, h, 0, True, 7)
        g = max(0.0, min(1.0, (lt - wt_(ln, 5)) / 1.2))
        cx, cy, R = lens_inset(sub, w, h, t, lt, grow=g)
        nbox("CLOSE-UP!", org[0] + 24, org[1] + 24, 38)
        if lt > wt_(ln, 2): text("SAC", 64, org[0] + cx - R * 0.42, org[1] + cy - R * 0.75, WHITE, 1, 6, pop=popv(lt, wt_(ln, 2)), rot=-4)
        if lt > wt_(ln, 2) + 0.15: text("SAC", 64, org[0] + cx + R * 0.42, org[1] + cy - R * 0.75, WHITE, 1, 6, pop=popv(lt, wt_(ln, 2) + 0.15), rot=4)
    panel(a, (50, 410, 1030, 1490), d, slide_u(lt), 1)

def S_oxygen(a, sc, ln, lt, dur, t):
    headline([("OXYGEN", 170, 175, YEL), ("STRAIGHT FROM THE WATER", 92, 320, WHITE)], lt)
    def d(sub, w, h, org):
        sub[:] = water(w, h, 0, True, 7)
        cx, cy, R = lens_inset(sub, w, h, t, lt, grow=1.0, oxy=min(1.0, lt / 0.8), oxy_lt=lt)
        nbox("O2 INTO BLOOD", org[0] + 24, org[1] + 24, 40, YEL)
        pb = popv(lt, 0.5)
        burst(sub, w * 0.86, h * 0.72, 92 * pb, RED, 11, 0.2)
        text("GULP!", 80, org[0] + w * 0.86, org[1] + h * 0.72 - 4, YEL, 1, 6, pop=pb, rot=-8)
    panel(a, (50, 420, 1030, 1490), d, slide_u(lt), -1)

def S_days(a, sc, ln, lt, dur, t):
    headline([("UNDERWATER", 136, 150, WHITE), ("FOR DAYS!", 170, 290, YEL)], lt)
    rects = [(50, 420, 1030, 760), (50, 790, 1030, 1130), (50, 1160, 1030, 1490)]
    for k, rc in enumerate(rects):
        at = k * dur * 0.22
        if lt < at: continue
        def d(sub, w, h, org, k=k):
            sub[:] = water(w, h, 70, True, 20 + k, YEL if k != 1 else NAVY)
            if k == 1:
                fill(sub, ell(w * 0.82, 34, 22, 22, 24), (255, 246, 200)); fill(sub, ell(w * 0.82 + 10, 28, 20, 20, 24), NAVY)
                for j in range(6): fill(sub, ell(60 + 130 * j, 20 + 22 * (j % 2), 3, 3, 6), WHITE)
            turtle(sub, w * (0.42 + 0.08 * k), h * 0.7, 0.5, t + k, eye=(1.0 if k != 1 else 0.0), swim=0.25)
            stream(sub, w * (0.42 + 0.08 * k) + 98, h * 0.7 + 15, t, 4, 0.5, 120, 20, 4, 9, 30 + k)
            nbox(f"DAY {k + 1}", org[0] + 22, org[1] + 88, 42, YEL if k != 1 else WHITE)
            if k == 2: nbox("STILL DOWN THERE!", org[0] + w - 22, org[1] + h - 22, 40, WHITE, fade(lt, at + 0.4), "br")
        panel(a, rc, d, slide_u(lt, at, 0.28), -1 if k % 2 else 1)

POST = []
def toggle(a, on, y=430, x0=180, x1=900, hh=136):
    r = hh / 2
    trk = ell(x0 + r, y, r, r, 30, 0, math.pi / 2, 1.5 * math.pi) + ell(x1 - r, y, r, r, 30, 0, -math.pi / 2, math.pi / 2)
    fill(a, [(x + 12, y_ + 14) for x, y_ in trk], INK); fill(a, trk, WHITE)
    kx = x0 + r + (x1 - x0 - hh) * on
    if on > 0:
        ri = r - 12
        g = ell(x0 + r, y, ri, ri, 30, 0, math.pi / 2, 1.5 * math.pi) + [(kx, y - ri), (kx, y + ri)]
        fill(a, g, GREEN); ht_poly(a, g, lambda xx, yy: 0.3 + 0 * xx, (40, 130, 64))
    line(a, trk, INK, 8, True)
    kn = ell(kx, y, r - 4, r - 4, 40)
    fill(a, [(x + 6, y_ + 8) for x, y_ in kn], INK); fill(a, kn, SHELL)
    ht_poly(a, kn, lambda xx, yy: np.clip((yy - y + 10) / r, 0, 1) * 0.7, SHELL_D)
    hexp = [(kx + 30 * math.cos(math.pi / 3 * j + on * 3), y + 30 * math.sin(math.pi / 3 * j + on * 3)) for j in range(6)]
    fill(a, hexp, mix(SHELL, YEL, 0.25)); line(a, hexp, INK, 5, True)
    for j in range(6):
        th = math.pi / 3 * j + on * 3 + math.pi / 6
        line(a, [(kx + 28 * math.cos(th), y + 28 * math.sin(th)), (kx + (r - 6) * math.cos(th), y + (r - 6) * math.sin(th))], INK, 4)
    line(a, kn, INK, 7, True)

def S_end(a, sc, ln, lt, dur, t):
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.35)
    text("SOUNDS FAKE?", 160, W / 2, 200, WHITE, 1.0, 8, pop=popv(lt, 0.0, 0.25), rot=-2)
    pb = popv(lt, click + 0.25)
    if lt > click + 0.2: burst(a, W / 2, 660, 330 * pb, YEL, 16, 0.2, 8, 0.62)
    toggle(a, on)
    text("FAKE", 72, W / 2 + 70, 432, RED, 1 - on, 0, shadow=False)
    text("TRUE", 72, W / 2 - 70, 432, WHITE, ease((on - 0.5) / 0.4), 6, shadow=False)
    text("IT'S TRUE!", 190, W / 2, 650, RED, fade(lt, click + 0.25, 0.15), 9, pop=pb, rot=-3)
    text("Follow for more.", 76, W / 2, 1010, INK, fade(lt, click + 0.6), 0, "cn", shadow=False)
    def d(sub, w, h, org):
        sub[:] = water(w, h, 0, True, 9)
        vx, vy = turtle(sub, w * 0.45, h * 0.55, 0.8, t, swim=1.2)
        stream(sub, vx, vy, t, 7, 0.8, 260, 40, 5, 14, 9)
    panel(a, (50, 1110, 1030, 1490), d, slide_u(lt, click + 0.5), 1)

SCENES = dict(hook=S_hook, loop=S_loop, meet=S_meet, pump=S_pump, sacs=S_sacs, oxygen=S_oxygen, days=S_days, end=S_end)

# ---------- audio ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
rng = np.random.default_rng(22)
NOTE = {n_: 261.63 * 2 ** (k / 12) for k, n_ in enumerate("C C# D D# E F F# G G# A A# B".split())}
def nf(nm, o=0): return NOTE[nm] * 2 ** o
def tuba(f, dur=0.35, gain=0.12):
    s = np.arange(int(dur * SR)) / SR
    sig = sum(np.sin(2 * np.pi * f * h * s) / h ** 1.2 for h in (1, 2, 3, 4)) * np.minimum(1, s / 0.02) * np.exp(-s * 5)
    return (sig * gain).astype(np.float32)
def pizz(f, gain=0.05):
    s = np.arange(int(0.4 * SR)) / SR
    return ((np.sin(2 * np.pi * f * s) + 0.4 * np.sin(4 * np.pi * f * s)) * np.exp(-s * 14) * gain).astype(np.float32)
def block(at, gain=0.05, f=1800):
    s = np.arange(int(0.05 * SR)) / SR; place(music, at, (np.sin(2 * np.pi * f * s) * np.exp(-s * 120)).astype(np.float32), gain)
def blub(at, gain=0.09, f0=220):
    s = np.arange(int(0.16 * SR)) / SR
    place(music, at, (np.sin(2 * np.pi * (f0 * s + 900 * s * s / 0.16 * 0.5 * 2)) * np.sin(np.pi * s / 0.16)).astype(np.float32), gain)
def slide(at, up=True, gain=0.05, dur=0.35):
    s = np.arange(int(dur * SR)) / SR; f = (600 + 900 * s / dur) if up else (1500 - 900 * s / dur)
    place(music, at, (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * s / dur)).astype(np.float32), gain)
BEAT = 60 / 120
PROG = [("F", "A", "C"), ("C", "E", "G"), ("D", "F", "A"), ("A#", "D", "F")]
BASS = [("F", "C"), ("C", "G"), ("D", "A"), ("A#", "F")]
for b in range(int(total / (BEAT * 4)) + 1):
    t0 = b * BEAT * 4; ch = PROG[b % 4]; bs = BASS[b % 4]
    for k in range(4):
        place(music, t0 + k * BEAT, tuba(nf(bs[k % 2], -2), 0.3, 0.13))
        for j, nm in enumerate(ch):
            place(music, t0 + k * BEAT + BEAT / 2, pizz(nf(nm, 0 + (j == 0 and k % 2)), 0.028))
        block(t0 + k * BEAT + BEAT / 2, 0.025, 1900 if k % 2 else 1500)
    mel = [ch[2], ch[1], ch[2], ch[0]] if b % 2 == 0 else [ch[0], ch[1], ch[2], ch[1]]
    for k, nm in enumerate(mel): place(music, t0 + k * BEAT + (0.25 if k % 2 else 0), pizz(nf(nm, 1), 0.035))
hook_hit(music, 0.3); blub(0.05, 0.12, 180); blub(0.3, 0.1, 240); blub(0.55, 0.09, 300)
for i, ln in enumerate(spec["lines"]):
    st = ln["scene"]["type"]; s0 = ln["_s"]; dur = ln["_se"] - s0
    if i > 0: whoosh(music, s0, 0.1)
    if st == "hook":
        for k in range(1, int(dur / 0.9)): blub(k * 0.9 + 0.2, 0.06, 200 + 30 * k)
    if st == "loop":
        slide(s0 + 0.1, False, 0.04); slide(words[min(ln["_w0"] + 4, ln["_w1"] - 1)][1] - 0.05, True, 0.04)
    if st == "pump":
        k = 0.0
        while k < dur:
            block(s0 + k, 0.06, 1200); blub(s0 + k + 0.42, 0.09, 200); k += 0.8
    if st == "sacs":
        for j in range(8): block(s0 + words[min(ln["_w0"] + 5, ln["_w1"] - 1)][1] - s0 + j * 0.14, 0.035, 2200 + 120 * j)
    if st == "oxygen":
        for j in range(5): blub(s0 + 0.3 + j * 0.35, 0.07, 260 + 40 * j)
    if st == "days":
        for k in range(3): slide(s0 + k * dur * 0.22, k % 2 == 0, 0.03, 0.25); block(s0 + k * dur * 0.22 + 0.25, 0.08, 900)
    if st == "end":
        c = s0 + ln["scene"].get("click_at", 0.45); block(c, 0.2, 1100)
        for j, nm in enumerate(("F", "A", "C", "F")): place(music, c + 0.2 + j * 0.07, pizz(nf(nm, 1 + (j == 3)), 0.08))
        place(music, c + 0.22, tuba(nf("F", -2), 0.8, 0.18))
write_audio(voice, music, work + "_audio.wav", music_gain=0.5, duck=0.45)

# ---------- captions + compositing ----------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0].upper() for i in g]; size = 66
    f = F(size, "cn")
    while f.getlength(" ".join(ws)) > W - 220 and size > 36: size -= 4; f = F(size, "cn")
    tw_ = f.getlength(" ".join(ws)); x = (W - tw_) / 2; y = 1585
    d = ImageDraw.Draw(img)
    d.rectangle([x - 40 + 10, y - 22 + 12, x + tw_ + 40 + 10, y + size + 26 + 12], fill=INK)
    d.rectangle([x - 40, y - 22, x + tw_ + 40, y + size + 26], fill=WHITE, outline=INK, width=6)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]; wl = f.getlength(w)
        if on: d.rectangle([x - 8, y - 6, x + wl + 8, y + size + 10], fill=YEL)
        d.text((x, y - size * 0.05), w, font=f, fill=INK); x += f.getlength(w + " ")

def scene_img(st, ln, lt, dur, t):
    a = PAGE.copy()
    SCENES[st](a, ln["scene"], ln, lt, dur, t)
    a = np.clip(a.astype(np.float32) * PTEX, 0, 255).astype(np.uint8)
    img = Image.fromarray(a).convert("RGBA")
    draw_texts(img)
    return img

HOOK = spec["lines"][0]
def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    st = ln["scene"]["type"]
    img = scene_img(st, ln, lt, dur, t)
    if st == "end":
        lp = ease((lt - (dur - 0.45)) / 0.4)
        if lp > 0: img = Image.blend(img, scene_img("hook", HOOK, 0.0, 2.0, t), lp)
    img = img.convert("RGB")
    caption(img, t)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 12, W, H], fill=INK); d.rectangle([0, H - 12, int(W * t / total), H], fill=RED)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=24); print(f"done {total:.1f}s")
