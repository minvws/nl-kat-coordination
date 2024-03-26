FROM python:3.11-alpine

WORKDIR /app
RUN adduser --disabled-password --gecos '' nonroot
RUN apk add --update drill && rm -rf /var/cache/apk/* && pip install httpx

ARG BOEFJE_PATH
ENV PYTHONPATH=/app:$BOEFJE_PATH

COPY ./images/docker_adapter.py ./
COPY $BOEFJE_PATH $BOEFJE_PATH

ENTRYPOINT ["/usr/local/bin/python", "-m", "docker_adapter"]
USER nonroot
