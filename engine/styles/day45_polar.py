"""Day 45 — POLAR MINIMAL style (Antarctica is the biggest desert on Earth).
White on white. A cold snowfield whose only texture is wind-carved sastrugi (stretched fbm ridges, shaded by a low sun
from the left) and drifting blown snow (parallax streaks moving with the wind). On top, everything is drawn with thin
polar-blue hairlines, like a survey sheet: a polar-stereographic grid (latitude rings + meridians) with a stylised
continent outline and elevation contours, a thin-walled measuring cylinder for precipitation, area-true discs, a thin
sun crossed out. Type: Jost (light 300 for sentences, medium/semibold for the key word), wide letter-spacing, small
DM Mono coordinates. Colour is used sparingly: polar navy ink, glacier blue accent, one warm sand tone for the Sahara.
Scene changes are a wind gust (horizontal motion blur + brightening whiteout).
Ending: a hairline toggle whose knob is a snowflake; it slides from FAKE to TRUE and the track fills glacier blue; the last
half second redraws the polar grid of the hook so the Short loops.
Music: glass-bell pentatonic plinks (inharmonic partials), soft D-major pad, wind bed; gusts on cuts.
Usage: python3 engine/styles/day45_polar.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
_F = {}
def F(wt, s, kind="jost"):
    k = (kind, int(wt), int(s))
    if k not in _F:
        if kind == "mono": _F[k] = ImageFont.truetype(f"{FONTS}/DMMono-Medium.ttf", int(s))
        else:
            f = ImageFont.truetype(f"{FONTS}/Jost-VF.ttf", int(s)); f.set_variation_by_axes([int(wt)]); _F[k] = f
    return _F[k]

INK = (22, 46, 86)          # polar navy
ICE = (64, 140, 200)        # glacier blue
PALE = (150, 182, 214)      # hairline blue
FROST = (226, 236, 246)     # ice fill
SAND = (205, 150, 84)       # Sahara
WHITE = (255, 255, 255)

# ---------- static snowfield ----------
def fbm(seed, scales, amps, size, stretch=1.0):
    rr = np.random.default_rng(seed); acc = np.zeros((size[1], size[0]), np.float32)
    for s, a in zip(scales, amps):
        g = rr.random((max(2, int(size[1] / s) + 2), max(2, int(size[0] / (s * stretch)) + 2))).astype(np.float32)
        acc += a * cv2.resize(g, size, interpolation=cv2.INTER_CUBIC)
    acc -= acc.min(); return acc / max(1e-6, acc.max())
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
BW = W + 400
_h = fbm(3, [60, 26, 10], [1, 0.5, 0.25], (BW, H), stretch=5.0)          # sastrugi height (stretched along the wind)
_sh = np.clip(np.gradient(_h, axis=1) * 90, -1, 1)                       # low sun from the left
_v = (np.arange(H, dtype=np.float32) / H)[:, None]
_band = np.clip((_v - 0.08) / 0.6, 0, 1) ** 1.2                           # texture fades toward the top (sky-ish)
BG = np.empty((H, BW, 3), np.float32)
base = np.stack([246 - 8 * (1 - _v), 249 - 5 * (1 - _v), 252 + 0 * _v], -1)
BG[:] = base
BG -= (np.stack([16, 11, 4], -1) * (np.clip(-_sh, 0, 1) * _band)[..., None])
BG += (np.stack([5, 4, 2], -1) * (np.clip(_sh, 0, 1) * _band)[..., None])
BG += ((fbm(9, [400, 120], [1, 0.5], (BW, H)) - 0.5) * 6)[..., None]
SNOW = [(random.Random(i).uniform(0, W), random.Random(i + 500).uniform(0, H), random.Random(i + 77).uniform(0.4, 1.6)) for i in range(110)]

def background(t):
    ox = int(200 + 160 * math.sin(t * 0.05))
    out = BG[:, ox:ox + W].copy()
    return out

# ---------- drawing helpers (on a uint8 HxWx3 array) ----------
def P(pts): return (np.array(pts, np.float32).reshape(-1, 1, 2) * 8).astype(np.int32)
def line(a, pts, col, w=3, closed=False, al=1.0):
    if al <= 0.01 or len(pts) < 2: return
    if al >= 0.99: cv2.polylines(a, [P(pts)], closed, col, max(1, int(w)), cv2.LINE_AA, shift=3); return
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, y0 = max(0, int(min(xs) - w - 2)), max(0, int(min(ys) - w - 2)); x1, y1 = min(W, int(max(xs) + w + 3)), min(H, int(max(ys) + w + 3))
    if x1 <= x0 or y1 <= y0: return
    reg = a[y0:y1, x0:x1]; tmp = reg.copy()
    cv2.polylines(tmp, [P([(x - x0, y - y0) for x, y in pts])], closed, col, max(1, int(w)), cv2.LINE_AA, shift=3)
    a[y0:y1, x0:x1] = (reg * (1 - al) + tmp * al).astype(np.uint8)
def fill(a, pts, col, al=1.0):
    if al <= 0.01: return
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, y0 = max(0, int(min(xs) - 2)), max(0, int(min(ys) - 2)); x1, y1 = min(W, int(max(xs) + 3)), min(H, int(max(ys) + 3))
    if x1 <= x0 or y1 <= y0: return
    reg = a[y0:y1, x0:x1]; tmp = reg.copy()
    cv2.fillPoly(tmp, [P([(x - x0, y - y0) for x, y in pts])], col, cv2.LINE_AA, shift=3)
    a[y0:y1, x0:x1] = (reg * (1 - al) + tmp * al).astype(np.uint8)
def circ_pts(cx, cy, r, n=120, a0=0, a1=2 * math.pi):
    return [(cx + r * math.sin(a0 + (a1 - a0) * k / n), cy - r * math.cos(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]
def shadow(a, pts, off=(10, 16), blur=18, strength=0.10):
    m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [P([(x + off[0], y + off[1]) for x, y in pts])], 255, cv2.LINE_AA, shift=3)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, y0 = max(0, int(min(xs)) - 60), max(0, int(min(ys)) - 60); x1, y1 = min(W, int(max(xs)) + 80), min(H, int(max(ys)) + 80)
    sm = cv2.GaussianBlur(m[y0:y1, x0:x1].astype(np.float32) / 255, (0, 0), blur)[..., None] * strength
    reg = a[y0:y1, x0:x1].astype(np.float32); a[y0:y1, x0:x1] = (reg * (1 - sm) + np.array([40, 70, 120], np.float32) * sm).astype(np.uint8)

# ---------- text (PIL, drawn after the hairlines) ----------
TXT = []                                    # (s, wt, size, cx, cy, col, alpha, track, kind)
def text(s, wt, size, cx, cy, col=INK, al=1.0, track=0.0, kind="jost", reveal=1.0):
    if al > 0.01: TXT.append((s, wt, size, cx, cy, col, al, track, kind, reveal))
def tw(s, wt, size, track=0.0, kind="jost"):
    f = F(wt, size, kind); return sum(f.getlength(c) for c in s) + track * size * (len(s) - 1)
def fit(s, wt, size, track=0.0, maxw=W - 150):
    while tw(s, wt, size, track) > maxw and size > 36: size -= 2
    return size
def draw_texts(img):
    d = ImageDraw.Draw(img, "RGBA")
    for s, wt, size, cx, cy, col, al, track, kind, rev in TXT:
        f = F(wt, size, kind); x = cx - tw(s, wt, size, track, kind) / 2
        asc, desc = f.getmetrics(); y = cy - (asc + desc) / 2 + desc * 0.35
        n = len(s); shown = rev * n
        for i, c in enumerate(s):
            a = al * max(0.0, min(1.0, shown - i))
            if a > 0.01: d.text((x, y + (1 - a) * 10), c, font=f, fill=col + (int(255 * a),))
            x += f.getlength(c) + track * size
    TXT.clear()

def fade(lt, at, d=0.3): return ease((lt - at) / d)
def wt_(ln, i): return words[min(ln["_w0"] + i, ln["_w1"] - 1)][1] - ln["_s"]

# ---------- motifs ----------
# coast colatitude (deg from pole) by longitude (deg east, 0 = up); stylised, not survey-accurate
COAST = [(0, 20), (30, 21), (60, 23), (90, 24), (120, 24), (150, 22), (165, 18), (180, 12), (200, 13), (215, 14), (240, 16),
         (260, 17), (280, 17), (288, 17.5), (293, 19), (296, 24), (298.5, 27.5), (300.5, 26), (302.5, 17), (306, 13), (310, 12.5), (320, 13),
         (330, 15), (340, 17), (350, 19), (360, 20)]
def coast_r(lon):
    lon %= 360
    for (a, ra), (b, rb) in zip(COAST, COAST[1:]):
        if a <= lon <= b: u = (lon - a) / (b - a); return ra + (rb - ra) * ease(u)
    return 20
_CN = [random.Random(k).uniform(-1, 1) for k in range(400)]
def continent(cx, cy, R, rot=0.0, scale=1.0, n=360):
    pts = []
    for k in range(n):
        lon = k * 360 / n
        r = coast_r(lon) / 24 * scale
        r *= 1 + (0.012 * math.sin(lon * 0.31 + 1) + 0.008 * math.sin(lon * 0.83 + 2) + 0.004 * _CN[k % 400]) * (1 if scale > 0.95 else 0.6)
        th = math.radians(lon + rot)
        pts.append((cx + R * r * math.sin(th), cy - R * r * math.cos(th)))
    return pts

def polar_map(a, cx, cy, R, rot=0.0, al=1.0, grow=1.0, contours=1.0, fill_al=1.0):
    """polar-stereographic survey plate: latitude rings, meridians, continent with elevation contours."""
    for k, lat in enumerate((1.0, 1.25)):                                   # latitude rings (60°S, 50°S)
        line(a, circ_pts(cx, cy, R * lat * grow), PALE, 2, al=al * 0.9)
    for m in range(12):
        th = math.radians(m * 30 + rot)
        line(a, [(cx + R * 0.08 * math.sin(th), cy - R * 0.08 * math.cos(th)), (cx + R * 1.25 * grow * math.sin(th), cy - R * 1.25 * grow * math.cos(th))], PALE, 2, al=al * 0.6)
    pts = continent(cx, cy, R, rot, grow)
    shadow(a, pts, strength=0.12 * al * fill_al)
    fill(a, pts, (251, 253, 255), al * fill_al)
    for i, s in enumerate((0.78, 0.56, 0.34)):                            # elevation contours
        u = max(0.0, min(1.0, contours * 3 - i))
        if u > 0: line(a, continent(cx, cy, R, rot, s * grow), (120, 160, 205), 2, True, al * u * 0.9)
    line(a, pts, INK, 3, True, al)
    line(a, circ_pts(cx, cy, 6), INK, 3, True, al)                          # the pole

def sun_icon(a, cx, cy, r, col, al=1.0, cross=0.0, rot=0.0):
    line(a, circ_pts(cx, cy, r, 60), col, 4, True, al)
    for k in range(12):
        th = rot + k * math.pi / 6
        line(a, [(cx + r * 1.35 * math.sin(th), cy - r * 1.35 * math.cos(th)), (cx + r * 1.7 * math.sin(th), cy - r * 1.7 * math.cos(th))], col, 4, al=al)
    if cross > 0:
        L = r * 2.1; u = ease(cross)
        line(a, [(cx - L, cy - L), (cx - L + 2 * L * u, cy - L + 2 * L * u)], ICE, 6, al=al)

def flake(a, cx, cy, r, col=ICE, w=4, al=1.0, rot=0.0):
    for k in range(6):
        th = rot + k * math.pi / 3; ex, ey = cx + r * math.sin(th), cy - r * math.cos(th)
        line(a, [(cx, cy), (ex, ey)], col, w, al=al)
        for f_ in (0.55,):
            bx, by = cx + r * f_ * math.sin(th), cy - r * f_ * math.cos(th)
            for s in (-1, 1):
                th2 = th + s * 0.75
                line(a, [(bx, by), (bx + r * 0.32 * math.sin(th2), by - r * 0.32 * math.cos(th2))], col, w, al=al)

def dunes(a, y0, t, col, al=1.0, n=5):
    for k in range(n):
        y = y0 + k * 70; ph = k * 1.7 + t * 0.15
        pts = [(x, y + 26 * math.sin(x / 170 + ph) + 12 * math.sin(x / 61 + ph * 1.3)) for x in range(-10, W + 20, 12)]
        line(a, pts, col, 3, al=al * (1 - k * 0.12))

def cloud(a, cx, cy, s, col=INK, al=1.0):
    m = np.zeros((H, W), np.uint8)
    for ox, oy, r in ((-0.5, 0.12, 0.34), (-0.08, -0.12, 0.46), (0.42, 0.06, 0.36)):
        cv2.circle(m, (int(cx + ox * s), int(cy + oy * s)), int(r * s), 255, -1)
    cv2.rectangle(m, (int(cx - 0.84 * s), int(cy + 0.1 * s)), (int(cx + 0.78 * s), int(cy + 0.42 * s)), 255, -1)
    cv2.rectangle(m, (0, int(cy + 0.42 * s)), (W, H), 0, -1)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    pts = [(float(q[0][0]), float(q[0][1])) for q in max(cs, key=len)][::3]
    shadow(a, pts, strength=0.10 * al)
    fill(a, pts, (252, 253, 255), al)
    line(a, pts, col, 4, True, al)

# ---------- scenes ----------
HX, HY, HR = 540, 1080, 300
def S_hook(a, sc, ln, lt, dur, t):
    polar_map(a, HX, HY, HR, rot=-8 + t * 0.5)
    sun_icon(a, 870, 760, 36, SAND, 1, cross=1.0, rot=t * 0.5)
    text("THE BIGGEST", 300, fit("THE BIGGEST", 300, 124, 0.08), W / 2, 200, INK, 1, 0.08)
    text("DESERT ON EARTH", 500, fit("DESERT ON EARTH", 500, 124, 0.04), W / 2, 345, INK, 1, 0.04)
    text("ISN'T HOT.", 600, 158, W / 2, 515, ICE, 1, 0.06)
    text("90° S", 400, 34, HX, HY + HR * 1.25 + 44, PALE, 1, 0.3, "mono")

def S_loop(a, sc, ln, lt, dur, t):
    k = wt_(ln, 5) - 0.15                                   # "And the reason…"
    g = ease((lt - k) / 0.7)
    sun_icon(a, 540, 820, 70, SAND, 1 - g * 0.7, cross=g, rot=t * 0.4)
    for j in range(5):                                      # dunes freeze: sand lines turn ice blue
        col = tuple(int(SAND[c] * (1 - g) + PALE[c] * g) for c in range(3))
        y = 1040 + j * 80; ph = j * 1.7 + t * 0.12 * (1 - g)
        pts = [(x, y + 28 * math.sin(x / 170 + ph) + 12 * math.sin(x / 61 + ph * 1.3)) for x in range(-10, W + 20, 12)]
        line(a, pts, col, 3, al=1 - j * 0.12)
    s_in = fade(lt, 0.0, 0.25)
    text("IT'S NOT", 300, 104, W / 2, 210, INK, 1, 0.1)
    text("THE SAHARA.", 600, fit("THE SAHARA.", 600, 150, 0.04), W / 2, 360, SAND, s_in, 0.04)
    if g > 0:
        line(a, [(150, 360), (150 + 780 * g, 360)], ICE, 7)        # struck through by the wind
    text("…and the reason why", 300, 62, W / 2, 520, INK, fade(lt, k, 0.35))
    text("is even stranger.", 500, 62, W / 2, 600, ICE, fade(lt, k + 0.5, 0.35))

def S_reveal(a, sc, ln, lt, dur, t):
    gr = 0.9 + 0.1 * eout(lt / 0.6)
    polar_map(a, 540, 1020, 380 * gr, rot=-8 + t * 0.5, contours=lt / 0.9)
    for j in range(3):                                       # survey pings from the pole
        u = (lt - 0.15 - j * 0.35) / 1.2
        if 0 < u < 1: line(a, circ_pts(540, 1020, 30 + 420 * eout(u)), ICE, 3, True, (1 - u) * 0.7)
    rv = min(1.0, lt / 0.55)
    text("ANTARCTICA", 500, fit("ANTARCTICA", 500, 140, 0.16), W / 2, 300, INK, 1, 0.16, reveal=rv * 1.0 + 0.001)
    text("14.2 MILLION KM²  ·  90° S", 400, 34, W / 2, 430, ICE, fade(lt, 0.5), 0.2, "mono")

def S_sky(a, sc, ln, lt, dur, t):
    k = wt_(ln, 5) - 0.1                                    # "It's about…"
    g = ease((lt - k) / 0.4)
    sun_icon(a, 540, 980, 90, SAND, 1 - g, cross=fade(lt, 0.5, 0.4), rot=t * 0.4)
    text("A DESERT", 300, 112, W / 2, 210, INK, 1, 0.1)
    text("ISN'T ABOUT HEAT.", 600, fit("ISN'T ABOUT HEAT.", 600, 112, 0.03), W / 2, 345, INK, 1 - g * 0.75, 0.03)
    if g > 0:
        cloud(a, 540, 860, 230, INK, g)
        for i in range(7):                                   # very few drops fall
            x = 400 + i * 47; ph = (lt * 0.9 + i * 0.37) % 1.0; y = 960 + ph * 420
            line(a, [(x, y), (x - 3, y + 26)], ICE, 4, al=g * (1 - ph) * (0.6 if i % 2 else 1))
        text("IT'S WHAT FALLS", 500, fit("IT'S WHAT FALLS", 500, 100, 0.06), W / 2, 500, ICE, g, 0.06)
        text("FROM THE SKY", 500, fit("FROM THE SKY", 500, 100, 0.06), W / 2, 615, ICE, fade(lt, k + 0.6), 0.06)

GX, GY0, GY1, GW = 540, 1440, 760, 220                     # cylinder centre x, bottom (0 mm), top (300 mm), width
def gy(v): return GY0 - (GY0 - GY1) * v / 300
def cylinder(a, level, col, t, al_line=1.0):
    x0, x1 = GX - GW / 2, GX + GW / 2
    if level > 0.5:
        top = gy(level); wave = [(x, top + 5 * math.sin(x / 26 + t * 3)) for x in np.linspace(x0 + 6, x1 - 6, 30)]
        fill(a, wave + [(x1 - 6, GY0 - 6), (x0 + 6, GY0 - 6)], col, 0.85)
        line(a, wave, INK, 2)
    line(a, [(x0, GY1 - 50), (x0, GY0), (x1, GY0), (x1, GY1 - 50)], INK, 4)
    line(a, [(x0 - 14, GY1 - 64), (x0, GY1 - 50)], INK, 4); line(a, [(x1 + 14, GY1 - 64), (x1, GY1 - 50)], INK, 4)
    for v in range(0, 301, 25):
        y = gy(v); L = 34 if v % 50 == 0 else 18
        line(a, [(x0, y), (x0 + L, y)], INK, 3)
        if v % 50 == 0: text(f"{v}", 400, 32, x0 - 60, y, INK, 0.85, 0, "mono")
    text("mm / year", 400, 30, x0 - 60, GY0 + 50, PALE, 1, 0, "mono")

def S_gauge(a, sc, ln, lt, dur, t):
    ph = sc.get("phase", "limit")
    if ph == "limit":
        u = ease((lt - 0.3) / 2.2); v = 250 * u
        cylinder(a, v, (180, 208, 232), t)
        al = fade(lt, 2.2, 0.3); y = gy(250)
        for xx_ in range(80, 1000, 34):                    # dashed desert line
            line(a, [(xx_, y), (xx_ + 18, y)], SAND, 4, al=al)
        text("DESERT LINE", 500, 40, 860, y - 40, SAND, al, 0.12)
        text("LESS THAN", 300, 96, W / 2, 210, INK, 1, 0.1)
        text(f"{int(round(v)):d} mm", 600, 150, W / 2, 360, ICE, 1, 0.02)
        text("of rain or snow a year", 300, 58, W / 2, 500, INK, fade(lt, 0.4), 0.02)
    else:
        u = ease((lt - 0.2) / 1.6); v = 250 - 200 * u
        y = gy(250)
        for xx_ in range(80, 1000, 34): line(a, [(xx_, y), (xx_ + 18, y)], SAND, 4)
        text("DESERT LINE", 500, 40, 860, y - 40, SAND, 1, 0.12)
        cylinder(a, v, tuple(int(c) for c in np.array([180, 208, 232]) * (1 - u) + np.array([236, 243, 250]) * u), t)
        al = fade(lt, 1.6, 0.4)
        for j in range(3): flake(a, GX - 60 + j * 60, gy(v) - 40 - j * 0 , 18, ICE, 3, al, t * 0.6 + j)
        line(a, [(GX + GW / 2 + 20, gy(50)), (GX + GW / 2 + 120, gy(50))], ICE, 4, al=al)
        text("POLAR", 500, 40, 850, gy(50) - 28, ICE, al, 0.14)
        text("PLATEAU", 500, 40, 850, gy(50) + 22, ICE, al, 0.14)
        text("ANTARCTIC INTERIOR", 400, 56, W / 2, 210, INK, 1, 0.08)
        text(f"≈ {int(round(v)):d} mm", 600, 150, W / 2, 360, ICE, 1, 0.02)
        text("a year", 300, 58, W / 2, 500, INK, 1, 0.02)

def S_compare(a, sc, ln, lt, dur, t):
    k = wt_(ln, 5) - 0.1                                   # "it beats the Sahara's"
    ga = eout((lt - 0.1) / 0.8); gs = eout((lt - k) / 0.7)
    RA = 250; RS = RA * math.sqrt(9 / 14)                  # equal-area scale
    cyA, cyS = 1060, 1060 + (RA - RS)
    if ga > 0:
        # Antarctica drawn as a disc of equal area (continent inside the plate)
        line(a, circ_pts(290, cyA, RA * ga), INK, 3, True)
        fill(a, circ_pts(290, cyA, RA * ga), (238, 244, 251), 1)
        line(a, circ_pts(290, cyA, RA * ga), INK, 3, True)
        pts = continent(290, cyA, RA * 0.82 * ga, -8 + t * 0.5)
        line(a, pts, ICE, 3, True)
        n = 14 * ga
        text(f"{n:.0f}M km²", 600, 72, 290, cyA + RA + 70, INK, 1, 0.02)
        text("ANTARCTICA", 500, 34, 290, cyA + RA + 130, ICE, 1, 0.2)
    if gs > 0:
        fill(a, circ_pts(800, cyS, RS * gs), (246, 228, 200), 1)
        for j in range(4):
            yj = cyS - RS * 0.5 + j * RS * 0.33
            hw = math.sqrt(max(0, (RS * gs) ** 2 - (yj - cyS) ** 2)) * 0.92
            pts = [(x, yj + 10 * math.sin(x / 40 + j)) for x in np.linspace(800 - hw, 800 + hw, 24)]
            line(a, pts, SAND, 3)
        line(a, circ_pts(800, cyS, RS * gs), SAND, 3, True)
        text(f"~{9 * gs:.0f}M km²", 600, 72, 800, cyA + RA + 70, SAND, 1, 0.02)
        text("SAHARA", 500, 34, 800, cyA + RA + 130, SAND, 1, 0.2)
    text("14 MILLION KM²", 600, fit("14 MILLION KM²", 600, 120, 0.03), W / 2, 220, INK, 1, 0.03)
    s = fade(lt, k + 0.8, 0.35)
    text("THE BIGGEST DESERT", 500, fit("THE BIGGEST DESERT", 500, 84, 0.08), W / 2, 380, ICE, max(fade(lt, 0.3), 0), 0.08)
    if s > 0:
        x0, x1, y0, y1 = 190, 890, 468, 562
        line(a, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], ICE, 3, True, s)
        text("BEATS THE SAHARA", 500, 44, W / 2, 515, ICE, s, 0.2)

def S_end(a, sc, ln, lt, dur, t):
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.35)
    text("SOUNDS FAKE?", 300, 112, W / 2, 210, INK, 1, 0.1)
    y = 430; x0, x1, hh = 200, 880, 128
    pill = circ_pts(x1 - hh / 2, y, hh / 2, 30, 0, math.pi) + circ_pts(x0 + hh / 2, y, hh / 2, 30, math.pi, 2 * math.pi)
    kx = x0 + hh / 2 + (x1 - x0 - hh) * on
    if on > 0:
        trk = circ_pts(kx, y, hh / 2 - 8, 30, 0, math.pi) + circ_pts(x0 + hh / 2, y, hh / 2 - 8, 30, math.pi, 2 * math.pi)
        fill(a, trk, (196, 222, 242), 1)
    line(a, pill, INK, 4, True)
    fill(a, circ_pts(kx, y, hh / 2 - 16, 60), WHITE, 1)
    line(a, circ_pts(kx, y, hh / 2 - 16, 60), INK, 4, True)
    flake(a, kx, y, hh / 2 - 34, ICE, 4, 1, on * math.pi / 3 * 2)
    text("FAKE", 500, 58, (x0 + x1) / 2 + 60, y, SAND, 1 - on, 0.2)
    text("TRUE", 600, 58, (x0 + x1) / 2 - 60, y, INK, ease((on - 0.5) / 0.4), 0.2)
    text("IT'S TRUE.", 600, fit("IT'S TRUE.", 600, 170, 0.04), W / 2, 650, ICE, fade(lt, click + 0.3, 0.3), 0.04)
    text("Follow for more.", 300, 70, W / 2, 790, INK, fade(lt, click + 0.6, 0.3), 0.04)
    lp = ease((lt - (dur - 0.7)) / 0.6)                     # redraw the hook's polar plate for the loop
    if lp > 0: polar_map(a, HX, HY, HR, rot=-8 + t * 0.5, al=lp, grow=0.9 + 0.1 * lp)
    else:
        for j in range(3): flake(a, 300 + j * 240, 1150 + 40 * math.sin(t + j), 40, PALE, 3, fade(lt, click + 0.8), t * 0.3 + j)

SCENES = dict(hook=S_hook, loop=S_loop, reveal=S_reveal, sky=S_sky, gauge=S_gauge, compare=S_compare, end=S_end)

# ---------- audio ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
rng = np.random.default_rng(45)
wz = rng.normal(0, 1, n).astype(np.float32)
wz = np.convolve(wz, np.ones(60) / 60, "same") * 6
tt = np.arange(n) / SR
music += wz * (0.025 + 0.02 * np.sin(2 * np.pi * 0.13 * tt) ** 2)
def bell(f, gain=0.05, dur=2.2):
    s = np.arange(int(dur * SR)) / SR
    sig = (np.sin(2 * np.pi * f * s) + 0.45 * np.sin(2 * np.pi * f * 2.76 * s) * np.exp(-s * 3) + 0.2 * np.sin(2 * np.pi * f * 5.4 * s) * np.exp(-s * 6))
    return (sig * np.exp(-s * 2.2) * np.minimum(1, s / 0.004)).astype(np.float32) * gain
PENT = [587.33, 659.25, 739.99, 880.0, 987.77, 1174.66, 1318.5]
CH = [[146.83, 220.0, 293.66, 369.99], [123.47, 185.0, 246.94, 293.66], [98.0, 146.83, 196.0, 246.94], [110.0, 164.81, 220.0, 277.18]]
BAR = 3.2
rr = random.Random(45)
for b in range(int(total / BAR) + 1):
    ch = CH[b % 4]; s = np.arange(int(BAR * 1.3 * SR)) / SR
    env = np.minimum(1, s / 0.8) * np.exp(-s * 0.3)
    pad = sum(np.sin(2 * np.pi * f * s * (1 + d)) / (1 + 0.5 * i) for i, f in enumerate(ch) for d in (-0.002, 0.002))
    place(music, b * BAR, (pad * env * 0.03).astype(np.float32))
    for k in range(8):
        if rr.random() < 0.62: place(music, b * BAR + k * BAR / 8, bell(rr.choice(PENT), 0.035))
hook_hit(music, 0.3); place(music, 0.0, bell(1174.66, 0.08))
def gust(at, gain=0.16, dur=0.6):
    s = np.arange(int(dur * SR)) / SR; z = rng.normal(0, 1, len(s)).astype(np.float32)
    z = np.convolve(z, np.ones(10) / 10, "same"); place(music, max(0, at - dur * 0.55), z * np.sin(np.pi * s / dur) ** 2, gain)
for i, ln in enumerate(spec["lines"]):
    st = ln["scene"]["type"]
    if i > 0: gust(ln["_s"], 0.2); whoosh(music, ln["_s"], 0.05)
    if st == "reveal":
        for j, f in enumerate((587.33, 880.0, 1174.66)): place(music, ln["_s"] + 0.05 + j * 0.12, bell(f, 0.07, 2.5))
    if st == "end":
        c = ln["_s"] + ln["scene"].get("click_at", 0.45)
        s = np.arange(int(0.05 * SR)) / SR; place(music, c, (rng.normal(0, 1, len(s)) * np.exp(-s * 120)).astype(np.float32), 0.25)
        for j, f in enumerate((587.33, 739.99, 880.0, 1174.66)): place(music, c + 0.25 + j * 0.06, bell(f, 0.06, 2.5))
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.4)

# ---------- compositing ----------
STARTS = [ln["_s"] for ln in spec["lines"]]
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 70
    f = F(600, size)
    while f.getlength(" ".join(ws)) > W - 240 and size > 36: size -= 4; f = F(600, size)
    tw_ = f.getlength(" ".join(ws)); x = (W - tw_) / 2; y = 1588
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([x - 46, y - 24, x + tw_ + 46, y + size + 26], radius=18, fill=(255, 255, 255, 246), outline=INK + (255,), width=3)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]; wl = f.getlength(w)
        if on: d.rounded_rectangle([x - 10, y - 4, x + wl + 10, y + size + 8], radius=10, fill=ICE + (255,))
        d.text((x, y - size * 0.06), w, font=f, fill=(255, 255, 255, 255) if on else INK + (255,)); x += f.getlength(w + " ")

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    a = background(t).clip(0, 255).astype(np.uint8)
    for x, y0, sp in SNOW:                                  # blown snow, parallax by size
        xv = (x + t * 260 * sp) % (W + 80) - 40; yv = (y0 + 30 * math.sin(t * 0.8 + x) + t * 25 * sp) % H
        L = int(10 + 22 * sp); c = int(232 - 22 * sp)
        cv2.line(a, (int(xv), int(yv)), (int(xv - L), int(yv - L * 0.08)), (c - 14, c - 4, min(255, c + 12)), max(1, int(sp * 1.8)), cv2.LINE_AA)
    SCENES[ln["scene"]["type"]](a, ln["scene"], ln, lt, dur, t)
    img = Image.fromarray(a); draw_texts(img)
    gk = 0.0
    for s in STARTS[1:]:                                    # wind-gust whiteout on cuts
        if s - 0.1 <= t < s + 0.22: gk = max(gk, 1 - abs(t - s) / (0.1 if t < s else 0.22))
    if gk > 0.02:
        arr = np.asarray(img); k = int(1 + 140 * gk)
        arr = cv2.blur(arr, (k, 1)).astype(np.float32); arr = arr + (255 - arr) * 0.45 * gk
        img = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    caption(img, t)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 8, W, H], fill=(214, 226, 238)); d.rectangle([0, H - 8, int(W * t / total), H], fill=ICE)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=24); print(f"done {total:.1f}s")
