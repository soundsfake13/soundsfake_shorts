"""Day 26 — RETRO-MISSION style (the Moon drifts ~3.8 cm a year away from Earth).
1970s space-mission print graphics: chocolate-brown printed 'space' with paper grain and halftone star dust,
every body drawn as flat spot colour + halftone shadow dots (Moon, Earth, dome), the 70s triple stripe
(mustard / orange / rust) used for motion trails, rulers and diagonal band wipes, an embroidered mission
patch with stitched borders and curved lettering, Jost Black titles with an orange misregistered shadow,
Space Mono technical labels, Quindar-style beeps on cuts and a warm Rhodes + analog-bass groove.
Ending: a console slider FAKE -> TRUE whose knob is a little halftone Moon; dissolves back into the hook.
Everything is drawn at 2x and reduced. Usage: python3 engine/styles/day26_mission.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
S = 2
BG = (46, 29, 22); BG2 = (66, 42, 30); CREAM = (242, 228, 198); TAN = (214, 188, 146)
MUST = (238, 172, 52); ORANGE = (226, 104, 38); RUST = (170, 60, 30); TEAL = (58, 122, 118); DEEP = (30, 26, 38)
STRIPES = (MUST, ORANGE, RUST)

_fc = {}
def F(name, size, w=None):
    k = (name, int(size), w)
    if k not in _fc:
        f = ImageFont.truetype(f"{FONTS}/{name}", int(size))
        if w: f.set_variation_by_axes([w])
        _fc[k] = f
    return _fc[k]
JOST = lambda s, w=900: F("Jost-VF.ttf", s * S, w)
MONO = lambda s: F("SpaceMono-Bold.ttf", s * S)

# ---------- printed background: brown stock, grain, halftone star dust ----------
rng = np.random.default_rng(26)
_b = np.full((H, W, 3), BG, np.float32) + rng.normal(0, 3.2, (H, W, 1))
_lo = Image.fromarray(rng.normal(0, 1, (H // 6, W // 6)).astype(np.float32)).resize((W, H), Image.BICUBIC)
_b += np.asarray(_lo)[..., None] * np.array([3.5, 2.2, 1.5])
yy, xx = np.mgrid[0:H, 0:W]
_b *= (1 - 0.22 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2))[..., None]
BASE = Image.fromarray(_b.clip(0, 255).astype(np.uint8)).resize((W * S, H * S), Image.BILINEAR)
_d = ImageDraw.Draw(BASE)
for _ in range(260):
    x, y = rng.uniform(0, W), rng.uniform(0, H); r = rng.choice([1.4, 2.0, 2.6, 3.6], p=[.45, .3, .17, .08])
    c = CREAM if rng.random() < 0.8 else MUST; a = int(rng.uniform(90, 200))
    _d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=c)
del _d

# ---------- drawing helpers ----------
class P:
    def __init__(self, img): self.img = img; self.d = ImageDraw.Draw(img, "RGBA")
    def _b(self, b): return [v * S for v in b]
    def ell(self, b, fill=None, outline=None, width=0): self.d.ellipse(self._b(b), fill=fill, outline=outline, width=int(width * S))
    def circ(self, cx, cy, r, **k): self.ell([cx - r, cy - r, cx + r, cy + r], **k)
    def rect(self, b, fill=None, outline=None, width=0): self.d.rectangle(self._b(b), fill=fill, outline=outline, width=int(width * S))
    def rrect(self, b, r, fill=None, outline=None, width=0): self.d.rounded_rectangle(self._b(b), int(r * S), fill=fill, outline=outline, width=int(width * S))
    def poly(self, pts, fill=None, outline=None, width=0):
        self.d.polygon([(x * S, y * S) for x, y in pts], fill=fill, outline=outline, width=int(width * S))
    def line(self, pts, fill, width, cap=True):
        self.d.line([(x * S, y * S) for x, y in pts], fill=fill, width=int(width * S), joint="curve")
        if cap:
            for (x, y) in (pts[0], pts[-1]): self.circ(x, y, width / 2 - 0.5, fill=fill)
    def tlen(self, s, f): return self.d.textlength(s, font=f) / S
    def text(self, xy, s, f, fill, anchor="mm", shadow=None, off=(6, 6)):
        x, y = xy
        if shadow: self.d.text(((x + off[0]) * S, (y + off[1]) * S), s, font=f, fill=shadow, anchor=anchor)
        self.d.text((x * S, y * S), s, font=f, fill=fill, anchor=anchor)
    def paste(self, spr, cx, cy, alpha=1.0):
        if alpha < 1:
            spr = spr.copy(); spr.putalpha(spr.getchannel("A").point(lambda v: int(v * alpha)))
        self.img.paste(spr, (int(cx * S - spr.size[0] / 2), int(cy * S - spr.size[1] / 2)), spr)

def title(p, s, y, size, fill=CREAM, shadow=ORANGE, maxw=960, u=1.0):
    while p.tlen(s, JOST(size)) > maxw and size > 40: size -= 4
    if u <= 0: return
    if u < 1:  # slide up + fade in (never used on the hook's first frame)
        y += (1 - eout(u)) * 40; a = int(255 * min(1, u * 1.6))
        fill = fill + (a,); shadow = shadow + (a,)
    p.text((W / 2, y), s, JOST(size), fill, shadow=shadow, off=(7, 6))

def label(p, s, xy, size=28, fill=CREAM, anchor="mm", box=None):
    if box:
        tw = p.tlen(s, MONO(size)); x, y = xy
        x0 = x - tw / 2 if anchor == "mm" else x
        p.rrect([x0 - 16, y - size * 0.8, x0 + tw + 16, y + size * 0.8], 8, fill=box)
    p.text(xy, s, MONO(size), fill, anchor=anchor)

def stripes(p, a, b, w=26, gap=6, alpha=255, cols=STRIPES):
    """The 70s triple stripe along the segment a->b."""
    (x0, y0), (x1, y1) = a, b; L = math.hypot(x1 - x0, y1 - y0) or 1
    nx, ny = -(y1 - y0) / L, (x1 - x0) / L
    for k, c in enumerate(cols):
        o = (k - 1) * (w + gap)
        p.line([(x0 + nx * o, y0 + ny * o), (x1 + nx * o, y1 + ny * o)], c + (alpha,), w)

def hstripes(p, x0, x1, y, w=14, gap=5):
    for k, c in enumerate(STRIPES): p.rect([x0, y + k * (w + gap), x1, y + k * (w + gap) + w], fill=c)

def header(p, s="MISSION 26  ·  LUNAR RECESSION"):
    hstripes(p, 70, 230, 128, 8, 4); hstripes(p, W - 230, W - 70, 128, 8, 4)
    label(p, s, (W / 2, 145), 24, TAN)

def arrow(p, a, b, col, w=10, head=26):
    p.line([a, b], col, w)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    p.poly([b, (b[0] - head * math.cos(ang - 0.45), b[1] - head * math.sin(ang - 0.45)),
            (b[0] - head * math.cos(ang + 0.45), b[1] - head * math.sin(ang + 0.45))], fill=col)

def dotted(p, pts, col, r=5, step=22):
    acc = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        while acc < L:
            u = acc / L; p.circ(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, r, fill=col); acc += step
        acc -= L

# ---------- halftone sprites ----------
def halftone(layer_rgba, r, cx, cy, light=(-0.62, -0.55), g=12.0, col=BG, gain=1.0):
    """Overlay shadow dots (col) on a sphere of radius r centred at (cx,cy) in the sprite (1x units)."""
    d = ImageDraw.Draw(layer_rgba)
    lx, ly = light; lz = math.sqrt(max(0, 1 - lx * lx - ly * ly))
    j = 0; y = cy - r
    while y <= cy + r:
        x = cx - r + (g / 2 if j % 2 else 0)
        while x <= cx + r:
            nx, ny = (x - cx) / r, (y - cy) / r; q = nx * nx + ny * ny
            if q < 1:
                nz = math.sqrt(1 - q); sh = max(0.0, nx * lx + ny * ly + nz * lz)
                dk = (1 - min(1.0, sh * 1.25 + 0.08)) * gain
                if dk > 0.03:
                    rr = g * 0.47 * math.sqrt(min(dk, 0.92))
                    d.ellipse([(x - rr) * S, (y - rr) * S, (x + rr) * S, (y + rr) * S], fill=col)
            x += g
        y += g * 0.866; j += 1

def _disc_mask(sz, r, pad):
    m = Image.new("L", (sz * S, sz * S), 0)
    ImageDraw.Draw(m).ellipse([pad * S, pad * S, (pad + 2 * r) * S, (pad + 2 * r) * S], fill=255); return m

_spr = {}
def moon(r):
    k = ("moon", r)
    if k in _spr: return _spr[k]
    pad = 6; sz = 2 * r + 2 * pad; c = pad + r
    img = Image.new("RGBA", (sz * S, sz * S), (0, 0, 0, 0)); p = P(img)
    p.circ(c, c, r, fill=CREAM)
    rr = np.random.default_rng(7)
    for (mx, my, mr) in [(-0.3, -0.25, 0.32), (0.05, -0.38, 0.22), (0.25, -0.05, 0.26), (-0.15, 0.2, 0.2), (0.35, 0.3, 0.14)]:
        for _ in range(5):
            ox, oy = rr.uniform(-0.08, 0.08), rr.uniform(-0.08, 0.08); s = mr * rr.uniform(0.6, 1.0)
            p.ell([c + (mx + ox - s) * r, c + (my + oy - s * 0.85) * r, c + (mx + ox + s) * r, c + (my + oy + s * 0.85) * r], fill=TAN)
    for (mx, my, mr) in [(0.2, 0.55, 0.09), (-0.55, 0.15, 0.07), (0.6, -0.3, 0.06), (-0.05, 0.62, 0.05), (0.45, 0.6, 0.05), (-0.4, -0.6, 0.05)]:
        p.circ(c + mx * r, c + my * r, mr * r, outline=TAN, width=max(2, r * 0.018))
    halftone(img, r, c, c, g=max(8, r / 22))
    p.circ(c, c, r - 1, outline=TAN, width=max(2, r / 60))
    img.putalpha(_disc_mask(sz, r, pad)); _spr[k] = img; return img

def earth(r):
    k = ("earth", r)
    if k in _spr: return _spr[k]
    pad = 6; sz = 2 * r + 2 * pad; c = pad + r
    img = Image.new("RGBA", (sz * S, sz * S), (0, 0, 0, 0)); p = P(img)
    p.circ(c, c, r, fill=TEAL)
    rr = np.random.default_rng(3)
    for (lx, ly, ls) in [(-0.35, -0.3, 0.42), (0.3, 0.25, 0.36), (0.45, -0.45, 0.22), (-0.2, 0.55, 0.2)]:
        pts = []
        for k2 in range(14):
            a = 2 * math.pi * k2 / 14; s = ls * rr.uniform(0.6, 1.15)
            pts.append((c + (lx + s * math.cos(a)) * r, c + (ly + s * 0.8 * math.sin(a)) * r))
        p.poly(pts, fill=MUST)
    for (cy_, w_) in [(-0.62, 0.5), (0.05, 0.7), (0.7, 0.45)]:
        p.d.arc([(c - w_ * r) * S, (c + (cy_ - 0.1) * r) * S, (c + w_ * r) * S, (c + (cy_ + 0.1) * r) * S], 200, 340, fill=CREAM, width=int(max(3, r * 0.035) * S))
    halftone(img, r, c, c, g=max(8, r / 18))
    p.circ(c, c, r - 1, outline=TEAL, width=max(2, r / 60))
    img.putalpha(_disc_mask(sz, r, pad)); _spr[k] = img; return img

def body(p, kind, cx, cy, r, alpha=1.0, ring=True):
    spr = moon(r) if kind == "moon" else earth(r)
    if ring: p.circ(cx + 8, cy + 8, r, fill=(0, 0, 0, int(70 * alpha)))
    p.paste(spr, cx, cy, alpha)

# ---------- mission patch ----------
def arc_text(img, s, cx, cy, R, f, fill, top=True, spacing=1.0):
    d = ImageDraw.Draw(img)
    ws = [d.textlength(ch, font=f) / S * spacing for ch in s]; span = sum(ws) / R
    th = (-math.pi / 2 - span / 2) if top else (math.pi / 2 + span / 2)
    for ch, w in zip(s, ws):
        a = th + (w / 2 / R) * (1 if top else -1)
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        gl = Image.new("RGBA", (int(f.size * 1.6), int(f.size * 1.6)), (0, 0, 0, 0))
        ImageDraw.Draw(gl).text((gl.size[0] / 2, gl.size[1] / 2), ch, font=f, fill=fill, anchor="mm")
        rot = -(math.degrees(a) + 90) if top else -(math.degrees(a) - 90)
        gl = gl.rotate(rot, resample=Image.BICUBIC)
        img.paste(gl, (int(x * S - gl.size[0] / 2), int(y * S - gl.size[1] / 2)), gl)
        th += (w / R) * (1 if top else -1)

def patch(R=340):
    k = ("patch", R)
    if k in _spr: return _spr[k]
    pad = 20; sz = 2 * (R + pad); c = R + pad
    img = Image.new("RGBA", (sz * S, sz * S), (0, 0, 0, 0)); p = P(img)
    p.circ(c, c, R, fill=CREAM); p.circ(c, c, R - 10, fill=RUST)
    p.d.ellipse([(c - R + 22) * S, (c - R + 22) * S, (c + R - 22) * S, (c + R - 22) * S], outline=MUST, width=6)
    n = 120
    for i in range(n):  # stitched dashes
        a0 = 2 * math.pi * i / n; a1 = a0 + math.pi / n
        p.line([(c + (R - 6) * math.cos(a0), c + (R - 6) * math.sin(a0)), (c + (R - 6) * math.cos(a1), c + (R - 6) * math.sin(a1))], BG, 3, cap=False)
    ri = R - 92
    p.circ(c, c, ri + 8, fill=CREAM); p.circ(c, c, ri, fill=DEEP)
    inner = Image.new("RGBA", img.size, (0, 0, 0, 0)); q = P(inner)
    for k2, col in enumerate(STRIPES):
        o = (k2 - 1) * 46
        q.line([(c - ri - 40, c + ri * 0.15 + o), (c + ri + 40, c - ri * 0.55 + o)], col, 38, cap=False)
    m = _disc_mask(sz, ri, c - ri); img.paste(inner, (0, 0), Image.fromarray(np.minimum(np.asarray(m), np.asarray(inner.getchannel("A")))))
    for _ in range(26):
        a = rng.uniform(0, 2 * math.pi); rr_ = ri * math.sqrt(rng.uniform(0, 0.9))
        p.circ(c + rr_ * math.cos(a), c + rr_ * math.sin(a), rng.choice([2, 3, 4]), fill=CREAM)
    e = earth(78); img.paste(e, (int((c - ri * 0.45) * S - e.size[0] / 2), int((c + ri * 0.42) * S - e.size[1] / 2)), e)
    mo = moon(58); img.paste(mo, (int((c + ri * 0.48) * S - mo.size[0] / 2), int((c - ri * 0.45) * S - mo.size[1] / 2)), mo)
    arc_text(img, "LUNAR  LASER  RANGING", c, c, R - 50, MONO(34), CREAM, top=True, spacing=1.08)
    arc_text(img, "EARTH  ·  MOON", c, c, R - 50, MONO(34), MUST, top=False, spacing=1.12)
    _spr[k] = img; return img

# ---------- scenes ----------
def S_hook(sc, lt, dur, t, p):
    header(p)
    ex, ey = 150, 1470
    mx, my = 650 + 34 * lt, 960 - 26 * lt
    stripes(p, (ex + 90, ey - 90), (mx - 60, my + 60), w=54, gap=10)
    for k in range(4):  # speed ticks
        o = (k * 0.27 + lt * 0.9) % 1.0; d0 = 340 + o * 160
        x0, y0 = mx - d0 * 0.7 + 150, my + d0 * 0.7 - 260
        p.line([(x0, y0), (x0 - 50, y0 + 50)], CREAM + (int(200 * (1 - o)),), 6)
    body(p, "earth", ex, ey, 300)
    body(p, "moon", mx, my, 250)
    title(p, "THE MOON IS", 330, 124)
    title(p, "RUNNING AWAY", 468, 138, MUST, RUST)

def S_loop(sc, lt, dur, t, p):
    header(p)
    u = back(lt / 0.45); spr = patch(); sc_ = max(0.05, u)
    img = spr.rotate(-18 * (1 - min(1, u)) + 3 * math.sin(lt * 2.2), resample=Image.BICUBIC)
    if abs(sc_ - 1) > 0.01: img = img.resize((max(2, int(img.size[0] * sc_)), max(2, int(img.size[1] * sc_))), Image.BILINEAR)
    p.circ(548, 1048, 360 * sc_, fill=(0, 0, 0, 70)); p.paste(img, 540, 1040)
    title(p, "HOW DO WE", 330, 124, u=lt / 0.3)
    title(p, "KNOW THIS?", 466, 138, MUST, RUST, u=(lt - 0.12) / 0.3)

def S_drift(sc, lt, dur, t, p):
    header(p)
    v = ease((lt - 0.3) / 1.6); val = 3.8 * v
    title(p, f"+{val:.1f} CM", 360, 190, MUST, RUST)
    title(p, "EVERY YEAR", 520, 96, u=lt / 0.3)
    ex, ey = 200, 1010; mx = 760 + 110 * v
    body(p, "earth", ex, ey, 150)
    dotted(p, [(ex + 170, ey), (mx - 120, ey)], CREAM + (170,), 5, 24)
    body(p, "moon", mx, ey, 100)
    label(p, "DISTANCE  →", (ex + 170 + (mx - 120 - ex - 170) / 2, ey - 44), 24, TAN)
    x0, x1, y = 140, 940, 1300; cm = (x1 - x0) / 5
    p.rrect([x0 - 30, y - 70, x1 + 30, y + 90], 16, fill=BG2)
    p.rect([x0, y - 20, x0 + cm * val, y + 22], fill=ORANGE); p.rect([x0, y - 20, x0 + cm * val, y - 8], fill=MUST)
    p.rect([x0, y + 10, x0 + cm * val, y + 22], fill=RUST)
    for i in range(51):
        x = x0 + cm * i / 10; L = 34 if i % 10 == 0 else (22 if i % 5 == 0 else 12)
        p.line([(x, y - 54), (x, y - 54 + L)], CREAM, 3 if i % 10 == 0 else 2, cap=False)
        if i % 10 == 0: label(p, str(i // 10), (x, y + 56), 26, CREAM)
    label(p, "CM", (x1 + 2, y + 56), 22, TAN)
    p.line([(x0 + cm * val, y - 40), (x0 + cm * val, y + 40)], CREAM, 4, cap=False)

def finger(p, cx, top, grow):
    """Flat 70s-print fingertip pointing up; the nail's free edge grows by `grow` px."""
    SKIN = (222, 160, 112); SKIN_D = (190, 124, 84)
    p.rrect([cx - 95 + 8, top + 8, cx + 95 + 8, top + 560], 95, fill=(0, 0, 0, 70))
    p.rrect([cx - 95, top, cx + 95, top + 560], 95, fill=SKIN)
    p.rrect([cx + 40, top + 40, cx + 95, top + 560], 60, fill=SKIN_D + (110,))
    for k in range(3): p.d.arc([(cx - 50) * S, (top + 360 + k * 18) * S, (cx + 50) * S, (top + 400 + k * 18) * S], 200, 340, fill=SKIN_D, width=6)
    nt = top + 70
    p.rrect([cx - 62, nt - grow, cx + 62, nt + 70], 50, fill=CREAM)                 # free edge (white)
    p.rrect([cx - 62, nt + 20, cx + 62, nt + 210], 56, fill=(236, 176, 150))         # nail plate
    p.ell([cx - 40, nt + 150, cx + 40, nt + 200], fill=(246, 210, 186))              # lunula
    p.line([(cx - 38, nt + 50), (cx - 38, nt + 150)], (255, 236, 220, 160), 10)       # shine

