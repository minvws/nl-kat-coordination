SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules
# Makefile Reference: https://tech.davis-hansson.com/p/make/

.PHONY: help done lint check test utest itest black mypy pylint migrate migrations

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

done: lint check test ## Prepare for a commit.
check: black mypy pylint ## Check the code style using black and mypy.
build: migrate


mypy: ## Check code style using mypy.
	mypy .


black: ## Check code style with black.
	black --check --diff .


pylint: ## Rate the code with pylint.
	pylint bytes | grep rated


lint: ## Format the code using black.
	black --diff .


py-run := docker-compose run bytes python


export revid
export m

migrations: ## Generate a migration using alembic
ifdef m
ifdef revid
	$(py-run) -m alembic revision --autogenerate -m "$(m)" --rev-id="$(revid)"
else
	$(HIDE) (echo "Specify a message with m={message} and a rev-id with revid={revid} (e.g. 0001 etc.)"; exit 1)
endif
else
	$(HIDE) (echo "Specify a message with m={message} and a rev-id with revid={revid} (e.g. 0001 etc.)"; exit 1)
endif


sql: ## Generate raw sql for the migrations
	$(py-run) -m alembic upgrade $(rev1):$(rev2) --sql


migrate: ## Run migrations using alembic
	$(py-run) -m alembic upgrade head


##
##|------------------------------------------------------------------------|
##			Tests
##|------------------------------------------------------------------------|

test: utest itest ## Run all tests.
ci-docker-compose := docker-compose -f base.yml  -f .ci/docker-compose.yml


utest: ## Run the unit tests.
	$(ci-docker-compose) build
	$(ci-docker-compose) down --remove-orphans
	$(ci-docker-compose) run --rm bytes_unit


itest: ## Run the integration tests.
	$(ci-docker-compose) build
	$(ci-docker-compose) down --remove-orphans
	$(ci-docker-compose) run --rm bytes_integration


##
##|------------------------------------------------------------------------|
##			Building
##|------------------------------------------------------------------------|
debian:
	-mkdir ./build
	docker run \
	--env PKG_NAME=kat-bytes \
	--env BUILD_DIR=./build \
	--env REPOSITORY=minvws/nl-kat-bytes \
	--env RELEASE_VERSION=${RELEASE_VERSION} \
	--env RELEASE_TAG=${RELEASE_TAG} \
	--mount type=bind,src=${CURDIR},dst=/app \
	--workdir /app \
	debian:latest \
	packaging/scripts/build-debian-package.sh

clean:
	-rm -rf build/