"""Day 09 — PULSAR CINEMA style (a teaspoon of neutron star weighs billions of tons).
Cold monochrome blue-white: sweeping lighthouse beams, volumetric haze, anamorphic horizontal flares, letterbox bars,
film grain, thin wide-tracked titles. Deliberately different from the warm Saturn video.
Usage: python3 engine/styles/day09_pulsar.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
F = lambda s, w="SemiBold": ImageFont.truetype(f"{FD}InterDisplay-{w}.otf", int(s))
ICE, WHITE, DIM = np.array([150, 205, 255], np.float32), (240, 248, 255), (120, 140, 170)
rng = np.random.default_rng(9)
STARS = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 2.2)) for _ in range(380)]
GRAIN = [rng.normal(0, 7, (H // 2, W // 2)).astype(np.float32) for _ in range(4)]

def base(t):
    img = Image.new("RGB", (W, H), (2, 4, 10)); d = ImageDraw.Draw(img)
    for (x, y, s) in STARS: c = int(150 * s / 2.2); d.ellipse([x - s, y - s, x + s, y + s], fill=(c, c, min(255, c + 30)))
    return img

def light_layer(): return Image.new("L", (W, H), 0)
def add_light(arr, L, col=ICE, k=1.0, blur=0):
    if blur: L = L.filter(ImageFilter.GaussianBlur(blur))
    arr += (np.asarray(L).astype(np.float32) / 255)[..., None] * col * k

def beams(arr, cx, cy, ang, width=0.07, k=1.0, length=2200):
    L = light_layer(); d = ImageDraw.Draw(L)
    for off in (0, math.pi):
        a = ang + off; d.polygon([(cx, cy), (cx + length * math.cos(a - width), cy + length * math.sin(a - width)), (cx + length * math.cos(a + width), cy + length * math.sin(a + width))], fill=170)
    add_light(arr, L, ICE, k, blur=18)

def star(arr, cx, cy, r, k=1.0):
    L = light_layer(); ImageDraw.Draw(L).ellipse([cx - r * 4, cy - r * 4, cx + r * 4, cy + r * 4], fill=120); add_light(arr, L, ICE, k, blur=r * 2.5)
    L = light_layer(); ImageDraw.Draw(L).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255); add_light(arr, L, np.array([255, 255, 255], np.float32), k * 1.3, blur=2)

def finish(arr, fi):
    small = np.clip(arr[::4, ::4] - 170, 0, 255)                                   # anamorphic streak from highlights
    streak = Image.fromarray(small.mean(axis=2).astype(np.uint8)).filter(ImageFilter.BoxBlur(40)).resize((W, H), Image.BILINEAR)
    arr += (np.asarray(streak).astype(np.float32) / 255)[..., None] * np.array([90, 160, 255], np.float32) * 1.4
    g = GRAIN[fi % 4]; arr += np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None]
    arr[:130] = 0; arr[H - 120:] = 0                                                  # letterbox
    return np.clip(arr, 0, 255).astype(np.uint8)

def title(img, s, size, y, col=WHITE, track=0.18, u=1.0):
    if u <= 0: return
    d = ImageDraw.Draw(img); f = F(size)
    ws = [d.textlength(ch, font=f) for ch in s]; tw = sum(ws) + track * size * (len(s) - 1)
    while tw > W - 100 and size > 30: size -= 4; f = F(size); ws = [d.textlength(ch, font=f) for ch in s]; tw = sum(ws) + track * size * (len(s) - 1)
    x = (W - tw) / 2; c = tuple(int(v * u) for v in col)
    for ch, w_ in zip(s, ws): d.text((x, y + (1 - u) * 20), ch, font=f, fill=c); x += w_ + track * size

def spoon(d, cx, cy, s=1.0):
    d.ellipse([cx - 130 * s, cy - 80 * s, cx + 130 * s, cy + 80 * s], outline=(170, 190, 215), width=int(6 * s))
    d.rounded_rectangle([cx + 120 * s, cy - 16 * s, cx + 560 * s, cy + 16 * s], int(16 * s), outline=(170, 190, 215), width=int(6 * s))

# ---------- scenes: return (img, arr) ----------
def S_hook(sc, lt, dur, t):
    img = base(t); arr = np.asarray(img).astype(np.float32); cx, cy = W / 2 - 60, 980
    beams(arr, cx, cy, 0.95 + t * 2.2 * sc.get("spin", 1.0), k=1.3); star(arr, cx, cy, 18, 1.2)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)); spoon(ImageDraw.Draw(img), cx, cy, 1.1)
    title(img, "ONE TEASPOON", 92, 250); title(img, "= BILLIONS OF TONS", 76, 370, (170, 215, 255))
    if sc.get("loop"): title(img, "& FASTER THAN YOUR BLENDER", 46, 1300, (200, 220, 255), u=ease(lt / 0.3))
    return img
def S_core(sc, lt, dur, t):
    img = base(t); arr = np.asarray(img).astype(np.float32); cx, cy = W / 2, 900
    p = ease((lt - 0.4) / 1.2); r = 330 * (1 - p) + 12 * p
    L = light_layer(); ImageDraw.Draw(L).ellipse([cx - r, cy - r, cx + r, cy + r], fill=200); add_light(arr, L, np.array([120, 170, 255]), 1.0, blur=8)
    if p > 0.95:
        q = ease((lt - 1.6) / 0.8); rr = 60 + 700 * q
        L = light_layer(); ImageDraw.Draw(L).ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=int(255 * (1 - q)), width=10); add_light(arr, L, ICE, 1.0, blur=6); star(arr, cx, cy, 12)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)); title(img, "A DEAD STAR'S", 78, 250); title(img, "CRUSHED CORE", 92, 360, (170, 215, 255))
    return img
def S_city(sc, lt, dur, t):
    img = base(t); arr = np.asarray(img).astype(np.float32); cx, cy = W / 2, 980
    star(arr, cx, cy - 160, 120, 0.9)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(img); r = random.Random(4); x = 60
    while x < W - 60:
        w_ = r.uniform(40, 110); h_ = r.uniform(80, 360); d.rectangle([x, 1240 - h_, x + w_, 1240], fill=(16, 22, 36), outline=(70, 90, 120), width=2); x += w_ + 6
    title(img, "MORE MASS THAN THE SUN", 62, 250); title(img, "IN A BALL THE SIZE OF A CITY", 52, 340, (170, 215, 255), u=ease((lt - 0.4) / 0.4))
    return img
def S_dense(sc, lt, dur, t):
    img = base(t); arr = np.asarray(img).astype(np.float32); cx, cy = W / 2, 900
    r = random.Random(2)
    for k in range(26):
        a = k * 2.4; rr = 26 * math.sqrt(k); x, y = cx + rr * math.cos(a + t * 0.4), cy + rr * math.sin(a + t * 0.4)
        L = light_layer(); ImageDraw.Draw(L).ellipse([x - 34, y - 34, x + 34, y + 34], fill=230 if k % 2 else 150); add_light(arr, L, ICE if k % 2 else np.array([255, 255, 255]), 0.8, blur=3)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    title(img, "AS DENSE AS", 70, 250); title(img, "AN ATOM'S NUCLEUS", 82, 350, (170, 215, 255))
    if lt > 1.4:
        v = int(3_000_000_000 * eout((lt - 1.4) / 1.2)); title(img, f"{v:,}+", 92, 1250, WHITE); title(img, "TONS PER TEASPOON", 50, 1370, (170, 215, 255))
    return img
def S_spin(sc, lt, dur, t):
    img = base(t); arr = np.asarray(img).astype(np.float32); cx, cy = W / 2, 960
    for k in range(6): beams(arr, cx, cy, t * 30 + k * 0.05, width=0.05, k=0.35)
    star(arr, cx, cy, 16)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    v = int(716 * eout((lt - 0.2) / 1.2)); title(img, str(v), 210, 230, WHITE, track=0.05); title(img, "SPINS PER SECOND", 56, 470, (170, 215, 255))
    if lt > 1.6: title(img, "≈ 2× A KITCHEN BLENDER", 54, 1320, WHITE, u=ease((lt - 1.6) / 0.4))
    return img
def S_end(sc, lt, dur, t):
    img = base(t); arr = np.asarray(img).astype(np.float32); beams(arr, W / 2, 1300, t * 2.2, k=0.6); star(arr, W / 2, 1300, 10)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(img)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.2); cx, cy, w_, h_ = W / 2, 900, 320, 140
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, outline=(170, 215, 255), width=6, fill=(60, 120, 200) if on > 0.5 else (10, 14, 24))
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; d.ellipse([kx - h_ / 2 + 18, cy - h_ / 2 + 18, kx + h_ / 2 - 18, cy + h_ / 2 - 18], fill=WHITE)
    d.text((cx - w_ / 2 - 40, cy), "FAKE", font=F(60), fill=WHITE if on < 0.5 else DIM, anchor="rm"); d.text((cx + w_ / 2 + 40, cy), "TRUE", font=F(60), fill=(170, 215, 255) if on >= 0.5 else DIM, anchor="lm")
    title(img, "SOUNDS FAKE ?!", 90, 330)
    return img
SCENES = dict(hook=S_hook, core=S_core, city=S_city, dense=S_dense, spin=S_spin, end=S_end)

voice, words, total = narrate(spec, lead=0.08, default_gap=0.22, tail=0.6)
n = len(voice); tt = np.arange(n) / SR; music = np.zeros(n, np.float32)
music += 0.05 * np.sin(2 * np.pi * 36.7 * tt) * (0.5 + 0.5 * np.sin(2 * np.pi * tt / 4) ** 2)          # deep drone
for k in range(int(total / 0.5)): place(music, k * 0.5, tone(1760, 0.08, decay=60, harm=(1,)), 0.03 if k % 2 else 0.06)  # pulsar ticks
for k in range(int(total / 4) + 1): place(music, k * 4, tone([146.83, 130.81, 116.54, 130.81][k % 4], 4.5, decay=0.7, harm=(1, 2, 3)), 0.05)
hook_hit(music, 0.45)
for s_ in scene_starts(spec): whoosh(music, s_, 0.16)
write_audio(voice, music, work + "_audio.wav", music_gain=0.6, duck=0.3)

groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0].upper() for i in g]; size = 62
    while d.textlength(" ".join(ws), font=F(size, "Bold")) > W - 160 and size > 34: size -= 4
    f = F(size, "Bold"); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1610
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=(170, 215, 255) if on else WHITE, stroke_width=6, stroke_fill=(0, 0, 0)); x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t)
    img = Image.fromarray(finish(np.asarray(img).astype(np.float32), fi))
    caption(img, t); ImageDraw.Draw(img).rectangle([0, H - 8, int(W * t / total), H], fill=(170, 215, 255))
    return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path, crf=26); print(f"done {total:.1f}s")
