===============================================
Plugins for OpenKAT: boefjes, whiskers and bits
===============================================

OpenKAT is modular and can be easily extended. This guide provides a first step for the development of new plugins: boefjes that scan, whiskers that collect objects, and bits that contain businessrules. 

OpenKAT comes with a KATalog of boefjes, which can be viewed through the front end of the system. The premise is that all information is processed and stored in the smallest unit, ensuring the modular nature of OpenKAT. 

OpenKAT can access multiple KATalogs, so it is possible to create your own overview of boefjes in addition to the official KATalog. This is of interest to organizations that use boefjes for specific purposes or with software that has a different licensing model.

This guide explains how the plugins work and how they are created, and gives an overview of which plugins already exist. 

The community is working on sample boefjes with a ``enter your code here`` option and a repository with a prebuilt CI that provides boefjes as artifacts. Please send an email to meedoen@openkat.nl if you would like to participate in this. 

What types of plugins are there?
==============================

There are three types of plugins, deployed by OpenKAT to collect information, translate it into objects for the data model and then analyze it. Boefjes gather facts, Whiskers structure the information for the data model and Bits determine what you want to think about it; they are the business rules. Each action is cut into the smallest possible pieces. 

- Boefjes gather factual information, such as by calling an external scanning tool like nmap or using a database like shodan. 

- Whiskers analyze the information and turn it into objects for the data model in Octopoes

- Bits contain the business rules that do the analysis on the objects. 

Boefjes and Whiskers are linked together through the mime-type that the rascal passes along to the information. For each mime-type, multiple Boefjes and Whiskers are possible, each with its own specialization. Thus, the data from a crook can be delivered to multiple whiskers to extract a different object each time. Bits are linked to objects and assess the objects in the data model.

How does it work? 
==============

A hostname given as an object to OpenKAT, for example, is used as input to a search by the matching boefjes. Based on the data model, logically related objects are searched to get a complete picture. 

Thus, OpenKAT is like a snowball rolling through the network based on the data model. The logical connections between objects point the way, and OpenKAT keeps looking for new boefjes until the model is complete. 

The new objects in the data model are evaluated by Bits, the business rules. This produces findings, which are added as objects. For example, the hostname includes a dns configuration, which must meet certain requirements. If it goes outside the established parameters it leads to a finding. 

Where to start? 
==============

The first question is what information you need. If you know this, there are a number of options, which determine what is best to do:

- the information is already present in the data model -> create a businessrule (bit)
- the information is present in the output of an existing boefje -> create a normalizer (whiskers) 
- the information is not yet available -> create a boefje, modify the data model and create a normalizer

If you want to add factual information, use a boefje. Want to add an opinion or analysis, use a bit. 

OpenKAT assumes that you collect and process all information in the smallest possible units so that they can contribute back to other combinations and results. This is how you maintain the modular nature of the package. 

To make a finding about a CVE to a software version, you have a string of objects: the finding of the software, the version, the CVE. That combination then leads to the object of the finding. 

Existing boefjes
=================

The existing boefjes can be viewed via the KATalog in OpenKAT and are on `GitHUB in the boefjes repository. <https://github.com/minvws/nl-kat-boefjes/tree/main/boefjes>`_

Example: the boefje for shodan
---------------------------------

The boefje calling shodan gives a good first impression of its capabilities. The boefje includes the following files. 

- __init.py__, which remains empty, 
- boefje.json, containing the normalizers and objects in the data model,
- cover.jpg, with a matching cat picture for the KATalog
- description.md, simple documentation of the boefje
- main.py, the actual boefje
- normalize.py, the normalizer (whiskers)
- normalizer.json, which accepts and supplies the normalizer
- requirements.txt, with the requirements for this rascal
- schema.json, settings for the web interface

boefje.json
***********

boefje.json is the definition of the boefje, with its position in the data model, the associated normalizer, the objects and the findings that the combination of boefje and normalizer can deliver. 

The objects associated with this boefje are IPAddressV4, IPAddressV6, Finding, CVEFindingType. This boefje consumes IP addresses and produces findings about the open ports, supplemented by the information about these ports.

