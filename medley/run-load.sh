#!/bin/bash
# Attempt to LOAD the transcribed HEARTS core into Medley Interlisp, headlessly,
# capturing the result to medley/hearts-load.log via the REM.CM auto-load file.
#
# Usage:
#   medley/run-load.sh              # default: SDL backend (no XQuartz needed)
#   medley/run-load.sh x11          # X11 backend (needs XQuartz running + DISPLAY)
#
# Regenerate medley/HEARTS first if the transcription changed:
#   python3 medley/build-loadfile.py
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
INSTALL="$HERE/.install"
MEDLEY="$INSTALL/medley/medley"
REMCM="$HERE/rem-load.cm"
LOG="$HERE/hearts-load.log"
BACKEND="${1:-sdl}"

# macOS clipboard (the CLIPBOARD library picks pbpaste/pbcopy vs xclip by checking
# getenv("OSTYPE") for "darwin"); OSTYPE is a shell var that isn't exported, so export
# it here or Medley thinks it's on Linux and the clipboard silently no-ops.
export OSTYPE="${OSTYPE:-darwin}"

rm -f "$LOG"
[ -f "$HERE/HEARTS" ] || { echo "missing $HERE/HEARTS — run: python3 medley/build-loadfile.py"; exit 1; }

PROGFLAG=()
if [ "$BACKEND" = "sdl" ]; then
  PROGFLAG=(--maikoprog ldesdl)         # native Cocoa window, no XQuartz
  # ldesdl links @rpath/SDL2.framework; let dyld find one installed in ~/Library/Frameworks
  export DYLD_FRAMEWORK_PATH="$HOME/Library/Frameworks${DYLD_FRAMEWORK_PATH:+:$DYLD_FRAMEWORK_PATH}"
fi

echo "Booting Medley ($BACKEND) with apps sysout + Interlisp exec, auto-loading HEARTS..."
# -a apps sysout, -e Interlisp exec, -n noscroll, -i unique id, -cm rem.cm auto-load
"$MEDLEY" -a -e -n -i heartsload "${PROGFLAG[@]}" -cm "$REMCM" &
MPID=$!

# Wait up to 180s for the REM.CM to finish (it ends with LOGOUT) or for the log to complete.
for i in $(seq 1 180); do
  if ! kill -0 "$MPID" 2>/dev/null; then break; fi
  if grep -q "==END-HEARTS-LOAD==" "$LOG" 2>/dev/null; then break; fi
  sleep 1
done
kill "$MPID" 2>/dev/null; wait "$MPID" 2>/dev/null
pkill -f "ldesdl.*heartsload" 2>/dev/null   # ensure the VM grandchild is gone too
sleep 1

echo "----- hearts-load.log -----"
cat "$LOG" 2>/dev/null || echo "(no log produced — Medley may not have reached the Interlisp exec)"
