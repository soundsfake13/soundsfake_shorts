"""LONG-FORM (16:9, 1920x1080) — 'Sounds Fake: Deep Dive' ep08: ACCIDENTAL INVENTIONS.
Look: "inventor's blueprint" — deep blueprint-blue paper with a drifting drafting grid, white/cyan line drawings that
draw themselves on, amber accents, handwritten margin notes.
Beats: self-drawing blueprint sketches (bubble wrap, sticky notes, flask, glue, jet, magnetron, popcorn, gas cylinder,
pan, resistor, pacemaker, Crookes tube, petri dish, melon, horn antenna), melting candy bar, giant first microwave vs
a person, heartbeat scope, X-ray hand, shoe X-ray, Big Bang afterglow, TV static.
Based on engine/long/ep07_time.py.
Usage: python3 engine/long/ep08_accidents.py spec.json out.mp4 [t1,t2,... preview]
"""
import json, math, os, random, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import core
from core import narrate, write_audio, caption_groups, group_at, ease, eout, back, tone, place, hook_hit, whoosh, SR

W, H, FPS = 1920, 1080, 30
spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
rng = np.random.default_rng(8); random.seed(8)
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(os.path.dirname(HERE), "fonts", "Kalam-Bold.ttf")
_fc = {}
def F(s, w="Black"):
    k = (int(s), w)
    if k not in _fc: _fc[k] = ImageFont.truetype(HAND if w == "Hand" else f"{FD}InterDisplay-{w}.otf", int(s))
    return _fc[k]
AMBER, CYAN, WHITE, DIM, RED, GREEN = (255, 186, 76), (120, 214, 255), (240, 246, 255), (130, 160, 205), (255, 104, 90), (120, 232, 160)
LINE = (196, 224, 255); INKD = (8, 22, 50); FILL = (30, 70, 130)
COL = dict(gold=AMBER, cyan=CYAN, white=WHITE, dim=(170, 190, 220), red=RED, green=GREEN)
def lerpc(a, b, u): return tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3))

# ---------------- background: blueprint paper + drifting grid ----------------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = np.exp(-(((xx - W / 2) / (W * 0.65)) ** 2 + ((yy - H * 0.45) / (H * 0.75)) ** 2))
BG = np.zeros((H, W, 3), np.float32) + np.array([6, 20, 48], np.float32) + vig[..., None] * np.array([12, 34, 70], np.float32)
r_ = np.random.default_rng(3).random((H // 6 + 1, W // 6 + 1)).astype(np.float32)
paper = np.asarray(Image.fromarray((r_ * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)).astype(np.float32) / 255
BG += (paper[..., None] - 0.5) * 7
BG_IMG = Image.fromarray(np.clip(BG, 0, 255).astype(np.uint8))
GRID = Image.new("RGBA", (W + 200, H + 200), (0, 0, 0, 0)); _g = ImageDraw.Draw(GRID)
for x in range(0, W + 200, 40): _g.line([(x, 0), (x, H + 200)], fill=(120, 170, 240, 60 if x % 200 == 0 else 20), width=2 if x % 200 == 0 else 1)
for y in range(0, H + 200, 40): _g.line([(0, y), (W + 200, y)], fill=(120, 170, 240, 60 if y % 200 == 0 else 20), width=2 if y % 200 == 0 else 1)
MARKS = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(20, 60), rng.uniform(0, 6.3)) for _ in range(10)]
def space(t, grid=True):
    img = BG_IMG.copy()
    if grid:
        ox, oy = int((t * 6) % 200), int((t * 3) % 200); img.paste(GRID.crop((ox, oy, ox + W, oy + H)), (0, 0), GRID.crop((ox, oy, ox + W, oy + H)))
        d = ImageDraw.Draw(img)
        for (x, y, r, ph) in MARKS:   # faint drafting circles + crosshairs drifting
            px = (x + t * 4) % W; py = y; a = int(26 + 14 * math.sin(t * 0.5 + ph))
            d.ellipse([px - r, py - r, px + r, py + r], outline=(30 + a, 64 + a, 120 + a), width=1)
            d.line([(px - r * 1.4, py), (px + r * 1.4, py)], fill=(34, 66, 118), width=1); d.line([(px, py - r * 1.4), (px, py + r * 1.4)], fill=(34, 66, 118), width=1)
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
    col = tuple(int(c * u + 8 * (1 - u)) for c in col)
    if shadow: d.text((x + 3, y + 4), s, font=f, fill=(2, 10, 26), anchor=anchor)
    d.text((x, y), s, font=f, fill=col, anchor=anchor)

def pill(img, s, size, x, y, fill=AMBER, ink=(10, 20, 40), u=1.0, w="Bold"):
    if u <= 0: return
    d = ImageDraw.Draw(img); f = F(size, w); tw = d.textlength(s, font=f); y = y + (1 - u) * 16
    d.rounded_rectangle([x - tw / 2 - 26, y - size * 0.72, x + tw / 2 + 26, y + size * 0.72], int(size * 0.72), fill=fill)
    d.text((x, y), s, font=f, fill=ink, anchor="mm")

def note(img, s, x, y, u, col=AMBER):
    """Handwritten margin note with an underline that draws on."""
    if u <= 0: return
    d = ImageDraw.Draw(img); c = tuple(int(v * u + 8 * (1 - u)) for v in col)
    if s.startswith("→ "):
        s = s[2:]; d.line([(x, y + 4), (x + 34, y + 4)], fill=c, width=5); d.polygon([(x + 44, y + 4), (x + 28, y - 8), (x + 28, y + 16)], fill=c); x += 62
    f = F(50, "Hand"); tw = d.textlength(s, font=f)
    while tw > 760: f = F(f.size - 4, "Hand"); tw = d.textlength(s, font=f)
    d.text((x, y), s, font=f, fill=c, anchor="lm")
    d.line([(x, y + 34), (x + tw * eout(u), y + 34)], fill=c, width=4)

def fmtnum(v, kind):
    if kind == "int": return f"{int(round(v)):,}"
    if kind == "f1": return f"{v:,.1f}"
    return str(v)

# ---------------- icon drawings (on an RGBA canvas 820x680, centre 410,340) ----------------
CW, CH = 820, 680
def heart_pts(cx, cy, s):
    return [(cx + s * 16 * math.sin(a) ** 3 / 16, cy - s * (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)) / 16) for a in np.linspace(0, 2 * math.pi, 80)]

