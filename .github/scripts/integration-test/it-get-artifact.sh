#!/bin/bash
# Get artifact digest from CI workflow
# Arguments: $1 - CI run ID
# Arguments: $2 - commit SHA
# Arguments: $3 - registry
# Arguments: $4 - image name
# Environment: GH_TOKEN must be set

set -euo pipefail

CI_RUN_ID=$1
COMMIT_SHA=$2
REGISTRY=$3
IMAGE_NAME=$4

echo "🔍 Retrieving artifact digest from CI workflow..." >&2

# Download CI workflow artifacts to get the digest
gh run download "$CI_RUN_ID" --name coverage-reports --dir /tmp/ci-artifacts || true

# Get artifact digest from artifact manager
DIGEST=$(python3 scripts/artifact_manager.py get-digest --commit "$COMMIT_SHA" 2>/dev/null || echo "")

if [ -z "$DIGEST" ]; then
  echo "❌ No artifact digest found for commit $COMMIT_SHA" >&2
  echo "This indicates the CI workflow did not create an artifact (likely due to CI gating failure)" >&2
  exit 1
fi

echo "✅ Found artifact digest: $DIGEST" >&2
echo "DIGEST=$DIGEST"

# Validate the digest format
python3 scripts/artifact_manager.py validate-digest \
  --digest "$DIGEST" \
  --registry "$REGISTRY" \
  --repository "$IMAGE_NAME"
