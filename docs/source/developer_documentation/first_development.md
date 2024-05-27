# Development example

We will be making a boefje, a normalizer, a bit, a new OOI-model and a report type which will check the database for an IPAddressV4 or IPAddressV6 OOI and create a simple Greeting object that contains a string provided by the user with an IPAddressV4 or IPAddressV6 OOI.

## Glossary

| **Term**   | **Description**                                                                                                                                                                                                                                                       |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| OOI        | Object Of Interest. An object that contains information. This can for example be an Ip address or a found vulnerability.                                                                                                                                              |
| Plugin     | A plugin that works in its docker container that looks for a certain type of OOI and then executes code (potentially scanning outside sources/APIs) when that OOI is found. This code will then return byte data that will be used by normalizers to create new OOIs. |
| Normalizer | A plugin that listens to specified boefjes', and creates new OOIs from the data that they find. This is often called a whisker.                                                                                                                                       |
| Bit        | A plugin that waits for specified OOIs and creates more OOIs from these.                                                                                                                                                                                              |

## Creating a boefje

1. Inside _boefjes/boefjes/plugins/_ create a new folder with a name starting with kat for this example we use _kat_hello_katty_

2. Inside this folder we need to have the following files:
   - \_\_init\_\_.py
   - boefje.json
   - cover.jpg
   - description.md
   - main.py
   - schema.json

### \_\_init\_\_.py

This file stays empty and is required for Python.

### boefje.json

This file contains metadata about the boefje. For example, this boefje contains information about what OOI this boefje should look out for. This is the example we will be using.

```json
{
  "id": "hello-katty",
  "name": "Hello Katty",
  "description": "A simple boefje that can say hello",
  "consumes": ["IPAddressV4", "IPAddressV6"],
  "environment_keys": ["MESSAGE", "NUMBER"],
  "scan_level": 0,
  "oci_image": "openkat/hello-katty"
}
```

- **id**: A unique identifier for the boefje.
- **name**: A name to display in the KAT-alogus
- **description**: A description in the KAT-alogus
- **consumes**: A list of OOI types that trigger the boefje to run. Whenever one of these OOIs gets added, this boefje will run with that OOI. In our case, we will run our boefje whenever a new IPAddressV4 or IPAddressV6 gets added.
- **environment_keys**: A list of inputs provided by the user. More information about these inputs can be found in schema.json. openKAT also provides some environment_keys.
- **scan_level**: A scan level that decides how intrusively this boefje will scan the provided OOIs. Since we will not make any external requests our boefje will have a scan level of 0.
- **oci_image**: The name of the docker image that is provided inside boefjes/Makefile

### cover.jpg

This file has to be an image of the developer's cat. This image will be used as a thumbnail for the boefje.

### description.md

This file contains a description of the boefje to explain to the user what this boefje does. For this example we can leave this empty.

### schema.json

This JSON is used as the basis for a form for the user. When the user enables this boefje they can get the option to give extra information. For example, it can contain an API key that the script requires.

This is an example of a schema.json file:

```json
{
  "title": "Arguments",
  "type": "object",
  "properties": {
    "MESSAGE": {
      "title": "Input text to give to the boefje",
      "type": "string",
      "description": "Some text so the boefje has some information to work with. Normally you could feed this an API key or a username"
    },
    "NUMBER": {
      "title": "Amount of cats to add",
      "type": "integer",
      "minimum": 0,
      "maximum": 9,
      "default": 0,
      "description": "A number between 0 and 9. To show how many cats you want to add to the greeting"
    }
  },
  "required": ["MESSAGE"]
}
```

- **title**: This should always contain a string containing 'Arguments'
- **type**: This should always contain a string containing 'object'
- **description**: A description of the boefje explaining in short what it can do. This will both be displayed inside the KAT-alogus and on the boefje's page.
- **properties**: This contains a list of objects which each will show the KAT-alogus what inputs are requested from the user. This can range from requesting for an API-key to extra commands the boefje should run.
  Inside the boefje.json file, we specified 2 environment variables that will be used by this boefje.
  - **MESSAGE**: For this property we ask the user to send us a string which this boefje will use to create some raw data.
  - **NUMBER**: For this property we ask the user to send us an integer between 1 and 9.