def S_nails(sc, lt, dur, t, p):
    header(p)
    title(p, "AS FAST AS", 330, 118, u=lt / 0.3)
    title(p, "FINGERNAILS GROW", 466, 112, MUST, RUST, u=(lt - 0.1) / 0.3)
    g = ease((lt - 0.35) / 1.8)
    finger(p, 290, 900, 10 + 70 * g)
    p.text((540, 1120), "=", JOST(150), MUST, shadow=RUST, off=(6, 6))
    my = 1180 - 190 * g
    p.line([(800, 1290), (800, my + 110)], CREAM + (120,), 4)
    stripes(p, (800, 1300), (800, my + 120), w=14, gap=4)
    body(p, "moon", 800, my, 100)
    for lx, s in ((290, "YOUR NAIL"), (800, "THE MOON")):
        label(p, s, (lx, 1420), 28, BG, box=CREAM)
    label(p, "1 YEAR", (540, 1240), 26, TAN)

def rot_ellipse(cx, cy, a, b, ang, n=60):
    ca, sa = math.cos(ang), math.sin(ang)
    return [(cx + a * math.cos(2 * math.pi * k / n) * ca - b * math.sin(2 * math.pi * k / n) * sa,
             cy + a * math.cos(2 * math.pi * k / n) * sa + b * math.sin(2 * math.pi * k / n) * ca) for k in range(n)]

