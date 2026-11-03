"""Day 7 — MANUSCRIPT vs CODEX style (Oxford is older than the Aztec Empire).
Two books share the screen: a medieval illuminated manuscript (vellum, black ink, vermilion rubrics, burnished
gold-leaf type with a moving sheen, Fraktur drop caps) and a screenfold codex panel (amate bark paper, flat
terracotta / turquoise / ochre fills, heavy black outlines, step-fret borders, footprints and hill place-signs).
Scenes change with a page turn. Fonts: Alegreya SC Black (type) + UnifrakturMaguntia (drop caps only).
Usage: python3 engine/styles/day07_codex.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
rng = np.random.default_rng(7); random.seed(7)
_fc = {}
def F(s, frak=False):
    k = (int(s), frak)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(f"{FONTS}/" + ("UnifrakturMaguntia-Book.ttf" if frak else "AlegreyaSC-Black.ttf"), int(s))
    return _fc[k]

VELLUM, INK, RED, BLUE = (238, 222, 184), (38, 26, 18), (178, 38, 26), (34, 62, 132)
GOLD, GOLD_D, GOLD_L = (212, 166, 58), (138, 96, 24), (255, 236, 160)
AMATE, TERRA, TURQ, OCHRE, BLACK, CREAM = (214, 186, 140), (190, 78, 46), (34, 146, 140), (224, 164, 52), (24, 18, 14), (244, 232, 204)

# ---------------- textures ----------------
def blotch(scale, amp, seed):
    r = np.random.default_rng(seed)
    small = r.normal(0, 1, (H // scale + 2, W // scale + 2)).astype(np.float32)
    big = np.asarray(Image.fromarray(small).resize((W + 2 * scale, H + 2 * scale), Image.BICUBIC))[:H, :W]
    return big * amp
grain = rng.normal(0, 1, (H, W)).astype(np.float32)
v = blotch(60, 7, 1) + blotch(14, 3, 2) + grain * 3
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vign = 1 - 0.18 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
VEL = np.clip((np.array(VELLUM, np.float32) + v[..., None] * np.array([1, 1, 1.2])) * vign[..., None], 0, 255)
fib = np.asarray(Image.fromarray((rng.normal(0, 1, (H // 2, W // 40)) * 40 + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)).astype(np.float32) - 128
AM = np.clip((np.array(AMATE, np.float32) + (fib * 0.22 + blotch(40, 6, 3) + grain * 4)[..., None]) * vign[..., None], 0, 255)
VEL_I = Image.fromarray(VEL.astype(np.uint8)); AM_I = Image.fromarray(AM.astype(np.uint8))

def vellum(): return VEL_I.copy()
def amate(): return AM_I.copy()

# ---------------- manuscript pieces ----------------
def ms_border(d, box, t=0.0):
    x0, y0, x1, y1 = box
    d.rectangle(box, outline=RED, width=6)
    d.rectangle([x0 + 16, y0 + 16, x1 - 16, y1 - 16], outline=GOLD_D, width=3)
    d.rectangle([x0 + 22, y0 + 22, x1 - 22, y1 - 22], outline=GOLD, width=4)
    for x in np.arange(x0 + 50, x1 - 30, 60):                       # tiny gold/blue dot vine
        for y in (y0 + 8, y1 - 8):
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=GOLD if int(x) // 60 % 2 else BLUE)
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        d.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=GOLD, outline=INK, width=3)
        d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=RED)

def gold_text(img, txt, size, cx, y, t=0.0, u=1.0, frak=False, anchor="ma"):
    """Burnished gold-leaf type: dark outline, vertical gradient, diagonal moving sheen."""
    if u <= 0: return
    d = ImageDraw.Draw(img)
    while d.textlength(txt, font=F(size, frak)) > W - 190 and size > 50: size -= 4
    f = F(size, frak)
    box = [int(round(v_)) for v_ in d.textbbox((cx, y), txt, font=f, anchor=anchor, stroke_width=6)]
    bw, bh = box[2] - box[0], box[3] - box[1]
    m = Image.new("L", (bw, bh), 0); ImageDraw.Draw(m).text((cx - box[0], y - box[1]), txt, font=f, anchor=anchor, fill=255)
    s = Image.new("L", (bw, bh), 0); ImageDraw.Draw(s).text((cx - box[0], y - box[1]), txt, font=f, anchor=anchor, fill=255, stroke_width=6)
    gy = np.linspace(0, 1, bh)[:, None]; gx = np.linspace(0, 1, bw)[None, :]
    base = np.array(GOLD_L) * (1 - gy[..., None]) * 0.55 + np.array(GOLD) * 0.45 + np.array(GOLD_D) * gy[..., None] * 0.55
    ph = (t * 0.45) % 1.6 - 0.3
    sheen = np.exp(-((gx * 0.8 + gy * 0.4 - ph) / 0.06) ** 2)[..., None]
    col = np.clip(base * (1 - sheen) + 255 * sheen, 0, 255).astype(np.uint8)
    lay = Image.new("RGBA", (bw, bh), INK + (0,)); lay.putalpha(s.point(lambda a: int(a * u)))
    img.paste(lay, (box[0] + 4, box[1] + 6), lay)                   # soft drop
    img.paste(Image.new("RGB", (bw, bh), INK), box[:2], s.point(lambda a: int(a * u)))
    img.paste(Image.fromarray(col), box[:2], m.point(lambda a: int(a * u)))

def dropcap(img, letter, x, y, s, t=0.0, bg=BLUE, frak=True):
    d = ImageDraw.Draw(img)
    d.rectangle([x, y, x + s, y + s], fill=bg, outline=GOLD, width=10)
    d.rectangle([x + 16, y + 16, x + s - 16, y + s - 16], outline=GOLD_L, width=2)
    for k in range(6):                                              # white filigree dots
        a = k * math.pi / 3 + t * 0.3
        d.ellipse([x + s / 2 + s * 0.36 * math.cos(a) - 5, y + s / 2 + s * 0.36 * math.sin(a) - 5,
                   x + s / 2 + s * 0.36 * math.cos(a) + 5, y + s / 2 + s * 0.36 * math.sin(a) + 5], fill=CREAM)
    gold_text(img, letter, int(s * (0.82 if frak else 0.7)), x + s / 2, y + s * (0.53 if frak else 0.5), t, frak=frak, anchor="mm")

def rubric(img, txt, size, cx, y, col=RED, u=1.0):
    if u <= 0: return
    d = ImageDraw.Draw(img); f = F(size)
    while d.textlength(txt, font=f) > W - 170 and size > 50: size -= 4; f = F(size)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.text((cx, y + (1 - u) * 30), txt, font=f, fill=col + (int(255 * u),), anchor="ma")
    img.paste(lay, (0, 0), lay)

def ribbon(img, txt, size, cx, cy, u=1.0, fill=RED, ink=CREAM):
    if u <= 0: return
    d = ImageDraw.Draw(img); f = F(size); tw = d.textlength(txt, font=f)
    while tw > W - 260 and size > 50: size -= 4; f = F(size); tw = d.textlength(txt, font=f)
    hw, hh = tw / 2 + 50, size * 0.72
    sc = 0.6 + 0.4 * back(u)
    lay = Image.new("RGBA", (W, int(hh * 2 + 60)), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay); my = lay.height / 2
    dk = tuple(int(c * 0.6) for c in fill)
    for sgn in (-1, 1):                                              # forked ribbon tails
        ex = cx + sgn * hw
        ld.polygon([(ex - sgn * 20, my - hh + 24), (ex + sgn * 80, my - hh + 24), (ex + sgn * 50, my + 12), (ex + sgn * 80, my + hh + 24), (ex - sgn * 20, my + hh + 24)], fill=dk, outline=INK)
    ld.rectangle([cx - hw, my - hh, cx + hw, my + hh], fill=fill, outline=INK, width=4)
    ld.text((cx, my), txt, font=f, fill=ink, anchor="mm")
    if sc != 1: lay = lay.resize((int(W * sc), int(lay.height * sc)), Image.BICUBIC)
    img.paste(lay, (int(cx - cx * sc), int(cy - lay.height / 2)), lay)

def quill(d, x, y, s=1.0):
    pts = [(x, y), (x + 40 * s, y - 70 * s), (x + 170 * s, y - 300 * s), (x + 210 * s, y - 330 * s), (x + 150 * s, y - 210 * s), (x + 30 * s, y - 50 * s)]
    d.polygon(pts, fill=CREAM, outline=INK)
    for k in range(9):
        a = 0.15 + k * 0.09
        px, py = x + (210 * s) * a, y - 330 * s * a
        d.line([(px, py), (px + 46 * s, py + 10 * s)], fill=INK, width=2)
    d.line([(x, y), (x + 200 * s, y - 320 * s)], fill=INK, width=4)

# ---------------- codex pieces ----------------
def fret(d, x0, y0, x1, h, col=BLACK, bg=TERRA):
    """Step-fret band (generic Mesoamerican geometric border)."""
    d.rectangle([x0, y0, x1, y0 + h], fill=bg, outline=BLACK, width=5)
    u = h - 16; nfit = int((x1 - x0 - 16 + 12) // (u + 12)); x = x0 + (x1 - x0 - nfit * (u + 12) + 12) / 2
    while x < x1 - u:
        y = y0 + 8
        pts = [(x, y + u), (x, y), (x + u * 0.75, y), (x + u * 0.75, y + u * 0.55), (x + u * 0.38, y + u * 0.55), (x + u * 0.38, y + u * 0.3),
               (x + u * 0.55, y + u * 0.3), (x + u * 0.55, y + u * 0.2), (x + u * 0.2, y + u * 0.2), (x + u * 0.2, y + u * 0.8), (x + u, y + u * 0.8), (x + u, y + u)]
        d.polygon(pts, fill=CREAM, outline=BLACK); x += u + 12

def cx_frame(d, box, shift=0):
    x0, y0, x1, y1 = box
    d.rectangle(box, outline=BLACK, width=8)
    fret(d, x0, y0, x1, 64); fret(d, x0, y1 - 64, x1, 64)
    d.rectangle([x0 + 12, y0 + 76, x1 - 12, y1 - 76], outline=TERRA, width=6)

def flat_text(img, txt, size, cx, y, fill=CREAM, block=TERRA, u=1.0, pad=28):
    """Codex label: flat colour block, heavy black outline, cream type with black stroke."""
    if u <= 0: return
    d = ImageDraw.Draw(img); f = F(size); tw = d.textlength(txt, font=f)
    while tw > W - 200 and size > 44: size -= 4; f = F(size); tw = d.textlength(txt, font=f)
    yo = (1 - back(u)) * 60
    if block:
        d.rectangle([cx - tw / 2 - pad + 10, y - pad * 0.5 + 10 + yo, cx + tw / 2 + pad + 10, y + size * 1.05 + pad * 0.5 + 10 + yo], fill=BLACK)
        d.rectangle([cx - tw / 2 - pad, y - pad * 0.5 + yo, cx + tw / 2 + pad, y + size * 1.05 + pad * 0.5 + yo], fill=block, outline=BLACK, width=6)
    dark = sum(fill) < 200
    d.text((cx, y + yo), txt, font=f, fill=fill, anchor="ma", stroke_width=0 if dark else max(3, size // 22), stroke_fill=BLACK)

def hill(d, cx, by, s, col=(92, 150, 70)):
    """Hill place-sign: bell-shaped hill with curled base."""
    pts = [(cx - 90 * s, by), (cx - 80 * s, by - 90 * s), (cx - 50 * s, by - 150 * s), (cx, by - 168 * s), (cx + 50 * s, by - 150 * s), (cx + 80 * s, by - 90 * s), (cx + 90 * s, by)]
    d.polygon(pts, fill=col, outline=BLACK); d.line(pts + [pts[0]], fill=BLACK, width=7)
    d.rectangle([cx - 100 * s, by - 6 * s, cx + 100 * s, by + 26 * s], fill=TERRA, outline=BLACK, width=6)
    for k in (-1, 1):
        d.arc([cx + k * 52 * s - 22 * s, by - 60 * s, cx + k * 52 * s + 22 * s, by - 16 * s], 0, 360, fill=OCHRE, width=int(8 * s))

def foot(d, x, y, s=1.0, left=True):
    o = -1 if left else 1
    d.ellipse([x - 18 * s, y - 34 * s, x + 18 * s, y + 30 * s], fill=BLACK)
    for k in range(4):
        tx = x - 15 * s + k * 10 * s; d.ellipse([tx - 6 * s, y - 50 * s - abs(k - 1.5) * 3 * s, tx + 6 * s, y - 38 * s], fill=BLACK)

def waves(d, box, t, col=TURQ):
    x0, y0, x1, y1 = box
    d.ellipse(box, fill=col, outline=BLACK, width=8)
    for r in range(4):
        y = y0 + (y1 - y0) * (0.22 + r * 0.18)
        for k in range(10):
            x = x0 + 60 + k * 90 + 30 * math.sin(t * 2 + r)
            if x0 + 40 < x < x1 - 80:
                d.arc([x, y - 16, x + 60, y + 16], 200, 340, fill=CREAM, width=6)

# ---------------- layout used by hook and end (so the loop closes) ----------------
SEAM = 960
def split_bg(t, glow=0.0):
    img = vellum(); img.paste(AM_I.crop((0, SEAM, W, H)), (0, SEAM)); d = ImageDraw.Draw(img)
    ms_border(d, (40, 70, W - 40, SEAM - 30), t)
    cx_frame(d, (40, SEAM + 20, W - 40, 1500))
    d.rectangle([0, SEAM - 10, W, SEAM + 10], fill=INK)            # the "spine" between the two books
    return img

# ---------------- narration & music ----------------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.26)
n = len(voice); tt = np.arange(n) / SR; music = np.zeros(n, np.float32)
music += (0.010 * (np.sin(2 * np.pi * 73.4 * tt) + 0.6 * np.sin(2 * np.pi * 110 * tt)) * (0.7 + 0.3 * np.sin(2 * np.pi * tt / 6))).astype(np.float32)  # D–A drone
dorian = [293.66, 329.63, 349.23, 392.0, 440.0, 493.88, 523.25, 587.33]
pat = [0, 4, 2, 4, 3, 1, 2, 0, 5, 4, 3, 4, 2, 1, 0, 1]
beat = 0.36
for k in range(int(total / beat)):                                   # plucked lute line in D dorian
    place(music, k * beat, tone(dorian[pat[k % 16]], 0.9, decay=7, harm=(1, 2, 3, 5)), 0.045)
    if k % 2 == 0:                                                   # soft hand drum underneath
        tb = np.arange(int(0.3 * SR)) / SR
        place(music, k * beat, np.sin(2 * np.pi * (90 + 70 * np.exp(-tb * 30)) * tb) * np.exp(-tb * 14), 0.09 if k % 8 == 0 else 0.05)
hook_hit(music, 0.4)
for s in scene_starts(spec): whoosh(music, s, gain=0.14)
whoosh(music, spec["lines"][0]["_s"] + 1.4, gain=0.1)
end_ln = spec["lines"][-1]
place(music, end_ln["_s"] + end_ln["scene"].get("click_at", 0.75), tone(880, 0.8, decay=5, harm=(1, 2, 3)), 0.12)   # TRUE chime
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.35)

# ---------------- scenes ----------------
def sc_hook(sc, lt, dur, t):
    img = split_bg(t); d = ImageDraw.Draw(img)
    dropcap(img, "O", 110, 150, 250, t, bg=BLUE, frak=False)
    gold_text(img, "XFORD", 196, 650, 170, t)                       # illuminated initial + gold leaf
    rubric(img, "UNIVERSITY", 64, 650, 390, col=INK)
    pu = 1.0 if lt < 1.3 else 0.82 + 0.18 * back((lt - 1.3) / 0.35)   # ribbon punches as "older" is spoken
    ribbon(img, "IS OLDER THAN", 116, W / 2, 700, u=pu)
    flat_text(img, "THE AZTEC", 132, W / 2, 1090, fill=CREAM, block=TERRA)
    flat_text(img, "EMPIRE", 132, W / 2, 1270, fill=CREAM, block=TURQ)
    pulse = 1 + 0.03 * math.sin(lt * 5)
    if lt > 0.0:                                                      # gentle push-in keeps frame 0 static-sharp
        z = 1 + 0.04 * ease(lt / max(1.0, dur))
        img = img.resize((int(W * z), int(H * z)), Image.BICUBIC).crop((int((W * z - W) / 2), int((H * z - H) / 2), int((W * z - W) / 2) + W, int((H * z - H) / 2) + H))
    return img

def sc_rubric(sc, lt, dur, t):
    img = vellum(); d = ImageDraw.Draw(img); ms_border(d, (40, 70, W - 40, 1500), t)
    dropcap(img, "N", W / 2 - 150, 230, 300, t, bg=RED)
    acc = sc.get("accent", {})
    for i, txt in enumerate(sc["lines"]):
        u = eout((lt - 0.05 - i * 0.3) / 0.3)
        if str(i) in acc: gold_text(img, txt, 128, W / 2, 680 + i * 180 + (1 - u) * 40, t, u=u)
        else: rubric(img, txt, 128, W / 2, 680 + i * 180, col=INK, u=u)
    for k in range(4):                                               # faint body text of the page
        d.text((150, 1110 + k * 80), TEXTUS[k + 2], font=F(50, True), fill=(160, 136, 104))
    return img

TEXTUS = ["Universitas magistrorum et", "scholarium Oxonie legit et", "docet artes liberales:", "grammatica, rhetorica, logica,", "arithmetica, geometria,", "musica et astronomia."]
def sc_scriptorium(sc, lt, dur, t):
    img = vellum(); d = ImageDraw.Draw(img); ms_border(d, (40, 70, W - 40, 1500), t)
    rubric(img, sc.get("label", ""), 70, W / 2, 190, u=eout((lt - 0.1) / 0.3))
    s = 0.7 + 0.3 * back((lt - 0.05) / 0.45)
    gold_text(img, sc["year"], int(300 * s), W / 2, 330 + (1 - s) * 150, t)
    rubric(img, "BY", 60, W / 2, 300, col=RED, u=eout(lt / 0.25))
    # lines of script being written by a quill
    p = ease((lt - 0.3) / max(0.8, dur - 0.3)) * 6
    qx, qy = 160, 840
    for k in range(6):
        y = 800 + k * 96
        f = min(1.0, max(0.0, p - k))
        if f <= 0: continue
        txt = TEXTUS[k]; lay = Image.new("L", (W - 300, 90), 0); ImageDraw.Draw(lay).text((0, 0), txt, font=F(54, True), fill=255)
        end = int((W - 300) * f); m = lay.crop((0, 0, end, 90))
        img.paste(Image.new("RGB", (end, 90), RED if k == 0 else INK), (150, y - 40), m); d = ImageDraw.Draw(img)
        qx, qy = 150 + end, y + 6
    quill(d, min(qx, W - 260), qy, 0.9)
    return img

def sc_lake(sc, lt, dur, t):
    img = amate(); d = ImageDraw.Draw(img); cx_frame(d, (40, 70, W - 40, 1500))
    flat_text(img, sc["year"], 230, W / 2, 200, fill=CREAM, block=TERRA, u=eout((lt + 0.05) / 0.35))
    waves(d, (110, 640, W - 110, 1300), t)
    gu = back((lt - 0.4) / 0.5)
    if gu > 0:                                                       # island + reeds rise from the lake
        ix, iy = W / 2 + 120, 980
        d.ellipse([ix - 170 * gu, iy - 70 * gu, ix + 170 * gu, iy + 70 * gu], fill=OCHRE, outline=BLACK, width=7)
        for k in range(5):
            rx = ix - 100 + k * 50
            d.line([(rx, iy - 20), (rx + 8 * math.sin(t * 2 + k), iy - 20 - 90 * gu)], fill=(70, 120, 50), width=9)
            d.ellipse([rx - 10, iy - 30 - 90 * gu, rx + 10, iy - 10 - 90 * gu], fill=TERRA, outline=BLACK, width=3)
    steps = int(max(0, (lt - 0.6) / 0.28))                           # codex footprints walk to the island
    for k in range(min(steps, 7)):
        x = 120 + k * 70; y = 1420 - k * 64 - (k % 2) * 20
        if k >= 4: x = 170 + k * 72; y = 1180 - (k - 4) * 60
        foot(d, x, y, 0.9, k % 2 == 0)
    rubric_u = eout((lt - 1.0) / 0.35)
    flat_text(img, sc.get("label", ""), 66, W / 2, 500, fill=BLACK, block=CREAM, u=rubric_u, pad=22)
    return img

def sc_alliance(sc, lt, dur, t):
    img = amate(); d = ImageDraw.Draw(img); cx_frame(d, (40, 70, W - 40, 1500))
    flat_text(img, sc["year"], 260, W / 2, 190, fill=CREAM, block=TURQ, u=eout((lt + 0.05) / 0.35))
    xs = [230, W / 2, W - 230]; cols = [(92, 150, 70), OCHRE, TERRA]
    on = [back((lt - 0.25 - i * 0.35) / 0.4) for i in range(3)]
    j = ease((lt - 1.4) / 0.6)
    if j > 0:                                                        # binding cord joins the three places
        d.line([(xs[0], 1060), (xs[0] + (xs[2] - xs[0]) * j, 1060)], fill=BLACK, width=22)
        d.line([(xs[0], 1060), (xs[0] + (xs[2] - xs[0]) * j, 1060)], fill=CREAM, width=10)
    for i in range(3):
        if on[i] > 0: hill(d, xs[i], 1000, 1.05 * on[i], cols[i])
    flat_text(img, sc.get("label", ""), 66, W / 2, 1200, fill=BLACK, block=CREAM, u=eout((lt - 1.5) / 0.35), pad=22)
    flat_text(img, "AZTEC EMPIRE", 96, W / 2, 560, fill=CREAM, block=TERRA, u=eout((lt - 0.15) / 0.35))
    return img

def sc_gap(sc, lt, dur, t):
    img = split_bg(t); d = ImageDraw.Draw(img)
    a, b = sc["from"], sc["to"]
    gold_text(img, str(a), 170, W / 2, 140, t)
    rubric(img, "OXFORD TEACHING", 58, W / 2, 330, col=RED)
    flat_text(img, str(b), 150, W / 2, 1260, fill=CREAM, block=TURQ)
    flat_text(img, "AZTEC EMPIRE", 60, W / 2, 1130, fill=BLACK, block=CREAM, pad=18)
    u = ease((lt - 0.2) / 1.3); n_ = int(round((b - a) * u))
    # vertical timeline crossing the spine
    y0, y1 = 470, 1100; yc = y0 + (y1 - y0) * u
    d.line([(150, y0), (150, y1)], fill=INK, width=6)
    d.line([(150, y0), (150, yc)], fill=GOLD_D, width=18)
    for k in range(0, 9): d.line([(132, y0 + k * (y1 - y0) / 8), (168, y0 + k * (y1 - y0) / 8)], fill=INK, width=4)
    d.ellipse([150 - 20, yc - 20, 150 + 20, yc + 20], fill=RED, outline=INK, width=4)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle([220, 520, W - 100, 900], 30, fill=CREAM + (235,), outline=INK, width=6)
    img.paste(lay, (0, 0), lay); d = ImageDraw.Draw(img)
    d.text((W / 2 + 60, 670), f"{n_}", font=F(240), fill=RED, anchor="mm", stroke_width=5, stroke_fill=INK)
    d.text((W / 2 + 60, 840), "YEARS LATER", font=F(70), fill=INK, anchor="mm")
    return img

def sc_today(sc, lt, dur, t):
    img = split_bg(t); d = ImageDraw.Draw(img)
    gold_text(img, "1096", 150, W / 2, 140, t)
    rubric(img, "TO", 60, W / 2, 310, col=RED)
    s = 0.6 + 0.4 * back((lt - 0.8) / 0.5) if lt > 0.8 else 0
    if s > 0: gold_text(img, "TODAY", int(190 * s), W / 2, 400 + (1 - s) * 80, t)
    if lt > 2.4: ribbon(img, "STILL TEACHING", 84, W / 2, 790, u=eout((lt - 2.4) / 0.35), fill=BLUE)
    flat_text(img, "1428 TO 1521", 104, W / 2, 1080, fill=CREAM, block=TERRA, u=eout((lt + 0.05) / 0.3))
    fu = ease((lt - 0.9) / 0.5)
    if fu > 0:                                                      # codex half dims as the empire falls
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rectangle([40, SEAM + 20, W - 40, 1500], fill=(20, 14, 10, int(120 * fu)))
        img.paste(sh, (0, 0), sh); d = ImageDraw.Draw(img)
        flat_text(img, "EMPIRE FALLS", 92, W / 2, 1270, fill=CREAM, block=BLACK, u=fu)
    return img

def sc_end(sc, lt, dur, t):
    img = split_bg(t); d = ImageDraw.Draw(img)
    click = sc.get("click_at", 0.75); on = ease((lt - click) / 0.3)
    rubric(img, "SOUNDS FAKE?", 120, W / 2, 230, col=INK, u=eout((lt + 0.05) / 0.3))
    if lt > click: gold_text(img, "IT'S TRUE.", 150, W / 2, 470, t, u=eout((lt - click) / 0.3))
    # switch straddles the spine: vellum-gold on TRUE, codex-terracotta on FAKE
    cx, cy, w_, h_ = W / 2, SEAM, 470, 180
    tr = tuple(int(TERRA[i] * (1 - on) + GOLD[i] * on) for i in range(3))
    d.rounded_rectangle([cx - w_ / 2 + 10, cy - h_ / 2 + 12, cx + w_ / 2 + 10, cy + h_ / 2 + 12], h_ // 2, fill=BLACK)
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=tr, outline=BLACK, width=8)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; r = h_ / 2 - 16
    d.ellipse([kx - r, cy - r, kx + r, cy + r], fill=RED, outline=INK, width=6)               # wax seal knob
    for k in range(10):
        a = k * math.pi / 5; d.ellipse([kx + (r - 4) * math.cos(a) - 12, cy + (r - 4) * math.sin(a) - 12, kx + (r - 4) * math.cos(a) + 12, cy + (r - 4) * math.sin(a) + 12], fill=RED)
    d.ellipse([kx - r * 0.55, cy - r * 0.55, kx + r * 0.55, cy + r * 0.55], outline=(120, 20, 14), width=6)
    lab_y = cy + h_ / 2 + 40
    flat_text(img, "FAKE", 84, cx - w_ / 2 + 60, lab_y + 40, fill=CREAM if on < 0.5 else (180, 160, 130), block=None)
    d.text((cx + w_ / 2 - 60, cy - h_ / 2 - 30), "TRUE", font=F(84), fill=GOLD_D if on >= 0.5 else (170, 150, 120), anchor="md", stroke_width=3, stroke_fill=INK if on >= 0.5 else (170, 150, 120))
    flat_text(img, "FOLLOW FOR MORE", 74, W / 2, 1300, fill=CREAM, block=TURQ, u=eout((lt - click - 0.3) / 0.3))
    return img

SCENES = dict(hook=sc_hook, rubric=sc_rubric, scriptorium=sc_scriptorium, lake=sc_lake, alliance=sc_alliance,
              gap=sc_gap, today=sc_today, end=sc_end)

# ---------------- captions: vellum strip, black ink, current word in vermilion ----------------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 76
    while d.textlength(" ".join(ws), font=F(size)) > W - 200 and size > 44: size -= 4
    f = F(size); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1585
    d.rectangle([x - 38 + 8, y - 22 + 8, x + tw + 38 + 8, y + size + 30 + 8], fill=INK)
    d.rectangle([x - 38, y - 22, x + tw + 38, y + size + 30], fill=CREAM, outline=INK, width=5)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=RED if on else INK)
        x += d.textlength(w + " ", font=f)

def scene_img(ln, t):
    lt = t - ln["_s"]; dur = ln["_se"] - ln["_s"]
    return SCENES[ln["scene"]["type"]](ln["scene"], max(lt, 0.0), dur, t)

TURN = 0.32
def frame(t, fi):
    lines = spec["lines"]; ln = active_line(spec, t)
    if ln is None: ln = lines[0]
    img = scene_img(ln, t)
    i = lines.index(ln); lt = t - ln["_s"]
    if i > 0 and lt < TURN:                                          # page turn: new page sweeps in from the right
        old = scene_img(lines[i - 1], t); u = ease(lt / TURN); edge = int(W * (1 - u))
        a = np.asarray(old).copy(); b = np.asarray(img)
        a[:, edge:] = b[:, edge:]
        sw = 70
        if edge > 0:                                                 # shadow cast onto the old page + curl highlight
            x0 = max(0, edge - sw); g = np.linspace(1, 0.55, edge - x0)[None, :, None]
            a[:, x0:edge] = (a[:, x0:edge] * g).astype(np.uint8)
            x1 = min(W, edge + 26); a[:, edge:x1] = np.clip(a[:, edge:x1].astype(np.int16) + 45, 0, 255).astype(np.uint8)
        img = Image.fromarray(a)
    caption(img, t)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 14, W, H], fill=INK); d.rectangle([0, H - 12, int(W * t / total), H - 2], fill=GOLD)
    return img.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","):
            Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{l['_s']:.2f}" for l in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path)
        print(f"done {total:.1f}s")
