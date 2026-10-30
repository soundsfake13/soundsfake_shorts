"""Kinetic-type YouTube Short renderer: flat color blocks, bold motion-blurred type,
3D cube, cursor + toggle beats, punchy beat.

Usage: python3 kinetic_short.py spec.json out.mp4
"""
import json, math, os, random, subprocess, sys
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from kokoro_onnx import Kokoro

W, H, FPS, SR = 1080, 1920, 30, 24000
FD = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/inter/").rstrip("/") + "/"
FB = lambda s: ImageFont.truetype(FD + "InterDisplay-Black.otf", s)
FS = lambda s: ImageFont.truetype(FD + "InterDisplay-Bold.otf", s)
RED, BLUE, CREAM, INK, YEL = (232, 58, 44), (36, 66, 220), (246, 240, 228), (16, 16, 22), (255, 210, 60)
COL = {"red": RED, "blue": BLUE, "cream": CREAM, "ink": INK, "yellow": YEL}
random.seed(5)

spec = json.load(open(sys.argv[1]))
out_path = sys.argv[2]
work = out_path.rsplit(".", 1)[0]
BPM = spec.get("bpm", 118); BEAT = 60 / BPM

# ================= narration =================
KD = os.path.expanduser(os.environ.get("KOKORO_DIR", "~/.cache/kokoro"))
tts = Kokoro(os.path.join(KD, "kokoro.onnx"), os.path.join(KD, "voices.bin"))
t, parts, words = 0.25, [np.zeros(int(SR * 0.25), np.float32)], []
for si, ln in enumerate(spec["lines"]):
    s, _ = tts.create(ln["text"], voice=spec.get("voice", "am_michael"), speed=spec.get("speed", 1.12), lang="en-us")
    nz = np.where(np.abs(s) > 0.01)[0]
    s = s[max(nz[0] - 500, 0): nz[-1] + 900]
    dur = len(s) / SR
    toks = ln.get("caption", ln["text"]).split()
    wts = [len(w.strip(".,!?…\"'")) + 2.5 for w in toks]
    acc, tot = 0, sum(wts)
    ln["_w0"] = len(words)
    for w, wt in zip(toks, wts):
        a = t + dur * acc / tot; acc += wt
        words.append((w, a, t + dur * acc / tot, si))
    ln["_w1"] = len(words)
    ln["_s"], ln["_e"] = t, t + dur
    gap = ln.get("pause", 0.18)
    parts += [s.astype(np.float32), np.zeros(int(SR * gap), np.float32)]
    t += dur + gap
for i, ln in enumerate(spec["lines"]):
    ln["_se"] = spec["lines"][i + 1]["_s"] if i + 1 < len(spec["lines"]) else t + 1.0
voice = np.concatenate(parts)
total = len(voice) / SR + 0.8
voice = np.pad(voice, (0, int(SR * total) - len(voice)))

# ================= beat =================
n = len(voice); tt = np.arange(n) / SR
mus = np.zeros(n, np.float32)
rs = np.random.default_rng(2)
def add(at, sig, gain=1.0):
    a = int(at * SR); b = min(a + len(sig), n)
    if a < n: mus[a:b] += sig[: b - a] * gain
kl = np.arange(int(0.35 * SR)) / SR
kick = np.sin(2 * np.pi * (45 * kl + 90 * (1 - np.exp(-kl * 30)) / 30)) * np.exp(-kl * 9)
sl = np.arange(int(0.18 * SR)) / SR
snare = (rs.normal(0, 1, len(sl)) * 0.6 + np.sin(2 * np.pi * 190 * sl)) * np.exp(-sl * 22)
hl = np.arange(int(0.05 * SR)) / SR
hat = np.diff(rs.normal(0, 1, len(hl) + 1)) * np.exp(-hl * 90)
bass_notes = [55.0, 55.0, 65.41, 49.0]
stab_ch = [[220.0, 261.63, 329.63], [220.0, 261.63, 329.63], [261.63, 329.63, 392.0], [196.0, 246.94, 293.66]]
nb = int(total / BEAT)
for b in range(nb):
    at = b * BEAT; bar = (b // 4) % 4
    if b % 4 in (0, 2) or (b % 8 == 7): add(at, kick, 0.55)
    if b % 4 in (1, 3): add(at, snare, 0.22)
    for h in range(2): add(at + h * BEAT / 2, hat, 0.08 if h else 0.05)
    bl = np.arange(int(BEAT * 0.9 * SR)) / SR
    f = bass_notes[bar]
    add(at, (np.sign(np.sin(2 * np.pi * f * bl)) * 0.3 + np.sin(2 * np.pi * f * bl)) * np.exp(-bl * 3), 0.10)
    if b % 4 == 0:
        sl2 = np.arange(int(0.22 * SR)) / SR
        add(at + BEAT * 1.5, sum(np.sign(np.sin(2 * np.pi * q * sl2)) for q in stab_ch[bar]) * np.exp(-sl2 * 14), 0.03)
mus *= np.clip(tt / 0.3, 0, 1) * np.clip((total - tt) / 0.8, 0, 1)
# duck music under the voice a little
env = np.convolve(np.abs(voice), np.ones(2400) / 2400, mode="same")
mus *= 1 - 0.45 * np.clip(env * 12, 0, 1)
mix = voice + mus * 0.75
mix = mix / np.abs(mix).max() * 0.93
sf.write(work + "_audio.wav", mix, SR)

# ================= helpers =================
def ease(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def eout(u): u = max(0.0, min(1.0, u)); return 1 - (1 - u) ** 3
def back(u):
    u = max(0.0, min(1.0, u)); c = 1.9
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2

def hblur(alpha, L):
    """Horizontal motion blur of an alpha array by L px (box kernel via cumsum)."""
    L = int(abs(L))
    if L < 2: return alpha
    p = np.pad(alpha, ((0, 0), (L, L)), mode="constant")
    c = np.cumsum(p, axis=1, dtype=np.float32)
    out = (c[:, L * 2:] - c[:, :-L * 2]) / (2 * L)
    return out[:, :alpha.shape[1]]

def vblur(alpha, L):
    return hblur(alpha.T, L).T

def kin_text(img, text, size, color, cx, cy, vx=0.0, vy=0.0, font=None, anchor="mm", scale=1.0):
    """Draw text with directional motion blur proportional to velocity (px/frame)."""
    f = (font or FB)(max(8, int(size * scale)))
    m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).text((cx, cy), text, font=f, fill=255, anchor=anchor)
    a = np.asarray(m).astype(np.float32) / 255
    if abs(vx) > 1.5: a = hblur(a, vx * 0.9)
    if abs(vy) > 1.5: a = vblur(a, vy * 0.9)
    layer = Image.new("RGBA", (W, H), color + (0,))
    layer.putalpha(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)))
    img.alpha_composite(layer)

