.PHONY: kat kat_parallel docker_init build init user

UNAME := $(shell uname)

kat:
	make kat_parallel -j 4

kat_parallel: docker_init
	docker compose up -d

docker_init: build
	docker compose run --rm openkat make -j 4 init

build: .env
ifeq ($(UNAME),Darwin)
	docker compose build --pull --build-arg USER_UID="$$(id -u)"
else
	docker compose build --pull --build-arg USER_UID="$$(id -u)" --build-arg USER_GID="$$(id -g)"
endif

init: user

user:
	-python manage.py createsuperuser --no-input

# Create .env file from the env-dist with randomly generated credentials from vars annotated by "{%EXAMPLE_VAR}"
.env:
	cp .env-dist .env
	echo "Initializing .env with random credentials"
ifeq ($(UNAME), Darwin)  # Different sed on MacOS
	$(HIDE) grep -o "{%\([_A-Z]*\)}" .env-dist | sort -u | while read v; do sed -i '' "s/$$v/$$(openssl rand -hex 25)/g" .env; done
else
	$(HIDE) grep -o "{%\([_A-Z]*\)}" .env-dist | sort -u | while read v; do sed -i "s/$$v/$$(openssl rand -hex 25)/g" .env; done
endif
