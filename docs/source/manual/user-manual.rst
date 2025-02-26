==========
User Guide
==========

This manual covers the day-to-day use of OpenKAT via the web interface. The concepts behind OpenKAT are explained in the "How does OpenKAT work" section. When using OpenKAT for the first time, the onboarding flow is available, see the section in this chapter.

Web interface
=============

The web interface of OpenKAT consists of the screens, which provide access to the information and main functions of the system:

- Crisis Room (overview page)
- KAT-alog (catalog)
- Findings
- Reports
- Objects
- Tasks
- Members
- Settings

Crisis Room
-----------

The Crisis Room gives an overview of findings for, which can be viewed for different moments in time. The date can be selected and the crisis room will provide an overview for that moment in time. Crisis rooms are available for:

- all organizations (the user has access to)
- each single organization (the user has access to)

The crisis room for all organizations shows which organizations you have access to and how many findings per severity are found. The screenshot below shows that there is one organization called Purr.

.. image:: img/crisisroom.png
  :alt: Crisisroom for all organizations

The crisis room for a single organization.

.. image:: img/crisisroom-organization.png
  :alt: Crisisroom single organization


KAT-alog
-----------

The KAT catalog is the place where you can see which tools are available, enabled and/or disabled. Tools can be common security scanning tools, like nmap (checks which ports are open), or specific tools that check for a CVE vulnerability. The KAT catalog also contains all the normalizers, which parse the data from the tools. Each boefje and normalizer contains more information on how it works and what is required, including the objects it can search for, and which are required for the boefje to work.

Before a boefje or normalizer can run the following two conditions must be met:
- The boefje and corresponding normalizer are enabled. Note: all normalizers are enabled by default.
- The clearance level of your object (e.g. hostname or URL) is similar or higher than the required scan level of the enabled boefje.

New boefjes can be added by an administrator in the web interface, or by manually adding an external KAT catalog in the Rocky's config ile.

.. image:: img/katalogus.png
  :alt: KAT catalog

Each boefje has an details page with information about the tool, the scan level and additional settings that can be given to the boefje. It also gives an overview on the required objects before the boefje can run ("Consumes") and which output objects are created ("Produces"). The details page also gives an overview of all associated tasks and which objects match the clearance level.

.. image:: img/boefjeinfopage.png
  :alt: Boefje information page

Findings
--------

The findings page gives an overview of all findings found by KAT. The filter section can be used to apply various filters to show specific findings (e.g. critical findings only) and/or hosts. The search bar can be used to search for specific findings or hosts. Clicking on a finding shows more information on this finding. Each finding can be viewed in the tree or graph by clicking the corresponding icons behind the finding.

A finding is also an object in the data model. This simply means that the finding can also be found on the Objects page.

.. image:: img/findings.png
  :alt: Findings

Muted findings
--------------
Findings can be muted until a specific date. This will prevent the finding(s) from showing up in the default view. Using the filters you can show all muted findings, or both muted and non-muted findings.

One or more findings can be selected. The textbox at the bottom allows for a description as to why this finding is muted (e.g. for audit purposes, or for review at a later point in time). Below the textbox the expiry date for the selected findings can be provided. Click the button 'Mute Findings' to mute the selected findings.

.. image:: img/mutedfindings.png
  :alt: Mute findings


Objects
-------

The Objects page lists all the objects in Octopoes. Objects can be anything, like DNS records, hostnames, URLs, software, software versions, ports, etc. It is any piece of information that is found by the normalizers, bits and boefjes. On a new installation you'll see the following objects by default:

.. image:: img/objects-clean-install.png
  :alt: overview of default objects

The table gives an overview on the following items:
- Object: this is the piece of data that was identified, such as a port, software version, hostname, etc.
- Object type: this shows how this object is labelled.
- Clearance level: this shows the clearance level of this object.
- Clearance type: this shows what kind of clearance level is set on the object. See `Object clearances` __ below for more information.

The objects can be filtered by object types, clearance levels and clearance types. The search functionality can also be used to search for specific objects, such as hostnames.

