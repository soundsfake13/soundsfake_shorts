"""Day 37 — FELT-CRAFT style (sea otters hold hands while they sleep).
Cozy handmade look: felt shapes with fibre texture, white running-stitch outlines, knitted wool waves
that bob, felt otters floating on their backs, kelp strips, button eyes; music-box lullaby.
Usage: python3 engine/styles/day37_felt.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
_FC = {}
def FRED(s):
    s = max(8, int(s))
    if s not in _FC: f = ImageFont.truetype(f"{FONTS}/Fredoka.ttf", s); f.set_variation_by_axes([650, 100]); _FC[s] = f
    return _FC[s]
SKY, SEA, SEA2, BROWN, BROWN2, FACE, KELP, CREAM, RED, NAVY = (250, 214, 180), (70, 140, 170), (50, 110, 150), (120, 80, 55), (95, 62, 42), (225, 205, 175), (80, 130, 60), (255, 246, 230), (215, 85, 70), (40, 50, 80)
rng = np.random.default_rng(37)
FIBRE = (rng.normal(0, 7, (H, W, 1)) + np.asarray(Image.fromarray(rng.normal(128, 40, (H // 4, W // 4)).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32)[..., None] * 0.08 - 10).astype(np.float32)

def stitch_poly(d, pts, col=CREAM, dash=18, gap=12, width=4, closed=True):
    pts = list(pts) + ([pts[0]] if closed else []); acc = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0); s = 0.0
        while s < L:
            ph = (acc + s) % (dash + gap)
            if ph < dash:
                e = min(L, s + dash - ph); d.line([(x0 + (x1 - x0) * s / L, y0 + (y1 - y0) * s / L), (x0 + (x1 - x0) * e / L, y0 + (y1 - y0) * e / L)], fill=col, width=width); s = e
            else: s += dash + gap - ph
        acc += L
def ell_pts(cx, cy, rx, ry, n=48, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    return [(cx + rx * math.cos(a) * c - ry * math.sin(a) * s, cy + rx * math.cos(a) * s + ry * math.sin(a) * c) for a in (2 * math.pi * k / n for k in range(n))]
def felt_ell(d, cx, cy, rx, ry, col, rot=0.0, inset=10):
    P = ell_pts(cx, cy, rx, ry, 48, rot); d.polygon(P, fill=col); stitch_poly(d, ell_pts(cx, cy, rx - inset, ry - inset, 48, rot))

def otter(d, cx, cy, s=1.0, rot=0.0, paw_dir=0, sleep=True):
    """Floating on its back; head to the left of body (rot rotates whole otter)."""
    c, sn = math.cos(rot), math.sin(rot)
    P = lambda x, y: (cx + (x * c - y * sn) * s, cy + (x * sn + y * c) * s)
    felt_ell(d, *P(40, 0), 150 * s, 70 * s, BROWN, rot)                     # body
    tx, ty = P(200, 10); felt_ell(d, tx, ty, 60 * s, 26 * s, BROWN2, rot)  # tail
    for fx in (150, 175): x, y = P(fx, -60); felt_ell(d, x, y, 24 * s, 16 * s, BROWN2, rot, 6)  # feet up
    felt_ell(d, *P(10, -10), 70 * s, 42 * s, FACE, rot)                       # belly
    hx, hy = P(-125, -5); felt_ell(d, hx, hy, 72 * s, 66 * s, FACE, rot)   # head
    for ex in (-1, 1):
        ax, ay = P(-130 + ex * 10, -5 + ex * 52); felt_ell(d, ax, ay, 16 * s, 16 * s, BROWN2, rot, 5)  # ears
    for ex in (-1, 1):
        x, y = P(-110, ex * 26)
        if sleep: d.arc([x - 16 * s, y - 10 * s, x + 16 * s, y + 14 * s], 200 + rot * 57, 340 + rot * 57, fill=NAVY, width=max(2, int(6 * s)))
        else: d.ellipse([x - 9 * s, y - 9 * s, x + 9 * s, y + 9 * s], fill=NAVY)
    nx, ny = P(-160, 0); d.ellipse([nx - 14 * s, ny - 11 * s, nx + 14 * s, ny + 11 * s], fill=NAVY)
    if paw_dir:                                                               # arm reaching out (up/down in screen)
        ax0, ay0 = P(-40, paw_dir * 40); ax1, ay1 = P(-40, paw_dir * 120)
        d.line([(ax0, ay0), (ax1, ay1)], fill=BROWN2, width=int(34 * s)); d.ellipse([ax1 - 22 * s, ay1 - 22 * s, ax1 + 22 * s, ay1 + 22 * s], fill=BROWN2)

def sea(img, t, y0):
    d = ImageDraw.Draw(img); d.rectangle([0, y0, W, H], fill=SEA)
    for row in range(14):                                                      # knitted rows of V stitches
        y = y0 + 20 + row * 70 + 10 * math.sin(t * 1.5 + row * 0.6); col = SEA2 if row % 2 else (90, 160, 190)
        off = (t * 30 * (1 if row % 2 else -1)) % 60
        for x in range(-60, W + 60, 60):
            xx = x + off; d.line([(xx, y), (xx + 30, y + 34), (xx + 60, y)], fill=col, width=12)
    return d

def bg(t, sea_y=980):
    a = np.full((H, W, 3), SKY, np.float32); img = Image.fromarray(a.astype(np.uint8)); d = ImageDraw.Draw(img)
    felt_ell(d, 860, 260, 90, 90, (250, 180, 90))                             # felt sun
    for k, (cx, cy) in enumerate(((240, 330), (700, 470))):
        x = (cx + t * 14 * (k + 1)) % (W + 300) - 150; felt_ell(d, x, cy, 130, 50, CREAM); felt_ell(d, x + 70, cy - 30, 80, 45, CREAM)
    sea(img, t, sea_y); return img
def finish(img):
    a = np.asarray(img).astype(np.float32) + FIBRE; return Image.fromarray(a.clip(0, 255).astype(np.uint8))

def title(d, s, y, size, col=NAVY, maxw=W - 140):
    while d.textlength(s, font=FRED(size)) > maxw and size > 30: size -= 4
    tw = d.textlength(s, font=FRED(size)); P = [(W / 2 - tw / 2 - 36, y - size * 0.75), (W / 2 + tw / 2 + 36, y - size * 0.75), (W / 2 + tw / 2 + 36, y + size * 0.75), (W / 2 - tw / 2 - 36, y + size * 0.75)]
    d.rounded_rectangle([P[0], P[2]], 30, fill=CREAM); stitch_poly(d, [(P[0][0] + 12, P[0][1] + 12), (P[1][0] - 12, P[1][1] + 12), (P[2][0] - 12, P[2][1] - 12), (P[3][0] + 12, P[3][1] - 12)], RED, 14, 10, 4)
    d.text((W / 2, y), s, font=FRED(size), fill=col, anchor="mm")

def S_hook(sc, lt, dur, t):
    img = bg(t); d = ImageDraw.Draw(img)
    title(d, "OTTERS HOLD HANDS", 470, 92); title(d, "WHILE THEY SLEEP", 620, 80, RED)
    b1 = 14 * math.sin(t * 2); b2 = 14 * math.sin(t * 2 + 0.8)
    otter(d, 580, 1030 + b1, 1.6, 0.0, paw_dir=1); otter(d, 580, 1440 + b2, 1.6, 0.0, paw_dir=-1)
    d.ellipse([480, 1200 + (b1 + b2) / 2, 560, 1270 + (b1 + b2) / 2], fill=BROWN2)            # joined paws
    if sc.get("loop"):
        u = back(lt / 0.35)
        if u > 0:
            for k in range(3): x = 900 + k * 40; y = 900 - k * 60 - 20 * math.sin(t * 3 + k); d.text((x, y), "z", font=FRED(int((50 + k * 14) * min(1.2, u))), fill=NAVY, anchor="mm")
        if lt > 0.6: title(d, "...SO THEY DON'T DRIFT", 780, 56, NAVY)
    return finish(img)
def S_raft(sc, lt, dur, t):
    img = bg(t, 760); d = ImageDraw.Draw(img); title(d, "A \"RAFT\" OF OTTERS", 330, 84)
    r = random.Random(5); n = min(9, int(1 + lt * 3.2))
    spots = [(260, 950), (700, 900), (480, 1130), (900, 1150), (220, 1300), (640, 1360), (380, 1540), (860, 1500), (560, 1700)]
    for k in range(n):
        x, y = spots[k]; u = eout((lt - k * 0.3) / 0.4)
        otter(d, x + (1 - u) * 300, y + 10 * math.sin(t * 2 + k), 0.72, r.uniform(-0.4, 0.4))
    return finish(img)
def S_kelp(sc, lt, dur, t):
    img = bg(t, 820); d = ImageDraw.Draw(img); title(d, "NO ONE TO HOLD?", 330, 86); title(d, "KELP SEATBELT", 470, 76, KELP)
    for k in range(5):                                                         # kelp strands rising from below
        x0 = 140 + k * 200; pts = [(x0 + 40 * math.sin(t * 1.2 + j * 0.7 + k), 1920 - j * 110) for j in range(9)]
        for (a, b) in zip(pts, pts[1:]): d.line([a, b], fill=KELP, width=34)
        for j in range(1, 9, 2): x, y = pts[j]; felt_ell(d, x + 30, y, 40, 18, (100, 155, 75), 0.5, 5)
    by = 1150 + 12 * math.sin(t * 2); otter(d, 560, by, 1.4, 0.0)
    w = ease((lt - 0.8) / 1.0)                                                   # kelp wraps across the belly
    if w > 0:
        x0, x1 = 400, 400 + 320 * w
        d.rounded_rectangle([x0, by - 30, x1, by + 30], 18, fill=KELP); stitch_poly(d, [(x0 + 8, by), (x1 - 8, by)], CREAM, 14, 10, 4, closed=False)
    if lt > 2.0: title(d, "CLICK!", 1500, 70, RED)
    return finish(img)
def S_fur(sc, lt, dur, t):
    img = bg(t, 1500); d = ImageDraw.Draw(img); title(d, "THICKEST FUR", 300, 96); title(d, "OF ANY ANIMAL", 440, 72, RED)
    cx, cy, R = W / 2, 980, 360; d.ellipse([cx - R - 20, cy - R - 20, cx + R + 20, cy + R + 20], fill=NAVY); d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=BROWN)
    r = random.Random(9); n = int(900 * ease((lt - 0.2) / 2.5))
    for k in range(n):
        a = r.uniform(0, 2 * math.pi); rr = R * math.sqrt(r.random()) * 0.96; x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
        d.line([(x, y), (x + 8 + 3 * math.sin(t * 3 + k), y - 22)], fill=(BROWN2, (150, 105, 70), FACE)[k % 3], width=3)
    v = int(1_000_000 * ease((lt - 0.2) / 2.5)); title(d, f"{v:,}", 1450, 100, RED); d.text((W / 2, 1560), "hairs per square inch", font=FRED(48), fill=NAVY, anchor="mm")
    return finish(img)
def S_pocket(sc, lt, dur, t):
    img = bg(t, 1100); d = ImageDraw.Draw(img); title(d, "THE WEIRD PART:", 300, 80); title(d, "A ROCK POCKET", 440, 92, RED)
    by = 1000 + 10 * math.sin(t * 2); otter(d, 560, by, 2.0, 0.0, sleep=False)
    px, py = 470, by + 120                                                      # pocket flap under the arm
    o = ease((lt - 0.6) / 0.5)
    rock_y = py - 140 * eout((lt - 1.0) / 0.6) if lt > 1.0 else py
    felt_ell(d, px, rock_y, 56, 40, (140, 140, 150), 0.3, 8)
    felt_ell(d, px, py + 30, 110, 60 - 30 * o, BROWN2, 0.0, 8)
    if lt > 2.2:
        cl = ease((lt - 2.2) / 0.5); felt_ell(d, 760, 1350, 80, 50, (230, 210, 200)); d.line([(690, 1350 - 4 * cl), (830, 1350 + 4 * cl)], fill=NAVY, width=6)
        if lt > 3.0: title(d, "CRACK!", 1520, 70, RED)
    return finish(img)
def S_end(sc, lt, dur, t):
    img = bg(t); d = ImageDraw.Draw(img); title(d, "SOUNDS FAKE ?!", 360, 100)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.2); cx, cy, w_, h_ = W / 2, 620, 330, 150
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=RED if on > 0.5 else (200, 180, 160))
    stitch_poly(d, [(cx - w_ / 2 + 20, cy - h_ / 2 + 12), (cx + w_ / 2 - 20, cy - h_ / 2 + 12), (cx + w_ / 2 - 20, cy + h_ / 2 - 12), (cx - w_ / 2 + 20, cy + h_ / 2 - 12)])
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; felt_ell(d, kx, cy, h_ / 2 - 16, h_ / 2 - 16, CREAM, 0, 8)
    d.text((cx - w_ / 2 - 30, cy), "FAKE", font=FRED(64), fill=NAVY if on < 0.5 else (170, 150, 140), anchor="rm"); d.text((cx + w_ / 2 + 30, cy), "TRUE", font=FRED(64), fill=RED if on >= 0.5 else (170, 150, 140), anchor="lm")
    b1 = 12 * math.sin(t * 2); otter(d, 560, 1100 + b1, 1.1, 0.0, paw_dir=1); otter(d, 560, 1390 - b1, 1.1, 0.0, paw_dir=-1)
    d.ellipse([480, 1215, 540, 1270], fill=BROWN2)
    return finish(img)
SCENES = dict(hook=S_hook, raft=S_raft, kelp=S_kelp, fur=S_fur, pocket=S_pocket, end=S_end)

voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
mel = [784.0, 659.25, 587.33, 659.25, 523.25, 587.33, 659.25, 783.99, 880.0, 783.99, 659.25, 587.33]
for k in range(int(total / 0.4)):                                       # music box
    place(music, k * 0.4, tone(mel[k % 12], 1.2, decay=4, harm=(1, 3, 5.4)), 0.035)
    if k % 3 == 0: place(music, k * 0.4, tone((130.81, 174.61, 196.0, 130.81)[(k // 6) % 4], 1.2, decay=2.5, harm=(1, 2)), 0.06)
hook_hit(music, 0.3)
for s_ in scene_starts(spec): whoosh(music, s_, 0.08)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.3)

groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 70
    while d.textlength(" ".join(ws), font=FRED(size)) > W - 200 and size > 36: size -= 4
    f = FRED(size); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1700
    d.rounded_rectangle([x - 34, y - 16, x + tw + 34, y + size + 32], 30, fill=NAVY)
    stitch_poly(d, [(x - 22, y - 4), (x + tw + 22, y - 4), (x + tw + 22, y + size + 20), (x - 22, y + size + 20)], CREAM, 12, 9, 3)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=(255, 190, 120) if on else CREAM); x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t); caption(img, t)
    ImageDraw.Draw(img).rectangle([0, H - 10, int(W * t / total), H], fill=RED); return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
