"""Day 39 — FILM-NOIR style (crows remember human faces).
Black-and-white detective film: venetian-blind shadows, rain streaks, flickering grain, spotlight vignette,
case-file captions; crows are ink silhouettes with the only colour in the frame — red eyes and red stamps.
Usage: python3 engine/styles/day39_noir.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
SERIF = lambda s: ImageFont.truetype(f"{FONTS}/DMSerifDisplay-Regular.ttf", max(8, int(s)))
_QC = {}
def Q(s, w=700):
    k = (int(s), w)
    if k not in _QC:
        f = ImageFont.truetype(f"{FONTS}/Quicksand.ttf", max(8, int(s)))
        try: f.set_variation_by_axes([w])
        except Exception: pass
        _QC[k] = f
    return _QC[k]
BLK, WHT, G1, G2, G3, RED = (8, 8, 10), (236, 236, 230), (40, 40, 44), (90, 90, 94), (160, 160, 162), (220, 30, 40)
rng = np.random.default_rng(39)
GRAIN = [rng.normal(0, 14, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]
yy, xx = np.mgrid[0:H, 0:W]
VIG = (1.15 - 0.9 * np.clip(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.45) / (H * 0.6)) ** 2, 0, 1))[..., None].astype(np.float32)
BLINDS = (0.62 + 0.38 * (((xx + yy * 0.45) // 70) % 2))[..., None].astype(np.float32)

def post(img, t, blinds=True):
    a = np.asarray(img).astype(np.float32)
    if blinds: a *= BLINDS
    a *= VIG * (0.96 + 0.04 * math.sin(t * 37))
    g = GRAIN[int(t * 24) % 6]; a += np.repeat(np.repeat(g, 2, 0), 2, 1)
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))

def rain(d, t, n=70, col=G2):
    r = random.Random(int(t * 12))
    for k in range(n):
        x, y = r.uniform(0, W), r.uniform(0, H); d.line([(x, y), (x - 14, y + 70)], fill=col, width=2)

def crow(d, x, y, s=1.0, flip=False, wing=0.0, eye=True):
    f = -1 if flip else 1; P = lambda a, b: (x + f * a * s, y + b * s)
    d.polygon([P(-120, 10), P(-40, -50), P(60, -60), P(110, -30), P(160, -20), P(110, 0), P(60, 40), P(-60, 50), P(-180, 60), P(-200, 40)], fill=BLK)   # body + tail
    d.ellipse([x + f * 40 * s - 55 * s, y - 115 * s, x + f * 40 * s + 55 * s, y - 15 * s], fill=BLK)               # head
    d.polygon([P(85, -80), P(170, -58), P(85, -45)], fill=BLK)                                                         # beak
    d.polygon([P(-40, -20), P(40, -40), P(-60 - 80 * wing, -140 * wing - 10), P(-120, 0)], fill=G1)                    # wing
    d.line([P(-10, 45), P(-20, 110)], fill=BLK, width=int(8 * s) + 1); d.line([P(30, 40), P(25, 110)], fill=BLK, width=int(8 * s) + 1)
    if eye: ex, ey = P(60, -72); d.ellipse([ex - 10 * s, ey - 10 * s, ex + 10 * s, ey + 10 * s], fill=RED)

def caveman(d, cx, cy, s=1.0, upside=False, hat=False):
    def P(a, b): return (cx + a * s, cy + (-b if upside else b) * s)
    r = random.Random(2)
    hair = [P(140 * math.cos(a) + r.uniform(-25, 25), -170 * abs(math.sin(a)) - 40 + r.uniform(-25, 25)) for a in np.linspace(0, math.pi, 18)]
    d.polygon([P(-150, 40)] + hair + [P(150, 40)], fill=(120, 120, 124))
    d.ellipse([cx - 120 * s, cy - 150 * s, cx + 120 * s, cy + 160 * s], fill=G3)
    d.rectangle([min(P(-110, -40)[0], P(110, -60)[0]), min(P(-110, -40)[1], P(110, -60)[1]), max(P(-110, -40)[0], P(110, -60)[0]), max(P(-110, -40)[1], P(110, -60)[1])], fill=G1)  # heavy brow
    for ex in (-50, 50): a, b = P(ex, -10); d.ellipse([a - 22 * s, b - 14 * s, a + 22 * s, b + 14 * s], fill=BLK)
    a, b = P(0, 90); d.chord([a - 60 * s, b - 30 * s, a + 60 * s, b + 30 * s], 0 if not upside else 180, 180 if not upside else 360, fill=BLK)
    for tx in (-30, 0, 30): a, b = P(tx, 92); d.rectangle([a - 8 * s, min(b, b + (14 if not upside else -14) * s), a + 8 * s, max(b, b + (14 if not upside else -14) * s)], fill=WHT)
    if hat:
        hy = cy - 170 * s; d.rectangle([cx - 190 * s, hy, cx + 190 * s, hy + 26 * s], fill=(200, 200, 196)); d.rectangle([cx - 110 * s, hy - 130 * s, cx + 110 * s, hy + 4 * s], fill=(200, 200, 196)); d.rectangle([cx - 110 * s, hy - 30 * s, cx + 110 * s, hy - 6 * s], fill=RED)

def plainmask(d, cx, cy, s=1.0):
    d.ellipse([cx - 115 * s, cy - 150 * s, cx + 115 * s, cy + 160 * s], fill=WHT)
    for ex in (-45, 45): d.ellipse([cx + (ex - 20) * s, cy - 30 * s, cx + (ex + 20) * s, cy - 6 * s], fill=BLK)
    d.arc([cx - 50 * s, cy + 40 * s, cx + 50 * s, cy + 100 * s], 20, 160, fill=BLK, width=int(8 * s))

def title(d, s, y, size, col=WHT):
    while d.textlength(s, font=SERIF(size)) > W - 140: size -= 4
    d.text((W / 2, y), s, font=SERIF(size), fill=col, anchor="mm")
def tag(d, s, y):
    tw = d.textlength(s, font=Q(40)); d.rectangle([W / 2 - tw / 2 - 24, y - 34, W / 2 + tw / 2 + 24, y + 34], fill=WHT); d.text((W / 2, y), s, font=Q(40), fill=BLK, anchor="mm")
def stamp(img, s, cx, cy, size, rot=-10, u=1.0):
    if u <= 0: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); f = SERIF(size * (1.6 - 0.6 * min(1, u))); tw = d.textlength(s, font=f)
    d.rectangle([cx - tw / 2 - 30, cy - size * 0.8, cx + tw / 2 + 30, cy + size * 0.8], outline=RED + (235,), width=10); d.text((cx, cy), s, font=f, fill=RED + (235,), anchor="mm")
    lay = lay.rotate(rot, center=(cx, cy), resample=Image.BICUBIC); img.paste(lay, (0, 0), lay)

def base(col=G1):
    img = Image.new("RGB", (W, H), col); return img, ImageDraw.Draw(img)

def S_hook(sc, lt, dur, t):
    img, d = base((26, 26, 30)); rain(d, t)
    zoom = 1.0 + 0.04 * min(1, (t) / 3)
    d.ellipse([W / 2 - 430, 560, W / 2 + 430, 1420], fill=(150, 150, 150)); d.ellipse([W / 2 - 380, 610, W / 2 + 380, 1370], fill=(190, 190, 186))
    crow(d, W / 2 + 40, 1010, 3.0 * zoom, flip=False, wing=0.15 * math.sin(t * 2))
    out = post(img, t); d = ImageDraw.Draw(out)
    title(d, "CROWS REMEMBER", 330, 104); title(d, "YOUR FACE", 460, 130, RED)
    tag(d, "CASE FILE No. 39", 190)
    if sc.get("loop"): stamp(out, "FOR YEARS.", W / 2, 1470, 84, rot=-8, u=back(lt / 0.3))
    return out
def S_trap(sc, lt, dur, t):
    img, d = base((30, 30, 34)); rain(d, t, 40)
    caveman(d, W / 2, 880, 1.7)
    out = post(img, t); d = ImageDraw.Draw(out)
    tag(d, "SEATTLE · UNIVERSITY CAMPUS", 190); title(d, "THE CAVEMAN MASK", 330, 92)
    n = min(7, int(lt / 0.3))
    for k in range(7):
        x = 150 + k * 130; y = 1400
        d.rectangle([x - 50, y - 50, x + 50, y + 50], fill=G3 if k < n else None, outline=WHT if k < n else G2, width=4)
        if k < n: crow(d, x + 10, y + 10, 0.32, eye=False)
    if lt > 2.2: d.text((W / 2, 1520), "7 CROWS TRAPPED", font=Q(52), fill=RED, anchor="mm")
    return out
def S_lineup(sc, lt, dur, t):
    img, d = base((44, 44, 48))
    for k in range(9): y = 620 + k * 110; d.line([(60, y), (W - 60, y)], fill=G2, width=3); d.text((80, y - 30), f"{7 - k * 0.5:.1f}'", font=Q(28), fill=G3)
    caveman(d, 300, 1050, 1.15); plainmask(d, 780, 1050, 1.15)
    out = post(img, t, blinds=False); d = ImageDraw.Draw(out)
    tag(d, "THE LINEUP", 190); title(d, "WHO DO THEY HATE?", 330, 92)
    if lt > 0.6:
        for k in range(4):
            a = t * 3 + k * 1.6; crow(d, 300 + 260 * math.cos(a), 700 + 120 * math.sin(a * 1.3), 0.5, flip=math.sin(a) > 0, wing=abs(math.sin(t * 9 + k)))
        stamp(out, "CAW! CAW!", 300, 1380, 70, rot=-8, u=back((lt - 0.6) / 0.3))
    if lt > 2.4: d.text((780, 1400), "ignored.", font=SERIF(70), fill=G3, anchor="mm")
    return out
def S_disguise(sc, lt, dur, t):
    img, d = base((30, 30, 34)); rain(d, t, 50)
    flip = lt > 1.4; hat = lt > 0.3
    caveman(d, W / 2, 980, 1.5, upside=flip, hat=hat and not flip)
    out = post(img, t); d = ImageDraw.Draw(out)
    tag(d, "DISGUISE ATTEMPT", 190); title(d, "UPSIDE DOWN" if flip else "WITH A HAT", 330, 100)
    crow(d, 880, 1420, 0.8, flip=True)
    if lt > 2.0: stamp(out, "STILL RECOGNISED", W / 2, 1560, 62, rot=-6, u=back((lt - 2.0) / 0.3))
    return out
def S_mob(sc, lt, dur, t):
    img, d = base((24, 24, 28)); rain(d, t, 60)
    caveman(d, W / 2, 1150, 1.1)
    out = post(img, t); d = ImageDraw.Draw(out)
    tag(d, "NEVER CAUGHT. STILL ANGRY.", 190); title(d, "THEY TAUGHT", 330, 110); title(d, "EACH OTHER", 460, 110, RED)
    n = min(26, 2 + int(lt * 5)); r = random.Random(8)
    for k in range(n):
        a = r.uniform(0, 2 * math.pi); rad = r.uniform(300, 480); sp = r.uniform(0.6, 1.4)
        x = W / 2 + rad * math.cos(a + t * sp * 0.5); y = 1000 + rad * 0.8 * math.sin(a + t * sp * 0.5)
        crow(d, x, y, r.uniform(0.3, 0.55), flip=math.cos(a + t * sp * 0.5) < 0, wing=abs(math.sin(t * 10 + k)))
    if lt > 3.0: d.text((W / 2, 1530), "the grudge lasted years", font=Q(52), fill=WHT, anchor="mm")
    return out
def S_end(sc, lt, dur, t):
    img, d = base((26, 26, 30)); rain(d, t, 40); d.ellipse([W / 2 - 330, 880, W / 2 + 330, 1500], fill=(170, 170, 166)); crow(d, W / 2, 1220, 1.6, wing=0.1)
    out = post(img, t); d = ImageDraw.Draw(out)
    title(d, "SOUNDS FAKE ?!", 340, 120)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.2); cx, cy, w_, h_ = W / 2, 620, 330, 150
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=RED if on > 0.5 else G2, outline=WHT, width=5)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; d.ellipse([kx - h_ / 2 + 18, cy - h_ / 2 + 18, kx + h_ / 2 - 18, cy + h_ / 2 - 18], fill=WHT)
    d.text((cx - w_ / 2 - 30, cy), "FAKE", font=SERIF(64), fill=WHT if on < 0.5 else G2, anchor="rm"); d.text((cx + w_ / 2 + 30, cy), "TRUE", font=SERIF(64), fill=RED if on >= 0.5 else G2, anchor="lm")
    return out
SCENES = dict(hook=S_hook, trap=S_trap, lineup=S_lineup, disguise=S_disguise, mob=S_mob, end=S_end)

voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
walk = [55.0, 65.41, 73.42, 77.78, 82.41, 77.78, 73.42, 65.41]                     # walking upright bass (blues)
for k in range(int(total / 0.42)):
    place(music, k * 0.42, tone(walk[k % 8], 0.45, decay=5, harm=(1, 2, 3)), 0.09)
    if k % 2 == 1: place(music, k * 0.42, (np.random.default_rng(k).normal(0, 1, int(0.12 * SR)) * np.exp(-np.linspace(0, 6, int(0.12 * SR)))).astype(np.float32), 0.012)  # brush
    if k % 8 == 0: place(music, k * 0.42, sum(tone(f, 2.5, decay=1.2, harm=(1, 2, 3)) for f in (220.0, 261.63, 311.13, 392.0)), 0.012)  # muted horn chord
rr = np.random.default_rng(3).normal(0, 1, n).astype(np.float32); k_ = np.ones(40, np.float32) / 40; music += np.convolve(rr, k_, "same") * 0.01  # rain hiss
hook_hit(music, 0.35)
for s_ in scene_starts(spec): whoosh(music, s_, 0.08)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.3)

groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 70
    while d.textlength(" ".join(ws), font=Q(size)) > W - 200 and size > 36: size -= 4
    f = Q(size); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1660
    d.rectangle([x - 30, y - 14, x + tw + 30, y + size + 30], fill=WHT)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=RED if on else BLK); x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t); caption(img, t)
    ImageDraw.Draw(img).rectangle([0, H - 10, int(W * t / total), H], fill=RED); return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
