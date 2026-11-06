#!/usr/bin/env python3
# Copyright (c) 2026 Athena Decision Systems SAS.
"""Check each recorded clip against the script, since nobody here can hear them.  The whole clip is transcribed for a
match score, and its last six seconds separately, because the voice model sometimes drops a short last sentence, and that
is the punchline.  A long clip can lose it and still score well."""
import difflib, json, pathlib, re, subprocess, sys, tempfile

OUT = pathlib.Path(__file__).resolve().parents[2] / "out/video/voice"
key = pathlib.Path("~/.config/hearts/openai-key").expanduser().read_text().strip()
NUM = {"one": "1", "three": "3", "five": "5", "four": "4", "seven": "7", "seventy": "70", "fifteen": "15", "nineteen": "19"}
words = lambda t: [NUM.get(w, w) for w in re.sub(r"[^a-z0-9' ]", " ", t.lower().replace("-", " ")).split()]


def hear(path, model):
    r = subprocess.run(["curl", "-sS", "-K", "-", "https://api.openai.com/v1/audio/transcriptions", "-F", f"model={model}",
                        "-F", f"file=@{path}", "-F", "response_format=text"],
                       input=f'header = "Authorization: Bearer {key}"\n', capture_output=True, text=True, timeout=180)
    return r.stdout


def main():
    bad = []
    for e in json.loads((OUT / "index.json").read_text()):
        path = OUT / e["file"]
        whole = hear(path, "whisper-1")
        ratio = difflib.SequenceMatcher(None, words(e["text"]), words(whole)).ratio()
        with tempfile.TemporaryDirectory() as d:
            tail = pathlib.Path(d) / "tail.mp3"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-6", "-i", str(path), str(tail)], check=True)
            end = hear(tail, "gpt-4o-transcribe") if e["seconds"] > 6 else whole
        want, got = words(e["text"])[-3:], words(end)
        ended = all(w in got for w in want)
        print(f"{e['clip']:02d} match {ratio:.2f}  end {'ok ' if ended else 'MISSING'}  ...{' '.join(want)}  | heard: {end.strip()[-60:]!r}")
        if not ended:
            bad.append(e["clip"])
    print("clips whose ending is missing:", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
