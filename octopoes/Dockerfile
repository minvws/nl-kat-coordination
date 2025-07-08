ARG PYTHON_VERSION=3.13
FROM python:$PYTHON_VERSION-bookworm AS base

EXPOSE 8000

ENTRYPOINT ["/app/octopoes/entrypoint.sh"]

ARG USER_UID=1000
ARG USER_GID=1000

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY . .

RUN groupadd --gid "$USER_GID" octopoes && \
    adduser --disabled-password --gecos "" --uid "$USER_UID" --gid "$USER_GID" octopoes

ENV PYTHONPATH=octopoes/

FROM base AS dev

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
     uv sync --frozen --group dev

USER octopoes

CMD ["uv", "run", "uvicorn", "octopoes.api.api:app", "--host", "0.0.0.0", "--port", "8000"]
