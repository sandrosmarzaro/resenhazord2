#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-code-only}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_NAME="bot"
HEALTH_TIMEOUT=120
HEALTH_INTERVAL=5

log() { echo "[deploy] $(date '+%H:%M:%S') $*"; }

# Guard: .env must exist before we do anything
if [[ ! -f "$APP_DIR/.env" ]]; then
  log "ERROR: .env not found at $APP_DIR/.env. Aborting."
  exit 1
fi

log "Pulling latest code..."
git -C "$APP_DIR" pull --ff-only origin main

if [[ "$MODE" == "full-rebuild" ]]; then
  log "Rebuilding image (dependency change detected)..."
  docker compose -f "$APP_DIR/docker-compose.yml" build
  docker compose -f "$APP_DIR/docker-compose.yml" up -d --force-recreate

elif [[ "$MODE" == "code-only" ]]; then
  log "Restarting container (code-only change)..."
  docker compose -f "$APP_DIR/docker-compose.yml" restart

else
  log "ERROR: Unknown mode '$MODE'."
  exit 1
fi

log "Waiting for healthy status (up to ${HEALTH_TIMEOUT}s)..."
elapsed=0
while true; do
  status=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "not_found")
  case "$status" in
    healthy)   log "Healthy. Deploy complete."; exit 0 ;;
    unhealthy) log "ERROR: Container unhealthy."; docker logs --tail 50 "$CONTAINER_NAME"; exit 1 ;;
    not_found) log "ERROR: Container not found."; exit 1 ;;
  esac
  if (( elapsed >= HEALTH_TIMEOUT )); then
    log "ERROR: Timed out after ${HEALTH_TIMEOUT}s. Status: $status"
    docker logs --tail 50 "$CONTAINER_NAME"
    exit 1
  fi
  sleep "$HEALTH_INTERVAL"
  elapsed=$(( elapsed + HEALTH_INTERVAL ))
done
