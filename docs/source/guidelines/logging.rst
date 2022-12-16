Logging
#######

Some general guidelines for how to log within your applications:

- Log after, not before. This communicates what operation was performed, and what the result was.

.. code-block:: python

    # Don't do this
    log.info("Doing stuff")
    some_stuff()

    # Do this
    some_stuff()
    log.info("Did stuff")

- Separate parameters and messages.
  This will make sure that logs are parseable, searchable, easy to extend, and read.
  A python package called `structlog <https://www.structlog.org/>`_ can help with this.
  This is one example on how to separate parameters and messages, you can also decide to for instance use a json output:

.. code-block:: python

    # Don't do this
    some_stuff()
    log.info("Did stuff with %s", url)

    # Do this
    some_stuff()
    log.info("Did stuff with %s [url=%s]", url, url)


* Use ``FATAL`` when immediate intervention is needed and the system can't
  continue running.

* Distinguish between ``WARNING`` and ``ERROR``. Use ``WARNING`` when you did
  something but an error occurred. Use ``ERROR`` when something wasn't done and
  went wrong. These severities need attention and fixing.

* ``INFO`` is for business, ``DEBUG`` is for technology. The ``INFO`` log should look
  like a book.

.. code-block:: text

    INFO  | User registered for newsletter. [user_id="3a937a10-da92-49b6-9350-6f2c74bcb34c"]
    INFO  | Newsletter sent to user. [user_id="3a937a10-da92-49b6-9350-6f2c74bcb34c"]
    INFO  | User unsubscribed from newsletter. [user_id="3a937a10-da92-49b6-9350-6f2c74bcb34c"]

.. code-block:: text

    DEBUG | Saved user to newsletter list. [user_id=3a937a10-da92-49b6-9350-6f2c74bcb34c]
    DEBUG | Sent welcome email. [user_id=3a937a10-da92-49b6-9350-6f2c74bcb34c]
    INFO  | User registered for newsletter. [user_id="3a937a10-da92-49b6-9350-6f2c74bcb34c"]
    DEBUG | Started cron job to send newsletter of the day. [subscribers=12345]
    INFO  | Newsletter sent to user. [user_id="3a937a10-da92-49b6-9350-6f2c74bcb34c"]
    INFO  | User unsubscribed from newsletter. [user_id="3a937a10-da92-49b6-9350-6f2c74bcb34c"]

- Design log to be chainable. When using parameters in logging make sure that
  it can be aggregated, over multiple logs. E.g.
  ``[user_id="3a937a10-da92-49b6-9350-6f2c74bcb34c"]`` allows you to aggregate
  logs from multiple logs with the same ``user_id`` parameter.

- Never log any personal identifiable information, and confidential
  information. So no email addresses, names, credit card numbers, etc.

- Always log in UTC, log in milliseconds. Synchronize your servers with a NTP
  daemon.

..
    - TODO: request guid, see if this is already done by log aggregation of them
      used cloud provider.

..
    - TODO: what always should be present: time, severity, process ID, thread ID,
      application identifier, request identifier, (user identifier), and message.

**Sources**

- `<https://tuhrig.de/my-logging-best-practices/>`_
- `<https://web.archive.org/web/20201023044233/>`_
- `<https://nerds.kueski.com/better-logging/>`_
- `<https://guicommits.com/how-to-log-in-python-like-a-pro/>`_