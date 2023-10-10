# Configuration

The scheduler allows some configuration options to be set. Environment
variables are used to configure the scheduler. And these can be set in the
`.env-dist` file. When a value isn't set the default value from the scheduler
will be used. And it's contents are as follows:

```
#####################################
### SCHEDULER APPLICATION SETTINGS ##
#####################################

# File path to the log configuration file,
# Default is: "../../../logging.json"
SCHEDULER_LOG_CFG=

# Host address of the scheduler api server
# Default: localhost
SCHEDULER_API_HOST=

# Host api server port, default: 8000
# Default: 8000
SCHEDULER_API_PORT=

# Boolean value that determines if the scheduler should run in debug mode.
# Default: False
SCHEDULER_DEBUG=

# Boolean that enables/disables the collection of metrics to be used with tools
# like Prometheus
# Default: False
SCHEDULER_COLLECT_METRICS=

# Database connection string
SCHEDULER_DB_DSN=

###############################
### PRIORITY QUEUE SETTINGS ###
###############################

# How many items a priority queue can holdA.
# Default: 1000
SCHEDULER_PQ_MAXSIZE=

# Grace period of when a job is considered to be running again (in seconds).
# Default: 86400
SCHEDULER_PQ_GRACE=

# The maximum number of random objects that can be added to the priority queue,
# per call.
# Default: 50
SCHEDULER_PQ_MAX_RANDOM_OBJECT=

#######################################
## EXTERNAL SERVICES HOSTS ADDRESSES ##
#######################################

KATALOGUS_API=
BYTES_API=
OCTOPOES_API=
SCHEDULER_RABBITMQ_DSN=
SPAN_EXPORT_GRPC_ENDPOINT=

################################
## EXTERNAL SERVICES SETTINGS ##
################################

# Bytes specific api credentials
BYTES_USERNAME=
BYTES_PASSWORD=

# The lifetime of the katalogus cache in seconds.
# Default: 30
SCHEDULER_KATALOGUS_CACHE_TTL=

# Interval in seconds of the execution of the `monitor_organisations` method
# of the scheduler application to check newly created or removed organisations
# from katalogus. It updates the organisations, their plugins, and the
# creation of their schedulers.
SCHEDULER_MONITOR_ORGANISATIONS_INTERVAL=

# The timeout in seconds for the requests to the octopoes api.
# Default: 10
SCHEDULER_OCTOPOES_REQUEST_TIMEOUT=


# RabbitMQ prefetch_count for channel.basic_qos(), which is the number of unacknowledged messages on a channel.
# Also see https://www.rabbitmq.com/consumer-prefetch.html.
SCHEDULER_RABBITMQ_PREFETCH_COUNT=
```
