#!/bin/bash
set -e

# Make env variable comparison case insensitive
shopt -s nocasematch

if [ "$1" = "web" ]; then
    exec uvicorn octopoes.api.api:app --host 0.0.0.0 --port 80
elif [ "$1" = "scanprofiles" ]; then
    exec python -m octopoes.tasks.scanprofiles --loglevel=DEBUG
elif [ "$1" = "worker" ]; then
    exec celery -A octopoes.tasks.tasks worker --loglevel=INFO
fi

exec "$@"
