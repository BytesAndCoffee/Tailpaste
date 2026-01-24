#!/bin/bash
# Mark artifact as deployable or failed
# Arguments: $1 - test status (passed/failed)
# Arguments: $2 - artifact digest

set -euo pipefail

TEST_STATUS=$1
ARTIFACT_DIGEST=$2

echo "🏷️ Updating artifact deployment status..." >&2

if [ "$TEST_STATUS" = "passed" ]; then
  # Mark artifact as deployable
  python3 scripts/artifact_manager.py update-status \
    --digest "$ARTIFACT_DIGEST" \
    --status "deployable" \
    --timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  
  echo "✅ Artifact marked as DEPLOYABLE" >&2
  echo "deployable=true"
else
  # Mark artifact as failed
  python3 scripts/artifact_manager.py update-status \
    --digest "$ARTIFACT_DIGEST" \
    --status "failed" \
    --timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  
  echo "❌ Artifact marked as FAILED - deployment blocked" >&2
  echo "deployable=false"
fi
