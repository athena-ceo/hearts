# HANDOFF — HEARTS revival

Start-here orientation for anyone (a person or a coding agent) picking this project up. It
summarizes **where things stand, how to run and rebuild it, the conventions that keep it sane, what's
left, and the roadmap.** Details live in the linked docs; this file is the map.

*Written by Claude Code (Anthropic coding agent) with Harley Davis, 2026-08-22.*

---

## TL;DR

The **entire non-KEE HEARTS system runs, end to end, on current Medley Interlisp** — Clown,
Conservative, and Human players; dealing, passing, trick play, scoring (moon shots included); a
clickable hand window; and the Conservatives' thought windows. Confirmed on the **Aug-2026 Medley
release (260810) over X11** on macOS, with working host clipboard, keyboard, and SEdit.

What's **not** done: the **KEE Expert player** (the adaptive one — KEE is proprietary and gone) and
the original **Ethernet networking**; both are deferred, with a plan below. Modern Common Lisp and
Python ports are future phases.

See it in action: [docs/hearts-game.png](docs/hearts-game.png).

---

## Current state

| Piece | Status |
|---|---|
| Transcription of the 1986 listing | ✅ complete, balance-checked ([transcription/](transcription/)) |
| Architecture spec | ✅ [ARCHITECTURE.md](ARCHITECTURE.md) |
| Loads on Medley | ✅ `(FILESLOAD CLIPBOARD ACTIVEREGIONS HEARTS)` clean on 260810/X11 |
| **Clown** player | ✅ plays |
| **Conservative** player | ✅ plays (one fixed *minimizing* strategy in Lisp; non-adaptive) |
| **Human** player | ✅ plays — name prompt, hand window, cards chosen by clicking |
| Card artwork (suit pips) | ✅ recovered & rendering ([tools/readbitmap-decode.py](tools/readbitmap-decode.py)) |
| ACTIVEREGIONS (clickable regions) | ✅ reimplemented ([medley/activeregions.lisp](medley/activeregions.lisp)) |
| Host clipboard / keyboard / SEdit | ✅ working on **X11** (not SDL — see MEDLEY-ISSUES) |
| Distribution package | ✅ [dist/](dist/) — `ACTIVEREGIONS` + `HEARTS` + README |
| **KEE Expert** player | ⛔ deferred (KEE gone; ~90 rules to reimplement) |
| Ethernet networking | ⛔ deferred (dead PUP/XNS; collapse to one image) |
| Modern CL / Python ports | 🔜 planned (Phases 3–4) |

Original 1986 bugs found and fixed, plus every revival patch, are in [HEARTS-BUGS.md](HEARTS-BUGS.md).
Every Medley/Maiko issue hit (and how it resolved) is in [MEDLEY-ISSUES.md](MEDLEY-ISSUES.md). The
narrative of the whole revival is [REVIVAL-LOG.md](REVIVAL-LOG.md).

---

## How to run it (the working setup)

Environment on this machine: repo at `~/Development/hearts`, Medley at `~/medley-260810` (note the
**space-free path** — the launcher breaks on spaces, MEDLEY-ISSUES M7), files loaded from the
connected dir `~/il`.

```bash
open -a XQuartz && cd ~/medley-260810/medley && export OSTYPE=darwin && ./medley --apps --interlisp --noscroll
```

Then, in the Interlisp Exec:

```
(FILESLOAD CLIPBOARD ACTIVEREGIONS HEARTS)
(LHearts '(HP CP CP CP))
```

Full setup (XQuartz tuning, leave-X-running, auto-load via `rem.cm`, quit with `(LOGOUT)` /
`pkill ldex`) is in [medley/MEDLEY-SETUP-NOTES.md](medley/MEDLEY-SETUP-NOTES.md) §1a. How to play is
in [USER-MANUAL.md](USER-MANUAL.md); first-time-on-Medley steps are in [dist/README.md](dist/README.md).

**Use X11, not SDL.** The SDL backend (`--maikoprog ldesdl`) gives a native window with no XQuartz
and the game plays, but on the current build it has no clipboard, an incomplete keyboard map, and
SEdit wedges. X11 has all three. (Root causes: MEDLEY-ISSUES M2/M3/M8.)

---

## How to rebuild the loadable files

The loadable `HEARTS` is **generated** from the faithful transcription — never hand-edit it. Edit the
source, then rebuild:

```bash
cd ~/Development/hearts
python3 medley/build-loadfile.py          # writes medley/HEARTS (dev) + dist/HEARTS + dist/ACTIVEREGIONS
cp dist/HEARTS dist/ACTIVEREGIONS ~/il/    # stage where Medley loads them
```

Then reload in Medley (`(FILESLOAD ACTIVEREGIONS HEARTS)`), or relaunch.

- **Source of truth:** [transcription/hearts-core.lisp](transcription/hearts-core.lisp) (assembled
  from [transcription/parts/](transcription/parts/)) + [medley/activeregions.lisp](medley/activeregions.lisp).
- **Build script:** [medley/build-loadfile.py](medley/build-loadfile.py) — does mechanical transforms
  (`←`→`_`, strip our annotations, stub the lost icon bitmaps) and injects **documented revival
  patches** (missing definitions + original-bug fixes). It emits two builds: `medley/HEARTS`
  (self-contained, ACTIVEREGIONS inlined — handy for one-file dev loads) and `dist/` (two files:
  `HEARTS` `(FILESLOAD ACTIVEREGIONS)`s the separate module — the community distribution).
