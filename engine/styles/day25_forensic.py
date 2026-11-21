"""Day 25 — FORENSIC LAB style (koala fingerprints look almost exactly like ours).
A night forensic workstation: graphite desk with a faint dot grid, a back-lit light table (cool white with a pale
blue measuring grid and a soft halo) that every exhibit is laid on. Fingerprints are fully procedural and realistic:
an orientation field (Sherlock-Monro core/delta model + noise) drives iterated oriented Gabor filtering of noise, so
ridges flow, split and end like real minutiae; ink density, breaks and an edge fade are added on top.
Exhibits are evidence cards (white card, soft shadow, typed Courier Prime label strip, exhibit letter), rubber stamps
(red/yellow, slightly rotated, slam in with overshoot), red minutiae circles, a yellow scanner bar, a split-field
microscope view (human | koala ridges at high magnification with pores, reticle, vignette, chromatic rim), a flat
koala-hand diagram with two thumbs and print-textured pads, a lineup of cousin cards, an ink family-tree that draws
itself, and a eucalyptus branch. Archivo Black headlines + Courier Prime typed labels; evidence-yellow / forensic-red
accents. Scene changes are a scanner sweep (bright bar wipes the new exhibit down over the old one).
Channel constants: am_michael voice, word-by-word captions on a cream evidence tag with a yellow marker on the active
word, scrolling evidence tape, thin yellow progress bar, FAKE -> TRUE slider whose knob is a fingerprint, CASE CLOSED
stamp, dissolve back into the hook for the loop.
Music: original D-minor investigation groove (muted bass pulse, plucked arpeggio, closed-hat ticks) + scanner beeps.
Usage: python3 engine/styles/day25_forensic.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from core import *

class _Draw(ImageDraw.ImageDraw):
    """Skip near-transparent fills (PIL can render alpha-0 text opaque on RGBA images)."""
    def text(self, xy, text, fill=None, *a, **k):
        if isinstance(fill, tuple) and len(fill) == 4 and fill[3] < 3: return
        return super().text(xy, text, fill, *a, **k)
    def line(self, xy, fill=None, *a, **k):
        if isinstance(fill, tuple) and len(fill) == 4 and fill[3] < 3: return
        return super().line(xy, fill, *a, **k)
def _mk(im, mode=None): return _Draw(im, mode)
ImageDraw.Draw = _mk

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
_F = {}
def F(kind, s):
    k = (kind, int(s))
    if k not in _F:
        path = {"h": "ArchivoBlack-Regular.ttf", "tb": "CourierPrime-Bold.ttf", "tr": "CourierPrime-Regular.ttf",
                "m": "DMMono-Medium.ttf"}[kind]
        _F[k] = ImageFont.truetype(f"{FONTS}/{path}", int(s))
    return _F[k]

DESK = (27, 32, 38); DESK2 = (20, 24, 29); INK = (30, 33, 40); WHITE = (246, 247, 244)
YEL = (245, 196, 48); RED = (214, 64, 54); CREAM = (243, 235, 211); BLUEGRID = (176, 200, 214); GREY = (120, 128, 136)
TX0, TY0, TX1, TY1 = 50, 610, 1030, 1490                   # light table

def rnoise(h, w, cell, rng):
    a = rng.normal(0, 1, (max(2, h // cell), max(2, w // cell))).astype(np.float32)
    return cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC)

# ---------- procedural fingerprints ----------
def ridges(w, h, seed, cores, deltas, period=10, iters=14, rot=0.0):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    x = (xx / w * 2 - 1) * (w / h); y = yy / h * 2 - 1
    th = np.zeros_like(x) + rot
    for cx, cy in cores: th += 0.5 * np.arctan2(y - cy, x - cx)
    for dx, dy in deltas: th -= 0.5 * np.arctan2(y - dy, x - dx)
    th += 0.12 * rnoise(h, w, 120, rng)
    NB = 24; img = rng.normal(0, 1, (h, w)).astype(np.float32)
    kers = [cv2.getGaborKernel((25, 25), 4.0, np.pi * k / NB, period, 0.9, 0, ktype=cv2.CV_32F) for k in range(NB)]
    idx = (np.round(((th + np.pi / 2) % np.pi) / np.pi * NB).astype(int)) % NB
    masks = [idx == k for k in range(NB)]
    for _ in range(iters):
        out = np.zeros_like(img)
        for k in range(NB):
            if masks[k].any(): out[masks[k]] = cv2.filter2D(img, -1, kers[k])[masks[k]]
        img = np.tanh(out / (np.std(out) + 1e-6) * 2.0)
    return img, x, y, rng

def fingerprint(w, h, seed, cores, deltas, period=10):
    img, x, y, rng = ridges(w, h, seed, cores, deltas, period)
    rid = np.clip(img * 1.4 + 0.2, 0, 1)
    rid *= np.clip((rnoise(h, w, 5, rng) + 2.3) / 0.4, 0, 1)
    m = np.sqrt((x / (0.92 * w / h)) ** 2 + ((y - 0.06) / 0.94) ** 2) + 0.012 * rnoise(h, w, 40, rng)
    mask = np.clip((1 - m) / 0.10, 0, 1)
    return (rid * mask * (0.8 + 0.2 * rnoise(h, w, 70, rng).clip(-1, 1))).clip(0, 1)

def magnified(w, h, seed, cores, deltas, up=4):
    """High magnification ridge field: small Gabor field upscaled then re-sharpened, with sweat pores."""
    img, x, y, rng = ridges(w // up, h // up, seed, cores, deltas, period=9, iters=12)
    big = cv2.resize(img, (w, h), interpolation=cv2.INTER_CUBIC)
    big += 0.18 * rnoise(h, w, 14, rng)                        # irregular ridge edges
    rid = 1 / (1 + np.exp(-(big + 0.05) * 9))
    pores = np.zeros((h, w), np.float32)
    for _ in range(int(w * h / 2600)):
        px, py = rng.integers(0, w), rng.integers(0, h)
        if rid[py, px] > 0.8: cv2.circle(pores, (int(px), int(py)), int(rng.integers(3, 6)), 1.0, -1, cv2.LINE_AA)
    rid *= 1 - 0.85 * pores
    return rid.clip(0, 1)

def ink_rgba(a, col=INK, alpha=235):
    h, w = a.shape; out = np.zeros((h, w, 4), np.uint8); out[..., :3] = col
    out[..., 3] = (a * alpha).astype(np.uint8); return Image.fromarray(out, "RGBA")

PW, PH = 300, 390
HUMAN = fingerprint(PW, PH, 1, ((0, -0.15),), ((-0.55, 0.35),))
KOALA = fingerprint(PW, PH, 7, ((0.08, -0.1),), ((0.6, 0.4),), period=10)
HUMAN_S = fingerprint(180, 234, 3, ((0.02, -0.1),), ((-0.5, 0.4),), period=8)
KOALA_S = fingerprint(180, 234, 11, ((0.05, -0.12),), ((0.55, 0.38),), period=8)
MAG_H = magnified(420, 840, 21, ((0.25, -0.62),), ((-0.6, 0.75),), up=3)
MAG_K = magnified(420, 840, 29, ((-0.15, -0.58),), ((0.65, 0.8),), up=3)

# ---------- static layers ----------
def build_base():
    rr = np.random.default_rng(25)
    a = np.zeros((H, W, 3), np.float32); a[:] = DESK
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    a *= (1.08 - 0.35 * (((xx - W / 2) / W) ** 2 + ((yy - 900) / H) ** 2))[..., None]
    a += rr.normal(0, 2.0, (H, W, 1)).astype(np.float32)
    img = Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(20, H, 40):
        for x in range(20, W, 40): d.point((x, y), fill=(70, 80, 92, 255))
    # table halo
    halo = Image.new("L", (W, H), 0); ImageDraw.Draw(halo).rounded_rectangle([TX0 - 6, TY0 - 6, TX1 + 6, TY1 + 6], 30, fill=120)
    halo = halo.filter(ImageFilter.GaussianBlur(40))
    img.paste((200, 220, 230), (0, 0), halo)
    # light table surface
    tw, th_ = TX1 - TX0, TY1 - TY0
    ty, tx = np.mgrid[0:th_, 0:tw].astype(np.float32)
    lum = 1.0 - 0.1 * (((tx - tw / 2) / tw) ** 2 * 2 + ((ty - th_ / 2) / th_) ** 2 * 2)
    s = np.zeros((th_, tw, 3), np.float32); s[:] = (236, 242, 242); s *= lum[..., None]
    surf = Image.fromarray(s.clip(0, 255).astype(np.uint8)).convert("RGBA")
    sd = ImageDraw.Draw(surf, "RGBA")
    for gx in range(20, tw, 40): sd.line([gx, 0, gx, th_], fill=BLUEGRID + ((90 if (gx - 20) % 200 == 0 else 40),), width=1)
    for gy in range(20, th_, 40): sd.line([0, gy, tw, gy], fill=BLUEGRID + ((90 if (gy - 20) % 200 == 0 else 40),), width=1)
    for gx in range(20, tw, 200): sd.text((gx + 4, 4), str((gx - 20) // 2), font=F("m", 16), fill=BLUEGRID + (200,))
    m = Image.new("L", (tw, th_), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, tw - 1, th_ - 1], 24, fill=255)
    img.paste(surf, (TX0, TY0), m)
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([TX0 - 2, TY0 - 2, TX1 + 2, TY1 + 2], 26, outline=(70, 78, 88, 255), width=4)
    # top bar
    d.text((50, 46), "SF FORENSICS", font=F("tb", 34), fill=(225, 228, 230, 255))
    d.text((50, 84), "LATENT PRINT UNIT  ·  CASE 25", font=F("tr", 26), fill=(140, 150, 160, 255))
    d.line([50, 122, W - 50, 122], fill=(60, 68, 78, 255), width=2)
    return img

BASE = build_base()

def tape_strip(off):
    """Scrolling yellow/black evidence tape (y 1748..1820)."""
    h = 66; wtot = W + 700
    im = Image.new("RGBA", (wtot, h), YEL + (255,)); d = ImageDraw.Draw(im)
    for x in range(-h, wtot, 60): d.polygon([(x, 0), (x + 22, 0), (x + 22 + h, h), (x + h, h)], fill=(22, 22, 22, 255))
    lab = "  EVIDENCE · DO NOT CROSS  "
    f = F("tb", 34); lw = f.getlength(lab)
    for x in range(0, wtot, 600):
        d.rectangle([x + 40, 10, x + 40 + lw, h - 10], fill=YEL + (255,)); d.text((x + 40, 14), lab, font=f, fill=(22, 22, 22, 255))
    return im
TAPE = tape_strip(0)

# ---------- reusable pieces ----------
_C = {}
def card(key, print_arr, label, letter, w=PW + 40, ang=0.0, blank=False):
    if key in _C: return _C[key]
    ph = int(w * 1.3) if print_arr is None else print_arr.shape[0] + 40
    h = ph + 70
    im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    sh = Image.new("L", im.size, 0); ImageDraw.Draw(sh).rectangle([34, 38, 30 + w, 34 + h], fill=110)
    im.paste((10, 14, 20), (0, 0), sh.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle([30, 30, 30 + w, 30 + h], fill=WHITE + (255,), outline=(200, 204, 206, 255), width=2)
    if print_arr is not None:
        pi = ink_rgba(print_arr); im.alpha_composite(pi, (30 + (w - pi.width) // 2, 50))
    if blank:
        cx, cy, rx, ry = 30 + w / 2, 30 + ph / 2 + 10, w * 0.32, ph * 0.38
        for k in range(0, 360, 14):
            a0, a1 = math.radians(k), math.radians(k + 8)
            d.line([cx + rx * math.cos(a0), cy + ry * math.sin(a0), cx + rx * math.cos(a1), cy + ry * math.sin(a1)], fill=(160, 166, 172, 255), width=4)
        f = F("tb", 26); s = "NO RIDGES"; d.text((cx - f.getlength(s) / 2, cy - 14), s, font=f, fill=(150, 156, 162, 255))
    d.rectangle([30, 30 + ph, 30 + w, 30 + h], fill=(232, 228, 214, 255))
    d.line([30, 30 + ph, 30 + w, 30 + ph], fill=(190, 186, 172, 255), width=2)
    f = F("tb", 30 if w > 260 else 26)
    while f.getlength(label) > w - 90: f = F("tb", f.size - 2)
    d.text((44, 30 + ph + 18), label, font=f, fill=INK + (255,))
    d.rectangle([30 + w - 56, 30 + ph + 12, 30 + w - 12, 30 + ph + 56], fill=INK + (255,))
    fl = F("h", 30); d.text((30 + w - 34 - fl.getlength(letter) / 2, 30 + ph + 14), letter, font=fl, fill=YEL + (255,))
    if ang: im = im.rotate(ang, Image.BICUBIC, expand=True)
    _C[key] = im; return im

def stamp_img(text, col, size=64, ang=-8):
    k = ("st", text, col, size, ang)
    if k in _C: return _C[k]
    f = F("h", size); tw_ = f.getlength(text)
    im = Image.new("RGBA", (int(tw_ + 80), int(size * 1.9)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([6, 6, im.width - 6, im.height - 6], 10, outline=col + (255,), width=8)
    d.text((40, size * 0.33), text, font=f, fill=col + (255,))
    # worn ink texture
    a = np.asarray(im).copy(); rng = np.random.default_rng(len(text))
    a[..., 3] = (a[..., 3] * np.clip(0.7 + rng.random(a.shape[:2]) * 0.6, 0, 1)).astype(np.uint8)
    im = Image.fromarray(a).rotate(ang, Image.BICUBIC, expand=True)
    _C[k] = im; return im

def paste(img, im, cx, cy, al=1.0, sc=1.0):
    if al <= 0.01 or sc <= 0.01: return
    if abs(sc - 1) > 0.01: im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR)
    if al < 0.99:
        im = im.copy(); a = np.asarray(im).copy(); a[..., 3] = (a[..., 3] * al).astype(np.uint8); im = Image.fromarray(a)
    img.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def slam(img, im, cx, cy, lt, at, al=1.0):
    u = (lt - at) / 0.22
    if u <= 0: return
    sc = 1.0 + 0.9 * (1 - eout(u)) if u < 1 else 1.0
    paste(img, im, cx, cy, al * min(1, u * 1.6), sc)

def fade(lt, at, d=0.25): return ease((lt - at) / d)
def wstart(ln, i): return words[min(ln["_w0"] + i, ln["_w1"] - 1)][1] - ln["_s"]

def fit(s, size, kind="h", maxw=960):
    while F(kind, size).getlength(s) > maxw and size > 30: size -= 2
    return size

def headline(img, rows, al=1.0, lt=9.0, y0=150, gap=14, stagger=0.0):
    """rows: [(text, color, size)] centred in the header zone; each row slides up + fades in."""
    d = ImageDraw.Draw(img, "RGBA"); y = y0
    for i, (s, col, size) in enumerate(rows):
        size = fit(s, size); f = F("h", size)
        u = 1.0 if stagger == 0 else eout((lt - i * stagger) / 0.25)
        a = int(255 * al * u)
        if a > 2:
            x = (W - f.getlength(s)) / 2; yy = y + 30 * (1 - u)
            d.text((x + 6, yy + 7), s, font=f, fill=(8, 10, 14, int(a * 0.8)))
            d.text((x, yy), s, font=f, fill=col + (a,))
        y += size * 1.0 + gap

def mcircle(d, x, y, r, al, n=None):
    if al <= 0.02: return
    d.ellipse([x - r, y - r, x + r, y + r], outline=RED + (int(255 * al),), width=5)
    if n is not None:
        f = F("tb", 26); d.text((x + r * 0.75, y - r - 26), str(n), font=f, fill=RED + (int(255 * al),))

# ---------- scenes: fn(img, ln, lt, dur, t, al) ----------
CARD_A = (300, 1010); CARD_B = (780, 1010)
MINU = [(-60, -90), (50, -20), (-30, 60), (70, 110), (-90, 20)]

def S_hook(img, ln, lt, dur, t, al=1.0):
    headline(img, [("KOALA PRINTS", WHITE, 118), ("LOOK LIKE", WHITE, 118), ("OURS.", YEL, 180)], al, y0=140, gap=10)
    paste(img, card("ha", HUMAN, "HUMAN", "A", ang=2), *CARD_A, al)
    paste(img, card("hb", KOALA, "KOALA", "B", ang=-2), *CARD_B, al)
    d = ImageDraw.Draw(img, "RGBA")
    for k, (dx, dy) in enumerate(MINU):                       # matching minutiae pop on both prints
        a = al * fade(lt, 0.2 + k * 0.28, 0.12)
        for (cx, cy) in (CARD_A, CARD_B): mcircle(d, cx + dx, cy - 30 + dy, 22, a, k + 1 if cx == CARD_B[0] else None)
        if a > 0.05: d.line([CARD_A[0] + dx + 22, CARD_A[1] - 30 + dy, CARD_B[0] + dx - 22, CARD_B[1] - 30 + dy], fill=RED + (int(70 * a),), width=2)
    # scanner bar sweeping both cards
    sy = 760 + (1240 - 760) * (0.5 - 0.5 * math.cos(t * 2.4))
    scan_bar(img, sy, 110, 970, al * 0.9)
    # similarity meter
    mx0, mx1, my = 120, 960, 1400
    v = 0.55 + 0.4 * eout(lt / 2.0)
    d.text((mx0, my - 46), "RIDGE SIMILARITY", font=F("tb", 30), fill=INK + (int(255 * al),))
    lab = "VERY HIGH" if v > 0.85 else "ANALYSING…"
    f = F("tb", 30); d.text((mx1 - f.getlength(lab), my - 46), lab, font=f, fill=(RED if v > 0.85 else INK) + (int(255 * al),))
    d.rounded_rectangle([mx0, my, mx1, my + 34], 8, fill=(205, 212, 214, int(255 * al)))
    segs = 28
    for k in range(int(segs * v)):
        x = mx0 + 6 + k * (mx1 - mx0 - 12) / segs
        d.rectangle([x, my + 6, x + (mx1 - mx0 - 12) / segs - 5, my + 28], fill=(RED if k > segs * 0.8 else INK) + (int(255 * al),))

def scan_bar(img, y, x0, x1, al):
    if al <= 0.02: return
    k = ("bar", x0, x1)
    if k not in _C:
        h = 90; a = np.zeros((h, x1 - x0, 4), np.uint8); a[..., :3] = YEL
        prof = np.exp(-((np.arange(h) - h / 2) / 14) ** 2); prof = np.maximum(prof, 0.9 * (np.abs(np.arange(h) - h / 2) < 2))
        a[..., 3] = (prof[:, None] * 200).astype(np.uint8); a[np.abs(np.arange(h) - h / 2) < 2, :, :3] = (255, 250, 220)
        _C[k] = Image.fromarray(a, "RGBA")
    paste(img, _C[k], (x0 + x1) / 2, y, al)

def S_loop(img, ln, lt, dur, t, al=1.0):
    headline(img, [("THE REASON", WHITE, 140), ("IS STRANGER", YEL, 140)], al, lt=lt, y0=180, stagger=0.25)
    d = ImageDraw.Draw(img, "RGBA")
    # case file folder
    fx0, fy0, fx1, fy1 = 140, 700, 940, 1400
    d.rounded_rectangle([fx0, fy0 - 40, fx0 + 280, fy0 + 20], 14, fill=(214, 182, 120, int(255 * al)))
    d.rectangle([fx0, fy0, fx1, fy1], fill=(226, 196, 136, int(255 * al)))
    d.rectangle([fx0 + 30, fy0 + 30, fx1 - 30, fy1 - 30], fill=(250, 248, 240, int(255 * al)))
    rows = [("CASE NO.", "25"), ("SUBJECT", "KOALA PRINTS"), ("MATCH", "HUMAN-LIKE"), ("STATUS", "OPEN"), ("MOTIVE", "? ? ?")]
    for i, (k, v) in enumerate(rows):
        y = fy0 + 80 + i * 92; a = al * fade(lt, 0.1 + i * 0.16, 0.1)
        d.text((fx0 + 70, y), k, font=F("tr", 34), fill=(110, 110, 104, int(255 * a)))
        n = int(len(v) * min(1, max(0, (lt - 0.15 - i * 0.16) / 0.3)))
        col = RED if k == "MOTIVE" else INK
        blink = 1.0 if k != "MOTIVE" or (t * 2.5) % 1 < 0.65 else 0.25
        d.text((fx0 + 330, y - 4), v[:n], font=F("tb", 44), fill=col + (int(255 * a * blink),))
        d.line([fx0 + 70, y + 56, fx1 - 70, y + 56], fill=(200, 204, 210, int(255 * a)), width=2)
    paste(img, card("ls", KOALA_S, "KOALA", "B", w=200, ang=6), 790, 1250, al * fade(lt, 0.3))
    slam(img, stamp_img("WAIT FOR IT", RED, 58, 8), 400, 1290, lt, wstart(ln, 4), al)

def S_micro(img, ln, lt, dur, t, al=1.0):
    headline(img, [("UNDER THE", WHITE, 130), ("MICROSCOPE", YEL, 150)], al, lt=lt, y0=180, stagger=0.2)
    cx, cy, R = 540, 1040, 400
    k = ("scope",)
    if k not in _C:
        yy, xx = np.mgrid[0:2 * R, 0:2 * R].astype(np.float32)
        r = np.sqrt((xx - R) ** 2 + (yy - R) ** 2) / R
        _C[k] = (np.clip((1 - r) / 0.012, 0, 1), np.clip(1.05 - 0.55 * r ** 3, 0, 1), r)
    m, vig, r = _C[k]
    pan = int(60 * lt)
    field = np.zeros((2 * R, 2 * R), np.float32)
    field[:, :R] = MAG_H[pan // 2: pan // 2 + 2 * R, :R][: 2 * R] if MAG_H.shape[0] >= pan // 2 + 2 * R else MAG_H[-2 * R:, :R]
    field[:, R:] = MAG_K[pan // 3: pan // 3 + 2 * R, :R][: 2 * R] if MAG_K.shape[0] >= pan // 3 + 2 * R else MAG_K[-2 * R:, :R]
    bg = np.array([238, 232, 214], np.float32); ink = np.array([92, 62, 50], np.float32)
    rgb = bg[None, None] * (1 - field[..., None]) + ink[None, None] * field[..., None]
    rgb *= vig[..., None]
    rim = np.exp(-((r - 0.985) / 0.012) ** 2)[..., None] * np.array([60, 30, 120], np.float32)
    rgb = rgb + rim
    a = (m * 255 * al).astype(np.uint8)
    im = Image.fromarray(np.dstack([rgb.clip(0, 255).astype(np.uint8), a]), "RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([cx - R - 22, cy - R - 22, cx + R + 22, cy + R + 22], fill=(18, 20, 24, int(255 * al)))
    img.alpha_composite(im, (cx - R, cy - R))
    d.line([cx, cy - R, cx, cy + R], fill=(30, 30, 30, int(200 * al)), width=4)              # split seam
    d.line([cx - R + 40, cy, cx + R - 40, cy], fill=(30, 30, 30, int(60 * al)), width=2)
    for k in range(-8, 9):
        d.line([cx + k * 40, cy - 10, cx + k * 40, cy + 10], fill=(30, 30, 30, int(80 * al)), width=2)
    for x, lab in ((cx - 200, "HUMAN"), (cx + 200, "KOALA")):
        f = F("tb", 34); tw_ = f.getlength(lab)
        d.rounded_rectangle([x - tw_ / 2 - 18, cy - R + 50, x + tw_ / 2 + 18, cy - R + 104], 10, fill=INK + (int(235 * al),))
        d.text((x - tw_ / 2, cy - R + 58), lab, font=f, fill=WHITE + (int(255 * al),))
    slam(img, stamp_img("INCONCLUSIVE", RED, 70, -9), cx, cy + 230, lt, wstart(ln, 8) - 0.05, al)

def koala_hand():
    k = ("hand",)
    if k in _C: return _C[k]
    S = 2; w, h = 860, 800
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    fill = (64, 70, 80, 255); pad = (150, 132, 128, 255)
    px, py = 450, 560                                             # palm centre
    digits = [(-168, 0, 175, "T1"), (-140, 0, 185, "T2"), (-80, 0, 200, ""), (-56, 0, 205, ""), (-32, 0, 185, "")]
    tips = []
    for ang, wd, L, lab in digits:
        a = math.radians(ang); ex, ey = px + L * 1.35 * math.cos(a), py + L * 1.35 * math.sin(a)
        d.line([px * S, py * S, ex * S, ey * S], fill=fill, width=int(84 * S))
        d.ellipse([(ex - 42) * S, (ey - 42) * S, (ex + 42) * S, (ey + 42) * S], fill=fill)
        tips.append((ex, ey, a, lab))
    d.ellipse([(px - 200) * S, (py - 170) * S, (px + 200) * S, (py + 190) * S], fill=fill)
    d.rounded_rectangle([(px - 60) * S, py * S, (px + 60) * S, (py + 250) * S], 50 * S, fill=fill)      # wrist
    d.ellipse([(px - 120) * S, (py - 60) * S, (px + 130) * S, (py + 130) * S], fill=pad)
    for ex, ey, a, lab in tips:                                    # claws
        cx_, cy_ = ex + 46 * math.cos(a), ey + 46 * math.sin(a)
        n = (math.cos(a + 1.57), math.sin(a + 1.57))
        pts = [(cx_ - 14 * n[0], cy_ - 14 * n[1]), (cx_ + 14 * n[0], cy_ + 14 * n[1]),
               (cx_ + 60 * math.cos(a + 0.5), cy_ + 60 * math.sin(a + 0.5))]
        d.polygon([(x * S, y * S) for x, y in pts], fill=(36, 34, 32, 255))
    im = im.resize((w, h), Image.LANCZOS)
    for ex, ey, a, lab in tips:                                    # printed pads
        pr = ink_rgba(cv2.resize(KOALA_S, (64, 84)), (240, 232, 226), 255)
        mk = Image.new("L", (64, 84), 0); ImageDraw.Draw(mk).ellipse([2, 2, 62, 82], fill=255)
        base = Image.new("RGBA", (64, 84), pad); base.alpha_composite(pr); base.putalpha(mk)
        base = base.rotate(-math.degrees(a) - 90, Image.BICUBIC, expand=True)
        im.alpha_composite(base, (int(ex - base.width / 2), int(ey - base.height / 2)))
    _C[k] = (im, tips); return _C[k]

def S_thumbs(img, ln, lt, dur, t, al=1.0):
    headline(img, [("TWO THUMBS", YEL, 150), ("ON EACH HAND", WHITE, 120)], al, lt=lt, y0=180, stagger=0.2)
    hand, tips = koala_hand()
    hx, hy = 520, 1010
    u = eout(lt / 0.35); paste(img, hand, hx, hy + 40 * (1 - u), al * u)
    d = ImageDraw.Draw(img, "RGBA")
    ox, oy = hx - hand.width / 2, hy - hand.height / 2
    for i, (ex, ey, a, lab) in enumerate(tips[:2]):
        aa = al * fade(lt, wstart(ln, 3) + i * 0.25, 0.15)
        if aa < 0.02: continue
        x, y = ox + ex, oy + ey
        mcircle(d, x, y, 58, aa)
        lx, ly = (150, 760) if i == 0 else (200, 1440)
        lx, ly = (x - 250, y + 40) if i == 0 else (x - 120, y - 150)
        d.line([x - 58 * 0.8, y, lx + 200, ly + 26], fill=RED + (int(255 * aa),), width=4)
        f = F("tb", 40); s = f"THUMB {i + 1}"
        d.rounded_rectangle([lx - 14, ly - 6, lx + f.getlength(s) + 14, ly + 52], 8, fill=RED + (int(255 * aa),))
        d.text((lx, ly), s, font=f, fill=WHITE + (int(255 * aa),))
    f = F("tb", 30); s = "FIG. 1 — KOALA FOREPAW (PALM VIEW)"
    d.text(((W - f.getlength(s)) / 2, 1430), s, font=f, fill=(90, 96, 104, int(255 * al * fade(lt, 0.3))))

def S_lineup(img, ln, lt, dur, t, al=1.0):
    headline(img, [("THEIR COUSINS?", WHITE, 128), ("NO PRINTS.", RED, 150)], al, lt=lt, y0=180, stagger=0.3)
    d = ImageDraw.Draw(img, "RGBA")
    for x in range(TX0 + 40, TX1 - 40, 24):                      # lineup height marks
        pass
    xs = (210, 540, 870)
    specs_ = (("WOMBAT", None, True, wstart(ln, 3)), ("KANGAROO", None, True, wstart(ln, 5)), ("KOALA", KOALA_S, False, 0.0))
    for i, (x, (lab, pa, blank, at)) in enumerate(zip(xs, specs_)):
        c = card("lu" + lab, pa, lab, "CDE"[i], w=270, ang=(-2, 1.5, -1)[i], blank=blank)
        u = eout((lt - at + 0.1) / 0.3) if at > 0 else 1.0
        paste(img, c, x, 1000 - 60 * (1 - u), al * u)
        if blank: slam(img, stamp_img("NONE", RED, 64, -12), x, 980, lt, at + 0.35, al)
        else: slam(img, stamp_img("PRINTS", YEL, 52, 10), x, 1150, lt, wstart(ln, 8), al)
    f = F("tb", 32); s = "MARSUPIAL RELATIVES"
    d.text(((W - f.getlength(s)) / 2, 1380), s, font=f, fill=(90, 96, 104, int(255 * al)))

def S_tree(img, ln, lt, dur, t, al=1.0):
    headline(img, [("EVOLVED", WHITE, 150), ("SEPARATELY", YEL, 150)], al, lt=lt, y0=180, stagger=0.2)
    d = ImageDraw.Draw(img, "RGBA")
    root, fork = (540, 1440), (540, 1220)
    L, Rt = (270, 960), (810, 960)
    g = lambda a, b: ease((lt - a) / b)
    def seg(p, q, u, wd=10):
        if u <= 0: return
        d.line([p[0], p[1], p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u], fill=INK + (int(255 * al),), width=wd)
    seg(root, fork, g(0.0, 0.3)); seg(fork, L, g(0.3, 0.45)); seg(fork, Rt, g(0.3, 0.45))
    tw_ = (700, 1080); seg((700, 1066), (930, 1170), g(0.6, 0.3), 7)  # side twig: other marsupials
    if lt > 0.85:
        a = al * fade(lt, 0.85)
        f = F("tb", 26); s = "WOMBATS, KANGAROOS"
        d.text((930 - f.getlength(s) + 70, 1186), s, font=f, fill=(90, 96, 104, int(255 * a)))
        d.line([915, 1155, 945, 1185], fill=RED + (int(255 * a),), width=6); d.line([945, 1155, 915, 1185], fill=RED + (int(255 * a),), width=6)
    f = F("tb", 30)
    for (p, lab, dx) in ((L, "PRIMATES", -1), (Rt, "MARSUPIALS", 1)):
        a = al * fade(lt, 0.6)
        s = lab; x = (290 - f.getlength(s)) if dx < 0 else 790; y = 1010
        d.text((x, y), s, font=f, fill=INK + (int(255 * a),))
    s = "COMMON ANCESTOR"; d.text((540 - f.getlength(s) / 2, 1445 - 50), "", font=f)
    d.text((570, 1400), s, font=F("tb", 26), fill=(90, 96, 104, int(255 * al * fade(lt, 0.1))))
    for (p, arr, lab, letter, at) in ((L, HUMAN_S, "HUMAN", "A", 0.75), (Rt, KOALA_S, "KOALA", "B", 0.95)):
        c = card("tr" + lab, arr, lab, letter, w=210)
        u = eout((lt - at) / 0.3); paste(img, c, p[0], p[1] - 170 + 30 * (1 - u), al * u)
    k = fade(lt, wstart(ln, 5), 0.2)
    if k > 0:
        s = "CONVERGENT EVOLUTION"; f = F("tb", 38); tw2 = f.getlength(s)
        d.rounded_rectangle([540 - tw2 / 2 - 20, 1290, 540 + tw2 / 2 + 20, 1348], 10, fill=YEL + (int(255 * al * k),))
        d.text((540 - tw2 / 2, 1298), s, font=f, fill=(22, 22, 22, int(255 * al * k)))

def branch_img():
    k = ("branch",)
    if k in _C: return _C[k]
    S = 2; w, h = 980, 880
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(-20 + 1020 * u, 760 - 520 * u - 120 * math.sin(math.pi * u)) for u in np.linspace(0, 1, 60)]
    d.line([(x * S, y * S) for x, y in pts], fill=(106, 78, 58, 255), width=26 * S, joint="curve")
    d.line([(x * S, (y - 6) * S) for x, y in pts], fill=(140, 108, 82, 255), width=6 * S, joint="curve")
    rng = np.random.default_rng(5)
    leaves = []
    for i in range(3, 58, 4):
        x, y = pts[i]; side = 1 if (i // 4) % 2 else -1
        ang = math.radians(-35 + side * 70 + rng.uniform(-15, 15)); Ls = rng.uniform(170, 230)
        leaves.append((x, y, ang, Ls, x / w))
    for x, y, ang, Ls, _ in leaves:
        ca, sa = math.cos(ang), math.sin(ang)
        poly = []
        for u in np.linspace(0, 1, 24): poly.append((u * Ls, 0.17 * Ls * math.sin(math.pi * u) ** 0.8 * (1 - 0.3 * u)))
        for u in np.linspace(1, 0, 24): poly.append((u * Ls, -0.17 * Ls * math.sin(math.pi * u) ** 0.8 * (1 - 0.3 * u) * 0.8))
        bend = lambda px_, py_: (px_, py_ + 0.0006 * px_ * px_)
        P = [bend(px_, py_) for px_, py_ in poly]
        P = [((x + px_ * ca - py_ * sa) * S, (y + px_ * sa + py_ * ca) * S) for px_, py_ in P]
        d.polygon(P, fill=(122, 160, 146, 255))
        mid = [bend(u * Ls, 0) for u in np.linspace(0, 1, 12)]
        d.line([((x + px_ * ca - py_ * sa) * S, (y + px_ * sa + py_ * ca) * S) for px_, py_ in mid], fill=(86, 118, 106, 255), width=3 * S)
    im = im.resize((w, h), Image.LANCZOS)
    _C[k] = im; return im

def S_motive(img, ln, lt, dur, t, al=1.0):
    headline(img, [("THE MOTIVE:", WHITE, 130), ("GRIP.", YEL, 190)], al, lt=lt, y0=170, stagger=0.25)
    b = branch_img()
    u = ease(lt / 0.8)                                            # branch reveals left -> right
    if u > 0:
        cw = max(1, int(b.width * u)); crop = b.crop((0, 0, cw, b.height))
        tmp = Image.new("RGBA", b.size, (0, 0, 0, 0)); tmp.paste(crop, (0, 0))
        paste(img, tmp, 540, 1060, al)
    c = card("mo", KOALA_S, "KOALA", "B", w=230, ang=-5)
    v = eout((lt - 0.5) / 0.3); paste(img, c, 300, 960 + 50 * (1 - v), al * v)
    d = ImageDraw.Draw(img, "RGBA")
    k = fade(lt, wstart(ln, 7), 0.2)
    if k > 0:
        s = "BRANCHES + EUCALYPTUS LEAVES"; f = F("tb", 34); tw2 = f.getlength(s)
        d.rounded_rectangle([540 - tw2 / 2 - 20, 1370, 540 + tw2 / 2 + 20, 1426], 10, fill=INK + (int(240 * al * k),))
        d.text((540 - tw2 / 2, 1378), s, font=f, fill=WHITE + (int(255 * al * k),))
    a = al * fade(lt, wstart(ln, 4), 0.15)
    if a > 0.02:                                                  # red string: print -> branch
        u = eout((lt - wstart(ln, 4)) / 0.4)
        mcircle(d, 300, 930, 80 + 6 * math.sin(lt * 6), a)
        d.line([380, 930, 380 + (700 - 380) * u, 930 + (955 - 930) * u], fill=RED + (int(255 * a),), width=5)
        if u > 0.95: mcircle(d, 700, 955, 30, a)
    slam(img, stamp_img("LIKELY", RED, 54, 8), 760, 760, lt, wstart(ln, 1), al)

def fp_knob():
    k = ("knob",)
    if k in _C: return _C[k]
    s = 120; im = Image.new("RGBA", (s + 20, s + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([6, 10, s + 10, s + 14], fill=(0, 0, 0, 90))
    d.ellipse([4, 4, s + 4, s + 4], fill=WHITE + (255,), outline=INK + (255,), width=5)
    pr = ink_rgba(cv2.resize(KOALA_S, (80, 104)), INK, 255)
    mk = Image.new("L", (80, 104), 0); ImageDraw.Draw(mk).ellipse([4, 4, 76, 100], fill=255)
    a = np.asarray(pr).copy(); a[..., 3] = (a[..., 3] * (np.asarray(mk) / 255)).astype(np.uint8)
    im.alpha_composite(Image.fromarray(a), (24, 12))
    _C[k] = im; return im

def S_end(img, ln, lt, dur, t, al=1.0):
    click = ln["scene"].get("click_at", 0.45); on = ease((lt - click) / 0.3)
    headline(img, [("SOUNDS FAKE?", WHITE, 140)], al, y0=260)
    d = ImageDraw.Draw(img, "RGBA")
    x0, x1, y, hh = 150, 930, 860, 150
    d.rounded_rectangle([x0, y - hh / 2, x1, y + hh / 2], hh / 2, fill=(205, 210, 212, int(255 * al)), outline=INK + (int(255 * al),), width=6)
    if on > 0:                                                    # track floods with evidence-yellow
        fx = x0 + (x1 - x0) * on
        d.rounded_rectangle([x0 + 8, y - hh / 2 + 8, max(x0 + hh, fx), y + hh / 2 - 8], hh / 2, fill=YEL + (int(255 * al),))
    f = F("h", 70)
    d.text((x1 - 70 - f.getlength("FAKE"), y - 46), "FAKE", font=f, fill=RED + (int(255 * al * (1 - on)),))
    d.text((x0 + 70, y - 46), "TRUE", font=f, fill=INK + (int(255 * al * on),))
    kx = x0 + hh / 2 + (x1 - x0 - hh) * on
    paste(img, fp_knob(), kx, y, al)
    k = fade(lt, click + 0.25, 0.2)
    s = "IT'S TRUE."; fs = fit(s, 190); f2 = F("h", fs)
    d.text(((W - f2.getlength(s)) / 2, 1010), s, font=f2, fill=INK + (int(255 * al * k),))
    s = "FOLLOW FOR MORE"; f3 = F("tb", 64)
    d.text(((W - f3.getlength(s)) / 2, 1250), s, font=f3, fill=INK + (int(255 * al * fade(lt, click + 0.55, 0.2)),))
    slam(img, stamp_img("CASE CLOSED", RED, 66, -10), 720, 680, lt, click + 0.4, al)

SCENES = dict(hook=S_hook, loop=S_loop, micro=S_micro, thumbs=S_thumbs, lineup=S_lineup, tree=S_tree, motive=S_motive, end=S_end)

# ---------- audio ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
rng = np.random.default_rng(25)
BPM = 104; beat = 60 / BPM
BASS = [73.42, 73.42, 58.27, 65.41]                           # D2 D2 Bb1 C2
ARP = [[293.66, 349.23, 440.0, 587.33], [293.66, 349.23, 440.0, 523.25], [233.08, 293.66, 349.23, 466.16], [261.63, 329.63, 392.0, 523.25]]
def pluck(f, dur, gain):
    N = int(dur * SR); p = max(2, int(SR / f)); buf = rng.uniform(-1, 1, p).astype(np.float32); out = np.zeros(N, np.float32)
    for i in range(N):
        out[i] = buf[i % p]; buf[i % p] = 0.5 * (buf[i % p] + buf[(i + 1) % p]) * 0.994
    return out * gain
PL = {}
def pl(f):
    if f not in PL: PL[f] = pluck(f, 0.6, 1.0)
    return PL[f]
def bassn(f, dur, gain):
    s = np.arange(int(dur * SR)) / SR
    sig = np.sin(2 * np.pi * f * s) + 0.35 * np.sin(2 * np.pi * 2 * f * s)
    return (sig * np.exp(-s * 6) * np.minimum(1, s / 0.008)).astype(np.float32) * gain
bars = int(total / (4 * beat)) + 1
for b in range(bars):
    ch = b % 4; t0 = b * 4 * beat
    for k in range(8): place(music, t0 + k * beat / 2, bassn(BASS[ch], beat * 0.5, 0.11 if k % 2 == 0 else 0.07))
    for k in (0, 3, 6, 10, 12, 14):
        place(music, t0 + k * beat / 4, pl(ARP[ch][k % 4]), 0.05)
    for k in range(8):
        hs = (rng.normal(0, 1, int(0.025 * SR)) * np.exp(-np.arange(int(0.025 * SR)) / SR * 220)).astype(np.float32)
        place(music, t0 + k * beat / 2 + beat / 4, hs, 0.025)
def beep(at, f=1568, gain=0.05, dur=0.12):
    s = np.arange(int(dur * SR)) / SR
    place(music, at, (np.sign(np.sin(2 * np.pi * f * s)) * 0.5 * np.minimum(1, (dur - s) / 0.02) * np.minimum(1, s / 0.004)).astype(np.float32), gain)
def thud(at, gain=0.25):
    s = np.arange(int(0.25 * SR)) / SR
    sig = np.sin(2 * np.pi * (60 + 80 * np.exp(-s * 30)) * s) * np.exp(-s * 18) + rng.normal(0, 1, len(s)) * np.exp(-s * 70) * 0.5
    place(music, at, sig.astype(np.float32), gain)
hook_hit(music, 0.3); beep(0.02, 1760, 0.04); beep(0.16, 2093, 0.04)
for k in range(5): beep(0.2 + k * 0.28, 1320, 0.025, 0.05)
STAMPS = {"loop": [4], "micro": [8], "lineup": [3, 5, 8], "motive": [1]}
for i, ln in enumerate(spec["lines"]):
    st = ln["scene"]["type"]; s0 = ln["_s"]
    if i > 0: whoosh(music, s0 - 0.1, 0.1, 0.3); beep(s0 - 0.12, 1175, 0.03, 0.08)
    for wi in STAMPS.get(st, []):
        off = 0.35 if (st == "lineup" and wi in (3, 5)) else 0.0
        thud(s0 + wstart(ln, wi) + off + 0.12, 0.22)
    if st == "end":
        c = s0 + ln["scene"].get("click_at", 0.45)
        thud(c, 0.2); thud(c + 0.4 + 0.12, 0.26)
        for j, f in enumerate((587.33, 698.46, 880.0, 1174.66)): place(music, c + 0.15 + j * 0.06, pl(f), 0.08)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.45)

# ---------- compositing ----------
CUTS = [ln["_s"] - 0.1 for ln in spec["lines"]][1:]
groups = caption_groups(words, 3)

def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 74; f = F("tb", size)
    while f.getlength(" ".join(ws)) > W - 220 and size > 40: size -= 4; f = F("tb", size)
    tw_ = f.getlength(" ".join(ws)); x = (W - tw_) / 2; y = 1572
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([x - 40 + 6, y - 24 + 8, x + tw_ + 40 + 6, y + size + 24 + 8], fill=(0, 0, 0, 120))
    d.rectangle([x - 40, y - 24, x + tw_ + 40, y + size + 24], fill=CREAM + (255,))
    d.ellipse([x - 28, y + size / 2 - 8, x - 12, y + size / 2 + 8], fill=DESK + (255,))   # tag hole
    for i, w_ in zip(g, ws):
        on = words[i][1] <= t < words[i][2]; wl = f.getlength(w_)
        if on: d.rectangle([x - 6, y + size * 0.12, x + wl + 6, y + size * 1.02], fill=YEL + (255,))
        d.text((x, y - size * 0.02), w_, font=f, fill=INK + (255,)); x += f.getlength(w_ + " ")

def scene_img(t, ln):
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = BASE.copy()
    SCENES[ln["scene"]["type"]](img, ln, lt, dur, t)
    return img

def frame(t, fi):
    ln = active_line(spec, t, lead=0.1) or spec["lines"][0]
    img = scene_img(t, ln)
    if ln["scene"]["type"] == "end":                              # dissolve back into the hook for the loop
        lp = (t - (ln["_se"] - 0.36)) / 0.32
        if lp > 0: img = Image.blend(img, scene_img(0.0, spec["lines"][0]), ease(lp))
    for c in CUTS:                                                # scanner sweep: new exhibit wipes down over the old
        ph = t - c
        if 0 <= ph < 0.24:
            i = [l["_s"] - 0.1 for l in spec["lines"]].index(c)
            old = scene_img(t, spec["lines"][i - 1])
            yb = int(140 + (1500 - 140) * eout(ph / 0.24))
            old_c = old.crop((0, yb, W, 1520)); img.paste(old_c, (0, yb))
            scan_bar(img, yb, 0, W, 1.0)
            break
    caption(img, t)
    off = int(t * 60) % 600
    img.alpha_composite(TAPE.crop((off, 0, off + W, TAPE.height)), (0, 1752))
    d = ImageDraw.Draw(img)
    rec = (t * 1.5) % 1 < 0.6
    if rec: d.ellipse([W - 240, 60, W - 216, 84], fill=RED)
    d.text((W - 200, 54), f"00:{int(t):02d}:{int((t % 1) * 30):02d}", font=F("m", 30), fill=(200, 205, 210))
    d.rectangle([0, H - 12, W, H], fill=DESK2); d.rectangle([0, H - 12, int(W * t / total), H], fill=YEL)
    return img.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=22); print(f"done {total:.1f}s")
