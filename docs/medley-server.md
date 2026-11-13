# The Medley server on apps.athenadecisions.com

Two services in `docker-compose.server.yml` put the 1986 network game on the demo server:

- **The relay** (`relay`, medley/hnetrelay.py): Medleys anywhere meet there. It passes messages
  between the machines in a room and evaluates nothing.
- **The resident Medley** (`medley`, docker/resident.lisp): a Medley that is always in room
  `athena`, offering three players (an Expert, the neural network and a Conservative). Anyone with
  a Medley can play it. Its screen is on the web, to watch or to control.

| What | Where |
|---|---|
| Relay, for `HNET.Connect` | `wss://apps.athenadecisions.com/hearts` |
| Watch the resident (view only, public) | https://apps.athenadecisions.com/hearts/medley/watch/ |
| Control the resident (login) | https://apps.athenadecisions.com/hearts/medley/control/ |

## Playing the resident from your Medley

`./hearts.sh medley` copies the HEARTS files to `~/il` and starts Medley. Then, at the Exec:

```
(FILESLOAD PLAYHEARTS)
(PlayHearts)
```

Choose yourself for seat 1, then **The resident (online)** for seat 2: the resident plays seats 2
to 4. `(PlayHearts '(HP NET))` does the same without the menus. Start Game claims the resident's
players for each game, and Exit lets it go and leaves the room. Your name in the room is your login
name; `PH.NetRoom` and `PH.NetRelay` say where the resident is.

The same, the 1986 way, without PlayHearts:

```
(FILESLOAD HEARTS HNET)
(HNET.Connect "athena" "yourname" "wss://apps.athenadecisions.com/hearts")
(SETQ Me (HP.Create))
(ADD.PROCESS '(Hearts (LIST Me)))
```

You are seat 1, and the resident's three players take seats 2 to 4. Its card table shows the game
too, so others can watch. When a game ends, the resident offers fresh players a few seconds later.
It also offers fresh players when the house leaves the room, or after 20 minutes with no move.

**One game at a time.** If someone else is already playing it, the resident answers no, and your
missing seats are filled with Conservatives on your own machine. Two people can also play each
other through the relay: use a room of your own, as in the USER-MANUAL's "Playing over the
network".

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
everything: the web platform, the relay and the resident Medley. Then it checks their health.
To start or restart only the relay and the resident:

```bash
./hearts.sh resident prod
```

Then, once:

1. Make the control login (run it again to add someone):

   ```bash
   ./hearts.sh control-login harley
   ```

   It writes `/etc/nginx/hearts-medley.htpasswd` with `htpasswd`, from `apache2-utils`.
2. Add the new locations to nginx:

   ```bash
   ./hearts.sh nginx-install
   ```

   This puts the part of `nginx/hearts-apps-location.conf` between its `hearts-medley` markers
   (`/hearts/hnet/` and `/hearts/medley/...`) into the site's server block. It goes just before
   `location ^~ /hearts/ {` if the web platform is already served there. Otherwise it goes at
   the end of the `apps.athenadecisions.com` block that listens on 443 (certbot's). It keeps a dated backup of the site file, runs `nginx -t`,
   and reloads, or puts the old file back if the test fails. Running it again after a change to
   those locations replaces its earlier copy. The site file is
   `/etc/nginx/sites-enabled/apps.athenadecisions.com`; set `NGINX_SITE` if yours is elsewhere.

The resident takes a minute or two to start, because loading the Expert brings in LOOPS.
`./hearts.sh health prod` checks the relay and both screens, and says whether the resident is in
its room yet. `./hearts.sh resident-logs prod` shows machines joining and leaving rooms. Locally,
`./hearts.sh resident dev` runs the same two services on this computer.

## How it's put together

- **The image** is the `resident` stage of `docker/Dockerfile`: the headless test image's Medley
  plus `x11vnc`, `novnc` and `websockify`, running as an ordinary user. The relay runs in the same
  image with a different entrypoint.
- **`docker/resident-run`** starts Xvfb, two VNC servers on that display (view-only on 5901, full
  on 5900, both local to the container), and noVNC for each: 6080 to watch, 6081 to control. It
  then starts Medley, and starts it again if it stops.
  - The VNC servers skip Xvfb's extra `(` and `)` keys (keycodes 187 and 188), which Medley
    ignores. Without that, parentheses typed through the browser were lost.
  - `autocutsel` keeps the X selections and the cut buffer in step. x11vnc uses only the cut
    buffer, while Medley pastes and copies through `xclip`.
- **`docker/resident.lisp`** loads `dist/` (mounted read-only), turns the Exec's page hold off,
  places windows itself (the players' Thoughts windows beside the card table, the Exec under it;
  the closed-hand Expert gets its Thoughts window as in PlayHearts), joins the room, and runs a
  process that keeps offering players. Settings:
  `RESIDENT_ROOM`, `RESIDENT_NAME`, `RESIDENT_PLAYERS` (e.g. `EP NP CP`) in the server's `.env`.
- Ports 8051 (relay), 8052 (watch) and 8053 (control) are published on 127.0.0.1 only, so nginx is
  the only way in.

## Security

- **Control is a full Lisp.** Whoever controls the resident can run shell commands in its
  container, so give the login only to people you trust. The container holds no secrets (no API
  keys, no `.env`), mounts only `dist/` read-only, runs as a non-root user with no Linux
  capabilities, and is limited to 1 GB. It can still reach the network.
- **Watching shows the resident's Thoughts windows.** A visitor who also watches can read what the
  Expert, the Conservative and the network are thinking, so this is a demo, not a tournament.
- **The relay's only access control is the room name.** A machine evaluates only the game's own
  calls (`HNET.Allowed`), so a stranger in a room can't run code. They could disrupt a game,
  though, and the relay has no rate limits yet.

## Testing it locally

`tests/run-resident.sh` builds and starts the two services under another project name, then
plays a visitor Medley against the resident twice. While it runs, the resident's screen is at
http://localhost:8052/vnc.html (control: :8053). `--keep` leaves the services running afterwards;
stop them with `docker compose -p hearts-resident-test -f docker-compose.server.yml down`.
