# Medley / Maiko issues found while reviving HEARTS

Issues we hit in **modern Medley Interlisp** (the Maiko VM + the macOS/SDL build) while
bringing a 1986 InterLisp-D application back to life. Recorded and shared for the
Interlisp-D community — these are candidates to report or PR upstream, not problems with
HEARTS itself. (HEARTS's own bugs live in [HEARTS-BUGS.md](HEARTS-BUGS.md).)

Environment: Medley on macOS (Darwin 25.x), SDL backend (`--maikoprog ldesdl`), no XQuartz.

| # | Status | Issue |
|---|--------|-------|
| M1 | **open, workaround** | The `CLIPBOARD` library picks `pbpaste`/`pbcopy` vs `xclip` by testing `getenv("OSTYPE")` for "darwin", but the `medley` launcher never exports `OSTYPE` (a non-exported shell var) → host clipboard silently no-ops on macOS. Workaround: export `OSTYPE=darwin` before launch. *Not a clean PR on its own — see M2.* |
| M2 | **open** | Even with `OSTYPE` set, `(GETCLIPBOARD)` faults: `CREATE-PROCESS-STREAM "pbpaste"` returns NIL — subprocess spawning appears non-functional on this SDL/Maiko build → `SETFILEINFO` on a NIL stream. Host clipboard is effectively unavailable on the SDL backend. Workaround: file-load (`(LOAD 'X)`) instead of paste. |
| M3 | **open** | SEdit wedges the image on this SDL build every time it is opened (hangs at/after "Select region for SEdit window"). Workaround: don't use SEdit; recover with `⌃D` (RESET) or relaunch. |
| M4 | note | `--vnc` headless display is explicitly unavailable on macOS; SDL (`--maikoprog ldesdl`) is the no-XQuartz path but needs `SDL2.framework` + an `install_name_tool` rpath fix + an ad-hoc re-sign (DYLD_* is stripped through `/bin/bash`). Documenting the exact recipe would help other macOS users. |
| M5 | note (not a bug) | `INVERTREGION` exists in Medley's sources (`TWODINSPECTOR`) but is **not loaded** in the apps sysout, so calling it faults. Use core `(DSPFILL region BLACKSHADE 'INVERT dsp)` instead. A good reminder that "in the sources" ≠ "in the running image". |

See [REVIVAL-LOG.md](REVIVAL-LOG.md) for the narrative behind each of these.
