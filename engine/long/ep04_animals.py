"""LONG-FORM (16:9, 1920x1080) — 'Sounds Fake: Deep Dive' ep04: ANIMAL SUPERPOWERS.
Comic-book 'superpower' look: violet radial burst, halftone dots, drifting sparks, simple flat animal drawings,
glowing type, chapter cards, lower-third captions. Based on engine/long/ep03_ocean.py.
Usage: python3 engine/long/ep04_animals.py spec.json out.mp4 [t1,t2,... preview]
"""
import json, math, os, random, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import core
from core import narrate, write_audio, caption_groups, group_at, ease, eout, back, tone, place, hook_hit, whoosh, SR

W, H, FPS = 1920, 1080, 30
spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
rng = np.random.default_rng(7); random.seed(7)
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
_fc = {}
def F(s, w="Black"):
    k = (int(s), w)
    if k not in _fc: _fc[k] = ImageFont.truetype(f"{FD}InterDisplay-{w}.otf", int(s))
    return _fc[k]

GOLD, TEAL, WHITE, DIM, CORAL, BLUE = (255, 204, 64), (80, 220, 230), (246, 242, 252), (160, 148, 196), (255, 96, 110), (100, 150, 255)
LIME, INK, CARD = (150, 235, 110), (16, 10, 30), (30, 20, 56)

# ---------------- background: "superpower" comic look — violet radial burst + halftone dots + drifting sparks ----------------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.45) / W) ** 2)
_a = np.arctan2(yy - H * 0.45, xx - W / 2)
BG = np.array([46, 24, 82], np.float32) * np.clip(1 - _r * 1.25, 0, 1)[..., None] ** 1.1 + np.array([12, 8, 28], np.float32)
BG += ((np.sin(_a * 14) > 0.55).astype(np.float32) * np.clip(1 - _r * 1.4, 0, 1) * 9)[..., None] * np.array([1.0, 0.7, 1.3], np.float32)
_g = 28; _cx = (xx % _g) - _g / 2; _cy = (yy % _g) - _g / 2
_dot = (np.sqrt(_cx ** 2 + _cy ** 2) < (1.5 + 7.0 * np.clip(_r * 1.6 - 0.35, 0, 1))).astype(np.float32)
BG += (_dot * 10)[..., None] * np.array([1.0, 0.8, 1.4], np.float32)
BG_IMG = Image.fromarray(np.clip(BG, 0, 255).astype(np.uint8))
NIGHT = np.array([3, 5, 16], np.float32) + np.clip(1 - yy / H, 0, 1)[..., None] ** 1.5 * np.array([10, 16, 44], np.float32)
NIGHT_IMG = Image.fromarray(np.clip(NIGHT, 0, 255).astype(np.uint8))
SPARKS = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(8, 26), rng.uniform(1.2, 3.0), rng.uniform(0, 6.3), int(rng.integers(0, 3))) for _ in range(46)]
STARS = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.8, 2.6), rng.uniform(0, 6.3)) for _ in range(260)]

def lab(t, night=False, sparks=True):
    img = (NIGHT_IMG if night else BG_IMG).copy(); d = ImageDraw.Draw(img)
    if night:
        for x, y, r, ph in STARS:
            f = 0.55 + 0.45 * math.sin(t * 1.3 + ph * 5); c = int(120 + 120 * f * min(1, r / 2))
            d.ellipse([x - r * 0.6, y - r * 0.6, x + r * 0.6, y + r * 0.6], fill=(c, c, min(255, c + 20)))
    elif sparks:
        for x, y, vy, r, ph, k in SPARKS:
            py = (y - vy * t) % (H + 40) - 20; px = x + 14 * math.sin(t * 0.4 + ph); f = 0.5 + 0.5 * math.sin(t * 2 + ph)
            col = ((120, 100, 60), (60, 110, 120), (120, 60, 90))[k]; col = tuple(int(c * (0.6 + 0.6 * f)) for c in col)
            d.ellipse([px - r, py - r, px + r, py + r], fill=col)
    return img

def bloom(img, k=0.5):
    a = np.asarray(img).astype(np.float32)
    s = Image.fromarray(np.clip((a - 150) * 1.5, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    b = np.asarray(s.filter(ImageFilter.GaussianBlur(8)).resize((W, H), Image.BILINEAR)).astype(np.float32)
    return Image.fromarray(np.clip(a + b * k, 0, 255).astype(np.uint8))

def halo(img, cx, cy, r, col, strength=160):
    g = Image.new("L", (W, H), 0); ImageDraw.Draw(g).ellipse([cx - r, cy - r, cx + r, cy + r], fill=int(max(0, min(255, strength))))
    img.paste(Image.new("RGB", (W, H), col), (0, 0), g.filter(ImageFilter.GaussianBlur(r * 0.5)))

def glow(img, draw_fn, col=TEAL, blur=10, gain=1.0):
    m = Image.new("L", (W // 4, H // 4), 0); draw_fn(ImageDraw.Draw(m), 0.25)
    m = m.filter(ImageFilter.GaussianBlur(max(1, blur / 4))).resize((W, H), Image.BILINEAR)
    if gain != 1.0: m = m.point(lambda v: int(min(255, v * gain)))
    img.paste(Image.new("RGB", (W, H), col), (0, 0), m)

def tint(img, box, col, alpha, radius=30):
    m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rounded_rectangle(box, radius, fill=int(alpha))
    img.paste(Image.new("RGB", (W, H), col), (0, 0), m)

# ---------------- type ----------------
def text(img, s, size, x, y, col=WHITE, w="Black", anchor="mm", u=1.0, maxw=W - 200, shadow=True):
    if u <= 0: return
    d = ImageDraw.Draw(img)
    while d.textlength(s, font=F(size, w)) > maxw and size > 24: size -= 4
    f = F(size, w); y = y + (1 - u) * 26
    col = tuple(int(c * u + 5 * (1 - u)) for c in col)
    if shadow: d.text((x + 3, y + 4), s, font=f, fill=(0, 0, 0), anchor=anchor)
    d.text((x, y), s, font=f, fill=col, anchor=anchor)

def pill(img, s, size, x, y, fill=GOLD, ink=INK, u=1.0):
    if u <= 0: return
    d = ImageDraw.Draw(img); f = F(size, "Bold"); tw = d.textlength(s, font=f); y = y + (1 - u) * 16
    d.rounded_rectangle([x - tw / 2 - 26, y - size * 0.72, x + tw / 2 + 26, y + size * 0.72], int(size * 0.72), fill=fill)
    d.text((x, y), s, font=f, fill=ink, anchor="mm")

def fmtnum(v, kind):
    if kind == "int": return f"{int(round(v)):,}"
    if kind == "f1": return f"{v:,.1f}"
    return str(v)

# ---------------- generic beats ----------------
def b_cold(sc, lt, dur, t):
    img = lab(t); halo(img, W / 2, H / 2, 300, (120, 60, 160), 80)
    for i, s in enumerate(sc["lines"]):
        text(img, s, sc.get("size", 120), W / 2, 380 + i * sc.get("size", 120) * 1.15, GOLD if str(i) in sc.get("accent", {}) else WHITE, u=1.0 if i == 0 else ease((lt - i * 0.5) / 0.4))
    if "sub" in sc: pill(img, sc["sub"], 40, W / 2, 760, fill=TEAL, u=ease((lt - 0.8) / 0.4))
    return img

def b_chapter(sc, lt, dur, t):
    img = lab(t); halo(img, W / 2, 430, 280, (150, 70, 170), 100)
    d = ImageDraw.Draw(img); u = back(lt / 0.45); r = 230 * min(1.0, max(0.0, u))
    if r > 4: d.ellipse([W / 2 - r, 420 - r, W / 2 + r, 420 + r], outline=GOLD, width=8)
    text(img, f"{sc['ch']:02d}", 300, W / 2, 420, GOLD, u=min(1, u))
    text(img, sc["title"], 84, W / 2, 720, WHITE, u=ease((lt - 0.3) / 0.4))
    if "sub" in sc: text(img, sc["sub"], 42, W / 2, 805, TEAL, w="SemiBold", u=ease((lt - 0.6) / 0.4))
    return img

def b_text(sc, lt, dur, t):
    img = lab(t)
    for i, s in enumerate(sc["lines"]):
        text(img, s, sc.get("size", 96), sc.get("x", W / 2), sc.get("y", 420) + i * sc.get("size", 96) * 1.2, GOLD if str(i) in sc.get("accent", {}) else WHITE,
             anchor=sc.get("anchor", "mm"), u=ease((lt - i * 0.35) / 0.4), maxw=sc.get("maxw", W - 200))
    return img

def b_counter(sc, lt, dur, t):
    img = lab(t); halo(img, W / 2, 450, 300, (130, 60, 150), 80)
    v = sc["from"] + (sc["to"] - sc["from"]) * eout((lt - 0.2) / max(0.6, sc.get("secs", 2.0)))
    text(img, sc.get("prefix", "") + fmtnum(v, sc.get("fmt", "int")) + sc.get("suffix", ""), sc.get("size", 210), W / 2, 450, GOLD, u=ease(lt / 0.3))
    text(img, sc["label"], 56, W / 2, 640, WHITE, w="Bold", u=ease((lt - 0.3) / 0.4))
    return img

# ---------------- helpers ----------------
def rot(pts, cx, cy, s, ang=0.0, flip=False):
    ca, sa = math.cos(ang), math.sin(ang); out = []
    for x, y in pts:
        if flip: x = -x
        out.append((cx + (x * ca - y * sa) * s, cy + (x * sa + y * ca) * s))
    return out

def arrow(d, x0, y0, x1, y1, col=WHITE, w=6, head=22):
    d.line([(x0, y0), (x1, y1)], fill=col, width=w); a = math.atan2(y1 - y0, x1 - x0)
    d.polygon([(x1 + head * 0.3 * math.cos(a), y1 + head * 0.3 * math.sin(a)), (x1 - head * math.cos(a - 0.45), y1 - head * math.sin(a - 0.45)), (x1 - head * math.cos(a + 0.45), y1 - head * math.sin(a + 0.45))], fill=col)

def dashed(d, x0, y0, x1, y1, col=DIM, w=4, dash=18):
    n = max(1, int(math.hypot(x1 - x0, y1 - y0) / dash))
    for k in range(0, n, 2):
        a, b = k / n, min(1, (k + 1) / n); d.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)], fill=col, width=w)

def check(d, x, y, s=1.0, col=LIME):
    d.line([(x - 18 * s, y), (x - 4 * s, y + 14 * s), (x + 22 * s, y - 16 * s)], fill=col, width=int(9 * s), joint="curve")

def cross(d, x, y, s=1.0, col=CORAL):
    for a, b in (((-16, -16), (16, 16)), ((-16, 16), (16, -16))): d.line([(x + a[0] * s, y + a[1] * s), (x + b[0] * s, y + b[1] * s)], fill=col, width=int(9 * s))

def bars(img, rows, maxv, lt, x0=360, y0=360, gap=210, scale=1100, title=None):
    """rows: (label, value, colour, value_text). Bars grow one after another."""
    d = ImageDraw.Draw(img)
    for k, (name, v, col, vt) in enumerate(rows):
        u = eout((lt - 0.2 - k * 0.7) / 1.2); y = y0 + k * gap
        d.text((x0, y - 46), name, font=F(44, "Black"), fill=col, anchor="ls")
        d.rounded_rectangle([x0, y - 28, x0 + 1100, y + 28], 28, fill=(34, 24, 62))
        wv = max(56, v / maxv * scale * u)
        d.rounded_rectangle([x0, y - 28, x0 + wv, y + 28], 28, fill=col)
        if u > 0.05: d.text((x0 + wv + 24, y), vt, font=F(48, "Black"), fill=WHITE, anchor="lm")
    if title: pill(img, title, 40, W / 2, 150)

def thermo(img, x, frac, marks, top=230, bot=800):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x - 34, top - 20, x + 34, bot], 34, fill=(30, 22, 50), outline=WHITE, width=5); d.ellipse([x - 64, bot - 30, x + 64, bot + 98], fill=CORAL, outline=WHITE, width=5)
    yv = bot - (bot - top) * max(0.0, min(1.03, frac)); d.rounded_rectangle([x - 18, yv, x + 18, bot + 10], 18, fill=CORAL)
    for fr, lab_ in marks:
        yy_ = bot - (bot - top) * fr; d.line([(x - 50, yy_), (x + 50, yy_)], fill=GOLD, width=4); d.text((x + 70, yy_), lab_, font=F(32, "Bold"), fill=GOLD, anchor="lm")

