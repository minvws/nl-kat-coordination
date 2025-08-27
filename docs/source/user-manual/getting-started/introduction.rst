Introduction
============

Let's get started with OpenKAT! If you want to read more about what OpenKAT is and why it is created, please read :doc:`/about-openkat/index`.


General information
-------------------

OpenKAT is an open source vulnerability analysis tool that can monitor, record, and analyze the status of information systems.
OpenKAT does this automatically and continuously.

With OpenKAT, networks can be scanned, including websites, mail servers, and DNS servers.
The tool scans for vulnerabilities and analyzes them. Various plugins (which are the most commonly used network tools and scanning software) are used for this purpose.

All information found by OpenKAT can be converted into clear, accessible reports.


The scanning process
--------------------

OpenKAT scans, collects, analyzes and reports in an ongoing process:

.. image:: img/openkat-simple-process.png
  :alt: Simple process of OpenKAT.


The information collected by OpenKAT is stored as objects. An object can be, for example, a URL, IP address, or hostname.

After the objects are stored, tasks are created. Then, the activated plugins start scanning the objects.
The resulting information is stored again as an object, which can lead to new scans.
This process continues until OpenKAT has searched the entire data model.

Reports can be generated from the objects, providing a clear overview of all the information.

An example:
    A user adds an object and hostname. If there is a hostname, OpenKAT also expects an IP address and possible open ports.
    Tasks are created and the plugins then start searching for IP addresses and open ports, which may yield some more information.
    That new information may in turn trigger new scans.
    This process continues until OpenKAT has searched the entire data model for this hostname.

How far OpenKAT goes with its search depends on the clearance levels that are provided. Read more about it here: :doc:`../basic-concepts/scan-levels-and-indemnification`.

So this is what OpenKAT does behind the scenes, in simple terms.
If you want more details about this process, please check :doc:`../basic-concepts/index` (simple terms) or the :doc:`../../developer-documentation/basic-principles/index` (for developers).


User flow
---------

Now let's see how this looks to the user.

- A user of OpenKAT must first add objects, such as a URL, a hostname, or an IP address.
- Next, the user chooses which plugins will be used for the scans.
- After the plugins have had some time to gather information, the user can view the findings.
- The user can now also generate reports based on the findings. This can be done once or periodically.


Starting with OpenKAT
---------------------

To start with OpenKAT you have to log in first. If you have trouble logging in, please read :doc:`login-and-registration`.

After logging in, you continue to the onboarding. This onboarding will walk you through creating and scanning your first object and report. You can more about the onboarding, here: :doc:`onboarding`.

You can also skip the onboarding and directly go to :doc:`create-object` to create your first object in OpenKAT.
