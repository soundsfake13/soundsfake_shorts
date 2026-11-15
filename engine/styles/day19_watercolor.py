"""Day 19 — WATERCOLOR FIELD JOURNAL style (butterflies taste with their feet).
Every frame is a page of a naturalist's sketchbook: cold-press cream paper (tooth, fibres, soft vignette, stitched
gutter on the left), soft watercolour washes that bloom outward from a point when they appear (noise-edged masks,
pigment pooling at the edges, granulation in the paper tooth, low-frequency colour variation), graphite pencil
construction lines drawn stroke by stroke, sepia-ink handwriting (Kalam) and italic Latin labels (EB Garamond).
Everything is composited as MULTIPLY onto the paper, like real transparent paint. Scene changes = the page turns
(new page slides in over the old one with a soft shadow + paper rustle).
Ending: a pencil-and-wash FAKE -> TRUE toggle whose knob is a painted butterfly; the track floods with green.
Music: plucked nylon-string arpeggios (Karplus-Strong) + soft pad + woodblock taps on the drumming.
Usage: python3 engine/styles/day19_watercolor.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import gaussian_filter
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
INTER = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter")
_F = {}
def F(kind, s):
    k = (kind, int(s))
    if k not in _F:
        path = {"hand": f"{FONTS}/Kalam-Bold.ttf", "handr": f"{FONTS}/Kalam-Regular.ttf",
                "latin": f"{FONTS}/EBGaramond-Italic[wght].ttf"}.get(kind, f"{INTER}/InterDisplay-Bold.otf")
        _F[k] = ImageFont.truetype(path, int(s))
        if kind == "latin":
            try: _F[k].set_variation_by_axes([560])
            except Exception: pass
    return _F[k]

INK = (44, 34, 30)            # sepia ink
PENCIL = (86, 84, 92)
YEL, DARK, BLUE, ORANGE = (250, 200, 64), (52, 44, 54), (92, 140, 205), (232, 118, 52)
GREEN, GREEN2, RED, PAPER = (128, 178, 92), (70, 128, 74), (205, 70, 60), (247, 241, 228)

# ---------- noise / paper ----------
def fbm(seed, scales, amps, size):
    rr = np.random.default_rng(seed); acc = np.zeros((size[1], size[0]), np.float32)
    for s, a in zip(scales, amps):
        g = rr.random((max(2, size[1] // s + 2), max(2, size[0] // s + 2))).astype(np.float32)
        acc += a * np.asarray(Image.fromarray(g, "F").resize(size, Image.BICUBIC))
    acc -= acc.min(); return acc / max(1e-6, acc.max())

def _paper():
    tone_ = fbm(1, [600, 240, 80], [1, 0.5, 0.25], (W, H))
    tooth = fbm(2, [5, 3, 2], [1, 0.7, 0.5], (W, H))
    p = np.array(PAPER, np.float32)[None, None, :] * (0.965 + 0.05 * tone_[..., None]) * (0.975 + 0.035 * tooth[..., None])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = 1 - 0.10 * (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2)
    gut = 1 - 0.16 * np.exp(-xx / 26) - 0.05 * np.exp(-xx / 120)                       # binding gutter
    p *= (vig * gut)[..., None]
    im = Image.fromarray(p.clip(0, 255).astype(np.uint8)); d = ImageDraw.Draw(im, "RGBA")
    r = random.Random(5)
    for _ in range(260):                                                               # paper fibres
        x, y = r.uniform(0, W), r.uniform(0, H); a = r.uniform(0, 6.28); L = r.uniform(6, 22)
        d.line([(x, y), (x + L * math.cos(a), y + L * math.sin(a))], fill=(150, 130, 110, r.randint(14, 30)), width=1)
    for k in range(28):                                                                # stitches in the gutter
        y = 40 + k * 68; d.line([(18, y), (18, y + 34)], fill=(120, 104, 90, 120), width=3)
    return np.asarray(im).astype(np.float32), tooth.astype(np.float32)
PAPER_IMG, TOOTH = _paper()

# ---------- watercolour ----------
def blur(a, s): return gaussian_filter(a, s)
def sstep(a, b, x): x = np.clip((x - a) / (b - a), 0, 1); return x * x * (3 - 2 * x)

class Wash:
    """A watercolour wash from a mask. Precomputes density + a bloom order field; apply() multiplies it onto a canvas."""
    def __init__(self, mask, col, seed=0, strength=0.85, edge=1.0, origin=None, pad=24, bloom=0.22):
        m = np.asarray(mask).astype(np.float32) / 255
        ys, xs = np.where(m > 0.01)
        if len(xs) == 0: self.ok = False; return
        self.ok = True
        x0, x1 = max(0, xs.min() - pad), min(m.shape[1], xs.max() + pad)
        y0, y1 = max(0, ys.min() - pad), min(m.shape[0], ys.max() + pad)
        m = m[y0:y1, x0:x1]; hh, ww = m.shape
        n1 = fbm(seed, [40, 16, 6], [1, 0.6, 0.35], (ww, hh))
        m2 = sstep(0.32, 0.62, blur(m, 3.5) + (n1 - 0.5) * 0.32)
        edge_ = np.clip(m2 - blur(m2, 7), 0, 1)
        low = fbm(seed + 1, [160, 60], [1, 0.5], (ww, hh))
        tooth = TOOTH[y0:y1, x0:x1] if m.shape == TOOTH[y0:y1, x0:x1].shape else fbm(seed + 2, [5, 3, 2], [1, 0.7, 0.5], (ww, hh))
        dens = m2 * (0.62 + 0.32 * low) + edge_ * 1.5 * edge + m2 * (tooth - 0.5) * 0.28
        self.a = np.clip(dens * strength, 0, 1).astype(np.float32)
        self.c = (1 - np.array(col, np.float32) / 255)[None, None, :]
        self.x0, self.y0 = x0, y0
        yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
        ox, oy = (origin[0] - x0, origin[1] - y0) if origin else (0, hh / 2)
        dist = np.hypot(xx - ox, yy - oy); dist /= max(1, dist.max())
        self.order = (dist * 0.8 + (n1 - 0.5) * 0.3).astype(np.float32)
        self.bloom = bloom
    def apply(self, cv, u=1.0, dx=0, dy=0, mul=1.0):
        if not self.ok or u <= 0: return
        a = self.a if u >= 1 else self.a * sstep(0, self.bloom, u * (1 + self.bloom) - self.order)
        if mul != 1: a = a * mul
        x0, y0 = int(self.x0 + dx), int(self.y0 + dy); hh, ww = a.shape
        sx0, sy0 = max(0, -x0), max(0, -y0); X0, Y0 = max(0, x0), max(0, y0)
        X1, Y1 = min(W, x0 + ww), min(H, y0 + hh)
        if X1 <= X0 or Y1 <= Y0: return
        aa = a[sy0:sy0 + Y1 - Y0, sx0:sx0 + X1 - X0]
        cv[Y0:Y1, X0:X1] *= (1 - aa[..., None] * self.c)

def mask_poly(polys, size=(W, H), ell=None, width=None):
    im = Image.new("L", size, 0); d = ImageDraw.Draw(im)
    for p in polys or []:
        if width: d.line(p, fill=255, width=width, joint="curve")
        else: d.polygon(p, fill=255)
    for e in ell or []: d.ellipse(e, fill=255)
    return im

def spline(pts, n=8, closed=False):
    P = list(pts) + ([pts[0], pts[1], pts[2]] if closed else [])
    if not closed: P = [P[0]] + P + [P[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            s = k / n; s2, s3 = s * s, s * s * s
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * s + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * s2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * s3) for j in (0, 1)))
    out.append(P[-2]); return out

def partial(pts, u):
    if u >= 1: return pts
    if u <= 0 or len(pts) < 2: return []
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]; goal = sum(seg) * u; acc = 0; out = [pts[0]]
    for i, L in enumerate(seg):
        if acc + L >= goal:
            f = (goal - acc) / max(L, 1e-6); out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f)); break
        out.append(pts[i + 1]); acc += L
    return out

def pencil(d, pts, u=1.0, w=3, col=PENCIL, alpha=200, seed=0):
    p = partial(pts, u)
    if len(p) < 2: return
    r = random.Random(seed)
    d.line(p, fill=col + (alpha,), width=w, joint="curve")
    q = [(x + r.uniform(-1.4, 1.4), y + r.uniform(-1.4, 1.4)) for x, y in p]
    d.line(q, fill=col + (alpha // 3,), width=max(1, w - 1))

def hand(d, txt, size, cx, cy, col=INK, u=1.0, kind="hand", anchor="mm", alpha=255):
    """handwriting written on left->right (u = fraction of characters)."""
    if u <= 0: return
    f = F(kind, size)
    if u < 1:
        full = f.getlength(txt); n = max(0, int(len(txt) * u + 0.999)); part = txt[:n]
        x = cx - full / 2 if anchor == "mm" else cx
        d.text((x, cy), part, font=f, fill=col + (alpha,), anchor="lm")
    else:
        d.text((cx, cy), txt, font=f, fill=col + (alpha,), anchor=anchor)

def fit(txt, size, maxw=W - 160, kind="hand"):
    while F(kind, size).getlength(txt) > maxw and size > 40: size -= 4
    return size

def knock(cv, m, x, y):
    """lift paint back to clean paper under mask m (L image) - the sprite was painted 'around'."""
    a = np.asarray(m).astype(np.float32) / 255; hh, ww = a.shape; x, y = int(x), int(y)
    sx0, sy0 = max(0, -x), max(0, -y); X0, Y0 = max(0, x), max(0, y); X1, Y1 = min(W, x + ww), min(H, y + hh)
    if X1 > X0 and Y1 > Y0:
        aa = a[sy0:sy0 + Y1 - Y0, sx0:sx0 + X1 - X0][..., None]
        cv[Y0:Y1, X0:X1] = cv[Y0:Y1, X0:X1] * (1 - aa) + PAPER_IMG[Y0:Y1, X0:X1] * aa

def mult(cv, img, x, y):
    """multiply a white-background RGB PIL image onto the float canvas at (x, y)."""
    a = np.asarray(img).astype(np.float32) / 255; hh, ww = a.shape[:2]; x, y = int(x), int(y)
    sx0, sy0 = max(0, -x), max(0, -y); X0, Y0 = max(0, x), max(0, y); X1, Y1 = min(W, x + ww), min(H, y + hh)
    if X1 > X0 and Y1 > Y0: cv[Y0:Y1, X0:X1] *= a[sy0:sy0 + Y1 - Y0, sx0:sx0 + X1 - X0]

# ---------- sprites (built once, white background, multiplied) ----------
FORE = [(6, -6), (30, -52), (70, -100), (128, -128), (168, -124), (176, -104), (160, -62), (122, -22), (66, -2), (14, 2)]
HIND = [(8, 4), (60, 6), (106, 26), (128, 62), (120, 100), (96, 128), (84, 140), (82, 190), (68, 192), (64, 146),
        (40, 128), (16, 84), (6, 30)]
def butterfly_sprite(s, seed=1):
    """top-view swallowtail-like butterfly (generic). Returns (RGB white image, cx, cy) body centre in image coords."""
    pw, ph = int(380 * s), int(360 * s); cx, cy = pw / 2, 150 * s
    def P(pts, side): return [(cx + side * x * s, cy + y * s) for x, y in pts]
    cv = np.ones((ph, pw, 3), np.float32) * 255
    sz = (pw, ph)
    fore = [spline(P(FORE, sd), 6, True) for sd in (1, -1)]; hind = [spline(P(HIND, sd), 6, True) for sd in (1, -1)]
    wings = mask_poly(fore + hind, sz)
    def W_(m, col, sd, **k):
        w = Wash(m, col, sd, **k); w.apply(cv)
    W_(wings, YEL, seed, strength=0.9, edge=0.7)
    # dark margins (band along the edge), base and tiger stripes, minus pale margin spots
    band = mask_poly(fore + hind, sz, width=int(22 * s))
    dark = Image.new("L", sz, 0); dd = ImageDraw.Draw(dark)
    dark.paste(band, (0, 0), band)
    for sd in (1, -1):
        dd.polygon(P([(4, -8), (26, -40), (24, -4), (6, 4)], sd), fill=255)                         # wing base
        dd.polygon(P([(6, 6), (24, 8), (28, 50), (12, 50)], sd), fill=255)
        for a_, b_ in ((44, 52), (84, 93), (124, 132)):                                             # tiger stripes
            dd.polygon(P([(a_ + 14, -66 - a_ * 0.4), (b_ + 14, -70 - b_ * 0.4), (b_ - 12, -30), (a_ - 12, -26)], sd), fill=255)
        dd.polygon(P([(70, 140), (96, 128), (86, 192), (66, 192)], sd), fill=255)                   # tail
    dark = Image.fromarray(np.minimum(np.asarray(dark), np.asarray(wings)))
    dd = ImageDraw.Draw(dark)
    for sd in (1, -1):
        for k in range(6):                                                                        # pale margin spots
            u = (k + 0.5) / 6; p = spline(P(FORE, sd), 6, True)
            x, y = P([(150 - 18 * k, -112 + 17 * k)], sd)[0]
            dd.ellipse([x - 6 * s, y - 4 * s, x + 6 * s, y + 4 * s], fill=0)
        for k in range(4):
            x, y = P([(112 - 10 * k, 66 + 18 * k)], sd)[0]
            dd.ellipse([x - 7 * s, y - 5 * s, x + 7 * s, y + 5 * s], fill=0)
    W_(dark, DARK, seed + 2, strength=0.8, edge=0.5)
    spots = Image.new("L", sz, 0); ds = ImageDraw.Draw(spots); eye = Image.new("L", sz, 0); de = ImageDraw.Draw(eye)
    for sd in (1, -1):
        for k in range(4):
            x, y = P([(96 - 12 * k, 54 + 16 * k)], sd)[0]; ds.ellipse([x - 8 * s, y - 5 * s, x + 8 * s, y + 5 * s], fill=255)
        x, y = P([(52, 128)], sd)[0]; de.ellipse([x - 11 * s, y - 11 * s, x + 11 * s, y + 11 * s], fill=255)
    W_(spots, BLUE, seed + 3, strength=1.0); W_(eye, ORANGE, seed + 4, strength=1.0)
    body = mask_poly([], sz, ell=[[cx - 9 * s, cy - 40 * s, cx + 9 * s, cy + 90 * s], [cx - 11 * s, cy - 54 * s, cx + 11 * s, cy - 34 * s]])
    W_(body, DARK, seed + 5, strength=1.1)
    im = Image.fromarray(cv.clip(0, 255).astype(np.uint8)); d = ImageDraw.Draw(im, "RGBA")
    for sd in (1, -1):                                                                            # pencil outline + veins
        pencil(d, fore[0 if sd == 1 else 1] + [fore[0 if sd == 1 else 1][0]], 1, max(2, int(1.3 * s)), seed=sd)
        pencil(d, hind[0 if sd == 1 else 1] + [hind[0 if sd == 1 else 1][0]], 1, max(2, int(1.3 * s)), seed=sd + 4)
        for ex, ey in ((60, -96), (110, -122), (150, -120), (166, -96), (150, -58), (110, -24)):
            pencil(d, spline(P([(10, -4), (ex * 0.5, ey * 0.55 - 6), (ex, ey)], sd), 6), 1, 2, alpha=120, seed=ex)
        for ex, ey in ((104, 30), (122, 70), (108, 108), (84, 136), (50, 126)):
            pencil(d, spline(P([(10, 6), (ex * 0.5, ey * 0.5 + 4), (ex, ey)], sd), 6), 1, 2, alpha=120, seed=ex + 1)
        pencil(d, spline(P([(3, -50), (14, -90), (32, -126), (38, -138)], sd), 6), 1, max(2, int(1.2 * s)), col=INK, alpha=220)
        x, y = P([(38, -138)], sd)[0]; d.ellipse([x - 4 * s, y - 4 * s, x + 4 * s, y + 4 * s], fill=INK + (230,))
    km = Image.fromarray(np.maximum(np.asarray(wings), np.asarray(body))).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(3))
    return im, cx, cy, km

def leaf_sprite(w, h, seed=0, col=GREEN, angle=0.0, chewed=False):
    """leaf seen from above, tip pointing up. returns RGB white image (w x h), midrib points."""
    cv = np.ones((h, w, 3), np.float32) * 255; cx = w / 2
    L = [(cx, h * 0.97), (cx - w * 0.40, h * 0.62), (cx - w * 0.44, h * 0.36), (cx - w * 0.22, h * 0.12), (cx, h * 0.02),
         (cx + w * 0.24, h * 0.14), (cx + w * 0.45, h * 0.38), (cx + w * 0.40, h * 0.64)]
    outline = spline(L, 8, True)
    m = mask_poly([outline], (w, h))
    if chewed:
        dm = ImageDraw.Draw(m)
        for k in range(5): dm.ellipse([cx + w * 0.32 + 16 * math.sin(k), h * (0.32 + 0.07 * k) - 30, cx + w * 0.5 + 10, h * (0.32 + 0.07 * k) + 30], fill=0)
    Wash(m, col, seed, strength=0.85).apply(cv)
    half = mask_poly([[(cx, 0), (cx + w, 0), (cx + w, h), (cx, h)]], (w, h))
    half = Image.fromarray(np.minimum(np.asarray(half), np.asarray(m)))
    Wash(half, GREEN2, seed + 1, strength=0.35, edge=0.4).apply(cv)
    im = Image.fromarray(cv.clip(0, 255).astype(np.uint8)); d = ImageDraw.Draw(im, "RGBA")
    pencil(d, outline + [outline[0]], 1, 3, seed=seed)
    pencil(d, spline([(cx, h * 0.97), (cx + 4, h * 0.6), (cx, h * 0.25), (cx - 2, h * 0.04)], 8), 1, 3, seed=seed + 1)
    for k in range(1, 7):
        y = h * (0.88 - k * 0.11); sp = w * 0.36 * math.sin(math.pi * min(0.95, (1 - y / h) * 1.05))
        for sd in (1, -1):
            pencil(d, spline([(cx, y), (cx + sd * sp * 0.5, y - h * 0.035), (cx + sd * sp, y - h * 0.09)], 6), 1, 2, alpha=130, seed=k * sd)
    return im

def caterpillar_sprite(n=9, r=30, seed=0):
    w, h = int(n * r * 1.5 + r * 4), int(r * 5)
    cv = np.ones((h, w, 3), np.float32) * 255
    cents = [(r * 2 + i * r * 1.45, h * 0.6 - 0.35 * r * math.sin(i * 0.9)) for i in range(n)]
    Wash(mask_poly([], (w, h), ell=[[x - r, y - r, x + r, y + r] for x, y in cents]), (150, 196, 92), seed, strength=0.95).apply(cv)
    st = Image.new("L", (w, h), 0); ds = ImageDraw.Draw(st)
    for x, y in cents[1:]: ds.line([(x, y - r), (x, y + r)], fill=255, width=int(r * 0.2))
    st = Image.fromarray(np.minimum(np.asarray(st), np.asarray(mask_poly([], (w, h), ell=[[x - r, y - r, x + r, y + r] for x, y in cents]))))
    Wash(st, DARK, seed + 1, strength=0.75).apply(cv)
    dots = mask_poly([], (w, h), ell=[[x + r * 0.3 - 6, y - r * 0.6 - 6, x + r * 0.3 + 6, y - r * 0.6 + 6] for x, y in cents[1:]])
    Wash(dots, YEL, seed + 2, strength=1.0).apply(cv)
    im = Image.fromarray(cv.clip(0, 255).astype(np.uint8)); d = ImageDraw.Draw(im, "RGBA")
    for x, y in cents: d.ellipse([x - r, y - r, x + r, y + r], outline=PENCIL + (170,), width=2)
    hx, hy = cents[-1]
    d.ellipse([hx + r * 0.2, hy - r * 0.4, hx + r * 0.5, hy - r * 0.1], fill=INK + (240,))
    for x, y in cents[1:-1:2]: d.line([(x, y + r), (x - 4, y + r + 12)], fill=INK + (200,), width=4)
    return im

# ---------- shared scene pieces ----------
BF_BIG = butterfly_sprite(2.15, 1)
BF_KNOB = butterfly_sprite(0.72, 7)
BF_SMALL = butterfly_sprite(0.55, 9)
LEAF_HOOK = leaf_sprite(900, 1150, 11)
LEAF_A = leaf_sprite(430, 560, 21)
LEAF_B = leaf_sprite(430, 560, 31, col=(170, 160, 92))
LEAF_C = leaf_sprite(600, 760, 41, chewed=True)
CAT = caterpillar_sprite(9, 30, 3)
LEAF_SIDE = leaf_sprite(330, 1040, 51).rotate(-90, expand=True, fillcolor=(255, 255, 255)).resize((1040, 380))

def put_butterfly(cv, spr, x, y, k=1.0, k2=None):
    """paste butterfly with body centre at (x, y); k = wing width factor (flap)."""
    im, cx, cy, km = spr; w, h = im.size
    k2 = k if k2 is None else k2
    for src in (km, im):
        R = src.crop((int(cx), 0, w, h)); Lh = src.crop((0, 0, int(cx), h))
        rw, lw = max(4, int(R.size[0] * k)), max(4, int(Lh.size[0] * k2))
        fn = knock if src is km else mult
        fn(cv, R.resize((rw, h), Image.BILINEAR), x, y - cy)
        fn(cv, Lh.resize((lw, h), Image.BILINEAR), x - lw, y - cy)

def header(d, page):
    d.text((90, 92), "Field journal  ·  Lepidoptera", font=F("handr", 40), fill=PENCIL + (200,), anchor="lm")
    d.text((W - 80, 92), f"p. {page}", font=F("handr", 40), fill=PENCIL + (200,), anchor="rm")
    d.line([(86, 128), (W - 80, 126)], fill=PENCIL + (90,), width=2)

def underline_wash(cv, x0, x1, y, col, u, seed):
    if u <= 0: return
    key = (int(x0), int(x1), int(y), col, seed)
    if key not in _UL:
        pts = [(x0 + (x1 - x0) * i / 10, y + 6 * math.sin(i * 1.3 + seed)) for i in range(11)]
        _UL[key] = Wash(mask_poly([pts], width=34), col, seed, strength=0.8, origin=(x0, y), bloom=0.15)
    _UL[key].apply(cv, u)
_UL = {}

def word_t(ln, i): return words[min(ln["_w0"] + i, ln["_w1"] - 1)][1] - ln["_s"]

# ---------- scenes: (cv float canvas, d=None) -> washes first, then a draw callback for pencil/ink ----------
def S_hook(cv, sc, ln, lt, dur, t):
    mult(cv, LEAF_HOOK.resize((760, 970)), 160, 640)
    k = 0.86 + 0.14 * math.cos(t * 2.2)
    put_butterfly(cv, BF_BIG, W / 2 + 10, 1040 + 6 * math.sin(t * 1.1), k)
    title = ["This butterfly", "is tasting", "with its feet."]
    def ink(d):
        header(d, 19)
        for i, s in enumerate(title):
            d.text((W / 2, 260 + i * 140), s, font=F("hand", 128), fill=INK + (255,), anchor="mm")
        if sc.get("loop"):
            u = eout(lt / 0.5)
            hand(d, "...but tasting for WHAT?", 64, W / 2, 1490, RED, u=u)
        else:
            hand(d, "(yes, really. its feet.)", 50, W / 2, 668, PENCIL, u=eout((lt - 0.6) / 0.6), kind="handr")
    f = F("hand", 128); lw = f.getlength("with its feet."); fx = W / 2 - lw / 2 + f.getlength("with its ")
    underline_wash(cv, fx - 6, fx + f.getlength("feet") + 6, 556, ORANGE, 1.0, 2)   # "feet" marked from frame 0
    return ink

FOOT_SEG = [(150, 640), (330, 820), (470, 930), (580, 1010), (680, 1080), (770, 1150), (860, 1230), (930, 1300)]
def S_foot(cv, sc, ln, lt, dur, t):
    u = eout(lt / 1.0)
    if "_fw" not in sc:
        sc["_fw"] = Wash(mask_poly([FOOT_SEG], width=52), (150, 118, 90), 51, strength=0.55, origin=FOOT_SEG[0], bloom=0.25)
        sc["_fw2"] = Wash(mask_poly([], ell=[[x - 70, y - 50, x + 70, y + 50] for x, y in FOOT_SEG[3:]]), YEL, 52, strength=0.55, origin=FOOT_SEG[-1])
    sc["_fw"].apply(cv, u)
    glow = eout((lt - 1.0) / 0.8)
    sc["_fw2"].apply(cv, glow)
    def ink(d):
        header(d, 20)
        hand(d, "Fig. 2 — the foot", 96, W / 2, 300, INK, u=1)
        d.text((W / 2, 400), "tarsus, much enlarged", font=F("latin", 56), fill=PENCIL + (230,), anchor="mm")
        for i in range(len(FOOT_SEG) - 1):                               # tapered segments, pencil outlines
            v = min(1, max(0, u * (len(FOOT_SEG) - 1) - i))
            if v <= 0: break
            (x0, y0), (x1, y1) = FOOT_SEG[i], FOOT_SEG[i + 1]; L = math.hypot(x1 - x0, y1 - y0)
            nx, ny = -(y1 - y0) / L, (x1 - x0) / L; w0, w1 = 30 - i * 2.6, 27 - i * 2.6
            pencil(d, [(x0 + nx * w0, y0 + ny * w0), (x0 + (x1 - x0) * v + nx * w1, y0 + (y1 - y0) * v + ny * w1)], 1, 3, col=INK, alpha=210, seed=i)
            pencil(d, [(x0 - nx * w0, y0 - ny * w0), (x0 + (x1 - x0) * v - nx * w1, y0 + (y1 - y0) * v - ny * w1)], 1, 3, col=INK, alpha=210, seed=i + 9)
            if v >= 1: d.line([(x1 + nx * w1, y1 + ny * w1), (x1 - nx * w1, y1 - ny * w1)], fill=INK + (200,), width=3)
        if u >= 1:
            x, y = FOOT_SEG[-1]
            for sd in (-1, 1): pencil(d, [(x, y), (x + 40, y + 10 + sd * 26), (x + 46, y + 40 + sd * 10)], 1, 5, col=INK)
        r = random.Random(4)
        for k in range(40):                                              # taste sensors: tiny hairs that light up
            i = r.randrange(3, len(FOOT_SEG) - 1); f = r.random()
            (x0, y0), (x1, y1) = FOOT_SEG[i], FOOT_SEG[i + 1]; x, y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
            a = r.uniform(0, 6.28); L = r.uniform(14, 30)
            vis = eout((lt - 0.7 - k * 0.02) / 0.3)
            if vis <= 0: continue
            d.line([(x, y), (x + L * math.cos(a), y + L * math.sin(a))], fill=INK + (int(200 * vis),), width=2)
            on = 0.5 + 0.5 * math.sin(t * 7 + k)
            if glow > 0: d.ellipse([x + L * math.cos(a) - 5, y + L * math.sin(a) - 5, x + L * math.cos(a) + 5, y + L * math.sin(a) + 5], fill=ORANGE + (int(255 * glow * on),))
        v = eout((lt - 1.1) / 0.5)
        hand(d, "taste sensors!", 88, 330, 1290, RED, u=v)
        pencil(d, spline([(420, 1225), (560, 1150), (690, 1095)], 6), v, 4, col=RED, seed=6)
        if v >= 1:
            d.line([(690, 1095), (650, 1092)], fill=RED + (220,), width=4); d.line([(690, 1095), (668, 1126)], fill=RED + (220,), width=4)
    return ink

def side_butterfly(d, cv, x, y, s, lt, tap=True):
    """side view facing right: wings folded up over the thorax, body level, three legs on the leaf; the front leg drums.
    (x, y) = thorax point, leaf surface at y + 70*s."""
    key = ("side", s)
    if key not in _SIDE:
        w, h = int(360 * s), int(380 * s); ox, oy = w * 0.5, h * 0.80
        c2 = np.ones((h, w, 3), np.float32) * 255
        def P(pts): return [(ox + px * s, oy + py * s) for px, py in pts]
        fw = spline(P([(22, -8), (40, -110), (40, -210), (10, -280), (-40, -270), (-70, -200), (-40, -90), (-8, -10)]), 8, True)
        hw = spline(P([(-6, -6), (-60, -40), (-120, -70), (-150, -120), (-120, -170), (-60, -150), (-20, -80)]), 8, True)
        body = [P([(-120, -14)])[0] + P([(40, 12)])[0]]
        wm = mask_poly([hw, fw], (w, h))
        Wash(wm, YEL, 61, strength=0.9).apply(c2)
        dm = mask_poly([fw, hw], (w, h), width=int(18 * s)); dd0 = ImageDraw.Draw(dm)
        for a_ in (-250, -200, -150):
            dd0.polygon(P([(-46, a_ + 26), (30, a_ + 10), (34, a_ + 26), (-40, a_ + 44)]), fill=255)
        dd0.ellipse(P([(-100, -130)])[0] + P([(-70, -100)])[0], fill=255)
        dm = Image.fromarray(np.minimum(np.asarray(dm), np.asarray(wm)))
        Wash(dm, DARK, 62, strength=0.8).apply(c2)
        Wash(mask_poly([], (w, h), ell=[P([(-140, -100)])[0] + P([(-122, -82)])[0]]), BLUE, 64, strength=1.0).apply(c2)
        bm = mask_poly([], (w, h), ell=body)
        Wash(bm, DARK, 63, strength=1.0).apply(c2)
        im = Image.fromarray(c2.clip(0, 255).astype(np.uint8)); dd = ImageDraw.Draw(im, "RGBA")
        pencil(dd, hw + [hw[0]], 1, 3, seed=1); pencil(dd, fw + [fw[0]], 1, 3, seed=2)
        for k in range(5):
            pencil(dd, spline(P([(10, -12), (0 - k * 10, -120 - k * 10), (-20 - k * 10, -230 + k * 20)]), 6), 1, 2, alpha=110, seed=k)
        km = Image.fromarray(np.maximum(np.asarray(wm), np.asarray(bm))).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(3))
        _SIDE[key] = (im, ox, oy, km)
    im, ox, oy, km = _SIDE[key]
    knock(cv, km, x - ox, y - oy); mult(cv, im, x - ox, y - oy)
    ground = y + 70 * s
    def ink(d):
        hx, hy = x + 56 * s, y - 4 * s
        d.ellipse([hx - 17 * s, hy - 17 * s, hx + 17 * s, hy + 17 * s], fill=DARK + (245,))
        d.ellipse([hx + 2 * s, hy - 9 * s, hx + 12 * s, hy + 1 * s], fill=(90, 80, 70, 255))
        for k in range(2):
            pencil(d, spline([(hx + 6 * s, hy - 12 * s), (hx + (40 + 16 * k) * s, hy - 80 * s), (hx + (70 + 26 * k) * s, hy - 140 * s)], 6), 1, max(2, int(2 * s)), col=INK, alpha=230)
            ax, ay = hx + (70 + 26 * k) * s, hy - 140 * s; d.ellipse([ax - 6 * s, ay - 6 * s, ax + 6 * s, ay + 6 * s], fill=INK + (240,))
        pc = [(hx + 16 * s + 9 * s * math.cos(a), hy + 26 * s + 9 * s * math.sin(a)) for a in np.linspace(-1.5, 4.3, 12)]
        pencil(d, pc, 1, max(2, int(2 * s)), col=INK)                    # curled proboscis
        foot_out = None
        for i, lx in enumerate((-36, -6, 30)):
            kx, ky = x + lx * s, y + 8 * s
            lift = 0
            if tap and i == 2: lift = max(0, math.sin(((lt * 7.0) % 1.0) * math.pi)) * 26 * s
            knee = (kx + (24 if i == 2 else 10 - 12 * i) * s, ky + 26 * s - lift * 0.5)
            foot = (kx + (46 if i == 2 else 4 - 14 * i) * s, ground - lift)
            pencil(d, [(kx, ky), knee, foot], 1, max(3, int(3 * s)), col=INK, alpha=240, seed=i)
            if i == 2: foot_out = (foot[0], ground)
        return foot_out
    return ink
_SIDE = {}

def S_drum(cv, sc, ln, lt, dur, t):
    mult(cv, LEAF_SIDE, 30, 1080)
    ink_b = side_butterfly(None, cv, 470, 1150, 1.6, lt)
    def ink(d):
        header(d, 21)
        hand(d, "She drums", 120, W / 2, 300, INK, u=1)
        hand(d, "the leaf.", 120, W / 2, 440, INK, u=1)
        foot = ink_b(d)
        ph = (lt * 7.0) % 1.0
        if lt > 0.3:
            for k in range(3):                                           # tap marks
                a = 0.4 + k * 0.5; rr = 22 + 18 * ((lt * 7.0 + k * 0.3) % 1.0)
                d.arc([foot[0] - rr, foot[1] - rr * 0.5, foot[0] + rr, foot[1] + rr * 0.5], 200, 340, fill=RED + (int(220 * (1 - ((lt * 7 + k * 0.3) % 1))),), width=3)
        n = min(4, int(lt / 0.55))
        for i in range(n):
            d.text((700 + i * 80, 820 - (i % 2) * 50), "tap", font=F("hand", 60), fill=RED + (230,), anchor="mm")
        hand(d, "front legs", 50, 840, 1480, PENCIL, u=eout((lt - 1.2) / 0.5), kind="handr")
    return ink

DROPS = [(380, 1080), (560, 1160), (720, 1040), (470, 1260), (650, 1300)]
def S_juice(cv, sc, ln, lt, dur, t):
    mult(cv, LEAF_HOOK.resize((820, 1048)), 130, 620)
    if "_dw" not in sc:
        sc["_dw"] = [Wash(mask_poly([], ell=[[x - 52, y - 40, x + 52, y + 40]]), (96, 168, 72), 70 + i, strength=1.0, origin=(x, y), bloom=0.3) for i, (x, y) in enumerate(DROPS)]
    for i, w in enumerate(sc["_dw"]): w.apply(cv, eout((lt - 0.4 - i * 0.22) / 0.6))
    def ink(d):
        header(d, 22)
        hand(d, "Tap... and taste", 112, W / 2, 300, INK, u=1)
        d.text((W / 2, 420), "the leaf's own juices", font=F("latin", 64), fill=PENCIL + (240,), anchor="mm")
        for i, (x, y) in enumerate(DROPS):                               # scratch marks
            v = eout((lt - 0.2 - i * 0.22) / 0.25)
            if v > 0:
                for k in range(2): pencil(d, [(x - 20 + k * 16, y - 18), (x - 14 + k * 16, y - 18 + 34 * v)], 1, 3, col=INK, alpha=190, seed=i * 3 + k)
        v = eout((lt - 1.4) / 0.6)
        if v > 0:
            cx, cy = 820, 760
            for k in range(6):                                           # little hexagon "chemical" doodle
                a0, a1 = k * math.pi / 3, (k + 1) * math.pi / 3
                pencil(d, [(cx + 50 * math.cos(a0), cy + 50 * math.sin(a0)), (cx + 50 * math.cos(a1), cy + 50 * math.sin(a1))], v, 3, col=INK)
            hand(d, "plant chemicals", 54, 640, 870, INK, u=v, kind="handr")
    return ink

def S_babies(cv, sc, ln, lt, dur, t):
    mult(cv, LEAF_C, 240, 720)
    if "_cw" not in sc:
        sc["_cw"] = Wash(mask_poly([[(160, 600), (930, 600)]], width=10), RED, 80, strength=0.9, origin=(160, 600), bloom=0.1)
    tb = word_t(ln, 4)
    cu = eout((lt - tb) / 0.8)
    if cu > 0: mult(cv, CAT, 330 - (1 - cu) * 120, 1000 + 4 * math.sin(t * 6))
    def ink(d):
        header(d, 23)
        v = eout(lt / 0.3)
        hand(d, "lunch?", 120, W / 2, 330, INK, u=v)
        s = eout((lt - 0.7) / 0.35)
        if s > 0: pencil(d, [(W / 2 - 200, 340), (W / 2 + 200, 320)], s, 9, col=RED, alpha=230, seed=4)
        hand(d, "food for her babies", 96, W / 2, 500, INK, u=eout((lt - tb + 0.3) / 0.7))
        hand(d, "Is this plant safe?", 58, W / 2, 620, PENCIL, u=eout((lt - tb - 0.6) / 0.6), kind="handr")
        if cu > 0:
            d.text((560, 1468), "caterpillar", font=F("latin", 60), fill=INK + (int(240 * cu),), anchor="mm")
            pencil(d, spline([(560, 1430), (600, 1320), (640, 1150)], 6), cu, 3, seed=8)
    return ink

def FLY(f): return (800 + 330 * f, 1000 - 260 * f + 60 * math.sin(f * 7))
def S_verdict(cv, sc, ln, lt, dur, t):
    mult(cv, LEAF_A, 70, 760); mult(cv, LEAF_B, 580, 760)
    t2 = word_t(ln, 6)                                                   # "Wrong plant?"
    def ink(d):
        header(d, 24)
        hand(d, "right plant", 76, 285, 640, GREEN2, u=1)
        hand(d, "wrong plant", 76, 795, 640, RED, u=eout((lt - t2 + 0.2) / 0.4))
        v = eout((lt - 0.6) / 0.4)
        if v > 0: pencil(d, [(220, 1400), (270, 1460), (370, 1340)], v, 10, col=GREEN2, alpha=240)
        r = random.Random(3)
        for k in range(7):                                               # eggs appear one by one
            e = eout((lt - 0.9 - k * 0.12) / 0.2)
            if e <= 0: continue
            x, y = 230 + (k % 4) * 42 + r.uniform(-6, 6), 1060 + (k // 4) * 50
            d.ellipse([x - 14 * e, y - 18 * e, x + 14 * e, y + 18 * e], fill=(250, 238, 190, 255), outline=PENCIL + (220,), width=2)
        w2 = eout((lt - t2 - 0.6) / 0.4)
        if w2 > 0:
            pencil(d, [(720, 1340), (880, 1460)], w2, 10, col=RED, alpha=240)
            pencil(d, [(880, 1340), (720, 1460)], w2, 10, col=RED, alpha=240, seed=2)
        hand(d, "Lay eggs", 96, 285, 420, INK, u=eout((lt - 0.3) / 0.4))
        hand(d, "Fly away", 96, 795, 420, INK, u=eout((lt - t2 - 0.2) / 0.4))
        if lt > t2:
            f = eout((lt - t2) / 1.6)
            path = [FLY(f * i / 24) for i in range(25)]
            for i in range(0, len(path) - 1, 2): d.line([path[i], path[i + 1]], fill=PENCIL + (200,), width=3)
    if lt <= t2: put_butterfly(cv, BF_SMALL, 800, 1000, 0.85 + 0.15 * math.cos(t * 3))
    else:
        f = eout((lt - t2) / 1.6)
        put_butterfly(cv, BF_SMALL, *FLY(f), abs(math.cos(t * 9)) * 0.8 + 0.2)
    return ink

def S_end(cv, sc, ln, lt, dur, t):
    click = sc.get("click_at", 0.45)
    on = eout((lt - click) / 0.35)
    x0, x1, y = 230, 850, 1010
    if "_tw" not in sc:
        sc["_tw"] = Wash(mask_poly([[(x0 + 20, y), (x1 - 20, y)]], width=150), GREEN, 90, strength=0.75, origin=(x0, y), bloom=0.2)
        sc["_rw"] = Wash(mask_poly([[(x0 + 20, y), (x1 - 20, y)]], width=150), (210, 170, 160), 91, strength=0.35, origin=(x1, y))
    sc["_rw"].apply(cv, 1 - on * 0.9 if on < 1 else 0.0)
    sc["_tw"].apply(cv, on)
    kx = x0 + 75 + (x1 - x0 - 150) * on
    put_butterfly(cv, BF_KNOB, kx, y - 10, 0.55 + 0.4 * abs(math.cos(t * (9 if 0 < on < 1 else 2.5))))
    def ink(d):
        header(d, 25)
        hand(d, "Sounds fake?", 128, W / 2, 330, INK, u=1)
        d.rounded_rectangle([x0, y - 90, x1, y + 90], radius=90, outline=PENCIL + (220,), width=5)
        d.text((x0 - 20, y + 200), "FAKE", font=F("hand", 72), fill=(INK if on < 0.5 else PENCIL) + (255 if on < 0.5 else 120,), anchor="lm")
        d.text((x1 + 20, y + 200), "TRUE", font=F("hand", 72), fill=(GREEN2 if on >= 0.5 else PENCIL) + (255 if on >= 0.5 else 120,), anchor="rm")
        if on > 0.6:
            w_ = eout((lt - click - 0.25) / 0.35)
            hand(d, "It's true.", 150, W / 2, 560, GREEN2, u=w_)
            hand(d, "Follow for more.", 84, W / 2, 1420, INK, u=eout((lt - click - 0.5) / 0.4))
    return ink

SCENES = dict(hook=S_hook, foot=S_foot, drum=S_drum, juice=S_juice, babies=S_babies, verdict=S_verdict, end=S_end)

# ---------- audio: nylon-string arpeggios + pad + woodblock taps ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.22, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32); tt = np.arange(n) / SR
def pluck(f, dur=1.8, seed=0):
    N = int(SR / f); buf = np.random.default_rng(seed).uniform(-1, 1, N).astype(np.float32)
    out = np.zeros(int(dur * SR), np.float32)
    for i in range(len(out)):
        out[i] = buf[i % N]; buf[i % N] = 0.5 * (buf[i % N] + buf[(i + 1) % N]) * 0.996
    return out
CH = [[146.83, 220.0, 293.66, 369.99], [123.47, 185.0, 246.94, 293.66], [98.0, 196.0, 246.94, 293.66], [110.0, 220.0, 277.18, 329.63]]
_pl = {}
BEAT = 0.3
for k in range(int(total / BEAT)):
    ch = CH[(k // 8) % 4]; pat = [0, 2, 1, 3, 2, 3, 1, 2][k % 8]; f = ch[pat]
    if f not in _pl: _pl[f] = pluck(f, 1.6, int(f))
    place(music, 0.05 + k * BEAT, _pl[f], 0.16 if k % 8 == 0 else 0.10)
for i, ch in enumerate(CH * 8):
    a = i * BEAT * 8
    if a > total: break
    s = np.arange(int(BEAT * 8 * SR + SR)) / SR; env = np.minimum(1, s / 0.6) * np.minimum(1, (s[-1] - s) / 0.6)
    place(music, a, (sum(np.sin(2 * np.pi * f * 2 * s) for f in ch[1:]) * env * 0.05).astype(np.float32), 1.0)
def block(at, gain):
    s = np.arange(int(0.08 * SR)) / SR
    place(music, at, (np.sin(2 * np.pi * 1250 * s) * np.exp(-s * 70)).astype(np.float32), gain)
hook_hit(music, 0.3)
for s_ in scene_starts(spec): whoosh(music, s_, 0.13)
for ln in spec["lines"]:
    typ = ln["scene"]["type"]
    if typ == "drum":
        k = 0.3
        while k < ln["_se"] - ln["_s"] - 0.2:
            block(ln["_s"] + k, 0.12); k += 1 / 7.0
    if typ == "end":
        place(music, ln["_s"] + ln["scene"].get("click_at", 0.45), tone(587.33, 1.6, decay=3, harm=(1, 2, 3)), 0.14)
        place(music, ln["_s"] + ln["scene"].get("click_at", 0.45) + 0.12, tone(880.0, 1.4, decay=3, harm=(1, 2)), 0.10)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.4)

# ---------- compose ----------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 76
    while F("bold", size).getlength(" ".join(ws)) > W - 260 and size > 36: size -= 4
    f = F("bold", size); tw = f.getlength(" ".join(ws)); x = (W - tw) / 2; y = 1588
    d = ImageDraw.Draw(img, "RGBA"); r = random.Random(gi)
    x0, x1, y0, y1 = x - 40, x + tw + 40, y - 22, y + size + 26
    d.polygon([(x0 + 4, y0 + 8), (x1 + 2, y0 + 2), (x1 - 2, y1 + 6), (x0 - 2, y1)], fill=(60, 50, 40, 40))     # shadow
    d.polygon([(x0, y0), (x1, y0 + r.uniform(-4, 4)), (x1 + r.uniform(-3, 3), y1), (x0 + r.uniform(-3, 3), y1)], fill=(255, 253, 246, 252))
    for tx in (x0 + 10, x1 - 70):                                                                       # washi tape
        d.polygon([(tx, y0 - 16), (tx + 64, y0 - 22), (tx + 70, y0 + 12), (tx + 6, y0 + 18)], fill=(232, 150, 120, 150))
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]
        if on: d.rectangle([x - 6, y + size * 0.55, x + f.getlength(w) + 6, y + size * 1.02], fill=YEL + (200,))
        d.text((x, y), w, font=f, fill=(20, 18, 24, 255)); x += f.getlength(w + " ")

def page(t):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    cv = PAPER_IMG.copy()
    ink = SCENES[ln["scene"]["type"]](cv, ln["scene"], ln, lt, dur, t)
    img = Image.fromarray(cv.clip(0, 255).astype(np.uint8)).convert("RGBA")
    ink(ImageDraw.Draw(img, "RGBA"))
    return img, ln

TURN = 0.32
def frame(t, fi):
    img, ln = page(t)
    i = spec["lines"].index(ln); u = t - ln["_s"]
    if i > 0 and 0 <= u < TURN and spec["lines"][i - 1]["scene"]["type"] != ln["scene"]["type"]:
        prev, _ = page(ln["_s"] - 0.04)
        x = int(W * (1 - eout(u / TURN)))
        base = prev.copy()
        sh = Image.new("RGBA", (60, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
        for k in range(60): ds.line([(k, 0), (k, H)], fill=(40, 30, 20, int(70 * (1 - k / 60))))
        base.alpha_composite(img.crop((0, 0, W - x, H)), (x, 0))
        if x > 0: base.alpha_composite(sh.transpose(Image.FLIP_LEFT_RIGHT), (max(0, x - 60), 0))
        img = base
    caption(img, t)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, H - 12, W, H], fill=(214, 204, 186, 255)); d.rectangle([0, H - 12, int(W * t / total), H], fill=GREEN2 + (255,))
    return img.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=24); print(f"done {total:.1f}s")
