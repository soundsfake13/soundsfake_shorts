"""LONG-FORM (16:9, 1920x1080) — 'Sounds Fake: Deep Dive' ep05: HISTORY.
Archival look: aged parchment, film grain + flicker + scratches, ink-drawn diagrams, serif headlines, a fictional
newspaper ('The Sounds Fake Gazette'), red rubber stamps, timelines. Based on engine/long/space_deep_dive.py.
Usage: python3 engine/long/ep05_history.py spec.json out.mp4 [t1,t2,... preview]
"""
import json, math, os, random, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import core
from core import narrate, write_audio, caption_groups, group_at, ease, eout, back, tone, place, hook_hit, whoosh, SR

W, H, FPS = 1920, 1080, 30
spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
rng = np.random.default_rng(5); random.seed(5)
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
ED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts") + "/"
_fc = {}
def F(s, w="Black"):
    k = (int(s), w)
    if k not in _fc:
        if w == "serif": _fc[k] = ImageFont.truetype(ED + "DMSerifDisplay-Regular.ttf", int(s))
        elif w == "black": _fc[k] = ImageFont.truetype(ED + "UnifrakturMaguntia-Book.ttf", int(s))
        else: _fc[k] = ImageFont.truetype(f"{FD}InterDisplay-{w}.otf", int(s))
    return _fc[k]

PAPER, INK, SEPIA, RED, GOLD, CREAM = (232, 218, 186), (42, 30, 22), (112, 84, 56), (178, 38, 30), (196, 140, 40), (250, 242, 222)
BRONZE, BRONZE_D, SKY = (176, 120, 60), (110, 70, 34), (70, 96, 120)

