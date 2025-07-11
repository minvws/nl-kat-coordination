ARG PYTHON_VERSION=3.13
FROM python:$PYTHON_VERSION-bookworm AS base

ENTRYPOINT ["/app/boefjes/entrypoint.sh"]

ARG USER_UID=1000
ARG USER_GID=1000

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY boefjes/pyproject.toml boefjes/uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=boefjes/uv.lock,target=uv.lock \
    --mount=type=bind,source=boefjes/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY boefjes/boefjes boefjes/
COPY boefjes/entrypoint.sh .

# todo: install Octopoes

RUN groupadd --gid "$USER_GID" openkat && \
    adduser --disabled-password --gecos "" --uid "$USER_UID" --gid "$USER_GID" openkat

ENV PYTHONPATH=/app/boefjes/

FROM base AS dev

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=boefjes/uv.lock,target=uv.lock \
    --mount=type=bind,source=boefjes/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --group dev

# todo: we currently have to run as root to be able to start containers using the Docker socket
# USER openkat

CMD ["uv", "run", "--module", "bin.worker", "boefje"]
