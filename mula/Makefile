SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules
# Makefile Reference: https://tech.davis-hansson.com/p/make/

.PHONY: help mypy check black done lint env debian ubuntu clean

# use HIDE to run commands invisibly, unless VERBOSE defined
HIDE:=$(if $(VERBOSE),,@)

BYTES_VERSION= v0.6.0

# Export cmd line args:
export VERBOSE
export m
export build
export file

# Export Docker buildkit options
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

ci-docker-compose := docker-compose -f base.yml  -f .ci/docker-compose.yml

##
##+------------------------------------------------------------------------+
##| Help                                                                   |
##+------------------------------------------------------------------------+
help: ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/ ##/			/' | sed -e 's/##//'

##
##+------------------------------------------------------------------------+
##| Development                                                            |
##+------------------------------------------------------------------------+

check: ## Check the code style using black, mypy and pylint.
	make black
	make mypy
	make pylint

mypy: ## Check code style using mypy.
	$(ci-docker-compose) run --rm mula \
		python -m mypy --cache-dir /home/scheduler/.mypy_cache /app/scheduler/scheduler

black: ## Check code style with black.
	$(ci-docker-compose) run --rm mula \
		black --check --diff .

pylint: ## Rate the code with pylint.
	$(ci-docker-compose) run --rm mula \
		pylint --rcfile pyproject.toml scheduler

fmt: ## Format the code using black.
	$(ci-docker-compose) run --rm mula \
		black .

done: ## Prepare for a commit.
	make lint
	make check
	make test

cov: ## Generate a test coverage report
	$(ci-docker-compose) run --rm mula \
		python -m pytest \
		--cov-report term-missing:skip-covered \
		--cov=scheduler tests/

##
##+------------------------------------------------------------------------+
##| Migrations                                                             |
##+------------------------------------------------------------------------+

sql: ## Generate raw sql for the migrations.
	docker-compose exec scheduler \
		alembic --config /app/scheduler/alembic.ini \
		upgrade $(rev1):$(rev2) --sql

migrations: ## Create migration.
ifeq ($(m),)
	$(HIDE) (echo "ERROR: Specify a message with m={message} and a rev-id with revid={revid} (e.g. 0001 etc.)"; exit 1)
else ifeq ($(revid),)
	$(HIDE) (echo "ERROR: Specify a message with m={message} and a rev-id with revid={revid} (e.g. 0001 etc.)"; exit 1)
else
	docker-compose run scheduler \
		alembic --config /app/scheduler/scheduler/alembic.ini \
		revision --autogenerate \
		-m "$(m)" --rev-id "$(revid)"
endif

migrate: ## Run migrations using alembic.
	docker-compose run scheduler \
		alembic --config /app/scheduler/scheduler/alembic.ini \
		upgrade head

##
##+------------------------------------------------------------------------+
##| Testing                                                                |
##+------------------------------------------------------------------------+

utest: ## Run the unit tests.
ifneq ($(file),)
	$(ci-docker-compose) run --rm mula python -m pytest tests/unit/${file} ${function}
else
	$(ci-docker-compose) run --rm mula python -m pytest tests/unit
endif
	$(ci-docker-compose) down --remove-orphans

itest: ## Run the integration tests.
ifneq ($(file),)
	$(ci-docker-compose) run --rm mula python -m pytest tests/integration/${file} ${function}
else
	$(ci-docker-compose) run --rm mula python -m pytest tests/integration
endif
	$(ci-docker-compose) down --remove-orphans

stest: ## Run the simulation tests.
	$(ci-docker-compose) run --rm mula python -m pytest tests/simulation
	$(ci-docker-compose) down --remove-orphans

test: ## Run all tests.
	make utest
	make itest

##
##+------------------------------------------------------------------------+
##| Building                                                               |
##+------------------------------------------------------------------------+
debian: ## debian
	mkdir -p build
	docker run --rm \
	--env PKG_NAME=kat-mula \
	--env BUILD_DIR=./build \
	--env REPOSITORY=minvws/nl-kat-mula \
	--env RELEASE_VERSION=${RELEASE_VERSION} \
	--env RELEASE_TAG=${RELEASE_TAG} \
	--mount type=bind,src=${CURDIR},dst=/app \
	--workdir /app \
	kat-debian-build-image \
	packaging/scripts/build-debian-package.sh

ubuntu: ## ubuntu
	mkdir -p build
	docker run --rm \
	--env PKG_NAME=kat-mula \
	--env BUILD_DIR=./build \
	--env REPOSITORY=minvws/nl-kat-mula \
	--env RELEASE_VERSION=${RELEASE_VERSION} \
	--env RELEASE_TAG=${RELEASE_TAG} \
	--mount type=bind,src=${CURDIR},dst=/app \
	--workdir /app \
	kat-ubuntu-build-image \
	packaging/scripts/build-debian-package.sh

clean: ## clean
	rm -rf build
	rm -rf debian/kat-*/ debian/.debhelper debian/files *.egg-info/ dist/
	rm -f debian/debhelper-build-stamp
	rm -f debian/*.*.debhelper
	rm -f debian/*.substvars
	rm -f debian/*.debhelper.log
	rm -f debian/changelog
