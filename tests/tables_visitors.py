#!/usr/bin/env python3
# Copyright (c) 2026 Athena Decision Systems SAS.
"""Several visitors from the web at once, each at a table of their own with the players one Medley offers.

    python3 tests/tables_visitors.py http://localhost:8058 ADMIN-PASSWORD TABLES [OVER-SCORE]

Each plays a game to OVER-SCORE (30) against the Medley's three players, all at the same time.  Checks that every
game ends, that the Medley's seats played every one of their cards, and prints how long a deal took.
Prints PASS and FAIL lines; exit 0 when every check passed.
"""
import asyncio
import statistics
import sys
import time

from house_client import Checks, House

house, TABLES = House(sys.argv[1], sys.argv[2]), int(sys.argv[3])
OVER = int(sys.argv[4]) if len(sys.argv) > 4 else 30
check = Checks()


async def main():
    people = [house.sign_up(f"V{n + 1}x{int(time.time()) % 10000}") for n in range(TABLES)]
    players = house.wait_for_offer(people[0][0], 900)
    check("the Medley offers three players to everyone", len(players) == 3, players)
    if len(players) != 3:
        return
    tables = []
    for headers, _ in people:
        kinds = [o["kind"] for o in house.offered(headers)]
        check(f"table {len(tables) + 1}: the players are on offer", len(kinds) == 3, kinds)
        tables.append(house.call("/api/tables", {"seats": kinds, "over_score": OVER}, headers))
    check(f"{TABLES} tables have the Medley's players at once",
          all([s["kind"] for s in t["seats"]] == ["person", "medley", "medley", "medley"] for t in tables))
    start = time.time()
    games = await asyncio.gather(*[house.play(t, token) for t, (_, token) in zip(tables, people)])
    deals = []
    for n, (table, seen) in enumerate(zip(tables, games), 1):
        cards = [m for m in seen if m["type"] == "card"]
        ends = [m["at"] for m in seen if m["type"] == "deal_end"]
        deals += [b - a for a, b in zip([start] + ends, ends)]
        check(f"table {n}: the game is played to the end", seen[-1]["type"] == "game_end" and len(cards) % 52 == 0, seen[-1])
        check(f"table {n}: the Medley's seats played three cards in four", len([m for m in cards if m["seat"] != 1]) * 4 == len(cards) * 3)
        after = house.call(f"/api/tables/{table['id']}", headers=people[n - 1][0])
        check(f"table {n}: the Medley played them itself to the end", not any(s["stand_in"] for s in after["seats"]), after["seats"])
    print(f"     {TABLES} games at once, {len(deals)} deals: median {statistics.median(deals):.1f} s a deal, "
          f"slowest {max(deals):.1f} s, {time.time() - start:.0f} s in all", flush=True)
    check("afterwards the Medley's players are on offer again", len(house.wait_for_offer(people[0][0], 60)) == 3)


asyncio.run(main())
sys.exit(1 if check.failed else 0)
