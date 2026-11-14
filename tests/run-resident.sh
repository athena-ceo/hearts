#!/bin/bash
# The demo server's game services, locally: the backend (the house, with its NetHub) and the
# resident Medley from docker-compose.server.yml.  A visitor from the web plays the resident's
# players twice (tests/resident_visitor.py), then a visitor Medley plays them through PlayHearts.
#
#   tests/run-resident.sh [--keep] [--web-only]     --keep leaves the services running afterwards
#
# While it runs, watch the resident at http://localhost:8052/vnc.html (control: :8053).
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
KEEP=0; WEBONLY=0
for A in "$@"; do case "$A" in --keep) KEEP=1 ;; --web-only) WEBONLY=1 ;; esac; done
P=hearts-resident-test
export BACKEND_PORT=8058 NETHUB_PORT=3397 HEARTS_ADMIN_PASSWORD=test-admin HEARTS_OFFER_KEY=test-key
C=(docker compose -p "$P" -f docker-compose.server.yml)
"${C[@]}" up -d --build backend medley >out/resident-up.log 2>&1 || { echo "cannot start the services (out/resident-up.log)"; exit 1; }
[ $KEEP = 1 ] || trap '"${C[@]}" logs backend >out/resident-backend.log 2>&1; "${C[@]}" logs medley >out/resident-medley.log 2>&1; "${C[@]}" down -v >/dev/null 2>&1' EXIT
for _ in $(seq 1 60); do curl -sf "http://localhost:$BACKEND_PORT/health" >/dev/null && break; sleep 1; done
.venv/bin/python tests/resident_visitor.py "http://localhost:$BACKEND_PORT" "$HEARTS_ADMIN_PASSWORD" 2>&1 | tee out/resident-web.txt
WEB=${PIPESTATUS[0]}
RC=0
if [ $WEBONLY = 0 ]; then
  MEDLEY_NETHUB=backend:3333:10-00-AA-00-00-22 tools/medley-headless --network "${P}_hearts-network" \
    --out /hearts/out/resident-visitor --timeout 3900 tests/resident-visitor.lisp > out/resident-visitor.txt 2>&1
  RC=$?
  grep -a -E "^(PASS|FAIL|ERROR)|got:|^= \(SECONDS" out/resident-visitor.txt
  echo "Medley visitor exit $RC  $(grep -a '==HT-SUMMARY==' out/resident-visitor.txt)"
fi
echo "web visitor exit $WEB"
curl -s "http://localhost:$BACKEND_PORT/health"; echo
[ "$WEB" = 0 ] && [ "$RC" = 0 ]