def ground(d, y, col=(44, 30, 30), edge=(110, 80, 70)):
    pts = [(0, H)] + [(x, y + 8 * math.sin(x * 0.012)) for x in range(0, W + 1, 20)] + [(W, H)]
    d.polygon(pts, fill=col); d.line(pts[1:-1], fill=edge, width=4)

# ---------------- 1: peregrine falcon ----------------
F_BODY = [(0.5, 0), (0.44, -0.06), (0.32, -0.1), (0.1, -0.12), (-0.15, -0.11), (-0.35, -0.07), (-0.5, -0.035), (-0.5, 0.035), (-0.35, 0.07), (-0.15, 0.1), (0.1, 0.11), (0.3, 0.09), (0.44, 0.05)]
F_BELLY = [(0.4, 0.03), (0.3, 0.085), (0.1, 0.105), (-0.15, 0.095), (-0.35, 0.065), (-0.3, 0.02), (0.1, 0.02)]
F_WING_TUCK = [(0.28, -0.07), (0.05, -0.115), (-0.5, -0.05), (-0.58, -0.02), (-0.2, 0.01), (0.2, 0.0)]
F_WING_OPEN = [(0.16, -0.06), (0.02, -0.45), (-0.12, -0.62), (-0.2, -0.6), (-0.16, -0.3), (-0.2, -0.06)]
F_TAIL = [(-0.48, -0.03), (-0.7, -0.06), (-0.72, 0.05), (-0.48, 0.03)]
def falcon(d, cx, cy, L, ang=0.0, wings="tuck", flap=0.0):
    sl = (96, 110, 136); dk = (40, 46, 64)
    d.polygon(rot(F_TAIL, cx, cy, L, ang), fill=dk)
    if wings == "open":
        wo = [(x, y * (1 - 0.35 * flap)) for x, y in F_WING_OPEN]; d.polygon(rot(wo, cx, cy, L, ang), fill=(70, 80, 104))
    d.polygon(rot(F_BODY, cx, cy, L, ang), fill=sl)
    d.polygon(rot(F_BELLY, cx, cy, L, ang), fill=(232, 224, 208))
    for k in range(5):
        x = 0.2 - k * 0.1; d.line(rot([(x, 0.05), (x - 0.02, 0.08)], cx, cy, L, ang), fill=(130, 124, 120), width=max(2, int(L * 0.008)))
    if wings == "tuck": d.polygon(rot(F_WING_TUCK, cx, cy, L, ang), fill=(70, 80, 104))
    (hx, hy), = rot([(0.36, -0.03)], cx, cy, L, ang); r = 0.085 * L
    d.pieslice([hx - r, hy - r, hx + r, hy + r], 180 + math.degrees(ang), 360 + math.degrees(ang), fill=dk)
    d.line(rot([(0.42, -0.03), (0.4, 0.05)], cx, cy, L, ang), fill=dk, width=max(3, int(L * 0.025)))
    (ex, ey), = rot([(0.43, -0.035)], cx, cy, L, ang); er = 0.022 * L
    d.ellipse([ex - er, ey - er, ex + er, ey + er], fill=(250, 210, 60)); d.ellipse([ex - er * 0.55, ey - er * 0.55, ex + er * 0.55, ey + er * 0.55], fill=(10, 10, 14))
    d.polygon(rot([(0.49, -0.02), (0.56, 0.015), (0.48, 0.03)], cx, cy, L, ang), fill=(250, 200, 60))

def b_falcon(sc, lt, dur, t):
    mode = sc.get("mode")
    if mode == "perch":
        img = lab(t); d = ImageDraw.Draw(img)
        x = 1250 + 60 * math.sin(t * 0.5); y = 470 + 20 * math.sin(t * 0.9)
        falcon(d, x, y, 760, 0.0, "open", 0.5 + 0.5 * math.sin(t * 2.2))
        text(img, "NOT THE CHEETAH", 70, 460, 400, DIM, u=ease(lt / 0.4), maxw=700)
        d = ImageDraw.Draw(img); d.line([(150, 400), (770, 400)], fill=CORAL, width=8) if lt > 1.2 else None
        text(img, "PEREGRINE", 96, 460, 560, GOLD, u=ease((lt - 1.8) / 0.4), maxw=700); text(img, "FALCON", 96, 460, 660, GOLD, u=ease((lt - 2.0) / 0.4), maxw=700)
        return img
    if mode == "dive":
        img = lab(t, sparks=False); d = ImageDraw.Draw(img)
        p = ((lt * 0.3) % 1.0); ang = math.radians(48)
        x = 760 + p * 900; y = 160 + p * 900 * math.tan(ang)
        r = random.Random(int(lt * 12))
        for k in range(26):
            o = r.uniform(-120, 120); L = r.uniform(200, 620); s = r.uniform(0.25, 1.0)
            bx = x - math.cos(ang) * (160 + r.uniform(0, 80)) - math.sin(ang) * o; by = y - math.sin(ang) * (160 + r.uniform(0, 80)) + math.cos(ang) * o
            d.line([(bx, by), (bx - math.cos(ang) * L, by - math.sin(ang) * L)], fill=tuple(int(c * s) for c in (200, 190, 255)), width=3)
        falcon(d, x, y, 420, ang, "tuck")
        v = 320 * eout((lt - 0.2) / 2.2)
        d.rounded_rectangle([80, 640, 640, 900], 40, fill=CARD)
        text(img, f"~{int(v)} KM/H", 90, 360, 730, GOLD, maxw=520); text(img, "≈ 200 MPH", 50, 360, 830, WHITE, w="Bold", u=ease((lt - 2.0) / 0.4))
        pill(img, "WINGS TUCKED · FULL DIVE", 38, 1300, 150, fill=CORAL, ink=WHITE)
        return img
    img = lab(t)
    if mode == "cruise":
        bars(img, [("NORMAL FLIGHT", 55, TEAL, "40–55 km/h"), ("THE DIVE", 320, GOLD, "~320 km/h")], 400, lt, title="SAME BIRD")
    else:
        bars(img, [("CAR ON THE HIGHWAY", 100, TEAL, "100 km/h"), ("PEREGRINE DIVE (1999 TEST)", 389, GOLD, "389 km/h")], 420, lt)
        pill(img, "≈ 4× FASTER", 46, W / 2, 820, fill=CORAL, ink=WHITE, u=ease((lt - 2.0) / 0.4))
    return img

# ---------------- 2: octopus ----------------
OCX, OCY = 960, 430
def arm_pt(i, s, t, L=430):
    a = math.radians(18 + i * (144 / 7)); ux, uy = math.cos(a), math.sin(a)
    w = math.sin(s * 3.2 + t * 1.6 + i * 0.9) * 46 * s
    return (OCX + ux * s * L * 1.25 - uy * w, OCY + 40 + uy * s * L * 0.95 + ux * w)
def octopus(d, t, col=(232, 104, 118)):
    for i in range(8):
        pts = [arm_pt(i, k / 24, t) for k in range(25)]
        for k in range(24):
            wd = int(46 * (1 - k / 26) + 6); d.line([pts[k], pts[k + 1]], fill=col, width=wd)
            d.ellipse([pts[k][0] - wd / 2, pts[k][1] - wd / 2, pts[k][0] + wd / 2, pts[k][1] + wd / 2], fill=col)
    bob = 6 * math.sin(t * 1.2)
    d.ellipse([OCX - 150, OCY - 300 + bob, OCX + 150, OCY + 70 + bob], fill=col)
    d.ellipse([OCX - 100, OCY - 250 + bob, OCX - 30, OCY - 180 + bob], fill=(250, 150, 160))
    for sx in (-1, 1):
        ex = OCX + sx * 70; ey = OCY - 30 + bob; d.ellipse([ex - 34, ey - 30, ex + 34, ey + 30], fill=(250, 240, 220)); d.rounded_rectangle([ex - 20, ey - 7, ex + 20, ey + 7], 6, fill=(20, 14, 20))