More information on objects is provided by clicking on the object. This will give an overview page with all information for the specific object. The object details page is further described below.


Object clearances
-----------------
Each object has a clearance type. The clearance type tells how the object was added to the Objects list. The following object types are available:

- Declared: declared objects were added by the user.
- Inherited: inherited objects were identified through propagation and the parsing of bits and normalizers. This means there is a relation to other object(s).
- Empty: empyth objects do not have a relation to other objects.

The objects below show different clearance types for various objects. The hostname `mispo.es` was manually added and thus is `declared`. The DNS zone is `inherited` based on the DNS zone boefje.

.. image:: img/objects-clearance-types.png
  :alt: different object clearance types

Object details
--------------
Object details can be found by clicking on an object on the Objects page. Object details provide data on that specific object and how it relates to other objects. The following detail tabs are available:

- Overview: the overview tab gives object details, it's declaration, related objects (objects that are somehow related), tasks that ran on this object, findings that are applicable to this object and a list of boefjes that can scan this object.
- Tree: the tree tab shows how all objects are related to this object. The point of view will be from the specific object. Thus the view for a hostname will be slightly different than the tree view for an IP address. Filters can be applied to the tree view.
- Graph: the graph tab visually shows how the objects are connected using lines. The graph is interactive, meaning you can click on objects in the graph. Filters can be applied to the graph view.
- Clearance level: the clearance level can be changed on the clearance level tab. This tab also shows the clearance type (declared, inherited, empty) and the inheritance tree for the object.
- Findings: the findings tab shows all findings that are linked to this object. Different objects have different findings, meaning that the Findings tab for a hostname is likely different from the findings tab for an IP address.


.. image:: img/object-details.png
  :alt: object detail page

Tasks
-----

All tasks can be found on the Tasks page. A task is created for each job that needs to be performed, such as running a boefje, normalizer or for generating a report. Each task is performed on an object (such as a hostname, finding, DNS records, etc.) and tasks have a status to show if the task is completed, scheduled, queued, etc. Each task contains meta and raw data that can be downloaded. This is the output, error message, proof, security hashes, etc. that belongs to the boefje or normalizer. Tasks can also be rescheduled and filtered to find specific tasks.

Tasks are organised between the boefje and normalizer tabs. The image below shows what the boefje tab could look like.

.. image:: img/tasks-boefjes.png
  :alt: overview of boefje tasks

The image below shows the normalizer tasks by clicking on the normalizer tab.

.. image:: img/tasks-normalizers.png
  :alt: overview of normalizer tasks

The normalizer tab has a special functionality called 'yielded objects'. If the normalizer was able to extract new data (points) this will result in new yielded objects. As an example below, the DNS records for the hostname `mispo.es` are parsed. The normalizer identifies various DNS records (A, NS, MX, SOA) and other information and creates objects for each of the identified information. This information is now also available to other tools to be parsed, if possible.

.. image:: img/tasks-normalizer-yielded-objects.png
  :alt: yielded objects for normalizers

Members
-------

The Members page allows for user management and is visible to users who have the rights to do this. When you have sufficient rights you can add new users either manually or through a file upload (CSV). This page also shows the accepted and assigned clearance levels to each user and whether or not the user is active.

.. image:: img/members.png
  :alt: Members page

Settings
--------

The Settings page shows general information and its settings. In some cases you might want to add tags to the organisation or decide to manually run all bits. This can be done from the settings page. If you created a new organization, you can also add the indemnification on this page.

* Organization data
* Indemnification
* Rerun all bits on the current dataset
* Tags

.. image:: img/settings.png
  :alt: Settings page


Users and organizations
=======================

OpenKAT has a superuser, several usertypes and organizations.

Organizations
-------------

Organizations own the systems for which KAT is deployed. From KAT, multiple organizations can be monitored simultaneously, each with its own settings. The superuser can add new organizations and each organization has its own users.

Users
-----

