#!/bin/bash
set -e

# Make env variable comparison case insensitive
shopt -s nocasematch

if [ "$DATABASE_MIGRATION" = "1" ] || [  "$DATABASE_MIGRATION" = "true" ]; then
    python -m alembic --config /app/bytes/bytes/alembic.ini upgrade head
fi

exec "$@"
