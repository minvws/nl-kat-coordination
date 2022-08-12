FROM python:3.8

ARG USER_UID=1000
ARG USER_GID=1000

# Reference to install yarn: https://linuxtut.com/install-yarn-in-docker-image-3f031

RUN \
    set -ex; \
    curl https://deb.nodesource.com/setup_16.x | bash; \
    curl https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -; \
    echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list; \
    apt-get update && apt-get install -y nodejs yarn gettext

RUN groupadd --gid $USER_GID rocky
RUN adduser --disabled-password --gecos '' --uid $USER_UID --gid $USER_GID rocky

USER rocky
WORKDIR /app/rocky

COPY nl-kat-rocky/requirements-dev.txt .
RUN pip3 install -r requirements-dev.txt

COPY --chown=rocky nl-kat-octopoes /app/octopoes
RUN pip3 install /app/octopoes

COPY --chown=rocky nl-kat-rocky .
