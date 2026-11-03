"""LONG-FORM (16:9, 1920x1080) — 'Sounds Fake: Deep Dive' space episode engine.
Cinematic dark-space motion graphics: parallax starfield, shaded planets, glow/bloom, big counters, chapter cards
'01 / 10', lower-third captions. Every line of the spec is a 'beat' with its own visual.
Usage: python3 engine/long/space_deep_dive.py spec.json out.mp4 [t1,t2,... preview]
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
def F(s, w="Black"): return ImageFont.truetype(f"{FD}InterDisplay-{w}.otf", int(s))
GOLD, ICE, WHITE, DIM, RED, BLUE = (255, 200, 90), (130, 210, 255), (240, 244, 255), (140, 150, 180), (255, 110, 80), (80, 140, 255)

# ---------------- background: nebula + 3 parallax star layers ----------------
def lowf(h, w, cell, seed):
    r = np.random.default_rng(seed); s = r.random((h // cell + 2, w // cell + 2)).astype(np.float32)
    return np.asarray(Image.fromarray((s * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255
neb = lowf(H, W, 260, 1) ** 2.4; neb2 = lowf(H, W, 380, 2) ** 3
BG = np.zeros((H, W, 3), np.float32) + np.array([3, 5, 14], np.float32)
BG += neb[..., None] * np.array([45, 20, 75], np.float32) + neb2[..., None] * np.array([10, 40, 70], np.float32)
STARS = [(rng.uniform(0, W), rng.uniform(0, H), rng.choice([0.7, 1.1, 1.8], p=[0.6, 0.3, 0.1]), rng.uniform(0, 6.3), rng.uniform(0.2, 1)) for _ in range(700)]
def space(t, zoom=0.0, drift=8.0):
    img = Image.fromarray(BG.astype(np.uint8)); d = ImageDraw.Draw(img)
    for (x, y, s, ph, dep) in STARS:
        px = ((x + drift * t * dep - W / 2) * (1 + zoom * dep)) % W; py = ((y - H / 2) * (1 + zoom * dep) + H / 2) % H
        c = int(255 * (0.55 + 0.45 * math.sin(t * 2 + ph)) * (0.4 + 0.6 * dep)); r = s * (0.7 + dep)
        if zoom > 0.03:
            vx, vy = (px - W / 2) * zoom * dep * 0.5, (py - H / 2) * zoom * dep * 0.5
            d.line([(px, py), (px - vx, py - vy)], fill=(c, c, min(255, c + 25)), width=max(1, int(r)))
        else: d.ellipse([px - r, py - r, px + r, py + r], fill=(c, c, min(255, c + 25)))
    return img

def bloom(img, k=0.7):
    a = np.asarray(img).astype(np.float32)
    s = Image.fromarray(np.clip((a - 150) * 1.5, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    b = np.asarray(s.filter(ImageFilter.GaussianBlur(8)).resize((W, H), Image.BILINEAR)).astype(np.float32)
    return Image.fromarray(np.clip(a + b * k, 0, 255).astype(np.uint8))

# ---------------- spheres ----------------
_geo = {}
def sphere(r, stops, rot=0.0, seed=0, light=(-0.6, -0.4, 0.7), ring=None, tilt=0.0, glow=None):
    """Shaded banded sphere as RGBA PIL image. stops: list of RGB tuples for bands."""
    key = (r, seed, tuple(stops), ring, round(tilt, 2))
    if key not in _geo:
        R = int(r * (2.3 if ring else 1.05)) + 2
        X, Y = np.meshgrid(np.arange(-R, R, dtype=np.float32), np.arange(-R, R, dtype=np.float32))
        xr = X * math.cos(tilt) + Y * math.sin(tilt); yr = -X * math.sin(tilt) + Y * math.cos(tilt)
        d2 = (xr ** 2 + yr ** 2) / r ** 2; disk = np.clip((1 - np.sqrt(d2)) * r * 0.8, 0, 1); z = np.sqrt(np.clip(1 - d2, 0, 1))
        L = np.array(light, np.float32); L /= np.linalg.norm(L)
        lam = np.clip((X / r) * L[0] + (Y / r) * L[1] + z * L[2], 0, 1)
        shade = 0.08 + 1.05 * lam ** 0.85
        rr = np.random.default_rng(seed); band = np.cumsum(rr.normal(0, 1, 400)); band = (band - band.min()) / (np.ptp(band) + 1e-6)
        st = np.array(stops, np.float32); idx = np.clip(band * (len(st) - 1), 0, len(st) - 1.001)
        cols = st[idx.astype(int)] * (1 - (idx % 1))[:, None] + st[np.minimum(idx.astype(int) + 1, len(st) - 1)] * (idx % 1)[:, None]
        v = np.clip(yr / r, -1, 1); bi = ((v * 0.5 + 0.5) * 399).astype(int)
        ulon = np.arcsin(np.clip(xr / (r * np.sqrt(np.clip(1 - v ** 2, 1e-4, 1))), -1, 1)) / math.pi + 0.5
        ringa = None
        if ring:
            rq = np.sqrt(xr ** 2 + (yr / 0.32) ** 2) / r
            ringa = (((rq > 1.3) & (rq < 2.2)) * (0.55 + 0.35 * np.sin(rq * 60))).astype(np.float32) * 0.85
        _geo[key] = (disk, shade, cols, bi, ulon, yr, ringa, R)
    disk, shade, cols, bi, ulon, yr, ringa, R = _geo[key]
    tex = cols[bi] * (0.94 + 0.12 * np.sin((ulon + rot) * 40 + bi * 0.05))[..., None]
    rgb = np.clip(tex * shade[..., None], 0, 255); a = disk.copy()
    if ringa is not None:
        back_ = ringa * (yr < 0) * (1 - disk); front = ringa * (yr >= 0)
        rgb = rgb * disk[..., None] + np.array([230, 215, 185]) * back_[..., None]; a = np.maximum(a, back_)
        rgb = rgb * (1 - front[..., None]) + np.array([230, 215, 185]) * front[..., None]; a = np.maximum(a, front)
    out = np.dstack([rgb, a * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")

def paste(img, spr, cx, cy):
    img.paste(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)), spr)

def halo(img, cx, cy, r, col, strength=160):
    g = Image.new("L", (W, H), 0); ImageDraw.Draw(g).ellipse([cx - r, cy - r, cx + r, cy + r], fill=strength)
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

def pill(img, s, size, x, y, fill=GOLD, ink=(14, 16, 30), u=1.0):
    if u <= 0: return
    d = ImageDraw.Draw(img); f = F(size, "Bold"); tw = d.textlength(s, font=f); y = y + (1 - u) * 16
    d.rounded_rectangle([x - tw / 2 - 26, y - size * 0.72, x + tw / 2 + 26, y + size * 0.72], int(size * 0.72), fill=fill)
    d.text((x, y), s, font=f, fill=ink, anchor="mm")

def fmtnum(v, kind):
    if kind == "int": return f"{int(round(v)):,}"
    if kind == "f1": return f"{v:,.1f}"
    if kind == "f2": return f"{v:,.2f}"
    return str(v)

# ---------------- beats ----------------
def b_cold(sc, lt, dur, t):
    img = space(t, zoom=0.12 * ease(lt / dur)); halo(img, W / 2, H / 2, 260, (60, 90, 160), 90)
    for i, s in enumerate(sc["lines"]):
        text(img, s, sc.get("size", 120), W / 2, 380 + i * sc.get("size", 120) * 1.15, GOLD if str(i) in sc.get("accent", {}) else WHITE, u=1.0 if i == 0 else ease((lt - i * 0.5) / 0.4))
    if "sub" in sc: pill(img, sc["sub"], 40, W / 2, 760, u=ease((lt - 0.8) / 0.4))
    return img

def b_chapter(sc, lt, dur, t):
    img = space(t, zoom=0.05 * ease(lt / dur))
    u = back(lt / 0.45)
    text(img, f"{sc['ch']:02d}", 330, W / 2, 420, GOLD, u=min(1, u))
    text(img, sc["title"], 84, W / 2, 660, WHITE, u=ease((lt - 0.3) / 0.4))
    if "sub" in sc: text(img, sc["sub"], 40, W / 2, 750, DIM, w="SemiBold", u=ease((lt - 0.6) / 0.4))
    return img

def b_text(sc, lt, dur, t):
    img = space(t)
    if "planet" in sc: p = sc["planet"]; paste(img, sphere(p.get("r", 220), [tuple(c) for c in p["stops"]], rot=t * 0.02, seed=p.get("seed", 0), ring=p.get("ring")), sc.get("px", 1500), sc.get("py", 560))
    for i, s in enumerate(sc["lines"]):
        text(img, s, sc.get("size", 96), sc.get("x", W / 2), sc.get("y", 420) + i * sc.get("size", 96) * 1.2, GOLD if str(i) in sc.get("accent", {}) else WHITE,
             anchor=sc.get("anchor", "mm"), u=ease((lt - i * 0.35) / 0.4), maxw=sc.get("maxw", W - 200))
    return img

def b_counter(sc, lt, dur, t):
    img = space(t)
    if "planet" in sc: p = sc["planet"]; paste(img, sphere(p.get("r", 200), [tuple(c) for c in p["stops"]], rot=t * 0.02, seed=p.get("seed", 0)), p.get("x", 1560), p.get("y", 540))
    v = sc["from"] + (sc["to"] - sc["from"]) * eout((lt - 0.2) / max(0.6, sc.get("secs", 2.0)))
    x = sc.get("x", W / 2)
    text(img, sc.get("prefix", "") + fmtnum(v, sc.get("fmt", "int")) + sc.get("suffix", ""), sc.get("size", 210), x, 450, GOLD, u=ease(lt / 0.3))
    text(img, sc["label"], 56, x, 640, WHITE, w="Bold", u=ease((lt - 0.3) / 0.4))
    if "note" in sc: text(img, sc["note"], 38, x, 720, DIM, w="SemiBold", u=ease((lt - 0.9) / 0.4))
    return img

def probe_icon(d, x, y, s=1.0, col=WHITE):
    d.ellipse([x - 26 * s, y - 26 * s, x + 26 * s, y + 26 * s], outline=col, width=max(2, int(5 * s)))      # dish
    d.line([(x, y), (x + 70 * s, y)], fill=col, width=max(2, int(4 * s)))
    d.rectangle([x + 20 * s, y - 10 * s, x + 40 * s, y + 10 * s], fill=col)
    d.line([(x + 30 * s, y), (x + 30 * s, y + 60 * s)], fill=col, width=max(2, int(3 * s)))
    d.line([(x + 30 * s, y), (x - 10 * s, y - 70 * s)], fill=col, width=max(2, int(3 * s)))

def b_probe(sc, lt, dur, t):
    img = space(t, drift=3); d = ImageDraw.Draw(img)
    sx, ex = 160, 330
    halo(img, sx, 560, 40, (255, 210, 120), 220); d = ImageDraw.Draw(img); d.ellipse([sx - 16, 544, sx + 16, 576], fill=(255, 230, 160))
    paste(img, sphere(22, [(40, 90, 200), (60, 140, 90), (230, 240, 255)], seed=3), ex, 560); text(img, "EARTH", 26, ex, 610, ICE, w="Bold")
    p = ease(lt / max(1.0, dur)); px = 560 + 1100 * p if sc.get("mode") == "fly" else 1660
    for k in range(int((px - 380) / 26)): d.ellipse([380 + k * 26 - 2, 558, 380 + k * 26 + 2, 562], fill=(90, 100, 140))
    probe_icon(d, px, 560, 1.4, GOLD)
    if sc.get("mode") == "signal":
        q = (lt * 0.35) % 1; lx = 1640 - (1640 - ex) * q
        halo(img, lx, 560, 30, ICE, 220); d = ImageDraw.Draw(img); d.ellipse([lx - 10, 550, lx + 10, 570], fill=WHITE)
        text(img, f"{int(24 * q):02d}:{int((24 * q % 1) * 60):02d} h", 70, W / 2, 360, ICE)
        pill(img, sc.get("label", "ONE-WAY SIGNAL: ABOUT 24 HOURS"), 38, W / 2, 800)
    else:
        km = sc.get("km", 25.9) * p
        text(img, f"{km:,.1f} BILLION KM", 96, W / 2, 340, GOLD)
        pill(img, sc.get("label", "LAUNCHED 1977"), 38, W / 2, 800, u=ease((lt - 0.5) / 0.4))
    return img

def b_record(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img); cx, cy = W / 2 - 330, 540
    halo(img, cx, cy, 300, (200, 150, 60), 110); d = ImageDraw.Draw(img)
    for k in range(40):
        r = 60 + k * 6.5; c = int(170 + 60 * math.sin(k * 0.9 + t * 3))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(c, int(c * 0.78), int(c * 0.35)), width=4)
    d.ellipse([cx - 55, cy - 55, cx + 55, cy + 55], fill=(110, 80, 30))
    for i, s in enumerate(sc["lines"]): text(img, s, 64, 1240, 420 + i * 90, GOLD if i == 0 else WHITE, u=ease((lt - i * 0.4) / 0.4))
    return img

def b_sunwalk(sc, lt, dur, t):
    img = space(t); cx, cy, R = 620, 540, 420
    halo(img, cx, cy, R * 1.2, (255, 150, 40), 120)
    d = ImageDraw.Draw(img); d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(255, 150, 40)); d.ellipse([cx - R * 0.7, cy - R * 0.7, cx + R * 0.7, cy + R * 0.7], fill=(255, 190, 80))
    d.ellipse([cx - R * 0.25, cy - R * 0.25, cx + R * 0.25, cy + R * 0.25], fill=(255, 240, 200))
    r = random.Random(4); pts = [(cx, cy)]; n = int(400 * ease(lt / max(1.5, dur * 0.7)))
    for _ in range(n):
        x, y = pts[-1]; a = r.uniform(0, 2 * math.pi); nx, ny = x + 26 * math.cos(a), y + 26 * math.sin(a)
        if (nx - cx) ** 2 + (ny - cy) ** 2 < (R * 0.95) ** 2: pts.append((nx, ny))
    if len(pts) > 1: d.line(pts, fill=(255, 255, 255), width=3)
    yrs = int(sc.get("years", 40000) * ease(lt / max(1.5, dur * 0.7)))
    text(img, f"{yrs:,} YEARS", 104, 1440, 420, GOLD)
    text(img, "core → surface", 46, 1440, 520, WHITE, w="SemiBold")
    if lt > dur * 0.7:
        u = ease((lt - dur * 0.7) / 0.6); text(img, "8 MINUTES", 80, 1440, 680, ICE, u=u); text(img, "surface → your face", 40, 1440, 760, WHITE, w="SemiBold", u=u)
    return img

def b_sunearth(sc, lt, dur, t):
    img = space(t); R = 900; cx, cy = -480, 540
    halo(img, cx + R, cy, 260, (255, 160, 60), 140)
    d = ImageDraw.Draw(img); d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(255, 160, 50)); d.ellipse([cx - R * 0.95, cy - R * 0.95, cx + R * 0.95, cy + R * 0.95], fill=(255, 185, 70))
    ex, ey, er = 1500, 540, 8
    paste(img, sphere(er, [(40, 90, 200), (60, 140, 90)], seed=3), ex, ey); text(img, "EARTH (to scale)", 30, ex, ey + 50, ICE, w="Bold")
    if sc.get("mode") == "mass":
        u = eout((lt - 0.3) / 1.2); v = 99.8 * u
        text(img, f"{v:.1f}%", 190, 1400, 330, GOLD); text(img, "OF ALL THE MASS IN THE SOLAR SYSTEM", 40, 1400, 450, WHITE, w="Bold", maxw=900)
    else:
        v = 1.3 * eout((lt - 0.3) / 1.5); text(img, f"{v:.1f} MILLION", 150, 1400, 330, GOLD); text(img, "EARTHS WOULD FIT INSIDE", 46, 1400, 440, WHITE, w="Bold")
    return img

def b_mountains(sc, lt, dur, t):
    img = space(t, drift=2); d = ImageDraw.Draw(img); base = 940; scale = 33          # px per km
    for km in range(0, 26, 5):
        y = base - km * scale; d.line([(120, y), (1800, y)], fill=(40, 46, 70), width=2); d.text((80, y), f"{km} km", font=F(26, "SemiBold"), fill=DIM, anchor="rm")
    u = eout((lt - 0.2) / 1.2)
    e_h = 8.85 * scale * u; d.polygon([(330, base), (520, base - e_h), (560, base - e_h * 0.9), (710, base)], fill=(150, 160, 185))
    d.polygon([(500, base - e_h * 0.93), (520, base - e_h), (560, base - e_h * 0.9), (540, base - e_h * 0.86)], fill=(250, 250, 255))
    text(img, "EVEREST 8.8 km", 34, 520, base + 50, WHITE, w="Bold")
    o_h = 22 * scale * eout((lt - 0.8) / 1.6)
    d.polygon([(820, base), (1240, base - o_h), (1380, base - o_h), (1800, base)], fill=(196, 90, 50))
    d.polygon([(1240, base - o_h), (1380, base - o_h), (1350, base - o_h + 14), (1270, base - o_h + 14)], fill=(120, 50, 30))
    text(img, "OLYMPUS MONS ~22 km", 34, 1310, base + 50, RED, w="Bold")
    if lt > 2.4: pill(img, sc.get("label", "≈ 2.5× EVEREST"), 42, 1310, base - o_h - 70, u=ease((lt - 2.4) / 0.4))
    return img

def b_planet(sc, lt, dur, t):
    img = space(t); p = sc
    if p.get("halo"): halo(img, p.get("x", W / 2), p.get("y", 540), p.get("r", 300) * 1.15, tuple(p["halo"]), 90)
    paste(img, sphere(p.get("r", 300), [tuple(c) for c in p["stops"]], rot=t * p.get("spin", 0.02), seed=p.get("seed", 0), ring=p.get("ring"), tilt=p.get("tilt", 0.0)), p.get("x", W / 2), p.get("y", 540))
    if p.get("axis"):
        d = ImageDraw.Draw(img); a = p.get("tilt", 0.0) + math.pi / 2; L = p.get("r", 300) * 1.45; x, y = p.get("x", W / 2), p.get("y", 540)
        d.line([(x - L * math.cos(a), y - L * math.sin(a)), (x + L * math.cos(a), y + L * math.sin(a))], fill=GOLD, width=5)
    for i, s in enumerate(p.get("lines", [])):
        text(img, s, p.get("size", 80), p.get("tx", 1440), p.get("ty", 420) + i * p.get("size", 80) * 1.2, GOLD if i == 0 else WHITE, u=ease((lt - 0.3 - i * 0.4) / 0.4), maxw=820)
    return img

def b_uranus(sc, lt, dur, t):
    img = space(t); cx, cy = 760, 560; halo(img, cx, cy, 60, (255, 210, 120), 230)
    d = ImageDraw.Draw(img); d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=(255, 235, 170)); d.ellipse([cx - 560, cy - 260, cx + 560, cy + 260], outline=(60, 70, 100), width=3)
    p = eout(lt / max(1.5, dur - 0.5)); a = math.pi + p * 2 * math.pi * 0.5
    ux, uy = cx + 560 * math.cos(a), cy + 260 * math.sin(a)
    lightdir = (cx - ux, cy - uy); n = math.hypot(*lightdir); L = (lightdir[0] / n, lightdir[1] / n, 0.25)
    paste(img, sphere(70, [(150, 220, 230), (120, 200, 215), (170, 230, 235)], seed=8, light=L), ux, uy)
    d = ImageDraw.Draw(img); d.line([(ux - 110, uy), (ux + 110, uy)], fill=GOLD, width=4)          # axis lies sideways
    yrs = int(84 * p); text(img, f"YEAR {yrs} OF 84", 64, 1560, 260, GOLD)
    side = "NORTH POLE: DAY" if yrs < 42 else "NORTH POLE: NIGHT"
    pill(img, side, 40, 1560, 360, fill=GOLD if yrs < 42 else (70, 80, 120), ink=(14, 16, 30) if yrs < 42 else WHITE)
    text(img, "42 years of sun · 42 years of dark", 36, 1560, 450, WHITE, w="SemiBold", maxw=700)
    return img

def b_pulsar(sc, lt, dur, t):
    img = space(t); cx, cy = 700, 540; spin = t * sc.get("vis_spin", 6.0)
    beam = Image.new("L", (W, H), 0); bd = ImageDraw.Draw(beam)
    for k in (0, math.pi):
        a = spin + k; bd.polygon([(cx, cy), (cx + 1300 * math.cos(a - 0.08), cy + 1300 * math.sin(a - 0.08)), (cx + 1300 * math.cos(a + 0.08), cy + 1300 * math.sin(a + 0.08))], fill=150)
    img.paste(Image.new("RGB", (W, H), (150, 200, 255)), (0, 0), beam.filter(ImageFilter.GaussianBlur(14)))
    halo(img, cx, cy, 70, (170, 210, 255), 255); d = ImageDraw.Draw(img); d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=WHITE)
    v = int(716 * eout((lt - 0.3) / 1.5))
    text(img, f"{v}", 200, 1460, 400, ICE); text(img, "SPINS PER SECOND", 52, 1460, 540, WHITE, w="Bold")
    pill(img, sc.get("label", "ABOUT 20 MILES ACROSS"), 38, 1460, 650, u=ease((lt - 1.0) / 0.4))
    return img

def b_spoon(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img); cx, cy = 640, 600
    d.ellipse([cx - 150, cy - 90, cx + 150, cy + 90], fill=(190, 196, 210)); d.ellipse([cx - 125, cy - 70, cx + 125, cy + 70], fill=(150, 156, 175))
    d.rounded_rectangle([cx + 130, cy - 22, cx + 620, cy + 22], 20, fill=(190, 196, 210))
    halo(img, cx, cy, 90, (170, 210, 255), 255); d = ImageDraw.Draw(img); d.ellipse([cx - 40, cy - 30, cx + 40, cy + 30], fill=WHITE)
    text(img, "BILLIONS", 150, 1420, 420, GOLD, u=back(lt / 0.4)); text(img, "OF TONS", 90, 1420, 560, WHITE, u=ease((lt - 0.3) / 0.4))
    text(img, "one teaspoon of neutron star", 40, 1420, 660, DIM, w="SemiBold", u=ease((lt - 0.6) / 0.4))
    return img

def b_geysers(sc, lt, dur, t):
    img = space(t); cx, cy, R = W / 2, 1650, 1000
    paste(img, sphere(R, [(220, 235, 245), (200, 220, 235), (235, 245, 250)], seed=11, light=(0.0, -0.9, 0.4)), cx, cy)
    r = random.Random(int(t * 30)); d = ImageDraw.Draw(img)
    for g in range(9):
        gx = cx - 520 + g * 130; top = cy - R + 12
        for k in range(26):
            age = (t * 0.6 + k / 26 + g * 0.11) % 1; h = age * (300 + 60 * math.sin(g)); spread = age * 70
            x = gx + r.uniform(-spread, spread); y = top - h; s = 3 + 5 * (1 - age); c = int(255 * (1 - age * 0.7))
            d.ellipse([x - s, y - s, x + s, y + s], fill=(c, c, 255))
    img = bloom(img, 0.5)
    text(img, sc.get("title", "ENCELADUS"), 90, W / 2, 180, WHITE); pill(img, sc.get("label", "100+ GEYSERS OF WATER & ICE"), 40, W / 2, 290, u=ease((lt - 0.5) / 0.4))
    return img

def b_footprint(sc, lt, dur, t):
    g = (np.random.default_rng(5).normal(0, 1, (H // 4, W // 4)) * 14 + 120).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(g).resize((W, H), Image.BICUBIC).convert("RGB"); d = ImageDraw.Draw(img)
    cx, cy = 760, 560
    d.rounded_rectangle([cx - 110, cy - 300, cx + 110, cy + 300], 110, fill=(88, 88, 92)); d.rounded_rectangle([cx - 95, cy - 285, cx + 95, cy + 285], 95, fill=(102, 102, 106))
    for k in range(13): y = cy - 260 + k * 42; d.line([(cx - 80, y), (cx + 80, y)], fill=(78, 78, 84), width=14)
    if int(t * 2.3) % 7 == 0:
        mx = 1200 + (t * 600) % 600; d.line([(mx, 80), (mx + 160, 260)], fill=(255, 240, 200), width=4)
    yrs = sc.get("years", 1_000_000) * eout((lt - 0.3) / 2.0)
    text(img, f"{int(yrs):,}+", 130, 1450, 420, (255, 255, 255)); text(img, "YEARS", 70, 1450, 530, GOLD)
    pill(img, sc.get("label", "NO WIND · NO RAIN"), 40, 1450, 640, u=ease((lt - 0.8) / 0.4))
    return img

def b_blackhole(sc, lt, dur, t):
    img = space(t * 0.5); cx, cy = 700, 540
    ring = Image.new("RGB", (W, H), (0, 0, 0)); rd = ImageDraw.Draw(ring)
    for k in range(60):
        r = 230 + k * 0.9; c = int(120 + 130 * (1 - k / 60))
        for a0 in range(0, 360, 12):
            br = 0.55 + 0.45 * math.cos(math.radians(a0 + t * 20) - 0.6)
            rd.arc([cx - r, cy - r, cx + r, cy + r], a0, a0 + 12, fill=(int(255 * br * c / 255), int(140 * br * c / 255), int(40 * br * c / 255)), width=2)
    ring = ring.filter(ImageFilter.GaussianBlur(10))
    img = Image.fromarray(np.clip(np.asarray(img).astype(np.int32) + np.asarray(ring).astype(np.int32) * 2, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img); d.ellipse([cx - 175, cy - 175, cx + 175, cy + 175], fill=(0, 0, 0))
    v = 4.0 * eout((lt - 0.3) / 1.4)
    text(img, f"{v:.1f} MILLION", 120, 1440, 400, GOLD); text(img, "TIMES THE MASS OF THE SUN", 46, 1440, 500, WHITE, w="Bold")
    pill(img, sc.get("label", "27,000 LIGHT-YEARS AWAY"), 38, 1440, 600, u=ease((lt - 0.8) / 0.4))
    return img

def b_diamonds(sc, lt, dur, t):
    img = space(t); cx, cy, R = 660, 560, 470
    d = ImageDraw.Draw(img)
    for k, (rf, col) in enumerate(((1.0, (60, 110, 220)), (0.8, (40, 70, 170)), (0.55, (30, 45, 120)), (0.25, (90, 80, 70)))):
        d.pieslice([cx - R * rf, cy - R * rf, cx + R * rf, cy + R * rf], 90, 450 if k == 0 else 450, fill=col)
    d.rectangle([cx - R - 10, cy - R - 10, cx, cy + R + 10], fill=None)
    r = random.Random(9)
    for k in range(60):
        a = r.uniform(-1.3, 1.3); dist0 = r.uniform(0.62, 0.78); speed = r.uniform(0.04, 0.09)
        dist = dist0 - ((t * speed + k * 0.017) % 0.38)
        x, y = cx + R * dist * math.sin(a), cy - R * dist * math.cos(a) * -1
        s = r.uniform(5, 11)
        d.polygon([(x, y - s), (x + s * 0.7, y), (x, y + s), (x - s * 0.7, y)], fill=(235, 250, 255))
    img = bloom(img, 0.6)
    text(img, sc.get("title", "DIAMOND RAIN"), 110, 1450, 400, ICE)
    for i, s in enumerate(sc.get("lines", [])): text(img, s, 40, 1450, 510 + i * 60, WHITE, w="SemiBold", u=ease((lt - 0.4 - i * 0.3) / 0.4), maxw=820)
    return img

def b_outro(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img)
    text(img, sc.get("q", "Which one sounded the MOST fake?"), 74, W / 2, 300, WHITE)
    click = sc.get("click_at", 1.6); on = ease((lt - click) / 0.25); cx, cy, w_, h_ = W / 2, 560, 300, 130
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=GOLD if on > 0.5 else (50, 56, 90), outline=WHITE, width=6)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; d.ellipse([kx - h_ / 2 + 16, cy - h_ / 2 + 16, kx + h_ / 2 - 16, cy + h_ / 2 - 16], fill=WHITE)
    text(img, "FAKE", 60, cx - w_ / 2 - 110, cy, WHITE if on < 0.5 else DIM); text(img, "TRUE", 60, cx + w_ / 2 + 110, cy, GOLD if on >= 0.5 else DIM)
    pill(img, "SUBSCRIBE · NEW DEEP DIVE EVERY TUE & FRI", 40, W / 2, 780, fill=RED, ink=WHITE, u=ease((lt - click - 0.4) / 0.4))
    return img

BEATS = dict(cold=b_cold, chapter=b_chapter, text=b_text, counter=b_counter, probe=b_probe, record=b_record, sunwalk=b_sunwalk,
             sunearth=b_sunearth, mountains=b_mountains, planet=b_planet, uranus=b_uranus, pulsar=b_pulsar, spoon=b_spoon,
             geysers=b_geysers, footprint=b_footprint, blackhole=b_blackhole, diamonds=b_diamonds, outro=b_outro)

# ---------------- narration & score ----------------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.42, tail=1.5)
n = len(voice); tt = np.arange(n) / SR; music = np.zeros(n, np.float32)
pads = [[110.0, 164.81, 220.0, 261.63], [98.0, 146.83, 196.0, 246.94], [87.31, 130.81, 174.61, 220.0], [82.41, 123.47, 164.81, 207.65]]
seg = 6.0
for i in range(int(total / seg) + 1):
    a, b = int(i * seg * SR), min(int((i + 1.4) * seg * SR), n)
    if a >= n: break
    lt = tt[a:b] - i * seg; env = np.clip(lt / 2.5, 0, 1) * np.clip((seg * 1.4 - lt) / 2.5, 0, 1)
    for f in pads[i % 4]: music[a:b] += (np.sin(2 * np.pi * f * lt) + 0.3 * np.sin(2 * np.pi * f * 1.004 * lt)) * env * 0.03
music += 0.02 * np.sin(2 * np.pi * 41.2 * tt) * (0.6 + 0.4 * np.sin(2 * np.pi * tt / 11))
for k in range(int(total * 0.8)):
    place(music, random.uniform(0, total), tone(random.choice([880, 1046.5, 1318.5, 1567.98]), 2.4, decay=1.6, harm=(1, 2)), 0.010)
hook_hit(music, 0.35)
for ln in spec["lines"]:
    if ln["scene"]["type"] == "chapter": hook_hit_t = ln["_s"]; place(music, hook_hit_t, tone(55, 1.2, decay=3, harm=(1, 2)), 0.25); whoosh(music, hook_hit_t, 0.18)
for ln in spec["lines"][1:]: whoosh(music, ln["_s"], 0.06)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.35)

# chapter index for the corner tracker
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
    d.rounded_rectangle([x - 28, y - 14, x + tw + 28, y + size + 18], 24, fill=(8, 10, 22))
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=GOLD if on else WHITE); x += d.textlength(w + " ", font=f)

def frame(t):
    ln = core.active_line(spec, t, lead=0.05) or spec["lines"][0]   # frame 0 = the full cold-open title
    if ln is None: img = space(t)
    else:
        lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]; sc = ln["scene"]
        img = BEATS[sc["type"]](sc, lt, dur, t)
        if sc["type"] not in ("geysers", "diamonds", "footprint"): img = bloom(img, 0.5)
        if ln["_ch"]: d = ImageDraw.Draw(img); d.text((W - 60, 50), f"{ln['_ch']:02d} / {NCH:02d}", font=F(34, "Bold"), fill=GOLD, anchor="ra")
    d = ImageDraw.Draw(img); d.rounded_rectangle([44, 40, 330, 92], 22, fill=(8, 10, 22)); d.text((62, 48), "SOUNDS FAKE  ?!", font=F(30, "Black"), fill=(220, 225, 240))
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
