==============================
Downgrading an OpenKAT install
==============================

Downgrading is not officially supported, however if you do need to downgrade these tips might help.
Please also be advised that running mixed versions of the OpenKAT parts can lead to unspecified behaviour.

Make backups of your `postgresql` database before attempting rollbacks if you value your data.

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


To fix this:
============

In this example migration `0010` used to be available, we want to downgrade to `0008`.

#. Start the previous version that was installed.

   Start a scheduler container from the original (newer) branch / version / release which contains the migration revision id `0010`.

   If you ran a specific branch, checkout that branch, or some other similar branch that contains the same revision file.
   `alembic` needs this file to know how to migrate back to a lower version.

#. Perform the rollback migration

   We are going to use `alembic` to migrate back to highest the version that is available in your wanted (older) release.

   For example, for release 1.18.2 this is migration `0008`.

   Be advised, not all migrations are fully backwards compatible, there may be data loss if a newer version has columns or tables that the older version does not.

   For the scheduler, you can find the available and migrtions for any release or branch in the folder `mula/scheduler/storage/migrations/versions`
   The following command executes the rollback migration to (in this example) revision `0008`.

   .. code-block:: sh

     docker compose run --rm scheduler python -m alembic --config /app/scheduler/scheduler/storage/migrations/alembic.ini downgrade 0008

#. Check if the rollback was completed

   .. code-block:: sh

     docker compose run --rm scheduler python -m alembic --config /app/scheduler/scheduler/storage/migrations/alembic.ini current

   If the rollback was completed you should see `0008`. You can now deploy and start the wanted container version again.
