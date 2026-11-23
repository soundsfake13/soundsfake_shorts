"""LONG-FORM (16:9, 1920x1080) — 'Sounds Fake: Deep Dive' ep07: TIME.
Look: "midnight clockwork" — ink-navy background with slow brass gears and drifting dust, cream type, brass + cyan accents.
Beats: glowing timelines with brackets, animated calendar pages (deleted / sliding days), light-travel diagrams, Venus,
the date line, pyramid + mammoth silhouettes, height-dilation clocks and GPS satellites.
Based on engine/long/ep06_earth.py.
Usage: python3 engine/long/ep07_time.py spec.json out.mp4 [t1,t2,... preview]
"""
import json, math, os, random, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import core
from core import narrate, write_audio, caption_groups, group_at, ease, eout, back, tone, place, hook_hit, whoosh, SR

W, H, FPS = 1920, 1080, 30
spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
rng = np.random.default_rng(7); random.seed(7)
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
HERE = os.path.dirname(os.path.abspath(__file__))
SERIF = os.path.join(os.path.dirname(HERE), "fonts", "OldStandard-Bold.ttf")
_fc = {}
def F(s, w="Black"):
    k = (int(s), w)
    if k not in _fc: _fc[k] = ImageFont.truetype(SERIF if w == "Serif" else f"{FD}InterDisplay-{w}.otf", int(s))
    return _fc[k]
BRASS, CYAN, WHITE, DIM, RED, GREEN = (240, 190, 96), (110, 210, 240), (246, 240, 228), (140, 146, 170), (240, 100, 80), (110, 230, 150)
INKD = (10, 12, 26)
COL = dict(gold=BRASS, cyan=CYAN, white=WHITE, dim=(190, 180, 160), red=RED, green=GREEN)
def lerpc(a, b, u): return tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3))

# ---------------- background: ink navy + warm vignette + slow brass gears + dust ----------------
def lowf(h, w, cell, seed):
    r = np.random.default_rng(seed); s = r.random((h // cell + 2, w // cell + 2)).astype(np.float32)
    return np.asarray(Image.fromarray((s * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = np.exp(-(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.45) / (H * 0.7)) ** 2))
BG = np.zeros((H, W, 3), np.float32) + np.array([6, 8, 20], np.float32)
BG += vig[..., None] * np.array([16, 20, 42], np.float32) + (lowf(H, W, 340, 1) ** 2.5)[..., None] * np.array([26, 18, 10], np.float32)
BG_IMG = Image.fromarray(np.clip(BG, 0, 255).astype(np.uint8))

def gear_sprite(R, teeth, col, a=40, hole=0.32, spokes=5):
    S = int(R * 2 + 40); g = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(g); c = S / 2
    pts = []
    for k in range(teeth * 4):
        ang = 2 * math.pi * k / (teeth * 4); r = R + (14 if k % 4 in (1, 2) else -6)
        pts.append((c + r * math.cos(ang), c + r * math.sin(ang)))
    d.polygon(pts, outline=col + (a,), width=6)
    d.ellipse([c - R * 0.78, c - R * 0.78, c + R * 0.78, c + R * 0.78], outline=col + (int(a * 0.8),), width=4)
    d.ellipse([c - R * hole, c - R * hole, c + R * hole, c + R * hole], outline=col + (a,), width=5)
    for k in range(spokes):
        ang = 2 * math.pi * k / spokes
        d.line([(c + R * hole * math.cos(ang), c + R * hole * math.sin(ang)), (c + R * 0.78 * math.cos(ang), c + R * 0.78 * math.sin(ang))], fill=col + (int(a * 0.8),), width=6)
    return g
GEARS = [(gear_sprite(330, 24, (200, 160, 90), 34), 1720, 980, 3.0), (gear_sprite(190, 14, (200, 160, 90), 30), 1340, 1060, -5.2), (gear_sprite(240, 18, (120, 160, 220), 24), 150, 90, 4.0)]
DUST = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 2.0), rng.uniform(0, 6.3), rng.uniform(4, 16)) for _ in range(140)]
def space(t, gears=True):
    img = BG_IMG.copy()
    if gears:
        for spr, gx, gy, sp in GEARS:
            r = spr.rotate(t * sp, resample=Image.BILINEAR); img.paste(r, (int(gx - r.width / 2), int(gy - r.height / 2)), r)
    d = ImageDraw.Draw(img)
    for (x, y, s, ph, v) in DUST:
        py = (y - v * t) % H; px = x + 8 * math.sin(t * 0.3 + ph)
        c = int(120 + 80 * (0.5 + 0.5 * math.sin(t * 1.5 + ph))); d.ellipse([px - s, py - s, px + s, py + s], fill=(c, int(c * 0.9), int(c * 0.75)))
    return img

def bloom(img, k=0.5):
    a = np.asarray(img).astype(np.float32)
    s = Image.fromarray(np.clip((a - 150) * 1.5, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    b = np.asarray(s.filter(ImageFilter.GaussianBlur(8)).resize((W, H), Image.BILINEAR)).astype(np.float32)
    return Image.fromarray(np.clip(a + b * k, 0, 255).astype(np.uint8))

def halo(img, cx, cy, r, col, strength=160):
    g = Image.new("L", (W, H), 0); ImageDraw.Draw(g).ellipse([cx - r, cy - r, cx + r, cy + r], fill=int(strength))
    img.paste(Image.new("RGB", (W, H), col), (0, 0), g.filter(ImageFilter.GaussianBlur(r * 0.5)))

def paste(img, spr, cx, cy): img.paste(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)), spr)

# ---------------- type ----------------
def text(img, s, size, x, y, col=WHITE, w="Black", anchor="mm", u=1.0, maxw=W - 200, shadow=True):
    if u <= 0: return
    d = ImageDraw.Draw(img)
    while d.textlength(s, font=F(size, w)) > maxw and size > 24: size -= 4
    f = F(size, w); y = y + (1 - u) * 26
    col = tuple(int(c * u + 5 * (1 - u)) for c in col)
    if shadow: d.text((x + 3, y + 4), s, font=f, fill=(0, 0, 0), anchor=anchor)
    d.text((x, y), s, font=f, fill=col, anchor=anchor)

def pill(img, s, size, x, y, fill=BRASS, ink=(16, 14, 24), u=1.0):
    if u <= 0: return
    d = ImageDraw.Draw(img); f = F(size, "Bold"); tw = d.textlength(s, font=f); y = y + (1 - u) * 16
    d.rounded_rectangle([x - tw / 2 - 26, y - size * 0.72, x + tw / 2 + 26, y + size * 0.72], int(size * 0.72), fill=fill)
    d.text((x, y), s, font=f, fill=ink, anchor="mm")

def fmtnum(v, kind):
    if kind == "int": return f"{int(round(v)):,}"
    if kind == "f1": return f"{v:,.1f}"
    return str(v)

def clockface(img, cx, cy, R, t, speed=1.0, col=BRASS, face=(18, 20, 40), alpha=255, ticks=True, hands=True):
    """A clean analog clock. speed scales the second hand."""
    d = ImageDraw.Draw(img)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=face, outline=col, width=max(3, int(R * 0.06)))
    if ticks:
        for k in range(60):
            a = math.radians(k * 6); r0 = R * (0.80 if k % 5 == 0 else 0.87)
            d.line([(cx + r0 * math.sin(a), cy - r0 * math.cos(a)), (cx + R * 0.92 * math.sin(a), cy - R * 0.92 * math.cos(a))], fill=col if k % 5 == 0 else DIM, width=max(2, int(R * (0.03 if k % 5 == 0 else 0.012))))
    if hands:
        s = t * speed; m = s / 60 * 6 + 1.6; h = m / 12 + 2.1
        for ang, L, wd, c in ((h, 0.48, 0.055, WHITE), (m, 0.7, 0.04, WHITE), (s * 2 * math.pi / 60, 0.8, 0.016, RED)):
            d.line([(cx, cy), (cx + R * L * math.sin(ang), cy - R * L * math.cos(ang))], fill=c, width=max(2, int(R * wd)))
        d.ellipse([cx - R * 0.06, cy - R * 0.06, cx + R * 0.06, cy + R * 0.06], fill=col)

