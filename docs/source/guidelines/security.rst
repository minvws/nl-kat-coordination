Security
########

The OpenKAT project is committed to providing a secure environment.
As a security product ourselves, we take security seriously and strive to be transparent about our security posture.

Security in the pipeline
=========================

The OpenKAT project uses a variety of tools to ensure the security of the coWdebase. These include:

SCA
---

To scan for vulnerabilities in our code base we use the built-in tool from Github, Dependabot.
This tool scans the code base for outdated components and vulnerabilities, and creates a pull request to update the dependencies.
This way we can ensure that the code base is up to date and secure.

SAST
----

To scan for code smells in our code base we use the built-in tool from Github, CodeQL.
We have enabled the ``security-extended`` option which may cause some more false positives but also gives a better insight into possible security risks.

The following languages are enabled within our CodeQL scan:

- Python
- JavaScript / TypeScript
- Github Actions

As an addition we also use SonarQube Cloud to scan for the code quality and as part of that it also scans for security hotspots.

Secret scanning
---------------

To prevent secrets from being exposed in the code base we use the built-in tool from Github, Secret scanning. There is currently no check on the pre-commit for secrets.

DAST
----

We currently do not have a DAST tool in place, but we are looking into the possibilities to implement this in the future.
