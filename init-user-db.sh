#!/bin/bash

# Reference: https://hub.docker.com/_/postgres

set -e

for APP in ${APPS}; do
    echo "Creating role and database for ${APP}"
    APP_DB="${APP}_DB"
    APP_DB_USER="${APP}_DB_USER"
    APP_DB_USER_CREATEDB="${APP}_DB_USER_CREATEDB"
    APP_DB_PASSWORD="${APP}_DB_PASSWORD"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<- EOSQL
		CREATE ROLE ${!APP_DB_USER} WITH ENCRYPTED PASSWORD '${!APP_DB_PASSWORD}' ${!APP_DB_USER_CREATEDB:-NOCREATEDB} LOGIN;
		CREATE DATABASE ${!APP_DB};
		ALTER DATABASE ${!APP_DB} OWNER TO ${!APP_DB_USER};
	EOSQL
done
