# HANDOFF — HEARTS revival

Start-here orientation for anyone (a person or a coding agent) picking this project up. It
summarizes **where things stand, how to run and rebuild it, the conventions that keep it sane, what's
left, and the roadmap.** Details live in the linked docs; this file is the map.

*Written by Claude Code (Anthropic coding agent) with Harley Davis, 2026-08-22; Expert player
(Phase 2b) and headless test environment added 2026-09-26.*

---

## TL;DR

The **entire HEARTS system — including the KEE Expert player — runs on current Medley
Interlisp.** Clown, Conservative and Human players play on the Aug-2026 release (260810) over X11
on macOS. The **Expert** (Phase 2b) runs its *original* 1986 code and all 97 *original* rules on
**KEELOOPS**, a small KEE compatibility layer built on Xerox LOOPS; it passes, plays, models its
opponents with certainty factors, and switches between minimizing, shooting and eclipsing. It is
verified in the **headless Docker Medley** ([docker/](docker/)): full four-Expert and Expert-vs-
Conservative games (every play legal, no rule errors), and a replay of the 1986 overview's worked
examples that reproduces the paper's rule firings and certainty factors. It has not yet been
played interactively on the Mac.

What's **not** done: the original **Ethernet networking** (deferred). Modern Common Lisp and
Python ports are future phases.

See it in action: [docs/hearts-game.png](docs/hearts-game.png).

---

## Current state

| Piece | Status |
|---|---|
| Transcription of the 1986 listing | ✅ complete, balance-checked ([transcription/](transcription/)) |
| Architecture spec | ✅ [ARCHITECTURE.md](ARCHITECTURE.md) |
| Loads on Medley | ✅ `(FILESLOAD CLIPBOARD ACTIVEREGIONS HEARTS)` clean on 260810/X11 |
| **Clown** player | ✅ plays |
| **Conservative** player | ✅ plays (one fixed *minimizing* strategy in Lisp; non-adaptive) |
| **Human** player | ✅ plays — name prompt, hand window, cards chosen by clicking |
| Card artwork (suit pips) | ✅ recovered & rendering ([tools/readbitmap-decode.py](tools/readbitmap-decode.py)) |
| ACTIVEREGIONS (clickable regions) | ✅ reimplemented ([medley/activeregions.lisp](medley/activeregions.lisp)) |
| Host clipboard / keyboard / SEdit | ✅ working on **X11** (not SDL — see MEDLEY-ISSUES) |
| Distribution package | ✅ [dist/](dist/) — `ACTIVEREGIONS` + `HEARTS` + `KEELOOPS` + `EXPERT` + README (fresh-image `FILESLOAD` fixed: HEARTS-BUGS H4) |
| **KEE Expert** player | ✅ runs headlessly — original `EP.*` code + 97 original rules on KEELOOPS/LOOPS ([medley/keeloops.lisp](medley/keeloops.lisp), [medley/expert-kb.lisp](medley/expert-kb.lisp)); tests in [tests/](tests/). Not yet tried interactively on the Mac. |
| Headless test Medley | ✅ [docker/](docker/) + [tools/medley-headless](tools/medley-headless) |
| **Neural network player** (`NP`, 2026) | 🟡 runs in pure Lisp and plays the same moves as Python on 300 deals; see "Benchmarks, rule experiments and the neural network" below. Not yet tried on the Mac, and `dist/HEARTSNET` holds a 1-hour network until training finishes. |
| **LLM player** (`LP`, 2026) | 🟡 complete games pass on a stub and through the real SDK against a mock server ([tests/llmplayer.lisp](tests/llmplayer.lisp)), and a short game has run against the real API on Haiku. See "The LLM player" below for what has not been run. |
| Ethernet networking | ⛔ deferred (dead PUP/XNS; collapse to one image) |
| Modern CL / Python ports | 🔜 planned (Phases 3–4) |

