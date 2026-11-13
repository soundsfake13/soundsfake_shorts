"""Day 17 — WEATHER-HUD style (HD 189733 b: a planet where it rains glass, sideways).
An interplanetary weather broadcast: deep-space navy, a per-pixel shaded cobalt gas giant with drifting bands and an
atmosphere rim, cyan HUD chrome (corner brackets, LIVE bug, mission clock, scrolling forecast ticker), glowing glass
shards streaking sideways, data panels (target lock, cloud report, temperature gauge, wind meter), signal-glitch
transitions (chroma split + scan band). Chakra Petch titles + Share Tech Mono data.
Ending: a HUD verdict slider snaps from FAKE (red) to TRUE (cyan). Music: synth arpeggio + pad + kick, data blips, wind.
Usage: python3 engine/styles/day17_weatherhud.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
_F = {}
def F(kind, s):
    k = (kind, int(s))
    if k not in _F:
        path = {"bold": f"{FONTS}/ChakraPetch-Bold.ttf", "semi": f"{FONTS}/ChakraPetch-SemiBold.ttf",
                "mono": f"{FONTS}/ShareTechMono-Regular.ttf"}[kind]
        _F[k] = ImageFont.truetype(path, int(s))
    return _F[k]

NAVY, CYAN, COBALT, AMBER, WHITE, RED = (5, 10, 28), (110, 236, 255), (46, 102, 255), (255, 186, 64), (236, 244, 255), (255, 84, 96)
def A(c, a): return tuple(c) + (int(max(0, min(1, a)) * 255),)

# ---------- background: space gradient + stars + faint HUD grid + scanlines (built once) ----------
def _bg():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    g = (yy / H)[..., None]
    img = np.array((4, 8, 22), np.float32) * (1 - g) + np.array((8, 18, 44), np.float32) * g
    d2 = ((xx - 540) ** 2 + (yy - 1150) ** 2) / 700 ** 2
    img += np.array((20, 50, 120), np.float32) * (np.exp(-d2) * 0.5)[..., None]
    r = np.random.default_rng(17)
    for _ in range(420):
        x, y = r.integers(0, W), r.integers(0, H); b = r.uniform(60, 230)
        img[y, x] += b;
        if b > 200 and x + 1 < W and y + 1 < H: img[y, x + 1] += b * 0.5; img[y + 1, x] += b * 0.5
    grid = ((xx % 90 < 1.2) | (yy % 90 < 1.2)).astype(np.float32) * 9
    img += np.array((40, 120, 160), np.float32) / 160 * grid[..., None]
    img *= (1 - 0.07 * ((yy.astype(int) % 4) == 0))[..., None]
    return Image.fromarray(img.clip(0, 255).astype(np.uint8)).convert("RGBA")
BG = _bg()

# ---------- planet: banded cobalt gas giant, per-pixel shaded ----------
def _tex():
    h, w = 400, 1024; r = np.random.default_rng(3)
    lat = np.linspace(-1, 1, h)[:, None]; lon = np.linspace(0, 2 * np.pi, w, endpoint=False)[None, :]
    b = np.zeros((h, w), np.float32)
    for k in range(7):
        f = r.uniform(6, 34); ph = r.uniform(0, 6.28); amp = r.uniform(0.25, 1.0) / (1 + k * 0.4)
        wob = 0.05 * np.sin(lon * r.integers(2, 6) + r.uniform(0, 6.28)) * np.sin(lat * 7 + ph)
        b += amp * np.sin((lat + wob) * f + ph)
    b = (b - b.min()) / (b.max() - b.min())
    # a couple of storm ovals
    for (la, lo, sa, so) in ((0.35, 2.0, 0.05, 0.25), (-0.5, 4.6, 0.04, 0.18)):
        dd = ((lat - la) / sa) ** 2 + ((np.angle(np.exp(1j * (lon - lo)))) / so) ** 2
        b = b * (1 - 0.6 * np.exp(-dd)) + 0.95 * 0.6 * np.exp(-dd)
    c0, c1, c2 = np.array((6, 20, 90)), np.array((30, 84, 235)), np.array((150, 205, 255))
    b = np.clip((b - 0.5) * 1.5 + 0.5, 0, 1)
    col = np.where(b[..., None] < 0.55, c0 + (c1 - c0) * (b[..., None] / 0.55), c1 + (c2 - c1) * ((b[..., None] - 0.55) / 0.45))
    return col.astype(np.float32)
TEX = _tex()
_GEO = {}
def planet(R, rot, light=(-0.55, -0.35, 0.76)):
    R = int(R)
    if R not in _GEO:
        s = 2 * R + 2; yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
        u, v = (xx - R) / R, (yy - R) / R; rr = u * u + v * v; m = rr < 1
        z = np.sqrt(np.clip(1 - rr, 0, 1)); lat = np.arcsin(np.clip(v, -1, 1)); lon = np.arctan2(u, z)
        L = np.array(light) / np.linalg.norm(light); dif = np.clip(u * L[0] + v * L[1] + z * L[2], 0, 1)
        edge = np.clip((1 - np.sqrt(rr)) * R / 1.5, 0, 1)
        rim = np.exp(-((1 - np.sqrt(np.clip(rr, 0, 1))) / 0.07) ** 2)
        ti = ((lat / (np.pi / 2) * 0.5 + 0.5) * (TEX.shape[0] - 1)).astype(int)
        _GEO[R] = (lon, ti, dif, edge, rim, m)
    lon, ti, dif, edge, rim, m = _GEO[R]
    lj = (((lon + rot) / (2 * np.pi)) % 1.0 * TEX.shape[1]).astype(int) % TEX.shape[1]
    col = TEX[ti, lj]
    shade = (0.14 + 0.95 * dif ** 0.9)[..., None]
    col = col * shade + np.array((120, 200, 255), np.float32) * (rim * (0.35 + 0.6 * dif))[..., None]
    spec_ = np.clip(dif, 0, 1) ** 40 * 60; col += spec_[..., None]
    arr = np.dstack([col.clip(0, 255), edge * 255]).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")
_HALO = {}
def put_planet(img, cx, cy, R, rot):
    R = int(R)
    if R not in _HALO:
        s = int(2 * R * 1.5); m = Image.new("L", (s, s), 0)
        ImageDraw.Draw(m).ellipse([s / 2 - R * 1.03, s / 2 - R * 1.03, s / 2 + R * 1.03, s / 2 + R * 1.03], fill=170)
        m = m.filter(ImageFilter.GaussianBlur(R * 0.09))
        lay = Image.new("RGBA", (s, s), (70, 150, 255, 0)); lay.putalpha(m); _HALO[R] = lay
    h = _HALO[R]; img.alpha_composite(h, (int(cx - h.width / 2), int(cy - h.height / 2)))
    p = planet(R, rot); img.alpha_composite(p, (int(cx - R - 1), int(cy - R - 1)))

# ---------- glass shards blown sideways ----------
SH = [(random.Random(i).uniform(0, 1), random.Random(i + 999).uniform(0, 1), random.Random(i + 77).uniform(0.4, 1.0)) for i in range(220)]
def shards(img, t, n=140, speed=1.0, slope=0.10, y0=0, y1=H, alpha=1.0, length=1.0):
    if alpha <= 0.01: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    span = y1 - y0
    for i in range(n):
        fx, fy, z = SH[i]
        v = (900 + 1700 * z) * speed
        x = (fx * (W + 600) + t * v) % (W + 600) - 300
        y = y0 + fy * span + (x + 300) * slope
        L = (40 + 150 * z) * length * (0.4 + 0.6 * min(1.5, speed)); w = 1 + int(3 * z)
        c = A((210, 245, 255) if i % 5 else (255, 230, 170), alpha * (0.35 + 0.65 * z))
        d.line([(x - L, y - L * slope), (x - L * 0.35, y - L * 0.35 * slope)], fill=A(c[:3], alpha * 0.35 * z), width=max(1, w - 1))
        hw = 1.5 + 2.5 * z
        d.polygon([(x - L * 0.45, y - L * 0.45 * slope), (x - L * 0.12, y - L * 0.12 * slope - hw), (x + 4, y), (x - L * 0.12, y - L * 0.12 * slope + hw * 0.6)], fill=c)
        d.line([(x - L * 0.12, y - L * 0.12 * slope - hw * 0.5), (x + 2, y)], fill=A(WHITE, alpha * z), width=1)
    glow = lay.filter(ImageFilter.GaussianBlur(5))
    img.alpha_composite(glow); img.alpha_composite(lay)

# ---------- HUD chrome ----------
def chrome(img, t, total):
    d = ImageDraw.Draw(img); c = A(CYAN, 0.75); L = 60; m = 34
    for (x, y, sx, sy) in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m - 20, 1, -1), (W - m, H - m - 20, -1, -1)):
        d.line([(x, y), (x + sx * L, y)], fill=c, width=4); d.line([(x, y), (x, y + sy * L)], fill=c, width=4)
    f = F("mono", 30)
    if int(t * 2) % 2 == 0: d.ellipse([78, 92, 98, 112], fill=A(RED, 1))
    d.text((110, 102), "LIVE", font=F("semi", 32), fill=A(WHITE, 0.95), anchor="lm")
    d.text((196, 102), "EXO-WEATHER NETWORK", font=f, fill=A(CYAN, 0.8), anchor="lm")
    d.text((W - 76, 102), f"T+{int(t // 60):02d}:{t % 60:04.1f}", font=f, fill=A(CYAN, 0.8), anchor="rm")
    # ticker
    y = 1790; d.rectangle([0, y - 26, W, y + 26], fill=A((4, 12, 32), 0.85)); d.line([(0, y - 26), (W, y - 26)], fill=A(CYAN, 0.5), width=2)
    d.rectangle([0, y - 26, 190, y + 26], fill=A(AMBER, 1));
    msg = "HD 189733 b  ·  SILICATE CLOUDS  ·  GLASS RAIN  ·  WINDS 7,000+ KM/H  ·  AIR 1,000+ °C  ·  63 LIGHT-YEARS AWAY  ·  "
    fm = F("mono", 30); mw = fm.getlength(msg); off = (t * 140) % mw
    tl = Image.new("RGBA", (W - 190, 52), (0, 0, 0, 0)); td = ImageDraw.Draw(tl)
    for k in range(3): td.text((-off + k * mw, 26), msg, font=fm, fill=A(WHITE, 0.85), anchor="lm")
    img.alpha_composite(tl, (190, y - 26))
    d.text((95, y), "FORECAST", font=F("semi", 30), fill=A(NAVY, 1), anchor="mm")

def text(img, s, font, x, y, fill=WHITE, alpha=1.0, anchor="mm", glow=0.0, gcol=None):
    if alpha <= 0.01: return
    bb = font.getbbox(s, anchor=anchor); pad = 30
    w_, h_ = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad; ox, oy = int(x + bb[0] - pad), int(y + bb[1] - pad)
    m = Image.new("L", (w_, h_), 0); ImageDraw.Draw(m).text((x - ox, y - oy), s, font=font, fill=255, anchor=anchor)
    patch = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    sh = m.filter(ImageFilter.GaussianBlur(10)).point(lambda p: int(min(255, p * (glow or 0.8) * alpha * 1.4)))
    patch = Image.new("RGBA", (w_, h_), tuple(gcol or (2, 6, 18)) + (255,)); patch.putalpha(sh)
    tl = Image.new("RGBA", (w_, h_), tuple(fill) + (255,)); tl.putalpha(m.point(lambda p: int(p * alpha)))
    patch.alpha_composite(tl); img.alpha_composite(patch, (ox, oy))
def fit(s, kind, size, maxw=W - 130):
    while F(kind, size).getlength(s) > maxw and size > 30: size -= 4
    return F(kind, size)
def rise(lt, delay=0.0, dur=0.35, instant=False): return 1.0 if instant else eout((lt - delay) / dur)
def tag(img, s, x, y, col=CYAN, alpha=1.0, size=34, fill_bg=False, anchor="mm"):
    if alpha <= 0.01: return
    f = F("mono", size); tw = f.getlength(s); d = ImageDraw.Draw(img)
    x0 = x - tw / 2 if anchor == "mm" else x
    box = [x0 - 22, y - size * 0.85, x0 + tw + 22, y + size * 0.85]
    if fill_bg: d.rectangle(box, fill=A(col, alpha))
    else: d.rectangle(box, fill=A((4, 12, 32), 0.75 * alpha), outline=A(col, alpha), width=3)
    d.text((x0, y), s, font=f, fill=A(NAVY if fill_bg else col, alpha), anchor="lm")
def panel(img, x0, y0, x1, y1, title=None, alpha=1.0, col=CYAN):
    d = ImageDraw.Draw(img); d.rectangle([x0, y0, x1, y1], fill=A((4, 14, 38), 0.72 * alpha), outline=A(col, 0.55 * alpha), width=2)
    k = 26
    for (x, y, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([(x, y), (x + sx * k, y)], fill=A(col, alpha), width=5); d.line([(x, y), (x, y + sy * k)], fill=A(col, alpha), width=5)
    if title:
        f = F("mono", 30); tw = f.getlength(title)
        d.rectangle([x0 + 40, y0 - 20, x0 + 40 + tw + 28, y0 + 20], fill=A(col, alpha)); d.text((x0 + 54, y0), title, font=f, fill=A(NAVY, alpha), anchor="lm")

# ---------- scenes ----------
def S_hook(sc, lt, dur, t):
    img = BG.copy(); inst = not sc.get("loop")
    put_planet(img, 540, 1180, 400, t * 0.25)
    shards(img, t, 150, 1.0, 0.09)
    d = ImageDraw.Draw(img)
    if int(t * 3) % 3 != 2:
        tag(img, "   SEVERE WEATHER ALERT", W / 2, 205, RED, 1.0, 34)
        tx0 = W / 2 - F("mono", 34).getlength("   SEVERE WEATHER ALERT") / 2 + 4
        d.polygon([(tx0, 222), (tx0 + 40, 222), (tx0 + 20, 186)], fill=A(RED, 1)); d.text((tx0 + 20, 211), "!", font=F("bold", 26), fill=A(NAVY, 1), anchor="mm")
    text(img, "THIS PLANET", F("bold", 112), W / 2, 330, WHITE, 1.0, glow=0.9)
    text(img, "RAINS GLASS.", F("bold", 140), W / 2, 462, WHITE, 1.0, glow=0.9)
    sx = 18 * math.sin(t * 9) * math.exp(-t * 1.5)                             # sideways jolt
    fS = F("bold", 176); x0s = W / 2 - fS.getlength("SIDEWAYS.") / 2 + sx
    for k, (yy_, ln_) in enumerate(((572, 120), (604, 190), (640, 150), (672, 90))):
        d.line([(x0s - 30 - ln_, yy_), (x0s - 30, yy_)], fill=A(AMBER, 0.85), width=8 - k)
    text(img, "SIDEWAYS.", F("bold", 176), W / 2 + sx, 620, AMBER, 1.0, glow=1.0, gcol=(60, 30, 0))
    if sc.get("loop"):
        tag(img, "FULL FORECAST INCOMING", W / 2, 790, AMBER, eout((lt - 0.2) / 0.3), 36, fill_bg=True)
    # target reticle on planet
    r = 455 + 8 * math.sin(t * 4); c = A(CYAN, 0.55)
    for a0 in (20, 110, 200, 290): d.arc([540 - r, 1180 - r, 540 + r, 1180 + r], a0, a0 + 50, fill=c, width=3)
    return img

def S_locate(sc, lt, dur, t):
    img = BG.copy(); d = ImageDraw.Draw(img)
    text(img, "TARGET LOCKED", F("mono", 44), W / 2, 210, CYAN, rise(lt, 0.0))
    n = int(63 * ease((lt - 0.1) / 1.2))
    text(img, f"{n}", F("bold", 300), W / 2 - 120, 420, WHITE, 1.0, glow=0.9)
    text(img, "LIGHT-", F("bold", 92), W / 2 + 230, 372, AMBER, 1.0); text(img, "YEARS", F("bold", 92), W / 2 + 230, 468, AMBER, 1.0)
    x0, y0, x1, y1 = 80, 640, W - 80, 1460; panel(img, x0, y0, x1, y1, "STAR MAP · VULPECULA", rise(lt, 0.1))
    r = random.Random(5)
    for _ in range(90):
        x, y = r.uniform(x0 + 20, x1 - 20), r.uniform(y0 + 30, y1 - 20); s = r.choice((2, 2, 3, 4))
        d.ellipse([x - s, y - s, x + s, y + s], fill=A(WHITE, r.uniform(0.4, 0.9)))
    ex, ey = 200, 1380; tx, ty = 690, 900
    d.ellipse([ex - 12, ey - 12, ex + 12, ey + 12], fill=A((90, 200, 120), 1)); text(img, "EARTH", F("mono", 34), ex + 30, ey + 2, WHITE, 1.0, anchor="lm")
    v = ease((lt - 0.3) / 1.0)
    if v > 0:
        n_ = 30; pts = [(ex + (tx - ex) * i / n_ * v, ey + (ty - ey) * i / n_ * v) for i in range(n_ + 1)]
        for i in range(0, n_, 2): d.line([pts[i], pts[i + 1]], fill=A(CYAN, 0.9), width=4)
    lk = ease((lt - 1.1) / 0.5); rr = 160 - 90 * lk
    if lt > 0.2:
        c = A(AMBER if lk >= 1 else CYAN, 1)
        for a0 in (0, 90, 180, 270): d.arc([tx - rr, ty - rr, tx + rr, ty + rr], a0 + 15 + 90 * (1 - lk), a0 + 75 + 90 * (1 - lk), fill=c, width=5)
        d.line([(tx - rr - 30, ty), (tx - rr + 10, ty)], fill=c, width=4); d.line([(tx + rr - 10, ty), (tx + rr + 30, ty)], fill=c, width=4)
    pv = back((lt - 1.5) / 0.5)
    if pv > 0.02:
        put_planet(img, tx, ty, max(8, int(60 * pv)), t * 0.3)
        text(img, "HD 189733 b", F("semi", 50), tx, ty - 150, WHITE, min(1, pv))
    cv = eout((lt - 2.4) / 0.4)
    if cv > 0:
        tag(img, "TYPE: GAS GIANT", 140, 1100, CYAN, cv, 34, anchor="lm")
        d.rectangle([140 - 22, 1180 - 30, 200, 1180 + 30], fill=A(COBALT, cv), outline=A(WHITE, cv), width=2)
        tag(img, "COLOR: DEEP COBALT BLUE", 232, 1180, CYAN, cv, 34, anchor="lm")
    return img

PART = [(random.Random(i).uniform(110, W - 110), random.Random(i + 5).uniform(760, 1420), random.Random(i + 9).randint(0, 13)) for i in range(260)]
CENT = [(170 + (k % 7) * 124 + (40 if k // 7 else 0), 1040 + (k // 7) * 190) for k in range(14)]
def S_sky(sc, lt, dur, t):
    img = BG.copy(); d = ImageDraw.Draw(img)
    text(img, "CLOUD REPORT", F("bold", 120), W / 2, 280, WHITE, rise(lt), glow=0.9)
    text(img, "what's in the sky?", F("mono", 46), W / 2, 400, CYAN, rise(lt, 0.15))
    x0, y0, x1, y1 = 80, 640, W - 80, 1470; panel(img, x0, y0, x1, y1, "ATMOSPHERE SCAN", 1.0)
    for i in range(6):                                                            # layered haze
        yy = y0 + 60 + i * 130; d.rectangle([x0 + 4, yy, x1 - 4, yy + 128], fill=A((20 + i * 10, 50 + i * 18, 120 + i * 18), 0.22))
    p = ease((lt - 1.2) / 1.6)
    for i, (px, py, c) in enumerate(PART):
        cx, cy = CENT[c]; jx = 10 * math.sin(t * 2 + i); jy = 8 * math.cos(t * 1.7 + i * 0.7)
        x = px + (cx - px) * p + jx * (1 - p); y = py + (cy - py) * p + jy * (1 - p)
        s = 4 if i % 3 else 5; d.rectangle([x - s, y - s, x + s, y + s], fill=A((200, 230, 255), 0.85 * (1 - p * 0.8)))
    if p > 0.6:
        g = eout((p - 0.6) / 0.4)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        dx = 70 * max(0.0, lt - 3.3)
        for k_, (cx, cy) in enumerate(CENT):
            cx = (cx + dx * (0.8 + 0.4 * (k_ % 3) / 2) - 110) % (W - 220) + 110
            R = 30 * g; ld.ellipse([cx - R, cy - R * 1.15, cx + R, cy + R], fill=A((160, 220, 255), 0.55 * g), outline=A(WHITE, g), width=3)
            ld.ellipse([cx - R * 0.5, cy - R * 0.7, cx - R * 0.1, cy - R * 0.3], fill=A(WHITE, g))
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(6))); img.alpha_composite(lay)
    tag(img, "SILICATE PARTICLES", W / 2, 720, CYAN, eout((lt - 0.4) / 0.3), 38)
    if p > 0.8: tag(img, "= TINY DROPS OF GLASS", W / 2, 1400, AMBER, eout((p - 0.8) / 0.2), 40, fill_bg=True)
    return img

def S_temp(sc, lt, dur, t):
    img = BG.copy(); d = ImageDraw.Draw(img)
    text(img, "TEMPERATURE", F("bold", 116), W / 2, 280, WHITE, rise(lt), glow=0.9)
    text(img, "DAYSIDE AIR", F("mono", 44), W / 2, 395, CYAN, rise(lt, 0.15))
    cx, cy, R = 540, 1030, 380; a0, a1 = 150, 390; vmax = 1200
    val = 1000 * ease((lt - 0.2) / 1.5) + (40 * (0.5 + 0.5 * math.sin(lt * 6)) if lt > 1.7 else 0)
    d.arc([cx - R, cy - R, cx + R, cy + R], a0, a1, fill=A((30, 60, 110), 1), width=34)
    steps = 80
    for i in range(steps):
        f_ = i / steps
        if f_ > val / vmax: break
        col = tuple(int(a + (b - a) * min(1, f_ * 1.25)) for a, b in zip(CYAN, AMBER)) if f_ < 0.75 else tuple(int(a + (b - a) * (f_ - 0.75) / 0.25) for a, b in zip(AMBER, RED))
        d.arc([cx - R, cy - R, cx + R, cy + R], a0 + (a1 - a0) * f_, a0 + (a1 - a0) * (f_ + 1 / steps) + 0.6, fill=A(col, 1), width=34)
    for v in range(0, 1201, 100):
        a = math.radians(a0 + (a1 - a0) * v / vmax); big = v % 200 == 0
        r0, r1 = R - 34, R - (70 if big else 52)
        d.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + r1 * math.cos(a), cy + r1 * math.sin(a))], fill=A(WHITE, 0.8), width=4 if big else 2)
        if big: text(img, str(v), F("mono", 32), cx + (R - 110) * math.cos(a), cy + (R - 110) * math.sin(a), WHITE, 0.8)
    a = math.radians(a0 + (a1 - a0) * min(val, vmax) / vmax)
    d.line([(cx, cy), (cx + (R - 80) * math.cos(a), cy + (R - 80) * math.sin(a))], fill=A(AMBER, 1), width=10)
    d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=A(AMBER, 1))
    shown = min(1000, int(val // 10 * 10))
    text(img, f"{shown:,}°C" + ("+" if lt > 1.7 else ""), F("bold", 150), cx, cy + 250, WHITE, 1.0, glow=1.0)
    if lt > 1.9: tag(img, "HEAT WARNING", W / 2, 1450, RED, eout((lt - 1.9) / 0.3), 40, fill_bg=int(t * 3) % 2 == 0)
    return img

def S_wind(sc, lt, dur, t):
    img = BG.copy(); sp = ease((lt - 0.2) / 1.6)
    shards(img, t, 60, 0.3 + 1.4 * sp, 0.25 * (1 - sp) + 0.06, 600, 1500, 0.35 + 0.4 * sp, 0.6 + sp)
    d = ImageDraw.Draw(img)
    text(img, "WIND SPEED", F("bold", 120), W / 2, 280, WHITE, rise(lt), glow=0.9)
    v = int(7000 * sp // 50 * 50)
    text(img, f"{v:,}", F("bold", 250), W / 2, 560, AMBER if sp >= 1 else WHITE, 1.0, glow=1.0, gcol=(40, 20, 0) if sp >= 1 else None)
    text(img, "KM/H" + ("  AND UP" if sp >= 1 else ""), F("semi", 64), W / 2, 740, CYAN, 1.0)
    # anemometer
    cx, cy = 540, 1060; ang = (lt * (1 + 18 * sp) * 2.2)
    d.line([(cx, cy), (cx, 1300)], fill=A(WHITE, 0.9), width=10)
    for k in range(3):
        a = ang + k * 2 * math.pi / 3; ex, ey = cx + 170 * math.cos(a), cy + 60 * math.sin(a)
        d.line([(cx, cy), (ex, ey)], fill=A(WHITE, 0.9), width=8)
        d.pieslice([ex - 46, ey - 34, ex + 46, ey + 34], 90 if math.cos(a) > 0 else -90, 270 if math.cos(a) > 0 else 90, fill=A(CYAN, 1))
    d.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], fill=A(AMBER, 1))
    # meter
    x0, x1, y = 120, W - 120, 1400; d.rectangle([x0, y - 22, x1, y + 22], outline=A(CYAN, 0.8), width=3)
    segs = 28
    for i in range(int(segs * sp)):
        col = CYAN if i < segs * 0.6 else (AMBER if i < segs * 0.85 else RED)
        sx = x0 + 8 + i * (x1 - x0 - 16) / segs; d.rectangle([sx, y - 14, sx + (x1 - x0 - 16) / segs - 6, y + 14], fill=A(col, 1))
    for k, lab in ((0, "0"), (0.5, "3,500"), (1, "7,000")):
        text(img, lab, F("mono", 30), x0 + (x1 - x0) * k, y + 52, WHITE, 0.8)
    return img

def S_side(sc, lt, dur, t):
    img = BG.copy()
    put_planet(img, 60, 1080, 520, t * 0.35)
    shards(img, t, 220, 1.6, 0.03, 200, 1700, 1.0, 1.6)
    d = ImageDraw.Draw(img)
    text(img, "GLASS RAIN", F("bold", 150), W / 2, 280, WHITE, 1.0, glow=1.0)
    u = eout((lt - 0.1) / 0.35)
    # "down" arrow, crossed out
    ax, ay = 300, 560
    d.line([(ax, ay - 90), (ax, ay + 70)], fill=A(WHITE, 0.55 * u), width=14); d.polygon([(ax - 40, ay + 50), (ax + 40, ay + 50), (ax, ay + 110)], fill=A(WHITE, 0.55 * u))
    text(img, "DOWN", F("semi", 60), ax, ay + 170, WHITE, 0.55 * u)
    xv = eout((lt - 1.0) / 0.25)
    if xv > 0:
        d.line([(ax - 90, ay - 90), (ax - 90 + 180 * xv, ay - 90 + 200 * xv)], fill=A(RED, 1), width=18)
        d.line([(ax + 90, ay - 90), (ax + 90 - 180 * xv, ay - 90 + 200 * xv)], fill=A(RED, 1), width=18)
    sv = eout((lt - 1.6) / 0.35)
    if sv > 0:
        bx, by = 600, 560; L = 340 * sv
        d.line([(bx, by), (bx + L - 40, by)], fill=A(AMBER, 1), width=22); d.polygon([(bx + L - 60, by - 50), (bx + L + 20, by), (bx + L - 60, by + 50)], fill=A(AMBER, 1))
        text(img, "SIDEWAYS", F("bold", 92), bx + 180, by + 140, AMBER, sv, glow=1.0, gcol=(40, 20, 0))
    return img

def S_end(sc, lt, dur, t):
    img = BG.copy()
    put_planet(img, 540, 1180, 400, t * 0.25)
    shards(img, t, 150, 1.0, 0.09, alpha=0.8)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.3)
    text(img, "SOUNDS FAKE?", F("bold", 130), W / 2, 250, WHITE, 1.0, glow=1.0)
    d = ImageDraw.Draw(img)
    x0, x1, y = 200, W - 200, 480; col = RED if on < 0.5 else CYAN
    panel(img, 90, 370, W - 90, 590, "VERDICT", 1.0, col)
    d.rounded_rectangle([x0 + 150, y - 50, x1 - 150, y + 50], 50, fill=A((10, 24, 56), 1), outline=A(col, 1), width=4)
    kx = (x0 + 200) + (x1 - x0 - 400) * on
    d.ellipse([kx - 44, y - 44, kx + 44, y + 44], fill=A(col, 1))
    text(img, "FAKE", F("bold", 66), x0 + 30, y, RED, 1.0 - 0.65 * on)
    text(img, "TRUE", F("bold", 66), x1 - 30, y, CYAN, 0.35 + 0.65 * on, glow=on)
    if on > 0.6:
        u = eout((lt - click - 0.2) / 0.35)
        text(img, "IT'S TRUE.", F("bold", 150), W / 2, 680, CYAN, u, glow=1.0, gcol=(0, 30, 50))
        text(img, "Follow for more.", F("semi", 64), W / 2, 800, WHITE, eout((lt - click - 0.4) / 0.35))
    return img

SCENES = dict(hook=S_hook, locate=S_locate, sky=S_sky, temp=S_temp, wind=S_wind, side=S_side, end=S_end)

# ---------- audio: synth arpeggio + pad + soft kick, data blips, wind ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
bpm = 112; beat = 60 / bpm; st = beat / 4
chords = [(110.0, [220.0, 261.63, 329.63]), (87.31, [174.61, 220.0, 261.63]), (130.81, [261.63, 329.63, 392.0]), (98.0, [196.0, 246.94, 293.66])]
k = 0
while k * st < total:
    root, ch = chords[int(k * st // (beat * 4)) % 4]
    place(music, k * st, tone(ch[k % 3] * (2 if k % 8 >= 4 else 1), 0.25, decay=14, harm=(1, 2, 3, 4)), 0.03)
    if k % 4 == 0:
        s = np.arange(int(0.25 * SR)) / SR; kick = np.sin(2 * np.pi * (45 + 90 * np.exp(-s * 30)) * s) * np.exp(-s * 14)
        place(music, k * st, kick.astype(np.float32), 0.12)
        place(music, k * st, tone(root, 0.45, decay=6, harm=(1, 2)), 0.05)
    k += 1
for b in range(int(total / (beat * 4)) + 1):
    root, ch = chords[b % 4]; s0 = b * beat * 4; seg = np.arange(int(beat * 4.3 * SR)) / SR
    env = np.sin(np.pi * np.clip(seg / (beat * 4.3), 0, 1)) ** 1.2
    sig = sum(np.sin(2 * np.pi * f * seg) * 0.5 + np.sin(2 * np.pi * f * 1.004 * seg) * 0.5 for f in ch) * env
    place(music, s0, sig.astype(np.float32), 0.018)
def blip(at, f0=1600, gain=0.08):
    for j in range(3): place(music, at + j * 0.06, tone(f0 * (1 + 0.25 * j), 0.05, decay=60, harm=(1,)), gain)
def wind(at, dur, gain):
    m = int(dur * SR); nz = np.random.default_rng(int(at * 10)).normal(0, 1, m)
    nz = np.convolve(nz, np.ones(18) / 18, mode="same"); s = np.arange(m) / SR
    env = np.clip(s / 0.8, 0, 1) * np.clip((dur - s) / 0.4, 0, 1) * (0.6 + 0.4 * np.sin(s * 3.1))
    place(music, at, (nz * env).astype(np.float32), gain)
hook_hit(music, 0.35); blip(0.02, 1400, 0.1)
for s_ in scene_starts(spec): whoosh(music, s_, 0.08); blip(s_ + 0.03)
for ln in spec["lines"]:
    ty = ln["scene"]["type"]
    if ty in ("hook", "side", "end") and not ln["scene"].get("loop"): wind(ln["_s"], ln["_se"] - ln["_s"], 0.05 if ty != "side" else 0.12)
    if ty == "wind": wind(ln["_s"], ln["_se"] - ln["_s"], 0.11)
    if ty == "end": place(music, ln["_s"] + ln["scene"].get("click_at", 0.45), tone(1318.5, 1.2, decay=4, harm=(1, 2, 3)), 0.12)
write_audio(voice, music, work + "_audio.wav", music_gain=0.65, duck=0.35)

# ---------- captions, transitions, progress ----------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 76
    while F("bold", size).getlength(" ".join(ws)) > W - 220 and size > 36: size -= 4
    f = F("bold", size); tw = f.getlength(" ".join(ws)); x = (W - tw) / 2; y = 1600
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    bx = [x - 36, y - 18, x + tw + 36, y + size + 22]
    d.rectangle(bx, fill=(3, 9, 26, 228), outline=A(CYAN, 0.9), width=3)
    d.rectangle([bx[0], bx[1], bx[0] + 10, bx[3]], fill=A(CYAN, 1))
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=AMBER + (255,) if on else (255, 255, 255, 255)); x += f.getlength(w + " ")
    img.alpha_composite(lay)

def glitch(img, k, t):
    a = np.array(img); s = int(22 * k)
    a[..., 0] = np.roll(a[..., 0], s, axis=1); a[..., 2] = np.roll(a[..., 2], -s, axis=1)
    yb = int(H * (1 - k)) % H; a[max(0, yb - 40):yb + 40, :, :3] = np.clip(a[max(0, yb - 40):yb + 40, :, :3].astype(int) + 60, 0, 255)
    for j in range(4):
        y0 = int((t * 997 + j * 431) % (H - 60)); a[y0:y0 + 24] = np.roll(a[y0:y0 + 24], int(40 * k * (1 if j % 2 else -1)), axis=1)
    return Image.fromarray(a, "RGBA")

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t)
    li = spec["lines"].index(ln)
    if li > 0 and spec["lines"][li - 1]["scene"]["type"] != ln["scene"]["type"] and lt < 0.28:
        img = glitch(img, 1 - ease(lt / 0.28), t)
    chrome(img, t, total); caption(img, t)
    d = ImageDraw.Draw(img); d.rectangle([0, H - 8, W, H], fill=(3, 9, 26, 255)); d.rectangle([0, H - 8, int(W * t / total), H], fill=CYAN + (255,))
    return img.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