# ---------------- background: aged parchment + vignette + stains; per-frame grain/flicker/scratches ----------------
def lowf(h, w, cell, seed):
    r = np.random.default_rng(seed); s = r.random((h // cell + 2, w // cell + 2)).astype(np.float32)
    return np.asarray(Image.fromarray((s * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = np.clip(1 - (((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.68)) ** 2) * 0.55, 0, 1)
P = np.array(PAPER, np.float32) * (0.80 + 0.20 * vig[..., None])
P -= (lowf(H, W, 220, 3) ** 3)[..., None] * np.array([22, 26, 28], np.float32)
P -= (lowf(H, W, 60, 4) * 10)[..., None]
fib = np.asarray(Image.fromarray((rng.random((H, W)) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32) / 255
P += ((fib - 0.5) * 14)[..., None]
PAPER_ARR = np.clip(P, 0, 255)
GRAINS = [np.clip(PAPER_ARR + rng.normal(0, 4, (H, W, 1)).astype(np.float32), 0, 255).astype(np.uint8) for _ in range(4)]
GRAIN_IMGS = [Image.fromarray(g) for g in GRAINS]
NOISE_L = [Image.fromarray(np.clip(128 + rng.normal(0, 14, (H, W)), 0, 255).astype(np.uint8)) for _ in range(3)]

def paper(t):
    return GRAIN_IMGS[0].copy()

def film(img, t, dark=False):
    """old-film overlay: scratches, flicker, dust."""
    d = ImageDraw.Draw(img); r = random.Random(int(t * 8))
    if r.random() < 0.35:
        x = r.uniform(80, W - 80); d.line([(x, 0), (x + r.uniform(-8, 8), H)], fill=(250, 240, 220) if dark else (150, 125, 95), width=1)
    for _ in range(r.randint(0, 3)):
        x, y, s = r.uniform(0, W), r.uniform(0, H), r.uniform(1, 3); d.ellipse([x - s, y - s, x + s, y + s], fill=(60, 45, 30) if not dark else (220, 210, 190))
    return img

def darkbg(t, top=(10, 14, 26), bot=(30, 32, 44)):
    a = np.array(top, np.float32) * (1 - yy[..., None] / H) + np.array(bot, np.float32) * (yy[..., None] / H)
    return a

_dcache = {}
def dark_img(t, key="night", top=(10, 14, 26), bot=(30, 32, 44)):
    if key not in _dcache: _dcache[key] = [Image.fromarray(np.clip(darkbg(0, top, bot) + rng.normal(0, 3, (H, W, 1)), 0, 255).astype(np.uint8)) for _ in range(3)]
    return _dcache[key][0].copy()

def bloom(img, k=0.6):
    a = np.asarray(img).astype(np.float32)
    s = Image.fromarray(np.clip((a - 140) * 1.5, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    b = np.asarray(s.filter(ImageFilter.GaussianBlur(8)).resize((W, H), Image.BILINEAR)).astype(np.float32)
    return Image.fromarray(np.clip(a + b * k, 0, 255).astype(np.uint8))

def halo(img, cx, cy, r, col, strength=160):
    g = Image.new("L", (W, H), 0); ImageDraw.Draw(g).ellipse([cx - r, cy - r, cx + r, cy + r], fill=strength)
    img.paste(Image.new("RGB", (W, H), col), (0, 0), g.filter(ImageFilter.GaussianBlur(r * 0.5)))

# ---------------- type ----------------
def text(img, s, size, x, y, col=INK, w="serif", anchor="mm", u=1.0, maxw=W - 220, shadow=False, bg=PAPER):
    if u <= 0: return
    d = ImageDraw.Draw(img)
    while d.textlength(s, font=F(size, w)) > maxw and size > 24: size -= 4
    f = F(size, w); y = y + (1 - min(1, u)) * 24
    uu = min(1.0, u); col = tuple(int(c * uu + b * (1 - uu)) for c, b in zip(col, bg))
    if shadow: d.text((x + 3, y + 4), s, font=f, fill=(0, 0, 0), anchor=anchor)
    d.text((x, y), s, font=f, fill=col, anchor=anchor)

def pill(img, s, size, x, y, fill=RED, ink=CREAM, u=1.0):
    if u <= 0: return
    d = ImageDraw.Draw(img); f = F(size, "Bold"); tw = d.textlength(s, font=f); y = y + (1 - min(1, u)) * 16
    d.rectangle([x - tw / 2 - 28, y - size * 0.75, x + tw / 2 + 28, y + size * 0.75], fill=fill)
    d.rectangle([x - tw / 2 - 20, y - size * 0.75 + 8, x + tw / 2 + 20, y + size * 0.75 - 8], outline=ink, width=2)
    d.text((x, y), s, font=f, fill=ink, anchor="mm")

def rule(d, x0, x1, y, col=INK, double=True):
    d.line([(x0, y), (x1, y)], fill=col, width=4)
    if double: d.line([(x0, y + 10), (x1, y + 10)], fill=col, width=1)

def fmtyear(y, bc=False):
    if y < 0: return f"{-y} BC"
    return f"{y} AD" if bc and y < 1000 else str(y)

# ---------------- stamp (cached, rotated, rough ink) ----------------
_st = {}
def stamp_img(s, size=150, col=RED, rot=-7):
    k = (s, size, rot)
    if k not in _st:
        f = F(size, "Black"); tw = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(s, font=f))
        w_, h_ = tw + 120, int(size * 1.7)
        m = Image.new("L", (w_, h_), 0); d = ImageDraw.Draw(m)
        d.rounded_rectangle([8, 8, w_ - 8, h_ - 8], 18, outline=255, width=12)
        d.text((w_ / 2, h_ / 2 + 4), s, font=f, fill=255, anchor="mm")
        nz = np.random.default_rng(len(s)).random((h_, w_))
        a = np.asarray(m).astype(np.float32) * (0.55 + 0.45 * (nz > 0.18))
        m = Image.fromarray(a.astype(np.uint8)).rotate(rot, expand=True, resample=Image.BICUBIC)
        rgba = Image.new("RGBA", m.size, col + (0,)); rgba.putalpha(m.point(lambda v: int(v * 0.92)))
        _st[k] = rgba
    return _st[k]

def put_stamp(img, s, x, y, lt, at=0.3, size=150, col=RED, rot=-7):
    if lt < at: return
    p = min(1.0, (lt - at) / 0.22); sc = 1.0 + 0.7 * (1 - p) ** 2
    sp = stamp_img(s, size, col, rot)
    if sc != 1.0: sp = sp.resize((int(sp.width * sc), int(sp.height * sc)), Image.BILINEAR)
    if p < 1: a = sp.getchannel("A").point(lambda v: int(v * p)); sp = sp.copy(); sp.putalpha(a)
    img.paste(sp, (int(x - sp.width / 2), int(y - sp.height / 2)), sp)

# ---------------- drawings ----------------
def emu(d, x, y, s=1.0, ph=0.0, col=INK, run=False):
    """flat emu facing right; (x, y) = body centre."""
    d.ellipse([x - 75 * s, y - 50 * s, x + 65 * s, y + 42 * s], fill=col)                         # body
    d.polygon([(x - 70 * s, y - 20 * s), (x - 105 * s, y + 5 * s), (x - 72 * s, y + 25 * s)], fill=col)   # tail fluff
    nx, ny = x + 42 * s, y - 30 * s; hx, hy = x + 70 * s + (12 * s if run else 0), y - 140 * s + (20 * s if run else 0)
    d.line([(nx, ny), (hx - 4 * s, hy + 10 * s)], fill=col, width=max(3, int(16 * s)))           # neck
    d.ellipse([hx - 16 * s, hy - 13 * s, hx + 16 * s, hy + 13 * s], fill=col)                    # head
    d.polygon([(hx + 12 * s, hy - 5 * s), (hx + 36 * s, hy + 2 * s), (hx + 12 * s, hy + 7 * s)], fill=col)   # beak
    d.ellipse([hx + 2 * s, hy - 6 * s, hx + 8 * s, hy], fill=PAPER)                              # eye
    for k, off in enumerate((0.0, math.pi)):
        a = math.sin(ph + off) * (0.6 if run else 0.0)
        kx, ky = x + (14 - 28 * k) * s + 30 * s * math.sin(a), y + 75 * s
        fx, fy = kx - 20 * s * math.sin(a) + 8 * s, y + 140 * s - (14 * s * max(0, math.sin(ph + off)) if run else 0)
        d.line([(x + (14 - 28 * k) * s, y + 25 * s), (kx, ky), (fx, fy)], fill=col, width=max(2, int(8 * s)), joint="curve")
        d.line([(fx, fy), (fx + 22 * s, fy)], fill=col, width=max(2, int(6 * s)))

def mammoth(d, x, y, s=1.0, col=(74, 50, 34), tusk=CREAM, ph=0.0):
    """flat woolly mammoth facing left; (x, y) = body centre."""
    for k, lx in enumerate((-80, -30, 50, 95)):
        sw = 10 * math.sin(ph + k * 1.6) * s
        d.rounded_rectangle([x + lx * s - 22 * s + sw, y + 20 * s, x + lx * s + 22 * s + sw, y + 150 * s], int(14 * s), fill=col)
    d.ellipse([x - 140 * s, y - 100 * s, x + 140 * s, y + 90 * s], fill=col)
    d.ellipse([x - 150 * s, y - 145 * s, x - 10 * s, y + 10 * s], fill=col)                      # head dome
    d.ellipse([x - 40 * s, y - 130 * s, x + 80 * s, y - 20 * s], fill=col)                       # shoulder hump
    d.line([(x - 140 * s, y - 40 * s), (x - 175 * s, y + 40 * s), (x - 168 * s, y + 120 * s), (x - 140 * s, y + 140 * s)], fill=col, width=int(30 * s), joint="curve")
    d.arc([x - 250 * s, y - 40 * s, x - 90 * s, y + 110 * s], 30, 200, fill=tusk, width=int(14 * s))
    d.ellipse([x - 112 * s, y - 72 * s, x - 100 * s, y - 60 * s], fill=CREAM)
    for k in range(14):                                                                     # shaggy fur strokes
        fx = x - 120 * s + k * 18 * s; d.line([(fx, y + 70 * s), (fx + 6 * s, y + 100 * s)], fill=(50, 34, 24), width=max(2, int(5 * s)))

def pyramid(d, cx, base, w, col=(210, 170, 100), dark=(160, 120, 60), u=1.0):
    h = w * 0.62 * u
    d.polygon([(cx - w / 2, base), (cx, base - h), (cx + w / 2, base)], fill=col)
    d.polygon([(cx, base - h), (cx + w / 2, base), (cx + w * 0.12, base)], fill=dark)
    for k in range(1, 9):
        yk = base - h * k / 9; half = w / 2 * (1 - k / 9); d.line([(cx - half, yk), (cx + half, yk)], fill=dark, width=2)

def gear(d, cx, cy, r, n, a, col=BRONZE, dark=BRONZE_D, spokes=4):
    pts = []
    for k in range(n * 4):
        ang = a + k * math.pi * 2 / (n * 4); rr = r + (14 if (k % 4) in (1, 2) else 0) * (r / 120) ** 0.4
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=col, outline=dark)
    d.ellipse([cx - r * 0.82, cy - r * 0.82, cx + r * 0.82, cy + r * 0.82], fill=dark)
    d.ellipse([cx - r * 0.74, cy - r * 0.74, cx + r * 0.74, cy + r * 0.74], fill=col)
    for k in range(spokes):
        ang = a + k * math.pi * 2 / spokes
        d.line([(cx, cy), (cx + r * 0.74 * math.cos(ang), cy + r * 0.74 * math.sin(ang))], fill=dark, width=max(3, int(r * 0.09)))
    d.ellipse([cx - r * 0.16, cy - r * 0.16, cx + r * 0.16, cy + r * 0.16], fill=dark)

# ---------------- beats ----------------
def b_cold(sc, lt, dur, t):
    img = paper(t); size = sc.get("size", 120); d = ImageDraw.Draw(img)
    for i, s in enumerate(sc["lines"]):
        text(img, s, size, W / 2, 360 + i * size * 1.2, RED if str(i) in sc.get("accent", {}) else INK, u=1.0 if i == 0 else ease((lt - i * 0.5) / 0.4))
    if "sub" in sc: pill(img, sc["sub"], 40, W / 2, 740, u=ease((lt - 0.8) / 0.4))
    return img

def b_chapter(sc, lt, dur, t):
    img = paper(t); d = ImageDraw.Draw(img); u = back(lt / 0.45)
    w_ = 700 * ease(lt / 0.5); rule(d, W / 2 - w_, W / 2 + w_, 230); rule(d, W / 2 - w_, W / 2 + w_, 820)
    text(img, "CHAPTER", 40, W / 2, 300, SEPIA, w="Bold", u=ease(lt / 0.3))
    text(img, f"No. {sc['ch']}", 260, W / 2, 470, RED, u=min(1, u))
    text(img, sc["title"], 92, W / 2, 680, INK, w="Black", u=ease((lt - 0.3) / 0.4))
    if "sub" in sc: text(img, sc["sub"], 42, W / 2, 770, SEPIA, w="SemiBold", u=ease((lt - 0.6) / 0.4))
    return img

def b_text(sc, lt, dur, t):
    img = paper(t); size = sc.get("size", 100)
    for i, s in enumerate(sc["lines"]):
        text(img, s, size, W / 2, sc.get("y", 420) + i * size * 1.25, RED if str(i) in sc.get("accent", {}) else INK, u=ease((lt - i * 0.35) / 0.4))
    d = ImageDraw.Draw(img); w_ = 260 * ease((lt - 0.4) / 0.5)
    yb = sc.get("y", 420) + len(sc["lines"]) * size * 1.25 + 10
    if w_ > 2: d.line([(W / 2 - w_, yb), (W / 2 + w_, yb)], fill=RED, width=5)
    return img

def b_counter(sc, lt, dur, t):
    img = paper(t)
    v = sc["from"] + (sc["to"] - sc["from"]) * eout((lt - 0.2) / max(0.6, sc.get("secs", 2.0)))
    text(img, sc.get("prefix", "") + f"{int(round(v)):,}" + sc.get("suffix", ""), sc.get("size", 240), W / 2, 420, RED, u=ease(lt / 0.3))
    text(img, sc["label"], 62, W / 2, 620, INK, w="Black", u=ease((lt - 0.3) / 0.4))
    if "note" in sc: text(img, sc["note"], 40, W / 2, 705, SEPIA, w="SemiBold", u=ease((lt - 0.9) / 0.4))
    return img

def b_headline(sc, lt, dur, t):
    img = paper(t); d = ImageDraw.Draw(img)
    p = eout(lt / 0.6); x0, x1 = 300, 1620; y0 = 90 + (1 - p) * 500; y1 = y0 + 820
    d.rectangle([x0 + 14, y0 + 16, x1 + 14, y1 + 16], fill=(170, 150, 115))
    d.rectangle([x0, y0, x1, y1], fill=(240, 232, 210), outline=(150, 128, 96), width=2)
    text(img, "The Sounds Fake Gazette", 92, W / 2, y0 + 90, INK, w="black", bg=(240, 232, 210))
    rule(d, x0 + 40, x1 - 40, y0 + 150)
    d.text((x0 + 44, y0 + 175), "SPECIAL EDITION", font=F(26, "Bold"), fill=SEPIA); d.text((x1 - 44, y0 + 175), "ONE PENNY", font=F(26, "Bold"), fill=SEPIA, anchor="ra")
    d.line([(x0 + 40, y0 + 215), (x1 - 40, y0 + 215)], fill=INK, width=2)
    pill(img, sc.get("kicker", "NEWS"), 40, W / 2, y0 + 285, u=ease((lt - 0.4) / 0.3))
    for i, s in enumerate(sc["head"]): text(img, s, 128, W / 2, y0 + 420 + i * 140, INK, u=ease((lt - 0.5 - i * 0.2) / 0.4), maxw=x1 - x0 - 100, bg=(240, 232, 210))
    yb = y0 + 420 + len(sc["head"]) * 140 - 30
    text(img, sc.get("sub", ""), 40, W / 2, yb, RED, w="Bold", u=ease((lt - 0.8) / 0.4), bg=(240, 232, 210))
    r = random.Random(3)
    for c in range(3):                                                                            # fake body columns
        cx0 = x0 + 50 + c * 410
        for k in range(6):
            yk = yb + 60 + k * 30
            if yk > y1 - 30: break
            d.rectangle([cx0, yk, cx0 + r.uniform(300, 380), yk + 10], fill=(196, 184, 156))
    return img

def b_clock(sc, lt, dur, t):
    img = paper(t); d = ImageDraw.Draw(img); cx, cy, R = 640, 520, 330
    d.ellipse([cx - R - 24, cy - R - 24, cx + R + 24, cy + R + 24], fill=(120, 86, 50)); d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(244, 236, 214), outline=INK, width=4)
    for k in range(60):
        a = k / 60 * 2 * math.pi - math.pi / 2; r0 = R - (40 if k % 5 == 0 else 20)
        d.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + (R - 8) * math.cos(a), cy + (R - 8) * math.sin(a))], fill=INK, width=6 if k % 5 == 0 else 2)
    for k, s in enumerate(["XII", "III", "VI", "IX"]):
        a = k * math.pi / 2 - math.pi / 2; d.text((cx + (R - 85) * math.cos(a), cy + (R - 85) * math.sin(a)), s, font=F(54, "serif"), fill=INK, anchor="mm")
    m = sc["from"] + (sc["to"] - sc["from"]) * ease((lt - 0.2) / max(0.8, dur - 0.8))
    hh, mm = (m / 60) % 12, m % 60
    ah = hh / 12 * 2 * math.pi - math.pi / 2; am = mm / 60 * 2 * math.pi - math.pi / 2
    if sc["to"] - sc["from"] > 5:                                                                # shaded war wedge
        a0 = math.degrees((sc["from"] % 60) / 60 * 2 * math.pi - math.pi / 2); a1 = math.degrees(am)
        if a1 > a0 + 0.5:
            ov = Image.new("L", (W, H), 0); ImageDraw.Draw(ov).pieslice([cx - R + 30, cy - R + 30, cx + R - 30, cy + R - 30], a0, a1, fill=90)
            img.paste(Image.new("RGB", (W, H), RED), (0, 0), ov); d = ImageDraw.Draw(img)
    d.line([(cx, cy), (cx + R * 0.5 * math.cos(ah), cy + R * 0.5 * math.sin(ah))], fill=INK, width=18)
    d.line([(cx, cy), (cx + R * 0.82 * math.cos(am), cy + R * 0.82 * math.sin(am))], fill=INK, width=10)
    d.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], fill=RED)
    text(img, f"{int(m // 60)}:{int(m % 60):02d} AM", 150, 1380, 430, RED)
    text(img, sc.get("label", ""), 56, 1380, 580, INK, w="Black", u=ease((lt - 0.3) / 0.4), maxw=820)
    text(img, "27 AUGUST 1896 · ZANZIBAR", 36, 1380, 660, SEPIA, w="SemiBold", u=ease((lt - 0.6) / 0.4))
    return img

def b_compare(sc, lt, dur, t):
    img = paper(t); d = ImageDraw.Draw(img); base = 900; scale = 12
    for i, (lab, val, mins, col) in enumerate(((sc["left"], sc["lv"], 45, SEPIA), (sc["right"], sc["rv"], 38, RED))):
        cx = 640 + i * 640; h = mins * scale * eout((lt - 0.2 - i * 0.5) / 1.0)
        d.rectangle([cx - 150, base - h, cx + 150, base], fill=col)
        if h > 60: text(img, val, 80, cx, base - h - 60, col, u=1)
        for k, s in enumerate(lab): text(img, s, 46, cx, 160 + k * 56, INK, w="Black", u=ease((lt - i * 0.5) / 0.4))
    d.line([(300, base), (1620, base)], fill=INK, width=5)
    return img

def b_emu(sc, lt, dur, t):
    m = sc.get("mode")
    img = paper(t); d = ImageDraw.Draw(img)
    # wheat field band
    d.rectangle([0, 860, W, H], fill=(206, 172, 96)); r = random.Random(2)
    for k in range(260):
        x = r.uniform(0, W); y = r.uniform(860, H); sw = 6 * math.sin(t * 2 + x * 0.01)
        d.line([(x, y), (x + sw, y - r.uniform(30, 60))], fill=(170, 130, 60), width=3)
    if m == "hook":
        for k, (ex, sc_) in enumerate(((1300, 1.6), (1690, 1.15), (990, 0.85))):
            emu(d, ex, 600 + (1.7 - sc_) * 150, sc_, ph=t * 6 + k, col=INK, run=False)
        for i, s in enumerate(sc["lines"]): text(img, s, 150, 480, 330 + i * 170, RED if i == 1 else INK, u=1.0 if i == 0 else ease((lt - 0.2) / 0.3), maxw=880)
        put_stamp(img, "1932", 470, 720, lt, at=0.4, size=96, rot=-6)
    elif m == "herd":
        r = random.Random(7); n = int(5 + 40 * ease(lt / 2.5))
        for k in range(n):
            x = r.uniform(80, W - 80); y = r.uniform(560, 860); s = 0.30 + (y - 560) / 300 * 0.35
            emu(d, x + 20 * math.sin(t * 0.7 + k), y, s, ph=0, col=(70 + int(30 * (1 - s)), 52, 36))
        pill(img, sc.get("label", ""), 52, W / 2, 230, u=ease((lt - 0.3) / 0.4))
        text(img, "WESTERN AUSTRALIA · 1932", 40, W / 2, 330, SEPIA, w="Bold", u=ease((lt - 0.6) / 0.4))
    elif m == "run":
        r = random.Random(9)
        for k in range(7):
            sp = r.uniform(380, 560); x = (r.uniform(-400, W) + sp * lt) % (W + 500) - 250; y = r.uniform(620, 800); s = 0.55 + (y - 620) / 180 * 0.25
            for q in range(4): d.line([(x - 100 * s - q * 30, y + 120 * s + q * 4), (x - 140 * s - q * 30, y + 120 * s + q * 4)], fill=(150, 120, 80), width=3)
            emu(d, x, y, s, ph=lt * 16 + k, col=INK, run=True)
        text(img, "TOO FAST.", 120, W / 2, 230, RED, u=ease(lt / 0.3)); text(img, "TOO SCATTERED.", 120, W / 2, 380, INK, u=ease((lt - 0.6) / 0.3))
    else:   # retreat
        emu(d, W / 2 + 260, 620, 1.6, col=INK)
        text(img, sc.get("label", "ROUND TWO"), 140, 640, 420, RED, u=ease(lt / 0.3))
        text(img, "8 Nov: soldiers withdrawn", 46, 640, 560, INK, w="Bold", u=ease((lt - 0.4) / 0.4))
        text(img, "12 Nov: sent back again", 46, 640, 630, INK, w="Bold", u=ease((lt - 0.9) / 0.4))
    return img

def b_tally(sc, lt, dur, t):
    img = paper(t); d = ImageDraw.Draw(img)
    text(img, "THE ARMY SENDS...", 64, W / 2, 180, SEPIA, w="Black", u=ease(lt / 0.3))
    for i, (num, lab) in enumerate(sc["rows"]):
        u = ease((lt - 0.4 - i * 0.9) / 0.35); y = 370 + i * 200
        if u <= 0: continue
        d.line([(360, y + 90), (1560, y + 90)], fill=(170, 140, 100), width=2)
        text(img, num, 150, 720, y, RED, anchor="rm", u=u); text(img, lab, 74, 780, y + 8, INK, w="Black", anchor="lm", u=u)
    return img

def b_quote(sc, lt, dur, t):
    img = paper(t); d = ImageDraw.Draw(img)
    d.text((70, 120), "“", font=F(400, "serif"), fill=(205, 170, 140))
    for i, s in enumerate(sc["lines"]): text(img, s, 92, W / 2 + 40, 360 + i * 130, INK if i != 1 else RED, u=ease((lt - 0.2 - i * 0.5) / 0.5))
    text(img, sc.get("by", ""), 42, W / 2, 790, SEPIA, w="SemiBold", u=ease((lt - 1.6) / 0.4))
    return img

def b_stamp(sc, lt, dur, t):
    img = paper(t); n = len(sc["lines"]); size = 70 if n > 1 else 84
    for i, s in enumerate(sc["lines"]): text(img, s, size, W / 2, 230 + i * size * 1.3, INK, w="Black", u=ease((lt - i * 0.25) / 0.35))
    put_stamp(img, sc["stamp"], W / 2, 290 + n * size * 1.3 + 170, lt, at=0.5 + n * 0.25, size=170)
    return img

LIQ = {"beer": ((120, 66, 22), (236, 220, 180)), "molasses": ((46, 24, 12), (110, 66, 36))}
def street(d, base=880):
    r = random.Random(4); x = 0
    while x < W:
        w_ = r.uniform(160, 260); h_ = r.uniform(260, 460)
        d.rectangle([x, base - h_, x + w_ - 8, base], fill=(150, 120, 88)); d.polygon([(x - 6, base - h_), (x + w_ / 2, base - h_ - 50), (x + w_ - 2, base - h_)], fill=(120, 92, 66))
        for wy in range(int(base - h_ + 40), base - 80, 90):
            for wx in range(int(x + 28), int(x + w_ - 50), 70): d.rectangle([wx, wy, wx + 34, wy + 50], fill=(90, 70, 52))
        x += w_
    d.rectangle([0, base, W, H], fill=(120, 100, 80))

def wavepoly(front, base, height, t, amp=18):
    pts = [(0, base)]
    for x in range(0, int(max(0, front)) + 1, 20):
        k = x / max(1, front); hh = height * (0.65 + 0.35 * k ** 2) * min(1, (front - x) / 120 + 0.75)
        pts.append((x, base - hh + amp * math.sin(x * 0.02 - t * 5)))
    pts += [(front + height * 0.4, base)]
    return pts

def b_wave(sc, lt, dur, t):
    img = paper(t); d = ImageDraw.Draw(img); col, foam = LIQ[sc["liquid"]]; m = sc.get("mode")
    if m == "burst":
        street(d, 880)
        vx, vy = 240, 560; crack = ease((lt - 0.2) / 0.4)
        d.rounded_rectangle([vx - 150, vy - 260, vx + 150, vy + 320], 40, fill=(110, 72, 40))
        for k in range(5): d.line([(vx - 150, vy - 200 + k * 120), (vx + 150, vy - 200 + k * 120)], fill=(50, 40, 34), width=12)
        if crack > 0: d.line([(vx + 150, vy - 100), (vx + 110, vy), (vx + 150, vy + 80)], fill=PAPER, width=8)
        front = 300 + 1700 * eout((lt - 0.4) / max(1.5, dur - 0.6))
        if lt > 0.4:
            d.polygon(wavepoly(front, 880, 260, t), fill=col); d.line(wavepoly(front, 880, 260, t)[1:-1], fill=foam, width=14)
        pill(img, sc.get("label", ""), 50, W / 2, 140, u=ease((lt - 0.5) / 0.4))
    elif m == "height":
        base, ppm = 900, 92; street(d, base)
        hm = sc.get("h", 4.6); hp = hm * ppm * eout((lt - 0.2) / 1.6); front = 1500 * eout((lt - 0.1) / 1.4) + 200
        if sc.get("bus"):                                                                       # double-decker bus 4.4 m reference
            bx = 1430; d.rounded_rectangle([bx, base - 4.4 * ppm, bx + 440, base - 20], 20, fill=(150, 40, 34))
            for row in (0, 1):
                for k in range(5): d.rectangle([bx + 25 + k * 82, base - 4.4 * ppm + 30 + row * 190, bx + 85 + k * 82, base - 4.4 * ppm + 120 + row * 190], fill=(230, 220, 190))
            for wx in (bx + 80, bx + 360): d.ellipse([wx - 40, base - 60, wx + 40, base + 20], fill=INK)
            text(img, "BUS ≈ 4.4 m", 32, bx + 220, base + 50, INK, w="Bold")
        fx = min(front, 1180)
        pts = [(0, base)] + [(x, base - hp * (1 - 0.15 * (x / 1180) ** 3) + 14 * math.sin(x * 0.015 - t * 4)) for x in range(0, int(fx) + 1, 20)]
        pts += [(fx + hp * 0.12, base - hp * 0.55), (fx + hp * 0.25, base)]
        d.polygon(pts + [(0, base)], fill=col); d.line(pts[1:-2], fill=foam, width=12)
        rx_ = 1040; d.line([(rx_, base), (rx_, base - hp)], fill=CREAM, width=6)
        for k in range(int(hm) + 1): d.line([(rx_ - 18, base - k * ppm), (rx_ + 18, base - k * ppm)], fill=CREAM, width=4)
        d.line([(rx_ - 40, base - hp), (rx_ + 40, base - hp)], fill=RED, width=8)
        text(img, sc.get("label", ""), 90, 760, max(130, base - hp - 90), RED, w="Black")
    else:   # settle
        street(d, 880)
        lvl = 880 - 120; pts = [(0, H)] + [(x, lvl + 10 * math.sin(x * 0.01 - t * 0.6)) for x in range(0, W + 21, 20)] + [(W, H)]
        d.polygon(pts, fill=col)
        for k in range(10):
            x = (k * 230 + t * 10) % W; d.line([(x, lvl + 30), (x + 140, lvl + 26)], fill=foam, width=6)
        pill(img, sc.get("label", ""), 50, W / 2, 140, u=ease((lt - 0.3) / 0.4))
        text(img, "21 lives lost · about 150 injured", 44, W / 2, 240, INK, w="Bold", u=ease((lt - 0.6) / 0.4))
    return img

def b_vending(sc, lt, dur, t):
    img = paper(t); d = ImageDraw.Draw(img); m = sc.get("mode")
    bx0, by0, bx1, by1 = 240, 200, 820, 760; ink = INK
    d.rectangle([bx0, by0, bx1, by1], outline=ink, width=6)
    d.rectangle([bx0 + 6, by0 + 280, bx1 - 6, by1 - 6], fill=(150, 176, 190))                # water tank
    for k in range(6): d.line([(bx0 + 30 + k * 90, by0 + 310), (bx0 + 80 + k * 90, by0 + 310)], fill=(220, 236, 240), width=3)
    d.rectangle([480, by0 - 20, 580, by0 + 6], fill=PAPER, outline=ink, width=4)              # coin slot
    px, py = 640, 330                                                                          # lever pivot
    tilt = {"coin": 0.0, "pour": 1.0, "reset": 1.0 - ease((lt - 0.6) / 0.6), "idle": 0.0}[m]
    if m == "coin": tilt = ease((lt - 1.1) / 0.3) * 0.0
    a = -0.28 + 0.56 * tilt                                                                     # left pan end goes down when tilt
    L1, L2 = 200, 130
    lx, ly = px - L1 * math.cos(a), py + L1 * math.sin(a); rx, ry = px + L2 * math.cos(a), py - L2 * math.sin(a)
    d.line([(lx, ly), (rx, ry)], fill=ink, width=10); d.polygon([(px - 22, py + 40), (px + 22, py + 40), (px, py)], fill=ink)
    d.rectangle([lx - 50, ly - 6, lx + 30, ly + 6], fill=ink)                                   # coin pan
    # rod from right end down to the plug at the bottom outlet
    plug_y = by1 - 40 - 50 * tilt
    d.line([(rx, ry), (rx, plug_y - 20)], fill=SEPIA, width=5)
    d.rectangle([rx - 24, plug_y - 20, rx + 24, plug_y + 20], fill=RED)
    d.rectangle([rx - 30, by1, rx + 30, by1 + 50], fill=ink)                                    # spout
    cup_x = rx; d.polygon([(cup_x - 70, 850), (cup_x + 70, 850), (cup_x + 52, 925), (cup_x - 52, 925)], fill=(200, 150, 80), outline=ink)
    # coin
    if m == "coin":
        cy_ = by0 - 120 + (ly - 18 - (by0 - 120)) * ease((lt - 0.3) / 0.8); cxp = 530 + (lx - 10 - 530) * ease((lt - 0.3) / 0.8)
        d.ellipse([cxp - 30, cy_ - 12, cxp + 30, cy_ + 12], fill=GOLD, outline=ink, width=3)
    elif m == "pour":
        d.ellipse([lx - 40, ly - 30, lx + 20, ly - 6], fill=GOLD, outline=ink, width=3)
        for k in range(6):
            yk = by1 + 55 + ((lt * 300 + k * 30) % 80); d.ellipse([rx - 7, yk - 10, rx + 7, yk + 10], fill=(120, 170, 200))
    elif m == "reset":
        s_ = ease((lt - 0.1) / 0.5); cxp, cy_ = lx - 10 - 120 * s_, ly - 18 + 300 * s_ ** 2
        d.ellipse([cxp - 30, cy_ - 12, cxp + 30, cy_ + 12], fill=GOLD, outline=ink, width=3)
    labels = ["1  COIN DROPS IN", "2  LEVER TIPS", "3  PLUG LIFTS", "4  WATER FLOWS"]
    for i, s_ in enumerate(labels):
        on = {"coin": i == 0, "pour": i in (1, 2, 3), "reset": False, "idle": True}[m]
        d.text((1080, 380 + i * 100), s_, font=F(50, "Black"), fill=RED if on else (170, 145, 110), anchor="lm")
    text(img, "HERO'S COIN MACHINE", 60, 1400, 190, INK, w="Black")
    text(img, "as described in his book Pneumatica", 34, 1400, 255, SEPIA, w="SemiBold")
    if m == "idle":
        text(img, "NO PRIEST NEEDED", 72, 1400, 830, RED, u=ease((lt - 0.3) / 0.4))
    return img

def gearset(d, t, ox=0, oy=0, k=1.0):
    gear(d, 760 + ox, 540 + oy, 230 * k, 40, t * 0.25, spokes=4)
    gear(d, 760 + ox + 330 * k, 540 + oy - 160 * k, 120 * k, 21, -t * 0.25 * 40 / 21 + 0.07, spokes=3)
    gear(d, 760 + ox + 300 * k, 540 + oy + 230 * k, 95 * k, 17, -t * 0.25 * 40 / 17, col=(150, 104, 52))
    gear(d, 760 + ox + 470 * k, 540 + oy - 10 * k, 70 * k, 12, t * 0.25 * 40 / 12 * 21 / 40, col=(190, 138, 76), spokes=3)

def b_gears(sc, lt, dur, t):
    m = sc.get("mode")
    img = paper(t); d = ImageDraw.Draw(img)
    if m == "reveal":
        u = ease((lt - 0.2) / 1.2)
        gearset(d, t, ox=-60)
        cov = Image.new("L", (W, H), 0); ImageDraw.Draw(cov).ellipse([300, 180, 1400, 900], fill=int(255 * (1 - u)))
        img.paste(Image.new("RGB", (W, H), (96, 110, 84)), (0, 0), cov.filter(ImageFilter.GaussianBlur(30)))
        text(img, "BRONZE GEARS", 80, W / 2, 140, INK, w="Black", u=ease((lt - 0.8) / 0.4))
    elif m == "label":
        gearset(d, t, ox=-380, k=0.85)
        for i, s in enumerate(sc.get("lines", [])): text(img, s, 72 if i == 0 else 56, 1440, 450 + i * 110, RED if i == 0 else INK, w="serif" if i == 0 else "Black", u=ease((lt - 0.3 - i * 0.4) / 0.4), maxw=820)
    else:   # sky dial
        cx, cy, R = 640, 540, 380
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(198, 150, 90), outline=BRONZE_D, width=8)
        d.ellipse([cx - R + 60, cy - R + 60, cx + R - 60, cy + R - 60], fill=(220, 186, 130), outline=BRONZE_D, width=4)
        for k in range(12):
            a = k * math.pi / 6; d.line([(cx + (R - 60) * math.cos(a), cy + (R - 60) * math.sin(a)), (cx + R * math.cos(a), cy + R * math.sin(a))], fill=BRONZE_D, width=4)
        for k, (rr, sp, col, sz) in enumerate(((300, 0.08, (230, 170, 40), 34), (240, 1.0, (235, 235, 225), 26), (180, 0.32, (200, 90, 60), 14), (130, 0.2, (240, 220, 160), 12))):
            a = t * sp + k; px_, py_ = cx + rr * math.cos(a), cy + rr * math.sin(a)
            d.line([(cx, cy), (px_, py_)], fill=BRONZE_D, width=4); d.ellipse([px_ - sz, py_ - sz, px_ + sz, py_ + sz], fill=col, outline=INK, width=2)
        d.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=INK)
        items = ["SUN & MOON", "THE PLANETS", "ECLIPSES", "MOON PHASES", "OLYMPIC GAMES"]
        for i, s in enumerate(items):
            u = ease((lt - 0.3 - i * dur / 7) / 0.35)
            if u > 0: d.text((1180, 300 + i * 110), "✓", font=F(56, "Black"), fill=RED, anchor="lm"); text(img, s, 60, 1260, 300 + i * 110, INK, w="Black", anchor="lm", u=u)
    return img

