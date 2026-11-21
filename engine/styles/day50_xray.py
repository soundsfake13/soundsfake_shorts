"""Day 50 — X-RAY SCAN style (glass frogs: see-through bellies, and they hide their blood in a mirror-coated liver to sleep).
A radiology light-box at night: deep film-navy base with a cool lightbox falloff, fine film grain and a faint mm grid.
The frog is not painted, it is *transmitted light*: one ventral-view frog model built from layered masks —
  skin  : a glass shell whose brightness comes from a distance-field rim (bright edges, almost clear inside, like glass),
  bones : white-hot radiograph skeleton (skull + jaw arc, orbits, vertebrae, urostyle, ilia, girdle, limb bones, phalanges),
  organs: pale coiled gut, two-lobed liver whose colour moves dark-red (packed with blood) -> polished silver (mirror coat
          with a travelling specular sheen and twinkling crystal glints), and a red heart that beats lub-dub,
  blood : red cells streaming along the vessels; at sleep they peel off and stream into the liver.
All light is additive with a two-radius bloom. A cyan scanner band sweeps the body and 'enhances' everything it crosses.
HUD chrome: corner brackets, Plex Mono readouts (SCAN id, AWAKE/SLEEP state, blinking dot), mm ruler ticks and a scrolling
ECG strip synced to the heartbeat (the audio thumps on the same beats). Type: Space Grotesk Bold (white / cyan / blood red).
Cuts: a bright scan line wipes down the frame, revealing the new scene above it.
Ending: a glass toggle FAKE -> TRUE whose knob is a beating heart; the track floods cyan; fades back into the hook (loop).
Music: original E-minor glass pad + inharmonic glass bells + heartbeat thumps + scanner beeps.
Usage: python3 engine/styles/day50_xray.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
_F = {}
def F(kind, s, wt=700):
    k = (kind, int(s), wt)
    if k not in _F:
        if kind == "sg":
            f = ImageFont.truetype(f"{FONTS}/SpaceGrotesk-VF.ttf", int(s)); f.set_variation_by_axes([wt])
        else:
            f = ImageFont.truetype(f"{FONTS}/IBMPlexMono-Medium.ttf", int(s))
        _F[k] = f
    return _F[k]

CYAN = np.array([90, 215, 255], np.float32); BONE = np.array([235, 245, 255], np.float32)
RED = np.array([255, 52, 70], np.float32); SILVER = np.array([205, 222, 240], np.float32)
GUT = np.array([120, 210, 200], np.float32); LIVR = np.array([190, 30, 55], np.float32)
C_CY, C_WH, C_RD, C_DIM = (110, 225, 255), (240, 248, 255), (255, 70, 86), (70, 120, 150)

# ---------- background: film on a lightbox ----------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.45) / (H * 0.6)) ** 2)
BG = np.zeros((H, W, 3), np.float32); BG[:] = (5, 11, 24)
BG += (np.clip(1 - _r, 0, 1) ** 1.5)[..., None] * np.array([10, 26, 44], np.float32)
_g = np.zeros((H, W), np.uint8)
for x in range(0, W, 45): cv2.line(_g, (x, 0), (x, H), 255, 1)
for y in range(0, H, 45): cv2.line(_g, (0, y), (W, y), 255, 1)
BG += (_g.astype(np.float32) / 255 * 5)[..., None] * np.array([0.6, 1.0, 1.3], np.float32)
GRAIN = np.random.default_rng(50).normal(0, 1, (H + 64, W + 64)).astype(np.float32)
GRAIN = cv2.GaussianBlur(GRAIN, (0, 0), 0.7) * 5.5

# ---------- the frog model (local canvas, ventral view, head up) ----------
LW, LH = 1000, 1200; LC = np.array([500.0, 640.0])
def mirror(pts): return [(LW - x, y) for x, y in pts]
ARM = [(372, 440), (232, 505), (205, 372)]
FING = [(140, 318), (168, 290), (214, 290), (250, 312)]
LEG = [(432, 795), (196, 700), (330, 905), (292, 1000)]
TOES = [(205, 1090), (250, 1112), (298, 1118), (346, 1106), (385, 1080)]

def aa(img, pts, col, th, closed=False):
    cv2.polylines(img, [(np.array(pts, np.float32) * 8).astype(np.int32).reshape(-1, 1, 2)], closed, col, th, cv2.LINE_AA, shift=3)
def disc(img, c, r, col):
    cv2.circle(img, (int(c[0] * 8), int(c[1] * 8)), int(r * 8), col, -1, cv2.LINE_AA, shift=3)

def build_frog():
    skin = np.zeros((LH, LW), np.uint8)
    cv2.ellipse(skin, (500, 300), (196, 150), 0, 0, 360, 255, -1, cv2.LINE_AA)
    cv2.ellipse(skin, (500, 580), (205, 285), 0, 0, 360, 255, -1, cv2.LINE_AA)
    for side in (lambda p: p, mirror):
        aa(skin, side(ARM), 255, 62); [aa(skin, [side(ARM)[-1], f], 255, 20) for f in side(FING)]
        [disc(skin, f, 17, 255) for f in side(FING)]
        aa(skin, side(LEG[:2]), 255, 96); aa(skin, side(LEG[1:3]), 255, 70); aa(skin, side(LEG[2:]), 255, 44)
        [aa(skin, [side(LEG)[-1], f], 255, 18) for f in side(TOES)]; [disc(skin, f, 16, 255) for f in side(TOES)]
        disc(skin, side([(352, 232)])[0], 62, 255)
    skin = cv2.GaussianBlur(skin, (0, 0), 1.0)
    m = skin.astype(np.float32) / 255
    d = cv2.distanceTransform((skin > 127).astype(np.uint8), cv2.DIST_L2, 5)
    rim = np.exp(-d / 7) * 1.0 + np.exp(-d / 30) * 0.35 + 0.07
    tex = cv2.GaussianBlur(np.random.default_rng(5).normal(0, 1, (LH, LW)).astype(np.float32), (0, 0), 6) * 0.9
    skinL = np.clip(rim + tex * 0.05, 0, 2) * m
    bones = np.zeros((LH, LW), np.uint8)
    cv2.ellipse(bones, (500, 318), (168, 128), 0, 180, 360, 255, 7, cv2.LINE_AA)           # jaw arc
    cv2.ellipse(bones, (500, 318), (150, 112), 0, 196, 344, 150, 3, cv2.LINE_AA)
    cv2.ellipse(bones, (500, 330), (58, 96), 0, 0, 360, 200, 5, cv2.LINE_AA)               # braincase
    for side in (lambda p: p, mirror):
        c = side([(352, 232)])[0]; cv2.circle(bones, (int(c[0]), int(c[1])), 50, 170, 4, cv2.LINE_AA)
        aa(bones, side([(372, 440), (440, 420), (500, 432)]), 230, 8)                       # girdle
        aa(bones, side([(500, 652), (440, 790)]), 255, 10)                                    # ilium
        for a, b in (ARM[:2], ARM[1:]): aa(bones, side([a, b]), 255, 9)
        for a, b in zip(LEG[:-1], LEG[1:]): aa(bones, side([a, b]), 255, 11 if a == LEG[0] else 9)
        for j in side(ARM + LEG): disc(bones, j, 11, 255)
        for f in side(FING): aa(bones, [side(ARM)[-1], f], 210, 4); disc(bones, f, 6, 255)
        for f in side(TOES): aa(bones, [side(LEG)[-1], f], 210, 4); disc(bones, f, 6, 255)
    for k in range(9):                                                                         # vertebrae
        y = 380 + k * 32; cv2.rectangle(bones, (482, y), (518, y + 22), 230, -1, cv2.LINE_AA)
        cv2.line(bones, (472, y + 11), (528, y + 11), 200, 4, cv2.LINE_AA)
    aa(bones, [(500, 670), (500, 840)], 255, 9)                                               # urostyle
    bonesL = cv2.GaussianBlur(bones, (0, 0), 1.1).astype(np.float32) / 255
    gut = np.zeros((LH, LW), np.uint8)
    th = np.linspace(0, 2.3 * 2 * math.pi, 220); rr = 22 + 68 * th / th[-1]
    aa(gut, list(zip(500 + rr * np.cos(th), 745 + rr * np.sin(th) * 0.8)), 255, 22)
    gutL = cv2.GaussianBlur(gut, (0, 0), 2).astype(np.float32) / 255
    gutL = gutL * 0.55 + (cv2.GaussianBlur(gut, (0, 0), 1) > 40) * (cv2.GaussianBlur(gut, (0, 0), 1) < 140) * 0.5
    liv = np.zeros((LH, LW), np.uint8)
    cv2.ellipse(liv, (425, 585), (92, 62), 22, 0, 360, 255, -1, cv2.LINE_AA)
    cv2.ellipse(liv, (575, 585), (92, 62), -22, 0, 360, 255, -1, cv2.LINE_AA)
    cv2.ellipse(liv, (500, 610), (70, 42), 0, 0, 360, 255, -1, cv2.LINE_AA)
    livL = cv2.GaussianBlur(liv, (0, 0), 1.5).astype(np.float32) / 255
    dl = cv2.distanceTransform((liv > 127).astype(np.uint8), cv2.DIST_L2, 5)
    livRim = np.exp(-dl / 5) * livL
    occ = np.zeros((LH, LW), np.uint8); cv2.ellipse(occ, (500, 470), (70, 76), 0, 0, 360, 255, -1)
    bonesL = bonesL * (1 - 0.92 * cv2.GaussianBlur(occ, (0, 0), 6).astype(np.float32) / 255) * (1 - 0.45 * livL)
    return skinL, bonesL, gutL, livL, livRim, m

SKIN, BONES, GUTL, LIV, LIVRIM, SKINM = build_frog()
_V = [[(500, 440), (500, 380), (468, 322), (420, 280)],
      [(470, 470), (420, 448), (372, 440), (232, 505), (205, 372)],
      [(500, 515), (488, 640), (500, 765), (432, 795), (196, 700), (330, 905), (292, 1000), (250, 1100)]]
VESS = _V + [mirror(v) for v in _V]
VMASK = np.zeros((LH, LW), np.uint8)
for v in VESS: aa(VMASK, v, 255, 5)
VMASK = cv2.GaussianBlur(VMASK, (0, 0), 1.2).astype(np.float32) / 255
def arclen(v):
    v = np.array(v, np.float32); seg = np.sqrt(((v[1:] - v[:-1]) ** 2).sum(1)); return v, np.concatenate([[0], np.cumsum(seg)])
VARC = [arclen(v) for v in VESS]
def along(i, s, rev=False):
    v, cl = VARC[i]; L = cl[-1]; d = (1 - s if rev else s) * L
    k = min(np.searchsorted(cl, d) - 1, len(v) - 2); k = max(k, 0); u = (d - cl[k]) / max(1e-6, cl[k + 1] - cl[k])
    return v[k] + (v[k + 1] - v[k]) * u
LIVC = np.array([500.0, 595.0])
rng0 = np.random.default_rng(7)
GLINTS = []
while len(GLINTS) < 46:
    p = rng0.uniform([330, 520], [670, 660])
    if LIV[int(p[1]), int(p[0])] > 0.8: GLINTS.append((p, rng0.uniform(0, 6.28), rng0.uniform(1.2, 2.6)))

# heartbeat: lub-dub every 0.75 s
BEAT = 0.75
def pulse(t):
    u = t % BEAT
    return math.exp(-(u / 0.06) ** 2) + 0.6 * math.exp(-((u - 0.2) / 0.06) ** 2) + math.exp(-((u - BEAT) / 0.06) ** 2)

def frog_light(t, P):
    """Render the frog as transmitted light on the local canvas -> float RGB (LH, LW, 3)."""
    vis, b, lf, mir = P.get("vis", 1.0), P.get("b", 1.0), P.get("liver", 0.0), P.get("mirror", 0.0)
    out = SKIN[..., None] * CYAN * (0.95 * vis)
    out += BONES[..., None] * BONE * (0.85 * (0.45 + 0.55 * vis))
    out += GUTL[..., None] * GUT * (0.55 * vis)
    # liver: faint tissue -> blood-packed red -> mirror silver with a travelling sheen
    sheen = np.clip(1 - np.abs((XL * 0.7 + YL * 0.5) - (520 + 260 * math.sin(t * 1.3))) / 70, 0, 1) ** 2
    livc = (LIV[..., None] * (CYAN * 0.18 * vis + LIVR * (0.25 * b + 0.9 * lf) * (1 - 0.8 * mir))
            + LIV[..., None] * SILVER * mir * (0.2 + 0.55 * sheen[..., None]) + LIVRIM[..., None] * SILVER * mir * 0.7)
    out += livc
    out += VMASK[..., None] * RED * (0.28 * b * (0.5 + 0.5 * vis))
    D = np.zeros((LH, LW), np.uint8); Dr = np.zeros((LH, LW), np.uint8)
    # heart
    pz = pulse(t); hr = 50 * (1 + 0.22 * pz)
    hp = np.array([[500 + hr * 1.05 * math.sin(a) * (1 - 0.18 * math.cos(a)), 470 - hr * math.cos(a) * (0.9 if math.cos(a) > 0 else 1.25)] for a in np.linspace(0, 2 * math.pi, 48)])
    cv2.fillPoly(Dr, [(hp * 8).astype(np.int32)], int(255 * min(1, 0.55 + 0.45 * b + 0.3 * pz)), cv2.LINE_AA, shift=3)
    # circulating red cells
    nb = int(round(18 * b))
    for i in range(len(VESS)):
        for k in range(nb):
            s = (k / 18 + t * 0.32 + i * 0.13) % 1
            p = along(i, s); disc(Dr, p, 5.5, 220)
    # cells streaming into the liver while falling asleep
    inflow = P.get("inflow", 0.0)
    if inflow > 0:
        for i in range(len(VESS)):
            for k in range(7):
                s = (k / 7 + t * 0.55 + i * 0.21) % 1
                if s < 0.75: p = along(i, s / 0.75, rev=True)
                else: p = np.array(VESS[i][0], np.float32) + (LIVC + [((k * 37) % 120) - 60, ((k * 23) % 50) - 25] - VESS[i][0]) * ((s - 0.75) / 0.25)
                disc(Dr, p, 5.5, int(230 * inflow))
    if mir > 0:
        for p, ph, sp in GLINTS:
            g = max(0.0, math.sin(t * sp * 2.2 + ph)) ** 6 * mir
            if g > 0.05:
                L = 5 + 13 * g; c = p
                aa(D, [(c[0] - L, c[1]), (c[0] + L, c[1])], int(255 * g), 2); aa(D, [(c[0], c[1] - L), (c[0], c[1] + L)], int(255 * g), 2)
                disc(D, c, 3, int(255 * g))
    out += (Dr.astype(np.float32) / 255)[..., None] * RED * 1.05
    out += (D.astype(np.float32) / 255)[..., None] * 255
    return out

YL, XL = np.mgrid[0:LH, 0:LW].astype(np.float32)

def M(P, t):
    s = P["s"] * (1 + 0.006 * math.sin(t * 2.1)); cx, cy = P["cx"], P["cy"]; fc = np.array(P.get("focus", LC))
    return np.array([[s, 0, cx - s * fc[0]], [0, s, cy - s * fc[1]]], np.float32)
def to_screen(P, t, p):
    A = M(P, t); return (A[0, 0] * p[0] + A[0, 2], A[1, 1] * p[1] + A[1, 2])

# ---------- text / HUD into a light layer ----------
class Light:
    def __init__(self): self.img = Image.new("RGB", (W, H)); self.d = ImageDraw.Draw(self.img)
def tw(s, size, kind="sg"): return F(kind, size).getlength(s)
def fit(s, size, maxw=W - 120, kind="sg"):
    while tw(s, size, kind) > maxw and size > 36: size -= 4
    return size
def scale(c, a): return tuple(int(v * max(0, min(1, a))) for v in c)
def text(L, s, size, cx, cy, col, a=1.0, kind="sg", anchor="c", reveal=1.0):
    if a <= 0.01: return
    f = F(kind, size); n = int(round(len(s) * max(0, min(1, reveal))))
    x = cx - f.getlength(s) / 2 if anchor == "c" else (cx if anchor == "l" else cx - f.getlength(s))
    L.d.text((x, cy), s[:n], font=f, fill=scale(col, a), anchor="lm")
def rich(L, parts, size, cy, a=1.0):
    """parts: [(text, colour)] centred on one line."""
    f = F("sg", size); tot = sum(f.getlength(p) for p, _ in parts); x = (W - tot) / 2
    for p, c in parts: L.d.text((x, cy), p, font=f, fill=scale(c, a), anchor="lm"); x += f.getlength(p)

def fade(lt, at, d=0.25): return ease((lt - at) / d)
def wstart(ln, i): return words[min(ln["_w0"] + i, ln["_w1"] - 1)][1] - ln["_s"]

def label(L, P, t, lp, side, y, s, a, col=C_CY):
    if a <= 0.01: return
    px, py = to_screen(P, t, lp); x = 70 if side < 0 else W - 70
    k = ease(a)
    ex = px + (x - px) * k
    L.d.line([(px, py), (px + (x - px) * 0.35 * k, y), (ex, y)], fill=scale(col, a * 0.9), width=3)
    L.d.ellipse([px - 8, py - 8, px + 8, py + 8], outline=scale(col, a), width=3)
    text(L, s, 40, x, y - 28, col, a, kind="mono", anchor="l" if side < 0 else "r")

# ---------- scenes: fn(ln, lt, dur, t, L) -> frog params ----------
def S_hook(ln, lt, dur, t, L, a=1.0):
    s1 = "SEE THIS FROG'S"; z1 = fit(s1, 118)
    text(L, s1, z1, W / 2, 245, C_WH, a)
    f = F("sg", 200); rich(L, [("HEART ", C_RD), ("BEAT", C_WH)], fit("HEART BEAT", 200), 410, a)
    return dict(s=0.9, cx=540, cy=1010, scan=True)

def S_loop(ln, lt, dur, t, L):
    text(L, "BUT WHILE IT SLEEPS…", fit("BUT WHILE IT SLEEPS…", 104), W / 2, 250, C_WH, 1, reveal=lt / 0.5)
    blink = 1.0 if (t * 2.2) % 1 < 0.6 else 0.3
    text(L, "WAIT FOR IT", 66, W / 2, 380, C_CY, fade(lt, 0.6) * blink, kind="mono")
    return dict(s=0.9, cx=540, cy=1010, scan=True, b=1 - 0.25 * fade(lt, 0.8, 1.2))

def S_leaf(ln, lt, dur, t, L):
    k = eout(lt / 0.5)
    # leaf: glowing outline + veins
    cx, cy = 540, 900; Lh, Lw = 430, 300
    ts = np.linspace(0, 1, 60)
    left = [(cx - Lw * math.sin(math.pi * u) ** 0.8 * (1 - 0.25 * u), cy - Lh + 2 * Lh * u) for u in ts]
    right = [(cx + Lw * math.sin(math.pi * u) ** 0.8 * (1 - 0.25 * u), cy - Lh + 2 * Lh * u) for u in ts[::-1]]
    L.d.line(left + right + [left[0]], fill=scale((60, 190, 150), k), width=5, joint="curve")
    L.d.line([(cx, cy - Lh), (cx, cy + Lh + 40)], fill=scale((60, 190, 150), k * 0.8), width=4)
    for j in range(1, 7):
        y0 = cy - Lh + j * 2 * Lh / 7.5; wv = Lw * math.sin(math.pi * j / 7.5) ** 0.8 * 0.85
        for sgn in (-1, 1): L.d.line([(cx, y0), (cx + sgn * wv * 0.6, y0 - 70), (cx + sgn * wv, y0 - 100)], fill=scale((50, 150, 120), k * 0.6), width=3, joint="curve")
    a2 = fade(lt, wstart(ln, 4) - 0.1, 0.3)
    text(L, "TINY", 190, W / 2, 250, C_WH, fade(lt, 0.0, 0.2) * (1 - a2))
    text(L, "2–3 cm", 190, W / 2, 250, C_CY, a2)
    text(L, "TROPICAL AMERICAS", 44, W / 2, 400, C_CY, fade(lt, 0.3) * 0.9, kind="mono")
    # ruler under the frog: frog local 150..1000 (~850 u) ~ 2.6 cm at s
    s = 0.52; pxcm = 850 * s / 2.6; x0 = 540 - 1.5 * pxcm; y = 1380
    if a2 > 0:
        L.d.line([(x0, y), (x0 + 3 * pxcm * a2, y)], fill=scale(C_WH, a2), width=4)
        for mm in range(0, int(30 * a2) + 1):
            x = x0 + mm * pxcm / 10; h = 34 if mm % 10 == 0 else (20 if mm % 5 == 0 else 11)
            L.d.line([(x, y), (x, y - h)], fill=scale(C_WH, a2), width=3 if mm % 10 == 0 else 2)
            if mm % 10 == 0: text(L, str(mm // 10), 34, x, y + 30, C_WH, a2, kind="mono")
        L.d.rectangle([x0 + 2 * pxcm, y - 46, x0 + 3 * pxcm, y - 40], fill=scale(C_CY, a2))
    return dict(s=s * (0.9 + 0.1 * k), cx=540, cy=900, scan=False, focus=(500, 620))

def S_belly(ln, lt, dur, t, L):
    P = dict(s=0.95, cx=540, cy=1000, scan=True)
    text(L, "SEE-THROUGH BELLY", fit("SEE-THROUGH BELLY", 104), W / 2, 240, C_WH, fade(lt, 0, 0.25))
    for k, (lp, side, y, s) in enumerate((((500, 470), -1, 700, "HEART"), ((560, 590), 1, 880, "LIVER"),
                                         ((560, 760), 1, 1150, "GUT"), ((196, 700), -1, 1250, "BONES"))):
        label(L, P, t, lp, side, y, s, fade(lt, wstart(ln, 9) - 0.2 + 0.28 * k, 0.3), C_RD if s == "HEART" else C_CY)
    return P

def S_pack(ln, lt, dur, t, L):
    st = wstart(ln, 3); en = wstart(ln, 13)
    u = ease((lt - st) / max(0.5, en - st))
    v = int(round(89 * eout((lt - st) / max(0.5, en - st)) + (1 if lt > en else 0)))
    text(L, "SLEEP MODE", 60, W / 2, 200, C_CY, fade(lt, 0.0, 0.2), kind="mono")
    text(L, f"{min(v, 90)}%", 230, W / 2, 360, C_RD, fade(lt, st - 0.2, 0.2))
    text(L, "RED BLOOD CELLS → LIVER", fit("RED BLOOD CELLS → LIVER", 56, kind="mono"), W / 2, 500, C_WH, fade(lt, st + 0.3), kind="mono")
    return dict(s=0.78, cx=540, cy=1080, scan=False, b=1 - 0.88 * u, liver=u, inflow=math.sin(math.pi * min(1, u * 1.05)) ** 0.5 if 0 < u < 0.97 else 0)

def S_mirror(ln, lt, dur, t, L):
    z = eout(lt / 0.8)
    mi = ease((lt - 0.3) / 1.4)
    text(L, "MIRROR-COATED", fit("MIRROR-COATED", 120), W / 2, 230, C_WH, fade(lt, 0, 0.2))
    rich(L, [("LIVER", tuple(int(v) for v in SILVER))], 150, 380, fade(lt, 0.2, 0.2))
    text(L, "REFLECTIVE CRYSTALS", fit("REFLECTIVE CRYSTALS", 52, kind="mono"), W / 2, 1400, C_CY, fade(lt, 1.0), kind="mono")
    blink = 1.0 if (t * 2) % 1 < 0.6 else 0.35
    text(L, "BLOOD: HIDDEN", 52, W / 2, 1470, C_RD, fade(lt, wstart(ln, 9)) * blink, kind="mono")
    return dict(s=0.78 + 0.95 * z, cx=540, cy=1010 - 60 * z, focus=(500, 640 - 45 * z), scan=False, b=0.12, liver=1.0, mirror=mi, vis=1 - 0.55 * z, vfade=z)

def S_vanish(ln, lt, dur, t, L):
    wk = wstart(ln, 5)
    vis = 1 - 0.62 * ease((lt - 0.1) / 1.6)
    wake = ease((lt - wstart(ln, 7)) / 0.9)
    vis = vis + (1 - vis) * wake
    a1 = fade(lt, 0, 0.2) * (1 - fade(lt, wk - 0.15, 0.2))
    text(L, "2–3×", 200, W / 2, 255, C_CY, a1)
    text(L, "MORE SEE-THROUGH", fit("MORE SEE-THROUGH", 80), W / 2, 410, C_WH, a1)
    a2 = fade(lt, wk - 0.05, 0.2)
    text(L, "WAKE UP:", 110, W / 2, 260, C_WH, a2)
    text(L, "BLOOD FLOWS BACK", fit("BLOOD FLOWS BACK", 96), W / 2, 400, C_RD, a2)
    # transparency meter
    y = 525; x0, x1 = 250, 830; g = ease((lt - 0.1) / 1.6) * (1 - wake)
    L.d.rounded_rectangle([x0, y - 16, x1, y + 16], 16, outline=scale(C_CY, 0.8 * (1 - a2)), width=3)
    if a2 < 0.99: L.d.rounded_rectangle([x0 + 5, y - 11, x0 + 5 + (x1 - x0 - 10) * (0.33 + 0.55 * g), y + 11], 11, fill=scale(C_CY, 0.9 * (1 - a2)))
    text(L, "×1", 38, x0 - 20, y, C_WH, 0.85 * (1 - a2), kind="mono", anchor="r")
    text(L, "×3", 38, x1 + 20, y, C_WH, 0.85 * (1 - a2), kind="mono", anchor="l")
    return dict(s=0.86, cx=540, cy=1030, scan=True, b=0.12 + 0.88 * wake, liver=1 - wake, mirror=1 - wake, vis=vis,
                inflow=0, flash=math.exp(-max(0, lt - wstart(ln, 7)) * 6) if lt > wstart(ln, 7) else 0)

def heart_shape(cx, cy, r):
    return [(cx + r * 16 * math.sin(a) ** 3 / 16, cy - r * (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)) / 16)
            for a in np.linspace(0, 2 * math.pi, 64)]

def S_end(ln, lt, dur, t, L):
    click = ln["scene"].get("click_at", 0.45); on = ease((lt - click) / 0.3)
    lp = (lt - (dur - 0.55)) / 0.5; a1 = 1 - ease(lp / 0.5); lh = ease((lp - 0.4) / 0.6)
    text(L, "SOUNDS FAKE?", fit("SOUNDS FAKE?", 130), W / 2, 250, C_WH, a1)
    x0, x1, y, h = 170, W - 170, 560, 160
    if on > 0: L.d.rounded_rectangle([x0 + 8, y - h / 2 + 8, x0 + 8 + (x1 - x0 - 16) * on, y + h / 2 - 8], h / 2 - 8, fill=scale((40, 150, 190), a1))
    L.d.rounded_rectangle([x0, y - h / 2, x1, y + h / 2], h / 2, outline=scale(C_CY, a1), width=6)
    text(L, "FAKE", 76, x1 - 60, y, C_DIM, a1 * (1 - on), anchor="r")
    text(L, "TRUE", 76, x0 + 60, y, C_WH, a1 * on, anchor="l")
    kx = x0 + h / 2 + (x1 - x0 - h) * on; r = 3.6 * (1 + 0.15 * pulse(t))
    L.d.polygon(heart_shape(kx, y + 6, r * 16 / 3.6 * 3.4), fill=scale(C_RD, a1))
    text(L, "IT'S TRUE.", fit("IT'S TRUE.", 200), W / 2, 820, C_CY, a1 * fade(lt, click + 0.3, 0.2))
    text(L, "FOLLOW FOR MORE", fit("FOLLOW FOR MORE", 92), W / 2, 990, C_WH, a1 * fade(lt, click + 0.6, 0.2))
    P = dict(s=0.9, cx=540, cy=1010, scan=True, vis=lh, alpha=lh)
    if lh > 0: S_hook(ln, lt, dur, t, L, lh)
    return P

SCENES = dict(hook=S_hook, loop=S_loop, leaf=S_leaf, belly=S_belly, pack=S_pack, mirror=S_mirror, vanish=S_vanish, end=S_end)

# ---------- audio ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32); tt = np.arange(n) / SR
rng = np.random.default_rng(50)
def pad(freqs, at, dur, gain):
    s = np.arange(int(dur * SR)) / SR
    env = np.minimum(1, s / 0.8) * np.minimum(1, (dur - s) / 0.8)
    sig = sum(np.sin(2 * np.pi * f * s) + 0.3 * np.sin(2 * np.pi * f * 2.003 * s) for f in freqs)
    place(music, at, (sig * env).astype(np.float32), gain)
CH = [(164.81, 196.0, 246.94), (130.81, 164.81, 196.0), (146.83, 185.0, 220.0), (123.47, 146.83, 185.0)]   # Em C D Bm
for k in range(int(total / 3.0) + 1): pad(CH[k % 4], k * 3.0 - 0.4, 3.8, 0.018)
def bell(at, f, gain):
    s = np.arange(int(1.6 * SR)) / SR
    sig = np.sin(2 * np.pi * f * s) + 0.5 * np.sin(2 * np.pi * f * 2.76 * s) * np.exp(-s * 4) + 0.25 * np.sin(2 * np.pi * f * 5.4 * s) * np.exp(-s * 8)
    place(music, at, (sig * np.exp(-s * 2.2) * np.minimum(1, s / 0.002)).astype(np.float32), gain)
MEL = [659.25, 493.88, 587.33, 739.99, 659.25, 987.77, 880.0, 739.99]
for k in range(int(total / 1.5)): bell(0.75 + k * 1.5, MEL[k % 8], 0.022)
def thump(at, gain):
    s = np.arange(int(0.25 * SR)) / SR
    place(music, at, (np.sin(2 * np.pi * (48 + 30 * np.exp(-s * 30)) * s) * np.exp(-s * 18)).astype(np.float32), gain)
for k in range(int(total / BEAT) + 1): thump(k * BEAT, 0.22); thump(k * BEAT + 0.2, 0.13)
def beep(at, f=1760, gain=0.05, dur=0.12):
    s = np.arange(int(dur * SR)) / SR; place(music, at, (np.sin(2 * np.pi * f * s) * np.minimum(1, s / 0.003) * np.minimum(1, (dur - s) / 0.02)).astype(np.float32), gain)
hook_hit(music, 0.3); beep(0.0, 1975, 0.05)
for i, ln in enumerate(spec["lines"]):
    st = ln["scene"]["type"]; s0 = ln["_s"]
    if i > 0:
        whoosh(music, s0 - 0.12, 0.08, 0.3); beep(s0 - 0.1, 1568 if i % 2 else 1318, 0.04)
    if st == "mirror":
        for k in range(10): bell(s0 + 0.4 + k * 0.17, 1318.5 * (1 + 0.12 * (k % 4)), 0.015)
    if st == "vanish":
        wk = s0 + wstart(ln, 7); whoosh(music, wk, 0.12, 0.6); thump(wk, 0.35)
    if st == "end":
        c = s0 + ln["scene"].get("click_at", 0.45)
        place(music, c, (rng.normal(0, 1, int(0.05 * SR)) * np.exp(-np.arange(int(0.05 * SR)) / SR * 90)).astype(np.float32), 0.2)
        for j, f in enumerate((659.25, 830.61, 987.77, 1318.5)): bell(c + 0.15 + j * 0.07, f, 0.04)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.45)

# ---------- compositing ----------
CUTS = [ln["_s"] - 0.12 for ln in spec["lines"]][1:]
groups = caption_groups(words, 3)

def hud(L, t, ln):
    d = L.d; c = scale(C_CY, 0.75)
    for (x, y, sx, sy) in ((40, 40, 1, 1), (W - 40, 40, -1, 1), (40, 1520, 1, -1), (W - 40, 1520, -1, -1)):
        d.line([(x, y + sy * 60), (x, y), (x + sx * 60, y)], fill=c, width=4)
    text(L, "XR-050 · CENTROLENIDAE", 30, 74, 92, C_CY, 0.8, kind="mono", anchor="l")
    st = ln["scene"]["type"]; sleep = st in ("pack", "mirror") or (st == "vanish" and t - ln["_s"] < wstart(ln, 7))
    lab = "SLEEP" if sleep else "AWAKE"; blink = 1.0 if (t * 1.6) % 1 < 0.6 else 0.25
    text(L, lab, 30, W - 104, 92, C_RD if not sleep else C_CY, 0.9, kind="mono", anchor="r")
    col = C_RD if not sleep else C_CY
    d.ellipse([W - 92, 82, W - 72, 102], fill=scale(col, blink))
    for k in range(0, 30):                                          # left mm ruler
        y = 560 + k * 30; d.line([(40, y), (40 + (22 if k % 5 == 0 else 10), y)], fill=scale(C_CY, 0.45), width=2)
    # ECG strip
    y0, x0, x1 = 1488, 120, W - 120
    if st != "mirror":
        pts = []
        for x in range(x0, x1, 3):
            tb = t - (x1 - x) / 260.0
            v = pulse(tb) if tb > 0 else 0
            u = tb % BEAT
            spike = -38 * math.exp(-((u - 0.02) / 0.018) ** 2) + 16 * math.exp(-((u - 0.06) / 0.02) ** 2) - 12 * math.exp(-((u - 0.22) / 0.04) ** 2)
            pts.append((x, y0 + spike))
        fadeedge = 0.75
        d.line(pts, fill=scale(C_RD, fadeedge), width=3)
        d.ellipse([x1 - 8, pts[-1][1] - 8, x1 + 8, pts[-1][1] + 8], fill=C_RD)

def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 74; f = F("sg", size)
    while f.getlength(" ".join(ws)) > W - 220 and size > 40: size -= 4; f = F("sg", size)
    tw_ = f.getlength(" ".join(ws)); x = (W - tw_) / 2; y = 1585
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([x - 40, y - 20, x + tw_ + 40, y + size + 24], radius=20, fill=(6, 14, 28, 240), outline=(110, 225, 255, 255), width=3)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]; wl = f.getlength(w)
        if on: d.rounded_rectangle([x - 8, y - 4, x + wl + 8, y + size + 10], radius=10, fill=(110, 225, 255, 255))
        d.text((x, y - size * 0.08), w, font=f, fill=(6, 14, 28) if on else (245, 250, 255)); x += f.getlength(w + " ")

def scene_light(t, ln):
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    L = Light()
    P = SCENES[ln["scene"]["type"]](ln, lt, dur, t, L)
    hud(L, t, ln)
    fl = frog_light(t, P) * P.get("alpha", 1.0)
    out = cv2.warpAffine(fl, M(P, t), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    if P.get("scan"):
        ys = 520 + (t * 420) % 1100
        band = np.exp(-((np.arange(H, dtype=np.float32) - ys) / 70) ** 2)[:, None, None]
        out = out * (1 + 0.45 * band)
        out[int(ys) - 2:int(ys) + 2, 60:W - 60] += CYAN * 0.55
        out += band * np.array([4, 18, 30], np.float32) * (np.abs(np.arange(W) - W / 2) < W / 2 - 60)[None, :, None]
    if P.get("vfade", 0) > 0:
        yv = np.arange(H, dtype=np.float32)
        k = np.clip((yv - 470) / 160, 0, 1) * np.clip((1330 - yv) / 120, 0, 1)
        out = out * (1 - P["vfade"] * (1 - k))[:, None, None]
    if P.get("flash", 0) > 0: out += P["flash"] * np.array([60, 20, 26], np.float32)
    return out + np.asarray(L.img, np.float32)

def bloom(x):
    s = cv2.resize(x, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    b1 = cv2.resize(cv2.GaussianBlur(s, (0, 0), 3), (W, H)); b2 = cv2.resize(cv2.GaussianBlur(cv2.resize(s, (W // 16, H // 16), interpolation=cv2.INTER_AREA), (0, 0), 3), (W, H))
    return x + b1 * 0.55 + b2 * 0.45

def frame(t, fi):
    lines = spec["lines"]
    ln = active_line(spec, t) or lines[0]
    light = scene_light(t, ln)
    i = lines.index(ln)
    if i > 0:
        ph = (t - (ln["_s"] - 0.12)) / 0.32
        if ph < 1:                                    # scan-line wipe: new scene above the line, old below
            prev = scene_light(t, lines[i - 1]); yw = int(H * eout(ph))
            light[yw:] = prev[yw:]
            g = np.exp(-((np.arange(H, dtype=np.float32) - yw) / 10) ** 2)[:, None, None]
            light += g * np.array([150, 240, 255], np.float32) * 1.4
    img = BG + bloom(light)
    ox, oy = (fi * 37) % 64, (fi * 53) % 64
    img += GRAIN[oy:oy + H, ox:ox + W, None]
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    caption(im, t)
    d = ImageDraw.Draw(im)
    d.rectangle([0, H - 10, W, H], fill=(8, 18, 34)); d.rectangle([0, H - 10, int(W * t / total), H], fill=C_CY)
    return im.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), int(float(tt_) * FPS))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=24); print(f"done {total:.1f}s")