NEUR_HEAD = [(OCX + random.Random(k).uniform(-110, 110), OCY - 120 + random.Random(k + 50).uniform(-130, 150)) for k in range(60)]
NEUR_ARM = [(random.Random(k * 3).randint(0, 7), random.Random(k * 3 + 1).uniform(0.12, 0.95)) for k in range(120)]
def neuron_dots(img, t, u, col_head=TEAL, col_arm=GOLD):
    hd = NEUR_HEAD[:int(len(NEUR_HEAD) * u)]; ar = [arm_pt(i, s, t) for i, s in NEUR_ARM[:int(len(NEUR_ARM) * u)]]
    glow(img, lambda dd, s: [dd.ellipse([(x - 12) * s, (y - 12) * s, (x + 12) * s, (y + 12) * s], fill=230) for x, y in hd], col_head, 10, 1.2)
    glow(img, lambda dd, s: [dd.ellipse([(x - 12) * s, (y - 12) * s, (x + 12) * s, (y + 12) * s], fill=230) for x, y in ar], col_arm, 10, 1.2)
    d = ImageDraw.Draw(img)
    for x, y in hd: d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(220, 255, 255))
    for x, y in ar: d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(255, 245, 200))

def b_octo(sc, lt, dur, t):
    mode = sc.get("mode"); img = lab(t); d = ImageDraw.Draw(img)
    octopus(d, t)
    if mode == "neurons":
        u = eout((lt - 0.2) / 2.0); neuron_dots(img, t, u, GOLD, GOLD)
        d = ImageDraw.Draw(img); d.rounded_rectangle([60, 300, 560, 560], 40, fill=CARD)
        text(img, f"{int(500 * u)} MILLION", 64, 310, 390, GOLD, maxw=460); text(img, "NEURONS", 44, 310, 470, WHITE, w="Bold", maxw=460)
        pill(img, "≈ AS MANY AS A DOG", 36, 1560, 300, fill=TEAL, u=ease((lt - 2.0) / 0.4))
    elif mode == "split":
        neuron_dots(img, t, 1.0)
        d = ImageDraw.Draw(img); u = ease((lt - 0.8) / 0.5)
        if u > 0:
            d.rounded_rectangle([60, 180, 520, 380], 40, fill=CARD); text(img, "~⅓ IN THE HEAD", 50, 290, 280, TEAL, u=u, maxw=420)
            v = ease((lt - 2.2) / 0.5)
            if v > 0: d.rounded_rectangle([1380, 640, 1860, 880], 40, fill=CARD); text(img, "~⅔ IN THE ARMS", 52, 1620, 730, GOLD, u=v, maxw=440); text(img, "not the brain", 38, 1620, 810, WHITE, w="SemiBold", u=v, maxw=440)
    else:   # share: pulses run from the brain down every arm
        neuron_dots(img, t, 1.0, TEAL, (120, 100, 60))
        pts = []
        for i in range(8):
            s = (lt * 0.5 + i * 0.03) % 1.0; pts.append(arm_pt(i, s, t))
        glow(img, lambda dd, s_: [dd.ellipse([(x - 30) * s_, (y - 30) * s_, (x + 30) * s_, (y + 30) * s_], fill=255) for x, y in pts], GOLD, 14, 1.4)
        d = ImageDraw.Draw(img)
        for x, y in pts: d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=(255, 250, 220))
        pill(img, "BRAIN LEARNS → EVERY ARM KNOWS", 40, W / 2, 140, fill=GOLD)
    return img

# ---------------- 3: dung beetle ----------------
def dung_beetle(d, x, y, s=1.0, cap=False, roll=0.0):
    """Side view, head down on the left, hind legs up on a ball to the right. (x, y) = feet line under the beetle."""
    bx, by = x, y - 70 * s; br = 80 * s; ball_x = x + 150 * s; ball_y = y - br
    d.ellipse([ball_x - br, ball_y - br, ball_x + br, ball_y + br], fill=(120, 84, 50), outline=(160, 120, 80), width=3)
    for k in range(7):
        a = roll + k * 0.9; rr = br * (0.3 + 0.08 * k)
        d.ellipse([ball_x + rr * math.cos(a) - 6 * s, ball_y + rr * math.sin(a) - 6 * s, ball_x + rr * math.cos(a) + 6 * s, ball_y + rr * math.sin(a) + 6 * s], fill=(96, 64, 38))
    body = rot([(0.6, 0), (0.45, -0.3), (0.0, -0.42), (-0.45, -0.3), (-0.6, 0), (-0.45, 0.3), (0.0, 0.42), (0.45, 0.3)], bx, by, 85 * s, math.radians(-28))
    for lx, ly, ex, ey in ((-30, 30, -70, 80), (10, 34, -10, 80), (40, 20, ball_x - x - br * 0.9, -20), (50, 0, ball_x - x - br * 0.6, -90)):
        d.line([(bx + lx * s, by + ly * s), (x + ex * s if ey > 0 else ball_x - br * 0.85, y - 70 * s + ey * s if ey > 0 else ball_y + ey * s * 0.5)], fill=(30, 26, 22), width=int(9 * s))
    d.polygon(body, fill=(40, 34, 30), outline=(100, 90, 80))
    d.line([body[1], body[5]], fill=(80, 70, 60), width=3)
    hx, hy = bx - 70 * s, by + 34 * s; d.pieslice([hx - 32 * s, hy - 26 * s, hx + 32 * s, hy + 26 * s], 0, 360, fill=(52, 44, 38))
    for k in range(4): d.line([(hx - 30 * s + k * 12 * s, hy + 18 * s), (hx - 36 * s + k * 12 * s, hy + 30 * s)], fill=(52, 44, 38), width=int(5 * s))
    if cap:
        d.chord([hx - 40 * s, hy - 52 * s, hx + 36 * s, hy + 10 * s], 180, 360, fill=CORAL); d.rectangle([hx - 50 * s, hy - 22 * s, hx + 4 * s, hy - 12 * s], fill=CORAL)

def milky_band(img, t, a=1.0):
    def g(dd, s):
        for k in range(14):
            x0 = 120 + k * 60; dd.ellipse([(x0 - 120) * s, (60 + k * 30) * s, (x0 + 160) * s, (200 + k * 30) * s], fill=int(90 * a))
    glow(img, g, (180, 170, 230), 40, 1.0)
    r = random.Random(3); d = ImageDraw.Draw(img)
    for k in range(int(240 * a)):
        u = r.random(); x = 60 + u * 900 + r.gauss(0, 60); y = 130 + u * 420 + r.gauss(0, 50); c = int(150 + 100 * r.random())
        d.point((x, y), fill=(c, c, 255)); d.point((x + 1, y), fill=(c, c, 255))

ARENA = (1380, 560, 300)
def arena_path(kind, u):
    cx, cy, R = ARENA; pts = []
    if kind == "straight":
        a = math.radians(-35); [pts.append((cx + math.cos(a) * R * k / 40 * u, cy + math.sin(a) * R * k / 40 * u)) for k in range(41)]
    else:
        x, y, a = cx, cy, 0.4; r = random.Random(11)
        for k in range(int(160 * u)):
            a += r.gauss(0, 0.45); x += 9 * math.cos(a); y += 9 * math.sin(a)
            if math.hypot(x - cx, y - cy) > R - 20: a += math.pi * 0.8; x -= 18 * math.cos(a - math.pi * 0.8); y -= 18 * math.sin(a - math.pi * 0.8)
            pts.append((x, y))
    return pts

def b_beetle(sc, lt, dur, t):
    mode = sc.get("mode")
    if mode == "roll":
        img = lab(t); d = ImageDraw.Draw(img); ground(d, 820)
        d.ellipse([140, 700, 520, 860], fill=(110, 76, 46)); d.ellipse([200, 660, 440, 790], fill=(120, 84, 50))
        dung_beetle(d, 300, 690, 0.6, roll=t)
        x = 700 + 520 * ease((lt - 0.3) / max(1.5, dur - 1.0)); dashed(d, 560, 836, x - 40, 836, GOLD, 5)
        dung_beetle(d, x, 820, 1.0, roll=-t * 3)
        pill(img, "STRAIGHT AWAY FROM THE PILE", 40, W / 2, 160); text(img, "before rivals steal the ball", 44, W / 2, 250, WHITE, w="SemiBold", u=ease((lt - 1.0) / 0.4))
        return img
    img = lab(t, night=True); d = ImageDraw.Draw(img)
    if mode == "dome":
        d.pieslice([360, 260, 1560, 1460], 180, 360, fill=(14, 16, 40), outline=(140, 130, 200), width=6)
        r = random.Random(5)
        for k in range(160):
            a = r.uniform(math.pi, 2 * math.pi); rr = 590 * math.sqrt(r.random()); x, y = 960 + rr * math.cos(a), 860 + rr * math.sin(a)
            if y < 850: f = 0.5 + 0.5 * math.sin(t * 2 + k); c = int(140 + 110 * f); d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(c, c, 255))
        d.rectangle([360, 860, 1560, 900], fill=(40, 30, 40)); dung_beetle(d, 960, 860, 0.7, roll=t)
        pill(img, "THE PLANETARIUM TEST", 42, W / 2, 150, fill=GOLD); text(img, "moonless sky, projected on a dome", 42, W / 2, 1010 - 90, DIM, w="SemiBold") if False else None
        return img
    # left: the sky the beetle sees; right: top-down arena with its track
    cx, cy, R = ARENA
    if mode in ("milky", "nomilky"):
        a = 1.0 if mode == "milky" else max(0.0, 1 - lt / 1.2); milky_band(img, t, a)
    d = ImageDraw.Draw(img); d.rounded_rectangle([60, 120, 1010, 900], 40, outline=(90, 90, 150), width=4)
    d.text((90, 140), "WHAT THE BEETLE SEES", font=F(30, "Bold"), fill=DIM)
    if mode == "nomilky":
        r = random.Random(8)
        for k in range(int(200 * ease((lt - 0.6) / 0.8))):
            x, y = r.uniform(100, 980), r.uniform(200, 860); d.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=(230, 230, 255))
        text(img, "+ THOUSANDS OF STARS", 44, 535, 780, WHITE, u=ease((lt - 0.8) / 0.4), maxw=860)
    if mode == "cap":
        d.rectangle([62, 122, 1008, 898], fill=(4, 4, 8)); dung_beetle(d, 470, 700, 1.4, cap=True, roll=t * 0.3)
        text(img, "CAP ON", 70, 535, 300, CORAL)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(28, 24, 34), outline=(120, 110, 150), width=5)
    d.text((cx, cy - R - 40), "TOP VIEW · ARENA", font=F(30, "Bold"), fill=DIM, anchor="mm")
    kind = "straight" if mode == "milky" else ("wander" if mode in ("cap", "nomilky") else "straight")
    u = ease((lt - 0.3) / max(1.5, dur - 1.0)) if not (mode == "nomilky") else ease((lt - 0.3) / max(1.5, dur - 1.0))
    pts = arena_path(kind, u)
    if mode == "nomilky":
        pts1 = arena_path("straight", 1.0); d.line(pts1, fill=(90, 120, 90), width=5)
        pts = arena_path("wander", u)
    if len(pts) > 1:
        d.line(pts, fill=GOLD if kind == "straight" else CORAL, width=7, joint="curve"); x, y = pts[-1]; d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=WHITE)
    else: d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=WHITE)
    lbl = {"milky": ("ONLY THE MILKY WAY", "STRAIGHT OUT", GOLD), "nomilky": ("MILKY WAY REMOVED", "SLOWER, WOBBLIER", CORAL), "cap": ("VIEW BLOCKED", "WANDERS AIMLESSLY", CORAL)}[mode]
    pill(img, lbl[0], 36, 535, 960 - 60 if False else 860, fill=(80, 70, 140), ink=WHITE) if mode != "cap" else None
    text(img, lbl[1], 50, cx, cy + R + 60, lbl[2], u=ease((lt - 1.0) / 0.4))
    return img