Original 1986 bugs found and fixed, plus every revival patch, are in [HEARTS-BUGS.md](HEARTS-BUGS.md).
Every Medley/Maiko issue hit (and how it resolved) is in [MEDLEY-ISSUES.md](MEDLEY-ISSUES.md). The
narrative of the whole revival is [REVIVAL-LOG.md](REVIVAL-LOG.md).

---

## How to run it (the working setup)

Environment on this machine: repo at `~/Development/hearts`, Medley at `~/medley-260810` (note the
**space-free path** — the launcher breaks on spaces, MEDLEY-ISSUES M7), files loaded from the
connected dir `~/il`.

```bash
open -a XQuartz && cd ~/medley-260810/medley && export OSTYPE=darwin && ./medley --apps --interlisp --noscroll
```

Then, in the Interlisp Exec:

```
(FILESLOAD CLIPBOARD ACTIVEREGIONS HEARTS)
(LHearts '(HP CP CP CP))
```

For the **Expert**, also load `EXPERT` (after HEARTS) — it needs LOOPS, which isn't in the Medley
release: `git clone https://github.com/Interlisp/loops ~/medley-260810/loops` once, and EXPERT loads
it itself (or set `LOOPSDIR`). Then e.g. `(LHearts '(HP EP EP CP) T)` — `T` = open hands, so each
Expert's window narrates its strategy and reasons.

The friendlier front door is **`(FILESLOAD PLAYHEARTS)` then `(PlayHearts)`**
([medley/playhearts.lisp](medley/playhearts.lisp), built into `dist/PLAYHEARTS`): menus for the
players and options, a Start Game / Setup… / Exit menu bar on the card table, games in their own
process, and Exit closes every Hearts window; closed-hand Experts narrate in their own
"Thoughts of …" windows. It only adds `PH.*` functions plus two pieces of *advice* (not
redefinitions) that act only on those Thoughts windows — `Open.RemakeWindow` draws no cards there,
`Open.Print` starts each message on a new line; `(UNADVISE 'Open.RemakeWindow)` /
`(UNADVISE 'Open.Print)` remove them. The 1986 `LHearts` (which starts at once and loops until
Ctrl-E) and all 1986 definitions are untouched.

Full setup (XQuartz tuning, leave-X-running, auto-load via `rem.cm`, quit with `(LOGOUT)` /
`pkill ldex`) is in [medley/MEDLEY-SETUP-NOTES.md](medley/MEDLEY-SETUP-NOTES.md) §1a. How to play is
in [USER-MANUAL.md](USER-MANUAL.md); first-time-on-Medley steps are in [dist/README.md](dist/README.md).

**Use X11, not SDL.** The SDL backend (`--maikoprog ldesdl`) gives a native window with no XQuartz
and the game plays, but on the current build it has no clipboard, an incomplete keyboard map, and
SEdit wedges. X11 has all three. (Root causes: MEDLEY-ISSUES M2/M3/M8.)

---

## The LLM player

[medley/llmplayer.lisp](medley/llmplayer.lisp) (built into `dist/LLMPLAYER`) is a `Type=Lisp` player
like the Conservative, so the core is untouched: one piece of advice on `H.MakePlayer` adds the seat
code `LP`. For each decision it writes what its seat knows to a JSON file and runs
[medley/llm_player.py](medley/llm_player.py), which calls the API and prints one S-expression line.
The helper adds the bookkeeping (points so far, unseen cards, known voids) and asks for structured
output. The model's plan is carried from move to move within a deal. How to use it and what it costs:
[USER-MANUAL.md](USER-MANUAL.md).

Design choices worth keeping:

- **Requests go through a file,** because long stdin writes lose bytes (MEDLEY-ISSUES M10).
- **Lisp validates every answer** against `H.GetLegals`, because the game loop doesn't, and falls back
  to a safe card rather than ever stopping the game.
