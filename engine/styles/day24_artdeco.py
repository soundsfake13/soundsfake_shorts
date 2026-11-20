"""Day 24 — ART-DECO TRAVEL POSTER style (A group of flamingos is called a flamboyance).
A 1930s lagoon travel poster that moves: deep-teal night-to-peach sky split by a slowly turning sunburst, a stepped
deco sun with cut-out bands sinking into the horizon, layered stepped dunes, a teal lagoon of broken gold ripple
lines with a striped sun reflection, and a gold double border with stepped corners. Flamingos are elegant flat
silhouettes (two-tone body, deco feather chevrons on the wing, S-curve neck built from a sampled Bezier tube, two-tone
bill) with striped water reflections; a whole flamboyance stands in a row for the hook. Detail scenes sit in cream
deco arches / gold-rimmed medallions over the dimmed poster: an egg hatching a fluffy grey chick, algae spirals and a
segmented brine shrimp, a chevron feather filling with pink pigment as gold drops fall, an upside-down feeding
flamingo with water chevrons through the bill, three arches with a flamingo growing from grey to pink.
Type: Limelight (deco display, cream with hard teal offset shadow, gold-gradient accent words) + Poiret One (thin
spaced labels). Palette: deep teal, peach, flamingo pink, cream, gold.
Scene changes: 'venetian' deco shutter — horizontal gold-edged teal bands close and open from alternating sides.
Ending: gold-rimmed pill switch whose knob is the deco sun; FAKE (grey) -> TRUE (flamingo pink); last 0.4 s dissolves
back into the hook poster for the loop.
Music: F-major lounge swing (maj7 piano-ish chords, walking plucked bass, brushed swung hats) + harp glissandi on cuts.
Usage: python3 engine/styles/day24_artdeco.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]

TEAL_D = (10, 42, 52); TEAL = (20, 84, 94); TEAL_M = (38, 116, 120); PEACH = (247, 172, 138); SAND = (250, 210, 168)
PINK = (240, 112, 138); PINK_D = (198, 70, 104); PINK_L = (250, 178, 186); CREAM = (247, 237, 216)
GOLD = (212, 168, 82); GOLD_L = (244, 216, 146); GOLD_D = (150, 110, 46); INK = (18, 30, 38)
GREY = (200, 196, 192); GREY_D = (150, 146, 144); GREEN = (70, 146, 116); GREEN_L = (130, 196, 150)
SS = 2; HOR = 1170

_F = {}
def F(size, kind="lime"):
    k = (kind, int(size))
    if k not in _F:
        _F[k] = ImageFont.truetype(f"{FONTS}/{'Limelight-Regular' if kind == 'lime' else 'PoiretOne-Regular'}.ttf", int(size))
    return _F[k]

def mix(a, b, u): u = max(0.0, min(1.0, u)); return tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3))
def S(v): return [x * SS for x in v]
def new(w, h): return Image.new("RGBA", (int(w * SS), int(h * SS)), (0, 0, 0, 0))
def down(im): return im.resize((im.width // SS, im.height // SS), Image.LANCZOS)

def put(base, spr, cx, cy, ang=0.0, al=1.0, sc=1.0):
    if al <= 0.01 or spr is None: return
    if abs(sc - 1) > 0.003: spr = spr.resize((max(1, int(spr.width * sc)), max(1, int(spr.height * sc))), Image.BICUBIC)
    if abs(ang) > 0.05: spr = spr.rotate(ang, resample=Image.BICUBIC, expand=True)
    if al < 0.99:
        spr = spr.copy(); a = np.asarray(spr)[..., 3].astype(np.float32) * al
        spr.putalpha(Image.fromarray(a.astype(np.uint8)))
    x, y = int(round(cx - spr.width / 2)), int(round(cy - spr.height / 2))
    sx0, sy0 = max(0, -x), max(0, -y); sx1, sy1 = min(spr.width, W - x), min(spr.height, H - y)
    if sx1 <= sx0 or sy1 <= sy0: return
    if (sx0, sy0, sx1, sy1) != (0, 0, spr.width, spr.height): spr = spr.crop((sx0, sy0, sx1, sy1))
    base.alpha_composite(spr, (x + sx0, y + sy0))

# ---------- type ----------
_TC = {}
def tsprite(s, size, col=CREAM, kind="lime", shadow=TEAL_D, gold=False, track=0):
    k = (s, int(size), col, kind, shadow, gold, track)
    if k not in _TC:
        f = F(size * SS, kind)
        widths = [f.getlength(c) for c in s]; tw = sum(widths) + track * SS * (len(s) - 1)
        bb = f.getbbox(s); h = bb[3] - bb[1]
        pad = 16 * SS; off = int(max(3, size * 0.06)) * SS
        im = Image.new("RGBA", (int(tw) + 2 * pad + off, h + 2 * pad + off), (0, 0, 0, 0))
        mk = Image.new("L", im.size, 0); dm = ImageDraw.Draw(mk); x = pad
        for c, w_ in zip(s, widths):
            dm.text((x, pad - bb[1]), c, font=f, fill=255); x += w_ + track * SS
        m = np.asarray(mk).astype(np.float32) / 255
        out = np.zeros(im.size[::-1] + (4,), np.float32)
        if shadow:
            sm = np.zeros_like(m); sm[off:, off:] = m[:-off, :-off]
            out[..., :3] = shadow; out[..., 3] = sm
        if gold:
            yy = np.linspace(0, 1, m.shape[0])[:, None]
            g = np.clip(np.abs(yy - 0.42) * 2.2, 0, 1)
            fill = np.stack([GOLD_L[i] * (1 - g) + GOLD[i] * g for i in range(3)], -1)
            fill = np.broadcast_to(fill, m.shape + (3,))
        else:
            fill = np.broadcast_to(np.array(col, np.float32), m.shape + (3,))
        a = m[..., None]
        out[..., :3] = fill * a + out[..., :3] * (1 - a) * (out[..., 3:4] > 0)
        out[..., 3] = np.maximum(out[..., 3], m)
        im = Image.fromarray((out * [1, 1, 1, 255]).clip(0, 255).astype(np.uint8), "RGBA")
        _TC[k] = down(im)
    return _TC[k]
def fit(s, size, maxw=W - 170, kind="lime", track=0):
    while F(size, kind).getlength(s) + track * len(s) > maxw and size > 30: size -= 2
    return size
def title(base, s, size, cy, t0, lt, col=CREAM, gold=False, kind="lime", track=0, maxw=W - 170, d=0.4, al=1.0):
    """slide-up + fade entrance at t0 (scene-local)."""
    size = fit(s, size, maxw, kind, track); u = eout((lt - t0) / d)
    if u <= 0: return
    put(base, tsprite(s, size, col, kind, TEAL_D, gold, track), W / 2, cy + (1 - u) * 50, 0, u * al)

def rule(base, cy, w=520, al=1.0):
    """gold deco rule with a centre diamond and end dots."""
    if al <= 0: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); a = int(255 * al)
    x0, x1 = W / 2 - w / 2, W / 2 + w / 2
    d.line((x0, cy - 5, W / 2 - 26, cy - 5), fill=GOLD + (a,), width=3); d.line((W / 2 + 26, cy - 5, x1, cy - 5), fill=GOLD + (a,), width=3)
    d.line((x0 + 30, cy + 5, W / 2 - 26, cy + 5), fill=GOLD + (a,), width=2); d.line((W / 2 + 26, cy + 5, x1 - 30, cy + 5), fill=GOLD + (a,), width=2)
    d.polygon([(W / 2, cy - 16), (W / 2 + 16, cy), (W / 2, cy + 16), (W / 2 - 16, cy)], fill=GOLD_L + (a,))
    for x in (x0 - 10, x1 + 10): d.ellipse((x - 5, cy - 10, x + 5, cy), fill=GOLD + (a,))
    base.alpha_composite(lay)

# ---------- poster background ----------
def make_sky():
    v = np.linspace(0, 1, HOR, dtype=np.float32)[:, None]
    u = np.clip((v - 0.30) / 0.70, 0, 1) ** 1.4
    cols = [TEAL_D, (40, 70, 92), (150, 96, 112), PEACH, SAND]
    stops = [0, 0.3, 0.62, 0.88, 1.0]
    r = np.interp(u, stops, [c[0] for c in cols]); g = np.interp(u, stops, [c[1] for c in cols]); b = np.interp(u, stops, [c[2] for c in cols])
    a = np.stack([r, g, b], -1)[:, 0, :][:, None, :].repeat(W, 1)
    return a.astype(np.float32)
SKY = make_sky()

def make_water():
    h = 1500 - HOR; v = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    top = np.array(TEAL_M, np.float32); bot = np.array(TEAL_D, np.float32)
    a = np.broadcast_to(top * (1 - v) + bot * v, (h, W, 3)).copy()
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA")
WATER = make_water()

def dunes_layer():
    im = new(W, 300); d = ImageDraw.Draw(im)
    # far stepped dunes then near ones (deco stepped tops)
    for col, base_y, steps, seed in (((70, 92, 110), 210, 7, 3), ((34, 74, 86), 250, 5, 9)):
        rr = random.Random(seed); pts = [(0, 300)]; x = 0; y = base_y - rr.uniform(20, 60)
        while x < W:
            w_ = rr.uniform(90, 200); pts += [(x, y), (x + w_ * 0.5, y - rr.uniform(10, 40))]; x += w_; y = base_y - rr.uniform(0, 70)
            pts += [(x - w_ * 0.2, y)]
        pts += [(W, y), (W, 300)]
        d.polygon([(px * SS, py * SS) for px, py in pts], fill=col + (255,))
    return down(im)
DUNES = dunes_layer()

def sun_spr(R=230):
    im = new(2 * R + 4, 2 * R + 4); d = ImageDraw.Draw(im); c = R + 2
    for k, (rr_, col) in enumerate(((R, (250, 200, 150)), (R * 0.82, (252, 214, 166)), (R * 0.64, (253, 228, 182)))):
        d.ellipse(S((c - rr_, c - rr_, c + rr_, c + rr_)), fill=col + (255,))
    # deco cut-out bands across the lower half
    for i in range(6):
        y = c + 18 + i * (R / 6.2); th = 4 + i * 2.6
        d.rectangle(S((0, y, 2 * R + 4, y + th)), fill=(0, 0, 0, 0))
    return down(im)
SUN = sun_spr()

def rays(base, t, cx=540, cy=HOR, n=28, al=0.10, col=(255, 236, 200)):
    lay = Image.new("RGBA", (W, HOR), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); R = 2400
    rot = t * 2.2
    for k in range(n):
        if k % 2: continue
        a0 = math.radians(rot + k * 360 / n); a1 = math.radians(rot + (k + 1) * 360 / n)
        d.polygon([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)), (cx + R * math.cos(a1), cy + R * math.sin(a1))], fill=col + (int(255 * al),))
    base.alpha_composite(lay, (0, 0))

def ripples(base, t, al=1.0):
    lay = Image.new("RGBA", (W, 1500 - HOR), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    rr = random.Random(24)
    for i in range(14):
        y = 14 + i * i * 1.55 + i * 6
        if y > 1500 - HOR - 6: break
        th = 2 + i // 4; x = -rr.uniform(0, 200) + 40 * math.sin(t * 0.8 + i)
        while x < W:
            L = rr.uniform(80, 240); gap = rr.uniform(30, 90)
            near_sun = abs(x + L / 2 - 540) < 200 - i * 6
            col = (GOLD_L if near_sun else GOLD) + (int((200 if near_sun else 120) * al),)
            d.line((x, y, x + L, y), fill=col, width=th); x += L + gap
    # striped sun reflection
    for i in range(9):
        y = 10 + i * 30; w_ = 300 - i * 26 + 10 * math.sin(t * 2 + i)
        d.rectangle((540 - w_ / 2, y, 540 + w_ / 2, y + 8 - i * 0.5), fill=(252, 214, 166, int(150 * al * (1 - i / 10))))
    base.alpha_composite(lay, (0, HOR))

def border(base):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for inset, w_ in ((26, 5), (42, 2)):
        x0, y0, x1, y1 = inset, inset, W - inset, H - inset; s = 34
        pts = [(x0 + s, y0), (x1 - s, y0), (x1 - s, y0 + s * 0.5), (x1 - s * 0.5, y0 + s * 0.5), (x1 - s * 0.5, y0 + s), (x1, y0 + s),
               (x1, y1 - s), (x1 - s * 0.5, y1 - s), (x1 - s * 0.5, y1 - s * 0.5), (x1 - s, y1 - s * 0.5), (x1 - s, y1),
               (x0 + s, y1), (x0 + s, y1 - s * 0.5), (x0 + s * 0.5, y1 - s * 0.5), (x0 + s * 0.5, y1 - s), (x0, y1 - s),
               (x0, y0 + s), (x0 + s * 0.5, y0 + s), (x0 + s * 0.5, y0 + s * 0.5), (x0 + s, y0 + s * 0.5)]
        d.line(pts + [pts[0]], fill=GOLD + (255,), width=w_, joint="curve")
    return lay
BORDER = Image.new("RGBA", (W, H)); BORDER = border(BORDER)

def bottom_band(base):
    d = ImageDraw.Draw(base)
    d.rectangle((0, 1500, W, H), fill=TEAL_D + (255,))
    d.line((0, 1500, W, 1500), fill=GOLD + (255,), width=5); d.line((0, 1512, W, 1512), fill=GOLD_D + (255,), width=2)
    # fan motif bottom
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    for i in range(5):
        r = 120 + i * 60
        dl.arc((540 - r, 1890 - r, 540 + r, 1890 + r), 180, 360, fill=GOLD + (40,), width=3)
    base.alpha_composite(lay)

def poster(t, sun_y=None, dim=0.0, sun_sc=1.0):
    sky = Image.fromarray(SKY.astype(np.uint8)).convert("RGBA")
    b = Image.new("RGBA", (W, H), TEAL_D + (255,)); b.paste(sky, (0, 0))
    rays(b, t)
    sy = HOR - 70 if sun_y is None else sun_y
    sun = SUN if abs(sun_sc - 1) < 0.01 else SUN.resize((int(SUN.width * sun_sc), int(SUN.height * sun_sc)), Image.LANCZOS)
    lay = Image.new("RGBA", (W, HOR), (0, 0, 0, 0)); put(lay, sun, 540, sy); b.alpha_composite(lay)
    b.alpha_composite(DUNES, (0, HOR - 300 + 4))
    b.alpha_composite(WATER, (0, HOR))
    ripples(b, t)
    bottom_band(b)
    if dim > 0:
        ov = Image.new("RGBA", (W, H), TEAL_D + (int(255 * dim),)); b.alpha_composite(ov)
    return b

# ---------- flamingo ----------
def bez(p0, p1, p2, p3, n=90):
    out = []
    for i in range(n + 1):
        u = i / n; a = (1 - u) ** 3; bb = 3 * u * (1 - u) ** 2; c = 3 * u * u * (1 - u); dd = u ** 3
        out.append((a * p0[0] + bb * p1[0] + c * p2[0] + dd * p3[0], a * p0[1] + bb * p1[1] + c * p2[1] + dd * p3[1]))
    return out

_FL = {}
def flamingo(col=PINK, pose="stand", flip=False):
    """flat deco flamingo facing right. canvas 620x780, feet at y=760."""
    k = (col, pose, flip)
    if k in _FL: return _FL[k]
    shade = mix(col, (90, 30, 60), 0.28); light = mix(col, (255, 255, 255), 0.35)
    im = new(620, 780); d = ImageDraw.Draw(im)
    def e(box, c): d.ellipse(S(box), fill=c + (255,))
    leg = mix(col, (120, 60, 70), 0.25)
    # legs
    if pose == "stand":
        d.line(S((300, 380, 306, 560, 300, 762)), fill=leg + (255,), width=9 * SS, joint="curve")
        d.line(S((318, 380, 380, 520, 318, 560)), fill=leg + (255,), width=9 * SS, joint="curve")   # tucked leg
        e((372, 510, 392, 530), leg)
        d.polygon(S((282, 760, 330, 760, 300, 748)), fill=leg + (255,))
    else:
        d.line(S((270, 380, 250, 560, 240, 762)), fill=leg + (255,), width=9 * SS, joint="curve")
        d.line(S((320, 380, 340, 560, 350, 762)), fill=leg + (255,), width=9 * SS, joint="curve")
        for fx in (240, 350): d.polygon(S((fx - 22, 760, fx + 26, 760, fx, 748)), fill=leg + (255,))
    # body + tail
    d.polygon(S((150, 300, 230, 280, 250, 352)), fill=shade + (255,))
    e((180, 260, 420, 400), col)
    # wing: lens with deco chevron feathers
    d.chord(S((190, 262, 400, 372)), 0, 180, fill=shade + (255,))
    d.polygon(S((190, 318, 140, 330, 200, 345)), fill=shade + (255,))
    for i in range(4):
        x = 220 + i * 42
        d.line(S((x, 330, x + 20, 352, x + 40, 330)), fill=light + (200,), width=3 * SS)
    # neck + head
    if pose == "stand":
        pts = bez((390, 300), (480, 200), (220, 170), (310, 70)); head = (318, 66); billdir = 1
    else:
        pts = bez((395, 300), (540, 160), (560, 420), (470, 600)); head = (468, 610); billdir = -1
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        r = 22 - 8 * i / n
        e((x - r, y - r, x + r, y + r), col)
    hx, hy = head
    e((hx - 30, hy - 26, hx + 30, hy + 26), col)
    if billdir == 1:
        d.polygon(S((hx + 10, hy - 20, hx + 70, hy - 4, hx + 84, hy + 22, hx + 40, hy + 18, hx + 14, hy + 16)), fill=CREAM + (255,))
        d.polygon(S((hx + 58, hy - 8, hx + 74, hy - 1, hx + 86, hy + 26, hx + 70, hy + 46, hx + 60, hy + 18)), fill=INK + (255,))
        e((hx - 2, hy - 12, hx + 10, hy), INK)
    else:   # upside down: bill points back toward the legs
        d.polygon(S((hx - 10, hy + 20, hx - 70, hy + 4, hx - 84, hy - 22, hx - 40, hy - 18, hx - 14, hy - 16)), fill=CREAM + (255,))
        d.polygon(S((hx - 58, hy + 8, hx - 74, hy + 1, hx - 86, hy - 26, hx - 70, hy - 46, hx - 60, hy - 18)), fill=INK + (255,))
        e((hx - 10, hy, hx + 2, hy + 12), INK)
    spr = down(im)
    if flip: spr = spr.transpose(Image.FLIP_LEFT_RIGHT)
    _FL[k] = spr; return spr

_RF = {}
def reflection(spr, key):
    if key not in _RF:
        r = spr.transpose(Image.FLIP_TOP_BOTTOM); a = np.asarray(r).astype(np.float32).copy()
        h = a.shape[0]; fade = np.linspace(0.55, 0.0, h)[:, None]
        stripes = ((np.arange(h) // 7) % 2 == 0).astype(np.float32)[:, None]
        a[..., :3] = a[..., :3] * 0.6 + np.array(TEAL_M) * 0.4
        a[..., 3] *= fade * stripes
        _RF[key] = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")
    return _RF[key]

def pink_at(u): return mix(GREY, PINK, u)
def fl_q(u, pose="stand", flip=False):
    q = round(max(0, min(1, u)) * 20) / 20
    return flamingo(pink_at(q), pose, flip), (q, pose, flip)

def place_flamingo(b, u, cx, feet_y, sc, t, ph, pose="stand", flip=False, al=1.0, refl=True):
    spr, key = fl_q(u, pose, flip)
    s2 = spr.resize((int(spr.width * sc), int(spr.height * sc)), Image.LANCZOS) if abs(sc - 1) > 0.01 else spr
    bobv = 3 * math.sin(t * 1.4 + ph)
    cy = feet_y - (760 - 390) * sc + bobv     # sprite centre is at y=390 in sprite coords
    if refl:
        r = reflection(s2, key + (round(sc, 3),))
        lay = Image.new("RGBA", (W, 1500 - HOR), (0, 0, 0, 0))
        put(lay, r, cx, feet_y - HOR + (s2.height / 2 - (780 - 760) * sc) + bobv * -0.5, 0, al)
        b.alpha_composite(lay, (0, HOR))
    put(b, s2, cx, cy, 0, al)

# ---------- other sprites ----------
def arch_spr(w, h, fill=CREAM):
    im = new(w + 20, h + 20); d = ImageDraw.Draw(im); x0, y0, x1, y1 = 10, 10, w + 10, h + 10; r = w / 2
    def shape(ins, col, outline=None, width=0):
        d.pieslice(S((x0 + ins, y0 + ins, x1 - ins, y0 + 2 * r - ins)), 180, 360, fill=col)
        d.rectangle(S((x0 + ins, y0 + r, x1 - ins, y1 - ins)), fill=col)
    shape(0, GOLD + (255,)); shape(8, TEAL_D + (255,)); shape(14, GOLD + (255,)); shape(20, fill + (255,))
    return down(im)
_AR = {}
def arch(w, h, fill=CREAM):
    k = (w, h, fill)
    if k not in _AR: _AR[k] = arch_spr(w, h, fill)
    return _AR[k]

_MD = {}
def medallion(r, fill=CREAM):
    k = (r, fill)
    if k not in _MD:
        im = new(2 * r + 10, 2 * r + 10); d = ImageDraw.Draw(im); c = r + 5
        for rr_, col in ((r, GOLD), (r - 8, TEAL_D), (r - 14, GOLD), (r - 20, fill)):
            d.ellipse(S((c - rr_, c - rr_, c + rr_, c + rr_)), fill=col + (255,))
        for k2 in range(24):
            a = k2 * math.pi / 12; d.line(S((c + (r - 4) * math.cos(a), c + (r - 4) * math.sin(a), c + (r - 1) * math.cos(a), c + (r - 1) * math.sin(a))), fill=TEAL_D + (255,), width=2 * SS)
        _MD[k] = down(im)
    return _MD[k]

def chick_spr(fluff=1.0):
    im = new(360, 360); d = ImageDraw.Draw(im); rr = random.Random(5)
    body = (180, 220, 105); head = (240, 120, 62)
    for (cx, cy, R), col in ((body, (214, 210, 206)), (head, (232, 230, 226))):
        for k in range(28):
            a = k * 2 * math.pi / 28; rr2 = R * 0.26 * fluff
            x = cx + R * 0.86 * math.cos(a); y = cy + R * 0.86 * math.sin(a)
            d.ellipse(S((x - rr2, y - rr2, x + rr2, y + rr2)), fill=col + (255,))
        d.ellipse(S((cx - R * 0.9, cy - R * 0.9, cx + R * 0.9, cy + R * 0.9)), fill=col + (255,))
    d.ellipse(S((150, 210, 240, 270)), fill=(196, 192, 188, 255))                               # wing hint
    d.polygon(S((292, 110, 340, 126, 296, 134)), fill=(60, 60, 64, 255))                         # straight little bill
    d.ellipse(S((258, 102, 272, 116)), fill=INK + (255,))
    for x in (160, 210): d.line(S((x, 315, x, 350)), fill=(130, 110, 110, 255), width=7 * SS)
    return down(im)
CHICK = chick_spr()

def egg_spr(crack=0.0):
    im = new(240, 300); d = ImageDraw.Draw(im)
    d.ellipse(S((20, 20, 220, 280)), fill=CREAM + (255,), outline=GOLD_D + (255,), width=4 * SS)
    d.ellipse(S((50, 50, 110, 130)), fill=(255, 252, 244, 255))
    if crack > 0:
        pts = [(30, 150), (65, 128), (95, 160), (125, 126), (155, 158), (185, 130), (212, 150)]
        n = max(2, int(len(pts) * min(1, crack)))
        d.line(S(sum(pts[:n], ())), fill=INK + (255,), width=4 * SS, joint="curve")
    return down(im)

def shrimp_spr(col=(240, 128, 110)):
    im = new(320, 260); d = ImageDraw.Draw(im)
    segs = 8
    for i in range(segs):
        a = math.radians(200 - i * 26); r = 85
        cx, cy = 165 + r * math.cos(a), 135 + r * math.sin(a); R = 34 - i * 3
        c = mix(col, (255, 210, 190), 0.15 * (i % 2))
        d.ellipse(S((cx - R, cy - R, cx + R, cy + R)), fill=c + (255,), outline=mix(col, INK, 0.3) + (255,), width=2 * SS)
    # tail fan
    a = math.radians(200 - segs * 26); tx, ty = 165 + 85 * math.cos(a), 135 + 85 * math.sin(a)
    d.polygon(S((tx, ty, tx + 40, ty - 34, tx + 50, ty + 6)), fill=col + (255,))
    # head + antennae + eye
    hx, hy = 165 + 85 * math.cos(math.radians(200)), 135 + 85 * math.sin(math.radians(200))
    d.line(S((hx - 10, hy - 20, hx - 60, hy - 110)), fill=mix(col, INK, 0.3) + (255,), width=2 * SS)
    d.line(S((hx, hy - 20, hx + 10, hy - 120)), fill=mix(col, INK, 0.3) + (255,), width=2 * SS)
    d.ellipse(S((hx - 12, hy - 20, hx + 2, hy - 6)), fill=INK + (255,))
    for i in range(5):
        a = math.radians(205 - i * 24); x0, y0 = 165 + 60 * math.cos(a), 135 + 60 * math.sin(a)
        d.line(S((x0, y0, x0 + 6, y0 + 30)), fill=mix(col, INK, 0.3) + (255,), width=2 * SS)
    return down(im)
SHRIMP = shrimp_spr()

def algae_spr():
    im = new(320, 320); d = ImageDraw.Draw(im)
    for (cx, cy, R, ph) in ((110, 120, 70, 0), (215, 175, 62, 1.5), (130, 230, 52, 3.0), (225, 85, 44, 2.0)):
        pts = []
        for k in range(160):
            u = k / 159; a = ph + u * 5.5 * math.pi; r = R * (1 - u * 0.85)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        d.line(S(sum(pts, ())), fill=GREEN + (255,), width=7 * SS, joint="curve")
        d.ellipse(S((cx - 7, cy - 7, cx + 7, cy + 7)), fill=GREEN_L + (255,))
    return down(im)
ALGAE = algae_spr()

def feather_mask(w=360, h=820):
    im = Image.new("L", (w * SS, h * SS), 0); d = ImageDraw.Draw(im); cx = w / 2
    right, left = [], []
    for i in range(121):
        u = i / 120; y = 20 + u * 670
        half = 140 * math.sin(math.pi * (u ** 0.75)) ** 0.8 + 6
        notch = 1 - (0.22 if 0.30 < u < 0.34 else 0) ; notch2 = 1 - (0.25 if 0.58 < u < 0.62 else 0)
        bend = 26 * math.sin(u * math.pi)                       # gentle curve of the shaft
        right.append((cx + bend + half * 1.05 * notch, y)); left.append((cx + bend - half * 0.9 * notch2, y))
    d.polygon([(x * SS, y * SS) for x, y in right + left[::-1]], fill=255)
    return im
FEATHER_M = feather_mask()
def feather(fill_u, t):
    w, h = 360, 820
    m = np.asarray(FEATHER_M).astype(np.float32) / 255
    yy = np.arange(h * SS)[:, None] / SS
    level = 690 - fill_u * 690 + 8 * np.sin(np.arange(w * SS)[None, :] / SS / 30 + t * 4)
    pinkf = (yy > level).astype(np.float32)
    col = np.where(pinkf[..., None] > 0, np.array(PINK, np.float32), np.array(CREAM, np.float32))
    col = np.broadcast_to(col, (h * SS, w * SS, 3)).copy()
    a = np.dstack([col, m * 255])
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA"); d = ImageDraw.Draw(im); cx = w / 2
    # outline-ish chevrons + quill
    for i in range(1, 13):
        u = i / 13; y = 20 + u * 670; bx = cx + 26 * math.sin(u * math.pi)
        d.line(S((bx - 110, y + 34, bx, y - 6, bx + 120, y + 34)), fill=(255, 255, 255, 70), width=3 * SS)
    shaft = [(cx + 26 * math.sin(min(1, (y - 20) / 670) * math.pi), y) for y in range(30, 800, 10)]
    d.line(S(sum(shaft, ())), fill=GOLD + (255,), width=8 * SS, joint="curve")
    d.ellipse(S((cx - 9, 790, cx + 9, 808)), fill=GOLD + (255,))
    im.putalpha(Image.fromarray(np.maximum(np.asarray(im)[..., 3], 0).astype(np.uint8)))
    return down(im)

def drop_spr(col=GOLD_L, s=1.0):
    im = new(60, 80); d = ImageDraw.Draw(im)
    d.polygon(S((30, 4, 50, 46, 10, 46)), fill=col + (255,)); d.ellipse(S((10, 30, 50, 70)), fill=col + (255,))
    d.ellipse(S((20, 40, 30, 52)), fill=(255, 255, 255, 170))
    return down(im)
DROP = drop_spr((246, 150, 90))

# ---------- scene helpers ----------
def wt_(ln, i): return words[min(ln["_w0"] + i, ln["_w1"] - 1)][1] - ln["_s"]
def fd(lt, at, d=0.3): return ease((lt - at) / d)
def pop(lt, at, d=0.45): return back((lt - at) / d, 1.5)
def label(base, s, cx, cy, size=40, col=GOLD_L, al=1.0, track=8):
    put(base, tsprite(s, size, col, "poiret", None, False, track), cx, cy, 0, al)

def H_titles(b, lt, first):
    o = -9 if first else 0   # frame 0 shows everything already set
    title(b, "A GROUP OF", 112, 200, o, lt)
    title(b, "FLAMINGOS", 132, 340, o, lt)
    title(b, "IS CALLED A", 112, 480, o, lt)
    title(b, "FLAMBOYANCE", 150, 640, o, lt, gold=True, maxw=W - 140)
    rule(b, 760, 560, fd(lt, o))

ROW = [(1, 230, 1196, 0.24, 0.9), (-1, 470, 1192, 0.22, 2.2), (1, 800, 1198, 0.25, 1.4),
       (-1, 150, 1300, 0.50, 0.0), (1, 300, 1245, 0.40, 1.1), (-1, 460, 1330, 0.60, 2.0), (1, 640, 1255, 0.44, 0.6),
       (-1, 800, 1310, 0.54, 1.7), (1, 935, 1250, 0.40, 2.6)]

def S_hook(b, sc, ln, lt, dur, t, first=True):
    for fl, x, fy, s, ph in sorted(ROW, key=lambda r: r[2]):
        place_flamingo(b, 1.0, x + 6 * math.sin(t * 0.5 + ph), fy, s, t, ph, flip=(fl < 0))
    H_titles(b, lt, first)

def S_loop(b, sc, ln, lt, dur, t):
    k = wt_(ln, 4)   # "It isn't"
    title(b, "THEIR FAMOUS", 104, 220, 0.0, lt)
    title(b, "PINK?", 190, 400, 0.15, lt, col=PINK_L)
    drain = fd(lt, k - 0.2, 0.7)
    place_flamingo(b, 1 - 0.85 * drain, 440, 1450, 0.98, t, 0.2)
    title(b, "NOT REALLY THEIRS.", 92, 560, k, lt, gold=True)
    mu = pop(lt, k + 0.1)
    if mu > 0:
        m = medallion(110, TEAL_D); put(b, m, 850, 860, 0, min(1, mu), max(0.05, mu))
        put(b, tsprite("?", 150, GOLD_L, "lime", None), 850, 868, 6 * math.sin(t * 3), min(1, mu), max(0.05, mu))

def S_chick(b, sc, ln, lt, dur, t):
    title(b, "BORN", 150, 210, 0.0, lt)
    title(b, "WHITE & GREY", 118, 370, 0.15, lt, col=(226, 224, 222))
    rule(b, 480, 460, fd(lt, 0.2))
    a = arch(620, 820); put(b, a, 540, 1080, 0, fd(lt, 0, 0.25), 0.9 + 0.1 * eout(lt / 0.4))
    k = wt_(ln, 3) - 0.2    # "fluffy"
    if lt < k:
        cr = fd(lt, 0.3, k - 0.4); wob = 5 * math.sin(lt * 26) * cr
        put(b, egg_spr(cr), 540, 1180, wob)
    else:
        u = pop(lt, k, 0.5)
        put(b, CHICK, 540 + 6 * math.sin(t * 2), 1150 + 4 * math.sin(t * 3), 3 * math.sin(t * 2.2), 1, max(0.05, u))
        sh = egg_spr(1); half = sh.crop((0, sh.height // 2, sh.width, sh.height))
        put(b, half, 540, 1290, 0, 1.0, 1.0)
    label(b, "FIG. I  ·  THE CHICK", 540, 1440, 34, GOLD_D, fd(lt, 0.3))

def S_food(b, sc, ln, lt, dur, t):
    title(b, "THE PINK", 128, 210, 0.0, lt)
    title(b, "IS FOOD", 150, 370, 0.12, lt, gold=True)
    k1 = wt_(ln, 6) - 0.15; k2 = wt_(ln, 8) - 0.2
    for j, (cx, cy, k, spr, nm) in enumerate(((300, 820, k1, ALGAE, "ALGAE"), (780, 1120, k2, SHRIMP, "BRINE SHRIMP"))):
        um = pop(lt, min(k, 0.2 + j * 0.3))
        if um <= 0: continue
        put(b, medallion(220), cx, cy, 0, min(1, um), max(0.05, um))
        u = pop(lt, k)
        if u <= 0:
            put(b, tsprite("?", 150, GOLD, "lime", None), cx, cy + 8, 5 * math.sin(t * 3 + j), 0.8); continue
        put(b, spr, cx + 4 * math.sin(t * 2 + cx), cy + 6 * math.sin(t * 1.6 + cx), 5 * math.sin(t * 1.2 + cy), min(1, u), max(0.05, u) * 1.05)
        label(b, nm, cx, cy + 270, 44, GOLD_L, fd(lt, k + 0.2), 10)
    # dotted deco link
    if lt > k2:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        for i in range(10):
            u = i / 9; x = 380 + (700 - 380) * u; y = 960 + 60 * math.sin(u * math.pi)
            if u <= fd(lt, k2, 0.5): d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=GOLD + (255,))
        b.alpha_composite(lay)

def S_pigment(b, sc, ln, lt, dur, t):
    k = wt_(ln, 5) - 0.2   # "carotenoids"
    title(b, "PACKED WITH", 104, 200, 0.0, lt)
    title(b, "PIGMENTS", 150, 350, 0.1, lt, col=PINK_L)
    a = arch(540, 940, TEAL); put(b, a, 540, 1020, 0, fd(lt, 0, 0.25))
    fu = ease((lt - 0.3) / max(0.6, dur - 0.6))
    put(b, feather(fu, t), 530, 1000, 4 * math.sin(t * 1.1))
    for i in range(6):
        ph = (lt * 0.9 + i / 6) % 1.0
        if lt < 0.2: continue
        x = 540 + 120 * math.sin(i * 2.1); y = 520 + ph * 560
        put(b, DROP, x, y, 0, min(1, ph * 5) * (1 - max(0, ph - 0.85) / 0.15))
    if lt > k:
        u = pop(lt, k)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.rectangle((150, 1375, 930, 1475), fill=TEAL_D + (255,)); d.rectangle((150, 1375, 930, 1475), outline=GOLD + (255,), width=4)
        d.rectangle((162, 1387, 918, 1463), outline=GOLD_D + (255,), width=2)
        put(b, lay.crop((140, 1365, 940, 1485)), 540, 1425, 0, min(1, u), max(0.05, u))
        put(b, tsprite("CAROTENOIDS", fit("CAROTENOIDS", 78, 700), CREAM, "lime", None, True), 540, 1427, 0, min(1, u), max(0.05, u))

def S_feed(b, sc, ln, lt, dur, t):
    title(b, "UPSIDE-DOWN", 124, 210, 0.0, lt, gold=True)
    title(b, "DINNER", 150, 370, 0.12, lt)
    sl = eout(lt / 0.5)
    place_flamingo(b, 1.0, 420 - (1 - sl) * 300, 1450, 1.2, t, 0.3, pose="feed", refl=False)
    # water surface + flow chevrons through the bill
    k = wt_(ln, 5) - 0.2   # "filtering"
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    wy = 1200
    d.rectangle((0, wy, W, 1500), fill=TEAL_M + (150,))
    for i in range(6):
        y = wy + 8 + i * 48; x = (t * 60 + i * 90) % 220 - 220
        while x < W: d.line((x, y, x + 120, y), fill=GOLD + (140,), width=3); x += 220
    if lt > k:
        for j in range(5):
            u = ((lt - k) * 0.9 + j / 5) % 1.0; x = 830 - u * 300; y = 1300 + 30 * math.sin(u * 6 + j)
            al = int(230 * math.sin(math.pi * u))
            d.line((x + 22, y - 18, x, y, x + 22, y + 18), fill=CREAM + (al,), width=6)
        for j in range(8):
            u = ((lt - k) * 0.6 + j / 8) % 1.0; bx = 640 + 40 * math.sin(j * 3 + t); by = 1290 - u * 100
            r = 5 + j % 3 * 3; d.ellipse((bx - r, by - r, bx + r, by + r), outline=CREAM + (int(200 * (1 - u)),), width=3)
    b.alpha_composite(lay)
    if lt > k: label(b, "FILTER FEEDING", 540, 1460, 44, GOLD_L, fd(lt, k + 0.1), 10)

def S_years(b, sc, ln, lt, dur, t):
    title(b, "SEVERAL YEARS", 118, 210, 0.0, lt)
    title(b, "TO TURN PINK", 128, 360, 0.12, lt, gold=True)
    k = wt_(ln, 6) - 0.4   # "that diet"
    for i, (x, nm) in enumerate(((200, "CHICK"), (540, "YOUNG"), (880, "ADULT"))):
        at = 0.15 + i * 0.35; u = fd(lt, at, 0.35)
        if u <= 0: continue
        put(b, arch(300, 760, TEAL), x, 1060 + (1 - u) * 80, 0, u)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if i == 0:
            put(lay, CHICK, x, 1260, 0, 1, 0.6)
        else:
            pu = (0.25 if i == 1 else 1.0) * ease((lt - k - i * 0.3) / 0.8) + (0.0)
            place_flamingo(lay, pu if i == 2 else 0.12 + 0.3 * ease((lt - k) / 0.8), x, 1380, 0.62 if i == 2 else 0.5, t, i, flip=False, refl=False)
        put(b, lay, W / 2, H / 2, 0, u)
        label(b, nm, x, 1475, 40, GOLD_L, u, 10)

def S_end(b, sc, ln, lt, dur, t):
    click = sc.get("click_at", 0.5); on = ease((lt - click) / 0.4)
    title(b, "SOUNDS FAKE?", 124, 230, 0.0, lt)
    y = 520; x0, x1, hh = 170, 910, 160
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((x0 - 12, y - hh / 2 - 12, x1 + 12, y + hh / 2 + 12), radius=hh / 2 + 12, fill=GOLD + (255,))
    d.rounded_rectangle((x0, y - hh / 2, x1, y + hh / 2), radius=hh / 2, fill=mix(GREY_D, PINK, on) + (255,))
    b.alpha_composite(lay)
    put(b, tsprite("FAKE", 76, CREAM, "lime", None), (x0 + x1) / 2 + 80, y + 2, 0, 1 - on)
    put(b, tsprite("TRUE", 76, CREAM, "lime", None), (x0 + x1) / 2 - 80, y + 2, 0, ease((on - 0.5) / 0.4))
    kx = x0 + hh / 2 + (x1 - x0 - hh) * on
    put(b, medallion(hh // 2 + 8, PEACH), kx, y, 0)
    put(b, SUN, kx, y, -360 * on, 1, 0.26)
    place_flamingo(b, 0.35 + 0.65 * on, 540, 1470, 0.68, t, 0.4)
    title(b, "IT'S TRUE.", 150, 760, click + 0.25, lt, gold=True)
    title(b, "Follow for more.", 78, 900, click + 0.55, lt, col=CREAM)

SCENES = dict(hook=S_hook, loop=S_loop, chick=S_chick, food=S_food, pigment=S_pigment, feed=S_feed, years=S_years, end=S_end)
BGOPT = dict(hook={}, loop=dict(sun_sc=1.2, sun_y=HOR - 40), chick=dict(dim=0.55), food=dict(dim=0.5), pigment=dict(dim=0.5),
             feed=dict(sun_y=HOR - 140, sun_sc=0.8), years=dict(dim=0.45), end=dict(sun_y=HOR - 20, sun_sc=1.3))

# ---------- audio ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
rng = np.random.default_rng(24)
def note(f, dur, gain, decay=3.0, bright=0.5):
    s = np.arange(int(dur * SR)) / SR
    sig = (np.sin(2 * np.pi * f * s) + bright * np.sin(2 * np.pi * 2 * f * s) * np.exp(-s * 6) + 0.25 * bright * np.sin(2 * np.pi * 3 * f * s) * np.exp(-s * 9))
    return (sig * np.exp(-s * decay) * np.minimum(1, s / 0.004) * gain).astype(np.float32)
BPM = 112; BEAT = 60 / BPM; BAR = 4 * BEAT
CH = [[174.61, 220.0, 261.63, 329.63], [146.83, 174.61, 220.0, 261.63], [196.0, 233.08, 293.66, 349.23], [130.81, 164.81, 196.0, 233.08]]
BASS = [[87.31, 98.0, 110.0, 116.54], [73.42, 82.41, 87.31, 92.5], [98.0, 110.0, 116.54, 123.47], [65.41, 73.42, 82.41, 77.78]]
for bi in range(int(total / BAR) + 2):
    ch = CH[bi % 4]; b0 = bi * BAR
    for k, f in enumerate(BASS[bi % 4]): place(music, b0 + k * BEAT, note(f, 0.6, 0.16, 5.0, 0.3))
    for at in (b0 + BEAT * 0.0 + 0.66 * BEAT, b0 + 2 * BEAT + 0.66 * BEAT):     # syncopated comp
        for j, f in enumerate(ch): place(music, at + j * 0.008, note(f * 2, 0.7, 0.035, 4.0, 0.6))
    for k in range(4):                                                     # brushed swing hats
        for sw, g in ((0.0, 0.010), (0.66 * BEAT, 0.006)):
            sl = np.arange(int(0.09 * SR)) / SR; z = rng.normal(0, 1, len(sl)) * np.exp(-sl * 40)
            z = z - np.convolve(z, np.ones(4) / 4, mode="same")
            place(music, b0 + k * BEAT + sw, z.astype(np.float32), g * (1.6 if k % 2 else 1.0))
    if bi % 2 == 1:                                                        # little vibes melody
        for j, f in enumerate((523.25, 659.25, 783.99, 880.0)[:: (1 if bi % 4 == 1 else -1)]):
            place(music, b0 + 2 * BEAT + j * BEAT / 2, note(f, 1.0, 0.03, 2.5, 0.2))
def harp(at, up=True, gain=0.04):
    sc_ = [349.23, 392.0, 440.0, 523.25, 587.33, 698.46, 783.99, 880.0, 1046.5, 1174.66]
    seq = sc_ if up else sc_[::-1]
    for j, f in enumerate(seq): place(music, at + j * 0.022, note(f, 0.9, gain, 3.5, 0.15))
hook_hit(music, 0.3); harp(0.0, True, 0.05)
for i, ln in enumerate(spec["lines"]):
    st = ln["scene"]["type"]; s0 = ln["_s"]
    if i > 0: whoosh(music, s0, 0.08); harp(s0 - 0.15, i % 2 == 0, 0.03)
    if st == "loop": place(music, s0 + wt_(ln, 4), note(110, 1.2, 0.12, 2.0, 0.2))
    if st == "chick": place(music, s0 + wt_(ln, 3) - 0.2, note(1318.5, 0.4, 0.06, 8, 0.1))
    if st == "food":
        for k_ in (6, 8): place(music, s0 + wt_(ln, k_) - 0.15, note(1046.5, 0.5, 0.06, 6, 0.2))
    if st == "pigment":
        for j in range(5): place(music, s0 + 0.5 + j * 0.45, note(1567.98 - j * 100, 0.3, 0.03, 9, 0.1))
    if st == "end":
        c = s0 + ln["scene"].get("click_at", 0.5)
        sl = np.arange(int(0.04 * SR)) / SR; place(music, c, (rng.normal(0, 1, len(sl)) * np.exp(-sl * 120)).astype(np.float32), 0.25)
        for j, f in enumerate((698.46, 880.0, 1046.5, 1396.9)): place(music, c + 0.15 + j * 0.06, note(f, 1.4, 0.06, 2.5, 0.3))
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.42)

# ---------- compositing ----------
STARTS = [ln["_s"] for ln in spec["lines"]]
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 76; f = F(size)
    while f.getlength(" ".join(ws)) > W - 260 and size > 40: size -= 4; f = F(size)
    tw_ = f.getlength(" ".join(ws)); x = (W - tw_) / 2; y = 1590
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([x - 46, y - 22, x + tw_ + 46, y + size + 18], fill=INK + (250,), outline=GOLD + (255,), width=4)
    d.rectangle([x - 36, y - 12, x + tw_ + 36, y + size + 8], outline=GOLD_D + (255,), width=2)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]
        d.text((x, y + size * 0.5), w, font=f, fill=(PINK_L if on else CREAM) + (255,), anchor="lm"); x += f.getlength(w + " ")

def scene_frame(t, ln, first=False):
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    st = ln["scene"]["type"]
    b = poster(t, **BGOPT.get(st, {}))
    if st == "hook": S_hook(b, ln["scene"], ln, lt, dur, t, first)
    else: SCENES[st](b, ln["scene"], ln, lt, dur, t)
    b.alpha_composite(BORDER)
    return b

def shutter(b, u, left):
    """deco venetian shutter: u=1 fully closed."""
    if u <= 0: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); nb = 12; bh = H / nb
    for i in range(nb):
        uu = max(0.0, min(1.0, u * 1.4 - (i % 2) * 0.2 - abs(i - nb / 2) * 0.02))
        w_ = W * ease(uu)
        if w_ <= 1: continue
        fromleft = (i % 2 == 0) == left
        x0, x1 = (0, w_) if fromleft else (W - w_, W)
        d.rectangle((x0, i * bh, x1, (i + 1) * bh + 1), fill=TEAL_D + (255,))
        ex = x1 if fromleft else x0
        d.rectangle((ex - 5, i * bh, ex + 5, (i + 1) * bh), fill=GOLD + (255,))
    b.alpha_composite(lay)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]
    first = ln is spec["lines"][0]
    b = scene_frame(t, ln, first)
    if ln["scene"]["type"] == "end":
        lt = t - ln["_s"]; dur = total - ln["_s"]; lp = ease((lt - (dur - 0.42)) / 0.38)
        if lp > 0: b = Image.blend(b, scene_frame(t, spec["lines"][0], True), lp)
    for j, s in enumerate(STARTS[1:]):
        lead = s - 0.12   # active_line switches at _s-0.12
        if lead - 0.16 <= t < lead: shutter(b, (t - (lead - 0.16)) / 0.16, j % 2 == 0)
        elif lead <= t < lead + 0.26: shutter(b, 1 - (t - lead) / 0.26, j % 2 == 0)
    img = b.convert("RGB")
    caption(img, t)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 10, W, H], fill=TEAL_D); d.rectangle([0, H - 10, int(W * t / total), H], fill=GOLD)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=22); print(f"done {total:.1f}s")
