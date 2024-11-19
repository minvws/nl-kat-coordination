FROM python:3.11-slim

ARG BOEFJE_PATH=./boefjes/plugins/kat_adr_validator
ENV PYTHONPATH=/app:$BOEFJE_PATH

RUN apt-get update && pip install httpx
COPY --from=registry.gitlab.com/commonground/don/adr-validator:0.2.0 /usr/local/bin/adr-validator /usr/local/bin/

COPY ./images/oci_adapter.py ./
COPY $BOEFJE_PATH $BOEFJE_PATH

ENTRYPOINT ["/usr/local/bin/python", "-m", "oci_adapter"]
