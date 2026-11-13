# HEARTS — brief user manual

How to play the revived game once it's loaded in Medley. New to Medley? Start with the
**Getting Started** section of [dist/README.md](dist/README.md) first, then come back here.

## The goal (Hearts, in one paragraph)

Hearts is a trick-taking game for four. You want to *avoid* taking points: each **heart** is
1 point and the **Queen of Spades (Q♠)** is 13. A game is several hands; when any player crosses
the losing threshold the game ends and the **lowest** total score wins. Each trick, everyone
plays one card of the led suit if they can; highest card of the led suit takes the trick (and its
points) and leads the next.

## Starting a game — the easy way: `PlayHearts`

```
(FILESLOAD PLAYHEARTS)
(PlayHearts)
```

`PlayHearts` asks, with pop-up menus, who sits in each of the four seats (you, an Expert, a
Conservative or a Clown), whether to play with open hands, whether to deal by hand, and — if there
are Conservatives or Experts — whether to show their thoughts; a human is asked for a name in the
prompt window. With hands closed, each Expert then gets its own **"Thoughts of …" window** (like
the Conservatives'), where it narrates in its own 1986 words without showing its cards: its
strategy ("My strategy is Shooting", "New strategy is: Minimizing"), the cards it passes and
receives, a reason for every play ("l2 of Hearts Leading a heart. What the hey." — `l`/`f`/`d` =
lead, follow, dump), and its hunches ("I think the player to my right is shooting.").
Then the card table opens with a **menu bar: Start Game · Setup… · Tidy · Exit**. Nothing happens until
you choose **Start Game**; the game runs in its own process, so the Exec stays free. When it ends,
the winner is announced in the prompt window and you can **Start Game** again (a fresh table, same
players, same place), **Setup…** to change players, or **Exit** — which stops a game in progress
and closes every Hearts window. Closing the card table does the same.

You don't place the windows yourself: the card table opens in the middle of the screen, and each
player's windows go next to their seat. Player 1 sits at the top of the table, 2 on the right, 3 at
the bottom, 4 on the left. A player's hand window goes beside their side of the table, and their
Thoughts window in the next corner clockwise; a player with only a Thoughts window has it beside
the table. A Thoughts window is made smaller if the screen is too small for it, and the windows at
the top stay clear of the prompt window; they can cover the Exec. If you move windows around,
**Tidy** puts them back. To place every window yourself, as in 1986, `(SETQ PH.AutoPlace? NIL)`
before `(PlayHearts)`.

Every computer player says what it is thinking in its own Thoughts window, whatever kind it is.
With open hands, the 1986 Expert and Conservative printed their reasoning in a strip above their
hand window instead; `PlayHearts` sends it to their Thoughts window, so a hand window shows only
cards. (The 1986 `LHearts` still uses the strips.) The Expert and the Conservative clear their
Thoughts window at each new deal.

You can skip the questions: `(PlayHearts '(HP EP EP CP) T)` — players, then open hands, then
manual deal, as for `LHearts`. `PLAYHEARTS` loads HEARTS if needed, and EXPERT when you choose an
Expert. It is a 2026 addition; the 1986 entry point, `LHearts`, is described next.

## Playing against an LLM (`LP`)

Seat code **`LP`** is a player that asks an LLM for each pass and play: Claude by default, or another
hosted or local model (see [Using another model](#using-another-model)). It sees only what its seat
would see, works out a plan, and explains each move in its **"Thoughts of…" window**. Choose **LLM
player** in the `PlayHearts` menu, or give the seat code directly:

```
(FILESLOAD PLAYHEARTS)
(PlayHearts '(HP LP EP CP))
```

**It costs real money, and each move takes as long as the model takes.** A game is roughly 100–140
decisions per LLM seat (a rough estimate is a few dollars per seat per game on Opus; on Haiku at low effort, one deal
measured about $0.006 and 5 seconds a move). A seat with only one legal card makes no API call. `(LP.Stats)` shows the decisions and tokens so far.

If anything goes wrong (no key, no network, an unusable answer), the game carries on: the seat plays
a safe legal card, the lowest for a play and the highest three for a pass, and says why in its
Thoughts window and the prompt window. The count is in `(LP.Stats)` as `fallbacks`.

### Setting it up

1. **Install the Anthropic SDK** for Python 3:

   ```bash
   pip install anthropic
   ```

   If the `python3` Medley finds isn't the one you installed it into, give the full path:
   `(SETQ LP.Python "/full/path/to/python3")`.

2. **Copy the files** `dist/LLMPLAYER` and `dist/llm_player.py` to `~/il` with the others, or set
   `LP.Helper` to the full path of `llm_player.py`.

3. **Provide your API key.** There is no `.env` file: the helper reads environment variables. Either
   export the key in the shell you launch Medley from, before you launch it:

   ```bash
   export ANTHROPIC_API_KEY=...
   ```

   or keep it in a private file outside this repository and have each helper call read it, which
   needs no restart and leaves your shell's environment alone. Put the key in
   `~/.config/hearts/anthropic-key`, make that file readable only by you
   (`chmod 600 ~/.config/hearts/anthropic-key`), then at the Exec:

   ```
   (SETQ LP.Python "ANTHROPIC_API_KEY=$(cat ~/.config/hearts/anthropic-key) python3")
   ```

4. **Check it,** which spends nothing:

   ```
   (FILESLOAD LLMPLAYER)
   (LP.Check)
   ```

   It returns `(CHECK python sdk keySet? model)`. `keySet?` is `T` if a key or token is set; it
   doesn't prove the key is valid. A bad key shows up on the first move, as a fallback whose reason
   is in the Thoughts window.

To try the whole path for free first, `(SETQ LP.HelperOptions "--stub lowest")` makes the seat play
its first legal card without calling the API. Set it back with `(SETQ LP.HelperOptions "")`.

### Settings

Set these with `SETQ` at the Exec, before or after loading `LLMPLAYER`. They take effect on the next
move, except `LP.Thoughts?`, which applies to new players. They last for the Medley session.

| Variable | Default | Meaning |
|---|---|---|
| `LP.Provider` | `"anthropic"` | Which kind of API: `"anthropic"` or `"openai"` (see below) |
| `LP.Model` | `"claude-opus-5-5"` | Which model; e.g. `"claude-haiku-5-5"` is far cheaper |
| `LP.Effort` | `"medium"` | `"low"`, `"medium"`, `"high"`, `"xhigh"` or `"max"`: how hard it thinks; more is slower and costs more. Only for `"anthropic"` |
| `LP.TimeoutSeconds` | `300` | How long a move may take before it plays safe |
| `LP.GraceSeconds` | `15` | Extra time Medley waits for the helper's answer beyond that |
| `LP.Python` | `"python3"` | The command that runs Python; can start with `NAME=value` settings, as in step 3 |
| `LP.Helper` | `NIL` | Full path of `llm_player.py`; `NIL` looks beside the loaded files |
| `LP.HelperOptions` | `""` | Extra options for the helper, such as `"--stub lowest"` |
| `LP.LogFile` | `NIL` | A file path to record every request and reply as JSON lines |
| `LP.TempDir` | `"/tmp"` | Where the request files are written |
| `LP.Thoughts?` | `T` | Whether a new LLM player gets a Thoughts window |

### Using another model

`LP.Provider` says which kind of API to speak. Set the variables below as in step 3: in the shell you
launch Medley from, or at the front of `LP.Python`.

**OpenAI, or any server with an OpenAI-compatible API** (`/v1/chat/completions`). Install its SDK with
`pip install openai`, then:

| Variable | Meaning |
|---|---|
| `OPENAI_API_KEY` | The key, sent as `Authorization: Bearer`. A server of your own may not need one |
| `OPENAI_BASE_URL` | The server's address, usually ending in `/v1`: requests go to `<address>/chat/completions`. Leave it unset for OpenAI itself |

```
(SETQ LP.Provider "openai")
(SETQ LP.Model "name-of-the-model")
(SETQ LP.Python "OPENAI_BASE_URL=https://llm.example.com/v1 OPENAI_API_KEY=$(cat ~/.config/hearts/llm-key) python3")
```

You have to set `LP.Model`, because the default is a Claude model. For example, a model on your own
machine through Ollama, which costs nothing and needs no key:

```
(SETQ LP.Provider "openai")
(SETQ LP.Model "mistral:latest")
(SETQ LP.Python "OPENAI_BASE_URL=http://127.0.0.1:11434/v1 python3")
```

The helper asks for structured output. If the server rejects that, it asks again without it, and it
accepts JSON wrapped in `<think>` reasoning or a code fence. It sends no token limit and no effort,
because servers disagree about those, so `LP.Effort` has no effect here. Two things to watch:

- **A small or local model may be weak or slow.** Raise `LP.TimeoutSeconds` if moves time out.
- **Ollama's context window can be as small as 2048 tokens,** and a request late in a deal comes close
  to that. A larger one is set on the Ollama side.

**A server that speaks the Anthropic API,** such as a company gateway or a proxy. Leave `LP.Provider`
as `"anthropic"`, and use:

| Variable | Meaning |
|---|---|
| `ANTHROPIC_BASE_URL` | The server's address, without `/v1`: requests go to `<address>/v1/messages` |
| `ANTHROPIC_API_KEY` | A key sent as the `x-api-key` header |
| `ANTHROPIC_AUTH_TOKEN` | Instead of a key, a token sent as `Authorization: Bearer` |

```
(SETQ LP.Python "ANTHROPIC_BASE_URL=https://llm.example.com ANTHROPIC_AUTH_TOKEN=$(cat ~/.config/hearts/gateway-token) python3")
(SETQ LP.Model "name-of-the-model")
```

Unlike the OpenAI path, this one has no way around a server that lacks a feature. The server has to
accept `thinking: {"type": "adaptive"}` and `output_config`, with `effort` and a `json_schema` format.
For the model names `claude-opus-5-5`, `claude-opus-5`, `claude-sonnet-5-5` and `claude-fable-5-1` it
also has to accept the beta endpoint with a `fallbacks` field.

Whichever you use, a server that fails doesn't stop the game: each move becomes a fallback, with the
server's error in the Thoughts window. Amazon Bedrock and Google Vertex aren't supported through
their own SDK clients.

## Playing against a neural network (`NP`)

Seat code **`NP`** is a neural network that runs entirely in Interlisp: no Python, no API and no cost
per move. It was trained outside Medley by playing millions of deals against itself, then its weights
were copied into the file `HEARTSNET`. Against three Experts it took about 3 points per deal fewer than
an Expert in the same seat, over 2,800 test deals, largely by shooting the moon more often. Choose
**Neural network** in the `PlayHearts` menu, or:

```
(FILESLOAD PLAYHEARTS)
(PlayHearts '(HP NP EP CP))
```

Copy `dist/NNPLAYER` and `dist/HEARTSNET` to `~/il` with the other files, or set `NP.ModelFile` to the
full path of the weights. Its **"Thoughts of Neural…" window** shows each decision as the network's
preference among the legal cards, such as `play: D9 71% DK 20% D3 9%`. Those shares are all it can
tell you: unlike the Expert or the LLM, it has no reasons to give. `(SETQ NP.Thoughts? NIL)` turns the
window off for new players, and `(NP.Stats)` shows the moves made and the time they took.

## Playing over the network (`HNET`)

In 1986 the players could sit at different machines: the house ran the game and asked the other
machines for their players' moves. `HNET` brings that back between Medleys anywhere, through a
relay that every machine dials out to (`medley/hnetrelay.py`, on a server both can reach). The
machines meet in a *room*, whose name you share like an invitation. The 1986 network code itself is
unchanged.

Copy `dist/HNET` and `dist/hnetlink.py` to `~/il` (Python 3 is all the link needs). On each machine:

```
(FILESLOAD HEARTS HNET)
(HNET.Connect "ourgame" "bob" "wss://relay.example.org")    ; a room, your name, the relay
```

Then the guest offers players and the house starts a game with fewer than four. The rest come from
the net, and anything still missing is filled with Conservatives:

```
(NetHearts (LIST (CP.Create) (HP.Create)))      ; on the guest: offer a Conservative and yourself
(Hearts (LIST (HP.Create) (CP.Create)))         ; on the house: seats 1 and 2 here, 3 and 4 from the net
```

The guest gets a card table of its own, and its players' windows open there. So far this has been
tested with Conservatives on both machines; a person at each one is the next thing to try. `(HNET.Disconnect)`
leaves the room. A machine answers only the calls the game makes (`HNET.Allowed`), never an
arbitrary form. For how it works, the gotchas and a general guide to networking in today's Medley,
see [docs/medley-networking.md](docs/medley-networking.md).

There is always someone to play online: the **resident Medley** on the demo server, in room
`athena`, offers an Expert, the neural network and a Conservative. In `PlayHearts`, choose **The
resident (online)** for a seat, and it plays that seat and the rest; or `(PlayHearts '(HP NET))`.
You can watch its screen in a browser. See [docs/medley-server.md](docs/medley-server.md).

## Starting a game — the 1986 way: `LHearts`

At the Interlisp Exec:

```
(LHearts '(HP CP CP CP))      ; the four seats, clockwise
```

Seat codes: **`HP`** = you (Human Player), **`CP`** = Conservative (a Lisp player running one fixed *minimizing* strategy — competent but non-adaptive),
**`CLOWN`** = Clown (plays a random legal card), **`EP`** = Expert (the 1986 KEE expert system,
revived on LOOPS — it picks a strategy, models its opponents, and switches strategy mid-hand), **`LP`** =
an LLM over an API, Claude by default (load `LLMPLAYER`; see above), **`NP`** = a neural network in pure Lisp (load `NNPLAYER`; see above). Mix
them however you like, e.g. `(LHearts '(HP EP CP EP))`.

The Expert needs one more file: load it with `(FILESLOAD CLIPBOARD ACTIVEREGIONS HEARTS EXPERT)`.
It also needs **LOOPS** ([github.com/Interlisp/loops](https://github.com/Interlisp/loops)), which
isn't part of the Medley release: clone it next to your `medley/` directory (as `loops/`, beside
`notecards/`) and EXPERT loads it for you. On a current Mac the Experts play without a noticeable pause
(the 1986 Dandelion took about fifteen seconds a move).

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
`LHearts` then **starts another game with the same players, and keeps doing so** — it never returns
(each finished game is saved on `H.GameList`). To stop, interrupt it: **Ctrl-E** aborts back to the
Exec prompt (Ctrl-D resets). Each new game closes the previous card table automatically (older
builds stacked a new one on top; see [HEARTS-BUGS.md](HEARTS-BUGS.md) U2).

To leave Medley entirely: `(IL:LOGOUT)` at the Exec.

## Tips

- Watch a `(LHearts '(CP CP CP CP))` game play itself (thought windows on by default) — a good way
  to learn the Conservatives' style before you sit down against them.
- The dreaded **Q♠** is worth 13 — shedding it on someone else is the whole game.
