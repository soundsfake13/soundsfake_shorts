"""Day 11 — HANAFUDA style (Nintendo began in 1889 making flower cards).
Lacquer-black table with seigaiha wave pattern, cream cards with flat woodblock plants (moon over grass,
crane under red sun, cherry blossom with poem ribbon, plum), cards flip and get dealt; koto-like plucks.
Generic cards only — no logos, characters or products.
Usage: python3 engine/styles/day11_hanafuda.py spec.json out.mp4 [t1,t2 preview]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from core import *

spec = json.load(open(sys.argv[1])); out_path = sys.argv[2]; work = out_path[:-4]
SERIF = lambda s: ImageFont.truetype(f"{FONTS}/DMSerifDisplay-Regular.ttf", max(8, int(s)))
def PF(s, w=800):
    f = ImageFont.truetype(f"{FONTS}/PlayfairDisplay.ttf", max(8, int(s))); f.set_variation_by_axes([w]); return f
INK, RED, CREAM, GOLD, PINK, GREEN, SKY = (22, 16, 16), (200, 30, 36), (244, 234, 212), (214, 170, 70), (240, 160, 180), (40, 90, 60), (226, 70, 50)

def make_bg():
    img = Image.new("RGB", (W, H), (28, 14, 14)); d = ImageDraw.Draw(img)
    for row in range(-1, H // 60 + 2):                                   # seigaiha waves
        for col in range(-1, W // 120 + 2):
            cx = col * 120 + (60 if row % 2 else 0); cy = row * 60
            for r in (60, 44, 28): d.arc([cx - r, cy - r, cx + r, cy + r], 180, 360, fill=(52, 24, 22), width=4)
    a = np.asarray(img).astype(np.float32); yy, xx = np.mgrid[0:H, 0:W]
    v = 1 - 0.55 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2.2
    return (a * v[..., None]).clip(0, 255).astype(np.uint8)
BG = make_bg()

CW, CH = 300, 480
def card_img(kind):
    im = Image.new("RGBA", (CW, CH), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, CW - 1, CH - 1], 22, fill=(60, 20, 20)); d.rounded_rectangle([10, 10, CW - 11, CH - 11], 14, fill=CREAM)
    if kind == "back":
        d.rounded_rectangle([10, 10, CW - 11, CH - 11], 14, fill=(30, 14, 14))
        for k in range(6): d.rounded_rectangle([30 + k * 8, 30 + k * 8, CW - 31 - k * 8, CH - 31 - k * 8], 10, outline=RED if k % 2 == 0 else GOLD, width=3)
        d.ellipse([CW / 2 - 50, CH / 2 - 50, CW / 2 + 50, CH / 2 + 50], fill=RED)
        return im
    if kind == "moon":
        d.rectangle([10, 10, CW - 11, 300], fill=SKY); d.ellipse([60, 70, 240, 250], fill=CREAM)
        d.pieslice([-200, 340, CW + 200, 760], 180, 360, fill=INK)
        for k in range(14): x = 20 + k * 20; d.line([(x, 400), (x + 18 * math.sin(k), 300 + 25 * (k % 3))], fill=INK, width=6)
    elif kind == "crane":
        d.ellipse([140, 50, 280, 190], fill=RED)
        d.polygon([(30, 300), (150, 250), (270, 300), (150, 330)], fill=GREEN); d.polygon([(10, 380), (150, 320), (290, 380), (150, 410)], fill=GREEN)
        d.rectangle([140, 300, 160, CH - 12], fill=(90, 50, 30))
        d.ellipse([60, 170, 180, 240], fill="white", outline=INK, width=3); d.line([(160, 190), (220, 120)], fill="white", width=14)
        d.ellipse([210, 105, 240, 135], fill="white"); d.ellipse([218, 108, 232, 122], fill=RED); d.line([(240, 120), (275, 128)], fill=INK, width=6)
        d.polygon([(70, 200), (20, 150), (110, 190)], fill=INK)
    elif kind == "sakura":
        d.rectangle([10, 10, CW - 11, 160], fill=(250, 214, 220))
        r = random.Random(4)
        for k in range(16):
            x, y = r.uniform(30, 270), r.uniform(30, 300)
            for j in range(5): a = j * 2 * math.pi / 5; d.ellipse([x + 16 * math.cos(a) - 14, y + 16 * math.sin(a) - 14, x + 16 * math.cos(a) + 14, y + 16 * math.sin(a) + 14], fill=PINK)
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=RED)
        d.polygon([(110, 260), (200, 250), (210, 420), (120, 430)], fill=RED)
        d.polygon([(30, 450), (CW - 30, 430), (CW - 11, CH - 12), (10, CH - 12)], fill=INK)
    elif kind == "plum":
        d.rectangle([10, 10, CW - 11, 200], fill=RED)
        d.line([(20, 460), (120, 300), (240, 200), (290, 120)], fill=INK, width=18); d.line([(120, 300), (60, 220)], fill=INK, width=12)
        for (x, y) in ((240, 200), (60, 220), (180, 260), (270, 140), (100, 340), (200, 230)):
            for j in range(5): a = j * 2 * math.pi / 5; d.ellipse([x + 13 * math.cos(a) - 12, y + 13 * math.sin(a) - 12, x + 13 * math.cos(a) + 12, y + 13 * math.sin(a) + 12], fill=CREAM, outline=RED, width=3)
        d.ellipse([150, 380, 230, 440], fill=(110, 140, 60))
    return im
CARDS = {k: card_img(k) for k in ("back", "moon", "crane", "sakura", "plum")}
_cache = {}
def put_card(img, kind, cx, cy, s=1.0, rot=0.0, flip=1.0):
    """flip: cos of flip angle; negative shows the back."""
    face = CARDS[kind if flip >= 0 else "back"]; sx = max(0.02, abs(flip))
    key = (kind if flip >= 0 else "back", round(s * sx, 2), round(s, 2), round(rot, 0))
    c = _cache.get(key)
    if c is None:
        c = face.resize((max(2, int(CW * s * sx)), int(CH * s)), Image.BICUBIC)
        sh = Image.new("RGBA", (c.width + 40, c.height + 40), (0, 0, 0, 0)); sh.paste((0, 0, 0, 110), (24, 30, 24 + c.width, 30 + c.height), c)
        sh.paste(c, (20, 20), c); c = sh.rotate(rot, expand=True, resample=Image.BICUBIC)
        if len(_cache) > 400: _cache.clear()
        _cache[key] = c
    img.paste(c, (int(cx - c.width / 2), int(cy - c.height / 2)), c)

def ctext(d, s, y, size, col=CREAM, font=None, maxw=W - 140):
    font = font or SERIF
    while d.textlength(s, font=font(size)) > maxw and size > 30: size -= 4
    d.text((W / 2, y), s, font=font(size), fill=col, anchor="mm"); return size

def stamp(img, s, cx, cy, size, rot=-10, u=1.0):
    if u <= 0: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); f = SERIF(size * (1.6 - 0.6 * min(1, u))); tw = d.textlength(s, font=f)
    d.rounded_rectangle([cx - tw / 2 - 34, cy - size * 0.85, cx + tw / 2 + 34, cy + size * 0.85], 14, fill=RED + (240,)); d.text((cx, cy), s, font=f, fill=CREAM + (255,), anchor="mm")
    lay = lay.rotate(rot, center=(cx, cy), resample=Image.BICUBIC); img.paste(lay, (0, 0), lay)

def S_hook(sc, lt, dur, t):
    img = Image.fromarray(BG.copy()); d = ImageDraw.Draw(img)
    ctext(d, "THE COMPANY BEHIND MARIO", 250, 62, GOLD, lambda s: PF(s, 700))
    ctext(d, "WAS BORN IN", 350, 84); ctext(d, "1889", 520, 230, RED)
    kinds = ("moon", "crane", "sakura", "plum")
    for k, kd in enumerate(kinds):
        a = (k - 1.5) * 14 + 2 * math.sin(t * 1.6 + k); fl = 1.0
        if sc.get("loop"): fl = math.cos(math.pi * 2 * ease((lt - 0.1 - k * 0.12) / 0.5))
        put_card(img, kd, W / 2 + (k - 1.5) * 170, 1080 + abs(k - 1.5) * 40, 1.0, -a, fl)
    if sc.get("loop"): stamp(img, "TO SELL CARDS?!", W / 2, 1450, 80, rot=-6, u=back(lt / 0.3))
    return img
def S_kyoto(sc, lt, dur, t):
    img = Image.fromarray(BG.copy()); d = ImageDraw.Draw(img)
    ctext(d, "KYOTO · 1889", 240, 110, GOLD)
    ctext(d, "Fusajiro Yamauchi", 360, 70, CREAM, lambda s: PF(s, 600))
    s = 1.7; cx, cy = W / 2, 930; put_card(img, "back", cx, cy, s, 0, 1)
    p = ease((lt - 0.3) / 2.2)                                            # painted top-to-bottom
    face = CARDS["moon"].resize((int(CW * s), int(CH * s)), Image.BICUBIC); hh = int(face.height * p)
    if hh > 2:
        cr = face.crop((0, 0, face.width, hh)); img.paste(cr, (int(cx - face.width / 2) + 20 - 20, int(cy - face.height / 2)), cr)
        by = cy - face.height / 2 + hh; bx = cx + 120 * math.sin(lt * 6)
        d.line([(bx, by), (bx + 90, by - 260)], fill=(150, 100, 60), width=18); d.ellipse([bx - 16, by - 16, bx + 16, by + 16], fill=INK)
    if lt > 2.0: ctext(d, "HANAFUDA = \"FLOWER CARDS\"", 1490, 60, CREAM, lambda s: PF(s, 700))
    return img
def S_deal(sc, lt, dur, t):
    img = Image.fromarray(BG.copy()); d = ImageDraw.Draw(img)
    ctext(d, "A HIT WITH GAMBLERS", 250, 90, CREAM)
    r = random.Random(7); kinds = ("moon", "crane", "sakura", "plum")
    n = 12
    for k in range(n):
        u = eout((lt - k * 0.22) / 0.35)
        if u <= 0: continue
        tx, ty = 200 + (k % 4) * 227, 620 + (k // 4) * 330; sx, sy = W / 2, H + 300
        put_card(img, kinds[k % 4], sx + (tx - sx) * u, sy + (ty - sy) * u, 0.62, r.uniform(-12, 12) * u + 180 * (1 - u), 1)
    cnt = min(n, int(lt / 0.22))
    if lt > 1.2: stamp(img, "THE SHOP GREW", W / 2, 1520 - 60, 70, rot=-5, u=back((lt - 1.2) / 0.3))
    return img
def taxi(d, cx, cy, s):
    d.rounded_rectangle([cx - 220 * s, cy - 40 * s, cx + 220 * s, cy + 70 * s], int(30 * s), fill=GOLD, outline=INK, width=6)
    d.polygon([(cx - 120 * s, cy - 40 * s), (cx - 70 * s, cy - 120 * s), (cx + 90 * s, cy - 120 * s), (cx + 140 * s, cy - 40 * s)], fill=GOLD, outline=INK)
    d.polygon([(cx - 95 * s, cy - 45 * s), (cx - 60 * s, cy - 105 * s), (cx + 5 * s, cy - 105 * s), (cx + 5 * s, cy - 45 * s)], fill=(160, 200, 220))
    d.polygon([(cx + 20 * s, cy - 45 * s), (cx + 20 * s, cy - 105 * s), (cx + 80 * s, cy - 105 * s), (cx + 115 * s, cy - 45 * s)], fill=(160, 200, 220))
    d.rectangle([cx - 40 * s, cy - 160 * s, cx + 40 * s, cy - 122 * s], fill=RED, outline=INK, width=4)
    for wx in (-130, 130): d.ellipse([cx + (wx - 45) * s, cy + 25 * s, cx + (wx + 45) * s, cy + 115 * s], fill=INK); d.ellipse([cx + (wx - 18) * s, cy + 52 * s, cx + (wx + 18) * s, cy + 88 * s], fill=(150, 150, 150))
def rice(d, cx, cy, s, t):
    for k in range(3): x = cx + (k - 1) * 50 * s; d.arc([x - 30 * s, cy - 220 * s - 20 * abs(math.sin(t * 3 + k)) - 2, x + 30 * s, cy - 120 * s], 90, 270, fill=(200, 190, 180), width=6)
    d.ellipse([cx - 170 * s, cy - 120 * s, cx + 170 * s, cy - 40 * s], fill="white")
    d.chord([cx - 190 * s, cy - 180 * s, cx + 190 * s, cy + 120 * s], 0, 180, fill=RED, outline=INK, width=6)
    d.rectangle([cx - 70 * s, cy + 110 * s, cx + 70 * s, cy + 140 * s], fill=RED, outline=INK, width=4)
def S_weird(sc, lt, dur, t):
    img = Image.fromarray(BG.copy()); d = ImageDraw.Draw(img)
    ctext(d, "IT TRIED ALMOST", 240, 90); ctext(d, "ANYTHING", 350, 120, RED)
    u1 = back((lt - 0.9) / 0.35); u2 = back((lt - 2.2) / 0.35)
    if u1 > 0:
        x = -300 + (W / 2 + 300) * eout((lt - 0.9) / 0.6); taxi(d, x, 760, 1.2); ctext(d, "A TAXI COMPANY", 1000, 72, GOLD, lambda s: PF(s, 800))
    if u2 > 0: rice(d, W / 2, 1290, 1.1 * min(1.1, u2), t); ctext(d, "INSTANT RICE", 1500, 72, GOLD, lambda s: PF(s, 800))
    return img
def S_toys(sc, lt, dur, t):
    img = Image.fromarray(BG.copy()); d = ImageDraw.Draw(img)
    ctext(d, "THEN: TOYS...", 300, 100, CREAM)
    for k in range(3):                                                   # toy blocks
        u = back((lt - 0.2 - k * 0.2) / 0.3)
        if u <= 0: continue
        x = W / 2 + (k - 1) * 230; sz = 90 * u; col = (RED, GOLD, (60, 120, 180))[k]
        d.rounded_rectangle([x - sz, 640 - sz, x + sz, 640 + sz], 18, fill=col, outline=INK, width=6)
    u = ease((lt - 1.2) / 0.4)
    if u > 0:
        ctext(d, "...THEN VIDEO GAMES", 900, 96, RED)
        d.rounded_rectangle([W / 2 - 300, 1050, W / 2 + 300, 1400], 60, fill=(70, 70, 80), outline=INK, width=8)  # generic gamepad
        d.rectangle([W / 2 - 200, 1190, W / 2 - 100, 1230], fill=INK); d.rectangle([W / 2 - 170, 1160, W / 2 - 130, 1260], fill=INK)
        for (bx, by, c) in ((140, 1180, RED), (210, 1240, GOLD)): d.ellipse([W / 2 + bx - 34, by - 34, W / 2 + bx + 34, by + 34], fill=c)
        blink = int(t * 4) % 2
        d.text((W / 2, 1110), "PRESS START" if blink else "", font=PF(36, 700), fill=CREAM, anchor="mm")
    return img
def S_today(sc, lt, dur, t):
    img = Image.fromarray(BG.copy()); d = ImageDraw.Draw(img)
    ctext(d, "130+ YEARS LATER", 240, 96, GOLD)
    ctext(d, "IT STILL SELLS", 350, 90, CREAM)
    for k, kd in enumerate(("plum", "sakura", "crane", "moon")):
        a = -26 + k * 17; u = eout((lt - 0.2 - k * 0.15) / 0.5)
        put_card(img, kd, W / 2 + (k - 1.5) * 150 * u, 1000 + abs(k - 1.5) * 30, 1.05, -a * u, math.cos(math.pi * (1 - u)))
    if lt > 1.6: stamp(img, "FLOWER CARDS. TODAY.", W / 2, 1460, 68, rot=-5, u=back((lt - 1.6) / 0.3))
    return img
def S_end(sc, lt, dur, t):
    img = Image.fromarray(BG.copy()); d = ImageDraw.Draw(img)
    ctext(d, "SOUNDS FAKE ?!", 330, 120, CREAM)
    click = sc.get("click_at", 0.45); on = ease((lt - click) / 0.2); cx, cy, w_, h_ = W / 2, 620, 330, 150
    d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], h_ // 2, fill=RED if on > 0.5 else (90, 60, 60), outline=GOLD, width=6)
    kx = cx - w_ / 2 + h_ / 2 + (w_ - h_) * on; d.ellipse([kx - h_ / 2 + 18, cy - h_ / 2 + 18, kx + h_ / 2 - 18, cy + h_ / 2 - 18], fill=CREAM)
    d.text((cx - w_ / 2 - 30, cy), "FAKE", font=SERIF(64), fill=CREAM if on < 0.5 else (120, 100, 100), anchor="rm"); d.text((cx + w_ / 2 + 30, cy), "TRUE", font=SERIF(64), fill=RED if on >= 0.5 else (120, 100, 100), anchor="lm")
    put_card(img, "moon", W / 2, 1110, 1.3, 4 * math.sin(t * 2), 1)
    return img
SCENES = dict(hook=S_hook, kyoto=S_kyoto, deal=S_deal, weird=S_weird, toys=S_toys, today=S_today, end=S_end)

voice, words, total = narrate(spec, lead=0.08, default_gap=0.2, tail=0.6)
n = len(voice); music = np.zeros(n, np.float32)
scale = [329.63, 349.23, 440.0, 493.88, 523.25, 659.25, 698.46]        # miyako-bushi-ish (E F A B C)
r = random.Random(11)
for k in range(int(total / 0.3)):                                      # koto plucks
    if k % 4 == 3 and r.random() < 0.5: continue
    f = scale[(k * 3 + (k // 8)) % 7]; place(music, k * 0.3, tone(f, 0.9, decay=5, harm=(1, 2, 3, 4)), 0.05)
    if k % 8 == 0: place(music, k * 0.3, tone(82.41, 1.6, decay=2.5, harm=(1, 2)), 0.08)
    if k % 4 == 2: place(music, k * 0.3, tone(1800, 0.05, decay=60, harm=(1,)), 0.02)   # wood click
hook_hit(music, 0.35)
for s_ in scene_starts(spec): whoosh(music, s_, 0.1)
write_audio(voice, music, work + "_audio.wav", music_gain=0.55, duck=0.3)

groups = caption_groups(words, 3)
def caption(img, t):
    gi, g = group_at(groups, words, t)
    if g is None: return
    d = ImageDraw.Draw(img); ws = [words[i][0] for i in g]; size = 70
    while d.textlength(" ".join(ws), font=PF(size, 900)) > W - 200 and size > 36: size -= 4
    f = PF(size, 900); tw = d.textlength(" ".join(ws), font=f); x = (W - tw) / 2; y = 1640
    d.rounded_rectangle([x - 30, y - 14, x + tw + 30, y + size + 30], 18, fill=CREAM)
    for i, w in zip(g, ws):
        on = words[i][1] <= t < words[i][2] + 0.05
        d.text((x, y), w, font=f, fill=RED if on else INK); x += d.textlength(w + " ", font=f)

def frame(t, fi):
    ln = active_line(spec, t) or spec["lines"][0]; lt = max(0.0, t - ln["_s"]); dur = ln["_se"] - ln["_s"]
    img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, t); caption(img, t)
    ImageDraw.Draw(img).rectangle([0, H - 10, int(W * t / total), H], fill=RED); return img.tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        for tt_ in sys.argv[3].split(","): Image.frombytes("RGB", (W, H), frame(float(tt_), 0)).save(f"{work}_f{tt_}.png")
    else:
        render(total, frame, work + "_audio.wav", out_path); print(f"done {total:.1f}s")
