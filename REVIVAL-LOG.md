# Reviving HEARTS — a field log of the challenges

*A running account of what it actually takes to bring a 1986 InterLisp-D / KEE program back
to life on modern hardware. Kept for the next person who tries something like this — and for
the small, valiant InterLisp-D community, who will recognize every one of these.*

*Maintained by Claude Code (Anthropic coding agent), working with Harley Davis. Newest entries
appended at the bottom.*

---

## The setting

HEARTS ("Hearts Expert, A Real Time Sink") is a 1986 MIT 6.871 project by Harley Davis and
Ramana Rao: a four-player networked Hearts game with AI players, written in InterLisp-D for the
Xerox Dandelion, with the expert player built in KEE. Forty years later, the only surviving
artifacts are **six scanned PDFs** — no source files, no disk images, no sysout. The goal:
get it running again on **Medley Interlisp** (https://interlisp.org/).

---

## Challenge 1 — The source is a stack of photocopies

The "source code" is a scanned paper listing: 47 pages for the core, 31 more for the KEE
expert player and rules. No text layer. Everything has to be read back out of images.

- **Watch out for:** the scans are *clean* (a 1986 laser printout, high contrast), which makes
  OCR feasible — but a card game's source is dense with parentheses, and every one matters.
- **What worked:** rendering each page with `poppler` (`pdftoppm`) and transcribing visually,
  fanning the 78 code pages out across parallel agents (one per page-range) writing to separate
  files, then reconciling. Across all 78 pages only ~6 characters were genuinely illegible.

## Challenge 2 — The arrow that is secretly an underscore

InterLisp's assignment operator prints as a left-arrow `←`, but on the wire it is **ASCII
underscore `_` (code 95)** — `←` is just the display glyph. Get this wrong and *every*
assignment in the file mis-parses.

- **What worked:** keep the human-readable master with `←` (it matches the printout and reads
  well), and generate the Medley-loadable copy with a one-line `←`→`_` substitution. Best of
  both; verified by actually loading in Medley.

## Challenge 3 — Getting Medley to run at all on a modern Mac

- `--vnc` (the headless display path) is **explicitly unavailable on macOS**. That leaves X11
  (XQuartz) or SDL.
- The SDL backend (`ldesdl`) needs **SDL2.framework**, which wasn't installed, and its rpath
  pointed at `/Library/Frameworks` (admin-only).
- `DYLD_FRAMEWORK_PATH` didn't help: macOS **strips `DYLD_*` when the launch chain passes through
  a SIP-protected system binary** (`/bin/bash`), so it never reached the VM.
- **What worked:** install SDL2.framework into `~/Library/Frameworks` (no admin), then
  `install_name_tool -change` the VM's SDL2 reference to that path and re-sign it ad-hoc
  (`codesign -f -s -`). Medley then boots to a native Cocoa window — **no XQuartz needed**.

## Challenge 4 — Feeding commands to a 1986 Exec headlessly

- The `--rem.cm` startup file looked like the way to auto-load without typing. But `INTERPRET.REM.CM`
  (found in Medley's own `ADIR` sources) **evaluates only the *first* form in the file** — a
  multi-form script silently runs just its first line. Wrap everything in one `(PROGN …)`.
- File paths in Interlisp are `{DSK}<dir>sub>name`, **not** Unix `/a/b/c`. A Unix path passed to
  `OPENSTREAM`/`LOAD` just fails.
- Pasting from the macOS clipboard into the SDL window didn't work.
- **What worked (for now):** drop the load file into the Exec's *connected directory* (`~/il`) so
  it loads with a bare `(LOAD 'HEARTS)` — no path, minimal typing. (A robust auto-load harness is
  still on the wish list.)

## Challenge 5 — Super-brackets, OCR, and a load that stops after four functions

This is the big one. InterLisp's `[ ]` "super-brackets" auto-close any number of open `(` —
`]` closes back to the nearest `[`. Prettyprinted 1986 code uses them *heavily*. And in a scan,
**`[` and `(` look almost identical**.

The first Medley load defined exactly four functions and stopped. The culprit: OCR bracket slips
that prematurely closed the enclosing `(DEFINEQ`, so every function after the slip silently failed
to define. Six functions were affected, in two flavors:

1. **`[` misread as `(`** at a `LET`/`PROG`/`SELECTQ`-clause opener — so the matching `]` had no
   `[` to close to and over-closed to the enclosing `[LAMBDA`, ending the function early.
   (`HNET.Hello`, `Hand.RemoveCard`, `Dealer.Menuer`, `HP.Menuer`.)
2. **A closing `]` expanded into `)))`** — the transcriber "helpfully" wrote out explicit parens
   but dropped the level the `]` also closed (e.g. a `PROG` var-list), leaving a bracket open.
   (`H.Setup`, `HP.PassOut`.)

- **Nasty property: the errors *mask each other*.** In a whole-file bracket count, one function's
  extra-close cancels another's missing-close, so the file "nets to zero" while being deeply
  broken. Fixing one error makes the next one appear.
- **What worked:** an InterLisp-aware bracket linter (`tools/`) that models
  super-bracket semantics and — crucially — checks **each top-level form independently** so errors
  can't hide behind each other. It localizes the broken function and the exact line; then a
  **high-resolution crop of the original scan** (`pdftoppm -r 300` + a tight PIL crop) settles
  `[` vs `(` beyond doubt. Every fix was verified against the paper, not guessed.
- **Lesson for others:** do not trust a global paren count on Interlisp source. Check per-form,
  and keep the scans handy — the ground truth for a `[`/`(` call is the paper, at 300+ DPI.

## Challenge 6 — The whole file loads… then dies on the artwork

With the six super-bracket bugs fixed, the linter went fully green and Medley loaded **every
function and record** — the entire game logic — before stopping. Where it stopped: a
`READBITMAP` near the end of the file, with `Invalid argument: -30`.

That's the **"Random Cruff"** block: seven packed-bitmap literals (a card outline, four suit
pips, and the 50×50 app icon + shadow). These were transcribed *best-effort* — the packed
strings are dense grids of `O`/`0`/`@`/`L` glyphs that OCR can't nail per-character, and one bad
char is enough to make `READBITMAP` compute a nonsense dimension and fault.

- **Key realization:** the bitmaps are pure decoration and are **not needed to run the core**.
- **What worked:** keep the (imperfect) bitmap data in the master for later, but have the build
  step swap each `(RPAQ NAME (READBITMAP)) (W H "rows"…)` for a blank
  `(RPAQ NAME (BITMAPCREATE W H))` of the same size. The load sails past.
- Same treatment for two other end-of-file forms that can't work yet: the `FILESLOAD` of the
  dead `EVALSERVER`/`ACTIVEREGIONS` DCOMs, and the top-level `(H.MakeIcon)` desktop-icon call —
  both replaced with `(* … )` no-ops in the load build.
- **Lesson:** separate *faithful transcription* from *loadable artifact*. The master stays true
  to the paper; a small, documented build step makes the version that actually boots. Don't let
  1986 artwork or dead peripherals block bringing the logic up.
- **BUT the suit bitmaps are not optional.** The card table draws each card's suit from
  `Clubs/Diamonds/Hearts/SpadesBits`; a human player literally cannot read their hand without
  them. So the stubs are temporary — the artwork *must* be recovered for a playable UI.
  What makes that feasible: the `READBITMAP` "hardcopy" packing is now understood — each
  character is a 4-bit nibble (`@`=0 … `O`=15, letters only — a literal `0`/`O` slip is fatal),
  and each raster row is padded to a 16-bit word (so 11-wide → 4 chars/row, 30-wide → 8). That
  gives a hard validator (row length, legal charset) and, better, lets us *decode and render*
  each bitmap to eyeball whether it actually looks like a ♣/♦/♥/♠ before trusting it. The four
  11×11 suit pips are small and very recoverable; the 50×50 desktop icon is lower priority.

## Challenge 7 — It loads, it runs… and hits a ghost: a reference to a lost definition

First attempt to actually *play* — `(LHearts '(CLOWN CLOWN CLOWN CLOWN))` — got past loading and
into execution, then stopped with `ClownNames is an unbound variable`. `CLOWN.Create` picks a
random clown name from a variable `ClownNames`… that **the recovered source never defines**, and
that isn't in the file's COMS either (whereas the exactly-parallel `ConservativeNames` *is* both
defined via `RPAQQ` and listed in the COMS). So in 1986 `ClownNames` lived somewhere else — a
different file, or just the running image — and never made it into this listing. Forty years
later it's a dangling reference to a definition that no longer exists.

- **Lesson:** a scanned listing is not necessarily a *complete program*. A residential Lisp image
  accumulates state (variables, patches, ad-hoc definitions) that a file dump doesn't capture.
  Expect dangling references to things that were "just defined in the environment," and expect to
  reconstruct them. The COMS (the File Manager's table of contents) is your oracle for what a file
  *actually* carries vs. what it merely *uses*.
- **What worked:** treat it like the bitmap/FILESLOAD stubs — keep the faithful transcription
  pure, and inject the missing definition as a documented *revival patch* in `build-loadfile.py`.
  The original clown names are lost, so they were re-invented (in the whimsical spirit of the
  surviving `ConservativeNames`: BoringBart, PredictablePete, TheFork, LiplessWonder, …).
- Also seen here: a DWIM "possible non-terminating iterative statement" warning on `LHearts` —
  that's the game system's outer loop that deals a fresh game when the last one ends, not a bug.

## Challenge 8 — The artwork is mandatory after all: decoding READBITMAP by hand

The suit bitmaps aren't decoration — a human can't read their hand without ♣/♦/♥/♠ on the cards.
So the Challenge-6 stubs had to be replaced with the *real* recovered pips.

- **What worked:** the `READBITMAP` "hardcopy" packing turned out to be decodable: each character is
  a 4-bit nibble (`@`=0 … `O`=15, letters only — an `O`/`0` slip is fatal), each raster row padded
  to a 16-bit word. That gives a hard validator (row length + legal charset) and, better, a way to
  **decode and render each bitmap to a PNG and eyeball it** (`tools/readbitmap-decode.py`) before
  trusting it. The four 11×11 suit pips came back cleanly; the card table now draws legible suits.
- **Lesson:** for OCR'd binary blobs, build a decoder/renderer and *look* at the result — don't
  trust the characters. The 50×50 desktop icon stays stubbed (pure decoration, low value).

## Challenge 9 — A whole UI library is missing: ACTIVEREGIONS

The human player picks cards by *clicking* them, via a 1986 INTERMEZZO LispUsers library called
`ACTIVEREGIONS` (clickable/highlightable window regions). It isn't shipped with modern Medley, and
the modern lookalikes (`REGIONMANAGER`/`AIREGIONS`/`ARMODES`) don't match the API the game calls.

- **What worked:** we **wrote our own** — `medley/activeregions.lisp`: a record plus
  `SETACTIVEREGIONS`/`GETPICKREGION`/highlight functions hung on the window's `BUTTONEVENTFN`,
  modeled on Medley's `FREEMENU`. The human hand window's card-clicking works through it.
- **Lesson:** a missing dependency isn't always a wall — a small, API-compatible reimplementation
  can be less work than it looks, and becomes a reusable artifact (see Challenge 16).

## Challenge 10 — The authors' own 1986 bugs, rediscovered 40 years later

Actually *playing* surfaced real bugs in the original code — the kind only runtime finds:

- **The 2♣ opening lead never fired for Clown or Human.** The trick loop passes a `FirstTrick?`
  flag to each player's `Play`, but `CLOWN.Play` and `HP.Play` declared their lambdas without it
  and dropped it on the floor (only `CP.Play` got it right) — so the "must lead the two of clubs"
  rule silently never applied to them. A genuine 1986 bug; the co-author rediscovered his own
  undergraduate mistake.
- **`PromptPrint` vs `PROMPTPRINT`.** `HP.Menuer` calls `PromptPrint` (mixed case), but the actual
  function is the system `PROMPTPRINT`. Interlisp is case-sensitive, so DWIM prompted to correct it
  at runtime — an original inconsistency the paper preserved.
- **What worked:** keep both faithful in the transcription; fix them as documented revival patches
  in the build (forward `FirstTrick?`; correct the case). All logged in `HEARTS-BUGS.md`.

## Challenge 11 — More ghosts from the image: `Card.PrintCard`

Same species as `ClownNames` (Challenge 7): `Card.PrintCard` is called ~8× (thought windows, help
strings) but **defined nowhere** — only the compact `Card.Print` ("KS") survives in the file. Another
definition that lived in the 1986 image, not the listing. Supplied a readable version
("King of Spades") as a revival patch.

## Challenge 12 — Display drift: smeared scores and a shrinking hand window

- **`CT.PrintStats` smeared.** It redrew each player's `S:`/`T:` without erasing first, so
  shrinking-width digits left ghosts ("T: 31" from "T: 3" over "1"). Fix: clear each field with a
  `WHITESHADE` fill before drawing.
- **The hand window ate its own top row.** The `Play/Pass/Score/LegalCards` menu is `ATTACHWINDOW`'d
  to the window's *top*, and the Clubs row sat right under it. Bumping the creation size wasn't
  enough — the real culprit was `HP.Reshape` (run every deal), which recomputed the height from the
  current region and **drifted a little smaller each hand** until the top row clipped again. Fix:
  pin a stable window height in `HP.Reshape`; let only the width follow the hand.
- **Lesson:** with a per-deal reshape in play, a one-time size fix won't hold — find the function
  that recomputes geometry on every cycle.

## Challenge 13 — The clipboard that couldn't: a helper process that never forks

Tired of retyping, we tried to get the host clipboard working — and fell down a rabbit hole worth
recording (investigated with parallel sub-agents reading the Maiko C source):

- The `CLIPBOARD` library chooses `pbpaste` vs `xclip` by reading `OSTYPE` — a **non-exported** shell
  variable, so it always guessed wrong on macOS.
- Deeper: `(GETCLIPBOARD)` shells out via a **`unixcomm` helper process** that is forked **only by the
  `lde` kickstarter binary**. Launching the emulator directly as `--maikoprog ldesdl` (the
  XQuartz-free path) **skips the kickstarter**, so the helper never starts, the pipe fds stay `-1`,
  and every subprocess call returns `NIL` (`"Failed to find UNIXCOMM file handles; no processes"`).
- On the 2021 build the kickstarter is **X11-only**, so "working clipboard" and "no XQuartz" were
  mutually exclusive *by construction*.
- **What worked:** the X11 path (`lde` → `ldex` + XQuartz) forks the helper — clipboard works there.
  (See Challenge 15.) Subprocess spawning was never a stub or a macOS gap; it just needs the helper.

## Challenge 14 — SEdit wedges the whole image (SDL only)

Opening the structure editor **froze the entire image** at "Select region for SEdit window."

- **Root cause:** SEdit is the first thing that runs an interactive **press-hold-drag region
  *sweep*** (`\GETREGIONTRACKWITHBOX`, a non-yielding spin), where the game only ever does discrete
  *clicks* (`\TRACKWITHBOX`). The X11 event driver keeps the held-button state across motion and
  kicks the scheduler on button events; the SDL driver evidently doesn't, so the sweep's terminating
  transition never arrives and the single-threaded VM spins forever. **SDL-backend-only.**
- **What worked:** X11. On the current build over X11, SEdit opens and the sweep completes normally.

## Challenge 15 — The real fix was a current Medley (the 2021 build was the problem)

Half of the above (clipboard, SEdit, keyboard) traced to running a **~4-year-old** Medley. Upgrading
to the Aug-2026 release resolved them — but the upgrade had its own speed bumps, each a genuine
Medley/Maiko issue (all in `MEDLEY-ISSUES.md`):

- **Spaces in the install path** break the launcher and its helper scripts (unquoted `$0`-relative
  paths): install under a space-free directory.
- **SDL keyboard** doesn't recognize a modern Mac keyboard (`Unsupported keyboard type: 14`, ⌘
  unmapped) — another reason X11 wins on this build.
- **A failed `FILESLOAD` looks like it corrupts the world** ("Undefined car of form: FILESLOAD").
  We nearly proposed an `UNWIND-PROTECT` PR — then **read the source first** and found `LOAD` already
  rebinds `*PACKAGE*`/`*READTABLE*` in a `PROG` (unwind-safe). The real cause: an error enters a
  **break, which *suspends* rather than unwinds** the stack, so the loader's in-progress reader
  environment is still live while you type in the break. Unwind the break and it's fine.
- **Lesson:** before writing a "safe version" or filing a fix, check whether the platform already
  does the right thing. It usually does; the surprise is usually elsewhere.
- **Result:** on current Medley over **X11**, clipboard, keyboard, and SEdit all work.

## Challenge 16 — Packaging ACTIVEREGIONS as a reusable lispusers module

To give the reimplemented `ACTIVEREGIONS` (Challenge 9) back to the community as a standalone
loadable module, it needed a proper file wrapper — which fought back on the current sysout:

- `DEFINE-FILE-INFO` keys must be **keywords** (`:PACKAGE`, not `PACKAGE`) → else
  "Unrecognized file info key."
- `FILECREATED` wants a **bytecount number** after the filename token, or a later comparison hits
  `IGREATERP` on `NIL`.
- A stray top-level `(* comment)` right after the `COMS` **tripped the reader** (`SYNTAXP` →
  "NIL is not a NUMBER").
- **What worked:** mirror a real stock library file's header exactly (we used `library/CLIPBOARD` as
  the template) and keep the module to the essential forms. The result loads clean and is
  `MAKEFILE`/`TCOMPL`-ready.

