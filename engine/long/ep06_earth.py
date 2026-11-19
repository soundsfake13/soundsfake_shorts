"""LONG-FORM (16:9, 1920x1080) — 'Sounds Fake: Deep Dive' ep06: PLANET EARTH.
Look: "Earth from orbit" — deep blue-black space, a real-coastline globe (Natural Earth land mask, public domain)
with atmosphere glow and drifting clouds, cutaways, clean cross-section diagrams, teal + gold accents.
Based on engine/long/space_deep_dive.py.
Usage: python3 engine/long/ep06_earth.py spec.json out.mp4 [t1,t2,... preview]
"""
import json, math, os, random, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import core
from core import narrate, write_audio, caption_groups, group_at, ease, eout, back, tone, place, hook_hit, whoosh, SR

W, H, FPS = 1920, 1080, 30
spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
rng = np.random.default_rng(6); random.seed(6)
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
_fc = {}
def F(s, w="Black"):
    k = (int(s), w)
    if k not in _fc: _fc[k] = ImageFont.truetype(f"{FD}InterDisplay-{w}.otf", int(s))
    return _fc[k]
GOLD, TEAL, WHITE, DIM, RED, BLUE = (255, 200, 90), (90, 225, 200), (240, 246, 255), (140, 160, 185), (255, 110, 80), (80, 150, 255)
SAND, GREEN, INKD = (214, 178, 112), (96, 170, 84), (8, 14, 26)
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------- background: blue-teal nebula + parallax stars ----------------
def lowf(h, w, cell, seed):
    r = np.random.default_rng(seed); s = r.random((h // cell + 2, w // cell + 2)).astype(np.float32)
    return np.asarray(Image.fromarray((s * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255
neb = lowf(H, W, 300, 1) ** 2.6; neb2 = lowf(H, W, 420, 2) ** 3
BG = np.zeros((H, W, 3), np.float32) + np.array([3, 7, 16], np.float32)
BG += neb[..., None] * np.array([12, 40, 70], np.float32) + neb2[..., None] * np.array([10, 55, 60], np.float32)
BG_IMG = Image.fromarray(BG.astype(np.uint8))
STARS = [(rng.uniform(0, W), rng.uniform(0, H), rng.choice([0.7, 1.1, 1.8], p=[0.6, 0.3, 0.1]), rng.uniform(0, 6.3), rng.uniform(0.2, 1)) for _ in range(600)]
def space(t, drift=6.0):
    img = BG_IMG.copy(); d = ImageDraw.Draw(img)
    for (x, y, s, ph, dep) in STARS:
        px = (x + drift * t * dep) % W
        c = int(255 * (0.55 + 0.45 * math.sin(t * 2 + ph)) * (0.4 + 0.6 * dep)); r = s * (0.7 + dep)
        d.ellipse([px - r, y - r, px + r, y + r], fill=(c, c, min(255, c + 25)))
    return img

def bloom(img, k=0.5):
    a = np.asarray(img).astype(np.float32)
    s = Image.fromarray(np.clip((a - 150) * 1.5, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    b = np.asarray(s.filter(ImageFilter.GaussianBlur(8)).resize((W, H), Image.BILINEAR)).astype(np.float32)
    return Image.fromarray(np.clip(a + b * k, 0, 255).astype(np.uint8))

def halo(img, cx, cy, r, col, strength=160):
    g = Image.new("L", (W, H), 0); ImageDraw.Draw(g).ellipse([cx - r, cy - r, cx + r, cy + r], fill=int(strength))
    img.paste(Image.new("RGB", (W, H), col), (0, 0), g.filter(ImageFilter.GaussianBlur(r * 0.5)))

# ---------------- Earth texture (equirectangular) ----------------
LAND = np.asarray(Image.open(os.path.join(HERE, "assets", "land_2048.png")).convert("L")).astype(np.float32) / 255   # 1024 x 2048
TH, TW = LAND.shape; LAND[int(TH * 168 / 180):] = 1.0                                                     # solid Antarctica at the pole
_wu = (0.5 - 0.5 * np.cos(2 * np.pi * (np.arange(TW) + 0.5) / TW))[None, :].astype(np.float32)
def seamless(a): return a * _wu + np.roll(a, TW // 2, axis=1) * (1 - _wu)                # no seam at the date line
_lat = (90 - (np.arange(TH) + 0.5) / TH * 180)[:, None] * np.ones((1, TW), np.float32)
_lon = ((np.arange(TW) + 0.5) / TW * 360 - 180)[None, :] * np.ones((TH, 1), np.float32)
nz1 = seamless(np.asarray(Image.fromarray((np.random.default_rng(3).random((TH // 16, TW // 16)) * 255).astype(np.uint8)).resize((TW, TH), Image.BICUBIC)).astype(np.float32) / 255)
nz2 = seamless(np.asarray(Image.fromarray((np.random.default_rng(4).random((TH // 4, TW // 4)) * 255).astype(np.uint8)).resize((TW, TH), Image.BICUBIC)).astype(np.float32) / 255)
coast = np.asarray(Image.fromarray((LAND * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10))).astype(np.float32) / 255
alat = np.abs(_lat)
ocean = np.array([10, 34, 82], np.float32) * (1 - coast[..., None] * 0.0) + np.array([14, 62, 120], np.float32) * coast[..., None] * 1.2
ocean = ocean + (nz2[..., None] - 0.5) * 8
def _sig(x): return 1 / (1 + np.exp(-x))
dry = np.exp(-((alat - 24) / 8) ** 2) * (0.35 + 0.45 * nz1) * np.where(_lat < 0, 0.7, 1.0)
dry += np.exp(-((_lat - 23) / 8) ** 2) * _sig((_lon + 17) / 3) * _sig((58 - _lon) / 3)            # Sahara + Arabia
dry += np.exp(-((_lat + 25) / 7) ** 2) * _sig((_lon - 118) / 3) * _sig((146 - _lon) / 3) * 0.8   # Australian interior
dry = np.clip(dry * (0.8 + 0.4 * nz1), 0, 1)
landc = np.array([62, 112, 56], np.float32) * (1 - dry[..., None]) + np.array(SAND, np.float32) * dry[..., None]
landc = landc * (0.85 + 0.3 * nz2[..., None])
cold = np.clip((alat - 55) / 12, 0, 1); landc = landc * (1 - cold[..., None] * 0.55) + np.array([120, 120, 110], np.float32) * cold[..., None] * 0.55
ice = ((_lat < -62) | ((_lat > 60) & (_lon > -72) & (_lon < -12)) | (_lat > 78)).astype(np.float32)
landc = landc * (1 - ice[..., None]) + np.array([236, 242, 248], np.float32) * ice[..., None]
TEX = np.clip(ocean * (1 - LAND[..., None]) + landc * LAND[..., None], 0, 255).astype(np.float32)
GOLDTEX = np.clip(np.array([205, 150, 45], np.float32) + (nz2[..., None] - 0.5) * 60 + LAND[..., None] * np.array([40, 30, 10], np.float32), 0, 255)
cl = seamless(lowf(TH, TW, 48, 9) * 0.65 + lowf(TH, TW, 20, 10) * 0.35)
cl = np.asarray(Image.fromarray((cl * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))).astype(np.float32) / 255
CLOUD = (np.clip((cl - 0.6) * 2.6, 0, 0.6) * (0.6 + 0.4 * np.clip(alat / 40, 0, 1)) * np.clip((80 - alat) / 15, 0, 1)).astype(np.float32)

_gg = {}
def _grid(r):
    if r not in _gg:
        R = int(r) + 3
        X, Y = np.meshgrid(np.arange(-R, R, dtype=np.float32) + 0.5, np.arange(-R, R, dtype=np.float32) + 0.5)
        x, y = X / r, -Y / r; rho2 = x * x + y * y
        z = np.sqrt(np.clip(1 - rho2, 0, 1)); alpha = np.clip((1 - np.sqrt(rho2)) * r, 0, 1)
        _gg[r] = (x, y, z, alpha, R)
    return _gg[r]

def globe(r, lat0, lon0, light=(-0.55, 0.35, 0.76), clouds=0.0, night=False, tex=None, lights=None):
    """Orthographic globe as RGBA. lat0/lon0 = centre of view (deg). Real coastlines."""
    x, y, z, alpha, R = _grid(r)
    p0, l0 = math.radians(lat0), math.radians(lon0)
    lat = np.arcsin(np.clip(z * math.sin(p0) + y * math.cos(p0), -1, 1))
    lon = l0 + np.arctan2(x, z * math.cos(p0) - y * math.sin(p0))
    u = (((np.degrees(lon) + 180) / 360 * TW).astype(np.int32)) % TW
    v = np.clip(((90 - np.degrees(lat)) / 180 * TH).astype(np.int32), 0, TH - 1)
    col = (TEX if tex is None else tex)[v, u]
    if clouds >= 0:
        uc = (u + int(clouds * 12)) % TW; c = CLOUD[v, uc][..., None]
        col = col * (1 - c) + 235 * c
    L = np.array(light, np.float32); L /= np.linalg.norm(L)
    lam = np.clip(x * L[0] + y * L[1] + z * L[2], 0, 1)
    shade = (0.05 + 1.0 * lam ** 0.8) if not night else (0.035 + 0.9 * lam ** 1.2)
    rgb = col * shade[..., None]
    rim = (1 - z) ** 3
    rgb = rgb + np.array([70, 150, 255], np.float32) * (rim * (0.35 + 0.65 * lam))[..., None] * 0.9
    out = np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")

def proj(r, lat0, lon0, lat, lon):
    p0, l0, p, l = map(math.radians, (lat0, lon0, lat, lon))
    x = math.cos(p) * math.sin(l - l0); y = math.cos(p0) * math.sin(p) - math.sin(p0) * math.cos(p) * math.cos(l - l0)
    z = math.sin(p0) * math.sin(p) + math.cos(p0) * math.cos(p) * math.cos(l - l0)
    return r * x, -r * y, z

def paste(img, spr, cx, cy):
    img.paste(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)), spr)

def put_globe(img, cx, cy, r, lat0, lon0, t, glow=True, **kw):
    if glow: halo(img, cx, cy, r * 1.08, (40, 110, 230), 120)
    paste(img, globe(r, lat0, lon0, clouds=t, **kw), cx, cy)

_hz = {}
def horizon(img, t):
    """Big static planet limb at the bottom of the frame (cached)."""
    if "h" not in _hz:
        r = 1000; g = globe(r, -8, 10, light=(0.0, 0.75, 0.66), clouds=0)
        base = Image.new("RGBA", (W, H), (0, 0, 0, 0)); base.paste(g, (int(W / 2 - g.width / 2), int(H + 560 - g.height / 2)), g)
        _hz["h"] = base
    halo(img, W / 2, H + 560, 1040, (40, 120, 255), 110)
    img.paste(_hz["h"], (0, 0), _hz["h"])

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
    return str(v)

def marker(img, x, y, t, col=GOLD, label=None, lsize=40):
    p = (t * 1.2) % 1; d = ImageDraw.Draw(img)
    rr = 14 + 46 * p; c = tuple(int(cc * (1 - p)) for cc in col)
    d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=c, width=4)
    halo(img, x, y, 26, col, 230); d = ImageDraw.Draw(img); d.ellipse([x - 10, y - 10, x + 10, y + 10], fill=WHITE)
    if label: pill(img, label, lsize, x, y - 80)

# ---------------- beats ----------------
def b_cold(sc, lt, dur, t):
    img = space(t); horizon(img, t)
    for i, s in enumerate(sc["lines"]):
        text(img, s, sc.get("size", 120), W / 2, 300 + i * sc.get("size", 120) * 1.15, GOLD if i == 1 else WHITE, u=1.0 if i == 0 else ease((lt - i * 0.5) / 0.4))
    if "sub" in sc: pill(img, sc["sub"], 40, W / 2, 610, fill=TEAL, u=ease((lt - 0.8) / 0.4))
    return img

def b_chapter(sc, lt, dur, t):
    img = space(t); horizon(img, t)
    u = back(lt / 0.45)
    text(img, f"{sc['ch']:02d}", 300, W / 2, 330, GOLD, u=min(1, u))
    text(img, sc["title"], 84, W / 2, 560, WHITE, u=ease((lt - 0.3) / 0.4))
    if "sub" in sc: text(img, sc["sub"], 40, W / 2, 650, TEAL, w="SemiBold", u=ease((lt - 0.6) / 0.4))
    return img

def b_text(sc, lt, dur, t):
    img = space(t)
    if sc.get("globe"): horizon(img, t)
    for i, s in enumerate(sc["lines"]):
        y = sc.get("y", 420) - (130 if sc.get("globe") else 0) + i * sc.get("size", 96) * 1.2
        text(img, s, sc.get("size", 96), W / 2, y, GOLD if str(i) in sc.get("accent", {}) else WHITE, u=ease((lt - i * 0.35) / 0.4))
    return img

def b_counter(sc, lt, dur, t):
    img = space(t); horizon(img, t)
    v = sc["from"] + (sc["to"] - sc["from"]) * eout((lt - 0.2) / max(0.6, sc.get("secs", 2.0)))
    text(img, sc.get("prefix", "") + fmtnum(v, sc.get("fmt", "int")) + sc.get("suffix", ""), sc.get("size", 210), W / 2, 300, GOLD, u=ease(lt / 0.3))
    text(img, sc["label"], 58, W / 2, 470, WHITE, w="Bold", u=ease((lt - 0.3) / 0.4))
    if "note" in sc: text(img, sc["note"], 38, W / 2, 545, TEAL, w="SemiBold", u=ease((lt - 0.9) / 0.4))
    return img

def b_globe(sc, lt, dur, t):
    img = space(t); m = sc.get("mode", "plain")
    lat0, lon0 = sc.get("lat", 10), sc.get("lon", 0)
    if m == "fly":
        a = ease((lt - 0.2) / 2.2); f = sc["from"]; lat0 = f[0] + (lat0 - f[0]) * a; lon0 = f[1] + (lon0 - f[1]) * a
    if m == "spin": lon0 = lon0 - lt * 12
    cx, cy, r = (560, 540, 400) if m in ("hook", "spin") else (W / 2, 560, 400)
    put_globe(img, cx, cy, r, lat0, lon0, t)
    d = ImageDraw.Draw(img)
    if sc.get("equator"):
        pts = []
        for k in range(0, 361, 3):
            x, y, z = proj(r, lat0, lon0, 0, k)
            if z > 0: pts.append((cx + x, cy + y))
            elif len(pts) > 1: d.line(pts, fill=GOLD, width=4); pts = []
        if len(pts) > 1: d.line(pts, fill=GOLD, width=4)
    if "mark" in sc:
        x, y, z = proj(r, lat0, lon0, *sc["mark"])
        if z > 0: marker(img, cx + x, cy + y, t, label=sc.get("marklabel") if (m != "fly" or lt > 2.2) else None)
    if sc.get("iss"):
        a = t * 0.9; ox, oy = cx + math.cos(a) * r * 1.15, cy - 60 + math.sin(a) * r * 0.32
        d = ImageDraw.Draw(img); d.ellipse([cx - r * 1.15, cy - 60 - r * 0.32, cx + r * 1.15, cy - 60 + r * 0.32], outline=(70, 110, 160), width=2)
        if math.sin(a) > -0.2 or abs(ox - cx) > r:
            halo(img, ox, oy, 22, (200, 230, 255), 230); d = ImageDraw.Draw(img)
            d.rectangle([ox - 26, oy - 3, ox + 26, oy + 3], fill=WHITE); d.rectangle([ox - 30, oy - 12, ox - 20, oy + 12], fill=(140, 180, 255)); d.rectangle([ox + 20, oy - 12, ox + 30, oy + 12], fill=(140, 180, 255))
    if m == "hook":
        for i, s in enumerate(sc["lines"]): text(img, s, 96, 1450, 420 + i * 116, GOLD if i == 1 else WHITE, u=ease((lt - i * 0.3) / 0.35), maxw=800)
        pill(img, "POINT NEMO · SOUTH PACIFIC", 36, 1450, 680, fill=TEAL, u=ease((lt - 0.8) / 0.4))
    if "counter" in sc:
        a0, a1, suf = sc["counter"]; v = a0 + (a1 - a0) * eout((lt - 0.3) / 1.8)
        text(img, f"{int(v):,}{suf}", 150, 1450, 440, GOLD); text(img, sc.get("label", ""), 44, 1450, 560, WHITE, w="Bold", maxw=820)
    return img

def b_orbit(sc, lt, dur, t):
    img = space(t); sx, sy = 330, 560
    halo(img, sx, sy, 230, (255, 160, 60), 200); d = ImageDraw.Draw(img); d.ellipse([sx - 110, sy - 110, sx + 110, sy + 110], fill=(255, 196, 90)); d.ellipse([sx - 80, sy - 80, sx + 80, sy + 80], fill=(255, 226, 150))
    ax, ay = 560, 250; d.ellipse([sx - ax, sy - ay, sx + ax, sy + ay], outline=(60, 90, 140), width=3)
    a = -0.6 + lt * 0.35
    for k in range(18):
        b = a - k * 0.025; d.ellipse([sx + ax * math.cos(b) - 4, sy + ay * math.sin(b) - 4, sx + ax * math.cos(b) + 4, sy + ay * math.sin(b) + 4], fill=(90 + 6 * (18 - k), 150, 255))
    ex, ey = sx + ax * math.cos(a), sy + ay * math.sin(a)
    put_globe(img, ex, ey, 46, 15, -lt * 40, t, light=((sx - ex) / 600, -(sy - ey) / 600, 0.5))
    v = sc["to"] * eout((lt - 0.2) / 2.0)
    text(img, f"{int(v):,}", 170, 1430, 420, GOLD); text(img, "KM/H", 70, 1430, 545, WHITE)
    pill(img, sc.get("label", "AROUND THE SUN"), 40, 1430, 650, fill=TEAL, u=ease((lt - 0.6) / 0.4))
    return img

def b_compare(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img); mx = max(sc["lv"], sc["rv"]); L = 880
    for i, (lab, val, tx, col) in enumerate(((sc["left"], sc["lv"], sc["lt"], TEAL), (sc["right"], sc["rv"], sc["rt"], GOLD))):
        y = 400 + i * 260; w = L * val / mx * eout((lt - 0.2 - i * 0.6) / 1.0)
        text(img, " ".join(lab), 48, 560, y, WHITE, w="Bold", anchor="rm", u=ease((lt - i * 0.6) / 0.3), maxw=480)
        d = ImageDraw.Draw(img)
        if w > 4: d.rounded_rectangle([600, y - 50, 600 + w, y + 50], 26, fill=col)
        if w > 4: text(img, tx, 50, 600 + w + 30, y, col, anchor="lm", u=ease((lt - 0.8 - i * 0.6) / 0.3))
    return img

def b_stamp(sc, lt, dur, t):
    img = space(t); horizon(img, t); n = len(sc["lines"]); size = 92 if n > 1 else 84
    for i, s in enumerate(sc["lines"]): text(img, s, size, W / 2, 170 + i * size * 1.25, WHITE if i == 0 else GOLD, u=ease((lt - i * 0.25) / 0.35))
    at = 0.5 + n * 0.25; u = (lt - at) / 0.22
    if u > 0:
        s = 1 + 1.4 * (1 - eout(u)); a = min(1, u * 2)
        st = Image.new("RGBA", (700, 300), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
        sd.rounded_rectangle([20, 40, 680, 260], 30, outline=(90, 235, 150, int(255 * a)), width=16)
        sd.text((350, 150), sc.get("stamp", "TRUE"), font=F(170, "Black"), fill=(90, 235, 150, int(255 * a)), anchor="mm")
        st = st.rotate(-8, expand=True, resample=Image.BICUBIC); st = st.resize((int(st.width * s * 0.62), int(st.height * s * 0.62)), Image.BICUBIC)
        paste(img, st, W / 2, 190 + n * size * 1.25 + 100)
    return img

def b_nemo(sc, lt, dur, t):
    m = sc["mode"]; img = space(t, drift=2); d = ImageDraw.Draw(img)
    if m in ("map", "sail"):
        cx, cy, R = 960, 520, 360
        g = Image.new("RGB", (W, H), (0, 0, 0)); gd = ImageDraw.Draw(g)
        for k in range(30, 0, -1):
            rr = R * 1.45 * k / 30; c = (8 + k, 34 + k * 2, 78 + k * 2); gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=c)
        msk = Image.new("L", (W, H), 0); ImageDraw.Draw(msk).ellipse([cx - R * 1.45, cy - R * 1.45, cx + R * 1.45, cy + R * 1.45], fill=255)
        img.paste(g, (0, 0), msk.filter(ImageFilter.GaussianBlur(20))); d = ImageDraw.Draw(img)
        u = eout((lt - 0.2) / 1.2); rr = R * u
        for k in range(0, 360, 6):
            a0 = math.radians(k + t * 6); d.arc([cx - rr, cy - rr, cx + rr, cy + rr], k + t * 6, k + 3 + t * 6, fill=TEAL, width=4)
        isl = [("DUCIE ISLAND", -95), ("MOTU NUI", -40), ("MAHER ISLAND", 90)]
        for i, (nm, ang) in enumerate(isl):
            if u < 0.98: break
            a = math.radians(ang); x, y = cx + R * math.cos(a), cy + R * math.sin(a); uu = ease((lt - 1.4 - i * 0.3) / 0.3)
            if uu <= 0: continue
            d.ellipse([x - 12, y - 9, x + 12, y + 9], fill=(120, 170, 90)); text(img, nm, 30, x + (0 if ang in (-95, 90) else 140), y + (-40 if ang < 0 else 44), WHITE, w="Bold", u=uu)
        marker(img, cx, cy, t, label="POINT NEMO", lsize=34)
        if m == "map":
            d = ImageDraw.Draw(img); d.line([(cx, cy), (cx + R * math.cos(0.5), cy + R * math.sin(0.5))], fill=GOLD, width=4)
            text(img, "≈ 2,700 KM", 48, cx + R * 0.62 * math.cos(0.5) + 110, cy + R * 0.62 * math.sin(0.5) + 10, GOLD, u=ease((lt - 1.2) / 0.4))
        else:
            a = math.radians(-40); p = ease((lt - 0.2) / max(1.0, dur - 0.5)); x0, y0 = cx + R * math.cos(a), cy + R * math.sin(a)
            bx, by = x0 + (cx - x0) * p, y0 + (cy - y0) * p
            for k in range(int(40 * p)):
                q = k / 40; d.ellipse([x0 + (cx - x0) * q - 3, y0 + (cy - y0) * q - 3, x0 + (cx - x0) * q + 3, y0 + (cy - y0) * q + 3], fill=(200, 220, 240))
            d.polygon([(bx - 22, by - 6), (bx + 22, by - 6), (bx + 14, by + 10), (bx - 14, by + 10)], fill=WHITE); d.polygon([(bx, by - 40), (bx, by - 8), (bx + 22, by - 8)], fill=GOLD)
            pill(img, "NOTHING BUT OPEN OCEAN", 38, 1600, 300, fill=TEAL)
    elif m == "side":
        sea = 760; d.rectangle([0, sea, W, H], fill=(10, 36, 80)); d.line([(0, sea), (W, sea)], fill=(70, 150, 230), width=3)
        sx, ix = 300, 300 + 1400; kpx = 1400 / 2700; u = eout((lt - 0.2) / 1.0)
        marker(img, sx, sea, t); text(img, "POINT NEMO", 34, sx, sea + 60, WHITE, w="Bold")
        d = ImageDraw.Draw(img); xx = sx + (ix - sx) * u; d.line([(sx, sea + 120), (xx, sea + 120)], fill=TEAL, width=5)
        d.polygon([(ix - 60, sea + 2), (ix - 20, sea - 26), (ix + 30, sea - 18), (ix + 60, sea + 2)], fill=(110, 160, 90))
        text(img, "NEAREST LAND", 34, ix, sea - 70, WHITE, w="Bold"); text(img, "≈ 2,700 KM", 50, (sx + ix) / 2, sea + 170, TEAL, u=u)
        v = ease((lt - 1.2) / 0.9); iy = sea - 400 * kpx * v
        d.line([(sx, sea - 10), (sx, iy)], fill=GOLD, width=5)
        if v > 0:
            halo(img, sx, iy, 30, (200, 230, 255), 230); d = ImageDraw.Draw(img)
            d.rectangle([sx - 30, iy - 4, sx + 30, iy + 4], fill=WHITE); d.rectangle([sx - 36, iy - 16, sx - 24, iy + 16], fill=(140, 180, 255)); d.rectangle([sx + 24, iy - 16, sx + 36, iy + 16], fill=(140, 180, 255))
            text(img, "SPACE STATION ≈ 400 KM UP", 46, sx + 70, iy - 10, GOLD, anchor="lm", u=v)
        pill(img, "DRAWN TO SCALE", 30, W / 2, 200, fill=(40, 60, 100), ink=WHITE)
    elif m == "iss":
        sea = 700; d.rectangle([0, sea, W, H], fill=(8, 30, 70)); d.line([(0, sea), (W, sea)], fill=(70, 150, 230), width=3)
        p = ease((lt - 0.3) / max(2.0, dur - 1.0)); x, y = 300 + 1100 * p, 160 + (sea - 200) * p * p
        for j in range(24):
            q = j / 24; d.line([(x - 360 * q, y - 300 * q * q - 60 * q), (x - 360 * (q + 0.05), y - 300 * (q + 0.05) ** 2 - 60 * (q + 0.05))], fill=(255, int(210 - 130 * q), int(110 - 90 * q)), width=max(1, int(14 * (1 - q))))
        halo(img, x, y, 60, (255, 190, 120), 220); d = ImageDraw.Draw(img)
        d.rectangle([x - 60, y - 6, x + 60, y + 6], fill=WHITE); d.rectangle([x - 72, y - 28, x - 48, y + 28], fill=(140, 180, 255)); d.rectangle([x + 48, y - 28, x + 72, y + 28], fill=(140, 180, 255))
        marker(img, 1400, sea, t, label="POINT NEMO", lsize=34)
        pill(img, "THE SPACE STATION'S PLANNED FINAL STOP", 44, W / 2, 180, fill=GOLD)
    else:   # graveyard
        sea = 640; d.rectangle([0, sea, W, H], fill=(8, 30, 70)); d.line([(0, sea), (W, sea)], fill=(70, 150, 230), width=3)
        r = random.Random(3)
        for k in range(7):
            ph = (lt * 0.35 + k / 7) % 1; x0 = 300 + k * 230 + r.uniform(-60, 60); x = x0 + 260 * ph; y = 80 + (sea - 80) * ph
            for j in range(14):
                q = j / 14; d.line([(x - 26 * q * 10, y - 26 * q * 9), (x - 26 * (q + 0.07) * 10, y - 26 * (q + 0.07) * 9)], fill=(255, int(200 - 120 * q), int(100 - 80 * q)), width=max(1, int(8 * (1 - q))))
            halo(img, x, y, 20, (255, 190, 120), 200); d = ImageDraw.Draw(img)
        for k in range(5):
            x = 200 + k * 360; d.polygon([(x, sea + 290), (x + 40, sea + 250), (x + 90, sea + 265), (x + 60, sea + 300)], fill=(60, 70, 90)); d.rectangle([x + 20, sea + 258, x + 50, sea + 276], fill=(80, 90, 110))
        pill(img, "THE SPACECRAFT CEMETERY", 46, W / 2, 740, fill=GOLD); text(img, "hundreds of crash landings since the 1970s", 38, W / 2, 815, WHITE, w="SemiBold")
    return img

def b_lightning(sc, lt, dur, t):
    img = space(t); cx, cy, r = 700, 560, 420; lat0, lon0 = 5, 20 - t * 3
    halo(img, cx, cy, r * 1.06, (30, 70, 160), 90); paste(img, globe(r, lat0, lon0, light=(-0.95, 0.1, 0.2), clouds=t, night=True), cx, cy)
    rr = random.Random(int(t * 30)); spots = 0
    for _ in range(4):
        lat, lon = rr.uniform(-28, 30), lon0 + rr.uniform(-80, 80)
        x, y, z = proj(r, lat0, lon0, lat, lon)
        if z > 0.15:
            halo(img, cx + x, cy + y, rr.uniform(18, 40), (200, 220, 255), 255); spots += 1
            d = ImageDraw.Draw(img); px, py = cx + x, cy + y
            d.line([(px, py - 16), (px - 6, py), (px + 5, py + 2), (px - 3, py + 18)], fill=WHITE, width=3)
    n = int((lt % 1.0) * sc.get("rate", 45)) + 1
    text(img, f"{n}", 200, 1480, 400, GOLD); text(img, "FLASHES · THIS SECOND", 44, 1480, 530, WHITE, w="Bold")
    pill(img, "SOMEWHERE ON EARTH, EVERY SECOND", 34, 1480, 620, fill=TEAL, u=ease((lt - 0.6) / 0.4))
    if sc.get("sat"):
        a = lt * 0.6; sx, sy = cx + math.cos(a) * r * 1.25, cy - r * 0.95 + math.sin(a) * 40
        cone = Image.new("L", (W, H), 0); ImageDraw.Draw(cone).polygon([(sx, sy), (sx - 120, sy + 260), (sx + 120, sy + 260)], fill=90)
        img.paste(Image.new("RGB", (W, H), (120, 200, 255)), (0, 0), cone.filter(ImageFilter.GaussianBlur(10)))
        d = ImageDraw.Draw(img); d.rectangle([sx - 14, sy - 10, sx + 14, sy + 10], fill=WHITE); d.rectangle([sx - 50, sy - 6, sx - 18, sy + 6], fill=BLUE); d.rectangle([sx + 18, sy - 6, sx + 50, sy + 6], fill=BLUE)
        pill(img, sc.get("label", ""), 34, 1480, 720, u=ease((lt - 0.4) / 0.4))
    return img

def _strip(lon_a, lon_b, lat_a, lat_b, w, h):
    j0, j1 = int((lon_a + 180) / 360 * TW), int((lon_b + 180) / 360 * TW); i0, i1 = int((90 - lat_a) / 180 * TH), int((90 - lat_b) / 180 * TH)
    return Image.fromarray(TEX[i0:i1, j0:j1].astype(np.uint8)).resize((w, h), Image.BILINEAR)
_ATL = {}
def b_drift(sc, lt, dur, t):
    img = space(t); m = sc["mode"]; d = ImageDraw.Draw(img)
    if m == "nail":
        cx, cy = 560, 560
        sk, sk2 = (222, 172, 140), (196, 146, 116)
        d.rounded_rectangle([cx - 120, cy - 260, cx + 120, cy + 520], 120, fill=sk)
        for yk in (cy + 130, cy + 160, cy + 380, cy + 405): d.arc([cx - 70, yk - 14, cx + 70, yk + 14], 200, 340, fill=sk2, width=5)
        g = 46 * eout((lt - 0.2) / 3.0)
        d.rounded_rectangle([cx - 82, cy - 250 - g, cx + 82, cy - 150], 60, fill=(252, 246, 240))
        d.rounded_rectangle([cx - 86, cy - 200, cx + 86, cy + 20], 70, fill=(242, 196, 186)); d.line([(cx - 74, cy - 186), (cx + 74, cy - 186)], fill=(255, 236, 228), width=8)
        d.ellipse([cx - 40, cy - 30, cx + 40, cy + 6], fill=(250, 222, 212))
        text(img, "PLATES MOVE", 70, 1380, 360, WHITE, u=ease(lt / 0.4)); text(img, "≈ AS FAST AS", 70, 1380, 450, WHITE, u=ease((lt - 0.3) / 0.4))
        text(img, "FINGERNAILS GROW", 76, 1380, 545, GOLD, u=ease((lt - 0.6) / 0.4)); pill(img, "A FEW CENTIMETERS A YEAR", 38, 1380, 660, fill=TEAL, u=ease((lt - 1.0) / 0.4))
    elif m == "atlantic":
        if "a" not in _ATL:
            _ATL["a"] = _strip(-110, -32, 72, -58, 680, 860); _ATL["b"] = _strip(-32, 50, 72, -58, 715, 860)
        s = 70 * ease((lt - 0.4) / max(1.0, dur - 1.0)); x0 = 960 - 680
        img.paste(_ATL["a"], (int(x0 - s), 80)); img.paste(_ATL["b"], (int(960 + s), 80)); d = ImageDraw.Draw(img)
        d.rectangle([int(960 - s), 80, int(960 + s), 940], fill=(10, 34, 82))
        d.line([(960, 80), (960, 940)], fill=RED, width=4)
        for k in range(5):
            y = 220 + k * 160; d.polygon([(960 - 30 - s, y), (960 - 70 - s, y - 18), (960 - 70 - s, y + 18)], fill=GOLD); d.polygon([(960 + 30 + s, y), (960 + 70 + s, y - 18), (960 + 70 + s, y + 18)], fill=GOLD)
        pill(img, "ATLANTIC: + A FEW CM EVERY YEAR", 40, 960, 150, fill=GOLD); pill(img, "MID-ATLANTIC RIDGE", 30, 960, 880, fill=RED, ink=WHITE)
        d = ImageDraw.Draw(img); d.rectangle([0, 0, W, 80], fill=None)
    else:   # life
        base = 860; u = eout((lt - 0.3) / 2.2)
        hx = 620; d.ellipse([hx - 40, base - 380, hx + 40, base - 300], fill=(200, 215, 235)); d.rounded_rectangle([hx - 60, base - 290, hx + 60, base - 120], 40, fill=(200, 215, 235)); d.rectangle([hx - 50, base - 140, hx - 10, base], fill=(200, 215, 235)); d.rectangle([hx + 10, base - 140, hx + 50, base], fill=(200, 215, 235))
        bw = 760 * u; d.rounded_rectangle([780, base - 70, 780 + bw, base], 20, fill=(20, 70, 140)); d.line([(780, base - 70), (780 + bw, base - 70)], fill=TEAL, width=4)
        for k in range(0, 3): x = 780 + 380 * k; d.line([(x, base + 10), (x, base + 40)], fill=DIM, width=3); text(img, f"{k} M", 30, x, base + 70, DIM, w="Bold")
        text(img, "ONE LIFETIME", 70, 1160, 360, WHITE, u=ease(lt / 0.4)); text(img, "≈ +2 METERS OF OCEAN", 76, 1160, 460, GOLD, u=ease((lt - 0.4) / 0.4), maxw=1000)
    return img

def _sky(top, bot):
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    return np.array(top, np.float32) * (1 - yy) + np.array(bot, np.float32) * yy
SKY_DAY = Image.fromarray(np.repeat(_sky((70, 140, 210), (240, 210, 160)), W, axis=1).astype(np.uint8))
def lerpc(a, b, u): return tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3))
def dunes(img, u_green, lake=0.0, t=0.0):
    d = ImageDraw.Draw(img)
    layers = [(560, 60, 0.004, (226, 190, 128), (128, 176, 92)), (660, 50, 0.006, (214, 172, 106), (104, 158, 78)), (780, 40, 0.009, (196, 152, 88), (84, 136, 64))]
    for k, (y0, amp, fq, cs, cg) in enumerate(layers):
        pts = [(x, y0 + amp * math.sin(x * fq + k * 1.7) + amp * 0.4 * math.sin(x * fq * 2.3 + k)) for x in range(0, W + 20, 20)]
        d.polygon(pts + [(W, H), (0, H)], fill=lerpc(cs, cg, u_green))
    if u_green > 0.5:
        r = random.Random(2)
        for _ in range(int(26 * (u_green - 0.5) * 2)):
            x, y = r.uniform(60, W - 60), r.uniform(600, 900)
            if abs(x - 960) < 640 and y > 700 and lake > 0: continue
            d.rectangle([x - 4, y - 50, x + 4, y], fill=(90, 70, 40)); d.ellipse([x - 40, y - 90, x + 40, y - 40], fill=(60, 130, 60))
    if lake > 0:
        lw = 560 * lake; d.ellipse([960 - lw, 850 - 80 * lake, 960 + lw, 850 + 80 * lake], fill=(50, 120, 190)); d.ellipse([960 - lw * 0.92, 838 - 62 * lake, 960 + lw * 0.92, 838 + 50 * lake], fill=(80, 150, 215))
def hippo(d, x, y, s=1.0):
    c = (70, 60, 72); d.ellipse([x - 70 * s, y - 34 * s, x + 50 * s, y + 18 * s], fill=c); d.ellipse([x + 30 * s, y - 30 * s, x + 90 * s, y + 6 * s], fill=c)
    d.ellipse([x + 38 * s, y - 40 * s, x + 50 * s, y - 26 * s], fill=c); d.ellipse([x + 60 * s, y - 40 * s, x + 72 * s, y - 26 * s], fill=c)
def croc(d, x, y, s=1.0):
    c = (52, 80, 50); d.polygon([(x - 120 * s, y), (x - 40 * s, y - 14 * s), (x + 60 * s, y - 12 * s), (x + 140 * s, y - 2 * s), (x + 60 * s, y + 6 * s), (x - 40 * s, y + 6 * s)], fill=c)
    for k in range(5): xx = x - 30 * s + k * 20 * s; d.polygon([(xx, y - 12 * s), (xx + 7 * s, y - 22 * s), (xx + 14 * s, y - 12 * s)], fill=c)
def b_sahara(sc, lt, dur, t):
    m = sc["mode"]; img = SKY_DAY.copy(); d = ImageDraw.Draw(img)
    halo(img, 1520, 220, 120, (255, 240, 200), 200); d = ImageDraw.Draw(img); d.ellipse([1470, 170, 1570, 270], fill=(255, 248, 220))
    if m == "sand":
        dunes(img, 0.0); text(img, "THE SAHARA", 120, W / 2, 330, WHITE, u=ease(lt / 0.4))
    elif m == "turn":
        u = ease((lt - 0.6) / 2.0); dunes(img, u, lake=ease((lt - 1.6) / 1.4))
        text(img, "GREEN.", 130, W / 2, 300, lerpc(WHITE, (150, 255, 140), u), u=ease((lt - 0.4) / 0.4)); pill(img, sc.get("label", ""), 40, W / 2, 420, fill=GOLD, u=ease((lt - 0.8) / 0.4))
    elif m == "lakes":
        dunes(img, 1.0, lake=1.0); d = ImageDraw.Draw(img)
        if lt > 0.6: hippo(d, 760, 840, 1.6)
        if lt > 1.4: croc(d, 1200, 850, 1.4)
        text(img, "LAKES · HIPPOS · CROCODILES", 72, W / 2, 330, WHITE, u=ease((lt - 0.2) / 0.4), maxw=1600)
    elif m == "bones":
        dunes(img, 0.0); d = ImageDraw.Draw(img); d.rectangle([0, 820, W, H], fill=(150, 112, 64))
        for k, (x, y, a) in enumerate(((520, 900, 0.3), (700, 930, -0.4), (880, 890, 0.1))):
            if lt < 0.4 + k * 0.3: continue
            dx, dy = 60 * math.cos(a), 60 * math.sin(a); d.line([(x - dx, y - dy), (x + dx, y + dy)], fill=(238, 230, 210), width=14)
            for sgn in (-1, 1): d.ellipse([x + sgn * dx - 14, y + sgn * dy - 14, x + sgn * dx + 14, y + sgn * dy + 14], fill=(238, 230, 210))
        if lt > 1.2:
            fx, fy = 1300, 905; d.line([(fx - 260, fy), (fx + 200, fy)], fill=(238, 230, 210), width=8)
            for k in range(12): xx = fx - 220 + k * 34; d.line([(xx, fy - 40 + abs(k - 6) * 3), (xx + 10, fy + 40 - abs(k - 6) * 3)], fill=(238, 230, 210), width=5)
            d.polygon([(fx + 200, fy), (fx + 270, fy - 50), (fx + 270, fy + 50)], outline=(238, 230, 210), width=6); d.polygon([(fx - 260, fy), (fx - 320, fy - 46), (fx - 320, fy + 46)], outline=(238, 230, 210), width=6)
            pill(img, "FISH ≈ 2 M LONG", 36, fx, 790, fill=GOLD)
        text(img, "DUG UP IN THE DESERT", 90, W / 2, 330, WHITE, u=ease(lt / 0.4))
    elif m == "cave":
        if "cave" not in _hz:
            a = (lowf(H, W, 90, 12) * 50 + lowf(H, W, 20, 13) * 25)[..., None] + np.array([150, 92, 52], np.float32)
            _hz["cave"] = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        img = _hz["cave"].copy(); d = ImageDraw.Draw(img); oc = (120, 36, 22)
        for k, (x, y) in enumerate(((560, 420), (860, 520), (1180, 400), (1420, 560), (760, 700), (1260, 720))):
            if lt < 0.3 + k * 0.25: continue
            d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=oc); d.line([(x + 14, y + 4), (x + 120, y + 18)], fill=oc, width=12)
            d.line([(x + 30, y + 6), (x - 40, y - 30)], fill=oc, width=8); d.line([(x + 40, y + 10), (x + 10, y + 50)], fill=oc, width=8)
            d.line([(x + 120, y + 18), (x + 170, y)], fill=oc, width=8); d.line([(x + 120, y + 18), (x + 170, y + 40)], fill=oc, width=8)
        pill(img, "THE “CAVE OF SWIMMERS” · PAINTED ≈ 9,000–6,000 YEARS AGO", 34, W / 2, 180, fill=INKD, ink=WHITE)
    else:   # cycle
        img = space(t); d = ImageDraw.Draw(img); x0, x1, y = 320, 1780, 560
        u = eout((lt - 0.2) / 2.5); n = int((x1 - x0) * u)
        pts = [(x0 + i, y - 160 * math.cos((i) / (x1 - x0) * 2 * math.pi * 3.5)) for i in range(0, n, 4)]
        for i in range(1, len(pts)):
            c = lerpc(SAND, GREEN, (math.cos(i * 4 / (x1 - x0) * 2 * math.pi * 3.5) + 1) / 2)
            d.line([pts[i - 1], pts[i]], fill=c, width=10)
        text(img, "GREEN", 40, 290, y - 160, GREEN, w="Bold", anchor="rm"); text(img, "DESERT", 40, 290, y + 160, SAND, w="Bold", anchor="rm")
        p = (x1 - x0) / 3.5
        if u > 0.5: d.line([(x0, y + 240), (x0 + p, y + 240)], fill=GOLD, width=5); text(img, "≈ 20,000 YEARS", 46, x0 + p / 2, y + 290, GOLD)
        text(img, "AGAIN AND AGAIN", 90, W / 2, 200, WHITE, u=ease(lt / 0.4))
    return img

def b_clock(sc, lt, dur, t):
    img = space(t); cx, cy, R = 640, 540, 320; d = ImageDraw.Draw(img)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(60, 80, 120), width=30)
    u = eout((lt - 0.2) / 2.0); h = sc.get("hours", 23.5) * u
    d.arc([cx - R, cy - R, cx + R, cy + R], -90, -90 + 360 * h / 24, fill=GOLD, width=30)
    if u > 0.98:
        d.arc([cx - R, cy - R, cx + R, cy + R], -90 + 360 * 23.5 / 24, 270, fill=RED, width=30)
        text(img, "−30 MIN", 44, cx + 120, cy - R - 60, RED)
    for k in range(24):
        a = math.radians(-90 + k * 15); d.line([(cx + (R - 50) * math.cos(a), cy + (R - 50) * math.sin(a)), (cx + (R - 30) * math.cos(a), cy + (R - 30) * math.sin(a))], fill=DIM, width=3)
    hh = int(h); mm = int((h - hh) * 60); text(img, f"{hh}h {mm:02d}m", 110, cx, cy, WHITE)
    text(img, "A DAY", 110, 1420, 420, GOLD, u=ease(lt / 0.4)); text(img, sc.get("label", ""), 40, 1420, 520, WHITE, w="Bold", u=ease((lt - 0.4) / 0.4), maxw=820)
    return img

def b_shell(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img); cx, top, bot = 640, 200, 900
    n = 46; u = eout((lt - 0.2) / 2.2)
    for k in range(n):
        q = k / n; y = bot - (bot - top) * q; w = 60 + 240 * q
        c = 150 + int(60 * ((k % 2) * 0.6 + 0.4 * math.sin(k)))
        if q <= u: d.rounded_rectangle([cx - w, y - (bot - top) / n, cx + w, y], 6, fill=(c, int(c * 0.88), int(c * 0.7)))
    mx, my = cx + 150, 470; d.ellipse([mx - 120, my - 120, mx + 120, my + 120], outline=WHITE, width=10); d.line([(mx + 85, my + 85), (mx + 180, my + 180)], fill=WHITE, width=22)
    text(img, "FOSSIL SHELL", 90, 1430, 400, WHITE, u=ease(lt / 0.4)); pill(img, "1 THIN LAYER = 1 DAY", 44, 1430, 520, fill=GOLD, u=ease((lt - 0.5) / 0.4))
    text(img, "≈ 70 million years old", 40, 1430, 620, TEAL, w="SemiBold", u=ease((lt - 0.9) / 0.4))
    return img

def b_moon(sc, lt, dur, t):
    img = space(t); m = sc["mode"]; ex, ey = 560, 540
    if m == "brake":
        bl = Image.new("L", (W, H), 0); ImageDraw.Draw(bl).ellipse([ex - 320, ey - 250, ex + 320, ey + 250], fill=110)
        img.paste(Image.new("RGB", (W, H), (60, 140, 255)), (0, 0), bl.filter(ImageFilter.GaussianBlur(12)))
        put_globe(img, ex, ey, 230, 20, -t * 20, t, glow=False); d = ImageDraw.Draw(img)
        mx = 1500; halo(img, mx, ey, 90, (200, 200, 210), 90); d = ImageDraw.Draw(img); d.ellipse([mx - 70, ey - 70, mx + 70, ey + 70], fill=(200, 200, 205)); d.ellipse([mx - 30, ey - 20, mx - 5, ey + 5], fill=(170, 170, 178))
        d.arc([ex - 300, ey - 300, ex + 300, ey + 300], 200, 320, fill=GOLD, width=8); d.polygon([(ex + 150, ey - 268), (ex + 192, ey - 236), (ex + 140, ey - 228)], fill=GOLD)
        pill(img, "TIDES = A BRAKE ON EARTH'S SPIN", 40, 1030, 860, fill=GOLD); text(img, "(tidal bulge exaggerated)", 30, 1030, 930, DIM, w="SemiBold")
    else:
        put_globe(img, 360, ey, 200, 20, -t * 20, t); d = ImageDraw.Draw(img)
        mx = 1300 + 220 * eout((lt - 0.3) / max(1.5, dur - 0.5)); d.line([(600, ey), (mx - 90, ey)], fill=(70, 90, 130), width=3)
        halo(img, mx, ey, 90, (200, 200, 210), 90); d = ImageDraw.Draw(img); d.ellipse([mx - 70, ey - 70, mx + 70, ey + 70], fill=(200, 200, 205)); d.ellipse([mx - 30, ey - 20, mx - 5, ey + 5], fill=(170, 170, 178))
        d.polygon([(mx + 100, ey), (mx + 80, ey - 16), (mx + 80, ey + 16)], fill=GOLD); d.line([(mx + 76, ey), (mx + 140, ey)], fill=GOLD, width=0)
        text(img, "+3.8 CM", 130, 1100, 250, GOLD, u=ease(lt / 0.4)); text(img, "FARTHER AWAY EVERY YEAR", 48, 1100, 360, WHITE, w="Bold", u=ease((lt - 0.3) / 0.4))
        text(img, "(distance not to scale)", 30, 1100, 920, DIM, w="SemiBold")
    return img

def b_mountain(sc, lt, dur, t):
    img = space(t, drift=2); m = sc["mode"]; d = ImageDraw.Draw(img); sea = 520 if m not in ("above", "everest") else 760; sc_ = 52 if m != "full" else 42   # px per km
    if m == "versus":
        base = 900; u = eout((lt - 0.2) / 1.2)
        for km in range(0, 12, 2):
            y = base - km * 60; d.line([(260, y), (1700, y)], fill=(40, 50, 75), width=2); d.text((230, y), f"{km} km", font=F(26, "SemiBold"), fill=DIM, anchor="rm")
        hm, he = 10.2 * 60 * u, 8.85 * 60 * eout((lt - 0.6) / 1.2)
        d.polygon([(380, base), (740, base - hm), (840, base - hm), (1180, base)], fill=(95, 80, 70)); text(img, "MAUNA KEA · base to peak", 34, 790, base + 40, WHITE, w="Bold")
        d.polygon([(1220, base), (1450, base - he), (1490, base - he * 0.95), (1680, base)], fill=(150, 160, 185)); d.polygon([(1430, base - he * 0.9), (1450, base - he), (1490, base - he * 0.95), (1475, base - he * 0.88)], fill=WHITE)
        text(img, "EVEREST · above sea level", 34, 1450, base + 40, WHITE, w="Bold")
        if lt > 1.6: pill(img, "+ 1.3 KM", 48, 1000, base - 10.2 * 60 - 60, u=ease((lt - 1.6) / 0.4))
        return img
    d.rectangle([0, sea, W, H], fill=(10, 36, 84)); d.line([(0, sea), (W, sea)], fill=(70, 150, 230), width=3); text(img, "SEA LEVEL", 28, W - 140, sea - 24, (110, 170, 230), w="Bold")
    if m == "everest":
        he = 8.849 * sc_ * eout((lt - 0.2) / 1.2); x0 = 960
        d.polygon([(x0 - 330, sea), (x0 - 20, sea - he), (x0 + 30, sea - he * 0.95), (x0 + 330, sea)], fill=(150, 160, 185)); d.polygon([(x0 - 40, sea - he * 0.9), (x0 - 20, sea - he), (x0 + 30, sea - he * 0.95), (x0 + 15, sea - he * 0.88)], fill=WHITE)
        if lt > 1.3: pill(img, "EVEREST ≈ 8,849 M", 44, x0, sea - he - 60, u=ease((lt - 1.3) / 0.4))
        return img
    he = 8.85 * sc_ * (eout((lt - 0.2) / 1.0) if m == "above" else 1)
    d.polygon([(1250, sea), (1460, sea - he), (1500, sea - he * 0.95), (1700, sea)], fill=(150, 160, 185)); d.polygon([(1440, sea - he * 0.9), (1460, sea - he), (1500, sea - he * 0.95), (1485, sea - he * 0.88)], fill=WHITE)
    text(img, "EVEREST 8.8 km", 34, 1475, sea + 34 if m == "above" else sea - he - 40, WHITE, w="Bold")
    ab = 4.2 * sc_ * (eout((lt - 0.6) / 1.0) if m == "above" else 1)
    if m == "full":
        dn = 6.0 * sc_ * eout((lt - 0.3) / 1.6); d.polygon([(160, sea + dn), (560, sea - ab), (680, sea - ab), (1080, sea + dn)], fill=(95, 80, 70))
        d.rectangle([0, sea, W, sea + 4], fill=(70, 150, 230)); d.rectangle([0, sea + dn, W, H], fill=(6, 20, 46))
        d.line([(120, sea - ab), (120, sea + dn)], fill=GOLD, width=5)
        if lt > 1.9: pill(img, "≈ 10.2 KM", 46, 620, sea + dn * 0.55, u=ease((lt - 1.9) / 0.4))
        text(img, "≈ 6 km UNDER WATER", 34, 620, sea + 50, (150, 200, 255), w="Bold")
    else:
        d.polygon([(380, sea), (560, sea - ab), (680, sea - ab), (860, sea)], fill=(95, 80, 70))
        if lt > 1.5: pill(img, "MAUNA KEA ≈ 4.2 KM", 40, 620, sea - ab - 60, u=ease((lt - 1.5) / 0.4))
    return img

def b_bulge(sc, lt, dur, t):
    img = space(t); m = sc["mode"]; cx, cy, A, B = 760, 540, 420, 330; d = ImageDraw.Draw(img)
    halo(img, cx, cy, 440, (30, 90, 200), 90); d = ImageDraw.Draw(img)
    a_ = A if m != "shape" else B + (A - B) * eout((lt - 0.3) / 1.6)
    d.ellipse([cx - B, cy - B, cx + B, cy + B], outline=(70, 90, 130), width=3)
    d.ellipse([cx - a_, cy - B, cx + a_, cy + B], fill=(22, 70, 140), outline=TEAL, width=5)
    for k in range(0, 2 * int(a_), 40): d.line([(cx - a_ + k, cy), (cx - a_ + k + 20, cy)], fill=GOLD, width=3)
    d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=WHITE)
    if m == "shape":
        text(img, "NOT A PERFECT BALL", 72, 1500, 420, WHITE, maxw=760); pill(img, "BULGES AT THE EQUATOR", 38, 1500, 520, fill=TEAL, u=ease((lt - 0.8) / 0.4))
        text(img, "(exaggerated)", 32, 1500, 600, DIM, w="SemiBold")
        return img
    def onell(lat_deg, ext=0):
        a = math.radians(lat_deg); return cx + (a_ + ext) * math.cos(a) * -1 if False else cx + (a_) * math.cos(a), cy - B * math.sin(a)
    ev, ch = onell(28), onell(-1.5)
    for (px, py), nm, col, hgt in ((ev, "EVEREST", WHITE, 70), (ch, "CHIMBORAZO", GOLD, 52)):
        dx, dy = px - cx, py - cy; L_ = math.hypot(dx, dy); ux, uy = dx / L_, dy / L_
        tip = (px + ux * hgt, py + uy * hgt); d.polygon([(px - uy * 34, py + ux * 34), tip, (px + uy * 34, py - ux * 34)], fill=col)
        text(img, nm, 34, tip[0] + 110, tip[1] - 10 if nm == "EVEREST" else tip[1] + 30, col, w="Bold", u=ease((lt - 0.3) / 0.4))
        if m == "lines":
            u = eout((lt - 0.5) / 1.2); d.line([(cx, cy), (cx + (tip[0] - cx) * u, cy + (tip[1] - cy) * u)], fill=col, width=5)
    if m == "lines" and lt > 1.9:
        pill(img, "CHIMBORAZO: ≈ 2 KM FARTHER", 40, 1480, 780, u=ease((lt - 1.9) / 0.4)); text(img, "from Earth's center", 36, 1480, 850, WHITE, w="SemiBold", u=ease((lt - 2.1) / 0.4))
    if m == "peaks": text(img, "ECUADOR · ALMOST ON THE EQUATOR", 40, 1480, 780, TEAL, w="Bold", maxw=760)
    return img

def cutaway(img, cx, cy, R, t, glowk=1.0):
    put_globe(img, cx, cy, R, 15, 30 - t * 4, t)
    d = ImageDraw.Draw(img)
    layers = [(1.0, (120, 70, 40)), (0.97, (205, 85, 40)), (0.55, (250, 160, 50)), (0.19, (255, 236, 180))]
    for f, c in layers: d.pieslice([cx - R * f, cy - R * f, cx + R * f, cy + R * f], -90, 0, fill=c)
    halo(img, cx, cy, R * 0.25, (255, 220, 140), int(200 * glowk))
    return img

def b_core(sc, lt, dur, t):
    img = space(t); cx, cy, R = 540, 540, 410; cutaway(img, cx, cy, R, t)
    if sc["mode"] == "cut":
        for i, (f, nm) in enumerate(((0.985, "CRUST"), (0.78, "MANTLE"), (0.38, "OUTER CORE · LIQUID"), (0.1, "INNER CORE · SOLID IRON"))):
            u = ease((lt - 0.3 - i * 0.35) / 0.35); y = cy - R * f + 6
            if u > 0: d = ImageDraw.Draw(img); d.line([(cx + 8, y), (1180, 220 + i * 150)], fill=DIM, width=2); text(img, nm, 46, 1200, 220 + i * 150, GOLD if i == 3 else WHITE, w="Bold", anchor="lm", u=u, maxw=680)
    else:
        v = 6000 * eout((lt - 0.2) / 1.8); text(img, f"{int(v):,} °C", 160, 1440, 430, GOLD, maxw=820)
        text(img, "EDGE OF THE INNER CORE", 46, 1440, 555, WHITE, w="Bold"); text(img, "estimate ± 500 °C", 34, 1440, 625, TEAL, w="SemiBold", u=ease((lt - 1.0) / 0.4))
    return img

def b_anvil(sc, lt, dur, t):
    img = space(t); cx, cy = 760, 540; d = ImageDraw.Draw(img); g = 40 - 22 * eout((lt - 0.3) / 1.0)
    for sgn in (-1, 1):
        y0 = cy + sgn * g; d.polygon([(cx - 210, y0 + sgn * 230), (cx + 210, y0 + sgn * 230), (cx + 60, y0), (cx - 60, y0)], fill=(190, 225, 245)); d.polygon([(cx - 210, y0 + sgn * 230), (cx + 210, y0 + sgn * 230), (cx + 150, y0 + sgn * 260), (cx - 150, y0 + sgn * 260)], fill=(150, 195, 225))
    if lt > 1.2:
        d.line([(80, 120), (cx, cy)], fill=(255, 70, 60), width=6); d.line([(80, 960), (cx, cy)], fill=(255, 70, 60), width=6)
        halo(img, cx, cy, 40, (255, 180, 90), 255); d = ImageDraw.Draw(img)
    if lt > 2.4:
        d.line([(cx, cy), (1300, cy - 4)], fill=(120, 230, 255), width=5); d.line([(cx, cy), (1300, cy + 110)], fill=(120, 230, 255), width=3); d.line([(cx, cy), (1300, cy - 110)], fill=(120, 230, 255), width=3)
    d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=(110, 110, 120))
    for i, (s, at, col) in enumerate((("DIAMONDS", 0.3, WHITE), ("LASERS", 1.2, (255, 120, 100)), ("X-RAYS", 2.4, (120, 230, 255)))):
        text(img, s, 64, 1580, 380 + i * 110, col, u=ease((lt - at) / 0.4))
    return img

def b_sunvs(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img)
    for i, (x, nm, col, inner) in enumerate(((560, "INNER CORE (EDGE)", (255, 200, 120), (255, 240, 200)), (1360, "SURFACE OF THE SUN", (255, 160, 60), (255, 220, 120)))):
        u = back((lt - i * 0.5) / 0.5)
        if u <= 0: continue
        r = 200 * min(1.1, u); halo(img, x, 470, r * 1.3, col, 200); d = ImageDraw.Draw(img); d.ellipse([x - r, 470 - r, x + r, 470 + r], fill=col); d.ellipse([x - r * 0.7, 470 - r * 0.7, x + r * 0.7, 470 + r * 0.7], fill=inner)
        text(img, nm, 42, x, 760, WHITE, w="Bold")
    if lt > 1.1: text(img, "≈", 200, W / 2, 460, GOLD, u=ease((lt - 1.1) / 0.3))
    return img

def b_gold(sc, lt, dur, t):
    img = space(t); m = sc["mode"]; cx, cy = 760, 540
    if m in ("sink", "core"):
        R = 400
        if "mo" not in _hz:
            a = (lowf(2 * R, 2 * R, 40, 21) * 120 + lowf(2 * R, 2 * R, 12, 22) * 50)
            _hz["mo"] = np.clip(np.dstack([150 + a, 50 + a * 0.6, 20 + a * 0.15]), 0, 255).astype(np.uint8)
        mol = Image.fromarray(_hz["mo"]); msk = Image.new("L", (2 * R, 2 * R), 0); ImageDraw.Draw(msk).ellipse([0, 0, 2 * R - 1, 2 * R - 1], fill=255)
        halo(img, cx, cy, R * 1.1, (255, 120, 40), 140); img.paste(mol, (cx - R, cy - R), msk); d = ImageDraw.Draw(img)
        r = random.Random(5)
        for k in range(60):
            ang = r.uniform(0, 6.283); d0 = r.uniform(0.35, 0.95); sp = r.uniform(0.15, 0.3)
            dist = max(0.0, d0 - sp * lt) if m == "sink" else r.uniform(0, 0.14)
            x, y = cx + R * dist * math.cos(ang), cy + R * dist * math.sin(ang); s = 9
            gold_ = m == "core" or (k % 4 == 0)
            d.ellipse([x - s, y - s, x + s, y + s], fill=GOLD if gold_ else (110, 110, 120))
        if m == "core":
            halo(img, cx, cy, 120, (255, 210, 90), 255); d = ImageDraw.Draw(img); d.ellipse([cx - 70, cy - 70, cx + 70, cy + 70], fill=(255, 214, 110))
            text(img, "GOLD · PLATINUM", 80, 1530, 430, GOLD, maxw=700); text(img, "pulled down with the iron", 40, 1530, 520, WHITE, w="SemiBold", u=ease((lt - 0.5) / 0.4))
        else:
            text(img, "IRON SINKS", 90, 1530, 430, WHITE); text(img, "to form the core", 44, 1530, 520, TEAL, w="SemiBold", u=ease((lt - 0.4) / 0.4))
    elif m == "coat":
        u = ease((lt - 0.4) / 1.8); R = 380; cx = 580
        put_globe(img, cx, cy, R, 15, 20 - t * 6, t)
        if u > 0:
            g = globe(R, 15, 20 - t * 6, clouds=-1, tex=GOLDTEX); a = np.asarray(g).copy(); a[..., 3] = (a[..., 3] * u).astype(np.uint8)
            halo(img, cx, cy, R * 1.12, (255, 190, 60), int(150 * u)); paste(img, Image.fromarray(a, "RGBA"), cx, cy)
        text(img, "4 METERS", 140, 1440, 420, GOLD, u=ease((lt - 1.0) / 0.4), maxw=820); text(img, "OF PRECIOUS METALS", 46, 1440, 530, WHITE, w="Bold", u=ease((lt - 1.3) / 0.4))
        text(img, "over the ENTIRE surface", 40, 1440, 600, TEAL, w="SemiBold", u=ease((lt - 1.6) / 0.4))
    elif m == "person":
        base = 900; px_m = 150; d = ImageDraw.Draw(img); u = eout((lt - 0.2) / 1.6)
        d.rectangle([0, base, W, H], fill=(40, 46, 60))
        gh = 4 * px_m * u; d.rectangle([980, base - gh, 1800, base], fill=(230, 176, 60)); d.rectangle([980, base - gh, 1800, base - gh + 14], fill=(255, 226, 140))
        hx, hh = 760, 1.75 * px_m; c = (200, 215, 235)
        d.ellipse([hx - 22, base - hh, hx + 22, base - hh + 44], fill=c); d.rounded_rectangle([hx - 34, base - hh + 50, hx + 34, base - hh * 0.45], 20, fill=c)
        d.rectangle([hx - 28, base - hh * 0.47, hx - 6, base], fill=c); d.rectangle([hx + 6, base - hh * 0.47, hx + 28, base], fill=c)
        for k in range(0, 5): y = base - k * px_m; d.line([(940, y), (965, y)], fill=DIM, width=3); d.text((925, y), f"{k} m", font=F(26, "SemiBold"), fill=DIM, anchor="rm")
        text(img, "≈ 1.75 m", 34, hx, base - hh - 40, WHITE, w="Bold"); text(img, "THE GOLDEN LAYER: 4 m", 50, 1390, base - 4 * px_m - 60, GOLD, u=ease((lt - 1.4) / 0.4))
    elif m == "rocks":
        d = ImageDraw.Draw(img); x0, y0 = 300, 360
        pts = [(x0, y0 + 80), (x0 + 220, y0), (x0 + 560, y0 + 30), (x0 + 720, y0 + 180), (x0 + 640, y0 + 420), (x0 + 260, y0 + 460), (x0 + 40, y0 + 330)]
        rock = Image.new("RGB", (W, H), (96, 100, 110)); rd = ImageDraw.Draw(rock)
        for k in range(10): y = y0 + 30 + k * 44; rd.line([(x0 - 20, y), (x0 + 760, y + 30 * math.sin(k))], fill=(130, 134, 146) if k % 2 else (70, 74, 84), width=12)
        msk = Image.new("L", (W, H), 0); ImageDraw.Draw(msk).polygon(pts, fill=255); img.paste(rock, (0, 0), msk)
        d = ImageDraw.Draw(img); d.polygon(pts, outline=(150, 156, 170), width=5)
        mx, my = x0 + 470, y0 + 210; halo(img, mx, my, 120, (120, 200, 255), 80); d = ImageDraw.Draw(img)
        d.ellipse([mx - 120, my - 120, mx + 120, my + 120], outline=WHITE, width=10); d.line([(mx + 85, my + 85), (mx + 190, my + 190)], fill=WHITE, width=22)
        text(img, "GREENLAND ROCKS", 72, 1460, 380, WHITE, u=ease(lt / 0.4), maxw=780); pill(img, "≈ 4 BILLION YEARS OLD", 40, 1460, 480, fill=GOLD, u=ease((lt - 0.4) / 0.4))
        text(img, "a slightly different chemistry", 40, 1460, 580, TEAL, w="SemiBold", u=ease((lt - 1.0) / 0.4), maxw=780)
    else:   # meteors
        put_globe(img, cx, cy + 120, 360, 15, 20 - t * 6, t); d = ImageDraw.Draw(img)
        r = random.Random(8)
        for k in range(9):
            ph = (lt * 0.45 + k / 9) % 1; ang = r.uniform(-2.9, -1.7); L0 = 900 * (1 - ph)
            x, y = cx + math.cos(ang) * (360 + L0), cy + 120 + math.sin(ang) * (360 + L0)
            for j in range(16):
                q = j / 16; xx, yy = x + math.cos(ang) * q * 160, y + math.sin(ang) * q * 160
                d.ellipse([xx - 7 * (1 - q), yy - 7 * (1 - q), xx + 7 * (1 - q), yy + 7 * (1 - q)], fill=(255, int(220 - 80 * q), int(120 - 100 * q)))
            halo(img, x, y, 18, (255, 220, 120), 230); d = ImageDraw.Draw(img)
        text(img, "A STORM OF METEORITES", 70, 1450, 220, GOLD, maxw=860); text(img, "after the core had formed", 40, 1450, 300, WHITE, w="SemiBold", u=ease((lt - 0.4) / 0.4))
    return img

def b_recap(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img)
    text(img, "QUICK RECAP", 92, W / 2, 150, GOLD, u=1)
    n = len(sc["items"])
    for i, s in enumerate(sc["items"]):
        u = ease((lt - 0.3 - i * (dur - 1.0) / n) / 0.3); y = 300 + i * 120
        if u <= 0: continue
        d.rounded_rectangle([520, y - 32, 584, y + 32], 12, outline=TEAL, width=5)
        if u > 0.6: d.line([(532, y), (550, y + 20), (596, y - 36)], fill=(90, 235, 150), width=10)
        text(img, s, 62, 630, y, WHITE, anchor="lm", u=u, maxw=1150)
    return img

def b_outro(sc, lt, dur, t):
    img = space(t); horizon(img, t); d = ImageDraw.Draw(img)
    text(img, sc.get("q", "Which one sounded the MOST fake?"), 74, W / 2, 220, WHITE)
    click = sc.get("click_at", 1.6); on = ease((lt - click) / 0.25); cx, cy, w_, h_ = W / 2, 420, 300, 130
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=GOLD if on > 0.5 else (50, 56, 90), outline=WHITE, width=6)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; d.ellipse([kx - h_ / 2 + 16, cy - h_ / 2 + 16, kx + h_ / 2 - 16, cy + h_ / 2 - 16], fill=WHITE)
    text(img, "FAKE", 60, cx - w_ / 2 - 110, cy, WHITE if on < 0.5 else DIM); text(img, "TRUE", 60, cx + w_ / 2 + 110, cy, GOLD if on >= 0.5 else DIM)
    pill(img, "SUBSCRIBE · NEW DEEP DIVE EVERY TUE & FRI", 40, W / 2, 610, fill=RED, ink=WHITE, u=ease((lt - click - 0.4) / 0.4))
    return img

BEATS = dict(cold=b_cold, chapter=b_chapter, text=b_text, counter=b_counter, globe=b_globe, orbit=b_orbit, compare=b_compare, stamp=b_stamp,
             nemo=b_nemo, lightning=b_lightning, drift=b_drift, sahara=b_sahara, clock=b_clock, shell=b_shell, moon=b_moon,
             mountain=b_mountain, bulge=b_bulge, core=b_core, anvil=b_anvil, sunvs=b_sunvs, gold=b_gold, recap=b_recap, outro=b_outro)
NOBLOOM = ("sahara",)

# ---------------- narration & score ----------------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.42, tail=1.5)
n = len(voice); tt = np.arange(n) / SR; music = np.zeros(n, np.float32)
pads = [[110.0, 164.81, 220.0, 277.18], [98.0, 146.83, 196.0, 246.94], [87.31, 130.81, 174.61, 220.0], [82.41, 123.47, 164.81, 207.65]]
seg = 6.0
for i in range(int(total / seg) + 1):
    a, b = int(i * seg * SR), min(int((i + 1.4) * seg * SR), n)
    if a >= n: break
    lt = tt[a:b] - i * seg; env = np.clip(lt / 2.5, 0, 1) * np.clip((seg * 1.4 - lt) / 2.5, 0, 1)
    for f in pads[i % 4]: music[a:b] += (np.sin(2 * np.pi * f * lt) + 0.3 * np.sin(2 * np.pi * f * 1.004 * lt)) * env * 0.03
music += 0.02 * np.sin(2 * np.pi * 41.2 * tt) * (0.6 + 0.4 * np.sin(2 * np.pi * tt / 11))
for k in range(int(total * 0.6)):
    place(music, random.uniform(0, total), tone(random.choice([659.25, 880, 987.77, 1318.5]), 2.4, decay=1.6, harm=(1, 2)), 0.010)
hook_hit(music, 0.35)
for ln in spec["lines"]:
    if ln["scene"]["type"] == "chapter": place(music, ln["_s"], tone(55, 1.2, decay=3, harm=(1, 2)), 0.25); whoosh(music, ln["_s"], 0.18)
    if ln["scene"]["type"] == "stamp": place(music, ln["_s"] + 0.5 + 0.25 * len(ln["scene"]["lines"]), tone(70, 0.4, decay=14, harm=(1, 2, 3)), 0.35)
for ln in spec["lines"][1:]: whoosh(music, ln["_s"], 0.06)
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
    d.rounded_rectangle([x - 28, y - 14, x + tw + 28, y + size + 18], 24, fill=INKD)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=GOLD if on else WHITE); x += d.textlength(w + " ", font=f)

def frame(t):
    ln = core.active_line(spec, t, lead=0.05) or spec["lines"][0]
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]; sc = ln["scene"]
    if t < 0.05: lt = 1.5                                                                       # frame 0 = full hook
    img = BEATS[sc["type"]](sc, lt, dur, t)
    if sc["type"] not in NOBLOOM: img = bloom(img, 0.45)
    d = ImageDraw.Draw(img)
    if ln["_ch"]: d.text((W - 60, 50), f"{ln['_ch']:02d} / {NCH:02d}", font=F(34, "Bold"), fill=GOLD, anchor="ra")
    d.rounded_rectangle([44, 40, 330, 92], 22, fill=INKD); d.text((62, 48), "SOUNDS FAKE  ?!", font=F(30, "Black"), fill=(220, 225, 240))
    caption(img, t)
    d.rectangle([0, H - 6, int(W * t / total), H], fill=GOLD)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","):
            Image.frombytes("RGB", (W, H), frame(float(tt_))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s")
        for ln in spec["lines"]: print(f"{ln['_s']:7.1f} {ln['scene']['type']:10s} {ln['scene'].get('mode', '')}")
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
