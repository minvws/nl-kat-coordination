=============================
Debugging and troubleshooting
=============================


Checking the health status of the KAT modules
=============================================

In the footer of every page, you can find a link to the health page.
This page shows the status of all containerized KAT modules, their version, and any self-reported warnings or errors.
If you KAT deployment is not working properly, this is the first place to check.

If you see any errors or warnings, please check the logs of the affected module.

You can also access the health JSON endpoint programmatically at ``http<s>://<rocky-host>/<org-code>/health``.
