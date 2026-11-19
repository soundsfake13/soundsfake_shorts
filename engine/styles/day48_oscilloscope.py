"""Day 48 — OSCILLOSCOPE style (sound travels ~4x faster in water than in air).
A 1970s bench oscilloscope fills the frame: warm putty-grey instrument panel with a fine brushed texture, black bezel,
round-cornered CRT with an 8x8 graticule (minor ticks on the centre axes), faint scanlines, vignette and a glass sheen.
Everything that happens is drawn by the electron beam: phosphor-green traces (CH1 = AIR) and amber traces (CH2 = WATER)
rendered as additive light with a white-hot core, two-radius bloom and a short persistence trail. Type on the screen is
VT323 (CRT terminal) glowing like the traces; the panel uses Barlow Condensed engraved labels.
Panel chrome: header plate, four knobs (TIME/DIV, CH1 AIR, CH2 WATER, INTENSITY) whose pointers click to new positions
on every scene, channel LEDs, BNC jacks and a power switch.
Scenes: dual-trace hook with pulses racing in two lanes, mystery CH3, AIR counter + scrolling sine, WATER counter with a
4.3x longer wavelength, 1 km race with timers, longitudinal 'squeeze' particle lanes, segmented bar graph (air / water /
steel) with x17, and a phosphor slide switch FAKE -> TRUE that fades back into the hook screen for the loop.
Scene changes are a CRT collapse: the picture squashes to a bright horizontal line and snaps open again.
Music: original A-minor synth pulse (sine bass + filtered square arpeggio) over a soft mains hum, sonar pings on cuts,
counter ticks, race sweeps, a switch clunk.
Usage: python3 engine/styles/day48_oscilloscope.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
_F = {}
def F(kind, s):
    k = (kind, int(s))
    if k not in _F:
        path = {"vt": "VT323-Regular.ttf", "bc": "BarlowCondensed-Bold.ttf", "bcs": "BarlowCondensed-SemiBold.ttf"}[kind]
        _F[k] = ImageFont.truetype(f"{FONTS}/{path}", int(s))
    return _F[k]

PANEL = (192, 186, 168); PANEL_D = (150, 144, 128); INKP = (40, 38, 34); BEZEL = (26, 28, 27)
GREEN = np.array([90, 255, 140], np.float32); AMBER = np.array([255, 172, 58], np.float32)
RED = (198, 62, 46); CREAM = (240, 234, 216)
SX, SY, SW, SH = 70, 196, 940, 960              # CRT screen rectangle
CX, CY = SW / 2, SH / 2

# ---------- static panel ----------
def build_panel():
    rr = np.random.default_rng(48)
    a = np.zeros((H, W, 3), np.float32); a[:] = PANEL
    br = rr.normal(0, 1, (H, W)).astype(np.float32)
    br = cv2.GaussianBlur(br, (0, 0), sigmaX=0.6, sigmaY=9) * 5           # vertical brushing
    a += br[..., None]
    v = (np.arange(H, dtype=np.float32) / H)[:, None, None]
    a *= 1.04 - 0.1 * v
    img = Image.fromarray(a.clip(0, 255).astype(np.uint8)); d = ImageDraw.Draw(img, "RGBA")
    # header plate
    d.rounded_rectangle([60, 52, W - 60, 150], 14, fill=(58, 56, 50, 255))
    d.rounded_rectangle([64, 56, W - 64, 146], 12, outline=(110, 106, 96, 255), width=2)
    f = F("bc", 48); s = "SF-48  DUAL TRACE OSCILLOSCOPE"
    d.text(((W - f.getlength(s)) / 2, 72), s, font=f, fill=CREAM + (255,))
    for x in (92, W - 92): d.ellipse([x - 9, 92, x + 9, 110], fill=(150, 146, 136, 255)); d.line([x - 6, 101, x + 6, 101], fill=(70, 68, 62, 255), width=3)
    # bezel with drop shadow
    sh = Image.new("L", (W, H), 0); ImageDraw.Draw(sh).rounded_rectangle([SX - 34, SY - 30, SX + SW + 40, SY + SH + 46], 46, fill=150)
    sh = sh.filter(__import__("PIL.ImageFilter", fromlist=["x"]).GaussianBlur(18))
    img.paste((40, 36, 30), (0, 0), sh)
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([SX - 34, SY - 34, SX + SW + 34, SY + SH + 34], 44, fill=BEZEL + (255,))
    d.rounded_rectangle([SX - 30, SY - 30, SX + SW + 30, SY + SH + 30], 42, outline=(64, 66, 64, 255), width=2)
    for x, y in ((SX - 16, SY - 16), (SX + SW + 16, SY - 16), (SX - 16, SY + SH + 16), (SX + SW + 16, SY + SH + 16)):
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(90, 92, 90, 255))
    # lower controls: labels for knobs
    for x, lab in zip(KNOB_X, ("TIME / DIV", "CH1 · AIR", "CH2 · WATER", "INTENSITY")):
        f = F("bc", 34); d.text((x - f.getlength(lab) / 2, 1210), lab, font=f, fill=INKP + (255,))
        for k in range(11):                                       # dial ticks
            ang = math.radians(-135 + 27 * k); r0, r1 = 74, 84 if k % 5 else 90
            d.line([x + r0 * math.sin(ang), KNOB_Y - r0 * math.cos(ang), x + r1 * math.sin(ang), KNOB_Y - r1 * math.cos(ang)], fill=INKP + (255,), width=3)
        d.ellipse([x - 64, KNOB_Y - 58, x + 70, KNOB_Y + 76], fill=(60, 54, 44, 90))        # knob shadow
        d.ellipse([x - 62, KNOB_Y - 62, x + 62, KNOB_Y + 62], fill=(30, 30, 30, 255))
        for k in range(36):                                       # knurled skirt
            ang = math.radians(k * 10)
            d.line([x + 50 * math.sin(ang), KNOB_Y - 50 * math.cos(ang), x + 61 * math.sin(ang), KNOB_Y - 61 * math.cos(ang)], fill=(70, 70, 68, 255), width=2)
        d.ellipse([x - 44, KNOB_Y - 44, x + 44, KNOB_Y + 44], fill=(214, 208, 192, 255))
        d.ellipse([x - 38, KNOB_Y - 38, x + 38, KNOB_Y + 38], fill=(230, 225, 210, 255))
    # LEDs labels
    for x, lab in zip(LED_X, ("CH1", "CH2", "TRIG")):
        f = F("bcs", 28); d.text((x - f.getlength(lab) / 2, 1488), lab, font=f, fill=INKP + (255,))
        d.ellipse([x + 30, 1490, x + 52, 1512], fill=(60, 58, 52, 255))
    # bottom row: BNC jacks + power switch (below the caption area)
    for x, lab in ((180, "CH1 IN"), (360, "CH2 IN"), (540, "EXT TRIG")):
        y = 1800; d.ellipse([x - 40, y - 40, x + 40, y + 40], fill=(120, 122, 124, 255)); d.ellipse([x - 32, y - 32, x + 32, y + 32], fill=(176, 178, 180, 255))
        d.ellipse([x - 18, y - 18, x + 18, y + 18], fill=(40, 40, 40, 255)); d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(190, 160, 90, 255))
        f = F("bcs", 28); d.text((x - f.getlength(lab) / 2, 1736 - 4), lab, font=f, fill=INKP + (255,))
    d.rounded_rectangle([760, 1760, 960, 1846], 12, fill=(58, 56, 50, 255))
    d.rounded_rectangle([870, 1772, 948, 1834], 9, fill=RED + (255,)); d.rectangle([872, 1774, 946, 1790], fill=(225, 100, 84, 255))
    f = F("bc", 36); d.text((774, 1782), "POWER", font=f, fill=CREAM + (255,))
    return np.asarray(img).copy()

KNOB_X = (165, 405, 675, 915); KNOB_Y = 1372
LED_X = (330, 540, 750)

# screen static layers
yy, xx = np.mgrid[0:SH, 0:SW].astype(np.float32)
_r = np.sqrt(((xx - CX) / (SW * 0.62)) ** 2 + ((yy - CY) / (SH * 0.62)) ** 2)
VIG = np.clip(1.08 - 0.55 * _r ** 2.2, 0.25, 1.0)[..., None]
SCAN = (0.86 + 0.14 * (np.arange(SH) % 3 != 0))[:, None, None].astype(np.float32)
BASE = np.zeros((SH, SW, 3), np.float32); BASE[:] = (7, 16, 11)
GRAT = np.zeros((SH, SW), np.uint8)
DIV = 110; GX0, GY0 = (SW - 8 * DIV) // 2, (SH - 8 * DIV) // 2
for k in range(9):
    cv2.line(GRAT, (GX0 + k * DIV, GY0), (GX0 + k * DIV, GY0 + 8 * DIV), 255, 1, cv2.LINE_AA)
    cv2.line(GRAT, (GX0, GY0 + k * DIV), (GX0 + 8 * DIV, GY0 + k * DIV), 255, 1, cv2.LINE_AA)
for k in range(41):
    x = GX0 + k * DIV // 5; cv2.line(GRAT, (x, int(CY) - 7), (x, int(CY) + 7), 255, 1, cv2.LINE_AA)
    y = GY0 + k * DIV // 5; cv2.line(GRAT, (int(CX) - 7, y), (int(CX) + 7, y), 255, 1, cv2.LINE_AA)
BASE += (GRAT.astype(np.float32) / 255)[..., None] * np.array([26, 70, 44], np.float32)
SHEEN = np.clip(1 - np.abs((xx * 0.55 + yy * 0.45) - 330) / 180, 0, 1) ** 2 * np.clip(1 - yy / SH * 1.6, 0, 1)
SHEEN = (SHEEN * 16)[..., None]
MASK = np.zeros((SH, SW), np.uint8)
Image.fromarray(MASK); _m = Image.new("L", (SW, SH), 0); ImageDraw.Draw(_m).rounded_rectangle([0, 0, SW - 1, SH - 1], 36, fill=255)
MASK = (np.asarray(_m).astype(np.float32) / 255)[..., None]

# ---------- beam drawing (screen-local coords) ----------
G8 = np.zeros((SH, SW), np.uint8); A8 = np.zeros((SH, SW), np.uint8)
TXT = []
def B(ch): return A8 if ch == "a" else G8
def P(pts): return (np.array(pts, np.float32).reshape(-1, 1, 2) * 8).astype(np.int32)
def beam(pts, ch="g", i=1.0, w=4, closed=False):
    if i <= 0.01 or len(pts) < 2: return
    cv2.polylines(B(ch), [P(pts)], closed, int(255 * min(1, i)), w, cv2.LINE_AA, shift=3)
def dot(x, y, r, ch="g", i=1.0):
    if i > 0.01: cv2.circle(B(ch), (int(x * 8), int(y * 8)), int(r * 8), int(255 * min(1, i)), -1, cv2.LINE_AA, shift=3)
def rect(x0, y0, x1, y1, ch="g", i=1.0):
    if i > 0.01: cv2.rectangle(B(ch), (int(x0), int(y0)), (int(x1), int(y1)), int(255 * min(1, i)), -1)
def txt(s, size, cx, cy, ch="g", i=1.0, reveal=1.0, anchor="c"):
    if i > 0.01: TXT.append((s, size, cx, cy, ch, i, reveal, anchor))
def tw(s, size): return F("vt", size).getlength(s)
def fit(s, size, maxw=SW - 110):
    while tw(s, size) > maxw and size > 40: size -= 4
    return size
def flush_text():
    for buf, ch in ((G8, "g"), (A8, "a")):
        items = [x for x in TXT if x[4] == ch]
        if not items: continue
        im = Image.fromarray(buf); d = ImageDraw.Draw(im)
        for s, size, cx, cy, _, i, rev, anc in items:
            f = F("vt", size); n = int(round(len(s) * max(0, min(1, rev)))); sh = s[:n]
            asc, desc = f.getmetrics()
            x = cx - f.getlength(s) / 2 if anc == "c" else (cx if anc == "l" else cx - f.getlength(s))
            y = cy - asc * 0.62
            d.text((x, y), sh, font=f, fill=int(255 * min(1, i)))
            if 0 < n < len(s) and rev < 1: d.rectangle([x + f.getlength(sh) + 4, y + asc * 0.3, x + f.getlength(sh) + size * 0.36, y + asc * 0.95], fill=int(255 * i))
        buf[:] = np.asarray(im)
    TXT.clear()

def fade(lt, at, d=0.25): return ease((lt - at) / d)
def wstart(ln, i): return words[min(ln["_w0"] + i, ln["_w1"] - 1)][1] - ln["_s"]

def packet(x, p, amp, wid, lam):
    u = (x - p) / wid
    return amp * np.exp(-u * u) * np.sin(2 * np.pi * (x - p) / lam)

def lane_trace(y, p, ch, amp=70, wid=60, lam=48, i=1.0, x0=40, x1=SW - 40):
    xs = np.arange(x0, x1, 3, dtype=np.float32)
    ys = y - packet(xs, p, amp, wid, lam)
    beam(list(zip(xs, ys)), ch, i, 4)

def wrap(p, x0=40, x1=SW - 40): return x0 + (p - x0) % (x1 - x0 + 240) - 120

# ---------- scenes: fn(ln, lt, dur, t, al) ----------
def lanes(t, al, third=False, lt=0.0):
    ys = (720, 880) if not third else (540, 690)
    amp = 70 if not third else 45; lo = 78 if not third else 58
    for k, dt in enumerate((0.09, 0.06, 0.03, 0.0)):         # persistence trail
        ii = al * (0.18, 0.3, 0.5, 1.0)[k]; tt_ = t - dt
        lane_trace(ys[0], wrap(330 + 120 * tt_), "g", amp=amp, i=ii)
        lane_trace(ys[1], wrap(560 + 516 * tt_), "a", amp=amp, wid=90, lam=48 * 4.3 / 2.2, i=ii)
    txt("CH1  AIR", 44, 44, ys[0] - lo, "g", al * 0.8, anchor="l")
    txt("CH2  WATER", 44, 44, ys[1] - lo, "a", al * 0.8, anchor="l")
    return ys

def S_hook(ln, lt, dur, t, al=1.0):
    txt("SOUND MOVES", fit("SOUND MOVES", 170), CX, 150, "g", al)
    txt("4× FASTER", fit("4× FASTER", 250), CX, 330, "a", al)
    txt("IN WATER", fit("IN WATER", 170), CX, 500, "g", al)
    lanes(t, al)

def S_loop(ln, lt, dur, t, al=1.0):
    txt("THAT'S NOT", 150, CX, 140, "g", al, reveal=lt / 0.35)
    txt("THE FASTEST...", fit("THE FASTEST...", 150), CX, 290, "a", al, reveal=(lt - wstart(ln, 4)) / 0.35)
    ys = lanes(t, al * 0.75, third=True)
    y3 = 840
    blink = 1.0 if (t * 2.2) % 1 < 0.6 else 0.35
    beam([(40, y3), (SW - 40, y3)], "g", al * 0.7, 3)
    txt("CH3  ? ? ?", 44, 44, y3 - 58, "g", al * blink, anchor="l")
    txt("WAIT FOR IT", 60, SW - 50, y3 - 58, "a", al * blink, anchor="r")

def counter(v, digits_comma=False):
    s = f"{int(v):,}" if digits_comma else str(int(v)); return s

def S_air(ln, lt, dur, t, al=1.0):
    txt("AIR  ·  20 °C", 64, CX, 90, "g", al * 0.85)
    v = 343 * eout((lt - 0.2) / 1.4)
    txt(counter(v), 300, CX - 70, 290, "g", al)
    txt("m/s", 100, CX + 250, 340, "g", al * fade(lt, 0.3))
    txt("METERS EVERY SECOND", 52, CX, 470, "g", al * fade(lt, wstart(ln, 7) - 0.1) * 0.85)
    for k, dt in enumerate((0.06, 0.03, 0.0)):
        tt_ = t - dt; xs = np.arange(40, SW - 40, 3, dtype=np.float32)
        ys = 720 - 90 * np.sin(2 * np.pi * (xs - 110 * tt_ * 1.3) / 110)
        beam(list(zip(xs, ys)), "g", al * (0.25, 0.5, 1.0)[k], 4)
    # wavelength marker
    beam([(GX0 + 2 * DIV, 860), (GX0 + 3 * DIV, 860)], "g", al * 0.8, 3)
    for x in (GX0 + 2 * DIV, GX0 + 3 * DIV): beam([(x, 845), (x, 875)], "g", al * 0.8, 3)
    txt("1 WAVE", 44, GX0 + 3 * DIV + 20, 860, "g", al * 0.8, anchor="l")

def S_water(ln, lt, dur, t, al=1.0):
    txt("WATER  ·  20 °C", 64, CX, 90, "a", al * 0.85)
    v = 1480 * eout((lt - 0.15) / 1.3)
    if v < 1479: v = int(v / 10) * 10
    txt(counter(v, True), 300, CX - 80, 290, "a", al)
    txt("m/s", 100, CX + 330, 340, "a", al * fade(lt, 0.3))
    k4 = fade(lt, 1.2, 0.3)
    txt("×4.3 FASTER", 76, CX, 470, "a", al * k4)
    xs = np.arange(40, SW - 40, 3, dtype=np.float32)
    for k, dt in enumerate((0.06, 0.03, 0.0)):
        tt_ = t - dt
        ya = 640 - 40 * np.sin(2 * np.pi * (xs - 110 * tt_ * 1.3) / 110)           # air (same pitch, short waves)
        beam(list(zip(xs, ya)), "g", al * 0.45 * (0.3, 0.6, 1.0)[k], 3)
        yw = 800 - 90 * np.sin(2 * np.pi * (xs - 473 * tt_ * 1.3) / 473)          # water: same pitch, 4.3x longer waves
        beam(list(zip(xs, yw)), "a", al * (0.25, 0.5, 1.0)[k], 4)
    txt("AIR", 40, SW - 50, 580, "g", al * 0.6, anchor="r")
    txt("WATER", 40, SW - 50, 900, "a", al * 0.8, anchor="r")

RACE_T0 = 0.35
def S_race(ln, lt, dur, t, al=1.0):
    x0, x1 = 90, SW - 90
    txt("RACE: 1 KILOMETER", fit("RACE: 1 KILOMETER", 110), CX, 110, "g", al)
    for x, lab in ((x0, "START"), (x1, "1 KM")):
        beam([(x, 250), (x, 760)], "g", al * 0.55, 3); txt(lab, 44, x, 222, "g", al * 0.7)
    for y, ch, v, lab in ((380, "g", 343, "AIR"), (620, "a", 1480, "WATER")):
        beam([(x0, y), (x1, y)], ch, al * 0.35, 2)
        el = max(0.0, lt - RACE_T0); arr = 1000 / v; done = el >= arr
        e = min(el, arr); px = x0 + (x1 - x0) * e / arr
        for k in range(6):                                          # trail
            q = max(0.0, e - 0.025 * (k + 1)); qx = x0 + (x1 - x0) * q / arr
            dot(qx, y, 12 - k * 1.5, ch, al * (0.6 - 0.09 * k))
        rad = 16 + (8 * math.sin(lt * 20) if done else 0)
        dot(px, y, rad, ch, al)
        if done:
            for k in range(3):                                      # arrival rings
                rr_ = 20 + (el - arr) * 260 + k * 30
                if rr_ < 140: beam([(px + rr_ * math.cos(a), y + rr_ * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 60)], ch, al * (1 - rr_ / 140), 3, True)
        txt(lab, 56, x0, y - 70, ch, al * 0.9, anchor="l")
        txt(f"{e:4.2f} s", 72, x1, y + 80, ch, al, anchor="r")
    if lt > RACE_T0 + 1000 / 1480 + 0.15:
        txt("WATER WINS", fit("WATER WINS", 120), CX, 860, "a", al * fade(lt, RACE_T0 + 0.83, 0.2))
    if lt > RACE_T0 + 1000 / 343 + 0.05:
        txt("+2.2 s", 70, CX + 260, 760, "a", al * fade(lt, RACE_T0 + 2.97, 0.15))

def S_squeeze(ln, lt, dur, t, al=1.0):
    txt("HARD TO SQUEEZE", fit("HARD TO SQUEEZE", 140), CX, 110, "a", al, reveal=(lt - wstart(ln, 1)) / 0.4 if lt < 1.5 else 1)
    for (y0, y1, sp, ch, spd, lab) in ((250, 520, 62, "g", 230, "AIR"), (600, 870, 22, "a", 980, "WATER")):
        beam([(40, y0), (SW - 40, y0), (SW - 40, y1), (40, y1)], ch, al * 0.4, 2, True)
        txt(lab, 44, 44, y0 - 28, ch, al * 0.9, anchor="l")
        p = 60 + (spd * lt) % (SW + 300)
        pist = 60 + 28 * max(0.0, math.sin(2 * math.pi * min(1, (spd * lt) % (SW + 300) / 220))) if (spd * lt) % (SW + 300) < 110 else 60
        beam([(pist, y0 + 20), (pist, y1 - 20)], ch, al, 6)                 # piston
        rows = int((y1 - y0 - 70) / sp) + 1
        for r in range(rows):
            yy_ = y0 + 50 + r * sp + (sp / 2 if r % 2 else 0) * 0
            if yy_ > y1 - 20: break
            for c in range(int((SW - 140) / sp) + 1):
                x = 90 + c * sp + (sp / 2 if r % 2 else 0)
                if x > SW - 50: break
                u = (x - p) / (55 if ch == "g" else 70)
                dx = -26 * u * math.exp(-u * u) if ch == "g" else -12 * u * math.exp(-u * u)
                dot(x + dx, yy_, 6 if ch == "g" else 4, ch, al * (0.55 + 0.45 * math.exp(-u * u)))
    txt("SLOW PUSH", 44, SW - 40, 222, "g", al * 0.8, anchor="r")
    txt("FAST PUSH", 44, SW - 40, 572, "a", al * 0.9, anchor="r")

def S_steel(ln, lt, dur, t, al=1.0):
    gx = 60; L = SW - 2 * gx
    for k, (lab, v, ch) in enumerate((("AIR", 343, "g"), ("WATER", 1480, "a"), ("STEEL", 5960, "g"))):
        y = 430 + k * 170; st = 0.15 + 0.35 * k if k < 2 else wstart(ln, 2)
        g = eout((lt - st) / (0.6 if k < 2 else 1.1)); n = int(L * v / 5960 * g / 26)
        txt(lab, 56, gx, y - 52, ch, al * fade(lt, st - 0.1), anchor="l")
        for s in range(n): rect(gx + s * 26, y - 20, gx + s * 26 + 20, y + 20, ch, al * (1.0 if k == 2 else 0.85))
        if g > 0.02: txt(f"{int(v * g):,} m/s", 52, SW - gx, y - 52, ch, al * fade(lt, st), anchor="r")
    kx = fade(lt, wstart(ln, 6) - 0.05, 0.15)
    flick = 1.0 if kx >= 1 or (lt * 18) % 1 < 0.7 else 0.5
    txt("×17", 330, CX, 200, "a", al * kx * flick)
    if kx < 0.5: txt("THROUGH STEEL?", fit("THROUGH STEEL?", 110), CX, 200, "g", al * (1 - kx * 2))

def S_end(ln, lt, dur, t, al=1.0):
    click = ln["scene"].get("click_at", 0.45)
    on = ease((lt - click) / 0.3)
    lp = (lt - (dur - 0.55)) / 0.5                             # fade into the hook screen for the loop
    a1 = al * (1 - ease(lp / 0.5)); lh = ease((lp - 0.4) / 0.6)
    txt("SOUNDS FAKE?", fit("SOUNDS FAKE?", 140), CX, 150, "g", a1)
    x0, x1, y, h = 150, SW - 150, 400, 150
    pts = [(x0 + h / 2 + (h / 2) * math.cos(a), y + (h / 2) * math.sin(a)) for a in np.linspace(math.pi / 2, 1.5 * math.pi, 30)]
    pts += [(x1 - h / 2 + (h / 2) * math.cos(a), y + (h / 2) * math.sin(a)) for a in np.linspace(-math.pi / 2, math.pi / 2, 30)]
    if on > 0:
        fx = x0 + (x1 - x0) * on
        fp = [(min(px, fx), py) for px, py in pts]
        cv2.fillPoly(A8, [P(fp)], int(255 * a1 * 0.25), cv2.LINE_AA, shift=3)
    beam(pts, "g", a1, 5, True)
    kx = x0 + h / 2 + (x1 - x0 - h) * on
    txt("FAKE", 80, x1 - h / 2 - 50, y, "g", a1 * (1 - on) * 0.9, anchor="r")
    txt("TRUE", 80, x0 + h / 2 + 40, y, "g", a1 * on, anchor="l")
    beam([(kx + 56 * math.cos(a), y + 56 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 60)], "g", a1, 6, True)
    dot(kx, y, 30, "g", a1)
    txt("IT'S TRUE.", fit("IT'S TRUE.", 220), CX, 650, "a", a1 * fade(lt, click + 0.3, 0.2))
    txt("FOLLOW FOR MORE", fit("FOLLOW FOR MORE", 100), CX, 830, "g", a1 * fade(lt, click + 0.6, 0.2))
    if lh > 0: S_hook(ln, lt, dur, t, al * lh)

SCENES = dict(hook=S_hook, loop=S_loop, air=S_air, water=S_water, race=S_race, squeeze=S_squeeze, steel=S_steel, end=S_end)

# ---------- audio ----------
voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32); tt = np.arange(n) / SR
rng = np.random.default_rng(48)
music += (np.sin(2 * np.pi * 60 * tt) * 0.5 + np.sin(2 * np.pi * 120 * tt) * 0.25 + np.sin(2 * np.pi * 180 * tt) * 0.1).astype(np.float32) * 0.012
BPM = 112; beat = 60 / BPM
BASS = [55.0, 55.0, 65.41, 49.0]                          # A1 A1 C2 G1
ARP = [[220.0, 261.63, 329.63, 440.0], [220.0, 261.63, 329.63, 392.0], [261.63, 329.63, 392.0, 523.25], [196.0, 246.94, 293.66, 392.0]]
def sq(f, dur, gain, cutoff=6):
    s = np.arange(int(dur * SR)) / SR
    sig = sum(np.sin(2 * np.pi * f * h * s) / h for h in (1, 3, 5, 7) if h <= cutoff)
    return (sig * np.exp(-s * 9) * np.minimum(1, s / 0.004)).astype(np.float32) * gain
def bassn(f, dur, gain):
    s = np.arange(int(dur * SR)) / SR
    sig = np.sin(2 * np.pi * f * s) + 0.3 * np.sin(2 * np.pi * 2 * f * s)
    return (sig * np.exp(-s * 3.5) * np.minimum(1, s / 0.01)).astype(np.float32) * gain
bars = int(total / (4 * beat)) + 1
for b in range(bars):
    ch = b % 4; t0 = b * 4 * beat
    for k in range(4): place(music, t0 + k * beat, bassn(BASS[ch], beat * 1.2, 0.09))
    for k in range(8): place(music, t0 + k * beat / 2, sq(ARP[ch][(k * 3) % 4] * 2, 0.25, 0.022))
    for k in range(4): place(music, t0 + k * beat + beat / 2, (rng.normal(0, 1, int(0.03 * SR)) * np.exp(-np.arange(int(0.03 * SR)) / SR * 160)).astype(np.float32), 0.03)
def ping(at, f=1320, gain=0.07, dur=0.9):
    s = np.arange(int(dur * SR)) / SR
    place(music, at, (np.sin(2 * np.pi * f * s) * np.exp(-s * 6) * np.minimum(1, s / 0.003)).astype(np.float32), gain)
hook_hit(music, 0.3); ping(0.0, 1760, 0.06)
def tick(at, gain=0.05):
    s = np.arange(int(0.012 * SR)) / SR; place(music, at, (np.sin(2 * np.pi * 3000 * s) * np.exp(-s * 300)).astype(np.float32), gain)
for i, ln in enumerate(spec["lines"]):
    st = ln["scene"]["type"]; s0 = ln["_s"]
    if i > 0: whoosh(music, s0 - 0.12, 0.09, 0.25); ping(s0 - 0.08, 1320 if i % 2 else 1100, 0.05)
    if st in ("air", "water"):
        for k in range(14): tick(s0 + 0.2 + 1.4 * (1 - (1 - k / 14) ** (1 / 3)), 0.04)
    if st == "race":
        for v, f in ((1480, 880), (343, 660)):
            tarr = s0 + RACE_T0 + 1000 / v; ping(tarr, f, 0.08, 0.6)
        s = np.arange(int(0.68 * SR)) / SR
        place(music, s0 + RACE_T0, (np.sin(2 * np.pi * (400 * s + 500 * s * s)) * 0.5 * np.minimum(1, s / 0.05)).astype(np.float32), 0.03)
    if st == "steel":
        a = s0 + wstart(ln, 6); place(music, a, bassn(55, 0.8, 0.25)); ping(a, 1760, 0.07)
    if st == "end":
        c = s0 + ln["scene"].get("click_at", 0.45)
        s = np.arange(int(0.06 * SR)) / SR; place(music, c, (rng.normal(0, 1, len(s)) * np.exp(-s * 90)).astype(np.float32), 0.25)
        place(music, c, bassn(82.4, 0.3, 0.2))
        for j, f in enumerate((440.0, 554.37, 659.25, 880.0)): ping(c + 0.2 + j * 0.07, f, 0.05, 1.2)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.45)

# ---------- compositing ----------
PANEL_IMG = build_panel()
CUTS = [ln["_s"] - 0.12 for ln in spec["lines"]][1:]
SIDX = {ln["scene"]["type"]: i for i, ln in enumerate(spec["lines"])}
groups = caption_groups(words, 3)

def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    ws = [words[i][0] for i in g]; size = 76
    f = F("bc", size)
    while f.getlength(" ".join(ws)) > W - 260 and size > 40: size -= 4; f = F("bc", size)
    tw_ = f.getlength(" ".join(ws)); x = (W - tw_) / 2; y = 1572
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([x - 44, y - 22, x + tw_ + 44, y + size + 22], radius=14, fill=(18, 20, 19, 250), outline=(120, 116, 104, 255), width=3)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2]; wl = f.getlength(w)
        if on: d.rounded_rectangle([x - 8, y - 4, x + wl + 8, y + size + 6], radius=8, fill=(255, 172, 58, 255))
        d.text((x, y - size * 0.1), w, font=f, fill=(20, 18, 14, 255) if on else (240, 240, 232, 255)); x += f.getlength(w + " ")

def knobs(img, t, ln):
    d = ImageDraw.Draw(img, "RGBA")
    si = spec["lines"].index(ln)
    for k, x in enumerate(KNOB_X):
        # each knob clicks to a new detent on every cut (eased, with a slight overshoot)
        lt_ = t - (ln["_s"] - 0.12)
        prev = (-90 + 27 * ((si - 1) * (k + 1) % 9)) if si > 0 else -90 + 27 * (k * 2 % 9)
        cur = -90 + 27 * (si * (k + 1) % 9) if si > 0 else prev
        ang = math.radians(prev + (cur - prev) * back(lt_ / 0.25, 1.2))
        d.line([x + 8 * math.sin(ang), KNOB_Y - 8 * math.cos(ang), x + 36 * math.sin(ang), KNOB_Y - 36 * math.cos(ang)], fill=RED + (255,), width=7)
        d.ellipse([x - 7, KNOB_Y - 7, x + 7, KNOB_Y + 7], fill=(190, 184, 168, 255))
    st = ln["scene"]["type"]
    leds = (st not in ("water",), st not in ("air",), (t * 1.8) % 1 < 0.5)
    for x, on, col in zip(LED_X, leds, ((90, 255, 140), (255, 172, 58), (255, 80, 60))):
        if on:
            glow = Image.new("RGBA", (80, 80), (0, 0, 0, 0)); ImageDraw.Draw(glow).ellipse([22, 22, 58, 58], fill=col + (110,))
            img.alpha_composite(glow.filter(__import__("PIL.ImageFilter", fromlist=["x"]).GaussianBlur(8)), (int(x + 1), 1441)) if img.mode == "RGBA" else None
            d.ellipse([x + 32, 1492, x + 50, 1510], fill=col + (255,)); d.ellipse([x + 36, 1495, x + 42, 1501], fill=(255, 255, 255, 200))

def screen(t, ln, lt, dur):
    G8[:] = 0; A8[:] = 0
    SCENES[ln["scene"]["type"]](ln, lt, dur, t)
    flush_text()
    g = np.stack([G8, A8], -1).astype(np.float32) / 255
    b1 = cv2.GaussianBlur(g, (0, 0), 3.5); b2 = cv2.GaussianBlur(cv2.resize(g, (SW // 4, SH // 4), interpolation=cv2.INTER_AREA), (0, 0), 5)
    b2 = cv2.resize(b2, (SW, SH), interpolation=cv2.INTER_LINEAR)
    e = g * 0.95 + b1 * 0.85 + b2 * 0.9
    rgb = BASE + e[..., 0:1] * GREEN + e[..., 1:2] * AMBER
    core = np.clip(g[..., 0:1] + g[..., 1:2] - 0.55, 0, 1) * 150
    rgb = (rgb + core) * SCAN * VIG + SHEEN
    # CRT collapse on cuts
    for c in CUTS:
        ph = t - c
        if -0.08 <= ph < 0.15:
            k = 1 - 0.985 * ease((ph + 0.08) / 0.08) if ph < 0 else 0.015 + 0.985 * eout(ph / 0.15)
            hh = max(2, int(SH * k))
            sq_ = cv2.resize(rgb, (SW, hh), interpolation=cv2.INTER_AREA) * (1 + 1.2 * (1 - k))
            out = BASE * VIG + 0; y0 = (SH - hh) // 2; out[y0:y0 + hh] = sq_
            if k < 0.3:
                ln_ = np.exp(-((np.arange(SH) - SH / 2) / (3 + 20 * k)) ** 2)[:, None, None] * (1 - k / 0.3)
                out = out + ln_ * np.array([200, 255, 220], np.float32) * np.exp(-((np.arange(SW) - SW / 2) / (SW * 0.45)) ** 4)[None, :, None]
            rgb = out
            break
    return rgb

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    a = PANEL_IMG.copy()
    scr = screen(t, ln, lt, dur)
    reg = a[SY:SY + SH, SX:SX + SW].astype(np.float32)
    a[SY:SY + SH, SX:SX + SW] = (reg * (1 - MASK) + np.clip(scr, 0, 255) * MASK).astype(np.uint8)
    img = Image.fromarray(a).convert("RGBA")
    knobs(img, t, ln)
    caption(img, t)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 10, W, H], fill=(26, 28, 27)); d.rectangle([0, H - 10, int(W * t / total), H], fill=(90, 255, 140))
    return img.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
        print(f"total {total:.1f}s; starts " + ", ".join(f"{ln['scene']['type']}@{ln['_s']:.1f}" for ln in spec["lines"]))
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=22); print(f"done {total:.1f}s")
