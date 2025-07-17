ARG PYTHON_VERSION=3.13
FROM python:$PYTHON_VERSION-bookworm AS dev

EXPOSE 8000

ARG USER_UID=1000
ARG USER_GID=1000

ENTRYPOINT ["/app/bytes/entrypoint.sh"]

RUN groupadd --gid "$USER_GID" bytes
RUN adduser --disabled-password --gecos '' --uid "$USER_UID" --gid "$USER_GID" bytes

WORKDIR /app/bytes
ENV PATH="/app/bytes/.venv/bin:$PATH"

ENV BYTES_DATA_DIR=/data
RUN mkdir "$BYTES_DATA_DIR" && chown bytes: "$BYTES_DATA_DIR"
VOLUME /data

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

USER bytes

FROM dev

COPY . .

CMD ["uvicorn", "bytes.api:app", "--host", "0.0.0.0", "--port", "8000"]
