SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules
# Makefile Reference: https://tech.davis-hansson.com/p/make/

.PHONY: help done lint test utest itest black mypy pylint migrate migrations debian ubuntu clean

# use HIDE to run commands invisibly, unless VERBOSE defined
export VERBOSE
HIDE:=$(if $(VERBOSE),,@)

# Export Docker buildkit options
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1


##
##|------------------------------------------------------------------------|
##			Help
##|------------------------------------------------------------------------|
help: ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/:\(.*\)##/:			/' | sed -e 's/##//'

##
##|------------------------------------------------------------------------|
##			Development
##|------------------------------------------------------------------------|

done: lint test ## Prepare for a commit.
build:


lint: ## Format the code using black.
	pre-commit run --all-files --show-diff-on-failure --color always

py-run := docker-compose run bytes python


export revid
export m

migrations: ## Generate a migration using alembic
ifdef m
	$(py-run) -m alembic --config /app/bytes/bytes/alembic.ini revision --autogenerate -m "$(m)"
else
	$(HIDE) (echo "Specify a message with m={message}"; exit 1)
endif


sql: ## Generate raw sql for the migrations
	$(py-run) -m alembic --config /app/bytes/bytes/alembic.ini upgrade $(rev1):$(rev2) --sql

migrate: ## Run alembic migrations
	$(py-run) -m alembic --config /app/bytes/bytes/alembic.ini upgrade head

##
##|------------------------------------------------------------------------|
##			Tests
##|------------------------------------------------------------------------|

test: utest itest ## Run all tests.
ci-docker-compose := docker-compose -f base.yml  -f .ci/docker-compose.yml


utest: ## Run the unit tests.
	$(ci-docker-compose) build $(build_args)
	$(ci-docker-compose) down --remove-orphans
	$(ci-docker-compose) run --rm bytes_unit


itest: ## Run the integration tests.
	$(ci-docker-compose) build $(build_args)
	$(ci-docker-compose) down --remove-orphans
	$(ci-docker-compose) run --rm bytes_integration


##
##|------------------------------------------------------------------------|
##			Building
##|------------------------------------------------------------------------|
debian:
	mkdir -p build
	docker run --rm \
	--env PKG_NAME=kat-bytes \
	--env BUILD_DIR=./build \
	--env REPOSITORY=minvws/nl-kat-bytes \
	--env RELEASE_VERSION=${RELEASE_VERSION} \
	--env RELEASE_TAG=${RELEASE_TAG} \
	--mount type=bind,src=${CURDIR},dst=/app \
	--workdir /app \
	kat-debian-build-image \
	packaging/scripts/build-debian-package.sh

ubuntu:
	mkdir -p build
	docker run --rm \
	--env PKG_NAME=kat-bytes \
	--env BUILD_DIR=./build \
	--env REPOSITORY=minvws/nl-kat-bytes \
	--env RELEASE_VERSION=${RELEASE_VERSION} \
	--env RELEASE_TAG=${RELEASE_TAG} \
	--mount type=bind,src=${CURDIR},dst=/app \
	--workdir /app \
	kat-ubuntu-build-image \
	packaging/scripts/build-debian-package.sh

clean:
	rm -rf build
	rm -rf debian/kat-*/ debian/.debhelper debian/files *.egg-info/ dist/
	rm -f debian/debhelper-build-stamp
	rm -f debian/*.*.debhelper
	rm -f debian/*.substvars
	rm -f debian/*.debhelper.log
	rm -f debian/changelog
