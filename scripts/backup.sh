#!/usr/bin/env sh
set -eu
test -n "${DATABASE_URL:-}"
test -n "${BACKUP_DIRECTORY:-}"
umask 077
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIRECTORY"
pg_dump --dbname="$DATABASE_URL" --format=custom --no-owner --file="$BACKUP_DIRECTORY/nextleap-$timestamp.dump"
sha256sum "$BACKUP_DIRECTORY/nextleap-$timestamp.dump" > "$BACKUP_DIRECTORY/nextleap-$timestamp.dump.sha256"
