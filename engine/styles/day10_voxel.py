"""Day 10 — VOXEL CHESS style (more possible chess games than atoms in the universe).
Isometric voxel world: a cube-built chessboard and pieces, glowing move tiles, numbers that grow into voxel towers,
soft pastel sky. Usage: python3 engine/styles/day10_voxel.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
F = lambda s, w="Black": ImageFont.truetype(f"{FD}InterDisplay-{w}.otf", int(s))
INK, CREAM, GOLD, MINT, CORAL = (40, 34, 60), (252, 244, 228), (255, 196, 70), (90, 220, 190), (255, 110, 100)
yy = np.linspace(0, 1, H)[:, None, None]
SKY = (np.array([196, 186, 240], np.float32) * (1 - yy) + np.array([255, 214, 190], np.float32) * yy).repeat(W, 1).astype(np.uint8)

def shade(c, k): return tuple(int(max(0, min(255, v * k))) for v in c)
class Iso:
    def __init__(self, cx, cy, s): self.cx, self.cy, self.s = cx, cy, s
    def p(self, x, y, z): return (self.cx + (x - y) * self.s * 0.866, self.cy + (x + y) * self.s * 0.5 - z * self.s)
    def cube(self, d, x, y, z, c, outline=True):
        P = self.p; o = INK if outline else None
        d.polygon([P(x, y, z + 1), P(x + 1, y, z + 1), P(x + 1, y + 1, z + 1), P(x, y + 1, z + 1)], fill=c, outline=o)
        d.polygon([P(x, y + 1, z + 1), P(x + 1, y + 1, z + 1), P(x + 1, y + 1, z), P(x, y + 1, z)], fill=shade(c, 0.72), outline=o)
        d.polygon([P(x + 1, y, z + 1), P(x + 1, y + 1, z + 1), P(x + 1, y + 1, z), P(x + 1, y, z)], fill=shade(c, 0.86), outline=o)

PIECE = {"pawn": [(0, 0.55), (1, 0.4)], "rook": [(0, 0.65), (1, 0.6), (2, 0.72)], "knight": [(0, 0.65), (1, 0.6), (2, 0.5)],
         "king": [(0, 0.65), (1, 0.6), (2, 0.55), (3, 0.3)], "queen": [(0, 0.65), (1, 0.6), (2, 0.5), (3, 0.36)]}
def board_cubes(iso, d, pieces, glow=(), t=0.0, glow_col=MINT):
    items = []
    for bx in range(8):
        for by in range(8):
            c = (236, 212, 170) if (bx + by) % 2 == 0 else (150, 100, 70)
            if (bx, by) in glow: c = shade(glow_col, 0.9 + 0.15 * math.sin(t * 6 + bx + by))
            items.append((bx + by, 0, bx, by, -1, c))
    for (bx, by, kind, white) in pieces:
        col = (248, 246, 240) if white else (60, 56, 76)
        for (z, wdt) in PIECE[kind]: items.append((bx + by, z + 1, bx, by, z, col, wdt))
    items.sort(key=lambda it: (it[0], it[1]))
    for it in items:
        if len(it) == 6: iso.cube(d, it[2], it[3], it[4], it[5])
        else:
            _, _, bx, by, z, col, wdt = it; o = (1 - wdt) / 2
            iso.cube(d, bx + o, by + o, z, col) if wdt == 1 else _mini(iso, d, bx + o, by + o, z, wdt, col)
def _mini(iso, d, x, y, z, w_, c):
    P = iso.p
    d.polygon([P(x, y, z + 1), P(x + w_, y, z + 1), P(x + w_, y + w_, z + 1), P(x, y + w_, z + 1)], fill=c, outline=INK)
    d.polygon([P(x, y + w_, z + 1), P(x + w_, y + w_, z + 1), P(x + w_, y + w_, z), P(x, y + w_, z)], fill=shade(c, 0.72), outline=INK)
    d.polygon([P(x + w_, y, z + 1), P(x + w_, y + w_, z + 1), P(x + w_, y + w_, z), P(x + w_, y, z)], fill=shade(c, 0.86), outline=INK)

START = [(x, 6, "pawn", True) for x in range(8)] + [(x, 1, "pawn", False) for x in range(8)] + \
        [(0, 7, "rook", True), (7, 7, "rook", True), (1, 7, "knight", True), (6, 7, "knight", True), (4, 7, "king", True), (3, 7, "queen", True),
         (0, 0, "rook", False), (7, 0, "rook", False), (1, 0, "knight", False), (6, 0, "knight", False), (4, 0, "king", False), (3, 0, "queen", False)]
MOVES20 = [(x, 5) for x in range(8)] + [(x, 4) for x in range(8)] + [(0, 5), (2, 5), (5, 5), (7, 5)]

def card(img, lines, y=200, size=96, accent=None):
    d = ImageDraw.Draw(img); szs = []
    for s in lines:
        z = size
        while d.textlength(s, font=F(z)) > W - 180 and z > 40: z -= 4
        szs.append(z)
    h = sum(z * 1.15 for z in szs) + 60
    d.rounded_rectangle([70, y + 12, W - 58, y + h + 12], 34, fill=INK); d.rounded_rectangle([60, y, W - 70, y + h], 34, fill=CREAM, outline=INK, width=6)
    cy = y + 30
    for i, (s, z) in enumerate(zip(lines, szs)): d.text((W / 2 - 5, cy), s, font=F(z), fill=CORAL if accent and str(i) in accent else INK, anchor="ma"); cy += z * 1.15

def tower(iso, d, n_cubes, x0, y0, col, maxh=14, cols=3):
    for k in range(n_cubes):
        z = k // (cols * cols); r = k % (cols * cols); iso.cube(d, x0 + r % cols, y0 + r // cols, z, shade(col, 0.9 + 0.1 * ((k * 7) % 3)))

def S_hook(sc, lt, dur, t):
    img = Image.fromarray(SKY.copy()); d = ImageDraw.Draw(img); iso = Iso(W / 2, 980, 62 + 4 * ease(lt / dur))
    board_cubes(iso, d, START, t=t); r = random.Random(1)
    for k in range(16):                                                   # floating voxels drifting up ('atoms')
        x, y = r.uniform(80, W - 80), (r.uniform(500, 1500) - t * 60 * r.uniform(0.5, 1.5)) % 1100 + 450; s = r.uniform(16, 30)
        Iso(x, y, s).cube(d, 0, 0, 0, MINT if k % 2 else GOLD)
    card(img, ["MORE CHESS GAMES", "THAN ATOMS", "IN THE UNIVERSE"], 170, 100, accent={"1": 1})
    if sc.get("loop"): d.rounded_rectangle([170, 1380, W - 170, 1490], 50, fill=CORAL, outline=INK, width=5); d.text((W / 2, 1435), sc.get("label", "IT EXPLODES IN 4 MOVES"), font=F(54), fill=CREAM, anchor="mm")
    return img
def S_count(sc, lt, dur, t):
    img = Image.fromarray(SKY.copy()); d = ImageDraw.Draw(img)
    target = sc["n"]; v = int(target * eout((lt - 0.2) / 1.0))
    if sc.get("board"):
        iso = Iso(W / 2, 1060, 60); g = MOVES20[:max(0, min(20, int(20 * ease((lt - 0.2) / 1.0))))]; board_cubes(iso, d, START, glow=set(g), t=t)
    else:
        iso = Iso(W / 2 - 40, 1300, 46); n = int(sc.get("cubes", 60) * eout((lt - 0.2) / 1.2)); tower(iso, d, n, 0, 0, sc.get("col", MINT) if isinstance(sc.get("col"), tuple) else MINT, cols=sc.get("cols", 3))
    d.text((W / 2 + 6, 300 + 8), f"{v:,}", font=F(200), fill=INK, anchor="mm"); d.text((W / 2, 300), f"{v:,}", font=F(200), fill=GOLD, anchor="mm", stroke_width=6, stroke_fill=INK)
    d.rounded_rectangle([120, 430, W - 120, 530], 40, fill=CREAM, outline=INK, width=5); d.text((W / 2, 480), sc["label"], font=F(48), fill=INK, anchor="mm")
    return img
def S_power(sc, lt, dur, t):
    img = Image.fromarray(SKY.copy()); d = ImageDraw.Draw(img); r = random.Random(2)
    n = int(140 * eout((lt - 0.2) / 1.4))
    for k in range(n):
        a = k * 2.399; rad = 40 + 9 * k ** 0.85; x, y = W / 2 + rad * math.cos(a + t * 0.3), 1050 + rad * math.sin(a + t * 0.3) * 0.7
        Iso(x, y, 22).cube(d, 0, 0, 0, GOLD if k % 3 else CORAL)
    card(img, [sc["big"]], 210, 200); d.rounded_rectangle([120, 560, W - 120, 660], 40, fill=CREAM, outline=INK, width=5); d.text((W / 2, 610), sc["label"], font=F(46), fill=INK, anchor="mm")
    return img
def S_compare(sc, lt, dur, t):
    img = Image.fromarray(SKY.copy()); d = ImageDraw.Draw(img)
    u = eout((lt - 0.2) / 1.2)
    iso = Iso(300, 1350, 34); tower(iso, d, int(18 * u), 0, 0, (150, 170, 255), cols=3)
    iso2 = Iso(760, 1350, 34); tower(iso2, d, int(90 * u), 0, 0, GOLD, cols=3)
    d.text((300, 1430), "ATOMS 10⁸⁰", font=F(44), fill=INK, anchor="mm"); d.text((760, 1430), "GAMES 10¹²⁰", font=F(44), fill=INK, anchor="mm")
    if lt > 1.4: card(img, ["10⁴⁰ TIMES MORE", "GAMES THAN ATOMS"], 230, 92, accent={"0": 1})
    return img
def S_end(sc, lt, dur, t):
    img = Image.fromarray(SKY.copy()); d = ImageDraw.Draw(img); iso = Iso(W / 2, 1180, 46); board_cubes(iso, d, START[:8] + START[8:16], t=t)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.2); cx, cy, w_, h_ = W / 2, 760, 330, 150
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=MINT if on > 0.5 else (200, 196, 210), outline=INK, width=6)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; Iso(kx, cy + 30, 50).cube(d, -0.5, -0.5, 0, CREAM)
    d.text((cx - w_ / 2 - 30, cy), "FAKE", font=F(58), fill=INK if on < 0.5 else (140, 130, 150), anchor="rm"); d.text((cx + w_ / 2 + 30, cy), "TRUE", font=F(58), fill=CORAL if on >= 0.5 else (140, 130, 150), anchor="lm")
    card(img, ["SOUNDS FAKE ?!"], 300, 110)
    return img
SCENES = dict(hook=S_hook, count=S_count, power=S_power, compare=S_compare, end=S_end)

voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
for k in range(int(total / 0.2)):                                       # chiptune-ish square arpeggio + blip
    ch = [[261.63, 329.63, 392.0, 523.25], [220.0, 261.63, 329.63, 440.0], [174.61, 220.0, 261.63, 349.23], [196.0, 246.94, 293.66, 392.0]][(k // 16) % 4]
    tt_ = np.arange(int(0.18 * SR)) / SR; sq = np.sign(np.sin(2 * np.pi * ch[k % 4] * tt_)) * np.exp(-tt_ * 14)
    place(music, k * 0.2, sq, 0.02)
    if k % 8 == 0: place(music, k * 0.2, np.sign(np.sin(2 * np.pi * ch[0] / 2 * np.arange(int(0.35 * SR)) / SR)) * np.exp(-np.arange(int(0.35 * SR)) / SR * 5), 0.03)
hook_hit(music, 0.35)
for s_ in scene_starts(spec): whoosh(music, s_, 0.12)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.3)

groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0].upper() for i in g]; size = 64
    while d.textlength(" ".join(ws), font=F(size)) > W - 180 and size > 34: size -= 4
    f = F(size); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1620
    d.rounded_rectangle([x - 30 + 8, y - 16 + 8, x + tw + 30 + 8, y + size + 26 + 8], 24, fill=INK); d.rounded_rectangle([x - 30, y - 16, x + tw + 30, y + size + 26], 24, fill=CREAM, outline=INK, width=5)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=CORAL if on else INK); x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t); caption(img, t)
    ImageDraw.Draw(img).rectangle([0, H - 10, int(W * t / total), H], fill=CORAL); return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
