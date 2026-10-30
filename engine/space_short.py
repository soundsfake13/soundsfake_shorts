"""GLOWING SPACE style (after 'Ray-traced black hole bends its glowing accretion disk' on claudevideo.org).
Deep starfield with nebula haze, shaded 3D planets and rings rendered per pixel, bloom, thin glowing type.
Best for space topics. Usage: python3 space_short.py spec.json out.mp4 [t1,t2,... preview]
"""
import json, math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
rng = np.random.default_rng(8); random.seed(8)
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
def FT(size, w="SemiBold"): return ImageFont.truetype(f"{FD}InterDisplay-{w}.otf", size)
GOLD, ICE, WHITE, DIM, WATER = (255, 206, 120), (140, 210, 255), (240, 244, 255), (150, 160, 190), (60, 140, 255)

# ---------------- background: nebula + stars ----------------
def lowf(h, w, cell, seed):
    r = np.random.default_rng(seed); s = r.random((h // cell + 2, w // cell + 2)).astype(np.float32)
    return np.asarray(Image.fromarray((s * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255
yy = np.linspace(0, 1, H)[:, None]
neb = (lowf(H, W, 240, 1) * 0.6 + lowf(H, W, 90, 2) * 0.4) ** 2.2
neb2 = (lowf(H, W, 300, 3)) ** 3
BG = np.zeros((H, W, 3), np.float32)
BG += np.array([4, 6, 16], np.float32)
BG += neb[..., None] * np.array([40, 22, 70], np.float32) + neb2[..., None] * np.array([10, 45, 70], np.float32)
BG *= (1 - 0.35 * np.abs(yy - 0.45))[..., None]
STARS = [(rng.uniform(0, W), rng.uniform(0, H), rng.choice([0.6, 1.0, 1.6], p=[0.6, 0.3, 0.1]), rng.uniform(0, 6.3), rng.uniform(0.3, 1)) for _ in range(520)]

def background(t, drift=(6, -3), zoom=0.0):
    img = Image.fromarray(BG.astype(np.uint8)).convert("RGB")
    d = ImageDraw.Draw(img)
    for (x, y, s, ph, depth) in STARS:
        px = (x + drift[0] * t * depth - W / 2) * (1 + zoom * depth) + W / 2
        py = (y + drift[1] * t * depth - H / 2) * (1 + zoom * depth) + H / 2
        px %= W; py %= H
        a = 0.55 + 0.45 * math.sin(t * 2.3 + ph)
        c = int(255 * a * (0.5 + 0.5 * depth)); r = s * (0.8 + depth)
        if zoom > 0.02:
            vx, vy = (px - W / 2) * zoom * depth * 0.4, (py - H / 2) * zoom * depth * 0.4
            d.line([(px, py), (px - vx, py - vy)], fill=(c, c, min(255, c + 20)), width=max(1, int(r)))
        else:
            d.ellipse([px - r, py - r, px + r, py + r], fill=(c, c, min(255, c + 20)))
    return img

# ---------------- planets ----------------
band = np.cumsum(rng.normal(0, 1, 600)); band = (band - band.min()) / (band.max() - band.min())
band = np.convolve(band, np.ones(9) / 9, mode="same")
BANDCOL = np.stack([np.interp(band, [0, 0.5, 1], [c1, c2, c3]) for c1, c2, c3 in
                    [(200, 236, 250), (150, 200, 230), (95, 150, 190)]], 1).astype(np.float32)   # tan -> cream
LONG = lowf(256, 512, 16, 9)
_geo = {}
def saturn(r, rot, tilt=0.42, roll=-0.22):
    """Return RGBA (numpy float 0..1) image of Saturn with rings; center = image center."""
    key = (r, round(tilt, 3), round(roll, 3))
    if key not in _geo:
        Rw = int(r * 2.4); Rh = int(max(r, r * 2.4 * math.sin(tilt)) + 4)
        X, Y = np.meshgrid(np.arange(-Rw, Rw, dtype=np.float32), np.arange(-Rh, Rh, dtype=np.float32))
        xr = X * math.cos(roll) + Y * math.sin(roll); yr = -X * math.sin(roll) + Y * math.cos(roll)
        d2 = (xr ** 2 + yr ** 2) / r ** 2
        disk = np.clip((1 - np.sqrt(d2)) * r * 0.9, 0, 1)
        z = np.sqrt(np.clip(1 - d2, 0, 1))
        L = np.array([-0.55, -0.45, 0.70]); L /= np.linalg.norm(L)
        lam = np.clip((xr / r) * L[0] + (yr / r) * L[1] + z * L[2], 0, 1)
        shade = 0.10 + 1.0 * lam ** 0.9 + 0.25 * np.clip(1 - z, 0, 1) ** 3 * (lam > 0.05)
        v = np.clip(yr / r + 0.18 * math.cos(tilt) * (1 - (xr / r) ** 2) * 0, -1, 1)
        bi = ((v * 0.5 + 0.5) * 599).astype(int)
        ulon = np.arcsin(np.clip(xr / (r * np.sqrt(np.clip(1 - v ** 2, 1e-4, 1))), -1, 1)) / math.pi + 0.5
        rr = np.sqrt(xr ** 2 + (yr / max(0.08, math.sin(tilt))) ** 2) / r
        prof = np.zeros_like(rr)
        for a, b_, k in ((1.24, 1.52, 0.35), (1.52, 1.95, 0.95), (2.02, 2.27, 0.70)):
            prof += ((rr > a) & (rr < b_)) * k * (0.75 + 0.25 * np.sin(rr * 90))
        ring_a = np.clip(prof, 0, 1) * 0.92
        ring_far = yr < 0
        # planet's shadow on the far ring (light from upper-left -> shadow lower-right)
        _geo[key] = dict(disk=disk, shade=shade, bi=bi, ulon=ulon, v=v, ring_a=ring_a, far=ring_far, size=(2 * Rw, 2 * Rh))
    g = _geo[key]
    lu = ((g["ulon"] * 0.5 + rot) % 1 * 511).astype(int); lv = ((g["v"] * 0.5 + 0.5) * 255).astype(int)
    col = BANDCOL[g["bi"]] * (0.93 + 0.14 * LONG[lv, lu])[..., None]
    planet = np.clip(col * g["shade"][..., None], 0, 255)
    ringcol = np.array([235, 220, 190], np.float32)
    out = np.zeros(g["disk"].shape + (4,), np.float32)
    back_a = g["ring_a"] * g["far"] * (1 - g["disk"])
    out[..., :3] = ringcol * back_a[..., None]; out[..., 3] = back_a
    out[..., :3] = out[..., :3] * (1 - g["disk"][..., None]) + planet * g["disk"][..., None]
    out[..., 3] = np.maximum(out[..., 3], g["disk"])
    front_a = g["ring_a"] * (~g["far"])
    shadow = np.where(g["disk"] > 0, 0.55, 1.0)
    out[..., :3] = out[..., :3] * (1 - front_a[..., None]) + ringcol * shadow[..., None] * front_a[..., None]
    out[..., 3] = np.maximum(out[..., 3], front_a)
    return out

_earth = {}
def earth(r):
    if r not in _earth:
        X, Y = np.meshgrid(np.arange(-r, r, dtype=np.float32), np.arange(-r, r, dtype=np.float32))
        d2 = (X ** 2 + Y ** 2) / r ** 2; disk = np.clip((1 - np.sqrt(d2)) * r, 0, 1); z = np.sqrt(np.clip(1 - d2, 0, 1))
        lam = np.clip(-0.55 * X / r - 0.45 * Y / r + 0.7 * z, 0, 1)
        land = lowf(2 * r, 2 * r, max(2, r // 4), 5) > 0.55
        col = np.where(land[..., None], [70, 150, 90], [40, 100, 220]).astype(np.float32)
        col = col * (0.15 + lam[..., None]) + 120 * (1 - z[..., None]) ** 4
        o = np.zeros((2 * r, 2 * r, 4), np.float32); o[..., :3] = np.clip(col, 0, 255); o[..., 3] = disk
        _earth[r] = o
    return _earth[r]

def comp(base, rgba, cx, cy, alpha=1.0):
    """Composite float RGBA (0..255 rgb, 0..1 a) onto base float image at center."""
    h, w = rgba.shape[:2]; x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xs, ys = max(0, x0), max(0, y0); xe, ye = min(W, x0 + w), min(H, y0 + h)
    if xe <= xs or ye <= ys: return
    sub = rgba[ys - y0:ye - y0, xs - x0:xe - x0]; a = sub[..., 3:4] * alpha
    base[ys:ye, xs:xe] = base[ys:ye, xs:xe] * (1 - a) + sub[..., :3] * a

def bloom(arr, k=0.75):
    small = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    s = np.asarray(small).astype(np.float32); s = np.clip(s - 120, 0, 255) * 1.6
    b = Image.fromarray(s.astype(np.uint8)).filter(ImageFilter.GaussianBlur(7)).resize((W, H), Image.BILINEAR)
    return arr + np.asarray(b).astype(np.float32) * k

# ---------------- glowing type ----------------
_tx = {}
def gtext(txt, size, color=WHITE, track=0.12, weight="SemiBold", glow=0.9):
    key = (txt, size, color, weight)
    if key in _tx: return _tx[key]
    f = FT(size, weight); d0 = ImageDraw.Draw(Image.new("L", (4, 4)))
    widths = [d0.textlength(ch, font=f) for ch in txt]; tw = int(sum(widths) + track * size * (len(txt) - 1))
    pad = int(size * 0.6); m = Image.new("L", (tw + 2 * pad, int(size * 1.3) + 2 * pad), 0); d = ImageDraw.Draw(m)
    x = pad
    for ch, w_ in zip(txt, widths): d.text((x, pad), ch, font=f, fill=255); x += w_ + track * size
    a = np.asarray(m).astype(np.float32) / 255
    g = np.asarray(m.filter(ImageFilter.GaussianBlur(size * 0.18))).astype(np.float32) / 255
    o = np.zeros(a.shape + (4,), np.float32)
    o[..., :3] = np.array(color, np.float32) * np.clip(a + g * glow, 0, 1)[..., None]
    o[..., 3] = np.clip(a + g * glow * 0.8, 0, 1)
    _tx[key] = o
    return o

# ---------------- narration & music ----------------
voice, words, total = narrate(spec, default_gap=0.32)
n = len(voice); tt = np.arange(n) / SR; music = np.zeros(n, np.float32)
pads = [[110.0, 164.81, 220.0, 277.18], [98.0, 146.83, 196.0, 246.94], [87.31, 130.81, 174.61, 220.0], [82.41, 123.47, 164.81, 207.65]]
seg = 4.0
for i in range(int(total / seg) + 1):
    a, b = int(i * seg * SR), min(int((i + 1.4) * seg * SR), n)
    if a >= n: break
    lt = tt[a:b] - i * seg; env = np.clip(lt / 1.8, 0, 1) * np.clip((seg * 1.4 - lt) / 1.8, 0, 1)
    for f in pads[i % 4]:
        music[a:b] += (np.sin(2 * np.pi * f * lt) + 0.4 * np.sin(2 * np.pi * f * 1.003 * lt)) * env * 0.035
music += 0.03 * np.sin(2 * np.pi * 41.2 * tt) * (0.6 + 0.4 * np.sin(2 * np.pi * tt / 9))
for k in range(int(total * 1.3)):
    f = random.choice([880, 1046.5, 1318.5, 1567.98, 1760]); place(music, random.uniform(0, total), tone(f, 2.5, decay=1.6, harm=(1, 2)), 0.012)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.3)

# ---------------- scenes ----------------
def title_lines(arr, lines, lt, y0, size=104, accent=None, gap=1.25):
    for i, txt in enumerate(lines):
        u = ease((lt - 0.15 - i * 0.35) / 0.6)
        if u <= 0: continue
        col = GOLD if accent and accent.get(str(i)) else WHITE
        sz = size
        while gtext(txt, sz, col).shape[1] - sz * 1.2 > W - 110 and sz > 40: sz -= 6
        comp(arr, gtext(txt, sz, col), W / 2, y0 + i * size * gap + (1 - u) * 30, alpha=u)

def sc_hero(sc, lt, dur, t):
    arr = np.asarray(background(t)).astype(np.float32)
    r = int(250 + 20 * ease(lt / dur)); tilt = 0.36 + 0.06 * math.sin(lt * 0.5)
    comp(arr, saturn(r, t * 0.05, tilt), W / 2, 980, alpha=ease(lt / 0.8))
    title_lines(arr, sc["lines"], lt, sc.get("y", 300), size=sc.get("size", 100), accent=sc.get("accent"))
    return arr

def sc_words(sc, lt, dur, t):
    arr = np.asarray(background(t, zoom=0.08 * ease(lt / dur))).astype(np.float32)
    title_lines(arr, sc["lines"], lt, sc.get("y", 760), size=sc.get("size", 130), accent=sc.get("accent"), gap=1.4)
    return arr

def sc_compare(sc, lt, dur, t):
    arr = np.asarray(background(t)).astype(np.float32)
    comp(arr, saturn(230, t * 0.05, 0.4), 610, 860)
    u = ease((lt - 0.3) / 0.5)
    comp(arr, earth(28), 170, 540, alpha=u)
    comp(arr, gtext("EARTH", 34, ICE, glow=0.6), 170, 610, alpha=u)
    for k, (num, lab) in enumerate(sc["rows"]):
        v = ease((lt - 0.6 - k * 1.3) / 0.5)
        if v <= 0: continue
        comp(arr, gtext(num, 150, GOLD, weight="Bold"), 330, 1300 + k * 190, alpha=v)
        comp(arr, gtext(lab, 54, WHITE), 700, 1310 + k * 190, alpha=v)
    return arr

def sc_elements(sc, lt, dur, t):
    arr = np.asarray(background(t)).astype(np.float32)
    for k, (sym, name, x) in enumerate((("H", "HYDROGEN", 330), ("He", "HELIUM", 750))):
        u = ease((lt - 0.2 - k * 0.4) / 0.5)
        if u <= 0: continue
        y = 880 + 14 * math.sin(t * 1.6 + k)
        tile = np.zeros((300, 300, 4), np.float32)
        img = Image.new("L", (300, 300), 0); ImageDraw.Draw(img).rounded_rectangle([20, 20, 280, 280], 34, outline=255, width=6)
        m = np.asarray(img).astype(np.float32) / 255; gl = np.asarray(img.filter(ImageFilter.GaussianBlur(10))).astype(np.float32) / 255
        tile[..., :3] = np.array(ICE) * np.clip(m + gl, 0, 1)[..., None]; tile[..., 3] = np.clip(m + gl * 0.7, 0, 1)
        comp(arr, tile, x, y, alpha=u)
        comp(arr, gtext(sym, 150, WHITE, track=0.0, weight="Bold"), x, y - 10, alpha=u)
        comp(arr, gtext(name, 46, ICE), x, y + 210, alpha=u)
    if lt > 1.2: comp(arr, gtext(sc.get("label", "THE LIGHTEST GASES"), 60, GOLD), W / 2, 420, alpha=ease((lt - 1.2) / 0.5))
    return arr

def bar(arr, x, y, w, h, col, a=1.0):
    img = Image.new("L", (int(w) + 60, h + 60), 0); ImageDraw.Draw(img).rounded_rectangle([30, 30, 30 + max(4, int(w)), 30 + h], h // 2, fill=255)
    m = np.asarray(img).astype(np.float32) / 255; g = np.asarray(img.filter(ImageFilter.GaussianBlur(12))).astype(np.float32) / 255
    o = np.zeros(m.shape + (4,), np.float32); o[..., :3] = np.array(col) * np.clip(m + g * 0.8, 0, 1)[..., None]; o[..., 3] = np.clip(m + g * 0.6, 0, 1)
    comp(arr, o, x + (w + 60) / 2 - 30, y + h / 2, alpha=a)

def sc_density(sc, lt, dur, t):
    arr = np.asarray(background(t)).astype(np.float32)
    full = W - 240
    for k, (lab, val, col) in enumerate((("WATER", 1.0, WATER), ("SATURN", 0.69, GOLD))):
        u = eout((lt - 0.2 - k * 0.6) / 0.9)
        if u <= 0: continue
        y = 720 + k * 300
        comp(arr, gtext(lab, 56, WHITE), 120 + gtext(lab, 56).shape[1] / 2 - 34, y - 70, alpha=min(1, u * 2))
        bar(arr, 120, y, full * val * u, 70, col)
        comp(arr, gtext(f"{val * u:.2f}", 64, col, weight="Bold"), 120 + full * val * u - 90, y + 140, alpha=min(1, u * 2))
    comp(arr, gtext("GRAMS PER CM³", 40, DIM), W / 2, 1300, alpha=ease((lt - 1.0) / 0.5))
    return arr

def sc_float(sc, lt, dur, t):
    arr = np.asarray(background(t)).astype(np.float32)
    wl = 1180; r = 210
    p = eout(lt / 2.2); cy = -300 + (wl + 0.38 * r - (-300)) * p + 10 * math.sin(t * 2.2) * p
    comp(arr, saturn(r, t * 0.05, 0.38), W / 2, cy)
    # water: translucent glowing layer below the waterline
    below = np.zeros((H - wl, W, 3), np.float32)
    grad = np.linspace(0.55, 0.9, H - wl)[:, None, None]
    arr[wl:] = arr[wl:] * (1 - grad * 0.75) + np.array([10, 40, 90], np.float32) * grad
    img = Image.new("L", (W, H), 0); d = ImageDraw.Draw(img)
    d.line([(0, wl), (W, wl)], fill=255, width=4)
    if p > 0.95:
        for k in range(3):
            ph = ((lt - 2.0) * 0.5 + k / 3) % 1
            rx = r * (1.1 + ph * 1.6); d.ellipse([W / 2 - rx, wl - rx * 0.06, W / 2 + rx, wl + rx * 0.06], outline=int(255 * (1 - ph)), width=4)
    g = np.asarray(img.filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255; m = np.asarray(img).astype(np.float32) / 255
    arr += (np.clip(m + g, 0, 1)[..., None] * np.array(ICE, np.float32)) * 0.9
    if lt > 1.6: comp(arr, gtext(sc.get("label", "IT FLOATS"), 92, GOLD, weight="Bold"), W / 2, 420, alpha=ease((lt - 1.6) / 0.4))
    return arr

def sc_tub(sc, lt, dur, t):
    arr = np.asarray(background(t)).astype(np.float32)
    img = Image.new("L", (W, H), 0); d = ImageDraw.Draw(img); u = eout(lt / 0.9)
    x0, x1, y0, y1 = 140, W - 140, 760, 1120
    d.line([(x0 - 30, y0), (x1 + 30, y0)], fill=255, width=8)
    d.rounded_rectangle([x0, y0, x1, y1], 90, outline=255, width=8)
    d.rectangle([x0 + 20, y0 - 4, x1 - 20, y0 + 30], fill=0)
    for lx in (x0 + 90, x1 - 90): d.line([(lx, y1 - 10), (lx - 10, y1 + 70)], fill=255, width=10)
    d.line([(x1 - 120, y0), (x1 - 120, y0 - 120), (x1 - 60, y0 - 120)], fill=255, width=8)
    m = np.asarray(img).astype(np.float32) / 255 * u; g = np.asarray(img.filter(ImageFilter.GaussianBlur(10))).astype(np.float32) / 255 * u
    arr += np.clip(m + g * 0.8, 0, 1)[..., None] * np.array(WHITE, np.float32) * 0.85
    arr[y0 + 60:y1 - 20, x0 + 30:x1 - 30] = arr[y0 + 60:y1 - 20, x0 + 30:x1 - 30] * 0.6 + np.array([10, 40, 90]) * 0.4 * u
    comp(arr, saturn(120, t * 0.05, 0.38), W / 2, y0 + 70 + 6 * math.sin(t * 2), alpha=u)
    v = ease((lt - 0.8) / 0.5)
    img2 = Image.new("L", (W, 120), 0); d2 = ImageDraw.Draw(img2)
    d2.line([(x0, 60), (x1, 60)], fill=255, width=4); d2.line([(x0, 35), (x0, 85)], fill=255, width=4); d2.line([(x1, 35), (x1, 85)], fill=255, width=4)
    arr[1220:1340] += (np.asarray(img2).astype(np.float32) / 255 * v)[..., None] * np.array(GOLD, np.float32)
    comp(arr, gtext(sc.get("label", "≈ 120,000 KM"), 72, GOLD, weight="Bold"), W / 2, 1380, alpha=v)
    return arr

def sc_end(sc, lt, dur, t):
    arr = np.asarray(background(t)).astype(np.float32)
    click = sc.get("click_at", 0.9); on = ease((lt - click) / 0.25)
    img = Image.new("L", (W, H), 0); d = ImageDraw.Draw(img)
    cx, cy, w_, h_ = W / 2, 960, 340, 160
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, outline=255, width=8)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on
    d.ellipse([kx - h_ / 2 + 22, cy - h_ / 2 + 22, kx + h_ / 2 - 22, cy + h_ / 2 - 22], fill=255)
    m = np.asarray(img).astype(np.float32) / 255; g = np.asarray(img.filter(ImageFilter.GaussianBlur(14))).astype(np.float32) / 255
    col = np.array(GOLD if on > 0.5 else ICE, np.float32)
    arr += np.clip(m + g, 0, 1)[..., None] * col
    comp(arr, gtext("FAKE", 64, WHITE if on < 0.5 else DIM), cx - w_ / 2 - 140, cy)
    comp(arr, gtext("TRUE", 64, GOLD if on >= 0.5 else DIM), cx + w_ / 2 + 140, cy)
    if lt > click + 0.3: comp(arr, gtext("SOUNDS FAKE ?!", 96, GOLD, weight="Bold"), W / 2, 600, alpha=ease((lt - click - 0.3) / 0.4))
    return arr

SCENES = dict(hero=sc_hero, words=sc_words, compare=sc_compare, elements=sc_elements, density=sc_density,
              float=sc_float, tub=sc_tub, end=sc_end)

# ---------------- captions ----------------
groups = caption_groups(words, 3)
def caption(arr, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    arr[1560:1730] *= 0.55
    ws = [words[i][0].upper() for i in g]; size = 70
    f = FT(size); d0 = ImageDraw.Draw(Image.new("L", (4, 4)))
    def width(sz): return sum(gtext(w, sz, WHITE, track=0.02, glow=0.2).shape[1] - 2 * int(sz * 0.6) for w in ws) + 0.32 * sz * (len(ws) - 1)
    while width(size) > W - 160 and size > 40: size -= 4
    x = (W - width(size)) / 2
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        spr = gtext(w, size, GOLD if on else WHITE, track=0.02, glow=0.5 if on else 0.2)
        comp(arr, spr, x + spr.shape[1] / 2 - int(size * 0.6), 1645)
        x += spr.shape[1] - 2 * int(size * 0.6) + 0.32 * size

def frame(t, fi):
    ln = active_line(spec, t)
    if ln is None: arr = np.asarray(background(t)).astype(np.float32)
    else:
        lt = t - ln["_s"]; dur = ln["_se"] - ln["_s"]
        arr = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t)
        if lt < 0.25: arr = arr * ease((lt + 0.12) / 0.37)
    arr = bloom(arr)
    caption(arr, t)
    arr[H - 10:, :int(W * t / total)] = np.array(GOLD)
    return np.clip(arr, 0, 255).astype(np.uint8).tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","):
            Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path)
        print(f"done {total:.1f}s")
