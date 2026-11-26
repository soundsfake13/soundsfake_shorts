"""Day 30 — HOLO-CARDS style (recap: the five weirdest facts of the month).
A countdown of collectible holographic trading cards:
- deep ink-violet backdrop with a soft iridescent glow behind the card and drifting four-point sparkles;
- every card has a holographic foil frame (iridescent LUT — cyan / violet / pink / gold / mint — flowing along a
  diagonal phase field with a bright sheen band sweeping across) around a window that plays the fact's ORIGINAL
  footage (the top of that day's video, cropped above its own captions), plus a dark name plate
  ("THE UNICORN" + "FROM DAY 18 · HERALDRY");
- header per card: giant holo-filled rank (#5 … #1) + WEIRDNESS pip meter that overflows on #1 ("OFF THE CHART");
- hook: the five cards fanned out, bobbing, holo sheen; the tease flips the centre card to its back ('#1 ?');
- cuts between facts are card flips (squash to an edge, new card springs out) with a foil 'shing';
  inside a card the footage cuts to its second moment behind a white sheen flash;
- type: Oswald Bold (condensed, trading-card stat look) + Quicksand Bold labels/captions;
- captions: dark pill with a foil rim, the active word on a holo chip in dark ink;
- ending: pill track FAKE → TRUE whose knob is a mini holo card, track floods with foil, dissolves back into the hook.
Music: original 112 bpm A-minor synth-pluck countdown (kick, clap, plucks, sub) + shimmer 'shing' on flips,
riser before #1.
Usage: python3 engine/styles/day30_holocards.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, sys, subprocess, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

INK = (18, 15, 36); INK2 = (30, 25, 58); WHT = (246, 244, 255); DIM = (150, 142, 190)
GOLD = (255, 214, 120)

_F = {}
def F(s, fam="oswald", w=700):
    k = (int(s), fam, w)
    if k not in _F:
        path = {"oswald": "Oswald-VF.ttf", "quick": "Quicksand.ttf"}[fam]
        f = ImageFont.truetype(f"{FONTS}/{path}", int(s))
        try: f.set_variation_by_axes([w])
        except Exception: pass
        _F[k] = f
    return _F[k]

# ---------- holo foil ----------
STOPS = [(120, 235, 255), (176, 150, 255), (255, 150, 214), (255, 222, 140), (150, 255, 200), (120, 235, 255)]
def _lut():
    xs = np.linspace(0, len(STOPS) - 1, 256)
    out = np.zeros((256, 3), np.float32)
    for i, x in enumerate(xs):
        a = int(min(x, len(STOPS) - 2)); f = x - a
        out[i] = np.array(STOPS[a]) * (1 - f) + np.array(STOPS[a + 1]) * f
    return out
LUT = _lut()
_r = np.random.default_rng(30)
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
_lo = cv2.resize(_r.normal(0, 1, (H // 120, W // 120)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
PHASE = (XX * 0.16 + YY * 0.11 + _lo * 38)
_fine = cv2.GaussianBlur(_r.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 1.0)
def holo(t, y0=0, y1=H, x0=0, x1=W):
    ph = (PHASE[y0:y1, x0:x1] + t * 90 + _fine[y0:y1, x0:x1] * 6) % 256
    col = LUT[ph.astype(np.int32)]
    # moving sheen band along the other diagonal
    d = (XX[y0:y1, x0:x1] * 0.8 - YY[y0:y1, x0:x1] * 0.6) - ((t * 900) % 2600 - 900)
    sheen = np.exp(-(d / 70) ** 2)[..., None]
    col = col * (0.88 + 0.12 * np.sin(ph[..., None] * 0.15)) + sheen * 120
    return np.clip(col, 0, 255)

# ---------- background ----------
def make_bg():
    b = np.zeros((H, W, 3), np.float32); b[:] = INK
    g = np.exp(-(((XX - W / 2) / 620) ** 2 + ((YY - 900) / 820) ** 2))[..., None]
    tint = LUT[((PHASE * 0.4) % 256).astype(np.int32)]
    b = b * (1 - 0.35 * g) + (INK2 + (tint - 128) * 0.18) * 0.35 * g + np.array(INK2) * 0.0
    b += _fine[..., None] * 2.5
    vig = 1 - 0.35 * np.clip(((XX - W / 2) / (W * 0.75)) ** 2 + ((YY - H / 2) / (H * 0.7)) ** 2, 0, 1)
    return np.clip(b * vig[..., None], 0, 255)
BG = make_bg().astype(np.uint8)
SPARKS = [(_r.uniform(40, W - 40), _r.uniform(40, H - 260), _r.uniform(6, 16), _r.uniform(0, 6.28), _r.uniform(0.6, 1.6))
          for _ in range(26)]
def sparkle(img, x, y, r, a, col=WHT):
    if r < 1 or a <= 0.02: return
    ov = img.copy()
    pts = np.array([[x, y - r * 2.2], [x + r * 0.35, y - r * 0.35], [x + r * 2.2, y], [x + r * 0.35, y + r * 0.35],
                    [x, y + r * 2.2], [x - r * 0.35, y + r * 0.35], [x - r * 2.2, y], [x - r * 0.35, y - r * 0.35]])
    cv2.fillPoly(ov, [(pts * 16).astype(np.int32)], col, cv2.LINE_AA, 4)
    cv2.addWeighted(ov, a, img, 1 - a, 0, img)
def background(t):
    img = BG.copy()
    for (x, y, r, ph, sp) in SPARKS:
        a = max(0.0, math.sin(t * sp + ph)) ** 3 * 0.8
        sparkle(img, x + 10 * math.sin(t * 0.3 + ph), (y - t * 14 * sp) % (H - 200), r, a)
    return img

# ---------- drawing helpers ----------
SH = 4; SC = 1 << SH
def rrect(img, x0, y0, x1, y1, r, col):
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1); r = int(max(1, min(r, (x1 - x0) // 2, (y1 - y0) // 2)))
    cv2.rectangle(img, (x0 + r, y0), (x1 - r, y1), col, -1)
    cv2.rectangle(img, (x0, y0 + r), (x1, y1 - r), col, -1)
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        cv2.circle(img, (cx * SC, cy * SC), r * SC, col, -1, cv2.LINE_AA, SH)
def rmask(w, h, r):
    m = np.zeros((h, w), np.uint8); rrect(m, 0, 0, w - 1, h - 1, r, 255); return m

def text_mask(s, size, fam="oswald", w=700, track=0):
    f = F(size, fam, w)
    if track:
        widths = [f.getlength(c) for c in s]; tw = int(sum(widths) + track * (len(s) - 1)) + 8
    else:
        tw = int(f.getlength(s)) + 8
    asc, desc = f.getmetrics(); th = asc + desc + 8
    im = Image.new("L", (tw, th), 0); d = ImageDraw.Draw(im)
    if track:
        x = 4
        for c, cw in zip(s, widths): d.text((x, 4), c, font=f, fill=255); x += cw + track
    else:
        d.text((4, 4), s, font=f, fill=255)
    return np.array(im)

def blend(img, m, x, y, col, alpha=1.0):
    """composite colour (tuple or HxWx3 array) through mask m (uint8) at top-left x,y."""
    x, y = int(round(x)), int(round(y)); h, w = m.shape
    xa, ya = max(0, x), max(0, y); xb, yb = min(W, x + w), min(H, y + h)
    if xb <= xa or yb <= ya: return
    a = (m[ya - y: yb - y, xa - x: xb - x].astype(np.float32) / 255 * alpha)[..., None]
    reg = img[ya:yb, xa:xb].astype(np.float32)
    if isinstance(col, np.ndarray):
        c = col[ya:yb, xa:xb] if col.shape[:2] == (H, W) else col[ya - y: yb - y, xa - x: xb - x]
    else: c = np.array(col, np.float32)
    img[ya:yb, xa:xb] = (reg * (1 - a) + c * a).astype(np.uint8)

def txt(img, s, size, x, y, col, anchor="l", fam="oswald", w=700, track=0, alpha=1.0, shadow=0):
    m = text_mask(s, size, fam, w, track)
    if anchor == "c": x -= m.shape[1] / 2
    elif anchor == "r": x -= m.shape[1]
    if shadow: blend(img, cv2.GaussianBlur(m, (0, 0), 6), x + shadow, y + shadow, (0, 0, 0), 0.7 * alpha)
    blend(img, m, x, y, col, alpha)
    return m.shape[1]

def holo_txt(img, s, size, x, y, t, anchor="l", fam="oswald", w=700, alpha=1.0, outline=6):
    m = text_mask(s, size, fam, w)
    if anchor == "c": x -= m.shape[1] / 2
    elif anchor == "r": x -= m.shape[1]
    x, y = int(x), int(y)
    pad = outline + 14
    mp = np.pad(m, pad); xo, yo = x - pad, y - pad
    dil = cv2.dilate(mp, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (outline * 2 + 1,) * 2))
    blend(img, cv2.GaussianBlur(dil, (0, 0), 8), xo + 8, yo + 12, (0, 0, 0), 0.6 * alpha)
    blend(img, dil, xo, yo, INK, alpha)
    ya, yb = max(0, yo), min(H, yo + mp.shape[0]); xa, xb = max(0, xo), min(W, xo + mp.shape[1])
    full = np.zeros((mp.shape[0], mp.shape[1], 3), np.float32)
    full[ya - yo: yb - yo, xa - xo: xb - xo] = holo(t, ya, yb, xa, xb)
    blend(img, mp, xo, yo, full, alpha)
    return m.shape[1]

# ---------- clips from the original videos ----------
CW, CHh = 740, 1028          # footage window (source cropped to 1080x1500 above its captions)
FRAME = 24; PLATE = 104
CARD_W, CARD_H = CW + 2 * FRAME, CHh + 2 * FRAME + PLATE
CLIPDIR = work + "_clips"
def extract(src, start, dur, key):
    d = os.path.join(CLIPDIR, key)
    if os.path.isdir(d) and len(glob.glob(d + "/*.jpg")) >= int(dur * FPS) - 2: return d
    os.makedirs(d, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-i", os.path.join(REPO, src), "-t", f"{dur:.3f}",
                    "-vf", f"fps={FPS},crop=1080:1500:0:0,scale={CW}:{CHh}:flags=lanczos", "-q:v", "2",
                    os.path.join(d, "%04d.jpg")], check=True)
    return d
_clipcache = {}
def clip_frame(d, k):
    files = sorted(glob.glob(d + "/*.jpg"))
    k = max(0, min(len(files) - 1, k))
    key = (d, k)
    if key not in _clipcache:
        if len(_clipcache) > 40: _clipcache.clear()
        _clipcache[key] = cv2.cvtColor(cv2.imread(files[k]), cv2.COLOR_BGR2RGB)
    return _clipcache[key]

# ---------- narration ----------
voice, words, total = narrate(spec, lead=0.08)
lines = spec["lines"]
CARDS = [ln for ln in lines if ln["scene"]["type"] == "card"]
for ln in CARDS:
    sc = ln["scene"]; dur = ln["_se"] - ln["_s"] + 0.6
    half = dur / 2
    sc["_dirs"] = [extract(sc["src"], sc["clips"][0], half + 0.5, f"r{sc['rank']}a"),
                   extract(sc["src"], sc["clips"][1], half + 0.6, f"r{sc['rank']}b")]
    sc["_half"] = (ln["_se"] - ln["_s"]) / 2

def wstart(ln, word):
    for i in range(ln["_w0"], ln["_w1"]):
        if words[i][0].lower().strip(".,!?#") .startswith(word.lower()): return words[i][1] - ln["_s"]
    return 0.0

# ---------- card ----------
RM_OUT = rmask(CARD_W, CARD_H, 34)
RM_WIN = rmask(CW, CHh, 18)
def card(sc, lt, t, flash=0.0):
    """returns (rgb, alpha) arrays of one card, footage at local time lt."""
    rgb = np.zeros((CARD_H, CARD_W, 3), np.uint8)
    foil = holo(t * 1.0, 300, 300 + CARD_H, 150, 150 + CARD_W).astype(np.uint8)
    rgb[:] = foil
    # inner dark line + plate
    rrect(rgb, FRAME - 6, FRAME - 6, FRAME + CW + 5, FRAME + CHh + 5, 22, INK)
    rrect(rgb, FRAME - 6, FRAME + CHh + 14, CARD_W - FRAME + 5, CARD_H - FRAME + 4, 18, INK)
    # footage
    seg = 0 if lt < sc["_half"] else 1
    k = int((lt if seg == 0 else lt - sc["_half"]) * FPS)
    fr = clip_frame(sc["_dirs"][seg], k).astype(np.float32)
    if flash > 0: fr = fr * (1 - flash) + 255 * flash
    win = rgb[FRAME:FRAME + CHh, FRAME:FRAME + CW].astype(np.float32)
    a = (RM_WIN.astype(np.float32) / 255)[..., None]
    rgb[FRAME:FRAME + CHh, FRAME:FRAME + CW] = (win * (1 - a) + fr * a).astype(np.uint8)
    # plate text
    py = FRAME + CHh + 22
    tmp = np.zeros_like(rgb)
    m = text_mask(sc["name"], 54, "oswald", 700)
    blend_local(rgb, m, FRAME + 22, py + 2, WHT)
    m2 = text_mask("FROM " + sc["from"], 25, "quick", 700, track=2)
    blend_local(rgb, m2, CARD_W - FRAME - 22 - m2.shape[1], py + 36, GOLD)
    return rgb, RM_OUT

def blend_local(arr, m, x, y, col):
    h, w = m.shape; x, y = int(x), int(y)
    h = min(h, arr.shape[0] - y); w = min(w, arr.shape[1] - x)
    a = (m[:h, :w].astype(np.float32) / 255)[..., None]
    arr[y:y + h, x:x + w] = (arr[y:y + h, x:x + w] * (1 - a) + np.array(col, np.float32) * a).astype(np.uint8)

def put_card(img, rgb, alpha, cx, cy, sx=1.0, sy=1.0, rot=0.0, shade=0.0, glow=True):
    h, w = alpha.shape
    if sx < 0.02: return
    M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, 1.0)
    M[0] *= sx; M[1] *= sy
    M[0, 2] += cx - w / 2 * 1; M[1, 2] += cy - h / 2 * 1
    # recentre after scale
    M[0, 2] = cx - (M[0, 0] * w / 2 + M[0, 1] * h / 2); M[1, 2] = cy - (M[1, 0] * w / 2 + M[1, 1] * h / 2)
    a = cv2.warpAffine(alpha, M, (W, H), flags=cv2.INTER_LINEAR).astype(np.float32) / 255
    if glow:
        sh = cv2.GaussianBlur(a, (0, 0), 22)
        img[:] = (img * (1 - 0.55 * np.roll(np.roll(sh, 22, 0), 10, 1)[..., None])).astype(np.uint8)
    c = cv2.warpAffine(rgb, M, (W, H), flags=cv2.INTER_LINEAR).astype(np.float32)
    if shade: c = c * (1 - shade)
    img[:] = (img * (1 - a[..., None]) + c * a[..., None]).astype(np.uint8)

def card_back(t, label="?", sub="#1"):
    rgb = holo(t, 300, 300 + CARD_H, 150, 150 + CARD_W).astype(np.uint8)
    pan = np.zeros_like(rgb); pan[:] = INK
    for i in range(-8, 9):
        cv2.line(pan, (CARD_W // 2 + i * 90 - 600, 0), (CARD_W // 2 + i * 90 + 600, CARD_H), INK2, 3, cv2.LINE_AA)
        cv2.line(pan, (CARD_W // 2 + i * 90 + 600, 0), (CARD_W // 2 + i * 90 - 600, CARD_H), INK2, 3, cv2.LINE_AA)
    pm = np.zeros((CARD_H, CARD_W), np.uint8); rrect(pm, FRAME + 10, FRAME + 10, CARD_W - FRAME - 10, CARD_H - FRAME - 10, 26, 255)
    pa = (pm.astype(np.float32) / 255)[..., None]
    rgb = (rgb * (1 - pa) + pan * pa).astype(np.uint8)
    cv2.circle(rgb, (CARD_W // 2, CARD_H // 2), 250, INK, -1, cv2.LINE_AA)
    m = text_mask(label, 380, "oswald", 700)
    foil = holo(t + 1.3, 0, m.shape[0], 0, m.shape[1])
    h, w = m.shape; x, y = CARD_W // 2 - w // 2, CARD_H // 2 - h // 2 - 40
    a = (m.astype(np.float32) / 255)[..., None]
    rgb[y:y + h, x:x + w] = (rgb[y:y + h, x:x + w] * (1 - a) + foil * a).astype(np.uint8)
    m2 = text_mask(sub, 90, "oswald", 700)
    blend_local(rgb, m2, CARD_W // 2 - m2.shape[1] // 2, CARD_H // 2 + 250, WHT)
    return rgb, RM_OUT

# mini cards (hook fan): a still from each card's footage
MINI = {}
def mini(sc, t):
    if sc["rank"] not in MINI:
        fr = clip_frame(sc["_dirs"][0], int(0.8 * FPS))
        MINI[sc["rank"]] = fr
    rgb = holo(t + sc["rank"] * 0.7, 300, 300 + CARD_H, 150, 150 + CARD_W).astype(np.uint8)
    rrect(rgb, FRAME - 6, FRAME - 6, FRAME + CW + 5, FRAME + CHh + 5, 22, INK)
    rrect(rgb, FRAME - 6, FRAME + CHh + 14, CARD_W - FRAME + 5, CARD_H - FRAME + 4, 18, INK)
    a = (RM_WIN.astype(np.float32) / 255)[..., None]
    win = rgb[FRAME:FRAME + CHh, FRAME:FRAME + CW].astype(np.float32)
    rgb[FRAME:FRAME + CHh, FRAME:FRAME + CW] = (win * (1 - a) + MINI[sc["rank"]] * a).astype(np.uint8)
    m = text_mask(f"#{sc['rank']}", 80, "oswald", 700)
    blend_local(rgb, m, FRAME + 22, FRAME + CHh + 16, WHT)
    return rgb, RM_OUT

# ---------- scenes ----------
FAN = {5: (-26, -330, 70), 4: (-13, -170, 18), 3: (0, 0, 0), 2: (13, 170, 18), 1: (26, 330, 70)}
ORDER = [5, 1, 4, 2, 3]
def fan(img, t, lift1=0.0, flip1=0.0, dim=0.0):
    bycard = {ln["scene"]["rank"]: ln["scene"] for ln in CARDS}
    # draw outer first, centre on top; #1 last when lifted
    order = [5, 1, 4, 2, 3] if lift1 <= 0 else [5, 4, 2, 3, 1]
    for r in order:
        ang, dx, dy = FAN[r]
        bob = math.sin(t * 2.2 + r) * 8
        s = 0.5
        cx, cy = W / 2 + dx, 1110 + dy + bob
        rot = -ang
        if r == 1 and lift1 > 0:
            e = back(lift1)
            cx = cx + (W / 2 - cx) * e; cy = cy + (1050 - cy) * e
            rot = rot * (1 - e); s = 0.5 + 0.16 * e
            sx = abs(math.cos(math.pi * flip1)) * s
            if flip1 >= 0.5: rgb, al = card_back(t)
            else: rgb, al = mini(bycard[r], t)
            put_card(img, rgb, al, cx, cy, sx, s, rot)
            continue
        rgb, al = mini(bycard[r], t)
        put_card(img, rgb, al, cx, cy, s, s, rot, shade=dim * 0.55)

def s_hook(ln, lt, dur, t):
    img = background(t)
    fan(img, t)
    pop = back(min(1, (lt + 0.25) / 0.35)) if lt < 0.3 else 1.0
    holo_txt(img, "5 FACTS", int(230 * pop), W / 2, 150 + (1 - pop) * 40, t, "c")
    txt(img, "THAT SOUND FAKE.", 112, W / 2, 430, WHT, "c", shadow=8)
    txt(img, "ALL TRUE", 46, W / 2, 590, GOLD, "c", "quick", 700, track=10)
    return img

def s_tease(ln, lt, dur, t):
    img = background(t)
    u = min(1, lt / 0.5); fl = ease((lt - 0.35) / 0.5)
    fan(img, t, lift1=u, flip1=fl, dim=u)
    holo_txt(img, "#1", 230, W / 2, 140, t, "c")
    txt(img, "IS THE HARDEST", 96, W / 2, 420, WHT, "c", shadow=8)
    txt(img, "TO BELIEVE", 96, W / 2, 530, WHT, "c", shadow=8)
    return img

def header(img, sc, lt, t):
    pop = back(min(1, max(0, lt - 0.12) / 0.32))
    holo_txt(img, f"#{sc['rank']}", int(190 * max(0.2, pop)), 90, 70 + (1 - pop) * 40, t, "l")
    txt(img, "WEIRDNESS", 34, W - 90, 102, DIM, "r", "quick", 700, track=6)
    n = sc["meter"]
    for k in range(5):
        x = W - 90 - (4 - k) * 78 - 62; y = 162
        on = k < n and lt > 0.25 + k * 0.12
        rrect(img, x, y, x + 62, y + 62, 14, INK2)
        if on:
            sub = holo(t + k * 0.3, y + 6, y + 56, x + 6, x + 56).astype(np.uint8)
            m = rmask(50, 50, 10)
            blend(img, m, x + 6, y + 6, _full(sub, x + 6, y + 6))
    if n > 5 and lt > 0.95:
        p = back(min(1, (lt - 0.95) / 0.3))
        tag = np.zeros_like(img);
        w_ = txt_width("OFF THE CHART", 40)
        x0 = W - 90 - w_ - 40; y0 = 246
        rrect(img, x0, y0, x0 + w_ + 40, y0 + 64, 32, (255, 92, 150))
        txt(img, "OFF THE CHART", 40, x0 + 20, y0 + 2, INK, "l", "oswald", 700, alpha=min(1, p))
        for k in range(3):
            sparkle(img, W - 70 + 10 * k, 170 + 40 * k + 10 * math.sin(t * 6 + k), 10 + 4 * math.sin(t * 9 + k), 0.9, GOLD)

def _full(sub, x, y):
    out = np.zeros((H, W, 3), np.float32); h, w = sub.shape[:2]; out[y:y + h, x:x + w] = sub; return out
def txt_width(s, size, fam="oswald"): return int(F(size, fam).getlength(s))

CARD_CY = 330 + CARD_H / 2
def s_card(ln, lt, dur, t):
    sc = ln["scene"]; img = background(t)
    i = lines.index(ln); prev = lines[i - 1]
    FL = 0.32
    if lt < FL / 2 and prev["scene"]["type"] == "card":   # flip: old card turns edge-on ...
        psc = prev["scene"]; plt = t - prev["_s"]
        rgb, al = card(psc, plt, t)
        put_card(img, rgb, al, W / 2, CARD_CY, max(0.02, math.cos(math.pi * lt / FL)), 1.0)
        header(img, psc, plt, t)
        return img
    sx = 1.0
    if lt < FL: sx = max(0.02, -math.cos(math.pi * lt / FL)) if prev["scene"]["type"] == "card" else max(0.02, eout(lt / FL))
    fl = 0.0
    h_ = sc["_half"]
    if h_ - 0.02 <= lt < h_ + 0.16: fl = 1 - (lt - h_ + 0.02) / 0.18
    rgb, al = card(sc, lt, t, flash=max(0, fl) * 0.85)
    put_card(img, rgb, al, W / 2, CARD_CY, sx * 1.0, 1.0)
    header(img, sc, lt, t)
    if sc["rank"] == 1 and lt < 0.9:
        for k in range(10):
            ang = k * 0.628 + 0.3; rr = 300 + 700 * eout(lt / 0.9)
            sparkle(img, W / 2 + math.cos(ang) * rr * 0.8, CARD_CY + math.sin(ang) * rr, 14, 1 - lt / 0.9, GOLD)
    return img

def s_end(ln, lt, dur, t):
    img = background(t)
    sc = ln["scene"]; c = sc.get("click_at", 0.5)
    holo_txt(img, "SOUNDS", 190, W / 2, 230, t, "c")
    holo_txt(img, "FAKE?", 190, W / 2, 450, t + 0.6, "c")
    # switch
    tw_, th_ = 640, 190; x0, y0 = W / 2 - tw_ / 2, 820
    u = ease((lt - c) / 0.28)
    rrect(img, x0 - 8, y0 - 8, x0 + tw_ + 8, y0 + th_ + 8, th_ // 2 + 8, (60, 52, 100))
    rrect(img, x0, y0, x0 + tw_, y0 + th_, th_ // 2, INK2)
    if u > 0:
        m = rmask(int(tw_), th_, th_ // 2)
        cut = int(tw_ * u)
        m[:, cut:] = 0
        blend(img, m, x0, y0, _full(holo(t, int(y0), int(y0) + th_, int(x0), int(x0) + int(tw_)), int(x0), int(y0)))
    txt(img, "FAKE", 60, x0 + 100, y0 + th_ + 26, WHT if u < 0.5 else (80, 72, 120), "c")
    txt(img, "TRUE", 60, x0 + tw_ - 100, y0 + th_ + 26, GOLD if u >= 0.5 else (80, 72, 120), "c")
    # knob = mini card
    kx = x0 + 100 + (tw_ - 200) * u; ky = y0 + th_ / 2
    rgb, al = card_back(t, "?!", "")
    put_card(img, rgb, al, kx, ky, 0.17, 0.17, -8 + 16 * u)
    if lt > c + 0.2:
        p = back(min(1, (lt - c - 0.2) / 0.3))
        txt(img, "IT'S TRUE.", int(130 * max(0.3, p)), W / 2, 1170, WHT, "c", shadow=8)
        txt(img, "FOLLOW FOR MORE", 50, W / 2, 1360, GOLD, "c", "quick", 700, track=8, alpha=min(1, p))
        if lt - c < 1.0:
            for k in range(12):
                ang = k * 0.52; rr = 120 + 520 * eout((lt - c) / 1.0)
                sparkle(img, kx + math.cos(ang) * rr, ky + math.sin(ang) * rr, 12, 1 - (lt - c), GOLD)
    return img

SCENES = {"hook": s_hook, "tease": s_tease, "card": s_card, "end": s_end}

# ---------- music ----------
rng = np.random.default_rng(3)
music = np.zeros(int(total * SR) + SR, np.float32)
def nt(semi): return 220.0 * 2 ** (semi / 12)
def pluck(f, dur=0.35):
    tt = np.arange(int(dur * SR)) / SR
    saw = sum(np.sin(2 * np.pi * f * h * tt) / h for h in range(1, 7))
    return saw * np.exp(-tt * 11) * (1 - np.exp(-tt * 400))
def kick():
    tt = np.arange(int(0.3 * SR)) / SR
    return np.sin(2 * np.pi * (45 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9)
def clap():
    tt = np.arange(int(0.2 * SR)) / SR
    nz = rng.normal(0, 1, len(tt)); nz = nz - np.convolve(nz, np.ones(4) / 4, mode="same")
    return nz * (np.exp(-tt * 30) + 0.5 * np.exp(-((tt - 0.012) * 300) ** 2))
def hat():
    tt = np.arange(int(0.06 * SR)) / SR
    nz = rng.normal(0, 1, len(tt)); nz = nz - np.convolve(nz, np.ones(3) / 3, mode="same")
    return nz * np.exp(-tt * 80)
def sub(f, dur):
    tt = np.arange(int(dur * SR)) / SR
    return np.sin(2 * np.pi * f * tt) * np.exp(-tt * 2.5) * (1 - np.exp(-tt * 200))
def shing(at, g=0.07):
    tt = np.arange(int(1.2 * SR)) / SR
    s = sum(np.sin(2 * np.pi * f * tt + k) for k, f in enumerate((2637, 3136, 3951, 4699, 5274))) / 5
    place(music, at, s * np.exp(-tt * 4) * (1 - np.exp(-tt * 300)), g)
def riser(end, dur=1.2, g=0.1):
    n = int(dur * SR); tt = np.arange(n) / SR
    nz = rng.normal(0, 1, n); nz = nz - np.convolve(nz, np.ones(8) / 8, mode="same")
    tone_ = np.sin(2 * np.pi * np.cumsum(300 + 1500 * (tt / dur) ** 2) / SR)
    place(music, end - dur, (nz * 0.6 + tone_ * 0.4) * (tt / dur) ** 2, g)

BEAT = 60 / 112
CH = [[0, 3, 7, 12], [-4, 0, 3, 8], [-9, -5, -2, 3], [-2, 2, 5, 10]]   # Am F C G (relative to A3)
BASS = [-12, -16, -21, -14]
for k in range(int(total / (BEAT / 2)) + 1):
    at = k * BEAT / 2; bar = (k // 8) % 4; st = k % 8; ch = CH[bar]
    place(music, at, pluck(nt(ch[[0, 2, 1, 3, 2, 1, 3, 2][st]] + 12)), 0.05)
    if st % 2 == 0: place(music, at, kick(), 0.32)
    if st in (2, 6): place(music, at, clap(), 0.06)
    place(music, at + BEAT / 4, hat(), 0.025)
    if st == 0: place(music, at, sub(nt(BASS[bar]), BEAT * 3.5), 0.2)
hook_hit(music, 0.32); shing(0.02, 0.06)
for i, ln in enumerate(lines):
    s0 = ln["_s"]; st = ln["scene"]["type"]
    if i > 0: whoosh(music, s0 - 0.05, 0.08, 0.3); shing(s0 + 0.05, 0.05)
    if st == "tease": shing(s0 + 0.45, 0.07)
    if st == "card":
        place(music, s0 + ln["scene"]["_half"], clap(), 0.05)
        if ln["scene"]["rank"] == 1: riser(s0 + 0.02, 1.4, 0.09); hook_hit(music, 0) ; place(music, s0, kick(), 0.4)
    if st == "end":
        c = s0 + ln["scene"].get("click_at", 0.5)
        place(music, c, kick(), 0.3); shing(c + 0.05, 0.09)
        for j, sm in enumerate((12, 15, 19, 24, 27)): place(music, c + 0.18 + j * 0.07, pluck(nt(sm + 12), 0.6), 0.07)
music = music[: int(total * SR)]
write_audio(voice, np.pad(music, (0, max(0, len(voice) - len(music))))[: len(voice)], work + "_audio.wav", music_gain=0.55, duck=0.45)

# ---------- captions / compositing ----------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 72
    f = F(size, "quick", 700)
    while f.getlength(" ".join(ws)) > W - 260 and size > 44: size -= 4; f = F(size, "quick", 700)
    gap = f.getlength(" ") + 16
    tw_ = sum(f.getlength(w) for w in ws) + gap * (len(ws) - 1); x = (W - tw_) / 2; y = 1588
    x0, y0, x1, y1 = x - 44, y - 26, x + tw_ + 44, y + size + 30
    rm = rmask(int(x1 - x0) + 8, int(y1 - y0) + 8, 44)
    blend(img, rm, x0 - 4, y0 - 4, _full(holo(t, int(y0) - 4, int(y0) - 4 + rm.shape[0], int(x0) - 4, int(x0) - 4 + rm.shape[1]), int(x0) - 4, int(y0) - 4))
    rrect(img, x0, y0, x1, y1, 40, (12, 10, 26))
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]; wl = f.getlength(w)
        if on:
            sx0, sy0 = int(x - 12), int(y - 6)
            cm = rmask(int(wl + 24), int(size + 22), 14)
            blend(img, cm, sx0, sy0, _full(holo(t * 2, sy0, sy0 + cm.shape[0], sx0, sx0 + cm.shape[1]), sx0, sy0))
        txt(img, w, size, x, y - size * 0.12, INK if on else WHT, "l", "quick", 700)
        x += wl + gap

def scene_img(t, ln):
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    return SCENES[ln["scene"]["type"]](ln, lt, dur, t)

def frame(t, fi):
    ln = active_line(spec, t) or lines[0]; i = lines.index(ln)
    img = scene_img(t, ln)
    if i > 0:
        ph = (t - (ln["_s"] - 0.12)) / 0.12
        if 0 <= ph < 1:   # old card squashes to an edge (first half of the flip)
            old = scene_img(ln["_s"] - 0.12 + ph * 0.12, lines[i - 1]) if lines[i - 1]["scene"]["type"] != "card" else None
            if old is not None:
                img = (old * (1 - ease(ph)) + img * ease(ph)).astype(np.uint8)
    if t > total - 0.45:
        a = ease((t - (total - 0.45)) / 0.45)
        img = (img * (1 - a) + scene_img(lines[0]["_s"], lines[0]) * a).astype(np.uint8)
    caption(img, t)
    rect_ = (30, H - 16, W - 30, H - 8)
    cv2.rectangle(img, (30, H - 16), (W - 30, H - 8), (48, 42, 84), -1)
    pw = int((W - 60) * t / total)
    if pw > 1:
        img[H - 16:H - 8, 30:30 + pw] = holo(t, H - 16, H - 8, 30, 30 + pw).astype(np.uint8)
        cv2.circle(img, (30 + pw, H - 12), 9, WHT, -1, cv2.LINE_AA)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), int(float(tt_) * FPS))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=22); print(f"done {total:.1f}s")