def S_tides(sc, lt, dur, t, p):
    header(p)
    title(p, "OCEAN TIDES", 330, 124, u=lt / 0.3)
    title(p, "PUSH IT OUT", 466, 138, MUST, RUST, u=(lt - 0.1) / 0.3)
    ex, ey = 330, 1060; v = ease(lt / max(1.0, dur))
    ma = math.radians(-8 - 34 * v); R = 430 + 70 * v
    pts = []
    for k in range(80):  # dotted spiral path of the Moon
        a = math.radians(30 - k * 1.2); rr_ = 400 + (30 - k * 1.2 + 8) / -42 * 100
        pts.append((ex + max(380, rr_) * math.cos(a), ey + max(380, rr_) * math.sin(a)))
    dotted(p, pts, CREAM + (110,), 4, 26)
    bul = ma + math.radians(22)
    pulse = 1 + 0.04 * math.sin(lt * 5)
    p.poly(rot_ellipse(ex, ey, 240 * pulse, 186, bul), fill=TEAL + (150,))
    p.poly(rot_ellipse(ex, ey, 214 * pulse, 180, bul), fill=(84, 156, 150))
    body(p, "earth", ex, ey, 170)
    sp = lt * 1.6  # spin arrow
    arc = [(ex + 215 * math.cos(math.radians(110 + 60 * k / 10) - sp * 0.2), ey + 215 * math.sin(math.radians(110 + 60 * k / 10) - sp * 0.2)) for k in range(11)]
    p.line(arc[:-1], MUST, 10); arrow(p, arc[-3], arc[-1], MUST, 10, 30)
    mx, my = ex + R * math.cos(ma), ey + R * math.sin(ma)
    bx, by = ex + 240 * math.cos(bul), ey + 240 * math.sin(bul)
    dotted(p, [(bx, by), (mx, my)], ORANGE + (220,), 5, 18)
    body(p, "moon", mx, my, 92)
    tx, ty = -math.sin(ma), math.cos(ma)
    arrow(p, (mx + 100 * math.cos(ma), my + 100 * math.sin(ma)), (mx + 210 * math.cos(ma), my + 210 * math.sin(ma)), ORANGE, 10, 30)
    label(p, "TIDAL BULGE", (ex, ey + 290), 26, CREAM, box=BG2)
    label(p, "PULLED FORWARD", (min(W - 190, mx), my + 150), 24, CREAM, box=BG2)

