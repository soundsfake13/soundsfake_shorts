"""Day 35 — 1960s MOD WALLPAPER style (bubble wrap was invented as wallpaper).
Bold repeating retro patterns (mustard, burnt orange, teal, chocolate), glossy bubbles that inflate out of the
pattern and POP, rounded retro display type. Frame 0 = full claim.
Usage: python3 engine/styles/day35_wallpaper.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
RF = lambda s: ImageFont.truetype(f"{FONTS}/Righteous.ttf", int(s))
MUST, ORNG, TEAL, CHOC, CREAM, PINK = (232, 178, 48), (214, 96, 40), (32, 128, 128), (74, 44, 30), (246, 234, 206), (226, 120, 140)

def pattern(kind, cols, t=0.0, cell=180):
    img = Image.new("RGB", (W, H), cols[0]); d = ImageDraw.Draw(img); off = (t * 20) % cell
    for j in range(-1, H // cell + 2):
        for i in range(-1, W // cell + 2):
            cx, cy = i * cell + (j % 2) * cell / 2, j * cell + off
            if kind == "flower":
                for k in range(6): a = k * math.pi / 3; d.ellipse([cx + 40 * math.cos(a) - 34, cy + 40 * math.sin(a) - 34, cx + 40 * math.cos(a) + 34, cy + 40 * math.sin(a) + 34], fill=cols[1])
                d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=cols[2])
            elif kind == "circles":
                for r, c in ((80, cols[1]), (56, cols[2]), (30, cols[1])): d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
            elif kind == "waves":
                d.arc([cx - 90, cy - 60, cx + 90, cy + 60], 0, 180, fill=cols[1], width=24); d.arc([cx - 50, cy - 30, cx + 50, cy + 30], 0, 180, fill=cols[2], width=18)
    return img

def bubble(img, cx, cy, r, pop=0.0):
    if r <= 1: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    if pop > 0:                                                     # burst lines
        for k in range(10): a = k * 0.63; d.line([(cx + r * math.cos(a), cy + r * math.sin(a)), (cx + r * (1.4 + pop) * math.cos(a), cy + r * (1.4 + pop) * math.sin(a))], fill=(255, 255, 255, int(255 * (1 - pop))), width=6)
        img.paste(lay, (0, 0), lay); return
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 70), outline=(255, 255, 255, 200), width=4)
    d.ellipse([cx - r * 0.55, cy - r * 0.6, cx - r * 0.15, cy - r * 0.25], fill=(255, 255, 255, 220))
    sh = lay.filter(ImageFilter.GaussianBlur(1.5)); img.paste(sh, (0, 0), sh)

def panel(img, lines, y=300, size=110, cols=(CREAM, CHOC), accent=None, u=1.0):
    if u <= 0: return
    d = ImageDraw.Draw(img); hs = []
    for s in lines:
        sz = size
        while d.textlength(s, font=RF(sz)) > W - 200 and sz > 40: sz -= 4
        hs.append(sz)
    h = sum(s * 1.18 for s in hs) + 70; yy = y + (1 - u) * 60
    d.rounded_rectangle([60, yy, W - 60, yy + h], 60, fill=cols[0], outline=cols[1], width=10)
    cy = yy + 40
    for i, (s, sz) in enumerate(zip(lines, hs)):
        d.text((W / 2, cy), s, font=RF(sz), fill=ORNG if accent and str(i) in accent else cols[1], anchor="ma"); cy += sz * 1.18

def S_hook(sc, lt, dur, t):
    img = pattern("flower", (MUST, ORNG, CHOC), t)
    r = random.Random(1)
    for k in range(9):
        bx, by = r.uniform(120, W - 120), r.uniform(860, 1480); rr = 70 + 40 * math.sin(t * 2 + k)
        bubble(img, bx, by, rr)
    panel(img, ["BUBBLE WRAP", "WAS MEANT TO BE", "WALLPAPER"], 240, 110, accent={"2": 1})
    if sc.get("loop"): d = ImageDraw.Draw(img); d.rounded_rectangle([180, 1330, W - 180, 1460], 60, fill=CHOC); d.text((W / 2, 1395), "...AND IT FAILED. TWICE.", font=RF(64), fill=CREAM, anchor="mm")
    return img
def S_curtains(sc, lt, dur, t):
    img = pattern("waves", (TEAL, CREAM, MUST), t); d = ImageDraw.Draw(img)
    p = ease((lt - 0.3) / 1.2)
    for k, x in enumerate((240 + 120 * p, W - 240 - 120 * p)):
        d.rectangle([x - 150, 520, x + 150, 1300], fill=(220, 236, 240), outline=CHOC, width=6)
        for j in range(8): d.line([(x - 150 + j * 42, 520), (x - 150 + j * 42, 1300)], fill=(190, 210, 216), width=4)
    if p > 0.9:
        r = random.Random(3)
        for k in range(14): bubble(img, r.uniform(330, 750), r.uniform(600, 1240), 40 * ease((lt - 1.5 - k * 0.05) / 0.4))
    panel(img, ["1957", "2 SHOWER CURTAINS + AIR"], 210, 96, cols=(CREAM, CHOC), accent={"0": 1})
    return img
def S_walls(sc, lt, dur, t):
    img = pattern("circles", (CREAM, TEAL, ORNG), t); d = ImageDraw.Draw(img)
    r = random.Random(4)
    for k in range(18):
        bx, by = 120 + (k % 6) * 170, 620 + (k // 6) * 230; pop = ease((lt - 0.4 - k * 0.06) / 0.25)
        bubble(img, bx, by, 70, pop if pop > 0 else 0.0)
    panel(img, sc.get("lines", ["AS WALLPAPER?", "FLOP."]), 240, 120, accent={"1": 1})
    return img
def S_green(sc, lt, dur, t):
    img = pattern("waves", (PINK, CREAM, CHOC), t); d = ImageDraw.Draw(img)
    d.polygon([(200, 1300), (200, 900), (540, 640), (880, 900), (880, 1300)], fill=(210, 236, 220), outline=CHOC)
    for k in range(5): d.line([(200 + k * 170, 1300), (200 + k * 170, 900 - (k * 170 if k <= 2 else (4 - k) * 170) * 0.76)], fill=CHOC, width=6)
    stamp = ease((lt - 1.0) / 0.3); panel(img, ["GREENHOUSE", "INSULATION?"], 230, 110)
    if stamp > 0: d = ImageDraw.Draw(img); d.rounded_rectangle([250, 1040, 830, 1180], 30, outline=ORNG, width=12); d.text((540, 1110), "FLOP #2", font=RF(int(90 * (2 - stamp))), fill=ORNG, anchor="mm")
    return img
def S_computer(sc, lt, dur, t):
    img = pattern("circles", (TEAL, MUST, CREAM), t); d = ImageDraw.Draw(img)
    d.rounded_rectangle([230, 760, 850, 1240], 30, fill=(200, 200, 196), outline=CHOC, width=8)          # generic 1960s mainframe
    for k in range(3): d.ellipse([290 + k * 190, 820, 410 + k * 190, 940], fill=(90, 90, 96), outline=CHOC, width=6)
    for k in range(8): d.rectangle([290 + k * 66, 1010, 330 + k * 66, 1040], fill=ORNG if k % 3 == 0 else CHOC)
    r = random.Random(6); u = ease((lt - 0.4) / 0.8)
    for k in range(26): a = k * 0.24; bubble(img, 540 + 400 * math.cos(a) * (0.6 + 0.4 * u), 1000 + 360 * math.sin(a) * (0.6 + 0.4 * u), 46 * u)
    panel(img, ["A COMPUTER NEEDED", "SAFE SHIPPING"], 230, 96)
    if lt > 1.4: d = ImageDraw.Draw(img); d.rounded_rectangle([200, 1330, 880, 1460], 60, fill=ORNG); d.text((540, 1395), "THE RIGHT JOB, AT LAST", font=RF(56), fill=CREAM, anchor="mm")
    return img
def S_end(sc, lt, dur, t):
    img = pattern("flower", (MUST, ORNG, CHOC), t); d = ImageDraw.Draw(img)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.2); cx, cy, w_, h_ = W / 2, 980, 340, 150
    d.rounded_rectangle([60, 820, W - 60, 1140], 60, fill=CREAM, outline=CHOC, width=10)
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=TEAL if on > 0.5 else (190, 170, 150), outline=CHOC, width=6)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; bubble(img, kx, cy, h_ / 2 - 16)
    d = ImageDraw.Draw(img); d.text((cx - w_ / 2 - 30, cy), "FAKE", font=RF(58), fill=CHOC if on < 0.5 else (170, 150, 130), anchor="rm"); d.text((cx + w_ / 2 + 30, cy), "TRUE", font=RF(58), fill=ORNG if on >= 0.5 else (170, 150, 130), anchor="lm")
    panel(img, ["SOUNDS FAKE ?!"], 360, 120)
    return img
SCENES = dict(hook=S_hook, curtains=S_curtains, walls=S_walls, green=S_green, computer=S_computer, end=S_end)

voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
for k in range(int(total / 0.25)):                                   # swingy 60s organ + pop percussion
    ch = [[261.63, 329.63, 392.0], [293.66, 349.23, 440.0], [246.94, 293.66, 392.0], [261.63, 329.63, 392.0]][(k // 8) % 4]
    if k % 2 == 0: place(music, k * 0.25, sum(tone(f, 0.24, decay=6, harm=(1, 2, 4)) for f in ch), 0.022)
    if k % 4 == 1: place(music, k * 0.25, np.sin(2 * np.pi * 900 * np.arange(int(0.03 * SR)) / SR) * np.exp(-np.arange(int(0.03 * SR)) / SR * 150), 0.05)
hook_hit(music, 0.35)
for s_ in scene_starts(spec): whoosh(music, s_, 0.12)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.3)

groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0].upper() for i in g]; size = 66
    while d.textlength(" ".join(ws), font=RF(size)) > W - 200 and size > 36: size -= 4
    f = RF(size); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1610
    d.rounded_rectangle([x - 34, y - 14, x + tw + 34, y + size + 26], 40, fill=CHOC)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=MUST if on else CREAM); x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t); caption(img, t)
    ImageDraw.Draw(img).rectangle([0, H - 10, int(W * t / total), H], fill=ORNG); return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
