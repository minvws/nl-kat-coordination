#!/bin/bash
set -e

# Make env variable comparison case insensitive
shopt -s nocasematch

if [ "$1" = "boefje" ]; then
    exec uv run --module boefjes boefje "${@:2}"
elif [ "$1" = "normalizer" ]; then
    exec uv run --module boefjes normalizer "${@:2}"
fi

# The migrations and seed are for the KATalogus. They are not inside the if clause because this way
# they can also be run when overruling the default cmd
if [ "$DATABASE_MIGRATION" = "1" ] || [[ $DATABASE_MIGRATION == "true" ]]; then
    echo Run the migrations for the boefjes database
    (cd /app/boefjes && uv run alembic --config boefjes/alembic.ini upgrade head)
fi

if [ "$1" = "katalogus" ]; then
    exec uv run --module uvicorn --host 0.0.0.0 boefjes.katalogus.root:app
fi

exec "$@"
