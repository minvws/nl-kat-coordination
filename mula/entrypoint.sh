#!/bin/bash
set -e

# Make env variable comparison case insensitive
shopt -s nocasematch

if [ "$DATABASE_MIGRATION" = "1" ] || [[ $DATABASE_MIGRATION == "true" ]]; then
    (cd /app/scheduler && uv run alembic --config scheduler/storage/migrations/alembic.ini upgrade head)
fi

exec "$@"
