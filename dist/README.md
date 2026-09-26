# HEARTS — a 1986 InterLisp-D card game, revived for Medley

This directory is the loadable distribution of **HEARTS**, an expert-system Hearts game
originally written in InterLisp-D + KEE for MIT 6.871 (spring 1986) by Harley Davis and
Ramana Rao, brought back to life on modern [Medley Interlisp](https://interlisp.org/).

All four player types work — **Clown** (random legal), **Conservative** (a single fixed
*minimizing* strategy in Lisp — plays competently but doesn't adapt), **Human** (you, clicking
cards), and the **Expert**: the 1986 KEE expert system, which chooses a strategy (minimize, shoot
the moon, or "eclipse" a shooter), models each opponent with certainty factors, and re-plans after
every trick. KEE itself is proprietary and gone; the Expert runs its original code and its 97
original rules on **KEELOOPS**, a small KEE compatibility layer built on Xerox **LOOPS**.

## Files

| File | What it is |
|------|------------|
| `ACTIVEREGIONS` | A standalone lispusers module: clickable/highlightable window regions, driven by the window `BUTTONEVENTFN`. A drop-in stand-in for the 1986 INTERMEZZO library of the same name, which modern Medley no longer ships. Reusable on its own. |
| `HEARTS` | The game. `(FILESLOAD ACTIVEREGIONS)`s the above, then defines everything else. |
| `KEELOOPS` | A reusable KEE compatibility layer on LOOPS: KEE units/slots/message handlers as LOOPS objects, plus `QUERY`, a backward-chaining interpreter for KEE's rule language (weights, `THE … OF … IS …` patterns, EMYCIN certainty factors). Loads LOOPS itself if it can find it. |
| `PLAYHEARTS` | A 2026 front door: `(PlayHearts)` asks for the players and options with menus, then puts a **Start Game · Setup… · Exit** menu bar on the card table; games run in their own process and Exit closes every Hearts window. Loads HEARTS (and EXPERT, if needed) itself. The 1986 `LHearts` is unchanged. |
| `EXPERT` | The Expert player: the reconstructed KEE knowledge base, the original 1986 `EP.*` code, and the original rules. `(FILESLOAD KEELOOPS)`s the above. Needs `HEARTS`. |

## Getting started (from scratch)

> **These install/launch steps are for macOS** (Apple Silicon or Intel) — that's the platform
> this revival was done on. The **in-Lisp steps are identical on every platform** (`FILESLOAD`,
> `LHearts`, …); only the download/launch shell mechanics differ. Linux and Windows/WSL users:
> grab the matching release from [interlisp.org](https://interlisp.org/) and launch per their
> docs, then pick up at step 3. A polished macOS daily workflow (stop the XQuartz xterm, leave
> the X server running, auto-load libraries, quit cleanly) is in
> [medley/MEDLEY-SETUP-NOTES.md](../medley/MEDLEY-SETUP-NOTES.md) §1a.

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

**3b. (For the Expert) get LOOPS.** It isn't in the Medley release. Clone
[Interlisp/loops](https://github.com/Interlisp/loops) next to your `medley/` directory:

```bash
cd <path-to>/medley_folder && git clone https://github.com/Interlisp/loops
```

then copy `KEELOOPS` and `EXPERT` beside `HEARTS` and load them too:

```
(FILESLOAD ACTIVEREGIONS HEARTS EXPERT)
```

EXPERT finds and loads LOOPS on its own (or set `LOOPSDIR` to your checkout, or load LOOPS first
yourself). Loading LOOPS prints a page of messages; that's normal.

**4. Play.** The simplest way is the menu-driven front door:

```
(FILESLOAD PLAYHEARTS)
(PlayHearts)
```

It asks who plays and how, then opens the card table with **Start Game · Setup… · Exit**. Or deal
directly with the 1986 entry point, as below (it plays game after game until you interrupt it
with Ctrl-E).

**4b. Deal a hand the 1986 way.** The argument is the four seats, clockwise:

```
(LHearts '(HP CP CP CP))
(LHearts '(CP CP CP CP))
(LHearts '(CLOWN CLOWN CLOWN CLOWN))
```

`HP` = Human, `CP` = Conservative, `EP` = Expert, `CLOWN` = Clown (try `(LHearts '(HP EP EP CP))`) — so the first line is you vs three
Conservatives, the second is four Conservatives playing themselves, the third is four random-legal
Clowns. You'll be prompted for your name, then your hand window opens. The Conservatives narrate
their reasoning in "Thoughts of …" windows **by default**; `(SETQ ThinkFlag? NIL)` before starting
to silence them.

## How to play

Click a card to select it, then use the window's **Play** / **Pass** menu. The full rules of the
table — passing, legal plays, reading the scores, the thought windows — are in the
**[user manual](../USER-MANUAL.md)**.

## Notes for macOS users (display backends)

macOS has two display backends, with a real tradeoff:

- **X11** (default `lde` → `ldex`, needs **XQuartz**) — **recommended.** Forks the `unixcomm`
  helper (so the **host clipboard works**), has the mature keyboard map, and runs SEdit without
  wedging. This is the full-featured path.
- **SDL** (`--maikoprog ldesdl`) — a native macOS window with **no XQuartz**, and the mouse-driven
  game plays fine on it. But on the current build it has **no clipboard** and an **incomplete
  keyboard map** (⌘ unmapped), and needs an `SDL2.framework` rpath fix. Fine for playing; not for
  editing or copy/paste.

The smooth macOS/X11 daily setup is in [medley/MEDLEY-SETUP-NOTES.md](../medley/MEDLEY-SETUP-NOTES.md)
§1a; the underlying root-causes (clipboard helper, keyboard, SDL framework) are in
[MEDLEY-ISSUES.md](../MEDLEY-ISSUES.md) (M1–M8).

## Provenance

- Faithful transcription of the original listing lives in `transcription/` at the project root.
- The loadable `HEARTS` here is that transcription with mechanical revival patches folded in
  (a handful of definitions the 1986 running image had but the paper listing didn't, plus a few
  original-1986 bug fixes). Every patch is documented in `HEARTS-BUGS.md` at the project root.
- Icons are stubbed (the two 50×50 icon bitmaps were lost); the five card bitmaps are recovered
  and real, so suits draw legibly.

To recompile for speed inside Medley: `(MAKEFILE 'ACTIVEREGIONS)` then `(TCOMPL 'ACTIVEREGIONS)`,
and likewise for `HEARTS` — then ship the resulting `.DCOM`s.