def pole(d, x, base=880, h=520):
    d.rectangle([x - 10, base - h, x + 10, base], fill=(96, 70, 46)); d.rectangle([x - 70, base - h + 20, x + 70, base - h + 34], fill=(96, 70, 46))
    for k in (-50, 0, 50): d.ellipse([x + k - 8, base - h + 6, x + k + 8, base - h + 22], fill=CREAM)

def b_wire(sc, lt, dur, t):
    m = sc.get("mode"); img = paper(t); d = ImageDraw.Draw(img)
    d.line([(0, 880), (W, 880)], fill=SEPIA, width=4)
    poles = [260, 760, 1160, 1660]
    for x in poles: pole(d, x)
    wy = 880 - 520 + 14
    for i in range(len(poles) - 1):
        x0, x1 = poles[i], poles[i + 1]; pts = [(x0 + (x1 - x0) * k / 20, wy + 40 * math.sin(math.pi * k / 20)) for k in range(21)]
        d.line(pts, fill=INK, width=3)
    def wire_xy(f):
        x = 260 + 1400 * f; i = min(2, int((x - 260) / 1400 * 3)); x0, x1 = poles[i], poles[i + 1]; k = (x - x0) / (x1 - x0)
        return x, wy + 40 * math.sin(math.pi * k)
    if m == "fax":
        for q in range(3):
            f = (lt * 0.5 + q / 3) % 1; x, y = wire_xy(f); d.ellipse([x - 10, y - 10, x + 10, y + 10], fill=RED)
        for side, sx in ((0, 330), (1, 1260)):
            d.rectangle([sx, 560, sx + 300, 840], fill=(246, 240, 224), outline=INK, width=3)
            prog = 1.0 if side == 0 else ease((lt - 0.3) / max(1.0, dur - 1.0))
            sh = Image.new("L", (300, 280), 0); sd = ImageDraw.Draw(sh)
            sd.polygon([(60, 200), (150, 90), (240, 200)], fill=255); sd.rectangle([80, 200, 220, 250], fill=255); sd.ellipse([210, 40, 260, 90], fill=255)
            cut = int(280 * prog); sh2 = Image.new("L", (300, 280), 0); sh2.paste(sh.crop((0, 0, 300, cut)), (0, 0))
            img.paste(Image.new("RGB", (300, 280), INK), (sx, 560), sh2); d = ImageDraw.Draw(img)
            if side == 1 and prog < 1: d.line([(sx, 560 + cut), (sx + 300, 560 + cut)], fill=RED, width=3)
        text(img, "SENT", 40, 480, 520, SEPIA, w="Black"); text(img, "RECEIVED", 40, 1410, 520, SEPIA, w="Black")
        pill(img, sc.get("label", ""), 50, W / 2, 170, u=ease((lt - 0.2) / 0.4))
    elif m == "sparks":
        r = random.Random(int(t * 15))
        for _ in range(7):
            x, y = wire_xy(r.random()); pts = [(x, y)]
            for k in range(5): pts.append((pts[-1][0] + r.uniform(-30, 30), pts[-1][1] + r.uniform(10, 34)))
            d.line(pts, fill=GOLD, width=4)
        for sx in (330, 1260):                                                                  # stations with paper tape catching fire
            d.rectangle([sx, 640, sx + 300, 840], fill=(150, 112, 70), outline=INK, width=3)
            fl = 30 + 12 * math.sin(t * 20 + sx); d.polygon([(sx + 120, 640), (sx + 150, 640 - fl * 2), (sx + 180, 640)], fill=(236, 120, 30))
            d.polygon([(sx + 135, 640), (sx + 150, 640 - fl), (sx + 165, 640)], fill=(250, 220, 90))
        pill(img, sc.get("label", ""), 56, W / 2, 170, u=ease((lt - 0.2) / 0.4))
    else:   # nobattery
        for q in range(3):
            f = (lt * 0.45 + q / 3) % 1; x, y = wire_xy(f); d.ellipse([x - 10, y - 10, x + 10, y + 10], fill=(60, 170, 110))
        bx, by = 480, 720
        d.rectangle([bx - 110, by - 60, bx + 110, by + 60], fill=(120, 110, 100), outline=INK, width=5); d.rectangle([bx + 110, by - 20, bx + 130, by + 20], fill=INK)
        d.text((bx, by), "+  −", font=F(50, "Black"), fill=CREAM, anchor="mm")
        if lt > 0.5: d.line([(bx - 140, by - 90), (bx + 140, by + 90)], fill=RED, width=14); d.line([(bx - 140, by + 90), (bx + 140, by - 90)], fill=RED, width=14)
        text(img, "BOSTON", 44, 260, 920, INK, w="Black"); text(img, "PORTLAND", 44, 1660, 920, INK, w="Black")
        pill(img, sc.get("label", ""), 52, W / 2, 170, u=ease((lt - 0.2) / 0.4))
        text(img, "messages still went through", 46, W / 2, 270, SEPIA, w="Bold", u=ease((lt - 1.0) / 0.4))
    return img

