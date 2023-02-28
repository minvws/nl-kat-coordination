# Bytes

Bytes is a service that provides an API for reading and writing metadata of jobs and job outputs (raw files).
It can also encrypt the raw data, and hash it to proof that the data was seen before a point in time (see below).

## Installation

There are two ways to setup the API.


### With Docker
Bytes can be fired up from the root directory of KAT using docker-compose (check out the README over there!).

To run Bytes as a standalone container, spin up a Postgresql database (e.g. using Docker),
create the database `bytes` and run
```shell
$ docker build . -t bytes

# Without an env-file
$ export BYTES_PASSWORD=$(openssl rand -hex 20) \
    && export SECRET=$(openssl rand -hex 20) \
    && export BYTES_DB_URI=postgresql://USER:PWD@bytes-db:5432/bytes  # change accordingly!
$ docker run --rm -p 8002:8002 -e BYTES_USERNAME=bytes -e BYTES_PASSWORD -e SECRET -e BYTES_DB_URI bytes


# With an env-file
$ docker run --rm -p 8002:8000 --env-file=/path/to/env bytes  # change accordingly!
```


### Without Docker

To create and start a python virtual environment, run
```shell
$ python -m venv $PWD/.venv
$ source .venv/bin/activate
```

To install the dependencies, assuming you are in the virtual environment, run
```shell
$ pip install -r requirements-dev.txt
```
Bytes depends on a Postgresql database that is configurable by the BYTES_DB_URI environment variable.
See above for a minimal set of environment variables to start Bytes and

To start the API run
```shell
$ uvicorn bytes.api:app --host 127.0.0.1 --port 8002 --reload --reload-dir /app/bytes/bytes
```
See http://localhost:8002/docs for the OpenAPI documentation.

## Configuration
You can configure several settings with your environment, see the env-dist:

```shell
$ cat .env-dist
# Bytes API, which uses JWT
SECRET=
BYTES_USERNAME=
BYTES_PASSWORD=
ACCESS_TOKEN_EXPIRE_MINUTES=1000

# Bytes DB
BYTES_DB_URI=

# Hashing/Encryption
HASHING_ALGORITHM="SHA512"
EXT_HASH_SERVICE="IN_MEMORY"
PASTEBIN_API_DEV_KEY=""
KAT_PRIVATE_KEY_B64=""
VWS_PUBLIC_KEY_B64=""

# Timestamping. See https://github.com/trbs/rfc3161ng for a list of public providers and their certificates
RFC3161_PROVIDER=
RFC3161_CERT_FILE=

# File system
BYTES_FOLDER_PERMISSION=740  # Unix permission level on the folders Bytes creates to save raw files
BYTES_FILE_PERMISSION=640  # Unix permission level on the raw files themselves
ENCRYPTION_MIDDLEWARE=IDENTITY

# QUEUE for messages other services in KAT listen to
QUEUE_URI=

# Optional environment variables
BYTES_LOG_FILE=  # Optional file with Bytes logs.
BYTES_DATA_DIR=  # Root for all the data. A change means that you no longer have access to old data unless you move it!
```

Most of these are self-explanatory, but a few sets of variables require more explanation.


### Hashing and Encryption

Every raw file is hashed with the current `ended_at` of the `boefje_meta`,
which functions as a 'proof' of it being uploaded at that time.
These proofs can be uploaded externally (a 3rd party) such that we can verify that this data was saved in the past.

Current implementations are
- `EXT_HASH_SERVICE="IN_MEMORY"` (just a stub)
- `EXT_HASH_SERVICE="PASTEBIN"` (Needs pastebin API development key)
- `EXT_HASH_SERVICE="RFC3161"`

For the RFC3161 implementation, see https://www.ietf.org/rfc/rfc3161.txt and https://github.com/trbs/rfc3161ng as a reference.
To use this implementation, set your environment to
- `EXT_HASH_SERVICE=RFC3161`
- `RFC3161_PROVIDER="https://freetsa.org/tsr"` (example)
- `RFC3161_CERT_FILE="bytes/timestamping/certificates/freetsa.crt"` (example)

Adding a new implementation means implementing the `bytes.repositories.hash_repository::HashRepository` interface.
Bind your new implementation in `bytes.timestamping.provider::create_hash_repository`.

The secure-hashing-algorithm can be specified with an env var: `HASHING_ALGORITHM="SHA512"`.
```bash
HASHING_ALGORITHM="SHA512"
EXT_HASH_SERVICE="IN_MEMORY"
PASTEBIN_API_DEV_KEY=""
```

Files in bytes can be saved encrypted to disk,
the implementation can be set using an env-var, `ENCRYPTION_MIDDLEWARE`. The options are:
- `"IDENTITY"`
- `"NACL_SEALBOX"`


The `"NACL_SEALBOX"` option requires the `KAT_PRIVATE_KEY_B64` and `VWS_PUBLIC_KEY_B64` env vars.
```bash
ENCRYPTION_MIDDLEWARE="IDENTITY"
KAT_PRIVATE_KEY_B64=""
VWS_PUBLIC_KEY_B64=""
```

## Design

The overall view of the application is as follows.

```mermaid
graph LR
    U[User] -- BoefjeMeta --> A1[API] -- save BoefjeMeta --> B1[Meta Repository]
    B1[Meta Repository] -- BoefjeMeta --> RDB
    B[Meta Repository] -- hash RawFile --> HR[Hasher] -- Hash --> B[Meta Repository]
    U[User] -- RawFile --> A2[API] -- save RawFile --> B[Meta Repository] -- save Hash --> H[Hash Repository]
    H[Hash Repository] -- Hash --> T[Third Party]
    B[Meta Repository] -- save RawFile --> R[Raw Repository] -- RawFile --> E[EnriptionMiddleware]
    E[EnriptionMiddleware] -- Encrypted Data --> Disk -- Encrypted Data  --> E[EnriptionMiddleware]
```

This flow does not show saving the `NormalizerMeta` object in the `MetaRepository`.
A message is sent through RabbitMQ once a `RawFile` has been saved.


## Development


The `Makefile` provides useful targets to use during development. To see the options run
```shell
$ make help
```

### Code style and tests
All the code style and linting checks are done by running
```shell
$ make check
```

The unit and integration tests targets are `utest` and `itest` respectively.
To run all test, run
```shell
$ make test
```
To make sure all github actions (checks and tests) pass, run
```shell
$ make done
```
Ideally, you run this before each commit.
Passing all the checks and tests in this target should ensure the github actions pass.

### Migrations

To make a new migration file and run the migration, run
```shell
$ make migrations m='Some migration message'
$ make migrate
```


### Export SQL migrations

To export raw SQL from the SQLAlchemy migration files, run the following target
(for the diff between 0003 and 0004):
```shell
$ make sql rev1=0003 rev2=0004 > sql_migrations/0004_change_x_to_y_add_column_z.sql
```
