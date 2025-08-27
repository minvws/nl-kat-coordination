Objects and recursion
=====================

The information collected by OpenKAT is stored as objects.
Objects can be anything, like DNS records, hostnames, URLs, IP addresses, software, software versions, ports, etc.


Properties
----------
Objects can be viewed via the 'Objects' page in OpenKAT's main menu. Here are the already created objects with the type and safeguard level for each object.
Objects can be added, scanned, filtered and there is an export option.

New objects can be created via the 'add' option. This can be done individually or per CSV.
The specification of the CSV is included on the page where it can be provided.


Recursion
---------
These objects are part of a data model. The data model is the logical connection between all objects and provides the basis for analysis and reporting.
OpenKAT includes a data model suitable for information security, but it can be expanded or adapted for other applications.

Adding an initial object with an appropriate safeguard puts OpenKAT to work. This can be done in on-boarding,
but objects can also be added individually or as CSV files. Objects are also referred to as 'Objects of Interest' (OOI).
The object itself contains the actual data: an objecttype describes the object and its logical relations to other objecttypes.

**Example:**
If there is a hostname, OpenKAT also expects an IP address and possible open ports based on the data model.
Depending on the given clearance level, this is then scanned, which in turn provides more information, which in turn may prompt new scans.
This process continues until OpenKAT has searched the entire data model for this hostname.
How far OpenKAT goes with its search depends on the safeguards.


Object clearance type
---------------------
Each object has a clearance type. The clearance type tells how the object was added to the Objects list. The following clearance types are available:

- Declared: declared objects were added by the user.
- Inherited: inherited objects were identified through propagation and the parsing of bits and normalizers. This means there is a relation to other object(s).
- Empty: empty objects do not have a relation to other objects.

The objects below show different clearance types for various objects. The hostname `mispo.es` was manually added and thus is `declared`.
The DNS zone is `inherited` based on the DNS zone boefje.

.. image:: img/objects-clearance-types.png
  :alt: different object clearance types
