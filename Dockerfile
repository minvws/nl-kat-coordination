FROM python:3.8

ARG USER_UID=1000
ARG USER_GID=1000

WORKDIR /app/octopoes_api

RUN groupadd --gid $USER_GID octopoes
RUN adduser --disabled-password --gecos '' --uid $USER_UID --gid $USER_GID octopoes
RUN mkdir /var/log/unit && chown octopoes /var/log/unit

USER octopoes
ENV PATH=/home/octopoes/.local/bin:${PATH}

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .
