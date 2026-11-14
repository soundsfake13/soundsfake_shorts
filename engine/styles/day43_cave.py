"""Day 43 — CAVE PAINTING style (woolly mammoths were still alive when the Great Pyramid was built).
The whole video is a torch-lit cave wall. A procedural limestone wall (fractal relief, hill-shaded bumps, cracks and
mineral stains) is lit by one flickering torch that drifts across it; everything else is pigment soaked into the rock:
red ochre, yellow ochre, charcoal and white kaolin. Figures are painted stroke by stroke with bristly brush strokes
(Catmull-Rom paths, jittered sub-bristles), fills soak in as washes, and every pigment pixel is broken up by the rock
grain. Hand stencils (sprayed ochre around a hand silhouette), tally marks and dot fields are the graphic vocabulary.
Titles in Caveat Brush, painted on with a ragged wipe. Scene changes = the torch dips and flares (with a whoosh).
Ending: a painted stone slider FAKE -> TRUE whose knob is a hand stencil.
Music: cave wind + bone-flute pentatonic + log drum + rattle.
Usage: python3 engine/styles/day43_cave.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
INTER = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter")
_F = {}
def F(kind, s):
    k = (kind, int(s))
    if k not in _F:
        if kind == "brush": _F[k] = ImageFont.truetype(f"{FONTS}/CaveatBrush-Regular.ttf", int(s))
        else: _F[k] = ImageFont.truetype(f"{INTER}/InterDisplay-Bold.otf", int(s))
    return _F[k]

RED, YEL, CHAR, KAO = (190, 56, 26), (246, 184, 66), (26, 18, 14), (242, 230, 206)

# ---------- the wall (built once) ----------
def fbm(seed, scales, amps, size=(W, H)):
    rr = np.random.default_rng(seed); acc = np.zeros((size[1], size[0]), np.float32)
    for s, a in zip(scales, amps):
        g = rr.random((max(2, size[1] // s + 2), max(2, size[0] // s + 2))).astype(np.float32)
        acc += a * np.asarray(Image.fromarray(g, "F").resize(size, Image.BICUBIC))
    acc -= acc.min(); return acc / max(1e-6, acc.max())

def _wall():
    h = fbm(1, [480, 240, 120, 60, 24, 10, 4], [1.0, 0.7, 0.45, 0.25, 0.12, 0.06, 0.03])
    gy, gx = np.gradient(h * 140)
    shade = np.clip(1.0 + (-gx * 0.6 - gy * 0.8) * 0.45, 0.7, 1.3)
    tone_ = fbm(2, [700, 300, 90, 30], [1, 0.6, 0.3, 0.15])
    stain = fbm(3, [500, 160, 50], [1, 0.5, 0.2])
    light, dark = np.array([150, 116, 86], np.float32), np.array([104, 76, 56], np.float32)
    col = dark + (light - dark) * tone_[..., None]
    col = col * (1 - 0.25 * np.clip(stain - 0.55, 0, 1)[..., None] * np.array([0, 0.6, 1.0]))      # reddish iron stains
    col *= shade[..., None]
    im = Image.fromarray(col.clip(0, 255).astype(np.uint8)); d = ImageDraw.Draw(im, "RGBA")
    rnd = random.Random(43)
    for _ in range(14):                                                        # cracks: dark line + light lip
        x, y = rnd.uniform(0, W), rnd.uniform(0, H); a = rnd.uniform(0, 6.28); pts = [(x, y)]
        for _ in range(rnd.randint(8, 22)):
            a += rnd.uniform(-0.6, 0.6); x += 22 * math.cos(a); y += 22 * math.sin(a); pts.append((x, y))
        d.line([(p[0] + 2, p[1] + 2) for p in pts], fill=(255, 235, 200, 40), width=3)
        d.line(pts, fill=(40, 26, 18, 120), width=rnd.choice([2, 3, 4]))
    im = im.filter(ImageFilter.GaussianBlur(0.7))
    return np.asarray(im).astype(np.float32), shade.astype(np.float32)
ROCK, SHADE = _wall()
GRAIN = (0.5 + 0.55 * fbm(7, [6, 3, 2, 1], [1, 0.8, 0.6, 0.5])).clip(0, 1)
GRAIN = np.where(np.random.default_rng(8).random((H, W)) < 0.03, 0.25, GRAIN).astype(np.float32)   # pits that skip pigment
PSHADE = (0.78 + 0.22 * np.clip(SHADE, 0.7, 1.3) / 1.3)[..., None].astype(np.float32)

yy_s, xx_s = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32) * 4
def lightmap(t, dip):
    fl = 1 + 0.07 * math.sin(13 * t) + 0.05 * math.sin(23.7 * t + 1) + 0.04 * math.sin(7.1 * t + 2)
    tx, ty = W * 0.5 + 170 * math.sin(0.45 * t), 820 + 130 * math.sin(0.31 * t + 1)
    r2 = ((xx_s - tx) ** 2 + (yy_s - ty) ** 2) / (1050 ** 2)
    L = (0.40 + 0.85 * fl * np.exp(-r2 * 1.6)) * dip
    L = np.asarray(Image.fromarray(L.astype(np.float32), "F").resize((W, H), Image.BILINEAR))
    return np.stack([L * 1.08, L * 0.98, L * 0.82], -1)

# ---------- painting helpers ----------
def spline(pts, n=8, closed=False):
    P = list(pts) + ([pts[0], pts[1], pts[2]] if closed else [])
    if not closed: P = [P[0]] + P + [P[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            s = k / n; s2, s3 = s * s, s * s * s
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * s + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * s2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * s3) for j in (0, 1)))
    out.append(P[-2]); return out

def partial(pts, u):
    if u >= 1: return pts
    if u <= 0 or len(pts) < 2: return []
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]; goal = sum(seg) * u; acc = 0; out = [pts[0]]
    for i, L in enumerate(seg):
        if acc + L >= goal:
            f = (goal - acc) / max(L, 1e-6); out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f)); break
        out.append(pts[i + 1]); acc += L
    return out

def brush(d, pts, u, col, w, seed=0, alpha=235):
    """bristly stroke: one body + jittered thinner bristles, drawn up to fraction u of its length."""
    p = partial(pts, u)
    if len(p) < 2: return
    d.line(p, fill=col + (alpha,), width=int(w), joint="curve")
    r = random.Random(seed)
    for b in range(3):
        o = r.uniform(-0.45, 0.45) * w
        q = [(x + o * 0.7 + r.uniform(-1.5, 1.5), y + o + r.uniform(-1.5, 1.5)) for x, y in p]
        d.line(q, fill=col + (int(alpha * 0.5),), width=max(2, int(w * 0.35)))
    for e in (p[0], p[-1]): d.ellipse([e[0] - w / 2, e[1] - w / 2, e[0] + w / 2, e[1] + w / 2], fill=col + (alpha,))

def tf(pts, cx, cy, s, flip=False):
    return [(cx + ((100 - x) if flip else x - 0) * s - 50 * s, cy + y * s - 44 * s) for x, y in pts]

MAM = [(4, 36), (14, 26), (28, 17), (42, 10), (54, 5), (62, 8), (66, 7), (71, 3), (78, 6), (83, 13), (86, 24), (87, 36),
       (87, 48), (88, 58), (93, 64), (95, 60), (91, 56), (84, 54), (81, 44), (79, 34), (75, 35), (73, 40), (73, 46),
       (73, 62), (74, 84), (65, 85), (64, 58), (55, 55), (45, 56), (35, 55), (33, 83), (24, 85), (22, 56), (12, 52), (6, 45)]
def mammoth(d, cx, cy, s, u=1.0, fill=1.0, flip=False, seed=0, col=RED):
    """cave mammoth, centred on (cx,cy), s = px per unit (~100 x 80 units). u: outline progress; fill: wash alpha."""
    body = spline(tf(MAM, cx, cy, s, flip), 6, closed=True)
    if fill > 0: d.polygon(body, fill=col + (int(200 * fill),))
    w = max(5, 2.2 * s)
    brush(d, body, ease(u / 0.75), CHAR, w, seed)
    v = ease((u - 0.6) / 0.4)
    if v > 0:
        brush(d, spline(tf([(76, 38), (85, 52), (97, 52), (103, 40)], cx, cy, s, flip), 8), v, KAO, w * 1.15, seed + 1)
        brush(d, spline(tf([(5, 40), (2, 46), (1, 52)], cx, cy, s, flip), 6), v, CHAR, w * 0.8, seed + 2)
        e = tf([(74, 14)], cx, cy, s, flip)[0]; r_ = w * 0.6 * v
        d.ellipse([e[0] - r_, e[1] - r_, e[0] + r_, e[1] + r_], fill=CHAR + (240,))
        for k, x in enumerate(range(28, 72, 6)):                              # hair fringe under the belly
            a, b = tf([(x, 55), (x - 1.5, 63)], cx, cy, s, flip)
            brush(d, [a, b], v, CHAR, w * 0.45, seed + 10 + k, 200)

def pyramid(d, cx, by, w, u=1.0, fill=1.0, seed=0):
    h = 0.62 * w; L, R_, A = (cx - w / 2, by), (cx + w / 2, by), (cx, by - h)
    if fill > 0: d.polygon([L, R_, A], fill=YEL + (int(215 * fill),))
    rows = 7
    for i in range(1, rows):
        y = by - h * i / rows; half = w / 2 * (1 - i / rows)
        vi = ease((u - 0.45 - 0.05 * i) / 0.25)
        if vi > 0: brush(d, [(cx - half, y), (cx + half, y)], vi, RED, max(4, w / 90), seed + i, 190)
        if vi > 0.5:
            for j in range(int(half * 2 / (w / 7)) + 1):
                x = cx - half + (j + 0.5 * (i % 2)) * (w / 7)
                if cx - half < x < cx + half: d.line([(x, y), (x, y + h / rows)], fill=RED + (150,), width=max(3, int(w / 140)))
    brush(d, [L, A, R_], ease(u / 0.5), CHAR, max(6, w / 55), seed)
    brush(d, [(L[0] - w * 0.08, by), (R_[0] + w * 0.08, by)], ease((u - 0.3) / 0.3), CHAR, max(6, w / 55), seed + 30)

def sun(d, cx, cy, r, u=1.0, t=0.0):
    if u <= 0: return
    d.ellipse([cx - r * u, cy - r * u, cx + r * u, cy + r * u], fill=RED + (225,))
    for k in range(12):
        a = k * math.pi / 6 + 0.1 * math.sin(t * 0.8); v = ease((u - k * 0.04) / 0.4)
        brush(d, [(cx + 1.35 * r * math.cos(a), cy + 1.35 * r * math.sin(a)), (cx + 1.85 * r * math.cos(a), cy + 1.85 * r * math.sin(a))], v, RED, r * 0.16, 70 + k)

def person(d, x, y, s, lean=0.25, u=1.0, seed=0, phase=0.0):
    """stick worker pulling to the left (leaning)."""
    hx, hy = x - lean * 40 * s, y - 70 * s
    sw = 10 * s * math.sin(phase)
    brush(d, [(x, y - 30 * s), (hx, hy + 12 * s)], u, CHAR, 8 * s, seed)
    brush(d, [(x, y - 30 * s), (x - 14 * s + sw, y)], u, CHAR, 7 * s, seed + 1)
    brush(d, [(x, y - 30 * s), (x + 12 * s - sw, y)], u, CHAR, 7 * s, seed + 2)
    brush(d, [(hx + 4 * s, hy + 26 * s), (hx - 30 * s, hy + 34 * s)], u, CHAR, 6 * s, seed + 3)
    if u > 0.5: d.ellipse([hx - 10 * s, hy - 10 * s, hx + 10 * s, hy + 10 * s], fill=CHAR + (235,))

def _hand(size=300):
    m = Image.new("L", (size, int(size * 1.25)), 0); d = ImageDraw.Draw(m); c = size / 2; py = size * 0.78
    d.ellipse([c - size * 0.22, py - size * 0.2, c + size * 0.22, py + size * 0.26], fill=255)
    for ang, L, wd in [(-0.95, 0.30, 0.085), (-0.32, 0.42, 0.08), (-0.08, 0.46, 0.08), (0.17, 0.42, 0.075), (0.42, 0.33, 0.065)]:
        bx, by_ = c + size * 0.2 * math.sin(ang * 1.4), py - size * 0.06
        ex, ey = bx + size * L * math.sin(ang), by_ - size * L * math.cos(ang)
        d.line([(bx, by_), (ex, ey)], fill=255, width=int(size * wd * 2)); r = size * wd
        d.ellipse([ex - r, ey - r, ex + r, ey + r], fill=255)
    d.rectangle([c - size * 0.17, py + size * 0.2, c + size * 0.17, m.size[1]], fill=255)
    halo = m.filter(ImageFilter.MaxFilter(31)).filter(ImageFilter.GaussianBlur(22))
    a = np.asarray(halo).astype(np.float32) - np.asarray(m).astype(np.float32) * 1.0
    sp = np.random.default_rng(5).random(a.shape) ** 0.5
    a = np.clip(a * 1.6 * sp, 0, 230)
    fade = np.clip((m.size[1] - np.arange(m.size[1])) / (size * 0.35), 0, 1)[:, None]
    return Image.fromarray((a * fade).astype(np.uint8))
HANDM = _hand()
_HS = {}
def hand(img, cx, cy, s, col=RED, a=1.0, rot=0):
    if a <= 0: return
    k = (int(s * 100), col, rot)
    if k not in _HS:
        m = HANDM.resize((int(HANDM.size[0] * s), int(HANDM.size[1] * s)), Image.LANCZOS).rotate(rot, expand=True, resample=Image.BICUBIC)
        sp = Image.new("RGBA", m.size, col + (0,)); sp.putalpha(m); _HS[k] = sp
    sp = _HS[k]
    if a < 1: sp = sp.copy(); sp.putalpha(sp.getchannel("A").point(lambda v: int(v * a)))
    img.alpha_composite(sp, (int(cx - sp.size[0] / 2), int(cy - sp.size[1] / 2)))

_TS = {}
def text(img, s, size, x, y, col=KAO, u=1.0, scale=1.0, kind="brush", outline=True):
    """painted title, centred; u = ragged left-to-right paint wipe."""
    if u <= 0: return
    k = (s, int(size), col, kind, outline)
    if k not in _TS:
        f = F(kind, size); bb = f.getbbox(s, stroke_width=8)
        sp = Image.new("RGBA", (bb[2] - bb[0] + 30, bb[3] - bb[1] + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(sp)
        d.text((15 - bb[0], 15 - bb[1]), s, font=f, fill=col + (255,), stroke_width=8 if outline else 0, stroke_fill=CHAR + (235,))
        _TS[k] = sp
    sp = _TS[k]
    if u < 1:
        w_, h_ = sp.size; cut = u * (w_ + 60) - 30
        ramp = np.clip((cut - np.arange(w_))[None, :] / 30 + np.random.default_rng(1).normal(0, 0.6, (h_, 1)), 0, 1)
        a = (np.asarray(sp.getchannel("A")).astype(np.float32) * ramp).astype(np.uint8)
        sp = sp.copy(); sp.putalpha(Image.fromarray(a))
    if abs(scale - 1) > 0.01: sp = sp.resize((max(1, int(sp.size[0] * scale)), max(1, int(sp.size[1] * scale))), Image.BILINEAR)
    img.alpha_composite(sp, (int(x - sp.size[0] / 2), int(y - sp.size[1] / 2)))

def fit(s, size, maxw=W - 140, kind="brush"):
    while F(kind, size).getlength(s) > maxw and size > 40: size -= 4
    return size

def slam(lt, at, d=0.28):
    u = (lt - at) / d
    return (0, 1) if u <= 0 else (1, 1 + 0.35 * (1 - back(min(1, u))) if u < 1 else 1)

def wt(ln, i): return words[ln["_w0"] + i][1] - ln["_s"]

# ---------- scenes ----------
def S_hook(img, sc, ln, lt, dur, t):
    d = ImageDraw.Draw(img, "RGBA")
    loop = sc.get("loop")
    hand(img, 150, 1380, 0.55, RED, 0.9, 15)
    pyramid(d, 830, 1300, 380, 1.0, 1.0, 3)
    sun(d, 950, 780, 40, 1.0, t)
    mammoth(d, 330, 1100, 5.6 + 0.05 * math.sin(t * 1.3), 1.0, 1.0, seed=4)
    if not loop:
        text(img, "MAMMOTHS", fit("MAMMOTHS", 230), W / 2, 250, YEL)
        text(img, "WERE ALIVE WHEN", 108, W / 2, 440, KAO)
        k = max(0.0, wt(ln, 5) - 0.1)                                          # "pyramids"
        text(img, "THESE WENT UP", 108, W / 2, 570, KAO)
        ax, ay = 800, 900
        brush(d, spline([(680, 640), (760, 740), (ax, ay)], 8), 1.0, KAO, 12, 9)
        brush(d, [(ax, ay), (ax - 36, ay - 34)], 1.0, KAO, 12, 10); brush(d, [(ax, ay), (ax + 18, ay - 44)], 1.0, KAO, 12, 11)
    else:
        a, s_ = slam(lt, 0.0)
        text(img, "HOW LONG", fit("HOW LONG", 200), W / 2, 290, YEL, scale=s_)
        a, s_ = slam(lt, 0.35)
        if a: text(img, "DID THEY LAST?", fit("DID THEY LAST?", 150), W / 2, 480, KAO, scale=s_)

def S_island(img, sc, ln, lt, dur, t):
    d = ImageDraw.Draw(img, "RGBA")
    text(img, "10,000", 200, W / 2, 230, YEL, u=ease(lt / 0.4))
    text(img, "YEARS AGO", 100, W / 2, 390, KAO, u=ease((lt - 0.2) / 0.4))
    cx, cy = W / 2, 1000
    isl = spline([(cx - 330, cy + 40), (cx - 260, cy - 110), (cx - 60, cy - 150), (cx + 150, cy - 120), (cx + 320, cy - 20),
                  (cx + 260, cy + 110), (cx + 30, cy + 150), (cx - 230, cy + 120)], 8, closed=True)
    d.polygon(isl, fill=YEL + (int(150 * ease((lt - 0.3) / 0.5)),))
    brush(d, isl, ease(lt / 0.9), CHAR, 12, 21)
    for k, (x, y, s, f) in enumerate([(cx - 110, cy - 30, 2.4, False), (cx + 120, cy - 10, 2.0, True), (cx + 10, cy + 70, 1.7, False)]):
        mammoth(d, x, y, s, ease((lt - 0.5 - 0.2 * k) / 0.8), ease((lt - 0.9 - 0.2 * k) / 0.5), flip=f, seed=30 + k)
    rise = ease((lt - 1.2) / max(0.5, dur - 2.0))                               # rising seas close in
    for r in range(6):
        off = 520 - 240 * rise - r * 60
        if off < 380: continue
        ph = t * 1.8 + r
        top = [(x, cy - off + 14 * math.sin(x / 50 + ph)) for x in range(80, W - 70, 30)]
        bot = [(x, cy + off - 60 + 14 * math.sin(x / 50 + ph + 1)) for x in range(80, W - 70, 30)]
        brush(d, top, 1.0, CHAR, 9, 40 + r, 170); brush(d, bot, 1.0, CHAR, 9, 50 + r, 170)
    k = wt(ln, 7)                                                              # "trapped"
    v = ease((lt - k) / 0.6)
    if v > 0:
        ring = spline([(cx + 410 * math.cos(a), cy + 250 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 13)[:-1]], 8, closed=True)
        brush(d, ring, v, RED, 14, 60)
        text(img, "TRAPPED!", 110, W / 2, 1400, RED, u=ease((lt - k - 0.2) / 0.3))

def S_tally(img, sc, ln, lt, dur, t):
    d = ImageDraw.Draw(img, "RGBA")
    text(img, "WRANGEL", fit("WRANGEL", 200), W / 2, 240, YEL, u=ease(lt / 0.4))
    text(img, "ISLAND", 120, W / 2, 420, KAO, u=ease((lt - 0.15) / 0.4))
    text(img, "off Siberia", 74, W / 2, 545, YEL, u=ease((lt - 0.6) / 0.4), outline=True)
    k = max(0.8, wt(ln, 5) - 0.1)                                              # "The herd started..."
    n = 8
    for i in range(n):
        at = k + i * 0.2; v = ease((lt - at) / 0.16)
        x = 230 + i * 88 + (40 if i >= 5 else 0); y0 = 750 + 10 * math.sin(i * 1.7)
        brush(d, [(x, y0), (x + 6 * math.sin(i), y0 + 330)], v, RED if i % 2 else CHAR, 26, 80 + i)
    v = ease((lt - k - 1.7) / 0.4)
    if v > 0: text(img, "FEWER THAN 10", fit("FEWER THAN 10", 130), W / 2, 1270, KAO, u=v)
    hand(img, 930, 1420, 0.5, RED, 0.85, -10)

def mam_dots(cx, cy, s, n=300, seed=1):
    poly = spline(tf(MAM, cx, cy, s), 4, closed=True); m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).polygon(poly, fill=255)
    A = np.asarray(m); rr = np.random.default_rng(seed); pts = []
    while len(pts) < n:
        x, y = rr.uniform(cx - 55 * s, cx + 55 * s), rr.uniform(cy - 45 * s, cy + 45 * s)
        if 0 <= int(y) < H and 0 <= int(x) < W and A[int(y), int(x)] and all((x - p[0]) ** 2 + (y - p[1]) ** 2 > (2.6 * s) ** 2 for p in pts[-60:]):
            pts.append((x, y))
    pts.sort(key=lambda p: p[0]); return poly, pts
DOTS = mam_dots(W / 2, 1010, 9.0)
def S_dots(img, sc, ln, lt, dur, t):
    d = ImageDraw.Draw(img, "RGBA")
    poly, pts = DOTS; s = 9.0
    brush(d, poly, ease(lt / 0.7), CHAR, 9, 90, 170)
    grow = ease((lt - 0.1) / max(0.6, dur * 0.7)); shown = int(len(pts) * grow)
    for i, (x, y) in enumerate(pts[:shown]):
        r_ = 10 + 2 * ((i * 7) % 3); c = RED if (i * 13) % 5 else YEL
        d.ellipse([x - r_, y - r_, x + r_, y + r_], fill=c + (230,))
    num = max(10, int(round(300 * grow)))
    text(img, f"~{num}", 220, W / 2, 300, YEL)
    text(img, "MAMMOTHS", 100, W / 2, 470, KAO, u=ease(lt / 0.4))

def S_pyramid(img, sc, ln, lt, dur, t):
    d = ImageDraw.Draw(img, "RGBA")
    a, s_ = slam(lt, wt(ln, 1) - 0.1)
    text(img, "2560 BC", fit("2560 BC", 210), W / 2, 250, YEL, u=1.0 if a else 0, scale=s_)
    k = max(0.3, wt(ln, 3) - 0.2)                                              # "Egypt"
    text(img, "EGYPT", 110, W / 2, 430, KAO, u=ease((lt - k) / 0.4))
    sun(d, 870, 640, 58, ease((lt - 0.2) / 0.6), t)
    pyramid(d, W / 2 + 40, 1230, 640, ease(lt / 1.6), ease((lt - 0.8) / 0.6), 5)
    v = ease((lt - 1.4) / 0.6)
    if v > 0:                                                                 # workers drag a block on a sled
        bx = 560 - 40 * ease((lt - 1.4) / 3.0)
        d.rectangle([bx - 70, 1300, bx + 70, 1400], fill=YEL + (int(220 * v),)); d.rectangle([bx - 70, 1300, bx + 70, 1400], outline=CHAR + (int(230 * v),), width=8)
        brush(d, [(bx - 95, 1410), (bx + 95, 1410)], v, CHAR, 8, 120)
        brush(d, [(bx - 70, 1330), (bx - 150, 1335), (bx - 330, 1330)], v, CHAR, 5, 121)
        for i in range(3): person(d, bx - 150 - i * 85, 1420, 1.25, 0.35, v, 130 + 5 * i, t * 6 + i)
    hand(img, 950, 1420, 0.48, YEL, 0.8, 8)

def S_timeline(img, sc, ln, lt, dur, t):
    d = ImageDraw.Draw(img, "RGBA")
    y = 960; x0, x1 = 170, 910
    k_c = wt(ln, 5) - 0.1; k_l = wt(ln, 6) - 0.1; k_4 = wt(ln, 12) - 0.15        # "centuries", "last", "4,000"
    if lt < k_l: text(img, "STILL THERE", fit("STILL THERE", 170), W / 2, 280, YEL, u=ease(lt / 0.35))
    else:
        a, s_ = slam(lt, k_l)
        text(img, "THE LAST ONES", fit("THE LAST ONES", 130), W / 2, 250, KAO, scale=s_)
        a2, s2 = slam(lt, k_4)
        if a2: text(img, "~4,000 YEARS AGO", fit("~4,000 YEARS AGO", 120), W / 2, 400, YEL, scale=s2)
    pyramid(d, x0, y - 40, 230, 1.0, 1.0, 5)
    text(img, "2560 BC", 74, x0, y + 70, KAO)
    v = ease((lt - 0.3) / max(0.6, k_c - 0.3 + 0.8))
    end = x0 + (x1 - x0) * v
    brush(d, [(x0 + 120, y - 40), (end, y - 40)], 1.0 if v > 0 else 0, KAO, 14, 140)
    for i, x in enumerate(np.arange(x0 + 170, end, 70)): brush(d, [(x, y - 60), (x, y - 20)], 1.0, KAO, 8, 150 + i)
    vb = ease((lt - k_c) / 0.5)
    if vb > 0:
        brush(d, spline([(x0 + 140, y - 120), (W / 2, y - 190), (x1 - 40, y - 120)], 10), vb, RED, 14, 160)
        text(img, "CENTURIES MORE", 100, W / 2 + 40, y - 270, RED, u=vb)
    vm = ease((lt - k_c - 0.3) / 0.9)
    if vm > 0:
        mammoth(d, x1 - 150, y + 220, 3.4, vm, ease((lt - k_c - 0.8) / 0.5), seed=170)
        text(img, "~2000 BC", 74, x1 - 150, y + 410, KAO, u=ease((lt - k_c - 0.8) / 0.4))
    hand(img, 150, 1350, 0.5, RED, 0.85, 20)

def S_end(img, sc, ln, lt, dur, t):
    d = ImageDraw.Draw(img, "RGBA")
    text(img, "SOUNDS FAKE?", fit("SOUNDS FAKE?", 170), W / 2, 210, KAO)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.35)
    y = 450; x0, x1 = 200, 880
    slab = spline([(x0, y - 70), (W / 2, y - 92), (x1, y - 72), (x1 + 60, y), (x1, y + 74), (W / 2, y + 90), (x0, y + 70), (x0 - 60, y)], 8, closed=True)
    d.polygon(slab, fill=CHAR + (200,))
    if on > 0:
        fillw = x0 - 60 + (x1 + 120 - x0) * (0.2 + 0.8 * on)
        m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).polygon(slab, fill=255)
        ImageDraw.Draw(m).rectangle([fillw, 0, W, H], fill=0)
        lay = Image.new("RGBA", (W, H), RED + (0,)); lay.putalpha(m.point(lambda v: int(v * 0.9))); img.alpha_composite(lay)
    brush(d, slab, 1.0, KAO, 9, 200, 200)
    text(img, "FAKE", 100, 690, y, KAO, u=1 - on if on < 1 else 0, outline=False) if on < 1 else None
    if on > 0: text(img, "TRUE", 100, 400, y, KAO, u=on, outline=False)
    hand(img, 300 + (780 - 300) * on, y + 6, 0.5, YEL, 1.0, -90)
    if on > 0.6:
        w_ = eout((lt - click - 0.25) / 0.35)
        text(img, "IT'S TRUE.", fit("IT'S TRUE.", 190), W / 2, 680, YEL, scale=0.6 + 0.4 * back(min(1, w_)) if w_ > 0 else 1, u=1 if w_ > 0 else 0)
        text(img, "Follow for more.", 84, W / 2, 830, KAO, u=eout((lt - click - 0.45) / 0.35))
    pyramid(d, 840, 1400, 340, 1.0, 1.0, 3)
    mammoth(d, 340, 1230, 4.8 + 0.05 * math.sin(t * 1.3), 1.0, 1.0, seed=4)

SCENES = dict(hook=S_hook, island=S_island, tally=S_tally, dots=S_dots, pyramid=S_pyramid, timeline=S_timeline, end=S_end)

# ---------- audio: cave wind + bone flute + log drum + rattle ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.22, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32); tt = np.arange(n) / SR
wind = np.convolve(np.random.default_rng(2).normal(0, 1, n), np.ones(80) / 80, mode="same")
music += (wind * (0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * tt)) * 0.9).astype(np.float32)
music += (0.10 * (np.sin(2 * np.pi * 73.42 * tt) + 0.4 * np.sin(2 * np.pi * 110.0 * tt)) * (1 + 0.08 * np.sin(2 * np.pi * 0.2 * tt))).astype(np.float32)
PENT = [293.66, 349.23, 392.0, 440.0, 523.25, 587.33]
mel = [0, 2, 3, 2, 4, 3, 2, 0, 1, 2, 3, 5, 4, 3, 2, 1]
def flute(f, dur):
    s = np.arange(int(dur * SR)) / SR; env = np.minimum(1, s / 0.08) * np.exp(-s * 1.6)
    bend = f * (1 - 0.03 * np.exp(-s * 12))
    ph = 2 * np.pi * np.cumsum(bend) / SR + 0.3 * np.sin(2 * np.pi * 4.8 * s) * np.minimum(1, s / 0.4)
    sig = (np.sin(ph) + 0.12 * np.sin(2 * ph)) * env + np.convolve(np.random.default_rng(int(f)).normal(0, 0.12, len(s)), np.ones(4) / 4, "same") * env
    return sig.astype(np.float32)
BEAT = 0.5
for k in range(int(total / (BEAT * 2))):
    place(music, 0.3 + k * BEAT * 2, flute(PENT[mel[k % len(mel)]], BEAT * 2.4), 0.07)
def log_drum(at, f, gain):
    s = np.arange(int(0.4 * SR)) / SR
    place(music, at, (np.sin(2 * np.pi * f * s) * np.exp(-s * 14) + 0.5 * np.sin(2 * np.pi * f * 1.5 * s) * np.exp(-s * 20)).astype(np.float32), gain)
def rattle(at, gain):
    s = np.arange(int(0.12 * SR)) / SR
    place(music, at, (np.random.default_rng(int(at * 100)).normal(0, 1, len(s)) * np.exp(-s * 40)).astype(np.float32), gain)
for k in range(int(total / BEAT)):
    log_drum(k * BEAT, 140 if k % 4 in (0, 3) else 196, 0.14 if k % 2 == 0 else 0.09)
    rattle(k * BEAT + BEAT / 2, 0.03)
hook_hit(music, 0.35)
for s_ in scene_starts(spec): whoosh(music, s_, 0.12)
for ln in spec["lines"]:
    typ = ln["scene"]["type"]
    if typ == "tally":
        k = max(0.8, words[ln["_w0"] + 5][1] - ln["_s"])
        for i in range(8): log_drum(ln["_s"] + k + i * 0.2, 260, 0.14)
    if typ == "end":
        place(music, ln["_s"] + ln["scene"].get("click_at", 0.45), tone(587.33, 1.6, decay=3, harm=(1, 2, 3)), 0.14)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.4)

# ---------- compose ----------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 74
    while F("bold", size).getlength(" ".join(ws)) > W - 240 and size > 36: size -= 4
    f = F("bold", size); tw = f.getlength(" ".join(ws)); x = (W - tw) / 2; y = 1588
    d = ImageDraw.Draw(img, "RGBA"); r = random.Random(gi)
    x0, x1, y0, y1 = x - 44, x + tw + 44, y - 26, y + size + 30
    slab = [(x0 + r.uniform(-8, 8), y0 + r.uniform(-6, 6)), ((x0 + x1) / 2, y0 - 8 + r.uniform(-4, 4)), (x1 + r.uniform(-8, 8), y0 + r.uniform(-6, 6)),
            (x1 + 12, (y0 + y1) / 2), (x1 + r.uniform(-8, 8), y1 + r.uniform(-6, 6)), ((x0 + x1) / 2, y1 + 8), (x0 + r.uniform(-8, 8), y1 + r.uniform(-6, 6)), (x0 - 12, (y0 + y1) / 2)]
    d.polygon(slab, fill=(20, 14, 10, 238)); d.line(slab + [slab[0]], fill=RED + (255,), width=5)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=(255, 196, 80, 255) if on else (255, 255, 255, 255)); x += f.getlength(w + " ")

STARTS = [ln["_s"] for ln in spec["lines"]]
def dip_at(t):
    dmin = 1.0
    for i, s in enumerate(STARTS[1:], 1):
        if spec["lines"][i]["scene"]["type"] == spec["lines"][i - 1]["scene"]["type"]: continue
        u = t - s
        if -0.12 < u < 0.35: dmin = min(dmin, 0.35 + 0.65 * (abs(u + 0.12) / 0.12 if u < 0 else min(1, u / 0.35) ** 0.7 * 1.0))
    return dmin

EMB = [(random.Random(i).uniform(200, 880), random.Random(i + 99).uniform(0, 1), random.Random(i + 7).uniform(0.6, 1.4)) for i in range(14)]
def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    paint = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    SCENES[ln["scene"]["type"]](paint, ln["scene"], ln, lt, dur, t)
    P = np.asarray(paint).astype(np.float32)
    a = (P[..., 3:4] / 255.0) * GRAIN[..., None] * 0.97
    out = ROCK * (1 - a) + P[..., :3] * PSHADE * a
    out *= lightmap(t, dip_at(t))
    img = Image.fromarray(out.clip(0, 255).astype(np.uint8)).convert("RGBA"); d = ImageDraw.Draw(img, "RGBA")
    for x, ph, sp in EMB[:6]:                                                      # embers drifting up from the torch
        u = (ph + t * 0.18 * sp) % 1.0; ex = x + 30 * math.sin(t * 2 * sp + ph * 6); ey = 1500 - u * 1350
        al = int(110 * math.sin(math.pi * u)); r_ = 2 + 1.2 * sp
        d.ellipse([ex - r_ * 2.5, ey - r_ * 2.5, ex + r_ * 2.5, ey + r_ * 2.5], fill=(255, 140, 40, al // 6))
        d.ellipse([ex - r_, ey - r_, ex + r_, ey + r_], fill=(255, 200, 110, al))
    caption(img, t)
    d.rectangle([0, H - 10, W, H], fill=CHAR); d.rectangle([0, H - 10, int(W * t / total), H], fill=YEL)
    return img.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=28); print(f"done {total:.1f}s")
