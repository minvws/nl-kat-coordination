.PHONY: build, build-rocky, build-rocky-frontend, run, test, export_migrations


# Export Docker buildkit options
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1


build:
	make build-rocky-frontend
	make build-rocky

build-rocky:
	python3 manage.py migrate
	-python3 manage.py setup --username admin --password admin
	python3 manage.py loaddata OOI_database_seed.json
	-python3 manage.py setup_dev_organization --username admin
	python3 manage.py compilemessages

build-rocky-frontend:
	yarn
	yarn build

run:
	python3 manage.py runserver

test:
	yarn --cwd roeltje
	yarn --cwd roeltje cypress run
	python3 manage.py test

itest: ## Run the integration tests.
	docker-compose -f base.yml  -f .ci/docker-compose.yml down
ifneq ($(build),)
	docker-compose -f base.yml -f .ci/docker-compose.yml build
endif
	docker-compose -f base.yml  -f .ci/docker-compose.yml run --rm rocky_integration

export_migrations:
	python manage.py export_migrations contenttypes 0001
	python manage.py export_migrations auth 0001
	python manage.py export_migrations admin 0001
	python manage.py export_migrations sessions 0001
	python manage.py export_migrations two_factor 0001
	python manage.py export_migrations otp_static 0001
	python manage.py export_migrations otp_totp 0001
	python manage.py export_migrations tools 0001
	python manage.py export_migrations fmea 0001
