#!/bin/bash

if [[ ${1} == "" ]]; then
    echo "Usage ./status_openkat.sh [process]"
else
    echo "Status ${1}:"
    sudo systemctl status "$1"
fi
