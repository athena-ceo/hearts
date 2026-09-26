# HANDOFF — HEARTS revival

Start-here orientation for anyone (a person or a coding agent) picking this project up. It
summarizes **where things stand, how to run and rebuild it, the conventions that keep it sane, what's
left, and the roadmap.** Details live in the linked docs; this file is the map.

*Written by Claude Code (Anthropic coding agent) with Harley Davis, 2026-08-22; Expert player
(Phase 2b) and headless test environment added 2026-09-26.*

---

## TL;DR

The **entire HEARTS system — including the KEE Expert player — runs on current Medley
Interlisp.** Clown, Conservative and Human players play on the Aug-2026 release (260810) over X11
on macOS. The **Expert** (Phase 2b) runs its *original* 1986 code and all 97 *original* rules on
**KEELOOPS**, a small KEE compatibility layer built on Xerox LOOPS; it passes, plays, models its
opponents with certainty factors, and switches between minimizing, shooting and eclipsing. It is
verified in the **headless Docker Medley** ([docker/](docker/)): full four-Expert and Expert-vs-
Conservative games (every play legal, no rule errors), and a replay of the 1986 overview's worked
examples that reproduces the paper's rule firings and certainty factors. It has not yet been
played interactively on the Mac.

What's **not** done: the original **Ethernet networking** (deferred). Modern Common Lisp and
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
| Distribution package | ✅ [dist/](dist/) — `ACTIVEREGIONS` + `HEARTS` + `KEELOOPS` + `EXPERT` + README (fresh-image `FILESLOAD` fixed: HEARTS-BUGS H4) |
| **KEE Expert** player | ✅ runs headlessly — original `EP.*` code + 97 original rules on KEELOOPS/LOOPS ([medley/keeloops.lisp](medley/keeloops.lisp), [medley/expert-kb.lisp](medley/expert-kb.lisp)); tests in [tests/](tests/). Not yet tried interactively on the Mac. |
| Headless test Medley | ✅ [docker/](docker/) + [tools/medley-headless](tools/medley-headless) |
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

For the **Expert**, also load `EXPERT` (after HEARTS) — it needs LOOPS, which isn't in the Medley
release: `git clone https://github.com/Interlisp/loops ~/medley-260810/loops` once, and EXPERT loads
it itself (or set `LOOPSDIR`). Then e.g. `(LHearts '(HP EP EP CP) T)` — `T` = open hands, so each
Expert's window narrates its strategy and reasons.

The friendlier front door is **`(FILESLOAD PLAYHEARTS)` then `(PlayHearts)`**
([medley/playhearts.lisp](medley/playhearts.lisp), built into `dist/PLAYHEARTS`): menus for the
players and options, a Start Game / Setup… / Exit menu bar on the card table, games in their own
process, and Exit closes every Hearts window. It only adds `PH.*` functions — the 1986 `LHearts`
(which starts at once and loops until Ctrl-E) is untouched.

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
python3 medley/build_expert.py            # writes medley/EXPERT (dev) + dist/EXPERT + dist/KEELOOPS
cp dist/HEARTS dist/ACTIVEREGIONS dist/KEELOOPS dist/EXPERT ~/il/    # stage where Medley loads them
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
- **Expert:** [medley/build_expert.py](medley/build_expert.py) reads the two KEE transcriptions
  (re-splicing the rules page that was bound into the EXPERT listing), applies revival patches
  K0–K16, re-emits the rules as `KEE.DEFRULE` data, and checks every definition's structure
  (including `LET`s closed too early — the class of OCR slip bracket linters can't see).
  Hand-written sources: [medley/keeloops.lisp](medley/keeloops.lisp) (KEE on LOOPS + the rule
  interpreter) and [medley/expert-kb.lisp](medley/expert-kb.lisp) (the reconstructed KB).

## How to test (headless Medley in Docker)

```bash
tools/medley-headless --build                                   # once
tools/medley-headless tests/smoke.lisp                          # harness self-test
tools/medley-headless --loops tests/expert-load.lisp            # KB wiring, pass/pass-in
tools/medley-headless --loops tests/expert-examples.lisp        # the 1986 worked examples
tools/medley-headless --loops tests/playhearts.lisp             # the PlayHearts front end
tools/medley-headless --loops --timeout 1500 tests/expert-game.lisp   # two full games (~12 min)
tests/run-all.sh                                                # everything, with a summary
tools/medley-headless --loops --timeout 2700 tests/expert-soak.lisp  # 3 more games, rare-situation hunt
```

Scripts are Interlisp forms; `HT.CHECK` gives PASS/FAIL lines, `HT.SNAP` screenshots the virtual
display. Output in `out/medley/`. Details and the Medley automation traps it works around:
[docker/README.md](docker/README.md).


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
- **Play the Expert on the Mac.** Clone LOOPS beside Medley, load EXPERT, and play
  `(LHearts '(HP EP EP EP) T)`; watch the narration. Only the headless runs have been done.
- **Tune the reconstructed personality** ([medley/expert-kb.lisp](medley/expert-kb.lisp)) —
  four values are from the 1986 overview, TriggerHappiness is inferred, the rest are guesses.


## Roadmap

- **Phase 0 — Transcription.** ✅ Done.
- **Phase 1 — Architecture spec.** ✅ Done ([ARCHITECTURE.md](ARCHITECTURE.md)).
- **Phase 2 — Medley revival (non-KEE).** ✅ **Done** — Clown, Conservative, Human all play on
  current Medley/X11.
- **Phase 2b — The KEE Expert player.** ✅ **Runs** (headless-verified; interactive Mac play still
  to do). KEE is gone, so instead of re-writing the rules we re-provided the part of KEE they use:
  **KEELOOPS** maps KEE units/slots/message handlers onto LOOPS objects and interprets the KEE rule
  language (backward chaining by weight, `THE … OF … IS …` patterns, unstructured facts, EMYCIN
  certainty factors). The original `EP.*` code and all 97 rules run from the transcription; the lost
  KB (unit classes, handler wiring, personality thresholds) is reconstructed from the code and the
  1986 overview. See REVIVAL-LOG Challenges 17–20 and HEARTS-BUGS section K.
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
tools/               interlisp-lint.py, interlisp-balance.py, readbitmap-decode.py, medley-headless
medley/              build-loadfile.py, activeregions.lisp, HEARTS (dev build), MEDLEY-SETUP-NOTES.md,
                     build_expert.py, keeloops.lisp, expert-kb.lisp, EXPERT (dev build), playhearts.lisp
dist/                Community distribution: ACTIVEREGIONS, HEARTS, KEELOOPS, EXPERT, PLAYHEARTS, README.md
docker/              Headless Medley (Maiko + Xvfb + LOOPS) for scripted tests
tests/               Headless test scripts (tools/medley-headless ...)
attic/               Superseded work kept for the record (the first Expert attempt)
modern-lisp/         Phase 3 (planned)
python/              Phase 4 (planned)
```

GitHub: <https://github.com/athena-ceo/hearts>
