FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y nmap && pip install httpx

ARG BOEFJE_PATH=./boefjes/plugins/kat_nmap_tcp
ENV PYTHONPATH=/app:$BOEFJE_PATH

COPY ./images/oci_adapter.py ./
COPY $BOEFJE_PATH $BOEFJE_PATH

ENTRYPOINT ["/usr/local/bin/python", "-m", "oci_adapter"]
