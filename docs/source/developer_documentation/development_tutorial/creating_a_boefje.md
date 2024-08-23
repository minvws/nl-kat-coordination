# Creating a boefje

Inside `boefjes/boefjes/plugins/` create a new folder with a name starting with `kat_` for this example we use `kat_hello_katty`

Inside this folder we need to have the following files:

```shell
$ tree boefjes/boefjes/plugins/kat_hello_katty/
├── __init__.py
├── boefje.json
├── cover.jpg
├── description.md
├── main.py
└── schema.json
```

## `__init__.py`

This file stays empty.

## `boefje.json`

This file contains information about our boefje. For example, this file contains information about what OOIs our boefje should be looking out for. Here is the example we will be using:

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

- **`id`**: A unique identifier for the boefje.
- **`name`**: A name to display in the KAT-alogus.
- **`description`**: A description in the KAT-alogus.
- **`consumes`**: A list of OOI types that trigger the boefje to run. Whenever one of these OOIs gets added, this boefje will run with that OOI. In our case, we will run our boefje whenever a new IPAddressV4 or IPAddressV6 gets added.
- **`environment_keys`**: A list of inputs provided by the user. More information about these inputs can be found in `schema.json`. OpenKAT also provides some environment variables.
- **`scan_level`**: A scan level that decides how intrusively this boefje will scan the provided OOIs. Since we will not make any external requests our boefje will have a scan level of 0.
- **`oci_image`**: The name of the docker image that is provided inside `boefjes/Makefile`

## `cover.jpg`

This file has to be an image of the developer's cat. This image will be used as a thumbnail for the boefje.

## `description.md`

This file contains a description of the boefje to explain to the user what this boefje does. For this example we can leave this empty.

## `schema.json`

This JSON is used as the basis for a form for the user. When the user enables this boefje they can get the option to give extra information. For example, it can contain an API key that the script requires.
This is an example of a `schema.json` file:

```json
{
  "title": "Arguments",
  "type": "object",
  "properties": {
    "MESSAGE": {
      "title": "Input text to give to the boefje",
      "type": "string",
      "description": "Some text so the boefje has some information to work with. Normally you could feed this an API key or a username."
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

- `title`: This should always contain a string containing 'Arguments'.
- `type`: This should always contain a string containing 'object'.
- `description`: A description of the boefje explaining in short what it can do. This will both be displayed inside the KAT-alogus and on the boefje's page.
- `properties`: This contains a list of objects which each will show the KAT-alogus what inputs are requested from the user. This can range from requesting for an API-key to extra commands the boefje should run.
  Inside the `boefje.json` file, we specified 2 environment variables that will be used by this boefje.
  - `MESSAGE`: For this property we ask the user to send us a string which this boefje will use to create some raw data.
  - `NUMBER`: For this property we ask the user to send us an integer between 0 and 9.
- `required`: In here we need to give a list of the objects' names that the user has to provide to run our boefje. For this example, we will only require the user to give us the `MESSAGE` variable. We do this by adding `"MESSAGE"` to the `required` list.

## `main.py`

This is the file where the boefje's meowgic happens. This file has to contain a run method that accepts a dictionary and returns a `list[tuple[set, bytes | str]]`.
This function will run whenever a new OOI gets created with one of the types mentioned in `consumes` inside `boefje.json`. :

Here is the example we will be using:

```python
import json
from os import getenv

def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    """Function that gets run to give a raw file for the normalizers to read from"""
    address = boefje_meta["arguments"]["input"]["address"]
    MESSAGE = getenv("MESSAGE", "ERROR")
    NUMBER = getenv("NUMBER", "0")

    # Check if NUMBER has been given, if it has not. Keep it at 0
    try:
        amount_of_cats = int(NUMBER)
    except _:
        amount_of_cats = 0

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

The most important part is the return value we send back. This is what will be used by our normalizer to create our new OOIs.

For ease of development, we added a generic finding normalizer. When we just want to create a CVE or other type of finding on the input OOI, we can return the CVE ID, CWE ID or KAT ID as a string with `openkat/finding` as mime-type.

---

The final task of creating a boefje is specifying what DockerFile our boefje should use. We can do this inside the file located in `boefjes/Makefile`.
Inside the `images` rule. We have to specify that we want to use `base.Dockerfile` since our boefje does not require any special packages to run. This is as simple as adding a single line. Here is what that would look like in our case:

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

This was the creation of our first boefje. If we run OpenKAT now we should be able to see this boefje sitting in the KAT-alogus. Let’s try it out!
