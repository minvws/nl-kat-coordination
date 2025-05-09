FROM python:3.13-slim

WORKDIR /app
RUN adduser --disabled-password --gecos '' nonroot
RUN apt update -y && apt-get install -y --no-install-recommends ldnsutils dnsutils dns-root-data && pip install httpx

ARG BOEFJE_PATH=./boefjes/plugins/kat_dnssec
ENV PYTHONPATH=/app:$BOEFJE_PATH

COPY ./images/oci_adapter.py ./
COPY $BOEFJE_PATH $BOEFJE_PATH

ENTRYPOINT ["/usr/local/bin/python", "-m", "oci_adapter"]
USER nonroot
