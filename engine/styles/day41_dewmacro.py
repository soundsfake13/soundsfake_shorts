"""Day 41 — DEW-MACRO style (spider silk is stronger than steel, by weight).
A macro lens at dawn: out-of-focus foliage and sun bokeh (round discs with bright rims), silver silk threads with a warm
glow, refracting dew drops with specular highlights and caustic crescents, shallow depth of field on the orb web,
rack-focus transitions between scenes, quiet camera readouts. Instrument Serif titles + Inter Display labels.
Ending: a dew drop slides along a silk thread from FAKE to TRUE. Music: kalimba arpeggio + warm pad + water plips.
Usage: python3 engine/styles/day41_dewmacro.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
INTER = "/usr/share/fonts/opentype/inter"
_F = {}
def F(kind, s):
    k = (kind, int(s))
    if k not in _F:
        path = {"serif": f"{FONTS}/InstrumentSerif-Regular.ttf", "ital": f"{FONTS}/InstrumentSerif-Italic.ttf",
                "bold": f"{INTER}/InterDisplay-Bold.otf", "semi": f"{INTER}/InterDisplay-SemiBold.otf"}[kind]
        _F[k] = ImageFont.truetype(path, int(s))
    return _F[k]

CREAM, GOLD, SILK, DARK, MOSS, AMBER = (250, 244, 228), (255, 204, 120), (238, 242, 236), (8, 22, 20), (60, 96, 70), (255, 170, 90)
PAD = 240                                                                   # extra width for slow drift

# ---------- backgrounds: soft bokeh, generated once ----------
def bokeh_bg(seed, top, bot, discs, sun=(0.82, 0.12), sun_col=(255, 196, 120), sun_r=520):
    w, h = W + PAD, H; r = random.Random(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    g = (yy / h)[..., None]; img = np.array(top, np.float32) * (1 - g) + np.array(bot, np.float32) * g
    d2 = ((xx - sun[0] * w) ** 2 + (yy - sun[1] * h) ** 2) / sun_r ** 2
    img += np.array(sun_col, np.float32) * (np.exp(-d2) * 0.55)[..., None]
    for (n, rmin, rmax, cols, inten, yband) in discs:
        for _ in range(n):
            R = r.uniform(rmin, rmax); cx = r.uniform(-R, w + R); cy = r.uniform(yband[0], yband[1]) * h
            c = np.array(r.choice(cols), np.float32) * r.uniform(0.5, 1.0) * inten
            x0, x1, y0, y1 = int(max(0, cx - R - 3)), int(min(w, cx + R + 3)), int(max(0, cy - R - 3)), int(min(h, cy + R + 3))
            if x0 >= x1 or y0 >= y1: continue
            dd = np.sqrt((xx[y0:y1, x0:x1] - cx) ** 2 + (yy[y0:y1, x0:x1] - cy) ** 2)
            m = np.clip((R - dd) / 2.5, 0, 1); rim = np.exp(-((R - dd) / (0.1 * R)) ** 2) * m
            img[y0:y1, x0:x1] += c * (0.45 * m + 0.5 * rim)[..., None]
    img += np.random.default_rng(seed).normal(0, 2.2, (h, w, 1))
    out = Image.fromarray(img.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))
    return out
DAWN_COLS = [(255, 210, 140), (230, 190, 110), (170, 200, 120), (120, 170, 120), (255, 230, 190)]
BG_DAWN = bokeh_bg(41, (14, 40, 34), (6, 18, 16),
                   [(9, 110, 220, DAWN_COLS, 0.28, (-0.05, 1.05)), (34, 30, 90, DAWN_COLS, 0.5, (-0.05, 1.05)), (30, 12, 28, [(255, 236, 200)], 0.7, (0, 0.6))])
BG_RIVER = bokeh_bg(7, (20, 44, 52), (8, 26, 34),
                    [(14, 90, 200, [(110, 160, 140), (80, 130, 120)], 0.35, (-0.05, 0.4)),
                     (60, 10, 34, [(255, 214, 150), (255, 240, 210)], 0.8, (0.52, 0.8)),
                     (20, 40, 100, [(140, 190, 200)], 0.3, (0.5, 1.0))], sun=(0.25, 0.42), sun_col=(255, 180, 110), sun_r=600)
# river: water band + defocused banks in the foreground
def _river():
    im = BG_RIVER.copy(); m = Image.new("L", im.size, 0); d = ImageDraw.Draw(m)
    d.polygon([(0, 1060), (260, 1120), (420, 1300), (380, 1920), (0, 1920)], fill=255)
    d.polygon([(W + PAD, 980), (W + PAD - 330, 1040), (W + PAD - 470, 1260), (W + PAD - 400, 1920), (W + PAD, 1920)], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(22))
    band = Image.new("L", im.size, 0); ImageDraw.Draw(band).rectangle([0, 980, W + PAD, 1500], fill=70); band = band.filter(ImageFilter.GaussianBlur(60))
    im = Image.composite(Image.new("RGB", im.size, (110, 150, 150)), im, band)
    return Image.composite(Image.new("RGB", im.size, (10, 20, 14)), im, m)
BG_RIVER = _river()

def bg(kind, t):
    src = BG_RIVER if kind == "river" else BG_DAWN
    x = int((t * 7) % PAD) if kind != "river" else int(PAD / 2 + 40 * math.sin(t * 0.3))
    return src.crop((x, 0, x + W, H)).convert("RGBA")

# ---------- sprites ----------
_DROP = {}
def drop_sprite(r, tint=(160, 196, 150)):
    r = max(3, int(r)); k = (r, tint)
    if k in _DROP: return _DROP[k]
    s = 2 * r + 6; yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    u, v = (xx - s / 2) / r, (yy - s / 2) / r; rho = np.sqrt(u * u + v * v)
    edge = np.clip((1 - rho) * r / 1.2, 0, 1)
    shade = np.clip(1 - rho ** 4, 0, 1)
    col = np.array((16, 28, 24), np.float32) * (1 - shade)[..., None] + np.array(tint, np.float32) * (0.85 * shade)[..., None]
    cres = np.exp(-((v - 0.58) / 0.17) ** 2) * np.exp(-(u / 0.55) ** 2) * (rho < 0.96)
    col = col * (1 - 0.6 * cres)[..., None] + np.array((255, 200, 130), np.float32) * (cres * 0.75)[..., None]
    sp = np.exp(-((u + 0.36) ** 2 + (v + 0.42) ** 2) / 0.014) + 0.6 * np.exp(-((u - 0.3) ** 2 + (v + 0.15) ** 2) / 0.004)
    col += 255 * sp[..., None]
    a = edge * (0.74 + 0.26 * rho ** 2) + sp * edge
    arr = np.dstack([col.clip(0, 255), (a.clip(0, 1) * 255)]).astype(np.uint8)
    _DROP[k] = Image.fromarray(arr, "RGBA"); return _DROP[k]
def put_drop(img, x, y, r, tint=(160, 196, 150)):
    sp = drop_sprite(r, tint); img.alpha_composite(sp, (int(x - sp.width / 2), int(y - sp.height / 2)))

def _star():
    s = 121; yy, xx = np.mgrid[0:s, 0:s].astype(np.float32) - s // 2
    a = np.exp(-(xx ** 2) / 3) * np.exp(-np.abs(yy) / 16) + np.exp(-(yy ** 2) / 3) * np.exp(-np.abs(xx) / 16) + np.exp(-(xx ** 2 + yy ** 2) / 40)
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "L")
STAR = _star()
def twinkle(img, x, y, k):
    if k <= 0.02: return
    sz = int(121 * (0.5 + 0.7 * k)); st = STAR.resize((sz, sz)).point(lambda p: int(p * min(1, k)))
    lay = Image.new("RGBA", (sz, sz), (255, 246, 220, 0)); lay.putalpha(st)
    img.alpha_composite(lay, (int(x - sz / 2), int(y - sz / 2)))

# ---------- silk threads (2x supersampled, glowing) ----------
def silk(img, polys, width=2.5, col=SILK, glow=0.7, glow_col=(255, 210, 150)):
    pts = [p for poly in polys for p in poly]
    if not pts: return
    x0 = max(0, int(min(p[0] for p in pts)) - 24); x1 = min(W, int(max(p[0] for p in pts)) + 24)
    y0 = max(0, int(min(p[1] for p in pts)) - 24); y1 = min(H, int(max(p[1] for p in pts)) + 24)
    if x1 <= x0 or y1 <= y0: return
    m = Image.new("L", ((x1 - x0) * 2, (y1 - y0) * 2), 0); d = ImageDraw.Draw(m)
    for poly in polys:
        if len(poly) > 1: d.line([((x - x0) * 2, (y - y0) * 2) for x, y in poly], fill=255, width=max(1, int(width * 2)), joint="curve")
    m = m.resize((x1 - x0, y1 - y0), Image.BOX)
    reg = img.crop((x0, y0, x1, y1))
    if glow:
        gm = m.filter(ImageFilter.GaussianBlur(7)).point(lambda p: int(min(255, p * glow * 2.2)))
        reg = Image.composite(Image.new("RGBA", reg.size, glow_col + (255,)), reg, gm)
    reg = Image.composite(Image.new("RGBA", reg.size, tuple(col) + (255,)), reg, m)
    img.paste(reg, (x0, y0))

def sag(p0, p1, s=30, n=24):
    return [(p0[0] + (p1[0] - p0[0]) * i / n, p0[1] + (p1[1] - p0[1]) * i / n + s * math.sin(math.pi * i / n)) for i in range(n + 1)]

# ---------- orb web layer with shallow depth of field (hook + end) ----------
def _web():
    hub = (760, 1180); r = random.Random(41); S = 2
    m = Image.new("L", (W * S, H * S), 0); d = ImageDraw.Draw(m)
    n = 18; angs = [2 * math.pi * i / n + r.uniform(-0.08, 0.08) for i in range(n)]
    for a in angs: d.line([(hub[0] * S, hub[1] * S), ((hub[0] + 2200 * math.cos(a)) * S, (hub[1] + 2200 * math.sin(a)) * S)], fill=200, width=3)
    drops = []
    rad = 70
    while rad < 1500:
        for i in range(n):
            a0, a1 = angs[i], angs[(i + 1) % n] + (2 * math.pi if i == n - 1 else 0)
            p0 = (hub[0] + rad * math.cos(a0), hub[1] + rad * math.sin(a0)); p1 = (hub[0] + (rad + 6) * math.cos(a1), hub[1] + (rad + 6) * math.sin(a1))
            pts = sag(p0, p1, 4 + rad * 0.012, 8)
            d.line([(x * S, y * S) for x, y in pts], fill=230, width=3)
            for _ in range(r.randint(0, 3)):
                k = r.randint(1, 7); drops.append((pts[k][0], pts[k][1] + 2, r.uniform(3, 7 + rad * 0.006)))
        rad += 44 + rad * 0.07
    m = m.resize((W, H), Image.BOX)
    lay = Image.new("RGBA", (W, H), SILK + (0,)); lay.putalpha(m)
    glow = Image.new("RGBA", (W, H), (255, 214, 160, 0)); glow.putalpha(m.filter(ImageFilter.GaussianBlur(8)).point(lambda p: min(255, p * 2)))
    sharp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sharp.alpha_composite(glow); sharp.alpha_composite(lay)
    for (x, y, rr) in drops:
        if -20 < x < W + 20 and -20 < y < H + 20: put_drop(sharp, x, y, rr)
    blur = sharp.filter(ImageFilter.GaussianBlur(9))
    yy = np.arange(H, dtype=np.float32); f = np.clip(1 - np.abs(yy - 1150) / 380, 0, 1) ** 0.8   # focus band
    mask = Image.fromarray(np.tile((f * 255).astype(np.uint8)[:, None], (1, W)), "L")
    return Image.composite(sharp, blur, mask), [(x, y, rr) for (x, y, rr) in drops if rr > 8 and 950 < y < 1400 and 0 < x < W]
WEB, WEB_DROPS = _web()

# ---------- text ----------
def label(img, s, font, x, y, fill=CREAM, alpha=1.0, anchor="mm", shadow=0.75, track=0):
    if alpha <= 0.01: return
    if track:
        s = " ".join(s) if track > 1 else s
    bb = font.getbbox(s, anchor=anchor); pad = 40
    w_, h_ = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    ox, oy = int(x + bb[0] - pad), int(y + bb[1] - pad)
    m = Image.new("L", (w_, h_), 0); ImageDraw.Draw(m).text((x - ox, y - oy), s, font=font, fill=255, anchor=anchor)
    patch = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    if shadow:
        sh = m.filter(ImageFilter.GaussianBlur(12)).point(lambda p: int(p * shadow * alpha))
        patch = Image.composite(Image.new("RGBA", (w_, h_), (4, 12, 10, 255)), patch, sh); patch.putalpha(sh)
    tl = Image.new("RGBA", (w_, h_), tuple(fill) + (255,)); tl.putalpha(m.point(lambda p: int(p * alpha)))
    patch.alpha_composite(tl); img.alpha_composite(patch, (ox, oy))
def fit(s, kind, size, maxw=W - 140):
    while F(kind, size).getlength(s) > maxw and size > 30: size -= 4
    return F(kind, size)
def title2(img, a, b, lt, y=300, size=150, delay=0.0, instant=False):
    """two-line serif title: roman line + italic gold line, rising in."""
    for i, (s, kind, col) in enumerate([(a, "serif", CREAM), (b, "ital", GOLD)]):
        if not s: continue
        u = 1.0 if instant else eout((lt - delay - 0.12 * i) / 0.45)
        label(img, s, fit(s, kind, size), W / 2, y + i * size * 0.98 + 30 * (1 - u), col, u)
def pill(img, s, y, alpha=1.0, fg=DARK, bgc=GOLD, size=42):
    if alpha <= 0.01: return
    f = F("bold", size); s = s.upper(); tw = f.getlength(s)
    lay = Image.new("RGBA", (W, int(size * 2.2)), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([W / 2 - tw / 2 - 34, 4, W / 2 + tw / 2 + 34, size * 2.2 - 4], int(size), fill=bgc + (int(240 * alpha),))
    d.text((W / 2, size * 1.1), s, font=f, fill=fg + (int(255 * alpha),), anchor="mm")
    img.alpha_composite(lay, (0, int(y - size * 1.1)))
def readout(img, t):
    d = ImageDraw.Draw(img); f = F("semi", 28)
    d.text((70, 92), "1:1  MACRO", font=f, fill=(250, 244, 228, 150), anchor="lm")
    d.text((W - 70, 92), "f/2.8   ISO 100", font=f, fill=(250, 244, 228, 150), anchor="rm")
    if int(t * 2) % 2 == 0: d.ellipse([W - 70 - f.getlength("f/2.8   ISO 100") - 34, 84, W - 70 - f.getlength("f/2.8   ISO 100") - 18, 100], fill=(255, 120, 90, 200))
def brackets(img, cx, cy, r, alpha=0.8, col=(250, 244, 228)):
    d = ImageDraw.Draw(img); c = col + (int(255 * alpha),); L = r * 0.35
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = cx + sx * r, cy + sy * r
            d.line([(x, y), (x - sx * L, y)], fill=c, width=4); d.line([(x, y), (x, y - sy * L)], fill=c, width=4)

# ---------- scenes ----------
HERO = (470, 1180, 140)
def S_hook(sc, lt, dur, t):
    img = bg("dawn", t); img.alpha_composite(WEB)
    hx, hy, hr = HERO
    silk(img, [sag((-20, 1000), (W + 20, 1330), 30)], 3.2, glow=0.9)
    put_drop(img, hx, hy + 6 * math.sin(t * 2.2), hr)
    for k, (x, y, rr) in enumerate(WEB_DROPS[:14]):
        twinkle(img, x - rr * 0.35, y - rr * 0.4, 0.9 * max(0, math.sin(t * 2.3 + k * 1.7)) ** 6)
    twinkle(img, hx - hr * 0.36, hy - hr * 0.42, 0.8 + 0.3 * math.sin(t * 3))
    brackets(img, hx, hy + 6 * math.sin(t * 2.2), hr * 1.35 + 6 * math.sin(t * 5), 0.7)
    instant = not sc.get("loop")
    title2(img, "Spider silk", "beats steel.", lt, 300, 168, instant=instant)
    label(img, "POUND FOR POUND", F("semi", 44), W / 2, 640, CREAM, 1.0, track=0)
    if sc.get("loop"):
        pill(img, "wait for the last spider", 1430, eout((lt - 0.3) / 0.4))
    return img

HAIR = None
def _hair():
    w_, h_ = W + 500, 150; yy = (np.arange(h_, dtype=np.float32) - h_ / 2) / (h_ / 2)
    shade = np.clip(1 - yy ** 2, 0, 1) ** 0.5; hl = np.exp(-((yy + 0.35) / 0.12) ** 2)
    col = np.array((70, 42, 22), np.float32) * (1 - shade)[:, None] + np.array((150, 96, 48), np.float32) * shade[:, None] + np.array((255, 214, 160), np.float32) * (0.6 * hl)[:, None]
    arr = np.tile(col[:, None, :], (1, w_, 1))
    xx = np.arange(w_, dtype=np.float32)
    scale = (np.abs(((xx[None, :] + 30 * yy[:, None] ** 2) % 46) - 2) < 2.2) * shade[:, None] * 0.35      # cuticle scales
    arr = arr * (1 - scale[..., None] * 0.45)
    a = (np.clip((1 - np.abs(yy)) * h_ / 4, 0, 1) * 255)[:, None].repeat(w_, 1)
    im = Image.fromarray(np.dstack([arr.clip(0, 255), a]).astype(np.uint8), "RGBA")
    return im.rotate(-9, resample=Image.BICUBIC, expand=True)
HAIR = _hair()
def S_hair(sc, lt, dur, t):
    img = bg("dawn", t + 3)
    u = eout(lt / 0.55); img.alpha_composite(HAIR, (int(-250 - 500 * (1 - u)), int(840 - HAIR.height / 2)))
    v = ease((lt - 0.35) / 0.9); a0, a1 = (-20, 1300), (W + 20, 700)
    if v > 0: silk(img, [[a0, (a0[0] + (a1[0] - a0[0]) * v, a0[1] + (a1[1] - a0[1]) * v)]], 2.2, glow=1.0)
    for k, f_ in enumerate((0.18, 0.62, 0.86)):
        if v > f_: put_drop(img, a0[0] + (a1[0] - a0[0]) * f_, a0[1] + (a1[1] - a0[1]) * f_ + 6, 13 + 5 * k)
    title2(img, "Thinner than", "a human hair", lt, 290, 140)
    d = ImageDraw.Draw(img)
    la = eout((lt - 0.6) / 0.4); lb = eout((lt - 1.3) / 0.4)
    if la > 0:
        d.line([(250, 760), (250, 640 + 40)], fill=CREAM + (int(220 * la),), width=3)
        label(img, "HUMAN HAIR", F("semi", 40), 250, 640, CREAM, la)
    if lb > 0:
        x, y = 820, 1300 - (820 + 20) / (W + 40) * 600 + 8
        d.line([(x, y + 30), (x, 1390)], fill=GOLD + (int(220 * lb),), width=3)
        label(img, "SPIDER SILK", F("semi", 40), x - 40, 1430, GOLD, lb)
    return img

def S_snap(sc, lt, dur, t):
    img = bg("dawn", t + 6); d = ImageDraw.Draw(img)
    title2(img, "For its weight…", "stronger than steel", lt, 220, 120)
    tw = [(40, 610), (300, 598), (600, 606), (900, 595), (1060, 602)]
    d.line(tw, fill=(46, 34, 24, 255), width=30, joint="curve"); d.line([(p[0], p[1] - 9) for p in tw], fill=(92, 70, 48, 255), width=6, joint="curve")
    pill(img, "same weight of material", 485, eout((lt - 0.2) / 0.4), CREAM, (30, 52, 44), 34)
    p = ease((lt - 0.3) / max(1.0, dur - 1.0)); ts = 0.3 + 0.45 * max(1.0, dur - 1.0)
    for side, x, kind in ((0, 300, "steel"), (1, 780, "silk")):
        top = 604
        if kind == "steel" and lt > ts:
            k = lt - ts; fall = 0.5 * 3200 * k * k
            silk(img, [[(x, top), (x + 10 * math.sin(k * 30) * math.exp(-k * 4), top + 90)]], 5, (175, 180, 186), glow=0)
            pr = 34 + 70 * min(p, 0.45)
            if 1100 + fall < H + 200:
                silk(img, [[(x, 760 + fall), (x, 1080 + fall)]], 5, (175, 180, 186), glow=0)
                put_drop(img, x, 1080 + fall + pr, pr)
            label(img, "SNAP!", F("ital", 110), x, 1200, (255, 140, 110), eout(k / 0.2) * (1 if k < 1.2 else max(0, 1 - (k - 1.2) * 2)))
        else:
            pr = 34 + 70 * p; L = 1080 + 40 * p
            if kind == "steel": silk(img, [[(x, top), (x, L)]], 5, (175, 180, 186), glow=0)
            else: silk(img, [[(x, top), (x, L)]], 2.6, glow=1.0)
            put_drop(img, x, L + pr - 6, pr)
            if kind == "silk": twinkle(img, x - pr * 0.36, L + pr - 6 - pr * 0.42, 0.6 + 0.4 * math.sin(t * 4))
    label(img, "STEEL WIRE", F("semi", 38), 300, 1335, (200, 206, 210), 1.0); label(img, "SPIDER SILK", F("semi", 38), 780, 1335, GOLD, 1.0)
    if lt > ts + 0.7: pill(img, "silk still holding", 1440, eout((lt - ts - 0.7) / 0.35))
    return img

def S_stretch(sc, lt, dur, t):
    img = bg("dawn", t + 9); d = ImageDraw.Draw(img)
    k = 1 + 3 * ease((lt - 0.3) / max(1.2, dur - 1.0))
    title2(img, "Stretch it up to", "", lt, 270, 120)
    label(img, f"{k:.1f}×", F("ital", 300), W / 2, 560, GOLD, 1.0)
    x0, y0 = 130, 1040; x1 = x0 + 205 * k
    d.line([(x0, 860), (x0 - 20, 1240)], fill=(46, 34, 24, 255), width=28)
    d.line([(x1 + 6, 900), (x1 + 30, 1220)], fill=(46, 34, 24, 255), width=24)
    silk(img, [sag((x0, y0), (x1, y0), 10 / k, 30)], max(1.4, 4.2 / math.sqrt(k)), glow=0.9)
    for i in range(5):
        f_ = (i + 0.5) / 5; put_drop(img, x0 + (x1 - x0) * f_, y0 + 10 / k * math.sin(math.pi * f_) + 9, 14)
    for n in range(1, 5):
        tx = x0 + 205 * n; on = k >= n - 0.02
        d.line([(tx, 1160), (tx, 1200)], fill=(GOLD if on else CREAM) + (255 if on else 120,), width=4)
        label(img, f"{n}×", F("semi", 40), tx, 1250, GOLD if on else CREAM, 1.0 if on else 0.45)
    d.line([(x0, 1180), (x0 + 820, 1180)], fill=CREAM + (120,), width=2)
    if k > 3.95: pill(img, "and it doesn't break", 1430, eout((lt - (0.3 + max(1.2, dur - 1.0))) / 0.3))
    return img

def spider(d, x, y, s=1.0):
    c = (22, 18, 14, 255)
    for i in range(4):
        for sx in (-1, 1):
            a = math.radians(-60 + i * 38); kx = x + sx * 26 * s * math.cos(a); ky = y + 26 * s * math.sin(a) - 4 * s
            ex = x + sx * 52 * s * math.cos(a * 0.8); ey = y + 46 * s * math.sin(a) + 16 * s
            d.line([(x, y), (kx, ky - 10 * s), (ex, ey)], fill=c, width=max(2, int(4 * s)))
    d.ellipse([x - 12 * s, y - 22 * s, x + 12 * s, y + 2 * s], fill=c); d.ellipse([x - 17 * s, y - 2 * s, x + 17 * s, y + 34 * s], fill=c)
def S_river(sc, lt, dur, t):
    img = bg("river", t); d = ImageDraw.Draw(img)
    label(img, "MADAGASCAR", F("semi", 40), W / 2, 210, CREAM, eout(lt / 0.3), track=2)
    title2(img, "Darwin's", "bark spider", lt, 320, 150, delay=0.1)
    L0, L1 = (-10, 800), (W + 10, 760)
    v = ease((lt - 1.0) / 1.4)
    line = sag(L0, L1, 40, 40); n = max(1, int(len(line) * v))
    if v > 0: silk(img, [line[:n + 1]], 3, glow=1.0)
    wv = ease((lt - 2.3) / 1.4); cx, cy = 560, 1080
    if wv > 0:
        polys = []; R = 250 * wv
        for i in range(14):
            a = 2 * math.pi * i / 14; polys.append([(cx, cy), (cx + R * math.cos(a), cy + R * math.sin(a))])
        polys.append([(cx, cy - R), (cx, 818)])
        for rr in np.arange(30, R, 26):
            polys.append([(cx + rr * math.cos(2 * math.pi * j / 14), cy + rr * math.sin(2 * math.pi * j / 14)) for j in range(15)])
        silk(img, polys, 1.6, glow=0.6)
        spider(ImageDraw.Draw(img), cx, cy - 6, 0.9 * wv)
    dv = eout((lt - 3.6) / 0.6)
    if dv > 0:
        c = CREAM + (int(230 * dv),); y = 690
        d.line([(60, y), (W - 60, y)], fill=c, width=3); d.line([(60, y - 18), (60, y + 18)], fill=c, width=3); d.line([(W - 60, y - 18), (W - 60, y + 18)], fill=c, width=3)
        for sx in (60, W - 60):
            dd = 1 if sx == 60 else -1; d.polygon([(sx, y), (sx + dd * 22, y - 10), (sx + dd * 22, y + 10)], fill=c)
        label(img, "up to 25 m", F("ital", 76), W / 2, y - 52, GOLD, dv)
    for k in range(6):
        x = 120 + k * 170; y = 1250 + 40 * math.sin(k * 2.1)
        twinkle(img, x, y, 0.8 * max(0, math.sin(t * 2.7 + k * 1.3)) ** 8)
    return img

def S_kevlar(sc, lt, dur, t):
    img = bg("dawn", t + 12); d = ImageDraw.Draw(img)
    n = 1 + int(9 * ease((lt - 0.1) / 1.0))
    label(img, f"{n}×", F("ital", 400), W / 2, 560, GOLD, 1.0)
    label(img, "TOUGHER THAN KEVLAR", F("semi", 48), W / 2, 860, CREAM, eout((lt - 0.2) / 0.4))
    bx, bw = 130, 820
    label(img, "KEVLAR", F("semi", 36), bx, 1010, CREAM, 1.0, anchor="lm")
    kv = eout((lt - 0.3) / 0.4); kw = bw * 0.1 * kv
    if kw > 2:
        d.rounded_rectangle([bx, 1050, bx + kw, 1110], 10, fill=(206, 166, 64, 255))
        for xx in range(int(bx), int(bx + kw), 12): d.line([(xx, 1052), (xx, 1108)], fill=(160, 124, 40, 255), width=2)
    label(img, "DARWIN'S BARK SPIDER SILK", F("semi", 36), bx, 1200, GOLD, 1.0, anchor="lm")
    sv = ease((lt - 0.4) / 1.1); sw = bw * sv
    if sw > 4:
        silk(img, [[(bx, 1270), (bx + sw, 1270)]], 26, (232, 236, 228), glow=1.0)
        for f_ in np.arange(0.07, sv, 0.12): put_drop(img, bx + bw * f_, 1270, 11)
    if lt > 1.8: label(img, "the toughest biological material known", F("ital", 54), W / 2, 1420, CREAM, eout((lt - 1.8) / 0.4))
    return img

def S_end(sc, lt, dur, t):
    img = bg("dawn", t); img.alpha_composite(WEB)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.32)
    title2(img, "Sounds fake?", "", 0, 330, 160, instant=True)
    y = 700; xa, xb = 340, 720
    silk(img, [sag((-20, y - 10), (W + 20, y - 10), 14)], 3, glow=1.0)
    x = xa + (xb - xa) * on; r = 92
    label(img, "FAKE", F("bold", 60), 140, y, CREAM, 1.0 - 0.6 * on)
    label(img, "TRUE", F("bold", 60), 945, y, GOLD if on > 0.5 else CREAM, 0.4 + 0.6 * on)
    put_drop(img, x, y + 4, r, (200, 210, 150) if on > 0.5 else (160, 196, 150))
    twinkle(img, x - r * 0.36, y + 4 - r * 0.42, 0.7 + 0.5 * on)
    if on > 0.6:
        u = eout((lt - click - 0.25) / 0.4)
        label(img, "It's true.", F("ital", 150), W / 2, 960, GOLD, u)
        label(img, "Follow for more.", F("semi", 56), W / 2, 1120, CREAM, eout((lt - click - 0.45) / 0.4))
    return img

SCENES = dict(hook=S_hook, hair=S_hair, snap=S_snap, stretch=S_stretch, river=S_river, kevlar=S_kevlar, end=S_end)

# ---------- audio: kalimba arpeggio + warm pad + water plips ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32); tt = np.arange(n) / SR
pent = [293.66, 329.63, 369.99, 440.0, 493.88, 587.33, 659.25, 739.99]
pat = [0, 2, 4, 5, 7, 5, 4, 2, 1, 3, 4, 6, 7, 6, 3, 2]
for k in range(int(total / 0.3)):
    place(music, k * 0.3, tone(pent[pat[k % 16]], 1.2, decay=5.5, harm=(1, 3.9, 7.1)), 0.035)
for k, root in enumerate([146.83, 123.47, 110.0, 130.81] * 6):                 # D, B, A, C pads (4 s each)
    s0 = k * 4.0
    if s0 >= total: break
    seg = np.arange(int(4.4 * SR)) / SR; env = np.sin(np.pi * np.clip(seg / 4.4, 0, 1)) ** 1.5
    sig = sum(np.sin(2 * np.pi * root * h * seg) / h for h in (1, 1.5, 2, 3)) * env
    place(music, s0, sig.astype(np.float32), 0.03)
def plip(at, f0=900, gain=0.12):
    s = np.arange(int(0.12 * SR)) / SR; sig = np.sin(2 * np.pi * (f0 + 2200 * s / 0.12) * s) * np.exp(-s * 40)
    place(music, at, sig.astype(np.float32), gain)
hook_hit(music, 0.33); plip(0.02, 700, 0.15)
for s_ in scene_starts(spec): whoosh(music, s_, 0.07); plip(s_ + 0.05, 800, 0.1)
for ln in spec["lines"]:
    if ln["scene"]["type"] == "snap":
        dur_ = ln["_se"] - ln["_s"]; at = ln["_s"] + 0.3 + 0.45 * max(1.0, dur_ - 1.0)
        nz = np.random.default_rng(5).normal(0, 1, int(0.08 * SR)) * np.exp(-np.arange(int(0.08 * SR)) / SR * 60)
        place(music, at, nz.astype(np.float32), 0.35); place(music, at, tone(1400, 0.6, decay=9, harm=(1, 2.3)), 0.12)
    if ln["scene"]["type"] == "end":
        place(music, ln["_s"] + ln["scene"].get("click_at", 0.45), tone(1174.66, 1.5, decay=3, harm=(1, 2, 3)), 0.12)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.35)

# ---------- captions, focus pulls, progress ----------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 70
    while F("bold", size).getlength(" ".join(ws)) > W - 220 and size > 36: size -= 4
    f = F("bold", size); tw = f.getlength(" ".join(ws)); x = (W - tw) / 2; y = 1585
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x - 34, y - 20, x + tw + 34, y + size + 26], 26, fill=(6, 16, 14, 215))
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=GOLD + (255,) if on else (255, 255, 255, 255)); x += f.getlength(w + " ")
    img.alpha_composite(lay)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t)
    li = spec["lines"].index(ln)
    if li > 0 and spec["lines"][li - 1]["scene"]["type"] != ln["scene"]["type"] and lt < 0.4:   # rack focus in
        rad = 14 * (1 - ease(lt / 0.4))
        if rad > 0.5: img = img.filter(ImageFilter.GaussianBlur(rad))
    readout(img, t); caption(img, t)
    d = ImageDraw.Draw(img); d.rectangle([0, H - 8, W, H], fill=(6, 16, 14, 255)); d.rectangle([0, H - 8, int(W * t / total), H], fill=GOLD + (255,))
    return img.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
