SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules
# Makefile Reference: https://tech.davis-hansson.com/p/make/

.PHONY: help sql migrate migrations

# use HIDE to run commands invisibly, unless VERBOSE defined
HIDE:=$(if $(VERBOSE),,@)

export m		# Message for alembic migration
export revid	# Revision id to generate raw sql for
export rev1		# Previous revision id for generating migrations
export rev2		# New revision id for the new migration file

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
build: migrate seed

seed:  # Seed the katalogus database
	-docker-compose run katalogus python -m boefjes.seed

##
##|------------------------------------------------------------------------|
##			Migrations
##|------------------------------------------------------------------------|

migrations: ## Generate a migration using alembic
ifeq ($(m),)
	$(HIDE) (echo "Specify a message with m={message} and a rev-id with revid={revid} (e.g. 0001 etc.)"; exit 1)
else ifeq ($(revid),)
	$(HIDE) (echo "Specify a message with m={message} and a rev-id with revid={revid} (e.g. 0001 etc.)"; exit 1)
else
	docker-compose run katalogus python -m alembic revision --autogenerate -m "$(m)" --rev-id="$(revid)"
endif


sql: ## Generate raw sql for the migrations
	docker-compose run katalogus python -m alembic upgrade $(rev1):$(rev2) --sql


migrate: ## Run migrations using alembic
	docker-compose run katalogus python -m alembic upgrade head

##
##|------------------------------------------------------------------------|
##			Tests
##|------------------------------------------------------------------------|

ci-docker-compose := docker-compose -f base.yml  -f .ci/docker-compose.yml


test: itest ## Run all tests.

itest: ## Run the integration tests.
	$(ci-docker-compose) build
	$(ci-docker-compose) down --remove-orphans
	$(ci-docker-compose) run --rm katalogus_integration

debian:
	-mkdir ./build
ifdef OCTOPOES_DIR
	docker run \
	--env PKG_NAME=kat-boefjes \
	--env BUILD_DIR=./build \
	--env REPOSITORY=minvws/nl-kat-boefjes \
	--env RELEASE_VERSION=${RELEASE_VERSION} \
	--env RELEASE_TAG=${RELEASE_TAG} \
	--env OCTOPOES_DIR=/octopoes \
	--mount type=bind,src=${CURDIR},dst=/app \
	--mount type=bind,src=${OCTOPOES_DIR},dst=/octopoes \
	--workdir /app \
	debian:latest \
	packaging/scripts/build-debian-package.sh
else
	docker run \
	--env PKG_NAME=kat-boefjes \
	--env BUILD_DIR=./build \
	--env REPOSITORY=minvws/nl-kat-boefjes \
	--env RELEASE_VERSION=${RELEASE_VERSION} \
	--env RELEASE_TAG=${RELEASE_TAG} \
	--mount type=bind,src=${CURDIR},dst=/app \
	--workdir /app \
	debian:latest \
	packaging/scripts/build-debian-package.sh
endif

clean:
	-rm -rf build