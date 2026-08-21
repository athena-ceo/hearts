#!/usr/bin/env python3
"""Generate the Medley-loadable HEARTS file from the human-readable master.

Mechanical, fidelity-preserving transforms ONLY:
  1. Drop our own annotation lines  (^\\s*;;  — page markers, file header).
     ';' is NOT an Interlisp comment char, so these must go. Note '.;59' version
     syntax is mid-line, never matched by ^\\s*;;.
  2. Strip our own  #| ... |#  transcription notes (not Interlisp syntax),
     including multi-line blocks; the best-guess token before them is kept.
  3. Convert the assignment arrow  ←  ->  _  (ASCII 0x5F), the byte the CLISP
     reader treats as assignment (see MEDLEY-SETUP-NOTES.md §3).
Interlisp's own (* ... ) comments, % escapes, and [ ] super-brackets are LEFT AS-IS.
Output is written with LF line endings (retry with CR if Medley's reader chokes).
"""
import re, sys, pathlib

SRC = pathlib.Path(__file__).resolve().parent.parent / "transcription" / "hearts-core.lisp"
OUT = pathlib.Path(__file__).resolve().parent / "HEARTS"

def build(text):
    # 2. remove #| ... |# (multi-line, non-greedy)
    text = re.sub(r"#\|.*?\|#", "", text, flags=re.DOTALL)
    # 1. drop pure ;; annotation lines
    lines = [ln for ln in text.split("\n") if not re.match(r"\s*;;", ln)]
    text = "\n".join(lines)
    # 2b. Stub ONLY the two 50x50 icon bitmaps (HIconBM, HShadowBM) with blank
    #     BITMAPCREATEs of the same size — those are still best-effort and only the
    #     desktop app icon (which H.MakeIcon, also neutralized below, would draw).
    #     The five CARD bitmaps (CardOutline + the four suit pips) have been verified
    #     (tools/readbitmap-decode.py) and are kept as real READBITMAP data so the card
    #     table draws legible suits. Replace each stubbed
    #     (RPAQ NAME (READBITMAP)) (W H "row"...)  with  (RPAQ NAME (BITMAPCREATE W H)).
    text = re.sub(
        r'\(RPAQ (HIconBM|HShadowBM) \(READBITMAP\)\)\s*\((\d+)\s+(\d+)(?:\s*"[^"]*")+\s*\)',
        r'(RPAQ \1 (BITMAPCREATE \2 \3))',
        text)
    # 2c. Neutralize end-of-file forms that depend on things Medley no longer has:
    #   - FILESLOAD of EVALSERVER.DCOM / ACTIVEREGIONS.DCOM (dead Ethernet remote-eval +
    #     an old UI lib) — networking is deferred (see ARCHITECTURE.md §9);
    #   - the top-level (H.MakeIcon) call that builds the desktop icon (UI side-effect,
    #     not needed to run the core headless).
    # Replaced with Interlisp (* ...) no-op comments so the load completes cleanly.
    text = re.sub(r'\(FILESLOAD.*?ACTIVEREGIONS\.DCOM\)',
                  '(* neutralized EVALSERVER and ACTIVEREGIONS FILESLOAD)',
                  text, flags=re.DOTALL)
    text = re.sub(r'(?m)^\(H\.MakeIcon\)$',
                  '(* neutralized H.MakeIcon icon call)',
                  text)
    # 2d. Revival patch: supply ClownNames. CLOWN.Create picks a random clown name from
    #     the variable ClownNames, but the recovered source never defines it and it is not
    #     in the file's COMS (unlike the parallel ConservativeNames) — the 1986 definition
    #     lived elsewhere and is lost. Inject an invented list so Clown players can be made.
    #     (Original clown names unknown; these are in the spirit of the ConservativeNames.)
    patch = ("(* revival patch: ClownNames was undefined in the recovered source; names invented)\n"
             "(RPAQQ ClownNames (Bozo Chuckles Giggles Patches Sprinkles Coco Bubbles WackyWally Sniffles Doodles))\n")
    text = text.replace("(PUTPROPS HEARTS COPYRIGHT", patch + "(PUTPROPS HEARTS COPYRIGHT", 1)
    # 3. arrow -> underscore
    text = text.replace("←", "_")
    # collapse runs of >2 blank lines left by stripping
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text

if __name__ == "__main__":
    raw = SRC.read_text(encoding="utf-8")
    out = build(raw)
    OUT.write_text(out, encoding="utf-8", newline="\n")
    # sanity report
    assert "←" not in out, "arrow left in output"
    assert "#|" not in out, "annotation block left in output"
    leftmarks = sum(1 for ln in out.split("\n") if re.match(r"\s*;;", ln))
    print(f"wrote {OUT}  ({len(out.splitlines())} lines)")
    print(f"  ← arrows remaining: {out.count(chr(0x2190))}")
    print(f"  _ underscores now:  {out.count('_')}")
    print(f"  ;; annotation lines remaining: {leftmarks}")
    print(f"  #| annotation blocks remaining: {out.count('#|')}")
