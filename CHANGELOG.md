<!-- Copyright (c) 2026 Athena Decision Systems SAS. -->

# Changelog

## [Unreleased]

### 2026-11-18

- **One Medley plays at several tables: proved** (not deployed). The resident offers its players
  at up to eight tables (`RESIDENT_TABLES`) and shows one game, chosen from a row of tabs.
  - Trials: `tests/courier/tables.lisp` with 1, 2, 4 and 8 visitors (12 of 12, no refused call, no
    stand-in move); a deal takes 26 s with one game and 31 s with eight at the 1986 2-second trick
    pause, so tables do not hold each other up. `tests/run-resident.sh` 14 of 14.
  - Fixed: calls for games not on show were refused (REJECT 65535) because `GETPROMPTWINDOW`
    re-attached a closed Expert's Thoughts window to itself; `PLAYHEARTS` now advises it to return
    the Thoughts window. `HCOURIER` skips `CLEARW` on a quiet window; `NP.Think` and `NP.Best` draw
    only when thoughts are on. `docker/resident.lisp`: an unbalanced `R.Lost` had stopped the
    resident offering; status window shows the players' kinds on one line; `R.Loop` prints a
    step's error in the Exec.
  - Interlisp, not Common Lisp (`HANDOFF.md` convention 6): `NLSETQ` and `ERRORMESS` for
    `CL:HANDLER-CASE`, `RESETLST`/`RESETSAVE` for `CL:UNWIND-PROTECT`, a `LET` with `SPECVARS` for
    `CL:PROGV` and `CL:PROCLAIM`, `READ` of `OPENSTRINGSTREAM` for `CL:WITH-INPUT-FROM-STRING`,
    `GETD`/`MACRO-FUNCTION` for `CL:FBOUNDP`, `bind … until` for a `PROG`/`GO` loop, in `medley/`,
    `docker/` and `tests/`; `dist/` rebuilt. Packages and `CL:COMPILE` stay Common Lisp, with a
    comment saying why.
  - `tests/resident_visitor.py` uses `tests/house_client.py`; docs (`docs/medley-server.md`,
    `USER-MANUAL.md`, `TODO.md`) describe several tables and `HC.Offer`'s forms.
- **Convention: on Medley, build the Medley way** (Harley, 2026-11-18). `HANDOFF.md`, convention 9:
  look first for what Medley has and build in Lisp on it; a child process or another language
  doing a Medley's work is the last resort and is justified where it is used.

### 2026-11-15

- **CI: three house tests no longer depend on the machine's speed.** Run 22 failed on GitHub's
  runner with tests that pass on a fast machine; each fails on one busy core. Tests only, no change
  to the house.
  - `play_until_end_of_deal` (`test_web.py`) answered the same decision twice when it came in the
    snapshot and again in the turn's announcement before the house had read the first answer, and
    the house refused the second ("seat 1 can't pass now"). It now answers a decision once.
  - `test_one_medleys_players_are_at_several_tables_at_once…` opened its three tables one after the
    other, so the second and third had nobody at them for longer than the wait and their players
    went home, as the product intends. The three people now have their tables open together.
  - `test_a_stand_in_plays_for_a_medley…` looked at `door.links` the moment the Medley closed its
    connection; it now waits for the house to see it (`until`, moved to `test_courier.py`).
  - `backend/tests`: 126 passed, four times running on one core shared with six busy processes.