def fit_size(text, size, maxw, font=FB):
    d = ImageDraw.Draw(Image.new("L", (4, 4)))
    while d.textlength(text, font=font(size)) > maxw and size > 30: size -= 6
    return size

def cube(img, cx, cy, s, rx, ry, rz=0.0, colors=(CREAM, (200, 196, 186), (150, 146, 140)), edge=INK, ew=6):
    """Flat-shaded 3D cube via painter's algorithm."""
    V = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], np.float32)
    def rot(v, a, i, j):
        c, sn = math.cos(a), math.sin(a); v = v.copy()
        v[:, i], v[:, j] = c * v[:, i] - sn * v[:, j], sn * v[:, i] + c * v[:, j]
        return v
    P = rot(rot(rot(V, rx, 1, 2), ry, 0, 2), rz, 0, 1)
    faces = [(0, 1, 3, 2), (4, 5, 7, 6), (0, 1, 5, 4), (2, 3, 7, 6), (0, 2, 6, 4), (1, 3, 7, 5)]
    light = np.array([-0.4, -0.7, -0.6]); light /= np.linalg.norm(light)
    proj = lambda p: (cx + p[0] * s / (1 + p[2] * 0.12), cy + p[1] * s / (1 + p[2] * 0.12))
    d = ImageDraw.Draw(img)
    order = sorted(faces, key=lambda f: -np.mean(P[list(f), 2]))
    for f in order:
        pts = P[list(f)]
        nrm = np.cross(pts[1] - pts[0], pts[2] - pts[0]); nrm /= (np.linalg.norm(nrm) + 1e-6)
        if nrm[2] > 0: nrm = -nrm
        lam = float(np.dot(nrm, light))
        base = np.array(colors[0], np.float32) * (0.55 + 0.45 * max(0, lam))
        d.polygon([proj(p) for p in pts], fill=tuple(int(x) for x in base), outline=edge, width=ew)

def cursor(img, x, y, press=0.0):
    d = ImageDraw.Draw(img); s = 1.6 * (1 - 0.15 * press)
    pts = [(0, 0), (0, 34), (9, 26), (15, 40), (21, 37), (15, 24), (27, 24)]
    P = [(x + px * s, y + py * s) for px, py in pts]
    d.polygon([(px + 4, py + 4) for px, py in P], fill=(0, 0, 0, 90))
    d.polygon(P, fill=CREAM, outline=INK, width=4)

def toggle(img, cx, cy, on, left, right, w=300, h=150):
    d = ImageDraw.Draw(img)
    tc = tuple(int(BLUE[i] * (1 - on) + RED[i] * on) for i in range(3))
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], h / 2, fill=tc, outline=INK, width=8)
    kx = cx - w / 2 + h / 2 + (w - h) * ease(on)
    d.ellipse([kx - h / 2 + 16, cy - h / 2 + 16, kx + h / 2 - 16, cy + h / 2 - 16], fill=CREAM, outline=INK, width=6)
    d.text((cx - w / 2 - 40, cy), left, font=FB(78), fill=CREAM if on < 0.5 else (110, 110, 125), anchor="rm")
    d.text((cx + w / 2 + 40, cy), right, font=FB(78), fill=CREAM if on >= 0.5 else (110, 110, 125), anchor="lm")

# ================= scenes =================
def bg(c): return Image.new("RGBA", (W, H), COL[c] + (255,))