def ico(name, mode, lt, t):
    c = Image.new("RGBA", (CW, CH), (0, 0, 0, 0)); d = ImageDraw.Draw(c); L = LINE + (255,); A = AMBER + (255,); Fi = FILL + (150,); wd = 6
    if name == "bubbles":
        d.rounded_rectangle([90, 110, 730, 570], 20, fill=(40, 90, 160, 90), outline=L, width=wd)
        for j in range(4):
            for i in range(6):
                k = j * 6 + i; u = eout((lt - 0.3 - k * 0.05) / 0.4); r = 42 * u
                x, y = 160 + i * 100 + (50 if j % 2 else 0) - 25, 175 + j * 110
                if r > 1:
                    d.ellipse([x - r, y - r, x + r, y + r], fill=(90, 160, 230, 110), outline=L, width=4)
                    d.arc([x - r * 0.6, y - r * 0.65, x + r * 0.2, y + r * 0.1], 190, 260, fill=(255, 255, 255, 230), width=5)
    elif name == "wall":
        d.rectangle([60, 60, 760, 520], fill=(40, 90, 160, 70), outline=L, width=wd)
        for j in range(6):
            for i in range(9):
                x, y = 100 + i * 78 + (39 if j % 2 else 0), 100 + j * 74
                if x < 740: d.ellipse([x - 22, y - 22, x + 22, y + 22], outline=(160, 200, 255, 170), width=3)
        d.rectangle([300, 150, 520, 300], fill=(10, 30, 60, 255), outline=A, width=6)   # picture frame
        d.polygon([(330, 280), (390, 200), (440, 260), (470, 230), (500, 280)], fill=A)
        d.line([(20, 520), (800, 520)], fill=L, width=wd)
        d.rounded_rectangle([110, 430, 330, 520], 26, outline=L, width=wd)               # sofa
        d.rounded_rectangle([90, 400, 140, 520], 20, outline=L, width=wd); d.rounded_rectangle([300, 400, 350, 520], 20, outline=L, width=wd)
    elif name == "box":
        d.polygon([(170, 300), (650, 300), (650, 600), (170, 600)], fill=(150, 110, 60, 200), outline=L)
        d.polygon([(170, 300), (90, 200), (330, 200), (410, 300)], fill=(120, 90, 50, 220), outline=L)
        d.polygon([(650, 300), (730, 200), (490, 200), (410, 300)], fill=(120, 90, 50, 220), outline=L)
        d.line([(170, 300), (650, 300)], fill=L, width=wd); d.rectangle([170, 300, 650, 600], outline=L, width=wd)
        # bubble sheet billowing out of the box
        ph = math.sin(t * 2) * 6
        for i in range(7):
            for j in range(2):
                x, y = 230 + i * 62 + j * 31, 260 - j * 52 + ph * (1 if i % 2 else -1)
                d.ellipse([x - 26, y - 26, x + 26, y + 26], fill=(150, 200, 255, 150), outline=L, width=3)
        d.text((410, 470), "FRAGILE", font=F(64, "Black"), fill=(230, 80, 70, 255), anchor="mm")
        d.text((410, 540), "▲ THIS SIDE UP ▲", font=F(30, "Bold"), fill=(40, 30, 20, 255), anchor="mm")
    elif name == "note":
        lift = 0.5 + 0.5 * math.sin(t * 2.2)
        d.rectangle([180, 120, 640, 560], fill=(255, 220, 90, 255))
        for k in range(4): d.line([(230, 230 + k * 75), (590, 230 + k * 75)], fill=(200, 160, 60, 255), width=5)
        cx_ = 120 * (0.4 + 0.6 * lift)
        d.polygon([(640, 560 - cx_), (640 - cx_, 560), (640, 560)], fill=(6, 20, 48, 255))
        d.polygon([(640, 560 - cx_), (640 - cx_, 560), (640 - cx_ * 0.9, 560 - cx_ * 0.9)], fill=(240, 190, 70, 255))
        d.text((410, 175), "remember!", font=F(60, "Hand"), fill=(80, 60, 30, 255), anchor="mm")
    elif name == "book":
        d.polygon([(410, 200), (110, 160), (110, 560), (410, 600)], fill=(230, 236, 250, 255), outline=L)
        d.polygon([(410, 200), (710, 160), (710, 560), (410, 600)], fill=(220, 228, 244, 255), outline=L)
        d.line([(410, 200), (410, 600)], fill=(140, 160, 200, 255), width=4)
        for k in range(7):
            d.line([(150, 215 + k * 48), (380, 245 + k * 48)], fill=(150, 165, 200, 255), width=5)
            d.line([(440, 245 + k * 48), (670, 215 + k * 48)], fill=(150, 165, 200, 255), width=5)
        for k in range(3):   # music notes
            x = 470 + k * 70; d.ellipse([x, 150 - k * 6, x + 30, 174 - k * 6], fill=A); d.line([(x + 28, 160 - k * 6), (x + 28, 90 - k * 6)], fill=A, width=5)
        if mode == "fall":
            for k in range(2):
                p = ((lt * 0.55 + k * 0.5) % 1.0); y = 140 + p * 520; x = 300 + k * 260 + math.sin(p * 9 + k) * 30
                s = Image.new("RGBA", (70, 200), (0, 0, 0, 0)); ImageDraw.Draw(s).rectangle([10, 0, 60, 200], fill=(240, 240, 240, int(255 * (1 - p ** 3))), outline=(180, 120, 90, 255), width=3)
                s = s.rotate(30 * math.sin(p * 7 + k), expand=True, resample=Image.BICUBIC); c.paste(s, (int(x - s.width / 2), int(y - s.height / 2)), s)
        else:
            for k in range(3):
                u = eout((lt - 0.3 - k * 0.35) / 0.35); y = 240 + k * 110
                if u > 0: d.rectangle([640 + 30 * (1 - u), y, 760 + 30 * (1 - u), y + 70], fill=(255, 220, 90, int(255 * u)))
    elif name == "flask":
        d.polygon([(350, 120), (470, 120), (470, 280), (640, 560), (180, 560), (350, 280)], fill=Fi, outline=L)
        d.line([(350, 120), (350, 280), (180, 560), (640, 560), (470, 280), (470, 120)], fill=L, width=wd, joint="curve")
        d.polygon([(286, 420), (534, 420), (640, 560), (180, 560)], fill=(110, 230, 160, 200))
        d.rectangle([330, 100, 490, 124], outline=L, width=wd)
        for k in range(6):
            p = (lt * 0.5 + k / 6) % 1; x = 330 + (k * 37) % 160 + math.sin(p * 8 + k) * 12; y = 540 - p * 180
            if y > 430: d.ellipse([x - 9, y - 9, x + 9, y + 9], outline=(220, 255, 230, 255), width=3)
        for k in range(3):
            p = (lt * 0.3 + k / 3) % 1; y = 90 - p * 90; x = 410 + math.sin(p * 6 + k * 2) * 40
            d.ellipse([x - 30 * p - 10, y - 20 * p - 8, x + 30 * p + 10, y + 20 * p + 8], outline=(200, 220, 255, int(200 * (1 - p))), width=3)
    elif name == "bread":
        d.rounded_rectangle([200, 260, 620, 580], 30, fill=(230, 180, 110, 255))
        d.ellipse([170, 130, 410, 340], fill=(230, 180, 110, 255)); d.ellipse([410, 130, 650, 340], fill=(230, 180, 110, 255))
        d.rounded_rectangle([230, 280, 590, 550], 24, fill=(250, 232, 190, 255)); d.ellipse([200, 160, 400, 330], fill=(250, 232, 190, 255)); d.ellipse([420, 160, 620, 330], fill=(250, 232, 190, 255))
        for k in range(9):
            x, y = 260 + (k * 97) % 320, 220 + (k * 61) % 300; d.ellipse([x, y, x + 12, y + 8], fill=(220, 190, 140, 255))
        for k in range(6):
            a = k * 1.05 + t * 0.6; r = 320 + 20 * math.sin(t * 3 + k); x, y = 410 + r * math.cos(a), 360 + r * 0.8 * math.sin(a)
            s = 22 + 10 * math.sin(t * 4 + k); d.polygon([(x, y - s), (x + s * 0.3, y - s * 0.3), (x + s, y), (x + s * 0.3, y + s * 0.3), (x, y + s), (x - s * 0.3, y + s * 0.3), (x - s, y), (x - s * 0.3, y - s * 0.3)], fill=A)
    elif name == "hand":
        hand_outline(d, 410, 600, 1.0, L, Fi)
        if mode == "sweet":
            for k in range(8):
                a = k * 0.8 + t * 0.5; r = 300 + 20 * math.sin(t * 2 + k); x, y = 410 + r * math.cos(a), 340 + r * 0.9 * math.sin(a)
                s = 20 + 8 * math.sin(t * 4 + k); d.polygon([(x, y - s), (x + s * 0.3, y - s * 0.3), (x + s, y), (x + s * 0.3, y + s * 0.3), (x, y + s), (x - s * 0.3, y + s * 0.3), (x - s, y), (x - s * 0.3, y - s * 0.3)], fill=A)
    elif name == "sight":
        d.ellipse([170, 100, 650, 580], fill=(140, 200, 255, 60), outline=L, width=10)
        d.ellipse([200, 130, 620, 550], outline=(160, 200, 255, 140), width=3)
        d.line([(410, 140), (410, 300)], fill=L, width=4); d.line([(410, 380), (410, 540)], fill=L, width=4)
        d.line([(210, 340), (370, 340)], fill=L, width=4); d.line([(450, 340), (610, 340)], fill=L, width=4)
        d.ellipse([400, 330, 420, 350], fill=A); d.arc([230, 160, 480, 400], 200, 250, fill=(255, 255, 255, 200), width=8)
    elif name == "drop":
        d.rounded_rectangle([90, 250, 420, 360], 30, fill=Fi, outline=L, width=wd); d.polygon([(420, 270), (520, 295), (520, 315), (420, 340)], fill=Fi, outline=L)
        d.rectangle([60, 260, 100, 350], fill=A)
        p = (lt * 0.8) % 1.6; y = 330 + min(p, 1.0) * 160
        d.ellipse([500, y - 20, 540, y + 28], fill=(240, 250, 255, 255)); d.polygon([(504, y - 6), (520, y - 46), (536, y - 6)], fill=(240, 250, 255, 255))
        d.rectangle([380, 520, 760, 600], fill=(120, 150, 200, 255), outline=L, width=4)   # two blocks glued
        d.rectangle([450, 440, 690, 520], fill=(160, 190, 230, 255), outline=L, width=4)
        d.line([(450, 520), (690, 520)], fill=A, width=8)
    elif name == "jet":
        pts = [(80, 360), (200, 330), (520, 320), (700, 300), (770, 330), (700, 360), (520, 380), (200, 380)]
        d.polygon(pts, fill=Fi, outline=L); d.line(pts + [pts[0]], fill=L, width=wd, joint="curve")
        d.polygon([(380, 330), (300, 170), (360, 170), (500, 330)], fill=Fi, outline=L)
        d.polygon([(380, 370), (300, 520), (360, 520), (500, 370)], fill=Fi, outline=L)
        d.polygon([(110, 350), (60, 240), (110, 240), (190, 340)], fill=Fi, outline=L)
        d.chord([560, 270, 700, 350], 180, 360, fill=(255, 190, 80, 200), outline=A, width=5)   # canopy
        halo_rgba(c, 630, 300, 60, AMBER, 70)
    elif name == "magnetron":
        d.rounded_rectangle([90, 260, 330, 520], 20, fill=Fi, outline=L, width=wd)
        for k in range(5): d.line([(120, 300 + k * 40), (300, 300 + k * 40)], fill=(160, 200, 255, 200), width=4)
        d.ellipse([170, 160, 250, 240], outline=L, width=wd); d.line([(210, 240), (210, 260)], fill=L, width=wd)
        for k in range(5):
            p = ((lt * 0.7 + k / 5) % 1); r = 60 + p * 420
            d.arc([330 - r, 390 - r, 330 + r, 390 + r], -35, 35, fill=AMBER + (int(255 * (1 - p)),), width=6)
    elif name == "popcorn":
        d.polygon([(230, 300), (590, 300), (540, 620), (280, 620)], fill=(240, 240, 250, 255), outline=L)
        for k in range(5): d.polygon([(250 + k * 72, 300), (286 + k * 72, 300), (268 + k * 60 + 30, 620), (268 + k * 60 + 14, 620)], fill=(230, 70, 70, 255))
        for k in range(16):
            u = eout((lt - 0.2 - k * 0.12) / 0.25); x = 260 + (k * 53) % 300; y = 290 - (k * 37) % 120 - 40 * u
            if u > 0:
                r = 26 * u
                for (dx, dy) in ((0, 0), (r * 0.8, -r * 0.4), (-r * 0.7, -r * 0.5), (0, -r * 0.9)): d.ellipse([x + dx - r * 0.7, y + dy - r * 0.7, x + dx + r * 0.7, y + dy + r * 0.7], fill=(255, 248, 225, 255))
                d.ellipse([x - 5, y + 2, x + 5, y + 10], fill=(220, 160, 60, 255))
    elif name == "cylinder":
        draw_cylinder(c, d, mode, lt, t)
    elif name == "pan":
        d.ellipse([140, 220, 600, 520], fill=(40, 46, 60, 255), outline=L, width=wd); d.ellipse([175, 250, 565, 490], fill=(60, 70, 92, 255))
        d.rounded_rectangle([580, 345, 790, 395], 20, fill=(30, 30, 40, 255), outline=L, width=wd)
        x = 370 + 90 * math.sin(t * 1.6); y = 370
        d.ellipse([x - 100, y - 70, x + 100, y + 70], fill=(250, 250, 250, 255)); d.ellipse([x - 38, y - 34, x + 38, y + 34], fill=(255, 190, 40, 255))
        for k in range(3): d.line([(x - 140 - k * 30 if math.cos(t * 1.6) > 0 else x + 120 + k * 30, y - 30 + k * 30), (x - 120 - k * 30 if math.cos(t * 1.6) > 0 else x + 140 + k * 30, y - 30 + k * 30)], fill=(200, 230, 255, 160), width=4)
    elif name == "circuit":
        d.rounded_rectangle([80, 160, 520, 560], 20, fill=(20, 80, 60, 230), outline=L, width=wd)
        for k in range(6): d.line([(120, 220 + k * 55), (480, 220 + k * 55)], fill=(200, 170, 90, 200), width=3)
        for (x, y) in ((180, 260), (300, 330), (400, 440), (220, 470)): d.rectangle([x - 26, y - 14, x + 26, y + 14], fill=(30, 30, 40, 255), outline=L, width=3)
        d.rounded_rectangle([560, 220, 780, 440], 16, fill=(10, 30, 20, 255), outline=L, width=wd)
        pts = [(580 + k * 4, 330 + 40 * math.sin(k * 0.3 + t * 4) * math.exp(-((k % 18) - 9) ** 2 / 40)) for k in range(50)]
        d.line(pts, fill=(120, 255, 160, 255), width=4)
        d.line([(520, 330), (560, 330)], fill=L, width=4)
    elif name == "resistor":
        wob = math.sin(t * 3) * 6
        d.line([(40, 340), (230, 340)], fill=(200, 200, 210, 255), width=12); d.line([(590, 340), (780, 340)], fill=(200, 200, 210, 255), width=12)
        d.rounded_rectangle([210, 250 + wob, 610, 430 + wob], 80, fill=(225, 200, 160, 255), outline=L, width=4)
        for k, cc in enumerate([(150, 80, 40), (20, 20, 20), (240, 200, 40), (210, 170, 60)]):
            x = 290 + k * 75; d.rectangle([x, 252 + wob, x + 34, 428 + wob], fill=cc + (255,))
        u = ease((lt - 0.6) / 0.4)
        if u > 0:
            d.ellipse([360 - 90 * u, 250 - 90 * u, 450 + 90 * u, 430 + 90 * u], outline=RED + (255,), width=10)
            d.text((640, 170), "?!", font=F(120, "Black"), fill=RED + (int(255 * u),), anchor="mm")
    elif name == "pacer":
        beat = (t * 1.2) % 1; s = 1 + 0.12 * math.exp(-beat * 10) if mode == "beat" else 1 + 0.06 * math.exp(-beat * 10)
        d.polygon(heart_pts(560, 360, 230 * s), fill=(220, 70, 80, 230), outline=(255, 180, 180, 255))
        d.rounded_rectangle([90, 250, 290, 430], 60, fill=(200, 210, 225, 255), outline=L, width=wd)
        d.rounded_rectangle([140, 220, 240, 260], 12, fill=(160, 170, 190, 255), outline=L, width=4)
        pts = [(190, 220), (240, 140), (380, 140), (480, 260), (520, 380)]
        d.line(pts, fill=L, width=6, joint="curve")
        if math.exp(-beat * 10) > 0.3: d.ellipse([505, 365, 535, 395], fill=A)
    elif name == "tube":
        glow = mode == "glow"; g = ease((lt - 0.4) / 0.5) if glow else 0
        d.ellipse([60, 250, 420, 430], fill=(150, 200, 255, 60), outline=L, width=wd); d.line([(20, 340), (60, 340)], fill=L, width=wd); d.line([(420, 340), (460, 340)], fill=L, width=wd)
        d.rectangle([90, 320, 120, 360], fill=L); d.rectangle([380, 320, 400, 360], fill=L)
        d.rounded_rectangle([600, 160, 650, 520], 10, fill=lerpc((40, 60, 90), (150, 255, 190), g) + (255,), outline=L, width=4)
        d.line([(625, 520), (625, 600)], fill=L, width=wd); d.line([(560, 600), (690, 600)], fill=L, width=wd)
        if g > 0:
            halo_rgba(c, 625, 340, 160, (140, 255, 180), int(160 * g))
            for k in range(6):
                p = (lt * 0.8 + k / 6) % 1; x = 430 + p * 160
                d.line([(x, 260 + k * 30), (x + 30, 260 + k * 30)], fill=(200, 255, 220, int(160 * (1 - p))), width=3)
    elif name == "dish":
        d.ellipse([110, 70, 710, 610], fill=(220, 220, 170, 60), outline=L, width=wd); d.ellipse([140, 100, 680, 580], outline=(170, 200, 255, 150), width=3)
        mold = ease((lt - 0.3) / 1.5) if mode == "mold" else 0
        mx, my = 330, 280; clear = 60 + 150 * mold
        rr = random.Random(5)
        for k in range(140):
            a = rr.uniform(0, 6.28); r = 260 * math.sqrt(rr.random()); x, y = 410 + r * math.cos(a), 340 + r * math.sin(a)
            if math.hypot(x - mx, y - my) < clear and mold > 0: continue
            d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(245, 230, 150, 230))
        if mold > 0:
            for k in range(26):
                a = k * 0.73; r = (20 + 60 * rr.random()) * (0.4 + 0.6 * mold); d.ellipse([mx + r * math.cos(a) - 26, my + r * math.sin(a) - 26, mx + r * math.cos(a) + 26, my + r * math.sin(a) + 26], fill=(110, 190, 120, 255))
            d.ellipse([mx - clear, my - clear, mx + clear, my + clear], outline=(255, 255, 255, int(160 * mold)), width=3)
    elif name == "melon":
        d.ellipse([140, 110, 680, 600], fill=(210, 190, 130, 255), outline=L, width=wd)
        for k in range(-6, 7):
            d.arc([410 - 260 + abs(k) * 0, 110, 410 + 260, 600], 0, 360, fill=(0, 0, 0, 0))
        rr = random.Random(9)
        for k in range(90):   # netted rind
            x, y = rr.uniform(180, 640), rr.uniform(150, 560)
            if math.hypot(x - 410, (y - 355) * 1.1) < 250: d.line([(x, y), (x + rr.uniform(-30, 30), y + rr.uniform(-30, 30))], fill=(240, 230, 190, 255), width=4)
        u = ease((lt - 0.3) / 1.0)
        for (mx, my, mr) in ((300, 230, 70), (500, 420, 90), (420, 300, 50)):
            r = mr * u
            if r > 2:
                for k in range(12): a = k * 0.52; d.ellipse([mx + r * 0.6 * math.cos(a) - r * 0.45, my + r * 0.6 * math.sin(a) - r * 0.45, mx + r * 0.6 * math.cos(a) + r * 0.45, my + r * 0.6 * math.sin(a) + r * 0.45], fill=(150, 200, 90, 255))
                d.ellipse([mx - r * 0.5, my - r * 0.5, mx + r * 0.5, my + r * 0.5], fill=(240, 210, 80, 255))
    elif name == "antenna":
        draw_antenna(c, d, mode, lt, t)
    return c

