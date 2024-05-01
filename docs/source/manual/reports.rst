=======
Reports
=======

With the Reports functionality you can create reports with a specific focus.

There are 3 different kinds of reports available. These are:

- **Normal report:** selecting one or more reports will show the contents of each report below each other. These reports can be exported as PDF.
- **Aggregate report:** selecting one or more reports will show aggregation of the data for each selected reports. This means that certain results from boefjes are aggregated together and can be used to get a general overview of the current compliance status of the scanned objects. These reports can be exported as PDF and JSON.
- **Multi report:** allow you to compare an organisation with another organisation based on the organisation tags. This is only possible for aggregate reports.

The table below gives an overview of which 12 reports are available. It also describes which Object is required in the selection process and whether the report is available as normal and/or as aggregate report.

.. list-table:: Report overview table
   :widths: 25 50 25 75
   :header-rows: 1

   * - Report type
     - Description
     - Object
     - Normal or Aggregate report
   * - DNS
     - The DNS report gives an overview of the identified DNS settings for the scanned hostnames. 
     - Hostname
     - Normal
   * - Findings
     - Shows all the finding types and their occurrences.
     - **Any**
     - Normal
   * - IPv6
     - Check whether hostnames point to ipv6 addresses.
     - Hostname
     - Normal + aggregate
   * - Mail
     - System specific mail report that focusses on IP addresses and hostnames.
     - Hostname
     - Normal + aggregate
   * - Name server
     - Name server report checks name servers on basic security standards.
     - Hostname
     - Normal + aggregate
   * - Open ports
     - Find open ports of IP addresses.
     - Hostname
     - Normal + aggregate
   * - RPKI
     - Shows whether the ip is covered by a valid RPKI ROA. For a hostname it shows the ip addresses and whether they are covered by a valid RPKI ROA.
     - Hostname
     - Normal + aggregate
   * - Safe connections
     - Shows whether the IPService contains safe ciphers.
     - Hostname
     - Normal + aggregate
   * - System
     - Combine IP addresses, hostnames and services into systems.
     - Hostname
     - Normal + aggregate
   * - TLS
     - TLS reports assess the security of data encryption and transmission protocols.
     - **IPService**
     - Normal
   * - Vulnerability
     - Vulnerabilities found are grouped for each system.
     - Hostname
     - Normal + aggregate
   * - Web system
     - Web system reports check web systems on basic security standards.
     - Hostname
     - Normal + aggregate



Report contents:
================

The general elements and order of the three different reports are listed below:

- Normal report:
 - Introduction
 - Asset overview (selected objects, reports and plugins)
 - Output of the selected reports are listed as chapters in the following order: 
 - Findings report
 - Vulnerability report
 - Open ports report
 - Web system report
 - Safe connections report
 - System report
 - DNS report
 - Mail report
 - Name server report
 - RPKI report
 - IPv6 report

- Aggregate report
- Multi report: 

The table below gives an overview of the elements that can be found in each report type based on the required plugins:

