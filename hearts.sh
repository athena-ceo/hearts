#!/usr/bin/env bash
# Copyright (c) 2026 Athena Decision Systems SAS.
#
# Control script for HEARTS (mirrors advent.sh / xcape.sh / golden-path): the Python web
# platform, Medley on this computer, and the resident Medley and relay on the server.
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
RELAY_PORT="${RELAY_PORT:-8051}"
MEDLEY_WATCH_PORT="${MEDLEY_WATCH_PORT:-8052}"
MEDLEY_CONTROL_PORT="${MEDLEY_CONTROL_PORT:-8053}"
PUBLIC="https://apps.athenadecisions.com/hearts"
# Medley on this computer: the release directory and the folder Medley loads files from.
IL_DIR="${HEARTS_IL:-$HOME/il}"
MEDLEY_DIR="${MEDLEY_DIR:-$(ls -d "$HOME"/medley-*/medley 2>/dev/null | sort | tail -1 || true)}"

# The commands that take dev|prod read it here.
environ() {
  ENVIRON="${1:-dev}"
  case "$ENVIRON" in
    dev)  COMPOSE="docker compose -p hearts-dev -f docker-compose.dev.yml"
          # The resident Medley and relay are only in the server file: locally they run as
          # their own project, beside the dev stack.
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
    echo "  Relay:      wss://apps.athenadecisions.com/hearts   (room athena: the resident Medley)"
    echo "  Watch:      ${PUBLIC}/medley/watch/"
    echo "  Control:    ${PUBLIC}/medley/control/   (nginx login)"
  else
    echo "  Relay:      ws://localhost:${RELAY_PORT}"
    echo "  Watch:      http://localhost:${MEDLEY_WATCH_PORT}/vnc.html?autoconnect=1&view_only=1&resize=scale"
    echo "  Control:    http://localhost:${MEDLEY_CONTROL_PORT}/vnc.html?autoconnect=1&resize=scale"
  fi
}

# Is the resident Medley in its room?  Reads the relay's log: the last thing it said about it.
resident_state() {
  local name="${RESIDENT_NAME:-athena}" last
  last="$($RESIDENT logs relay 2>/dev/null | grep -E " ${name} (joined|left) " | tail -1 || true)"
  case "$last" in
    *joined*) echo "in its room" ;;
    *left*)   echo "left its room (restarting?)" ;;
    *)        echo "not in its room yet (it takes a minute or two to load the Expert)" ;;
  esac
}

check() {  # check LABEL URL [EXPECTED-CODE]
  local code; code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$2" || true)"
  if [ "$code" = "${3:-200}" ]; then printf '  %-10s ok\n' "$1"; else printf '  %-10s DOWN (%s)\n' "$1" "${code:-no answer}"; fi
}

