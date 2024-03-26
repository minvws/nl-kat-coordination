FROM noamblitz/drill:latest

ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd --gid $USER_GID nonroot && adduser --disabled-password --gecos '' --uid $USER_UID --gid $USER_GID nonroot

RUN apk add --update --no-cache python3 curl && ln -sf python3 /usr/bin/python && python3 -m ensurepip

ARG BOEFJE_PATH
ENV PYTHONPATH=/app:$BOEFJE_PATH

ENTRYPOINT ["/app/boefje_entrypoint.sh"]

COPY ./images/boefje_entrypoint.sh /app/boefje_entrypoint.sh
COPY ./images/docker_adapter.py .
COPY $BOEFJE_PATH $BOEFJE_PATH

USER nonroot