OpenKAT knows four types of users: the client, the red team user, the admin and the superuser. In OpenKAT, permissions utilise a stacked model. This means that a higher permission level includes all lower permissions of the lower levels. The client is a 'read only' type of user, the red teamer is a researcher who can start scans. The admin is an administrative user who can do user management etc, the superuser has the ability to do everything.

Rights and functions per user type
----------------------------------

+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Action                                                                                              | USER | RED TEAM | ADMIN | SUPERUSER |
+=====================================================================================================+======+==========+=======+===========+
| Login                                                                                               | x    | x        | x     | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can start scans on objects with enough clearance                                                    | x    | x        | x     | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can view reports                                                                                    | x    | x        | x     | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can start scans on objects with not enough clearance, but the user has enough clearance             |      | x        | x     | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can edit settings of scan tools                                                                     |      | x        | x     | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can enable/disable scan tools                                                                       |      | x        | x     | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can add objects                                                                                     |      | x        | x     | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can give clearance to objects up to it’s own clearance level                                        |      | x        | x     | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can give clearance to users                                                                         |      |          | x     | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can manage organisation members                                                                     |      |          | x     | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can create new account(s) in OpenKAT                                                                |      |          | x     | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can create new and add, or add existing accounts, to the organisation                               |      |          | x     | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can view users of an organisation                                                                   |      |          | x     | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can edit users of an organisation                                                                   |      |          | x     | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can view organisation details                                                                       |      |          | x     | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can edit organisation details and settings                                                          |      |          | x     | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can add organisations                                                                               |      |          |       | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can start scans on objects regardless of clearance                                                  |      |          |       | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+
| Can access Django admin                                                                             |      |          |       | x         |
+-----------------------------------------------------------------------------------------------------+------+----------+-------+-----------+


User management
---------------

Users and organizations can be created in the on boarding flow, in the Web interface or automated. The administrator of the system can create organizations and do user management. The administrator of an organization in turn can create users within the organization. The django interface provides additional capabilities for user management via the command line, for use in an automated deployment and linkage to external user management.

Adding users through a CSV file
-------------------------------

Adding multiple users at a time to OpenKAT can be done using a CSV file. To make this work SMTP should be configured.

How does it work?
*****************

Select the organization to which the new users will be added. On the members page click the Add member(s) menu and select Upload a CSV. This takes you to the CSV upload page.

.. image:: img/csvupload.png
  :alt: CSV upload page

Download the template file, fill in the data of the users you want to add and upload them into the system. The new users will be added to the organization of your choice.

.. image:: img/csvformat.png
  :alt: CSV format

How should I prepare the CSV file?
**********************************

CSV files are great when they work. Edit the downloaded template file and use a plain texteditor to make sure your CSV file contains exactly what is needed for its purpose.

Each user will have its on line in the CSV file. The template has five columns: full_name, email, account_type, trusted_clearance_level, acknowledged_clearance_level.

*User details:*

A user is recognized by their full name and email address.

* full_name : the full name of the user
* email : a working emailadress of the user

*User type:*

Through the CSV upload you can add the usertypes client, admin and redteam. Read about users and roles in the :ref:`manual/user-manual:Users` section.

* account_type : client, admin or redteam

*User clearance:*

Clearance levels are related to the scan level of the Boefjes a user is able to dispatch. Read about this in the :ref:`manual/user-manual:Scan levels, clearance & indemnities` section.

The trusted_clearance_level is the level a user receives from the organization. It is the maximum level available for this user, based on the decision of the admin or superuser. The acknowledged_clearance_level is the level accepted by the user. Both can be added in the CSV file. The accepted level can be changed by the user.

* trusted_clearance_level : between -1 and 4
* accepted_clearance_level : between -1 and 4

The ability to add the accepted clearance level allows you to copy users from one organization to another, which might be needed on larger installs. The user should have accepted this level at some point, in- or outside OpenKAT.

*Warnings*

If the CSV file contains data that cannot be parsed OpenKAT will give a warning with the data concerned.

