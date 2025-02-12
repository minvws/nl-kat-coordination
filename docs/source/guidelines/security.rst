Security
########

The OpenKAT project is committed to providing a secure environment.
As a security product ourselves, we take security seriously and strive to be transparent about our security posture.

Security in the pipeline
=========================

The OpenKAT project uses a variety of tools to ensure the security of the codebase. These include:

SCA
---

To scan for vulnerabilities in our code base and keep dependencies up-to-date, we use Dependabot, a tool for automated dependency updates built into Github.
This tool scans the code base for outdated components and vulnerabilities, and creates a pull request to update the dependencies.
This way we can ensure that the code base is up to date and secure.

SAST
----

To scan for Security Hotspots in our code base we use the built-in tool from Github, CodeQL and SonarQube Cloud.

**CodeQL**

We have enabled the ``security-extended`` option which may cause some more false positives but also gives a better insight into possible security risks.

The following languages are enabled within our CodeQL scan:

- Python
- JavaScript / TypeScript
- GitHub Actions

**SonarQube Cloud**

SonarQube Cloud is used to scan for the code quality, it also looks for Security Hotspots, which are lines of code that may contain vulnerabilities.

Secret scanning
---------------

To prevent secrets from being exposed in the code base we use the built-in tool from Github, Secret scanning. There is currently no check on the pre-commit for secrets.

DAST
----

We currently do not have a DAST tool in place, but we are looking into the possibilities to implement this in the future.

Security of the application
===========================

Modern browser have many security features build in that can be enabled by sending the correct headers or setting configuration settings. 
To allow this OpenKAT is designed to support these settings.
Below is an overview the design choices and best practices that can be used when configuring OpenKAT.

Security headers
----------------

For the security headers settings, see the hardening page, which can be found at: :ref:`installation-and-deployment/hardening:Security headers`.

Security cookies
----------------

To make sure cookies are secure we follow best practices from the OWASP ASVS standard.

Our cookies are:

=========== ========== ======================= ========== ======== ======== ======== ======= ======== ======== ========
is_session  name       used for                domain     path     expires  HttpOnly Secure  SameSite __HOST   Entropy
=========== ========== ======================= ========== ======== ======== ======== ======= ======== ======== ========
True        sessionid  User session management DOMAIN     /        1 hour   True     True    Strict   False    144+
False       csrftoken  CSRF protection         DOMAIN     /        1 day    False*   True    Strict   False    151+
=========== ========== ======================= ========== ======== ======== ======== ======= ======== ======== ========

\* needed to be called by JavaScript.
\+ Determined with BurpSuite Sequencer.

iRealisate Secure Development Path (iSDP)
=========================================

At the Ministerie van Volksgezondheid, Welzijn en Sport (VWS) we use the iRealisate Secure Development Path (iSDP) to ensure that the code we write is secure.
It is based on the OWASP ASVS standard. When completed the results will be shared on this documentation page.

