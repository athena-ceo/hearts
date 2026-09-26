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
| H1 | **fixed** | `CLOWN.Play` and `HP.Play` called `H.GetLegals` without the `FirstTrick?` arg the trick loop passes (`(H.Apply Player 'Play Trick HeartsBroken? (EQP TrickNum 1))`), so the 2♣ opening-lead rule never fired for them (`CP.Play` does it right). Both fixed via revival patch: `HP.Play` now takes `FirstTrick?`, forwards it to `H.GetLegals`, and stashes it as a window prop so the "LegalCards" menu button (which had the same gap) uses it too. |
| H2 | **fixed (build)** | `HP.Menuer` calls `PromptPrint` (mixed case) in 3 places, but the function is the system `PROMPTPRINT` (all caps) — Interlisp is case-sensitive, so DWIM prompts to correct at runtime. Corrected in the build (`PromptPrint → PROMPTPRINT`); the faithful transcription keeps the original casing. |
| H3 | **fixed (build)** | `Card.MaxCard` with an `InSuit` argument seeds `highest` from the *first* card whatever its suit, so `(Card.MaxCard '(KH 3S) 'S)` is the K♥. `CardList.HighSpades?` inherits it: the Expert's `dump.hi.s` ("dumping my highest spade") could dump a heart. Fix: start from the first card *in* the suit. Revival patch 2m in `medley/build-loadfile.py`. |
| H4 | **fixed (build)** | On a fresh image `(FILESLOAD ACTIVEREGIONS HEARTS)` died with "NIL is not a NUMBER" (and so did plain `LOAD` of dist `HEARTS`, which `FILESLOAD`s ACTIVEREGIONS). Cause: the generated `dist/ACTIVEREGIONS` has no final `STOP`. Because its `FILECREATED` carries a byte count, `LOAD` takes the file-map path, which reads on past the last form and calls `SYNTAXP` on the end-of-file `NIL`. A second load "worked" only because the definitions were already in. Fix: end the file with `STOP`; a fresh `FILESLOAD ACTIVEREGIONS HEARTS EXPERT` then loads cleanly. Found by the headless tests; fixed in `build_activeregions()`. |

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
| D2 | **reimplemented (Phase 2b)** | `KEE` (IntelliCorp) — the Expert player's substrate. Proprietary, gone. Replaced by **KEELOOPS** ([medley/keeloops.lisp](medley/keeloops.lisp)): the subset of the KEE API the Expert uses (units, multi-valued slots, message handlers, `UNITMSG`/`GET.VALUE`/`PUT.VALUE`/…, certainty factors) on **LOOPS** objects, plus `QUERY`, a backward-chaining interpreter for the KEE rule language. The original `EP.*` code and all 97 original rules then run from the transcription; the lost knowledge base is reconstructed in [medley/expert-kb.lisp](medley/expert-kb.lisp). Built by [medley/build_expert.py](medley/build_expert.py) into `EXPERT`. See section K below. |
| D3 | deferred | `EVALSERVER` / Ethernet networking — dead PUP/XNS. Collapse the 4-machine design into one image with 4 processes. |

## Display / UI

| # | Status | Issue |
|---|--------|-------|
| U1 | **fixed** | Card-table `S:/T:` (score/tricks) smeared — `CT.PrintStats` redrew without erasing, so changing-width digits overlapped (bogus "T: 31"). Now clears each field with a `WHITESHADE` fill first. |
| U2 | **fixed (build), partial** | Replaying `(LHearts …)` stacked a **new card-table window** over the old one: `Hearts` does `(push CT.All (CT.Open Players))` each game, but `H.Initialize` only reset the `CT.All` *list* (`(SETQ CT.All)`) — it never `CLOSEW`'d the previous windows. `H.Initialize` now closes any still-open card tables (guarded by `BOUNDP` for the first call) before clearing the list. Per-player Conservative *thought* windows and the human *hand* window still persist across replays (they're not tracked in `CT.All`) — a lesser remaining leak. |
| U3 | **fixed (build)** | The human hand window's top (Clubs) card row was clipped under the attached Play/Pass/Score/LegalCards menu. **Two parts:** (a) `HP.CreateWindow` created it only 245px tall (`GETBOXREGION 300 245`) — bumped to 300; (b) the real cause — **`HP.Reshape` (called by `HP.RemakeHand` every deal) recomputed the height as `(PLUS fontheight (fetch HEIGHT of OldReg))`, which mixes region kinds / under-compensates for the title + attached-menu overhead, so the client shrank a little each deal** until Clubs clipped again (silently overriding the creation size). Fixed by pinning `HP.Reshape` to a stable constant height (320) while keeping the dynamic width. Card rows are pinned to the window *bottom*, so the fixed height keeps the top row clear. |

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

### Expert Player listings (`kee-expert-player.txt`, `kee-expert-rules.txt`)

Proofread page by page against 300-DPI scans (Sept 2026) once the code was actually going to be
loaded. Thirteen slips fixed, several of them balanced and so invisible to the bracket linters;
`medley/build_expert.py` now also checks every `LET` for bindings that don't look like bindings
and for `LET` variables used after the `LET` has closed (the two runtime-only ones below).

- `EP.DoPass` — `(PLUS (FLENGTH PCards))` closed early (the count of cards already chosen fell
  out of the sum), `(LET* ((` for `(LET* [(`, and `…CurrentPassCards)))` for `…]`.
- `EP.ComputeStats` — one `)` too many after `ComputeWinnersAndLosers` closed the `LET`, so the
  scoring half ran with `PlayerNum` unbound (found only by running a game).
