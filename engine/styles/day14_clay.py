"""Day 14 — CLAYMATION RAINFOREST style (sloths hold their breath for 40 minutes).
Plasticine look: chunky rounded shapes with soft top-left highlight and bottom rim shade, thumbprint texture,
layered clay leaves that sway, a round clay sloth, stop-motion stepping at 12 fps; marimba + rain-stick.
Usage: python3 engine/styles/day14_clay.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
_FC = {}
def FRED(s):
    s = max(8, int(s))
    if s not in _FC: f = ImageFont.truetype(f"{FONTS}/Fredoka.ttf", s); f.set_variation_by_axes([650, 100]); _FC[s] = f
    return _FC[s]
SKY, LEAF1, LEAF2, LEAF3, FUR, FUR2, FACE, MASK, WATER, CREAM, RED, BROWN, ALGAE = (190, 225, 200), (70, 150, 80), (40, 115, 65), (110, 180, 90), (150, 120, 90), (115, 90, 68), (225, 205, 170), (80, 60, 45), (70, 160, 200), (255, 245, 225), (230, 90, 70), (110, 75, 45), (120, 190, 90)
rng = np.random.default_rng(14)
TEX = np.asarray(Image.fromarray(rng.normal(128, 30, (H // 8, W // 8)).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32)[..., None]
TEX = (TEX - 128) * 0.12 + rng.normal(0, 3, (H, W, 1))

def sh(c, k): return tuple(max(0, min(255, int(v * k))) for v in c)
def blob(d, box, col, rot_light=True):
    """Clay ellipse: base + darker rim at bottom + highlight top-left."""
    x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0
    d.ellipse(box, fill=sh(col, 0.78))
    d.ellipse([x0 + w * 0.03, y0, x1 - w * 0.03, y1 - h * 0.08], fill=col)
    d.ellipse([x0 + w * 0.18, y0 + h * 0.1, x0 + w * 0.48, y0 + h * 0.32], fill=sh(col, 1.18))
def rblob(d, box, r, col):
    x0, y0, x1, y1 = box; h = y1 - y0
    d.rounded_rectangle(box, r, fill=sh(col, 0.78)); d.rounded_rectangle([x0, y0, x1, y1 - h * 0.1], r, fill=col)
    if x1 - x0 > 60 and y1 - y0 > 50: d.rounded_rectangle([x0 + 14, y0 + 10, x0 + max(30, (x1 - x0) * 0.4), y0 + 30], 10, fill=sh(col, 1.18))
def leaf(d, cx, cy, L, ang, col):
    pts = []
    for k in range(17):
        u = k / 16; w_ = math.sin(u * math.pi) * L * 0.32
        pts.append((u * L, w_))
    pts += [(u, -w) for (u, w) in reversed(pts)]
    c, s = math.cos(ang), math.sin(ang)
    P = [(cx + x * c - y * s, cy + x * s + y * c) for (x, y) in pts]
    d.polygon(P, fill=sh(col, 0.8)); d.polygon([(x - 4 * c, y - 6) for (x, y) in P[:17]] + [(cx + L * 0.5 * c, cy + L * 0.5 * s)], fill=col)
    d.line([(cx, cy), (cx + L * c, cy + L * s)], fill=sh(col, 0.65), width=5)

def jungle(d, t, rows=((180, LEAF2), (1500, LEAF1)), branch=True):
    st = math.floor(t * 12) / 12                                          # stop-motion time
    r = random.Random(14)
    for (y, col) in rows:
        for k in range(9):
            x = k * 140 - 40 + r.uniform(-30, 30); a = r.uniform(-2.6, -0.5) if y > 900 else r.uniform(0.5, 2.6)
            leaf(d, x, y + r.uniform(-60, 60), r.uniform(200, 300), a + 0.05 * math.sin(st * 1.5 + k), col if k % 2 else LEAF3)
    if branch: rblob(d, [-40, 520, W + 40, 600], 40, BROWN)
def sloth(d, cx, cy, s=1.0, t=0.0, eyes="open", hang=True):
    st = math.floor(t * 12) / 12; sw = 6 * math.sin(st * 1.2) * s
    if hang:
        for ax in (-110, 110): rblob(d, [cx + ax * s - 34 * s + sw, cy - 230 * s, cx + ax * s + 34 * s + sw, cy - 40 * s], int(30 * s), FUR2)
        for ax in (-110, 110):
            for k in range(3): d.arc([cx + (ax - 30 + k * 22) * s + sw, cy - 262 * s, cx + (ax - 6 + k * 22) * s + sw, cy - 222 * s], 180, 360, fill=CREAM, width=max(2, int(7 * s)))
    blob(d, [cx - 170 * s + sw, cy - 120 * s, cx + 170 * s + sw, cy + 230 * s], FUR)                # body
    blob(d, [cx - 130 * s + sw, cy - 210 * s, cx + 130 * s + sw, cy + 20 * s], FUR)                 # head
    blob(d, [cx - 100 * s + sw, cy - 170 * s, cx + 100 * s + sw, cy - 10 * s], FACE)
    for ex in (-1, 1):
        d.ellipse([cx + (ex * 52 - 40) * s + sw, cy - 130 * s, cx + (ex * 52 + 40) * s + sw, cy - 80 * s], fill=MASK)
        x = cx + ex * 52 * s + sw; y = cy - 105 * s
        if eyes == "open": d.ellipse([x - 12 * s, y - 12 * s, x + 12 * s, y + 12 * s], fill=(20, 15, 10)); d.ellipse([x - 5 * s, y - 9 * s, x + 1 * s, y - 3 * s], fill=CREAM)
        else: d.arc([x - 16 * s, y - 10 * s, x + 16 * s, y + 10 * s], 10, 170, fill=(20, 15, 10), width=max(2, int(6 * s)))
    d.ellipse([cx - 22 * s + sw, cy - 78 * s, cx + 22 * s + sw, cy - 52 * s], fill=(50, 35, 25))
    d.arc([cx - 40 * s + sw, cy - 70 * s, cx + 40 * s + sw, cy - 30 * s], 20, 160, fill=(50, 35, 25), width=max(2, int(6 * s)))

def finish(img):
    a = np.asarray(img).astype(np.float32) + TEX; return Image.fromarray(a.clip(0, 255).astype(np.uint8))
def plaque(d, s, y, size, col=CREAM, txt=(60, 40, 30)):
    while d.textlength(s, font=FRED(size)) > W - 200: size -= 4
    tw = d.textlength(s, font=FRED(size)); rblob(d, [W / 2 - tw / 2 - 40, y - size * 0.8, W / 2 + tw / 2 + 40, y + size * 0.85], int(size * 0.5), col)
    d.text((W / 2, y - 4), s, font=FRED(size), fill=txt, anchor="mm")
def bubbles(d, t, x, y, n=5):
    for k in range(n):
        p = ((t * 0.7 + k / n) % 1.0); bx = x + 20 * math.sin(t * 3 + k); by = y - p * 500; r = 10 + 14 * p
        d.ellipse([bx - r, by - r, bx + r, by + r], outline=CREAM, width=5)

def S_hook(sc, lt, dur, t):
    img = Image.new("RGB", (W, H), SKY); d = ImageDraw.Draw(img)
    d.rectangle([0, 1050, W, H], fill=WATER); jungle(d, t, rows=((150, LEAF2),), branch=False)
    for k in range(6): y = 1070 + k * 50; d.arc([-50 + (k % 2) * 90 + math.floor(t * 12) / 12 * 30 % 180, y, 200, y + 40], 200, 340, fill=sh(WATER, 1.2), width=6)
    sloth(d, W / 2, 1290, 1.25, t, eyes="closed", hang=False); bubbles(d, t, W / 2 + 160, 1180)
    plaque(d, "HOLDS ITS BREATH", 420, 84); plaque(d, "40 MINUTES", 570, 120, RED, CREAM)
    if sc.get("loop"):
        sec = int(lt * 8) % 60; plaque(d, f"00:{39 - min(39, int(lt*6)):02d}:{sec:02d}", 760, 64, CREAM)
    return finish(img)
def S_heart(sc, lt, dur, t):
    img = Image.new("RGB", (W, H), sh(WATER, 0.7)); d = ImageDraw.Draw(img)
    jungle(d, t, rows=((1650, LEAF2),), branch=False); sloth(d, 340, 1100, 0.9, t, eyes="closed", hang=False)
    bpm = 1.0 - 0.67 * ease((lt - 0.3) / 2.0); ph = (t * (2.2 * bpm)) % 1.0; beat = 1 + 0.18 * math.exp(-ph * 10)
    cx, cy, r = 780, 1000, 120 * beat
    blob(d, [cx - r, cy - r, cx + 4, cy + r * 0.6], RED); blob(d, [cx - 4, cy - r, cx + r, cy + r * 0.6], RED); d.polygon([(cx - r * 0.95, cy + 10), (cx + r * 0.95, cy + 10), (cx, cy + r * 1.3)], fill=sh(RED, 0.9))
    plaque(d, "HEART RATE", 380, 84); plaque(d, f"{int(round(100 * bpm))}%", 1300, 110, RED, CREAM)
    if lt > 2.0: plaque(d, "LESS THAN 1/3!", 540, 72, CREAM, RED)
    return finish(img)
def S_swim(sc, lt, dur, t):
    img = Image.new("RGB", (W, H), SKY); d = ImageDraw.Draw(img)
    rblob(d, [-40, 700, W + 40, 760], 30, BROWN); d.rectangle([0, 1120, W, H], fill=WATER)
    st = math.floor(t * 12) / 12
    lx = 120 + (st * 18) % 300; sloth(d, lx, 650, 0.38, t)                          # land crawl, tiny, slow
    sx = 120 + (st * 260) % (W - 100); sloth(d, sx, 1300, 0.5, t, hang=False)       # swimmer, fast
    for k in range(4): d.line([(sx - 120 - k * 40, 1300 + k * 14), (sx - 200 - k * 40, 1300 + k * 14)], fill=CREAM, width=6)
    plaque(d, "ON LAND: 1x", 560, 54, CREAM); plaque(d, "IN WATER: 3x", 1050, 70, RED, CREAM)
    plaque(d, "3x FASTER", 330, 110)
    return finish(img)
def S_fur(sc, lt, dur, t):
    img = Image.new("RGB", (W, H), SKY); d = ImageDraw.Draw(img); jungle(d, t)
    sloth(d, W / 2, 950, 1.4, t)
    r = random.Random(3); n = int(60 * ease((lt - 0.2) / 2.0))
    for k in range(n):
        x = W / 2 + r.uniform(-200, 200); y = 950 + r.uniform(-100, 280); rr = r.uniform(8, 18)
        if ((x - W / 2) / 220) ** 2 + ((y - 1040) / 300) ** 2 < 1: d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=ALGAE)
    if lt > 1.8:
        for k in range(3):
            a = t * 2 + k * 2.1; mx = W / 2 + 230 * math.cos(a); my = 1000 + 160 * math.sin(a * 1.3); fl = abs(math.sin(t * 14 + k))
            d.polygon([(mx, my), (mx - 40, my - 30 * fl - 6), (mx - 46, my + 10)], fill=(200, 180, 140)); d.polygon([(mx, my), (mx + 40, my - 30 * fl - 6), (mx + 46, my + 10)], fill=(200, 180, 140)); d.ellipse([mx - 8, my - 14, mx + 8, my + 14], fill=(90, 70, 50))
    plaque(d, "A JUNGLE IN ITS FUR", 360, 80)
    return finish(img)
def S_poop(sc, lt, dur, t):
    img = Image.new("RGB", (W, H), SKY); d = ImageDraw.Draw(img); jungle(d, t, rows=((180, LEAF2),), branch=False)
    rblob(d, [W / 2 - 50, 300, W / 2 + 50, 1450], 40, BROWN); d.rectangle([0, 1450, W, H], fill=(120, 90, 55))
    p = ease(lt / 2.5); y = 700 + 520 * p
    sloth(d, W / 2 + 10, y, 0.7, t)
    plaque(d, "ONCE A WEEK", 360, 96); plaque(d, "THE BATHROOM TRIP", 500, 60, CREAM)
    if lt > 2.8:
        u = back((lt - 2.8) / 0.4); rblob(d, [140, 1380 - 60 * u, 360, 1450], 40, (100, 70, 40))
        plaque(d, "UP TO 1/3 OF ITS WEIGHT", 1560, 56, RED, CREAM)
    return finish(img)
def S_end(sc, lt, dur, t):
    img = Image.new("RGB", (W, H), SKY); d = ImageDraw.Draw(img); jungle(d, t)
    sloth(d, W / 2, 1230, 1.0, t, eyes="closed" if lt < sc.get("click_at", 0.45) else "open")
    plaque(d, "SOUNDS FAKE ?!", 330, 100)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.2); cx, cy, w_, h_ = W / 2, 760, 330, 150
    rblob(d, [cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, RED if on > 0.5 else sh(CREAM, 0.85))
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; blob(d, [kx - h_ / 2 + 16, cy - h_ / 2 + 12, kx + h_ / 2 - 16, cy + h_ / 2 - 20], CREAM)
    d.text((cx - w_ / 2 - 30, cy), "FAKE", font=FRED(62), fill=(60, 40, 30) if on < 0.5 else sh(CREAM, 0.7), anchor="rm"); d.text((cx + w_ / 2 + 30, cy), "TRUE", font=FRED(62), fill=RED if on >= 0.5 else (60, 40, 30), anchor="lm")
    return finish(img)
SCENES = dict(hook=S_hook, heart=S_heart, swim=S_swim, fur=S_fur, poop=S_poop, end=S_end)

voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
mel = [392.0, 440.0, 523.25, 440.0, 392.0, 329.63, 293.66, 329.63, 392.0, 523.25, 587.33, 523.25, 440.0, 392.0, 329.63, 392.0]
for k in range(int(total / 0.3)):                                      # marimba
    place(music, k * 0.3, tone(mel[k % 16], 0.6, decay=9, harm=(1, 4, 9.9)), 0.04)
    if k % 4 == 0: place(music, k * 0.3, tone((98.0, 130.81, 110.0, 87.31)[(k // 8) % 4], 0.9, decay=5, harm=(1, 4)), 0.08)
    if k % 8 == 6: place(music, k * 0.3, (np.random.default_rng(k).normal(0, 1, int(0.5 * SR)) * np.linspace(0, 1, int(0.5 * SR)) ** 2 * np.exp(-np.linspace(0, 3, int(0.5 * SR)))).astype(np.float32), 0.01)
hook_hit(music, 0.3)
for s_ in scene_starts(spec): whoosh(music, s_, 0.08)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.3)

groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 72
    while d.textlength(" ".join(ws), font=FRED(size)) > W - 200 and size > 36: size -= 4
    f = FRED(size); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1680
    rblob(d, [x - 36, y - 18, x + tw + 36, y + size + 34], 34, CREAM)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=RED if on else (60, 40, 30)); x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t); caption(img, t)
    ImageDraw.Draw(img).rectangle([0, H - 10, int(W * t / total), H], fill=RED); return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
