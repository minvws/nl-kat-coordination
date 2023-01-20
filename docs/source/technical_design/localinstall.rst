==========================
Developer or local install
==========================

make kat
========

Install OpenKAT on your own machine with ``make kat`` or ``make kat-stable``. KAT-stable, as the name implies, is the last major release. If you want to deploy OpenKAT in a production environment use the hardening settings as well.

Requirements
------------

You need the following things to install OpenKAT:

- A computer with a Linux installation. In this document we use Ubuntu, but on many other distributions it works in a similar way. Later we will also add instructions for macOS.
- Docker. If you don't already have this, install it first in Chapter 2.

- OpenKAT's `GitHub repository: <https://github.com/minvws/nl-kat-coordination/>`_

Before installing
-----------------

OpenKAT is installed in Docker, and therefore Docker must be installed first. Do this according to the instructions of your (Unix) operating system. You can read the instructions for Ubuntu below. On the `website of Docker <https://docs.docker.com/engine/install/>`_ you will see installation instructions for other distributions.

Docker install
**************

Open a terminal of your choice, such as gnome-terminal on Ubuntu.

- We won't assume you have older versions of Docker running, but if you do, you need to uninstall them with the following command:

.. code-block:: sh

	$ sudo apt-get remove docker docker-engine docker.io containerd runc yarnpkg

If apt-get does not run through because of missing packages, try the command again without the name that apt-get stumbled over.

- Then install some required packages that allow *apt* to use packages over HTTPS:

.. code-block:: sh

	$ sudo apt-get install apt-transport-https ca-certificates curl gnupg lsb-release

The packages are checked and updated as needed. If an installation is required, apt asks if you want to continue with the installation ("Do you want to continue?"). Type 'Y' and press enter.

-Next add Docker's official GPG key:

.. code-block:: sh

	$ curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
	$ echo  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null


- Update your packages and install the latest Docker version:

.. code-block:: sh

	$ sudo apt-get update
	$ sudo apt-get install docker-ce docker-ce-cli containerd.io
	$ sudo usermod -aG docker ${USER}


When asked if you want to continue the installation, type 'Y' again and press enter.

Install docker-compose
**********************

Install the latest version of docker-compose and give the tool appropriate permissions with the following two commands:

.. code-block:: sh

	$ sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
	$ sudo chmod +x /usr/local/bin/docker-compose


Install dependencies
********************

Dependencies are packages required for OpenKAT to work. Run the following commands to install them:


.. code-block:: sh

	$ curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
	$ sudo apt-get install -y nodejs gcc g++ make python3-pip docker-compose
	$ curl -sL https://dl.yarnpkg.com/debian/pubkey.gpg | gpg --dearmor | sudo tee /usr/share/keyrings/yarnkey.gpg >/dev/null
	$ echo "deb [signed-by=/usr/share/keyrings/yarnkey.gpg] https://dl.yarnpkg.com/debian stable main" | sudo tee /etc/apt/sources.list.d/yarn.list
	$ sudo apt-get update && sudo apt-get install yarn

Getting Started
---------------

Now the installation of OpenKAT can begin. We do this via git.

Default installation
*********************

- Clone the repository:

.. code-block:: sh

	$ git clone https://github.com/minvws/nl-kat-coordination.git

- Go to the folder:

.. code-block:: sh

	$ cd nl-kat-coordination

- Make KAT:

.. code-block:: sh

	$ make kat

Other options are "make clone" and "make pull" to either clone only or update the repositories. the above command performs this itself.

Currently, the make cat instruction only works for the first user on a ``*nix`` system. This is a known problem which will be solved soon. The current user must be user 1000. You can check this by executing `id`.

In some cases this may not work because Docker does not yet know your user name. You solve this with the following commands, entering your user name instead of $USER:

.. code-block:: sh

	$ sudo gpasswd -a $USER docker
	$ newgrp docker

Then OpenKAT is built, including all the parts such as Octopoes and Rocky.

Specific builds
***************

If you want to create a specific build, you have a number of options. You can also look in the `Makefile <https://github.com/minvws/nl-kat-coordination/blob/main/Makefile>`_. Below are some examples.

- Clone only relevant repositories

.. code-block:: sh

	$ make clone

- Start a separate container

.. code-block:: sh

	$ docker-compose up --build -d {container_name}

 Set up a superuser with custom credentials (fill in the parameters as preferred for your installation)


By default a user named 'admin', with the password 'admin' should be available.

- Optional seed of the database with OOI information

.. code-block:: sh

	$ docker exec -it nl-kat-coordination_rocky_1 python3 /app/rocky/manage.py loaddata OOI_database_seed.json

- install octopus-core in your local python environment with a symlink (after cloning)

.. code-block:: sh

	$ pip install -e nl-kat-coordination-octopoes-core

Updates
-------

Updating an existing installation can be done with the new make update.

Go to the directory containing openkat:

.. code-block:: sh

	$ cd nl-kat-coordination
	$ make update

Create a new superuser for the new version. You can delete the old superuser after the update. This is not pretty, but has the advantage that your databases remain intact. Check that you are on the most recent version everywhere, especially Rocky sometimes hangs because of yarn.lock.
