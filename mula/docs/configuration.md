# Configuration

The scheduler allows some configuration options to be set. Environment
variables are used to configure the scheduler. And these can be set in the
`.env-dist` file. When a value isn't set the default value from the scheduler
will be used. And it's contents are as follows:

```
# Host address, default: 0.0.0.0
SCHEDULER_API_HOST=

# Host api server port, default: 8000
SCHEDULER_API_PORT=

# Boolean value that determines if the scheduler should run in debug mode.
# Default is `False`.
SCHEDULER_DEBUG=

# File path to the log configuration file, default is "../../../logging.json"
SCHEDULER_LOG_CFG=

# Enable the boefje populate_queue, default: False
SCHEDULER_BOEFJE_POPULATE=

# Enable the normalizer populate_queue, default: True
SCHEDULER_NORMALIZER_POPULATE=

# How many items a priority queue can hold, default: 1000
SCHEDULER_PQ_MAXSIZE=

# Interval in seconds of the  execution of the `populate_queue` method of the
# `scheduler.Scheduler` class, default: 60
`populate_queue` method of the  `scheduler.Scheduler` class
SCHEDULER_PQ_INTERVAL=

# Grace period of when a job is considered to be running again (in seconds),
# default: 86400
SCHEDULER_PQ_GRACE=

# The maximum of random objects that are requested from the random ooi
# endpoint from the octopoes api: default: 50
SCHEDULER_PQ_MAX_RANDOM_OBJECTS=

# Interval in seconds of the execution of the `monitor_organisations` method
# of the scheduler application to check newly created or removed organisations
# from katalogus. It updates the organisations, their plugins, and the
# creation of their schedulers.
SCHEDULER_MONITOR_ORGANISATIONS_INTERVAL=

# RabbitMQ host address
SCHEDULER_RABBITMQ_DSN=

# Database host address
SCHEDULER_DB_DSN=

# Host url's of external service connectors
KATALOGUS_API=
BYTES_API=
OCTOPOES_API=

# Bytes specific api credentials
BYTES_USERNAME=
BYTES_PASSWORD=
```

`SCHEDULER_API_HOST` is the host address of the scheduler api server, default
is `0.0.0.0`.

`SCHEDULER_API_PORT` is the port of the scheduler api server, default is
`8000`.

`SCHEDULER_DEBUG` is a boolean value that determines if the scheduler should
run in debug mode. Default is `False`.

`SCHEDULER_BOEFJE_POPULATE` is a boolean to enable or disable the automatic
queue population of the boefje schedulers, default is false

`SCHEDULER_NORMALIZER_POPULATE_ENABLED` is a boolean to enable or disable the
automatic queue population of the normalizer schedulers, default is true

`SCHEDULER_LOG_CFG` is the path to the log configuration file, default is
`../../../logging.json`.

`SCHEDULER_PQ_MAXSIZE` is the maximum size of items the priority queues can
hold, default is `1000`. When set to `0` the queue will be unbounded.

`SCHEDULER_PQ_INTERVAL` is the interval in seconds of the execution of the
`populate_queue` method of the `scheduler.Scheduler` class, default is `60`.

`SCHEDULER_PQ_MAX_RANDOM_OBJECTS` is the maximum of random objects that are
requested from the random ooi endpoint from the octopoes api, default is `50`.

`SCHEDULER_PQ_GRACE` is the grace period in seconds of when a task is considered
to be running again. E.g. a task can be considered to be put onto the queue
again when it just has been dispatched. With this setting we can avoid that
tasks are put onto the queue again when they are not allowed to be dispatched
again. Default is `86400`.

Interval in seconds of the execution of the `monitor_organisations` method
of the scheduler application to check newly created or removed organisations
from katalogus. It updates the organisations, their plugins, and the
creation of their schedulers. Default is `60`.

`SCHEDULER_RABBITMQ_DSN` is the url of the RabbitMQ host.

`SCHEDULER_RABBITMQ_PREFETCH_COUNT` is the RabbitMQ prefetch count for
`channel.basic_qos()`, i.e. the number of unacknowledged messages on a channel.
Also see https://www.rabbitmq.com/consumer-prefetch.html.

`SCHEDULER_DB_DSN` is the locator of the database