def halo_rgba(c, cx, cy, r, col, strength=120):
    g = Image.new("L", c.size, 0); ImageDraw.Draw(g).ellipse([cx - r, cy - r, cx + r, cy + r], fill=int(strength))
    layer = Image.new("RGBA", c.size, col + (0,)); layer.putalpha(g.filter(ImageFilter.GaussianBlur(r * 0.5)))
    c.alpha_composite(layer)

def hand_outline(d, cx, base, s, L, Fi, bones=False):
    """Simple open hand (palm + four fingers + thumb)."""
    pw = 230 * s; ph = 220 * s; top = base - ph
    fingers = [(-0.36, 190), (-0.12, 230), (0.12, 215), (0.36, 170)]
    if not bones:
        d.rounded_rectangle([cx - pw / 2, top, cx + pw / 2, base], int(60 * s), fill=Fi, outline=L, width=6)
        for (fx, fl) in fingers:
            x = cx + fx * pw; d.rounded_rectangle([x - 26 * s, top - fl * s, x + 26 * s, top + 40 * s], int(26 * s), fill=Fi, outline=L, width=6)
        a_, b_ = (cx - pw / 2 + 40 * s, base - 50 * s), (cx - pw / 2 - 85 * s, top + 5 * s)
        for rr_, cc_ in ((32 * s, L), (26 * s, Fi)):
            d.line([a_, b_], fill=cc_, width=int(rr_ * 2))
            for q in (a_, b_): d.ellipse([q[0] - rr_, q[1] - rr_, q[0] + rr_, q[1] + rr_], fill=cc_)
        d.rounded_rectangle([cx - pw / 2, top, cx + pw / 2, base], int(60 * s), fill=Fi, outline=L, width=6)
        d.rectangle([cx - pw / 2 + 6, top + 50 * s, cx + pw / 2 - 6, base - 6], fill=Fi)

