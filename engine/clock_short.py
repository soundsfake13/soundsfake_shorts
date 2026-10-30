"""ONE-DAY CLOCK style (after 'Human inventions unfold on a one-day clock toward midnight' on claudevideo.org).
Minimal data-viz on warm off-white: a 24-hour dial that squeezes a span of history into one day,
sweeping hand, rolling year counter, line icons, bold editorial type. Best for 'surprising time gap' facts.
Usage: python3 clock_short.py spec.json out.mp4 [t1,t2,... preview]
Spec top level: "span": [start_year, end_year] (negative = BC); clock scenes use "events": [[year, label, icon]].
"""
import json, math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
def FT(s, w="Black"): return ImageFont.truetype(f"{FD}InterDisplay-{w}.otf", s)
_MONO = next((p for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
              "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf") if os.path.exists(p)), None)
MONO = (lambda s: ImageFont.truetype(_MONO, s)) if _MONO else (lambda s: FT(s, "Bold"))
PAPER, INK, RED, GREY, LINE, BLUE = (244, 242, 236), (20, 20, 22), (229, 72, 46), (140, 138, 132), (214, 210, 200), (47, 91, 234)
Y0, Y1 = spec["span"]
SPAN = (Y1 - Y0) - (1 if Y0 < 0 < Y1 else 0)       # no year zero
def hours_of(year): return 24 * ((year - Y0) - (1 if Y0 < 0 < year else 0)) / SPAN
def year_at(h):
    y = Y0 + h / 24 * SPAN
    if Y0 < 0 and y >= 0 and not abs(Y0) >= 100000: y += 1
    return int(round(y))
DEEP = abs(Y0) >= 100000          # deep time: show "X MILLION YEARS AGO" instead of BC/AD
def fmt(y):
    if DEEP:
        ago = Y1 - y
        if ago < 1e6: return "TODAY" if ago < 1000 else f"{ago / 1e3:,.0f} THOUSAND YRS AGO"
        return f"{ago / 1e6:,.0f} MILLION YRS AGO"
    return f"{-y:,} BC" if y < 0 else f"{y} AD"

BG = Image.new("RGB", (W, H), PAPER); d = ImageDraw.Draw(BG)
for x in range(30, W, 40):
    for y in range(30, H, 40): d.point((x, y), fill=LINE)

# ---------------- narration & music: sparse piano + clock tick ----------------
voice, words, total = narrate(spec, default_gap=0.3)
n = len(voice); music = np.zeros(n, np.float32)
notes = [261.63, 311.13, 392.0, 466.16, 392.0, 311.13, 349.23, 415.30]
for k in range(int(total / 0.75)):
    place(music, k * 0.75, tone(notes[k % 8] * (0.5 if k % 4 == 0 else 1), 1.4, decay=3.5, harm=(1, 2, 3, 5)), 0.06)
tick = np.random.default_rng(1).normal(0, 1, int(0.012 * SR)) * np.exp(-np.arange(int(0.012 * SR)) / SR * 400)
for k in range(int(total * 2)): place(music, k * 0.5, tick, 0.05 if k % 2 == 0 else 0.03)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.3)

# ---------------- drawing helpers ----------------
CX, CY, R = W / 2, 930, 360
def ang(h): return math.radians(h / 24 * 360 - 90)
def pt(h, r): a = ang(h); return CX + r * math.cos(a), CY + r * math.sin(a)

