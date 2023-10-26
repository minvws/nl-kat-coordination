Octopoes Research
#################

Introduction
============
At time of writing, KAT has been in development for almost 2 years. The project has gone through several iterations of refinement and changes in scope, but the overall software architecture has remained stable for a while now.

This document concerns Octopoes, a core component within KAT which is intended to store a modeled copy of the world in a bi-temporal graph database. Octopoes is intended to include a reasoning engine that is able to post-process data by executing rules to draw conclusions from a given dataset.

While the architecture of KAT is quite clear and documented, the workings of Octopoes are still slightly obscure and not sufficiently formally defined. This lack of documentation and formalization in this core component of KAT is currently resulting in unclear constraints considering the rule-engine, vagueness of to be made trade-offs between expressivity and computational complexity, etc.

A large revision of Octopoes is currently in the works that should incorporate the learnings and experience of the last two years. This revision should address most of the current challenges and it is of vital importance to have a (relatively formal) description of the intended workings.

This document is divided in two parts. Part 1 addresses the context of Octopoes and sketches rough requirements. Complexities of the intended functionality are described, with their respective backgrounds.

Part 2 attempts to sketch the possible components that, when combined, result in the software that satisfies the requirements, within the known constraints.

Note: as KAT is first and foremost developed for application in the cybersecurity domain, some examples in this document are given in this context.


Part I - Requirements, context and inherent complexities
========================================================

Context of Octopoes in KAT
--------------------------

Event loop
^^^^^^^^^^

KAT as a whole can be defined as a configurable, distributed crawler. A feedback loop is constructed by continuously:

1. Executing programs that gather data, with entities as input
2. Structuring the yielded data to extract entities
3. Storing the extracted entities in a persisted graph
4. Feeding these entities as input for the programs in step 1

KAT dataflow
^^^^^^^^^^^^
For reasons like scalability and extensibility the above concept is broken up and realized into multiple components.

Objectives
----------

KAT
^^^