- **Sanity tools:** [tools/interlisp-balance.py](tools/interlisp-balance.py) (whole-file bracket
  balance) and [tools/interlisp-lint.py](tools/interlisp-lint.py) (per-top-level-form, catches
  super-bracket slips that mask each other).

---

## Conventions (please keep these)

1. **Faithful transcription stays faithful.** [transcription/](transcription/) matches the 1986 paper
   listing, warts (original bugs, OCR-verified `[`/`(`) and all. Fixes and reconstructions go in
   `build-loadfile.py` as labeled revival patches — never by editing the master. This keeps "what
   they wrote" separate from "what we changed to run it."
2. **Two bug trackers, by audience.** [HEARTS-BUGS.md](HEARTS-BUGS.md) = HEARTS's own bugs (for us);
   [MEDLEY-ISSUES.md](MEDLEY-ISSUES.md) = Medley/Maiko upstream issues (for the Interlisp community).
3. **Verify OCR against the scans.** For any `[`/`(` or packed-bitmap question, the 300-DPI scan is
   ground truth (`pdftoppm -r 300` + a tight crop). Don't guess.
4. **Interlisp is case-sensitive.** `LHearts` ≠ `LHEARTS`. Watch this in both the code and when
   reaching HEARTS symbols from a Common Lisp exec (`IL::|LHearts|`).
5. **Commit messages** end with the `Co-Authored-By` trailer; keep the trackers/docs updated in the
   same commit as the change they describe.

---

## Follow-ups (near-term, concrete)

- **Contribute ACTIVEREGIONS upstream.** It's a clean, reusable stand-in for the lost INTERMEZZO
  library — worth a PR to the community `lispusers` collection. Compile with `(MAKEFILE 'ACTIVEREGIONS)`
  then `(TCOMPL 'ACTIVEREGIONS)` and ship the `.DCOM` alongside source.
- **Report the confirmed Medley/Maiko issues** to the Maiko/Medley project: M2 (the `unixcomm`
  helper is forked only by the `lde` kickstarter, so a direct `ldesdl` launch has no
  subprocess/clipboard), M3 (SDL region-sweep wedge), M7 (launcher breaks on spaces), M8 (SDL
  keyboard map). All have file:line evidence in [MEDLEY-ISSUES.md](MEDLEY-ISSUES.md).
- **Announce it** — interlisp.org Zulip / the Interlisp community, and Ramana. The
  [docs/hearts-game.png](docs/hearts-game.png) screenshot is the hook.
- **Finish U2** (minor): replaying `(LHearts …)` still leaves per-player *thought* and *hand* windows
  stacked (only the card table is now closed on re-init). Track and close them too if it bothers you.
- **Optional:** recover or redraw the 50×50 desktop icon bitmaps (currently stubbed) if you want the
  `H.MakeIcon` desktop icon back.

---

## Roadmap

- **Phase 0 — Transcription.** ✅ Done.
- **Phase 1 — Architecture spec.** ✅ Done ([ARCHITECTURE.md](ARCHITECTURE.md)).
- **Phase 2 — Medley revival (non-KEE).** ✅ **Done** — Clown, Conservative, Human all play on
  current Medley/X11.
- **Phase 2b — The KEE Expert player.** The interesting one: it's the player that *adaptively
  reasons* about the game (models opponents, re-plans) — unlike the fixed-strategy Conservative. KEE
  itself is gone, but the spec survives: the ~90 production rules in
  [transcription/kee-expert-rules.txt](transcription/kee-expert-rules.txt) and the Interlisp `EP.*`
  glue in [transcription/kee-expert-player.txt](transcription/kee-expert-player.txt). The core couples
  to it at only **4 `UNITMSG` seams** (see ARCHITECTURE §8), so it can be reimplemented as plain Lisp
  (or a small rules engine) behind those seams without touching the rest.
- **Phase 2c — Networking.** The original 4-machine Ethernet design (`EVALSERVER`/PUP/XNS) is dead.
  Plan: collapse to a single image running four processes (Medley multiprocessing already backs the
  in-image multiplayer that works today), or a modern socket transport — optional, and mostly
  interesting for period authenticity.
- **Phase 3 — Modern Common Lisp port.** Build against the language-neutral contract in
  [ARCHITECTURE.md](ARCHITECTURE.md) (six-message protocol, dispatch, data model, game loop).
- **Phase 4 — Python port.** Same contract, for broad distribution.

---

## Repo map

```
README.md            Project intro (origin story) + "play it today" + doc index
HANDOFF.md           This file
ARCHITECTURE.md      Language-neutral spec — the contract for every port
REVIVAL-LOG.md       Narrative field log of the whole revival (Challenges 1–16)
HEARTS-BUGS.md       HEARTS's own bugs (original 1986 + revival patches)
MEDLEY-ISSUES.md     Medley/Maiko upstream issues (for the community)
USER-MANUAL.md       How to play a hand
docs/hearts-game.png Screenshot of a game in progress
original/            The scanned source PDFs (starting assets)
transcription/       Faithful text recovered from the scans (+ parts/, docs/, KEE files)
tools/               interlisp-lint.py, interlisp-balance.py, readbitmap-decode.py
medley/              build-loadfile.py, activeregions.lisp, HEARTS (dev build), MEDLEY-SETUP-NOTES.md
dist/                Community distribution: ACTIVEREGIONS, HEARTS, README.md
modern-lisp/         Phase 3 (planned)
python/              Phase 4 (planned)
```

GitHub: <https://github.com/athena-ceo/hearts>
