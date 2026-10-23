#!/usr/bin/env sh
set -eu
test -n "${RESTORE_DATABASE_URL:-}"
test -f "$1"
sha256sum --check "$1.sha256"
pg_restore --dbname="$RESTORE_DATABASE_URL" --clean --if-exists --no-owner "$1"
psql "$RESTORE_DATABASE_URL" -v ON_ERROR_STOP=1 -c "SELECT count(*) FROM dataset_versions WHERE status = 'active';"