- **required**: In here we need to give a list of the objects' names that the user has to provide to run our boefje. For this example, we will only require the user to give us the MESSAGE variable. We do this by adding _"MESSAGE"_ to the _required_ list.

### main.py

This is the file where the boefje's meowgic happens. This file has to contain a run method that accepts a dictionary and returns a _list\[tuple\[set, bytes | str]]_.
This function will run whenever a new OOI gets created with one of the types mentioned in _consumes_ inside the _boefje.json_. :

Here is the example we will be using.

```python
import json
from os import getenv

def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    """Function that gets run to give a raw file for the normalizers to read from"""
    address = boefje_meta["arguments"]["input"]["address"]
    MESSAGE = getenv("MESSAGE", "ERROR")
    NUMBER = getenv("NUMBER", "0")

    # Check if NUMBER has been given, if it has not. Keep it at 0
    amount_of_cats = 0
    if NUMBER != "":
        try:
            amount_of_cats = int(NUMBER)
        except:
            pass

    cats = "😺" * amount_of_cats
    greeting = f"{MESSAGE}{cats}!!!"

    raw = json.dumps({
        "address": address,
        "greeting": greeting
    })


    return [
        (set(), raw)
    ]
```

The most important part is the return value we send back :
The final task of creating a boefje is specifying what DockerFile our boefje should use. We can do this inside the file located in boefjes/Makefile.
Inside the _images_ rule. We have to specify that we want to use _base.Dockerfile_ since our boefje does not require any special packages to run. This is as simple as adding a single line. Here is what that would look like in our case:

**BEFORE**

```
images:  # Build the images for the containerized boefjes
	docker build -f ./boefjes/plugins/kat_nmap_tcp/boefje.Dockerfile -t openkat/nmap  .
```

**AFTER**

```
images:  # Build the images for the containerized boefjes
	docker build -f ./boefjes/plugins/kat_nmap_tcp/boefje.Dockerfile -t openkat/nmap  .
	docker build -f images/base.Dockerfile -t openkat/hello-katty --build-arg BOEFJE_PATH=./boefjes/plugins/kat_hello_katty .
```

This was the creation of our first boefje. If we run openKAT now we should be able to see this boefje sitting in the KAT-alogus. Let’s try it out!

### Testing the boefje

First, we run `make kat`. After that successfully finishes. You can run `grep 'DJANGO_SUPERUSER_PASSWORD' .env` to get the password for the super user. The login e-mail is _superuser@localhost_.

After logging in, openKAT will guide you through their first-time setup.

1. Click the "Let's get started" button.
2. Input the name of your company (or just any name since this is a test run)
3. Also input a short code which will be used to identify your company on the back-end
4. On the next page give indemnification on the organization and declare that you as a person can be held accountable.
5. Press the "Continue with this account, onboard me!" button
6. And then you can press on the "Skip onboarding" button to finish the setup.
7. After that in the top left corner you can select your company.

We recommend that you at least once go through the onboarding process before developing your boefje.

8. Now we want to enable our boefje, for this we will need to go to the KAT-alogus (from the top nav bar) and look for our boefje and enable it.
9. If you followed the steps correctly, you should see two text inputs being requested from you. In the first one, you can put in any text that you want to be part of the boefje's greeting. As you might remember the second input is asking for an integer between 1 and 9 (you can see the description of the text inputs by pressing the question mark to the right of the text input.)
10. After having made your choice you can press the "Add settings and enable boefje" button.
11. Now it should say that the boefje has been enabled, but if we go to the Tasks page (from the top nav-bar) we see that the boefje is currently not doing anything. This is because our boefje will only run if a valid IPAddressV4 or IPAddressV6 OOI is available. Let's create one of those by using existing boefjes and normalizers.

If you do not want to go through the trouble of seeing existing boefjes and normalizers to work you can go to Objects > Add new object > Object type: _IPAddressV4_ > Insert an IPv4 address and choose as network _Network|internet_ and then skip to step 19.

