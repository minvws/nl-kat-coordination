FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && pip install httpx && pip install requests

ARG BOEFJE_PATH=./boefjes/plugins/kat_export_http
ENV PYTHONPATH=/app:$BOEFJE_PATH

COPY ./boefjes/worker .
COPY $BOEFJE_PATH $BOEFJE_PATH

ENTRYPOINT ["/usr/local/bin/python", "-m", "worker.oci_adapter"]
