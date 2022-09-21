# syntax=docker/dockerfile:1
FROM node:18-bullseye AS builder

WORKDIR /app

COPY package.json yarn.lock .
COPY assets assets

RUN yarn --ignore-engines && yarn build

FROM python:3.8

ARG USER_UID=1000
ARG USER_GID=1000

ENTRYPOINT ["/app/rocky/entrypoint.sh"]

RUN groupadd --gid $USER_GID rocky
RUN adduser --disabled-password --gecos '' --uid $USER_UID --gid $USER_GID rocky

WORKDIR /app/rocky

RUN --mount=type=cache,target=/var/cache/apt \
  apt-get update \
  && apt-get -y upgrade \
  && apt-get install -y --no-install-recommends gettext \
  && rm -rf /var/lib/apt/lists/*

# Build with "docker build --build-arg ENVIRONMENT=dev" to install dev
# dependencies
ARG ENVIRONMENT

COPY requirements.txt requirements-check.txt requirements-dev.txt .
RUN --mount=type=cache,target=/root/.cache --mount=type=secret,id=github_token \
    git config --global url."https://`cat /run/secrets/github_token`@github.com/".insteadOf "ssh://git@github.com/" \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && if [ "$ENVIRONMENT" = "dev" ]; then pip install -r requirements-check.txt -r requirements-dev.txt; fi \
    && rm /root/.gitconfig

COPY . .

# These files need to be available when we run collectstatic
COPY --link --from=builder /app/assets/dist assets/dist

# The secret key isn't used by the commands, but Django won't work do anything
# without it
RUN export SECRET_KEY="secret" && python manage.py collectstatic -l && python manage.py compilemessages

USER rocky

CMD ["uwsgi", "--ini", "uwsgi.ini", "--wsgi-file", "rocky/wsgi.py"]
