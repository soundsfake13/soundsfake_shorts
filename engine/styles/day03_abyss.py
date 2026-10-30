"""Day 03 — ABYSS GLOW style (immortal jellyfish).
Deep-sea bioluminescence: near-black water, drifting marine snow, faint light shafts, translucent glowing
jellyfish with a red core, additive light + bloom, thin rounded type that glows, a VHS 'rewind' when the
jellyfish turns back into a polyp. Usage: python3 engine/styles/day03_abyss.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
rng = np.random.default_rng(3); random.seed(3)
def QS(size, wt=600):
    f = ImageFont.truetype(f"{FONTS}/Quicksand.ttf", size); f.set_variation_by_axes([wt]); return f
CYAN, MAG, CORE, WHITE, DIM = (90, 230, 255), (255, 90, 200), (255, 90, 60), (235, 245, 255), (120, 150, 190)

# ---------------- water ----------------
yy = np.linspace(0, 1, H)[:, None, None]
BG = (np.array([4, 18, 40], np.float32) * (1 - yy) ** 1.4 + np.array([0, 2, 8], np.float32)).repeat(W, 1)
shafts = Image.new("L", (W, H), 0); sd = ImageDraw.Draw(shafts)
for x0 in (160, 430, 700, 940):
    sd.polygon([(x0 - 30, 0), (x0 + 50, 0), (x0 - 120, H * 0.7), (x0 - 330, H * 0.7)], fill=22)
BG += (np.asarray(shafts.filter(ImageFilter.GaussianBlur(50))).astype(np.float32) / 255)[..., None] * np.array([60, 140, 200], np.float32)
SNOW = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1, 3.5), rng.uniform(6, 26), rng.uniform(0, 6.3)) for _ in range(260)]

def bloom(light, k=1.1, r=10):
    small = Image.fromarray(np.clip(light, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    b = small.filter(ImageFilter.GaussianBlur(r)).resize((W, H), Image.BILINEAR)
    return light + np.asarray(b).astype(np.float32) * k

# ---------------- glowing drawings (on an RGB 'light' canvas) ----------------
def jelly(d, x, y, s=1.0, t=0.0, a=1.0, core=True):
    pulse = math.sin(t * 3.0)
    bw, bh = 150 * s * (1 + 0.07 * pulse), 120 * s * (1 - 0.06 * pulse)
    c = lambda col, k=1.0: tuple(int(v * a * k) for v in col)
    for k in range(14):                                         # tentacles
        x0 = x - bw * 0.9 + k * bw * 1.8 / 13
        pts = [(x0 + 14 * s * math.sin(t * 2.2 + j * 0.45 + k) * (j / 20), y + j * 16 * s) for j in range(21)]
        d.line(pts, fill=c(CYAN, 0.45), width=max(1, int(3 * s)))
    for k in range(4):                                          # oral arms
        x0 = x - 30 * s + k * 20 * s
        pts = [(x0 + 10 * s * math.sin(t * 1.6 + j * 0.5 + k), y + 10 * s + j * 12 * s) for j in range(12)]
        d.line(pts, fill=c(MAG, 0.6), width=max(2, int(6 * s)))
    d.pieslice([x - bw, y - bh, x + bw, y + bh * 0.35], 180, 360, fill=c((20, 70, 110)))   # translucent bell
    d.arc([x - bw, y - bh, x + bw, y + bh * 0.35], 180, 360, fill=c(CYAN), width=max(2, int(6 * s)))
    d.line([(x - bw, y - bh * 0.32), (x + bw, y - bh * 0.32)], fill=c(CYAN, 0.8), width=max(2, int(4 * s)))
    if core:
        d.ellipse([x - 38 * s, y - bh * 0.75, x + 38 * s, y - bh * 0.15], fill=c(CORE))  # red core (its stomach)

def polyp(d, x, y, s=1.0, grow=1.0, t=0.0, a=1.0):
    c = lambda col, k=1.0: tuple(int(v * a * k) for v in col)
    h = 260 * s * grow
    d.line([(x, y), (x + 10 * math.sin(t), y - h)], fill=c(CYAN, 0.9), width=max(2, int(8 * s)))
    for k, (bx, by) in enumerate(((-70, 0.45), (60, 0.65), (-40, 0.85))):
        if grow < by: continue
        px, py = x + bx * s * min(1, (grow - by) * 4), y - h * by
        d.line([(x + 10 * math.sin(t) * by, py), (px, py - 40 * s)], fill=c(CYAN, 0.7), width=max(2, int(5 * s)))
        d.ellipse([px - 16 * s, py - 56 * s, px + 16 * s, py - 24 * s], fill=c(MAG, 0.8))
    d.ellipse([x - 22 * s + 10 * math.sin(t), y - h - 24 * s, x + 22 * s + 10 * math.sin(t), y - h + 14 * s], fill=c(MAG))
    d.ellipse([x - 60 * s, y - 8, x + 60 * s, y + 14], fill=c((40, 90, 120)))   # holdfast on the seabed

_tx = {}
def gtext(light, txt, size, col, cx, cy, a=1.0, wt=600):
    key = (txt, size, col, wt)
    if key not in _tx:
        f = QS(size, wt); d0 = ImageDraw.Draw(Image.new("L", (4, 4))); tw = int(d0.textlength(txt, font=f))
        m = Image.new("L", (tw + 40, int(size * 1.4) + 20), 0); ImageDraw.Draw(m).text((20, 10), txt, font=f, fill=255)
        _tx[key] = np.asarray(m).astype(np.float32) / 255
    m = _tx[key]; h, w = m.shape; x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xs, ys, xe, ye = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xe > xs and ye > ys:
        light[ys:ye, xs:xe] += m[ys - y0:ye - y0, xs - x0:xe - x0, None] * np.array(col, np.float32) * a

def fit(txt, size, maxw=W - 120, wt=600):
    d0 = ImageDraw.Draw(Image.new("L", (4, 4)))
    while d0.textlength(txt, font=QS(size, wt)) > maxw and size > 36: size -= 4
    return size

def titles(light, lines, lt, y0=330, size=104, accent=None):
    for i, txt in enumerate(lines):
        u = ease((lt - 0.1 - i * 0.4) / 0.7)
        if u <= 0: continue
        col = MAG if accent and str(i) in accent else WHITE
        gtext(light, txt, fit(txt, size), col, W / 2, y0 + i * size * 1.25 + (1 - u) * 24, a=u, wt=700)

# ---------------- narration & music ----------------
voice, words, total = narrate(spec, default_gap=0.32)
n = len(voice); tt = np.arange(n) / SR; music = np.zeros(n, np.float32)
music += 0.045 * np.sin(2 * np.pi * 49 * tt) * (0.6 + 0.4 * np.sin(2 * np.pi * tt / 8))
music += 0.02 * np.sin(2 * np.pi * 73.4 * tt + 0.5 * np.sin(2 * np.pi * tt / 5))
for k in range(int(total / 3.2) + 1):                        # sonar ping + echo
    for e, g in ((0, 0.05), (0.42, 0.02), (0.84, 0.008)):
        place(music, k * 3.2 + 0.4 + e, tone(1046.5, 1.8, decay=2.2, harm=(1,)), g)
for k in range(int(total * 1.5)):                            # bubbles: tiny rising chirps
    at = random.uniform(0, total); bl = np.arange(int(0.07 * SR)) / SR
    place(music, at, np.sin(2 * np.pi * (500 + 2600 * bl / 0.07) * bl) * np.exp(-bl * 40), 0.012)
for k in range(int(total / 4) + 1):                          # soft pad
    a_, b_ = int(k * 4 * SR), min(int((k * 4 + 5.5) * SR), n)
    if a_ >= n: break
    lt = tt[a_:b_] - k * 4; env = np.clip(lt / 2, 0, 1) * np.clip((5.5 - lt) / 2, 0, 1)
    for f in ([196, 293.66, 392], [174.61, 261.63, 349.23], [164.81, 246.94, 329.63], [174.61, 261.63, 392])[k % 4]:
        music[a_:b_] += np.sin(2 * np.pi * f * lt) * env * 0.018
write_audio(voice, music, work + "_audio.wav", music_gain=0.65, duck=0.3)

# ---------------- scenes: each draws on an RGB light canvas and returns it ----------------
def canvas(): img = Image.new("RGB", (W, H), (0, 0, 0)); return img, ImageDraw.Draw(img)
def as_light(img): return np.asarray(img).astype(np.float32)

def sc_hook(sc, lt, dur, t):
    img, d = canvas(); jelly(d, W / 2, 1150 - 60 * ease(lt / dur), 1.7, t, a=ease(lt / 0.6))
    L = as_light(img); titles(L, sc["lines"], lt, accent=sc.get("accent")); return L

def sc_words(sc, lt, dur, t):
    img, d = canvas(); jelly(d, W / 2, 1300, 0.8, t, a=0.35)
    L = as_light(img); titles(L, sc["lines"], lt, y0=sc.get("y", 640), size=sc.get("size", 130), accent=sc.get("accent")); return L

def sc_size(sc, lt, dur, t):
    img, d = canvas(); s = 1.6 - 1.25 * ease((lt - 0.3) / 1.2)
    jelly(d, W / 2, 900 + 120 * (1.6 - s), s, t)
    u = ease((lt - 1.0) / 0.6)
    if u > 0:
        y = 1260; x0, x1 = 160, W - 160; c = tuple(int(v * u) for v in CYAN)
        d.line([(x0, y), (x1, y)], fill=c, width=4)
        for mm in range(11):
            x = x0 + (x1 - x0) * mm / 10; d.line([(x, y), (x, y - (40 if mm % 5 == 0 else 22))], fill=c, width=4)
        xa, xb = W / 2 - (x1 - x0) * 0.225, W / 2 + (x1 - x0) * 0.225
        d.line([(xa, y + 40), (xb, y + 40)], fill=tuple(int(v * u) for v in MAG), width=6)
    L = as_light(img)
    if u > 0: gtext(L, "≈ 4.5 mm", 92, MAG, W / 2, 1380, a=u, wt=700); gtext(L, "(ruler: 10 mm)", 40, DIM, W / 2, 1200, a=u)
    return L

def sc_life(sc, lt, dur, t):
    img, d = canvas()
    stages = [("BABY", 0.0), ("ADULT", 0.9), ("OLD", 1.8)]
    for i, (lab, at) in enumerate(stages):
        u = ease((lt - at) / 0.5)
        if u <= 0: continue
        x = 220 + i * 320; fade = 1.0 if i < 2 else max(0.15, 1 - ease((lt - 2.6) / 1.2))
        jelly(d, x, 950, [0.35, 0.8, 0.8][i], t + i, a=u * fade * (0.55 if i == 2 else 1), core=i < 2)
    L = as_light(img)
    for i, (lab, at) in enumerate(stages):
        u = ease((lt - at) / 0.5)
        if u > 0: gtext(L, lab, 54, DIM, 220 + i * 320, 1240, a=u, wt=700)
    if lt > 2.8: gtext(L, "...THE END", 80, DIM, W / 2, 520, a=ease((lt - 2.8) / 0.6), wt=500)
    return L

def sc_rewind(sc, lt, dur, t):
    img, d = canvas(); p = ease((lt - 0.4) / max(1.0, dur - 1.0))
    if p < 0.6:
        q = p / 0.6; jelly(d, W / 2, 900 + 420 * q, 1.3 * (1 - 0.8 * q), -t * 3, a=1.0 - 0.3 * q)
    else:
        q = (p - 0.6) / 0.4
        d.ellipse([W / 2 - 40, 1330 - 40, W / 2 + 40, 1330 + 40], fill=tuple(int(v * (1 - q)) for v in MAG))
        polyp(d, W / 2, 1360, 1.2, grow=q, t=t)
    L = as_light(img)
    if int(lt * 3) % 2 == 0: gtext(L, "<< REWIND", 64, WHITE, 230, 260, wt=700)
    if p > 0.85: gtext(L, "POLYP", 80, MAG, W / 2, 520, a=ease((p - 0.85) / 0.15), wt=700)
    return L

def sc_regrow(sc, lt, dur, t):
    img, d = canvas(); polyp(d, W / 2, 1360, 1.2, 1.0, t)
    for k in range(3):
        u = ease((lt - 0.3 - k * 0.5) / 1.6)
        if u <= 0: continue
        jelly(d, W / 2 + (k - 1) * 260 * u, 1100 - 520 * u, 0.25 + 0.6 * u, t + k)
    L = as_light(img); gtext(L, "PLAY >", 64, WHITE, 200, 260, wt=700); return L

def sc_forever(sc, lt, dur, t):
    img, d = canvas(); cx, cy, A = W / 2, 900, 380
    pts = [(cx + A * math.cos(a) / (1 + math.sin(a) ** 2), cy + A * math.sin(a) * math.cos(a) / (1 + math.sin(a) ** 2) * 1.4)
           for a in np.linspace(0, 2 * math.pi, 240)]
    k = int(len(pts) * ease(lt / 1.2))
    if k > 2: d.line(pts[:k], fill=CYAN, width=8)
    ph = (lt * 0.25) % 1; jx, jy = pts[int(ph * 239)]
    jelly(d, jx, jy - 40, 0.45, t)
    return as_light(img)

def sc_danger(sc, lt, dur, t):
    img, d = canvas(); dim = 1 - 0.6 * ease((lt - 0.8) / 0.8)
    jelly(d, W / 2, 950, 1.0, t, a=dim)
    L = as_light(img)
    fx = W + 500 - (W + 1200) * ease((lt - 0.3) / max(1.2, dur - 0.4))      # big dark fish silhouette
    fish = Image.new("L", (W, H), 0); fd = ImageDraw.Draw(fish)
    fd.ellipse([fx - 420, 700, fx + 300, 1120], fill=255); fd.polygon([(fx + 260, 910), (fx + 520, 720), (fx + 520, 1100)], fill=255)
    fm = np.asarray(fish.filter(ImageFilter.GaussianBlur(6))).astype(np.float32)[..., None] / 255
    L *= (1 - 0.92 * fm)
    rim = Image.new("L", (W, H), 0); rd = ImageDraw.Draw(rim)
    rd.arc([fx - 420, 700, fx + 300, 1120], 190, 350, fill=255, width=5); rd.line([(fx + 520, 720), (fx + 520, 1100)], fill=255, width=4)
    L += (np.asarray(rim.filter(ImageFilter.GaussianBlur(3))).astype(np.float32) / 255)[..., None] * np.array([60, 120, 170], np.float32)
    if lt > 0.6: gtext(L, "BUT...", 110, WHITE, W / 2, 420, a=ease((lt - 0.6) / 0.4), wt=700)
    return L

def sc_end(sc, lt, dur, t):
    img, d = canvas(); click = sc.get("click_at", 0.9); on = ease((lt - click) / 0.25)
    cx, cy, w_, h_ = W / 2, 980, 330, 150; col = MAG if on > 0.5 else CYAN
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, outline=col, width=8)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on
    d.ellipse([kx - h_ / 2 + 22, cy - h_ / 2 + 22, kx + h_ / 2 - 22, cy + h_ / 2 - 22], fill=col)
    jelly(d, W / 2, 1380, 0.5, t, a=0.6)
    L = as_light(img)
    gtext(L, "FAKE", 64, WHITE if on < 0.5 else DIM, cx - w_ / 2 - 130, cy, wt=700)
    gtext(L, "TRUE", 64, MAG if on >= 0.5 else DIM, cx + w_ / 2 + 130, cy, wt=700)
    if lt > click + 0.3: gtext(L, "SOUNDS FAKE ?!", 104, WHITE, W / 2, 620, a=ease((lt - click - 0.3) / 0.4), wt=700)
    return L

SCENES = dict(hook=sc_hook, words=sc_words, size=sc_size, life=sc_life, rewind=sc_rewind, regrow=sc_regrow,
              forever=sc_forever, danger=sc_danger, end=sc_end)

# ---------------- captions ----------------
groups = caption_groups(words, 3)
def caption(arr, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    arr[1555:1720] *= 0.4
    ws = [words[i][0] for i in g]; size = fit(" ".join(ws), 68, W - 160, 700)
    d0 = ImageDraw.Draw(Image.new("L", (4, 4))); f = QS(size, 700)
    x = (W - d0.textlength(" ".join(ws), font=f)) / 2
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05; ww = d0.textlength(w, font=f)
        gtext(arr, w, size, CYAN if on else WHITE, x + ww / 2, 1638, wt=700)
        x += d0.textlength(w + " ", font=f)

def frame(t, fi):
    arr = BG.copy()
    for (x, y, r, sp, ph) in SNOW:                                   # marine snow drifting down
        py = (y + sp * t) % H; px = x + 10 * math.sin(t * 0.7 + ph)
        arr[int(py):int(py) + int(r) + 1, int(px):int(px) + int(r) + 1] += 70
    ln = active_line(spec, t)
    if ln is not None:
        lt = t - ln["_s"]; dur = ln["_se"] - ln["_s"]; sc = ln["scene"]
        light = SCENES[sc["type"]](sc, lt, dur, t)
        if lt < 0.3: light = light * ease((lt + 0.1) / 0.4)
        arr = arr + bloom(light)
        if sc["type"] == "rewind" and lt < dur - 0.2:                  # VHS tracking bands while rewinding
            for k in range(3):
                y0 = int((t * 900 + k * 640) % H); arr[y0:y0 + 26] = np.roll(arr[y0:y0 + 26], 40, axis=1) * 0.7 + 50
    caption(arr, t)
    arr[H - 8:, :int(W * t / total)] = np.array(CYAN)
    return np.clip(arr, 0, 255).astype(np.uint8).tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","):
            Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path)
        print(f"done {total:.1f}s")
