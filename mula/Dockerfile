ARG PYTHON_VERSION=3.13
FROM python:$PYTHON_VERSION-bookworm AS dev

EXPOSE 8000

ARG USER_UID=1000
ARG USER_GID=1000

ENTRYPOINT ["/app/scheduler/entrypoint.sh"]

RUN groupadd --gid "$USER_GID" scheduler
RUN adduser --disabled-password --gecos '' --uid "$USER_UID" --gid "$USER_GID" scheduler

WORKDIR /app/scheduler
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/usr/local

# Build with "docker build --build-arg ENVIRONMENT=dev" to install dev
# dependencies
ARG ENVIRONMENT

RUN --mount=type=cache,target=/root/.cache \
    --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    if [ "$ENVIRONMENT" = "dev" ]; then \
    uv sync --locked --no-install-project ; \
    else \
    uv sync --locked --no-install-project --no-dev ; \
    fi

USER scheduler

CMD ["python", "-m", "scheduler"]

FROM dev

COPY . /app/scheduler
