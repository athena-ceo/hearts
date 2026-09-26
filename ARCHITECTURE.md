# HEARTS — Architecture Specification

*A language-neutral specification of the 1986 HEARTS system, reconstructed from the transcribed
InterLisp-D source (`transcription/hearts-core.lisp`) and the original design write-up
(`transcription/docs/overview.md`). Written by Claude Code (Anthropic coding agent) for Harley
Davis, as Phase 1 of the revival. Line references are to `transcription/hearts-core.lisp`.*

This document is the shared contract for every reimplementation: the Medley revival (Phase 2),
the modern Common Lisp port (Phase 3), and the Python port (Phase 4). It describes **what the
system does and how its parts talk**, independent of Interlisp.

---

## 1. Overview

HEARTS plays the card game of hearts with four players. Players may be any mix of four kinds —
**Clown** (random), **Conservative** (rule-of-thumb minimizer), **Human** (interactive UI), and
**Expert** (the KEE expert system) — and, in the original, may be spread across several networked
Xerox machines. A non-intelligent **Administrator** ("the house") runs the game and a shared
graphic **Card Table**, communicating with players through a small, fixed **message protocol**.

The design's key idea: *players are opaque objects behind a uniform message interface.* The
Administrator neither knows nor cares whether a player is a Lisp function, a KEE knowledge base,
or a proxy for a player on another machine. Everything below follows from that.

```
                 ┌───────────────────────────────────────────────┐
                 │              Administrator ("house")            │
                 │   deal · rotate passes · run tricks · score     │
                 └───────────────┬───────────────────────────────┘
                                 │  H.Apply(player, op, …args)  →  reply
        ┌───────────────┬────────┴────────┬────────────────┐
        ▼               ▼                 ▼                ▼
     Clown         Conservative        Human            Expert
    (Lisp)            (Lisp)           (Lisp/UI)        (KEE unit)
        │               │                 │                │
        └───────────────┴───────┬─────────┴────────────────┘
                                 ▼
                      Card Table (shared display)      [+ Network proxies]
```

---

## 2. Domain: the rules of hearts

Standard hearts, as implemented (see `overview.md` §2 and `H.PlayGame`/`H.GetLegals`):

- One 52-card deck, four players, 13 cards each.
- **Passing.** Before each deal, each player passes **3** cards. Direction rotates by deal:
  **left → across → right → hold (no pass) →** repeat (`H.Deal`, lines ~430–470; direction offset
  tables `Left (4 1 2 3)`, `Across (3 4 1 2)`, `Right (2 3 4 1)`).
- **Play.** The holder of **2♣** leads the first trick. Players must follow the led suit if able;
  otherwise they may play anything (**dump**). Highest card of the led suit wins the trick and
  leads the next (`H.GetLegals`, `Trick.Winner`).
- **Restrictions.** No hearts or the Q♠ on the first trick; hearts may not be *led* until "broken"
  (a heart has been dumped) — tracked by `HeartsBroken?` in the play loop (lines ~320–345).
- **Scoring.** Each heart = 1 point; **Q♠ ("the Maggie") = 13 points**. Points are penalties
  (low is good). **Shooting the moon:** taking all 26 points scores 26 to *everyone else* instead
  (`Deal.SetScore`, `Game.Update`). A game ends when any player reaches **100**
  (`Game.OverScore`); lowest score wins.
- **Card equivalence.** Cards separated only by already-played cards are strategically
  "equivalent"; the Expert player exploits this (History unit — see §8).

---

## 3. Data model

The original `RECORD`/`DATATYPE` declarations, to be realized as structs/classes/objects in each
target language. (Exact fields as transcribed.)

