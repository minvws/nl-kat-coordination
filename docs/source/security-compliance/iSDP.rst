=============================================
iRealisatie Secure Development Pathway (iSDP)
=============================================

The iRealisatie Secure Development Pathway (`iSDP <https://github.com/minvws/rdo-isdp/tree/main>`_) is a pathway based on the OWASP ASVS 4.0.3 (Application Security Verification Standard).
The ASVS aims to provide a framework for improving the security of web applications by offering a detailed checklist of security requirements.
It serves as a security manual that helps developers and product owners understand what they should aim for to keep their applications secure.

Chapter V02 - Authentication
============================
Chapter "V02 - Authentication" of ASVS is about making sure only the right people get access to your application.
It helps you use the best methods to identify users and verify that they are who they say they are.

.. mermaid::

    flowchart LR
        rectId["iSDP: Chapter V02 - Authentication"] --> n1["Beheer je gebruikersaccount in je applicatie?"]
        n1 -- Ja --> n2["V2.1<br>V2.5"]
        n1 -- Nee --> n3["Skip V02"]
        n2 --> n4["Gebruik je een authenticator in je applicatie?"]
        n4 -- Ja --> n5["V2.2<br>V2.3<br>V2.7<br>V2.8"]
        n4 -- Nee --> n6["Implementeer 2FA met authenticator"]

        n1@{ shape: decision}
        n4@{ shape: decision}
        n1:::Pine
        n2:::Pine
        n3:::Rose
        n4:::Aqua
        n4:::Pine
        n5:::Rose
        n6:::Pine
        classDef Aqua stroke-width:1px, stroke-dasharray:none, stroke:#46EDC8, fill:#DEFFF8, color:#378E7A
        classDef Pine stroke-width:1px, stroke-dasharray:none, stroke:#254336, fill:#27654A, color:#FFFFFF
        classDef Rose stroke-width:1px, stroke-dasharray:none, stroke:#FF5978, fill:#FFDFE5, color:#8E2236
        style n1 stroke:#00C853

2.1.1 - Verify that user set passwords are at least 12 characters in length (after multiple spaces are combined).
-----------------------------------------------------------------------------------------------------------------

PROOF TODO

2.1.2 - Verify that passwords of at least 64 characters are permitted, and that passwords of more than 128 characters are denied.
---------------------------------------------------------------------------------------------------------------------------------

PROOF TODO

2.1.3 - Verify that password truncation is not performed. However, consecutive multiple spaces may be replaced by a single space.
---------------------------------------------------------------------------------------------------------------------------------

PROOF TODO

2.1.4 - Verify that any printable Unicode character, including language neutral characters such as spaces and Emojis are permitted in passwords.
------------------------------------------------------------------------------------------------------------------------------------------------

PROOF TODO

2.1.5 - Verify users can change their password.
-----------------------------------------------

PROOF TODO

2.1.6 - Verify that password change functionality requires the user's current and new password.
-----------------------------------------------------------------------------------------------

PROOF TODO

2.1.7 - Verify that passwords submitted during account registration, login, and password change are checked against a set of breached passwords either locally (such as the top 1,000 or 10,000 most common passwords which match the system's password policy) or using an external API. If using an API a zero knowledge proof or other mechanism should be used to ensure that the plain text password is not sent or used in verifying the breach status of the password. If the password is breached, the application must require the user to set a new non-breached password.
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

PROOF TODO

2.1.8 - Verify that a password strength meter is provided to help users set a stronger password.
------------------------------------------------------------------------------------------------

PROOF TODO

2.1.9 - Verify that there are no password composition rules limiting the type of characters permitted. There should be no requirement for upper or lower case or numbers or special characters.
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
PROOF TODO

2.1.10 - Verify that there are no periodic credential rotation or password history requirements.
------------------------------------------------------------------------------------------------
PROOF TODO

2.1.11 - Verify that "paste" functionality, browser password helpers, and external password managers are permitted.
-------------------------------------------------------------------------------------------------------------------
PROOF TODO

2.1.12 - Verify that the user can choose to either temporarily view the entire masked password, or temporarily view the last typed character of the password on platforms that do not have this as built-in functionality.
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
PROOF TODO

2.5.1 - Verify that a system generated initial activation or recovery secret is not sent in clear text to the user.
-------------------------------------------------------------------------------------------------------------------

PROOF TODO

2.5.2 - Verify password hints or knowledge-based authentication (so-called "secret questions") are not present.
---------------------------------------------------------------------------------------------------------------

PROOF TODO

2.5.3 - Verify password credential recovery does not reveal the current password in any way.
--------------------------------------------------------------------------------------------

PROOF TODO

2.5.4 - Verify shared or default accounts are not present (e.g. "root", "admin", or "sa").
-------------------------------------------------------------------------------------------

PROOF TODO

2.5.5 - Verify that if an authentication factor is changed or replaced, that the user is notified of this event.
----------------------------------------------------------------------------------------------------------------

PROOF TODO

2.5.6 - Verify forgotten password, and other recovery paths use a secure recovery mechanism, such as time-based OTP (TOTP) or other soft token, mobile push, or another offline recovery mechanism.
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

PROOF TODO
