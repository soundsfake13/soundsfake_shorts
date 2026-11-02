"""Day 31 — HONEYCOMB style (honey never spoils).
Warm golden macro: hexagon cells filling with slow amber honey, drips from the top, warm backlight bokeh,
elegant serif type on cream wax labels. Usage: python3 engine/styles/day31_honeycomb.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
rng = np.random.default_rng(31); random.seed(31)
SERIF = lambda s: ImageFont.truetype(f"{FONTS}/DMSerifDisplay-Regular.ttf", s)
AMBER, GOLD, DEEP, WAX, BROWN, WATER, GERM = (236, 160, 30), (255, 205, 80), (120, 62, 8), (252, 238, 205), (70, 36, 6), (90, 170, 230), (130, 190, 90)

# ---------------- backgrounds ----------------
yy = np.linspace(0, 1, H)[:, None, None]
WARM = (np.array([92, 48, 8], np.float32) * (1 - yy) + np.array([40, 18, 2], np.float32) * yy).repeat(W, 1)
BOKEH = Image.new("RGB", (W, H), (0, 0, 0)); bd = ImageDraw.Draw(BOKEH)
for _ in range(40):
    x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(30, 110)
    c = int(rng.uniform(40, 110)); bd.ellipse([x - r, y - r, x + r, y + r], fill=(c, int(c * 0.65), int(c * 0.15)))
WARM += np.asarray(BOKEH.filter(ImageFilter.GaussianBlur(24))).astype(np.float32)

HEX_R = 74
CELLS = []
for row in range(-1, int(H / (HEX_R * 1.5)) + 2):
    for col in range(-1, int(W / (HEX_R * math.sqrt(3))) + 2):
        cx = col * HEX_R * math.sqrt(3) + (row % 2) * HEX_R * math.sqrt(3) / 2; cy = row * HEX_R * 1.5
        CELLS.append((cx, cy))
def hexpts(cx, cy, r): return [(cx + r * math.cos(math.radians(60 * k + 30)), cy + r * math.sin(math.radians(60 * k + 30))) for k in range(6)]

def comb(fill_level, t, dim=1.0):
    """Honeycomb wall: cells fill with honey from the bottom up to fill_level (0..1 of screen height)."""
    img = Image.fromarray(np.clip(WARM * dim, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(img)
    line_y = H * (1 - fill_level)
    for (cx, cy) in CELLS:
        d.polygon(hexpts(cx, cy, HEX_R - 4), fill=tuple(int(c * dim) for c in (60, 30, 4)))
        f = np.clip((cy + HEX_R - line_y + 30 * math.sin(cx / 140 + t)) / (2 * HEX_R), 0, 1)
        if f > 0:
            r = (HEX_R - 10) * f
            d.polygon(hexpts(cx, cy + (HEX_R - 10) * (1 - f) * 0.5, r), fill=tuple(int(c * dim) for c in AMBER))
            d.ellipse([cx - r * 0.45, cy - r * 0.55, cx - r * 0.05, cy - r * 0.25], fill=tuple(int(c * dim) for c in GOLD))
        d.polygon(hexpts(cx, cy, HEX_R), outline=tuple(int(c * dim) for c in (210, 150, 60)), width=7)
    return img

def drips(img, t, n=7, length=1.0, top=0):
    d = ImageDraw.Draw(img)
    for k in range(n):
        x = 80 + k * (W - 160) / (n - 1); L = (180 + 140 * math.sin(k * 1.7)) * length * (0.85 + 0.15 * math.sin(t * 1.3 + k))
        d.rectangle([x - 24, top, x + 24, top + L], fill=AMBER)
        d.ellipse([x - 34, top + L - 34, x + 34, top + L + 34], fill=AMBER)
        d.ellipse([x - 16, top + L - 18, x - 2, top + L + 4], fill=GOLD)
    d.rectangle([0, top, W, top + 40], fill=AMBER)

def label(img, txt, size, cx, cy, u=1.0, fill=WAX, ink=BROWN, rot=0):
    if u <= 0: return
    f = SERIF(size); tw = ImageDraw.Draw(img).textlength(txt, font=f)
    while tw > W - 140 and size > 40: size -= 4; f = SERIF(size); tw = ImageDraw.Draw(img).textlength(txt, font=f)
    lay = Image.new("RGBA", (int(tw + 90), int(size * 1.5)), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle([0, 0, lay.width - 1, lay.height - 1], int(size * 0.35), fill=fill + (int(240 * u),))
    ld.text((45, size * 0.2), txt, font=f, fill=ink + (int(255 * u),))
    if rot: lay = lay.rotate(rot, expand=True, resample=Image.BICUBIC)
    img.paste(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)), lay)

def titles(img, lines, lt, y0=360, size=118, accent=None):
    d = ImageDraw.Draw(img)
    for i, txt in enumerate(lines):
        u = ease((lt - 0.1 - i * 0.35) / 0.5)
        if u <= 0: continue
        sz = size
        while d.textlength(txt, font=SERIF(sz)) > W - 120 and sz > 50: sz -= 4
        col = GOLD if accent and str(i) in accent else WAX
        y = y0 + i * size * 1.1 + (1 - u) * 40
        tw = d.textlength(txt, font=SERIF(sz)); band = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(band).rounded_rectangle([W / 2 - tw / 2 - 40, y - 10, W / 2 + tw / 2 + 40, y + sz * 1.12], 30, fill=(30, 14, 0, int(170 * u)))
        img.paste(Image.alpha_composite(img.convert("RGBA"), band).convert("RGB")); d = ImageDraw.Draw(img)
        d.text((W / 2 + 4, y + 6), txt, font=SERIF(sz), fill=(30, 14, 0), anchor="ma")
        d.text((W / 2, y), txt, font=SERIF(sz), fill=tuple(int(c * u + 40 * (1 - u)) for c in col), anchor="ma")

def jar(d, cx, cy, s=1.0, honey=AMBER, grain=0.0, t=0.0):
    d.ellipse([cx - 210 * s, cy - 150 * s, cx + 210 * s, cy + 260 * s], fill=(176, 104, 50))          # clay body
    d.rectangle([cx - 90 * s, cy - 250 * s, cx + 90 * s, cy - 120 * s], fill=(160, 92, 42))           # neck
    d.ellipse([cx - 120 * s, cy - 280 * s, cx + 120 * s, cy - 220 * s], fill=(190, 116, 58))          # rim
    d.ellipse([cx - 95 * s, cy - 268 * s, cx + 95 * s, cy - 232 * s], fill=honey)                      # honey surface
    for k in range(3): d.arc([cx - 200 * s, cy - 60 * s + k * 70 * s, cx + 200 * s, cy + 40 * s + k * 70 * s], 10, 170, fill=(140, 78, 34), width=6)
    r = random.Random(int(t * 8))
    for _ in range(int(60 * grain)):
        x, y = cx + r.uniform(-80, 80) * s, cy - 250 * s + r.uniform(-10, 10) * s
        d.rectangle([x - 4, y - 4, x + 4, y + 4], fill=(255, 240, 200))

def bee(d, x, y, s=1.0, t=0.0):
    w = 30 * s * (0.6 + 0.4 * abs(math.sin(t * 40)))
    d.ellipse([x - 20 * s, y - 50 * s - w, x + 25 * s, y - 20 * s], fill=(240, 245, 255))
    d.ellipse([x - 5 * s, y - 55 * s - w * 0.8, x + 40 * s, y - 25 * s], fill=(225, 235, 250))
    d.ellipse([x - 60 * s, y - 32 * s, x + 60 * s, y + 32 * s], fill=GOLD)
    for k in (-25, 5, 35): d.rectangle([x + k * s - 8 * s, y - 30 * s, x + k * s + 8 * s, y + 30 * s], fill=BROWN)
    d.ellipse([x + 45 * s, y - 22 * s, x + 80 * s, y + 18 * s], fill=BROWN)

# ---------------- narration & music ----------------
voice, words, total = narrate(spec, default_gap=0.3)
n = len(voice); tt = np.arange(n) / SR; music = np.zeros(n, np.float32)
hum = np.sign(np.sin(2 * np.pi * 196 * tt)) * 0.5 + np.sin(2 * np.pi * 196.8 * tt)
music += (hum * 0.012 * (0.4 + 0.6 * np.sin(2 * np.pi * tt / 5) ** 2)).astype(np.float32)   # lazy bee hum
prog = [[261.63, 329.63, 392.0], [220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 246.94, 293.66]]
for k in range(int(total / 0.42)):                                                            # warm plucked guitar-ish arpeggio
    ch = prog[(k // 8) % 4]; f = ch[k % 3] * (2 if k % 8 == 6 else 1)
    place(music, k * 0.42, tone(f, 1.2, decay=5, harm=(1, 2, 3, 4)), 0.05)
    if k % 8 == 0: place(music, k * 0.42, tone(ch[0] / 2, 2.0, decay=2.5, harm=(1, 2)), 0.06)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.35)

# ---------------- scenes ----------------
def sc_hook(sc, lt, dur, t):
    img = comb(0.15 + 0.45 * ease(lt / dur), t); titles(img, sc["lines"], lt, accent=sc.get("accent")); return img

def sc_words(sc, lt, dur, t):
    img = comb(0.0, t, dim=0.7); drips(img, t, length=ease(lt / 1.2))
    titles(img, sc["lines"], lt, y0=sc.get("y", 760), size=150, accent=sc.get("accent")); return img

def sc_tomb(sc, lt, dur, t):
    img = Image.new("RGB", (W, H), (88, 66, 40)); d = ImageDraw.Draw(img)
    r = random.Random(5)
    for row in range(0, H, 110):                                   # sandstone blocks
        off = (row // 110 % 2) * 120
        for col in range(-120, W, 240):
            c = r.randint(118, 150); d.rectangle([col + off + 6, row + 6, col + off + 234, row + 104], fill=(c, int(c * 0.8), int(c * 0.55)))
    d.rectangle([180, 560, W - 180, 1420], fill=(46, 30, 16))         # niche
    glow = Image.new("L", (W, H), 0); ImageDraw.Draw(glow).ellipse([W / 2 - 300, 760, W / 2 + 300, 1360], fill=int(150 * ease(lt / 1.0)))
    img = Image.composite(Image.new("RGB", (W, H), (255, 180, 60)), img, glow.filter(ImageFilter.GaussianBlur(80)))
    d = ImageDraw.Draw(img); jar(d, W / 2, 1120, 0.9, t=t)
    label(img, sc.get("label", "THOUSANDS OF YEARS OLD"), 64, W / 2, 400, u=ease((lt - 0.8) / 0.4))
    return img

def sc_water(sc, lt, dur, t):
    img = comb(0.0, t, dim=0.55); d = ImageDraw.Draw(img)
    cx, cy, R = W / 2, 820, 330
    d.ellipse([cx - R, cy - R + 60, cx + R, cy + R + 60], fill=AMBER); d.polygon([(cx - R * 0.72, cy - R * 0.45), (cx + R * 0.72, cy - R * 0.45), (cx, cy - R * 1.35)], fill=AMBER)
    v = int(17 * ease((lt - 0.2) / 0.9))
    d.text((cx, cy + 40), f"{v}%", font=SERIF(240), fill=WAX, anchor="mm"); d.text((cx, cy + 210), "WATER", font=SERIF(64), fill=BROWN, anchor="mm")
    if lt > 1.6:                                                   # a germ losing its water
        p = ease((lt - 1.6) / 1.4); gx, gy = 280, 1330; gr = 80 * (1 - 0.55 * p)
        d.ellipse([gx - gr, gy - gr, gx + gr, gy + gr], fill=GERM, outline=(60, 110, 40), width=6)
        for k in range(6):
            a = k * 1.05 + t; dist = 90 + 260 * p
            x, y = gx + dist * math.cos(a) * 0.5 + 300 * p, gy + dist * math.sin(a) * 0.4 - 160 * p
            d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=WATER)
        label(img, "SUGAR PULLS THE WATER OUT", 50, 700, 1480, u=p)
    return img

def sc_acid(sc, lt, dur, t):
    img = comb(0.0, t, dim=0.55); d = ImageDraw.Draw(img)
    x0, x1, y = 120, W - 120, 860
    for k in range(15):
        col = (int(230 - k * 10), int(60 + k * 12), int(40 + k * 12))
        d.rectangle([x0 + (x1 - x0) * k / 15, y, x0 + (x1 - x0) * (k + 1) / 15 - 4, y + 90], fill=col)
        if k % 7 == 0: d.text((x0 + (x1 - x0) * (k + 0.5) / 15, y + 140), str(k), font=SERIF(48), fill=WAX, anchor="mm")
    u = ease((lt - 0.3) / 0.8); a, b = 3.4, 4.5
    xa, xb = x0 + (x1 - x0) * a / 15, x0 + (x1 - x0) * b / 15
    d.rectangle([xa, y - 30, xa + (xb - xa) * u, y + 120], outline=WAX, width=8)
    if u > 0.9: d.text(((xa + xb) / 2, y - 90), "HONEY", font=SERIF(64), fill=GOLD, anchor="mm")
    titles(img, ["ACIDIC"], lt, y0=440, size=140)
    if lt > 1.2: label(img, "MOST GERMS CAN'T GROW", 56, W / 2, 1220, u=ease((lt - 1.2) / 0.4))
    return img

def sc_bee(sc, lt, dur, t):
    img = comb(0.3, t, dim=0.75); d = ImageDraw.Draw(img)
    x = -150 + (W + 300) * (lt / max(1.0, dur)); y = 820 + 120 * math.sin(lt * 3)
    for k in range(10):                                              # sparkle trail
        px = x - 60 - k * 55; py = 820 + 120 * math.sin((lt - k * 0.06) * 3) + 40
        r = 10 - k * 0.8
        if r > 0: d.ellipse([px - r, py - r, px + r, py + r], fill=(255, 245, 200))
    bee(d, x, y, 1.6, t)
    label(img, sc.get("label", "+ A GERM-FIGHTING ENZYME"), 58, W / 2, 400, u=ease((lt - 0.4) / 0.4))
    return img

def sc_crystal(sc, lt, dur, t):
    img = comb(0.0, t, dim=0.55); d = ImageDraw.Draw(img)
    grain = ease((lt - 0.3) / 1.0) * (1 - ease((lt - 2.4) / 1.0))
    honey = tuple(int(AMBER[i] * (1 - grain) + (245, 210, 140)[i] * grain) for i in range(3))
    jar(d, W / 2, 1060, 1.1, honey=honey, grain=grain, t=t)
    if lt > 2.0:                                                     # warm it up: heat waves
        for k in range(3):
            x = W / 2 - 180 + k * 180
            pts = [(x + 20 * math.sin(j * 0.6 + t * 6), 1460 - j * 18) for j in range(14)]
            d.line(pts, fill=(255, 120, 40), width=10)
    lab = "CRYSTALS? STILL FINE" if lt < 2.2 else "WARM IT UP"
    label(img, lab, 64, W / 2, 400, u=ease((lt - 0.5) / 0.4))
    label(img, "KEEP IT SEALED", 52, W / 2, 520, u=ease((lt - 0.2) / 0.4), fill=BROWN, ink=WAX)
    return img

def sc_end(sc, lt, dur, t):
    img = comb(0.0, t, dim=0.5); drips(img, t, length=0.6); d = ImageDraw.Draw(img)
    click = sc.get("click_at", 0.9); on = ease((lt - click) / 0.25)
    cx, cy, w_, h_ = W / 2, 1000, 340, 150
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=AMBER if on > 0.5 else (90, 60, 30), outline=WAX, width=8)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on
    d.polygon(hexpts(kx, cy, h_ / 2 - 18), fill=WAX)
    d.text((cx - w_ / 2 - 40, cy), "FAKE", font=SERIF(70), fill=WAX if on < 0.5 else (150, 110, 70), anchor="rm")
    d.text((cx + w_ / 2 + 40, cy), "TRUE", font=SERIF(70), fill=GOLD if on >= 0.5 else (150, 110, 70), anchor="lm")
    if lt > click + 0.3: titles(img, ["Sounds Fake ?!"], lt - click - 0.3, y0=600, size=130, accent={"0": 1})
    return img

SCENES = dict(hook=sc_hook, words=sc_words, tomb=sc_tomb, water=sc_water, acid=sc_acid, bee=sc_bee, crystal=sc_crystal, end=sc_end)

# ---------------- captions: wax labels ----------------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 70
    while d.textlength(" ".join(ws), font=SERIF(size)) > W - 200 and size > 40: size -= 4
    f = SERIF(size); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1610
    d.rounded_rectangle([x - 36, y - 18, x + tw + 36, y + size + 30], 28, fill=WAX)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=(200, 110, 0) if on else BROWN)
        x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t)
    if ln is None: img = comb(0.0, t, dim=0.5)
    else:
        lt = t - ln["_s"]; dur = ln["_se"] - ln["_s"]
        img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t)
        if lt < 0.2: img = Image.blend(Image.new("RGB", (W, H), (40, 18, 2)), img, ease((lt + 0.05) / 0.25))
    caption(img, t)
    ImageDraw.Draw(img).rectangle([0, H - 10, int(W * t / total), H], fill=GOLD)
    return img.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","):
            Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path)
        print(f"done {total:.1f}s")
