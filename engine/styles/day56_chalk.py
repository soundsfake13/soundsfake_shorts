"""Day 56 — CHALK-SKELETON style (chickens are close living relatives of T. rex).
A natural-history museum classroom blackboard that draws itself:
- slate-green board with erased-chalk clouds, ghosts of old lessons, vignette, a wooden frame and chalk tray
  (with chalk sticks) under the captions;
- every mark is chalk: polylines and text drawn into per-colour masks, then broken up by a two-variant
  grain texture (dry, skipping strokes) and 'boiled' at ~7.5 fps (points jitter like hand redraws);
  palette: white, butter-yellow, pink and sky-blue chalk;
- skeletons are bone line-drawings built from named parts (skull, jaw, neck, back, tail, ribs, arm/wing,
  pelvis, legs) resampled to the same point count, so a T. rex skeleton can MORPH into a chicken skeleton;
  vertebra ticks along the spine, teeth that fade out, orbit circles;
- other chalk diagrams: a dinosaur family tree with crossed-out branches and the living bird branch,
  a hatched femur with a magnifier showing the collagen triple helix, a comparison table with X marks and circles;
- type: Caveat Brush headlines, Patrick Hand labels, Kalam Bold captions (white, active word yellow + underline),
  all written on left-to-right;
- cuts: a felt board-eraser sweeps across leaving a dust smear;
- ending: chalk-drawn switch FAKE -> TRUE (hatched knob slides, TRUE gets circled), dissolves back into the hook.
Music: original G-major plucked 'museum walk' (Karplus-Strong plucks + upright-style bass, soft brushes),
chalk squeaks on headlines, eraser swishes on cuts.
Usage: python3 engine/styles/day56_chalk.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]

WHT = (238, 238, 230); YEL = (250, 226, 120); PNK = (246, 150, 172); BLU = (140, 200, 236); DIM = (150, 165, 158)
COLS = {"w": WHT, "y": YEL, "p": PNK, "b": BLU, "d": DIM}
BRUSH = "CaveatBrush-Regular.ttf"; HAND = "PatrickHand-Regular.ttf"; KAL = "Kalam-Bold.ttf"

_F = {}
def F(name, s):
    k = (name, int(s))
    if k not in _F: _F[k] = ImageFont.truetype(f"{FONTS}/{name}", int(s))
    return _F[k]

_TM = {}
def tmask(s, font, size):
    k = (s, font, int(size))
    if k in _TM: return _TM[k]
    f = F(font, size); tw = f.getlength(s); asc, desc = f.getmetrics()
    im = Image.new("L", (int(tw) + 60, asc + desc + 60), 0); ImageDraw.Draw(im).text((30, 30), s, font=f, fill=255)
    m = np.asarray(im)
    ys = np.where(m.max(1) > 5)[0]; xs = np.where(m.max(0) > 5)[0]
    m = m[ys[0]: ys[-1] + 1, xs[0]: xs[-1] + 1].copy()
    _TM[k] = m; return m

# ---------- board ----------
def fbm(h, w, seed, oct_=5, base=4):
    r = np.random.default_rng(seed); acc = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(oct_):
        gh = max(2, int(base * 2 ** o)); gw = max(2, int(base * 2 ** o * w / h))
        acc += amp * cv2.resize(r.normal(0, 1, (gh, gw)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
        tot += amp; amp *= 0.55
    return acc / tot

YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
FR = 26            # wooden frame width (left/right/top)
TRAY = 1742        # chalk tray top
def make_board():
    base = np.array((34, 50, 45), np.float32)
    n = fbm(H, W, 1, 6, 3)
    img = np.ones((H, W, 3), np.float32) * base
    img *= (1 + 0.10 * n)[..., None]
    # erased chalk clouds: long horizontal smears
    sm = fbm(H // 4, W // 4, 2, 4, 3); sm = cv2.resize(sm, (W, H)); sm = cv2.GaussianBlur(sm, (0, 0), 6)
    sm = cv2.resize(cv2.resize(sm, (W // 8, H), interpolation=cv2.INTER_AREA), (W, H), interpolation=cv2.INTER_LINEAR)
    img += np.clip(sm * 40, 0, 26)[..., None] * np.array((0.9, 1.0, 0.95))
    # ghosts of old lessons (blurred faint chalk writing)
    gh = Image.new("L", (W, H), 0); d = ImageDraw.Draw(gh); r = np.random.default_rng(5)
    for s in ["Cretaceous", "femur", "Theropoda", "Aves", "66 mya", "x = 3", "Jurassic", "phylogeny", "tibia", "skull"]:
        d.text((int(r.uniform(40, W - 300)), int(r.uniform(80, H - 400))), s, font=F(HAND, int(r.uniform(50, 90))), fill=255)
    g = cv2.GaussianBlur(np.asarray(gh).astype(np.float32) / 255, (0, 0), 7)
    img += g[..., None] * 8
    # dust grain
    img += np.random.default_rng(3).normal(0, 3.0, (H, W, 1)).astype(np.float32)
    # vignette
    v = ((XX - W / 2) / W) ** 2 + ((YY - H * 0.45) / H) ** 2
    img *= (1 - 0.5 * v)[..., None]
    # wooden frame
    wood = fbm(H, W, 7, 4, 4)
    grain = 0.5 + 0.5 * np.sin(YY * 0.02 + wood * 6 + XX * 0.001)
    wcol = np.array((122, 80, 46), np.float32)[None, None] * (0.78 + 0.25 * grain[..., None])
    fm = (XX < FR) | (XX > W - FR) | (YY < FR)
    img[fm] = wcol[fm]
    # inner bevel
    img[(XX >= FR) & (XX < FR + 4)] *= 0.55; img[(XX <= W - FR) & (XX > W - FR - 4)] *= 0.55
    img[(YY >= FR) & (YY < FR + 4) & (XX >= FR) & (XX <= W - FR)] *= 0.55
    # chalk tray: lip + shelf, then wood down to the bottom
    tm = YY >= TRAY
    tg = 0.5 + 0.5 * np.sin(XX * 0.013 + wood * 5)
    tc = np.array((140, 94, 54), np.float32)[None, None] * (0.8 + 0.22 * tg[..., None])
    img[tm] = tc[tm]
    img[(YY >= TRAY) & (YY < TRAY + 10)] *= 1.25
    img[(YY >= TRAY + 10) & (YY < TRAY + 16)] *= 0.6
    img[(YY >= TRAY + 70) & (YY < TRAY + 78)] *= 0.55
    # dust on the shelf
    dust = np.clip(fbm(H, W, 9, 5, 8) * 1.5, 0, 1) * ((YY > TRAY + 16) & (YY < TRAY + 70))
    img += dust[..., None] * 60
    img[YY < TRAY] = img[YY < TRAY]  # noop for clarity
    out = np.clip(img, 0, 255).astype(np.uint8)
    # chalk sticks on the tray
    for (x, ln, c) in [(150, 120, WHT), (330, 80, YEL), (820, 100, PNK), (930, 60, BLU)]:
        y = TRAY + 42
        cv2.rectangle(out, (x, y - 11), (x + ln, y + 11), tuple(int(v * 0.7) for v in c), -1)
        cv2.rectangle(out, (x, y - 11), (x + ln, y + 3), c, -1)
        cv2.ellipse(out, (x + ln, y), (6, 11), 0, -90, 90, tuple(int(v * 0.85) for v in c), -1)
    # eraser on the tray
    ex = 520; ey = TRAY + 18
    cv2.rectangle(out, (ex, ey), (ex + 190, ey + 38), (96, 62, 36), -1)
    cv2.rectangle(out, (ex, ey + 26), (ex + 190, ey + 46), (70, 70, 74), -1)
    cv2.rectangle(out, (ex, ey), (ex + 190, ey + 6), (150, 106, 66), -1)
    return out

BOARD = make_board()
BOARDF = BOARD.astype(np.float32)

def grain_tex(seed):
    r = np.random.default_rng(seed)
    n = r.uniform(0, 1, (H, W)).astype(np.float32)
    n = cv2.GaussianBlur(n, (0, 0), 0.9)
    streak = cv2.blur(r.uniform(0, 1, (H, W)).astype(np.float32), (9, 2))
    g = np.clip((n - 0.30) * 3.2, 0, 1) * 0.6 + np.clip((streak - 0.42) * 4, 0, 1) * 0.4
    return np.clip(0.25 + 0.85 * g, 0, 1)
GRAIN = [grain_tex(11), grain_tex(12)]

# ---------- chalk canvas ----------
def boil_seed(t): return int(t * 7.5)
class Chalk:
    def __init__(self, t):
        self.t = t; self.m = {}; self.seed = boil_seed(t)
    def mask(self, c):
        if c not in self.m: self.m[c] = np.zeros((H, W), np.uint8)
        return self.m[c]
    def jit(self, pts, amp=1.6, salt=0):
        r = np.random.default_rng((self.seed * 131 + salt) % (2 ** 31))
        return pts + r.normal(0, amp, pts.shape).astype(np.float32)
    def line(self, pts, c="w", th=7, prog=1.0, salt=0, closed=False, amp=1.6):
        pts = np.asarray(pts, np.float32)
        if prog <= 0 or len(pts) < 2: return
        if closed: pts = np.vstack([pts, pts[:1]])
        pts = partial(pts, prog)
        p = self.jit(pts, amp, salt)
        cv2.polylines(self.mask(c), [np.round(p * 4).astype(np.int32)], False, 255, int(th), cv2.LINE_AA, shift=2)
    def circle(self, cx, cy, r, c="w", th=7, prog=1.0, salt=0, a0=-90):
        n = max(24, int(r / 3))
        ang = np.radians(a0) + np.linspace(0, 2 * np.pi * 1.06, n)
        pts = np.stack([cx + r * np.cos(ang), cy + r * np.sin(ang) * 0.96], 1)
        self.line(pts, c, th, prog, salt)
    def text(self, s, size, x, y, c="w", prog=1.0, font=BRUSH, anchor="c"):
        if prog <= 0: return 0
        m = tmask(s, font, size); h, w = m.shape
        x0 = x - w / 2 if anchor == "c" else (x - w if anchor == "r" else x)
        r = np.random.default_rng(self.seed + len(s))
        x0 += r.normal(0, 0.8); y0 = y + r.normal(0, 0.8)
        cut = int(w * min(1, prog))
        if cut <= 0: return w
        stamp(self.mask(c), m[:, :cut], x0, y0)
        return w
    def comp(self, img=None, alpha=1.0):
        out = (BOARDF.copy() if img is None else img.astype(np.float32))
        g = GRAIN[self.seed % 2]
        for c, m in self.m.items():
            mm = cv2.GaussianBlur(m, (0, 0), 0.7).astype(np.float32) / 255 * g * 0.95 * alpha
            out += (np.array(COLS[c], np.float32) - out) * mm[..., None]
        return out

def stamp(dst, m, x0, y0):
    h, w = m.shape; x0, y0 = int(round(x0)), int(round(y0))
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if xa >= xb or ya >= yb: return
    np.maximum(dst[ya:yb, xa:xb], m[ya - y0: yb - y0, xa - x0: xb - x0], out=dst[ya:yb, xa:xb])

def partial(pts, prog):
    if prog >= 1: return pts
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)])
    L = cum[-1] * prog; k = int(np.searchsorted(cum, L))
    if k <= 0: return pts[:1]
    k = min(k, len(pts) - 1)
    a, b = pts[k - 1], pts[k]; f = (L - cum[k - 1]) / max(seg[k - 1], 1e-6)
    return np.vstack([pts[:k], a + (b - a) * f])

def resample(pts, n=48):
    pts = np.asarray(pts, np.float32)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)])
    s = np.linspace(0, cum[-1], n)
    return np.stack([np.interp(s, cum, pts[:, 0]), np.interp(s, cum, pts[:, 1])], 1)

def smooth(pts, n=48):
    """Catmull-Rom through the control points, then resample evenly."""
    p = np.asarray(pts, np.float32); out = []
    P = np.vstack([p[:1], p, p[-1:]])
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for u in np.linspace(0, 1, 10, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    out.append(p[-1])
    return resample(np.array(out), n)

# ---------- skeletons (box coords ~1000 x 700) ----------
def ribs(xs, ys, lens, bend):
    return {f"rib{i}": [(x, y), (x + bend * 0.5, y + L * 0.4), (x + bend, y + L * 0.8), (x + bend * 0.7, y + L)] for i, (x, y, L) in enumerate(zip(xs, ys, lens))}
TREX = {
    "tail": [(0, 380), (80, 352), (170, 318), (260, 288), (340, 264), (410, 250)],
    "back": [(410, 250), (480, 240), (560, 245), (630, 262), (680, 280)],
    "neck": [(680, 280), (712, 270), (738, 248), (758, 224)],
    "skull": [(745, 216), (772, 182), (822, 166), (890, 170), (950, 190), (976, 214), (962, 232), (900, 237), (830, 241), (776, 246), (745, 216)],
    "jaw": [(772, 250), (822, 266), (892, 266), (956, 240)],
    "arm": [(684, 330), (706, 362), (728, 372), (742, 390)],
    "pelvis": [(350, 246), (420, 228), (492, 240), (498, 272), (430, 292), (360, 279), (350, 246)],
    "pubis": [(442, 290), (462, 350), (482, 395), (512, 404)],
    "leg1": [(432, 286), (456, 346), (470, 410), (456, 470), (432, 540), (442, 600), (452, 650), (505, 660)],
    "leg2": [(400, 286), (388, 345), (372, 405), (372, 470), (338, 540), (326, 600), (312, 650), (356, 662)],
    "keel": [(470, 380), (540, 398), (610, 396), (660, 372)],
    **ribs([470, 505, 540, 575, 610, 645], [242, 241, 244, 250, 258, 268], [90, 125, 145, 140, 118, 86], 16),
}
CHICK = {
    "tail": [(322, 238), (338, 254), (356, 268), (378, 280), (400, 290), (422, 296)],
    "back": [(422, 296), (472, 302), (522, 300), (560, 290), (592, 274)],
    "neck": [(592, 274), (626, 240), (614, 196), (642, 160)],
    "skull": [(630, 166), (640, 136), (670, 122), (706, 128), (762, 150), (714, 162), (672, 168), (642, 172), (630, 166)],
    "jaw": [(664, 172), (700, 170), (736, 162), (760, 154)],
    "arm": [(586, 302), (528, 330), (592, 342), (466, 348)],
    "pelvis": [(398, 284), (452, 276), (502, 288), (502, 312), (452, 322), (404, 310), (398, 284)],
    "pubis": [(452, 320), (442, 356), (422, 380), (396, 392)],
    "leg1": [(472, 316), (498, 352), (516, 392), (496, 432), (482, 472), (490, 510), (500, 546), (542, 554)],
    "leg2": [(450, 316), (452, 354), (446, 394), (430, 434), (414, 474), (404, 512), (396, 546), (434, 556)],
    "keel": [(476, 352), (520, 392), (570, 380), (598, 318)],
    **ribs([480, 500, 520, 540, 560, 578], [301, 301, 300, 296, 290, 282], [44, 62, 76, 74, 62, 44], -10),
}
PARTS = list(TREX.keys())
TR_S = {k: smooth(v) for k, v in TREX.items()}
CH_S = {k: smooth(v) for k, v in CHICK.items()}
TR_EYE = (842, 198, 17); CH_EYE = (676, 146, 15)

def ticks(C, pts, c, th, every=3, ln=12, prog=1.0, salt=0):
    n = int(len(pts) * prog)
    for i in range(1, n - 1, every):
        d = pts[i + 1] - pts[i - 1]; nrm = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-6)
        C.line([pts[i] - nrm * ln, pts[i] + nrm * ln], c, th, 1.0, salt + i)

def skeleton(C, mix, ox, oy, s, prog=1.0, c="w", teeth=None, th=7, far="d"):
    """mix: 0 = T. rex, 1 = chicken. prog: draw-on 0..1 (part order: spine, skull, ribs, limbs)."""
    m = ease(mix)
    sc = 1.0 - 0.0 * m
    order = ["tail", "back", "neck", "skull", "jaw", "pelvis", "pubis", "leg2", "leg1", "arm", "keel"] + [f"rib{i}" for i in range(6)]
    for i, k in enumerate(order):
        p = TR_S[k] * (1 - m) + CH_S[k] * m
        P = np.stack([ox + p[:, 0] * s, oy + p[:, 1] * s], 1)
        pp = np.clip(prog * len(order) * 0.55 - i * 0.45, 0, 1) if prog < 1 else 1.0
        col = far if k == "leg2" else c
        C.line(P, col, th + (3 if k.startswith("leg") else 0), pp, salt=i * 7)
        if k.startswith("leg") and pp >= 1:
            cp = np.array(TREX[k], np.float32) * (1 - m) + np.array(CHICK[k], np.float32) * m
            for j in (2, 4):
                C.circle(ox + cp[j, 0] * s, oy + cp[j, 1] * s, 9 * s + 3, col, 5, salt=i * 7 + j)
        if k in ("tail", "back", "neck"):
            ticks(C, P, col, max(3, th - 3), 3 if k != "neck" else 4, (14 if k != "tail" else 11) * s * (1 - 0.35 * m), pp, salt=i * 13)
    ex = TR_EYE[0] * (1 - m) + CH_EYE[0] * m; ey = TR_EYE[1] * (1 - m) + CH_EYE[1] * m; er = TR_EYE[2] * (1 - m) + CH_EYE[2] * m
    if prog >= 0.6: C.circle(ox + ex * s, oy + ey * s, er * s, c, max(3, th - 2), salt=99)
    ta = (1 - m) if teeth is None else teeth
    if ta > 0.15 and prog >= 0.7:
        sk = TR_S["skull"] * (1 - m) + CH_S["skull"] * m
        for j, x in enumerate(np.linspace(800, 950, 8)):
            xx = x * (1 - m) + (680 + (x - 800) * 0.5) * m
            idx = np.argmin(np.abs(sk[25:, 0] - xx)) + 25
            y = sk[idx, 1]
            L = 15 * ta
            C.line([(ox + xx * s, oy + y * s), (ox + (xx + 3) * s, oy + (y + L) * s)], c, max(3, th - 3), 1.0, salt=200 + j)

def arrow(C, pts, c="p", th=8, prog=1.0, salt=0, head=28):
    P = smooth(pts, 40); C.line(P, c, th, prog, salt)
    if prog >= 0.98:
        d = P[-1] - P[-4]; d = d / (np.linalg.norm(d) + 1e-6); nrm = np.array([-d[1], d[0]])
        tip = P[-1]
        C.line([tip - d * head + nrm * head * 0.6, tip, tip - d * head - nrm * head * 0.6], c, th, 1.0, salt + 1)

def cross(C, cx, cy, r, c="p", prog=1.0, th=10, salt=0):
    C.line([(cx - r, cy - r), (cx + r, cy + r)], c, th, min(1, prog * 2), salt)
    C.line([(cx + r, cy - r * 0.95), (cx - r, cy + r * 1.05)], c, th, max(0, prog * 2 - 1), salt + 1)

def scribble_circle(C, cx, cy, rx, ry, c="y", prog=1.0, th=8, salt=0):
    a = np.linspace(-2.2, -2.2 + 2 * np.pi * 1.15, 60)
    wob = 1 + 0.04 * np.sin(a * 3)
    pts = np.stack([cx + rx * wob * np.cos(a), cy + ry * wob * np.sin(a)], 1)
    C.line(pts, c, th, prog, salt)

def helix(C, cx, cy, wdt, amp, phase, prog=1.0, th=6, n=90, turns=3.0):
    xs = np.linspace(cx - wdt / 2, cx + wdt / 2, n)
    for k, c in enumerate(["w", "p", "b"]):
        ys = cy + amp * np.sin(np.linspace(0, 2 * np.pi * turns, n) + phase + k * 2 * np.pi / 3)
        C.line(np.stack([xs, ys], 1), c, th, prog, salt=300 + k, amp=1.0)

# femur outline (computed once per placement from a union of simple shapes)
_FEM = {}
def femur_pts(cx, cy, L, s=1.0):
    k = (cx, cy, L, s)
    if k in _FEM: return _FEM[k]
    m = np.zeros((H, W), np.uint8)
    hx, rx = cx - L / 2, cx + L / 2
    shaft = np.array([(hx + 90 * s, cy - 36 * s), (cx, cy - 28 * s), (rx - 80 * s, cy - 40 * s),
                      (rx - 80 * s, cy + 44 * s), (cx, cy + 30 * s), (hx + 90 * s, cy + 40 * s)], np.int32)
    cv2.fillPoly(m, [shaft], 255)
    # neck up-left to the ball head, greater trochanter bump
    cv2.line(m, (int(hx + 110 * s), int(cy - 10 * s)), (int(hx + 40 * s), int(cy - 70 * s)), 255, int(52 * s))
    cv2.circle(m, (int(hx + 34 * s), int(cy - 78 * s)), int(48 * s), 255, -1)
    cv2.ellipse(m, (int(hx + 110 * s), int(cy + 10 * s)), (int(60 * s), int(44 * s)), 0, 0, 360, 255, -1)
    # two condyles at the knee end
    cv2.circle(m, (int(rx - 50 * s), int(cy - 34 * s)), int(48 * s), 255, -1)
    cv2.circle(m, (int(rx - 46 * s), int(cy + 40 * s)), int(46 * s), 255, -1)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=len)[:, 0, :].astype(np.float32)
    c = np.vstack([c, c[:1]])
    # start the stroke at the head
    i0 = int(np.argmin(c[:, 0] + c[:, 1]))
    c = np.vstack([c[i0:], c[1:i0 + 1]])
    pts = resample(c, 200)
    _FEM[k] = pts; return pts

def femur(C, cx, cy, L, s, prog=1.0, hatch=1.0, c="w"):
    P = femur_pts(cx, cy, L, s)
    C.line(P, c, 8, prog, salt=400)
    if hatch > 0:
        # shading hatches along the lower shaft
        n = int(14 * hatch)
        for k in range(n):
            x = cx - L * 0.3 + k * L * 0.6 / 14
            C.line([(x, cy + 30 * s), (x + 18 * s, cy + 8 * s)], "d", 4, 1.0, salt=420 + k)

# ---------- scene helpers ----------
def wstart(ln, word):
    for w in words[ln["_w0"]: ln["_w1"]]:
        if word.lower() in w[0].lower(): return w[1] - ln["_s"]
    return 0.0
def wp(ln, lt, word, d=0.35, early=0.1): return (lt - wstart(ln, word) + early) / d
def wr(lt, a, d=0.35): return (lt - a) / d

def headline(C, s, size, y, c="w", prog=1.0, x=540):
    return C.text(s, size, x, y, c, eout(prog) if prog < 1 else 1.0)

# ---------- scenes ----------
def hook(C, ln, lt, dur, t):
    headline(C, "T. REX'S CLOSEST", 118, 120, "w")
    headline(C, "LIVING RELATIVE?", 132, 262, "y")
    skeleton(C, 0, 40, 262, 0.98, 1.0, "w")
    # chicken, scaled up from its box, below
    skeleton(C, 1, -100, 880, 1.15, 1.0, "w", th=7)
    C.text("T. REX", 60, 190, 700, "b", font=HAND)
    arrow(C, [(180, 760), (175, 930), (270, 1090)], "p", 9, 1.0, salt=500)
    u = wp(ln, lt, "chickens", 0.4)
    scribble_circle(C, 545, 1240, 300, 270, "y", min(1, max(0, u)), 9, salt=510)
    if u > 0.7: C.text("CHICKENS!", 96, 800, 1030, "p", min(1, (u - 0.7) * 3))
    return C

def why(C, ln, lt, dur, t):
    headline(C, "THE PROOF WAS", 112, 150, "w", wr(lt, 0, 0.3))
    headline(C, "INSIDE A BONE", 132, 290, "y", wp(ln, lt, "inside", 0.35))
    femur(C, 540, 820, 760, 1.15, eout(lt / 0.7), hatch=min(1, max(0, (lt - 0.6) / 0.5)))
    u = wp(ln, lt, "wait", 0.4)
    if u > 0:
        r = 110 * back(min(1, u), 2)
        C.circle(540, 1200, r, "p", 9, min(1, u), salt=520)
        C.text("?", int(150 * min(1, u)) + 10, 540, 1200 - r * 0.7, "p", 1.0)
        C.text("WAIT FOR IT...", 58, 540, 1380, "b", min(1, (u - 0.5) * 2), font=HAND)
    return C

def tree(C, ln, lt, dur, t):
    headline(C, "BIRDS ARE", 120, 110, "w", wr(lt, 0, 0.3))
    headline(C, "DINOSAURS", 150, 250, "y", wp(ln, lt, "they", 0.35))
    g = lambda a, d=0.5: min(1, max(0, (lt - a) / d))
    # trunk + branches (base at bottom)
    C.line(smooth([(540, 1470), (545, 1370), (540, 1280)], 20), "w", 11, g(0.1, 0.4), salt=600)
    C.text("DINOSAURS", 54, 540, 1490, "w", g(0.1, 0.4), font=HAND)
    br = [((540, 1280), (200, 1000), "TRICERATOPS", 0.4), ((540, 1280), (420, 960), "LONG-NECKS", 0.7), ((540, 1280), (700, 1120), None, 1.0)]
    for i, (a, b, lab, at) in enumerate(br):
        mid = ((a[0] + b[0]) / 2 + (10 if i % 2 else -10), (a[1] + b[1]) / 2)
        C.line(smooth([a, mid, b], 20), "w", 9, g(at, 0.4), salt=610 + i)
        if lab: C.text(lab, 46, b[0], b[1] - 62, "w", g(at + 0.3, 0.4), font=HAND)
    C.text("THEROPODS", 46, 860, 1150, "b", g(1.2, 0.4), font=HAND)
    C.line(smooth([(700, 1120), (640, 1000), (610, 880)], 20), "w", 9, g(1.4, 0.4), salt=620)
    C.text("T. REX", 50, 610, 820, "w", g(1.7, 0.3), font=HAND)
    C.line(smooth([(700, 1120), (790, 980), (830, 840), (830, 790)], 24), "y", 11, g(1.5, 0.6), salt=621)
    # extinct crosses (next to each label)
    xa = wp(ln, lt, "they", 0.3)
    for k, (cx, cy) in enumerate([(200, 1010), (420, 970), (610, 890)]):
        cross(C, cx, cy, 30, "p", min(1, max(0, xa - k * 0.4)), 9, salt=630 + k * 3)
    # living bird branch: little chicken skeleton at the tip
    ua = min(1, max(0, (lt - 1.8) / 0.6))
    skeleton(C, 1, 830 - 540 * 0.5, 650 - 340 * 0.5, 0.5, ua, "y", th=5, far="y")
    ub = wp(ln, lt, "are", 0.35) - 0.3
    if ub > 0:
        scribble_circle(C, 830, 640, 160, 150, "y", min(1, ub), 7, salt=640)
        C.text("STILL ALIVE!", 60, 320, 640, "y", min(1, ub), font=HAND)
        arrow(C, [(460, 650), (560, 640), (650, 640)], "y", 6, min(1, ub), salt=645, head=18)
    return C

def bone(C, ln, lt, dur, t):
    u = wp(ln, lt, "68", 0.25)
    n = int(68 * eout(min(1, max(0, u) / 2.2))) if u > 0 else 0
    headline(C, f"{n} MILLION", 140, 120, "y", 1.0 if u > 0 else 0)
    headline(C, "YEARS OLD", 110, 290, "w", min(1, max(0, u)))
    femur(C, 520, 760, 780, 1.2, eout(lt / 0.7), hatch=min(1, max(0, (lt - 0.6) / 0.5)))
    C.text("T. REX THIGHBONE", 52, 520, 560, "b", wp(ln, lt, "thighbone", 0.4), font=HAND)
    # magnifier over the shaft -> protein helix
    v = wp(ln, lt, "traces", 0.45)
    if v > 0:
        vv = min(1, v)
        C.circle(560, 1250, 210, "w", 10, vv, salt=700)
        C.line([(560 - 150, 1250 - 150), (470, 870)], "w", 6, vv, salt=701)
        C.line([(560 + 150, 1250 - 150), (640, 870)], "w", 6, vv, salt=702)
        C.line([(560 + 148, 1250 + 148), (560 + 260, 1250 + 260)], "w", 18, vv, salt=703)
        if v > 0.6: helix(C, 560, 1250, 300, 50, t * 3, min(1, (v - 0.6) * 2), 6)
    p = wp(ln, lt, "protein", 0.35)
    if p > 0: C.text("PROTEIN!", 80, 860, 1060, "p", min(1, p))
    return C

ROWS = [("LIZARD", 860), ("ALLIGATOR", 1000), ("OSTRICH", 1140), ("CHICKEN", 1280)]
def table(C, lt, prog_rows, t):
    helix(C, 540, 500, 560, 46, t * 2.5, 1.0, 6, turns=3.5)
    C.text("T. REX COLLAGEN", 52, 540, 590, "b", 1.0, font=HAND)
    C.line([(150, 770), (930, 770)], "w", 6, prog_rows[0] if prog_rows else 0, salt=800)
    for k, (lab, y) in enumerate(ROWS):
        pr = prog_rows[k]
        C.text(lab, 70, 200, y - 40, "w", pr, font=HAND, anchor="l")
        if pr > 0.5:
            C.line([(150, y + 52), (930, y + 52)], "d", 4, min(1, (pr - 0.5) * 2), salt=810 + k)

def compare(C, ln, lt, dur, t):
    headline(C, "COMPARE THE", 112, 120, "w", wr(lt, 0, 0.3))
    headline(C, "PROTEIN", 140, 260, "y", wp(ln, lt, "collagen", 0.35, 0.3))
    la = wstart(ln, "compared") + 0.2
    pr = [min(1, max(0, (lt - la + 0.4 - k * 0.32) / 0.4)) for k in range(4)]
    table(C, lt, pr, t)
    for k, (lab, y) in enumerate(ROWS):
        if pr[k] >= 1:
            q = 0.6 + 0.4 * math.sin(t * 6 + k)
            C.text("?", int(80 + 8 * q), 840, y - 46, "b", 1.0)
    return C

def match(C, ln, lt, dur, t):
    headline(C, "BEST MATCH?", 132, 160, "y", wr(lt, 0, 0.3))
    table(C, lt, [1, 1, 1, 1], t)
    a1 = wp(ln, lt, "lizards", 0.35); a2 = wp(ln, lt, "alligators", 0.35)
    for k, a in enumerate((a1, a2)):
        y = ROWS[k][1]
        C.line([(170, y), (620, y - 6)], "p", 9, min(1, max(0, a)), salt=900 + k)
        cross(C, 840, y, 40, "p", min(1, max(0, a)), 10, salt=910 + k * 3)
    b = wp(ln, lt, "chickens", 0.4, 0.15)
    if b > 0:
        for k in (2, 3):
            y = ROWS[k][1]
            scribble_circle(C, 330, y, 230, 62, "y", min(1, b - (k - 2) * 0.3), 8, salt=920 + k)
            vv = min(1, max(0, b - 0.4 - (k - 2) * 0.3))
            C.line([(800, y - 6), (830, y + 26), (890, y - 40)], "y", 11, vv, salt=930 + k)
        if b > 1.0:
            C.text("CLOSEST!", 100, 540, 1390, "y", min(1, (b - 1.0) * 2))
    return C

def morph(C, ln, lt, dur, t):
    m = ease((lt - 0.5) / 2.6)
    s = 1.0 - 0.0 * m
    headline(C, "SAME FAMILY", 118, 130, "w", wr(lt, 0, 0.3))
    headline(C, "TREE", 150, 270, "y", wr(lt, 0.25, 0.3))
    skeleton(C, m, 40 + 30 * m, 520 + 60 * m, 0.98, 1.0, "w")
    C.text("T. REX", 60, 220, 1350, "b" if m < 0.5 else "d", 1.0, font=HAND)
    C.text("CHICKEN", 60, 830, 1350, "y" if m > 0.5 else "d", 1.0, font=HAND)
    arrow(C, [(330, 1385), (540, 1360), (690, 1385)], "w", 7, 1.0, salt=1000, head=22)
    u = wp(ln, lt, "cousin", 0.4)
    if u > 0:
        C.text("TINY COUSIN", 92, 540, 1440, "p", min(1, u))
    return C

def end(C, ln, lt, dur, t):
    cl = ln["scene"].get("click_at", 0.45)
    headline(C, "SOUNDS FAKE?", 128, 220, "w", wr(lt, 0, 0.25))
    u = ease((lt - cl) / 0.35)
    headline(C, "IT'S TRUE!", 170, 400, "y", wr(lt, cl + 0.1, 0.3))
    # chalk switch (stadium track)
    y = 900; x0, x1 = 330, 750; r = 72
    aa = np.linspace(-np.pi / 2, np.pi / 2, 24)
    rs = np.stack([x1 + r * np.cos(aa), y + r * np.sin(aa)], 1)
    ls = np.stack([x0 - r * np.cos(aa), y - r * np.sin(aa)], 1)
    C.line(np.vstack([[(x0, y - r)], rs, ls]), "w", 8, 1.0, salt=1100, closed=True)
    kx = x0 + (x1 - x0) * u
    kc = "y" if u > 0.5 else "w"
    C.circle(kx, y, r - 18, kc, 8, 1.0, salt=1110)
    for k in range(5):
        dx = -32 + k * 16
        C.line([(kx + dx - 10, y + 28), (kx + dx + 12, y - 28)], kc, 4, 1.0, salt=1120 + k)
    C.text("FAKE", 78, x0, y - 190, "w" if u < 0.5 else "d", 1.0, font=HAND)
    C.text("TRUE", 78, x1, y - 190, "y" if u > 0.5 else "d", 1.0, font=HAND)
    if u > 0.5:
        cross(C, x0, y - 150, 52, "p", min(1, (u - 0.5) * 3), 8, salt=1130)
        scribble_circle(C, x1, y - 150, 120, 66, "y", min(1, (u - 0.5) * 2.5), 8, salt=1140)
    C.text("FOLLOW FOR MORE", 96, 540, 1180, "p", min(1, max(0, (lt - cl - 0.55) / 0.4)))
    skeleton(C, 1, 540 - 560 * 0.4, 1380 - 340 * 0.4, 0.4, 1.0, "w", th=5)
    return C

SCENES = {"hook": hook, "why": why, "tree": tree, "bone": bone, "compare": compare, "match": match, "morph": morph, "end": end}

# ---------- narration + music ----------
voice, words, total = narrate(spec, lead=0.08)
n = len(voice); music = np.zeros(n, np.float32)
G3 = 196.0
def nt(semi): return G3 * 2 ** (semi / 12)
def pluck(f, dur=0.8, damp=0.996, bright=0.5, seed=0):
    N = int(dur * SR); p = max(2, int(SR / f))
    r = np.random.default_rng(seed)
    buf = r.uniform(-1, 1, p).astype(np.float32)
    buf = buf * bright + np.convolve(buf, [0.5, 0.5], mode="same") * (1 - bright)
    out = np.zeros(N, np.float32)
    for i in range(N):
        out[i] = buf[i % p]
        buf[i % p] = damp * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    return out
_PC = {}
def pl(semi, dur=0.7, damp=0.995):
    k = (semi, dur, damp)
    if k not in _PC: _PC[k] = pluck(nt(semi), dur, damp, seed=semi + 40)
    return _PC[k]
BPM = 104; BEAT = 60 / BPM
# G - Em - C - D, one bar each; melody plucks (8th notes) + walking bass
CH = [(0, 4, 7), (-3, 0, 4), (-7, -3, 0), (-5, -1, 2)]
MEL = [[12, 14, 16, 19, 16, 14, 12, 11], [9, 12, 16, 12, 9, 7, 9, 12], [7, 9, 12, 16, 14, 12, 9, 7], [7, 11, 14, 19, 18, 14, 11, 14]]
nbars = int(total / (4 * BEAT)) + 1
for b in range(nbars):
    t0 = b * 4 * BEAT; ch = CH[b % 4]
    for i, sm in enumerate(MEL[b % 4]):
        if (b % 2 == 1 and i in (3, 7)): continue
        place(music, t0 + i * BEAT / 2, pl(sm, 0.6, 0.994), 0.10)
    for i in range(4):
        bn = ch[0] - 12 + (0, 7, 4, 7)[i]
        place(music, t0 + i * BEAT, pl(bn - 12, 0.5, 0.993), 0.22)
    # brushes on 2 and 4
    for i in (1, 3):
        nz = np.random.default_rng(b * 4 + i).normal(0, 1, int(0.12 * SR)).astype(np.float32)
        nz = nz - np.convolve(nz, np.ones(5) / 5, mode="same")
        place(music, t0 + i * BEAT, nz * np.exp(-np.arange(len(nz)) / SR * 30), 0.05)
def squeak(at, dur=0.25, f=2600, gain=0.03, seed=0):
    N = int(dur * SR); s = np.arange(N) / SR
    nz = np.random.default_rng(seed).normal(0, 1, N).astype(np.float32)
    ff = f * (1 + 0.15 * np.sin(2 * np.pi * 9 * s))
    sig = np.sin(2 * np.pi * np.cumsum(ff) / SR) * 0.4 + nz * 0.6
    sig = sig - np.convolve(sig, np.ones(4) / 4, mode="same")
    env = np.sin(np.pi * s / dur) ** 0.6
    place(music, at, (sig * env).astype(np.float32), gain)
hook_hit(music, 0.35)
squeak(0.02, 0.3, seed=1)
for i, ln in enumerate(spec["lines"]):
    s0 = ln["_s"]
    if i > 0:
        whoosh(music, s0 - 0.05, 0.14, 0.45)
        squeak(s0 + 0.05, 0.22, 2400 + 200 * (i % 3), 0.03, seed=i)
    if ln["scene"]["type"] == "end":
        c = s0 + ln["scene"].get("click_at", 0.45)
        place(music, c, tone(1200, 0.06, 80, (1,)), 0.2)
        for j, sm in enumerate((12, 16, 19, 24)): place(music, c + 0.15 + j * 0.08, pl(sm, 0.9, 0.997), 0.16)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.45)

# ---------- compositing ----------
groups = caption_groups(words, 3)
CAP_Y = 1580
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return img
    ws = [words[i][0] for i in g]; size = 92
    while sum(tmask(w, KAL, size).shape[1] for w in ws) + 30 * (len(ws) - 1) > W - 160 and size > 56: size -= 4
    wl = [tmask(w, KAL, size).shape[1] for w in ws]
    tw = sum(wl) + 30 * (len(ws) - 1); x = (W - tw) / 2
    # dark wiped panel behind (clean board where the teacher wiped)
    pad_x, y0, y1 = 50, CAP_Y - 40, CAP_Y + 130
    xa, xb = int(max(FR + 6, x - pad_x)), int(min(W - FR - 6, x + tw + pad_x))
    reg = img[y0:y1, xa:xb]
    yy = np.linspace(-1, 1, y1 - y0)[:, None]; xx = np.linspace(-1, 1, xb - xa)[None]
    a = np.clip((1 - np.maximum(np.abs(yy) ** 6, np.abs(xx) ** 10)) * 1.5, 0, 1)[..., None] * 0.75
    img[y0:y1, xa:xb] = reg * (1 - a) + np.array((22, 33, 30), np.float32) * a
    C = Chalk(t)
    for i, w, ww in zip(g, ws, wl):
        on = words[i][1] <= t < words[i][2]
        m = tmask(w, KAL, size)
        stamp(C.mask("y" if on else "w"), m, x, CAP_Y + (100 - m.shape[0]) / 2 + (8 if m.shape[0] < 60 else 0))
        if on: C.line([(x - 4, CAP_Y + 112), (x + ww + 4, CAP_Y + 108)], "y", 7, 1.0, salt=i)
        x += ww + 30
    # high-contrast caption: denser grain
    out = img
    for c, m in C.m.items():
        mm = cv2.GaussianBlur(m, (0, 0), 0.6).astype(np.float32) / 255 * (0.82 + 0.18 * GRAIN[C.seed % 2])
        out += (np.array(COLS[c], np.float32) - out) * mm[..., None]
    return out

def scene_img(t, ln):
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    C = Chalk(t)
    SCENES[ln["scene"]["type"]](C, ln, lt, dur, t)
    return C.comp()

ERASE = 0.42
def eraser(img, x, y):
    x, y = int(x), int(y)
    cv2.rectangle(img, (x - 115 + 10, y - 50 + 12), (x + 115 + 10, y + 50 + 12), (10, 16, 14), -1)
    cv2.rectangle(img, (x - 115, y - 50), (x + 115, y + 20), (118, 78, 46), -1)
    cv2.rectangle(img, (x - 115, y - 50), (x + 115, y - 40), (160, 112, 70), -1)
    cv2.rectangle(img, (x - 115, y + 20), (x + 115, y + 50), (78, 78, 84), -1)
    for k in range(8): cv2.line(img, (x - 100 + k * 28, y + 24), (x - 100 + k * 28, y + 46), (60, 60, 66), 2)

def frame(t, fi):
    lines = spec["lines"]; ln = active_line(spec, t) or lines[0]; i = lines.index(ln)
    img = scene_img(t, ln)
    if i > 0:
        ph = (t - (ln["_s"] - 0.12)) / ERASE
        if ph < 1:
            old = scene_img(ln["_s"] - 0.12, lines[i - 1])
            p = ease(ph) * (W + 500) - 250
            edge = p + 60 * np.sin(YY / 140 + i)
            new_m = (XX < edge)[..., None]
            img = np.where(new_m, img, old)
            # dust smear trailing the eraser
            sm = np.clip(1 - (edge - XX) / 220, 0, 1) * (XX < edge)
            img = img + (np.array((120, 135, 128), np.float32) - img) * (sm * 0.35)[..., None]
            ey = 300 + (TRAY - 600) * (0.5 + 0.5 * math.sin(ph * math.pi * 3))
            img = img.astype(np.float32)
            ib = img.astype(np.uint8); eraser(ib, p, ey); img = ib.astype(np.float32)
    if t > total - 0.45:
        a = ease((t - (total - 0.45)) / 0.45)
        img = img * (1 - a) + scene_img(lines[0]["_s"], lines[0]) * a
    # keep frame + tray clean (scenes draw only on the board)
    img[YY >= TRAY] = BOARDF[YY >= TRAY] if False else img[YY >= TRAY]
    img = caption(img.astype(np.float32), t)
    # progress: a yellow chalk line on the wooden ledge
    pw = int((W - 80) * t / total)
    y = H - 30
    cv2.line(img, (40, y), (W - 40, y), (70, 48, 30), 8)
    if pw > 1:
        cv2.line(img, (40, y), (40 + pw, y), YEL, 8)
        cv2.circle(img, (40 + pw, y), 9, WHT, -1, cv2.LINE_AA)
    return np.clip(img, 0, 255).astype(np.uint8).tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), int(float(tt_) * FPS))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=24); print(f"done {total:.1f}s")
