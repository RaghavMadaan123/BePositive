"""
Render the GlucoTwin animated explainer.
    python render.py            -> video/GlucoTwin_Explainer.mp4
Needs audio/ (from tts.py), boards/ (slide + dashboard images), ffmpeg.
Two worker processes render halves of the frame range in parallel, then the halves are concatenated and muxed with audio.
"""
import json
import os
import subprocess
import sys
import textwrap
from multiprocessing import Process

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from characters import sprites, W as SW, H as SH
from script import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 15
VW, VH = 1280, 720
BX, BY, BW, BH = 200, 22, 880, 495
GAP, SCENE_IN, SCENE_OUT, XFADE = 0.40, 0.55, 0.70, 0.45
FONT = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"
FONT_B = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
NAMES = {"M": ("DR. MEERA", (60, 192, 201)), "G": ("GLUCO · THE DIGITAL TWIN", (176, 156, 255))}


# ----------------------------------------------------------------- timeline + audio
def build_timeline():
    meta = json.load(open(os.path.join(HERE, "audio", "lines.json")))
    sr = meta[0]["sr"]
    t, cur_scene, events, scene_spans = 0.0, -1, [], []
    chunks = []
    for m in meta:
        if m["scene"] != cur_scene:
            if cur_scene >= 0:
                t += SCENE_OUT - GAP
                scene_spans[-1][2] = t
            cur_scene = m["scene"]
            scene_spans.append([cur_scene, t, None])
            t += SCENE_IN
        a, _ = sf.read(os.path.join(HERE, "audio", f"{m['i']:03d}.wav"), dtype="float32")
        events.append(dict(m, start=t, end=t + m["dur"]))
        chunks.append((t, a))
        t += m["dur"] + GAP
    t += SCENE_OUT
    scene_spans[-1][2] = t
    total = t
    audio = np.zeros(int(total * sr) + sr, dtype=np.float32)
    for st, a in chunks:
        i0 = int(st * sr); audio[i0:i0 + len(a)] += a
    audio = audio / max(1e-6, np.abs(audio).max()) * 0.92
    return events, scene_spans, total, audio, sr


def envelope(audio, sr, n_frames):
    hop = sr // FPS
    env = np.zeros(n_frames)
    for f in range(n_frames):
        seg = audio[f * hop:(f + 1) * hop]
        env[f] = np.sqrt((seg ** 2).mean()) if len(seg) else 0
    return env / (np.percentile(env[env > 0], 90) + 1e-9)


# ----------------------------------------------------------------- subtitles
def chunk_text(text, draw, font, maxw=780, maxlines=3):
    words = text.split()
    chunks, cur = [], []
    def lines_of(ws):
        return wrap(" ".join(ws), draw, font, maxw)
    for w in words:
        if len(lines_of(cur + [w])) > maxlines:
            chunks.append(" ".join(cur)); cur = [w]
        else:
            cur.append(w)
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def wrap(text, draw, font, maxw):
    lines, cur = [], ""
    for w in text.split():
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= maxw:
            cur = test
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


