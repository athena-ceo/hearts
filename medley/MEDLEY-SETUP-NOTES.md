# Reviving HEARTS (1986 Interlisp-D / Xerox Dandelion) on Medley Interlisp

Research notes for LOADing a transcribed 1986 InterLisp-D source file into the
modern **Medley Interlisp** emulator on macOS (Apple Silicon).
Research only — nothing installed or changed. Sources listed at the end.

> Confidence flags used below: **[confirmed]** = stated in Interlisp/Medley docs
> or repo; **[strong]** = follows directly from how Interlisp-D/Medley works but
> not quoted verbatim from a single page; **[verify in-image]** = should be
> checked by actually loading the file, because the docs did not give a
> definitive answer.

---

## 1. Install & run Medley on macOS (Apple Silicon)

**Supported install methods today**

- **Prebuilt release (recommended, and the only method the macOS page documents).**
  Download the latest `medley-full-macos-universal-*.zip` from the downloads
  page. It is a **universal binary** (one zip works on both Apple Silicon and
  Intel), so no Rosetta and no build needed. **[confirmed]**
- **Build from source** (git clone `Interlisp/medley` + `Interlisp/maiko` and
  build the `maiko` VM). Documented but only needed for development, not for
  running a program. **[confirmed]**
- **Docker** exists in the project (there is a one-step Docker installer for
  *Windows*), but the macOS install page does **not** document a Docker path —
  on macOS the native universal zip is the intended route. **[confirmed]**
- **Web / "Medley Online"** — a hosted browser version exists for trying Medley,
  but for loading your own files you want a local install. **[confirmed]**

**Prerequisites on macOS**

- **XQuartz** (X11 server) must be installed; first launch spends ~10–15 s
  starting XQuartz. (A `--vnc` display path also exists, mainly for WSL.) **[confirmed]**
- **Gatekeeper quarantine** must be cleared on the VM binaries, e.g.:
  ```
  xattr -d com.apple.quarantine <path>/maiko/darwin.universal/lde*
  ```
  **[confirmed]**

**Launch + get an Interlisp exec**

```
cd <path-to>/medley_folder/medley
./medley --apps --interlisp --noscroll
# shorthand:
./medley -a -e -n
```

- `--apps` / `-a` — boot the **apps** sysout (full dev tools: File Manager,
  TEdit, Notecards, CLOS, etc.). Good base for old code.
- `--interlisp` / `-e` — make the **initial Exec an Interlisp Exec** (the classic
  `_` prompt / CLISP world) instead of the default Common Lisp Exec. **This
  matters** — your file is Interlisp, not Common Lisp. Note `-e` only takes
  effect together with `--apps`. **[confirmed]**
- `--noscroll` / `-n` — scroll-bar behavior.
- `--full` / `-f` — full dev sysout without the extra apps; `--lisp` / `-l` —
  minimal core only.
- `--sysout FILE` / `-y` — load a specific sysout; `--id` / `-i` — session id
  (use a unique id to run several images at once — relevant for multi-player, see §6).
- Startup file hooks: `--greet FILE`, `--rem.cm FILE` (a command file Medley
  reads/executes at startup, *after* greet files). You can use `--rem.cm` to
  auto-`LOAD` your source at boot. **[confirmed]**
- Exit the image with `(IL:LOGOUT)` at the Exec. **[confirmed]**

You'll get the Interlisp Exec window inside the Medley X/VNC display; type Lisp
there.

---

## 1a. Smooth macOS / X11 daily setup (verified on the 2026 build, 260810)

