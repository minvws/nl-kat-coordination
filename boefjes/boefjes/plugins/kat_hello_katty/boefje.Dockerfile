FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && pip install httpx

ARG BOEFJE_PATH=./boefjes/plugins/kat_hello_katty
ENV PYTHONPATH=/app:$BOEFJE_PATH

COPY ./images/oci_adapter.py ./
COPY $BOEFJE_PATH $BOEFJE_PATH

ENTRYPOINT ["/usr/local/bin/python", "-m", "oci_adapter"]
