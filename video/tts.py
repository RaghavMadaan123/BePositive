"""Synthesise every dialogue line with Kokoro (open-weight TTS, Apache-2.0).
Usage: python tts.py <model.onnx> <voices.bin>"""
import json
import os
import re
import sys

import soundfile as sf
from kokoro_onnx import Kokoro

from script import SCENES, SPEAK

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "audio")
VOICE = {"M": ("af_heart", 1.0), "G": ("am_puck", 1.05)}


def spoken(t):
    for a, b in SPEAK:
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t)


def main():
    os.makedirs(OUT, exist_ok=True)
    k = Kokoro(sys.argv[1], sys.argv[2])
    meta = []
    i = 0
    for si, sc in enumerate(SCENES):
        for spk, text, b in sc["lines"]:
            path = os.path.join(OUT, f"{i:03d}.wav")
            if not os.path.exists(path):
                v, sp = VOICE[spk]
                samples, sr = k.create(spoken(text), voice=v, speed=sp, lang="en-us")
                sf.write(path, samples, sr)
            info = sf.info(path)
            meta.append(dict(i=i, scene=si, spk=spk, text=text, board=b, dur=info.duration, sr=info.samplerate))
            print(i, round(info.duration, 1), flush=True)
            i += 1
    json.dump(meta, open(os.path.join(OUT, "lines.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