**Platform note:** everything in this section is **macOS-specific** (Apple Silicon or
Intel). The in-Lisp steps (§2 onward — `FILESLOAD`, `LHearts`, etc.) are identical on
every platform; only the install/launch/quit shell mechanics below differ per-OS. Linux
and Windows/WSL users: see [interlisp.org](https://interlisp.org/) for their install.

We hit a run of small friction points bringing HEARTS up on a current Medley; here's the
setup that makes it painless. Backhistory and root-causes are in
[../MEDLEY-ISSUES.md](../MEDLEY-ISSUES.md).

**Display backend — use X11, not SDL, for the full experience.** The SDL backend
(`--maikoprog ldesdl`) renders in a native macOS window with no XQuartz, and the
mouse-driven game plays fine on it — but on the current build it has **no host clipboard**
(the `unixcomm` helper is only forked by the X11 kickstarter — see MEDLEY-ISSUES M2) and
an **incomplete keyboard map** (M8). The default **X11** path (`lde` → `ldex`, needs
XQuartz) forks the helper and has the mature keyboard map, so clipboard, keys, and SEdit
all work. Recommended: X11.

1. **Install under a space-free path.** The launcher and `maiko/bin/{osversion,machinetype}`
   don't quote paths, so a directory with a space (e.g. `~/Documents/MBP Docs/…`) fails with
   `No such file or directory` / "cannot find the Maiko executable" (MEDLEY-ISSUES M7). Put
   Medley somewhere like `~/medley-260810`.

2. **Stop XQuartz's startup xterm** (once): XQuartz runs `/opt/X11/bin/xterm` on launch by
   default; point that at a no-op, then restart XQuartz:
   ```bash
   defaults write org.xquartz.X11 app_to_run /usr/bin/true
   ```

3. **Leave the X server running.** XQuartz doesn't auto-quit when its last client exits, so
   start it once (`open -a XQuartz`) and leave it. To have it up after every reboot, add
   XQuartz to **System Settings → General → Login Items**.

4. **Set two env vars once** (in `~/.zshrc`) so launches are turnkey:
   ```bash
   export OSTYPE=darwin                         # so the CLIPBOARD lib picks pbpaste (MEDLEY-ISSUES M1)
   export LDEREMCM="$HOME/il/medley-startup.cm" # a startup command file, auto-run each launch
   ```

5. **Auto-load libraries at startup** via that command file (`--rem.cm`, run after the sysout
   is up). Keep it to a single form (older Medley rem.cm reliably runs only the first).
   `~/il/medley-startup.cm`:
   ```
   (FILESLOAD CLIPBOARD)
   ```
   Widen it once you've confirmed the files load clean, e.g.:
   ```
   (FILESLOAD CLIPBOARD ACTIVEREGIONS HEARTS)
   ```
   (The revival build already defaults `ThinkFlag?` to `T`, so the Conservatives narrate without
   any extra form; `(SETQ ThinkFlag? NIL)` if you'd rather they didn't.)

6. **Launch** (X11; XQuartz already running from step 3):
   ```bash
   cd ~/medley-260810/medley && ./medley --apps --interlisp --noscroll
   ```
   With steps 4–5 done, this comes up with `CLIPBOARD` (and whatever else) already loaded.

7. **Quit cleanly** — at the Exec:
   ```
   (LOGOUT)
   ```
   This exits Medley but leaves XQuartz running for next time. If the image is **wedged** and
   you can't type, kill just Medley from a terminal (the X11 binary is `ldex`):
   ```bash
   pkill ldex
   ```

> **Careful with startup auto-loads:** if a file in the rem.cm *errors* mid-load, you land in
> a break at startup with the loader's reader-environment still active (so `FILESLOAD` looks
> undefined — MEDLEY-ISSUES M9). Only auto-load files you've confirmed load cleanly; recover by
> unwinding the break to top level, or relaunch.

---

## 2. Loading old source into Medley

Interlisp's unit of code is the **symbolic file** managed by the **File Manager**
(historically "the filepkg"). Key facts for your case:

- **`LOAD`** reads and evaluates a symbolic (source) file: `(LOAD 'HEARTS)` or
  `(LOAD "HEARTS")`. Variants: **`LOADFROM`** (load definitions but mark the file
  as the source of record for editing), and **`FILESLOAD`** (load one or more
  files, preferring a compiled `.DFASL` if present, else source). **[confirmed]**
