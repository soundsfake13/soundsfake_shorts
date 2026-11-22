"""Day 51 — THERMAL CAMERA style (polar bears: black skin, clear hollow hairs, and they almost vanish on a heat camera).
Every scene is a scalar *temperature field* rendered at sensor resolution (540x960), softened, given sensor noise and
fixed-pattern column noise, upscaled and mapped through an 'ironbow' palette (black -> indigo -> violet -> magenta ->
orange -> yellow -> white-hot), with a glow on the hottest pixels. Nothing is painted in colour directly: bear, ice,
hairs, light rays and breath are all temperatures, so the whole frame reads like real IR footage.
Crisp camera chrome sits on top: corner brackets, mode/REC/battery readouts, an ironbow scale bar with degree ticks,
and a moving spot-meter crosshair whose reading is sampled from the field. Type: Big Shoulders Display Black with an
ironbow gradient fill + dark-violet outline (white-hot words), 'BLACK' set in black on a white-hot plate;
JetBrains Mono for readouts. Cuts are 'NUC' shutter recalibrations: the image freezes, flattens to a grey field and
settles into the next scene (with a shutter clack). The bear is shown with a 'FUR FILTER' until the payoff, where the
filter turns off and the bear cools into the snow, leaving only eyes, nose and breath.
Ending: an ironbow toggle FAKE -> TRUE whose fill heats up along the palette, with a white-hot paw-print knob;
dissolves back into the hook for the loop. Music: original D-minor cold synth (sub drone, glassy triangle arpeggio,
icy wind), warming in timbre near the end, shutter clacks on cuts.
Usage: python3 engine/styles/day51_thermal.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
FW, FH = W // 2, H // 2

_F = {}
def F(kind, s, wt=900):
    k = (kind, int(s), wt)
    if k not in _F:
        f = ImageFont.truetype(f"{FONTS}/{'BigShouldersDisplay-VF.ttf' if kind == 'bs' else 'JetBrainsMono-VF.ttf'}", int(s))
        f.set_variation_by_axes([wt]); _F[k] = f
    return _F[k]

# ---------- ironbow palette ----------
STOPS = [(0.0, (0, 0, 6)), (0.12, (16, 2, 52)), (0.3, (88, 6, 140)), (0.48, (178, 24, 128)), (0.62, (226, 70, 50)),
         (0.76, (247, 140, 18)), (0.9, (255, 214, 60)), (1.0, (255, 252, 230))]
LUT = np.zeros((256, 3), np.float32)
for i in range(256):
    v = i / 255
    for (a, ca), (b, cb) in zip(STOPS[:-1], STOPS[1:]):
        if a <= v <= b:
            u = (v - a) / (b - a); LUT[i] = np.array(ca) * (1 - u) + np.array(cb) * u; break
def iron(v): return tuple(int(c) for c in LUT[int(max(0, min(1, v)) * 255)])
WHITE, INK, DIM = (250, 248, 240), (20, 0, 40), (150, 120, 170)
YEL = iron(0.9); ORG = iron(0.74)

# ---------- shared field pieces ----------
rng0 = np.random.default_rng(51)
def fbm(h, w, seed, octaves=4, base=40):
    r = np.random.default_rng(seed); out = np.zeros((h, w), np.float32); amp = 1.0
    for o in range(octaves):
        s = max(2, base >> o)
        n = r.normal(0, 1, (h // s + 2, w // s + 2)).astype(np.float32)
        out += cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC) * amp; amp *= 0.5
    return out / 1.8
FY, FX = np.mgrid[0:FH, 0:FW].astype(np.float32)
HOR = 575
def landscape():
    f = 0.06 + 0.07 * (FY / HOR)
    xr = FX[0]; ridge = HOR - 30 - 22 * np.sin(xr / 70) - 14 * np.sin(xr / 23 + 1) - 8 * fbm(1, FW, 3, 3, 20)[0] * 3
    f = np.where(FY > ridge[None, :], 0.16 + 0.03 * fbm(FH, FW, 4, 3, 30), f)
    g = FY > HOR
    f = np.where(g, 0.2 + 0.05 * (FY - HOR) / (FH - HOR) + 0.035 * fbm(FH, FW, 5, 4, 40), f)
    return f.astype(np.float32)
LAND = landscape()
FPN = (np.random.default_rng(9).normal(0, 1, FW) * 0.006).astype(np.float32)[None, :]
FLAKES = rng0.uniform(0, 1, (140, 4)).astype(np.float32)
def snow(f, t, amt=0.12, wind=30):
    for x, y, sp, sz in FLAKES:
        yy = (y * FH + t * (40 + 50 * sp)) % FH; xx = (x * FW + t * wind * (0.5 + sp) + 8 * math.sin(t * 1.5 + x * 20)) % FW
        cv2.circle(f, (int(xx * 4), int(yy * 4)), int((0.8 + 1.4 * sz) * 4), float(f[int(yy) % FH, int(xx) % FW] + amt), -1, cv2.LINE_AA, shift=2)

# ---------- bear model (side view, facing right) in a local canvas ----------
BW, BH = 960, 640
def build_bear():
    m = np.zeros((BH, BW), np.uint8)
    cv2.ellipse(m, (420, 330), (270, 150), 0, 0, 360, 255, -1, cv2.LINE_AA)       # body
    cv2.ellipse(m, (230, 320), (150, 150), 0, 0, 360, 255, -1, cv2.LINE_AA)       # rump
    cv2.ellipse(m, (580, 280), (140, 125), -10, 0, 360, 255, -1, cv2.LINE_AA)     # shoulder hump
    cv2.fillPoly(m, [np.array([[620, 220], [760, 205], [800, 300], [650, 360]], np.int32)], 255, cv2.LINE_AA)  # neck
    cv2.ellipse(m, (775, 245), (90, 68), 8, 0, 360, 255, -1, cv2.LINE_AA)         # head
    cv2.ellipse(m, (858, 272), (66, 40), 12, 0, 360, 255, -1, cv2.LINE_AA)        # snout
    cv2.circle(m, (735, 182), 24, 255, -1, cv2.LINE_AA)                           # ear
    for (x0, x1) in ((150, 250), (270, 350), (560, 640), (650, 730)):            # legs
        cv2.line(m, ((x0 + x1) // 2, 380), ((x0 + x1) // 2 + 6, 560), 255, x1 - x0, cv2.LINE_AA)
        cv2.ellipse(m, ((x0 + x1) // 2 + 18, 580), ((x1 - x0) // 2 + 14, 26), 0, 0, 360, 255, -1, cv2.LINE_AA)
    cv2.ellipse(m, (95, 300), (28, 22), 0, 0, 360, 255, -1, cv2.LINE_AA)         # tail
    m = cv2.GaussianBlur(m, (0, 0), 1.5)
    mf = m.astype(np.float32) / 255
    d = cv2.distanceTransform((m > 127).astype(np.uint8), cv2.DIST_L2, 5)
    warm = 0.5 + 0.38 * (1 - np.exp(-d / 45))
    # fur strands: noise smeared along a diagonal
    n = np.random.default_rng(12).normal(0, 1, (BH, BW)).astype(np.float32)
    k = np.zeros((15, 15), np.float32); cv2.line(k, (2, 12), (12, 2), 1, 1); k /= k.sum()
    fur = cv2.filter2D(cv2.GaussianBlur(n, (0, 0), 0.8), -1, k) * 0.9
    fur += fbm(BH, BW, 13, 3, 60) * 0.5
    # legs separation shading (cooler gaps), belly underside cooler
    shade = np.clip((np.arange(BH, dtype=np.float32)[:, None] - 430) / 160, 0, 1) * 0.12
    face = np.zeros((BH, BW), np.float32)
    cv2.ellipse(face, (902, 258), (22, 18), 0, 0, 360, 1.0, -1, cv2.LINE_AA)   # nose
    cv2.circle(face, (800, 225), 9, 1.0, -1, cv2.LINE_AA)    # eye
    cv2.line(face, (860, 300), (905, 292), 0.7, 5, cv2.LINE_AA)   # mouth
    face = cv2.GaussianBlur(face, (0, 0), 1.6)
    return mf, warm - shade, fur, face
BMASK, BWARM, BFUR, BFACE = build_bear()
NOSE = np.array([902.0, 258.0])

def bear_layer(t, s, cx, cy, heat=1.0, focus=(480, 380), bg=None):
    """Composite the bear into field `bg` (in place). s = local->field scale; (cx,cy) = field position of `focus`."""
    br = 1 + 0.012 * math.sin(t * 2.4)
    A = np.array([[s, 0, cx - s * focus[0]], [0, s * br, cy - s * br * focus[1]]], np.float32)
    amb = 0.24
    val = BWARM * heat + amb * (1 - heat) + BFUR * (0.05 * heat + 0.022)
    val = val * (1 - BFACE * 0.95 * heat) + BFACE * (0.62 * (1 - heat))          # face dark when 'filtered', glows when real IR
    v = cv2.warpAffine(val, A, (FW, FH), flags=cv2.INTER_LINEAR)
    m = cv2.warpAffine(BMASK, A, (FW, FH), flags=cv2.INTER_LINEAR)
    bg[:] = bg * (1 - m) + v * m
    return A

def to_field(A, p): return (A[0, 0] * p[0] + A[0, 2], A[1, 1] * p[1] + A[1, 2])

def breath(f, t, A, amt):
    if amt <= 0: return
    nx, ny = to_field(A, NOSE)
    for k in range(4):
        u = ((t * 0.7 + k / 4) % 1)
        x = nx + 10 + 70 * u * A[0, 0] / 0.45; y = ny - 6 - 20 * u
        r = (6 + 26 * u) * A[0, 0] / 0.45
        blob = np.exp(-(((FX - x) ** 2 + (FY - y) ** 2) / (r * r)))
        f += blob * amt * 0.32 * (1 - u) ** 1.2

# ---------- overlay helpers (crisp chrome & type at full res) ----------
_TM = {}
def tmask(s, size, kind="bs", wt=900, stroke=0):
    k = (s, size, kind, wt, stroke)
    if k not in _TM:
        f = F(kind, size, wt); l, tp, r, b = f.getbbox(s, anchor="ls", stroke_width=stroke)
        im = Image.new("L", (r - l + 4, b - tp + 4)); ImageDraw.Draw(im).text((2 - l, 2 - tp), s, font=f, fill=255, anchor="ls", stroke_width=stroke)
        _TM[k] = (im, l - 2, tp - 2)
    return _TM[k]
def tw(s, size, kind="bs", wt=900): return F(kind, size, wt).getlength(s)
def fit(s, size, maxw=W - 140, kind="bs", wt=900):
    while tw(s, size, kind, wt) > maxw and size > 36: size -= 4
    return size
def amask(m, a): return m if a >= 0.999 else m.point(lambda p: int(p * a))
_GR = {}
def grad_img(w, h, v0=1.0, v1=0.7):
    k = (w, h, v0, v1)
    if k not in _GR:
        col = LUT[(np.linspace(v0, v1, h) * 255).astype(int)].astype(np.uint8)
        _GR[k] = Image.fromarray(np.repeat(col[:, None, :], w, 1)).convert("RGBA")
    return _GR[k]
def hot(O, s, size, cx, cy, a=1.0, v0=1.0, v1=0.72, anchor="c"):
    """White-hot ironbow gradient text with dark outline; cy = baseline-ish centre."""
    if a <= 0.01: return
    m, ox, oy = tmask(s, size); sm, sx, sy = tmask(s, size, stroke=max(4, size // 16))
    wdt = tw(s, size); x = cx - wdt / 2 if anchor == "c" else (cx if anchor == "l" else cx - wdt)
    by = cy + size * 0.36
    O.paste(Image.new("RGBA", sm.size, INK + (255,)), (int(x + sx), int(by + sy)), amask(sm, a))
    O.paste(grad_img(m.size[0], m.size[1], v0, v1), (int(x + ox), int(by + oy)), amask(m, a))
def plate(O, s, size, cx, cy, a=1.0, pad=34):
    """Black word on a white-hot plate."""
    if a <= 0.01: return
    d = ImageDraw.Draw(O); wdt = tw(s, size); x0 = cx - wdt / 2 - pad; x1 = cx + wdt / 2 + pad
    y0, y1 = cy - size * 0.52, cy + size * 0.5
    sh = Image.new("RGBA", O.size, (0, 0, 0, 0))
    gi = grad_img(int(x1 - x0), int(y1 - y0), 1.0, 0.86)
    mk = Image.new("L", gi.size, 0); ImageDraw.Draw(mk).rounded_rectangle([0, 0, gi.size[0] - 1, gi.size[1] - 1], 18, fill=int(255 * a))
    d.rounded_rectangle([x0 - 7, y0 - 7, x1 + 7, y1 + 7], 24, fill=INK + (int(230 * a),))
    O.paste(gi, (int(x0), int(y0)), mk)
    m, ox, oy = tmask(s, size)
    O.paste(Image.new("RGBA", m.size, (6, 0, 10, 255)), (int(cx - wdt / 2 + ox), int(cy + size * 0.36 + oy)), amask(m, a))
def mono(O, s, size, x, y, col, a=1.0, anchor="l", wt=700):
    if a <= 0.01: return
    d = ImageDraw.Draw(O); f = F("mono", size, wt)
    xx = x if anchor == "l" else (x - f.getlength(s) / 2 if anchor == "c" else x - f.getlength(s))
    d.text((xx + 2, y + 2), s, font=f, fill=INK + (int(200 * a),), anchor="lm")
    d.text((xx, y), s, font=f, fill=tuple(col) + (int(255 * a),), anchor="lm")
def tag(O, s, x, y, a, col=WHITE, size=40, anchor="l"):
    if a <= 0.01: return
    d = ImageDraw.Draw(O); f = F("mono", size, 800); w = f.getlength(s)
    x0 = x if anchor == "l" else (x - w - 36 if anchor == "r" else x - w / 2 - 18)
    d.rounded_rectangle([x0, y - size * 0.75, x0 + w + 36, y + size * 0.75], 10, fill=INK + (int(215 * a),), outline=tuple(col) + (int(255 * a),), width=3)
    d.text((x0 + 18, y), s, font=f, fill=tuple(col) + (int(255 * a),), anchor="lm")
def leader(O, p, q, a, col=WHITE):
    if a <= 0.01: return
    d = ImageDraw.Draw(O); k = ease(a); e = (p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k)
    d.line([p, e], fill=INK + (int(200 * a),), width=7); d.line([p, e], fill=tuple(col) + (int(255 * a),), width=3)
    d.ellipse([p[0] - 9, p[1] - 9, p[0] + 9, p[1] + 9], outline=tuple(col) + (int(255 * a),), width=3)

def fade(lt, at, d=0.25): return ease((lt - at) / d)
def wstart(ln, i): return words[min(ln["_w0"] + i, ln["_w1"] - 1)][1] - ln["_s"]

# ---------- scenes: fn(ln, lt, dur, t, O) -> dict(field, cross, mode) ----------
def S_hook(ln, lt, dur, t, O, a=1.0):
    f = LAND.copy(); snow(f, t)
    A = bear_layer(t, 0.54 + 0.004 * lt, 270, 700, 1.0, focus=(500, 600), bg=f)
    hot(O, "A POLAR BEAR'S", fit("A POLAR BEAR'S", 130), W / 2, 230, a)
    hot(O, "SKIN IS", 130, W / 2, 365, a, 0.95, 0.7)
    plate(O, "BLACK", 210, W / 2, 545, a)
    return dict(field=f, cross=(820, 1010), mode="FUR FILTER: ON")

def S_loop(ln, lt, dur, t, O):
    f = LAND.copy(); z = eout(lt / 1.6)
    A = bear_layer(t, 0.5 + 0.55 * z, 270 + 10 * z, 700 - 60 * z, 1.0, focus=(500 - 120 * z, 600 - 230 * z), bg=f); snow(f, t)
    hot(O, "ITS FUR ISN'T", fit("ITS FUR ISN'T", 140), W / 2, 240, fade(lt, 0, 0.15))
    hot(O, "WHITE EITHER", fit("WHITE EITHER", 150), W / 2, 395, fade(lt, wstart(ln, 4) - 0.1, 0.2), 1.0, 0.78)
    blink = 1.0 if (t * 2.2) % 1 < 0.6 else 0.25
    tag(O, "WAIT FOR IT", W / 2, 540, fade(lt, wstart(ln, 6)) * blink, YEL, 46, "c")
    return dict(field=f, cross=(560 + 40 * z, 1050), mode="FUR FILTER: ON")

def section(lt, t, O, a0):
    """Cross-section: hairs over black skin over hot fat."""
    f = np.full((FH, FW), 0.2, np.float32) + 0.04 * fbm(FH, FW, 21, 3, 50)
    sk0, sk1, fat1 = 560, 600, 720
    f[sk1:fat1] = 0.84 + 0.05 * fbm(fat1 - sk1, FW, 22, 3, 30) - 0.12 * ((FY[sk1:fat1] - sk1) / (fat1 - sk1)) ** 3
    f[sk0:sk1] = 0.0 + 0.01 * fbm(sk1 - sk0, FW, 23, 2, 20)
    g = eout(a0 / 0.9)
    hl = np.zeros((FH, FW), np.float32); core = np.zeros((FH, FW), np.float32)
    for i in range(11):
        x0 = 30 + i * 48 + (i % 2) * 8; h = (230 + 40 * math.sin(i * 2.1)) * g
        sw = 18 * math.sin(t * 1.3 + i)
        pts = np.array([(x0 + sw * (k / 12) ** 2 + 22 * (k / 12) ** 1.5, sk0 - h * k / 12) for k in range(13)], np.float32)
        cv2.polylines(hl, [(pts * 4).astype(np.int32).reshape(-1, 1, 2)], False, 1.0, 13 * 4 // 4 * 1, cv2.LINE_AA, shift=2)
        cv2.polylines(core, [(pts[:-1] * 4).astype(np.int32).reshape(-1, 1, 2)], False, 1.0, 4, cv2.LINE_AA, shift=2)
    hl = cv2.GaussianBlur(hl, (0, 0), 0.8); core = cv2.GaussianBlur(core, (0, 0), 0.6)
    f = f * (1 - hl) + hl * 0.46; f = f * (1 - core * 0.8) + core * 0.14
    tg = fade(lt, 0.35, 0.3)
    leader(O, (520, 900), (760, 820), tg); tag(O, "FUR", 770, 820, tg, WHITE)
    leader(O, (300, 1160), (150, 1290), fade(lt, 0.6, 0.3), YEL); tag(O, "BLACK SKIN", 120, 1300, fade(lt, 0.6, 0.3), YEL)
    leader(O, (760, 1330), (860, 1440), fade(lt, 0.85, 0.3)); tag(O, "WARM BODY", 1010, 1440, fade(lt, 0.85, 0.3), WHITE, 40, "r")
    return f

def S_skin(ln, lt, dur, t, O):
    cut = wstart(ln, 4) - 0.12
    if lt < cut:
        f = LAND.copy(); z = eout(lt / 0.8)
        A = bear_layer(t, 1.05 + 0.3 * z, 290, 560, 1.0, focus=(840, 270), bg=f); snow(f, t)
        nx, ny = to_field(A, NOSE)
        hot(O, "SEE THAT", 120, W / 2, 230, fade(lt, 0, 0.15))
        plate(O, "BLACK NOSE?", fit("BLACK NOSE?", 150, W - 220), W / 2, 395, fade(lt, wstart(ln, 2) - 0.1, 0.15))
        tag(O, "BARE SKIN", nx * 2 - 40, ny * 2 + 140, fade(lt, wstart(ln, 3), 0.25), YEL, 42, "c")
        return dict(field=f, cross=(nx * 2, ny * 2), mode="FUR FILTER: ON")
    a0 = lt - cut
    f = section(lt - cut, t, O, a0)
    hot(O, "SAME DARK SKIN", fit("SAME DARK SKIN", 130), W / 2, 235, fade(a0, 0, 0.15))
    hot(O, "UNDER THE WHOLE COAT", fit("UNDER THE WHOLE COAT", 92), W / 2, 365, fade(lt, wstart(ln, 7) - 0.1, 0.2), 0.95, 0.75)
    return dict(field=f, cross=None, mode="CROSS-SECTION", flash=math.exp(-a0 * 9))

def S_hair(ln, lt, dur, t, O):
    f = np.full((FH, FW), 0.09, np.float32) + 0.05 * fbm(FH, FW, 31, 3, 70)
    for k in range(9):                               # soft out-of-focus hairs behind
        x = (k * 67 + t * 6) % (FW + 100) - 50
        cv2.line(f, (int(x), 0), (int(x + 140), FH), 0.17, 9, cv2.LINE_AA)
    f = cv2.GaussianBlur(f, (0, 0), 6)
    g = eout(lt / 0.7)
    p0 = np.array([-40, 700.0]); p1 = np.array([600, 330.0]); pe = p0 + (p1 - p0) * g
    tube = np.zeros((FH, FW), np.uint8); cv2.line(tube, tuple(p0.astype(int)), tuple(pe.astype(int)), 255, 78, cv2.LINE_AA)
    core = np.zeros((FH, FW), np.uint8); cv2.line(core, tuple(p0.astype(int)), tuple((pe - (p1 - p0) * 0.02).astype(int)), 255, 26, cv2.LINE_AA)
    d = cv2.distanceTransform((tube > 127).astype(np.uint8), cv2.DIST_L2, 5)
    dc = cv2.distanceTransform((core < 128).astype(np.uint8), cv2.DIST_L2, 5)
    tm = tube.astype(np.float32) / 255; cm = core.astype(np.float32) / 255
    u = ((FX - p0[0]) * (p1 - p0)[0] + (FY - p0[1]) * (p1 - p0)[1]) / ((p1 - p0) ** 2).sum()
    sheen = np.exp(-((u - ((t * 0.35) % 1.3 - 0.15)) / 0.06) ** 2)
    glass = 0.16 + 0.62 * np.exp(-d / 4) + 0.14 * np.exp(-d / 14) + 0.3 * sheen * np.exp(-d / 10)
    f = f * (1 - tm) + glass * tm
    corev = 0.03 + 0.45 * np.exp(-dc / 2.5) * (cm > 0.5)
    f = f * (1 - cm) + corev * cm + (1 - cm) * tm * 0.0
    # cross-section ring inset (end-on view of the hair)
    cxs, cys, R = 135, 300, 68
    rr = np.sqrt((FX - cxs) ** 2 + (FY - cys) ** 2); ag = fade(lt, wstart(ln, 8) - 0.3, 0.4)
    ring = (np.exp(-((rr - R) / 4) ** 2) * 0.75 + np.exp(-((rr - 26) / 3) ** 2) * 0.45) * ag
    f = np.where(rr < R, f * (1 - ag) + ag * np.where(rr < 26, 0.03, 0.2), f) + ring
    hot(O, "EACH HAIR:", 140, W / 2, 230, fade(lt, 0, 0.15))
    tag(O, "CLEAR", 620, 1010, fade(lt, wstart(ln, 3)), WHITE, 50); leader(O, (560, 960), (610, 1010), fade(lt, wstart(ln, 3)))
    tag(O, "NO PIGMENT", 560, 1150, fade(lt, wstart(ln, 5)), WHITE, 50); leader(O, (380, 1020), (550, 1150), fade(lt, wstart(ln, 5)))
    ah = fade(lt, wstart(ln, 8))
    tag(O, "HOLLOW", 420, 600, ah, YEL, 56); leader(O, (cxs * 2, cys * 2), (410, 600), ah, YEL)
    return dict(field=f, cross=(760, 760), mode="MACRO x400")

RAYS = []
_r = np.random.default_rng(77)
for i in range(26): RAYS.append((_r.uniform(0, 1), _r.uniform(-0.9, 0.9, 4), _r.uniform(0.6, 1.2)))
def S_scatter(ln, lt, dur, t, O):
    f = np.full((FH, FW), 0.08, np.float32) + 0.03 * fbm(FH, FW, 41, 3, 60)
    sun = (70, 150)
    rs = np.sqrt((FX - sun[0]) ** 2 + (FY - sun[1]) ** 2); f += np.exp(-(rs / 30) ** 2) * 0.95 + np.exp(-(rs / 90) ** 2) * 0.18
    hairs = [(150 + 75 * i, 470 + 25 * (i % 2)) for i in range(5)]
    hm = np.zeros((FH, FW), np.float32)
    for k, (x, ytop) in enumerate(hairs):
        sw = 10 * math.sin(t * 1.2 + k)
        cv2.line(hm, (x, ytop - 30), (int(x + sw + 30), 730), 1.0, 26, cv2.LINE_AA)
    d = cv2.distanceTransform((hm > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    f = f * (1 - hm) + hm * (0.15 + 0.5 * np.exp(-d / 3))
    # ice crystals on the right
    for (cx, cy, r) in ((400, 330, 34), (320, 250, 22)):
        pts = np.array([(cx + r * math.cos(a + t * 0.3), cy + r * math.sin(a + t * 0.3)) for a in np.arange(6) * math.pi / 3], np.float32)
        cv2.polylines(f, [(pts * 4).astype(np.int32)], True, 0.6, 3 * 4 // 4, cv2.LINE_AA, shift=2)
        for a in np.arange(3) * math.pi / 3:
            cv2.line(f, (int(cx - r * math.cos(a + t * .3)), int(cy - r * math.sin(a + t * .3))), (int(cx + r * math.cos(a + t * .3)), int(cy + r * math.sin(a + t * .3))), 0.45, 1, cv2.LINE_AA)
    # light rays: from the sun into the hairs, then scattered in all directions
    L = np.zeros((FH, FW), np.float32)
    for i, (ph, dirs, sp) in enumerate(RAYS):
        tgt = hairs[i % 5] if i < 20 else ((400, 330) if i % 2 else (320, 250))
        hit = (tgt[0] + (i * 7) % 20 - 4, tgt[1] + 20 + (i * 37) % 200 if i < 20 else tgt[1])
        u = ((lt * sp * 0.9 + ph) % 1.0) * 2
        if u < 1:
            a = np.array(sun) + (np.array(hit) - np.array(sun)) * max(0, u - 0.25); b = np.array(sun) + (np.array(hit) - np.array(sun)) * u
            cv2.line(L, tuple(a.astype(int)), tuple(b.astype(int)), 1.0, 3, cv2.LINE_AA)
        else:
            v = u - 1
            for dd in dirs:
                ang = dd * math.pi + (math.pi if dd < 0 else 0) * 0.5
                e = np.array(hit) + 150 * v * np.array([math.cos(ang * 3.3), math.sin(ang * 3.3)])
                s0 = np.array(hit) + 150 * max(0, v - 0.3) * np.array([math.cos(ang * 3.3), math.sin(ang * 3.3)])
                cv2.line(L, tuple(s0.astype(int)), tuple(e.astype(int)), 0.9 * (1 - v * 0.8), 3, cv2.LINE_AA)
    f = np.maximum(f, cv2.GaussianBlur(L, (0, 0), 0.7) * 1.0 + 0.08)
    a2 = fade(lt, wstart(ln, 11) - 0.15, 0.2)
    hot(O, "LIKE SNOW & ICE", fit("LIKE SNOW & ICE", 140), W / 2, 235, fade(lt, 0, 0.15) * (1 - a2))
    hot(O, "SCATTER LIGHT", fit("SCATTER LIGHT", 120), W / 2, 380, fade(lt, wstart(ln, 6) - 0.1, 0.2) * (1 - a2), 0.95, 0.75)
    hot(O, "LOOKS", 130, W / 2, 235, a2, 0.9, 0.7)
    hot(O, "WHITE", 230, W / 2, 420, a2, 1.0, 0.92)
    return dict(field=f, cross=None, mode="LIGHT PATHS")

def vanish_heat(ln, lt): return 1 - ease((lt - wstart(ln, 11)) / 1.4)
def S_vanish(ln, lt, dur, t, O):
    f = LAND.copy(); h = vanish_heat(ln, lt)
    A = bear_layer(t, 0.5, 270, 720, h, focus=(500, 600), bg=f); breath(f, t, A, 1 - h * 0.7); snow(f, t)
    a1 = 1 - fade(lt, wstart(ln, 7) - 0.15, 0.2)
    hot(O, "FUR HOLDS", 140, W / 2, 230, fade(lt, 0, 0.15) * a1)
    hot(O, "THE HEAT IN", 140, W / 2, 380, fade(lt, wstart(ln, 3) - 0.1, 0.2) * a1, 0.95, 0.75)
    a2 = fade(lt, wstart(ln, 7) - 0.1, 0.2); a3 = fade(lt, wstart(ln, 12) - 0.1, 0.2)
    hot(O, "ON A HEAT CAMERA…", fit("ON A HEAT CAMERA…", 110), W / 2, 230, a2 * (1 - a3), 0.95, 0.75)
    hot(O, "IT ALMOST", 130, W / 2, 230, a3, 0.95, 0.75)
    hot(O, "VANISHES", 190, W / 2, 400, a3, 1.0, 0.85)
    nx, ny = to_field(A, NOSE)
    mode = "FUR FILTER: ON" if h > 0.98 else "FUR FILTER: OFF"
    if h < 0.6: tag(O, "BREATH", nx * 2 + 60, ny * 2 - 110, (0.6 - h) / 0.6, YEL, 38, "r")
    return dict(field=f, cross=(560, 1010), mode=mode)

def paw(d, cx, cy, r, col):
    d.ellipse([cx - r * 0.55, cy - r * 0.1, cx + r * 0.55, cy + r * 0.62], fill=col)
    for k, (dx, dy) in enumerate(((-0.62, -0.42), (-0.22, -0.72), (0.22, -0.72), (0.62, -0.42))):
        d.ellipse([cx + dx * r - r * 0.2, cy + dy * r - r * 0.24, cx + dx * r + r * 0.2, cy + dy * r + r * 0.2], fill=col)
def S_end(ln, lt, dur, t, O):
    click = ln["scene"].get("click_at", 0.5); on = ease((lt - click) / 0.35)
    lp = (lt - (dur - 0.55)) / 0.5; a1 = 1 - ease(lp / 0.5); lh = ease((lp - 0.4) / 0.6)
    f = LAND.copy(); A = bear_layer(t, 0.5, 270, 720, on * 0.0 + lh, focus=(500, 600), bg=f); breath(f, t, A, 1 - lh); snow(f, t)
    f = f * (1 - 0.45 * a1 * (1 - lh))
    hot(O, "SOUNDS FAKE?", fit("SOUNDS FAKE?", 140), W / 2, 240, a1)
    x0, x1, y, hh = 170, W - 170, 560, 160
    d = ImageDraw.Draw(O)
    d.rounded_rectangle([x0 - 6, y - hh / 2 - 6, x1 + 6, y + hh / 2 + 6], hh / 2 + 6, fill=INK + (int(235 * a1),))
    if on > 0:
        fw = int((x1 - x0) * (0.12 + 0.88 * on))
        g = LUT[(np.linspace(0.3, 0.3 + 0.7 * on, fw) * 255).astype(int)].astype(np.uint8)
        gi = Image.fromarray(np.repeat(g[None], hh, 0)).convert("RGBA")
        mk = Image.new("L", (fw, hh), 0); ImageDraw.Draw(mk).rounded_rectangle([0, 0, fw - 1, hh - 1], hh / 2, fill=int(255 * a1))
        O.paste(gi, (x0, int(y - hh / 2)), mk)
    d.rounded_rectangle([x0, y - hh / 2, x1, y + hh / 2], hh / 2, outline=WHITE + (int(255 * a1),), width=5)
    mono(O, "FAKE", 70, x1 - 60, y, DIM, a1 * (1 - on), "r", 800)
    m, ox, oy = tmask("TRUE", 84)
    O.paste(Image.new("RGBA", m.size, (10, 0, 16, 255)), (int(x0 + 60 + ox), int(y + 84 * 0.36 + oy)), amask(m, a1 * on))
    kx = x0 + hh / 2 + (x1 - x0 - hh) * on
    d.ellipse([kx - 66, y - 66, kx + 66, y + 66], fill=iron(0.98) + (int(255 * a1),), outline=INK + (int(255 * a1),), width=5)
    paw(d, kx, y + 6, 40, (40, 0, 60, int(255 * a1)))
    hot(O, "IT'S TRUE.", fit("IT'S TRUE.", 210), W / 2, 820, a1 * fade(lt, click + 0.3, 0.2))
    hot(O, "FOLLOW FOR MORE", fit("FOLLOW FOR MORE", 96), W / 2, 990, a1 * fade(lt, click + 0.6, 0.2), 0.9, 0.7)
    if lh > 0:
        S_hook(ln, lt, dur, t, O, lh)
    return dict(field=f, cross=(820, 1010) if lh > 0.5 else None, mode="FUR FILTER: ON" if lh > 0.5 else "VERDICT")

SCENES = dict(hook=S_hook, loop=S_loop, skin=S_skin, hair=S_hair, scatter=S_scatter, vanish=S_vanish, end=S_end)

# ---------- audio ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
rng = np.random.default_rng(51)
def tri(f, dur, decay, bright=0.0):
    s = np.arange(int(dur * SR)) / SR
    ph = (f * s) % 1; w = 4 * np.abs(ph - 0.5) - 1
    w = w + bright * np.sin(2 * np.pi * f * 3 * s) * 0.4
    return (w * np.exp(-s * decay) * np.minimum(1, s / 0.004)).astype(np.float32)
DM = [(73.42, [293.66, 349.23, 440.0, 587.33]), (58.27, [233.08, 293.66, 349.23, 466.16]),
      (65.41, [261.63, 329.63, 392.0, 523.25]), (55.0, [277.18, 329.63, 440.0, 554.37])]   # Dm Bb C A
BAR = 2.4
for k in range(int(total / BAR) + 1):
    root, arp = DM[k % 4]; at = k * BAR
    s = np.arange(int(BAR * 1.1 * SR)) / SR
    drone = (np.sin(2 * np.pi * root * s) + 0.3 * np.sin(2 * np.pi * root * 2 * s)) * np.minimum(1, s / 0.3) * np.minimum(1, (BAR * 1.1 - s) / 0.3)
    place(music, at, drone.astype(np.float32), 0.09)
    warm = min(1, max(0, (at - total * 0.55) / (total * 0.4)))
    for j in range(8):
        place(music, at + j * BAR / 8, tri(arp[(j * 3 + k) % 4] * (2 if j % 4 == 3 else 1), 0.6, 6, warm), 0.035)
wind = rng.normal(0, 1, n).astype(np.float32)
wind = np.convolve(wind, np.ones(40) / 40, mode="same") * (0.6 + 0.4 * np.sin(np.arange(n) / SR * 0.7))
music += wind * 0.18
def clack(at, gain=0.25):
    m = int(0.06 * SR); s = np.arange(m) / SR
    place(music, at, (rng.normal(0, 1, m) * np.exp(-s * 120) + np.sin(2 * np.pi * 180 * s) * np.exp(-s * 60)).astype(np.float32), gain)
    place(music, at + 0.11, (rng.normal(0, 1, m) * np.exp(-s * 160)).astype(np.float32), gain * 0.6)
def beep(at, f=2093, gain=0.04, dur=0.09):
    s = np.arange(int(dur * SR)) / SR; place(music, at, (np.sin(2 * np.pi * f * s) * np.minimum(1, (dur - s) / 0.02)).astype(np.float32), gain)
hook_hit(music, 0.32); beep(0.02)
for i, ln in enumerate(spec["lines"]):
    s0 = ln["_s"]; st = ln["scene"]["type"]
    if i > 0: whoosh(music, s0 - 0.12, 0.07, 0.3); clack(s0 - 0.12, 0.2)
    if st == "skin": clack(s0 + wstart(ln, 4) - 0.12, 0.18)
    if st == "vanish":
        a = s0 + wstart(ln, 11); s = np.arange(int(1.6 * SR)) / SR
        place(music, a, (np.sin(2 * np.pi * (520 - 300 * s / 1.6) * s) * np.exp(-s * 1.4)).astype(np.float32), 0.05)
    if st == "end":
        c = s0 + ln["scene"].get("click_at", 0.5); clack(c, 0.3)
        for j, fq in enumerate((587.33, 739.99, 880.0, 1174.66)): place(music, c + 0.12 + j * 0.07, tri(fq, 1.2, 2.5, 0.6), 0.06)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.45)

# ---------- compositing ----------
groups = caption_groups(words, 3)
SCALE = Image.fromarray(np.repeat(LUT[np.linspace(255, 0, 700).astype(int)].astype(np.uint8)[:, None, :], 22, 1))

def hud(O, t, mode, cross, field):
    d = ImageDraw.Draw(O); c = WHITE + (220,)
    for (x, y, sx, sy) in ((40, 40, 1, 1), (W - 40, 40, -1, 1), (40, 1515, 1, -1), (W - 40, 1515, -1, -1)):
        d.line([(x, y + sy * 64), (x, y), (x + sx * 64, y)], fill=INK + (180,), width=9)
        d.line([(x, y + sy * 64), (x, y), (x + sx * 64, y)], fill=c, width=4)
    mono(O, "IR 51 · IRONBOW", 28, 78, 92, WHITE, 0.85)
    mono(O, mode, 28, 78, 132, YEL if "OFF" in mode else WHITE, 0.85)
    blink = 1.0 if (t * 1.4) % 1 < 0.6 else 0.2
    d.ellipse([W - 196, 80, W - 172, 104], fill=(255, 60, 40, int(255 * blink)))
    mono(O, "REC", 28, W - 162, 92, WHITE, 0.85)
    d.rectangle([W - 128, 122, W - 84, 142], outline=WHITE + (200,), width=3); d.rectangle([W - 84, 128, W - 79, 136], fill=WHITE + (200,))
    d.rectangle([W - 124, 126, W - 96, 138], fill=WHITE + (200,))
    # scale bar
    x0, y0 = W - 64, 560
    O.paste(SCALE, (x0, y0)); d.rectangle([x0 - 2, y0 - 2, x0 + 23, y0 + 701], outline=WHITE + (200,), width=2)
    for k, lab in enumerate(("+40°", "+5°", "-30°")):
        mono(O, lab, 24, x0 - 10, y0 + k * 350, WHITE, 0.8, "r")
    lo, hi = float(field.min()), float(field.max())
    mono(O, f"MIN {-30 + 70 * lo:5.1f}°  MAX {-30 + 70 * hi:5.1f}°", 26, W / 2, 1480, WHITE, 0.75, "c")
    if cross is not None:
        x, y = cross; v = float(field[int(min(FH - 1, max(0, y / 2))), int(min(FW - 1, max(0, x / 2)))])
        for col, wd in ((INK + (200,), 8), (WHITE + (255,), 3)):
            d.ellipse([x - 30, y - 30, x + 30, y + 30], outline=col, width=wd)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                d.line([(x + dx * 18, y + dy * 18), (x + dx * 48, y + dy * 48)], fill=col, width=wd)
        lab = f"SP1 {-30 + 70 * v:.1f}°C"
        if x > 640: mono(O, lab, 30, x - 58, y - 44, WHITE, 0.95, "r")
        else: mono(O, lab, 30, x + 58, y - 44, WHITE, 0.95)

def caption(O, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 88; f = F("bs", size, 800)
    while f.getlength(" ".join(ws)) > W - 240 and size > 44: size -= 4; f = F("bs", size, 800)
    tw_ = f.getlength(" ".join(ws)); x = (W - tw_) / 2; y = 1588
    d = ImageDraw.Draw(O)
    d.rounded_rectangle([x - 40, y - 18, x + tw_ + 40, y + size + 18], radius=18, fill=(14, 3, 30, 238), outline=ORG + (255,), width=4)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]; wl = f.getlength(w)
        if on: d.rounded_rectangle([x - 10, y - 4, x + wl + 10, y + size + 6], radius=10, fill=YEL + (255,))
        d.text((x, y - size * 0.1), w, font=f, fill=(12, 0, 20) if on else WHITE); x += f.getlength(w + " ")

def scene(t, ln):
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    O = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    P = SCENES[ln["scene"]["type"]](ln, lt, dur, t, O)
    return P, O

def to_rgb(field, fi, flash=0.0):
    f = cv2.GaussianBlur(field, (0, 0), 0.9)
    r = np.random.default_rng(fi)
    f = f + r.normal(0, 0.011, f.shape).astype(np.float32) + FPN
    if flash > 0: f = f * (1 - flash) + 0.32 * flash
    big = cv2.resize(f, (W, H), interpolation=cv2.INTER_CUBIC)
    rgb = LUT[np.clip(big * 255, 0, 255).astype(np.uint8)]
    hotp = np.clip((f - 0.8) / 0.2, 0, 1)[..., None] * LUT[230]
    glow = cv2.resize(cv2.GaussianBlur(hotp, (0, 0), 10), (W, H))
    rgb = rgb + glow * 0.5
    # vignette
    return rgb * VIG
_vy, _vx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.35 * np.clip(((_vx - W / 2) / (W * 0.62)) ** 2 + ((_vy - H / 2) / (H * 0.62)) ** 2, 0, 1) ** 1.5)[..., None]

def frame(t, fi):
    lines = spec["lines"]; ln = active_line(spec, t) or lines[0]; i = lines.index(ln)
    P, O = scene(t, ln); field = P["field"]; flash = P.get("flash", 0.0)
    if i > 0:
        ph = (t - (ln["_s"] - 0.12)) / 0.3
        if ph < 1:                                   # NUC shutter: freeze old -> flat field -> new
            if ph < 0.5:
                Pp, Op = scene(ln["_s"] - 0.12, lines[i - 1]); field = Pp["field"]; O = Op; P = Pp
                flash = max(flash, ease(ph / 0.5))
            else:
                flash = max(flash, 1 - ease((ph - 0.5) / 0.5))
    rgb = to_rgb(field, fi, flash)
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert("RGBA")
    hud(O if True else None, t, P.get("mode", ""), P.get("cross"), field)
    if flash > 0.3: mono(O, "NUC", 44, W / 2, 960, WHITE, min(1, (flash - 0.3) / 0.3), "c", 800)
    caption(O, t)
    d = ImageDraw.Draw(O)
    d.rectangle([0, H - 12, W, H], fill=(10, 2, 22, 255))
    pw = int(W * t / total)
    if pw > 1:
        g = LUT[(np.linspace(0.25, 1.0, pw) * 255).astype(int)].astype(np.uint8)
        O.paste(Image.fromarray(np.repeat(g[None], 12, 0)).convert("RGBA"), (0, H - 12))
    im.alpha_composite(O)
    return im.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), int(float(tt_) * FPS))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=24); print(f"done {total:.1f}s")
