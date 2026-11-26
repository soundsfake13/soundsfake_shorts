"""Day 55 — PULP-SCIFI style (it rains methane on Saturn's moon Titan).
A 1950s pulp science-fiction magazine cover that moves (fictional masthead, no real titles):
- every background is an oil-painted plate (procedural scene -> cv2.xphoto.oilPainting -> upscale), so skies,
  lakes and rocks read as brushwork: rust-to-tangerine skies, a ringed Saturn hanging in the haze, dark glossy
  methane lakes, mesas; spheres (Titan, Mercury, the Moon, Earth) are per-pixel shaded and painted the same way;
- printed on cheap pulp: yellowed paper with fibres and age stains multiplied over everything, halftone dots
  in the shadows, slight red-plate misregistration;
- type: Bangers cover lettering with a deep red 3D extrusion, black outline and yellow-to-orange face; slab-serif
  masthead strip 'STRANGE BUT TRUE' (AlfaSlab) with an issue box; Oswald for spaced labels; red starburst blurbs;
- motion: rain streaks and lake ripples run all the time, headlines slam in with overshoot, slow push-ins,
  counters; cuts are diagonal cover-banner wipes with a yellow/black edge;
- ending: a chrome rocket-age control-panel lever flips FAKE -> TRUE (red lamp -> green lamp), then dissolves
  back into the cover so the Short loops.
Music: original theremin-style gliding melody (vibrato sine) over a low minor pad, rain hiss, thunder at t=0.
Usage: python3 engine/styles/day55_pulp.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]

INK = (26, 18, 20); CRM = (246, 233, 196); YEL = (255, 214, 48); ORG = (246, 128, 30)
RED = (196, 38, 28); DRED = (110, 18, 16); CYA = (90, 200, 215); GRN = (70, 200, 90)

_F = {}
def F(name, s):
    k = (name, int(s))
    if k not in _F:
        f = ImageFont.truetype(f"{FONTS}/{name}", int(s))
        if name.startswith("Oswald"):
            try: f.set_variation_by_axes([600])
            except Exception: pass
        _F[k] = f
    return _F[k]
BANG = "Bangers-Regular.ttf"; SLAB = "AlfaSlabOne-Regular.ttf"; OSW = "Oswald-VF.ttf"

R = np.random.default_rng(55)
def fbm(h, w, seed, oct_=5, base=6, aniso=1.0):
    r = np.random.default_rng(seed); acc = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(oct_):
        gh = max(2, int(base * 2 ** o)); gw = max(2, int(base * 2 ** o * w / h * aniso))
        n = r.normal(0, 1, (gh, gw)).astype(np.float32)
        acc += amp * cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC); tot += amp; amp *= 0.5
    return acc / tot

def paint(img, size=5, half=True):
    """oil-paint a float/uint8 RGB plate (painted at half res, upscaled, re-sharpened a touch)."""
    u = np.clip(img, 0, 255).astype(np.uint8)
    h, w = u.shape[:2]
    if half: u = cv2.resize(u, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    p = cv2.xphoto.oilPainting(u, size, 1)
    if half: p = cv2.resize(p, (w, h), interpolation=cv2.INTER_CUBIC)
    bl = cv2.GaussianBlur(p, (0, 0), 2)
    return cv2.addWeighted(p, 1.4, bl, -0.4, 0)

YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
def vgrad(stops, h=H):
    y = np.linspace(0, 1, h)[:, None]
    out = np.zeros((h, 1, 3), np.float32)
    ys = [s[0] for s in stops]
    for c in range(3): out[:, 0, c] = np.interp(y[:, 0], ys, [s[1][c] for s in stops])
    return out

# ---------- spheres ----------
def sphere(r, tex, light=(-0.55, -0.45, 0.70), rim=None, rimw=0.10, amb=0.12, rot=0.0):
    pad = int(r * (rimw * 3 + 0.08)) + 4; S = 2 * (r + pad)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    nx = (xx - S / 2) / r; ny = (yy - S / 2) / r; d = np.sqrt(nx ** 2 + ny ** 2)
    nz = np.sqrt(np.clip(1 - d ** 2, 0, 1))
    lat = np.arcsin(np.clip(-ny, -1, 1)); lon = np.arctan2(nx, nz + 1e-6) + rot
    col = tex(lat, lon, nx, ny).astype(np.float32)
    L = np.array(light, np.float32); L /= np.linalg.norm(L)
    sh = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    sh = amb + (1 - amb) * sh ** 0.8
    rgb = col * sh[..., None]
    a = np.clip((1 - d) * r, 0, 1)
    if rim is not None:
        lim = np.clip(1 - nz, 0, 1) ** 3 * (0.4 + 0.6 * np.clip(-(nx * L[0] + ny * L[1]) + 0.6, 0, 1.4))
        rgb = rgb + np.array(rim, np.float32) * lim[..., None] * 0.7 * a[..., None]
        halo = np.exp(-np.clip(d - 1, 0, None) / rimw) * (d > 1)
        ha = halo * 0.85
        rgb = rgb * a[..., None] + np.array(rim, np.float32) * ha[..., None] * (1 - a[..., None])
        alpha = np.clip(a + ha, 0, 1)
        rgb = rgb / np.maximum(alpha[..., None], 1e-3)
    else:
        alpha = a
    rgb = paint(np.clip(rgb, 0, 255), 3, half=False).astype(np.float32)
    return np.dstack([rgb, alpha])

def tex_titan(lat, lon, nx, ny):
    b = 0.5 + 0.5 * np.sin(lat * 7 + 0.4 * np.sin(lon * 3))
    base = np.array((232, 150, 60), np.float32)
    c = base[None, None] * (0.86 + 0.12 * b[..., None])
    polar = np.clip((np.abs(lat) - 1.0) / 0.4, 0, 1)[..., None]
    return c * (1 - polar) + np.array((200, 120, 60), np.float32) * polar

_CR = np.random.default_rng(3).uniform(-1, 1, (70, 3))
def craters(lat, lon, base, dark, n=70, s=0.12):
    x = np.cos(lat) * np.sin(lon); y = np.sin(lat); z = np.cos(lat) * np.cos(lon)
    v = np.full(lat.shape, 1.0, np.float32)
    for k in range(n):
        p = _CR[k] / (np.linalg.norm(_CR[k]) + 1e-6)
        dd = np.sqrt((x - p[0]) ** 2 + (y - p[1]) ** 2 + (z - p[2]) ** 2)
        rr = s * (0.3 + 0.7 * abs(_CR[(k + 7) % n][0]))
        v -= 0.25 * np.clip(1 - dd / rr, 0, 1) ** 0.6 * (dd < rr)
        v += 0.12 * np.exp(-((dd - rr) / (rr * 0.15)) ** 2)
    return np.array(base, np.float32) * v[..., None] + np.array(dark, np.float32) * (1 - v[..., None]) * 0.2

def tex_mercury(lat, lon, nx, ny): return craters(lat, lon, (150, 142, 136), (60, 55, 55))
def tex_moon(lat, lon, nx, ny):
    c = craters(lat, lon, (205, 202, 195), (80, 80, 80), 50, 0.14)
    m = np.clip(np.sin(lon * 2 + 1) * np.cos(lat * 3) - 0.3, 0, 1)[..., None]
    return c * (1 - 0.35 * m)

_EN = fbm(256, 512, 9, 5, 3)
def tex_earth(lat, lon, nx, ny):
    u = ((lon / (2 * np.pi)) % 1 * 511).astype(np.int32); v = ((0.5 - lat / np.pi) * 255).clip(0, 255).astype(np.int32)
    n = _EN[v, u]
    land = n > 0.22
    c = np.where(land[..., None], np.array((96, 150, 70), np.float32), np.array((40, 95, 190), np.float32))
    c = np.where((land & (n > 0.5))[..., None], np.array((180, 150, 95), np.float32), c)
    cl = np.clip((_EN[(v * 3 + 40) % 256, (u * 2 + 100) % 512] - 0.15) * 2.5, 0, 0.9)[..., None]
    ice = np.clip((np.abs(lat) - 1.2) * 4, 0, 1)[..., None]
    c = c * (1 - cl) + 245 * cl
    return c * (1 - ice) + 240 * ice

def saturn_sprite(r):
    """painted Saturn with tilted rings, RGBA"""
    S = int(r * 5.0); cx = cy = S / 2
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    nx = (xx - cx) / r; ny = (yy - cy) / r; d = np.sqrt(nx ** 2 + ny ** 2)
    nz = np.sqrt(np.clip(1 - d ** 2, 0, 1)); lat = np.arcsin(np.clip(-ny, -1, 1))
    band = 0.5 + 0.5 * np.sin(lat * 14 + 0.3 * np.sin(lat * 40))
    col = np.array((236, 200, 140), np.float32) * (0.82 + 0.18 * band[..., None])
    L = np.array((-0.5, -0.5, 0.7)); L /= np.linalg.norm(L)
    sh = 0.15 + 0.85 * np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1) ** 0.8
    planet = col * sh[..., None]; pa = np.clip((1 - d) * r, 0, 1)
    tilt = 0.26
    v = ny / tilt; rad = np.sqrt(nx ** 2 + v ** 2)
    ring = ((rad > 1.3) & (rad < 2.25)).astype(np.float32)
    rb = 0.6 + 0.4 * np.sin(rad * 38) * np.sin(rad * 11 + 1)
    gap = 1 - 0.85 * np.exp(-((rad - 1.86) / 0.03) ** 2)
    ra = ring * np.clip((rad - 1.3) * 30, 0, 1) * np.clip((2.25 - rad) * 30, 0, 1) * gap * (0.55 + 0.4 * rb)
    rcol = np.array((240, 214, 170), np.float32) * (0.75 + 0.25 * rb[..., None])
    # planet shadow on back ring + ring shadow on planet
    front = ny > 0
    rgb = np.zeros((S, S, 3), np.float32); a = np.zeros((S, S), np.float32)
    back_ = ra * (~front)
    rgb = rcol * back_[..., None]; a = back_
    rgb = planet * pa[..., None] + rgb * (1 - pa[..., None]); a = pa + a * (1 - pa)
    rs = (np.abs(ny + 0.12 - 0.0) < 0.05) & (pa > 0)
    rgb[rs] *= 0.6
    fr = ra * front
    rgb = rcol * fr[..., None] + rgb * (1 - fr[..., None]); a = fr + a * (1 - fr)
    rgb = rgb / np.maximum(a[..., None], 1e-3) * (a[..., None] > 0)
    rgb = paint(rgb, 3, half=False).astype(np.float32)
    out = np.dstack([rgb, a])
    M = cv2.getRotationMatrix2D((cx, cy), 14, 1.0)
    return cv2.warpAffine(out, M, (S, S), flags=cv2.INTER_LINEAR)

def paste(img, spr, cx, cy, scale=1.0, alpha=1.0):
    if scale <= 0.01 or alpha <= 0: return
    if abs(scale - 1) > 1e-3:
        spr = cv2.resize(spr, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    h, w = spr.shape[:2]; x0 = int(round(cx - w / 2)); y0 = int(round(cy - h / 2))
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if xa >= xb or ya >= yb: return
    s = spr[ya - y0: yb - y0, xa - x0: xb - x0]
    a = s[..., 3:4] * alpha
    reg = img[ya:yb, xa:xb].astype(np.float32)
    img[ya:yb, xa:xb] = (reg * (1 - a) + s[..., :3] * a).astype(np.uint8)

# ---------- painted plates ----------
HOR = 1130
def mesas(img, y_base, amp, col, seed, rough=1.0):
    r = np.random.default_rng(seed)
    xs = np.arange(W)
    h = np.zeros(W, np.float32)
    for k in range(5):
        x0 = r.uniform(-100, W + 100); wd = r.uniform(120, 360); ht = r.uniform(0.3, 1.0) * amp
        h = np.maximum(h, ht * np.clip(1 - np.abs(xs - x0) / wd, 0, 1) ** 0.35)
    h += np.cumsum(r.normal(0, 1, W)) * 0.3 * rough; h -= h.min() * 0.5
    top = (y_base - h).astype(np.int32)
    for x in range(W): img[top[x]:y_base, x] = col
    return top

def cover_plate():
    sky = np.broadcast_to(vgrad([(0, (96, 30, 30)), (0.25, (170, 60, 34)), (0.45, (226, 108, 40)), (0.56, (248, 176, 98)), (0.59, (252, 205, 130)), (1, (252, 205, 130))]), (H, W, 3)).copy()
    cl = fbm(H, W, 1, 5, 5, aniso=0.25)
    band = np.clip(1 - np.abs(YY - 520) / 420, 0, 1)
    sky += (cl[..., None] * 60 * band[..., None]) * np.array((1.0, 0.7, 0.45))
    img = sky
    u = img.astype(np.uint8)
    # Saturn in the haze
    spr = saturn_sprite(150)
    paste(u, spr, 800, 860)
    img = u.astype(np.float32)
    haze = np.clip((YY - 700) / 450, 0, 1)[..., None] * 0.55
    img = img * (1 - haze) + np.array((250, 180, 110), np.float32) * haze
    u = img.astype(np.uint8)
    mesas(u, HOR + 2, 90, (176, 92, 70), 4)
    mesas(u, HOR + 2, 50, (120, 56, 52), 5)
    img = u.astype(np.float32)
    # lake: darkened reflection of the sky, streaky
    lake_rows = np.arange(HOR, H)
    src = np.clip(2 * HOR - lake_rows, 0, HOR - 1)
    refl = cv2.GaussianBlur(img[src].copy(), (0, 0), sigmaX=3, sigmaY=14)
    dep = ((lake_rows - HOR) / (H - HOR))[:, None, None]
    streak = fbm(H - HOR, W, 2, 4, 40, aniso=0.03)[..., None]
    dark = np.array((16, 18, 30), np.float32)
    lake = refl * (0.5 - 0.38 * dep) + dark * (0.5 + 0.38 * dep) + streak * 10
    img[HOR:] = lake
    # foreground rocks with rim light
    u = img.astype(np.uint8)
    for (cx0, cy0, rx, ry, s) in [(-40, 1880, 360, 230, 11), (1120, 1840, 330, 260, 12), (120, 1300, 150, 40, 13), (930, 1260, 120, 30, 14)]:
        rr = np.random.default_rng(s)
        ang = np.linspace(0, 2 * np.pi, 40)
        rad = 1 + 0.18 * rr.normal(0, 1, 40); rad = np.convolve(np.r_[rad[-3:], rad, rad[:3]], np.ones(4) / 4, "same")[3:-3]
        pts = np.stack([cx0 + rx * rad * np.cos(ang), cy0 + ry * rad * np.sin(ang)], 1).astype(np.int32)
        cv2.fillPoly(u, [pts], (52, 30, 34), cv2.LINE_AA)
        top = pts[pts[:, 1] < cy0 - ry * 0.4]
        if len(top) > 2: cv2.polylines(u, [top[np.argsort(top[:, 0])]], False, (230, 130, 60), 5, cv2.LINE_AA)
    return paint(u, 5)

def space_plate(seed=6):
    img = np.broadcast_to(vgrad([(0, (14, 12, 30)), (0.5, (30, 18, 40)), (1, (16, 12, 26))]), (H, W, 3)).copy()
    n = fbm(H, W, seed, 5, 3)
    img += np.clip(n * 1.2, 0, 1)[..., None] * np.array((120, 55, 30), np.float32) * 0.45
    img += np.clip(-n * 1.2, 0, 1)[..., None] * np.array((20, 40, 70), np.float32) * 0.6
    u = paint(img, 5)
    r = np.random.default_rng(seed); lay = np.zeros_like(u)
    for _ in range(380):
        x, y = r.integers(0, W), r.integers(0, H); b = r.uniform(110, 255)
        cv2.circle(lay, (int(x), int(y)), int(r.choice([1, 1, 2, 2, 3])), (int(b), int(b * 0.95), int(b * 0.82)), -1, cv2.LINE_AA)
    lay = cv2.add(lay, cv2.GaussianBlur(lay, (0, 0), 4))
    return cv2.add(u, lay)

def rain_plate():
    img = np.broadcast_to(vgrad([(0, (60, 34, 34)), (0.3, (140, 70, 40)), (0.42, (220, 140, 80)), (0.44, (150, 90, 60)), (1, (96, 56, 40))]), (H, W, 3)).copy()
    cl = fbm(H, W, 21, 5, 5, aniso=0.35)[..., None]
    up = (YY < 820)[..., None]
    img += up * cl * 50 * np.array((0.8, 0.5, 0.4))
    gr = fbm(H, W, 22, 5, 10, aniso=0.5)[..., None]
    img += (~up) * gr * 40 * np.array((0.9, 0.6, 0.4))
    img += (~up) * np.clip((YY[..., None] - 820) / 1100, 0, 1) * np.array((40, 22, 10))
    u = img.astype(np.uint8)
    mesas(u, 830, 70, (150, 80, 62), 24); mesas(u, 830, 36, (110, 58, 50), 25)
    return paint(u, 5)

# river path: from horizon (narrow) meandering toward the viewer (wide)
def river_path():
    ys = np.linspace(830, 1920, 160)
    u = (ys - 830) / (1920 - 830)
    xs = 540 + 300 * np.sin(u * 5.2 + 0.4) * (0.25 + u) - 80 * u
    wd = 8 + 150 * u ** 1.6
    return np.stack([xs, ys], 1), wd
RIV, RIVW = river_path()

def land_plate():
    n = fbm(H, W, 31, 6, 4)
    rel = cv2.Sobel(cv2.GaussianBlur(n, (0, 0), 3), cv2.CV_32F, 1, 1, ksize=3)
    img = np.array((206, 128, 64), np.float32) + n[..., None] * np.array((60, 40, 20)) + rel[..., None] * 900
    dune = np.sin((XX * 0.6 + YY) / 14 + n * 6)[..., None]
    img += dune * 8
    return paint(img, 5), n

def lake_plate():
    n = fbm(H, W, 32, 4, 8, aniso=0.6)
    img = np.array((20, 26, 42), np.float32) + n[..., None] * np.array((14, 18, 30))
    glint = np.clip(1 - np.abs((XX - 700) * 0.6 + (YY - 700) * 0.3) / 260, 0, 1) ** 2
    img += glint[..., None] * np.array((150, 110, 70)) * 0.5
    return paint(img, 4)

def ice_plate():
    img = np.broadcast_to(vgrad([(0, (20, 30, 60)), (0.6, (44, 70, 110)), (1, (24, 34, 64))]), (H, W, 3)).copy()
    n = fbm(H, W, 41, 6, 5)
    cr = np.abs(fbm(H, W, 42, 5, 6)); veins = np.clip(1 - cr * 18, 0, 1)
    img += n[..., None] * 30 + veins[..., None] * np.array((120, 170, 210)) * 0.5
    edge = np.clip(1 - np.minimum(np.minimum(XX, W - XX), np.minimum(YY, H - YY)) / 160, 0, 1) ** 2
    img = img * (1 - edge[..., None] * 0.5) + edge[..., None] * np.array((210, 230, 250)) * 0.5
    return paint(img, 5)

print("painting plates…", flush=True)
COVER = cover_plate(); SPACE = space_plate(); RAINP = rain_plate(); LAND, LANDN = land_plate(); LAKE = lake_plate(); ICE = ice_plate()
SP_TITAN = sphere(170, tex_titan, rim=(250, 170, 80), rimw=0.09)
SP_MERC = sphere(161, tex_mercury); SP_MOON = sphere(109, tex_moon)
SP_TITAN2 = sphere(190, tex_titan, rim=(250, 170, 80), rimw=0.09)
SP_EARTH = sphere(190, tex_earth, rim=(120, 180, 255), rimw=0.07)

# ---------- paper finish ----------
def make_paper():
    r = np.random.default_rng(155)
    g = cv2.GaussianBlur(r.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 1.0)
    fib = cv2.GaussianBlur(r.normal(0, 1, (H, W)).astype(np.float32), (0, 0), sigmaX=7, sigmaY=0.7)
    stain = fbm(H, W, 156, 4, 3)
    edge = np.clip(1 - np.minimum(np.minimum(XX, W - XX), np.minimum(YY, H - YY)) / 70, 0, 1)
    m = np.stack([1 + 0.02 * g + 0.015 * fib - 0.02 * stain - 0.10 * edge,
                  1 + 0.02 * g + 0.015 * fib - 0.035 * stain - 0.13 * edge,
                  1 + 0.02 * g + 0.015 * fib - 0.07 * stain - 0.20 * edge], -1) * np.array((1.0, 0.97, 0.88))
    return m.astype(np.float32)
PAPER = make_paper()
pp = 7.0
HT = ((np.sin(2 * np.pi * (XX + YY) / (pp * 1.414)) * np.sin(2 * np.pi * (XX - YY) / (pp * 1.414)) + 1) / 2).astype(np.float32)

def finish(img):
    f = img.astype(np.float32)
    L = f.mean(2) / 255
    dots = np.clip(((1 - L) * 0.85 - HT) * 5, 0, 1) * np.clip((0.62 - L) * 3, 0, 1)
    f *= (1 - 0.32 * dots)[..., None]
    f[..., 0] = np.roll(f[..., 0], 2, axis=1); f[..., 2] = np.roll(f[..., 2], -1, axis=0)
    return f * PAPER

# ---------- type ----------
def tmask(s, font, size, track=0):
    f = F(font, size)
    tw = sum(f.getlength(c) for c in s) + track * (len(s) - 1) if track else f.getlength(s)
    asc, desc = f.getmetrics()
    im = Image.new("L", (int(tw) + 40, asc + desc + 40), 0); d = ImageDraw.Draw(im)
    if track:
        x = 20
        for c in s: d.text((x, 20), c, font=f, fill=255); x += f.getlength(c) + track
    else: d.text((20, 20), s, font=f, fill=255)
    m = np.asarray(im).astype(np.float32) / 255
    ys = np.where(m.max(1) > 0.02)[0]; xs = np.where(m.max(0) > 0.02)[0]
    return m[ys[0]: ys[-1] + 1, xs[0]: xs[-1] + 1]

_HL = {}
def hl_patch(s, size, face=(YEL, ORG), ext=DRED, depth=None, font=BANG, outline=None):
    k = (s, size, face, ext, depth, font)
    if k in _HL: return _HL[k]
    m = tmask(s, font, size)
    depth = depth or max(4, size // 12); ow = outline or max(3, size // 18)
    pad = ow + 4; h, w = m.shape
    P_ = np.zeros((h + 2 * pad + depth, w + 2 * pad + depth), np.float32)
    P_[pad:pad + h, pad:pad + w] = m
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * ow + 1, 2 * ow + 1))
    o = cv2.dilate(P_, kern)
    E = np.zeros_like(o)
    for d in range(1, depth + 1):
        M = np.float32([[1, 0, d * 0.6], [0, 1, d]]); E = np.maximum(E, cv2.warpAffine(o, M, o.shape[::-1]))
    rgb = np.zeros(o.shape + (3,), np.float32)
    shade = np.linspace(1.0, 0.65, o.shape[0])[:, None, None]
    rgb[:] = np.array(ext, np.float32) * shade
    a = np.maximum(E, o)
    rgb = rgb * (1 - o[..., None]) + np.array(INK, np.float32) * o[..., None]
    gy = np.clip((np.arange(o.shape[0]) - pad) / max(1, h), 0, 1)[:, None, None]
    fc = np.array(face[0], np.float32) * (1 - gy) + np.array(face[1], np.float32) * gy
    rgb = rgb * (1 - P_[..., None]) + fc * P_[..., None]
    out = np.dstack([rgb, a]); _HL[k] = out
    return out

def headline(img, s, size, cx, y, prog=1.0, rot=0.0, anchor="c", **kw):
    """y = top of letters. prog: slam-in scale with overshoot."""
    if prog <= 0: return
    p = hl_patch(s, size, **kw)
    if rot:
        h, w = p.shape[:2]; d = int(math.hypot(h, w)) + 4
        big = np.zeros((d, d, 4), np.float32); big[(d - h) // 2:(d - h) // 2 + h, (d - w) // 2:(d - w) // 2 + w] = p
        p = cv2.warpAffine(big, cv2.getRotationMatrix2D((d / 2, d / 2), rot, 1), (d, d))
    sc = back(min(1, prog), 2.2) if prog < 1 else 1.0
    sc = 0.4 + 0.6 * sc if prog < 1 else 1.0
    h, w = p.shape[:2]
    x = cx if anchor == "c" else (cx + w / 2 if anchor == "l" else cx - w / 2)
    paste(img, p, x, y + h / 2, sc, min(1, prog * 3))

def txt(img, s, size, x, y, col, anchor="c", font=OSW, track=0, a=1.0, shadow=None):
    m = tmask(s, font, size, track); h, w = m.shape
    x0 = x - w / 2 if anchor == "c" else (x - w if anchor == "r" else x)
    if shadow is not None: blend(img, m, x0 + 4, y + 5, shadow, a)
    blend(img, m, x0, y, col, a)
    return w

def blend(img, m, x0, y0, col, a=1.0):
    h, w = m.shape; x0, y0 = int(round(x0)), int(round(y0))
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if xa >= xb or ya >= yb: return
    mm = m[ya - y0: yb - y0, xa - x0: xb - x0, None] * a
    reg = img[ya:yb, xa:xb].astype(np.float32)
    img[ya:yb, xa:xb] = (reg * (1 - mm) + np.array(col, np.float32) * mm).astype(np.uint8)

def burst(img, cx, cy, r, lines, prog=1.0, col=RED, tcol=YEL, spin=0.0, size=54):
    if prog <= 0: return
    u = back(min(1, prog), 2.4); rr = r * u
    n = 18; pts = []
    for k in range(2 * n):
        a = math.pi * k / n + spin; q = rr if k % 2 == 0 else rr * 0.78
        pts.append((cx + q * math.cos(a), cy + q * math.sin(a)))
    pts = np.array(pts) * 16
    cv2.fillPoly(img, [(pts + np.array([10 * 16, 12 * 16])).astype(np.int32)], INK, cv2.LINE_AA, 4)
    cv2.fillPoly(img, [pts.astype(np.int32)], col, cv2.LINE_AA, 4)
    cv2.polylines(img, [pts.astype(np.int32)], True, INK, 5, cv2.LINE_AA, 4)
    if u > 0.7:
        tot = len(lines) * size * 1.05; y = cy - tot / 2
        for s in lines:
            txt(img, s, size, cx, y, tcol, font=BANG, shadow=INK); y += size * 1.05

def banner(img, s, cx, cy, size, prog=1.0, rot=-4, col=RED, tcol=YEL):
    if prog <= 0: return
    m = tmask(s, BANG, size); h, w = m.shape
    bw, bh = w + 90, h + 50
    pat = np.zeros((bh + 30, bw + 30, 4), np.float32)
    cv2.rectangle(pat, (16, 18), (16 + bw, 18 + bh), (*INK, 1), -1)
    cv2.rectangle(pat, (4, 4), (4 + bw, 4 + bh), (*col, 1), -1)
    cv2.rectangle(pat, (4, 4), (4 + bw, 4 + bh), (*INK, 1), 5)
    tm = np.zeros(pat.shape[:2], np.float32); tm[4 + 25:4 + 25 + h, 4 + 45:4 + 45 + w] = m
    sh = np.roll(np.roll(tm, 4, 0), 4, 1)
    for c in range(3): pat[..., c] = pat[..., c] * (1 - sh) + INK[c] * sh
    for c in range(3): pat[..., c] = pat[..., c] * (1 - tm) + tcol[c] * tm
    d = int(math.hypot(*pat.shape[:2])) + 4; big = np.zeros((d, d, 4), np.float32)
    ph, pw = pat.shape[:2]; big[(d - ph) // 2:(d - ph) // 2 + ph, (d - pw) // 2:(d - pw) // 2 + pw] = pat
    big = cv2.warpAffine(big, cv2.getRotationMatrix2D((d / 2, d / 2), rot, 1), (d, d))
    u = min(1, prog)
    paste(img, big, cx + (1 - eout(u)) * -700, cy, 1.0, 1.0)

def masthead(img):
    cv2.rectangle(img, (0, 0), (W, 150), RED, -1)
    cv2.rectangle(img, (0, 150), (W, 160), INK, -1)
    cv2.rectangle(img, (0, 160), (W, 166), YEL, -1)
    txt(img, "STRANGE BUT TRUE", 60, 40, 44, CRM, "l", font=SLAB, shadow=INK)
    cv2.rectangle(img, (848, 26), (1040, 126), CRM, -1); cv2.rectangle(img, (848, 26), (1040, 126), INK, 4)
    txt(img, "TITAN ISSUE", 26, 944, 40, INK, track=2)
    txt(img, "No. 55", 40, 944, 74, RED, font=SLAB)

# ---------- overlays: rain, ripples ----------
RN = np.random.default_rng(77)
DROPS = [(RN.uniform(-200, W), RN.uniform(0, H), RN.uniform(1300, 2100), RN.uniform(30, 70), RN.uniform(0.5, 1)) for _ in range(260)]
def rain(img, t, y_max=H, dens=1.0, slant=0.22, col=(255, 226, 180), gain=0.45, y_min=0):
    lay = np.zeros_like(img)
    for i, (x0, y0, sp, ln, b) in enumerate(DROPS):
        if i > len(DROPS) * dens: break
        y = (y0 + sp * t) % (H + 200) - 100
        if y < y_min or y > y_max: continue
        x = (x0 + slant * sp * t) % (W + 200) - 100
        c = tuple(int(v * b) for v in col)
        cv2.line(lay, (int(x), int(y)), (int(x - slant * ln), int(y - ln)), c, 2, cv2.LINE_AA)
    cv2.add(img, (lay * gain).astype(np.uint8), img)

RIP = [(RN.uniform(80, W - 80), RN.uniform(HOR + 40, H - 60), RN.uniform(0, 1)) for _ in range(40)]
def ripples(img, t, y0=HOR, sc=1.0):
    lay = np.zeros_like(img)
    for (x, y, ph) in RIP:
        q = (t * 0.9 + ph) % 1.0
        dep = (y - y0) / (H - y0)
        r = (10 + 60 * q) * (0.4 + dep) * sc
        b = int(150 * (1 - q))
        cv2.ellipse(lay, (int(x), int(y)), (int(r), int(r * 0.22)), 0, 0, 360, (b, int(b * 0.75), int(b * 0.5)), 2, cv2.LINE_AA)
    cv2.add(img, lay, img)

def wstart(ln, k):
    i = next(j for j in range(ln["_w1"] - ln["_w0"]) if words[ln["_w0"] + j][0].lower().strip(".,?!:") == k)
    return words[ln["_w0"] + i][1] - ln["_s"]

def zoom(plate, cx, cy, s):
    M = np.float32([[s, 0, W / 2 - s * cx], [0, s, H / 2 - s * cy]])
    return cv2.warpAffine(plate, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

# ---------- scenes ----------
def hook(ln, lt, dur, t):
    img = COVER.copy()
    ripples(img, t); rain(img, t)
    masthead(img)
    headline(img, "IT RAINS", 190, 540, 220)
    headline(img, "ON TITAN.", 190, 540, 430)
    b = wstart(ln, "but")
    banner(img, "BUT NOT WATER!", 540, 720, 104, eout((lt - b + 0.05) / 0.3), rot=-4)
    return img

def why(ln, lt, dur, t):
    s = 1.0 + 0.35 * ease(lt / max(dur, 0.1))
    img = zoom(COVER, 540, 1250, s)
    ripples(img, t, sc=s); rain(img, t, dens=0.8)
    masthead(img)
    headline(img, "WHAT FILLS", 150, 540, 240, eout(lt / 0.25))
    headline(img, "ITS LAKES?", 150, 540, 420, eout((lt - 0.2) / 0.25), face=(CRM, YEL))
    st = wstart(ln, "stay")
    burst(img, 760, 830, 175, ["STAY", "FOR IT!"], (lt - st + 0.1) / 0.35, spin=lt * 0.3, size=58)
    return img

def size_(ln, lt, dur, t):
    img = zoom(SPACE, 540, 960, 1.0 + 0.03 * lt)
    masthead(img)
    headline(img, "BIGGER THAN", 140, 540, 230, eout(lt / 0.25))
    headline(img, "A PLANET!", 170, 540, 400, eout((lt - wstart(ln, "larger") + 0.1) / 0.3), face=(YEL, ORG))
    y = 960
    for i, (spr, x, name, sub) in enumerate([(SP_MOON, 150, "OUR MOON", ""), (SP_MERC, 425, "MERCURY", "A PLANET"), (SP_TITAN, 800, "TITAN", "A MOON")]):
        at = 0.25 + 0.35 * i if i < 2 else wstart(ln, "titan") + 0.0
        if i == 1: at = wstart(ln, "larger") - 0.1
        if i == 2: at = 0.1
        u = (lt - at) / 0.4
        if u <= 0: continue
        paste(img, spr, x, y + 6 * math.sin(t * 1.5 + i), back(min(1, u), 1.8))
        a = min(1, max(0, (u - 0.5) * 3))
        txt(img, name, 46, x, 1210, CRM if i < 2 else YEL, track=4, a=a, shadow=INK)
        if sub: txt(img, sub, 30, x, 1272, (230, 170, 120), track=5, a=a)
    lb = wstart(ln, "larger")
    q = eout((lt - lb) / 0.4)
    if q > 0:
        y0 = 1350; x0 = 425 - 161; x1 = 800 + 170
        cv2.line(img, (x0, y0), (int(x0 + (x1 - x0) * q), y0), YEL, 5, cv2.LINE_AA)
    txt(img, "TO SCALE", 26, 540, 1380, (200, 180, 160), track=8, a=min(1, max(0, (lt - lb) * 2)))
    return img

def cold(ln, lt, dur, t):
    img = zoom(ICE, 540, 960, 1.04 - 0.03 * lt / max(dur, 0.1))
    masthead(img)
    headline(img, "BRRR!", 170, 540, 220, eout(lt / 0.25), face=(CRM, CYA), ext=(20, 50, 100))
    # thermometer
    tx, ty0, ty1 = 260, 420, 1330
    cv2.rectangle(img, (tx - 70 + 10, ty0 - 30 + 12), (tx + 70 + 10, ty1 + 12), INK, -1)
    cv2.rectangle(img, (tx - 70, ty0 - 30), (tx + 70, ty1), (205, 215, 225), -1)
    cv2.rectangle(img, (tx - 70, ty0 - 30), (tx + 70, ty1), INK, 6)
    cv2.circle(img, (tx + 8, ty1 + 80), 105, INK, -1)
    cv2.circle(img, (tx, ty1 + 70), 105, INK, -1); cv2.circle(img, (tx, ty1 + 70), 95, (40, 120, 220), -1)
    cv2.circle(img, (tx - 35, ty1 + 35), 22, (190, 230, 255), -1, cv2.LINE_AA)
    q = ease((lt - 0.15) / 1.6)
    temp = 20 - 199 * q
    level = ty0 + 60 + (ty1 - ty0 - 120) * 0.78 * q
    cv2.rectangle(img, (tx - 26, int(level)), (tx + 26, ty1 + 10), (40, 120, 220), -1)
    for k in range(9):
        yk = ty0 + 30 + k * (ty1 - ty0 - 60) / 8
        cv2.line(img, (tx + 70, int(yk)), (tx + 110, int(yk)), INK, 6)
    cv2.line(img, (tx - 45, ty0), (tx - 45, ty1 - 40), (255, 255, 255), 6, cv2.LINE_AA)
    headline(img, f"{temp:+.0f}°C".replace("+0", "0"), 200, 700, 640, 1.0, face=(CRM, CYA), ext=(20, 50, 100))
    txt(img, "ABOUT", 40, 700, 590, CRM, track=8, shadow=INK)
    wa = wstart(ln, "far")
    u = (lt - wa + 0.1) / 0.35
    if u > 0:
        # ice cube
        cx, cy = 700, 1140; s = 120 * back(min(1, u), 2)
        pts = np.array([(cx - s, cy - s * 0.6), (cx, cy - s), (cx + s, cy - s * 0.6), (cx + s, cy + s * 0.5), (cx, cy + s), (cx - s, cy + s * 0.5)], np.int32)
        cv2.fillPoly(img, [pts + 10], INK, cv2.LINE_AA)
        cv2.fillPoly(img, [pts], (170, 215, 245), cv2.LINE_AA)
        cv2.fillPoly(img, [np.array([(cx - s, cy - s * 0.6), (cx, cy - s), (cx + s, cy - s * 0.6), (cx, cy - s * 0.2)], np.int32)], (235, 248, 255), cv2.LINE_AA)
        cv2.fillPoly(img, [np.array([(cx, cy - s * 0.2), (cx + s, cy - s * 0.6), (cx + s, cy + s * 0.5), (cx, cy + s)], np.int32)], (120, 175, 220), cv2.LINE_AA)
        cv2.polylines(img, [pts], True, INK, 6, cv2.LINE_AA)
        if u > 0.6: banner(img, "TOO COLD FOR WATER", 610, 1390, 54, min(1, (u - 0.6) * 3), rot=3, col=(30, 70, 140), tcol=CRM)
    return img

def rain_(ln, lt, dur, t):
    img = zoom(RAINP, 540, 960, 1.0 + 0.04 * lt)
    q = ease((lt - 0.4) / 2.2)
    n = max(2, int(len(RIV) * q))
    if q > 0:
        for k in range(1, n):
            a, b = RIV[k - 1], RIV[k]; w = RIVW[k]
            cv2.line(img, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (70, 40, 34), int(w + 18), cv2.LINE_AA)
        for k in range(1, n):
            a, b = RIV[k - 1], RIV[k]; w = RIVW[k]
            cv2.line(img, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (34, 38, 56), int(w), cv2.LINE_AA)
        for k in range(1, n):
            a, b = RIV[k - 1], RIV[k]; w = RIVW[k]
            cv2.line(img, (int(a[0] - w * 0.25), int(a[1])), (int(b[0] - w * 0.25), int(b[1])), (200, 140, 90), max(2, int(w * 0.08)), cv2.LINE_AA)
    rain(img, t * 1.3, dens=1.0, slant=0.3, gain=0.6)
    masthead(img)
    headline(img, "METHANE", 170, 540, 230, eout(lt / 0.25))
    headline(img, "RAIN!", 210, 540, 420, eout((lt - wstart(ln, "methane") + 0.1) / 0.3), face=(CRM, CYA), ext=(20, 50, 100))
    rv = wstart(ln, "rivers")
    burst(img, 820, 1310, 150, ["REAL", "RIVERS!"], (lt - rv + 0.15) / 0.35, spin=lt * 0.3, size=50)
    return img

def lakes(ln, lt, dur, t):
    s = 1.12 - 0.08 * ease(lt / max(dur, 0.1))
    land = zoom(LAND, 540, 980, s); lake = zoom(LAKE, 540, 980, s)
    nn = zoom(LANDN[..., None].repeat(3, 2), 540, 980, s)[..., 0]
    level = -0.25 + 0.42 * ease((lt - 0.1) / 2.2)
    m = np.clip((level - nn) * 22, 0, 1)[..., None]
    img = (land * (1 - m) + lake * m).astype(np.uint8)
    edge = np.clip(1 - np.abs(level - nn) * 60, 0, 1)
    img[edge > 0.5] = (240, 190, 120)
    masthead(img)
    headline(img, "LAKES OF", 150, 540, 220, eout(lt / 0.25))
    headline(img, "NATURAL GAS!", 140, 540, 390, eout((lt - wstart(ln, "natural") + 0.1) / 0.3), face=(CRM, CYA), ext=(20, 50, 100))
    u = (lt - wstart(ln, "kind") + 0.1) / 0.35
    if u > 0:
        cx, cy, r = 760, 1180, int(190 * back(min(1, u), 1.6))
        cv2.circle(img, (cx + 12, cy + 14), r + 16, INK, -1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), r + 16, YEL, -1, cv2.LINE_AA); cv2.circle(img, (cx, cy), r + 16, INK, 6, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), r, (36, 30, 40), -1, cv2.LINE_AA)
        if r > 150:
            # burner + blue flame tongues
            cv2.ellipse(img, (cx, cy + 50), (120, 30), 0, 0, 360, (90, 90, 96), -1, cv2.LINE_AA)
            cv2.ellipse(img, (cx, cy + 50), (120, 30), 0, 0, 360, INK, 4, cv2.LINE_AA)
            lay = np.zeros_like(img)
            for k in range(11):
                a = math.pi * 2 * k / 11
                bx, by = cx + 110 * math.cos(a), cy + 50 + 26 * math.sin(a)
                hgt = 55 + 18 * math.sin(t * 17 + k * 2.1)
                cv2.ellipse(lay, (int(bx), int(by - hgt / 2)), (11, int(hgt / 2)), 0, 0, 360, (60, 120, 255), -1, cv2.LINE_AA)
                cv2.ellipse(lay, (int(bx), int(by - hgt / 4)), (5, int(hgt / 4)), 0, 0, 360, (180, 220, 255), -1, cv2.LINE_AA)
            lay = cv2.GaussianBlur(lay, (0, 0), 2)
            cv2.add(img, lay, img)
            txt(img, "SAME GAS", 40, cx, cy - 140, YEL, track=6)
    return img

def only(ln, lt, dur, t):
    img = zoom(SPACE, 540, 960, 1.04 - 0.03 * lt)
    masthead(img)
    headline(img, "ONLY TWO", 160, 540, 220, eout(lt / 0.25))
    headline(img, "KNOWN WORLDS", 120, 540, 410, eout((lt - 0.2) / 0.3), face=(CRM, YEL))
    ue = (lt - wstart(ln, "earth") + 0.1) / 0.4
    paste(img, SP_EARTH, 290, 900 + 8 * math.sin(t * 1.4), back(min(1, max(0, ue)), 1.8) if ue > 0 else 0)
    paste(img, SP_TITAN2, 790, 900 + 8 * math.sin(t * 1.4 + 2), back(min(1, max(0, (lt - 0.05) / 0.4)), 1.8))
    if ue > 0.6:
        txt(img, "EARTH", 46, 290, 1140, CRM, track=4, shadow=INK)
        txt(img, "TITAN", 46, 790, 1140, YEL, track=4, shadow=INK)
    wl = (lt - wstart(ln, "liquid") + 0.1) / 0.35
    banner(img, "WITH LIQUID ON THE SURFACE", 540, 1330, 58, wl, rot=-3)
    txt(img, "NOT TO SCALE", 24, 540, 1450, (200, 180, 160), track=8, a=0.8 if ue > 0 else 0)
    return img

COVER_DIM = (COVER.astype(np.float32) * 0.45).astype(np.uint8)
def end(ln, lt, dur, t):
    img = COVER_DIM.copy()
    rain(img, t, gain=0.3)
    masthead(img)
    cl = ln["scene"].get("click_at", 0.45)
    headline(img, "SOUNDS FAKE?", 130, 540, 230, 1.0, face=(CRM, YEL))
    u = ease((lt - cl) / 0.3)
    headline(img, "IT'S TRUE!", 190, 540, 410, eout((lt - cl - 0.15) / 0.3))
    # chrome control panel
    x0, y0, x1, y1 = 120, 720, 960, 1120
    cv2.rectangle(img, (x0 + 14, y0 + 16), (x1 + 14, y1 + 16), INK, -1)
    g = vgrad([(0, (235, 235, 238)), (0.45, (150, 152, 160)), (0.5, (205, 206, 212)), (1, (110, 112, 120))], y1 - y0)
    img[y0:y1, x0:x1] = np.broadcast_to(g, (y1 - y0, x1 - x0, 3)).astype(np.uint8)
    cv2.rectangle(img, (x0, y0), (x1, y1), INK, 7)
    for (rx, ry) in [(x0 + 28, y0 + 28), (x1 - 28, y0 + 28), (x0 + 28, y1 - 28), (x1 - 28, y1 - 28)]:
        cv2.circle(img, (rx, ry), 12, (90, 90, 96), -1, cv2.LINE_AA); cv2.circle(img, (rx, ry), 12, INK, 3, cv2.LINE_AA)
    sy = 960; sx0, sx1 = 330, 750
    cv2.rectangle(img, (sx0 - 30, sy - 22), (sx1 + 30, sy + 22), INK, -1)
    kx = sx0 + (sx1 - sx0) * u
    # lamps
    lamp_off = (70, 40, 40)
    cr = RED if u < 0.5 else (90, 40, 36); cg = GRN if u > 0.5 else (40, 70, 44)
    for (lx, c) in [(215, cr), (865, cg)]:
        cv2.circle(img, (int(lx), 800), 40, INK, -1, cv2.LINE_AA); cv2.circle(img, (int(lx), 800), 32, c, -1, cv2.LINE_AA)
        cv2.circle(img, (int(lx) - 10, 790), 9, (255, 255, 255), -1, cv2.LINE_AA)
    txt(img, "FAKE", 64, 215, 1010, INK if u < 0.5 else (90, 90, 96), font=BANG)
    txt(img, "TRUE", 64, 865, 1010, INK if u > 0.5 else (90, 90, 96), font=BANG)
    if u < 0.5: cv2.line(img, (150, 1080), (280, 1060), RED, 8, cv2.LINE_AA)
    # lever: stem + red ball
    ang = -0.35 + 0.7 * u
    tx_, ty_ = kx + 100 * math.sin(ang), sy - 100 * math.cos(ang)
    cv2.line(img, (int(kx), sy), (int(tx_), int(ty_)), INK, 26, cv2.LINE_AA)
    cv2.line(img, (int(kx), sy), (int(tx_), int(ty_)), (200, 200, 208), 14, cv2.LINE_AA)
    cv2.circle(img, (int(tx_) + 6, int(ty_) + 8), 48, INK, -1, cv2.LINE_AA)
    cv2.circle(img, (int(tx_), int(ty_)), 46, RED, -1, cv2.LINE_AA)
    cv2.circle(img, (int(tx_), int(ty_)), 46, INK, 5, cv2.LINE_AA)
    cv2.circle(img, (int(tx_) - 14, int(ty_) - 16), 12, (255, 190, 170), -1, cv2.LINE_AA)
    banner(img, "FOLLOW FOR MORE", 540, 1300, 80, (lt - cl - 0.5) / 0.35, rot=-3)
    return img

SCENES = {"hook": hook, "why": why, "size": size_, "cold": cold, "rain": rain_, "lakes": lakes, "only": only, "end": end}

# ---------- narration + music ----------
voice, words, total = narrate(spec, lead=0.08)
n = len(voice); music = np.zeros(n, np.float32)
A3 = 220.0
def nt(semi): return A3 * 2 ** (semi / 12)
def theremin(notes, at, gain=0.05):
    """notes: [(semi, dur)] with portamento between them, vibrato."""
    total_d = sum(d for _, d in notes); N = int(total_d * SR); s = np.arange(N) / SR
    f = np.zeros(N, np.float32); k = 0
    prev = nt(notes[0][0])
    for semi, d in notes:
        m = int(d * SR); tgt = nt(semi)
        ramp = np.clip(np.arange(m) / (0.12 * SR), 0, 1)
        f[k:k + m] = prev + (tgt - prev) * ramp; prev = tgt; k += m
    f *= 1 + 0.012 * np.sin(2 * np.pi * 5.8 * s) * np.clip(s / 0.4, 0, 1)
    ph = 2 * np.pi * np.cumsum(f) / SR
    sig = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)
    env = np.clip(s / 0.15, 0, 1) * np.clip((total_d - s) / 0.4, 0, 1)
    place(music, at, (sig * env).astype(np.float32), gain)
def pad(f, at, dur, gain=0.04):
    s = np.arange(int(dur * SR)) / SR
    sig = sum(np.sin(2 * np.pi * f * m * s + m) / m for m in (1, 1.005, 2, 3))
    env = np.clip(s / 0.8, 0, 1) * np.clip((dur - s) / 0.8, 0, 1)
    place(music, at, (sig * env).astype(np.float32), gain)
# minor pad progression Am - F - Dm - E, 4 s each
PR = [(-12, -5, 0), (-16, -9, -4), (-19, -12, -7), (-17, -13, -10)]
for k in range(int(total / 4) + 1):
    for semi in PR[k % 4]: pad(nt(semi), k * 4, 4.6, 0.025)
    place(music, k * 4, tone(nt(PR[k % 4][0] - 12), 1.8, 1.5, (1, 2)), 0.12)
MEL = [[(12, 0.8), (15, 0.6), (19, 1.2), (17, 0.7), (15, 0.7)], [(8, 0.8), (12, 0.6), (15, 1.4), (14, 1.2)],
       [(5, 0.8), (8, 0.7), (12, 1.2), (10, 1.3)], [(11, 1.0), (14, 0.8), (16, 1.0), (19, 1.2)]]
for k in range(int(total / 4) + 1): theremin(MEL[k % 4], k * 4 + 0.1, 0.035)
# rain hiss + thunder
hiss = np.random.default_rng(1).normal(0, 1, n).astype(np.float32)
hiss = hiss - np.convolve(hiss, np.ones(8) / 8, mode="same")
music += hiss * 0.02
tt = np.arange(int(2.0 * SR)) / SR
thunder = np.convolve(np.random.default_rng(2).normal(0, 1, len(tt)), np.ones(120) / 120, mode="same") * np.exp(-tt * 2.2) * 6
place(music, 0.0, thunder.astype(np.float32), 0.25)
hook_hit(music, 0.35)
for i, ln in enumerate(spec["lines"]):
    s0 = ln["_s"]
    if i > 0: whoosh(music, s0 - 0.1, 0.12, 0.4); place(music, s0, tone(nt(-24), 0.5, 6, (1, 2)), 0.15)
    if ln["scene"]["type"] == "end":
        c = s0 + ln["scene"].get("click_at", 0.45)
        place(music, c, tone(1400, 0.08, 60, (1,)), 0.15)
        for j, sm in enumerate((12, 15, 19, 24)): place(music, c + 0.2 + j * 0.08, tone(nt(sm), 0.9, 3, (1, 2)), 0.06)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.45)

# ---------- compositing ----------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 84
    f = F(BANG, size)
    while f.getlength(" ".join(ws)) > W - 260 and size > 50: size -= 4; f = F(BANG, size)
    gap = f.getlength(" ") + 12
    wl = [tmask(w, BANG, size).shape[1] for w in ws]
    tw_ = sum(wl) + gap * (len(ws) - 1); x = (W - tw_) / 2; y = 1585
    hh = int(size * 0.95)
    cv2.rectangle(img, (int(x - 40 + 12), y - 26 + 14), (int(x + tw_ + 40 + 12), y + hh + 26 + 14), INK, -1)
    cv2.rectangle(img, (int(x - 40), y - 26), (int(x + tw_ + 40), y + hh + 26), CRM, -1)
    cv2.rectangle(img, (int(x - 40), y - 26), (int(x + tw_ + 40), y + hh + 26), INK, 6)
    for i, w, ww in zip(g, ws, wl):
        on = words[i][1] <= t < words[i][2]
        if on: cv2.rectangle(img, (int(x - 10), y - 12), (int(x + ww + 10), y + hh + 12), RED, -1)
        m = tmask(w, BANG, size)
        blend(img, m, x, y + (hh - m.shape[0]) / 2 if m.shape[0] < hh else y, YEL if on else INK)
        x += ww + gap

def scene_img(t, ln):
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    return SCENES[ln["scene"]["type"]](ln, lt, dur, t)

def frame(t, fi):
    lines = spec["lines"]; ln = active_line(spec, t) or lines[0]; i = lines.index(ln)
    img = scene_img(t, ln)
    if i > 0:
        ph = (t - (ln["_s"] - 0.12)) / 0.36
        if ph < 1:
            old = scene_img(ln["_s"] - 0.12, lines[i - 1])
            p = eout(ph) * (W + H * 0.45 + 160) - 80
            d = XX + (H - YY) * 0.45 if i % 2 else (W - XX) + (H - YY) * 0.45
            new_m = (d < p - 60)[..., None]; band_ = ((d >= p - 60) & (d < p))
            stripes = ((XX + YY) // 26 % 2 == 0)
            out = np.where(new_m, img, old)
            out[band_ & stripes] = YEL; out[band_ & ~stripes] = INK
            img = out
    if t > total - 0.45:
        a = ease((t - (total - 0.45)) / 0.45)
        img = (img * (1 - a) + scene_img(lines[0]["_s"], lines[0]) * a).astype(np.uint8)
    caption(img, t)
    cv2.rectangle(img, (30, H - 18), (W - 30, H - 8), (60, 40, 40), -1)
    pw = int((W - 60) * t / total)
    if pw > 1:
        cv2.rectangle(img, (30, H - 18), (30 + pw, H - 8), YEL, -1)
        cv2.rectangle(img, (30 + pw - 8, H - 24), (30 + pw + 8, H - 2), RED, -1)
    return np.clip(finish(img), 0, 255).astype(np.uint8).tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), int(float(tt_) * FPS))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=24); print(f"done {total:.1f}s")