def b_sun(sc, lt, dur, t):
    m = sc.get("mode")
    if m == "flare":
        img = dark_img(t, "flare", (16, 12, 8), (34, 26, 18)); cx, cy, R = 700, 540, 330
        halo(img, cx, cy, R * 1.1, (220, 140, 60), 110); d = ImageDraw.Draw(img)
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(236, 170, 80)); d.ellipse([cx - R * 0.9, cy - R * 0.9, cx + R * 0.9, cy + R * 0.9], fill=(244, 190, 100))
        for (sx, sy, s) in ((-80, -40, 26), (-40, -10, 14), (60, 60, 20)): d.ellipse([cx + sx - s, cy + sy - s, cx + sx + s, cy + sy + s], fill=(120, 70, 30))
        fl = ease((lt - 0.6) / 0.4) * (1 - 0.5 * ease((lt - 3.0) / 1.5))
        if fl > 0:
            for (sx, sy) in ((-60, -60), (-20, -25)): halo(img, cx + sx, cy + sy, 40, (255, 255, 240), int(255 * fl))
        img = bloom(img, 0.6)
        text(img, "FIRST SOLAR FLARE", 76, 1420, 440, CREAM, w="serif", bg=(20, 16, 12), maxw=820)
        text(img, "EVER OBSERVED", 76, 1420, 530, (240, 190, 100), w="serif", bg=(20, 16, 12))
        text(img, sc.get("label", ""), 40, 1420, 630, (200, 180, 150), w="Bold", u=ease((lt - 0.5) / 0.4), bg=(20, 16, 12))
        return img
    img = dark_img(t, "night")
    cur = Image.new("RGB", (W, H), (0, 0, 0)); a = np.zeros((H, W), np.float32)
    xs = np.arange(W, dtype=np.float32)
    for k, (col, base_y, amp) in enumerate((((60, 230, 140), 330, 70), ((80, 255, 170), 420, 50), ((220, 70, 110), 230, 60))):
        top = base_y + amp * np.sin(xs * 0.004 + t * 0.6 + k * 2) + 20 * np.sin(xs * 0.013 - t * 0.9)
        band = np.clip(1 - np.abs(yy - top[None, :]) / (160 if k < 2 else 120), 0, 1) ** 1.6 * (0.6 + 0.4 * np.sin(xs * 0.05 + t * 2 + k))[None, :]
        band *= (yy < top[None, :] + 40)
        c = np.asarray(cur).astype(np.float32) + band[..., None] * np.array(col, np.float32) * 0.9
        cur = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8))
    img = Image.fromarray(np.clip(np.asarray(img).astype(np.int32) + np.asarray(cur).astype(np.int32), 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    d.polygon([(0, 900), (300, 820), (620, 870), (980, 800), (1400, 860), (1920, 810), (1920, 1080), (0, 1080)], fill=(8, 8, 12))
    for x in (300, 800, 1300): d.rectangle([x - 6, 600, x + 6, 900], fill=(8, 8, 12)); d.rectangle([x - 50, 610, x + 50, 620], fill=(8, 8, 12))
    img = bloom(img, 0.4)
    pill(img, sc.get("label", ""), 44, W / 2, 160, u=ease((lt - 0.4) / 0.4))
    return img

def b_mammoth(sc, lt, dur, t):
    m = sc.get("mode"); img = paper(t); d = ImageDraw.Draw(img)
    if m == "pyramid":
        d.rectangle([0, 840, W, H], fill=(214, 186, 130))
        pyramid(d, W / 2, 840, 820, u=eout((lt - 0.1) / 1.0))
        text(img, "THE GREAT PYRAMID", 80, W / 2, 130, INK, w="Black", u=ease(lt / 0.3))
        pill(img, sc.get("label", ""), 52, W / 2, 240, u=ease((lt - 0.5) / 0.4))
    elif m == "both":
        d.rectangle([0, 840, W, H], fill=(214, 186, 130)); pyramid(d, 520, 840, 760)
        d.line([(W / 2 + 40, 300), (W / 2 + 40, 980)], fill=SEPIA, width=3)
        d.rectangle([W / 2 + 42, 300, W, 840], fill=(226, 230, 228)); d.rectangle([W / 2 + 42, 840, W, H], fill=(236, 240, 240))
        mx = 1700 - 240 * eout((lt - 0.3) / 1.6); mammoth(d, mx, 640, 0.95, ph=lt * 5)
        text(img, "≈ 2560 BC · EGYPT", 44, 520, 260, INK, w="Black"); text(img, "SAME ERA · SIBERIA", 44, 1440, 260, INK, w="Black", u=ease((lt - 0.4) / 0.4))
        put_stamp(img, "SAME TIME", W / 2 + 40, 120, lt, at=1.2, size=80, rot=-4)
    else:   # island map
        d.rectangle([0, 0, W, H], fill=(170, 190, 196))
        for k in range(14): d.arc([-200 + k * 160, 700 + (k % 3) * 40, k * 160, 760 + (k % 3) * 40], 200, 340, fill=(140, 166, 176), width=3)
        d.polygon([(0, 1080), (0, 820), (300, 860), (600, 800), (900, 870), (1300, 830), (1700, 880), (1920, 850), (1920, 1080)], fill=(214, 198, 160))
        text(img, "SIBERIA", 60, 960, 905, SEPIA, w="Black", bg=(214, 198, 160))
        ix, iy = 1100, 430
        d.polygon([(ix - 260, iy + 40), (ix - 180, iy - 70), (ix + 20, iy - 100), (ix + 240, iy - 60), (ix + 280, iy + 40), (ix + 120, iy + 110), (ix - 120, iy + 100)], fill=(226, 214, 180), outline=SEPIA)
        mammoth(d, ix, iy - 10, 0.32)
        text(img, "WRANGEL ISLAND", 50, ix, iy + 170, INK, w="Black", bg=(170, 190, 196))
        pill(img, sc.get("label", ""), 40, W / 2, 140, u=ease((lt - 0.4) / 0.4))
    return img

def b_timeline(sc, lt, dur, t):
    img = paper(t); d = ImageDraw.Draw(img); y0, x0, x1 = 560, 160, 1760; a, b = sc["span"]; bc = sc.get("bc", False)
    X = lambda yr: x0 + (yr - a) / (b - a) * (x1 - x0)
    p = eout(lt / 0.8); d.line([(x0, y0), (x0 + (x1 - x0) * p, y0)], fill=INK, width=6)
    if p > 0.95: d.polygon([(x1, y0 - 16), (x1 + 30, y0), (x1, y0 + 16)], fill=INK)
    step = 10 if b - a <= 60 else (200 if b - a <= 1500 else 1000)
    for yr in range(int(math.ceil(a / step) * step), b + 1, step):
        x = X(yr)
        if x > x0 + (x1 - x0) * p: break
        d.line([(x, y0 - 12), (x, y0 + 12)], fill=SEPIA, width=3); d.text((x, y0 + 40), fmtyear(yr, bc) if yr != 0 else "0", font=F(26, "SemiBold"), fill=SEPIA, anchor="mm")
    for i, (yr, lab) in enumerate(sc["points"]):
        u = ease((lt - 0.5 - i * 0.6) / 0.35)
        if u <= 0: continue
        x = X(yr); up = i % 2 == 0; col = RED
        d.line([(x, y0), (x, y0 + (-170 if up else 170) * u)], fill=col, width=4); d.ellipse([x - 16, y0 - 16, x + 16, y0 + 16], fill=col)
        ty = y0 - 250 if up else y0 + 250; x = min(max(x, 300), W - 300)
        text(img, lab, 56, x, ty, INK, w="Black", u=u, maxw=560); text(img, fmtyear(yr, bc), 48, x, ty + (60 if up else 60), RED, u=u)
    for j, (ya, yb, lab) in enumerate(sc.get("brackets", [])):
        u = ease((lt - 0.6 - len(sc["points"]) * 0.6 - j * 0.6) / 0.4)
        if u <= 0: continue
        xa, xb = X(ya), X(ya) + (X(yb) - X(ya)) * u; by = y0 + (110 if j % 2 == 0 else -110) * (1 if len(sc["points"]) < 3 else 1)
        by = y0 - 110 if (len(sc["points"]) >= 3 and j == 1) else by
        d.line([(xa, by), (xb, by)], fill=SEPIA, width=5); d.line([(xa, by - 16), (xa, by + 16)], fill=SEPIA, width=5); d.line([(xb, by - 16), (xb, by + 16)], fill=SEPIA, width=5)
        if u > 0.9:
            tw = d.textlength(lab, font=F(40, "Black")); mx = (xa + xb) / 2
            d.rectangle([mx - tw / 2 - 14, by - 30, mx + tw / 2 + 14, by + 30], fill=PAPER); d.text((mx, by), lab, font=F(40, "Black"), fill=SEPIA, anchor="mm")
    return img

def b_recap(sc, lt, dur, t):
    img = paper(t); d = ImageDraw.Draw(img)
    text(img, sc.get("title", "QUICK RECAP"), 96, W / 2, 170, RED, u=1)
    n = len(sc["items"])
    for i, s in enumerate(sc["items"]):
        u = ease((lt - 0.3 - i * (dur - 1.0) / n) / 0.3); y = 360 + i * 140
        if u <= 0: continue
        d.rectangle([520, y - 34, 588, y + 34], outline=INK, width=5)
        if u > 0.6: d.line([(530, y), (552, y + 24), (600, y - 40)], fill=RED, width=10)
        text(img, s, 64, 640, y, INK, w="Black", anchor="lm", u=u, maxw=1100)
    return img

def b_outro(sc, lt, dur, t):
    img = paper(t); d = ImageDraw.Draw(img)
    text(img, sc.get("q", "Which one sounded the MOST fake?"), 84, W / 2, 300, INK)
    click = sc.get("click_at", 1.6); on = ease((lt - click) / 0.25); cx, cy, w_, h_ = W / 2, 560, 300, 130
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=RED if on > 0.5 else (150, 130, 104), outline=INK, width=6)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; d.ellipse([kx - h_ / 2 + 16, cy - h_ / 2 + 16, kx + h_ / 2 - 16, cy + h_ / 2 - 16], fill=CREAM)
    text(img, "FAKE", 64, cx - w_ / 2 - 120, cy, INK if on < 0.5 else (170, 150, 120), w="Black"); text(img, "TRUE", 64, cx + w_ / 2 + 120, cy, RED if on >= 0.5 else (170, 150, 120), w="Black")
    pill(img, "SUBSCRIBE · NEW DEEP DIVE EVERY TUE & FRI", 42, W / 2, 780, u=ease((lt - click - 0.4) / 0.4))
    return img

BEATS = dict(cold=b_cold, chapter=b_chapter, text=b_text, counter=b_counter, headline=b_headline, clock=b_clock, compare=b_compare,
             emu=b_emu, tally=b_tally, quote=b_quote, stamp=b_stamp, wave=b_wave, vending=b_vending, gears=b_gears, wire=b_wire,
             sun=b_sun, mammoth=b_mammoth, timeline=b_timeline, recap=b_recap, outro=b_outro)
DARK = ("sun",)

# ---------------- narration & score (music-box / harpsichord-ish plucks over warm pad) ----------------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.42, tail=1.5)
n = len(voice); tt = np.arange(n) / SR; music = np.zeros(n, np.float32)
pads = [[110.0, 164.81, 220.0, 277.18], [98.0, 146.83, 196.0, 246.94], [87.31, 130.81, 174.61, 220.0], [82.41, 123.47, 164.81, 207.65]]
seg = 6.0
for i in range(int(total / seg) + 1):
    a, b = int(i * seg * SR), min(int((i + 1.4) * seg * SR), n)
    if a >= n: break
    lt = tt[a:b] - i * seg; env = np.clip(lt / 2.5, 0, 1) * np.clip((seg * 1.4 - lt) / 2.5, 0, 1)
    for f in pads[i % 4]: music[a:b] += (np.sin(2 * np.pi * f * lt) + 0.3 * np.sin(2 * np.pi * f * 1.004 * lt)) * env * 0.026
beat = np.zeros(n, np.float32)
arp = [(220.0, 329.63, 440.0, 329.63), (196.0, 293.66, 392.0, 293.66), (174.61, 261.63, 349.23, 261.63), (164.81, 246.94, 329.63, 246.94)]
for k in range(int(total / 0.5)):
    f = arp[int(k * 0.5 / seg) % 4][k % 4]
    place(beat, k * 0.5, tone(f * 2, 0.6, decay=7, harm=(1, 2, 3)), 0.012)
music += beat
hook_hit(music, 0.35)
for ln in spec["lines"]:
    if ln["scene"]["type"] == "chapter": place(music, ln["_s"], tone(55, 1.2, decay=3, harm=(1, 2)), 0.25); whoosh(music, ln["_s"], 0.16)
    if ln["scene"]["type"] == "stamp": place(music, ln["_s"] + 0.5 + 0.25 * len(ln["scene"]["lines"]), tone(70, 0.4, decay=14, harm=(1, 2, 3)), 0.35)
for ln in spec["lines"][1:]: whoosh(music, ln["_s"], 0.05)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.35)