def stopwatch(img, x, y, s, label, col=BRASS, size=150):
    text(img, s, size, x, y, col); text(img, label, 44, x, y + size * 0.75, WHITE, w="Bold")

# ---------------- beats: generic ----------------
def b_cold(sc, lt, dur, t):
    img = space(t)
    for i, s in enumerate(sc["lines"]):
        text(img, s, sc.get("size", 120), W / 2, 330 + i * sc.get("size", 120) * 1.15, BRASS if i == 1 else WHITE, u=1.0 if i == 0 else ease((lt - i * 0.5) / 0.4))
    if "sub" in sc: pill(img, sc["sub"], 40, W / 2, 640, fill=CYAN, u=ease((lt - 0.8) / 0.4))
    return img

def b_chapter(sc, lt, dur, t):
    img = space(t); u = back(lt / 0.45)
    clockface(img, W / 2, 330, 190, t * 6, speed=1, alpha=255)
    text(img, f"{sc['ch']:02d}", 150, W / 2, 330, BRASS, u=min(1, u))
    text(img, sc["title"], 84, W / 2, 620, WHITE, u=ease((lt - 0.3) / 0.4))
    if "sub" in sc: text(img, sc["sub"], 42, W / 2, 712, CYAN, w="SemiBold", u=ease((lt - 0.6) / 0.4))
    return img

def b_text(sc, lt, dur, t):
    img = space(t)
    if sc.get("clock"):
        clockface(img, W / 2, 760, 210, t * 8, speed=1)
    for i, s in enumerate(sc["lines"]):
        y = sc.get("y", 420) - (170 if sc.get("clock") else 0) + i * sc.get("size", 96) * 1.2
        text(img, s, sc.get("size", 96), W / 2, y, BRASS if str(i) in sc.get("accent", {}) else WHITE, u=ease((lt - i * 0.35) / 0.4))
    return img

def b_counter(sc, lt, dur, t):
    img = space(t)
    v = sc["from"] + (sc["to"] - sc["from"]) * eout((lt - 0.2) / max(0.6, sc.get("secs", 2.0)))
    text(img, sc.get("prefix", "") + fmtnum(v, sc.get("fmt", "int")) + sc.get("suffix", ""), sc.get("size", 210), W / 2, 380, BRASS, u=ease(lt / 0.3))
    text(img, sc["label"], 62, W / 2, 560, WHITE, w="Bold", u=ease((lt - 0.3) / 0.4))
    if "note" in sc: text(img, sc["note"], 40, W / 2, 640, CYAN, w="SemiBold", u=ease((lt - 0.9) / 0.4))
    return img

def b_compare(sc, lt, dur, t):
    img = space(t); mx = max(sc["lv"], sc["rv"]); L = 880; cols = [COL[c] for c in sc.get("colors", ["cyan", "gold"])]
    for i, (lab, val, tx, col) in enumerate(((sc["left"], sc["lv"], sc["lt"], cols[0]), (sc["right"], sc["rv"], sc["rt"], cols[1]))):
        y = 420 + i * 240; w = L * val / mx * eout((lt - 0.2 - i * 0.6) / 1.0)
        text(img, " ".join(lab), 54, 560, y, WHITE, w="Bold", anchor="rm", u=ease((lt - i * 0.6) / 0.3), maxw=480)
        d = ImageDraw.Draw(img)
        if w > 4: d.rounded_rectangle([600, y - 50, 600 + w, y + 50], 26, fill=col)
        if w > 4: text(img, tx, 50, 600 + w + 30, y, col, anchor="lm", u=ease((lt - 0.8 - i * 0.6) / 0.3))
    if lt > 2.0: pill(img, "THE YEAR ENDS FIRST", 44, W / 2, 210, fill=BRASS, u=ease((lt - 2.0) / 0.4))
    return img

def b_stamp(sc, lt, dur, t):
    img = space(t); n = len(sc["lines"]); size = 96 if n > 1 else 110
    for i, s in enumerate(sc["lines"]): text(img, s, size, W / 2, 210 + i * size * 1.25, WHITE if i == 0 else BRASS, u=ease((lt - i * 0.25) / 0.35))
    at = 0.5 + n * 0.25; u = (lt - at) / 0.22; sc_col = RED if sc.get("col") == "red" else GREEN
    if u > 0:
        s = 1 + 1.4 * (1 - eout(u)); a = min(1, u * 2)
        st = Image.new("RGBA", (760, 300), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
        sd.rounded_rectangle([20, 40, 740, 260], 30, outline=sc_col + (int(255 * a),), width=16)
        sd.text((380, 150), sc.get("stamp", "TRUE"), font=F(170, "Black"), fill=sc_col + (int(255 * a),), anchor="mm")
        st = st.rotate(-8, expand=True, resample=Image.BICUBIC); st = st.resize((int(st.width * s * 0.62), int(st.height * s * 0.62)), Image.BICUBIC)
        paste(img, st, W / 2, 250 + n * size * 1.25 + 120)
    return img

def b_recap(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img)
    text(img, "QUICK RECAP", 92, W / 2, 150, BRASS, u=1)
    n = len(sc["items"])
    for i, s in enumerate(sc["items"]):
        u = ease((lt - 0.3 - i * (dur - 1.0) / n) / 0.3); y = 310 + i * 130
        if u <= 0: continue
        d.rounded_rectangle([520, y - 32, 584, y + 32], 12, outline=CYAN, width=5)
        if u > 0.6: d.line([(532, y), (550, y + 20), (596, y - 36)], fill=GREEN, width=10)
        text(img, s, 64, 630, y, WHITE, anchor="lm", u=u, maxw=1150)
    return img

def b_outro(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img)
    text(img, sc.get("q", "Which one sounded the MOST fake?"), 74, W / 2, 240, WHITE)
    click = sc.get("click_at", 1.6); on = ease((lt - click) / 0.25); cx, cy, w_, h_ = W / 2, 440, 300, 130
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=BRASS if on > 0.5 else (50, 56, 90), outline=WHITE, width=6)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; d.ellipse([kx - h_ / 2 + 16, cy - h_ / 2 + 16, kx + h_ / 2 - 16, cy + h_ / 2 - 16], fill=WHITE)
    text(img, "FAKE", 60, cx - w_ / 2 - 110, cy, WHITE if on < 0.5 else DIM); text(img, "TRUE", 60, cx + w_ / 2 + 110, cy, BRASS if on >= 0.5 else DIM)
    pill(img, "SUBSCRIBE · NEW DEEP DIVE EVERY TUE & FRI", 40, W / 2, 640, fill=RED, ink=WHITE, u=ease((lt - click - 0.4) / 0.4))
    return img

# ---------------- beats: timeline ----------------
def _vlabel(v, sc):
    if sc.get("ad"): return f"{-v} BC" if v < 0 else (f"AD {v}" if v < 1000 else f"{v}")
    if sc["unit"] == "MILLION YEARS AGO": return "TODAY" if v == 0 else f"{v} MILLION YRS AGO"
    if sc["unit"] == "YEARS AGO": return f"{v:,} YEARS AGO"
    return str(v)
