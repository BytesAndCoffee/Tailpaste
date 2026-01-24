#!/bin/bash
# Mark artifact as deployable or failed
# Arguments: $1 - test status (passed/failed)
# Arguments: $2 - artifact digest

set -euo pipefail

TEST_STATUS=$1
ARTIFACT_DIGEST=$2

echo "🏷️ Updating artifact deployment status..."

if [ "$TEST_STATUS" = "passed" ]; then
  # Mark artifact as deployable
  python scripts/artifact_manager.py update-status \
    --digest "$ARTIFACT_DIGEST" \
    --status "deployable" \
    --timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  
  echo "✅ Artifact marked as DEPLOYABLE"
  echo "DEPLOYABLE=true"
else
  # Mark artifact as failed
  python scripts/artifact_manager.py update-status \
    --digest "$ARTIFACT_DIGEST" \
    --status "failed" \
    --timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  
  echo "❌ Artifact marked as FAILED - deployment blocked"
  echo "DEPLOYABLE=false"
fi
