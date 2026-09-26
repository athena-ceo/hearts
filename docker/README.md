# Headless Medley for testing

A Docker image that runs Medley Interlisp (Maiko + the 260810 release) against a virtual X
display (Xvfb), so Interlisp can be driven from a script: evaluate forms, capture their values
and errors, take screenshots, and exit. It's how the KEE Expert Player was brought up and how
its tests run. Nothing about it is HEARTS-specific.

## Use

```bash
tools/medley-headless --build                       # build the image (first time / after edits here)
tools/medley-headless tests/smoke.lisp              # run a script
tools/medley-headless --loops tests/expert-game.lisp  # ...with LOOPS loaded first
tests/run-all.sh                                    # the whole HEARTS suite, in parallel
```

Results land in `out/medley/`: `transcript.txt` (each form, then `= value` or `ERROR: ...`),
`dribble.txt` (everything printed to the Lisp terminal), and any screenshots. The transcript is
also printed. Exit status: 0 all good, 1 a `FAIL`/`ERROR` line, 2 timeout (the screen at that
moment is saved as `timeout.png` — usually a prompt or break window waiting for a human).

Options (`medley-run --help`): `--loops`, `--timeout SECS` (default 300), `--out DIR`,
`--geometry WxH`, and `--shell` for a bash prompt inside the container.

## Scripts

A script is a file of Interlisp forms, read with the Interlisp readtable in the INTERLISP
package and evaluated in an Interlisp exec. Errors are trapped per form (no break windows).
Helpers from [harness.lisp](harness.lisp):

| Form | Does |
|---|---|
| `(HT.CHECK "label" form [expected])` | `PASS`/`FAIL` line: form non-NIL, or `EQUAL` to expected |
| `(HT.SNAP "name")` | screenshot the virtual display to `out/medley/name.png` |
| `(HT.LOG x)` | write a line to the transcript |
| `(HT.AUTOPLACE)` | answer `GETBOXREGION`/`GETREGION` placement prompts automatically |

The repo is mounted at `/hearts`, so files are loaded as e.g. `(LOAD "{DSK}/hearts/medley/EXPERT")`.

## How it works (and the traps it avoids)

- The image installs the Medley "full" release tarball (Maiko + sysouts) for the container's
  architecture, and [Interlisp/loops](https://github.com/Interlisp/loops) at a pinned commit.
- [medley-run](medley-run) starts Xvfb, then `medley -a` with a REM.CM. **Medley honours
  REM.CM only if it starts with a double quote** (the string is stuffed into the exec's
  type-ahead; see `sources/ADIR`). So the REM.CM is a one-line quoted string and the real
  parameters travel in environment variables — **without underscores**, which didn't survive
  `UNIX-GETENV`.
- The REM.CM types `(EXEC_INTERLISP)` first (what `medley -e` does, which is why `-e` can't be
  combined with our REM.CM) so scripts run in an Interlisp exec. Header-less files like HEARTS
  are read in the exec's environment; in an XCL exec their `(* ...)` comments become CL
  multiplication.
- `PAGEFULLFN` is advised to return (as Medley's own loadup scripts do): a full exec window
  otherwise waits for a keypress.
- The transcript is appended and closed on every write; a killed Medley doesn't flush open
  streams.
- `DEFINE-FILE-INFO` keys must be keywords (`:PACKAGE`), and the XCL condition macro is
  `XCL:CONDITION-CASE` (Medley's CL has no `HANDLER-CASE`).
- LOOPS drops into interactive prompts on some mistakes (an unknown IV, some class-browsing
  messages); in a headless run those show up as a timeout plus `timeout.png`.