Shodan comes with an API key, which you can add in the web interface. 

.. code-block::

    {
        "id": "shodan",
        "name": "Shodan",
        "description": "Use Shodan to find open ports with vulnerabilities that are found on that port",
        "consumes": [
            "IPAddressV4",
            "IPAddressV6"
        ],
        "produces": [
            "Finding",
            "IPPort",
            "CVEFindingType"
        ],
        "environment_keys": ["SHODAN_API"],
        "scan_level": 1
    }

Using the template as a base, you can create a boefje.json for your own boefje. The template starts with the name of your new boefje: 


.. code-block::

    {
        "id": "boefje",
        "name": "Boefje",
        "description": "Beschrijving",

Your boefje collects information to turn it into objects. Specify the objects your boefje needs. Those objects come from the data model. Should the information you want to retrieve not yet be incorporated into the data model, you need to modify it separately. How this works is described in general terms later in this document. 

.. code-block::

        "consumes": [
            "object uit het datamodel",
            "nog een object uit het datamodel"
        ],
        "produces": [
            "informatie",
            "informatie"
        ],

The boefje can also bring variables from the web interface, like in Shodan the API key. There are more possibilities, you can be creative with this and let the end user bring settings from the web interface. 

.. code-block::

        "environment_keys": ["SHODAN_API"],
        "scan_level": 1
        

schema.json
***********

To allow the user to add information through the web interface, add the schema.json file to the folder where your boefje is located. This json is used as the basis for a form for the user. In this case, it can contain an API key, but it can also be something else that your boefje responds to. This Schema must conform to the https://json-schema.org/ standard.

Currently, however, OpenKAT only understands fairly shallow structures. For example, not all field types are supported, nor does OpenKAT understand references. You can test whether your Schema is neatly understood by checking the settings form in Rocky's KAT catalog for your boefje.

.. code-block::

 {
  "title": "Arguments",
  "type": "object",
  "properties": {
    "SHODAN_API": {
      "title": "SHODAN_API",
      "maxLength": 128,	
      "type": "string",
      "description": "A Shodan API key (see https://developer.shodan.io/api/requirements)."
    }
  },
  "required": [
    "SHODAN_API"
  ]
 }

main.py 
*******

The boefje itself imports the shodan api module, assigns an IP address to it and accepts the output. This output goes to Bytes and is analyzed by one (or more) normalizers. The link between the normalizer and the byte is made via the mime-type, which you can give in the ``set`` function in the byte. The code block below also contains a check, to prevent you from asking for non-public IP addresses. 

.. code-block::

	import json
	import logging
	from typing import Tuple, Union, List

	import shodan

	from os import getenv
	from ipaddress import ip_address

	from boefjes.job_models import BoefjeMeta


	def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
	    api = shodan.Shodan(getenv("SHODAN_API"))
	    input_ = boefje_meta.arguments["input"]
	    ip = input_["address"]
	    results = {}
	
	    if ip_address(ip).is_private:
	        logging.info("Private IP requested, I will not forward this to Shodan.")
	    else:
	        try:
	            results = api.host(ip)
	        except shodan.APIError as e:
	            if e.args[0] != "No information available for that IP.":
	                raise
	            logging.info(e)

	    return [(set(), json.dumps(results))]

Normalizers 
-----------

The normalizer imports the raw information, extracts the objects from it and gives them to Octopoes. Since OpenKAT 1.3.0, the normalizers are fully self-contained. They consist of the following files: 

- __init__.py
- normalize.py
- normalizer.json

normalizer.json
***************

The normalizers translate the output of a boefje into objects that fit the data model. Each normalizer defines what input it accepts and what it provides. In the case of the shodan normalizer, it involves the entire output of the shodan boefje (created based on IP address), where findings and ports come out. The normalizer.json defines these:

.. code-block::

	{
	    "id": "kat_shodan_normalize",
	    "consumes": [
	        "shodan"
	    ],
	    "produces": [
	        "Finding",
	        "IPPort",
	        "CVEFindingType"
	    ]
	}

normalize.py
************

The file normalize.py contains the actual normalizer. From octopoes, the normalizer retrieves the objects and their references: from the findings list the CVEFindingType for the CVEs and the Finding for the findings, from the network objects list the IPPort, the Protocol and the PortState. Then the information about those objects is extracted from the imported data and stored as objects. 

.. code-block::

 import json
 from typing import Iterator, Union

 from octopoes.models import OOI, Reference
 from octopoes.models.ooi.findings import CVEFindingType, Finding
 from octopoes.models.ooi.network import IPPort, Protocol, PortState

 from boefjes.job_models import NormalizerMeta

 def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    results = json.loads(raw)
    ooi = Reference.from_str(normalizer_meta.boefje_meta.input_ooi)

    for scan in results["data"]:
        port_nr = scan["port"]
        transport = scan["transport"]

        ip_port = IPPort(
            address=ooi,
            protocol=Protocol(transport),
            port=int(port_nr),
            state=PortState("open"),
        )
        yield ip_port

        if "vulns" in scan:
            for cve, _ in scan["vulns"].items():
                ft = CVEFindingType(id=cve)
                f = Finding(finding_type=ft.reference, ooi=ip_port.reference)
                yield ft
                yield f

Adding objects
==============

If you want to add an object, you need to know with which other objects there is a logical relationship. An object is as simple as possible. As a result, a seemingly simple query sometimes explodes into a whole tree of parts. 

Adding objects to the data model requires an addition in octopus. Here, an object can be added if it is connected to other objects. Visually this is well understood using the `Graph explorer <https://mispo.es/model-explorer/model-explorer.html>`_. The actual code is `in the Octopoes repo <https://github.com/minvws/nl-kat-octopoes/tree/main/octopoes/models/ooi>`_. 

As with the boefje for shodan, here we again use the example from the functional documentation. A description of an object in the data model, in this case an IPPort, looks like this: 


.. code-block::

 class IPPort(OOI):
    object_type: Literal["IPPort"] = "IPPort"

    address: Reference = ReferenceField(IPAddress, max_issue_scan_level=0, max_inherit_scan_level=4)
    protocol: Protocol
    port: conint(gt=0, lt=2 ** 16)
    state: Optional[PortState]

    _natural_key_attrs = ["address", "protocol", "port"]
    _reverse_relation_names = {"address": "ports"}
    _information_value = ["protocol", "port"]
    

Here it is defined that to an IPPort belongs an IPadress, a Protocol and a PortState. It also specifies how scan levels flow through this object and specifies the attributes that format the primary/natural key: "_natural_key_attrs = ["address", "protocol", "port"]". More explanation about scan levels / indemnities follows later in this document. 

The PortState is defined separately. This can be done for information that has a very specific nature so you can describe it. 

.. code-block::

 class PortState(Enum):
    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"
    UNFILTERED = "unfiltered"
    OPEN_FILTERED = "open|filtered"
    CLOSED_FILTERED = "closed|filtered"

Bits: businessrules
===================

Bits are businessrules that assess objects. Which ports are allowed to be open, which are not, which software version is acceptable, which is not. Does a system as a whole meet a set of requirements associated with a particular certification or not? 

In the hostname example, that provides an IP address, and based on the IP address, we look at which ports are open. These include some ports that should be open because certain software is running and ports that should be closed because they are not used from a security or configuration standpoint. 

The example below comes from the functional documentation and discusses the Bit for the IPPort object. The bit used for the analysis of open ports consists of three files: 

- __init.py__, an empty file
- bit.py, which defines the structure
- port_classification.py, which contains the business rules

Bit.py gives the structure of the bit, containing the input and the businessrules against which it is tested. An example is included below. The bit accepts input belonging to the objects IPPort and IPAddress. It then calls the module port_classification, which contains the businessrules.


.. code-block::

 from bits.definitions import BitParameterDefinition, BitDefinition
 from octopoes.models.ooi.network import IPPort, IPAddress

 BIT = BitDefinition(
    id="port-classification",
    consumes=IPPort,
    parameters=[],
    module="bits.port_classification.port_classification",
 )
 
The businessrules are contained in the module port_classification, in the file port_classification.py. This bit grabs the IPPort object and supplies the KATFindingType and Finding objects. The businessrules in this case distinguish three types of ports: the COMMON_TCP_PORTS that may be open, SA_PORTS that are for management purposes and should be closed, and DB_PORTS that indicate the presence of certain databases and should be closed. 

The specification for a bit is broad, but limited by the data model. Boefjes retrieve information externally, bits only look at the objects in Octopus. Analysis of the information can then be used to create new objects, such as the KATFindingTypes which in turn correspond to a set of specific reports in OpenKAT. 

.. code-block::

 from typing import List, Iterator

 from octopoes.models import OOI
 from octopoes.models.ooi.findings import KATFindingType, Finding
 from octopoes.models.ooi.network import IPPort

 COMMON_TCP_PORTS = [25, 53, 110, 143, 993, 995, 80, 443]
 SA_PORTS = [21, 22, 23, 3389, 5900]
 DB_PORTS = [1433, 1434, 3050, 3306, 5432]


 def run(
    input_ooi: IPPort,
    additional_oois: List,
 ) -> Iterator[OOI]:

    port = input_ooi.port
    if port in SA_PORTS:
        open_sa_port = KATFindingType(id="KAT-560")
        yield open_sa_port
        yield Finding(
            finding_type=open_sa_port.reference,
            ooi=input_ooi.reference,
            description=f"Port {port} is a system administrator port and should not be open.",
        )

    if port in DB_PORTS:
        ft = KATFindingType(id="KAT-561")
        yield ft
        yield Finding(
            finding_type=ft.reference,
            ooi=input_ooi.reference,
            description=f"Port {port} is a database port and should not be open.",
        )

    if port not in COMMON_TCP_PORTS and port not in SA_PORTS and port not in DB_PORTS:
        kat = KATFindingType(id="KAT-562")
        yield kat
        yield Finding(
            finding_type=kat.reference,
            ooi=input_ooi.reference,
            description=f"Port {port} is not a common port and should possibly not be open.",
        )

Bits can recognize patterns and derive objects from them. The Bit for internet.nl can thus deduce from a series of objects whether a particular site meets the requirements of internet.nl or not. This bit retrieves findings from a series of items and draws conclusions based on them. The analysis underlying this is built up from small steps, which go around OpenKAT several times before enough information is available to draw the right conclusions. 

.. code-block::

	from bits.definitions import BitParameterDefinition, BitDefinition
	from octopoes.models.ooi.dns.zone import Hostname
	from octopoes.models.ooi.findings import Finding
	from octopoes.models.ooi.web import Website

	BIT = BitDefinition(
	    id="internet-nl",
	    consumes=Hostname,
	    parameters=[
	        BitParameterDefinition(ooi_type=Finding, relation_path="ooi"),  # findings on hostnames
	        BitParameterDefinition(ooi_type=Finding, relation_path="ooi.website.hostname"),  # findings on resources
	        BitParameterDefinition(ooi_type=Finding, relation_path="ooi.resource.website.hostname"),  # findings on headers
	        BitParameterDefinition(ooi_type=Finding, relation_path="ooi.hostname"),  # findings on websites
	        BitParameterDefinition(ooi_type=Finding, relation_path="ooi.netloc"),  # findings on weburls
	        BitParameterDefinition(ooi_type=Website, relation_path="hostname"),  # only websites have to comply
	    ],
	    module="bits.internetnl.internetnl",
	)

Add Boefjes
===========

There are a number of ways to add your new boefje to OpenKAT. 

- Put your boefje in the local folder with the other boefjes 
- Do a commit of your code, after review it can be included
- Add an image server in the KAT catalog config file ``*`` 

``*`` If you want to add an image server, join the ongoing project to standardize and describe it. The idea is to add an image server in the KAT catalog config file that has artifacts from your boefjes and normalizers as outputted by the Github CI. 

The goal is to set up a separate Github repo with a complete CI to create artifacts based on a template boefje. You can clone this repo. Your OpenKAT installation points you to the artifacts so they are usable from your system. This is now being worked on by the OpenKAT community. Send an email to meedoen@openkat.nl if you want to help. (status: Dec. 2022)