12. Enable the "DnsRecords" boefje. This boefje takes in a hostname and makes a DNS-record from it.
13. Let's add a URL OOI. Go to Objects (from the top nav-bat) and on the right you will see an "Add" button. After pressing this button press the "Add object" button.
14. As an object type we will choose URL.
15. As a network for the URL we will select the internet ("Network|internet") and now we have to give it a website URL. For this example, we can use "https://mispo.es/" and then press the "add url" button.
16. If we now go to the Tasks tab, we will see that still no boefjes are being run. This is because our URL has too low of a clearance level. Go to the tab Objects and select the "mispo.es" OOI by pressing the checkbox in front of it. Then you can change the clearance level on the bottom of the page. To be able to get an IPAddressV4 OOI from this object, we will need to give it a clearance level of L1 or higher. For this example let's set it to L2.
17. After doing this we can go to the Tasks tab and see that boefjes have started running on our provided OOI. Now the "DnsRecords" boefje will make a raw file (of type "boefje/dns-records") and the "Dns Normalize" normalizer will obtain an IPAddressV4 or IPAddressV6 from this (you can see the normalizers task by going to the tab Tasks and then switching from Boefjes to the Normalizers tab.)
18. If we now go to the Objects tab. We can see that a lot more OOIs have been added. And also among other things, we can see IPAddressV4s being added. This means our boefje should run too.
19. After IPAddressV4 or IPAddressV6 OOIs have been added. Our boefje should immediately be queued to run from it. We can see this by going into the Tasks tab again. If you see a boefje called "Hello Katty" being run with a completed status then congratulations! Your first boefje has officially run!
20. We can now open the task with the arrow button on the right and if we then press the "Download meta and raw data" it will install a zip file with 2 files inside.
    - **meta file**: The json file contains meta data that our boefje has received. The _boefje_meta_ object has been given to our _run_ method as a parameter.
    - **raw file**: The other file without extension contains the information our boefje has returned. In our case it should contain a json as a single line string. You can open this file with any text editor to check it out. This data will be available for the normalizers that consume raw data with the type _boefje/hello-katty_.

Now that we have a way to generate the data for normalizers, we need to create a new type of OOI that the normalizer should generate from this raw data. So let's do that!

## Creating a new model

1. Inside _octopoes/octopoes/models/ooi/_ create a file called _greeting.py_. This file will contain the model for our Greeting OOI.
2. Inside this file we will create a class Greeting which will inherit from the OOI class. Inside this class, we can specify attributes that this model will maintain. For this example, we will add :
   - A greeting with the type string that will contain text from the information provided from the boefje.
   - An address with the type IPAddress (which can both be an IPAddressV4 an IPAddressV6) that has triggered our boefje.

This is how our _Greeting.py_ should look like now:

```python
from __future__ import annotations

from octopoes.models.ooi.network import IPAddress
from octopoes.models import OOI

class Greeting(OOI):
    greeting: str
    address: IPAddress
```

But openKAT also requires each OOI model to have properties called _object_type_ and _\_natural_key_attrs_. _object_type_ has to be of type _Literal\[<model_name>]_ containing the model's name. And _\_natural_key_attrs_ is used to create the primary key for the database. It has to contain a list of strings that contain names of the unique attributes of our model. This is an example of how our _Greeting.py_ could look like:

```python
from __future__ import annotations

from typing import Literal
from octopoes.models.ooi.network import IPAddress
from octopoes.models import OOI

class Greeting(OOI):
    object_type: Literal["Greeting"] = "Greeting"

    greeting: str
    address: IPAddress

    _natural_key_attrs = ["greeting", "address"]
```

The final part we want to change is the address field. Instead of having a field _address_ that contains information about the address. We can store a reference to an existing address. And we know this address exists since this model will only be created when our boefje runs and our boefje only runs when an IPAddressV4 or IPAddressV6 OOI gets added. We can make our address a reference by changing the code in the following way.

```python
from __future__ import annotations

from typing import Literal
from octopoes.models.persistence import ReferenceField
from octopoes.models.ooi.network import IPAddress
from octopoes.models import OOI, Reference

class Greeting(OOI):
    object_type: Literal["Greeting"] = "Greeting"

    greeting: str
    address: Reference = ReferenceField(IPAddress, max_issue_scan_level=0, max_inherit_scan_level=3)

    _natural_key_attrs = ["greeting", "address"]
```