- **Two API paths in the helper, chosen by `LP.Provider`:** `anthropic` (Messages API, adaptive
  thinking, effort) and `openai` (Chat Completions). The second is deliberately forgiving because
  servers vary: it sends no token limit or effort, retries once without `response_format` on a 400,
  and reads JSON out of `<think>` reasoning or a code fence.
- **The output schema is fixed** (all 52 cards) rather than narrowed to each decision's legal cards,
  because every new schema pays a compile on first use. An illegal answer gets one retry.
- **[tests/check_llm_log.py](tests/check_llm_log.py) lists the allowed request fields exactly,** to
  guard against leaking another seat's cards. Adding a field means editing that list deliberately.

Refusal fallback (`fallbacks: "default"`) is on for the models that accept it. The real API has
been called once in a short game (2026-11-05, `claude-haiku-5-5`, low effort, one deal to a 10-point
limit): 10 calls, no fallbacks, 27,065 input and 6,632 output tokens, about $0.006, and 5 seconds a
move on average (12 at most). The OpenAI path has played the same short game on a real server, local
Ollama 0.6.0 with `mistral:latest` (12 calls, no fallbacks), and passed `tests/real_api_check.py` with
`gemma2:latest`. Not yet done: anything on OpenAI's own API or a hosted OpenAI-compatible service, a
game on the Mac, a game on Opus, a full game to 100, and any measurement of how well it plays.

**Testing against the real API.** Two checks spend real money and stay out of `tests/run-all.sh`.
Both default to `claude-haiku-5-5` at low effort. Keep the key in a private file outside the repo
and pass it on the command line of the one command that needs it:

```bash
ANTHROPIC_API_KEY="$(cat ~/.config/hearts/anthropic-key)" python3 tests/real_api_check.py
```

```bash
ANTHROPIC_API_KEY="$(cat ~/.config/hearts/anthropic-key)" tools/medley-headless --timeout 900 tests/llm-real-game.lisp
```

The first asks for one play and one pass, with no Medley. The second plays a short game in headless
Medley, with the model's reasoning in `out/llm-real-game.jsonl`. `tools/medley-headless` also passes
`ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LP_PROVIDER` and
`LP_MODEL` through.

For the OpenAI path, a local Ollama is a free real server. Inside Docker its address is
`host.docker.internal` rather than `127.0.0.1`:

```bash
OPENAI_BASE_URL=http://127.0.0.1:11434/v1 python3 tests/real_api_check.py --provider openai --model mistral:latest
```

```bash
LP_PROVIDER=openai LP_MODEL=mistral:latest OPENAI_BASE_URL=http://host.docker.internal:11434/v1 tools/medley-headless --timeout 900 tests/llm-real-game.lisp
```

In Claude Code, use this form rather than setting the key in `env` in `settings.json`, or exporting
it in the shell Claude Code starts from: Claude Code reads `ANTHROPIC_API_KEY` and
`ANTHROPIC_BASE_URL` for its own API calls too. Don't paste the key into chat.

---

## Benchmarks, rule experiments and the neural network

**The benchmark** ([bench/](bench/)): `bench/run.py` plays one player in seat 1 against three Experts, on
fixed deals ([bench/deals.lisp](bench/deals.lisp), 4,000 shuffles, from `bench/make_deals.py`), in one long
game with the over score out of reach and the table's trick pause off. `bench/report.py` writes
[docs/benchmarks/](docs/benchmarks/); `bench/compare.py` compares variants by points and by margin (points
minus the average of the other three). The Expert is deterministic on fixed deals: an unchanged run
matched on all 1,000 deals, so only deals a change actually touches differ, which makes rule tests sensitive.

Deals are split so results stay honest: 1-200 are the pilot, 201-1200 are for trying things,
1201-2000 and 2001-4000 are held out for a final test of a candidate, once.

