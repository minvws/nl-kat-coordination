===========================
Community tools and scripts
===========================

Running OpenKAT requires regular updates and some basic debugging. Rob Musquetier contributed several scripts that make life with OpenKAT easier:

Install and update
==================

Install
-------

:download:`openKAT_install.sh <utilities/scripts/openKAT_install.sh>` installs OpenKAT on Debian 11 or 12, following the steps of the Debian install manual. After downloading, use the script as follows:

Change the permissions on the file to 750:

``chmod 750 openKAT_install.sh``

usage:
``./openKAT_install.sh [debian version] [openkat version] [no_super_user]``

Parameters:
debian version: mandatory parameter, currently version 11 or 12 are supported
openKAT version: mandatory parameter, e.g. 1.10.0
no_super_user: optional parameter used for re-installs only

Example for initial install of KAT version 1.10.0 on Debian 11 (create including the super user):
``./openKAT_install.sh 11 1.10.0``

and re-installing KAT version 1.10.0rc1 without super user account on Debian 12:
``./openKAT_install.sh 12 1.10.0rc1 no_super_user``

Update
------

:download:`openKAT_update.sh <utilities/scripts/openKAT_update.sh>` updates OpenKAT, removes old packages and restarts your instances.

To update an existing KAT installation using the Debian packages download the script and change the permissions to 750:

``chmod 750 openKAT_update.sh``

Usage:
``./openKAT_update [Debian version] [openKAT version]``

Parameters:
debian version: mandatory parameter, currently version 11 or 12 are supported
openKAT version: mandatory parameter, e.g. 1.10.0

Example to update a previous openKAT installation to version 1.10.0 on Debian 12:
``./openKAT_update.sh 12 1.10.0``

Status and logs
===============

Status
------

:download:`status_openkat.sh <utilities/scripts/status_openkat.sh>` shows you the status of all OpenKAT related processes from systemctl.

Show journal
------------

:download:`show_journal_openkat.sh <utilities/scripts/show_journal_openkat.sh>` shows the journalctl -n of all OpenKAT related processes.

Starting, stopping, restarting
==============================

Start
-----

:download:`start_openkat.sh <utilities/scripts/start_openkat.sh>` starts all OpenKAT processes.

Stop
----

:download:`stop_openkat.sh <utilities/scripts/stop_openkat.sh>` stops all OpenKAT processes.

Restart
-------

:download:`restart_openkat.sh <utilities/scripts/restart_openkat.sh>` restarts all OpenKAT processes.

Empty queue
===========

:download:`empty job queue_openkat.sh <utilities/scripts/empty_job_queue_openkat.sh>` stops your OpenKAT processes, empties the job queue and starts all processes. It also includes a 60 second sleep to make sure all processes have started completely.
