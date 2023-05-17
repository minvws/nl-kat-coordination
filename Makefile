SHELL := bash
.ONESHELL:
.NOTPARALLEL:

# use HIDE to run commands invisibly, unless VERBOSE defined
HIDE:=$(if $(VERBOSE),,@)
UNAME := $(shell uname)

.PHONY: $(MAKECMDGOALS)

# Export Docker buildkit options
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Build and bring up all containers (default target)
kat: env-if-empty build up
	@echo
	@echo "The KAT frontend is running at http://localhost:8000,"
	@echo "credentials can be found as DJANGO_SUPERUSER_* in the .env file."
	@echo
	@echo "WARNING: This is a development environment, do not use in production!"
	@echo "See https://docs.openkat.nl/technical_design/install.html for production"
	@echo "installation instructions."

# Remove containers, update using git pull and bring up containers
update: down pull kat

# Remove all containers and volumes, and bring containers up again (data loss!)
reset: clean kat

# Bring up containers
up:
	docker-compose up --detach

# Stop containers
stop:
	-docker-compose stop

# Remove containers but not volumes (no data loss)
down:
	-docker-compose down

# Remove containers and all volumes (data loss!)
clean:
	-docker-compose down --timeout 0 --volumes --remove-orphans

# Fetch the latest changes from the Git remote
fetch:
	git fetch --all --prune --tags

# Pull the latest changes from the default upstream
pull:
	git pull

# Upgrade to the latest release without losing persistent data. Usage: `make upgrade version=v1.5.0` (version is optional)
VERSION?=$(shell curl -sSf "https://api.github.com/repos/minvws/nl-kat-coordination/tags" | jq -r '[.[].name | select(. | contains("rc") | not)][0]')
upgrade: down fetch
	git checkout $(VERSION)
	make kat

# Create .env file only if it does not exist
env-if-empty:
ifeq ("$(wildcard .env)","")
	make env
endif

# Create .env file from the env-dist with randomly generated credentials from vars annotated by "{%EXAMPLE_VAR}"
env:
	cp .env-dist .env
	echo "Initializing .env with random credentials"
ifeq ($(UNAME), Darwin)  # Different sed on MacOS
	$(HIDE) grep -o "{%\([_A-Z]*\)}" .env-dist | sort -u | while read v; do sed -i '' "s/$$v/$$(openssl rand -hex 25)/g" .env; done
else
	$(HIDE) grep -o "{%\([_A-Z]*\)}" .env-dist | sort -u | while read v; do sed -i "s/$$v/$$(openssl rand -hex 25)/g" .env; done
endif

# Build will prepare all services: migrate them, seed them, etc.
build:
ifeq ($(UNAME),Darwin)
	docker-compose build --pull --parallel --build-arg USER_UID="$$(id -u)"
else
	docker-compose build --pull --parallel --build-arg USER_UID="$$(id -u)" --build-arg USER_GID="$$(id -g)"
endif
	make -C rocky build
	make -C boefjes build

# Build Debian build image
debian-build-image:
	docker build -t kat-debian-build-image packaging/debian

# Build Ubuntu build image
ubuntu-build-image:
	docker build -t kat-ubuntu-build-image packaging/ubuntu
