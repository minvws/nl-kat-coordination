# Production: Container deployment

OpenKAT can be deployed using containers. We aim to support both simple docker /
docker-compose setups and container orchestration systems like Kubernetes and
Nomad.

There is a docker-compose.release-example.yml in the root directory that can be
used as an example how to deploy using docker-compose.

## Container images

The container images can be found here:

- https://github.com/minvws/nl-kat-boefjes/pkgs/container/nl-kat-boefjes
- https://github.com/minvws/nl-kat-bytes/pkgs/container/nl-kat-bytes
- https://github.com/minvws/nl-kat-mula/pkgs/container/nl-kat-mula
- https://github.com/minvws/nl-kat-octopoes/pkgs/container/nl-kat-octopoes
- https://github.com/minvws/nl-kat-rocky/pkgs/container/nl-kat-rocky
- https://github.com/minvws/nl-kat-keiko/pkgs/container/nl-kat-keiko

## Setup

To set up an installation with pre-built containers, you can pull the repository using:

```shell
git clone https://github.com/minvws/nl-kat-coordination.git
```

If this is your first install, and you do not have an .env file yet, you can create an .env file using the following command:

```shell
make env
```

This will create an .env file with the default values. You can edit this file to change the default values. Now you can pull and start the containers using the following command:

```shell
docker-compose -f docker-compose.release-example.yml up -d
```


The container image run the necessary database migration commands in the
entrypoint if DATABASE_MIGRATION is set. You manually need to run setup commands
in the katalogus and rocky containers to initialize everything. In the katalogus
container we need to create an organisation, we can do this by running the
following in the katalogus container:

```shell
python3 -m boefjes.seed
```

With docker-compose you would run this as:

```shell
docker-compose -f docker-compose.release-example.yml exec katalogus python3 -m boefjes.seed
```

In the rocky container we first need to import the OOI database seed:

```shell
python3 manage.py loaddata OOI_database_seed.json
```

With docker-compose you would run this as:

```shell
docker-compose -f docker-compose.release-example.yml exec rocky python3 manage.py loaddata OOI_database_seed.json
```

Next we need to create the superuser, this will prompt for the e-mail address and password:

```shell
python3 manage.py createsuperuser
```

With docker-compose you would run this as:

```shell
docker-compose -f docker-compose.release-example.yml exec rocky python3 manage.py createsuperuser
```


We also need to create an organisation, this command will create a development organisation:

```shell
python3 manage.py setup_dev_account
```

With docker-compose you would run this as:

```shell
docker-compose -f docker-compose.release-example.yml exec rocky python3 manage.py setup_dev_account
```

## Container commands

We have two container images that are used to run multiple containers. What the container runs is be specified by overriding the CMD of the container.

| Container image | CMD         | Description                                                                       |
|-----------------|-------------|-----------------------------------------------------------------------------------|
| boefjes         | boefje      | Boefjes runtime                                                                   |
| boefjes         | normalizer  | Normalizers runtime                                                               |
| boefjes         | katalogus   | Katalogus API                                                                     |
| octopoes        | web         | Octopoes API                                                                      |
| octopoes        | worker-beat | Celery worker running beat. There must only be exactly one container of this type |
| octopoes        | worker      | Celery worker. Use this if you need to more than one work container for scaling   |

## Env variables

Each container needs to be configured using a set of environment variables

### Boefjes / Katalogus

