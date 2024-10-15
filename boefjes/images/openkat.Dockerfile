FROM python:3.11-slim

ENV PATH=/home/nonroot/.local/bin:${PATH}
WORKDIR /app
RUN adduser --disabled-password --gecos '' nonroot

COPY boefjes/requirements-dev.txt boefjes/requirements.txt .

RUN --mount=type=cache,target=/root/.cache \
    pip install --upgrade pip \
    grep -v git+https:// requirements.txt | pip install -r /dev/stdin && \
    grep git+https:// requirements.txt | pip install -r /dev/stdin ; \
    fi

COPY octopoes/ /tmp/octopoes
RUN cd /tmp/octopoes && python setup.py bdist_wheel
RUN pip install /tmp/octopoes/dist/octopoes*.whl

COPY ./images/oci_adapter.py .
COPY boefjes/boefjes ./boefjes

ENTRYPOINT ["/usr/local/bin/python", "-m", "oci_adapter"]
USER nonroot
