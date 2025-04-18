==============================
Downgrading an OpenKAT install
==============================

Downgrading is not officially supported, however if you do need to downgrade these tips might help.
Please also be advised that running mixed versions of the OpenKAT parts can lead to unspecified behaviour.

Make Backups of your `postgresql` database before attempting rollbacks if you value your data.

Downgrading the scheduler / Mula:
=================================

If you have deployed a previous version of the Scheduler, and are presented with Alembic migration errors about migration files being missing, this indicates that the version you initially installed (be it Main, or a specific release) has ran migrations that are now no longer available for the container or for the process.
Example:

.. code-block:: sh

  # docker compose logs -f scheduler
  INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
  INFO  [alembic.runtime.migration] Will assume transactional DDL.
  ERROR [alembic.util.messaging] Can't locate revision identified by '0010'
  FAILED: Can't locate revision identified by '0010'


In this example migration 10 used to be available, and has been applied, but now can no longer be found.

To fix this:

1. Start a scheduler container from the original (newer) version which contains the migration revision id `0010` (for our example).

   If you ran a specific branch, checkout that branch, or some other similar branch that contains the same revision file.
   `alembic` needs this file to know how to migrate back to a lower version.

2. Obtain an interactive shell in the scheduler container. The `docker` command would be:

.. code-block:: sh

  docker compose exec <service> /bin/bash
  docker compose exec scheduler /bin/bash


3. Now, inside the container we are going to use `alembic` to migrate back to highest the version that is available in your wanted (older) release.

  For example, for release 1.18.2 this is migration `0008`.

  Be advised, not all migrations are ful backwards compatible, there might be data-loss if a newer version has columns or tables that the older version does not.

  For the scheduler, you can find the available and migrtions for any release or branch in the folder `mula/scheduler/storage/migrations/versions`
  The following command executes the rollback migration to (in this example) revision `0008`.

.. code-block:: sh

  python -m alembic --config /app/scheduler/scheduler/storage/migrations/alembic.ini downgrade 0008


4. Check if the rollback was completed:

.. code-block:: sh

  python -m alembic --config /app/scheduler/scheduler/storage/migrations/alembic.ini current


5. If the rollback was completed you should see `0008`. You can now deploy and start the wanted container version again.
