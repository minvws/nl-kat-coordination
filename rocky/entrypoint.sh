#!/bin/bash
set -e

# Make env variable comparison case insensitive
shopt -s nocasematch

if [ "$DATABASE_MIGRATION" = "1" ] || [[ $DATABASE_MIGRATION == "true" ]]; then
    uv run --no-sync manage.py migrate --noinput
fi

if [ "$1" = "web" ]; then
    exec uv run --no-sync granian --interface wsgi rocky.wsgi:application --host 0.0.0.0
elif [ "$1" = "worker" ]; then
    exec uv run --no-sync manage.py worker
fi

exec "$@"
