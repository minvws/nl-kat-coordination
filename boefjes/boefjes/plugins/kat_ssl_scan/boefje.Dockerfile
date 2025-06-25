FROM openkat/boefje-base:latest

ARG OCI_IMAGE=ghcr.io/minvws/openkat/ssl-version:latest
ENV OCI_IMAGE=$OCI_IMAGE

USER root
RUN VERSION= SHA256= /bin/sh -c apk update;\
    apk add alpine-sdk perl zlib-dev linux-headers curl unzip git ;\
    curl -L https://github.com/rbsec/sslscan/archive/refs/heads/master.zip -o sslscan-master.zip;\
    unzip sslscan-master.zip;\
    cd sslscan-master;\
    make static && make install;\
    cd / && rm -rf sslscan-master;\
    adduser -D -g '' sslscan;\
    apk del alpine-sdk perl zlib-dev linux-headers curl unzip git;\
    rm -rf /var/cache/apk/*
USER nonroot

COPY ./boefjes/plugins/kat_ssl_scan ./kat_ssl_scan
