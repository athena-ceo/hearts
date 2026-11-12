#!/usr/bin/env python3
"""The network game's relay and link, without Medley: forwarding, refusals, a long message,
and wss:// with a certificate (a self-signed one, trusted through SSL_CERT_FILE).

    python3 tests/test_hnet.py          (needs the websockets package, and openssl for wss)
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELAY = os.path.join(ROOT, "medley", "hnetrelay.py")
LINK = os.path.join(ROOT, "medley", "hnetlink.py")
checks = failures = 0


def check(label, got, want):
    global checks, failures
    checks += 1
    if got != want:
        failures += 1
        print(f"FAIL {label}\n   got: {got!r}\n  want: {want!r}")


def relay(port, *extra):
    p = subprocess.Popen([sys.executable, RELAY, "--host", "127.0.0.1", "--port", str(port), *extra],
                         stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    return p


class Link:
    def __init__(self, url, room, name, env=None):
        self.p = subprocess.Popen([sys.executable, LINK, url, room, name], env=env,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def say(self, line):
        self.p.stdin.write(line.encode() + b"\n")
        self.p.stdin.flush()

    def hear(self):
        return self.p.stdout.readline().decode().rstrip("\n")


r = relay(8797)
url = "ws://127.0.0.1:8797"
try:
    a, b = Link(url, "t1", "alice"), Link(url, "t1", "bob")
    check("alice is welcomed", a.hear(), "WELCOME alice")
    check("bob is welcomed", b.hear(), "WELCOME bob")
    a.say("PEERS")
    check("alice sees bob", a.hear(), "PEERS bob")
    a.say("CALL bob 7 (Greet (QUOTE x))")
    check("a call arrives", b.hear(), "CALL alice 7 (Greet (QUOTE x))")
    b.say('REPLY alice 7 (T . "hi")')
    check("the reply returns", a.hear(), 'REPLY bob 7 (T . "hi")')
    a.say("CALL carol 8 (X)")
    check("a call to no one", a.hear(), "NOPEER carol 8")
    check("a name in use", Link(url, "t1", "bob").hear(), "CLOSED bob is already in room t1")
    check("a bad name", Link(url, "t1", "b_ad").hear(),
          "CLOSED use /hnet/ROOM?name=NAME: letters, digits, dots, dashes")
    other = Link(url, "t2", "bob")
    check("rooms are apart", other.hear(), "WELCOME bob")
    big = "(" + "A " * 30000 + ")"
    a.say(f"CALL bob 9 {big}")
    check("a 60 KB message", len(b.hear()), len("CALL alice 9 ") + len(big))
    b.say("QUIT")
    time.sleep(0.5)
    a.say("PEERS")
    check("bob left", a.hear(), "PEERS ")
    r.terminate()
    check("the relay stops", a.hear(), "CLOSED the relay closed the connection")
finally:
    r.terminate()

if shutil.which("openssl"):
    with tempfile.TemporaryDirectory() as d:
        cert, key = os.path.join(d, "cert.pem"), os.path.join(d, "key.pem")
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key,
                        "-out", cert, "-days", "1", "-subj", "/CN=localhost",
                        "-addext", "subjectAltName=DNS:localhost"], check=True, capture_output=True)
        r = relay(8796, "--cert", cert, "--key", key)
        try:
            trust = dict(os.environ, SSL_CERT_FILE=cert)
            url = "wss://localhost:8796"
            a, b = Link(url, "t3", "alice", trust), Link(url, "t3", "bob", trust)
            check("wss: alice", a.hear(), "WELCOME alice")
            check("wss: bob", b.hear(), "WELCOME bob")
            a.say("CALL bob 1 (Greet (QUOTE x))")
            check("wss: a call", b.hear(), "CALL alice 1 (Greet (QUOTE x))")
            refused = Link(url, "t3", "carol", dict(os.environ)).hear()
            check("wss: an unknown certificate is refused", "CERTIFICATE_VERIFY_FAILED" in refused, True)
        finally:
            r.terminate()
else:
    print("(no openssl: wss not tested)")

print(f"{'OK' if not failures else 'FAILED'}: {checks - failures} of {checks} checks pass")
sys.exit(1 if failures else 0)
