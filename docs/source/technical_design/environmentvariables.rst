=====================
Environment variables
=====================

We strive to keep ``.env-dist`` complete with all relevant environment variables and their default values.
Not all services require all environment variables, but we use a unified file to keep things simple.

Current ``.env-dist``
=====================

.. literalinclude:: ../../../.env-dist
   :language: bash

Boefjes
=======
By design, Boefjes do not have access to the host system's environment variables.
If a Boefje requires access to a system-wide variable (e.g. ``HTTP_PROXY`` or ``USER_AGENT``), it should note as such in its ``boefje.json`` manifest.
These system-wide variables can be set in OpenKAT's global ``.env``, by prefixing it with ``BOEFJE_``.
This is to prevent a Boefje from accessing variables it should not have access to, such as secrets.
To illustrate: if ``BOEFJE_HTTP_PROXY=HTTP_PROXY`` is set in the global ``.env``, the Boefje can access it as ``HTTP_PROXY``.
This feature can also be used to set default values for Katalogus settings. For example, configuring ``BOEFJE_TOP_PORTS``
in the global ``.env`` will set the default value for the ``TOP_PORTS`` setting (used by the nmap Boefje).
This default value can be overridden by setting any value for ``TOP_PORTS`` in the Katalogus.


Bytes
=====
Every raw file is hashed with the current ``ended_at`` of the ``boefje_meta``,
which functions as a 'proof' of it being uploaded at that time.
These proofs can be uploaded externally (a 3rd party) such that we can verify that this data was saved in the past.

Current implementations are:

- ``EXT_HASH_SERVICE="IN_MEMORY"`` (just a stub)
- ``EXT_HASH_SERVICE="PASTEBIN"`` (Needs pastebin API development key)
- ``EXT_HASH_SERVICE="RFC3161"``

For the RFC3161 implementation, see https://www.ietf.org/rfc/rfc3161.txt and https://github.com/trbs/rfc3161ng as a reference.
To use this implementation, set your environment to:

- ``EXT_HASH_SERVICE=RFC3161``
- ``RFC3161_PROVIDER="https://freetsa.org/tsr"`` (example)
- ``RFC3161_CERT_FILE="bytes/timestamping/certificates/freetsa.crt"`` (example)

Adding a new implementation means implementing the ``bytes.repositories.hash_repository::HashRepository`` interface.
Bind your new implementation in ``bytes.timestamping.provider::create_hash_repository``.

The secure-hashing-algorithm can be specified with an env var: ``HASHING_ALGORITHM="SHA512"``.

```bash
HASHING_ALGORITHM="SHA512"
EXT_HASH_SERVICE="IN_MEMORY"
PASTEBIN_API_DEV_KEY=""
```

Files in bytes can be saved encrypted to disk,
the implementation can be set using an env-var, ``ENCRYPTION_MIDDLEWARE``. The options are:

- ``"IDENTITY"``
- ``"NACL_SEALBOX"``

``IDENTITY`` means using no encryption.


The ``"NACL_SEALBOX"`` option requires the ``KAT_PRIVATE_KEY_B64`` and ``VWS_PUBLIC_KEY_B64`` env vars.

```bash
ENCRYPTION_MIDDLEWARE="IDENTITY"
KAT_PRIVATE_KEY_B64=""
VWS_PUBLIC_KEY_B64=""
```
