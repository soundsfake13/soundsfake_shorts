"""Day 38 — MUSEUM-SCALE infographic style (a blue whale's heart is the size of a bumper car).
Natural-history-museum wall panel: warm cream card, thin black rules, specimen labels, scale silhouettes with
dimension lines, a big ECG monitor whose trace slows to 2 bpm; soft cello-like drone + heartbeat thumps.
Usage: python3 engine/styles/day38_museum.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
SERIF = lambda s: ImageFont.truetype(f"{FONTS}/DMSerifDisplay-Regular.ttf", max(8, int(s)))
_QC = {}
def Q(s, w=600):
    k = (int(s), w)
    if k not in _QC:
        f = ImageFont.truetype(f"{FONTS}/Quicksand.ttf", max(8, int(s)))
        try: f.set_variation_by_axes([w])
        except Exception: pass
        _QC[k] = f
    return _QC[k]
CREAM, INK, GREY, RED, DRED, BLUE, PALE = (242, 236, 222), (28, 28, 30), (150, 145, 135), (200, 40, 50), (130, 20, 30), (40, 70, 110), (226, 218, 200)
BASE = (np.full((H, W, 3), CREAM, np.float32) + np.random.default_rng(38).normal(0, 3, (H, W, 1))).clip(0, 255).astype(np.uint8)

def heart(d, cx, cy, s, col=RED, beat=1.0):
    s = s * beat
    d.ellipse([cx - 150 * s, cy - 120 * s, cx + 10 * s, cy + 40 * s], fill=col); d.ellipse([cx - 20 * s, cy - 130 * s, cx + 150 * s, cy + 30 * s], fill=col)
    d.polygon([(cx - 145 * s, cy - 20 * s), (cx + 148 * s, cy - 30 * s), (cx + 10 * s, cy + 190 * s)], fill=col)
    d.rounded_rectangle([cx - 40 * s, cy - 230 * s, cx + 20 * s, cy - 90 * s], int(24 * s), fill=DRED)        # aorta
    d.rounded_rectangle([cx + 30 * s, cy - 200 * s, cx + 80 * s, cy - 90 * s], int(20 * s), fill=BLUE)
    d.arc([cx - 60 * s, cy - 90 * s, cx + 40 * s, cy + 120 * s], 200, 300, fill=DRED, width=max(2, int(8 * s)))

def person(d, x, y, h, col=INK):
    s = h / 360; d.ellipse([x - 26 * s, y - 360 * s, x + 26 * s, y - 308 * s], fill=col)
    d.rounded_rectangle([x - 40 * s, y - 300 * s, x + 40 * s, y - 150 * s], int(20 * s), fill=col)
    d.rectangle([x - 34 * s, y - 160 * s, x - 6 * s, y], fill=col); d.rectangle([x + 6 * s, y - 160 * s, x + 34 * s, y], fill=col)

def bumper(d, cx, by, s=1.0):
    d.rounded_rectangle([cx - 230 * s, by - 150 * s, cx + 230 * s, by - 20 * s], int(60 * s), fill=(80, 130, 190), outline=INK, width=5)
    d.rounded_rectangle([cx - 260 * s, by - 60 * s, cx + 260 * s, by], int(30 * s), fill=INK)
    d.line([(cx + 60 * s, by - 150 * s), (cx + 60 * s, by - 420 * s)], fill=INK, width=8); d.rectangle([cx + 50 * s, by - 440 * s, cx + 70 * s, by - 420 * s], fill=RED)

def dim_line(d, x0, y0, x1, y1, label, col=INK):
    d.line([(x0, y0), (x1, y1)], fill=col, width=3)
    for (x, y) in ((x0, y0), (x1, y1)):
        if y0 == y1: d.line([(x, y - 18), (x, y + 18)], fill=col, width=3)
        else: d.line([(x - 18, y), (x + 18, y)], fill=col, width=3)
    d.text(((x0 + x1) / 2, (y0 + y1) / 2 - (30 if y0 == y1 else 0)), label, font=Q(40, 700), fill=col, anchor="mm")

def panel(img, tag, title, sub=None):
    d = ImageDraw.Draw(img)
    d.line([(80, 150), (W - 80, 150)], fill=INK, width=3); d.text((80, 180), tag, font=Q(34, 700), fill=GREY, anchor="lm")
    d.text((W - 80, 180), "HALL OF GIANTS", font=Q(34, 700), fill=GREY, anchor="rm")
    size = 104
    while d.textlength(title, font=SERIF(size)) > W - 160: size -= 4
    d.text((80, 300), title, font=SERIF(size), fill=INK, anchor="lm")
    if sub: d.text((80, 400), sub, font=Q(48, 500), fill=RED, anchor="lm")
    d.line([(80, 460), (W - 80, 460)], fill=INK, width=1)
    return d

def beatpulse(t, bpm):
    ph = (t * bpm / 60) % 1.0; return 1 + 0.08 * math.exp(-ph * 18)

def S_hook(sc, lt, dur, t):
    img = Image.fromarray(BASE.copy()); d = panel(img, "SPECIMEN No. 38", "A WHALE'S HEART", "= the size of a bumper car")
    bumper(d, 730, 1330, 1.0); heart(d, 300, 1110, 0.85, beat=beatpulse(t, 30))
    d.text((W / 2, 1520), "fig. 1 — heart vs. bumper car", font=Q(36, 500), fill=GREY, anchor="mm")
    if sc.get("loop"):
        u = back(lt / 0.3)
        if u > 0: d.rounded_rectangle([W - 420, 520, W - 80, 640], 16, fill=RED); d.text((W - 250, 580), "...AND MORE", font=Q(int(46 * min(1.1, u)), 700), fill=CREAM, anchor="mm")
    return img
def S_scale(sc, lt, dur, t):
    img = Image.fromarray(BASE.copy()); d = panel(img, "WEIGHT", "~180 KILOGRAMS", "Royal Ontario Museum specimen")
    tilt = 0.12 * (1 - ease((lt - 0.3) / 1.2)) - 0.0
    cx, cy = W / 2, 760; L = 380
    d.polygon([(cx - 40, 1450), (cx + 40, 1450), (cx + 12, cy), (cx - 12, cy)], fill=INK)
    lx, ly = cx - L * math.cos(tilt), cy + L * math.sin(tilt); rx, ry = cx + L * math.cos(tilt), cy - L * math.sin(tilt)
    d.line([(lx, ly), (rx, ry)], fill=INK, width=12); d.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], fill=INK)
    for (x, y) in ((lx, ly), (rx, ry)): d.line([(x, y), (x - 120, y + 260)], fill=INK, width=4); d.line([(x, y), (x + 120, y + 260)], fill=INK, width=4); d.rectangle([x - 150, y + 260, x + 150, y + 274], fill=INK)
    heart(d, lx, ly + 150, 0.55, beat=beatpulse(t, 30))
    n = 2 if lt > 0.6 else 0
    for k in range(n): person(d, rx - 60 + k * 120, ry + 258, 220 * ease((lt - 0.6 - k * 0.2) / 0.3))
    if lt > 1.6: d.text((rx, ry + 330), "2 ADULTS", font=Q(48, 700), fill=RED, anchor="mm")
    return img
def S_whale(sc, lt, dur, t):
    img = Image.fromarray(BASE.copy()); d = panel(img, "CONTEXT", "BIGGEST HEART KNOWN", "in the biggest animal ever")
    p = eout(lt / 1.4); x0 = W + 50 - (W - 20) * p; y = 1000 + 14 * math.sin(t * 1.4); k_ = 0.78
    P = lambda a, b: (x0 + a * k_, y + b * k_)
    pts = [P(0, 0), P(120, -90), P(600, -110), P(1050, -40), P(1200, -110), P(1170, 0), P(1200, 110), P(1050, 40), P(600, 90), P(120, 80)]
    d.polygon(pts, fill=BLUE); ex, ey = P(130, -20); d.ellipse([ex - 10, ey - 10, ex + 10, ey + 10], fill=CREAM)
    for k in range(10): a, b = P(80 + k * 30, 30); c, e = P(120 + k * 32, 70); d.line([(a, b), (c, e)], fill=(70, 100, 140), width=4)
    hx = x0 + 300; heart(d, hx, y, 0.18, beat=beatpulse(t, 30))
    if lt > 1.2:
        dim_line(d, x0, y + 200, x0 + 936, y + 200, "up to ~30 m")
        person(d, 140, 1400, 90); d.text((140, 1440), "you", font=Q(34, 600), fill=GREY, anchor="mm")
    return img
def ecg_trace(d, x0, y0, w, h, t, bpm, col=RED, window=6.0):
    pts = []
    for i in range(0, w, 4):
        tt = t - window + window * i / w; ph = (tt * bpm / 60) % 1.0; sec = ph * 60 / bpm
        v = 0.0
        if sec < 0.08: v = math.sin(sec / 0.08 * math.pi) * 0.15
        elif 0.12 < sec < 0.16: v = -0.2
        elif 0.16 <= sec < 0.22: v = 1.0 - abs(sec - 0.19) / 0.03 * 1.0
        elif 0.22 <= sec < 0.26: v = -0.3
        elif 0.4 < sec < 0.55: v = 0.25 * math.sin((sec - 0.4) / 0.15 * math.pi)
        pts.append((x0 + i, y0 + h / 2 - v * h * 0.42))
    d.line(pts, fill=col, width=6)
def monitor(d, t, bpm, label):
    d.rounded_rectangle([90, 560, W - 90, 1230], 30, fill=(20, 26, 24)); d.rounded_rectangle([110, 580, W - 110, 1210], 20, fill=(14, 40, 30))
    for gx in range(130, W - 110, 60): d.line([(gx, 600), (gx, 1190)], fill=(24, 60, 44), width=1)
    for gy in range(600, 1200, 60): d.line([(130, gy), (W - 130, gy)], fill=(24, 60, 44), width=1)
    ecg_trace(d, 140, 640, W - 280, 380, t, bpm, (90, 240, 140))
    d.text((150, 1110), label, font=Q(44, 700), fill=(90, 240, 140), anchor="lm")
def S_fast(sc, lt, dur, t):
    img = Image.fromarray(BASE.copy()); d = panel(img, "ECG · SURFACE", "AT THE SURFACE", "first ECG of a wild blue whale, 2019")
    monitor(d, t, 34, ""); d.text((W - 150, 1110), "30+ BPM", font=SERIF(84), fill=(90, 240, 140), anchor="rm")
    heart(d, W / 2, 1480, 0.55, beat=beatpulse(t, 34) ** 2)
    return img
def S_slow(sc, lt, dur, t):
    img = Image.fromarray(BASE.copy()); d = panel(img, "ECG · DEEP DIVE", "ON A DEEP DIVE", "the heart nearly stops")
    bpm = 34 - 32 * ease((lt - 0.3) / 2.2); monitor(d, t, bpm, "")
    d.text((W - 150, 1110), f"{int(round(bpm))} BPM", font=SERIF(84), fill=(255, 120, 120) if bpm < 5 else (90, 240, 140), anchor="rm")
    heart(d, W / 2, 1480, 0.55, beat=beatpulse(t, bpm) ** 2)
    if bpm < 3: d.text((W / 2, 1300), "2 beats. per. minute.", font=Q(52, 700), fill=RED, anchor="mm")
    return img
def S_end(sc, lt, dur, t):
    img = Image.fromarray(BASE.copy()); d = panel(img, "VERDICT", "SOUNDS FAKE ?!", None)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.2); cx, cy, w_, h_ = W / 2, 700, 330, 150
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=RED if on > 0.5 else PALE, outline=INK, width=5)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; d.ellipse([kx - h_ / 2 + 18, cy - h_ / 2 + 18, kx + h_ / 2 - 18, cy + h_ / 2 - 18], fill=CREAM, outline=INK, width=4)
    d.text((cx - w_ / 2 - 30, cy), "FAKE", font=SERIF(64), fill=INK if on < 0.5 else GREY, anchor="rm"); d.text((cx + w_ / 2 + 30, cy), "TRUE", font=SERIF(64), fill=RED if on >= 0.5 else GREY, anchor="lm")
    heart(d, W / 2, 1180, 0.9, beat=beatpulse(t, 30))
    return img
SCENES = dict(hook=S_hook, scale=S_scale, whale=S_whale, fast=S_fast, slow=S_slow, end=S_end)

voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
chords = [(65.41, 98.0, 130.81), (55.0, 82.41, 130.81), (43.65, 87.31, 130.81), (49.0, 73.42, 123.47)]
for k in range(int(total / 2.4) + 1):
    for f in chords[k % 4]: place(music, k * 2.4, tone(f, 2.8, decay=0.8, harm=(1, 2, 3, 4)), 0.03)
# heartbeat thumps synced to visuals
def thump(): return tone(48, 0.25, decay=14, harm=(1, 2))
for ln in spec["lines"]:
    ty = ln["scene"]["type"]; s0, s1 = ln["_s"], ln["_se"]
    if ty == "slow":
        tt = s0;
        while tt < s1:
            lt = tt - s0; bpm = 34 - 32 * ease((lt - 0.3) / 2.2); place(music, tt, thump(), 0.25); place(music, tt + 0.22, thump(), 0.15); tt += 60 / bpm
    elif ty in ("fast",):
        tt = s0
        while tt < s1: place(music, tt, thump(), 0.25); place(music, tt + 0.22, thump(), 0.15); tt += 60 / 34
hook_hit(music, 0.35)
for s_ in scene_starts(spec): whoosh(music, s_, 0.08)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.35)

groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 70
    while d.textlength(" ".join(ws), font=Q(size, 700)) > W - 200 and size > 36: size -= 4
    f = Q(size, 700); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1640
    d.rectangle([x - 30, y - 14, x + tw + 30, y + size + 30], fill=INK)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=(255, 120, 120) if on else CREAM); x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t); caption(img, t)
    ImageDraw.Draw(img).rectangle([0, H - 10, int(W * t / total), H], fill=RED); return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
