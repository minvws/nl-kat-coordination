FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && pip install httpx

ARG BOEFJE_PATH=./boefjes/plugins/kat_nmap_tcp
ENV PYTHONPATH=/app:$BOEFJE_PATH

COPY ./images/oci_adapter.py ./
COPY $BOEFJE_PATH $BOEFJE_PATH

RUN git clone https://github.com/sullo/nikto
RUN ./nikto/program/nikto.pl -h 46.23.85.171 -o ./output.json

ENTRYPOINT ["/usr/local/bin/python", "-m", "oci_adapter"]