def sc_slam(sc, lt, dur, ln):
    """Stacked words slam in one by one from alternating sides, with motion blur."""
    img = bg(sc.get("bg", "red"))
    lines = sc["lines"]; size = sc.get("size", 230)
    y0 = sc.get("y", 560); gapy = int(size * 0.95)
    for i, w in enumerate(lines):
        st = i * sc.get("stagger", 0.32)
        u = (lt - st) / 0.28
        if u <= 0: continue
        side = -1 if i % 2 == 0 else 1
        p = back(u); pp = back(u - 1 / (0.28 * FPS))
        x = W / 2 + side * (1 - p) * 1100; vx = side * (pp - p) * 1100
        col = COL[sc.get("colors", ["cream"] * 9)[i % len(sc.get("colors", ["cream"]))]]
        sz = fit_size(w, size, W - 100)
        kin_text(img, w, sz, col, x, y0 + i * gapy, vx=vx)
    if sc.get("cube"):
        u = ease((lt - 0.9) / 0.5)
        if u > 0:
            cube(img, W / 2, 1250, 120 * u, lt * 1.3 + 0.5, lt * 1.9, colors=(CREAM,))
    return img

def sc_flash(sc, lt, dur, ln):
    """Each spoken word flashes full-screen, alternating color blocks (the 'word-by-word' beat)."""
    t_abs = ln["_s"] + lt
    idx = ln["_w0"]
    for i in range(ln["_w0"], ln["_w1"]):
        if words[i][1] - 0.05 <= t_abs: idx = i
    k = idx - ln["_w0"]
    pal = sc.get("palette", ["blue", "cream", "red"])
    bgc = pal[k % len(pal)]
    img = bg(bgc)
    fg = CREAM if bgc != "cream" else INK
    w = words[idx][0].strip(".,!?").upper()
    lw = t_abs - words[idx][1]
    s = 1.0 + 0.25 * (1 - eout(lw / 0.18))
    kin_text(img, w, fit_size(w, 300, W - 90), fg, W / 2, 900, vy=-(1 - eout(lw / 0.12)) * 40, scale=s)
    if sc.get("cube"):
        cube(img, W / 2, 1330, 110, lt * 1.1 + 0.4, lt * 1.7, colors=(CREAM if bgc != "cream" else BLUE,))
    return img

def sc_cube(sc, lt, dur, ln):
    """Big spinning cube on a color block; snaps 90° on each beat."""
    img = bg(sc.get("bg", "blue"))
    beats = lt / BEAT
    snap = math.floor(beats) + eout((beats % 1) / 0.45)
    ry = snap * math.pi / 2 + 0.6; rx = 0.55 + 0.08 * math.sin(lt * 2)
    sc_in = back(lt / 0.35)
    cube(img, W / 2, sc.get("y", 860), 260 * sc_in, rx, ry, colors=(COL[sc.get("cube_color", "cream")],), ew=8)
    if "label" in sc:
        u = back((lt - 0.2) / 0.3)
        kin_text(img, sc["label"], fit_size(sc["label"], 150, W - 100), CREAM, W / 2, 330 - (1 - u) * 200)
    return img

def sc_grid(sc, lt, dur, ln):
    """Tiny cubes popping into a grid with a counter."""
    img = bg(sc.get("bg", "red"))
    nmax = sc.get("count", 100); cols = 10
    shown = int(nmax * ease(lt / max(0.8, dur - 0.5)))
    cs = 74; x0 = (W - cols * cs) / 2 + cs / 2; y0 = 520
    for k in range(shown):
        r, c = divmod(k, cols)
        cube(img, x0 + c * cs, y0 + r * cs, 24, 0.6, 0.7 + k * 0.05, colors=(CREAM,), ew=3)
    kin_text(img, str(shown), 230, CREAM, W / 2, 330)
    kin_text(img, sc.get("label", "PER NIGHT"), 72, INK, W / 2, 1330, font=FB)
    return img

def sc_big(sc, lt, dur, ln):
    """One big glyph/phrase that punches in, optional sub."""
    img = bg(sc.get("bg", "ink"))
    u = back(lt / 0.3)
    col = COL[sc.get("color", "yellow")]
    kin_text(img, sc["text"], fit_size(sc["text"], sc.get("size", 560), W - 80), col, W / 2, sc.get("y", 860), scale=max(0.05, u))
    if "sub" in sc:
        u2 = eout((lt - 0.35) / 0.3)
        kin_text(img, sc["sub"], fit_size(sc["sub"], 90, W - 100), CREAM, W / 2 + (1 - u2) * 600, 1260, vx=-(1 - u2) * 50)
    return img

