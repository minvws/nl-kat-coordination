#!/bin/bash

#GITHUB_TOKEN should be ${{ secrets.GITHUB_TOKEN }}
#DESTINATION_BRANCH should be ${{ github.ref }}

FILES=$(git diff --name-only)
for FILE in $FILES; do
    CONTENT=$(base64 -i "$FILE")
    SHA=$(git rev-parse "$DESTINATION_BRANCH":"$FILE")
    gh api --method PUT /repos/:owner/:repo/contents/"$FILE" \
        --field message="Update $FILE" \
        --field content="$CONTENT" \
        --field encoding="base64" \
        --field branch="$DESTINATION_BRANCH" \
        --field sha="$SHA"
done
