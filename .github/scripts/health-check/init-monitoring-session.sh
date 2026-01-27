#!/bin/bash
# Initialize health monitoring session
# Extracted from health-monitor.yml

set -e

echo "🏥 Starting continuous health monitoring session..."

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "⚠️  WARNING: GitHub CLI not available"
    echo "   Skipping GitHub variable operations"
    DEPLOYED_DIGEST=""
    DEPLOYMENT_STATUS="unknown"
else
    # Get current deployment state
    DEPLOYED_DIGEST=$(gh variable get DEPLOYED_ARTIFACT_DIGEST --repo "$GITHUB_REPOSITORY" 2>/dev/null || echo "")
    DEPLOYMENT_STATUS=$(gh variable get DEPLOYMENT_STATUS --repo "$GITHUB_REPOSITORY" 2>/dev/null || echo "unknown")
fi

echo "Current deployed artifact: ${DEPLOYED_DIGEST:-'none'}"
echo "Current deployment status: $DEPLOYMENT_STATUS"

# Initialize monitoring session variables
MONITORING_SESSION_ID="health-$(date +%Y%m%d-%H%M%S)-$(openssl rand -hex 4)"
echo "MONITORING_SESSION_ID=$MONITORING_SESSION_ID" >> "$GITHUB_ENV"
echo "DEPLOYED_DIGEST=$DEPLOYED_DIGEST" >> "$GITHUB_ENV"
echo "DEPLOYMENT_STATUS=$DEPLOYMENT_STATUS" >> "$GITHUB_ENV"

# Record monitoring session start (if gh is available)
if command -v gh &> /dev/null; then
    gh variable set LAST_HEALTH_CHECK_START --body "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --repo "$GITHUB_REPOSITORY" || echo "⚠️  Failed to set LAST_HEALTH_CHECK_START"
    gh variable set HEALTH_MONITORING_SESSION --body "$MONITORING_SESSION_ID" --repo "$GITHUB_REPOSITORY" || echo "⚠️  Failed to set HEALTH_MONITORING_SESSION"
fi

echo "✅ Health monitoring session initialized: $MONITORING_SESSION_ID"
