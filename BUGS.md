# Bug & issue tracker — HEARTS revival

Running list of everything we've hit, so nothing gets lost. Grouped by *whose* bug it is.
Newest discoveries near the top of each section. See `REVIVAL-LOG.md` for the narrative.

## Medley / Maiko (upstream — candidates to report/PR once confirmed)

| # | Status | Issue |
|---|---|---|
| M1 | **open, workaround** | `CLIPBOARD` library picks `pbpaste`/`pbcopy` vs `xclip` by testing `getenv("OSTYPE")` for "darwin", but the `medley` launcher never exports `OSTYPE` (it's a non-exported shell var) → host clipboard silently no-ops on macOS. Workaround: export `OSTYPE=darwin` before launch (done in `medley/run-load.sh`). *Not yet a clean PR — see M2.* |
| M2 | **open** | Even with `OSTYPE` set, `(GETCLIPBOARD)` faults: `CREATE-PROCESS-STREAM "pbpaste"` returns NIL (subprocess spawning appears non-functional on this SDL/Maiko build) → `SETFILEINFO` on a NIL stream. Host clipboard is effectively unavailable on the SDL backend. Workaround: file-load (`(LOAD 'X)`). |
| M3 | **open** | SEdit wedges the image on this SDL build every time it's opened (hangs at/after "Select region for SEdit window"). Workaround: don't use SEdit; recover with `⌃D` (RESET) or relaunch. |
| M4 | note | `--vnc` headless display is explicitly unavailable on macOS; SDL (`--maikoprog ldesdl`) is the no-XQuartz path but needs SDL2.framework + an `install_name_tool` rpath fix + ad-hoc re-sign (DYLD_* is stripped through `/bin/bash`). |

## HEARTS — original 1986 bugs (kept in the faithful transcription; fixed in the running build)

| # | Status | Issue |
|---|---|---|
| H1 | **fixed (CLOWN), open (HP)** | `CLOWN.Play` and `HP.Play` call `H.GetLegals` without the `FirstTrick?` arg the trick loop passes, so the 2♣ opening-lead rule never fired for them (`CP.Play` does it right). `CLOWN.Play` fixed via revival patch in `build-loadfile.py`; `HP.Play` still needs the same fix. |

## Missing 1986 dependencies (not in modern Medley)

| # | Status | Issue |
|---|---|---|
| D1 | **stubbed** | `ACTIVEREGIONS` (INTERMEZZO LispUsers lib) — clickable/highlightable window regions. Not in modern Medley; APIs of `REGIONMANAGER`/`AIREGIONS`/`ARMODES` don't match. No-op stubs let a Clown game run, but the **human player needs real active regions to click cards** — reimplement on the window `BUTTONEVENTFN` or adapt `REGIONMANAGER`. |
| D2 | deferred | `KEE` (IntelliCorp) — the Expert player. Proprietary, gone. ~90 rules to reimplement (post non-KEE). |
| D3 | deferred | `EVALSERVER` / Ethernet networking — dead PUP/XNS. Collapse the 4-machine design into one image with 4 processes. |

## Display / UI polish (open — needs pinning down)

| # | Status | Issue |
|---|---|---|
| U1 | **open** | Card-table display issues observed during Clown play (to be specified + fixed). Winning-trick highlight is currently absent because `ACTIVEREGIONS/DEFAULTHIGHLIGHTFN` is a no-op stub (D1). |

## Fixed transcription (OCR) errors — historical, resolved

Super-bracket / paren OCR slips, each verified against a 300-DPI scan crop and fixed in
`transcription/parts/`: `H.Setup` (×2), `HNET.Hello`, `Hand.RemoveCard`, `Dealer.Menuer`,
`HP.Menuer`, `HP.PassOut`, `H.PlayGame` (dropped `as`), `H.Deal` (stray `)` closing the deal
`bind` early). Plus the missing `ClownNames` variable (supplied as a revival patch).
