#!/bin/bash
# The demo server's network-game services, locally: the relay and the resident Medley from
# docker-compose.server.yml, and a visitor Medley that plays the resident twice.
#
#   tests/run-resident.sh [--keep]      --keep leaves the services running afterwards
#
# While it runs, watch the resident at http://localhost:8052/vnc.html (control: :8053).
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
P=hearts-resident-test
C=(docker compose -p "$P" -f docker-compose.server.yml)
"${C[@]}" up -d --build relay medley >/dev/null 2>&1 || { echo "cannot start the services"; exit 1; }
[ "${1:-}" = "--keep" ] || trap '"${C[@]}" down >/dev/null 2>&1' EXIT
export HNET_RELAY=ws://relay:8765
tools/medley-headless --network "${P}_hearts-network" --out /hearts/out/resident-visitor --timeout 3000 \
  tests/resident-visitor.lisp > out/resident-visitor.txt 2>&1
RC=$?
grep -a -E "^(PASS|FAIL)|got:|^= \(SECONDS" out/resident-visitor.txt
"${C[@]}" logs relay 2>&1 | grep -E "joined|left" | tail -6
echo "visitor exit $RC  $(grep -a '==HT-SUMMARY==' out/resident-visitor.txt)"
exit $RC
