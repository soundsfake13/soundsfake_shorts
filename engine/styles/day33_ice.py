"""Day 33 — ICE-CRYSTAL style (wood frogs freeze solid and come back to life).
Deep winter blue, frost dendrites that grow across the frame, a flat-graphic frog that turns to glassy ice
and thaws back to green, a flatlining heart monitor, sugar crystals, thermometer + day counter; glassy chimes.
Usage: python3 engine/styles/day33_ice.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
_QC = {}
def Q(s, w=700):
    k = (int(s), w)
    if k not in _QC:
        f = ImageFont.truetype(f"{FONTS}/Quicksand.ttf", max(8, int(s)))
        try: f.set_variation_by_axes([w])
        except Exception: pass
        _QC[k] = f
    return _QC[k]
NAVY, DEEP, ICE, ICE2, WHT, GREEN, GREEN2, BROWN, PINK, GOLD = (10, 22, 48), (18, 46, 92), (170, 220, 245), (110, 170, 220), (240, 250, 255), (120, 170, 70), (80, 120, 50), (150, 105, 60), (255, 120, 140), (255, 210, 90)
yy, xx = np.mgrid[0:H, 0:W]
BG = (np.stack([NAVY[i] + (DEEP[i] - NAVY[i]) * (1 - yy / H) for i in range(3)], -1) + np.random.default_rng(33).normal(0, 3, (H, W, 1))).clip(0, 255).astype(np.uint8)

def make_frost(seed, n_roots, region):
    r = random.Random(seed); segs = []                                     # (x0,y0,x1,y1,t_start,t_end,width)
    def grow(x, y, a, L, t, depth, w):
        if depth > 5 or L < 12: return
        x1, y1 = x + L * math.cos(a), y + L * math.sin(a); dt = L / 900
        segs.append((x, y, x1, y1, t, t + dt, w))
        for side in (-1, 1):
            if r.random() < 0.85: grow(x + (x1 - x) * r.uniform(0.3, 0.8), y + (y1 - y) * r.uniform(0.3, 0.8), a + side * math.pi / 3, L * 0.5, t + dt * 0.6, depth + 1, max(2, w - 2))
        grow(x1, y1, a + r.uniform(-0.15, 0.15), L * 0.8, t + dt, depth + 1, max(2, w - 1))
    x0, y0, x1, y1 = region
    for k in range(n_roots):
        side = r.choice("ltrb")
        if side == "l": x, y, a = x0, r.uniform(y0, y1), r.uniform(-0.5, 0.5)
        elif side == "r": x, y, a = x1, r.uniform(y0, y1), math.pi + r.uniform(-0.5, 0.5)
        elif side == "t": x, y, a = r.uniform(x0, x1), y0, math.pi / 2 + r.uniform(-0.5, 0.5)
        else: x, y, a = r.uniform(x0, x1), y1, -math.pi / 2 + r.uniform(-0.5, 0.5)
        grow(x, y, a, r.uniform(140, 240), r.uniform(0, 0.4), 0, 7)
    return segs
FROST = make_frost(3, 22, (0, 0, W, H))
def frost(d, p, col=ICE):
    """p: growth time in seconds"""
    for (x0, y0, x1, y1, ts, te, w) in FROST:
        if p <= ts: continue
        u = min(1, (p - ts) / (te - ts)); d.line([(x0, y0), (x0 + (x1 - x0) * u, y0 + (y1 - y0) * u)], fill=col, width=w)

def mix(a, b, u): return tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3))
def frog(d, cx, cy, s=1.0, ice=0.0, t=0.0):
    g, g2, br = mix(GREEN, ICE, ice), mix(GREEN2, ICE2, ice), mix(BROWN, ICE2, ice)
    E = lambda x0, y0, x1, y1, c: d.ellipse([cx + x0 * s, cy + y0 * s, cx + x1 * s, cy + y1 * s], fill=c)
    E(-260, 40, -60, 200, g2); E(60, 40, 260, 200, g2)                     # back legs
    E(-300, 170, -150, 220, g2); E(150, 170, 300, 220, g2)                 # feet
    E(-200, -120, 200, 190, g)                                             # body
    E(-150, -230, 150, -40, g)                                             # head
    d.polygon([(cx - 150 * s, cy - 120 * s), (cx - 60 * s, cy - 90 * s), (cx - 130 * s, cy - 60 * s)], fill=br)  # mask stripe
    d.polygon([(cx + 150 * s, cy - 120 * s), (cx + 60 * s, cy - 90 * s), (cx + 130 * s, cy - 60 * s)], fill=br)
    for ex in (-1, 1):
        E(ex * 95 - 55, -290, ex * 95 + 55, -180, g)
        if ice > 0.6: d.line([(cx + (ex * 95 - 30) * s, cy - 235 * s), (cx + (ex * 95 + 30) * s, cy - 235 * s)], fill=NAVY, width=int(10 * s))
        else: E(ex * 95 - 30, -265, ex * 95 + 30, -205, NAVY); E(ex * 95 - 10, -255, ex * 95 + 8, -237, WHT)
    d.arc([cx - 90 * s, cy - 120 * s, cx + 90 * s, cy - 50 * s], 20, 160, fill=g2, width=int(8 * s))
    E(-80, 200, -20, 240, g2); E(20, 200, 80, 240, g2)
    if ice > 0.3:                                                          # glassy highlights
        a = int(200 * min(1, (ice - 0.3) / 0.5))
        d.line([(cx - 120 * s, cy - 40 * s), (cx - 40 * s, cy - 110 * s)], fill=mix(ICE, WHT, 0.8), width=int(12 * s))
        d.line([(cx + 60 * s, cy + 80 * s), (cx + 130 * s, cy + 20 * s)], fill=mix(ICE, WHT, 0.8), width=int(8 * s))

def title(d, s, y, size, col=WHT, w=700):
    while d.textlength(s, font=Q(size, w)) > W - 140: size -= 4
    d.text((W / 2, y), s, font=Q(size, w), fill=col, anchor="mm")
def pill(d, s, y, size=44, bg=ICE, fg=NAVY):
    tw = d.textlength(s, font=Q(size)); d.rounded_rectangle([W / 2 - tw / 2 - 30, y - size * 0.8, W / 2 + tw / 2 + 30, y + size * 0.8], int(size * 0.8), fill=bg); d.text((W / 2, y), s, font=Q(size), fill=fg, anchor="mm")

def S_hook(sc, lt, dur, t):
    img = Image.fromarray(BG.copy()); d = ImageDraw.Draw(img)
    frost(d, 0.6 + t * 0.5, (60, 100, 150))
    loop = sc.get("loop"); ice = 1.0 if not loop else 1 - ease((lt - 0.2) / 0.9)
    frog(d, W / 2, 1050 + (0 if ice > 0.5 else -60 * abs(math.sin(lt * 6))), 1.3, ice)
    title(d, "THIS FROG", 300, 120); title(d, "FREEZES SOLID", 440, 120, ICE)
    if loop and lt > 0.6: pill(d, "...AND WAKES UP", 1490, 56, GREEN, WHT)
    return img
def S_freeze(sc, lt, dur, t):
    img = Image.fromarray(BG.copy()); d = ImageDraw.Draw(img)
    p = ease((lt - 0.2) / 2.6); frost(d, 0.2 + lt * 0.8, (90, 140, 190))
    frog(d, W / 2, 1050, 1.1, p * 0.95)
    title(d, "UP TO", 290, 70, ICE); title(d, f"{int(60 * p)}% ICE", 420, 150)
    d.rounded_rectangle([140, 1430, W - 140, 1480], 25, outline=ICE, width=4); d.rounded_rectangle([146, 1436, 146 + (W - 292) * 0.6 * p / 0.6 * 0.6, 1474], 20, fill=ICE)
    return img
def S_flat(sc, lt, dur, t):
    img = Image.fromarray(BG.copy()); d = ImageDraw.Draw(img); frost(d, 3 + t * 0.3, (60, 100, 150))
    d.rounded_rectangle([90, 520, W - 90, 1100], 30, fill=(6, 14, 30), outline=ICE2, width=4)
    stop = 1.0
    pts = []
    for i in range(0, W - 220, 5):
        x = 110 + i; tt = lt - (W - 220 - i) / 500
        v = 0
        if tt < stop:
            ph = (tt * 1.4) % 1.0; v = (1 - abs(ph - 0.1) / 0.03) if abs(ph - 0.1) < 0.03 else 0
        pts.append((x, 810 - v * 200))
    d.line(pts, fill=PINK if lt < stop + 1.2 else ICE, width=6)
    title(d, "HEART: 0 BPM", 1180, 76, PINK); title(d, "BREATHING: NONE", 1290, 76, ICE)
    title(d, "STILL ALIVE?", 330, 110)
    return img
def S_sugar(sc, lt, dur, t):
    img = Image.fromarray(BG.copy()); d = ImageDraw.Draw(img); frost(d, 3, (50, 80, 130))
    title(d, "THE SECRET:", 280, 80, ICE); title(d, "SUGAR", 420, 170, GOLD)
    frog(d, W / 2, 1130, 0.9, 0.85)
    r = random.Random(4); n = int(30 * ease((lt - 0.3) / 1.8))
    for k in range(n):
        a = r.uniform(0, 2 * math.pi); rad = r.uniform(80, 260); x = W / 2 + rad * math.cos(a + t * 0.5); y = 1100 + rad * 0.8 * math.sin(a + t * 0.5); s_ = r.uniform(14, 26)
        d.rectangle([x - s_, y - s_, x + s_, y + s_], fill=WHT, outline=GOLD, width=3)
    if lt > 2.0: pill(d, "NATURAL ANTIFREEZE", 1520, 54, GOLD, NAVY)
    return img
def S_alaska(sc, lt, dur, t):
    img = Image.fromarray(BG.copy()); d = ImageDraw.Draw(img)
    thaw = ease((lt - dur + 2.6) / 1.2) if dur > 3 else 0
    frost(d, max(0.0, 6 - thaw * 6), (60, 100, 150))
    title(d, "ALASKA", 270, 120, ICE)
    tx = 200; d.rounded_rectangle([tx - 40, 450, tx + 40, 1150], 40, fill=WHT); d.ellipse([tx - 80, 1100, tx + 80, 1260], fill=WHT)
    lvl = ease((lt - 0.3) / 1.2); top = 600 + 480 * lvl if thaw == 0 else 1080 - 480 * thaw
    d.rounded_rectangle([tx - 22, top, tx + 22, 1150], 22, fill=(80, 160, 255) if thaw < 0.5 else (240, 90, 80)); d.ellipse([tx - 62, 1118, tx + 62, 1242], fill=(80, 160, 255) if thaw < 0.5 else (240, 90, 80))
    d.text((tx + 80, 1150), "−18 °C", font=Q(66), fill=ICE, anchor="lm")
    days = int(218 * ease((lt - 1.2) / 2.5))
    d.text((W - 110, 560), "FROZEN FOR", font=Q(48), fill=ICE, anchor="rm"); d.text((W - 110, 700), f"{days}", font=Q(190), fill=WHT, anchor="rm"); d.text((W - 110, 830), "DAYS", font=Q(60), fill=ICE, anchor="rm")
    hop = 0 if thaw < 1 else abs(math.sin((lt - dur + 1.4) * 6)) * 120
    frog(d, 650, 1290 - hop, 0.75, 1 - thaw)
    if thaw > 0.5: pill(d, "SPRING: HOP!", 1530, 56, GREEN, WHT)
    return img
def S_end(sc, lt, dur, t):
    img = Image.fromarray(BG.copy()); d = ImageDraw.Draw(img); frost(d, 1.5, (50, 80, 130))
    title(d, "SOUNDS FAKE ?!", 340, 120)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.2); cx, cy, w_, h_ = W / 2, 620, 330, 150
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=GREEN if on > 0.5 else ICE2, outline=WHT, width=5)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; d.ellipse([kx - h_ / 2 + 18, cy - h_ / 2 + 18, kx + h_ / 2 - 18, cy + h_ / 2 - 18], fill=WHT)
    d.text((cx - w_ / 2 - 30, cy), "FAKE", font=Q(64), fill=WHT if on < 0.5 else ICE2, anchor="rm"); d.text((cx + w_ / 2 + 30, cy), "TRUE", font=Q(64), fill=GREEN if on >= 0.5 else ICE2, anchor="lm")
    frog(d, W / 2, 1150, 0.9, 1 - on)
    return img
SCENES = dict(hook=S_hook, freeze=S_freeze, flat=S_flat, sugar=S_sugar, alaska=S_alaska, end=S_end)

voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
notes = [1318.5, 1567.98, 1975.5, 1760.0, 1318.5, 1174.66, 1567.98, 2093.0]
for k in range(int(total / 0.45)):                                     # glassy celesta
    place(music, k * 0.45, tone(notes[(k * 5) % 8], 1.4, decay=3.5, harm=(1, 2.76, 5.4)), 0.02)
    if k % 4 == 0: place(music, k * 0.45, tone((73.42, 65.41, 82.41, 61.74)[(k // 4) % 4], 2.0, decay=1.0, harm=(1, 2, 3)), 0.05)
hook_hit(music, 0.35)
for s_ in scene_starts(spec): whoosh(music, s_, 0.08)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.3)

groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 72
    while d.textlength(" ".join(ws), font=Q(size)) > W - 200 and size > 36: size -= 4
    f = Q(size); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1660
    d.rounded_rectangle([x - 30, y - 14, x + tw + 30, y + size + 30], 22, fill=WHT)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=(30, 120, 210) if on else NAVY); x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t); caption(img, t)
    ImageDraw.Draw(img).rectangle([0, H - 10, int(W * t / total), H], fill=ICE); return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
