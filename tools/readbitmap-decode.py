#!/usr/bin/env python3
"""Decode / validate / render an InterLisp-D READBITMAP "hardcopy" packed bitmap.

Old Interlisp source files store bitmaps as
    (RPAQ NAME (READBITMAP))
    (WIDTH HEIGHT "row" "row" ...)
where each row string is a packed scanline. The packing:

  * each character is a 4-bit nibble:  value = ord(c) - 64   (so @=0, A=1, ... O=15;
    letters/@ only — a literal '0'/'O' or 'I'/'l' slip is fatal to READBITMAP)
  * bits are MSB-first within each nibble
  * each scanline is padded to a 16-bit word (Interlisp BITSPERWORD), so
    chars-per-row = ceil(WIDTH/16) * 4 ; the first WIDTH bits are the pixels.

This tool decodes those rows, validates them (row length + legal charset), prints
ASCII art, and writes a scaled PNG so you can eyeball whether the artwork is right
before trusting an OCR'd transcription. Built for the HEARTS revival; reusable for
any Interlisp-D bitmap. See ../REVIVAL-LOG.md.

Usage:
  readbitmap-decode.py NAME WIDTH HEIGHT ROW1 ROW2 ...     # rows as CLI args
  # writes ./NAME.png, prints validation + ASCII art
"""
import sys
try:
    from PIL import Image
except ImportError:
    Image = None

def validate(w, h, rows):
    cpr = ((w + 15)//16) * 4
    errs = []
    if len(rows) != h:
        errs.append(f"row count {len(rows)} != height {h}")
    for i, r in enumerate(rows):
        if len(r) != cpr:
            errs.append(f"row {i}: len {len(r)} != expected {cpr}  ({r!r})")
        for ch in r:
            if not (64 <= ord(ch) <= 79):
                errs.append(f"row {i}: illegal char {ch!r} (ord {ord(ch)}, must be @..O)")
    return cpr, errs

def decode(w, rows):
    out = []
    for r in rows:
        bits = "".join(format(ord(ch)-64, "04b") for ch in r)
        out.append([1 if b == "1" else 0 for b in bits[:w]])
    return out

def ascii_art(px):
    return "\n".join("".join("##" if v else ".." for v in row) for row in px)

def render(px, w, h, path, scale=18):
    if Image is None:
        return None
    img = Image.new("L", (w*scale, h*scale), 255)
    for y, row in enumerate(px):
        for x, v in enumerate(row):
            if v:
                for dy in range(scale):
                    for dx in range(scale):
                        img.putpixel((x*scale+dx, y*scale+dy), 0)
    img.save(path)
    return path

def main(argv):
    if len(argv) < 4:
        print(__doc__); return 2
    name, w, h = argv[1], int(argv[2]), int(argv[3])
    rows = argv[4:]
    cpr, errs = validate(w, h, rows)
    print(f"{name}: {w}x{h}, expect {cpr} chars/row, {h} rows")
    print("  validation OK" if not errs else "  VALIDATION ERRORS:")
    for e in errs:
        print("   -", e)
    px = decode(w, rows)
    print(ascii_art(px))
    out = render(px, w, h, f"{name}.png")
    print("wrote", out) if out else print("(install Pillow for PNG output)")
    return 1 if errs else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
