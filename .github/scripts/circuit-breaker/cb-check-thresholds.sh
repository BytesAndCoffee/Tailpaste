#!/bin/bash
# Check circuit breaker thresholds and auto-open if needed
# Arguments: $1 - GitHub repository
# Environment: GH_TOKEN must be set

set -euo pipefail

REPOSITORY=$1

echo "🔍 Checking thresholds and auto-opening if needed..."

# Use the enhanced circuit breaker script to check and auto-open
if python3 scripts/circuit_breaker.py --repo "$REPOSITORY" check; then
  echo "✅ Thresholds are within limits"
else
  echo "🚫 Circuit breaker was automatically opened due to threshold violations"
  
  # Record the automatic opening
  gh variable set LAST_AUTOMATIC_CB_TRIGGER --body "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --repo "$REPOSITORY"
  gh variable set AUTOMATIC_CB_TRIGGER_REASON --body "threshold_monitoring" --repo "$REPOSITORY"
fi