.. list-table:: Report overview
   :widths: 25 50 25 25
   :header-rows: 1

   * - Report type
     - Normal report
     - Aggregate report
     - Multi report
   * - Standard elements
     - * Introduction 
       * Asset overview (selected objects, reports, plugins)
     - * Summary overview
       * Recommendations
       * Asset overview
       * Appendices (Terms, selected objects, reports, plugins and used config objects)
     - TODO
   * - DNS
     - The table gives an overview of all identified DNS records for the selected hostname. This can help to identify potential misconfigurations for hostnames. The Security Measures table shows which DNS security measures are applied and/or missing. 
     - TODO
     - TODO
   * - Findings
     - Shows an overview table with the number of findings and occurrences per risk level (Critical, high, medium, low, recommendation), followed by a list of all findings. Each finding can be opened to view more details, such as a description of the finding, the possible impact, a general recommendation and the hosts where this finding was identified. 
     - TODO
     - TODO
   * - IPv6
     - Shows if IPv6 was detected on the scanned system.
     - TODO
     - TODO
   * - Mail
     - The table gives an overview of some security configurations that are recommended to be implemented to ensure authenticated e-mails are sent on behalf of the hostname. The compliance checks look at the presence of SPF, DKIM and DMARC, which are used to prevent spammers from sending unwanted e-mails.. Each check will show whether or not the system is compliant with this security configuration. If a lack of compliance is identified, the table below will show what compliance issue was identified with what risk.
     - TODO
     - TODO
   * - Name server
     - The table gives an overview of the recommended security configurations to ensure an increased level of security for the domain name servers for the scanned domain. The compliance checks look at the presence and configuration of DNSSEC, and the open ports that are enabled. Each check will show whether or not the system is compliant with this security configuration. If a lack of compliance is identified, the table below will show what compliance issue was identified with what risk. **This requires that the hostnames of the name servers are selected!**
     - TODO
     - TODO
   * - Open ports
     - Shows for the identified IP addresses which ports were found to be open and thus reachable. If available the table will show the IPv4 and/or IPv6 addresses, the hostname(s) and all open ports identified on both IPv4 and IPv6 (if available). Please note that you have to manually enable IPv6 support in Dockerized environments. See the docs on how to do this.
     - TODO
     - TODO
   * - RPKI
     - The table gives an overview of the RPKI status for the selected domain. It currently shows if RPKI is available and if the data is not expired.
     - TODO
     - TODO
   * - Safe connections
     - The table gives an overview of some security configurations that are recommended to be implemented to ensure safe connections (encryption). The compliance checks look at the TLS protocols and TLS Ciphers offered by the system. Each check will show whether or not the system is compliant with this security configuration. If a lack of compliance is identified, the table below will show what compliance issue was identified with what risk.
     - TODO
     - TODO
   * - Systems
     - The table gives an overview of which system types were identified on the system. This is performed based on the identified open ports, which can have one or more of the following labels: DICOM, DNS, Mail, Web, Other.
     - TODO
     - TODO
   * - TLS
     - The table shows which TLS protocol versions and TLS ciphers were identified on the system, including the status of the identified data. This means that if outdated protocols (such as SSL3) are identified, the table will show a recommendation such as ‘Phase out’.
     - TODO
     - TODO
   * - Vulnerability
     - TODO
     - TODO
     - TODO
   * - Web system
     - The table gives an overview of some basic security configurations that are recommended to be implemented. These checks are performed against the scanned systems/hosts.  Each check will show whether or not the system is compliant with this security configuration. If a lack of compliance is identified, the table below will show what compliance issue was identified with what risk.
     - TODO
     - TODO

Report flow
===========

** TODO!! When you click on the Reports tab, you will see the report generation flow. In this flow you first have to decide if you want a normal, aggregate or multi report. After that you will see ….. <TODO Continue>**

Plugins
=======
Each report has both required and suggested plugins that are to show data in the report. These plugins are shown in the report flow. You can still generate reports if not all required plugins are enabled, however a warning a message is shown and the generated report will show that not all required plugins were enabled at the time of generation.


Downloading and/or exporting a report
=====================================
The normal and multi report can be downloaded as PDF file. The aggregate report can be exported as a PDF and also as a JSON file. In order to do this either click the 'Download' or 'Export' button on the right. The JSON output is required in order to create a Multi-Report and compare organisation sectors against each other.



Generating a Multi Report
=========================
With the Multi report you can compare organisations against each other, for example if both organisations are similar health care institutions.
Create two organisations and make sure both organisations have data. For this tutorial they are named `CAT` and `DOG`.

#. Generate an ‘Aggregate Report’ and export this to JSON format.

#. Create a third organisation called ‘BIRD’.

#. In BIRD, go to Objects > Add > ‘Upload raw file’.

#. Upload both raw files (from CAT and DOG) using the mime-type openkat/report-data’.

#. Click on ‘Reports’ and click on ‘Multi Report’.

#. Select the report data of the organisations CAT and DOG and follow the report flow steps to generate the report.



Troubleshooting
===============

When you do not see one (or more) of the reports options, please check the following things:

- Do you have the required object selected? (This is either the Hostname or IPService for all reports, except the findings report.)
- Does your selected object have sufficient clearance? Generally L2 or higher is required.
