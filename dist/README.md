# HEARTS — a 1986 InterLisp-D card game, revived for Medley

This directory is the loadable distribution of **HEARTS**, an expert-system Hearts game
originally written in InterLisp-D + KEE for MIT 6.871 (spring 1986) by Harley Davis and
Ramana Rao, brought back to life on modern [Medley Interlisp](https://interlisp.org/).

Three player types work today — **Clown** (random legal), **Conservative** (rule-based AI),
and **Human** (you, clicking cards). The KEE-based **Expert** player is not included (KEE is
proprietary and gone); see the project root for the revival story and the plan to reimplement it.

## Files

| File | What it is |
|------|------------|
| `ACTIVEREGIONS` | A standalone lispusers module: clickable/highlightable window regions, driven by the window `BUTTONEVENTFN`. A drop-in stand-in for the 1986 INTERMEZZO library of the same name, which modern Medley no longer ships. Reusable on its own. |
| `HEARTS` | The game. `(FILESLOAD ACTIVEREGIONS)`s the above, then defines everything else. |

## Getting started (from scratch)

Never run Medley before? Here's the whole path from nothing to dealing a hand.

**1. Install Medley Interlisp.** Download the prebuilt **`medley-full-macos-universal-*.zip`**
from the [Interlisp downloads page](https://interlisp.org/) (one universal binary works on both
Apple Silicon and Intel — no build needed). On macOS you'll also want **XQuartz** installed, and
you must clear Gatekeeper quarantine on the VM binaries once:

```bash
xattr -d com.apple.quarantine <path>/maiko/darwin.universal/lde*
```

(There's also an XQuartz-free **SDL** launch path we use on macOS; the exact framework/re-sign
recipe is in [MEDLEY-ISSUES.md](../MEDLEY-ISSUES.md) M4 and
[medley/MEDLEY-SETUP-NOTES.md](../medley/MEDLEY-SETUP-NOTES.md) §1.)

**2. Launch Medley into an _Interlisp_ Exec** (not the default Common Lisp one — HEARTS is
Interlisp):

```bash
cd <path-to>/medley_folder/medley
./medley --apps --interlisp --noscroll     # shorthand: ./medley -a -e -n
```

You'll get an Exec window with the classic `_` prompt.

**3. Get the two files where Medley can reach them.** Copy `ACTIVEREGIONS` and `HEARTS` (from this
`dist/` directory) into a folder on a mounted host directory — e.g. `~/il/`. In the Exec, connect
to that folder (`CONN`, or the File Browser), then load both:

```
(FILESLOAD ACTIVEREGIONS HEARTS)
```

(Loading details and the connect syntax are in
[medley/MEDLEY-SETUP-NOTES.md](../medley/MEDLEY-SETUP-NOTES.md) §2.)

**4. Deal a hand.** The argument is the four seats, clockwise:

```
(SETQ ThinkFlag? T)                      ; optional: let the Conservatives narrate
(LHearts '(HP CP CP CP))                 ; you (Human) vs three Conservatives
(LHearts '(CP CP CP CP))                 ; four Conservatives play themselves
(LHearts '(CLOWN CLOWN CLOWN CLOWN))     ; four random-legal Clowns
```

`HP` = Human, `CP` = Conservative, `CLOWN` = Clown. You'll be prompted for your name, then your
hand window opens.

## How to play

Click a card to select it, then use the window's **Play** / **Pass** menu. The full rules of the
table — passing, legal plays, reading the scores, the thought windows — are in the
**[user manual](../USER-MANUAL.md)**.

## Notes for macOS / SDL users

Medley on macOS runs headless-ish through the SDL backend (`--maikoprog ldesdl`, no XQuartz).
Setup gotchas we hit (framework install, an `install_name_tool` rpath fix, ad-hoc re-signing,
and a clipboard/subprocess caveat) are written up in the project's
[MEDLEY-ISSUES.md](../MEDLEY-ISSUES.md).

## Provenance

- Faithful transcription of the original listing lives in `transcription/` at the project root.
- The loadable `HEARTS` here is that transcription with mechanical revival patches folded in
  (a handful of definitions the 1986 running image had but the paper listing didn't, plus a few
  original-1986 bug fixes). Every patch is documented in `HEARTS-BUGS.md` at the project root.
- Icons are stubbed (the two 50×50 icon bitmaps were lost); the five card bitmaps are recovered
  and real, so suits draw legibly.

To recompile for speed inside Medley: `(MAKEFILE 'ACTIVEREGIONS)` then `(TCOMPL 'ACTIVEREGIONS)`,
and likewise for `HEARTS` — then ship the resulting `.DCOM`s.
