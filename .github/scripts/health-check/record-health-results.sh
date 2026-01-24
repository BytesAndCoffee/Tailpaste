#!/bin/bash
# Record health check results
# Extracted from health-monitor.yml

set -e

echo "📊 Recording health check results..."

OVERALL_HEALTH="$1"
HEALTH_DETAILS="$2"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Record results in GitHub variables
gh variable set LAST_HEALTH_CHECK_STATUS --body "$OVERALL_HEALTH" --repo "$GITHUB_REPOSITORY"
gh variable set LAST_HEALTH_CHECK_TIME --body "$TIMESTAMP" --repo "$GITHUB_REPOSITORY"
gh variable set LAST_HEALTH_CHECK_SESSION --body "$MONITORING_SESSION_ID" --repo "$GITHUB_REPOSITORY"

# Record in artifact manager if we have a deployed artifact
if [ -n "$DEPLOYED_DIGEST" ]; then
  echo "Recording health check for deployed artifact: $DEPLOYED_DIGEST"
  
  python scripts/ci/artifact_manager.py record-test-result \
    --digest "$DEPLOYED_DIGEST" \
    --test-type "health_check" \
    --status "$OVERALL_HEALTH" \
    --timestamp "$TIMESTAMP" \
    --details "Continuous health monitoring: $HEALTH_DETAILS"
else
  echo "⚠️  No deployed artifact found - health check not recorded in artifact manager"
fi

# Update health check history (keep last 10 results)
HEALTH_HISTORY=$(gh variable get HEALTH_CHECK_HISTORY --repo "$GITHUB_REPOSITORY" 2>/dev/null || echo "[]")

export HEALTH_HISTORY
export TIMESTAMP
export OVERALL_HEALTH
export MONITORING_SESSION_ID

UPDATED_HISTORY=$(python3 scripts/health/update_health_history.py)

gh variable set HEALTH_CHECK_HISTORY --body "$UPDATED_HISTORY" --repo "$GITHUB_REPOSITORY"

echo "✅ Health check results recorded"
