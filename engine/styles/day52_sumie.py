"""Day 52 — SUMI-E style (some bamboo grows almost a meter a day; bamboo is a giant grass).
A hanging-scroll ink painting that paints itself. Everything is ink soaked into warm rice paper:
- paper: cream base with low-frequency mottling, long kozo fibres and flecks, celadon silk mount strips at both sides;
- ink: every mark is a brush stroke drawn along a path (circle stamps of varying radius -> ragged edge from noise ->
  dry-brush streaks -> darker 'wet edge' where the ink pooled), multiplied into the paper;
- pale ink-wash grove and mist bands for depth, one pale indigo wash for water, vermilion for seals and accents;
- bamboo culms painted segment by segment with dark node strokes, swaying leaf clusters, a pointed young shoot
  that grows beside a brushed ruler; ensō circle clock; inflating water cells; a red seal 竹/草.
Type: Shippori Mincho B1 ExtraBold set in ink (slightly ragged edges), vermilion accents, Kaushan Script for small
brush notes. Cuts are dry-brush wipes (a ragged ink edge sweeps across the scroll).
Ending: a dry-brush track with FAKE / TRUE; the knob is a vermilion seal (竹) that slides across and stamps,
then dissolves back into the hook for the loop.
Music: original D-minor pentatonic koto-style plucks (Karplus-Strong), breathy flute tones, low drone,
soft taiko on cuts, wood-block ticks, seal thud.
Usage: python3 engine/styles/day52_sumie.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys
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
        _F[k] = ImageFont.truetype(f"{FONTS}/{'ShipporiMinchoB1-ExtraBold.ttf' if kind == 'm' else 'KaushanScript-Regular.ttf'}", int(s))
    return _F[k]

PAPER_C = np.array([238, 229, 208], np.float32)
INK = np.array([20, 18, 24], np.float32)
RED = np.array([196, 44, 32], np.float32)
INDIGO = np.array([66, 92, 132], np.float32)
CREAM = (246, 239, 222)

# ---------- noise ----------
def fbm(h, w, seed, octaves=4, base=64):
    r = np.random.default_rng(seed); out = np.zeros((h, w), np.float32); amp = 1.0
    for o in range(octaves):
        s = max(2, base >> o)
        n = r.normal(0, 1, (h // s + 2, w // s + 2)).astype(np.float32)
        out += cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC) * amp; amp *= 0.5
    return out / 1.6
NZ = fbm(H, W, 1, 4, 16)
NZ2 = fbm(H, W, 2, 4, 90)
_r = np.random.default_rng(3).normal(0, 1, (H, W)).astype(np.float32)
VST = cv2.blur(_r, (3, 61)); VST = (VST / VST.std() - 0.4).astype(np.float32)
HST = cv2.blur(_r, (61, 3)); HST = (HST / HST.std() - 0.4).astype(np.float32)

# ---------- paper ----------
def make_paper():
    p = np.ones((H, W, 3), np.float32) * PAPER_C
    p *= (1 + 0.035 * NZ2[..., None] + 0.012 * NZ[..., None])
    rng = np.random.default_rng(7)
    fib = np.zeros((H, W), np.float32)
    for _ in range(900):
        x, y = rng.uniform(0, W), rng.uniform(0, H); a = rng.uniform(0, math.pi); L = rng.uniform(20, 120)
        pts = [(x + math.cos(a + 0.4 * math.sin(k)) * L * k / 6, y + math.sin(a + 0.4 * math.sin(k)) * L * k / 6) for k in range(7)]
        cv2.polylines(fib, [np.array(pts, np.int32)], False, float(rng.uniform(0.3, 1)), 1, cv2.LINE_AA)
    fib = cv2.GaussianBlur(fib, (0, 0), 0.6)
    p *= (1 - 0.05 * fib[..., None])
    fl = (rng.uniform(0, 1, (H, W)) > 0.9993).astype(np.float32); fl = cv2.GaussianBlur(fl, (0, 0), 1.2) * 6
    p *= (1 - 0.25 * np.clip(fl, 0, 1)[..., None])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = 1 - 0.16 * np.clip(((xx - W / 2) / (W * 0.7)) ** 2 + ((yy - H / 2) / (H * 0.66)) ** 2, 0, 1) ** 1.4
    p *= vig[..., None]
    # silk mount strips at both sides
    for x0, x1 in ((0, 26), (W - 26, W)):
        p[:, x0:x1] = np.array([150, 162, 150], np.float32) * (1 + 0.05 * HST[:, x0:x1, None] * 0.3 + 0.03 * NZ[:, x0:x1, None])
    p[:, 26:30] *= 0.55; p[:, W - 30:W - 26] *= 0.55
    return p
PAPER = make_paper()

# ---------- brush ----------
def bez(p0, p1, p2, n=24):
    s = np.linspace(0, 1, n)[:, None]; p0, p1, p2 = map(np.array, (p0, p1, p2))
    return (1 - s) ** 2 * p0 + 2 * (1 - s) * s * p1 + s * s * p2

def prof(kind, s):
    if kind == "brush": return np.clip(s / 0.05, 0.25, 1) ** 0.5 * np.clip((1 - s) / 0.06, 0.3, 1) ** 0.5
    if kind == "leaf": return np.clip(s / 0.28, 0, 1) ** 0.7 * (1 - s) ** 0.85 * 1.25 + 0.04
    if kind == "taper": return (1 - s * 0.92) ** 0.8 * np.clip(s / 0.06, 0.35, 1) ** 0.5
    if kind == "tip": return np.clip(1 - s, 0.02, 1) ** 0.9
    return np.ones_like(s)

def ink(L, d, x0, y0):
    """multiply-accumulate density patch d into layer L at (x0, y0) with clipping."""
    h, w = d.shape; X0, Y0 = max(0, x0), max(0, y0); X1, Y1 = min(W, x0 + w), min(H, y0 + h)
    if X1 <= X0 or Y1 <= Y0: return
    sub = d[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
    L[Y0:Y1, X0:X1] = 1 - (1 - L[Y0:Y1, X0:X1]) * (1 - sub)

def stroke(L, pts, w, dens=0.92, prog=1.0, kind="brush", rough=1.0, dry=0.0, wet=0.6, streak="v", alpha=1.0):
    pts = np.asarray(pts, np.float32)
    if prog <= 0: return
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)]); tot = cum[-1]
    M = max(4, int(tot / 2.2)); s = np.linspace(0, 1, M)
    P = np.stack([np.interp(s * tot, cum, pts[:, 0]), np.interp(s * tot, cum, pts[:, 1])], 1)
    k = max(2, int(math.ceil(M * min(1, prog))))
    r = np.maximum(0.7, w / 2 * prof(kind, s))
    P, r = P[:k], r[:k]
    mg = int(r.max() + 8)
    x0, y0 = int(P[:, 0].min()) - mg, int(P[:, 1].min()) - mg
    x1, y1 = int(P[:, 0].max()) + mg, int(P[:, 1].max()) + mg
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if X1 - X0 < 2 or Y1 - Y0 < 2: return
    m = np.zeros((Y1 - Y0, X1 - X0), np.float32)
    for (px, py), rr in zip(P, r):
        cv2.circle(m, (int((px - X0) * 4), int((py - Y0) * 4)), int(rr * 4), 1.0, -1, cv2.LINE_AA, 2)
    m = cv2.GaussianBlur(m, (0, 0), 1.0)
    if rough: m = np.clip((m - 0.5) * 2.4 + 0.5 + rough * 0.2 * NZ[Y0:Y1, X0:X1], 0, 1)
    if dry: m *= 1 - dry * np.clip((VST if streak == "v" else HST)[Y0:Y1, X0:X1], 0, 1)
    e = np.clip(m - cv2.GaussianBlur(m, (0, 0), 4), 0, 1)
    d = np.clip(m * dens * 0.82 + e * wet * 1.6, 0, 1) * alpha
    ink(L, d, X0, Y0)

def dot(L, x, y, r, dens=0.6, wet=0.8):
    stroke(L, [(x, y), (x + 0.5, y + 0.5)], 2 * r, dens, kind="line", wet=wet)

def wash(L, mask, dens):
    L[:] = 1 - (1 - L) * (1 - np.clip(mask * dens * (0.82 + 0.18 * NZ2), 0, 1))

# ---------- type ----------
_TM = {}
def tmask(s, size, kind="m", rough=0.1):
    k = (s, size, kind, rough)
    if k not in _TM:
        f = F(kind, size); l, tp, r, b = f.getbbox(s)
        im = Image.new("L", (r - l + 16, b - tp + 16)); ImageDraw.Draw(im).text((8 - l, 8 - tp), s, font=f, fill=255)
        m = np.asarray(im, np.float32) / 255
        h, w = m.shape
        if rough:
            m = cv2.GaussianBlur(m, (0, 0), 0.8)
            m = np.clip((m - 0.5) * 2.6 + 0.5 + rough * NZ[:h, :w] * 0.5, 0, 1)
            m *= 1 - 0.18 * np.clip(HST[100:100 + h, :w], 0, 1)
        e = np.clip(m - cv2.GaussianBlur(m, (0, 0), 3), 0, 1)
        _TM[k] = (np.clip(m * 0.9 + e * 0.5, 0, 1), l - 8, tp - 8, f.getlength(s))
    return _TM[k]

def text(L, s, size, x, y, anchor="c", prog=1.0, kind="m", rough=0.1, alpha=1.0):
    """y = top of the ink box; anchor c/l/r on x."""
    if prog <= 0: return
    m, _, _, tw = tmask(s, size, kind, rough)
    h, w = m.shape
    x0 = int(x - w / 2) if anchor == "c" else (int(x) - 8 if anchor == "l" else int(x - w + 8))
    if prog < 1:
        xs = np.arange(w, dtype=np.float32); ramp = np.clip((prog * (w + 60) - xs) / 60, 0, 1)
        m = m * ramp[None, :]
    ink(L, m * alpha, x0, int(y))
    return w

def seal(R, cx, cy, size, ch="竹", alpha=1.0, rot=0.0):
    """vermilion stone seal: rounded square, uneven stamp texture, character carved out (cream)."""
    S = int(size * 1.5)
    m = np.zeros((S, S), np.float32); h = size / 2
    c = S / 2
    cv2.rectangle(m, (int(c - h), int(c - h)), (int(c + h), int(c + h)), 1.0, -1, cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), 1.5)
    m = np.clip((m - 0.5) * 3 + 0.5 + 0.25 * NZ[300:300 + S, 300:300 + S], 0, 1)
    f = F("m", int(size * 0.74)); im = Image.new("L", (S, S))
    ImageDraw.Draw(im).text((c, c), ch, font=f, fill=255, anchor="mm")
    g = np.asarray(im, np.float32) / 255
    g = np.clip((cv2.GaussianBlur(g, (0, 0), 0.8) - 0.5) * 3 + 0.5 + 0.2 * NZ[600:600 + S, 200:200 + S], 0, 1)
    m = m * (1 - g)
    m *= 1 - 0.3 * np.clip(NZ2[100:100 + S, 500:500 + S] * 1.5 + 0.2 * VST[0:S, 0:S], 0, 1)
    if rot:
        A = cv2.getRotationMatrix2D((c, c), rot, 1.0); m = cv2.warpAffine(m, A, (S, S))
    ink(R, np.clip(m * alpha, 0, 1), int(cx - c), int(cy - c))

# ---------- bamboo ----------
def node(L, x, y, w, dens=0.95):
    stroke(L, bez((x - w * 0.62, y + 3), (x, y - 7), (x + w * 0.62, y + 3), 10), 7, dens, kind="taper", wet=0.3)
    stroke(L, bez((x - w * 0.3, y + 9), (x, y + 13), (x + w * 0.35, y + 8), 8), 4, dens * 0.8, kind="tip", wet=0.2)

def culm(L, x, ybot, ytop, w, seg=200, dens=0.85, lean=0.0, prog=1.0, dry=0.25, nodes=True, rough=1.0, wet=0.75):
    """mature culm, painted bottom->top segment by segment (prog = fraction painted)."""
    n = max(1, int(math.ceil((ybot - ytop) / seg))); done = prog * n
    for i in range(n):
        if i >= done: break
        y0 = ybot - i * seg; y1 = max(ytop, y0 - seg + 9)
        xx0 = x + lean * (ybot - y0); xx1 = x + lean * (ybot - y1)
        p = min(1, done - i)
        stroke(L, [(xx0, y0 - 4), ((xx0 + xx1) / 2 + 2, (y0 + y1) / 2), (xx1, y1)], w, dens, p, "brush", rough, dry, wet)
        if nodes and p >= 1 and y1 > ytop: node(L, xx1, y1 - 4, w, min(1, dens + 0.1))

def shoot(L, x, ybase, h, w=42, dens=0.9, seed=0, t=0.0):
    """young bamboo shoot with a pointed sheath tip; segments short near the base."""
    if h < 10: return
    n = max(2, int(h / 78) + 1)
    wts = np.array([0.6 + 0.4 * min(1, i / 3) for i in range(n)]); wts = wts / wts.sum() * h
    y = ybase
    for i in range(n):
        y1 = y - wts[i]; ww = w * (1 - 0.3 * i / n)
        if i < n - 1:
            stroke(L, [(x, y - 3), (x + 1, (y + y1) / 2), (x, y1 + 6)], ww, dens, kind="brush", dry=0.25, wet=0.75)
            node(L, x, y1 + 2, ww, min(1, dens + 0.1))
            side = 1 if i % 2 else -1
            stroke(L, bez((x + side * ww * 0.4, y1 + 4), (x + side * ww * 0.9, y1 - 18), (x + side * ww * 1.2, y1 - 44 - 6 * math.sin(t * 2 + i)), 10),
                   ww * 0.35, dens * 0.9, kind="leaf", wet=0.5, rough=0.6)
        else:
            stroke(L, [(x, y - 3), (x + 2, (y + y1) / 2), (x + 4 + 3 * math.sin(t * 1.7), y1)], ww * 1.05, dens, kind="tip", dry=0.2, wet=0.8)
        y = y1

def leaf(L, x, y, ang, length, width, dens=0.95, droop=0.25):
    ca, sa = math.cos(ang), math.sin(ang)
    p2 = (x + ca * length, y + sa * length + droop * length * 0.5)
    p1 = (x + ca * length * 0.5, y + sa * length * 0.5 - droop * length * 0.05)
    stroke(L, bez((x, y), p1, p2, 14), width, dens, kind="leaf", rough=0.7, wet=0.45)

def cluster(L, x, y, ang, size, t, seed=0, n=5, dens=0.95, spread=0.8):
    sw = 0.06 * math.sin(t * 1.3 + seed * 1.7)
    ex, ey = x + math.cos(ang) * size * 0.45, y + math.sin(ang) * size * 0.45
    stroke(L, bez((x, y), ((x + ex) / 2, (y + ey) / 2 - 6), (ex, ey), 10), 5, dens * 0.9, kind="taper", wet=0.2, rough=0.5)
    r = np.random.default_rng(seed)
    for i in range(n):
        a = ang + spread * (i - (n - 1) / 2) / max(1, (n - 1) / 2) + sw * (1 + i * 0.3) + r.uniform(-0.08, 0.08)
        leaf(L, ex, ey, a, size * r.uniform(1.0, 1.3), size * 0.15, dens * r.uniform(0.7, 1.0), 0.35 + 0.2 * r.uniform())

def grove(L, seed=0, dens=0.12, xs=(120, 230, 860, 960), mist=(1250, 1380), clear=(110, 120, 970, 820)):
    r = np.random.default_rng(seed)
    G = np.zeros((H, W), np.float32)
    for x in xs:
        w = r.uniform(22, 32); s = r.uniform(170, 240)
        culm(G, x, H + 20, -40, w, s, dens, r.uniform(-0.01, 0.01), dry=0.15, wet=0.3)
    ys = np.arange(H, dtype=np.float32)
    band = np.exp(-((ys - (mist[0] + mist[1]) / 2) / ((mist[1] - mist[0]) / 2)) ** 2)[:, None]
    G *= 1 - 0.85 * np.clip(band * (0.8 + 0.3 * NZ2), 0, 1)
    if clear:
        c = np.zeros((H, W), np.float32); cv2.rectangle(c, clear[:2], clear[2:], 1.0, -1)
        c = cv2.GaussianBlur(c, (0, 0), 70); G *= 1 - 0.8 * c
    L[:] = 1 - (1 - L) * (1 - G)

def ground(L, y, x0=60, x1=W - 60, dens=0.35, seed=5):
    stroke(L, [(x0, y + 6), ((x0 + x1) / 2, y - 4), (x1, y + 8)], 26, dens, kind="brush", dry=0.6, streak="h", wet=0.5)
    r = np.random.default_rng(seed)
    for _ in range(18):
        gx = r.uniform(x0 + 20, x1 - 20); hgt = r.uniform(18, 46); a = r.uniform(-0.5, 0.5)
        stroke(L, bez((gx, y), (gx + a * hgt * 0.3, y - hgt * 0.6), (gx + a * hgt, y - hgt), 8), 6, dens + 0.3, kind="tip", wet=0.3, rough=0.5)

def ruler(L, R, x, ybot, ytop, ticks, labels=(), dens=0.85, red_at=None, prog=1.0):
    stroke(L, [(x, ybot), (x, ytop)], 7, dens, prog, "line", 0.6, 0.0, 0.3)
    n = len(ticks)
    for i, (y, big) in enumerate(ticks):
        if (ybot - y) > prog * (ybot - ytop) + 2: continue
        lw = 34 if big else 18
        stroke(L, [(x - 2, y), (x - 2 - lw, y + 1)], 5 if big else 4, dens, kind="taper", rough=0.5, wet=0.2)
    for (y, s, size) in labels:
        if (ybot - y) <= prog * (ybot - ytop) + 2: text(L, s, size, x - 46, y - size * 0.62, "r", kind="k", rough=0.05)

# ---------- scenes ----------
STATIC = {}
def static(name, builder):
    if name not in STATIC:
        D = np.zeros((H, W), np.float32); R = np.zeros((H, W), np.float32); B = np.zeros((H, W), np.float32)
        builder(D, R, B); STATIC[name] = (D, R, B)
    D, R, B = STATIC[name]
    return D.copy(), R.copy(), B.copy()

def wstart(ln, k): return words[ln["_w0"] + k][1] - ln["_s"]

M1 = 900; GY = 1452   # hook ruler: 1 m from GY up to M1
def hook(ln, lt, dur, t):
    def b(D, R, B):
        grove(D, 1, 0.15, (180, 300, 760, 880), (1180, 1330))
        culm(D, 52, H + 20, -40, 50, 230, 0.9, 0.004)
        culm(D, 1028, H + 20, -40, 58, 210, 0.9, -0.006)
        ground(D, GY)
        ticks = [(GY - k * (GY - M1) / 10, k % 5 == 0) for k in range(11)]
        ruler(D, R, 330, GY, M1 - 4, ticks, [(GY - 2, "0", 44), ((GY + M1) / 2, "50 cm", 40)])
        text(D, "THIS GRASS", 116, W / 2, 160)
        text(D, "GROWS", 116, W / 2, 300)
        text(R, "1 METER", 164, W / 2, 440)
        text(D, "A DAY", 116, W / 2, 640)
        seal(R, 905, 360, 92, "竹", 0.95, -4)
    D, R, B = static("hook", b)
    cluster(D, 70, 70, -0.25, 140, t, 1); cluster(D, 1010, 60, math.pi + 0.25, 140, t, 2)
    cluster(D, 1005, 1010, math.pi + 0.15, 140, t, 3); cluster(D, 75, 1180, 0.2, 130, t, 4, 4)
    g = 0.7 + 0.3 * eout(lt / 1.8)
    shoot(D, 600, GY - 6, (GY - M1) * g, 46, 0.95, 0, t)
    if g > 0.97:   # red dashed 1 m mark
        for k in range(6): stroke(R, [(372 + k * 48, M1), (398 + k * 48, M1)], 6, 0.9, kind="taper", rough=0.5)
    text(R, "1 m", 58, 300, M1 - 50, "r", kind="k", rough=0.05)
    return D, R, B

def tree(ln, lt, dur, t):
    def b(D, R, B):
        grove(D, 2, 0.12, (150, 930), (1150, 1300))
        ground(D, GY, 140, 940, seed=8)
    D, R, B = static("tree", b)
    p = eout(lt / 1.0)
    items = []
    items.append(lambda pp: stroke(D, bez((540, GY), (500, 1180), (560, 960), 20), 74, 0.9, pp, "taper", 1, 0.45, 0.7))
    for (sx, sy, ex, ey, w) in ((548, 1080, 380, 900, 26), (556, 1010, 730, 860, 24), (560, 960, 470, 780, 20), (552, 1150, 760, 1060, 18)):
        items.append(lambda pp, a=(sx, sy, ex, ey, w): stroke(D, bez(a[:2], ((a[0] + a[2]) / 2, a[1] - 60), a[2:4], 14), a[4], 0.9, pp, "taper", 1, 0.3, 0.5))
    r = np.random.default_rng(11)
    blobs = [(cx + r.normal(0, 70), cy + r.normal(0, 40), r.uniform(26, 48)) for cx, cy in ((400, 870), (720, 840), (560, 760), (480, 800), (650, 790), (770, 1040)) for _ in range(5)]
    for i, (x, y, rr) in enumerate(blobs):
        ang_ = r.uniform(-0.6, 0.6) + (math.pi if i % 2 else 0)
        items.append(lambda pp, a=(x, y, rr, i, ang_): stroke(D, [(a[0], a[1]), (a[0] + math.cos(a[4]) * a[2] * 1.4, a[1] + math.sin(a[4]) * a[2] * 0.9)],
                                                         a[2] * 0.9, 0.55 + 0.4 * (a[3] % 3) / 2, pp, "leaf", 1.3, 0.2, 0.35))
    n = len(items)
    for i, it in enumerate(items):
        pp = np.clip(p * n * 0.75 - i * 0.75, 0, 1) if i < 5 else np.clip((p * 1.4 - 0.4) * n - (i - 5) * 0.5, 0, 1)
        if pp > 0: it(pp)
    text(D, "IT'S NOT", 120, W / 2, 190, prog=eout(lt / 0.35))
    text(D, "EVEN A TREE", 120, W / 2, 340, prog=eout((lt - 0.1) / 0.4))
    a = wstart(ln, 5) - 0.1
    stroke(R, [(330, 760), (750, 1300)], 40, 0.95, eout((lt - a) / 0.22), "taper", 1, 0.25, 0.6)
    stroke(R, [(760, 740), (320, 1320)], 40, 0.95, eout((lt - a - 0.2) / 0.22), "taper", 1, 0.25, 0.6)
    text(R, "wait for the last part...", 64, W / 2, 545, prog=eout((lt - wstart(ln, 6)) / 0.5), kind="k", rough=0.03)
    return D, R, B

def day(ln, lt, dur, t):
    def b(D, R, B):
        grove(D, 3, 0.13, (140, 900, 990), (1200, 1330))
        ground(D, GY)
        ticks = [(GY - k * (GY - M1) / 10, k % 5 == 0) for k in range(11)]
        ruler(D, R, 330, GY, M1 - 4, ticks, [(GY - 2, "0", 44), ((GY + M1) / 2, "50", 44), (M1, "100 cm", 44)])
        culm(D, 820, GY, 1000, 34, 120, 0.55, 0.0)
        culm(D, 900, GY, 900, 30, 130, 0.45, 0.0)
    D, R, B = static("day", b)
    u = ease(min(1, lt / (dur - 0.4)))
    cm = 91 * u
    shoot(D, 600, GY - 6, (GY - M1) * 0.91 * u + 14, 46, 0.95, 0, t)
    if u > 0.98:
        y91 = GY - (GY - M1) * 0.91
        for k in range(5): stroke(R, [(372 + k * 48, y91), (398 + k * 48, y91)], 6, 0.9, kind="taper", rough=0.5)
    # sun arc = 24 hours
    ang = math.pi * (1 - u); sx, sy = 540 + 380 * math.cos(ang), 690 - 120 * math.sin(ang)
    stroke(D, bez((150, 700), (540, 470), (930, 700), 30), 4, 0.35, 1, "line", 0.6, 0.5, 0.1)
    dot(R, sx, sy, 38, 0.9, 0.6)
    text(D, f"HOUR {int(24 * u):d}", 40, sx, sy + 50, kind="k", rough=0.03)
    text(D, f"{int(round(cm))} cm", 210, W / 2, 150 + 0 * lt)
    text(R, "IN 24 HOURS", 96, W / 2, 400, prog=eout(lt / 0.4))
    return D, R, B

def hour(ln, lt, dur, t):
    def b(D, R, B):
        cx, cy, rr = 540, 860, 250
        pts = [(cx + rr * math.cos(a), cy + rr * math.sin(a)) for a in np.linspace(-math.pi / 2 + 0.25, 1.5 * math.pi - 0.05, 70)]
        stroke(D, pts, 46, 0.95, 1, "taper", 1, 0.55, 0.8, "h")
        for k in range(12):
            a = k / 12 * 2 * math.pi - math.pi / 2
            stroke(D, [(cx + 185 * math.cos(a), cy + 185 * math.sin(a)), (cx + 205 * math.cos(a), cy + 205 * math.sin(a))], 9, 0.85, kind="taper", rough=0.4)
        ground(D, GY, 200, 880, 0.3)
        ticks = [(GY - 30 - k * 70, True) for k in range(5)]
        ruler(D, R, 380, GY - 30, GY - 30 - 4 * 70 - 4, ticks, [(GY - 30 - k * 70, f"{k} cm", 40) for k in range(5)])
    D, R, B = static("hour", b)
    u = min(1, lt / (dur - 0.3)); cx, cy = 540, 860
    a = -math.pi / 2 + 2 * math.pi * ease(u)
    stroke(D, [(cx, cy), (cx + 160 * math.cos(a), cy + 160 * math.sin(a))], 16, 0.95, 1, "taper", 0.6, 0, 0.4)
    stroke(D, [(cx, cy), (cx + 105 * math.cos(-math.pi / 2 + 0.52 * ease(u)), cy + 105 * math.sin(-math.pi / 2 + 0.52 * ease(u)))], 22, 0.95, 1, "taper", 0.6, 0, 0.4)
    dot(R, cx, cy, 16, 0.95)
    text(D, "1 HOUR", 54, cx, cy + 140, kind="k", rough=0.03)
    # tip of a shoot rising ~4 cm (70 px per cm)
    y0 = GY - 30 - 280 * ease(u)
    stroke(D, [(600, GY + 20), (601, (GY + y0) / 2 + 40), (600, y0 + 60)], 50, 0.92, 1, "brush", 1, 0.25, 0.75)
    stroke(D, [(600, y0 + 64), (602, y0 + 30), (604, y0 - 10)], 52, 0.95, 1, "tip", 1, 0.2, 0.8)
    stroke(R, [(450, y0 - 10), (560, y0 - 10)], 6, 0.9, kind="taper", rough=0.4)
    text(R, "~4 cm", 190, W / 2, 140, prog=eout(lt / 0.35))
    text(D, "EVERY HOUR", 112, W / 2, 370, prog=eout((lt - 0.1) / 0.4))
    return D, R, B

def cells(ln, lt, dur, t):
    def b(D, R, B):
        grove(D, 4, 0.1, (150, 940), (1250, 1400))
    D, R, B = static("cells", b)
    u = ease(min(1, max(0, (lt - 0.2) / (dur - 0.6))))
    x0, x1, yb = 380, 700, 1440
    yt = 1120 - 430 * u
    for x in (x0, x1):
        stroke(D, [(x, yb), (x + 2, (yb + yt) / 2), (x, yt)], 26, 0.9, 1, "brush", 1, 0.35, 0.7)
    node(D, 540, yb + 10, 380); node(D, 540, yt - 4, 380)
    stroke(D, [(x0 - 20, yb + 40), (x0 - 20, H + 30)], 26, 0.9, 1, "brush", 1, 0.35, 0.7)
    stroke(D, [(x1 + 20, yb + 40), (x1 + 20, H + 30)], 26, 0.9, 1, "brush", 1, 0.35, 0.7)
    stroke(D, [(x0, yt - 20), (x0 - 10, yt - 140)], 26, 0.9, 1, "tip", 1, 0.35, 0.7)
    stroke(D, [(x1, yt - 20), (x1 + 10, yt - 140)], 26, 0.9, 1, "tip", 1, 0.35, 0.7)
    cols, rows = 4, 7
    cw = (x1 - x0 - 40) / cols; ch = (yb - yt - 30) / rows
    for i in range(rows):
        for j in range(cols):
            cxp = x0 + 20 + cw * (j + 0.5); cyp = yt + 15 + ch * (i + 0.5)
            k = (rows - 1 - i) * 0.08 + j * 0.03
            f = np.clip(u * 1.6 - k, 0, 1)
            ax, ay = max(4, cw * 0.42), max(4, ch * 0.42)
            if f > 0:
                m = np.zeros((int(ay * 2 + 10), int(ax * 2 + 10)), np.float32)
                cv2.ellipse(m, (int(ax + 5), int(ay + 5)), (int(ax * (0.55 + 0.45 * f)), int(ay * (0.55 + 0.45 * f))), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
                m = cv2.GaussianBlur(m, (0, 0), 3)
                ink(B, m * 0.55 * f, int(cxp - ax - 5), int(cyp - ay - 5))
            cv2.ellipse(D, (int(cxp), int(cyp)), (int(ax), int(ay)), 0, 0, 360, 0.55, 3, cv2.LINE_AA)
    # falling water drops (indigo)
    for k in range(5):
        ph = (lt * 0.9 + k / 5) % 1
        dot(B, x0 + 40 + k * 60, yt - 160 + ph * 300, 10 * (1 - ph * 0.5), 0.7 * (1 - ph), 0.6)
    # stretch arrow
    stroke(R, [(800, yb - 20), (800, yt + 20)], 12, 0.92, 1, "line", 0.6, 0.2, 0.3)
    stroke(R, [(800, yt + 10), (776, yt + 60)], 10, 0.92, kind="taper"); stroke(R, [(800, yt + 10), (824, yt + 60)], 10, 0.92, kind="taper")
    text(D, "CELLS FILL", 118, W / 2, 150, prog=eout(lt / 0.35))
    text(B, "WITH WATER", 118, W / 2, 300, prog=eout((lt - 0.12) / 0.4))
    text(R, "stretch!", 60, 830, (yb + yt) / 2 - 40, "l", prog=eout((lt - 1.0) / 0.4), kind="k", rough=0.03)
    return D, R, B

def tall(ln, lt, dur, t):
    top = 560
    def b(D, R, B):
        grove(D, 5, 0.1, (960,), (1300, 1420))
        ground(D, GY)
        # 10-story building (generic), ~30 m
        bx0, bx1 = 600, 880; fh = (GY - top) / 10
        for (p, q) in (((bx0, GY), (bx0, top)), ((bx1, GY), (bx1, top)), ((bx0 - 14, top), (bx1 + 14, top))):
            stroke(D, [p, q], 12, 0.85, kind="brush", dry=0.3, wet=0.5)
        for k in range(1, 10):
            y = GY - k * fh
            stroke(D, [(bx0, y), (bx1, y + 2)], 5, 0.6, kind="taper", rough=0.5, wet=0.2)
            for j in range(3):
                dot(D, bx0 + 55 + j * 85, y + fh * 0.5, 13, 0.32, 0.7)
        stroke(D, [(bx0 + 120, GY), (bx0 + 120, GY - 55)], 34, 0.5, kind="brush")
        ticks = [(GY - k * (GY - top) / 6, k % 2 == 0) for k in range(7)]
        ruler(D, R, 170, GY, top - 4, ticks, [(GY - 2, "0", 44), (GY - (GY - top) / 2, "15 m", 44)])
    D, R, B = static("tall", b)
    p = eout(lt / 1.6)
    culm(D, 400, GY, top, 46, (GY - top) / 9, 0.95, 0.0, p, 0.3)
    yt = GY - (GY - top) * p
    if p > 0.95:
        cluster(D, 400, top + 40, -0.6, 130, t, 6, 4); cluster(D, 400, top + 120, math.pi + 0.5, 120, t, 7, 4)
    # tiny person (generic stick figure, ~1.7 m)
    px, py = 300, GY - 4; hh = (GY - top) / 30 * 1.7
    stroke(D, [(px, py - hh * 0.45), (px, py - hh * 0.82)], 6, 0.9, kind="line", rough=0.3)
    stroke(D, [(px, py - hh * 0.45), (px - 6, py)], 5, 0.9, kind="line", rough=0.3); stroke(D, [(px, py - hh * 0.45), (px + 6, py)], 5, 0.9, kind="line", rough=0.3)
    dot(D, px, py - hh * 0.92, 5, 0.9, 0.3)
    if p > 0.95:
        for k in range(6): stroke(R, [(196 + k * 40, top), (218 + k * 40, top)], 6, 0.9, kind="taper", rough=0.5)
    text(R, "30 m", 62, 150, top - 60, "r", kind="k", rough=0.03, prog=eout((lt - 1.2) / 0.3))
    text(D, "~10 floors", 52, 740, top - 80, kind="k", rough=0.03, prog=eout((lt - 1.4) / 0.4))
    text(D, "UP TO", 110, W / 2, 140, prog=eout(lt / 0.3))
    text(R, "30 METERS", 150, W / 2, 280, prog=eout((lt - 0.1) / 0.4))
    return D, R, B

def grass(ln, lt, dur, t):
    def b(D, R, B):
        grove(D, 6, 0.12, (880, 990), (1300, 1420))
        ground(D, GY)
        culm(D, 85, H + 20, -40, 58, 220, 0.95, 0.002)
        culm(D, 200, H + 20, 760, 40, 190, 0.8, -0.004)
    D, R, B = static("grass", b)
    cluster(D, 85, 760, 0.1, 140, t, 8, 4); cluster(D, 200, 900, -0.2, 140, t, 10, 4)
    cluster(D, 85, 1180, 0.25, 130, t, 11, 4); cluster(D, 85, 30, -0.5, 110, t, 9, 4)
    # tuft of lawn grass, blades with the same leaf shape
    r = np.random.default_rng(12)
    for k in range(9):
        a = -math.pi / 2 + (k - 4) * 0.16 + 0.05 * math.sin(t * 2 + k)
        leaf(D, 760 + (k - 4) * 6, GY, a, r.uniform(110, 170), 18, 0.95, 0.15 * (k - 4) / 4)
    gw = wstart(ln, 7) if ln["_w1"] - ln["_w0"] > 7 else 1.6
    text(D, "NOT A TREE.", 112, 600, 170, prog=eout(lt / 0.35))
    text(D, "A GIANT", 120, 650, 330, prog=eout((lt - gw + 0.6) / 0.35))
    text(R, "GRASS", 190, 650, 480, prog=eout((lt - gw + 0.2) / 0.35))
    stroke(R, bez((520, 1480), (780, 1520), (1000, 1440), 20), 10, 0.85, eout((lt - gw) / 0.4), "taper", 0.6, 0.2, 0.3)
    text(R, "same family as your lawn", 50, 760, 1170, prog=eout((lt - gw - 0.2) / 0.5), kind="k", rough=0.03)
    sp = (lt - gw - 0.3) / 0.18
    if sp > 0:
        sc = 1 + 0.25 * (1 - eout(min(1, sp)))
        seal(R, 900, 1010, int(110 * sc), "草", min(1, sp), 3)
    return D, R, B

def end(ln, lt, dur, t):
    def b(D, R, B):
        grove(D, 7, 0.13, (140, 260, 830, 950), (1250, 1380))
        stroke(D, [(250, 960), (540, 950), (830, 962)], 96, 0.55, 1, "brush", 1, 0.65, 0.7, "h")
        text(D, "SOUNDS FAKE?", 118, W / 2, 330)
    D, R, B = static("end", b)
    c = ln["scene"].get("click_at", 0.5)
    u = back(min(1, max(0, (lt - c) / 0.4)), 1.2)
    kx = 270 + (810 - 270) * u
    fa = 1 - 0.75 * min(1, max(0, (lt - c) / 0.3))
    text(D, "FAKE", 88, 270, 1050, alpha=fa)
    text(R, "TRUE", 88, 810, 1050, alpha=0.35 + 0.65 * min(1, max(0, (lt - c - 0.2) / 0.2)))
    if lt > c + 0.35: stroke(R, [(190, 1100), (350, 1092)], 12, 0.9, eout((lt - c - 0.35) / 0.2), "taper", 0.6)
    landed = (lt - c - 0.4) / 0.15
    sc = 1 + (0.12 * (1 - min(1, landed)) if landed > 0 else 0)
    seal(R, kx, 956, int(124 * sc), "竹", 1.0, -3 + 3 * u)
    if landed > 0:
        rr = np.random.default_rng(4)
        for k in range(7):
            a = rr.uniform(0, 2 * math.pi); dd = 100 + 40 * rr.uniform()
            dot(R, 810 + math.cos(a) * dd, 956 + math.sin(a) * dd, rr.uniform(4, 9) * min(1, landed), 0.85)
    text(R, "IT'S TRUE.", 130, W / 2, 470, prog=eout((lt - c - 0.3) / 0.35))
    text(D, "Follow for more", 74, W / 2, 1230, kind="k", rough=0.03, prog=eout((lt - 0.9) / 0.5))
    return D, R, B

SCENES = {"hook": hook, "tree": tree, "day": day, "hour": hour, "cells": cells, "tall": tall, "grass": grass, "end": end}

# ---------- narration + music ----------
voice, words, total = narrate(spec, lead=0.08)
n = len(voice); music = np.zeros(n, np.float32); rng = np.random.default_rng(52)

def pluck(f, dur=1.6, bright=0.5, decay=0.996):
    L = int(dur * SR); N = max(2, int(SR / f))
    y = np.zeros(L + N + 1, np.float32)
    y[:N + 1] = rng.uniform(-1, 1, N + 1) * np.hanning(N + 1)
    for st in range(N + 1, L + N + 1, N):
        e = min(st + N, L + N + 1)
        y[st:e] = decay * ((1 - bright * 0.5) * y[st - N:e - N] + bright * 0.5 * y[st - N - 1:e - N - 1])
    out = y[N + 1:N + 1 + L]
    return out / (np.abs(out).max() + 1e-6)

def flute(f, dur):
    s = np.arange(int(dur * SR)) / SR
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * s) * np.clip(s / 0.6, 0, 1)
    ph = np.cumsum(2 * np.pi * f * vib / SR)
    tone_ = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)
    br = np.convolve(rng.normal(0, 1, len(s)), np.ones(8) / 8, "same") * 0.18
    env = np.clip(s / 0.35, 0, 1) * np.clip((dur - s) / 0.5, 0, 1)
    return ((tone_ + br) * env).astype(np.float32)

def taiko(at, gain=0.3):
    s = np.arange(int(0.7 * SR)) / SR
    sig = np.sin(2 * np.pi * (55 + 50 * np.exp(-s * 18)) * s) * np.exp(-s * 5) + rng.normal(0, 1, len(s)) * np.exp(-s * 60) * 0.25
    place(music, at, sig.astype(np.float32), gain)

def block(at, gain=0.08, f=1200):
    s = np.arange(int(0.08 * SR)) / SR
    place(music, at, (np.sin(2 * np.pi * f * s) * np.exp(-s * 70)).astype(np.float32), gain)

PENT = [146.83, 174.61, 196.0, 220.0, 261.63, 293.66, 349.23, 392.0, 440.0, 523.25]   # D minor pentatonic
BEAT = 0.42
pat = [5, 7, 8, 6, 5, 3, 4, 2, 5, 7, 9, 8, 6, 5, 4, 3]
for k in range(int(total / BEAT)):
    at = k * BEAT
    if k % 2 == 0 or k % 8 == 7:
        place(music, at, pluck(PENT[pat[k % 16]], 1.4, 0.6), 0.08)
    if k % 8 == 0:
        place(music, at, pluck(PENT[0] / 2, 2.4, 0.3, 0.998), 0.07)
        place(music, at, pluck(PENT[3] / 2, 2.4, 0.3, 0.998), 0.05)
s_ = np.arange(n) / SR
music += (np.sin(2 * np.pi * 73.42 * s_) * 0.05 + np.sin(2 * np.pi * 110 * s_) * 0.025).astype(np.float32)
for at, f, d in ((1.0, 440.0, 2.6), (6.5, 392.0, 2.5), (12.0, 523.25, 2.2), (17.5, 440.0, 2.8)):
    if at + d < total: place(music, at, flute(f, d), 0.06)
hook_hit(music, 0.3); taiko(0.0, 0.25)
for i, ln in enumerate(spec["lines"]):
    s0 = ln["_s"]; st = ln["scene"]["type"]
    if i > 0: whoosh(music, s0 - 0.1, 0.08, 0.32); taiko(s0 - 0.1, 0.2)
    if st == "hour":
        for k in range(int((ln["_se"] - s0) / 0.25)): block(s0 + k * 0.25, 0.05, 1500 if k % 4 == 0 else 1100)
    if st == "tree": taiko(s0 + wstart(ln, 5) - 0.1, 0.18)
    if st == "grass" and ln["_w1"] - ln["_w0"] > 7: taiko(s0 + wstart(ln, 7) + 0.3, 0.3)
    if st == "end":
        c = s0 + ln["scene"].get("click_at", 0.5)
        taiko(c + 0.4, 0.35)
        for j, fq in enumerate((293.66, 349.23, 440.0, 587.33)): place(music, c + 0.45 + j * 0.08, pluck(fq, 1.6, 0.7), 0.09)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.45)

# ---------- compositing ----------
groups = caption_groups(words, 3)
def caption(O, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 78; f = F("m", size)
    while f.getlength(" ".join(ws)) > W - 220 and size > 44: size -= 4; f = F("m", size)
    tw_ = f.getlength(" ".join(ws)); x = (W - tw_) / 2; y = 1590
    d = ImageDraw.Draw(O)
    d.rounded_rectangle([x - 36, y - 20, x + tw_ + 36, y + size + 26], radius=14, fill=CREAM + (240,), outline=(24, 22, 26, 255), width=4)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]; wl = f.getlength(w)
        if on: d.rounded_rectangle([x - 9, y - 6, x + wl + 9, y + size + 12], radius=8, fill=tuple(int(c) for c in RED) + (255,))
        d.text((x, y - size * 0.06), w, font=f, fill=CREAM if on else (20, 18, 24)); x += f.getlength(w + " ")

def comp(D, R, B):
    out = PAPER * (1 - D[..., None] * (1 - INK / 255))
    out = out * (1 - B[..., None] * (1 - INDIGO / 255))
    out = out * (1 - R[..., None]) + RED * R[..., None] * (out / PAPER_C) ** 0.3
    return out

def scene_rgb(t, ln):
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    D, R, B = SCENES[ln["scene"]["type"]](ln, lt, dur, t)
    return comp(D, R, B)

WY = np.arange(H, dtype=np.float32)
WOFF = (60 * np.sin(WY / 140) + 40 * fbm(H, 1, 21, 3, 40)[:, 0] * 2).astype(np.float32)
XS = np.arange(W, dtype=np.float32)[None, :]
def frame(t, fi):
    lines = spec["lines"]; ln = active_line(spec, t) or lines[0]; i = lines.index(ln)
    rgb = scene_rgb(t, ln)
    if i > 0:   # dry-brush wipe: a ragged ink edge sweeps left -> right revealing the new scene
        ph = (t - (ln["_s"] - 0.12)) / 0.42
        if ph < 1:
            old = scene_rgb(ln["_s"] - 0.12, lines[i - 1])
            ex = -200 + (W + 400) * ease(ph) + WOFF[:, None]
            m = np.clip((ex - XS) / 30, 0, 1)[..., None]
            rgb = rgb * m + old * (1 - m)
            band = np.exp(-((XS - ex + 40) / 60) ** 2) * (1 - np.clip(HST * 0.8, 0, 0.85))
            rgb = rgb * (1 - 0.85 * band[..., None])
    if t > total - 0.45:   # loop: dissolve back into the hook
        a = ease((t - (total - 0.45)) / 0.45)
        rgb = rgb * (1 - a) + scene_rgb(lines[0]["_s"], lines[0]) * a
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert("RGBA")
    O = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    caption(O, t)
    d = ImageDraw.Draw(O)
    d.rectangle([30, H - 14, W - 30, H - 4], fill=(20, 18, 24, 60))
    pw = int((W - 60) * t / total)
    if pw > 1:
        d.rectangle([30, H - 14, 30 + pw, H - 4], fill=(20, 18, 24, 235))
        d.rectangle([30 + pw - 10, H - 16, 30 + pw + 2, H - 2], fill=tuple(int(c) for c in RED) + (255,))
    im.alpha_composite(O)
    return im.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), int(float(tt_) * FPS))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=24); print(f"done {total:.1f}s")