def sc_squeeze(sc, lt, dur, ln):
    """Gut diagram: stiff (red) and stretchy (blue) bands squeeze a round blob into a cube."""
    img = bg("cream"); d = ImageDraw.Draw(img)
    cx, cy = W / 2, 880
    # tube walls
    d.rectangle([0, cy - 300, W, cy - 250], fill=INK); d.rectangle([0, cy + 250, W, cy + 300], fill=INK)
    for i in range(6):
        x = 40 + i * 180
        stiff = i % 2 == 0
        d.rectangle([x, cy - 250, x + 160, cy - 225 if not stiff else cy - 205], fill=RED if stiff else BLUE)
        d.rectangle([x, cy + 225 if not stiff else cy + 205, x + 160, cy + 250], fill=RED if stiff else BLUE)
    m = ease((lt - 0.4) / max(0.8, dur - 1.0))
    r = 170; rad = r * (1 - 0.95 * m)
    bx = cx - 250 + 250 * ease(lt / 1.0)
    d.rounded_rectangle([bx - r, cy - r, bx + r, cy + r], rad, fill=(120, 82, 52), outline=INK, width=8)
    kin_text(img, "STIFF", 64, RED, 230, cy - 400)
    kin_text(img, "STRETCHY", 64, BLUE, W - 270, cy - 400)
    lab = "→ CORNERS" if m > 0.85 else ""
    if lab: kin_text(img, lab, 96, INK, W / 2, cy + 420)
    return img

def sc_rock(sc, lt, dur, ln):
    """Ball rolls off the rock, cube stays put."""
    img = bg("blue"); d = ImageDraw.Draw(img)
    d.polygon([(120, 1200), (300, 960), (760, 930), (980, 1200)], fill=INK)
    d.rectangle([0, 1200, W, 1240], fill=INK)
    # stacked cubes on the rock
    for k, (x, y) in enumerate([(470, 860), (560, 860), (515, 775)]):
        u = back((lt - k * 0.25) / 0.3)
        if u > 0: cube(img, x, y - (1 - u) * 300, 44, 0.45, 0.6, colors=(CREAM,), ew=4)
    # rolling ball
    p = ease((lt - 0.9) / 1.4)
    if lt > 0.3:
        bx = 700 + p * 600; by = 880 + (p ** 2) * 380 if p > 0.12 else 880
        d.ellipse([bx - 44, by - 44, bx + 44, by + 44], fill=(170, 160, 150), outline=INK, width=4)
    kin_text(img, "STAYS PUT", 110, CREAM, W / 2, 470)
    return img

def sc_toggle(sc, lt, dur, ln):
    """Cursor glides in and flips FAKE -> TRUE."""
    img = bg(sc.get("bg", "ink"))
    click = sc.get("click_at", 1.1)
    on = ease((lt - click) / 0.25)
    toggle(img, W / 2, 900, on, sc.get("left", "FAKE"), sc.get("right", "TRUE"))
    mx = W / 2 - 110 + 220 * on
    px = W + 100 + (mx - W - 100) * eout(lt / (click - 0.05)) if lt < click else mx
    py = 1280 + (930 - 1280) * eout(lt / (click - 0.05)) if lt < click else 930
    press = 1.0 if click - 0.04 < lt < click + 0.12 else 0.0
    cursor(img, px, py, press)
    if lt > click + 0.35:
        u = back((lt - click - 0.35) / 0.3)
        kin_text(img, sc.get("title", "SOUNDS FAKE ?!"), fit_size(sc.get("title", "SOUNDS FAKE ?!"), 130, W - 100), YEL, W / 2, 520, scale=max(0.05, u))
        if sc.get("sub"): kin_text(img, sc["sub"], 64, CREAM, W / 2, 1180)
    return img

# ---------- flat Venus scenes ----------
_ptex = {}
def flat_planet(img, cx, cy, r, rot, base=CREAM, band=RED):
    key = (r, base, band)
    if key not in _ptex:
        tw = 4 * r; tex = Image.new("RGB", (tw * 2, 2 * r), base); d = ImageDraw.Draw(tex)
        for i, (yf, th) in enumerate([(0.18, 0.07), (0.36, 0.11), (0.58, 0.08), (0.76, 0.12), (0.9, 0.05)]):
            pts_top = [(x, 2 * r * yf + 0.04 * r * math.sin(x / r * 3 + i)) for x in range(0, tw * 2 + 20, 20)]
            pts_bot = [(x, y + 2 * r * th) for x, y in reversed(pts_top)]
            d.polygon(pts_top + pts_bot, fill=band if i % 2 == 0 else tuple(int(c * 0.82) for c in base))
        m = Image.new("L", (2 * r, 2 * r), 0); ImageDraw.Draw(m).ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=255)
        _ptex[key] = (tex, m, tw)
    tex, m, tw = _ptex[key]
    off = int((rot % 1) * tw)
    img.paste(tex.crop((off, 0, off + 2 * r, 2 * r)), (int(cx - r), int(cy - r)), m)
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=INK, width=max(4, r // 30))
    # flat shadow crescent
    sh = Image.new("L", (2 * r, 2 * r), 0); sd = ImageDraw.Draw(sh)
    sd.ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=70); sd.ellipse([-r * 0.35, -r * 0.35, 2 * r * 0.92, 2 * r * 0.92], fill=0)
    img.paste(Image.new("RGBA", (2 * r, 2 * r), INK + (255,)), (int(cx - r), int(cy - r)), sh)

