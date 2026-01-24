#!/bin/bash
# Record integration test results
# Arguments: $1 - job status
# Arguments: $2 - artifact digest

set -euo pipefail

TEST_STATUS=$1
ARTIFACT_DIGEST=$2
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "📊 Recording integration test results..." >&2

# Determine final test status
if [ "$TEST_STATUS" = "success" ]; then
  FINAL_STATUS="passed"
  echo "✅ Integration tests PASSED" >&2
else
  FINAL_STATUS="failed"
  echo "❌ Integration tests FAILED" >&2
fi

echo "status=$FINAL_STATUS"

# Record test outcome in artifact manager only if we have a valid digest
if [ -n "$ARTIFACT_DIGEST" ]; then
  python3 scripts/ci/artifact_manager.py record-test-result \
    --digest "$ARTIFACT_DIGEST" \
    --test-type "integration" \
    --status "$FINAL_STATUS" \
    --timestamp "$TIMESTAMP" \
    --details "Integration tests completed with status: $FINAL_STATUS"
  
  echo "📝 Test results recorded for artifact: $ARTIFACT_DIGEST" >&2
else
  echo "⚠️  No artifact digest available - skipping artifact manager recording" >&2
fi
