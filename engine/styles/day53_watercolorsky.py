"""Day 53 — WATERCOLOR-SKY style (a fluffy cumulus cloud weighs about as much as 100 elephants).
A picture-book sky painted wet-in-wet, full bleed — no page, no journal, just sky:
- paper: warm cold-press white with embossed tooth; every colour is a transparent wash multiplied into it;
- washes: computed at half resolution as pigment density (wet-in-wet variation, granulation that settles into the
  tooth, darker pooled 'hard edges' where a wash dried), then upscaled — soft by nature;
- clouds are *negative painting*: the cerulean sky is painted around them, they stay paper-white, with a violet-grey
  shadow wash pooled along their flat bases and a thin warm sienna rim on top;
- elephants are clouds too: elephant silhouettes with puffy backs, painted the same way, drifting as a herd;
- props in rigger-brush indigo line + washes: isometric 1 km cube, 1 m³ cube with a single drop, a billion-cell grid,
  a hanging balance scale (cloud vs elephants), a magnifier full of droplets lifted by rose warm-air strokes;
- type: Fraunces (soft, black) laid in as wash letters with pooled edges, Patrick Hand for small painted notes;
- cuts: a water bloom — the new scene floods outward from a point with a dark tide-line at its front;
- ending: a wash track FAKE → TRUE; the knob is a little cloud, the track floods cerulean behind it.
Music: original F-major celesta/music-box over a soft pad, water drips and wind on cuts.
Usage: python3 engine/styles/day53_watercolorsky.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
S = 0.5; LW, LH = int(W * S), int(H * S)

_F = {}
def F(kind, s, wght=900):
    k = (kind, int(s), wght)
    if k not in _F:
        if kind == "h":
            f = ImageFont.truetype(f"{FONTS}/PatrickHand-Regular.ttf", int(s))
        else:
            f = ImageFont.truetype(f"{FONTS}/Fraunces-VF.ttf", int(s))
            try: f.set_variation_by_axes([144, wght, 100, 0])
            except Exception: pass
        _F[k] = f
    return _F[k]

# pigment colours (what the pigment looks like at full strength on white)
CERU = np.array([62, 132, 198], np.float32)
ULTRA = np.array([40, 52, 128], np.float32)
VIOL = np.array([128, 112, 160], np.float32)
ROSE = np.array([206, 70, 98], np.float32)
SIEN = np.array([222, 150, 86], np.float32)
SAP = np.array([96, 150, 128], np.float32)
INDIGO = np.array([30, 36, 74], np.float32)
PAPER_C = np.array([251, 247, 238], np.float32)

# ---------- noise ----------
def fbm(h, w, seed, octaves=4, base=64):
    r = np.random.default_rng(seed); out = np.zeros((h, w), np.float32); amp = 1.0
    for o in range(octaves):
        s = max(2, base >> o)
        n = r.normal(0, 1, (h // s + 2, w // s + 2)).astype(np.float32)
        out += cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC) * amp; amp *= 0.5
    return out / 1.6
NZL = fbm(LH, LW, 1, 4, 24)          # edge raggedness (low-res)
NZW = fbm(LH, LW, 2, 3, 110)         # wet-in-wet blooms (low-res)
GR = cv2.GaussianBlur(np.random.default_rng(3).normal(0, 1, (LH, LW)).astype(np.float32), (0, 0), 1.3); GR /= GR.std()
NZF = fbm(H, W, 4, 4, 20)            # full-res edge noise for type and lines
NZWF = cv2.resize(NZW, (W, H))

def smooth(a, b, x):
    u = np.clip((x - a) / (b - a), 0, 1); return u * u * (3 - 2 * u)
def blur(m, s): return cv2.GaussianBlur(m, (0, 0), s)

# ---------- paper ----------
def make_paper():
    n = cv2.GaussianBlur(np.random.default_rng(9).normal(0, 1, (H, W)).astype(np.float32), (0, 0), 1.6)
    n2 = fbm(H, W, 10, 3, 8)
    hgt = n * 0.7 + n2 * 0.5
    gx = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3)
    shade = 1 + 0.028 * np.clip(-(gx * 0.7 + gy * 0.7), -2, 2)
    p = PAPER_C[None, None, :] * shade[..., None]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = 1 - 0.07 * np.clip(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2, 0, 1)
    return (p * vig[..., None]).astype(np.float32), (0.5 + 0.5 * np.tanh(hgt)).astype(np.float32)
PAPER, TOOTH = make_paper()
TOOTH_L = cv2.resize(TOOTH, (LW, LH), interpolation=cv2.INTER_AREA)

# ---------- washes (low-res) ----------
def wash(img, m, col, dens=0.8, edge=0.45, gran=0.1, var=0.22, eb=4):
    e = np.clip(m - blur(m, eb), 0, 1)
    d = m * dens * (1 - var * 0.5 + var * NZW) + e * edge
    d = d * (1 + gran * (GR * 0.6 + (0.5 - TOOTH_L)))
    img *= 1 - np.clip(d, 0, 1)[..., None] * (1 - col / 255)

def sky(img, top, bot, cloud, col=CERU, warm=0.0, warm_col=ROSE):
    yy = np.linspace(0, 1, LH, dtype=np.float32)[:, None]
    cloud = M(cloud)
    d = (top + (bot - top) * yy ** 0.9) * np.ones((1, LW), np.float32)
    d = d * (1 + 0.28 * NZW)
    wash(img, d * (1 - cloud), col, 1.0, 0.32, 0.12, 0.0, 3)
    if warm > 0:
        w = smooth(0.45, 1.0, yy) * np.ones((1, LW), np.float32) * warm
        wash(img, w * (1 - cloud * 0.85), warm_col, 1.0, 0.0, 0.15, 0.2)

def hills(img, y0, col=SAP, dens=0.55, seed=0, amp=40, y1=None):
    xs = np.arange(LW, dtype=np.float32)
    top = (y0 * S + amp * S * np.sin(xs / 90 + seed) + amp * 0.5 * S * np.sin(xs / 37 + seed * 2)).astype(np.float32)
    yy = np.arange(LH, dtype=np.float32)[:, None]
    m = smooth(-1.5, 1.5, yy - top[None, :] + 6 * NZL)
    wash(img, m, col, dens, 0.4, 0.08)
    return m

def shift(m, dx, dy):
    A = np.float32([[1, 0, dx * S], [0, 1, dy * S]])
    return cv2.warpAffine(m, A, (LW, LH), flags=cv2.INTER_LINEAR, borderValue=0)

def vshift(m, k):
    """value k low-res px below (k>0) / above (k<0), zero fill."""
    out = np.zeros_like(m)
    if k > 0: out[:-k] = m[k:]
    elif k < 0: out[-k:] = m[:k]
    else: out[:] = m
    return out

# ---------- clouds ----------
def soften(m, b=2.2, amt=0.24, edge=0.12):
    m = blur(m, b); return blur(smooth(0.5 - edge, 0.5 + edge, m + amt * NZL), 0.8)

def puffs(cx, cy, w, h, seed=0):
    """cumulus outline: a dome envelope of bumps of varied size (big tower in the middle, small curls at the sides),
    a second row of inner bumps, everything cut flat at the base."""
    r = np.random.default_rng(seed); P = []
    base = cy + h * 0.42
    n = 13
    for i in range(n):
        u = (i + 0.5 + r.uniform(-0.25, 0.25)) / n
        env = math.sqrt(max(0.0, 1 - (2 * u - 1) ** 2)) ** 0.8
        rr = w * (0.05 + 0.085 * env) * r.uniform(0.8, 1.2)
        top = base - h * (0.18 + 0.82 * env) * r.uniform(0.86, 1.04)
        P.append((cx - w / 2 + w * u, top + rr, rr))
    for i in range(6):
        u = 0.2 + 0.6 * (i + 0.5) / 6
        env = math.sqrt(max(0.0, 1 - (2 * u - 1) ** 2))
        rr = w * 0.1 * r.uniform(0.8, 1.15)
        P.append((cx - w / 2 + w * u + r.uniform(-15, 15), base - h * 0.55 * env + rr * 0.4, rr))
    return P, base

def cloud_mask(cx, cy, w, h, seed=0):
    P, base = puffs(cx, cy, w, h, seed)
    m = np.zeros((LH, LW), np.float32)
    for x, y, rr in P:
        cv2.circle(m, (int(x * S * 4), int(y * S * 4)), int(rr * S * 4), 1.0, -1, cv2.LINE_AA, 2)
    poly = [(P[1][0], base)] + [(x, y) for x, y, _ in P[1:12]] + [(P[11][0], base)]
    cv2.fillPoly(m, [np.int32(np.array(poly) * S * 4)], 1.0, cv2.LINE_AA, 2)
    r2 = np.random.default_rng(seed + 100)
    for i in range(7):
        x = P[1][0] + (P[11][0] - P[1][0]) * i / 6; rr = w * r2.uniform(0.07, 0.09)
        cv2.circle(m, (int(x * S * 4), int((base - rr * 0.75) * S * 4)), int(rr * S * 4), 1.0, -1, cv2.LINE_AA, 2)
    m[int(base * S):] = 0
    m = soften(m, 1.6, 0.2)
    # inner curls: the lower rim of each upper bump, painted as a soft shadow crescent inside the cloud
    cu = np.zeros((LH, LW), np.float32)
    for x, y, rr in P[:13]:
        cv2.ellipse(cu, (int(x * S * 4), int((y + rr * 0.15) * S * 4)), (int(rr * 0.9 * S * 4), int(rr * 0.9 * S * 4)), 0, 35, 145, 1.0, max(4, int(rr * S * 0.18 * 4)), cv2.LINE_AA, 2)
    cu = blur(cu, 2.5) * blur(vshift(m, 10), 2) * m * 0.8
    return np.stack([m, np.clip(cu, 0, 1)], -1)

def elephant_mask(x, y, s, m=None):
    """cloud elephant facing right; (x, y) = body centre, s = half body length (full-res units)."""
    if m is None: m = np.zeros((LH, LW), np.float32)
    def C(px, py, r): cv2.circle(m, (int(px * S * 4), int(py * S * 4)), max(1, int(r * S * 4)), 1.0, -1, cv2.LINE_AA, 2)
    def E(px, py, a, b, ang=0): cv2.ellipse(m, (int(px * S * 4), int(py * S * 4)), (int(a * S * 4), int(b * S * 4)), ang, 0, 360, 1.0, -1, cv2.LINE_AA, 2)
    E(x, y, s, s * 0.6)
    for i in range(5): C(x - s * 0.78 + s * 0.38 * i, y - s * 0.42 - 0.06 * s * math.sin(i * 2.1), s * 0.26)
    C(x + s * 0.98, y - s * 0.28, s * 0.44)
    E(x + s * 0.72, y - s * 0.14, s * 0.3, s * 0.4, -10)
    tr = [(x + s * 1.3, y - s * 0.15), (x + s * 1.42, y + s * 0.2), (x + s * 1.44, y + s * 0.55), (x + s * 1.32, y + s * 0.72)]
    for k in range(len(tr) - 1):
        for u in np.linspace(0, 1, 6):
            px = tr[k][0] + (tr[k + 1][0] - tr[k][0]) * u; py = tr[k][1] + (tr[k + 1][1] - tr[k][1]) * u
            C(px, py, s * (0.17 - 0.035 * (k + u)))
    for lx in (-0.68, -0.32, 0.3, 0.62):
        cv2.rectangle(m, (int((x + lx * s - s * 0.15) * S), int((y + 0.2 * s) * S)), (int((x + lx * s + s * 0.15) * S), int((y + 1.0 * s) * S)), 1.0, -1)
        C(x + lx * s, y + 0.98 * s, s * 0.15)
    cv2.line(m, (int((x - s * 0.95) * S), int((y - 0.1 * s) * S)), (int((x - s * 1.22) * S), int((y + 0.38 * s) * S)), 1.0, max(1, int(s * 0.07 * S)), cv2.LINE_AA)
    return m

def herd(spots):
    m = np.zeros((LH, LW), np.float32)
    for (x, y, s) in spots: elephant_mask(x, y, s, m)
    return soften(m, 1.6, 0.18)

def M(a): return a[..., 0] if a.ndim == 3 else a

def paint_cloud(img, m, k=34, shadow=0.55, rim=0.3, col=VIOL):
    curl = m[..., 1] if m.ndim == 3 else None; m = M(m)
    below = vshift(m, int(k))
    sh = m * (1 - blur(below, k * 0.3))
    sh = blur(sh, k * 0.22) * m
    # each bump gets a soft shadow on its lower right (inner curls)
    if curl is not None:
        wash(img, np.clip(curl * m, 0, 1), col, shadow * 0.4, 0.0, 0.08, 0.2)
    body = m * smooth(-0.2, 1.0, NZW + 0.3) * 0.12
    wash(img, np.clip(sh * 1.1 + body, 0, 1), col, shadow, 0.18, 0.25, 0.25, 3)
    above = vshift(m, -max(2, int(k * 0.18)))
    rm = blur(m * (1 - above), 1.5)
    wash(img, rm, SIEN, rim, 0.0, 0.1, 0.1)

# ---------- full-res layers: type and rigger lines ----------
_TM = {}
def tmask(s, size, kind="f", wght=900):
    k = (s, size, kind, wght)
    if k not in _TM:
        f = F(kind, size, wght); l, tp, r, b = f.getbbox(s)
        im = Image.new("L", (r - l + 24, b - tp + 24)); ImageDraw.Draw(im).text((12 - l, 12 - tp), s, font=f, fill=255)
        m = np.asarray(im, np.float32) / 255
        h, w = m.shape
        m = blur(m, 1.0)
        m = np.clip((m - 0.5) * 2.4 + 0.5 + 0.18 * NZF[:h, :w], 0, 1)
        e = np.clip(m - blur(m, 3.5), 0, 1)
        var = 0.82 + 0.18 * NZWF[200:200 + h, 100:100 + w] if h < H - 200 and w < W - 100 else 1
        _TM[k] = (np.clip(m * 0.86 * var + e * 0.55, 0, 1).astype(np.float32), w)
    return _TM[k]

def fit(s, size, maxw=980, kind="f"):
    while F(kind, size).getlength(s) > maxw and size > 40: size -= 4
    return size

def put(L, d, x0, y0):
    h, w = d.shape; X0, Y0 = max(0, x0), max(0, y0); X1, Y1 = min(W, x0 + w), min(H, y0 + h)
    if X1 <= X0 or Y1 <= Y0: return
    sub = d[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
    L[Y0:Y1, X0:X1] = 1 - (1 - L[Y0:Y1, X0:X1]) * (1 - sub)

def text(L, s, size, x, y, anchor="c", prog=1.0, kind="f", alpha=1.0, maxw=980):
    """y = top of the box; wet reveal left -> right."""
    if prog <= 0: return
    size = fit(s, size, maxw, kind)
    m, w = tmask(s, size, kind)
    h = m.shape[0]
    x0 = int(x - w / 2) if anchor == "c" else (int(x) - 12 if anchor == "l" else int(x - w + 12))
    if prog < 1:
        xs = np.arange(w, dtype=np.float32)[None, :]
        front = prog * (w + 120) - 60 + 30 * NZF[:h, :w]
        m = m * np.clip((front - xs) / 40, 0, 1)
    put(L, m * alpha, x0, int(y))

def line(L, pts, w=4, dens=0.85, prog=1.0, dash=0):
    pts = np.asarray(pts, np.float32)
    if prog <= 0 or len(pts) < 2: return
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)]); tot = cum[-1]
    n = max(2, int(tot / 3)); s = np.linspace(0, tot * min(1, prog), n)
    P = np.stack([np.interp(s, cum, pts[:, 0]), np.interp(s, cum, pts[:, 1])], 1)
    x0, y0 = int(P[:, 0].min()) - 12, int(P[:, 1].min()) - 12; x1, y1 = int(P[:, 0].max()) + 12, int(P[:, 1].max()) + 12
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if X1 - X0 < 2 or Y1 - Y0 < 2: return
    m = np.zeros((Y1 - Y0, X1 - X0), np.float32)
    Q = ((P - [X0, Y0]) * 4).astype(np.int32)
    if dash:
        k = max(1, int(dash / 3))
        for i in range(0, len(Q) - 1, 2 * k):
            cv2.polylines(m, [Q[i:i + k + 1]], False, 1.0, w, cv2.LINE_AA, 2)
    else:
        cv2.polylines(m, [Q], False, 1.0, w, cv2.LINE_AA, 2)
    m = blur(m, 0.7)
    m = np.clip(m * (0.85 + 0.3 * NZF[Y0:Y1, X0:X1]), 0, 1)
    put(L, m * dens, X0, Y0)

def blob(L, x, y, r, dens=0.8):
    """small round wash dot with a pooled edge (full-res)."""
    R = int(r + 6); m = np.zeros((2 * R, 2 * R), np.float32)
    cv2.circle(m, (R * 4, R * 4), int(r * 4), 1.0, -1, cv2.LINE_AA, 2)
    m = blur(m, 1.0); e = np.clip(m - blur(m, 2.5), 0, 1)
    put(L, np.clip(m * dens * 0.75 + e * 0.6, 0, 1), int(x - R), int(y - R))

def wstart(ln, k):
    i = min(ln["_w0"] + k, ln["_w1"] - 1); return words[i][1] - ln["_s"]

# ---------- cached masks ----------
_MC = {}
def cached(key, fn):
    if key not in _MC: _MC[key] = fn()
    return _MC[key]

def L0(): return np.ones((LH, LW, 3), np.float32)
def Z(): return np.zeros((H, W), np.float32)

# ---------- scenes: return (img_lowres_transmittance, layers{col: density}) ----------
def hook(ln, lt, dur, t):
    img = L0()
    c = shift(cached("hc", lambda: cloud_mask(540, 930, 860, 560, 1)), 18 * math.sin(t * 0.6), 6 * math.sin(t * 0.9))
    hx = -60 + 26 * t
    hd = shift(cached("hh", lambda: herd([(150, 1350, 62), (370, 1330, 74), (610, 1352, 60), (830, 1336, 70)])), hx, 5 * math.sin(t * 2))
    allc = np.maximum(M(c), hd)
    sky(img, 0.55, 0.28, allc, warm=0.25)
    paint_cloud(img, c, 28, 0.5, 0.32)
    paint_cloud(img, hd, 16, 0.6, 0.25)
    D, R = Z(), Z()
    text(D, "THIS FLUFFY CLOUD", 118, W / 2, 150)
    text(D, "WEIGHS AS MUCH AS", 92, W / 2, 300)
    text(R, "100 ELEPHANTS", 140, W / 2, 420)
    for (x, y, s) in [(150, 1350, 62), (370, 1330, 74), (610, 1352, 60), (830, 1336, 70)]:
        blob(D, x + s * 1.1 + hx, y - s * 0.38 + 5 * math.sin(t * 2), 5, 0.9)
    return img, {"D": D, "R": R}

def why(ln, lt, dur, t):
    img = L0()
    bob = 14 * math.sin(lt * 2.2)
    c = shift(cached("wc", lambda: cloud_mask(600, 760, 760, 470, 2)), 10 * math.sin(lt), bob)
    sky(img, 0.6, 0.25, c, warm=0.45, warm_col=SIEN)
    paint_cloud(img, c, 36, 0.6, 0.3)
    hills(img, 1300, SAP, 0.32, 1.0, 36)
    hills(img, 1420, SAP, 0.36, 3.0, 26)
    # little house
    hm = cached("house", lambda: (lambda m: (cv2.rectangle(m, (int(300 * S), int(1250 * S)), (int(440 * S), int(1360 * S)), 1.0, -1), m)[1])(np.zeros((LH, LW), np.float32)))
    wash(img, soften(hm, 0.8, 0.08, 0.2), SIEN, 0.5, 0.4)
    rf = cached("roof", lambda: (lambda m: (cv2.fillPoly(m, [np.int32(np.array([(280, 1258), (370, 1180), (460, 1258)]) * S)], 1.0), m)[1])(np.zeros((LH, LW), np.float32)))
    wash(img, soften(rf, 0.8, 0.08, 0.2), ROSE, 0.75, 0.5)
    D, R = Z(), Z()
    line(D, [(300, 1250), (440, 1250), (440, 1360), (300, 1360), (300, 1250)], 3, 0.7)
    line(D, [(280, 1258), (370, 1180), (460, 1258)], 3, 0.7)
    line(D, [(355, 1360), (355, 1305), (385, 1305), (385, 1360)], 3, 0.7)
    a = eout(lt / 0.8)
    line(R, [(560, 1020 + bob), (470, 1170)], 6, 0.85, a, dash=24)
    if a > 0.9:
        line(R, [(470, 1170), (476, 1128)], 6, 0.85); line(R, [(470, 1170), (508, 1150)], 6, 0.85)
    q = back(min(1, max(0, (lt - 0.5) / 0.4)))
    if q > 0: text(R, "?", int(230 * max(0.3, q)), 800, 1000 + bob, alpha=min(1, q))
    text(D, "SO WHY DOESN'T", 112, W / 2, 140, prog=eout(lt / 0.35))
    text(R, "IT FALL?", 160, W / 2, 290, prog=eout((lt - 0.15) / 0.4))
    return img, {"D": D, "R": R}

def iso(i, j, k, a, ox, oy):
    return (ox + (i - j) * a * 0.866, oy + (i + j) * a * 0.5 - k * a)

def cube_lines(D, R, a, ox, oy, prog, label="1 km", lsize=64, lt=0.0):
    V = {(i, j, k): iso(i, j, k, a, ox, oy) for i in (0, 1) for j in (0, 1) for k in (0, 1)}
    back_e = [((0, 0, 0), (1, 0, 0)), ((0, 0, 0), (0, 1, 0)), ((0, 0, 0), (0, 0, 1))]
    front = [((1, 0, 0), (1, 1, 0)), ((0, 1, 0), (1, 1, 0)), ((1, 1, 0), (1, 1, 1)), ((1, 0, 0), (1, 0, 1)), ((0, 1, 0), (0, 1, 1)),
             ((0, 0, 1), (1, 0, 1)), ((0, 0, 1), (0, 1, 1)), ((1, 0, 1), (1, 1, 1)), ((0, 1, 1), (1, 1, 1))]
    for n, (p, q) in enumerate(back_e): line(D, [V[p], V[q]], 3, 0.45, prog * 1.5 - n * 0.1, dash=18)
    for n, (p, q) in enumerate(front): line(D, [V[p], V[q]], 5, 0.9, prog * 2.2 - n * 0.12)
    if label and prog > 0.6:
        al = min(1, (prog - 0.6) / 0.3)
        a1 = V[(1, 0, 0)]; a2 = V[(1, 1, 0)]; a3 = V[(0, 1, 0)]
        text(R, label, lsize, (a1[0] + a2[0]) / 2 + 70, (a1[1] + a2[1]) / 2 + 10, kind="h", alpha=al)
        text(R, label, lsize, (a3[0] + a2[0]) / 2 - 70, (a3[1] + a2[1]) / 2 + 10, kind="h", alpha=al)
        b1 = V[(1, 0, 1)]
        text(R, label, lsize, a1[0] + 90, (a1[1] + b1[1]) / 2 - 30, kind="h", alpha=al)
    return V

def cube(ln, lt, dur, t):
    img = L0()
    c = shift(cached("cc", lambda: cloud_mask(540, 1010, 640, 430, 3)), 8 * math.sin(t * 0.8), 5 * math.sin(t * 1.1))
    sky(img, 0.45, 0.3, c, col=CERU)
    paint_cloud(img, c, 30, 0.55, 0.3)
    D, R = Z(), Z()
    cube_lines(D, R, 400, 540, 1010, eout(lt / 1.4), "1 km", 66)
    text(D, "1 KM WIDE,", 124, W / 2, 140, prog=eout(lt / 0.35))
    text(D, "TALL AND DEEP", 124, W / 2, 290, prog=eout((lt - 0.15) / 0.4))
    return img, {"D": D, "R": R}

def drop(ln, lt, dur, t):
    img = L0()
    sky(img, 0.32, 0.22, np.zeros((LH, LW), np.float32), col=CERU, warm=0.15)
    mist = cached("mist", lambda: soften((lambda m: (cv2.fillPoly(m, [np.int32(np.array([iso(i, j, k, 330, 540, 1030) for (i, j, k) in
        [(0, 0, 0), (1, 0, 0), (1, 0, 1), (1, 1, 1), (0, 1, 1), (0, 1, 0)]]) * S)], 1.0), m)[1])(np.zeros((LH, LW), np.float32)), 6, 0.3, 0.3))
    wash(img, mist * (0.6 + 0.4 * NZW), VIOL, 0.22, 0.1)
    D, R, B = Z(), Z(), Z()
    V = cube_lines(D, R, 330, 540, 1030, eout(lt / 1.0), None)
    if lt > 0.6:
        al = min(1, (lt - 0.6) / 0.3); a1 = V[(1, 0, 0)]; a2 = V[(1, 1, 0)]
        text(D, "1 m", 60, (a1[0] + a2[0]) / 2 + 80, (a1[1] + a2[1]) / 2 + 6, kind="h", alpha=al)
    # one drop
    u = back(min(1, max(0, (lt - 0.5) / 0.45)), 1.4)
    if u > 0:
        cx, cy = 540, 1050 + 8 * math.sin(lt * 3)
        r = 46 * u
        m = np.zeros((260, 200), np.float32)
        cv2.circle(m, (100 * 4, 160 * 4), int(r * 4), 1.0, -1, cv2.LINE_AA, 2)
        cv2.fillPoly(m, [np.int32(np.array([(100 - r * 0.88, 160 - r * 0.45), (100, 160 - r * 2.2), (100 + r * 0.88, 160 - r * 0.45)]) * 4)], 1.0, cv2.LINE_AA, 2)
        m = blur(m, 1.2); hl = np.zeros_like(m)
        cv2.ellipse(hl, (int((100 - r * 0.35) * 4), int((160 - r * 0.2) * 4)), (int(r * 0.16 * 4) + 1, int(r * 0.3 * 4) + 1), 20, 0, 360, 1.0, -1, cv2.LINE_AA, 2)
        hl = blur(hl, 1.5)
        e = np.clip(m - blur(m, 4), 0, 1)
        put(B, np.clip((m * 0.8 + e * 0.7) * (1 - hl), 0, 1), int(cx - 100), int(cy - 160))
        if u >= 1:
            al = min(1, (lt - 0.95) / 0.3)
            line(R, [(578, 1015), (850, 770)], 4, 0.8, al)
            text(R, "≈ ½ gram", 70, 880, 680, kind="h", alpha=al)
    text(D, "1 CUBIC METER", 120, W / 2, 140, prog=eout(lt / 0.35))
    text(R, "≈ ½ GRAM OF WATER", 104, W / 2, 290, prog=eout((lt - wstart(ln, 4) + 0.1) / 0.4))
    return img, {"D": D, "R": R, "B": B}

GRID = None
def billion(ln, lt, dur, t):
    global GRID
    img = L0()
    cm = cached("bc", lambda: cloud_mask(540, 1060, 920, 640, 7))
    c = shift(cm, 0, 6 * math.sin(t * 1.2))
    sky(img, 0.7, 0.4, c, col=CERU, warm=0.2, warm_col=VIOL)
    paint_cloud(img, c, 40, 0.5, 0.3)
    D, R = Z(), Z()
    if GRID is None:
        GRID = np.zeros((H, W), np.float32)
        for x in range(0, W, 34): cv2.line(GRID, (x, 0), (x, H), 1.0, 2, cv2.LINE_AA)
        for y in range(0, H, 34): cv2.line(GRID, (0, y), (W, y), 1.0, 2, cv2.LINE_AA)
        GRID = blur(GRID, 0.6) * (0.75 + 0.25 * NZF)
        YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
        globals()["GD"] = np.sqrt((XX - 540) ** 2 + (YY - 1000) ** 2) + 60 * NZF
    p = eout(lt / 1.8)
    cu = cv2.resize(M(c), (W, H), interpolation=cv2.INTER_LINEAR)
    rev = np.clip((p * 700 - GD) / 40, 0, 1)
    D[:] = np.clip(GRID * cu * rev * 0.45, 0, 1)
    v = int(1_000_000_000 * min(1, (lt / 1.6) ** 2.2))
    text(D, "1 CLOUD =", 104, W / 2, 140, prog=eout(lt / 0.3))
    text(R, f"{v:,}", 136, W / 2, 270)
    text(D, "CUBIC METERS", 92, W / 2, 440, prog=eout((lt - 0.3) / 0.4))
    return img, {"D": D, "R": R}

def scale(ln, lt, dur, t):
    img = L0()
    a = 0.28 * math.exp(-lt * 1.3) * math.cos(lt * 4.2)    # beam angle (left side down when > 0)
    px, py, Lb, hang = 540, 640, 330, 400
    le = (px - Lb * math.cos(a), py + Lb * math.sin(a)); re = (px + Lb * math.cos(a), py - Lb * math.sin(a))
    lp = (le[0], le[1] + hang); rp = (re[0], re[1] + hang)
    cm = cached("sc", lambda: cloud_mask(160, 1040, 290, 240, 6))
    c = shift(cm, lp[0] - 160, lp[1] - 1135)
    em = cached("se", lambda: herd([(880, 1010, 46), (1010, 1018, 42), (940, 950, 44)]))
    e = shift(em, rp[0] - 945, rp[1] - 1110)
    allc = np.maximum(M(c), e)
    sky(img, 0.5, 0.3, allc, col=CERU, warm=0.4, warm_col=ROSE)
    paint_cloud(img, c, 24, 0.55, 0.3)
    paint_cloud(img, e, 12, 0.62, 0.25)
    # pans (sienna bowls) + beam wash
    pm = np.zeros((LH, LW), np.float32)
    for (x, y) in (lp, rp):
        cv2.ellipse(pm, (int(x * S * 4), int(y * S * 4)), (int(150 * S * 4), int(42 * S * 4)), 0, 0, 180, 1.0, -1, cv2.LINE_AA, 2)
    pm = blur(pm, 1.0)
    wash(img, pm, SIEN, 0.7, 0.5)
    D, R = Z(), Z()
    line(D, [(px, 470), (px, py)], 5, 0.9)
    line(D, [le, re], 10, 0.9)
    blob(D, px, py, 14, 0.9)
    for (end, pan) in ((le, lp), (re, rp)):
        line(D, [end, (pan[0] - 145, pan[1])], 3, 0.75); line(D, [end, (pan[0] + 145, pan[1])], 3, 0.75)
        line(D, [(pan[0] - 152, pan[1]), (pan[0] + 152, pan[1])], 4, 0.85)
    # pointer
    line(R, [(px, py), (px + 140 * math.sin(a), py - 140 * math.cos(a))], 5, 0.85)
    for (x, y, s) in [(880, 1010, 46), (1010, 1018, 42), (940, 950, 44)]:
        blob(D, x + s * 1.1 + rp[0] - 945, y - s * 0.38 + rp[1] - 1110, 4, 0.9)
    lvl = min(1, max(0, (lt - 1.2) / 0.3))
    text(R, "× 100", 72, rp[0], rp[1] + 70, kind="h")
    text(D, "1 cloud", 64, lp[0], lp[1] + 70, kind="h")
    text(D, "ABOUT", 92, W / 2, 120, prog=eout(lt / 0.3))
    text(R, "500,000 KG", 150, W / 2, 230, prog=eout((lt - 0.1) / 0.4))
    text(D, "≈ 1.1 million lb", 62, W / 2, 1290, kind="h", alpha=lvl)
    return img, {"D": D, "R": R}

DROPS = np.random.default_rng(77).uniform(0, 1, (80, 4)).astype(np.float32)
def floaty(ln, lt, dur, t):
    img = L0()
    c = shift(cached("fc", lambda: cloud_mask(540, 1000, 1060, 760, 8)), 10 * math.sin(t * 0.7), 6 * math.sin(t))
    sky(img, 0.55, 0.3, c, col=CERU, warm=0.2)
    paint_cloud(img, c, 44, 0.5, 0.3)
    cx, cy, r = 520, 960, 290
    lens = cached("lens", lambda: blur((lambda m: (cv2.circle(m, (int(cx * S * 4), int(cy * S * 4)), int(r * S * 4), 1.0, -1, cv2.LINE_AA, 2), m)[1])(np.zeros((LH, LW), np.float32)), 1.0))
    # inside the lens: pale mist (wet-in-wet violet + cerulean)
    wash(img, lens * (0.5 + 0.5 * NZW), CERU, 0.16, 0.0)
    D, R, B = Z(), Z(), Z()
    zin = eout(lt / 0.5)
    for k, (u, v, s, ph) in enumerate(DROPS):
        ang = u * 2 * math.pi; rad = math.sqrt(v) * (r - 30)
        x = cx + math.cos(ang) * rad + 6 * math.sin(lt * 3 + ph * 9)
        y = cy + math.sin(ang) * rad - ((lt * 26 + ph * 60) % 60) + 30
        if (x - cx) ** 2 + (y - cy) ** 2 < (r - 16) ** 2:
            blob(B, x, y, (4 + 7 * s) * zin, 0.8)
    for k in range(4):
        ph = (lt * 0.55 + k / 4) % 1
        x0 = cx - 180 + k * 120; y0 = cy + 200 - ph * 380
        al = math.sin(ph * math.pi)
        pts = [(x0 + 14 * math.sin(q * 0.8 + k), y0 - q * 14) for q in range(10)]
        if all((p[0] - cx) ** 2 + (p[1] - cy) ** 2 < (r - 10) ** 2 for p in (pts[0], pts[-1])):
            line(R, pts, 6, 0.8 * al)
            tip = pts[-1]
            line(R, [tip, (tip[0] - 16, tip[1] + 18)], 6, 0.8 * al); line(R, [tip, (tip[0] + 16, tip[1] + 18)], 6, 0.8 * al)
    ring = np.zeros((H, W), np.float32)
    cv2.circle(ring, (cx * 4, cy * 4), r * 4, 1.0, 14, cv2.LINE_AA, 2)
    D[:] = np.maximum(D, blur(ring, 0.8) * 0.9)
    line(D, [(cx + r * 0.72, cy + r * 0.72), (cx + r * 1.2, cy + r * 1.2)], 26, 0.9)
    gw = wstart(ln, 8)
    text(D, "TINY DROPLETS", 120, W / 2, 140, prog=eout(lt / 0.35))
    text(R, "+ RISING WARM AIR", 100, W / 2, 290, prog=eout((lt - gw) / 0.4))
    text(R, "warm air", 62, 230, 1250, kind="h", alpha=min(1, max(0, (lt - gw - 0.2) / 0.3)))
    return img, {"D": D, "R": R, "B": B}

def end(ln, lt, dur, t):
    img = L0()
    c = shift(cached("ec", lambda: cloud_mask(300, 760, 420, 260, 11)), 20 * math.sin(t * 0.5), 0)
    c2 = shift(cached("ec2", lambda: cloud_mask(840, 1430, 300, 190, 12)), -15 * math.sin(t * 0.5), 0)
    allc = np.maximum(M(c), M(c2))
    sky(img, 0.45, 0.2, allc, col=CERU, warm=0.7, warm_col=ROSE)
    paint_cloud(img, c, 22, 0.5, 0.35); paint_cloud(img, c2, 20, 0.5, 0.35)
    cl = ln["scene"].get("click_at", 0.5)
    u = back(min(1, max(0, (lt - cl) / 0.45)), 1.2)
    kx = 270 + (810 - 270) * u
    tm = cached("track", lambda: soften((lambda m: (cv2.rectangle(m, (int(220 * S), int(880 * S)), (int(860 * S), int(980 * S)), 1.0, -1), m)[1])(np.zeros((LH, LW), np.float32)), 2, 0.2, 0.15))
    wash(img, tm, VIOL, 0.35, 0.4)
    fx = (kx + 10) * S
    flood = tm * np.clip((fx - np.arange(LW, dtype=np.float32)[None, :] + 14 * NZL) / 6, 0, 1)
    wash(img, flood, CERU, 0.85, 0.6)
    km = shift(cached("knob", lambda: cloud_mask(270, 940, 230, 170, 13)), kx - 270, -8 * math.sin(lt * 4) * (1 - u))
    img_k = M(km)
    # paint knob: lift (paper white) then shade
    img[:] = img * (1 - img_k[..., None]) + img_k[..., None]
    paint_cloud(img, km, 14, 0.6, 0.3)
    D, R = Z(), Z()
    fa = 1 - 0.75 * min(1, max(0, (lt - cl) / 0.3))
    text(D, "FAKE", 84, 300, 1020, alpha=fa)
    text(R, "TRUE", 84, 780, 1020, alpha=0.3 + 0.7 * min(1, max(0, (lt - cl - 0.25) / 0.2)))
    text(D, "SOUNDS FAKE?", 128, W / 2, 200)
    text(R, "IT'S TRUE.", 150, W / 2, 370, prog=eout((lt - cl - 0.3) / 0.35))
    text(D, "Follow for more", 84, W / 2, 1170, kind="h", prog=eout((lt - 0.9) / 0.5))
    return img, {"D": D, "R": R}

SCENES = {"hook": hook, "why": why, "cube": cube, "drop": drop, "billion": billion, "scale": scale, "float": floaty, "end": end}

# ---------- narration + music ----------
voice, words, total = narrate(spec, lead=0.08)
n = len(voice); music = np.zeros(n, np.float32); rng = np.random.default_rng(53)

def bell(f, dur=2.2, amp=1.0):
    s = np.arange(int(dur * SR)) / SR
    sig = (np.sin(2 * np.pi * f * s) + 0.35 * np.sin(2 * np.pi * f * 2.0 * s) * np.exp(-s * 3) + 0.18 * np.sin(2 * np.pi * f * 3.01 * s) * np.exp(-s * 6))
    return (amp * sig * np.exp(-s * 2.4) * np.clip(s / 0.004, 0, 1)).astype(np.float32)

def pad(freqs, dur):
    s = np.arange(int(dur * SR)) / SR
    sig = sum(np.sin(2 * np.pi * f * s) + 0.6 * np.sin(2 * np.pi * f * 1.003 * s) for f in freqs)
    env = np.clip(s / 0.8, 0, 1) * np.clip((dur - s) / 0.8, 0, 1)
    return (sig * env / len(freqs)).astype(np.float32)

def drip(at, gain=0.12):
    s = np.arange(int(0.18 * SR)) / SR
    f = 500 + 1400 * (1 - np.exp(-s * 40))
    place(music, at, (np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-s * 26)).astype(np.float32), gain)

CH = [(174.61, 220.0, 261.63), (146.83, 174.61, 220.0), (116.54, 146.83, 174.61), (130.81, 164.81, 196.0)]   # F Dm Bb C
MEL = [698.46, 880.0, 1046.5, 880.0, 783.99, 698.46, 587.33, 659.25, 698.46, 880.0, 783.99, 659.25, 587.33, 523.25, 587.33, 698.46]
BEAT = 0.5
for k in range(int(total / 2.0) + 1):
    place(music, k * 2.0, pad(CH[k % 4], 2.6), 0.07)
    place(music, k * 2.0, bell(CH[k % 4][0] / 2, 2.4), 0.06)
for k in range(int(total / BEAT)):
    if k % 4 != 3: place(music, k * BEAT, bell(MEL[k % 16], 1.6), 0.05)
hook_hit(music, 0.28); drip(0.02, 0.14)
for i, ln in enumerate(spec["lines"]):
    s0 = ln["_s"]; st = ln["scene"]["type"]
    if i > 0: whoosh(music, s0 - 0.1, 0.07, 0.45); drip(s0 - 0.05, 0.1)
    if st == "billion":
        for k in range(16): drip(s0 + k * 0.1, 0.035)
    if st == "drop": drip(s0 + 0.55, 0.16)
    if st == "scale":
        for k in range(3): place(music, s0 + 0.2 + k * 0.75, bell(220.0 * (1.5 if k % 2 else 1), 1.2), 0.05)
    if st == "end":
        c = s0 + ln["scene"].get("click_at", 0.5)
        drip(c + 0.4, 0.18)
        for j, fq in enumerate((698.46, 880.0, 1046.5, 1396.9)): place(music, c + 0.45 + j * 0.08, bell(fq, 1.8), 0.08)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.45)

# ---------- compositing ----------
LAYC = {"D": INDIGO, "R": np.array([178, 34, 72], np.float32), "B": CERU * 0.8}
groups = caption_groups(words, 3)
CREAM = (252, 248, 238)
def caption(O, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 76; f = F("f", size, 700)
    while f.getlength(" ".join(ws)) > W - 220 and size > 44: size -= 4; f = F("f", size, 700)
    gap = f.getlength(" ") + 16
    tw_ = sum(f.getlength(w) for w in ws) + gap * (len(ws) - 1); x = (W - tw_) / 2; y = 1590
    d = ImageDraw.Draw(O)
    d.rounded_rectangle([x - 38 + 6, y - 22 + 8, x + tw_ + 38 + 6, y + size + 28 + 8], radius=26, fill=(40, 52, 128, 70))
    d.rounded_rectangle([x - 38, y - 22, x + tw_ + 38, y + size + 28], radius=26, fill=CREAM + (246,), outline=(30, 36, 74, 255), width=4)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]; wl = f.getlength(w)
        if on: d.rounded_rectangle([x - 10, y - 6, x + wl + 10, y + size + 14], radius=14, fill=(36, 92, 166, 255))
        d.text((x, y - size * 0.1), w, font=f, fill=CREAM if on else (30, 36, 74)); x += wl + gap

def scene_rgb(t, ln):
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img, lay = SCENES[ln["scene"]["type"]](ln, lt, dur, t)
    up = cv2.resize(img, (W, H), interpolation=cv2.INTER_CUBIC)
    out = PAPER * up
    for k, L in lay.items():
        out *= 1 - L[..., None] * (1 - LAYC[k] / 255)
    return out

_DF = {}
def dfield(ox, oy):
    k = (ox, oy)
    if k not in _DF:
        YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
        _DF[k] = np.sqrt((XX - ox) ** 2 + (YY - oy) ** 2) + 110 * NZF
    return _DF[k]

ORIG = [(300, 700), (780, 1100), (540, 500), (250, 1200)]
def frame(t, fi):
    lines = spec["lines"]; ln = active_line(spec, t) or lines[0]; i = lines.index(ln)
    rgb = scene_rgb(t, ln)
    if i > 0:   # water bloom: new scene floods out from a point, dark tide-line at the front
        ph = (t - (ln["_s"] - 0.12)) / 0.45
        if ph < 1:
            old = scene_rgb(ln["_s"] - 0.12, lines[i - 1])
            D_ = dfield(*ORIG[i % len(ORIG)])
            r = 2400 * eout(ph) ** 1.1
            m = np.clip((r - D_) / 30, 0, 1)[..., None]
            rgb = rgb * m + old * (1 - m)
            tide = np.exp(-((D_ - r + 14) / 16) ** 2) * (0.55 * (1 - ph))
            rgb = rgb * (1 - tide[..., None] * (1 - VIOL / 255))
    if t > total - 0.45:
        a = ease((t - (total - 0.45)) / 0.45)
        rgb = rgb * (1 - a) + scene_rgb(lines[0]["_s"], lines[0]) * a
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert("RGBA")
    O = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    caption(O, t)
    d = ImageDraw.Draw(O)
    d.rounded_rectangle([30, H - 16, W - 30, H - 6], radius=5, fill=(30, 36, 74, 70))
    pw = int((W - 60) * t / total)
    if pw > 1:
        d.rounded_rectangle([30, H - 16, 30 + pw, H - 6], radius=5, fill=(36, 92, 166, 240))
        d.ellipse([30 + pw - 11, H - 22, 30 + pw + 11, H], fill=(206, 70, 98, 255))
    im.alpha_composite(O)
    return im.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), int(float(tt_) * FPS))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=24); print(f"done {total:.1f}s")
