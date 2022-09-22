FROM debian:latest

RUN apt update && apt install -y curl
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash
ENV NVM_DIR "$HOME/.nvm"
RUN DEBIAN_FRONTEND=noninteractive apt install gettext devscripts debhelper -y
