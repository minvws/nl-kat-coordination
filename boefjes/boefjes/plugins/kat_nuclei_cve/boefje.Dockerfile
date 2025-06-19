FROM openkat/boefje-base:latest

ARG OCI_IMAGE=ghcr.io/minvws/openkat/nuclei-cve:latest
ENV OCI_IMAGE=$OCI_IMAGE

COPY --from=projectdiscovery/nuclei:v3.2.4 /usr/local/bin/nuclei /usr/local/bin/

COPY ./boefjes/plugins/kat_nuclei_cve ./kat_nuclei_cve
