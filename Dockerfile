# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.13

FROM python:$PYTHON_VERSION-trixie AS dev

ENV GRANIAN_WORKERS=2
ENV GRANIAN_THREADS=4
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/usr/local

ARG USER_UID=1000
ARG USER_GID=1000

ENTRYPOINT ["/app/openkat/entrypoint.sh"]

RUN groupadd --gid "$USER_GID" openkat
RUN adduser --disabled-password --gecos '' --uid "$USER_UID" --gid "$USER_GID" openkat

WORKDIR /app/openkat

RUN --mount=type=cache,target=/var/cache/apt \
  apt-get update \
  && apt-get -y upgrade \
  && apt-get install -y --no-install-recommends gettext netcat-openbsd \
  && rm -rf /var/lib/apt/lists/*

# Build with "docker build --build-arg ENVIRONMENT=dev" to install dev dependencies
ARG ENVIRONMENT

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    if [ "$ENVIRONMENT" = "dev" ]; then uv sync --locked --no-install-project --group dev; else uv sync --locked --no-install-project; fi

COPY . .

FROM dev

# The secret key isn't used by the commands, but Django won't work without it

RUN export SECRET_KEY="secret" XTDB_URI="http://localhost/fake" REDIS_QUEUE_URI="redis://localhost/fake" && \
    python manage.py collectstatic -l && python manage.py compress && python manage.py compilemessages

RUN rm -rf tests

USER openkat

CMD ["granian", "--interface", "wsgi", "openkat.wsgi:application", "--host", "0.0.0.0"]
