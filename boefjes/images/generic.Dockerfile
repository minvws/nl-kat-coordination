FROM python:3.11-slim as base

WORKDIR /app
RUN adduser --disabled-password --gecos '' nonroot

ENV PATH=/home/nonroot/.local/bin:${PATH}
ENV OPENKAT_CACHE_PATH=/home/nonroot/openkat_cache
RUN mkdir "$OPENKAT_CACHE_PATH" && chown nonroot: "$OPENKAT_CACHE_PATH"

VOLUME /home/nonroot/openkat_cache

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
COPY boefjes/plugins/kat_rpki boefjes/plugins/kat_rpki
COPY boefjes/plugins/kat_security_txt_downloader boefjes/plugins/kat_security_txt_downloader
COPY boefjes/plugins/kat_service_banner boefjes/plugins/kat_service_banner
COPY boefjes/plugins/kat_shodan boefjes/plugins/kat_shodan
COPY boefjes/plugins/kat_webpage_analysis boefjes/plugins/kat_webpage_analysis
COPY boefjes/plugins/pdio_subfinder boefjes/plugins/pdio_subfinder
COPY boefjes/plugins/kat_adr_finding_types boefjes/plugins/kat_adr_finding_types
COPY boefjes/plugins/kat_cve_finding_types boefjes/plugins/kat_cve_finding_types
COPY boefjes/plugins/kat_cwe_finding_types boefjes/plugins/kat_cwe_finding_types
COPY boefjes/plugins/kat_kat_finding_types boefjes/plugins/kat_kat_finding_types
COPY boefjes/plugins/kat_retirejs_finding_types boefjes/plugins/kat_retirejs_finding_types
COPY boefjes/plugins/kat_snyk_finding_types boefjes/plugins/kat_snyk_finding_types

RUN find ./boefjes -name 'requirements.txt' -execdir sh -c "cat {} && echo" \; | sort -u > /tmp/boefjes-requirements.txt

RUN --mount=type=cache,target=/root/.cache pip install --upgrade pip && pip install httpx && \
    pip install -r /tmp/boefjes-requirements.txt

USER nonroot


FROM base as standalone

ENTRYPOINT ["/usr/local/bin/python", "-m", "generic_oci_adapter"]
COPY ./images/generic_oci_adapter.py .


FROM base as worker

ARG OCI_IMAGE
ENV OCI_IMAGE=$OCI_IMAGE

ENTRYPOINT ["python", "-m", "worker"]

RUN --mount=type=cache,target=/root/.cache pip install structlog
RUN --mount=type=cache,target=/root/.cache pip install pydantic
RUN --mount=type=cache,target=/root/.cache pip install jsonschema
RUN --mount=type=cache,target=/root/.cache pip install croniter

COPY ./boefjes/worker ./worker
COPY ./boefjes/logging.json logging.json

FROM standalone
