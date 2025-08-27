Glossary
========

In this glossary you will find the most commonly used terms in OpenKAT with it's definition.


.. list-table:: Glossary
   :widths: 15 85
   :header-rows: 1

   * - Term
     - Definition
   * - Object/OOI
     - The information collected by OpenKAT is stored as objects.
       Objects can be anything, like DNS records, hostnames, URLs, IP addresses, software, software versions, ports, etc.
   * - Object type
     - The type of object, for example IP address, URL, website.
   * - Finding
     - Information about the system found by OpenKAT.
   * - Finding type
     - The type of information that has been found by OpenKAT.
   * - Plugin
     - Deployed by OpenKAT to collect information, translate it into objects for the data model and then analyze it.
   * - Boefje
     - A type of plugin, which gathers facts from the objects.
   * - Task
     - A task is created for each job that needs to be performed, such as running a plugin or for generating a report.
       Not every task results in findings, but almost every task results in new objects.
   * - Clearance type
     - The clearance type tells how the object was added to the Objects list.
       **Declared** objects were added by the user.
       **Inherited** objects were identified through propagation and the parsing of bits and normalizers. This means there is a relation to other object(s).
       **Empty** objects do not have a relation to other objects.
   * - Clearance level
     - The clearance level of an object tells OpenKAT how far it can go with scanning the object.
   * - Scan level
     - The scan level of a plugin tells you how deeply this plugin can scan your object. OpenKAT always checks if the plugins do not exceed the clearance level of the objects.
   * - Separate report
     - Reports that are created for separate assets. This function might be turned off by default by your administrator.
   * - Aggregate report
     - Report that aggregate findings from different assets into one report.
   * - Multi report
     - This report combine aggregate reports from different organizations into one report.
