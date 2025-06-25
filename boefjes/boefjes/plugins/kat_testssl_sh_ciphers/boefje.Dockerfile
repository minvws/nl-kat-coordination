FROM openkat/boefje-base:latest

ARG OCI_IMAGE=ghcr.io/minvws/openkat/testssl-sh-ciphers:latest
ENV OCI_IMAGE=$OCI_IMAGE

USER root
RUN INSTALL_ROOT=/rootfs /bin/sh -c;\
    ln -s /usr/bin/busybox /usr/bin/tar;\
    ln -s /usr/bin/busybox /usr/bin/hexdump;\
    ln -s /usr/bin/busybox /usr/bin/xxd;\
    echo 'testssl:x:1000:1000::/home/nonroot:/bin/bash' >> /etc/passwd;\
    echo 'nonroot:x:1000:' >> /etc/group;\
    echo 'nonroot:!::0:::::' >> /etc/shadow;\
    install --mode 2755 --owner nonroot --group nonroot --directory /home/nonroot;\
    ln -s /home/nonroot/testssl.sh /usr/local/bin/testssl.sh
USER nonroot

COPY ./boefjes/plugins/kat_testssl_sh_ciphers ./kat_testssl_sh_ciphers
