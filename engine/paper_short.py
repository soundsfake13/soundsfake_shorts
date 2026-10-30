"""PAPER-CUTOUT style (after 'Paper-cutout girl writes a question' on claudevideo.org).
Layered cut paper with rough edges, soft drop shadows, paper grain, stop-motion 'boil'.
Best for animals, plants and nature. Usage: python3 paper_short.py spec.json out.mp4
"""
import json, math, random, sys
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
random.seed(4); rng = np.random.default_rng(4)

def FONT(size, weight=650):
    f = ImageFont.truetype(f"{FONTS}/Fredoka.ttf", size); f.set_variation_by_axes([weight, 100]); return f

C = dict(deep=(31, 78, 95), sea=(46, 125, 140), light=(143, 201, 196), sand=(233, 211, 166), cream=(246, 238, 220),
         coral=(232, 102, 74), red=(214, 64, 56), blue=(58, 111, 216), ink=(43, 37, 34), yellow=(242, 179, 61),
         pink=(240, 160, 150), green=(86, 150, 98), dkgreen=(52, 110, 74), white=(252, 250, 244))

# ---------------- paper machinery ----------------
def noise(h, w, cell, seed):
    r = np.random.default_rng(seed)
    s = r.random((max(2, h // cell), max(2, w // cell))).astype(np.float32)
    return np.asarray(Image.fromarray((s * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255

TEX = (0.95 + 0.06 * noise(H, W, 3, 1) + 0.04 * noise(H, W, 40, 2) - 0.03).astype(np.float32)

def rough(m, seed, amt=0.42):
    a = np.asarray(m.filter(ImageFilter.GaussianBlur(2.2))).astype(np.float32) / 255
    n = noise(m.height, m.width, 4, seed) + 0.6 * noise(m.height, m.width, 14, seed + 7)
    out = ((a + (n - 0.8) * amt) > 0.5).astype(np.uint8) * 255
    return Image.fromarray(out).filter(ImageFilter.GaussianBlur(0.8))

class Sheet:
    """A stack of cut-paper layers; each layer casts a soft shadow on what is below."""
    def __init__(self, w, h, base=None):
        self.w, self.h = w, h
        self.img = base.copy() if base is not None else Image.new("RGBA", (w, h), (0, 0, 0, 0))
    def add(self, draw, color, seed=0, sh=(7, 11), blur=8, salpha=0.30, amt=0.42):
        m = Image.new("L", (self.w, self.h), 0); draw(ImageDraw.Draw(m)); m = rough(m, seed, amt)
        if salpha > 0:
            s = ImageChops.offset(m.filter(ImageFilter.GaussianBlur(blur)), *sh)
            shadow = Image.new("RGBA", (self.w, self.h), (25, 18, 12, 0))
            shadow.putalpha(s.point(lambda v: int(v * salpha))); self.img.alpha_composite(shadow)
        ox, oy = random.randrange(0, W - self.w + 1) if self.w < W else 0, random.randrange(0, H - self.h + 1) if self.h < H else 0
        tex = TEX[oy:oy + self.h, ox:ox + self.w]
        if tex.shape != (self.h, self.w): tex = np.ones((self.h, self.w), np.float32)
        rgb = np.clip(np.array(color, np.float32)[None, None, :] * tex[..., None], 0, 255).astype(np.uint8)
        layer = Image.fromarray(rgb).convert("RGBA"); layer.putalpha(m); self.img.alpha_composite(layer)
        return self

def heart_pts(cx, cy, s):
    pts = []
    for k in range(60):
        a = k / 60 * 2 * math.pi
        x = 16 * math.sin(a) ** 3; y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((cx + x * s, cy - y * s))
    return pts

def drop_pts(cx, cy, r):
    pts = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in np.linspace(-0.25 * math.pi, 1.25 * math.pi, 40)]
    return pts + [(cx, cy - r * 2.3)]

# ---------------- sprites ----------------
def octopus(var, stretch=0.0, size=(660, 760)):
    w, h = size; S = Sheet(w, h); cx, cy = w / 2, 250
    def tentacles(d):
        for k in range(8):
            x0 = cx - 165 + k * 47
            side = (k - 3.5) / 3.5
            pts = []
            L = 330 + 90 * stretch
            for j in range(36):
                u = j / 35
                sway = (1 - stretch) * (34 * math.sin(u * 3.2 + var * 2.1 + k * 0.9) + 120 * side * u ** 1.6)
                pts.append((x0 + sway + side * 40 * u, 360 + u * L))
            for j, (x, y) in enumerate(pts):
                r = 34 * (1 - j / 40)
                d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    S.add(tentacles, C["coral"], seed=10 + var)
    S.add(lambda d: d.ellipse([cx - 185, cy - 215, cx + 185, cy + 175], fill=255), C["coral"], seed=20 + var, sh=(5, 8), salpha=0.22)
    def spots(d):
        for (x, y, r) in [(-90, -110, 22), (60, -140, 15), (110, -60, 18), (-40, -40, 12), (20, -175, 10)]:
            d.ellipse([cx + x - r, cy + y - r, cx + x + r, cy + y + r], fill=255)
    S.add(spots, (245, 140, 110), seed=30 + var, salpha=0.0)
    S.add(lambda d: [d.ellipse([cx + dx - 46, cy - 46, cx + dx + 46, cy + 46], fill=255) for dx in (-75, 75)], C["white"], seed=40 + var, sh=(3, 5), blur=4)
    S.add(lambda d: [d.ellipse([cx + dx - 20, cy - 12, cx + dx + 20, cy + 28], fill=255) for dx in (-68, 82)], C["ink"], seed=50 + var, salpha=0.0, amt=0.2)
    S.add(lambda d: [d.ellipse([cx + dx - 34, cy + 48, cx + dx + 2, cy + 72], fill=255) for dx in (-105, 120)], C["pink"], seed=60 + var, salpha=0.0)
    S.add(lambda d: d.arc([cx - 40, cy + 40, cx + 40, cy + 100], 20, 160, fill=255, width=12), C["ink"], seed=70 + var, salpha=0.0, amt=0.15)
    return S.img

def heart_sprite(color, s=10, var=0, label=None):
    w = int(s * 40); S = Sheet(w, w)
    S.add(lambda d: d.polygon(heart_pts(w / 2, w / 2 - s, s), fill=255), color, seed=80 + var)
    S.add(lambda d: d.ellipse([w * 0.30, w * 0.25, w * 0.42, w * 0.37], fill=255), (255, 255, 255), seed=85 + var, salpha=0.0)
    return S.img

def drop_sprite(color, r=110, var=0):
    w, h = int(r * 2.6), int(r * 4.0); S = Sheet(w, h)
    S.add(lambda d: d.polygon(drop_pts(w / 2, h - r * 1.2, r), fill=255), color, seed=90 + var)
    S.add(lambda d: d.ellipse([w / 2 - r * 0.55, h - r * 1.7, w / 2 - r * 0.2, h - r * 1.25], fill=255), (255, 255, 255), seed=95 + var, salpha=0.0)
    return S.img

def strip(text, size=86, fill=C["cream"], ink=C["ink"], pad=(44, 22), seed=0, hi=None, hi_col=C["coral"]):
    f = FONT(size); d0 = ImageDraw.Draw(Image.new("L", (4, 4)))
    tw = int(d0.textlength(text, font=f)); w, h = tw + pad[0] * 2 + 30, size + pad[1] * 2 + 30
    S = Sheet(w, h)
    S.add(lambda d: d.rectangle([15, 12, w - 15, h - 18], fill=255), fill, seed=100 + seed, amt=0.6)
    d = ImageDraw.Draw(S.img); x = 15 + pad[0]
    for i, word in enumerate(text.split(" ")):
        d.text((x, 12 + pad[1] - size * 0.12), word, font=f, fill=hi_col if (hi is not None and i == hi) else ink)
        x += d.textlength(word + " ", font=f)
    return S.img

def paste(frame, spr, cx, cy, rot=0.0, scale=1.0):
    if scale != 1.0:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    if rot: spr = spr.rotate(rot, expand=True, resample=Image.BICUBIC)
    frame.alpha_composite(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2))) if (
        0 <= int(cx - spr.width / 2) and int(cx + spr.width / 2) <= W and 0 <= int(cy - spr.height / 2) and int(cy + spr.height / 2) <= H) \
        else safe_paste(frame, spr, int(cx - spr.width / 2), int(cy - spr.height / 2))

def safe_paste(frame, spr, x, y):
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + spr.width), min(H, y + spr.height)
    if x1 <= x0 or y1 <= y0: return
    frame.alpha_composite(spr.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))

# ---------------- backgrounds ----------------
def bg_sea(seed=0, floor=True):
    base = Image.new("RGBA", (W, H), C["deep"] + (255,))
    S = Sheet(W, H, base)
    def wave(y, amp, ph):
        return lambda d: d.polygon([(x, y + amp * math.sin(x / 140 + ph)) for x in range(-20, W + 40, 30)] + [(W + 40, H), (-20, H)], fill=255)
    S.add(wave(330, 26, seed), (38, 98, 114), seed=200 + seed)
    S.add(wave(720, 30, seed + 2), C["sea"], seed=210 + seed)
    if floor:
        S.add(wave(1390, 22, seed + 4), C["sand"], seed=220 + seed)
        for k, x in enumerate((110, 230, 900, 990)):
            S.add(lambda d, x=x, k=k: d.polygon([(x - 24 + 14 * math.sin(j * 0.7 + k), 1400 - j * 26) for j in range(16)] +
                                                [(x + 24 + 14 * math.sin(j * 0.7 + k), 1400 - j * 26) for j in reversed(range(16))], fill=255),
                  C["green"] if k % 2 else C["dkgreen"], seed=230 + k + seed)
        S.add(lambda d: [d.ellipse([x - r, 1405 - r * 0.6, x + r, 1405 + r * 0.6], fill=255) for x, r in ((340, 70), (760, 95), (580, 45))],
              (176, 160, 140), seed=240 + seed)
    return S.img

def bg_flat(color, seed=0):
    base = Image.new("RGBA", (W, H), color + (255,))
    S = Sheet(W, H, base)
    darker = tuple(int(c * 0.88) for c in color)
    S.add(lambda d: d.polygon([(0, 1250), (W, 1120), (W, H), (0, H)], fill=255), darker, seed=300 + seed)
    return S.img

# ---------------- narration & music ----------------
voice, words, total = narrate(spec, default_gap=0.28)
n = len(voice); music = np.zeros(n, np.float32)
bpm = 104; beat = 60 / bpm
scale_ = [261.63, 293.66, 329.63, 392.0, 440.0, 523.25]
chords = [[0, 2, 4], [1, 3, 5], [0, 2, 3], [2, 4, 5]]
for b in range(int(total / beat * 2)):
    at = b * beat / 2; ch = chords[(b // 8) % 4]
    note = scale_[ch[(b * 2 + (b // 3)) % 3]] * (2 if b % 4 == 3 else 1)
    place(music, at, tone(note, 0.5, decay=9, harm=(1, 4, 10)), 0.10)
    if b % 4 == 0: place(music, at, tone(scale_[ch[0]] / 2, 0.9, decay=3, harm=(1, 2)), 0.12)
    sh = rng.normal(0, 1, int(0.04 * SR)) * np.exp(-np.arange(int(0.04 * SR)) / SR * 80)
    place(music, at, sh, 0.012 if b % 2 else 0.02)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55)

# ---------------- scenes ----------------
CACHE = {}
def cached(key, fn):
    if key not in CACHE: CACHE[key] = fn()
    return CACHE[key]
OCTO = [octopus(v) for v in range(3)]
OCTO_SWIM = [octopus(v, stretch=0.8) for v in range(3)]
def boil(t): return int(t * 8) % 3
def jit(t, k=0, a=4):
    q = math.floor(t * 12); r = random.Random(q * 31 + k); return r.uniform(-a, a), r.uniform(-a, a)

def strips_in(frame, lines, lt, y0, gap=150, size=96, colors=None, hi=None):
    for i, txt in enumerate(lines):
        u = back((lt - i * 0.28) / 0.35)
        if u <= 0: continue
        fill = C[colors[i % len(colors)]] if colors else C["cream"]
        hw = hi.get(str(i)) if hi else None
        spr = cached(("strip", txt, size, fill, hw), lambda: strip(txt, size, fill=fill, seed=i * 3 + len(txt), hi=hw))
        jx, jy = jit(lt, i, 2)
        paste(frame, spr, W / 2 + jx, y0 + i * gap - (1 - u) * 260 + jy, rot=(-3 if i % 2 else 2.5) * u, scale=1.0)

def sc_hook(sc, lt, dur, t):
    f = cached(("bg_sea", 0), lambda: bg_sea(0)).copy()
    jx, jy = jit(t, 9, 3)
    paste(f, OCTO[boil(t)], W / 2 + jx, 1020 + 22 * math.sin(t * 2.2) + jy, rot=4 * math.sin(t * 1.3), scale=0.95 * back(lt / 0.5))
    strips_in(f, sc["lines"], lt, 300, gap=150, size=sc.get("size", 96), hi=sc.get("hi"))
    return f

def sc_title(sc, lt, dur, t):
    f = cached(("bg_flat", sc.get("bg", "yellow")), lambda: bg_flat(C[sc.get("bg", "yellow")], 1)).copy()
    strips_in(f, sc["lines"], lt, sc.get("y", 720), gap=200, size=sc.get("size", 120), colors=sc.get("colors"), hi=sc.get("hi"))
    return f

def sc_hearts(sc, lt, dur, t):
    f = cached(("bg_sea", 1), lambda: bg_sea(1, floor=False)).copy()
    paste(f, cached("oct_small", lambda: octopus(1).resize((330, 380))), W / 2, 330 + 8 * math.sin(t * 2), rot=3 * math.sin(t))
    specs = [(250, 900, 7, "GILLS", 0.0), (W / 2, 1000, 11, "BODY", 0.25), (W - 250, 900, 7, "GILLS", 0.5)]
    for k, (x, y, s, lab, ph) in enumerate(specs):
        u = back((lt - 0.2 - k * 0.35) / 0.35)
        if u <= 0: continue
        beat_ = 1 + 0.08 * max(0, math.sin((t * 2.4 + ph) * 2 * math.pi)) ** 6
        spr = cached(("heart", s, k), lambda: heart_sprite(C["red"], s, var=k))
        paste(f, spr, x, y, scale=u * beat_)
        lab_spr = cached(("lab", lab, k), lambda: strip(lab, 56, fill=C["cream"], seed=40 + k))
        paste(f, lab_spr, x, y + s * 24 + 40, rot=-2 + k * 2, scale=u)
    if lt > 1.4:
        u = back((lt - 1.4) / 0.35)
        paste(f, cached("three", lambda: strip("3 HEARTS", 120, fill=C["yellow"], seed=77)), W / 2, 1470, rot=-4, scale=u)
    return f

def sc_blood(sc, lt, dur, t):
    f = cached(("bg_flat", "cream"), lambda: bg_flat((236, 226, 204), 2)).copy()
    for k, (col, x, lab, sub) in enumerate([(C["red"], 290, "US", "IRON"), (C["blue"], W - 290, "OCTOPUS", "COPPER")]):
        u = back((lt - 0.2 - k * 0.6) / 0.4)
        if u <= 0: continue
        jx, jy = jit(t, k + 20, 2)
        paste(f, cached(("drop", k), lambda: drop_sprite(col, 120, k)), x + jx, 760 - (1 - u) * 500 + jy)
        paste(f, cached(("dl", lab), lambda: strip(lab, 64, seed=k + 60)), x, 1080, rot=-2 + 4 * k, scale=u)
        paste(f, cached(("ds", sub), lambda: strip(sub, 52, fill=col, ink=C["white"], seed=k + 70)), x, 1200, rot=2 - 4 * k, scale=u)
    return f

def sc_swim(sc, lt, dur, t):
    f = cached(("bg_sea", 2), lambda: bg_sea(2, floor=False)).copy()
    y = 1300 - 700 * eout(lt / max(1.0, dur))
    for k in range(9):   # bubbles trailing behind
        by = y + 380 + ((k * 97 + t * 160) % 520); bx = W / 2 - 120 + (k * 53) % 240 + 20 * math.sin(t * 3 + k)
        r = 10 + (k % 3) * 7
        paste(f, cached(("bub", r), lambda: Sheet(r * 2 + 30, r * 2 + 30).add(lambda d: d.ellipse([12, 12, 12 + 2 * r, 12 + 2 * r], outline=255, width=5), C["light"], seed=r, salpha=0.0).img), bx, by)
    paste(f, OCTO_SWIM[boil(t)], W / 2, y, scale=0.85)
    hx, hy = 830, 360
    paste(f, cached("hs", lambda: heart_sprite(C["red"], 6, 9)), hx, hy)
    if lt > 0.8:
        u = back((lt - 0.8) / 0.3)
        paste(f, cached("paused", lambda: strip("STOPS!", 64, fill=C["yellow"], seed=91)), hx, hy + 150, rot=-10, scale=u)
    return f

def sc_crawl(sc, lt, dur, t):
    f = cached(("bg_sea", 3), lambda: bg_sea(3)).copy()
    x = 170 + (W - 340) * ease(lt / max(1.0, dur))
    jx, jy = jit(t, 5, 3)
    paste(f, OCTO[boil(t)], x + jx, 1180 + 14 * abs(math.sin(t * 4)) + jy, rot=-6 + 4 * math.sin(t * 4), scale=0.6)
    strips_in(f, sc.get("lines", []), lt, 380, gap=150, size=88, hi=sc.get("hi"))
    return f

def sc_end(sc, lt, dur, t):
    f = cached(("bg_flat", "ink"), lambda: bg_flat((52, 46, 60), 5)).copy()
    click = sc.get("click_at", 0.9); on = ease((lt - click) / 0.25)
    tx, ty, tw_, th = W / 2, 980, 380, 170
    track = cached(("track", int(on > 0.5)), lambda: Sheet(tw_ + 40, th + 40).add(lambda d: d.rounded_rectangle([12, 12, tw_ + 12, th + 12], th // 2, fill=255), C["coral"] if on > 0.5 else (120, 128, 150), seed=7).img)
    paste(f, track, tx, ty)
    knob = cached("knob", lambda: Sheet(th + 10, th + 10).add(lambda d: d.ellipse([16, 16, th - 14, th - 14], fill=255), C["cream"], seed=8).img)
    paste(f, knob, tx - tw_ / 2 + th / 2 + (tw_ - th) * on, ty)
    for txt, x, active in (("FAKE", tx - tw_ / 2 - 150, on < 0.5), ("TRUE", tx + tw_ / 2 + 150, on >= 0.5)):
        paste(f, cached(("tl", txt, active), lambda: strip(txt, 70, fill=C["cream"] if active else (150, 150, 165), seed=len(txt))), x, ty)
    if lt > click + 0.3:
        u = back((lt - click - 0.3) / 0.35)
        paste(f, cached("sfk", lambda: strip("SOUNDS FAKE ?!", 104, fill=C["yellow"], seed=99)), W / 2, 620, rot=-3, scale=u)
    return f

SCENES = dict(hook=sc_hook, title=sc_title, hearts=sc_hearts, blood=sc_blood, swim=sc_swim, crawl=sc_crawl, end=sc_end)

# ---------------- captions ----------------
groups = caption_groups(words, 3)
def caption(f, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    act = max([k for k, i in enumerate(g) if words[i][1] <= t + 0.02] or [0])
    txt = " ".join(words[i][0] for i in g)
    size = 76
    d0 = ImageDraw.Draw(Image.new("L", (4, 4)))
    while d0.textlength(txt, font=FONT(size)) > W - 200 and size > 44: size -= 4
    spr = cached(("cap", gi, act, size), lambda: strip(txt, size, fill=C["white"], seed=gi, hi=act, hi_col=C["coral"]))
    paste(f, spr, W / 2, 1640, rot=(-1.2 if gi % 2 else 1.2))

def frame(t, fi):
    ln = active_line(spec, t)
    if ln is None: f = bg_flat(C["yellow"])
    else:
        lt = t - ln["_s"]; dur = ln["_se"] - ln["_s"]
        f = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t)
    caption(f, t)
    ImageDraw.Draw(f).rectangle([0, H - 12, int(W * t / total), H], fill=C["coral"])
    return f.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:   # preview frames: python3 paper_short.py spec out.mp4 t1,t2,...
        for tt in sys.argv[3].split(","):
            Image.frombytes("RGB", (W, H), frame(float(tt), 0)).save(f"{work}_f{tt}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path)
        print(f"done {total:.1f}s")
