FROM perl:5.40

WORKDIR /app
RUN apt update
RUN apt install -y git
RUN apt install -y nodejs

RUN git clone https://github.com/sullo/nikto

ARG BOEFJE_PATH=./boefjes/plugins/kat_nikto
COPY $BOEFJE_PATH ./

ENTRYPOINT [ "node", "./" ]
