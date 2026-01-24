#!/bin/bash
# Reset circuit breaker
# Arguments: $1 - GitHub repository
# Arguments: $2 - reset_failures (true/false)
# Arguments: $3 - GitHub actor
# Environment: GH_TOKEN must be set

set -euo pipefail

REPOSITORY=$1
RESET_FAILURES=$2
ACTOR=$3

echo "🔄 Resetting circuit breaker..."

if [ "$RESET_FAILURES" = "true" ]; then
  python3 scripts/circuit_breaker.py --repo "$REPOSITORY" close
else
  python3 scripts/circuit_breaker.py --repo "$REPOSITORY" close --keep-failures
fi

if [ $? -eq 0 ]; then
  echo "✅ Circuit breaker reset successfully"
  
  # Record manual reset
  gh variable set LAST_MANUAL_CB_RESET --body "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --repo "$REPOSITORY"
  gh variable set MANUAL_CB_RESET_BY --body "$ACTOR" --repo "$REPOSITORY"
else
  echo "❌ Failed to reset circuit breaker"
  exit 1
fi