def S_mirrors(sc, lt, dur, t, p):
    header(p)
    title(p, "MIRRORS", 330, 130, u=lt / 0.3)
    title(p, "ON THE MOON", 466, 130, MUST, RUST, u=(lt - 0.1) / 0.3)
    body(p, "earth", 840, 720, 95)
    # lunar ground: big cream arc with halftone shading and craters
    gy = 1170
    p.ell([-600, gy, W + 600, gy + 1600], fill=CREAM)
    for (cx, cy, w_) in [(150, 1260, 110), (900, 1230, 70), (660, 1400, 140), (330, 1480, 90), (1000, 1420, 60)]:
        p.ell([cx - w_, cy - w_ * 0.28, cx + w_, cy + w_ * 0.28], fill=TAN)
        p.d.arc([(cx - w_) * S, (cy - w_ * 0.28) * S, (cx + w_) * S, (cy + w_ * 0.28) * S], 180, 360, fill=BG + (200,), width=8)
    for j in range(9):
        for i in range(40):
            x = i * 28 + (14 if j % 2 else 0); y = gy + 30 + j * 26; rr_ = 6.5 * (1 - j / 9) ** 1.2
            if rr_ > 0.6: p.circ(x, y + 0.0003 * (x - 540) ** 2, rr_, fill=BG + (150,))
    # retroreflector array (generic grid of corner cubes)
    cx, cy = 420, 1245
    def Q(u, v): return (cx - 200 + 400 * u + 70 * v, cy - 40 - 120 * v + 20 * u)
    p.poly([Q(0, 0), Q(1, 0), Q(1, 1), Q(0, 1)], fill=MUST)
    for i in range(10):
        for j in range(6):
            a, b = 0.04 + i * 0.093, 0.06 + j * 0.15
            p.poly([Q(a, b), Q(a + 0.08, b), Q(a + 0.08, b + 0.12), Q(a, b + 0.12)], fill=DEEP)
            gl = 0.5 + 0.5 * math.sin(t * 6 + i * 0.7 + j * 1.3)
            x, y = Q(a + 0.03, b + 0.08); p.circ(x, y, 3 + 2 * gl, fill=CREAM + (int(120 + 120 * gl),))
    p.poly([Q(0, 0), Q(1, 0), (Q(1, 0)[0], Q(1, 0)[1] + 26), (Q(0, 0)[0], Q(0, 0)[1] + 26)], fill=RUST)
    for u_ in (0.1, 0.9): x, y = Q(u_, 0); p.line([(x, y + 26), (x, y + 70)], BG, 10)
    # laser beam from Earth
    b = ease((lt - 0.5) / 0.5); tgt = Q(0.55, 0.55); src = (810, 790)
    if b > 0:
        end = (src[0] + (tgt[0] - src[0]) * b, src[1] + (tgt[1] - src[1]) * b)
        glow = Image.new("RGBA", p.img.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
        gd.line([(src[0] * S, src[1] * S), (end[0] * S, end[1] * S)], fill=ORANGE + (150,), width=40 * S)
        glow = glow.filter(ImageFilter.GaussianBlur(18 * S)); p.img.paste(glow, (0, 0), glow)
        p.line([src, end], ORANGE, 10); p.line([src, end], (255, 220, 160), 3)
        if b >= 1:
            for k in range(3):
                u = ((lt - 1.0) * 0.9 + k / 3) % 1.0
                x, y = tgt[0] + (src[0] - tgt[0]) * u, tgt[1] + (src[1] - tgt[1]) * u
                p.circ(x, y, 9, fill=(255, 240, 200))
            ring = (lt * 2) % 1.0; p.circ(tgt[0], tgt[1], 20 + 60 * ring, outline=CREAM + (int(220 * (1 - ring)),), width=5)
    label(p, "APOLLO 11 · 14 · 15", (cx, 1050), 28, BG, box=CREAM)

def S_photon(sc, lt, dur, t, p):
    header(p)
    title(p, "JUST 1 PHOTON", 330, 124, MUST, RUST, u=lt / 0.3)
    title(p, "EVERY FEW SECONDS", 460, 92, u=(lt - 0.1) / 0.3)
    mx, my, mr = 540, 760, 120; dx, dy = 540, 1380
    w = ease(lt / 0.8)
    p.poly([(dx - 14, dy - 60), (dx + 14, dy - 60), (dx + 330 * w + 14, my + 40), (dx - 330 * w - 14, my + 40)], fill=ORANGE + (60,))
    p.poly([(dx - 6, dy - 60), (dx + 6, dy - 60), (dx + 160 * w + 6, my + 40), (dx - 160 * w - 6, my + 40)], fill=ORANGE + (70,))
    body(p, "moon", mx, my, mr)
    for k in range(26):  # photons going up
        u = ((lt * 0.9) + k / 26) % 1.0; sx = (((k * 37) % 26) / 25 - 0.5) * 2
        x = dx + sx * 300 * u * w; y = dy - 70 - (dy - 70 - my - 40) * u
        p.circ(x, y, 5, fill=MUST + (int(230 * (1 - u * 0.5)),))
    # the lonely returning photon
    ret = (lt - 0.7) / 1.6
    if 0 < ret < 1:
        u = ease(ret); x = mx + 20 - 20 * u; y = my + 60 + (dy - 80 - my - 60) * u
        for k in range(5): p.circ(x, y - k * 14, 12 - k * 2, fill=CREAM + (220 - k * 40,))
        p.circ(x, y, 26, outline=CREAM, width=4)
    if ret >= 1:
        f = min(1.0, (ret - 1) * 3); p.circ(dx, dy - 70, 30 + 90 * f, outline=CREAM + (int(255 * (1 - f)),), width=6)
        label(p, "1 PHOTON RECEIVED", (dx, dy - 180), 30, BG, box=CREAM)
    # observatory dome
    p.rect([0, dy + 40, W, dy + 160], fill=BG2)
    p.rect([dx - 150, dy - 10, dx + 150, dy + 60], fill=TAN)
    p.d.pieslice([(dx - 150) * S, (dy - 160) * S, (dx + 150) * S, (dy + 140) * S], 180, 360, fill=CREAM)
    halftone_dome = [(dx + 40 + i * 22, dy - 120 + j * 22) for i in range(5) for j in range(6)]
    for x, y in halftone_dome:
        if (x - dx) ** 2 / 150 ** 2 + (y - dy + 10) ** 2 / 150 ** 2 < 0.95 and y < dy - 10: p.circ(x, y, 3 + (x - dx - 40) / 30, fill=BG + (170,))
    p.rect([dx - 16, dy - 150, dx + 16, dy - 10], fill=DEEP)
    hstripes(p, dx - 150, dx + 150, dy + 10, 10, 4)
    label(p, "BEAM: MILES WIDE", (850, 960), 22, CREAM, box=BG2)

HOOK_CACHE = {}
def S_end(sc, lt, dur, t, p):
    header(p, "MISSION STATUS")
    title(p, "SOUNDS FAKE?", 380, 128)
    click = sc.get("click_at", 0.45); on = back((lt - click) / 0.35); onc = max(0.0, min(1.0, on))
    p.rrect([140 + 10, 760 + 10, 940 + 10, 1240 + 10], 40, fill=(0, 0, 0, 80))
    p.rrect([140, 760, 940, 1240], 40, fill=BG2); p.rrect([140, 760, 940, 1240], 40, outline=TAN, width=4)
    hstripes(p, 180, 900, 800, 12, 5)
    for sx, sy in ((180, 1200), (900, 1200)): p.circ(sx, sy, 12, fill=TAN); p.line([(sx - 7, sy - 7), (sx + 7, sy + 7)], BG2, 3)
    p.text((300, 930), "FAKE", JOST(70), CREAM if on < 0.5 else (130, 110, 90))
    p.text((780, 930), "TRUE", JOST(70), MUST if on >= 0.5 else (130, 110, 90))
    x0, x1, y = 280, 800, 1080
    p.rrect([x0 - 70, y - 60, x1 + 70, y + 60], 60, fill=DEEP)
    kx = x0 + (x1 - x0) * on
    if onc > 0: p.rrect([x0 - 70, y - 60, max(x0 + 60, kx + 60), y + 60], 60, fill=ORANGE)
    body(p, "moon", kx, y, 70)
    if on >= 0.5:
        u = back((lt - click - 0.15) / 0.35)
        if u > 0: title(p, "IT'S TRUE.", 1380, int(max(10, 118 * min(1.2, u))), MUST, RUST)
        label(p, "FOLLOW FOR MORE", (540, 1480), 30, TAN)

SCENES = dict(hook=S_hook, loop=S_loop, drift=S_drift, nails=S_nails, tides=S_tides, mirrors=S_mirrors, photon=S_photon, end=S_end)

# ---------- audio: Rhodes + analog bass groove, Quindar beeps ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
def rhodes(f, dur):
    tt = np.arange(int(dur * SR)) / SR
    return (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * 2 * f * tt) * np.exp(-tt * 6)
            + 0.15 * np.sin(2 * np.pi * 7 * f * tt) * np.exp(-tt * 30)) * np.exp(-tt * 2.2) * (1 + 0.2 * np.sin(2 * np.pi * 4.5 * tt))
