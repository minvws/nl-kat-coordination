================================
Chapter V03 - Session Management
================================

Chapter "V02 - Authentication" of ASVS is about making sure only the right people get access to your application.
It helps you use the best methods to identify users and verify that they are who they say they are.

.. mermaid::

    flowchart LR
        rectId["iSDP: Chapter V03 - Session Management"] --> n1["Gebruik je gebruikersaccounts in je applicatie?"]
        n1 -- Ja --> n2["V3.1<br>V3.2<br>V3.3<br>V3.4<br>V3.7"]
        n1 -- Nee --> n3["V3.1<br>V3.4"]

        n1@{ shape: decision}
        rectId:::Aqua
        rectId:::Sky
        n1:::Pine
        n2:::Pine
        n3:::Rose
        classDef Pine stroke-width:1px, stroke-dasharray:none, stroke:#254336, fill:#27654A, color:#FFFFFF
        classDef Rose stroke-width:1px, stroke-dasharray:none, stroke:#FF5978, fill:#FFDFE5, color:#8E2236
        classDef Aqua stroke-width:1px, stroke-dasharray:none, stroke:#46EDC8, fill:#DEFFF8, color:#378E7A
        classDef Sky stroke-width:1px, stroke-dasharray:none, stroke:#374D7C, fill:#E2EBFF, color:#374D7C
        style n1 stroke:#00C853

|todo| 3.1.1 Verify the application never reveals session tokens in URL parameters
----------------------------------------------------------------------------------

Discuss with team, is a finding done in Pentest or do we know a case?

|compliant| 3.2.1 Verify the application generates a new session token on user authentication
---------------------------------------------------------------------------------------------

As can be deduced from the entropy a new session token is generated on authentication.

To extra verify this a login was performed twice resulting in two different session tokens. yf6qycnuy4jauyd0dpwrjqarplr9t3w4 and huz609obui44zwwlxqkdkiq0ha35qab7

|compliant| 3.2.2 Verify that session tokens possess at least 64 bits of entropy
--------------------------------------------------------------------------------

Using BurpSuite Sequencer, we can see that the sessionid cookie has an entropy of 144+ bits and the csrftoken cookie has an entropy of 151+ bits.

|compliant| 3.2.3 Verify the application only stores session tokens in the browser using secure methods such as appropriately secured cookies
---------------------------------------------------------------------------------------------------------------------------------------------

We use session cookies to store the session.

=========== ========== ======================= ========== ======== ======== ======== ======= ======== ======== ========
is_session  name       used for                domain     path     expires  HttpOnly Secure  SameSite __HOST   Entropy
=========== ========== ======================= ========== ======== ======== ======== ======= ======== ======== ========
True        sessionid  User session management DOMAIN     \/       1 hour   True     True    Strict   False    144+
False       csrftoken  CSRF protection         DOMAIN     \/       1 day    False*   True    Strict   False    151+
=========== ========== ======================= ========== ======== ======== ======== ======= ======== ======== ========

\* needed to be called by JavaScript.

It can be deduced from these settings that HTTP cookies are appropriately secured.

|compliant| 3.3.1 Verify that logout and expiration invalidate the session token, such that the back button or a downstream relying party does not resume an authenticated session, including across relying parties
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

On logout a request is performed to ``/en/logout/`` which invalidates the session token. This is confirmed by checking the sessionid cookie in BurpSuite.

|todo| 3.3.2 If authenticators permit users to remain logged in, verify that re-authentication occurs periodically both when actively used or after an idle period
------------------------------------------------------------------------------------------------------------------------------------------------------------------

Discuss


|compliant| 3.4.1 Verify that cookie-based session tokens have the 'Secure' attribute set
-----------------------------------------------------------------------------------------

Cookies are configured with the following default settings:

=========== ========== ======================= ========== ======== ======== ======== ======= ======== ======== ========
is_session  name       used for                domain     path     expires  HttpOnly Secure  SameSite __HOST   Entropy
=========== ========== ======================= ========== ======== ======== ======== ======= ======== ======== ========
True        sessionid  User session management DOMAIN     \/       1 hour   True     True    Strict   False    144+
False       csrftoken  CSRF protection         DOMAIN     \/       1 day    False*   True    Strict   False    151+
=========== ========== ======================= ========== ======== ======== ======== ======= ======== ======== ========

|compliant| 3.4.2 Verify that cookie-based session tokens have the 'HttpOnly' attribute set
-------------------------------------------------------------------------------------------

Cookies are configured with the following default settings:

=========== ========== ======================= ========== ======== ======== ======== ======= ======== ======== ========
is_session  name       used for                domain     path     expires  HttpOnly Secure  SameSite __HOST   Entropy
=========== ========== ======================= ========== ======== ======== ======== ======= ======== ======== ========
True        sessionid  User session management DOMAIN     \/       1 hour   True     True    Strict   False    144+
False       csrftoken  CSRF protection         DOMAIN     \/       1 day    False*   True    Strict   False    151+
=========== ========== ======================= ========== ======== ======== ======== ======= ======== ======== ========

The csrftoken does not have the HttpOnly attribute set, because it is needed to be called by JavaScript.

|compliant| 3.4.3 Verify that cookie-based session tokens utilize the 'SameSite' attribute to limit exposure to cross-site request forgery attacks
--------------------------------------------------------------------------------------------------------------------------------------------------

Cookies are configured with the following default settings:

=========== ========== ======================= ========== ======== ======== ======== ======= ======== ======== ========
is_session  name       used for                domain     path     expires  HttpOnly Secure  SameSite __HOST   Entropy
=========== ========== ======================= ========== ======== ======== ======== ======= ======== ======== ========
True        sessionid  User session management DOMAIN     \/       1 hour   True     True    Strict   False    144+
False       csrftoken  CSRF protection         DOMAIN     \/       1 day    False*   True    Strict   False    151+
=========== ========== ======================= ========== ======== ======== ======== ======= ======== ======== ========

As can be seen, SameSite is set to Strict for both cookies.

|non_compliant| 3.4.4 Verify that cookie-based session tokens use the "__Host-" prefix so cookies are only sent to the host that initially set the cookie
---------------------------------------------------------------------------------------------------------------------------------------------------------

At the moment to OpenKAT cookies do not use the __Host- prefix.

|compliant| 3.4.5 Verify that if the application is published under a domain name with other applications that set or use session cookies that might disclose the session cookies, set the path attribute in cookie-based session tokens using the most precise path possible
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Cookies are not published under a domain name with other applications.

|todo| 3.7.1 Verify the application ensures a full, valid login session or requires re-authentication or secondary verification before allowing any sensitive transactions or account modifications
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

The only allowed account modification is blocking or unblocking an account. No re-authentication is required for this.

Will be discussed in: TDODO

.. |compliant| image:: img/compliant.svg
.. |non_compliant| image:: img/non_compliant.svg
.. |partial_compliant| image:: img/partial_compliant.svg
.. |todo| image:: img/todo.svg
.. |accepted| image:: img/accepted.svg
