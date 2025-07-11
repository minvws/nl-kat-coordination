FROM openkat/boefje-base:latest

ARG OCI_IMAGE=ghcr.io/minvws/openkat/wp-scan:latest
ENV OCI_IMAGE=$OCI_IMAGE

user root
RUN apt-get update && \
    apt-get install -y ruby-dev build-essential libcurl4-openssl-dev libxml2 libxml2-dev libxslt1-dev ruby-dev libgmp-dev zlib1g-dev && \
    gem install wpscan

RUN --mount=type=cache,target=/root/.cache pip install --upgrade pip &&  \
    pip install httpx structlog pydantic jsonschema croniter click
USER nonroot

COPY ./boefjes/plugins/kat_wpscan ./kat_wpscan
