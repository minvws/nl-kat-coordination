SHELL := bash
.ONESHELL:

# use HIDE to run commands invisibly, unless VERBOSE defined
HIDE:=$(if $(VERBOSE),,@)
UNAME := $(shell uname)

.PHONY: kat rebuild update clean migrate build itest debian-build-image ubuntu-build-image

# Export Docker buildkit options
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

kat: env-if-empty clean # This should give you a clean install
	make build
	make up

rebuild: clean
	make build
	make up

update: down pull
	make build
	make up

clean: down # This should clean up all persistent data
	-docker volume rm nl-kat-coordination_rocky-db-data nl-kat-coordination_bytes-db-data nl-kat-coordination_bytes-data nl-kat-coordination_katalogus-db-data nl-kat-coordination_xtdb-data nl-kat-coordination_scheduler-db-data

export version

upgrade: fetch down # Upgrade to the latest release without losing persistent data. Usage: `make upgrade version=v1.5.0` (version is optional)
ifeq ($(version),)
	version=$(shell curl --silent  "https://api.github.com/repos/minvws/nl-kat-coordination/tags" | jq -r '.[].name' | grep -v "rc" | head -n 1)
	make upgrade version=$$version
else
	make checkout branch=$(version)
	make build-all
	make up
endif

reset: down
	-docker volume rm nl-kat-coordination_bytes-db-data nl-kat-coordination_bytes-data nl-kat-coordination_katalogus-db-data nl-kat-coordination_xtdb-data nl-kat-coordination_scheduler-db-data
	make up
	make -C boefjes build
	make -C rocky almost-flush

up:
	docker-compose up -d --force-recreate

down:
	-docker-compose down

fetch:
	-git fetch

pull:
	-git pull

env-if-empty:
ifeq ("$(wildcard .env)","")
	make env
endif

env:  # Create .env file from the env-dist with randomly generated credentials from vars annotated by "{%EXAMPLE_VAR}"
	$(HIDE) cp .env-dist .env
ifeq ($(UNAME), Darwin)  # Different sed on MacOS
	$(HIDE) grep -o "{%\([_A-Z]*\)}" .env-dist | sort -u | while read v; do sed -i '' "s/$$v/$$(openssl rand -hex 25)/g" .env; done
else
	$(HIDE) grep -o "{%\([_A-Z]*\)}" .env-dist | sort -u | while read v; do sed -i "s/$$v/$$(openssl rand -hex 25)/g" .env; done
endif

checkout: # Usage: `make checkout branch=develop`
	-git checkout $(branch)

pull-reset:
	-git reset --hard HEAD
	-git pull

build-all:  # Build should prepare all other services: migrate them, seed them, etc.
ifeq ($(UNAME), Darwin)
	docker-compose build --build-arg USER_UID="$$(id -u)"
else
	docker-compose build --build-arg USER_UID="$$(id -u)" --build-arg USER_GID="$$(id -g)"
endif

build: build-all
	make -C rocky build
	make -C boefjes build

debian-build-image:
	docker build -t kat-debian-build-image packaging/debian

ubuntu-build-image:
	docker build -t kat-ubuntu-build-image packaging/ubuntu
