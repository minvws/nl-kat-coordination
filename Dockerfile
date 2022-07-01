FROM python:3.8

# Reference to install yarn: https://linuxtut.com/install-yarn-in-docker-image-3f031

RUN \
    set -ex; \
    curl https://deb.nodesource.com/setup_12.x | bash; \
    curl https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -; \
    echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list; \
    apt-get update && apt-get install -y nodejs yarn gettext

RUN groupadd --gid 1000 rocky
RUN adduser --disabled-password --gecos '' --uid 1000 --gid 1000 rocky

USER rocky
WORKDIR /app/rocky

COPY nl-kat-rocky/requirements-dev.txt .
RUN pip3 install -r requirements-dev.txt

COPY --chown=rocky nl-kat-octopoes /app/octopoes
RUN pip3 install /app/octopoes

COPY nl-kat-rocky .
