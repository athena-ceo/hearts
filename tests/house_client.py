# Copyright (c) 2026 Athena Decision Systems SAS.
"""A visitor to the house from the web, as a browser is: REST and the table's WebSocket.  Shared by the trials that
run against a real house and a real Medley (tests/resident_visitor.py, tests/tables_visitors.py)."""
import asyncio
import json
import time
import urllib.request

import websockets


class Checks:
    """PASS and FAIL lines, and how many failed."""

    def __init__(self):
        self.failed = 0

    def __call__(self, label, ok, detail=""):
        self.failed += not ok
        print(("PASS " if ok else "FAIL ") + label + (f"   got: {detail}" if detail and not ok else ""), flush=True)


class House:
    def __init__(self, base, admin):
        self.base, self.admin = base.rstrip("/"), admin

    def call(self, path, body=None, headers=None):
        request = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None,
                                         headers={"Content-Type": "application/json", **(headers or {})})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def sign_up(self, name):
        """A new player: (headers for REST, token for the socket)."""
        code = self.call("/api/admin/invites", {"note": "trial"}, {"X-Hearts-Admin": self.admin})["code"]
        signed = self.call("/api/auth/register", {"name": name, "password": "long enough", "code": code})
        return {"X-Hearts-Token": signed["token"]}, signed["token"]

    def offered(self, headers):
        """The players a Medley offers to everyone, as the lobby lists them now."""
        return [o for o in self.call("/api/opponents", headers=headers)["opponents"] if o["kind"].startswith("medley:")]

    def wait_for_offer(self, headers, seconds, count=3):
        end = time.time() + seconds
        while time.time() < end:
            found = self.offered(headers)
            if len(found) >= count:
                return found
            time.sleep(3)
        return self.offered(headers)

    async def play(self, table, token, moves=None):
        """Play seat 1 with the first legal card until the game ends, or for this many moves.  Returns the events
        seen, each with the time it came as "at"."""
        seen = []
        url = self.base.replace("http", "ws", 1) + f"/api/tables/{table['id']}/ws?token={token}"
        async with websockets.connect(url) as socket:
            while True:
                m = json.loads(await asyncio.wait_for(socket.recv(), 900))
                m["at"] = time.time()
                seen.append(m)
                view = m.get("view")
                if m["type"] in ("snapshot", "turn") and view and 1 in m.get("waiting", []):
                    if view["decision"] == "pass":
                        await socket.send(json.dumps({"type": "pass", "cards": view["hand"][:3]}))
                    elif view["legal"]:
                        await socket.send(json.dumps({"type": "play", "card": view["legal"][0]}))
                    if moves is not None:
                        moves -= 1
                if m["type"] == "game_end" or moves == 0:
                    return seen
