===========
Crisis Room
===========

In OpenKAT we differentiate two Crisis Rooms:

- **Single Organization Crisis Room:** a Crisis Room for each organization separately
- **General Crisis Room:** one general Crisis Room with for all organizations


Single Organization Crisis Room
===============================

This page shows a Crisis Room for each organization separately.
Currently, this Crisis Room shows the top 10 most severe Findings.
In the future it will serve as a dashboard which can be customized by the user.


General Crisis Room
===================

This page shows the Crisis Room for all organizations.
Currently, this Crisis Room only shows the Findings, but in the future it will also show dashboards,
which can be customized by the user.

Findings
--------
This section shows all the findings that have been identified for all organizations.
These findings are shown in a table, grouped by organization and finding types.

Every organization has one default report recipe. This recipe is used to create an Aggregate Findings Report.
The output of this report, for each organization, is shown in this section.

The default settings for this report recipe are:

- report_name_format = ``Crisis Room Aggregate Report``
- ooi_types =  ``["IPAddressV6", "Hostname", "IPAddressV4"]``
- scan_level = ``[1, 2, 3]``
- scan_type = ``["declared"]``
- report_types = ``["systems-report", "findings-report"]``
- cron_expression = ``0 * * * *`` (every hour)

It is possible to update the report recipe*. To do this:

- Go to "Reports"
- Click on the tab "Scheduled"
- Look for the "Criris Room Aggregate Report"
- Open the row
- Click on "Edit report recipe"

*\*Note: if you want to update the report recipe, you have to do this for every organization.*