User notification
*****************

After the CSV file has been uploaded the users receive a welcome email on their account. The link in this email allows them to create a password for their account. If SMTP is not configured on your install, this will not work.

::

 Content-Type: text/plain; charset="utf-8"
 MIME-Version: 1.0
 Content-Transfer-Encoding: 7bit
 Subject: Verify OpenKAT account on localhost:8000
 From:
 To: a@bbbb.dl
 Date: Thu, 20 Jul 2023 13:34:32 -0000
 Message-ID: <168986007241.76.14464090403674779824@af745d470510>

 Welcome to OpenKAT. You're receiving this email because you have been added to organization "test" at localhost:8000.
 Please go to the following page and choose a new password:

  http://localhost:8000/en/reset/MTY/brn1pk-914a9d550dbb2a5b0269c85f6b667e21/

 Sincerely,
 The OpenKAT team


API token authentication
------------------------

Authentication tokens can be created in the admin interface (/admin). The token is created for an user account and will have the same permissions as the user. After creating a token it will display the newly created token once. You need to copy the token immediately, because the token are stored hashed in the database and won't be visible anymore.

The token can be used by adding the Authorization header with the token to the request:

::

    Authorization: Token f2505ed4d2a51624fe1691c977789ce00dc9886d48271c6c91a25e7dd258c932

For example this will use the token to get the list of organizations:

.. code-block:: sh

    curl -H 'Authorization: Token f2505ed4d2a51624fe1691c977789ce00dc9886d48271c6c91a25e7dd258c932' http://127.0.0.1:8000/api/v1/organization/


Working with objects
====================

Adding an initial object with an appropriate safeguard puts OpenKAT to work. This can be done in on-boarding, but objects can also be added individually or as CSV files. Objects are also referred to as 'objects of interest' or OOI. The object itself contains the actual data: an objecttype describes the object and its logical relations to other objecttypes.

Properties
----------

Objects can be viewed via the 'Objects' page in OpenKAT's main menu. Here are the already created objects with the type and safeguard level for each object. Objects can be added, scanned, filtered and there is an export option.

New objects can be created via the 'add' option. This can be done individually or per CSV. The specification of the CSV is included on the page where it can be provided.

Start scan
----------

Based on the object and the clearance, OpenKAT provides an overview of available boefjes. All users can perform a manual scan appropriate to the given safeguard level. The manual scan is accelerated by the scheduler. The results appear as findings with the object.

View Findings
-------------

Findings appear on the general findings page, but can also be viewed by object.


Scan levels, clearance & indemnities
====================================

Boefjes can collect information with varying intensity. OpenKAT has a system of safeguards to control permission to perform scans and prevent damage to the systems under test.

* Boefjes have a scan level
* Objects have clearance
* Users can receive and accept the ability to give clearance to an object and to start a scan

For each object, the 'clearance level' menu indicates how deeply scanning is allowed. Here the user agrees to the risks of the scans and gives permission to store the information gathered on these systems.

The levels used range from level 0 to level 4, from 'do not scan' to 'very intrusive'. Scanning levels are distributed in the data model, either by inheritance or by user statements. The different levels are qualitative in nature. L1 'do not touch' is obvious, but the difference between L2 'normal user' and L3 'detectable scanning' is at the discretion of the developer and administrator. The use of NMAP, for example, falls in between and depends heavily on the arguments the tool brings.

.. list-table:: Scan levels
   :widths: 25 50
   :header-rows: 1

   * - Level
     - Description
   * - L0
     - do not scan
   * - L1
     - do not touch
   * - L2
     - normal user
   * - L3
     - detectable scan
   * - L4
     - intensive scan


Indemification by user
----------------------

The user's statement counts as an indemnification for scanning a particular object. This obtains permission to scan and store the information. The statement is given at the start of a new scan or specifically for certain objects.

Inheritance
-----------

Objects are linked to other objects in the data model. Underlying objects receive the same safeguard level, parent objects a lower level. For example, a hostname has an ip address for which the same safeguard level applies, but it also has a DNS server that may be outside the organization's domain and receives a lower level.