- Your file is a **prettyprint symbolic listing** — it *is* the native Interlisp
  source format: it begins with `(FILECREATED ...)`, then `(PRETTYCOMPRINT ...)`,
  `(RPAQQ HEARTSCOMS (...))` (the file's COMS/table of contents), then the
  `(DEFINEQ ...)`, `(RECORDS ...)`, `(RPAQQ/RPAQ ...)` blocks that the COMS name.
  When you `LOAD` it, `FILECREATED`/`RPAQQ HEARTSCOMS`/`DEFINEQ` are just forms
  that get evaluated and register everything with the File Manager. So a
  correctly transcribed listing loads **as-is** — there is no separate
  "importer" needed. **[strong]**
- **Does Medley read plain-text `.lisp` files?** Yes — a symbolic Interlisp file
  is a text file (historically in XCCS with CR line-ends). Medley now has UTF-8
  I/O (see §3/§8), so a UTF-8 text transcription can be read. There is **no
  requirement** that the file be in a binary Xerox container; the classic format
  *is* text. **[strong]**  Caveat: **`.tedit`** files are TEdit documents with
  binary formatting/looks properties — that is *not* what you want for source;
  keep the transcription as a plain code file. **[strong]**
- After loading/editing, **`(MAKEFILE 'HEARTS)`** writes the file back out (the
  File Manager regenerates the prettyprinted listing, updates `FILECREATED`,
  compiles if asked). This is how you'd re-save a cleaned-up version. **[confirmed]**
- Practical import tip seen in the community for bringing outside text into
  Medley: land the file where the image can see it (the Medley file system / a
  mounted host dir), then `LOAD`/`FILESLOAD` it. TextModule/`FILESLOAD` workflows
  are used for pulling in external Common Lisp text; the same file-visibility
  concern applies to Interlisp source. **[strong]**

**Recommended first attempt:** boot with `-a -e`, get the file visible to the
image, `(LOAD 'HEARTS)`, and watch for reader errors (they'll point at
transcription problems — see §3, §4, §8).

---

## 3. The `←` assignment arrow — what byte to use

Background: In Interlisp/CLISP the assignment operator is historically the
character **underscore, ASCII/`CHARCODE` 95 (0x5F)**. On Xerox displays and in
prettyprint *listings* that same character was drawn with a **left-arrow glyph
`←`**. So the `←` you see in the 1986 scan and the `_` you type are the **same
underlying character** — `←` is the glyph, `_` (0x5F) is the code. The reader's
CLISP infix assignment (`x_(foo)` / shown as `x ←(foo)`) is triggered by that
code-95 character. **[strong]**

Practical guidance for the UTF-8 transcription:

- **Safest choice: transcribe each listing `←` as an ASCII underscore `_`
  (0x5F).** That is the byte the classic reader unambiguously treats as
  assignment, independent of Unicode mapping. `x_(foo)` will parse as "assign
  `(foo)` to `x`". **[strong] / [verify in-image]**
- **U+2190 `←` (UTF-8 `E2 86 90`)**: Medley's Unicode/XCCS layer has mapping
  tables between XCCS codes and Unicode, and the display font shows assignment as
  `←`. Whether the *reader*, on a UTF-8 input stream, folds a literal U+2190 back
  to the assignment operator depends on those readtable/encoding mappings and is
  **not something the public docs state definitively** — so do not assume a raw
  U+2190 byte will assign. **[verify in-image]**
- **Recommendation:** do the transcription with `_` for every assignment arrow,
  confirm one assignment loads and behaves (`(EDITF ...)` / evaluate a function
  that uses it), and only consider literal `←` if you deliberately test that the
  reader accepts it. Beware: an underscore that is genuinely part of an *atom
  name* would need `%` escaping (see §4) — but 1980s Interlisp code rarely uses
  `_` inside identifiers precisely because it means assignment.

---

## 4. `%` escape, `[ ]` super-brackets, `(* …)` comments

All three are core Interlisp reader conventions and remain in force in Medley
(same reader, same CLISP). **[confirmed for the conventions; [strong] that Medley’s reader is unchanged]**

- **`%` escape** — `%` before a delimiter (space, paren, bracket, `_`, etc.)
  makes it a literal constituent of the atom rather than a delimiter. Transcribe
  every `%` in the scan literally; dropping one will silently change tokenizing.
  **[confirmed]**
- **`[ ]` super-brackets** — `[` opens like `(`, but `]` closes **all** open
  parens back to the matching `[` (or the whole expression). Interlisp prettyprint
  emits these heavily. Keep them exactly; do not "normalize" them to parens
  unless you also rebalance, or you'll change structure. **[confirmed]**
- **`(* … )` comments** — In Interlisp a comment is the form `(* comment text)`;
  the `*` is bound (as a function/CLISP hook) so the reader/evaluator discards it.
  Prettyprint shows comments to the right and can render them as `** COMMENT **`.
  These load fine. Watch two transcription hazards: (a) a `)` or bracket *inside*
  comment prose must be handled the way the original did (comments run to their
  closing paren), and (b) OCR turning `(*` into `( *` or vice-versa. **[confirmed]**

---

## 5. Windowing & processes

The Interlisp-D **window system and the process/monitor machinery are part of
Medley itself** — Medley *is* Interlisp-D re-hosted, and the residential
environment (windows, menus, TEdit, SEdit/DEdit, the File Manager) runs on
exactly these facilities. So the primitives your program uses are present and
working: **[strong]**

- **Window system:** `WINDOWPROP`, `CREATEW`, `MENU`/`ADDMENU`, bitmaps
  (`BITMAP`/`BITBLT`), `ACTIVEREGIONS` — all standard IRM Volume II facilities,
  still the same API. **[strong]**
- **Processes:** the **process package** (`ADD.PROCESS`, `THIS.PROCESS`,
  `WAKE.PROCESS`, etc.) and synchronization (`MONITORLOCK`, `WITH.MONITOR`,
  `MONITOR.AWAIT.EVENT`) are core and available. **[strong]**

Caveat: exact **pixel/geometry and event timing** differ (Medley runs in an X11
or VNC window at modern resolutions, not a 1024×808 Dandelion display), so
hard-coded screen coordinates, `DSPFONT` assumptions, or region sizes may need
tuning, but the calls themselves resolve. **[strong] / [verify in-image]**

---

## 6. Networking: the Ethernet `EVALSERVER` / `ETHERHOSTNUMBER` layer

This is the area most likely to **not** survive as-is.

- Historically Interlisp-D networked over **PUP** and **XNS** (Xerox's
  pre-TCP/IP Ethernet stacks). `ETHERHOSTNUMBER`, the NS/PUP layers, and a
  remote-eval "EVALSERVER" sat on top of those. **[confirmed background]**
- In modern Medley: **TCP/IP's old in-Lisp stack was removed** (Medley now uses
  the host OS TCP stack). **PUP is non-functional.** **XNS works only through
  emulation** — you must run an external **"Dodo" NetHub/server** and call
  `\NSINIT` to bring XNS up against that virtual network; it's used mainly for
  file service/printing demos, not turnkey. **[confirmed]**
