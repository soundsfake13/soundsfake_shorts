"""Day 20 — STORM NEON style (lightning is hotter than the Sun's surface).
A night thunderstorm drawn in light. Procedural cloud banks (fbm density, lit from below) drift over a deep indigo sky;
procedural branching lightning (recursive midpoint displacement + side branches) strikes in a 0.1 s leader, then
flickers and fades, flashing the clouds and the sky. Everything that matters is a glowing neon tube: titles in Tilt Neon
with white-hot cores, a thermal scale tube, a neon Sun, shockwave rings, sound-wave arcs. All neon is drawn into an
emission layer that gets a two-radius bloom; a wet ground below the horizon reflects the glow with a ripple; rain streaks
slant across. Scene changes are a lightning flash (white-out frame + new strike).
Palette: storm indigo #0a0820, violet #3b2a6b, electric cyan #36e6ff, hot magenta #ff3fa4, solar amber #ffb03b, white.
Type: Tilt Neon (titles, labels), Inter Display Bold (captions).
Ending: a neon toggle; a bolt strikes its knob, which jumps from FAKE to TRUE and floods the track cyan.
Music: dark synth pad (Em-C-Am-B), plucked arpeggio, soft kick, rain bed, crackles + rolling thunder on strikes.
Usage: python3 engine/styles/day20_stormneon.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
INTER = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter")
_F = {}
def F(kind, s):
    k = (kind, int(s))
    if k not in _F:
        if kind == "neon": _F[k] = ImageFont.truetype(f"{FONTS}/TiltNeon.ttf", int(s))
        else: _F[k] = ImageFont.truetype(f"{INTER}/InterDisplay-Bold.otf", int(s))
    return _F[k]

CYAN, MAG, AMB, WHITE, VIO = (54, 230, 255), (255, 63, 164), (255, 176, 59), (255, 255, 255), (150, 110, 255)
HZ = 1500                                        # horizon (wet ground below)

# ---------- static backdrop ----------
def fbm(seed, scales, amps, size):
    rr = np.random.default_rng(seed); acc = np.zeros((size[1], size[0]), np.float32)
    for s, a in zip(scales, amps):
        g = rr.random((max(2, size[1] // s + 2), max(2, size[0] // s + 2))).astype(np.float32)
        acc += a * cv2.resize(g, size, interpolation=cv2.INTER_CUBIC)
    acc -= acc.min(); return acc / max(1e-6, acc.max())
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_v = yy / HZ
SKY = np.stack([10 + 34 * _v ** 2, 8 + 16 * _v ** 2, 32 + 60 * _v ** 2], -1).astype(np.float32)
_g = yy > HZ
_d = np.clip((yy - HZ) / (H - HZ), 0, 1)
SKY[_g] = (np.stack([30 - 24 * _d ** 0.5, 18 - 13 * _d ** 0.5, 66 - 50 * _d ** 0.5], -1))[_g]
SKY += (fbm(4, [300, 90], [1, 0.4], (W, H)) - 0.5)[..., None] * 10
CW = W + 900
CLOUD = fbm(7, [420, 200, 90, 40, 16], [1, 0.7, 0.4, 0.22, 0.1], (CW, 900))
CLOUD2 = fbm(8, [300, 140, 60, 24], [1, 0.6, 0.3, 0.15], (CW, 900))
RAIN = [(random.Random(i).uniform(-200, W + 200), random.Random(i + 999).uniform(0, H), random.Random(i + 77).uniform(0.7, 1.3)) for i in range(100)]

def clouds(out, t, y0, h, flash, fx, dens=1.0):
    """two drifting cloud layers in band [y0, y0+h]; lit from below + around the strike x on a flash."""
    ox1 = int(450 + 420 * math.sin(t * 0.03)); ox2 = int(450 + 420 * math.sin(t * 0.05 + 2))
    d1 = cv2.resize(CLOUD[:, ox1:ox1 + W], (W, h)); d2 = cv2.resize(CLOUD2[:, ox2:ox2 + W], (W, h))
    v = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    band = np.clip(np.minimum(v / 0.35, (1 - v) / 0.45), 0, 1)
    D = np.clip((0.55 * d1 + 0.45 * d2 - 0.36) * 2.6, 0, 1) * band * dens
    under = np.clip(np.gradient(d1, axis=0) * -60 + 0.5, 0, 1)
    lit = flash * np.exp(-((xx[:h] - fx) / 420) ** 2) * (0.5 + 0.5 * under)
    col = np.stack([28 + 40 * d2 + 200 * lit, 22 + 26 * d2 + 205 * lit, 58 + 60 * d2 + 255 * lit], -1)
    reg = out[y0:y0 + h]; a = D[..., None]
    out[y0:y0 + h] = reg * (1 - a) + col * a

# ---------- emission drawing ----------
class Neon:
    def __init__(self): self.N = np.zeros((H, W, 3), np.uint8)
    def add(self, mask, x, y, col, a=1.0, core=True):
        """max-composite a float mask (0..1) tinted col at top-left (x, y), with a white-hot core."""
        x, y = int(x), int(y); h_, w_ = mask.shape
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w_), min(H, y + h_)
        if x1 <= x0 or y1 <= y0 or a <= 0: return
        m = mask[y0 - y:y1 - y, x0 - x:x1 - x][..., None] * a
        c = np.array(col, np.float32)
        if core: c = c * (1 - m * 0) ; px = m * c; cm = np.clip((m - 0.0) ** 3, 0, 1); px = px * (1 - 0.65 * cm) + 255 * 0.65 * cm
        else: px = m * c
        reg = self.N[y0:y1, x0:x1]; np.maximum(reg, px.clip(0, 255).astype(np.uint8), out=reg)
    def poly(self, pts, col, w, a=1.0, closed=False, core=True):
        if a <= 0 or len(pts) < 2: return
        p = np.array(pts, np.float32).reshape(-1, 1, 2); p = (p * 4).astype(np.int32)
        c = tuple(int(v * a) for v in col)
        cv2.polylines(self.N, [p], closed, c, max(1, int(w)), cv2.LINE_AA, shift=2)
        if core and w >= 3:
            cw = tuple(int(min(255, (v * 0.35 + 255 * 0.65) * a)) for v in col)
            cv2.polylines(self.N, [p], closed, cw, max(1, int(w * 0.38)), cv2.LINE_AA, shift=2)
    def circle(self, cx, cy, r, col, w, a=1.0, core=True):
        pts = [(cx + r * math.cos(k / 72 * 2 * math.pi), cy + r * math.sin(k / 72 * 2 * math.pi)) for k in range(72)]
        self.poly(pts, col, w, a, True, core)
    def rrect(self, x0, y0, x1, y1, r, col, w, a=1.0, core=True):
        pts = []
        for (cx, cy, a0) in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
            for k in range(10): ang = math.radians(a0 + 90 * k / 9); pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        self.poly(pts, col, w, a, True, core)

_TM = {}
def tmask(s, size, kind="neon"):
    k = (s, int(size), kind)
    if k not in _TM:
        f = F(kind, size); bb = f.getbbox(s); pad = 20
        im = Image.new("L", (bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad), 0)
        ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), s, font=f, fill=255)
        m = np.asarray(im, np.float32) / 255
        er = cv2.erode(m, np.ones((3, 3), np.uint8), iterations=max(1, int(size / 45)))
        _TM[k] = (m, er)
    return _TM[k]
def fit(s, size, maxw=W - 140, kind="neon"):
    while F(kind, size).getlength(s) > maxw and size > 40: size -= 4
    return size
def neon_text(nz, s, size, cx, cy, col, a=1.0, scale=1.0):
    if a <= 0.01: return
    m, er = tmask(s, size)
    if abs(scale - 1) > 0.01:
        sz = (max(1, int(m.shape[1] * scale)), max(1, int(m.shape[0] * scale)))
        m = cv2.resize(m, sz); er = cv2.resize(er, sz)
    x, y = cx - m.shape[1] / 2, cy - m.shape[0] / 2
    nz.add(m, x, y, col, a, core=False)
    nz.add(er, x, y, tuple(min(255, int(v * 0.3 + 255 * 0.7)) for v in col), a, core=False)

def ignite(lt, at):
    """neon-tube ignition: flickers on over ~0.2 s."""
    u = lt - at
    if u < 0: return 0.0
    if u > 0.22: return 1.0
    return [1, 0.15, 0.9, 0.3, 1, 0.6, 1][int(u / 0.032) % 7]
def slam(lt, at, d=0.28):
    u = (lt - at) / d
    if u <= 0: return 0.0
    return 1.0 if u >= 1 else back(u)
def wt(ln, i): return words[min(ln["_w0"] + i, ln["_w1"] - 1)][1] - ln["_s"]

def label(nz, s, size, cx, cy, col, a=1.0):
    neon_text(nz, s, size, cx, cy, col, a)

# ---------- lightning ----------
_BOLTS = {}
def gen_bolt(seed, x0, y0, x1, y1, rough=0.26, depth=7, branches=6):
    key = (seed, int(x0), int(y0), int(x1), int(y1), branches)
    if key in _BOLTS: return _BOLTS[key]
    rnd = random.Random(seed)
    def mid(pts, rough, depth):
        for _ in range(depth):
            nxt = [pts[0]]
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                L = math.hypot(bx - ax, by - ay); nx_, ny_ = -(by - ay) / max(L, 1e-6), (bx - ax) / max(L, 1e-6)
                o = rnd.gauss(0, 1) * rough * L * 0.5
                nxt += [((ax + bx) / 2 + nx_ * o, (ay + by) / 2 + ny_ * o), (bx, by)]
            pts = nxt
        return pts
    main = mid([(x0, y0), (x1, y1)], rough, depth)
    br = []
    for k in range(branches):
        i = rnd.randint(len(main) // 10, int(len(main) * 0.7)); bx, by = main[i]
        ang = math.radians(90 + rnd.choice([-1, 1]) * rnd.uniform(25, 60)); L = rnd.uniform(120, 340)
        pts = mid([(bx, by), (bx + L * math.cos(ang), by + L * math.sin(ang))], 0.3, 5)
        br.append((i, pts))
    _BOLTS[key] = (main, br); return _BOLTS[key]

def strike_env(lt, at):
    """(progress 0..1, intensity 0..1) of a strike that starts at `at` (lt relative)."""
    u = lt - at
    if u < 0: return 0.0, 0.0
    prog = min(1.0, u / 0.1)
    if u < 0.1: return prog, 0.7
    v = u - 0.1
    fl = [1.0, 0.45, 1.0, 0.6, 0.9][min(4, int(v / 0.05))] if v < 0.25 else 1.0
    return 1.0, fl * max(0.0, 1 - max(0, v - 0.25) / 0.75)

def draw_bolt(nz, bolt, prog, inten, col=VIO, w=9):
    main, br = bolt
    n = max(2, int(len(main) * prog))
    nz.poly(main[:n], col, w * 2.4, 0.35 * inten, core=False)
    nz.poly(main[:n], col, w, inten)
    for i, pts in br:
        if i < n:
            m = max(2, int(len(pts) * min(1, (n - i) / (len(main) * 0.3))))
            nz.poly(pts[:m], col, w * 0.5, inten * 0.85)

class Ctx:
    def __init__(self):
        self.nz = Neon(); self.flash = 0.0; self.fx = W / 2; self.cloud = (560, 420, 1.0); self.shake = 0.0; self.white = 0.0

def storm_strike(cx, lt, at, seed, x0, y0, x1, y1, col=VIO, w=9, branches=6, gain=1.0):
    p, it = strike_env(lt, at)
    if it <= 0: return 0.0
    draw_bolt(cx.nz, gen_bolt(seed, x0, y0, x1, y1, branches=branches), p, it * gain, col, w)
    f = it ** 2 * (1 if p >= 1 else 0.4) * gain
    if f > cx.flash: cx.flash, cx.fx = f, x1
    return f

def sun(nz, cx, cy, r, t, a=1.0):
    nz.circle(cx, cy, r, AMB, 10, a)
    nz.circle(cx, cy, r * 0.62, AMB, 6, a * 0.8)
    for k in range(12):
        ang = t * 0.6 + k * math.pi / 6
        nz.poly([(cx + r * 1.22 * math.cos(ang), cy + r * 1.22 * math.sin(ang)), (cx + r * 1.5 * math.cos(ang), cy + r * 1.5 * math.sin(ang))], AMB, 8, a)

def bolt_icon(nz, cx, cy, s, col=CYAN, a=1.0):
    pts = [(0.15, -1), (-0.45, 0.1), (0.05, 0.1), (-0.2, 1), (0.5, -0.2), (0.0, -0.2), (0.35, -1)]
    nz.poly([(cx + x * s, cy + y * s) for x, y in pts], col, 8, a, True)

# ---------- scenes ----------
def S_hook(cx, sc, ln, lt, dur, t):
    cx.cloud = (560, 430, 1.0)
    storm_strike(cx, lt, -0.2, 11, 640, 780, 560, HZ + 4, VIO, 11, 7)
    storm_strike(cx, lt, 1.25, 12, 380, 800, 470, HZ + 4, VIO, 9, 5)
    neon_text(cx.nz, "LIGHTNING", fit("LIGHTNING", 200), W / 2, 210, CYAN)
    neon_text(cx.nz, "IS HOTTER THAN", fit("IS HOTTER THAN", 112), W / 2, 380, WHITE)
    neon_text(cx.nz, "THE SUN", fit("THE SUN", 200), W / 2, 540, AMB)

def S_loop(cx, sc, ln, lt, dur, t):
    cx.cloud = (560, 430, 1.0)
    storm_strike(cx, lt, 0.0, 21, 760, 790, 690, HZ + 4, MAG, 10, 6)
    storm_strike(cx, lt, wt(ln, 4) - 0.1, 22, 300, 800, 380, HZ + 4, VIO, 10, 6)
    storm_strike(cx, lt, wt(ln, 9) - 0.1, 23, 560, 790, 560, HZ + 4, CYAN, 9, 5)
    neon_text(cx.nz, "NOT A LITTLE", fit("NOT A LITTLE", 130), W / 2, 230, WHITE, ignite(lt, 0.0))
    neon_text(cx.nz, "HOTTER.", fit("HOTTER.", 210), W / 2, 420, MAG, 1, slam(lt, wt(ln, 3) - 0.1))
    a = ignite(lt, wt(ln, 7) - 0.05)
    neon_text(cx.nz, "…and it makes a sound", 62, W / 2, 610, CYAN, a)

TX, TY0, TY1 = 300, 1440, 520                     # thermal tube x, bottom (0 °C) and top (30,000 °C)
def ty(v): return TY0 - (TY0 - TY1) * v / 30000
def S_scale(cx, sc, ln, lt, dur, t):
    cx.cloud = (0, 330, 0.55)
    nz = cx.nz; ph = sc.get("phase", "sun")
    nz.rrect(TX - 34, TY1 - 50, TX + 34, TY0 + 30, 34, (70, 90, 160), 5, 1, core=False)
    for v in range(0, 30001, 5000):
        y = ty(v); nz.poly([(TX - 58, y), (TX - 40, y)], (120, 140, 220), 4, 1, core=False)
        neon_text(nz, f"{v:,}°", 40, TX - 150, y, (150, 170, 240), 0.9)
    sy = ty(5500)
    if ph == "sun":
        u = ease((lt - 0.3) / 1.6); v = 5500 * u
        nz.poly([(TX, TY0 + 6), (TX, ty(v))], AMB, 36, 1)
        nz.poly([(TX + 50, sy), (640, sy)], AMB, 4, ease((lt - 1.6) / 0.3), core=False)
        sun(nz, 800, sy, 95, t, ignite(lt, 0.0))
        neon_text(nz, "SUN'S SURFACE", fit("SUN'S SURFACE", 120), W / 2, 200, AMB, ignite(lt, 0.0))
        neon_text(nz, f"{int(round(v / 100) * 100):,} °C", 150, W / 2 + 120, 370, WHITE, 1)
    else:
        nz.poly([(TX, TY0 + 6), (TX, sy)], AMB, 36, 1)
        nz.poly([(TX + 50, sy), (640, sy)], AMB, 4, 1, core=False)
        sun(nz, 800, sy, 95, t, 1)
        k = wt(ln, 2) - 0.1
        storm_strike(cx, lt, k - 0.2, 31, W + 20, 600, TX + 30, TY1 - 40, CYAN, 9, 2, 0.9)
        u = ease((lt - k) / 1.4); v = 5500 + 24500 * u
        nz.poly([(TX, sy), (TX, ty(v))], CYAN, 36, 1)
        a = ignite(lt, k + 1.3)
        bolt_icon(nz, 800, TY1 + 60, 70, CYAN, a)
        nz.poly([(TX + 50, TY1 + 0), (700, TY1 + 0)], CYAN, 4, a, core=False)
        neon_text(nz, "LIGHTNING", fit("LIGHTNING", 150), W / 2, 200, CYAN, ignite(lt, 0.0))
        neon_text(nz, f"{int(round(v / 100) * 100):,} °C", 150, W / 2 + 120, 370, WHITE, 1)

def S_times(cx, sc, ln, lt, dur, t):
    cx.cloud = (0, 330, 0.55)
    nz = cx.nz
    neon_text(nz, "5×", 300, W / 2, 300, MAG, 1, slam(lt, wt(ln, 3) - 0.15))
    neon_text(nz, "HOTTER", fit("HOTTER", 120), W / 2, 520, WHITE, ignite(lt, wt(ln, 4) - 0.05))
    # left: one bolt; right: five suns stacked
    storm_strike(cx, lt, -0.05, 41, 270, 660, 250, 1390, CYAN, 10, 1, 0.95)
    for j, at in enumerate((0.85, 1.7, 2.55)): storm_strike(cx, lt, at, 42 + j, 250, 660, 270, 1390, CYAN, 10, 1, 0.95)
    neon_text(nz, "1 BOLT", 56, 260, 1460, CYAN, 1)
    neon_text(nz, "=", 130, 540, 1010, WHITE, ignite(lt, 0.2))
    for i in range(5):
        a = ignite(lt, 0.25 + i * 0.28)
        sun(nz, 820, 1330 - i * 152, 50, t + i, a)
    neon_text(nz, "5 SUNS", 56, 820, 1460, AMB, ignite(lt, 1.6))

def S_blast(cx, sc, ln, lt, dur, t):
    cx.cloud = (560, 400, 1.0)
    nz = cx.nz; bx = 540
    storm_strike(cx, lt, -0.05, 51, 520, 760, bx, HZ + 4, WHITE, 12, 4)
    k = wt(ln, 5) - 0.2
    storm_strike(cx, lt, k - 0.05, 52, 560, 760, bx, HZ + 4, WHITE, 12, 4)
    for j in range(5):
        u = (lt - k - j * 0.22) / 1.3
        if 0 < u < 1:
            r = 40 + 560 * eout(u); a = (1 - u) ** 1.2
            pts = [(bx + r * math.cos(q / 60 * 2 * math.pi), 1150 + r * 0.55 * math.sin(q / 60 * 2 * math.pi)) for q in range(60)]
            nz.poly(pts, MAG if j % 2 == 0 else CYAN, 8, a, True)
    neon_text(nz, "THE AIR HEATS", fit("THE AIR HEATS", 120), W / 2, 200, WHITE, ignite(lt, 0.0))
    neon_text(nz, "SO FAST", fit("SO FAST", 170), W / 2, 370, CYAN, 1, slam(lt, wt(ln, 4) - 0.1))
    neon_text(nz, "IT BURSTS OUTWARD", fit("IT BURSTS OUTWARD", 92), W / 2, 545, MAG, ignite(lt, k + 0.1))

def S_thunder(cx, sc, ln, lt, dur, t):
    cx.cloud = (560, 430, 1.0)
    nz = cx.nz
    storm_strike(cx, lt, -0.1, 61, 600, 780, 520, HZ + 4, VIO, 11, 7)
    storm_strike(cx, lt, 1.0, 62, 420, 790, 640, HZ + 4, CYAN, 9, 5)
    cx.shake = max(0.0, 1 - lt / 0.9) * 22
    s = slam(lt, 0.0, 0.22)
    neon_text(nz, "BOOM", fit("BOOM", 290), W / 2, 260, MAG, 1, s)
    k = wt(ln, 3) - 0.1
    neon_text(nz, "THAT'S", 90, W / 2, 470, WHITE, ignite(lt, k - 0.4))
    neon_text(nz, "THUNDER", fit("THUNDER", 170), W / 2, 610, CYAN, 1, slam(lt, k))
    for j in range(4):                                   # sound-wave arcs spreading from the bolt
        u = ((lt + j * 0.35) % 1.4) / 1.4; r = 80 + 520 * u; a = (1 - u) * 0.8
        for side in (-1, 1):
            pts = [(560 + side * r * math.cos(q), 1180 + r * math.sin(q) * 0.9) for q in np.linspace(-0.6, 0.6, 16)]
            nz.poly(pts, AMB, 7, a, False)

def S_end(cx, sc, ln, lt, dur, t):
    cx.cloud = (560, 430, 1.0)
    nz = cx.nz; click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.3)
    neon_text(nz, "SOUNDS FAKE?", 128, W / 2 - 30, 190, WHITE, 1)
    y = 400; x0, x1, hh = 190, 890, 130
    nz.rrect(x0, y - hh / 2, x1, y + hh / 2, hh / 2, MAG if on < 0.5 else CYAN, 8, 1)
    kx = x0 + hh / 2 + (x1 - x0 - hh) * on
    if on < 0.98: neon_text(nz, "FAKE", 70, (x0 + x1) / 2 + 60, y, (255, 90, 110), 1 - on)
    if on > 0:
        nz.poly([(x0 + hh / 2, y), (kx, y)], CYAN, hh - 44, 0.22, core=False)
        neon_text(nz, "TRUE", 70, (x0 + kx) / 2 - 20, y, (10, 20, 40) if False else WHITE, ease((on - 0.5) / 0.4))
    nz.circle(kx, y, hh / 2 - 14, WHITE, 10, 1)
    storm_strike(cx, lt, click - 0.1, 71, W + 20, 330, x1 - hh / 2 + 10, y - hh / 2 + 6, CYAN, 9, 2)
    w_ = slam(lt, click + 0.3)
    neon_text(nz, "IT'S TRUE.", fit("IT'S TRUE.", 180), W / 2, 640, CYAN, 1, w_)
    neon_text(nz, "Follow for more.", 76, W / 2, 790, WHITE, ignite(lt, click + 0.6))
    storm_strike(cx, lt, dur - 0.35, 11, 640, 900, 560, HZ + 4, VIO, 11, 7)    # flows into the hook's bolt
    cx.cloud = (880, 380, 1.0)

SCENES = dict(hook=S_hook, loop=S_loop, scale=S_scale, times=S_times, blast=S_blast, thunder=S_thunder, end=S_end)

# ---------- audio ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32); tt = np.arange(n) / SR
rng = np.random.default_rng(5)
rain = rng.normal(0, 1, n).astype(np.float32); rain = (rain - np.convolve(rain, np.ones(8) / 8, "same")) * 0.03
music += rain
CH = [[82.41, 164.81, 196.0, 246.94], [65.41, 130.81, 164.81, 196.0], [55.0, 110.0, 130.81, 164.81], [61.74, 123.47, 155.56, 185.0]]
BAR = 2.4
for b in range(int(total / BAR) + 1):
    ch = CH[b % 4]; s = np.arange(int(BAR * 1.2 * SR)) / SR
    env = np.minimum(1, s / 0.4) * np.exp(-s * 0.35)
    pad = sum(np.sin(2 * np.pi * f * s * (1 + d) + 0.4 * np.sin(2 * np.pi * 0.3 * s)) / (1 + 0.6 * i) for i, f in enumerate(ch) for d in (-0.003, 0.003))
    place(music, b * BAR, (pad * env * 0.05).astype(np.float32))
    for k in range(16):
        f = ch[[1, 2, 3, 2][k % 4]] * (2 if k % 8 >= 4 else 1)
        s2 = np.arange(int(0.25 * SR)) / SR
        pl = (np.sign(np.sin(2 * np.pi * f * s2)) * 0.3 + np.sin(2 * np.pi * f * s2)) * np.exp(-s2 * 18)
        place(music, b * BAR + k * BAR / 16, pl.astype(np.float32), 0.035)
    for k in range(4):
        s3 = np.arange(int(0.3 * SR)) / SR
        place(music, b * BAR + k * BAR / 4, (np.sin(2 * np.pi * (48 + 70 * np.exp(-s3 * 30)) * s3) * np.exp(-s3 * 10)).astype(np.float32), 0.14)
def crackle(at, gain=0.12, dur=0.35):
    s = np.arange(int(dur * SR)) / SR; z = rng.normal(0, 1, len(s)) * (rng.random(len(s)) > 0.8)
    place(music, at, (z * np.exp(-s * 9)).astype(np.float32), gain)
def thunder(at, gain=0.3, dur=2.4):
    s = np.arange(int(dur * SR)) / SR; z = rng.normal(0, 1, len(s)).astype(np.float32)
    lo = np.convolve(z, np.ones(160) / 160, "same") * 9
    rum = lo * (np.minimum(1, s / 0.05)) * np.exp(-s * 1.4) * (1 + 0.5 * np.sin(2 * np.pi * 3.1 * s))
    place(music, at, (rum + z * np.exp(-s * 25) * 0.4).astype(np.float32), gain)
hook_hit(music, 0.38); thunder(0.0, 0.22)
STRIKES = {"hook": [1.25], "loop": [0.0, ("w", 4), ("w", 9)], "scale": [], "times": [0.85, 1.7, 2.55], "blast": [], "thunder": [1.0]}
for i, ln in enumerate(spec["lines"]):
    st = ln["scene"]["type"]
    if i > 0: whoosh(music, ln["_s"], 0.08); crackle(ln["_s"], 0.1)
    for s_ in STRIKES.get(st, []):
        at = ln["_s"] + (s_ if not isinstance(s_, tuple) else wt(ln, s_[1]) - 0.1)
        crackle(at, 0.12); thunder(at + 0.15, 0.12, 1.4)
    if st == "scale" and ln["scene"].get("phase") == "bolt": crackle(ln["_s"] + wt(ln, 2) - 0.3, 0.16)
    if st == "blast": thunder(ln["_s"] + wt(ln, 5) - 0.2, 0.22, 1.6)
    if st == "thunder": thunder(ln["_s"], 0.5, 2.8)
    if st == "end":
        c = ln["_s"] + ln["scene"].get("click_at", 0.45); crackle(c - 0.1, 0.2); thunder(c, 0.15, 1.5)
        s = np.arange(int(1.6 * SR)) / SR
        place(music, c + 0.3, (sum(np.sin(2 * np.pi * f * s) for f in (329.63, 493.88, 659.25)) * np.exp(-s * 2.2) * np.minimum(1, s / 0.01)).astype(np.float32), 0.05)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.45)

# ---------- compositing ----------
STARTS = [ln["_s"] for ln in spec["lines"]]
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 72
    while F("inter", size).getlength(" ".join(ws)) > W - 220 and size > 36: size -= 4
    f = F("inter", size); tw = f.getlength(" ".join(ws)); x = (W - tw) / 2; y = 1590
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([x - 44, y - 26, x + tw + 44, y + size + 30], radius=22, fill=(8, 6, 26, 238), outline=(54, 230, 255, 255), width=4)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=(255, 225, 77, 255) if on else (255, 255, 255, 255)); x += f.getlength(w + " ")

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    cx = Ctx()
    SCENES[ln["scene"]["type"]](cx, ln["scene"], ln, lt, dur, t)
    for s in STARTS[1:]:                                    # scene change = lightning white-out
        if s - 0.03 <= t < s + 0.12: cx.white = max(cx.white, 0.55 * (1 - (t - s + 0.03) / 0.15))
    out = SKY * (1 + 1.6 * cx.flash * np.exp(-((xx - cx.fx) / 700) ** 2) * (yy < HZ))[..., None]
    cy0, ch, dens = cx.cloud
    if ch > 0: clouds(out, t, cy0, ch, cx.flash, cx.fx, dens)
    clouds(out, t * 0.7 + 30, 0, 300, cx.flash * 0.6, cx.fx, 0.75)
    N = cx.nz.N
    d8 = N                                                  # rain streaks (dim, slanted)
    for x, ph, sp in RAIN:
        yv = (ph + t * 1500 * sp) % (H + 200) - 100; xv = x - (yv - ph) * 0.0 + (t * 300 * sp) % 400 - 200
        if yv > HZ: continue
        cv2.line(d8, (int(xv), int(yv)), (int(xv - 10 * sp), int(yv + 46 * sp)), (42, 50, 96), 2, cv2.LINE_AA)
    if cx.shake > 0:
        dx, dy = int(cx.shake * math.sin(t * 91)), int(cx.shake * 0.6 * math.cos(t * 73)); N = np.roll(N, (dy, dx), (0, 1))
    Nf = N.astype(np.float32)
    small = cv2.resize(Nf, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    g = cv2.GaussianBlur(small, (0, 0), 3) * 1.5 + cv2.GaussianBlur(small, (0, 0), 14) * 1.5
    # wet-ground reflection of the glow + emission
    rows = H // 4 - HZ // 4; src = (small * 0.6 + g)[HZ // 4 - rows:HZ // 4][::-1]
    refl = np.zeros_like(g); refl[HZ // 4:] = src * np.linspace(0.55, 0.1, rows)[:, None, None]
    refl = cv2.GaussianBlur(refl, (0, 0), 1.5)
    g = cv2.resize(g + refl, (W, H), interpolation=cv2.INTER_LINEAR)
    sh = int(6 * math.sin(t * 3)); out[HZ:] = np.roll(out[HZ:], sh, 1)
    out = out + Nf + g * 0.9
    if cx.white > 0: out = out + 255 * cx.white
    img = Image.fromarray(out.clip(0, 255).astype(np.uint8))
    caption(img, t)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 10, W, H], fill=(20, 16, 50)); d.rectangle([0, H - 10, int(W * t / total), H], fill=CYAN)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=24); print(f"done {total:.1f}s")
