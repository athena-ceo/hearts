# Reviving HEARTS — a field log of the challenges

*A running account of what it actually takes to bring a 1986 InterLisp-D / KEE program back
to life on modern hardware. Kept for the next person who tries something like this — and for
the small, valiant InterLisp-D community, who will recognize every one of these.*

*Maintained by Claude Code (Anthropic coding agent), working with Harley Davis. Newest entries
appended at the bottom.*

---

## The setting

HEARTS ("Hearts Expert, A Real Time Sink") is a 1986 MIT 6.871 project by Harley Davis and
Ramana Rao: a four-player networked Hearts game with AI players, written in InterLisp-D for the
Xerox Dandelion, with the expert player built in KEE. Forty years later, the only surviving
artifacts are **six scanned PDFs** — no source files, no disk images, no sysout. The goal:
get it running again on **Medley Interlisp** (https://interlisp.org/).

---

## Challenge 1 — The source is a stack of photocopies

The "source code" is a scanned paper listing: 47 pages for the core, 31 more for the KEE
expert player and rules. No text layer. Everything has to be read back out of images.

- **Watch out for:** the scans are *clean* (a 1986 laser printout, high contrast), which makes
  OCR feasible — but a card game's source is dense with parentheses, and every one matters.
- **What worked:** rendering each page with `poppler` (`pdftoppm`) and transcribing visually,
  fanning the 78 code pages out across parallel agents (one per page-range) writing to separate
  files, then reconciling. Across all 78 pages only ~6 characters were genuinely illegible.

## Challenge 2 — The arrow that is secretly an underscore

InterLisp's assignment operator prints as a left-arrow `←`, but on the wire it is **ASCII
underscore `_` (code 95)** — `←` is just the display glyph. Get this wrong and *every*
assignment in the file mis-parses.

- **What worked:** keep the human-readable master with `←` (it matches the printout and reads
  well), and generate the Medley-loadable copy with a one-line `←`→`_` substitution. Best of
  both; verified by actually loading in Medley.

## Challenge 3 — Getting Medley to run at all on a modern Mac

- `--vnc` (the headless display path) is **explicitly unavailable on macOS**. That leaves X11
  (XQuartz) or SDL.
- The SDL backend (`ldesdl`) needs **SDL2.framework**, which wasn't installed, and its rpath
  pointed at `/Library/Frameworks` (admin-only).
- `DYLD_FRAMEWORK_PATH` didn't help: macOS **strips `DYLD_*` when the launch chain passes through
  a SIP-protected system binary** (`/bin/bash`), so it never reached the VM.
- **What worked:** install SDL2.framework into `~/Library/Frameworks` (no admin), then
  `install_name_tool -change` the VM's SDL2 reference to that path and re-sign it ad-hoc
  (`codesign -f -s -`). Medley then boots to a native Cocoa window — **no XQuartz needed**.

## Challenge 4 — Feeding commands to a 1986 Exec headlessly

- The `--rem.cm` startup file looked like the way to auto-load without typing. But `INTERPRET.REM.CM`
  (found in Medley's own `ADIR` sources) **evaluates only the *first* form in the file** — a
  multi-form script silently runs just its first line. Wrap everything in one `(PROGN …)`.
- File paths in Interlisp are `{DSK}<dir>sub>name`, **not** Unix `/a/b/c`. A Unix path passed to
  `OPENSTREAM`/`LOAD` just fails.
- Pasting from the macOS clipboard into the SDL window didn't work.
- **What worked (for now):** drop the load file into the Exec's *connected directory* (`~/il`) so
  it loads with a bare `(LOAD 'HEARTS)` — no path, minimal typing. (A robust auto-load harness is
  still on the wish list.)

## Challenge 5 — Super-brackets, OCR, and a load that stops after four functions

This is the big one. InterLisp's `[ ]` "super-brackets" auto-close any number of open `(` —
`]` closes back to the nearest `[`. Prettyprinted 1986 code uses them *heavily*. And in a scan,
**`[` and `(` look almost identical**.

The first Medley load defined exactly four functions and stopped. The culprit: OCR bracket slips
that prematurely closed the enclosing `(DEFINEQ`, so every function after the slip silently failed
to define. Six functions were affected, in two flavors:

1. **`[` misread as `(`** at a `LET`/`PROG`/`SELECTQ`-clause opener — so the matching `]` had no
   `[` to close to and over-closed to the enclosing `[LAMBDA`, ending the function early.
   (`HNET.Hello`, `Hand.RemoveCard`, `Dealer.Menuer`, `HP.Menuer`.)
2. **A closing `]` expanded into `)))`** — the transcriber "helpfully" wrote out explicit parens
   but dropped the level the `]` also closed (e.g. a `PROG` var-list), leaving a bracket open.
   (`H.Setup`, `HP.PassOut`.)

- **Nasty property: the errors *mask each other*.** In a whole-file bracket count, one function's
  extra-close cancels another's missing-close, so the file "nets to zero" while being deeply
  broken. Fixing one error makes the next one appear.
- **What worked:** an InterLisp-aware bracket linter (`tools/`) that models
  super-bracket semantics and — crucially — checks **each top-level form independently** so errors
  can't hide behind each other. It localizes the broken function and the exact line; then a
  **high-resolution crop of the original scan** (`pdftoppm -r 300` + a tight PIL crop) settles
  `[` vs `(` beyond doubt. Every fix was verified against the paper, not guessed.
- **Lesson for others:** do not trust a global paren count on Interlisp source. Check per-form,
  and keep the scans handy — the ground truth for a `[`/`(` call is the paper, at 300+ DPI.

## Challenge 6 — The whole file loads… then dies on the artwork

With the six super-bracket bugs fixed, the linter went fully green and Medley loaded **every
function and record** — the entire game logic — before stopping. Where it stopped: a
`READBITMAP` near the end of the file, with `Invalid argument: -30`.

That's the **"Random Cruff"** block: seven packed-bitmap literals (a card outline, four suit
pips, and the 50×50 app icon + shadow). These were transcribed *best-effort* — the packed
strings are dense grids of `O`/`0`/`@`/`L` glyphs that OCR can't nail per-character, and one bad
char is enough to make `READBITMAP` compute a nonsense dimension and fault.

- **Key realization:** the bitmaps are pure decoration and are **not needed to run the core**.
- **What worked:** keep the (imperfect) bitmap data in the master for later, but have the build
  step swap each `(RPAQ NAME (READBITMAP)) (W H "rows"…)` for a blank
  `(RPAQ NAME (BITMAPCREATE W H))` of the same size. The load sails past.
- Same treatment for two other end-of-file forms that can't work yet: the `FILESLOAD` of the
  dead `EVALSERVER`/`ACTIVEREGIONS` DCOMs, and the top-level `(H.MakeIcon)` desktop-icon call —
  both replaced with `(* … )` no-ops in the load build.
- **Lesson:** separate *faithful transcription* from *loadable artifact*. The master stays true
  to the paper; a small, documented build step makes the version that actually boots. Don't let
  1986 artwork or dead peripherals block bringing the logic up.
- **BUT the suit bitmaps are not optional.** The card table draws each card's suit from
  `Clubs/Diamonds/Hearts/SpadesBits`; a human player literally cannot read their hand without
  them. So the stubs are temporary — the artwork *must* be recovered for a playable UI.
  What makes that feasible: the `READBITMAP` "hardcopy" packing is now understood — each
  character is a 4-bit nibble (`@`=0 … `O`=15, letters only — a literal `0`/`O` slip is fatal),
  and each raster row is padded to a 16-bit word (so 11-wide → 4 chars/row, 30-wide → 8). That
  gives a hard validator (row length, legal charset) and, better, lets us *decode and render*
  each bitmap to eyeball whether it actually looks like a ♣/♦/♥/♠ before trusting it. The four
  11×11 suit pips are small and very recoverable; the 50×50 desktop icon is lower priority.

## Still ahead (known, not yet hit)

- **KEE is gone.** IntelliCorp's KEE was proprietary and never open-sourced; the expert player's
  rules must be reimplemented. The good news: the core couples to KEE at only 4 `UNITMSG` seams.
- **Networking is gone.** The Ethernet `EVALSERVER`/PUP/XNS remote-eval layer the four-machine
  game rode on is non-functional in Medley; plan is to collapse to one image with four processes.
  (The file ends with a `FILESLOAD` of `EVALSERVER.DCOM` that will fail to load — expected.)
- **Window geometry/fonts** are hard-coded for a 1024×808 Dandelion display and will need tuning.
