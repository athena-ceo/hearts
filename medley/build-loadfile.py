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
    # 2e. Revival: install our ACTIVEREGIONS reimplementation (medley/activeregions.lisp) —
    #     the 1986 INTERMEZZO LispUsers library isn't in modern Medley. Ours gives the human
    #     player clickable card regions via the window BUTTONEVENTFN. Injected here with its
    #     ;; header comments stripped (;; isn't Interlisp reader syntax).
    ar_src = (pathlib.Path(__file__).resolve().parent / "activeregions.lisp").read_text()
    ar_src = "\n".join(l for l in ar_src.split("\n") if not re.match(r"\s*;;", l)).strip()

    clown_fix = (
        "(* revival FIX -- CLOWN.Play dropped the FirstTrick? arg so the 2-of-clubs opening"
        " lead was never enforced; forward it. Original bug kept faithful in the"
        " transcription -- see BUGS.md)\n"
        "(DEFINEQ\n"
        "(CLOWN.Play (LAMBDA (Clown Trick HeartsBroken? FirstTrick?)\n"
        "    (LET* ((Possibles (H.GetLegals (fetch Clown.Hand of Clown) Trick HeartsBroken? FirstTrick?))\n"
        "           (Card (CAR (NTH Possibles (RAND 1 (LENGTH Possibles))))))\n"
        "      (Hand.RemoveCard (fetch Clown.Hand of Clown) Card)\n"
        "      Card)))\n"
        ")\n")

    # 2f. Revival FIX: CT.PrintStats redrew each player's score/tricks without erasing, so
    #     changing digits smeared together. Clear each field with a WHITESHADE fill first.
    ct_fix = (
        "(* revival FIX -- CT.PrintStats redrew score/tricks without erasing so digits"
        " smeared; clear each field with WHITESHADE before drawing)\n"
        "(DEFINEQ\n"
        "(CT.PrintStats (LAMBDA (Win)\n"
        "    (PROG ((DS (WINDOWPROP Win (QUOTE DSP)))\n"
        "           (Tricks (WINDOWPROP Win (QUOTE Tricks)))\n"
        "           (Score (WINDOWPROP Win (QUOTE Score))))\n"
        "      (DSPFONT (QUOTE (GACHA 10 BOLD)) DS)\n"
        "      (DSPFILL (CREATEREGION CT.X1 (DIFFERENCE CT.Y1 14) 96 12) WHITESHADE (QUOTE REPLACE) DS)\n"
        "      (MOVETO CT.X1 (DIFFERENCE CT.Y1 12) DS)\n"
        "      (printout DS \"S: \" (CAR Score) \" T: \" (CAR Tricks))\n"
        "      (DSPFILL (CREATEREGION CT.X2 (DIFFERENCE CT.Y2 14) 96 12) WHITESHADE (QUOTE REPLACE) DS)\n"
        "      (MOVETO CT.X2 (DIFFERENCE CT.Y2 12) DS)\n"
        "      (printout DS \"S: \" (CADR Score) \" T: \" (CADR Tricks))\n"
        "      (DSPFILL (CREATEREGION CT.X3 (PLUS CT.Y3 13) 96 12) WHITESHADE (QUOTE REPLACE) DS)\n"
        "      (MOVETO CT.X3 (PLUS CT.Y3 15) DS)\n"
        "      (printout DS \"S: \" (CADDR Score) \" T: \" (CADDR Tricks))\n"
        "      (DSPFILL (CREATEREGION CT.X4 (DIFFERENCE CT.Y4 14) 96 12) WHITESHADE (QUOTE REPLACE) DS)\n"
        "      (MOVETO CT.X4 (DIFFERENCE CT.Y4 12) DS)\n"
        "      (printout DS \"S: \" (CADDDR Score) \" T: \" (CADDDR Tricks))\n"
        "      (RETURN Win))))\n"
        ")\n")

    # 2g. Revival patch: Card.PrintCard is called ~8x (thought windows, help strings) but
    #     never defined — only the compact Card.Print ("KS") exists. Another lost-definition
    #     inconsistency like ClownNames. Supply a readable card name.
    card_fix = (
        "(* revival patch: Card.PrintCard is called but never defined -- only the compact"
        " Card.Print exists. Supply a readable card name for the thought windows and help strings)\n"
        "(DEFINEQ\n"
        "(Card.PrintCard (LAMBDA (Card)\n"
        "    (CONCAT (SELECTQ (fetch Value of Card) (J \"Jack\") (Q \"Queen\") (K \"King\") (A \"Ace\")\n"
        "                     (fetch Value of Card))\n"
        "            \" of \"\n"
        "            (SELECTQ (fetch Suit of Card) (C \"Clubs\") (D \"Diamonds\") (H \"Hearts\") (S \"Spades\")\n"
        "                     (fetch Suit of Card)))))\n"
        ")\n")

    patch = (
        "(* revival patch: ClownNames was undefined in the recovered source; names invented)\n"
        "(RPAQQ ClownNames (Bozo Chuckles Giggles Patches Sprinkles Coco Bubbles WackyWally Sniffles Doodles))\n"
        "(* revival: our ACTIVEREGIONS reimplementation -- medley/activeregions.lisp)\n"
        + ar_src + "\n"
        + clown_fix
        + ct_fix
        + card_fix)
    text = text.replace("(PUTPROPS HEARTS COPYRIGHT", patch + "(PUTPROPS HEARTS COPYRIGHT", 1)
    # 2h. Case-fix: HP.Menuer calls PromptPrint (mixed case) 3x, but the function is the
    #     system PROMPTPRINT and Interlisp is case-sensitive, so DWIM prompts at runtime.
    #     Original 1986 inconsistency (kept in the faithful transcription); correct it here.
    text = text.replace("PromptPrint", "PROMPTPRINT")
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