def icon(d, kind, x, y, s, col):
    if kind == "pyramid":
        d.polygon([(x - s, y + s * 0.7), (x + s, y + s * 0.7), (x, y - s * 0.8)], outline=col, width=6)
        d.line([(x, y - s * 0.8), (x + s * 0.25, y + s * 0.7)], fill=col, width=4)
    elif kind == "crown":
        d.line([(x - s, y + s * 0.5), (x - s, y - s * 0.4), (x - s * 0.5, y + s * 0.05), (x, y - s * 0.7), (x + s * 0.5, y + s * 0.05),
                (x + s, y - s * 0.4), (x + s, y + s * 0.5), (x - s, y + s * 0.5)], fill=col, width=6, joint="curve")
    elif kind == "moon":
        d.ellipse([x - s, y - s, x + s, y + s], outline=col, width=6)
        d.arc([x - s * 0.55, y - s * 0.9, x + s * 1.25, y + s * 0.9], 100, 260, fill=col, width=6)
    elif kind == "rocket":
        d.polygon([(x, y - s), (x + s * 0.4, y + s * 0.3), (x - s * 0.4, y + s * 0.3)], outline=col, width=6)
        d.line([(x - s * 0.4, y + s * 0.3), (x - s * 0.7, y + s * 0.8)], fill=col, width=6)
        d.line([(x + s * 0.4, y + s * 0.3), (x + s * 0.7, y + s * 0.8)], fill=col, width=6)

def dial(d, a=1.0):
    d.ellipse([CX - R, CY - R, CX + R, CY + R], outline=INK, width=6)
    for h in range(24):
        r0 = R - (34 if h % 6 == 0 else 18)
        d.line([pt(h, r0), pt(h, R - 4)], fill=INK if h % 6 == 0 else GREY, width=6 if h % 6 == 0 else 3)
    for h in (0, 6, 12, 18):
        x, y = pt(h, R - 78); d.text((x, y), f"{h:02d}", font=MONO(30), fill=GREY, anchor="mm")

def callout(d, h, label, sub, kind, col, u):
    if u <= 0: return
    x, y = pt(h % 24, R); rr = 16 * min(1, u * 1.5)
    d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col)
    if u < 0.35: return
    a = ang(h % 24); c, s_ = math.cos(a), math.sin(a)
    if abs(c) < 0.3:
        side = -1 if h < 12 else 1; lx, ly = x + side * 40, y + (-120 if s_ < 0 else 120)
    else:
        side = 1 if c > 0 else -1; lx, ly = x + side * 70, y
    d.line([(x, y), (lx, ly)], fill=col, width=3)
    icon(d, kind, lx + side * 42, ly - 4, 26, col)
    tx = lx + side * 86; anc = "ls" if side > 0 else "rs"
    d.text((tx, ly - 4), label, font=FT(42), fill=col, anchor=anc)
    d.text((tx, ly + 38), sub, font=MONO(30), fill=INK, anchor=anc)

def headline(img, lines, lt, accent, y0=520, size=118, left=80):
    d = ImageDraw.Draw(img)
    for i, txt in enumerate(lines):
        u = eout((lt - 0.1 - i * 0.22) / 0.4)
        if u <= 0: continue
        sz = size
        while d.textlength(txt, font=FT(sz)) > W - 2 * left and sz > 50: sz -= 6
        y = y0 + i * size * 1.08 + (1 - u) * 50
        col = RED if accent and str(i) in accent else INK
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(layer).text((left, y), txt, font=FT(sz), fill=col + (int(255 * u),))
        img.alpha_composite(layer)

# ---------------- scenes ----------------
def sc_headline(sc, lt, dur, t):
    img = BG.copy().convert("RGBA")
    headline(img, sc["lines"], lt, sc.get("accent"), y0=sc.get("y", 520), size=sc.get("size", 118))
    return img

