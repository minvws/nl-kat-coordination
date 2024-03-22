ARG PYTHON_VERSION=3.11
FROM python:$PYTHON_VERSION

ARG USER_UID=1000
ARG USER_GID=1000
ARG BOEFJE_PATH
ENV PATH=/home/nonroot/.local/bin:${PATH}

WORKDIR /app
RUN groupadd --gid $USER_GID nonroot && adduser --disabled-password --gecos '' --uid $USER_UID --gid $USER_GID nonroot

COPY ./images/boefje_entrypoint.sh .
ENTRYPOINT ["/app/boefje_entrypoint.sh"]

ENV PYTHONPATH=/app:$BOEFJE_PATH

# requirements.txt file is optional this way
COPY $BOEFJE_PATH/requirements.txt* .

# TODO: fix the dependency on the job_models.py and pydantic
RUN --mount=type=cache,target=/root/.cache pip install --upgrade pip \
    && pip install "pydantic==2.4.2" && (pip install -r requirements.txt || true)

COPY ./images/docker_adapter.py .

COPY $BOEFJE_PATH $BOEFJE_PATH
COPY ./boefjes/job_models.py boefjes/job_models.py

ENV BOEFJE_ENTRYPOINT='python -m docker_adapter'