def b_timeline(sc, lt, dur, t):
    img = space(t); hook = sc.get("mode") == "hook"
    a, b = sc["span"]; x0, x1 = 170, 1750; ay = 700 if hook else 560
    X = lambda v: x0 + (x1 - x0) * (v - a) / (b - a)
    d = ImageDraw.Draw(img)
    # axis with a glowing arrow (time flows to the right)
    d.line([(x0 - 40, ay), (x1 + 50, ay)], fill=(90, 96, 130), width=6)
    d.polygon([(x1 + 80, ay), (x1 + 46, ay - 18), (x1 + 46, ay + 18)], fill=(90, 96, 130))
    span = abs(b - a); step = [s for s in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000) if span / s <= 9][0]
    v = math.ceil(min(a, b) / step) * step
    while v <= max(a, b):
        x = X(v); d.line([(x, ay - 12), (x, ay + 12)], fill=(90, 96, 130), width=3)
        if not sc.get("ad") or True:
            lab = (f"{-v} BC" if v < 0 else str(v)) if sc.get("ad") else f"{v:,}"
            d.text((x, ay + 34), lab, font=F(24, "SemiBold"), fill=(120, 126, 156), anchor="mm")
        v += step
    if not sc.get("ad"): pill(img, sc["unit"], 26, W / 2, ay + 78, fill=(34, 38, 64), ink=DIM)
    k0 = sc.get("anim", 0); ev = sc["events"]
    def appear(i):
        if hook: return ease((lt - 0.15 - i * 0.35) / 0.35)
        if i < k0: return 1.0
        return ease((lt - 0.25 - (i - k0) * 0.6) / 0.45)
    # brackets (below the axis): appear with their later endpoint
    for j, (p, q, lab, c) in enumerate(sc.get("brackets", [])):
        ip = max(i for i, e in enumerate(ev) if e[0] in (p, q)); u = appear(ip)
        if u <= 0: continue
        col = COL[c]; by = ay + 120 + (j % 2) * 0 ; xa, xb = X(p), X(q); xm = xa + (xb - xa) * eout(u)
        d = ImageDraw.Draw(img)
        d.line([(xa, by), (xm, by)], fill=col, width=6); d.line([(xa, by - 22), (xa, by + 22)], fill=col, width=6)
        if u > 0.95: d.line([(xb, by - 22), (xb, by + 22)], fill=col, width=6)
        text(img, lab, 50 if hook else 54, (xa + xb) / 2, by + 62, col, u=ease((u - 0.6) / 0.4), maxw=max(300, abs(xb - xa) - 20))
    # events (dot + label above axis)
    for i, (v, lab, c) in enumerate(ev):
        u = appear(i)
        if u <= 0: continue
        col = COL[c]; x = X(v)
        p = (t * 1.0 + i * 0.3) % 1; rr = 14 + 40 * p; d = ImageDraw.Draw(img)
        d.ellipse([x - rr, ay - rr, x + rr, ay + rr], outline=lerpc(col, INKD, p), width=4)
        halo(img, x, ay, 30, col, 230); d = ImageDraw.Draw(img); d.ellipse([x - 13, ay - 13, x + 13, ay + 13], fill=WHITE)
        ly = ay - 110 - (60 if (i % 2 and not hook) else 0)
        d.line([(x, ay - 20), (x, ly + 34)], fill=col, width=3)
        pill(img, lab, 40 if hook else 44, max(260, min(W - 260, x)), ly, fill=col, ink=INKD, u=u)
        if not hook: text(img, _vlabel(v, sc), 34, max(260, min(W - 260, x)), ly - 62, col, w="Bold", u=u)
    if hook:
        for i, s in enumerate(sc["lines"]):
            text(img, s, 104, W / 2, 140 + i * 118, BRASS if i == 1 else WHITE, u=1.0 if i == 0 else ease((lt - i * 0.25) / 0.3), maxw=1700)
    return img

# ---------------- beats: calendar page ----------------
def b_calendar(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img)
    px, py, pw, ph = 470, 110, 980, 760
    d.rounded_rectangle([px + 12, py + 16, px + pw + 12, py + ph + 16], 30, fill=(0, 0, 0))
    d.rounded_rectangle([px, py, px + pw, py + ph], 30, fill=(244, 236, 218))
    d.rounded_rectangle([px, py, px + pw, py + 150], 30, fill=(170, 52, 40)); d.rectangle([px, py + 110, px + pw, py + 150], fill=(170, 52, 40))
    for k in range(6): rx = px + 120 + k * 150; d.ellipse([rx - 14, py - 20, rx + 14, py + 8], fill=(60, 60, 70))
    d.text((px + pw / 2, py + 78), f"{sc['month']} {sc['year']}", font=F(78, "Serif"), fill=(250, 240, 222), anchor="mm")
    cw, ch_ = pw / 7, 100; gy = py + 200
    for k, s in enumerate("SMTWTFS"): d.text((px + cw * (k + 0.5), gy), s, font=F(34, "Bold"), fill=(150, 120, 100), anchor="mm")
    cut = sc.get("cut"); slide = bool(cut) and sc.get("slide") and cut[1] > cut[0]
    gone = set(range(cut[0], cut[1] + 1)) if cut else set()
    done = sc.get("done", False)
    p_strike = 1.0 if done else ease((lt - 0.8) / 0.6)
    p_fade = 1.0 if done else ease((lt - 1.8) / 0.5)
    p_slide = (1.0 if done else eout((lt - 2.5) / 0.9)) if slide else 0.0
    ncut = len(gone) if slide else 0
    for day in range(1, sc["days"] + 1):
        i0 = sc["first"] + day - 1
        i1 = i0 - ncut if (slide and day > cut[1]) else i0
        if slide and day > cut[1] and 0 < p_slide < 1:   # crossfade: old cell fades out, new cell fades in
            for idx, al in ((i0, max(0.0, 1 - 2 * p_slide)), (i1, max(0.0, 2 * p_slide - 1))):
                r, c = divmod(idx, 7); x, y = px + cw * (c + 0.5), gy + 80 + r * ch_ - (1 - al) * 14 * (1 if idx == i1 else -1)
                d.text((x, y), str(day), font=F(52, "Bold"), fill=lerpc((244, 236, 218), (40, 34, 40), al), anchor="mm")
            continue
        r, c = divmod(i1 if p_slide >= 1 else i0, 7)
        x, y = px + cw * (c + 0.5), gy + 80 + r * ch_
        if day in gone:
            a = 1 - p_fade
            if a <= 0: continue
            col = lerpc((244, 236, 218), (60, 50, 50), a)
            d.text((x, y), str(day), font=F(52, "Bold"), fill=col, anchor="mm")
            if p_strike > 0:
                L = 40 * p_strike; d.line([(x - L, y - L * 0.5), (x + L, y + L * 0.5)], fill=lerpc((244, 236, 218), RED, a), width=8)
            continue
        hi = day in sc.get("hi", [])
        if hi and (lt > 0.4 or done):
            hu = 1.0 if done else ease((lt - (3.2 if slide else 1.2)) / 0.4) if day != sc.get("hi", [0])[0] else ease((lt - 0.4) / 0.4)
            if hu > 0:
                d.ellipse([x - 44 * hu, y - 44 * hu, x + 44 * hu, y + 44 * hu], fill=(240, 190, 96))
        d.text((x, y), str(day), font=F(52, "Bold"), fill=(40, 34, 40), anchor="mm")
    if sc.get("star"):
        day = sc["star"]; i0 = sc["first"] + day - 1; r, c = divmod(i0, 7); x, y = px + cw * (c + 0.5), gy + 80 + r * ch_
        u = ease((lt - 0.8) / 0.4)
        if u > 0:
            halo(img, x, y, 90, (255, 200, 90), int(200 * u)); d = ImageDraw.Draw(img)
            d.ellipse([x - 46, y - 46, x + 46, y + 46], fill=BRASS); d.text((x, y), str(day), font=F(54, "Black"), fill=INKD, anchor="mm")
            pill(img, "A REAL DATE", 40, px + pw + 200, y, fill=RED, ink=WHITE, u=u); d = ImageDraw.Draw(img); d.line([(x + 50, y), (px + pw + 50, y)], fill=RED, width=5) if u > 0.5 else None
    if cut and not slide:
        u = ease((lt - 1.6) / 0.4); pill(img, sc.get("label", "FRIDAY · DELETED"), 40, W / 2, py + ph + 52, fill=RED, ink=WHITE, u=u)
    if slide and False:
        u = 1.0 if done else ease((lt - 3.4) / 0.4); pill(img, "WED 2  →  THU 14", 40, W / 2, py + ph + 52, fill=RED, ink=WHITE, u=u)
    return img