# ---------------- 4: electric eel ----------------
def eel_pts(x0, x1, y0, t, amp=60, waves=1.3):
    pts = []
    for k in range(61):
        s = k / 60; x = x0 + (x1 - x0) * s; y = y0 + amp * math.sin(s * 6.283 * waves - t * 3.0) * (1.1 - 0.8 * s)
        pts.append((x, y, s))
    return pts
def eel(d, x0, x1, y0, t, amp=60):
    pts = eel_pts(x0, x1, y0, t, amp); top, bot = [], []
    for k, (x, y, s) in enumerate(pts):
        x2, y2, _ = pts[min(k + 1, 60)]; x1_, y1_, _ = pts[max(k - 1, 0)]; a = math.atan2(y2 - y1_, x2 - x1_); nx, ny = -math.sin(a), math.cos(a)
        th = 8 + 52 * min(1.0, s * 1.6) * (1 - max(0, s - 0.93) * 6)
        top.append((x - nx * th, y - ny * th)); bot.append((x + nx * th * 0.95, y + ny * th * 0.95))
    d.polygon(top + bot[::-1], fill=(64, 72, 50), outline=(110, 120, 80))
    d.line(bot[8:-3], fill=(214, 150, 70), width=10)
    hx, hy, _ = pts[-1]; d.ellipse([hx - 30, hy - 26, hx + 30, hy + 22], fill=(64, 72, 50))
    d.ellipse([hx - 4, hy - 20, hx + 8, hy - 8], fill=(240, 220, 120)); d.line([(hx + 10, hy + 6), (hx + 30, hy + 4)], fill=(30, 30, 20), width=4)
    return pts
def zaps(img, pts, t, n=9, col=(255, 240, 120)):
    r = random.Random(int(t * 12)); segs = []
    for _ in range(n):
        x, y, s = pts[r.randint(10, 58)]; a = r.uniform(0, 6.283); L = r.uniform(70, 170); seg = [(x, y)]
        for j in range(1, 6): seg.append((x + math.cos(a) * L * j / 5 + r.uniform(-18, 18), y + math.sin(a) * L * j / 5 + r.uniform(-18, 18)))
        segs.append(seg)
    glow(img, lambda dd, s_: [dd.line([(x * s_, y * s_) for x, y in seg], fill=255, width=3) for seg in segs], (120, 200, 255), 10, 1.6)
    d = ImageDraw.Draw(img)
    for seg in segs: d.line(seg, fill=col, width=4)

def b_eel(sc, lt, dur, t):
    mode = sc.get("mode"); img = lab(t); d = ImageDraw.Draw(img)
    if mode == "swim":
        off = 80 * math.sin(t * 0.4); pts = eel(d, 300 + off, 1650 + off, 600, t)
        pill(img, "ELECTROPHORUS VOLTAI", 44, W / 2, 200, fill=GOLD); text(img, "described in 2019 · Amazon basin", 42, W / 2, 290, WHITE, w="SemiBold", u=ease((lt - 0.6) / 0.4))
    elif mode == "bars":
        bars(img, [("THE CLASSIC ELECTRIC EEL", 650, TEAL, "~650 V"), ("ELECTROPHORUS VOLTAI", 860, GOLD, "860 V")], 900, lt, title="NEW RECORD HOLDER")
    elif mode == "compare":
        bars(img, [("US WALL OUTLET", 120, TEAL, "~120 V"), ("ONE EEL", 860, GOLD, "860 V")], 900, lt)
        ox, oy = 1640, 330; d = ImageDraw.Draw(img); d.rounded_rectangle([ox - 70, oy - 90, ox + 70, oy + 90], 24, fill=(230, 226, 240))
        for sx in (-26, 26): d.rounded_rectangle([ox + sx - 7, oy - 50, ox + sx + 7, oy - 10], 4, fill=(40, 30, 50))
        d.chord([ox - 16, oy + 18, ox + 16, oy + 52], 180, 360, fill=(40, 30, 50)); d.rectangle([ox - 16, oy + 35, ox + 16, oy + 52], fill=(40, 30, 50))
        pill(img, "≈ 7×", 60, W / 2, 820, fill=CORAL, ink=WHITE, u=ease((lt - 2.0) / 0.4))
    else:
        pts = eel(d, 250, 1670, 560, t, 40); zaps(img, pts, t, 12)
        d = ImageDraw.Draw(img); y = 790; d.line([(250, y), (1670, y)], fill=GOLD, width=5)
        for x in (250, 1670): d.line([(x, y - 18), (x, y + 18)], fill=GOLD, width=5)
        text(img, "2+ METERS", 64, W / 2, y + 70, GOLD)
        pill(img, "A LIVING BATTERY", 44, W / 2, 200, fill=TEAL)
    return img

# ---------------- 5: axolotl ----------------
PINK, GILL = (250, 176, 196), (236, 88, 128)
def axolotl(d, cx, cy, s=1.0, t=0.0, leg=1.0, glow_leg=False):
    bob = 6 * math.sin(t * 1.4)
    cy = cy + bob
    wag = 26 * s * math.sin(t * 2)
    d.polygon([(cx - 200 * s, cy - 78 * s), (cx - 400 * s, cy - 62 * s + wag * 0.5), (cx - 610 * s, cy + wag), (cx - 400 * s, cy + 46 * s + wag * 0.5), (cx - 200 * s, cy + 62 * s)], fill=(252, 206, 220))
    d.polygon([(cx - 200 * s, cy - 44 * s), (cx - 420 * s, cy - 22 * s + wag * 0.5), (cx - 590 * s, cy + wag), (cx - 420 * s, cy + 18 * s + wag * 0.5), (cx - 200 * s, cy + 40 * s)], fill=(244, 160, 184))
    for lx, ln_ in ((-140, 1.0), (130, leg)):
        if ln_ <= 0.02: continue
        x0, y0 = cx + lx * s, cy + 50 * s; x1, y1 = x0 + 30 * s * ln_, y0 + 110 * s * ln_
        d.line([(x0, y0), (x1, y1)], fill=PINK, width=int(30 * s));
        if ln_ > 0.85:
            for k in range(4): d.line([(x1, y1), (x1 - 24 * s + k * 18 * s, y1 + 26 * s)], fill=PINK, width=int(10 * s))
    d.ellipse([cx - 280 * s, cy - 80 * s, cx + 200 * s, cy + 80 * s], fill=PINK)
    hx, hy = cx + 250 * s, cy - 14 * s
    for k, a in enumerate((-2.2, -1.75, -1.3)):
        for sx in (0,):
            x0, y0 = hx - 80 * s, hy - 50 * s + k * 10 * s; aa = a + 0.08 * math.sin(t * 2 + k); x1, y1 = x0 + math.cos(aa) * 150 * s, y0 + math.sin(aa) * 150 * s
            d.line([(x0, y0), (x1, y1)], fill=GILL, width=int(14 * s))
            for j in range(1, 6):
                fx, fy = x0 + (x1 - x0) * j / 6, y0 + (y1 - y0) * j / 6
                for sg in (-1, 1): d.line([(fx, fy), (fx + math.cos(aa + sg * 1.2) * 26 * s, fy + math.sin(aa + sg * 1.2) * 26 * s)], fill=GILL, width=int(6 * s))
    d.ellipse([hx - 130 * s, hy - 95 * s, hx + 120 * s, hy + 90 * s], fill=PINK)
    d.ellipse([hx + 30 * s, hy - 40 * s, hx + 58 * s, hy - 12 * s], fill=(30, 20, 30))
    d.arc([hx - 10 * s, hy - 10 * s, hx + 110 * s, hy + 50 * s], 20, 120, fill=(180, 80, 110), width=int(6 * s))
    if glow_leg: return (cx + 130 * s, cy + 50 * s)

def b_axo(sc, lt, dur, t):
    mode = sc.get("mode"); img = lab(t); d = ImageDraw.Draw(img)
    if mode == "hello":
        axolotl(d, 1060, 520, 1.15, t); pill(img, "AXOLOTL", 48, 520, 820, fill=GOLD); text(img, "a salamander from Mexico", 40, 520, 900, WHITE, w="SemiBold", u=ease((lt - 0.5) / 0.4))
        return img
    if mode == "regrow":
        cyc = (lt % 3.4) / 3.4; g = ease((cyc - 0.15) / 0.7)
        sp = axolotl(d, 1000, 480, 1.15, t, leg=g, glow_leg=True)
        if g < 0.98: halo(img, sp[0], sp[1] + 40, 70, (255, 220, 120), 200)
        n = 1 + int(lt / 3.4)
        pill(img, "REGROWING…" if g < 0.98 else "NEW LEG ✓" if False else "NEW LEG", 44, W / 2, 160, fill=GOLD if g >= 0.98 else TEAL)
        text(img, f"TIME #{n}", 60, 300, 860, WHITE, u=ease((lt - 0.4) / 0.4))
        return img
    if mode == "done":
        axolotl(d, 1000, 480, 1.15, t); d = ImageDraw.Draw(img); x, y = 1000 + 150 * 1.15, 480 + 140 * 1.15
        d.ellipse([x - 120, y - 120, x + 120, y + 120], outline=GOLD, width=6)
        text(img, "WHERE WAS THE CUT?", 70, W / 2, 180, WHITE); text(img, "?", 120, x + 200, y - 40, GOLD, u=ease((lt - 0.5) / 0.4))
        return img
    if mode == "parts":
        axolotl(d, 640, 540, 0.85, t); d = ImageDraw.Draw(img)
        for k, s in enumerate(("LEGS", "PARTS OF THE SPINAL CORD", "PIECES OF THE HEART", "PARTS OF THE BRAIN")):
            u = ease((lt - 0.3 - k * 0.9) / 0.4)
            if u <= 0: continue
            y = 280 + k * 150; check(d, 1150, y, 1.4); text(img, s, 50, 1210, y, GOLD if k == 3 else WHITE, anchor="lm", u=u, maxw=680)
        pill(img, "IT CAN REGENERATE…", 40, 640, 160, fill=TEAL)
        return img
    # lab
    axolotl(d, 960, 470, 1.0, t); d = ImageDraw.Draw(img)
    pill(img, "STUDIED IN LABS WORLDWIDE", 42, W / 2, 150, fill=GOLD); text(img, "to help humans heal", 56, W / 2, 860, WHITE, w="Bold", u=ease((lt - 0.5) / 0.4))
    return img

