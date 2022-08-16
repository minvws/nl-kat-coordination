FROM python:3.8 as boefjes-requirements

COPY nl-kat-boefjes/boefjes ./boefjes

# The echo since cat does not add a newline
RUN find ./boefjes -name 'requirements.txt' -execdir sh -c "cat {} && echo" \; | sort -u > /tmp/boefjes-requirements.txt



FROM python:3.8 as dev

WORKDIR /app/boefjes

COPY nl-kat-octopoes/ /app/octopoes
RUN pip install /app/octopoes

COPY --from=boefjes-requirements /tmp/boefjes-requirements.txt /tmp/boefjes-requirements.txt
RUN pip install -r /tmp/boefjes-requirements.txt

COPY nl-kat-boefjes/requirements-dev.txt .
RUN pip install -r requirements-dev.txt

COPY nl-kat-boefjes/plugin_repository/requirements.txt ./plugin_repository/requirements.txt
RUN pip install -r plugin_repository/requirements.txt

COPY nl-kat-boefjes/ .

FROM dev
