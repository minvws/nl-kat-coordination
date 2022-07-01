#!/bin/bash

# Reference: https://hub.docker.com/_/postgres

set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	CREATE USER ${!APP_DB_USER} WITH ENCRYPTED PASSWORD '${!APP_DB_PASSWORD}';
	CREATE DATABASE ${!APP_DB};
	ALTER DATABASE ${!APP_DB} OWNER TO ${!APP_DB_USER};
EOSQL
