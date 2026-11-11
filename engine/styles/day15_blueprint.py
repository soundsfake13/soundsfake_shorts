"""Day 15 — BLUEPRINT engineering-drawing style (the Eiffel Tower grows in summer).
Cyanotype drafting sheet: deep Prussian-blue paper with mottling, fine + major grid, white drafting lines that draw
themselves stroke by stroke (2x supersampled, soft glow), dimension arrows, mono annotations, condensed technical
titles, warm orange "heat" accents. Ending: a schematic knife switch flips from FAKE to TRUE with a spark.
Music: ticking drafting-pen pulse + minor arpeggio on a soft pad.
Usage: python3 engine/styles/day15_blueprint.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
_FC = {}
def F(name, s):
    k = (name, int(s))
    if k not in _FC: _FC[k] = ImageFont.truetype(f"{FONTS}/{name}", max(8, int(s)))
    return _FC[k]
HEAD = lambda s: F("BarlowCondensed-Bold.ttf", s)
SEMI = lambda s: F("BarlowCondensed-SemiBold.ttf", s)
MONO = lambda s: F("ShareTechMono-Regular.ttf", s)
GREEK = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", int(s))

PAPER, DEEP = np.array((22, 66, 128), np.float32), np.array((12, 40, 86), np.float32)
WHITE, CYAN, HEAT, NAVY = (240, 248, 255), (140, 205, 255), (255, 168, 64), (8, 26, 58)
SS = 2  # supersampling for line art

def _base():
    rng = np.random.default_rng(15)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # mottled cyanotype paper: low-frequency noise, upscaled
    lo = rng.normal(0, 1, (H // 60 + 2, W // 60 + 2)).astype(np.float32)
    lo = np.array(Image.fromarray(((lo - lo.min()) / np.ptp(lo) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.45) / (H * 0.7)) ** 2)
    v = np.clip(r, 0, 1) ** 1.6
    img = PAPER[None, None] * (1 - v[..., None]) + DEEP[None, None] * v[..., None]
    img = img * (0.94 + 0.10 * lo[..., None]) + rng.normal(0, 2.2, (H, W, 1))
    g = Image.new("L", (W, H), 0); d = ImageDraw.Draw(g)
    for x in range(0, W, 30): d.line([(x, 0), (x, H)], fill=26 if x % 150 else 60, width=1)
    for y in range(0, H, 30): d.line([(0, y), (W, y)], fill=26 if y % 150 else 60, width=1)
    gm = np.array(g, np.float32)[..., None] / 255
    img = img * (1 - gm * 0.55) + np.array((150, 200, 245), np.float32) * gm * 0.55
    return img.clip(0, 255).astype(np.uint8)
BASE = _base()

def sheet(img, t):
    """Drawing-sheet furniture: border, header strip and footer title block (outside the caption band)."""
    d = ImageDraw.Draw(img)
    d.rectangle([28, 28, W - 28, H - 28], outline=WHITE, width=3); d.rectangle([40, 40, W - 40, H - 40], outline=CYAN, width=1)
    d.text((70, 92), "DWG No. SF-015", font=MONO(32), fill=CYAN, anchor="lm")
    d.text((W - 70, 92), "SCALE: N.T.S.", font=MONO(32), fill=CYAN, anchor="rm")
    d.line([(60, 128), (W - 60, 128)], fill=CYAN, width=1)
    d.rectangle([60, 1780, W - 60, 1872], outline=WHITE, width=2); d.line([(560, 1780), (560, 1872)], fill=WHITE, width=2)
    d.text((80, 1826), "IRON TOWER · THERMAL STUDY", font=MONO(30), fill=WHITE, anchor="lm")
    d.text((W - 80, 1826), "SOUNDS FAKE ENG. DEPT.", font=MONO(30), fill=CYAN, anchor="rm")
    return d

class Pen:
    """Two supersampled line masks (white + heat) composited with a soft glow."""
    def __init__(self):
        self.m = {c: Image.new("L", (W * SS, H * SS), 0) for c in ("w", "h", "c")}
        self.d = {c: ImageDraw.Draw(self.m[c]) for c in self.m}
    def line(self, pts, w=3, col="w"):
        if len(pts) >= 2: self.d[col].line([(x * SS, y * SS) for x, y in pts], fill=255, width=int(w * SS), joint="curve")
    def poly(self, pts, col="w", fill=255):
        self.d[col].polygon([(x * SS, y * SS) for x, y in pts], fill=fill)
    def circle(self, cx, cy, r, w=3, col="w", fill=None):
        self.d[col].ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], outline=255, width=int(w * SS), fill=fill)
    def compose(self, base):
        out = base.astype(np.float32)
        for c, col, gl in (("c", CYAN, 0.25), ("w", WHITE, 0.35), ("h", HEAT, 0.7)):
            mi = self.m[c].resize((W, H), Image.BOX)
            m = np.array(mi, np.float32)[..., None] / 255
            if m.max() == 0: continue
            g = np.array(mi.filter(ImageFilter.GaussianBlur(7)), np.float32)[..., None] / 255
            colv = np.array(col, np.float32)
            out = out * (1 - m) + colv * m
            out = out + colv * g * gl
        return Image.fromarray(out.clip(0, 255).astype(np.uint8))

def partial(pts, p):
    """First fraction p (by length) of a polyline."""
    if p >= 1: return pts
    if p <= 0 or len(pts) < 2: return []
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]; L = sum(seg) * p; out = [pts[0]]
    for (a, b), s in zip(zip(pts, pts[1:]), seg):
        if L >= s: out.append(b); L -= s
        else:
            f = L / max(s, 1e-6); out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)); break
    return out

# ---------- the tower, in normalised coordinates (x in units of height, h from 0 to 1) ----------
def wo(h): return 0.195 * (1 - min(h, 1)) ** 2.2 + 0.014
def wi(h): return max(0.0, wo(h) - 0.062) * max(0.0, 1 - h / 0.39) ** 0.6
def _tower_parts():
    G = []  # (group, polyline in (x, h))
    hs = [i / 60 * 0.93 for i in range(61)]
    G.append(("edge", [(-wo(h), h) for h in hs])); G.append(("edge", [(wo(h), h) for h in hs]))
    hl = [i / 30 * 0.39 for i in range(31)]
    G.append(("inner", [(-wi(h), h) for h in hl])); G.append(("inner", [(wi(h), h) for h in hl]))
    a = wi(0.0); G.append(("inner", [(-a + 2 * a * j / 30, 0.125 * math.sqrt(max(0, 1 - ((-a + 2 * a * j / 30) / a) ** 2))) for j in range(31)]))
    for h0, th, ov in ((0.19, 0.022, 0.018), (0.39, 0.016, 0.012)):
        x0, x1 = wo(h0) + ov, wo(h0 + th) + ov
        G.append(("deck", [(-x0, h0), (x0, h0), (x1, h0 + th), (-x1, h0 + th), (-x0, h0)]))
    G.append(("deck", [(-0.026, 0.91), (0.026, 0.91), (0.022, 0.94), (-0.022, 0.94), (-0.026, 0.91)]))
    G.append(("deck", [(0, 0.94), (0, 1.0)]))
    # leg lattice: zigzag between outer and inner edges, below the 2nd deck
    for s in (-1, 1):
        zz, k, h = [], 0, 0.01
        while h < 0.385:
            zz.append((s * (wo(h) if k % 2 == 0 else max(wi(h), 0.004)), h)); h += 0.022; k += 1
        G.append(("lat", zz))
    # shaft: X bracing + ties from 2nd deck to the top cabin
    h = 0.41; step = 0.055
    while h < 0.9:
        h2 = min(0.905, h + step)
        G.append(("lat", [(-wo(h), h), (wo(h2), h2)])); G.append(("lat", [(wo(h), h), (-wo(h2), h2)]))
        G.append(("lat", [(-wo(h2), h2), (wo(h2), h2)]))
        h = h2; step *= 0.9
    return G
TOWER = _tower_parts()
WIN = {"edge": (0.0, 0.40), "inner": (0.25, 0.55), "deck": (0.45, 0.70), "lat": (0.55, 1.0)}

def tower(pen, bx, by, hpx, p=1.0, lean=0.0, stretch=0.0, col="w", sun_side=None, wpx=3.0):
    """Draw the lattice tower; p = drawing progress, lean = shear (x per unit h), stretch = extra px of height."""
    Ht = hpx + stretch
    tr = lambda x, h: (bx + (x + lean * h) * hpx, by - h * Ht)
    groups = {}
    for g, pl in TOWER: groups.setdefault(g, []).append(pl)
    for g, pls in groups.items():
        a, b = WIN[g]; n = len(pls)
        for i, pl in enumerate(pls):
            s = a + (b - a) * 0.6 * i / max(1, n); e = s + (b - a) * 0.4 + 0.0001
            q = (p - s) / (e - s)
            if q <= 0: continue
            pts = partial([tr(x, h) for x, h in pl], min(1.0, q))
            c = col
            if sun_side is not None and g == "edge" and ((sun_side > 0) == (pl[5][0] > 0)): c = "h"
            pen.line(pts, wpx + (1.5 if g == "edge" else 0) - (1.2 if g == "lat" else 0), c)
    if p > 0.02: pen.line([(bx - 0.3 * hpx, by), (bx + 0.3 * hpx, by)], 3, "c")  # ground line

def dimension(pen, d, x0, y0, x1, y1, label, col="c", tcol=CYAN, font=None, side=1):
    pen.line([(x0, y0), (x1, y1)], 2.5, col)
    ang = math.atan2(y1 - y0, x1 - x0)
    for (x, y, s) in ((x0, y0, 1), (x1, y1, -1)):
        for da in (0.4, -0.4):
            pen.line([(x, y), (x + s * 26 * math.cos(ang + da), y + s * 26 * math.sin(ang + da))], 2.5, col)
    if label:
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        f = font or MONO(40)
        if abs(x1 - x0) < 5: d.text((mx + side * 22, my), label, font=f, fill=tcol, anchor="lm" if side > 0 else "rm")
        else: d.text((mx, my - 34), label, font=f, fill=tcol, anchor="mm")

def title(d, lines, y=230, size=128, hi=None, lt=9.0, anim=True):
    hi = hi or {}
    for k, ln in enumerate(lines):
        s = size
        while d.textlength(ln, font=HEAD(s)) > W - 160: s -= 4
        u = 1.0 if not anim else eout((lt - 0.08 * k) / 0.35)
        if u <= 0: continue
        n = max(0, int(round(len(ln) * u)))  # "typed" by a plotter
        d.text((W / 2, y + k * (s * 0.98)), ln[:n] if u < 1 else ln, font=HEAD(s), fill=HEAT if hi.get(k) else WHITE, anchor="mt")

def sun(pen, cx, cy, r, t, col="h"):
    pen.circle(cx, cy, r, 4, col)
    for k in range(12):
        a = k * math.pi / 6 + t * 0.4; r0, r1 = r + 18, r + 18 + (34 if k % 2 == 0 else 20)
        pen.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + r1 * math.cos(a), cy + r1 * math.sin(a))], 4, col)

def dashed(pen, x0, y0, x1, y1, col="c", w=2, dash=18):
    L = math.dist((x0, y0), (x1, y1)); n = int(L / dash)
    for k in range(0, n, 2):
        a, b = k / n, min(1, (k + 1) / n)
        pen.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)], w, col)

# ---------- scenes ----------
def S_hook(sc, lt, dur, t):
    pen = Pen(); bx, by, hp = 540, 1470, 860
    st = 34 * (0.5 - 0.5 * math.cos(t * 2.4))  # breathing growth (exaggerated)
    tower(pen, bx, by, hp, 1.0, stretch=st)
    # ghost of the summer outline
    dashed(pen, bx - 70, by - hp - 40, bx + 70, by - hp - 40, "h", 3)
    dimension(pen, None, 860, by - hp, 860, by - hp - st - 2, None, "h") if st > 8 else None
    sun(pen, 900, 620, 44, t)
    img = pen.compose(BASE); d = sheet(img, t)
    title(d, ["IT GETS TALLER", "EVERY SUMMER"], 175, 132, {0: False, 1: True}, lt, anim=False)
    d.text((630, by - hp - 40), "+15 cm", font=MONO(44), fill=HEAT, anchor="lm")
    d.line([(150, by), (150, by - hp)], fill=CYAN, width=2)
    for y in (by, by - hp): d.line([(130, y), (170, y)], fill=CYAN, width=2)
    d.text((170, by - hp / 2), "330 m", font=MONO(40), fill=CYAN, anchor="lm")
    if sc.get("loop"):
        u = back(lt / 0.35)
        if u > 0.08:
            box = Image.new("RGBA", (330, 150), (0, 0, 0, 0)); bd = ImageDraw.Draw(box)
            bd.rectangle([4, 4, 325, 145], outline=HEAT, width=5)
            bd.text((165, 50), "NOTE 3:", font=MONO(40), fill=HEAT, anchor="mm"); bd.text((165, 102), "THE STRANGE PART", font=SEMI(42), fill=WHITE, anchor="mm")
            box = box.rotate(6, expand=True, resample=Image.BICUBIC); s = min(1.15, u)
            box = box.resize((int(box.width * s), int(box.height * s)), Image.BICUBIC)
            img.paste(box, (int(860 - box.width / 2), int(1180 - box.height / 2)), box)
    return img

def S_iron(sc, lt, dur, t):
    pen = Pen(); bx, by, hp = 330, 1470, 860
    tower(pen, bx, by, hp, ease(lt / 2.4))
    # I-beam cross-section detail
    cx, cy, s = 800, 760, 1.0
    beam = [(-90, -110), (90, -110), (90, -80), (18, -80), (18, 80), (90, 80), (90, 110), (-90, 110), (-90, 80), (-18, 80), (-18, -80), (-90, -80), (-90, -110)]
    pen.line(partial([(cx + x * s, cy + y * s) for x, y in beam], ease((lt - 0.3) / 1.0)), 4, "w")
    for k in range(-3, 4):  # hatch
        if lt > 1.1: pen.line([(cx - 14, cy + k * 22 - 8), (cx + 14, cy + k * 22 + 8)], 2, "c")
    pen.circle(cx, cy, 170, 2, "c") if lt > 0.2 else None
    dashed(pen, bx + 0.06 * hp, by - 0.5 * hp, cx - 170, cy + 40, "c", 2)
    img = pen.compose(BASE); d = sheet(img, t)
    title(d, ["7,300 TONNES", "OF IRON"], 175, 132, {0: True}, lt)
    n = int(7300 * eout((lt - 0.2) / 1.8)); d.text((800, 1010), f"{n:,} t", font=MONO(76), fill=HEAT, anchor="mm")
    d.text((800, 1090), "PUDDLED IRON", font=MONO(36), fill=CYAN, anchor="mm")
    d.text((800, 1140), "18,038 PARTS", font=MONO(36), fill=CYAN, anchor="mm")
    return img

def S_expand(sc, lt, dur, t):
    pen = Pen(); x0, Lc = 150, 640
    grow = 90 * ease((lt - 0.3) / 1.4)
    pen.line([(x0, 820), (x0 + Lc, 820)], 34, "c")
    hot = "h" if lt > 0.3 else "w"
    pen.line([(x0, 1110), (x0 + Lc + grow, 1110)], 34, hot)
    for k in range(5):  # heat waves under the hot bar
        xx = x0 + 60 + k * 130; ph = t * 6 + k
        if lt > 0.3: pen.line([(xx + 10 * math.sin(ph + j * 0.6), 1240 - j * 9) for j in range(10)], 4, "h")
    dashed(pen, x0 + Lc, 760, x0 + Lc, 1170, "c", 2)
    if grow > 20: dimension(pen, None, x0 + Lc, 1040, x0 + Lc + grow, 1040, None, "h")
    # thermometer
    tx, ty0, ty1 = 940, 1300, 700
    pen.line([(tx - 26, ty0), (tx - 26, ty1), ], 4, "w"); pen.line([(tx + 26, ty0), (tx + 26, ty1)], 4, "w")
    pen.line(partial([(tx - 26, ty1), (tx, ty1 - 26), (tx + 26, ty1)], 1), 4, "w")
    pen.circle(tx, ty0 + 40, 52, 4, "w")
    lvl = ty0 - 40 - 480 * (0.15 + 0.8 * ease((lt - 0.2) / 1.5))
    pen.line([(tx, ty0 + 20), (tx, lvl)], 22, "h"); pen.circle(tx, ty0 + 40, 34, 4, "h", fill=255)
    img = pen.compose(BASE); d = sheet(img, t)
    title(d, ["HEAT IT UP.", "IRON GROWS."], 175, 132, {1: True}, lt)
    d.text((x0, 760), "COLD", font=MONO(40), fill=CYAN, anchor="ls"); d.text((x0, 1050), "HOT", font=MONO(40), fill=HEAT, anchor="ls")
    if grow > 20: d.text((x0 + Lc + grow / 2, 985), "ΔL", font=GREEK(44), fill=HEAT, anchor="mm")
    d.text((x0, 1380), "ΔL = α · L · ΔT", font=GREEK(52), fill=WHITE, anchor="lm")
    d.text((x0, 1440), "α(iron) ≈ 0.000012 / °C", font=GREEK(36), fill=CYAN, anchor="lm")
    return img

def S_grow(sc, lt, dur, t):
    pen = Pen(); by, hp = 1430, 640
    tower(pen, 290, by, hp, 1.0, col="c")
    st = 90 * ease((lt - 0.4) / 1.6)
    tower(pen, 790, by, hp, 1.0, stretch=st)
    dashed(pen, 160, by - hp, 940, by - hp, "c", 2)
    if st > 10: dimension(pen, None, 980, by - hp, 980, by - hp - st, None, "h")
    dashed(pen, 700, by - hp - st, 990, by - hp - st, "h", 2)
    sun(pen, 930, 560, 30, t)
    # snowflake
    for k in range(3):
        a = k * math.pi / 3; pen.line([(150 + 34 * math.cos(a), 560 + 34 * math.sin(a)), (150 - 34 * math.cos(a), 560 - 34 * math.sin(a))], 4, "c")
    img = pen.compose(BASE); d = sheet(img, t)
    title(d, ["WINTER VS SUMMER"], 175, 120, {}, lt)
    cm = 15 * ease((lt - 0.4) / 1.6)
    d.text((W / 2, 400), f"UP TO +{cm:.0f} cm", font=HEAD(110), fill=HEAT, anchor="mt")
    d.text((290, 1480), "WINTER", font=MONO(40), fill=CYAN, anchor="mt"); d.text((790, 1480), "SUMMER", font=MONO(40), fill=HEAT, anchor="mt")
    d.text((W / 2, 525), "DRAWING EXAGGERATED", font=MONO(28), fill=CYAN, anchor="mt")
    return img

def S_tilt(sc, lt, dur, t):
    pen = Pen(); bx, by, hp = 470, 1470, 820
    lean = -0.075 * ease((lt - 0.8) / 1.8)
    tower(pen, bx, by, hp, 1.0, lean=lean, sun_side=1 if lt > 0.4 else None)
    sun(pen, 900, 640, 60, t)
    for k in range(4):  # sun rays hitting the right side
        if lt > 0.3:
            yk = 820 + k * 150; pen.line(partial([(820, 690 + k * 40), (bx + wo((by - yk) / hp) * hp + 30, yk)], ease((lt - 0.3 - 0.1 * k) / 0.5)), 3, "h")
    dashed(pen, bx, by, bx, by - hp - 40, "c", 2)  # plumb line
    if lean < -0.01:
        r = 300; a0 = -math.pi / 2; a1 = a0 + math.atan(lean)
        pen.line([(bx + r * math.cos(a0 + (a1 - a0) * j / 12), by + r * math.sin(a0 + (a1 - a0) * j / 12)) for j in range(13)], 3, "h")
    img = pen.compose(BASE); d = sheet(img, t)
    title(d, ["IT LEANS AWAY", "FROM THE SUN"], 175, 132, {1: True}, lt)
    d.text((W - 80, 1520), "LEAN EXAGGERATED · N.T.S.", font=MONO(28), fill=CYAN, anchor="rb")
    if lt > 0.5: d.text((820, 1090), "HOT SIDE", font=MONO(36), fill=HEAT, anchor="lm") if False else None
    return img

def S_end(sc, lt, dur, t):
    pen = Pen(); click = sc.get("click_at", 0.45); u = ease((lt - click) / 0.18)
    px, py = 300, 980; L = 440
    a = math.radians(-38 + 38 * u)  # blade from FAKE (up) to TRUE (level)
    tip = (px + L * math.cos(a), py + L * math.sin(a))
    pen.line([(120, py), (px, py)], 5, "w"); pen.circle(px, py, 16, 5, "w")
    pen.line([(px, py), tip], 12, "h" if u > 0.5 else "w")
    fx, fy = px + L * math.cos(math.radians(-38)), py + L * math.sin(math.radians(-38))
    pen.circle(fx, fy, 16, 5, "c"); pen.line([(fx + 16, fy), (W - 120, fy)], 5, "c")
    tx_, ty_ = px + L, py
    pen.circle(tx_, ty_, 16, 5, "h" if u > 0.5 else "w"); pen.line([(tx_ + 16, ty_), (W - 120, ty_)], 5, "h" if u > 0.5 else "w")
    if 0.5 < u and lt - click < 0.6:  # spark
        for k in range(8):
            ang = k * math.pi / 4 + 0.3; r0 = 26; r1 = 26 + 50 * (1 - (lt - click) / 0.6)
            pen.line([(tx_ + r0 * math.cos(ang), ty_ + r0 * math.sin(ang)), (tx_ + r1 * math.cos(ang), ty_ + r1 * math.sin(ang))], 4, "h")
    tower(pen, 540, 1470, 280, 1.0, col="c", wpx=2.2)
    img = pen.compose(BASE); d = sheet(img, t)
    title(d, ["SOUNDS FAKE?"], 175, 132, {}, 9, anim=False)
    if u > 0.5: title(d, ["IT'S TRUE."], 320, 132, {0: True}, lt - click, anim=True)
    d.text((W - 130, fy - 40), "FAKE", font=HEAD(80), fill=CYAN if u < 0.5 else (90, 130, 185), anchor="rb")
    d.text((W - 130, ty_ - 40), "TRUE", font=HEAD(80), fill=HEAT if u >= 0.5 else (90, 130, 185), anchor="rb")
    return img

SCENES = dict(hook=S_hook, iron=S_iron, expand=S_expand, grow=S_grow, tilt=S_tilt, end=S_end)

# ---------- audio ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
roots = [110.0, 87.31, 130.81, 98.0]  # A minor, F, C, G
for bar in range(int(total / 2.0) + 1):
    r = roots[bar % 4]
    for f in (r / 2, r, r * 1.5): place(music, bar * 2.0, tone(f, 2.4, decay=0.9, harm=(1, 2)), 0.025)
    for k in range(8):  # arpeggio
        f = r * (1, 1.5, 2, 2.5, 3, 2.5, 2, 1.5)[k]; place(music, bar * 2.0 + k * 0.25, tone(f * 2, 0.3, decay=12, harm=(1, 2, 3)), 0.02)
rng = np.random.default_rng(1)
for k in range(int(total / 0.25)):  # drafting-pen tick
    tk = np.arange(int(0.03 * SR)) / SR; place(music, k * 0.25, rng.normal(0, 1, len(tk)) * np.exp(-tk * 260), 0.05 if k % 2 == 0 else 0.025)
hook_hit(music, 0.35)
for s_ in scene_starts(spec): whoosh(music, s_, 0.09)
for ln in spec["lines"]:
    if ln["scene"]["type"] == "end":
        tc = ln["_s"] + ln["scene"].get("click_at", 0.45) + 0.1
        place(music, tc, tone(880, 0.4, decay=10, harm=(1, 2, 3)), 0.12); place(music, tc, rng.normal(0, 1, int(0.05 * SR)) * np.exp(-np.arange(int(0.05 * SR)) / SR * 90), 0.2)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.35)

# ---------- captions + frame ----------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 84
    while d.textlength(" ".join(ws), font=HEAD(size)) > W - 220 and size > 40: size -= 4
    f = HEAD(size); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1600
    d.rectangle([x - 30, y - 16, x + tw + 30, y + size + 22], fill=NAVY, outline=WHITE, width=3)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=HEAT if on else WHITE); x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    if ln is spec["lines"][0]: lt = t
    img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t); caption(img, t)
    ImageDraw.Draw(img).rectangle([0, H - 12, int(W * t / total), H], fill=HEAT); return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
