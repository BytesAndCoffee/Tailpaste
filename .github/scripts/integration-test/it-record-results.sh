#!/bin/bash
# Record integration test results
# Arguments: $1 - job status
# Arguments: $2 - artifact digest

set -euo pipefail

TEST_STATUS=$1
ARTIFACT_DIGEST=$2
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "📊 Recording integration test results..."

# Determine final test status
if [ "$TEST_STATUS" = "success" ]; then
  FINAL_STATUS="passed"
  echo "✅ Integration tests PASSED"
else
  FINAL_STATUS="failed"
  echo "❌ Integration tests FAILED"
fi

echo "FINAL_STATUS=$FINAL_STATUS"

# Record test outcome in artifact manager
python scripts/artifact_manager.py record-test-result \
  --digest "$ARTIFACT_DIGEST" \
  --test-type "integration" \
  --status "$FINAL_STATUS" \
  --timestamp "$TIMESTAMP" \
  --details "Integration tests completed with status: $FINAL_STATUS"

echo "📝 Test results recorded for artifact: $ARTIFACT_DIGEST"
