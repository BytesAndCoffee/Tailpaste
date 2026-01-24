#!/bin/bash
# Generate health check summary for GitHub Actions
# Arguments: $1 - health check outcome (success/failure)
# Arguments: $2 - GitHub run number

set -euo pipefail

OUTCOME=$1
RUN_NUMBER=$2

echo "## Health Check Summary" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY
echo "- **Status**: $OUTCOME" >> $GITHUB_STEP_SUMMARY
echo "- **Timestamp**: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $GITHUB_STEP_SUMMARY
echo "- **Run Number**: $RUN_NUMBER" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY

if [ -f /tmp/health_check_results.json ]; then
  echo "### Detailed Results" >> $GITHUB_STEP_SUMMARY
  echo "\`\`\`json" >> $GITHUB_STEP_SUMMARY
  cat /tmp/health_check_results.json >> $GITHUB_STEP_SUMMARY
  echo "\`\`\`" >> $GITHUB_STEP_SUMMARY
fi