# ---------------- 6: bombardier beetle ----------------
def bombardier(d, cx, cy, s=1.0, t=0.0):
    for k, (lx, ex) in enumerate(((-90, -150), (0, -30), (70, 120))):
        sw = 6 * math.sin(t * 6 + k)
        d.line([(cx + lx * s, cy + 40 * s), (cx + (ex + sw) * s, cy + 120 * s)], fill=(30, 26, 30), width=int(10 * s))
    d.ellipse([cx - 230 * s, cy - 110 * s, cx + 90 * s, cy + 70 * s], fill=(34, 52, 104), outline=(110, 140, 220), width=4)
    d.line([(cx - 230 * s, cy - 20 * s), (cx + 80 * s, cy - 20 * s)], fill=(70, 100, 170), width=3)
    d.ellipse([cx + 60 * s, cy - 70 * s, cx + 190 * s, cy + 50 * s], fill=(232, 126, 40))
    d.ellipse([cx + 160 * s, cy - 50 * s, cx + 250 * s, cy + 30 * s], fill=(232, 126, 40))
    d.ellipse([cx + 200 * s, cy - 34 * s, cx + 222 * s, cy - 12 * s], fill=(20, 16, 20))
    for sg in (0, 1): d.line([(cx + 230 * s, cy - 40 * s), (cx + (330 + 30 * sg) * s, cy - (130 - 40 * sg) * s)], fill=(200, 110, 40), width=int(6 * s))
    return (cx - 230 * s, cy - 20 * s)

def b_bomb(sc, lt, dur, t):
    mode = sc.get("mode"); img = lab(t); d = ImageDraw.Draw(img)
    if mode == "intro":
        ground(d, 760); bombardier(d, 1100, 640, 1.4, t)
        pill(img, "BOMBARDIER BEETLE", 46, W / 2, 170, fill=GOLD); text(img, "armed at the back end", 46, W / 2, 260, WHITE, w="SemiBold", u=ease((lt - 0.5) / 0.4))
        return img
    if mode == "chambers":
        y0, y1 = 360, 720; open_ = (lt % 1.2) < 0.6
        d.rounded_rectangle([200, y0, 820, y1], 60, fill=(30, 40, 80), outline=WHITE, width=5)
        d.rounded_rectangle([220, y0 + 120, 800, y1 - 20], 46, fill=(60, 110, 200))
        d.rounded_rectangle([1000, y0 + 40, 1480, y1 - 40], 60, fill=(70, 40, 40), outline=WHITE, width=5)
        d.rectangle([820, 520, 1000, 560], fill=(50, 40, 70)); vx = 910
        d.rectangle([vx - 10, 500 if not open_ else 470, vx + 10, 580 if not open_ else 500], fill=GOLD)
        d.polygon([(1480, 500), (1640, 470), (1640, 610), (1480, 580)], fill=(90, 60, 60), outline=WHITE)
        if open_ and lt > 1.0:
            p = (lt % 0.6) / 0.6; x = 830 + p * 170; d.ellipse([x - 14, 526, x + 14, 554], fill=(120, 180, 255))
        if lt > 1.0 and not open_: halo(img, 1240, 540, 120, (255, 160, 60), 220)
        d = ImageDraw.Draw(img)
        text(img, "FUEL", 60, 510, 300, (140, 190, 255)); text(img, "ENZYMES", 60, 1240, 300, (255, 170, 110))
        text(img, "VALVE", 34, 910, 640, GOLD, w="Bold")
        if lt > 3.5: arrow(d, 1660, 540, 1840, 540, CORAL, 10, 40)
        return img
    # spray
    ground(d, 820); rear = bombardier(d, 1250, 700, 1.15, t * 0.2)
    pulse = (lt * 4) % 1.0; d = ImageDraw.Draw(img)
    puffs = []
    for k in range(10):
        p = ((lt * 4 - k * 0.1) % 1.0)
        if lt * 4 - k * 0.1 < 0: continue
        x = rear[0] - 40 - p * 560; y = rear[1] - 30 - p * 150 - 60 * math.sin(p * 3); r = 20 + 60 * p; puffs.append((x, y, r, 1 - p))
    glow(img, lambda dd, s: [dd.ellipse([(x - r) * s, (y - r) * s, (x + r) * s, (y + r) * s], fill=int(255 * a)) for x, y, r, a in puffs], (255, 200, 140), 16, 1.2)
    d = ImageDraw.Draw(img)
    for x, y, r, a in puffs: d.ellipse([x - r * 0.5, y - r * 0.5, x + r * 0.5, y + r * 0.5], fill=tuple(int(240 * a + 40 * (1 - a)) for _ in range(3)))
    fr = eout((lt - 0.4) / 2.2); thermo(img, 200, fr, [(1.0, "100°C")], top=260, bot=740)
    text(img, f"~{int(100 * fr)}°C", 110, 1250, 260, CORAL); text(img, "BOILING-HOT SPRAY", 48, 1250, 370, WHITE, w="Bold", u=ease((lt - 1.5) / 0.4))
    return img

# ---------------- 7: mantis shrimp ----------------
SEG_COLS = [(60, 200, 170), (70, 190, 120), (120, 200, 90), (200, 190, 70), (230, 140, 60), (230, 90, 70)]
def mantis(d, hx, hy, s, t, strike=0.0):
    for k in range(6):
        x = hx - 90 * s - k * 70 * s; r = (62 - k * 5) * s; y = hy + 8 * s * k
        d.ellipse([x - 52 * s, y - r, x + 52 * s, y + r], fill=SEG_COLS[k], outline=(20, 40, 40), width=3)
    tx = hx - 90 * s - 6 * 70 * s + 20 * s; ty = hy + 40 * s
    for a in (-0.5, 0.0, 0.5): d.polygon([(tx, ty), (tx - 90 * s * math.cos(a), ty + 90 * s * math.sin(a) - 20 * s), (tx - 70 * s * math.cos(a), ty + 90 * s * math.sin(a) + 20 * s)], fill=(60, 150, 200))
    for k in range(4): d.line([(hx - 120 * s - k * 60 * s, hy + 50 * s), (hx - 130 * s - k * 60 * s, hy + 110 * s)], fill=(230, 120, 80), width=int(8 * s))
    d.ellipse([hx - 70 * s, hy - 66 * s, hx + 70 * s, hy + 60 * s], fill=(70, 210, 190), outline=(20, 40, 40), width=3)
    for sx, h in ((-10, 120), (20, 140)):
        ex, ey = hx + sx * s + 30 * s, hy - h * s; d.line([(hx + sx * s, hy - 40 * s), (ex, ey)], fill=(70, 210, 190), width=int(12 * s))
        d.ellipse([ex - 26 * s, ey - 20 * s, ex + 26 * s, ey + 20 * s], fill=(120, 230, 110), outline=(20, 40, 40), width=3)
        d.line([(ex - 26 * s, ey), (ex + 26 * s, ey)], fill=(30, 60, 40), width=int(4 * s))
    sxp, syp = hx + 40 * s, hy + 50 * s
    a1 = math.radians(100 - 110 * strike); a2 = math.radians(-100 + 200 * strike) if strike < 1 else math.radians(100 - 110)
    ex, ey = sxp + math.cos(a1) * 110 * s, syp + math.sin(a1) * 110 * s
    a2 = a1 + math.radians(-150 + 150 * strike)
    cx_, cy_ = ex + math.cos(a2) * 120 * s, ey + math.sin(a2) * 120 * s
    d.line([(sxp, syp), (ex, ey)], fill=(230, 100, 90), width=int(26 * s)); d.line([(ex, ey), (cx_, cy_)], fill=(240, 120, 100), width=int(30 * s))
    d.ellipse([cx_ - 34 * s, cy_ - 34 * s, cx_ + 34 * s, cy_ + 34 * s], fill=(250, 150, 110), outline=(120, 40, 40), width=3)
    return cx_, cy_

def snail(d, x, y, r, cracked=False):
    d.ellipse([x - r, y - r, x + r, y + r], fill=(220, 190, 140), outline=(120, 90, 60), width=5)
    for k in range(1, 5): rr = r * (1 - k * 0.2); d.arc([x - rr + k * 6, y - rr, x + rr + k * 6, y + rr], 200, 520, fill=(150, 110, 70), width=5)
    if cracked:
        d.line([(x - r * 0.9, y - 10), (x - r * 0.4, y + 10), (x - r * 0.1, y - 20), (x + r * 0.2, y + 6)], fill=(40, 30, 20), width=6)

