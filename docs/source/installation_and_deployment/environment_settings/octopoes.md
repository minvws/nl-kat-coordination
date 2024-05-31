# Octopoes

## `OCTOPOES_LOG_CFG`

_Optional_, default value: `../../../logging.yml`

Path to the logging configuration file

## `QUEUE_URI`

**Required**

KAT queue URI

### Examples

`amqp://`

## `XTDB_URI`

**Required**

XTDB API

### Examples

`http://xtdb:3000`

## `KATALOGUS_API`

**Required**

Katalogus API URL

### Examples

`http://localhost:8003`

## `OCTOPOES_SCAN_LEVEL_RECALCULATION_INTERVAL`

_Optional_, default value: `60`

Interval in seconds of the periodic task that recalculates scan levels

## `OCTOPOES_BITS_ENABLED`

_Optional_, default value: `set()`

Explicitly enabled bits

### Examples

`["port-common"]`

## `OCTOPOES_BITS_DISABLED`

_Optional_, default value: `set()`

Explicitly disabled bits

### Examples

`["port-classification-ip"]`

## `SPAN_EXPORT_GRPC_ENDPOINT`

_Optional_, default value: `None`

OpenTelemetry endpoint