- `EP.UpdateModel` — one `)` too many closed the `LET` bindings after the first one.
- `EP.WinnerSuit?` — a dropped inner `(GET.VALUE`.
- `EP.NonWinners` (`(OR` for `[OR`), `EP.ShootPlay` (`)))` for `]`), `EP.Trick` (dropped final `)`).
- `EP.Create` — `"%"expert%"""` had one `"` too many (unterminated string).
- `EXPERTCOMS` `EP.NumbrWithPoints` → `EP.NumberWithPoints`; `"Receiving; "` → `"Receiving: "`.
- Rules `te.go.for.it` (an extra `)` pulled a premise out of its `OR`), `slead.non.op.void.loser`
  (a misplaced `]` turned an argument into a premise), `sfol.little.over` (`[` for `(`).

## K — Expert Player revival (KEE → LOOPS)

The Expert runs the transcribed `EP.*` code and rules; these are the changes needed to do so,
all applied by [medley/build_expert.py](medley/build_expert.py) (each asserts it matched once).

**Original 1986 bugs fixed** (kept faithful in the transcription):

| # | Issue |
|---|---|
| K2 | `EP.NumberWithPoints` counted players with **more than one** point. The 1986 overview (§4.2.2, Example 2) diagnoses exactly this ("counts the number of players with *greater* than one point") and says it was changed; the listing predates the fix. Now `> 0`. |
| K3 | `EP.ShootPlay` cleared `WeakestSuit` on the *strategy* unit instead of the player, so `compute.weak.suit` ran once per game and its answer stuck. |
| K4 | `EP.Init` folded each deal's points into the totals but never zeroed them, so from the second deal every player looked like it had points (breaks `eclipse.success`, `te.go.for.it`, `ote.no.shooting`). |
| K5 | `EP.PrintLastGameReasons` ended with `(CLOSEALL)`, which in Medley closes every stream (dribbles too); `EP.PrintReasons` now closes the file it opened. |
| K6 | Reasons print in play order (KEELOOPS stores multi-valued slots newest-first). |
| K7 | Rules ask `EP.Equivalent?` about cards of *different* suits — directly (`edump.hope.to.screw.shooter`: is the shooter's card, maybe an off-suit dump, *not* the lead-suit winner?) and through `HighestEquivalent` over multi-suit candidate lists (`dump.non.winner`). The original answers with `SHOULDNT`, which breaks rather than signalling an error, so the game hangs — as it would have in 1986. Now: different suits are never equivalent (returns `Not?`). Found by a full-game test. |
| K8 | Once a suit is played out its winner is `NIL`, and `EP.FewestWinners` (rule `compute.weak.suit`) asks for the cards equivalent to it — `Hand.CardsInSuit` of suit `NIL` is another `SHOULDNT` break. `EP.EquivalentCards` of no card is now no cards. Found by the soak test. |
| K10 | Rule `lead.single.diamond` took `(CAR ?Clubs)` — copied from `lead.single.club`; `?Clubs` is unbound there, so it never fired. → `?Diamonds`. |
| K11 | `sfol.last.dump.loser` calls `Card.Tricks` (no such function) for `Trick.Cards`. |
| K12 | `slead.hearts` sends `LowestEquivalent?`; the handler is `LowestEquivalent`. |
| K13 | `edump.useless` tests `?ShooterVoids`, never bound in that rule (copied from `edump.shooter.void`); → `?AllCardSuitCards`. |
| K14 | `dump.loser` sent `Losers` an extra `?Self` argument (which became the *suit*), so it never matched a card. |
| K15 | `edump.hope.to.screw.shooter` and `edump.screw.shooter` bind `?Shooter` to the shooter's unit, then re-bind it to the shooter's number, so they could never fire. Second use renamed `?ShooterNum`. |
| K16 | `follow.highest.below.QS` compares against `?Mag`, never bound in that rule (its siblings bind it to the Q♠), and calls `CardList.LowerCards` with no suit, which matches nothing. Supplied both. Found by the full-game test (the only rule that raised an error). |

**Load mechanics:** K0 escapes `:` in the 1986 `FILECREATED` host names and comment words
(`{MITFS1-E40:…}`, `changes to:`) — under the INTERLISP readtable `:` is a package separator;
K0b drops the listing's `STOP` (the rules follow it); K1 drops `(RPAQQ AUTOBACKTRACEFLG ALWAYS)`
and `(RPAQQ INITIALS hed)`, which would change the user's session.

**Lost knowledge base, reconstructed** ([medley/expert-kb.lisp](medley/expert-kb.lisp)). The KEE
KB file itself did not survive: unit classes and slots are inferred from use; which unit each
`EP.*` function is a handler on is inferred from how it is sent (`SuitWithFewestWinners` is
`EP.FewestWinners`); `EP.AllCardSuits`, `CardList.EliminateSuits` (undefined in 1986 too — the
overview notes the rule that needs it never fired), `CardList.MaxCard`, `Card.CardsBetween` and
`Non.Null` (a slip for `Not.Null`) are supplied. **Personality values** are partly documented:
POMaxLowSpades 2, POMaxLoserHearts 3, POMinShootPoints 15 and LowPassPoints 0 come from the
overview's Example 1; TriggerHappiness 0.5 is inferred from Example 2 (Kant suspected Marcel at
CF .44 after the pass and switched to Eclipsing at .51 after trick 1 — our engine reproduces the
.44 exactly); the rest are judgement calls.

**KEE semantics choices** (in [medley/keeloops.lisp](medley/keeloops.lisp)'s header): rules by
descending weight; first answer vs `ALL`; premises left to right with backtracking; an undefined
function in a premise is an "unstructured fact" (as the overview describes); a Lisp premise that
errors fails and is logged in `KEE.RuleErrors`; `?variables` match case-insensitively (the
listing mixes `?self`/`?Self` inside single rules — `shoot.test`, `eclipse.success`, …).
