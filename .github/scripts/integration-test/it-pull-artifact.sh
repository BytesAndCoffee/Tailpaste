#!/bin/bash
# Pull and run exact artifact for testing
# Arguments: $1 - artifact digest
# Arguments: $2 - registry
# Arguments: $3 - image name

set -euo pipefail

ARTIFACT_DIGEST=$1
REGISTRY=$2
IMAGE_NAME=$3
# Docker requires lowercase repository names
IMAGE_NAME_LOWER=$(echo "$IMAGE_NAME" | tr '[:upper:]' '[:lower:]')
FULL_IMAGE="$REGISTRY/$IMAGE_NAME_LOWER@$ARTIFACT_DIGEST"

echo "🐳 Pulling exact artifact for integration testing..."
echo "Pulling image: $FULL_IMAGE"
docker pull "$FULL_IMAGE"

# Tag the image for easier reference in tests
docker tag "$FULL_IMAGE" tailpaste-integration-test:latest

echo "✅ Artifact pulled and tagged for testing"

# Verify we're using the exact digest
PULLED_DIGEST=$(docker inspect "$FULL_IMAGE" --format='{{index .RepoDigests 0}}' | cut -d'@' -f2)
if [ "$PULLED_DIGEST" != "$ARTIFACT_DIGEST" ]; then
  echo "❌ Digest mismatch! Expected: $ARTIFACT_DIGEST, Got: $PULLED_DIGEST"
  exit 1
fi
echo "✅ Digest verification passed"
