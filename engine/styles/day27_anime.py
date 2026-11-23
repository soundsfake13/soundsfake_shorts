"""Day 27 — ANIME IMPACT style (the mantis shrimp punch that makes water boil).
Cel-shaded anime action: a deep ultramarine sea painted as smooth anime background art (gradient water, soft
god-ray shafts, flat teal reef silhouettes with pink coral), a cel-shaded peacock mantis shrimp built from inked
capsules and rounded plates (flat base colour + one hard shadow band + rim highlight, thick ink outlines), whose
two-link smasher arm really folds and fires. Anime grammar everywhere: radial concentration lines boiling at 12 fps,
horizontal speed streaks, smear frames (ghost clubs) on every strike, screen shake, two-tone/inverted IMPACT frames
on the big hits, starburst flashes, shock rings, cavitation bubbles with crescent highlights, power-up aura.
Type: Dela Gothic One (heavy, slanted, white/yellow with ink stroke and a hot-pink extrusion) + Rajdhani Bold for
HUD stat cards. Cuts are white diagonal slash wipes. Ending: a slanted anime toggle FAKE -> TRUE whose knob is the
pink club; it slams across with a smear + impact frame, then dissolves back into the hook for the loop.
Music: original 150 bpm E-minor action cue (kick/snare/hats, driving bass, synth stabs) + booms on every hit.
Usage: python3 engine/styles/day27_anime.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]

# ---------- palette & fonts ----------
INK = (12, 10, 28); WHITE = (252, 252, 255); PINK = (255, 46, 122); YEL = (255, 224, 58)
CYAN = (80, 236, 255); NAVY = (10, 14, 52); DEEP = (22, 34, 110); TEAL = (26, 128, 176)
GREEN = (58, 196, 118); GSH = (22, 122, 84); GHI = (176, 252, 196)
ORANGE = (255, 132, 40); OSH = (196, 70, 20); CLUB = (255, 72, 120); CSH = (186, 26, 82)
BLUE = (62, 112, 255)
_F = {}
def F(kind, s):
    k = (kind, int(s))
    if k not in _F:
        _F[k] = ImageFont.truetype(f"{FONTS}/{'DelaGothicOne-Regular.ttf' if kind == 'd' else 'Rajdhani-Bold.ttf'}", int(s))
    return _F[k]

# ---------- text ----------
_T = {}
def title(text, size, fill=WHITE, ext=PINK, skew=0.16, maxw=1000):
    k = (text, size, fill, ext, skew, maxw)
    if k in _T: return _T[k]
    f = F("d", size)
    while f.getlength(text) + size * 0.5 > maxw and size > 40: size -= 4; f = F("d", size)
    sw = max(4, int(size * 0.085)); ex = max(5, int(size * 0.07))
    bb = f.getbbox(text, stroke_width=sw)
    w = bb[2] - bb[0] + ex + 4; h = bb[3] - bb[1] + ex + 4
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ox, oy = -bb[0] + 2, -bb[1] + 2
    for k2 in range(ex, 0, -2):
        d.text((ox + k2, oy + k2), text, font=f, fill=ext, stroke_width=sw, stroke_fill=INK)
    d.text((ox, oy), text, font=f, fill=fill, stroke_width=sw, stroke_fill=INK)
    w2 = int(w + skew * h)
    im = im.transform((w2, h), Image.AFFINE, (1, skew, -skew * h, 0, 1, 0), resample=Image.BICUBIC)
    _T[k] = im; return im

def put(O, im, cx, cy, sc=1.0, alpha=1.0):
    if sc != 1.0:
        im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BICUBIC)
    if alpha < 1.0:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    O.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def slam(O, text, size, cx, cy, lt, at=0.0, fill=WHITE, ext=PINK):
    """anime title slam: big -> 1.0 in 0.14 s with a tiny overshoot; fully drawn if at<0 (frame-0 safe)."""
    u = (lt - at) / 0.16
    if u < 0: return
    sc = 1.0 if at < 0 else 1 + 0.9 * (1 - eout(min(1, u))) - 0.06 * math.sin(math.pi * min(1, max(0, (u - 1) / 0.8)))
    put(O, title(text, size, fill, ext), cx, cy, sc, min(1, u * 3) if at >= 0 else 1)

def card(O, label, value, cx, cy, w=560, h=190, a=1.0, col=CYAN):
    """slanted HUD stat card (Rajdhani label, Dela Gothic value)."""
    L = Image.new("RGBA", (w + 80, h + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    sk = 36
    d.polygon([(sk + 10, 10), (w + 60, 10), (w + 60 - sk, h + 10), (10, h + 10)], fill=INK + (235,), outline=col + (255,), width=6)
    lw = F("r", 40).getlength(label) + 40
    d.polygon([(sk + 10, 10), (sk + 10 + lw, 10), (sk - 10 + lw, 54), (sk - 10, 54)], fill=col + (255,))
    d.text((sk + 26, 12), label, font=F("r", 40), fill=INK)
    f = F("d", min(96, h - 90))
    while f.getlength(value) > w - 90: f = F("d", f.size - 4)
    d.text((w / 2 + 30, 60 + (h - 50) / 2), value, anchor="mm", font=f, fill=YEL, stroke_width=4, stroke_fill=INK)
    put(O, L, cx, cy, 1.0, a)

# ---------- background art ----------
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
def build_sea():
    v = YY / H
    top = np.array((40, 120, 190), np.float32); mid = np.array(DEEP, np.float32); bot = np.array(NAVY, np.float32)
    g = np.where((v < 0.45)[..., None], top + (mid - top) * (v / 0.45)[..., None],
                 mid + (bot - mid) * ((v - 0.45) / 0.55)[..., None])
    return g.astype(np.float32)
SEA = build_sea()
def build_rays():
    m = np.zeros((H, W), np.float32)
    for k, (x0, wd, a) in enumerate(((140, 90, 0.5), (380, 150, 0.35), (640, 70, 0.45), (860, 120, 0.3), (1020, 60, 0.4))):
        cx = x0 + (YY * 0.32); d = np.abs(XX - cx) / (wd * (1 + YY / H))
        m += a * np.clip(1 - d, 0, 1) ** 1.6 * np.clip(1 - YY / (H * 0.85), 0, 1)
    return m
RAYS = build_rays()
def build_reef():
    L = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    r = np.random.default_rng(27)
    pts = [(0, 2 * H)] + [(x, 2 * (1700 - 90 * math.sin(x / 260) - 60 * math.sin(x / 97 + 1) - 40 * r.random())) for x in range(0, 2 * W + 60, 60)] + [(2 * W, 2 * H)]
    d.polygon(pts, fill=(14, 40, 92, 255))
    pts2 = [(0, 2 * H)] + [(x, 2 * (1800 - 50 * math.sin(x / 180 + 2) - 30 * r.random())) for x in range(0, 2 * W + 60, 60)] + [(2 * W, 2 * H)]
    d.polygon(pts2, fill=(10, 24, 62, 255))
    for cx, cy, s in ((150, 1640, 1.0), (930, 1600, 0.8), (520, 1700, 0.6)):   # flat coral fans
        for j in range(7):
            a = math.radians(-150 + j * 20)
            d.line([(2 * cx, 2 * cy), (2 * (cx + 120 * s * math.cos(a)), 2 * (cy + 120 * s * math.sin(a)))], fill=(200, 60, 120, 255), width=int(18 * s))
            d.ellipse([2 * (cx + 120 * s * math.cos(a)) - 18 * s, 2 * (cy + 120 * s * math.sin(a)) - 18 * s,
                       2 * (cx + 120 * s * math.cos(a)) + 18 * s, 2 * (cy + 120 * s * math.sin(a)) + 18 * s], fill=(240, 90, 150, 255))
    return L.resize((W, H), Image.LANCZOS)
REEF = build_reef()
MOTES = np.random.default_rng(3).uniform(0, 1, (46, 4))

def sea_bg(t, burst=None, tint=0.0):
    rays = RAYS * (0.85 + 0.15 * math.sin(t * 1.3))
    g = SEA + rays[..., None] * np.array((90, 150, 140), np.float32)
    if burst is not None:
        bx, by, br, bc = burst
        d = np.sqrt((XX - bx) ** 2 + (YY - by) ** 2) / br
        g = g + np.clip(1 - d, 0, 1)[..., None] ** 1.5 * np.array(bc, np.float32)
    if tint: g = g * (1 - tint) + np.array(PINK, np.float32) * tint
    im = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert("RGBA")
    im.alpha_composite(REEF)
    d = ImageDraw.Draw(im)
    for x, y, sp, sz in MOTES:
        yy = (y * H - t * (30 + 50 * sp)) % H; xx = x * W + 14 * math.sin(t + x * 9)
        r = 3 + 7 * sz
        d.ellipse([xx - r, yy - r, xx + r, yy + r], outline=(170, 230, 255, 140), width=2)
    return im

# ---------- anime effects ----------
_RL = {}
def radial_lines(O, cx, cy, rin, t, col=WHITE, n=110, alpha=210, seedb=0):
    k = (int(cx), int(cy), int(rin), int(t * 12) % 4 + seedb * 10, col, alpha)
    if k not in _RL:
        if len(_RL) > 40: _RL.clear()
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        r = np.random.default_rng(k[3] * 7 + 1)
        for i in range(n):
            a = 2 * math.pi * (i + r.random() * 0.8) / n; wa = 0.004 + 0.016 * r.random()
            ri = rin * (0.85 + 0.6 * r.random()); ro = 2400
            p = [(cx + ri * math.cos(a), cy + ri * math.sin(a)),
                 (cx + ro * math.cos(a - wa), cy + ro * math.sin(a - wa)), (cx + ro * math.cos(a + wa), cy + ro * math.sin(a + wa))]
            d.polygon(p, fill=col + (alpha,))
        _RL[k] = L
    O.alpha_composite(_RL[k])

STREAKS = np.random.default_rng(11).uniform(0, 1, (70, 4))
def speed_streaks(O, t, speed=3200, col=WHITE, alpha=200, y0=0, y1=H):
    d = ImageDraw.Draw(O)
    for y, x, ln, wd in STREAKS:
        yy = y0 + y * (y1 - y0); L = 200 + 700 * ln; th = 2 + 7 * wd
        xx = W + 400 - ((x * 3000 + t * speed * (0.6 + ln)) % (W + 1200))
        d.polygon([(xx, yy), (xx + L, yy - th / 2), (xx + L, yy + th / 2)], fill=col + (alpha,))

def starburst(O, cx, cy, r, pts=8, rot=0.0, fill=WHITE, inner=0.35, outline=True):
    d = ImageDraw.Draw(O); P = []
    for i in range(pts * 2):
        a = rot + math.pi * i / pts; rr = r * (1 if i % 2 == 0 else inner) * (1 if i % 4 else 1.0)
        P.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    if outline: d.polygon(P, fill=fill + (255,), outline=INK + (255,), width=8)
    else: d.polygon(P, fill=fill + (255,))

def ring(O, cx, cy, r, w, col=WHITE, a=255):
    ImageDraw.Draw(O).ellipse([cx - r, cy - r, cx + r, cy + r], outline=col + (int(a),), width=int(max(1, w)))

def bubble(d, x, y, r, a=255):
    d.ellipse([x - r, y - r, x + r, y + r], fill=(150, 235, 255, int(a * 0.35)), outline=WHITE + (int(a),), width=max(2, int(r * 0.12)))
    if r > 6:
        d.arc([x - r * 0.68, y - r * 0.68, x + r * 0.68, y + r * 0.68], 200, 260, fill=WHITE + (int(a),), width=max(2, int(r * 0.16)))

def aura(im, col=CYAN, grow=14, blur=10, a=0.9):
    A = np.array(im.getchannel("A"))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (grow * 2 + 1, grow * 2 + 1))
    m = cv2.GaussianBlur(cv2.dilate(A, k), (0, 0), blur).astype(np.float32) * a
    L = np.zeros(A.shape + (4,), np.uint8); L[..., :3] = col; L[..., 3] = np.clip(m, 0, 255)
    return Image.fromarray(L)

# ---------- cel-shaded mantis shrimp (local 1000x560, drawn at 2x) ----------
SS = 2; LW, LH = 1000, 560; OW = 7
def yc(x): return 330 - 50 * math.sin(math.pi * (x - 100) / 560)
def capsule(d, p0, p1, r0, r1, fill, ow=OW, shade=None):
    def poly(R0, R1):
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dy) or 1; nx, ny = -dy / L, dx / L
        return [(SS * (p0[0] + nx * R0), SS * (p0[1] + ny * R0)), (SS * (p1[0] + nx * R1), SS * (p1[1] + ny * R1)),
                (SS * (p1[0] - nx * R1), SS * (p1[1] - ny * R1)), (SS * (p0[0] - nx * R0), SS * (p0[1] - ny * R0))]
    for R0, R1, c in ((r0 + ow, r1 + ow, INK), (r0, r1, fill)):
        d.polygon(poly(R0, R1), fill=c)
        for (px, py), R in ((p0, R0), (p1, R1)): d.ellipse([SS * (px - R), SS * (py - R), SS * (px + R), SS * (py + R)], fill=c)
    if shade:   # hard cel shadow on the lower side
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dy) or 1; nx, ny = -dy / L, dx / L
        if ny < 0: nx, ny = -nx, -ny
        q0 = (p0[0] + nx * r0 * 0.25, p0[1] + ny * r0 * 0.25); q1 = (p1[0] + nx * r1 * 0.25, p1[1] + ny * r1 * 0.25)
        d.polygon([(SS * q0[0], SS * q0[1]), (SS * q1[0], SS * q1[1]), (SS * (p1[0] + nx * r1 * 0.92), SS * (p1[1] + ny * r1 * 0.92)),
                   (SS * (p0[0] + nx * r0 * 0.92), SS * (p0[1] + ny * r0 * 0.92))], fill=shade)

def plate(d, box, rad, fill, shade, hi, spots=()):
    x0, y0, x1, y1 = box
    d.rounded_rectangle([SS * (x0 - OW), SS * (y0 - OW), SS * (x1 + OW), SS * (y1 + OW)], radius=SS * (rad + OW), fill=INK)
    d.rounded_rectangle([SS * x0, SS * y0, SS * x1, SS * y1], radius=SS * rad, fill=fill)
    sy = y0 + (y1 - y0) * 0.58
    d.rounded_rectangle([SS * (x0 + 4), SS * sy, SS * (x1 - 4), SS * (y1 - 3)], radius=SS * max(4, rad - 6), fill=shade)
    d.line([(SS * (x0 + rad * 0.7), SS * (y0 + 9)), (SS * (x1 - rad * 0.9), SS * (y0 + 9))], fill=hi, width=SS * 6)
    for sx, sy2, r in spots:
        d.ellipse([SS * (sx - r), SS * (sy2 - r), SS * (sx + r), SS * (sy2 + r)], fill=GSH)

def arm_pose(s):
    s = max(0.0, min(1.0, s))
    a1 = math.radians(60 + (5 - 60) * s); a2 = math.radians(215 + (0 - 215) * s)
    p0 = (660, 318); p1 = (p0[0] + 105 * math.cos(a1), p0[1] + 105 * math.sin(a1))
    p2 = (p1[0] + 118 * math.cos(a2), p1[1] + 118 * math.sin(a2))
    return p0, p1, p2

_SH = {}
def shrimp(strike=0.0, ghosts=(), scale=1.0):
    """RGBA image of the shrimp, local box LWxLH scaled by `scale`. ghosts = earlier strike values for smear."""
    k = (round(strike, 2), tuple(round(g, 2) for g in ghosts), round(scale, 3))
    if k in _SH: return _SH[k]
    if len(_SH) > 120: _SH.clear()
    im = Image.new("RGBA", (LW * SS, LH * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    # far antenna
    d.line([(SS * x, SS * y) for x, y in ((705, 222), (790, 190), (880, 175), (965, 190))], fill=INK, width=SS * 7, joint="curve")
    # tail fan
    bx, by = 140, yc(140)
    for ang, col, L in ((150, BLUE, 105), (205, BLUE, 105), (165, ORANGE, 118), (190, ORANGE, 118), (178, GREEN, 120)):
        a = math.radians(ang); tip = (bx + L * math.cos(a), by + L * math.sin(a))
        capsule(d, (bx, by), tip, 12, 22, col, shade=OSH if col == ORANGE else (30, 60, 190) if col == BLUE else GSH)
    # swimmerets + legs (behind body)
    for x in (250, 300, 350, 400):
        y = yc(x) + 62; capsule(d, (x, y), (x - 26, y + 46), 9, 14, (255, 150, 160), ow=5)
    for x in (470, 515, 560):
        y = yc(x) + 60; capsule(d, (x, y), (x - 10, y + 52), 8, 7, ORANGE, ow=5, shade=OSH); capsule(d, (x - 10, y + 52), (x - 34, y + 80), 7, 5, ORANGE, ow=5)
    # body segments tail -> head
    xs = np.linspace(170, 560, 8)
    for i, x in enumerate(xs):
        h = 96 + 70 * math.sin(math.pi * min(1, (x - 120) / 520) * 0.85)
        y = yc(x); spots = ((x - 8, y - h * 0.2, 5), (x + 14, y + h * 0.05, 4)) if i % 2 else ((x + 6, y - h * 0.1, 5),)
        plate(d, (x - 40, y - h / 2, x + 40, y + h / 2 - 6), 26, GREEN, GSH, GHI, spots)
        d.line([(SS * (x - 34), SS * (y + h * 0.05)), (SS * (x - 34), SS * (y + h * 0.36))], fill=INK, width=SS * 3)
    # carapace / head
    hp = [(560, 204), (640, 186), (700, 204), (718, 242), (706, 300), (650, 334), (560, 334)]
    d.polygon([(SS * x, SS * y) for x, y in hp], fill=INK)
    hp2 = [(566, 212), (640, 194), (694, 210), (709, 243), (699, 294), (648, 325), (566, 326)]
    d.polygon([(SS * x, SS * y) for x, y in hp2], fill=GREEN)
    d.polygon([(SS * x, SS * y) for x, y in ((566, 282), (705, 270), (699, 294), (648, 325), (566, 326))], fill=GSH)
    d.line([(SS * 584, SS * 214), (SS * 650, SS * 200), (SS * 690, SS * 214)], fill=GHI, width=SS * 6, joint="curve")
    for sx, sy, r in ((600, 245, 7), (630, 232, 5), (660, 250, 6), (615, 272, 4)):
        d.ellipse([SS * (sx - r), SS * (sy - r), SS * (sx + r), SS * (sy + r)], fill=GSH)
    # antennal scale + near antenna
    capsule(d, (712, 236), (790, 222), 9, 15, ORANGE, ow=5, shade=OSH)
    d.line([(SS * x, SS * y) for x, y in ((712, 228), (800, 214), (900, 225), (985, 262))], fill=INK, width=SS * 7, joint="curve")
    # eyes on stalks (back then front): big eye with mid-band + anime highlight
    for base, tip, rx, ry, dark in (((690, 214), (712, 128), 30, 22, True), ((700, 214), (748, 142), 36, 26, False)):
        capsule(d, base, tip, 10, 12, GSH if dark else GREEN, ow=6)
        ex, ey = tip
        d.ellipse([SS * (ex - rx - 7), SS * (ey - ry - 7), SS * (ex + rx + 7), SS * (ey + ry + 7)], fill=INK)
        d.ellipse([SS * (ex - rx), SS * (ey - ry), SS * (ex + rx), SS * (ey + ry)], fill=(60, 170, 235) if dark else (96, 214, 255))
        d.rectangle([SS * (ex - rx + 3), SS * (ey - 6), SS * (ex + rx - 3), SS * (ey + 6)], fill=INK)
        d.rectangle([SS * (ex - rx + 6), SS * (ey - 2), SS * (ex + rx - 6), SS * (ey + 2)], fill=YEL)
        if not dark:
            d.ellipse([SS * (ex - 18), SS * (ey - 20), SS * (ex - 4), SS * (ey - 9)], fill=WHITE)
            d.ellipse([SS * (ex + 10), SS * (ey + 10), SS * (ex + 17), SS * (ey + 17)], fill=WHITE)
    # smear ghosts of the club
    if ghosts:
        G = Image.new("RGBA", im.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(G)
        for j, gs in enumerate(ghosts):
            _, g1, g2 = arm_pose(gs); a = int(90 + 120 * (j + 1) / len(ghosts))
            for R, c in ((40, WHITE + (a,)),):
                gd.ellipse([SS * (g2[0] - R), SS * (g2[1] - R), SS * (g2[0] + R), SS * (g2[1] + R)], fill=c)
                gd.line([(SS * g1[0], SS * g1[1]), (SS * g2[0], SS * g2[1])], fill=c, width=SS * 40)
        im.alpha_composite(G)
    # smasher arm
    p0, p1, p2 = arm_pose(strike)
    capsule(d, p0, p1, 27, 23, (60, 200, 170), shade=(24, 130, 120))
    capsule(d, p1, p2, 22, 30, CLUB, shade=CSH)
    R = 38; d.ellipse([SS * (p2[0] - R - OW), SS * (p2[1] - R - OW), SS * (p2[0] + R + OW), SS * (p2[1] + R + OW)], fill=INK)
    d.ellipse([SS * (p2[0] - R), SS * (p2[1] - R), SS * (p2[0] + R), SS * (p2[1] + R)], fill=CLUB)
    d.chord([SS * (p2[0] - R), SS * (p2[1] - R), SS * (p2[0] + R), SS * (p2[1] + R)], 10, 170, fill=CSH)
    d.ellipse([SS * (p2[0] - 20), SS * (p2[1] - 26), SS * (p2[0] - 2), SS * (p2[1] - 12)], fill=(255, 200, 220))
    out = im.resize((int(LW * scale), int(LH * scale)), Image.LANCZOS)
    _SH[k] = out; return out

def club_tip(ox, oy, s, scale=1.0):
    _, _, p2 = arm_pose(s); return ox + p2[0] * scale, oy + p2[1] * scale

def strike_curve(lt, period, t0=0.0):
    """repeating punch: hold coiled, fire in 0.06 s, hold, retract. Returns (s, ghosts, hit_age)."""
    u = (lt - t0) % period; k = (lt - t0) // period
    if lt < t0: return 0.0, (), 9
    if u < 0.06: s = eout(u / 0.06); return s, (max(0, s - 0.5), max(0, s - 0.3), max(0, s - 0.15)), 9
    if u < period * 0.55: return 1.0, (), u - 0.06
    s = 1 - ease((u - period * 0.55) / (period * 0.4)); return s, (), u - 0.06

def wstart(ln, i): return words[min(ln["_w0"] + i, ln["_w1"] - 1)][1] - ln["_s"]

# ---------- scenes: fn(ln, lt, dur, t) -> (image RGBA, fx dict) ----------
def bubbles_cloud(O, cx, cy, n, spread, t, grow=1.0, seed=1, a=255):
    r = np.random.default_rng(seed); d = ImageDraw.Draw(O)
    for i in range(n):
        ang = r.uniform(-1.4, 1.4); dist = spread * r.random() ** 0.7
        x = cx + dist * math.cos(ang) + 6 * math.sin(t * 9 + i); y = cy + dist * math.sin(ang) * 0.9 + 6 * math.cos(t * 7 + i * 2)
        rr = (8 + 34 * r.random() ** 2) * grow * (0.85 + 0.15 * math.sin(t * 14 + i))
        bubble(d, x, y, rr, a)

def S_hook(ln, lt, dur, t):
    ox, oy = -120, 900
    if lt < 0.5: s, gh, age = 1.0, (), 9
    elif lt < 0.8: s, gh, age = 1 - ease((lt - 0.5) / 0.3), (), 9
    else: s, gh, age = strike_curve(lt, 1.25, 0.85)
    tx, ty = club_tip(ox, oy, s)
    hot = s > 0.95
    bg = sea_bg(t, burst=(tx + 40, ty, 700, (255, 60, 140)) if hot else None)
    radial_lines(bg, tx + 40, ty, 260, t, WHITE, alpha=200)
    if hot:
        starburst(bg, tx + 70, ty, 150 + 20 * math.sin(t * 30), 9, t * 2, YEL)
        starburst(bg, tx + 70, ty, 80, 7, -t * 3, WHITE, outline=False)
        bubbles_cloud(bg, tx + 90, ty, 22, 190, t, 1.0, seed=2)
    sh = shrimp(s, gh); bg.alpha_composite(sh, (ox, oy))
    slam(bg, "THIS SHRIMP", 112, W / 2, 230, lt, -1)
    slam(bg, "PUNCHES", 170, W / 2, 400, lt, -1, YEL)
    slam(bg, "SO HARD,", 150, W / 2, 570, lt, -1)
    slam(bg, "WATER BOILS.", 132, W / 2, 740, lt, -1, CYAN, INK)
    shake = 22 * math.exp(-max(0, age) * 9) if age < 1 else 0
    if lt < 0.4: shake = max(shake, 18 * math.exp(-lt * 8))
    return bg, dict(shake=shake, impact=(0.0 <= age < 0.1 and lt > 0.85))

def S_charge(ln, lt, dur, t):
    sc = 1.45 + 0.12 * ease(lt / dur); ox, oy = W / 2 - 640 * sc, 1010 - 300 * sc
    bg = sea_bg(t, tint=0.0)
    radial_lines(bg, W / 2, 900, 520, t, (130, 230, 255), alpha=120)
    sh = shrimp(0.0, (), round(sc, 2))
    au = aura(sh, CYAN if int(t * 12) % 2 else (200, 255, 255), 16, 12, 0.85)
    jx = 4 * math.sin(t * 40)
    bg.alpha_composite(au, (int(ox + jx), int(oy))); bg.alpha_composite(sh, (int(ox + jx), int(oy)))
    d = ImageDraw.Draw(bg); r = np.random.default_rng(5)
    for i in range(26):   # rising energy sparks
        x = r.uniform(80, W - 80); sp = r.uniform(200, 500); y = 1500 - ((lt * sp + r.uniform(0, 1400)) % 1400)
        d.line([(x, y), (x, y + 40)], fill=CYAN + (230,), width=5)
    ex, ey = ox + 748 * sc, oy + 142 * sc
    k = (lt - 0.9) / 0.5
    if 0 < k < 1:
        starburst(bg, ex - 10, ey - 12, 70 * math.sin(math.pi * k), 4, 0.2, WHITE, 0.18, outline=False)
    slam(bg, "THE WEIRD PART?", 104, W / 2, 230, lt, 0.0)
    slam(bg, "AFTER THE PUNCH.", 96, W / 2, 380, lt, wstart(ln, 5), YEL)
    return bg, dict(shake=3 if lt > 0.2 else 0)

def S_speed(ln, lt, dur, t):
    bg = sea_bg(t)
    speed_streaks(bg, t, 3600, WHITE, 170, 760, 1500)
    ox, oy = -170, 930
    s, gh, age = strike_curve(lt, 1.1, 0.35)
    sh = shrimp(s, gh); bg.alpha_composite(sh, (ox + int(8 * math.sin(t * 50)), oy))
    tx, ty = club_tip(ox, oy, s)
    if age < 0.25:
        starburst(bg, tx + 50, ty, 110 * (1 - age / 0.25) + 30, 8, t, YEL)
    v = int(80 * ease(min(1, max(0, lt - wstart(ln, 2)) / 0.8)))
    slam(bg, f"{v} KM/H", 190, W / 2, 420, lt, 0.0, YEL)
    if lt > wstart(ln, 3): card(bg, "CLUB SPEED", "≈ 23 m/s", W / 2, 690, 560, 170, min(1, (lt - wstart(ln, 3)) * 5))
    return bg, dict(shake=14 * math.exp(-age * 10) if age < 1 else 0, impact=(0 <= age < 0.07))

def S_gforce(ln, lt, dur, t):
    bg = sea_bg(t, burst=(W / 2, 700, 900, (110, 40, 160)))
    radial_lines(bg, W / 2, 700, 360, t, WHITE, alpha=190, seedb=2)
    a = wstart(ln, 6)
    u = min(1, max(0, (lt - a + 0.4) / 0.7)); v = int(round(10000 * eout(u), -2))
    slam(bg, "UP TO", 90, W / 2, 420, lt, 0.0, WHITE)
    slam(bg, f"{v:,}", 230, W / 2, 640, lt, 0.05, YEL)
    slam(bg, "× GRAVITY", 120, W / 2, 860, lt, 0.1, CYAN, INK)
    # power gauge
    x0, x1, y = 120, W - 120, 1080; segs = 14; fill = u * segs
    d = ImageDraw.Draw(bg)
    d.polygon([(x0 - 14, y - 52), (x1 + 34, y - 52), (x1 + 14, y + 52), (x0 - 34, y + 52)], fill=INK + (240,), outline=WHITE + (255,), width=5)
    for i in range(segs):
        sx = x0 + (x1 - x0) * i / segs; ex = sx + (x1 - x0) / segs - 10
        col = (CYAN if i < 6 else YEL if i < 11 else PINK) + ((255,) if i < fill else (50,))
        d.polygon([(sx + 12, y - 36), (ex + 12, y - 36), (ex - 4, y + 36), (sx - 4, y + 36)], fill=col)
    if u >= 1:
        k = lt - (a + 0.3);
        if k > 0:
            starburst(bg, x1 + 10, y, 120 + 40 * math.exp(-k * 6), 10, t * 3, PINK)
            put(bg, title("MAX!", 80, WHITE, PINK), x1 - 40, y - 2)
    ox, oy, sc = -60, 1200, 0.62
    s, gh, age = strike_curve(lt, 0.9, 0.3)
    bg.alpha_composite(shrimp(s, gh, sc), (ox, oy))
    imp = (u >= 1 and 0 <= lt - (a + 0.3) < 0.07)
    return bg, dict(shake=(16 * math.exp(-(lt - a - 0.3) * 8) if lt > a + 0.3 else 2), impact=imp)

def S_boil(ln, lt, dur, t):
    bg = sea_bg(t)
    d = ImageDraw.Draw(bg)
    for i in range(0, H, 6):  # slow-mo scanline sheen
        pass
    ox, oy, sc = -260, 760, 1.3
    s = 0.55 + 0.43 * ease(lt / (dur * 0.9))
    sh = shrimp(s, (max(0, s - 0.08), max(0, s - 0.04)), sc)
    bg.alpha_composite(sh, (ox, oy))
    tx, ty = club_tip(ox, oy, s, sc)
    g = min(1, max(0, (lt - wstart(ln, 7) + 0.4) / 1.0))
    if g > 0:
        bubbles_cloud(bg, tx + 70, ty, int(8 + 26 * g), 60 + 230 * g, t * 0.3, 0.6 + 0.8 * g, seed=4)
    sm = title("SLOW MOTION", 60, WHITE, BLUE, 0.1); put(bg, sm, 120 + sm.width / 2, 160)
    ImageDraw.Draw(bg).ellipse([66, 144, 98, 176], fill=(255, 60, 60, 255 if int(t * 2) % 2 else 90))
    slam(bg, "THE WATER", 120, W / 2, 430, lt, 0.0)
    if lt > wstart(ln, 6) - 0.1: slam(bg, "BOILS!", 220, W / 2, 640, lt, wstart(ln, 6) - 0.1, CYAN, PINK)
    return bg, dict(shake=2)

def S_collapse(ln, lt, dur, t):
    c = wstart(ln, 3) + 0.25
    cx, cy = W / 2, 820
    k = lt - c
    bg = sea_bg(t, burst=(cx, cy, 1000, (255, 210, 120)) if k > 0 else None, tint=0.0)
    if k < 0:
        r = 300 * (1 - 0.75 * ease(lt / c)) + 6 * math.sin(t * 30)
        radial_lines(bg, cx, cy, r + 120, t, (180, 240, 255), alpha=150)
        d = ImageDraw.Draw(bg)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(140, 230, 255, 90), outline=WHITE + (255,), width=12)
        d.arc([cx - r * 0.75, cy - r * 0.75, cx + r * 0.75, cy + r * 0.75], 200, 255, fill=WHITE + (255,), width=18)
        d.ellipse([cx + r * 0.35, cy + r * 0.3, cx + r * 0.5, cy + r * 0.45], fill=WHITE + (220,))
    else:
        radial_lines(bg, cx, cy, 120, t, WHITE, alpha=230, seedb=3)
        for j in range(3):
            rr = (k - j * 0.18) * 1500
            if rr > 0: ring(bg, cx, cy, rr, 26 * math.exp(-k * 2), WHITE, 255 * max(0, 1 - rr / 1600))
        starburst(bg, cx, cy, 230 + 30 * math.sin(t * 25), 12, t * 2, YEL, 0.4)
        starburst(bg, cx, cy, 120, 8, -t * 3, WHITE, 0.3, outline=False)
        r2 = np.random.default_rng(9); d = ImageDraw.Draw(bg)
        for i in range(30):   # spray of micro-bubbles
            a = r2.uniform(0, 2 * math.pi); dist = 150 + k * r2.uniform(300, 900)
            bubble(d, cx + dist * math.cos(a), cy + dist * math.sin(a), r2.uniform(6, 20), int(255 * max(0, 1 - k / 2)))
    for wi, txt, x, y, col, ex in ((6, "BANG!", 290, 330, WHITE, PINK), (7, "HEAT!", 790, 1220, ORANGE, INK), (10, "LIGHT!", 560, 1390, YEL, PINK)):
        a = wstart(ln, wi) - 0.05
        if lt > a and k > 0: slam(bg, txt, 140, x, y, lt, a, col, ex)
    if k < 0: slam(bg, "THEN...", 120, W / 2, 300, lt, 0.0, WHITE, BLUE)
    imp = 0 <= k < 0.1
    return bg, dict(shake=26 * math.exp(-k * 6) if k > 0 else 4 * (lt / c), impact=imp, flash=max(0, 1 - k / 0.12) if 0 <= k < 0.12 else 0)

CRACK = None
def build_crack(cx, cy):
    r = np.random.default_rng(27); segs = []
    for i in range(13):
        a = 2 * math.pi * i / 13 + r.uniform(-0.15, 0.15); x, y = cx, cy; L = 0
        pts = [(x, y)]
        while L < 900:
            st = r.uniform(50, 110); a += r.uniform(-0.3, 0.3); x += st * math.cos(a); y += st * math.sin(a); L += st
            pts.append((x, y))
            if r.random() < 0.25:
                b = a + r.choice([-1, 1]) * r.uniform(0.5, 0.9); segs.append((L, [(x, y), (x + 120 * math.cos(b), y + 120 * math.sin(b))]))
        segs.append((0, pts))
    rings = [(rr, [(cx + rr * (1 + 0.15 * r.random()) * math.cos(2 * math.pi * j / 13), cy + rr * (1 + 0.15 * r.random()) * math.sin(2 * math.pi * j / 13)) for j in range(14)]) for rr in (70, 170, 320)]
    return segs, rings

def S_glass(ln, lt, dur, t):
    global CRACK
    bg = sea_bg(t)
    ox, oy = -120, 860
    hit = 0.55
    if lt < hit - 0.08: s, gh = 0.0, ()
    elif lt < hit: s = eout((lt - hit + 0.08) / 0.08); gh = (max(0, s - 0.5), max(0, s - 0.25))
    else: s, gh = 1.0, ()
    bg.alpha_composite(shrimp(s, gh), (ox, oy))
    tx, ty = club_tip(ox, oy, 1.0)
    cx, cy = tx + 40, ty
    G = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(G)
    d.rectangle([0, 0, W, H], fill=(170, 230, 255, 28))
    for x0, wd in ((-200, 140), (60, 50), (700, 90)):   # glass reflections
        d.polygon([(x0, H), (x0 + wd, H), (x0 + wd + 900, 0), (x0 + 900, 0)], fill=(255, 255, 255, 34))
    k = lt - hit
    if k > 0:
        if CRACK is None: CRACK = build_crack(cx, cy)
        segs, rings = CRACK; grow = 1200 * eout(min(1, k / 0.35))
        for L0, pts in segs:
            acc = L0; out = [pts[0]]
            for p, q in zip(pts[:-1], pts[1:]):
                sl = math.hypot(q[0] - p[0], q[1] - p[1])
                if acc + sl <= grow: out.append(q); acc += sl
                else:
                    u = max(0, (grow - acc) / sl); out.append((p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u)); break
            if len(out) > 1:
                d.line(out, fill=INK + (200,), width=9, joint="curve"); d.line(out, fill=WHITE + (255,), width=4, joint="curve")
        for rr, pts in rings:
            if grow > rr * 1.3:
                d.line(pts, fill=INK + (180,), width=7); d.line(pts, fill=WHITE + (240,), width=3)
        if k < 0.3: starburst(G, cx, cy, 160 * (1 - k / 0.3) + 40, 10, 0.3, WHITE, 0.3)
    bg.alpha_composite(G)
    if k > 0: slam(bg, "CRACK!", 200, W / 2, 330, lt, hit, WHITE, PINK)
    else: slam(bg, "EVEN GLASS?", 110, W / 2, 330, lt, 0.0, YEL)
    if lt > wstart(ln, 4) - 0.1: card(bg, "TARGET", "AQUARIUM GLASS", W / 2, 560, 760, 160, min(1, (lt - wstart(ln, 4) + 0.1) * 5), PINK)
    return bg, dict(shake=24 * math.exp(-k * 8) if k > 0 else 0, impact=0 <= k < 0.07)

def S_end(ln, lt, dur, t):
    c = ln["scene"].get("click_at", 0.45)
    on = lt > c
    bg = sea_bg(t, burst=(W / 2, 900, 900, (255, 70, 150)) if on else None)
    radial_lines(bg, W / 2, 900, 420, t, YEL if on else WHITE, alpha=170 if on else 110, seedb=4)
    slam(bg, "SOUNDS FAKE?", 118, W / 2, 330, lt, 0.0)
    # slanted toggle
    x0, x1, y0, y1, sk = 120, W - 120, 800, 1020, 50
    d = ImageDraw.Draw(bg)
    d.polygon([(x0 + sk - 14, y0 - 14), (x1 + 14, y0 - 14), (x1 - sk + 14, y1 + 14), (x0 - 14, y1 + 14)], fill=INK + (255,))
    u = eout(min(1, max(0, (lt - c) / 0.1)))
    fillc = PINK if on else (70, 80, 120)
    d.polygon([(x0 + sk, y0), (x1, y0), (x1 - sk, y1), (x0, y1)], fill=fillc + (255,))
    f = F("d", 92)
    if not on: d.text((x1 - 110 - f.getlength("FAKE"), (y0 + y1) / 2 - 62), "FAKE", font=f, fill=WHITE, stroke_width=5, stroke_fill=INK)
    else: d.text((x0 + 110, (y0 + y1) / 2 - 62), "TRUE", font=f, fill=YEL, stroke_width=5, stroke_fill=INK)
    kx = (x0 + 140) + (x1 - x0 - 280) * u; ky = (y0 + y1) / 2
    if 0 < u < 1:
        for j in range(1, 5):
            gx = kx - j * 70; ImageDraw.Draw(bg).ellipse([gx - 80, ky - 80, gx + 80, ky + 80], fill=WHITE + (int(160 / j),))
    d = ImageDraw.Draw(bg)
    d.ellipse([kx - 96, ky - 96, kx + 96, ky + 96], fill=INK + (255,))
    d.ellipse([kx - 86, ky - 86, kx + 86, ky + 86], fill=CLUB + (255,))
    d.chord([kx - 86, ky - 86, kx + 86, ky + 86], 10, 170, fill=CSH + (255,))
    d.ellipse([kx - 46, ky - 60, kx - 6, ky - 28], fill=(255, 200, 220, 255))
    if on:
        slam(bg, "IT'S TRUE.", 150, W / 2, 1250, lt, c + 0.05, YEL)
        k = lt - c
        if k < 0.25: starburst(bg, x1 - 140, ky, 200 * (1 - k / 0.25) + 60, 9, 0.2, WHITE, 0.3)
    k = lt - c
    return bg, dict(shake=22 * math.exp(-k * 8) if k > 0 else 0, impact=0 <= k < 0.07)

SCENES = dict(hook=S_hook, charge=S_charge, speed=S_speed, gforce=S_gforce, boil=S_boil, collapse=S_collapse, glass=S_glass, end=S_end)

# ---------- audio ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.18, tail=0.55)
n = len(voice); music = np.zeros(n, np.float32); rng = np.random.default_rng(27)
BEAT = 0.4
def kick(at, g=0.5):
    s = np.arange(int(0.3 * SR)) / SR; place(music, at, (np.sin(2 * np.pi * (45 + 110 * np.exp(-s * 30)) * s) * np.exp(-s * 12)).astype(np.float32), g)
def snare(at, g=0.22):
    m = int(0.18 * SR); s = np.arange(m) / SR
    place(music, at, (rng.normal(0, 1, m) * np.exp(-s * 22) + 0.5 * np.sin(2 * np.pi * 190 * s) * np.exp(-s * 30)).astype(np.float32), g)
def hat(at, g=0.05):
    m = int(0.05 * SR); s = np.arange(m) / SR; nz = rng.normal(0, 1, m); nz = nz - np.convolve(nz, np.ones(4) / 4, "same")
    place(music, at, (nz * np.exp(-s * 80)).astype(np.float32), g)
def saw(f, dur, g, decay=3.0):
    s = np.arange(int(dur * SR)) / SR
    w = sum(np.sin(2 * np.pi * f * h * s) / h for h in range(1, 7))
    return (w * np.exp(-s * decay) * np.minimum(1, s / 0.005) * np.minimum(1, (dur - s) / 0.02)).astype(np.float32) * g
def boom(at, g=0.45):
    s = np.arange(int(0.9 * SR)) / SR
    b = np.sin(2 * np.pi * (34 + 90 * np.exp(-s * 14)) * s) * np.exp(-s * 4.5)
    cr = rng.normal(0, 1, len(s)) * np.exp(-s * 35) * 0.6
    place(music, at, (b + cr).astype(np.float32), g)
CH = [(82.41, (329.63, 392.0, 493.88)), (65.41, (261.63, 329.63, 392.0)), (73.42, (293.66, 369.99, 440.0)), (61.74, (246.94, 311.13, 369.99))]
for bar in range(int(total / (BEAT * 4)) + 1):
    at = bar * BEAT * 4; root, ch = CH[bar % 4]
    for b in range(4):
        kick(at + b * BEAT, 0.42 if b % 2 == 0 else 0.25)
        if b % 2: snare(at + b * BEAT)
        hat(at + b * BEAT + BEAT / 2); hat(at + b * BEAT, 0.03)
    for e in range(8):
        place(music, at + e * BEAT / 2, saw(root * (2 if e in (3, 7) else 1), BEAT / 2 * 0.9, 0.05, 4))
    for e in (0, 3, 6):
        for f in ch: place(music, at + e * BEAT / 2, saw(f, 0.22, 0.012, 10))
def swish(at): whoosh(music, at, 0.14, 0.28)
hook_hit(music, 0.4); boom(0.0, 0.35)
HITS = []
for i, ln in enumerate(spec["lines"]):
    s0 = ln["_s"]; st = ln["scene"]["type"]
    if i > 0: swish(s0 - 0.08)
    if st == "hook": HITS.append(s0 + 0.85)
    if st == "speed":
        k = 0.35
        while k < ln["_se"] - s0: HITS.append(s0 + k); k += 1.1
    if st == "gforce": HITS.append(s0 + wstart(ln, 6) + 0.3)
    if st == "collapse":
        c = s0 + wstart(ln, 3) + 0.25; s = np.arange(int(0.6 * SR)) / SR
        place(music, c - 0.6, (rng.normal(0, 1, len(s)) * (s / 0.6) ** 3).astype(np.float32), 0.12)
        boom(c, 0.6)
        for wi in (6, 7, 10): place(music, s0 + wstart(ln, wi), saw(1318.5, 0.25, 0.04, 14))
    if st == "boil":
        r2 = np.random.default_rng(3)
        for j in range(18):
            a = s0 + wstart(ln, 7) - 0.3 + j * 0.08 + r2.uniform(0, 0.05); f0 = r2.uniform(500, 1400); s = np.arange(int(0.05 * SR)) / SR
            place(music, a, (np.sin(2 * np.pi * (f0 + 8000 * s) * s) * np.exp(-s * 60)).astype(np.float32), 0.05)
    if st == "glass":
        a = s0 + 0.55; HITS.append(a); m = int(0.7 * SR); s = np.arange(m) / SR
        place(music, a, (rng.normal(0, 1, m) * np.exp(-s * 6) * (0.5 + 0.5 * np.sin(2 * np.pi * 3100 * s))).astype(np.float32), 0.12)
    if st == "end":
        c = s0 + ln["scene"].get("click_at", 0.45); HITS.append(c)
        for j, fq in enumerate((659.25, 783.99, 987.77, 1318.51)): place(music, c + 0.1 + j * 0.07, saw(fq, 0.5, 0.03, 5))
for h in HITS: boom(h, 0.4)
write_audio(voice, music, work + "_audio.wav", music_gain=0.5, duck=0.45)

# ---------- compositing ----------
groups = caption_groups(words, 3)
def caption(O, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 70; f = F("d", size)
    while f.getlength(" ".join(ws)) > W - 260 and size > 40: size -= 4; f = F("d", size)
    tw_ = f.getlength(" ".join(ws)); x = (W - tw_) / 2; y = 1585; sk = 26
    d = ImageDraw.Draw(O)
    d.polygon([(x - 50 + sk, y - 22), (x + tw_ + 56, y - 22), (x + tw_ + 56 - sk, y + size + 26), (x - 50, y + size + 26)], fill=INK + (240,))
    d.polygon([(x - 50, y + size + 18), (x + tw_ + 56 - sk * 0.2, y + size + 18), (x + tw_ + 56 - sk, y + size + 26), (x - 50, y + size + 26)], fill=PINK + (255,))
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]
        d.text((x, y - size * 0.12), w, font=f, fill=YEL if on else WHITE, stroke_width=4, stroke_fill=INK); x += f.getlength(w + " ")

def scene(t, ln):
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    return SCENES[ln["scene"]["type"]](ln, lt, dur, t)

def two_tone(im, inv):
    a = np.asarray(im.convert("L")).astype(np.float32)
    out = np.empty(a.shape + (3,), np.uint8)
    lo, mid = a < 70, (a >= 70) & (a < 150)
    if inv: out[:] = INK; out[lo] = WHITE; out[mid] = PINK
    else: out[:] = WHITE; out[lo] = INK; out[mid] = PINK
    return Image.fromarray(out).convert("RGBA")

def frame(t, fi):
    lines = spec["lines"]; ln = active_line(spec, t) or lines[0]; i = lines.index(ln)
    im, fx = scene(t, ln)
    if i > 0 and t - (ln["_s"] - 0.12) < 0.24:          # white diagonal slash wipe
        ph = (t - (ln["_s"] - 0.12)) / 0.24
        if ph < 0.5: im, fx = scene(ln["_s"] - 0.121, lines[i - 1])
        cx = -500 + (W + 1000) * ph; d = ImageDraw.Draw(im)
        d.polygon([(cx - 260, H), (cx + 160, H), (cx + 900, 0), (cx + 480, 0)], fill=WHITE + (255,))
        d.polygon([(cx - 330, H), (cx - 290, H), (cx + 450, 0), (cx + 410, 0)], fill=PINK + (255,))
    if lines[-1] is ln:                                  # loop: dissolve into the hook
        k = (t - (total - 0.35)) / 0.35
        if k > 0:
            h0, _ = S_hook(lines[0], 0.0, 1, t); im = Image.blend(im, h0, min(1, k))
    if fx.get("impact"):
        im = two_tone(im, fi % 2 == 1)
    if fx.get("flash"):
        im = Image.blend(im, Image.new("RGBA", (W, H), WHITE + (255,)), min(1, fx["flash"]) * 0.85)
    sh = fx.get("shake", 0)
    if sh > 0.5:
        r = np.random.default_rng(fi); dx, dy = r.uniform(-sh, sh), r.uniform(-sh, sh); z = 1 + 2.2 * sh / W
        im = im.transform((W, H), Image.AFFINE, (1 / z, 0, (W - W / z) / 2 - dx, 0, 1 / z, (H - H / z) / 2 - dy), resample=Image.BILINEAR)
    O = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    caption(O, t)
    d = ImageDraw.Draw(O)
    d.rectangle([0, H - 12, W, H], fill=INK + (255,))
    pw = int(W * t / total)
    if pw > 1:
        g = np.linspace(0, 1, pw)[:, None] * (np.array(YEL) - np.array(PINK)) + np.array(PINK)
        O.paste(Image.fromarray(np.repeat(g.astype(np.uint8)[None], 12, 0)).convert("RGBA"), (0, H - 12))
    im.alpha_composite(O)
    return im.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), int(float(tt_) * FPS))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=22); print(f"done {total:.1f}s")
