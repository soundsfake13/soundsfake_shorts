"""Day 21 — GREENHOUSE DIORAMA style (a pineapple takes about two years to grow).
A tabletop miniature photographed with a tilt-shift lens: a tiny glass greenhouse (white-painted frames, tinted panes,
diagonal glare) on a warm oak table in front of a seamless mint paper backdrop. Only a thin horizontal band is in focus;
everything above and below melts into lens blur, colours are pushed toward toy-like saturation, corners vignetted.
Inside, a pineapple plant built from shaded two-tone blades (lit edge / shadow edge, swaying) carries a fruit made of
a real lattice of hexagonal fruitlets that ripen bottom-up, with eyes, highlights and a spiky crown. The fruit can
also be shown as a pink inflorescence with purple flowers popping open bottom-up, which then fuse into the fruit.
Props: a lollipop model tree that tips over, paper flag tags on pins, a time-lapse month counter.
Type: Bricolage Grotesque ExtraBold (chunky, toy-like) with dark-green ink, pineapple-gold accents with ink outline,
soft drop shadows; DM Mono on the paper tags. Scene changes are a rack-focus pull (whole frame defocuses and snaps back).
Ending: a cream track with a tiny pineapple knob slides FAKE → TRUE and fills leaf green; the hook framing returns
under it so the Short loops.
Music: marimba-style plucks (C major, 112 bpm) + shaker + soft bass; pops for the flowers, ticks for the time-lapse.
Usage: python3 engine/styles/day21_diorama.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
_F = {}
def F(size, wt=800, kind="bric"):
    k = (kind, int(wt), int(size))
    if k not in _F:
        if kind == "mono": _F[k] = ImageFont.truetype(f"{FONTS}/DMMono-Medium.ttf", int(size))
        else:
            f = ImageFont.truetype(f"{FONTS}/BricolageGrotesque-VF.ttf", int(size)); f.set_variation_by_axes([96, int(wt), 100]); _F[k] = f
    return _F[k]

INK = (26, 56, 38)
GOLD = (244, 178, 38)
LEAF_D, LEAF_L = (40, 92, 62), (112, 164, 104)
PURP = (150, 88, 214)
PINK = (196, 84, 120)
CREAM = (252, 246, 228)
WHITE = (255, 255, 255)

# ---------- camera ----------
CAM = [540.0, 1040.0, 1.0]
SX, SY = 540, 1060
def tp(p): return ((p[0] - CAM[0]) * CAM[2] + SX, (p[1] - CAM[1]) * CAM[2] + SY)
def Z(): return CAM[2]

# ---------- drawing helpers (uint8 HxWx3, screen coords) ----------
def P(pts): return (np.array(pts, np.float32).reshape(-1, 1, 2) * 8).astype(np.int32)
def _box(a, pts, pad):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; h, w = a.shape[:2]
    return max(0, int(min(xs) - pad)), max(0, int(min(ys) - pad)), min(w, int(max(xs) + pad + 1)), min(h, int(max(ys) + pad + 1))
def fill(a, pts, col, al=1.0):
    if al <= 0.01 or len(pts) < 3: return
    x0, y0, x1, y1 = _box(a, pts, 2)
    if x1 <= x0 or y1 <= y0: return
    reg = a[y0:y1, x0:x1]
    if al >= 0.99: cv2.fillPoly(reg, [P([(x - x0, y - y0) for x, y in pts])], col, cv2.LINE_AA, shift=3); return
    tmp = reg.copy(); cv2.fillPoly(tmp, [P([(x - x0, y - y0) for x, y in pts])], col, cv2.LINE_AA, shift=3)
    a[y0:y1, x0:x1] = (reg * (1 - al) + tmp * al).astype(np.uint8)
def line(a, pts, col, w=3, closed=False, al=1.0):
    if al <= 0.01 or len(pts) < 2: return
    x0, y0, x1, y1 = _box(a, pts, w + 3)
    if x1 <= x0 or y1 <= y0: return
    reg = a[y0:y1, x0:x1]
    if al >= 0.99: cv2.polylines(reg, [P([(x - x0, y - y0) for x, y in pts])], closed, col, max(1, int(round(w))), cv2.LINE_AA, shift=3); return
    tmp = reg.copy(); cv2.polylines(tmp, [P([(x - x0, y - y0) for x, y in pts])], closed, col, max(1, int(round(w))), cv2.LINE_AA, shift=3)
    a[y0:y1, x0:x1] = (reg * (1 - al) + tmp * al).astype(np.uint8)
def ell_pts(cx, cy, rx, ry, n=48, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    return [(cx + rx * math.cos(2 * math.pi * k / n) * c - ry * math.sin(2 * math.pi * k / n) * s,
             cy + rx * math.cos(2 * math.pi * k / n) * s + ry * math.sin(2 * math.pi * k / n) * c) for k in range(n)]
def soft_shadow(a, pts, blur=14, strength=0.35, col=(60, 40, 30)):
    x0, y0, x1, y1 = _box(a, pts, blur * 3)
    if x1 <= x0 or y1 <= y0: return
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillPoly(m, [P([(x - x0, y - y0) for x, y in pts])], 255, cv2.LINE_AA, shift=3)
    sm = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), blur)[..., None] * strength
    reg = a[y0:y1, x0:x1].astype(np.float32); a[y0:y1, x0:x1] = (reg * (1 - sm) + np.array(col, np.float32) * sm).astype(np.uint8)
def mix(c1, c2, u): u = max(0.0, min(1.0, u)); return tuple(int(c1[i] * (1 - u) + c2[i] * u) for i in range(3))
def shade(c, k): return tuple(int(max(0, min(255, v * k))) for v in c)

# ---------- static world layers ----------
OX, OY, WW, WH = -300, -400, 1680, 2800
def fbm(seed, scales, amps, size, stretch=1.0):
    rr = np.random.default_rng(seed); acc = np.zeros((size[1], size[0]), np.float32)
    for s, a_ in zip(scales, amps):
        g = rr.random((max(2, int(size[1] / s) + 2), max(2, int(size[0] / (s * stretch)) + 2))).astype(np.float32)
        acc += a_ * cv2.resize(g, size, interpolation=cv2.INTER_CUBIC)
    acc -= acc.min(); return acc / max(1e-6, acc.max())
def wp(pts): return [(x - OX, y - OY) for x, y in pts]

GX0, GX1, GYB, GYE, GYP = 230, 850, 1300, 880, 720    # greenhouse: left, right, base, eave, peak (front face)
DX, DY = 56, -44                                       # depth offset to the back face
TABLE_Y = 1210

def build_static():
    yy = np.arange(WH, dtype=np.float32)[:, None] + OY; xx = np.arange(WW, dtype=np.float32)[None, :] + OX
    # seamless mint backdrop with a warm soft light from upper left
    v = np.clip((yy + 400) / (TABLE_Y + 400), 0, 1)
    top, bot = np.array([156, 204, 186], np.float32), np.array([214, 234, 214], np.float32)
    bg = top * (1 - v[..., None]) + bot * v[..., None]
    bg = np.broadcast_to(bg, (WH, WW, 3)).copy()
    light = np.exp(-(((xx - 200) / 700) ** 2 + ((yy - 300) / 600) ** 2))
    bg += light[..., None] * np.array([34, 26, 8], np.float32)
    bg += ((fbm(4, [300, 90], [1, 0.4], (WW, WH)) - 0.5) * 7)[..., None]
    # oak table with planks in perspective
    tb = yy >= TABLE_Y
    grain = fbm(11, [40, 14, 5], [1, 0.6, 0.35], (WW, WH), stretch=14.0)
    oak = np.array([198, 146, 96], np.float32)
    wood = oak[None, None, :] * (0.82 + 0.3 * grain[..., None])
    rowsY = [TABLE_Y]; h = 34
    while rowsY[-1] < OY + WH: rowsY.append(rowsY[-1] + h); h *= 1.13
    for k, (ya, yb) in enumerate(zip(rowsY, rowsY[1:])):
        sl = slice(max(0, int(ya - OY)), min(WH, int(yb - OY)))
        wood[sl] *= 0.92 + 0.12 * random.Random(k).random()
        r0 = int(ya - OY)
        if 0 <= r0 < WH: wood[r0:r0 + 2] *= 0.6
    depth = np.clip((yy - TABLE_Y) / 600, 0, 1)[..., None]
    wood = wood * (0.86 + 0.18 * depth) + (1 - depth) * np.array([16, 18, 14], np.float32)   # far = hazier
    bg = np.where(tb[..., None], wood, bg)
    edge = (yy >= TABLE_Y) & (yy < TABLE_Y + 4)
    bg[np.broadcast_to(edge, (WH, WW))] *= 1.0
    back = np.clip(bg, 0, 255).astype(np.uint8)
    # greenhouse shadow on the table (light from upper left → shadow to the right/back)
    soft_shadow(back, wp([(GX0 + 10, GYB + 40), (GX1 + 10, GYB + 40), (GX1 + DX + 150, GYB + DY + 30), (GX0 + DX + 120, GYB + DY + 20)]), 30, 0.45)
    soft_shadow(back, wp([(GX0 - 6, GYB + 50), (GX1 + 6, GYB + 50), (GX1 + 6, GYB + 62), (GX0 - 6, GYB + 62)]), 6, 0.5)
    # small props: terracotta pot with sprout (right front), stack of tiny crates (left back)
    px, py = 960, 1452
    soft_shadow(back, wp(ell_pts(px + 18, py + 8, 64, 16)), 8, 0.4)
    fill(back, wp([(px - 46, py - 74), (px + 46, py - 74), (px + 34, py), (px - 34, py)]), (196, 102, 64))
    fill(back, wp([(px - 46, py - 74), (px - 30, py - 74), (px - 22, py), (px - 34, py)]), (226, 136, 92))
    fill(back, wp([(px - 52, py - 92), (px + 52, py - 92), (px + 52, py - 70), (px - 52, py - 70)]), (210, 116, 74))
    fill(back, wp(ell_pts(px, py - 92, 50, 8)), (92, 60, 40))
    for s_, ang in ((1, -0.5), (-1, 0.5), (1, 0.1)):
        bx, by = px, py - 94
        pts = [(bx + 70 * math.sin(ang) * u + s_ * 16 * u * u, by - 60 * u) for u in np.linspace(0, 1, 8)]
        line(back, wp(pts), (70, 140, 80), 6)
        fill(back, wp(ell_pts(pts[-1][0] + s_ * 10, pts[-1][1], 16, 8, rot=-s_ * 0.5)), (96, 170, 96))
    cx_, cy_ = 70, 1300
    for k, (ox_, oy_) in enumerate(((0, 0), (78, 0), (38, -58))):
        x, y = cx_ + ox_, cy_ + oy_
        soft_shadow(back, wp([(x, y), (x + 74, y), (x + 84, y + 10), (x + 10, y + 10)]), 6, 0.35) if k < 2 else None
        fill(back, wp([(x, y - 56), (x + 72, y - 56), (x + 72, y), (x, y)]), (214, 172, 112))
        for j in range(3): line(back, wp([(x + 2, y - 46 + j * 18), (x + 70, y - 46 + j * 18)]), (170, 126, 76), 3)
        line(back, wp([(x, y - 56), (x + 72, y - 56), (x + 72, y), (x, y)]), (150, 108, 64), 3, True)
    # back face + right side of the greenhouse (behind the plant)
    bf = [(GX0 + DX, GYB + DY), (GX0 + DX, GYE + DY), (540 + DX, GYP + DY), (GX1 + DX, GYE + DY), (GX1 + DX, GYB + DY)]
    side = [(GX1, GYB), (GX1, GYE), (GX1 + DX, GYE + DY), (GX1 + DX, GYB + DY)]
    fill(back, wp(bf), (226, 244, 240), 0.22)
    fill(back, wp(side), (226, 244, 240), 0.26)
    for pts in (bf,):
        line(back, wp(pts), (180, 196, 192), 7, True); line(back, wp(pts), (236, 240, 236), 4, True)
    for x in (GX0 + 155, 540, GX1 - 155):
        line(back, wp([(x + DX, GYB + DY), (x + DX, GYE + DY + (0 if x != 540 else (GYP - GYE)))]), (226, 232, 228), 4, al=0.8)
    # soil bed
    soil = [(GX0 + 6, GYB), (GX1 - 6, GYB), (GX1 + DX - 6, GYB + DY), (GX0 + DX + 6, GYB + DY)]
    fill(back, wp(soil), (86, 58, 40))
    rr = random.Random(5)
    for _ in range(260):
        u, w_ = rr.random(), rr.random()
        x = GX0 + 10 + u * (GX1 - GX0 - 20) + DX * w_; y = GYB + DY * w_
        cv2.circle(back, (int(x - OX), int(y - OY)), rr.choice((1, 2, 2, 3)), (60 + rr.randint(0, 50), 42 + rr.randint(0, 30), 30), -1, cv2.LINE_AA)
    # ---- front layer (RGBA): planter box, front glass, roof, frames, glare ----
    fr = np.zeros((WH, WW, 4), np.uint8)
    def fr_fill(pts, col, al):
        tmp = np.zeros((WH, WW), np.uint8)
        x0, y0, x1, y1 = _box(fr, wp(pts), 2)
        sub = tmp[y0:y1, x0:x1]; cv2.fillPoly(sub, [P([(x - OX - x0, y - OY - y0) for x, y in pts])], 255, cv2.LINE_AA, shift=3)
        aa = sub.astype(np.float32) / 255 * al
        reg = fr[y0:y1, x0:x1].astype(np.float32); A = reg[..., 3:4] / 255
        nA = aa[..., None] + A * (1 - aa[..., None])
        rgb = (np.array(col, np.float32) * aa[..., None] + reg[..., :3] * A * (1 - aa[..., None])) / np.maximum(nA, 1e-6)
        fr[y0:y1, x0:x1, :3] = rgb.astype(np.uint8); fr[y0:y1, x0:x1, 3] = (nA[..., 0] * 255).astype(np.uint8)
    def fr_line(pts, col, w, al=1.0, closed=False):
        x0, y0, x1, y1 = _box(fr, wp(pts), w + 3)
        sub = np.zeros((y1 - y0, x1 - x0), np.uint8)
        cv2.polylines(sub, [P([(x - OX - x0, y - OY - y0) for x, y in pts])], closed, 255, int(w), cv2.LINE_AA, shift=3)
        aa = sub.astype(np.float32) / 255 * al
        reg = fr[y0:y1, x0:x1].astype(np.float32); A = reg[..., 3:4] / 255
        nA = aa[..., None] + A * (1 - aa[..., None])
        rgb = (np.array(col, np.float32) * aa[..., None] + reg[..., :3] * A * (1 - aa[..., None])) / np.maximum(nA, 1e-6)
        fr[y0:y1, x0:x1, :3] = rgb.astype(np.uint8); fr[y0:y1, x0:x1, 3] = (nA[..., 0] * 255).astype(np.uint8)
    def bar(pts, w=10, al=1.0, closed=False):
        fr_line(pts, (150, 162, 156), w + 4, al, closed); fr_line(pts, (248, 248, 242), w, al, closed)
    ff = [(GX0, GYB), (GX0, GYE), (540, GYP), (GX1, GYE), (GX1, GYB)]
    fr_fill(ff, (220, 242, 244), 0.12)
    roofL = [(GX0, GYE), (540, GYP), (540 + DX, GYP + DY), (GX0 + DX, GYE + DY)]
    roofR = [(540, GYP), (GX1, GYE), (GX1 + DX, GYE + DY), (540 + DX, GYP + DY)]
    fr_fill(roofL, (232, 248, 248), 0.30); fr_fill(roofR, (210, 236, 240), 0.22)
    for k, (gx, w_) in enumerate(((300, 46), (380, 18), (640, 60), (720, 20))):     # diagonal glare on the front panes
        y_top = GYE - (gx - GX0) * 0.15 if gx < 540 else GYE - (GX1 - gx) * 0.15
        fr_fill([(gx, GYB - 60), (gx + w_, GYB - 60), (gx + w_ + 160, y_top + 60), (gx + 160, y_top + 60)], WHITE, 0.16 if w_ > 30 else 0.24)
    fr_fill([(330, GYE - 20), (400, GYE - 52), (430, GYE - 40), (360, GYE - 8)], WHITE, 0.3)
    # planter box (front plank)
    fr_fill([(GX0 - 8, GYB - 6), (GX1 + 8, GYB - 6), (GX1 + 8, GYB + 52), (GX0 - 8, GYB + 52)], (158, 104, 62), 1)
    fr_fill([(GX0 - 8, GYB - 6), (GX1 + 8, GYB - 6), (GX1 + 8, GYB + 4), (GX0 - 8, GYB + 4)], (196, 142, 92), 1)
    fr_line([(GX0 - 8, GYB + 24), (GX1 + 8, GYB + 24)], (128, 82, 48), 3)
    for x in (GX0 + 30, GX1 - 30): fr_fill(ell_pts(x, GYB + 24, 5, 5, 12), (110, 80, 60), 1)
    fr_fill([(GX1 + 8, GYB - 6), (GX1 + 8 + DX * 0.3, GYB - 6 + DY * 0.3), (GX1 + 8 + DX * 0.3, GYB + 52 + DY * 0.3), (GX1 + 8, GYB + 52)], (122, 80, 46), 1)
    # frames
    bar(roofL, 9, closed=True); bar(roofR, 9, closed=True)
    for u in (0.33, 0.66):
        bar([(GX0 + (540 - GX0) * u, GYE + (GYP - GYE) * u), (GX0 + (540 - GX0) * u + DX, GYE + (GYP - GYE) * u + DY)], 6)
        bar([(540 + (GX1 - 540) * u, GYP + (GYE - GYP) * u), (540 + (GX1 - 540) * u + DX, GYP + (GYE - GYP) * u + DY)], 6)
    bar([(GX1, GYB - 4), (GX1 + DX, GYB + DY - 4)], 7); bar([(GX1 + DX, GYB + DY), (GX1 + DX, GYE + DY)], 7)
    bar(ff, 11, closed=True)
    for x in (GX0 + 155, GX1 - 155): bar([(x, GYB), (x, GYE - (min(x - GX0, GX1 - x)) * (GYE - GYP) / 310)], 8)
    bar([(GX0, GYE), (GX1, GYE)], 8)
    bar([(GX0, GYB - 150), (GX0 + 155, GYB - 150)], 6); bar([(GX1 - 155, GYB - 150), (GX1, GYB - 150)], 6)
    return back, fr

BACK, FRONT = build_static()
def cam_M():
    z = CAM[2]
    return np.float32([[z, 0, z * (OX - CAM[0]) + SX], [0, z, z * (OY - CAM[1]) + SY]])
def warp(img, M, border):
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE if border else cv2.BORDER_CONSTANT)

# ---------- plant + fruit (screen space) ----------
def leaf(a, B, ang, L, w0, droop=0.35, dk=LEAF_D, lt_=LEAF_L, al=1.0):
    if L < 2: return
    n = 12; sp = []
    sg = 1 if ang >= 0 else -1
    for k in range(n + 1):
        s = k / n
        sp.append((B[0] + L * (math.sin(ang) * s + sg * droop * 0.15 * s * s), B[1] + L * (-math.cos(ang) * s + droop * 0.75 * s * s)))
    left, right = [], []
    for k, (x, y) in enumerate(sp):
        x2, y2 = sp[min(k + 1, n)]; x1, y1 = sp[max(k - 1, 0)]
        dx, dy = x2 - x1, y2 - y1; d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d, dx / d; w = w0 * (1 - k / n) ** 0.85
        left.append((x + nx * w, y + ny * w)); right.append((x - nx * w, y - ny * w))
    fill(a, left + right[::-1], dk, al)
    upper = left if left[n // 2][1] < right[n // 2][1] else right     # the upper half catches the light
    fill(a, upper + sp[::-1], lt_, al)
    line(a, sp[: n - 1], shade(lt_, 1.12), max(1, w0 * 0.12), al=al * 0.7)

LEAVES = []
_r = random.Random(21)
for i in range(30):
    ang = (i / 29 - 0.5) * 2.45 + _r.uniform(-0.05, 0.05)
    L = 300 - 40 * (1 - abs(ang) / 1.25) ** 2 + _r.uniform(-25, 25)
    LEAVES.append((ang, L, _r.uniform(0.2, 0.5), _r.uniform(0, 6.28), _r.uniform(0.9, 1.1)))
LEAVES.sort(key=lambda q: -abs(q[0]))
FRONT_LEAVES = [(-1.05, 190, 0.4, 1.0), (0.95, 200, 0.45, 2.0), (-0.55, 150, 0.3, 3.0), (0.6, 160, 0.3, 4.0)]

def fruit(a, cx, cy, sc, rip=1.0, pink=0.0, bloom=None, fuse=1.0, crown=1.0, glow=0.0, t=0.0, spin=0.0):
    """rx/ry ∝ sc. bloom: None or 0..1 (flowers opening bottom-up). fuse: 0 = separate fruitlets, 1 = solid fruit."""
    rx, ry = 66 * sc, 96 * sc
    if rx < 1: return
    shadow_col = mix(mix((70, 100, 50), (150, 92, 30), rip), (110, 40, 70), pink)
    fill(a, ell_pts(cx, cy, rx * (0.80 + 0.2 * fuse), ry * (0.92 + 0.08 * fuse)), shadow_col)
    # crown
    if crown > 0:
        for k in range(11):
            ang = (k / 10 - 0.5) * 1.9
            Lc = ry * (0.75 + 0.55 * (1 - abs(ang) / 1.0) ** 1.5) * crown * (0.6 + 0.4 * fuse)
            leaf(a, (cx + rx * 0.12 * math.sin(ang), cy - ry * 0.9), ang, Lc, rx * 0.16, 0.25, (46, 104, 70), (104, 166, 110))
    nrows, ncols = 8, 9
    cells = []
    for j in range(nrows):
        yy = -0.84 + 1.68 * j / (nrows - 1)
        rxj = rx * math.sqrt(max(0.05, 1 - (yy * 0.93) ** 2))
        for i in range(ncols):
            th = (i + 0.5 * (j % 2)) * 2 * math.pi / ncols + spin
            th = (th + math.pi) % (2 * math.pi) - math.pi
            c = math.cos(th)
            if c < 0.08: continue
            cells.append((c, j, i, yy, th, rxj))
    cells.sort()
    for c, j, i, yy, th, rxj in cells:
        x = cx + rxj * math.sin(th); y = cy + ry * yy
        hw = rxj * math.pi / ncols * c * 1.02; hh = ry / (nrows - 1) * 1.04
        s = 0.62 + 0.38 * ease(fuse)
        hx, hy = hw * s, hh * s
        poly = [(x - hx, y), (x - hx * 0.5, y - hy), (x + hx * 0.5, y - hy), (x + hx, y), (x + hx * 0.5, y + hy), (x - hx * 0.5, y + hy)]
        lr = max(0.0, min(1.0, rip * 1.5 - 0.5 * (1 - (yy + 1) / 2)))
        base = mix(mix((104, 152, 74), GOLD, lr), PINK, pink)
        lit = 0.78 + 0.32 * (-math.sin(th)) * 0.8 + 0.12 * (-yy) + 0.1 * c
        fill(a, poly, shade(base, lit))
        if fuse > 0.4:
            inner = [(x + (px - x) * 0.55, y - hh * 0.12 + (py - y) * 0.55) for px, py in poly]
            fill(a, inner, shade(base, lit * 1.12), min(1, (fuse - 0.4) * 2))
        line(a, poly, shade(base, lit * 0.62), max(1, sc * 1.6), True)
        if glow > 0: line(a, poly, (255, 250, 220), max(1, sc * 2.2), True, glow * c)
        if fuse > 0.5 and c > 0.3:
            ex, ey = x + hw * 0.1, y + hh * 0.15
            cv2.circle(a, (int(ex), int(ey)), max(1, int(sc * 2.6 * c)), shade(base, 0.45), -1, cv2.LINE_AA)
            cv2.circle(a, (int(x - hw * 0.35), int(y - hh * 0.4)), max(1, int(sc * 1.5 * c)), shade(base, 1.35), -1, cv2.LINE_AA)
        if bloom is not None:
            order = (1 - (yy + 1) / 2)                      # bottom rows first
            b = back(max(0.0, min(1.0, (bloom * 1.6 - order) * 2.2)))
            if b > 0.02 and c > 0.25:
                r = hw * 0.9 * b
                for k in range(3):
                    ang = k * 2.094 + i + j * 0.7
                    fill(a, ell_pts(x + r * 0.55 * math.cos(ang), y + r * 0.55 * math.sin(ang) - hh * 0.1, r * 0.62, r * 0.42, 16, ang), shade(PURP, 0.9 + 0.25 * c))
                fill(a, ell_pts(x, y - hh * 0.1, r * 0.28, r * 0.28, 12), (238, 214, 250))
    # specular sheen
    fill(a, ell_pts(cx - rx * 0.42, cy - ry * 0.25, rx * 0.12, ry * 0.32, 24, 0.15), WHITE, 0.16 * fuse)

def plant(a, base, sc, g=1.0, t=0.0, fruit_kw=None, stalk=250):
    for ang, L, dr, ph, wk in LEAVES:
        aa = ang + 0.025 * math.sin(t * 1.3 + ph)
        leaf(a, base, aa, L * sc * g, 19 * sc * (0.45 + 0.55 * g) * wk, dr)
    if fruit_kw is not None and fruit_kw.get("size", 1) > 0.01:
        fs = fruit_kw.pop("size", 1.0)
        fy = base[1] - stalk * sc * (0.55 + 0.45 * fs)
        cv2.line(a, (int(base[0]), int(base[1] - 20 * sc)), (int(base[0]), int(fy + 60 * sc * fs)), (96, 128, 66), max(2, int(16 * sc)), cv2.LINE_AA)
        fruit(a, base[0], fy, sc * fs, t=t, **fruit_kw)
    for ang, L, dr, ph in FRONT_LEAVES:
        leaf(a, (base[0], base[1] + 6 * sc), ang + 0.02 * math.sin(t * 1.4 + ph), L * sc * g, 14 * sc * (0.45 + 0.55 * g), dr)

PB = (540, 1286)       # plant base (world)
def draw_plant(a, t, g=1.0, **kw):
    b = tp(PB); plant(a, b, Z(), g, t, kw if kw else dict(size=1.0))

def tree(a, base, sc, rot=0.0, t=0.0):
    """Lollipop model-railway tree with a pineapple hanging from it (the wrong idea)."""
    bx, by = base; c, s = math.cos(rot), math.sin(rot)
    def R(x, y): return (bx + (x * c - y * s) * sc, by + (x * s + y * c) * sc)
    soft_shadow(a, [R(-40, 0), R(40, 0), R(70, 14), R(-20, 14)], 8 * sc, 0.35)
    fill(a, [R(-9, 0), R(9, 0), R(6, -150), R(-6, -150)], (120, 80, 50))
    fill(a, [R(-9, 0), R(-2, 0), R(-2, -150), R(-6, -150)], (156, 108, 70))
    for k, (ox, oy, r) in enumerate(((-34, -170, 52), (30, -178, 54), (0, -224, 60), (-40, -220, 40), (40, -226, 40), (0, -150, 44))):
        cx, cy = R(ox, oy)
        fill(a, ell_pts(cx, cy, r * sc, r * sc, 32), (62, 132, 74))
        hx, hy = R(ox - r * 0.3, oy - r * 0.3)
        fill(a, ell_pts(hx, hy, r * 0.55 * sc, r * 0.5 * sc, 24), (98, 170, 96))
    fx, fy = R(34, -128)
    line(a, [R(34, -150), (fx, fy - 18 * sc)], (90, 70, 50), max(1, 2 * sc))
    fruit(a, fx, fy, 0.34 * sc, rip=1.0, crown=0.7)

def tag(a, anchor, txt, up=150, side=1, al=1.0, size=30):
    """Paper flag on a pin, stuck at `anchor` (screen)."""
    if al <= 0.01: return
    ax, ay = anchor; tx, ty = ax + side * 40, ay - up
    line(a, [(ax, ay), (tx, ty)], (110, 110, 110), 3, al=al)
    cv2.circle(a, (int(tx), int(ty)), 7, (214, 60, 52), -1, cv2.LINE_AA)
    f = F(size, kind="mono"); w = f.getlength(txt) + 36; h = size + 26
    x0 = tx + 8 if side > 0 else tx - 8 - w
    pts = [(x0, ty - h / 2), (x0 + w, ty - h / 2), (x0 + w, ty + h / 2), (x0, ty + h / 2)]
    soft_shadow(a, [(x + 8, y + 10) for x, y in pts], 6, 0.3 * al)
    fill(a, pts, CREAM, al); line(a, pts, (200, 184, 150), 2, True, al)
    TAGS.append((txt, x0 + 18, ty, size, al))
TAGS = []

# ---------- titles (PIL, sharp, after the lens) ----------
TXT = []
def text(s, size, cx, cy, col=INK, al=1.0, stroke=0, wt=800, pop=1.0):
    if al > 0.01: TXT.append((s, int(size), cx, cy, col, al, stroke, wt, pop))
def fit(s, size, maxw=W - 140, wt=800):
    while F(size, wt).getlength(s) > maxw and size > 40: size -= 2
    return size
def draw_texts(img):
    if not TXT and not TAGS: img_ = img
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for s, size, cx, cy, col, al, stroke, wt, pop in TXT:
        sz = max(10, int(size * (0.86 + 0.14 * pop)) // 2 * 2); f = F(sz, wt)
        w = f.getlength(s); asc, desc = f.getmetrics(); y = cy - (asc + desc) / 2 + desc * 0.3 + (1 - pop) * 26
        d.text((cx - w / 2, y), s, font=f, fill=col + (int(255 * al),), stroke_width=stroke, stroke_fill=INK + (int(255 * al),))
    sh = lay.split()[3].filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * 0.42))
    shadow = Image.new("RGBA", (W, H), (20, 50, 30, 0)); shadow.putalpha(sh)
    img = img.convert("RGBA")
    img.alpha_composite(shadow, (8, 12)); img.alpha_composite(lay)
    d2 = ImageDraw.Draw(img)
    for txt, x, y, size, al in TAGS:
        f = F(size, kind="mono"); asc, desc = f.getmetrics()
        d2.text((x, y - (asc + desc) / 2 + 2), txt, font=f, fill=INK + (int(255 * al),))
    TXT.clear(); TAGS.clear()
    return img.convert("RGB")

def fade(lt, at, d=0.3): return ease((lt - at) / d)
def popv(lt, at, d=0.35): return back(max(0.0, min(1.0, (lt - at) / d)))
def wt_(ln, i): return words[min(ln["_w0"] + i, ln["_w1"] - 1)][1] - ln["_s"]
def setcam(cx, cy, z): CAM[0], CAM[1], CAM[2] = cx, cy, z

# ---------- scenes: each returns after setting CAM; draw(a) draws the dynamic layer ----------
def C_hook(sc, ln, lt, dur, t): setcam(540, 1040 - 8 * ease(lt / dur), 1.0 + 0.05 * lt / dur)
def D_hook(a, sc, ln, lt, dur, t):
    draw_plant(a, t, 1.0, size=1.0, rip=1.0)
    text("THIS PINEAPPLE", fit("THIS PINEAPPLE", 112), W / 2, 200, INK)
    text("TOOK 2 YEARS", fit("TOOK 2 YEARS", 156), W / 2, 365, GOLD, 1, 6)
    text("TO GROW.", 112, W / 2, 530, INK)

def C_loop(sc, ln, lt, dur, t):
    u = ease(lt / 1.3); setcam(540, 1040 - 40 * u, 1.05 + 0.85 * u)
def D_loop(a, sc, ln, lt, dur, t):
    gl = 0.5 + 0.5 * math.sin(lt * 6)
    draw_plant(a, t, 1.0, size=1.0, rip=1.0, glow=fade(lt, 0.6, 0.4) * (0.35 + 0.4 * gl))
    k = wt_(ln, 3)
    text("AND HOW IT'S BUILT", fit("AND HOW IT'S BUILT", 96), W / 2, 230, INK, 1, 0, 800, popv(lt, 0.0, 0.3))
    text("IS EVEN STRANGER.", fit("IS EVEN STRANGER.", 116), W / 2, 380, GOLD, fade(lt, k - 0.1, 0.2), 6, 800, popv(lt, k - 0.1))

TREE_W = (120, 1500)
def C_ground(sc, ln, lt, dur, t): setcam(470 + 30 * ease(lt / dur), 1080, 0.88 + 0.05 * lt / dur)
def D_ground(a, sc, ln, lt, dur, t):
    k_tree = wt_(ln, 4); k_they = wt_(ln, 5)
    fall = ease((lt - k_tree - 0.15) / 0.55)
    rot = -1.45 * fall ** 1.6
    if fall < 1 or True:
        tree(a, tp(TREE_W), Z() * 1.55, rot, t)
    draw_plant(a, t, 1.0, size=1.0, rip=1.0)
    s = fade(lt, k_tree - 0.25, 0.2)
    if s > 0 and fall < 0.9:
        cx, cy = tp((TREE_W[0], TREE_W[1] - 250)); r = 210 * Z() * (0.8 + 0.2 * popv(lt, k_tree - 0.25))
        line(a, ell_pts(cx, cy, r, r, 48), (214, 50, 46), 14 * Z(), True, s * (1 - fall))
        line(a, [(cx - r * 0.7, cy + r * 0.7), (cx + r * 0.7, cy - r * 0.7)], (214, 50, 46), 14 * Z(), al=s * (1 - fall))
    tg = fade(lt, k_they + 0.2, 0.3)
    tag(a, tp((620, 1288)), "IN THE GROUND", 300 * Z(), 1, tg)
    text("NOT ON TREES.", fit("NOT ON TREES.", 116), W / 2, 220, INK, 1, 0, 800, popv(lt, 0.0, 0.3))
    if s > 0:
        u_ = ease((lt - k_tree + 0.1) / 0.3)
        POST.append(lambda b_: line(b_, [(150, 226), (150 + 780 * u_, 226)], (214, 50, 46), 12))
    text("FROM A SPIKY PLANT", fit("FROM A SPIKY PLANT", 92), W / 2, 380, INK, fade(lt, k_they - 0.1, 0.2), 0, 800, popv(lt, k_they - 0.1))
    text("IN THE GROUND", fit("IN THE GROUND", 112), W / 2, 505, GOLD, fade(lt, k_they + 0.6, 0.2), 6, 800, popv(lt, k_they + 0.6))

def month_at(lt, dur): return 24 * max(0.0, min(1.0, (lt - 0.25) / (dur - 0.7)))
def C_grow(sc, ln, lt, dur, t): setcam(540, 1050, 0.97 + 0.03 * lt / dur)
def D_grow(a, sc, ln, lt, dur, t):
    m = month_at(lt, dur)
    g = 0.14 + 0.86 * ease(min(1, m / 14))
    fs = ease((m - 13) / 7); pink = 1 - max(0.0, min(1.0, (m - 14.5) / 2.5)); rip = max(0.0, min(1.0, (m - 18) / 6))
    bl = max(0.0, min(1.0, (m - 13.5) / 2)) if m < 17 else max(0.0, 1 - (m - 17) / 1.5)
    draw_plant(a, t, g, size=fs, rip=rip, pink=pink, bloom=bl if bl > 0 else None, fuse=min(1.0, max(0.0, (m - 16) / 2.5)), crown=fs)
    sunx = 540 + 420 * math.sin(2 * math.pi * m / 6)        # time-lapse: a tiny sun lamp swings by every few 'months'
    text("MONTH", 64, W / 2, 175, INK, 1, 0, 700)
    text(f"{int(m):d}", 210, W / 2, 330, GOLD, 1, 7)
    if m >= 17.5:
        p = popv(m, 17.5, 1.2)
        text("FIRST FRUIT: 18–24 MONTHS", fit("FIRST FRUIT: 18–24 MONTHS", 64), W / 2, 500, INK, min(1, (m - 17.5) / 0.8), 0, 800, p)
    # calendar ticks along the top of the counter
    for k in range(24):
        x = 160 + k * (760 / 23); on = k < m
        cv2.circle(a, (int(x), 600), 9 if on else 6, GOLD if on else (190, 214, 200), -1, cv2.LINE_AA)

def C_one(sc, ln, lt, dur, t): setcam(540, 1010, 1.3 + 0.08 * lt / dur)
def D_one(a, sc, ln, lt, dur, t):
    k = wt_(ln, 5)
    b = 1 + 0.06 * math.sin(max(0, lt - k) * 14) * math.exp(-max(0, lt - k) * 4) if lt > k else 1
    draw_plant(a, t, 1.0, size=b, rip=1.0)
    tg = fade(lt, k + 0.1, 0.3)
    tag(a, tp((560, 1110)), "1 PER PLANT", 250 * Z() * 0.75, 1, tg, 30)
    text("JUST ONE", 124, W / 2, 205, INK, 1, 0, 800, popv(lt, 0.0, 0.3))
    text("PINEAPPLE", fit("PINEAPPLE", 150), W / 2, 365, GOLD, fade(lt, k - 0.15, 0.2), 6, 800, popv(lt, k - 0.15))
    text("AT A TIME.", 96, W / 2, 515, INK, fade(lt, wt_(ln, 7) - 0.1, 0.2), 0, 800, popv(lt, wt_(ln, 7) - 0.1))

def C_flowers(sc, ln, lt, dur, t): setcam(540, 1000, 2.35 + 0.12 * lt / dur)
def D_flowers(a, sc, ln, lt, dur, t):
    k = wt_(ln, 5)
    bl = max(0.0, min(1.0, (lt - k + 0.4) / 1.6))
    draw_plant(a, t, 1.0, size=0.92, rip=0.0, pink=1.0, bloom=bl, fuse=0.0, crown=0.85)
    text("THE STRANGE PART?", fit("THE STRANGE PART?", 92), W / 2, 210, INK, 1, 0, 800, popv(lt, 0.0, 0.3))
    text("DOZENS OF TINY", fit("DOZENS OF TINY", 104), W / 2, 360, INK, fade(lt, k - 0.15, 0.2), 0, 800, popv(lt, k - 0.15))
    text("PURPLE FLOWERS", fit("PURPLE FLOWERS", 124), W / 2, 500, (190, 140, 250), fade(lt, wt_(ln, 8) - 0.15, 0.2), 6, 800, popv(lt, wt_(ln, 8) - 0.15))

def C_fuse(sc, ln, lt, dur, t): setcam(540, 1000 + 20 * ease(lt / dur), 2.47 - 0.6 * ease(lt / dur))
def D_fuse(a, sc, ln, lt, dur, t):
    u = ease((lt - 0.2) / 1.5)
    bl = 1 - ease((lt - 0.1) / 0.8)
    draw_plant(a, t, 1.0, size=0.92 + 0.08 * u, rip=u, pink=1 - u, bloom=bl if bl > 0.02 else None, fuse=u, crown=0.85 + 0.15 * u,
               glow=0.6 * math.sin(math.pi * u))
    if 0.3 < u < 1:
        cx, cy = tp((540, 1286 - 300)); rr = random.Random(int(lt * 8))
        for j in range(6):
            ang = rr.uniform(0, 6.28); r = 120 * Z() * rr.uniform(0.6, 1.0)
            x, y = cx + r * math.cos(ang), cy + r * math.sin(ang); s = 10 * rr.uniform(0.6, 1.2)
            fill(a, [(x, y - s * 2), (x + s * 0.5, y - s * 0.5), (x + s * 2, y), (x + s * 0.5, y + s * 0.5), (x, y + s * 2), (x - s * 0.5, y + s * 0.5), (x - s * 2, y), (x - s * 0.5, y - s * 0.5)], (255, 248, 210), 0.8)
    text("THAT FUSE INTO", fit("THAT FUSE INTO", 104), W / 2, 230, INK, 1, 0, 800, popv(lt, 0.0, 0.3))
    text("ONE FRUIT.", fit("ONE FRUIT.", 170), W / 2, 410, GOLD, fade(lt, wt_(ln, 5) - 0.15, 0.2), 7, 800, popv(lt, wt_(ln, 5) - 0.15))

def C_end(sc, ln, lt, dur, t):
    lp = ease((lt - (dur - 0.75)) / 0.65)
    setcam(540, 1040 - 20 * (1 - lp), 0.92 + 0.08 * lp)
POST = []
def toggle(a, on, ea, y=355, x0=210, x1=870, hh=120):
    r = hh / 2
    trk = [(x0 + r + (x1 - x0 - hh) * (k > 20) + r * math.sin(math.pi * (k % 21) / 20 + (math.pi if k <= 20 else 0)),
            y - r * math.cos(math.pi * (k % 21) / 20 + (math.pi if k <= 20 else 0))) for k in range(42)]
    soft_shadow(a, [(x + 8, y_ + 14) for x, y_ in trk], 10, 0.35 * ea)
    fill(a, trk, CREAM, ea)
    kx = x0 + r + (x1 - x0 - hh) * on
    if on > 0:
        ri = r - 10
        g = [(x0 + r - ri * math.sin(math.pi * k / 20), y - ri * math.cos(math.pi * k / 20)) for k in range(21)] + [(kx, y + ri), (kx, y - ri)]
        fill(a, g, (104, 168, 96), ea)
    line(a, trk, INK, 5, True, ea)
    soft_shadow(a, ell_pts(kx + 6, y + 12, 46, 46, 30), 8, 0.4 * ea)
    fill(a, ell_pts(kx, y, 52, 52, 40), WHITE, ea); line(a, ell_pts(kx, y, 52, 52, 40), INK, 4, True, ea)
    if ea > 0.5: fruit(a, kx, y + 8, 0.36, rip=1.0, crown=0.75, spin=on * 2.0)

def D_end(a, sc, ln, lt, dur, t):
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.35)
    lp = ease((lt - (dur - 0.4)) / 0.25)
    draw_plant(a, t, 1.0, size=1.0, rip=1.0)
    ea = 1 - ease((lt - (dur - 0.72)) / 0.28)
    text("SOUNDS FAKE?", fit("SOUNDS FAKE?", 112), W / 2, 185, INK, ea)
    y = 355; x0, x1, hh = 210, 870, 120
    if ea > 0.01:
        POST.append(lambda b: toggle(b, on, ea))
        TXT.append(("FAKE", 54, (x0 + x1) / 2 + 60, y, (200, 90, 70), ea * (1 - on), 0, 800, 1.0))
        TXT.append(("TRUE", 54, (x0 + x1) / 2 - 60, y, WHITE, ea * ease((on - 0.5) / 0.4), 4, 800, 1.0))
    text("IT'S TRUE.", fit("IT'S TRUE.", 150), W / 2, 535, GOLD, ea * fade(lt, click + 0.3, 0.25), 7, 800, popv(lt, click + 0.3))
    text("Follow for more.", 70, W / 2, 660, INK, ea * fade(lt, click + 0.6, 0.25), 0, 700)
    if lp > 0:                                             # hook titles return for the loop
        text("THIS PINEAPPLE", fit("THIS PINEAPPLE", 112), W / 2, 200, INK, lp)
        text("TOOK 2 YEARS", fit("TOOK 2 YEARS", 156), W / 2, 365, GOLD, lp, 6)
        text("TO GROW.", 112, W / 2, 530, INK, lp)

CAMS = dict(hook=C_hook, loop=C_loop, ground=C_ground, grow=C_grow, one=C_one, flowers=C_flowers, fuse=C_fuse, end=C_end)
SCENES = dict(hook=D_hook, loop=D_loop, ground=D_ground, grow=D_grow, one=D_one, flowers=D_flowers, fuse=D_fuse, end=D_end)

# ---------- audio ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
rng = np.random.default_rng(21)
def marimba(f, gain=0.06, dur=0.9):
    s = np.arange(int(dur * SR)) / SR
    sig = np.sin(2 * np.pi * f * s) * np.exp(-s * 5) + 0.35 * np.sin(2 * np.pi * f * 3.93 * s) * np.exp(-s * 22) + 0.12 * np.sin(2 * np.pi * f * 9.2 * s) * np.exp(-s * 50)
    return (sig * np.minimum(1, s / 0.002)).astype(np.float32) * gain
NOTE = {n_: 261.63 * 2 ** (k / 12) for k, n_ in enumerate("C C# D D# E F F# G G# A A# B".split())}
def nf(nm, o=0): return NOTE[nm] * 2 ** o
BEAT = 60 / 112
PROG = [("C", "E", "G"), ("A", "C", "E"), ("F", "A", "C"), ("G", "B", "D")]
BASS = ["C", "A", "F", "G"]
for b in range(int(total / (BEAT * 4)) + 1):
    t0 = b * BEAT * 4; ch = PROG[b % 4]
    place(music, t0, marimba(nf(BASS[b % 4], -2), 0.13, 1.6)); place(music, t0 + BEAT * 2.5, marimba(nf(BASS[b % 4], -2), 0.08, 1.0))
    pat = [0, 1, 2, 1, 0, 2, 1, 2] if b % 2 == 0 else [2, 1, 0, 1, 2, 0, 1, 0]
    for k in range(8):
        if k in (3, 7) and b % 2: continue
        o = 1 if (k + b) % 5 == 0 else 0
        place(music, t0 + k * BEAT / 2, marimba(nf(ch[pat[k]], o), 0.045 if k % 2 else 0.06))
    for k in range(8):                                     # shaker
        s = np.arange(int(0.07 * SR)) / SR; z = rng.normal(0, 1, len(s)).astype(np.float32)
        z = z - np.convolve(z, np.ones(4) / 4, "same")
        place(music, t0 + k * BEAT / 2 + (0.02 if k % 2 else 0), z * np.exp(-s * 60), 0.03 if k % 2 else 0.018)
hook_hit(music, 0.3); place(music, 0.0, marimba(nf("C", 1), 0.1, 1.2)); place(music, 0.0, marimba(nf("G", 1), 0.07, 1.2))
def pop(at, f=900, gain=0.07):
    s = np.arange(int(0.09 * SR)) / SR
    place(music, at, (np.sin(2 * np.pi * (f + 900 * s / 0.09) * s) * np.exp(-s * 40)).astype(np.float32), gain)
def tick(at, gain=0.05):
    s = np.arange(int(0.03 * SR)) / SR; place(music, at, (rng.normal(0, 1, len(s)) * np.exp(-s * 300)).astype(np.float32), gain)
for i, ln in enumerate(spec["lines"]):
    st = ln["scene"]["type"]; s0 = ln["_s"]; dur = ln["_se"] - s0
    if i > 0: whoosh(music, s0, 0.08)
    if st == "ground":
        k = words[ln["_w0"] + 4][1]; place(music, k + 0.6, marimba(nf("C", -2), 0.12, 0.6)); tick(k + 0.62, 0.12)
    if st == "grow":
        for mo in range(25):
            at = s0 + 0.25 + (dur - 0.7) * mo / 24; tick(at, 0.04)
        place(music, s0 + 0.25 + (dur - 0.7) * 18 / 24, marimba(nf("E", 1), 0.08, 1.2))
    if st == "flowers":
        k = words[ln["_w0"] + 5][1] - 0.4
        for j in range(14): pop(k + j * 0.11 + rng.uniform(0, 0.04), 700 + 60 * j, 0.05)
    if st == "fuse":
        for j, nm in enumerate(("C", "E", "G", "C")): place(music, s0 + 0.3 + j * 0.12, marimba(nf(nm, 1 + (j == 3)), 0.08, 1.4))
    if st == "end":
        c = s0 + ln["scene"].get("click_at", 0.45); tick(c, 0.2)
        for j, nm in enumerate(("C", "E", "G", "C")): place(music, c + 0.2 + j * 0.07, marimba(nf(nm, 1 + (j == 3)), 0.08, 1.6))
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.4)

# ---------- lens + compositing ----------
STARTS = [ln["_s"] for ln in spec["lines"]]
_yy = np.arange(H, dtype=np.float32)
FOCUS_Y = 1040
TS = np.clip((np.abs(_yy - FOCUS_Y) - 230) / 600, 0, 1) ** 1.1
TS1 = np.clip(TS * 2, 0, 1)[:, None, None]; TS2 = np.clip(TS * 2 - 1, 0, 1)[:, None, None]
_vy, _vx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.30 * np.clip((((_vx - W / 2) / (W * 0.75)) ** 2 + ((_vy - H * 0.52) / (H * 0.7)) ** 2), 0, 1) ** 1.3)[..., None].astype(np.float32)

def lens(a, extra=0.0):
    f = a.astype(np.float32)
    small = cv2.resize(f, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    b1 = cv2.resize(cv2.GaussianBlur(small, (0, 0), 2.6), (W, H), interpolation=cv2.INTER_LINEAR)
    b2 = cv2.resize(cv2.GaussianBlur(small, (0, 0), 7.0), (W, H), interpolation=cv2.INTER_LINEAR)
    out = f + (b1 - f) * TS1
    out = out + (b2 - out) * TS2
    if extra > 0.01: out = out + (b2 - out) * extra
    lum = out.mean(axis=2, keepdims=True)
    out = lum + (out - lum) * 1.22                                    # toy-like saturation
    out = 255 * (out / 255) ** 0.96
    out = (out - 128) * 1.05 + 131
    return np.clip(out * VIG, 0, 255).astype(np.uint8)

groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 70
    f = F(size, 800)
    while f.getlength(" ".join(ws)) > W - 240 and size > 36: size -= 4; f = F(size, 800)
    tw_ = f.getlength(" ".join(ws)); x = (W - tw_) / 2; y = 1590
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([x - 44, y - 22 + 8, x + tw_ + 44 + 8, y + size + 28 + 8], radius=26, fill=(20, 50, 30, 90))
    d.rounded_rectangle([x - 44, y - 22, x + tw_ + 44, y + size + 28], radius=26, fill=CREAM + (255,), outline=INK + (255,), width=4)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]; wl = f.getlength(w)
        if on: d.rounded_rectangle([x - 10, y - 4, x + wl + 10, y + size + 10], radius=12, fill=GOLD + (255,))
        d.text((x, y - size * 0.1), w, font=f, fill=INK + (255,)); x += f.getlength(w + " ")

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    st = ln["scene"]["type"]
    CAMS[st](ln["scene"], ln, lt, dur, t)
    M = cam_M()
    a = warp(BACK, M, True)
    SCENES[st](a, ln["scene"], ln, lt, dur, t)
    fr = warp(FRONT, M, False).astype(np.float32)
    al = fr[..., 3:4] / 255
    a = (a.astype(np.float32) * (1 - al) + fr[..., :3] * al).astype(np.uint8)
    ex = 0.0
    for s in STARTS[1:]:                                    # rack-focus pull on cuts
        if s - 0.12 <= t < s + 0.2: ex = max(ex, 1 - abs(t - s) / (0.12 if t < s else 0.2))
    a = lens(a, ex)
    for fn in POST: fn(a)
    POST.clear()
    img = Image.fromarray(a)
    img = draw_texts(img)
    caption(img, t)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 9, W, H], fill=(200, 222, 206)); d.rectangle([0, H - 9, int(W * t / total), H], fill=GOLD)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=22); print(f"done {total:.1f}s")
