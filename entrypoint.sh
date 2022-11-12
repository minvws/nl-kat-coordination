#!/bin/bash
set -e

# Make env variable comparison case insensitive
shopt -s nocasematch

if [ "$1" = "boefje" ]; then
    exec python -m boefjes boefje
elif [ "$1" = "normalizer" ]; then
    exec python -m boefjes normalizer
fi

# The migrations are for katalogus. They are not inside the if because this way
# they can also be run when overruling the default cmd
if [ "$DATABASE_MIGRATION" = "1" ] || [  "$DATABASE_MIGRATION" = "true" ]; then
    python -m alembic upgrade head
fi

if [ "$1" = "katalogus" ]; then
    exec python -m uvicorn --host 0.0.0.0 boefjes.katalogus.api:app
fi

exec "$@"
