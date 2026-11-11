"""Day 40 — TOPO-MAP style (Hawaii is moving toward Japan).
A vintage survey chart that is alive: a procedural sea floor rendered as stepped hypsometric tints with anti-aliased
contour lines (index contours heavier), soft hill-shading, cream paper grain, a segmented black/white neatline with
graticule ticks, spaced italic serif place names, mono coordinates and a cartographic scale bar. The Hawaiian chain
drifts north-west across the chart while dashed red track arrows march toward Japan. Ending: a compass rose whose
needle swings from FAKE to TRUE (north).
Music: slow marimba-like plucks over a low sea drone, sonar pings on scene changes.
Usage: python3 engine/styles/day40_topo.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
_FC = {}
def _font(file, s, wt=None):
    k = (file, int(s), wt)
    if k not in _FC:
        f = ImageFont.truetype(f"{FONTS}/{file}", max(8, int(s)))
        if wt:
            try: f.set_variation_by_axes([wt])
            except Exception: pass
        _FC[k] = f
    return _FC[k]
SANS = lambda s, w=700: _font("JosefinSans-VF.ttf", s, w)
ITAL = lambda s, w=600: _font("CormorantGaramond-Italic-VF.ttf", s, w)
MONO = lambda s: _font("DMMono-Medium.ttf", s)

PAPER = np.array((242, 234, 214), np.float32)
INK, RED, CREAM, SEA_INK, BROWN = (24, 38, 56), (206, 58, 42), (246, 240, 224), (40, 86, 112), (128, 84, 46)
HW, HH = W // 2, H // 2                                   # height field is evaluated at half resolution

# ---------- the world (units: km; x east, y south; Big Island at 0,0) ----------
# features: (x, y, sx, sy, angle_deg, amplitude_m, group)   group "h" = rides the drifting Hawaiian chain
FEAT = [
    (0, 0, 62, 70, 20, 9300, "h"), (-125, -125, 34, 26, 30, 8000, "h"), (-150, -150, 30, 18, 20, 4000, "h"),
    (-225, -175, 40, 12, 10, 6400, "h"), (-330, -215, 34, 26, 30, 6400, "h"), (-500, -290, 30, 28, 0, 6600, "h"),
    (-570, -305, 14, 10, 0, 5400, "h"),
    (-760, -430, 28, 22, 0, 3600, "h"), (-980, -560, 26, 20, 0, 3300, "h"), (-1220, -690, 30, 22, 0, 3400, "h"),
    (-1480, -830, 26, 22, 0, 3000, "h"), (-1760, -960, 30, 24, 0, 2900, "h"), (-2050, -1080, 26, 20, 0, 2600, "h"),
    (-300, -180, 420, 230, 30, 1100, "h"),                 # Hawaiian swell
    # Japan arc (static), plus its trench
    (-3300, -5350, 170, 130, 35, 6000, "j"), (-3650, -4900, 260, 90, 50, 6400, "j"), (-4000, -4500, 260, 85, 35, 6600, "j"),
    (-4450, -4200, 240, 80, 20, 6200, "j"), (-4850, -4050, 150, 80, 30, 5800, "j"),
    (-3000, -5000, 70, 520, 35, -3600, "j"), (-3550, -4300, 60, 420, 50, -3200, "j"),
    (-1900, -3300, 60, 50, 0, 3000, "j"), (-2600, -2400, 50, 40, 0, 2800, "j"), (-900, -2800, 55, 45, 0, 2600, "j"),
    (-2300, -4300, 40, 40, 0, 2500, "j"),
]
_rng = np.random.default_rng(40)
WAVES = [(_rng.uniform(0, 2 * math.pi), L, A, _rng.uniform(0, 2 * math.pi))
         for L, A in ((1900, 260), (1300, 220), (900, 180), (620, 140), (330, 90), (190, 60), (110, 40))]

def drift(t):
    """Exaggerated plate motion of the Hawaiian group (km): slowly north-west over the whole video."""
    k = 7.0 * t; return (-k * 0.8, -k * 0.6)

def field(cam, t, extra=(0.0, 0.0)):
    cx, cy, s = cam
    xs = cx + (np.arange(HW) * 2 + 1 - W / 2) / s; ys = cy + (np.arange(HH) * 2 + 1 - H / 2) / s
    X, Y = np.meshgrid(xs.astype(np.float32), ys.astype(np.float32))
    h = np.full((HH, HW), -4900.0, np.float32)
    for a, L, A, ph in WAVES:
        if L * s < 90: continue
        h += A * np.sin((X * math.cos(a) + Y * math.sin(a)) * 2 * math.pi / L + ph)
    dx, dy = drift(t); dx += extra[0]; dy += extra[1]
    for (fx, fy, sx, sy, ang, amp, g) in FEAT:
        if g == "h": fx, fy = fx + dx, fy + dy
        r = 3.2 * max(sx, sy)
        i0 = int(max(0, ((fx - r - cx) * s + W / 2) / 2)); i1 = int(min(HW, ((fx + r - cx) * s + W / 2) / 2 + 2))
        j0 = int(max(0, ((fy - r - cy) * s + H / 2) / 2)); j1 = int(min(HH, ((fy + r - cy) * s + H / 2) / 2 + 2))
        if i1 <= i0 or j1 <= j0: continue
        u = X[j0:j1, i0:i1] - fx; v = Y[j0:j1, i0:i1] - fy
        c, sn = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        a_ = (u * c + v * sn) / sx; b_ = (-u * sn + v * c) / sy
        h[j0:j1, i0:i1] += amp * np.exp(-0.5 * (a_ * a_ + b_ * b_))
    return np.array(Image.fromarray(h, "F").resize((W, H), Image.BILINEAR), np.float32)

# stepped hypsometric tints
TL = [-7000, -5500, -4000, -2500, -1000, -200, 0, 1, 600, 1500, 2600, 4000]
TC = np.array([(70, 116, 146), (96, 142, 168), (124, 166, 186), (152, 188, 200), (182, 210, 214), (206, 226, 222), (214, 230, 224),
               (206, 214, 170), (222, 214, 166), (214, 184, 136), (192, 152, 112), (238, 230, 214)], np.float32)
_grain = np.random.default_rng(7).normal(0, 1, (H, W)).astype(np.float32)
_lo = np.array(Image.fromarray(np.random.default_rng(8).normal(128, 40, (H // 40, W // 40)).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255
PAPER_TEX = (0.965 + 0.05 * _lo + 0.012 * _grain)[..., None]

def chart(cam, t, fade=0.0, extra=(0.0, 0.0)):
    """Render the living chart: tints + hill-shade + contours + coastline. fade -> wash toward paper."""
    h = field(cam, t, extra)
    step = 500.0 if cam[2] > 0.5 else 1000.0
    hq = np.where(h >= 0, (np.floor(h / step) + 0.5) * step, (np.floor(h / step) + 0.5) * step)
    hq = np.where((h >= 0) & (hq < 1), 1, hq)
    img = np.stack([np.interp(hq, TL, TC[:, i]) for i in range(3)], -1).astype(np.float32)
    gy, gx = np.gradient(h)
    land = (h > 0)[..., None]
    shade = np.clip(1 + (gx + gy) * (0.0028 * 0.5), 0.82, 1.12)[..., None]
    img = img * np.where(land, shade, 1 + (shade - 1) * 0.5)
    g = np.hypot(gx, gy) + 1e-3
    def line(spacing, width, offset=0.0):
        f = (h - offset) / spacing; dist = np.abs(f - np.round(f)) * spacing / g
        return np.clip(width / 2 + 0.5 - dist, 0, 1)
    c_minor = line(step, 1.4); c_major = line(step * 4, 2.6)
    coast = np.clip(2.2 + 0.5 - np.abs(h) / g, 0, 1)
    sea_col = np.array(SEA_INK, np.float32); land_col = np.array(BROWN, np.float32)
    col = np.where(land, land_col, sea_col)
    a = np.maximum(c_minor * 0.42, c_major * 0.75)[..., None]
    img = img * (1 - a) + col * a
    img = img * (1 - coast[..., None]) + np.array(INK, np.float32) * coast[..., None]
    if fade > 0: img = img * (1 - fade) + PAPER * fade
    img = img * PAPER_TEX
    return Image.fromarray(img.clip(0, 255).astype(np.uint8))

def w2s(cam, x, y):
    cx, cy, s = cam; return (W / 2 + (x - cx) * s, H / 2 + (y - cy) * s)

# ---------- chart furniture ----------
def neatline(d, cam):
    """Segmented black/white map border with graticule-style ticks and coordinates."""
    m, bw = 22, 14
    d.rectangle([m, m, W - m, H - m], outline=INK, width=2)
    d.rectangle([m + bw, m + bw, W - m - bw, H - m - bw], outline=INK, width=2)
    seg = 60
    for k in range(0, W, seg):
        if (k // seg) % 2 == 0:
            d.rectangle([max(m, k), m, min(W - m, k + seg), m + bw], fill=INK); d.rectangle([max(m, k), H - m - bw, min(W - m, k + seg), H - m], fill=INK)
    for k in range(0, H, seg):
        if (k // seg) % 2 == 1:
            d.rectangle([m, max(m, k), m + bw, min(H - m, k + seg)], fill=INK); d.rectangle([W - m - bw, max(m, k), W - m, min(H - m, k + seg)], fill=INK)

def spaced(d, xy, text, font, fill, anchor="mm", track=0.18, stroke=0, sfill=None):
    """Letter-spaced text (cartographic place names)."""
    sz = font.size; widths = [d.textlength(ch, font=font) for ch in text]
    tw = sum(widths) + track * sz * (len(text) - 1)
    x = xy[0] - (tw / 2 if anchor[0] == "m" else (tw if anchor[0] == "r" else 0))
    for ch, w in zip(text, widths):
        d.text((x, xy[1]), ch, font=font, fill=fill, anchor="l" + anchor[1], stroke_width=stroke, stroke_fill=sfill)
        x += w + track * sz

def plate(img, lines, y, size=118, hi=None, lt=9.0, anim=True, w_pad=60):
    """Cream cartouche label with double rule, title lines inside. hi = {line: True} lines in red."""
    hi = hi or {}; d = ImageDraw.Draw(img)
    sizes = []
    for ln in lines:
        s = size
        while d.textlength(ln, font=SANS(s)) > W - 200 and s > 40: s -= 4
        sizes.append(s)
    hgt = sum(s * 1.02 for s in sizes) + 70
    wd = max(d.textlength(ln, font=SANS(s)) for ln, s in zip(lines, sizes)) + 2 * w_pad
    u = 1.0 if not anim else eout(lt / 0.3)
    if u <= 0: return
    x0, x1 = W / 2 - wd / 2, W / 2 + wd / 2
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rectangle([x0 + 10, y + 10, x1 + 10, y + hgt + 10], fill=(24, 38, 56, 70))
    od.rectangle([x0, y, x1, y + hgt], fill=CREAM + (255,), outline=INK, width=4)
    od.rectangle([x0 + 10, y + 10, x1 - 10, y + hgt - 10], outline=INK, width=1)
    img.paste(ov, (0, 0), ov); d = ImageDraw.Draw(img)
    yy = y + 38
    for k, (ln, s) in enumerate(zip(lines, sizes)):
        uk = 1.0 if not anim else eout((lt - 0.1 * k) / 0.3)
        if uk > 0:
            n = len(ln) if uk >= 1 else max(1, int(len(ln) * uk))
            d.text((W / 2, yy + s * 0.08), ln[:n], font=SANS(s), fill=RED if hi.get(k) else INK, anchor="mt")
        yy += s * 1.02

def arrow(L, x0, y0, x1, y1, t, col=RED, w=7, head=34, march=True, prog=1.0):
    """Dashed track line with marching dashes and an arrowhead (drawn on supersampled layer L)."""
    ex, ey = x0 + (x1 - x0) * prog, y0 + (y1 - y0) * prog
    Ld = math.dist((x0, y0), (ex, ey))
    if Ld < 4: return
    ux, uy = (ex - x0) / Ld, (ey - y0) / Ld
    dash, off = 34, ((t * 70) % 68 if march else 0)
    s = -68 + off
    while s < Ld - head * 0.8:
        a, b = max(0, s), min(Ld - head * 0.8, s + dash)
        if b > a: L.line([(x0 + ux * a, y0 + uy * a), (x0 + ux * b, y0 + uy * b)], w, col)
        s += 68
    px, py = -uy, ux
    L.poly([(ex, ey), (ex - ux * head + px * head * 0.5, ey - uy * head + py * head * 0.5),
            (ex - ux * head - px * head * 0.5, ey - uy * head - py * head * 0.5)], col)

class Layer:
    SS = 2
    def __init__(self):
        self.im = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0)); self.d = ImageDraw.Draw(self.im)
    def line(self, pts, w, col): self.d.line([(x * 2, y * 2) for x, y in pts], fill=tuple(col) + (255,), width=int(w * 2), joint="curve")
    def poly(self, pts, col, outline=None, w=0):
        self.d.polygon([(x * 2, y * 2) for x, y in pts], fill=(tuple(col) + (255,)) if col else None, outline=(tuple(outline) + (255,)) if outline else None, width=int(w * 2))
    def circle(self, cx, cy, r, col=None, outline=None, w=0):
        self.d.ellipse([(cx - r) * 2, (cy - r) * 2, (cx + r) * 2, (cy + r) * 2], fill=(tuple(col) + (255,)) if col else None,
                       outline=(tuple(outline) + (255,)) if outline else None, width=int(w * 2))
    def onto(self, img):
        sm = self.im.resize((W, H), Image.BOX); img.paste(sm, (0, 0), sm)

def scalebar(d, L, x, y, units, unit_px, label, sub=None, col=INK, n=None):
    """Alternating black/white cartographic scale bar."""
    n = n or units
    for k in range(n):
        x0 = x + k * unit_px; fill = col if k % 2 == 0 else CREAM
        L.poly([(x0, y), (x0 + unit_px, y), (x0 + unit_px, y + 22), (x0, y + 22)], fill, outline=col, w=2)
    for k in range(0, n + 1, max(1, n // 5) if n > 5 else 1):
        d.text((x + k * unit_px, y + 34), str(k), font=MONO(30), fill=col, anchor="mt")
    if label: d.text((x + n * unit_px + 16, y + 11), label, font=MONO(30), fill=col, anchor="lm")

def cam_lerp(a, b, u):
    u = ease(u); s = math.exp(math.log(a[2]) + (math.log(b[2]) - math.log(a[2])) * u)
    return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, s)

CAM_HAWAII = (-170, -175, 1.15)
CAM_WIDE = (-2250, -2900, 0.165)
HOKKAIDO = (-3300, -5350)

def place_label(d, cam, x, y, text, size=46, fill=INK, track=0.22, stroke=3):
    sx, sy = w2s(cam, x, y)
    spaced(d, (sx, sy), text, ITAL(size), fill, track=track, stroke=stroke, sfill=CREAM)

def hawaii_labels(d, cam, t):
    dx, dy = drift(t)
    for (x, y, nm, off) in ((0, 0, "HAWAII", (-20, 150)), (-500, -290, "KAUAI", (-10, -70)), (-330, -215, "OAHU", (-30, 62))):
        sx, sy = w2s(cam, x + dx, y + dy)
        spaced(d, (sx + off[0], sy + off[1]), nm, ITAL(44 if nm != "HAWAII" else 56), INK, track=0.2, stroke=3, sfill=CREAM)

# ---------- scenes ----------
def S_hook(sc, lt, dur, t):
    cam = CAM_HAWAII
    img = chart(cam, t); d = ImageDraw.Draw(img); L = Layer()
    bx, by = w2s(cam, *drift(t))
    arrow(L, bx - 50, by - 70, bx - 420, by - 660, t, w=9, head=46)
    L.onto(img); d = ImageDraw.Draw(img)
    hawaii_labels(d, cam, t)
    sx, sy = bx - 420, by - 660
    spaced(d, (sx + 20, sy - 50), "TO JAPAN", SANS(50), RED, track=0.2, stroke=4, sfill=CREAM)
    spaced(d, (W / 2, 1480), "NORTH  PACIFIC  OCEAN", ITAL(50), SEA_INK, track=0.25)
    plate(img, ["HAWAII IS SLIDING", "TOWARD JAPAN"], 120, 112, {1: True}, lt, anim=False)
    if sc.get("loop"):
        u = back(lt / 0.35)
        if u > 0.05:
            box = Image.new("RGBA", (440, 190), (0, 0, 0, 0)); bd = ImageDraw.Draw(box)
            bd.rectangle([6, 6, 433, 183], outline=RED, width=6); bd.rectangle([18, 18, 421, 171], outline=RED, width=2)
            bd.text((220, 62), "ARRIVAL DATE", font=MONO(40), fill=RED, anchor="mm")
            bd.text((220, 124), "CALCULATED", font=SANS(58), fill=RED, anchor="mm")
            box = box.rotate(-8, expand=True, resample=Image.BICUBIC); s = min(1.2, max(0.05, u)) if lt < 0.35 else 1.0
            box = box.resize((max(1, int(box.width * s)), max(1, int(box.height * s))), Image.BICUBIC)
            img.paste(box, (int(310 - box.width / 2), int(1270 - box.height / 2)), box)
    neatline(ImageDraw.Draw(img), cam)
    return img

def S_plate(sc, lt, dur, t):
    cam = cam_lerp(CAM_HAWAII, CAM_WIDE, lt / 1.4)
    img = chart(cam, t); L = Layer()
    # plate boundary along the trench: line with subduction teeth
    bnd = [(-4700, -3650), (-4100, -3900), (-3600, -4250), (-3150, -4700), (-2800, -5200), (-2550, -5800)]
    p = ease((lt - 0.9) / 1.0)
    pts = [w2s(cam, x, y) for x, y in bnd]
    if p > 0:
        seglen = [math.dist(a, b) for a, b in zip(pts, pts[1:])]; tot = sum(seglen) * p; acc = 0
        for (a, b), sl in zip(zip(pts, pts[1:]), seglen):
            if acc >= tot: break
            f = min(1, (tot - acc) / sl); e = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            L.line([a, e], 6, RED)
            ux, uy = (b[0] - a[0]) / sl, (b[1] - a[1]) / sl
            for k in range(int(sl * f / 46)):
                cx_, cy_ = a[0] + ux * (k * 46 + 23), a[1] + uy * (k * 46 + 23)
                L.poly([(cx_ - ux * 11, cy_ - uy * 11), (cx_ + ux * 11, cy_ + uy * 11), (cx_ - uy * 18, cy_ + ux * 18)], RED)
            acc += sl
    # arrow field: the plate creeps north-west
    if lt > 1.1:
        for gx in range(-1, 4):
            for gy in range(-1, 5):
                x, y = -3200 + gx * 1100 + (gy % 2) * 550, -3600 + gy * 1000
                sx, sy = w2s(cam, x, y)
                if not (120 < sx < W - 120 and 520 < sy < 1480): continue
                ph = ((t * 0.9 + gx * 0.13 + gy * 0.21) % 1.0)
                L2 = 70; ox, oy = -0.8 * 30 * ph, -0.6 * 30 * ph
                a = min(1, ease((lt - 1.1 - 0.05 * (gx + gy)) / 0.4))
                if a > 0: arrow(L, sx + ox + 0.8 * L2 / 2, sy + oy + 0.6 * L2 / 2, sx + ox - 0.8 * L2 / 2, sy + oy - 0.6 * L2 / 2, 0, col=INK, w=5, head=22, march=False, prog=a)
    L.onto(img); d = ImageDraw.Draw(img)
    if lt > 1.2:
        x, y = w2s(cam, -1500, -2000)
        spaced(d, (x, y), "PACIFIC PLATE", ITAL(78, 700), INK, track=0.16, stroke=4, sfill=CREAM)
    if lt > 1.0:
        place_label(d, cam, -4300, -4700, "JAPAN", 50)
    hawaii_labels(d, cam, t) if lt < 0.25 else None
    plate(img, ["A GIANT SLAB OF", "EARTH'S OUTER SHELL"], 120, 96, {1: True}, lt)
    neatline(d, cam); return img

def S_speed(sc, lt, dur, t):
    cam = (-40, -60, 4.2 + 0.5 * lt)  # close-up on the Big Island's flank
    img = chart(cam, t, fade=0.35); d = ImageDraw.Draw(img); L = Layer()
    # legend panel
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rectangle([90, 560, W - 90, 1330], fill=CREAM + (240,), outline=INK, width=4); od.rectangle([102, 572, W - 102, 1318], outline=INK, width=1)
    img.paste(ov, (0, 0), ov); d = ImageDraw.Draw(img)
    spaced(d, (W / 2, 640), "LEGEND  ·  PLATE  SPEED", MONO(34), INK, track=0.1)
    d.line([(150, 690), (W - 150, 690)], fill=INK, width=2)
    u = eout((lt - 0.15) / 0.5)
    d.text((W / 2, 800), "7–10 cm", font=SANS(int(170 * (0.8 + 0.2 * u))), fill=RED, anchor="mm")
    d.text((W / 2, 930), "EVERY YEAR", font=SANS(72), fill=INK, anchor="mm")
    # compass-direction tag
    spaced(d, (W / 2, 1020), "HEADING  NORTH-WEST", ITAL(50), SEA_INK, track=0.12)
    # scale bar 0-10 cm with a marker sweeping 7..10
    x0, ub = 170, 74
    scalebar(d, L, x0, 1110, 10, ub, None)
    k = 7 + 3 * (0.5 - 0.5 * math.cos(t * 2.5))
    mx = x0 + k * ub
    L.poly([(x0 + 7 * ub, 1100), (x0 + 10 * ub, 1100), (x0 + 10 * ub, 1092), (x0 + 7 * ub, 1092)], RED)
    L.poly([(mx, 1104), (mx - 16, 1076), (mx + 16, 1076)], RED)
    L.onto(img); d = ImageDraw.Draw(img)
    d.text((x0 + 10 * ub + 18, 1121), "cm", font=MONO(30), fill=INK, anchor="lm")
    plate(img, ["IT CREEPS", "NORTH-WEST"], 120, 118, {1: True}, lt)
    neatline(d, cam); return img

def finger(L, x0, y, tipx, width):
    """A flat cartographic finger: cream body emerging from the legend edge, nail, knuckle creases,
    and a fingerprint drawn as topographic contour loops around the tip."""
    r = width / 2; body = [(x0, y - r)] + [(tipx - r + r * math.cos(a), y + r * math.sin(a)) for a in np.linspace(-math.pi / 2, math.pi / 2, 31)] + [(x0, y + r)]
    L.poly(body, (236, 214, 184), outline=INK, w=4)
    for k in range(1, 6):  # fingerprint contours (pad side)
        rr = r * (1 - k * 0.15); cxp = tipx - r * 1.3
        arc = [(cxp + rr * 1.15 * math.cos(a), y + r * 0.22 + rr * 0.6 * math.sin(a)) for a in np.linspace(-1.35, 1.35, 25)]
        L.line(arc, 2.2, BROWN)
    nr = r * 0.3; nx0, nx1, ny = tipx - r * 1.7, tipx - r * 0.55, y - r * 0.42
    nail = [(nx1 + nr * math.cos(a), ny + nr * math.sin(a)) for a in np.linspace(-math.pi / 2, math.pi / 2, 13)] + \
           [(nx0 + nr * math.cos(a), ny + nr * math.sin(a)) for a in np.linspace(math.pi / 2, 3 * math.pi / 2, 13)]
    L.poly(nail, (250, 238, 226), outline=INK, w=3)
    for kx in (tipx - r * 2.6, tipx - r * 4.6):
        if kx > x0 + 20:
            L.line([(kx, y - r * 0.55), (kx - 8, y), (kx, y + r * 0.55)], 3, BROWN); L.line([(kx + 16, y - r * 0.4), (kx + 10, y + r * 0.4)], 2, BROWN)

def S_finger(sc, lt, dur, t):
    cam = (-40, -60, 5.0 + 0.4 * lt)
    img = chart(cam, t, fade=0.55); L = Layer()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rectangle([90, 600, W - 90, 1330], fill=CREAM + (240,), outline=INK, width=4); od.rectangle([102, 612, W - 102, 1318], outline=INK, width=1)
    img.paste(ov, (0, 0), ov); d = ImageDraw.Draw(img)
    x0, ub = 170, 74
    p = eout((lt - 0.1) / 0.6)
    if p > 0: finger(L, 104, 870, 104 + (x0 + 7.5 * ub - 104) * (0.35 + 0.65 * p), 150)
    scalebar(d, L, x0, 1060, 10, ub, None)
    for xx in (x0 + 7 * ub, x0 + 10 * ub):
        L.line([(xx, 960), (xx, 1050)], 3, RED)
    L.onto(img); d = ImageDraw.Draw(img)
    d.text((x0 + 10 * ub + 18, 1071), "cm", font=MONO(30), fill=INK, anchor="lm")
    spaced(d, (W / 2, 690), "FIG. 2  —  ONE YEAR OF DRIFT", MONO(32), INK, track=0.06)
    spaced(d, (W / 2, 1210), "roughly one finger, every year", ITAL(58), SEA_INK, track=0.04)
    plate(img, ["ABOUT ONE FINGER", "A YEAR"], 120, 112, {1: True}, lt)
    neatline(d, cam); return img

def S_distance(sc, lt, dur, t):
    cam = cam_lerp((-2250, -2900, 0.19), CAM_WIDE, lt / dur)
    img = chart(cam, t); L = Layer()
    hx, hy = w2s(cam, *drift(t)); jx, jy = w2s(cam, *HOKKAIDO)
    p = ease((lt - 0.2) / 1.4)
    # dimension line offset perpendicular
    ux, uy = (jx - hx), (jy - hy); n = math.hypot(ux, uy); ux, uy = ux / n, uy / n; px, py = uy, -ux
    off = 70
    a = (hx + px * off, hy + py * off); b = (a[0] + (jx - hx) * p, a[1] + (jy - hy) * p)
    L.line([(hx, hy), (hx + px * (off + 24), hy + py * (off + 24))], 3, INK)
    if p > 0.98: L.line([(jx, jy), (jx + px * (off + 24), jy + py * (off + 24))], 3, INK)
    L.line([a, b], 5, RED)
    for (x, y, sgn) in ((a[0], a[1], 1), (b[0], b[1], -1)):
        L.poly([(x, y), (x + sgn * (ux * 30) + px * 12, y + sgn * (uy * 30) + py * 12), (x + sgn * (ux * 30) - px * 12, y + sgn * (uy * 30) - py * 12)], RED)
    L.circle(hx, hy, 14, outline=RED, w=5); L.circle(jx, jy, 14, outline=RED, w=5)
    L.onto(img); d = ImageDraw.Draw(img)
    km = int(round(6300 * p / 10) * 10)
    mx, my = (a[0] + b[0]) / 2 + px * 40, (a[1] + b[1]) / 2 + py * 40
    lab = Image.new("RGBA", (520, 130), (0, 0, 0, 0)); ld = ImageDraw.Draw(lab)
    ld.rectangle([4, 4, 515, 125], fill=CREAM + (255,), outline=INK, width=4)
    ld.text((260, 66), f"{km:,} km", font=SANS(84), fill=RED, anchor="mm")
    img.paste(lab, (int(mx - 260 + 60), int(my - 65)), lab); d = ImageDraw.Draw(img)
    place_label(d, cam, -4300, -4700, "JAPAN", 52)
    sx, sy = w2s(cam, *drift(t)); spaced(d, (sx - 30, sy + 60), "HAWAII", ITAL(52), INK, anchor="rm", track=0.2, stroke=3, sfill=CREAM)
    plate(img, ["JAPAN IS", "6,300 KM AWAY"], 120, 116, {1: True}, lt)
    neatline(d, cam); return img

def S_eta(sc, lt, dur, t):
    cam = CAM_WIDE
    u = ease((lt - 0.3) / (dur * 0.62))
    hx0, hy0 = drift(t)
    ex = (HOKKAIDO[0] - 0 - 260 * 0.8) * u * 0.93; ey = (HOKKAIDO[1] - 260 * 0.6) * u * 0.93  # chain slides along the track
    img = chart(cam, t, extra=(ex, ey)); L = Layer()
    sx0, sy0 = w2s(cam, hx0, hy0); jx, jy = w2s(cam, *HOKKAIDO)
    arrow(L, sx0, sy0, jx + 40, jy + 50, t, w=6, head=34)
    hx, hy = w2s(cam, hx0 + ex, hy0 + ey)
    L.circle(hx, hy, 22 + 4 * math.sin(t * 6), outline=RED, w=5)
    L.onto(img); d = ImageDraw.Draw(img)
    place_label(d, cam, -4300, -4700, "JAPAN", 52)
    yrs = 63_000_000 * u
    lab = Image.new("RGBA", (860, 300), (0, 0, 0, 0)); ld = ImageDraw.Draw(lab)
    ld.rectangle([4, 4, 855, 295], fill=CREAM + (255,), outline=INK, width=4); ld.rectangle([16, 16, 843, 283], outline=INK, width=1)
    ld.text((430, 70), "ESTIMATED ARRIVAL", font=MONO(36), fill=INK, anchor="mm")
    ld.text((430, 165), f"{int(yrs):,}", font=SANS(112), fill=RED, anchor="mm")
    ld.text((430, 248), "YEARS FROM NOW", font=SANS(48), fill=INK, anchor="mm")
    img.paste(lab, (int(W / 2 - 430), 1180), lab); d = ImageDraw.Draw(img)
    if lt > dur * 0.55:
        v = back((lt - dur * 0.55) / 0.35)
        box = Image.new("RGBA", (600, 150), (0, 0, 0, 0)); bd = ImageDraw.Draw(box)
        bd.rectangle([6, 6, 593, 143], fill=CREAM + (235,), outline=RED, width=6)
        bd.text((300, 50), "IF IT NEVER", font=SANS(50), fill=RED, anchor="mm"); bd.text((300, 104), "CHANGES COURSE", font=SANS(50), fill=RED, anchor="mm")
        box = box.rotate(6, expand=True, resample=Image.BICUBIC); s = max(0.05, min(1.15, v))
        box = box.resize((max(1, int(box.width * s)), max(1, int(box.height * s))), Image.BICUBIC)
        img.paste(box, (int(720 - box.width / 2), int(980 - box.height / 2)), box)
    plate(img, ["ARRIVING IN JAPAN…"], 120, 104, {}, lt)
    neatline(ImageDraw.Draw(img), cam); return img

def S_end(sc, lt, dur, t):
    cam = CAM_HAWAII
    img = chart(cam, t, fade=0.45); L = Layer()
    click = sc.get("click_at", 0.45); u = back((lt - click) / 0.35, 1.2)
    cx, cy, R = W / 2, 980, 255
    L.circle(cx, cy, R + 26, col=CREAM, outline=INK, w=5); L.circle(cx, cy, R, outline=INK, w=2); L.circle(cx, cy, R - 60, outline=INK, w=1.5)
    for k in range(72):
        a = k * math.pi / 36; r0 = R - (26 if k % 9 == 0 else 12)
        L.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + R * math.cos(a), cy + R * math.sin(a))], 2.5 if k % 9 == 0 else 1.5, INK)
    for k in range(8):  # rose points
        a = -math.pi / 2 + k * math.pi / 4; rr = R - 70 if k % 2 == 0 else R - 150
        tip = (cx + rr * math.cos(a), cy + rr * math.sin(a))
        l = (cx + 30 * math.cos(a - math.pi / 2), cy + 30 * math.sin(a - math.pi / 2)); r = (cx + 30 * math.cos(a + math.pi / 2), cy + 30 * math.sin(a + math.pi / 2))
        L.poly([l, tip, (cx, cy)], INK if k % 2 == 0 else (90, 110, 130)); L.poly([r, tip, (cx, cy)], CREAM, outline=INK, w=2)
    # needle: from FAKE (west) to TRUE (north)
    ang = -math.pi + (math.pi / 2) * u + 0.04 * math.sin(t * 9) * max(0, 1 - (lt - click) / 1.2) * (lt > click)
    tip = (cx + (R - 40) * math.cos(ang), cy + (R - 40) * math.sin(ang)); tail = (cx - (R - 110) * math.cos(ang), cy - (R - 110) * math.sin(ang))
    pl = (cx + 26 * math.cos(ang + math.pi / 2), cy + 26 * math.sin(ang + math.pi / 2)); pr = (cx + 26 * math.cos(ang - math.pi / 2), cy + 26 * math.sin(ang - math.pi / 2))
    L.poly([tip, pl, tail, pr], RED, outline=INK, w=2); L.poly([tail, pl, (cx, cy), pr], INK)
    L.circle(cx, cy, 18, col=CREAM, outline=INK, w=4)
    L.onto(img); d = ImageDraw.Draw(img)
    on = u > 0.5
    d.text((cx, cy - R - 70), "TRUE", font=SANS(88), fill=RED if on else (150, 150, 140), anchor="mb")
    d.text((cx - R - 50, cy), "FAKE", font=SANS(64), fill=(150, 150, 140) if on else INK, anchor="rm") if False else None
    spaced(d, (cx - R - 44, cy), "FAKE", SANS(62), (150, 150, 140) if on else INK, anchor="rm", track=0.05, stroke=4, sfill=CREAM)
    plate(img, ["SOUNDS FAKE?"], 120, 118, {}, 9, anim=False)
    if on:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        y0 = 1340; od.rectangle([200, y0, W - 200, y0 + 150], fill=CREAM + (255,), outline=RED, width=5)
        img.paste(ov, (0, 0), ov); d = ImageDraw.Draw(img)
        d.text((W / 2, y0 + 78), "IT'S TRUE.", font=SANS(104), fill=RED, anchor="mm")
    neatline(d, cam); return img

SCENES = dict(hook=S_hook, plate=S_plate, speed=S_speed, finger=S_finger, distance=S_distance, eta=S_eta, end=S_end)

# ---------- audio ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32); rng = np.random.default_rng(4)
tt = np.arange(n) / SR
music += (0.030 * np.sin(2 * np.pi * 55 * tt) + 0.018 * np.sin(2 * np.pi * 82.4 * tt + 1)) * (0.7 + 0.3 * np.sin(2 * np.pi * tt / 6))
scale = [220.0, 246.94, 277.18, 329.63, 369.99, 440.0, 493.88]   # A major pentatonic-ish
pattern = [0, 2, 4, 2, 5, 4, 2, 3]
for k in range(int(total / 0.375)):
    f = scale[pattern[k % 8] + (1 if (k // 8) % 4 == 3 and pattern[k % 8] < 6 else 0)]
    place(music, k * 0.375, tone(f, 0.6, decay=9, harm=(1, 4, 10), amp=1.0), 0.05 if k % 2 == 0 else 0.03)
    if k % 8 == 0: place(music, k * 0.375, tone(f / 4, 1.6, decay=2.2, harm=(1, 2)), 0.06)
def ping(at, g=0.07):
    place(music, at, tone(1320, 0.9, decay=5, harm=(1,)), g); place(music, at + 0.18, tone(1320, 0.7, decay=6, harm=(1,)), g * 0.35)
hook_hit(music, 0.35)
for s_ in scene_starts(spec): whoosh(music, s_, 0.08); ping(s_, 0.05)
for ln in spec["lines"]:
    if ln["scene"]["type"] == "end":
        tc = ln["_s"] + ln["scene"].get("click_at", 0.45) + 0.12
        place(music, tc, tone(880, 0.5, decay=8, harm=(1, 2, 3)), 0.12); place(music, tc + 0.09, tone(1318.5, 0.6, decay=7, harm=(1, 2)), 0.1)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.35)

# ---------- captions + frame ----------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 80
    while d.textlength(" ".join(ws), font=SANS(size)) > W - 240 and size > 40: size -= 4
    f = SANS(size); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1600
    d.rectangle([x - 34, y - 20, x + tw + 34, y + size + 14], fill=INK)
    d.rectangle([x - 26, y - 12, x + tw + 26, y + size + 6], outline=CREAM, width=2)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y + size * 0.1), w, font=f, fill=(255, 196, 88) if on else CREAM); x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    if ln is spec["lines"][0]: lt = t
    img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t); caption(img, t)
    d = ImageDraw.Draw(img); d.rectangle([0, H - 12, W, H], fill=INK); d.rectangle([0, H - 12, int(W * t / total), H], fill=RED)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
