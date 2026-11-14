"""Day 18 — HERALDRY / woven tapestry style (Scotland's national animal is the unicorn).
Everything is a flat heraldic charge woven into a navy tapestry: a procedural warp/weft thread texture is multiplied over
every frame, the field is a dark 'millefleur' meadow of tiny stitched flowers inside a madder-red border with gold
lozenges. Charges are drawn the heraldic way: flat ivory (argent) beasts with gold (or) horn, mane, hooves and chain,
thick dark outlines, generic shields (no real arms), coronets and red ribbon scrolls. Titles in Cinzel Decorative
gold with stitched outlines. Scene changes are a 'loom' wipe: coloured threads slide out sideways band by band.
Ending: an embroidered FAKE -> TRUE band whose knob is a gold unicorn coin.
Music: drone (A + E, reedy) + tin-whistle jig in A mixolydian + frame-drum.
Usage: python3 engine/styles/day18_heraldry.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
INTER = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter")
_F = {}
def F(kind, s):
    k = (kind, int(s))
    if k not in _F:
        if kind == "deco": f = ImageFont.truetype(f"{FONTS}/CinzelDecorative-Black.ttf", int(s))
        elif kind == "cin":
            f = ImageFont.truetype(f"{FONTS}/Cinzel[wght].ttf", int(s)); f.set_variation_by_name("Bold")
        elif kind == "cinb":
            f = ImageFont.truetype(f"{FONTS}/Cinzel[wght].ttf", int(s)); f.set_variation_by_name("Black")
        else: f = ImageFont.truetype(f"{INTER}/InterDisplay-Bold.otf", int(s))
        _F[k] = f
    return _F[k]

NAVY, DEEP, GOLD, GOLD2, IVORY, RED, INK, GREEN = (22, 34, 72), (12, 18, 42), (226, 176, 72), (168, 116, 38), \
    (242, 232, 208), (160, 40, 36), (14, 14, 26), (52, 88, 62)

def ac(L, sp, pos=(0, 0)): L.alpha_composite(sp, (int(pos[0]), int(pos[1])))

# ---------- tapestry field (built once) ----------
def _field():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.45) / H) ** 2)
    base = np.array(NAVY, np.float32) * (1.15 - 0.55 * r)[..., None]
    im = Image.fromarray(base.clip(0, 255).astype(np.uint8)).convert("RGBA"); d = ImageDraw.Draw(im, "RGBA")
    rnd = random.Random(18)
    for _ in range(240):                                                     # millefleur: sprigs + tiny flowers
        x, y = rnd.uniform(40, W - 40), rnd.uniform(40, H - 40)
        a = rnd.uniform(0, 6.28); L = rnd.uniform(14, 26)
        d.line([(x, y), (x + L * math.cos(a), y + L * math.sin(a))], fill=GREEN + (80,), width=4)
        for k in (-1, 1):
            b = a + k * 0.9; d.ellipse([x + 0.5 * L * math.cos(a) + 8 * math.cos(b) - 5, y + 0.5 * L * math.sin(a) + 8 * math.sin(b) - 3,
                                        x + 0.5 * L * math.cos(a) + 8 * math.cos(b) + 5, y + 0.5 * L * math.sin(a) + 8 * math.sin(b) + 3], fill=GREEN + (75,))
        c = rnd.choice([IVORY, RED, GOLD, (200, 120, 150), (130, 150, 220)])
        fx, fy = x + L * math.cos(a), y + L * math.sin(a)
        for p in range(5):
            q = p * 1.2566 + a; d.ellipse([fx + 6 * math.cos(q) - 5, fy + 6 * math.sin(q) - 5, fx + 6 * math.cos(q) + 5, fy + 6 * math.sin(q) + 5], fill=c + (80,))
        d.ellipse([fx - 3, fy - 3, fx + 3, fy + 3], fill=GOLD + (100,))
    # border: madder band + gold rules + lozenges
    B = 34
    d.rectangle([0, 0, W, B], fill=RED); d.rectangle([0, H - B, W, H], fill=RED)
    d.rectangle([0, 0, B, H], fill=RED); d.rectangle([W - B, 0, W, H], fill=RED)
    d.rectangle([B, B, W - B, H - B], outline=GOLD, width=5); d.rectangle([B + 12, B + 12, W - B - 12, H - B - 12], outline=GOLD2 + (200,), width=2)
    for x in range(20, W, 54):
        for y in (B / 2, H - B / 2): d.polygon([(x, y - 11), (x + 11, y), (x, y + 11), (x - 11, y)], fill=GOLD)
    for y in range(20, H, 54):
        for x in (B / 2, W - B / 2): d.polygon([(x, y - 11), (x + 11, y), (x, y + 11), (x - 11, y)], fill=GOLD)
    return im
FIELD = _field()

def _weave():
    """warp/weft texture: 7px cells, alternating over/under, each thread rounded across its width, slight per-thread tone."""
    yy, xx = np.mgrid[0:H, 0:W]; c = 7
    i, j = xx // c, yy // c; fx, fy = (xx % c) / c, (yy % c) / c
    over = ((i + j) % 2 == 0)
    rr = np.random.default_rng(3)
    warp_t = rr.normal(0, 0.035, W // c + 2)[i]; weft_t = rr.normal(0, 0.035, H // c + 2)[j]
    s_warp = 0.80 + 0.22 * np.sin(np.pi * fx) + warp_t
    s_weft = 0.80 + 0.22 * np.sin(np.pi * fy) + weft_t
    m = np.where(over, s_warp, s_weft)
    m *= np.where(over, 1.0 - 0.10 * (fy < 0.12), 1.0 - 0.10 * (fx < 0.12))    # tiny gap shadow at cell edge
    return np.clip(m, 0.6, 1.12).astype(np.float32)[..., None]
WEAVE = _weave()

# ---------- text: gold/ivory 'stitched' type ----------
_T = {}
def ttext(s, kind, size, col=GOLD, outline=INK, shadow=True):
    k = (s, kind, size, col, outline, shadow)
    if k in _T: return _T[k]
    f = F(kind, size); bb = f.getbbox(s, anchor="mm"); pad = 30
    w_, h_ = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad; ox, oy = -bb[0] + pad, -bb[1] + pad
    im = Image.new("RGBA", (w_, h_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    sw = max(3, size // 22)
    if shadow: d.text((ox + sw + 3, oy + sw + 4), s, font=f, fill=(0, 0, 0, 150), anchor="mm", stroke_width=sw, stroke_fill=(0, 0, 0, 150))
    d.text((ox, oy), s, font=f, fill=col + (255,), anchor="mm", stroke_width=sw, stroke_fill=outline + (255,))
    if col == GOLD:                                                         # lower half a touch darker (thread shading)
        m = Image.new("L", (w_, h_), 0); ImageDraw.Draw(m).text((ox, oy), s, font=f, fill=255, anchor="mm")
        g = np.linspace(0, 1, h_, dtype=np.float32)[:, None]; sh = Image.fromarray((np.clip((g - 0.5) * 2, 0, 1) * 80).repeat(w_, 1).astype(np.uint8))
        dk = Image.new("RGBA", (w_, h_), GOLD2 + (0,)); dk.putalpha(ImageChops.multiply(m, sh)); im.alpha_composite(dk)
    _T[k] = (im, ox, oy); return _T[k]

def put_text(img, s, kind, size, x, y, a=1.0, col=GOLD, outline=INK, scale=1.0):
    if a <= 0.01: return
    im, ox, oy = ttext(s, kind, size, col, outline)
    if abs(scale - 1) > 0.01:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR); ox *= scale; oy *= scale
    if a < 0.999: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    ac(img, im, (x - ox, y - oy))

def fit(s, kind, size, maxw=W - 160):
    while F(kind, size).getlength(s) > maxw and size > 30: size -= 4
    return size

def slam(lt, at=0.0, d=0.28): u = (lt - at) / d; return (0.0, 0.0) if u <= 0 else (min(1.0, u * 2.5), 1 + 0.6 * (1 - back(u)))

# ---------- heraldic beast (unicorn / lion), rampant facing left ----------
def _ell(cx, cy, rx, ry, ang, n=40):
    c, s = math.cos(ang), math.sin(ang)
    return [(cx + rx * math.cos(a) * c - ry * math.sin(a) * s, cy + rx * math.cos(a) * s + ry * math.sin(a) * c)
            for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]

_B = {}
def beast(kind, size, flip=False, collar=False):
    """returns RGBA sprite (size x size*1.2) — unit box 100 wide, origin offset so units (-10..110, -12..108)."""
    k = (kind, int(size), flip, collar)
    if k in _B: return _B[k]
    SS = 3; u = size / 100 * SS; ox, oy = 10, 12; Wc, Hc = int(120 * u), int(120 * u)
    def P(x, y): return ((x + ox) * u, (y + oy) * u)
    def PL(pts): return [P(*p) for p in pts]
    body = Image.new("L", (Wc, Hc), 0); gold = Image.new("L", (Wc, Hc), 0)
    db, dg = ImageDraw.Draw(body), ImageDraw.Draw(gold)
    def limb(dr, pts, w):
        dr.line(PL(pts), fill=255, width=int(w * u), joint="curve")
        for p in pts: x, y = P(*p); r = w * u / 2; dr.ellipse([x - r, y - r, x + r, y + r], fill=255)
    db.polygon(PL(_ell(57, 55, 21, 11, math.radians(50))), fill=255)            # body
    db.polygon(PL([(42, 44), (36, 31), (37, 21), (45, 15), (52, 22), (55, 36), (54, 44)]), fill=255)  # neck/chest
    db.polygon(PL(_ell(68, 69, 9, 7.5, 0.5)), fill=255)                         # haunch
    limb(db, [(45, 40), (32, 33), (24, 42)], 5.2); limb(db, [(48, 46), (37, 49), (32, 59)], 5.0)
    limb(db, [(64, 70), (56, 80), (60, 92)], 5.6); limb(db, [(72, 70), (78, 81), (73, 93)], 5.2)
    limb(db, [(78, 63), (88, 54), (86, 42), (91, 33)], 2.6)                    # tail
    if kind == "unicorn":
        db.polygon(PL([(46, 16), (42, 10), (36, 9), (30, 12), (23, 19), (19, 24), (22, 28), (30, 26), (37, 25), (44, 27)]), fill=255)
        db.polygon(PL([(39, 11), (42, 3), (45, 12)]), fill=255)                # ear
        dg.polygon(PL([(31, 13), (36, 9), (13, -9)]), fill=255)                # horn
        dg.polygon(PL([(30, 25.5), (28.5, 35), (31, 33), (34, 25)]), fill=255)     # beard
        for i, p in enumerate(np.linspace(0, 1, 9)):                           # curly mane down the neck
            x, y = 44 + 13 * p, 9 + 30 * p; r = 4.2 - 1.2 * p
            dg.ellipse(list(P(x + 2 - r, y - r)) + list(P(x + 2 + r, y + r)), fill=255)
        for hoof in [(24, 42), (32, 59), (60, 92), (73, 93)]:
            x, y = hoof; dg.polygon(PL([(x - 3.6, y + 1), (x + 3.6, y + 1), (x + 3.2, y + 5.5), (x - 3.2, y + 5.5)]), fill=255)
    else:                                                                      # lion: maned head, claws
        for a in np.linspace(0, 2 * math.pi, 14, endpoint=False):
            x, y = 36 + 11 * math.cos(a), 19 + 11 * math.sin(a)
            dg.ellipse(list(P(x - 5.5, y - 5.5)) + list(P(x + 5.5, y + 5.5)), fill=255)
        dg.ellipse(list(P(25, 8)) + list(P(47, 30)), fill=255)
        db.polygon(PL([(39, 11), (32, 11), (25, 17), (22, 22), (25, 27), (32, 29), (39, 26)]), fill=255)  # face
        for hoof in [(24, 42), (32, 59), (60, 92), (73, 93)]:
            x, y = hoof
            for c in (-2.5, 0, 2.5): dg.polygon(PL([(x + c - 1.2, y + 2), (x + c + 1.2, y + 2), (x + c - 2.5, y + 6.5)]), fill=255)
    for (x, y, r) in [(91, 31, 3.6), (88, 27, 3.0), (94, 26, 3.0), (91, 22, 2.6), (86, 33, 2.4)]:  # tail tuft (curls)
        dg.ellipse(list(P(x - r, y - r)) + list(P(x + r, y + r)), fill=255)
    if collar:                                                                 # gold coronet collar
        dg.polygon(PL([(37, 27), (48, 22), (52, 27), (40, 32)]), fill=255)
        for t_ in np.linspace(0.1, 0.9, 4):
            x0, y0 = 37 + (48 - 37) * t_, 27 + (22 - 27) * t_
            dg.polygon(PL([(x0 - 1.4, y0 + 0.5), (x0 + 0.4, y0 - 4.5), (x0 + 1.6, y0 - 0.3)]), fill=255)
    union = ImageChops.lighter(body, gold)
    outl = union.filter(ImageFilter.GaussianBlur(1.3 * u)).point(lambda v: 255 if v > 16 else 0)
    im = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
    im.paste(Image.new("RGBA", (Wc, Hc), INK + (255,)), (0, 0), outl)
    bcol = IVORY if kind == "unicorn" else GOLD
    gcol = GOLD if kind == "unicorn" else (196, 120, 40)
    bl = Image.new("RGBA", (Wc, Hc), bcol + (255,))
    g = np.linspace(0, 1, Hc, dtype=np.float32)[:, None]; gx = np.linspace(0, 1, Wc, dtype=np.float32)[None, :]
    shade = np.clip(0.35 * g + 0.25 * gx - 0.2, 0, 0.35)                       # lower-right a little darker
    arr = np.array(bl).astype(np.float32); arr[..., :3] *= (1 - shade)[..., None]; bl = Image.fromarray(arr.astype(np.uint8))
    im.paste(bl, (0, 0), body)
    gl = Image.new("RGBA", (Wc, Hc), gcol + (255,)); im.paste(gl, (0, 0), gold)
    d = ImageDraw.Draw(im); lw = max(2, int(0.7 * u)); dk = (120, 100, 70, 255) if kind == "unicorn" else (120, 60, 20, 255)
    if kind == "unicorn":
        for p in np.linspace(0.15, 0.85, 6):                                   # horn spiral bands
            a = (31 + (13 - 31) * p, 13 + (-9 - 13) * p); b = (36 + (13 - 36) * p, 9 + (-9 - 9) * p)
            d.line([P(a[0] - 0.4, a[1] + 0.8), P(b[0] + 0.6, b[1] - 0.6)], fill=GOLD2 + (255,), width=lw)
        ex, ey = P(32, 15); r = 1.4 * u; d.ellipse([ex - r, ey - r * 0.7, ex + r, ey + r * 0.7], fill=INK + (255,))
        d.line([P(20, 25), P(27, 25.5)], fill=dk, width=lw); nx, ny = P(22, 21.5); d.ellipse([nx - 0.8 * u, ny - 0.8 * u, nx + 0.8 * u, ny + 0.8 * u], fill=dk)
    else:
        ex, ey = P(30, 17); r = 1.3 * u; d.ellipse([ex - r, ey - r, ex + r, ey + r], fill=INK + (255,))
        d.line([P(24, 24), P(31, 25)], fill=dk, width=lw)
    d.arc(list(P(42, 36)) + list(P(58, 54)), 160, 260, fill=dk, width=lw)      # shoulder
    d.arc(list(P(58, 60)) + list(P(76, 78)), 180, 300, fill=dk, width=lw)      # thigh
    im = im.resize((Wc // SS, Hc // SS), Image.LANCZOS)
    if flip: im = im.transpose(Image.FLIP_LEFT_RIGHT)
    _B[k] = im; return im

def U2S(cx, cy, size, flip, x, y):
    """unit coords of a beast placed with put_beast -> screen coords."""
    s = size / 100; ux = (x + 10) * s; uy = (y + 12) * s; w = 120 * s
    if flip: ux = w - ux
    return cx - w / 2 + ux, cy - w / 2 + uy

def put_beast(img, kind, cx, cy, size, flip=False, collar=False, rot=0.0):
    sp = beast(kind, size, flip, collar)
    if abs(rot) > 0.05: sp = sp.rotate(rot, Image.BICUBIC, expand=False)
    ac(img, sp, (cx - sp.width / 2, cy - sp.height / 2))

def chain(img, pts, t, n=None, sway=0.0, reveal=1.0, link=26):
    """gold chain along a polyline of screen points (links alternate face-on / edge-on)."""
    seg = []
    for a, b in zip(pts, pts[1:]): seg.append((a, b, math.hypot(b[0] - a[0], b[1] - a[1])))
    total = sum(s[2] for s in seg); m = int(total / (link * 0.78)); d = ImageDraw.Draw(img, "RGBA")
    for i in range(int(m * reveal)):
        s_ = i * total / max(1, m); acc = 0
        for a, b, L in seg:
            if s_ <= acc + L: f = (s_ - acc) / L; break
            acc += L
        x, y = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        x += sway * math.sin(t * 2.2) * (s_ / total) ** 1.5
        ang = math.atan2(b[1] - a[1], b[0] - a[0]); ca, sa = math.cos(ang), math.sin(ang)
        rw, rh = link * 0.55, (link * 0.34 if i % 2 == 0 else link * 0.12)
        poly = [(x + rw * math.cos(q) * ca - rh * math.sin(q) * sa, y + rw * math.cos(q) * sa + rh * math.sin(q) * ca) for q in np.linspace(0, 6.283, 20)]
        d.polygon(poly, outline=INK + (255,), fill=None, width=10); d.polygon(poly, outline=GOLD + (255,), width=6)
        if i % 2 == 0: d.line([poly[3], poly[6]], fill=(255, 230, 160, 255), width=2)

def shield(img, cx, cy, w, kind="saltire", a=1.0, scale=1.0):
    w *= scale; h = w * 1.18; lay = Image.new("RGBA", (int(w + 40), int(h + 40)), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    ox, oy = 20, 20
    pts = [(ox, oy), (ox + w, oy)] + [(ox + w / 2 + (w / 2) * math.cos(q), oy + h * 0.45 + (h * 0.55) * math.sin(q) ** 1.0) for q in np.linspace(0, math.pi / 2, 14)][::-1][:0]
    side = [(ox + w - (w / 2) * (1 - math.cos(q)) , oy + h * 0.42 + h * 0.58 * math.sin(q)) for q in np.linspace(0, math.pi / 2, 16)]
    pts = [(ox, oy), (ox + w, oy)] + side + [(2 * ox + w - x, y) for x, y in side[::-1]]
    m = Image.new("L", lay.size, 0); ImageDraw.Draw(m).polygon(pts, fill=255)
    fill = Image.new("RGBA", lay.size, (0, 0, 0, 0)); fd = ImageDraw.Draw(fill)
    if kind == "saltire":
        fd.rectangle([0, 0, lay.width, lay.height], fill=(30, 70, 150, 255))
        bw = w * 0.17
        for (x0, y0, x1, y1) in [(ox, oy, ox + w, oy + h), (ox + w, oy, ox, oy + h)]:
            fd.line([(x0, y0), (x1, y1)], fill=IVORY + (255,), width=int(bw))
    else:                                                                      # quarterly (generic)
        fd.rectangle([0, 0, lay.width, lay.height], fill=RED + (255,))
        fd.rectangle([ox + w / 2, oy, ox + w + 30, oy + h * 0.5], fill=NAVY + (255,)); fd.rectangle([ox - 30, oy + h * 0.5, ox + w / 2, oy + h + 30], fill=NAVY + (255,))
        for (x, y) in [(ox + w * 0.25, oy + h * 0.25), (ox + w * 0.75, oy + h * 0.62)]:
            fd.polygon([(x, y - 34), (x + 26, y), (x, y + 34), (x - 26, y)], fill=GOLD + (255,))
        for (x, y) in [(ox + w * 0.75, oy + h * 0.25), (ox + w * 0.25, oy + h * 0.62)]:
            fd.ellipse([x - 26, y - 26, x + 26, y + 26], fill=IVORY + (255,))
    lay.paste(fill, (0, 0), m)
    d = ImageDraw.Draw(lay); d.line(pts + [pts[0]], fill=INK + (255,), width=16, joint="curve"); d.line(pts + [pts[0]], fill=GOLD + (255,), width=9, joint="curve")
    if a < 0.999: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    ac(img, lay, (cx - lay.width / 2, cy - h / 2 - 20))

def crown(img, cx, cy, w, a=1.0):
    d = ImageDraw.Draw(img, "RGBA"); h = w * 0.42; al = int(255 * a)
    base = [(cx - w / 2, cy + h * 0.25), (cx + w / 2, cy + h * 0.25), (cx + w / 2 * 0.92, cy + h * 0.55), (cx - w / 2 * 0.92, cy + h * 0.55)]
    pts = [(cx - w / 2, cy + h * 0.25)]
    for i in range(5):
        x = cx - w / 2 + w * i / 4
        pts += [(x - w * 0.05, cy + h * 0.1), (x, cy - h * (0.5 if i % 2 == 0 else 0.25)), (x + w * 0.05, cy + h * 0.1)]
    pts += [(cx + w / 2, cy + h * 0.25)]
    for p, c, wd in ((pts, GOLD, 0), (base, GOLD2, 0)):
        d.polygon(p, fill=c + (al,), outline=INK + (al,), width=6)
    for i in range(5):
        x = cx - w / 2 + w * i / 4; y = cy - h * (0.5 if i % 2 == 0 else 0.25); r = w * 0.045
        d.ellipse([x - r, y - r, x + r, y + r], fill=IVORY + (al,), outline=INK + (al,), width=4)
    for i in range(3):
        x = cx - w * 0.3 + i * w * 0.3; y = cy + h * 0.4; r = w * 0.04
        d.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], fill=RED + (al,))

def ribbon(img, s, cx, cy, size=86, col=RED, tcol=IVORY, a=1.0, scale=1.0, wave=0.0):
    f = F("cinb", size); tw = f.getlength(s); bw, bh = tw + 90, size * 1.45
    lay = Image.new("RGBA", (int(bw + 220), int(bh + 80)), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    x0, y0 = 110, 40; dark = tuple(int(c * 0.55) for c in col)
    for side in (-1, 1):                                                       # folded tails
        xe = x0 if side < 0 else x0 + bw
        tail = [(xe - side * 10, y0 + 24), (xe + side * 100, y0 + 24), (xe + side * 66, y0 + bh / 2 + 24), (xe + side * 100, y0 + bh + 24), (xe - side * 10, y0 + bh + 24)]
        d.polygon(tail, fill=dark + (255,), outline=INK + (255,), width=6)
    body = [(x0 + bw * p, y0 + wave * math.sin(p * 6.28)) for p in np.linspace(0, 1, 20)] + \
           [(x0 + bw * p, y0 + bh + wave * math.sin(p * 6.28)) for p in np.linspace(1, 0, 20)]
    d.polygon(body, fill=col + (255,), outline=INK + (255,), width=7)
    d.line([(x0 + 14, y0 + 12), (x0 + bw - 14, y0 + 12)], fill=GOLD + (200,), width=3)
    d.line([(x0 + 14, y0 + bh - 12), (x0 + bw - 14, y0 + bh - 12)], fill=GOLD + (200,), width=3)
    d.text((x0 + bw / 2, y0 + bh / 2 + 2), s, font=f, fill=tcol + (255,), anchor="mm", stroke_width=3, stroke_fill=INK + (255,))
    if abs(scale - 1) > 0.01: lay = lay.resize((max(1, int(lay.width * scale)), max(1, int(lay.height * scale))), Image.BILINEAR)
    if a < 0.999: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    ac(img, lay, (cx - lay.width / 2, cy - lay.height / 2))

_SP = {}
def sparkle(img, x, y, r, a):
    if a <= 0.02 or r < 2: return
    d = ImageDraw.Draw(img, "RGBA"); al = int(255 * a)
    d.polygon([(x, y - r), (x + r * 0.22, y - r * 0.22), (x + r, y), (x + r * 0.22, y + r * 0.22), (x, y + r), (x - r * 0.22, y + r * 0.22), (x - r, y), (x - r * 0.22, y - r * 0.22)], fill=(255, 238, 180, al))

def twinkles(img, pts, t, r=26):
    for i, (x, y) in enumerate(pts):
        ph = (t * 0.9 + i * 0.37) % 1.0; sparkle(img, x, y, r * math.sin(math.pi * ph), math.sin(math.pi * ph))

def coin(img, cx, cy, R, spin, a=1.0):
    """gold coin; spin in turns (0 = face-on). Face: embossed unicorn; reverse: cross fleury-ish saltire."""
    c = math.cos(spin * 2 * math.pi); sx = max(0.04, abs(c)); D = int(2 * R + 40)
    lay = Image.new("RGBA", (D, D), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); o = 20
    d.ellipse([o, o, o + 2 * R, o + 2 * R], fill=GOLD + (255,), outline=INK + (255,), width=10)
    d.ellipse([o + R * 0.1, o + R * 0.1, o + R * 1.9, o + R * 1.9], outline=GOLD2 + (255,), width=6)
    for k in range(48):
        q = k / 48 * 6.283; x, y = o + R + R * 0.86 * math.cos(q), o + R + R * 0.86 * math.sin(q); d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=GOLD2 + (255,))
    if c >= 0:
        sp = beast("unicorn", int(R * 1.25), False, False); m = sp.getchannel("A")
        sh = Image.new("RGBA", sp.size, GOLD2 + (255,)); hi = Image.new("RGBA", sp.size, (255, 226, 150, 255)); mid = Image.new("RGBA", sp.size, (236, 190, 90, 255))
        px, py = int(o + R - sp.width / 2), int(o + R - sp.height / 2 + R * 0.04)
        lay.paste(hi, (px - 4, py - 4), m); lay.paste(sh, (px + 5, py + 5), m); lay.paste(mid, (px, py), m)
    else:
        for (x0, y0, x1, y1) in [(o + R * 0.45, o + R * 0.45, o + R * 1.55, o + R * 1.55), (o + R * 1.55, o + R * 0.45, o + R * 0.45, o + R * 1.55)]:
            d.line([(x0, y0), (x1, y1)], fill=GOLD2 + (255,), width=int(R * 0.16)); d.line([(x0 - 4, y0 - 4), (x1 - 4, y1 - 4)], fill=(255, 226, 150, 255), width=4)
    if sx < 0.999: lay = lay.resize((max(2, int(D * sx)), D), Image.BILINEAR)
    if a < 0.999: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    ac(img, lay, (cx - lay.width / 2, cy - D / 2))

# ---------- scenes ----------
def wt(ln, k): return words[min(ln["_w0"] + k, ln["_w1"] - 1)][1] - ln["_s"]

def S_hook(img, sc, ln, lt, dur, t):
    put_text(img, "SCOTLAND'S", "cinb", 104, W / 2, 230, col=IVORY)
    put_text(img, "NATIONAL ANIMAL", "cinb", fit("NATIONAL ANIMAL", "cinb", 96, W - 200), W / 2, 345, col=IVORY)
    put_text(img, "A UNICORN.", "deco", fit("A UNICORN.", "deco", 150, W - 150), W / 2, 500)
    by = 1110 + 8 * math.sin(t * 2.0)
    put_beast(img, "unicorn", W / 2 + 20, by, 760, rot=1.5 * math.sin(t * 1.4))
    hx, hy = U2S(W / 2 + 20, by, 760, False, 13, -9)
    twinkles(img, [(hx, hy), (hx + 120, hy + 80), (W / 2 + 330, by - 140), (W / 2 - 310, by + 200)], t, 30)

def S_nots(img, sc, ln, lt, dur, t):
    put_beast(img, "unicorn", W / 2 + 150, 1230, 540, rot=1.2 * math.sin(t * 1.4))
    for i, (s, k, y) in enumerate([("NOT A LION.", 0, 330), ("NOT A STAG.", 3, 560)]):
        a, sc_ = slam(lt, wt(ln, k) - 0.06 if k else 0.0)
        ribbon(img, s, W / 2, y, 96, RED if i == 0 else NAVY, a=a, scale=sc_, wave=6 * math.sin(t * 3 + i))
    a, sc_ = slam(lt, wt(ln, 6) - 0.05)
    if a > 0:
        put_text(img, "WAIT FOR", "cinb", 64, W / 2 + 60, 760, a, col=IVORY, scale=sc_)
        put_text(img, "THE CHAINS…", "deco", 84, W / 2 + 60, 855, a, scale=sc_)
        u = eout((lt - wt(ln, 6)) / 0.6)
        chain(img, [(W / 2 + 60 - 300, 935), (W / 2 + 60 - 300 + 600 * u, 935)], t, sway=0, link=34)

def S_arms(img, sc, ln, lt, dur, t):
    put_text(img, "THE ROYAL", "cinb", 84, W / 2, 210, col=IVORY)
    put_text(img, "COAT OF ARMS", "deco", fit("COAT OF ARMS", "deco", 116), W / 2, 320)
    u = eout(lt / 0.45)
    put_beast(img, "unicorn", 250 - 400 * (1 - u), 980, 560, flip=True, rot=-1.5 * math.sin(t * 1.4))
    put_beast(img, "unicorn", 830 + 400 * (1 - u), 980, 560, flip=False, rot=1.5 * math.sin(t * 1.4))
    s = back(min(1, lt / 0.4)) if lt < 0.4 else 1.0
    shield(img, W / 2, 960, 380, "saltire", scale=max(0.05, s))
    v = eout((lt - 0.5) / 0.35)
    if v > 0: crown(img, W / 2, 640 - 80 * (1 - v), 300, v)
    ribbon(img, "SCOTLAND", W / 2, 1360, 62, RED, a=eout((lt - 0.8) / 0.3), wave=4 * math.sin(t * 3))

def S_coin(img, sc, ln, lt, dur, t):
    put_text(img, "A GOLD COIN", "cinb", 80, W / 2, 210, col=IVORY)
    put_text(img, "CALLED…", "cinb", 64, W / 2, 300, col=IVORY)
    k = wt(ln, 7)                                                              # "unicorn,"
    a, s_ = slam(lt, k - 0.05)
    put_text(img, "THE UNICORN", "deco", fit("THE UNICORN", "deco", 112), W / 2, 420, a, scale=s_)
    spin = 2.0 * (1 - eout(lt / 2.0))
    coin(img, W / 2, 870, 300, spin)
    twinkles(img, [(W / 2 + 220, 650), (W / 2 - 240, 1060), (W / 2 + 260, 1020)], t, 34)
    ky = wt(ln, 9)                                                             # "first struck"
    if lt > ky - 0.1:
        u = ease((lt - ky) / 1.0); yr = int(1400 + 84 * u)
        put_text(img, "FIRST STRUCK", "cinb", 50, W / 2, 1255, eout((lt - ky) / 0.3), col=IVORY)
        put_text(img, f"{yr}", "deco", 150, W / 2, 1385, eout((lt - ky) / 0.3))

def S_virtues(img, sc, ln, lt, dur, t):
    put_text(img, "IN CELTIC LEGEND", "cinb", fit("IN CELTIC LEGEND", "cinb", 76), W / 2, 200, col=IVORY)
    # medallion
    cx, cy, R = W / 2, 860, 380
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=DEEP + (255,), outline=INK + (255,), width=14)
    d.ellipse([cx - R + 8, cy - R + 8, cx + R - 8, cy + R - 8], outline=GOLD + (255,), width=8)
    for q in np.linspace(0, 6.283, 36, endpoint=False):                        # laurel-ish leaves
        x, y = cx + (R - 34) * math.cos(q), cy + (R - 34) * math.sin(q)
        d.ellipse([x - 12, y - 7, x + 12, y + 7], fill=GREEN + (255,))
    put_beast(img, "unicorn", cx + 10, cy + 20 + 6 * math.sin(t * 2), 560, rot=1.2 * math.sin(t * 1.4))
    for s, k, y, col in (("PURITY", 7, 1290, IVORY), ("POWER", 9, 1430, RED)):
        a, sc_ = slam(lt, wt(ln, k) - 0.06)
        ribbon(img, s, W / 2, y, 82, NAVY if col == IVORY else RED, tcol=IVORY if col == IVORY else GOLD, a=a, scale=sc_, wave=5 * math.sin(t * 3))

def S_chains(img, sc, ln, lt, dur, t):
    k2 = wt(ln, 5)
    by = 1050; size = 700
    put_beast(img, "unicorn", W / 2 + 70, by, size, collar=True)
    cx, cy = U2S(W / 2 + 70, by, size, False, 45, 29)
    u = eout(lt / 0.9)
    chain(img, [(cx, cy), (cx - 90, cy + 220), (cx - 260, cy + 430), (130, 1480)], t, sway=24, reveal=u, link=30)
    d = ImageDraw.Draw(img, "RGBA"); d.ellipse([90, 1440, 170, 1520], outline=INK + (255,), width=14); d.ellipse([90, 1440, 170, 1520], outline=GOLD + (255,), width=8)
    if lt < k2 + 0.1:
        a, s_ = slam(lt, 0.0)
        put_text(img, "WHY THE", "cinb", 90, W / 2, 230, col=IVORY)
        put_text(img, "CHAINS?", "deco", 150, W / 2, 370, a, scale=s_)
    else:
        v = lt - k2
        crown(img, W / 2, 200, 230, eout(v / 0.3))
        a, s_ = slam(v, 0.05)
        put_text(img, "ONLY A KING", "deco", fit("ONLY A KING", "deco", 116), W / 2, 360, a, scale=s_)
        a, s_ = slam(v, 0.35)
        put_text(img, "COULD TAME IT", "cinb", fit("COULD TAME IT", "cinb", 92), W / 2, 480, a, col=IVORY, scale=s_)
        twinkles(img, [(cx, cy), (cx - 180, cy + 330), (cx + 120, cy - 60)], t, 30)

def S_lion(img, sc, ln, lt, dur, t):
    u = ease(lt / 0.9); yr = int(1484 + (1603 - 1484) * u)
    put_text(img, "SINCE", "cinb", 64, W / 2, 190, col=IVORY)
    put_text(img, f"{yr}", "deco", 160, W / 2, 320)
    kl = wt(ln, 7) - 0.35                                                      # "English lion"
    v = eout((lt - kl) / 0.5)
    put_beast(img, "unicorn", 860, 970, 500, flip=False, rot=1.5 * math.sin(t * 1.4))
    if v > 0: put_beast(img, "lion", 225 - 500 * (1 - v), 970, 500, flip=True, rot=-1.5 * math.sin(t * 1.4))
    shield(img, W / 2, 980, 320, "quarterly")
    crown(img, W / 2, 700, 240)
    put_text(img, "LION", "cinb", 64, 220, 1330, v, col=GOLD)
    put_text(img, "+", "deco", 80, W / 2, 1330, v, col=IVORY)
    put_text(img, "UNICORN", "cinb", 64, 850, 1330, 1.0, col=IVORY)

def S_end(img, sc, ln, lt, dur, t):
    put_text(img, "SOUNDS FAKE?", "deco", fit("SOUNDS FAKE?", "deco", 120), W / 2, 220)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.35)
    y = 450; x0, x1 = 210, 870
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([x0 - 14, y - 104, x1 + 14, y + 104], 104, fill=INK + (255,))
    d.rounded_rectangle([x0, y - 90, x1, y + 90], 90, fill=DEEP + (255,), outline=GOLD + (255,), width=6)
    if on > 0: d.rounded_rectangle([x0, y - 90, x0 + (x1 - x0) * (0.25 + 0.75 * on), y + 90], 90, fill=(int(DEEP[0] + (GOLD2[0] - DEEP[0]) * on), int(DEEP[1] + (GOLD2[1] - DEEP[1]) * on), int(DEEP[2] + (GOLD2[2] - DEEP[2]) * on), 255))
    for xx in range(x0 + 60, x1 - 50, 26): d.line([(xx, y - 74), (xx + 12, y - 74)], fill=GOLD + (160,), width=3); d.line([(xx, y + 74), (xx + 12, y + 74)], fill=GOLD + (160,), width=3)
    put_text(img, "FAKE", "cinb", 64, 680, y, 1 - on, col=IVORY)
    put_text(img, "TRUE", "cinb", 64, 400, y, on, col=IVORY)
    kx = 300 + (780 - 300) * on
    coin(img, kx, y, 82, 0.0)
    if on > 0.6:
        w_ = eout((lt - click - 0.25) / 0.35)
        ribbon(img, "IT'S TRUE.", W / 2, 680, 92, RED, tcol=GOLD, a=w_, scale=0.6 + 0.4 * back(min(1, w_)))
        put_text(img, "Follow for more.", "cin", 60, W / 2, 815, eout((lt - click - 0.45) / 0.35), col=IVORY)
    by = 1235 + 8 * math.sin(t * 2.0)
    put_beast(img, "unicorn", W / 2 + 20, by, 580, collar=on > 0.5, rot=1.5 * math.sin(t * 1.4))
    hx, hy = U2S(W / 2 + 20, by, 580, False, 13, -9)
    twinkles(img, [(hx, hy), (W / 2 + 300, by - 100), (W / 2 - 280, by + 160)], t, 30)

SCENES = dict(hook=S_hook, nots=S_nots, arms=S_arms, coin=S_coin, virtues=S_virtues, chains=S_chains, lion=S_lion, end=S_end)

# ---------- audio: reed drone + tin whistle jig + frame drum ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.22, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32); tt = np.arange(n) / SR
drone = sum(np.sin(2 * np.pi * f * h * tt) / h ** 1.2 for f in (110.0, 164.81) for h in (1, 2, 3, 4, 5))
drone *= (1 + 0.04 * np.sin(2 * np.pi * 5.2 * tt))
music += (drone / 6).astype(np.float32) * 0.09
A_MIX = {"A4": 440.0, "B4": 493.88, "C#5": 554.37, "D5": 587.33, "E5": 659.25, "F#5": 739.99, "G5": 783.99, "A5": 880.0, "G4": 392.0}
jig = ["A4", "C#5", "E5", "A5", "E5", "C#5", "D5", "F#5", "A5", "F#5", "E5", "D5", "C#5", "E5", "A5", "E5", "C#5", "A4",
       "G4", "B4", "D5", "G5", "D5", "B4"]
ST = 0.19
def whistle(f, dur):
    s = np.arange(int(dur * SR)) / SR; env = np.minimum(1, s / 0.015) * np.exp(-s * 2.5)
    sig = (np.sin(2 * np.pi * f * s + 0.25 * np.sin(2 * np.pi * 5.5 * s)) + 0.15 * np.sin(4 * np.pi * f * s)) * env
    sig += np.random.default_rng(int(f)).normal(0, 0.03, len(s)) * env
    return sig.astype(np.float32)
for k in range(int(total / ST)):
    place(music, 0.05 + k * ST, whistle(A_MIX[jig[k % len(jig)]], ST * 1.3), 0.05)
def drum(at, gain):
    s = np.arange(int(0.35 * SR)) / SR
    sig = np.sin(2 * np.pi * (70 + 50 * np.exp(-s * 30)) * s) * np.exp(-s * 12) + np.random.default_rng(1).normal(0, 0.2, len(s)) * np.exp(-s * 60)
    place(music, at, sig.astype(np.float32), gain)
for k in range(int(total / (ST * 3))): drum(0.05 + k * ST * 3, 0.16 if k % 2 == 0 else 0.1)
hook_hit(music, 0.33)
for s_ in scene_starts(spec): whoosh(music, s_, 0.09)
for ln in spec["lines"]:
    if ln["scene"]["type"] == "end":
        place(music, ln["_s"] + ln["scene"].get("click_at", 0.45), tone(880.0, 1.6, decay=3, harm=(1, 2, 3, 4.2)), 0.14)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.4)

# ---------- compose ----------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 74
    while F("bold", size).getlength(" ".join(ws)) > W - 240 and size > 36: size -= 4
    f = F("bold", size); tw = f.getlength(" ".join(ws)); x = (W - tw) / 2; y = 1590
    d = ImageDraw.Draw(img, "RGBA")
    box = [x - 40, y - 24, x + tw + 40, y + size + 30]
    d.rounded_rectangle([box[0] - 6, box[1] - 6, box[2] + 6, box[3] + 6], 22, fill=INK + (255,))
    d.rounded_rectangle(box, 18, fill=DEEP + (245,))
    for xx in np.arange(box[0] + 18, box[2] - 18, 22):                           # stitched gold border
        d.line([(xx, box[1] + 9), (xx + 11, box[1] + 9)], fill=GOLD + (255,), width=3); d.line([(xx, box[3] - 9), (xx + 11, box[3] - 9)], fill=GOLD + (255,), width=3)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=(255, 205, 90, 255) if on else (255, 255, 255, 255)); x += f.getlength(w + " ")

THREADS = [GOLD, NAVY, RED, IVORY, DEEP, GOLD2]
def loom(img, lt):
    """scene change: thread bands slide out to alternating sides."""
    if lt >= 0.32: return
    d = ImageDraw.Draw(img); bh = 40
    for k in range(H // bh + 1):
        delay = 0.012 * (k % 7); u = eout((lt - delay) / 0.24)
        if u >= 1: continue
        cover = W * (1 - u); col = THREADS[k % len(THREADS)]
        if k % 2: d.rectangle([0, k * bh, cover, k * bh + bh], fill=col)
        else: d.rectangle([W - cover, k * bh, W, k * bh + bh], fill=col)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    typ = ln["scene"]["type"]; img = FIELD.copy()
    SCENES[typ](img, ln["scene"], ln, lt, dur, t)
    li = spec["lines"].index(ln)
    if li > 0 and spec["lines"][li - 1]["scene"]["type"] != typ: loom(img, lt)
    arr = np.asarray(img.convert("RGB")).astype(np.float32) * WEAVE
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")
    caption(img, t)
    d = ImageDraw.Draw(img); d.rectangle([0, H - 10, W, H], fill=INK); d.rectangle([0, H - 10, int(W * t / total), H], fill=GOLD)
    return img.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=26); print(f"done {total:.1f}s")
