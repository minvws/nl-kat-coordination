#!/bin/bash
set -e

if [ "$1" = "raw" ]; then
    echo $2 | eval $BOEFJE_ENTRYPOINT > out.json
    cat out.json
    exit 0
fi

curl -s $1 > input.json
OUTPUT_URL=$(cat input.json | python3 -c "import sys, json; print(json.loads(sys.stdin.read())['output_url'])")

# Pass the task to the boefje entrypoint and save the output, or send back that the task has failed
cat input.json | eval $BOEFJE_ENTRYPOINT > out.json || curl -s -X POST -d '{"status": "FAILED"}' $OUTPUT_URL
curl -s -X POST -f -d '@out.json' -H "Content-type: application/json" $OUTPUT_URL
