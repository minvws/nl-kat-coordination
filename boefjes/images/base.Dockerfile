FROM python:3.11-slim as base

ENV PYTHONPATH=/app/boefje

WORKDIR /app/boefje
RUN adduser --disabled-password --gecos '' nonroot
RUN --mount=type=cache,target=/root/.cache pip install --upgrade pip && pip install httpx structlog pydantic jsonschema croniter click

USER nonroot

COPY ./images/oci_adapter.py /app/boefje
COPY ./boefjes/worker ./worker
COPY ./boefjes/logging.json logging.json

ENTRYPOINT ["/usr/local/bin/python"]
CMD ["-m", "oci_adapter"]

FROM base as builder

ARG BOEFJE_PATH

COPY $BOEFJE_PATH/requirements.txt* .
RUN if test -f requirements.txt; then pip install -r requirements.txt; fi

COPY $BOEFJE_PATH .

FROM base
