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

Put `HEARTS`, `ACTIVEREGIONS`, `HNET` and `hnetlink.py` from `dist/` in `~/il`. Then, at the Exec:

```
(FILESLOAD HEARTS HNET)
(HNET.Connect "athena" "yourname" "wss://apps.athenadecisions.com/hearts")
(SETQ Me (HP.Create))
(ADD.PROCESS (LIST (QUOTE Hearts) (KWOTE (LIST Me))))
```

You are seat 1, and the resident's three players take seats 2 to 4. Its card table shows the game
too, so others can watch. When a game ends, the resident offers fresh players a few seconds later.
It also offers fresh players when the house leaves the room, or after 20 minutes with no move.

**One game at a time.** If someone else is already playing it, the resident answers no, and your
missing seats are filled with Conservatives on your own machine. Two people can also play each
other through the relay: use a room of your own, as in the USER-MANUAL's "Playing over the
network".

## Deploying

On the server, in the checkout:

```bash
git pull
docker compose -f docker-compose.server.yml up -d --build relay medley
```

Then, once:

1. Paste the new locations from `nginx/hearts-apps-location.conf` (`/hearts/hnet/` and
   `/hearts/medley/...`) into the `apps.athenadecisions.com` server block.
2. Make the control login:

   ```bash
   sudo htpasswd -c /etc/nginx/hearts-medley.htpasswd harley
   ```

   `htpasswd` is in `apache2-utils`.
3. Reload nginx:

   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```

The resident takes a minute or two to start: loading the Expert brings in LOOPS. Its status window
at the top of the screen says when it is waiting for a game. `docker compose -f
docker-compose.server.yml logs -f relay` shows machines joining and leaving rooms.

## How it's put together

- **The image** is the `resident` stage of `docker/Dockerfile`: the headless test image's Medley
  plus `x11vnc`, `novnc` and `websockify`, running as an ordinary user. The relay runs in the same
  image with a different entrypoint.
- **`docker/resident-run`** starts Xvfb, two VNC servers on that display (view-only on 5901, full
  on 5900, both local to the container), and noVNC for each: 6080 to watch, 6081 to control. It
  then starts Medley, and starts it again if it stops.
- **`docker/resident.lisp`** loads `dist/` (mounted read-only), turns the Exec's page hold off,
  places windows itself, joins the room, and runs a process that keeps offering players. Settings:
  `RESIDENT_ROOM`, `RESIDENT_NAME`, `RESIDENT_PLAYERS` (e.g. `EP NP CP`) in the server's `.env`.
- Ports 8051 (relay), 8052 (watch) and 8053 (control) are published on 127.0.0.1 only, so nginx is
  the only way in.

## Security

- **Control is a full Lisp.** Whoever controls the resident can run shell commands in its
  container, so give the login only to people you trust. The container holds no secrets (no API
  keys, no `.env`), mounts only `dist/` read-only, runs as a non-root user with no Linux
  capabilities, and is limited to 1 GB. It can still reach the network.
- **Watching shows the resident's Thoughts windows.** A visitor who also watches can read what the
  Conservative and the network are thinking, so this is a demo, not a tournament.
- **The relay's only access control is the room name.** A machine evaluates only the game's own
  calls (`HNET.Allowed`), so a stranger in a room can't run code. They could disrupt a game,
  though, and the relay has no rate limits yet.

## Testing it locally

`tests/run-resident.sh` builds and starts the two services under another project name, then
plays a visitor Medley against the resident twice. While it runs, the resident's screen is at
http://localhost:8052/vnc.html (control: :8053). `--keep` leaves the services running afterwards;
stop them with `docker compose -p hearts-resident-test -f docker-compose.server.yml down`.