| Environment variable         | Required | Default Value | Format                               | Description                                                                            |
|------------------------------|----------|---------------|--------------------------------------|----------------------------------------------------------------------------------------|
| `WORKER_CONCURRENCY`         | no       | 10            |                                      | Number of worker processes to start                                                    |
| `QUEUE_NAME_BOEFJES`         | no       | boefjes       |                                      | Queue name for boefjes                                                                 |
| `QUEUE_NAME_NORMALIZERS`     | no       | normalizers   |                                      | Queue name for normalizers                                                             |
| `QUEUE_URI`                  | yes      |               | amqp://user:pass@host:5672/vhost     | RabbitMQ used by celery, should be the same as Mula `SCHEDULER_DSP_BROKER_URL`         |
| `BYTES_API`                  | yes      |               | http://bytes:8000                    | URI for the Bytes API                                                                  |
| `BYTES_USERNAME`             | yes      |               |                                      | Username for Bytes API                                                                 |
| `BYTES_PASSWORD`             | yes      |               |                                      | Password for Bytes API                                                                 |
| `KATALOGUS_API`              | yes      |               | http://katalogus:8000                | URI for the Katalogus API                                                              |
| `OCTOPOES_API`               | yes      |               | http://octopoes_api:8000             | URI for the Octopoes API                                                               |
| `KATALOGUS_DB_URI`           | yes      |               | postgresql://user:paswd@host:5432/db | URI for the Postgresql DB                                                              |
| `WP_SCAN_API`                | no       |               |                                      | A token needed by WP Scan boefje                                                       |
| `ENCRYPTION_MIDDLEWARE`      | no       | IDENTITY      |                                      | Encryption to use for the katalogus settings: IDENTITY (no encryption) or NACL_SEALBOX |
| `KATALOGUS_PRIVATE_KEY_B_64` | no       |               |                                      | KATalogus NaCl Sealbox base-64 private key string                                      |
| `KATALOGUS_PUBLIC_KEY_B_64`  | no       |               |                                      | KATalogus NaCl Sealbox base-64 public key string                                       |
| `WP_SCAN_API`                | no       |               |                                      |                                                                                        |
| `SHODAN_API`                 | no       |               |                                      |                                                                                        |
| `BINARYEDGE_API`             | no       |               |                                      |                                                                                        |
| `LEAKIX_API`                 | no       |               |                                      |                                                                                        |
| `REMOTE_NS`                  | no       | 8.8.8.8       |                                      |                                                                                        |
| `LXD_ENDPOINT`               | no       |               |                                      |                                                                                        |
| `LXD_PASSWORD`               | no       |               |                                      |                                                                                        |
| `DATABASE_MIGRATION`         | no       | false         |                                      | Container entrypoint will run database migrations if set to "true"                     |

See also https://github.com/minvws/nl-kat-boefjes#environment-variables

## Bytes

| Environment variable    | Required | Default Value  | Format                               | Description                                                        |
|-------------------------|----------|----------------|--------------------------------------|--------------------------------------------------------------------|
| `SECRET`                | yes      |                |                                      | Secret used for JWT                                                |
| `BYTES_USERNAME`        | yes      |                |                                      | Username for Bytes API                                             |
| `BYTES_PASSWORD`        | yes      |                |                                      | Password for Bytes API                                             |
| `QUEUE_URI`             | no       |                |                                      | RabbitMQ queue to send events to                                   |
| `BYTES_DB_URI`          | yes      |                | postgresql://user:paswd@host:5432/db | URI for the Postgresql DB                                          |
| `BYTES_DATA_DIR`        | yes      |                |                                      | Directory to store files                                           |
| `ENCRYPTION_MIDDLEWARE` | yes      | `NACL_SEALBOX` |                                      | Encryption to use: IDENTITY (no encryption) or NACL_SEALBOX        |
| `DATABASE_MIGRATION`    | no       | false          |                                      | Container entrypoint will run database migrations if set to "true" |

See also https://github.com/minvws/nl-kat-bytes#configuration

## Octopoes

| Environment variable | Required | Default Value | Format                | Description                  |
|----------------------|----------|---------------|-----------------------|------------------------------|
| `XTDB_URI`           | yes      |               | http://crux:3000      | XTDB uri                     |
| `XTDB_TYPE`          | no       | crux          |                       | crux, xtdb or xtdb-multinode |
| `QUEUE_URI`          | yes      |               |                       | RabbitMQ queue               |
| `KATALOGUS_API`      | yes      |               | http://katalogus:8000 | URI for the Katalogus API    |

See also https://github.com/minvws/nl-kat-octopoes#environment-variables

## Mula

