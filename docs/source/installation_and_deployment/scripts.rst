Scripts
=======

There are some scripts in the `scripts/installation
<https://github.com/minvws/nl-kat-coordination/tree/main/scripts/installation>`__ directory
that can be used to install and update OpenKAT on Debian and will do all the
steps described on the :ref:`Debian installation<Production: Debian packages>` page.

Installation
------------

The `openkat-install.sh
<https://raw.githubusercontent.com/minvws/nl-kat-coordination/main/scripts/installation/openkat-install.sh>`__
script installs OpenKAT. Change the permissions on the file to 755:

``chmod 755 openkat-install.sh``

usage:
``./openkat-install.sh [OpenKAT version] [no_super_user]``

Parameters:
 * openKAT version: optional parameter, e.g. 1.10.0. If not supplied latest version is used.
 * no_super_user: optional parameter used for re-installs and won't create superuser account

Example for initial install of KAT version 1.10.0 (including creatng the super user):

``./openkat-install.sh 1.10.0``

and re-installing KAT version 1.10.0rc1 without super user account:

``./openkat-_install.sh 1.10.0rc1 no_super_user``

Update
-------

The `openkat-update.sh
<https://raw.githubusercontent.com/minvws/nl-kat-coordination/main/scripts/installation/openkat-update.sh>`__
script updates OpenKAT. Change the permissions on the file to 755:

``chmod 755 openkat-update.sh``

Usage:

``./openkat-update.sh [openKAT version]``

Parameters:
 * openKAT version: optional parameter, e.g. 1.10.0. If not supplied latest version is used.

Example to update a previous openKAT installation to version 1.10.0:

``./openkat-update.sh 1.10.0``

Status and logs
---------------

`openkat-status.sh
<https://raw.githubusercontent.com/minvws/nl-kat-coordination/main/scripts/installation/openkat-status.sh>`__
shows you the status of all OpenKAT related processes from systemctl.

`openkat-show-journal.sh
<https://raw.githubusercontent.com/minvws/nl-kat-coordination/main/scripts/installation/openkat-show-journal.sh>`__
shows the journalctl -n of all OpenKAT related processes.

Starting, stopping, restarting
------------------------------

`openkat-start.sh
<https://raw.githubusercontent.com/minvws/nl-kat-coordination/main/scripts/installation/openkat-start.sh>`__
starts all OpenKAT processes.

`openkat-stop.sh
<https://raw.githubusercontent.com/minvws/nl-kat-coordination/main/scripts/installation/openkat-stop.sh>`__
stops all OpenKAT processes.

`openkat-restart.sh
<https://raw.githubusercontent.com/minvws/nl-kat-coordination/main/scripts/installation/openkat-restart.sh>`__
restarts all OpenKAT processes.

Empty queue
-----------

`openkat-empty-job-queue.sh
<https://raw.githubusercontent.com/minvws/nl-kat-coordination/main/scripts/installation/openkat-empty-job-queue.sh>`__
stops your OpenKAT processes, empties the job queue and starts all processes.
