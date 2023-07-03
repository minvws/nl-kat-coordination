===========================
Community contributed tools
===========================

Running OpenKAT requires regular updates and some basic debugging. Rob Musquetier contributed several scripts that make life with OpenKAT easier:

Install and update
==================

openKAT_install.sh
------------------

`openKAT_install.sh </utilities/scripts/openKAT_install.sh>`_ installs OpenKAT on Debian 11 or 12, following the steps of the Debian install manual. Before running the script, edit it to specify the version of OpenKAT you want to run.

openKAT_update.sh
-----------------

`openKAT_update.sh </utilities/scripts/openKAT_update.sh>`_ updates OpenKAT, removes old packages and restarts your instances.

Status and logs
===============

status_openkat.sh
-----------------

`status_openkat.sh </utilities/scripts/status_openkat.sh>`_ shows you the status of all OpenKAT related processes from systemctl.

show_journal_openkat.sh
-----------------------

`show_journal_openkat.sh </utilities/scripts/show_journal_openkat.sh>`_ shows the journalctl -n of all OpenKAT related processes.

Starting, stopping, restarting
==============================

start_openkat.sh
----------------

`start_openkat.sh </utilities/scripts/start_openkat.sh>`_ starts all OpenKAT processes.

stop_openkat.sh
---------------

`stop_openkat.sh </utilities/scripts/stop_openkat.sh>`_ stops all OpenKAT processes.

restart_openkat.sh
------------------

`restart_openkat.sh </utilities/scripts/restart_openkat.sh>`_ restarts all OpenKAT processes.

Empty queue
===========

`empty job queue_openkat.sh </utilities/scripts/empty_job_queue_openkat.sh>`_ stops your OpenKAT processes, empties the job queue and starts all processes. It also includes a 60 second sleep to make sure all processes have started completely.



