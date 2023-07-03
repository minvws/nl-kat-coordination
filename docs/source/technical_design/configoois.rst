======================
What are Config OOI's?
======================

Config OOI's are, in principle, the same as regular objects, but serve to apply settings to the object that they to.
Re-running all bits (through the Settings menu) will make sure they are applied.


====================
Current Config OOI's
====================

The below Config OOI's can be added by going to the ``Network|internet`` object detail page,
clicking "Add" under "Related objects", selecting "Config" in the dropdown menu, and then clicking "Add object".

The ``Type`` and ``ooi`` fields should be automatically filled by default.
In principle, only the ``bit-id`` string field and ``config`` JSON field should be filled in manually.

HSTS
====

You can currently configure the ``max-age`` before HSTS headers will be considered to be too short lived.

.. code-block:: json

    {
        "object_type": "Config",
        "ooi": "Network|internet",
        "bit-id": "check-hsts-header",
        "config": {"max-age": "4153600"}
    }

Aggregate findings
==================

Setting this to ``True`` will aggregate all findings of the same type into one finding,
resulting in cleaner finding reports (both in the web UI and in PDF's). For example, ``KAT-UNCOMMON-OPEN-PORT``
will be aggregated into one finding, instead of one separate finding per port.

.. code-block:: json

    {
        "object_type": "Config",
        "ooi": "Network|internet",
        "bit-id": "port-classification-ip",
        "config": {"aggregate_findings": "True"}
    }
