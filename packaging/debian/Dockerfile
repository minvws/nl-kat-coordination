FROM debian:bullseye

SHELL ["/bin/bash", "-c"]
RUN apt-get update && apt-get install -y curl &&\
    curl -sL https://deb.nodesource.com/setup_16.x -o /tmp/setup_16.x.sh &&\
    checksum=$(sha256sum /tmp/setup_16.x.sh | awk '{ print $1 }') &&\
    ([ "$checksum" == "409dec0f6c33737dc988c1459509bf32ddbb44a0fca8dbb3539bb81ec0bd9ff9" ] || exit 100) &&\
    bash /tmp/setup_16.x.sh

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    gettext devscripts debhelper equivs python3.9 \
    python3-setuptools python3-pip python3-dev \
    libssl-dev dh-virtualenv libpq-dev libssl-dev \
    build-essential nodejs git openssh-client \
    libfreetype-dev zlib1g-dev libjpeg-dev libffi-dev
RUN corepack enable
