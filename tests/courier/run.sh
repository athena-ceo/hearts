#!/bin/bash
# Two headless Medleys on a NetHub; one calls the other with Medley's stock Courier packages
# (COURIEREVALSERVE's REMOTEEVAL and REMOTEAPPLY) and with a small Courier program of our own.
# No HEARTS in it: this is the example for docs/medley-networking.md.
#
#   tests/courier/run.sh        (needs the hearts-medley image: tools/medley-headless --build)
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
NET="hearts-courier-$$"; HUB="$NET-hub"
cleanup() { docker rm -f "$HUB" >/dev/null 2>&1; docker network rm "$NET" >/dev/null 2>&1; }
trap cleanup EXIT
docker network create "$NET" >/dev/null
docker run -d --rm --name "$HUB" --network "$NET" -v "$ROOT:/hearts" --entrypoint python3 \
  hearts-medley -u /hearts/tools/nethub.py --log >/dev/null
medley() {  # medley MAC OUT TIMEOUT SCRIPT
  docker run --rm --network "$NET" -e MEDLEY_NETHUB="$HUB:3333:$1" -v "$ROOT:/hearts" \
    -v "$ROOT/docker/medley-run:/usr/local/bin/medley-run:ro" -w /hearts hearts-medley \
    --out "/hearts/out/$2" --timeout "$3" "$4"
}
mkdir -p out
medley 10-00-AA-00-00-01 courier-server 200 tests/courier/server.lisp >out/courier-server.txt 2>&1 &
medley 10-00-AA-00-00-02 courier-client 200 tests/courier/client.lisp >out/courier-client.txt 2>&1
RC=$?
wait
docker logs "$HUB" >out/courier-hub.log 2>&1
grep -a -E "^(PASS|FAIL|ERROR|\(|==HT-SUMMARY)" out/courier-client.txt
echo "hub: $(grep -c B out/courier-hub.log) frames"
exit $RC
