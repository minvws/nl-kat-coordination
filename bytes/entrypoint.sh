#!/bin/bash
set -e

# Make env variable comparison case insensitive
shopt -s nocasematch

if [ "$DATABASE_MIGRATION" = "1" ] || [[ $DATABASE_MIGRATION == "true" ]]; then
    (cd /app/bytes/ && uv run alembic --config bytes/alembic.ini upgrade head)
fi

exec "$@"
