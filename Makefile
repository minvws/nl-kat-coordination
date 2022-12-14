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
	-docker volume rm nl-rt-tim-abang_rocky-db-data nl-rt-tim-abang_bytes-db-data nl-rt-tim-abang_katalogus-db-data nl-rt-tim-abang_xtdb-data

up:
	docker-compose up -d --force-recreate rocky

down:
	-docker-compose down

clone:
	-git clone git@github.com:minvws/nl-rt-tim-abang-boefjes.git
	-git clone git@github.com:minvws/nl-rt-tim-abang-bytes.git
	-git clone git@github.com:minvws/nl-rt-tim-abang-octopoes.git
	-git clone git@github.com:minvws/nl-rt-tim-abang-mula.git
	-git clone git@github.com:minvws/nl-rt-tim-abang-keiko.git
	-git clone git@github.com:minvws/nl-rt-tim-abang-rocky.git

clone-main:
	-git clone --branch main git@github.com:minvws/nl-rt-tim-abang-boefjes.git
	-git clone --branch main git@github.com:minvws/nl-rt-tim-abang-bytes.git
	-git clone --branch main git@github.com:minvws/nl-rt-tim-abang-octopoes.git
	-git clone --branch main git@github.com:minvws/nl-rt-tim-abang-mula.git
	-git clone --branch main git@github.com:minvws/nl-rt-tim-abang-keiko.git
	-git clone --branch main git@github.com:minvws/nl-rt-tim-abang-rocky.git

pull:
	-git pull
	-git -C nl-rt-tim-abang-boefjes pull
	-git -C nl-rt-tim-abang-bytes pull
	-git -C nl-rt-tim-abang-octopoes pull
	-git -C nl-rt-tim-abang-mula pull
	-git -C nl-rt-tim-abang-keiko pull
	-git -C nl-rt-tim-abang-rocky pull

env:  # Create .env file from the env-dist with randomly generated credentials from vars annotated by "{%EXAMPLE_VAR}"
	$(HIDE) cp .env-dist .env
ifeq ($(UNAME), Darwin)  # Different sed on MacOS
	$(HIDE) grep -o "{%\([_A-Z]*\)}" .env-dist | sort -u | while read v; do sed -i '' "s/$$v/$$(openssl rand -hex 25)/g" .env; done
else
	$(HIDE) grep -o "{%\([_A-Z]*\)}" .env-dist | sort -u | while read v; do sed -i "s/$$v/$$(openssl rand -hex 25)/g" .env; done
endif

checkout: # Usage: `make checkout branch=develop`
	-git checkout $(branch)
	-git -C nl-rt-tim-abang-boefjes checkout $(branch)
	-git -C nl-rt-tim-abang-bytes checkout $(branch)
	-git -C nl-rt-tim-abang-octopoes checkout $(branch)
	-git -C nl-rt-tim-abang-mula checkout $(branch)
	-git -C nl-rt-tim-abang-keiko checkout $(branch)
	-git -C nl-rt-tim-abang-rocky checkout $(branch)

pull-reset:
	-git reset --hard HEAD
	-git pull
	-git -C nl-rt-tim-abang-boefjes reset --hard HEAD
	-git -C nl-rt-tim-abang-boefjes pull
	-git -C nl-rt-tim-abang-bytes reset --hard HEAD
	-git -C nl-rt-tim-abang-bytes pull
	-git -C nl-rt-tim-abang-octopoes reset --hard HEAD
	-git -C nl-rt-tim-abang-octopoes pull
	-git -C nl-rt-tim-abang-mula reset --hard HEAD
	-git -C nl-rt-tim-abang-mula pull
	-git -C nl-rt-tim-abang-keiko reset --hard HEAD
	-git -C nl-rt-tim-abang-keiko pull
	-git -C nl-rt-tim-abang-rocky reset --hard HEAD
	-git -C nl-rt-tim-abang-rocky pull

build:  # Build should prepare all other services: migrate them, seed them, etc.
ifeq ($(UNAME), Darwin)
	docker-compose build --build-arg USER_UID="$$(id -u)"
else
	docker-compose build --build-arg USER_UID="$$(id -u)" --build-arg USER_GID="$$(id -g)"
endif
	docker-compose run --rm rocky make build-rocky
	make -C nl-rt-tim-abang-rocky build-rocky-frontend
	make -C nl-rt-tim-abang-boefjes build
	make -C nl-rt-tim-abang-bytes build

debian-build-image:
	docker build -t kat-debian-build-image packaging/debian

ubuntu-build-image:
	docker build -t kat-ubuntu-build-image packaging/ubuntu
