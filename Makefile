debian:
	-mkdir ./build
	docker run \
	--env PKG_NAME=kat-octopoes \
	--env BUILD_DIR=./build \
	--env REPOSITORY=minvws/nl-kat-octopoes \
	--env RELEASE_VERSION=${RELEASE_VERSION} \
	--env RELEASE_TAG=${RELEASE_TAG} \
	--mount type=bind,src=${CURDIR},dst=/app \
	--workdir /app \
	debian:latest \
	packaging/scripts/build-debian-package.sh

format:
	black .
	robotidy tests/robot

clean:
	-rm -rf build/

check: ## Check the code style using black, mypy, flake8 and pylint.
	black --diff --check .
	flake8 octopoes bits
	pylint --recursive=y octopoes bits
	mypy octopoes bits
	vulture octopoes bits

test:
	python -m unittest discover -s tests -p "test_*.py"

itest:
	docker-compose -f docker-compose-base.yml -f .ci/docker-compose.yml up -d --build
	sleep 1
	robot -d reports --variable OCTOPOES_URI:http://localhost:29000/_dev tests/robot
	docker-compose -f docker-compose-base.yml -f .ci/docker-compose.yml down --remove-orphans

itest-crux:
	docker-compose -f docker-compose-base.yml -f .ci/docker-compose-crux.yml up -d --build
	sleep 1
	robot -d reports --variable OCTOPOES_URI:http://localhost:28000/_dev tests/robot
	docker-compose -f docker-compose-base.yml -f .ci/docker-compose-crux.yml down --remove-orphans

export-requirements: ## Export the requirements to requirements.txt
	poetry export --output requirements.txt --without-hashes && \
	poetry export --output requirements-dev.txt --with dev --without-hashes && \
	poetry export --output requirements-check.txt --only dev --without-hashes
