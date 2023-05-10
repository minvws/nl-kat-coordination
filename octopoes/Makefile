.PHONY: debian ubuntu clean

debian:
	mkdir -p build
	docker run --rm \
	--env PKG_NAME=kat-octopoes \
	--env BUILD_DIR=./build \
	--env REPOSITORY=minvws/nl-kat-octopoes \
	--env RELEASE_VERSION=${RELEASE_VERSION} \
	--env RELEASE_TAG=${RELEASE_TAG} \
	--mount type=bind,src=${CURDIR},dst=/app \
	--workdir /app \
	kat-debian-build-image \
	packaging/scripts/build-debian-package.sh

ubuntu:
	mkdir -p build
	docker run --rm \
	--env PKG_NAME=kat-octopoes \
	--env BUILD_DIR=./build \
	--env REPOSITORY=minvws/nl-kat-octopoes \
	--env RELEASE_VERSION=${RELEASE_VERSION} \
	--env RELEASE_TAG=${RELEASE_TAG} \
	--mount type=bind,src=${CURDIR},dst=/app \
	--workdir /app \
	kat-ubuntu-build-image \
	packaging/scripts/build-debian-package.sh

format:
	black .
	robotidy tests/robot

clean:
	rm -rf build
	rm -fr debian/kat-*/ debian/.debhelper debian/files *.egg-info/ dist/
	rm -f debian/debhelper-build-stamp
	rm -f debian/*.*.debhelper
	rm -f debian/*.substvars
	rm -f debian/*.debhelper.log
	rm -f debian/changelog

check:
	pre-commit run --all-files --show-diff-on-failure --color always

test:
	pytest

rtest:
	docker-compose -f docker-compose-base.yml -f .ci/docker-compose.yml up -d --build
	sleep 1
	robot -d reports --variablefile tests/robot/variables.py:xtdb tests/robot
	docker-compose -f docker-compose-base.yml -f .ci/docker-compose.yml down --remove-orphans

itest:
	docker-compose -f docker-compose-base.yml -f .ci/docker-compose.yml build $(build_args)
	docker-compose -f docker-compose-base.yml -f .ci/docker-compose.yml down
	docker-compose -f docker-compose-base.yml -f .ci/docker-compose.yml  run --rm octopoes_integration

rtest-crux:
	docker-compose -f docker-compose-base.yml -f .ci/docker-compose-crux.yml up -d --build
	sleep 1
	robot -d reports --variablefile tests/robot/variables.py:crux tests/robot || :
	docker-compose -f docker-compose-base.yml -f .ci/docker-compose-crux.yml down --remove-orphans

export-requirements: ## Export the requirements to requirements.txt
	poetry export --output requirements.txt --without-hashes && \
	poetry export --output requirements-dev.txt --with dev --without-hashes
