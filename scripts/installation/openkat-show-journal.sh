#!/bin/bash

if [[ ${1} == "" ]]; then
    echo "Usage ./show_journal_openkat.sh [nr. of lines]"
else
    sudo journalctl -n "${1}"
fi
