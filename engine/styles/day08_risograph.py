"""Day 08 — RISOGRAPH style (bananas are berries, strawberries aren't).
Retro 2-3 spot-colour riso print: fluoro pink, blue and yellow inks that multiply on cream paper, halftone-dot
shading, slight mis-registration between ink layers, rubber stamps. Frame 0 = the full claim.
Usage: python3 engine/styles/day08_risograph.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
F = lambda s, w="Black": ImageFont.truetype(f"{FD}InterDisplay-{w}.otf", int(s))
PINK, BLUE, YEL = np.array([255, 72, 140], np.float32), np.array([0, 120, 191], np.float32), np.array([255, 226, 0], np.float32)
PAPER = (np.full((H, W, 3), [245, 238, 222], np.float32) + np.random.default_rng(8).normal(0, 5, (H, W, 1))).clip(0, 255)
REG = {"pink": (5, -3), "blue": (-4, 3), "yellow": (2, 4)}          # mis-registration per ink
INK = {"pink": PINK, "blue": BLUE, "yellow": YEL}

class Plate:
    """One ink layer drawn as an L mask; composed with multiply."""
    def __init__(self): self.m = Image.new("L", (W, H), 0); self.d = ImageDraw.Draw(self.m)

def halftone(plate, shade, cell=16, maxr=8.5, angle=0.3):
    """shade: L image 0..255 → halftone dots onto plate."""
    a = np.asarray(shade.resize((W // cell + 1, H // cell + 1), Image.BILINEAR)).astype(np.float32) / 255
    for j in range(a.shape[0]):
        for i in range(a.shape[1]):
            v = a[j, i]
            if v > 0.04:
                x = i * cell + (j % 2) * cell / 2; y = j * cell; r = maxr * math.sqrt(v)
                plate.d.ellipse([x - r, y - r, x + r, y + r], fill=255)

def compose(plates, t):
    out = PAPER.copy()
    jit = int(t * 8) % 2                                             # tiny print-jitter
    for name, p in plates.items():
        dx, dy = REG[name]; m = np.asarray(p.m.transform(p.m.size, Image.AFFINE, (1, 0, -dx - jit, 0, 1, -dy), resample=Image.NEAREST)).astype(np.float32) / 255
        m = m * 0.92
        out *= 1 - m[..., None] * (1 - INK[name] / 255)
    return out

def txt(plate, s, size, x, y, anchor="mm", w="Black", maxw=W - 120):
    while plate.d.textlength(s, font=F(size, w)) > maxw and size > 30: size -= 4
    plate.d.text((x, y), s, font=F(size, w), fill=255, anchor=anchor)

# ---------- motifs (draw into plates) ----------
def banana(P, cx, cy, s=1.0, rot=0.0):
    m = Image.new("L", (W, H), 0); d = ImageDraw.Draw(m)
    d.ellipse([cx - 320 * s, cy - 300 * s, cx + 320 * s, cy + 140 * s], fill=255)
    d.ellipse([cx - 360 * s, cy - 420 * s, cx + 360 * s, cy + 40 * s], fill=0)          # bite out the top -> crescent
    d.rectangle([0, 0, W, cy - 150 * s], fill=0)
    m = m.rotate(math.degrees(rot) - 8, center=(cx, cy), resample=Image.BICUBIC)
    P["yellow"].m.paste(255, (0, 0), m)
    sh = Image.new("L", (W, H), 0); sh.paste(150, (0, 0), m.crop((0, 0, W, H)).point(lambda v: v))
    shade = Image.new("L", (W, H), 0); ImageDraw.Draw(shade).rectangle([0, cy + 40 * s, W, H], fill=255)
    sh = Image.composite(sh, Image.new("L", (W, H), 0), shade); halftone(P["pink"], sh, 14, 5)
    edge = m.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 60 else 0).filter(ImageFilter.MaxFilter(7))
    P["blue"].m.paste(255, (0, 0), edge)

def strawberry(P, cx, cy, s=1.0, glow=0.0):
    prof = []
    for u in np.linspace(0, 1, 40):
        wdt = 190 * math.sqrt(max(0.0, 1 - ((u - 0.32) / 0.68) ** 2 if u > 0.32 else 1 - ((0.32 - u) / 0.45) ** 2)) * (1 - 0.55 * max(0, u - 0.32))
        prof.append((cx + s * wdt, cy - s * 120 + s * 320 * u))
    body = [(cx - (x - cx), y) for x, y in reversed(prof)] + prof
    P["pink"].d.polygon(body, fill=255)
    sh = Image.new("L", (W, H), 0); ImageDraw.Draw(sh).ellipse([cx, cy - 80 * s, cx + 160 * s, cy + 160 * s], fill=140); halftone(P["blue"], sh, 14, 4.5)
    r = random.Random(3)
    for k in range(34):
        a = r.uniform(0.15, 0.95); y = cy - s * 100 + s * 280 * a; half = s * 160 * math.sin(a * math.pi) * (1 - 0.35 * a) * 0.85
        x = cx + r.uniform(-half, half); rr = s * (6 + 6 * glow * (0.5 + 0.5 * math.sin(k)))
        P["yellow"].d.ellipse([x - rr, y - rr * 1.4, x + rr, y + rr * 1.4], fill=255)
    for k in range(5):
        a = -math.pi / 2 + (k - 2) * 0.55
        P["blue"].d.polygon([(cx, cy - s * 120), (cx + s * 110 * math.cos(a - 0.2), cy - s * 120 + s * 60 * math.sin(a - 0.2) - 30 * s), (cx + s * 120 * math.cos(a), cy - s * 125 + s * 70 * math.sin(a) - 30 * s)], fill=255)

def stamp(P, ink, s, cx, cy, rot=-12, size=70, u=1.0):
    if u <= 0: return
    f = F(size * (2 - u)); tmp = Image.new("L", (W, H), 0); td = ImageDraw.Draw(tmp)
    tw = td.textlength(s, font=f); td.rounded_rectangle([cx - tw / 2 - 30, cy - size * 0.9, cx + tw / 2 + 30, cy + size * 0.9], 20, outline=255, width=10)
    td.text((cx, cy), s, font=f, fill=255, anchor="mm")
    tmp = tmp.rotate(rot, center=(cx, cy), resample=Image.BICUBIC)
    P[ink].m.paste(255, (0, 0), tmp)

def fruit_icon(P, kind, cx, cy, s=1.0):
    if kind == "tomato":
        P["pink"].d.ellipse([cx - 80 * s, cy - 70 * s, cx + 80 * s, cy + 70 * s], fill=255); P["blue"].d.polygon([(cx - 30 * s, cy - 70 * s), (cx, cy - 40 * s), (cx + 30 * s, cy - 70 * s), (cx, cy - 90 * s)], fill=255)
    elif kind == "grapes":
        for k, (dx, dy) in enumerate([(-40, -40), (0, -40), (40, -40), (-20, 0), (20, 0), (0, 40)]): P["blue"].d.ellipse([cx + dx * s - 26 * s, cy + dy * s - 26 * s, cx + dx * s + 26 * s, cy + dy * s + 26 * s], fill=255)
        P["pink"].d.ellipse([cx - 60 * s, cy - 60 * s, cx + 60 * s, cy + 70 * s], fill=110)
    elif kind == "eggplant":
        P["blue"].d.ellipse([cx - 55 * s, cy - 40 * s, cx + 55 * s, cy + 90 * s], fill=255); P["pink"].d.ellipse([cx - 55 * s, cy - 40 * s, cx + 55 * s, cy + 90 * s], fill=255)
        P["yellow"].d.polygon([(cx - 30 * s, cy - 40 * s), (cx, cy - 90 * s), (cx + 30 * s, cy - 40 * s)], fill=255)
    elif kind == "watermelon":
        P["pink"].d.pieslice([cx - 100 * s, cy - 100 * s, cx + 100 * s, cy + 100 * s], 0, 180, fill=255)
        P["blue"].d.arc([cx - 100 * s, cy - 100 * s, cx + 100 * s, cy + 100 * s], 0, 180, fill=255, width=int(16 * s))
        for k in range(5): x = cx - 50 * s + k * 25 * s; P["blue"].d.ellipse([x - 5, cy + 30 * s - 5, x + 5, cy + 30 * s + 5], fill=255)
    elif kind == "pumpkin":
        for dx in (-45, 0, 45): P["yellow"].d.ellipse([cx + dx * s - 50 * s, cy - 60 * s, cx + dx * s + 50 * s, cy + 60 * s], fill=255)
        P["pink"].d.ellipse([cx - 95 * s, cy - 60 * s, cx + 95 * s, cy + 60 * s], fill=120); P["blue"].d.rectangle([cx - 8 * s, cy - 90 * s, cx + 8 * s, cy - 55 * s], fill=255)

# ---------- narration & music ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
music = np.zeros(len(voice), np.float32)
for k in range(int(total / 0.3)):                                      # bouncy lo-fi pluck + clap
    place(music, k * 0.3, tone([392, 440, 523.25, 440, 349.23, 392, 440, 392][k % 8] * (0.5 if k % 2 else 1), 0.35, decay=12, harm=(1, 2, 3)), 0.05)
    if k % 4 == 2: place(music, k * 0.3, np.random.default_rng(k).normal(0, 1, int(0.06 * SR)) * np.exp(-np.arange(int(0.06 * SR)) / SR * 70), 0.05)
hook_hit(music, 0.4)
for s_ in scene_starts(spec): whoosh(music, s_, 0.14)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.3)

# ---------- scenes ----------
def plates(): return {"yellow": Plate(), "pink": Plate(), "blue": Plate()}
def sc_hook(sc, lt, dur, t):
    P = plates(); banana(P, 330, 900, 0.95, rot=0.05 * math.sin(t * 2)); strawberry(P, 800, 860, 0.85)
    txt(P["blue"], "BANANA = BERRY", 104, W / 2, 330); txt(P["pink"], "STRAWBERRY = NOT", 96, W / 2, 470)
    if sc.get("loop"): stamp(P, "pink", "WAIT FOR THE LIST", W / 2, 1330, rot=-8, size=60, u=back(lt / 0.3))
    return P
def sc_rule(sc, lt, dur, t):
    P = plates(); cx, cy = W / 2, 860
    P["pink"].d.ellipse([cx - 230, cy - 230, cx + 230, cy + 230], fill=255)
    sh = Image.new("L", (W, H), 0); ImageDraw.Draw(sh).ellipse([cx - 230, cy - 230, cx + 230, cy + 230], fill=170); halftone(P["blue"], sh, 18, 6)
    for k in range(6): a = k * 1.05 + t * 0.3; P["yellow"].d.ellipse([cx + 110 * math.cos(a) - 30, cy + 110 * math.sin(a) - 45, cx + 110 * math.cos(a) + 30, cy + 110 * math.sin(a) + 45], fill=255)
    txt(P["blue"], "BOTANY RULE:", 70, W / 2, 330, w="Bold"); txt(P["blue"], "1 FLOWER · 1 OVARY", 92, W / 2, 440)
    if lt > 1.2: stamp(P, "blue", "SEEDS INSIDE", W / 2, 1250, rot=6, size=64, u=back((lt - 1.2) / 0.3))
    return P
def sc_banana(sc, lt, dur, t):
    P = plates(); banana(P, W / 2, 880, 1.35, rot=0.08 * math.sin(t * 1.6))
    txt(P["blue"], "ONE OVARY", 110, W / 2, 360)
    stamp(P, "pink", "✓ BERRY", W / 2, 1260, rot=-10, size=96, u=back((lt - 0.6) / 0.3))
    return P
def sc_straw(sc, lt, dur, t):
    P = plates(); strawberry(P, W / 2, 820, 1.35, glow=ease((lt - 0.8) / 0.6))
    txt(P["pink"], "MANY OVARIES", 104, W / 2, 330)
    if lt > 1.0: txt(P["blue"], "EACH DOT = ITS OWN TINY FRUIT", 50, W / 2, 1270, w="Bold")
    if lt > 2.0: stamp(P, "pink", "✗ NOT A BERRY", W / 2, 1420, rot=8, size=76, u=back((lt - 2.0) / 0.3))
    return P
def sc_list(sc, lt, dur, t):
    P = plates(); txt(P["blue"], "ALSO BERRIES:", 110, W / 2, 300)
    items = [("tomato", 290, 640), ("grapes", 790, 640), ("eggplant", 290, 1010), ("watermelon", 790, 1010), ("pumpkin", 540, 1330)]
    for k, (kind, x, y) in enumerate(items):
        u = back((lt - 0.2 - k * 0.45) / 0.3)
        if u <= 0: continue
        fruit_icon(P, kind, x, y, 1.45 * min(1.15, u)); txt(P["pink"], kind.upper(), 48, x, y + 175, w="Bold")
    return P
def sc_end(sc, lt, dur, t):
    P = plates(); click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.2); cx, cy, w_, h_ = W / 2, 960, 330, 150
    (P["pink"] if on > 0.5 else P["blue"]).d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=255)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; P["yellow"].d.ellipse([kx - h_ / 2 + 18, cy - h_ / 2 + 18, kx + h_ / 2 - 18, cy + h_ / 2 - 18], fill=255)
    txt(P["blue"], "FAKE", 70, cx - w_ / 2 - 130, cy); txt(P["pink"], "TRUE", 70, cx + w_ / 2 + 130, cy)
    txt(P["blue"], "SOUNDS FAKE ?!", 110, W / 2, 620); banana(P, 300, 1350, 0.6); strawberry(P, 780, 1300, 0.55)
    return P
SCENES = dict(hook=sc_hook, rule=sc_rule, banana=sc_banana, straw=sc_straw, list=sc_list, end=sc_end)

groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0].upper() for i in g]; size = 64
    while d.textlength(" ".join(ws), font=F(size)) > W - 180 and size > 36: size -= 4
    f = F(size); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1610
    d.rectangle([x - 26, y - 16, x + tw + 26, y + size + 26], fill=(20, 60, 140))
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=(255, 226, 0) if on else (255, 245, 235)); x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = Image.fromarray(compose(SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t), t).astype(np.uint8))
    caption(img, t); ImageDraw.Draw(img).rectangle([0, H - 10, int(W * t / total), H], fill=(255, 72, 140))
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