def bass(f, dur):
    tt = np.arange(int(dur * SR)) / SR; ph = (f * tt) % 1.0
    saw = 2 * ph - 1; sm = np.convolve(saw, np.ones(18) / 18, mode="same")
    return (0.6 * sm + 0.6 * np.sin(2 * np.pi * f * tt)) * np.exp(-tt * 3.5) * np.clip(tt / 0.005, 0, 1)
CH = [(146.83, 174.61, 220.0, 261.63), (196.0, 246.94, 293.66, 349.23), (164.81, 196.0, 246.94, 293.66), (220.0, 277.18, 329.63, 392.0)]
BS = [73.42, 98.0, 82.41, 110.0]
beat = 60 / 96
for b in range(int(total / beat) + 2):
    bar, pos = (b // 4) % 4, b % 4; t0 = b * beat
    if pos in (0, 2):
        for k, f in enumerate(CH[bar]): place(music, t0 + (0.0 if pos == 0 else beat * 0.5) + k * 0.012, rhodes(f, 1.4), 0.045)
    place(music, t0, bass(BS[bar], beat * 0.9), 0.12)
    if pos == 3: place(music, t0 + beat / 2, bass(BS[bar] * 2, beat * 0.4), 0.07)
    tt = np.arange(int(0.25 * SR)) / SR
    if pos in (0, 2): place(music, t0, np.sin(2 * np.pi * (50 + 70 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 12), 0.22)
    if pos in (1, 3): place(music, t0, np.random.default_rng(b).normal(0, 1, len(tt)) * np.exp(-tt * 22), 0.05)
    hh = np.random.default_rng(b + 99).normal(0, 1, int(0.04 * SR)); hh = hh - np.convolve(hh, np.ones(4) / 4, "same")
    place(music, t0 + beat / 2, hh * np.exp(-np.arange(len(hh)) / SR * 90), 0.03)
def quindar(at, f=2525.0, dur=0.22, g=0.035):
    tt = np.arange(int(dur * SR)) / SR; place(music, at, np.sin(2 * np.pi * f * tt) * np.clip(tt / 0.005, 0, 1) * np.clip((dur - tt) / 0.005, 0, 1), g)
hook_hit(music, 0.35)
for s_ in scene_starts(spec): whoosh(music, s_, 0.08); quindar(s_ + 0.02)
L = {ln["scene"]["type"]: ln for ln in spec["lines"]}
if "mirrors" in L:  # laser zap
    tt = np.arange(int(0.5 * SR)) / SR; place(music, L["mirrors"]["_s"] + 0.5, np.sin(2 * np.pi * (1800 * np.exp(-tt * 5) + 300) * tt) * np.exp(-tt * 6), 0.06)
if "photon" in L:
    place(music, L["photon"]["_s"] + 0.7 + 1.6, tone(1760, 0.6, decay=5, harm=(1, 2)), 0.1)
end_ln = spec["lines"][-1]
quindar(end_ln["_s"] + end_ln["scene"].get("click_at", 0.45) + 0.05, 2525, 0.3, 0.05)
place(music, end_ln["_s"] + end_ln["scene"].get("click_at", 0.45) + 0.1, tone(1174.7, 0.6, decay=5, harm=(1, 2)), 0.1)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.35)

# ---------- captions, wipes, progress, frame ----------
groups = caption_groups(words, 3)
def caption(p, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0].upper() for i in g]; size = 72
    while p.tlen(" ".join(ws), JOST(size, 800)) > W - 200 and size > 36: size -= 4
    f = JOST(size, 800); tw = p.tlen(" ".join(ws), f); x = (W - tw) / 2; y = 1625
    p.rrect([x - 36 + 7, y - size * 0.78 + 7, x + tw + 36 + 7, y + size * 0.78 + 7], 20, fill=ORANGE)
    p.rrect([x - 36, y - size * 0.78, x + tw + 36, y + size * 0.78], 20, fill=CREAM, outline=BG, width=5)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        p.text((x, y), w, f, RUST if on else BG, anchor="lm"); x += p.tlen(w + " ", f)