def draw_cylinder(c, d, mode, lt, t):
    L = LINE + (255,); x0, x1, y0, y1 = 300, 520, 170, 560
    sx = 0
    if mode == "cut":
        u = eout((lt - 0.3) / 0.6); sx = 50 * u
    for side, off in ((0, -sx), (1, sx)):
        xa = x0 + off if side == 0 else (x0 + x1) / 2 + off; xb = (x0 + x1) / 2 + off if side == 0 else x1 + off
        d.rectangle([xa, y0 + 40, xb, y1], fill=(90, 120, 170, 255))
    d.ellipse([x0 - sx, y0, x1 + sx, y0 + 80], fill=(110, 140, 190, 255)) if mode != "cut" else None
    if mode == "cut":
        d.chord([x0 - sx, y0, (x0 + x1) / 2 - sx, y0 + 80], 90, 270, fill=(110, 140, 190, 255)); d.chord([(x0 + x1) / 2 + sx, y0, x1 + sx, y0 + 80], 270, 90, fill=(110, 140, 190, 255))
        rr = random.Random(2); p = ease((lt - 0.6) / 1.0)
        for k in range(160):
            x = (x0 + x1) / 2 + rr.gauss(0, 30 + 120 * p); y = y1 - rr.random() * 380 * (1 - p * 0.7)
            d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(250, 250, 250, 255))
        d.polygon([((x0 + x1) / 2 - 140 * p - 20, y1), ((x0 + x1) / 2, y1 - 100 * p - 20), ((x0 + x1) / 2 + 140 * p + 20, y1)], fill=(250, 250, 250, 255))
    d.rectangle([380, 120, 440, 175], fill=(180, 190, 210, 255), outline=L, width=4); d.rectangle([350, 105, 470, 125], fill=(200, 80, 70, 255))
    if mode == "valve":
        u = ease((lt - 0.4) / 0.4)
        for k in range(3): d.arc([470 + k * 30, 70 - k * 20, 560 + k * 40, 160 + k * 20], 300, 60, fill=(200, 220, 255, int(140 * (1 - u))), width=4)
        if u > 0: d.text((620, 120), "…?", font=F(110, "Black"), fill=AMBER + (int(255 * u),), anchor="mm")
    if mode == "scale":
        d.rectangle([220, 560, 600, 620], fill=(60, 80, 120, 255), outline=L, width=5)
        d.ellipse([620, 400, 800, 580], fill=(240, 244, 255, 255), outline=L, width=5)
        a = math.radians(-120 + 200 * eout((lt - 0.3) / 0.8)); d.line([(710, 490), (710 + 70 * math.sin(a), 490 - 70 * math.cos(a))], fill=(220, 50, 50, 255), width=6)
        d.text((710, 545), "FULL", font=F(28, "Black"), fill=(20, 30, 50, 255), anchor="mm")
    d.text(((x0 + x1) / 2, 380), "GAS", font=F(44, "Black"), fill=(220, 230, 250, 200), anchor="mm") if mode != "cut" else None

def pigeon(d, x, y, s, col=(200, 210, 230, 255), flip=False, flap=0.0):
    k = -1 if flip else 1
    d.ellipse([x - 40 * s, y - 22 * s, x + 40 * s, y + 22 * s], fill=col)
    d.ellipse([x + k * 30 * s - 18 * s, y - 46 * s, x + k * 30 * s + 18 * s, y - 12 * s], fill=col)
    d.polygon([(x + k * 46 * s, y - 32 * s), (x + k * 62 * s, y - 28 * s), (x + k * 46 * s, y - 24 * s)], fill=AMBER + (255,))
    d.polygon([(x - k * 36 * s, y), (x - k * 70 * s, y - 8 * s), (x - k * 66 * s, y + 12 * s)], fill=col)
    d.polygon([(x - k * 10 * s, y - 6 * s), (x - k * 40 * s, y - 10 * s - 50 * s * flap), (x + k * 14 * s, y - 4 * s)], fill=(160, 170, 195, 255))
    d.ellipse([x + k * 32 * s - 4 * s, y - 36 * s, x + k * 32 * s + 4 * s, y - 28 * s], fill=(20, 20, 30, 255))