def flat_arrow(img, cx, cy, R, a0, a1, prog, col=CREAM, w=22):
    d = ImageDraw.Draw(img)
    k = max(2, int(40 * prog))
    pts = [(cx + R * math.cos(math.radians(a0 + (a1 - a0) * i / 40)), cy + R * math.sin(math.radians(a0 + (a1 - a0) * i / 40))) for i in range(k)]
    d.line(pts, fill=col, width=w, joint="curve")
    if len(pts) > 3:
        ex, ey = pts[-1]; px, py = pts[-4]; ang = math.atan2(ey - py, ex - px)
        d.polygon([(ex + 55 * math.cos(ang), ey + 55 * math.sin(ang)), (ex + 42 * math.cos(ang + 2.3), ey + 42 * math.sin(ang + 2.3)), (ex + 42 * math.cos(ang - 2.3), ey + 42 * math.sin(ang - 2.3))], fill=col)

def counter(img, value, y, col, label=None, lcol=CREAM, lt=0.0):
    pop = 1 + 0.06 * (1 - eout((lt * 8) % 1))
    kin_text(img, str(value), 250, col, W / 2, y, scale=pop)
    if label: kin_text(img, label, 64, lcol, W / 2, y + 170)

def sc_planet(sc, lt, dur, ln):
    img = bg(sc.get("bg", "blue"))
    sgn = sc.get("dir", 1)
    r = int(sc.get("r", 300) * back(lt / 0.4)) or 1
    cy = sc.get("y", 860)
    flat_planet(img, W / 2, cy, r, lt / sc.get("spin_secs", 20) * sgn)
    if sc.get("arrow"):
        a0, a1 = (-150, -30) if sgn > 0 else (-30, -150)
        flat_arrow(img, W / 2, cy, sc.get("r", 300) + 80, a0, a1, eout((lt - 0.2) / 0.5), COL[sc.get("arrow_color", "yellow")])
    if "label" in sc:
        u = back((lt - 0.1) / 0.3); lbl = sc["label"]
        kin_text(img, lbl, fit_size(lbl, 150, W - 100), CREAM, W / 2 + (1 - u) * 900, 330, vx=-(1 - u) * 60)
    if "count" in sc:
        v = int(sc["count"] * ease((lt - 0.2) / max(1, dur - 0.7)))
        counter(img, v, 1300, YEL, sc.get("count_label", "EARTH DAYS"), lt=lt)
    return img

def sc_orbit(sc, lt, dur, ln):
    img = bg(sc.get("bg", "ink")); d = ImageDraw.Draw(img)
    cx, cy, R = W / 2, 820, 360
    for k in range(48):   # dashed orbit
        a = k / 48 * 2 * math.pi
        if k % 2 == 0: d.arc([cx - R, cy - R, cx + R, cy + R], math.degrees(a), math.degrees(a) + 360 / 48, fill=(70, 72, 90), width=6)
    p = ease(lt / max(1, dur - 0.4))
    steps = int(p * 120)
    if steps > 1:
        d.arc([cx - R, cy - R, cx + R, cy + R], -90, -90 + 360 * p, fill=RED, width=14)
    s = back(lt / 0.35)
    d.ellipse([cx - 95 * s, cy - 95 * s, cx + 95 * s, cy + 95 * s], fill=YEL, outline=INK, width=6)
    for k in range(12):   # flat sun rays
        a = k / 12 * 2 * math.pi + lt * 0.8
        d.line([(cx + 120 * s * math.cos(a), cy + 120 * s * math.sin(a)), (cx + 160 * s * math.cos(a), cy + 160 * s * math.sin(a))], fill=YEL, width=12)
    ang = -math.pi / 2 + p * 2 * math.pi
    flat_planet(img, cx + R * math.cos(ang), cy + R * math.sin(ang), 60, p * 0.9)
    counter(img, int(sc["days"] * p), 1300, YEL, sc.get("count_label", "DAYS AROUND THE SUN"), lt=lt)
    if "label" in sc:
        u = back((lt - 0.1) / 0.3)
        kin_text(img, sc["label"], fit_size(sc["label"], 130, W - 100), CREAM, W / 2 - (1 - u) * 900, 300, vx=(1 - u) * 60)
    return img

def sc_bars(sc, lt, dur, ln):
    img = bg("cream"); d = ImageDraw.Draw(img)
    kin_text(img, "ON VENUS", 120, INK, W / 2, 330)
    mx = max(r[1] for r in sc["rows"])
    for i, (label, val, col) in enumerate(sc["rows"]):
        y = 560 + i * 340
        u = eout((lt - 0.15 - i * 0.45) / 0.6)
        d.text((90, y), label, font=FB(90), fill=INK)
        bw = int((W - 180) * val / mx * max(0, u))
        d.rectangle([90, y + 120, 90 + max(bw, 12), y + 250], fill=COL[col], outline=INK, width=6)
        if u > 0.05: d.text((120, y + 185), f"{int(val * u)} DAYS", font=FB(66), fill=CREAM, anchor="lm")
    if lt > 1.5:
        u = back((lt - 1.5) / 0.3); txt = sc.get("stamp", "THE DAY WINS")
        f = FB(int(96 * max(0.05, u))); tw = d.textlength(txt, font=f)
        stamp = Image.new("RGBA", (int(tw + 80), 170), (0, 0, 0, 0)); sd = ImageDraw.Draw(stamp)
        sd.rectangle([0, 0, tw + 79, 169], fill=YEL, outline=INK, width=8)
        sd.text(((tw + 80) / 2, 85), txt, font=f, fill=INK, anchor="mm")
        stamp = stamp.rotate(-6, expand=True, resample=Image.BICUBIC)
        img.alpha_composite(stamp, (int(W / 2 - stamp.width / 2), 1240))
    return img

