FROM python:3.11-slim

ENV PATH=/home/nonroot/.local/bin:${PATH}
WORKDIR /app
RUN adduser --disabled-password --gecos '' nonroot

COPY boefjes/plugins/kat_dns boefjes/plugins/kat_dns
COPY boefjes/plugins/kat_snyk boefjes/plugins/kat_snyk
COPY boefjes/plugins/kat_binaryedge boefjes/plugins/kat_binaryedge
COPY boefjes/plugins/kat_censys boefjes/plugins/kat_censys
COPY boefjes/plugins/kat_crt_sh boefjes/plugins/kat_crt_sh
COPY boefjes/plugins/kat_cve_2023_34039 boefjes/plugins/kat_cve_2023_34039
COPY boefjes/plugins/kat_cve_2023_35078 boefjes/plugins/kat_cve_2023_35078
COPY boefjes/plugins/kat_dicom boefjes/plugins/kat_dicom
COPY boefjes/plugins/kat_dns_version boefjes/plugins/kat_dns_version
COPY boefjes/plugins/kat_dns_zone boefjes/plugins/kat_dns_zone
COPY boefjes/plugins/kat_external_db boefjes/plugins/kat_external_db
COPY boefjes/plugins/kat_fierce boefjes/plugins/kat_fierce
COPY boefjes/plugins/kat_green_hosting boefjes/plugins/kat_green_hosting
COPY boefjes/plugins/kat_leakix boefjes/plugins/kat_leakix
COPY boefjes/plugins/kat_rdns boefjes/plugins/kat_rdns
COPY boefjes/plugins/kat_security_txt_downloader boefjes/plugins/kat_security_txt_downloader
COPY boefjes/plugins/kat_service_banner boefjes/plugins/kat_service_banner
COPY boefjes/plugins/kat_shodan boefjes/plugins/kat_shodan
COPY boefjes/plugins/kat_webpage_analysis boefjes/plugins/kat_webpage_analysis
COPY boefjes/plugins/pdio_subfinder boefjes/plugins/pdio_subfinder
# TODO: etc.

RUN find ./boefjes -name 'requirements.txt' -execdir sh -c "cat {} && echo" \; | sort -u > /tmp/boefjes-requirements.txt

RUN --mount=type=cache,target=/root/.cache pip install --upgrade pip && pip install httpx && \
    pip install -r /tmp/boefjes-requirements.txt

COPY ./images/generic_oci_adapter.py .

ENTRYPOINT ["/usr/local/bin/python", "-m", "generic_oci_adapter"]
USER nonroot
