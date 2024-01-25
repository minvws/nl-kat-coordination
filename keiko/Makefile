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

# Export cmd line args:
export VERBOSE

# Export Docker buildkit options
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

help: ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/ ##/			/' | sed -e 's/##//'

check:
	pre-commit run --all-files --show-diff-on-failure --color always

check-latex:
	for file in `find . -name "*.tex"`;  do \
		echo "$$file"
		chktex "$$file" -n 15 -n 17;\
	done

test:
	pytest

itest:
	docker compose -f docker-compose-base.yml -f .ci/docker-compose.yml up -d --build && sleep 1
	robot -d reports tests/robot
	docker compose -f docker-compose-base.yml -f .ci/docker-compose.yml down --remove-orphans

debian12:
	mkdir -p build
	docker run --rm \
	--env PKG_NAME=kat-keiko \
	--env BUILD_DIR=./build \
	--env REPOSITORY=minvws/nl-kat-keiko \
	--env RELEASE_VERSION=${RELEASE_VERSION} \
	--env RELEASE_TAG=${RELEASE_TAG} \
	--mount type=bind,src=${CURDIR},dst=/app \
	--workdir /app \
	kat-debian12-build-image \
	packaging/scripts/build-debian-package.sh

ubuntu22.04:
	mkdir -p build
	docker run --rm \
	--env PKG_NAME=kat-keiko \
	--env BUILD_DIR=./build \
	--env REPOSITORY=minvws/nl-kat-keiko \
	--env RELEASE_VERSION=${RELEASE_VERSION} \
	--env RELEASE_TAG=${RELEASE_TAG} \
	--mount type=bind,src=${CURDIR},dst=/app \
	--workdir /app \
	kat-ubuntu22.04-build-image \
	packaging/scripts/build-debian-package.sh

clean:
	rm -rf build
	rm -rf debian/kat-*/ debian/.debhelper debian/files *.egg-info/ dist/
	rm -f debian/debhelper-build-stamp
	rm -f debian/*.*.debhelper
	rm -f debian/*.substvars
	rm -f debian/*.debhelper.log
	rm -f debian/changelog
