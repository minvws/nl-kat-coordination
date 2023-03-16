================
What is OpenKAT?
================

OpenKAT aims to monitor, record and analyze the status of information systems. The basic premise is that many of the major security incidents are caused by small errors and known vulnerabilities, and that if you can find them in time your systems and infrastructure become a lot more secure.

OpenKAT scans, collects, analyzes and reports in an ongoing process:

.. image:: docs/source/introduction/img/flowopenkat.png
  :alt: flow of OpenKAT

OpenKAT scans networks, finds vulnerabilities and creates accessible reports. It integrates the most widely used network tools and scanning software into a modular framework, accesses external databases such as shodan, and combines the information from all these sources into clear reports. It also includes lots of cat hair.

OpenKAT is useful if you want to monitor a complex system and want to know whether it contains known vulnerabilities or configuration errors. Due to its modular structure and extensibility, OpenKAT can be applied in a multitude of situations. You can customize it and put it to your own use.

Documentation
=============

Brochures
*********

The high level documentation on OpenKAT explains the purpose and operation of OpenKAT at the management level:

- `the 'TL;DR' of 2 pages (English) <https://github.com/minvws/nl-kat-coordination/blob/main/docs/source/introduction/pdf/OpenKAT%20handout_ENG.pdf>`_
- `the extensive brochure on OpenKAT (Dutch) <https://github.com/minvws/nl-kat-coordination/blob/main/docs/source/introduction/pdf/introductie%20OpenKAT%20V20220621.pdf>`_

Technical documentation
***********************

`The full documentation of OpenKAT can be found here <https://docs.openkat.nl>`_. It includes information such as:

- Introduction to the system
- Modules
- Guidelines
- Templates
- Technical documentation

Principles behind OpenKAT
=========================

The Ministry of Health, Welfare and Sport built the "Vulnerability Analysis Tool" to monitor systems during the pandemic. OpenKAT was built by the ministry's own programmers. Because of the scale and dynamics of the campaign, monitoring had to be automated, flexible and traceable. The structure of the system gives an indication of the possibilities:

Framework
*********

OpenKAT is a framework that can be used for information collection, storage and processing. It is so flexible that "the pieces almost fall out": just about everything that can be separated is. Thus, it can respond to new developments and new functions can be included.

Plugins for information collection
**********************************

The 'Boefjes' retrieve information: they are plugins ranging from a small script or scraper to an external tool running in its own container. If there is a new issue that is not yet covered, create a boefje for it that retrieves the information.

Forensic assurance
******************

The raw data is stored with a hash and an external timestamp. This allows retrieval of what information was stored at what time. Are there new vulnerabilities coming out for a particular software version? Then it is already known in the system and no separate scanning is required.

Data model
**********

In order to process all inputs, data is converted into objects, which fit into a predetermined data model. For example, an IP address is an object, which can be found through various routes and has logical relationships with other objects. The data model can be extended to include all sorts of objects with logical relations.

Automatic scanning
******************

The package itself searches for information, based on the logical relationships in the data model. The results of the scans in turn lead to new actions, just as the passage of time leads to repetition of previous scans.

Clearances per user and organization
************************************

The intensity of a scan is determined by the indemnity available. OpenKAT can invoke enough tools to put a heavy load on a system and permission is required to do so. If there is none, information can always be gathered through "third parties" such as with shodan and similar databases.

Findings and reports
********************

The results of the analysis are easy to view, by user, organization, object, etc. Reports are available for common questions and easily expandable.

Current release
===============

The current release of OpenKAT can be found via the `release page on this repository <https://github.com/minvws/nl-kat-coordination/releases>`_.

What code does OpenKAT contain?
===============================

OpenKAT includes the following subsystems, which can all be found in the `NL-KAT-Coordination <https://github.com/minvws/nl-kat-coordination>`_ repository (aka this one):

:Scheduler: `Mula <https://github.com/minvws/nl-kat-coordination/tree/main/mula>`_