def draw_antenna(c, d, mode, lt, t):
    L = LINE + (255,); Fi = FILL + (190,)
    # horn: narrow throat bottom-left, wide square mouth opening up-right
    d.line([(60, 620), (780, 620)], fill=L, width=6)
    d.polygon([(150, 560), (230, 560), (720, 210), (560, 60)], fill=Fi, outline=L)
    d.line([(150, 560), (560, 60), (720, 210), (230, 560), (150, 560)], fill=L, width=6, joint="curve")
    d.polygon([(560, 60), (720, 210), (760, 170), (600, 20)], fill=(70, 120, 190, 220), outline=L)
    d.rectangle([110, 540, 270, 600], fill=(60, 90, 140, 255), outline=L, width=5)
    for (a, b) in (((200, 600), (200, 620)), ((420, 400), (420, 620)), ((620, 200), (650, 620))): d.line([a, b], fill=L, width=6)
    d.line([(420, 620), (650, 400)], fill=L, width=4); d.line([(200, 620), (420, 480)], fill=L, width=4)
    if mode in ("hiss",):
        for k in range(14):
            a = k * 2 * math.pi / 14; p = (lt * 0.6 + k * 0.17) % 1; r = 420 * (1 - p)
            x, y = 640 + r * math.cos(a), 140 + r * math.sin(a) * 0.8
            d.arc([x - 22, y - 22, x + 22, y + 22], math.degrees(a) + 120, math.degrees(a) + 240, fill=AMBER + (int(230 * min(1, p * 3)),), width=5)
    if mode in ("pigeons", "tease"):
        pigeon(d, 600, 150, 1.1, flap=0.3 * max(0, math.sin(t * 6))); pigeon(d, 680, 210, 1.0, flip=True)
        for k in range(7): x = 470 + k * 36; d.ellipse([x, 330 - k * 25, x + 16, 342 - k * 25], fill=(240, 240, 240, 255))
    if mode == "clean":
        p = ease(lt / 2.0)
        pigeon(d, 600 + 250 * p, 150 - 160 * p, 1.1, flap=abs(math.sin(t * 14))); pigeon(d, 680 + 120 * p, 210 - 220 * p, 1.0, flip=True, flap=abs(math.sin(t * 13 + 1)))
        for k in range(6):
            x, y = 330 + k * 60, 470 - k * 55; s = 18 + 8 * math.sin(t * 5 + k)
            d.polygon([(x, y - s), (x + s * 0.3, y - s * 0.3), (x + s, y), (x + s * 0.3, y + s * 0.3), (x, y + s), (x - s * 0.3, y + s * 0.3), (x - s, y), (x - s * 0.3, y - s * 0.3)], fill=(255, 255, 255, 230))

def reveal(layer, u):
    """Blueprint draw-on: a soft left-to-right wipe."""
    if u >= 1: return layer
    m = Image.new("L", layer.size, 0); x = int(layer.width * u * 1.15)
    ImageDraw.Draw(m).rectangle([0, 0, x, layer.height], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(30)); a = layer.getchannel("A")
    layer = layer.copy(); layer.putalpha(Image.fromarray((np.asarray(a).astype(np.float32) * np.asarray(m) / 255).astype(np.uint8))); return layer

# ---------------- beats: generic ----------------
def b_cold(sc, lt, dur, t):
    img = space(t)
    for i, s in enumerate(sc["lines"]):
        text(img, s, sc.get("size", 120), W / 2, 330 + i * sc.get("size", 120) * 1.15, AMBER if i == 1 else WHITE, u=1.0 if i == 0 else ease((lt - i * 0.5) / 0.4))
    if "sub" in sc: pill(img, sc["sub"], 40, W / 2, 640, fill=CYAN, u=ease((lt - 0.8) / 0.4))
    return img

def b_chapter(sc, lt, dur, t):
    img = space(t); u = back(lt / 0.45); d = ImageDraw.Draw(img); cx, cy, R = W / 2, 320, 170
    # rotating dashed drafting ring + crosshair, number inside
    for k in range(36):
        a0 = k * 10 + t * 20
        d.arc([cx - R - 30, cy - R - 30, cx + R + 30, cy + R + 30], a0, a0 + 5, fill=CYAN, width=5)
    d.ellipse([cx - R * min(1, u), cy - R * min(1, u), cx + R * min(1, u), cy + R * min(1, u)], fill=(12, 34, 74), outline=AMBER, width=8)
    d.line([(cx - R - 70, cy), (cx - R - 20, cy)], fill=DIM, width=3); d.line([(cx + R + 20, cy), (cx + R + 70, cy)], fill=DIM, width=3)
    text(img, f"{sc['ch']:02d}", 150, cx, cy, AMBER, u=min(1, u))
    text(img, sc["title"], 84, W / 2, 610, WHITE, u=ease((lt - 0.3) / 0.4))
    if "sub" in sc: note(img, sc["sub"], W / 2 - ImageDraw.Draw(img).textlength(sc["sub"], font=F(50, "Hand")) / 2, 705, ease((lt - 0.6) / 0.4), CYAN)
    return img

def b_text(sc, lt, dur, t):
    img = space(t)
    for i, s in enumerate(sc["lines"]):
        y = sc.get("y", 420) + i * sc.get("size", 96) * 1.2
        text(img, s, sc.get("size", 96), W / 2, y, AMBER if str(i) in sc.get("accent", {}) else WHITE, u=ease((lt - i * 0.35) / 0.4))
    return img

def b_counter(sc, lt, dur, t):
    img = space(t)
    v = sc["from"] + (sc["to"] - sc["from"]) * eout((lt - 0.2) / max(0.6, sc.get("secs", 2.0)))
    text(img, sc.get("prefix", "") + fmtnum(v, sc.get("fmt", "int")) + sc.get("suffix", ""), sc.get("size", 210), W / 2, 380, AMBER, u=ease(lt / 0.3))
    text(img, sc["label"], 62, W / 2, 560, WHITE, w="Bold", u=ease((lt - 0.3) / 0.4))
    if "note" in sc: text(img, sc["note"], 40, W / 2, 640, CYAN, w="SemiBold", u=ease((lt - 0.9) / 0.4))
    return img

def b_compare(sc, lt, dur, t):
    img = space(t); mx = max(sc["lv"], sc["rv"]); Lm = 880; cols = [COL[c] for c in sc.get("colors", ["cyan", "gold"])]
    for i, (lab, val, tx_, col) in enumerate(((sc["left"], sc["lv"], sc["lt"], cols[0]), (sc["right"], sc["rv"], sc["rt"], cols[1]))):
        y = 440 + i * 220; w = Lm * val / mx * eout((lt - 0.2 - i * 0.6) / 1.0)
        text(img, " ".join(lab), 54, 560, y, WHITE, w="Bold", anchor="rm", u=ease((lt - i * 0.6) / 0.3), maxw=480)
        d = ImageDraw.Draw(img)
        if w > 4: d.rounded_rectangle([600, y - 50, 600 + w, y + 50], 26, fill=col)
        if w > 4: text(img, tx_, 50, 600 + min(w, Lm - 260) + 30 if i == 0 else 600 + w - 30, y, INKD if i else col, anchor="lm" if i == 0 else "rm", u=ease((lt - 0.8 - i * 0.6) / 0.3), shadow=not i)
    if sc.get("pill") and lt > 1.8: pill(img, sc["pill"], 44, W / 2, 230, fill=AMBER, u=ease((lt - 1.8) / 0.4))
    return img