# ---------------- beats: light ----------------
def sun(img, x, y, r, a=1.0):
    if a <= 0: return
    halo(img, x, y, r * 2.0, (255, 160, 60), int(200 * a)); d = ImageDraw.Draw(img)
    d.ellipse([x - r, y - r, x + r, y + r], fill=lerpc(INKD, (255, 196, 90), a)); d.ellipse([x - r * 0.72, y - r * 0.72, x + r * 0.72, y + r * 0.72], fill=lerpc(INKD, (255, 230, 160), a))
def planet(img, x, y, r, c1=(60, 130, 220), c2=(90, 170, 90), lit=1.0):
    d = ImageDraw.Draw(img); halo(img, x, y, r * 1.3, (60, 120, 230), 90); d = ImageDraw.Draw(img)
    d.ellipse([x - r, y - r, x + r, y + r], fill=c1); d.ellipse([x - r * 0.5, y - r * 0.55, x + r * 0.1, y + r * 0.05], fill=c2); d.ellipse([x + r * 0.1, y + r * 0.1, x + r * 0.55, y + r * 0.6], fill=c2)
def b_light(sc, lt, dur, t):
    img = space(t, gears=False); m = sc["mode"]; d = ImageDraw.Draw(img)
    if m in ("sun", "late"):
        sx, ex, y = 300, 1640, 520
        if m == "sun":
            sun(img, sx, y, 150); planet(img, ex, y, 46)
            p = ((lt - 0.3) / max(1.5, dur - 0.8)); p = min(1.0, max(0.0, p)); d = ImageDraw.Draw(img)
            xx_ = sx + 160 + (ex - 60 - sx - 160) * p
            for k in range(26):
                q = k / 26; xk = xx_ - q * 220
                if xk < sx + 160: break
                d.ellipse([xk - 10 * (1 - q), y - 10 * (1 - q), xk + 10 * (1 - q), y + 10 * (1 - q)], fill=lerpc((255, 240, 180), INKD, q))
            halo(img, xx_, y, 30, (255, 230, 150), 230)
            tsec = 500 * p; stopwatch(img, W / 2, 230, f"{int(tsec // 60)}:{int(tsec % 60):02d}", "MIN : SEC", BRASS)
            text(img, "≈ 150 MILLION KM", 40, W / 2, 780, CYAN, w="Bold"); d = ImageDraw.Draw(img); d.line([(sx + 170, 730), (ex - 60, 730)], fill=CYAN, width=3)
            text(img, "(not to scale)", 28, W / 2, 840, DIM, w="SemiBold")
        else:
            gone = ease((lt - 1.0) / 0.5)
            sun(img, sx, y, 150, 1 - gone)
            if gone > 0: d = ImageDraw.Draw(img); d.ellipse([sx - 150, y - 150, sx + 150, y + 150], outline=lerpc(INKD, DIM, gone), width=4)
            # the last light still on its way
            p = min(1.0, max(0.0, (lt - 1.0) / max(1.5, dur - 1.2))); xx_ = sx + 160 + (ex - 60 - sx - 160) * p
            d = ImageDraw.Draw(img); d.rectangle([max(sx + 160, xx_ - 900), y - 6, xx_, y + 6], fill=(255, 220, 140)) if gone > 0 else d.rectangle([sx + 160, y - 6, ex - 60, y + 6], fill=(255, 220, 140))
            planet(img, ex, y, 46)
            text(img, "YOU SEE THE SUN", 64, W / 2, 210, WHITE, u=ease(lt / 0.4)); text(img, "AS IT WAS 8 MINUTES AGO", 64, W / 2, 290, BRASS, u=ease((lt - 0.3) / 0.4))
            if gone > 0: pill(img, "STILL VISIBLE FOR 8 MINUTES", 40, W / 2, 800, fill=RED, ink=WHITE, u=gone)
    elif m == "moon":
        planet(img, 560, 540, 170); mx = 1360; d = ImageDraw.Draw(img)
        halo(img, mx, 540, 80, (200, 200, 210), 90); d = ImageDraw.Draw(img); d.ellipse([mx - 60, 480, mx + 60, 600], fill=(205, 205, 210)); d.ellipse([mx - 25, 505, mx, 530], fill=(170, 170, 178)); d.ellipse([mx + 10, 550, mx + 30, 570], fill=(175, 175, 182))
        p = min(1.0, max(0.0, (lt - 0.2) / 1.3)); xx_ = mx - 70 - (mx - 70 - 740) * p
        d.line([(mx - 70, 540), (xx_, 540)], fill=(255, 240, 200), width=5); halo(img, xx_, 540, 20, (255, 240, 200), 220)
        stopwatch(img, W / 2, 220, f"{1.3 * p:.1f} s", "MOONLIGHT'S TRIP", BRASS, size=130)
    else:   # andromeda
        d = ImageDraw.Draw(img); r = random.Random(4)
        for _ in range(400):
            x, y, s = r.uniform(0, W), r.uniform(0, H), r.choice([0.8, 1.2, 1.8]); c = int(r.uniform(90, 240) * (0.7 + 0.3 * math.sin(t * 2 + x)))
            d.ellipse([x - s, y - s, x + s, y + s], fill=(c, c, min(255, c + 20)))
        gx, gy = 1180, 470; gal = Image.new("RGBA", (900, 900), (0, 0, 0, 0)); gd = ImageDraw.Draw(gal)
        for k in range(30, 0, -1):
            q = k / 30; gd.ellipse([450 - 400 * q, 450 - 120 * q, 450 + 400 * q, 450 + 120 * q], fill=(int(140 + 110 * (1 - q)), int(150 + 90 * (1 - q)), int(200 + 40 * (1 - q)), int(30 + 160 * (1 - q) ** 2)))
        gal = gal.filter(ImageFilter.GaussianBlur(10)).rotate(28, resample=Image.BICUBIC); u = ease(lt / 1.0)
        a = np.asarray(gal).copy(); a[..., 3] = (a[..., 3] * u).astype(np.uint8); paste(img, Image.fromarray(a, "RGBA"), gx, gy)
        halo(img, gx, gy, 50, (255, 245, 220), int(220 * u))
        pill(img, "THE ANDROMEDA GALAXY", 44, 520, 260, fill=CYAN, ink=INKD, u=ease((lt - 0.5) / 0.4)); text(img, "a faint smudge on a dark night", 38, 520, 340, WHITE, w="SemiBold", u=ease((lt - 0.8) / 0.4))
    return img