- **One Medley plays at several tables (in progress; committed to change computers, not deployed).**
  Asked by Harley on 2026-11-15, in place of a pool of resident Medleys. Both Courier programs are
  now version 2: every `HEARTSPLAYERS` call names its table first, `OFFER` says how many tables the
  players can be at at once, and `LEAVE` names a table or, with an empty name, all of them
  (ARCHITECTURE §4.2). There is one version: a Medley with the old `HCOURIER` is rejected.
  - House (`backend/hearts/courier.py`): a `Link` holds `games`, one per table; players offered to
    everyone stay on offer until the Medley is at `capacity` tables; its calls still go one at a
    time, because the 1986 Expert's rules share one working memory. Fixed on the way: a seat
    waiting for the answer of a Medley whose connection closed during the call waited for ever.
  - Medley (`medley/hcourier.lisp`): a game is an `HCGAME` record and `HC.Games` is the list of
    them; the globals `HC.Players`, `HC.Playing`, `HC.Winners`, `HC.Scores` and the use of
    `Player.Array`, `HNET.MyPlayers` and `HNET.CardTable` are gone. `HC.Offer` takes forms that
    make players, and they are made fresh for each table.
  - One game is on show (`HC.Shown`, `HC.Show`, `HC.Pick`). Tried on Medley 260810: any drawing in
    a covered or closed window brings it to the top, so games not on show draw nothing (their
    players' windows are closed and marked `HC.Quiet`, `ThinkFlag?` and `NP.Thoughts?` are bound to
    NIL around their players' calls) and `HC.CatchUp` redraws a card table when its game takes the
    screen.
  - Resident (`docker/resident.lisp`): one standing offer for `RESIDENTTABLES` tables (8), and a
    row of tabs under the status window, one for each game.
  - Proved so far: `backend/tests` 126 passed; `tests/run-courier.sh` (a whole game on a headless
    Medley) 20 of 20. **Not yet run:** `tests/run-resident.sh` with the new resident and its tabs;
    `VISITORS=4 LOOPS=1 tests/run-courier.sh tests/courier/tables.lisp` (several tables at once,
    switching the game on show); timings with 1, 2 and 8 games. `tests/resident_visitor.py` is
    still to be moved onto `tests/house_client.py`. See HANDOFF, "In progress".
- **A Medley's offered players are held only while someone is at their table.** Seen on the live
  server: a visitor left after one deal and the resident's players played the game out against
  stand-ins, unavailable to anyone else for about 5 minutes; a browser player who closed a table
  with no move timer held them until the next restart. Now a table knows who is there
  (`Table.present`, `backend/hearts/tables.py`): a person with the table open in a browser, or
  who had it open or moved within `HEARTS_MEDLEY_HOLD` seconds (120), or a Medley that sat its own
  players. When nobody is (`Table.unattended`), the players a Medley offered to everyone go home
  (`Door.vacate`: `GAME.OVER` with no winner, stand-ins in their seats) and can be offered again.
  The game is kept if a person can come back to it. If no one can, because its only people were on
  a Medley that has left, it ends there with the new status `abandoned`, and a restart does not
  bring it back. A table still waiting for players follows the same rule (Harley, 2026-11-15): the
  offered players' seats are open again and the Medley's offer stands, since it was told nothing
  of a table that never started.
  - Web: a seat carries `stand_in`; the table says that the Medley's players have left and a
    stand-in is playing for them, and tells someone watching that a game ended because its players
    left (EN/FR).
  - Fixed on the way: a Medley that had left one game and begun another could be asked for a card
    by the first, where the seat number was the same (`MedleySeat` now checks the table).
  - Tests: `backend/tests/test_presence.py`, a matrix over who the people were, how they went, what
    else was at the table and when, for games and for waiting tables (23 cases). `tests/resident_visitor.py` walks away from a game
    with the real resident and comes back to finish it.

### 2026-11-14

- **The 1986 port is boxed.** Tag `revival-1986` marks the finished revival; `HANDOFF.md` has the
  direction from here.
- **HEARTS over Courier.** Medleys and browsers now meet at the same tables. The house (the web
  backend) runs a NetHub (`HEARTS_NETHUB_PORT`, 3333 on the server) and speaks XNS on it:
  `backend/hearts/xns.py` (IDP, SPP, Courier, written against Medley's sources) and
  `backend/hearts/courier.py` (the door: Courier programs `HEARTSHOUSE` 19860 and `HEARTSPLAYERS`
  19861, seats of kind `medley`, a stand-in for a Medley that goes away, limits on connections
  and tables, `HEARTS_OFFER_KEY`). The hub passes no frame between machines. The protocol is new:
  every event to every seat that may see it, and requests that carry the legal cards
  (ARCHITECTURE §4.2).
  - Medley: `medley/hcourier.lisp` (`dist/HCOURIER`) defines both programs on the stock
    `COURIERSERVE` and adapts the calls to the 1986 players. `PLAYHEARTS`' online seat now opens a
    table at the house (`PH.RunOnline`); its relay code is gone.
  - `backend/hearts/tables.py`: Medley seats pass in their own time beside people; `StandIn`;
    `Tables.opponents` lists players a Medley offers; a recorded pass is found whatever order the
    passes came in, so a game with Medley seats replays after a restart.
  - The resident Medley (`docker/resident.lisp`, `docker/resident-run`) offers its Expert, network
    and Conservative to the house instead of sitting in the relay's room, waits for the NetHub
    before it starts, and logs out to rejoin when the house has gone.
  - Web: offered players are in the seat menus; if they were just taken, the lobby says so (EN/FR)
    and asks again who is offered. `/health` reports `medleys` and `offered`.
  - `docker/Dockerfile` rebuilds the release's Maiko with `-DMAIKO_ENABLE_NETHUB` for every Medley
    image; `./hearts.sh maiko-nethub` does the same beside a local Medley release (run on an Apple
    Silicon Mac, where a whole game passed), and `./hearts.sh medley` then starts Medley on the
    house's NetHub. `MEDLEY_NETHUB` in `docker/medley-run` and `tools/medley-headless`.
  - Revival patch 2q (HEARTS-BUGS H8): HEARTS no longer asks for its PUP host number as it loads,
    which never returned on a NetHub.
  - Tests: `backend/tests/test_courier.py` (the door, with a stand-in for Medley),
    `tests/run-courier.sh` (a headless Medley's players play a game to 100 at the house),
    `tests/run-resident.sh` (a web visitor, then a PlayHearts Medley, play the resident's
    players), two lobby tests.
- **The 1986 relay way is retired** (Harley: one live version, the improved one). Removed:
  `medley/hnet.lisp`, `hnetlink.py`, `hnetrelay.py`, `dist/HNET`, the `relay` service, its nginx
  location, `./hearts.sh relay`, and the tests `run-hnet.sh`, `test_hnet.py`, `hnet-*.lisp`. They
  are at tag `revival-1986`. On the server the `/hearts/hnet/` location stays in nginx until
  `./hearts.sh nginx-install` is run again.
- **Online play is quicker.** Measured on the live server: the line and the house cost one round
  trip a call (7 ms). Two delays were elsewhere. A Medley's first call to the house waited 8
  seconds for a router that isn't there: the house now answers Medley's routing information
  request (`backend/hearts/xns.py`), and the first call is immediate, also after five idle
  minutes. And the resident's card table held each trick for 2 seconds, most of a deal's 29:
  `HC.TrickPause` (`medley/hcourier.lisp`) sets it, and the resident uses 1 second.
- **`./hearts.sh nginx-install` installs the web game too**: the page, its API and its health
  address, with the resident's screens, between new `hearts` markers; it replaces a copy from the
  earlier `hearts-medley` markers (`scripts/nginx_install.py`, `backend/tests/test_nginx_install.py`).
  Until now the game's own addresses had to be pasted by hand, and on the server they never were.
- **Courier trial.** Two headless Medleys on a NetHub call each other with the stock
  `COURIERSERVE` / `COURIEREVALSERVE` and a restricted `COURIERPROGRAM` of our own:
  `tests/courier/run.sh` (10 checks pass) and `tools/nethub.py` (a minimal hub).
- **`docs/medley-networking.md` corrected.** `REMOTEEVAL` is in the release (LispUsers), and XNS
  through a NetHub works; the Courier way is now the recommended one.
