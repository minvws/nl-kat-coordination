SHELL := bash
.ONESHELL:
.NOTPARALLEL:

# use HIDE to run commands invisibly, unless VERBOSE defined
HIDE:=$(if $(VERBOSE),,@)
UNAME := $(shell uname)

.PHONY: kat update reset up stop down clean fetch pull upgrade env-if-empty env build debian-build-image ubuntu-build-image docs

# Export Docker buildkit options
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

define build-settings-doc
	echo "# $$(echo "$(3)" | sed 's/.*/\u&/')" > docs/source/technical_design/environment_settings/$(3).md
	DOCS=True PYTHONPATH=./$(1) settings-doc generate \
	-f markdown -m $(2) \
	--templates docs/settings-doc-templates \
	>> docs/source/technical_design/environment_settings/$(3).md
endef


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
	-rm -Rf rocky/node_modules rocky/assets/dist rocky/.parcel-cache rocky/static

# Fetch the latest changes from the Git remote
fetch:
	git fetch --all --prune --tags

# Pull the latest changes from the default upstream
pull:
	git pull
	docker-compose pull

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

# Build Debian 11 build image
debian11-build-image:
	docker build -t kat-debian11-build-image packaging/debian11

# Build Debian 11 build image
debian12-build-image:
	docker build -t kat-debian12-build-image packaging/debian12

# Build Ubuntu 22.04 build image
ubuntu22.04-build-image:
	docker build -t kat-ubuntu22.04-build-image packaging/ubuntu22.04

docs:
	$(call build-settings-doc,keiko,keiko.settings,keiko)
	$(call build-settings-doc,octopoes,octopoes.config.settings,octopoes)
	$(call build-settings-doc,boefjes,boefjes.config,boefjes)
	$(call build-settings-doc,bytes,bytes.config,bytes)
	$(call build-settings-doc,mula/scheduler,config.settings,mula)
	sphinx-build -b html docs/source docs/_build

poetry-dependencies:
	for path in . keiko octopoes boefjes bytes mula rocky; do \
		echo $$path; \
		poetry check --lock -C $$path; \
		poetry export -C $$path --without=dev -f requirements.txt -o $$path/requirements.txt; \
		poetry export -C $$path --with=dev -f requirements.txt -o $$path/requirements-dev.txt; \
	done
