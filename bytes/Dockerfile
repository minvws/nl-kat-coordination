ARG PYTHON_VERSION=3.13
FROM python:$PYTHON_VERSION-bookworm AS base

EXPOSE 8000

ENTRYPOINT ["/app/bytes/entrypoint.sh"]

ARG USER_UID=1000
ARG USER_GID=1000

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY bytes/ bytes/
COPY entrypoint.sh .

RUN groupadd --gid "$USER_GID" bytes && \
    adduser --disabled-password --gecos "" --uid "$USER_UID" --gid "$USER_GID" bytes

ENV BYTES_DATA_DIR=/data
RUN mkdir "$BYTES_DATA_DIR" && chown bytes: "$BYTES_DATA_DIR"
VOLUME /data

ENV PYTHONPATH=/app/bytes/

FROM base AS dev

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --group dev

USER bytes

CMD ["uv", "run", "uvicorn", "bytes.api:app", "--host", "0.0.0.0", "--port", "8000"]
