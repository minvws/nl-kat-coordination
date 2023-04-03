=============================
Debugging and troubleshooting
=============================


Checking the health status of the KAT modules
=============================================


If you see any errors or warnings, please check the logs of the affected module.


=================
Debugging OpenKAT
=================

If OpenKAT does not function in the way you expect, there are several options to help you find the cause and solve the problem. Checking the healthpage, logs, services and usersettings are the basics.

If you can't find it, we look forward to bugreports as well. Squashing bugs makes everyone happy. Create an issue on GitHub or send us a report on meedoen@openkat.nl.


Healthpage
==========

The admin and superuser accounts have access to the health page. In the footer of every page, you can find a link to the Health page.
This page shows the status of all containerized KAT modules, their version, and any self-reported warnings or errors.
If you KAT deployment is not working properly, this is the first place to check.

... image:: img/healthpage.png
  :alt: healthpage

You can also access the health JSON endpoint programmatically at ``http<s>://<rocky-host>/<org-code>/health``.

If one of the modules is unhappy, the 'windows 3.11 approach' of a simple restart might be needed. Otherwise there might be a configuration issue or bug. In the latter two cases, check the issues on Github or contact the team on signal or IRC.

Processes
=========

When debugging, check if the actual processes are running. Depending on the way you run OpenKAT, there are several ways to do this:

Dockers
-------

``dockerps`` gives you an overview of all running dockers.

... image:: img/dockerps.png
  :alt: docker containers

Packaged versions
-----------------

``systemctl status KAT-*`` gives you an overview of all KAT related processes. 

The relevant services for OpenKAT: 

* kat-mula.service
* kat-octopoes.service
* kat-keiko.service
* kat-rocky.service
* kat-boefjes.service
* kat-katalogus.service
* kat-octopoes-worker.service
* kat-normalizers.service
* kat-bytes.service

Logs
----

Sometimes, the logs might give output that is usefull. 

``journalctl`` has the output of the logs. Select the ``kat-*`` related services and relevant timeframe to find out more about the service you want to inspect. 

Diskspace in debug mode
=======================

When OpenKAT runs in debug mode, it produces large logfiles. Several hours of debug mode might fill a disk, so make sure to check this and clean up space. 

Permissions
===========

Check in the user interface if the users have permission to perform scans and are part of an organization. 

The current usermodel also needs a superuser that is part of an organization. Normally this is set automagically. With several organizations in your instance the superuser might end up alone. This must be corrected through the django interface, in which the superuser can be added to the organization. 

You can reach the django admin interface through /admin on the rocky instance. While you are there, do check the `hardening settings <https://docs.openkat.nl/technical_design/hardening.html>`_ if you have not already done so. 


SystemCTL output
================

This is the typical systemctl status output, included for completeness.  