cur_ch = 0
for ln in spec["lines"]:
    if ln["scene"]["type"] == "chapter": cur_ch = ln["scene"]["ch"]
    ln["_ch"] = cur_ch
NCH = max(ln["_ch"] for ln in spec["lines"])
def _ts(x): x = int(x); return f"{x // 60}:{x % 60:02d}"
_chap = ["0:00 Intro"] + [f"{_ts(ln['_s'])} {ln['scene']['ch']}. {ln['scene']['title'].title()}" for ln in spec["lines"] if ln["scene"]["type"] == "chapter"]
_rc = [ln["_s"] for ln in spec["lines"] if ln["scene"]["type"] == "recap"]
if _rc: _chap.append(f"{_ts(_rc[0])} Recap")
open(work + "_chapters.txt", "w").write("\n".join(_chap) + "\n")

groups = caption_groups(words, 6)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 46
    while d.textlength(" ".join(ws), font=F(size, "Bold")) > W - 400 and size > 30: size -= 2
    f = F(size, "Bold"); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 975
    d.rectangle([x - 28, y - 14, x + tw + 28, y + size + 18], fill=INK)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=(255, 196, 80) if on else CREAM); x += d.textlength(w + " ", font=f)

def frame(t):
    ln = core.active_line(spec, t, lead=0.05) or spec["lines"][0]
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]; sc = ln["scene"]
    if t < 0.05: lt = 1.5                                                                       # frame 0 = full hook
    img = BEATS[sc["type"]](sc, lt, dur, t)
    img = film(img, t, dark=sc["type"] in DARK)
    d = ImageDraw.Draw(img)
    if ln["_ch"]: d.text((W - 60, 50), f"{ln['_ch']:02d} / {NCH:02d}", font=F(34, "Bold"), fill=RED, anchor="ra")
    d.rectangle([44, 40, 330, 92], fill=INK); d.text((62, 48), "SOUNDS FAKE  ?!", font=F(30, "Black"), fill=CREAM)
    caption(img, t)
    d.rectangle([0, H - 6, int(W * t / total), H], fill=RED)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","):
            Image.frombytes("RGB", (W, H), frame(float(tt_))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s")
    else:
        if os.environ.get("PART"):
            i_, n_ = map(int, os.environ["PART"].split("/")); N = int(total * FPS); a_, b_ = N * i_ // n_, N * (i_ + 1) // n_
            ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", f"{work}_part{i_}.mp4"], stdin=subprocess.PIPE)
            for fi in range(a_, b_): ff.stdin.write(frame(fi / FPS))
            ff.stdin.close(); ff.wait(); print("part done", i_); sys.exit(0)
        tmp = out_path[:-4] + ".part.mp4"
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                               "-i", "-", "-i", work + "_audio.wav", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p",
                               "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
        for fi in range(int(total * FPS)): ff.stdin.write(frame(fi / FPS))
        ff.stdin.close()
        if ff.wait() == 0: os.replace(tmp, out_path); print(f"done {total:.1f}s")
        else: raise SystemExit("ffmpeg failed")
