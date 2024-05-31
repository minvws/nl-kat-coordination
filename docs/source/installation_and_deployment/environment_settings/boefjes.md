# Boefjes

## `BOEFJES_LOG_CFG`

_Optional_, default value: `../logging.json`

Path to the logging configuration file

## `BOEFJES_POOL_SIZE`

_Optional_, default value: `2`

Number of workers to run per queue

## `BOEFJES_POLL_INTERVAL`

_Optional_, default value: `10.0`

Time to wait before polling for tasks when all queues are empty

## `BOEFJES_WORKER_HEARTBEAT`

_Optional_, default value: `1.0`

Seconds to wait before checking the workers when queues are full

## `BOEFJES_REMOTE_NS`

_Optional_, default value: `1.1.1.1`

Name server used for remote DNS resolution in the boefje runner

## `BOEFJES_SCAN_PROFILE_WHITELIST`

_Optional_

Whitelist for normalizer ids allowed to produce scan profiles, including a maximum level.

### Examples

`{"kat_external_db_normalize": 3, "kat_dns_normalize": 1}`

## `QUEUE_URI`

**Required**

KAT queue URI

### Examples

`amqp://`

## `KATALOGUS_DB_URI`

**Required**

Katalogus Postgres DB URI

### Examples

`postgresql://xx:xx@host:5432/katalogus`

## `KATALOGUS_DB_CONNECTION_POOL_SIZE`

_Optional_, default value: `16`

Database connection pool size

## `SCHEDULER_API`

**Required**

Mula API URL

### Examples

`http://localhost:8004`

## `KATALOGUS_API`

**Required**

Katalogus API URL

### Examples

`http://localhost:8003`

## `OCTOPOES_API`

**Required**

Octopoes API URL

### Examples

`http://localhost:8001`

## `BOEFJES_API`

**Required**

The URL on which the boefjes API is available

### Examples

`http://boefje:8000`

## `BOEFJES_API_HOST`

_Optional_, default value: `0.0.0.0`

Host address of the Boefje API server

## `BOEFJES_API_PORT`

_Optional_, default value: `8000`

Host port of the Boefje API server

## `BOEFJES_DOCKER_NETWORK`

_Optional_, default value: `bridge`

Docker network to run Boefjes in

## `BYTES_API`

**Required**

Bytes API URL

### Examples

`http://localhost:8002`

## `BYTES_USERNAME`

**Required**

Bytes JWT login username

### Examples

`test`

## `BYTES_PASSWORD`

**Required**

Bytes JWT login password

### Examples

`secret`

## `SPAN_EXPORT_GRPC_ENDPOINT`

_Optional_, default value: `None`

OpenTelemetry endpoint
