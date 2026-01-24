#!/bin/bash
# Generate integration test summary
# Arguments: $1 - artifact digest
# Arguments: $2 - test status
# Arguments: $3 - deployable (true/false)

set -euo pipefail

ARTIFACT_DIGEST=$1
TEST_STATUS=$2
DEPLOYABLE=$3

echo "================================"
echo "Integration Test Summary"
echo "Artifact Digest: $ARTIFACT_DIGEST"
echo "Test Status: $TEST_STATUS"
echo "Deployable: $DEPLOYABLE"
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "================================"

# Add to GitHub Step Summary
echo "## Integration Test Results" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY
echo "- **Artifact Digest**: \`$ARTIFACT_DIGEST\`" >> $GITHUB_STEP_SUMMARY
echo "- **Test Status**: $( [ "$TEST_STATUS" = "passed" ] && echo '✅ PASSED' || echo '❌ FAILED' )" >> $GITHUB_STEP_SUMMARY
echo "- **Deployable**: $( [ "$DEPLOYABLE" = "true" ] && echo '✅ YES' || echo '❌ NO' )" >> $GITHUB_STEP_SUMMARY
echo "- **Timestamp**: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $GITHUB_STEP_SUMMARY

if [ "$TEST_STATUS" = "failed" ]; then
  echo "" >> $GITHUB_STEP_SUMMARY
  echo "⚠️ **Deployment Blocked**: Integration tests failed. The artifact will not be deployed." >> $GITHUB_STEP_SUMMARY
fi