# ---------------- beats: Venus ----------------
VTEX = None
def venus_sprite(r, rot, light=(-0.6, 0.3, 0.74)):
    global VTEX
    if VTEX is None:
        n = lowf(256, 512, 10, 31) * 0.6 + lowf(256, 512, 4, 32) * 0.4; band = 0.5 + 0.5 * np.sin(np.linspace(0, 18, 256))[:, None]
        v = n * 0.7 + band * 0.3; VTEX = np.dstack([215 + 40 * v, 170 + 50 * v, 90 + 40 * v]).astype(np.float32)
    R = int(r); Xg, Yg = np.meshgrid(np.arange(-R, R) + 0.5, np.arange(-R, R) + 0.5); x, y = Xg / r, -Yg / r; rho2 = x * x + y * y
    z = np.sqrt(np.clip(1 - rho2, 0, 1)); al = np.clip((1 - np.sqrt(rho2)) * r, 0, 1)
    lat = np.arcsin(np.clip(y, -1, 1)); lon = np.arctan2(x, z) + rot
    u = ((lon / (2 * np.pi)) * 512).astype(int) % 512; v = ((0.5 - lat / np.pi) * 255).astype(int)
    L = np.array(light); L = L / np.linalg.norm(L); lam = np.clip(x * L[0] + y * L[1] + z * L[2], 0, 1)
    rgb = VTEX[v, u] * (0.08 + 0.95 * lam ** 0.8)[..., None] + np.array([255, 200, 120]) * ((1 - z) ** 3 * 0.5)[..., None]
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), al * 255]).astype(np.uint8), "RGBA")
def b_venus(sc, lt, dur, t):
    img = space(t, gears=False); m = sc["mode"]; d = ImageDraw.Draw(img)
    if m == "spin":
        halo(img, 600, 540, 380, (255, 170, 80), 90); paste(img, venus_sprite(340, -lt * 0.15), 600, 540)
        d = ImageDraw.Draw(img); d.arc([600 - 400, 540 - 400, 600 + 400, 540 + 400], 215, 325, fill=BRASS, width=6)
        ax_, ay_ = 600 + 400 * math.cos(math.radians(215)), 540 + 400 * math.sin(math.radians(215)); d.polygon([(ax_ - 22, ay_ + 30), (ax_ - 14, ay_ - 16), (ax_ + 26, ay_ + 8)], fill=BRASS)
        v = 243 * eout((lt - 0.2) / 2.2); text(img, f"{int(v)}", 220, 1420, 420, BRASS); text(img, "EARTH DAYS", 60, 1420, 560, WHITE, w="Bold")
        pill(img, "TO SPIN AROUND ONCE", 40, 1420, 660, fill=CYAN, ink=INKD, u=ease((lt - 0.6) / 0.4))
    elif m == "orbit":
        sx, sy = 560, 540; sun(img, sx, sy, 90); d = ImageDraw.Draw(img); ax, ay = 420, 300
        d.ellipse([sx - ax, sy - ay, sx + ax, sy + ay], outline=(90, 90, 120), width=3)
        a = -1.2 + 2 * math.pi * eout((lt - 0.2) / max(2.0, dur - 0.6))
        for k in range(30):
            b = a - k * 0.03; d.ellipse([sx + ax * math.cos(b) - 4, sy + ay * math.sin(b) - 4, sx + ax * math.cos(b) + 4, sy + ay * math.sin(b) + 4], fill=lerpc(BRASS, INKD, k / 30))
        vx, vy = sx + ax * math.cos(a), sy + ay * math.sin(a); paste(img, venus_sprite(46, 0, light=((sx - vx) / 500, -(sy - vy) / 500, 0.4)), vx, vy)
        v = 225 * eout((lt - 0.2) / max(2.0, dur - 0.6)); text(img, f"{int(v)}", 220, 1420, 420, CYAN); text(img, "EARTH DAYS", 60, 1420, 560, WHITE, w="Bold")
        pill(img, "TO GO AROUND THE SUN", 40, 1420, 660, fill=BRASS, ink=INKD, u=ease((lt - 0.6) / 0.4))
    elif m == "cake":
        u = ease(lt / 0.4); d = ImageDraw.Draw(img)
        cx, cy = 600, 560; d.rounded_rectangle([cx - 230, cy - 230, cx + 230, cy + 230], 36, fill=(244, 236, 218)); d.rounded_rectangle([cx - 230, cy - 230, cx + 230, cy - 120], 36, fill=(170, 52, 40)); d.rectangle([cx - 230, cy - 150, cx + 230, cy - 120], fill=(170, 52, 40))
        d.text((cx, cy - 175), "VENUS · DAY 1", font=F(44, "Bold"), fill=WHITE, anchor="mm"); d.text((cx, cy + 50), "1", font=F(220, "Black"), fill=(40, 34, 40), anchor="mm")
        yr = 1 + int(eout((lt - 0.6) / 1.4) >= 0.999); text(img, f"YEAR {yr}", 150, 1400, 440, BRASS if yr == 2 else WHITE)
        text(img, "HAPPY BIRTHDAY!", 56, 1400, 560, WHITE, w="Bold", u=ease((lt - 1.9) / 0.4)); pill(img, "STILL THE SAME DAY", 42, 1400, 660, fill=CYAN, ink=INKD, u=ease((lt - 2.3) / 0.4))
    else:   # west: Sun rises in the west
        sky = np.repeat(np.linspace(0, 1, H, dtype=np.float32)[:, None, None], W, axis=1)
        a = np.array([70, 40, 20], np.float32) * (1 - sky) + np.array([210, 140, 60], np.float32) * sky
        img = Image.fromarray(a.astype(np.uint8)); d = ImageDraw.Draw(img)
        p = ease((lt - 0.3) / max(1.5, dur - 0.5)); sx, sy = 380, 820 - 360 * p
        halo(img, sx, sy, 160, (255, 230, 170), 200); d = ImageDraw.Draw(img); d.ellipse([sx - 60, sy - 60, sx + 60, sy + 60], fill=(255, 244, 210))
        pts = [(x, 820 + 30 * math.sin(x * 0.006) + 14 * math.sin(x * 0.02)) for x in range(0, W + 20, 20)]
        d.polygon(pts + [(W, H), (0, H)], fill=(96, 56, 30))
        text(img, "W", 90, 380, 940, WHITE); text(img, "E", 90, 1540, 940, DIM)
        text(img, "SUNRISE IN THE WEST", 90, W / 2, 200, WHITE, u=ease(lt / 0.4)); pill(img, "VENUS SPINS BACKWARDS", 40, W / 2, 310, fill=BRASS, ink=INKD, u=ease((lt - 0.4) / 0.4))
    return img

# ---------------- beats: Sweden's leap-day muddle ----------------
def b_leaps(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img); x0, x1 = 520, 1700
    rows = [("OLD CALENDAR", 300, CYAN, 0), ("NEW CALENDAR", 720, BRASS, 0), ("SWEDEN", 510, RED, 1)]
    for i, (lab, y, col, wob) in enumerate(rows):
        u = ease((lt - i * 0.5) / 0.4)
        if u <= 0: continue
        text(img, lab, 50, 470, y, col, w="Bold", anchor="rm", u=u)
        d = ImageDraw.Draw(img); xe = x0 + (x1 - x0) * eout((lt - i * 0.5) / 1.2)
        if wob:
            pts = [(x, y + 60 * math.sin((x - x0) * 0.008) * min(1, (x - x0) / 300)) for x in range(x0, int(xe), 8)]
            if len(pts) > 1: d.line(pts, fill=col, width=10)
        else: d.line([(x0, y), (xe, y)], fill=col, width=10)
        for k in range(8):
            x = x0 + k * 160
            if x < xe: d.ellipse([x - 12, (y if not wob else y + 60 * math.sin((x - x0) * 0.008) * min(1, (x - x0) / 300)) - 12, x + 12, (y if not wob else y + 60 * math.sin((x - x0) * 0.008) * min(1, (x - x0) / 300)) + 12], fill=WHITE)
    pill(img, "OUT OF STEP WITH EVERYONE", 44, W / 2, 900, fill=RED, ink=WHITE, u=ease((lt - 2.0) / 0.4))
    pill(img, "SKIP LEAP DAYS, ONE AT A TIME", 40, W / 2, 140, fill=(40, 44, 72), ink=WHITE, u=ease((lt - 0.2) / 0.4))
    return img

