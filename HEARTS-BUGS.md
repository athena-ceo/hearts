# HEARTS — bug & issue tracker

Bugs in HEARTS itself: original 1986 bugs rediscovered during the revival, definitions the
running image had but the listing didn't, missing 1986 dependencies, display/UI glitches, and
resolved transcription (OCR) errors. Kept so nothing gets lost. See [REVIVAL-LOG.md](REVIVAL-LOG.md)
for the narrative.

Issues with **Medley/Maiko itself** (not HEARTS) are tracked separately for the community in
[MEDLEY-ISSUES.md](MEDLEY-ISSUES.md).

## Original 1986 bugs (kept faithful in the transcription; fixed in the running build)

| # | Status | Issue |
|---|--------|-------|
| H1 | **fixed (CLOWN), open (HP)** | `CLOWN.Play` and `HP.Play` call `H.GetLegals` without the `FirstTrick?` arg the trick loop passes, so the 2♣ opening-lead rule never fired for them (`CP.Play` does it right). `CLOWN.Play` fixed via revival patch; `HP.Play` still needs the same fix. |
| H2 | **fixed (build)** | `HP.Menuer` calls `PromptPrint` (mixed case) in 3 places, but the function is the system `PROMPTPRINT` (all caps) — Interlisp is case-sensitive, so DWIM prompts to correct at runtime. Corrected in the build (`PromptPrint → PROMPTPRINT`); the faithful transcription keeps the original casing. |

## Lost image-definitions (things the 1986 running image had that the *listing* doesn't)

A residential Lisp image accumulates definitions that a file dump never captures. These were
referenced by the recovered code but defined nowhere in it — reconstructed as revival patches in
`medley/build-loadfile.py`. **This is the single strongest argument against
image-as-source-of-truth**, and why a scanned listing isn't a complete program.

| # | Status | Issue |
|---|--------|-------|
| L1 | **fixed (patch)** | `ClownNames` — `CLOWN.Create` picks a random clown name from it; undefined, and not in the file COMS (unlike the parallel `ConservativeNames`). Supplied an invented list. |
| L2 | **fixed (patch)** | `Card.PrintCard` — called ~8× (thought windows, help strings) but never defined; only the compact `Card.Print` ("KS") is in the file. Supplied a readable version ("King of Spades"). |

## Missing 1986 dependencies (not in modern Medley)

| # | Status | Issue |
|---|--------|-------|
| D1 | **reimplemented** | `ACTIVEREGIONS` (INTERMEZZO LispUsers lib) — clickable/highlightable window regions. Not in modern Medley; `REGIONMANAGER`/`AIREGIONS`/`ARMODES` don't match the API. **We wrote our own: `medley/activeregions.lisp`** (record + `SETACTIVEREGIONS`/`GETPICKREGION`/`DEFAULTHIGHLIGHTFN`/`DOLOWLIGHT`, on the window `BUTTONEVENTFN`). Verified via human card-clicking in a full game. Being packaged as a standalone lispusers module for the community. |
| D2 | deferred | `KEE` (IntelliCorp) — the Expert player. Proprietary, gone. ~90 rules to reimplement (post non-KEE). |
| D3 | deferred | `EVALSERVER` / Ethernet networking — dead PUP/XNS. Collapse the 4-machine design into one image with 4 processes. |

## Display / UI

| # | Status | Issue |
|---|--------|-------|
| U1 | **fixed** | Card-table `S:/T:` (score/tricks) smeared — `CT.PrintStats` redrew without erasing, so changing-width digits overlapped (bogus "T: 31"). Now clears each field with a `WHITESHADE` fill first. |
| U2 | **open** | The outer `(bind … do (Hearts …))` game loop calls `CT.Open` each game, stacking a **new card-table window per game** (and thought windows per Conservative). Cosmetic/resource leak; harmless but messy. Consider reusing one card table, or `⌃E` to stop after a game. |
| U3 | **fixed (build)** | Human hand window was created 245px tall (`GETBOXREGION 300 245`), but the option menu (Play/Pass/Score/LegalCards) is `ATTACHWINDOW`'d to its `TOP`. Card rows are pinned to the window *bottom* (Clubs top row at y=176–221, only ~24px from the top edge), so the attached menu hid the Clubs label and card bodies. Grew the window to 300px — extra height lands above the top row, giving Clubs ~79px of clearance. Scoped to `HP.CreateWindow` (Open/Dealer windows use the same box but have no attached top menu). |

## Fixed transcription (OCR) errors — historical, resolved

Each verified against a 300-DPI scan crop and fixed in `transcription/parts/`. Two flavors:
**super-bracket `[`↔`(` confusion**, and **balanced-but-semantically-wrong** parens (a paren in the
wrong place that still balances, so the linter can't see it — only runtime does):

- `H.Setup` (×2), `HNET.Hello`, `Hand.RemoveCard`, `Dealer.Menuer`, `HP.Menuer`, `HP.PassOut`
  (super-bracket slips, caught by the linter).
- `H.PlayGame` — dropped the CLISP keyword `as` (only runtime caught it — bracket linters can't
  see a missing word).
- `H.Deal` — a stray `)` closed the deal `bind` one form early, so the collected `Hand` fell
  outside the loop and read unbound (balanced, so linter-invisible; runtime-only).
- `HP.Create` — `[((Name …` had one paren too many, nesting the `LET` binding so the *variable*
  became the list `(Name …)` → "is not a SYMBOL" at runtime (balanced; runtime-only).