As you can see, the _ReferenceField_ function takes in 3 parameters. The first option is the type of the object being referenced. _max_issue_scan_level_ gets used to set the clearance level of the IPAddress (which will be scanned again once a new Greeting OOI gets created and references this address), in our example, we set it to 0 because we don't want the address to be scanned again. And with _max_inherit_scan_level_ we specify what clearance level our Greeting OOI should get. The clearance level of our Greeting OOI gets inherited by the IPAddress as long as it is lower than _max_inherit_scan_level_.

Now that our model is finished we need to add it to the lists of existing OOIs. We can do this by going to _octopoes/octopoes/models/types.py_ and importing our Model by saying:

```python
from octopoes.models.ooi.greeting import Greeting
```

And then adding our _Greeting_ type to the _ConcreteOOIType_ set.
After this. OpenKAT has all the information needed for our model. Next, we will make a normalizer that takes in the boefje's raw data and makes a _Greeting_ OOI.

## Creating a normalizer

A normalizer takes as input raw data (a single string or a list of bytes) and produces OOIs from this. If you followed the steps correctly, we should have both the raw data (from our boefje) and the model for the OOI we want to produce.

To create a normalizer we are going to need 2 more files. These files can both be created inside the same directory as our boefje (_boefjes/boefjes/plugins/kat_hello_katty/_):

- normalizer.json
- normalize.py

### normalizer.json

This is a JSON file that contains information about our normalizer. The object inside should have 3 attributes:

- **id**: The string _id_ of the normalizer. For this, we will use the boefje's id with _"-normalize"_ concatenated to it.
- **consumes**: This is a list where we can specify which boefje's data the normalizer can use. The list is made out of the boefjes' ids. This normalizer will only use the raw data from our boefje, so we will make a list containing our boefje's id prefixed with _boefje/_.
- **produces**: This is also a list of strings where we can specify what OOIs our normalizer can produce. In our boefje's raw data, we can extract 3 kinds of OOIs. The _IPAddressV4_, _IPAddressV6_ and _Greeting_ OOI. But when you want to create an _IPAddress_ OOI, then you have to give it a reference to its network. Because we have to get the Network OOI anyway, we will also produce it in our normalizer.

Here is an example of how our _normalizer.json_ can look like:

```json
{
  "id": "hello-katty-normalize",
  "consumes": ["boefje/hello-katty"],
  "produces": ["IPAddressV6", "IPAddressV4", "Network", "Greeting"]
}
```

### normalize.py

This file is where the normalizer's meowgic happens. This file also has a run function that takes in information about the boefje and the raw data the boefje has provided. This run method returns an Iterable that contains OOIs. The first step we should take is to decode the raw data that we have received from our boefje and load the JSON string as a dictionary. Then we can create IPAddress OOIs. We do not know whether we should make an IPAddressV4 or IPAddressV6 So we will have to check what kind of IPAddress we have and yield the correct one. Creating an IPAddress requires specifying what network that IPAddress lies on (in our example that is the internet.) We can get this by using _normalizer_meta_ also provided in our run function. This dictionary is similar to the JSON you have seen when downloading the results of our boefje's task. Inside this dictionary, we can get information on the IPAddress that has triggered our boefje. And pull the reference.

Lastly, we will create our unique OOI. This is as simple as creating an object of the _Greeting_ class we have made and yielding it. This is what our file could look like:

```python
import json
from collections.abc import Iterable
from ipaddress import AddressValueError, IPv4Network, NetmaskValueError

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, Network
from octopoes.models.ooi.greeting import Greeting


def is_ipv4(string: str) -> bool:
    try:
        IPv4Network(string)
        return True
    except (AddressValueError, NetmaskValueError, ValueError) as e:
        return False

def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    """Function that gets run to produce OOIs from the boefje it consumes"""

    data_string = str(raw, "utf-8")
    data: dict = json.loads(data_string)

    network = Network(name=normalizer_meta.raw_data.boefje_meta.arguments["input"]["network"]["name"])
    yield network

    ip = None
    if is_ipv4(data["address"]):
        ip = IPAddressV4(network=network.reference, address=data["address"])
    else:
        ip = IPAddressV6(network=network.reference, address=data["address"])

    yield ip
    yield Greeting(address=ip.reference, greeting=data["greeting"])
```