## Milestone — the non-KEE game plays, end to end, on current Medley

`(LHearts '(HP CP CP CP))` on the current Medley release over X11: a human (clicking cards through
our ACTIVEREGIONS) plays a full game against three Conservatives — each a Lisp player running one
fixed *minimizing* strategy (competent but non-adaptive: no opponent modeling, no re-planning),
narrating its play in a thought window — with recovered card bitmaps, correct scoring, working host
clipboard, working keyboard, and a structure editor that no longer wedges. Forty years after 6.871,
the beer-driven GOFAI Hearts system runs again — everything except the KEE Expert player, which is
the one that actually *reasons* adaptively about the game (the reason it was the interesting part).

## Challenge 17 — A Medley you can script: headless Maiko in Docker

Everything so far was verified by a human watching an X11 window. To bring up the Expert we needed
to *run* Interlisp from a script and read the results back. [docker/](docker/) packages the 260810
release (Maiko + sysouts) with Xvfb and LOOPS; `tools/medley-headless script.lisp` boots it,
evaluates each form with errors trapped, writes a transcript, screenshots on request, and exits
(about a second of overhead). Getting there meant learning how Medley *really* takes input:
REM.CM is honoured only if it begins with a double quote (it is stuffed into type-ahead); `-e`
itself works through REM.CM, so ours had to type `(EXEC_INTERLISP)` first; environment variables
with underscores didn't survive `UNIX-GETENV`; a full exec window stops for a keypress unless
`PAGEFULLFN` is advised (Medley's own loadups do this); and nothing may ask for a window position,
so the harness answers `GETBOXREGION` itself. The payoff: whole games, screenshots included, in CI.

## Challenge 18 — Reviewing the first Expert attempt

A previous agent session had written three files (`ep-loops`, `ep-rules`, `ep-glue`) and marked
Phase 2b "complete" — but they had never been loaded. They could not have been: an invented
`DEFINECLASS` syntax that is neither LOOPS nor CLOS, `RPAQQ` and comments inside `DEFINEQ` (which
*defines* them as functions), redefinitions that would have clobbered core HEARTS functions, and
`H.MakePlayer` still calling KEE. More fundamentally, it hand-translated each rule into a pair of
Lisp lambdas, which throws away what made them rules: backward chaining (`?Self` is bound by
unifying the *goal* with the conclusion), side-effecting premises evaluated in order (the pass-out
rules call `DoPass` inside their premises), and "unstructured facts" proved by other rules
(`(Poor Spades Protection)`). We set it aside (kept in [attic/expert-first-attempt/](attic/expert-first-attempt/)).

## Challenge 19 — Don't rewrite the rules; bring back enough KEE

The core talks to the Expert only through `UNITMSG` — and its `H.Apply` still has the `Kee`
branch. So instead of porting 97 rules, we re-provided the slice of KEE they use, on LOOPS:
**KEELOOPS**. KEE units are LOOPS objects (named, so rules can say `expert.players`); slots are
instance variables, with a `Cardinality Multiple` IV property for KEE's multi-valued slots;
message handlers are LOOPS methods (LOOPS insists on `Class.Selector` names, so each is a
generated wrapper around the original `EP.*` function); certainty factors live in a facet IV and
combine by the EMYCIN rule. `QUERY` is a small backward chainer written without closures — the
remaining goals are passed along as data, which gives backtracking through `OR` and multi-valued
slots for free. The semantics come from the rules themselves and from the 1986 overview: rules by
descending weight, first answer versus `ALL`, `OR` short-circuits ("only the first is evaluated"),
an undefined function makes a premise an unstructured fact. The original code and rules then load
straight from the transcription; the KEE knowledge-base file itself is lost, so the unit classes,
handler wiring and personality thresholds are reconstructed — several of the thresholds from the
examples in the 1986 write-up.

The first real test was the pass: `two.d`, then `one.d`, then `highest.non.s.pick`, and — for a
hand with thin spades — `s.prot?.1` chained to prove `(Poor Spades Protection)` before `pass.hi.s`
fired. Handed the 2♥ 3♥ that Marcel passed Kant in the overview's Example 2, the Expert rated its
passer as Shooting with certainty **0.44** — exactly what the paper's narrative implies.

## Challenge 20 — Running code finds what proofreading misses

Loading code for the first time is a proofreading pass of its own. Five agents re-checked all 31
KEE pages against the scans and fixed ten slips; three more got past them — an unterminated
string the build's parser tripped on, and two *balanced* slips where a single extra `)` closed a
`LET` early, so later code ran with its variables unbound (`EP.ComputeStats`, which only a running
game exposed, and `EP.UpdateModel`). The build now checks for exactly that. Games then turned up
the authors' own slips — a rule reading `?Clubs` in the diamond case, `Card.Tricks` for
`Trick.Cards`, a variable bound to a unit and then to a number, per-deal points never reset —
each fixed as a labelled patch (HEARTS-BUGS §K). Two core bugs fell out too: `Card.MaxCard` ignoring
its suit argument for the first card (H3), and `dist/ACTIVEREGIONS` lacking a final `STOP`, which
made a fresh `FILESLOAD` of the game fail (H4). A soak test of back-to-back all-Expert games then caught
two rarer ones — rules asking whether cards of *different* suits are "equivalent", and asking for
the equivalents of a played-out suit's (non-existent) winner. Both end in the original code's
`SHOULDNT`, which in Medley is an unconditional break (not even `NLSETQ` catches it), so the game
simply froze — as it would have in 1986 (K7, K8). And one rule the paper says "probably should have
fired" (`slead.non.op.void.loser`, dead in 1986 because `CardList.EliminateSuits` was undefined)
now does; the example test replays that lead both ways.

## Milestone — the Expert plays again

Headless, on the 260810 release: a four-Expert game and an Expert-versus-three-Conservatives game
play to completion — 845 Expert plays, every one legal, no rule errors, 69 distinct rules firing,
including the whole strategy cycle (shoot, notice a shooter, eclipse, `eclipse.success`). The
overview's Example 1 replays rule for rule: `shoot.test`, then `pass.all.loser.h` (J♥) and
`pass.lowest.non.s` twice (2♦, 3♣), then `ope.min.is.normal` and `ope.low.pass` on the passer at
CF .3 each. About two seconds a move — the 1986 Dandelion took fifteen.

## Still ahead

- *(Done: the KEE Expert — Challenges 17–20.)* Still to do there: play it interactively on the Mac,
  and tune the reconstructed personality.
- **Networking is gone.** The Ethernet `EVALSERVER`/PUP/XNS remote-eval layer the four-machine
  game rode on is non-functional in Medley; plan is to collapse to one image with four processes.
- **Modern ports (Phases 3–4):** a Common Lisp port and a Python port, per `ARCHITECTURE.md`.
- *(Done since first written: the card artwork is recovered (Ch. 8), ACTIVEREGIONS is reimplemented
  (Ch. 9), and the 1024×808 Dandelion window geometry has been tuned enough to play (Ch. 12).)*
