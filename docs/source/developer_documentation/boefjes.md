# Boefjes

This module has several entry points discussed below, but let us first consider the prerequisites and scope.
If you already have running setup and want to learn where each bit of functionality goes, read the following page:

[Developing Openkat Plugins](README.md#your-first-boefje)

## Prerequisites

To run a development environment you need to have:

- A running RabbitMQ service
- A running Bytes API service
- A `./env` containing the environment variables explained below
- Everything in `requirements.txt` installed

Optionally, you could have an instance of the octopoes api listening on a port that receives the normalized data from
the normalizers.

## KATalogus

See the openAPI reference at http://localhost:8003/docs.
The KATalogus has CRUD endpoints for several objects such as:
- `Organisation`
- `Repository`
- `Plugin`
- `Setting`

### Organisations
Supported HTTP methods (for CRUD): `POST`, `GET`, `DELETE`.
Includes an endpoint that lists all objects.
All subsequent objects in the API are namespaced on the `organisation_id`.

### Repositories
Supported HTTP methods (for CRUD): `POST`, `GET`, `DELETE`.
Includes an endpoint that lists all objects.

### Plugins
Supported HTTP methods (for CRUD): `GET`, `PATCH`.
Note: there are endpoints namespaced on the `repository_id` included.


### Settings

Supported HTTP methods (for CRUD): `POST`, `GET`, `DELETE`, `PUT`.
Includes an endpoint that lists all objects.

The KATalogus stores environment settings for the different organisations and plugins, accessible through the API.
These can be encrypted by setting the `BYTES_ENCRYPTION_MIDDLEWARE=NACL_SEALBOX`, and the public and private key env vars.
More info about the encryption scheme can be found here: https://pynacl.readthedocs.io/en/latest/public/.
Currently, the settings are encrypted when stored, and returned decrypted.
This could be changed in the future when the boefje-runner/plugin-code can decrypt the secrets itself,
although this would be more complicated.

## Environment variables
By design, Boefjes do not have access to the host system's environment variables.
If a Boefje requires access to an environment variable (e.g. `HTTP_PROXY` or `USER_AGENT`), it should note as such in its `boefje.json` manifest.
The system-wide variables can be set as environment variable to the boefjes runner by prefixing it with `BOEFJE_`.
This is to prevent a Boefje from accessing variables it should not have access to, such as secrets.
To illustrate: if `BOEFJE_HTTP_PROXY=https://proxy:8080` environment variable is configured, the Boefje can access it as `HTTP_PROXY`.
This feature can also be used to set default values for KAT-alogus settings. For example, configuring the `BOEFJE_TOP_PORTS` environment variable
will set the default value for the `TOP_PORTS` setting (used by the nmap Boefje).
This default value can be overridden by setting any value for `TOP_PORTS` in the KAT-alogus.

## Design

Boefjes will run as containerized workers pulling jobs from a centralized job queue:

![design](img/boefje_design.png)

Connections to other components, represented by the yellow squares, are abstracted by the modules inside them. The red
components live outside the boefjes module. The green core files however is what can be focused on and can be
developed/refactored further to support boefjes of all different kinds.

### Boefje and Normalizer Workers

When we configure a `POOL_SIZE` of `n`, we have `n` + 1 processes: one main process and `n` workers.
The main process pushes to a `multiprocessing.Manager.Queue` and keeps track of the task that was being handled by the workers.
It sets the status to failed when the worker was killed,
like when the process [runs out of memory and is killed by Docker](https://github.com/minvws/nl-kat-coordination/pull/1187).
(Note: `multiprocessing.Queue` will not work due to [`qsize()` not being implemented on macOS](https://github.com/minvws/nl-kat-coordination/pull/1374).)
No maximum size is defined on the queue since we want to avoid blocking.
Hence, we manually check if the queue does not pile up beyond the number of workers, i.e. `n`.

#### Design

The setup for the main process and workers:

```{mermaid}
graph LR

SchedulerRuntimeManager -- "pop()" --> Scheduler

subgraph Process 0

  multiprocessing.Queue
  SchedulerRuntimeManager -- "put(p_item)" --> multiprocessing.Queue["multiprocessing.Manager.Queue()"]

  Worker-1["Worker 1<br/><i>target = _start_working()"] -- "get()" --> multiprocessing.Queue

  subgraph Process 1
    Worker-1
    Worker-1 -- runs --> Plugin1["Plugin"]
  end

  Worker-2["Worker 2<br/><i>target = _start_working()"] -- "get()" --> multiprocessing.Queue

  subgraph Process 2
      Worker-2
      Worker-2 -- runs --> Plugin2["Plugin"]
  end
end
```

#### Worker failure mode
Rough representation of the failure mode when a SIGKILL has been sent to the worker:

```{mermaid}
sequenceDiagram
  participant SchedulerRuntimeManager
  participant handling_tasks
  participant Worker1
  participant Scheduler
  participant Worker2
  Worker1->>handling_tasks: set p_item.id for worker1.pid
  SchedulerRuntimeManager->>Worker1: if not is_alive()
  SchedulerRuntimeManager->>handling_tasks: get p_item.id for worker1.pid
  SchedulerRuntimeManager->>Scheduler: set p_item.status to FAILED
  SchedulerRuntimeManager->>Worker1: close()
  SchedulerRuntimeManager->>Worker2: start()
```



### Running as a Docker container

To run a boefje and normalizer worker as a docker container, you can run

```bash
docker build . -t boefje
docker run --rm -d --name boefje boefje python -m boefjes boefje
docker run --rm -d --name normalizer boefje python -m boefjes normalizer
```

Note: the worker needs a running Bytes API and RabbitMQ. The service locations can be specified with environment variables
(see the Docker documentation to use a `.env` file with the `--env-file` flag, for instance).

### Running the worker directly

To start the worker process listening on the job queue, use the `python -m boefjes` module.
```bash
$ python -m boefjes --help
Usage: python -m boefjes [OPTIONS] {boefje|normalizer}

Options:
  --log-level [DEBUG|INFO|WARNING|ERROR]
                                  Log level
  --help                          Show this message and exit.
```

So to start either a `boefje` worker or `normalizer` worker, run:

- `python -m boefjes boefje`
- `python -m boefjes normalizer`

Again, service locations can be specified with environment variables.

### Example job
The job file for a DNS scan might look like this:

```json
{
  "id": "b445dc20-c030-4bc3-b779-4ed9069a8ca2",
  "organization": "_dev",
  "boefje": {
    "id": "ssl-scan-job",
    "version": null
  },
  "input_ooi": "Hostname|internet|www.example.nl"
}
```

If the tool runs smoothly, the data can be accessed using the Bytes API (see Bytes documentation).

### Manually running a boefje or normalizer

It is possible to manually run a boefje using

```shell
$ ./tools/run_boefje.py ORGANIZATION_CODE BOEFJE_ID INPUT_OOI
```

This will execute the boefje with debug logging turned on. It will log the raw
file id in the output, which can be viewed using `show_raw`:

```shell
$ ./tools/show_raw.py RAW_ID
```

There is also a `--json` option to parse the raw file as JSON and pretty print
it. The normalizer is run using:

```shell
$ ./tools/run_normalizer.py NORMALIZER_ID RAW_ID
```

Both `run_boefje.py` and `run_normalizer.py` support the `--pdb` option to enter
the standard Python Debugger when an exceptions happens or breakpoint is
triggered.

If you are using the standard docker compose developer setup, you can use
`docker compose exec` to execute the commands in the container. The boefje and
normalizer containers use the same images and settings, so you can use both:

```shell
$ docker compose exec boefje ./tools/run_boefje.py ORGANIZATION_CODE BOEFJE_ID INPUT_OOI
```

For example:

```shell
$ docker compose exec boefje ./tools/run_boefje.py myorganization dns-records "Hostname|internet|example.com"
$ docker compose exec boefje ./tools/show_raw.py --json 794986d7-cf39-4a2c-8bdf-17ae58f361ea
$ docker compose exec boefje ./tools/run_normalizer.py kat_dns_normalize 794986d7-cf39-4a2c-8bdf-17ae58f361ea
```


### Boefje and normalizer structure

Each boefje and normalizer module is placed in `boefjes/<module>`. A module's main script is usually called `main.py`,
and a normalizer is usually called `normalize.py`, but it also may contain one or more normalizers.
A definition file with metadata about the boefje is called `boefje.py`.
Here a `Boefje` object that wraps this metadata is defined, as well as `Normalizer` objects that can parse this Boefje's output.
Each module may also have its own `requirements.txt` file that lists dependencies not included in the base requirements.
Furthermore, you can add static data such as a cover and a description (markdown) to show up in Rocky's KATalogus.

Example structure:

```shell
$ tree boefjes/kat_dns
├── boefje.py
├── cover.jpg
├── description.md
├── __init__.py
├── main.py
├── normalize.py
└── requirements.txt
```

### Running the test suite

To run the test suite, run:

```shell
$ python -m pytest
```

To lint the code using black, run:
```shell
$ python -m black .
```
