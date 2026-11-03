"""Day 34 — 1930s ASTRONOMICAL GLASS PLATE style (Pluto hasn't finished an orbit since discovery).
Negative star fields on grey-blue glass, handwritten plate labels, red grease-pencil circles, a blink-comparator flip,
an orbit drawn in ink on the plate, typewriter dates, dust and scratches. Frame 0 = full claim.
Usage: python3 engine/styles/day34_plates.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
def HAND(s, w=700):
    f = ImageFont.truetype(f"{FONTS}/Caveat.ttf", int(s)); f.set_variation_by_axes([w]); return f
_M = next((p for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf") if os.path.exists(p)), None)
FDI = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
TYPE = (lambda s: ImageFont.truetype(_M, int(s))) if _M else (lambda s: ImageFont.truetype(FDI + "InterDisplay-Bold.otf", int(s)))
GLASS, INKC, SEPIA, RED, DARK = (206, 213, 214), (24, 24, 30), (70, 46, 30), (196, 40, 36), (40, 44, 52)

r0 = random.Random(34)
STARS = [(r0.uniform(70, W - 70), r0.uniform(230, 1450), r0.choice([1.5, 2, 2.5, 3.5, 5])) for _ in range(420)]
def glass_base():
    a = np.full((H, W, 3), GLASS, np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    a *= (1 - 0.18 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2)[..., None]
    a += np.random.default_rng(2).normal(0, 4, (H, W, 1))
    img = Image.fromarray(a.clip(0, 255).astype(np.uint8)); d = ImageDraw.Draw(img)
    d.rectangle([40, 190, W - 40, 1500], outline=(150, 156, 160), width=6)                 # plate edge
    r = random.Random(7)
    for _ in range(60): x, y = r.uniform(0, W), r.uniform(0, H); d.line([(x, y), (x + r.uniform(-120, 120), y + r.uniform(-8, 8))], fill=(225, 230, 232), width=1)
    return img
BASE = glass_base()

def starfield(d, shift=(0, 0)):
    for (x, y, s) in STARS: d.ellipse([x + shift[0] - s, y + shift[1] - s, x + shift[0] + s, y + shift[1] + s], fill=INKC)

def label(d, txt, x, y, size=58, col=SEPIA, anchor="la"): d.text((x, y), txt, font=HAND(size), fill=col, anchor=anchor)
def typed(d, txt, x, y, size=44, col=DARK, anchor="la", n=None):
    s = txt if n is None else txt[:n]; d.text((x, y), s, font=TYPE(size), fill=col, anchor=anchor)
def circle(d, x, y, r, u=1.0, col=RED):
    if u <= 0: return
    pts = [(x + r * math.cos(a) * (1 + 0.06 * math.sin(a * 3)), y + r * math.sin(a) * (1 + 0.06 * math.cos(a * 2))) for a in np.linspace(-1.2, -1.2 + 2 * math.pi * 1.08 * u, 60)]
    d.line(pts, fill=col, width=7, joint="curve")
def title(d, l1, l2, y=60):
    d.rectangle([0, 0, W, 185], fill=(236, 230, 214)); d.line([(0, 185), (W, 185)], fill=SEPIA, width=3)
    def fit(t, s):
        while d.textlength(t, font=HAND(s)) > W - 80 and s > 40: s -= 4
        return s
    d.text((W / 2, 52), l1, font=HAND(fit(l1, 76)), fill=INKC, anchor="mm"); d.text((W / 2, 132), l2, font=HAND(fit(l2, 86)), fill=RED, anchor="mm")

PL = (640, 760)                     # where 'Pluto' sits on the plate
def sc_hook(sc, lt, dur, t):
    img = BASE.copy(); d = ImageDraw.Draw(img); starfield(d)
    d.ellipse([PL[0] - 7, PL[1] - 7, PL[0] + 7, PL[1] + 7], fill=INKC); circle(d, *PL, 60, 1.0)
    label(d, "Pluto!", PL[0] + 75, PL[1] - 40, 74, RED)
    title(d, sc.get("l1", "SINCE 1930, PLUTO HASN'T"), sc.get("l2", "FINISHED A SINGLE LAP"))
    if sc.get("loop"):
        d.rectangle([150, 1300, W - 150, 1420], fill=(236, 230, 214), outline=SEPIA, width=4); label(d, sc.get("label", "the end date is wild..."), W / 2, 1360, 70, RED, "mm")
    typed(d, "PLATE 1930-01-23  LOWELL OBS.", 70, 1460, 34)
    return img

def sc_blink(sc, lt, dur, t):
    img = BASE.copy(); d = ImageDraw.Draw(img); starfield(d)
    second = int(lt * 2.5) % 2 == 1; px = PL[0] + (36 if second else 0)
    d.ellipse([px - 7, PL[1] - 7, px + 7, PL[1] + 7], fill=INKC)
    typed(d, "JAN 29, 1930" if second else "JAN 23, 1930", 70, 230, 48, RED if second else DARK)
    if lt > 1.2: circle(d, PL[0] + 18, PL[1], 80, ease((lt - 1.2) / 0.6)); label(d, "it moved!", PL[0] + 120, PL[1] + 40, 72, RED)
    d.rectangle([0, 0, W, 185], fill=(236, 230, 214)); d.text((W / 2, 95), "BLINK COMPARATOR", font=TYPE(64), fill=INKC, anchor="mm")
    return img

def sc_orbit(sc, lt, dur, t):
    img = BASE.copy(); d = ImageDraw.Draw(img); starfield(d)
    cx, cy, a, b = W / 2, 850, 420, 330
    d.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=(250, 250, 250), outline=INKC, width=3); label(d, "Sun", cx + 22, cy + 6, 46, SEPIA)
    pts = [(cx - 80 + a * math.cos(q), cy + b * math.sin(q)) for q in np.linspace(0, 2 * math.pi, 200)]
    for k in range(0, 200, 4): d.line(pts[k:k + 3], fill=SEPIA, width=4)
    frac = sc.get("frac", 0.0) + (sc.get("to", 0.0) - sc.get("frac", 0.0)) * ease((lt - 0.3) / max(0.6, dur - 0.8))
    k = int(200 * frac)
    if k > 1: d.line(pts[:k + 1], fill=RED, width=10)
    px, py = pts[min(k, 199)]; d.ellipse([px - 14, py - 14, px + 14, py + 14], fill=INKC)
    label(d, "1930", pts[0][0] + 20, pts[0][1] - 30, 54, RED)
    yr = 1930 + int(248 * frac); typed(d, f"YEAR {yr}", W / 2, 1360, 64, INKC, "mm")
    d.rectangle([0, 0, W, 185], fill=(236, 230, 214)); d.text((W / 2, 95), sc.get("head", "ONE LAP = ~248 YEARS"), font=TYPE(60), fill=INKC, anchor="mm")
    if sc.get("stamp") and lt > 1.0:
        d.rectangle([140, 1410, W - 140, 1500], fill=(236, 230, 214), outline=RED, width=5); typed(d, sc["stamp"], W / 2, 1455, 52, RED, "mm")
    return img

def sc_date(sc, lt, dur, t):
    img = BASE.copy(); d = ImageDraw.Draw(img); starfield(d)
    d.rectangle([110, 520, W - 110, 1180], fill=(240, 236, 224), outline=SEPIA, width=6)
    s = "MARCH 23, 2178"; n = int(len(s) * ease((lt - 0.2) / 1.0))
    typed(d, "FIRST FULL LAP SINCE DISCOVERY:", W / 2, 640, 40, DARK, "mm"); typed(d, s, W / 2, 820, 96, RED, "mm", n)
    if lt > 1.5: label(d, "152 years from now", W / 2, 1010, 74, SEPIA, "mm")
    d.rectangle([0, 0, W, 185], fill=(236, 230, 214)); d.text((W / 2, 95), "MARK YOUR CALENDAR", font=TYPE(60), fill=INKC, anchor="mm")
    return img

def sc_named(sc, lt, dur, t):
    img = BASE.copy(); d = ImageDraw.Draw(img); starfield(d)
    d.rectangle([110, 560, W - 110, 1120], fill=(240, 236, 224), outline=SEPIA, width=6)
    label(d, "Name suggested by:", W / 2, 680, 70, SEPIA, "mm"); label(d, "an 11-year-old girl", W / 2, 860, 104, RED, "mm")
    circle(d, W / 2, 860, 330, ease((lt - 0.6) / 0.8))
    return img

def sc_end(sc, lt, dur, t):
    img = BASE.copy(); d = ImageDraw.Draw(img); starfield(d)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.2); cx, cy, w_, h_ = W / 2, 980, 330, 150
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=RED if on > 0.5 else (170, 176, 180), outline=INKC, width=6)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; d.ellipse([kx - h_ / 2 + 18, cy - h_ / 2 + 18, kx + h_ / 2 - 18, cy + h_ / 2 - 18], fill=(240, 236, 224), outline=INKC, width=4)
    typed(d, "FAKE", cx - w_ / 2 - 40, cy, 60, INKC if on < 0.5 else (140, 140, 140), "rm"); typed(d, "TRUE", cx + w_ / 2 + 40, cy, 60, RED if on >= 0.5 else (140, 140, 140), "lm")
    title(d, "SOUNDS FAKE ?!", "...but it's true")
    return img

SCENES = dict(hook=sc_hook, blink=sc_blink, orbit=sc_orbit, date=sc_date, named=sc_named, end=sc_end)

voice, words, total = narrate(spec, lead=0.08, default_gap=0.22, tail=0.6)
n = len(voice); tt = np.arange(n) / SR; music = np.zeros(n, np.float32)
for k in range(int(total / 0.6)):                              # music-box melody + old-record crackle
    place(music, k * 0.6, tone([659.25, 783.99, 880.0, 783.99, 659.25, 587.33, 523.25, 587.33][k % 8], 0.9, decay=5, harm=(1, 3, 5)), 0.05)
crackle = np.zeros(n, np.float32); rr = np.random.default_rng(5); idx = rr.integers(0, n, int(total * 25)); crackle[idx] = rr.normal(0, 1, len(idx))
music += crackle * 0.08 + rr.normal(0, 1, n).astype(np.float32) * 0.003
hook_hit(music, 0.35)
for s_ in scene_starts(spec): whoosh(music, s_, 0.12)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.3)

groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 76
    while d.textlength(" ".join(ws), font=HAND(size)) > W - 180 and size > 40: size -= 4
    f = HAND(size); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1600
    d.rectangle([x - 30, y - 6, x + tw + 30, y + size + 22], fill=(240, 236, 224), outline=SEPIA, width=4)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=RED if on else INKC); x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t)
    if random.Random(int(t * 12)).random() < 0.25:                # film dust
        d = ImageDraw.Draw(img); r = random.Random(int(t * 12) + 1)
        for _ in range(4): x, y = r.uniform(0, W), r.uniform(0, H); d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(90, 90, 90))
    caption(img, t); ImageDraw.Draw(img).rectangle([0, H - 10, int(W * t / total), H], fill=RED)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
