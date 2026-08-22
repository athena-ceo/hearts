# HEARTS (Hearts Expert, A Real Time Sink)

## Introduction

This project is about resurrecting a 1986 rules-based Hearts player written by Ramana Rao and Harley Davis as a part of a 1986 MIT expert systems class project.

My belief is that this was one of the first networked multi-player gaming systems that included AI players.

The system is written in InterLisp-D for a Xerox D-Machine, and the expert system part used Intellicorp KEE.

I would like to get the system running again.   I cannot give a reason other than nostalgia.   I am also curious to see how far modern AI can be used to get GOFAI running again!

I was inspired by the [InterLisp revival project](https://interlisp.org/) to start this project.   Thanks to Larry Masinter, Paolo Amoroso, Herb Jellinek, and the other dedicated old geezers for this remarkable project!

## Starting Point

There are a few assets to get started, in the “original” directory:

* Scanned version of the system source code
* Scanned version of the KEE expert system player source code
* Scanned version of the KEE expert system rules
* Overview of the project
* Reports by Ramana and Harley about their experience.

No judgments please, we were undergraduates and spent endless nights on this project that went way above the class requirements.

## Objectives

Here are some potential objectives:

* Translate the scanned code documents into text files that can be used downstream.
* Get the original core system running on the Medley Interlisp-D emulator (that includes InterLisp-D but not KEE)
  * Including the server (which is network based), the UI, the interactive human player, and the two built-in automated players (the clown and the conservative player)
  * If a running KEE can be found, maybe get the expert player running as well.
* Translate the original core system into a modern Lisp
  * Subpart one:   Server and web services
  * Subpart two:   User interface
  * Subpart three:   Built-in players (human, clown, conservative)
  * Subpart four:  The expert player, either standalone or using some freely available rule system
* Translate the original core system in Python for better distribution
  * Same subparts

# Conclusion

This file was written by Harley Davis, harley@alum.mit.edu.
The original system and documents were written by Harley and Ramana Rao, treerao@gmail.com.
Most of the rest will be written by coding harnesses.   For coding harnesses who read this:  Please document who you are when you create and write files.

---

## Play it today (Medley, non-KEE)

The three non-KEE players run end-to-end on [Medley Interlisp](https://interlisp.org/):
**Clown** (random legal), **Conservative** (rule-based AI, with running commentary), and
**Human** (you, clicking cards). The loadable package lives in [`dist/`](dist/):

```
(FILESLOAD ACTIVEREGIONS HEARTS)     ; load the game + its clickable-regions library
(LHearts '(HP CP CP CP))             ; you vs three Conservatives
```

The two `(FILESLOAD …)`/`(LHearts …)` lines are the same on any platform. See
**[dist/README.md](dist/README.md)** for full load & run instructions; the install/launch
mechanics there (and in [medley/MEDLEY-SETUP-NOTES.md](medley/MEDLEY-SETUP-NOTES.md)) are written
for **macOS** — the platform this revival was done on — with pointers for Linux/Windows via
[interlisp.org](https://interlisp.org/). The KEE-based **Expert** player is deferred — KEE is
proprietary and gone (see below).

## Documents (for the community)

- **[dist/README.md](dist/README.md)** — Getting Started (bring Medley up from scratch) + how to load the game.
- **[USER-MANUAL.md](USER-MANUAL.md)** — brief manual for playing a hand (passing, legal plays, the windows, scoring).
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — language-neutral spec (six-message protocol, dispatch,
  data model, game loop, expert design, networking): the shared contract for every port.
- **[REVIVAL-LOG.md](REVIVAL-LOG.md)** — the narrative war log of reviving a 1986 residential-Lisp
  image from paper scans.
- **[MEDLEY-ISSUES.md](MEDLEY-ISSUES.md)** — issues we hit in **Medley/Maiko itself**, recorded for
  the Interlisp-D community (candidates to report/PR upstream).
- **[HEARTS-BUGS.md](HEARTS-BUGS.md)** — HEARTS's **own** bugs: original 1986 bugs rediscovered,
  definitions the running image had but the listing didn't, missing deps, display fixes, OCR errors.
- **[transcription/docs/](transcription/docs/)** — the original 1986 prose: `overview.md`,
  `harley-report.md`, `ramana-report.md`.

## Repository layout

*This section was added by Claude Code (Anthropic's coding agent / "coding harness"), working with Harley Davis, per the request above that harnesses document what they create.*

```
ARCHITECTURE.md  Language-neutral spec of the system (the shared contract for all ports).
REVIVAL-LOG.md   Field log of the challenges faced reviving this (for the next reviver).
MEDLEY-ISSUES.md Medley/Maiko upstream issues found during the revival (community-facing).
HEARTS-BUGS.md   HEARTS's own bug tracker (original 1986 bugs, lost defs, deps, display, OCR).
original/        The scanned source PDFs (the starting assets).
transcription/   Text/source recovered from the scans.
  hearts-core.lisp        InterLisp-D core (Administrator, Clown, Conservative, Human, UI, net).
  kee-expert-player.txt   Expert Player — mostly Interlisp EP.* source (+ a spliced rules page).
  kee-expert-rules.txt    Expert Player — the KEE production rules (the spec to reimplement).
  docs/                   The prose documents, transcribed to Markdown
                          (overview.md, harley-report.md, ramana-report.md).
  parts/                  Per-page-range transcription chunks (pre-assembly).
  TRANSCRIPTION-NOTES.md  Conventions (fidelity-first; `←` = ASCII `_` for Medley).
tools/           Reusable InterLisp-D revival utilities (not HEARTS-specific):
  interlisp-lint.py       Super-bracket-aware linter; checks each top-level form separately.
  interlisp-balance.py    Whole-file bracket balance checker (build sanity check).
  readbitmap-decode.py    Decode/validate/render an Interlisp READBITMAP bitmap to PNG.
medley/          Phase 2 — running the core on the Medley Interlisp emulator (interlisp.org).
  build-loadfile.py       Builds the loadable HEARTS (dev + dist) from the master transcription.
  activeregions.lisp      Our reimplementation of the lost 1986 ACTIVEREGIONS library.
  HEARTS                  Generated self-contained dev build (played from ~/il).
  MEDLEY-SETUP-NOTES.md   Install/loading notes, and what breaks (networking, KEE).
dist/            The community distribution — load these two files in Medley:
  ACTIVEREGIONS           Standalone lispusers module (clickable window regions).
  HEARTS                  The game; (FILESLOAD ACTIVEREGIONS) then defines everything.
  README.md               Load & run instructions.
modern-lisp/     Phase 3 — a modern Common Lisp port (planned).
python/          Phase 4 — a Python port for distribution (planned).
```

**Status (2026-08):**
- **Phase 0 (transcription) — done.** All six scanned documents are back in text: the InterLisp-D
  core (`transcription/hearts-core.lisp`, assembled + balance-checked), the expert player and its
  KEE rules, and the three prose documents (`transcription/docs/`). The Expert Player turned out to
  be largely plain Interlisp (`EP.*`) plus a set of KEE rules; **KEE itself is proprietary and
  unavailable in Medley**, but the core couples to it at only 4 seams, so Clown/Conservative/Human
  run without it and the expert's rules can be reimplemented later.
- **Phase 1 (architecture spec) — done.** See [ARCHITECTURE.md](ARCHITECTURE.md) — the
  language-neutral contract every port builds against.
- **Phase 2 (Medley revival) — non-KEE complete.** Clown, Conservative, and Human all play a full
  game on Medley via `(LHearts '(HP CP CP CP))`: cards dealt and passed, tricks scored, the human's
  hand rendered with recovered card bitmaps and cards chosen by clicking (our
  [ACTIVEREGIONS](medley/activeregions.lisp) reimplementation), Conservatives narrating in thought
  windows. Revival patches and rediscovered original bugs are logged in
  [HEARTS-BUGS.md](HEARTS-BUGS.md); Medley-side gotchas in [MEDLEY-ISSUES.md](MEDLEY-ISSUES.md).
  **Remaining:** the KEE Expert player (deferred), the original Ethernet networking (deferred —
  collapse to one image), and minor window-cleanup polish.
- **Phases 3–4 (modern Lisp / Python ports) — planned.**