**Rule experiments** ([bench/rules/](bench/rules/)): each `x-*.lisp` gives seat 1 alone its own rules or
thresholds (`bench/rules/epx.lisp`), leaving the 1986 rule base and the other Experts untouched. `x-combo`
(no setting out to shoot, no eclipsing, more spade protection, play high when you must win anyway) scored
-1.21 of margin on the training deals, then -0.46 on 800 unseen deals and -0.79 on 2,000 fresh ones, -0.70
over both. The shooting threshold of 15 comes from one example player in the 1986 overview, and applying it
to every Expert is our assumption, so that gain may partly reflect our reconstruction.

**The network** ([selfplay/](selfplay/)):

- `hearts_sim.py` is the game outside Medley. `test_sim.py` replays real Medley logs through it, so a rule
  mismatch fails loudly. It needs benchmark logs in `out/bench/`.
- `features.py` turns the same request the LLM helper gets into 512 numbers. `train.py` trains by self-play
  with PPO in a local virtual environment (`python3 -m venv selfplay/.venv`, then `pip install numpy torch`).
  `overnight.py` runs two seeds and tries them in Medley on the way.
- `nn_helper.py` plays a network through the LLM player's seat, in pure Python, to test it against the
  real Expert before any Lisp is involved: `python3 bench/run.py nn:out/selfplay/a/best.json`.
- `export_lisp.py` writes the weights for [medley/nnplayer.lisp](medley/nnplayer.lisp), seat `NP`, which
  needs nothing outside Medley: `python3 bench/run.py np:PATH`. `NP.Features` must stay the exact twin of
  `features.py`. To check them, play the same deals both ways and compare `deals.jsonl`: on 300 deals every
  score matched. A move takes about 10 ms because `NP.Layer` and `NP.Scores` are compiled when the file loads.
  Layers are arrays of raw float blocks because `\ALLOCBLOCK` rows read straight off the file with `\BINS`.

---

## How to rebuild the loadable files

The loadable `HEARTS` is **generated** from the faithful transcription — never hand-edit it. Edit the
source, then rebuild:

```bash
cd ~/Development/hearts
python3 medley/build-loadfile.py          # writes medley/HEARTS (dev) + dist/HEARTS + dist/ACTIVEREGIONS
python3 medley/build_expert.py            # writes medley/EXPERT (dev) + dist/EXPERT + dist/KEELOOPS
cp dist/HEARTS dist/ACTIVEREGIONS dist/KEELOOPS dist/EXPERT dist/PLAYHEARTS dist/LLMPLAYER dist/llm_player.py ~/il/    # stage where Medley loads them
```

Then reload in Medley (`(FILESLOAD ACTIVEREGIONS HEARTS)`), or relaunch.

- **Source of truth:** [transcription/hearts-core.lisp](transcription/hearts-core.lisp) (assembled
  from [transcription/parts/](transcription/parts/)) + [medley/activeregions.lisp](medley/activeregions.lisp).
- **Build script:** [medley/build-loadfile.py](medley/build-loadfile.py) — does mechanical transforms
  (`←`→`_`, strip our annotations, stub the lost icon bitmaps) and injects **documented revival
  patches** (missing definitions + original-bug fixes). It emits two builds: `medley/HEARTS`
  (self-contained, ACTIVEREGIONS inlined — handy for one-file dev loads) and `dist/` (two files:
  `HEARTS` `(FILESLOAD ACTIVEREGIONS)`s the separate module — the community distribution).
- **Sanity tools:** [tools/interlisp-balance.py](tools/interlisp-balance.py) (whole-file bracket
  balance) and [tools/interlisp-lint.py](tools/interlisp-lint.py) (per-top-level-form, catches
  super-bracket slips that mask each other).