def sc_clock(sc, lt, dur, t):
    img = BG.copy().convert("RGBA"); d = ImageDraw.Draw(img)
    ev = sc["events"]; frm, to = sc.get("from", 0), sc.get("to", 0)
    h0 = hours_of(ev[frm][0]); h1 = hours_of(ev[to][0])
    p = ease((lt - 0.4) / max(0.6, sc.get("sweep", dur - 1.0)))
    h = h0 + (h1 - h0) * p
    dial(d)
    # filled arcs between consecutive events up to the hand
    for k in range(len(ev) - 1):
        a0 = hours_of(ev[k][0]); a1 = min(hours_of(ev[k + 1][0]), h)
        if a1 > a0:
            col = [RED, BLUE, GREY][k % 3]
            d.arc([CX - R + 26, CY - R + 26, CX + R - 26, CY + R - 26], a0 / 24 * 360 - 90, a1 / 24 * 360 - 90, fill=col, width=26)
    for k, (yr, label, kind) in enumerate(ev):
        if hours_of(yr) <= h + 1e-6 or k <= frm:
            u = ease((lt - (0.2 if k <= frm else 0.0)) / 0.4) if k <= frm else ease((h - hours_of(yr) + 0.4) / 0.4)
            col = sc.get("event_colors", [INK, RED, BLUE])[k % 3]
            callout(d, hours_of(yr), label, fmt(yr), kind, col, u)
    hx, hy = pt(h % 24, R - 60)
    d.line([(CX, CY), (hx, hy)], fill=RED, width=10); d.ellipse([CX - 18, CY - 18, CX + 18, CY + 18], fill=RED)
    yr = year_at(h); hh = int(h) % 24 if h < 24 else 24; mm = int((h % 1) * 60) if h < 24 else 0
    ys = 64
    while d.textlength(fmt(yr), font=FT(ys)) > R * 1.3 and ys > 30: ys -= 4
    tw = d.textlength(fmt(yr), font=FT(ys))
    d.rounded_rectangle([CX - tw / 2 - 24, CY + 78, CX + tw / 2 + 24, CY + 210], 18, fill=PAPER, outline=LINE, width=3)
    d.text((CX, CY + 122), fmt(yr), font=FT(ys), fill=INK, anchor="mm")
    d.text((CX, CY + 180), f"{hh:02d}:{mm:02d}", font=MONO(34), fill=GREY, anchor="mm")
    if "note" in sc and lt > sc.get("note_at", 1.2):
        u = eout((lt - sc.get("note_at", 1.2)) / 0.35)
        f = FT(64); tw = d.textlength(sc["note"], font=f)
        box = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(box)
        bd.rectangle([CX - tw / 2 - 28, 1450 - 46, CX + tw / 2 + 28, 1450 + 46], fill=RED if to == 1 else BLUE)
        bd.text((CX, 1450), sc["note"], font=f, fill=PAPER, anchor="mm")
        box.putalpha(box.getchannel("A").point(lambda v: int(v * u))); img.alpha_composite(box)
    if sc.get("title"):
        d.text((80, 200), sc["title"], font=FT(54), fill=INK)
    return img

def sc_end(sc, lt, dur, t):
    img = BG.copy().convert("RGBA"); d = ImageDraw.Draw(img)
    click = sc.get("click_at", 0.9); on = ease((lt - click) / 0.25)
    cx, cy, w_, h_ = W / 2, 960, 330, 150
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=RED if on > 0.5 else LINE, outline=INK, width=6)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on
    d.ellipse([kx - h_ / 2 + 16, cy - h_ / 2 + 16, kx + h_ / 2 - 16, cy + h_ / 2 - 16], fill=PAPER, outline=INK, width=6)
    d.text((cx - w_ / 2 - 40, cy), "FAKE", font=FT(66), fill=INK if on < 0.5 else GREY, anchor="rm")
    d.text((cx + w_ / 2 + 40, cy), "TRUE", font=FT(66), fill=RED if on >= 0.5 else GREY, anchor="lm")
    if lt > click + 0.3:
        headline(img, ["SOUNDS", "FAKE ?!"], lt - click - 0.3, {"1": True}, y0=420, size=130)
    return img

SCENES = dict(headline=sc_headline, clock=sc_clock, end=sc_end)

# ---------------- captions ----------------
groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 66
    while d.textlength(" ".join(ws), font=FT(size, "Bold")) > W - 160 and size > 40: size -= 4
    f = FT(size, "Bold"); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2
    d.rectangle([x - 26, 1600, x + tw + 26, 1600 + size + 40], fill=INK)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, 1618), w, font=f, fill=(255, 120, 95) if on else PAPER)
        x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t)
    if ln is None: img = BG.copy().convert("RGBA")
    else:
        lt = t - ln["_s"]; dur = ln["_se"] - ln["_s"]
        img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t)
    caption(img, t)
    ImageDraw.Draw(img).rectangle([0, H - 10, int(W * t / total), H], fill=RED)
    return img.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","):
            Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path)
        print(f"done {total:.1f}s")
