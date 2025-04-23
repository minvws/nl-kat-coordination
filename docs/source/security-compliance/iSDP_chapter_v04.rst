================================
Chapter V04 - Access Control
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

|todo| 4.1.1 Verify that the application enforces access control rules on a trusted service layer, especially if client-side access control is present and could be bypassed
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Discuss with team. Where is this step perofrmed?

Pentest?

Matrix https://docs.openkat.nl/basics/users-and-organisations.html#rights-and-functions-per-user-type

.. |compliant| image:: img/compliant.svg
.. |non_compliant| image:: img/non_compliant.svg
.. |partial_compliant| image:: img/partial_compliant.svg
.. |todo| image:: img/todo.svg
.. |accepted| image:: img/accepted.svg
