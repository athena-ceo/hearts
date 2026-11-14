<!-- Copyright (c) 2026 Athena Decision Systems SAS. -->

# Changelog

## [Unreleased]

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
- **Courier trial.** Two headless Medleys on a NetHub call each other with the stock
  `COURIERSERVE` / `COURIEREVALSERVE` and a restricted `COURIERPROGRAM` of our own:
  `tests/courier/run.sh` (10 checks pass) and `tools/nethub.py` (a minimal hub).
- **`docs/medley-networking.md` corrected.** `REMOTEEVAL` is in the release (LispUsers), and XNS
  through a NetHub works; the Courier way is now the recommended one.