def b_stamp(sc, lt, dur, t):
    img = space(t); n = len(sc["lines"]); size = 96 if n > 1 else 110
    for i, s in enumerate(sc["lines"]): text(img, s, size, W / 2, 230 + i * size * 1.25, WHITE if i == 0 else AMBER, u=ease((lt - i * 0.25) / 0.35))
    at = 0.5 + n * 0.25; u = (lt - at) / 0.22; sc_col = {"red": RED, "green": GREEN}.get(sc.get("col"), AMBER)
    if u > 0:
        s = 1 + 1.4 * (1 - eout(u)); a = min(1, u * 2)
        st = Image.new("RGBA", (860, 300), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
        sd.rounded_rectangle([20, 40, 840, 260], 30, outline=sc_col + (int(255 * a),), width=16)
        txt = sc.get("stamp", "TRUE"); fs = 170
        while sd.textlength(txt, font=F(fs, "Black")) > 740: fs -= 6
        sd.text((430, 150), txt, font=F(fs, "Black"), fill=sc_col + (int(255 * a),), anchor="mm")
        st = st.rotate(-8, expand=True, resample=Image.BICUBIC); st = st.resize((int(st.width * s * 0.62), int(st.height * s * 0.62)), Image.BICUBIC)
        paste(img, st, W / 2, 270 + n * size * 1.25 + 130)
    return img

def b_recap(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img)
    text(img, "QUICK RECAP", 92, W / 2, 150, AMBER, u=1)
    n = len(sc["items"])
    for i, s in enumerate(sc["items"]):
        u = ease((lt - 0.3 - i * (dur - 1.0) / n) / 0.3); y = 310 + i * 130
        if u <= 0: continue
        d.rounded_rectangle([420, y - 32, 484, y + 32], 12, outline=CYAN, width=5)
        if u > 0.6: d.line([(432, y), (450, y + 20), (496, y - 36)], fill=GREEN, width=10)
        text(img, s, 60, 530, y, WHITE, anchor="lm", u=u, maxw=1250)
    return img

def b_outro(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img)
    text(img, sc.get("q", "Which one sounded the MOST fake?"), 74, W / 2, 240, WHITE)
    click = sc.get("click_at", 1.6); on = ease((lt - click) / 0.25); cx, cy, w_, h_ = W / 2, 440, 300, 130
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=AMBER if on > 0.5 else (40, 64, 110), outline=WHITE, width=6)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; d.ellipse([kx - h_ / 2 + 16, cy - h_ / 2 + 16, kx + h_ / 2 - 16, cy + h_ / 2 - 16], fill=WHITE)
    text(img, "FAKE", 60, cx - w_ / 2 - 110, cy, WHITE if on < 0.5 else DIM); text(img, "TRUE", 60, cx + w_ / 2 + 110, cy, AMBER if on >= 0.5 else DIM)
    pill(img, "SUBSCRIBE · NEW DEEP DIVE EVERY TUE & FRI", 40, W / 2, 640, fill=RED, ink=WHITE, u=ease((lt - click - 0.4) / 0.4))
    return img

def b_timeline(sc, lt, dur, t):
    img = space(t)
    a, b = sc["span"]; x0, x1 = 200, 1720; ay = 600
    X = lambda v: x0 + (x1 - x0) * (v - a) / (b - a)
    d = ImageDraw.Draw(img)
    d.line([(x0 - 40, ay), (x1 + 50, ay)], fill=(110, 150, 210), width=6)
    d.polygon([(x1 + 80, ay), (x1 + 46, ay - 18), (x1 + 46, ay + 18)], fill=(110, 150, 210))
    span = abs(b - a); step = [s for s in (1, 2, 5, 10, 20, 25, 50) if span / s <= 9][0]
    v = math.ceil(min(a, b) / step) * step
    while v <= max(a, b):
        x = X(v); d.line([(x, ay - 12), (x, ay + 12)], fill=(110, 150, 210), width=3)
        d.text((x, ay + 34), str(v), font=F(26, "SemiBold"), fill=(140, 170, 215), anchor="mm"); v += step
    ev = sc["events"]
    def appear(i): return ease((lt - 0.25 - i * 0.6) / 0.45)
    for j, (p, q, lab, c) in enumerate(sc.get("brackets", [])):
        ip = max(i for i, e in enumerate(ev) if e[0] in (p, q)); u = appear(ip)
        if u <= 0: continue
        col = COL[c]; by = ay + 120; xa, xb = X(p), X(q); xm = xa + (xb - xa) * eout(u); d = ImageDraw.Draw(img)
        d.line([(xa, by), (xm, by)], fill=col, width=6); d.line([(xa, by - 22), (xa, by + 22)], fill=col, width=6)
        if u > 0.95: d.line([(xb, by - 22), (xb, by + 22)], fill=col, width=6)
        text(img, lab, 54, (xa + xb) / 2, by + 62, col, u=ease((u - 0.6) / 0.4))
    for i, (v, lab, c) in enumerate(ev):
        u = appear(i)
        if u <= 0: continue
        col = COL[c]; x = X(v); p = (t * 1.0 + i * 0.3) % 1; rr = 14 + 40 * p; d = ImageDraw.Draw(img)
        d.ellipse([x - rr, ay - rr, x + rr, ay + rr], outline=lerpc(col, INKD, p), width=4)
        halo(img, x, ay, 30, col, 230); d = ImageDraw.Draw(img); d.ellipse([x - 13, ay - 13, x + 13, ay + 13], fill=WHITE)
        ly = ay - 120 - (110 if i % 2 else 0)
        d.line([(x, ay - 20), (x, ly + 34)], fill=col, width=3)
        pill(img, lab, 40, max(260, min(W - 260, x)), ly, fill=col, ink=INKD, u=u)
        text(img, str(v), 40, max(260, min(W - 260, x)), ly - 62, col, w="Bold", u=u)
    return img

# ---------------- beats: sketches ----------------
def b_sketch(sc, lt, dur, t):
    img = space(t); lines = sc.get("lines", []); notes = sc.get("notes", [])
    layer = reveal(ico(sc["icon"], sc.get("mode", ""), lt, t), eout(lt / 0.9))
    ix = 600 if lines or notes else W / 2
    paste(img, layer, ix, 560)
    if lines:
        tx0 = 1060; y0 = 380 - (len(lines) - 1) * 60 - (40 if notes else 0)
        for i, s in enumerate(lines):
            text(img, s, 96 if len(lines) > 1 else 110, tx0, y0 + i * 118, AMBER if i == len(lines) - 1 and len(lines) > 1 else WHITE, anchor="lm", u=ease((lt - 0.15 - i * 0.3) / 0.4), maxw=800)
        ny = y0 + len(lines) * 118 + 20
    else:
        tx0, ny = 1060, 380
    for k, s in enumerate(notes):
        note(img, "→ " + s, tx0, ny + k * 90, ease((lt - 0.8 - k * 0.6) / 0.5), CYAN if k % 2 else AMBER)
    return img

def candy(img, x, y, melt, t):
    d = ImageDraw.Draw(img); w, h = 420, 130
    d.rounded_rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], 18, fill=(110, 62, 36))
    d.rectangle([x - w / 2, y - h / 2, x - w / 2 + 170, y + h / 2], fill=(220, 60, 50)); d.rectangle([x - w / 2 + 170, y - h / 2, x - w / 2 + 180, y + h / 2], fill=(250, 220, 120))
    for k in range(3): d.rounded_rectangle([x - 20 + k * 62, y - 44, x + 30 + k * 62, y + 44], 10, outline=(80, 40, 24), width=4)
    if melt > 0:
        for k in range(6):
            dx = x - 30 + k * 40; L_ = (60 + 50 * ((k * 37) % 3)) * melt + 8 * math.sin(t * 2 + k) * melt
            d.rounded_rectangle([dx - 13, y + h / 2 - 10, dx + 13, y + h / 2 + L_], 13, fill=(110, 62, 36)); d.ellipse([dx - 17, y + h / 2 + L_ - 20, dx + 17, y + h / 2 + L_ + 14], fill=(110, 62, 36))
        d.ellipse([x - 50, y + h / 2 + 125 * melt, x + 190, y + h / 2 + 125 * melt + 30 * melt], fill=(96, 54, 30))

def b_hook(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img)
    for i, s in enumerate(sc["lines"]):
        text(img, s, 104, W / 2, 150 + i * 122, AMBER if i == 1 else WHITE, u=1.0 if (i == 0 or sc.get("plain") is None) and lt >= 2.9 else ease((lt - i * 0.3) / 0.35), maxw=1760)
    # magnetron (left), waves, candy bar in a pocket outline (right)
    mag = ico("magnetron", "", lt, t); paste(img, mag, 560, 690)
    note(img, "radar magnetron", 330, 935, 1.0, CYAN)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([1150, 520, 1650, 920], 40, outline=LINE, width=6); d.line([(1150, 600), (1650, 600)], fill=LINE, width=4)
    d.text((1400, 560), "POCKET", font=F(34, "Bold"), fill=DIM, anchor="mm")
    melt = ease((lt - 0.5) / 2.0)
    halo(img, 1400, 680, 220, (255, 140, 60), int(90 * melt))
    candy(img, 1400, 680, melt, t)
    return img

