SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules
# Makefile Reference: https://tech.davis-hansson.com/p/make/

.PHONY: help mypy check black done lint env

# use HIDE to run commands invisibly, unless VERBOSE defined
HIDE:=$(if $(VERBOSE),,@)

# Export cmd line args:
export VERBOSE

# Export Docker buildkit options
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

help: ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/ ##/			/' | sed -e 's/##//'

check: ## Check the code style using black, mypy, flake8 and pylint.
	robotidy --diff --check tests/robot
	black --diff --check .
	flake8 keiko
	pylint --recursive=y keiko
	mypy keiko
	vulture --min-confidence=90 keiko

check-latex:
	for file in `find . -name "*.tex"`;  do \
		echo "$$file"
		chktex "$$file" -n 15 -n 17;\
	done

test:
	python -m unittest discover -s tests -p "test_*.py"

itest:
	docker-compose -f docker-compose-base.yml -f .ci/docker-compose.yml up -d --build
	robot -d reports tests/robot
	docker-compose -f docker-compose-base.yml -f .ci/docker-compose.yml down --remove-orphans
