"""Day 16 — RETRO-AD style (hippos secrete a red 'sunscreen').
A 1960s magazine advertisement come to life: cream coated paper, a rotating mustard sunburst disc, a flat
mid-century hippo with a glossy red-orange sheen, chunky slab headlines with misregistered offset shadows,
Pacifico script taglines, NEW!/BUT WAIT! starburst badges, dashed coupons, paint-chip swatches, a lotion tube,
and an appliance-dial FAKE -> TRUE ending. Bossa-lounge vibraphone jingle.
Everything is drawn at 2x and reduced, so shapes are anti-aliased.
Usage: python3 engine/styles/day16_retroad.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
S = 2                                                     # supersampling factor
PAPER = (245, 234, 208); INK = (58, 40, 32); CORAL = (226, 78, 56); TEAL = (40, 150, 146)
MUST = (242, 180, 62); MUST_L = (248, 218, 150); ORANGE = (240, 130, 50); HIP = (150, 140, 182)
HIP_D = (112, 102, 146); HIP_L = (182, 174, 208); PINK = (236, 160, 160); GERM = (128, 168, 84)

_fc = {}
def F(name, size, w=None):
    k = (name, int(size), w)
    if k not in _fc:
        f = ImageFont.truetype(f"{FONTS}/{name}", int(size))
        if w: f.set_variation_by_axes([w])
        _fc[k] = f
    return _fc[k]
SLAB = lambda s: F("AlfaSlabOne-Regular.ttf", s * S)
SCRIPT = lambda s: F("Pacifico-Regular.ttf", s * S)
COND = lambda s, w=600: F("Oswald-VF.ttf", s * S, w)

# ---------- paper ----------
rng = np.random.default_rng(16)
_p = np.full((H, W, 3), PAPER, np.float32) + rng.normal(0, 4.5, (H, W, 1))
yy, xx = np.mgrid[0:H, 0:W]
edge = np.minimum(np.minimum(xx, W - xx), np.minimum(yy, H - yy)).astype(np.float32)
_p *= (0.9 + 0.1 * np.clip(edge / 90, 0, 1))[..., None]
_fib = Image.fromarray(rng.normal(0, 1, (H // 4, W // 4)).astype(np.float32)).resize((W, H), Image.BICUBIC)
_p += np.asarray(_fib)[..., None] * 3
BASE = Image.fromarray(_p.clip(0, 255).astype(np.uint8)).resize((W * S, H * S), Image.BILINEAR)

# ---------- drawing helpers (1x coordinates, drawn on a 2x canvas) ----------
class P:
    def __init__(self, img): self.img = img; self.d = ImageDraw.Draw(img, "RGBA" if img.mode in ("RGB", "RGBA") else None)
    def _b(self, b): return [v * S for v in b]
    def ell(self, b, fill=None, outline=None, width=0): self.d.ellipse(self._b(b), fill=fill, outline=outline, width=int(width * S))
    def circ(self, cx, cy, r, **k): self.ell([cx - r, cy - r, cx + r, cy + r], **k)
    def rect(self, b, fill=None, outline=None, width=0): self.d.rectangle(self._b(b), fill=fill, outline=outline, width=int(width * S))
    def rrect(self, b, r, fill=None, outline=None, width=0): self.d.rounded_rectangle(self._b(b), int(r * S), fill=fill, outline=outline, width=int(width * S))
    def poly(self, pts, fill=None, outline=None, width=0):
        self.d.polygon([(x * S, y * S) for x, y in pts], fill=fill, outline=outline, width=int(width * S))
    def line(self, pts, fill, width, joint="curve"):
        self.d.line([(x * S, y * S) for x, y in pts], fill=fill, width=int(width * S), joint=joint)
        for (x, y) in (pts[0], pts[-1]): self.circ(x, y, width / 2 - 0.5, fill=fill)
    def tlen(self, s, f): return self.d.textlength(s, font=f) / S
    def text(self, xy, s, f, fill, anchor="mm", shadow=None, off=(6, 6)):
        x, y = xy
        if shadow: self.d.text(((x + off[0]) * S, (y + off[1]) * S), s, font=f, fill=shadow, anchor=anchor)
        self.d.text((x * S, y * S), s, font=f, fill=fill, anchor=anchor)

def fit(p, s, ff, size, maxw):
    while p.tlen(s, ff(size)) > maxw and size > 30: size -= 4
    return size

def head(p, s, y, size, fill=INK, shadow=TEAL, ff=SLAB, maxw=960, off=(7, 7)):
    size = fit(p, s, ff, size, maxw); p.text((W / 2, y), s, ff(size), fill, shadow=shadow, off=off); return size

def star(p, cx, cy, r, text, rot=0.0, fill=CORAL, tcol=PAPER, n=18, tsize=None, lines=None):
    pts = []
    for k in range(n * 2):
        a = rot + math.pi * k / n; rr = r if k % 2 == 0 else r * 0.8
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    p.poly([(x + 6, y + 6) for x, y in pts], fill=INK + (90,))
    p.poly(pts, fill=fill)
    p.circ(cx, cy, r * 0.68, outline=PAPER + (160,), width=3)
    lines = lines or [text]; ts = tsize or r * 0.5
    for i, ln in enumerate(lines):
        p.text((cx, cy + (i - (len(lines) - 1) / 2) * ts * 1.05), ln, SLAB(ts), tcol)

def kicker(p, y=150):
    """Small 'ADVERTISEMENT' line at the top of the page, like a magazine ad."""
    f = COND(26, 500); s = "A D V E R T I S E M E N T"; tw = p.tlen(s, f)
    p.text((W / 2, y), s, f, INK + (170,))
    p.line([(120, y), (W / 2 - tw / 2 - 24, y)], INK + (120,), 2); p.line([(W / 2 + tw / 2 + 24, y), (W - 120, y)], INK + (120,), 2)

# ---------- sunburst disc ----------
RR = 560
def _rays():
    img = Image.new("RGBA", (2 * RR * S, 2 * RR * S), (0, 0, 0, 0)); d = ImageDraw.Draw(img); c = RR * S; n = 28
    d.ellipse([0, 0, 2 * c, 2 * c], fill=MUST_L)
    for k in range(n):
        if k % 2: continue
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        d.polygon([(c, c), (c + 2 * c * math.cos(a0), c + 2 * c * math.sin(a0)), (c + 2 * c * math.cos(a1), c + 2 * c * math.sin(a1))], fill=MUST)
    return img
RAYS = _rays()
MASK = Image.new("L", RAYS.size, 0); ImageDraw.Draw(MASK).ellipse([0, 0, RAYS.size[0] - 1, RAYS.size[1] - 1], fill=255)

def sunburst(p, cx, cy, r, t, speed=5.0):
    sc = r / RR; rot = RAYS.rotate(t * speed, resample=Image.BICUBIC)
    if abs(sc - 1) > 1e-3:
        sz = (int(RAYS.size[0] * sc), int(RAYS.size[1] * sc)); rot = rot.resize(sz, Image.BILINEAR); m = MASK.resize(sz, Image.BILINEAR)
    else: m = MASK
    p.circ(cx + 8, cy + 10, r, fill=INK + (60,))
    p.img.paste(rot.convert("RGB"), (int((cx - r) * S), int((cy - r) * S)), m)
    p.circ(cx, cy, r, outline=CORAL, width=8); p.circ(cx, cy, r - 16, outline=PAPER, width=4)

# ---------- hippo sprite ----------
HW, HH = 780, 540
def _hippo(blink=False):
    img = Image.new("RGBA", (HW * S, HH * S), (0, 0, 0, 0)); p = P(img)
    def body(fill, dx=0, dy=0):
        o = lambda b: [b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy]
        for x in (130, 230, 380, 470): p.rrect(o([x, 330, x + 92, 500]), 40, fill=fill)
        p.ell(o([60, 120, 580, 450]), fill=fill)
        p.ell(o([430, 60, 700, 340]), fill=fill)
        p.rrect(o([520, 170, 760, 390]), 100, fill=fill)
        p.ell(o([462, 30, 516, 100]), fill=fill); p.ell(o([520, 22, 574, 92]), fill=fill)
        p.line([(70 + dx, 270 + dy), (36 + dx, 300 + dy)], fill, 16)
    body(INK + (255,), 9, 9)                               # misregistered print shadow
    body(HIP + (255,))
    for x in (130, 230, 380, 470): p.rrect([x, 330, x + 92, 500], 40, fill=HIP_D)
    p.ell([60, 120, 580, 450], fill=HIP); p.ell([430, 60, 700, 340], fill=HIP); p.rrect([520, 170, 760, 390], 100, fill=HIP)
    p.ell([130, 300, 560, 460], fill=HIP_D)                # belly shade
    p.ell([60, 120, 580, 420], fill=HIP)
    p.ell([150, 140, 460, 250], fill=HIP_L)                # back highlight
    for x in (130, 230, 380, 470):
        for k in range(3): p.ell([x + 10 + k * 26, 478, x + 34 + k * 26, 500], fill=PAPER)
    p.ell([462, 30, 516, 100], fill=HIP_D); p.ell([474, 46, 504, 90], fill=PINK)
    p.ell([520, 22, 574, 92], fill=HIP_D); p.ell([532, 38, 562, 82], fill=PINK)
    p.ell([680, 196, 714, 218], fill=INK); p.ell([712, 200, 740, 222], fill=INK)       # nostrils
    p.ell([600, 270, 680, 320], fill=PINK + (200,))                                    # cheek
    p.d.arc([630 * S, 280 * S, 755 * S, 360 * S], 20, 150, fill=INK, width=7 * S)       # smile
    if blink:
        p.d.arc([548 * S, 108 * S, 612 * S, 160 * S], 10, 170, fill=INK, width=7 * S)
    else:
        p.ell([548, 96, 612, 166], fill=PAPER); p.ell([570, 112, 604, 154], fill=INK); p.circ(592, 124, 6, fill=PAPER)
        p.line([(546, 100), (530, 84)], INK, 6); p.line([(560, 92), (552, 72)], INK, 6)
    return img

def _sheen():
    m = Image.new("L", (HW * S, HH * S), 0); p = P(m)
    for b in ([110, 150, 300, 230], [230, 128, 430, 205], [400, 120, 520, 210], [452, 92, 540, 150], [640, 176, 730, 226]):
        p.ell(b, fill=255)
    for x, l in ((150, 80), (260, 50), (350, 100), (440, 60), (520, 110)):
        y0 = 190 if x < 600 else 200
        p.rrect([x, y0, x + 26, y0 + l], 13, fill=255); p.circ(x + 13, y0 + l, 18, fill=255)
    p.ell([600, 280, 690, 330], fill=255)
    return m.filter(ImageFilter.GaussianBlur(2.4))
HIPPO = {False: _hippo(False), True: _hippo(True)}
SHEEN = _sheen()
SILH = HIPPO[False].split()[3]

def hippo_img(sheen=1.0, col=CORAL, blink=False, gloss_t=0.0):
    img = HIPPO[blink].copy()
    if sheen > 0:
        a = np.asarray(SHEEN, np.float32) * np.asarray(SILH, np.float32) / 255 * 0.82 * sheen
        lay = Image.new("RGBA", img.size, col + (0,)); lay.putalpha(Image.fromarray(a.astype(np.uint8)))
        img = Image.alpha_composite(img, lay)
        d = ImageDraw.Draw(img)
        for (x, y, r) in ((200, 172, 9), (330, 152, 7), (480, 110, 8), (680, 192, 6)):  # glossy glints
            g = int(220 * sheen * (0.6 + 0.4 * math.sin(gloss_t * 4 + x)))
            d.ellipse([(x - r) * S, (y - r * 0.6) * S, (x + r) * S, (y + r * 0.6) * S], fill=(255, 250, 235, g))
    return img

def paste_hippo(p, cx, cy, scale=1.0, **k):
    h = hippo_img(**k); sz = (int(HW * scale * S), int(HH * scale * S)); h = h.resize(sz, Image.BICUBIC)
    p.img.paste(h, (int(cx * S - sz[0] / 2), int(cy * S - sz[1] / 2)), h)

def blink_at(t): return (t % 3.1) > 2.95

def drop(p, cx, cy, r, fill):
    p.poly([(cx, cy - r * 1.9), (cx - r * 0.86, cy - r * 0.5), (cx + r * 0.86, cy - r * 0.5)], fill=fill)
    p.circ(cx, cy, r, fill=fill); p.ell([cx - r * 0.5, cy - r * 0.55, cx - r * 0.15, cy - r * 0.05], fill=(255, 255, 255, 150))

def dashed_box(p, b, col=INK, dash=22, gap=14, width=4):
    x0, y0, x1, y1 = b
    for (a, c) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        L = math.hypot(c[0] - a[0], c[1] - a[1]); k = 0.0
        while k < L:
            e = min(L, k + dash); ux, uy = (c[0] - a[0]) / L, (c[1] - a[1]) / L
            p.d.line([((a[0] + ux * k) * S, (a[1] + uy * k) * S), ((a[0] + ux * e) * S, (a[1] + uy * e) * S)], fill=col, width=width * S)
            k += dash + gap

def cross(p, cx, cy, r, u, col=CORAL, w=26):
    if u <= 0: return
    u1, u2 = min(1, u * 2), max(0, u * 2 - 1)
    p.line([(cx - r, cy - r), (cx - r + 2 * r * u1, cy - r + 2 * r * u1)], col, w)
    if u2 > 0: p.line([(cx + r, cy - r), (cx + r - 2 * r * u2, cy - r + 2 * r * u2)], col, w)

# ---------- scenes ----------
def S_hook(sc, lt, dur, t, p):
    kicker(p)
    sunburst(p, W / 2, 1200, 490, t)
    head(p, "HIPPOS SWEAT", 300, 124, INK, TEAL)
    pop = 1.0 if not sc.get("loop") else 1.0
    head(p, "RED.", 480, 230, CORAL, INK, off=(9, 9))
    p.text((W / 2, 650), "...and it's sunscreen!", SCRIPT(fit(p, "...and it's sunscreen!", SCRIPT, 84, 900)), TEAL, shadow=PAPER, off=(3, 3))
    bob = 8 * math.sin(t * 2.2)
    paste_hippo(p, W / 2 - 20, 1250 + bob, 1.02, sheen=1.0, blink=blink_at(t), gloss_t=t)
    if sc.get("loop"):
        u = back(lt / 0.35); star(p, 830, 920, 150 * max(0.01, u), "", rot=t * 0.4, fill=TEAL, lines=["BUT", "WAIT!"], tsize=max(4, 54 * u))
    else:
        star(p, 840, 900, 120, "NEW!", rot=t * 0.4, tsize=48)

def S_notit(sc, lt, dur, t, p):
    kicker(p)
    head(p, "IT'S NOT...", 300, 150, INK, TEAL)
    for k, (x0, word, col) in enumerate(((90, "BLOOD", CORAL), (570, "SWEAT", TEAL))):
        u = back((lt - k * 0.25) / 0.35)
        if u <= 0: continue
        cy = 760; x1 = x0 + 420
        p.rect([x0 + 8, 470 + 8, x1 + 8, 1050 + 8], fill=INK + (70,))
        p.rect([x0, 470, x1, 1050], fill=(250, 243, 226)); dashed_box(p, [x0 + 18, 488, x1 - 18, 1032])
        drop(p, x0 + 210, 720, 92 * min(1.1, u), col)
        p.text((x0 + 210, 950), word, SLAB(70), INK)
        cross(p, x0 + 210, 760, 150, ease((lt - (0.55 if k == 0 else dur * 0.5)) / 0.4))
    u = back((lt - dur * 0.72) / 0.3)
    paste_hippo(p, W / 2 + 60, 1290 + 6 * math.sin(t * 2.2), 0.78, sheen=1.0, blink=blink_at(t), gloss_t=t)
    if u > 0.05: star(p, 180, 1130, 130 * u, "", rot=-0.2, fill=MUST, tcol=INK, lines=["NEI-", "THER!"], tsize=max(4, 46 * u))

def S_color(sc, lt, dur, t, p):
    kicker(p)
    p.text((W / 2, 290), "Fresh from the hippo:", SCRIPT(fit(p, "Fresh from the hippo:", SCRIPT, 86, 940)), TEAL, shadow=PAPER, off=(3, 3))
    head(p, "CLEAR  >  RED", 450, 120, INK, CORAL)
    k = ease((lt - 0.9) / 1.4)
    chips = (("CLEAR", None), ("RED-ORANGE", CORAL))
    for i, (lab, col) in enumerate(chips):
        x0 = 120 + i * 470; y0 = 560
        lift = -16 if (i == 0 and k < 0.5) or (i == 1 and k >= 0.5) else 0
        p.rect([x0 + 8, y0 + 8, x0 + 370 + 8, y0 + 300 + 8], fill=INK + (70,))
        p.rect([x0, y0 + lift, x0 + 370, y0 + 300 + lift], fill=(252, 248, 238), outline=INK, width=3)
        if col: p.rect([x0 + 18, y0 + 18 + lift, x0 + 352, y0 + 210 + lift], fill=col)
        else:
            p.rect([x0 + 18, y0 + 18 + lift, x0 + 352, y0 + 210 + lift], fill=(236, 240, 238), outline=(180, 190, 190), width=2)
            for j in range(3): p.line([(x0 + 60 + j * 60, y0 + 190 + lift), (x0 + 150 + j * 60, y0 + 40 + lift)], (255, 255, 255, 220), 12)
        p.text((x0 + 185, y0 + 255 + lift), lab, COND(44, 700), INK)
    # timer chip between
    p.circ(W / 2, 710, 46, fill=MUST, outline=INK, width=4)
    a = -math.pi / 2 + 2 * math.pi * k; p.line([(W / 2, 710), (W / 2 + 30 * math.cos(a), 710 + 30 * math.sin(a))], INK, 7)
    p.text((W / 2, 790), "MINUTES", COND(26, 700), INK)
    col = tuple(int(a_ + (b_ - a_) * k) for a_, b_ in zip((235, 225, 215), CORAL))
    paste_hippo(p, W / 2, 1230 + 6 * math.sin(t * 2.2), 0.95, sheen=0.25 + 0.75 * k, col=col, blink=blink_at(t), gloss_t=t)

def S_rays(sc, lt, dur, t, p):
    kicker(p)
    head(p, "BUILT-IN UV SHIELD", 290, 116, INK, TEAL)
    for i, (lab, col) in enumerate((("RED PIGMENT", CORAL), ("ORANGE PIGMENT", ORANGE))):
        u = back((lt - 0.3 - i * 0.35) / 0.3)
        if u <= 0: continue
        f = COND(42, 700); tw = p.tlen(lab, f); cx = 290 + i * 500
        p.rrect([cx - tw / 2 - 30, 400, cx + tw / 2 + 30, 470], 35, fill=col); p.text((cx, 434), lab, f, PAPER)
    sx, sy = 190, 700
    for k in range(16):
        a = 2 * math.pi * k / 16 + t * 0.6; p.line([(sx + 105 * math.cos(a), sy + 105 * math.sin(a)), (sx + 140 * math.cos(a), sy + 140 * math.sin(a))], MUST, 12)
    p.circ(sx, sy, 88, fill=MUST, outline=CORAL, width=8); p.text((sx, sy + 4), "UV", SLAB(54), CORAL)
    hx, hy = W / 2 + 70, 1170
    paste_hippo(p, hx, hy + 5 * math.sin(t * 2.2), 0.9, sheen=1.0, blink=blink_at(t), gloss_t=t)
    targets = [(hx - 220, hy - 130), (hx - 70, hy - 160), (hx + 90, hy - 190), (hx + 210, hy - 150)]
    for i, (tx, ty) in enumerate(targets):
        ph = ((lt * 0.9 + i * 0.27) % 1.0)
        L = math.hypot(tx - sx, ty - sy); ux, uy = (tx - sx) / L, (ty - sy) / L; nx, ny = -uy, ux
        head_d = min(L - 10, 140 + (L - 140) * ph); tail = max(140, head_d - 260)
        pts = []
        for s in np.linspace(tail, head_d, 24):
            w_ = 16 * math.sin(s / 22 - t * 10); pts.append((sx + ux * s + nx * w_, sy + uy * s + ny * w_))
        p.line(pts, (110, 60, 160, 240), 14)
        if ph > 0.9:
            r = 20 + 60 * (ph - 0.9) / 0.1; p.circ(tx, ty, r, outline=PAPER + (int(255 * (1 - (ph - 0.9) / 0.1)),), width=6)
    u = back((lt - dur * 0.55) / 0.3)
    if u > 0.1: p.text((W / 2 + 70, 1470), "Blocked!", SCRIPT(max(8, int(78 * u))), CORAL, shadow=INK, off=(4, 4))

GERMS = [(random.Random(i).uniform(-300, 300), random.Random(i + 99).uniform(-300, 300)) for i in range(40)]
GERMS = [g for g in GERMS if math.hypot(*g) < 300][:16]
def S_germs(sc, lt, dur, t, p):
    kicker(p)
    head(p, "IT FIGHTS GERMS", 290, 120, CORAL, INK)
    p.text((W / 2, 440), "Double action!", SCRIPT(76), TEAL, shadow=PAPER, off=(3, 3))
    cx, cy, R = W / 2, 980, 380
    p.circ(cx + 10, cy + 12, R + 26, fill=INK + (70,)); p.circ(cx, cy, R + 26, fill=TEAL); p.circ(cx, cy, R, fill=(236, 244, 236))
    p.d.arc([(cx - R + 30) * S, (cy - R + 30) * S, (cx + R - 30) * S, (cy + R - 30) * S], 200, 250, fill=(255, 255, 255), width=14 * S)
    dropu = ease((lt - 0.4) / 0.5); spread = ease((lt - 0.9) / 1.6) * (R - 10)
    if 0 < dropu < 1: drop(p, cx, 520 + (cy - 520) * dropu, 40, CORAL)
    if spread > 0: p.circ(cx, cy, spread, fill=CORAL + (90,)); p.circ(cx, cy, spread, outline=CORAL + (200,), width=5)
    for i, (gx, gy) in enumerate(GERMS):
        d_ = math.hypot(gx, gy); kill = ease((spread - d_ + 20) / 80)
        r = 30 * (1 - 0.75 * kill); x, y = cx + gx + 6 * math.sin(t * 3 + i), cy + gy + 6 * math.cos(t * 2.6 + i)
        col = tuple(int(a + (b - a) * kill) for a, b in zip(GERM, (190, 180, 170)))
        for k in range(8):
            a = 2 * math.pi * k / 8 + t; p.line([(x + r * math.cos(a), y + r * math.sin(a)), (x + r * 1.35 * math.cos(a), y + r * 1.35 * math.sin(a))], col, 5)
        p.circ(x, y, r, fill=col)
        if kill < 0.5: p.circ(x - r * 0.3, y - r * 0.2, r * 0.18, fill=INK); p.circ(x + r * 0.3, y - r * 0.2, r * 0.18, fill=INK)
    p.text((W / 2, 1450), "*in lab tests, on some germs", COND(34, 500), INK + (200,))

def S_product(sc, lt, dur, t, p):
    kicker(p)
    head(p, "SUNSCREEN", 280, 150, CORAL, INK)
    head(p, "+ GERM FIGHTER", 420, 92, INK, TEAL)
    sunburst(p, W / 2, 1040, 460, t)
    u = back(lt / 0.45); s = max(0.05, u); cx, cy = W / 2, 1060
    def T(x, y): return (cx + (x - cx) * s, cy + (y - cy) * s)
    tilt = 0
    body = [T(390, 640), T(690, 640), T(720, 1320), T(360, 1320)]
    p.poly([(x + 10, y + 10) for x, y in body], fill=INK + (90,))
    p.poly(body, fill=(252, 247, 236))
    for k in range(7):                                         # crimp
        a, b = T(390 + k * 300 / 7, 610), T(390 + (k + 1) * 300 / 7, 640)
        p.rect([a[0], a[1], b[0], b[1]], fill=CORAL if k % 2 == 0 else (230, 100, 80))
    p.poly([T(362, 1150), T(718, 1150), T(724, 1250), T(356, 1250)], fill=TEAL)
    p.rrect([*T(450, 1320), *T(630, 1410)], 24 * s, fill=INK); p.rrect([*T(470, 1330), *T(500, 1395)], 10 * s, fill=(255, 255, 255, 60))
    if u > 0.5:
        p.text(T(540, 760), "Hippo", SCRIPT(int(92 * s)), CORAL, shadow=INK, off=(3, 3))
        p.text(T(540, 880), "FORMULA", SLAB(int(64 * s)), INK)
        p.text(T(540, 960), "SUN + GERM GUARD", COND(int(34 * s), 700), TEAL)
        p.text(T(540, 1200), "RED-ORANGE · ALL DAY", COND(int(30 * s), 700), PAPER)
        paste_hippo(p, *T(540, 1060), 0.17 * s, sheen=1.0, gloss_t=t)
    v = back((lt - 0.8) / 0.3)
    if v > 0: star(p, 850, 760, 125 * v, "", rot=t * 0.4, fill=CORAL, lines=["MADE BY", "HIPPOS"], tsize=max(4, 34 * v))
    p.text((W / 2, 1495), "Not sold in stores. Available only on hippos.", COND(32, 500), INK + (200,))

def S_end(sc, lt, dur, t, p):
    kicker(p)
    head(p, "SOUNDS FAKE?", 310, 140, INK, TEAL)
    cx, cy = W / 2, 1010
    sunburst(p, cx, cy, 470, t)
    click = sc.get("click_at", 0.45); on = back((lt - click) / 0.3)
    p.circ(cx + 10, cy + 12, 250, fill=INK + (90,)); p.circ(cx, cy, 250, fill=CORAL); p.circ(cx, cy, 215, fill=(250, 244, 228))
    for k in range(-6, 7):
        a = math.radians(-90 + k * 10); r0 = 182 if k % 3 else 160
        p.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + 205 * math.cos(a), cy + 205 * math.sin(a))], INK, 6 if k % 3 == 0 else 3)
    ang = math.radians(-90 - 50 + 100 * max(0, min(1.08, on)))
    lf, lt_ = (INK if on < 0.5 else (170, 160, 140)), (CORAL if on >= 0.5 else (170, 160, 140))
    p.text((cx - 190, cy - 300), "FAKE", SLAB(64), lf); p.text((cx + 190, cy - 300), "TRUE", SLAB(64), lt_)
    p.circ(cx, cy, 120, fill=TEAL); p.circ(cx, cy, 104, fill=(60, 170, 166))
    p.line([(cx, cy), (cx + 150 * math.cos(ang), cy + 150 * math.sin(ang))], INK, 22)
    p.circ(cx, cy, 34, fill=INK); p.circ(cx - 8, cy - 8, 8, fill=(255, 255, 255, 120))
    if on >= 0.5:
        u = back((lt - click - 0.15) / 0.3)
        p.text((W / 2, 1390), "It's true!", SCRIPT(max(8, int(110 * u))), CORAL, shadow=INK, off=(4, 4))
        star(p, 880, 1330, 105 * u, "", rot=t * 0.5, fill=TEAL, lines=["100%", "REAL"], tsize=max(4, 36 * u))

SCENES = dict(hook=S_hook, notit=S_notit, color=S_color, rays=S_rays, germs=S_germs, product=S_product, end=S_end)

# ---------- audio: bossa-lounge vibraphone jingle ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
def vib(f, dur):
    tt = np.arange(int(dur * SR)) / SR
    return (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * 4 * f * tt) * np.exp(-tt * 12)) * np.exp(-tt * 3.2) * (1 + 0.25 * np.sin(2 * np.pi * 5.5 * tt))
CH = [(261.63, 329.63, 392.0, 493.88), (220.0, 261.63, 329.63, 392.0), (293.66, 349.23, 440.0, 523.25), (196.0, 246.94, 293.66, 349.23)]
BASS = [65.41, 55.0, 73.42, 49.0]
beat = 0.5; rr = random.Random(5)
for b in range(int(total / beat) + 2):
    bar, pos = (b // 4) % 4, b % 4; ch = CH[bar]; t0 = b * beat
    for e in range(2):
        if rr.random() < 0.8: place(music, t0 + e * beat / 2, vib(ch[(pos * 2 + e) % 4] * 2, 0.9), 0.05)
    place(music, t0, tone(BASS[bar] * (1.5 if pos == 2 else 1), 0.45, decay=5, harm=(1, 2)), 0.16 if pos in (0, 2) else 0.0)
    if pos in (1, 3): place(music, t0 + 0.25, tone(BASS[bar] * 2, 0.3, decay=8, harm=(1, 2)), 0.08)
    nz = np.random.default_rng(b).normal(0, 1, int(0.06 * SR)) * np.exp(-np.arange(int(0.06 * SR)) / SR * 70)
    place(music, t0, nz, 0.03); place(music, t0 + 0.25, nz, 0.018)
hook_hit(music, 0.35)
for s_ in scene_starts(spec): whoosh(music, s_, 0.1)
end_ln = spec["lines"][-1]
place(music, end_ln["_s"] + end_ln["scene"].get("click_at", 0.45), tone(1318.5, 0.5, decay=6, harm=(1, 2)), 0.12)  # ding!
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.35)

# ---------- captions, progress, frame ----------
groups = caption_groups(words, 3)
def caption(p, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0].upper() for i in g]; size = 70
    while p.tlen(" ".join(ws), COND(size, 700)) > W - 200 and size > 36: size -= 4
    f = COND(size, 700); tw = p.tlen(" ".join(ws), f); x = (W - tw) / 2; y = 1625
    p.rrect([x - 34 + 6, y - size * 0.75 + 6, x + tw + 34 + 6, y + size * 0.75 + 6], 22, fill=CORAL)
    p.rrect([x - 34, y - size * 0.75, x + tw + 34, y + size * 0.75], 22, fill=INK)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        p.text((x, y), w, f, MUST if on else PAPER, anchor="lm"); x += p.tlen(w + " ", f)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = BASE.copy(); p = P(img)
    SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t, p); caption(p, t)
    p.rect([0, H - 12, W, H], fill=INK + (40,)); p.rect([0, H - 12, W * t / total, H], fill=CORAL)
    return img.reduce(S).tobytes()

if __name__ == "__main__":
    print(" ".join(f"{l['_s']:.2f}" for l in spec["lines"]), f"total {total:.2f}")
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