- The docs I found say **nothing about EVALSERVER specifically working today**,
  and the transport it depended on (real Ethernet PUP/XNS between D-machines) is
  gone. **Treat the original four-machine networked play as not directly
  revivable.** **[strong]**

**Recommendation:** replace networked multi-machine play. Best option:
**run all four Hearts players inside one Medley image** as separate *processes*
(`ADD.PROCESS`) communicating through in-image queues/monitors instead of the
`EVALSERVER` remote-eval RPC. This removes the network entirely and is by far the
lowest-risk path. (If you truly need multiple images, you could run several
Medley instances with distinct `--id`s and bridge them over host TCP — but that
means rewriting the EVALSERVER transport, so it's more work than collapsing into
one image.) **[strong / recommendation]**

---

## 7. KEE (IntelliCorp Knowledge Engineering Environment)

- **KEE is NOT part of Medley and is not available.** It was a **proprietary
  IntelliCorp** frame/expert-system product (first released 1983). Medley is
  MIT-licensed open source and ships no KEE. **[confirmed]**
- KEE's early versions did run on Xerox 1108/1109 (Dandelion/Dandetiger)
  Interlisp-D machines, so a 1986 program *could* have depended on it — but later
  KEE moved to Common Lisp on Symbolics/TI/Suns and the IP ended up with
  IntelliCorp's successors (assets sold to Tricentis in 2019). There is **no
  legal, obtainable, or emulated KEE** for Medley. **[confirmed / strong]**
