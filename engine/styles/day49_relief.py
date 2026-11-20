"""Day 49 — STONE RELIEF style (the Great Pyramid was the tallest building on Earth for ~3,800 years).
The whole frame is one sandstone slab under a low, raking sun. Nothing is 'drawn': every element is a height field —
sunken relief for inscriptions (Egyptian-style cut-in type), raised relief for the pyramid, the cathedral and the sun disc —
and each frame is relit: surface normals from the height map, Lambert shading against a low light, and real cast shadows
(height-field ray march along the light direction). Sandstone albedo has warped bedding strata, speckle and pits; a
carved border frames the slab. Key words keep traces of ancient pigment (gold, Egyptian blue, red ochre) inside the cuts.
Motion language: everything appears by a chisel wipe (left-to-right for type, bottom-up course by course for buildings)
with sand chips spraying from the cutting front and chisel taps in the audio; numbers slam in; the light azimuth drifts
all video and dips low on every scene change (shadows stretch) with a puff of dust and a whoosh.
Type: Cinzel (inscriptional Roman caps, tracked) for carvings; captions on a polished basalt tablet in Inter Bold.
Ending: a carved slider groove with a raised cartouche knob that slides FAKE -> TRUE, back on the hook's pyramid (loop).
Music: original D-Hijaz drone + Karplus-Strong plucked-string melody + frame-drum doum/tek, chisel taps synced to carving.
Usage: python3 engine/styles/day49_relief.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageFilter
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
INTER = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter")
_F = {}
def F(kind, s, wt=800):
    k = (kind, int(s), wt)
    if k not in _F:
        if kind == "cin":
            f = ImageFont.truetype(f"{FONTS}/Cinzel[wght].ttf", int(s))
            try: f.set_variation_by_axes([wt])
            except Exception: pass
            _F[k] = f
        else: _F[k] = ImageFont.truetype(f"{INTER}/Inter-Bold.otf", int(s))
    return _F[k]

GOLD, BLUE, RED, TURQ = (226, 168, 52), (38, 84, 168), (176, 58, 34), (34, 140, 138)
BASALT = (30, 27, 25)

# ---------- the slab (built once) ----------
def fbm(seed, scales, amps, size=(W, H)):
    rr = np.random.default_rng(seed); acc = np.zeros((size[1], size[0]), np.float32)
    for s, a in zip(scales, amps):
        g = rr.random((max(2, size[1] // s + 2), max(2, size[0] // s + 2))).astype(np.float32)
        acc += a * cv2.resize(g, size, interpolation=cv2.INTER_CUBIC)
    acc -= acc.min(); return acc / max(1e-6, acc.max())

def _slab():
    h = fbm(11, [400, 160, 60, 20, 7, 3], [1, .55, .3, .16, .08, .05]) * 3.2
    rr = np.random.default_rng(12)
    pits = np.zeros((H, W), np.float32)
    for _ in range(380):
        x, y, r = rr.integers(0, W), rr.integers(0, H), rr.uniform(1, 3.5)
        cv2.circle(pits, (int(x), int(y)), int(r), 1.0, -1)
    h -= cv2.GaussianBlur(pits, (0, 0), 1.2) * 1.3
    # carved border + inner fillet
    fr = np.zeros((H, W), np.float32)
    cv2.rectangle(fr, (34, 34), (W - 35, H - 35), 1.0, 7)
    cv2.rectangle(fr, (52, 52), (W - 53, H - 53), 0.5, 3)
    for x in range(80, W - 80, 64):                               # register band of little carved pyramids
        cv2.fillPoly(fr, [np.array([[x, 1830], [x + 26, 1790], [x + 52, 1830]], np.int32)], 0.8)
    cv2.line(fr, (70, 1770), (W - 70, 1770), 0.8, 4); cv2.line(fr, (70, 1846), (W - 70, 1846), 0.8, 4)
    h -= cv2.GaussianBlur(fr, (0, 0), 2.0) * 9
    # albedo: warped bedding strata
    yy = np.arange(H, dtype=np.float32)[:, None]
    warp = fbm(13, [500, 200, 80], [1, .4, .15]) * 90
    band = 0.5 * np.sin((yy + warp) / 41.0) + 0.3 * np.sin((yy + warp * 1.3) / 13.7 + 1) + 0.2 * np.sin((yy + warp) / 5.1)
    tone_ = fbm(14, [600, 240, 90, 30], [1, .6, .3, .15])
    light, dark = np.array([226, 190, 138], np.float32), np.array([178, 132, 86], np.float32)
    k = np.clip(0.55 * tone_ + 0.22 * band + 0.25, 0, 1)
    alb = dark + (light - dark) * k[..., None]
    speck = rr.random((H, W)).astype(np.float32)
    alb *= (1 - 0.18 * (speck > 0.985))[..., None]
    alb *= (1 + 0.05 * (speck < 0.01))[..., None]
    rust = fbm(15, [300, 90], [1, .4])
    alb = alb * (1 - 0.12 * np.clip(rust - 0.6, 0, 1)[..., None] * np.array([0, .5, 1.0], np.float32))
    return h.astype(np.float32), alb.astype(np.float32)
BASEH, ALB = _slab()
PGRAIN = (0.55 + 0.45 * fbm(16, [40, 12, 4, 2], [1, .7, .5, .4])).astype(np.float32)   # weathered pigment
yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.32 * (((xx_ - W / 2) / (W * 0.75)) ** 2 + ((yy_ - H * 0.45) / (H * 0.7)) ** 2)).clip(0.55, 1)[..., None]

# ---------- sprites ----------
_SP = {}
def tsprite(s, size, wt=800, track=0.08):
    k = ("t", s, int(size), wt, track)
    if k not in _SP:
        f = F("cin", size, wt); pad = int(size * 0.3)
        widths = [f.getlength(c) + (track * size if c != " " else 0) for c in s]
        im = Image.new("L", (int(sum(widths)) + 2 * pad, int(size * 1.5) + 2 * pad), 0); d = ImageDraw.Draw(im)
        x = pad
        for c, w in zip(s, widths): d.text((x, pad), c, font=f, fill=255); x += w
        _SP[k] = im.crop(im.getbbox())
    return _SP[k]

def text_w(s, size, wt=800, track=0.08): return tsprite(s, size, wt, track).size[0]
def fit(s, size, maxw=W - 180, wt=800):
    while text_w(s, size, wt) > maxw and size > 40: size -= 6
    return size

def shape(key, w, h, fn):
    k = ("s", key, int(w), int(h))
    if k not in _SP:
        im = Image.new("L", (int(w), int(h)), 0); fn(ImageDraw.Draw(im), int(w), int(h)); _SP[k] = im
    return _SP[k]

class Frame:
    def __init__(self):
        self.cut = Image.new("L", (W, H), 0); self.rise = Image.new("L", (W, H), 0)
        self.paint = Image.new("RGBA", (W, H), (0, 0, 0, 0)); self.emit = []; self.puffs = []

def _wipe(sp, u, dir_):
    if u >= 1: return sp
    w_, h_ = sp.size
    if dir_ == "lr":
        cut = u * (w_ + 40) - 20
        ramp = np.clip((cut - np.arange(w_, dtype=np.float32))[None, :] / 18 + np.random.default_rng(1).normal(0, .3, (h_, 1)), 0, 1)
        front = (cut, None)
    else:                                                       # bottom-up
        cut = u * (h_ + 40) - 20
        ramp = np.clip((cut - (h_ - 1 - np.arange(h_, dtype=np.float32)))[:, None] / 14, 0, 1) * np.ones((1, w_), np.float32)
        front = (None, h_ - cut)
    a = (np.asarray(sp).astype(np.float32) * ramp).astype(np.uint8)
    return Image.fromarray(a), front

def stamp(fr, sp, cx, cy, mode="cut", u=1.0, dir_="lr", scale=1.0, value=255, paint=None, palpha=0.85, anchor="c", emit=True):
    """press a sprite into the cut (sunken) or rise (raised) map at (cx,cy); u<1 = chisel wipe with dust."""
    if u <= 0: return None
    if abs(scale - 1) > 0.01: sp = sp.resize((max(1, int(sp.size[0] * scale)), max(1, int(sp.size[1] * scale))), Image.BILINEAR)
    front = None
    if u < 1: sp, front = _wipe(sp, u, dir_)
    if value < 255: sp = sp.point(lambda v: v * value // 255)
    x0 = int(cx - sp.size[0] / 2); y0 = int(cy - sp.size[1] / 2) if anchor == "c" else int(cy - sp.size[1])
    tgt = fr.cut if mode == "cut" else fr.rise
    box = (x0, y0, x0 + sp.size[0], y0 + sp.size[1])
    tgt.paste(ImageChops.lighter(tgt.crop(box), sp), box)
    if paint:
        m = sp.filter(ImageFilter.MinFilter(3)) if mode == "cut" else sp
        m = m.point(lambda v: int(v * palpha))
        fr.paint.paste(Image.new("RGBA", sp.size, paint + (255,)), box, m)
    if front is not None and emit:
        if front[0] is not None: fr.emit.append((x0 + front[0], y0, y0 + sp.size[1]))
        else: fr.emit.append((x0 + sp.size[0] / 2 + (random.random() - .5) * sp.size[0] * 0.5, y0 + front[1] - 4, y0 + front[1] + 4))
    return box

# --- shapes ---
def _pyr(d, w, h):
    d.polygon([(0, h - 1), (w / 2, 0), (w - 1, h - 1)], fill=255)
    d.polygon([(w / 2, 0), (w - 1, h - 1), (w * 0.62, h - 1)], fill=212)            # shaded east face (lower plane)
    rows = 11
    for i in range(1, rows):
        y = h * i / rows; half = w / 2 * y / h
        d.line([(w / 2 - half + 3, y), (w / 2 + half - 3, y)], fill=150, width=3)
def pyramid(fr, cx, by, w, u=1.0, paint=True):
    h = w * 0.62; sp = shape("pyr", w, h, _pyr)
    stamp(fr, sp, cx, by, "rise", u, "bu", anchor="b", paint=GOLD if paint else None, palpha=0.42)

def _sun(d, w, h):
    r = w / 2; d.ellipse([w * .18, h * .18, w * .82, h * .82], fill=255)
    d.ellipse([w * .26, h * .26, w * .74, h * .74], fill=205)
def sun(fr, cx, cy, r, u=1.0):
    sp = shape("sun", r * 2, r * 2, _sun); stamp(fr, sp, cx, cy, "rise", u, "bu", paint=RED, palpha=0.55)
    if u >= 1:
        for k in range(12):
            a = k * math.pi / 6
            ImageDraw.Draw(fr.cut).line([(cx + r * 0.95 * math.cos(a), cy + r * 0.95 * math.sin(a)),
                                         (cx + r * 1.35 * math.cos(a), cy + r * 1.35 * math.sin(a))], fill=255, width=7)

def _cath_body(d, w, h):
    # west towers, nave, central tower (no spire); h is total incl. spire area, body drawn in lower part
    g = h * 0.62                                                 # ground-to-tower-top fraction measured from bottom
    base = h - 1
    d.rectangle([w * .02, base - h * .30, w * .98, base], fill=255)                    # nave + aisles
    d.polygon([(w * .02, base - h * .30), (w * .5, base - h * .36), (w * .98, base - h * .30)], fill=255)  # roof
    d.rectangle([w * .02, base - h * .42, w * .16, base], fill=255)                    # west towers
    d.rectangle([w * .84, base - h * .40, w * .98, base], fill=255)
    for x in (w * .02, w * .16 - 14, w * .84, w * .98 - 14):
        top = base - (h * .42 if x < w / 2 else h * .40)
        d.polygon([(x, top), (x + 7, top - 26), (x + 14, top)], fill=255)
    d.rectangle([w * .40, base - h * .55, w * .60, base], fill=255)                    # central tower
    for i in range(8):                                                                   # pointed windows (grooves)
        x = w * .2 + i * w * .085
        if w * .38 < x < w * .6: continue
        d.rectangle([x, base - h * .2, x + w * .035, base - h * .06], fill=140)
        d.polygon([(x, base - h * .2), (x + w * .0175, base - h * .24), (x + w * .035, base - h * .2)], fill=140)
    for i in range(2):
        x = w * .44 + i * w * .07
        d.rectangle([x, base - h * .5, x + w * .04, base - h * .4], fill=140)
def _spire(d, w, h): d.polygon([(0, h - 1), (w / 2, 0), (w - 1, h - 1)], fill=255); d.polygon([(w / 2, 0), (w - 1, h - 1), (w * .55, h - 1)], fill=215)

def cathedral(fr, cx, by, w, u=1.0, spire=True, spire_u=1.0, paint=BLUE):
    h = w * 1.25
    stamp(fr, shape("cath", w, h, _cath_body), cx, by, "rise", u, "bu", anchor="b", paint=paint, palpha=0.28)
    sw, sh = w * .2, h * .45
    if spire and spire_u > 0:
        stamp(fr, shape("spire", sw, sh, _spire), cx, by - h * .55 + 2, "rise", spire_u, "bu", anchor="b", paint=paint, palpha=0.28)
    return h

def _obel(d, w, h): d.polygon([(w * .2, h - 1), (w * .3, h * .1), (w / 2, 0), (w * .7, h * .1), (w * .8, h - 1)], fill=255)
def _col(d, w, h):
    d.rectangle([w * .25, h * .1, w * .75, h - 1], fill=255); d.rectangle([0, 0, w - 1, h * .1], fill=255)
    for i in range(3): d.line([(w * (.35 + .15 * i), h * .14), (w * (.35 + .15 * i), h - 6)], fill=160, width=4)
def _tower(d, w, h):
    d.rectangle([w * .1, h * .12, w * .9, h - 1], fill=255)
    for i in range(4): d.rectangle([w * (.1 + .22 * i), 0, w * (.1 + .22 * i + .14), h * .13], fill=255)
    d.rectangle([w * .42, h * .3, w * .58, h * .42], fill=140)
def _dome(d, w, h):
    d.rectangle([0, h * .55, w - 1, h - 1], fill=255); d.pieslice([w * .12, h * .1, w * .88, h], 180, 360, fill=255)
    d.rectangle([w * .47, 0, w * .53, h * .15], fill=255)
def _light(d, w, h):
    d.rectangle([w * .1, h * .55, w * .9, h - 1], fill=255); d.rectangle([w * .25, h * .22, w * .75, h * .55], fill=255)
    d.rectangle([w * .38, 0, w * .62, h * .22], fill=255)

# ---------- text helpers ----------
def carve(fr, s, size, x, y, u=1.0, paint=None, wt=800, scale=1.0, mode="cut", track=0.08, palpha=0.85):
    return stamp(fr, tsprite(s, size, wt, track), x, y, mode, u, "lr", scale, paint=paint, palpha=palpha)

def slam(lt, at, d=0.26):
    u = (lt - at) / d
    return (0, 1) if u <= 0 else (1, 1 + 0.4 * (1 - back(min(1, u))) if u < 1 else 1)

def wt_(ln, i): return words[ln["_w0"] + min(i, ln["_w1"] - ln["_w0"] - 1)][1] - ln["_s"]
def cw(lt, at, dur=0.45): return ease((lt - at) / dur)

def ground(fr, y, x0=90, x1=W - 90, u=1.0):
    if u <= 0: return
    ImageDraw.Draw(fr.cut).line([(x0, y), (x0 + (x1 - x0) * u, y)], fill=255, width=8)

# ---------- scenes ----------
HOOK_PYR = (W / 2, 1405, 780)
def S_hook(fr, sc, ln, lt, dur, t):
    pyramid(fr, *HOOK_PYR)
    ground(fr, 1418)
    sun(fr, 880, 860, 54)
    if not sc.get("loop"):
        carve(fr, "TALLEST ON EARTH", fit("TALLEST ON EARTH", 104), W / 2, 250, paint=BLUE)
        carve(fr, "3,800", fit("3,800", 290, W - 220, 900), W / 2, 470, paint=GOLD, wt=900)
        carve(fr, "YEARS", 128, W / 2, 665, paint=RED)
    else:
        a, s_ = slam(lt, 0.0)
        carve(fr, "WHAT", 170, W / 2, 300, paint=BLUE, scale=s_, wt=900)
        a, s_ = slam(lt, max(0.35, wt_(ln, 2) - 0.1))
        if a: carve(fr, "BEAT IT?", fit("BEAT IT?", 190), W / 2, 520, paint=GOLD, scale=s_, wt=900)

def ruler(fr, x, by, top, u, marks=6):
    d = ImageDraw.Draw(fr.cut); y1 = by - (by - top) * u
    d.line([(x, by), (x, y1)], fill=255, width=7)
    for i in range(marks + 1):
        y = by - (by - top) * i / marks
        if y >= y1 - 1: d.line([(x - 22, y), (x + 22, y)], fill=255, width=6)
    return y1

def S_build(fr, sc, ln, lt, dur, t):
    k_y = wt_(ln, 2)                                                     # "4,500"
    carve(fr, "4,500", 230, W / 2, 300, u=cw(lt, max(0.0, k_y - 0.35), 0.4), paint=GOLD, wt=900)
    carve(fr, "YEARS AGO", 104, W / 2, 470, u=cw(lt, k_y + 0.2, 0.4), paint=BLUE)
    k_m = wt_(ln, 9)                                                     # "146"
    grow = ease(lt / max(1.0, k_m - 0.1))
    pyramid(fr, W / 2 - 60, 1405, 680, u=max(0.02, grow))
    ground(fr, 1418)
    top = 1405 - 680 * 0.62
    y1 = ruler(fr, 960, 1405, top, grow)
    a, s_ = slam(lt, k_m - 0.08)
    if a:
        carve(fr, "146 M", 130, W / 2 + 40, 690, paint=RED, scale=s_, wt=900)
        ImageDraw.Draw(fr.cut).line([(W / 2 - 60, top - 18), (990, top - 18)], fill=255, width=5)

STRUCT = [("obel", _obel, 60, 205, 520, 0.18), ("col", _col, 80, 160, 612, 0.36),
          ("tower", _tower, 110, 195, 722, 0.54), ("dome", _dome, 150, 140, 862, 0.72)]
def S_ages(fr, sc, ln, lt, dur, t):
    pyr_w = 420; by = 1405; top = by - pyr_w * 0.62
    pyramid(fr, 275, by, pyr_w)
    ground(fr, 1418)
    d = ImageDraw.Draw(fr.cut)
    for x in range(480, 990, 46): d.line([(x, top), (x + 24, top)], fill=255, width=6)   # record line
    carve(fr, "146 M", 64, 275, top - 60, paint=RED)
    yr = int(-2560 + (1300 + 2560) * ease(lt / max(1, dur - 0.3)))
    yr = round(yr / 10) * 10
    s = f"{-yr} BC" if yr < 0 else f"{max(yr, 1)} AD"
    carve(fr, s, 170, W / 2, 420, paint=GOLD, wt=900)
    k_n = wt_(ln, 8)                                                    # "nothing"
    carve(fr, "NOTHING TALLER", fit("NOTHING TALLER", 100), W / 2, 620, u=cw(lt, k_n - 0.15, 0.45), paint=BLUE)
    for i, (key, fn, w, h, x, at) in enumerate(STRUCT):
        u = ease((lt - at * dur * 0.8) / 0.5)
        stamp(fr, shape(key, w, h, fn), x, by, "rise", u, "bu", anchor="b", paint=TURQ if i % 2 else GOLD, palpha=0.3)

def S_spire(fr, sc, ln, lt, dur, t):
    k = wt_(ln, 3) - 0.1                                                # "1311"
    a, s_ = slam(lt, max(0.0, k))
    if a: carve(fr, "1311", 230, W / 2, 400, paint=GOLD, scale=s_, wt=900)
    pw = 440; by = 1405; ptop = by - pw * 0.62
    pyramid(fr, 270, by, pw)
    ground(fr, 1418)
    cw_ = 360; ch = cw_ * 1.25; ccx = 790
    u_b = ease((lt - 0.2) / 1.0)
    cathedral(fr, ccx, by, cw_, u=u_b, spire_u=ease((lt - 1.1) / 0.9))
    ctop = by - ch * .55 - ch * .45
    d = ImageDraw.Draw(fr.cut)
    for x in range(110, 1000, 46): d.line([(x, ptop), (x + 24, ptop)], fill=255, width=6)
    carve(fr, "146 M", 62, 270, ptop - 60, paint=RED)
    k_b = wt_(ln, 10) - 0.2                                             # "beat"
    v = cw(lt, k_b, 0.4)
    if v > 0:
        carve(fr, "~160 M", 62, ccx, ctop - 52, u=v, paint=GOLD)
        carve(fr, "ENGLAND", 90, W / 2, 610, u=cw(lt, k_b + 0.15, 0.4), paint=BLUE)

SPIRE_FALL = {}
def S_storm(fr, sc, ln, lt, dur, t):
    k = wt_(ln, 4) - 0.05                                               # "knocked"
    k_y = wt_(ln, 8) - 0.1                                              # "1548"
    by = 1405; cw_ = 400; ccx = W / 2 + 20; ch = cw_ * 1.25
    ground(fr, 1418)
    cathedral(fr, ccx, by, cw_, spire=False)
    sw, sh = cw_ * .2, ch * .45; sbase = by - ch * .55 + 2
    sp = shape("spire", sw, sh, _spire)
    ft = lt - k
    if ft < 0:
        wob = 2.5 * math.sin(lt * 9) * min(1, lt / 1.0)
        spr = sp.rotate(wob, expand=True, resample=Image.BICUBIC)
        stamp(fr, spr, ccx + wob * 2, sbase - sh / 2, "rise", paint=BLUE, palpha=0.28)
    else:
        ang = min(100.0, 60 * ft * ft + 20 * ft)                       # tips over to the right, falls
        drop = min(sh * 0.5 + 80 * 1.0, 900 * ft * ft)
        cx = ccx + sh * 0.5 * math.sin(math.radians(ang)) + 120 * ft
        cy = sbase - sh / 2 * math.cos(math.radians(ang)) + drop
        if cy < by - sw * 0.6:
            spr = sp.rotate(-ang, expand=True, resample=Image.BICUBIC)
            stamp(fr, spr, cx, cy, "rise", paint=BLUE, palpha=0.28)
        else:
            if not SPIRE_FALL.get("hit"): SPIRE_FALL["hit"] = lt
            r = random.Random(7)
            for i in range(7):                                              # rubble
                x = cx - 110 + i * 34 + r.uniform(-8, 8); s = r.uniform(24, 44)
                ImageDraw.Draw(fr.rise).polygon([(x, by), (x + s * .2, by - s * r.uniform(.5, 1)), (x + s * .8, by - s * r.uniform(.4, .9)), (x + s, by)], fill=230)
            fr.puffs.append((cx, by - 20, lt - SPIRE_FALL["hit"]))
    # wind grooves streaming in from the left
    d = ImageDraw.Draw(fr.cut)
    for i in range(5):
        y = 640 + i * 70 + 20 * math.sin(i * 1.7)
        off = (t * 520 + i * 260) % 1400 - 400
        pts = [(x, y + 18 * math.sin(x / 90 + i)) for x in range(int(off), int(off) + 360, 12) if 70 < x < W - 70]
        if len(pts) > 2: d.line(pts, fill=200, width=7)
    a, s_ = slam(lt, max(0.0, k_y))
    carve(fr, "STORM", 170, W / 2, 330, u=cw(lt, 0.0, 0.35), paint=BLUE, wt=900)
    if a: carve(fr, "1548", 170, W / 2, 520, paint=GOLD, scale=s_, wt=900)

def S_stand(fr, sc, ln, lt, dur, t):
    pyramid(fr, *HOOK_PYR)
    ground(fr, 1418)
    sun(fr, 880, 860 + 120 * (1 - eout(lt / 1.2)), 54)
    a, s_ = slam(lt, 0.0)
    carve(fr, "STILL", 200, W / 2, 290, paint=GOLD, scale=s_, wt=900)
    k = wt_(ln, 2) - 0.1
    a, s_ = slam(lt, max(0.3, k))
    if a: carve(fr, "STANDING", fit("STANDING", 170), W / 2, 500, paint=BLUE, scale=s_, wt=900)

def _track(d, w, h): d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=255)
def _cart(d, w, h):
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=255)
    d.rounded_rectangle([12, 12, w - 13, h - 13], radius=h // 2 - 12, fill=200)
    d.line([(w - 6, 14), (w - 6, h - 14)], fill=255, width=10)
def S_end(fr, sc, ln, lt, dur, t):
    pyramid(fr, *HOOK_PYR)
    ground(fr, 1418)
    sun(fr, 880, 860, 54)
    carve(fr, "SOUNDS FAKE?", fit("SOUNDS FAKE?", 130), W / 2, 200, paint=BLUE)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.4)
    y = 390; x0, x1 = 230, 850
    stamp(fr, shape("track", x1 - x0 + 120, 112, _track), (x0 + x1) / 2, y, "cut")
    if on > 0:                                                          # pigment fills the groove behind the knob
        fx = x0 - 50 + (x1 - x0 + 100) * on
        m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rounded_rectangle([x0 - 56, y - 52, fx, y + 52], radius=52, fill=int(220 * min(1, on * 2)))
        fr.paint.paste(Image.new("RGBA", (W, H), TURQ + (255,)), (0, 0), m)
    kx = x0 + 10 + (x1 - x0 - 20) * on
    stamp(fr, shape("cart", 150, 88, _cart), kx, y, "rise", paint=GOLD, palpha=0.45)
    carve(fr, "FAKE", 70, x0 + 10, y + 110, paint=RED if on < 0.5 else None)
    carve(fr, "TRUE", 70 if on < 0.5 else 84, x1 - 10, y + 110, paint=GOLD if on >= 0.5 else None, wt=900 if on >= .5 else 800)
    if on > 0.6:
        w_ = eout((lt - click - 0.25) / 0.3)
        if w_ > 0: carve(fr, "IT'S TRUE.", fit("IT'S TRUE.", 150), W / 2, 615, paint=GOLD, wt=900, scale=0.65 + 0.35 * back(min(1, w_)))
        carve(fr, "FOLLOW FOR MORE", fit("FOLLOW FOR MORE", 70), W / 2, 735, u=cw(lt, click + 0.45, 0.35), paint=BLUE)

SCENES = dict(hook=S_hook, build=S_build, ages=S_ages, spire=S_spire, storm=S_storm, stand=S_stand, end=S_end)

# ---------- narration + timing ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.22, tail=0.6)
STARTS = [ln["_s"] for ln in spec["lines"]]
CHANGE = [ln["_s"] for i, ln in enumerate(spec["lines"]) if i > 0]

def scene_frame(t):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    fr = Frame(); SCENES[ln["scene"]["type"]](fr, ln["scene"], ln, lt, dur, t); return fr

# ---------- lighting ----------
def light_at(t):
    az = math.radians(212 + 22 * t / total)                              # sun drifts across the slab
    el = 25.0
    for s in CHANGE:
        u = t - s
        if -0.1 < u < 0.6: el = min(el, 25 - 13 * (1 - abs(u + 0.1) / 0.1 if u < 0 else (1 - u / 0.6) ** 2))
    el = math.radians(el)
    return np.array([math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)], np.float32)

STEPS = [2, 4, 7, 11, 16, 23, 32]
def shade(fr, t):
    cut = cv2.GaussianBlur(np.asarray(fr.cut, np.float32) / 255, (0, 0), 2.0)
    rise = cv2.GaussianBlur(np.asarray(fr.rise, np.float32) / 255, (0, 0), 3.2)
    D = BASEH - cut * 11.0 + rise * 12.0
    gx = cv2.Sobel(D, cv2.CV_32F, 1, 0, ksize=3) / 8; gy = cv2.Sobel(D, cv2.CV_32F, 0, 1, ksize=3) / 8
    L = light_at(t); lxy = math.hypot(L[0], L[1]); dx, dy = L[0] / lxy, L[1] / lxy; tane = L[2] / lxy
    ndl = (-gx * L[0] - gy * L[1] + L[2]) / np.sqrt(gx * gx + gy * gy + 1)
    r = np.clip(ndl, 0, None) / L[2]
    occ = np.zeros_like(D)
    for k in STEPS:
        M = np.float32([[1, 0, -dx * k], [0, 1, -dy * k]])               # sample toward the light
        sh = cv2.warpAffine(D, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        occ = np.maximum(occ, np.clip((sh - D - k * tane) / 2.5, 0, 1))
    occ = cv2.GaussianBlur(occ, (0, 0), 1.2)
    lit = 0.30 + 0.80 * (r / (0.35 + 0.65 * r)) * (1 - 0.8 * occ)
    P = np.asarray(fr.paint, np.float32); a = P[..., 3:4] / 255 * PGRAIN[..., None]
    alb = ALB * (1 - a) + P[..., :3] * a
    # warm pool of light that follows the sun
    px = W * (0.25 + 0.5 * (t / total)); pool = 0.86 + 0.22 * np.exp(-(((xx_[::8, ::8] - px) / 900) ** 2 + ((yy_[::8, ::8] - 600) / 1300) ** 2))
    pool = cv2.resize(pool.astype(np.float32), (W, H))[..., None]
    col = alb * lit[..., None] * pool * VIG * np.array([1.04, 1.0, 0.93], np.float32)
    return col

# ---------- dust ----------
def dust(img, fr, t):
    d = ImageDraw.Draw(img, "RGBA")
    for j, (x, y0, y1) in enumerate(fr.emit[:6]):
        r = random.Random(int(t * 30) * 7 + j)
        for i in range(14):
            tau = r.uniform(0, 0.45); vx = r.uniform(-60, 260); vy = r.uniform(-420, -60)
            px = x + vx * tau; py = r.uniform(y0, y1) + vy * tau + 1400 * tau * tau
            s = r.uniform(2, 6) * (1 - tau / 0.5); al = int(230 * (1 - tau / 0.45))
            d.ellipse([px - s + 2, py - s + 3, px + s + 2, py + s + 3], fill=(70, 46, 26, al // 3))
            d.ellipse([px - s, py - s, px + s, py + s], fill=(236, 206, 156, al))
    for (x, y, u) in fr.puffs:
        if 0 <= u < 1.2:
            r = random.Random(3)
            for i in range(26):
                a = r.uniform(math.pi, 2 * math.pi); sp = r.uniform(80, 340)
                px = x + math.cos(a) * sp * eout(u / 1.2) * 1.6; py = y + math.sin(a) * sp * eout(u / 1.2) * 0.6
                s = 10 + 30 * u; al = int(120 * (1 - u / 1.2))
                d.ellipse([px - s, py - s, px + s, py + s], fill=(214, 182, 132, al))
    # scene-change sand puff sweeping across
    for s in CHANGE:
        u = (t - s + 0.05) / 0.55
        if 0 <= u < 1:
            r = random.Random(int(s * 100))
            for i in range(60):
                y = r.uniform(150, 1450); x = -100 + (W + 200) * (u * r.uniform(0.7, 1.3)) + r.uniform(-120, 120)
                sz = r.uniform(3, 9); al = int(170 * math.sin(math.pi * u))
                d.ellipse([x - sz, y - sz * 0.6, x + sz, y + sz * 0.6], fill=(240, 214, 168, al))
    # ambient motes in the sunbeam
    for i in range(18):
        r = random.Random(100 + i); ph = r.random(); sp = r.uniform(0.4, 1.0)
        u = (ph + t * 0.05 * sp) % 1.0
        x = r.uniform(80, W - 80) + 40 * math.sin(t * sp + i); y = 1500 - u * 1400
        al = int(90 * math.sin(math.pi * u)); s = r.uniform(1.5, 3)
        d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 238, 200, al))

# ---------- captions (basalt tablet) ----------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 72
    while F("bold", size).getlength(" ".join(ws)) > W - 260 and size > 36: size -= 4
    f = F("bold", size); tw = f.getlength(" ".join(ws)); x = (W - tw) / 2; y = 1586
    d = ImageDraw.Draw(img, "RGBA")
    x0, x1, y0, y1 = x - 46, x + tw + 46, y - 26, y + size + 30
    d.rounded_rectangle([x0 + 5, y0 + 8, x1 + 5, y1 + 8], radius=18, fill=(60, 36, 18, 120))
    d.rounded_rectangle([x0, y0, x1, y1], radius=18, fill=BASALT + (244,))
    d.rounded_rectangle([x0 + 8, y0 + 8, x1 - 8, y1 - 8], radius=12, outline=GOLD + (230,), width=3)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=(255, 204, 84, 255) if on else (255, 255, 255, 255)); x += f.getlength(w + " ")

def frame(t, fi):
    fr = scene_frame(t)
    col = shade(fr, t)
    img = Image.fromarray(col.clip(0, 255).astype(np.uint8)).convert("RGBA")
    dust(img, fr, t)
    caption(img, t)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 12, W, H], fill=BASALT); d.rectangle([0, H - 12, int(W * t / total), H], fill=GOLD)
    return img.convert("RGB").tobytes()

# ---------- audio ----------
def build_audio():
    n = len(voice); music = np.zeros(n, np.float32); tt = np.arange(n) / SR
    D2, A2 = 73.42, 110.0
    drone = (np.sin(2 * np.pi * D2 * tt) + 0.6 * np.sin(2 * np.pi * A2 * tt) + 0.25 * np.sin(2 * np.pi * D2 * 2.003 * tt)) * (1 + 0.15 * np.sin(2 * np.pi * 0.17 * tt))
    music += (0.09 * drone).astype(np.float32)
    air = np.convolve(np.random.default_rng(4).normal(0, 1, n), np.ones(120) / 120, mode="same") * (0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * tt))
    music += (air * 0.6).astype(np.float32)
    def pluck(f, dur, seed):
        N = int(SR / f); buf = np.random.default_rng(seed).uniform(-1, 1, N).astype(np.float32)
        out = np.zeros(int(dur * SR), np.float32)
        for i in range(len(out)):
            out[i] = buf[i % N]; buf[i % N] = 0.5 * (buf[i % N] + buf[(i + 1) % N]) * 0.996
        return out
    HIJ = [293.66, 311.13, 369.99, 392.0, 440.0, 466.16, 523.25, 587.33]       # D hijaz
    mel = [0, 2, 3, 4, 3, 2, 1, 0, 4, 5, 4, 3, 2, 3, 1, 0]
    BEAT = 0.6
    cache = {}
    for k in range(int(total / BEAT)):
        if k % 2 == 0 or k % 8 == 5:
            f = HIJ[mel[(k // 2) % len(mel)]]
            if f not in cache: cache[f] = pluck(f, 1.2, int(f))
            place(music, 0.2 + k * BEAT, cache[f], 0.11)
    def drum(at, f, gain, dec):
        s = np.arange(int(0.35 * SR)) / SR
        sig = np.sin(2 * np.pi * f * s * (1 + 0.5 * np.exp(-s * 30))) * np.exp(-s * dec)
        place(music, at, sig.astype(np.float32), gain)
    for k in range(int(total / (BEAT / 2))):
        at = k * BEAT / 2; pos = k % 8
        if pos in (0, 5): drum(at, 70, 0.30, 9)                                    # doum
        elif pos in (2, 3, 6): drum(at, 330, 0.07, 30)                             # tek
    hook_hit(music, 0.38)
    for s_ in CHANGE: whoosh(music, s_, 0.14)
    # chisel taps synced to carving (dry pass over the scenes)
    tap = (np.random.default_rng(9).normal(0, 1, int(0.05 * SR)) * np.exp(-np.arange(int(0.05 * SR)) / SR * 90)
           + tone(2900, 0.05, decay=80, harm=(1, 1.7))).astype(np.float32)
    last = -1
    for fi in range(0, int(total * 15)):
        tq = fi / 15
        fr = scene_frame(tq)
        if fr.emit and tq - last >= 0.085:
            place(music, tq, tap, 0.10); last = tq
        if fr.puffs and fr.puffs[0][2] < 0.07: drum(tq, 55, 0.4, 5)
    for ln in spec["lines"]:
        if ln["scene"]["type"] == "end":
            c = ln["_s"] + ln["scene"].get("click_at", 0.45)
            drum(c, 90, 0.3, 12); place(music, c + 0.3, tone(587.33, 1.6, decay=3, harm=(1, 2, 3)), 0.13)
    SPIRE_FALL.clear()
    write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.4)

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): SPIRE_FALL.clear(); Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        build_audio()
        render(total, frame, work + "_audio.wav", out_path, crf=24); print(f"done {total:.1f}s")
