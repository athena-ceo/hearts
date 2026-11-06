#!/usr/bin/env python3
# Copyright (c) 2026 Athena Decision Systems SAS.
"""Mix the video's sound and join it to the picture: the narration at the times in timeline.json, a quiet drone under it,
and, over the last card, Daisy Bell on a square wave (Harry Dacre, 1892), slowing and sinking as it plays.

    .venv/bin/python docs/talk/mix_video.py
"""
import json, pathlib, subprocess
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "out/video"
RATE = 48000
T = json.loads((OUT / "timeline.json").read_text())


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(RATE), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def drone(n):
    t = np.arange(n) / RATE
    out = np.zeros(n)
    for f, a, lfo in ((73.42, 1.0, 0.031), (110.0, 0.55, 0.043), (146.83, 0.3, 0.057), (220.0, 0.12, 0.071)):
        out += a * np.sin(2 * np.pi * f * t) * (0.6 + 0.4 * np.sin(2 * np.pi * lfo * t))
    return out / np.abs(out).max()


def daisy(seconds):
    """Dai-sy, Dai-sy, give me your an-swer do.  It starts in tempo, then the clock runs down."""
    notes = [(587.33, 3), (493.88, 3), (392.0, 3), (293.66, 3), (329.63, 1), (369.99, 1), (392.0, 1), (329.63, 2), (392.0, 1), (293.66, 6)]
    beat, phase, out = 0.36, 0.0, []
    played, total = 0, sum(b for _, b in notes)
    for freq, beats in notes:
        for b in range(beats):
            progress = played / total
            slow = 1 + 1.1 * max(0, progress - 0.35) ** 1.4
            sink = 1 - 0.28 * max(0, progress - 0.5) ** 1.5 * 2
            n = int(beat * slow * RATE)
            inc = 2 * np.pi * freq * sink / RATE
            phases = phase + inc * np.arange(n)
            phase = phases[-1] + inc
            wave = np.sign(np.sin(phases))
            wave = np.convolve(wave, np.ones(24) / 24, mode="same")  # Take the edge off the square.
            start = 0 if b else 1
            env = np.minimum(1, np.arange(n) / 400) * (np.exp(-np.arange(n) / (RATE * 0.9)) if start else 0.8 * np.exp(-(b + np.arange(n) / n) * 0.3))
            out.append(wave * env)
            played += 1
    y = np.concatenate(out)
    return y / np.abs(y).max()


length = int((T["total"] + 0.5) * RATE)
voice = np.zeros(length)
for c in T["clips"]:
    clip = decode(c["file"])
    at = int(c["start"] * RATE)
    voice[at:at + len(clip)] += clip[:length - at]
voice /= np.abs(voice).max()

bed = drone(length) * 0.045
edge = int(4 * RATE)
ramp = np.ones(length)
ramp[:edge] = np.linspace(0, 1, edge)
end = int(T["endStart"] * RATE)
ramp[end - edge:end] = np.linspace(1, 0.15, edge)
ramp[end:] = np.linspace(0.15, 0, length - end)
bed *= ramp

tune = daisy(13)
at = end + int(0.6 * RATE)
tune = tune[:length - at]
fadeout = np.minimum(1, (len(tune) - np.arange(len(tune))) / (RATE * 0.6))
mix = 0.88 * voice + bed
mix[at:at + len(tune)] += 0.07 * tune * fadeout
mix = np.clip(mix, -1, 1)
pcm = OUT / "mix.f32"
pcm.write_bytes(mix.astype(np.float32).tobytes())
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(OUT / "picture.mp4"), "-f", "f32le", "-ar", str(RATE), "-ac", "1", "-i", str(pcm),
                "-af", "loudnorm=I=-18:TP=-1.5:LRA=11", "-ar", str(RATE),
                "-vf", f"fade=t=in:st=0:d=1,fade=t=out:st={T['total'] - 1.2:.2f}:d=1.2",
                "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                "-shortest", str(OUT / "hearts-by-claude.mp4")], check=True)
pcm.unlink()
print("wrote", OUT / "hearts-by-claude.mp4", f"{T['total']:.1f} s, tune {len(tune) / RATE:.1f} s")