---
- **Expert:** [medley/build_expert.py](medley/build_expert.py) reads the two KEE transcriptions
  (re-splicing the rules page that was bound into the EXPERT listing), applies revival patches
  K0–K16, re-emits the rules as `KEE.DEFRULE` data, and checks every definition's structure
  (including `LET`s closed too early — the class of OCR slip bracket linters can't see).
  Hand-written sources: [medley/keeloops.lisp](medley/keeloops.lisp) (KEE on LOOPS + the rule
  interpreter) and [medley/expert-kb.lisp](medley/expert-kb.lisp) (the reconstructed KB).

## How to test (headless Medley in Docker)

```bash
tools/medley-headless --build                                   # once
tools/medley-headless tests/smoke.lisp                          # harness self-test
tools/medley-headless --loops tests/expert-load.lisp            # KB wiring, pass/pass-in
tools/medley-headless --loops tests/expert-examples.lisp        # the 1986 worked examples
tools/medley-headless --loops tests/playhearts.lisp             # the PlayHearts front end
tools/medley-headless --loops --timeout 1500 tests/expert-game.lisp   # two full games (~12 min)
tools/medley-headless --timeout 900 tests/llmplayer.lisp        # the LLM player: stub + mock API, no key needed
python3 tests/test_llm_player.py                                # its Python helper, on your own SDK
tools/medley-headless --timeout 900 tests/nnplayer.lisp         # the neural network player, in pure Lisp
python3 selfplay/test_sim.py                                    # the simulator, against real Medley logs
python3 tests/real_api_check.py                                 # the real API: costs money, needs a key (see "The LLM player")
tests/run-all.sh                                                # everything, with a summary
tools/medley-headless --loops --timeout 2700 tests/expert-soak.lisp  # 3 more games, rare-situation hunt
```

Scripts are Interlisp forms; `HT.CHECK` gives PASS/FAIL lines, `HT.SNAP` screenshots the virtual
display. Output in `out/medley/`. Details and the Medley automation traps it works around:
[docker/README.md](docker/README.md).


## Conventions (please keep these)

1. **Faithful transcription stays faithful.** [transcription/](transcription/) matches the 1986 paper
   listing, warts (original bugs, OCR-verified `[`/`(`) and all. Fixes and reconstructions go in
   `build-loadfile.py` as labeled revival patches — never by editing the master. This keeps "what
   they wrote" separate from "what we changed to run it."
2. **Two bug trackers, by audience.** [HEARTS-BUGS.md](HEARTS-BUGS.md) = HEARTS's own bugs (for us);
   [MEDLEY-ISSUES.md](MEDLEY-ISSUES.md) = Medley/Maiko upstream issues (for the Interlisp community).
3. **Verify OCR against the scans.** For any `[`/`(` or packed-bitmap question, the 300-DPI scan is
   ground truth (`pdftoppm -r 300` + a tight crop). Don't guess.
4. **Interlisp is case-sensitive.** `LHearts` ≠ `LHEARTS`. Watch this in both the code and when
   reaching HEARTS symbols from a Common Lisp exec (`IL::|LHearts|`).
5. **Commit messages** end with the `Co-Authored-By` trailer; keep the trackers/docs updated in the
   same commit as the change they describe.

---

## Follow-ups (near-term, concrete)

- **Contribute ACTIVEREGIONS upstream.** It's a clean, reusable stand-in for the lost INTERMEZZO
  library — worth a PR to the community `lispusers` collection. Compile with `(MAKEFILE 'ACTIVEREGIONS)`
  then `(TCOMPL 'ACTIVEREGIONS)` and ship the `.DCOM` alongside source.
- **Report the confirmed Medley/Maiko issues** to the Maiko/Medley project: M2 (the `unixcomm`
  helper is forked only by the `lde` kickstarter, so a direct `ldesdl` launch has no
  subprocess/clipboard), M3 (SDL region-sweep wedge), M7 (launcher breaks on spaces), M8 (SDL
  keyboard map). All have file:line evidence in [MEDLEY-ISSUES.md](MEDLEY-ISSUES.md).
- **Announce it** — interlisp.org Zulip / the Interlisp community, and Ramana. The
  [docs/hearts-game.png](docs/hearts-game.png) screenshot is the hook.
- **Finish U2** (minor): replaying `(LHearts …)` still leaves per-player *thought* and *hand* windows
  stacked (only the card table is now closed on re-init). Track and close them too if it bothers you.
- **Optional:** recover or redraw the 50×50 desktop icon bitmaps (currently stubbed) if you want the
  `H.MakeIcon` desktop icon back.

---
- **Play the Expert on the Mac.** Clone LOOPS beside Medley, load EXPERT, and play
  `(LHearts '(HP EP EP EP) T)`; watch the narration. Only the headless runs have been done.
- **Tune the reconstructed personality** ([medley/expert-kb.lisp](medley/expert-kb.lisp)) —
  four values are from the 1986 overview, TriggerHappiness is inferred, the rest are guesses.


## Roadmap

- **Phase 0 — Transcription.** ✅ Done.
- **Phase 1 — Architecture spec.** ✅ Done ([ARCHITECTURE.md](ARCHITECTURE.md)).
- **Phase 2 — Medley revival (non-KEE).** ✅ **Done** — Clown, Conservative, Human all play on
  current Medley/X11.
- **Phase 2b — The KEE Expert player.** ✅ **Runs** (headless-verified; interactive Mac play still
  to do). KEE is gone, so instead of re-writing the rules we re-provided the part of KEE they use:
  **KEELOOPS** maps KEE units/slots/message handlers onto LOOPS objects and interprets the KEE rule
  language (backward chaining by weight, `THE … OF … IS …` patterns, unstructured facts, EMYCIN
  certainty factors). The original `EP.*` code and all 97 rules run from the transcription; the lost
  KB (unit classes, handler wiring, personality thresholds) is reconstructed from the code and the
  1986 overview. See REVIVAL-LOG Challenges 17–20 and HEARTS-BUGS section K.
- **Phase 2c — Networking.** The original 4-machine Ethernet design (`EVALSERVER`/PUP/XNS) is dead.
  Plan: collapse to a single image running four processes (Medley multiprocessing already backs the
  in-image multiplayer that works today), or a modern socket transport — optional, and mostly
  interesting for period authenticity.
- **Phase 3 — Modern Common Lisp port.** Build against the language-neutral contract in
  [ARCHITECTURE.md](ARCHITECTURE.md) (six-message protocol, dispatch, data model, game loop).
- **Phase 4 — Python port.** Same contract, for broad distribution.

---

## Repo map

```
README.md            Project intro (origin story) + "play it today" + doc index
HANDOFF.md           This file
ARCHITECTURE.md      Language-neutral spec — the contract for every port
REVIVAL-LOG.md       Narrative field log of the whole revival (Challenges 1–16)
HEARTS-BUGS.md       HEARTS's own bugs (original 1986 + revival patches)
MEDLEY-ISSUES.md     Medley/Maiko upstream issues (for the community)
USER-MANUAL.md       How to play a hand
docs/hearts-game.png Screenshot of a game in progress
original/            The scanned source PDFs (starting assets)
transcription/       Faithful text recovered from the scans (+ parts/, docs/, KEE files)
tools/               interlisp-lint.py, interlisp-balance.py, readbitmap-decode.py, medley-headless
medley/              build-loadfile.py, activeregions.lisp, HEARTS (dev build), MEDLEY-SETUP-NOTES.md,
                     build_expert.py, keeloops.lisp, expert-kb.lisp, EXPERT (dev build), playhearts.lisp,
                     llmplayer.lisp + llm_player.py (the LLM player)
dist/                Community distribution: ACTIVEREGIONS, HEARTS, KEELOOPS, EXPERT, PLAYHEARTS, LLMPLAYER,
                     llm_player.py, README.md
docker/              Headless Medley (Maiko + Xvfb + LOOPS) for scripted tests
tests/               Headless test scripts (tools/medley-headless ...)
attic/               Superseded work kept for the record (the first Expert attempt)
modern-lisp/         Phase 3 (planned)
python/              Phase 4 (planned)
```

GitHub: <https://github.com/athena-ceo/hearts>
