# The house and the resident Medley on apps.athenadecisions.com

HEARTS is played at **tables of the house**: the web platform (`backend/hearts`), which deals, keeps
the score and records every game. People sit at a table from a browser. Medleys bring players to
the same tables over Courier (`medley/hcourier.lisp`), through the house's NetHub.

Two services in `docker-compose.server.yml` matter here:

- **The house** (`backend`): the web platform, and on port 3333 the **NetHub** that Medleys
  connect to. On that hub the house speaks two Courier programs and nothing else
  ([docs/medley-networking.md](medley-networking.md), "HEARTS on Courier").
- **The resident Medley** (`medley`, docker/resident.lisp): a Medley that keeps offering three
  players to the house (an Expert, the neural network and a Conservative, the 1986 code running
  on Medley). Anyone opening a table can take them as opponents. Its screen is on the web, to
  watch or to control.
The 1986 way of playing between machines (`HNET`, a relay and remote evaluation of the game's own calls) was retired on 2026-11-14; it is kept at git tag `revival-1986`.

| What | Where |
|---|---|
| Play from a browser | https://apps.athenadecisions.com/hearts/ |
| The NetHub, for `medley --nethub` | `apps.athenadecisions.com:3333` |
| Watch the resident (view only, public) | https://apps.athenadecisions.com/hearts/medley/watch/ |
| Control the resident (login) | https://apps.athenadecisions.com/hearts/medley/control/ |

## Playing the resident's players from a browser

Start a game, and choose **Expert on Medley**, **Neural network on Medley** or **Conservative on
Medley** for a seat. They are in the seat menus while the resident is free. Each move is then made
on the resident Medley, and you can watch it think on the watch page.

**One game at a time.** While its players are at a table they are not in the menus. If someone
takes them just before you, the lobby says so and shows who can be chosen now. The house's own
Expert is the same 1986 rules in Python and is always there.

## Playing from your Medley

Your Medley needs an emulator with NetHub support: the released ones have none.
`./hearts.sh maiko-nethub` builds one beside your Medley release, which it leaves as it is. Then
`./hearts.sh medley` copies the HEARTS files to `~/il` and starts Medley on the house's NetHub. At
the Exec:

```
(FILESLOAD PLAYHEARTS)
(PlayHearts)
```

Choose yourself for seat 1, then **Online (the house's players)** for seat 2. Start Game opens a
table at the house: your players sit in the first seats, and the house fills the rest with the
resident's players if they are free, or with its own Experts. `(PlayHearts '(HP NET))` does the same
without the menus. Exit leaves the table.

Without PlayHearts:

```
(FILESLOAD HEARTS HCOURIER)
(HC.Opponents)                                              ; who the house can seat now
(HC.NewTable (LIST (HP.Create)) '("expert" "network" "person"))  ; you, two of the house's, a seat left open
(HC.Tables)                                                 ; tables waiting for players
(HC.Sit (LIST (HP.Create)) "the-table's-name")              ; a seat at one of them
(HC.Leave)
```

A seat left open (`"person"`) can be taken by someone in a browser, or by another Medley with
`HC.Sit`. The game starts when the last seat is taken.

Starting Medley by hand: `medley --maikodir ~/medley-260810/maiko-nethub --nethub
apps.athenadecisions.com:3333:10-00-AA-BB-CC-DD` (any address of your own after the port).

## Using the control screen

Click a window to type into it. Any keyboard layout works: on a French keyboard, `(` and `)`
reach Medley as they would from a US one.

**To paste from your computer:** noVNC can't read your computer's clipboard, so Cmd-V on the
screen finds nothing ("Error: target STRING not available"). The text has to go through noVNC's
own box:
1. Copy the text on your computer as usual.
2. Open noVNC's side panel (the small tab at the left edge) and choose the clipboard
   (Presse-papiers in French).
3. Paste into its box with Cmd-V, and close the panel.
4. Click on Medley's screen, so the keyboard goes back to Medley.
5. Press Option-V (Alt-V, Medley's Meta-V) where the text should go.

Text Medley copies (Meta-C in SEdit) appears in that same box, to copy from.

## Deploying

On the server, in the checkout, `./hearts.sh deploy prod` pulls, rebuilds and restarts
everything: the house, the web pages and the resident Medley. Then it checks their
health. The first build takes several minutes, because it compiles the emulator.

Once, for the Courier game:

1. Set a key in the server's `.env`, so that only the resident can offer players to everyone:

   ```
   HEARTS_OFFER_KEY=some-long-random-text
   ```

2. Open port 3333 to the Internet, in the server's firewall and in the hosting provider's, if it
   has one. For `ufw`:

   ```bash
   sudo ufw allow 3333/tcp
   ```

Once, for the web addresses (run it again after any change to `nginx/hearts-apps-location.conf`):

1. Make the control login (run it again to add someone):

   ```bash
   ./hearts.sh control-login harley
   ```

   It writes `/etc/nginx/hearts-medley.htpasswd` with `htpasswd`, from `apache2-utils`.
2. Add the game's and the resident's addresses to nginx:

   ```bash
   ./hearts.sh nginx-install
   ```

   This puts the part of `nginx/hearts-apps-location.conf` between its `hearts` markers (the game's
   page, its API and health address, and the resident's two screens) at the end of the
   `apps.athenadecisions.com` server block that listens on 443 (certbot's). It replaces an earlier
   copy, keeps a dated backup of the site file, runs `nginx -t`, and reloads, or puts the old file
   back if the test fails. It refuses if the site has `/hearts/` addresses pasted in by hand. The
   site file is `/etc/nginx/sites-enabled/apps.athenadecisions.com`; set `NGINX_SITE` if yours is
   elsewhere.

The resident takes a minute or two to start, because loading the Expert brings in LOOPS.
`./hearts.sh health prod` checks the house and both screens, and says whether the
resident is offering players. `./hearts.sh resident-logs prod` shows the resident's log.
Locally, `./hearts.sh start dev` runs the house with its NetHub on this computer (port 3333,
local only), and `./hearts.sh resident dev` adds a resident beside it.

## How it's put together

- **The house's NetHub** is in the backend's own process (`backend/hearts/courier.py`), opened when
  `HEARTS_NETHUB_PORT` is set. Each Medley holds one TCP connection to it. A Medley's players are
  seats of kind `medley` at a table. The table tells the Medley every event its seats may see and
  asks it for their passes and cards. If the Medley goes away, answers with a card it may not play,
  or doesn't answer for 15 minutes (`HEARTS_MEDLEY_ANSWER_WITHIN`), a Conservative of the house's
  plays the seat from then on, so a game never waits for a machine that has gone.
- **The image** is the `resident` stage of `docker/Dockerfile`: the headless test image's Medley,
  with the emulator rebuilt for NetHub, plus `x11vnc`, `novnc` and `websockify`, running as an
  ordinary user.
- **`docker/resident-run`** starts Xvfb, two VNC servers on that display (view-only on 5901, full
  on 5900, both local to the container), and noVNC for each: 6080 to watch, 6081 to control. It
  waits for the NetHub to answer, starts Medley on it, and starts it again if it stops.
  - The VNC servers skip Xvfb's extra `(` and `)` keys (keycodes 187 and 188), which Medley
    ignores. Without that, parentheses typed through the browser were lost.
  - `autocutsel` keeps the X selections and the cut buffer in step. x11vnc uses only the cut
    buffer, while Medley pastes and copies through `xclip`.
- **`docker/resident.lisp`** loads `dist/` (mounted read-only), turns the Exec's page hold off,
  places windows itself (the players' Thoughts windows beside the card table, the Exec under it;
  the closed-hand Expert gets its Thoughts window as in PlayHearts), and runs a process that keeps
  offering players: after each game, and after 20 minutes of a game in which nothing happens.
  The emulator joins the hub only as it starts, so when the house stops answering (a deploy), the
  resident logs out after three tries and `resident-run` starts it again.
  Settings in the server's `.env`: `HEARTS_OFFER_KEY`, and `RESIDENT_PLAYERS` (e.g. `EP NP CP`).
- Ports 8052 (watch) and 8053 (control) are published on 127.0.0.1 only, so nginx is
  the only way in. Port 3333 (the NetHub) is published to the Internet: it is XNS in TCP, which
  nginx's web server can't carry.

## Security

- **The NetHub is open to the Internet.** Anyone can connect a machine to it. What they reach is
  the house's two Courier programs: they can open a table, sit players at an open table whose name
  they know (the list they can ask for leaves out tables by invitation), and leave. Unlike a
  person in a browser, a Medley needs no account. They can't reach another Medley on the hub,
  because the house passes no frame from one machine to another. Names are stripped to plain
  characters, and messages and sequences are bounded. At most 64 machines are connected at once,
  8 from one address, and a machine opens at most 12 tables an hour. The traffic is not
  encrypted: cards and moves cross the Internet in the clear.
- **Only a machine with the key offers players to everyone.** Without `HEARTS_OFFER_KEY` on the
  server, any Medley could put players in everyone's seat menus under any name.
- **Control is a full Lisp.** Whoever controls the resident can run shell commands in its
  container, so give the login only to people you trust. The container holds no secrets but the
  offer key (no API keys, no `.env`), mounts only `dist/` read-only, runs as a non-root user with
  no Linux capabilities, and is limited to 1 GB. It can still reach the network.
- **Watching shows the resident's Thoughts windows.** A visitor who also watches can read what the
  Expert, the Conservative and the network are thinking, so this is a demo, not a tournament.

## Testing it locally

`tests/run-resident.sh` builds and starts the house and the resident under another project name.
A visitor from the web takes the resident's three players and plays them twice
(`tests/resident_visitor.py`), then a visitor Medley plays them through PlayHearts
(`tests/resident-visitor.lisp`). While it runs, the resident's screen is at
http://localhost:8052/vnc.html (control: :8053). `--keep` leaves the services running afterwards;
stop them with `docker compose -p hearts-resident-test -f docker-compose.server.yml down`.
`--web-only` skips the Medley visitor, whose game to 100 takes much longer.
