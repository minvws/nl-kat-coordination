FROM noamblitz/drill:latest

RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python && python3 -m ensurepip

ARG BOEFJE_PATH
ENV PYTHONPATH=/app:$BOEFJE_PATH

ENTRYPOINT ["/app/boefje_entrypoint.sh"]

COPY ./images/boefje_entrypoint.sh /app/boefje_entrypoint.sh
COPY ./images/docker_adapter.py .
COPY $BOEFJE_PATH $BOEFJE_PATH