Extended profiles
-----------------

L0: Do not scan
***************

The user can explicitly indicate that certain systems should not be scanned. For example, because he is not the owner of these.

L1: Do not touch
****************

OpenSource and passive data collection. For this profile, objects are viewed through various freely available data and sources via the Internet. These can be sources that do not have explicit permission (e.g. LinkedIn, DNS, leaked password databases). The goal here is to detect public information that could be a risk to the client: information that could be misused by an attacker in a targeted attack.

Examples of sources/tools used:

- Shodan (via API)
- HaveIbeenPnwed
- DNS

L2: Touching at the normal user level
*************************************

Targeted scans, limited intrusive. Scan will be dosed and skip known sensitive scans. The scanned target usually continues to function without problems.

Example of scanning tools useful for this purpose:

- Nmap
- Nikto
- Burp passive scanner

L3: Detectable scan
*******************

This scan will be more intrusive: connect to services to find out versions, try to log in with commonly used (default) login credentials, automated testing of found vulnerabilities whether they are vulnerable, more intensive guessing of urls and more intensive crawling of web pages.

A greater number of scans will be performed, resulting in a spike in data traffic. The infrastructure may not be designed for this.

Example of useful scanning tools and methods:

- Nessus, Nexpose, Acunetix
- Burp Intruder, active scanner

L4: Intensive scan
******************

The premise of the test profile is to verify whether an attacker can exploit vulnerabilities to give himself more extensive access to the tested environment. Thus, known exploit code is applied in this level.

Bits
====

Bits are businessrules that assess objects. These can be disabled or enabled using environment variables. The parameters of a Bit can be configured using config objects, which are explained in detail in :ref:`introduction/make-your-own:Bits: businessrules`.

Almost all bits are enabled by default and be disabled by adding the bit to `BITS_DISABLED`. The disabled bits can be enabled using `BITS_ENABLED`. For example:

.. code-block:: sh

    BITS_ENABLED='["bit1","bit2"]'
    BITS_DISABLED='["bit3"]'


Note that if you enable a bit that was previously enabled the bit won't be automatically run for every object it should have run on, but only when it is triggered again after a new scan or other bit that has run. When a bit that was previously enabled is disabled the resulting objects from that bit will also not be automatically removed. Only when the bit triggers instead of running the bit the resulting OOIs of the previous run will be deleted. This also means that if the bit isn't triggered the old objects will not be removed.

Reports
=======

OpenKAT displays all findings in the crisis room, the entry point for all current information from the system. In addition, OpenKAT can create thematic reports and display findings per object. The reports are available in the front end and as PDF, based on a LaTeX parser. The organization's house style can also be incorporated. It is also possible to link to other reporting and alerting systems.

.. image:: img/report.png
  :alt: Report

My first scan
=============

If you are using OpenKAT for the first time you can use the on-boarding flow. The on-boarding flow helps you through the full cycle of OpenKAT. After following this flow, you will have a functioning OpenKAT installation running a first set of scans. By adding more objects, releasing and selecting boefjes, you can find out more information and perform analysis.

The on-boarding flow uses the following steps to get you going:

- Create admin account with 2FA

The administrator account in the front end uses a login, password and two-factor authentication with one-time passwords. The code for creating the one time passwords is available as a string and as a QR code.

- Organization creation

The organization is the entity that "owns" the systems to be scanned and on whose behalf the user can provide an indemnification. From an OpenKAT installation, multiple organizations can be scanned, each with its own settings and its own objects. Organizations can be created automatically from release 1.5 on the basis of an API, which is relevant for larger systems.

- User creation

Users in OpenKAT are the red team and the read-only user.

- Choosing a report ("what question do you ask OpenKAT?")

OpenKAT starts with a question, for example about the situation around the DNS configuration of a particular domain. For this, choose the relevant report.

- Creating an object ('what should OpenKAT look at first?')

