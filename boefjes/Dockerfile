ARG PYTHON_VERSION=3.11
FROM python:$PYTHON_VERSION-bookworm AS boefjes-requirements

COPY boefjes/boefjes ./boefjes
COPY boefjes/requirements.txt ./boefjes

# The echo since cat does not add a newline
RUN find ./boefjes/plugins -name 'requirements.txt' -execdir sh -c "cat {} && echo" \; | sort -u > /tmp/boefjes-requirements.txt

FROM python:$PYTHON_VERSION AS dev

ARG USER_UID=1000
ARG USER_GID=1000

ENTRYPOINT ["/app/boefjes/entrypoint.sh"]

RUN groupadd --gid $USER_GID nonroot
RUN adduser --disabled-password --gecos '' --uid $USER_UID --gid $USER_GID nonroot

WORKDIR /app/boefjes
ENV PATH=/home/nonroot/.local/bin:${PATH}

ARG ENVIRONMENT

COPY --from=boefjes-requirements /tmp/boefjes-requirements.txt /tmp/boefjes-requirements.txt
COPY boefjes/requirements-dev.txt boefjes/requirements.txt .

RUN --mount=type=cache,target=/root/.cache \
    pip install --upgrade pip \
    && pip install -r /tmp/boefjes-requirements.txt \
    && rm /tmp/boefjes-requirements.txt \
    && pip install -r requirements.txt \
    && if [ "$ENVIRONMENT" = "dev" ]; then pip install -r requirements-dev.txt; fi

FROM dev

COPY octopoes/ /tmp/octopoes
RUN cd /tmp/octopoes && python setup.py bdist_wheel
RUN pip install /tmp/octopoes/dist/octopoes*.whl

COPY boefjes/entrypoint.sh .
COPY boefjes/boefjes ./boefjes

# FIXME: We currently have to run as root to be able to start containers using
# the docker socket
#USER nonroot

CMD ["python", "-m", "bin.worker", "boefje"]