health() {
  check backend "http://localhost:${BACKEND_PORT}/health"
  if [ "$ENVIRON" = "prod" ] || [ -n "$($RESIDENT ps -q relay 2>/dev/null)" ]; then
    check relay "http://localhost:${RELAY_PORT}/" 426      # a WebSocket server: plain HTTP gets 426
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
    # Run on the server, from the checked-out repo: the web platform, the relay and the
    # resident Medley.
    environ "${1:-}"
    [ "$ENVIRON" = "prod" ] || { echo "deploy is for prod; use start for dev"; exit 1; }
    git pull --ff-only
    $COMPOSE up -d --build
    echo "==> waiting for health"
    for i in $(seq 1 30); do
      if curl -fsS "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1; then
        health; print_urls; exit 0
      fi
      sleep 2
    done
    echo "health check failed"; $COMPOSE logs --tail 50 backend; exit 1 ;;

  # --- The resident Medley and the relay (docker-compose.server.yml) -----------------------
  resident)
    environ "${1:-}"
    $RESIDENT up -d --build relay medley
    echo ""; print_resident_urls; echo ""
    echo "  The resident takes a minute or two to load; ./hearts.sh health $ENVIRON says when it's in its room." ;;
  resident-stop)    environ "${1:-}"; $RESIDENT stop medley relay ;;
  resident-restart) environ "${1:-}"; $RESIDENT restart medley relay ;;
  resident-logs)    environ "${1:-}"; $RESIDENT logs -f relay medley ;;
  control-login)
    # The login for the resident's control screen (nginx basic auth), on the server.
    USER_NAME="${1:-${USER:-harley}}"
    command -v htpasswd >/dev/null || { echo "needs htpasswd: sudo apt install apache2-utils"; exit 1; }
    FILE=/etc/nginx/hearts-medley.htpasswd
    if [ -f "$FILE" ]; then sudo htpasswd "$FILE" "$USER_NAME"; else sudo htpasswd -c "$FILE" "$USER_NAME"; fi
    echo "Now: sudo nginx -t && sudo systemctl reload nginx" ;;

  nginx-install)
    # On the server: add the relay and resident Medley locations to the site's server block
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
    if [ "$(uname)" = Darwin ]; then open -a XQuartz; export OSTYPE=darwin; fi
    echo "Starting Medley from $MEDLEY_DIR.  At the Exec: (FILESLOAD PLAYHEARTS) (PlayHearts)"
    cd "$MEDLEY_DIR" && exec ./medley "${ARGS[@]}" ;;
  medley-install) install_medley_files ;;
  medley-build)   python3 medley/build-loadfile.py && install_medley_files ;;
  medley-test)
    # ./hearts.sh medley-test [all|net|SCRIPT]   The headless tests, in Docker.
    case "${1:-all}" in
      all) tests/run-all.sh ;;
      net) python3 tests/test_hnet.py && tests/run-hnet.sh && tools/medley-headless tests/netguide.lisp ;;
      *)   tools/medley-headless "$@" ;;
    esac ;;
  relay)
    # ./hearts.sh relay [PORT]   A relay on this computer, for Medleys on the same network.
    PORT="${1:-8765}"
    ADDR="$( (ipconfig getifaddr en0 || hostname -I | awk '{print $1}') 2>/dev/null || true)"
    echo "Medleys on this network connect with (HNET.Connect \"ROOM\" \"NAME\" \"ws://${ADDR:-THIS-COMPUTER}:${PORT}\")"
    exec python3 medley/hnetrelay.py --port "$PORT" ;;

  help|*)
    cat <<EOF
HEARTS ops — ./hearts.sh <command> [dev|prod] [args]

The Python web platform (in prod: everything on the server)
  start | stop | restart | build | status | urls [dev|prod]
  logs [dev|prod] [SERVICE...]
  health [dev|prod]          backend, and the relay and resident Medley when they run
  smoke | test               smoke tests against the running stack | backend and frontend tests
  invite [dev|prod] [NOTE]   a code and link for one new player
  backup-db [dev|prod]       copy the SQLite database to ./backups
  deploy prod                on the server: pull, rebuild, restart everything, check health

The resident Medley and the relay (docs/medley-server.md)
  resident [dev|prod]        start the relay and the resident Medley (dev: on this computer)
  resident-stop | resident-restart | resident-logs [dev|prod]
  control-login [USER]       on the server: the login for the resident's control screen
  nginx-install              on the server: add the relay and screen locations to nginx, check, reload

Medley on this computer (Medley found: ${MEDLEY_DIR:-none; set MEDLEY_DIR})
  medley [ID]                copy the HEARTS files to ${IL_DIR} and start Medley
  medley-install             copy the HEARTS files (dist/) to ${IL_DIR}
  medley-build               rebuild dist/ from medley/ and copy it to ${IL_DIR}
  medley-test [all|net|SCRIPT]  headless tests in Docker: all, the network game, or one script
  relay [PORT]               a relay here, for Medleys on the same network (default 8765)
EOF
    ;;
esac
