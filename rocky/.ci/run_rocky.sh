#!/bin/bash

set -e

# To ensure the postgres container is up and running
sleep 1

pytest
