#!/bin/bash
# Check circuit breaker status and output results
# Arguments: $1 - GitHub repository
# Environment: GH_TOKEN must be set

set -euo pipefail

log() { echo "$@" >&2; }

REPOSITORY=$1

log "🔍 Checking comprehensive circuit breaker status..."

# Use the enhanced circuit breaker script
python3 scripts/ci/circuit_breaker.py --repo "$REPOSITORY" status --json > /tmp/cb_status.json

# Parse status
CB_STATUS=$(python3 -c "import json; data=json.load(open('/tmp/cb_status.json')); print(data['status'])")
RECOVERY_FAILURES=$(python3 -c "import json; data=json.load(open('/tmp/cb_status.json')); print(data['recovery_failure_count'])")
DEPLOYMENT_FAILURES=$(python3 -c "import json; data=json.load(open('/tmp/cb_status.json')); print(data['deployment_failure_count'])")
RECOVERY_THRESHOLD=$(python3 -c "import json; data=json.load(open('/tmp/cb_status.json')); print(data['recovery_threshold'])")
DEPLOYMENT_THRESHOLD=$(python3 -c "import json; data=json.load(open('/tmp/cb_status.json')); print(data['deployment_threshold'])")

log "Circuit Breaker Status: $CB_STATUS"
log "Recovery Failures: $RECOVERY_FAILURES / $RECOVERY_THRESHOLD"
log "Deployment Failures: $DEPLOYMENT_FAILURES / $DEPLOYMENT_THRESHOLD"

# Output for GitHub Actions (stdout only)
printf 'CB_STATUS=%s\n' "$CB_STATUS"
printf 'RECOVERY_FAILURES=%s\n' "$RECOVERY_FAILURES"
printf 'DEPLOYMENT_FAILURES=%s\n' "$DEPLOYMENT_FAILURES"
printf 'RECOVERY_THRESHOLD=%s\n' "$RECOVERY_THRESHOLD"
printf 'DEPLOYMENT_THRESHOLD=%s\n' "$DEPLOYMENT_THRESHOLD"

# Check if thresholds are exceeded
RECOVERY_EXCEEDED=$([[ $RECOVERY_FAILURES -ge $RECOVERY_THRESHOLD ]] && echo "true" || echo "false")
DEPLOYMENT_EXCEEDED=$([[ $DEPLOYMENT_FAILURES -ge $DEPLOYMENT_THRESHOLD ]] && echo "true" || echo "false")

printf 'RECOVERY_EXCEEDED=%s\n' "$RECOVERY_EXCEEDED"
printf 'DEPLOYMENT_EXCEEDED=%s\n' "$DEPLOYMENT_EXCEEDED"

if [ "$CB_STATUS" = "open" ]; then
  log "🚫 Circuit breaker is currently OPEN"
elif [ "$RECOVERY_EXCEEDED" = "true" ] || [ "$DEPLOYMENT_EXCEEDED" = "true" ]; then
  log "⚠️  Thresholds exceeded but circuit breaker is still closed"
else
  log "✅ Circuit breaker is healthy"
fi