def b_tower(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img); base = 940; px_m = 430   # 1 m = 430 px
    # height scale
    d.line([(260, base), (260, base - 2 * px_m)], fill=DIM, width=4)
    for k in range(5):
        y = base - k * 0.5 * px_m; d.line([(240, y), (280, y)], fill=DIM, width=4); d.text((225, y), f"{k * 0.5:.1f} m", font=F(30, "SemiBold"), fill=DIM, anchor="rm")
    u = eout((lt - 0.2) / 1.2); hh = 1.8 * px_m * u
    x0 = 520; wv = 380
    if hh > 10:
        d.rectangle([x0, base - hh, x0 + wv, base], fill=(40, 80, 140), outline=LINE, width=6)
        d.rectangle([x0 + 40, base - hh + 40, x0 + wv - 40, base - hh + 40 + min(hh - 80, 300)], fill=(14, 30, 60), outline=LINE, width=4) if hh > 120 else None
        for k in range(int(hh // 60)):
            y = base - 40 - k * 40
            if y > base - hh + 380: d.line([(x0 + 40, y), (x0 + wv - 40, y)], fill=(120, 160, 220), width=3)
    text(img, "THE FIRST MICROWAVE", 46, x0 + wv / 2, base - hh - 50, AMBER, w="Bold", u=ease((lt - 1.2) / 0.4))
    # person silhouette 1.75 m
    pxh = 1.75 * px_m; cx = 1180; d = ImageDraw.Draw(img); col = (150, 180, 220)
    hr = pxh * 0.065; d.ellipse([cx - hr, base - pxh, cx + hr, base - pxh + 2 * hr], fill=col)
    d.rounded_rectangle([cx - pxh * 0.12, base - pxh + 2.2 * hr, cx + pxh * 0.12, base - pxh * 0.47], 30, fill=col)
    d.rounded_rectangle([cx - pxh * 0.11, base - pxh * 0.5, cx - pxh * 0.015, base], 18, fill=col); d.rounded_rectangle([cx + pxh * 0.015, base - pxh * 0.5, cx + pxh * 0.11, base], 18, fill=col)
    d.rounded_rectangle([cx - pxh * 0.17, base - pxh + 2.4 * hr, cx - pxh * 0.12, base - pxh * 0.5], 14, fill=col); d.rounded_rectangle([cx + pxh * 0.12, base - pxh + 2.4 * hr, cx + pxh * 0.17, base - pxh * 0.5], 14, fill=col)
    text(img, "A PERSON", 40, cx, base - pxh - 50, (180, 200, 230), w="Bold")
    d.line([(100, base), (1820, base)], fill=LINE, width=5)
    pill(img, "≈ 6 FT TALL", 50, 1580, 380, fill=AMBER, u=ease((lt - 1.6) / 0.4))
    pill(img, "≈ 750 LB", 50, 1580, 520, fill=CYAN, u=ease((lt - 3.2) / 0.4))
    return img

def b_ecg(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img)
    for i, s in enumerate(sc["lines"]): text(img, s, 96, W / 2, 140 + i * 112, AMBER if i == 1 else WHITE, u=ease((lt - i * 0.3) / 0.35))
    x0, x1, y0, y1 = 220, 1700, 400, 900
    d.rounded_rectangle([x0, y0, x1, y1], 30, fill=(6, 26, 22), outline=LINE, width=6)
    for x in range(x0 + 40, x1, 60): d.line([(x, y0 + 10), (x, y1 - 10)], fill=(20, 70, 50), width=1)
    for y in range(y0 + 40, y1, 60): d.line([(x0 + 10, y), (x1 - 10, y)], fill=(20, 70, 50), width=1)
    cy = 680; head = x0 + 20 + ((lt * 520) % (x1 - x0 - 40)); pts = []
    for x in range(x0 + 20, int(head)):
        ph = ((x - x0) % 300) / 300
        y = cy - (220 * math.exp(-((ph - 0.5) * 40) ** 2) - 50 * math.exp(-((ph - 0.56) * 30) ** 2) + 30 * math.exp(-((ph - 0.75) * 12) ** 2))
        pts.append((x, y))
    if len(pts) > 2:
        d.line(pts, fill=(120, 255, 160), width=6); d.ellipse([pts[-1][0] - 10, pts[-1][1] - 10, pts[-1][0] + 10, pts[-1][1] + 10], fill=WHITE)
    return img

def bone(d, a, b, w, col):
    d.line([a, b], fill=col, width=int(w));
    for p in (a, b): d.ellipse([p[0] - w * 0.75, p[1] - w * 0.75, p[0] + w * 0.75, p[1] + w * 0.75], fill=col)

def xray_hand(img, cx, base, s, u_ring=1.0, glow=1.0):
    """Glowing X-ray of an open hand: metacarpals + phalanges, with a ring on the ring finger."""
    d = ImageDraw.Draw(img); col = lerpc((20, 40, 70), (200, 236, 255), glow)
    # faint flesh outline
    fl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fd = ImageDraw.Draw(fl)
    hand_outline(fd, cx, base, s * 1.12, (80, 140, 200, 140), (60, 110, 170, 70)); img.paste(fl, (0, 0), fl); d = ImageDraw.Draw(img)
    wrist = (cx, base + 10 * s)
    fingers = [(-0.36, 190), (-0.12, 230), (0.12, 215), (0.36, 170)]; pw = 230 * s * 1.12; top = base - 220 * s * 1.12
    for i, (fx, fl_) in enumerate(fingers):
        kx = cx + fx * pw; k = (kx, top + 30 * s); bone(d, (cx + fx * 50 * s, base - 20 * s), k, 18 * s, col)
        segs = [0.45, 0.32, 0.23]; y = k[1]; Lf = fl_ * s * 1.12 + 30 * s
        for j, f in enumerate(segs):
            y2 = y - Lf * f; bone(d, (kx, y - 8 * s), (kx, y2 + 8 * s), (15 - j * 3) * s, col);
            if i == 2 and j == 0 and u_ring > 0:
                ry = (y + y2) / 2; d.ellipse([kx - 30 * s, ry - 12 * s, kx + 30 * s, ry + 12 * s], outline=AMBER, width=int(12 * s))
            y = y2
    tb = (cx - pw / 2 + 20 * s, base - 70 * s)
    bone(d, (cx - 40 * s, base - 10 * s), tb, 18 * s, col)
    bone(d, tb, (cx - pw / 2 - 70 * s, top + 40 * s), 16 * s, col); bone(d, (cx - pw / 2 - 70 * s, top + 40 * s), (cx - pw / 2 - 100 * s, top - 10 * s), 13 * s, col)
    for k in range(6): d.ellipse([cx - 70 * s + k * 26 * s, base - 10 * s, cx - 46 * s + k * 26 * s, base + 18 * s], fill=col)
    bone(d, (cx - 40 * s, base + 30 * s), (cx - 50 * s, base + 160 * s), 26 * s, col); bone(d, (cx + 40 * s, base + 30 * s), (cx + 50 * s, base + 160 * s), 22 * s, col)

def b_xray(sc, lt, dur, t):
    img = space(t, grid=False); d = ImageDraw.Draw(img)
    d.rounded_rectangle([560, 60, 1360, 1010], 24, fill=(4, 10, 20), outline=LINE, width=6)
    g = ease((lt - 0.2) / 1.0); xray_hand(img, 960, 700, 1.25, u_ring=ease((lt - 1.5) / 0.3), glow=g)
    note(img, "→ his wife's hand", 1420, 380, ease((lt - 0.8) / 0.5), CYAN)
    note(img, "→ her ring!", 1420, 480, ease((lt - 1.8) / 0.5), AMBER)
    text(img, "1895", 90, 300, 200, AMBER, u=ease(lt / 0.4))
    return img

def b_shoe(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img)
    text(img, "SHOE STORES", 96, W / 2, 130, WHITE, u=ease(lt / 0.35)); text(img, "X-RAYED YOUR FEET", 96, W / 2, 240, AMBER, u=ease((lt - 0.3) / 0.35))
    # dark viewer panel with a shoe outline and glowing foot bones
    d.rounded_rectangle([430, 330, 1490, 850], 30, fill=(4, 10, 20), outline=LINE, width=6)
    g = ease((lt - 0.6) / 0.8); bc = lerpc((20, 40, 70), (200, 236, 255), g)
    shoe = [(560, 780), (560, 660), (640, 580), (820, 560), (980, 600), (1180, 660), (1320, 700), (1360, 760), (1340, 800), (560, 800)]
    d.line(shoe + [shoe[0]], fill=(90, 150, 210), width=8, joint="curve")
    # bones: heel, ankle, five metatarsals + toes
    d.ellipse([590, 680, 720, 780], fill=bc); d.ellipse([700, 620, 800, 700], fill=bc)
    for k in range(5):
        a0 = (790, 660 + k * 14); a1 = (1110 + k * 10, 680 + k * 22); bone(d, a0, a1, 16 - k, bc)
        bone(d, (a1[0] + 20, a1[1]), (a1[0] + 120 - k * 14, a1[1] + 6), 12 - k, bc)
    pill(img, "1920s – 1950s", 44, W / 2, 905, fill=CYAN, u=ease((lt - 1.4) / 0.4))
    return img

def b_bigbang(sc, lt, dur, t):
    img = space(t, grid=False); d = ImageDraw.Draw(img); cx, cy = W / 2, 560
    p = eout(lt / 3.0)
    for k in range(5):
        r = (lt * 160 + k * 160) % 800; a = max(0, 1 - r / 800)
        d.ellipse([cx - r, cy - r * 0.8, cx + r, cy + r * 0.8], outline=lerpc((6, 20, 48), (255, 170, 90), a * 0.8), width=4)
    halo(img, cx, cy, 120 + 60 * math.sin(t * 2), (255, 200, 120), 200)
    rr = random.Random(4)
    d = ImageDraw.Draw(img)
    for k in range(260):
        a = rr.uniform(0, 6.28); r = rr.uniform(30, 900) * p; s = rr.uniform(1.5, 4)
        x, y = cx + r * math.cos(a), cy + r * 0.8 * math.sin(a)
        d.ellipse([x - s, y - s, x + s, y + s], fill=lerpc((255, 220, 160), (120, 160, 255), min(1, r / 700)))
    text(img, "THE AFTERGLOW", 104, W / 2, 140, WHITE, u=ease((lt - 0.4) / 0.4)); text(img, "OF THE BIG BANG", 104, W / 2, 260, AMBER, u=ease((lt - 0.8) / 0.4))
    return img

def b_tv(sc, lt, dur, t):
    img = space(t); d = ImageDraw.Draw(img)
    text(img, "OLD TV STATIC", 96, W / 2, 110, WHITE, u=ease(lt / 0.35))
    x0, y0, x1, y1 = 560, 330, 1340, 790
    d.rounded_rectangle([x0 - 40, y0 - 40, x1 + 200, y1 + 40], 50, fill=(90, 62, 40), outline=LINE, width=6)
    for k in range(2): d.ellipse([x1 + 70, y0 + 60 + k * 140, x1 + 150, y0 + 140 + k * 140], fill=(50, 36, 24), outline=(200, 180, 150), width=4)
    d.line([(x0 + 330, y0 - 40), (x0 + 250, y0 - 140)], fill=LINE, width=6); d.line([(x0 + 430, y0 - 40), (x0 + 520, y0 - 140)], fill=LINE, width=6)
    fi = int(t * 30); nz = np.random.default_rng(fi).random(((y1 - y0) // 4, (x1 - x0) // 4)).astype(np.float32)
    rgb = np.stack([nz * 235] * 3, -1)
    frac = ease((lt - 1.2) / 0.6)
    if frac > 0:   # tint a small fraction of the specks amber: 'a small fraction is the Big Bang'
        m = (np.random.default_rng(fi + 7).random(nz.shape) < 0.03) & (nz > 0.45)
        rgb[m] = np.array([255, 170, 60]) * (0.4 + 0.6 * frac)
    scr = Image.fromarray(rgb.astype(np.uint8)).resize((x1 - x0, y1 - y0), Image.NEAREST)
    mask = Image.new("L", scr.size, 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, scr.width, scr.height], 60, fill=255)
    img.paste(scr, (x0, y0), mask)
    pill(img, "A SMALL FRACTION = THE BIG BANG'S AFTERGLOW", 40, W / 2, 895, fill=AMBER, u=frac)
    return img

BEATS = dict(cold=b_cold, chapter=b_chapter, text=b_text, counter=b_counter, compare=b_compare, stamp=b_stamp, recap=b_recap, outro=b_outro,
             timeline=b_timeline, sketch=b_sketch, hook=b_hook, tower=b_tower, ecg=b_ecg, xray=b_xray, shoe=b_shoe, bigbang=b_bigbang, tv=b_tv)
NOBLOOM = ("tv", "shoe")

# ---------------- narration & score (warm pads + soft plucks + gentle pencil ticks) ----------------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.42, tail=1.5)
n = len(voice); tt = np.arange(n) / SR; music = np.zeros(n, np.float32)
pads = [[130.81, 196.0, 261.63, 329.63], [110.0, 164.81, 220.0, 277.18], [116.54, 174.61, 233.08, 293.66], [98.0, 146.83, 196.0, 246.94]]
seg = 6.0
for i in range(int(total / seg) + 1):
    a, b = int(i * seg * SR), min(int((i + 1.4) * seg * SR), n)
    if a >= n: break
    lt = tt[a:b] - i * seg; env = np.clip(lt / 2.5, 0, 1) * np.clip((seg * 1.4 - lt) / 2.5, 0, 1)
    for f in pads[i % 4]: music[a:b] += (np.sin(2 * np.pi * f * lt) + 0.3 * np.sin(2 * np.pi * f * 1.004 * lt)) * env * 0.028
scale = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5]
for k in range(int(total * 1.0)):
    if k % 2 == 0: place(music, k * 0.5 * 2 + 0.25, tone(random.choice(scale), 0.9, decay=6, harm=(1, 2)), 0.018)
hook_hit(music, 0.35)
for ln in spec["lines"]:
    if ln["scene"]["type"] == "chapter": place(music, ln["_s"], tone(65.4, 1.2, decay=3, harm=(1, 2)), 0.25); whoosh(music, ln["_s"], 0.18)
    if ln["scene"]["type"] == "stamp": place(music, ln["_s"] + 0.5 + 0.25 * len(ln["scene"]["lines"]), tone(70, 0.4, decay=14, harm=(1, 2, 3)), 0.35)
for ln in spec["lines"][1:]: whoosh(music, ln["_s"], 0.06)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.35)

cur_ch = 0
for ln in spec["lines"]:
    if ln["scene"]["type"] == "chapter": cur_ch = ln["scene"]["ch"]
    ln["_ch"] = cur_ch
NCH = max(ln["_ch"] for ln in spec["lines"])
def _ts(x): x = int(x); return f"{x // 60}:{x % 60:02d}"
_chap = ["0:00 Intro"] + [f"{_ts(ln['_s'])} {ln['scene']['ch']}. {' '.join(w_.capitalize() for w_ in ln['scene']['title'].split())}" for ln in spec["lines"] if ln["scene"]["type"] == "chapter"]
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
        d.text((x, y), w, font=f, fill=AMBER if on else WHITE); x += d.textlength(w + " ", font=f)

def frame(t):
    ln = core.active_line(spec, t, lead=0.05) or spec["lines"][0]
    lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]; sc = ln["scene"]
    if t < 0.05: lt = 3.0                                                                       # frame 0 = full hook
    img = BEATS[sc["type"]](sc, lt, dur, t)
    if sc["type"] not in NOBLOOM: img = bloom(img, 0.35)
    d = ImageDraw.Draw(img)
    if ln["_ch"]: d.text((W - 60, 50), f"{ln['_ch']:02d} / {NCH:02d}", font=F(34, "Bold"), fill=AMBER, anchor="ra")
    d.rounded_rectangle([44, 40, 330, 92], 22, fill=INKD); d.text((62, 48), "SOUNDS FAKE  ?!", font=F(30, "Black"), fill=(230, 236, 246))
    caption(img, t)
    d.rectangle([0, H - 6, int(W * t / total), H], fill=AMBER)
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","):
            Image.frombytes("RGB", (W, H), frame(float(tt_))).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s")
        for ln in spec["lines"]: print(f"{ln['_s']:7.1f} {ln['scene']['type']:10s} {ln['scene'].get('icon', '')} {ln['scene'].get('mode', '')}")
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