# ----------------------------------------------------------------- static layers
def background():
    y = np.linspace(0, 1, VH)[:, None]
    x = np.linspace(0, 1, VW)[None, :]
    c1, c2 = np.array([8, 44, 56]), np.array([14, 78, 92])
    mix = np.clip(0.55 * y + 0.45 * (1 - np.abs(x - 0.5) * 2) * 0.6, 0, 1)[..., None]
    arr = (c1 * (1 - mix) + c2 * mix).astype(np.uint8)
    bg = Image.fromarray(np.broadcast_to(arr, (VH, VW, 3)).copy())
    d = ImageDraw.Draw(bg, "RGBA")
    for (cx, cy, r, a) in [(90, 120, 120, 18), (1190, 160, 150, 14), (640, 690, 260, 10), (60, 600, 90, 12)]:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(122, 90, 248, a))
    # board shadow + frame
    sh = Image.new("RGBA", (VW, VH), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((BX - 4, BY + 6, BX + BW + 4, BY + BH + 12), radius=18, fill=(0, 0, 0, 110))
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    bg = Image.alpha_composite(bg.convert("RGBA"), sh)
    ImageDraw.Draw(bg).rounded_rectangle((BX - 8, BY - 8, BX + BW + 8, BY + BH + 8), radius=16, fill=(255, 255, 255))
    return bg.convert("RGB")


def load_boards():
    names = sorted({b for sc in SCENES for b in sc["board"]})
    return {n: Image.open(os.path.join(HERE, "boards", n)).convert("RGB").resize((1280, 720), Image.LANCZOS) for n in names}


def round_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    return m


# ----------------------------------------------------------------- frame renderer
def render_range(f0, f1, out_path):
    events, spans, total, audio, sr = build_timeline()
    n_frames = int(total * FPS)
    env = envelope(audio, sr, n_frames)
    bg = background()
    boards = load_boards()
    sp = sprites()
    mask = round_mask(BW, BH, 10)
    font = ImageFont.truetype(FONT, 22)
    font_tag = ImageFont.truetype(FONT_B, 14)
    font_name = ImageFont.truetype(FONT_B, 15)
    dtmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    # subtitle chunks with timings
    for e in events:
        cs = chunk_text(e["text"], dtmp, font)
        L = sum(len(c) for c in cs)
        t = e["start"]
        e["subs"] = []
        for c in cs:
            d = e["dur"] * len(c) / L
            e["subs"].append((t, t + d, wrap(c, dtmp, font, 780)))
            t += d
    # which board is showing at time t
    def board_at(t):
        cur = None
        for sc_i, s0, s1 in spans:
            if s0 <= t < s1 or (t >= s1 and sc_i == spans[-1][0]):
                cur = (sc_i, s0, s1)
        sc_i, s0, s1 = cur if cur else spans[0]
        b = 0; bstart = s0
        for e in events:
            if e["scene"] == sc_i and e["start"] <= t:
                if e["board"] != b:
                    b = e["board"]; bstart = e["start"]
        return sc_i, SCENES[sc_i]["board"][b], bstart, s0, s1

    rng = np.random.default_rng(1)
    blink_times = {k: np.cumsum(rng.uniform(2.5, 5.5, 600)) for k in ("M", "G")}
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                             "-pix_fmt", "yuv420p", out_path], stdin=subprocess.PIPE)
    prev_board_name = None
    for f in range(f0, min(f1, n_frames)):
        t = f / FPS
        frame = bg.copy()
        sc_i, bname, bstart, s0, s1 = board_at(t)
        # Ken Burns zoom over the scene
        prog = (t - s0) / max(s1 - s0, 1e-6)
        z = 1.0 + 0.04 * prog
        cw, ch = 1280 / z, 720 / z
        ox, oy = (1280 - cw) / 2 + 10 * np.sin(prog * 2), (720 - ch) / 2
        img = boards[bname].resize((BW, BH), Image.BILINEAR, box=(ox, oy, ox + cw, oy + ch))
        # cross-fade from the previous board
        if t - bstart < XFADE:
            prev = None
            # previous board = board showing just before bstart
            _, pname, _, ps0, ps1 = board_at(max(0, bstart - 0.05))
            if pname != bname and bstart > 0.1:
                pprog = (bstart - ps0) / max(ps1 - ps0, 1e-6)
                pz = 1.0 + 0.04 * min(pprog, 1)
                pcw, pch = 1280 / pz, 720 / pz
                pox, poy = (1280 - pcw) / 2 + 10 * np.sin(min(pprog, 1) * 2), (720 - pch) / 2
                prev = boards[pname].resize((BW, BH), Image.BILINEAR, box=(pox, poy, pox + pcw, poy + pch))
                img = Image.blend(prev, img, (t - bstart) / XFADE)
        frame.paste(img, (BX, BY), mask)

        # active line
        active = None
        for e in events:
            if e["start"] <= t < e["end"]:
                active = e; break
        last = None
        for e in events:
            if e["start"] <= t:
                last = e
        d = ImageDraw.Draw(frame, "RGBA")
        # characters
        for who, x in (("M", 2), ("G", VW - SW - 2)):
            speaking = active is not None and active["spk"] == who
            m = 0
            if speaking:
                v = env[f]
                m = 0 if v < 0.18 else (1 if v < 0.55 else 2)
            bt = blink_times[who]
            blink = np.any((t >= bt) & (t < bt + 0.15))
            if who == "M":
                bob = (3.5 if speaking else 1.5) * np.sin(t * (6 if speaking else 2))
            else:
                bob = 7 * np.sin(t * 2.2) + (2 * np.sin(t * 9) if speaking else 0)
            y = VH - SH + 6 + int(bob)
            if who == "G":
                sx = int(x + SW / 2)
                d.ellipse((sx - 60, VH - 14, sx + 60, VH - 2), fill=(0, 0, 0, int(70 - bob * 3)))
            spr = sp[(who, m, bool(blink))]
            frame.paste(spr, (x, y), spr)
            if speaking:
                name, col = NAMES[who]
                tw = d.textlength(name, font=font_tag)
                tx = x + SW / 2 - tw / 2 - 12
                ty = y - 30
                d.rounded_rectangle((tx, ty, tx + tw + 24, ty + 26), radius=13, fill=col + (255,))
                d.text((tx + 12, ty + 4), name, font=font_tag, fill=(10, 30, 38))
        # subtitles
        sub_e = active if active else (last if last and t - last["end"] < GAP else None)
        if sub_e:
            lines = None
            for (a, b, ls) in sub_e["subs"]:
                if a <= t < b + (GAP if (a, b, ls) == sub_e["subs"][-1] else 0):
                    lines = ls
            if lines:
                name, col = NAMES[sub_e["spk"]]
                top = 545
                d.rounded_rectangle((232, top, 1048, top + 34 + 31 * len(lines) + 10), radius=14, fill=(6, 24, 32, 205))
                d.text((252, top + 9), name, font=font_name, fill=col)
                for k, ln in enumerate(lines):
                    d.text((252, top + 34 + 31 * k), ln, font=font, fill=(240, 246, 248))
        # progress bar
        d.rectangle((0, VH - 4, int(VW * t / total), VH), fill=(60, 192, 201, 255))
        proc.stdin.write(frame.tobytes())
        prev_board_name = bname
    proc.stdin.close(); proc.wait()


def main():
    events, spans, total, audio, sr = build_timeline()
    n = int(total * FPS)
    print(f"duration {total / 60:.1f} min, {n} frames", flush=True)
    sf.write(os.path.join(HERE, "audio_full.wav"), audio, sr)
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        f0 = int(float(sys.argv[2]) * FPS); render_range(f0, f0 + int(float(sys.argv[3]) * FPS), os.path.join(HERE, "test.mp4")); return
    half = n // 2
    parts = [os.path.join(HERE, f"part{i}.mp4") for i in (0, 1)]
    ps = [Process(target=render_range, args=(0, half, parts[0])), Process(target=render_range, args=(half, n, parts[1]))]
    [p.start() for p in ps]; [p.join() for p in ps]
    lst = os.path.join(HERE, "parts.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    out = os.path.join(HERE, "GlucoTwin_Explainer.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", os.path.join(HERE, "audio_full.wav"),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out], check=True)
    for p in parts + [lst]:
        os.remove(p)
    print("wrote", out)


if __name__ == "__main__":
    main()
