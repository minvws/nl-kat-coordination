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

`The full documentation of OpenKAT can be found here: https://docs.openkat.nl <https://docs.openkat.nl>`_. It includes information such as:

- Introduction to the system
- Modules
- Guidelines
- Templates
- Technical documentation
- Our `Figma / UX designs <https://docs.openkat.nl/ux_design/figma.html>`_.

Brochures
=========

The high level documentation on OpenKAT explains the purpose and operation of OpenKAT at the management level:

- `the 'TL;DR' of 2 pages (English) <https://github.com/minvws/nl-kat-coordination/blob/main/docs/source/introduction/pdf/OpenKAT%20handout_ENG.pdf>`_
- `the extensive brochure on OpenKAT (Dutch) <https://github.com/minvws/nl-kat-coordination/blob/main/docs/source/introduction/pdf/introductie%20OpenKAT%20V20220621.pdf>`_

Current release
===============

The current release of OpenKAT can be found via the `release page on this repository <https://github.com/minvws/nl-kat-coordination/releases>`_.

Translations
============
.. image:: https://hosted.weblate.org/widget/openkat/287x66-white.png
   :target: https://hosted.weblate.org/engage/openkat/
   :alt: Translation status (summary)

.. image:: https://hosted.weblate.org/widget/openkat/multi-auto.svg
   :target: https://hosted.weblate.org/engage/openkat/
   :alt: Translation status (bar chart)

We gratefully use `Weblate <https://hosted.weblate.org/engage/openkat/>`_ to manage the translations.
See `the docs <https://docs.openkat.nl/guidelines/contributions.html#contribute-translations>`_ for more information.


Which license applies to OpenKAT?
=================================

OpenKAT is available under the `EU PL 1.2 license <https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12>`_. This license was chosen because it provides a reasonable degree of freedom while ensuring public character. The EU PL 1.2 license is retained upon further distribution of the software. Modifications and additions can be made under the EU PL 1.2 license or under compatible licenses, which are similar in nature.

The tools addressed by OpenKAT may have their own license, from the OS/S domain or from commercial application. This is the responsibility of the owner of the system addressing these tools. The inclusion of new boefjes in the KAT catalog is governed by a separate agreement.

Contact
=======

There several options to contact the OpenKAT team:

- Direct contact: meedoen@openkat.nl
- `Github Discussions <https://github.com/minvws/nl-kat-coordination/discussions>`_
- `OpenKAT group on Linkedin <https://www.linkedin.com/>`_ (search for OpenKAT)
- IRC: #openkat on irc.libera.chat
- `Signal group <https://signal.group/#CjQKIIS4T1mDK1RcTqelkv-vDvnzrsU4b2qGj3xIPPrqWO8HEhDISi92dF_m4g7tXEB_QwN_>`_

Privacy
=======

OpenKAT is not designed to collect private information and it does not act on any private information that its finds. Some information considered to be personally identifying information might be collected through one or more of OpenKAT's plugins and subsequently stored, but only if that information was accessible to OpenKAT. E.g. a phone number or email address listed on a website might end up being collected as part of OpenKAT normal data collection. This data might then be stored for a long time because OpenKAT stores 'proofs' of its actions. No email or phone number models are present and as such they won't be processed into objects by OpenKAT.
An OpenKAT installation requires user accounts for users to be able to login. These accounts (and all data OpenKAT works with) are stored only on the OpenKAT installation itself and are not shared with other parties or outside of your OpenKAT install.

Security
========

OpenKAT is designed to be secure by default in its production setup. In the development setup some debugging flags are enabled by default and it will not include TLS out of the box. To setup a secure production OpenKAT install, please follow the `Production setup guidelines <https://docs.openkat.nl/installation_and_deployment/install.html#production-environments>`_ and `Hardening guidelines <https://docs.openkat.nl/installation_and_deployment/hardening.html>`_.
