.PHONY: build, build-rocky, build-rocky-frontend, run, test, export_migrations


# Export Docker buildkit options
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1


build:
	make build-rocky
	make build-rocky-frontend

build-rocky:
	python3 manage.py migrate
	python3 manage.py createsuperuser
	python3 manage.py loaddata OOI_database_seed.json
	python3 manage.py setup_dev_account
	python3 manage.py compilemessages

build-rocky-frontend:
	yarn --ignore-engines
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
	python manage.py export_migrations accounts 0001

languages:
	python manage.py makemessages --locale nl
	python manage.py makemessages --locale pap

lang:
	make languages

install-rf:
	pip3 install -r requirements-dev.txt
	rfbrowser init

test-prepare:
	python3 manage.py flush --no-input
	python3 manage.py makemigrations
	python3 manage.py migrate
	DJANGO_SUPERUSER_PASSWORD=robotpassword python3 manage.py createsuperuser --email robot@localhost --noinput
	python3 manage.py loaddata OOI_database_seed.json
	python3 manage.py setup_dev_account

test-finish:
	python3 manage.py flush --no-input
	python3 manage.py makemigrations
	python3 manage.py migrate
	python3 manage.py createsuperuser
	python3 manage.py loaddata OOI_database_seed.json
	python3 manage.py setup_dev_account

reset-database:
	docker exec -it nl-kat_rocky_1 make test-finish

test-rf:
	# Test fresh login while fully skipping onboarding
	docker exec -it nl-kat_rocky_1 make test-prepare
	robot -d tests/robot/results-skip_onboarding_no_report -v headless:false tests/robot/skip_onboarding_no_report

	# Test fresh login while generating a report but not creating more user accounts
	docker exec -it nl-kat_rocky_1 make test-prepare
	robot -d tests/robot/results-skip_onboarding_with_report -v headless:false tests/robot/skip_onboarding_with_report

	# Test fresh login while creating all users and running report generation as the redteamer
	docker exec -it nl-kat_rocky_1 make test-prepare
	robot -d tests/robot/results-complete_onboarding -v headless:false tests/robot/complete_onboarding

	# You can run `make reset-database` manually after running tests to reset the database and create a new superuser account
