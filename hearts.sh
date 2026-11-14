#!/usr/bin/env bash
# Copyright (c) 2026 Athena Decision Systems SAS.
#
# Control script for HEARTS (mirrors advent.sh / xcape.sh / golden-path): the Python web
# platform, Medley on this computer, and the resident Medley on the server.
#   ./hearts.sh <command> [dev|prod] [args]
#   ./hearts.sh help
set -euo pipefail
cd "$(dirname "$0")"

CMD="${1:-help}"
shift || true

# Pick up any port overrides from .env (the same file docker compose reads).
if [ -f .env ]; then set -a; . ./.env; set +a; fi
BACKEND_PORT="${BACKEND_PORT:-8050}"
FRONTEND_PORT="${FRONTEND_PORT:-3050}"
MEDLEY_WATCH_PORT="${MEDLEY_WATCH_PORT:-8052}"
MEDLEY_CONTROL_PORT="${MEDLEY_CONTROL_PORT:-8053}"
NETHUB_PORT="${NETHUB_PORT:-3333}"
PUBLIC="https://apps.athenadecisions.com/hearts"
# Medley on this computer: the release directory and the folder Medley loads files from.
IL_DIR="${HEARTS_IL:-$HOME/il}"
MEDLEY_DIR="${MEDLEY_DIR:-$(ls -d "$HOME"/medley-*/medley 2>/dev/null | sort | tail -1 || true)}"
# An emulator built with NetHub support, for online play (./hearts.sh maiko-nethub).
NETHUB_MAIKO="${NETHUB_MAIKO:-${MEDLEY_DIR:+$(dirname "$MEDLEY_DIR")/maiko-nethub}}"

# The commands that take dev|prod read it here.
environ() {
  ENVIRON="${1:-dev}"
  case "$ENVIRON" in
    dev)  COMPOSE="docker compose -p hearts-dev -f docker-compose.dev.yml"
          # The resident Medley is only in the server file: locally it runs as its own
          # project, beside the dev stack, and reaches the dev backend's NetHub through
          # this computer.
          export MEDLEY_NETHUB="${MEDLEY_NETHUB:-host.docker.internal:${NETHUB_PORT}:10-00-AA-00-00-10}"
          RESIDENT="docker compose -p hearts-resident -f docker-compose.server.yml" ;;
    prod) COMPOSE="docker compose -p hearts -f docker-compose.server.yml"
          RESIDENT="$COMPOSE" ;;
    *) echo "unknown environment: $ENVIRON (use dev|prod)"; exit 1 ;;
  esac
}

print_urls() {
  echo ""
  echo "  Frontend:   http://localhost:${FRONTEND_PORT}"
  echo "  API docs:   http://localhost:${BACKEND_PORT}/docs      (Swagger UI)"
  echo "  Health:     http://localhost:${BACKEND_PORT}/health"
  if [ "$ENVIRON" = "prod" ]; then
    echo "  Public:     ${PUBLIC}/"
    print_resident_urls
  fi
  echo ""
}

print_resident_urls() {
  if [ "$ENVIRON" = "prod" ]; then
    echo "  NetHub:     apps.athenadecisions.com:${NETHUB_PORT}   (medley --nethub apps.athenadecisions.com:${NETHUB_PORT}:YOUR-MAC)"
    echo "  Watch:      ${PUBLIC}/medley/watch/"
    echo "  Control:    ${PUBLIC}/medley/control/   (nginx login)"
  else
    echo "  NetHub:     localhost:${NETHUB_PORT}"
    echo "  Watch:      http://localhost:${MEDLEY_WATCH_PORT}/vnc.html?autoconnect=1&view_only=1&resize=scale"
    echo "  Control:    http://localhost:${MEDLEY_CONTROL_PORT}/vnc.html?autoconnect=1&resize=scale"
  fi
}

# Is the resident Medley at the house?  The backend's health says how many Medleys are on its
# NetHub and how many players they offer to everyone.
resident_state() {
  curl -s --max-time 5 "http://localhost:${BACKEND_PORT}/health" | python3 -c '
import json, sys
try:
    h = json.load(sys.stdin)
except Exception:
    print("no answer from the backend"); sys.exit()
if h.get("medleys") is None:
    print("the backend has no NetHub (HEARTS_NETHUB_PORT is not set)")
elif h.get("offered"):
    print("offering %d players (%d Medley(s) on the NetHub)" % (h["offered"], h["medleys"]))
elif h["medleys"]:
    print("%d Medley(s) on the NetHub, none offering players now (in a game, or still loading)" % h["medleys"])
else:
    print("no Medley on the NetHub yet (the resident takes a minute or two to load the Expert)")'
}

