#!/usr/bin/env bash
# Copyright (c) 2026 Athena Decisions Systems SAS.
#
# Control script for the HEARTS app (mirrors advent.sh / xcape.sh / golden-path).
#   ./hearts.sh <command> [dev|prod]
#
# Commands: start stop restart logs ps build urls health smoke test invite backup-db deploy
set -euo pipefail
cd "$(dirname "$0")"

CMD="${1:-help}"
ENVIRON="${2:-dev}"
case "$ENVIRON" in
  dev)  COMPOSE="docker compose -p hearts-dev -f docker-compose.dev.yml" ;;
  prod) COMPOSE="docker compose -p hearts -f docker-compose.server.yml" ;;
  *) echo "unknown environment: $ENVIRON (use dev|prod)"; exit 1 ;;
esac

# Pick up any port overrides from .env (the same file docker compose reads).
if [ -f .env ]; then set -a; . ./.env; set +a; fi
BACKEND_PORT="${BACKEND_PORT:-8050}"
FRONTEND_PORT="${FRONTEND_PORT:-3050}"

print_urls() {
  echo ""
  echo "  Frontend:   http://localhost:${FRONTEND_PORT}"
  echo "  API docs:   http://localhost:${BACKEND_PORT}/docs      (Swagger UI)"
  echo "  Health:     http://localhost:${BACKEND_PORT}/health"
  if [ "$ENVIRON" = "prod" ]; then
    echo "  Public:     https://apps.athenadecisions.com/hearts/"
  fi
  echo ""
}

case "$CMD" in
  start)   $COMPOSE up -d --build && print_urls ;;
  stop)    $COMPOSE down ;;
  restart) $COMPOSE down && $COMPOSE up -d --build && print_urls ;;
  build)   $COMPOSE build ;;
  logs)    shift 2 2>/dev/null || true; $COMPOSE logs -f "$@" ;;
  ps)      $COMPOSE ps && print_urls ;;
  urls)    print_urls ;;
  health)
    curl -fsS "http://localhost:${BACKEND_PORT}/health" && echo ;;
  smoke)
    SMOKE_BASE_URL="http://localhost:${BACKEND_PORT}" python3 scripts/smoke_test.py ;;
  test)
    python -m pytest backend/tests -q && ( cd frontend && npm test ) ;;
  invite)
    # ./hearts.sh invite dev "for Ana" prints a code and link for one new player.
    : "${HEARTS_ADMIN_PASSWORD:?set HEARTS_ADMIN_PASSWORD in .env}"
    NOTE="${3:-}"
    BODY="$(python3 -c 'import json,sys; print(json.dumps({"note": sys.argv[1]}))' "$NOTE")"
    CODE="$(curl -fsS -X POST "http://localhost:${BACKEND_PORT}/api/admin/invites" \
      -H "X-Hearts-Admin: ${HEARTS_ADMIN_PASSWORD}" -H 'Content-Type: application/json' -d "$BODY" \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["code"])')"
    if [ "$ENVIRON" = "prod" ]; then
      echo "https://apps.athenadecisions.com/hearts/?invite=${CODE}"
    else
      echo "http://localhost:${FRONTEND_PORT}/?invite=${CODE}"
    fi ;;
  backup-db)
    mkdir -p backups
    OUT="backups/hearts-$(date +%Y%m%d-%H%M%S).db"
    $COMPOSE exec -T backend python -c 'import sqlite3,sys; s=sqlite3.connect("/data/db/hearts.db"); d=sqlite3.connect("/tmp/backup.db"); s.backup(d); d.close()'
    $COMPOSE cp backend:/tmp/backup.db "$OUT"
    echo "$OUT" ;;
  deploy)
    # Run on the server, from the checked-out repo.
    [ "$ENVIRON" = "prod" ] || { echo "deploy is for prod; use start for dev"; exit 1; }
    git pull --ff-only
    $COMPOSE up -d --build
    echo "==> waiting for health"
    for i in $(seq 1 30); do
      if curl -fsS "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1; then
        echo "healthy"; exit 0
      fi
      sleep 2
    done
    echo "health check failed"; $COMPOSE logs --tail 50 backend; exit 1 ;;
  *)
    echo "usage: ./hearts.sh {start|stop|restart|build|logs|ps|urls|health|smoke|test|invite|backup-db|deploy} [dev|prod]"
esac
