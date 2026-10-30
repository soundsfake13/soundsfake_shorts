"""Cinematic B&W 'ink & grain' YouTube Short renderer.

Look: black & white, film grain, fog, silhouettes, type that forms from ink blots.
Usage: python3 ink_short.py spec.json out.mp4
"""
import json, math, os, random, subprocess, sys
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from kokoro_onnx import Kokoro

W, H, FPS, SR = 1080, 1920, 30, 24000
SERIF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "DMSerifDisplay-Regular.ttf")
F = lambda s: ImageFont.truetype(SERIF, s)
rng = np.random.default_rng(11); random.seed(11)

spec = json.load(open(sys.argv[1]))
out_path = sys.argv[2]
work = out_path.rsplit(".", 1)[0]

# ================= narration =================
KD = os.path.expanduser(os.environ.get("KOKORO_DIR", "~/.cache/kokoro"))
tts = Kokoro(os.path.join(KD, "kokoro.onnx"), os.path.join(KD, "voices.bin"))
t, parts, words = 0.6, [np.zeros(int(SR * 0.6), np.float32)], []
for si, ln in enumerate(spec["lines"]):
    s, _ = tts.create(ln["text"], voice=spec.get("voice", "am_michael"), speed=spec.get("speed", 1.0), lang="en-us")
    nz = np.where(np.abs(s) > 0.01)[0]
    s = s[max(nz[0] - 600, 0): nz[-1] + 1200]
    dur = len(s) / SR
    toks = ln.get("caption", ln["text"]).split()
    wts = [len(w.strip(".,!?…\"'")) + 2.5 for w in toks]
    acc, tot = 0, sum(wts)
    for w, wt in zip(toks, wts):
        a = t + dur * acc / tot; acc += wt
        words.append((w, a, t + dur * acc / tot, si))
    ln["_s"], ln["_e"] = t, t + dur
    gap = ln.get("pause", 0.35)
    parts += [s.astype(np.float32), np.zeros(int(SR * gap), np.float32)]
    t += dur + gap
for i, ln in enumerate(spec["lines"]):
    ln["_se"] = spec["lines"][i + 1]["_s"] if i + 1 < len(spec["lines"]) else t + 1.2
voice = np.concatenate(parts)
total = len(voice) / SR + 1.2
voice = np.pad(voice, (0, int(SR * total) - len(voice)))

# ================= score: sparse piano + drone + tape hiss =================
n = len(voice); tt = np.arange(n) / SR
music = np.zeros(n, np.float32)
music += 0.05 * np.sin(2 * np.pi * 55 * tt) + 0.03 * np.sin(2 * np.pi * 82.41 * tt + 1)
music *= 0.6 + 0.4 * np.sin(2 * np.pi * tt / 7) ** 2
notes = [220.0, 261.63, 329.63, 246.94, 196.0, 261.63, 293.66, 220.0, 174.61, 220.0, 261.63, 329.63]
step = 1.5
for k in range(int(total / step)):
    f = notes[k % len(notes)]
    a = int((k * step + 0.2) * SR); b = min(a + int(3.0 * SR), n)
    if a >= n: break
    lt = tt[a:b] - tt[a]
    tone = sum(np.sin(2 * np.pi * f * h * lt) / h ** 1.6 for h in (1, 2, 3, 4))
    music[a:b] += tone * np.exp(-lt * 1.6) * 0.07
    if k % 2 == 0:   # soft lower octave
        music[a:b] += np.sin(np.pi * f * lt) * np.exp(-lt * 1.2) * 0.04
music += rng.normal(0, 0.004, n).astype(np.float32)        # tape hiss
music *= np.clip(tt / 2.0, 0, 1) * np.clip((total - tt) / 2.0, 0, 1)
mix = voice + music * 0.55
mix = mix / np.abs(mix).max() * 0.92
sf.write(work + "_audio.wav", mix, SR)