check() {  # check LABEL URL [EXPECTED-CODE]
  local code; code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$2" || true)"
  if [ "$code" = "${3:-200}" ]; then printf '  %-10s ok\n' "$1"; else printf '  %-10s DOWN (%s)\n' "$1" "${code:-no answer}"; fi
}

health() {
  check backend "http://localhost:${BACKEND_PORT}/health"
  if [ "$ENVIRON" = "prod" ] || [ -n "$($RESIDENT ps -q medley 2>/dev/null)" ]; then
    check watch "http://localhost:${MEDLEY_WATCH_PORT}/vnc.html"
    check control "http://localhost:${MEDLEY_CONTROL_PORT}/vnc.html"
    printf '  %-10s %s\n' resident "$(resident_state)"
  fi
}

install_medley_files() {
  mkdir -p "$IL_DIR"
  for f in dist/*; do
    case "$(basename "$f")" in README.md) continue ;; esac
    cp -p "$f" "$IL_DIR/"
  done
  echo "HEARTS files copied to $IL_DIR"
}

case "$CMD" in

  # --- The Python web platform (and, in prod, everything on the server) -------------------
  start)   environ "${1:-}"; $COMPOSE up -d --build && print_urls ;;
  stop)    environ "${1:-}"; $COMPOSE down ;;
  restart) environ "${1:-}"; $COMPOSE down && $COMPOSE up -d --build && print_urls ;;
  build)   environ "${1:-}"; $COMPOSE build ;;
  logs)    environ "${1:-}"; shift || true; $COMPOSE logs -f "$@" ;;
  ps|status) environ "${1:-}"; $COMPOSE ps && print_urls ;;
  urls)    environ "${1:-}"; print_urls ;;
  health)  environ "${1:-}"; health ;;
  smoke)
    SMOKE_BASE_URL="http://localhost:${BACKEND_PORT}" python3 scripts/smoke_test.py ;;
  test)
    python -m pytest backend/tests -q && ( cd frontend && npm test ) ;;
  invite)
    # ./hearts.sh invite dev "for Ana" prints a code and link for one new player.
    environ "${1:-}"
    : "${HEARTS_ADMIN_PASSWORD:?set HEARTS_ADMIN_PASSWORD in .env}"
    NOTE="${2:-}"
    BODY="$(python3 -c 'import json,sys; print(json.dumps({"note": sys.argv[1]}))' "$NOTE")"
    CODE="$(curl -fsS -X POST "http://localhost:${BACKEND_PORT}/api/admin/invites" \
      -H "X-Hearts-Admin: ${HEARTS_ADMIN_PASSWORD}" -H 'Content-Type: application/json' -d "$BODY" \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["code"])')"
    if [ "$ENVIRON" = "prod" ]; then
      echo "${PUBLIC}/?invite=${CODE}"
    else
      echo "http://localhost:${FRONTEND_PORT}/?invite=${CODE}"
    fi ;;
  backup-db)
    environ "${1:-}"
    mkdir -p backups
    OUT="backups/hearts-$(date +%Y%m%d-%H%M%S).db"
    $COMPOSE exec -T backend python -c 'import sqlite3,sys; s=sqlite3.connect("/data/db/hearts.db"); d=sqlite3.connect("/tmp/backup.db"); s.backup(d); d.close()'
    $COMPOSE cp backend:/tmp/backup.db "$OUT"
    echo "$OUT" ;;
  deploy)
    # Run on the server, from the checked-out repo: the web platform (with its NetHub) and
    # the resident Medley.
    environ "${1:-}"
    [ "$ENVIRON" = "prod" ] || { echo "deploy is for prod; use start for dev"; exit 1; }
    git pull --ff-only
    $COMPOSE up -d --build --remove-orphans
    echo "==> waiting for health"
    for i in $(seq 1 30); do
      if curl -fsS "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1; then
        health; print_urls; exit 0
      fi
      sleep 2
    done
    echo "health check failed"; $COMPOSE logs --tail 50 backend; exit 1 ;;

  # --- The resident Medley (docker-compose.server.yml) -------------------------------------
  resident)
    environ "${1:-}"
    $RESIDENT up -d --build --no-deps medley
    echo ""; print_resident_urls; echo ""
    echo "  The resident takes a minute or two to load; ./hearts.sh health $ENVIRON says when it is offering players." ;;
  resident-stop)    environ "${1:-}"; $RESIDENT stop medley ;;
  resident-restart) environ "${1:-}"; $RESIDENT restart medley ;;
  resident-logs)    environ "${1:-}"; $RESIDENT logs -f medley ;;
  control-login)
    # The login for the resident's control screen (nginx basic auth), on the server.
    USER_NAME="${1:-${USER:-harley}}"
    command -v htpasswd >/dev/null || { echo "needs htpasswd: sudo apt install apache2-utils"; exit 1; }
    FILE=/etc/nginx/hearts-medley.htpasswd
    if [ -f "$FILE" ]; then sudo htpasswd "$FILE" "$USER_NAME"; else sudo htpasswd -c "$FILE" "$USER_NAME"; fi
    echo "Now: sudo nginx -t && sudo systemctl reload nginx" ;;

  nginx-install)
    # On the server: add the resident Medley locations to the site's server block
    # (scripts/nginx_install.py), check the result with nginx -t, then reload, or put the old
    # file back.  Safe to run again: it replaces its earlier copy.
    SITE="${NGINX_SITE:-/etc/nginx/sites-enabled/apps.athenadecisions.com}"
    [ -e "$SITE" ] || SITE=/etc/nginx/sites-available/apps.athenadecisions.com
    SITE="$(readlink -f "$SITE")"
    [ -f "$SITE" ] || { echo "no nginx site file: set NGINX_SITE"; exit 1; }
    [ -f /etc/nginx/hearts-medley.htpasswd ] || echo "note: no control login yet; make one with ./hearts.sh control-login"
    TMP="$(mktemp)"
    sudo cat "$SITE" > "$TMP.site"
    python3 scripts/nginx_install.py "$TMP.site" nginx/hearts-apps-location.conf "$TMP" || { rm -f "$TMP" "$TMP.site"; exit 1; }
    BAK="$SITE.bak-$(date +%Y%m%d-%H%M%S)"
    sudo cp -p "$SITE" "$BAK"
    sudo cp "$TMP" "$SITE"
    rm -f "$TMP" "$TMP.site"
    if sudo nginx -t; then
      sudo systemctl reload nginx && echo "nginx reloaded ($SITE; the old file is $BAK)"
    else
      sudo cp -p "$BAK" "$SITE"; echo "nginx -t failed, so $SITE is back as it was"; exit 1
    fi ;;

  # --- Medley on this computer -------------------------------------------------------------
  medley)
    # ./hearts.sh medley [ID]   Copy the HEARTS files to ~/il and start Medley.  A second
    # Medley alongside needs its own ID, e.g. ./hearts.sh medley guest.
    [ -n "$MEDLEY_DIR" ] && [ -x "$MEDLEY_DIR/medley" ] || { echo "no Medley found: set MEDLEY_DIR to the release's medley/ directory"; exit 1; }
    install_medley_files
    ARGS=(--apps --interlisp --noscroll)
    [ -n "${1:-}" ] && ARGS+=(--id "$1")
    # Online play needs an emulator with NetHub support (./hearts.sh maiko-nethub builds one
    # beside the release).  With it, Medley joins the house's NetHub; HEARTS_NETHUB=HOST:PORT
    # names another house, e.g. localhost:3333 for ./hearts.sh start dev.
    HUB="${HEARTS_NETHUB:-apps.athenadecisions.com:${NETHUB_PORT}}"
    if [ -x "$NETHUB_MAIKO/bin/osversion" ]; then
      # The emulator joins the hub only as it starts, and waits a long time for one that
      # doesn't answer: so look first.
      if python3 -c 'import socket, sys; socket.create_connection((sys.argv[1], int(sys.argv[2])), 3)' "${HUB%:*}" "${HUB##*:}" 2>/dev/null; then
        MAC="10-00-$(printf '%s' "$(hostname)${1:-}" | cksum | awk '{printf "%08X", $1}' | sed 's/../&-/g; s/-$//')"
        ARGS+=(--maikodir "$NETHUB_MAIKO" --nethub "${HUB}:${MAC}")
        echo "Online play: on the NetHub at ${HUB} as ${MAC}"
      else
        echo "Online play is off: no NetHub answers at ${HUB}.  (HEARTS_NETHUB=HOST:PORT names another.)"
      fi
    else
      echo "Online play is off: this emulator has no NetHub support.  ./hearts.sh maiko-nethub builds one that has."
    fi
    if [ "$(uname)" = Darwin ]; then open -a XQuartz; export OSTYPE=darwin; fi
    echo "Starting Medley from $MEDLEY_DIR.  At the Exec: (FILESLOAD PLAYHEARTS) (PlayHearts)"
    cd "$MEDLEY_DIR" && exec ./medley "${ARGS[@]}" ;;
  maiko-nethub)
    # Build Maiko, Medley's emulator, with NetHub support, into maiko-nethub/ beside the Medley
    # release, which is left as it is.  The released emulators are built without it.  Needs a
    # C compiler and the X11 headers (on a Mac: the Xcode command line tools and XQuartz).
    [ -n "$MEDLEY_DIR" ] || { echo "no Medley found: set MEDLEY_DIR to the release's medley/ directory"; exit 1; }
    TAG="${MAIKO_TAG:-maiko-260319-9259716e}"     # The Maiko of Medley release 260810.
    SRC="$NETHUB_MAIKO.src"
    rm -rf "$SRC"
    git clone --depth 1 --branch "$TAG" https://github.com/Interlisp/maiko.git "$SRC"
    ( cd "$SRC/bin"
      if [ "$(uname)" = Darwin ]; then
        # The Darwin makefiles take no extra flags from the environment.
        sed -i '' 's/^DEBUGFLAGS *=.*/DEBUGFLAGS = -DMAIKO_ENABLE_NETHUB/' makefile-darwin.*-x
        ./makeright x
      else
        ADDITIONAL_DFLAGS=-DMAIKO_ENABLE_NETHUB ./makeright x
      fi )
    BUILT="$SRC/$("$SRC/bin/osversion").$("$SRC/bin/machinetype")"
    case "$("$BUILT/ldex" -help 2>&1 || true)" in
      *nh-host*) ;;
      *) echo "the build has no NetHub option"; exit 1 ;;
    esac
    rm -rf "$NETHUB_MAIKO"; mkdir -p "$NETHUB_MAIKO"
    cp -R "$SRC/bin" "$BUILT" "$NETHUB_MAIKO/"
    rm -rf "$SRC"
    echo "Built $NETHUB_MAIKO.  ./hearts.sh medley now starts Medley on the house's NetHub." ;;
  medley-install) install_medley_files ;;
  medley-build)   python3 medley/build-loadfile.py && install_medley_files ;;
  medley-test)
    # ./hearts.sh medley-test [all|net|SCRIPT]   The headless tests, in Docker.
    case "${1:-all}" in
      all) tests/run-all.sh ;;
      net) tests/run-courier.sh && tests/courier/run.sh ;;
      *)   tools/medley-headless "$@" ;;
    esac ;;

  help|*)
    cat <<EOF
