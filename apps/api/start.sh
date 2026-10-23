#!/usr/bin/env sh
set -eu

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  alembic -c /app/alembic.ini upgrade head
fi

exec uvicorn restaurant_recommender.main:app \
  --host "${APP_HOST:-0.0.0.0}" \
  --port "${PORT:-${APP_PORT:-8000}}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --timeout-graceful-shutdown "${GRACEFUL_SHUTDOWN_SECONDS:-20}" \
  --no-access-log
