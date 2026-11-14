#!/usr/bin/env python3
"""A minimal XNS NetHub: the virtual Ethernet that Maiko's -nh-host option connects to.

Each machine holds one TCP connection.  A packet is a 2-byte big-endian length followed by
that many bytes of raw Ethernet frame (destination MAC first).  Like a hub, this sends every
frame to every other connection; each Maiko keeps only frames for its own MAC or broadcast.
It offers none of the services of a Dodo server (time, routing, clearinghouse).

    python3 tools/nethub.py [--port 3333] [--log]
"""
import argparse
import asyncio

clients = set()


async def serve(reader, writer, log):
    clients.add(writer)
    peer = writer.get_extra_info("peername")
    print(f"joined {peer}", flush=True)
    try:
        while True:
            head = await reader.readexactly(2)
            frame = await reader.readexactly(int.from_bytes(head, "big"))
            if log:
                print(f"{peer[0]} {len(frame)}B dst={frame[0:6].hex()} src={frame[6:12].hex()} "
                      f"type={frame[12:14].hex()}", flush=True)
            for other in list(clients):
                if other is not writer:
                    other.write(head + frame)
    except (asyncio.IncompleteReadError, ConnectionError):
        pass
    finally:
        clients.discard(writer)
        print(f"left {peer}", flush=True)
        writer.close()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=3333)
    ap.add_argument("--log", action="store_true")
    args = ap.parse_args()
    server = await asyncio.start_server(lambda r, w: serve(r, w, args.log), "0.0.0.0", args.port)
    print(f"nethub on {args.port}", flush=True)
    async with server:
        await server.serve_forever()

asyncio.run(main())
