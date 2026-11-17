"""Day 46 — MOTION STUDY style (hummingbirds can fly backwards).
An 1880s chronophotographic plate in the manner of the early motion-study pioneers: a cream mount card with paper fibres,
sequences of small sepia albumen prints laid out in a numbered grid, each print a gridded backdrop (the measuring screen)
with vignetting, toning blotches, and 12 fps film grain. The subject is a flat dark hummingbird silhouette whose wing is
re-posed in every frame (figure-eight wing-tip path, ghosted strobe exposures), visiting a trumpet flower.
Annotations are hand-inked in oxblood (arrows, circles, a figure-eight trace with arrowheads, leader lines).
Type: IM Fell English (roman / italic / small caps) for plate titles and numbers; Playfair Display Black for captions on
an umber label. Motion language: shutters firing cell by cell, push-ins from a grid cell to a full plate, magnesium-flash
cuts. One inverted (dark) plate for the multiple-exposure wing fan, like a single-plate chronophotograph.
Ending: a sliding plate-holder switch FAKE → TRUE whose knob is a hummingbird medallion; the last half second returns to
the hook plate for the loop.
Music: music-box waltz in G (bell partials), soft bowed drone, zoetrope/shutter ticks, a low wing hum in the beat scene.
Usage: python3 engine/styles/day46_motionstudy.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
_F = {}
def F(kind, s):
    k = (kind, int(s))
    if k not in _F:
        if kind == "cap":
            f = ImageFont.truetype(f"{FONTS}/PlayfairDisplay.ttf", int(s)); f.set_variation_by_axes([900]); _F[k] = f
        else:
            _F[k] = ImageFont.truetype(f"{FONTS}/" + {"rm": "IMFeENrm28P", "it": "IMFeENit28P", "sc": "IMFeENsc28P"}[kind] + ".ttf", int(s))
    return _F[k]

CARD = (234, 223, 198)
INK = (44, 30, 20)           # umber ink / silhouette
SEPIA = (112, 84, 56)
OX = (150, 38, 30)           # oxblood annotation ink
PALE = (214, 196, 160)

# ---------- static textures ----------
def fbm(seed, scales, amps, size):
    rr = np.random.default_rng(seed); acc = np.zeros((size[1], size[0]), np.float32)
    for s, a in zip(scales, amps):
        g = rr.random((max(2, int(size[1] / s) + 2), max(2, int(size[0] / s) + 2))).astype(np.float32)
        acc += a * cv2.resize(g, size, interpolation=cv2.INTER_CUBIC)
    acc -= acc.min(); return acc / max(1e-6, acc.max())
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_vig = 1 - 0.10 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
CARD_BG = np.array(CARD, np.float32)[None, None] * _vig[..., None]
CARD_BG += ((fbm(4, [300, 90, 20], [1, .5, .3], (W, H)) - 0.5) * 12)[..., None]
_fib = np.random.default_rng(5)
for _ in range(900):                                       # paper fibres
    x, y = _fib.uniform(0, W), _fib.uniform(0, H); L = _fib.uniform(6, 26); an = _fib.uniform(0, math.pi)
    cv2.line(CARD_BG, (int(x), int(y)), (int(x + L * math.cos(an)), int(y + L * math.sin(an))), (205, 192, 165), 1, cv2.LINE_AA)
for _ in range(60):                                        # foxing specks
    x, y = _fib.uniform(0, W), _fib.uniform(0, H)
    cv2.circle(CARD_BG, (int(x), int(y)), int(_fib.uniform(1, 4)), (196, 168, 128), -1, cv2.LINE_AA)
CARD_BG = CARD_BG.clip(0, 255)
GRAIN = [np.random.default_rng(10 + i).normal(0, 1, (H, W)).astype(np.float32) for i in range(4)]
GRAIN = [cv2.GaussianBlur(g, (0, 0), 0.7) * 9 for g in GRAIN]
_TONE = fbm(7, [200, 60], [1, .5], (1200, 1200))

_CELL = {}
def cell_tex(w, h, dark=False):
    """sepia print of the measuring backdrop (grid lines scale with the cell height)."""
    k = (w, h, dark)
    if k in _CELL: return _CELL[k]
    v, u = np.mgrid[0:h, 0:w].astype(np.float32)
    r = ((u - w / 2) / (w / 2)) ** 2 + ((v - h / 2) / (h / 2)) ** 2
    vg = np.clip(1 - 0.32 * r ** 1.3, 0, 1)
    tone = cv2.resize(_TONE, (w, h))
    if dark:
        base = np.array([40, 30, 22], np.float32)[None, None] * (0.7 + 0.5 * vg[..., None]) + (tone[..., None] - .5) * 10
        line_c = np.array([92, 74, 54], np.float32)
    else:
        base = np.array([222, 204, 168], np.float32)[None, None] * (0.55 + 0.45 * vg[..., None]) + (tone[..., None] - .5) * 18
        line_c = np.array([136, 108, 76], np.float32)
    img = base.copy()
    step = h / 5.0
    m = np.zeros((h, w), np.float32)
    gx = w / 2 - step * math.floor(w / 2 / step)
    for i in range(int(w / step) + 2):
        x = gx + i * step; cv2.line(m, (int(x), 0), (int(x), h), 1.0, max(1, int(h / 220)), cv2.LINE_AA)
    for j in range(6):
        y = j * step; cv2.line(m, (0, int(y)), (w, int(y)), 1.0, max(1, int(h / 220)), cv2.LINE_AA)
    al = (0.55 * m * vg)[..., None]
    img = img * (1 - al) + line_c * al
    _CELL[k] = img.clip(0, 255).astype(np.uint8); return _CELL[k]

# ---------- drawing helpers ----------
def P(pts): return (np.array(pts, np.float32).reshape(-1, 1, 2) * 8).astype(np.int32)
def _box(pts, pad):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return max(0, int(min(xs) - pad)), max(0, int(min(ys) - pad)), min(W, int(max(xs) + pad + 1)), min(H, int(max(ys) + pad + 1))
def fill(a, pts, col, al=1.0):
    if al <= 0.01 or len(pts) < 3: return
    if al >= 0.99: cv2.fillPoly(a, [P(pts)], col, cv2.LINE_AA, shift=3); return
    x0, y0, x1, y1 = _box(pts, 2)
    if x1 <= x0 or y1 <= y0: return
    reg = a[y0:y1, x0:x1]; tmp = reg.copy()
    cv2.fillPoly(tmp, [P([(x - x0, y - y0) for x, y in pts])], col, cv2.LINE_AA, shift=3)
    a[y0:y1, x0:x1] = (reg * (1 - al) + tmp * al).astype(np.uint8)
def line(a, pts, col, w=3, closed=False, al=1.0):
    if al <= 0.01 or len(pts) < 2: return
    if al >= 0.99: cv2.polylines(a, [P(pts)], closed, col, max(1, int(w)), cv2.LINE_AA, shift=3); return
    x0, y0, x1, y1 = _box(pts, w + 2)
    if x1 <= x0 or y1 <= y0: return
    reg = a[y0:y1, x0:x1]; tmp = reg.copy()
    cv2.polylines(tmp, [P([(x - x0, y - y0) for x, y in pts])], closed, col, max(1, int(w)), cv2.LINE_AA, shift=3)
    a[y0:y1, x0:x1] = (reg * (1 - al) + tmp * al).astype(np.uint8)
def ellipse_pts(cx, cy, rx, ry, rot=0.0, n=40):
    c, s = math.cos(rot), math.sin(rot)
    return [(cx + rx * math.cos(2 * math.pi * k / n) * c - ry * math.sin(2 * math.pi * k / n) * s,
             cy + rx * math.cos(2 * math.pi * k / n) * s + ry * math.sin(2 * math.pi * k / n) * c) for k in range(n)]
def wobble(pts, amp=2.0, seed=0):
    r = random.Random(seed); return [(x + amp * math.sin(i * 0.7 + seed) + r.uniform(-amp, amp) * 0.3, y + amp * math.cos(i * 0.9 + seed)) for i, (x, y) in enumerate(pts)]
def ink(a, pts, w=6, prog=1.0, al=1.0, col=OX, seed=1):
    """hand-inked stroke, drawn progressively."""
    if prog <= 0 or len(pts) < 2: return []
    n = max(2, int(len(pts) * min(1, prog))); p = wobble(pts[:n], 1.6, seed)
    line(a, p, col, w, False, al); return p
def arrowhead(a, p, q, col=OX, size=26, w=6, al=1.0):
    ang = math.atan2(q[1] - p[1], q[0] - p[0])
    for d in (2.6, -2.6):
        line(a, [q, (q[0] + size * math.cos(ang + d), q[1] + size * math.sin(ang + d))], col, w, False, al)
def curve(p0, p1, bend=0.0, n=40):
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2; dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    c = (mx - dy * bend, my + dx * bend)
    return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * c[0] + u * u * p1[0], (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * c[1] + u * u * p1[1]) for u in np.linspace(0, 1, n)]

TXT = []
def text(s, kind, size, cx, cy, col=INK, al=1.0, track=0.0, anchor="m"):
    if al > 0.01: TXT.append((s, kind, size, cx, cy, col, al, track, anchor))
def tw(s, kind, size, track=0.0):
    f = F(kind, size); return sum(f.getlength(c) for c in s) + track * size * (len(s) - 1)
def fit(s, kind, size, track=0.0, maxw=W - 140):
    while tw(s, kind, size, track) > maxw and size > 30: size -= 2
    return size
def draw_texts(img):
    d = ImageDraw.Draw(img, "RGBA")
    for s, kind, size, cx, cy, col, al, track, anchor in TXT:
        f = F(kind, size); wdt = tw(s, kind, size, track)
        x = cx - wdt / 2 if anchor == "m" else (cx if anchor == "l" else cx - wdt)
        if track == 0: d.text((x, cy), s, font=f, fill=col + (int(255 * al),), anchor="lm"); continue
        for c in s:
            d.text((x, cy), c, font=f, fill=col + (int(255 * al),), anchor="lm"); x += f.getlength(c) + track * size
    TXT.clear()

def fade(lt, at, d=0.3): return ease((lt - at) / d)
def wt_(ln, i): return words[min(ln["_w0"] + i, ln["_w1"] - 1)][1] - ln["_s"]

# ---------- the bird ----------
BODY = ellipse_pts(0, 0, 0.56, 0.21, 0.0, 36)
HEAD = ellipse_pts(0.56, -0.13, 0.2, 0.19, 0.0, 28)
BEAK = [(0.7, -0.19), (1.5, -0.1), (1.5, -0.085), (0.72, -0.07)]
TAIL = [(-0.36, -0.08), (-0.98, -0.26), (-1.08, -0.06), (-1.02, 0.12), (-0.9, 0.2), (-0.36, 0.13)]
GORGET = ellipse_pts(0.42, 0.02, 0.17, 0.1, 0.4, 20)
SHOULDER = (0.12, -0.17)
def xf(pts, cx, cy, s, pitch, face):
    c, si = math.cos(pitch), math.sin(pitch); out = []
    for x, y in pts:
        X, Y = x * c - y * si, x * si + y * c
        out.append((cx + face * X * s, cy + Y * s))
    return out
def wing_tip(phase):
    """wing-tip offset from the shoulder in screen units (before facing): a sideways figure eight."""
    return (1.05 * math.sin(phase), -0.7 + 0.32 * math.sin(2 * phase))
def wing_poly(cx, cy, s, pitch, face, phase):
    S = xf([SHOULDER], cx, cy, s, pitch, face)[0]
    tx, ty = wing_tip(phase); T = (S[0] + face * tx * s, S[1] + ty * s)
    dx, dy = T[0] - S[0], T[1] - S[1]; L = math.hypot(dx, dy) + 1e-6; nx, ny = -dy / L, dx / L
    wd = 0.24 * s
    return [S, (S[0] + dx * 0.3 + nx * wd, S[1] + dy * 0.3 + ny * wd), (S[0] + dx * 0.75 + nx * wd * 0.6, S[1] + dy * 0.75 + ny * wd * 0.6),
            T, (S[0] + dx * 0.6 - nx * wd * 0.25, S[1] + dy * 0.6 - ny * wd * 0.25)], S, T
def bird(a, cx, cy, s, phase, face=1, pitch=-0.55, col=INK, al=1.0, ghosts=2, wing_col=None, eye=True):
    wc = wing_col or tuple(int(c * 0.8 + 40) for c in col)
    for g in range(ghosts, 0, -1):                          # strobe ghosts of the beating wing
        for sg in (-1, 1):
            wp, _, _ = wing_poly(cx, cy, s, pitch, face, phase + sg * 0.38 * g)
            fill(a, wp, wc, al * (0.2 / g))
    for part in (TAIL, BODY, HEAD, BEAK): fill(a, xf(part, cx, cy, s, pitch, face), col, al)
    fill(a, xf(GORGET, cx, cy, s, pitch, face), tuple(min(255, c + 22) for c in col), al * 0.7)
    wp, S, T = wing_poly(cx, cy, s, pitch, face, phase)
    fill(a, wp, wc, al * 0.9)
    if eye:
        e = xf([(0.62, -0.18)], cx, cy, s, pitch, face)[0]
        cv2.circle(a, (int(e[0]), int(e[1])), max(1, int(s * 0.04)), (200, 182, 150), -1, cv2.LINE_AA)
    return S, T
def beak_tip(cx, cy, s, pitch, face): return xf([(1.5, -0.095)], cx, cy, s, pitch, face)[0]
def flower(a, mx, my, s, col=(78, 58, 40), al=1.0, face=-1):
    """trumpet flower whose mouth is at (mx,my), opening toward `face` (-1 = left)."""
    L = 0.9 * s
    tube = [(mx, my - 0.32 * s), (mx - face * L * 0.25, my - 0.12 * s), (mx - face * L, my - 0.06 * s),
            (mx - face * L, my + 0.06 * s), (mx - face * L * 0.25, my + 0.12 * s), (mx, my + 0.32 * s), (mx + face * 0.06 * s, my)]
    fill(a, tube, col, al)
    base = (mx - face * L, my)
    stem = curve(base, (base[0] - face * 0.1 * s, my + 3.5 * s), -0.15, 20)
    line(a, stem, col, max(2, int(s * 0.07)), False, al)
    lf = stem[11]; fill(a, [lf, (lf[0] - face * 0.7 * s, lf[1] - 0.35 * s), (lf[0] - face * 0.3 * s, lf[1] + 0.1 * s)], col, al)

def plate(a, x, y, w, h, draw_fn, num=None, al=1.0, dark=False, bright=0.0, border=True):
    """one sepia print: backdrop + content (clipped) + border + number below."""
    x, y, w, h = int(x), int(y), int(w), int(h)
    if w < 8 or h < 8: return
    tex = cell_tex(w, h, dark).copy()
    draw_fn(tex, w, h)
    if bright > 0: tex = (tex.astype(np.float32) + (255 - tex) * 0.22 * bright).astype(np.uint8)
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    src = tex[y0 - y:y1 - y, x0 - x:x1 - x]
    if al >= 0.99: a[y0:y1, x0:x1] = src
    else: a[y0:y1, x0:x1] = (a[y0:y1, x0:x1] * (1 - al) + src * al).astype(np.uint8)
    if border: line(a, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], (60, 44, 30), 2, True, al)
    if num is not None: text(str(num), "sc", max(26, int(h * 0.13)), x + w / 2, y + h + max(20, h * 0.09), SEPIA, al)

# ---------- scenes ----------
HOOK_CELLS = [(60 + c * 326, 540 + r * 290, 308, 232) for r in range(3) for c in range(3)]
def hook_cell(k, t, speed=2.2):
    def fn(tex, w, h):
        s = h * 0.19; mx, my = w * 0.84, h * 0.46
        flower(tex, mx, my, s)
        pitch = -0.5; cx0 = mx - (beak_tip(0, 0, s, pitch, 1)[0]) - 4
        cx = cx0 - k * w * 0.05; cy = my - beak_tip(0, 0, s, pitch, 1)[1] + 6 + 3 * math.sin(k * 0.8)
        bird(tex, cx, cy, s, k * 1.15 + t * speed, 1, pitch)
    return fn

def S_hook(a, sc, ln, lt, dur, t, al=1.0):
    text("ANIMAL LOCOMOTION  ·  PLATE 46", "sc", 36, W / 2, 96, SEPIA, al, 0.12)
    line(a, [(150, 128), (930, 128)], SEPIA, 2, False, al)
    text("This bird can fly", "rm", 118, W / 2, 255, INK, al)
    text("in reverse.", "it", 168, W / 2, 410, OX, al)
    fire = int(t * 12) % 12
    for k, (x, y, w, h) in enumerate(HOOK_CELLS):
        plate(a, x, y, w, h, hook_cell(k, t), k + 1, al, bright=1.0 if k == fire else 0.0)
    y = 1478; pts = curve((930, y), (170, y), 0.04, 50)
    ink(a, pts, 7, 1.0, al, seed=3); arrowhead(a, pts[-6], pts[-1], al=al)
    text("tail first", "it", 50, W / 2, y - 42, OX, al)

def S_loop(a, sc, ln, lt, dur, t):
    u = eout(lt / 0.55)
    x0, y0, w0, h0 = HOOK_CELLS[4]; X, Y, Wd, Hd = 60, 470, 960, 723
    x, y, w, h = x0 + (X - x0) * u, y0 + (Y - y0) * u, w0 + (Wd - w0) * u, h0 + (Hd - h0) * u
    k = 4
    def fn(tex, w_, h_):
        hook_cell(k, t, speed=2.2 + 6 * u)(tex, w_, h_)
    plate(a, x, y, w, h, fn, None)
    if u > 0.9:
        text("No. 5  ·  enlarged", "it", 40, W / 2, Y + Hd + 46, SEPIA, fade(lt, 0.5))
        # annotate the wing: oxblood ink ellipse around the wing region
        s = Hd * 0.15; mx, my = Wd * 0.8, Hd * 0.44; pitch = -0.5
        bt = beak_tip(0, 0, s, pitch, 1); cx = mx - bt[0] - 4 - k * Wd * 0.052; cy = my - bt[1] + 6 + 3 * math.sin(k * 0.8)
        S = xf([SHOULDER], cx, cy, s, pitch, 1)[0]
        e = ellipse_pts(X + S[0] + 5, Y + S[1] - 0.5 * s, 1.35 * s, 0.85 * s, -0.15, 60) + ellipse_pts(X + S[0] + 5, Y + S[1] - 0.5 * s, 1.35 * s, 0.85 * s, -0.15, 60)[:8]
        ink(a, e, 8, (lt - 0.75) / 0.6, 1, seed=5)
        q = fade(lt, 1.3, 0.3)
        text("?", "it", 120, X + S[0] + 1.9 * s, Y + S[1] - 1.6 * s, OX, q)
    text("The secret is hiding", "rm", 104, W / 2, 205, INK, fade(lt, 0.0, 0.2))
    text("in its wings.", "it", 140, W / 2, 340, OX, fade(lt, wt_(ln, 5) - 0.1, 0.25))

DIRS = [("FORWARD", (1, 0)), ("BACKWARD", (-1, 0)), ("UP", (0, -1)), ("DOWN", (0, 1))]
def S_dirs(a, sc, ln, lt, dur, t):
    text("In any direction", "it", 112, W / 2, 205, INK, 1)
    ats = [wt_(ln, 1) - 0.15, wt_(ln, 2) - 0.15, wt_(ln, 7) - 0.15, wt_(ln, 9) - 0.15]
    cw, ch, gap = 228, 168, 16
    for r, (name, (dx, dy)) in enumerate(DIRS):
        ap = fade(lt, ats[r], 0.25)
        if ap <= 0: continue
        y = 360 + r * 280 + (1 - ap) * 30
        text(name, "sc", 48, 64, y - 5, INK, ap, 0.14, anchor="l")
        lx = 64 + tw(name, "sc", 48, 0.14) + 30
        p0 = (lx, y - 5); p1 = (lx + 120 * (1 if dx >= 0 else 1), y - 5)
        if dx: pts = curve((lx + (0 if dx > 0 else 120), y - 4), (lx + (120 if dx > 0 else 0), y - 4), 0.05, 20)
        else: pts = curve((lx + 60, y - 4 - 30 * dy), (lx + 60, y - 4 + 30 * dy), 0.05, 20)
        ink(a, pts, 6, (lt - ats[r]) / 0.3, ap, seed=r);
        if lt - ats[r] > 0.3: arrowhead(a, pts[-4], pts[-1], size=20, w=6, al=ap)
        for c in range(4):
            def fn(tex, w, h, c=c, dx=dx, dy=dy):
                s = h * 0.14; mx, my = w * 0.84, h * 0.42
                flower(tex, mx, my, s)
                bt = beak_tip(0, 0, s, -0.5, 1)
                if dx > 0: cx = mx - bt[0] - 4 - (3 - c) * w * 0.12; cy = my - bt[1] + 5
                elif dx < 0: cx = mx - bt[0] - 4 - c * w * 0.12; cy = my - bt[1] + 5
                else:
                    cx = mx - bt[0] - 18; cy = h * 0.5 + dy * (c - 1.5) * h * 0.14
                bird(tex, cx, cy, s, c * 1.3 + t * 2.4 + r, 1, -0.5)
            plate(a, 64 + c * (cw + gap), y + 34, cw, ch, fn, None, ap, bright=1.0 if int(t * 12) % 4 == c else 0)

def S_hover(a, sc, ln, lt, dur, t):
    text("HOVER", "sc", 190, W / 2, 215, INK, 1, 0.18)
    text("unlike any other bird", "it", 58, W / 2, 345, OX, fade(lt, 0.05, 0.25))
    cw, ch = 466, 330; xs = (60, 554); ys = (450, 870)
    eye_y = None
    for k in range(4):
        x, y = xs[k % 2], ys[k // 2]
        ap = fade(lt, 0.08 * k, 0.25)
        def fn(tex, w, h, k=k):
            s = h * 0.17; mx, my = w * 0.82, h * 0.43
            flower(tex, mx, my, s)
            bt = beak_tip(0, 0, s, -0.5, 1); cx = mx - bt[0] - 4; cy = my - bt[1] + 6
            bird(tex, cx, cy, s, k * 1.5 + t * 2.0, 1, -0.5)
        plate(a, x, y, cw, ch, fn, None, ap, bright=1.0 if int(t * 12) % 4 == k else 0)
        text(f"·{(k * 3 + 3):02d} sec", "it", 36, x + cw / 2, y + ch + 30, SEPIA, ap)
    # oxblood level lines: the head never moves
    s = ch * 0.17; bt = beak_tip(0, 0, s, -0.5, 1); ey = ch * 0.43 - bt[1] + 6 + xf([(0.62, -0.18)], 0, 0, s, -0.5, 1)[0][1]
    pr = (lt - 0.6) / 0.7
    for row in range(2):
        yl = ys[row] + ey
        pts = [(40 + i * 25, yl) for i in range(41)]
        n = max(0, min(41, int(41 * pr)))
        for i in range(0, n - 1, 2): line(a, [pts[i], pts[i + 1]], OX, 4)
    if pr > 1: text("the head stays at the same height", "it", 50, W / 2, ys[1] + 330 + 100, OX, fade(lt, 1.35, 0.3))

def S_beats(a, sc, ln, lt, dur, t):
    at = wt_(ln, 5) - 0.1
    u = ease((lt - at) / 0.9)
    n = int(round(80 * u))
    text(str(n), "rm", 300, W / 2, 250, OX, 1)
    text("WING BEATS A SECOND", "sc", 56, W / 2, 445, INK, 1, 0.12)
    text("in the smallest species", "it", 42, W / 2, 510, SEPIA, fade(lt, at + 0.6, 0.3))
    X, Y, Wd, Hd = 60, 590, 960, 860
    def fn(tex, w, h):
        s = h * 0.2; cx, cy = w * 0.45, h * 0.55
        nexp = 1 + int(min(13, (lt / max(0.1, dur - 0.3)) * 18))
        for e in range(nexp):                               # multiple exposure fan of the wing
            ph = -math.pi / 2 + e * (2 * math.pi / 14)
            wp, _, _ = wing_poly(cx, cy, s, -0.55, 1, ph)
            fill(tex, wp, (226, 210, 178), 0.32)
            line(tex, wp, (236, 222, 192), 2, True, 0.5)
        bird(tex, cx, cy, s, t * 30, 1, -0.55, col=(232, 216, 186), ghosts=0, wing_col=(240, 228, 200), eye=False)
        e = xf([(0.62, -0.18)], cx, cy, s, -0.55, 1)[0]
        cv2.circle(tex, (int(e[0]), int(e[1])), max(2, int(s * 0.045)), (40, 30, 22), -1, cv2.LINE_AA)
    plate(a, X, Y, Wd, Hd, fn, None, dark=True)
    text("single plate · 14 exposures", "it", 38, W / 2, Y + Hd + 40, SEPIA, 1)

def S_secret(a, sc, ln, lt, dur, t):
    text("A figure 8", "it", 170, W / 2, 230, OX, 1)
    X, Y, Wd, Hd = 60, 380, 960, 1000
    s = Hd * 0.16; cx, cy = Wd * 0.42, Hd * 0.6; pitch = -0.6
    ph = t * 3.2
    def fn(tex, w, h):
        bt = beak_tip(cx, cy, s, pitch, 1); flower(tex, bt[0] + 8, bt[1], s)
        bird(tex, cx, cy, s, ph, 1, pitch, ghosts=1)
    plate(a, X, Y, Wd, Hd, fn, None)
    S = xf([SHOULDER], cx, cy, s, pitch, 1)[0]; S = (S[0] + X, S[1] + Y)
    path = [(S[0] + wing_tip(p)[0] * s, S[1] + wing_tip(p)[1] * s) for p in np.linspace(0, 2 * math.pi, 120)]
    pr = (lt - 0.3) / 1.6
    p = ink(a, path, 7, pr, 1, seed=8)
    if pr > 0.3: arrowhead(a, path[30], path[33], size=22)
    if pr > 0.85: arrowhead(a, path[90], path[93], size=22)
    sa = fade(lt, wt_(ln, 4) - 0.1, 0.3)                    # shoulder pivot
    if sa > 0:
        cv2.circle(a, (int(S[0]), int(S[1])), 14, OX, 5, cv2.LINE_AA)
        lp = curve((S[0] - 12, S[1] - 12), (S[0] - 250, S[1] - 250), -0.2, 30)
        ink(a, lp, 4, sa, 1, seed=2)
        text("shoulder", "it", 58, S[0] - 270, S[1] - 345, OX, sa)
        text("swivels", "it", 58, S[0] - 270, S[1] - 290, OX, sa)
    text("fig. 1 — the wing tip's path", "it", 38, W / 2, Y + Hd + 40, SEPIA, 1)

def S_end(a, sc, ln, lt, dur, t):
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.4)
    text("Sounds fake?", "it", 150, W / 2, 250, INK, 1)
    y = 520; x0, x1, hh = 170, 910, 150
    cv2.rectangle(a, (x0, int(y - hh / 2)), (x1, int(y + hh / 2)), (214, 198, 166), -1)   # plate-holder slot
    for i in range(1, 12):
        xi = x0 + i * (x1 - x0) / 12; line(a, [(xi, y + hh / 2 - 18), (xi, y + hh / 2)], SEPIA, 2)
    kx = x0 + hh / 2 + (x1 - x0 - hh) * on
    if on > 0: cv2.rectangle(a, (x0, int(y - hh / 2)), (int(kx), int(y + hh / 2)), OX, -1)
    line(a, [(x0, y - hh / 2), (x1, y - hh / 2), (x1, y + hh / 2), (x0, y + hh / 2)], INK, 5, True)
    text("FAKE", "sc", 70, (x0 + x1) / 2 + 70, y, SEPIA, max(0, 1 - on * 2.5), 0.16)
    text("TRUE", "sc", 70, (x0 + x1) / 2 - 70, y, CARD, ease((on - 0.5) / 0.4), 0.16)
    cv2.circle(a, (int(kx), int(y)), int(hh / 2 + 6), CARD, -1, cv2.LINE_AA)            # medallion knob
    cv2.circle(a, (int(kx), int(y)), int(hh / 2 + 6), INK, 5, cv2.LINE_AA)
    cv2.circle(a, (int(kx), int(y)), int(hh / 2 - 8), SEPIA, 2, cv2.LINE_AA)
    bird(a, kx - 14, y + 12, 34, t * 6 + on * 8, 1, -0.5, ghosts=1)
    text("IT'S TRUE.", "sc", fit("IT'S TRUE.", "sc", 190, 0.06), W / 2, 800, OX, fade(lt, click + 0.3, 0.3), 0.06)
    text("Follow for more.", "it", 84, W / 2, 960, INK, fade(lt, click + 0.6, 0.3))
    for j, k in enumerate((0, 4, 8)):
        x, y2, w, h = HOOK_CELLS[j]; plate(a, x, 1110, w, h, hook_cell(k, t), k + 1, fade(lt, 0.1 * j, 0.3), bright=1.0 if int(t * 12) % 3 == j else 0)

SCENES = dict(hook=S_hook, loop=S_loop, dirs=S_dirs, hover=S_hover, beats=S_beats, secret=S_secret, end=S_end)

# ---------- audio ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
rng = np.random.default_rng(46)
def mbox(f, gain=0.05, dur=1.6):
    s = np.arange(int(dur * SR)) / SR
    sig = np.sin(2 * np.pi * f * s) + 0.35 * np.sin(2 * np.pi * f * 3.01 * s) * np.exp(-s * 6) + 0.15 * np.sin(2 * np.pi * f * 5.2 * s) * np.exp(-s * 12)
    return (sig * np.exp(-s * 3.0) * np.minimum(1, s / 0.002)).astype(np.float32) * gain
BEAT = 60 / 138
G = {"G": [392.0, 493.88, 587.33, 783.99], "C": [523.25, 659.25, 783.99, 1046.5], "D": [587.33, 739.99, 880.0, 1174.66], "Em": [493.88, 659.25, 783.99, 987.77]}
BASS = {"G": 98.0, "C": 130.81, "D": 146.83, "Em": 164.81}
PROG = ["G", "Em", "C", "D"]
bar = 3 * BEAT
for b in range(int(total / bar) + 1):
    ch = PROG[b % 4]; t0 = b * bar
    s = np.arange(int(bar * 1.2 * SR)) / SR
    drone = (np.sin(2 * np.pi * BASS[ch] * s) + 0.4 * np.sin(2 * np.pi * BASS[ch] * 2 * s) + 0.2 * np.sin(2 * np.pi * BASS[ch] * 3 * s))
    place(music, t0, (drone * np.minimum(1, s / 0.25) * np.exp(-s * 0.9) * 0.05).astype(np.float32))
    notes = G[ch]; pat = [0, 2, 1, 3, 2, 1]
    for k in range(6): place(music, t0 + k * BEAT / 2, mbox(notes[pat[k]] * (2 if k == 3 else 1) / (1 if k != 3 else 2), 0.04))
tt = np.arange(n) / SR
tick = np.zeros(n, np.float32)
cl = (rng.normal(0, 1, int(0.006 * SR)) * np.exp(-np.arange(int(0.006 * SR)) / SR * 900)).astype(np.float32)
for k in range(int(total * 12)): place(tick, k / 12, cl, 1.0)
music += tick * 0.06
hook_hit(music, 0.32); place(music, 0.0, mbox(1567.98, 0.08))
def clack(at, gain=0.2):
    s = np.arange(int(0.08 * SR)) / SR
    place(music, at, (rng.normal(0, 1, len(s)) * np.exp(-s * 70) + np.sin(2 * np.pi * 180 * s) * np.exp(-s * 40)).astype(np.float32), gain)
for i, ln in enumerate(spec["lines"]):
    st = ln["scene"]["type"]
    if i > 0: clack(ln["_s"]); whoosh(music, ln["_s"], 0.06)
    if st == "beats":
        a0, a1 = ln["_s"], ln["_se"]; m = (tt >= a0) & (tt < a1)
        hum = np.sin(2 * np.pi * 80 * tt) * (0.6 + 0.4 * np.sin(2 * np.pi * 40 * tt)) + 0.3 * np.sin(2 * np.pi * 160 * tt)
        env = np.clip((tt - a0) / 0.4, 0, 1) * np.clip((a1 - tt) / 0.3, 0, 1)
        music += (hum * env * m * 0.05).astype(np.float32)
    if st == "end":
        c = ln["_s"] + ln["scene"].get("click_at", 0.45); clack(c, 0.3)
        for j, f in enumerate((783.99, 987.77, 1174.66, 1567.98)): place(music, c + 0.2 + j * 0.07, mbox(f, 0.07, 2.0))
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.4)

# ---------- compositing ----------
STARTS = [ln["_s"] for ln in spec["lines"]]
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 72
    f = F("cap", size)
    while f.getlength(" ".join(ws)) > W - 240 and size > 36: size -= 4; f = F("cap", size)
    tw_ = f.getlength(" ".join(ws)); x = (W - tw_) / 2; y = 1590
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([x - 44, y - 22, x + tw_ + 44, y + size + 30], fill=(40, 28, 20, 248))
    d.rectangle([x - 36, y - 14, x + tw_ + 36, y + size + 22], outline=(196, 170, 128, 255), width=2)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]; wl = f.getlength(w)
        if on: d.rectangle([x - 8, y - 2, x + wl + 8, y + size + 12], fill=OX + (255,))
        d.text((x, y - size * 0.04), w, font=f, fill=(248, 238, 216, 255)); x += f.getlength(w + " ")

def scene_frame(t):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    a = CARD_BG.astype(np.uint8)
    SCENES[ln["scene"]["type"]](a, ln["scene"], ln, lt, dur, t)
    img = Image.fromarray(a); draw_texts(img)
    end = spec["lines"][-1]
    lp = ease((t - (total - 0.42)) / 0.34)
    if lp > 0 and ln is end:                                # loop: dissolve back into the hook plate
        b = CARD_BG.astype(np.uint8); S_hook(b, {}, spec["lines"][0], 0, 1, t); hb = Image.fromarray(b); draw_texts(hb)
        img = Image.blend(img, hb, lp)
    return img

def frame(t, fi):
    img = scene_frame(t)
    arr = np.asarray(img).astype(np.float32)
    fl = 1 + 0.018 * math.sin(int(t * 12) * 2.3)              # exposure flicker at 12 fps
    arr = arr * fl + GRAIN[int(t * 12) % 4][..., None]
    gk = 0.0
    for s in STARTS[1:]:                                    # magnesium flash on cuts
        if s - 0.05 <= t < s + 0.22: gk = max(gk, 1 - abs(t - s) / (0.05 if t < s else 0.22))
    if gk > 0.02: arr = arr + (np.array([255, 246, 225], np.float32) - arr) * 0.7 * gk
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    caption(img, t)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 8, W, H], fill=(200, 184, 152)); d.rectangle([0, H - 8, int(W * t / total), H], fill=OX)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=26); print(f"done {total:.1f}s")
