# HEARTS — brief user manual

How to play the revived game once it's loaded in Medley. New to Medley? Start with the
**Getting Started** section of [dist/README.md](dist/README.md) first, then come back here.

## The goal (Hearts, in one paragraph)

Hearts is a trick-taking game for four. You want to *avoid* taking points: each **heart** is
1 point and the **Queen of Spades (Q♠)** is 13. A game is several hands; when any player crosses
the losing threshold the game ends and the **lowest** total score wins. Each trick, everyone
plays one card of the led suit if they can; highest card of the led suit takes the trick (and its
points) and leads the next.

## Starting a game

At the Interlisp Exec:

```
(LHearts '(HP CP CP CP))      ; the four seats, clockwise
```

Seat codes: **`HP`** = you (Human Player), **`CP`** = Conservative (a Lisp player running one fixed *minimizing* strategy — competent but non-adaptive),
**`CLOWN`** = Clown (plays a random legal card), **`EP`** = Expert (the 1986 KEE expert system,
revived on LOOPS — it picks a strategy, models its opponents, and switches strategy mid-hand). Mix
them however you like, e.g. `(LHearts '(HP EP CP EP))`.

The Expert needs one more file: load it with `(FILESLOAD CLIPBOARD ACTIVEREGIONS HEARTS EXPERT)`.
It also needs **LOOPS** ([github.com/Interlisp/loops](https://github.com/Interlisp/loops)), which
isn't part of the Medley release: clone it next to your `medley/` directory (as `loops/`, beside
`notecards/`) and EXPERT loads it for you. An Expert thinks for a second or two per move.

Handy options:

- `ThinkFlag?` — **on by default** in this revival build, so the Conservatives narrate their
  reasoning in "Thoughts of …" windows (great for watching them think, and for screenshots). To
  silence it, `(SETQ ThinkFlag? NIL)` before starting.
- `(LHearts Config Open? ManualDeal?)` — `Open?` T deals all hands face-up (for kibitzing);
  `ManualDeal?` T lets you deal by hand. Both default off. With `Open?` T each **Expert** gets a
  window whose top line narrates its reasoning, as it did in 1986: "My strategy is Shooting",
  the cards it passes and receives, and a reason for every play ("l2 of Hearts Leading a heart.
  What the hey." — `l`/`f`/`d` = lead, follow, dump).
- After a game, `(EP.PrintLastGameReasons 'histories)` writes each Expert's play-by-play reasons
  to a file named after it; `(SETQ KEE.Trace T)` prints every rule as it fires.

You'll be asked to type your name; a hand window titled **"Hearts Window for _you_"** opens.

## The windows you'll see

![A game in progress: the Hearts Card Table (center) with each player's score and tricks, "Hearts
Window for Harley" (top right) showing the hand grouped by suit with the Play/Pass/Score/LegalCards
menu, and a "Thoughts of …" window for each Conservative narrating its play.](docs/hearts-game.png)

- **Hearts Window for _you_** — your 13 cards, grouped in rows by suit (Clubs, Diamonds, Hearts,
  Spades). Along the top is a menu: **Play · Pass · Score · LegalCards**. You click cards here.
- **Hearts Card Table** — the four seats around the table. Under each name, **`S:`** is that
  player's score (points taken) and **`T:`** is tricks taken this hand. Cards played to the
  current trick appear in the middle.
- **Prompt Window** — short messages ("Your turn, _you_", "Illegal card. Try again.", "Pass noted.").
- **Thoughts of _name_** — a Conservative's running commentary (shown while `ThinkFlag?` is `T`, the default).

## Passing (start of each hand)

Before the play, every hand you pass **3 cards**. The direction rotates each hand:
**Left → Across → Right → (hold, no pass) →** repeat.

1. Click **3 cards** to select them (a selected card is shaded).
2. Click **Pass** in the menu. ("Pass noted.")

Click a shaded card again to unselect it if you change your mind.

## Playing a trick

When the Prompt Window says **"Your turn, _you_"**:

1. Click **one** card to select it.
2. Click **Play**.

Rules the game enforces for you:

- The **2♣** must lead the very first trick.
- You must **follow the led suit** if you hold it.
- You can't **lead hearts** until hearts are "broken" (someone has discarded one).

If you pick an illegal card you'll see **"Illegal card. Try again."** — the selection clears and
you choose again. Not sure what's legal? Click **LegalCards** to highlight your legal plays.

The **Score** button just acknowledges ("Score noted") — read the real scores off the card table.

## Ending & replaying

The game plays hand after hand until someone reaches the losing score; then the lowest score wins.
To play again, just call `(LHearts …)` again — the previous card table now closes itself
automatically (older builds stacked a new one on top; see [HEARTS-BUGS.md](HEARTS-BUGS.md) U2).

To leave Medley entirely: `(IL:LOGOUT)` at the Exec.

## Tips

- Watch a `(LHearts '(CP CP CP CP))` game play itself (thought windows on by default) — a good way
  to learn the Conservatives' style before you sit down against them.
- The dreaded **Q♠** is worth 13 — shedding it on someone else is the whole game.
