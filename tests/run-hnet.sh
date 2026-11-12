#!/bin/bash
# The network game end to end: a relay and two headless Medleys, each in its own container on a
# private Docker network, play a full game; then an intruder tries forms that aren't game calls.
#
#   tests/run-hnet.sh [--utf8]
#
# Results in out/hnet-house/, out/hnet-guest/, out/hnet-relay.log; with HNET_TRACE=1, every message
# each Medley sent and got in out/hnet-house-trace.txt and out/hnet-guest-trace.txt.  Exit 0 when all is well.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PRE=()
[ "${1:-}" = "--utf8" ] && PRE=(--utf8)
NET="hearts-hnet-$$"
RELAY="$NET-relay"
export HNET_RELAY="ws://$RELAY:8765"
cleanup() { docker rm -f "$RELAY" >/dev/null 2>&1; docker network rm "$NET" >/dev/null 2>&1; }
trap cleanup EXIT
docker network create "$NET" >/dev/null
docker run -d --rm --name "$RELAY" --network "$NET" -v "$ROOT:/hearts" --entrypoint python3 \
  hearts-medley -u /hearts/medley/hnetrelay.py >/dev/null
mkdir -p out
tools/medley-headless ${PRE[@]+"${PRE[@]}"} --network "$NET" --out /hearts/out/hnet-guest --timeout 2400 \
  tests/hnet-guest.lisp >out/hnet-guest.txt 2>&1 &
GUEST=$!
tools/medley-headless ${PRE[@]+"${PRE[@]}"} --network "$NET" --out /hearts/out/hnet-house --timeout 2400 \
  tests/hnet-house.lisp >out/hnet-house.txt 2>&1
HOUSE=$?
docker exec "$RELAY" python3 /hearts/tests/hnet-intruder.py "$HNET_RELAY" >out/hnet-intruder.txt 2>&1
INTRUDER=$?
wait $GUEST
GUESTRC=$?
docker logs "$RELAY" >out/hnet-relay.log 2>&1
summary() { grep -a "==HT-SUMMARY==" "$1" | tail -1; }
score() { grep -a -A1 "(LIST (QUOTE SCORE)" "$1" | grep -a "^= " | tail -1; }
echo "house    exit $HOUSE    $(summary out/hnet-house.txt)    $(score out/hnet-house.txt)"
echo "guest    exit $GUESTRC    $(summary out/hnet-guest.txt)    $(score out/hnet-guest.txt)"
echo "intruder exit $INTRUDER    $(tail -1 out/hnet-intruder.txt)"
SAME=1
[ -n "$(score out/hnet-house.txt)" ] && [ "$(score out/hnet-house.txt)" = "$(score out/hnet-guest.txt)" ] || SAME=0
echo "both tables show the same final score: $([ $SAME = 1 ] && echo yes || echo NO)"
[ $HOUSE = 0 ] && [ $GUESTRC = 0 ] && [ $INTRUDER = 0 ] && [ $SAME = 1 ]