The ability to timestamp and sign raw output data and metadata (primarily bytes' responsibility)
The ability to schedule new scans for newly created objects and recurring scans for existing objects (primarily mula's responsibility)
The ability to extract structured data from raw data (primarily whisker's responsibility)


Octopoes
^^^^^^^^

The ability to draw conclusions ("findings") automatically from data, based on business rules which are called “bits”.
Create new objects from business rules
And by extension: trigger new business rules on those new objects
Perform advanced, complex, and fast queries on the data for analysis, alerting, and reporting
The ability to change, reduce, and expand the set of objects and rules throughout KAT's lifecycle
A domain-independent architecture, i.e. the model should accommodate domains beyond technical cybersecurity
The ability to enable and disable certain objects and rules
The ability for objects to inherit clearance levels from their neighbors, in an automatic and sensible way (n.b. probably specific to the security domain - maybe generalizable through bits)

Desired/future
^^^^^^^^^^^^^^

Temporal reasoning about historical states of the data
The ability to federate several KAT installations, to enable distributed computing and accept signed results from other instances (e.g. to gain information about private networks and systems).


Complexities of Octopoes
------------------------

Realizing these objectives comes with several challenging aspects.

Open-world assumption
^^^^^^^^^^^^^^^^^^^^^

Octopoes gains knowledge by three methods:
1. Observation by scanning the world
2. Information declared to be true by users or other software systems
3. Reasoning through defined rules (bits)

Per definition, Octopoes is not authoritative of the data it captures and therefore has to take an open-world assumption (OWA). In short, this means that the information stored in Octopoes is not complete (Octopoes does not know the full state of the world). Octopoes can only make claims about data that is known. Questions about information that is unknown to Octopoes are consequently answered by ‘unknown’.

On the contrary, a system making a closed-world assumption (CWA), seems to be simpler to deal with. CWA systems have complete knowledge of their respective domain and are therefore authoritative. Any questions asked to this system can be definitively answered with a yes or no.

Example of an authoritative database

In a “classical” application, the database source contains the complete knowledge about the domain. Questions like “Is there an order with id 31” can be answered with “no” definitively.

Example in KAT

Question: “Is port 443 open on IPAddress 2.2.2.2?”
KAT: “Unknown”

Contradicting information
^^^^^^^^^^^^^^^^^^^^^^^^^

Information about the world can come from several sources. Direct observations but also third parties can be sources of information. It is absolutely not guaranteed that these several sources agree on statements about the world and it is even likely that these sources will contradict each other at some point.

Octopoes needs to deal with this, by performing (naive) disambiguation. Perhaps an approach based on confidence scores of sources and the age of the provided information is suitable.

Example
Claims:
Shodan claims the state of port 80 of IPv4 address 1.1.1.1 as ‘closed’, 2 days ago
A nmap scan claims the state of port 80 of IPv4 address 1.1.1.1 as ‘filtered’, 1 day ago
A HTTP request to port 80 of IPv4 address 1.1.1.1 is successful, resulting in a claim of the port state ‘open’, just now

An approach to determine the state of the port could be to first compare the confidence levels of the sources.
Shodan is a third party, resulting in a low source confidence score
Nmap provides a direct observation, resulting in a relatively high source confidence score
The HTTP request cannot be successful without the open port, resulting in a very high source confidence

Then, take into account the age of each claim.
The Shodan claim was 2 days ago, resulting in a low age confidence score
The nmap claim was 1 day ago, resulting in a medium age confidence score
The HTTP request claim was just now, resulting in a very high age confidence score

A possible approach could be to multiply the source confidence score with the age confidence score and take the highest combined confidence score as for truth.


Logic
^^^^^
By including rule-base data processing into a system, it needs to be clear that the domain of computational and mathematical logic is entered. We will briefly go over some of the basics of logic. At its core, logic consists of premises resulting in consequences. Given a set of premises, a reasoner can infer logical consequences and therefore yield additional (implicit) knowledge.

For the first iteration of the rule engine in Octopoes, a simple approach was proposed to find objects in the graph satisfying specific conditions and applying labels to these objects.
Example rule
Condition: 			Public IPv4 address with port 1433 open
Logical consequence: 	Vulnerability with high severity

IPv4Address(x) ^ Port(y) ^ RelationState("open", x, y) Finding(Severity 1, Reason "Open Port", x, y)

(where x is an object that satisfies the criteria of an IPv4 address, y is an object that satisfies the criteria of a port, RelationState() represents a relationship linking two objects together with the condition "open".)

The premises (knowledge base and rules) form the mathematical proof for the existence of the consequence

Reasoning
In this simple example, the logical consequence of this rule is not a premise for another rule. Therefore, the derived knowledge (presence of a high vulnerability) is a first-order derivative from the knowledge base. It gets more complicated though, when derived consequences can be a premise for another rule. Recursion of inference can start to occur, resulting in a process which is called inference chaining.


Part II - Working towards a solution
====================================


See :ref:`Development` for our code style, coding conventions, and overall workflow.

- Fork the right repository in GitHub
- Create a new branch from either ``main`` or a release tag. Note that ``main`` changes rapidly, and as such may not be a suitable basis for your work.
    - This branch should be in the following format:
    - ``[feature|enhancement|bug|hotfix]/random-cat-popup-on-screen``
- Commit and push the code
    - Make sure the code is linted, formatted and has correct typing
    - The code must pass ``pre-commit`` locally
- Submit Pull Request
    - Make sure your code is tested and the PR has a good title and description
    - Use the PR template
    - Let your code be reviewed
    - You might have to update your PR after remarks and submit rework for approval


Contribute Documentation
========================

Contributing to the documentation benefits everyone who uses OpenKAT.
We encourage you to help us improve the documentation, and you don't have to be an expert using OpenKAT to do so.
There are many sections that are better off written by non-experts.
If something in the docs doesn't make sense to you, updating the relevant section might be a great way to ensure it will help the next person.
You're welcome to propose edits to almost every text, including comments and docstrings in the code, this documentation, and other files.

You could help us out with the following sections:

- Code documentation
- Tutorials
- Translations
- This document

All documentation should be placed in a repository's ``docs`` folder.

Contribute Translations
=======================

.. image:: https://hosted.weblate.org/widget/openkat/287x66-white.png
   :target: https://hosted.weblate.org/engage/openkat/
   :alt: Translation status (summary)

.. image:: https://hosted.weblate.org/widget/openkat/multi-auto.svg
   :target: https://hosted.weblate.org/engage/openkat/
   :alt: Translation status (bar chart)

============ ==============================
 Language     Support
============ ==============================
 English      Default; used in source code
 Dutch        Official
 Papiamentu   Community
 Italian      Community
============ ==============================

We gratefully use `Weblate <https://hosted.weblate.org/engage/openkat/>`_ to manage the translations.
Community contributions are very welcome and can be made via Weblate's interface.
This is a great way to help the project forward and doesn't require any technical expertise.
If you would like to see OpenKAT in another language, let us know!

Any authenticated Weblate user can edit translation strings directly or make suggestions.
Any translation updates in Weblate will be automatically submitted as a GitHub PR after 24 hours, which will be reviewed by the development team.
If you contribute to the translation effort, you will receive a mention in the source code.

Note that editing the English localization requires changing the source string in Django, which must be done through a GitHub PR manually.

Contributor Social Contract
===========================
All contributors (including, but not limited to, developers and issue reporters) promise to do their best to adhere to the guidelines in :ref:`Project Guidelines`.
Everyone is encouraged to politely and constructively point out guidelines violations to others.
Actively enforcing these guidelines makes that the entire project benefits in quality control.

Code of Conduct
===============
See the `Code of Conduct of the Ministry of Health, Welfare, and Sport <https://github.com/minvws/.github/blob/main/CODE_OF_CONDUCT.md>`_.

Security
========
See the `Responsible Disclosure Statement of the Ministry of Health, Welfare, and Sport <https://github.com/minvws/.github/blob/main/SECURITY.md>`_.