That should be all for the normalizer! If you restart openKAT with `make kat`. Then you should see that the normalizer gets dispatched. You can see this by going to the tab _Tasks_ and then switching from _Boefjes_ to _Normalizers_. And after it is completed (you might need to refresh your browser to see it update) you can unfold the task and see the OOIs it has created. One of those should be our Greeting OOI.

To see the Greeting object we can go to the tab _Objects_ and look for the object with the type _Greeting_. If you click it we can see the information of this particular object.

That is it for the normalizer, our next step is to look for our Greeting OOI and create a _Finding_ for it. With findings, we can create reports.

## Creating a bit

Next, we want to look for our Greeting OOI and generate a finding from this once it has been added. Since findings are also an OOI, that means we want to generate OOIs from OOIs. This is the job for a bit. A bit consumes OOIs and generates other OOIs from it.

To start creating a bit create a folder inside _octopoes/bits/_ called _check_greeting_. This folder will contain the information about our bit. Inside this folder we need to have the following files:

- \_\_init\_\_.py
- bit.py
- check_greeting.py

### \_\_init\_\_.py

This file stays empty and is required for Python.

### bit.py

Inside this file, we write information about our bit. Here we give information such as the id of our bit, what OOI our bit should look out for, other OOIs that our bit requires (which are related to the OOI the bit is looking out for such as the IpAddress contained inside our Greeting OOI) and the path to the module that runs the bit (in our example this will be _bits.check_greeting.check_greeting_.)

This is what our _bit.py_ would look like:

```python
from bits.definitions import BitDefinition, BitParameterDefinition
from octopoes.models.ooi.greeting import Greeting

BIT = BitDefinition(
    id="check-greeting",
    consumes=Greeting,
    parameters=[],
    module="bits.check_greeting.check_greeting",
)
```

You can see inside _parameters_ that we have given it a new object. This object gives us access to OOIs that are related to the OOI referenced in _consumes_. In our example, we do not have a solid reason to do this.

### check_greeting.py

This is the file where the bit's meowgic happens. This file has to contain a run method which accepts the following:

- the model specified inside the _bit.py_'s _consumes_ parameter
- additional OOIs that have been specified inside the _bit.py_'s _parameters_ parameter
- a dictionary which contains some config

This function returns an Iterator of OOIs. The OOIs that we will return have to do with the _Finding_ type. This is a special OOI that is not displayed in openKAT's Objects tab and instead gets displayed in the Findings tab. This finding contains information such as the name and description of the finding, the severity (how impactful it is that the cause of this finding exists) and the recommendation to the user on what the user should do in this situation.

For our case, we will make a simple Finding that will signal to the user that a Greeting OOI has been sighted in the database. This Finding will have a severity level of recommendation this is the lowest of the severity levels. The severity order goes from recommendation to critical like this:

- recommendation
- low
- medium
- high
- critical

In our code, we will first create the type of finding and then we will create the finding and give more information about the current finding inside the description. This is what our file could look like:

```python
from collections.abc import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.greeting import Greeting

def run(
    input_ooi: Greeting,
    additional_oois: list,
    config: dict,
) -> Iterator[OOI]:
    greeting_text = input_ooi.greeting
    address = input_ooi.address

    kat = KATFindingType(id="KAT-GREETING")
    yield kat
    yield Finding(
        finding_type=kat.reference,
        ooi=input_ooi.reference,
        description=f"We have received a greeting: {greeting_text} because of address: {str(address)}.",
    )
```

After this file is created all we have to do is create a finding type of _KAT-GREETING_ that contains the information about the finding. This is done inside _boefjes/boefjes/plugins/kat_kat_finding_types/kat_finding_types.json_. Inside this file, we can add a new object called _KAT-GREETING_ which will contain information about our findings.

We will add the following object to this file:

```json
"KAT-GREETING": {
    "description": "A greeting object has been found.",
    "risk": "recommendation",
    "impact": "This has no impact except for the fact that it uses space in the database.",
    "recommendation": "Ignore this finding, it is only for learning purposes."
}
```

