#!/bin/bash
set -e

# Make env variable comparison case insensitive
shopt -s nocasematch

exec "$@"