Add the objects that OpenKAT can take as a starting point for the scan, for example a hostname.

- Specify clearance level ('how intensive should OpenKAT search?')

Specify the intensity of the scan: how intensely may OpenKAT scan? The heavier, the greater the impact on the system being scanned.

- Select boefjes and have OpenKAT scan them

Based on the report, object and safeguard, select the relevant boefjes for your first scan and run the scan.

- View results: in the web interface or as a PDF report

The scan is an ongoing process, looking for information based on derivation and logical connections in the data model. The results of the scan appear over time, any findings can be viewed by object, at Findings and in the Crisis Room. In each context, reports can also be generated.


Questions & Configs
===================
OpenKAT can be used to customise OpenKAT to your own company policies and industry standards. This will allow you to set your security more or less strict depending on your needs and wishes. This can be done using the Question objects on the Objects page. By default no policies are applied. In order to set an policy you have to answer the policy questions and apply these. After applying the questions a Config is created which contains all the answers to your Questions. OpenKAT reads the applied Config files and ensures that all observations are measured against your applied policy.

To summarize: your personal policy is stored in Configs. In order to create a Config you have to answer the Questions. After answering all questions the Config is automatically generated and applied. Questions consist of a JSON schema, which is rendered as a form in the web interface.

Currently the following pre-defined policies are available:

- Disallowed hostnames in the CSP header
- Objects in the HTTP headers
- Port classification


Disallowed CSP hostnames
------------------------

**Why is this question introduced?**
Websites often load scripts and content from external servers (e.g. jQuery from a Content Delivery Network (CDN) like Cloudflare). This can be dangerous as you have limited control over the content that is inside the scripts that these external servers are serving. This Question allows you to check if the hostname in the CSP is allowed by your policy.

**What are the risks?**
Loading external content from websites you do not have control over could result in supply chain attacks. Attackers could serve malicious code (scripts) on CDN networks that is then automatically loaded into the browser of each website visitor.

**Limitations**
This question looks only for bad hostnames that are provided by the user (denylist). This means that findings for bad hostnames in the CSP header are only shown for those domains that are added to the list.

**Examples**
Provide hostnames which are unwanted, separate each hostname by a comma. You can specify the main domain (`bad.com`), subdomains are automatically taken into account (`script.bad.com`).

.. code-block:: RST

   E.g. evil.com, bad.evil.com, attacker.com.

OOIs in headers
---------------

**Why is this question introduced?**
Some websites like SSO portals result in new objects on the Objects page for each time a boefje visited the website with a new session token. By specifying which session parameters are used the number of objects will be limited to only the paths on the server.

**What are the risks?**
There is no direct impact. This question helps reduce the number of duplicate items in the Objects list and thus helps in getting a better overview.

**Limitations**
It only checks for parameters in the URL, headers are ignored. There is currently no way to specify the parameters per hostname.

**Examples**
Provide the URL parameter that is to be ignored, separate each parameter by a comma. URL parameters can be found in the URL bar after the `?` sign. They are the values after the `&` and before the `=` signs.

The URL is: `https://example.com/index.php?session_id=12346&search=meow <dontredirect>`_ . This URL has two parameters:`session_id` and `search`, which both have a value (`123456` and `meow`). The parameter and value for `session_id=123456` are expected to clutter the Objects list, as for each new session the value `123456` is different. The next time you visit the website this might be `session_id=43215` and the next time `session_id=958367`. You can reduce the object clutter by adding the parameter `session_id` to the list as this will be the same for each session. Adding the value `123456` will not work, as this will be different each time.



Port mapping
------------

**Why is this question introduced?**
Maps open ports into specific categories based on the services in your environment. You can specify common TCP and UDP ports which will not trigger a finding (such as e-mail server ports). By adding ports to the database (db) and system administrator (sa) lists you tell OpenKAT which ports are likely used in your network. Depending on your port mapping OpenKAT will show different findings if the port is detected. The `aggregate_findings` functionality allows you to group findings by IP address rather than treating them as separate ports.

