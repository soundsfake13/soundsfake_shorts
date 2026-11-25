"""Day 54 — BAUHAUS-POSTER style (honeybees dance to give directions).
A 1920s Bauhaus exhibition poster that moves:
- printed cream poster stock (fibre grain, faint misregistered ink), every element a flat primary shape:
  red circle, yellow, blue, black — no gradients, no outlines except thick black rules;
- the bee itself is pure geometry (black circle thorax, red circle head, yellow disc abdomen with black bands,
  cream circle wings with black rims), rotated and wiggled as a sprite;
- the waggle dance is drawn as a diagram: thick black waggle run + thin return arcs (figure-eight), the bee traces it;
- comb = hexagon grid in yellow line on black; sun = red disc; flowers = blue disc + red triangle petals;
- type: Josefin Sans Bold (geometric, Futura-era), lowercase titles, small spaced uppercase labels, vertical
  side labels, numbered steps ('1. find'), angle arcs and a 40° protractor, stopwatch pie;
- motion: snappy slide-ins with overshoot on a grid, shapes pop by scale, 90° rotations;
- cuts alternate a circle iris (primary ring at its edge) and a red/yellow/blue bar sweep;
- ending: black pill track FAKE → TRUE, the knob is the bee's striped abdomen; fills blue; dissolves into the hook.
Music: original 120 bpm C-major marimba/woodblock 'mechanical ballet' figure + plucked bass, bee buzz on dances.
Usage: python3 engine/styles/day54_bauhaus.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]

RED = (214, 58, 43); YEL = (242, 183, 5); BLU = (28, 76, 158); BLK = (24, 22, 22); CRM = (241, 233, 214)
GRY = (70, 66, 62)

_F = {}
def F(s, w=700):
    k = (int(s), w)
    if k not in _F:
        f = ImageFont.truetype(f"{FONTS}/JosefinSans-VF.ttf", int(s))
        try: f.set_variation_by_axes([w])
        except Exception: pass
        _F[k] = f
    return _F[k]

# ---------- paper ----------
def make_paper():
    r = np.random.default_rng(54)
    g = cv2.GaussianBlur(r.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 1.2)
    lo = cv2.resize(r.normal(0, 1, (H // 60, W // 60)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    fib = cv2.GaussianBlur(r.normal(0, 1, (H, W)).astype(np.float32), (0, 0), sigmaX=6, sigmaY=0.8)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = 1 - 0.06 * np.clip(((xx - W / 2) / (W * 0.7)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2, 0, 1)
    m = (1 + 0.018 * g + 0.008 * lo + 0.012 * fib) * vig
    return m.astype(np.float32)
PAPER = make_paper()[..., None]
# ink tooth: flat ink areas get a slight speckle (applied only where dark/colour)
INKN = cv2.GaussianBlur(np.random.default_rng(7).normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.9)[..., None]

def canvas(col=CRM):
    img = np.empty((H, W, 3), np.uint8); img[:] = col; return img

SH = 4; SC = 1 << SH
def P(p): return (int(round(p[0] * SC)), int(round(p[1] * SC)))
def circ(img, x, y, r, col, th=-1):
    if r <= 0: return
    cv2.circle(img, P((x, y)), int(r * SC), col, th if th < 0 else int(th), cv2.LINE_AA, SH)
def poly(img, pts, col):
    cv2.fillPoly(img, [np.array([P(p) for p in pts], np.int32)], col, cv2.LINE_AA, SH)
def pline(img, pts, col, th, closed=False):
    cv2.polylines(img, [np.array([P(p) for p in pts], np.int32)], closed, col, int(th), cv2.LINE_AA, SH)
def line(img, a, b, col, th):
    cv2.line(img, P(a), P(b), col, int(th), cv2.LINE_AA, SH)
def rect(img, x0, y0, x1, y1, col):
    poly(img, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], col)
def hexa(img, x, y, r, col, th=-1, rot=0):
    pts = [(x + r * math.cos(math.radians(60 * k + 30 + rot)), y + r * math.sin(math.radians(60 * k + 30 + rot))) for k in range(6)]
    if th < 0: poly(img, pts, col)
    else: pline(img, pts, col, th, True)
def dashed(img, pts, col, th, dash=26, gap=18, prog=1.0):
    pts = np.array(pts, np.float32)
    if len(pts) < 2: return
    cum = np.concatenate([[0], np.cumsum(np.sqrt(((pts[1:] - pts[:-1]) ** 2).sum(1)))])
    tot = cum[-1] * prog
    def at(d):
        return np.stack([np.interp(d, cum, pts[:, 0]), np.interp(d, cum, pts[:, 1])], 1)
    d0 = 0.0
    while d0 < tot:
        d1 = min(d0 + dash, tot)
        inner = cum[(cum > d0) & (cum < d1)]
        ds = np.concatenate([[d0], inner, [d1]])
        pline(img, at(ds), col, th)
        d0 += dash + gap
def arc_pts(cx, cy, r, a0, a1, n=60):
    """angles in our convention: degrees, 0 = up, clockwise positive."""
    return [(cx + r * math.sin(math.radians(a)), cy - r * math.cos(math.radians(a))) for a in np.linspace(a0, a1, n)]
def wedge(img, cx, cy, r, a0, a1, col):
    if abs(a1 - a0) < 0.3: return
    poly(img, [(cx, cy)] + arc_pts(cx, cy, r, a0, a1), col)

# ---------- type ----------
_TM = {}
def tmask(s, size, w=700, track=0):
    k = (s, int(size), w, track)
    if k not in _TM:
        f = F(size, w)
        if track:
            tw = sum(f.getlength(c) for c in s) + track * (len(s) - 1)
        else:
            tw = f.getlength(s)
        asc, desc = f.getmetrics()
        im = Image.new("L", (int(tw) + 8, asc + desc + 8), 0); d = ImageDraw.Draw(im)
        if track:
            x = 4
            for c in s: d.text((x, 4), c, font=f, fill=255); x += f.getlength(c) + track
        else:
            d.text((4, 4), s, font=f, fill=255)
        m = np.asarray(im).astype(np.float32) / 255
        ys = np.where(m.max(1) > 0.02)[0]
        cap = f.getbbox("H")[1] + 4
        off = max(ys[0] - 2, 0) if len(ys) else 0
        m = m[off: ys[-1] + 3] if len(ys) else m
        _TM[k] = (m, off - cap)
    return _TM[k]

def blend(img, m, x0, y0, col, a=1.0):
    h, w = m.shape; x0, y0 = int(round(x0)), int(round(y0))
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if xa >= xb or ya >= yb: return
    mm = m[ya - y0: yb - y0, xa - x0: xb - x0, None] * a
    reg = img[ya:yb, xa:xb].astype(np.float32)
    img[ya:yb, xa:xb] = (reg * (1 - mm) + np.array(col, np.float32) * mm).astype(np.uint8)

def txt(img, s, size, x, y, col, anchor="c", prog=1.0, w=700, track=0, rot=0, slide=(0, 0), a=1.0):
    """anchor c: x = centre; l: x = left edge; r: right edge. y = top of cap height. prog: slide/fade-in."""
    if prog <= 0: return 0
    m, yoff = tmask(s, size, w, track)
    if not rot: y = y + yoff
    if rot: m = np.ascontiguousarray(np.rot90(m, 1 if rot > 0 else -1))
    h, wd = m.shape
    if anchor == "c": x0 = x - wd / 2
    elif anchor == "r": x0 = x - wd
    else: x0 = x
    u = back(min(1, prog), 1.6)
    x0 += slide[0] * (1 - u); y0 = y + slide[1] * (1 - u)
    blend(img, m, x0, y0, col, a * min(1, prog * 2.5))
    return wd

# ---------- the bee ----------
def make_bee(open_w):
    S2 = 2; Wd, Hd = 360 * S2, 420 * S2
    rgb = np.zeros((Hd, Wd, 3), np.uint8); al = np.zeros((Hd, Wd), np.uint8)
    cx, cy = Wd // 2, Hd // 2
    def both(fn, *a, col):
        fn(rgb, *a, col); fn(al, *a, 255)
    def C(x, y, r, col, th=-1):
        circ(rgb, cx + x * S2, cy + y * S2, r * S2, col, th if th < 0 else th * S2)
        circ(al, cx + x * S2, cy + y * S2, r * S2, 255, th if th < 0 else th * S2)
    # wings (behind)
    wr = 62 if open_w else 52; wx = 66 if open_w else 44; wy = -46 if open_w else -20
    for sg in (-1, 1):
        C(sg * wx, wy, wr + 7, BLK); C(sg * wx, wy, wr, CRM)
    # abdomen: yellow disc with two black bands, clipped, + stinger triangle
    ab = np.zeros((Hd, Wd), np.uint8); circ(ab, cx, cy + 62 * S2, 74 * S2, 255)
    poly(rgb, [(cx - 16 * S2, cy + 128 * S2), (cx + 16 * S2, cy + 128 * S2), (cx, cy + 160 * S2)], BLK)
    poly(al, [(cx - 16 * S2, cy + 128 * S2), (cx + 16 * S2, cy + 128 * S2), (cx, cy + 160 * S2)], 255)
    abm = ab > 0
    band = np.zeros((Hd, Wd), bool)
    for y0, y1 in ((34, 56), (82, 104)):
        band[cy + y0 * S2: cy + y1 * S2] = True
    rgb[abm] = YEL; rgb[abm & band] = BLK
    al[:] = np.maximum(al, ab)
    # thorax + head + antennae
    C(0, -22, 46, BLK)
    for sg in (-1, 1):
        line(rgb, (cx + sg * 10 * S2, cy - 96 * S2), (cx + sg * 40 * S2, cy - 150 * S2), BLK, 7 * S2)
        line(al, (cx + sg * 10 * S2, cy - 96 * S2), (cx + sg * 40 * S2, cy - 150 * S2), 255, 7 * S2)
        C(sg * 40, -152, 9, BLK)
    C(0, -86, 30, RED)
    rgba = np.dstack([rgb, al]).astype(np.float32)
    rgba[..., :3] *= rgba[..., 3:] / 255
    return rgba, (cx, cy)
BEES = [make_bee(True), make_bee(False)]

def bee(img, x, y, ang, k=1.0, t=0.0, flap=True):
    spr, (cx, cy) = BEES[int(t * 24) % 2 if flap else 0]
    kk = k / 2
    R = int(260 * k) + 4
    x0, y0 = int(x) - R, int(y) - R
    M = cv2.getRotationMatrix2D((cx, cy), -ang, kk)
    M[0, 2] += x - x0 - cx; M[1, 2] += y - y0 - cy
    out = cv2.warpAffine(spr, M, (2 * R, 2 * R), flags=cv2.INTER_AREA if kk < 0.7 else cv2.INTER_LINEAR, borderValue=0)
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + 2 * R, W), min(y0 + 2 * R, H)
    if xa >= xb or ya >= yb: return
    o = out[ya - y0: yb - y0, xa - x0: xb - x0]
    a = o[..., 3:] / 255
    reg = img[ya:yb, xa:xb].astype(np.float32)
    img[ya:yb, xa:xb] = np.clip(reg * (1 - a) + o[..., :3], 0, 255).astype(np.uint8)

def vec(a): return math.sin(math.radians(a)), -math.cos(math.radians(a))
def heading(vx, vy): return math.degrees(math.atan2(vx, -vy))

def dance_path(cx, cy, ang, L):
    dx, dy = vec(ang); px, py = vec(ang + 90)
    s = (cx - dx * L / 2, cy - dy * L / 2); e = (cx + dx * L / 2, cy + dy * L / 2)
    arcs = []
    for sg in (1, -1):
        arcs.append([(cx + dx * L / 2 * math.cos(th) + px * sg * L / 2 * math.sin(th) * 0.9,
                      cy + dy * L / 2 * math.cos(th) + py * sg * L / 2 * math.sin(th) * 0.9) for th in np.linspace(0, math.pi, 50)])
    return s, e, arcs

def draw_path(img, cx, cy, ang, L, col, th=16, thin=7, prog=1.0):
    s, e, arcs = dance_path(cx, cy, ang, L)
    u = min(1, prog * 2)
    if u > 0:
        line(img, s, (s[0] + (e[0] - s[0]) * u, s[1] + (e[1] - s[1]) * u), col, th)
        # waggle zig marks along the run
    v = max(0, prog * 2 - 1)
    if v > 0:
        for a in arcs:
            n = max(2, int(len(a) * v)); dashed(img, a[:n], col, thin, 18, 14)
        # arrow head at end of run
    if prog >= 1:
        dx, dy = vec(ang); px, py = vec(ang + 90)
        tip = (e[0] + dx * 34, e[1] + dy * 34)
        poly(img, [tip, (e[0] + px * 24, e[1] + py * 24), (e[0] - px * 24, e[1] - py * 24)], col)

def dance_bee(img, cx, cy, ang, L, t, k=0.6, period=2.4, wag=0.56, t0=0.0):
    """Bee tracing a figure-eight: waggle run (fast side-to-side), then return loop alternating sides."""
    tt = (t + t0) % (2 * period); side = 1 if tt < period else -1; u = (tt % period) / period
    dx, dy = vec(ang); px, py = vec(ang + 90)
    if u < wag:
        q = u / wag
        sx, sy = cx - dx * L / 2, cy - dy * L / 2
        wob = math.sin(2 * math.pi * 6.0 * (t + t0))
        x = sx + dx * L * q + px * wob * 14 * k / 0.6
        y = sy + dy * L * q + py * wob * 14 * k / 0.6
        bee(img, x, y, ang + 22 * wob, k, t)
        return True
    th = math.pi * ease((u - wag) / (1 - wag))
    x = cx + dx * L / 2 * math.cos(th) + px * side * L / 2 * math.sin(th) * 0.9
    y = cy + dy * L / 2 * math.cos(th) + py * side * L / 2 * math.sin(th) * 0.9
    vx = -dx * math.sin(th) + px * side * math.cos(th) * 0.9; vy = -dy * math.sin(th) + py * side * math.cos(th) * 0.9
    bee(img, x, y, heading(vx, vy), k, t)
    return False

# ---------- props ----------
def flower(img, x, y, r, t, stem=True):
    if stem: line(img, (x, y), (x, y + r * 3.2), BLK, max(6, r * 0.16))
    rot = t * 30
    for k in range(6):
        a = rot + 60 * k
        dx, dy = vec(a); px, py = vec(a + 90)
        b = (x + dx * r * 0.9, y + dy * r * 0.9)
        poly(img, [(b[0] + px * r * 0.55, b[1] + py * r * 0.55), (b[0] - px * r * 0.55, b[1] - py * r * 0.55), (x + dx * r * 2.0, y + dy * r * 2.0)], RED)
    circ(img, x, y, r, BLU)
    circ(img, x, y, r * 0.38, YEL)

def hive(img, x, y, r):
    hexa(img, x, y, r + 8, BLK); hexa(img, x, y, r, YEL)
    for k in (-1, 0, 1):
        line(img, (x - r * 0.75, y + k * r * 0.34), (x + r * 0.75, y + k * r * 0.34), BLK, max(4, r * 0.07))
    circ(img, x, y + r * 0.55, r * 0.2, BLK)

def sun(img, x, y, r, t=0.0, rays=False):
    if rays:
        for k in range(12):
            a = k * 30 + t * 12
            dx, dy = vec(a)
            line(img, (x + dx * (r + 18), y + dy * (r + 18)), (x + dx * (r + 52), y + dy * (r + 52)), RED, 10)
    circ(img, x, y, r, RED)

_CACHE = {}
def cached(k, fn):
    if k not in _CACHE: _CACHE[k] = fn()
    return _CACHE[k]

def comb_tex():
    img = canvas(BLK)
    r = 62; dx = r * math.sqrt(3); dy = r * 1.5
    for j in range(-1, int(H / dy) + 2):
        for i in range(-1, int(W / dx) + 2):
            x = i * dx + (dx / 2 if j % 2 else 0); y = j * dy
            hexa(img, x, y, r - 4, (52, 44, 30), 5)
    return img

def wstart(ln, k):
    if isinstance(k, str):
        k = next(j for j in range(ln["_w1"] - ln["_w0"]) if words[ln["_w0"] + j][0].lower().strip(".,?!:") == k)
    i = min(ln["_w0"] + k, ln["_w1"] - 1); return words[i][1] - ln["_s"]

def label(img, s, x, y, col=BLK, size=34, prog=1.0, anchor="l", rot=0):
    return txt(img, s, size, x, y, col, anchor, prog, 600, track=8, rot=rot, slide=(0, 30))

def num_tag(img, n, x, y, col, bg, prog=1.0):
    if prog <= 0: return
    r = 34 * back(min(1, prog), 2.0)
    circ(img, x, y, r, bg); txt(img, str(n), 44, x, y - 18, col)

# ---------- scenes ----------
def hook(ln, lt, dur, t):
    img = canvas()
    sun(img, 880, 330, 230)
    rect(img, 0, 1180, 1080, 1500, BLU)
    circ(img, 120, 1180, 150, YEL)
    rect(img, 60, 108, 360, 122, BLK)
    label(img, "FIG. 1  —  THE WAGGLE DANCE", 60, 140)
    txt(img, "bees give", 150, 540, 300, BLK)
    txt(img, "directions", 150, 540, 470, BLK)
    txt(img, "by dancing.", 150, 540, 640, BLU)
    draw_path(img, 560, 1030, 32, 460, BLK, 18, 8)
    dance_bee(img, 560, 1030, 32, 460, lt, 0.74, t0=0.15)
    label(img, "APIS MELLIFERA", 1020, 1250, CRM, 32, anchor="r")
    return img

def why(ln, lt, dur, t):
    img = canvas(BLU)
    circ(img, 900, 260, 120, YEL); txt(img, "?", 150, 900, 205, BLK)
    txt(img, "the whole map", 118, 70, 470, CRM, "l", eout(lt / 0.3), slide=(-200, 0))
    o = txt(img, "is in one ", 118, 70, 610, CRM, "l", eout((lt - 0.1) / 0.3), slide=(-200, 0))
    txt(img, "wiggle.", 118, 70 + o, 610, YEL, "l", eout((lt - 0.25) / 0.3), slide=(0, -120))
    draw_path(img, 540, 1110, 0, 420, CRM, 18, 8, prog=eout(lt / 0.9))
    if lt > 0.3: dance_bee(img, 540, 1110, 0, 420, lt - 0.3, 0.6)
    gw = wstart(ln, "wait")
    if lt > gw - 0.1:
        u = back(min(1, (lt - gw + 0.1) / 0.35), 1.6)
        poly(img, [(60, 760 - 0), (60 + 520 * u, 760), (60 + 520 * u, 850), (60, 850)], RED)
        if u > 0.6: label(img, "WAIT FOR THE END  →", 90, 788, CRM, 36)
    return img

def forage(ln, lt, dur, t):
    img = canvas()
    gh = wstart(ln, "flies"); gd = wstart(ln, "dances")
    # step header row
    for i, (s, g) in enumerate((("find", 0.0), ("fly home", gh), ("dance", gd))):
        x = 90 + i * 330
        num_tag(img, i + 1, x, 190, CRM, (BLU, YEL, RED)[i] if lt >= g - 0.1 else GRY, prog=eout((lt - i * 0.1) / 0.3))
        txt(img, s, 56, x + 50, 168, BLK if lt >= g - 0.1 else (150, 144, 136), "l", eout((lt - i * 0.1) / 0.3), slide=(0, 40))
    rect(img, 60, 270, 1020, 280, BLK)
    flower(img, 230, 560, 62, t)
    hive(img, 820, 1190, 120)
    pts = [(230 + (820 - 230) * s, 560 + (1190 - 560) * s - 260 * math.sin(math.pi * s)) for s in np.linspace(0, 1, 60)]
    dashed(img, pts, BLK, 8, 24, 18, prog=1.0)
    if lt < gh: bee(img, 300, 640, 140 + 10 * math.sin(lt * 6), 0.5, t)
    else:
        q = ease((lt - gh) / max(0.4, gd - gh - 0.1))
        i = min(58, int(q * 59)); a = pts[i]; b = pts[i + 1]
        bee(img, a[0], a[1], heading(b[0] - a[0], b[1] - a[1]), 0.5, t)
    # dark hive panel rises at "dances"
    if lt > gd - 0.15:
        u = eout((lt - gd + 0.15) / 0.45)
        top = 1500 - (1500 - 300) * u
        comb = cached("comb", comb_tex)
        img[int(top):1500] = comb[int(top):1500]
        rect(img, 0, top, 1080, top + 12, YEL)
        if u > 0.5:
            lt2 = lt - gd
            draw_path(img, 540, 920, 0, 380, YEL, 16, 7, prog=eout(lt2 / 0.6))
            dance_bee(img, 540, 920, 0, 380, lt2, 0.58)
            label(img, "INSIDE THE DARK HIVE", 70, top + 50, CRM, 34, prog=eout(lt2 / 0.3))
            label(img, "VERTICAL COMB", 1010, top + 50, YEL, 34, anchor="r", prog=eout((lt2 - 0.1) / 0.3))
    return img

def up(ln, lt, dur, t):
    img = canvas()
    comb = cached("comb", comb_tex)
    split = 540 * eout(lt / 0.35)
    img[:1500, :int(split)] = comb[:1500, :int(split)]
    sun(img, 810, 330, 130, t, rays=True)
    txt(img, "sun", 64, 810, 300, CRM)
    hive(img, 810, 1300, 90)
    dashed(img, [(810, 1190), (810, 500)], BLK, 9, 26, 18, prog=eout((lt - 0.2) / 0.8))
    q = ease(min(1, max(0, (lt - 0.3) / 1.6)))
    bee(img, 810, 1170 - (1170 - 560) * q, 0, 0.42, t)
    if split > 400:
        draw_path(img, 270, 920, 0, 400, YEL, 16, 7, prog=eout(lt / 0.5))
        dance_bee(img, 270, 920, 0, 400, lt, 0.5)
        txt(img, "up", 150, 270, 240, CRM, prog=eout((lt - 0.15) / 0.3), slide=(0, -80))
        label(img, "ON THE COMB", 270, 420, YEL, 32, anchor="c", prog=eout((lt - 0.2) / 0.3))
    label(img, "IN THE FIELD", 810, 1420, BLK, 32, anchor="c", prog=eout((lt - 0.3) / 0.3))
    # equals sign on the seam
    u = back(min(1, max(0, (lt - 0.35) / 0.35)), 2.0)
    if u > 0:
        circ(img, 540, 330, 70 * u, YEL)
        rect(img, 540 - 34 * u, 310, 540 + 34 * u, 322, BLK); rect(img, 540 - 34 * u, 338, 540 + 34 * u, 350, BLK)
    return img

def angle(ln, lt, dur, t):
    img = canvas()
    deg = ln["scene"].get("deg", 40)
    a = deg * eout(max(0, lt - 0.3) / 0.8)
    comb = cached("comb", comb_tex)
    img[110:760] = comb[110:760]
    # comb: vertical reference + tilted dance
    cx, cy = 540, 470
    dashed(img, [(cx, cy + 250), (cx, cy - 280)], CRM, 6, 20, 14)
    wedge(img, cx, cy, 230, 0, a, YEL)
    circ(img, cx, cy, 12, CRM)
    draw_path(img, cx, cy, a, 380, CRM, 14, 6)
    dance_bee(img, cx, cy, a, 380, lt, 0.48)
    vertical = label
    vertical(img, "COMB", 40, 150, YEL, 34, rot=1)
    txt(img, f"{int(round(a))}°", 110, cx + 150, cy - 300, YEL, "l")
    label(img, "UP", cx - 16, cy - 330, CRM, 30, anchor="r")
    # field
    fx, fy = 540, 1430
    sun(img, fx, 900, 70, t)
    line(img, (fx, fy), (fx, 990), BLK, 6)
    wedge(img, fx, fy, 300, 0, a, YEL)
    dx, dy = vec(a)
    line(img, (fx, fy), (fx + dx * 500, fy + dy * 500), BLK, 10)
    flower(img, fx + dx * 520, fy + dy * 520, 34, t, stem=False)
    hive(img, fx, fy, 50)
    label(img, "FIELD", 40, 830, BLK, 34, rot=1)
    txt(img, f"{int(round(a))}°", 100, fx + 60, 1080, BLK, "l", prog=eout((lt - 0.3) / 0.3))
    label(img, "SUN", fx - 96, 880, BLK, 30, anchor="r")
    return img

def distance(ln, lt, dur, t):
    img = canvas(YEL)
    ga = wstart(ln, "about")
    if lt < ga:
        txt(img, "longer waggle", 104, 70, 150, BLK, "l", eout(lt / 0.3), slide=(-200, 0))
        o = txt(img, "= ", 104, 70, 280, BLK, "l", eout((lt - 0.15) / 0.3), slide=(-200, 0))
        txt(img, "farther food", 104, 70 + o, 280, RED, "l", eout((lt - 0.2) / 0.3), slide=(-200, 0))
        g0 = wstart(ln, "longer")
        for i, L in enumerate((170, 340, 520)):
            y = 560 + i * 360
            st = g0 - 0.3 + i * 0.45
            u = eout((lt - st) / 0.5)
            if u <= 0: continue
            label(img, ("NEAR", "FAR", "FARTHER")[i], 90, y - 90, BLK, 32, prog=u)
            rect(img, 90, y - 16, 90 + L * u, y + 16, BLK)
            if u > 0.6:
                q = ((lt - st) * 0.8) % 1
                wob = math.sin(2 * math.pi * 6 * lt)
                bee(img, 90 + L * q, y + wob * 8, 90 + 20 * wob, 0.3, t)
            D = 90 + L * 1.65 * u
            dashed(img, [(90, y + 70), (D, y + 70)], BLU, 8, 22, 14)
            hive(img, 90, y + 70, 26)
            flower(img, D, y + 70, 24, t, stem=False)
        return img
    lt2 = lt - ga
    img[:] = CRM
    txt(img, "about", 80, 540, 170, BLK, prog=eout(lt2 / 0.25))
    # stopwatch
    cx, cy, r = 300, 560, 190
    q = min(1, max(0, (lt2 - 0.2) / 1.2))
    circ(img, cx, cy, r + 16, BLK); circ(img, cx, cy, r, CRM)
    rect(img, cx - 24, cy - r - 52, cx + 24, cy - r - 14, BLK)
    wedge(img, cx, cy, r - 18, 0, 360 * q, RED)
    txt(img, f"{q:.1f} s", 84, cx, cy + r + 50, BLK)
    txt(img, "≈", 140, 690, 470, BLK, prog=eout((lt2 - 0.3) / 0.3))
    # distance counter
    km = q
    txt(img, f"{km:.1f}", 170, 900, 440, RED, prog=eout((lt2 - 0.4) / 0.3))
    txt(img, "km", 70, 900, 640, BLK, prog=eout((lt2 - 0.5) / 0.3))
    # waggle bee + track
    y = 1040
    rect(img, 90, y - 14, 90 + 900 * q, y + 14, BLK)
    wob = math.sin(2 * math.pi * 6 * lt2)
    bee(img, 90 + 900 * q, y + wob * 10, 90 + 22 * wob, 0.42, t)
    label(img, "WAGGLE RUN", 90, y - 110, BLK, 32)
    yb = 1340
    hive(img, 110, yb, 60)
    dashed(img, [(180, yb), (180 + 760 * q, yb)], BLU, 10, 26, 16)
    flower(img, 940, yb, 44, t, stem=False)
    label(img, "≈ 1 KM TO THE FLOWERS", 990, yb - 150, BLU, 32, anchor="r", prog=eout((lt2 - 1.3) / 0.3))
    return img

def nobel(ln, lt, dur, t):
    img = canvas(BLK)
    # grid of decoded dance glyphs
    angs = [-60, -20, 0, 35, 80, 140, -110, 170]
    for i, a0 in enumerate(angs):
        gx = 160 + (i % 4) * 253; gy = 1200 + (i // 4) * 200
        u = back(min(1, max(0, (lt - 0.2 - i * 0.08) / 0.35)), 1.8)
        if u <= 0: continue
        col = (YEL, RED, BLU, CRM)[i % 4]
        a = a0 + 90 * (1 - u)
        draw_path(img, gx, gy, a, 120 * u, col, 10, 5)
    # medal
    u = back(min(1, max(0, (lt - 0.8) / 0.4)), 1.8)
    if u > 0:
        circ(img, 790, 880, 190 * u, YEL)
        circ(img, 790, 880, 162 * u, BLK, 6)
        if u > 0.8:
            txt(img, "1973", 100, 790, 830, BLK)
            txt(img, "NOBEL PRIZE", 24, 790, 950, BLK, w=600, track=5)
    txt(img, "code", 130, 70, 260, CRM, "l", eout(lt / 0.3), slide=(-200, 0))
    txt(img, "cracked.", 130, 70, 410, RED, "l", eout((lt - 0.1) / 0.3), slide=(-200, 0))
    label(img, "KARL VON FRISCH", 70, 600, YEL, 36, prog=eout((lt - 0.3) / 0.3))
    label(img, "DECODED THE DANCE", 70, 660, CRM, 28, prog=eout((lt - 0.4) / 0.3))
    return img

def end(ln, lt, dur, t):
    img = canvas()
    cl = ln["scene"].get("click_at", 0.45)
    sun(img, 900, 250, 150)
    rect(img, 0, 1250, 1080, 1500, BLU)
    txt(img, "sounds fake?", 128, 540, 330, BLK)
    u = back(min(1, max(0, (lt - cl) / 0.4)), 1.3)
    txt(img, "it's true.", 150, 540, 500, RED, prog=eout((lt - cl - 0.2) / 0.3), slide=(0, -100))
    # pill track
    y = 880; x0, x1 = 230, 850; r = 74
    circ(img, x0, y, r + 10, BLK); circ(img, x1, y, r + 10, BLK); rect(img, x0, y - r - 10, x1, y + r + 10, BLK)
    kx = x0 + (x1 - x0) * u
    if u > 0:
        circ(img, x0, y, r - 6, BLU); rect(img, x0, y - r + 6, kx, y + r - 6, BLU)
    label(img, "FAKE", x0 - 40, y + 120, BLK, 46, anchor="c", prog=1)
    if lt < cl + 0.2: rect(img, x0 - 120, y + 140, x0 + 40, y + 148, RED)
    txt(img, "TRUE", 46, x1, y + 120, BLU if u > 0.8 else (150, 144, 136), w=600, track=8)
    # knob = the bee's striped abdomen, rotated so stripes run vertical
    circ(img, kx, y, r - 10, YEL)
    for dxs in (-26, 18):
        poly(img, [(kx + dxs + sx, y + math.sqrt(max(0, (r - 10) ** 2 - (dxs + sx) ** 2)) * sg) for sx, sg in ((0, -1), (16, -1), (16, 1), (0, 1))], BLK)
    txt(img, "follow for more", 72, 540, 1330, CRM, prog=eout((lt - 0.9) / 0.4), slide=(0, 60))
    bee(img, 160, 1180, 70 + 10 * math.sin(lt * 5), 0.4, t)
    return img

SCENES = {"hook": hook, "why": why, "forage": forage, "up": up, "angle": angle, "distance": distance, "nobel": nobel, "end": end}

# ---------- narration + music ----------
voice, words, total = narrate(spec, lead=0.08)
n = len(voice); music = np.zeros(n, np.float32)

def marimba(f, dur=0.6, amp=1.0):
    s = np.arange(int(dur * SR)) / SR
    sig = np.sin(2 * np.pi * f * s) * np.exp(-s * 7) + 0.25 * np.sin(2 * np.pi * f * 3.93 * s) * np.exp(-s * 30) + 0.1 * np.sin(2 * np.pi * f * 9.2 * s) * np.exp(-s * 60)
    return (amp * sig * np.clip(s / 0.002, 0, 1)).astype(np.float32)
def block(at, gain=0.06, f=1800):
    s = np.arange(int(0.05 * SR)) / SR
    place(music, at, (np.sin(2 * np.pi * f * s) * np.exp(-s * 140)).astype(np.float32), gain)
def bass(f, dur=0.45):
    s = np.arange(int(dur * SR)) / SR
    sig = np.sin(2 * np.pi * f * s) + 0.3 * np.sin(2 * np.pi * 2 * f * s)
    return (sig * np.exp(-s * 6) * np.clip(s / 0.004, 0, 1)).astype(np.float32)
def buzz(at, dur, gain=0.03, f=260):
    s = np.arange(int(dur * SR)) / SR
    saw = 2 * ((f * s + 0.1 * np.sin(2 * np.pi * 7 * s)) % 1) - 1
    saw = np.convolve(saw, np.ones(5) / 5, mode="same")
    env = (0.6 + 0.4 * np.sin(2 * np.pi * 26 * s)) * np.clip(s / 0.05, 0, 1) * np.clip((dur - s) / 0.08, 0, 1)
    place(music, at, (saw * env).astype(np.float32), gain)

C4 = 261.63
def nt(semi): return C4 * 2 ** (semi / 12)
CH = [[0, 4, 7, 12], [-3, 0, 4, 9], [-7, -3, 0, 5], [-5, -1, 2, 7]]     # C Am F G
BASS = [-24, -27, -31, -29]
BEAT = 0.5
for k in range(int(total / (BEAT / 2)) + 1):
    bar = (k // 8) % 4; st = k % 8; ch = CH[bar]
    at = k * BEAT / 2
    pat = [0, 2, 1, 3, 2, 1, 3, 2][st]
    if st not in (3, 7): place(music, at, marimba(nt(ch[pat] + 12), 0.5), 0.07)
    if st in (0, 4): place(music, at, bass(nt(BASS[bar])), 0.16)
    if st in (2, 6): block(at, 0.05)
hook_hit(music, 0.3); buzz(0.05, 1.1, 0.04)
for i, ln in enumerate(spec["lines"]):
    s0 = ln["_s"]; st = ln["scene"]["type"]
    if i > 0: whoosh(music, s0 - 0.12, 0.08, 0.4); block(s0, 0.1, 900)
    if st in ("why", "up"): buzz(s0 + 0.4, 1.0, 0.025)
    if st == "distance":
        ga = ln["_s"] + wstart(ln, "about")
        buzz(ga + 0.2, 1.2, 0.035)
        place(music, ga + 1.45, marimba(nt(19), 0.9), 0.1)
    if st == "nobel":
        for j, sm in enumerate((12, 16, 19, 24)): place(music, s0 + 0.8 + j * 0.07, marimba(nt(sm), 0.8), 0.08)
    if st == "end":
        c = s0 + ln["scene"].get("click_at", 0.45)
        block(c, 0.14, 1200)
        for j, sm in enumerate((12, 16, 19, 24, 28)): place(music, c + 0.25 + j * 0.07, marimba(nt(sm), 0.9), 0.09)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.45)

# ---------- compositing ----------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 74
    f = F(size)
    while f.getlength(" ".join(ws)) > W - 240 and size > 44: size -= 4; f = F(size)
    gap = f.getlength(" ") + 14
    tw_ = sum(f.getlength(w) for w in ws) + gap * (len(ws) - 1); x = (W - tw_) / 2; y = 1588
    rect(img, x - 44 + 10, y - 30 + 10, x + tw_ + 44 + 10, y + size + 26 + 10, RED)
    rect(img, x - 44, y - 30, x + tw_ + 44, y + size + 26, BLK)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]; wl = f.getlength(w)
        if on: rect(img, x - 10, y - 12, x + wl + 10, y + size + 8, YEL)
        txt(img, w, size, x, y - size * 0.02, BLK if on else CRM, "l")
        x += wl + gap

def finish(img):
    f = img.astype(np.float32) * PAPER
    dark = 1 - f.mean(2, keepdims=True) / 255
    f = f * (1 + 0.05 * INKN * dark)
    return f

def scene_img(t, ln):
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    return SCENES[ln["scene"]["type"]](ln, lt, dur, t)

YYg, XXg = np.mgrid[0:H, 0:W].astype(np.float32)
_DF = {}
def dfield(ox, oy):
    if (ox, oy) not in _DF: _DF[(ox, oy)] = np.sqrt((XXg - ox) ** 2 + (YYg - oy) ** 2)
    return _DF[(ox, oy)]
ORIG = [(540, 760), (900, 300), (180, 1300), (540, 200), (880, 1200), (200, 400), (540, 900)]
RINGS = [RED, YEL, BLU]
def frame(t, fi):
    lines = spec["lines"]; ln = active_line(spec, t) or lines[0]; i = lines.index(ln)
    img = scene_img(t, ln)
    if i > 0:
        ph = (t - (ln["_s"] - 0.12)) / 0.42
        if ph < 1:
            old = scene_img(ln["_s"] - 0.12, lines[i - 1])
            if i % 2 == 1:   # circle iris with a primary ring
                D_ = dfield(*ORIG[i % len(ORIG)]); r = 2300 * eout(ph)
                m = (D_ < r)[..., None]
                ring = ((D_ >= r) & (D_ < r + 46))[..., None]
                img = np.where(m, img, np.where(ring, np.array(RINGS[i % 3], np.uint8), old))
            else:            # red / yellow / blue bar sweep
                bw = 150; p = eout(ph) * (W + 3 * bw)
                xs = np.arange(W)
                out = old.copy()
                out[:, xs < p - 3 * bw] = img[:, xs < p - 3 * bw]
                for k, c in enumerate((BLU, YEL, RED)):
                    sel = (xs >= p - (3 - k) * bw) & (xs < p - (2 - k) * bw)
                    out[:, sel] = c
                img = out
    if t > total - 0.45:
        a = ease((t - (total - 0.45)) / 0.45)
        img = (img * (1 - a) + scene_img(lines[0]["_s"], lines[0]) * a).astype(np.uint8)
    caption(img, t)
    rect(img, 30, H - 16, W - 30, H - 8, (200, 192, 176))
    pw = (W - 60) * t / total
    if pw > 1:
        rect(img, 30, H - 16, 30 + pw, H - 8, BLK)
        rect(img, 30 + pw - 8, H - 22, 30 + pw + 8, H - 2, RED)
    return np.clip(finish(img), 0, 255).astype(np.uint8).tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), int(float(tt_) * FPS))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=22); print(f"done {total:.1f}s")