def b_mantis(sc, lt, dur, t):
    mode = sc.get("mode"); img = lab(t); d = ImageDraw.Draw(img); hx, hy, s = 900, 520, 1.25
    if mode == "intro":
        mantis(d, hx, hy, s, t, 0.0); snail(d, 1400, 640, 90)
        pill(img, "MANTIS SHRIMP", 46, W / 2, 160, fill=GOLD); text(img, "club-like arms, folded and ready", 42, W / 2, 250, WHITE, w="SemiBold", u=ease((lt - 0.6) / 0.4))
        return img
    if mode == "strike":
        cyc = (lt % 1.6) / 1.6; st = 0.0 if cyc < 0.55 else min(1.0, (cyc - 0.55) / 0.06) if cyc < 0.85 else max(0.0, 1 - (cyc - 0.85) / 0.15)
        cx_, cy_ = mantis(d, hx, hy, s, t, st); snail(d, 1310, 640, 90, cracked=lt > 1.0)
        if 0.6 < cyc < 0.7:
            for k in range(5): d.arc([cx_ - 60 - k * 30, cy_ - 60 - k * 30, cx_ + 60 + k * 30, cy_ + 60 + k * 30], -40, 40, fill=WHITE, width=4)
        d.rounded_rectangle([1420, 280, 1880, 560], 40, fill=CARD)
        text(img, "~80 KM/H", 76, 1650, 360, GOLD, maxw=420); text(img, "1,000s OF G", 56, 1650, 470, WHITE, u=ease((lt - 2.5) / 0.4), maxw=420)
        return img
    st = 1.0; cx_, cy_ = mantis(d, hx, hy, s, t, st); snail(d, 1310, 640, 90, cracked=True)
    bx, by = cx_ + 60, cy_
    if mode == "bubble":
        g = eout((lt - 0.3) / 1.2); r = 10 + 80 * g
        glow(img, lambda dd, s_: dd.ellipse([(bx - r) * s_, (by - r) * s_, (bx + r) * s_, (by + r) * s_], outline=255, width=2), (180, 230, 255), 6, 1.4)
        d = ImageDraw.Draw(img); d.ellipse([bx - r, by - r, bx + r, by + r], outline=(220, 245, 255), width=5); d.ellipse([bx - r * 0.5, by - r * 0.6, bx - r * 0.2, by - r * 0.3], fill=(230, 250, 255))
        pill(img, "CAVITATION BUBBLE", 42, W / 2, 160, fill=TEAL)
    elif mode == "flash":
        cyc = (lt % 1.8) / 1.8; r = 80 * (1 - ease(cyc / 0.4)); f = max(0.0, 1 - abs(cyc - 0.42) / 0.12)
        if r > 3: d.ellipse([bx - r, by - r, bx + r, by + r], outline=(220, 245, 255), width=5)
        if f > 0: halo(img, bx, by, 160, (255, 250, 200), 255 * f); d = ImageDraw.Draw(img)
        for k, w_ in enumerate(("HEAT", "SOUND", "LIGHT")):
            u = ease((lt - 0.6 - k * 0.6) / 0.4)
            if u > 0: pill(img, w_, 50, 1650, 330 + k * 150, fill=(CORAL, TEAL, GOLD)[k], ink=WHITE if k == 0 else INK, u=u)
    return img

# ---------------- 8: wood frog (+ the hook) ----------------
FROG, FROG_D = (176, 132, 84), (120, 84, 50)
def frog(d, cx, cy, s=1.0, col=FROG):
    dk = tuple(int(c * 0.68) for c in col)
    for sx in (-1, 1): d.ellipse([cx + sx * 150 * s - 110 * s, cy + 10 * s, cx + sx * 150 * s + 110 * s, cy + 150 * s], fill=dk)
    d.ellipse([cx - 190 * s, cy - 150 * s, cx + 190 * s, cy + 140 * s], fill=col)
    d.ellipse([cx - 120 * s, cy - 10 * s, cx + 120 * s, cy + 130 * s], fill=tuple(min(255, int(c * 1.3)) for c in col))
    for sx in (-1, 1):
        d.polygon([(cx + sx * 60 * s, cy - 120 * s), (cx + sx * 200 * s, cy - 100 * s), (cx + sx * 190 * s, cy - 40 * s), (cx + sx * 60 * s, cy - 70 * s)], fill=(60, 40, 30))
        ex = cx + sx * 100 * s; ey = cy - 140 * s; d.ellipse([ex - 50 * s, ey - 46 * s, ex + 50 * s, ey + 46 * s], fill=col)
        d.ellipse([ex - 32 * s, ey - 30 * s, ex + 32 * s, ey + 30 * s], fill=(236, 210, 120)); d.ellipse([ex - 26 * s, ey - 12 * s, ex + 26 * s, ey + 12 * s], fill=(14, 10, 10))
        d.ellipse([cx + sx * 70 * s - 26 * s, cy + 110 * s, cx + sx * 70 * s + 26 * s, cy + 150 * s], fill=dk)
    d.arc([cx - 130 * s, cy - 110 * s, cx + 130 * s, cy - 10 * s], 20, 160, fill=(70, 50, 30), width=int(6 * s))

def ice_block(img, box, t, frac=1.0):
    x0, y0, x1, y1 = box; top = y1 - (y1 - y0) * frac
    if frac <= 0: return
    tint(img, (x0, top, x1, y1), (150, 220, 255), 120, 24)
    d = ImageDraw.Draw(img); d.rounded_rectangle([x0, top, x1, y1], 24, outline=(220, 245, 255), width=5)
    r = random.Random(4)
    for k in range(10):
        x = r.uniform(x0 + 30, x1 - 60); y = r.uniform(top + 20, y1 - 40)
        if y > top: d.line([(x, y), (x + 40, y - 30)], fill=(235, 250, 255), width=3)
    for k in range(40):
        x = r.uniform(x0, x1); y = r.uniform(top, y1); d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(240, 252, 255))

def ecg(img, box, t, lt, flat_at=None, revive_at=None):
    x0, y0, x1, y1 = box; d = ImageDraw.Draw(img); d.rounded_rectangle(box, 26, fill=(6, 20, 16), outline=(70, 120, 100), width=4)
    for gx in range(int(x0) + 30, int(x1), 40): d.line([(gx, y0 + 8), (gx, y1 - 8)], fill=(12, 40, 30), width=1)
    pts = []; mid = (y0 + y1) / 2 + 10; n = int((x1 - x0 - 40) / 4)
    for k in range(n):
        x = x0 + 20 + k * 4; tt_ = lt - (n - k) * 0.006
        alive = (flat_at is None or tt_ < flat_at) or (revive_at is not None and tt_ > revive_at)
        ph = (tt_ * 1.3) % 1.0; y = mid
        if alive:
            if 0.10 < ph < 0.13: y = mid - (y1 - y0) * 0.38
            elif 0.13 <= ph < 0.16: y = mid + (y1 - y0) * 0.18
            elif 0.30 < ph < 0.4: y = mid - 10 * math.sin((ph - 0.3) / 0.1 * math.pi)
        pts.append((x, y))
    glow(img, lambda dd, s: dd.line([(x * s, y * s) for x, y in pts], fill=255, width=2), (80, 255, 140), 6, 1.2)
    d = ImageDraw.Draw(img); d.line(pts, fill=(140, 255, 170), width=4)
    alive_now = (flat_at is None or lt < flat_at) or (revive_at is not None and lt > revive_at)
    d.text((x0 + 26, y0 + 16), "HEART", font=F(28, "Bold"), fill=(120, 200, 150))
    d.text((x1 - 26, y0 + 16), "BEATING" if alive_now else "0 BPM", font=F(28, "Black"), fill=(140, 255, 170) if alive_now else CORAL, anchor="ra")

def b_frog(sc, lt, dur, t):
    mode = sc.get("mode")
    if mode == "hook":
        img = lab(t, sparks=False); halo(img, 1300, 470, 360, (90, 170, 230), 120); d = ImageDraw.Draw(img)
        frog(d, 1300, 520, 1.1, (150, 150, 160)); ice_block(img, (970, 180, 1630, 780), t)
        ecg(img, (970, 820, 1630, 940), t, lt + 10, flat_at=0.0)
        for i, s in enumerate(sc["lines"]): text(img, s, 110 if i == 0 else 130, 490, 400 + i * 150, GOLD if i == 1 else WHITE, maxw=820)
        pill(img, "…THEN THAWS OUT IN SPRING", 36, 490, 700, fill=TEAL, u=ease((lt - 4.0) / 0.4))
        return img
    img = lab(t); d = ImageDraw.Draw(img)
    if mode == "meet":
        frog(d, 1250, 560, 1.2); pill(img, "WOOD FROG", 48, 520, 400, fill=GOLD); text(img, "as far north as Alaska", 44, 520, 490, WHITE, w="SemiBold", u=ease((lt - 0.5) / 0.4))
        for k in range(14):
            x = 160 + k * 120 + 20 * math.sin(t + k); y = ((t * 40 + k * 70) % 900) + 80; d.line([(x - 8, y), (x + 8, y)], fill=(230, 240, 255), width=3); d.line([(x, y - 8), (x, y + 8)], fill=(230, 240, 255), width=3)
        return img
    if mode == "ice":
        u = ease((lt - 0.3) / 2.2); col = tuple(int(a * (1 - u * 0.5) + b * u * 0.5) for a, b in zip(FROG, (150, 150, 160)))
        frog(d, 1250, 560, 1.2, col); ice_block(img, (915, 230, 1585, 830), t, 0.6 * u / 0.6 if u < 1 else 1.0)
        text(img, f"{int(60 * u)}%", 200, 480, 460, (170, 230, 255)); text(img, "OF ITS BODY FROZEN", 52, 480, 610, WHITE, u=ease((lt - 0.6) / 0.4), maxw=760)
        return img
    if mode == "flat":
        frog(d, 1350, 480, 1.0, (150, 150, 160)); ice_block(img, (1075, 230, 1625, 720), t)
        ecg(img, (1060, 780, 1640, 920), t, lt, flat_at=0.6)
        d = ImageDraw.Draw(img)
        for k, s in enumerate(("HEART", "BRAIN", "BREATHING")):
            u = ease((lt - 0.4 - k * 0.7) / 0.3)
            if u <= 0: continue
            y = 300 + k * 160; cross(d, 200, y, 1.6); text(img, s, 70, 270, y, WHITE, anchor="lm", u=u, maxw=600)
        text(img, "STOPPED", 60, 420, 820, CORAL, u=ease((lt - 2.6) / 0.4))
        return img
    if mode == "sugar":
        frog(d, 1300, 560, 1.1, (160, 150, 150)); r = random.Random(2)
        hexes = []
        for k in range(26):
            p = (lt * 0.25 + k / 26) % 1; x = 1300 + r.uniform(-200, 200); y = 300 + r.uniform(0, 460); a_ = p * 6
            hexes.append((x, y, a_, min(1.0, lt / 1.0)))
        for x, y, a_, al in hexes:
            pts = [(x + 18 * math.cos(a_ + k * 1.047), y + 18 * math.sin(a_ + k * 1.047)) for k in range(6)]; d.polygon(pts, outline=GOLD, width=3)
        pill(img, "GLUCOSE = ANTIFREEZE", 44, 600, 200, fill=GOLD)
        fr = (16 * eout((lt - 2.5) / 1.6)) / 20.0
        thermo(img, 320, 1 - fr, [(1.0, "0°C"), (1 - 0.8, "−16°C")], top=340, bot=820)
        text(img, f"−{int(20 * fr)}°C" if fr > 0.02 else "0°C", 90, 760, 520, (170, 230, 255))
        return img
    # thaw
    u = ease((lt - 0.3) / 2.0); col = tuple(int(b * (1 - u) + a * u) for a, b in zip(FROG, (150, 150, 160)))
    hop = max(0.0, math.sin(max(0, lt - 3.0) * 4)) * 60 if lt > 3.0 else 0
    frog(d, 1300, 520 - hop, 1.1, col); ice_block(img, (1000, 230, 1600, 780), t, 1 - u)
    for k in range(8):
        if u > 0.1: x = 1060 + k * 65; y = 790 + ((t * 120 + k * 37) % 120); d.ellipse([x - 6, y - 10, x + 6, y + 6], fill=(150, 220, 255))
    ecg(img, (120, 760, 760, 900), t, lt, flat_at=-1, revive_at=1.6)
    pill(img, "SPRING", 48, 440, 300, fill=LIME); text(img, "heart starts again", 52, 440, 400, WHITE, w="Bold", u=ease((lt - 1.6) / 0.4), maxw=700)
    return img

