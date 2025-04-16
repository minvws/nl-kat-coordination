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
- ooi_types =  ``["IPAddressV6", "Hostname", "IPAddressV4", "URL"]``
- scan_level = ``[1, 2, 3, 4]``
- scan_type = ``["declared"]``
- report_types = ``["systems-report", "findings-report"]``
- cron_expression = ``0 * * * *`` (every hour)

It is possible to update the report recipe*. To do this:

- Go to "Reports"- Click on the tab "Scheduled"
- Look for the "Criris Room Aggregate Report"
- Open the row
- Click on "Edit report recipe"

*\*Note: if you want to update the report recipe, you have to do this for every organization.*

Create a Findings Dashboard for Your Organization
=================================================

OpenKAT automates the process of creating findings dashboards for your organization.

Steps to Create a Findings Dashboard in Development:
----------------------------------------------------

1. **Install OpenKAT or Add a New Organization:**
   Ensure that you have OpenKAT installed or a new organization has been added to your setup.

2. **Navigate to Your OpenKAT Installation Directory:**
   Open a terminal and change to the OpenKAT installation folder:

   .. code-block:: bash

      cd nl-kat-coordination

3. **Go to the 'rocky' Folder:**
   Within the OpenKAT directory, enter the ``rocky`` folder:

   .. code-block:: bash

      cd rocky

4. **Run the Dashboard Creation Command:**
   Execute the following command to create the findings dashboard:

   .. code-block:: bash

      make dashboards

Steps to Create a Findings Dashboard in Production:
---------------------------------------------------
1. **Run Django Migrations:**
   Run Django migrations for crisis_room app:

   .. code-block:: bash

      python manage.py makemigrations
      python manage.py migrate

2. **Re-run Django migrations:**
   If something happens and later you still want to run the migration script do:

   .. code-block:: bash

      python manage.py dashboards

What Happens After Running the Command or migrations:
-----------------------------------------------------

- The system will automatically search for all installed organizations.
- A **recipe** for the findings dashboard will be generated.
- A **scheduled task** will be created to generate findings reports every hour.
- Findings will be **added to the organization’s crisis room** for easy access and monitoring.
