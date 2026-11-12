#!/usr/bin/env python3
"""Medley's link to the HEARTS network relay (hnetrelay.py).

Medley starts this with CREATE-PROCESS-STREAM and talks to it in lines of text on its
standard input and output; this keeps the WebSocket connection to the relay.  It needs
nothing beyond Python 3's standard library, so a Medley user has nothing to install.

    python3 hnetlink.py RELAY ROOM NAME        e.g. wss://hearts.example.com ROOM NAME

Medley -> link (stdin)                    link -> Medley (stdout)
  CALL to id body                           WELCOME name
  REPLY to id body                          PEERS name name ...
  PEERS                                     CALL from id body
  QUIT                                      REPLY from id body
                                            NOPEER to id
                                            CLOSED reason      (then the link exits)

A body is the rest of the line: a Lisp form, as Medley printed it.  The link passes its
bytes through unchanged (as Latin-1, so every byte survives).
"""
import base64
import hashlib
import json
import os
import socket
import ssl
import struct
import sys
import threading
import urllib.parse

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class Link:
    def __init__(self, url):
        u = urllib.parse.urlsplit(url)
        secure = u.scheme == "wss"
        port = u.port or (443 if secure else 80)
        sock = socket.create_connection((u.hostname, port), timeout=20)
        if secure:
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=u.hostname)
        key = base64.b64encode(os.urandom(16)).decode()
        path = u.path + ("?" + u.query if u.query else "")
        host = u.hostname if u.port is None else f"{u.hostname}:{u.port}"
        sock.sendall((f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\n"
                      f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                      f"Sec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = sock.recv(4096)
            if not chunk:
                raise ConnectionError("the relay closed the connection")
            head += chunk
        head, self.buffer = head.split(b"\r\n\r\n", 1)
        lines = head.decode("latin-1").split("\r\n")
        if " 101 " not in lines[0] + " ":
            raise ConnectionError(f"the relay answered {lines[0]}")
        accept = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
        if not any(l.lower().startswith("sec-websocket-accept:") and l.split(":", 1)[1].strip() == accept
                   for l in lines[1:]):
            raise ConnectionError("the relay's handshake is wrong")
        sock.settimeout(None)
        self.sock = sock
        self.lock = threading.Lock()

    def send(self, opcode, data):
        """One frame; a client must mask what it sends."""
        mask = os.urandom(4)
        n = len(data)
        if n < 126:
            head = struct.pack("!BB", 0x80 | opcode, 0x80 | n)
        elif n < 65536:
            head = struct.pack("!BBH", 0x80 | opcode, 0x80 | 126, n)
        else:
            head = struct.pack("!BBQ", 0x80 | opcode, 0x80 | 127, n)
        body = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        with self.lock:
            self.sock.sendall(head + mask + body)

    def send_json(self, obj):
        self.send(0x1, json.dumps(obj).encode())

    def read(self, n):
        while len(self.buffer) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("the relay closed the connection")
            self.buffer += chunk
        data, self.buffer = self.buffer[:n], self.buffer[n:]
        return data

    def message(self):
        """The next text message, answering pings on the way.  None when the relay closes."""
        parts = []
        while True:
            b0, b1 = self.read(2)
            opcode, n = b0 & 0x0F, b1 & 0x7F
            if n == 126:
                n = struct.unpack("!H", self.read(2))[0]
            elif n == 127:
                n = struct.unpack("!Q", self.read(8))[0]
            mask = self.read(4) if b1 & 0x80 else None
            data = self.read(n)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if opcode == 0x8:
                reason = data[2:].decode("utf-8", "replace") if len(data) > 2 else "closed"
                return None, reason
            if opcode == 0x9:
                self.send(0xA, data)
                continue
            if opcode == 0xA:
                continue
            parts.append(data)
            if b0 & 0x80:
                return b"".join(parts).decode("utf-8"), None


def say(line):
    try:
        sys.stdout.buffer.write(line.encode("latin-1", "replace") + b"\n")
        sys.stdout.buffer.flush()
    except OSError:          # Medley has gone: nobody to tell
        os._exit(0)


def from_medley(link):
    """Medley's lines, sent on to the relay."""
    for raw in sys.stdin.buffer:
        line = raw.decode("latin-1").rstrip("\r\n")
        words = line.split(" ", 3)
        try:
            if words[0] in ("CALL", "REPLY") and len(words) == 4:
                link.send_json({"type": words[0].lower(), "to": words[1],
                                "id": int(words[2]), "body": words[3]})
            elif words[0] == "PEERS":
                link.send_json({"type": "peers"})
            elif words[0] == "QUIT":
                break
        except (OSError, ValueError):
            break
    try:
        link.send(0x8, struct.pack("!H", 1000))
    except OSError:
        pass
    os._exit(0)


def main():
    if len(sys.argv) != 4:
        say("CLOSED usage: hnetlink.py RELAY ROOM NAME")
        return
    relay, room, name = sys.argv[1:]
    url = (relay.rstrip("/") + "/hnet/" + urllib.parse.quote(room)
           + "?name=" + urllib.parse.quote(name))
    try:
        link = Link(url)
    except (OSError, ConnectionError, ValueError) as e:
        say(f"CLOSED cannot reach the relay at {relay}: {e}")
        return
    threading.Thread(target=from_medley, args=(link,), daemon=True).start()
    try:
        while True:
            text, reason = link.message()
            if text is None:
                say(f"CLOSED {reason}")
                return
            msg = json.loads(text)
            kind = msg.get("type")
            if kind == "welcome":
                say(f"WELCOME {msg['name']}")
            elif kind == "peers":
                say("PEERS " + " ".join(msg["peers"]))
            elif kind in ("call", "reply"):
                body = msg["body"].replace("\r", " ").replace("\n", " ")   # one line per message
                say(f"{kind.upper()} {msg['from']} {int(msg['id'])} {body}")
            elif kind == "nopeer":
                say(f"NOPEER {msg['to']} {msg['id']}")
    except (OSError, ConnectionError, ValueError) as e:
        say(f"CLOSED {e}")


if __name__ == "__main__":
    main()
    os._exit(0)              # don't wait on the stdin thread, and don't finalize under it