| Record | Fields | Notes |
|---|---|---|
| `Card` | `Suit . Value` | Suit ∈ `C D H S`; Value 2–14 (J=11…A=14). A cons pair. (line 2119) |
| `Hand` | `C D H S Owner` | Cards held, **split into four per-suit lists** + owning player. (2121) |
| `Trick` | `LeadPlayerNum Cards Winner` | One trick in progress/complete. (2123) |
| `Deal` | `Hands Tricks D.Score D.CumScore PassDir PassOut PassIn D.RealHands` | One deal (hand). (2117) |
| `Game` | `Players Deals Score Winners` | The whole game. (2113) |
| `Player` | `Name Number Type Object Mapping` | **The dispatch record — see §4.** (2115) |
| `CP` | `Name Hand ThoughtWindow MaggiePlayed? CP.OpenHand? CP.HandWindow` | Conservative player state. (1735) |
| `Clown` | `Clown.Hand` | Clown state (a `DATATYPE`). (2057) |
| `HN.Player` | `HNP.Name HNP.Host` | Network proxy: a remote player's name + host. (489) |

Design notes for ports:
- **`Hand` is suit-bucketed** (`C/D/H/S` lists), not one flat list — many helpers (`Hand.CardsInSuit`,
  `Hand.Void?`, `Card.MaxCard … LeadSuit`) rely on this. Keep the shape or provide equivalents.
- `Card` as `(Suit . Value)` — a 2-field immutable value. Comparison is within-suit by Value.
- `Player.Object` is the per-player opaque state (a `CP`, `Clown`, KEE unit, or `HN.Player`);
  `Player.Mapping` and `Player.Type` drive dispatch.

---

## 4. The player message protocol (the heart of the system)

All Administrator→player communication goes through one entry point (`H.Apply`, lines 415–446):

```
H.Apply(player, op, …args) →
    switch player.Type:
      Lisp:  fn = player.Mapping[op]                       ; per-player {op → function} alist
             if fn: return fn(player.Object, …args)
             elif op ∈ MustOps: error                      ; required op not implemented
      Kee:   return UNITMSG*(player.Object, op, args)       ; send message to KEE unit
      Net:   if op ∈ ResponseOps:                           ; ops that expect a reply
                 return REMOTEVAL(HNET.Apply(player.Number, op, args), player.Object.Host)
    finally: CT.InformAll(player, op, args, reply)          ; update shared Card Table
```

Three consequences the ports must preserve:

1. **Uniform dispatch by player type.** `Lisp`/`Kee`/`Net` are the three transports. A player's
   *kind* (Clown/Conservative/Human/Expert) is realized as a `Type` + a `Mapping` (for Lisp
   players) or a KEE unit (for the Expert). Ports map this naturally: **CLOS generic functions**
   (Phase 3) or a **`Player` base class with method dispatch** (Phase 4); the `Kee` transport
   becomes "call the rules engine," the `Net` transport becomes "call over the network."
2. **The Card Table is a cross-cutting observer.** *Every* message result is echoed to the shared
   display via `CT.InformAll`. Ports should keep this as an observer/event hook, not inline it.
3. **`MustOps` vs optional ops.** Some ops are mandatory; `Trick`/`Results` are optional
   notifications (overview §3.2.1). A player may ignore optional ops.

### 4.1 The messages

Sent by the Administrator during a deal (see `H.PlayGame`/`H.Deal`, and overview §3.2.1):

| Op | Direction | Args | Returns | Meaning |
|---|---|---|---|---|
| `GiveHand` | house→player | `hand`, `playerNumber` | — | Start of deal: store your 13-card hand and seat (1–4). (line 390) |
| `PassOut` | house→player | `direction` | **3 cards** | It's time to pass; choose 3 cards from your hand in the given direction. (394) |
| `PassIn` | house→player | `cards` | — | Here are the 3 cards passed *to* you; merge into your hand. (408) |
| `Play` | house→player | `trick` (partial) | **1 legal card** | It's your turn; play one legal card given the trick so far. (329) |
| `Trick` | house→player | `trick` (complete) | — | *(optional)* A trick finished: who led, cards played, who won. (340) |
| `Results` | house→player | `scores` | — | *(optional)* The deal is over; here are the scores. (349) |

Legality of a `Play` reply is defined by `H.GetLegals(hand, trick, heartsBroken?, firstTrick?)`
(line 450): follow suit if possible; on the first trick exclude hearts and Q♠; don't lead hearts
until broken. The Administrator is the authority — a player returns a card, the house validates.

---

## 5. The game loop (Administrator)

From `H.PlayGame` (lines ~300–355) and `H.Deal`:

