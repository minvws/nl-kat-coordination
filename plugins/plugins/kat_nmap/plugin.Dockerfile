FROM ghcr.io/astral-sh/uv:python3.13-alpine

RUN uv pip install --system httpx==0.27.2 python-libnmap==0.7.3
COPY ./plugins/plugins/kat_nmap/ ./
