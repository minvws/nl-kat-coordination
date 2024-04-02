FROM python:3.11-slim

WORKDIR /app
RUN adduser --disabled-password --gecos '' nonroot
RUN apt update -y && apt-get install -y --no-install-recommends ldnsutils dnsutils && pip install httpx
RUN dig . DNSKEY @8.8.8.8 | grep -Ev '^($|;)' > root.key

ARG BOEFJE_PATH
ENV PYTHONPATH=/app:$BOEFJE_PATH

COPY ./images/docker_adapter.py ./
COPY $BOEFJE_PATH $BOEFJE_PATH

ENTRYPOINT ["/usr/local/bin/python", "-m", "docker_adapter"]
USER nonroot