```
new Game(players); Game.Score ← 0,0,0,0
repeat until some score ≥ 100 (Game.OverScore):
    Deal:
      shuffle; deal 13 to each (H.Shuffle, H.Deal)
      GiveHand → each player
      if this deal's direction ≠ hold:
          collect PassOut from each player (3 cards each)
          route them by direction; PassIn → each player
      Lead ← holder of 2♣
      for trick in 1..13:
          for seat starting at Lead, going clockwise:
              card ← Play(player, trick-so-far)          ; validated legal
              add card to trick; set HeartsBroken? if a heart was dumped
          Winner ← highest card of led suit (Trick.Winner)
          Trick → each player                            ; optional notification
          Lead ← Winner
      Deal.SetScore: tally hearts + Maggie per player; apply shoot-the-moon rule
      Results → each player                              ; optional notification
      Game.Update: fold deal scores into game scores
Winner(s) ← lowest game score
```

The loop is purely mechanical/deterministic — no game knowledge lives here. All intelligence is
in the players.

---

## 6. Players

Each kind is defined by how it answers the six messages. (Creation dispatch: `H.MakePlayer`,
line ~170, maps the UI choices `EP/CP/HP/CLOWN` to concrete players; the dispatch `Type` is
`Lisp` for Clown/Conservative/Human, `Kee` for Expert, `Net` for a remote proxy.)

- **Clown** (`CLOWN.*`, `Type=Lisp`). Passes 3 random cards; plays a random legal card. The
  baseline for testing the house and other players.
- **Conservative** (`CP.*`, `Type=Lisp`). A pure *minimizer* encoded as long `if…elseif…` chains
  (`CP.Think`, `CP.Lead`, `CP.Follow`, `CP.PassOut`…). No memory across tricks, no opponent
  modeling — yet plays a "pretty good" game (overview §3.2.2). All of its knowledge was later
  re-expressed as Expert rules.
- **Human** (`HP.*`, `Type=Lisp`). A windowed interface: the user's hand is drawn; the user
  mouses cards to pass and play; legal cards can be highlighted. Uses the same six messages, but
  the method bodies drive UI and wait for input (`HP.WaitForReady`, `HP.ChooseSomeCards`).
- **Expert** (`EP.*` + KEE units, `Type=Kee`). The expert system — see §8. Dispatched via
  `UNITMSG*` to a KEE unit rather than a Lisp function alist.

---

## 7. Card Table & UI

- **Card Table** (`CT.*`, lines ~490–560+): the shared game display — plays, tricks, and score
  (excluding the current deal). `CT.InformAll` is called after *every* `H.Apply`, so it is a pure
  **observer** of the message stream. `CT.All` holds the table; `CT.CurrentTrick` the trick view.
- **Open-hand utilities** (`Open.*`) and the **dealing UI** (`Dealer.*`) let a spectator or manual
  dealer see/arrange cards. Each computer player can run in *closed-hand* or *open-hand* mode
  (a window showing its hand + any messages it emits — the source of the annotated screenshots in
  `overview.md`).
- All UI is Interlisp-D windowing (`WINDOWPROP`, `MENU`, bitmaps, `ACTIVEREGIONS`). Ports replace
  this: Phase 2 keeps native Medley windows; Phases 3–4 use a web UI over the same message stream.

---

## 8. The Expert player (KEE)

Detailed in `overview.md` §4 and `transcription/kee-expert-rules.txt`. Summary for the ports:

- **Composite object:** an `expert.players` unit + a **History** unit (all cards played, per-suit
  high/low, equivalence classes), **three Opponent-Model** units (per opponent: are they shooting?
  which cards/voids are known?), plus **strategy** and **personality** units.
- **Rules:** 97 rules in 16 classes, evaluated by KEE **RuleSystem2 backward chaining**, ordered
  by an explicit `WEIGHT` slot (not premise count). Three top-level families:
  - **Passout rules** — choose the 3 cards to pass (per strategy).
  - **Play rules** — choose a card, split into *lead / follow / dump*.
  - **Evaluation rules** — *strategy determination* (Minimize / Shoot / Eclipse) and *opponent
    modeling* (EMYCIN-style **certainty factors** accumulating evidence that an opponent is
    shooting).