# ---------------- beats: the date line ----------------
def b_dateline(sc, lt, dur, t):
    img = space(t, gears=False); m = sc["mode"]
    sea = Image.new("RGB", (W, H), (10, 40, 80)); a = (lowf(H, W, 160, 41) * 30)[..., None] * np.array([0.3, 0.8, 1.0])
    img = Image.fromarray(np.clip(np.asarray(sea).astype(np.float32) + a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(img)
    lx = 1060
    # the date line (dashed, with a small zig)
    for y in range(80, H, 40):
        xo = lx + (0 if y < 420 or y > 760 else 60 * math.sin((y - 420) / 340 * math.pi))
        d.line([(xo, y), (xo, y + 22)], fill=WHITE, width=6)
    text(img, "INTERNATIONAL DATE LINE", 34, lx, 60, WHITE, w="Bold")
    text(img, "FRIDAY", 80, 520, 200, BRASS); text(img, "THURSDAY", 80, 1500, 200, CYAN)
    def island(x, y, s, col=(120, 170, 90)):
        d.polygon([(x - 50 * s, y), (x - 20 * s, y - 26 * s), (x + 30 * s, y - 20 * s), (x + 56 * s, y + 6 * s), (x + 10 * s, y + 22 * s), (x - 40 * s, y + 16 * s)], fill=col)
    island(330, 700, 3.2); text(img, "AUSTRALIA", 40, 330, 800, WHITE, w="Bold")
    island(760, 790, 1.4); text(img, "NEW ZEALAND", 36, 760, 860, WHITE, w="Bold")
    if m == "line":
        pill(img, "CROSS IT → THE DATE CHANGES", 40, W / 2, 330, fill=BRASS, ink=INKD, u=ease((lt - 0.6) / 0.4))
    else:
        if m == "jump":
            p = ease((lt - 1.2) / 1.4); sx = 1340 + (940 - 1340) * p
        else: p = 0; sx = 1340
        sy = 560 - 40 * math.sin(math.pi * p) if m == "jump" else 560
        island(sx, sy, 1.0, (150, 200, 110)); d = ImageDraw.Draw(img)
        halo(img, sx, sy, 50, BRASS, 120); d = ImageDraw.Draw(img); island(sx, sy, 1.0, (150, 200, 110))
        pill(img, "SAMOA", 40, sx, sy - 80, fill=BRASS if p > 0.5 else CYAN, ink=INKD)
        if m == "behind": pill(img, "ALMOST A DAY BEHIND", 40, 1500, 330, fill=RED, ink=WHITE, u=ease((lt - 0.5) / 0.4))
        else: pill(img, "2011: SAMOA SWITCHES SIDES", 40, W / 2, 330, fill=BRASS, ink=INKD, u=ease((lt - 0.4) / 0.4))
    text(img, "(map not to scale)", 28, 1700, 1010, (160, 190, 220), w="SemiBold")
    return img

# ---------------- beats: pyramid + mammoth ----------------
def pyramid(d, cx, base, w, h, layers_u=1.0, col=(220, 180, 110)):
    n = 14; k = int(n * layers_u + 0.999)
    for i in range(k):
        y0 = base - h * i / n; y1 = base - h * (i + 1) / n; w0 = w * (1 - i / n) / 2; w1 = w * (1 - (i + 1) / n) / 2
        c = lerpc(col, (255, 225, 160), i / n * 0.5)
        d.polygon([(cx - w0, y0), (cx + w0, y0), (cx + w1, y1), (cx - w1, y1)], fill=c)
        d.polygon([(cx, y0), (cx + w0, y0), (cx + w1, y1), (cx, y1)], fill=lerpc(c, (120, 90, 60), 0.35))
def mammoth(img, x, y, s=1.0, col=(120, 84, 60), t=0.0):
    d = ImageDraw.Draw(img); step = math.sin(t * 3) * 8 * s
    for lx, ph in ((-70, 0), (-30, 1), (40, 1), (80, 0)):
        o = step if ph else -step; d.rounded_rectangle([x + (lx - 16) * s + o * 0.3, y + 10 * s, x + (lx + 16) * s + o * 0.3, y + 120 * s], int(12 * s), fill=lerpc(col, (0, 0, 0), 0.15))
    d.ellipse([x - 130 * s, y - 90 * s, x + 110 * s, y + 60 * s], fill=col)               # body
    d.ellipse([x - 120 * s, y - 120 * s, x - 20 * s, y - 30 * s], fill=col)               # shoulder hump
    d.ellipse([x + 60 * s, y - 120 * s, x + 170 * s, y - 10 * s], fill=col)               # head
    d.line([(x + 150 * s, y - 40 * s), (x + 175 * s, y + 30 * s), (x + 160 * s, y + 90 * s)], fill=col, width=int(26 * s), joint="curve")   # trunk
    d.arc([x + 90 * s, y - 50 * s, x + 260 * s, y + 70 * s], 90, 200, fill=(244, 236, 218), width=int(12 * s))   # tusk
    d.ellipse([x + 118 * s, y - 92 * s, x + 132 * s, y - 78 * s], fill=(20, 16, 14))
    for k in range(9): hx = x - 110 * s + k * 26 * s; d.line([(hx, y + 40 * s), (hx - 6 * s, y + 66 * s)], fill=lerpc(col, (0, 0, 0), 0.3), width=int(6 * s))   # shaggy fringe
def b_pyramid(sc, lt, dur, t):
    m = sc["mode"]
    if m == "island":
        img = space(t, gears=False); d = ImageDraw.Draw(img); sea_y = 760
        d.rectangle([0, sea_y, W, H], fill=(14, 40, 70)); d.polygon([(200, sea_y), (420, 640), (900, 610), (1500, 650), (1760, sea_y)], fill=(210, 222, 230))
        d.polygon([(420, 640), (900, 610), (1500, 650), (1200, 680), (700, 690)], fill=(236, 242, 248))
        for k in range(60): x = (k * 97 + t * 40) % W; y = (k * 53 + t * 60) % H; d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(230, 236, 244))
        mammoth(img, 820 + 30 * math.sin(lt * 0.3), 520, 1.0, t=t)
        pill(img, "WRANGEL ISLAND · ARCTIC OCEAN", 42, W / 2, 160, fill=CYAN, ink=INKD, u=ease(lt / 0.4)); text(img, "UNTIL ≈ 4,000 YEARS AGO", 70, W / 2, 260, BRASS, u=ease((lt - 0.4) / 0.4))
        return img
    sky = np.repeat(np.linspace(0, 1, H, dtype=np.float32)[:, None, None], W, axis=1)
    a = np.array([60, 110, 190], np.float32) * (1 - sky) + np.array([240, 200, 150], np.float32) * sky
    img = Image.fromarray(a.astype(np.uint8)); d = ImageDraw.Draw(img)
    halo(img, 1580, 200, 110, (255, 240, 200), 200); d = ImageDraw.Draw(img); d.ellipse([1530, 150, 1630, 250], fill=(255, 248, 220))
    d.rectangle([0, 820, W, H], fill=(214, 176, 110))
    if m == "build":
        u = eout((lt - 0.2) / max(1.5, dur - 1.0)); pyramid(d, 960, 820, 1000, 520, u)
        text(img, "THE GREAT PYRAMID", 90, W / 2, 150, WHITE, u=ease(lt / 0.4)); pill(img, "FINISHED ≈ 4,500 YEARS AGO", 42, W / 2, 250, fill=INKD, ink=WHITE, u=ease((lt - 0.5) / 0.4))
    else:   # both
        pyramid(d, 560, 820, 760, 400)
        d.rectangle([1040, 0, W, H], fill=(36, 52, 74)); d.rectangle([1040, 820, W, H], fill=(220, 230, 238)); d.line([(1040, 0), (1040, H)], fill=WHITE, width=6)
        mammoth(img, 1440, 640, 0.95, t=t)
        text(img, "EGYPT", 52, 560, 880, INKD, w="Bold", shadow=False); text(img, "WRANGEL ISLAND", 52, 1480, 880, INKD, w="Bold", shadow=False)
        pill(img, "PYRAMID: ALREADY CENTURIES OLD", 40, 560, 160, fill=INKD, ink=WHITE, u=ease(lt / 0.4)); pill(img, "THE LAST MAMMOTHS", 40, 1480, 160, fill=CYAN, ink=INKD, u=ease((lt - 0.4) / 0.4))
    return img

# ---------------- beats: height clocks ----------------
def person(d, x, base, h, col=(200, 212, 235)):
    d.ellipse([x - h * 0.07, base - h, x + h * 0.07, base - h + h * 0.14], fill=col); d.rounded_rectangle([x - h * 0.11, base - h * 0.84, x + h * 0.11, base - h * 0.45], int(h * 0.06), fill=col)
    d.rectangle([x - h * 0.09, base - h * 0.47, x - h * 0.02, base], fill=col); d.rectangle([x + h * 0.02, base - h * 0.47, x + h * 0.09, base], fill=col)
def b_clocks(sc, lt, dur, t):
    img = space(t); m = sc["mode"]; d = ImageDraw.Draw(img)
    if m in ("lab", "raise"):
        d.rectangle([260, 860, 1660, 890], fill=(80, 84, 110))
        up = 0 if m == "lab" else 200 * ease((lt - 0.4) / 1.0)
        for i, (x, yb) in enumerate(((680, 860), (1240, 860 - up))):
            d = ImageDraw.Draw(img)
            if i == 1 and up > 0: d.rectangle([x - 120, yb, x + 120, 860], fill=(60, 64, 92))
            d.rounded_rectangle([x - 150, yb - 330, x + 150, yb], 24, fill=(30, 34, 60), outline=(120, 126, 160), width=4)
            clockface(img, x, yb - 170, 120, t * (1.0 if i == 0 or m == "lab" else 1.0 + 0.6 * ease((lt - 1.4) / 0.4)) * 6, speed=1, col=CYAN if i == 0 else BRASS)
            text(img, "ATOMIC CLOCK " + "AB"[i], 34, x, yb - 365, WHITE, w="Bold")
        if m == "lab": pill(img, "THE MOST PRECISE CLOCKS EVER BUILT", 44, W / 2, 180, fill=BRASS, ink=INKD, u=ease(lt / 0.4))
        else:
            d = ImageDraw.Draw(img)
            if up > 10:
                d.line([(1440, 860), (1440, 860 - up)], fill=BRASS, width=5); d.line([(1420, 860), (1460, 860)], fill=BRASS, width=5); d.line([(1420, 860 - up), (1460, 860 - up)], fill=BRASS, width=5)
                text(img, "33 CM", 52, 1550, 860 - up / 2, BRASS)
            pill(img, "HIGHER CLOCK TICKS FASTER", 44, W / 2, 180, fill=BRASS, ink=INKD, u=ease((lt - 1.4) / 0.4)); text(img, "(speed-up hugely exaggerated)", 30, W / 2, 250, DIM, w="SemiBold", u=ease((lt - 1.6) / 0.4))
    elif m == "body":
        base = 940; person(d, 760, base, 760)
        clockface(img, 1060, 260, 90, t * 9, speed=1, col=BRASS); clockface(img, 1060, 860, 90, t * 6, speed=1, col=CYAN)
        d = ImageDraw.Draw(img); d.line([(830, 250), (960, 260)], fill=BRASS, width=4); d.line([(830, 900), (960, 870)], fill=CYAN, width=4)
        text(img, "HEAD: AGES A TINY BIT FASTER", 54, 1180, 260, BRASS, anchor="lm", u=ease(lt / 0.4), maxw=700); text(img, "FEET: A TINY BIT SLOWER", 54, 1180, 860, CYAN, anchor="lm", u=ease((lt - 0.5) / 0.4), maxw=700)
    else:   # stairs
        d = ImageDraw.Draw(img); x0, y0 = 360, 920
        for k in range(8): d.rectangle([x0 + k * 140, y0 - (k + 1) * 70, x0 + (k + 1) * 140, y0], fill=(52, 56, 86)); d.line([(x0 + k * 140, y0 - (k + 1) * 70), (x0 + (k + 1) * 140, y0 - (k + 1) * 70)], fill=(120, 126, 160), width=4)
        p = ease((lt - 0.2) / max(1.5, dur - 0.6)); k = p * 7; px = x0 + 70 + k * 140; py = y0 - (int(k) + 1) * 70
        person(d, px, py, 210); clockface(img, px + 120, py - 190, 50, t * 6 * (1 + p), speed=1, col=BRASS)
        text(img, "HIGHER = FASTER CLOCK", 72, 620, 220, WHITE, u=ease(lt / 0.4), maxw=900); pill(img, "VERY, VERY SLIGHTLY", 40, 620, 320, fill=CYAN, ink=INKD, u=ease((lt - 0.5) / 0.4))
    return img

# ---------------- beats: GPS ----------------
def earth(img, x, y, r, t):
    halo(img, x, y, r * 1.12, (40, 110, 230), 120); d = ImageDraw.Draw(img); d.ellipse([x - r, y - r, x + r, y + r], fill=(22, 70, 150))
    rr = random.Random(9)
    for k in range(9):
        a = rr.uniform(0, 6.28) + t * 0.05; dd = rr.uniform(0, 0.7) * r; cx_, cy_ = x + dd * math.cos(a), y + dd * math.sin(a) * 0.8; s = rr.uniform(0.15, 0.32) * r
        if math.hypot(cx_ - x, cy_ - y) + s < r: d.ellipse([cx_ - s, cy_ - s * 0.7, cx_ + s, cy_ + s * 0.7], fill=(70, 140, 80))
    m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).ellipse([x - r, y - r, x + r, y + r], fill=110)
    sh = Image.new("L", (W, H), 0); ImageDraw.Draw(sh).ellipse([x - r * 0.6, y - r * 1.3, x + r * 1.6, y + r * 1.1], fill=255)
    from PIL import ImageChops
    img.paste((4, 8, 20), (0, 0), ImageChops.multiply(m, sh.filter(ImageFilter.GaussianBlur(r * 0.3))))