| Environment variable            | Required | Default Value | Format                               | Description                                                        |
|---------------------------------|----------|---------------|--------------------------------------|--------------------------------------------------------------------|
| `SCHEDULER_BOEFJE_POPULATE`     | no       | False         |                                      | Set to True to enable queueing of boefjes                          |
| `SCHEDULER_NORMALIZER_POPULATE` | no       | True          |                                      | Set to True to enable queueing of normalizers                      |
| `SCHEDULER_DSP_BROKER_URL`      | yes      |               | amqp://user:pass@host:5672/vhost     | RabbitMQ instance used by celery                                   |
| `SCHEDULER_RABBITMQ_DSN`        | yes      |               | amqp://user:pass@host:5672/vhost     | RabbitMQ instance used by scheduler, can be the same as celery     |
| `SCHEDULER_DB_DSN`              | yes      |               | postgresql://user:paswd@host:5432/db | URI for scheduler DB                                               |
| `BYTES_API`                     | yes      |               | http://bytes:8000                    | URI for the Bytes API                                              |
| `BYTES_USERNAME`                | yes      |               |                                      | Username for Bytes API                                             |
| `BYTES_PASSWORD`                | yes      |               |                                      | Password for Bytes API                                             |
| `KATALOGUS_API`                 | yes      |               | http://katalogus:8000                | URI for the Katalogus API                                          |
| `OCTOPOES_API`                  | yes      |               | http://octopoes_api:8000             | URI for the Octopoes API                                           |
| `DATABASE_MIGRATION`            | no       | false         |                                      | Container entrypoint will run database migrations if set to "true" |

See also https://github.com/minvws/nl-kat-mula/blob/main/docs/configuration.md

## Rocky

| Environment variable     | Required | Default Value | Format                           | Description                                                                                       |
|--------------------------|----------|---------------|----------------------------------|---------------------------------------------------------------------------------------------------|
| `ROCKY_DB_HOST`          | yes      |               |                                  | Postgres host                                                                                     |
| `ROCKY_DB_PORT`          | yes      |               |                                  | Postgres port                                                                                     |
| `ROCKY_DB`               | yes      |               |                                  | Postgres database database                                                                        |
| `ROCKY_DB_USER`          | yes      |               |                                  | Postgres username                                                                                 |
| `ROCKY_DB_PASSWORD`      | yes      |               |                                  | Postgres password                                                                                 |
| `SECRET_KEY`             | yes      |               | String                           | Key of at least 50 characters, see https://docs.djangoproject.com/en/4.1/ref/settings/#secret-key |
| `QUEUE_NAME_BOEFJES`     | no       | boefjes       |                                  | Queue name for boefjes                                                                            |
| `QUEUE_NAME_NORMALIZERS` | no       | normalizers   |                                  | Queue name for normalizers                                                                        |
| `QUEUE_URI`              | yes      |               | amqp://user:pass@host:5672/vhost | RabbitMQ used by celery, should be the same as Mula `SCHEDULER_DSP_BROKER_URL`                    |
| `BYTES_API`              | yes      |               | http://bytes:8000                | URI for the Bytes API                                                                             |
| `BYTES_USERNAME`         | yes      |               |                                  | Username for Bytes API                                                                            |
| `BYTES_PASSWORD`         | yes      |               |                                  | Password for Bytes API                                                                            |
| `KATALOGUS_API`          | yes      |               | http://katalogus:8000            | URI for the Katalogus API                                                                         |
| `OCTOPOES_API`           | yes      |               | http://octopoes_api:8000         | URI for the Octopoes API                                                                          |
| `SCHEDULER_API`          | yes      |               | http://scheduler:8000            | URI for the scheduler API                                                                         |
| `EMAIL_HOST`             | no       |               |                                  | Hostname of mail server to use to send e-mails                                                    |
| `EMAIL_PORT`             | no       | 25            |                                  | Mail server port                                                                                  |
| `EMAIL_HOST_USER`        | no       |               |                                  | Username to use to connect to mail server                                                         |
| `EMAIL_HOST_PASSWORD`    | no       |               |                                  | Password to use to connect to mail server                                                         |
| `DEFAULT_FROM_EMAIL`     | no       |               |                                  | https://docs.djangoproject.com/en/4.1/ref/settings/#default-from-email                            |
| `SERVER_EMAIL`           | no       |               |                                  | https://docs.djangoproject.com/en/4.1/ref/settings/#server-email                                  |
| `EMAIL_USE_TLS`          | no       |               |                                  | https://docs.djangoproject.com/en/4.1/ref/settings/#email-use-tls                                 |
| `EMAIL_USE_SSL`          | no       |               |                                  | https://docs.djangoproject.com/en/4.1/ref/settings/#email-use-ssl                                 |
| `DATABASE_MIGRATION`     | no       | false         |                                  | Container entrypoint will run database migrations if set to "true"                                |
