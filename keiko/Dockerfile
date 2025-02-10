ARG PYTHON_VERSION=3.11
FROM python:$PYTHON_VERSION-bookworm AS dev

WORKDIR /app/keiko
COPY removekeiko.sh .
ENTRYPOINT ["/app/keiko/removekeiko.sh"]