def sat(d, x, y, s=1.0):
    d.rectangle([x - 14 * s, y - 10 * s, x + 14 * s, y + 10 * s], fill=WHITE); d.rectangle([x - 56 * s, y - 7 * s, x - 18 * s, y + 7 * s], fill=CYAN); d.rectangle([x + 18 * s, y - 7 * s, x + 56 * s, y + 7 * s], fill=CYAN)
def b_gps(sc, lt, dur, t):
    img = space(t, gears=False); m = sc["mode"]
    if m == "orbit":
        cx, cy = 620, 560; earth(img, cx, cy, 200, t); d = ImageDraw.Draw(img)
        d.ellipse([cx - 440, cy - 440, cx + 440, cy + 440], outline=(80, 96, 140), width=3)
        for k in range(4):
            a = t * 0.25 + k * math.pi / 2; x, y = cx + 440 * math.cos(a), cy + 440 * math.sin(a); halo(img, x, y, 26, CYAN, 160); d = ImageDraw.Draw(img); sat(d, x, y)
        text(img, "≈ 20,000 KM UP", 96, 1420, 430, BRASS, u=ease(lt / 0.4), maxw=820); pill(img, "WEAKER GRAVITY UP THERE", 40, 1420, 550, fill=CYAN, ink=INKD, u=ease((lt - 0.5) / 0.4))
        text(img, "(not to scale)", 28, 620, 1030, DIM, w="SemiBold")
    elif m == "drift":
        clockface(img, 520, 520, 200, t * 6, speed=1, col=CYAN); clockface(img, 1400, 520, 200, t * 6.2, speed=1, col=BRASS)
        d = ImageDraw.Draw(img); sat(d, 1400, 250, 1.3)
        text(img, "ON THE GROUND", 46, 520, 790, CYAN, w="Bold"); text(img, "ON THE SATELLITE", 46, 1400, 790, BRASS, w="Bold")
        v = 38 * eout((lt - 0.3) / 1.5); text(img, f"+{int(v)} µs", 150, W / 2, 200, WHITE, u=ease(lt / 0.3)); text(img, "PER DAY  (µs = millionth of a second)", 34, W / 2, 300, DIM, w="SemiBold")
        pill(img, "+45 WEAKER GRAVITY   −7 HIGH SPEED", 36, W / 2, 900, fill=(40, 44, 72), ink=WHITE, u=ease((lt - 1.2) / 0.4))
    else:   # error: map drift
        img = Image.new("RGB", (W, H), (226, 230, 222)); d = ImageDraw.Draw(img)
        for k in range(0, W, 120): d.line([(k, 0), (k, H)], fill=(205, 210, 200), width=2)
        for k in range(0, H, 120): d.line([(0, k), (W, k)], fill=(205, 210, 200), width=2)
        for (a, b, c, e) in ((0, 380, W, 300), (700, 0, 820, H), (0, 820, W, 900), (1300, 0, 1200, H)): d.line([(a, b), (c, e)], fill=(250, 250, 250), width=26)
        d.polygon([(200, 500), (480, 470), (520, 700), (230, 720)], fill=(170, 210, 160)); d.ellipse([1400, 520, 1700, 760], fill=(150, 196, 226))
        def pin(x, y, col):
            d.ellipse([x - 30, y - 90, x + 30, y - 30], fill=col); d.polygon([(x - 26, y - 52), (x + 26, y - 52), (x, y)], fill=col); d.ellipse([x - 12, y - 72, x + 12, y - 48], fill=WHITE)
        p = eout((lt - 0.4) / max(1.5, dur - 1.0)); ex, ey = 760 + 900 * p, 600 - 280 * p
        d.line([(760, 600), (ex, ey)], fill=RED, width=6); pin(760, 600, (60, 120, 230)); pin(ex, ey, RED)
        text(img, "YOU", 40, 760, 640, (30, 40, 70), w="Bold", shadow=False); text(img, "YOUR MAP", 40, ex, ey + 40, RED, w="Bold", shadow=False)
        text(img, f"{10 * p:.1f} KM OFF", 120, W / 2, 160, RED, u=ease(lt / 0.3)); pill(img, "AFTER ONE DAY, UNCORRECTED", 40, W / 2, 260, fill=INKD, ink=WHITE, u=ease((lt - 0.4) / 0.4))
    return img

