"""Day 04 — STRATA style (sharks are older than trees).
A geology-survey cross-section: the camera digs straight down through layered, hand-textured rock (ochre, sienna,
umber, clay), a depth gauge on the right counts millions of years, fossils (dinosaur, early tree, shark) lie faint in
their layers and are "brushed clean" with a dashed survey ring when the camera reaches them, field-label cards in a
slab serif, then the camera pulls back to the whole rock column with brackets for the time gaps.
Ending: a carved stone slider moves from FAKE to TRUE.
Usage: python3 engine/styles/day04_strata.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
rng = np.random.default_rng(4); random.seed(4)
_f = {}
def ZS(size, bold=True):
    k = (size, bold)
    if k not in _f: _f[k] = ImageFont.truetype(f"{FONTS}/ZillaSlab-{'Bold' if bold else 'SemiBold'}.ttf", size)
    return _f[k]
D0 = ImageDraw.Draw(Image.new("L", (4, 4)))
def tw(txt, f): return D0.textlength(txt, font=f)

CREAM, UMBER, OCHRE, RUST, BONE = (246, 236, 214), (58, 36, 24), (226, 156, 58), (184, 72, 40), (236, 220, 186)
SKYT, SKYB = np.array([247, 236, 210], np.float32), np.array([236, 214, 172], np.float32)
K, SURF, MAXD = 9, 760, 540                       # px per million years, world y of the surface
def wy(d): return SURF + d * K

# ---------------- the rock column (one tall static image) ----------------
TH = SURF + MAXD * K
xs = np.arange(W)[None, :].astype(np.float32); ys = np.arange(TH)[:, None].astype(np.float32)
pal = [(222, 186, 128), (204, 142, 66), (172, 98, 56), (196, 128, 92), (150, 104, 70), (214, 170, 112),
       (128, 92, 70), (186, 116, 64)]
bounds, d = [0.0], 0.0
while d < MAXD: d += rng.uniform(14, 34); bounds.append(d)
def bline(dd, i):
    if i == 0: return SURF + 10 * np.sin(xs / 210 + 1.3) + 6 * np.sin(xs / 67)
    return wy(dd) + 16 * np.sin(xs / rng.uniform(140, 300) + i) + 7 * np.sin(xs / rng.uniform(40, 80) + 2 * i)
BL = [bline(dd, i) for i, dd in enumerate(bounds)]
idx = np.zeros((TH, W), np.int16)
for b in BL: idx += (ys >= b)
cols = np.zeros((len(BL) + 1, 3), np.float32)
for i in range(1, len(BL) + 1):
    dark = 1 - 0.32 * min(1, bounds[min(i, len(bounds) - 1)] / MAXD)
    cols[i] = np.array(pal[(i * 3) % len(pal)], np.float32) * dark
img = cols[idx]
sky = (idx == 0)[..., None]
skyg = SKYT + (SKYB - SKYT) * np.clip(ys / SURF, 0, 1)[..., None]
lam = 7 * np.sin(ys / 5.5 + 2.5 * np.sin(xs / 90 + ys / 300)) * (np.sin(ys / 37) > 0.1)        # fine laminations
img = img + lam[..., None] + rng.normal(0, 6, (TH, W, 1)).astype(np.float32)
edge = np.zeros((TH, W), bool); edge[1:] = idx[1:] != idx[:-1]
edge = edge | np.roll(edge, 1, 0) | np.roll(edge, 2, 0)
img[edge & (idx[..., None] > 0)[..., 0]] *= 0.62
img = np.where(sky, skyg, img)
soil = (idx == 1) & (ys < BL[0] + 18)                                                          # dark topsoil band
img[soil] = np.array([92, 62, 40], np.float32)
rock = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)); rd = ImageDraw.Draw(rock)
for x in range(-40, W + 60, 160):                                                              # far hills
    hx = x + rng.uniform(-30, 30); hh = rng.uniform(50, 110)
    rd.pieslice([hx - 170, SURF - hh, hx + 170, SURF + hh], 180, 360, fill=(226, 200, 156))
for x in range(0, W, 4):                                                                       # grass rim
    y0 = int(BL[0][0, x]); rd.line([(x, y0 + 4), (x + rng.uniform(-3, 3), y0 - rng.uniform(6, 18))], fill=(110, 120, 60), width=3)
for _ in range(900):                                                                           # pebbles
    px, pd = rng.uniform(0, W), rng.uniform(4, MAXD); py = wy(pd); r = rng.uniform(3, 11)
    base = np.array(rock.getpixel((int(px), int(min(TH - 1, py)))), np.float32)
    c = tuple(int(v) for v in np.clip(base * rng.choice([0.72, 1.18]), 0, 255))
    rd.ellipse([px - r, py - r * 0.6, px + r, py + r * 0.6], fill=c)
def shell(d, x, y, r, c):                                                                       # tiny spiral shells
    pts = [(x + r * (a / 12.6) * math.cos(a), y + r * (a / 12.6) * math.sin(a)) for a in np.linspace(0, 12.6, 60)]
    d.line(pts, fill=c, width=3)
for _ in range(40):
    pd = rng.uniform(30, MAXD); x = rng.uniform(40, 880); y = wy(pd)
    base = np.array(rock.getpixel((int(x), int(y))), np.float32)
    shell(rd, x, y, rng.uniform(10, 18), tuple(int(v) for v in base * 0.65))
TALL = np.asarray(rock)
PADT, PADB = 4200, 4200
TALLP = np.concatenate([np.broadcast_to(SKYT.astype(np.uint8), (PADT, W, 3)), TALL,
                        np.broadcast_to(TALL[-1:].mean(1, keepdims=True).astype(np.uint8), (PADB, W, 3))], 0)
BACK = np.zeros((H, W, 3), np.float32) + np.array([42, 29, 21], np.float32)
vy, vx = np.mgrid[0:H, 0:W]; BACK *= (1 - 0.45 * (((vx - W / 2) / W) ** 2 + ((vy - H / 2) / H) ** 2))[..., None]
BACK = BACK.astype(np.uint8)

# ---------------- fossil sprites (bone-coloured, embossed) ----------------
def fossil_sprite(draw_fn, w, h):
    S = 2; m = Image.new("L", (w * S, h * S), 0); draw_fn(ImageDraw.Draw(m), S)
    m = m.resize((w, h), Image.LANCZOS); pad = 24
    M = Image.new("L", (w + 2 * pad, h + 2 * pad), 0); M.paste(m, (pad, pad))
    a = np.asarray(M).astype(np.float32) / 255
    sh = np.asarray(M.filter(ImageFilter.GaussianBlur(5))).astype(np.float32) / 255
    sh = np.roll(np.roll(sh, 6, 0), 6, 1)
    hi = np.roll(np.roll(a, -3, 0), -3, 1); lo = np.roll(np.roll(a, 3, 0), 3, 1)
    body = np.zeros(a.shape + (3,), np.float32) + np.array(BONE, np.float32)
    body += ((a - lo).clip(0, 1) * 40)[..., None] - ((a - hi).clip(0, 1) * 110)[..., None]
    grain = rng.normal(0, 7, a.shape)[..., None]; body += grain
    outline = (np.asarray(M.filter(ImageFilter.MaxFilter(5))).astype(np.float32) / 255 - a).clip(0, 1)
    rgb = body * a[..., None] + np.array(UMBER, np.float32) * (1 - a[..., None])
    alpha = np.maximum(a, np.maximum(outline, sh * 0.55))
    rgb = np.where((a < 0.5)[..., None] & (outline < 0.3)[..., None], np.array([30, 18, 10], np.float32), rgb)
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8))

def draw_shark(d, S):
    pts_t, pts_b, L, x0, cy = [], [], 370, 30, 120
    for u in np.linspace(0, 1, 40):
        h = 58 * math.sin(math.pi * min(1, u ** 0.62)) + 9 * u
        pts_t.append((x0 + L * u, cy - h)); pts_b.append((x0 + L * u, cy + h * 0.72))
    body = pts_t + [(x0 + L + 125, cy - 105), (x0 + L + 55, cy - 4), (x0 + L + 92, cy + 58)] + pts_b[::-1]
    d.polygon([(x * S, y * S) for x, y in body], fill=255)
    for tri in ([(165, cy - 52), (215, cy - 140), (250, cy - 50)], [(335, cy - 22), (352, cy - 52), (365, cy - 18)],
                [(125, cy + 30), (205, cy + 105), (185, cy + 34)], [(305, cy + 20), (325, cy + 48), (340, cy + 18)]):
        d.polygon([(x * S, y * S) for x, y in tri], fill=255)
    for k in range(5):
        gx = 108 + k * 11; d.line([(gx * S, (cy - 18) * S), ((gx - 4) * S, (cy + 18) * S)], fill=0, width=3 * S)
    d.ellipse([60 * S, (cy - 22) * S, 72 * S, (cy - 10) * S], fill=0)

def draw_tree(d, S):
    cx, base, top = 160, 430, 30
    d.polygon([((cx - 26) * S, base * S), ((cx - 9) * S, top * S), ((cx + 9) * S, top * S), ((cx + 26) * S, base * S)], fill=255)
    for k in range(-3, 4):
        d.line([((cx + k * 10) * S, base * S), ((cx + k * 22) * S, (base + 18) * S)], fill=255, width=6 * S)
    for i in range(11):
        y = 80 + i * 30; ln = 40 + i * 10.5
        for sgn in (-1, 1):
            ex, ey = cx + sgn * ln, y - 26 + i * 0.5
            d.line([(cx * S, (y + 10) * S), (ex * S, ey * S)], fill=255, width=6 * S)
            for j in range(1, 6):
                u = j / 6; bx, by = cx + sgn * ln * u, y + 10 + (ey - y - 10) * u
                d.line([(bx * S, by * S), ((bx + sgn * 10) * S, (by + 16) * S)], fill=255, width=4 * S)
                d.line([(bx * S, by * S), ((bx + sgn * 12) * S, (by - 14) * S)], fill=255, width=4 * S)

def draw_dino(d, S):
    P = lambda pts: [(x * S, y * S) for x, y in pts]
    d.ellipse(P([(150, 80), (300, 165)]), fill=255)                                          # body
    d.polygon(P([(280, 95), (500, 112), (505, 120), (290, 150)]), fill=255)                  # tail
    d.polygon(P([(175, 105), (120, 40), (100, 46), (150, 125)]), fill=255)                   # neck
    d.polygon(P([(88, 30), (140, 26), (150, 48), (120, 58), (80, 50), (70, 40)]), fill=255)  # head
    d.ellipse(P([(118, 33), (127, 42)]), fill=0)
    for lx in (225, 262):                                                                    # legs
        d.polygon(P([(lx - 18, 140), (lx + 18, 140), (lx + 6, 195), (lx + 24, 230), (lx - 4, 230), (lx - 10, 190)]), fill=255)
        d.polygon(P([(lx - 6, 226), (lx + 34, 226), (lx + 34, 236), (lx - 6, 236)]), fill=255)
    d.line(P([(170, 135), (148, 160), (158, 172)]), fill=255, width=7 * S)                  # arm

FOSSILS = {"dino": (fossil_sprite(draw_dino, 520, 250), 230, 420),
           "tree": (fossil_sprite(draw_tree, 320, 460), 385, 430),
           "shark": (fossil_sprite(draw_shark, 560, 240), 450, 440)}
# when each fossil gets "found"
found_at = {}

# ---------------- narration & music ----------------
voice, words, total = narrate(spec, default_gap=0.3)
scenes = [ln for ln in spec["lines"] if "scene" in ln]
for ln in scenes:
    if ln["scene"].get("fossil"): found_at[ln["scene"]["fossil"]] = ln["_s"] + 1.2
n = len(voice); tt = np.arange(n) / SR; music = np.zeros(n, np.float32)
music += 0.05 * np.sin(2 * np.pi * 55 * tt) * (0.7 + 0.3 * np.sin(2 * np.pi * tt / 6))      # earthy drone
music += 0.025 * np.sin(2 * np.pi * 82.4 * tt + 0.4 * np.sin(2 * np.pi * tt / 7))
beat = 60 / 92; scale = [220, 261.63, 293.66, 329.63, 392, 440]
patt = [0, 2, 4, 2, 3, 1, 5, 2]
for k in range(int(total / beat) + 1):
    at = k * beat
    sw = np.arange(int(0.35 * SR)) / SR                                                      # soft frame-drum thud
    if k % 2 == 0: place(music, at, np.sin(2 * np.pi * (48 + 70 * np.exp(-sw * 18)) * sw) * np.exp(-sw * 9), 0.28)
    place(music, at + beat / 2, tone(scale[patt[k % 8]], 0.7, decay=7, harm=(1, 3.93, 9.2)), 0.05)   # marimba
rs = np.random.default_rng(9)
for i, ln in enumerate(scenes):
    if i == 0: continue
    st = ln["_s"]; place(music, st + 1.0, tone(2350, 0.4, decay=22, harm=(1, 2.7)), 0.07)   # pick "tink" on arrival
    nl = int(1.4 * SR); noise = np.convolve(rs.normal(0, 1, nl), np.ones(300) / 300, "same")
    env = np.sin(np.linspace(0, math.pi, nl)); place(music, st, noise * env * 6, 0.12)       # rumble while digging
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.35)

# ---------------- camera ----------------
ZS_ = 0.262
def target(sc):
    t = sc["type"]
    if t == "hook": return (wy(-12), 1.0)
    if t == "compare": return (wy(232), ZS_)
    if t == "end": return (wy(470), 1.0)
    return (wy(sc.get("depth", 0)), 1.0)
TG = [target(ln["scene"]) for ln in scenes]
def camera(t):
    i = 0
    for k, ln in enumerate(scenes):
        if t >= ln["_s"] - 0.1: i = k
    a, b = TG[max(0, i - 1)], TG[i]
    u = ease((t - scenes[i]["_s"] + 0.1) / 1.4) if i > 0 else 1.0
    cy = a[0] + (b[0] - a[0]) * u; s = math.exp(math.log(a[1]) + (math.log(b[1]) - math.log(a[1])) * u)
    sp = abs(b[0] - a[0]) * (u * (1 - u)) * 4 / 1000 if a != b else 0
    return cy, s, sp
def view(s):
    z = (1 - s) / (1 - ZS_); return 860 + 90 * z, 540 - 70 * z     # anchor y, column centre x

def to_screen(wy_, x, cy, s):
    ay, cx = view(s); return cx + (x - W / 2) * s, ay + (wy_ - cy) * s

# ---------------- drawing helpers ----------------
def ctext(d, txt, f, cx, cy, fill):
    d.text((cx - tw(txt, f) / 2, cy), txt, font=f, fill=fill, anchor="lm")

def fitf(txt, size, maxw, bold=True):
    while tw(txt, ZS(size, bold)) > maxw and size > 30: size -= 4
    return ZS(size, bold)

def card(arr, d, kicker, lines, lt, cx=470, y=160, maxw=800):
    u = back(lt / 0.55, 1.2)
    if lt < 0: return
    fk = ZS(42); fl = [fitf(l, 104, maxw - 70) for l in lines]
    wd = max([tw(kicker, fk) if kicker else 0] + [tw(l, f) for l, f in zip(lines, fl)]) + 80
    ht = (60 if kicker else 0) + sum(f.size * 1.08 for f in fl) + 50
    y = y - (1 - u) * 420; x0, x1 = int(cx - wd / 2), int(cx + wd / 2); y0, y1 = int(y), int(y + ht)
    return (x0, y0, x1, y1, kicker, lines, fk, fl)
def card_draw(d, c):
    if not c: return
    x0, y0, x1, y1, kicker, lines, fk, fl = c
    d.rectangle([x0, y0, x1, y1], fill=CREAM, outline=UMBER, width=5)
    d.rectangle([x0 + 10, y0 + 10, x1 - 10, y1 - 10], outline=(196, 170, 130), width=2)
    for hx in (x0 + 26, x1 - 26): d.ellipse([hx - 7, y0 + 19, hx + 7, y0 + 33], fill=(150, 120, 90))   # pins
    cx = (x0 + x1) / 2; y = y0 + 30
    if kicker: ctext(d, kicker, fk, cx, y + 22, RUST); y += 60
    for l, f in zip(lines, fl): ctext(d, l, f, cx, y + f.size * 0.52, UMBER); y += f.size * 1.08

def dashed_ring(d, cx, cy, rx, ry, prog, col=RUST, w=6):
    n = 36
    for k in range(int(n * prog)):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 0.55) / n
        d.line([(cx + rx * math.cos(a), cy + ry * math.sin(a)) for a in np.linspace(a0, a1, 5)], fill=col, width=w)

# ---------------- scenes (overlays on top of the camera view) ----------------
def sc_hook(sc, lt, dur, t, arr, d, cam):
    for i, txt in enumerate(sc["lines"]):
        u = back((lt - 0.05 - i * 0.28) / 0.5, 1.4)
        if u <= 0: continue
        f = fitf(txt, 132, W - 120); y = 360 + i * 160 - (1 - min(1, u)) * 60
        ctext(d, txt, f, W / 2 + 5, y + 6, (205, 178, 136))
        ctext(d, txt, f, W / 2, y, RUST if i == len(sc["lines"]) - 1 else UMBER)
    # little shovel stuck in the ground
    cy, s, _ = cam; sx, sy = to_screen(wy(0), 820, cy, s)
    d.line([(sx, sy - 210), (sx + 10, sy + 10)], fill=(120, 76, 40), width=12)
    d.rectangle([sx - 26, sy - 226, sx + 24, sy - 210], fill=(120, 76, 40))
    d.polygon([(sx - 22, sy), (sx + 40, sy + 4), (sx + 32, sy + 70), (sx + 6, sy + 92), (sx - 22, sy + 64)], fill=(140, 140, 140), outline=UMBER)
    return []

def sc_dig(sc, lt, dur, t, arr, d, cam):
    return [card(arr, d, sc.get("kicker"), sc["lines"], lt - 0.2)]

def sc_find(sc, lt, dur, t, arr, d, cam):
    cy, s, _ = cam; spr, fd, fx = FOSSILS[sc["fossil"]]
    x, y = to_screen(wy(fd), fx, cy, s)
    pr = eout((lt - 1.1) / 0.8)
    if pr > 0: dashed_ring(d, x, y, spr.width * 0.58, spr.height * 0.6, pr)
    return [card(arr, d, sc.get("kicker"), sc["lines"], lt - 1.0)]

def sc_compare(sc, lt, dur, t, arr, d, cam):
    cy, s, _ = cam; z = ease((lt - 0.9) / 0.5)
    if z > 0:
        _, ya = to_screen(wy(sc["from"]), 0, cy, s); xl, yb = to_screen(wy(sc["to"]), 0, cy, s)
        xb = xl - 26; yb2 = ya + (yb - ya) * eout((lt - 0.9) / 0.7)
        d.line([(xb, ya), (xb, yb2)], fill=OCHRE, width=8)
        d.line([(xb, ya), (xb + 22, ya)], fill=OCHRE, width=8)
        if yb2 > yb - 2: d.line([(xb, yb), (xb + 22, yb)], fill=OCHRE, width=8)
        mid = (ya + yb) / 2; f = fitf(sc["big"], 120, xb - 50)
        d.text((xb - 24, mid - 10), sc["big"], font=f, fill=tuple(int(c * z + 42 * (1 - z)) for c in OCHRE), anchor="rm")
        d.text((xb - 24, mid + 58), "MILLION YRS", font=ZS(30), fill=tuple(int(c * z + 42 * (1 - z)) for c in CREAM), anchor="rm")
    zt = ease((lt - 0.5) / 0.5)
    if zt > 0:                                                                                  # fossil tags right of column
        for name, (spr, fd, fx) in FOSSILS.items():
            xr, yy_ = to_screen(wy(fd), W, cy, s)
            lab = {"dino": "DINOSAURS", "tree": "TREES", "shark": "SHARKS"}[name]
            hot = name in ("shark",) or (name == "tree" and sc["from"] == 385) or (name == "dino" and sc["from"] == 230)
            col = tuple(int(c * zt + 42 * (1 - zt)) for c in (CREAM if hot else (170, 140, 110)))
            d.line([(xr + 6, yy_), (xr + 40, yy_)], fill=col, width=4)
            d.text((xr + 50, yy_), lab, font=ZS(40), fill=col, anchor="lm")
    return [card(arr, d, sc.get("kicker"), sc["lines"], lt - 0.6, cx=470, y=130, maxw=840)]

def sc_end(sc, lt, dur, t, arr, d, cam):
    click = sc.get("click_at", 0.9); on = ease((lt - click) / 0.35)
    cx, cy, w_, h_ = W / 2, 1040, 560, 150
    d.rounded_rectangle([cx - w_ / 2 - 10, cy - h_ / 2 - 10, cx + w_ / 2 + 10, cy + h_ / 2 + 10], h_ // 2 + 10, fill=(150, 112, 80))
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=(44, 28, 18))
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on
    if on > 0: d.rounded_rectangle([cx - w_ / 2 + 8, cy - h_ / 2 + 8, kx + h_ / 2 - 8, cy + h_ / 2 - 8], h_ // 2 - 8, fill=OCHRE)
    r = h_ / 2 - 14
    d.ellipse([kx - r + 6, cy - r + 8, kx + r + 6, cy + r + 8], fill=(30, 18, 10))
    d.ellipse([kx - r, cy - r, kx + r, cy + r], fill=(214, 190, 150), outline=UMBER, width=5)
    d.ellipse([kx - r * 0.6, cy - r * 0.7, kx + r * 0.1, cy - r * 0.2], fill=(236, 218, 186))
    f = ZS(64)
    d.text((cx - w_ / 2 - 20, cy + h_ / 2 + 50), "FAKE", font=ZS(44), fill=(170, 140, 110) if on > 0.5 else CREAM, anchor="lm")
    d.text((cx + w_ / 2 + 20, cy + h_ / 2 + 50), "TRUE", font=ZS(44), fill=OCHRE if on > 0.5 else (170, 140, 110), anchor="rm")
    c = card(arr, d, None, ["SOUNDS FAKE?"] + (["IT'S TRUE."] if lt > click + 0.2 else []), lt - 0.05, cx=W / 2, y=260, maxw=900)
    u = ease((lt - click - 0.8) / 0.5)
    if u > 0: ctext(d, "FOLLOW FOR MORE", ZS(64), W / 2, 1330, tuple(int(c_ * u + 40 * (1 - u)) for c_ in CREAM))
    return [c]

SCENES = dict(hook=sc_hook, dig=sc_dig, find=sc_find, compare=sc_compare, end=sc_end)

# ---------------- captions ----------------
groups = caption_groups(words, 3)
def caption(arr, d, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; f = fitf(" ".join(ws), 74, W - 160)
    x = (W - tw(" ".join(ws), f)) / 2
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x + 4, 1642), w, font=f, fill=(20, 12, 8), anchor="lm")
        d.text((x, 1638), w, font=f, fill=OCHRE if on else CREAM, anchor="lm")
        x += tw(w + " ", f)

# ---------------- frame ----------------
_sc = {}
def scaled(name, s):
    k = (name, round(s, 3))
    if k not in _sc:
        if len(_sc) > 60: _sc.clear()
        spr = FOSSILS[name][0]; _sc[k] = spr if s > 0.999 else spr.resize((max(1, int(spr.width * s)), max(1, int(spr.height * s))), Image.BILINEAR)
    return _sc[k]

def frame(t, fi):
    cy, s, sp = camera(t)
    shake = sp * 6 * math.sin(t * 70); cy += shake
    ay, ccx = view(s)
    top = cy - ay / s
    if s > 0.999:
        r0 = int(top) + PADT; arr = TALLP[r0:r0 + H].copy()
    else:
        r0 = int(top) + PADT; r1 = int(top + H / s) + PADT
        col = Image.fromarray(TALLP[max(0, r0):r1]).resize((int(W * s), H), Image.BILINEAR)
        z = (1 - s) / (1 - ZS_)                                          # trim to a core sample as we pull back
        yt = int(ay + (wy(-30 + 18 * z) - cy) * s); yb = int(ay + (wy(min(MAXD, 600 - 118 * z)) - cy) * s)
        yt, yb = max(0, yt), min(H, yb)
        base = Image.fromarray(BACK.copy()); x0 = int(ccx - W * s / 2)
        if yb > yt: base.paste(col.crop((0, yt, col.width, yb)), (x0, yt))
        dd = ImageDraw.Draw(base); dd.rectangle([x0 - 3, yt - 3, x0 + int(W * s) + 2, yb + 2], outline=CREAM, width=3)
        arr = np.asarray(base).copy()
    im = Image.fromarray(arr)
    for name, (spr, fd, fx) in FOSSILS.items():                       # fossils: faint imprint until found
        fa = found_at.get(name, 1e9); a = 0.28 + 0.72 * ease((t - fa) / 0.8)
        sx, sy = to_screen(wy(fd), fx, cy, s)
        if sy < -400 or sy > H + 400: continue
        sp_ = scaled(name, s); al = sp_.getchannel("A").point(lambda v: int(v * a))
        im.paste(sp_.convert("RGB"), (int(sx - sp_.width / 2), int(sy - sp_.height / 2)), al)
    arr = np.asarray(im).copy()
    ln = active_line(spec, t); sc = ln["scene"] if ln else {"type": "hook", "lines": []}
    gal = max(0.0, min(1.0, ((cy - SURF) / K - 15) / 40)) * (0 if sc["type"] == "end" else 1)
    if sc["type"] == "end":
        lt = t - ln["_s"]
        arr[:] = (arr * (1 - 0.55 * ease(lt / 0.5))).astype(np.uint8)
    if sp > 0 and s > 0.95:                                             # dust while digging
        for k in range(int(40 * sp)):
            x = (k * 397 + fi * 13) % W; y = (k * 211 + fi * 61) % 1500
            arr[y:y + 4, x:x + 4] = (190, 160, 120)
    arr[1555:1722] = (arr[1555:1722] * 0.32).astype(np.uint8)
    if gal > 0:
        arr[0:1540, 942:] = (arr[0:1540, 942:] * (1 - 0.6 * gal) + np.array([30, 20, 14]) * 0.6 * gal).astype(np.uint8)
    im = Image.fromarray(arr); d = ImageDraw.Draw(im)
    if gal > 0: gauge_ticks(d, cy, s, gal)
    cards = []
    if ln is not None:
        lt = t - ln["_s"]; dur = ln["_se"] - ln["_s"]
        cards = SCENES[sc["type"]](sc, lt, dur, t, arr, d, (cy, s, sp))
    for c in cards:
        if not c: continue
        o = np.asarray(im).copy(); x0, y0, x1, y1 = c[:4]
        sy0, sy1, sx0, sx1 = max(0, y0 + 12), max(0, y1 + 12), max(0, x0 + 12), min(W, x1 + 12)
        if sy1 > sy0: o[sy0:sy1, sx0:sx1] = (o[sy0:sy1, sx0:sx1] * 0.55).astype(np.uint8)
        im = Image.fromarray(o); d = ImageDraw.Draw(im); card_draw(d, c)
    if gal > 0.05 and s > 0.85 and sc["type"] != "end":               # current depth pointer
        dep = max(0, (cy - SURF) / K); ya = view(s)[0]
        d.polygon([(942, ya), (918, ya - 18), (918, ya + 18)], fill=OCHRE)
        d.rounded_rectangle([948, ya - 28, 1074, ya + 28], 8, fill=OCHRE)
        d.text((1011, ya), f"{int(round(dep))}", font=ZS(44), fill=UMBER, anchor="mm")
    caption(None, d, t)
    d.rectangle([0, H - 10, int(W * t / total), H], fill=OCHRE)
    return im.tobytes()

def gauge_ticks(d, cy, s, alpha):
    x0 = 942; step, lab = (5, 25) if s > 0.6 else (10, 50)
    ay, _ = view(s); dtop = (cy - ay / s - SURF) / K; dbot = (cy + (1540 - ay) / s - SURF) / K
    col = tuple(int(c * alpha + 40 * (1 - alpha)) for c in CREAM)
    for m in range(int(max(0, dtop) // step) * step, int(dbot) + step, step):
        if m <= 0 or m > MAXD: continue
        y = ay + (wy(m) - cy) * s
        if not 100 < y < 1530: continue
        big = m % lab == 0
        d.line([(x0, y), (x0 + (34 if big else 16), y)], fill=col, width=4 if big else 2)
        if big and not (s > 0.85 and abs(y - ay) < 40): d.text((x0 + 44, y), str(m), font=ZS(36), fill=col, anchor="lm")
    d.text((x0 + 69, 44), "MILLION", font=ZS(24), fill=col, anchor="mm")
    d.text((x0 + 69, 72), "YRS AGO", font=ZS(24), fill=col, anchor="mm")

if __name__ == "__main__":
    print(f"total {total:.1f}s", flush=True)
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","):
            Image.frombytes("RGB", (W, H), frame(float(tt_), int(float(tt_) * FPS))).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=24)
        print(f"done {total:.1f}s")
