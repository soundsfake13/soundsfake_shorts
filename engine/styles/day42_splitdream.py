"""Day 42 — SPLIT-DREAM style (dolphins sleep with half their brain).
The frame is split down the middle like the dolphin's brain. LEFT = asleep: a moonlit dreamscape (indigo/violet night,
soft glowing pastel shapes, drifting bokeh orbs, twinkling stars, floating z's, Young Serif with a halo).
RIGHT = awake: a crisp night-watch display (black-teal, fine grid, sweeping scan line, sonar rings, Space Mono labels,
hard cyan drop shadows). Every element is drawn twice — once per world — and the two layers are cut together at the
seam, so a single dolphin / brain / title is half dream, half alert. Scene changes are a quick eyelid BLINK.
The halves physically swap (sliding wipe) in the 'swap' scene, and keep cycling in 'days'.
Ending: FAKE -> TRUE switch whose knob is an eye: closed on the dream side, wide open on the alert side.
Music: music-box bells + soft pad (dream) with sonar pings (alert).
Usage: python3 engine/styles/day42_splitdream.py spec.json out.mp4 [t1,t2 preview]
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
        path = {"serif": f"{FONTS}/YoungSerif-Regular.ttf", "mono": f"{FONTS}/DMMono-Medium.ttf",
                "monor": f"{FONTS}/DMMono-Medium.ttf", "bold": f"{INTER}/InterDisplay-Bold.otf"}[kind]
        _F[k] = ImageFont.truetype(path, int(s))
    return _F[k]

SEAM = W // 2
def ac(L, sp, pos=(0, 0)):
    """alpha-blend an RGBA sprite onto an RGB layer (layers are RGB so ImageDraw 'RGBA' blends translucent ink)."""
    L.paste(sp, (int(pos[0]), int(pos[1])), sp)
# dream palette
NIGHT, VIOLET, LAV, PINK, MOON = (16, 12, 46), (62, 36, 104), (196, 176, 255), (255, 196, 232), (255, 238, 210)
# alert palette
BLACK, TEAL, CYAN, WHITE, SIGNAL = (3, 14, 20), (8, 40, 52), (70, 236, 255), (240, 252, 255), (255, 170, 60)
SURF = 780                                                                  # water surface line (sea scenes)

# ---------- backgrounds (built once) ----------
def _grad(top, mid, bot, h=H):
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    a = np.array(top, np.float32); b = np.array(mid, np.float32); c = np.array(bot, np.float32)
    g = np.where(y < 0.5, a + (b - a) * (y / 0.5), b + (c - b) * ((y - 0.5) / 0.5))
    return np.repeat(g[:, None, :], W, 1).reshape(h, W, 3)

def _dream(sea):
    img = _grad(NIGHT, (40, 26, 84), (22, 16, 60)) if not sea else _grad((22, 14, 58), (70, 40, 112), (12, 14, 46))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); r = random.Random(42 + sea)
    for _ in range(9):                                                      # soft colour clouds
        cx, cy, R = r.uniform(0, W), r.uniform(0, H), r.uniform(200, 420)
        c = np.array(r.choice([(120, 80, 200), (200, 110, 190), (90, 90, 210), (160, 120, 230)]), np.float32)
        img += c * (0.22 * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / R ** 2))[..., None]
    if sea:
        mx, my = 150, 650
        img += np.array((255, 220, 200), np.float32) * (0.5 * np.exp(-((xx - mx) ** 2 + (yy - my) ** 2) / 260 ** 2))[..., None]
        under = (yy > SURF)[..., None]
        img = np.where(under, img * 0.62 + np.array((10, 20, 60), np.float32) * 0.38, img)
        streak = np.exp(-((xx - mx) / (40 + (yy - SURF) * 0.12)) ** 2) * np.exp(-np.maximum(yy - SURF, 0) / 420) * (yy > SURF)
        wob = (np.sin(yy * 0.35) * 0.5 + 0.5) ** 3
        img += np.array((255, 226, 210), np.float32) * (0.55 * streak * (0.4 + 0.6 * wob))[..., None]
    img += np.random.default_rng(42).normal(0, 2.0, (H, W, 1))
    im = Image.fromarray(img.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))
    if sea:
        d = ImageDraw.Draw(im, "RGBA")
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
        gd.ellipse([150 - 64, 650 - 64, 150 + 64, 650 + 64], fill=MOON + (255,))
        gd.line([(0, SURF), (W, SURF)], fill=(230, 210, 255, 180), width=6)
        im = im.convert("RGBA"); im.alpha_composite(g.filter(ImageFilter.GaussianBlur(16)))
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(2)))
        im = im.convert("RGB")
    return im

def _alert(sea):
    img = _grad(BLACK, (4, 22, 30), (2, 12, 18))
    im = Image.fromarray(img.clip(0, 255).astype(np.uint8)).convert("RGBA"); d = ImageDraw.Draw(im)
    for x in range(0, W, 54): d.line([(x, 0), (x, H)], fill=(18, 64, 76, 255) if x % 216 else (24, 88, 104, 255), width=1)
    for y in range(0, H, 54): d.line([(0, y), (W, y)], fill=(18, 64, 76, 255) if y % 216 else (24, 88, 104, 255), width=1)
    for x in range(SEAM + 30, W - 20, 27): d.line([(x, 160), (x, 170 if x % 108 else 182)], fill=CYAN + (160,), width=2)
    if sea:
        under = Image.new("RGBA", (W, H - SURF), (0, 30, 44, 110)); im.alpha_composite(under, (0, SURF))
        d.line([(0, SURF), (W, SURF)], fill=CYAN + (255,), width=3)
        for x in range(SEAM + 20, W, 36): d.line([(x, SURF), (x, SURF + 14)], fill=CYAN + (200,), width=2)
        for i, y in enumerate(range(SURF + 120, H - 300, 120)):
            d.text((W - 40, y), f"-{(i + 1) * 2:02d}m", font=F("monor", 24), fill=CYAN + (150,), anchor="rm")
    return im.convert("RGB")

BG = {"sea": (_dream(1), _alert(1)), "plain": (_dream(0), _alert(0))}

# small sprites
def _soft(r, col, a=1.0):
    s = 2 * r; yy, xx = np.mgrid[0:s, 0:s].astype(np.float32) - r
    al = np.exp(-(xx ** 2 + yy ** 2) / (0.35 * r * r)) * a
    arr = np.zeros((s, s, 4), np.uint8); arr[..., :3] = col; arr[..., 3] = (al.clip(0, 1) * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")
STAR = _soft(14, MOON); ORB = {c: _soft(70, c, 0.35) for c in [(200, 150, 255), (255, 170, 220), (150, 170, 255)]}
RS = random.Random(7)
STARS = [(RS.uniform(0, W), RS.uniform(0, H), RS.uniform(0, 6.28), RS.uniform(0.6, 1.4)) for _ in range(60)]
ORBS = [(RS.uniform(0, W), RS.uniform(0, H), RS.uniform(-12, 12), RS.uniform(-30, -10), RS.choice(list(ORB))) for _ in range(10)]

def dream_life(D, t, sea):
    for (x, y, ph, s) in STARS:
        if sea and y > SURF - 20: continue
        k = 0.5 + 0.5 * math.sin(t * 2.2 * s + ph)
        sz = int(10 + 18 * k * s)
        sp = STAR.resize((sz, sz)); ac(D, sp, (int(x - sz / 2), int(y - sz / 2)))
    for (x, y, vx, vy, c) in ORBS:
        px, py = (x + vx * t) % (W + 140) - 70, (y + vy * t) % (H + 140) - 70
        ac(D, ORB[c], (int(px - 70), int(py - 70)))

def alert_life(A, t):
    d = ImageDraw.Draw(A, "RGBA"); y = int((t * 420) % (H + 200)) - 100
    for k in range(14): d.line([(0, y - k * 6), (W, y - k * 6)], fill=CYAN + (int(70 * (1 - k / 14)),), width=6)
    d.line([(0, y), (W, y)], fill=CYAN + (170,), width=2)

# ---------- split-styled text ----------
_TP = {}
def text_pair(s, font_kind, size):
    """same glyph geometry, two finishes: dream (cream + lavender halo, softened) / alert (white + hard cyan shadow)."""
    k = (s, font_kind, size)
    if k in _TP: return _TP[k]
    f = F(font_kind, size); bb = f.getbbox(s, anchor="mm"); pad = 50
    w_, h_ = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad; ox, oy = -bb[0] + pad, -bb[1] + pad
    m = Image.new("L", (w_, h_), 0); ImageDraw.Draw(m).text((ox, oy), s, font=f, fill=255, anchor="mm")
    dp = Image.new("RGBA", (w_, h_), (150, 110, 255, 0)); dp.putalpha(m.filter(ImageFilter.GaussianBlur(16)).point(lambda p: min(255, int(p * 1.6))))
    dt = Image.new("RGBA", (w_, h_), (255, 240, 252, 0)); dt.putalpha(m.filter(ImageFilter.GaussianBlur(0.8))); dp.alpha_composite(dt)
    ap = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    sh = Image.new("RGBA", (w_, h_), (0, 150, 180, 0)); sh.putalpha(ImageChops.offset(m, 6, 6)); ap.alpha_composite(sh)
    at = Image.new("RGBA", (w_, h_), WHITE + (0,)); at.putalpha(m); ap.alpha_composite(at)
    _TP[k] = (dp, ap, ox, oy); return _TP[k]

def _fade(p, a):
    if a >= 0.999: return p
    q = p.copy(); q.putalpha(p.getchannel("A").point(lambda v: int(v * a))); return q

def stext(D, A, s, kind, size, x, y, a=1.0):
    if a <= 0.01: return
    dp, ap, ox, oy = text_pair(s, kind, size)
    ac(D, _fade(dp, a), (int(x - ox), int(y - oy))); ac(A, _fade(ap, a), (int(x - ox), int(y - oy)))

def fitsize(s, kind, size, maxw=W - 120):
    while F(kind, size).getlength(s) > maxw and size > 40: size -= 4
    return size

def title(D, A, lines, lt, y0=250, size=128, instant=False):
    for i, s in enumerate(lines):
        u = 1.0 if instant else eout((lt - 0.1 * i) / 0.4)
        stext(D, A, s, "serif", fitsize(s, "serif", size), W / 2, y0 + i * size * 1.08 + 26 * (1 - u), u)

def dlabel(D, s, size, x, y, a=1.0, col=LAV):
    """dream-only label (soft italic-ish serif with halo)."""
    if a <= 0.01: return
    dp, _, ox, oy = text_pair(s, "serif", size); ac(D, _fade(dp, a), (int(x - ox), int(y - oy)))
def alabel(A, s, size, x, y, a=1.0):
    if a <= 0.01: return
    _, ap, ox, oy = text_pair(s, "mono", size); ac(A, _fade(ap, a), (int(x - ox), int(y - oy)))

def zzz(D, x, y, t, n=3, s=1.0):
    for k in range(n):
        ph = (t * 0.45 + k / n) % 1.0
        dlabel(D, "z", int((40 + 50 * ph) * s), x + 60 * ph * s + 20 * math.sin(ph * 6), y - 220 * ph * s, math.sin(math.pi * ph))

def brackets(A, cx, cy, rw, rh, a=1.0):
    d = ImageDraw.Draw(A, "RGBA"); c = CYAN + (int(255 * a),); L = 36
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = cx + sx * rw, cy + sy * rh
            d.line([(x, y), (x - sx * L, y)], fill=c, width=4); d.line([(x, y), (x, y - sy * L)], fill=c, width=4)

def sonar(A, x, y, t, rmax=300, period=1.6, a=1.0):
    d = ImageDraw.Draw(A, "RGBA")
    for k in range(3):
        ph = ((t / period) + k / 3) % 1.0; r = 30 + rmax * ph
        d.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], outline=CYAN + (int(200 * (1 - ph) * a),), width=3)

# ---------- dolphin (one outline, two finishes) ----------
OUT = [(1.00, 0.030), (0.965, 0.012), (0.93, 0.0), (0.905, -0.03), (0.88, -0.075), (0.84, -0.11), (0.76, -0.135),
       (0.64, -0.145), (0.58, -0.145), (0.53, -0.19), (0.48, -0.235), (0.43, -0.258), (0.445, -0.22), (0.46, -0.17),
       (0.44, -0.13), (0.34, -0.105), (0.24, -0.07), (0.15, -0.04), (0.09, -0.025), (0.06, -0.03), (0.02, -0.08),
       (-0.03, -0.12), (-0.045, -0.115), (-0.02, -0.06), (0.0, -0.005), (-0.02, 0.05), (-0.045, 0.10), (-0.03, 0.105),
       (0.02, 0.07), (0.06, 0.03), (0.09, 0.03), (0.15, 0.05), (0.24, 0.085), (0.34, 0.12), (0.46, 0.14), (0.60, 0.135),
       (0.62, 0.15), (0.57, 0.225), (0.585, 0.235), (0.67, 0.17), (0.70, 0.125), (0.80, 0.10), (0.87, 0.07),
       (0.92, 0.05), (0.96, 0.04), (0.99, 0.035)]
def chaikin(pts, n=2):
    for _ in range(n):
        q = []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        pts = q
    return pts
_DOL = {}
def dolphin(L, eye_open_alert=True):
    """returns (dream_sprite, alert_sprite) of the same geometry; the body centre is the sprite centre."""
    k = (int(L), eye_open_alert)
    if k in _DOL: return _DOL[k]
    S = 2; pad = 0.2 * L; w_, h_ = int(1.1 * L + 2 * pad), int(0.55 * L + 2 * pad)
    def P(x, y): return ((x * L + pad + 0.05 * L) * S, (y * L + h_ / 2) * S)
    poly = [P(x, y) for x, y in chaikin(OUT, 2)]
    m = Image.new("L", (w_ * S, h_ * S), 0); ImageDraw.Draw(m).polygon(poly, fill=255); m = m.resize((w_, h_), Image.LANCZOS)
    yy = np.linspace(0, 1, h_, dtype=np.float32)[:, None, None]
    ex, ey = 0.83, -0.035; ecx, ecy = (ex * L + pad + 0.05 * L), (ey * L + h_ / 2)
    # dream finish
    top, bel = np.array((170, 150, 250), np.float32), np.array((255, 205, 236), np.float32)
    col = np.repeat((top + (bel - top) * np.clip((yy - 0.35) / 0.35, 0, 1)), w_, 1)
    dsp = Image.fromarray(col.astype(np.uint8)).convert("RGBA"); dsp.putalpha(m.filter(ImageFilter.GaussianBlur(1.2)))
    hl = Image.new("L", (w_ * S, h_ * S), 0); ImageDraw.Draw(hl).line([P(x, y + 0.03) for x, y in [(0.86, -0.07), (0.72, -0.095), (0.55, -0.1), (0.35, -0.07), (0.2, -0.04)]], fill=170, width=int(0.02 * L * S), joint="curve")
    hl = hl.resize((w_, h_), Image.LANCZOS).filter(ImageFilter.GaussianBlur(5))
    dsp.alpha_composite(Image.merge("RGBA", [Image.new("L", (w_, h_), 255)] * 3 + [ImageChops.multiply(hl, m)]))
    dd = ImageDraw.Draw(dsp); er = 0.022 * L
    dd.arc([ecx - er, ecy - er * 0.9, ecx + er, ecy + er * 0.9], 15, 165, fill=(90, 60, 150, 255), width=max(3, int(L * 0.006)))
    glow = Image.new("RGBA", (w_, h_), (170, 140, 255, 0)); glow.putalpha(m.filter(ImageFilter.GaussianBlur(22)).point(lambda p: int(p * 0.75)))
    glow.alpha_composite(dsp); dsp = glow
    # alert finish
    top, bel = np.array((16, 62, 78), np.float32), np.array((6, 26, 36), np.float32)
    col = np.repeat((top + (bel - top) * np.clip((yy - 0.3) / 0.5, 0, 1)), w_, 1)
    asp = Image.fromarray(col.astype(np.uint8)).convert("RGBA"); asp.putalpha(m)
    lines = Image.new("L", (w_ * S, h_ * S), 0); ld = ImageDraw.Draw(lines)
    for fx in np.arange(0.12, 0.98, 0.07): ld.line([P(fx, -0.4), P(fx, 0.4)], fill=90, width=2 * S)
    ld.line([P(x, y) for x, y in [(0.86, -0.075), (0.72, -0.1), (0.55, -0.105), (0.35, -0.075), (0.2, -0.045)]], fill=255, width=3 * S)
    lines = ImageChops.multiply(lines.resize((w_, h_), Image.LANCZOS), m)
    asp.alpha_composite(Image.merge("RGBA", [Image.new("L", (w_, h_), c) for c in CYAN] + [lines]))
    edge = Image.new("L", (w_ * S, h_ * S), 0); ImageDraw.Draw(edge).line(poly + [poly[0]], fill=255, width=5 * S, joint="curve")
    edge = edge.resize((w_, h_), Image.LANCZOS)
    asp.alpha_composite(Image.merge("RGBA", [Image.new("L", (w_, h_), c) for c in CYAN] + [edge]))
    ad = ImageDraw.Draw(asp); er = 0.026 * L
    if eye_open_alert:
        ad.ellipse([ecx - er, ecy - er, ecx + er, ecy + er], fill=WHITE + (255,), outline=CYAN + (255,), width=3)
        ad.ellipse([ecx - er * 0.5 + er * 0.25, ecy - er * 0.55, ecx + er * 0.5 + er * 0.25, ecy + er * 0.45], fill=(4, 10, 16, 255))
    _DOL[k] = (dsp, asp); return _DOL[k]

def put_dolphin(D, A, cx, cy, L, ang=0.0):
    dsp, asp = dolphin(L)
    if abs(ang) > 0.01:
        dsp = dsp.rotate(ang, resample=Image.BICUBIC, expand=True); asp = asp.rotate(ang, resample=Image.BICUBIC, expand=True)
    ac(D, dsp, (int(cx - dsp.width / 2), int(cy - dsp.height / 2)))
    ac(A, asp, (int(cx - asp.width / 2), int(cy - asp.height / 2)))

def head_pos(cx, cy, L, ang=0.0, fx=0.83, fy=-0.035):
    w_ = 1.1 * L + 0.4 * L; x = fx * L + 0.2 * L + 0.05 * L - w_ / 2; y = fy * L
    a = math.radians(-ang); return cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)

# ---------- brain (top view) ----------
def _brain(R=300):
    S = 2; w_, h_ = int(2.3 * R), int(2.9 * R); cx, cy = w_ / 2, h_ / 2
    def shape(sx):
        pts = []
        for i in range(81):
            th = -math.pi / 2 + math.pi * i / 80
            x = R * 0.95 * math.cos(th) ** 0.75 if math.cos(th) > 0 else 0; y = R * 1.25 * math.sin(th)
            x *= 1 - 0.12 * max(0, -math.sin(th))
            pts.append(((cx + sx * (10 + x)) * S, (cy + y) * S))
        pts += [((cx + sx * 10) * S, (cy + R * 1.25) * S), ((cx + sx * 10) * S, (cy - R * 1.25) * S)]
        return pts
    m = Image.new("L", (w_ * S, h_ * S), 0); d = ImageDraw.Draw(m); d.polygon(shape(-1), fill=255); d.polygon(shape(1), fill=255)
    m = m.resize((w_, h_), Image.LANCZOS)
    g = Image.new("L", (w_ * S, h_ * S), 0); gd = ImageDraw.Draw(g); r = random.Random(3)
    for _ in range(46):
        x, y, a = r.uniform(0, w_), r.uniform(0, h_), r.uniform(0, 6.28); pts = []
        for _ in range(26):
            pts.append((x * S, y * S)); a += r.uniform(-0.9, 0.9); x += 16 * math.cos(a); y += 16 * math.sin(a)
        gd.line(pts, fill=255, width=7 * S, joint="curve")
    g = ImageChops.multiply(g.resize((w_, h_), Image.LANCZOS), m.filter(ImageFilter.MinFilter(15)))
    # dream
    dsp = Image.new("RGBA", (w_, h_), (130, 100, 220, 0)); dsp.putalpha(m.filter(ImageFilter.GaussianBlur(1.5)))
    gl = Image.new("RGBA", (w_, h_), (230, 205, 255, 0)); gl.putalpha(g.filter(ImageFilter.GaussianBlur(3)).point(lambda p: int(p * 0.8))); dsp.alpha_composite(gl)
    halo = Image.new("RGBA", (w_, h_), (170, 130, 255, 0)); halo.putalpha(m.filter(ImageFilter.GaussianBlur(30)).point(lambda p: int(p * 0.7))); halo.alpha_composite(dsp); dsp = halo
    # alert
    asp = Image.new("RGBA", (w_, h_), TEAL + (0,)); asp.putalpha(m)
    thin = g.filter(ImageFilter.FIND_EDGES).point(lambda p: 255 if p > 60 else 0)
    asp.alpha_composite(Image.merge("RGBA", [Image.new("L", (w_, h_), c) for c in CYAN] + [thin.point(lambda p: int(p * 0.85))]))
    e = m.filter(ImageFilter.FIND_EDGES).point(lambda p: 255 if p > 40 else 0).filter(ImageFilter.MaxFilter(3))
    asp.alpha_composite(Image.merge("RGBA", [Image.new("L", (w_, h_), c) for c in CYAN] + [e]))
    return dsp, asp
BRAIN = _brain()

# ---------- eyes ----------
def eye_pair(D, A, cx, cy, r, open_k, look, t):
    """draw one eye on both layers: dream = closed lid (soft, lashes); alert = open (open_k 0..1), iris looks `look` (-1..1)."""
    dd = ImageDraw.Draw(D, "RGBA")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.arc([cx - r, cy - r * 0.9, cx + r, cy + r * 0.9], 20, 160, fill=MOON + (255,), width=12)
    for k in range(5):
        a = math.radians(40 + 25 * k); x0, y0 = cx + r * math.cos(a), cy + r * 0.9 * math.sin(a)
        ld.line([(x0, y0), (x0 + 0.28 * r * math.cos(a), y0 + 0.28 * r * math.sin(a))], fill=MOON + (255,), width=9)
    g = lay.filter(ImageFilter.GaussianBlur(14)); ac(D, g); ac(D, g); ac(D, lay.filter(ImageFilter.GaussianBlur(1)))
    # alert eye
    ad = ImageDraw.Draw(A, "RGBA"); h_ = r * 0.62 * open_k
    S = 2; m = Image.new("L", (int(2 * r * S + 8), int(2 * r * S + 8)), 0); md = ImageDraw.Draw(m); o = r * S + 4
    pts_top = [(o + r * S * math.cos(a), o - h_ * S * math.sin(a)) for a in np.linspace(math.pi, 0, 40)]
    pts_bot = [(o + r * S * math.cos(a), o + h_ * S * math.sin(a)) for a in np.linspace(0, math.pi, 40)]
    if h_ > 1:
        md.polygon(pts_top + pts_bot, fill=255)
        m = m.resize((int(m.width / S), int(m.height / S)), Image.LANCZOS)
        e = Image.new("RGBA", m.size, (0, 0, 0, 0)); ed = ImageDraw.Draw(e); c = m.width / 2
        ed.ellipse([0, 0, m.width, m.height], fill=WHITE + (255,))
        ix = c + look * r * 0.38; ir = r * 0.42
        ed.ellipse([ix - ir, c - ir, ix + ir, c + ir], fill=(20, 120, 140, 255), outline=CYAN + (255,), width=4)
        ed.ellipse([ix - ir * 0.5, c - ir * 0.5, ix + ir * 0.5, c + ir * 0.5], fill=(2, 8, 12, 255))
        ed.ellipse([ix - ir * 0.45 + ir * 0.3, c - ir * 0.62, ix - ir * 0.05 + ir * 0.3, c - ir * 0.22], fill=(255, 255, 255, 255))
        e.putalpha(ImageChops.multiply(e.getchannel("A"), m)); ac(A, e, (int(cx - c), int(cy - c)))
    ad.line([(cx - r * S / 2 * 2 / S, cy)] + [(cx + r * math.cos(a), cy - (h_) * math.sin(a)) for a in np.linspace(math.pi, 0, 40)], fill=CYAN + (255,), width=5)
    ad.line([(cx + r * math.cos(a), cy + (h_) * math.sin(a)) for a in np.linspace(0, math.pi, 40)], fill=CYAN + (255,), width=5)

# ---------- scenes: each draws on D (dream) and A (alert); returns dict(x0=, bg=) ----------
def S_hook(D, A, sc, lt, dur, t):
    title(D, A, ["Dolphins sleep", "with half", "their brain."], lt, 250, 132, instant=not sc.get("loop"))
    cy = 1150 + 14 * math.sin(t * 1.6); ang = 3 * math.sin(t * 1.6 + 0.6)
    put_dolphin(D, A, W / 2 + 10, cy, 860, ang)
    hx, hy = head_pos(W / 2 + 10, cy, 860, ang)
    sonar(A, hx, hy, t, 360); brackets(A, hx, hy, 60, 60, 0.9)
    zzz(D, 230, cy - 160, t)
    dlabel(D, "asleep", 54, SEAM / 2, 1400, 1.0); alabel(A, "AWAKE", 50, SEAM + SEAM / 2, 1400, 1.0)
    if sc.get("loop"):
        u = eout((lt - 0.3) / 0.4)
        stext(D, A, "now watch the eyes", "mono", 44, W / 2, 1470, u)
    return {"bg": "sea"}

def eeg_dream(D, y0, t, x1=W):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    pts = [(x, y0 + 70 * math.sin(x / 1080 * 2 * math.pi * 1.6 - t * 2.4)) for x in range(0, x1, 6)]
    ld.line(pts, fill=PINK + (255,), width=10, joint="curve")
    ac(D, lay.filter(ImageFilter.GaussianBlur(12))); ac(D, lay.filter(ImageFilter.GaussianBlur(1.5)))
NZ = np.random.default_rng(9).normal(0, 1, 4000)
def eeg_alert(A, y0, t):
    d = ImageDraw.Draw(A, "RGBA"); off = int(t * 260)
    pts = [(x, y0 + 26 * NZ[(x // 6 + off) % 4000] + 18 * math.sin(x * 0.21 + t * 9)) for x in range(0, W, 6)]
    d.line(pts, fill=CYAN + (255,), width=3)
    d.line([(SEAM + 20, y0 - 90), (SEAM + 20, y0 + 90)], fill=CYAN + (90,), width=1)

def S_brain(D, A, sc, lt, dur, t):
    title(D, A, ["One brain.", "Two shifts."], lt, 250, 128)
    dsp, asp = BRAIN; u = eout(lt / 0.5); y = 900 + 60 * (1 - u)
    ac(D, _fade(dsp, u), (int(W / 2 - dsp.width / 2), int(y - dsp.height / 2)))
    ac(A, _fade(asp, u), (int(W / 2 - asp.width / 2), int(y - asp.height / 2)))
    zzz(D, 250, 820, t, 3, 1.1)
    brackets(A, 800, y, 190, 260, u)
    eeg_dream(D, 1380, t); eeg_alert(A, 1380, t)
    v = eout((lt - 0.5) / 0.4)
    dlabel(D, "slow waves", 46, SEAM / 2, 1260, v); alabel(A, "AWAKE", 44, SEAM + SEAM / 2, 1260, v)
    return {"bg": "plain"}

def S_breathe(D, A, sc, lt, dur, t):
    title(D, A, ["Every breath", "is a choice."], lt, 240, 124)
    p = ease((lt - 0.2) / max(1.4, dur * 0.55)); cy = 1340 - (1340 - 860) * p; ang = 16 * math.sin(math.pi * p) + 2 * math.sin(t * 2)
    put_dolphin(D, A, W / 2, cy, 780, ang)
    bx, by = head_pos(W / 2, cy, 780, ang, 0.78, -0.13)
    if p > 0.97:                                                            # spout
        k = lt - (0.2 + max(1.4, dur * 0.55)); d = ImageDraw.Draw(A, "RGBA"); r = random.Random(1)
        for i in range(26):
            vx, vy = r.uniform(-120, 120), r.uniform(-700, -420); tt = (k * 1.2 + i * 0.03) % 0.9
            x, y = bx + vx * tt, by + vy * tt + 0.5 * 1300 * tt * tt
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=CYAN + (220,))
            ac(D, ORB[(255, 170, 220)].resize((40, 40)), (int(x - 20), int(y - 20)))
        alabel(A, "+1 BREATH", 48, SEAM + SEAM / 2, 1230, eout(k / 0.3))
        dlabel(D, "ahh…", 60, SEAM / 2, 1230, eout(k / 0.3))
    sonar(A, *head_pos(W / 2, cy, 780, ang), t, 260)
    zzz(D, 200, cy - 140, t)
    return {"bg": "sea"}

def S_eyes(D, A, sc, lt, dur, t):
    title(D, A, ["One eye shut.", "One on watch."], lt, 250, 124)
    ok = eout((lt - 0.3) / 0.35); look = math.sin(t * 2.4) * 0.9 if lt > 0.8 else 0
    eye_pair(D, A, 270, 880, 190, ok, look, t)
    eye_pair(D, A, 810, 880, 190, ok, look, t)
    zzz(D, 340, 780, t)
    brackets(A, 810, 880, 230, 170, ok)
    # watch cone
    if lt > 0.8:
        d = ImageDraw.Draw(A, "RGBA"); a = 90 + 40 * math.sin(t * 2.4)
        for k in range(5):
            r = 260 + k * 60; d.arc([810 - r, 880 - r, 810 + r, 880 + r], -a - 14 + 90, -a + 14 + 90, fill=CYAN + (180 - 30 * k,), width=4)
    dlabel(D, "sleeping side", 48, SEAM / 2, 1240, eout((lt - 0.4) / 0.4)); alabel(A, "ON WATCH", 44, SEAM + SEAM / 2, 1240, eout((lt - 0.4) / 0.4))
    return {"bg": "plain"}

def clock_face(D, A, cx, cy, R, hours):
    for L, (col, w, blur) in ((D, (MOON, 10, True)), (A, (CYAN, 5, False))):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=col + (255,), width=w)
        for k in range(12):
            a = math.radians(k * 30 - 90); r0 = R - (40 if k % 3 == 0 else 24)
            d.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + (R - 8) * math.cos(a), cy + (R - 8) * math.sin(a))], fill=col + (255,), width=w)
        if hours > 0.01:
            d.pieslice([cx - R + 30, cy - R + 30, cx + R - 30, cy + R - 30], -90, -90 + hours * 30, fill=col + (70,))
        a = math.radians(-90 + hours * 30)
        d.line([(cx, cy), (cx + (R - 60) * math.cos(a), cy + (R - 60) * math.sin(a))], fill=col + (255,), width=w + 4)
        d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=col + (255,))
        if blur: ac(L, lay.filter(ImageFilter.GaussianBlur(12))); ac(L, lay.filter(ImageFilter.GaussianBlur(1.2)))
        else: ac(L, lay)

def S_swap(D, A, sc, lt, dur, t):
    h = 2 * ease((lt - 0.1) / 1.1)
    title(D, A, ["Two hours later…", "they swap."], lt, 250, 112)
    clock_face(D, A, W / 2, 880, 260, h)
    stext(D, A, f"~{h:.1f} h", "mono", 64, W / 2, 1220, eout(lt / 0.3))
    s = ease((lt - 1.25) / 0.7); x0 = 540 * s
    if s > 0.95: dlabel(D, "now resting", 46, 810, 1360, (s - 0.95) * 20); alabel(A, "NOW AWAKE", 42, 270, 1360, (s - 0.95) * 20)
    if s < 0.05: dlabel(D, "asleep", 46, 270, 1360, 1 - s * 20); alabel(A, "AWAKE", 42, 810, 1360, 1 - s * 20)
    zzz(D, (x0 + 220) % W, 760, t)
    return {"bg": "plain", "x0": x0, "chrome": s < 0.02 or s > 0.98}

def S_days(D, A, sc, lt, dur, t):
    n = 1 + int(14 * ease((lt - 0.2) / max(1.5, dur - 1.2)))
    stext(D, A, "DAY", "mono", 64, W / 2, 330, 1.0)
    stext(D, A, f"{n}", "serif", 420, W / 2, 620, 1.0)
    stext(D, A, "still alert", "serif", 100, W / 2, 920, eout((lt - 0.3) / 0.4))
    for i in range(15):                                                     # day dots
        x = 120 + i * (840 / 14); on = i < n; c = (x, 1120)
        d = ImageDraw.Draw(A, "RGBA"); d.ellipse([x - 14, 1106, x + 14, 1134], outline=CYAN + (255,), width=3, fill=(CYAN + (255,)) if on else None)
        dd = ImageDraw.Draw(D, "RGBA"); dd.ellipse([x - 14, 1106, x + 14, 1134], fill=(MOON + (255,)) if on else (120, 100, 180, 255))
    put_dolphin(D, A, W / 2, 1300, 560, 2 * math.sin(t * 2))
    stext(D, A, "in a study of 2 dolphins", "mono", 38, W / 2, 1470, eout((lt - 0.8) / 0.4))
    x0 = (540 + lt * 340) % W
    return {"bg": "plain", "x0": x0, "chrome": False}

def S_end(D, A, sc, lt, dur, t):
    title(D, A, ["Sounds fake?"], 0, 300, 140, instant=True)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.35)
    y = 600; xa, xb = 350, 790
    for L, col in ((D, LAV), (A, CYAN)):
        d = ImageDraw.Draw(L, "RGBA"); d.rounded_rectangle([250, y - 90, 890, y + 90], 90, outline=col + (255,), width=6, fill=(0, 0, 0, 90))
    dlabel(D, "fake", 58, 350, y + 150, 1 - 0.6 * on); alabel(A, "TRUE", 56, 790, y + 150, 0.4 + 0.6 * on)
    x = xa + (xb - xa) * on
    eye_pair(D, A, x, y, 70, eout((lt - click - 0.2) / 0.3) if x > SEAM else 0.0, 0, t)
    if on > 0.6:
        u = eout((lt - click - 0.3) / 0.4)
        stext(D, A, "It's true.", "serif", 150, W / 2, 910, u)
        stext(D, A, "Follow for more.", "mono", 56, W / 2, 1050, eout((lt - click - 0.5) / 0.4))
    cy = 1250 + 10 * math.sin(t * 1.6)
    put_dolphin(D, A, W / 2 + 10, cy, 640, 3 * math.sin(t * 1.6 + 0.6))
    zzz(D, 150, cy - 40, t, 3, 0.8)
    return {"bg": "sea"}

SCENES = dict(hook=S_hook, brain=S_brain, breathe=S_breathe, eyes=S_eyes, swap=S_swap, days=S_days, end=S_end)

# ---------- audio: music box + pad (dream), sonar pings (alert) ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
scale = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.66, 1318.5]
pat = [0, 4, 2, 5, 3, 6, 4, 7, 5, 3, 4, 1, 2, 5, 4, 0]
for k in range(int(total / 0.36)):
    place(music, k * 0.36, tone(scale[pat[k % 16]], 1.6, decay=3.5, harm=(1, 2.76, 5.4)), 0.03)
for k, root in enumerate([130.81, 110.0, 87.31, 98.0] * 6):                 # C Am F G pads
    s0 = k * 3.6
    if s0 >= total: break
    seg = np.arange(int(4.2 * SR)) / SR; env = np.sin(np.pi * np.clip(seg / 4.2, 0, 1)) ** 1.5
    sig = sum(np.sin(2 * np.pi * root * h * seg + 0.3 * np.sin(2 * np.pi * 0.3 * seg)) / h for h in (1, 1.5, 2, 3)) * env
    place(music, s0, sig.astype(np.float32), 0.035)
def ping(at, gain=0.07):
    s = np.arange(int(0.9 * SR)) / SR; sig = np.sin(2 * np.pi * 1760 * s) * np.exp(-s * 6) * (1 + 0.3 * np.sin(2 * np.pi * 7 * s))
    place(music, at, sig.astype(np.float32), gain)
for k in range(int(total / 1.6)): ping(0.3 + k * 1.6)
hook_hit(music, 0.33)
for s_ in scene_starts(spec): whoosh(music, s_, 0.08)
for ln in spec["lines"]:
    if ln["scene"]["type"] == "end":
        place(music, ln["_s"] + ln["scene"].get("click_at", 0.45), tone(1046.5, 1.6, decay=3, harm=(1, 2, 3)), 0.12)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.35)

# ---------- compose ----------
_M = {}
def split_mask(x0):
    x0 = int(x0) % W
    if x0 in _M: return _M[x0]
    row = np.zeros(W, np.float32); xs = np.arange(W)
    rel = (xs - x0) % W; row = ((rel < SEAM)).astype(np.float32)
    m = Image.fromarray((row * 255).astype(np.uint8)[None, :].repeat(H, 0), "L")
    _M[x0] = m; return m

def seam(img, x0):
    d = ImageDraw.Draw(img)
    for x in {int(x0) % W, int(x0 + SEAM) % W}:
        if x <= 2 or x >= W - 2: continue
        lay = Image.new("RGBA", (40, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        ld.line([(20, 0), (20, H)], fill=(220, 210, 255, 255), width=4)
        ac(img, lay.filter(ImageFilter.GaussianBlur(8)), (x - 20, 0)); d.line([(x, 0), (x, H)], fill=(255, 255, 255, 255), width=2)

def chrome(D, A, x0, t):
    xd = (x0 + 270) % W; xa = (x0 + 810) % W
    d = ImageDraw.Draw(D, "RGBA"); d.ellipse([xd - 180, 92, xd - 150, 122], fill=MOON + (255,)); d.ellipse([xd - 172, 86, xd - 140, 118], fill=(40, 28, 90, 255))
    dlabel(D, "dreaming", 40, xd + 10, 108)
    alabel(A, "ON WATCH", 34, xa + 20, 108)
    if int(t * 2) % 2 == 0:
        ImageDraw.Draw(A, "RGBA").ellipse([xa - 150, 96, xa - 126, 120], fill=SIGNAL + (255,))

groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 72
    while F("bold", size).getlength(" ".join(ws)) > W - 220 and size > 36: size -= 4
    f = F("bold", size); tw = f.getlength(" ".join(ws)); x = (W - tw) / 2; y = 1585
    lay = Image.new("RGBA", (W, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); oy = 1585 - 60
    d.rounded_rectangle([x - 34, y - 20 - oy, x + tw + 34, y + size + 26 - oy], 30, fill=(6, 8, 26, 225))
    d.line([(x - 4, y + size + 26 - oy - 1), (W / 2, y + size + 26 - oy - 1)], fill=LAV + (255,), width=4)
    d.line([(W / 2, y + size + 26 - oy - 1), (x + tw + 4, y + size + 26 - oy - 1)], fill=CYAN + (255,), width=4)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y - oy), w, font=f, fill=(255, 220, 120, 255) if on else (255, 255, 255, 255)); x += f.getlength(w + " ")
    ac(img, lay, (0, oy))

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    typ = ln["scene"]["type"]
    sea = typ in ("hook", "breathe", "end")
    db, ab = BG["sea" if sea else "plain"]
    D = db.copy(); A = ab.copy()
    dream_life(D, t, sea); alert_life(A, t)
    info = SCENES[typ](D, A, ln["scene"], lt, dur, t)
    x0 = info.get("x0", 0)
    if info.get("chrome", True): chrome(D, A, x0, t)
    img = Image.composite(D, A, split_mask(x0))
    seam(img, x0)
    li = spec["lines"].index(ln)
    if li > 0 and spec["lines"][li - 1]["scene"]["type"] != typ and lt < 0.26:      # eyelid blink open
        k = 1 - eout(lt / 0.26); hh = int(H / 2 * k)
        if hh > 0:
            d = ImageDraw.Draw(img); d.rectangle([0, 0, W, hh], fill=(6, 4, 20, 255)); d.rectangle([0, H - hh, W, H], fill=(6, 4, 20, 255))
            d.line([(0, hh), (W, hh)], fill=LAV + (255,), width=4); d.line([(0, H - hh), (W, H - hh)], fill=CYAN + (255,), width=4)
    caption(img, t)
    d = ImageDraw.Draw(img); d.rectangle([0, H - 8, W, H], fill=(6, 8, 26, 255))
    px = int(W * t / total); d.rectangle([0, H - 8, min(px, SEAM), H], fill=LAV + (255,))
    if px > SEAM: d.rectangle([SEAM, H - 8, px, H], fill=CYAN + (255,))
    return img.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=23); print(f"done {total:.1f}s")