# ---------------- 9: tardigrade ----------------
TARD = (226, 200, 160)
def tardigrade(d, cx, cy, s=1.0, t=0.0, tun=0.0):
    if tun >= 0.98:
        d.ellipse([cx - 120 * s, cy - 90 * s, cx + 120 * s, cy + 90 * s], fill=(200, 170, 120), outline=(140, 110, 70), width=4)
        for k in range(5): d.arc([cx - 100 * s + k * 10 * s, cy - 70 * s, cx + 100 * s - k * 10 * s, cy + 70 * s], 200 + k * 5, 330 - k * 5, fill=(150, 120, 80), width=4)
        return
    sq = 1 - 0.6 * tun; ll = 1 - tun
    for k in range(4):
        lx = cx + (-210 + k * 140) * s * sq; sw = 10 * math.sin(t * 4 + k * 1.3)
        if ll > 0.05:
            d.rounded_rectangle([lx - 26 * s, cy + 40 * s, lx + 26 * s, cy + (40 + 90 * ll) * s], int(24 * s), fill=TARD)
            for c in range(3): d.line([(lx - 14 * s + c * 14 * s + sw * 0.2, cy + (40 + 90 * ll) * s), (lx - 18 * s + c * 14 * s + sw * 0.2, cy + (54 + 90 * ll) * s)], fill=(90, 70, 50), width=int(4 * s))
    for k in range(4):
        x = cx + (-220 + k * 145) * s * sq; d.ellipse([x - 120 * s * sq, cy - 110 * s, x + 120 * s * sq, cy + 90 * s], fill=TARD)
    for k in range(3): x = cx + (-150 + k * 145) * s * sq; d.arc([x - 40 * s, cy - 104 * s, x + 40 * s, cy + 84 * s], 250, 290, fill=(190, 160, 120), width=int(5 * s))
    hx = cx + 300 * s * sq; d.ellipse([hx - 70 * s, cy - 70 * s, hx + 70 * s, cy + 60 * s], fill=TARD)
    d.ellipse([hx + 50 * s, cy - 10 * s, hx + 84 * s, cy + 24 * s], fill=(200, 160, 130)); d.ellipse([hx + 62 * s, cy + 2 * s, hx + 74 * s, cy + 12 * s], fill=(80, 50, 40))
    d.ellipse([hx + 10 * s, cy - 40 * s, hx + 26 * s, cy - 24 * s], fill=(30, 20, 20))

def b_tard(sc, lt, dur, t):
    mode = sc.get("mode")
    if mode == "orbit" or mode == "survive":
        img = lab(t, night=True); d = ImageDraw.Draw(img)
        ex, ey, R = 760, 1640, 980
        halo(img, ex, ey, R + 40, (60, 120, 255), 160); d = ImageDraw.Draw(img)
        d.ellipse([ex - R, ey - R, ex + R, ey + R], fill=(30, 80, 170))
        r = random.Random(6)
        for k in range(9):
            a = r.uniform(-2.6, -0.5); rr = R * r.uniform(0.6, 0.97); x, y = ex + rr * math.cos(a), ey + rr * math.sin(a); w_ = r.uniform(60, 160)
            d.ellipse([x - w_, y - w_ * 0.5, x + w_, y + w_ * 0.5], fill=(60, 140, 90))
        a = -1.9 + 0.9 * ((lt * 0.08) % 1.0) if mode == "orbit" else -1.45; Ro = R + 160
        sx, sy = ex + Ro * math.cos(a), ey + Ro * math.sin(a)
        d.arc([ex - Ro, ey - Ro, ex + Ro, ey + Ro], 200, 340, fill=(80, 90, 130), width=2)
        d.ellipse([sx - 60, sy - 50, sx + 60, sy + 50], fill=(200, 205, 215), outline=WHITE, width=3)
        d.rectangle([sx - 160, sy - 12, sx - 60, sy + 12], fill=(60, 80, 160)); d.rectangle([sx + 60, sy - 12, sx + 160, sy + 12], fill=(60, 80, 160))
        d.rounded_rectangle([sx - 30, sy - 70, sx + 30, sy - 40], 10, fill=(80, 70, 50))
        for k in range(3): d.ellipse([sx - 24 + k * 18, sy - 66, sx - 10 + k * 18, sy - 52], fill=(210, 180, 130))
        if mode == "orbit":
            d.rounded_rectangle([1240, 200, 1860, 560], 40, fill=CARD)
            for k, (s_, c) in enumerate((("2007", GOLD), ("10 DAYS IN OPEN SPACE", WHITE), ("~270 KM UP", TEAL))):
                text(img, s_, 90 if k == 0 else 44, 1550, 280 + (k > 0) * 90 + max(0, k - 1) * 80, c, u=ease((lt - k * 0.6) / 0.4), maxw=580)
        else:
            d.rounded_rectangle([1100, 160, 1860, 760], 40, fill=CARD)
            for k, (s_, ok) in enumerate((("VACUUM", "MOST SURVIVED"), ("COSMIC RAYS", "MOST SURVIVED"), ("SOLAR UV", "SOME SURVIVED"))):
                u = ease((lt - 0.4 - k * 1.1) / 0.4)
                if u <= 0: continue
                y = 260 + k * 170; check(d, 1170, y + 10, 1.3); text(img, s_, 54, 1220, y, WHITE, anchor="lm", u=u, maxw=600); text(img, ok, 34, 1220, y + 58, GOLD if k < 2 else TEAL, w="Bold", anchor="lm", u=u)
        return img
    img = lab(t); d = ImageDraw.Draw(img)
    if mode == "hello":
        tardigrade(d, 900, 520, 1.15, t)
        pill(img, "TARDIGRADE · \"WATER BEAR\"", 44, W / 2, 160, fill=GOLD)
        d = ImageDraw.Draw(img); d.line([(500, 820), (1400, 820)], fill=WHITE, width=5)
        for x in (500, 1400): d.line([(x, 800), (x, 840)], fill=WHITE, width=5)
        text(img, "≤ ~1 MM · 8 LEGS", 50, W / 2, 890, WHITE, u=ease((lt - 1.0) / 0.4))
    else:
        u = ease((lt - 0.6) / 1.6); tardigrade(d, 960, 520, 1.1 if u < 0.98 else 1.6, t, u)
        pill(img, "DRIED OUT → A \"TUN\"", 44, W / 2, 160, fill=TEAL); text(img, "almost totally shut down", 50, W / 2, 860, WHITE, w="Bold", u=ease((lt - 2.0) / 0.4))
    return img

# ---------------- 10: immortal jellyfish ----------------
def jelly(img, cx, cy, s=1.0, t=0.0, alpha=1.0):
    pulse = 1 + 0.07 * math.sin(t * 3); rx, ry = 120 * s * (2 - pulse), 100 * s * pulse
    d = ImageDraw.Draw(img)
    for k in range(12):
        x0 = cx - rx * 0.85 + k * rx * 1.7 / 11; pts = [(x0 + 12 * s * math.sin(t * 2 + k + j * 0.6) * j / 6, cy + j * 34 * s) for j in range(7)]
        d.line(pts, fill=(255, 205, 220), width=max(2, int(3 * s)))
    if s >= 0.5: halo(img, cx, cy - ry * 0.4, rx * 1.1, (255, 150, 190), 90 * alpha)
    m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).chord([cx - rx, cy - ry, cx + rx, cy + ry], 180, 360, fill=int(170 * alpha))
    img.paste(Image.new("RGB", (W, H), (255, 214, 230)), (0, 0), m)
    d = ImageDraw.Draw(img)
    d.arc([cx - rx, cy - ry, cx + rx, cy + ry], 180, 360, fill=(255, 240, 248), width=max(2, int(4 * s))); d.line([(cx - rx, cy), (cx + rx, cy)], fill=(255, 225, 235), width=max(2, int(3 * s)))
    d.ellipse([cx - 40 * s, cy - 62 * s, cx + 40 * s, cy + 4 * s], fill=(220, 50, 60))

def jelly_clip(img, cx, cy, s, t, bg_t):
    """Draw jelly then repaint the lower half of the bell area with background so only a dome remains."""
    jelly(img, cx, cy, s, t)

def polyp(d, x, y, s=1.0, t=0.0, n=1):
    d.ellipse([x - 90 * s, y - 10 * s, x + 90 * s, y + 30 * s], fill=(90, 70, 70))
    for k in range(n):
        bx = x + (k - (n - 1) / 2) * 60 * s; h = 120 * s * (1 - 0.2 * (k % 2)); sw = 10 * s * math.sin(t * 1.5 + k)
        d.line([(bx, y), (bx + sw, y - h)], fill=(240, 180, 190), width=int(10 * s)); d.ellipse([bx + sw - 22 * s, y - h - 30 * s, bx + sw + 22 * s, y - h + 6 * s], fill=(240, 150, 170))
        for j in range(5):
            a = -math.pi / 2 + (j - 2) * 0.5; d.line([(bx + sw, y - h - 26 * s), (bx + sw + 34 * s * math.cos(a), y - h - 26 * s + 34 * s * math.sin(a))], fill=(255, 200, 210), width=max(2, int(4 * s)))