- **Action:** grep the transcription for KEE-isms (`UNITMSG`, `UNITS`, `MAKE.UNIT`,
  `GET.VALUE`/`PUT.VALUE`, `KEE`/`UNITKB`, ActiveValues, `THEMEMBER`, etc.). If
  HEARTS uses KEE, those parts must be **reimplemented** in plain Interlisp
  (records/property lists you already have via `(RECORDS ...)` are the natural
  substitute). If it's pure Interlisp-D + window/process code, you're fine.
  **[recommendation]**

---

## 8. Known gotchas importing 1980s Dandelion source into Medley

- **Character set (XCCS vs UTF-8).** Original files are **XCCS**-encoded. Medley
  now has a **UNICODE library / `:UTF8` external file format** and XCCS↔Unicode
  mapping tables, and the clipboard converts to UTF-8. But conversion is only
  **lossless XCCS→Unicode→XCCS**; Unicode→XCCS can be lossy for out-of-range
  chars. For a hand-transcription to UTF-8, keep to ASCII wherever the original
  was ASCII, and be deliberate about the few special glyphs (`←`, and any Greek,
  math, or accented chars in comments). **[confirmed]**
- **The assignment arrow** — see §3. This is the single most common transcription
  trap: get `←`/`_` right or every assignment mis-parses.
- **Line endings.** Classic Interlisp files use **CR (0x0D)** as the line
  terminator; Unix/macOS text is **LF (0x0A)**. Medley has had explicit work on
  EOL handling and can read modern text, but a stray mixed CR/LF or a file the
  reader opens in the "wrong" EOL mode is a known class of problem — save the
  transcription with consistent line endings and, if the reader chokes, try the
  other EOL convention. **[confirmed there was EOL work / [verify in-image]]**
- **Control characters / font shifts.** Old prettyprint listings and especially
  hardcopy embed **XCCS control-character font-shift bytes** (for bold/italic,
  the `←` rendering, comment styling). A scan-to-text pass can silently inject or
  drop these. Make sure the transcription contains **only real code characters**,
  no leftover formatting control bytes. **[confirmed background]**
- **`CHARDELETE` / editing control chars.** `CHARDELETE` and friends are the old
  interactive line-edit control characters (rubout/backspace semantics). They
  matter when *typing* into the Exec, not in a `LOAD`ed file — but if OCR of an
  interactive transcript injected DEL/backspace control codes into your source,
  strip them. **[strong]**
- **`FILECREATED` timestamp / `FILEMAP`.** The `(FILECREATED ...)` line and any
  `FILEMAP` byte-offset table in the original are **stale** for a re-typed file.
  They're harmless to `LOAD` (evaluated as data), and `MAKEFILE` will regenerate
  them; don't try to hand-preserve byte offsets. **[strong]**
- **COMS must match reality.** `(RPAQQ HEARTSCOMS (...))` lists what the File
  Manager thinks is in the file. If transcription drops a function that COMS
  names, `MAKEFILE` will complain (missing definition); if you add one not in
  COMS it won't be saved. Reconcile COMS with the actual `DEFINEQ` set. **[strong]**
