"""Shared pieces for every 'Sounds Fake' style: narration + word timing, audio mix,
caption grouping, easing, and the render loop (one ffmpeg pass, temp file then rename)."""
import json, math, os, subprocess
import numpy as np
import soundfile as sf

W, H, FPS, SR = 1080, 1920, 30, 24000
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")

def ease(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def eout(u): u = max(0.0, min(1.0, u)); return 1 - (1 - u) ** 3
def back(u, c=1.8):
    u = max(0.0, min(1.0, u)); return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2

def kokoro():
    from kokoro_onnx import Kokoro
    kd = os.path.expanduser(os.environ.get("KOKORO_DIR", "~/.cache/kokoro"))
    return Kokoro(os.path.join(kd, "kokoro.onnx"), os.path.join(kd, "voices.bin"))

def narrate(spec, lead=0.35, default_gap=0.28, tail=0.9):
    """Speak each line; annotate lines with _s/_e/_se and word index range; return voice, words, total."""
    tts = kokoro()
    t = lead
    parts, words = [np.zeros(int(SR * lead), np.float32)], []
    for si, ln in enumerate(spec["lines"]):
        s, _ = tts.create(ln["text"], voice=spec.get("voice", "am_michael"),
                          speed=spec.get("speed", 1.08), lang="en-us")
        nz = np.where(np.abs(s) > 0.01)[0]
        s = s[max(nz[0] - 600, 0): nz[-1] + 1200]
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
        gap = ln.get("pause", default_gap)
        parts += [s.astype(np.float32), np.zeros(int(SR * gap), np.float32)]
        t += dur + gap
    for i, ln in enumerate(spec["lines"]):
        ln["_se"] = spec["lines"][i + 1]["_s"] if i + 1 < len(spec["lines"]) else t + tail
    voice = np.concatenate(parts)
    total = len(voice) / SR + tail
    voice = np.pad(voice, (0, int(SR * total) - len(voice)))
    return voice, words, total

def write_audio(voice, music, path, music_gain=0.5, duck=0.4):
    env = np.convolve(np.abs(voice), np.ones(2400) / 2400, mode="same")
    music = music * (1 - duck * np.clip(env * 12, 0, 1))
    n = len(voice); tt = np.arange(n) / SR; total = n / SR
    music = music * np.clip(tt / 1.0, 0, 1) * np.clip((total - tt) / 1.2, 0, 1)
    mix = voice + music * music_gain
    mix = mix / max(1e-6, np.abs(mix).max()) * 0.92
    sf.write(path, mix, SR)

def caption_groups(words, maxw=3):
    groups, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        if len(cur) == maxw or i + 1 == len(words) or words[i + 1][3] != w[3] or w[0][-1] in ".,?!…":
            groups.append(cur); cur = []
    return groups

def group_at(groups, words, t):
    for gi, g in enumerate(groups):
        if words[g[0]][1] - 0.05 <= t < words[g[-1]][2] + 0.12:
            return gi, g
    return None, None

def active_line(spec, t, lead=0.12):
    cur = None
    for ln in spec["lines"]:
        if "scene" in ln and ln["_s"] - lead <= t: cur = ln
    return cur

def render(total, frame_fn, audio_path, out_path, crf=20, pix="rgb24"):
    """frame_fn(t, fi) -> bytes of one WxH frame in `pix` format. Writes to a temp .mp4 and renames on success."""
    tmp = out_path[:-4] + ".part.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", pix,
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", audio_path,
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", tmp],
                          stdin=subprocess.PIPE)
    for fi in range(int(total * FPS)):
        ff.stdin.write(frame_fn(fi / FPS, fi))
    ff.stdin.close()
    if ff.wait() == 0:
        os.replace(tmp, out_path)
    else:
        raise SystemExit("ffmpeg failed")

def tone(f, dur, decay=4.0, harm=(1, 2, 3), amp=1.0):
    t = np.arange(int(dur * SR)) / SR
    return amp * sum(np.sin(2 * np.pi * f * h * t) / h ** 1.5 for h in harm) * np.exp(-t * decay)

def place(buf, at, sig, gain=1.0):
    a = int(at * SR); b = min(a + len(sig), len(buf))
    if 0 <= a < len(buf): buf[a:b] += sig[: b - a] * gain
