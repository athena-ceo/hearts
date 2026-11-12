#!/usr/bin/env python3
"""Joins the test room and sends the guest forms that aren't game calls; both must be refused.
Run by tests/run-hnet.sh inside the relay's container:  python3 hnet-intruder.py RELAY"""
import signal, subprocess, sys
signal.alarm(60)   # never hang the test run
link = subprocess.Popen([sys.executable, "-u", "/hearts/dist/hnetlink.py", sys.argv[1], "hnettest", "intruder"],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
print(link.stdout.readline().decode().strip())
link.stdin.write(b"CALL guest 1 (CLOSEALL)\nCALL guest 2 (HNET.Apply (CLOSEALL))\n")
link.stdin.flush()
answers = [link.stdout.readline().decode().strip() for _ in range(2)]
link.stdin.write(b"QUIT\n"); link.stdin.flush()
for a in answers:
    print(a)
refused = '(NIL . "not an HNET call")'
ok = len(answers) == 2 and all(a.startswith("REPLY guest ") and a.endswith(refused) for a in answers)
print("intruder: refused" if ok else "intruder: NOT REFUSED")
sys.exit(0 if ok else 1)
