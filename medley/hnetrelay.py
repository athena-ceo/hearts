#!/usr/bin/env python3
"""The HEARTS network relay: passes messages between Medleys over the Internet.

In 1986 the Medleys called each other directly over the Xerox Ethernet: REMOTEVAL sent a
Lisp form to another machine's EVALSERVER, which evaluated it.  Across the Internet the
machines can't reach each other (NAT, firewalls), so each one dials out to this relay
instead, through its helper (hnetlink.py), and the relay passes messages between the
Medleys in the same room.

The relay never evaluates anything.  It reads only the envelope (type, to, id) and
passes the body through untouched.  The receiving Medley decides what it will run
(HNET.Allowed in hnet.lisp).

    python3 hnetrelay.py [--host 0.0.0.0] [--port 8765] [--cert CERT.pem --key KEY.pem]

A Medley joins with  ws://HOST:PORT/hnet/ROOM?name=NAME, or wss:// when the relay has a
certificate (--cert and --key) or sits behind a TLS proxy.
ROOM and NAME are 1 to 32 letters, digits, dots or dashes.  Anyone who knows a room's
name can join it, so the room name works like an invitation code.

Messages are JSON, one per WebSocket text message:
  relay -> Medley   {"type": "welcome", "name": N, "peers": [...]}
                    {"type": "peers", "peers": [...]}      (the others, in the order they joined)
                    {"type": "call"|"reply", "from": N, "id": I, "body": S}
                    {"type": "nopeer", "to": N, "id": I}   (a call to someone not in the room)
  Medley -> relay   {"type": "peers"}
                    {"type": "call"|"reply", "to": N, "id": I, "body": S}
"""
import argparse
import asyncio
import json
import logging
import re
import ssl
import urllib.parse

import websockets

NAME = re.compile(r"^[A-Za-z0-9.-]{1,32}$")
MAX_MESSAGE = 1 << 20          # a hand or a trick is a few hundred bytes
MAX_ROOM = 8                   # a room's machines; --max-room changes it

rooms = {}                     # room -> {name: websocket}, in joining order
log = logging.getLogger("hnetrelay")


def where(ws):
    """The room and name a connection asked for, or None."""
    url = urllib.parse.urlsplit(ws.request.path)
    parts = url.path.strip("/").split("/")
    name = urllib.parse.parse_qs(url.query).get("name", [""])[0]
    if len(parts) == 2 and parts[0] == "hnet" and NAME.match(parts[1]) and NAME.match(name):
        return parts[1], name
    return None


async def handler(ws):
    place = where(ws)
    if place is None:
        await ws.close(4000, "use /hnet/ROOM?name=NAME: letters, digits, dots, dashes")
        return
    room, name = place
    members = rooms.setdefault(room, {})
    if name in members:
        await ws.close(4001, f"{name} is already in room {room}")
        return
    if len(members) >= MAX_ROOM:
        await ws.close(4002, f"room {room} is full")
        return
    members[name] = ws
    log.info("%s joined %s (%d there)", name, room, len(members))

    def others():
        return [n for n in members if n != name]

    try:
        await ws.send(json.dumps({"type": "welcome", "name": name, "peers": others()}))
        async for raw in ws:
            try:
                msg = json.loads(raw)
                kind = msg["type"]
            except (ValueError, KeyError, TypeError):
                continue
            if kind == "peers":
                await ws.send(json.dumps({"type": "peers", "peers": others()}))
            elif kind in ("call", "reply"):
                to, ident, body = msg.get("to"), msg.get("id"), msg.get("body")
                if not isinstance(body, str) or not isinstance(ident, int):
                    continue
                target = members.get(to)
                if target is not None and to != name:
                    try:
                        await target.send(json.dumps(
                            {"type": kind, "from": name, "id": ident, "body": body}))
                        continue
                    except websockets.ConnectionClosed:
                        pass
                if kind == "call":
                    await ws.send(json.dumps({"type": "nopeer", "to": to, "id": ident}))
    except websockets.ConnectionClosed:
        pass
    finally:
        del members[name]
        if not members:
            del rooms[room]
        log.info("%s left %s", name, room)


async def main(host, port, tls):
    async with websockets.serve(handler, host, port, max_size=MAX_MESSAGE, ssl=tls):
        log.info("HEARTS relay on %s://%s:%d/hnet/ROOM?name=NAME", "wss" if tls else "ws", host, port)
        await asyncio.Future()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--max-room", type=int, default=MAX_ROOM, help="machines per room (default 8)")
    ap.add_argument("--cert", help="TLS certificate (PEM), for wss://")
    ap.add_argument("--key", help="its private key (PEM)")
    args = ap.parse_args()
    MAX_ROOM = args.max_room
    tls = None
    if args.cert:
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(args.cert, args.key)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    asyncio.run(main(args.host, args.port, tls))