def flat_figure(d, x, feet, h, fill=INK):
    s = h / 100
    d.ellipse([x - 8 * s, feet - 100 * s, x + 8 * s, feet - 84 * s], fill=fill)
    d.rounded_rectangle([x - 13 * s, feet - 84 * s, x + 13 * s, feet - 34 * s], 8 * s, fill=fill)
    d.rectangle([x - 11 * s, feet - 38 * s, x - 3 * s, feet], fill=fill)
    d.rectangle([x + 3 * s, feet - 38 * s, x + 11 * s, feet], fill=fill)

def sc_sunrise(sc, lt, dur, ln):
    img = bg("red"); d = ImageDraw.Draw(img)
    p = eout(lt / max(1, dur - 0.3))
    sx, sy = 260 + 40 * p, 1250 - 500 * p
    d.ellipse([sx - 130, sy - 130, sx + 130, sy + 130], fill=YEL, outline=INK, width=8)
    d.rectangle([0, 1200, W, H], fill=INK)
    d.polygon([(0, 1200), (180, 1150), (380, 1200)], fill=INK); d.polygon([(620, 1200), (860, 1130), (1080, 1200)], fill=INK)
    flat_figure(d, 820, 1205, 210)
    for txt, x, col in (("WEST", 260, YEL), ("EAST", 820, CREAM)):
        u = back((lt - 0.4) / 0.3)
        kin_text(img, txt, 96, col, x, 1330 + (1 - u) * 200)
    kin_text(img, "SUNRISE ↑", 70, CREAM, 260, 1450) if lt > 0.9 else None
    return img

def sc_thermo(sc, lt, dur, ln):
    img = bg("red"); d = ImageDraw.Draw(img)
    x0, ytop, ybot = 300, 360, 1250
    d.rounded_rectangle([x0 - 60, ytop, x0 + 60, ybot], 60, fill=CREAM, outline=INK, width=8)
    d.ellipse([x0 - 110, ybot - 80, x0 + 110, ybot + 140], fill=INK)
    d.ellipse([x0 - 92, ybot - 62, x0 + 92, ybot + 122], fill=YEL)
    u = eout((lt - 0.2) / 1.2)
    lvl = ybot - (ybot - ytop - 70) * u * sc["value"] / sc["max"]
    d.rectangle([x0 - 34, lvl, x0 + 34, ybot], fill=YEL)
    for label, val, col in sc["marks"]:
        y = ybot - (ybot - ytop - 70) * val / sc["max"]
        d.rectangle([x0 + 75, y - 6, x0 + 140, y + 6], fill=INK)
        d.text((x0 + 165, y), label, font=FB(60), fill=COL[col], anchor="lm")
    return img

# ---------- reusable creature / life-cycle scenes ----------
def flat_jelly(img, cx, cy, r, t=0.0, body=CREAM, spot=RED, n_tent=6):
    """Flat jellyfish: dome bell with INK outline, pulsing, wavy tentacles."""
    d = ImageDraw.Draw(img)
    pulse = 1 + 0.06 * math.sin(t * 5)
    rw, rh = r * pulse, r * 0.85 / pulse
    # tentacles (behind the bell)
    for k in range(n_tent):
        x0 = cx - rw * 0.75 + k * (1.5 * rw / max(1, n_tent - 1))
        pts = [(x0 + 0.12 * r * math.sin(t * 4 + k + j * 0.6), cy + j * r * 0.16) for j in range(12)]
        d.line(pts, fill=INK, width=max(4, int(r * 0.075)), joint="curve")
        d.line(pts, fill=body, width=max(2, int(r * 0.04)), joint="curve")
    # bell
    d.pieslice([cx - rw, cy - rh, cx + rw, cy + rh], 180, 360, fill=body, outline=INK, width=max(4, int(r * 0.05)))
    d.rounded_rectangle([cx - rw, cy - r * 0.04, cx + rw, cy + r * 0.12], r * 0.08, fill=body, outline=INK, width=max(4, int(r * 0.05)))
    # inner spot (gut) + cheeks
    d.ellipse([cx - r * 0.28, cy - rh * 0.62, cx + r * 0.28, cy - rh * 0.12], fill=spot, outline=INK, width=max(3, int(r * 0.03)))
    return d

def flat_polyp(img, cx, base, h, t=0.0, body=CREAM):
    """Flat polyp: little stalk with a crown of tentacles, standing on a base line."""
    d = ImageDraw.Draw(img); w = h * 0.16
    sway = math.sin(t * 3) * h * 0.04
    d.rounded_rectangle([cx - w / 2 + sway, base - h, cx + w / 2 + sway, base], w / 2, fill=body, outline=INK, width=max(3, int(h * 0.04)))
    for k in range(5):
        a = math.radians(-160 + k * 35) + 0.15 * math.sin(t * 4 + k)
        x1, y1 = cx + sway, base - h
        d.line([(x1, y1), (x1 + h * 0.32 * math.cos(a), y1 + h * 0.32 * math.sin(a))], fill=INK, width=max(4, int(h * 0.06)))
    return d

