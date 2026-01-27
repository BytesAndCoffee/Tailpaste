#!/bin/bash
# Cleanup circuit breaker monitoring session
# Arguments: $1 - GitHub repository
# Arguments: $2 - monitoring session ID
# Environment: GH_TOKEN must be set

set -euo pipefail

REPOSITORY=${1:?Repository is required}
MONITORING_SESSION_ID=${2:-}

if [ -z "$MONITORING_SESSION_ID" ]; then
	echo "MONITORING_SESSION_ID is empty; skipping variable update" >&2
	exit 1
fi

echo "🧹 Cleaning up circuit breaker monitoring session..."

# Update last monitoring session
gh variable set LAST_CB_MONITORING_SESSION --body "$MONITORING_SESSION_ID" --repo "$REPOSITORY"
gh variable set LAST_CB_MONITORING_TIME --body "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --repo "$REPOSITORY"

echo "✅ Circuit breaker monitoring session cleanup completed"
