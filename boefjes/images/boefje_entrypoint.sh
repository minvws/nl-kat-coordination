#!/bin/bash

set -e

curl -s $1 > input.json
OUTPUT_URL=$(cat input.json | python3 -c "import sys, json; print(json.loads(sys.stdin.read())['output_url'])")

# Pass the task to the boefje entrypoint and save the output, or send back that the task has failed
cat input.json | python -m docker_adapter > out.json || curl -s -X POST -d '{"status": "FAILED"}' $OUTPUT_URL
curl -s -X POST -f -d '@out.json' -H "Content-type: application/json" $OUTPUT_URL
