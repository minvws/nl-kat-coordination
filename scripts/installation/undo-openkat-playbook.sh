#!/bin/bash
#
systemctl stop postgresql@15-main.service
systemctl stop rabbitmq-server
systemctl stop epmd
systemctl stop kat-rocky
systemctl stop xtdb-http-multinode
apt remove -y --purge python3-psycopg2 python3-pexpect rabbitmq-server
apt remove -y --purge postgresql*
apt remove -y --purge kat-* xtdb-http-multinode

rm -rf /etc/kat /var/log/kat-bytes
rm -rf /var/lib/postgresql/ /etc/postgresql/