BEATS = dict(cold=b_cold, chapter=b_chapter, text=b_text, counter=b_counter, compare=b_compare, stamp=b_stamp, recap=b_recap, outro=b_outro,
             timeline=b_timeline, calendar=b_calendar, light=b_light, venus=b_venus, leaps=b_leaps, dateline=b_dateline, pyramid=b_pyramid,
             clocks=b_clocks, gps=b_gps)
NOBLOOM = ("pyramid", "dateline", "calendar", "gps")

# ---------------- narration & score (warm music box + soft ticking) ----------------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.42, tail=1.5)
n = len(voice); tt = np.arange(n) / SR; music = np.zeros(n, np.float32)
pads = [[110.0, 164.81, 220.0, 277.18], [98.0, 146.83, 196.0, 246.94], [87.31, 130.81, 174.61, 220.0], [82.41, 123.47, 164.81, 207.65]]
seg = 6.0
for i in range(int(total / seg) + 1):
    a, b = int(i * seg * SR), min(int((i + 1.4) * seg * SR), n)
    if a >= n: break
    lt = tt[a:b] - i * seg; env = np.clip(lt / 2.5, 0, 1) * np.clip((seg * 1.4 - lt) / 2.5, 0, 1)
    for f in pads[i % 4]: music[a:b] += (np.sin(2 * np.pi * f * lt) + 0.3 * np.sin(2 * np.pi * f * 1.004 * lt)) * env * 0.028
tick = tone(2600, 0.03, decay=200, harm=(1, 2)); tock = tone(1900, 0.03, decay=200, harm=(1, 2))
for k in range(int(total)): place(music, k + 0.0, tick if k % 2 == 0 else tock, 0.05)
for k in range(int(total * 0.5)):
    place(music, random.uniform(0, total), tone(random.choice([659.25, 880, 987.77, 1318.5, 1760.0]), 2.0, decay=2.2, harm=(1, 3)), 0.010)
hook_hit(music, 0.35)
for ln in spec["lines"]:
    if ln["scene"]["type"] == "chapter": place(music, ln["_s"], tone(55, 1.2, decay=3, harm=(1, 2)), 0.25); whoosh(music, ln["_s"], 0.18)
    if ln["scene"]["type"] == "stamp": place(music, ln["_s"] + 0.5 + 0.25 * len(ln["scene"]["lines"]), tone(70, 0.4, decay=14, harm=(1, 2, 3)), 0.35)
for ln in spec["lines"][1:]: whoosh(music, ln["_s"], 0.06)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.35)

cur_ch = 0
for ln in spec["lines"]:
    if ln["scene"]["type"] == "chapter": cur_ch = ln["scene"]["ch"]
    ln["_ch"] = cur_ch
NCH = max(ln["_ch"] for ln in spec["lines"])
def _ts(x): x = int(x); return f"{x // 60}:{x % 60:02d}"
_chap = ["0:00 Intro"] + [f"{_ts(ln['_s'])} {ln['scene']['ch']}. {ln['scene']['title'].title()}" for ln in spec["lines"] if ln["scene"]["type"] == "chapter"]
_rc = [ln["_s"] for ln in spec["lines"] if ln["scene"]["type"] == "recap"]
if _rc: _chap.append(f"{_ts(_rc[0])} Recap")
open(work + "_chapters.txt", "w").write("\n".join(_chap) + "\n")

groups = caption_groups(words, 6)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 46
    while d.textlength(" ".join(ws), font=F(size, "Bold")) > W - 400 and size > 30: size -= 2
    f = F(size, "Bold"); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 975
    d.rounded_rectangle([x - 28, y - 14, x + tw + 28, y + size + 18], 24, fill=INKD)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=BRASS if on else WHITE); x += d.textlength(w + " ", font=f)

def frame(t):
    ln = core.active_line(spec, t, lead=0.05) or spec["lines"][0]
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]; sc = ln["scene"]
    if t < 0.05: lt = 3.0                                                                       # frame 0 = full hook
    img = BEATS[sc["type"]](sc, lt, dur, t)
    if sc["type"] not in NOBLOOM: img = bloom(img, 0.4)
    d = ImageDraw.Draw(img)
    if ln["_ch"]: d.text((W - 60, 50), f"{ln['_ch']:02d} / {NCH:02d}", font=F(34, "Bold"), fill=BRASS, anchor="ra")
    d.rounded_rectangle([44, 40, 330, 92], 22, fill=INKD); d.text((62, 48), "SOUNDS FAKE  ?!", font=F(30, "Black"), fill=(230, 226, 214))
    caption(img, t)
    d.rectangle([0, H - 6, int(W * t / total), H], fill=BRASS)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","):
            Image.frombytes("RGB", (W, H), frame(float(tt_))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s")
        for ln in spec["lines"]: print(f"{ln['_s']:7.1f} {ln['scene']['type']:10s} {ln['scene'].get('mode', '')}")
    else:
        if os.environ.get("PART"):
            i_, n_ = map(int, os.environ["PART"].split("/")); N = int(total * FPS); a_, b_ = N * i_ // n_, N * (i_ + 1) // n_
            ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", f"{work}_part{i_}.mp4"], stdin=subprocess.PIPE)
            for fi in range(a_, b_): ff.stdin.write(frame(fi / FPS))
            ff.stdin.close(); ff.wait(); print("part done", i_); sys.exit(0)
        tmp = out_path[:-4] + ".part.mp4"
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                               "-i", "-", "-i", work + "_audio.wav", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p",
                               "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
        for fi in range(int(total * FPS)): ff.stdin.write(frame(fi / FPS))
        ff.stdin.close()
        if ff.wait() == 0: os.replace(tmp, out_path); print(f"done {total:.1f}s")
        else: raise SystemExit("ffmpeg failed")
