# syntax=docker/dockerfile:1

FROM alpine:3.18

# Packages:
# build-base, gcc, make, linux-headers: create masscan binary
# git: get masscan source
# libpcap(-dev): run masscan
# libcap: set cap_net_raw permission for user lama
RUN apk update && apk upgrade \
    && apk add --no-cache build-base git make gcc libpcap libpcap-dev linux-headers libcap \
    && adduser -D lama

WORKDIR /home/lama

# Version pinning on specific commit. Tag in boefje.py may need an update when updating this hash.
RUN mkdir masscan \
    && cd masscan \
    && git init \
    && git remote add origin https://github.com/robertdavidgraham/masscan.git \
    && git fetch --dept 1 origin 9065684c52682d3e12a35559ef72cd0f07838bff \
    && git checkout FETCH_HEAD \
    && make -j \
    && chown -R lama:lama /home/lama/masscan \
    && setcap cap_net_raw=eip /home/lama/masscan/bin/masscan

USER lama
ENTRYPOINT [ "/home/lama/masscan/bin/masscan" ]
