#!/bin/bash
#
# Build image from the currently checked out version of the wikidata bot
# and push it to the Docker Hub, with an optional tag (by default "latest").
#
# Usage:
#   $ ./docker/push.sh [tag]

set -eu

cd "$(dirname "${BASH_SOURCE[0]}")/../"

TAG=${1:-latest}
IMAGE="metabrainz/wikidata-bot:$TAG"

echo "Building $IMAGE..."
docker build -t "$IMAGE" .
echo "Pushing $IMAGE..."
docker push "$IMAGE"