- **CLISP iteration (`bind/for/do/collect`) and `i.s.opr`s.** These are standard
  CLISP and load fine, but CLISP is **whitespace/`.`-sensitive** in ways OCR
  breaks (e.g. `for X in Y collect ...`). Proofread iteration clauses carefully.
  **[strong]**
- **Compile after loading.** Once it `LOAD`s clean, run the File Manager /
  compiler (`MAKEFILE` with compile, or `TCOMPL`/`BCOMPL`) to shake out residual
  issues and get `.DFASL` speed. **[strong]**

---

## Suggested revival sequence (condensed)

1. Install the macOS universal zip, clear quarantine, install XQuartz.
2. `./medley -a -e -n` → Interlisp Exec.
3. Transcribe with `_` for `←`, literal `%`/`[`/`]`, `(* … )` comments intact,
   consistent line endings, ASCII-only except intended specials.
4. Make the file visible to the image; `(LOAD 'HEARTS)`; fix reader errors.
5. Grep for KEE dependencies; reimplement if present.
6. Replace the `EVALSERVER` networked design with 4 in-image processes.
7. Tune window geometry/fonts for a modern display.
8. `(MAKEFILE 'HEARTS)` + compile.

## Biggest risks / unknowns

- **Networking (EVALSERVER/PUP/XNS)** — original multi-machine transport is
  effectively gone; plan to collapse to one image. (Highest-impact redesign.)
- **KEE dependency** — if HEARTS uses KEE at all, that code is unrecoverable and
  must be rewritten; unknown until the source is grepped.
- **The `←`/`_` encoding decision** — needs an in-image confirmation test; get it
  wrong and nothing assigns.
- **XCCS→UTF-8 fidelity + hidden control/font-shift bytes** in the scans.
- **Screen-geometry/font assumptions** in the window code on a modern display.

---

## Sources

- Install & run (macOS): https://interlisp.org/software/install-and-run/macos/
- Install & run (index): https://interlisp.org/software/install-and-run/
- macOS from GitHub: https://interlisp.org/software/install-and-run/macos/macos-from-github/
- `medley` script man page (flags): https://online.interlisp.org/downloads/man_medley.html
- Medley main repo: https://github.com/Interlisp/medley
- Using Medley (basics): https://interlisp.org/software/using-medley/il-using/
- Interlisp basics for Common Lisp users: https://interlisp.org/software/using-medley/cl-using/
- Unicode support discussion (`:UTF8`, XCCS mapping): https://github.com/orgs/Interlisp/discussions/1
- Change EOL convention to LF (issue #2): https://github.com/Interlisp/medley/issues/2
- Networking: what to do with TCP/networking tools (Dodo/XNS/`\NSINIT`, PUP dead): https://github.com/orgs/Interlisp/discussions/1179
- Set up/test Interlisp networking tools (issue #573): https://github.com/Interlisp/medley/issues/573
- 2024 Medley Annual Report (PUP/XNS/TCP status): https://interlisp.org/project/status/2024medleyannualreport/
- Importing files / FILESLOAD / MAKEFILE workflow (Paolo Amoroso): https://journal.paoloamoroso.com/importing-common-lisp-files-in-medley-with-textmodules
- Interlisp reader syntax (super-brackets, `%`, comments) — Wikipedia Interlisp: https://en.wikipedia.org/wiki/Interlisp
- Interlisp-D Reference Manual Vol II (Environment; windows, processes): https://www.bitsavers.org/pdf/xerox/interlisp-d/198510_Koto/3101273_Interlisp-D_Vol_2_Environment_Oct85.pdf
- KEE (Knowledge Engineering Environment): https://en.wikipedia.org/wiki/Knowledge_Engineering_Environment
- IntelliCorp: https://en.wikipedia.org/wiki/IntelliCorp
- Left arrow (←) character: https://en.wikipedia.org/wiki/%E2%86%90
