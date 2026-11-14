#!/usr/bin/env python3
# Copyright (c) 2026 Athena Decision Systems SAS.
"""A visitor from the web to the resident Medley: signs up, takes the three players the resident offers as
opponents, and plays a short game against them, twice, as a browser would (REST and the table's WebSocket).

    python3 tests/resident_visitor.py http://localhost:8058 ADMIN-PASSWORD      (run by tests/run-resident.sh)

Prints PASS and FAIL lines; exit 0 when every check passed.
"""
import asyncio
import json
import sys
import time
import urllib.request

import websockets

BASE, ADMIN = sys.argv[1].rstrip("/"), sys.argv[2]
failed = 0


def check(label, ok, detail=""):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + label + (f"   got: {detail}" if detail and not ok else ""), flush=True)


def call(path, body=None, headers=None):
    request = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def offered(headers):
    return [o for o in call("/api/opponents", headers=headers)["opponents"] if o["kind"].startswith("medley:")]


def wait_for_offer(headers, seconds):
    end = time.time() + seconds
    while time.time() < end:
        found = offered(headers)
        if len(found) >= 3:
            return found
        time.sleep(3)
    return offered(headers)


async def play(table, token):
    """Play seat 1 with the first legal card until the game ends.  Returns the events seen."""
    seen = []
    url = BASE.replace("http", "ws", 1) + f"/api/tables/{table['id']}/ws?token={token}"
    async with websockets.connect(url) as socket:
        while True:
            m = json.loads(await asyncio.wait_for(socket.recv(), 900))
            seen.append(m)
            view = m.get("view")
            if m["type"] in ("snapshot", "turn") and view and 1 in m.get("waiting", []):
                if view["decision"] == "pass":
                    await socket.send(json.dumps({"type": "pass", "cards": view["hand"][:3]}))
                elif view["legal"]:
                    await socket.send(json.dumps({"type": "play", "card": view["legal"][0]}))
            if m["type"] == "game_end":
                return seen


def main():
    code = call("/api/admin/invites", {"note": "resident test"}, {"X-Hearts-Admin": ADMIN})["code"]
    signed = call("/api/auth/register", {"name": f"Visitor{int(time.time()) % 100000}", "password": "long enough", "code": code})
    headers, token = {"X-Hearts-Token": signed["token"]}, signed["token"]
    players = wait_for_offer(headers, 900)
    check("the resident offers three players to everyone", len(players) == 3, players)
    if len(players) != 3:
        return
    print("     " + ", ".join(o["label"] for o in players), flush=True)
    for game in (1, 2):
        start = time.time()
        table = call("/api/tables", {"seats": [o["kind"] for o in players], "over_score": 1}, headers)
        check(f"game {game}: a table with the resident's players starts",
              table["status"] == "playing" and [s["kind"] for s in table["seats"]] == ["person", "medley", "medley", "medley"], table)
        check(f"game {game}: nobody else can take them meanwhile", not offered(headers))
        seen = asyncio.run(play(table, token))
        cards = [m for m in seen if m["type"] == "card"]
        end = seen[-1]
        check(f"game {game}: it is played to the end", end["type"] == "game_end" and len(cards) % 52 == 0, end)
        check(f"game {game}: the Medley's seats played three cards in four", len([m for m in cards if m["seat"] != 1]) * 4 == len(cards) * 3)
        print(f"     {len(cards) // 52} deal(s), totals {end['totals']}, {int(time.time() - start)} seconds", flush=True)
        players = wait_for_offer(headers, 240)
        check(f"game {game}: afterwards the resident offers fresh players", len(players) == 3, players)
        if len(players) != 3:
            return


main()
sys.exit(1 if failed else 0)
