# Transcription conventions

Transcribing the scanned InterLisp-D listings in `../original/` back into loadable source.
Goal: a faithful, paren-balanced reproduction that can eventually be read by Medley Interlisp.

## Conventions
- **Fidelity first.** Reproduce the code exactly as printed, including function/variable
  names, capitalization, and structure. Do not "modernize" or fix apparent bugs during
  transcription — corrections happen later, tracked separately.
- **Assignment arrow.** The Interlisp left-arrow assignment is transcribed as `←` (U+2190)
  in the human-readable master (matches the printed glyph, reads well in an editor).
  **Medley note:** `←` is only the *display glyph* for ASCII underscore `_` (code 95); `_` is
  the byte the CLISP reader treats as assignment, and whether a literal U+2190 folds back to
  the operator is undocumented. So the Medley-loadable copy is generated from the master by a
  single global `←`→`_` substitution (verified by actually loading in Medley in Phase 2).
  Underscore is safe as a 1:1 swap because 1980s Interlisp did not use `_` inside symbol names.
- **Escape char `%`.** Preserved as printed — `%` escapes the next char in Interlisp
  (e.g. `SLOAN% SCHOOL` = the literal `SLOAN SCHOOL` with an escaped space).
- **Page markers.** Each scanned page begins with a `;; ==== page N ====` comment so text
  can be cross-checked against the PDF. These are transcription aids, not part of the
  original source.
- **Uncertain reads.** Anything not confidently legible is marked `#| ?? ... |#` inline
  with a short note, never silently guessed.
- **Verification.** After each file, parens are balanced-checked and the COMS (file
  table-of-contents) is reconciled against the actual FNS/RECORDS/VARS definitions.

## Status
- [x] hearts-core.lisp       (47 pp) — assembled from `parts/core-p*.lisp`
- [x] kee-expert-player.txt  (13 pp) — mostly Interlisp `EP.*` source (+ one spliced rules page)
- [x] kee-expert-rules.txt   (18 pp) — the KEE production rules
- [ ] docs/ prose (overview, harley-report, ramana-report) — not yet transcribed to Markdown

Transcription done by parallel subagents (one per page-range), one page (core 43–47, the
`READBITMAP` "Random Cruff" block) done directly. Only **6 uncertain-character markers**
(`#| ?? |#`) across all 78 scanned pages; the packed bitmap literals are best-effort and
flagged for visual re-verification in Medley.

## Balance / structure check
`tools/interlisp-balance.py hearts-core.lisp` — a rough Interlisp-aware paren/bracket checker
(super-bracket `]` semantics, `%` escape, strings, comments). The core nets to zero open
groups; round parens are net-open (closed by `]` super-brackets) and there are 4 net-extra
`]` — all legitimate "close-to-top" brackets at definition/`DEFINEQ` ends, verified by eye.
**Authoritative validation is loading in Medley (Phase 2), not this script.**

## Recovered facts (for Phase 2 planning)
- **KEE coupling is tiny:** the core calls KEE only at 4 `UNITMSG`/`UNITMSG*` seams to the
  `expert.players` unit. Administrator + Clown + Conservative + Human are KEE-free, so the
  core runs on Medley once those 4 expert-player seams are stubbed/replaced.
- **Networking** (`EVALSERVER`/`HNET`/`NetHearts`, ~50 lines) is the Phase-2 casualty — collapse
  to one image with four `ADD.PROCESS` players.
- 102 `←` assignment arrows in the core.
