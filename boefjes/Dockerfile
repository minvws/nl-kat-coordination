ARG PYTHON_VERSION=3.13
FROM python:$PYTHON_VERSION AS dev

ARG USER_UID=1000
ARG USER_GID=1000

ENTRYPOINT ["/app/boefjes/entrypoint.sh"]

RUN groupadd --gid "$USER_GID" nonroot
RUN adduser --disabled-password --gecos '' --uid "$USER_UID" --gid "$USER_GID" nonroot

WORKDIR /app/boefjes
ENV PATH="/app/boefjes/.venv/bin:$PATH"

ARG ENVIRONMENT

COPY boefjes/requirements-dev.txt boefjes/requirements.txt .

RUN --mount=type=cache,target=/root/.cache \
    --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    --mount=type=bind,source=boefjes/uv.lock,target=uv.lock \
    --mount=type=bind,source=boefjes/pyproject.toml,target=pyproject.toml \
    if [ "$ENVIRONMENT" = "dev" ]; then \
    uv sync --locked --no-install-project ; \
    else \
    uv sync --locked --no-install-project --no-dev ; \
    fi

FROM dev

COPY octopoes/ /tmp/octopoes
RUN cd /tmp/octopoes && python setup.py bdist_wheel
RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    uv pip install --no-deps /tmp/octopoes/dist/octopoes*.whl

COPY boefjes/entrypoint.sh .
COPY boefjes/boefjes ./boefjes

# FIXME: We currently have to run as root to be able to start containers using
# the docker socket
#USER nonroot

CMD ["python", "-m", "bin.worker", "boefje"]
