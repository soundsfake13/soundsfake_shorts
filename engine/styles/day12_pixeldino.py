"""Day 12 — 16-BIT PIXEL-DINO style (days were shorter when dinosaurs lived).
Everything is drawn on a 180x320 canvas with hard pixels and upscaled x6 (nearest): fast day/night sky,
sauropod sprite, pixel Earth, fossil clam rings, Moon with tidal bulge, HUD counters, scanlines; chiptune.
Usage: python3 engine/styles/day12_pixeldino.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
LW, LH, SC = 180, 320, 6
RIGHT = ImageFont.truetype(f"{FONTS}/Righteous.ttf", 10)
_tc = {}
def ptext(d, s, x, y, size=1, col=(255, 255, 255), anchor="mm", shadow=(20, 12, 40)):
    """Hard-pixel text: render small then threshold; size = integer pixel scale."""
    key = (s, size)
    if key not in _tc:
        f = ImageFont.truetype(f"{FONTS}/Righteous.ttf", 9 * size)
        w = int(f.getlength(s)) + 4; m = Image.new("L", (w, 12 * size + 4), 0); ImageDraw.Draw(m).text((2, 1), s, font=f, fill=255)
        _tc[key] = m.point(lambda v: 255 if v > 110 else 0)
    m = _tc[key]; ox = {"mm": -m.width // 2, "lm": 0, "rm": -m.width}[anchor]; oy = -m.height // 2
    im = d._image
    if shadow: im.paste(shadow, (int(x + ox + 1), int(y + oy + 1)), m)
    im.paste(col, (int(x + ox), int(y + oy)), m)

SKYD, SKYN, GROUND, GRASS, DINO, DINO2, SUN, MOONC, WHITE, RED, YEL, NAVY = (110, 180, 255), (20, 16, 60), (120, 80, 40), (60, 170, 70), (90, 160, 90), (50, 110, 60), (255, 220, 60), (230, 230, 210), (255, 255, 255), (230, 60, 60), (255, 220, 60), (20, 12, 40)
def lerpc(a, b, u): return tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3))

def dino(d, x, y, t, s=1):
    """Sauropod sprite, x,y = feet baseline left."""
    R = lambda a, b, w, h, c=DINO: d.rectangle([x + a * s, y - (b + h) * s, x + (a + w) * s - 1, y - b * s - 1], fill=c)
    step = int(t * 6) % 2
    R(10, 10, 34, 14); R(14, 22, 26, 6)                                    # body
    R(12, 0, 5, 10 + step, DINO2); R(36, 0, 5, 10 + (1 - step), DINO2); R(18, 0, 5, 10, DINO); R(30, 0, 5, 10, DINO)
    R(40, 18, 6, 8); R(44, 24, 5, 10); R(46, 32, 5, 8); R(48, 38, 10, 6); R(56, 40, 3, 2, NAVY)  # neck/head/eye
    R(0, 14, 10, 4); R(-8, 12, 8, 3)                                       # tail
    for k in range(4): R(16 + k * 7, 26, 3, 2, DINO2)                    # back spots

def world(t, speed=1.0, dayfrac=None):
    img = Image.new("RGB", (LW, LH)); d = ImageDraw.Draw(img)
    ph = (t * 0.6 * speed) % 1.0 if dayfrac is None else dayfrac
    light = 0.5 + 0.5 * math.sin(2 * math.pi * ph)
    for y in range(0, 230, 6): d.rectangle([0, y, LW, y + 5], fill=lerpc(SKYN, lerpc(SKYD, (180, 220, 255), y / 230), light))
    a = 2 * math.pi * ph - math.pi / 2
    sx, sy = LW / 2 + 80 * math.cos(a + math.pi), 230 - 170 * math.sin(a + math.pi)
    mx, my = LW / 2 + 80 * math.cos(a), 230 - 170 * math.sin(a)
    if sy < 230: d.rectangle([sx - 7, sy - 7, sx + 7, sy + 7], fill=SUN); d.rectangle([sx - 9, sy - 4, sx + 9, sy + 4], fill=SUN)
    if my < 230: d.rectangle([mx - 5, my - 5, mx + 5, my + 5], fill=MOONC)
    if light < 0.4:
        r = random.Random(1)
        for k in range(30): d.point((r.randrange(LW), r.randrange(150)), fill=WHITE)
    for k in range(5):                                                     # volcano + hills
        hx = (k * 50 - t * 4) % (LW + 60) - 30; d.polygon([(hx - 30, 232), (hx, 200 - (k % 2) * 14), (hx + 30, 232)], fill=lerpc((30, 30, 60), (70, 120, 90), light))
    d.rectangle([0, 232, LW, 240], fill=GRASS); d.rectangle([0, 240, LW, LH], fill=GROUND)
    for k in range(12): d.rectangle([(k * 16 - t * 20) % LW, 248 + (k % 3) * 18, (k * 16 - t * 20) % LW + 5, 250 + (k % 3) * 18], fill=(100, 64, 32))
    return img, d, light

def up(img):
    a = np.asarray(img.resize((W, H), Image.NEAREST)).copy()
    a[::6] = (a[::6] * 0.82).astype(np.uint8)                            # scanlines
    return Image.fromarray(a)

def box(d, x0, y0, x1, y1, fill=NAVY, edge=WHITE):
    d.rectangle([x0, y0, x1, y1], fill=edge); d.rectangle([x0 + 1, y0 + 1, x1 - 1, y1 - 1], fill=fill)

def clock(d, cx, cy, txt, col=YEL):
    box(d, cx - 40, cy - 12, cx + 40, cy + 12); ptext(d, txt, cx, cy, 2, col)

def S_hook(sc, lt, dur, t):
    img, d, _ = world(t, 1.8); dino(d, 50, 232, t, 1)
    box(d, 8, 22, LW - 8, 66); ptext(d, "A DAY WASN'T", LW / 2, 34, 1, WHITE); ptext(d, "24 HOURS", LW / 2, 52, 2, YEL)
    if sc.get("loop"):
        g = int(lt * 12) % 2 if lt < 0.8 else 1
        clock(d, LW / 2, 100, "23.5 H" if g else "24.0 H", RED if g else YEL)
        if lt > 0.9: ptext(d, "...IT WAS SHORTER", LW / 2, 125, 1, WHITE)
    else:
        clock(d, LW / 2, 100, "24.0 H");
        if int(t * 4) % 2: d.line([(LW / 2 - 40, 112), (LW / 2 + 40, 88)], fill=RED, width=3)
    return up(img)
def S_spin(sc, lt, dur, t):
    img = Image.new("RGB", (LW, LH), NAVY); d = ImageDraw.Draw(img)
    r = random.Random(3)
    for k in range(60): d.point((r.randrange(LW), r.randrange(LH)), fill=WHITE if k % 3 else YEL)
    ptext(d, "70,000,000 YEARS AGO", LW / 2, 26, 1, YEL)
    cx, cy, R = LW / 2, 130, 52; off = t * 70
    for y in range(-R, R + 1, 2):
        w_ = int(math.sqrt(max(0, R * R - y * y)))
        for x in range(-w_, w_ + 1, 2):
            u = ((x + off) % 80) / 80; land = (math.sin(u * 2 * math.pi * 2 + y * 0.08) > 0.3)
            d.rectangle([cx + x, cy + y, cx + x + 1, cy + y + 1], fill=(70, 170, 80) if land else (40, 100, 220))
    for k in range(3): a = t * 8 + k * 2.1; d.arc([cx - R - 10, cy - R - 10, cx + R + 10, cy + R + 10], math.degrees(a), math.degrees(a) + 30, fill=WHITE, width=2)
    ptext(d, "SPIN SPEED", LW / 2, 200, 1, WHITE); box(d, 30, 210, 150, 222, NAVY); d.rectangle([32, 212, 32 + int(116 * min(1, 0.2 + lt / 2)), 220], fill=RED)
    hrs = 24 - 0.5 * ease((lt - 1.2) / 1.5); clock(d, LW / 2, 262, f"{int(hrs)}H {int(round((hrs % 1) * 60)):02d}M", YEL if hrs > 23.6 else RED)
    return up(img)
def S_clam(sc, lt, dur, t):
    img, d, _ = world(t, 1.0, dayfrac=0.25); dino(d, 118, 232, t * 0.5, 1)
    box(d, 8, 18, LW - 8, 54); ptext(d, "FOSSIL CLAM", LW / 2, 30, 2, YEL); ptext(d, "1 LAYER = 1 DAY", LW / 2, 46, 1, WHITE)
    cx, cy = 60, 160                                                       # rudist: cone shell with growth bands
    n = int(min(40, lt * 14))
    for k in range(40):
        y = cy + 60 - k * 3; w_ = 8 + k * 0.9
        col = (220, 200, 160) if k % 2 else (190, 160, 120)
        if k >= n: col = (80, 60, 40)
        d.rectangle([cx - w_, y, cx + w_, y + 2], fill=col)
    d.ellipse([cx - 44, cy - 66, cx + 44, cy - 54], fill=(150, 120, 90))
    ptext(d, f"DAY {n * 9 + 1}", cx, cy + 78, 1, YEL)
    return up(img)
def S_moon(sc, lt, dur, t):
    img = Image.new("RGB", (LW, LH), NAVY); d = ImageDraw.Draw(img)
    r = random.Random(4)
    for k in range(50): d.point((r.randrange(LW), r.randrange(LH)), fill=WHITE)
    ptext(d, "THE CULPRIT:", LW / 2, 26, 1, WHITE); ptext(d, "THE MOON", LW / 2, 44, 2, YEL)
    ex, ey = 70, 160; bul = 6 + 2 * math.sin(t * 4)
    d.ellipse([ex - 40 - bul, ey - 34, ex + 40 + bul, ey + 34], fill=(60, 120, 230))          # tidal bulge
    d.ellipse([ex - 32, ey - 32, ex + 32, ey + 32], fill=(40, 100, 200)); d.rectangle([ex - 12, ey - 20, ex + 8, ey], fill=(70, 170, 80)); d.rectangle([ex + 4, ey + 6, ex + 20, ey + 18], fill=(70, 170, 80))
    mx = 150; d.rectangle([mx - 9, ey - 9, mx + 9, ey + 9], fill=MOONC); d.rectangle([mx - 4, ey - 4, mx - 1, ey - 1], fill=(180, 180, 160))
    if lt > 1.0:
        ptext(d, "BRAKE!", ex, ey + 56, 2, RED)
        for k in range(3): x = ex + 46 + k * 6 + int(t * 20) % 6; d.rectangle([x, ey - 2, x + 2, ey + 2], fill=RED)
    if lt > 2.2: box(d, 12, 250, LW - 12, 280); ptext(d, "SLOWER EVERY CENTURY", LW / 2, 265, 1, YEL)
    return up(img)
def S_year(sc, lt, dur, t):
    img, d, _ = world(t, 3.0); dino(d, 20, 232, t, 1)
    box(d, 8, 22, LW - 8, 60); ptext(d, "DAYS IN A YEAR", LW / 2, 34, 1, WHITE)
    v = 365 + int(7 * ease((lt - 1.0) / 1.6)); ptext(d, str(v), LW / 2, 50, 2, RED if v > 365 else YEL)
    for k in range(min(7, max(0, v - 365))):                                # 7 bonus day tiles
        x = 14 + k * 23; d.rectangle([x, 80, x + 18, 98], fill=WHITE); d.rectangle([x, 80, x + 18, 84], fill=RED); d.rectangle([x + 8, 86, x + 10, 96], fill=RED); d.rectangle([x + 4, 90, x + 14, 92], fill=RED)
    return up(img)
def S_end(sc, lt, dur, t):
    img, d, _ = world(t, 1.0); dino(d, 60, 232, t, 1)
    box(d, 8, 22, LW - 8, 56); ptext(d, "SOUNDS FAKE ?!", LW / 2, 39, 2, YEL)
    click = sc.get("click_at", 0.45); on = lt > click; cx, cy = LW / 2, 100
    box(d, cx - 30, cy - 10, cx + 30, cy + 10, RED if on else (90, 90, 110)); kx = cx + (14 if on else -14); d.rectangle([kx - 12, cy - 7, kx + 12, cy + 7], fill=WHITE)
    ptext(d, "FAKE", cx - 36, cy, 1, WHITE if not on else (120, 120, 140), "rm"); ptext(d, "TRUE", cx + 36, cy, 1, YEL if on else (120, 120, 140), "lm")
    if on and lt < click + 0.6: ptext(d, "+1 UP", LW / 2, 130 - int((lt - click) * 30), 1, YEL)
    return up(img)
SCENES = dict(hook=S_hook, spin=S_spin, clam=S_clam, moon=S_moon, year=S_year, end=S_end)

voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
SQ = (1, 3, 5, 7, 9)
mel = [523.25, 659.25, 783.99, 659.25, 587.33, 698.46, 880.0, 698.46, 523.25, 659.25, 783.99, 1046.5, 987.77, 783.99, 659.25, 587.33]
bass = [130.81, 130.81, 174.61, 196.0]
for k in range(int(total / 0.2)):
    if k % 2 == 0: place(music, k * 0.2, tone(mel[(k // 2) % 16], 0.18, decay=10, harm=SQ), 0.022)
    if k % 4 == 0: place(music, k * 0.2, tone(bass[(k // 16) % 4], 0.35, decay=6, harm=(1, 3, 5)), 0.05)
    if k % 4 == 2: place(music, k * 0.2, (np.random.default_rng(k).normal(0, 1, int(0.04 * SR)) * np.exp(-np.linspace(0, 8, int(0.04 * SR)))).astype(np.float32), 0.03)
hook_hit(music, 0.3)
for s_ in scene_starts(spec): whoosh(music, s_, 0.08)
write_audio(voice, music, work + "_audio.wav", music_gain=0.5, duck=0.3)

groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0].upper() for i in g]; line = " ".join(ws)
    small = Image.new("RGB", (LW, 26), NAVY); d = ImageDraw.Draw(small); d.rectangle([0, 0, LW - 1, 25], outline=WHITE)
    sz = 2 if RIGHT.getlength(line) * 2 < LW - 10 else 1
    x = LW / 2 - (Image.new("L", (1, 1)) and 0); f = ImageFont.truetype(f"{FONTS}/Righteous.ttf", 9 * sz); tw = f.getlength(line); x = (LW - tw) / 2
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        ptext(d, w, x, 13, sz, YEL if on else WHITE, "lm"); x += f.getlength(w + " ")
    img.paste(small.resize((W, 26 * SC), Image.NEAREST), (0, 1660))

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t); caption(img, t)
    ImageDraw.Draw(img).rectangle([0, H - 12, int(W * t / total) // 12 * 12, H], fill=RED); return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
