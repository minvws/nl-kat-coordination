FROM openkat/boefje-base:latest

COPY --from=golang:1.13-alpine /usr/local/go/ /usr/local/go/

ARG OCI_IMAGE=ghcr.io/minvws/cynalytics/octoscan:latest
ENV OCI_IMAGE=$OCI_IMAGE

USER root
RUN apt-get update

COPY ./boefjes/plugins/kat_nmap_tcp ./kat_nmap_tcp
