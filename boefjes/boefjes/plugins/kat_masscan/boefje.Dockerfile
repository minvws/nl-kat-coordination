# syntax=docker/dockerfile:1

FROM python:3.11-slim

ARG BOEFJE_PATH=./boefjes/plugins/kat_masscan
ENV PYTHONPATH=/app:$BOEFJE_PATH

RUN adduser --disabled-password lama
WORKDIR /home/lama

# Packages:
# git: get masscan source
# libpcap(-dev): run masscan
# libcap: set cap_net_raw permission for user lama
RUN apt-get update && apt-get install -y git libpcap-dev libcap2-bin make gcc && pip install httpx

# Version pinning on specific commit. Tag in boefje.py may need an update when updating this hash.
RUN mkdir masscan \
    && cd masscan \
    && git init \
    && git remote add origin https://github.com/robertdavidgraham/masscan.git \
    && git fetch --dept 1 origin 9065684c52682d3e12a35559ef72cd0f07838bff \
    && git checkout FETCH_HEAD \
    && make -j \
    && chown -R lama:lama /home/lama/masscan \
    && setcap cap_net_raw=eip /home/lama/masscan/bin/masscan

USER lama

COPY ./images/oci_adapter.py ./
COPY $BOEFJE_PATH $BOEFJE_PATH

ENTRYPOINT ["/usr/local/bin/python", "-m", "oci_adapter"]
