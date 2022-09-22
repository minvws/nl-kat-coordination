FROM python:3.8 as boefjes-requirements

COPY boefjes ./boefjes
COPY requirements.txt ./boefjes

# The echo since cat does not add a newline
RUN find ./boefjes -name 'requirements.txt' -execdir sh -c "cat {} && echo" \; | sort -u > /tmp/boefjes-requirements.txt

FROM python:3.8

ARG USER_UID=1000
ARG USER_GID=1000

ENTRYPOINT ["/app/boefjes/entrypoint.sh"]

RUN groupadd --gid $USER_GID nonroot
RUN adduser --disabled-password --gecos '' --uid $USER_UID --gid $USER_GID nonroot

WORKDIR /app/boefjes
ENV PATH=/home/nonroot/.local/bin:${PATH}

ARG ENVIRONMENT

COPY --from=boefjes-requirements /tmp/boefjes-requirements.txt /tmp/boefjes-requirements.txt
COPY requirements-dev.txt .

RUN --mount=type=cache,target=/root/.cache --mount=type=secret,id=github_token \
    git config --global url."https://github.com/".insteadOf "ssh://git@github.com/" \
    && pip install --upgrade pip \
    && pip install -r /tmp/boefjes-requirements.txt \
    && rm /tmp/boefjes-requirements.txt \
    && if [ "$ENVIRONMENT" = "dev" ]; then pip install -r requirements-dev.txt; fi \
    && rm /root/.gitconfig

COPY . .

# FIXME: We currently have to run as root to be able to start containers using
# the docker socket
#USER nonroot

CMD ["python", "-m", "bin.worker", "boefje"]