def sc_jelly(sc, lt, dur, ln):
    """Bobbing flat jellyfish with optional label, sub-line and size ruler (e.g. '4.5 MM')."""
    img = bg(sc.get("bg", "blue"))
    r = sc.get("r", 230) * back(lt / 0.4)
    y = sc.get("y", 820) + 20 * math.sin(lt * 2.2)
    flat_jelly(img, W / 2, y, max(r, 2), lt, COL[sc.get("color", "cream")], COL[sc.get("spot", "red")])
    if "label" in sc:
        u = back((lt - 0.1) / 0.3); lbl = sc["label"]
        kin_text(img, lbl, fit_size(lbl, 150, W - 100), COL[sc.get("label_color", "cream")], W / 2 + (1 - u) * 900, 300, vx=-(1 - u) * 60)
    if "ruler" in sc and lt > 0.5:
        d = ImageDraw.Draw(img); u = eout((lt - 0.5) / 0.4); R = sc.get("r", 230)
        x0, x1, yy = W / 2 - R, W / 2 - R + 2 * R * u, y + R * 2.2
        d.rectangle([x0, yy - 8, x1, yy + 8], fill=YEL)
        d.rectangle([x0 - 8, yy - 36, x0 + 8, yy + 36], fill=YEL)
        if u > 0.95: d.rectangle([x1 - 8, yy - 36, x1 + 8, yy + 36], fill=YEL)
        kin_text(img, sc["ruler"], 110, YEL, W / 2, yy + 100)
    if "sub" in sc:
        u2 = eout((lt - 0.35) / 0.3)
        kin_text(img, sc["sub"], fit_size(sc["sub"], 90, W - 100), COL[sc.get("sub_color", "cream")], W / 2 + (1 - u2) * 600, sc.get("sub_y", 1380), vx=-(1 - u2) * 50)
    return img

def sc_cycle(sc, lt, dur, ln):
    """Life cycle: stages on a ring, a dot travels the arrows; optional highlighted
    shortcut arrow ('reverse': [from_idx, to_idx]) drawn across the middle + stamp.
    stage icons: 'jelly', 'polyp', 'dot'."""
    img = bg(sc.get("bg", "ink")); d = ImageDraw.Draw(img)
    st = sc["stages"]; n = len(st); icons = sc.get("icons", ["dot"] * n)
    cx, cy, R = W / 2, sc.get("y", 860), sc.get("R", 330)
    ang = [-math.pi / 2 + k * 2 * math.pi / n for k in range(n)]
    pos = [(cx + R * math.cos(a), cy + R * math.sin(a)) for a in ang]
    ring = sc.get("ring", "cream"); rc = (90, 92, 110) if sc.get("reverse") else COL[ring]
    p = ease((lt - 0.2) / max(0.8, sc.get("ring_secs", dur - 0.4)))
    d.arc([cx - R, cy - R, cx + R, cy + R], -90, -90 + 360 * (p if not sc.get("reverse") else 1), fill=rc, width=12)
    for k in range(n):   # arrowheads between stages
        a = ang[k] + math.pi / n
        if sc.get("reverse") or p * n > k + 0.5:
            hx, hy = cx + R * math.cos(a), cy + R * math.sin(a); ta = a + math.pi / 2
            d.polygon([(hx + 34 * math.cos(ta), hy + 34 * math.sin(ta)), (hx + 26 * math.cos(ta + 2.4), hy + 26 * math.sin(ta + 2.4)),
                       (hx + 26 * math.cos(ta - 2.4), hy + 26 * math.sin(ta - 2.4))], fill=rc)
    for k, ((x, y), lab) in enumerate(zip(pos, st)):
        u = back((lt - 0.1 * k) / 0.3)
        if u <= 0: continue
        d.ellipse([x - 105 * u, y - 105 * u, x + 105 * u, y + 105 * u], fill=COL[sc.get("node", "blue")], outline=INK, width=8)
        ic = icons[k]
        if ic == "jelly": flat_jelly(img, x, y - 10, 52 * u, lt)
        elif ic == "polyp": d.rectangle([x - 60, y + 55, x + 60, y + 62], fill=INK) if u > 0.9 else None; flat_polyp(img, x, y + 58, 95 * u, lt)
        else: d.ellipse([x - 30 * u, y - 30 * u, x + 30 * u, y + 30 * u], fill=CREAM, outline=INK, width=5)
        side = 0 if abs(x - cx) < R * 0.5 else (1 if x > cx else -1)
        ly = y - 170 if y < cy - R * 0.5 else y + 165
        lx = x + side * 80   # push side labels outward so they clear the ring
        kin_text(img, lab, fit_size(lab, 60 if side else 66, 300 if side else 420), CREAM, lx, ly)
    if sc.get("reverse"):
        a_i, b_i = sc["reverse"]; (x0, y0), (x1, y1) = pos[a_i], pos[b_i]
        q = eout((lt - 0.5) / 0.7)
        if q > 0:
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            bx, by = mx + (cx - mx) * 1.6, my + (cy - my) * 1.6   # bow through the middle
            pts = []
            for j in range(int(40 * q) + 2):
                s_ = j / 40 * 0.82
                pts.append(((1 - s_) ** 2 * x0 + 2 * (1 - s_) * s_ * bx + s_ ** 2 * x1, (1 - s_) ** 2 * y0 + 2 * (1 - s_) * s_ * by + s_ ** 2 * y1))
            pts = pts[3:] if len(pts) > 5 else pts
            d.line(pts, fill=YEL, width=26, joint="curve")
            if len(pts) > 3:
                ex, ey = pts[-1]; px, py = pts[-3]; an = math.atan2(ey - py, ex - px)
                d.polygon([(ex + 60 * math.cos(an), ey + 60 * math.sin(an)), (ex + 48 * math.cos(an + 2.3), ey + 48 * math.sin(an + 2.3)),
                           (ex + 48 * math.cos(an - 2.3), ey + 48 * math.sin(an - 2.3))], fill=YEL)
    if "label" in sc:
        u = back((lt - 0.1) / 0.3)
        kin_text(img, sc["label"], fit_size(sc["label"], 130, W - 100), COL[sc.get("label_color", "cream")], W / 2 - (1 - u) * 900, 250, vx=(1 - u) * 60)
    if "stamp" in sc and lt > 1.3:
        u = back((lt - 1.3) / 0.3); txt = sc["stamp"]
        f = FB(int(96 * max(0.05, u))); tw = d.textlength(txt, font=f)
        stamp = Image.new("RGBA", (int(tw + 80), 170), (0, 0, 0, 0)); sd = ImageDraw.Draw(stamp)
        sd.rectangle([0, 0, tw + 79, 169], fill=YEL, outline=INK, width=8)
        sd.text(((tw + 80) / 2, 85), txt, font=f, fill=INK, anchor="mm")
        stamp = stamp.rotate(-6, expand=True, resample=Image.BICUBIC)
        img.alpha_composite(stamp, (int(W / 2 - stamp.width / 2), sc.get("stamp_y", 1330)))
    return img

