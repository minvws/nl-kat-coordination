FROM ghcr.io/astral-sh/uv:python3.13-alpine

RUN uv pip install --system httpx==0.27.2 dnspython==2.6.1 python-libnmap==0.7.3

COPY ./plugins/plugins/kat_dns/ ./kat_dns
COPY ./plugins/plugins/kat_dig/ ./kat_dig
COPY ./plugins/plugins/kat_nmap/ ./kat_nmap
