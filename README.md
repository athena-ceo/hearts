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

## Repository layout & status

*This section was added by Claude Code (Anthropic's coding agent / "coding harness"), working with Harley Davis, per the request above that harnesses document what they create.*

```
original/        The scanned source PDFs (the starting assets).
transcription/   Text/source recovered from the scans.
  hearts-core.lisp        InterLisp-D core (Administrator, Clown, Conservative, Human, UI, net).
  kee-expert-player.txt   Expert Player — mostly Interlisp EP.* source (+ a spliced rules page).
  kee-expert-rules.txt    Expert Player — the KEE production rules (the spec to reimplement).
  parts/                  Per-page-range transcription chunks (pre-assembly).
  TRANSCRIPTION-NOTES.md  Conventions (fidelity-first; `←` = ASCII `_` for Medley).
medley/          Phase 2 — running the core on the Medley Interlisp emulator (interlisp.org).
  MEDLEY-SETUP-NOTES.md   Install/loading notes, and what breaks (networking, KEE).
modern-lisp/     Phase 3 — a modern Common Lisp port (planned).
python/          Phase 4 — a Python port for distribution (planned).
```

**Status (2026-08):** Phase 0 — the six scanned documents have been transcribed back to text.
The core listing is faithful InterLisp-D; the Expert Player turned out to be largely plain
Interlisp (`EP.*`) plus a set of KEE rules. **KEE itself is proprietary and unavailable in
Medley**, so the expert player's rules will be reimplemented rather than loaded. Next up:
assemble/verify the core and attempt a load in Medley (see `medley/MEDLEY-SETUP-NOTES.md`).
