# Scheduler

## Purpose

The scheduler is responsible for scheduling the execution of tasks. The
execution of those tasks are being prioritized / scored by a ranker. The tasks
are then pushed onto a priority queue.

Within the project of KAT, the scheduler is tasked with scheduling boefje and
normalizer tasks.

## Architecture

See
[architecture](https://github.com/minvws/nl-kat-coordination/tree/main/mula/docs/architecture.md)
document for the architecture and the
[extending](https://github.com/minvws/nl-kat-coordination/tree/main/mula/docs/extending.md)
document for the extending the scheduler with your own custom schedulers, and
rankers.

### Stack, packages and libraries

| Name           | Version  | Description                                        |
|----------------|----------|----------------------------------------------------|
| Python         | ^3.8     |                                                    |
| FastAPI        | ^0.93.0  | Used for api server                                |
| SQLAlchemy     | ^1.4.48  |                                                    | 

### External services

The scheduler interfaces with the following services:

| Service     | Usage                                                                    |
|-------------|--------------------------------------------------------------------------|
| [Octopoes]  | Retrieving random OOI's of organizations                                 |
| [Katalogus] | Used for referencing available plugins and organizations                 |
| [Bytes]     | Retrieve last run boefje for organization and OOI                        |
| [Boefjes]   | Sending boefje, and normalizer tasks to Celery                           |
| [RabbitMQ]  | Used for retrieving scan profile changes, and created raw data in bytes  |

### Project structure

```
$ tree -L 3 --dirsfirst
.
├── docs/                           # additional documentation
├── scheduler/                      # scheduler python module
│   ├── config                      # application settings configuration
│   ├── connectors                  # external service connectors
│   │   ├── listeners               # channel/socket listeners
│   │   ├── services                # rest api connectors
│   │   └── __init__.py
│   ├── context/                    # shared application context
│   ├── models/                     # internal model definitions
│   ├── queues/                     # priority queue
│   ├── rankers/                    # priority/score calculations
│   ├── repositories/               # data abstraction layer
│   ├── schedulers/                 # schedulers
│   ├── server/                     # scheduler rest api interface
│   ├── utils/                      # common utility functions
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py                      # kat scheduler app implementation
│   └── version.py                  # version information
└─── tests/
    ├── factories/
    ├── integration/
    ├── simulation/
    ├── unit/
    └── __init__.py
```

## Running / Developing

Typically the scheduler will be run from the overarching
[nl-kat-coordination](https://github.com/minvws/nl-kat-coordination) project.
When you want to run and the scheduler individually you can use the following
setup. We are using docker to setup our development environment, but you are
free to use whatever you want.

### Prerequisites

By the use of environment variables we load in the configuration of the
scheduler. Look at the [.env-dist](.env-dist) file for the application
configuration settings, to build a `.env` file. Refer to the
[`configuration.md`](https://github.com/minvws/nl-kat-coordination/tree/main/mula/docs/configuration.md) file for more information on the
individual settings.

### Running

```
# Build and run the scheduler in the background
$ docker-compose up --build -d scheduler
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