**What are the risks?**
There is no direct impact. This question helps to tune findings to your own demands. Having good insights in your network helps with risk mitigation.

**Limitations**
If a port is added to multiple lists the finding for the first list is shown. If a port is added to both sa_tcp_ports and db_tcp_ports, then the finding relating to the system administrator ports is shown, as this is the first in the list.

**Examples**
Enter ports separated by a comma. Such as: 21,22,3389.

.. image:: img/question-port-mapping.png
  :alt: Port mapping order

Trusted timestamps in OpenKAT
=============================

OpenKAT can use a trusted timestamp provider for the raw data in Bytes. This timestamp provider needs to conform to rfc3161. It can be set in the `Bytes .env file <https://github.com/minvws/nl-kat-coordination/blob/main/bytes/.env-dist>`_.

About the protocol
------------------

The RFC3161 timestamp protocol is a simple and effective way to add a timestamp to data. The data concerned is hashed to provide an identifier. The hash is uploaded and timestamped by the server. As long as you trust the server, you can prove the data existed at the point in time indicated by the server.

Wikipedia has a nice explanation of the protocol, including lovely images:

`https://en.wikipedia.org/wiki/Trusted_timestamping <https://en.wikipedia.org/wiki/Trusted_timestamping>`_

The `RFC 3161 itself is human readable as well <https://www.ietf.org/rfc/rfc3161.txt>`_

Available timestamp servers
---------------------------

The .env file in Bytes specifies a time stamp server. The default specification is empty in order to prevent you from querying an external server without prior knowledge. OpenKAT will sign the data itself but for proper timestamping an external server is required. `Find a list of public servers here <https://github.com/trbs/rfc3161ng>`_.

Add the timestamp server address and the certificate to the .env file in Bytes and restart OpenKAT. It will automatically use the specified server for all new data.

How to verify a timestamp?
--------------------------

The verification process involves the raw data, the hash from it and the timestamp that was set using this hash. Using the following steps we can verify the data:

* download the raw data
* verify the hash
* check the timestamp

Download the raw data
*********************

The raw data of your object can be found in the object page or task that created it. Download the zip file, open it and locate the raw_meta json. Inside are the hash of the data and the retrieval link for the timestamp. In this document we will check an object timestamped with the freetsa.org server, so parts of this example might be different depending on the service you have configured.

* Raw data filename (example): ``[example file name]``
* JSON filename (example): ``raw_meta_[example file name].json``

Verify the hash
***************

Check the hash of the file using the timestamp::

  #!/bin/bash

  timestamp=$(jq -r ".boefje_meta.ended_at" raw_meta_[example file name].json | python3 -c "import datetime, sys; print(datetime.datetime.fromisoformat(sys.stdin.readline().strip()).timestamp())")

  cat [example file name] <(echo $timestamp) | tr -d '\n' | shasum -a 512

The result of this should deliver a hash exactly similar to the one in the JSON.

Verify the timestamp
********************

Check the timestamp using openssl tools. Add the hash and retrieval link to small files and compare them to the certs from the timestamp service::

  #!/bin/bash

  jq -r ".secure_hash" raw_meta_[example file name].json | tr -d '\n' > data_file
  jq -r ".hash_retrieval_link" raw_meta_[example file name].json | base64 -d > time_stamp_token
  wget https://freetsa.org/files/tsa.crt
  wget https://freetsa.org/files/cacert.pem

  openssl ts -verify -in time_stamp_token -token_in -data data_file -CAfile cacert.pem -untrusted tsa.crt``

The output of these commands is quite verbose, which makes it possible to follow the steps. If everything is correct and the data has not been changed, you will receive a ``Verification: OK`` as result, confirming the data is correct.

Automation of the verification process
**************************************

OpenKAT has been created to automate tedious tasks such as this one. We like to include an automated verification process for objects that includes the entire chain of information, with nice green checkmarks. It is on the roadmap, if you want to contribute to it you are most welcome! Get in touch through meedoen@openkat.nl.
