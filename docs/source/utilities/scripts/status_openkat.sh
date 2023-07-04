#!/usr/bin/bash

if [[ ${1} == "" ]]; then
	echo "Usage ./status_openkat.sh [proces]" 
else 
	echo "Status ${1}:"
	sudo systemctl status $1
fi