SCENES = {"slam": sc_slam, "flash": sc_flash, "cube": sc_cube, "grid": sc_grid, "big": sc_big,
          "squeeze": sc_squeeze, "rock": sc_rock, "toggle": sc_toggle,
          "planet": sc_planet, "orbit": sc_orbit, "bars": sc_bars, "sunrise": sc_sunrise, "thermo": sc_thermo,
          "jelly": sc_jelly, "cycle": sc_cycle}

# ================= captions =================
groups, cur = [], []
for i, w in enumerate(words):
    cur.append(i)
    if len(cur) == 3 or i + 1 == len(words) or words[i + 1][3] != w[3] or w[0][-1] in ".,?!…":
        groups.append(cur); cur = []
def captions(img, t, ln):
    if ln and ln["scene"]["type"] == "flash": return     # the scene itself is the caption
    d = ImageDraw.Draw(img)
    for g in groups:
        if words[g[0]][1] - 0.05 <= t < words[g[-1]][2] + 0.1:
            txt = " ".join(words[i][0].upper() for i in g)
            sz = fit_size(txt, 76, W - 160)
            f = FB(sz); tw = d.textlength(txt, font=f)
            d.rounded_rectangle([(W - tw) / 2 - 30, 1540, (W + tw) / 2 + 30, 1540 + sz + 44], 18, fill=INK)
            x = (W - tw) / 2
            for i in g:
                wd = words[i][0].upper()
                on = words[i][1] <= t < words[i][2] + 0.05
                d.text((x, 1562), wd, font=f, fill=YEL if on else CREAM)
                x += d.textlength(wd + " ", font=f)
            return

# ================= render =================
def active(t):
    cur = None
    for ln in spec["lines"]:
        if "scene" in ln and ln["_s"] - 0.1 <= t: cur = ln
    return cur

ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-i", work + "_audio.wav", "-c:v", "libx264", "-preset", "veryfast",
                       "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                       "-movflags", "+faststart", out_path], stdin=subprocess.PIPE)
prev, prev_ln = None, None
brand = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(brand)
bd.rounded_rectangle([56, 96, 150, 166], 20, fill=INK); bd.polygon([(74, 162), (104, 162), (78, 186)], fill=INK)
bd.text((103, 131), "?!", font=FB(52), fill=YEL, anchor="mm")
for fi in range(int(total * FPS)):
    t = fi / FPS
    ln = active(t)
    if ln:
        lt = t - ln["_s"]; dur = ln["_se"] - ln["_s"]
        img = SCENES[ln["scene"]["type"]](ln["scene"], lt, dur, ln)
        # color-block wipe on scene change
        if prev is not None and ln is not prev_ln and lt < 0.22:
            cut = int(W * eout((lt + 0.1) / 0.3))
            if cut < W:
                mixd = prev.copy(); mixd.paste(img.crop((0, 0, cut, H)), (0, 0)); img = mixd
        if lt >= 0.22: prev_ln = ln
    else:
        img = bg("ink")
    img.alpha_composite(brand)
    captions(img, t, ln)
    if prev_ln is ln or prev is None: prev = img
    ff.stdin.write(img.convert("RGB").tobytes())
ff.stdin.close(); ff.wait()
print(f"done {total:.1f}s, {len(words)} words")
