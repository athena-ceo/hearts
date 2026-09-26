#!/usr/bin/env python3
"""Generate the Medley-loadable HEARTS file(s) from the human-readable master.

Two outputs:
  * medley/HEARTS        — self-contained DEV build (ACTIVEREGIONS inlined). This is
                           what we copy to ~/il and test/play with; one file, no deps.
  * dist/HEARTS          — DISTRIBUTION build: same revival patches folded in, but it
    dist/ACTIVEREGIONS     (FILESLOAD ACTIVEREGIONS) instead of inlining it, and ships
                           ACTIVEREGIONS as its own standalone lispusers module. This is
                           the package the Interlisp-D community loads (see dist/README.md).

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

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE.parent / "transcription" / "hearts-core.lisp"
OUT = HERE / "HEARTS"
DIST = HERE.parent / "dist"


def load_ar_src():
    """The ACTIVEREGIONS fns/record, ;;-comments stripped (;; isn't Interlisp syntax)."""
    ar_src = (HERE / "activeregions.lisp").read_text()
    return "\n".join(l for l in ar_src.split("\n") if not re.match(r"\s*;;", l)).strip()


def build(text, dist=False):
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
    # 2c. Handle the end-of-file FILESLOAD of EVALSERVER.DCOM / ACTIVEREGIONS.DCOM and the
    #     top-level (H.MakeIcon) desktop-icon call.
    #   - DEV build: neutralize both (ACTIVEREGIONS is inlined below; networking deferred).
    #   - DIST build: restore (FILESLOAD ACTIVEREGIONS) — it ships as its own module now —
    #     but still drop EVALSERVER (dead Ethernet remote-eval; networking deferred, see
    #     ARCHITECTURE.md §9). H.MakeIcon stays neutralized in both (icon bitmaps are lost).
    text = re.sub(r'\(FILESLOAD.*?ACTIVEREGIONS\.DCOM\)',
                  '(FILESLOAD ACTIVEREGIONS)' if dist
                  else '(* neutralized EVALSERVER and ACTIVEREGIONS FILESLOAD)',
                  text, flags=re.DOTALL)
    text = re.sub(r'(?m)^\(H\.MakeIcon\)$',
                  '(* neutralized H.MakeIcon icon call)',
                  text)
    # 2d. Revival patch: supply ClownNames. CLOWN.Create picks a random clown name from
    #     the variable ClownNames, but the recovered source never defines it and it is not
    #     in the file's COMS (unlike the parallel ConservativeNames) — the 1986 definition
    #     lived elsewhere and is lost. Inject an invented list so Clown players can be made.
    #     (Original clown names unknown; these are in the spirit of the ConservativeNames.)
    # 2e. Revival: ACTIVEREGIONS reimplementation (medley/activeregions.lisp). In the DEV
    #     build it is inlined here; in the DIST build it is a separate FILESLOAD'd module.
    ar_src = load_ar_src()

    clown_fix = (
        "(* revival FIX -- CLOWN.Play dropped the FirstTrick? arg so the 2-of-clubs opening"
        " lead was never enforced; forward it. Original bug kept faithful in the"
        " transcription -- see HEARTS-BUGS.md)\n"
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

    # 2j. Revival FIX (H1): HP.Play (the human's play) declared (HWin Trick HeartsBroken?),
    #     dropping the FirstTrick? arg the trick loop passes -- (H.Apply Player 'Play Trick
    #     HeartsBroken? (EQP TrickNum 1)) -- so the 2-of-clubs opening-lead rule was never
    #     enforced for the human (the same original bug as CLOWN.Play). Add FirstTrick?, forward
    #     it to H.GetLegals, and stash it as a window prop so the LegalCards menu button (patched
    #     via text-replace below) can use it too. Redefined fully-parenthesized. See HEARTS-BUGS.md H1.
    hp_fix = (
        "(* revival FIX -- HP.Play dropped the FirstTrick? arg so the 2-of-clubs opening lead"
        " was never enforced for the human; add it, forward to H.GetLegals, stash as a window"
        " prop. Original bug kept faithful in the transcription -- see HEARTS-BUGS.md H1)\n"
        "(DEFINEQ\n"
        "(HP.Play (LAMBDA (HWin Trick HeartsBroken? FirstTrick?)\n"
        "    (LET ((Possibles (H.GetLegals (WINDOWPROP HWin (QUOTE Hand))\n"
        "                                  Trick HeartsBroken? FirstTrick?))\n"
        "          Card)\n"
        "      (WINDOWPROP HWin (QUOTE CurrentTrick) Trick)\n"
        "      (WINDOWPROP HWin (QUOTE HeartsBroken?) HeartsBroken?)\n"
        "      (WINDOWPROP HWin (QUOTE FirstTrick?) FirstTrick?)\n"
        "      (PROMPTPRINT (CONCAT \"Your turn, \" (WINDOWPROP HWin (QUOTE Name))))\n"
        "      (HP.WaitForReady HWin \"Please hurry. There are many impatient players here.\")\n"
        "      (SETQ Card (CAR (WINDOWPROP HWin (QUOTE SelectedCards))))\n"
        "      (while (NOT (MEMBER Card Possibles))\n"
        "         do (HP.Unselect HWin Card)\n"
        "            (PROMPTPRINT \"Illegal card. Try again.\")\n"
        "            (WINDOWPROP HWin (QUOTE Ready?) NIL)\n"
        "            (HP.WaitForReady HWin \"Please hurry. There are many impatient players here.\")\n"
        "            (SETQ Card (CAR (WINDOWPROP HWin (QUOTE SelectedCards)))))\n"
        "      (if (WINDOWPROP HWin (QUOTE Legal))\n"
        "          then (DOSELECTEDITEM (WINDOWPROP HWin (QUOTE HeartsMenu))\n"
        "                               (CADDDR (fetch ITEMS of (WINDOWPROP HWin (QUOTE HeartsMenu))))))\n"
        "      (HP.Unselect HWin Card)\n"
        "      (HP.RemoveCard HWin Card)\n"
        "      (WINDOWPROP HWin (QUOTE Ready?) NIL)\n"
        "      Card)))\n"
        ")\n")

    # 2k. Revival FIX (U2): H.Initialize reset the CT.All list but never CLOSED the previous
    #     game's card-table window(s), so replaying (LHearts ...) stacked a fresh card table
    #     over the old one. Close any still-open card tables before clearing the list. (BOUNDP
    #     guards the very first call, when CT.All is not yet set.) See HEARTS-BUGS.md U2.
    init_fix = (
        "(* revival FIX -- H.Initialize cleared the CT.All list but left the previous game's"
        " card-table windows on screen; close them first so replays don't stack. See HEARTS-BUGS.md U2)\n"
        "(DEFINEQ\n"
        "(H.Initialize (LAMBDA NIL\n"
        "    (HNET.GoodBye)\n"
        "    (COND ((BOUNDP (QUOTE CT.All))\n"
        "           (for CT in CT.All do (COND ((WINDOWP CT) (CLOSEW CT))))))\n"
        "    (SETQ CT.All)))\n"
        ")\n")

    # 2m. Revival FIX (U3, real cause): HP.RemakeHand -> HP.Reshape runs every deal and
    #     SHAPEWs the window to height (PLUS fontheight (fetch HEIGHT of OldReg)). That mixes
    #     region kinds / under-compensates for the title + attached-menu overhead, so the client
    #     shrinks a little each deal until the top (Clubs) card row is clipped under the menu --
    #     and it silently overrode the taller creation size. Keep the dynamic WIDTH, but pin the
    #     HEIGHT to a stable constant (320) so it never drifts. See HEARTS-BUGS.md U3.
    reshape_fix = (
        "(* revival FIX -- HP.Reshape recomputed height from the current region each deal and"
        " drifted smaller until the top card row clipped; pin a stable height. See HEARTS-BUGS.md U3)\n"
        "(DEFINEQ\n"
        "(HP.Reshape (LAMBDA (HWin Width)\n"
        "    (LET ((OldReg (WINDOWPROP HWin (QUOTE REGION))))\n"
        "      (SHAPEW HWin (CREATEREGION (fetch LEFT of OldReg)\n"
        "                                 (fetch BOTTOM of OldReg)\n"
        "                                 (PLUS 10 Width)\n"
        "                                 320))\n"
        "      (REDISPLAYW HWin))))\n"
        ")\n")

    ar_block = ("" if dist else
                "(* revival: our ACTIVEREGIONS reimplementation -- medley/activeregions.lisp)\n"
                + ar_src + "\n")
    patch = (
        "(* revival patch: ClownNames was undefined in the recovered source; names invented)\n"
        "(RPAQQ ClownNames (Bozo Chuckles Giggles Patches Sprinkles Coco Bubbles WackyWally Sniffles Doodles))\n"
        "(* revival default: ship ThinkFlag? as T so the Conservatives' reasoning shows in thought"
        " windows by default. The 1986 source defaults it NIL (kept faithful in the transcription);"
        " loaded after that, this override wins. (SETQ ThinkFlag? NIL) to silence.)\n"
        "(RPAQQ ThinkFlag? T)\n"
        + ar_block
        + clown_fix
        + ct_fix
        + card_fix
        + hp_fix
        + init_fix
        + reshape_fix)
    text = text.replace("(PUTPROPS HEARTS COPYRIGHT", patch + "(PUTPROPS HEARTS COPYRIGHT", 1)
    # 2h. Case-fix: HP.Menuer calls PromptPrint (mixed case) 3x, but the function is the
    #     system PROMPTPRINT and Interlisp is case-sensitive, so DWIM prompts at runtime.
    #     Original 1986 inconsistency (kept in the faithful transcription); correct it here.
    text = text.replace("PromptPrint", "PROMPTPRINT")
    # 2i. Revival FIX (display): the human hand window was 245px tall, but the option
    #     menu (Play/Pass/Score/LegalCards) is ATTACHWINDOW'd to its TOP, and the top
    #     card row (Clubs, y=176..221) sat only ~24px from the top edge -- so the menu
    #     hid the Clubs label + card bodies. Card rows are pinned to the window BOTTOM,
    #     so growing the height adds space at the TOP, right where the menu needs it.
    #     245 -> 300 gives the Clubs row ~79px of clearance. Scoped to HP.CreateWindow
    #     via its unique prompt string (Open/Dealer windows use the same 300 245 box but
    #     have no attached top menu). Original 1986 layout; corrected here. See HEARTS-BUGS.md U3.
    text = text.replace(
        '(GETBOXREGION 300 245 NIL NIL NIL (CONCAT "Position for your interface window, "',
        '(GETBOXREGION 300 300 NIL NIL NIL (CONCAT "Position for your interface window, "')
    # 2l. Revival FIX (H1, cont.): the LegalCards menu button in HP.Menuer recomputed the
    #     legal set via H.GetLegals WITHOUT FirstTrick?, so on the opening trick it would
    #     highlight the wrong cards. Feed it the FirstTrick? window prop that HP.Play (2j)
    #     now stashes. The `?]` superbracket form is unique to this call site.
    text = text.replace(
        "(WINDOWPROP HWin (QUOTE HeartsBroken?]",
        "(WINDOWPROP HWin (QUOTE HeartsBroken?))\n"
        "                                                  (WINDOWPROP HWin (QUOTE FirstTrick?]")
    # 2m. Revival FIX (H3): Card.MaxCard with an InSuit argument seeded `highest` from the
    #     FIRST card whatever its suit, so (Card.MaxCard '(KH 3S) 'S) returned the KH. Bites
    #     CardList.HighSpades? on mixed lists (the Expert's dump.hi.s "dump my highest spade"
    #     played a heart). Start from the first card that is in the suit. See HEARTS-BUGS.md H3.
    maxcard_fix = (
        "(* revival FIX H3 -- Card.MaxCard with InSuit started from the first card whatever"
        " its suit; start from the first card IN the suit)\n"
        "(DEFINEQ\n"
        "(Card.MaxCard (LAMBDA (CardList InSuit)\n"
        "    (LET ((highest NIL))\n"
        "      (for c in CardList do (if (AND (OR (NOT InSuit) (EQUAL (fetch Suit of c) InSuit))\n"
        "                                     (OR (NULL highest) (Card.Higher? c highest)))\n"
        "                                then (SETQ highest c)))\n"
        "      highest)))\n"
        ")\n")
    assert text.count("(PUTPROPS HEARTS COPYRIGHT") == 1
    text = text.replace("(PUTPROPS HEARTS COPYRIGHT", maxcard_fix + "(PUTPROPS HEARTS COPYRIGHT")
    # 3. arrow -> underscore
    text = text.replace("←", "_")
    # collapse runs of >2 blank lines left by stripping
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def build_activeregions():
    """Wrap the ACTIVEREGIONS fns as a standalone, loadable Interlisp lispusers module.

    Same fns/record as the inlined dev copy, but with a real FILEPKG header (FILECREATED +
    ACTIVEREGIONSCOMS) so the community can (FILESLOAD ACTIVEREGIONS), and later
    (MAKEFILE 'ACTIVEREGIONS)/(TCOMPL 'ACTIVEREGIONS) to compile it. ;; comments are
    stripped (not Interlisp syntax); the header uses (* ... ) Interlisp comments instead.
    """
    ar_src = load_ar_src()
    # Mirror the canonical minimal lispusers-file structure (cf. medley/library/CLIPBOARD):
    # DEFINE-FILE-INFO, then FILECREATED WITH a bytecount number after the filename token
    # (the newer file-loader compares it with IGREATERP; a missing number -> "NIL is not a
    # NUMBER"), PRETTYCOMPRINT, RPAQQ ...COMS, a SINGLE plain (* ...) comment (no bare `_`
    # assignment arrows, `/`, `--`, or nested parens -- those tripped the stricter reader),
    # the record + fns, then PUTPROPS.
    # NOTE: no top-level (* ...) banner comment here. A stray comment as the form right
    # after the COMS tripped the file reader on the current sysout (SYNTAXP -> IGREATERP ->
    # "NIL is not a NUMBER" while reading it). The human-readable docs live in
    # medley/activeregions.lisp and dist/README.md instead.
    body = (
        "(PRETTYCOMPRINT ACTIVEREGIONSCOMS)\n\n"
        "(RPAQQ ACTIVEREGIONSCOMS ((RECORDS ACTIVEREGION)\n"
        "                          (FNS ACTIVEREGIONS/DEFAULTHIGHLIGHTFN ACTIVEREGIONS/DOLOWLIGHT\n"
        "                               GETPICKREGION SETACTIVEREGIONS \\AR.REGIONUNDER \\AR.BUTTONEVENTFN)))\n\n"
        + ar_src + "\n\n"
        '(PUTPROPS ACTIVEREGIONS COPYRIGHT ("Harley Davis and Ramana Rao" 2026))\n'
        # H4: every Medley source file ends with STOP. Without it LOAD's file-map path (taken
        # because FILECREATED has a byte count) reads on to EOF and dies with "NIL is not a
        # NUMBER" (SYNTAXP of NIL in \\LOAD-STREAM) -- so on a fresh image the first load of
        # ACTIVEREGIONS, and of HEARTS, which FILESLOADs it, failed. See HEARTS-BUGS.md H4.
        'STOP\n')
    # DEFINE-FILE-INFO keys must be keywords (:PACKAGE), exactly as the real
    # library/CLIPBOARD file writes them -- bare PACKAGE -> "Unrecognized file info key".
    fileinfo = '(DEFINE-FILE-INFO :PACKAGE "INTERLISP" :READTABLE "INTERLISP" :BASE 10)\n\n'
    mk = lambda n: (fileinfo
                    + '(FILECREATED " 21-Aug-2026 22:00:00" ACTIVEREGIONS.;1 %d)\n\n' % n
                    + body)
    return mk(len(mk(0)))  # fill the bytecount with the file's own length


def _report(name, out):
    print(f"wrote {name}  ({len(out.splitlines())} lines)")
    assert "←" not in out, f"arrow left in {name}"
    assert "#|" not in out, f"annotation block left in {name}"
    assert not any(re.match(r"\s*;;", ln) for ln in out.split("\n")), f";; line left in {name}"


if __name__ == "__main__":
    raw = SRC.read_text(encoding="utf-8")

    # DEV build — self-contained, what we copy to ~/il and play with.
    dev = build(raw)
    OUT.write_text(dev, encoding="utf-8", newline="\n")
    _report(OUT, dev)

    # DIST package — the two-file build the community loads.
    DIST.mkdir(exist_ok=True)
    dist_hearts = build(raw, dist=True)
    (DIST / "HEARTS").write_text(dist_hearts, encoding="utf-8", newline="\n")
    _report(DIST / "HEARTS", dist_hearts)
    ar = build_activeregions()
    (DIST / "ACTIVEREGIONS").write_text(ar, encoding="utf-8", newline="\n")
    _report(DIST / "ACTIVEREGIONS", ar)
    assert "FILESLOAD ACTIVEREGIONS" in dist_hearts, "dist HEARTS should FILESLOAD ACTIVEREGIONS"
    # \AR.BUTTONEVENTFN is our lib's private handler -- HEARTS never calls it, so its
    # presence uniquely means the AR *definition* got inlined (dev), absence means it did not.
    assert "\\AR.BUTTONEVENTFN" not in dist_hearts, "dist HEARTS must not inline AR (FILESLOAD instead)"
    assert "\\AR.BUTTONEVENTFN" in dev, "dev HEARTS should inline AR"