After all of this is done, we can run `run kat` and refresh our OpenKAT page. Now our bit should automatically run. But if it takes too long. We can go into the Settings tab and press the _Rerun all bits_ button. After a small delay, we can go to the Findings tab and see our Findings of each Greeting object. If it is... then congratulations! Our Bit is finally working! The last step to complete the introduction is enabling the user to create a report with our findings!

## Creating a report

If you go into the Reports tab you should be able to see our URL where we set our clearance level to L2 under the header _Select objects_. This is because by default openKAT only displays OOIs in this list with a clearance level of L2 and higher. We can fix this by pressing the _Show filter options_ button and then checking the L1 checkbox and checking the _Inherited_ box as well (since the clearance level of our OOI got inherited) to include our Greeting OOIs in this list as well. After pressing the _Set filters_ button we should be able to see our Greeting OOI in the list as well. When you do, you can check one of our Greeting OOIs and at the bottom press the _Continue with selection_ button.

When you press this, the only option you will see is to go back since there is no report type for our Greeting OOI yet. Let's create one!

First, we will once again make a new folder inside _rocky/reports/report_types_ called _greetings_report_. And inside of here, we will create 3 more files:

- \_\_init\_\_.py
- report.py
- report.html

### \_\_init\_\_.py

This file stays empty and is required for Python.

### report.py

Inside this file, we will parse the data from the findings into our html. This file has to contain a class inheriting from _reports.report_types.definitions.Report_ and requires a method that will generate data for our _report.html_. For this example, we will use the _generate_data_ function which has a reference to our OOI.

We also have to overwrite some attributes of the class to give information about what kind of report it should be. The attributes that we have to assign are:

- id
- name, which will be used to display the report type (encapsulated by _gettext_lazy_ from the Django package.)
- description, which will be used to explain to the user what kind of report will be generated (encapsulated by _gettext_lazy_ from the Django package.)
- plugins, which will tell the user what other plugins (mainly boefjes) are recommended to be enabled when generating this report. (in our case there will be none)
- input_ooi_types, which is a set containing the Models this report "consumes".
- template_path, which will contain the path to our HTML document.

With that, we now have to return a dictionary that contains information to be used for our HTML report. Let's keep it simple and only return our OOI. This is what our file could look like:

```python
from datetime import datetime
from logging import getLogger
from typing import Any

from django.utils.translation import gettext_lazy as _

from octopoes.models.ooi.greeting import Greeting
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6
from reports.report_types.definitions import Report

logger = getLogger(__name__)


class GreetingsReport(Report):
    id = "greetings-report"
    name = _("Greetings report")
    description = _("Makes a nice report about the selected greeting objects")
    plugins = {"required": [], "optional": []}
    input_ooi_types = {Greeting, IPAddressV4, IPAddressV6}
    template_path = "greetings_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> dict[str, Any]:
        return {"input_ooi": input_ooi}
```

### report.html

Inside this file, we create a template of how our report should look like. This HTML file makes use of the [Django template language](https://docs.djangoproject.com/en/5.0/ref/templates/language/#the-django-template-language). In our example we will make a very simple, bare-bones page that displays our information. The return value of _GreetingReport_'s _generate_data_ is contained in a variable called _data_, this is where we can get our information from. This is what our file could look like:

```html
<section id="greeting">
  <div>
    <h2>Greeting report</h2>
    <p>{{ data.input_ooi }}</p>
  </div>
</section>
```

After making these files we have to add our report to the list of report types. This is located inside _rocky/reports/report_types/helpers.py_ and inside here we can add our report to the list of reports called _REPORTS_.

After having done all that. The user should be able to create their own GreetingsReport! Let's try it out.

Let's go to the reports tab, and change our filters again so we can see our Greetings OOI. Check one of their boxes and press the _Continue with selection_ button. Now in the grid of available report types you can make, you should see 2 options. The Findings Report and the Greetings Report. Let's check them both and press once more on the _Continue with selection_ button. Now you will see a report that includes both the Findings Report and the Greetings report inside a single web page. In the top right, you can press the _Export_ button which will make a pdf of your report. Including information about every finding of your project.

## Conclusion

If everything looks correct, then you have just created your very first boefje, normalizer, model, bit and report! Hopefully, this has successfully taught you how you can create plugins on OpenKAT to more efficiently test networks.