:Datamodel with object types and objects: `Octopoes <https://github.com/minvws/nl-kat-coordination/tree/main/octopoes>`_

:Front end: `Rocky <https://github.com/minvws/nl-kat-coordination/tree/main/rocky>`_

:Raw data storage: `Bytes <https://github.com/minvws/nl-kat-coordination/tree/main/bytes>`_

:Boefjes and normalizers: `Boefjes <https://github.com/minvws/nl-kat-coordination/tree/main/boefjes>`_

Which licence applies to OpenKAT?
=================================

OpenKAT is available under the `EU PL 1.2 license <https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12>`_. This license was chosen because it provides a reasonable degree of freedom while ensuring public character. The EU PL 1.2 license is retained upon further distribution of the software. Modifications and additions can be made under the EU PL 1.2 license or under compatible licenses, which are similar in nature.

The tools addressed by OpenKAT may have their own license, from the OS/S domain or from commercial application. This is the responsibility of the owner of the system addressing these tools. The inclusion of new boefjes in the KAT catalog is governed by a separate agreement.

Participate
===========

You can directly participate and be involved in the development of OpenKAT. There is a community around OpenKAT with active developers and organizations working on implementing their own OpenKAT setup. If you want to start slowly, there are nice options:

- Install the system and use it, give us feedback
- Build your own boefjes, whiskers and bits
- Help extend the data model
- Suggest new features
- Submit `bugreports <https://github.com/minvws/nl-kat-coordination/issues>`_ as an issue
- Help make OpenKAT available for other operating systems

Test or develop via GitPod
**************************

Through gitpod, anyone (with a github, gitlab account) can quickly start up and test an OpenKAT environment. During this installation, you can enter your own username and password.

`Gitpod test environment <https://gitpod.io/#github.com/minvws/nl-kat-coordination>`_

Once started, the Rocky interface will be available on the service running on port 8000.

Can I also add code?
********************

That is most welcome! The coordination of the project lies with the development team at the Ministry of Health, Welfare and Sport, which is open to all contributions. Please get in touch, there are many people working on OpenKAT and combined efforts make the whole system stronger.

How can I add changes such as bug fixes, patches and new features?
******************************************************************

You can submit PRs directly via Github, or contact the community manager at meedoen@openkat.nl. Check out the templates and coding guidelines.

OpenKAT uses the following principles for writing code:

* python 3.8
* All code via pull requests with reviews
* `Python with PEP8 <https://peps.python.org/pep-0008/>`_.
* Pylint
* `[Black], 120 characters line length: <https://pypi.org/project/black/>`_
* Type hinting
* Tests

On Github you will find a development branch. Pull requests can be submitted for review. Based on the development branch, the main branch is fed for production releases. The reviews are done by VWS developers.

If you want your boefje to be included in the KAT catalog, a separate arrangement applies, which we would be happy to tell you about. Send an email to meedoen@openkat.nl.

I run Arch/NetBSD/OpenVMS or something else
*******************************************

How can I make sure OpenKAT works on my system? OpenKAT assumes you're running ubuntu or debian, but the community manager got it working under Mac OS X in no time. So feel free to try it and help us with fixes and documentation for installation on your favorite system!

Internationalization
====================

OpenKAT currently supports the following languages:

- English
- Dutch
- Papiamento

Most of the documentation in the software itself is written in English. Some of the general documentation is in Dutch, but we would like to make it available in other languages as well.

Contact
=======

There several options to contact the OpenKAT team:

- Direct contact: meedoen@openkat.nl
- `Github Discussions <https://github.com/minvws/nl-kat-coordination/discussions>`_
- `OpenKAT group on Linkedin <https://www.linkedin.com/>`_ (search for OpenKAT)
- IRC: #openkat on irc.libera.chat
- `Signal group <https://signal.group/#CjQKIIS4T1mDK1RcTqelkv-vDvnzrsU4b2qGj3xIPPrqWO8HEhDISi92dF_m4g7tXEB_QwN_>`_
