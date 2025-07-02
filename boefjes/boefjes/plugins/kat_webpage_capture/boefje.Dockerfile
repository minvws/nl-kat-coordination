FROM mcr.microsoft.com/playwright:v1.53.0-noble

RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update
RUN apt-get install python3.13

ARG BOEFJES_API=http://boefje:8000
ENV BOEFJES_API=$BOEFJES_API
ENV PYTHONPATH=/app/boefje:/app

WORKDIR /app/boefje
RUN adduser --disabled-password --gecos '' nonroot
RUN --mount=type=cache,target=/root/.cache pip install --upgrade pip && pip install httpx structlog pydantic jsonschema croniter click

USER nonroot

COPY ./boefjes/worker ./worker
COPY ./boefjes/logging.json logging.json

ENTRYPOINT ["/usr/local/bin/python", "-m", "worker"]
CMD []

ARG OCI_IMAGE=ghcr.io/minvws/openkat/webpage-capture:latest
ENV OCI_IMAGE=$OCI_IMAGE
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY ./boefjes/plugins/kat_webpage_capture ./kat_webpage_capture
