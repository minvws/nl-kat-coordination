# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.13
FROM node:20-bookworm AS node_builder

WORKDIR /app

COPY rocky/package.json rocky/yarn.lock ./
COPY rocky/assets assets
COPY rocky/components components

RUN yarn --ignore-engines && yarn build

FROM python:$PYTHON_VERSION-bookworm AS base

ENTRYPOINT ["/app/rocky/entrypoint.sh"]

ARG USER_UID=1000
ARG USER_GID=1000

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app/rocky

COPY rocky/ ./

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=rocky/uv.lock,target=uv.lock \
    --mount=type=bind,source=rocky/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Install Octopoes wheel
COPY octopoes/ /tmp/octopoes
RUN uv build /tmp/octopoes && uv pip install /tmp/octopoes/dist/octopoes*.whl

# These files need to be available when we run collectstatic
COPY --link --from=node_builder /app/assets/dist rocky/assets/dist

RUN groupadd --gid "$USER_GID" rocky && \
    adduser --disabled-password --gecos "" --uid "$USER_UID" --gid "$USER_GID" rocky

RUN --mount=type=cache,target=/var/cache/apt \
  apt-get update \
  && apt-get -y upgrade \
  && apt-get install -y --no-install-recommends gettext netcat-openbsd \
  && rm -rf /var/lib/apt/lists/*

ENV GRANIAN_WORKERS=2
ENV GRANIAN_THREADS=4
ENV PYTHONPATH=/app/rocky/

# The secret key isn't used by the commands, but Django won't work do anything
# without it
RUN export SECRET_KEY="secret" BYTES_API="http://bytes:8000" BYTES_PASSWORD="password" \
    BYTES_USERNAME="username" KATALOGUS_API="http://katalogus:8000" \
    OCTOPOES_API="http://octopoes_api:80" SCHEDULER_API="http://scheduler:8000" && \
    uv run --frozen manage.py collectstatic -l && \
    uv run --frozen manage.py compress && \
    uv run --frozen manage.py compilemessages

FROM base AS dev

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=rocky/uv.lock,target=uv.lock \
    --mount=type=bind,source=rocky/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --group dev

USER rocky

CMD ["uv", "run", "granian", "--interface", "wsgi", "rocky.wsgi:application", "--host", "0.0.0.0"]
