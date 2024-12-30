# Scheduler

## Purpose

The scheduler is responsible for scheduling the execution of tasks. The
execution of those tasks are being prioritized / scored by a ranker. The tasks
are then pushed onto a priority queue.

Within the project of KAT, the scheduler is tasked with scheduling boefje,
normalizer, and report tasks.

## Architecture

See
[architecture](https://github.com/minvws/nl-kat-coordination/tree/main/mula/docs/architecture.md)
document for the architecture and the
[extending](https://github.com/minvws/nl-kat-coordination/tree/main/mula/docs/extending.md)
document for the extending the scheduler with your own custom schedulers, and
rankers.

### Stack, packages and libraries

| Name       | Version   | Description         |
| ---------- | --------- | ------------------- |
| Python     | ^3.10     |                     |
| FastAPI    | ^0.1115.2 | Used for api server |
| SQLAlchemy | ^2.0.23   |                     |
| pydantic   | ^2.7.2    |                     |

### External services

The scheduler interfaces with the following services:

| Service     | Usage                                                                   |
| ----------- | ----------------------------------------------------------------------- |
| [Octopoes]  | Retrieving random OOI's of organizations                                |
| [Katalogus] | Used for referencing available plugins and organizations                |
| [Bytes]     | Retrieve last run boefje for organization and OOI                       |
| [RabbitMQ]  | Used for retrieving scan profile changes, and created raw data in bytes |

### Project structure

```
.
├── docs/                           # additional documentation
├── scheduler/                      # scheduler python module
│   ├── clients/                    # external service clients
│   │   ├── amqp/                   # rabbitmq clients
│   │   └── http/                   # http clients
│   ├── context/                    # shared application context, and configuration
│   ├── models/                     # internal model definitions
│   ├── schedulers/                 # schedulers
│   │   ├── queue/                  # priority queue
│   │   ├── rankers/                # priority/score calculations
│   │   └── schedulers/             # schedulers implementations
│   ├── server/                     # http rest api server
│   ├── storage/                    # data abstraction layer
│   │   ├── migrations/             # database migrations
│   │   └── stores/                 # data stores
│   ├── utils/                      # common utility functions
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py                      # OpenKAT scheduler app implementation
│   └── version.py                  # version information
└─── tests/                         # test suite
    ├── factories/                  # factories for test data
    ├── integration/                # integration tests
    ├── mocks/                      # mocks for testing
    ├── simulation/                 # simulation tests
    ├── unit/                       # unit tests
    └── utils/                      # utility functions for tests
```

## Running / Developing

Typically the scheduler will be run from the overarching
[nl-kat-coordination](https://github.com/minvws/nl-kat-coordination) project.
When you want to run and the scheduler individually you can use the following
setup. We are using docker to setup our development environment, but you are
free to use whatever you want.

### Prerequisites

By the use of environment variables we load in the configuration of the
scheduler. See the environment settings section under Installation and Deployment for more information.

### Running

```
# Build and run the scheduler in the background
$ docker compose up --build -d scheduler
```

### Migrations

Creating a migration:

```
# Run migrations
make revid=0008 m="add_task_schedule" migrations
```

Sometimes it is helpful to run the migrations in a clean environment:

```
docker system prune
docker volume prune --force --all
```

## Testing

```
# Run integration tests
$ make itest

# Run unit tests
$ make utest

# Individually test a file
$ make file=test_file.py utest

# Individually test a function
$ make file=test_file.py function='test_function' utest
```
