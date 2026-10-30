"""Day 02 — TRAIL CAMERA style (wombats are nocturnal: up to 100 cubes a night).
Infrared night-vision wildlife footage: green-grey grain, IR illuminator falloff, eyeshine, camera HUD
(REC, timestamp, temperature), motion-detection boxes, 'ENHANCE' digital zoom, time-lapse, lab-scan overlay.
Usage: python3 engine/styles/day02_trailcam.py spec.json out.mp4 [t1,t2,... preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
rng = np.random.default_rng(2); random.seed(2)
_M = next((p for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf") if os.path.exists(p)), None)
FDI = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
MONO = (lambda s: ImageFont.truetype(_M, s)) if _M else (lambda s: ImageFont.truetype(FDI + "InterDisplay-Bold.otf", s))
TINT = np.array([0.62, 1.0, 0.70], np.float32)          # night-vision green-grey
HUDC = 235                                               # HUD drawn in near-white luminance

# ---------------- film: grain, IR falloff, scanlines ----------------
GRAIN = [rng.normal(0, 1, (H, W)).astype(np.float32) for _ in range(6)]
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
IR = np.clip(1.15 - 0.85 * np.sqrt(((xx - W * 0.5) / (W * 0.85)) ** 2 + ((yy - H * 0.58) / (H * 0.55)) ** 2), 0.12, 1.0)
SCAN = (1 - 0.06 * (np.arange(H) % 4 < 2)).astype(np.float32)[:, None]

def finish(L, t, fi, grain=0.075):
    """L: float luminance 0..1 (H,W). -> RGB bytes with tint, grain, scanlines."""
    L = np.clip(L * 1.22, 0, 1) * SCAN + GRAIN[fi % 6] * grain
    rgb = np.clip(L[..., None] * TINT * 255, 0, 255)
    return rgb.astype(np.uint8).tobytes()

# ---------------- world pieces (drawn in luminance, 'L' images) ----------------
def ground(d, horizon=1050, seed=0):
    r = random.Random(seed)
    d.rectangle([0, 0, W, horizon], fill=18)                                   # dark bush line / sky
    for k in range(14):                                                        # bush silhouettes
        x = r.uniform(-80, W + 80); s = r.uniform(120, 260)
        d.ellipse([x - s, horizon - s * 0.9, x + s, horizon + s * 0.3], fill=r.randint(26, 40))
    d.rectangle([0, horizon, W, H], fill=70)                                   # lit ground
    for k in range(900):                                                       # dirt speckle
        x, y = r.uniform(0, W), r.uniform(horizon, H); g = r.randint(45, 105)
        d.ellipse([x - 3, y - 2, x + 3, y + 2], fill=g)
    for k in range(70):                                                        # grass tufts in front
        x = r.uniform(0, W); y = r.uniform(horizon + 300, H)
        for j in range(5):
            d.line([(x + j * 6, y), (x + j * 6 + r.uniform(-20, 20), y - r.uniform(40, 110))], fill=r.randint(110, 170), width=4)

def wombat(d, x, y, s=1.0, step=0.0, face=1):
    """Chunky wombat silhouette, IR-lit. x,y = feet center. Eyes glow (eyeshine)."""
    lift = abs(math.sin(step)) * 8 * s
    d.ellipse([x - 170 * s, y - 210 * s - lift, x + 150 * s, y - 20 * s - lift], fill=150)        # body
    hx = x + face * 140 * s
    d.ellipse([hx - 95 * s, y - 200 * s - lift, hx + 95 * s, y - 60 * s - lift], fill=165)        # head
    d.ellipse([hx + face * 40 * s - 45 * s, y - 150 * s - lift, hx + face * 40 * s + 45 * s, y - 85 * s - lift], fill=175)  # nose
    for ex in (-40, 10):
        ex2 = hx + face * ex * s
        d.ellipse([ex2 - 22 * s, y - 230 * s - lift, ex2 + 22 * s, y - 175 * s - lift], fill=140)  # ears
    for k, lx in enumerate((-110, -40, 50, 110)):                                               # legs
        sw = math.sin(step + k * 1.6) * 14 * s
        d.rounded_rectangle([x + lx * s - 26 * s + sw, y - 60 * s, x + lx * s + 26 * s + sw, y], 12, fill=120)
    ex = hx + face * 25 * s
    d.ellipse([ex - 13 * s, y - 165 * s - lift, ex + 13 * s, y - 139 * s - lift], fill=255)      # eyeshine

def cube(d, x, y, s=26, fill=200):
    """Small iso cube (top, left, right faces)."""
    d.polygon([(x, y - s), (x + s, y - s * 0.5), (x, y), (x - s, y - s * 0.5)], fill=min(255, fill + 40))
    d.polygon([(x - s, y - s * 0.5), (x, y), (x, y + s), (x - s, y + s * 0.5)], fill=fill - 30)
    d.polygon([(x + s, y - s * 0.5), (x, y), (x, y + s), (x + s, y + s * 0.5)], fill=fill - 70)

def rock(d, x, y, w=420):
    d.polygon([(x - w / 2, y), (x - w * 0.38, y - 150), (x - w * 0.1, y - 190), (x + w * 0.3, y - 170), (x + w / 2, y)], fill=95)
    d.line([(x - w * 0.38, y - 150), (x - w * 0.1, y - 190), (x + w * 0.3, y - 170)], fill=130, width=6)

def bracket(d, x0, y0, x1, y1, label=None, c=HUDC, L=40, w=5):
    for (cx, cy, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([(cx, cy), (cx + sx * L, cy)], fill=c, width=w); d.line([(cx, cy), (cx, cy + sy * L)], fill=c, width=w)
    if label:
        f = MONO(30); tw = d.textlength(label, font=f)
        d.rectangle([x0, y0 - 46, x0 + tw + 20, y0 - 6], fill=c); d.text((x0 + 10, y0 - 42), label, font=f, fill=10)

def hud(d, t, mode="IR", clock_s=None, temp="11°C"):
    d.rectangle([0, 0, W, 200], fill=0); d.rectangle([0, H - 210, W, H], fill=0)
    if int(t * 2) % 2 == 0: d.ellipse([60, 80, 92, 112], fill=255)
    d.text((110, 74), "REC", font=MONO(40), fill=HUDC)
    d.text((W - 60, 74), f"CAM 03 · {mode}", font=MONO(40), fill=HUDC, anchor="ra")
    s = clock_s if clock_s is not None else 2 * 3600 + 14 * 60 + int(t)
    hh, mm, ss = int(s // 3600) % 24, int(s % 3600 // 60), int(s % 60)
    d.text((60, 140), f"2026-10-30  {hh:02d}:{mm:02d}:{ss:02d}", font=MONO(34), fill=150)
    d.text((W - 60, 140), f"{temp}  ☾", font=MONO(34), fill=150, anchor="ra")

def headline(d, lines, lt, y0=330, size=92, inv=None):
    for i, txt in enumerate(lines):
        n = int(len(txt) * min(1, max(0, (lt - i * 0.35) / 0.45)))     # typewriter
        if n <= 0: continue
        sz = size
        while d.textlength(txt, font=MONO(sz)) > W - 140 and sz > 40: sz -= 4
        f = MONO(sz); part = txt[:n]; tw = d.textlength(txt, font=f); x = (W - tw) / 2; y = y0 + i * (size + 30)
        hi = inv is not None and str(i) in inv
        d.rectangle([x - 22, y - 12, x + tw + 22, y + sz + 16], fill=HUDC if hi else 0)
        d.text((x, y), part + ("▌" if n < len(txt) and int(lt * 6) % 2 else ""), font=f, fill=0 if hi else HUDC)

def new_L(): return Image.new("L", (W, H), 0)
def to_arr(img): return np.asarray(img).astype(np.float32) / 255

# ---------------- narration & music ----------------
voice, words, total = narrate(spec, default_gap=0.25)
n = len(voice); tt = np.arange(n) / SR; music = np.zeros(n, np.float32)
for k in range(int(total * 2.2)):                       # crickets: rapid chirp pulses
    at = random.uniform(0, total); f = random.choice([4200, 4700, 5100])
    ch = np.arange(int(0.18 * SR)) / SR
    place(music, at, np.sin(2 * np.pi * f * ch) * (np.sin(2 * np.pi * 45 * ch) > 0.3) * np.exp(-ch * 9), 0.010)
music += 0.04 * np.sin(2 * np.pi * 55 * tt) * (0.5 + 0.5 * np.sin(2 * np.pi * tt / 6))
for k in range(int(total / 1.0)):                       # soft synth pulse
    place(music, k * 1.0, tone([110, 130.81, 98, 110][k % 4], 0.9, decay=4, harm=(1, 2)), 0.05)
    if k % 2: place(music, k * 1.0 + 0.5, tone(440, 0.25, decay=14, harm=(1,)), 0.015)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.35)

# ---------------- scenes (return luminance image) ----------------
BASE = new_L(); ground(ImageDraw.Draw(BASE)); BASE_A = None

def sc_hook(sc, lt, dur, t):
    img = BASE.copy(); d = ImageDraw.Draw(img)
    x = -300 + 990 * eout(lt / 0.9); wombat(d, x, 1420, 1.15, step=lt * 9 if lt < 0.9 else 0)
    if lt > 0.75:
        u = ease((lt - 0.75) / 0.25); cube(d, x - 260, 1440, 32 * u)
        bracket(d, x - 315, 1370, x - 205, 1495, "CUBE? 99%" if lt > 1.0 else None)
    bracket(d, x - 215, 1140, x + 310, 1440, "WOMBAT 98%")
    headline(d, sc["lines"], lt, inv=sc.get("inv"))
    return img

def sc_enhance(sc, lt, dur, t):
    img = BASE.copy(); d = ImageDraw.Draw(img); wombat(d, 690, 1420, 1.15); cube(d, 430, 1440, 32)
    z = 1 + 4 * ease(lt / 0.9); cx, cy = 690 + (430 - 690) * ease(lt / 0.9), 1300 + 140 * ease(lt / 0.9)
    crop = img.crop((cx - W / (2 * z), cy - H / (2 * z), cx + W / (2 * z), cy + H / (2 * z)))
    px = max(1, int(14 * min(1, lt / 0.3) * (1 - ease((lt - 0.9) / 0.6))))
    small = crop.resize((max(1, W // px), max(1, H // px)), Image.BILINEAR)
    img = small.resize((W, H), Image.NEAREST if px > 1 else Image.BILINEAR); d = ImageDraw.Draw(img)
    d.text((60, 240), f"ENHANCE ×{z:.1f}", font=MONO(40), fill=HUDC)
    for i, (lab, ok) in enumerate((("ROUND", False), ("LUMPY", False), ("CUBE", True))):
        if lt > 0.5 + i * 0.55:
            y = 1250 + i * 80; f = MONO(52)
            d.rectangle([90, y, 520, y + 66], fill=HUDC if ok else 0)
            d.text((110, y + 4), f"[{'X' if ok else ' '}] {lab}", font=f, fill=0 if ok else HUDC)
    return img

def sc_timelapse(sc, lt, dur, t):
    img = BASE.copy(); d = ImageDraw.Draw(img); rock(d, 540, 1350, 520)
    p = ease((lt - 0.2) / max(0.8, dur - 0.6)); n = int(sc.get("count", 100) * p)
    for k in range(min(n, 18)):                                   # visible stack on the rock
        r, c = divmod(k, 6); cube(d, 400 + c * 56 + (r % 2) * 28, 1180 - r * 46, 24)
    for k in range(max(0, n - 18)):                               # scattered around
        rr = random.Random(k); cube(d, rr.uniform(80, W - 80), rr.uniform(1420, 1640), 18, fill=rr.randint(150, 200))
    d.rectangle([60, 240, 640, 320], fill=HUDC); d.text((80, 252), f"TIMELAPSE ×600", font=MONO(48), fill=0)
    d.text((W / 2, 520), f"{n:03d}", font=MONO(220), fill=HUDC, anchor="mm")
    d.text((W / 2, 660), "CUBES TONIGHT", font=MONO(50), fill=150, anchor="mm")
    return img, 2 * 3600 + int(p * 6.5 * 3600)

def sc_unknown(sc, lt, dur, t):
    img = BASE.copy(); d = ImageDraw.Draw(img)
    jitter = random.Random(int(t * 15)).randint(-14, 14) if int(t * 4) % 3 == 0 else 0
    d.text((W / 2 + jitter, 760), "?", font=MONO(420), fill=HUDC, anchor="mm")
    d.rectangle([140, 1060, W - 140, 1150], fill=0); d.text((W / 2, 1105), "ANALYSIS: UNKNOWN", font=MONO(56), fill=HUDC, anchor="mm")
    return img

def tube(d, cx, cy, lt, morph, labels=True):
    d.rectangle([0, 0, W, H], fill=14)
    for x in range(0, W, 60): d.line([(x, 0), (x, H)], fill=30)
    for y in range(0, H, 60): d.line([(0, y), (W, y)], fill=30)
    d.rectangle([40, cy - 300, W - 40, cy - 250], fill=200); d.rectangle([40, cy + 250, W - 40, cy + 300], fill=200)
    for i in range(6):
        x = 60 + i * 165; stiff = i % 2 == 0
        d.rectangle([x, cy - 250, x + 150, cy - 205 if stiff else cy - 232], fill=255 if stiff else 120)
        d.rectangle([x, cy + (205 if stiff else 232), x + 150, cy + 250], fill=255 if stiff else 120)
    r = 175; rad = r * (1 - 0.95 * morph); bx = cx - 260 + 260 * ease(lt / 1.0)
    d.rounded_rectangle([bx - r, cy - r, bx + r, cy + r], rad, fill=170, outline=255, width=6)
    if labels:
        d.text((90, cy - 420), "▮ STIFF", font=MONO(52), fill=255); d.text((W - 90, cy - 420), "▯ STRETCHY", font=MONO(52), fill=150, anchor="ra")

def sc_scan(sc, lt, dur, t):
    img = new_L(); d = ImageDraw.Draw(img); cy = 950
    tube(d, W / 2, cy, lt, 0.0, labels=False)
    sy = 240 + (lt * 520) % (H - 480); d.rectangle([0, sy, W, sy + 10], fill=230)
    d.rectangle([60, 240, 700, 320], fill=HUDC); d.text((80, 252), "LAB SCAN · INTESTINE", font=MONO(48), fill=0)
    return img

def sc_squeeze(sc, lt, dur, t):
    img = new_L(); d = ImageDraw.Draw(img); cy = 950
    m = ease((lt - 0.6) / max(0.8, dur - 1.3)); tube(d, W / 2, cy, lt, m)
    if m > 0.85: d.text((W / 2, cy + 420), "→ CORNERS", font=MONO(84), fill=255, anchor="mm")
    return img

def sc_rock(sc, lt, dur, t):
    img = BASE.copy(); d = ImageDraw.Draw(img); rock(d, 540, 1350, 560)
    for k, (x, y) in enumerate(((470, 1180), (560, 1180), (515, 1132))):
        u = back((lt - k * 0.25) / 0.3)
        if u > 0: cube(d, x, y - (1 - u) * 300, 32)
    p = ease((lt - 1.0) / 1.2)
    if lt > 0.4:
        bx = 680 + p * 520; by = 1150 + (p ** 2) * 420 if p > 0.12 else 1150
        d.ellipse([bx - 34, by - 34, bx + 34, by + 34], fill=190)
        if p > 0.3: bracket(d, bx - 60, by - 60, bx + 60, by + 60, "ROLLED AWAY")
    bracket(d, 420, 1060, 610, 1215, "STAYS PUT")
    headline(d, sc.get("lines", ["MARKS ITS TURF"]), lt, y0=330, size=80)
    return img

def sc_alert(sc, lt, dur, t):
    img = BASE.copy(); d = ImageDraw.Draw(img); d.rectangle([0, 0, W, H], fill=10)
    on = int(lt * 4) % 2 == 0 or lt > 1.0
    d.rectangle([80, 620, W - 80, 1200], outline=HUDC, width=8)
    if on: d.rectangle([80, 620, W - 80, 720], fill=HUDC)
    d.text((W / 2, 670), "! ALERT", font=MONO(64), fill=0 if on else HUDC, anchor="mm")
    u = ease((lt - 0.4) / 0.4)
    if u > 0:
        cx, cy = W / 2, 900                                           # line-art trophy
        d.arc([cx - 90, cy - 120, cx + 90, cy + 40], 0, 180, fill=HUDC, width=10)
        d.line([(cx - 90, cy - 40), (cx + 90, cy - 40)], fill=HUDC, width=10)
        d.line([(cx, cy + 40), (cx, cy + 100)], fill=HUDC, width=10); d.line([(cx - 60, cy + 100), (cx + 60, cy + 100)], fill=HUDC, width=10)
        d.text((W / 2, 1080), sc.get("text", "IG NOBEL PRIZE · 2019"), font=MONO(56), fill=HUDC, anchor="mm")
    return img

def sc_end(sc, lt, dur, t):
    img = BASE.copy(); d = ImageDraw.Draw(img); d.rectangle([0, 0, W, H], fill=12)
    click = sc.get("click_at", 0.9); on = ease((lt - click) / 0.25)
    cx, cy, w_, h_ = W / 2, 980, 340, 150
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, outline=HUDC, width=8, fill=HUDC if on > 0.5 else 0)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on
    d.ellipse([kx - h_ / 2 + 18, cy - h_ / 2 + 18, kx + h_ / 2 - 18, cy + h_ / 2 - 18], fill=0 if on > 0.5 else HUDC)
    d.text((cx - w_ / 2 - 40, cy), "FAKE", font=MONO(64), fill=HUDC if on < 0.5 else 90, anchor="rm")
    d.text((cx + w_ / 2 + 40, cy), "TRUE", font=MONO(64), fill=HUDC if on >= 0.5 else 90, anchor="lm")
    if lt > click + 0.3: headline(d, ["SOUNDS FAKE ?!"], lt - click - 0.3, y0=560, size=96, inv={"0": 1})
    return img

SCENES = dict(hook=sc_hook, enhance=sc_enhance, timelapse=sc_timelapse, unknown=sc_unknown, scan=sc_scan,
              squeeze=sc_squeeze, rock=sc_rock, alert=sc_alert, end=sc_end)
MODES = dict(scan="LAB", squeeze="LAB", alert="SYS", end="SYS")

# ---------------- captions: HUD subtitles ----------------
groups = caption_groups(words, 3)
def caption(d, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0].upper() for i in g]; size = 56
    while d.textlength(" ".join(ws), font=MONO(size)) > W - 140 and size > 34: size -= 4
    f = MONO(size); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1560
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05; ww = d.textlength(w, font=f)
        d.rectangle([x - 8, y - 6, x + ww + 8, y + size + 10], fill=HUDC if on else 0)
        d.text((x, y), w, font=f, fill=0 if on else HUDC)
        x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t); clock_s = None; mode = "IR"
    if ln is None: img = BASE.copy()
    else:
        lt = t - ln["_s"]; dur = ln["_se"] - ln["_s"]; sc = ln["scene"]
        r = SCENES[sc["type"]](sc, lt, dur, t)
        img, clock_s = r if isinstance(r, tuple) else (r, None)
        mode = MODES.get(sc["type"], "IR")
        if lt < 0.12: img = Image.new("L", (W, H), 0)                 # hard camera cut
    L = to_arr(img)
    if mode == "IR": L = L * IR
    d = ImageDraw.Draw(img2 := Image.fromarray((np.clip(L, 0, 1) * 255).astype(np.uint8)))
    hud(d, t, mode, clock_s); caption(d, t)
    d.rectangle([0, H - 10, int(W * t / total), H], fill=HUDC)
    return finish(to_arr(img2), t, fi)

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","):
            Image.frombytes("RGB", (W, H), frame(float(tt_), int(float(tt_) * 30))).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=28)
        print(f"done {total:.1f}s")
