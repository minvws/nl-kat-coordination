#!/bin/bash

set -e

# To ensure the postgres container is up and running
sleep 1

python manage.py migrate
python manage.py loaddata /app/rocky_db_seed.json
python manage.py test