# ================= backgrounds & film =================
yy = np.linspace(0, 1, H)[:, None]; xx = np.linspace(-1, 1, W)[None, :]
def fog(horizon=0.62, top=0.42, glow=0.93, bottom=0.30):
    """Foggy gradient, brightest just above the horizon."""
    up = np.clip((horizon - yy) / horizon, 0, 1)
    sky = glow * (1 - up) + top * up
    ground = glow - (glow - bottom) * np.clip((yy - horizon) / (1 - horizon), 0, 1) ** 0.6
    g = np.where(yy < horizon, sky, ground) * np.ones((1, W))
    return g.astype(np.float32)
FOG = fog()
NIGHT = (0.10 + 0.10 * np.exp(-((yy - 0.45) ** 2) / 0.08) * np.ones((1, W))).astype(np.float32)
VIG = (1 - 0.55 * np.clip((xx ** 2) * 0.55 + ((yy - 0.48) * 2) ** 2 * 0.45, 0, 1) ** 1.4).astype(np.float32)
GRAIN = [rng.normal(0, 1, (H, W)).astype(np.float32) for _ in range(8)]

def ease(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)

# ================= ink text =================
def lowfreq(h, w, cell, seed):
    r = np.random.default_rng(seed)
    small = r.random((max(2, h // cell), max(2, w // cell))).astype(np.float32)
    return np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255 - 0.5

class Ink:
    """Text that bleeds into shape from blots. render(u) -> alpha (0..1) for u in 0..1."""
    def __init__(self, lines, size, align="center", lead=1.08, seed=0, maxw=W - 120):
        f = F(size)
        tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
        while max(tmp.textlength(l, font=f) for l in lines) > maxw and size > 30:
            size -= 4; f = F(size)
        pad = int(size * 0.5)
        lh = int(size * lead)
        self.h = lh * len(lines) + pad * 2
        m = Image.new("L", (W, self.h), 0); d = ImageDraw.Draw(m)
        for i, l in enumerate(lines):
            d.text((W / 2 if align == "center" else 70, pad + i * lh), l, font=f, fill=255, anchor="ma" if align == "center" else "la")
        M = np.asarray(m).astype(np.float32) / 255
        self.M = np.asarray(m.filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255
        self.B = np.asarray(m.filter(ImageFilter.GaussianBlur(size * 0.10))).astype(np.float32) / 255
        self.N = lowfreq(self.h, W, max(6, size // 7), seed) + 0.5 * lowfreq(self.h, W, max(3, size // 18), seed + 1)
        # splatter blots around the letters
        r = random.Random(seed)
        sp = Image.new("L", (W, self.h), 0); sd = ImageDraw.Draw(sp)
        ys, xs = np.nonzero(M > 0.5)
        for _ in range(26 if len(xs) else 0):
            k = r.randrange(len(xs)); cx = xs[k] + r.gauss(0, size * 0.45); cy = ys[k] + r.gauss(0, size * 0.35)
            rad = r.uniform(size * 0.05, size * 0.15)
            sd.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=255)
        self.S = np.asarray(sp.filter(ImageFilter.GaussianBlur(size * 0.05))).astype(np.float32) / 255
    def render(self, u):
        u = max(0.0, min(1.0, u))
        thr = 1.15 - 0.73 * ease(u)
        splat = 0.9 * math.sin(math.pi * min(1, u * 1.25)) + 0.12 * u
        v = self.M * 0.62 + self.B * 0.55 + self.S * splat * 1.0 + self.N * 0.28
        return np.clip((v - thr) * 12, 0, 1)

def apply_ink(arr, ink, u, y, tone=0.04, strength=1.0):
    a = ink.render(u) * strength
    y0, y1 = max(0, y), min(H, y + ink.h)
    if y1 <= y0: return
    a = a[y0 - y: y1 - y]
    arr[y0:y1] = arr[y0:y1] * (1 - a) + tone * a

# ================= silhouettes =================
def figure(d, x, feet, h, face=-1, fill=0):
    """Lone standing figure in a long coat; face=-1 looks left."""
    s = h / 100.0
    d.ellipse([x - 6 * s, feet - 100 * s, x + 6 * s, feet - 87 * s], fill=fill)           # head
    d.polygon([(x - 4 * s, feet - 88 * s), (x + 4 * s, feet - 88 * s), (x + 11 * s, feet - 80 * s),
               (x + 13 * s, feet - 45 * s), (x + 15 * s, feet - 22 * s), (x - 15 * s, feet - 22 * s),
               (x - 13 * s, feet - 45 * s), (x - 11 * s, feet - 80 * s)], fill=fill)          # coat
    d.polygon([(x - 8 * s, feet - 23 * s), (x - 2 * s, feet - 23 * s), (x - 3 * s, feet), (x - 8 * s, feet)], fill=fill)
    d.polygon([(x + 2 * s, feet - 23 * s), (x + 8 * s, feet - 23 * s), (x + 8 * s, feet), (x + 3 * s, feet)], fill=fill)
    d.polygon([(x - 6 * s, feet - 101 * s), (x + 6 * s, feet - 101 * s), (x + 9 * s, feet - 95 * s), (x - 9 * s, feet - 95 * s)], fill=fill)  # hat brim

def ridge(d, base, seed, amp=40, fill=0):
    r = random.Random(seed); pts = [(0, H)]
    for x in range(0, W + 60, 60):
        pts.append((x, base + r.uniform(-amp, amp) * (0.6 + 0.4 * math.sin(x / 170))))
    pts.append((W, H)); d.polygon(pts, fill=fill)

# grey banded planet texture
TEX_W, TEX_H = 1600, 520
gy = np.linspace(0, 1, TEX_H)[:, None]; gx = np.linspace(0, 2 * np.pi, TEX_W)[None, :]
band = np.sin(gy * 24 + np.sin(gx * 3) * 1.4) + 0.6 * np.sin(gy * 57 + np.cos(gx * 5) * 2) + 0.4 * np.sin(gx * 7 + gy * 9)
band = (band - band.min()) / (band.max() - band.min())
TEX = np.concatenate([0.22 + 0.30 * band] * 2, 1).astype(np.float32)
_pl = {}
def planet(arr, cx, cy, r, rot=0.0, lit=True):
    """Draw a grey banded sphere lit from the upper left (crescent-ish)."""
    if r not in _pl:
        g = np.mgrid[-r:r, -r:r].astype(np.float32) / r
        dist = np.sqrt(g[0] ** 2 + g[1] ** 2)
        mask = np.clip((1 - dist) * r / 2, 0, 1)
        z = np.sqrt(np.clip(1 - dist ** 2, 0, 1))
        light = np.clip(-0.55 * g[1] - 0.6 * g[0] + 0.55 * z, 0, 1) ** 1.3
        rim = np.clip(1 - np.abs(dist - 0.985) * 40, 0, 1) * np.clip(-g[1] - g[0], 0, 1)
        _pl[r] = (mask, light, rim)
    mask, light, rim = _pl[r]
    off = int((rot % 1) * TEX_W)
    tex = np.asarray(Image.fromarray((TEX[:, off:off + TEX_W // 2] * 255).astype(np.uint8)).resize((2 * r, 2 * r))).astype(np.float32) / 255
    body = tex * (0.25 + 1.25 * light) + rim * 0.6 if lit else np.full_like(tex, 0.03)
    y0, x0 = cy - r, cx - r
    ys = slice(max(0, y0), min(H, y0 + 2 * r)); xs = slice(max(0, x0), min(W, x0 + 2 * r))
    sub_m = mask[ys.start - y0: ys.stop - y0, xs.start - x0: xs.stop - x0]
    sub_b = body[ys.start - y0: ys.stop - y0, xs.start - x0: xs.stop - x0]
    arr[ys, xs] = arr[ys, xs] * (1 - sub_m) + np.clip(sub_b, 0, 1) * sub_m

def glow(arr, cx, cy, r, strength=0.7, core=True):
    d2 = ((np.arange(W)[None, :] - cx) ** 2 + (np.arange(H)[:, None] - cy) ** 2).astype(np.float32)
    g = strength * np.exp(-d2 / (2 * (r * 2.2) ** 2))
    arr += g
    if core: arr[:] = np.maximum(arr, np.clip((r - np.sqrt(d2)) * 0.15, 0, 1) * 1.0)

def layer_from(draw_fn, soften=1.2):
    """Run a PIL draw function on a mask; return 0..1 alpha (for black silhouettes)."""
    m = Image.new("L", (W, H), 0); draw_fn(ImageDraw.Draw(m))
    if soften: m = m.filter(ImageFilter.GaussianBlur(soften))
    return np.asarray(m).astype(np.float32) / 255

# ================= scenes =================
INK = {}
def ink(key, lines, size, seed=None):
    if key not in INK: INK[key] = Ink(lines, size, seed=seed if seed is not None else len(INK) * 7 + 1)
    return INK[key]

def sc_title(sc, lt, dur, arr):
    arr[:] = FOG
    sil = layer_from(lambda d: (ridge(d, 1330, 4, 22, fill=255), figure(d, 760, 1340, 150, fill=255)))
    arr *= (1 - sil * 0.97)
    for i, ln in enumerate(sc["lines"]):
        k = ink(f"title{i}{ln}", [ln], sc.get("size", 132))
        apply_ink(arr, k, (lt - 0.15 - i * 0.55) / 1.3, 420 + i * int(sc.get("size", 132) * 1.12))

def sc_planet(sc, lt, dur, arr):
    arr[:] = NIGHT
    r = sc.get("r", 360)
    planet(arr, W // 2, sc.get("y", 860), r, rot=lt / sc.get("spin_secs", 60) * sc.get("dir", 1))
    if sc.get("arrow"):
        sgn = sc.get("dir", 1)
        def arrow(d):
            a0, a1 = (-150, -30) if sgn > 0 else (-30, -150)
            cx, cy, R = W // 2, sc.get("y", 860), r + 70
            pts = [(cx + R * math.cos(math.radians(a0 + (a1 - a0) * k / 40)), cy + R * math.sin(math.radians(a0 + (a1 - a0) * k / 40))) for k in range(int(41 * ease(lt / 1.2)))]
            if len(pts) > 3:
                d.line(pts, fill=255, width=14, joint="curve")
                ex, ey = pts[-1]; px, py = pts[-4]; ang = math.atan2(ey - py, ex - px)
                d.polygon([(ex + 40 * math.cos(ang), ey + 40 * math.sin(ang)), (ex + 30 * math.cos(ang + 2.4), ey + 30 * math.sin(ang + 2.4)), (ex + 30 * math.cos(ang - 2.4), ey + 30 * math.sin(ang - 2.4))], fill=255)
        a = layer_from(arrow, 1.5); arr[:] = arr * (1 - a) + 0.92 * a
    if "label" in sc:
        k = ink("pl" + sc["label"], [sc["label"]], sc.get("label_size", 110))
        apply_ink(arr, k, (lt - 0.3) / 1.1, sc.get("label_y", 260), tone=0.93)
    if "count" in sc:
        v = int(sc["count"] * ease((lt - 0.2) / max(1, dur - 0.8)))
        f = F(190); m = Image.new("L", (W, 260), 0); ImageDraw.Draw(m).text((W / 2, 10), str(v), font=f, fill=255, anchor="ma")
        a = np.asarray(m.filter(ImageFilter.GaussianBlur(1))).astype(np.float32) / 255
        arr[1270:1530] = arr[1270:1530] * (1 - a) + 0.95 * a

def sc_orbit(sc, lt, dur, arr):
    arr[:] = NIGHT
    cx, cy, R = W // 2, 860, 380
    glow(arr, cx, cy, 70, 0.55)
    p = ease(lt / max(1, dur - 0.4))
    def path(d):
        steps = int(p * 160)
        pts = [(cx + R * math.cos(-math.pi / 2 + k / 160 * 2 * math.pi), cy + R * math.sin(-math.pi / 2 + k / 160 * 2 * math.pi)) for k in range(steps + 1)]
        if len(pts) > 1: d.line(pts, fill=255, width=5)
    a = layer_from(path, 1); arr[:] = arr * (1 - a) + 0.75 * a
    ang = -math.pi / 2 + p * 2 * math.pi
    planet(arr, int(cx + R * math.cos(ang)), int(cy + R * math.sin(ang)), 54, rot=p)
    v = int(sc["days"] * p)
    f = F(190); m = Image.new("L", (W, 260), 0); ImageDraw.Draw(m).text((W / 2, 10), str(v), font=f, fill=255, anchor="ma")
    a = np.asarray(m.filter(ImageFilter.GaussianBlur(1))).astype(np.float32) / 255
    arr[1300:1560] = arr[1300:1560] * (1 - a) + 0.95 * a
    k = ink("orbitlbl", [sc.get("label", "one lap of the Sun")], 84)
    apply_ink(arr, k, (lt - 0.2) / 1.0, 300, tone=0.93)

def sc_ledger(sc, lt, dur, arr):
    arr[:] = FOG * 1.02
    for i, ln in enumerate(sc["lines"]):
        k = ink("led" + ln, [ln], sc.get("size", 120))
        apply_ink(arr, k, (lt - i * 0.9) / 1.1, sc.get("y", 470) + i * int(sc.get("size", 120) * 1.5))

def sc_horizon(sc, lt, dur, arr):
    arr[:] = FOG
    p = ease(lt / max(1, dur))
    sx, sy = 250 + 60 * p, 1330 - 380 * p
    glow(arr, sx, sy, 75, 0.35)
    sil = layer_from(lambda d: (ridge(d, 1340, 9, 30, fill=255), figure(d, 800, 1350, 210, fill=255)))
    arr *= (1 - sil * 0.97)
    for key, txt, x, y in (("w", "west", 250, 1420), ("e", "east", 800, 1420)):
        m = Image.new("L", (W, 120), 0); ImageDraw.Draw(m).text((x, 0), txt, font=F(80), fill=255, anchor="ma")
        a = np.asarray(m).astype(np.float32) / 255 * ease((lt - 0.6) / 0.6)
        arr[y:y + 120] = arr[y:y + 120] * (1 - a) + 0.85 * a

def sc_heat(sc, lt, dur, arr):
    arr[:] = FOG
    glow(arr, W // 2, 520, 160, 0.35)
    sil = layer_from(lambda d: (ridge(d, 1300, 21, 18, fill=255), figure(d, W // 2, 1310, 260, fill=255)))
    arr *= (1 - sil * 0.97)
    # heat shimmer: wobble rows above the ground
    rows = np.arange(700, 1300)
    shift = (6 * np.sin(rows / 9 + lt * 9) * np.clip((rows - 700) / 600, 0, 1)).astype(int)
    for r0 in range(0, len(rows), 3):
        r = rows[r0]; arr[r:r + 3] = np.roll(arr[r:r + 3], shift[r0], axis=1)
    k = ink("heat" + sc["big"], [sc["big"]], 230)
    apply_ink(arr, k, (lt - 0.2) / 1.1, 330)
    k2 = ink("heat2" + sc["small"], [sc["small"]], 70)
    apply_ink(arr, k2, (lt - 0.9) / 1.0, 700)

def sc_end(sc, lt, dur, arr):
    arr[:] = FOG
    k = ink("end1", ["Sounds Fake"], 170, seed=99)
    apply_ink(arr, k, (lt - 0.1) / 1.4, 560)
    def bubble(d):
        u = ease((lt - 1.0) / 0.6)
        if u <= 0: return
        cx, cy = W / 2, 1000; w, h = 190 * u, 140 * u
        d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], 40 * u, fill=255)
        d.polygon([(cx - w * 0.3, cy + h / 2 - 4), (cx - w * 0.05, cy + h / 2 - 4), (cx - w * 0.33, cy + h / 2 + 40 * u)], fill=255)
    a = layer_from(bubble, 1.2); arr[:] = arr * (1 - a) + 0.05 * a
    if lt > 1.2:
        m = Image.new("L", (W, 140), 0); ImageDraw.Draw(m).text((W / 2, 70), "?!", font=F(110), fill=255, anchor="mm")
        a = np.asarray(m).astype(np.float32) / 255 * ease((lt - 1.2) / 0.4)
        arr[930:1070] = arr[930:1070] * (1 - a) + 0.95 * a
    k2 = ink("end2", ["follow for more"], 70, seed=98)
    apply_ink(arr, k2, (lt - 1.6) / 1.0, 1150)

SCENES = {"title": sc_title, "planet": sc_planet, "orbit": sc_orbit, "ledger": sc_ledger,
          "horizon": sc_horizon, "heat": sc_heat, "end": sc_end}

def active(t):
    cur = None
    for ln in spec["lines"]:
        if "scene" in ln and ln["_s"] - 0.2 <= t: cur = ln
    return cur

# ================= captions (ink, in a soft band) =================
groups, cur = [], []
for i, w in enumerate(words):
    cur.append(i)
    if len(cur) == 4 or i + 1 == len(words) or words[i + 1][3] != w[3] or w[0][-1] in ".,?!…":
        groups.append(cur); cur = []
CAPS = [Ink([" ".join(words[i][0] for i in g)], 78, seed=500 + gi) for gi, g in enumerate(groups)]
CAP_Y = 1600
BAND = np.exp(-((np.arange(H)[:, None] - (CAP_Y + 55)) ** 2) / (2 * 75 ** 2)).astype(np.float32) * np.ones((1, W), np.float32)

def captions(arr, t):
    for gi, g in enumerate(groups):
        s0, e0 = words[g[0]][1] - 0.08, words[g[-1]][2] + 0.15
        if s0 <= t < e0:
            if arr[CAP_Y - 20:CAP_Y + 130].mean() < 0.45:   # dark scene: white ink
                apply_ink(arr, CAPS[gi], (t - s0) / 0.28, CAP_Y - 30, tone=0.96)
            else:                                            # light scene: black ink on a soft pale band
                arr[:] = arr * (1 - BAND * 0.6) + 0.9 * BAND * 0.6
                apply_ink(arr, CAPS[gi], (t - s0) / 0.28, CAP_Y - 30, tone=0.03)
            return

# ================= render =================
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-i", work + "_audio.wav", "-c:v", "libx264", "-preset", "veryfast",
                       "-crf", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                       "-movflags", "+faststart", out_path], stdin=subprocess.PIPE)
prev = None; arr = np.zeros((H, W), np.float32)
for fi in range(int(total * FPS)):
    t = fi / FPS
    ln = active(t)
    if ln:
        sc = ln["scene"]; lt = t - ln["_s"]; dur = ln["_se"] - ln["_s"]
        SCENES[sc["type"]](sc, lt, dur, arr)
        # quick dip-to-black between scenes, like a film cut
        if lt < 0.0: arr *= 0.0
        elif lt < 0.25: arr *= ease((lt + 0.2) / 0.45)
    else:
        arr[:] = 0
    captions(arr, t)
    # film look: vignette, flicker, grain, dust
    out = arr * VIG * (1 + 0.035 * math.sin(t * 23) + 0.02 * random.random())
    out += GRAIN[fi % len(GRAIN)] * 0.065
    if random.random() < 0.35:
        x, y = random.randrange(W), random.randrange(H)
        out[max(0, y - 2):y + 2, max(0, x - 2):x + 2] = random.choice((0.0, 1.0))
    if random.random() < 0.06:
        x = random.randrange(W); out[:, x:x + 2] *= 0.75
    ff.stdin.write((np.clip(out, 0, 1) * 255).astype(np.uint8).tobytes())
ff.stdin.close(); ff.wait()
print(f"done {total:.1f}s")
