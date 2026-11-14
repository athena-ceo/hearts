#!/bin/bash
# HEARTS over Courier, end to end: the house (the web backend, with its Courier door open) on this
# computer, and a headless Medley in a container whose 1986 players sit at a table and play a game.
#
#   tests/run-courier.sh [SCRIPT]       default tests/courier/table.lisp
#
# Needs the hearts-medley image (tools/medley-headless --build) and the backend's virtual
# environment (.venv).  Results in out/courier-table/ and out/courier-house.log.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
SCRIPT="${1:-tests/courier/table.lisp}"
NAME="$(basename "$SCRIPT" .lisp)"
PORT="${HEARTS_NETHUB_PORT:-3399}"
WORK="$(mktemp -d)"
mkdir -p out
HEARTS_DB="$WORK/hearts.db" HEARTS_NETHUB_PORT="$PORT" BACKEND_PORT=8059 HEARTS_OFFER_KEY=test-key \
  HEARTS_ADMIN_PASSWORD=test-admin PYTHONPATH=backend .venv/bin/python -m uvicorn hearts.web:app --port 8059 \
  --log-level info >out/courier-house.log 2>&1 &
HOUSE=$!
cleanup() { kill $HOUSE 2>/dev/null; rm -rf "$WORK"; }
trap cleanup EXIT
for _ in $(seq 1 50); do curl -sf http://127.0.0.1:8059/health >/dev/null && break; sleep 0.2; done
docker run --rm -e MEDLEY_NETHUB="host.docker.internal:$PORT:10-00-AA-00-00-01" -e HOUSE_URL=http://host.docker.internal:8059 \
  -v "$ROOT:/hearts" -v "$ROOT/docker/medley-run:/usr/local/bin/medley-run:ro" -w /hearts hearts-medley \
  --out "/hearts/out/courier-$NAME" --timeout "${TIMEOUT:-1800}" ${LOOPS:+--loops} "$SCRIPT" >"out/courier-$NAME.txt" 2>&1
RC=$?
grep -a -E "^(PASS|FAIL|ERROR|==HT-SUMMARY)|^= \(SCORE" "out/courier-$NAME.txt"
REFUSED="$(grep -c "refused call" out/courier-house.log)"
echo "calls the Medley refused: $REFUSED"
[ "$RC" = 0 ] && [ "$REFUSED" = 0 ]