def b_jelly(sc, lt, dur, t):
    mode = sc.get("mode"); img = lab(t); d = ImageDraw.Draw(img)
    if mode == "size":
        fx = 1180; d.rounded_rectangle([fx, 300, 2100, 760], 220, fill=(214, 168, 140)); d.rounded_rectangle([fx + 40, 360, fx + 420, 700], 120, fill=(236, 200, 186), outline=(200, 150, 130), width=4)
        jelly(img, 760, 500, 0.85, t)
        d = ImageDraw.Draw(img); y = 800; d.line([(658, y), (862, y)], fill=GOLD, width=5)
        for x in (658, 862): d.line([(x, y - 16), (x, y + 16)], fill=GOLD, width=5)
        text(img, "~4.5 MM", 60, 760, 870, GOLD); pill(img, "TURRITOPSIS DOHRNII", 44, 760, 170, fill=GOLD)
        text(img, "a little fingernail", 40, fx + 230, 820, WHITE, w="SemiBold")
        return img
    xs = (420, 960, 1500); y = 560
    if mode in ("cycle", "rewind"):
        polyp(d, xs[0], y + 120, 1.0, t, 1); text(img, "POLYP", 46, xs[0], y + 230, TEAL)
        jelly(img, xs[1], y - 40, 0.9, t); text(img, "ADULT", 46, xs[1], y + 230, GOLD)
        d = ImageDraw.Draw(img); arrow(d, xs[0] + 120, y, xs[1] - 150, y, WHITE, 6)
        dead = ease((lt - 1.6) / 0.5) if mode == "cycle" else 1.0
        if dead > 0:
            arrow(d, xs[1] + 150, y, xs[2] - 120, y, (120, 110, 140), 6); text(img, "DIES", 64, xs[2], y, (150, 140, 170), u=dead)
        if mode == "rewind":
            d.line([(xs[2] - 90, y - 50), (xs[2] + 90, y + 50)], fill=CORAL, width=10) if lt > 0.6 else None
            u = ease((lt - 1.2) / 1.4); pts = []
            for k in range(int(60 * u) + 1):
                a = math.pi * (1 - k / 60); pts.append((xs[1] - 270 + 270 * math.cos(a) * -1 + 0, y - 160 - 200 * math.sin(math.pi * k / 60)))
            pts = [(xs[1] - (xs[1] - xs[0]) * k / 60, y - 170 - 190 * math.sin(math.pi * k / 60)) for k in range(int(60 * u) + 1)]
            if len(pts) > 1:
                glow(img, lambda dd, s: dd.line([(x * s, yy_ * s) for x, yy_ in pts], fill=255, width=4), GOLD, 10, 1.2); d = ImageDraw.Draw(img)
                d.line(pts, fill=GOLD, width=10)
                if u > 0.95: x1, y1 = pts[-1]; x0, y0 = pts[-4]; arrow(d, x0, y0, x1 + (x1 - x0), y1 + (y1 - y0) * 2, GOLD, 10, 40)
            text(img, "REWIND", 70, (xs[0] + xs[1]) / 2, y - 420, GOLD, u=ease((lt - 2.4) / 0.4))
        return img
    if mode == "bud":
        polyp(d, 960, 860, 1.2, t, 5)
        for k in range(5):
            p = ((lt * 0.22 + k * 0.2) % 1); x = 760 + k * 100 + 40 * math.sin(t + k); yy_ = 700 - p * 560
            jelly(img, x, yy_, 0.32 + 0.1 * p, t + k, 1.0)
        pill(img, "NEW JELLYFISH · SAME GENES", 42, W / 2, 150, fill=GOLD)
        return img
    # loop
    cx, cy, R = 960, 520, 300
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(90, 80, 130), width=6)
    a = lt * 1.4; pts = [(cx + R * math.cos(a - k * 0.04), cy + R * math.sin(a - k * 0.04)) for k in range(40)]
    glow(img, lambda dd, s: dd.line([(x * s, y * s) for x, y in pts], fill=255, width=4), GOLD, 10, 1.2); d = ImageDraw.Draw(img)
    d.line(pts, fill=GOLD, width=12)
    polyp(d, cx - R, cy + 60, 0.7, t, 1); jelly(img, cx + R, cy - 20, 0.55, t)
    text(img, "∞", 220, cx, cy, GOLD); d = ImageDraw.Draw(img)
    text(img, "AGAIN AND AGAIN", 54, cx, cy + R + 80, WHITE, w="Black", u=ease((lt - 0.5) / 0.4))
    pill(img, "MAY NEVER DIE OF OLD AGE", 42, W / 2, 140, fill=TEAL, u=ease((lt - 3.5) / 0.4))
    return img

def b_outro(sc, lt, dur, t):
    img = lab(t); d = ImageDraw.Draw(img)
    text(img, sc.get("q", "Which one sounded the MOST fake?"), 74, W / 2, 300, WHITE)
    click = sc.get("click_at", 1.6); on = ease((lt - click) / 0.25); cx, cy, w_, h_ = W / 2, 560, 300, 130
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=GOLD if on > 0.5 else (40, 30, 70), outline=WHITE, width=6)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; d.ellipse([kx - h_ / 2 + 16, cy - h_ / 2 + 16, kx + h_ / 2 - 16, cy + h_ / 2 - 16], fill=WHITE)
    text(img, "FAKE", 60, cx - w_ / 2 - 110, cy, WHITE if on < 0.5 else DIM); text(img, "TRUE", 60, cx + w_ / 2 + 110, cy, GOLD if on >= 0.5 else DIM)
    pill(img, "SUBSCRIBE · NEW DEEP DIVE EVERY TUE & FRI", 40, W / 2, 780, fill=CORAL, ink=WHITE, u=ease((lt - click - 0.4) / 0.4))
    return img

BEATS = dict(cold=b_cold, chapter=b_chapter, text=b_text, counter=b_counter, outro=b_outro, falcon=b_falcon, octo=b_octo, beetle=b_beetle,
             eel=b_eel, axo=b_axo, bomb=b_bomb, mantis=b_mantis, frog=b_frog, tard=b_tard, jelly=b_jelly)
NOBLOOM = ()

# ---------------- narration & score ----------------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.42, tail=1.5)
n = len(voice); tt = np.arange(n) / SR; music = np.zeros(n, np.float32)
pads = [[130.81, 196.0, 261.63, 329.63], [110.0, 164.81, 220.0, 277.18], [116.54, 174.61, 233.08, 293.66], [98.0, 146.83, 196.0, 246.94]]
seg = 6.0
for i in range(int(total / seg) + 1):
    a, b = int(i * seg * SR), min(int((i + 1.4) * seg * SR), n)
    if a >= n: break
    lt = tt[a:b] - i * seg; env = np.clip(lt / 2.5, 0, 1) * np.clip((seg * 1.4 - lt) / 2.5, 0, 1)
    for f in pads[i % 4]: music[a:b] += (np.sin(2 * np.pi * f * lt) + 0.3 * np.sin(2 * np.pi * f * 1.004 * lt)) * env * 0.028
beat = np.zeros(n, np.float32)                                                       # light plucked pulse under the pad
for k in range(int(total / 0.75)):
    f = (261.63, 392.0, 329.63, 392.0)[k % 4] * (2 if k % 8 >= 4 else 1)
    place(beat, k * 0.75, tone(f, 0.5, decay=9, harm=(1, 2)), 0.016)
music += beat
for k in range(int(total * 0.6)):
    place(music, random.uniform(0, total), tone(random.choice([784, 1046.5, 1174.66, 1568]), 2.0, decay=1.8, harm=(1, 2)), 0.008)
hook_hit(music, 0.35)
for ln in spec["lines"]:
    if ln["scene"]["type"] == "chapter": place(music, ln["_s"], tone(55, 1.2, decay=3, harm=(1, 2)), 0.25); whoosh(music, ln["_s"], 0.18)
for ln in spec["lines"][1:]: whoosh(music, ln["_s"], 0.06)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.35)

cur_ch = 0
for ln in spec["lines"]:
    if ln["scene"]["type"] == "chapter": cur_ch = ln["scene"]["ch"]
    ln["_ch"] = cur_ch
NCH = max(ln["_ch"] for ln in spec["lines"])
def _ts(x): x = int(x); return f"{x // 60}:{x % 60:02d}"
_chap = ["0:00 Intro"] + [f"{_ts(ln['_s'])} {ln['scene']['ch']}. {ln['scene']['title'].title()}" for ln in spec["lines"] if ln["scene"]["type"] == "chapter"]
_rc = [ln["_s"] for ln in spec["lines"] if ln["scene"]["type"] == "cold" and "RECAP" in " ".join(ln["scene"].get("lines", []))]
if _rc: _chap.append(f"{_ts(_rc[0])} Recap")
open(work + "_chapters.txt", "w").write("\n".join(_chap) + "\n")

groups = caption_groups(words, 6)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 46
    while d.textlength(" ".join(ws), font=F(size, "Bold")) > W - 400 and size > 30: size -= 2
    f = F(size, "Bold"); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 975
    d.rounded_rectangle([x - 28, y - 14, x + tw + 28, y + size + 18], 24, fill=INK)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=GOLD if on else WHITE); x += d.textlength(w + " ", font=f)

def frame(t):
    ln = core.active_line(spec, t, lead=0.05) or spec["lines"][0]
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]; sc = ln["scene"]
    img = BEATS[sc["type"]](sc, lt, dur, t)
    if sc["type"] not in NOBLOOM: img = bloom(img, 0.45)
    d = ImageDraw.Draw(img)
    if ln["_ch"]: d.text((W - 60, 50), f"{ln['_ch']:02d} / {NCH:02d}", font=F(34, "Bold"), fill=GOLD, anchor="ra")
    d.rounded_rectangle([44, 40, 330, 92], 22, fill=INK); d.text((62, 48), "SOUNDS FAKE  ?!", font=F(30, "Black"), fill=(220, 235, 240))
    caption(img, t)
    d.rectangle([0, H - 6, int(W * t / total), H], fill=GOLD)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","):
            Image.frombytes("RGB", (W, H), frame(float(tt_))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s")
    else:
        tmp = out_path[:-4] + ".part.mp4"
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                               "-i", "-", "-i", work + "_audio.wav", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p",
                               "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
        for fi in range(int(total * FPS)): ff.stdin.write(frame(fi / FPS))
        ff.stdin.close()
        if ff.wait() == 0: os.replace(tmp, out_path); print(f"done {total:.1f}s")
        else: raise SystemExit("ffmpeg failed")
