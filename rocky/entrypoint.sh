#!/bin/bash
set -e

# Make env variable comparison case insensitive
shopt -s nocasematch

if [ "$DATABASE_MIGRATION" = "1" ] || [[ $DATABASE_MIGRATION == "true" ]]; then
    uv run --frozen rocky/manage.py migrate --noinput
fi

if [ "$1" = "web" ]; then
    exec uv run --frozen granian --interface wsgi rocky.wsgi:application --host 0.0.0.0
elif [ "$1" = "worker" ]; then
    exec uv run --frozen rocky/manage.py worker
fi

exec "$@"
