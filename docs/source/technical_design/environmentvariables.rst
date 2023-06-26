=====================
Environment variables
=====================

We strive to keep ``.env-dist`` complete with all relevant environment variables and their default values.
Not all services require all environment variables, but we use a unified file to keep things simple.



General notes
=============

.. literalinclude:: ../../../.env-dist
   :language: bash

Boefjes
=======
By design, Boefjes do not have access to the host system's environment variables.
If a Boefje requires access to a system-wide variable (e.g. `HTTP_PROXY` or `USER_AGENT`), it should note as such in its `boefje.json` manifest.
These system-wide variables can be set in OpenKAT's global `.env`, by prefixing it with `BOEFJE_`.
This is to prevent a Boefje from accessing variables it should not have access to, such as secrets.
To illustrate: if `BOEFJE_HTTP_PROXY=HTTP_PROXY` is set in the global `.env`, the Boefje can access it as `HTTP_PROXY`.
This feature can also be used to set default values for Katalogus settings. For example, configuring `BOEFJE_TOP_PORTS`
in the global `.env` will set the default value for the `TOP_PORTS` setting (used by the nmap Boefje).
This default value can be overridden by setting any value for `TOP_PORTS` in the Katalogus.


| Environment variable       | Value                        | Description                                       |
|----------------------------|------------------------------|---------------------------------------------------|
| QUEUE_NAME_BOEFJES         | "boefjes"                    | Queue name for boefjes                            |
| QUEUE_NAME_NORMALIZERS     | "normalizers"                | Queue name for normalizers                        |
| QUEUE_HOST                 | "rabbitmq"                   | The RabbitMQ host                                 |
| OCTOPOES_API               | "http://octopoes_api:80"     | URI for the Octopoes API                          |
| BYTES_API                  | "http://bytes:8000"          | URI for the Bytes API                             |
| KATALOGUS_API              | "http://katalogus:8000"      | URI for the Katalogus API                         |
| KATALOGUS_DB_URI           | "postgresql:// ..."          | URI for the Postgresql DB                         |
| ENCRYPTION_MIDDLEWARE      | "IDENTITY" or "NACL_SEALBOX" | Encryption to use for the katalogus settings      |
| KATALOGUS_PRIVATE_KEY_B_64 | "..."                        | KATalogus NaCl Sealbox base-64 private key string |
| KATALOGUS_PUBLIC_KEY_B_64  | "..."                        | KATalogus NaCl Sealbox base-64 public key string  |

Keiko
=====
The `templates`, `glossaries` and `assets` folders should for now point to the corresponding folders in the repository.
Example with environment variables, assuming that the keiko code lives in `/app/keiko`:
```bash
export KEIKO_TEMPLATES_FOLDER=/app/keiko/templates
export KEIKO_ASSETS_FOLDER=/app/keiko/assets
export KEIKO_GLOSSARIES_FOLDER=/app/keiko/glossaries
export KEIKO_REPORT_FOLDER=/var/keiko/reports
uvicorn keiko.app:api --port 8005
```


Bytes
=====
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
BYTES_METRICS_TTL_SECONDS=0  # The time to cache slow queries performed in the metrics endpoint.
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

Octopoes
========
```bash
export XTDB_URI="http://xtdb.local"
export QUEUE_URI="amqp://guest:guest@localhost:5672/%2fkat"

# Optional
export LOG_CFG="logging.yml"
export QUEUE_NAME_OCTOPOES="octopoes"
```
