#!/bin/bash

#GITHUB_TOKEN should be ${{ secrets.GITHUB_TOKEN }}
#DESTINATION_BRANCH should be ${{ github.ref }}

FILES=$(git diff --name-only)
for FILE in $FILES; do
    SHA=$(git rev-parse "$DESTINATION_BRANCH":"$FILE")
    gh api --method PUT /repos/:owner/:repo/contents/"$FILE" \
        --field message="Update $FILE" \
        --field content=@<(base64 -i "$FILE") \
        --field branch="$DESTINATION_BRANCH" \
        --field sha="$SHA"
done
