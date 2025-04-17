===========
Quick start
===========

Installation
************
This quick start guides will help you to get OpenKAT started on Ubuntu using the Docker setup. The steps below were performed on a clean Ubuntu 22.04 LTS virtual machine. This quick start assumes you have a working Ubuntu installation ready. Please note that these steps help you to setup a playground/developer environment for OpenKAT, this means you should not use it as a production environment. If you do, you do so at your own risk.

Do *not* install Docker directly from the default Ubuntu repositories. This version is older and OpenKAT generally uses newer features. Using the Ubuntu repository version will likely break your OpenKAT install (at some point).

#. Follow the Docker installation steps as mentioned here: `Docker Ubuntu Installation steps <https://docs.docker.com/engine/install/ubuntu/#installation-methods>`_. This tutorial followed the installation steps using the `apt` repository. Make sure that you can run the `hello-world` Docker image.

#. Follow the Post-installations steps as described here: `Docker Post-installation steps <https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user>`_. Make sure that the Docker `hello-world` image can run as a normal (non-root) user.

#. Install missing Ubuntu packages.

.. code-block:: sh

    sudo apt install make
..

#. Clone the OpenKAT repository to a location of your choice as shown below.

.. code-block:: sh

    $ git clone https://github.com/minvws/nl-kat-coordination.git
..

#. Change into the cloned repository.

.. code-block:: sh

    $ cd nl-kat-coordination/
..

#. Create the environment file and run kat.

.. code-block:: sh

    $ make env
    $ make kat
..

#. Pet your cat while you wait for all the containers to be built.

#. Get your password from the `.env` file. An example of what this looks like is shown below.

.. code-block:: sh

    $ cat .env | grep DJANGO
    DJANGO_SUPERUSER_PASSWORD=83d0ddac75c3fed23d2fc3a607affe432f9916d0f9dcc12680
..

#. Open your browser and go to: `http://localhost:8000/en/login`. Login using the username `superuser@localhost` and the password that you found using the previous step (everything after the equal sign `=`).

#. Meowlations! You just installed OpenKAT. As this is your first time using OpenKAT, you will have to walk through the onboarding. This is explained further below.

Onboarding
**********

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
