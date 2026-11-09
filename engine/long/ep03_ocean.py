"""LONG-FORM (16:9, 1920x1080) — 'Sounds Fake: Deep Dive' ep03: THE DEEP OCEAN.
Deep-sea look: blue-to-black depth gradient, faint light rays, drifting marine snow, bioluminescent specks,
glowing type, chapter cards, lower-third captions. Based on engine/long/ep02_body.py.
Usage: python3 engine/long/ep03_ocean.py spec.json out.mp4 [t1,t2,... preview]
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
GOLD, TEAL, WHITE, DIM, CORAL, BLUE = (255, 200, 90), (80, 220, 240), (238, 246, 250), (120, 150, 175), (255, 112, 100), (90, 160, 255)
INK = (8, 18, 26)

# ---------------- background: deep-ocean gradient + faint light rays + drifting marine snow + biolum specks ----------------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_v = (yy / H)
vig = np.clip(1 - (((xx - W / 2) / (W * 0.8)) ** 2 + ((yy - H / 2) / (H * 0.95)) ** 2), 0, 1) ** 0.7
BG = (np.array([1, 5, 14], np.float32) + ((1 - _v) ** 1.6)[..., None] * np.array([6, 42, 78], np.float32)) * (0.55 + 0.45 * vig[..., None])
rays = np.zeros((H, W), np.float32)
for k, (x0, wd) in enumerate(((420, 70), (760, 40), (1180, 90), (1520, 50))):
    xc = x0 + (yy * 0.35)
    rays += np.exp(-((xx - xc) / wd) ** 2) * np.clip(1 - yy / (H * 0.75), 0, 1) ** 2 * 7
BG += rays[..., None] * np.array([0.4, 0.9, 1.0], np.float32)
BG_IMG = Image.fromarray(np.clip(BG, 0, 255).astype(np.uint8))
DARK_IMG = Image.fromarray(np.clip(BG * 0.3, 0, 255).astype(np.uint8))
SNOW = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(6, 22), rng.uniform(0.8, 2.6), rng.uniform(0, 6.3), int(rng.uniform(50, 120))) for _ in range(150)]
SPECK = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0, 6.3), rng.uniform(0.3, 0.9)) for _ in range(26)]

def lab(t, cells=True, dark=False):
    img = (DARK_IMG if dark else BG_IMG).copy()
    if cells:
        d = ImageDraw.Draw(img)
        for x, y, vy, r, ph, c in SNOW:
            px = (x + 12 * math.sin(t * 0.3 + ph)) % W; py = (y + vy * t) % (H + 20) - 10
            d.ellipse([px - r, py - r, px + r, py + r], fill=(int(c * 0.7), int(c * 0.85), c))
        for x, y, ph, sp in SPECK:
            f = max(0.0, math.sin(t * sp * 2 + ph)) ** 6
            if f > 0.05:
                r = 2 + 3 * f; px = (x + 6 * t) % W
                d.ellipse([px - r, y - r, px + r, y + r], fill=(int(60 + 120 * f), int(140 + 110 * f), 255))
    return img

def bloom(img, k=0.5):
    a = np.asarray(img).astype(np.float32)
    s = Image.fromarray(np.clip((a - 150) * 1.5, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    b = np.asarray(s.filter(ImageFilter.GaussianBlur(8)).resize((W, H), Image.BILINEAR)).astype(np.float32)
    return Image.fromarray(np.clip(a + b * k, 0, 255).astype(np.uint8))

def halo(img, cx, cy, r, col, strength=160):
    g = Image.new("L", (W, H), 0); ImageDraw.Draw(g).ellipse([cx - r, cy - r, cx + r, cy + r], fill=int(max(0, min(255, strength))))
    img.paste(Image.new("RGB", (W, H), col), (0, 0), g.filter(ImageFilter.GaussianBlur(r * 0.5)))

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

# ---------------- generic human figure (simple rounded shapes, no likeness) ----------------
def figure(d, cx, foot, h, fill, stretch=1.0, arms="down"):
    """Draw a simple standing figure of height h (px) with feet at y=foot. stretch scales the torso only."""
    s = h / 600.0; tor = 200 * s * stretch; leg = 270 * s; head = 52 * s
    hip = foot - leg; sh = hip - tor; hy = sh - 18 * s - head
    lw = int(46 * s)
    for dx in (-30, 30): d.line([(cx + dx * s * 0.8, hip), (cx + dx * s * 1.1, foot - lw / 2)], fill=fill, width=lw, joint="curve")
    for dx in (-30, 30): d.ellipse([cx + dx * s * 1.1 - lw / 2, foot - lw, cx + dx * s * 1.1 + lw / 2, foot], fill=fill)
    d.rounded_rectangle([cx - 66 * s, sh, cx + 66 * s, hip + 24 * s], int(40 * s), fill=fill)
    aw = int(36 * s)
    for sx in (-1, 1):
        x0 = cx + sx * 74 * s
        if arms == "up": pts = [(x0, sh + 20 * s), (x0 + sx * 70 * s, sh - 120 * s)]
        elif arms == "out": pts = [(x0, sh + 20 * s), (x0 + sx * 150 * s, sh + 60 * s)]
        else: pts = [(x0, sh + 20 * s), (x0 + sx * 18 * s, sh + 220 * s)]
        d.line(pts, fill=fill, width=aw)
        for p in pts: d.ellipse([p[0] - aw / 2, p[1] - aw / 2, p[0] + aw / 2, p[1] + aw / 2], fill=fill)
    d.rounded_rectangle([cx - 18 * s, sh - 26 * s, cx + 18 * s, sh + 8 * s], int(10 * s), fill=fill)
    d.ellipse([cx - head, hy - head, cx + head, hy + head], fill=fill)
    return hy - head   # top of head

# ---------------- beats ----------------
def b_cold(sc, lt, dur, t):
    img = lab(t); halo(img, W / 2, H / 2, 300, (30, 120, 130), 80)
    for i, s in enumerate(sc["lines"]):
        text(img, s, sc.get("size", 120), W / 2, 380 + i * sc.get("size", 120) * 1.15, GOLD if str(i) in sc.get("accent", {}) else WHITE, u=1.0 if i == 0 else ease((lt - i * 0.5) / 0.4))
    if "sub" in sc: pill(img, sc["sub"], 40, W / 2, 760, fill=TEAL, u=ease((lt - 0.8) / 0.4))
    return img

def b_chapter(sc, lt, dur, t):
    img = lab(t); halo(img, W / 2, 430, 260, (20, 110, 120), 90)
    u = back(lt / 0.45)
    text(img, f"{sc['ch']:02d}", 330, W / 2, 420, GOLD, u=min(1, u))
    text(img, sc["title"], 84, W / 2, 660, WHITE, u=ease((lt - 0.3) / 0.4))
    if "sub" in sc: text(img, sc["sub"], 40, W / 2, 750, TEAL, w="SemiBold", u=ease((lt - 0.6) / 0.4))
    return img

def b_text(sc, lt, dur, t):
    img = lab(t)
    for i, s in enumerate(sc["lines"]):
        text(img, s, sc.get("size", 96), sc.get("x", W / 2), sc.get("y", 420) + i * sc.get("size", 96) * 1.2, GOLD if str(i) in sc.get("accent", {}) else WHITE,
             anchor=sc.get("anchor", "mm"), u=ease((lt - i * 0.35) / 0.4), maxw=sc.get("maxw", W - 200))
    return img

def b_counter(sc, lt, dur, t):
    img = lab(t); halo(img, W / 2, 450, 280, (20, 100, 110), 70)
    v = sc["from"] + (sc["to"] - sc["from"]) * eout((lt - 0.2) / max(0.6, sc.get("secs", 2.0)))
    text(img, sc.get("prefix", "") + fmtnum(v, sc.get("fmt", "int")) + sc.get("suffix", ""), sc.get("size", 210), W / 2, 450, GOLD, u=ease(lt / 0.3))
    text(img, sc["label"], 56, W / 2, 640, WHITE, w="Bold", u=ease((lt - 0.3) / 0.4))
    return img

# ---------------- shared deep-sea helpers ----------------
CYAN = (80, 230, 255); ROCK = (34, 32, 40); ROCK_EDGE = (70, 92, 115); BONE = (225, 214, 188); RED = (235, 60, 60)

def glow(img, draw_fn, col=CYAN, blur=10, gain=1.0):
    """Cheap glow: draw shapes on a quarter-res mask (draw_fn(d, s) with s=0.25), blur, upscale, tint-paste."""
    m = Image.new("L", (W // 4, H // 4), 0); draw_fn(ImageDraw.Draw(m), 0.25)
    m = m.filter(ImageFilter.GaussianBlur(max(1, blur / 4))).resize((W, H), Image.BILINEAR)
    if gain != 1.0: m = m.point(lambda v: int(min(255, v * gain)))
    img.paste(Image.new("RGB", (W, H), col), (0, 0), m)

def shape_pts(shape, cx, cy, L, flip=False, t=0.0, wob=0.0):
    out = []
    for x, y in shape:
        xx_ = -x if flip else x
        y2 = y + wob * math.sin(t * 3.0 - x * 6) * max(0.0, 0.5 - x)       # tail wobbles more
        out.append((cx + xx_ * L, cy + y2 * L))
    return out

SHARK = [(0.5, 0.0), (0.46, -0.06), (0.36, -0.1), (0.15, -0.125), (0.04, -0.13), (0.0, -0.155), (-0.05, -0.125), (-0.2, -0.1), (-0.24, -0.13), (-0.29, -0.09),
         (-0.4, -0.045), (-0.5, -0.15), (-0.535, -0.13), (-0.49, -0.01), (-0.53, 0.08), (-0.5, 0.085), (-0.41, 0.035), (-0.28, 0.065), (-0.2, 0.09), (-0.16, 0.075),
         (0.1, 0.1), (0.14, 0.15), (0.2, 0.155), (0.22, 0.1), (0.4, 0.07), (0.48, 0.035)]
WHALE = [(0.5, -0.06), (0.48, -0.13), (0.3, -0.15), (0.05, -0.13), (-0.2, -0.08), (-0.38, -0.035), (-0.47, -0.13), (-0.53, -0.13), (-0.45, 0.0), (-0.53, 0.13),
         (-0.47, 0.13), (-0.38, 0.035), (-0.18, 0.08), (0.12, 0.12), (0.38, 0.1), (0.5, 0.05)]

def seafloor(d, y0, amp=18, col=ROCK, seed=1, x0=0, x1=W):
    r = random.Random(seed); pts = [(x0, H)]
    for x in range(int(x0), int(x1) + 41, 40): pts.append((x, y0 + amp * math.sin(x * 0.006 + seed) + r.uniform(-amp * 0.4, amp * 0.4)))
    pts.append((x1, H)); d.polygon(pts, fill=col); d.line(pts[1:-1], fill=ROCK_EDGE, width=4)

def arrow(d, x0, y0, x1, y1, col=WHITE, w=6, head=22):
    d.line([(x0, y0), (x1, y1)], fill=col, width=w); a = math.atan2(y1 - y0, x1 - x0)
    d.polygon([(x1, y1), (x1 - head * math.cos(a - 0.45), y1 - head * math.sin(a - 0.45)), (x1 - head * math.cos(a + 0.45), y1 - head * math.sin(a + 0.45))], fill=col)

def dashed(d, x0, y0, x1, y1, col=DIM, w=4, dash=18):
    n = int(math.hypot(x1 - x0, y1 - y0) / dash)
    for k in range(0, n, 2):
        a, b = k / n, min(1, (k + 1) / n); d.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)], fill=col, width=w)

# ---------------- hook / 2: trench + Everest ----------------
TS, TY0 = 67.0, 170          # px per km, sea level y
def trench_floor_y(x):
    if x < 980 or x > 1600: return 560 + 14 * math.sin(x * 0.01)
    if 1180 <= x <= 1400: return TY0 + 10.935 * TS
    if x < 1180: u = (x - 980) / 200
    else: u = (1600 - x) / 200
    return 560 + (TY0 + 10.935 * TS - 560) * ease(u)

def everest(d, cx, base, dy=0):
    s = 8.848 * TS / 595.0
    P = [(-260, 0), (-140, -266), (-90, -306), (-40, -486), (0, -595), (40, -506), (80, -436), (130, -346), (260, 0)]
    pts = [(cx + x, base + y * s + dy) for x, y in P]
    d.polygon(pts, fill=(118, 126, 142), outline=(190, 200, 215))
    snow = [(cx - 40, base - 486 * s + dy), (cx, base - 595 * s + dy), (cx + 40, base - 506 * s + dy), (cx + 60, base - 470 * s + dy), (cx + 20, base - 480 * s + dy),
            (cx - 10, base - 455 * s + dy), (cx - 30, base - 470 * s + dy)]
    d.polygon(snow, fill=(240, 246, 252))
    d.line([(cx - 90, base - 306 * s + dy), (cx - 20, base - 200 * s + dy), (cx + 30, base - 120 * s + dy)], fill=(95, 102, 118), width=5)
    return base - 595 * s + dy

def b_trench(sc, lt, dur, t):
    mode = sc.get("mode", "hook"); img = lab(t); d = ImageDraw.Draw(img)
    d.rectangle([720, 90, 1860, TY0], fill=(10, 34, 60))                       # sky strip
    for k in range(30): d.rectangle([720, TY0 + k * 31, 1860, TY0 + (k + 1) * 31], fill=(int(8 - 6 * k / 30), int(44 - 34 * k / 30), int(84 - 60 * k / 30)))
    pts = [(720, H)] + [(x, trench_floor_y(x)) for x in range(720, 1861, 10)] + [(1860, H)]
    d.polygon(pts, fill=ROCK); d.line(pts[1:-1], fill=ROCK_EDGE, width=4)
    wv = [(x, TY0 + 4 * math.sin(x * 0.03 + t * 2)) for x in range(720, 1861, 8)]; d.line(wv, fill=CYAN, width=4)
    d.text((740, TY0 - 46), "SEA LEVEL", font=F(26, "Bold"), fill=CYAN)
    for km in range(0, 11, 2):
        y = TY0 + km * TS; d.line([(722, y), (742, y)], fill=DIM, width=3)
        if km: d.text((750, y), f"{km} km", font=F(24, "SemiBold"), fill=DIM, anchor="lm")
    cx, base = 1290, TY0 + 10.935 * TS
    if mode == "depth":
        p = ease((lt - 0.3) / max(1.0, dur - 1.0)); y = TY0 + p * (base - TY0 - 14)
        halo(img, cx, y, 40, (120, 230, 255), 220); d = ImageDraw.Draw(img); d.ellipse([cx - 12, y - 12, cx + 12, y + 12], fill=WHITE)
        d.line([(cx + 24, y), (cx + 80, y)], fill=GOLD, width=3); d.text((cx + 92, y), f"{int(p * 10935):,} m", font=F(40, "Black"), fill=GOLD, anchor="lm")
        text(img, sc.get("label", "CHALLENGER DEEP"), 76, 370, 420, GOLD, maxw=640); text(img, "deepest known spot", 44, 370, 510, WHITE, w="SemiBold", maxw=640)
        pill(img, "MARIANA TRENCH · W. PACIFIC", 32, 370, 620, fill=TEAL, u=ease((lt - 0.6) / 0.4))
        return img
    dy = 0.0 if mode == "hook" else -760 * (1 - eout((lt - 0.3) / 1.8))
    peak = everest(d, cx, base, dy)
    show = 1.0 if mode == "hook" else ease((lt - 2.2) / 0.5)
    if show > 0:
        bx = 1600; d.line([(bx, TY0 + 8), (bx, peak)], fill=GOLD, width=5)
        for yy_ in (TY0 + 8, peak): d.line([(bx - 18, yy_), (bx + 18, yy_)], fill=GOLD, width=5)
        dashed(d, cx + 30, peak, bx - 20, peak, GOLD, 3)
        text(img, "2+ KM", 52, bx + 120, (TY0 + peak) / 2 - 20, GOLD, u=show); text(img, "OF WATER", 30, bx + 120, (TY0 + peak) / 2 + 26, WHITE, w="Bold", u=show)
    if mode == "hook":
        for i, s in enumerate(sc["lines"]): text(img, s, 100 if i == 0 else 150, 370, 400 + i * 150, GOLD if i == 1 else WHITE, maxw=640)
        pill(img, "IN THE DEEPEST OCEAN", 34, 370, 700, fill=TEAL)
    else:
        text(img, "EVEREST", 64, 370, 380, WHITE, maxw=640); text(img, "8,848 m TALL", 52, 370, 455, DIM, w="Bold", maxw=640)
        text(img, "THE TRENCH", 64, 370, 580, GOLD, maxw=640); text(img, "~10,935 m DEEP", 52, 370, 655, GOLD, w="Bold", maxw=640)
    return img

def car(d, x, y, col):
    d.rounded_rectangle([x - 150, y - 60, x + 150, y + 10], 22, fill=col); d.rounded_rectangle([x - 80, y - 110, x + 70, y - 50], 24, fill=col)
    d.rounded_rectangle([x - 66, y - 100, x - 10, y - 60], 8, fill=(150, 200, 230)); d.rounded_rectangle([x, y - 100, x + 56, y - 60], 8, fill=(150, 200, 230))
    for wx in (x - 95, x + 95): d.ellipse([wx - 30, y - 18, wx + 30, y + 42], fill=(25, 25, 30)); d.ellipse([wx - 12, y, wx + 12, y + 24], fill=(150, 150, 160))

def b_pressure(sc, lt, dur, t):
    img = lab(t); d = ImageDraw.Draw(img); sx, sy, ss = 560, 870, 140
    d.rectangle([sx - ss / 2, sy - ss, sx + ss / 2, sy], fill=(236, 226, 200))
    for k in range(8):
        for (px, py) in ((sx - ss / 2 + k * ss / 7, sy - ss), (sx - ss / 2 + k * ss / 7, sy), (sx - ss / 2, sy - ss + k * ss / 7), (sx + ss / 2, sy - ss + k * ss / 7)):
            d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=(10, 30, 50))
    d.rectangle([sx - ss / 2 + 18, sy - ss + 18, sx + ss / 2 - 18, sy - 18], fill=(70, 130, 170))
    cols = [CORAL, (90, 160, 255), GOLD, (120, 220, 170), (200, 140, 255)]
    for k in range(5):
        u = eout((lt - 0.2 - k * 0.45) / 0.5)
        if u <= 0: continue
        y = sy - ss - 12 - k * 128 - (1 - u) * 300; car(d, sx + (k % 2) * 16 - 8, y, cols[k])
    text(img, "8+ TONS", 150, 1350, 380, GOLD, u=ease(lt / 0.4)); text(img, "ON EVERY SQUARE INCH", 52, 1350, 500, WHITE, u=ease((lt - 0.3) / 0.4))
    pill(img, "> 1,000× SURFACE PRESSURE", 42, 1350, 640, fill=TEAL, u=ease((lt - 2.0) / 0.4))
    return img

# ---------------- 1: maps ----------------
def b_map(sc, lt, dur, t):
    mode = sc.get("mode"); img = lab(t); d = ImageDraw.Draw(img)
    if mode == "mars":
        cx, cy, R = 560, 500, 270; u = ease((lt - 0.2) / 1.5)
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(190, 92, 52))
        r = random.Random(4)
        for _ in range(18):
            a, rr, s = r.uniform(0, 6.28), R * math.sqrt(r.uniform(0, 0.85)), r.uniform(10, 34)
            x, y = cx + rr * math.cos(a), cy + rr * math.sin(a); d.ellipse([x - s, y - s, x + s, y + s], fill=(160, 74, 42), outline=(215, 120, 80), width=2)
        for k in range(1, 8):                                          # map grid sweeps in
            yk = cy - R + k * R / 4
            if (k / 8) <= u:
                hw = math.sqrt(max(0, R * R - (yk - cy) ** 2)); d.line([(cx - hw, yk), (cx + hw, yk)], fill=(255, 220, 170), width=2)
            ex = R * math.cos(k / 8 * math.pi)
            if (k / 8) <= u: d.ellipse([cx - abs(ex), cy - R, cx + abs(ex), cy + R], outline=(255, 220, 170), width=2)
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(255, 200, 150), width=4)
        text(img, "MARS", 64, cx, 840, CORAL); 
        cx2 = 1360; d.ellipse([cx2 - R, cy - R, cx2 + R, cy + R], fill=(12, 48, 90), outline=(80, 160, 220), width=4)
        r = random.Random(9)
        for _ in range(9):
            a, rr = r.uniform(0, 6.28), R * 0.8 * math.sqrt(r.uniform(0, 1)); x, y = cx2 + rr * math.cos(a), cy + rr * math.sin(a); ang = r.uniform(0, 3.14)
            d.line([(x - 50 * math.cos(ang), y - 50 * math.sin(ang)), (x + 50 * math.cos(ang), y + 50 * math.sin(ang))], fill=(60, 200, 210), width=9)
        text(img, "?", 200, cx2, cy, (120, 170, 210), u=ease((lt - 0.8) / 0.4))
        text(img, "OUR SEAFLOOR", 64, cx2, 840, TEAL)
        pill(img, "MORE DETAILED MAPS", 36, cx, 180, fill=CORAL, ink=WHITE, u=ease((lt - 1.2) / 0.4))
    elif mode == "light":
        d.rectangle([0, 90, W, 220], fill=(40, 100, 150)); halo(img, 1500, 150, 60, (255, 230, 150), 255); d = ImageDraw.Draw(img)
        d.ellipse([1460, 110, 1540, 190], fill=(255, 236, 170))
        for k in range(7):
            x = 500 + k * 160; L = 260 * ease((lt - 0.2 - k * 0.08) / 0.8)
            glow(img, lambda dd, s, x=x, L=L: dd.polygon([((x - 30) * s, 222 * s), ((x + 30) * s, 222 * s), ((x + 10) * s, (222 + L) * s), ((x - 10) * s, (222 + L) * s)], fill=200), (255, 225, 140), 18, 0.8)
        d = ImageDraw.Draw(img)
        for k in range(40): d.rectangle([0, 420 + k * 12, W, 432 + k * 12], fill=(int(2 * (1 - k / 40)) + 1, int(10 * (1 - k / 40)) + 3, int(20 * (1 - k / 40)) + 8))
        d.rectangle([0, 900, W, H], fill=(2, 4, 9))
        seafloor(d, 860, 20, (16, 18, 26), 3)
        text(img, "SUNLIGHT FADES OUT", 72, W / 2, 560, WHITE, u=ease((lt - 0.5) / 0.4)); text(img, "in the first few hundred feet", 44, W / 2, 650, DIM, w="SemiBold", u=ease((lt - 0.8) / 0.4))
        text(img, "?   ?   ?", 70, W / 2, 790, (90, 120, 150), u=ease((lt - 1.4) / 0.4))
    elif mode == "sonar":
        sy, fy = 230, 820; p = ease(lt / max(1.0, dur)); shx = 260 + p * 1400
        prof = lambda x: fy + 50 * math.sin(x * 0.004) + 30 * math.sin(x * 0.013 + 1) - 90 * math.exp(-((x - 1100) / 120) ** 2) - 140 * math.exp(-((x - 600) / 90) ** 2)
        pts = [(0, H)] + [(x, prof(x)) for x in range(0, W + 1, 12)] + [(W, H)]
        d.polygon(pts, fill=(14, 18, 26))
        mapped = [(x, prof(x)) for x in range(0, int(shx) + 1, 12) if x >= 240]
        unk = [(x, prof(x)) for x in range(int(shx), W + 1, 12)]
        if len(unk) > 1:
            for k in range(0, len(unk) - 1, 2): d.line([unk[k], unk[k + 1]], fill=(60, 80, 100), width=3)
        fan = [(shx, sy + 20), (shx - 120, prof(shx - 120)), (shx + 120, prof(shx + 120))]
        glow(img, lambda dd, s: dd.polygon([(x * s, y * s) for x, y in fan], fill=110), CYAN, 10, 1.0); d = ImageDraw.Draw(img)
        for k in range(3):
            rr = ((t * 1.2 + k / 3) % 1) * (fy - sy); d.arc([shx - rr * 0.35, sy + 20 - rr, shx + rr * 0.35, sy + 20 + rr], 60, 120, fill=CYAN, width=3)
        if len(mapped) > 1:
            d.line(mapped, fill=GOLD, width=8)
            for x, y in mapped[::3]: d.line([(x, y), (x, y + 30)], fill=(150, 110, 50), width=6)
        d.line([(0, sy), (W, sy)], fill=CYAN, width=3)
        d.polygon([(shx - 90, sy - 8), (shx + 100, sy - 8), (shx + 70, sy + 22), (shx - 70, sy + 22)], fill=(220, 230, 240)); d.rectangle([shx - 30, sy - 46, shx + 30, sy - 8], fill=(220, 230, 240))
        pill(img, "ONE STRIP AT A TIME", 40, W / 2, 150)
    else:   # percent grid
        order = list(range(100)); random.Random(5).shuffle(order); on = set(order[:27]); u = (lt - 0.2) / 2.2
        lit = int(27 * eout(u)); onl = order[:lit]
        for i in range(100):
            r_, c_ = divmod(i, 10); x, y = 300 + c_ * 64, 190 + r_ * 64
            d.rounded_rectangle([x, y, x + 54, y + 54], 8, fill=GOLD if i in onl else (14, 34, 56), outline=(40, 80, 110), width=2)
        text(img, f"{int(round(27 * eout(u)))}%", 220, 1360, 420, GOLD)
        text(img, "OF THE SEAFLOOR", 56, 1360, 580, WHITE); text(img, "mapped to modern standards", 40, 1360, 650, DIM, w="SemiBold")
        pill(img, "AS OF 2025 · 27.3%", 34, 1360, 760, fill=TEAL, u=ease((lt - 1.2) / 0.4))
    return img

# ---------------- 3: nightly migration ----------------
MIG = [(random.Random(k).uniform(260, W - 80), random.Random(k + 100).uniform(600, 860), random.Random(k + 200).uniform(280, 470), random.Random(k + 300).randint(0, 2), random.Random(k + 400).uniform(0, 6.3)) for k in range(130)]
def critter(d, x, y, kind, col, t, ph, s=1.0):
    if kind == 0:   # fish
        d.ellipse([x - 16 * s, y - 6 * s, x + 16 * s, y + 6 * s], fill=col); d.polygon([(x - 14 * s, y), (x - 26 * s, y - 8 * s), (x - 26 * s, y + 8 * s)], fill=col)
    elif kind == 1: # jelly
        d.pieslice([x - 14 * s, y - 12 * s, x + 14 * s, y + 12 * s], 180, 360, fill=col)
        for k in range(3): d.line([(x - 8 * s + k * 8 * s, y), (x - 8 * s + k * 8 * s + 4 * math.sin(t * 3 + ph + k), y + 20 * s)], fill=col, width=2)
    else:           # shrimp
        d.arc([x - 12 * s, y - 10 * s, x + 12 * s, y + 10 * s], 200, 340, fill=col, width=max(2, int(6 * s)))

def b_migrate(sc, lt, dur, t):
    mode = sc.get("mode"); img = lab(t, cells=False, dark=True); d = ImageDraw.Draw(img); surf = 260
    span = max(1.5, dur * 0.85)
    if mode == "day": p, night = 0.0, 0.0
    elif mode == "night": p, night = eout((lt - 0.3) / span), min(1.0, 0.3 + lt / 1.0)
    else: p, night = 1 - eout((lt - 0.3) / span), max(0.0, 1 - lt / span)
    sky = tuple(int(a * (1 - night) + b * night) for a, b in zip((60, 130, 190), (6, 12, 30)))
    d.rectangle([0, 90, W, surf], fill=sky)
    for k in range(40):
        f = k / 40; m_ = (1 - f) * (1 - night * 0.8); c = (int(4 + 24 * m_), int(14 + 70 * m_), int(30 + 90 * m_))
        d.rectangle([0, surf + k * 17, W, surf + (k + 1) * 17], fill=c)
    d.rectangle([0, 420, 170, 860], fill=(20, 30, 50)); d.text((85, 640), "TWILIGHT\nZONE", font=F(26, "Bold"), fill=DIM, anchor="mm", align="center")
    for yy_, lab_ in ((surf + 10, "SURFACE"), (420, "200 m"), (860, "1,000 m")): d.text((30, yy_), lab_, font=F(26, "Bold"), fill=DIM, anchor="lm"); d.line([(170, yy_), (210, yy_)], fill=DIM, width=3)
    if night < 0.5: halo(img, 1640, 170, 50, (255, 230, 150), 255 * (1 - night * 2)); d = ImageDraw.Draw(img); d.ellipse([1610, 140, 1670, 200], fill=(255, 236, 170))
    else:
        d.ellipse([1610, 140, 1670, 200], fill=(230, 235, 245)); d.ellipse([1630, 132, 1690, 192], fill=sky)
    d.line([(0, surf), (W, surf)], fill=CYAN, width=3)
    for x, yd, ys, kind, ph in MIG:
        y = yd + (ys - yd) * min(1, max(0, p * 1.15 - (yd - 600) / 2600)) + 6 * math.sin(t * 1.5 + ph); xx_ = x + 10 * math.sin(t * 0.7 + ph)
        critter(d, xx_, y, kind, (110, 210, 240), t, ph)
        if p > 0.05 and p < 0.95: d.line([(xx_, y + 14), (xx_, y + 40)], fill=(40, 90, 120), width=2)
    lbl = {"day": "DAYTIME · HIDING IN THE DARK", "night": "SUNSET · EVERYONE SWIMS UP", "dawn": "BEFORE SUNRISE · BACK DOWN"}[mode]
    pill(img, lbl, 38, W / 2, 175, fill=GOLD)
    return img

# ---------------- 4: bioluminescence ----------------
GL = [(random.Random(k * 7).uniform(120, W - 120), random.Random(k * 7 + 1).uniform(180, 900), random.Random(k * 7 + 2).randint(0, 2), random.Random(k * 7 + 3).uniform(0, 6.3), random.Random(k * 7 + 4).uniform(0.8, 2.2)) for k in range(46)]
def b_glowers(sc, lt, dur, t):
    mode = sc.get("mode"); img = lab(t, cells=False, dark=True); d = ImageDraw.Draw(img)
    if mode in ("dark", "many"):
        n = 8 if mode == "dark" else len(GL); items = []
        for x, y, kind, ph, s in GL[:n]:
            f = (0.5 + 0.5 * math.sin(t * 1.6 + ph * 3)) ** 2 * min(1.0, lt / 0.8 + (1 if mode == "dark" else 0)); items.append((x + 8 * math.sin(t * 0.5 + ph), y + 6 * math.cos(t * 0.6 + ph), kind, ph, s, f))
        def gdraw(dd, sc_):
            for x, y, kind, ph, s, f in items:
                r = 22 * s * sc_; dd.ellipse([x * sc_ - r, y * sc_ - r, x * sc_ + r, y * sc_ + r], fill=int(220 * f))
        glow(img, gdraw, CYAN, 18, 1.0); d = ImageDraw.Draw(img)
        for x, y, kind, ph, s, f in items:
            col = (int(40 + 150 * f), int(90 + 160 * f), int(130 + 125 * f)); critter(d, x, y, kind, col, t, ph, s * 1.6)
        if mode == "dark":
            d.rounded_rectangle([W / 2 - 560, 380, W / 2 + 560, 620], 40, fill=(2, 6, 12))
            text(img, "NO SUNLIGHT AT ALL", 88, W / 2, 460, WHITE); text(img, "...but not completely dark", 48, W / 2, 560, TEAL, w="SemiBold", u=ease((lt - 1.5) / 0.5))
        else: pill(img, "YEARS OF DEEP-SEA ROBOT VIDEO", 38, W / 2, 150)
    else:
        u = eout((lt - 0.2) / 2.0); order = list(range(100)); random.Random(3).shuffle(order); lit = set(order[:int(76 * u)])
        pos = [(260 + (i % 10) * 72, 200 + (i // 10) * 72) for i in range(100)]
        glow(img, lambda dd, s: [dd.ellipse([(x - 26) * s, (y - 26) * s, (x + 26) * s, (y + 26) * s], fill=230) for i, (x, y) in enumerate(pos) if i in lit], CYAN, 14, 1.0)
        d = ImageDraw.Draw(img)
        for i, (x, y) in enumerate(pos):
            on = i in lit; d.ellipse([x - 18, y - 18, x + 18, y + 18], fill=(200, 250, 255) if on else (30, 42, 56))
        text(img, f"{int(round(76 * u))}%", 230, 1420, 400, GOLD); text(img, "OF OPEN-WATER ANIMALS", 50, 1420, 560, WHITE); text(img, "CAN MAKE LIGHT", 50, 1420, 625, WHITE)
        pill(img, "ON THE SEAFLOOR: ~45%", 36, 1420, 760, fill=TEAL, u=ease((lt - (dur - 2.6)) / 0.4))
    return img

# ---------------- 5: squid eyes ----------------
def eye_draw(d, cx, cy, R, pupil):
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(176, 190, 206), outline=(230, 240, 250), width=max(2, int(R * 0.02)))
    ri = R * 0.78; d.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=(52, 70, 104))
    for k in range(36):
        a = k / 36 * 6.283; d.line([(cx + pupil * math.cos(a), cy + pupil * math.sin(a)), (cx + ri * 0.95 * math.cos(a), cy + ri * 0.95 * math.sin(a))], fill=(80, 104, 140), width=max(1, int(R * 0.012)))
    d.ellipse([cx - pupil, cy - pupil, cx + pupil, cy + pupil], fill=(4, 6, 10))
    hr = pupil * 0.28; d.ellipse([cx - pupil * 0.45 - hr, cy - pupil * 0.45 - hr, cx - pupil * 0.45 + hr, cy - pupil * 0.45 + hr], fill=(240, 248, 255))

def squid(d, x, y, s, col):
    d.polygon([(x + 120 * s, y), (x + 20 * s, y - 34 * s), (x - 20 * s, y - 30 * s), (x - 20 * s, y + 30 * s), (x + 20 * s, y + 34 * s)], fill=col)
    d.polygon([(x + 120 * s, y), (x + 150 * s, y - 30 * s), (x + 150 * s, y + 30 * s)], fill=col)
    for k in range(6): d.line([(x - 20 * s, y - 20 * s + k * 8 * s), (x - 110 * s, y - 40 * s + k * 16 * s)], fill=col, width=max(2, int(7 * s)))
    d.ellipse([x - 16 * s, y - 16 * s, x + 16 * s, y + 16 * s], fill=(176, 190, 206)); d.ellipse([x - 7 * s, y - 7 * s, x + 7 * s, y + 7 * s], fill=(0, 0, 0))

def b_eye(sc, lt, dur, t):
    mode = sc.get("mode"); img = lab(t); d = ImageDraw.Draw(img)
    if mode == "size":
        k = 17.0; g = back(lt / 0.8) if sc.get("grow") else 1.0; R = 13.5 * k * max(0.05, g); cx, cy = 660, 490
        dashed(d, cx - 255, cy + 262, cx + 255, cy + 262, DIM, 3, 14) if False else None
        d.ellipse([cx - 262, cy - 262, cx + 262, cy + 262], outline=(230, 225, 210), width=3) if g >= 0.99 else None
        eye_draw(d, cx, cy, R, 4.5 * k * max(0.05, g))
        if g >= 0.99:
            d.line([(cx - R, cy + R + 40), (cx + R, cy + R + 40)], fill=GOLD, width=4)
            for xx_ in (cx - R, cx + R): d.line([(xx_, cy + R + 26), (xx_, cy + R + 54)], fill=GOLD, width=4)
            text(img, "~27 cm", 52, cx, cy + R + 92, GOLD)
        sx_, sy_ = 1380, 560; eye_draw(d, sx_, sy_, 4.5 * k, 1.6 * k)
        text(img, "SWORDFISH", 44, sx_, sy_ + 120, WHITE); text(img, "~9 cm", 40, sx_, sy_ + 172, DIM, w="Bold")
        pill(img, "BIGGEST EYES OF ANY KNOWN ANIMAL", 38, W / 2, 140)
        if not sc.get("grow"): pill(img, "≈ A DINNER PLATE", 34, 660, 880, fill=TEAL, u=ease((lt - 1.4) / 0.4))
    else:
        img = lab(t, cells=False, dark=True); d = ImageDraw.Draw(img)
        wx = (1260 if sc.get("dist") else 1380) - 120 * ease(lt / max(1.0, dur)); wy, L = 480, 820
        poly = shape_pts(WHALE, wx, wy, L, flip=True, t=t, wob=0.02)
        d.polygon(poly, fill=(10, 18, 26))
        r = random.Random(2); pts = []
        for i in range(len(poly)):
            (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
            for _ in range(int(math.hypot(x1 - x0, y1 - y0) / 10)):
                u_ = r.random(); off = r.gauss(0, 10); pts.append((x0 + (x1 - x0) * u_ + off, y0 + (y1 - y0) * u_ + r.gauss(0, 10), r.uniform(0, 6.3)))
        reveal = 1.0 if sc.get("dist") else ease((lt - 0.4) / 1.5)
        glow(img, lambda dd, s: [dd.ellipse([(x - 6) * s, (y - 6) * s, (x + 6) * s, (y + 6) * s], fill=int(255 * reveal)) for x, y, ph in pts], CYAN, 14, 1.4)
        d = ImageDraw.Draw(img)
        for x, y, ph in pts:
            f = reveal * (0.5 + 0.5 * math.sin(t * 5 + ph)); c = int(255 * f)
            if c > 20: d.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=(c // 2, c, c))
        squid(d, 300, 540, 1.3, (150, 70, 80))
        u2 = ease((lt - 0.6) / 0.6) if sc.get("dist") else 0.0
        if u2 > 0:
            dashed(d, 330, 520, wx - L * 0.5 - 20, 500, GOLD, 4); text(img, "~120 m", 56, (330 + wx - L * 0.5) / 2, 450, GOLD, u=u2)
        pill(img, "THE WHALE LIGHTS UP", 38, W / 2, 150, fill=TEAL)
    return img

# ---------------- 6: brine pools ----------------
def pool_y(x): return 600 + 210 * max(0.0, math.sin(math.pi * (x - 440) / 1040)) ** 0.7 if 440 <= x <= 1480 else 600 + 10 * math.sin(x * 0.01)
BS = 668
MUSSELS = [x for x in range(300, 1640, 22) if not (470 < x < 1450)] + [x for x in range(440, 1481, 20) if abs(pool_y(x) - BS) < 40]
def b_brine(sc, lt, dur, t):
    mode = sc.get("mode"); img = lab(t); d = ImageDraw.Draw(img)
    pts = [(0, H)] + [(x, pool_y(x)) for x in range(0, W + 1, 10)] + [(W, H)]
    d.polygon(pts, fill=ROCK)
    xs = [x for x in range(440, 1481, 6) if pool_y(x) > BS]
    surf = [(x, BS + 5 * math.sin(x * 0.02 + t * 1.8)) for x in xs]
    d.polygon(surf + [(x, pool_y(x)) for x in reversed(xs)], fill=(40, 96, 128))
    for k in range(6):
        yk = BS + 22 + k * 22; seg = [(x, yk + 3 * math.sin(x * 0.03 + t * 2 + k)) for x in xs if pool_y(x) > yk + 6]
        if len(seg) > 1: d.line(seg, fill=(60, 126, 160), width=2)
    glow(img, lambda dd, s: dd.line([(x * s, y * s) for x, y in surf], fill=255, width=2), CYAN, 8, 0.9); d = ImageDraw.Draw(img)
    d.line(surf, fill=(170, 235, 255), width=4); d.line(pts[1:-1], fill=ROCK_EDGE, width=4)
    hl = mode == "mussels"
    for i, x in enumerate(MUSSELS):
        y = pool_y(x) - 8 if not (470 < x < 1450) else BS - 6
        d.ellipse([x - 12, y - 7, x + 12, y + 7], fill=(40, 30, 60) if not hl else (90, 70, 140), outline=(140, 120, 190) if hl else (70, 60, 90), width=2)
    if mode == "sink":
        for k in range(10):
            p = (t * 0.35 + k / 10) % 1; x = 520 + k * 95; y = 260 + p * (BS - 260)
            d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=(60, 140, 180)); arrow(d, x, y + 18, x, y + 50, (120, 200, 230), 3, 12)
        text(img, "TOO SALTY TO MIX", 72, W / 2, 200, WHITE)
    elif mode == "deadly":
        r = random.Random(8)
        for k in range(6):
            x = 640 + k * 120 + r.uniform(-20, 20); y = pool_y(x) - 18
            col = (150, 120, 110); d.ellipse([x - 26, y - 14, x + 26, y + 14], outline=col, width=4)
            for sx in (-1, 1):
                for j in range(3): d.line([(x + sx * 20, y + j * 5 - 4), (x + sx * 44, y + j * 8 + 6)], fill=col, width=3)
        pill(img, "DEADLY FOR MOST ANIMALS", 40, W / 2, 200, fill=CORAL, ink=WHITE); text(img, "more than 1 km down", 40, W / 2, 280, DIM, w="SemiBold")
    elif mode == "mussels":
        for k in range(14):
            p = (t * 0.25 + k / 14) % 1; x = (470 if k % 2 else 1450) + (k * 13 % 50) - 25; y = BS - p * 380
            d.ellipse([x - 7, y - 7, x + 7, y + 7], outline=(150, 220, 240), width=2)
        pill(img, "MUSSELS ON THE SHORE", 40, W / 2, 200, fill=GOLD); text(img, "living off methane", 40, W / 2, 280, WHITE, w="SemiBold")
    else:
        pill(img, "BRINE POOL", 40, W / 2, 200, fill=GOLD); text(img, "a lake on the ocean floor", 48, W / 2, 285, WHITE, w="SemiBold", u=ease((lt - 0.4) / 0.4))
        d = ImageDraw.Draw(img); arrow(d, 1560, 520, 1470, BS - 20, GOLD, 5); d.text((1570, 500), "SHORELINE", font=F(34, "Black"), fill=GOLD, anchor="lm")
    return img

# ---------------- 7/8: vents ----------------
PLUME = [(random.Random(k * 5).uniform(0, 1), random.Random(k * 5 + 1).uniform(-1, 1), random.Random(k * 5 + 2).uniform(16, 40)) for k in range(70)]
def vent_scene(img, t, vx=760, top=420, floor=830):
    d = ImageDraw.Draw(img); seafloor(d, floor, 16, ROCK, 5)
    d.polygon([(vx - 120, floor + 10), (vx - 50, top), (vx + 50, top), (vx + 120, floor + 10)], fill=(46, 42, 46), outline=(90, 80, 80))
    for k in range(5): d.line([(vx - 60 + k * 30, floor), (vx - 40 + k * 22 + 8 * math.sin(k), top + 120 + k * 40)], fill=(200, 90, 40), width=3)
    halo(img, vx, top, 70, (255, 140, 60), 170)
    def pdraw(dd, s):
        for ph, sx, r in PLUME:
            p = (t * 0.22 + ph) % 1; y = top - p * 380; x = vx + sx * (20 + 150 * p) + 20 * math.sin(t + ph * 9); rr = r * (0.6 + 1.6 * p)
            dd.ellipse([(x - rr) * s, (y - rr) * s, (x + rr) * s, (y + rr) * s], fill=int(200 * (1 - p)))
    glow(img, pdraw, (12, 12, 16), 10, 1.2)
    return ImageDraw.Draw(img)

def thermometer(img, x, frac, lt):
    d = ImageDraw.Draw(img); top, bot = 220, 800
    d.rounded_rectangle([x - 34, top - 20, x + 34, bot], 34, fill=(20, 30, 44), outline=WHITE, width=5); d.ellipse([x - 64, bot - 30, x + 64, bot + 98], fill=CORAL, outline=WHITE, width=5)
    yv = bot - (bot - top) * frac; d.rounded_rectangle([x - 18, yv, x + 18, bot + 10], 18, fill=CORAL)
    for val, lab_ in ((100, "100°C · BOILS ON LAND"), (327, "327°C · LEAD MELTS")):
        yy_ = bot - (bot - top) * val / 400; d.line([(x - 50, yy_), (x + 50, yy_)], fill=GOLD, width=4); d.text((x + 70, yy_), lab_, font=F(30, "Bold"), fill=GOLD, anchor="lm")
    return yv

def b_vent(sc, lt, dur, t):
    mode = sc.get("mode"); img = lab(t)
    if mode == "sub":
        d = vent_scene(img, t, 1300, 520, 860); p = eout((lt - 0.2) / max(1.5, dur - 1)); x, y = 760 + 260 * p, 120 + 420 * p
        glow(img, lambda dd, s: dd.polygon([((x + 70) * s, (y + 10) * s), ((x + 520) * s, (y + 260) * s), ((x + 420) * s, (y + 380) * s)], fill=90), (220, 240, 255), 20, 1.0)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([x - 110, y - 50, x + 90, y + 50], 50, fill=(236, 240, 244)); d.rounded_rectangle([x - 40, y - 90, x + 20, y - 40], 14, fill=(236, 240, 244))
        d.ellipse([x + 30, y - 22, x + 74, y + 22], fill=(60, 140, 200), outline=(40, 60, 80), width=5); d.rectangle([x - 140, y - 12, x - 110, y + 12], fill=(200, 90, 50))
        text(img, "1977", 160, 380, 640, GOLD); text(img, "~2.5 KM DOWN", 48, 380, 760, WHITE, w="Bold")
        return img
    d = vent_scene(img, t)
    if mode == "chimney":
        for k in range(4):
            x0 = 300 + k * 40; p = (t * 0.4 + k * 0.25) % 1
            dashed(d, x0, 830, x0 + 200, 1000, (90, 170, 230), 5, 14); d.ellipse([x0 + 200 * p - 8, 830 + 170 * p - 8, x0 + 200 * p + 8, 830 + 170 * p + 8], fill=(120, 200, 255))
        pill(img, "HYDROTHERMAL VENT", 42, 1380, 380, fill=GOLD); text(img, "seawater heated by magma", 44, 1380, 470, WHITE, w="SemiBold", u=ease((lt - 0.4) / 0.4))
    elif mode == "thermo":
        fr = min(1.03, eout((lt - 0.2) / 2.2) * 1.03); thermometer(img, 1380, fr, lt)
        text(img, f"{int(400 * min(fr, 1.0))}°C+" if fr >= 1 else f"{int(400 * fr)}°C", 96, 1060, 300, CORAL)
    else:
        for k in range(5):
            x = 300 + k * 260; off = 20 * ((t * 1.2 + k * 0.3) % 1)
            arrow(d, x, 140 + off, x, 300 + off, (120, 190, 230), 14, 40)
        pill(img, "PRESSURE KEEPS IT LIQUID", 42, 1380, 470, fill=TEAL); text(img, "400°C+ · NO BOILING", 52, 1380, 570, CORAL)
    return img

# ---------------- 8: tube worms ----------------
WORMS = [(-150, 0.78, 0.2), (-90, 1.0, 1.1), (-30, 0.86, 2.3), (30, 0.95, 0.7), (90, 0.7, 3.1), (150, 0.9, 1.8), (-200, 0.6, 2.7)]
def tubeworm(d, x, base, h, t, ph):
    sw = 14 * math.sin(t * 1.4 + ph); top = (x + sw, base - h)
    d.line([(x, base), (x + sw * 0.4, base - h * 0.5), top], fill=(232, 228, 214), width=30, joint="curve")
    for k in range(9):
        a = -math.pi / 2 + (k - 4) * 0.22 + 0.08 * math.sin(t * 2 + ph + k); L = 70
        d.line([top, (top[0] + L * math.cos(a), top[1] + L * math.sin(a))], fill=RED, width=16)
    d.ellipse([top[0] - 30, top[1] - 50, top[0] + 30, top[1] + 10], fill=(210, 40, 50))

def b_worm(sc, lt, dur, t):
    mode = sc.get("mode"); img = lab(t); d = ImageDraw.Draw(img); base = 870
    if mode == "scale":
        seafloor(d, base, 10, ROCK, 6); M = 290; g = eout((lt - 0.2) / 1.5)
        for dx, f, ph in WORMS: tubeworm(d, 700 + dx, base + 8, 2.2 * M * f * g, t, ph)
        figure(d, 1360, base, 1.7 * M, (90, 110, 128))
        yt = base - 2.2 * M; dashed(d, 480, yt, 1640, yt, GOLD, 3); text(img, "2+ m", 52, 1720, yt, GOLD)
        yp = base - 1.7 * M; dashed(d, 1240, yp, 1640, yp, DIM, 3); text(img, "PERSON", 34, 1720, yp, DIM, w="Bold")
        pill(img, "GIANT TUBE WORMS", 40, 700, 140, fill=GOLD)
    else:
        cx = 900; topy = 320
        d.rounded_rectangle([cx - 70, topy, cx + 70, base], 40, fill=(30, 36, 44), outline=(232, 228, 214), width=10)
        d.rounded_rectangle([cx - 46, topy + 30, cx + 46, base - 20], 30, fill=(150, 60, 70))
        r = random.Random(1)
        for k in range(110):
            x = cx + r.uniform(-34, 34) + 2 * math.sin(t * 4 + k); y = r.uniform(topy + 180, base - 40); d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(110, 230, 140))
        for k in range(9):
            a = -math.pi / 2 + (k - 4) * 0.2 + 0.08 * math.sin(t * 2 + k); d.line([(cx, topy + 10), (cx + 120 * math.cos(a), topy + 10 + 120 * math.sin(a))], fill=RED, width=20)
        u = ease((lt - 0.5) / 0.5)
        if u > 0:
            arrow(d, cx - 330, topy - 40, cx - 90, topy + 10, CYAN, 6); text(img, "VENT CHEMICALS IN", 34, cx - 420, topy - 80, CYAN, w="Black", u=u)
            arrow(d, cx + 60, 640, cx + 260, 640, GOLD, 6); text(img, "BACTERIA", 44, cx + 470, 610, (110, 230, 140), u=u); text(img, "MAKE THE FOOD", 44, cx + 470, 670, GOLD, u=u)
        text(img, "NO SUNLIGHT NEEDED", 46, 380, 640, WHITE, u=ease((lt - 1.4) / 0.4), maxw=600)
    return img

# ---------------- 9: whale fall ----------------
def skeleton(d, x0=560, x1=1380, y=800, col=BONE):
    n = 22
    for k in range(n):
        x = x0 + (x1 - x0) * k / n; yy_ = y - 18 * math.sin(k / n * math.pi); w_ = 14 if k < n - 6 else 18
        d.rounded_rectangle([x - w_, yy_ - 12, x + w_, yy_ + 12], 6, fill=col)
        if n - 12 < k < n - 1: d.arc([x - 40, yy_ - 110, x + 40, yy_ + 10], 180, 300, fill=col, width=8)
    d.rounded_rectangle([x1 + 10, y - 70, x1 + 210, y + 14], 30, fill=col); d.polygon([(x1 + 30, y + 14), (x1 + 200, y + 14), (x1 + 180, y + 36), (x1 + 40, y + 30)], fill=col)
    d.polygon([(x0 - 10, y), (x0 - 90, y - 40), (x0 - 70, y), (x0 - 90, y + 40)], fill=col)

def b_whale(sc, lt, dur, t):
    mode = sc.get("mode"); img = lab(t); d = ImageDraw.Draw(img); fl = 850
    seafloor(d, fl, 10, ROCK, 7)
    if mode == "fall":
        p = eout((lt - 0.2) / max(1.5, dur - 0.8)); cy = 180 + p * (fl - 90 - 180)
        d.polygon(shape_pts(WHALE, 980, cy, 760, flip=False), fill=(80, 96, 112), outline=(140, 160, 180))
        pill(img, "WHALE FALL", 42, W / 2, 140, fill=GOLD)
    elif mode == "feast":
        d.polygon(shape_pts(WHALE, 980, fl - 70, 760), fill=(96, 82, 90), outline=(150, 130, 140))
        for k in range(26):
            a = t * (0.5 + k * 0.03) + k; rx, ry = 430 + 30 * (k % 3), 120 + 20 * (k % 4)
            x, y = 980 + rx * math.cos(a), fl - 160 + ry * math.sin(a) * 0.6
            sgn = -1 if math.sin(a) > 0 else 1; s = 1.4 if k % 3 else 2.0
            critter(d, x, y, 0, (120, 140, 160), t, k, s) if sgn > 0 else critter(d, x, y, 0, (120, 140, 160), t, k, s)
        for k in range(6):
            x = 640 + k * 130 + 20 * math.sin(t + k); y = fl - 8; c = (200, 90, 70)
            d.ellipse([x - 20, y - 12, x + 20, y + 10], fill=c)
            for sx in (-1, 1): d.line([(x + sx * 16, y), (x + sx * 34, y + 10)], fill=c, width=4)
        pill(img, "THE FEAST BEGINS", 42, W / 2, 140, fill=CORAL, ink=WHITE)
    else:
        skeleton(d, 560, 1380, fl - 40)
        r = random.Random(12); g = ease((lt - 0.3) / 1.2) if mode == "worms" else 1.0
        for k in range(int(46 * g)):
            x = r.uniform(520, 1580); y = fl - 52 - 18 * math.sin((x - 560) / 820 * math.pi) if x < 1390 else fl - 110 + r.uniform(0, 60)
            sw = 4 * math.sin(t * 2 + k)
            for j in range(4): d.line([(x, y), (x + (j - 1.5) * 7 + sw, y - 26 - j % 2 * 6)], fill=(240, 80, 90), width=4)
        if mode == "worms":
            pill(img, "ZOMBIE WORMS", 42, W / 2, 140, fill=CORAL, ink=WHITE); text(img, "no eyes · no mouth · no stomach", 46, W / 2, 230, WHITE, w="SemiBold", u=ease((lt - 1.0) / 0.4))
        else:
            text(img, "50–100 YEARS", 120, W / 2, 330, GOLD, u=ease((lt - 1.6) / 0.4)); pill(img, "100+ SPECIES ON ONE WHALE FALL", 40, W / 2, 160, fill=TEAL, u=ease(lt / 0.4))
    return img

# ---------------- 10: Greenland shark ----------------
def draw_shark(d, cx, cy, L, t, col=(96, 100, 108)):
    pts = shape_pts(SHARK, cx, cy, L, flip=True, t=t, wob=0.025)
    d.polygon(pts, fill=col, outline=(140, 146, 156))
    ex, ey = cx - 0.4 * L, cy - 0.035 * L; d.ellipse([ex - L * 0.008, ey - L * 0.008, ex + L * 0.008, ey + L * 0.008], fill=(170, 200, 210))
    for k in range(5): x = cx - (0.3 - k * 0.018) * L; d.line([(x, cy - 0.03 * L), (x + 0.006 * L, cy + 0.05 * L)], fill=(70, 74, 82), width=3)

def b_shark(sc, lt, dur, t):
    mode = sc.get("mode"); dark = mode in ("final", "swim"); img = lab(t, dark=False); d = ImageDraw.Draw(img)
    if mode in ("swim", "final"):
        p = lt / max(1.0, dur); cx = 1400 - 500 * p if mode == "swim" else 1250 - 250 * p; cy = 620 if mode == "swim" else 680
        draw_shark(d, cx, cy + 10 * math.sin(t * 0.8), 980, t * 0.6)
        if mode == "swim":
            pill(img, "GREENLAND SHARK", 42, W / 2, 150, fill=GOLD); text(img, "grows ~1 cm a year", 46, W / 2, 240, WHITE, w="SemiBold", u=ease((lt - 3.0) / 0.4))
        else:
            text(img, "SOME MAY BE OLDER", 84, W / 2, 230, WHITE); text(img, "THAN THE UNITED STATES", 84, W / 2, 330, GOLD, u=ease((lt - 0.4) / 0.4))
    elif mode == "lens":
        cx, cy = 640, 520
        for k, (r, c) in enumerate(((300, (60, 90, 120)), (250, (72, 104, 136)), (200, (84, 118, 150)), (150, (96, 132, 164)), (100, (110, 146, 178)))):
            d.ellipse([cx - r, cy - r * 0.86, cx + r, cy + r * 0.86], fill=c, outline=(150, 190, 220), width=2)
        f = 0.75 + 0.25 * math.sin(t * 3); halo(img, cx, cy, 70, (255, 210, 120), 230 * f); d = ImageDraw.Draw(img)
        d.ellipse([cx - 48, cy - 42, cx + 48, cy + 42], fill=GOLD)
        u = ease((lt - 1.0) / 0.5); arrow(d, cx + 360, cy - 120, cx + 70, cy - 10, GOLD, 5) if u > 0 else None
        text(img, "EYE LENS CORE", 64, 1400, 400, GOLD, u=u); text(img, "formed when it was a baby", 44, 1400, 480, WHITE, w="SemiBold", u=u)
        pill(img, "CARBON-DATED", 40, 1400, 600, fill=TEAL, u=ease((lt - 2.5) / 0.4))
    else:   # timeline bars
        x0, sc_ = 360, 2.6; u = eout((lt - 0.2) / 1.8)
        for row, (name, yrs, col) in enumerate((("GREENLAND SHARK", 392, GOLD), ("BOWHEAD WHALE", 211, (120, 170, 210)))):
            y = 380 + row * 220; d.text((x0, y - 84), name, font=F(44, "Black"), fill=col)
            d.rounded_rectangle([x0, y - 22, x0 + yrs * sc_ * u, y + 22], 22, fill=col)
            d.text((x0 + yrs * sc_ * u + 20, y), f"~{int(yrs * u)} yrs", font=F(44, "Black"), fill=WHITE, anchor="lm")
        if u > 0.95:
            y = 380; d.line([(x0 + 272 * sc_, y + 34), (x0 + 512 * sc_, y + 34)], fill=GOLD, width=3)
            for xx_ in (272, 512): d.line([(x0 + xx_ * sc_, y + 24), (x0 + xx_ * sc_, y + 44)], fill=GOLD, width=3)
        v = ease((lt - 3.5) / 0.4)
        if v > 0:
            xm = x0 + 150 * sc_; d.line([(xm, 350), (xm, 440)], fill=CORAL, width=5)
            text(img, "READY TO BREED: ~150", 36, xm, 470, CORAL, u=v)
        pill(img, "LONGEST-LIVED VERTEBRATE KNOWN", 38, W / 2, 140, fill=TEAL)
    return img

def b_outro(sc, lt, dur, t):
    img = lab(t); d = ImageDraw.Draw(img)
    text(img, sc.get("q", "Which one sounded the MOST fake?"), 74, W / 2, 300, WHITE)
    click = sc.get("click_at", 1.6); on = ease((lt - click) / 0.25); cx, cy, w_, h_ = W / 2, 560, 300, 130
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=GOLD if on > 0.5 else (30, 60, 72), outline=WHITE, width=6)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; d.ellipse([kx - h_ / 2 + 16, cy - h_ / 2 + 16, kx + h_ / 2 - 16, cy + h_ / 2 - 16], fill=WHITE)
    text(img, "FAKE", 60, cx - w_ / 2 - 110, cy, WHITE if on < 0.5 else DIM); text(img, "TRUE", 60, cx + w_ / 2 + 110, cy, GOLD if on >= 0.5 else DIM)
    pill(img, "SUBSCRIBE · NEW DEEP DIVE EVERY TUE & FRI", 40, W / 2, 780, fill=CORAL, ink=WHITE, u=ease((lt - click - 0.4) / 0.4))
    return img

BEATS = dict(cold=b_cold, chapter=b_chapter, text=b_text, counter=b_counter, outro=b_outro, trench=b_trench, pressure=b_pressure, map=b_map,
             migrate=b_migrate, glowers=b_glowers, eye=b_eye, brine=b_brine, vent=b_vent, worm=b_worm, whale=b_whale, shark=b_shark)
NOBLOOM = ("glowers", "migrate")

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
beat = np.zeros(n, np.float32)                                                       # slow sonar pings under the pad
for k in range(int(total / 7.0)):
    place(beat, k * 7.0 + 3.0, tone(1318.5, 1.6, decay=3.2, harm=(1,)), 0.03); place(beat, k * 7.0 + 3.35, tone(1318.5, 1.2, decay=4, harm=(1,)), 0.012)
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
    d.rounded_rectangle([x - 28, y - 14, x + tw + 28, y + size + 18], 24, fill=(6, 14, 20))
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
    d.rounded_rectangle([44, 40, 330, 92], 22, fill=(6, 14, 20)); d.text((62, 48), "SOUNDS FAKE  ?!", font=F(30, "Black"), fill=(220, 235, 240))
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
