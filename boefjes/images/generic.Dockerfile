FROM python:3.11-slim

ENV PATH=/home/nonroot/.local/bin:${PATH}
WORKDIR /app
RUN adduser --disabled-password --gecos '' nonroot

COPY boefjes/plugins/kat_dns boefjes/plugins/kat_dns
# TODO: etc.

RUN find ./boefjes -name 'requirements.txt' -execdir sh -c "cat {} && echo" \; | sort -u > /tmp/boefjes-requirements.txt

RUN --mount=type=cache,target=/root/.cache pip install --upgrade pip && pip install httpx && \
    pip install -r /tmp/boefjes-requirements.txt

COPY ./images/generic_oci_adapter.py .

ENTRYPOINT ["/usr/local/bin/python", "-m", "generic_oci_adapter"]
USER nonroot
