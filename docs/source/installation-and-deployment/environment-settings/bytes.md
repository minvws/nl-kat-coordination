# Bytes

## `BYTES_SECRET`

**Required**

Secret key used for generating Bytes' API JWT

### Examples

`bec4837fe5108205ce6cd1bc11735d4a220e253345e90619c6`

## `BYTES_USERNAME`

**Required**

Username used for generating Bytes' API JWT

### Examples

`test`

## `BYTES_PASSWORD`

**Required**

Password used for generating Bytes' API JWT

### Examples

`secret`

## `QUEUE_URI`

**Required**

KAT queue URI

### Examples

`amqp://`

## `BYTES_LOG_CFG`

_Optional_, default value: `../../dev.logging.conf`

Path to the logging configuration file

## `BYTES_DB_URI`

**Required**

Bytes Postgres DB URI

### Examples

`postgresql://xx:xx@host:5432/bytes`

## `BYTES_DATA_DIR`

_Optional_, default value: `/data`

Root for all the data. A change means that you no longer have access to old data unless you move it!

## `BYTES_LOG_FILE`

_Optional_, default value: `bytes.log`

Optional file with Bytes logs

## `BYTES_ACCESS_TOKEN_EXPIRE_MINUTES`

_Optional_, default value: `15.0`

Access token expiration time in minutes

## `BYTES_FOLDER_PERMISSION`

_Optional_, default value: `740`

Unix permission level on the folders Bytes creates to save raw files

## `BYTES_FILE_PERMISSION`

_Optional_, default value: `640`

Unix permission level on the raw files themselves

## `BYTES_HASHING_ALGORITHM`

_Optional_, default value: `HashingAlgorithm.SHA512`

Hashing algorithm used in Bytes

### Possible values

`sha512`, `sha224`

## `BYTES_EXT_HASH_REPOSITORY`

_Optional_, default value: `HashingRepositoryReference.IN_MEMORY`

Hashing repository used in Bytes (IN_MEMORY is a stub)

### Possible values

`IN_MEMORY`, `PASTEBIN`, `RFC3161`

## `BYTES_PASTEBIN_API_DEV_KEY`

_Optional_, default value: `None`

API key for Pastebin. Required when using PASTEBIN hashing repository.

## `BYTES_RFC3161_PROVIDER`

_Optional_, default value: `None`

Timestamping. See https://github.com/trbs/rfc3161ng for a list of public providers and their certificates. Required when using RFC3161 hashing repository.

### Examples

`https://freetsa.org/tsr`

## `BYTES_RFC3161_CERT_FILE`

_Optional_, default value: `None`

Path to the certificate of the RFC3161 provider. Required when using RFC3161 hashing repository. `freetsa.crt` is included in the Bytes source code.

### Examples

`bytes/timestamping/certificates/freetsa.crt`

## `BYTES_ENCRYPTION_MIDDLEWARE`

_Optional_, default value: `EncryptionMiddleware.IDENTITY`

Encryption middleware used in Bytes

### Possible values

`IDENTITY`, `NACL_SEALBOX`

## `BYTES_PRIVATE_KEY_B64`

_Optional_, default value: `None`

KATalogus NaCl Sealbox base-64 private key string. Required when using NACL_SEALBOX encryption middleware.

## `BYTES_PUBLIC_KEY_B64`

_Optional_, default value: `None`

KATalogus NaCl Sealbox base-64 public key string. Required when using NACL_SEALBOX encryption middleware.

## `BYTES_METRICS_TTL_SECONDS`

_Optional_, default value: `300`

The time to cache slow queries performed in the metrics endpoint

## `BYTES_METRICS_CACHE_SIZE`

_Optional_, default value: `200`

The amount of cache entries to keep for metrics endpoints with query parameters.

## `SPAN_EXPORT_GRPC_ENDPOINT`

_Optional_, default value: `None`

OpenTelemetry endpoint

## `BYTES_DB_CONNECTION_POOL_SIZE`

_Optional_, default value: `16`

Database connection pool size

## `BYTES_LOGGING_FORMAT`

_Optional_, default value: `text`

Logging format

### Possible values

`text`, `json`

## `S3_BUCKET_PREFIX`

_Optional_, default value: `None`

## `S3_BUCKET`

_Optional_, default value: `None`

## `BUCKET_PER_ORG`

_Optional_, default value: `True`
