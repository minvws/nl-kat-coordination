FROM ghcr.io/astral-sh/uv:python3.13-alpine

RUN uv pip install --system httpx
COPY ./plugins/plugins/kat_dig/ ./
