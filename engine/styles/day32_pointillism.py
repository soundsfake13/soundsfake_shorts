"""Day 32 — POINTILLISM style (more trees on Earth than stars in the Milky Way).
Seurat-like dots on warm paper: ~3000 dots morph between pictures (starry sky + forest, a spiral galaxy, a dense
forest, a person among trees, a 'twice as many' ghost forest). Frame 0 is the full hook (no fade), impact at t=0,
whoosh on every morph. Usage: python3 engine/styles/day32_pointillism.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
rng = np.random.default_rng(32); random.seed(32)
def PF(size, wt=900):
    f = ImageFont.truetype(f"{FONTS}/PlayfairDisplay.ttf", size); f.set_variation_by_axes([wt]); return f
PAPER, NAVY, CREAM, GOLD, LEAF, INKC = (246, 240, 226), (22, 30, 64), (250, 244, 228), (246, 196, 72), (40, 140, 70), (24, 28, 44)
N = 3000
GREENS = np.array([(40, 140, 70), (70, 170, 80), (30, 110, 60), (120, 180, 70), (20, 90, 55), (90, 150, 60)], np.float32)
STARC = np.array([(255, 255, 255), (255, 236, 170), (190, 215, 255), (255, 210, 120)], np.float32)
PAPER_TEX = (np.random.default_rng(1).normal(0, 4, (H, W, 1))).astype(np.float32)

# ---------------- dot pictures: each returns (pos Nx2, col Nx3, size N) ----------------
def tree_points(cx, base, h, n, r):
    pts, cols = [], []
    for _ in range(n):
        if r.random() < 0.12:                                     # trunk
            pts.append((cx + r.uniform(-h * 0.05, h * 0.05), base - r.uniform(0, h * 0.3))); cols.append((110, 70, 40))
        else:                                                     # canopy: stacked cone
            v = r.random() ** 0.8; y = base - h * 0.25 - v * h * 0.75; half = (1 - v) * h * 0.38
            pts.append((cx + r.uniform(-half, half), y)); cols.append(tuple(GREENS[r.randrange(6)]))
    return pts, cols

def forest(n, y0, y1, ntrees, seed, xmin=60, xmax=W - 60):
    r = random.Random(seed); pts, cols = [], []
    trees = sorted([(r.uniform(xmin, xmax), r.uniform(y0, y1), r.uniform(220, 380)) for _ in range(ntrees)], key=lambda t: t[1])
    per = n // ntrees
    for (cx, base, h) in trees:
        p, c = tree_points(cx, base, h * (0.6 + 0.6 * (base - y0) / max(1, y1 - y0)), per, r); pts += p; cols += c
    while len(pts) < n: pts.append(pts[r.randrange(len(pts))]); cols.append(cols[r.randrange(len(cols))])
    return pts[:n], cols[:n]

def sky(n, y0, y1, seed):
    r = random.Random(seed)
    return [(r.uniform(30, W - 30), r.uniform(y0, y1)) for _ in range(n)], [tuple(STARC[r.randrange(4)]) for _ in range(n)]

def pack(pts, cols, size=7.0, jitter=0.0):
    p = np.array(pts, np.float32); c = np.array(cols, np.float32)
    s = np.full(len(p), size, np.float32) * (0.7 + 0.6 * rng.random(len(p)))
    return p, c, s

def T_hook():
    sp, sc = sky(1300, 330, 900, 1); fp, fc = forest(1700, 1180, 1500, 11, 2)
    return pack(sp + fp, sc + fc)

def T_galaxy():
    r = random.Random(3); pts, cols = [], []
    for k in range(N):
        arm = k % 2; t = r.random() ** 0.7 * 3.4
        a = t * 1.9 + arm * math.pi + r.gauss(0, 0.28); rad = 40 + t * 120
        pts.append((540 + rad * math.cos(a) + r.gauss(0, 14), 930 + rad * math.sin(a) * 0.82 + r.gauss(0, 14)))
        cols.append(tuple(STARC[r.randrange(4)]) if t > 0.5 else (255, 235, 180))
    return pack(pts, cols, 6.0)

def T_forest():
    fp, fc = forest(N, 700, 1480, 26, 4); return pack(fp, fc, 7.5)

def T_person():
    r = random.Random(5); pts, cols = [], []
    for _ in range(260):                                          # a person in the middle, drawn in navy dots
        part = r.random()
        if part < 0.25: a = r.uniform(0, 2 * math.pi); rr = 50 * math.sqrt(r.random()); pts.append((540 + rr * math.cos(a), 900 + rr * math.sin(a)))
        else: pts.append((540 + r.uniform(-45, 45) * (1 - (part - 0.25)), 980 + (part - 0.25) * 300))
        cols.append(NAVY)
    n_trees = N - len(pts); k = 0
    while len(pts) < N:                                           # a ring of little trees around them
        a = k * 2.399 ; rad = 260 + (k % 7) * 60; k += 1
        p, c = tree_points(540 + rad * math.cos(a), 960 + rad * math.sin(a) * 1.15, 110, 14, r); pts += p; cols += c
    return pack(pts[:N], cols[:N], 6.0)

def T_twist():
    fp, fc = forest(N // 2, 1100, 1480, 14, 6)                    # today's forest
    gp, gc = forest(N - N // 2, 760, 1060, 14, 7)                 # the 'missing' forest, drawn pale
    gc = [tuple(int(v * 0.35 + 246 * 0.65) for v in c) for c in gc]
    return pack(fp + gp, fc + gc, 7.0)

def T_end():
    r = random.Random(8); pts, cols = [], []
    for k in range(N):
        a = r.uniform(0, 2 * math.pi); rad = 480 + r.uniform(0, 520)
        pts.append((540 + rad * math.cos(a), 960 + rad * math.sin(a) * 1.6)); cols.append(tuple(GREENS[r.randrange(6)]) if k % 3 else (246, 196, 72))
    return pack(pts, cols, 6.0)

PICS = dict(hook=T_hook, loop=T_hook, galaxy=T_galaxy, forest=T_forest, person=T_person, twist=T_twist, end=T_end)
_cache = {}
def pic(name):
    if name not in _cache: _cache[name] = PICS[name]()
    return _cache[name]
BG = dict(hook="split", loop="split", galaxy="night", forest="paper", person="paper", twist="paper", end="night")

# ---------------- narration & music ----------------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.22, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
notes = [523.25, 659.25, 783.99, 659.25, 587.33, 698.46, 880.0, 698.46]
for k in range(int(total / 0.25)):                                 # light plucked pattern, like dots of sound
    place(music, k * 0.25, tone(notes[k % 8] * (0.5 if k % 4 == 0 else 1), 0.4, decay=10, harm=(1, 3)), 0.04)
    if k % 8 == 0: place(music, k * 0.25, tone(130.81 if (k // 8) % 2 == 0 else 110.0, 1.6, decay=2.5, harm=(1, 2)), 0.08)
hook_hit(music, 0.4)
for s_ in scene_starts(spec): whoosh(music, s_, 0.16)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.3)

# ---------------- drawing ----------------
def background(kind, mix=1.0, prev=None):
    def one(k):
        a = np.empty((H, W, 3), np.float32)
        if k == "night": a[:] = NAVY
        elif k == "paper": a[:] = PAPER
        else: a[:] = PAPER; a[:960] = NAVY
        return a
    a = one(kind)
    if prev is not None and prev != kind and mix < 1: a = one(prev) * (1 - mix) + a * mix
    return a + PAPER_TEX

def draw_dots(img, p, c, s, t, shimmer=1.0):
    d = ImageDraw.Draw(img); ph = np.arange(len(p)) * 0.37
    jx = np.sin(t * 3.1 + ph) * 1.6 * shimmer; jy = np.cos(t * 2.7 + ph) * 1.6 * shimmer
    for (x, y), col, r, dx, dy in zip(p, c, s, jx, jy):
        d.ellipse([x + dx - r, y + dy - r, x + dx + r, y + dy + r], fill=(int(col[0]), int(col[1]), int(col[2])))

def text(img, txt, size, cx, cy, col, u=1.0, shadow=None, wt=900):
    if u <= 0: return
    d = ImageDraw.Draw(img); sz = size
    while d.textlength(txt, font=PF(sz, wt)) > W - 100 and sz > 40: sz -= 4
    f = PF(sz, wt); y = cy + (1 - u) * 30
    if shadow: d.text((cx + 5, y + 6), txt, font=f, fill=shadow, anchor="mm")
    d.text((cx, y), txt, font=f, fill=col, anchor="mm")

def pill(img, txt, size, cx, cy, fill=CREAM, ink=INKC, u=1.0):
    if u <= 0: return
    d = ImageDraw.Draw(img); f = PF(size, 800); tw = d.textlength(txt, font=f); y = cy + (1 - u) * 20
    d.rounded_rectangle([cx - tw / 2 - 34, y - size * 0.75, cx + tw / 2 + 34, y + size * 0.75], int(size * 0.75), fill=fill)
    d.text((cx, y), txt, font=f, fill=ink, anchor="mm")

def overlay(img, name, sc, lt, dur, t):
    if name in ("hook", "loop"):                                   # frame 0: the whole claim, big, already there
        plate = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(plate).rounded_rectangle([50, 360, W - 50, 750], 50, fill=NAVY + (235,))
        img.paste(Image.alpha_composite(img.convert("RGBA"), plate).convert("RGB"))
        text(img, "MORE TREES", 150, W / 2, 470, CREAM, shadow=(0, 0, 0))
        text(img, "THAN STARS", 150, W / 2, 640, GOLD, shadow=(0, 0, 0))
        if name == "hook": pill(img, "EARTH vs OUR GALAXY", 44, W / 2, 1040)
        else: pill(img, sc.get("label", "THAT'S NOT EVEN THE WEIRD PART"), 48, W / 2, 1040, fill=GOLD, ink=INKC, u=back(lt / 0.3))
    elif name == "galaxy":
        v = 100 + 300 * ease((lt - 0.4) / 1.2)
        text(img, f"{int(v)} BILLION", 120, W / 2, 360, CREAM, u=ease(lt / 0.3), shadow=(0, 0, 0))
        pill(img, "STARS IN THE MILKY WAY", 46, W / 2, 1520 - 40, u=ease((lt - 0.2) / 0.3))
        if lt > 1.6: text(img, "(100–400 billion)", 46, W / 2, 470, (200, 210, 240), wt=500)
    elif name == "forest":
        v = 3.0 * ease((lt - 0.3) / 1.0)
        text(img, f"{v:.1f} TRILLION" if v < 2.95 else "3 TRILLION", 130, W / 2, 400, LEAF, u=ease(lt / 0.3))
        pill(img, "TREES ON EARTH", 50, W / 2, 560, fill=LEAF, ink=CREAM, u=ease((lt - 0.2) / 0.3))
    elif name == "person":
        v = int(422 * ease((lt - 0.3) / 1.4))
        text(img, str(v), 200, W / 2, 380, LEAF, u=ease(lt / 0.3))
        pill(img, "TREES FOR EVERY PERSON", 46, W / 2, 1480, u=ease((lt - 0.2) / 0.3))
    elif name == "twist":
        text(img, "ALMOST 2×", 150, W / 2, 380, NAVY, u=back((lt - 0.3) / 0.35))
        pill(img, "BEFORE FARMING BEGAN", 46, W / 2, 520, fill=NAVY, ink=CREAM, u=ease((lt - 0.5) / 0.3))
        pill(img, "PALE TREES = THE ONES WE'VE LOST", 40, W / 2, 640, fill=(225, 220, 205), ink=INKC, u=ease((lt - 1.0) / 0.3))
    elif name == "end":
        d = ImageDraw.Draw(img); click = sc.get("click_at", 0.5); on = ease((lt - click) / 0.2)
        cx, cy, w_, h_ = W / 2, 960, 330, 150
        d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=LEAF if on > 0.5 else (60, 66, 96), outline=CREAM, width=8)
        kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on
        for k in range(18):                                         # the knob is made of dots too
            a = k * 2.399; rr = 46 * math.sqrt((k + 0.5) / 18)
            d.ellipse([kx + rr * math.cos(a) - 9, cy + rr * math.sin(a) - 9, kx + rr * math.cos(a) + 9, cy + rr * math.sin(a) + 9], fill=CREAM)
        text(img, "FAKE", 66, cx - w_ / 2 - 130, cy, CREAM if on < 0.5 else (120, 126, 150), wt=800)
        text(img, "TRUE", 66, cx + w_ / 2 + 130, cy, GOLD if on >= 0.5 else (120, 126, 150), wt=800)
        if lt > click + 0.2: text(img, "Sounds Fake ?!", 120, W / 2, 640, GOLD, u=ease((lt - click - 0.2) / 0.3), shadow=(0, 0, 0))

# ---------------- captions ----------------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 66
    while d.textlength(" ".join(ws), font=PF(size, 800)) > W - 200 and size > 40: size -= 4
    f = PF(size, 800); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1620
    d.rounded_rectangle([x - 36, y - 20, x + tw + 36, y + size + 34], 40, fill=CREAM, outline=INKC, width=4)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=LEAF if on else INKC)
        x += d.textlength(w + " ", font=f)

# ---------------- render loop with dot morphing ----------------
lines = spec["lines"]
def frame(t, fi):
    idx = 0
    for i, ln in enumerate(lines):
        if ln["_s"] - 0.05 <= t: idx = i
    ln = lines[idx]; name = ln["scene"]["type"]; lt = t - ln["_s"]; dur = ln["_se"] - ln["_s"]
    p1, c1, s1 = pic(name)
    prev = lines[idx - 1]["scene"]["type"] if idx > 0 else None
    m = 1.0 if prev is None else eout(lt / 0.55)                    # frame 0: already fully formed
    if prev is not None and m < 1:
        p0, c0, s0 = pic(prev)
        swirl = np.sin(np.arange(N) * 0.7)[:, None] * 120 * math.sin(math.pi * m)
        p = p0 * (1 - m) + p1 * m + swirl * np.array([[1, 0.4]]); c = c0 * (1 - m) + c1 * m; s = s0 * (1 - m) + s1 * m
    else:
        p, c, s = p1, c1, s1
    arr = background(BG[name], mix=m, prev=BG.get(prev))
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    draw_dots(img, p, c, s, t)
    overlay(img, name, ln["scene"], lt, dur, t)
    caption(img, t)
    ImageDraw.Draw(img).rectangle([0, H - 10, int(W * t / total), H], fill=GOLD)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","):
            Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path)
        print(f"done {total:.1f}s")
