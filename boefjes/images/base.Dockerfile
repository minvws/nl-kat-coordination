FROM python:3.11-slim

ARG BOEFJE_PATH
ENV PYTHONPATH=/app:$BOEFJE_PATH

WORKDIR /app
RUN adduser --disabled-password --gecos '' nonroot

COPY $BOEFJE_PATH/requirements.txt* .

RUN --mount=type=cache,target=/root/.cache pip install --upgrade pip && pip install httpx
RUN if test -f requirements.txt; then pip install -r requirements.txt; fi

COPY ./images/oci_adapter.py .
COPY $BOEFJE_PATH $BOEFJE_PATH

ENTRYPOINT ["/usr/local/bin/python", "-m", "oci_adapter"]
USER nonroot
