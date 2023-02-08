==========================
Developer or local install
==========================

**Important:** The version of OpenKAT you are about to install is a **development environment**, which is used by the developers to build OpenKAT. This is not a version that would be used in a production environment, and it requires some knowledge about Linux, compiling software, and Docker.

make kat
========

Install OpenKAT on your own machine with ``make kat`` or ``make kat-stable``. KAT-stable, as the name implies, is the last major release. If you want to deploy OpenKAT in a production environment use the hardening settings as well.

Requirements
------------

You need the following things to install OpenKAT:

- A computer with a Linux installation. In this document we use Ubuntu, but on many other distributions it works in a similar way. Later we will also add instructions for macOS.
- Docker. If you don't already have this, install it first.

- OpenKAT's `GitHub repository <https://github.com/minvws/nl-kat-coordination/>`_.

Before installing
-----------------

Install Docker
**************

OpenKAT is installed in Docker, and therefore Docker must be installed first. The preferred method of installation is through a repository.

OpenKAT requires a newer version of Docker than what is available in the default ubuntu and debian repositories. That is why you should always use Docker's repository. On the `Docker Engine installation overview <https://docs.docker.com/engine/install/>`_ page you can find links to installation pages for all major Linux distributions. For a specific example using the Docker repository on Debian, see `Debian install using the repository <https://docs.docker.com/engine/install/debian/#install-using-the-repository>`_. The installation pages for the other Linux distributions contain similar instructions.

**Important:** Please follow the post-installation steps as well! You can find them here: `Docker Engine post-installation steps <https://docs.docker.com/engine/install/linux-postinstall/>`_.

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

Front end
*********

Find the frontend of your OpenKAT install at port 8000 or 8443 of your localhost and follow the 'on boarding flow' to test your setup and start using your development setup of OpenKAT.

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
