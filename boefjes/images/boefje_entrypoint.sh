#!/bin/bash

set -e

curl -s "$1" > input.json
OUTPUT_URL=$(python3 -c "import sys, json; print(json.loads(sys.stdin.read())['output_url'])" < input.json)

# Pass the task to the boefje entrypoint and save the output, or send back that the task has failed
python -m docker_adapter < input.json > out.json || curl -s -X POST -d '{"status": "FAILED"}' "$OUTPUT_URL"
curl -s -X POST -f -d '@out.json' -H "Content-type: application/json" "$OUTPUT_URL"