def wipe(p, u):
    """Three diagonal 70s stripes sweep down across the cut."""
    c = -900 + 3200 * eout(u)
    for k, col in enumerate(STRIPES):
        y0 = c - k * 170
        p.poly([(0, y0), (W, y0 - 520), (W, y0 - 520 + 150), (0, y0 + 150)], fill=col)

def scene_frame(t):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = BASE.copy(); p = P(img)
    SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t, p)
    if ln is not spec["lines"][0] and lt < 0.34: wipe(p, lt / 0.34)
    return img, p

def frame(t, fi):
    img, p = scene_frame(t)
    tail = total - t
    if tail < 0.45:  # dissolve back into the hook for the loop
        if "h" not in HOOK_CACHE:
            hi = BASE.copy(); S_hook({}, 0.0, 1.0, 0.0, P(hi)); HOOK_CACHE["h"] = hi
        img = Image.blend(img, HOOK_CACHE["h"], ease(1 - tail / 0.45)); p = P(img)
    caption(p, t)
    p.rect([0, H - 12, W, H], fill=CREAM + (40,)); p.rect([0, H - 12, W * t / total, H], fill=ORANGE)
    return img.reduce(S).tobytes()

if __name__ == "__main__":
    print(" ".join(f"{l['_s']:.2f}" for l in spec["lines"]), f"total {total:.2f}")
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