HEARTS ops — ./hearts.sh <command> [dev|prod] [args]

The Python web platform (in prod: everything on the server)
  start | stop | restart | build | status | urls [dev|prod]
  logs [dev|prod] [SERVICE...]
  health [dev|prod]          backend, and the resident Medley when it runs
  smoke | test               smoke tests against the running stack | backend and frontend tests
  invite [dev|prod] [NOTE]   a code and link for one new player
  backup-db [dev|prod]       copy the SQLite database to ./backups
  deploy prod                on the server: pull, rebuild, restart everything, check health

The resident Medley (docs/medley-server.md)
  resident [dev|prod]        start the resident Medley (dev: on this computer)
  resident-stop | resident-restart | resident-logs [dev|prod]
  control-login [USER]       on the server: the login for the resident's control screen
  nginx-install              on the server: add the resident's screen locations to nginx, check, reload

Medley on this computer (Medley found: ${MEDLEY_DIR:-none; set MEDLEY_DIR})
  medley [ID]                copy the HEARTS files to ${IL_DIR} and start Medley
  maiko-nethub               build an emulator with NetHub support beside the release, for online play
  medley-install             copy the HEARTS files (dist/) to ${IL_DIR}
  medley-build               rebuild dist/ from medley/ and copy it to ${IL_DIR}
  medley-test [all|net|SCRIPT]  headless tests in Docker: all, the Courier game, or one script
EOF
    ;;
esac
