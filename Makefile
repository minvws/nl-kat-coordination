.PHONY: build build-openkat build-openkat-frontend run test export_migrations debian clean

UNAME := $(shell uname)

# Export Docker buildkit options
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Do not turn on OpenTelemetry when building OpenKAT
unexport SPAN_EXPORT_GRPC_ENDPOINT

kat:
	make kat_parallel -j 4

kat_parallel: frontend docker_init images
	docker compose up -d

clean: .env
	docker compose down --timeout 0 --volumes --remove-orphans
	-rm -Rf node_modules assets/dist .parcel-cache static media *.egg-info

build: .env
ifeq ($(UNAME),Darwin)
	docker compose build --pull --build-arg USER_UID="$$(id -u)"
else
	docker compose build --pull --build-arg USER_UID="$$(id -u)" --build-arg USER_GID="$$(id -g)"
endif

reset:
	make clean
	make kat

dashboards:
	docker compose run --rm openkat python3 manage.py dashboards

docker_init: build
	docker compose run --rm openkat make -j 4 init

init: user seed messages sync nsync

user:
	-python manage.py createsuperuser --no-input

seed:
	python manage.py setup_dev_account

messages:
	python manage.py compilemessages

sync:
	-python manage.py sync

nsync:
	-python manage.py nsync

frontend:
	docker run --rm -v $$PWD:/app/openkat node:20-bookworm sh -c "cd /app/openkat && yarn --ignore-engine && yarn build && chown -R $$(id -u) .parcel-cache node_modules assets/dist"

base-image:
	docker build -f katalogus/images/base.Dockerfile -t openkat/boefje-base:latest .

export REGISTRY=ghcr.io/minvws/openkat

images: dns-sec nmap export-http nikto generic

dns-sec: base-image
	docker build -f katalogus/boefjes/kat_dnssec/boefje.Dockerfile -t $(REGISTRY)/dns-sec:latest -t openkat/dns-sec .

nmap: base-image
	docker build -f katalogus/boefjes/kat_nmap_tcp/boefje.Dockerfile -t $(REGISTRY)/nmap:latest -t openkat/nmap .

export-http: base-image
	docker build -f katalogus/boefjes/kat_export_http/boefje.Dockerfile -t $(REGISTRY)/export-http:latest -t openkat/export-http .

nikto: base-image
	docker build -f katalogus/boefjes/kat_nikto/boefje.Dockerfile -t $(REGISTRY)/nikto:latest .

generic: base-image
	docker build -f katalogus/images/generic.Dockerfile -t $(REGISTRY)/generic:latest -t openkat/generic .

testclean:
	docker compose -f .ci/docker-compose.yml kill
	docker compose -f .ci/docker-compose.yml down --remove-orphans
	docker compose -f .ci/docker-compose.yml build

utest: testclean ## Run the unit tests.
	docker compose -f .ci/docker-compose.yml run --rm openkat_tests

itest: testclean ## Run the integration tests.
	docker compose -f .ci/docker-compose.yml run --rm openkat_integration

bench: testclean ## Run the report benchmark.
	docker compose -f .ci/docker-compose.yml run --rm openkat_integration \
	python -m cProfile -o .ci/bench_$$(date +%Y_%m_%d-%H:%M:%S).pstat -m pytest -m slow --no-cov tests/integration

languages:
# Extracts strings to `.pot` file which should be translated
# Note that the creation of `.po` files is delegated to another tool (Weblate)
	python manage.py makemessages -i "venv/*" -i "build/*" -i "octopoes/*" -i "node_modules/*" --verbosity 2 --add-location file -a --keep-pot

lang: languages

check:
	pre-commit run --all-files --show-diff-on-failure --color always

# Create .env file from the env-dist with randomly generated credentials from vars annotated by "{%EXAMPLE_VAR}"
.env:
	cp .env-dist .env
	echo "Initializing .env with random credentials"
ifeq ($(UNAME), Darwin)  # Different sed on MacOS
	$(HIDE) grep -o "{%\([_A-Z]*\)}" .env-dist | sort -u | while read v; do sed -i '' "s/$$v/$$(openssl rand -hex 25)/g" .env; done
else
	$(HIDE) grep -o "{%\([_A-Z]*\)}" .env-dist | sort -u | while read v; do sed -i "s/$$v/$$(openssl rand -hex 25)/g" .env; done
endif
