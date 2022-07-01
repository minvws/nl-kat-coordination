FROM python:3.8

WORKDIR /app/octopoes_api

RUN groupadd --gid 1000 octopoes
RUN adduser --disabled-password --gecos '' --uid 1000 --gid 1000 octopoes
RUN mkdir /var/log/unit && chown octopoes /var/log/unit

USER octopoes
ENV PATH=/home/octopoes/.local/bin:${PATH}

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .
