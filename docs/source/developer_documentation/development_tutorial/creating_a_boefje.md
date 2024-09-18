# Creating a Boefje

There are two ways to create a Boefje. The first is to create a Boefje with the User Interface (UI). The second option is to create it in the backend.

## Boefje variants

Boefje variants are Boefjes that use the same container image. In OpenKAT, all Boefjes with the same container image will be seen as 'variants' of each other and will be shown together on those Boefje detail pages.

## Creating a Boefje (variant) in the User Interface

**Note:** Currently, only admins are able to create Boefjes in the UI.

To create a **new** Boefje, go to the KAT-alogus. Here you will find the _'Add Boefje'_ button.
To create a **variant** of an existing Boefje, go to the Boefje detail page of the Boefje you would like to use as a template and press the _'Add variant'_ button.

### Set up your Boefje

You will be directed to the Setup page, where you can configure your Boefje. The following items can be filled in:

| Field             | Required | Explanation                                                                                                                                                                                                                                                                                                                             |
| ----------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Container image   | Yes      | The name of the Docker image. For example: _'ghcr.io/minvws/openkat/nmap'_                                                                                                                                                                                                                                                              |
| Name              | Yes      | Give your Boefje a suitable name. This name will be visible in the KAT-alogus.                                                                                                                                                                                                                                                          |
| Description       | No       | A description of the Boefje explaining in short what it can do. This will both be displayed inside the KAT-alogus and on the Boefje details page.                                                                                                                                                                                       |
| Arguments         | No       | For example: _'-sTU --top-ports 1000'_                                                                                                                                                                                                                                                                                                  |
| Json Schema       | No       | If any other settings are needed for your Boefje, add these as a JSON Schema, otherwise, leave the field empty or 'null'. This JSON is used as the basis for a form for the user. When the user enables this Boefje they can get the option to give extra information. For example, it can contain an API key that the script requires. |
| Input object type | No       | Select the object type(s) that your Boefje consumes.                                                                                                                                                                                                                                                                                    |
| Output mime-types | No       | Add a set of mime-types that are produced by this Boefje, separated by commas. For example: _'text/html'_, _'image/jpeg'_ or _'boefje/{boefje-id}'_. These output mime-types will be shown on the Boefje detail page as information for other users.                                                                                    |
| Clearance level   | No       | Select a clearance level for your Boefje, which indicates the clearance level the OOI's need before your Boefje will be scheduled on them.                                                                                                                                                                                              |

### Using your Boefje

After finishing the setup and creating your Boefje, you can view it in the KAT-alogus for All Organizations in your OpenKAT-install. The Boefje detail page will show you all the detailed information about your newly created Boefje. Both on the KAT-alogus as on the Boefje detail page, you can enable or disable your Boefje.

### Updating your Boefje

To update your Boefje, you go to the _'Variants'_ section on the Boefje detail page. Expand the table row of the Boefje you want to change and press the _'Edit Boefje'_ button.

## Creating a boefje in the code

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

### `__init__.py`

This file stays empty.

### `boefje.json`

This file contains information about our boefje. For example, this file contains information about what OOIs our boefje should be looking out for. Here is the example we will be using:

```json
{
  "id": "hello-katty",
  "name": "Hello Katty",
  "description": "A simple boefje that can say hello",
  "consumes": ["IPAddressV4", "IPAddressV6"],
  "scan_level": 0,
  "oci_image": "openkat/hello-katty"
}
```

- **`id`**: A unique identifier for the boefje.
- **`name`**: A name to display in the KAT-alogus.
- **`description`**: A description in the KAT-alogus.
- **`consumes`**: A list of OOI types that trigger the boefje to run. Whenever one of these OOIs gets added, this boefje will run with that OOI. In our case, we will run our boefje whenever a new IPAddressV4 or IPAddressV6 gets added.
- **`scan_level`**: A scan level that decides how intrusively this boefje will scan the provided OOIs. Since we will not make any external requests our boefje will have a scan level of 0.
- **`oci_image`**: The name of the docker image that is provided inside `boefjes/Makefile`

### `cover.jpg`

This file has to be an image of the developer's cat. This image will be used as a thumbnail for the boefje.

### `description.md`

This file contains a description of the boefje to explain to the user what this boefje does. For this example we can leave this empty.

### `schema.json`

To allow the user to pass information to a boefje runtime, add a schema.json file to the folder where your boefje is located.
This can be used, for example, to add an API key that the script requires.
It must conform to the https://json-schema.org/ standard, for example:

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

This JSON defines which additional environment variables can be set for the boefje.
There are two ways to do this.
Firstly, using this schema as an example, you could set the `BOEFJE_MESSAGE` environment variable in the boefje runtime.
Prepending the key with `BOEFJE_` provides an extra safeguard.
Note that setting an environment variable means this configuration is applied to _all_ organisations.
Secondly, if you want to avoid setting environment variables or configure it for just one organisation,
it is also possible to set the API key through the KAT-alogus.
Navigate to the boefje detail page of Shodan to find the schema as a form.
These values take precedence over the environment variables.
This is also a way to test whether the schema is properly understood for your boefje.
If encryption has been set up for the KATalogus, all keys provided through this form are stored encrypted in the database.

Although the Shodan boefje defines an API key, the schema could contain anything your boefje needs.
However, OpenKAT currently officially only supports "string" and "integer" properties that are one level deep.
Because keys may be passed through environment variables,
schema validation does not happen right away when settings are added or boefjes enabled.
Schema validation happens right before spawning a boefje, meaning your tasks will fail if is missing a required variable.

- `title`: This should always contain a string containing 'Arguments'.
- `type`: This should always contain a string containing 'object'.
- `description`: A description of the boefje explaining in short what it can do. This will both be displayed inside the KAT-alogus and on the boefje's page.
- `properties`: This contains a list of objects which each will show the KAT-alogus what inputs are requested from the user. This can range from requesting for an API-key to extra commands the boefje should run.
  Inside the `boefje.json` file, we specified 2 environment variables that will be used by this boefje.
  - `MESSAGE`: For this property we ask the user to send us a string which this boefje will use to create some raw data.
  - `NUMBER`: For this property we ask the user to send us an integer between 0 and 9.
- `required`: In here we need to give a list of the objects' names that the user has to provide to run our boefje. For this example, we will only require the user to give us the `MESSAGE` variable. We do this by adding `"MESSAGE"` to the `required` list.

### `main.py`

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

For ease of development, we added a generic finding normalizer. When we just want to create a CVE or other type of finding on the input OOI, we can return the CVE ID or KAT ID as a string with `openkat/finding` as mime-type.

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
