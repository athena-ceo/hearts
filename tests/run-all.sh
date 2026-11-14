#!/bin/bash
# Run every headless test (see docker/README.md) and summarize.  ~20 minutes, mostly the games.
# Each test gets its own output directory under out/, so they can run in parallel.
cd "$(dirname "$0")/.." || exit 1
run() {  # run NAME [medley-run options...] SCRIPT
  local name=$1; shift
  local pre=(); if [ "${1:-}" = "--utf8" ]; then pre=(--utf8); shift; fi
  tools/medley-headless ${pre[@]+"${pre[@]}"} --out "/hearts/out/test-$name" "$@" > "out/test-$name.log" 2>&1
  printf '%-18s exit %s  %s\n' "$name" "$?" "$(grep -ah '==HT-SUMMARY==' "out/test-$name.log" | sed 's/==HT-SUMMARY== //')"
}
mkdir -p out
printf '%-18s %s\n' llm-helper "$(python3 tests/test_llm_player.py 2>&1 | tail -1)"
printf '%-18s %s\n' simulator "$(python3 selfplay/test_sim.py 2>&1 | tail -1)"
run smoke                                   tests/smoke.lisp &
run expert-load     --loops                 tests/expert-load.lisp &
run expert-examples --loops                 tests/expert-examples.lisp &
run expert-autoloops                        tests/expert-autoloops.lisp &
run expert-dist     --timeout 1200          tests/expert-dist.lisp &
run expert-open     --loops --timeout 900   tests/expert-open.lisp &
run expert-pagehold --timeout 600           tests/expert-pagehold.lisp &
run dealer                                  tests/dealer.lisp &
run playhearts      --loops --timeout 900   tests/playhearts.lisp &
run llmplayer       --timeout 900           tests/llmplayer.lisp &
run nnplayer        --timeout 900           tests/nnplayer.lisp &
run netguide        --timeout 300           tests/netguide.lisp &
wait
# The players that name files and run commands, again under a UTF-8 locale, as on a Mac (M11).
run llmplayer-utf8  --utf8 --timeout 900    tests/llmplayer.lisp &
run nnplayer-utf8   --utf8 --timeout 900    tests/nnplayer.lisp &
run playhearts-utf8 --utf8 --loops --timeout 1500 tests/playhearts.lisp &
wait
run expert-game     --loops --timeout 1800  tests/expert-game.lisp   # alone: it needs the CPU
wait
# Courier between two Medleys on a NetHub, with the stock packages (tests/courier/run.sh).
printf '%-18s %s\n' courier-medleys "$(tests/courier/run.sh 2>&1 | grep -a 'HT-SUMMARY' | sed 's/==HT-SUMMARY== //')"
# HEARTS over Courier: a Medley's players at a table of the house (tests/run-courier.sh).
printf '%-18s %s\n' courier-house "$(tests/run-courier.sh 2>&1 | tail -3 | tr '\n' ' ')"
# The demo server's house and resident Medley, with a visitor from the web and one from a Medley (tests/run-resident.sh).
printf '%-18s %s\n' resident "$(tests/run-resident.sh 2>&1 | tail -4 | tr '\n' ' ')"
