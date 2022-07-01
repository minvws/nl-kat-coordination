FROM python:3.8

WORKDIR /app/boefjes

COPY nl-kat-boefjes/requirements-dev.txt .
RUN pip install -r requirements-dev.txt

COPY nl-kat-octopoes/ /app/octopoes
RUN pip install /app/octopoes

COPY nl-kat-boefjes/ .
RUN find . -name 'requirements.txt' -execdir pip install -r {} \;
