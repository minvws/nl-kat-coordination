FROM python:3.13-slim

WORKDIR /app
RUN apt-get update && pip install httpx && pip install requests

ARG BOEFJE_PATH=./boefjes/plugins/kat_export_http
ENV PYTHONPATH=/app:$BOEFJE_PATH

COPY ./images/oci_adapter.py ./
COPY $BOEFJE_PATH $BOEFJE_PATH

ENTRYPOINT ["/usr/local/bin/python", "-m", "oci_adapter"]
