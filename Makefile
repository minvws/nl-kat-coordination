SHELL := bash
.ONESHELL:

# use HIDE to run commands invisibly, unless VERBOSE defined
HIDE:=$(if $(VERBOSE),,@)
UNAME := $(shell uname)


.PHONY: kat kat-stable clone migrate build itest debian-build-image ubuntu-build-image

# Export Docker buildkit options
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1



kat:  # This should give you a clean install
ifeq ("$(wildcard .env)","")
	make env
endif
	make clean
	make clone
	make build
	make up


kat-stable:  # This should give you a clean install of a stable version
ifeq ("$(wildcard .env)","")
	make env
endif
	make clean
	make clone-main
	make build
	make up

rebuild:
	make clean
	make build
	make up

update:
	-docker-compose down
	make pull
	make build
	make up

clean:
	-docker-compose down
	-docker volume rm nl-kat_rocky-db-data nl-kat_bytes-db-data nl-kat_katalogus-db-data nl-kat_xtdb-data

up:
	docker-compose up -d --force-recreate rocky

down:
	-docker-compose down

clone:
	-git clone git@github.com:minvws/nl-kat-boefjes.git
	-git clone git@github.com:minvws/nl-kat-bytes.git
	-git clone git@github.com:minvws/nl-kat-octopoes.git
	-git clone git@github.com:minvws/nl-kat-mula.git
	-git clone git@github.com:minvws/nl-kat-keiko.git
	-git clone git@github.com:minvws/nl-kat-rocky.git

clone-main:
	-git clone --branch main git@github.com:minvws/nl-kat-boefjes.git
	-git clone --branch main git@github.com:minvws/nl-kat-bytes.git
	-git clone --branch main git@github.com:minvws/nl-kat-octopoes.git
	-git clone --branch main git@github.com:minvws/nl-kat-mula.git
	-git clone --branch main git@github.com:minvws/nl-kat-keiko.git
	-git clone --branch main git@github.com:minvws/nl-kat-rocky.git

pull:
	-git pull
	-git -C nl-kat-boefjes pull
	-git -C nl-kat-bytes pull
	-git -C nl-kat-octopoes pull
	-git -C nl-kat-mula pull
	-git -C nl-kat-keiko pull
	-git -C nl-kat-rocky pull

env:  # Create .env file from the env-dist with randomly generated credentials from vars annotated by "{%EXAMPLE_VAR}"
	$(HIDE) cp .env-dist .env
ifeq ($(UNAME), Darwin)  # Different sed on MacOS
	$(HIDE) grep -o "{%\([_A-Z]*\)}" .env-dist | sort -u | while read v; do sed -i '' "s/$$v/$$(openssl rand -hex 25)/g" .env; done
else
	$(HIDE) grep -o "{%\([_A-Z]*\)}" .env-dist | sort -u | while read v; do sed -i "s/$$v/$$(openssl rand -hex 25)/g" .env; done
endif

checkout: # Usage: `make checkout branch=develop`
	-git checkout $(branch)
	-git -C nl-kat-boefjes checkout $(branch)
	-git -C nl-kat-bytes checkout $(branch)
	-git -C nl-kat-octopoes checkout $(branch)
	-git -C nl-kat-mula checkout $(branch)
	-git -C nl-kat-keiko checkout $(branch)
	-git -C nl-kat-rocky checkout $(branch)

pull-reset:
	-git reset --hard HEAD
	-git pull
	-git -C nl-kat-boefjes reset --hard HEAD
	-git -C nl-kat-boefjes pull
	-git -C nl-kat-bytes reset --hard HEAD
	-git -C nl-kat-bytes pull
	-git -C nl-kat-octopoes reset --hard HEAD
	-git -C nl-kat-octopoes pull
	-git -C nl-kat-mula reset --hard HEAD
	-git -C nl-kat-mula pull
	-git -C nl-kat-keiko reset --hard HEAD
	-git -C nl-kat-keiko pull
	-git -C nl-kat-rocky reset --hard HEAD
	-git -C nl-kat-rocky pull

build:  # Build should prepare all other services: migrate them, seed them, etc.
ifeq ($(UNAME), Darwin)
	docker-compose build --build-arg USER_UID="$$(id -u)"
else
	docker-compose build --build-arg USER_UID="$$(id -u)" --build-arg USER_GID="$$(id -g)"
endif
	docker-compose run --rm rocky make build-rocky
	make -C nl-kat-rocky build-rocky-frontend
	make -C nl-kat-boefjes build
	make -C nl-kat-bytes build

debian-build-image:
	docker build -t kat-debian-build-image packaging/debian

ubuntu-build-image:
	docker build -t kat-ubuntu-build-image packaging/ubuntu