..code-block::
● kat-mula.service - kat-mula daemon
     Loaded: loaded (/lib/systemd/system/kat-mula.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2023-03-28 23:24:31 CEST; 2 days ago
   Main PID: 53374 (python)
      Tasks: 7 (limit: 4574)
     Memory: 52.2M
        CPU: 8h 29min 57.501s
     CGroup: /system.slice/kat-mula.service
             └─53374 /opt/venvs/kat-mula/bin/python -m scheduler

::

Mar 31 11:36:54 deb17 kat-mula[53374]: [2023-03-31 11:36:54 +0200] [53374] [INFO] [h11_impl] [uvicorn.access] 127.0.0.1:51232 - "GET /queues/normalizer-test/pop HTTP/1.1" 200
Mar 31 11:36:54 deb17 kat-mula[53374]: [2023-03-31 11:36:54 +0200] [53374] [INFO] [h11_impl] [uvicorn.access] 127.0.0.1:51236 - "GET /queues HTTP/1.1" 200
Mar 31 11:36:54 deb17 kat-mula[53374]: [2023-03-31 11:36:54 +0200] [53374] [INFO] [h11_impl] [uvicorn.access] 127.0.0.1:51236 - "GET /queues/normalizer-test/pop HTTP/1.1" 200
Mar 31 11:37:33 deb17 kat-mula[53374]: [2023-03-31 11:37:33 +0200] [53374] [INFO] [connection_workflow] [pika.adapters.utils.connection_workflow] Pika version 1.2.0 connecting to ('127.0.0.1', 5672)
Mar 31 11:37:33 deb17 kat-mula[53374]: [2023-03-31 11:37:33 +0200] [53374] [INFO] [io_services_utils] [pika.adapters.utils.io_services_utils] Socket connected: <socket.socket fd=17, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=6, laddr=('127.0.0.1', 53862), raddr=('127.0.0.1', 5672)>
Mar 31 11:37:33 deb17 kat-mula[53374]: [2023-03-31 11:37:33 +0200] [53374] [INFO] [connection_workflow] [pika.adapters.utils.connection_workflow] Streaming transport linked up: (<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0x7f0bfb5bb790>, _StreamingProtocolShim: <SelectConnection PROTOCOL transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0x7f0bfb5bb790> params=<URLParameters host=127.0.0.1 port=5672 virtual_host=kat ssl=False>>).
Mar 31 11:37:33 deb17 kat-mula[53374]: [2023-03-31 11:37:33 +0200] [53374] [INFO] [connection_workflow] [pika.adapters.utils.connection_workflow] AMQPConnector - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0x7f0bfb5bb790> params=<URLParameters host=127.0.0.1 port=5672 virtual_host=kat ssl=False>>
Mar 31 11:37:33 deb17 kat-mula[53374]: [2023-03-31 11:37:33 +0200] [53374] [INFO] [connection_workflow] [pika.adapters.utils.connection_workflow] AMQPConnectionWorkflow - reporting success: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0x7f0bfb5bb790> params=<URLParameters host=127.0.0.1 port=5672 virtual_host=kat ssl=False>>
Mar 31 11:37:33 deb17 kat-mula[53374]: [2023-03-31 11:37:33 +0200] [53374] [INFO] [blocking_connection] [pika.adapters.blocking_connection] Connection workflow succeeded: <SelectConnection OPEN transport=<pika.adapters.utils.io_services_utils._AsyncPlaintextTransport object at 0x7f0bfb5bb790> params=<URLParameters host=127.0.0.1 port=5672 virtual_host=kat ssl=False>>
Mar 31 11:37:33 deb17 kat-mula[53374]: [2023-03-31 11:37:33 +0200] [53374] [INFO] [blocking_connection] [pika.adapters.blocking_connection] Created channel=1

::

● kat-octopoes.service - kat-octopoes daemon
     Loaded: loaded (/lib/systemd/system/kat-octopoes.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2023-03-28 15:43:24 CEST; 2 days ago
   Main PID: 594 (python)
      Tasks: 11 (limit: 4574)
     Memory: 255.7M
        CPU: 2h 57min 36.142s
     CGroup: /system.slice/kat-octopoes.service
             ├─594 /opt/venvs/kat-octopoes/bin/python -m gunicorn --access-logfile - -c /etc/kat/octopoes.gunicorn.conf.py -k uvicorn.workers.UvicornWorker octopoes.api.api:app
             ├─734 /opt/venvs/kat-octopoes/bin/python -m gunicorn --access-logfile - -c /etc/kat/octopoes.gunicorn.conf.py -k uvicorn.workers.UvicornWorker octopoes.api.api:app
             ├─737 /opt/venvs/kat-octopoes/bin/python -m gunicorn --access-logfile - -c /etc/kat/octopoes.gunicorn.conf.py -k uvicorn.workers.UvicornWorker octopoes.api.api:app
             ├─743 /opt/venvs/kat-octopoes/bin/python -m gunicorn --access-logfile - -c /etc/kat/octopoes.gunicorn.conf.py -k uvicorn.workers.UvicornWorker octopoes.api.api:app
             ├─744 /opt/venvs/kat-octopoes/bin/python -m gunicorn --access-logfile - -c /etc/kat/octopoes.gunicorn.conf.py -k uvicorn.workers.UvicornWorker octopoes.api.api:app
             └─747 /opt/venvs/kat-octopoes/bin/python -m gunicorn --access-logfile - -c /etc/kat/octopoes.gunicorn.conf.py -k uvicorn.workers.UvicornWorker octopoes.api.api:app

::

Mar 31 11:37:36 deb17 kat-octopoes[747]: [2023-03-31 11:37:36 +0200] [747] [INFO] [h11_impl] 127.0.0.1:57396 - "GET /test/objects/random?amount=50 HTTP/1.1" 200
Mar 31 11:37:36 deb17 python[747]: [2023-03-31 11:37:36 +0200] [747] [INFO] [h11_impl] 127.0.0.1:57396 - "GET /test/objects/random?amount=50 HTTP/1.1" 200
Mar 31 11:37:38 deb17 kat-octopoes[734]: [2023-03-31 11:37:38 +0200] [734] [INFO] [service] Populating scan profiles for 50 oois
Mar 31 11:37:38 deb17 python[734]: [2023-03-31 11:37:38 +0200] [734] [INFO] [service] Populating scan profiles for 50 oois
Mar 31 11:37:38 deb17 kat-octopoes[734]: [2023-03-31 11:37:38 +0200] [734] [INFO] [h11_impl] 127.0.0.1:34558 - "GET /test/objects/random?amount=50 HTTP/1.1" 200
Mar 31 11:37:38 deb17 python[734]: [2023-03-31 11:37:38 +0200] [734] [INFO] [h11_impl] 127.0.0.1:34558 - "GET /test/objects/random?amount=50 HTTP/1.1" 200
Mar 31 11:37:40 deb17 kat-octopoes[734]: [2023-03-31 11:37:40 +0200] [734] [INFO] [service] Populating scan profiles for 50 oois
Mar 31 11:37:40 deb17 python[734]: [2023-03-31 11:37:40 +0200] [734] [INFO] [service] Populating scan profiles for 50 oois
Mar 31 11:37:40 deb17 kat-octopoes[734]: [2023-03-31 11:37:40 +0200] [734] [INFO] [h11_impl] 127.0.0.1:34558 - "GET /test/objects/random?amount=50 HTTP/1.1" 200
Mar 31 11:37:40 deb17 python[734]: [2023-03-31 11:37:40 +0200] [734] [INFO] [h11_impl] 127.0.0.1:34558 - "GET /test/objects/random?amount=50 HTTP/1.1" 200

::

● kat-keiko.service - kat-keiko daemon
     Loaded: loaded (/lib/systemd/system/kat-keiko.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2023-03-28 15:43:24 CEST; 2 days ago
   Main PID: 590 (python)
      Tasks: 6 (limit: 4574)
     Memory: 102.5M
        CPU: 52min 6.564s
     CGroup: /system.slice/kat-keiko.service
             ├─590 /opt/venvs/kat-keiko/bin/python -m gunicorn --access-logfile - -c /etc/kat/keiko.gunicorn.conf.py -k uvicorn.workers.UvicornWorker keiko.app:api
             ├─713 /opt/venvs/kat-keiko/bin/python -m gunicorn --access-logfile - -c /etc/kat/keiko.gunicorn.conf.py -k uvicorn.workers.UvicornWorker keiko.app:api
             ├─714 /opt/venvs/kat-keiko/bin/python -m gunicorn --access-logfile - -c /etc/kat/keiko.gunicorn.conf.py -k uvicorn.workers.UvicornWorker keiko.app:api
             ├─715 /opt/venvs/kat-keiko/bin/python -m gunicorn --access-logfile - -c /etc/kat/keiko.gunicorn.conf.py -k uvicorn.workers.UvicornWorker keiko.app:api
             ├─716 /opt/venvs/kat-keiko/bin/python -m gunicorn --access-logfile - -c /etc/kat/keiko.gunicorn.conf.py -k uvicorn.workers.UvicornWorker keiko.app:api
             └─717 /opt/venvs/kat-keiko/bin/python -m gunicorn --access-logfile - -c /etc/kat/keiko.gunicorn.conf.py -k uvicorn.workers.UvicornWorker keiko.app:api

::

● kat-rocky.service - kat-rocky daemon
     Loaded: loaded (/lib/systemd/system/kat-rocky.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2023-03-28 15:43:37 CEST; 2 days ago
   Main PID: 595 (uwsgi)
     Status: "uWSGI is ready"
      Tasks: 10 (limit: 4574)
     Memory: 134.8M
        CPU: 27.696s
     CGroup: /system.slice/kat-rocky.service
             ├─ 595 /opt/venvs/kat-rocky/bin/uwsgi --ini /etc/kat/rocky.uwsgi.ini
             ├─1249 /opt/venvs/kat-rocky/bin/uwsgi --ini /etc/kat/rocky.uwsgi.ini
             └─1257 /opt/venvs/kat-rocky/bin/uwsgi --ini /etc/kat/rocky.uwsgi.ini

::

● kat-boefjes.service - kat-boefjes daemon
     Loaded: loaded (/lib/systemd/system/kat-boefjes.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2023-03-28 15:43:24 CEST; 2 days ago
   Main PID: 587 (python)
      Tasks: 6 (limit: 4574)
     Memory: 105.8M
        CPU: 19.046s
     CGroup: /system.slice/kat-boefjes.service
             ├─ 587 /opt/venvs/kat-boefjes/bin/python -m boefjes boefje
             ├─1237 /opt/venvs/kat-boefjes/bin/python -m boefjes boefje
             └─1238 /opt/venvs/kat-boefjes/bin/python -m boefjes boefje

::

● kat-katalogus.service - kat-katalogus daemon
     Loaded: loaded (/lib/systemd/system/kat-katalogus.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2023-03-28 15:43:24 CEST; 2 days ago
   Main PID: 589 (python)
      Tasks: 11 (limit: 4574)
     Memory: 408.3M
        CPU: 1h 24min 11.889s
     CGroup: /system.slice/kat-katalogus.service
             ├─589 /opt/venvs/kat-boefjes/bin/python -m gunicorn --access-logfile - -c /etc/kat/katalogus.gunicorn.conf.py -k uvicorn.workers.UvicornWorker boefjes.katalogus.api:app
             ├─726 /opt/venvs/kat-boefjes/bin/python -m gunicorn --access-logfile - -c /etc/kat/katalogus.gunicorn.conf.py -k uvicorn.workers.UvicornWorker boefjes.katalogus.api:app
             ├─733 /opt/venvs/kat-boefjes/bin/python -m gunicorn --access-logfile - -c /etc/kat/katalogus.gunicorn.conf.py -k uvicorn.workers.UvicornWorker boefjes.katalogus.api:app
             ├─740 /opt/venvs/kat-boefjes/bin/python -m gunicorn --access-logfile - -c /etc/kat/katalogus.gunicorn.conf.py -k uvicorn.workers.UvicornWorker boefjes.katalogus.api:app
             ├─742 /opt/venvs/kat-boefjes/bin/python -m gunicorn --access-logfile - -c /etc/kat/katalogus.gunicorn.conf.py -k uvicorn.workers.UvicornWorker boefjes.katalogus.api:app
             └─745 /opt/venvs/kat-boefjes/bin/python -m gunicorn --access-logfile - -c /etc/kat/katalogus.gunicorn.conf.py -k uvicorn.workers.UvicornWorker boefjes.katalogus.api:app

::

Mar 31 11:35:48 deb17 kat-katalogus[742]: 127.0.0.1:50904 - "GET /v1/organisations HTTP/1.1" 200
Mar 31 11:36:15 deb17 kat-katalogus[740]: 127.0.0.1:34656 - "GET /v1/organisations HTTP/1.1" 200
Mar 31 11:36:16 deb17 kat-katalogus[740]: 127.0.0.1:34656 - "GET /v1/organisations/test/plugins HTTP/1.1" 200
Mar 31 11:36:40 deb17 kat-katalogus[733]: 127.0.0.1:45206 - "GET /v1/organisations HTTP/1.1" 200
Mar 31 11:36:45 deb17 kat-katalogus[733]: 127.0.0.1:45210 - "GET /v1/organisations HTTP/1.1" 200
Mar 31 11:36:46 deb17 kat-katalogus[733]: 127.0.0.1:45210 - "GET /v1/organisations/test/plugins HTTP/1.1" 200
Mar 31 11:36:48 deb17 kat-katalogus[740]: 127.0.0.1:34596 - "GET /v1/organisations HTTP/1.1" 200
Mar 31 11:37:15 deb17 kat-katalogus[726]: 127.0.0.1:47396 - "GET /v1/organisations HTTP/1.1" 200
Mar 31 11:37:16 deb17 kat-katalogus[726]: 127.0.0.1:47396 - "GET /v1/organisations/test/plugins HTTP/1.1" 200
Mar 31 11:37:40 deb17 kat-katalogus[726]: 127.0.0.1:51428 - "GET /v1/organisations HTTP/1.1" 200

::

● kat-octopoes-worker.service - kat-octopoes worker
     Loaded: loaded (/lib/systemd/system/kat-octopoes-worker.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2023-03-28 15:43:24 CEST; 2 days ago
   Main PID: 593 (python)
      Tasks: 4 (limit: 4574)
     Memory: 135.3M
        CPU: 1h 30min 50.091s
     CGroup: /system.slice/kat-octopoes-worker.service
             ├─ 593 /opt/venvs/kat-octopoes/bin/python -m celery -A octopoes.tasks.tasks worker -B -s /tmp/celerybeat-schedule --loglevel=WARNING
             ├─1245 /opt/venvs/kat-octopoes/bin/python -m celery -A octopoes.tasks.tasks worker -B -s /tmp/celerybeat-schedule --loglevel=WARNING
             ├─1246 /opt/venvs/kat-octopoes/bin/python -m celery -A octopoes.tasks.tasks worker -B -s /tmp/celerybeat-schedule --loglevel=WARNING
             └─1247 /opt/venvs/kat-octopoes/bin/python -m celery -A octopoes.tasks.tasks worker -B -s /tmp/celerybeat-schedule --loglevel=WARNING

::

● kat-normalizers.service - kat-normalizers daemon
     Loaded: loaded (/lib/systemd/system/kat-normalizers.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2023-03-28 15:43:24 CEST; 2 days ago
   Main PID: 592 (python)
      Tasks: 6 (limit: 4574)
     Memory: 75.1M
        CPU: 1min 47.591s
     CGroup: /system.slice/kat-normalizers.service
             ├─ 592 /opt/venvs/kat-boefjes/bin/python -m boefjes normalizer
             ├─1232 /opt/venvs/kat-boefjes/bin/python -m boefjes normalizer
             └─1233 /opt/venvs/kat-boefjes/bin/python -m boefjes normalizer

::

Mar 31 11:34:54 deb17 kat-normalizers[1233]: [2023-03-31 11:34:54 +0200] [1233] [INFO] [app] Popping from queue normalizer-test
Mar 31 11:34:54 deb17 kat-normalizers[1233]: [2023-03-31 11:34:54 +0200] [1233] [INFO] [app] Queue normalizer-test empty
Mar 31 11:35:54 deb17 kat-normalizers[1232]: [2023-03-31 11:35:54 +0200] [1232] [INFO] [app] Popping from queue normalizer-test
Mar 31 11:35:54 deb17 kat-normalizers[1232]: [2023-03-31 11:35:54 +0200] [1232] [INFO] [app] Queue normalizer-test empty
Mar 31 11:35:54 deb17 kat-normalizers[1233]: [2023-03-31 11:35:54 +0200] [1233] [INFO] [app] Popping from queue normalizer-test
Mar 31 11:35:54 deb17 kat-normalizers[1233]: [2023-03-31 11:35:54 +0200] [1233] [INFO] [app] Queue normalizer-test empty
Mar 31 11:36:54 deb17 kat-normalizers[1232]: [2023-03-31 11:36:54 +0200] [1232] [INFO] [app] Popping from queue normalizer-test
Mar 31 11:36:54 deb17 kat-normalizers[1232]: [2023-03-31 11:36:54 +0200] [1232] [INFO] [app] Queue normalizer-test empty
Mar 31 11:36:54 deb17 kat-normalizers[1233]: [2023-03-31 11:36:54 +0200] [1233] [INFO] [app] Popping from queue normalizer-test
Mar 31 11:36:54 deb17 kat-normalizers[1233]: [2023-03-31 11:36:54 +0200] [1233] [INFO] [app] Queue normalizer-test empty

::

● kat-bytes.service - kat-bytes daemon
     Loaded: loaded (/lib/systemd/system/kat-bytes.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2023-03-28 15:43:24 CEST; 2 days ago
   Main PID: 588 (python)
      Tasks: 11 (limit: 4574)
     Memory: 351.7M
        CPU: 10h 25min 51.699s
     CGroup: /system.slice/kat-bytes.service
             ├─588 /opt/venvs/kat-bytes/bin/python -m gunicorn --access-logfile - -c /etc/kat/bytes.gunicorn.conf.py -k uvicorn.workers.UvicornWorker bytes.api:app
             ├─703 /opt/venvs/kat-bytes/bin/python -m gunicorn --access-logfile - -c /etc/kat/bytes.gunicorn.conf.py -k uvicorn.workers.UvicornWorker bytes.api:app
             ├─704 /opt/venvs/kat-bytes/bin/python -m gunicorn --access-logfile - -c /etc/kat/bytes.gunicorn.conf.py -k uvicorn.workers.UvicornWorker bytes.api:app
             ├─710 /opt/venvs/kat-bytes/bin/python -m gunicorn --access-logfile - -c /etc/kat/bytes.gunicorn.conf.py -k uvicorn.workers.UvicornWorker bytes.api:app
             ├─711 /opt/venvs/kat-bytes/bin/python -m gunicorn --access-logfile - -c /etc/kat/bytes.gunicorn.conf.py -k uvicorn.workers.UvicornWorker bytes.api:app
             └─712 /opt/venvs/kat-bytes/bin/python -m gunicorn --access-logfile - -c /etc/kat/bytes.gunicorn.conf.py -k uvicorn.workers.UvicornWorker bytes.api:app

::

Mar 31 11:37:41 deb17 kat-bytes[710]: [2023-03-31 11:37:41 +0200] [710] [INFO] [sql_meta_repository] Querying boefje meta
Mar 31 11:37:41 deb17 kat-bytes[710]: [2023-03-31 11:37:41 +0200] [710] [INFO] [sql_meta_repository] Committing session
Mar 31 11:37:41 deb17 kat-bytes[710]: [2023-03-31 11:37:41 +0200] [710] [INFO] [h11_impl] 127.0.0.1:50100 - "GET /bytes/boefje_meta?boefje_id=dns-sec&input_ooi=Hostname%7Cinternet%7Cexample.com.&organization=test&limit=1&descending=true HTTP/1.1" 200
Mar 31 11:37:41 deb17 kat-bytes[710]: [2023-03-31 11:37:41 +0200] [710] [INFO] [sql_meta_repository] Closing session
Mar 31 11:37:41 deb17 kat-bytes[710]: [2023-03-31 11:37:41 +0200] [710] [INFO] [sql_meta_repository] Querying boefje meta
Mar 31 11:37:41 deb17 kat-bytes[710]: [2023-03-31 11:37:41 +0200] [710] [INFO] [sql_meta_repository] Committing session
Mar 31 11:37:41 deb17 kat-bytes[710]: [2023-03-31 11:37:41 +0200] [710] [INFO] [h11_impl] 127.0.0.1:50100 - "GET /bytes/boefje_meta?boefje_id=ssl-certificates&input_ooi=Website%7Cinternet%7C192.0.2.3%7Ctcp%7C80%7Chttp%7Cinternet%7Cexample.com..&organization=test&limit=1&descending=true HTTP/1.1" 200
Mar 31 11:37:41 deb17 kat-bytes[710]: [2023-03-31 11:37:41 +0200] [710] [INFO] [sql_meta_repository] Closing session
Mar 31 11:37:41 deb17 kat-bytes[710]: [2023-03-31 11:37:41 +0200] [710] [INFO] [sql_meta_repository] Querying boefje meta
Mar 31 11:37:41 deb17 kat-bytes[710]: [2023-03-31 11:37:41 +0200] [710] [INFO] [sql_meta_repository] Committing session
Mar 31 11:37:41 deb17 kat-bytes[710]: [2023-03-31 11:37:41 +0200] [710] [INFO] [h11_impl] 127.0.0.1:50100 - "GET /bytes/boefje_meta?boefje_id=ssl-certificates&input_ooi=Website%7Cinternet%7C192.0.2.3%7Ctcp%7C80%7Chttp%7Cinternet%7Cexample.com.&organization=test&limit=1&descending=true HTTP/1.1" 200



