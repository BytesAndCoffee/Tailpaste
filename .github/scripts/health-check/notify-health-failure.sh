#!/bin/bash
# Generate failure notification for health check
# Arguments: $1 - health check outcome
# Arguments: $2 - GitHub run number
# Arguments: $3 - GitHub repository
# Arguments: $4 - GitHub run ID

set -euo pipefail

OUTCOME=$1
RUN_NUMBER=$2
REPOSITORY=$3
RUN_ID=$4

echo "## ⚠️ Health Check Failed" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY
echo "The service health check has failed with outcome: **$OUTCOME**" >> $GITHUB_STEP_SUMMARY
echo "The deploy workflow has been triggered to attempt recovery." >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY
echo "**Failure Details:**" >> $GITHUB_STEP_SUMMARY
echo "- Run Number: $RUN_NUMBER" >> $GITHUB_STEP_SUMMARY
echo "- Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $GITHUB_STEP_SUMMARY
echo "- Run URL: https://github.com/$REPOSITORY/actions/runs/$RUN_ID" >> $GITHUB_STEP_SUMMARY
echo "" >> $GITHUB_STEP_SUMMARY
echo "**Next Steps:**" >> $GITHUB_STEP_SUMMARY
echo "1. Monitor the deploy workflow execution" >> $GITHUB_STEP_SUMMARY
echo "2. Check service logs for errors" >> $GITHUB_STEP_SUMMARY
echo "3. Verify service availability after deployment" >> $GITHUB_STEP_SUMMARY
