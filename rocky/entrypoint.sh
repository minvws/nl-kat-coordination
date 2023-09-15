#!/bin/bash
set -e

# Make env variable comparison case insensitive
shopt -s nocasematch

if [ "$DATABASE_MIGRATION" = "1" ] || [  "$DATABASE_MIGRATION" = "true" ]; then
    python manage.py migrate --noinput
fi

if [ "$USE_GRANIAN" = "1" ] || [  "$USE_GRANIAN" = "true" ]; then
    exec granian --workers "$GRANIAN_WORKERS" --threads "$GRANIAN_THREADS" --interface wsgi rocky.wsgi:application --host 0.0.0.0
else
    exec "$@"
fi
