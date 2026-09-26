#!/bin/bash
# Run every headless test (see docker/README.md) and summarize.  ~20 minutes, mostly the games.
# Each test gets its own output directory under out/, so they can run in parallel.
cd "$(dirname "$0")/.." || exit 1
run() {  # run NAME [medley-run options...] SCRIPT
  local name=$1; shift
  tools/medley-headless --out "/hearts/out/test-$name" "$@" > "out/test-$name.log" 2>&1
  printf '%-18s exit %s  %s\n' "$name" "$?" "$(grep -h '==HT-SUMMARY==' "out/test-$name.log" | sed 's/==HT-SUMMARY== //')"
}
mkdir -p out
run smoke                                   tests/smoke.lisp &
run expert-load     --loops                 tests/expert-load.lisp &
run expert-examples --loops                 tests/expert-examples.lisp &
run expert-autoloops                        tests/expert-autoloops.lisp &
run expert-dist     --timeout 1200          tests/expert-dist.lisp &
run expert-open     --loops --timeout 900   tests/expert-open.lisp &
wait
run expert-game     --loops --timeout 1800  tests/expert-game.lisp   # alone: it needs the CPU
wait
