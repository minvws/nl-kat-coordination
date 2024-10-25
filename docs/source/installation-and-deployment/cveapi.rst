=======
CVE API
=======

OpenKAT will request information about CVE's from https://cve.openkat.dev. It is
possible to run your own instance in case you don't want to rely on third party
service for this. The kat-cveapi Debian package that can be downloaded from
`GitHub <https://github.com/minvws/nl-kat-coordination/releases/latest>`__ can
be used for this.

The package has a script that will download all the CVE information to the
``/var/lib/kat-cveapi`` directory. The package includes a systemd timer that will
run the script after the package is installed and hourly to keep the CVE
information up-to-date. The ``/var/lib/kat-cveapi`` can then be served as static
files by your webserver. Example nginx configuration that is used by
https://cve.openkat.dev/:

.. code-block:: sh

    server {
        listen   [::]:443;

        server_name cve.openkat.dev;

        ssl_certificate /etc/letsencrypt/live/openkat.dev/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/openkat.dev/privkey.pem;

        access_log /var/log/nginx/cve/access.log;
        error_log /var/log/nginx/cve/error.log;

        root /var/lib/kat-cveapi;
    }

The CVEAPI_URL configuration parameter of the kat_cve_finding_types boefje can
then be set to your own instance.
