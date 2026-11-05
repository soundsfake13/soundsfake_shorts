"""LONG-FORM (16:9, 1920x1080) — 'Sounds Fake: Deep Dive' ep02: YOUR BODY.
Clean medical-illustration look: deep teal lab background with a faint grid and drifting translucent cells,
glowing type, chapter cards '01 / 10', lower-third captions. Based on engine/long/space_deep_dive.py.
Usage: python3 engine/long/ep02_body.py spec.json out.mp4 [t1,t2,... preview]
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
GOLD, TEAL, WHITE, DIM, CORAL, BLUE = (255, 200, 90), (90, 230, 210), (238, 246, 250), (130, 160, 175), (255, 112, 100), (90, 160, 255)
INK = (8, 18, 26)

# ---------------- background: teal lab gradient + faint grid + drifting cells ----------------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = np.clip(1 - (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.85)) ** 2), 0, 1) ** 0.8
BG = (np.array([3, 9, 16], np.float32) + vig[..., None] * np.array([10, 38, 50], np.float32))
grid = ((xx % 60 < 1.2) | (yy % 60 < 1.2)).astype(np.float32) * vig * 9
BG += grid[..., None] * np.array([0.6, 1.0, 1.0], np.float32)
BG_IMG = Image.fromarray(np.clip(BG, 0, 255).astype(np.uint8))
DARK_IMG = Image.fromarray(np.clip(BG * 0.35, 0, 255).astype(np.uint8))

def cell_sprite(r, col, a=70):
    s = Image.new("RGBA", (int(r * 2 + 8), int(r * 2 + 8)), (0, 0, 0, 0)); d = ImageDraw.Draw(s); c = r + 4
    d.ellipse([c - r, c - r, c + r, c + r], fill=col + (int(a * 0.35),), outline=col + (a,), width=max(2, int(r * 0.08)))
    d.ellipse([c - r * 0.32 + r * 0.15, c - r * 0.32 - r * 0.1, c + r * 0.32 + r * 0.15, c + r * 0.32 - r * 0.1], fill=col + (int(a * 0.7),))
    return s.filter(ImageFilter.GaussianBlur(max(1.5, r * 0.06)))
CELLS = []
for k in range(26):
    r = float(rng.choice([18, 28, 44, 70], p=[0.4, 0.3, 0.2, 0.1])); col = [TEAL, (120, 190, 255), (255, 150, 140)][k % 3]
    CELLS.append((cell_sprite(r, col, 55 if r > 40 else 75), rng.uniform(0, W), rng.uniform(0, H), rng.uniform(-14, 14), rng.uniform(-9, 9), rng.uniform(0, 6.3)))

def lab(t, cells=True, dark=False):
    img = (DARK_IMG if dark else BG_IMG).copy()
    if cells:
        for spr, x, y, vx, vy, ph in CELLS:
            px = (x + vx * t + 10 * math.sin(t * 0.4 + ph)) % (W + 160) - 80; py = (y + vy * t + 8 * math.cos(t * 0.5 + ph)) % (H + 160) - 80
            img.paste(spr, (int(px - spr.width / 2), int(py - spr.height / 2)), spr)
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

# --- 9 / hook: the glow ---
_fig = {}
def fig_mask(cx, foot, h, arms="down"):
    k = (cx, foot, h, arms)
    if k not in _fig:
        m = Image.new("L", (W, H), 0); figure(ImageDraw.Draw(m), cx, foot, h, 255, arms=arms); _fig[k] = m
    return _fig[k]

def glow_body(img, cx, foot, h, inten, face_boost=0.0):
    m = fig_mask(cx, foot, h)
    for blur, k in ((60, 0.55), (22, 0.8), (6, 0.6)):
        g = m.filter(ImageFilter.GaussianBlur(blur)).point(lambda v, kk=k * inten: int(min(255, v * kk)))
        img.paste(Image.new("RGB", (W, H), (110, 220, 255)), (0, 0), g)
    body = m.point(lambda v: int(v * 0.85))
    img.paste(Image.new("RGB", (W, H), (int(14 + 40 * inten), int(30 + 70 * inten), int(42 + 80 * inten))), (0, 0), body)
    if face_boost > 0:
        s = h / 600.0; hy = foot - 270 * s - 200 * s - 18 * s - 52 * s
        halo(img, cx, hy, 90 * s, (170, 240, 255), 200 * face_boost)

def b_glow(sc, lt, dur, t):
    mode = sc.get("mode", "reveal"); img = lab(t * 0.3, cells=False, dark=True)
    cx, foot, h = (1380, 1000, 860) if mode != "clock" else (640, 1000, 820)
    if mode == "hook":
        glow_body(img, cx, foot, h, 0.85 + 0.15 * math.sin(t * 2.2), 0.6)
        for i, s in enumerate(sc["lines"]): text(img, s, 104 if i == 0 else 120, 640, 400 + i * 140, GOLD if i == 1 else WHITE, maxw=1100)
        pill(img, "REAL LIGHT · 1,000× TOO FAINT TO SEE", 34, 640, 650, fill=TEAL, u=ease((lt - 0.8) / 0.4))
    elif mode == "dark":
        glow_body(img, cx, foot, h, 0.05)
        d = ImageDraw.Draw(img); x, y = 520, 520                                          # camera icon
        d.rounded_rectangle([x - 150, y - 90, x + 110, y + 90], 22, fill=(40, 60, 70)); d.polygon([(x + 110, y - 40), (x + 200, y - 85), (x + 200, y + 85), (x + 110, y + 40)], fill=(40, 60, 70))
        d.ellipse([x - 90, y - 60, x + 30, y + 60], fill=(15, 25, 32), outline=TEAL, width=6)
        if int(t * 2) % 2 == 0: d.ellipse([x - 130, y - 75, x - 108, y - 53], fill=CORAL)
        text(img, "PITCH-BLACK ROOM", 70, 560, 760, WHITE); text(img, "ultra-sensitive cameras", 40, 560, 840, DIM, w="SemiBold")
    elif mode == "reveal":
        u = ease((lt - 0.3) / 1.6); glow_body(img, cx, foot, h, u * (0.85 + 0.1 * math.sin(t * 2)), 0.6 * u)
        text(img, sc.get("label", "THE CAMERAS SAW IT"), 84, 600, 440, GOLD, maxw=1000); text(img, "real, visible light", 46, 600, 540, WHITE, w="SemiBold")
        pill(img, "SHOWN ~1,000× BRIGHTER THAN REAL", 32, 600, 660, fill=(40, 70, 80), ink=WHITE, u=ease((lt - 0.9) / 0.4))
    else:   # clock: brightness through the day
        hr = 8 + 10 * ease((lt - 0.5) / max(2.0, dur - 1.5))
        b = 0.25 + 0.75 * max(0.0, math.cos((hr - 16) / 12 * math.pi)) if hr >= 10 else 0.25 + 0.05 * (10 - hr)
        glow_body(img, cx, foot, h, b, 0.9 * b)
        d = ImageDraw.Draw(img); ox, oy, R = 1420, 420, 190
        d.ellipse([ox - R, oy - R, ox + R, oy + R], outline=WHITE, width=8)
        for k in range(12):
            a = k / 12 * 2 * math.pi; d.line([(ox + (R - 26) * math.sin(a), oy - (R - 26) * math.cos(a)), (ox + (R - 8) * math.sin(a), oy - (R - 8) * math.cos(a))], fill=WHITE, width=6)
        a = (hr % 12) / 12 * 2 * math.pi; d.line([(ox, oy), (ox + 110 * math.sin(a), oy - 110 * math.cos(a))], fill=GOLD, width=12)
        a2 = (hr % 1) * 2 * math.pi; d.line([(ox, oy), (ox + 160 * math.sin(a2), oy - 160 * math.cos(a2))], fill=WHITE, width=6)
        d.ellipse([ox - 14, oy - 14, ox + 14, oy + 14], fill=GOLD)
        hh = int(hr); lab_ = f"{(hh - 1) % 12 + 1}:{int((hr % 1) * 60):02d} {'AM' if hh < 12 else 'PM'}"
        text(img, lab_, 64, ox, oy + R + 80, GOLD)
        tag = "DIMMEST ~10 AM" if hr < 13 else "BRIGHTEST ~4 PM"
        pill(img, tag, 38, ox, oy + R + 180, fill=TEAL if hr >= 13 else (40, 70, 80), ink=INK if hr >= 13 else WHITE)
    return img

# --- 1: height ---
def ruler(d, x, top, bot, step=40):
    d.line([(x, top), (x, bot)], fill=DIM, width=3)
    for k, y in enumerate(range(int(bot), int(top), -step)): d.line([(x, y), (x + (26 if k % 5 == 0 else 14), y)], fill=DIM, width=3)

def b_height(sc, lt, dur, t):
    img = lab(t); d = ImageDraw.Draw(img)
    if sc.get("mode") == "space":
        img = lab(t, cells=False, dark=True); d = ImageDraw.Draw(img); r = random.Random(3)
        for _ in range(220):
            x, y = r.uniform(0, W), r.uniform(0, H); c = r.randint(90, 230); d.ellipse([x - 1.6, y - 1.6, x + 1.6, y + 1.6], fill=(c, c, c))
        u = ease((lt - 0.5) / 2.0); fy = 920 + 14 * math.sin(t * 1.3)
        top = figure(d, 640, fy, 660, (210, 230, 240), stretch=1.0 + 0.10 * u, arms="out")      # stretch exaggerated for clarity
        d.line([(860, top), (960, top)], fill=GOLD, width=5); d.line([(860, fy), (960, fy)], fill=GOLD, width=5); d.line([(910, top), (910, fy)], fill=GOLD, width=3)
        text(img, f"+{3 * u:.1f}%", 190, 1420, 400, GOLD); text(img, "TALLER IN SPACE", 64, 1420, 540, WHITE)
        pill(img, "ABOUT +5 CM FOR A TALL PERSON", 36, 1420, 650, fill=TEAL, u=ease((lt - 1.4) / 0.4))
        return img
    foot = 860; hm = 600; u = ease((lt - 0.8) / 1.4); hn = hm - 26 * u          # difference exaggerated ~2x so it reads
    ruler(d, 330, foot - 700, foot)
    ta = figure(d, 640, foot, hm, (200, 225, 238)); tb = figure(d, 1060, foot, hn, (150, 175, 190))
    d.line([(520, ta), (1250, ta)], fill=GOLD, width=4)
    if u > 0.05:
        d.line([(940, tb), (1250, tb)], fill=CORAL, width=4); pill(img, "≈ 1 CM", 40, 1380, (ta + tb) / 2, u=u)
    text(img, "MORNING", 46, 640, foot + 60, GOLD); text(img, "BEDTIME", 46, 1060, foot + 60, CORAL)
    return img

def b_spine(sc, lt, dur, t):
    img = lab(t); d = ImageDraw.Draw(img); cx = 700
    sq = sc.get("mode") == "squeeze"; u = ease((lt - 0.4) / 2.2)
    disc = 30 - 16 * u if sq else 14 + 16 * u
    y = 900
    for k in range(9):
        bh = 54
        d.rounded_rectangle([cx - 120, y - bh, cx + 120, y], 22, fill=(196, 202, 192)); d.rounded_rectangle([cx + 100, y - bh + 14, cx + 190, y - 14], 14, fill=(170, 176, 166))
        y -= bh
        if k < 8:
            d.ellipse([cx - 112, y - disc, cx + 112, y], fill=TEAL); y -= disc
    if sq:
        for k in range(3):
            ay = 260 + ((t * 120 + k * 120) % 360)
            for ax in (cx - 230, cx + 290): d.polygon([(ax - 30, ay), (ax + 30, ay), (ax, ay + 40)], fill=CORAL)
        text(img, "GRAVITY", 70, 1400, 380, CORAL); text(img, "squeezes the discs", 48, 1400, 470, WHITE, w="SemiBold")
        pill(img, "DISCS LOSE A LITTLE FLUID", 38, 1400, 580, fill=TEAL, u=ease((lt - 1.2) / 0.4))
    else:
        text(img, "LYING DOWN", 70, 1400, 380, TEAL); text(img, "the discs refill", 48, 1400, 470, WHITE, w="SemiBold")
        pill(img, "YOU GROW BACK OVERNIGHT", 38, 1400, 580, u=ease((lt - 1.0) / 0.4))
    return img

# --- 2: bones ---
BONEPTS = [(random.Random(k).uniform(150, 980), random.Random(k + 999).uniform(180, 850)) for k in range(300)]
def b_bones(sc, lt, dur, t):
    img = lab(t); d = ImageDraw.Draw(img); mode = sc.get("mode")
    if mode == "merge": m = ease((lt - 0.3) / max(1.5, dur - 1.0))
    elif mode == "count": m = ease((lt - 3.2) / 2.0)
    else: m = 0.0
    n_alive = int(300 - 94 * m)
    for k, (x, y) in enumerate(BONEPTS):
        if k >= 206:                                                               # these 94 pieces fuse into a partner
                    px, py = BONEPTS[k - 206]; x, y = x + (px - x) * m, y + (py - y) * m
        if k >= 206 and m >= 0.999: continue
        r = 10 if mode != "soft" else 11 + 2.5 * math.sin(t * 3 + k)
        col = (235, 232, 220) if mode != "soft" or k % 3 else TEAL
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)
    if mode == "soft":
        text(img, "SOFT CARTILAGE", 80, 1440, 420, TEAL); text(img, "flexible, for birth", 46, 1440, 520, WHITE, w="SemiBold")
    else:
        v = 300 - 94 * m; text(img, f"{int(round(v))}", 230, 1440, 430, GOLD)
        text(img, "BONES" if m < 0.98 else "BONES AS AN ADULT", 60, 1440, 590, WHITE)
        pill(img, "AT BIRTH: ~300" if m < 0.5 else "FUSED TOGETHER", 38, 1440, 700, fill=TEAL)
    return img

# --- 3: heart ---
def heart_poly(cx, cy, s):
    pts = []
    for k in range(120):
        a = k / 120 * 2 * math.pi; x = 16 * math.sin(a) ** 3; y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((cx + x * s, cy - y * s))
    return pts

def b_heart(sc, lt, dur, t):
    img = lab(t); cx, cy = 600, 470
    ph = (t * 1.2) % 1; pulse = 1 + 0.09 * math.exp(-((ph - 0.05) / 0.06) ** 2) + 0.05 * math.exp(-((ph - 0.25) / 0.06) ** 2)
    halo(img, cx, cy, 260 * pulse, (255, 80, 80), 120)
    d = ImageDraw.Draw(img); d.polygon(heart_poly(cx, cy, 15 * pulse), fill=(230, 70, 80)); d.polygon(heart_poly(cx - 40, cy - 50, 6 * pulse), fill=(250, 110, 115))
    pts = []                                                                        # ECG trace
    for x in range(0, W, 6):
        p = ((x / 520) - t * 1.2) % 1; y = 880
        if 0.30 < p < 0.34: y -= 120 * math.sin((p - 0.30) / 0.04 * math.pi)
        elif 0.34 < p < 0.37: y += 50 * math.sin((p - 0.34) / 0.03 * math.pi)
        elif 0.5 < p < 0.6: y -= 20 * math.sin((p - 0.5) / 0.1 * math.pi)
        pts.append((x, y))
    d.line(pts, fill=TEAL, width=4)
    if sc.get("mode") == "size":
        text(img, "≈ TWO CLASPED HANDS", 74, 1400, 420, GOLD, maxw=900); text(img, "that's how big it is", 46, 1400, 520, WHITE, w="SemiBold")
    else:
        v = sc.get("to", 100000) * eout((lt - 0.3) / 2.5)
        text(img, f"{int(v):,}", 200, 1400, 420, GOLD); text(img, sc.get("label", "BEATS EVERY DAY"), 60, 1400, 560, WHITE)
    return img

def b_tubs(sc, lt, dur, t):
    img = lab(t); d = ImageDraw.Draw(img); n = sc.get("n", 50); fill_n = n * eout((lt - 0.3) / max(2.0, dur - 1.2))
    for k in range(n):
        c, r = k % 10, k // 10; x, y = 140 + c * 92, 250 + r * 120
        d.rounded_rectangle([x, y, x + 76, y + 50], 18, outline=(200, 215, 225), width=4)
        f = max(0.0, min(1.0, fill_n - k))
        if f > 0: d.rounded_rectangle([x + 6, y + 6 + 38 * (1 - f), x + 70, y + 44], 12, fill=CORAL)
        d.line([(x + 14, y + 50), (x + 10, y + 64)], fill=(200, 215, 225), width=4); d.line([(x + 62, y + 50), (x + 66, y + 64)], fill=(200, 215, 225), width=4)
    v = 7500 * eout((lt - 0.3) / max(2.0, dur - 1.2))
    text(img, f"{int(v):,} L", 170, 1460, 420, GOLD); text(img, "PUMPED EVERY DAY", 56, 1460, 560, WHITE)
    pill(img, f"≈ {int(round(fill_n))} BATHTUBS", 40, 1460, 670, fill=TEAL)
    return img

# --- 4: brain ---
def b_brainbar(sc, lt, dur, t):
    img = lab(t); d = ImageDraw.Draw(img); base, top = 820, 230; sc_ = (base - top) / 25.0
    for k in range(0, 26, 5):
        y = base - k * sc_; d.line([(360, y), (1100, y)], fill=(30, 60, 70), width=2); d.text((330, y), f"{k}%", font=F(28, "SemiBold"), fill=DIM, anchor="rm")
    u1 = eout((lt - 0.2) / 1.0); h1 = 2 * sc_ * u1
    d.rounded_rectangle([450, base - max(h1, 4), 690, base], 16, fill=TEAL)
    text(img, "WEIGHT", 44, 570, base + 50, TEAL); text(img, "2%", 72, 570, base - h1 - 60, TEAL, u=u1)
    if sc.get("stage", 1) >= 2:
        u2 = eout((lt - 0.4) / 1.6); h2 = 20 * sc_ * u2
        d.rounded_rectangle([800, base - max(h2, 4), 1040, base], 16, fill=GOLD)
        text(img, "ENERGY", 44, 920, base + 50, GOLD); text(img, f"~{int(20 * u2)}%", 72, 920, base - h2 - 60, GOLD, u=u2)
        text(img, "≈ ONE FIFTH", 90, 1520, 440, GOLD); text(img, "of your energy, at rest", 44, 1520, 540, WHITE, w="SemiBold")
    else:
        text(img, "YOUR BRAIN", 90, 1520, 440, WHITE); text(img, "about 2% of your weight", 44, 1520, 540, TEAL, w="SemiBold")
    return img

def b_bulb(sc, lt, dur, t):
    img = lab(t); cx, cy = 620, 470; fl = 0.85 + 0.15 * math.sin(t * 9) * math.sin(t * 3.7)
    halo(img, cx, cy, 300, (255, 200, 110), 150 * fl)
    d = ImageDraw.Draw(img); d.ellipse([cx - 170, cy - 200, cx + 170, cy + 140], fill=(255, 226, 150)); d.rectangle([cx - 80, cy + 120, cx + 80, cy + 220], fill=(255, 226, 150))
    for k in range(4): d.rounded_rectangle([cx - 88, cy + 220 + k * 30, cx + 88, cy + 244 + k * 30], 10, fill=(150, 160, 170))
    d.line([(cx - 50, cy + 100), (cx - 30, cy - 40), (cx, cy + 20), (cx + 30, cy - 40), (cx + 50, cy + 100)], fill=(255, 150, 40), width=6)
    v = 20 * eout((lt - 0.2) / 1.5)
    text(img, f"≈ {int(round(v))} WATTS", 150, 1420, 420, GOLD); text(img, "TO RUN YOUR BRAIN", 56, 1420, 550, WHITE)
    pill(img, "LESS THAN MANY OLD LIGHT BULBS", 36, 1420, 660, fill=TEAL, u=ease((lt - 1.2) / 0.4))
    return img

NEU = [(random.Random(k * 7).uniform(120, 1000), random.Random(k * 7 + 1).uniform(170, 900)) for k in range(70)]
EDG = [(i, j) for i in range(len(NEU)) for j in range(i + 1, len(NEU)) if math.dist(NEU[i], NEU[j]) < 170]
def b_neurons(sc, lt, dur, t):
    img = lab(t, cells=False); d = ImageDraw.Draw(img)
    for i, j in EDG: d.line([NEU[i], NEU[j]], fill=(40, 110, 120), width=2)
    for k, (i, j) in enumerate(EDG):
        p = (t * 0.7 + k * 0.137) % 1
        if (k * 31) % 4 == 0:
            x = NEU[i][0] + (NEU[j][0] - NEU[i][0]) * p; y = NEU[i][1] + (NEU[j][1] - NEU[i][1]) * p; d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=GOLD)
    for x, y in NEU: d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=TEAL)
    img = bloom(img, 0.5)
    v = 86 * eout((lt - 0.2) / 2.0)
    text(img, f"{int(round(v))} BILLION", 140, 1460, 420, GOLD); text(img, "NERVE CELLS", 64, 1460, 540, WHITE)
    return img

# --- 5: DNA ---
def helix(d, x0, x1, cy, amp, t, col1=TEAL, col2=CORAL, step=6, width=6, rungs=True):
    p1, p2 = [], []
    for x in range(int(x0), int(x1), step):
        a = x / 46 + t * 2.0; p1.append((x, cy + amp * math.sin(a))); p2.append((x, cy + amp * math.sin(a + math.pi)))
    if rungs:
        for k in range(0, len(p1), 4): d.line([p1[k], p2[k]], fill=(120, 150, 160), width=3)
    if len(p1) > 1: d.line(p1, fill=col1, width=width); d.line(p2, fill=col2, width=width)

def b_dna(sc, lt, dur, t):
    img = lab(t); d = ImageDraw.Draw(img); mode = sc.get("mode")
    if mode == "coil":
        cx, cy = 600, 520; halo(img, cx, cy, 260, (40, 140, 150), 90); d = ImageDraw.Draw(img)
        d.ellipse([cx - 280, cy - 280, cx + 280, cy + 280], fill=(18, 50, 62), outline=TEAL, width=6)
        r = random.Random(2); pts = [(cx, cy)]
        for k in range(260):
            x, y = pts[-1]; a = r.uniform(0, 6.283) + 0.3 * math.sin(t + k); nx, ny = x + 22 * math.cos(a), y + 22 * math.sin(a)
            if math.dist((nx, ny), (cx, cy)) < 240: pts.append((nx, ny))
        d.line(pts, fill=CORAL, width=4)
        text(img, "YOUR DNA", 100, 1440, 420, GOLD); text(img, "folded into each nucleus", 46, 1440, 520, WHITE, w="SemiBold")
        pill(img, "TOO SMALL TO SEE", 38, 1440, 630, fill=TEAL, u=ease((lt - 0.8) / 0.4))
    elif mode == "stretch":
        u = eout((lt - 0.3) / 2.2); x1 = 260 + 1380 * u
        helix(d, 260, x1, 640, 34, t)
        ruler_y = 760; d.line([(260, ruler_y), (1640, ruler_y)], fill=DIM, width=3)
        for k in range(11): x = 260 + k * 138; d.line([(x, ruler_y), (x, ruler_y + (26 if k % 5 == 0 else 14))], fill=DIM, width=3)
        text(img, "0 m", 30, 260, ruler_y + 60, DIM, w="SemiBold"); text(img, "1 m", 30, 950, ruler_y + 60, DIM, w="SemiBold"); text(img, "2 m", 30, 1640, ruler_y + 60, DIM, w="SemiBold")
        figure(d, 1760, 900, 600 * 1.75 / 2.0 * 0.9, (120, 150, 165))
        text(img, f"{2 * u:.1f} METERS", 130, 900, 330, GOLD); text(img, "of DNA from ONE cell", 46, 900, 440, WHITE, w="SemiBold")
    else:  # pluto
        u = eout((lt - 0.4) / max(2.0, dur - 1.5))
        img = lab(t, cells=False, dark=True); d = ImageDraw.Draw(img); r = random.Random(5)
        for _ in range(200):
            x, y = r.uniform(0, W), r.uniform(0, H); c = r.randint(80, 220); d.ellipse([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=(c, c, c))
        ex, px, cy = 220, 1700, 600
        halo(img, ex, cy, 90, (60, 140, 255), 120); d = ImageDraw.Draw(img); d.ellipse([ex - 70, cy - 70, ex + 70, cy + 70], fill=(50, 110, 210)); d.ellipse([ex - 40, cy - 50, ex + 10, cy - 10], fill=(70, 160, 100))
        d.ellipse([px - 26, cy - 26, px + 26, cy + 26], fill=(205, 180, 150)); d.ellipse([px - 8, cy - 4, px + 14, cy + 16], fill=(235, 220, 200))
        text(img, "EARTH", 32, ex, cy + 110, BLUE, w="Bold"); text(img, "PLUTO", 32, px, cy + 70, (220, 200, 170), w="Bold")
        x1 = ex + 80 + (px - 40 - ex - 80) * u
        helix(d, ex + 80, x1, cy, 14, t, step=5, width=4, rungs=False)
        text(img, "ALL YOUR DNA, END TO END", 72, W / 2, 300, GOLD); text(img, "would reach Pluto", 46, W / 2, 390, WHITE, w="SemiBold")
        pill(img, "ESTIMATE: SALK INSTITUTE", 32, W / 2, 860, fill=(40, 70, 80), ink=WHITE, u=ease((lt - 1.0) / 0.4))
    return img

# --- 6: gut lining ---
def b_gut(sc, lt, dur, t):
    img = lab(t, cells=False); d = ImageDraw.Draw(img)
    d.rectangle([0, 860, W, H], fill=(120, 40, 55))
    for v in range(9):                                                        # villi: fingers made of cells moving up and shedding
        bx = 140 + v * 210; top = 380 + 40 * math.sin(v * 1.7)
        d.rounded_rectangle([bx - 70, top, bx + 70, 880], 70, fill=(200, 80, 95))
        for side in (-1, 1):
            for k in range(14):
                p = (k / 14 + t * 0.08 + v * 0.05) % 1; y = 870 - (870 - top) * p; x = bx + side * 52
                if p > 0.9: x += side * (p - 0.9) * 400; y -= (p - 0.9) * 300
                r = 17 * (1 - max(0, p - 0.9) * 5)
                if r > 2: d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 175, 170), outline=(150, 50, 65), width=2)
    for k in range(40):                                                       # food/acid particles rushing past
        x = (k * 97 + t * 420) % (W + 200) - 100; y = 160 + (k * 53) % 200
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(230, 210, 120))
    img = bloom(img, 0.3)
    pill(img, sc.get("label", "THE LINING OF YOUR GUT"), 46, W / 2, 110, u=ease((lt - 0.2) / 0.4))
    return img

# --- 7: cell turnover ---
CELLP = [(random.Random(k * 3).uniform(60, W - 60), random.Random(k * 3 + 1).uniform(150, 940), random.Random(k * 3 + 2).uniform(0, 1)) for k in range(240)]
def b_cells(sc, lt, dur, t):
    img = lab(t, cells=False); d = ImageDraw.Draw(img)
    for x, y, ph in CELLP:
        p = (t * 0.45 + ph) % 1; r = 16 * math.sin(p * math.pi) ** 0.5
        col = (255, 120, 110) if ph < 0.6 else TEAL
        if r > 1: d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(c * 0.55) for c in col), outline=col, width=2)
    d.rounded_rectangle([W / 2 - 620, 300, W / 2 + 620, 700], 40, fill=(6, 16, 22))
    if sc.get("mode") == "second":
        v = 3.8e6 * max(0.0, lt - 0.2)
        text(img, f"{int(v):,}", 170, W / 2, 450, GOLD); text(img, "NEW CELLS SINCE THIS SENTENCE STARTED", 44, W / 2, 590, WHITE, w="Bold")
    else:
        v = 330 * eout((lt - 0.2) / 2.0)
        text(img, f"{int(round(v))} BILLION", 170, W / 2, 450, GOLD); text(img, "CELLS REPLACED EVERY DAY", 54, W / 2, 590, WHITE)
    return img

# --- 8: bacteria ---
def b_bacteria(sc, lt, dur, t):
    img = lab(t, cells=False); d = ImageDraw.Draw(img); both = sc.get("mode") == "both"
    r = random.Random(11)
    def blob(cx, n, kind, u):
        for k in range(int(n * u)):
            a = r.uniform(0, 6.283); rr = 240 * math.sqrt(r.uniform(0, 1)); x = cx + rr * math.cos(a) + 4 * math.sin(t * 2 + k); y = 520 + rr * math.sin(a) * 0.9
            if kind == "h": d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=(230, 100, 100), outline=(255, 170, 160), width=2)
            else:
                ang = r.uniform(0, 3.14) + 0.2 * math.sin(t + k); dx, dy = 13 * math.cos(ang), 13 * math.sin(ang)
                d.line([(x - dx, y - dy), (x + dx, y + dy)], fill=TEAL, width=11)
    blob(560 if both else W / 2, 300, "h", eout(lt / 1.0) if not both else 1.0)
    text(img, "HUMAN CELLS", 50, 560 if both else W / 2, 830, CORAL); text(img, "~30 TRILLION", 80, 560 if both else W / 2, 200, WHITE)
    if both:
        u = eout((lt - 0.2) / 1.4); blob(1360, 380, "b", u)
        text(img, "BACTERIA", 50, 1360, 830, TEAL); text(img, "~38 TRILLION", 80, 1360, 200, GOLD, u=u)
        text(img, "vs", 60, W / 2 - 0, 520, DIM)
    return img

# --- 10: atoms / big bang ---
def b_atoms(sc, lt, dur, t):
    img = lab(t); d = ImageDraw.Draw(img); cx, cy, R = 620, 520, 300
    u = eout((lt - 0.2) / 1.8)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(30, 60, 72))
    d.pieslice([cx - R, cy - R, cx + R, cy + R], -90, -90 + 360 * 0.63 * u, fill=GOLD)
    d.ellipse([cx - R * 0.58, cy - R * 0.58, cx + R * 0.58, cy + R * 0.58], fill=(8, 24, 32))
    text(img, "H", 150, cx, cy, GOLD)
    text(img, f"{int(round(63 * u))}%", 200, 1420, 400, GOLD); text(img, "OF YOUR ATOMS", 60, 1420, 540, WHITE)
    pill(img, "ARE HYDROGEN", 42, 1420, 650, fill=TEAL, u=ease((lt - 0.8) / 0.4))
    return img

BANG = [(random.Random(k).uniform(0, 6.283), random.Random(k + 5).uniform(0.3, 1.0), random.Random(k + 9).choice([GOLD, (255, 255, 255), (255, 150, 90), (140, 200, 255)])) for k in range(500)]
def b_bigbang(sc, lt, dur, t):
    img = lab(t, cells=False, dark=True); d = ImageDraw.Draw(img); cx, cy = 640, 540
    if sc.get("mode") == "bang":
        p = eout(lt / 3.0)
        halo(img, cx, cy, 60 + 260 * (1 - p), (255, 230, 170), 255 * (1 - 0.7 * p)); d = ImageDraw.Draw(img)
        for a, sp, col in BANG:
            rr = 30 + sp * 900 * p; x, y = cx + rr * math.cos(a), cy + rr * math.sin(a) * 0.8; s = 2 + 2 * sp
            d.ellipse([x - s, y - s, x + s, y + s], fill=col)
        for k in range(7):                                                   # hydrogen atoms drifting out
            a = k / 7 * 6.283 + 0.4; rr = 120 + 300 * p; x, y = cx + rr * math.cos(a), cy + rr * math.sin(a) * 0.8
            d.ellipse([x - 34, y - 34, x + 34, y + 34], outline=TEAL, width=4); d.text((x, y), "H", font=F(36, "Black"), fill=WHITE, anchor="mm")
        img = bloom(img, 0.6)
        text(img, "MADE IN THE", 60, 1480, 400, WHITE); text(img, "BIG BANG", 130, 1480, 510, GOLD)
        pill(img, "BEFORE THE FIRST STARS", 38, 1480, 640, fill=TEAL, u=ease((lt - 1.2) / 0.4))
    else:
        for k, (sx, sy, lab_) in enumerate(((260, 260, "C"), (520, 180, "O"), (380, 760, "N"), (760, 300, "Ca"), (180, 560, "Fe"))):
            fl = 0.8 + 0.2 * math.sin(t * 3 + k); halo(img, sx, sy, 70, (255, 200, 120), 220 * fl)
            d = ImageDraw.Draw(img); d.ellipse([sx - 16, sy - 16, sx + 16, sy + 16], fill=(255, 245, 210))
            p = ((t * 0.25 + k * 0.2) % 1); x = sx + (1000 - sx) * p; y = sy + (560 - sy) * p
            d.ellipse([x - 26, y - 26, x + 26, y + 26], outline=GOLD, width=3); d.text((x, y), lab_, font=F(26, "Black"), fill=WHITE, anchor="mm")
        figure(d, 1060, 960, 600, (150, 185, 200))
        img = bloom(img, 0.5)
        text(img, "FORGED IN STARS", 84, 1520, 360, GOLD); text(img, "carbon · oxygen · more", 44, 1520, 460, WHITE, w="SemiBold")
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

BEATS = dict(cold=b_cold, chapter=b_chapter, text=b_text, counter=b_counter, glow=b_glow, height=b_height, spine=b_spine, bones=b_bones,
             heart=b_heart, tubs=b_tubs, brainbar=b_brainbar, bulb=b_bulb, neurons=b_neurons, dna=b_dna, gut=b_gut, cells=b_cells,
             bacteria=b_bacteria, atoms=b_atoms, bigbang=b_bigbang, outro=b_outro)
NOBLOOM = ("neurons", "gut", "bigbang", "glow")

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
beat = np.zeros(n, np.float32)                                                       # soft heartbeat-like pulse under the pad
for k in range(int(total / 1.2)):
    for off, g in ((0.0, 1.0), (0.22, 0.6)): place(beat, k * 1.2 + off, tone(52, 0.25, decay=18, harm=(1,)), 0.05 * g)
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
