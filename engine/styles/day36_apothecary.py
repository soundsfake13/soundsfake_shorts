"""Day 36 — VICTORIAN APOTHECARY style (tomatoes were sold as medicine in the 1830s).
Engraved-label look: cream paper, double rules and corner flourishes, two-colour letterpress (black + vermilion),
serif display type, a medicine bottle and pill box, newspaper columns, rubber 'QUACKERY' stamps.
Usage: python3 engine/styles/day36_apothecary.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
SERIF = lambda s: ImageFont.truetype(f"{FONTS}/DMSerifDisplay-Regular.ttf", int(s))
def PF(s, w=700):
    f = ImageFont.truetype(f"{FONTS}/PlayfairDisplay.ttf", int(s)); f.set_variation_by_axes([w]); return f
PAPER, BLACK, VERM, SEP, GREEN = (240, 228, 200), (30, 24, 20), (196, 52, 32), (120, 90, 60), (60, 90, 60)
BASE = (np.full((H, W, 3), PAPER, np.float32) + np.random.default_rng(36).normal(0, 6, (H, W, 1))).clip(0, 255).astype(np.uint8)

def frame_border(d, x0, y0, x1, y1, col=BLACK):
    d.rectangle([x0, y0, x1, y1], outline=col, width=8); d.rectangle([x0 + 16, y0 + 16, x1 - 16, y1 - 16], outline=col, width=3)
    for (cx, cy) in ((x0 + 16, y0 + 16), (x1 - 16, y0 + 16), (x0 + 16, y1 - 16), (x1 - 16, y1 - 16)):
        d.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], outline=col, width=4); d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=col)

def ctext(d, s, y, size, col=BLACK, font=None, maxw=W - 220):
    font = font or SERIF
    while d.textlength(s, font=font(size)) > maxw and size > 30: size -= 4
    d.text((W / 2, y), s, font=font(size), fill=col, anchor="mm"); return size

def rule(d, y, w=500, col=BLACK):
    d.line([(W / 2 - w / 2, y), (W / 2 + w / 2, y)], fill=col, width=4); d.polygon([(W / 2, y - 12), (W / 2 + 12, y), (W / 2, y + 12), (W / 2 - 12, y)], fill=col)

def bottle(d, cx, cy, s=1.0):
    d.rounded_rectangle([cx - 150 * s, cy - 120 * s, cx + 150 * s, cy + 300 * s], int(40 * s), fill=(120, 60, 40), outline=BLACK, width=6)
    d.rectangle([cx - 50 * s, cy - 230 * s, cx + 50 * s, cy - 120 * s], fill=(120, 60, 40), outline=BLACK, width=6)
    d.rectangle([cx - 62 * s, cy - 280 * s, cx + 62 * s, cy - 230 * s], fill=(200, 180, 150), outline=BLACK, width=6)
    d.rectangle([cx - 120 * s, cy - 40 * s, cx + 120 * s, cy + 200 * s], fill=PAPER, outline=BLACK, width=4)
    d.text((cx, cy + 20 * s), "TOMATO", font=SERIF(int(48 * s)), fill=VERM, anchor="mm"); d.text((cx, cy + 80 * s), "EXTRACT", font=SERIF(int(36 * s)), fill=BLACK, anchor="mm")
    d.text((cx, cy + 140 * s), "cures all ills", font=PF(int(28 * s), 400), fill=BLACK, anchor="mm")

def tomato(d, cx, cy, r):
    d.ellipse([cx - r, cy - r * 0.85, cx + r, cy + r * 0.85], fill=VERM, outline=BLACK, width=5)
    for k in range(5): a = -math.pi / 2 + (k - 2) * 0.5; d.line([(cx, cy - r * 0.8), (cx + r * 0.5 * math.cos(a), cy - r * 0.8 + r * 0.35 * math.sin(a) - 10)], fill=GREEN, width=8)

def stamp(img, s, cx, cy, size, rot=-14, u=1.0, col=VERM):
    if u <= 0: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); f = SERIF(int(size * (1.8 - 0.8 * u))); tw = d.textlength(s, font=f)
    d.rectangle([cx - tw / 2 - 30, cy - size * 0.8, cx + tw / 2 + 30, cy + size * 0.8], outline=col + (230,), width=10); d.text((cx, cy), s, font=f, fill=col + (230,), anchor="mm")
    lay = lay.rotate(rot, center=(cx, cy), resample=Image.BICUBIC); img.paste(lay, (0, 0), lay)

def S_hook(sc, lt, dur, t):
    img = Image.fromarray(BASE.copy()); d = ImageDraw.Draw(img); frame_border(d, 50, 150, W - 50, 1520)
    ctext(d, "IN THE 1830s,", 290, 70, BLACK, PF); ctext(d, "TOMATOES WERE", 400, 104); ctext(d, "SOLD AS MEDICINE", 520, 104, VERM); rule(d, 610)
    bottle(d, W / 2, 1000 + 8 * math.sin(t * 2), 1.15)
    if sc.get("loop"): stamp(img, "...WITH A SECRET", W / 2, 1390, 64, rot=-6, u=back(lt / 0.3))
    return img
def S_claims(sc, lt, dur, t):
    img = Image.fromarray(BASE.copy()); d = ImageDraw.Draw(img); frame_border(d, 50, 150, W - 50, 1520)
    ctext(d, "DR. BENNETT, 1834:", 280, 64, BLACK, PF); ctext(d, "TOMATOES TREAT...", 390, 86, VERM); rule(d, 470)
    for k, s in enumerate(["Diarrhea", "Indigestion", "Headaches", "...even cholera?!"]):
        u = ease((lt - 0.4 - k * 0.5) / 0.3)
        if u <= 0: continue
        y = 620 + k * 170
        if k < 3: d.line([(200, y), (230, y + 30), (280, y - 35)], fill=VERM, width=12, joint="curve")
        else: d.text((235, y), "?", font=SERIF(90), fill=VERM, anchor="mm")
        d.text((330, y), s, font=PF(84, 600), fill=BLACK, anchor="lm")
    tomato(d, 860, 1330, 110)
    return img
def S_pills(sc, lt, dur, t):
    img = Image.fromarray(BASE.copy()); d = ImageDraw.Draw(img); frame_border(d, 50, 150, W - 50, 1520)
    ctext(d, "TOMATO PILLS", 300, 120, VERM); ctext(d, "~ cure almost anything ~", 420, 60, BLACK, lambda s: PF(s, 400)); rule(d, 500)
    d.rounded_rectangle([250, 760, 830, 1080], 30, fill=(150, 100, 60), outline=BLACK, width=6); d.rectangle([290, 800, 790, 1040], fill=PAPER, outline=BLACK, width=3)
    d.text((540, 880), "PILLS", font=SERIF(80), fill=BLACK, anchor="mm"); d.text((540, 970), "of Tomato", font=PF(46, 500), fill=VERM, anchor="mm")
    r = random.Random(3); n = int(22 * ease((lt - 0.3) / 1.4))
    for k in range(n): x, y = 300 + r.uniform(0, 480), 1150 + r.uniform(0, 260); d.ellipse([x - 26, y - 20, x + 26, y + 20], fill=(150, 80, 50), outline=BLACK, width=3)
    return img
def S_feud(sc, lt, dur, t):
    img = Image.fromarray(BASE.copy()); d = ImageDraw.Draw(img)
    ctext(d, "THE PILL WAR", 260, 104, BLACK); ctext(d, "two sellers · two years · newspapers", 360, 46, SEP, lambda s: PF(s, 500)); rule(d, 430)
    for k, x0 in enumerate((80, 560)):
        d.rectangle([x0, 520, x0 + 440, 1420], fill=(232, 220, 192), outline=BLACK, width=4)
        u = back((lt - 0.4 - k * 0.6) / 0.3)
        if u > 0: d.text((x0 + 220, 640), "FRAUD!", font=SERIF(max(8, int(96 * min(1.1, u)))), fill=VERM, anchor="mm")
        for j in range(14): w_ = 360 if j % 4 else 250; d.line([(x0 + 40, 740 + j * 44), (x0 + 40 + w_, 740 + j * 44)], fill=(90, 80, 70), width=6)
    return img
def S_test(sc, lt, dur, t):
    img = Image.fromarray(BASE.copy()); d = ImageDraw.Draw(img); frame_border(d, 50, 150, W - 50, 1520)
    ctext(d, "THEN THEY TESTED THEM", 300, 76, BLACK)
    d.ellipse([440, 760, 640, 920], fill=(150, 80, 50), outline=BLACK, width=5)
    p = ease((lt - 0.3) / 0.8); mx = 300 + 240 * p
    d.ellipse([mx - 150, 690, mx + 150, 990], outline=BLACK, width=14); d.line([(mx + 105, 950), (mx + 230, 1120)], fill=BLACK, width=26)
    if lt > 1.0: ctext(d, "TOMATO: 0%", 1220, 120, VERM)
    stamp(img, "BASICALLY LAXATIVES", W / 2, 1390, 56, rot=-8, u=back((lt - 2.0) / 0.3))
    return img
def S_end(sc, lt, dur, t):
    img = Image.fromarray(BASE.copy()); d = ImageDraw.Draw(img); frame_border(d, 50, 150, W - 50, 1520)
    ctext(d, "SOUNDS FAKE ?!", 360, 110, VERM); rule(d, 460)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.2); cx, cy, w_, h_ = W / 2, 900, 330, 150
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=VERM if on > 0.5 else (200, 186, 160), outline=BLACK, width=6)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; d.ellipse([kx - h_ / 2 + 18, cy - h_ / 2 + 18, kx + h_ / 2 - 18, cy + h_ / 2 - 18], fill=PAPER, outline=BLACK, width=4)
    d.text((cx - w_ / 2 - 30, cy), "FAKE", font=SERIF(64), fill=BLACK if on < 0.5 else (160, 150, 130), anchor="rm"); d.text((cx + w_ / 2 + 30, cy), "TRUE", font=SERIF(64), fill=VERM if on >= 0.5 else (160, 150, 130), anchor="lm")
    tomato(d, W / 2, 1250, 120)
    return img
SCENES = dict(hook=S_hook, claims=S_claims, pills=S_pills, feud=S_feud, test=S_test, end=S_end)

voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
mel = [392.0, 440.0, 493.88, 523.25, 493.88, 440.0, 392.0, 349.23]
for k in range(int(total / 0.36)):                                     # saloon-piano waltz feel
    place(music, k * 0.36, tone(mel[k % 8], 0.5, decay=6, harm=(1, 2, 3, 5)), 0.04)
    if k % 3 == 0: place(music, k * 0.36, tone(98.0 if (k // 6) % 2 == 0 else 130.81, 0.6, decay=5, harm=(1, 2)), 0.06)
    else: place(music, k * 0.36, sum(tone(f, 0.3, decay=9, harm=(1, 2)) for f in (196.0, 246.94, 293.66)), 0.015)
hook_hit(music, 0.35)
for s_ in scene_starts(spec): whoosh(music, s_, 0.1)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.3)

groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 68
    while d.textlength(" ".join(ws), font=PF(size, 800)) > W - 200 and size > 36: size -= 4
    f = PF(size, 800); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1610
    d.rectangle([x - 30, y - 12, x + tw + 30, y + size + 28], fill=BLACK)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=(240, 120, 90) if on else PAPER); x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t); caption(img, t)
    ImageDraw.Draw(img).rectangle([0, H - 10, int(W * t / total), H], fill=VERM); return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
