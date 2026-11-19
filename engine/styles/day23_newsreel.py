"""Day 23 — NEWSREEL-1896 style (the shortest war in history).
An 1890s newspaper extra seen through a silent-era newsreel projector. Everything is drawn in a sepia palette
(ink brown, tan, cream newsprint) with one hand-tinted brick red for stamps and the stopwatch wedge.
Look: letterpress front pages (Unifraktur masthead, Anton condensed headlines, Old Standard dateline + greeked type
columns with column rules), ornate silent-film intertitle cards (double cream border with corner flourishes), an
engraved map with 'waterlining' around the coasts, a harbour with steam-warship silhouettes and soft smoke puffs (no
violence shown), a brass stopwatch whose red wedge counts the minutes, a spinning newspaper 'EXTRA', a throne in a
spotlight with a rubber NOT APPROVED stamp. Film layer on every frame: gate weave, exposure flicker, grain, vertical
scratches, dust, rounded gate vignette; iris-in and flash cuts between scenes.
Ending: brass meter gauge whose needle swings FAKE -> TRUE, then the hook front page dissolves back in for the loop.
Music: original ragtime/music-hall piano in C (stride bass + syncopated right hand) over a projector clatter.
Usage: python3 engine/styles/day23_newsreel.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
FF = {"anton": "Anton-Regular.ttf", "os": "OldStandard-Bold.ttf", "osr": "OldStandard-Regular.ttf",
      "osi": "OldStandard-Italic.ttf", "frak": "UnifrakturMaguntia-Book.ttf"}
_F = {}
def F(size, kind="anton"):
    k = (kind, int(size))
    if k not in _F: _F[k] = ImageFont.truetype(f"{FONTS}/{FF[kind]}", int(size))
    return _F[k]

INK = (36, 25, 16); DARK = (60, 44, 29); SEPIA = (122, 88, 54); TAN = (184, 150, 106)
PAPER = (230, 213, 176); LIGHT = (245, 233, 205); RED = (168, 48, 32); GOLD = (226, 184, 98)
rng0 = np.random.default_rng(23)

# ---------- sprite helpers (RGBA uint8) ----------
def to_np(img): return np.asarray(img.convert("RGBA")).copy()
def paste(a, spr, cx, cy, s=1.0, rot=0.0, al=1.0):
    if al <= 0.003 or s <= 0.01: return
    h, w = spr.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, s); M[0, 2] += cx - w / 2; M[1, 2] += cy - h / 2
    cs = np.array([[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]], np.float32) @ M.T
    x0, y0 = max(0, int(cs[:, 0].min()) - 1), max(0, int(cs[:, 1].min()) - 1)
    x1, y1 = min(W, int(cs[:, 0].max()) + 2), min(H, int(cs[:, 1].max()) + 2)
    if x1 <= x0 or y1 <= y0: return
    M2 = M.copy(); M2[0, 2] -= x0; M2[1, 2] -= y0
    wp = cv2.warpAffine(spr, M2, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    alp = wp[..., 3:4].astype(np.float32) / 255 * al
    reg = a[y0:y1, x0:x1].astype(np.float32)
    a[y0:y1, x0:x1] = (reg * (1 - alp) + wp[..., :3].astype(np.float32) * alp).astype(np.uint8)

_T = {}
def tsp(text, size, kind="anton", col=INK, track=0, stroke=0, scol=INK):
    """Text sprite with optional tracking."""
    k = (text, size, kind, col, track, stroke, scol)
    if k in _T: return _T[k]
    f = F(size, kind); pad = 20 + stroke
    widths = [f.getlength(c) for c in text]
    tw = int(sum(widths) + track * max(0, len(text) - 1)) + 2 * pad
    asc, desc = f.getmetrics(); th = asc + desc + 2 * pad
    img = Image.new("RGBA", (tw, th), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    x = pad
    for c, wc in zip(text, widths):
        d.text((x, pad), c, font=f, fill=col + (255,), stroke_width=stroke, stroke_fill=scol + (255,)); x += wc + track
    arr = to_np(img)
    ys = np.where(arr[..., 3].max(1) > 0)[0]
    if len(ys): arr = arr[max(0, ys[0] - 4): ys[-1] + 5]
    _T[k] = arr; return arr

def fitw(spr, mw): return min(1.0, mw / spr.shape[1])

def ss_draw(w, h, fn, ss=2):
    """Supersampled PIL drawing -> anti-aliased RGBA numpy sprite."""
    img = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    fn(d, ss); return to_np(img.resize((w, h), Image.LANCZOS))

def noise_tex(w, h, scale=6, amp=0.08, seed=1):
    r = np.random.default_rng(seed)
    n = r.normal(0, 1, (h // scale + 2, w // scale + 2)).astype(np.float32)
    n = cv2.resize(cv2.GaussianBlur(n, (0, 0), 1.2), (w, h), interpolation=cv2.INTER_CUBIC)
    fine = r.normal(0, 0.35, (h, w)).astype(np.float32)
    return 1 + amp * (n / (n.std() + 1e-6)) + amp * 0.4 * fine

def shadow_of(spr, blur=14, alpha=0.55, pad=40):
    h, w = spr.shape[:2]
    sh = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.uint8)
    m = cv2.GaussianBlur(spr[..., 3].astype(np.float32), (0, 0), blur)
    sh[pad:pad + h, pad:pad + w, 3] = (m * alpha).astype(np.uint8)
    return sh

# ---------- newspaper pages ----------
def greek(d, x0, y0, x1, y1, seed, lh=17, col=SEPIA, para=True):
    r = np.random.default_rng(seed); y = y0
    while y + 6 <= y1:
        x = x0 + (18 if para and r.random() < 0.12 else 0)
        end = x1 - (r.integers(40, (x1 - x0) // 2) if r.random() < 0.1 else 0)
        while x < end - 8:
            wl = int(r.integers(10, 46)); wl = min(wl, end - x)
            d.rectangle([x, y, x + wl, y + 6], fill=col); x += wl + 7
        y += lh

def newspaper(w, h, heads, mast="The Morning Chronicle", hole=None, seed=5, date="THURSDAY, AUGUST 27, 1896",
              head_y=None, sub=None, maxw=None, top=34):
    img = Image.new("RGBA", (w, h), PAPER + (255,)); d = ImageDraw.Draw(img)
    tex = noise_tex(w, h, 24, 0.022, seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    edge = np.clip(np.minimum.reduce([xx, yy, w - xx, h - yy]) / 60, 0, 1) * 0.12 + 0.88
    m = 36
    fm = F(118, "frak"); tw = fm.getlength(mast)
    mmw = min(w - 2 * m, (maxw or 9999) - 20)
    if tw > mmw: fm = F(int(118 * mmw / tw), "frak"); tw = fm.getlength(mast)
    d.text(((w - tw) / 2, top), mast, font=fm, fill=INK)
    yb = top + fm.size + 40
    d.rectangle([m, yb, w - m, yb + 5], fill=INK); d.rectangle([m, yb + 10, w - m, yb + 12], fill=INK)
    fd = F(26, "os"); line_ = f"No. 1,204      {date}      ONE PENNY"
    d.text(((w - fd.getlength(line_)) / 2, yb + 22), line_, font=fd, fill=INK)
    d.rectangle([m, yb + 62, w - m, yb + 64], fill=INK); d.rectangle([m, yb + 69, w - m, yb + 74], fill=INK)
    y = head_y if head_y is not None else yb + 100
    for txt, size in heads:
        f = F(size); tw = f.getlength(txt)
        mw = maxw or (w - 2 * m - 20)
        if tw > mw: f = F(int(size * mw / tw)); tw = f.getlength(txt)
        d.text(((w - tw) / 2, y - f.size * 0.08), txt, font=f, fill=INK); y += int(f.size * 1.08)
    if sub:
        fs = F(46, "osi"); d.text(((w - fs.getlength(sub)) / 2, y + 6), sub, font=fs, fill=INK); y += 70
    y += 14; d.rectangle([m, y, w - m, y + 3], fill=INK); y += 22
    ncol = 4; cw = (w - 2 * m - (ncol - 1) * 24) / ncol
    for c in range(ncol):
        cx0 = int(m + c * (cw + 24)); cx1 = int(cx0 + cw)
        if c: d.rectangle([cx0 - 13, y, cx0 - 12, h - m], fill=SEPIA)
        if hole and cx1 > hole[0] and cx0 < hole[2]:
            greek(d, cx0, y, cx1, hole[1] - 20, seed + c); greek(d, cx0, hole[3] + 20, cx1, h - m, seed + 10 + c)
        else:
            fh = F(30, "os"); hd = ["LATEST CABLES", "SHIPPING NEWS", "FROM THE COAST", "MARKETS"][c]
            d.text((cx0 + (cw - fh.getlength(hd)) / 2, y), hd, font=fh, fill=INK)
            greek(d, cx0, y + 46, cx1, h - m, seed + c)
    arr = to_np(img).astype(np.float32)
    arr[..., :3] *= (tex * edge)[..., None]
    return np.clip(arr, 0, 255).astype(np.uint8)

# ---------- stopwatch / clock ----------
def watch_face(r, kind="stop"):
    S = int(r * 2.6); c = S / 2
    def fn(d, ss):
        C = c * ss; R = r * ss
        if kind == "stop":
            d.rounded_rectangle([C - 0.16 * R, C - 1.28 * R, C + 0.16 * R, C - 1.06 * R], 8 * ss, fill=DARK)
            d.ellipse([C - 0.22 * R, C - 1.16 * R, C + 0.22 * R, C - 0.92 * R], outline=DARK, width=int(10 * ss))
            for sgn in (-1, 1):
                ax = C + sgn * math.sin(0.62) * R * 1.04; ay = C - math.cos(0.62) * R * 1.04
                d.ellipse([ax - 0.09 * R, ay - 0.09 * R, ax + 0.09 * R, ay + 0.09 * R], fill=DARK)
        d.ellipse([C - R * 1.06, C - R * 1.06, C + R * 1.06, C + R * 1.06], fill=DARK)
        d.ellipse([C - R * 0.99, C - R * 0.99, C + R * 0.99, C + R * 0.99], fill=TAN)
        d.ellipse([C - R * 0.93, C - R * 0.93, C + R * 0.93, C + R * 0.93], fill=LIGHT)
        d.ellipse([C - R * 0.885, C - R * 0.885, C + R * 0.885, C + R * 0.885], outline=SEPIA, width=int(2 * ss))
        n = 60
        for k in range(n):
            th = 2 * math.pi * k / n; big = k % 5 == 0
            r0 = R * (0.76 if big else 0.82); r1 = R * 0.885
            d.line([C + r0 * math.sin(th), C - r0 * math.cos(th), C + r1 * math.sin(th), C - r1 * math.cos(th)],
                   fill=INK, width=int((5 if big else 2) * ss))
        if kind == "stop":
            f = F(int(R * 0.16), "os")
            for k in range(1, 13):
                th = 2 * math.pi * k / 12; lab = str(k * 5); rr = R * 0.6
                d.text((C + rr * math.sin(th), C - rr * math.cos(th)), lab, font=f, fill=INK, anchor="mm")
            fi = F(int(R * 0.11), "osi"); d.text((C, C + R * 0.36), "minutes", font=fi, fill=SEPIA, anchor="mm")
        else:
            f = F(int(R * 0.2), "os")
            for k, lab in enumerate(["XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI"]):
                th = 2 * math.pi * k / 12; rr = R * 0.6
                d.text((C + rr * math.sin(th), C - rr * math.cos(th)), lab, font=f, fill=INK, anchor="mm")
    return ss_draw(S, S, fn)

_WF = {}
def P(pts): return (np.array(pts, np.float32).reshape(-1, 1, 2) * 8).astype(np.int32)
def blend_poly(a, pts, col, al):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, y0 = max(0, int(min(xs)) - 2), max(0, int(min(ys)) - 2); x1, y1 = min(W, int(max(xs)) + 3), min(H, int(max(ys)) + 3)
    if x1 <= x0 or y1 <= y0: return
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillPoly(m, [P([(x - x0, y - y0) for x, y in pts])], 255, cv2.LINE_AA, shift=3)
    al_ = (m.astype(np.float32) / 255 * al)[..., None]
    reg = a[y0:y1, x0:x1].astype(np.float32)
    a[y0:y1, x0:x1] = (reg * (1 - al_) + np.array(col, np.float32) * al_).astype(np.uint8)
def hand(a, cx, cy, ang, L, w, col=INK, tail=0.18):
    s, c = math.sin(ang), math.cos(ang)
    tip = (cx + L * s, cy - L * c); bk = (cx - L * tail * s, cy + L * tail * c)
    nx, ny = c * w / 2, s * w / 2
    blend_poly(a, [(bk[0] + nx, bk[1] + ny), (tip[0] + nx * 0.3, tip[1] + ny * 0.3), (tip[0] - nx * 0.3, tip[1] - ny * 0.3),
                   (bk[0] - nx, bk[1] - ny)], col, 1.0)

def stopwatch(a, cx, cy, r, minutes, sweep=None, wedge_col=RED, s=1.0, rot=0.0):
    k = ("stop", r)
    if k not in _WF: _WF[k] = watch_face(r, "stop")
    paste(a, _WF[k], cx, cy, s, rot)
    R = r * s
    if minutes > 0.05:
        n = max(3, int(minutes * 2))
        pts = [(cx, cy)] + [(cx + R * 0.88 * math.sin(2 * math.pi * minutes / 60 * j / n),
                             cy - R * 0.88 * math.cos(2 * math.pi * minutes / 60 * j / n)) for j in range(n + 1)]
        blend_poly(a, pts, wedge_col, 0.5)
    hand(a, cx, cy, 2 * math.pi * minutes / 60, R * 0.8, R * 0.06)
    if sweep is not None: hand(a, cx, cy, sweep, R * 0.86, R * 0.025, RED, 0.25)
    cv2.circle(a, (int(cx), int(cy)), int(R * 0.06), INK, -1, cv2.LINE_AA)
    cv2.circle(a, (int(cx), int(cy)), int(R * 0.025), GOLD, -1, cv2.LINE_AA)

def clock(a, cx, cy, r, hours, minutes):
    k = ("clock", r)
    if k not in _WF: _WF[k] = watch_face(r, "clock")
    paste(a, _WF[k], cx, cy)
    hand(a, cx, cy, 2 * math.pi * ((hours % 12) + minutes / 60) / 12, r * 0.5, r * 0.08)
    hand(a, cx, cy, 2 * math.pi * minutes / 60, r * 0.78, r * 0.05)
    cv2.circle(a, (int(cx), int(cy)), int(r * 0.07), INK, -1, cv2.LINE_AA)

# ---------- stamps ----------
def stamp(text, size=110, col=RED, seed=3):
    f = F(size); tw = int(f.getlength(text)); pad = 36; w = tw + 2 * pad + 40; h = int(size * 1.25) + 2 * pad
    def fn(d, ss):
        d.rounded_rectangle([8 * ss, 8 * ss, (w - 8) * ss, (h - 8) * ss], 18 * ss, outline=col, width=int(10 * ss))
        d.rounded_rectangle([24 * ss, 24 * ss, (w - 24) * ss, (h - 24) * ss], 10 * ss, outline=col, width=int(4 * ss))
        d.text((w / 2 * ss, h / 2 * ss), text, font=F(size * ss), fill=col, anchor="mm")
    arr = ss_draw(w, h, fn)
    r = np.random.default_rng(seed)
    n = cv2.GaussianBlur(r.random((h, w)).astype(np.float32), (0, 0), 1.6)
    n = (n - n.min()) / (n.max() - n.min() + 1e-6)
    arr[..., 3] = (arr[..., 3].astype(np.float32) * np.clip((n - 0.18) * 3.2, 0.25, 1) * 0.92).astype(np.uint8)
    return arr

# ---------- intertitle card ----------
def card_bg():
    img = Image.new("RGB", (W, H), DARK); d = ImageDraw.Draw(img)
    for inset, wd in ((56, 5), (76, 2)):
        d.rectangle([inset, inset, W - inset, H - inset], outline=PAPER, width=wd)
    for (x, y, sx, sy) in ((76, 76, 1, 1), (W - 76, 76, -1, 1), (76, H - 76, 1, -1), (W - 76, H - 76, -1, -1)):
        for rr in (40, 64):
            box = [x - rr, y - rr, x + rr, y + rr]
            st = {(1, 1): 0, (-1, 1): 90, (-1, -1): 180, (1, -1): 270}[(sx, sy)]
            d.arc(box, st, st + 90, fill=PAPER, width=3)
        cx_, cy_ = x + sx * 30, y + sy * 30
        d.polygon([(cx_, cy_ - 12), (cx_ + 12, cy_), (cx_, cy_ + 12), (cx_ - 12, cy_)], fill=GOLD)
    for x in (W / 2 - 160, W / 2 + 160):
        d.line([x - 110, 96, x + 110, 96], fill=PAPER, width=2)
    d.polygon([(W / 2, 84), (W / 2 + 14, 96), (W / 2, 108), (W / 2 - 14, 96)], fill=GOLD)
    a = np.asarray(img).astype(np.float32) * noise_tex(W, H, 10, 0.07, 9)[..., None]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    glow = 1 + 0.22 * np.exp(-(((xx - W / 2) / 600) ** 2 + ((yy - 800) / 800) ** 2))
    return np.clip(a * glow[..., None], 0, 255).astype(np.uint8)

# ---------- map ----------
def build_map():
    w, h = 1400, 2300
    land = np.zeros((h, w), np.uint8)
    r = np.random.default_rng(4)
    ys = np.arange(h)
    def wig(n, amp, seed):
        q = np.random.default_rng(seed).normal(0, 1, n // 40 + 3)
        return cv2.resize(q.reshape(-1, 1).astype(np.float32), (1, n), interpolation=cv2.INTER_CUBIC).ravel() * amp
    coast = 300 + wig(h, 40, 1) + 60 * np.sin(ys / 380)
    for y in range(h): land[y, : int(coast[y])] = 255
    # island (elongated N-S)
    cx, cy = 900, 1150
    pts = []
    for k in range(120):
        th = 2 * math.pi * k / 120
        rr = 1 + 0.09 * math.sin(3 * th + 1) + 0.06 * math.sin(7 * th) + 0.04 * math.sin(11 * th + 2)
        x = 150 * rr * math.cos(th) * (1 - 0.25 * math.sin(th)); y = 430 * rr * math.sin(th)
        pts.append((cx + x + 40 * math.sin(y / 260), cy + y))
    cv2.fillPoly(land, [np.array(pts, np.int32)], 255, cv2.LINE_AA)
    dist = cv2.distanceTransform(255 - (land > 127).astype(np.uint8) * 255, cv2.DIST_L2, 5)
    a = np.zeros((h, w, 3), np.float32); a[:] = PAPER
    sea = (land < 128)
    # engraved horizontal hatch on open sea + waterlines around coasts
    hatch = ((ys[:, None] % 14) < 2).astype(np.float32) * np.ones((1, w), np.float32)
    wl = (((dist % 22) < 2.6) & (dist < 140) & (dist > 6)).astype(np.float32)
    lines = np.clip(np.where(dist > 150, hatch * 0.55, 0) + wl * (1 - dist / 170), 0, 1) * sea
    a = a * (1 - lines[..., None] * 0.55) + np.array(SEPIA, np.float32) * lines[..., None] * 0.55
    # land: tan stipple
    st = (r.random((h, w)) < 0.06).astype(np.float32)
    lm = (land.astype(np.float32) / 255)[..., None]
    a = a * (1 - lm) + (np.array(TAN, np.float32) * (1 - 0.25 * st[..., None])) * lm
    edge = cv2.morphologyEx(land, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8)).astype(np.float32)[..., None] / 255
    a = a * (1 - edge) + np.array(INK, np.float32) * edge
    a *= noise_tex(w, h, 24, 0.025, 7)[..., None]
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA"); d = ImageDraw.Draw(img)
    def spaced(x, y, txt, f, col, tr):
        tw = sum(f.getlength(c) for c in txt) + tr * (len(txt) - 1); xx = x - tw / 2
        for c in txt: d.text((xx, y), c, font=f, fill=col); xx += f.getlength(c) + tr
    spaced(cx + 20, cy - 40, "ZANZIBAR", F(64, "os"), INK, 14)
    spaced(150, 1040, "AFRICA", F(54, "osi"), INK, 18)
    spaced(1080, 1860, "Indian Ocean", F(50, "osi"), DARK, 6)
    # compass rose
    rx, ry = 1180, 520
    for k in range(8):
        th = math.pi / 4 * k; L = 110 if k % 2 == 0 else 60
        tip = (rx + L * math.sin(th), ry - L * math.cos(th))
        l = (rx + 16 * math.sin(th - math.pi / 2), ry - 16 * math.cos(th - math.pi / 2))
        rr_ = (rx + 16 * math.sin(th + math.pi / 2), ry - 16 * math.cos(th + math.pi / 2))
        d.polygon([l, tip, (rx, ry)], fill=INK); d.polygon([rr_, tip, (rx, ry)], fill=PAPER, outline=INK)
    d.ellipse([rx - 70, ry - 70, rx + 70, ry + 70], outline=INK, width=2)
    d.text((rx, ry - 150), "N", font=F(48, "os"), fill=INK, anchor="mm")
    # neatline
    d.rectangle([20, 20, w - 20, h - 20], outline=INK, width=6); d.rectangle([34, 34, w - 34, h - 34], outline=INK, width=2)
    return to_np(img), (cx, cy)

# ---------- harbour ----------
def build_harbour():
    yy = np.arange(H, dtype=np.float32)[:, None]
    hz = 1180
    sky = np.array(LIGHT, np.float32) * (1 - np.clip(yy / hz, 0, 1)[..., None] * 0.25) + \
          np.array(TAN, np.float32) * (np.clip(yy / hz, 0, 1)[..., None] * 0.25)
    a = np.repeat(sky, W, 1)
    sea = yy > hz
    sea_col = np.array(SEPIA, np.float32) * 0.8 + np.array(TAN, np.float32) * 0.2
    a = np.where(sea[..., None], sea_col, a)
    r = np.random.default_rng(11)
    img = Image.fromarray(np.clip(a * noise_tex(W, H, 24, 0.02, 3)[..., None], 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    y = hz + 8
    while y < H:
        gap = 6 + (y - hz) * 0.06
        x = -r.integers(0, 80)
        while x < W:
            L = int(r.integers(40, 220)); d.line([x, y, x + L, y], fill=TAN, width=max(1, int(1 + (y - hz) / 300))); x += L + int(r.integers(20, 90))
        y += int(gap)
    d.line([0, hz, W, hz], fill=DARK, width=3)
    # distant shore + palm-like low skyline (generic)
    pts = [(0, hz)] + [(x, hz - 18 - 10 * math.sin(x / 70) - 8 * math.sin(x / 23)) for x in range(0, W + 20, 20)] + [(W, hz)]
    d.polygon(pts, fill=SEPIA)
    return np.asarray(img).copy(), hz

def ship_sprite(scale=1.0, seed=0):
    w, h = int(520 * scale), int(300 * scale)
    def fn(d, ss):
        s = scale * ss
        hull = [(20 * s, 200 * s), (500 * s, 200 * s), (470 * s, 270 * s), (60 * s, 270 * s)]
        d.polygon(hull, fill=INK)
        d.rectangle([110 * s, 160 * s, 400 * s, 205 * s], fill=INK)
        d.rectangle([170 * s, 120 * s, 330 * s, 165 * s], fill=INK)
        for fx in (200, 270):
            d.rectangle([fx * s, 60 * s, (fx + 34) * s, 130 * s], fill=INK)
            d.rectangle([fx * s, 70 * s, (fx + 34) * s, 78 * s], fill=SEPIA)
        for mx in (120, 400):
            d.rectangle([mx * s, 10 * s, (mx + 6) * s, 165 * s], fill=INK)
            d.rectangle([(mx - 26) * s, 40 * s, (mx + 32) * s, 46 * s], fill=INK)
        d.line([(126 * s, 14 * s), (403 * s, 14 * s)], fill=INK, width=int(2 * ss))
        for gx in (70, 440):
            d.rectangle([gx * s, 182 * s, (gx + 22) * s, 200 * s], fill=INK)
        for px in range(140, 400, 34): d.ellipse([px * s, 225 * s, (px + 10) * s, 235 * s], fill=SEPIA)
    return ss_draw(w, h, fn)

def puff_sprite(seed):
    S = 300; r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    al = np.zeros((S, S), np.float32)
    for k in range(9):
        cx, cy = S / 2 + r.normal(0, 40), S / 2 + r.normal(0, 30); rr = r.uniform(50, 85)
        al = np.maximum(al, np.clip(1 - np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / rr, 0, 1))
    al = cv2.GaussianBlur(al, (0, 0), 6)
    shade = np.clip(1 - (yy - S / 2) / S * 0.8, 0, 1)
    rgb = (np.array(LIGHT, np.float32) * shade[..., None] + np.array(TAN, np.float32) * (1 - shade[..., None]))
    return np.dstack([rgb, np.clip(al * 1.6, 0, 1) * 235]).astype(np.uint8)

# ---------- throne + crown ----------
def throne_sprite():
    w, h = 560, 900
    def fn(d, ss):
        s = ss
        d.rounded_rectangle([120 * s, 120 * s, 440 * s, 600 * s], 30 * s, fill=INK)
        d.pieslice([120 * s, 20 * s, 440 * s, 260 * s], 180, 360, fill=INK)
        for x in (110, 450):
            d.rectangle([(x - 18) * s, 80 * s, (x + 18) * s, 640 * s], fill=INK)
            d.ellipse([(x - 30) * s, 40 * s, (x + 30) * s, 100 * s], fill=INK)
        d.ellipse([255 * s, -10 * s, 305 * s, 40 * s], fill=INK)
        d.rounded_rectangle([170 * s, 160 * s, 390 * s, 560 * s], 20 * s, fill=RED)
        d.pieslice([170 * s, 90 * s, 390 * s, 280 * s], 180, 360, fill=RED)
        for k in range(5):
            d.ellipse([(270 - 6) * s, (220 + k * 70) * s, (270 + 18) * s, (244 + k * 70) * s], fill=GOLD)
        d.rounded_rectangle([40 * s, 560 * s, 520 * s, 660 * s], 24 * s, fill=INK)
        d.rectangle([60 * s, 520 * s, 140 * s, 580 * s], fill=INK); d.rectangle([420 * s, 520 * s, 500 * s, 580 * s], fill=INK)
        d.ellipse([30 * s, 500 * s, 150 * s, 560 * s], fill=INK); d.ellipse([410 * s, 500 * s, 530 * s, 560 * s], fill=INK)
        for x in (70, 450):
            d.rectangle([x * s, 650 * s, (x + 40) * s, 860 * s], fill=INK)
            d.ellipse([(x - 10) * s, 840 * s, (x + 50) * s, 890 * s], fill=INK)
        d.rectangle([60 * s, 610 * s, 500 * s, 618 * s], fill=GOLD)
    return ss_draw(w, h, fn)

def crown_sprite():
    w, h = 340, 240
    def fn(d, ss):
        s = ss
        pts = [(30, 200), (30, 90), (95, 150), (170, 50), (245, 150), (310, 90), (310, 200)]
        d.polygon([(x * s, y * s) for x, y in pts], fill=GOLD, outline=INK, width=int(6 * ss))
        d.rectangle([24 * s, 180 * s, 316 * s, 222 * s], fill=GOLD, outline=INK, width=int(6 * ss))
        for x, y in ((30, 90), (170, 50), (310, 90)):
            d.ellipse([(x - 16) * s, (y - 16) * s, (x + 16) * s, (y + 16) * s], fill=LIGHT, outline=INK, width=int(4 * ss))
        for x in (90, 170, 250):
            d.ellipse([(x - 13) * s, 189 * s, (x + 13) * s, 213 * s], fill=RED, outline=INK, width=int(3 * ss))
    return ss_draw(w, h, fn)

# ---------- gauge (ending) ----------
def gauge_sprite():
    w, h = 900, 620; cx, cy, R = 450, 520, 400
    def fn(d, ss):
        C = (cx * ss, cy * ss); Rs = R * ss
        d.rounded_rectangle([20 * ss, 40 * ss, 880 * ss, 610 * ss], 40 * ss, fill=DARK, outline=GOLD, width=int(6 * ss))
        d.pieslice([C[0] - Rs, C[1] - Rs, C[0] + Rs, C[1] + Rs], 180, 360, fill=LIGHT)
        r2 = Rs * 0.96
        d.arc([C[0] - r2, C[1] - r2, C[0] + r2, C[1] + r2], 180, 270, fill=SEPIA, width=int(26 * ss))
        d.arc([C[0] - r2, C[1] - r2, C[0] + r2, C[1] + r2], 270, 360, fill=RED, width=int(26 * ss))
        for k in range(21):
            th = math.pi + math.pi * k / 20; big = k % 5 == 0
            r0 = Rs * (0.74 if big else 0.8); r1 = Rs * 0.88
            d.line([C[0] + r0 * math.cos(th), C[1] + r0 * math.sin(th), C[0] + r1 * math.cos(th), C[1] + r1 * math.sin(th)],
                   fill=INK, width=int((6 if big else 3) * ss))
        f = F(84 * ss, "anton")
        d.text((C[0] - Rs * 0.5, C[1] - Rs * 0.4), "FAKE", font=f, fill=SEPIA, anchor="mm")
        d.text((C[0] + Rs * 0.5, C[1] - Rs * 0.4), "TRUE", font=f, fill=RED, anchor="mm")
        d.text((C[0], C[1] - Rs * 0.16), "VERDICT", font=F(34 * ss, "os"), fill=INK, anchor="mm")
        d.rectangle([60 * ss, C[1], 840 * ss, C[1] + 8 * ss], fill=GOLD)
    return ss_draw(w, h, fn), (cx, cy, R)

# ---------- build static assets ----------
print("building assets…")
PAGE_HOOK = newspaper(1180, 2080, [("THIS WAR LASTED", 156), ("LESS THAN", 156), ("AN HOUR", 156)],
                      hole=(0, 960, 1180, 1580), seed=5, maxw=930, top=150)
PAGE_OVER = newspaper(900, 1260, [("WAR OVER", 150), ("IN 38 MINUTES", 118)], sub="Firing ceased at 9:40 a.m.",
                      hole=(0, 700, 900, 1180), seed=12)
# print a stopwatch onto the 'over' page
_tmp = np.zeros((H, W, 3), np.uint8)
PAGE_OVER_SH = shadow_of(PAGE_OVER, 22, 0.7, 60)
CARD = card_bg()
MAP, ISLE = build_map()
HARB, HZ = build_harbour()
SHIPS = [ship_sprite(0.9, 0), ship_sprite(0.7, 1), ship_sprite(0.55, 2)]
PUFFS = [puff_sprite(s) for s in range(5)]
THRONE = throne_sprite(); CROWN = crown_sprite()
GAUGE, GG = gauge_sprite()
ST_EXTRA = stamp("EXTRA!", 100, RED, 1)
ST_38 = stamp("38 MINUTES", 96, RED, 2)
ST_NO = stamp("NOT APPROVED", 104, RED, 3)
ST_DEAD = stamp("DEADLINE  9 A.M.", 92, INK, 4)
yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float32)
DIST = np.sqrt((xx_ - W / 2) ** 2 + (yy_ - H * 0.45) ** 2)
SPOT = (0.35 + 0.65 * np.exp(-(((xx_ - W / 2) / 420) ** 2 + ((yy_ - 1000) / 640) ** 2)))[..., None].astype(np.float32)
# film gate vignette (rounded corners + falloff)
_g = np.ones((H, W), np.float32)
_m = np.zeros((H, W), np.uint8); cv2.rectangle(_m, (14, 14), (W - 15, H - 15), 255, -1)
_m = cv2.GaussianBlur(_m.astype(np.float32), (0, 0), 16) / 255
_rr = np.sqrt(((xx_ - W / 2) / (W * 0.62)) ** 2 + ((yy_ - H / 2) / (H * 0.62)) ** 2)
VIG = (_m * (1 - 0.42 * np.clip(_rr - 0.45, 0, 1) ** 1.4))[..., None].astype(np.float32)
GRAIN = []
for k in range(8):
    g = np.random.default_rng(100 + k).normal(0, 1, (H // 2, W // 2)).astype(np.float32)
    g = cv2.resize(cv2.GaussianBlur(g, (0, 0), 0.7), (W, H), interpolation=cv2.INTER_LINEAR) * 11
    GRAIN.append(g[..., None])
del xx_, yy_, _rr, _m

# ---------- narration ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
def wt(ln, k, end=False):
    i = min(ln["_w0"] + k, ln["_w1"] - 1); return words[i][2 if end else 1] - ln["_s"]

def popv(lt, at, d=0.25):
    u = (lt - at) / d
    return 0.0 if u <= 0 else (back(u, 2.2) if u < 1 else 1.0)
def slam(lt, at, d=0.18):
    """1.8 -> 1.0 scale slam."""
    u = (lt - at) / d
    if u <= 0: return 0.0
    return 1.0 + 0.8 * (1 - eout(u))
def fade(lt, at, d=0.2): return ease((lt - at) / d)

# ---------- scenes ----------
def S_hook(a, sc, ln, lt, dur, t):
    a[:] = DARK
    s = 1.0 + 0.045 * min(lt, 3.0) / 3.0
    paste(a, PAGE_HOOK, W / 2, 980, s, -1.2)
    m = 38 * eout(min(1, lt / 2.0))
    stopwatch(a, W / 2, 1185, 240, m, sweep=lt * 5.0, s=1.0)
    p = popv(lt, 0.55, 0.22)
    if p > 0: paste(a, ST_EXTRA, 860, 1000, 0.95 * (1 + 0.6 * (1 - min(1, (lt - 0.55) / 0.15))), -14, min(1, p))

def S_loop(a, sc, ln, lt, dur, t):
    a[:] = CARD
    rows = ["AND WHY IT", "STARTED IS", "EVEN STRANGER"]
    for i, r_ in enumerate(rows):
        sp = tsp(r_, 132, "os", PAPER, 4)
        al = fade(lt, i * 0.12, 0.15)
        paste(a, sp, W / 2, 400 + i * 165, fitw(tsp("EVEN STRANGER", 132, "os", PAPER, 4), 860) * (1.0 + 0.04 * (1 - al)), 0, al)
    q = tsp("?", 520, "osi", RED)
    p = popv(lt, 0.45, 0.3)
    paste(a, q, W / 2, 1140 + 10 * math.sin(lt * 4), max(0.01, p), 8 * math.sin(lt * 2.4), min(1, p * 1.5))

def S_place(a, sc, ln, lt, dur, t):
    a[:] = PAPER
    u = ease(lt / max(1.0, dur))
    s = 0.85 + 0.35 * u
    mx = W / 2 - (ISLE[0] - MAP.shape[1] / 2) * s * u * 0.7
    my = 1050 - (ISLE[1] - MAP.shape[0] / 2) * s * u * 0.7
    paste(a, MAP, mx, my, s)
    ix = mx + (ISLE[0] - MAP.shape[1] / 2) * s; iy = my + (ISLE[1] - MAP.shape[0] / 2) * s
    pr = ease((lt - 0.5) / 0.8)
    if pr > 0:
        n = int(80 * pr) + 2
        pts = [(ix + 230 * s * math.cos(-2.2 + 2 * math.pi * 1.05 * k / 80) * (1 + 0.03 * math.sin(k)),
                iy + 520 * s * math.sin(-2.2 + 2 * math.pi * 1.05 * k / 80)) for k in range(n)]
        cv2.polylines(a, [P(pts)], False, RED, 9, cv2.LINE_AA, shift=3)
    # dateline slug band
    a[150:430] = (a[150:430].astype(np.float32) * 0.25 + np.array(DARK, np.float32) * 0.75).astype(np.uint8)
    paste(a, tsp("ZANZIBAR", 120, "anton", LIGHT, 10), W / 2, 225, max(0.01, slam(lt, 0.0)), 0, fade(lt, 0.0, 0.08))
    d_ = ["AUGUST 27,", "1896"]
    sps = [tsp(s_, 96, "os", GOLD, 6) for s_ in d_]; gap = 30
    tot = sum(sp.shape[1] for sp in sps) + gap; x = W / 2 - tot / 2
    for i, sp in enumerate(sps):
        at = wt(ln, 1 + 2 * i) - 0.05
        k = slam(lt, at)
        if k > 0: paste(a, sp, x + sp.shape[1] / 2, 355, k, 0, fade(lt, at, 0.06))
        x += sp.shape[1] + gap

def harbour_base(a, lt, ship_in=0.0, shake=(0, 0)):
    a[:] = HARB
    xs = [(700, HZ - 40, 0), (330, HZ - 22, 1), (980, HZ - 10, 2)]
    for i, (x, y, k) in enumerate(xs):
        off = (1 - ship_in) * (600 + 200 * i)
        paste(a, SHIPS[k], x + off + shake[0], y + 3 * math.sin(lt * 2 + i) + shake[1], 1.0, 0.6 * math.sin(lt * 1.6 + i))
    return xs

def S_deadline(a, sc, ln, lt, dur, t):
    harbour_base(a, lt, eout(min(1, lt / 0.9)))
    mins = 55 + 5 * min(1, lt / max(0.5, dur - 0.3))
    mins = math.floor(mins * 2) / 2 if mins < 60 else 60
    h_ = 8 if mins < 60 else 9; mm = mins % 60
    clock(a, W / 2, 560, 300, h_, mm)
    k = slam(lt, wt(ln, 5) - 0.05, 0.16)
    if k > 0: paste(a, ST_DEAD, W / 2, 970, 0.9 * k, -4)

PUFF_T = [0.25, 0.75, 1.15, 1.6, 2.0, 2.45, 2.9]
def S_fire(a, sc, ln, lt, dur, t):
    sh = (0, 0)
    for pt in PUFF_T:
        if 0 <= lt - pt < 0.12:
            q = 1 - (lt - pt) / 0.12; sh = (int(8 * q * math.sin(lt * 90)), int(6 * q * math.cos(lt * 70)))
    xs = harbour_base(a, lt, 1.0, sh)
    for i, pt in enumerate(PUFF_T):
        u = (lt - pt) / 1.6
        if 0 <= u < 1:
            x, y, k = xs[i % 3]
            sc_ = [0.9, 0.7, 0.55][k]
            gx = x + (-200 if i % 2 else 200) * sc_ + sh[0]
            paste(a, PUFFS[i % 5], gx - 60 * u, y + 40 * sc_ - 240 * u + sh[1], (0.9 + 1.9 * eout(u)) * (0.6 + 0.5 * sc_), 10 * u, min(1, 3 * u + 0.3) * (1 - u) ** 1.2)
    m = 9 * min(1, lt / max(1.0, dur))
    stopwatch(a, W / 2, 540 + sh[1], 270, m, sweep=lt * 7)
    paste(a, tsp("THE CLOCK STARTS", 64, "os", INK, 8), W / 2, 150, 1, 0, fade(lt, 0.1))

def S_over(a, sc, ln, lt, dur, t):
    a[:] = INK
    a[:] = (a.astype(np.float32) * (0.6 + 1.6 * SPOT)).clip(0, 255).astype(np.uint8)
    u = eout(min(1, lt / 0.7))
    rot = -3 + (1 - u) * 720; s = 0.06 + 0.94 * u
    paste(a, PAGE_OVER_SH, W / 2 + 26, 800 + 30, s, rot, 0.8)
    pg = PAGE_OVER.copy()
    # stopwatch on the page: counts to 38 then stops
    sub = np.ascontiguousarray(pg[..., :3])
    _a = sub
    m = 38 * eout(min(1, max(0, lt - 0.4) / 1.3))
    global W_, H_
    stopwatch_on(_a, 450, 950, 200, m)
    pg[..., :3] = _a
    paste(a, pg, W / 2, 800, s, rot)
    k = slam(lt, wt(ln, 6) - 0.05, 0.16)
    if k > 0: paste(a, ST_38, W / 2 + 150, 1330, 0.8 * k, -10)

def stopwatch_on(arr, cx, cy, r, m):
    """Stopwatch drawn into an arbitrary-size array (used to print on the spinning page)."""
    global W, H
    sw, sh_ = W, H
    W, H = arr.shape[1], arr.shape[0]
    try: stopwatch(arr, cx, cy, r, m)
    finally: W, H = sw, sh_

def S_why(a, sc, ln, lt, dur, t):
    a[:] = DARK
    a[:] = (a.astype(np.float32) * (0.35 + 1.15 * SPOT)).clip(0, 255).astype(np.uint8)
    paste(a, tsp("WHY?", 230, "anton", LIGHT, 8), W / 2, 250, max(0.01, slam(lt, 0.0)), 0, 1)
    paste(a, THRONE, W / 2, 1060, 1.0 + 0.03 * lt / dur)
    cu = ease((lt - 0.4) / 1.4)
    paste(a, CROWN, W / 2, 520 + 230 * cu + 6 * math.sin(lt * 3), 0.8, 4 * math.sin(lt * 2))
    l2 = fade(lt, wt(ln, 1) - 0.05, 0.15)
    paste(a, tsp("A NEW SULTAN, NO APPROVAL", 54, "os", PAPER, 6), W / 2, 410, 1, 0, l2)
    at = wt(ln, sc.get("stamp_word", 9)) - 0.08
    k = slam(lt, at, 0.16)
    if k > 0: paste(a, ST_NO, W / 2, 1330, 0.95 * k, -10)

def S_end(a, sc, ln, lt, dur, t):
    a[:] = CARD
    click = sc.get("click_at", 0.5)
    sp = tsp("SOUNDS FAKE?", 128, "os", PAPER, 6); paste(a, sp, W / 2, 330, fitw(sp, 880), 0, 1)
    paste(a, GAUGE, W / 2, 860)
    cx, cy, R = GG; gx = W / 2 - GAUGE.shape[1] / 2 + cx; gy = 860 - GAUGE.shape[0] / 2 + cy
    u = (lt - click) / 0.5
    if u <= 0: ang = -1.25 + 0.03 * math.sin(lt * 30)
    else: ang = 1.15 - 2.4 * math.exp(-u * 4.5) * math.cos(u * 9)
    hand(a, gx, gy, ang, R * 0.86, 22, INK, 0.12)
    cv2.circle(a, (int(gx), int(gy)), 34, INK, -1, cv2.LINE_AA); cv2.circle(a, (int(gx), int(gy)), 14, GOLD, -1, cv2.LINE_AA)
    k = slam(lt, click + 0.3, 0.16)
    if k > 0: paste(a, tsp("IT'S TRUE.", 170, "anton", GOLD, 6), W / 2, 1210, k)
    paste(a, tsp("Follow for more.", 70, "osi", PAPER, 2), W / 2, 1390, 1, 0, fade(lt, click + 0.6))

SCENES = dict(hook=S_hook, loop=S_loop, place=S_place, deadline=S_deadline, fire=S_fire, over=S_over, why=S_why, end=S_end)
TRANS = dict(place="iris", why="iris", deadline="flash", fire="flash", over="flash", loop="flash", end="iris")

# ---------- audio ----------
n = len(voice); music = np.zeros(n, np.float32)
NOTE = {n_: 261.63 * 2 ** (k / 12) for k, n_ in enumerate("C C# D D# E F F# G G# A A# B".split())}
def nf(nm, o=0): return NOTE[nm] * 2 ** o
def piano(f, dur=0.6, gain=0.05):
    s = np.arange(int(dur * SR)) / SR
    sig = sum(np.sin(2 * np.pi * f * h * 1.0007 ** h * s) / h ** 1.6 * math.exp(-0.25 * h) for h in range(1, 7))
    sig = sig * np.minimum(1, s / 0.004) * np.exp(-s * (3.2 + f / 900))
    return (sig * gain).astype(np.float32)
BEAT = 60 / 104
CH = [("C", "E", "G"), ("C", "E", "G"), ("F", "A", "C"), ("C", "E", "G"), ("D", "F#", "A"), ("G", "B", "D"), ("C", "E", "G"), ("G", "B", "F")]
rmel = np.random.default_rng(1896)
for b in range(int(total / (BEAT * 4)) + 1):
    t0 = b * BEAT * 4; ch = CH[b % 8]
    for k in range(4):
        if k % 2 == 0: place(music, t0 + k * BEAT, piano(nf(ch[0], -2) if k == 0 else nf(ch[2], -2), 0.5, 0.09))
        else:
            for nm in ch: place(music, t0 + k * BEAT, piano(nf(nm, -1), 0.3, 0.035))
    pat = [0, 0.75, 1.5, 2, 2.75, 3.5]
    for j, p_ in enumerate(pat):
        nm = ch[int(rmel.integers(0, 3))]; o = 0 if j % 3 else 1
        place(music, t0 + p_ * BEAT, piano(nf(nm, o), 0.35, 0.04))
# projector clatter
clat = np.zeros(n, np.float32); cl = np.random.default_rng(2).normal(0, 1, int(0.004 * SR)).astype(np.float32)
for k in range(int(total * 24)): place(clat, k / 24, cl, 0.02 * (1 + 0.5 * (k % 2)))
music += np.convolve(clat, np.ones(4) / 4, mode="same")
def thud(at, gain=0.25, f0=55):
    s = np.arange(int(0.5 * SR)) / SR
    sig = np.sin(2 * np.pi * (f0 + 50 * np.exp(-s * 25)) * s) * np.exp(-s * 7)
    nz = np.random.default_rng(int(at * 100)).normal(0, 1, len(s)) * np.exp(-s * 18) * 0.3
    place(music, at, (sig + np.convolve(nz, np.ones(20) / 20, mode="same")).astype(np.float32), gain)
def tick(at, gain=0.06, f=2600):
    s = np.arange(int(0.03 * SR)) / SR; place(music, at, (np.sin(2 * np.pi * f * s) * np.exp(-s * 200)).astype(np.float32), gain)
def bell(at, gain=0.08):
    s = np.arange(int(1.4 * SR)) / SR
    sig = sum(np.sin(2 * np.pi * 1320 * h * s) * np.exp(-s * (2 + h)) / h for h in (1, 2.76, 5.4))
    place(music, at, sig.astype(np.float32), gain)
hook_hit(music, 0.32)
for ln in spec["lines"]:
    st = ln["scene"]["type"]; s0 = ln["_s"]; dur = ln["_se"] - s0
    if st != "hook": whoosh(music, s0, 0.1)
    if st == "hook": thud(0.55, 0.18, 70)
    if st == "deadline":
        k = 0.0
        while k < dur: tick(s0 + k, 0.07, 2600 if int(k * 2) % 2 else 2100); k += 0.5
        thud(s0 + wt(ln, 5), 0.18, 80)
    if st == "fire":
        for pt in PUFF_T: thud(s0 + pt, 0.28, 48)
    if st == "over":
        thud(s0 + wt(ln, 6), 0.22, 80); bell(s0 + 1.7, 0.05)
    if st == "why": thud(s0 + wt(ln, ln["scene"].get("stamp_word", 9)) - 0.05, 0.25, 75)
    if st == "end":
        c = s0 + ln["scene"].get("click_at", 0.5); tick(c, 0.15, 900); bell(c + 0.35, 0.1)
        for j, nm in enumerate(("C", "E", "G", "C")): place(music, c + 0.3 + j * 0.08, piano(nf(nm, 1 + (j == 3)), 0.8, 0.07))
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.45)

# ---------- film layer ----------
def film(a, fi, t):
    step = fi // 2
    r = np.random.default_rng(7000 + step)
    dx, dy = int(r.integers(-2, 3)), int(r.integers(-3, 4))
    if dx or dy: a = np.roll(a, (dy, dx), (0, 1))
    fl = 1 + 0.035 * r.normal()
    f = a.astype(np.float32) * (VIG * fl) + GRAIN[step % 8]
    for _ in range(int(r.integers(0, 3))):
        x = int(r.integers(40, W - 40)); wd = int(r.integers(1, 3)); lightp = r.random() < 0.6
        y0 = int(r.integers(0, H // 2)); y1 = int(r.integers(H // 2, H))
        f[y0:y1, x:x + wd] = f[y0:y1, x:x + wd] * 0.6 + (255 if lightp else 20) * 0.4
    for _ in range(int(r.integers(0, 5))):
        cx, cy = int(r.integers(0, W)), int(r.integers(0, H)); rr = int(r.integers(1, 5))
        cv2.circle(f, (cx, cy), rr, (25, 18, 12), -1, cv2.LINE_AA)
    if r.random() < 0.15:
        cx, cy = int(r.integers(0, W)), int(r.integers(0, H))
        pts = np.array([[cx + 12 * k, cy + int(10 * math.sin(k * 0.9))] for k in range(6)], np.int32)
        cv2.polylines(f, [pts], False, (25, 18, 12), 1, cv2.LINE_AA)
    return np.clip(f, 0, 255).astype(np.uint8)

# ---------- captions + compositing ----------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0].upper() for i in g]; size = 64; f = F(size, "os")
    while f.getlength(" ".join(ws)) > W - 220 and size > 36: size -= 4; f = F(size, "os")
    tw_ = f.getlength(" ".join(ws)); x = (W - tw_) / 2; y = 1588
    d = ImageDraw.Draw(img)
    bx0, by0, bx1, by1 = x - 44, y - 26, x + tw_ + 44, y + size + 30
    d.rectangle([bx0, by0, bx1, by1], fill=INK)
    d.rectangle([bx0 + 8, by0 + 8, bx1 - 8, by1 - 8], outline=PAPER, width=2)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]; wl = f.getlength(w)
        d.text((x, y), w, font=f, fill=GOLD if on else LIGHT)
        if on: d.rectangle([x, y + size + 6, x + wl, y + size + 10], fill=GOLD)
        x += f.getlength(w + " ")

def scene_arr(ln, t):
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    a = np.zeros((H, W, 3), np.uint8)
    SCENES[ln["scene"]["type"]](a, ln["scene"], ln, lt, dur, t)
    return a, lt, dur

HOOK = spec["lines"][0]
def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]
    st = ln["scene"]["type"]
    a, lt, dur = scene_arr(ln, t)
    tr = TRANS.get(st)
    if tr == "iris" and lt < 0.3:
        rad = 40 + 1300 * eout(lt / 0.3)
        m = np.clip((rad - DIST) / 6, 0, 1)[..., None]
        a = (a.astype(np.float32) * m).astype(np.uint8)
    elif tr == "flash" and lt < 0.12:
        a = np.clip(a.astype(np.float32) + 120 * (1 - lt / 0.12), 0, 255).astype(np.uint8)
    if st == "end":
        lp = ease((lt - (dur - 0.45)) / 0.4)
        if lp > 0:
            hk, _, _ = scene_arr(HOOK, 0.0)
            a = (a.astype(np.float32) * (1 - lp) + hk.astype(np.float32) * lp).astype(np.uint8)
    a = film(a, fi, t)
    img = Image.fromarray(a)
    caption(img, t)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 12, W, H], fill=INK); d.rectangle([0, H - 12, int(W * t / total), H], fill=GOLD)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","):
            Image.frombytes("RGB", (W, H), frame(float(tt_), int(float(tt_) * FPS))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=26); print(f"done {total:.1f}s")
