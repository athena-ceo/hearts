#!/usr/bin/env python3
# Copyright (c) 2026 Athena Decision Systems SAS.
"""A visitor from the web to the resident Medley: signs up, takes the three players the resident offers as
opponents, and plays a short game against them, twice, as a browser would (REST and the table's WebSocket).
Then starts a third, walks away from it, and checks that the resident has its players back and that the game
is still there to finish.

    python3 tests/resident_visitor.py http://localhost:8058 ADMIN-PASSWORD [HOLD-SECONDS]   (run by tests/run-resident.sh)

Prints PASS and FAIL lines; exit 0 when every check passed.
"""
import asyncio
import sys
import time

from house_client import Checks, House

house = House(sys.argv[1], sys.argv[2])
HOLD = float(sys.argv[3]) if len(sys.argv) > 3 else 120  # HEARTS_MEDLEY_HOLD on that server.
check = Checks()
call, play = house.call, house.play


def main():
    headers, token = house.sign_up(f"Visitor{int(time.time()) % 100000}")
    players = house.wait_for_offer(headers, 900)
    check("the resident offers three players to everyone", len(players) == 3, players)
    if len(players) != 3:
        return
    print("     " + ", ".join(o["label"] for o in players), flush=True)
    for game in (1, 2):
        start = time.time()
        table = call("/api/tables", {"seats": [o["kind"] for o in players], "over_score": 1}, headers)
        check(f"game {game}: a table with the resident's players starts",
              table["status"] == "playing" and [s["kind"] for s in table["seats"]] == ["person", "medley", "medley", "medley"], table)
        check(f"game {game}: the resident has room for more tables, so they are still on offer", len(house.offered(headers)) == 3)
        seen = asyncio.run(play(table, token))
        cards = [m for m in seen if m["type"] == "card"]
        end = seen[-1]
        check(f"game {game}: it is played to the end", end["type"] == "game_end" and len(cards) % 52 == 0, end)
        check(f"game {game}: the Medley's seats played three cards in four", len([m for m in cards if m["seat"] != 1]) * 4 == len(cards) * 3)
        print(f"     {len(cards) // 52} deal(s), totals {end['totals']}, {int(time.time() - start)} seconds", flush=True)
        players = house.wait_for_offer(headers, 240)
        check(f"game {game}: afterwards the resident is still offering its players", len(players) == 3, players)
        if len(players) != 3:
            return
    # The visitor walks away in the middle of a game.
    table = call("/api/tables", {"seats": [o["kind"] for o in players], "over_score": 1}, headers)
    asyncio.run(play(table, token, moves=5))
    left = time.time()
    def stood_in():
        return [s["stand_in"] for s in call(f"/api/tables/{table['id']}", headers=headers)["seats"]]
    check("walking away: the resident's players are still at the table a moment later", stood_in() == [False] * 4)
    while stood_in() == [False] * 4 and time.time() - left < HOLD + 120:
        time.sleep(1)
    check("walking away: the resident's players have gone home", stood_in() == [False, True, True, True])
    check("walking away: not before the wait was over", time.time() - left >= HOLD, int(time.time() - left))
    print(f"     {int(time.time() - left)} seconds after the table was closed", flush=True)
    kept = call(f"/api/tables/{table['id']}", headers=headers)
    check("walking away: the game is kept, with stand-ins in the Medley's seats",
          kept["status"] == "playing" and [s["stand_in"] for s in kept["seats"]] == [False, True, True, True], kept)
    seen = asyncio.run(play(table, token))
    check("walking away: the visitor comes back and finishes the game", seen[-1]["type"] == "game_end", seen[-1])
    check("walking away: the resident's players were not taken again for it", len(house.offered(headers)) == 3)


main()
sys.exit(1 if check.failed else 0)
