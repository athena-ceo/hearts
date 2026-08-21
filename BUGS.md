# Bug & issue tracker — HEARTS revival

Running list of everything we've hit, so nothing gets lost — kept for the InterLisp-D
community. Grouped by *whose* problem it is. See `REVIVAL-LOG.md` for the narrative.

## Medley / Maiko (upstream — candidates to report/PR once confirmed)

| # | Status | Issue |
|---|---|---|
| M1 | **open, workaround** | The `CLIPBOARD` library picks `pbpaste`/`pbcopy` vs `xclip` by testing `getenv("OSTYPE")` for "darwin", but the `medley` launcher never exports `OSTYPE` (a non-exported shell var) → host clipboard silently no-ops on macOS. Workaround: export `OSTYPE=darwin` before launch (done in `medley/run-load.sh`). *Not a clean PR on its own — see M2.* |
| M2 | **open** | Even with `OSTYPE` set, `(GETCLIPBOARD)` faults: `CREATE-PROCESS-STREAM "pbpaste"` returns NIL — subprocess spawning appears non-functional on this SDL/Maiko build → `SETFILEINFO` on a NIL stream. Host clipboard is effectively unavailable on the SDL backend. Workaround: file-load (`(LOAD 'X)`). |
| M3 | **open** | SEdit wedges the image on this SDL build every time it's opened (hangs at/after "Select region for SEdit window"). Workaround: don't use SEdit; recover with `⌃D` (RESET) or relaunch. |
| M4 | note | `--vnc` headless display is explicitly unavailable on macOS; SDL (`--maikoprog ldesdl`) is the no-XQuartz path but needs SDL2.framework + an `install_name_tool` rpath fix + ad-hoc re-sign (DYLD_* is stripped through `/bin/bash`). |
| M5 | note (not a bug) | `INVERTREGION` exists in Medley's sources (`TWODINSPECTOR`) but is **not loaded** in the apps sysout, so calling it faults. Use core `(DSPFILL region BLACKSHADE 'INVERT dsp)` instead. Good reminder that "in the sources" ≠ "in the running image". |

## Lost image-definitions (things the 1986 running image had that the *listing* doesn't)

A residential Lisp image accumulates definitions that a file dump never captures. These
were referenced by the recovered code but defined nowhere in it — reconstructed as revival
patches in `medley/build-loadfile.py`. **This is the single strongest argument against
image-as-source-of-truth**, and why a scanned listing isn't a complete program.

| # | Status | Issue |
|---|---|---|
| L1 | **fixed (patch)** | `ClownNames` — `CLOWN.Create` picks a random clown name from it; undefined, and not in the file COMS (unlike the parallel `ConservativeNames`). Supplied an invented list. |
| L2 | **fixed (patch)** | `Card.PrintCard` — called ~8× (thought windows, help strings) but never defined; only the compact `Card.Print` ("KS") is in the file. Supplied a readable version ("King of Spades"). |

## HEARTS — original 1986 bugs (kept faithful in the transcription; fixed in the running build)

| # | Status | Issue |
|---|---|---|
| H1 | **fixed (CLOWN), open (HP)** | `CLOWN.Play` and `HP.Play` call `H.GetLegals` without the `FirstTrick?` arg the trick loop passes, so the 2♣ opening-lead rule never fired for them (`CP.Play` does it right). `CLOWN.Play` fixed via revival patch; `HP.Play` still needs the same fix. |
| H2 | **fixed (build)** | `HP.Menuer` calls `PromptPrint` (mixed case) in 3 places, but the function is the system `PROMPTPRINT` (all caps) — Interlisp is case-sensitive, so DWIM prompts to correct at runtime. Corrected in the build (`PromptPrint → PROMPTPRINT`); the faithful transcription keeps the original casing. |

## Missing 1986 dependencies (not in modern Medley)

| # | Status | Issue |
|---|---|---|
| D1 | **reimplemented** | `ACTIVEREGIONS` (INTERMEZZO LispUsers lib) — clickable/highlightable window regions. Not in modern Medley; `REGIONMANAGER`/`AIREGIONS`/`ARMODES` don't match the API. **We wrote our own: `medley/activeregions.lisp`** (record + `SETACTIVEREGIONS`/`GETPICKREGION`/`DEFAULTHIGHLIGHTFN`/`DOLOWLIGHT`, on the window `BUTTONEVENTFN`). Highlight path verified via the trick-winner flash; human card-clicking still to be play-tested. Could become a lispusers contribution. |
| D2 | deferred | `KEE` (IntelliCorp) — the Expert player. Proprietary, gone. ~90 rules to reimplement (post non-KEE). |
| D3 | deferred | `EVALSERVER` / Ethernet networking — dead PUP/XNS. Collapse the 4-machine design into one image with 4 processes. |

## Display / UI

| # | Status | Issue |
|---|---|---|
| U1 | **fixed** | Card-table `S:/T:` (score/tricks) smeared — `CT.PrintStats` redrew without erasing, so changing-width digits overlapped (bogus "T: 31"). Now clears each field with a `WHITESHADE` fill first. |
| U2 | **open** | The outer `(bind … do (Hearts …))` game loop calls `CT.Open` each game, stacking a **new card-table window per game** (and thought windows per Conservative). Cosmetic/resource leak; harmless but messy. Consider reusing one card table, or `⌃E` to stop after a game. |

## Fixed transcription (OCR) errors — historical, resolved

Each verified against a 300-DPI scan crop and fixed in `transcription/parts/`. Two flavors:
**super-bracket `[`↔`(` confusion**, and **balanced-but-semantically-wrong** parens (a paren
in the wrong place that still balances, so the linter can't see it — only runtime does):

- `H.Setup` (×2), `HNET.Hello`, `Hand.RemoveCard`, `Dealer.Menuer`, `HP.Menuer`, `HP.PassOut`
  (super-bracket slips, caught by the linter).
- `H.PlayGame` — dropped the CLISP keyword `as` (only runtime caught it — bracket linters can't
  see a missing word).
- `H.Deal` — a stray `)` closed the deal `bind` one form early, so the collected `Hand` fell
  outside the loop and read unbound (balanced, so linter-invisible; runtime-only).
- `HP.Create` — `[((Name …` had one paren too many, nesting the `LET` binding so the *variable*
  became the list `(Name …)` → "is not a SYMBOL" at runtime (balanced; runtime-only).