- **Strategies:** *Minimizing* (take few points), *Shooting* (take all 26), *Eclipsing* (stop a
  suspected shooter). Re-evaluated after the deal, after the pass, and after every trick.

**Revival implication (all phases):** KEE is proprietary and unavailable. The rules in
`kee-expert-rules.txt` are the *specification*. Phase 2b (Medley) runs them as written on
**KEELOOPS** ([medley/keeloops.lisp](medley/keeloops.lisp)): the KEE API subset the Expert uses,
on LOOPS objects, plus a small backward chainer with weights, unstructured facts and certainty
factors — its header documents the rule semantics precisely, which is the contract a port's
engine must honour (Phase 3 LISA / Phase 4 `experta`, or a port of the chainer itself). The `EP.*` helpers are already plain Interlisp and largely portable. Crucially, the
**core couples to the Expert at only 4 `UNITMSG`/`UNITMSG*` seams** — so Clown/Conservative/Human
run with no rules engine at all; the Expert can be added later.

---

## 9. Networking

- **Original:** players can live on different Xerox Dandelions. A local `Player` of `Type=Net`
  holds an `HN.Player` proxy (`HNP.Name`, `HNP.Host`); `H.Apply` forwards ops in `ResponseOps` via
  `REMOTEVAL` to `HNET.Apply` on the remote host (lines 437–443). Startup handshake is
  `HNET.Hello`/`HelloAgain`/`DoIWantToPlay?`/`GoodBye`; transport is the Interlisp `EVALSERVER`
  (remote-eval) over Xerox Ethernet (`ETHERHOSTNUMBER`, `NetHearts`). Harley believes this made it
  one of the first networked multiplayer games with AI players.
- **Revival reality (from `medley/MEDLEY-SETUP-NOTES.md`):** the PUP/XNS Ethernet stack behind
  `EVALSERVER` is effectively gone. **Phase 2 collapses the four-machine game into one Medley
  image with four `ADD.PROCESS` players** — the `Net` transport is simply not used; `Lisp`/`Kee`
  dispatch is unchanged. Phases 3–4 reintroduce real networking cleanly with WebSockets, keeping
  the same six-message protocol as the wire contract.

---

## 10. Mapping the architecture to each port

| Concern | Original (Interlisp) | Phase 2 (Medley) | Phase 3 (Common Lisp) | Phase 4 (Python) |
|---|---|---|---|---|
| Player dispatch | `H.Apply` + `Type`/`Mapping` | unchanged | CLOS generic fns per op | `Player` base class, methods per op |
| Records | `RECORD`/`DATATYPE` | unchanged | `defstruct`/`defclass` | `@dataclass` |
| `←` assignment | `←` (= `_`) | `←`→`_` load copy | n/a | n/a |
| Card Table | `CT.*` windows | native Medley windows | web UI (observer) | web UI (observer) |
| Networking | `EVALSERVER`/`REMOTEVAL` | **dropped**; 4 `ADD.PROCESS` | WebSocket | WebSocket |
| Expert rules | KEE RuleSystem2 | reimpl. backward-chainer | LISA / custom | `experta` / custom |
| UI toolkit | Interlisp-D windows | Interlisp-D windows | browser | browser |

**Invariant across all ports:** the six-message protocol (§4.1), the deterministic game loop (§5),
and the data model (§3). Everything else is substitutable.

---

## 11. Open questions / to verify in Phase 2

1. Does `hearts-core.lisp` load in Medley after the `←`→`_` conversion and annotation strip?
   (Authoritative test of the transcription.)
2. Exact contents of `H.PlayerMustOps` and `HNET.ResponseOps` (which ops are mandatory / expect a
   reply) — read from the loaded image.
3. Do the hard-coded window geometries/fonts render on a modern display, or need retuning?
4. Confirm the 4 `UNITMSG` seams are the *only* KEE coupling in the core (grep says yes).
5. Best-effort bitmap literals (`HIconBM`/`HShadowBM` etc.) — verify by rendering in Medley.
