#!/usr/bin/env python3
# Copyright (c) 2026 Athena Decision Systems SAS.
"""Record the video's narration from video-script.md, one clip per paragraph, into out/video/voice.

    python3 docs/talk/make_narration.py

A clip already recorded from the same text is kept, so changing a line costs only that line.  The key is read from
~/.config/hearts/openai-key and goes to curl on stdin, never on a command line.
"""
import hashlib, json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "out/video/voice"
VOICE = "onyx"
DIRECTION = ("Voice: a soft-spoken, serene male computer narrator. Tone: calm, courteous, even and unhurried, with an almost gentle "
             "politeness. Emotion: very restrained, with a faint, dry amusement underneath that never breaks the surface. "
             "Pacing: slow and deliberate, with clean pauses between sentences, and a longer pause before a punchline. "
             "Never theatrical, and never robotic.")


def paragraphs():
    """(section number, text) for every spoken paragraph.  Italics are stage directions, and headings and the last card aren't spoken."""
    section, out = 0, []
    text = (pathlib.Path(__file__).parent / "video-script.md").read_text().split("---", 1)[1]
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if m := re.match(r"## (\d+)\.", block):
            section = int(m.group(1))
        elif block and section and not block.startswith(("*", "---")):
            spoken = re.sub(r"^> ", "", block, flags=re.M).replace("`", "").replace("HANDOFF.md", "Handoff dot M D")
            spoken = spoken.replace("DEFINEQ", "define-Q")
            out.append((section, spoken))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    key = pathlib.Path("~/.config/hearts/openai-key").expanduser().read_text().strip()
    index = []
    for i, (section, text) in enumerate(paragraphs(), 1):
        tag = hashlib.sha1((VOICE + DIRECTION + text).encode()).hexdigest()[:10]
        path = OUT / f"{i:02d}-s{section}-{tag}.mp3"
        if not path.exists() and (take := next(OUT.glob(f"*-{tag}.mp3"), None)):
            take.rename(path)  # The same words: keep the take, whatever its place in the order.
        if not path.exists():
            body = json.dumps({"model": "gpt-4o-mini-tts", "voice": VOICE, "input": text, "instructions": DIRECTION, "response_format": "mp3"})
            r = subprocess.run(["curl", "-sS", "-K", "-", "-o", str(path), "-w", "%{http_code}", "https://api.openai.com/v1/audio/speech",
                                "-H", "Content-Type: application/json", "-d", body],
                               input=f'header = "Authorization: Bearer {key}"\n', capture_output=True, text=True, timeout=240)
            if r.stdout.strip() != "200":
                sys.exit(f"clip {i}: {r.stdout} {path.read_text(errors='replace')[:300]}")
        d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                 capture_output=True, text=True).stdout)
        index.append({"clip": i, "section": section, "file": path.name, "seconds": round(d, 2), "text": text})
        print(f"{i:02d} s{section} {d:5.1f}s  {text[:60]}")
    (OUT / "index.json").write_text(json.dumps(index, indent=1))
    keep = {e["file"] for e in index} | {"index.json"}
    for stale in OUT.glob("*.mp3"):
        if stale.name not in keep:
            stale.unlink()
    print(f"{len(index)} clips, {sum(e['seconds'] for e in index):.0f} s of speech")


if __name__ == "__main__":
    main()
