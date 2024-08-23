FROM node:19-bullseye

WORKDIR /app
RUN apt update
RUN apt install -y git


RUN git clone https://github.com/sullo/nikto

ARG BOEFJE_PATH=./boefjes/plugins/kat_nikto
COPY $BOEFJE_PATH ./

RUN npm ci

ENTRYPOINT [ "node", "./" ]
